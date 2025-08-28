import os
from flask import Flask
from flask_login import LoginManager
from firebase_config import initialize_firebase
import markdown

# Initialize extensions
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Initialize Firebase
    initialize_firebase()
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Import Firebase models
    from firebase_models import User, Project
    
    # Register blueprints
    from auth import auth_bp
    from dashboard import dashboard_bp
    from api import api_bp
    from main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)
    
    # Add markdown filter for templates
    @app.template_filter('markdown')
    def markdown_filter(text):
        return markdown.markdown(text, extensions=['codehilite', 'fenced_code'])
    
    # Add bold formatting filter for pitch deck content
    @app.template_filter('format_bold')
    def format_bold_filter(text):
        import re
        if not text:
            return text
        # Replace **text** with <strong>text</strong>
        formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        return formatted
    
    # Create admin user route for Firebase (since we can't do it automatically)
    @app.route('/init-admin')
    def init_admin():
        # Check if admin already exists
        admin = User.get_by_email('admin@synoptic.com')
        if not admin:
            admin = User(
                email='admin@synoptic.com',
                username='admin',
                is_admin=True
            )
            admin.set_password('admin123')
            if admin.save():
                return 'Admin user created successfully! Email: admin@synoptic.com, Password: admin123'
            else:
                return 'Failed to create admin user'
        return 'Admin user already exists'
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
