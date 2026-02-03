import os
from dotenv import load_dotenv

# Allow overriding the .env location via the DOTENV_PATH environment variable.
# If DOTENV_PATH is set, load that file; otherwise fall back to default behaviour
# (which searches for a .env in the current working directory).
dotenv_path = os.environ.get("DOTENV_PATH")
if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path)
else:
    load_dotenv()

class Settings:
    DISABLE_AUTH: bool = os.getenv("DISABLE_AUTH", "false").lower() == "true"
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./boletin.db")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()
