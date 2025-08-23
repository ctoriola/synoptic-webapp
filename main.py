from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_login import current_user
from models import db, User
from werkzeug.security import generate_password_hash
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('landing.html')

@main_bp.route('/init-db')
def init_database():
    """Initialize database tables for production deployment"""
    try:
        # Create all tables
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(email='admin@synoptic.com').first()
        if not admin:
            admin = User(
                email='admin@synoptic.com',
                username='admin',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            
        return jsonify({
            'status': 'success',
            'message': 'Database initialized successfully',
            'tables_created': True,
            'admin_user_created': True
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
