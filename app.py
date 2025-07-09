from flask import Flask
from flask_cors import CORS
import os

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    @app.route('/')
    def index():
        return {
            'message': 'RecycleTek Wallet API is running!',
            'status': 'success',
            'version': '1.0.0'
        }, 200
    
    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200
    
    return app

# Create app instance for gunicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)