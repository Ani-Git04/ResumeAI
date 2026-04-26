import json
import os
import time
from typing import Any, Dict, List, Optional

from groq import Groq


def _client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY environment variable.")
    return Groq(api_key=api_key)


def groq_chat(
    *,
    messages: List[Dict[str, str]],
    model: str = "llama3-70b-8192",
    temperature: float = 0.2,
    max_tokens: int = 1200,
    response_format: Optional[Dict[str, Any]] = None,
    retries: int = 2,
) -> str:
    """
    Small, production-oriented wrapper around Groq Chat Completions.
    Returns the assistant text content (string).
    """
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            params: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            # Groq may support structured outputs depending on SDK/version.
            if response_format is not None:
                params["response_format"] = response_format

            completion = _client().chat.completions.create(**params)
            return completion.choices[0].message.content or ""
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.4 * (2**attempt))
                continue
            raise RuntimeError(f"Groq request failed: {e}") from e


def best_effort_json(text: str) -> Any:
    """
    Attempts to parse JSON from a model response that might include markdown fences.
    """
    t = (text or "").strip()
    if not t:
        return None

    # Strip common markdown fences
    if t.startswith("```"):
        t = t.split("```", 2)[1] if "```" in t else t
        t = t.replace("json", "", 1).strip()
    # Try direct parse
    try:
        return json.loads(t)
    except Exception:
        pass

    # Try to locate first/last json object/array
    first_obj = t.find("{")
    last_obj = t.rfind("}")
    first_arr = t.find("[")
    last_arr = t.rfind("]")

    candidates = []
    if first_obj != -1 and last_obj != -1 and last_obj > first_obj:
        candidates.append(t[first_obj : last_obj + 1])
    if first_arr != -1 and last_arr != -1 and last_arr > first_arr:
        candidates.append(t[first_arr : last_arr + 1])

    for c in candidates:
        try:
            return json.loads(c)
        except Exception:
            continue

    return None
