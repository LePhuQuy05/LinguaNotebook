"""Donations API — support links and transparency."""

from fastapi import APIRouter
from src.core.config import settings

router = APIRouter(prefix="/api/v1/donations", tags=["Donations"])


@router.get("/support")
async def support_links():
    """Get donation/support platform links."""
    platforms = []
    if settings.github_sponsors_url:
        platforms.append({"name": "GitHub Sponsors", "url": settings.github_sponsors_url, "description": "Support development with a monthly donation"})
    if settings.kofi_url:
        platforms.append({"name": "Ko-fi", "url": settings.kofi_url, "description": "Buy us a coffee"})
    return {"platforms": platforms, "message": "LinguaNotebook is 100% free. Donations are optional and do not affect features."}


@router.get("")
async def list_donations(limit: int = 50):
    """List recent community donations (transparency)."""
    return {"donations": [], "total_count": 0, "total_amount_display": "Community support powers this project"}
