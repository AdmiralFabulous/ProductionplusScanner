"""
EYESON - Voice AI API Endpoints

Open Source TTS using Kokoro-82M (Apache 2.0)
Provides voice guidance for the 90-second body scan experience.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path as FastApiPath, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.core.config import settings
from src.services.tts_service import tts_service

logger = logging.getLogger(__name__)
router = APIRouter()


class TTSSynthesizeRequest(BaseModel):
    """TTS synthesis request."""
    text: str = Field(..., min_length=1, max_length=500, description="Text to synthesize")
    voice: Optional[str] = Field(default=None, description="Voice ID")
    speed: Optional[float] = Field(default=None, ge=0.5, le=2.0, description="Speaking speed")
    stream: bool = Field(default=False, description="Stream audio chunks")


class TTSResponse(BaseModel):
    """TTS synthesis response."""
    success: bool
    audio_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    voice_used: str
    cached: bool


class VoicePromptLibrary(BaseModel):
    """Voice prompt library response."""
    language: str
    prompts: dict


# Voice prompt library for the 90-second scan experience
VOICE_PROMPTS = {
    "en": {
        "welcome": "Welcome to EYESON BodyScan. I'm your AI guide. In the next 90 seconds, I'll help you capture your measurements with professional accuracy. Let's begin.",
        "consent": "Your privacy matters. Your video is processed securely and deleted within 24 hours. Only your measurements are stored. Tap continue to proceed.",
        "device_setup": "First, place your phone against a wall or on a stable surface, about 6 feet from where you'll stand. Make sure the camera can see your full body.",
        "calibration": "Great! Now place the calibration card on the floor where you'll stand. It helps us measure accurately. Hold it flat and visible to the camera.",
        "positioning": "Perfect! Step back onto the card. Stand naturally with arms slightly away from your body. Look straight ahead. You should see a green skeleton overlay. When ready, the scan will begin automatically.",
        "capture_start": "Excellent position! Starting scan in 3, 2, 1. Please turn slowly to your left. Keep turning... nice and steady.",
        "capture_progress_1": "Keep turning, you're doing great. About halfway there.",
        "capture_progress_2": "Almost complete. Maintain your posture.",
        "capture_progress_3": "Final few seconds. Hold that position.",
        "capture_complete": "Perfect! Scan complete. Now let me process your measurements. This takes about 20 seconds.",
        "processing": "Building your 3D model... extracting measurements... nearly done.",
        "results": "All done! Your measurements are ready. You can review them on screen or have them sent to your tailor.",
        "error_lighting": "I notice the lighting is a bit dim. Try moving closer to a window or turning on more lights, then tap retry.",
        "error_position": "I can't see your full body. Please step back a bit further and make sure you're completely in the camera view.",
        "error_speed": "You turned a bit too quickly. Let's try again - turn slowly and steadily, like a rotating display.",
        "error_general": "Something didn't work quite right. Let's try that step again. Tap retry when ready.",
    },
    "es": {
        "welcome": "Bienvenido a EYESON BodyScan. Soy tu guía de IA. En los próximos 90 segundos, te ayudaré a capturar tus medidas con precisión profesional. Comencemos.",
        "consent": "Tu privacidad es importante. Tu video se procesa de forma segura y se elimina en 24 horas. Solo se almacenan tus medidas. Toca continuar para proceder.",
        "device_setup": "Primero, coloca tu teléfono contra una pared o sobre una superficie estable, a unos 2 metros de donde te pararás. Asegúrate de que la cámara pueda ver tu cuerpo completo.",
        "capture_start": "¡Excelente posición! Comenzando escaneo en 3, 2, 1. Gira lentamente hacia tu izquierda. Sigue girando... nice and steady.",
        "results": "¡Listo! Tus medidas están listas. Puedes revisarlas en la pantalla o enviarlas a tu sastre.",
    },
    "fr": {
        "welcome": "Bienvenue sur EYESON BodyScan. Je suis votre guide IA. Dans les 90 prochaines secondes, je vous aiderai à capturer vos mesures avec une précision professionnelle. Commençons.",
        "consent": "Votre vie privée est importante. Votre vidéo est traitée en toute sécurité et supprimée sous 24 heures. Seules vos mesures sont stockées. Appuyez sur continuer pour procéder.",
        "results": "Terminé! Vos mesures sont prêtes. Vous pouvez les consulter à l'écran ou les envoyer à votre tailleur.",
    }
}


@router.get("/voice/health")
async def voice_health():
    """Check voice service health."""
    health = await tts_service.health_check()
    return health


@router.get("/voice/voices")
async def list_voices():
    """List available TTS voices."""
    voices = tts_service.get_voices()
    return {
        "primary_engine": "Kokoro-82M (Apache 2.0)" if voices["primary"] else None,
        "fallback_engine": "Piper TTS (MIT)" if voices["fallback"] else None,
        "voices": voices
    }


@router.post("/voice/synthesize", response_model=TTSResponse)
async def synthesize_speech(request: TTSSynthesizeRequest):
    """
    Synthesize speech from text using open source TTS.
    
    Uses Kokoro-82M (Apache 2.0) as primary engine.
    Falls back to Piper TTS (MIT) if needed.
    """
    try:
        audio_data = await tts_service.synthesize(
            text=request.text,
            voice=request.voice,
            speed=request.speed,
            use_cache=True
        )
        
        # Return audio as downloadable file
        # In production, this would be a URL to stored audio
        return TTSResponse(
            success=True,
            audio_url=f"/api/v1/voice/audio/{hash(request.text)}",
            duration_seconds=len(audio_data) / (22050 * 2),  # Approximate duration
            voice_used=request.voice or settings.tts_voice,
            cached=False
        )
        
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS synthesis failed: {str(e)}"
        )


@router.post("/voice/synthesize/stream")
async def synthesize_speech_stream(request: TTSSynthesizeRequest):
    """
    Stream synthesized speech as audio chunks.
    
    Returns audio as WAV stream for real-time playback.
    """
    try:
        async def audio_stream():
            async for chunk in tts_service.synthesize_stream(
                text=request.text,
                voice=request.voice,
                speed=request.speed
            ):
                yield chunk
        
        return StreamingResponse(
            audio_stream(),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"inline; filename=\"speech_{hash(request.text)}.wav\""
            }
        )
        
    except Exception as e:
        logger.error(f"TTS streaming failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS streaming failed: {str(e)}"
        )


@router.get("/voice/prompts/{language}", response_model=VoicePromptLibrary)
async def get_voice_prompts(
    language: str = FastApiPath(..., pattern="^[a-z]{2}$"),
    section: Optional[str] = Query(None, description="Filter by section (welcome, capture, etc.)")
):
    """
    Get voice prompt library for a specific language.
    
    Returns all voice prompts for the 90-second scan experience.
    """
    if language not in VOICE_PROMPTS:
        available = list(VOICE_PROMPTS.keys())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language '{language}' not available. Available: {available}"
        )
    
    prompts = VOICE_PROMPTS[language]
    
    if section:
        prompts = {k: v for k, v in prompts.items() if section in k}
    
    return VoicePromptLibrary(
        language=language,
        prompts=prompts
    )


@router.get("/voice/prompts/{language}/{prompt_id}")
async def get_single_prompt(language: str, prompt_id: str):
    """Get a single voice prompt by ID."""
    if language not in VOICE_PROMPTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language '{language}' not available"
        )
    
    if prompt_id not in VOICE_PROMPTS[language]:
        available = list(VOICE_PROMPTS[language].keys())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{prompt_id}' not found. Available: {available}"
        )
    
    return {
        "language": language,
        "prompt_id": prompt_id,
        "text": VOICE_PROMPTS[language][prompt_id]
    }


@router.post("/voice/prompts/{language}/{prompt_id}/speak")
async def speak_prompt(
    language: str,
    prompt_id: str,
    voice: Optional[str] = Query(None),
    speed: Optional[float] = Query(1.0, ge=0.5, le=2.0)
):
    """
    Speak a predefined prompt.
    
    Combines prompt retrieval + TTS synthesis in one call.
    """
    # Get prompt text
    if language not in VOICE_PROMPTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Language '{language}' not available"
        )
    
    if prompt_id not in VOICE_PROMPTS[language]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{prompt_id}' not found"
        )
    
    text = VOICE_PROMPTS[language][prompt_id]
    
    # Synthesize
    try:
        audio_data = await tts_service.synthesize(
            text=text,
            voice=voice,
            speed=speed,
            use_cache=True
        )
        
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"inline; filename=\"{prompt_id}_{language}.wav\"",
                "X-Prompt-Text": text[:100]  # Header for debugging
            }
        )
        
    except Exception as e:
        logger.error(f"Prompt synthesis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synthesis failed: {str(e)}"
        )


@router.post("/voice/cache/clear")
async def clear_tts_cache():
    """Clear TTS audio cache (admin only)."""
    # This would require admin authentication in production
    tts_service.cache.clear()
    return {"message": "TTS cache cleared", "cache_size": len(tts_service.cache)}
