from providers.base import TTSProvider
from providers.openai_common import post

class OpenAITTS(TTSProvider):
    def __init__(self, key, model): self.key = key; self.model = model
    def synth(self, text, voice, instructions=None):
        body = {"model": self.model, "voice": voice, "input": text[:3500], "response_format": "wav"}
        if instructions and "gpt-4o" in self.model: body["instructions"] = instructions
        return post("/audio/speech", self.key, timeout=60, json=body).content
