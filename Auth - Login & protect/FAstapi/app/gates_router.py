from fastapi import APIRouter, Depends

from app.auth_dependency import get_current_user, security

gates_router = APIRouter()


@gates_router.get(
    "/public/info",
    summary="Public information",
    description="Returns a public message. No authentication required.",
)
async def public_info():
    return {"message": "Welcome stranger! This info is public."}


@gates_router.get(
    "/protected/profile",
    summary="Protected profile",
    description="Returns verified user profile. Requires a valid Bearer token.",
    dependencies=[Depends(security)],
)
async def protected_profile(auth=Depends(get_current_user)):
    user = auth["user"]
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }


@gates_router.get(
    "/protected/dashboard",
    summary="Protected dashboard",
    description="Returns dashboard data. Requires a valid Bearer token.",
    dependencies=[Depends(security)],
)
async def protected_dashboard(auth=Depends(get_current_user)):
    user = auth["user"]
    return {
        "message": "Welcome to your dashboard",
        "user_id": user.id,
    }
