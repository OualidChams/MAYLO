"""
Application settings — read from environment variables (.env locally,
or from Railway/Supabase in production).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # -- App --
    environment: str = "development"
    app_name: str = "Restaurant AI Agent"

    # -- Database (Supabase Postgres) --
    # example: postgresql+asyncpg://user:password@host:5432/postgres
    database_url: str

    # -- Twilio --
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    # default Twilio number (optional, useful for local dev verification)
    twilio_phone_number: str = ""

    # -- Deepgram / Qwen / Fish Audio (used starting Days 3-8) --
    deepgram_api_key: str = ""
    qwen_api_key: str = ""
    fish_audio_api_key: str = ""

    # -- Sentry (Days 11-12) --
    sentry_dsn: str = ""

    # -- Stopgap endpoint protection (Phase 1) --
    # NOT the real authorization model (see ROADMAP.md section 4). Just
    # closes the fact that /restaurants is reachable on a public
    # Railway/ngrok URL with zero protection right now.
    admin_api_key: str = ""

    # Note: no need to configure a "public host" manually — it's built from
    # request.url in the webhook itself (the same public domain Twilio used
    # to call it, whether ngrok or Railway).


@lru_cache
def get_settings() -> Settings:
    return Settings()
