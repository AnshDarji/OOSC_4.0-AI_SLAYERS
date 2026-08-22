import os
import sys
import json
import glob
import time
import ast
import logging
import threading
import queue
import torch
from typing import List

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.knowledge.embeddings import embedding_service
from app.knowledge.vector_store import vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "judgments")
CHECKPOINT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ingestion_checkpoint.json")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Could not load checkpoint: {e}")
    return {"completed_files": [], "failed_files": []}

def save_checkpoint(checkpoint):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f)

def safe_eval_list(s):
    if not s or s == "null":
        return []
    try:
        if isinstance(s, str):
            parsed = ast.literal_eval(s)
            if isinstance(parsed, list):
                return parsed
        elif isinstance(s, list):
            return s
    except:
        pass
    return []

def chunk_text(text: str, max_chars: int = 1600, overlap_chars: int = 200) -> List[str]:
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
            
        if len(current_chunk) + len(p) + 2 > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            overlap_text = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else current_chunk
            first_space = overlap_text.find(" ")
            if first_space != -1:
                overlap_text = overlap_text[first_space+1:]
            current_chunk = overlap_text + "\n\n" + p
        else:
            if current_chunk:
                current_chunk += "\n\n" + p
            else:
                current_chunk = p
                
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def reader_worker(file_queue, chunk_queue, completed_files):
    while True:
        file_path = file_queue.get()
        if file_path is None:
            chunk_queue.put(None)
            break
            
        basename = os.path.basename(file_path)
        if basename in completed_files:
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if not data or not data.get("text"):
                chunk_queue.put(("error", basename))
                continue
                
            text = data["text"]
            
            case_no = data.get("case_no")
            if isinstance(case_no, list): case_no = ", ".join(case_no)
            case_name = f"{data.get('petitioner', 'Unknown')} v. {data.get('respondent', 'Unknown')}"
            
            base_metadata = {
                "case_name": case_name[:100],
                "petitioner": str(data.get("petitioner", ""))[:100],
                "respondent": str(data.get("respondent", ""))[:100],
                "judgment_date": str(data.get("judgment_dates", ""))[:50],
                "bench": str(data.get("bench", ""))[:200],
                "case_number": str(case_no)[:100],
                "sections_cited": ", ".join(safe_eval_list(data.get("sections_cited")))[:200],
                "articles_cited": ", ".join(safe_eval_list(data.get("articles_cited")))[:200],
                "source_type": "judgment",
                "authority_type": "judicial",
                "court_level": "Supreme Court",
                "jurisdiction": "India",
                "source_file": basename
            }
            
            case_id = f"SC_{basename.replace('.json', '')}"
            chunks = chunk_text(text)
            
            ids = []
            documents = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{case_id}_CHUNK_{i+1:06d}"
                
                meta = base_metadata.copy()
                meta["case_id"] = case_id
                meta["chunk_index"] = i + 1
                meta["total_chunks"] = len(chunks)
                
                clean_meta = {k: v for k, v in meta.items() if v and v != "None"}
                        
                context_prefix = f"Case: {case_name}\nCourt: Supreme Court of India\n"
                doc_text = context_prefix + "\n" + chunk
                
                ids.append(chunk_id)
                documents.append(doc_text)
                metadatas.append(clean_meta)
                
            logger.info(f"Reader: chunked {basename} into {len(chunks)} chunks.")
            chunk_queue.put(("success", basename, ids, documents, metadatas))
        except Exception as e:
            logger.error(f"Error parsing {basename}: {e}")
            chunk_queue.put(("error", basename))

def embedder_worker(chunk_queue, write_queue):
    # Let PyTorch handle threading optimally by default
    # Warmup
    embedding_service.warmup()
    logger.info("Embedder ready, entering loop.")
    
    # Use inference mode for speed
    with torch.inference_mode():
        while True:
            item = chunk_queue.get()
            if item is None:
                write_queue.put(None)
                break
                
            status = item[0]
            if status == "error":
                write_queue.put(item)
                continue
                
            _, basename, ids, documents, metadatas = item
            
            try:
                # Use default batch_size=32 which worked better
                embeddings = embedding_service.model.encode(documents, batch_size=32, normalize_embeddings=True, show_progress_bar=False).tolist()
                write_queue.put(("success", basename, ids, embeddings, documents, metadatas))
            except Exception as e:
                logger.error(f"Error embedding {basename}: {e}")
                write_queue.put(("error", basename))

def writer_worker(write_queue, total_files, completed_files, failed_files):
    checkpoint = {"completed_files": list(completed_files), "failed_files": list(failed_files)}
    processed = len(completed_files)
    start_time = time.time()
    
    # Process counter for periodic checkpointing
    writes_since_checkpoint = 0
    
    while True:
        item = write_queue.get()
        if item is None:
            break
            
        status = item[0]
        if status == "error":
            basename = item[1]
            checkpoint["failed_files"].append(basename)
        else:
            _, basename, ids, embeddings, documents, metadatas = item
            try:
                logger.info(f"Writer: inserting {basename}...")
                vector_store.add_chunks(ids, embeddings, documents, metadatas, target_collection="supreme_court_cases")
                checkpoint["completed_files"].append(basename)
                logger.info(f"Writer: completed {basename} ({len(checkpoint['completed_files'])} total)")
            except Exception as e:
                logger.error(f"Error writing to ChromaDB for {basename}: {e}")
                checkpoint["failed_files"].append(basename)
                
        writes_since_checkpoint += 1
        
        # Checkpoint every 50 files
        if writes_since_checkpoint >= 50:
            save_checkpoint(checkpoint)
            elapsed = time.time() - start_time
            rate = writes_since_checkpoint / elapsed if elapsed > 0 else 0
            
            rem_files = total_files - len(checkpoint["completed_files"])
            rem_time = rem_files / rate if rate > 0 else 0
            logger.info(f"Progress: {len(checkpoint['completed_files'])}/{total_files} ({len(checkpoint['completed_files'])/total_files*100:.2f}%) - Speed: {rate:.2f} files/sec - ETA: {rem_time/60:.2f} min")
            
            # Reset counters for the next window to get current speed
            start_time = time.time()
            writes_since_checkpoint = 0
            
    # Final save
    save_checkpoint(checkpoint)

def main():
    logger.info("Starting PIPELINED SC Judgment Ingestion")
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    logger.info(f"Found {len(files)} JSON files in {DATA_DIR}")
    
    checkpoint = load_checkpoint()
    completed_set = set(checkpoint["completed_files"])
    failed_set = set(checkpoint["failed_files"])
    
    file_queue = queue.Queue()
    chunk_queue = queue.Queue(maxsize=50) # Prevent memory ballooning
    write_queue = queue.Queue(maxsize=50)
    
    for f in files:
        file_queue.put(f)
    file_queue.put(None)
    
    # Start threads
    t_reader = threading.Thread(target=reader_worker, args=(file_queue, chunk_queue, completed_set))
    t_embedder = threading.Thread(target=embedder_worker, args=(chunk_queue, write_queue))
    t_writer = threading.Thread(target=writer_worker, args=(write_queue, len(files), completed_set, failed_set))
    
    t_reader.start()
    t_embedder.start()
    t_writer.start()
    
    t_reader.join()
    t_embedder.join()
    t_writer.join()
    
    logger.info("Ingestion completed.")

if __name__ == "__main__":
    main()
