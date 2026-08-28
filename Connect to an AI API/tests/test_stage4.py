import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "title": "A Light in the Attic",
    "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
    "price_gbp": 51.77,
    "availability": 22,
    "rating": 3,
    "description": "A sample book description.",
    "source_page": "https://books.toscrape.com/catalogue/page-1.html",
    "fetched_at": "2026-08-19T11:58:56.741061+00:00",
}


def test_1_timeout_succeeds_after_retry():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    from openai import APITimeoutError
    
    success_resp = json.dumps({"category": "poetry", "summary": "A poetry book.", "quality_flags": []})
    
    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        # First call raises APITimeoutError, second call succeeds
        mock_create.side_effect = [
            APITimeoutError(request=MagicMock()),
            type("obj", (object,), {
                "choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": success_resp})})],
                "usage": type("obj", (object,), {"prompt_tokens": 10, "completion_tokens": 5})
            })
        ]

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "poetry"
        assert mock_create.call_count == 2


def test_2_timeout_exhausted():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    from openai import APITimeoutError

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_create.side_effect = APITimeoutError(request=MagicMock())

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 504
        # max 2 retries -> 3 total attempts
        assert mock_create.call_count == 3


def test_3_500_then_success():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    from openai import APIStatusError

    success_resp = json.dumps({"category": "fiction", "summary": "A fiction book.", "quality_flags": []})

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_create.side_effect = [
            APIStatusError("Internal Server Error", response=mock_resp, body=None),
            type("obj", (object,), {
                "choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": success_resp})})],
                "usage": None
            })
        ]

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200
        assert response.json()["category"] == "fiction"
        assert mock_create.call_count == 2


def test_4_repeated_500():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    from openai import APIStatusError

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_create.side_effect = APIStatusError("Internal Server Error", response=mock_resp, body=None)

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 500
        assert mock_create.call_count == 3


def test_5_429_with_retry_after():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    from openai import APIStatusError

    success_resp = json.dumps({"category": "mystery", "summary": "A mystery book.", "quality_flags": []})

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "0.01"}
        mock_create.side_effect = [
            APIStatusError("Too Many Requests", response=mock_resp, body=None),
            type("obj", (object,), {
                "choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": success_resp})})],
                "usage": None
            })
        ]

        with patch("time.sleep") as mock_sleep:
            response = client.post("/enrich", json=VALID_PAYLOAD)
            assert response.status_code == 200
            assert response.json()["category"] == "mystery"
            assert mock_create.call_count == 2
            mock_sleep.assert_called_with(0.01)


def test_6_401_no_retry():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    from openai import APIStatusError

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_create.side_effect = APIStatusError("Unauthorized", response=mock_resp, body=None)

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 401
        assert mock_create.call_count == 1


def test_7_403_no_retry():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    from openai import APIStatusError

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_create.side_effect = APIStatusError("Forbidden", response=mock_resp, body=None)

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 403
        assert mock_create.call_count == 1


def test_8_400_no_retry():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    from openai import APIStatusError

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_create.side_effect = APIStatusError("Bad Request", response=mock_resp, body=None)

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 400
        assert mock_create.call_count == 1


def test_9_llm_enabled_false():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "false"

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "other"
        assert "disabled" in data["summary"].lower()
        assert mock_create.call_count == 0


def test_10_usage_logging():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    success_resp = json.dumps({"category": "poetry", "summary": "Poetry.", "quality_flags": []})

    log_file = Path("logs/llm_calls.jsonl")
    initial_lines = 0
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            initial_lines = len(f.readlines())

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_create.return_value = type("obj", (object,), {
            "choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": success_resp})})],
            "usage": type("obj", (object,), {"prompt_tokens": 123, "completion_tokens": 45})
        })()

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200

        assert log_file.exists()
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) >= initial_lines + 1
            entry = json.loads(lines[-1])
            assert entry["prompt_version"] == "enrich-v1.md"
            assert entry["model"] == "gemma3:1b"
            assert entry["input_tokens"] == 123
            assert entry["output_tokens"] == 45
            assert "duration_ms" in entry
            assert entry["repair"] is False
            assert entry["success"] is True


def test_11_provider_without_usage_metadata():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    success_resp = json.dumps({"category": "poetry", "summary": "Poetry.", "quality_flags": []})

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_create.return_value = type("obj", (object,), {
            "choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": success_resp})})],
            "usage": None
        })()

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200
        assert response.json()["category"] == "poetry"


def test_12_stage_3_regression_malformed_then_repair():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    bad_resp = "not json"
    good_resp = json.dumps({"category": "children", "summary": "Children.", "quality_flags": []})

    with patch("openai.resources.chat.completions.Completions.create") as mock_create:
        mock_create.side_effect = [
            type("obj", (object,), {
                "choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": bad_resp})})],
                "usage": type("obj", (object,), {"prompt_tokens": 10, "completion_tokens": 5})
            })(),
            type("obj", (object,), {
                "choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": good_resp})})],
                "usage": type("obj", (object,), {"prompt_tokens": 15, "completion_tokens": 8})
            })()
        ]

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200
        assert response.json()["category"] == "children"
        assert mock_create.call_count == 2


def test_13_stage_3_repair_provider_failure():
    os.environ["LLM_STUB"] = "0"
    os.environ["LLM_ENABLED"] = "true"
    from openai import APITimeoutError
    bad_resp = "not json"

    with patch("src.main.execute_llm_call_with_retries") as mock_exec:
        # First call succeeds with bad JSON, repair call raises APITimeoutError
        mock_exec.side_effect = [
            (bad_resp, 200),
            APITimeoutError(request=MagicMock())
        ]

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 504
