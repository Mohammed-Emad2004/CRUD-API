from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth_dependency import get_current_user, security
from app.models import AuthRequest, AuthResponse
from app.supabase_client import get_supabase

auth_router = APIRouter(prefix="/auth")


@auth_router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=201,
    summary="Sign up a new user",
    description="Creates a new user account with Supabase Auth.",
)
async def signup(body: AuthRequest):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    client = get_supabase()

    try:
        result = client.auth.sign_up({"email": body.email, "password": body.password})
    except Exception as e:
        message = str(e)
        if "rate limit" in message.lower():
            raise HTTPException(status_code=400, detail="Signup request rate limited. Please try again later.")
        if "already registered" in message.lower() or "already been registered" in message.lower():
            raise HTTPException(status_code=400, detail="A user with this email already exists.")
        raise HTTPException(status_code=400, detail=message or "Signup failed")

    if result.session is None:
        return AuthResponse(
            message="Signup successful. Please confirm your email.",
        )

    return AuthResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
    )


@auth_router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in an existing user",
    description="Authenticates a user with email and password via Supabase Auth.",
)
async def login(body: AuthRequest):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    client = get_supabase()

    try:
        result = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        message = str(e)
        if "invalid login credentials" in message.lower():
            raise HTTPException(status_code=401, detail="Invalid login credentials")
        raise HTTPException(status_code=401, detail=message or "Login failed")

    return AuthResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
    )


@auth_router.post(
    "/logout",
    status_code=204,
    summary="Log out the current user",
    description="Invalidates the current session. Requires a valid Bearer token.",
    dependencies=[Depends(security)],
)
async def logout(auth=Depends(get_current_user)):
    client = get_supabase()
    client.auth.sign_out(auth["token"])
    return Response(status_code=204)
