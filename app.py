from flask import Flask
from flask_cors import CORS
import os
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Minimal configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    app.logger.info("Starting minimal Flask app")
    
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
    
    @app.route('/test')
    def test():
        return {'test': 'working', 'env': os.environ.get('RAILWAY_ENVIRONMENT', 'unknown')}, 200
    
    app.logger.info("Minimal Flask app created successfully")
    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)