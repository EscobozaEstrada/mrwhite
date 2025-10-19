#!/bin/bash
# Development Startup Script
echo "🚀 Starting FastAPI Development Server..."
echo "📝 Using development fallback for MemoryDB"
uvicorn main_dev:app --reload --host 0.0.0.0 --port 8001
