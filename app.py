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
    
    # Configure logging
    if app.config.get('FLASK_ENV') == 'development':
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)
        
    if not firebase_admin._apps:
        firebase_creds = app.config.get("FIREBASE_SERVICE_ACCOUNT")
        if firebase_creds:
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred)
        else:
            app.logger.warning("FIREBASE_SERVICE_ACCOUNT not found. Firebase will not be initialized.")
    
    # Log configuration on startup
    app.logger.info(f"Firebase Project ID: {app.config.get('FIREBASE_PROJECT_ID')}")
    app.logger.info(f"TEST_USER_EMAIL: {os.getenv('TEST_USER_EMAIL')}")
    app.logger.info(f"Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
    
    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(deposit_bp)
    app.register_blueprint(withdraw_bp)
    
    # Import models to ensure they're registered
    from models import User, Wallet, Transaction, Withdrawal
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}, 200
    
    @app.route('/debug/config')
    def debug_config():
        """Debug endpoint to check configuration"""
        if app.config.get('FLASK_ENV') != 'development':
            return {'error': 'Debug endpoint only available in development'}, 404
        
        return {
            'firebase_project_id': app.config.get('FIREBASE_PROJECT_ID'),
            'test_user_email': os.getenv('TEST_USER_EMAIL'),
            'has_database_url': bool(app.config.get('SQLALCHEMY_DATABASE_URI')),
            'has_stripe_key': bool(os.getenv('STRIPE_SECRET_KEY')),
            'environment': app.config.get('FLASK_ENV')
        }, 200
    
    return app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway provides PORT env
    app.run(host="0.0.0.0", port=port)
