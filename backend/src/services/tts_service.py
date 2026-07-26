"""TTS service — Edge TTS (primary) + Piper TTS (fallback) with Redis caching."""

import hashlib
import logging
import io

from src.core.redis import redis_client

logger = logging.getLogger(__name__)
CACHE_PREFIX = "tts:"
CACHE_TTL = 30 * 24 * 3600  # 30 days


async def synthesize(text: str, language: str, voice: str = "default", speed: float = 1.0) -> dict:
    """Generate or retrieve cached TTS audio. Returns {audio_url, duration_seconds, cached, engine}."""
    content_hash = hashlib.sha256(f"{text}:{language}:{voice}:{speed}".encode()).hexdigest()
    cache_key = f"{CACHE_PREFIX}{content_hash}"

    # Check cache
    cached = await redis_client.get(cache_key)
    if cached:
        return {"audio_url": f"/api/v1/tts/audio/{content_hash}", "duration_seconds": 0, "cached": True, "engine": "cache"}

    # Generate via Edge TTS (primary)
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice if voice != "default" else _default_voice(language))
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]

        await redis_client.setex(cache_key, CACHE_TTL, audio_bytes)
        return {"audio_url": f"/api/v1/tts/audio/{content_hash}", "duration_seconds": len(audio_bytes) / 16000, "cached": False, "engine": "edge_tts"}

    except Exception as e:
        logger.warning(f"Edge TTS failed: {e}, falling back to Piper")
        # Piper TTS fallback
        try:
            import piper_tts
            audio_bytes = piper_tts.synthesize(text, _piper_model_path(language, voice))
            await redis_client.setex(cache_key, CACHE_TTL, audio_bytes)
            return {"audio_url": f"/api/v1/tts/audio/{content_hash}", "duration_seconds": 0, "cached": False, "engine": "piper_tts"}
        except Exception as e2:
            logger.error(f"Piper TTS also failed: {e2}")
            return {"error": "TTS unavailable", "detail": str(e2)}


async def get_cached_audio(content_hash: str) -> bytes | None:
    """Retrieve cached audio bytes by hash."""
    return await redis_client.get(f"{CACHE_PREFIX}{content_hash}")


def _default_voice(language: str) -> str:
    voices = {"en": "en-US-Emma", "vi": "vi-VN-Mai", "zh": "zh-CN-Xiaoxiao", "ja": "ja-JP-Nanami", "ko": "ko-KR-SunHi", "fr": "fr-FR-Denise", "de": "de-DE-Katja", "es": "es-ES-Elvira"}
    return voices.get(language, "en-US-Emma")


def _piper_model_path(language: str, voice: str) -> str:
    return f"./models/piper/{language}/{voice}.onnx"
