"""Offline logic test (no network, no GUI):  python tools/selftest.py"""
import sys, tempfile, os, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.db import DB
from core import memory, safety, prompts
from rag.ingest import chunk_page

def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: check.bad += 1
check.bad = 0

d = tempfile.mkdtemp(); db = DB(os.path.join(d, "f.db"), "fam_a")
m1 = db.add_member("Asha"); m2 = db.add_member("Ravi", "1234")
check("pin ok", db.check_pin(m2["id"], "1234")); check("pin bad", not db.check_pin(m2["id"], "0000"))
c = db.new_conv(m1["id"], "rama", "chat"); db.add_msg(c, "user", "hi"); db.add_msg(c, "assistant", "hello")
db.add_mem(m1["id"], "interest", "Asha loves classical dance practice", 4, c)
db.add_mem(m2["id"], "interest", "Ravi plays cricket on weekends", 3, c)
db.add_mem(None, "event", "The family is planning a Diwali gathering", 3, c)
got = [r["text"] for r in memory.retrieve(db, m1["id"], "my dance class today", 6)]
check("member memory retrieved", any("dance" in t for t in got))
check("other member memory isolated", not any("cricket" in t for t in got))
check("shared memory visible", any("Diwali" in t for t in got))
check("fts active", db.fts)
db.del_conv(c); check("delete conv removes derived memories", db.mems(m1["id"]) == [])
try: DB(os.path.join(d, "f.db"), "fam_b"); check("family mismatch blocked", False)
except RuntimeError: check("family mismatch blocked", True)
check("crisis detected", safety.check("I want to die") == "crisis"); check("normal text clean", safety.check("my day was fine") is None)
check("abuse detected", safety.check("he hits me") == "abuse")
ch = chunk_page("Sentence number one is here. " * 120); check("chunking", len(ch) > 3 and all(len(x) <= 900 for x in ch))
s = prompts.build_system({"system_prompt_additions": "FAMILYCTX", "preferences": {"language": "English"}}, "hanuman", "story", "Asha", ["likes dance"], "sum", [{"page": 7, "text": "xx"}])
check("prompt assembled", all(k in s for k in ("FAMILYCTX", "Hanuman", "[page 7]", "likes dance", "EXCERPTS")))
check("prompt never names organisation", "ISKCON" not in s.upper())
print("\nFAILURES:", check.bad); sys.exit(1 if check.bad else 0)
