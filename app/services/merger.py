from pathlib import Path
from typing import List, Optional
from PyPDF2 import PdfReader, PdfWriter
import io
from datetime import datetime
from app.config import settings


class PDFMerger:
    def merge_documents(self, documents: List[dict], employee_name: str, storage=None) -> dict:
        try:
            writer = PdfWriter()
            bookmarks = []

            for idx, doc in enumerate(documents):
                doc_path = doc.get("stored_path")
                doc_type = doc.get("doc_type", "unknown")

                pdf_bytes = None
                if storage:
                    pdf_bytes = storage.read_file(doc_path)
                elif doc_path and Path(doc_path).exists():
                    pdf_bytes = Path(doc_path).read_bytes()

                if pdf_bytes:
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    for page in reader.pages:
                        writer.add_page(page)
                    doc_name = settings.ALL_DOCUMENT_TYPES.get(doc_type, doc_type)
                    bookmarks.append({"name": doc_name, "page": idx, "file": doc.get("original_filename")})

            output_buffer = io.BytesIO()
            writer.write(output_buffer)
            output_buffer.seek(0)

            safe_name = employee_name.replace(" ", "_").lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_name}_employment_package_{timestamp}.pdf"

            return {"success": True, "pdf_content": output_buffer.getvalue(), "filename": filename, "bookmarks": bookmarks, "page_count": len(writer.pages)}

        except Exception as e:
            return {"success": False, "error": str(e)}
