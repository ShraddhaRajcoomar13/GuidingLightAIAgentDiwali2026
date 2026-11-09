from providers.base import Embedder, ApiError
from providers.openai_common import post

class OpenAIEmbedder(Embedder):
    def __init__(self, key, model): self.key = key; self.model = model
    def embed(self, texts):
        r = post("/embeddings", self.key, timeout=60, json={"model": self.model, "input": texts})
        try: return [d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"])]
        except Exception: raise ApiError("other")
