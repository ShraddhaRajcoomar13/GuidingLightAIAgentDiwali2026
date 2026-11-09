import sqlite3, time, hashlib, secrets
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY, name TEXT NOT NULL, pin_salt TEXT, pin_hash TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS conversations(id INTEGER PRIMARY KEY, member_id INTEGER, companion TEXT, mode TEXT,
  started_at REAL, ended_at REAL, summary TEXT, summary_upto INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, conv_id INTEGER, role TEXT, content TEXT, created_at REAL, source_refs TEXT);
CREATE INDEX IF NOT EXISTS ix_msg_conv ON messages(conv_id);
CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY, member_id INTEGER, category TEXT, text TEXT,
  importance INTEGER DEFAULT 3, source_conv INTEGER, created_at REAL, last_used_at REAL);
CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY, message_id INTEGER, conv_id INTEGER, area TEXT, rating INTEGER, comment TEXT, created_at REAL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS usage_log(id INTEGER PRIMARY KEY, kind TEXT, tokens_in INTEGER, tokens_out INTEGER, ts REAL);
"""
FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(text, content='memories', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS mem_ai AFTER INSERT ON memories BEGIN INSERT INTO memories_fts(rowid,text) VALUES (new.id,new.text); END;
CREATE TRIGGER IF NOT EXISTS mem_ad AFTER DELETE ON memories BEGIN INSERT INTO memories_fts(memories_fts,rowid,text) VALUES('delete',old.id,old.text); END;
"""

class DB:
    def __init__(self, path, family_id):
        self.path = str(path); self.family_id = family_id; self.fts = True
        with self._c() as c:
            c.executescript(SCHEMA)
            try:
                c.executescript(FTS)
            except sqlite3.OperationalError:
                self.fts = False
            r = c.execute("SELECT value FROM meta WHERE key='family_id'").fetchone()
            if r and r["value"] != family_id:
                raise RuntimeError("This database belongs to a different family.")
            c.execute("INSERT OR IGNORE INTO meta VALUES('family_id',?)", (family_id,))

    @contextmanager
    def _c(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def q(self, sql, a=()):
        with self._c() as c:
            return [dict(r) for r in c.execute(sql, a).fetchall()]

    def x(self, sql, a=()):
        with self._c() as c:
            return c.execute(sql, a).lastrowid

    # settings
    def get(self, key, default=None):
        r = self.q("SELECT value FROM settings WHERE key=?", (key,))
        return r[0]["value"] if r else default

    def put(self, key, value):
        self.x("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    # members
    @staticmethod
    def _h(pin, salt):
        return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 100_000).hex()

    def members(self):
        return self.q("SELECT id,name,(pin_hash IS NOT NULL) AS has_pin FROM members ORDER BY id")

    def add_member(self, name, pin=None):
        salt = secrets.token_hex(8) if pin else None
        h = self._h(pin, salt) if pin else None
        mid = self.x("INSERT INTO members(name,pin_salt,pin_hash,created_at) VALUES(?,?,?,?)", (name.strip(), salt, h, time.time()))
        return {"id": mid, "name": name.strip(), "has_pin": bool(pin)}

    def check_pin(self, mid, pin):
        r = self.q("SELECT pin_salt,pin_hash FROM members WHERE id=?", (mid,))
        if not r or not r[0]["pin_hash"]:
            return True
        return secrets.compare_digest(self._h(pin or "", r[0]["pin_salt"]), r[0]["pin_hash"])

    # conversations
    def new_conv(self, member_id, companion, mode):
        return self.x("INSERT INTO conversations(member_id,companion,mode,started_at) VALUES(?,?,?,?)", (member_id, companion, mode, time.time()))

    def conv(self, cid):
        r = self.q("SELECT * FROM conversations WHERE id=?", (cid,))
        return r[0] if r else {}

    def end_conv(self, cid):
        self.x("UPDATE conversations SET ended_at=? WHERE id=?", (time.time(), cid))

    def set_summary(self, cid, text, upto):
        self.x("UPDATE conversations SET summary=?, summary_upto=? WHERE id=?", (text, upto, cid))

    def add_msg(self, cid, role, content, refs=None):
        return self.x("INSERT INTO messages(conv_id,role,content,created_at,source_refs) VALUES(?,?,?,?,?)", (cid, role, content, time.time(), refs))

    def msgs(self, cid):
        return self.q("SELECT * FROM messages WHERE conv_id=? ORDER BY id", (cid,))

    def convs(self, member_id):
        return self.q("""SELECT c.*, (SELECT COUNT(*) FROM messages WHERE conv_id=c.id) AS n,
            (SELECT content FROM messages WHERE conv_id=c.id AND role='user' ORDER BY id LIMIT 1) AS first
            FROM conversations c WHERE member_id=? ORDER BY started_at DESC""", (member_id,))

    def del_conv(self, cid):
        with self._c() as c:
            c.execute("DELETE FROM memories WHERE source_conv=?", (cid,))
            c.execute("DELETE FROM messages WHERE conv_id=?", (cid,))
            c.execute("DELETE FROM feedback WHERE conv_id=?", (cid,))
            c.execute("DELETE FROM conversations WHERE id=?", (cid,))

    def del_all_convs(self, member_id):
        for c in self.q("SELECT id FROM conversations WHERE member_id=?", (member_id,)):
            self.del_conv(c["id"])

    # memories
    def add_mem(self, member_id, category, text, importance, source_conv):
        now = time.time()
        return self.x("INSERT INTO memories(member_id,category,text,importance,source_conv,created_at,last_used_at) VALUES(?,?,?,?,?,?,?)",
                      (member_id, category, text, importance, source_conv, now, now))

    def mems(self, member_id):
        return self.q("SELECT * FROM memories WHERE member_id=? OR member_id IS NULL ORDER BY created_at DESC", (member_id,))

    def del_mem(self, mid):
        self.x("DELETE FROM memories WHERE id=?", (mid,))

    def clear_mems(self, member_id, include_shared=False):
        if include_shared:
            self.x("DELETE FROM memories WHERE member_id=? OR member_id IS NULL", (member_id,))
        else:
            self.x("DELETE FROM memories WHERE member_id=?", (member_id,))

    def touch_mems(self, ids):
        for i in ids:
            self.x("UPDATE memories SET last_used_at=? WHERE id=?", (time.time(), i))

    # feedback / usage
    def add_feedback(self, conv_id, message_id, area, rating, comment):
        self.x("INSERT INTO feedback(message_id,conv_id,area,rating,comment,created_at) VALUES(?,?,?,?,?,?)",
               (message_id, conv_id, area, rating, comment, time.time()))

    def log_usage(self, kind, tin, tout):
        self.x("INSERT INTO usage_log(kind,tokens_in,tokens_out,ts) VALUES(?,?,?,?)", (kind, tin or 0, tout or 0, time.time()))
