import json
import os
import sys
from typing import Any, Dict, List


ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(ROOT, "utils"))

from groq_client import best_effort_json, groq_chat  # noqa: E402
from prompts import QUESTION_GEN_SYSTEM, QUESTION_GEN_USER  # noqa: E402
from skill_parser import uniq_skills  # noqa: E402


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
      { "skills": ["Python", "SQL", ...] }
    Output JSON:
      { "questions_by_skill": { "Python": ["q1","q2","q3"], ... } }
    """
    try:
        payload = _read_request_json(request)
        skills: List[str] = uniq_skills(payload.get("skills") or [])
        if not skills:
            return _json_response(400, {"error": "Missing skills"})

        raw = groq_chat(
            messages=[
                {"role": "system", "content": QUESTION_GEN_SYSTEM},
                {
                    "role": "user",
                    "content": QUESTION_GEN_USER.format(skills_json=json.dumps(skills)),
                },
            ],
            temperature=0.25,
            max_tokens=1400,
        )
        data = best_effort_json(raw) or {}
        qbs = data.get("questions_by_skill") or {}

        # Ensure exactly 3 per skill, and preserve requested skill list.
        cleaned: Dict[str, List[str]] = {}
        for s in skills:
            qs = qbs.get(s) or qbs.get(s.lower()) or []
            if not isinstance(qs, list):
                qs = []
            qs = [str(x).strip() for x in qs if str(x).strip()]
            cleaned[s] = (qs + [""] * 3)[:3]
            cleaned[s] = [q for q in cleaned[s] if q] or [
                f"Walk me through a real project where you used {s}. What was your role?",
                f"What’s a common pitfall in {s}, and how do you avoid it?",
                f"Design a small solution using {s}. Explain trade-offs and edge cases.",
            ]

        return _json_response(200, {"questions_by_skill": cleaned})
    except Exception as e:
        return _json_response(500, {"error": "Failed to generate questions", "detail": str(e)})
