import random
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal, QTimer, Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
from core.paths import asset
from ui.widgets import AvatarLabel, ChatView
from ui.styles import THEMES

class FamilyCallManager(QObject):
    triggered = Signal()
    def __init__(self, db, cfg, parent=None):
        super().__init__(parent)
        self.db = db; self.cfg = cfg.get("family_call", {}) or {}
        self.timer = QTimer(self); self.timer.setInterval(30_000); self.timer.timeout.connect(self._check)
        self.reload()

    def reload(self):
        # Read from DB, fallback to config JSON
        self.enabled = self.db.get("fc_enabled", str(self.cfg.get("enabled", False))).lower() == "true"
        start_str = self.db.get("fc_window_start", self.cfg.get("window_start", "19:30"))
        end_str = self.db.get("fc_window_end", self.cfg.get("window_end", "19:40"))
        
        self.start_h, self.start_m = self._parse(start_str)
        self.end_h, self.end_m = self._parse(end_str)
        
        if self.enabled:
            self.timer.start()
        else:
            self.timer.stop()
            self.db.put("fc_done_date", "")
            self.db.put("fc_sched", "")

    def _parse(self, s):
        try:
            h, m = str(s).split(":"); return int(h), int(m)
        except Exception:
            return 19, 30

    def _parse(self, s):
        try:
            h, m = str(s).split(":"); return int(h), int(m)
        except Exception:
            return 19, 30

    def _check(self):
        if not self.enabled: return
        now = datetime.now(); today = now.date().isoformat()
        if self.db.get("fc_done_date") == today or self.db.get("fc_skipped_date") == today: return
        
        sched = self.db.get("fc_sched")
        sched_date = self.db.get("fc_sched_date")
        
        if sched_date != today or not sched:
            start = now.replace(hour=self.start_h, minute=self.start_m, second=0, microsecond=0)
            end = now.replace(hour=self.end_h, minute=self.end_m, second=0, microsecond=0)
            if end <= start: 
                end += timedelta(days=1) # Handles midnight crossover
            t = start + timedelta(seconds=random.uniform(0, (end - start).total_seconds()))
            self.db.put("fc_sched", t.isoformat()); self.db.put("fc_sched_date", today)
            sched = t.isoformat()
            
        try: sched_dt = datetime.fromisoformat(sched)
        except Exception: return
        
        if now >= sched_dt:
            self.db.put("fc_done_date", today)
            self.triggered.emit()

class FamilyCallRing(QDialog):
    def __init__(self, win):
        super().__init__(win); self.win = win; self.accepted_call = False
        self.setObjectName("ring_dialog")
        self.setWindowTitle("Family Gathering"); self.setMinimumWidth(420)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("🪔  Family Gathering Time"))
        v.addWidget(QLabel("The evening window is open. Would the family like to gather for a few minutes together?"))
        row = QHBoxLayout(); j = QPushButton("Join now"); j.setObjectName("gold")
        s = QPushButton("In 10 minutes"); s.setObjectName("ghost"); k = QPushButton("Not today"); k.setObjectName("ghost")
        row.addWidget(s); row.addWidget(k); row.addWidget(j); v.addLayout(row)
        j.clicked.connect(self._join); s.clicked.connect(self._snooze); k.clicked.connect(self._skip)
        self._player = None
        chime = asset("chime.wav")
        if chime.exists():
            try:
                self._player = QMediaPlayer(); self._ao = QAudioOutput()
                self._player.setAudioOutput(self._ao); self._ao.setVolume(0.7)
                self._player.setSource(QUrl.fromLocalFile(str(chime)))
                self._player.setLoops(QMediaPlayer.Loops.Infinite)
                self._player.play()
            except Exception: self._player = None
    def _stop_audio(self):
        if self._player:
            try: self._player.stop()
            except Exception: pass
    def _join(self): self._stop_audio(); self.accepted_call = True; self.accept()
    def _snooze(self):
        self._stop_audio()
        try:
            t = datetime.now() + timedelta(minutes=10)
            self.win.db.put("fc_sched", t.isoformat())
            self.win.db.put("fc_sched_date", t.date().isoformat())
            self.win.db.x("DELETE FROM settings WHERE key='fc_done_date'")
        except Exception: pass
        self.reject()
    def _skip(self):
        self._stop_audio()
        self.win.db.put("fc_skipped_date", datetime.now().date().isoformat())
        self.reject()
    def closeEvent(self, ev): self._stop_audio(); ev.accept()

class FamilyGatheringDialog(QDialog):
    def __init__(self, win, duration_min=10):
        super().__init__(win); self.win = win; self.duration = duration_min
        self.setWindowTitle("Family Gathering"); self.resize(640, 780)
        self.setModal(True)
        v = QVBoxLayout(self)
        head = QLabel(f"🪔  Family Gathering — {duration_min} minutes")
        head.setObjectName("title"); head.setAlignment(Qt.AlignmentFlag.AlignCenter); v.addWidget(head)
        sub = QLabel("Gather round. Speak one at a time, and let others be heard.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter); v.addWidget(sub)
        av = QHBoxLayout(); av.addStretch(); self.avatar = AvatarLabel(120)
        self.avatar.set_companion(win.e.companion); av.addWidget(self.avatar); av.addStretch(); v.addLayout(av)
        self.chat = ChatView(); v.addWidget(self.chat, 1)
        self.timer_lbl = QLabel(f"{duration_min}:00 remaining"); self.timer_lbl.setObjectName("status")
        self.timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); v.addWidget(self.timer_lbl)
        row = QHBoxLayout(); self.mic = QPushButton("🎤 Tap to speak"); self.mic.setObjectName("saffron")
        end = QPushButton("End gathering"); end.setObjectName("danger")
        row.addWidget(self.mic); row.addWidget(end); v.addLayout(row)
        self.mic.clicked.connect(self._toggle_mic); end.clicked.connect(self._end)
        win.active = self.chat
        win._begin_turn(); win.e.speak = True
        win.e.greet()
        self.remaining = duration_min * 60
        self.tick = QTimer(self); self.tick.setInterval(1000); self.tick.timeout.connect(self._on_tick); self.tick.start()

    def _toggle_mic(self):
        self.win.toggle_mic()
        self.mic.setText("⏹ Done speaking" if self.win.rec.active else "🎤 Tap to speak")

    def _on_tick(self):
        if self.remaining <= 0:
            self._end(); return
        self.remaining -= 1
        m, s = divmod(self.remaining, 60)
        self.timer_lbl.setText(f"{m}:{s:02d} remaining")
        if self.remaining == 30:
            self.win.e.submit("(The gathering has about thirty seconds left. Please close with a short, heartfelt blessing for the family.)")

    def _end(self):
        self.tick.stop()
        try:
            if self.win.rec.active: self.win.rec.stop()
            self.win.e.interrupt(); self.win.player.stop()
        except Exception: pass
        self.accept()

    def closeEvent(self, ev):
        try: self.win.active = self.win.chat
        except Exception: pass
        ev.accept()
