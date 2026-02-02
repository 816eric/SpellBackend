"""
Text-to-Speech API Routes
Provides endpoints for generating and serving TTS audio.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import logging

from ..services.tts_service import tts_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str
    language_code: Optional[str] = None
    voice_name: Optional[str] = None


@router.get("/speak")
async def speak(
    text: str = Query(..., description="Text to synthesize"),
    lang: Optional[str] = Query(None, description="Language code (e.g., en-US, zh-CN)"),
    voice: Optional[str] = Query(None, description="Specific voice name")
):
    """
    Generate speech from text using Google Cloud TTS.
    Returns MP3 audio file.
    
    If Google Cloud TTS is not configured, returns 503.
    Frontend should fallback to browser TTS.
    """
    if not tts_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="TTS service not available. Please configure Google Cloud credentials."
        )
    
    if not text or len(text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
    
    try:
        audio_content = tts_service.synthesize_speech(
            text=text,
            language_code=lang,
            voice_name=voice
        )
        
        if audio_content is None:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
        
        # Create a safe filename (avoid encoding issues with Chinese characters in headers)
        safe_filename = f"tts_{hash(text) % 10000}.mp3"
        
        return Response(
            content=audio_content,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=31536000",  # Cache for 1 year
                "Content-Disposition": f'inline; filename="{safe_filename}"'
            }
        )
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@router.post("/speak")
async def speak_post(request: TTSRequest):
    """
    Generate speech from text (POST version for longer texts).
    Returns MP3 audio file.
    """
    if not tts_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="TTS service not available. Please configure Google Cloud credentials."
        )
    
    if not request.text or len(request.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if len(request.text) > 5000:
        raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
    
    try:
        audio_content = tts_service.synthesize_speech(
            text=request.text,
            language_code=request.language_code,
            voice_name=request.voice_name
        )
        
        if audio_content is None:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
        
        return Response(
            content=audio_content,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=31536000",
                "Content-Disposition": f'inline; filename="{request.text[:30]}.mp3"'
            }
        )
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@router.get("/voices")
async def get_voices(lang: Optional[str] = Query(None, description="Language code filter")):
    """
    Get list of available voices from Google Cloud TTS.
    """
    if not tts_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="TTS service not available"
        )
    
    voices = tts_service.get_available_voices(language_code=lang)
    return {"voices": voices}


@router.get("/status")
async def get_status():
    """
    Check if TTS service is available.
    """
    return {
        "enabled": tts_service.enabled,
        "service": "Google Cloud Text-to-Speech"
    }


@router.get("/stats")
async def get_stats():
    """
    Get TTS usage statistics including API calls, cache performance, and cost estimates.
    Useful for monitoring usage and staying within free tier limits.
    """
    return tts_service.get_stats()
