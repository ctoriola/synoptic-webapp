from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_login import current_user
from firebase_models import User
import os
import markdown

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('landing.html')

@main_bp.route('/init-admin')
def init_admin():
    """Initialize admin user - for development only"""
    from firebase_models import User
    
    # Check if admin already exists
    admin = User.get_by_username('admin')
    if admin:
        return "Admin user already exists!"
    
    # Create admin user
    admin = User(
        username='admin',
        email='admin@synoptic.com',
        is_admin=True,
        account_tier='pro',
        tokens=50
    )
    admin.set_password('admin123')  # Change this in production!
    
    if admin.save():
        return "Admin user created successfully! Username: admin, Password: admin123"
    else:
        return "Failed to create admin user"

@main_bp.route('/migrate-users')
def migrate_users():
    """Migrate existing users to free tier - run once after deployment"""
    from firebase_models import User
    from firebase_config import get_db
    
    db = get_db()
    if not db:
        return "Database connection failed"
    
    updated_count = 0
    users_collection = db.collection('users')
    
    # Get all users
    docs = users_collection.stream()
    
    for doc in docs:
        data = doc.to_dict()
        
        # Check if user already has account_tier and tokens
        if 'account_tier' not in data or 'tokens' not in data:
            # Update user with free tier defaults
            users_collection.document(doc.id).update({
                'account_tier': 'free',
                'tokens': 3
            })
            updated_count += 1
    
    return f"Migration completed! Updated {updated_count} users to free tier with 3 tokens."

@main_bp.route('/init-db')
def init_database():
    """Initialize Firebase database for production deployment"""
    try:
        # Create admin user if it doesn't exist
        admin = User.get_by_email('admin@synoptic.com')
        if not admin:
            admin = User(
                email='admin@synoptic.com',
                username='admin',
                is_admin=True
            )
            admin.set_password('admin123')
            admin.save()
            
        return jsonify({
            'status': 'success',
            'message': 'Firebase database initialized successfully',
            'admin_user_created': True,
            'admin_credentials': {
                'email': 'admin@synoptic.com',
                'password': 'admin123'
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Database initialization failed: {str(e)}'
        }), 500

@main_bp.route('/features')
def features():
    return render_template('features.html')

@main_bp.route('/pricing')
def pricing():
    return render_template('pricing.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')
