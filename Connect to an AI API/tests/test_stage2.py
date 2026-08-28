import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_prompt_loading():
    from src.main import load_enrich_prompt
    prompt = load_enrich_prompt()
    assert "# Role and Job" in prompt
    assert "fiction" in prompt
    assert "quality_flags" in prompt

def test_enrich_endpoint_integration_unstubbed():
    os.environ["LLM_STUB"] = "0"
    from src.main import app
    # Re-create client to pick up env var change if needed, but TestClient reads app
    local_client = TestClient(app)

    payload1 = {
        "title": "A Light in the Attic",
        "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "price_gbp": 51.77,
        "availability": 22,
        "rating": 3,
        "description": "This now-classic collection of poetry and drawings from Shel Silverstein celebrates its 20th anniversary with this special edition.",
        "source_page": "https://books.toscrape.com/catalogue/page-1.html",
        "fetched_at": "2026-08-19T11:58:56.741061+00:00"
    }

    response = local_client.post("/enrich", json=payload1)
    assert response.status_code == 200
    data = response.json()
    assert "category" in data
    assert "summary" in data

    os.environ["LLM_STUB"] = "1"

if __name__ == "__main__":
    test_prompt_loading()
    test_enrich_endpoint_integration_unstubbed()
    print("Stage 2 manual tests completed successfully!")
