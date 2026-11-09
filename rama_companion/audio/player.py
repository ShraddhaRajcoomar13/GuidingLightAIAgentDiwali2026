import os, tempfile
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

class Player(QObject):
    started = Signal()
    idle = Signal()

    def __init__(self, volume=1.0):
        super().__init__()
        self._p = QMediaPlayer(); self._o = QAudioOutput(); self._p.setAudioOutput(self._o); self._o.setVolume(volume)
        self._q, self._cur, self.busy = [], None, False
        self._p.mediaStatusChanged.connect(self._status)
        self._p.errorOccurred.connect(lambda *a: self._next())

    def set_volume(self, v): self._o.setVolume(max(0.0, min(1.0, v)))

    def enqueue(self, wav):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".wav"); f.write(wav); f.close()
        self._q.append(f.name)
        if not self.busy: self._next()

    def _drop(self):
        if self._cur:
            self._p.setSource(QUrl())
            try: os.remove(self._cur)
            except OSError: pass
            self._cur = None

    def _next(self):
        self._drop()
        if not self._q:
            was = self.busy; self.busy = False
            if was: self.idle.emit()
            return
        self._cur = self._q.pop(0); self.busy = True
        self._p.setSource(QUrl.fromLocalFile(self._cur)); self._p.play(); self.started.emit()

    def _status(self, st):
        if st == QMediaPlayer.MediaStatus.EndOfMedia: self._next()

    def stop(self):
        self._p.stop()
        for f in self._q:
            try: os.remove(f)
            except OSError: pass
        self._q.clear(); self._drop()
        was = self.busy; self.busy = False
        if was: self.idle.emit()
