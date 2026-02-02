"""
Text-to-Speech Service using Google Cloud TTS
Provides TTS functionality with caching to minimize API calls and costs.
"""
import os
import json
import hashlib
import tempfile
from pathlib import Path
from typing import Optional
from google.cloud import texttospeech
import logging

logger = logging.getLogger(__name__)

class TTSService:
    def __init__(self, cache_dir: str = "tts_cache"):
        """
        Initialize TTS service with Google Cloud credentials.
        
        Args:
            cache_dir: Directory to store cached audio files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Stats tracking
        self.api_calls = 0
        self.cache_hits = 0
        self.total_characters = 0
        
        # Initialize Google Cloud TTS client
        # Supports two auth methods:
        # 1. GOOGLE_APPLICATION_CREDENTIALS env var pointing to JSON file (local dev)
        # 2. GOOGLE_APPLICATION_CREDENTIALS_JSON env var with JSON content (Fly.io)
        try:
            # Check if credentials JSON is provided as environment variable (Fly.io)
            creds_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            if creds_json:
                # Write credentials to temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    f.write(creds_json)
                    temp_creds_path = f.name
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_creds_path
                logger.info("Using credentials from GOOGLE_APPLICATION_CREDENTIALS_JSON")
            
            self.client = texttospeech.TextToSpeechClient()
            self.enabled = True
            logger.info("Google Cloud TTS initialized successfully")
        except Exception as e:
            logger.warning(f"Google Cloud TTS not configured: {e}. Service will be disabled.")
            self.client = None
            self.enabled = False
    
    def _get_cache_filename(self, text: str, language_code: str, voice_name: Optional[str]) -> str:
        """Generate a unique cache filename based on text and settings."""
        cache_key = f"{text}_{language_code}_{voice_name or 'default'}"
        hash_value = hashlib.md5(cache_key.encode()).hexdigest()
        return f"{hash_value}.mp3"
    
    def _is_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters."""
        return any('\u4e00' <= char <= '\u9fff' for char in text)
    
    def synthesize_speech(
        self, 
        text: str,
        language_code: Optional[str] = None,
        voice_name: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Synthesize speech using Google Cloud TTS.
        Returns cached audio if available, otherwise generates new audio.
        
        Args:
            text: The text to synthesize
            language_code: Language code (e.g., 'en-US', 'zh-CN'). Auto-detected if None.
            voice_name: Specific voice name. Uses default if None.
            
        Returns:
            Audio content as bytes (MP3 format) or None if service is disabled
        """
        if not self.enabled:
            return None
        
        # Auto-detect language if not specified
        if language_code is None:
            language_code = 'zh-CN' if self._is_chinese(text) else 'en-US'
        
        # Check cache first
        cache_file = self.cache_dir / self._get_cache_filename(text, language_code, voice_name)
        if cache_file.exists():
            self.cache_hits += 1
            logger.info(f"Serving cached TTS for: {text}")
            return cache_file.read_bytes()
        
        try:
            # Set up synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure voice
            if voice_name:
                voice = texttospeech.VoiceSelectionParams(
                    language_code=language_code,
                    name=voice_name
                )
            else:
                # Use default high-quality voices
                if language_code.startswith('zh'):
                    # For Chinese, use Neural2 or Wavenet voices for better quality
                    voice = texttospeech.VoiceSelectionParams(
                        language_code=language_code,
                        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
                    )
                else:
                    # For English, use Neural2 voices
                    voice = texttospeech.VoiceSelectionParams(
                        language_code=language_code,
                        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
                    )
            
            # Configure audio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,  # Normal speed
                pitch=0.0,  # Normal pitch
                volume_gain_db=0.0,  # Normal volume
            )
            
            # Perform TTS request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Cache the audio
            cache_file.write_bytes(response.audio_content)
            
            # Update stats
            self.api_calls += 1
            self.total_characters += len(text)
            logger.info(f"Generated and cached TTS for: {text}")
            
            return response.audio_content
            
        except Exception as e:
            logger.error(f"Error generating TTS for '{text}': {e}")
            return None
    
    def get_available_voices(self, language_code: Optional[str] = None):
        """
        Get list of available voices from Google Cloud TTS.
        
        Args:
            language_code: Filter by language code (e.g., 'en-US', 'zh-CN')
            
        Returns:
            List of voice information or empty list if service disabled
        """
        if not self.enabled:
            return []
        
        try:
            voices = self.client.list_voices(language_code=language_code)
            return [
                {
                    "name": voice.name,
                    "language_codes": voice.language_codes,
                    "gender": texttospeech.SsmlVoiceGender(voice.ssml_gender).name,
                    "natural_sample_rate": voice.natural_sample_rate_hertz
                }
                for voice in voices.voices
            ]
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
            return []
    
    def clear_cache(self):
        """Clear all cached audio files."""
        for cache_file in self.cache_dir.glob("*.mp3"):
            cache_file.unlink()
        logger.info("TTS cache cleared")
    
    def get_stats(self):
        """Get usage statistics."""
        cache_files = list(self.cache_dir.glob("*.mp3"))
        cache_size_bytes = sum(f.stat().st_size for f in cache_files)
        cache_size_mb = cache_size_bytes / (1024 * 1024)
        
        total_requests = self.api_calls + self.cache_hits
        cache_hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        # Estimate cost (Google Cloud TTS pricing)
        # Standard voices: $4 per 1M characters
        # WaveNet/Neural2: $16 per 1M characters
        # Using $16 as conservative estimate
        estimated_cost = (self.total_characters / 1_000_000) * 16
        free_tier_remaining = max(0, 4_000_000 - self.total_characters)
        
        return {
            "enabled": self.enabled,
            "api_calls": self.api_calls,
            "cache_hits": self.cache_hits,
            "total_requests": total_requests,
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "total_characters_processed": self.total_characters,
            "cached_files_count": len(cache_files),
            "cache_size_mb": round(cache_size_mb, 2),
            "cache_size_bytes": cache_size_bytes,
            "estimated_cost_usd": round(estimated_cost, 4),
            "free_tier_characters_remaining": free_tier_remaining,
            "within_free_tier": self.total_characters <= 4_000_000
        }


# Global instance
tts_service = TTSService()
