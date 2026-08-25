import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Cargar .env desde la raíz del servidor o la raíz del proyecto
server_dir = Path(__file__).resolve().parent.parent
env_file = server_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Arey AI Brain"
    VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Gemini AI Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    
    # Security / Auth Token (para proteger la conexión de tus dispositivos)
    DEVICE_AUTH_TOKEN: str = os.getenv("DEVICE_AUTH_TOKEN", "arey-secret-token-2026")
    
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(server_dir / "data" / "memory.db"))
    
    # Defaults
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Mexico_City")

    class Config:
        case_sensitive = True

settings = Settings()
