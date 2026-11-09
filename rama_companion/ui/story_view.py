from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QCheckBox, QGridLayout
from ui.widgets import ChatView

class StoryView(QWidget):
    def __init__(self, win):
        super().__init__(); self.w = win
        v = QVBoxLayout(self)
        top = QHBoxLayout(); back = QPushButton("← Back"); back.setObjectName("ghost"); back.clicked.connect(win.leave_story)
        t = QLabel("Ramayana Stories"); t.setObjectName("title"); top.addWidget(back); top.addWidget(t); top.addStretch()
        self.listen = QCheckBox("Read aloud"); self.listen.setChecked(True); top.addWidget(self.listen)
        stop = QPushButton("⏹ Stop"); stop.setObjectName("saffron"); stop.clicked.connect(win.interrupt); top.addWidget(stop); v.addLayout(top)
        grid = QGridLayout()
        for i, c in enumerate(win.cfg["story_chips"]):
            b = QPushButton(c); b.setObjectName("ghost"); b.clicked.connect(lambda _=False, s=c: win.send_story(f"Tell me the story: {s}")); grid.addWidget(b, i // 3, i % 3)
        v.addLayout(grid)
        self.chat = ChatView(); v.addWidget(self.chat, 1)
        self.sources = QLabel(""); self.sources.setObjectName("sources"); v.addWidget(self.sources)
        row = QHBoxLayout(); self.inp = QLineEdit(); self.inp.setPlaceholderText("Ask about a character, event or teaching…")
        self.mic = QPushButton("🎤"); self.mic.setObjectName("saffron"); send = QPushButton("➤"); send.setObjectName("gold")
        row.addWidget(self.inp, 1); row.addWidget(self.mic); row.addWidget(send); v.addLayout(row)
        self.mic.clicked.connect(win.toggle_mic); send.clicked.connect(self.go); self.inp.returnPressed.connect(self.go)
    def go(self):
        t = self.inp.text().strip()
        if t: self.inp.clear(); self.w.send_story(t)
