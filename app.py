from flask import Flask, jsonify
import os
import secrets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    DEBUG = True  # Set the default configuration directly here

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Setup database path
    base_dir = os.path.abspath(os.path.dirname(__file__))
    instance_dir = os.path.join(base_dir, "instance")
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_dir, "app.db")}'

    # Ensure required directories exist
    directories = [
        instance_dir,
        os.path.join(base_dir, 'static', 'audio'),
        os.path.join(base_dir, 'static', 'images'),
        os.path.join(base_dir, 'static', 'videos'),
        os.path.join(base_dir, 'static', 'temp')
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    # Initialize extensions
    from models import db
    db.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.memes import memes_bp
    from routes.config_routes import config_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(memes_bp)
    app.register_blueprint(config_bp)

    # Add health check endpoint
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({'status': 'healthy', 'app': 'Automatic Meme Content Generator'})

    # Create database tables
    with app.app_context():
        from models import db
        db.create_all()

    return app

# Create Flask application
app = create_app()

if __name__ == '__main__':
    # Make the app available on local network
    app.run(host='0.0.0.0', port=5000, debug=True)
