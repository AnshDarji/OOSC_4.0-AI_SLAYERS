import os
import sys
import json
import glob
import time
import ast
import logging
from typing import List

# Ensure app is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.knowledge.embeddings import embedding_service
from app.knowledge.vector_store import vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Using absolute path for DATA_DIR since we will run from BACKEND/scripts
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

def process_file(file_path: str) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if not data or not data.get("text"):
            return False
            
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
            "source_file": os.path.basename(file_path)
        }
        
        case_id = f"SC_{os.path.basename(file_path).replace('.json', '')}"
        
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
            
            clean_meta = {}
            for k, v in meta.items():
                if v and v != "None":
                    clean_meta[k] = v
                    
            context_prefix = f"Case: {case_name}\nCourt: Supreme Court of India\n"
            doc_text = context_prefix + "\n" + chunk
            
            ids.append(chunk_id)
            documents.append(doc_text)
            metadatas.append(clean_meta)
            
        embeddings = embedding_service.embed_texts(documents)
        vector_store.add_chunks(ids, embeddings, documents, metadatas, target_collection="supreme_court_cases")
        
        return True
    except Exception as e:
        logger.error(f"Error processing {os.path.basename(file_path)}: {e}")
        return False

def main():
    logger.info("Starting SC Judgment Ingestion")
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    logger.info(f"Found {len(files)} JSON files in {DATA_DIR}")
    
    embedding_service.warmup()
    
    checkpoint = load_checkpoint()
    completed = set(checkpoint["completed_files"])
    
    total = len(files)
    processed = len(completed)
    start_time = time.time()
    
    for i, file_path in enumerate(files):
        basename = os.path.basename(file_path)
        if basename in completed:
            continue
            
        success = process_file(file_path)
        
        if success:
            checkpoint["completed_files"].append(basename)
        else:
            checkpoint["failed_files"].append(basename)
            
        if (i+1) % 10 == 0 or i == total - 1:
            save_checkpoint(checkpoint)
            elapsed = time.time() - start_time
            new_processed = (i + 1) - len(completed)
            rate = new_processed / elapsed if elapsed > 0 else 0
            rem_files = total - (i + 1)
            rem_time = rem_files / rate if rate > 0 else 0
            logger.info(f"Progress: {i+1}/{total} ({(i+1)/total*100:.2f}%) - Speed: {rate:.2f} files/sec - ETA: {rem_time/60:.2f} min")
            
    save_checkpoint(checkpoint)
    logger.info("Ingestion completed.")

if __name__ == "__main__":
    main()
