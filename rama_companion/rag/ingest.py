import re, sqlite3, hashlib, time, os
import numpy as np

def chunk_page(text, size=800, overlap=100):
    text = re.sub(r"\s+", " ", text or "").strip()
    out, i = [], 0
    while i < len(text):
        j = min(len(text), i + size)
        if j < len(text):
            k = max(text.rfind(". ", i + size // 2, j), text.rfind("? ", i + size // 2, j), text.rfind("! ", i + size // 2, j))
            if k > 0: j = k + 1
        out.append(text[i:j].strip())
        if j >= len(text): break
        i = max(j - overlap, i + 1)
    return [c for c in out if len(c) >= 80]

def ingest(pdf_path, out_db, embedder, title=None, progress=print):
    from pypdf import PdfReader
    sha = hashlib.sha256(open(pdf_path, "rb").read()).hexdigest()
    reader = PdfReader(pdf_path)
    chunks = []
    for n, page in enumerate(reader.pages, 1):
        try: t = page.extract_text() or ""
        except Exception: t = ""
        for c in chunk_page(t): chunks.append((n, c))
    if sum(len(c) for _, c in chunks) < 2000:
        raise RuntimeError("Almost no text could be extracted. The PDF may be scanned images (needs OCR) or protected.")
    progress(f"{len(chunks)} chunks from {len(reader.pages)} pages; embedding...")
    tmp = str(out_db) + ".tmp"
    if os.path.exists(tmp): os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.executescript("CREATE TABLE chunks(id INTEGER PRIMARY KEY, page INTEGER, text TEXT, embedding BLOB);"
                      "CREATE TABLE source(title TEXT, sha256 TEXT, ingested_at REAL, pages INTEGER);")
    B = 64
    for i in range(0, len(chunks), B):
        batch = chunks[i:i + B]
        vecs = embedder.embed([c for _, c in batch])
        con.executemany("INSERT INTO chunks(page,text,embedding) VALUES(?,?,?)",
                        [(p, c, np.asarray(v, dtype=np.float32).tobytes()) for (p, c), v in zip(batch, vecs)])
        progress(f"  embedded {min(i + B, len(chunks))}/{len(chunks)}")
    con.execute("INSERT INTO source VALUES(?,?,?,?)", (title or os.path.basename(pdf_path), sha, time.time(), len(reader.pages)))
    con.commit(); con.close()
    os.replace(tmp, out_db)
    progress("Done: " + str(out_db))
