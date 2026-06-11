from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, Any, Union


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ReportForge"
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/pdf_analytics"
    POSTGRES_SERVER: str = "db"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "pdf_analytics"
    POSTGRES_PORT: str = "5432"
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[list, str] = [
        "http://localhost",
        "http://localhost:4028",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:4028",
        "http://127.0.0.1:3000",
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [v]
        return v

    
    # File Upload
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "./uploads"
    
    # OCR Settings
    TESSERACT_CMD: Optional[str] = None  # Path to tesseract executable if not in PATH

    # Groq API Settings
    GROQ_API_KEY: str = ""

    # Gemini API Settings
    GEMINI_API_URL: str = "https://generativelanguage.googleapis.com"
    GEMINI_API_KEY: str = ""
    GEMINI_API_KEYS: str = ""  # comma-separated list of keys for rotation
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_API_VERSION: str = "v1beta"

    @property
    def gemini_key_pool(self) -> list[str]:
        """All Gemini keys deduplicated, GEMINI_API_KEY always included first."""
        keys: list[str] = []
        if self.GEMINI_API_KEY:
            keys.append(self.GEMINI_API_KEY)
        for k in self.GEMINI_API_KEYS.split(","):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
        return keys
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
