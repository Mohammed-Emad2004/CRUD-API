import os
from pathlib import Path

import psycopg

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


_load_env()


def get_connection():
    database_url = os.environ["DATABASE_URL"]
    return psycopg.connect(database_url)
