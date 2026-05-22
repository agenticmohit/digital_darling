from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    supabase_url: str = "https://xxxx.supabase.co"
    supabase_anon_key: str = "placeholder"
    supabase_jwt_secret: str = "placeholder-dev-secret-32-chars-min"
    openai_api_key: str = "placeholder"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    app_url: str = "http://localhost:8000"
    environment: str = "development"

    # Load from the local .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_sandbox_mode(self) -> bool:
        # Returns True if credentials are placeholders or env is development
        return (
            "xxxx.supabase.co" in self.supabase_url or
            "placeholder" in self.supabase_anon_key or
            self.environment == "development"
        )

settings = Settings()

