import time
import uuid
from typing import List
from datetime import datetime
from app.services.storage import StorageService
from app.services.merger import PDFMerger
from app.services.signature_detector import detect_signature_from_bytes, detect_signature
from app.models.database import insert_document, insert_package, update_package, get_documents_by_employee


class DocumentProcessor:
    def __init__(self):
        self.storage = StorageService()
        self.merger = PDFMerger()

    def process_upload(self, files: List[dict], employee_name: str) -> dict:
        start_time = time.time()
        stored_files = []

        try:
            for file in files:
                result = self.storage.store_raw(
                    file["content"],
                    file["filename"],
                    employee_name
                )
                stored_files.append(result)

            unsigned_files = []
            signed_files = []
            sig_results = {}

            for i, file_info in enumerate(stored_files):
                content = files[i]["content"]
                sig_result = detect_signature_from_bytes(content)
                sig_results[file_info["path"]] = sig_result
                if sig_result["is_signed"]:
                    signed_files.append(file_info)
                else:
                    unsigned_files.append(file_info["original_filename"])

            if unsigned_files:
                for file_info in stored_files:
                    self.storage.delete_file(file_info["path"])
                return {
                    "success": False,
                    "message": f"Cannot upload: {len(unsigned_files)} file(s) not signed: {', '.join(unsigned_files)}",
                    "unsigned_files": unsigned_files,
                    "signed_count": len(signed_files),
                    "total_count": len(stored_files)
                }

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
            package = self._create_or_update_package(employee_name, all_docs)

            merged_path = None
            if len(all_docs) >= 1:
                merge_result = self.merger.merge_documents(all_docs, employee_name, self.storage)
                if merge_result["success"]:
                    merged_path = self.storage.store_merged(
                        merge_result["pdf_content"],
                        employee_name,
                        merge_result["filename"]
                    )
                    update_package(package["id"], {
                        "merged_pdf_path": merged_path,
                        "status": "merged"
                    })

            processing_time = time.time() - start_time

            return {
                "success": True,
                "message": f"{len(files)} signed files uploaded & merged for {employee_name}",
                "package_id": package["id"],
                "employee_name": employee_name,
                "documents_processed": len(stored_files),
                "merged_path": merged_path,
                "processing_time_seconds": round(processing_time, 2)
            }

        except Exception as e:
            import traceback
            for file_info in stored_files:
                self.storage.delete_file(file_info["path"])
            return {
                "success": False,
                "message": f"Error: {type(e).__name__}: {str(e)}",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def _create_or_update_package(self, employee_name: str, documents: list) -> dict:
        """Create or update employee package"""
        from app.models.database import get_package_by_employee
        
        existing_package = get_package_by_employee(employee_name)
        
        if existing_package:
            pkg_id = existing_package["id"]
            updates = {
                "document_count": len(documents),
                "status": "merged"
            }
            update_package(pkg_id, updates)
            return {**existing_package, **updates}
        else:
            pkg_id = str(uuid.uuid4())
            package = {
                "id": pkg_id,
                "employee_name": employee_name,
                "document_count": len(documents),
                "required_docs": [],
                "missing_docs": [],
                "is_complete": True,
                "status": "merged",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            insert_package(package)
            return package
    
    def get_employee_summary(self, employee_name: str) -> dict:
        """Get summary for an employee"""
        from app.models.database import get_package_by_employee
        
        package = get_package_by_employee(employee_name)
        documents = get_documents_by_employee(employee_name)
        
        return {
            "employee_name": employee_name,
            "has_package": package is not None,
            "package": package,
            "documents": documents
        }
