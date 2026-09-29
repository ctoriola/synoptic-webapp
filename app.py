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
    from auth import auth_bp, init_oauth
    from dashboard import dashboard_bp
    from api import api_bp
    from main import main_bp
    from stripe_payments import stripe_bp
    
    # Initialize OAuth
    init_oauth(app)
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(stripe_bp, url_prefix='/api/stripe')
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)
    
    # Add markdown filter for templates
    @app.template_filter('markdown')
    def markdown_filter(text):
        return markdown.markdown(text, extensions=['codehilite', 'fenced_code'])
    
    @app.context_processor
    def inject_now_year():
        from datetime import datetime
        return {'now_year': datetime.utcnow().year}
    
    # Deck length helper for templates
    from slide_plan import user_slide_count
    app.jinja_env.globals['user_slide_count'] = user_slide_count
    
    # Render pitch deck Markdown as safe, structured HTML
    @app.template_filter('format_markdown')
    def format_markdown_filter(text):
        import html
        import re
        if not text:
            return ''
        lines = []
        for line in text.replace('\r', '').split('\n'):
            # Treat "•" bullets as Markdown list items
            line = re.sub(r'^(\s*)[•▪●]\s+', r'\1- ', line)
            # Markdown needs a blank line before a list that follows a paragraph
            if re.match(r'^\s*([-*+]|\d+\.)\s+', line) and lines and lines[-1].strip() \
                    and not re.match(r'^\s*([-*+]|\d+\.)\s+', lines[-1]):
                lines.append('')
            lines.append(line)
        # Escape raw HTML first: pitch text comes from AI and users
        source = html.escape('\n'.join(lines), quote=False)
        return markdown.markdown(source, extensions=['sane_lists', 'nl2br', 'tables'])
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
