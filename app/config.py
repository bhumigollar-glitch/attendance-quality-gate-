from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""
    APP_NAME: str = "Attendance Spreadsheet Quality Gate"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./attendance_gate.db"

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STORAGE_DIR: Path = BASE_DIR / "data"
    RAW_STORAGE_DIR: Path = BASE_DIR / "data" / "raw"
    CLEANED_STORAGE_DIR: Path = BASE_DIR / "data" / "cleaned"

    # Upload Constraints
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    ALLOWED_EXTENSIONS: List[str] = [".csv", ".xlsx"]
    ALLOWED_MIME_TYPES: List[str] = [
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "application/octet-stream",
    ]

    # Rule Configuration
    DEFAULT_RULE_VERSION: str = "v1.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def init_storage(self) -> None:
        """Ensure storage directories exist."""
        self.RAW_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.CLEANED_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.init_storage()
