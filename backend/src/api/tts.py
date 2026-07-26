"""TTS API endpoints."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from src.core.dependencies import get_current_user_id
from src.services import tts_service

router = APIRouter(prefix="/api/v1/tts", tags=["TTS"])


@router.post("/synthesize")
async def synthesize(
    text: str = Query(..., max_length=5000),
    language: str = Query("en"),
    voice: str = Query("default"),
    speed: float = Query(1.0, ge=0.5, le=2.0),
    user_id: str = Depends(get_current_user_id),
):
    """Generate or retrieve cached TTS audio."""
    return await tts_service.synthesize(text, language, voice, speed)


@router.get("/voices")
async def list_voices(
    language: str = Query("en"),
    user_id: str = Depends(get_current_user_id),
):
    """List available voices for a language."""
    voices_map = {
        "en": [{"id": "en-US-Emma", "name": "Emma", "gender": "female", "engine": "edge_tts"}, {"id": "en-US-Eric", "name": "Eric", "gender": "male", "engine": "edge_tts"}],
        "vi": [{"id": "vi-VN-Mai", "name": "Mai", "gender": "female", "engine": "edge_tts"}],
    }
    return voices_map.get(language, [])


@router.get("/audio/{content_hash}")
async def get_audio(content_hash: str):
    """Stream cached audio file."""
    audio = await tts_service.get_cached_audio(content_hash)
    if audio is None:
        return Response(status_code=404)
    return Response(content=audio, media_type="audio/mpeg")
