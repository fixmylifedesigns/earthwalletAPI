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
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    
    # Initialize Firebase safely
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
            app.logger.warning("FIREBASE_SERVICE_ACCOUNT not found")
    
    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)
    
    # Import models (AFTER db is initialized)
    with app.app_context():
        try:
            from models import User, Wallet, Transaction, Withdrawal
            app.logger.info("Models imported successfully")
        except Exception as e:
            app.logger.error(f"Failed to import models: {e}")
    
    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(deposit_bp)
    app.register_blueprint(withdraw_bp)
    
    @app.route('/')
    def index():
        return {
            'message': 'RecycleTek Wallet API',
            'status': 'running',
            'version': '1.0.0'
        }, 200
    
    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200
    
    app.logger.info("Flask app created successfully")
    return app

# Create app instance for gunicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)