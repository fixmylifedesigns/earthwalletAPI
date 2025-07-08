import os
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://postgres:password@localhost/recycling_wallet'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Firebase
    FIREBASE_SERVICE_ACCOUNT = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT", "{}"))
    FIREBASE_PROJECT_ID = FIREBASE_SERVICE_ACCOUNT.get("project_id")
    
    # Stripe
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379'
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = REDIS_URL or 'memory://'
    RATELIMIT_DEFAULT = "1000 per hour"
    
    # Dev/testing
    TEST_USER_EMAIL = os.environ.get('TEST_USER_EMAIL')
    
    @staticmethod
    def init_app(app):
        app.logger.info(f"Firebase Project ID configured: {bool(Config.FIREBASE_PROJECT_ID)}")
        app.logger.info(f"Test User Email configured: {bool(Config.TEST_USER_EMAIL)}")
