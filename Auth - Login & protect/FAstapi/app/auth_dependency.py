from fastapi import Header
from fastapi.security import HTTPBearer

from app.auth_error import AuthError
from app.supabase_client import get_supabase

security = HTTPBearer(auto_error=False)


def get_current_user(authorization: str | None = Header(None)):
    if not authorization:
        raise AuthError(status_code=401, detail={"error": "Access token required"})

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer" or not parts[1].strip():
        raise AuthError(status_code=401, detail={"error": "Access token required"})

    token = parts[1].strip()

    try:
        client = get_supabase()
        result = client.auth.get_user(token)
    except Exception:
        raise AuthError(status_code=401, detail={"error": "Invalid or expired token"})

    if result.user is None:
        raise AuthError(status_code=401, detail={"error": "Invalid or expired token"})

    return {"user": result.user, "token": token}
