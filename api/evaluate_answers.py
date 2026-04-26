import json
import os
import sys
from typing import Any, Dict


ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(ROOT, "utils"))

from groq_client import best_effort_json, groq_chat  # noqa: E402
from prompts import EVAL_SYSTEM, EVAL_USER  # noqa: E402


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


def handler(request):
    """
    Input JSON:
      { "job_description": "...", "qa_by_skill": { "Python": [{"q":"...","a":"..."}] } }
    Output JSON:
      { "skills": [{ "skill": "...", "score": 0-10, "level": "...", "rationale": "..." }] }
    """
    try:
        payload = _read_request_json(request)
        job_description = (payload.get("job_description") or "").strip()
        qa_by_skill = payload.get("qa_by_skill") or {}
        if not qa_by_skill:
            return _json_response(400, {"error": "Missing qa_by_skill"})

        raw = groq_chat(
            messages=[
                {"role": "system", "content": EVAL_SYSTEM},
                {
                    "role": "user",
                    "content": EVAL_USER.format(
                        job_description=job_description[:12000],
                        qa_json=json.dumps(qa_by_skill)[:16000],
                    ),
                },
            ],
            temperature=0.15,
            max_tokens=1400,
        )
        data = best_effort_json(raw) or {}
        skills = data.get("skills") or []
        return _json_response(200, {"skills": skills})
    except Exception as e:
        return _json_response(500, {"error": "Failed to evaluate answers", "detail": str(e)})
