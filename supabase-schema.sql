-- Run this in Supabase SQL Editor to create the tables

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    employee_name TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    file_size INTEGER,
    file_hash TEXT,
    platform TEXT,
    doc_type TEXT,
    classification_confidence TEXT,
    title TEXT,
    signers JSONB DEFAULT '[]',
    document_date TEXT,
    status TEXT DEFAULT 'uploaded',
    validation JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS employee_packages (
    id TEXT PRIMARY KEY,
    employee_name TEXT NOT NULL,
    document_count INTEGER DEFAULT 0,
    required_docs JSONB DEFAULT '["offer_letter","nda","employment_contract"]',
    missing_docs JSONB DEFAULT '[]',
    is_complete BOOLEAN DEFAULT FALSE,
    merged_pdf_path TEXT,
    summary_path TEXT,
    status TEXT DEFAULT 'incomplete',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    document_id TEXT,
    package_id TEXT,
    action TEXT NOT NULL,
    agent TEXT,
    status TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_employee ON documents(employee_name);
CREATE INDEX IF NOT EXISTS idx_packages_employee ON employee_packages(employee_name);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);

-- Enable Row Level Security (optional, for client-side access)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE employee_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create storage bucket (run in Supabase Storage dashboard)
-- Bucket name: documents
-- Make it public if you want public file access, or keep private for signed URLs
