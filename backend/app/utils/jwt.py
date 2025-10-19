import jwt
from datetime import datetime, timedelta, timezone
from app.config import Config

def generate_token(user):
    payload = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'exp': datetime.now(timezone.utc) + timedelta(days=Config.JWT_EXPIRY_DAYS)
    }
    
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.JWT_ALGORITHM)

def decode_token(token):
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
        # Ensure the payload has required fields
        if 'id' not in payload:
            print("Missing 'id' in token payload:", payload)
            return None
        return payload
    except jwt.ExpiredSignatureError:
        print("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error decoding token: {e}")
        return None
