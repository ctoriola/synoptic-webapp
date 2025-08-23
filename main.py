from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_login import current_user
from firebase_models import User
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('landing.html')

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
