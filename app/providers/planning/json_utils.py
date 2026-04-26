from __future__ import annotations

import json
import re
from typing import Any

from app.core.errors import LlmResponseFormatError
from app.core.serialization import narrative_plan_from_dict


def parse_plan_json(text: str):
    try:
        return narrative_plan_from_dict(json.loads(_extract_json_object(text)))
    except Exception as exc:
        raise LlmResponseFormatError(str(exc)) from exc


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or start >= end:
        raise ValueError("JSON object not found")

    return json.loads(cleaned[start : end + 1])

