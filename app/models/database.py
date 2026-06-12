import os
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from app.config import settings, CLOUD_MODE

if CLOUD_MODE:
    from supabase import create_client, Client
    _supabase: Optional[Client] = None

    def _get_supabase() -> Client:
        global _supabase
        if _supabase is None:
            _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return _supabase
else:
    DATABASE_PATH = settings.DATABASE_PATH
    _lock = threading.Lock()
    _conn: Optional[sqlite3.Connection] = None

    def _get_conn() -> sqlite3.Connection:
        global _conn
        if _conn is None:
            _conn = sqlite3.connect(str(DATABASE_PATH), timeout=60, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode=WAL")
            _conn.execute("PRAGMA busy_timeout=30000")
            _conn.execute("PRAGMA synchronous=NORMAL")
            _conn.execute("PRAGMA foreign_keys=ON")
        return _conn


# ── Helpers ───────────────────────────────────────────────────────

def _serialize(v):
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    return v


def _deserialize(v):
    if v is None:
        return v
    try:
        return json.loads(v)
    except (json.JSONDecodeError, TypeError):
        return v


def db_health() -> bool:
    try:
        if CLOUD_MODE:
            _get_supabase().table("documents").select("id").limit(1).execute()
        else:
            _get_conn().execute("SELECT 1")
        return True
    except Exception:
        return False


# ── Init ──────────────────────────────────────────────────────────

def init_db():
    if CLOUD_MODE:
        return
    with _lock:
        conn = _get_conn()
        conn.executescript("""
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
                signers TEXT,
                document_date TEXT,
                status TEXT DEFAULT 'uploaded',
                validation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS employee_packages (
                id TEXT PRIMARY KEY,
                employee_name TEXT NOT NULL,
                document_count INTEGER DEFAULT 0,
                required_docs TEXT DEFAULT '["offer_letter","nda","employment_contract"]',
                missing_docs TEXT DEFAULT '[]',
                is_complete INTEGER DEFAULT 0,
                merged_pdf_path TEXT,
                summary_path TEXT,
                status TEXT DEFAULT 'incomplete',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT,
                package_id TEXT,
                action TEXT NOT NULL,
                agent TEXT,
                status TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()


# ── Read ──────────────────────────────────────────────────────────

def _map_row(r):
    if r is None:
        return None
    d = dict(r)
    for k in ("signers", "validation", "required_docs", "missing_docs", "details"):
        if k in d and isinstance(d.get(k), str):
            d[k] = _deserialize(d[k])
    if "is_complete" in d:
        d["is_complete"] = bool(d["is_complete"])
    return d


def resolve_employee_name(name: str) -> Optional[str]:
    if not name or len(name.strip()) < 2:
        return None
    name = name.strip()
    if CLOUD_MODE:
        sb = _get_supabase()
        r = sb.table("documents").select("employee_name").eq("employee_name", name).limit(1).execute()
        if r.data:
            return r.data[0]["employee_name"]
        r = sb.table("documents").select("employee_name").ilike("employee_name", f"%{name}%").limit(1).execute()
        if r.data:
            return r.data[0]["employee_name"]
        return None
    else:
        for query in [
            "SELECT employee_name FROM documents WHERE employee_name = ? LIMIT 1",
            "SELECT employee_name FROM documents WHERE employee_name LIKE ? LIMIT 1",
            "SELECT employee_name FROM documents WHERE employee_name LIKE ? LIMIT 1",
        ]:
            params = (name, f"%{name}%", f"{name}%")
            if query == "SELECT employee_name FROM documents WHERE employee_name = ? LIMIT 1":
                r = _fetchone(query, (name,))
            else:
                r = _fetchone(query, (f"%{name}%" if "LIKE ?" in query else f"{name}%",))
            if r:
                return r["employee_name"]
        return None


def get_documents_by_employee(employee_name: str) -> List[dict]:
    resolved = resolve_employee_name(employee_name) or employee_name
    if CLOUD_MODE:
        r = _get_supabase().table("documents").select("*").eq("employee_name", resolved).order("created_at", desc=True).execute()
        return r.data or []
    return _fetchall("SELECT * FROM documents WHERE employee_name = ? ORDER BY created_at DESC", (resolved,))


def get_all_documents() -> List[dict]:
    if CLOUD_MODE:
        r = _get_supabase().table("documents").select("*").order("created_at", desc=True).execute()
        return r.data or []
    return _fetchall("SELECT * FROM documents ORDER BY created_at DESC")


def get_package_by_employee(employee_name: str) -> Optional[dict]:
    resolved = resolve_employee_name(employee_name) or employee_name
    if CLOUD_MODE:
        r = _get_supabase().table("employee_packages").select("*").eq("employee_name", resolved).order("created_at", desc=True).limit(1).execute()
        if r.data:
            return _map_row(r.data[0])
        return None
    pkg = _fetchone("SELECT * FROM employee_packages WHERE employee_name = ? ORDER BY created_at DESC LIMIT 1", (resolved,))
    return _map_row(pkg)


def get_all_packages() -> List[dict]:
    if CLOUD_MODE:
        r = _get_supabase().table("employee_packages").select("*").order("created_at", desc=True).execute()
        return [_map_row(p) for p in (r.data or [])]
    packages = _fetchall("SELECT * FROM employee_packages ORDER BY created_at DESC")
    return [_map_row(p) for p in packages]


# ── Write (local SQLite helpers) ──────────────────────────────────

def _execute(sql, params=()):
    with _lock:
        return _get_conn().execute(sql, params)


def _commit():
    with _lock:
        _get_conn().commit()


def _fetchall(sql, params=()):
    with _lock:
        rows = _get_conn().execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def _fetchone(sql, params=()):
    with _lock:
        row = _get_conn().execute(sql, params).fetchone()
        return dict(row) if row else None


def _audit_log_sqlite(cursor, log: dict):
    cursor.execute("""
        INSERT INTO audit_logs (document_id, package_id, action, agent, status, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        log.get("document_id"), log.get("package_id"),
        log["action"], log.get("agent"), log.get("status"),
        json.dumps(log.get("details", {}))
    ))


# ── Write ─────────────────────────────────────────────────────────

ALLOWED_DOC_COLUMNS = {
    "platform", "doc_type", "classification_confidence", "title",
    "signers", "document_date", "status", "validation"
}
ALLOWED_PKG_COLUMNS = {
    "document_count", "required_docs", "missing_docs", "is_complete",
    "merged_pdf_path", "summary_path", "status"
}


def insert_document(doc: dict) -> str:
    now = datetime.now().isoformat()
    if CLOUD_MODE:
        payload = {
            "id": doc["id"],
            "employee_id": doc["employee_id"],
            "employee_name": doc["employee_name"],
            "original_filename": doc["original_filename"],
            "stored_path": doc["stored_path"],
            "file_size": doc["file_size"],
            "file_hash": doc["file_hash"],
            "platform": doc.get("platform"),
            "doc_type": doc.get("doc_type"),
            "classification_confidence": doc.get("classification_confidence"),
            "title": doc.get("title"),
            "signers": _serialize(doc.get("signers", [])),
            "document_date": doc.get("document_date"),
            "status": doc.get("status", "uploaded"),
            "validation": _serialize(doc.get("validation")),
            "created_at": doc.get("created_at", now),
            "updated_at": doc.get("updated_at", now),
        }
        _get_supabase().table("documents").insert(payload).execute()
        _get_supabase().table("audit_logs").insert({
            "document_id": doc["id"],
            "action": "upload",
            "status": "success",
            "details": _serialize({"filename": doc["original_filename"], "employee": doc["employee_name"]})
        }).execute()
        return doc["id"]

    doc = dict(doc)
    doc["signers"] = json.dumps(doc.get("signers", []))
    with _lock:
        conn = _get_conn()
        conn.execute("""
            INSERT INTO documents (
                id, employee_id, employee_name, original_filename,
                stored_path, file_size, file_hash, platform,
                doc_type, classification_confidence, title,
                signers, document_date, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc["id"], doc["employee_id"], doc["employee_name"],
            doc["original_filename"], doc["stored_path"], doc["file_size"],
            doc["file_hash"], doc.get("platform"), doc.get("doc_type"),
            doc.get("classification_confidence"), doc.get("title"),
            doc.get("signers", "[]"), doc.get("document_date"),
            doc.get("status", "uploaded"),
            doc.get("created_at", now),
            doc.get("updated_at", now)
        ))
        _audit_log_sqlite(conn.cursor(), {
            "document_id": doc["id"],
            "action": "upload",
            "status": "success",
            "details": {"filename": doc["original_filename"], "employee": doc["employee_name"]}
        })
        conn.commit()
    return doc["id"]


def update_document(doc_id: str, updates: dict):
    updates = {k: v for k, v in updates.items() if k in ALLOWED_DOC_COLUMNS}
    if not updates:
        return
    now = datetime.now().isoformat()
    updates["updated_at"] = now
    if CLOUD_MODE:
        payload = {}
        for k, v in updates.items():
            if k in ("signers", "validation") and isinstance(v, (dict, list)):
                payload[k] = _serialize(v)
            else:
                payload[k] = v
        _get_supabase().table("documents").update(payload).eq("id", doc_id).execute()
        return
    if "signers" in updates and isinstance(updates["signers"], list):
        updates["signers"] = json.dumps(updates["signers"])
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [doc_id]
    with _lock:
        _get_conn().execute(f"UPDATE documents SET {set_clause} WHERE id = ?", values)
        _get_conn().commit()


def delete_document(doc_id: str):
    if CLOUD_MODE:
        _get_supabase().table("documents").delete().eq("id", doc_id).execute()
        _get_supabase().table("audit_logs").insert({
            "document_id": doc_id,
            "action": "delete",
            "status": "success",
            "details": _serialize({})
        }).execute()
        return
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        _audit_log_sqlite(conn.cursor(), {
            "document_id": doc_id,
            "action": "delete",
            "status": "success"
        })
        conn.commit()


def insert_package(pkg: dict) -> str:
    now = datetime.now().isoformat()
    if CLOUD_MODE:
        payload = {
            "id": pkg["id"],
            "employee_name": pkg["employee_name"],
            "document_count": pkg.get("document_count", 0),
            "required_docs": _serialize(pkg.get("required_docs", [])),
            "missing_docs": _serialize(pkg.get("missing_docs", [])),
            "is_complete": pkg.get("is_complete", False),
            "merged_pdf_path": pkg.get("merged_pdf_path"),
            "summary_path": pkg.get("summary_path"),
            "status": pkg.get("status", "incomplete"),
            "created_at": pkg.get("created_at", now),
            "updated_at": pkg.get("updated_at", now),
        }
        _get_supabase().table("employee_packages").insert(payload).execute()
        return pkg["id"]

    pkg = dict(pkg)
    pkg["required_docs"] = json.dumps(pkg.get("required_docs", []))
    pkg["missing_docs"] = json.dumps(pkg.get("missing_docs", []))
    pkg["is_complete"] = 1 if pkg.get("is_complete") else 0
    with _lock:
        conn = _get_conn()
        conn.execute("""
            INSERT INTO employee_packages (
                id, employee_name, document_count, required_docs,
                missing_docs, is_complete, merged_pdf_path, summary_path,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pkg["id"], pkg["employee_name"], pkg.get("document_count", 0),
            pkg.get("required_docs", "[]"), pkg.get("missing_docs", "[]"),
            pkg.get("is_complete", 0), pkg.get("merged_pdf_path"),
            pkg.get("summary_path"), pkg.get("status", "incomplete"),
            pkg.get("created_at", now),
            pkg.get("updated_at", now)
        ))
        conn.commit()
    return pkg["id"]


def update_package(pkg_id: str, updates: dict):
    updates = {k: v for k, v in updates.items() if k in ALLOWED_PKG_COLUMNS}
    if not updates:
        return
    now = datetime.now().isoformat()
    updates["updated_at"] = now
    if CLOUD_MODE:
        payload = {}
        for k, v in updates.items():
            if k in ("required_docs", "missing_docs") and isinstance(v, list):
                payload[k] = _serialize(v)
            elif k == "is_complete":
                payload[k] = bool(v)
            else:
                payload[k] = v
        _get_supabase().table("employee_packages").update(payload).eq("id", pkg_id).execute()
        return
    if "required_docs" in updates and isinstance(updates["required_docs"], list):
        updates["required_docs"] = json.dumps(updates["required_docs"])
    if "missing_docs" in updates and isinstance(updates["missing_docs"], list):
        updates["missing_docs"] = json.dumps(updates["missing_docs"])
    if "is_complete" in updates:
        updates["is_complete"] = 1 if updates["is_complete"] else 0
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [pkg_id]
    with _lock:
        _get_conn().execute(f"UPDATE employee_packages SET {set_clause} WHERE id = ?", values)
        _get_conn().commit()


def insert_audit_log(log: dict):
    if CLOUD_MODE:
        payload = {
            "document_id": log.get("document_id"),
            "package_id": log.get("package_id"),
            "action": log["action"],
            "agent": log.get("agent"),
            "status": log.get("status"),
            "details": _serialize(log.get("details", {})),
        }
        _get_supabase().table("audit_logs").insert(payload).execute()
        return
    with _lock:
        conn = _get_conn()
        _audit_log_sqlite(conn.cursor(), log)
        conn.commit()


def delete_employee_all(employee_name: str):
    if CLOUD_MODE:
        _get_supabase().table("documents").delete().eq("employee_name", employee_name).execute()
        _get_supabase().table("employee_packages").delete().eq("employee_name", employee_name).execute()
        _get_supabase().table("audit_logs").insert({
            "action": "delete_package",
            "status": "success",
            "details": _serialize({"employee": employee_name})
        }).execute()
        return
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM documents WHERE employee_name = ?", (employee_name,))
        conn.execute("DELETE FROM employee_packages WHERE employee_name = ?", (employee_name,))
        _audit_log_sqlite(conn.cursor(), {
            "action": "delete_package",
            "status": "success",
            "details": {"employee": employee_name}
        })
        conn.commit()
