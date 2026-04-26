import base64
import io
import json
import os
import sys
from typing import Any, Dict

from pypdf import PdfReader


ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(ROOT, "utils"))


def _json_response(status: int, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(data),
    }


def _read_request_json(request: Any) -> Dict[str, Any]:
    if hasattr(request, "json") and callable(getattr(request, "json")):
        return request.json()
    if hasattr(request, "get_json") and callable(getattr(request, "get_json")):
        return request.get_json()
    body = getattr(request, "body", None)
    if body is None and hasattr(request, "get_body"):
        body = request.get_body()
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8", errors="ignore")
    if not body:
        return {}
    return json.loads(body)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            parts.append("")
    text = "\n".join(parts).strip()
    return text


def handler(request):
    """
    Input JSON:
      { "resume_pdf_base64": "<base64 string>" }
    Output:
      { "resume_text": "..." }
    """
    try:
        payload = _read_request_json(request)
        b64 = (payload.get("resume_pdf_base64") or "").strip()
        if not b64:
            return _json_response(400, {"error": "Missing resume_pdf_base64"})
        pdf_bytes = base64.b64decode(b64, validate=False)
        resume_text = _extract_pdf_text(pdf_bytes)
        return _json_response(200, {"resume_text": resume_text})
    except Exception as e:
        return _json_response(500, {"error": "Failed to parse resume", "detail": str(e)})
