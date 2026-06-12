---
title: Demerge Backend
emoji: 📄
colorFrom: gray
colorTo: black
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Demerge Backend

FastAPI backend for Demerge document management system.

## Environment Variables

Set these in your HF Space secrets:

- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase service role key
- `SUPABASE_STORAGE_BUCKET` - Storage bucket name (default: documents)
- `CORS_ORIGINS` - Allowed origins (default: *)

## API Endpoints

- `GET /health` - Health check
- `GET /config` - App configuration
- `POST /api/documents/upload` - Upload documents
- `POST /api/documents/process` - Process uploaded files
- `POST /api/documents/cleanup` - Clean expired files
- `GET /api/packages/` - List all packages
- `GET /api/packages/with-status` - List with signature status
- `POST /api/packages/{name}/merge` - Merge documents
- `DELETE /api/packages/{name}` - Delete employee
- `POST /api/packages/bulk-delete` - Bulk delete
- `POST /api/packages/bulk-download` - Bulk download ZIP
