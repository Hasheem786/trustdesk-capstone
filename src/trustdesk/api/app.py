from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.trustdesk.config import settings
from src.trustdesk.storage.database import init_db
from src.trustdesk.api.routes import router as api_router

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "web" / "static"
TEMPLATES_DIR = BASE_DIR / "web" / "templates"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables & initial data exist
    init_db()
    yield

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Enterprise AI Support Operations Agent with Grounded RAG, HITL Actions, and Adversarial Guardrails",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
def read_root():
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "TrustDesk API is operational. Visit /docs for OpenAPI documentation."}

@app.get("/walkthrough", include_in_schema=False)
def read_walkthrough():
    wt_path = TEMPLATES_DIR / "walkthrough.html"
    if wt_path.exists():
        return FileResponse(str(wt_path))
    return {"message": "Walkthrough page not found."}
