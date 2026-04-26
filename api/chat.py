import json
import os
import sys
from typing import Any, Dict, List


ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(os.path.join(ROOT, "utils"))

from groq_client import groq_chat  # noqa: E402
from prompts import CHAT_INTERVIEWER_SYSTEM  # noqa: E402


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
    Conversational interviewer.

    Input JSON:
      {
        "conversation": [{"role":"user|assistant","content":"..."}],
        "active_skill": "Python",
        "current_question": "..."
      }

    Output JSON:
      { "assistant_message": "..." }
    """
    try:
        payload = _read_request_json(request)
        conversation: List[Dict[str, str]] = payload.get("conversation") or []
        active_skill = (payload.get("active_skill") or "").strip()
        current_question = (payload.get("current_question") or "").strip()

        preface = "You are interviewing for the skill: " + (active_skill or "General") + "."
        if current_question:
            preface += "\nThe current interview question is:\n" + current_question

        messages = [{"role": "system", "content": CHAT_INTERVIEWER_SYSTEM + "\n\n" + preface}]
        # Keep last turns to fit context windows.
        messages.extend(conversation[-16:])

        assistant = groq_chat(
            messages=messages,
            temperature=0.35,
            max_tokens=700,
        ).strip()

        return _json_response(200, {"assistant_message": assistant})
    except Exception as e:
        return _json_response(500, {"error": "Chat failed", "detail": str(e)})
