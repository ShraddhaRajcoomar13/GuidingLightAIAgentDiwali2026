import os, sys, json
from pathlib import Path

APP_NAME = "RamaCompanion"

def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent

def user_root() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".local" / "share")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

def family_dir(fid: str) -> Path:
    p = user_root() / fid
    (p / "logs").mkdir(parents=True, exist_ok=True)
    return p

def load_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default

def app_config() -> dict:
    return load_json(app_dir() / "config" / "app_config.json", {}) or {}

def family_config(fid: str) -> dict:
    return load_json(app_dir() / "config" / "families" / f"{fid}.json", {}) or {}

def asset(name: str) -> Path:
    """User override folder (%APPDATA%/RamaCompanion/assets) wins over bundled assets."""
    o = user_root() / "assets" / name
    return o if o.exists() else app_dir() / "assets" / name

def ramayana_db() -> Path:
    return app_dir() / "data" / "ramayana.db"
