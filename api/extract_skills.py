import json
import os
import sys
from typing import Any, Dict


ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(ROOT, "utils"))

from groq_client import best_effort_json, groq_chat  # noqa: E402
from prompts import SKILL_EXTRACTION_SYSTEM, SKILL_EXTRACTION_USER  # noqa: E402
from skill_parser import compute_missing, uniq_skills  # noqa: E402


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
      { "resume_text": "...", "job_description": "..." }
    Output JSON:
      { "resume_skills": [], "jd_skills": [], "missing_skills": [] }
    """
    try:
        payload = _read_request_json(request)
        resume_text = (payload.get("resume_text") or "").strip()
        job_description = (payload.get("job_description") or "").strip()
        if not resume_text or not job_description:
            return _json_response(400, {"error": "Missing resume_text or job_description"})

        prompt = SKILL_EXTRACTION_USER.format(
            resume_text=resume_text[:12000],
            job_description=job_description[:12000],
        )

        raw = groq_chat(
            messages=[
                {"role": "system", "content": SKILL_EXTRACTION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1200,
        )
        data = best_effort_json(raw) or {}
        resume_skills = uniq_skills(data.get("resume_skills") or [])
        jd_skills = uniq_skills(data.get("jd_skills") or [])
        missing_skills = compute_missing(jd_skills, resume_skills)

        return _json_response(
            200,
            {
                "resume_skills": resume_skills,
                "jd_skills": jd_skills,
                "missing_skills": missing_skills,
            },
        )
    except Exception as e:
        return _json_response(500, {"error": "Failed to extract skills", "detail": str(e)})
