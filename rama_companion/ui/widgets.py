import html, math
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QTextBrowser, QWidget
from core.paths import asset
from ui import styles

class AvatarLabel(QWidget):
    def __init__(self, size=150):
        super().__init__()
        self.setFixedSize(size, size)
        self.pm = None
        self.letter = "R"
        self.speaking = False
        self.ph = 0.0
        self.t = QTimer(self)
        self.t.timeout.connect(self._tick)
        self.t.start(70)

    def set_companion(self, name):
        self.letter = name[:1].upper()
        pm = QPixmap(str(asset(f"{name.lower()}.png")))
        self.pm = None if pm.isNull() else pm
        self.update()

    def set_speaking(self, b):
        self.speaking = b
        self.update()

    def _tick(self):
        if self.speaking:
            self.ph = (self.ph + 0.3) % 6.283
            self.update()

    def paintEvent(self, e):
        th = styles.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.width()
        m = 10
        a = (0.55 + 0.35 * math.sin(self.ph)) if self.speaking else 0.3
        c = QColor(th["accent"])
        c.setAlphaF(a)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(2, 2, s - 4, s - 4)
        r = QRectF(m, m, s - 2 * m, s - 2 * m)
        path = QPainterPath()
        path.addEllipse(r)
        p.setClipPath(path)
        if self.pm:
            sc = self.pm.scaled(int(r.width()), int(r.height()), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(int(r.x() - (sc.width() - r.width()) / 2), int(r.y() - (sc.height() - r.height()) / 2), sc)
        else:
            p.fillRect(r, QColor(th["primary"]))
            p.setPen(QColor(th["accent"]))
            f = QFont("Georgia", 40)
            p.setFont(f)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.letter)

def _bubble(role, text):
    th = styles.current()
    t = html.escape(text).replace("\n", "<br>")
    if role == "user":
        return (f'<table width="100%" cellspacing="6"><tr><td width="22%"></td><td align="right">'
                f'<table align="right" cellpadding="9" bgcolor="{th["bubble_user"]}"><tr><td>'
                f'<font color="{th["bubble_user_fg"]}">{t}</font></td></tr></table></td></tr></table>')
    return (f'<table width="100%" cellspacing="6"><tr><td align="left">'
            f'<table align="left" cellpadding="9" bgcolor="{th["bubble_bot"]}"><tr><td>'
            f'<font color="{th["fg"]}">{t}</font></td></tr></table></td><td width="22%"></td></tr></table>')

class ChatView(QTextBrowser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.live = None

    def clear_all(self):
        self.items, self.live = [], None
        self._render()

    def add(self, role, text):
        self.items.append((role, text))
        self._render()

    def begin_live(self):
        self.live = ""
        self._render()

    def append_live(self, d):
        if self.live is None:
            self.live = ""
        self.live += d
        self._render()

    def end_live(self):
        if self.live and self.live.strip():
            self.items.append(("assistant", self.live))
        self.live = None
        self._render()

    def _render(self):
        parts = [_bubble(r, t) for r, t in self.items]
        if self.live is not None:
            parts.append(_bubble("assistant", self.live or "…"))
        self.setHtml("".join(parts))
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())