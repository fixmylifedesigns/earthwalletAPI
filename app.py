from flask import Flask
from flask_cors import CORS
from extensions import db, limiter, migrate
from routes.wallet import wallet_bp
from routes.user import user_bp
from routes.deposit import deposit_bp
from routes.withdraw import withdraw_bp
from config import Config
import os
import logging
import firebase_admin
from firebase_admin import credentials

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)
    
    # Configure logging for both development and production
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    
    # Initialize Firebase
    if not firebase_admin._apps:
        firebase_creds = app.config.get("FIREBASE_SERVICE_ACCOUNT")
        if firebase_creds:
            try:
                cred = credentials.Certificate(firebase_creds)
                firebase_admin.initialize_app(cred)
                app.logger.info("Firebase initialized successfully")
            except Exception as e:
                app.logger.error(f"Failed to initialize Firebase: {e}")
        else:
            app.logger.warning("FIREBASE_SERVICE_ACCOUNT not found. Firebase will not be initialized.")
    
    # Log configuration on startup
    app.logger.info(f"Flask Environment: {app.config.get('FLASK_ENV', 'production')}")
    app.logger.info(f"Firebase Project ID: {app.config.get('FIREBASE_PROJECT_ID')}")
    app.logger.info(f"TEST_USER_EMAIL: {os.getenv('TEST_USER_EMAIL')}")
    app.logger.info(f"Database URL configured: {bool(app.config.get('SQLALCHEMY_DATABASE_URI'))}")
    app.logger.info(f"Stripe Key configured: {bool(os.getenv('STRIPE_SECRET_KEY'))}")
    
    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    
    # Create database tables automatically
    with app.app_context():
        try:
            # Import models to ensure they're registered
            from models import User, Wallet, Transaction, Withdrawal
            
            # Create all tables
            db.create_all()
            app.logger.info("Database tables created/verified successfully")
            
            # Log table info
            tables = db.engine.table_names() if hasattr(db.engine, 'table_names') else []
            app.logger.info(f"Database tables: {tables}")
            
        except Exception as e:
            app.logger.error(f"Failed to create database tables: {e}")
    
    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(deposit_bp)
    app.register_blueprint(withdraw_bp)
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        return {
            'status': 'healthy',
            'database': db_status,
            'firebase': bool(firebase_admin._apps),
            'environment': app.config.get('FLASK_ENV', 'production')
        }, 200
    
    @app.route('/debug/config')
    def debug_config():
        """Debug endpoint to check configuration - works in production too"""
        return {
            'firebase_project_id': app.config.get('FIREBASE_PROJECT_ID'),
            'test_user_email': os.getenv('TEST_USER_EMAIL'),
            'has_database_url': bool(app.config.get('SQLALCHEMY_DATABASE_URI')),
            'has_stripe_key': bool(os.getenv('STRIPE_SECRET_KEY')),
            'environment': app.config.get('FLASK_ENV', 'production'),
            'firebase_initialized': bool(firebase_admin._apps),
            'database_url_preview': str(app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set'))[:50] + '...' if app.config.get('SQLALCHEMY_DATABASE_URI') else 'Not set'
        }, 200
    
    @app.route('/')
    def index():
        """Root endpoint"""
        return {
            'message': 'RecycleTek Wallet API',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'health': '/health',
                'debug': '/debug/config',
                'wallet': '/wallet',
                'deposit': '/deposit',
                'withdraw': '/withdraw',
                'validate_kiosk': '/validate-kiosk-id'
            }
        }, 200
    
    return app

# Create app instance for gunicorn
app = create_app()

if __name__ == "__main__":
    # For local development
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)