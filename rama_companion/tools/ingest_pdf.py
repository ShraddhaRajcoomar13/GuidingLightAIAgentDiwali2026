"""python tools/ingest_pdf.py path/to/ramayana.pdf  [--title "Name"]   (uses OPENAI_API_KEY env var, or the active family's stored key)"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core import paths, keystore
from providers.openai_embed import OpenAIEmbedder
from rag.ingest import ingest

def main():
    if len(sys.argv) < 2: print(__doc__); return 1
    pdf = sys.argv[1]; title = sys.argv[sys.argv.index("--title") + 1] if "--title" in sys.argv else None
    cfg = paths.app_config(); key = keystore.get_key(cfg["family_id"])
    if not key: print("No key found. Set OPENAI_API_KEY or run: python tools/set_family.py key <family_id>"); return 1
    out = ROOT / "data" / "ramayana.db"
    try: ingest(pdf, out, OpenAIEmbedder(key, cfg["models"]["embed"]), title)
    except Exception as e: print("FAILED:", type(e).__name__, e); return 1
    return 0

if __name__ == "__main__": sys.exit(main())
