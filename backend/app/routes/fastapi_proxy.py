"""
FastAPI Proxy Routes for App Runner Single Port Deployment
"""
from flask import Blueprint, request, Response
import requests
import os

fastapi_proxy_bp = Blueprint('fastapi_proxy', __name__)

# FastAPI service URLs (running locally in the same container)
FASTAPI_CHAT_URL = "http://127.0.0.1:8000"
INTELLIGENT_CHAT_URL = "http://127.0.0.1:8001"

@fastapi_proxy_bp.route('/fastapi/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy_fastapi_chat(path):
    """Proxy requests to FastAPI chat service"""
    try:
        url = f"{FASTAPI_CHAT_URL}/{path}"
        
        # Forward the request
        resp = requests.request(
            method=request.method,
            url=url,
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            params=request.args,
            allow_redirects=False,
            stream=True if 'stream' in path else False
        )
        
        # Create response
        response = Response(
            resp.iter_content(chunk_size=1024) if 'stream' in path else resp.content,
            status=resp.status_code,
            headers=dict(resp.headers)
        )
        
        # Add CORS headers
        response.headers['Access-Control-Allow-Origin'] = 'https://app.mrwhiteaidogbuddy.com'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
        
    except requests.exceptions.ConnectionError:
        return {"error": "FastAPI chat service unavailable"}, 503
    except Exception as e:
        return {"error": f"Proxy error: {str(e)}"}, 500

@fastapi_proxy_bp.route('/intelligent/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy_intelligent_chat(path):
    """Proxy requests to Intelligent chat service"""
    try:
        url = f"{INTELLIGENT_CHAT_URL}/{path}"
        
        # Forward the request
        resp = requests.request(
            method=request.method,
            url=url,
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            params=request.args,
            allow_redirects=False,
            stream=True if 'stream' in path else False
        )
        
        # Create response
        response = Response(
            resp.iter_content(chunk_size=1024) if 'stream' in path else resp.content,
            status=resp.status_code,
            headers=dict(resp.headers)
        )
        
        # Add CORS headers
        response.headers['Access-Control-Allow-Origin'] = 'https://app.mrwhiteaidogbuddy.com'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
        
    except requests.exceptions.ConnectionError:
        return {"error": "Intelligent chat service unavailable"}, 503
    except Exception as e:
        return {"error": f"Proxy error: {str(e)}"}, 500