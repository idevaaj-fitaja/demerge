from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response
from app.models.database import get_all_packages, get_package_by_employee, update_package, get_documents_by_employee, insert_audit_log, update_document, delete_employee_all, resolve_employee_name
from app.services.merger import PDFMerger
from app.services.storage import StorageService
from app.services.processor import DocumentProcessor
from app.services.signature_detector import detect_signature_from_bytes, detect_signature
from app.config import settings, CLOUD_MODE, DATA_DIR
from pathlib import Path
from urllib.parse import unquote

router = APIRouter(prefix="/api/packages", tags=["packages"])
merger = PDFMerger()
storage = StorageService()
processor = DocumentProcessor()


def resolve_path(file_path: str) -> Path:
    p = Path(file_path)
    if p.exists():
        return p
    resolved = DATA_DIR / file_path
    if resolved.exists():
        return resolved
    resolved = Path(settings.RAW_PATH) / file_path
    if resolved.exists():
        return resolved
    return p


def validate_path(file_path: str, allowed_dir: Path) -> bool:
    try:
        resolved = Path(file_path).resolve()
        return resolved.is_relative_to(allowed_dir.resolve())
    except (ValueError, OSError):
        return False


@router.get("/")
async def list_packages():
    try:
        return get_all_packages()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/with-status")
async def list_packages_with_status():
    try:
        packages = get_all_packages()
        for pkg in packages:
            emp_name = pkg.get("employee_name")
            documents = get_documents_by_employee(emp_name)
            if not documents:
                pkg["signature_status"] = "no_documents"
                pkg["signed_count"] = 0
                pkg["total_count"] = 0
                continue
            total_count = len(documents)
            signed_count = sum(1 for d in documents if d.get("status") == "signed")
            if signed_count == total_count:
                pkg["signature_status"] = "all_signed"
            elif signed_count > 0:
                pkg["signature_status"] = "partially_signed"
            else:
                pkg["signature_status"] = "not_signed"
            pkg["signed_count"] = signed_count
            pkg["total_count"] = total_count
        return packages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_name}")
async def get_package(employee_name: str):
    try:
        return processor.get_employee_summary(employee_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{employee_name}/merge")
async def merge_documents(employee_name: str):
    try:
        employee_name = resolve_employee_name(unquote(employee_name)) or unquote(employee_name)
        documents = get_documents_by_employee(employee_name)
        if not documents:
            raise HTTPException(status_code=404, detail="No documents found for this employee")

        unsigned_docs = []
        for doc in documents:
            if doc.get("status") != "signed":
                unsigned_docs.append(doc.get("original_filename", "Unknown"))

        if unsigned_docs:
            raise HTTPException(status_code=400, detail=f"Cannot merge: {len(unsigned_docs)} unsigned document(s): {', '.join(unsigned_docs)}")

        merge_result = merger.merge_documents(documents, employee_name, storage)
        if not merge_result["success"]:
            raise HTTPException(status_code=500, detail="Merge failed")

        merged_path = storage.store_merged(merge_result["pdf_content"], employee_name, merge_result["filename"])
        package = get_package_by_employee(employee_name)
        if package:
            update_package(package["id"], {"merged_pdf_path": merged_path, "status": "merged"})

        insert_audit_log({"package_id": package["id"] if package else None, "action": "merge", "status": "success", "details": {"employee": employee_name, "pages": merge_result["page_count"]}})

        return {"success": True, "message": f"Documents merged successfully for {employee_name}", "merged_path": merged_path, "filename": merge_result["filename"], "page_count": merge_result["page_count"], "bookmarks": merge_result["bookmarks"]}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{employee_name}")
async def delete_package(employee_name: str):
    try:
        resolved = resolve_employee_name(unquote(employee_name)) or employee_name
        storage.delete_employee_files(resolved)
        delete_employee_all(resolved)
        return {"success": True, "message": f"All data for {resolved} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_name}/download")
async def download_merged(employee_name: str):
    try:
        employee_name = unquote(employee_name)
        package = get_package_by_employee(employee_name)
        if not package:
            raise HTTPException(status_code=404, detail="No package found")

        merged_path = package.get("merged_pdf_path")
        if not merged_path:
            raise HTTPException(status_code=404, detail="Merged PDF not found. Please merge first.")

        if CLOUD_MODE:
            signed_url = storage.get_signed_url(merged_path)
            if signed_url:
                return RedirectResponse(url=signed_url)
            raise HTTPException(status_code=500, detail="Failed to generate download URL")

        resolved_merged = resolve_path(merged_path)
        if not resolved_merged or not resolved_merged.exists():
            raise HTTPException(status_code=404, detail="Merged PDF not found")
        if not validate_path(str(resolved_merged), settings.MERGED_PATH):
            raise HTTPException(status_code=403, detail="Access denied")

        return FileResponse(path=str(resolved_merged), filename=resolved_merged.name, media_type="application/pdf")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_name}/download/{doc_id}")
