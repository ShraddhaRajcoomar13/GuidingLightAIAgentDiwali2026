import sys, logging
from logging.handlers import RotatingFileHandler
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from core import paths, keystore
from core.db import DB
from core.engine import Engine
from ui import firstrun
from ui.main_window import MainWindow
from ui.styles import qss

def main():
    app = QApplication(sys.argv); app.setApplicationName("Evening Companion")
    cfg = paths.app_config(); fid = cfg.get("family_id")
    if not fid or not paths.family_config(fid):
        QMessageBox.critical(None, "Setup problem", "This copy hasn't been configured for a family. Please contact whoever gave it to you."); return 1
    fam = paths.family_config(fid); fam.setdefault("family_id", fid)
    fdir = paths.family_dir(fid)
    h = RotatingFileHandler(fdir / "logs" / "app.log", maxBytes=500_000, backupCount=2, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[h], format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    sys.excepthook = lambda t, v, tb: logging.getLogger("rama").error("uncaught", exc_info=(t, v, tb))
    ic = paths.asset("icon.ico")
    if ic.exists(): app.setWindowIcon(QIcon(str(ic)))
    try:
        db = DB(fdir / "family.db", fid)
    except Exception as e:
        logging.getLogger("rama").error("db open failed: %s", type(e).__name__)
        QMessageBox.critical(None, "Could not open your data", "The saved data couldn't be opened. Nothing was deleted. Please contact whoever set this up."); return 1
    app.setStyleSheet(qss(int(db.get("font_pt", "13")), db.get("theme", "warm")))
    firstrun.disclose(None, db)
    key = keystore.get_key(fid, fam)
    eng = Engine(db, cfg, fam, key)
    if not key: firstrun.ask_for_key(None, fid, eng)
    m = firstrun.choose_member(None, db)
    if not m: return 0
    eng.member = m; eng.companion = db.get("companion") or fam.get("default_companion", "rama")
    win = MainWindow(eng, db, cfg, fam); win.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
