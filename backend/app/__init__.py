"""
Updated Flask App Initialization with SSM Parameter Store Support

This updated __init__.py can use either traditional environment variables
or the new SSM-aware configuration system.
"""

import os
import logging
from flask import Flask, make_response, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from datetime import timedelta

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app(config_name=None):
    """Application factory pattern with SSM support"""
    app = Flask(__name__)
    
    # Determine if we should use SSM configuration
    use_ssm_config = os.getenv('USE_SSM_CONFIG', 'False').lower() in ('true', '1', 'yes')
    environment = os.getenv('ENVIRONMENT', 'dev')
    
    if use_ssm_config:
        # Use SSM-aware configuration
        try:
            # Import from tools at backend level (not app.tools)
            import sys
            from pathlib import Path
            backend_path = Path(__file__).parent.parent
            if str(backend_path) not in sys.path:
                sys.path.insert(0, str(backend_path))
            
            from tools.ssm_config import get_config
            config_obj = get_config(environment)
            app.config.from_object(config_obj)
            app.logger.info(f"✅ Using SSM configuration for environment: {environment}")
        except ImportError as e:
            app.logger.warning(f"⚠️  SSM config module not found: {e}, falling back to environment variables")
            use_ssm_config = False
        except Exception as e:
            app.logger.warning(f"⚠️  Failed to load SSM configuration: {e}, falling back to environment variables")
            use_ssm_config = False
    
    if not use_ssm_config:
        # Fallback to traditional environment variable configuration
        app.logger.info("📝 Using traditional environment variable configuration")
        
        # Load configuration from object if specified
        if config_name:
            app.config.from_object(config_name)
        else:
            # Default configuration from environment variables
            app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
            app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

            # Database connection pool settings to prevent timeouts
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'pool_pre_ping': True,  # Verify connections before use
                'pool_recycle': 300,    # Recycle connections every 5 minutes
                'pool_timeout': 20,     # Connection timeout of 20 seconds
                'max_overflow': 10,     # Allow up to 10 overflow connections
                'pool_size': 5,         # Base pool size of 5 connections
            }
            
            # JWT Configuration
            app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', os.getenv('SECRET_KEY', 'dev-secret-key'))
            app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=int(os.getenv('JWT_EXPIRY_DAYS', 1)))
            app.config['JWT_ALGORITHM'] = os.getenv('JWT_ALGORITHM', 'HS256')
            
            # Cookie Configuration
            app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
            app.config['JWT_COOKIE_SECURE'] = os.getenv('COOKIE_SECURE', 'False').lower() == 'true'
            app.config['JWT_COOKIE_CSRF_PROTECT'] = False
            app.config['JWT_COOKIE_SAMESITE'] = os.getenv('COOKIE_SAMESITE', 'Lax')
            app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
            app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
            app.config['JWT_COOKIE_DOMAIN'] = None
            
            # Additional Cookie Configuration
            app.config['COOKIE_HTTPONLY'] = os.getenv('COOKIE_HTTPONLY', 'True').lower() == 'true'
            app.config['COOKIE_SECURE'] = os.getenv('COOKIE_SECURE', 'False').lower() == 'true'
            app.config['COOKIE_MAX_AGE'] = int(os.getenv('COOKIE_MAX_AGE', '604800'))  # 7 days
            app.config['COOKIE_SAMESITE'] = os.getenv('COOKIE_SAMESITE', 'Lax')
            
            # AWS Configuration
            app.config['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID')
            app.config['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY')
            app.config['S3_BUCKET_NAME'] = os.getenv('S3_BUCKET_NAME')
            
            # SES Configuration
            app.config['SES_SMTP_HOST'] = os.getenv('SES_SMTP_HOST')
            app.config['SES_SMTP_PORT'] = os.getenv('SES_SMTP_PORT')
            app.config['SES_SMTP_USERNAME'] = os.getenv('SES_SMTP_USERNAME')
            app.config['SES_SMTP_PASSWORD'] = os.getenv('SES_SMTP_PASSWORD')
            app.config['SES_EMAIL_FROM'] = os.getenv('SES_EMAIL_FROM')
            
            # Other configurations
            app.config['FRONTEND_URL'] = os.getenv('FRONTEND_URL', 'http://localhost:3000')
            app.config['CORS_MAX_AGE'] = int(os.getenv('CORS_MAX_AGE', '3600'))
            app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
            app.config['PINECONE_API_KEY'] = os.getenv('PINECONE_API_KEY')
            app.config['PINECONE_ENVIRONMENT'] = os.getenv('PINECONE_ENVIRONMENT')
            app.config['PINECONE_INDEX_NAME'] = os.getenv('PINECONE_INDEX_NAME')
            
            # OpenAI Configuration
            app.config['OPENAI_EMBEDDING_MODEL'] = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')
            app.config['OPENAI_TEMPERATURE'] = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
            app.config['OPENAI_CHAT_MODEL'] = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4')
            app.config['OPENAI_MAX_TOKENS'] = int(os.getenv('OPENAI_MAX_TOKENS', '1000'))
            app.config['OPENAI_FILE_UPLOAD_TEMPERATURE'] = float(os.getenv('OPENAI_FILE_UPLOAD_TEMPERATURE', '0.9'))
            
            # Payment Processing
            app.config['STRIPE_SECRET_KEY'] = os.getenv('STRIPE_SECRET_KEY')
            app.config['STRIPE_PUBLISHABLE_KEY'] = os.getenv('STRIPE_PUBLISHABLE_KEY')
            
            # Firebase Configuration
            app.config['FIREBASE_PROJECT_ID'] = os.getenv('FIREBASE_PROJECT_ID')
            app.config['FIREBASE_API_KEY'] = os.getenv('FIREBASE_API_KEY')
            app.config['FIREBASE_AUTH_DOMAIN'] = os.getenv('FIREBASE_AUTH_DOMAIN')
            app.config['FIREBASE_STORAGE_BUCKET'] = os.getenv('FIREBASE_STORAGE_BUCKET')
            app.config['FIREBASE_MESSAGING_SENDER_ID'] = os.getenv('FIREBASE_MESSAGING_SENDER_ID')
            app.config['FIREBASE_APP_ID'] = os.getenv('FIREBASE_APP_ID')
            app.config['FIREBASE_MEASUREMENT_ID'] = os.getenv('FIREBASE_MEASUREMENT_ID')
            
            # Firebase Service Account JSON (from SSM or fallback to file path)
            app.config['FIREBASE_SERVICE_ACCOUNT_JSON'] = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
            app.config['FIREBASE_SERVICE_ACCOUNT_PATH'] = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 
                                                                    '/home/danae/development/mrwhite/Mr-White-Project/backend/firebase-service-account.json')
            
            # VAPID Keys for Push Notifications
            app.config['VAPID_PRIVATE_KEY'] = os.getenv('VAPID_PRIVATE_KEY')
            app.config['VAPID_PUBLIC_KEY'] = os.getenv('VAPID_PUBLIC_KEY')
            app.config['VAPID_EMAIL'] = os.getenv('VAPID_EMAIL')
            
            # External APIs
            app.config['TEXTBELT_API_KEY'] = os.getenv('TEXTBELT_API_KEY')
            
            # Flask Server Configuration
            app.config['FLASK_HOST'] = os.getenv('FLASK_HOST', '0.0.0.0')
            app.config['FLASK_PORT'] = int(os.getenv('FLASK_PORT', '5001'))
            app.config['FLASK_DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app, 
        supports_credentials=True,
        resources={
            r"/api/*": {
                "origins": [app.config['FRONTEND_URL'], "http://localhost:3000", "http://localhost:3005"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
                "expose_headers": ["Content-Range", "X-Content-Range"],
                "max_age": app.config['CORS_MAX_AGE'],
                "supports_credentials": True
            }
        }
    )
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Log configuration source
    if use_ssm_config:
        app.logger.info("🔐 Configuration loaded from AWS SSM Parameter Store")
    else:
        app.logger.info("📝 Configuration loaded from environment variables")
    
    # Register blueprints
    from .routes import auth_bp, chatbot_bp, conversation_bp, contact_bp, enhanced_chat_bp, care_archive_bp, payment_bp
    from .routes.subscription import subscription_bp
    from .routes.usage import usage_bp
    from .routes.health_intelligence_routes import health_intelligence_bp
    from .routes.enhanced_health import enhanced_health_bp
    from .routes.health_routes import health_bp
    from .routes.credit_system import credit_system_bp
    from .routes.enhanced_reminder_routes import enhanced_reminder_bp
    from .routes.timezone_routes import timezone_bp
    from .routes.gallery import gallery_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chatbot_bp, url_prefix='/api')
    app.register_blueprint(conversation_bp, url_prefix='/api')
    app.register_blueprint(contact_bp, url_prefix='/api/contact')
    app.register_blueprint(enhanced_chat_bp, url_prefix='/api')
    app.register_blueprint(care_archive_bp, url_prefix='/api/care-archive')
    app.register_blueprint(payment_bp, url_prefix='/api/payment')
    app.register_blueprint(subscription_bp, url_prefix='/api/subscription')
    app.register_blueprint(usage_bp, url_prefix='/api/usage')
    app.register_blueprint(health_intelligence_bp)  # Already has /api/health-intelligence prefix
    app.register_blueprint(enhanced_health_bp)  # Already has /api/enhanced-health prefix
    app.register_blueprint(health_bp)  # Already has /api/health prefix
    app.register_blueprint(credit_system_bp, url_prefix='/api/credit-system')
    app.register_blueprint(enhanced_reminder_bp)  # Already has /api/reminders prefix
    app.register_blueprint(timezone_bp, url_prefix='/api/timezone')
    app.register_blueprint(gallery_bp)  # Already has /api/gallery prefix
    
    # Initialize precision reminder scheduler with app context
    try:
        from .services.precision_reminder_scheduler import start_precision_scheduler
        start_precision_scheduler(app)
        app.logger.info("✅ Precision reminder scheduler initialized successfully")
    except Exception as e:
        app.logger.error(f"❌ Failed to initialize precision reminder scheduler: {str(e)}")
        
        # Fallback to old scheduler if precision scheduler fails
        try:
            from .services.reminder_scheduler_service import start_reminder_scheduler
            start_reminder_scheduler(app)
            app.logger.info("✅ Fallback reminder scheduler initialized successfully")
        except Exception as fallback_error:
            app.logger.error(f"❌ Failed to initialize fallback reminder scheduler: {str(fallback_error)}")
    
    # Add a generic OPTIONS route handler
    @app.route('/api/<path:path>', methods=['OPTIONS'])
    def handle_api_options(path):
        response = make_response()
        # Allow requests from both the configured frontend URL and localhost development ports
        allowed_origins = [app.config['FRONTEND_URL'], "http://localhost:3000", "http://localhost:3005"]
        origin = request.headers.get('Origin')
        if origin in allowed_origins:
            response.headers.add("Access-Control-Allow-Origin", origin)
        else:
            # Default to localhost:3000 for development
            response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Accept, Origin")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        response.headers.add("Access-Control-Max-Age", str(app.config['CORS_MAX_AGE']))
        return response

    # Add route to serve uploaded images
    @app.route('/uploads/images/<int:user_id>/<filename>')
    def serve_uploaded_image(user_id, filename):
        """Serve uploaded images stored locally with CORS headers"""
        from flask import send_from_directory
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'images', str(user_id))
        try:
            response = send_from_directory(upload_dir, filename)
            
            # Add CORS headers for frontend access
            allowed_origins = [app.config['FRONTEND_URL'], "http://localhost:3000", "http://localhost:3005"]
            origin = request.headers.get('Origin')
            if origin in allowed_origins:
                response.headers.add("Access-Control-Allow-Origin", origin)
            else:
                # Default to localhost:3000 for development
                response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
            
            response.headers.add("Access-Control-Allow-Credentials", "true")
            response.headers.add("Access-Control-Allow-Methods", "GET")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
            
            return response
        except FileNotFoundError:
            from flask import abort
            abort(404)
    
    # Add health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint for App Runner"""
        return {'status': 'healthy', 'config_source': 'ssm' if use_ssm_config else 'env'}, 200

    return app