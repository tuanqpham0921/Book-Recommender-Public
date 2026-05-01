import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.lifecycle import start_all, shutdown_all
from app.config.logging_config import setup_logging

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup phase - Critical for Cloud Run
    logger.info("🚀 Application starting...")
    logger.info("🔧 Initializing services for Cloud Run...")
    
    try:
        await start_all(app)
        logger.info("✅ All services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise  # This will prevent Cloud Run from routing traffic
    
    yield  # App runs here
    
    # Shutdown phase - Graceful cleanup when scaling to zero
    logger.info("🔻 Application shutting down...")
    try:
        await shutdown_all(app)
        logger.info("✅ Graceful shutdown completed")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


app = FastAPI(
    title="Book Recommender API",
    description="AI-powered book recommendation system",
    version="3.0.0",
    lifespan=lifespan
)

# CORS configuration for Cloud Run
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"], # TODO: need to update this
    allow_headers=["*"],
)

# Include routers
from app.api.routes.health import router as health_router
from app.api.routes.chat_message import router as chat_router  
from app.api.routes.session import router as session_router

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(session_router)

# Cloud Run entry point
if __name__ == "__main__":
    import uvicorn
    
    # Cloud Run provides PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info(f"🌐 Starting server on {host}:{port}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,  # Never use reload in production
        access_log=True,
        log_level="info"
    )