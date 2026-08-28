import os
import sys
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma3:1b")

if not LLM_API_KEY:
    LLM_API_KEY = "ollama"

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai")
    sys.exit(1)

try:
    client = OpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
    )
except Exception as e:
    print(f"ERROR: Failed to create OpenAI client: {e}")
    sys.exit(1)

try:
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "user", "content": "Reply with exactly the word: ready"}
        ],
        max_tokens=10,
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"ERROR: Failed to call Ollama API: {e}")
    sys.exit(1)
