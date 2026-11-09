"""Developer tool.  python tools/set_family.py new <id> | use <id> | key <id>"""
import json, shutil, sys, getpass
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def main():
    if len(sys.argv) < 3: print(__doc__); return 1
    cmd, fid = sys.argv[1], sys.argv[2]
    fam = ROOT / "config" / "families" / f"{fid}.json"
    if cmd == "new":
        if fam.exists(): print("Already exists:", fam); return 1
        d = json.loads((ROOT / "config" / "families" / "family_demo.json").read_text(encoding="utf-8"))
        d["family_id"] = fid; d["display_name"] = fid
        fam.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8"); print("Created", fam, "- now edit it."); return 0
    if cmd == "use":
        if not fam.exists(): print("No such family file:", fam); return 1
        p = ROOT / "config" / "app_config.json"; c = json.loads(p.read_text(encoding="utf-8")); c["family_id"] = fid
        p.write_text(json.dumps(c, indent=2), encoding="utf-8")
        print(f"Active family = {fid}. Only config/families/{fid}.json is bundled into the build."); return 0
    if cmd == "key":
        from core import keystore
        k = getpass.getpass("API key (hidden): ").strip()
        if k: keystore.set_key(fid, k); print("Stored in Windows Credential Manager for", fid)
        return 0
    print(__doc__); return 1

if __name__ == "__main__": sys.exit(main())
