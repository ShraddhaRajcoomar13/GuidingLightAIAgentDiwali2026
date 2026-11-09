import json, re
EXTRACT = """You maintain a small long-term memory for a family companion app. From the conversation, extract at most {n} durable, useful, NON-SENSITIVE facts worth remembering for future friendly conversations: stable preferences, recurring topics, names of family members or pets the person mentions, ongoing events (e.g. an upcoming exam), interests.
DO NOT store: health or medical details, finances, abuse, self-harm, legal trouble, passwords or ID numbers, intimate details, anything the person asked not to be remembered, or one-off passing remarks.
Return JSON only: {{"memories":[{{"category":"preference|topic|person|event|interest","text":"short third-person fact","importance":3,"scope":"member|family"}}]}}. importance is 1-5. If nothing qualifies return {{"memories":[]}}."""

def _tokens(text):
    return list(dict.fromkeys(re.findall(r"[a-z']{4,}", (text or "").lower())))[:12]

def retrieve(db, member_id, query, k=6):
    hits = []
    toks = _tokens(query)
    if toks:
        try:
            if db.fts:
                match = " OR ".join('"%s"' % t.replace('"', "") for t in toks)
                hits = db.q("""SELECT m.* FROM memories_fts f JOIN memories m ON m.id=f.rowid
                    WHERE memories_fts MATCH ? AND (m.member_id=? OR m.member_id IS NULL) ORDER BY bm25(memories_fts) LIMIT 4""", (match, member_id))
            else:
                like = " OR ".join("text LIKE ?" for _ in toks)
                hits = db.q(f"SELECT * FROM memories WHERE (member_id=? OR member_id IS NULL) AND ({like}) LIMIT 4", (member_id, *[f"%{t}%" for t in toks]))
        except Exception:
            hits = []
    base = db.q("SELECT * FROM memories WHERE member_id=? OR member_id IS NULL ORDER BY importance DESC, last_used_at DESC LIMIT ?", (member_id, k))
    out, seen = [], set()
    for r in hits + base:
        if r["id"] not in seen:
            seen.add(r["id"]); out.append(r)
        if len(out) >= k: break
    db.touch_mems([r["id"] for r in out])
    return out

def _norm(s): return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()

def extract(db, llm, conv_id, member_id, n=5):
    msgs = db.msgs(conv_id)
    if sum(1 for m in msgs if m["role"] == "user") < 2: return 0
    transcript = "\n".join(f"{m['role']}: {m['content'][:400]}" for m in msgs[-40:])
    raw = llm.complete([{"role": "system", "content": EXTRACT.format(n=n)}, {"role": "user", "content": transcript}], json_mode=True, max_tokens=500)
    try:
        items = json.loads(raw).get("memories", [])
    except Exception:
        return 0
    existing = [_norm(m["text"]) for m in db.mems(member_id)]
    added = 0
    for it in items[:n]:
        t = str(it.get("text", "")).strip()
        if len(t) < 6 or len(t) > 240: continue
        nt = _norm(t)
        if any(nt in e or e in nt for e in existing): continue
        scope = None if it.get("scope") == "family" else member_id
        imp = max(1, min(5, int(it.get("importance", 3) or 3)))
        db.add_mem(scope, str(it.get("category", "topic"))[:20], t, imp, conv_id)
        existing.append(nt); added += 1
    return added

def maybe_summarize(db, llm, conv_id, keep=20, step=12):
    msgs = db.msgs(conv_id); c = db.conv(conv_id)
    upto = c.get("summary_upto") or 0; target = len(msgs) - keep
    if target - upto < step: return
    chunk = "\n".join(f"{m['role']}: {m['content'][:500]}" for m in msgs[upto:target])
    prev = c.get("summary") or ""
    text = llm.complete([{"role": "system", "content": "Update the running summary of this conversation in under 120 words. Keep names, topics and unresolved threads. Plain text."},
                         {"role": "user", "content": f"Previous summary:\n{prev}\n\nNew exchanges:\n{chunk}"}], max_tokens=250)
    if text.strip(): db.set_summary(conv_id, text.strip(), target)
