import json
import re
from typing import Any, Dict


def extract_and_parse_json(raw_text: str) -> Dict[str, Any]:
    """
    Robustly extract and parse JSON from raw model text.
    Handles:
    - Normal JSON objects
    - JSON wrapped in markdown ```json ... ``` or ``` ... ``` fences
    - Harmless surrounding text where a JSON object can safely be extracted via regex/brace matching
    Raises ValueError if parsing fails or no valid JSON object can be extracted.
    """
    if not raw_text or not isinstance(raw_text, str):
        raise ValueError("Raw text is empty or not a string")

    cleaned = raw_text.strip()

    # 1. Try direct json.loads
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # 2. Try extracting from markdown code fences (```json ... ``` or ``` ... ```)
    # Support both ```json and generic ``` blocks safely
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    matches = re.findall(fence_pattern, cleaned)
    for match in matches:
        try:
            parsed = json.loads(match.strip())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # 3. Try finding the first '{' and last '}' for surrounding text extraction
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidate = cleaned[start_idx : end_idx + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract a valid JSON object from raw text: {raw_text[:200]!r}")
