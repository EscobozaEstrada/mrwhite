#!/bin/bash
# Startup script for App Runner - runs all services on different ports

set -e  # Exit on any error

echo "🚀 Starting Mr. White Backend Services..."
echo "📍 Current directory: $(pwd)"
echo "📍 Directory contents: $(ls -la)"
echo "📍 Python version: $(python3 --version)"
echo "📍 Available Python packages:"
pip3 list | head -20

# Get the current directory (should be /app/backend from App Runner)
BACKEND_DIR=$(pwd)
echo "📍 Backend directory: $BACKEND_DIR"

# Function to check if a port is available
check_port() {
    local port=$1
    if netstat -tuln | grep ":$port " > /dev/null; then
        echo "❌ Port $port is already in use"
        return 1
    else
        echo "✅ Port $port is available"
        return 0
    fi
}

# Check if ports are available
check_port 8000
check_port 8001
check_port 8080

# Start FastAPI Chat service in background
echo "📡 Starting FastAPI Chat service on port 8000..."
if [ -d "$BACKEND_DIR/fastapi_chat" ]; then
    cd "$BACKEND_DIR/fastapi_chat"
    echo "📂 FastAPI Chat directory contents: $(ls -la)"
    python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info &
    FASTAPI_CHAT_PID=$!
    echo "✅ FastAPI Chat started with PID: $FASTAPI_CHAT_PID"
    cd "$BACKEND_DIR"
else
    echo "❌ FastAPI Chat directory not found at $BACKEND_DIR/fastapi_chat"
fi

# Start Intelligent Chat service in background  
echo "🧠 Starting Intelligent Chat service on port 8001..."
if [ -d "$BACKEND_DIR/intelligent_chat" ]; then
    cd "$BACKEND_DIR/intelligent_chat"
    echo "📂 Intelligent Chat directory contents: $(ls -la)"
    python3 -m uvicorn main:app --host 127.0.0.1 --port 8001 --log-level info &
    INTELLIGENT_CHAT_PID=$!
    echo "✅ Intelligent Chat started with PID: $INTELLIGENT_CHAT_PID"
    cd "$BACKEND_DIR"
else
    echo "❌ Intelligent Chat directory not found at $BACKEND_DIR/intelligent_chat"
fi

# Wait for services to start
echo "⏳ Waiting for services to initialize..."
sleep 10

# Test health endpoints of FastAPI services
echo "🔍 Testing FastAPI services..."
if command -v python3 >/dev/null 2>&1; then
    echo "Testing FastAPI Chat health with Python..."
    python3 -c "
import requests
import sys
try:
    response = requests.get('http://127.0.0.1:8000/health', timeout=5)
    print(f'FastAPI Chat: {response.status_code} - {response.text}')
except Exception as e:
    print(f'FastAPI Chat health check failed: {e}')
    sys.exit(0)
" || echo "FastAPI Chat health check failed"
    
    echo "Testing Intelligent Chat health with Python..."
    python3 -c "
import requests
import sys
try:
    response = requests.get('http://127.0.0.1:8001/health', timeout=5)
    print(f'Intelligent Chat: {response.status_code} - {response.text}')
except Exception as e:
    print(f'Intelligent Chat health check failed: {e}')
    sys.exit(0)
" || echo "Intelligent Chat health check failed"
else
    echo "Python not available for health checks"
fi

# Check if services are running
echo "🔍 Checking service status..."
ps aux | grep uvicorn || echo "No uvicorn processes found"

# Alternative to netstat using Python
echo "🔍 Checking ports with Python..."
python3 -c "
import socket
ports = [8000, 8001, 8080]
for port in ports:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', port))
    if result == 0:
        print(f'✅ Port {port} is listening')
    else:
        print(f'❌ Port {port} is not available')
    sock.close()
" || echo "Port check failed"

# Verify wsgi.py exists
if [ -f "$BACKEND_DIR/wsgi.py" ]; then
    echo "✅ wsgi.py found"
    echo "📄 wsgi.py contents:"
    head -10 "$BACKEND_DIR/wsgi.py"
else
    echo "❌ wsgi.py not found in $BACKEND_DIR"
    ls -la "$BACKEND_DIR"
    exit 1
fi

# Test if we can import the Flask app
echo "🧪 Testing Flask app import..."
cd "$BACKEND_DIR"
python3 -c "
try:
    from wsgi import application
    print('✅ Flask app imported successfully')
    print(f'App config: {dict(application.config)}' if hasattr(application, 'config') else 'No config available')
except Exception as e:
    print(f'❌ Flask app import failed: {e}')
    import traceback
    traceback.print_exc()
" || echo "Flask import test failed"

# Start Flask app with Gunicorn on port 8080 (foreground)
echo "🌐 Starting Flask app with Gunicorn on port 8080..."

# Set environment variables for production
export ENVIRONMENT=prod  
export USE_SSM_CONFIG=true

# Add some additional environment variables that might be needed
export FLASK_HOST=0.0.0.0
export FLASK_PORT=8080

# Start gunicorn with additional logging and health checks
echo "🚀 Executing: gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --log-level info --access-logfile - --error-logfile - wsgi:application"
exec gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --log-level info --access-logfile - --error-logfile - wsgi:application

# Cleanup function (though it won't be reached in normal operation due to exec)
cleanup() {
    echo "🛑 Shutting down services..."
    if [ ! -z "$FASTAPI_CHAT_PID" ]; then
        kill $FASTAPI_CHAT_PID 2>/dev/null || echo "FastAPI Chat already stopped"
    fi
    if [ ! -z "$INTELLIGENT_CHAT_PID" ]; then
        kill $INTELLIGENT_CHAT_PID 2>/dev/null || echo "Intelligent Chat already stopped"
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT

echo "📋 Service startup summary:"
echo "- FastAPI Chat PID: ${FASTAPI_CHAT_PID:-'Not started'}"  
echo "- Intelligent Chat PID: ${INTELLIGENT_CHAT_PID:-'Not started'}"
echo "- Flask will start on port 8080 with gunicorn"