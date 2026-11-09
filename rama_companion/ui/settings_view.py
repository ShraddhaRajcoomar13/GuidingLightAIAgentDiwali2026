import time, json
from PySide6.QtCore import Qt, QUrl, QTime
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QWidget, QSpinBox, QCheckBox,
                               QComboBox, QSlider, QListWidget, QTextBrowser, QMessageBox, QTextEdit, QTimeEdit, QFormLayout)
from core import keystore
from ui import firstrun
from ui.styles import THEMES

VOICE_CHOICES = ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer", "verse"]
AREAS = ["Conversation quality", "Voice quality", "Storytelling", "Spiritual relevance", "General experience"]

def _fmt(ts): return time.strftime("%d %b %Y %H:%M", time.localtime(ts or 0))

class ConversationsDialog(QDialog):
    def __init__(self, parent, db, member):
        super().__init__(parent); self.db, self.m = db, member; self.setWindowTitle("My conversations"); self.resize(760, 460)
        h = QHBoxLayout(self); left = QVBoxLayout(); self.lst = QListWidget(); left.addWidget(self.lst)
        r = QHBoxLayout(); d1 = QPushButton("Delete selected"); d1.setObjectName("danger"); d2 = QPushButton("Delete all"); d2.setObjectName("danger")
        r.addWidget(d1); r.addWidget(d2); left.addLayout(r); h.addLayout(left, 2)
        self.view = QTextBrowser(); h.addWidget(self.view, 3)
        self.lst.currentRowChanged.connect(self.show_conv); d1.clicked.connect(self.del_one); d2.clicked.connect(self.del_all); self.fill()
    def fill(self):
        self.lst.clear(); self.rows = [c for c in self.db.convs(self.m["id"]) if c["n"]]
        for c in self.rows:
            snip = (c["first"] or "")[:40]
            self.lst.addItem(f"{_fmt(c['started_at'])} · {c['mode']} · {c['companion'].title()}\n{snip}")
        self.view.clear()
    def show_conv(self, i):
        if i < 0 or i >= len(self.rows): return
        out = []
        for m in self.db.msgs(self.rows[i]["id"]):
            who = "You" if m["role"] == "user" else self.rows[i]["companion"].title()
            out.append(f"<p><b>{who}:</b> {m['content']}</p>".replace("\n", "<br>"))
        self.view.setHtml("".join(out))
    def del_one(self):
        i = self.lst.currentRow()
        if i >= 0 and QMessageBox.question(self, "Delete", "Delete this conversation (and memories learned from it)?") == QMessageBox.StandardButton.Yes:
            self.db.del_conv(self.rows[i]["id"]); self.fill()
    def del_all(self):
        if QMessageBox.question(self, "Delete all", "Delete ALL of your conversations? This cannot be undone.") == QMessageBox.StandardButton.Yes:
            self.db.del_all_convs(self.m["id"]); self.fill()

class MemoriesDialog(QDialog):
    def __init__(self, parent, db, member):
        super().__init__(parent); self.db, self.m = db, member; self.setWindowTitle("What I remember"); self.resize(560, 420)
        v = QVBoxLayout(self); v.addWidget(QLabel("Things remembered to make our conversations feel continuous. Delete anything you like."))
        self.lst = QListWidget(); v.addWidget(self.lst)
        r = QHBoxLayout(); d1 = QPushButton("Delete selected"); d1.setObjectName("danger"); d2 = QPushButton("Clear all my memory"); d2.setObjectName("danger")
        r.addWidget(d1); r.addWidget(d2); v.addLayout(r); d1.clicked.connect(self.del_one); d2.clicked.connect(self.clear); self.fill()
    def fill(self):
        self.lst.clear(); self.rows = self.db.mems(self.m["id"])
        for r in self.rows: self.lst.addItem(f"[{r['category']}{', shared' if r['member_id'] is None else ''}] {r['text']}")
    def del_one(self):
        i = self.lst.currentRow()
        if i >= 0: self.db.del_mem(self.rows[i]["id"]); self.fill()
    def clear(self):
        if QMessageBox.question(self, "Clear memory", "Clear everything remembered about you, including family-shared items?") == QMessageBox.StandardButton.Yes:
            self.db.clear_mems(self.m["id"], include_shared=True); self.fill()

