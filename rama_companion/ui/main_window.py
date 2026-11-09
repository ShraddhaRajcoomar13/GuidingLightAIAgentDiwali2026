from datetime import datetime
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
                               QStackedWidget, QComboBox, QMessageBox, QApplication)
from audio.player import Player
from audio.recorder import Recorder
from ui import firstrun
from ui.settings_view import SettingsDialog, ConversationsDialog, FeedbackDialog
from ui.story_view import StoryView
from ui.styles import qss
from ui.family_call import FamilyCallManager, FamilyCallRing, FamilyGatheringDialog
from ui.widgets import AvatarLabel, ChatView

STATES = {"idle": "", "listening": "Listening…", "transcribing": "Understanding…", "thinking": "Thinking…", "speaking": "Speaking…"}

class MainWindow(QMainWindow):
    def __init__(self, engine, db, cfg, fam):
        super().__init__()
        self.e, self.db, self.cfg, self.fam = engine, db, cfg, fam; self.fid = fam.get("family_id") or cfg["family_id"]
        self.in_call = False; self.tts_done = True; self.last_msg = 0; self.setWindowTitle("Evening Companion"); self.resize(560, 820)
        a = cfg["audio"]; self.rec = Recorder(a["silence_ms"], a["threshold"], a["max_seconds"])
        self.player = Player(int(db.get("volume", "90")) / 100)
        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root); outer = QVBoxLayout(root)

        # header
        h = QHBoxLayout(); self.title = QLabel(""); self.title.setObjectName("title"); h.addWidget(self.title, 1)
        self.who = QComboBox(); self.who.addItems(["Rama", "Hanuman"]); self.who.setCurrentText(self.e.companion.title()); h.addWidget(self.who)
        for txt, fn in (("History", self.open_history), ("Feedback", self.open_feedback), ("⚙", self.open_settings)):
            b = QPushButton(txt); b.setObjectName("ghost"); b.clicked.connect(fn); h.addWidget(b)
        outer.addLayout(h)
        self.notice = QLabel(""); self.notice.setObjectName("notice"); self.notice.setWordWrap(True); self.notice.hide(); outer.addWidget(self.notice)

        self.stack = QStackedWidget(); outer.addWidget(self.stack, 1)
        home = QWidget(); hv = QVBoxLayout(home); hv.setContentsMargins(0, 0, 0, 0)
        ar = QHBoxLayout(); ar.addStretch(); self.avatar = AvatarLabel(); ar.addWidget(self.avatar); ar.addStretch(); hv.addLayout(ar)
        self.status = QLabel(""); self.status.setObjectName("status"); self.status.setAlignment(Qt.AlignmentFlag.AlignCenter); hv.addWidget(self.status)
        self.chat = ChatView(); hv.addWidget(self.chat, 1)
        row = QHBoxLayout(); self.inp = QLineEdit(); self.inp.setPlaceholderText("Type a message…")
        self.mic = QPushButton("🎤"); self.mic.setObjectName("saffron"); send = QPushButton("➤"); send.setObjectName("gold")
        self.listen_btn = QPushButton("🔊"); self.listen_btn.setObjectName("ghost")
        self.stop_btn = QPushButton("⏹"); self.stop_btn.setObjectName("ghost")
        row.addWidget(self.inp, 1); row.addWidget(self.mic); row.addWidget(self.listen_btn); row.addWidget(self.stop_btn); row.addWidget(send); hv.addLayout(row)
        # bottom bars: normal and call
        self.bottom = QWidget(); bl = QHBoxLayout(self.bottom); bl.setContentsMargins(0, 0, 0, 0)
        c = QPushButton("📞  Evening Call"); c.setObjectName("gold"); s = QPushButton("📖  Ramayana Stories"); bl.addWidget(c); bl.addWidget(s); hv.addWidget(self.bottom)
        self.callbar = QWidget(); cl = QHBoxLayout(self.callbar); cl.setContentsMargins(0, 0, 0, 0)
        self.cmic = QPushButton("🎤 Tap to speak"); self.cmic.setObjectName("saffron"); it = QPushButton("✋ Interrupt"); it.setObjectName("ghost")
        end = QPushButton("🔴 End call"); end.setObjectName("danger"); cl.addWidget(self.cmic); cl.addWidget(it); cl.addWidget(end); self.callbar.hide(); hv.addWidget(self.callbar)
        self.stack.addWidget(home); self.story = StoryView(self); self.stack.addWidget(self.story); self.active = self.chat

        # wiring
        send.clicked.connect(self.send_text); self.inp.returnPressed.connect(self.send_text)
        self.mic.clicked.connect(self.toggle_mic)
        self.listen_btn.clicked.connect(self.read_aloud)
        self.stop_btn.clicked.connect(self.interrupt); self.cmic.clicked.connect(self.toggle_mic)
        c.clicked.connect(self.start_call); s.clicked.connect(self.enter_story); it.clicked.connect(self.interrupt); end.clicked.connect(self.end_call)
        self.who.currentTextChanged.connect(self.change_companion)
        b = self.e.bus
        b.chunk.connect(self.on_chunk); b.turn_done.connect(self.on_done); b.user_text.connect(lambda t: self.active.add("user", t))
        b.state.connect(self.set_state); b.notice.connect(self.show_notice); b.audio.connect(self.player.enqueue)
        b.tts_finished.connect(self.on_tts_finished); b.sources.connect(self.on_sources)
        self.player.started.connect(lambda: (self.avatar.set_speaking(True), self.set_state("speaking")))
        self.player.idle.connect(self.on_player_idle)
        self.rec.finished.connect(self.on_rec); self.rec.failed.connect(self.on_rec_failed)
        self.apply_settings()
        self.fc_manager = FamilyCallManager(self.db, self.cfg, self)
        self.fc_manager.triggered.connect(self.show_family_ring)
        self.reset_home()

    # ---- helpers
    def apply_settings(self):
        QApplication.instance().setStyleSheet(qss(int(self.db.get("font_pt", "13")), self.db.get("theme", "warm")))
        self.player.set_volume(int(self.db.get("volume", "90")) / 100); self.avatar.set_companion(self.e.companion)

    def reset_home(self):
        n = self.e.member["name"]; hr = datetime.now().hour
        g = "Good morning" if hr < 12 else "Good afternoon" if hr < 17 else "Good evening"
        self.title.setText(f"{self.e.companion.title()}'s Companion"); self.chat.clear_all()
        self.chat.add("assistant", f"{g}, {n}. I'm here whenever you'd like to talk. You can type below, tap the microphone, start an evening call, or open the Ramayana stories.")

    def show_notice(self, msg):
        self.notice.setText(msg); self.notice.show(); QTimer.singleShot(9000, self.notice.hide)

    def set_state(self, s):
        self.status.setText(STATES.get(s, "") if not (s == "idle" and self.in_call) else "Your turn. Tap the microphone.")
        self.story.sources.setText(self.story.sources.text() if s != "thinking" else "")

    def _speak_flag(self):
        if self.in_call: return True
        if self.e.mode == "story": return self.story.listen.isChecked()
        return self.db.get("speak_chat", "0") == "1"

    def _begin_turn(self):
        self.e.speak = self._speak_flag(); self.tts_done = not self.e.speak; self.player.stop()

    def _ready(self):
        from core import keystore
        if keystore.get_key(self.fid): return True
        return firstrun.ask_for_key(self, self.fid, self.e)

    # ---- engine signals
    def on_chunk(self, d): self.active.append_live(d)
    def on_done(self, mid, text):
        self.active.end_live(); self.last_msg = mid or self.last_msg
    def on_sources(self, pages):
        self.story.sources.setText("Sources: pages " + ", ".join(str(p) for p in pages))
    def on_tts_finished(self):
        self.tts_done = True
        if not self.player.busy: self.on_player_idle()
    def on_player_idle(self):
        self.avatar.set_speaking(False)
        if self.tts_done: self.set_state("idle")

    # ---- chat
    def send_text(self):
        t = self.inp.text().strip()
        if not t or not self._ready(): return
        self.inp.clear()
        if self.e.conv is None: self.e.start_conversation("chat")
        self.active.add("user", t); self._begin_turn(); self.e.submit(t)

    def read_aloud(self):
        if not self._ready(): return
        last_msg = next((t for r, t in reversed(self.chat.items) if r == "assistant"), "")
        if last_msg:
            self.player.stop()
            self.e.speak_text(last_msg)

    def change_companion(self, name):
        if self.in_call: self.end_call()
        self.e.end_conversation(); self.e.companion = name.lower(); self.db.put("companion", name.lower())
        self.apply_settings(); self.reset_home()

    # ---- voice
    def toggle_mic(self):
        if self.rec.active: self.rec.stop(); return
        if not self._ready(): return
        if self.db.get("mic_ok") != "1":
            if QMessageBox.question(self, "Use the microphone?",
                "When you tap the microphone, the app listens only until you stop speaking, and sends that speech to OpenAI to turn it into text. "
                "The recording is not saved on this computer. You can always type instead.") != QMessageBox.StandardButton.Yes: return
            self.db.put("mic_ok", "1")
        if self.e.conv is None: self.e.start_conversation("story" if self.stack.currentIndex() == 1 else "chat")
        self.player.stop(); self.e.interrupt()
        if self.rec.start():
            self.set_state("listening"); self.cmic.setText("⏹ Done speaking")

    def on_rec(self, wav):
        self.cmic.setText("🎤 Tap to speak")
        if not wav:
            self.show_notice("I didn't catch anything. Tap the microphone and try again, or type."); self.set_state("idle"); return
        self._begin_turn(); self.e.voice_turn(wav)

    def on_rec_failed(self, msg):
        self.cmic.setText("🎤 Tap to speak"); self.show_notice(msg); self.set_state("idle")

    def interrupt(self):
        self.rec.stop() if self.rec.active else None
        self.e.interrupt(); self.player.stop(); self.tts_done = True; self.active.end_live(); self.set_state("idle")

    # ---- call
    def start_call(self):
        if not self._ready(): return
        self.e.start_conversation("call"); self.in_call = True
        self.bottom.hide(); self.callbar.show(); self._begin_turn(); self.e.greet()

    def end_call(self):
        self.interrupt(); self.in_call = False; self.e.end_conversation()
        self.callbar.hide(); self.bottom.show(); self.set_state("idle")
        self.chat.add("assistant", "Our call has ended. Thank you for the time together.")

    # ---- story
    def enter_story(self):
        if not self._ready(): return
        self.e.start_conversation("story"); self.active = self.story.chat; self.stack.setCurrentIndex(1)
        if not self.story.chat.items:
            self.story.chat.add("assistant", "Choose a story above, or ask me about any character, event or teaching. I'll tell it from the Ramayana text I've been given, and I'll be clear about what is the text and what is my own telling.")

    def leave_story(self):
        self.interrupt(); self.e.end_conversation(); self.active = self.chat; self.stack.setCurrentIndex(0); self.story.chat.clear_all()

    def send_story(self, text):
        if not self._ready(): return
        if self.e.conv is None: self.e.start_conversation("story")
        self.story.chat.add("user", text); self._begin_turn(); self.e.submit(text)

    # ---- dialogs
    def show_family_ring(self):
        if self.in_call: return
        dlg = FamilyCallRing(self)
        if dlg.exec() and dlg.accepted_call: self.start_family_call()
    def start_family_call(self):
        if not self._ready(): return
        self.e.start_conversation("family")
        dur = int(self.db.get("fc_duration", self.cfg.get("family_call", {}).get("duration_minutes", 10)))
        FamilyGatheringDialog(self, dur).exec()
        self.e.end_conversation()
        self.active = self.chat
        self.reset_home()
    def open_settings(self): SettingsDialog(self).exec()
    def open_history(self): ConversationsDialog(self, self.db, self.e.member).exec()
    def open_feedback(self): FeedbackDialog(self, self.db, self.e.conv, self.last_msg).exec()

    def switch_member(self):
        self.interrupt(); self.e.end_conversation(); self.in_call = False; self.callbar.hide(); self.bottom.show()
        m = firstrun.choose_member(self, self.db)
        if m: self.e.member = m
        self.reset_home()

    def closeEvent(self, ev):
        self.rec.stop() if self.rec.active else None
        self.player.stop(); self.e.end_conversation(wait=True); ev.accept()
