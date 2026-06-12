import sys
import os
from pathlib import Path

_app_path = Path(__file__).resolve()
_in_app_bundle = False
for parent in _app_path.parents:
    if parent.suffix == ".app" and (parent / "Contents" / "MacOS").exists():
        _in_app_bundle = True
        break

if _in_app_bundle or getattr(sys, 'frozen', False):
    sys.frozen = True
    os.chdir(Path(__file__).resolve().parent)

from app.models.database import init_db, _get_conn
from app.models.database import CLOUD_MODE
from app.main import app

if __name__ == "__main__":
    init_db()

    import uvicorn
    import atexit

    if not CLOUD_MODE:
        @atexit.register
        def _shutdown():
            try:
                conn = _get_conn()
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.close()
            except Exception:
                pass

    uvicorn.run(app, host="127.0.0.1", port=8000)
