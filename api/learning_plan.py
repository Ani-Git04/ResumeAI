import json
import os
import sys
from typing import Any, Dict


ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(ROOT, "utils"))

from groq_client import groq_chat  # noqa: E402
from prompts import LEARNING_PLAN_SYSTEM, LEARNING_PLAN_USER  # noqa: E402


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
      { "job_description": "...", "missing_skills": [...], "scored_skills": [...] }
    Output JSON:
      { "learning_plan_markdown": "..." }
    """
    try:
        payload = _read_request_json(request)
        job_description = (payload.get("job_description") or "").strip()
        missing_skills = payload.get("missing_skills") or []
        scored_skills = payload.get("scored_skills") or []

        md = groq_chat(
            messages=[
                {"role": "system", "content": LEARNING_PLAN_SYSTEM},
                {
                    "role": "user",
                    "content": LEARNING_PLAN_USER.format(
                        job_description=job_description[:12000],
                        missing_skills_json=json.dumps(missing_skills),
                        scored_skills_json=json.dumps(scored_skills)[:12000],
                    ),
                },
            ],
            temperature=0.25,
            max_tokens=1900,
        ).strip()

        return _json_response(200, {"learning_plan_markdown": md})
    except Exception as e:
        return _json_response(500, {"error": "Failed to generate learning plan", "detail": str(e)})
