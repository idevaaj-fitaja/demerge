from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class DocumentType(str, Enum):
    OFFER_LETTER = "offer_letter"
    NDA = "nda"
    EMPLOYMENT_CONTRACT = "employment_contract"
    JOB_DESCRIPTION = "job_description"
    COMPANY_POLICY = "company_policy"


class Platform(str, Enum):
    PRIVYID = "privyid"
    DOCUSIGN = "docusign"
    ADOBE_SIGN = "adobe_sign"
    MANUAL = "manual"
    OTHER = "other"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    VALID = "valid"
    INVALID = "invalid"
    MERGED = "merged"
    ARCHIVED = "archived"


class PackageStatus(str, Enum):
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    MERGED = "merged"
    ARCHIVED = "archived"


class Signer(BaseModel):
    name: str
    role: str
    status: str  # signed, pending, declined
    signed_date: Optional[str] = None


class DocumentClassification(BaseModel):
    platform: str
    doc_type: str
    confidence: str  # high, medium, low


class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    signers: List[Signer] = []
    key_info: dict = {}


class Document(BaseModel):
    id: str
    employee_id: str
    employee_name: str
    original_filename: str
    stored_path: str
    file_size: int
    file_hash: str
    
    # Classification
    platform: Optional[str] = None
    doc_type: Optional[str] = None
    classification_confidence: Optional[str] = None
    
    # Metadata
    title: Optional[str] = None
    signers: List[dict] = []
    document_date: Optional[str] = None
    
    # Status
    status: DocumentStatus = DocumentStatus.UPLOADED
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class EmployeePackage(BaseModel):
    id: str
    employee_name: str
    
    # Documents
    documents: List[Document] = []
    document_count: int = 0
    
    # Completeness
    required_docs: List[str] = ["offer_letter", "nda", "employment_contract"]
    missing_docs: List[str] = []
    is_complete: bool = False
    
    # Merged output
    merged_pdf_path: Optional[str] = None
    summary_path: Optional[str] = None
    
    # Status
    status: PackageStatus = PackageStatus.INCOMPLETE
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class UploadResponse(BaseModel):
    success: bool
    message: str
    employee_name: str
    documents_processed: int
    package_id: Optional[str] = None
    classification_results: List[dict] = []


class ProcessResponse(BaseModel):
    success: bool
    message: str
    package_id: str
    employee_name: str
    is_complete: bool
    missing_docs: List[str]
    merged_path: Optional[str] = None
    processing_time_seconds: float


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
