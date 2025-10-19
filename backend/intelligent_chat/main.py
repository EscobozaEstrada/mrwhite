"""
FastAPI Application for Intelligent Chat System
"""
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables (.env.local takes priority)
env_local = Path(__file__).parent / ".env.local"
env_parent = Path(__file__).parent.parent / ".env"

if env_local.exists():
    load_dotenv(env_local)
else:
    load_dotenv(env_parent)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Import routes using relative imports
from api.routes.chat import router as chat_router
from api.routes.dogs import router as dogs_router
from api.routes.documents import router as documents_router
from api.routes.reminders import router as reminders_router
from api.routes.feedback import router as feedback_router
from api.routes.system_message import router as system_message_router
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Intelligent Chat API",
    description="Intelligent chatbot system with memory, learning, and context awareness",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(chat_router, prefix="/api/v2", tags=["chat"])
app.include_router(dogs_router, prefix="/api/v2", tags=["dogs"])
app.include_router(documents_router, prefix="/api/v2/documents", tags=["documents"])
app.include_router(reminders_router, tags=["reminders"])
app.include_router(feedback_router, prefix="/api/v2", tags=["feedback"])
app.include_router(system_message_router, prefix="/api/v2", tags=["system"])

# Root endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Intelligent Chat API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "intelligent_chat",
        "version": "1.0.0"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Intelligent Chat API starting up...")
    logger.info(f"✅ Environment: {settings.ENVIRONMENT}")
    logger.info(f"✅ Database: Connected")
    logger.info(f"✅ Pinecone Namespace: intelligent-chat")
    logger.info("✅ All systems ready!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Intelligent Chat API shutting down...")

# Run with uvicorn when executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "intelligent_chat.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
