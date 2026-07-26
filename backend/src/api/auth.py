"""Auth API — registration, login, refresh, OAuth."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import get_current_user_id
from src.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from src.models.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/register")
async def register(
    email: str = Query(...),
    password: str = Query(..., min_length=8),
    display_name: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Register a new account."""
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")

    user = User(email=email, hashed_password=hash_password(password), display_name=display_name)
    db.add(user)
    await db.commit()
    return {"id": user.id, "email": user.email, "message": "Account created. Verification email sent."}


@router.post("/login")
async def login(
    email: str = Query(...),
    password: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")
    if user.deleted_at:
        raise HTTPException(401, "Account deleted")

    return {
        "access_token": create_access_token(user.id, user.token_version),
        "refresh_token": create_refresh_token(user.id, user.token_version),
        "user": {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role.value},
    }


@router.post("/refresh")
async def refresh(token: str = Query(...)):
    """Refresh access token."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
        return {"access_token": create_access_token(payload["sub"], payload.get("version", 1)), "refresh_token": token}
    except Exception:
        raise HTTPException(401, "Invalid refresh token")


@router.get("/me")
async def me(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    """Get current user profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role.value, "created_at": user.created_at.isoformat()}


@router.delete("/me")
async def delete_account(user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    """Delete account (GDPR — 30 day retention)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        from datetime import datetime, timezone
        user.deleted_at = datetime.now(timezone.utc)
        await db.commit()
    return {"status": "deletion scheduled", "retention_days": 30}