async def download_document(employee_name: str, doc_id: str):
    try:
        employee_name = unquote(employee_name)
        documents = get_documents_by_employee(employee_name)
        doc = next((d for d in documents if d["id"] == doc_id), None)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        stored_path = doc.get("stored_path")
        if not stored_path:
            raise HTTPException(status_code=404, detail="File not found")

        if CLOUD_MODE:
            signed_url = storage.get_signed_url(stored_path)
            if signed_url:
                return RedirectResponse(url=signed_url)
            raise HTTPException(status_code=500, detail="Failed to generate download URL")

        resolved = resolve_path(stored_path)
        if not resolved or not resolved.exists():
            raise HTTPException(status_code=404, detail="File not found")
        if not validate_path(str(resolved), settings.RAW_PATH):
            raise HTTPException(status_code=403, detail="Access denied")

        return FileResponse(path=str(resolved), filename=doc.get("original_filename", "document.pdf"), media_type="application/pdf")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_name}/signatures")
async def check_signatures(employee_name: str):
    try:
        employee_name = resolve_employee_name(unquote(employee_name)) or unquote(employee_name)
        documents = get_documents_by_employee(employee_name)
        if not documents:
            raise HTTPException(status_code=404, detail="No documents found")

        results = []
        all_signed = True
        for doc in documents:
            sig_result = {
                "is_signed": doc.get("status") == "signed",
                "signature_type": "digital" if doc.get("status") == "signed" else "none",
                "signers": doc.get("signers", []) or [],
                "platform": doc.get("platform") or "unknown",
                "signed_date": doc.get("document_date"),
                "details": "Cached from upload",
                "document_name": doc.get("original_filename", "Unknown"),
                "document_type": doc.get("doc_type") or "Unknown",
            }
            results.append(sig_result)
            if not sig_result["is_signed"]:
                all_signed = False

        return {"employee_name": employee_name, "total_documents": len(results), "signed_documents": sum(1 for r in results if r["is_signed"]), "all_signed": all_signed, "documents": results}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_name}/signature-status")
async def get_signature_status(employee_name: str):
    try:
        employee_name = resolve_employee_name(unquote(employee_name)) or unquote(employee_name)
        documents = get_documents_by_employee(employee_name)

        if not documents:
            return {"employee_name": employee_name, "status": "no_documents", "message": "No documents uploaded yet"}

        total_count = len(documents)
        signed_count = sum(1 for d in documents if d.get("status") == "signed")

        if signed_count == total_count:
            status = "all_signed"
            message = f"All {total_count} documents are signed"
        elif signed_count > 0:
            status = "partially_signed"
            message = f"{signed_count}/{total_count} documents are signed"
        else:
            status = "not_signed"
            message = "No documents are signed"

        return {"employee_name": employee_name, "status": status, "message": message, "signed_count": signed_count, "total_count": total_count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{employee_name}/clear-status")
async def clear_document_status(employee_name: str):
    try:
        employee_name = resolve_employee_name(unquote(employee_name)) or unquote(employee_name)
        documents = get_documents_by_employee(employee_name)
        if not documents:
            raise HTTPException(status_code=404, detail="No documents found")
        for doc in documents:
            update_document(doc["id"], {"status": "uploaded"})
        insert_audit_log({"action": "clear_status", "status": "success", "details": {"employee": employee_name, "count": len(documents)}})
        return {"success": True, "message": f"Cleared status for {len(documents)} documents"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{employee_name}/reset-fields")
async def reset_document_fields(employee_name: str):
    try:
        employee_name = resolve_employee_name(unquote(employee_name)) or unquote(employee_name)
        documents = get_documents_by_employee(employee_name)
        if not documents:
            raise HTTPException(status_code=404, detail="No documents found")
        for doc in documents:
            update_document(doc["id"], {"platform": None, "doc_type": None, "classification_confidence": None, "title": None, "signers": [], "document_date": None})
        insert_audit_log({"action": "reset_fields", "status": "success", "details": {"employee": employee_name, "count": len(documents)}})
        return {"success": True, "message": f"Reset fields for {len(documents)} documents"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
