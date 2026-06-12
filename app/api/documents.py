from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from typing import List
from pydantic import BaseModel
from app.services.processor import DocumentProcessor
from app.services.storage import StorageService
from app.services.signature_detector import detect_signature_from_bytes
from app.models.database import get_documents_by_employee, get_all_documents, delete_document
from app.config import settings, CLOUD_MODE
import asyncio
import hashlib
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/documents", tags=["documents"])
processor = DocumentProcessor()
storage = StorageService()

PDF_MAGIC = b'%PDF'


@router.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...), employee_name: str = Form(...)):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        if not employee_name or not employee_name.strip():
            raise HTTPException(status_code=400, detail="Employee name is required")

        employee_name = employee_name.strip()[:100]
        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        file_data = []

        for file in files:
            if file.content_type and file.content_type != "application/pdf":
                raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}. Only PDF files are allowed.")

            content = await file.read()

            if len(content) > max_size:
                raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds {settings.MAX_FILE_SIZE_MB}MB limit")
            if content[:4] != PDF_MAGIC:
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a valid PDF")

            file_data.append({"content": content, "filename": file.filename})

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, processor.process_upload, file_data, employee_name)

        if not result["success"]:
            return {"success": False, "message": result["message"], "unsigned_files": result.get("unsigned_files", []), "signed_count": result.get("signed_count", 0), "total_count": result.get("total_count", 0)}

        return {"success": True, "message": result["message"], "employee_name": result["employee_name"], "documents_processed": result["documents_processed"], "package_id": result.get("package_id")}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {type(e).__name__}: {str(e)}")


# ── Pre-signed upload (for Vercel: file bypasses backend) ────────

class UploadURLRequest(BaseModel):
    employee_name: str
    filenames: List[str]


