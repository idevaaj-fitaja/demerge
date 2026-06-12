from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List
from app.services.processor import DocumentProcessor
from app.models.database import get_documents_by_employee, get_all_documents, delete_document
from app.config import settings
import asyncio

router = APIRouter(prefix="/api/documents", tags=["documents"])
processor = DocumentProcessor()

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
