import json
from providers.base import LLMProvider, ApiError
from providers.openai_common import post

class OpenAILLM(LLMProvider):
    def __init__(self, key, model):
        self.key = key; self.model = model; self.last_usage = {}

    def stream(self, messages, max_tokens=300, temperature=0.8, cancel=None):
        body = {"model": self.model, "messages": messages, "stream": True,
                "max_completion_tokens": max_tokens, "stream_options": {"include_usage": True}}
        if temperature is not None: body["temperature"] = temperature
        r = post("/chat/completions", self.key, timeout=90, json=body, stream=True)
        try:
            for line in r.iter_lines():
                if cancel is not None and cancel.is_set(): return
                if not line: continue
                line = line.decode("utf-8", "ignore")
                if not line.startswith("data:"): continue
                d = line[5:].strip()
                if d == "[DONE]": break
                try: j = json.loads(d)
                except Exception: continue
                if j.get("usage"): self.last_usage = j["usage"]
                ch = j.get("choices") or []
                if ch:
                    t = (ch[0].get("delta") or {}).get("content")
                    if t: yield t
        finally:
            r.close()

    def complete(self, messages, json_mode=False, max_tokens=400):
        body = {"model": self.model, "messages": messages, "max_completion_tokens": max_tokens}
        if json_mode: body["response_format"] = {"type": "json_object"}
        r = post("/chat/completions", self.key, timeout=60, json=body)
        try: return r.json()["choices"][0]["message"]["content"] or ""
        except Exception: raise ApiError("other")
