#!/bin/bash
# Startup script for App Runner - runs all services on different ports

echo "🚀 Starting Mr. White Backend Services..."
echo "📍 Current directory: $(pwd)"
echo "📍 Directory contents: $(ls -la)"

# Get the current directory (should be /app/backend from App Runner)
BACKEND_DIR=$(pwd)
echo "📍 Backend directory: $BACKEND_DIR"

# Start FastAPI Chat service in background
echo "📡 Starting FastAPI Chat service on port 8000..."
cd "$BACKEND_DIR/fastapi_chat" && python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info &
FASTAPI_CHAT_PID=$!
echo "✅ FastAPI Chat started with PID: $FASTAPI_CHAT_PID"

# Start Intelligent Chat service in background  
echo "🧠 Starting Intelligent Chat service on port 8001..."
cd "$BACKEND_DIR/intelligent_chat" && python3 -m uvicorn main:app --host 127.0.0.1 --port 8001 --log-level info &
INTELLIGENT_CHAT_PID=$!
echo "✅ Intelligent Chat started with PID: $INTELLIGENT_CHAT_PID"

# Wait a moment for services to start
echo "⏳ Waiting for services to initialize..."
sleep 5

# Check if services are running
echo "🔍 Checking service status..."
ps aux | grep uvicorn || echo "No uvicorn processes found"

# Start Flask app with Gunicorn on port 8080 (foreground)
echo "🌐 Starting Flask app with Gunicorn on port 8080..."
cd "$BACKEND_DIR" && exec gunicorn --bind 0.0.0.0:8080 wsgi:application

# Cleanup function (though it won't be reached in normal operation)
cleanup() {
    echo "🛑 Shutting down services..."
    kill $FASTAPI_CHAT_PID $INTELLIGENT_CHAT_PID 2>/dev/null
    exit 0
}

trap cleanup SIGTERM SIGINT