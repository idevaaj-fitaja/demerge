import io
import re
from typing import Dict
from pyhanko.sign.fields import enumerate_sig_fields
from pyhanko.pdf_utils.reader import PdfFileReader


def detect_signature_from_bytes(pdf_bytes: bytes) -> Dict:
    """Detect signature from PDF bytes (file-like object)."""
    result = {"is_signed": False, "signature_type": "none", "signers": [], "platform": "unknown", "signed_date": None, "details": ""}
    try:
        r = PdfFileReader(io.BytesIO(pdf_bytes))
        all_fields = list(enumerate_sig_fields(r))
        if not all_fields:
            result["details"] = "No signature fields found"
            return result
        signed_fields = list(enumerate_sig_fields(r, filled_status=True))
        if signed_fields:
            result["is_signed"] = True
            result["signature_type"] = "digital"
            for name, ref, field_obj in signed_fields:
                result["signers"].append(name)
                result["details"] += f"Found signed /Sig field: {name}\n"
                name_lower = name.lower()
                if 'privy' in name_lower or 'assistpriv' in name_lower:
                    result["platform"] = "privyid"
                elif 'docusign' in name_lower:
                    result["platform"] = "docusign"
                elif 'adobe' in name_lower:
                    result["platform"] = "adobe_sign"
        else:
            result["details"] = f"Found {len(all_fields)} empty signature field(s)"
        if result["is_signed"] and result["platform"] == "unknown":
            full_text = ""
            for page in r.pages:
                text = page.extract_text() or ""
                full_text += text
            platform_patterns = {
                "privyid": [r"privy\s*id", r"privy\.id", r"pt\.?\s*privy\s*digisign", r"assistpriv"],
                "docusign": [r"docu\s*sign", r"docusign\.com"],
                "adobe_sign": [r"adobe\s*sign", r"adobe\s*cloud\s*sign"],
                "onesign": [r"onesign", r"one\s*sign"],
            }
            for platform, patterns in platform_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, full_text, re.IGNORECASE):
                        result["platform"] = platform
                        result["details"] += f"Detected platform from text: {platform}\n"
                        break
    except Exception as e:
        result["details"] = f"Error reading PDF: {str(e)}"
    return result


def detect_signature(pdf_path: str) -> Dict:
    """Detect signature from a file path. Delegates to bytes version."""
    import os
    if not os.path.exists(pdf_path):
        return {"is_signed": False, "signature_type": "none", "signers": [], "platform": "unknown", "signed_date": None, "details": "File not found"}
    with open(pdf_path, 'rb') as f:
        return detect_signature_from_bytes(f.read())


def get_signature_status_text(result: Dict) -> str:
    if result["is_signed"]:
        platform = f" ({result['platform'].upper()})" if result["platform"] != "unknown" else ""
        signers = f" by: {', '.join(result['signers'])}" if result["signers"] else ""
        return f"{result['signature_type'].upper()}{platform}{signers}"
    return "NOT SIGNED"
