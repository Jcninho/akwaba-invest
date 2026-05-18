from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    FIREBASE_CREDENTIALS_PATH: str
    ADMIN_API_KEY: str
    WAVE_API_KEY: str
    WAVE_WEBHOOK_SECRET: str
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
