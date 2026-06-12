from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
import sys
import os
from app.config import settings, CLOUD_MODE
from app.api.documents import router as documents_router
from app.api.packages import router as packages_router
from app.models.database import db_health

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

API_KEY = os.getenv("API_KEY", "")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

request_counts = defaultdict(list)


def check_rate_limit(ip: str):
    now = datetime.now()
    window = now - timedelta(minutes=1)
    request_counts[ip] = [t for t in request_counts[ip] if t > window]
    if len(request_counts[ip]) >= RATE_LIMIT_PER_MINUTE:
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})
    request_counts[ip].append(now)
    return None


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    if path in ("/health", "/docs", "/openapi.json"):
        return await call_next(request)

    ip = request.client.host if request.client else "unknown"
    rate_response = check_rate_limit(ip)
    if rate_response:
        return rate_response

    if API_KEY:
        auth_header = request.headers.get("authorization", "")
        api_key_header = request.headers.get("x-api-key", "")

        valid = False
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token == API_KEY:
                valid = True
        elif api_key_header:
            if api_key_header == API_KEY:
                valid = True

        if not valid:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

    return await call_next(request)


cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860, log_level="info")
