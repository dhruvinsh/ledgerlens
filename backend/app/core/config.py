from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/ledgerlens.db"
    DATA_DIR: str = "./data"

    # LLM
    LLM_BASE_URL: str = "http://127.0.0.1:11434/v1"
    LLM_MODEL: str = "llama3.2"
    LLM_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_RETRIES: int = 1

    # Auth
    SECRET_KEY: str = "change-me"

    # Rate limiting (per IP)
    RATE_LIMIT_LOGIN_MAX: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 900
    RATE_LIMIT_REGISTER_MAX: int = 3
    RATE_LIMIT_REGISTER_WINDOW_SECONDS: int = 900

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Google CSE (optional, for product images)
    GOOGLE_CSE_API_KEY: str = ""
    GOOGLE_CSE_CX: str = ""

    # Fuzzy matching — products
    FUZZY_AUTO_LINK_THRESHOLD: int = 85
    FUZZY_SUGGEST_THRESHOLD: int = 60

    # Fuzzy matching — stores
    STORE_FUZZY_AUTO_LINK_THRESHOLD: int = 88
    STORE_FUZZY_SUGGEST_THRESHOLD: int = 65

    # Retroactive matching
    RETROACTIVE_BATCH_SIZE: int = 200
    RETROACTIVE_INTERVAL_SECONDS: int = 300

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    TASK_SOFT_TIME_LIMIT: int = 300
    TASK_HARD_TIME_LIMIT: int = 360

    # Tesseract
    TESSERACT_LANG: str = "eng"
    TESSERACT_PSM: int = 6
    TESSERACT_DPI: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
