import os
import hashlib
import json
import uuid
from pathlib import Path
from typing import Optional
from app.config import settings, CLOUD_MODE

if CLOUD_MODE:
    from supabase import create_client
    _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    _bucket = settings.SUPABASE_STORAGE_BUCKET


class StorageService:
    def store_raw(self, file_content: bytes, filename: str, employee_name: str) -> dict:
        safe_name = self._sanitize_name(employee_name)
        safe_filename = self._sanitize_filename(filename)
        file_hash = hashlib.md5(file_content).hexdigest()[:8]
        unique_filename = f"{file_hash}_{safe_filename}"
        storage_path = f"raw/{safe_name}/{unique_filename}"

        if CLOUD_MODE:
            _supabase.storage.from_(_bucket).upload(storage_path, file_content, {"content-type": "application/pdf"})
            return {
                "path": storage_path,
                "filename": unique_filename,
                "original_filename": filename,
                "file_size": len(file_content),
                "file_hash": file_hash
            }

        employee_dir = settings.RAW_PATH / safe_name
        employee_dir.mkdir(parents=True, exist_ok=True)
        file_path = employee_dir / unique_filename
        file_path.write_bytes(file_content)
        return {
            "path": str(file_path),
            "filename": unique_filename,
            "original_filename": filename,
            "file_size": len(file_content),
            "file_hash": file_hash
        }

    def store_merged(self, pdf_content: bytes, employee_name: str, filename: str) -> str:
        safe_name = self._sanitize_name(employee_name)
        storage_path = f"merged/{safe_name}/{filename}"

        if CLOUD_MODE:
            _supabase.storage.from_(_bucket).upload(storage_path, pdf_content, {"content-type": "application/pdf"})
            return storage_path

        employee_dir = settings.MERGED_PATH / safe_name
        employee_dir.mkdir(parents=True, exist_ok=True)
        file_path = employee_dir / filename
        file_path.write_bytes(pdf_content)
        return str(file_path)

    def read_file(self, storage_path: str) -> Optional[bytes]:
        if CLOUD_MODE:
            try:
                return _supabase.storage.from_(_bucket).download(storage_path)
            except Exception:
                return None
        p = Path(storage_path)
        if p.exists():
            return p.read_bytes()
        alt = settings.RAW_PATH / storage_path
        if alt.exists():
            return alt.read_bytes()
        alt2 = settings.MERGED_PATH / storage_path
        if alt2.exists():
            return alt2.read_bytes()
        return None

    def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> Optional[str]:
        if CLOUD_MODE:
            try:
                r = _supabase.storage.from_(_bucket).create_signed_url(storage_path, expires_in)
                return r["signedURL"]
            except Exception:
                return None
        return storage_path

    def get_public_url(self, storage_path: str) -> Optional[str]:
        if CLOUD_MODE:
            try:
                return _supabase.storage.from_(_bucket).get_public_url(storage_path)
            except Exception:
                return None
        return storage_path

    def delete_file(self, storage_path: str):
        if CLOUD_MODE:
            try:
                _supabase.storage.from_(_bucket).remove([storage_path])
            except Exception:
                pass
            return
        p = Path(storage_path)
        if p.exists():
            p.unlink()

    def delete_employee_files(self, employee_name: str):
        safe_name = self._sanitize_name(employee_name)
        if CLOUD_MODE:
            for prefix in ("raw", "merged"):
                try:
                    files = _supabase.storage.from_(_bucket).list(f"{prefix}/{safe_name}")
                    paths = [f["name"] for f in files]
                    if paths:
                        _supabase.storage.from_(_bucket).remove([f"{prefix}/{safe_name}/{p}" for p in paths])
                except Exception:
                    pass
            return
        import shutil
        for d in [settings.RAW_PATH / safe_name, settings.MERGED_PATH / safe_name]:
            if d.exists():
                shutil.rmtree(d)

    def list_employee_files(self, employee_name: str, prefix: str = "raw") -> list:
        safe_name = self._sanitize_name(employee_name)
        if CLOUD_MODE:
            try:
                return _supabase.storage.from_(_bucket).list(f"{prefix}/{safe_name}")
            except Exception:
                return []
        p = (settings.RAW_PATH if prefix == "raw" else settings.MERGED_PATH) / safe_name
        if p.exists():
            return [f.name for f in p.iterdir() if f.is_file()]
        return []

    def _sanitize_name(self, name: str) -> str:
        return "".join(c if c.isalnum() or c in "._-" else "_" for c in name).lower()[:50]

    def _sanitize_filename(self, filename: str) -> str:
        filename = os.path.basename(filename)
        return "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
