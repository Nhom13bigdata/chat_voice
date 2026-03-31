"""Audio processing utilities"""

import logging

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Audio processing utilities for testing/debugging"""

    def __init__(self, sample_rate=16000, channels=1, sample_width=2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width  # bytes per sample

    def validate_audio_chunk(self, audio_data: bytes) -> bool:
        """Validate audio chunk format"""
        if not audio_data:
            return False

        # Check if size is aligned with sample width
        if len(audio_data) % self.sample_width != 0:
            logger.warning(
                f"Audio chunk size {len(audio_data)} not aligned with sample width {self.sample_width}"
            )
            return False

        return True

    def get_audio_duration(self, audio_data: bytes) -> float:
        """Calculate duration in seconds"""
        if not audio_data:
            return 0.0

        num_samples = len(audio_data) // self.sample_width
        duration = num_samples / self.sample_rate
        return duration

    def detect_silence(self, audio_data: bytes, threshold: int = 500) -> bool:
        """Detect if audio chunk is silence"""
        if not audio_data:
            return True

        # Convert bytes to amplitude values (simplified)
        amplitudes = [
            abs(int.from_bytes(audio_data[i : i + 2], "little", signed=True))
            for i in range(0, len(audio_data), 2)
        ]

        avg_amplitude = sum(amplitudes) / len(amplitudes)
        return avg_amplitude < threshold


# Global instance
audio_processor = AudioProcessor()
