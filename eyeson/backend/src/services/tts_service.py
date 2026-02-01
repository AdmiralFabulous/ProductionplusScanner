"""
EYESON - Open Source TTS Service

Uses Kokoro-82M as primary TTS (Apache 2.0, browser-ready)
Falls back to Piper TTS for edge cases (MIT license)

Both models are:
- Fully open source
- CPU-friendly
- Sub-300ms latency
- Natural-sounding
"""

import hashlib
import io
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio

import numpy as np

from src.core.config import settings

logger = logging.getLogger(__name__)


class TTSService:
    """
    Text-to-Speech service using open source models.
    
    Primary: Kokoro-82M (ONNX) - Apache 2.0
    Fallback: Piper TTS - MIT License
    """
    
    def __init__(self):
        self.model = None
        self.piper_model = None
        self.cache: Dict[str, bytes] = {}
        self._initialized = False
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Lazy initialization of TTS models."""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:
                return
                
            try:
                await self._load_kokoro()
                self._initialized = True
                logger.info("TTS Service initialized with Kokoro-82M")
            except Exception as e:
                logger.error(f"Failed to load Kokoro, will use fallback: {e}")
                await self._load_piper()
                self._initialized = True
                logger.info("TTS Service initialized with Piper (fallback)")
    
    async def _load_kokoro(self) -> None:
        """Load Kokoro-82M ONNX model."""
        try:
            # Kokoro uses ONNX Runtime - works on CPU efficiently
            import onnxruntime as ort
            
            model_path = settings.sam3d_model_path / "kokoro-82m.onnx"
            
            # Configure ONNX Runtime for optimal CPU performance
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = 4
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            providers = ['CPUExecutionProvider']
            if settings.tts_device == 'cuda' and 'CUDAExecutionProvider' in ort.get_available_providers():
                providers.insert(0, 'CUDAExecutionProvider')
            
            self.model = ort.InferenceSession(
                str(model_path),
                sess_options,
                providers=providers
            )
            
            logger.info(f"Kokoro-82M loaded with providers: {providers}")
            
        except ImportError:
            logger.warning("onnxruntime not available, will use fallback")
            raise
    
    async def _load_piper(self) -> None:
        """Load Piper TTS as fallback."""
        try:
            # Piper is extremely lightweight and fast
            from piper import PiperVoice
            
            model_path = Path(f"./models/piper/{settings.tts_fallback_model}.onnx")
            config_path = model_path.with_suffix('.onnx.json')
            
            self.piper_model = PiperVoice.load(str(model_path), str(config_path))
            logger.info(f"Piper TTS loaded: {settings.tts_fallback_model}")
            
        except ImportError:
            logger.error("Neither Kokoro nor Piper available - TTS will fail")
            raise RuntimeError("No TTS model available")
    
    def _get_cache_key(self, text: str, voice: str, speed: float) -> str:
        """Generate cache key for TTS audio."""
        key_data = f"{text}|{voice}|{speed}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        use_cache: bool = True
    ) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice: Voice ID (default from settings)
            speed: Speaking speed multiplier (0.5-2.0)
            use_cache: Whether to use/cache the result
            
        Returns:
            Audio data as WAV bytes
        """
        await self.initialize()
        
        voice = voice or settings.tts_voice
        speed = speed or settings.tts_speed
        
        # Check cache
        if use_cache and settings.tts_cache_enabled:
            cache_key = self._get_cache_key(text, voice, speed)
            
            # Check memory cache
            if cache_key in self.cache:
                logger.debug(f"TTS cache hit (memory): {text[:30]}...")
                return self.cache[cache_key]
            
            # Check disk cache
            cache_file = settings.tts_cache_dir / f"{cache_key}.wav"
            if cache_file.exists():
                logger.debug(f"TTS cache hit (disk): {text[:30]}...")
                audio_data = cache_file.read_bytes()
                self.cache[cache_key] = audio_data
                return audio_data
        
        # Synthesize
        start_time = asyncio.get_event_loop().time()
        
        try:
            if self.model:
                audio_data = await self._synthesize_kokoro(text, voice, speed)
            else:
                audio_data = await self._synthesize_piper(text, voice, speed)
                
            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"TTS synthesis completed in {elapsed:.3f}s: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise
        
        # Cache result
        if use_cache and settings.tts_cache_enabled:
            cache_key = self._get_cache_key(text, voice, speed)
            self.cache[cache_key] = audio_data
            
            # Also cache to disk
            cache_file = settings.tts_cache_dir / f"{cache_key}.wav"
            cache_file.write_bytes(audio_data)
        
        return audio_data
    
    async def _synthesize_kokoro(self, text: str, voice: str, speed: float) -> bytes:
        """Synthesize using Kokoro-82M."""
        # Run in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._synthesize_kokoro_sync, text, voice, speed
        )
    
    def _synthesize_kokoro_sync(self, text: str, voice: str, speed: float) -> bytes:
        """Synchronous Kokoro synthesis."""
        import onnxruntime as ort
        import scipy.io.wavfile as wav
        
        # Kokoro inference
        # Note: This is a simplified version - actual implementation
        # would use the proper Kokoro tokenizer and phonemizer
        
        inputs = {
            'text': np.array([text], dtype=object),
            'voice': np.array([voice], dtype=object),
            'speed': np.array([speed], dtype=np.float32)
        }
        
        outputs = self.model.run(None, inputs)
        audio = outputs[0]
        
        # Convert to WAV
        buffer = io.BytesIO()
        wav.write(buffer, 22050, audio.astype(np.float32))
        
        return buffer.getvalue()
    
    async def _synthesize_piper(self, text: str, voice: str, speed: float) -> bytes:
        """Synthesize using Piper TTS (fallback)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._synthesize_piper_sync, text, voice, speed
        )
    
    def _synthesize_piper_sync(self, text: str, voice: str, speed: float) -> bytes:
        """Synchronous Piper synthesis."""
        import wave
        
        buffer = io.BytesIO()
        
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            
            # Piper synthesis
            for audio_bytes in self.piper_model.synthesize_stream_raw(text):
                wav_file.writeframes(audio_bytes)
        
        return buffer.getvalue()
    
    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None
    ):
        """
        Stream synthesized audio chunks.
        
        Yields:
            Audio chunks as bytes
        """
        await self.initialize()
        
        voice = voice or settings.tts_voice
        speed = speed or settings.tts_speed
        
        if self.piper_model:
            # Piper supports streaming natively
            for chunk in self.piper_model.synthesize_stream_raw(text):
                yield chunk
        else:
            # Kokoro doesn't stream as naturally, yield full result
            audio = await self.synthesize(text, voice, speed, use_cache=True)
            # Yield in chunks
            chunk_size = 8192
            for i in range(0, len(audio), chunk_size):
                yield audio[i:i + chunk_size]
    
    def get_voices(self) -> list:
        """Get list of available voices."""
        # Kokoro voices
        kokoro_voices = [
            {"id": "af", "name": "American Female", "lang": "en"},
            {"id": "am", "name": "American Male", "lang": "en"},
            {"id": "bf", "name": "British Female", "lang": "en"},
            {"id": "bm", "name": "British Male", "lang": "en"},
        ]
        
        # Piper voices would be loaded from available models
        piper_voices = [
            {"id": "en_US-lessac-medium", "name": "Lessac (US)", "lang": "en"},
            {"id": "en_GB-southern_male-medium", "name": "Southern Male (UK)", "lang": "en"},
        ]
        
        return {
            "primary": kokoro_voices if self.model else [],
            "fallback": piper_voices if self.piper_model else [],
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check TTS service health."""
        return {
            "initialized": self._initialized,
            "primary_model": "Kokoro-82M" if self.model else None,
            "fallback_model": "Piper" if self.piper_model else None,
            "cache_size": len(self.cache),
            "status": "healthy" if self._initialized else "uninitialized"
        }


# Singleton instance
tts_service = TTSService()
