import uvicorn
import sys
import os

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

from app.models.database import init_db
init_db()

from app.main import app
uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
