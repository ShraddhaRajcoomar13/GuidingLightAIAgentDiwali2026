import json, logging, queue, re, threading
from PySide6.QtCore import QObject, Signal
from core import memory, prompts, safety
from core.paths import ramayana_db
from providers.base import ApiError, friendly
from providers.openai_llm import OpenAILLM
from providers.openai_stt import OpenAISTT
from providers.openai_tts import OpenAITTS
from providers.openai_embed import OpenAIEmbedder
from rag.retrieve import RamayanaRetriever

log = logging.getLogger("rama")
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

def split_sentences(buf, min_len=50):
    parts = _SPLIT.split(buf)
    if len(parts) == 1: return [], buf
    out, cur = [], ""
    for p in parts[:-1]:
        cur = (cur + " " + p).strip()
        if len(cur) >= min_len: out.append(cur); cur = ""
    rest = parts[-1]
    return out, ((cur + " " + rest).strip() if cur else rest)

class Bus(QObject):
    user_text = Signal(str)
    chunk = Signal(str)
    turn_done = Signal(int, str)
    state = Signal(str)          # idle | transcribing | thinking
    notice = Signal(str)
    audio = Signal(bytes)
    tts_finished = Signal()
    sources = Signal(list)

class Engine:
    def __init__(self, db, cfg, fam, key):
        self.db, self.cfg, self.fam = db, cfg, fam
        self.bus = Bus(); self.member = None
        self.companion = fam.get("default_companion", "rama")
        self.conv = None; self.mode = "chat"; self.speak = False
        self.cancel = threading.Event()
        self.set_key(key)

    def set_key(self, key):
        m = self.cfg["models"]
        self.llm = OpenAILLM(key, m["chat"]); self.stt = OpenAISTT(key, m["stt"])
        self.tts = OpenAITTS(key, m["tts"]); self.emb = OpenAIEmbedder(key, m["embed"])
        self.rag = RamayanaRetriever(ramayana_db(), self.emb, self.cfg["rag"]["min_score"])

    @property
    def voice(self):
        return self.db.get(f"voice_{self.companion}") or self.cfg["voices"].get(self.companion, "alloy")

    # ---- conversation lifecycle
    def start_conversation(self, mode):
        self.end_conversation()
        self.mode = mode
        self.conv = self.db.new_conv(self.member["id"], self.companion, mode)

    def end_conversation(self, wait=False):
        cid, self.conv = self.conv, None
        if not cid: return
        self.cancel.set(); self.db.end_conv(cid)
        if self.db.get("memory_on", "1") != "1": return
        def work():
            try: memory.extract(self.db, self.llm, cid, self.member["id"], self.cfg["memory"]["max_per_call"])
            except Exception as e: log.warning("memory extraction failed: %s", type(e).__name__)
        t = threading.Thread(target=work, daemon=True); t.start()
        if wait: t.join(10)


    def speak_text(self, text):
        if not text: return
        def run():
            try:
                wav = self.tts.synth(text, self.voice, self.cfg["tts_instructions"].get(self.companion))
                self.bus.audio.emit(wav)
            except ApiError as e:
                self.bus.notice.emit(friendly(e, "voice"))
        threading.Thread(target=run, daemon=True).start()

    def interrupt(self): self.cancel.set()

    def _begin(self):
        self.cancel.set(); self.cancel = threading.Event(); return self.cancel

    # ---- entry points (each runs in a worker thread)
    def submit(self, text):
        ev = self._begin(); threading.Thread(target=self._turn, args=(text, ev, False), daemon=True).start()

    def greet(self):
        ev = self._begin(); threading.Thread(target=self._turn, args=(None, ev, True), daemon=True).start()

    def voice_turn(self, wav):
        ev = self._begin()
        def run():
            try:
                self.bus.state.emit("transcribing")
                text = self.stt.transcribe(wav).strip()
            except ApiError as e:
                self.bus.notice.emit(friendly(e)); self.bus.state.emit("idle"); return
            except Exception:
                log.exception("stt failed"); self.bus.notice.emit("I couldn't understand the recording. Please try again or type."); self.bus.state.emit("idle"); return
            if ev.is_set(): return
            if not text:
                self.bus.notice.emit("I couldn't make out any words. Tap the microphone and try again, or type."); self.bus.state.emit("idle"); return
            self.bus.user_text.emit(text)
            self._turn(text, ev, False)
        threading.Thread(target=run, daemon=True).start()

    def preview_voice(self):
        def run():
            try: self.bus.audio.emit(self.tts.synth("Hello, I'm glad you're here.", self.voice, self.cfg["tts_instructions"].get(self.companion)))
            except ApiError as e: self.bus.notice.emit(friendly(e, "voice"))
        threading.Thread(target=run, daemon=True).start()

    # ---- internals
    def _tts_loop(self, tq, ev):
        ok = True
        try:
            while True:
                s = tq.get()
                if s is None or ev.is_set(): break
                if not ok: continue
                try:
                    wav = self.tts.synth(s, self.voice, self.cfg["tts_instructions"].get(self.companion))
                    if not ev.is_set(): self.bus.audio.emit(wav)
                except ApiError as e:
                    ok = False; self.bus.notice.emit(friendly(e, "voice"))
                except Exception:
                    ok = False; log.exception("tts failed"); self.bus.notice.emit("Voice problem, so I'll show text only.")
        finally:
            self.bus.tts_finished.emit()

    def _canned(self, text, ev, speak):
        self.bus.chunk.emit(text)
        mid = self.db.add_msg(self.conv, "assistant", text)
        self.bus.turn_done.emit(mid, text)
        if speak:
            tq = queue.Queue(); tq.put(text); tq.put(None); self._tts_loop(tq, ev)

    def _story_excerpts(self, text):
        if not self.rag.available():
            return ("The Ramayana text hasn't been loaded on this computer yet, so I can't tell stories from it just now. "
                    "I'd rather say so than make something up. Please ask whoever set this up to add the book.")
        q = text
        if len(text) < 60:
            prev = [m for m in self.db.msgs(self.conv) if m["role"] == "user"][-2:-1]
            if prev: q = prev[0]["content"][:200] + " " + text
        hits = self.rag.search(q, self.cfg["rag"]["top_k"])
        if not hits:
            return "I looked through the text I have and couldn't find that. I don't want to guess, so could you tell me a little more, or ask about a different part of the story?"
        return hits

    def _turn(self, text, ev, greeting):
        b, speak = self.bus, self.speak
        tq, tt, tts_handled = queue.Queue(), None, False
        try:
            if self.conv is None: return
            b.state.emit("thinking")
            excerpts = None
            if not greeting:
                self.db.add_msg(self.conv, "user", text)
                kind = safety.check(text)
                if kind:
                    tts_handled = speak
                    return self._canned(safety.reply(kind, self.fam.get("helplines", [])), ev, speak)
                if self.mode == "story":
                    r = self._story_excerpts(text)
                    if isinstance(r, str):
                        tts_handled = speak
                        return self._canned(r, ev, speak)
                    excerpts = r
            mems = []
            if self.db.get("memory_on", "1") == "1":
                mems = [m["text"] for m in memory.retrieve(self.db, self.member["id"], text or "", self.cfg["memory"]["retrieve_k"])]
            summary = self.db.conv(self.conv).get("summary")
            system = prompts.build_system(self.fam, self.companion, self.mode, self.member["name"], mems, summary, excerpts)
            hist = [{"role": m["role"], "content": m["content"]} for m in self.db.msgs(self.conv)[-self.cfg["history_turns"] * 2:]]
            if greeting: hist.append({"role": "user", "content": prompts.greeting_instruction(self.member["name"])})
            messages = [{"role": "system", "content": system}] + hist
            if speak:
                tt = threading.Thread(target=self._tts_loop, args=(tq, ev), daemon=True); tt.start(); tts_handled = True
            limit = self.cfg["max_story_tokens"] if self.mode == "story" else self.cfg["max_reply_tokens"]
            full, buf = "", ""
            for d in self.llm.stream(messages, limit, self.cfg.get("temperature"), ev):
                if ev.is_set(): break
                full += d; b.chunk.emit(d)
                if speak:
                    parts, buf = split_sentences(buf + d)
                    for p in parts: tq.put(p)
            if speak and buf.strip() and not ev.is_set(): tq.put(buf.strip())
            mid = 0
            if full.strip():
                refs = json.dumps(sorted({e["page"] for e in excerpts})) if excerpts else None
                mid = self.db.add_msg(self.conv, "assistant", full, refs)
            if not ev.is_set():
                b.turn_done.emit(mid, full)
                if excerpts: b.sources.emit(sorted({e["page"] for e in excerpts}))
            u = self.llm.last_usage
            if u: self.db.log_usage("chat", u.get("prompt_tokens"), u.get("completion_tokens"))
            if self.conv: memory.maybe_summarize(self.db, self.llm, self.conv)
        except ApiError as e:
            b.notice.emit(friendly(e)); b.turn_done.emit(0, "")
        except Exception:
            log.exception("turn failed"); b.notice.emit("Something went wrong on my side. Please try again."); b.turn_done.emit(0, "")
        finally:
            if tt: tq.put(None)
            if speak and not tts_handled: b.tts_finished.emit()
            if not speak: b.state.emit("idle")
