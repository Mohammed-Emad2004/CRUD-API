import datetime
import json
import os
from typing import Any, Dict, Optional

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
QUARANTINE_FILE = os.path.join(LOGS_DIR, "quarantine.jsonl")


def log_quarantine_record(
    input_record: Dict[str, Any],
    prompt_version: str,
    raw_model_output: str,
    validation_error: str,
    repair_raw_output: Optional[str] = None,
    final_error: Optional[str] = None,
) -> None:
    """
    Writes one JSONL quarantine record containing debugging info for failed parse/validation attempts.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)

    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "prompt_version": prompt_version,
        "input_record": input_record,
        "raw_model_output": raw_model_output,
        "validation_error": validation_error,
        "repair_raw_output": repair_raw_output,
        "final_error": final_error or validation_error,
    }

    with open(QUARANTINE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
