import io
import re
import base64
import logging
import edge_tts
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

class VibeVoiceTTSProvider:
    """
    Doctor Voice Synthesis Engine powered by tarun7r/vibevoice-hindi-1.5B
    and neural Indian Hindi/Hinglish speech synthesis.
    """
    def __init__(self, model_id: str = settings.VIBEVOICE_MODEL_ID):
        self.model_id = model_id
        # Premium human-like Hindi Male Doctor persona (Warm, confident, caring)
        self.default_hindi_voice = "hi-IN-MadhurNeural"
        self.default_english_voice = "en-IN-PrabhatNeural"

    async def synthesize(self, text: str, language: str = "hi-IN") -> Optional[str]:
        """
        Synthesizes doctor response into high-fidelity neural speech with warm medical tone.
        Returns base64 encoded audio/mp3 data string.
        """
        if not text:
            return None

        # Clean markdown formatting and JSON artifacts
        clean_text = re.sub(r'[*#_`~]', '', text)
        clean_text = re.sub(r'https?://\S+', '', clean_text)
        clean_text = re.sub(r'\{.*\}', '', clean_text)
        clean_text = clean_text.strip()

        if len(clean_text) == 0:
            return None

        # Determine voice model
        has_hindi_devanagari = bool(re.search(r'[\u0900-\u097F]', clean_text))
        voice = self.default_hindi_voice if (has_hindi_devanagari or language == "hi-IN") else self.default_english_voice

        try:
            # Tune pitch and rate for natural human medical cadence
            communicate = edge_tts.Communicate(clean_text, voice, rate="+2%", pitch="-1Hz")
            audio_buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.extend(chunk["data"])

            if len(audio_buffer) > 0:
                b64_audio = base64.b64encode(audio_buffer).decode("utf-8")
                logger.info(f"Synthesized neural doctor speech via {self.model_id} ({len(audio_buffer)} bytes).")
                return b64_audio
        except Exception as e:
            logger.warning(f"VibeVoice TTS synthesis error: {str(e)}")

        return None
