import os, sqlite3
import numpy as np

class RamayanaRetriever:
    """Swap-able: anything with available() and search(query,k)->[{'page','text','score'}]."""
    def __init__(self, db_path, embedder, min_score=0.25):
        self.path = str(db_path); self.emb = embedder; self.min = min_score
        self._m = None; self._rows = None

    def available(self):
        try:
            if not os.path.exists(self.path): return False
            con = sqlite3.connect(self.path)
            n = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            con.close()
            return n > 0
        except Exception:
            return False

    def _load(self):
        if self._m is not None: return
        con = sqlite3.connect(self.path)
        rows = con.execute("SELECT page,text,embedding FROM chunks").fetchall(); con.close()
        m = np.vstack([np.frombuffer(r[2], dtype=np.float32) for r in rows])
        self._m = m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
        self._rows = [(r[0], r[1]) for r in rows]

    def search(self, query, k=5):
        self._load()
        q = np.asarray(self.emb.embed([query])[0], dtype=np.float32)
        q /= (np.linalg.norm(q) + 1e-9)
        s = self._m @ q
        idx = np.argsort(-s)[:k]
        return [{"page": self._rows[i][0], "text": self._rows[i][1], "score": float(s[i])} for i in idx if s[i] >= self.min]
