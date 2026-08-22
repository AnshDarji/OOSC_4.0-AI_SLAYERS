"""
NYAAY AI — Supreme Court Judgment Corpus Analysis & Embedding Benchmark
Runs in the BACKEND venv. Analyses corpus stats then benchmarks embedding throughput.
"""
import json, os, glob, sys, time, statistics, gc, traceback
import psutil

# ─── 1. CORPUS STATISTICS ─────────────────────────────────────────────────
folder = os.path.join(os.path.dirname(__file__), '..', 'data', 'judgments')
files = sorted(glob.glob(os.path.join(folder, '*.json')))
print(f"Files found: {len(files)}")

texts = []
field_counts = {k: 0 for k in ('petitioner','respondent','bench','judgment_dates','case_no','sections_cited','articles_cited')}

for f in files:
    try:
        d = json.load(open(f, encoding='utf-8', errors='ignore'))
        t = (d.get('text') or '')
        texts.append(len(t))
        for k in field_counts:
            v = d.get(k)
            if v and str(v).strip() not in ('', '-', 'null', 'None'):
                field_counts[k] += 1
    except Exception as e:
        pass

total_chars = sum(texts)
total_tok   = total_chars // 4     # ~4 chars/token (BPE estimate)
n           = len(texts)

print("\n=== CORPUS STATISTICS ===")
print(f"Total judgments          : {n:,}")
print(f"Total characters         : {total_chars:,}")
print(f"Total estimated tokens   : {total_tok:,}")
print(f"Average chars/judgment   : {total_chars//n:,}")
print(f"Median chars/judgment    : {int(statistics.median(texts)):,}")
print(f"Max chars/judgment       : {max(texts):,}")
print(f"Min chars/judgment       : {min(texts):,}")
print(f"Average tokens/judgment  : {total_tok//n:,}")

buckets = [0]*5
for t in texts:
    tok = t // 4
    if   tok <  1000: buckets[0] += 1
    elif tok <  3000: buckets[1] += 1
    elif tok <  6000: buckets[2] += 1
    elif tok < 12000: buckets[3] += 1
    else:             buckets[4] += 1

