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
        """True when Supabase is placeholder — mocks auth and DB."""
        return (
            "xxxx.supabase.co" in self.supabase_url or
            "placeholder" in self.supabase_anon_key or
            self.environment == "development"
        )

    @property
    def use_real_ai(self) -> bool:
        """True when a real OpenAI key is present — enables live GPT-4o calls."""
        key = self.openai_api_key
        return (
            key not in ("placeholder", "", "sk-...")
            and len(key) > 20
        )

    @property
    def is_beta_mode(self) -> bool:
        """Deployed beta: real OpenAI, mock auth/DB, only beta credentials work."""
        return self.is_sandbox_mode and self.use_real_ai and self.environment == "production"

settings = Settings()

