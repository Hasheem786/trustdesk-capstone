import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

class Settings(BaseModel):
    app_name: str = "TrustDesk: AI Support Operations Agent"
    version: str = "0.1.0"
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    db_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'trustdesk.db'}")
    ai_provider: str = os.getenv("AI_PROVIDER", "mock")  # "mock" or "gemini"
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    eval_cases_path: Path = DATA_DIR / "eval_cases.jsonl"
    kb_path: Path = DATA_DIR / "kb_documents.json"
    customers_path: Path = DATA_DIR / "customers.json"
    orders_path: Path = DATA_DIR / "orders.json"

settings = Settings()
