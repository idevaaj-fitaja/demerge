from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sys
from app.config import settings, CLOUD_MODE
from app.api.documents import router as documents_router
from app.api.packages import router as packages_router
from app.models.database import db_health

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(documents_router)
app.include_router(packages_router)


@app.get("/health")
async def health_check():
    checks = {"status": "healthy", "mode": "cloud" if CLOUD_MODE else "local"}
    try:
        db_result = db_health()
        if db_result["ok"]:
            checks["database"] = "ok"
        else:
            checks["database"] = db_result
            checks["status"] = "degraded"
    except Exception as e:
        checks["status"] = "degraded"
        checks["database"] = str(e)
    return checks


@app.get("/config")
async def get_config():
    return {"app_name": settings.APP_NAME, "required_documents": settings.REQUIRED_DOCUMENTS, "optional_documents": settings.OPTIONAL_DOCUMENTS, "document_types": settings.ALL_DOCUMENT_TYPES, "platforms": settings.PLATFORMS}


if not CLOUD_MODE:
    FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
