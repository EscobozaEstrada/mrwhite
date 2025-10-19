import os
from datetime import timedelta
from dotenv import load_dotenv


load_dotenv()

class Config:
    # Database Configuration
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,  # Recycle connections every 5 minutes
        'pool_timeout': 20,   # Timeout after 20 seconds
        'max_overflow': 0,    # Don't create additional connections beyond pool_size
        'pool_size': 10,      # Connection pool size
        'connect_args': {
            'connect_timeout': 10,  # 10 second connection timeout
            'sslmode': 'prefer'
        }
    }

    # Email configuration
    # MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    # MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    # MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ['true', 'yes', '1']
    # MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    # MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    # MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@mrwhite.com')
    MAIL_SERVER = os.getenv('SES_SMTP_HOST')
    MAIL_PORT = int(os.getenv('SES_SMTP_PORT', 587))
    MAIL_USE_TLS = True    
    MAIL_USERNAME = os.getenv('SES_SMTP_USERNAME')
    MAIL_PASSWORD = os.getenv('SES_SMTP_PASSWORD')
    # MAIL_DEFAULT_SENDER = os.getenv('SES_EMAIL_FROM', 'mrwhitetheai@gmail.com')
    MAIL_DEFAULT_SENDER = "no-reply@mrwhiteaidogbuddy.com"

    # Email Configuration
    # ADMIN_EMAIL = os.getenv('SES_EMAIL_FROM', 'mrwhitetheai@gmail.com')
    ADMIN_EMAIL = "mrwhitetheai@gmail.com"

    # CORS Configuration
    FRONTEND_URL = os.getenv('FRONTEND_URL')
    CORS_MAX_AGE = int(os.getenv('CORS_MAX_AGE', '3600'))

    # JWT Configuration
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_EXPIRY_DAYS = int(os.getenv('JWT_EXPIRY_DAYS', '1'))

    # Cookie Configuration
    COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'False').lower() == 'true'
    COOKIE_MAX_AGE = int(os.getenv('COOKIE_MAX_AGE', '604800'))  # 7 days
    COOKIE_HTTPONLY = os.getenv('COOKIE_HTTPONLY', 'True').lower() == 'true'
    COOKIE_SAMESITE = os.getenv('COOKIE_SAMESITE', 'Lax')

    # OpenAI Configuration
    OPENAI_CHAT_MODEL = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4')
    OPENAI_EMBEDDING_MODEL = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')
    OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '1000'))
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
    OPENAI_FILE_UPLOAD_TEMPERATURE = float(os.getenv('OPENAI_FILE_UPLOAD_TEMPERATURE', '0.9'))

    # Pinecone Configuration
    PINECONE_DIMENSION = int(os.getenv('PINECONE_DIMENSION', '1536'))
    PINECONE_METRIC = os.getenv('PINECONE_METRIC', 'cosine')

    # File Processing Configuration
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '100'))
    UPLOAD_DIRECTORY = os.getenv('UPLOAD_DIRECTORY', 'uploads')
    VECTOR_SEARCH_TOP_K = int(os.getenv('VECTOR_SEARCH_TOP_K', '3'))

    # Server Configuration
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', '5001'))

    # Database Schema Limits
    MAX_USERNAME_LENGTH = int(os.getenv('MAX_USERNAME_LENGTH', '100'))
    MAX_EMAIL_LENGTH = int(os.getenv('MAX_EMAIL_LENGTH', '100'))
    MAX_PASSWORD_LENGTH = int(os.getenv('MAX_PASSWORD_LENGTH', '100'))
    MAX_TITLE_LENGTH = int(os.getenv('MAX_TITLE_LENGTH', '255'))
    MAX_ATTACHMENT_TYPE_LENGTH = int(os.getenv('MAX_ATTACHMENT_TYPE_LENGTH', '50'))
    MAX_ATTACHMENT_URL_LENGTH = int(os.getenv('MAX_ATTACHMENT_URL_LENGTH', '512'))
    MAX_ATTACHMENT_NAME_LENGTH = int(os.getenv('MAX_ATTACHMENT_NAME_LENGTH', '255'))
    MAX_MESSAGE_TYPE_LENGTH = int(os.getenv('MAX_MESSAGE_TYPE_LENGTH', '10'))

    # Default Values
    DEFAULT_CONVERSATION_TITLE = os.getenv('DEFAULT_CONVERSATION_TITLE', 'New Conversation')
    DEFAULT_MESSAGE_TYPE = os.getenv('DEFAULT_MESSAGE_TYPE', 'user')
    DEFAULT_CONTEXT = os.getenv('DEFAULT_CONTEXT', 'chat')

    # Email Configuration
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'mrwhitetheai@gmail.com')

    # Stripe Configuration
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    STRIPE_TEST_SECRET_KEY = os.getenv('STRIPE_TEST_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLIC_KEY')
    STRIPE_PRICE_ID = os.getenv('STRIPE_PRICE_ID')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

