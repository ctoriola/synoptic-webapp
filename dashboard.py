from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from firebase_models import Project, User
from datetime import datetime
from functools import wraps

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/')
@login_required
def index():
    # Get user's recent projects
    recent_projects = Project.get_by_user(current_user.id, limit=5)
    
    stats = {
        'total_projects': len(Project.get_by_user(current_user.id)),
        'recent_count': len(recent_projects)
    }
    
    return render_template('dashboard/index.html', 
                         recent_projects=recent_projects, 
                         stats=stats)

@dashboard_bp.route('/generator')
@login_required
def generator():
    return render_template('dashboard/generator.html')

@dashboard_bp.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if query:
        projects = Project.search_by_user(current_user.id, query)
    else:
        projects = []
    
    return jsonify([{
        'id': p.id,
        'title': p.title,
        'repo_url': p.repo_url,
        'created_at': p.created_at.isoformat() if p.created_at else None
    } for p in projects])

@dashboard_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard with user statistics"""
    # Get statistics
    total_users = User.get_user_count()
    total_projects = Project.get_project_count()
    total_generations = Project.get_generation_count()
    
    # Get recent users and projects
    recent_users = User.get_all_users(limit=10)
    recent_projects = Project.get_all_projects(limit=10)
    
    stats = {
        'total_users': total_users,
        'total_projects': total_projects,
        'total_generations': total_generations
    }
    
    return render_template('dashboard/admin.html', 
                         stats=stats, 
                         recent_users=recent_users,
                         recent_projects=recent_projects)

@dashboard_bp.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Admin user management page"""
    users = User.get_all_users(limit=100)
    return render_template('dashboard/admin_users.html', users=users)

@dashboard_bp.route('/admin/projects')
@login_required
@admin_required
def admin_projects():
    """Admin project management page"""
    projects = Project.get_all_projects(limit=100)
    return render_template('dashboard/admin_projects.html', projects=projects)

@dashboard_bp.route('/projects')
@login_required
def projects():
    search = request.args.get('search', '')
    if search:
        projects = Project.search_by_user(current_user.id, search, limit=50)
    else:
        projects = Project.get_by_user(current_user.id, limit=50)
    
    return render_template('dashboard/projects.html', projects=projects, search=search)

@dashboard_bp.route('/projects/<project_id>')
@login_required
def project_detail(project_id):
    project = Project.get(project_id)
    if not project or project.user_id != current_user.id:
        flash('Project not found', 'error')
        return redirect(url_for('dashboard.projects'))
    return render_template('dashboard/project_detail.html', project=project)

@dashboard_bp.route('/projects/<project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.get(project_id)
    if not project or project.user_id != current_user.id:
        flash('Project not found', 'error')
        return redirect(url_for('dashboard.projects'))
    
    if project.delete():
        flash('Project deleted successfully', 'success')
    else:
        flash('Failed to delete project', 'error')
    return redirect(url_for('dashboard.projects'))

@dashboard_bp.route('/settings')
@login_required
def settings():
    return render_template('dashboard/settings.html')
