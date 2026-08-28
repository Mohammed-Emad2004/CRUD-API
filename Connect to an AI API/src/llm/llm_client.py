import datetime
import json
import os
import random
import time
from typing import Any, Dict, Optional, Tuple

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
LLM_CALLS_LOG = os.path.join(LOGS_DIR, "llm_calls.jsonl")

MAX_PROVIDER_RETRIES = 2  # max 3 total attempts (1 initial + 2 retries)


def log_llm_call(
    prompt_version: str,
    model: str,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    duration_ms: int,
    repair: bool,
    attempt: int,
    success: bool,
    status_code: Optional[int] = None,
    retry_reason: Optional[str] = None,
) -> None:
    """
    Writes one structured JSONL log record for every actual LLM provider call.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)

    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "prompt_version": prompt_version,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "repair": repair,
        "attempt": attempt,
        "success": success,
    }
    if status_code is not None:
        record["status_code"] = status_code
    if retry_reason is not None:
        record["retry_reason"] = retry_reason

    with open(LLM_CALLS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def execute_llm_call_with_retries(
    messages: list,
    model: str,
    base_url: str,
    api_key: str,
    prompt_version: str,
    is_repair: bool = False,
) -> Tuple[str, Optional[int]]:
    """
    Executes an OpenAI-compatible LLM call with:
    - explicit 30.0s timeout
    - disabled SDK automatic retries (max_retries=0)
    - bounded provider retry policy for timeout, 429, 5xx (max 2 retries -> 3 attempts)
    - exponential backoff + jitter (~1s for attempt 1, ~2s for attempt 2)
    - Retry-After header respect for 429
    - structured cost/usage logging to logs/llm_calls.jsonl
    """
    from openai import OpenAI, APIStatusError, APITimeoutError, APIConnectionError

    client = OpenAI(
        base_url=base_url,
        api_key=api_key or "ollama",
        max_retries=0,  # disable SDK automatic retries
        timeout=30.0,   # explicit timeout
    )

    attempt = 0
    while True:
        attempt += 1
        start_time = time.time()
        status_code = None
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
            )
            duration_ms = int((time.time() - start_time) * 1000)

            # Extract usage safely
            input_tokens = None
            output_tokens = None
            if hasattr(response, "usage") and response.usage:
                input_tokens = getattr(response.usage, "prompt_tokens", None)
                output_tokens = getattr(response.usage, "completion_tokens", None)

            log_llm_call(
                prompt_version=prompt_version,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                repair=is_repair,
                attempt=attempt,
                success=True,
                status_code=200,
            )
            return response.choices[0].message.content, 200

        except APITimeoutError as timeout_exc:
            duration_ms = int((time.time() - start_time) * 1000)
            log_llm_call(
                prompt_version=prompt_version,
                model=model,
                input_tokens=None,
                output_tokens=None,
                duration_ms=duration_ms,
                repair=is_repair,
                attempt=attempt,
                success=False,
                retry_reason="timeout",
            )
            if attempt > MAX_PROVIDER_RETRIES:
                raise timeout_exc
            # Backoff: ~1s for 1st retry, ~2s for 2nd retry + jitter
            sleep_time = (2 ** (attempt - 1)) + random.uniform(0.1, 0.3)
            time.sleep(sleep_time)

        except APIStatusError as status_exc:
            duration_ms = int((time.time() - start_time) * 1000)
            status_code = status_exc.status_code
            retry_reason = f"http_{status_code}"

            log_llm_call(
                prompt_version=prompt_version,
                model=model,
                input_tokens=None,
                output_tokens=None,
                duration_ms=duration_ms,
                repair=is_repair,
                attempt=attempt,
                success=False,
                status_code=status_code,
                retry_reason=retry_reason,
            )

            # Check if retryable (429 or 5xx)
            is_retryable = status_code == 429 or status_code >= 500
            if not is_retryable or attempt > MAX_PROVIDER_RETRIES:
                raise status_exc

            # Determine sleep time (respect Retry-After if 429)
            sleep_time = None
            if status_code == 429 and hasattr(status_exc, "response") and status_exc.response:
                retry_after_header = status_exc.response.headers.get("Retry-After")
                if retry_after_header:
                    try:
                        sleep_time = float(retry_after_header)
                    except ValueError:
                        pass

            if sleep_time is None:
                sleep_time = (2 ** (attempt - 1)) + random.uniform(0.1, 0.3)

            time.sleep(sleep_time)

        except (APIConnectionError, Exception) as exc:
            # Check if it's a timeout or connection error disguised
            exc_str = str(exc).lower()
            is_timeout_like = "timeout" in exc_str or "timed out" in exc_str
            duration_ms = int((time.time() - start_time) * 1000)
            retry_reason = "timeout" if is_timeout_like else "connection_error"

            log_llm_call(
                prompt_version=prompt_version,
                model=model,
                input_tokens=None,
                output_tokens=None,
                duration_ms=duration_ms,
                repair=is_repair,
                attempt=attempt,
                success=False,
                retry_reason=retry_reason,
            )

            if not is_timeout_like or attempt > MAX_PROVIDER_RETRIES:
                raise exc

            sleep_time = (2 ** (attempt - 1)) + random.uniform(0.1, 0.3)
            time.sleep(sleep_time)
