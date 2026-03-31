"""Cấu hình dự án"""

from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):

    # Model
    GEMINI_API_KEY: str
    MODEL_NAME: str = "gemini-3-flash-live"
    LANGUAGE_CODE: str = "vi-VN"

    # Audio configuration
    AUDIO_FORMAT: str = "pcm"
    AUDIO_CHANNELS: int = 1
    SEND_SAMPLE_RATE: int = 16000  # Input to Gemini
    RECEIVE_SAMPLE_RATE: int = 24000  # Output from Gemini

    # server config
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS origins for frontend
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]

    # logging level
    LOG_LEVEL: str = "DEBUG"

    # cấu hình prompt
    CLINIC_NAME: str = "Medical Center"
    SPECIALTY: str = "Primary care and General Medicine"
    GREETING_STYLE: str = "warm"  # warm/professional/friendly
    SYSTEM_INSTRUCTION: str = (
        "You are a professional, calm, and understanding medical assistant. Respond concisely to fit voice communication."
    )

    # voice model
    VOICE_MODEL: str = "Puck"

    # Conversation
    CONVERSATION_STORAGE_PATH: str = "./conversation"
    SAVE_CONVERSATIONS: bool = True

    # sesion log
    ENABLE_SESSION_LOGS: bool = True
    SESSION_LOG_PATH: str = "./session_logs"

    # tools
    ENABLE_TOOLS: bool = True
    TOOLS_PATH: str = "./tools"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
