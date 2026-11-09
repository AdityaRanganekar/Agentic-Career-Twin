import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router as api_router
from src.utils.logger import get_custom_logger
from src.db.database import init_db

logger = get_custom_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Agentic Career Twin API...")
    init_db()
    yield

def create_app() -> FastAPI:
    app = FastAPI(
        title="Agentic Career Twin API",
        description="Backend for the Evidence-Grounded Agentic Career Twin",
        version="2.0.0",
        lifespan=lifespan
    )

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    allowed_origins = [
        frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8501",
    ]
    # Remove duplicates while preserving order
    allowed_origins = list(dict.fromkeys([o for o in allowed_origins if o]))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.hf\.space",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    @app.get("/health")
    def health_check():
        return {
            "status": "online",
            "service": "Agentic Career Twin API",
            "version": "2.0.0"
        }

    app.include_router(api_router, prefix="/api/v1")
    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=port, reload=True)