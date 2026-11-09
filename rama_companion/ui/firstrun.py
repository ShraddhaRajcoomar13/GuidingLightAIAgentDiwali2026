from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget,
                               QMessageBox, QInputDialog, QApplication)
from PySide6.QtCore import Qt
from core import keystore
from providers.openai_common import validate_key

DISCLOSURE = ("Welcome.\n\nThis is a private companion inspired by the qualities of Rama and Hanuman. It is an AI, not a spiritual authority, "
              "and its voice is computer-generated.\n\nWhat stays on this computer: your conversations and memories.\n"
              "What is sent to OpenAI to make it work: the text you type, your spoken words while the microphone is on (not saved here), "
              "and the text it speaks aloud. There is no analytics or tracking.\n\nYou can review or delete conversations and memories any time under Settings, Privacy.")

def disclose(parent, db):
    if db.get("disclosed") == "1": return
    QMessageBox.information(parent, "Before we begin", DISCLOSURE)
    db.put("disclosed", "1")

def ask_for_key(parent, fid, engine=None):
    """Masked entry; the key is never displayed. Returns True if a key was saved."""
    text, ok = QInputDialog.getText(parent, "Activation", "Enter your activation code (API key):", QLineEdit.EchoMode.Password)
    key = (text or "").strip()
    if not ok or not key: return False
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try: res = validate_key(key)
    finally: QApplication.restoreOverrideCursor()
    if res == "auth":
        QMessageBox.warning(parent, "Not accepted", "That code was not accepted. Please check it and try again."); return False
    if res == "network":
        if QMessageBox.question(parent, "No connection", "I couldn't check the code because there is no internet. Save it anyway?") != QMessageBox.StandardButton.Yes:
            return False
    try:
        keystore.set_key(fid, key)
    except Exception:
        QMessageBox.critical(parent, "Could not save", "Windows would not let me store the code securely. Please contact whoever set this up."); return False
    if engine: engine.set_key(key)
    return True

def _add_member(parent, db):
    name, ok = QInputDialog.getText(parent, "Who is this?", "Your first name:")
    if not ok or not name.strip(): return None
    pin, ok2 = QInputDialog.getText(parent, "Optional PIN", "Optional PIN so others can't open your chats (leave empty for none):", QLineEdit.EchoMode.Password)
    return db.add_member(name, pin.strip() if ok2 and pin.strip() else None)

def _pin_ok(parent, db, m):
    if not m.get("has_pin"): return True
    for _ in range(3):
        pin, ok = QInputDialog.getText(parent, "PIN", f"PIN for {m['name']}:", QLineEdit.EchoMode.Password)
        if not ok: return False
        if db.check_pin(m["id"], pin): return True
        QMessageBox.warning(parent, "PIN", "That PIN doesn't match.")
    return False

class MemberDialog(QDialog):
    def __init__(self, parent, db):
        super().__init__(parent); self.db = db; self.chosen = None
        self.setWindowTitle("Who is here?"); self.setMinimumWidth(340)
        v = QVBoxLayout(self); v.addWidget(QLabel("Who is here this evening?"))
        self.lst = QListWidget(); v.addWidget(self.lst)
        row = QHBoxLayout(); b1 = QPushButton("Continue"); b1.setObjectName("gold"); b2 = QPushButton("Add someone new"); b2.setObjectName("ghost")
        row.addWidget(b2); row.addWidget(b1); v.addLayout(row)
        b1.clicked.connect(self.go); b2.clicked.connect(self.add); self.lst.itemDoubleClicked.connect(lambda _: self.go()); self.fill()
    def fill(self):
        self.lst.clear(); self.ms = self.db.members()
        for m in self.ms: self.lst.addItem(m["name"] + ("  🔒" if m["has_pin"] else ""))
        if self.ms: self.lst.setCurrentRow(0)
    def go(self):
        i = self.lst.currentRow()
        if i < 0: return
        m = self.ms[i]
        if _pin_ok(self, self.db, m): self.chosen = m; self.accept()
    def add(self):
        if _add_member(self, self.db): self.fill()

def choose_member(parent, db):
    ms = db.members()
    if not ms:
        return _add_member(parent, db)
    if len(ms) == 1 and not ms[0]["has_pin"]:
        return ms[0]
    d = MemberDialog(parent, db)
    return d.chosen if d.exec() and d.chosen else None
