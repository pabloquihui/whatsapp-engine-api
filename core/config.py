from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

load_dotenv()


class Settings(BaseSettings):
    APP_ENV: str
    OPENAI_API_KEY: str | None = None
    MISTRAL_API_KEY: str | None = None
    TENANT_DEV_SEED_FILE: str | None = None

    # Optional backends
    AZURE_COSMOS_URL: Optional[str] = None
    AZURE_COSMOS_KEY: Optional[str] = None
    AZURE_COSMOS_DB: Optional[str] = None
    AZURE_COSMOS_CONTAINER: Optional[str] = None
    AZURE_KEYVAULT_URL: Optional[str] = None

    # LLMs
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: Optional[str] = None

    AZURE_OAI_ENDPOINT: Optional[str] = None
    AZURE_OAI_API_KEY: Optional[str] = None
    AZURE_OAI_DEPLOYMENT: Optional[str] = None
    AZURE_OAI_API_VERSION: Optional[str] = None

    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_MODEL: Optional[str] = (
        None  # e.g. "mistral-small-latest" or "mistral-large-latest"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
