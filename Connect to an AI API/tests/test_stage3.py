import os
import sys
import json
from pathlib import Path
from unittest.mock import patch

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


def test_valid_json_response_200():
    os.environ["LLM_STUB"] = "0"
    valid_resp = json.dumps({"category": "poetry", "summary": "A poetry book.", "quality_flags": []})
    with patch("src.main.execute_llm_call_with_retries") as mock_exec:
        mock_exec.return_value = (valid_resp, 200)

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "poetry"
        # Verify exactly one call (no repair)
        assert mock_exec.call_count == 1


def test_json_inside_markdown_fences():
    os.environ["LLM_STUB"] = "0"
    fenced_resp = "Here is the result:\n```json\n{\"category\": \"fiction\", \"summary\": \"A fiction book.\", \"quality_flags\": []}\n```"
    with patch("src.main.execute_llm_call_with_retries") as mock_exec:
        mock_exec.return_value = (fenced_resp, 200)

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "fiction"
        assert mock_exec.call_count == 1


def test_json_with_harmless_surrounding_text():
    os.environ["LLM_STUB"] = "0"
    surrounded_resp = "Sure! {\"category\": \"mystery\", \"summary\": \"A mystery book.\", \"quality_flags\": []} Hope this helps."
    with patch("src.main.execute_llm_call_with_retries") as mock_exec:
        mock_exec.return_value = (surrounded_resp, 200)

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "mystery"
        assert mock_exec.call_count == 1


def test_malformed_json_triggers_one_repair_success():
    os.environ["LLM_STUB"] = "0"
    bad_resp = "not json at all"
    good_repair = json.dumps({"category": "children", "summary": "A children book.", "quality_flags": []})

    with patch("openai.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = [
            type("obj", (object,), {"choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": bad_resp})})]})(),
            type("obj", (object,), {"choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": good_repair})})]})(),
        ]

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "children"
        assert mock_client.chat.completions.create.call_count == 2


def test_invalid_category_triggers_one_repair_success():
    os.environ["LLM_STUB"] = "0"
    invalid_cat_resp = json.dumps({"category": "invalid_cat_name", "summary": "Bad category.", "quality_flags": []})
    good_repair = json.dumps({"category": "romance", "summary": "A romance book.", "quality_flags": []})

    with patch("openai.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = [
            type("obj", (object,), {"choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": invalid_cat_resp})})]})(),
            type("obj", (object,), {"choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": good_repair})})]})(),
        ]

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "romance"
        assert mock_client.chat.completions.create.call_count == 2


def test_first_and_repair_invalid_returns_422_and_quarantines():
    os.environ["LLM_STUB"] = "0"
    bad_resp_1 = "bad json 1"
    bad_resp_2 = "bad json 2"

    quarantine_path = Path("logs/quarantine.jsonl")
    initial_lines = 0
    if quarantine_path.exists():
        with open(quarantine_path, "r", encoding="utf-8") as f:
            initial_lines = len(f.readlines())

    with patch("openai.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = [
            type("obj", (object,), {"choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": bad_resp_1})})]})(),
            type("obj", (object,), {"choices": [type("obj", (object,), {"message": type("obj", (object,), {"content": bad_resp_2})})]})(),
        ]

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 422
        data = response.json()
        # Verify raw model text is never returned in 422 response
        assert "bad json" not in str(data)
        assert "error" in data

        # Verify exactly one new quarantine entry written
        assert quarantine_path.exists()
        with open(quarantine_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == initial_lines + 1
            last_record = json.loads(lines[-1])
            assert last_record["raw_model_output"] == bad_resp_1
            assert last_record["repair_raw_output"] == bad_resp_2


def test_llm_call_failure_does_not_trigger_repair():
    os.environ["LLM_STUB"] = "0"
    with patch("openai.OpenAI") as mock_openai:
        mock_client = mock_openai.return_value
        # Simulate connection/API failure on initial call
        mock_client.chat.completions.create.side_effect = Exception("Ollama unavailable")

        response = client.post("/enrich", json=VALID_PAYLOAD)
        assert response.status_code == 500
        # Verify exactly one call was made (no repair attempt initiated)
        assert mock_client.chat.completions.create.call_count == 1
