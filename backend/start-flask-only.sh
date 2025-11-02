#!/bin/bash
# Simplified startup script for App Runner - Flask only to isolate issues

set -e  # Exit on any error

echo "🚀 Starting Flask Only for App Runner..."
echo "📍 Current directory: $(pwd)"
echo "📍 Directory contents:"
ls -la

# Get the current directory (should be /app/backend from App Runner)
BACKEND_DIR=$(pwd)
echo "📍 Backend directory: $BACKEND_DIR"

# Check required files exist
echo "🔍 Checking required files..."
if [ ! -f "$BACKEND_DIR/wsgi.py" ]; then
    echo "❌ wsgi.py not found in $BACKEND_DIR"
    exit 1
fi

if [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
    echo "❌ requirements.txt not found in $BACKEND_DIR"
    exit 1
fi

if [ ! -d "$BACKEND_DIR/app" ]; then
    echo "❌ app directory not found in $BACKEND_DIR"
    exit 1
fi

echo "✅ All required files found"

# Check Python and packages
echo "📍 Python version: $(python3 --version)"
echo "📍 Key Python packages:"
python3 -c "
import sys
packages = ['flask', 'gunicorn', 'sqlalchemy', 'requests']
for pkg in packages:
    try:
        __import__(pkg)
        print(f'✅ {pkg} is available')
    except ImportError:
        print(f'❌ {pkg} is NOT available')
"

# Test Flask app import before starting gunicorn
echo "🧪 Testing Flask app import..."
python3 -c "
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from wsgi import application
    print('✅ Flask app imported successfully')
    
    # Test if app has the health endpoint
    with application.test_client() as client:
        response = client.get('/health')
        print(f'✅ Health endpoint test: {response.status_code} - {response.data.decode()}')
        
except Exception as e:
    print(f'❌ Flask app test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

# Set environment variables for production
echo "🔧 Setting environment variables..."
export ENVIRONMENT=prod
export USE_SSM_CONFIG=true
export FLASK_HOST=0.0.0.0  
export FLASK_PORT=8080

# Start Flask with gunicorn - minimal configuration first
echo "🌐 Starting Flask with minimal Gunicorn configuration..."
echo "Command: gunicorn --bind 0.0.0.0:8080 --log-level debug --access-logfile - --error-logfile - wsgi:application"

exec gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 1 \
    --timeout 30 \
    --log-level debug \
    --access-logfile - \
    --error-logfile - \
    --preload \
    wsgi:application