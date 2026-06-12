import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

# Cloud mode detection
CLOUD_MODE = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))

if CLOUD_MODE:
    DATA_DIR = BASE_DIR
else:
    if os.environ.get("DEMERGE_PACKAGED") == "1":
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        DATA_DIR = base / "com.demerge.app"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    else:
        DATA_DIR = BASE_DIR


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Demerge")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")

    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")

    # Local mode paths
    STORAGE_PATH: Path = DATA_DIR / os.getenv("STORAGE_PATH", "./storage")
    DATABASE_PATH: Path = DATA_DIR / os.getenv("DATABASE_PATH", "./hr_documents.db")
    RAW_PATH: Path = STORAGE_PATH / "raw"
    MERGED_PATH: Path = STORAGE_PATH / "merged"
    METADATA_PATH: Path = STORAGE_PATH / "metadata"

    # Supabase config
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_STORAGE_BUCKET: str = os.getenv("SUPABASE_STORAGE_BUCKET", "documents")

    # Backend URL for frontend API calls (Vercel → Railway)
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

    REQUIRED_DOCUMENTS: list = os.getenv(
        "REQUIRED_DOCUMENTS",
        "offer_letter,nda,employment_contract"
    ).split(",")

    OPTIONAL_DOCUMENTS: list = os.getenv(
        "OPTIONAL_DOCUMENTS",
        "job_description,company_policy"
    ).split(",")

    ALL_DOCUMENT_TYPES: dict = {
        "offer_letter": "Offer Letter",
        "nda": "NDA (Non-Disclosure Agreement)",
        "employment_contract": "Employment Contract",
        "job_description": "Job Description",
        "company_policy": "Company Policy"
    }

    PLATFORMS: dict = {
        "privyid": "PrivyID",
        "docusign": "DocuSign",
        "adobe_sign": "Adobe Sign",
        "manual": "Manual Signature",
        "other": "Other Platform"
    }


settings = Settings()

# Create local dirs if not in cloud mode
if not CLOUD_MODE:
    settings.RAW_PATH.mkdir(parents=True, exist_ok=True)
    settings.MERGED_PATH.mkdir(parents=True, exist_ok=True)
    settings.METADATA_PATH.mkdir(parents=True, exist_ok=True)