class FeedbackDialog(QDialog):
    def __init__(self, parent, db, conv_id, msg_id):
        super().__init__(parent); self.db, self.cid, self.mid = db, conv_id, msg_id; self.setWindowTitle("Feedback"); self.setMinimumWidth(380)
        v = QVBoxLayout(self); v.addWidget(QLabel("How was it? This stays on this computer."))
        self.area = QComboBox(); self.area.addItems(AREAS); v.addWidget(self.area)
        self.rate = QComboBox(); self.rate.addItems(["5 - Wonderful", "4 - Good", "3 - Okay", "2 - Not great", "1 - Poor"]); v.addWidget(self.rate)
        self.txt = QTextEdit(); self.txt.setPlaceholderText("Anything you'd like to add (optional)"); self.txt.setFixedHeight(90); v.addWidget(self.txt)
        b = QPushButton("Save feedback"); b.setObjectName("gold"); b.clicked.connect(self.save); v.addWidget(b)
    def save(self):
        self.db.add_feedback(self.cid, self.mid, self.area.currentText(), 5 - self.rate.currentIndex(), self.txt.toPlainText().strip())
        QMessageBox.information(self, "Thank you", "Saved. Thank you."); self.accept()

class SettingsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win); self.w = win; self.db = win.db; self.e = win.e
        self.setWindowTitle("Settings"); self.resize(520, 480)
        v = QVBoxLayout(self); tabs = QTabWidget(); v.addWidget(tabs)
        
        # General
        g = QWidget(); gl = QVBoxLayout(g)
        gl.addWidget(QLabel("Text size")); self.size = QSpinBox(); self.size.setRange(10, 24); self.size.setValue(int(self.db.get("font_pt", "13"))); gl.addWidget(self.size)
        
        gl.addWidget(QLabel("Theme")); self.theme = QComboBox()
        for key, meta in THEMES.items(): self.theme.addItem(meta["label"], key)
        idx = self.theme.findData(self.db.get("theme", "warm")); self.theme.setCurrentIndex(max(0, idx)); gl.addWidget(self.theme)
        
        self.spk = QCheckBox("Read replies aloud in normal chat"); self.spk.setChecked(self.db.get("speak_chat", "0") == "1"); gl.addWidget(self.spk)
        sw = QPushButton("Switch person"); sw.setObjectName("ghost"); sw.clicked.connect(lambda: (self.accept(), win.switch_member())); gl.addWidget(sw)
        gl.addStretch(); tabs.addTab(g, "General")
        
        # Family Call
        f = QWidget(); fl = QFormLayout(f)
        self.fc_enable = QCheckBox("Enable daily Family Gathering ring")
        self.fc_enable.setChecked(self.db.get("fc_enabled", "false").lower() == "true")
        fl.addRow(self.fc_enable)
        
        self.fc_start = QTimeEdit()
        self.fc_start.setDisplayFormat("HH:mm")
        t_str = self.db.get("fc_window_start", "19:30")
        self.fc_start.setTime(QTime(int(t_str.split(":")[0]), int(t_str.split(":")[1])))
        fl.addRow("Window Start Time:", self.fc_start)
        
        self.fc_end = QTimeEdit()
        self.fc_end.setDisplayFormat("HH:mm")
        t_str = self.db.get("fc_window_end", "19:40")
        self.fc_end.setTime(QTime(int(t_str.split(":")[0]), int(t_str.split(":")[1])))
        fl.addRow("Window End Time:", self.fc_end)
        
        self.fc_dur = QSpinBox(); self.fc_dur.setRange(5, 60); self.fc_dur.setSuffix(" minutes")
        self.fc_dur.setValue(int(self.db.get("fc_duration", "10")))
        fl.addRow("Duration:", self.fc_dur)
        
        # --- NEW TEST BUTTONS ---
        test_layout = QHBoxLayout()
        btn_chime = QPushButton("Test Chime"); btn_chime.setObjectName("ghost")
        btn_ring = QPushButton("Test Ring Now"); btn_ring.setObjectName("gold")
        btn_chime.clicked.connect(self.test_chime)
        btn_ring.clicked.connect(self.test_ring)
        test_layout.addWidget(btn_chime); test_layout.addWidget(btn_ring)
        fl.addRow(test_layout)
        # ------------------------

        fl.addRow(QLabel("The app will gently chime at a random moment inside this window."))
        tabs.addTab(f, "Family Call")
        
        # Voice
        vo = QWidget(); vl = QVBoxLayout(vo)
        vl.addWidget(QLabel(f"Voice for {self.e.companion.title()}")); self.voice = QComboBox(); self.voice.addItems(VOICE_CHOICES)
        self.voice.setCurrentText(self.e.voice); vl.addWidget(self.voice)
        pv = QPushButton("Preview voice"); pv.setObjectName("ghost"); pv.clicked.connect(self.preview); vl.addWidget(pv)
        vl.addWidget(QLabel("Volume")); self.vol = QSlider(Qt.Orientation.Horizontal); self.vol.setRange(0, 100); self.vol.setValue(int(self.db.get("volume", "90"))); vl.addWidget(self.vol)
        vl.addWidget(QLabel("The voice is computer-generated. Speech is processed by OpenAI and recordings are not saved.")); vl.addStretch(); tabs.addTab(vo, "Voice")
        
        # Privacy
        p = QWidget(); pl = QVBoxLayout(p)
        self.mem = QCheckBox("Remember useful things between conversations"); self.mem.setChecked(self.db.get("memory_on", "1") == "1"); pl.addWidget(self.mem)
        for txt, fn in (("View my conversations…", self.conv), ("View what I remember…", self.mems)):
            b = QPushButton(txt); b.setObjectName("ghost"); b.clicked.connect(fn); pl.addWidget(b)
        pl.addWidget(QLabel("Stays on this computer: conversations and memories.\nSent to OpenAI: typed text, spoken words while the microphone is on, and text to be spoken.\nNothing is recorded in the background. No analytics.")); pl.addStretch(); tabs.addTab(p, "Privacy")
        
        # Account
        a = QWidget(); al = QVBoxLayout(a)
        self.status = QLabel(); al.addWidget(self.status); self._status()
        b1 = QPushButton("Replace API key…"); b1.setObjectName("ghost"); b1.clicked.connect(self.key); al.addWidget(b1)
        b2 = QPushButton("Open OpenAI billing page"); b2.setObjectName("ghost")
        b2.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(win.cfg["billing_url"]))); al.addWidget(b2); al.addStretch(); tabs.addTab(a, "Account")
        
        ok = QPushButton("Save"); ok.setObjectName("gold"); ok.clicked.connect(self.save); v.addWidget(ok)

    def _status(self): self.status.setText("API key: saved securely ✓" if keystore.get_key(self.w.fid) else "API key: not set")
    def key(self): firstrun.ask_for_key(self, self.w.fid, self.e); self._status()
    def conv(self): ConversationsDialog(self, self.db, self.e.member).exec()
    def mems(self): MemoriesDialog(self, self.db, self.e.member).exec()
    def preview(self): self.db.put(f"voice_{self.e.companion}", self.voice.currentText()); self.e.preview_voice()
    def test_chime(self):
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PySide6.QtCore import QUrl
        from core.paths import asset
        path = asset("chime.wav")
        if path.exists():
            self._test_player = QMediaPlayer()
            self._test_audio = QAudioOutput()
            self._test_player.setAudioOutput(self._test_audio)
            self._test_player.setSource(QUrl.fromLocalFile(str(path)))
            self._test_player.play()
        else:
            QMessageBox.warning(self, "Missing", "chime.wav not found in assets folder.")
            
    def test_ring(self):
        self.save() # Save current settings first
        self.accept() # Close settings
        from ui.family_call import FamilyCallRing
        dlg = FamilyCallRing(self.w)
        if dlg.exec() and dlg.accepted_call:
            self.w.start_family_call()
            
    def save(self):
        self.db.put("font_pt", self.size.value()); self.db.put("speak_chat", int(self.spk.isChecked()))
        self.db.put("theme", self.theme.currentData() or "warm")
        self.db.put(f"voice_{self.e.companion}", self.voice.currentText()); self.db.put("volume", self.vol.value())
        self.db.put("memory_on", int(self.mem.isChecked()))
        
        # Family Call saves
        self.db.put("fc_enabled", str(self.fc_enable.isChecked()).lower())
        self.db.put("fc_window_start", self.fc_start.time().toString("HH:mm"))
        self.db.put("fc_window_end", self.fc_end.time().toString("HH:mm"))
        self.db.put("fc_duration", self.fc_dur.value())
        
        self.db.x("DELETE FROM settings WHERE key IN ('fc_sched', 'fc_sched_date', 'fc_done_date', 'fc_skipped_date')")
        
        # Tell the call manager to load the new settings right away
        if hasattr(self.w, "fc_manager"):
            self.w.fc_manager.reload()

        self.w.apply_settings(); self.accept()