@router.post("/upload-url")
async def get_upload_urls(payload: UploadURLRequest):
    if not CLOUD_MODE:
        raise HTTPException(status_code=400, detail="Pre-signed upload only available in cloud mode")
    if not payload.employee_name or not payload.employee_name.strip():
        raise HTTPException(status_code=400, detail="Employee name is required")
    if not payload.filenames:
        raise HTTPException(status_code=400, detail="No filenames provided")

    employee_name = payload.employee_name.strip()[:100]
    safe_name = storage._sanitize_name(employee_name)
    results = []

    try:
        for filename in payload.filenames:
            safe_filename = storage._sanitize_filename(filename)
            file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
            unique_filename = f"{file_hash}_{safe_filename}"
            storage_path = f"raw/{safe_name}/{unique_filename}"

            from supabase import create_client
            sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            r = sb.storage.from_(settings.SUPABASE_STORAGE_BUCKET).create_signed_upload_url(storage_path)

            results.append({
                "filename": filename,
                "storage_path": storage_path,
                "signed_url": r.get("signedURL") or r.get("signedUrl"),
                "token": r.get("token", ""),
            })

        return {"success": True, "employee_name": employee_name, "uploads": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create upload URLs: {str(e)}")


class ProcessRequest(BaseModel):
    employee_name: str
    files: List[dict]


@router.post("/process")
async def process_uploaded_files(payload: ProcessRequest):
    if not payload.employee_name or not payload.employee_name.strip():
        raise HTTPException(status_code=400, detail="Employee name is required")
    if not payload.files:
        raise HTTPException(status_code=400, detail="No files to process")

    employee_name = payload.employee_name.strip()[:100]
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from supabase import create_client
        sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        bucket = settings.SUPABASE_STORAGE_BUCKET

        def download_file(file_info):
            storage_path = file_info.get("storage_path", "")
            filename = file_info.get("filename", "unknown.pdf")
            try:
                file_bytes = sb.storage.from_(bucket).download(storage_path)
            except Exception:
                return None
            if len(file_bytes) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                return None
            if file_bytes[:4] != PDF_MAGIC:
                return None
            file_hash = hashlib.md5(file_bytes).hexdigest()[:8]
            return {
                "path": storage_path,
                "filename": f"{file_hash}_{storage._sanitize_filename(filename)}",
                "original_filename": filename,
                "file_size": len(file_bytes),
                "file_hash": file_hash,
                "content": file_bytes,
            }

        with ThreadPoolExecutor(max_workers=min(len(payload.files), 8)) as pool:
            futures = {pool.submit(download_file, fi): fi for fi in payload.files}
            stored_files = [f.result() for f in as_completed(futures) if f.result()]

        if not stored_files:
            return {"success": False, "message": "No valid PDF files found", "unsigned_files": [], "signed_count": 0, "total_count": len(payload.files)}

        def check_signature(file_info):
            return file_info["path"], detect_signature_from_bytes(file_info["content"])

        with ThreadPoolExecutor(max_workers=min(len(stored_files), 8)) as pool:
            sig_futures = {pool.submit(check_signature, fi): fi for fi in stored_files}
            sig_results = {}
            for f in as_completed(sig_futures):
                path, result = f.result()
                sig_results[path] = result

        unsigned_files = []
        signed_files = []

        for file_info in stored_files:
            sig_result = sig_results[file_info["path"]]
            if sig_result["is_signed"]:
                signed_files.append(file_info)
            else:
                unsigned_files.append(file_info["original_filename"])

        if unsigned_files:
            for file_info in stored_files:
                storage.delete_file(file_info["path"])
            return {"success": False, "message": f"Cannot upload: {len(unsigned_files)} file(s) not signed: {', '.join(unsigned_files)}", "unsigned_files": unsigned_files, "signed_count": len(signed_files), "total_count": len(stored_files)}

        from app.models.database import insert_document, insert_package, get_package_by_employee, update_package, get_documents_by_employee

        for file_info in stored_files:
            sig_result = sig_results[file_info["path"]]
            doc = {
                "id": str(uuid.uuid4()),
                "employee_id": employee_name.lower().replace(" ", "_"),
                "employee_name": employee_name,
                "original_filename": file_info["original_filename"],
                "stored_path": file_info["path"],
                "file_size": file_info["file_size"],
                "file_hash": file_info["file_hash"],
                "platform": sig_result.get("platform"),
                "doc_type": None,
                "classification_confidence": None,
                "title": None,
                "signers": sig_result.get("signers", []),
                "document_date": sig_result.get("signed_date"),
                "status": "signed",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "validation": {"is_valid": True, "issues": [], "score": 100}
            }
            insert_document(doc)

        all_docs = get_documents_by_employee(employee_name)
        package = processor._create_or_update_package(employee_name, all_docs)

        merged_path = None
        if len(all_docs) >= 1:
            from app.services.merger import PDFMerger
            merger = PDFMerger()
            merge_result = merger.merge_documents(all_docs, employee_name, storage)
            if merge_result["success"]:
                merged_path = storage.store_merged(merge_result["pdf_content"], employee_name, merge_result["filename"])
                update_package(package["id"], {"merged_pdf_path": merged_path, "status": "merged"})

        return {
            "success": True,
            "message": f"{len(stored_files)} signed files processed & merged for {employee_name}",
            "package_id": package["id"],
            "employee_name": employee_name,
            "documents_processed": len(stored_files),
            "merged_path": merged_path,
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {type(e).__name__}: {str(e)}"}


# ── Auto-cleanup: delete files older than TTL ───────────────────

CLEANUP_TTL_HOURS = int(__import__("os").getenv("CLEANUP_TTL_HOURS", "12"))


@router.post("/cleanup")
async def cleanup_expired():
    if not CLOUD_MODE:
        return {"success": True, "message": "Cleanup skipped (local mode)"}

    try:
        from datetime import timedelta
        from app.models.database import _get_supabase, delete_employee_all, get_all_packages

        sb = _get_supabase()
        cutoff = (datetime.utcnow() - timedelta(hours=CLEANUP_TTL_HOURS)).isoformat()

        r = sb.table("documents").select("*").lt("created_at", cutoff).execute()
        expired_docs = r.data or []

        if not expired_docs:
            return {"success": True, "message": "No expired files", "deleted": 0}

        deleted_paths = []
        for doc in expired_docs:
            path = doc.get("stored_path")
            if path:
                try:
                    sb.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([path])
                    deleted_paths.append(path)
                except Exception:
                    pass

        expired_employees = list({d["employee_name"] for d in expired_docs})
        for emp in expired_employees:
            try:
                sb.table("documents").delete().eq("employee_name", emp).execute()
                sb.table("employee_packages").delete().eq("employee_name", emp).execute()
            except Exception:
                pass

        return {
            "success": True,
            "message": f"Cleaned up {len(expired_docs)} files from {len(expired_employees)} employee(s)",
            "deleted": len(expired_docs),
            "storage_deleted": len(deleted_paths),
        }
    except Exception as e:
        return {"success": False, "message": f"Cleanup error: {str(e)}"}


# ── GET routes (after POST routes to avoid path conflict) ───────

@router.get("/")
async def list_documents():
    try:
        return get_all_documents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_name}")
async def get_employee_documents(employee_name: str):
    try:
        return get_documents_by_employee(employee_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}")
async def delete_doc(doc_id: str):
    try:
        delete_document(doc_id)
        return {"success": True, "message": "Document deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_name}/summary")
async def get_employee_summary(employee_name: str):
    try:
        return processor.get_employee_summary(employee_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
