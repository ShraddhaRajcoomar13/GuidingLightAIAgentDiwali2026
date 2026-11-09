from providers.base import STTProvider, ApiError
from providers.openai_common import post

class OpenAISTT(STTProvider):
    def __init__(self, key, model): self.key = key; self.model = model
    def transcribe(self, wav_bytes):
        r = post("/audio/transcriptions", self.key, timeout=60,
                 files={"file": ("speech.wav", wav_bytes, "audio/wav")}, data={"model": self.model})
        try: return r.json().get("text", "")
        except Exception: raise ApiError("other")
