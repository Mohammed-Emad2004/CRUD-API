import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["LLM_STUB"] = "1"

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


def test_valid_input_stub():
    response = client.post("/enrich", json=VALID_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert "category" in data
    assert "summary" in data
    assert "quality_flags" in data
    assert data["category"] in ["fiction", "nonfiction", "poetry", "children", "mystery", "romance", "other"]
    assert isinstance(data["summary"], str) and len(data["summary"]) > 0
    assert isinstance(data["quality_flags"], list)


def test_missing_required_field():
    payload = VALID_PAYLOAD.copy()
    del payload["title"]
    response = client.post("/enrich", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "field" in data
    assert "title" in data["field"]


def test_invalid_rating():
    payload = VALID_PAYLOAD.copy()
    payload["rating"] = 6
    response = client.post("/enrich", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "field" in data
    assert "rating" in data["field"]


def test_invalid_url():
    payload = VALID_PAYLOAD.copy()
    payload["product_url"] = "not-a-url"
    response = client.post("/enrich", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "field" in data
    assert "product_url" in data["field"]


def test_negative_availability():
    payload = VALID_PAYLOAD.copy()
    payload["availability"] = -1
    response = client.post("/enrich", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "field" in data
    assert "availability" in data["field"]


def test_empty_title():
    payload = VALID_PAYLOAD.copy()
    payload["title"] = ""
    response = client.post("/enrich", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "field" in data
    assert "title" in data["field"]


if __name__ == "__main__":
    print("Running tests...")
    
    tests = [
        test_valid_input_stub,
        test_missing_required_field,
        test_invalid_rating,
        test_invalid_url,
        test_negative_availability,
        test_empty_title,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__} - {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed!")