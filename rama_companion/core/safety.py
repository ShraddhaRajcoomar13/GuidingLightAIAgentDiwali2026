import re

_CRISIS = [r"\bkill myself\b", r"\bsuicid", r"\bend my life\b", r"\bwant to die\b", r"\bdon'?t want to (live|be alive)\b",
           r"\bhurt myself\b", r"\bself[- ]?harm", r"\bcut myself\b", r"\bbetter off (dead|without me)\b", r"\btake my (own )?life\b"]
_ABUSE = [r"\b(hits|beats|hurts|threatens) me\b", r"\babus(e|es|ing|ed) me\b", r"\bafraid (of|for) my (life|safety)\b",
          r"\bdomestic violence\b", r"\bmolest", r"\btouch(es|ed) me\b.*\b(wrong|inappropriate)"]

def check(text):
    t = (text or "").lower()
    if any(re.search(p, t) for p in _CRISIS): return "crisis"
    if any(re.search(p, t) for p in _ABUSE): return "abuse"
    return None

def reply(kind, helplines):
    lines = ""
    if helplines:
        lines = " You can reach: " + "; ".join(f"{h.get('name','')} {h.get('number','')}".strip() for h in helplines) + "."
    if kind == "crisis":
        return ("I'm really glad you told me, and I'm taking it seriously. You don't have to carry this alone. "
                "Please reach out right now to someone close to you, or to a crisis line or emergency services in your area." + lines +
                " I'm here to keep talking with you, but the most important thing is that you are safe. Are you safe right now?")
    return ("I'm so sorry this is happening. Your safety matters more than anything. If you are in danger right now, "
            "please contact emergency services or go to someone you trust nearby." + lines +
            " I'm here to listen, and a trusted adult, a doctor or a counsellor can help you take the next steps.")
