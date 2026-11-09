class ApiError(Exception):
    """kind: nokey | auth | credits | rate | network | other"""
    def __init__(self, kind, detail=""):
        super().__init__(kind); self.kind = kind; self.detail = detail

MSG = {
    "nokey": "No API key is set yet. Open Settings, then Account, to add it.",
    "auth": "The API key was not accepted. Please check it in Settings, then Account.",
    "credits": "The OpenAI account is out of credits or over its spending limit. Open Settings, then Account, to check billing.",
    "rate": "The service is busy right now. Please wait a moment and try again.",
    "network": "I can't reach the internet right now. Typing will work again once you're back online.",
    "other": "Something went wrong talking to the service. Please try again.",
}

def friendly(e, what=""):
    base = MSG.get(getattr(e, "kind", "other"), MSG["other"])
    return ("Voice problem, so I'll show text only. " + base) if what == "voice" else base

class LLMProvider:
    def stream(self, messages, max_tokens, temperature, cancel=None): raise NotImplementedError
    def complete(self, messages, json_mode=False, max_tokens=400): raise NotImplementedError

class STTProvider:
    def transcribe(self, wav_bytes): raise NotImplementedError

class TTSProvider:
    def synth(self, text, voice, instructions=None): raise NotImplementedError

class Embedder:
    def embed(self, texts): raise NotImplementedError
