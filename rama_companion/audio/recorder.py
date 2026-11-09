import io, time, wave
import numpy as np
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices

F = QAudioFormat.SampleFormat

def _to_i16(raw, fmt):
    sf, ch = fmt.sampleFormat(), fmt.channelCount()
    if sf == F.Int16: a = np.frombuffer(raw, dtype=np.int16)
    elif sf == F.Float: a = (np.frombuffer(raw, dtype=np.float32) * 32767).clip(-32768, 32767).astype(np.int16)
    elif sf == F.Int32: a = (np.frombuffer(raw, dtype=np.int32) >> 16).astype(np.int16)
    elif sf == F.UInt8: a = (np.frombuffer(raw, dtype=np.uint8).astype(np.int16) - 128) << 8
    else: a = np.zeros(0, dtype=np.int16)
    if ch > 1:
        a = a[: len(a) // ch * ch].reshape(-1, ch)[:, 0]
    return a

class Recorder(QObject):
    """Explicit, click-started recording. Audio stays in RAM; emits WAV bytes (b'' if no speech)."""
    finished = Signal(bytes)
    failed = Signal(str)

    def __init__(self, silence_ms=1500, threshold=450, max_s=60, no_speech_s=10):
        super().__init__()
        self.silence_s = silence_ms / 1000; self.th = threshold; self.max_s = max_s; self.no_speech_s = no_speech_s
        self.active = False; self._src = None; self._io = None
        self._t = QTimer(self); self._t.setInterval(50); self._t.timeout.connect(self._poll)

    def start(self):
        dev = QMediaDevices.defaultAudioInput()
        if dev.isNull():
            self.failed.emit("I can't find a microphone. You can type instead."); return False
        fmt = QAudioFormat(); fmt.setSampleRate(16000); fmt.setChannelCount(1); fmt.setSampleFormat(F.Int16)
        if not dev.isFormatSupported(fmt): fmt = dev.preferredFormat()
        self._fmt = fmt; self._bps = max(1, fmt.bytesPerSample()) * max(1, fmt.channelCount())
        self._src = QAudioSource(dev, fmt); self._io = self._src.start()
        if self._io is None:
            self.failed.emit("The microphone couldn't start. Check Windows Settings, Privacy, Microphone."); return False
        self._chunks, self._tail = [], b""
        self._t0 = self._last_voice = time.monotonic(); self._spoke = False; self._got = False
        self.active = True; self._t.start()
        return True

    def _poll(self):
        raw = self._tail + bytes(self._io.readAll().data())
        n = len(raw) // self._bps * self._bps
        raw, self._tail = raw[:n], raw[n:]
        now = time.monotonic()
        if raw:
            self._got = True
            a = _to_i16(raw, self._fmt); self._chunks.append(a)
            rms = float(np.sqrt(np.mean(a.astype(np.float32) ** 2))) if len(a) else 0.0
            if rms > self.th: self._spoke = True; self._last_voice = now
        el = now - self._t0
        if not self._got and el > 2.5:
            self._halt(); self.failed.emit("I'm not hearing any sound from the microphone. Check Windows Settings, Privacy, Microphone."); return
        if self._spoke and now - self._last_voice > self.silence_s: self.stop()
        elif el > self.max_s: self.stop()
        elif not self._spoke and el > self.no_speech_s: self._halt(); self.finished.emit(b"")

    def _halt(self):
        self._t.stop(); self.active = False
        if self._src: self._src.stop(); self._src = None

    def stop(self):
        if not self.active: return
        self._halt()
        if not self._spoke or not self._chunks: self.finished.emit(b""); return
        a = np.concatenate(self._chunks)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(self._fmt.sampleRate()); w.writeframes(a.tobytes())
        self._chunks = []
        self.finished.emit(buf.getvalue())
