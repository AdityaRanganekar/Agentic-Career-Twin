import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router as api_router
from src.utils.logger import * 

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title="Agentic Career Twin API",
        description="Backend for the Evidence-Grounded Agentic Career Twin",
        version="0.1.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")
    return app

app = create_app()

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Agentic Career Twin API...")

if __name__ == "__main__":
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)