print("Token distribution:")
labels = ['<1k','1k-3k','3k-6k','6k-12k','>12k']
for l, b in zip(labels, buckets):
    bar = '#' * (b * 40 // n)
    print(f"  {l:>7}: {b:4d} ({b*100//n:2d}%)  {bar}")

# Chunk estimate: 400-token chunks with 50-token overlap → net 350 tokens/chunk
net_chunk_tok = 350
total_chunks_estimate = sum(max(1, (t // 4 + net_chunk_tok - 1) // net_chunk_tok) for t in texts)
print(f"\nEstimated chunks (400-tok, 50-overlap) : {total_chunks_estimate:,}")
print(f"Average chunks/judgment                : {total_chunks_estimate/n:.1f}")

print("\nMetadata field availability:")
for k, v in field_counts.items():
    print(f"  {k:20}: {v}/{n} ({v*100//n}%)")


# ─── 2. EMBEDDING MODEL INFO ──────────────────────────────────────────────
print("\n=== EMBEDDING MODEL ===")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from app.knowledge.embeddings import embedding_service
    model_name = getattr(embedding_service, 'model_name', 'unknown')
    print(f"Model                    : {model_name}")
    raw_model = getattr(embedding_service, 'model', None)
    if raw_model:
        total_params = sum(p.numel() for p in raw_model.parameters() if hasattr(raw_model, 'parameters'))
        print(f"Parameters               : {total_params/1e6:.1f}M")
    # Get embedding dim from a test
    test_emb = embedding_service.embed_texts(["test"])
    print(f"Embedding dimension      : {len(test_emb[0])}")
    print("Status                   : Loaded OK")
    embed_fn = embedding_service.embed_texts
except Exception as e:
    print(f"ERROR loading model: {e}")
    sys.exit(1)


# ─── 3. REPRESENTATIVE SAMPLE BENCHMARK ───────────────────────────────────
print("\n=== BENCHMARK: 50 judgments ===")

sample_files = files[:50]

# Load texts
t0 = time.perf_counter()
sample_data = []
for f in sample_files:
    try:
        d = json.load(open(f, encoding='utf-8', errors='ignore'))
        sample_data.append(d)
    except:
        pass
load_time = time.perf_counter() - t0
print(f"Load/preprocess 50 judgments : {load_time:.2f}s")

# Chunk them (simple fixed-size character chunking matching ~400 tokens)
t1 = time.perf_counter()
CHUNK_CHARS = 1600     # 400 tokens * 4 chars
OVERLAP_CHARS = 200    # 50 tokens overlap

all_chunks = []
for d in sample_data:
    text = (d.get('text') or '').strip()
    if not text:
        continue
    start = 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        chunk = text[start:end]
        all_chunks.append(chunk)
        if end == len(text):
            break
        start += CHUNK_CHARS - OVERLAP_CHARS

chunk_time = time.perf_counter() - t1
print(f"Chunking 50 judgments        : {chunk_time:.3f}s  → {len(all_chunks)} chunks")

# Benchmark batch sizes
def bench_batch(chunks, batch_size):
    total = 0.0
    i = 0
    while i < len(chunks):
        batch = chunks[i:i+batch_size]
        t = time.perf_counter()
        embed_fn(batch)
        total += time.perf_counter() - t
        i += batch_size
    return total

print(f"\nEmbedding throughput benchmark ({len(all_chunks)} chunks):")
print(f"{'Batch':>8} | {'Total(s)':>10} | {'Chunks/s':>10} | {'Emb/s':>10}")
print("-" * 48)

results = {}
for bs in [8, 16, 32]:
    gc.collect()
    elapsed = bench_batch(all_chunks, bs)
    cps = len(all_chunks) / elapsed
    results[bs] = {'elapsed': elapsed, 'cps': cps}
    print(f"{bs:>8} | {elapsed:>10.2f} | {cps:>10.1f} | {cps:>10.1f}")

# Best batch
best_bs = max(results, key=lambda b: results[b]['cps'])
best_cps = results[best_bs]['cps']

# ─── 4. EXTRAPOLATION ──────────────────────────────────────────────────────
print("\n=== FULL CORPUS PROJECTION ===")

# Scale chunks to full corpus
sample_chunks = len(all_chunks)
scale = total_chunks_estimate / sample_chunks

est_embed_s   = (total_chunks_estimate / best_cps)
est_load_s    = load_time * (n / 50)
est_chunk_s   = chunk_time * (n / 50)
est_chroma_s  = total_chunks_estimate * 0.002   # ~2ms per chunk for insertion
est_total_s   = est_embed_s + est_load_s + est_chunk_s + est_chroma_s

def fmt_time(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    return f"{h}h {m}m"

print(f"Optimal batch size           : {best_bs}")
print(f"Measured throughput          : {best_cps:.1f} chunks/sec")
print(f"Total estimated chunks       : {total_chunks_estimate:,}")
print()
print(f"  Embedding time             : {fmt_time(est_embed_s)}  ({est_embed_s:.0f}s)")
print(f"  Load/parse time            : {fmt_time(est_load_s)}  ({est_load_s:.0f}s)")
print(f"  Chunking time              : {fmt_time(est_chunk_s)}  ({est_chunk_s:.0f}s)")
print(f"  ChromaDB insertion         : {fmt_time(est_chroma_s)}  ({est_chroma_s:.0f}s)")
print(f"  ─────────────────────────────────")
print(f"  TOTAL (Expected)           : {fmt_time(est_total_s)}")
print(f"  Best-case  (×0.8)          : {fmt_time(est_total_s * 0.8)}")
print(f"  Worst-case (×1.4)          : {fmt_time(est_total_s * 1.4)}")

print("\nRAM usage now:", round(psutil.virtual_memory().used / (1024**3), 2), "GB used")
print("\nDone.")
