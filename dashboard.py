from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
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
    # Check if coming from GitHub repo selection
    from_github = request.args.get('from_github')
    selected_repo = session.get('selected_repo')
    
    # Pre-fill repo URL if coming from GitHub selection
    repo_url = None
    if from_github and selected_repo:
        repo_url = selected_repo.get('url')
        # Clear the session data after using it
        session.pop('selected_repo', None)
    
    return render_template('dashboard/generator.html', 
                         prefilled_repo_url=repo_url,
                         from_github=from_github)

@dashboard_bp.route('/documentation/<project_id>')
@login_required
def documentation(project_id):
    """View project documentation"""
    project = Project.get(project_id)
    
    if not project or project.user_id != current_user.id:
        flash('Project not found or access denied.', 'error')
        return redirect(url_for('dashboard.projects'))
    
    return render_template('dashboard/documentation.html', project=project)

@dashboard_bp.route('/user-guide/<project_id>')
@login_required
def user_guide(project_id):
    """View project user guide"""
    project = Project.get(project_id)
    
    if not project or project.user_id != current_user.id:
        flash('Project not found or access denied.', 'error')
        return redirect(url_for('dashboard.projects'))
    
    return render_template('dashboard/user_guide.html', project=project)

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
    
    # Get user information for each project
    projects_with_users = []
    for project in projects:
        user = User.get(project.user_id) if project.user_id else None
        project_data = {
            'project': project,
            'user': user
        }
        projects_with_users.append(project_data)
    
    return render_template('dashboard/admin_projects.html', projects_with_users=projects_with_users)

@dashboard_bp.route('/projects')
@login_required
def projects():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    search = request.args.get('search', '')
    
    if search:
        all_projects = Project.search_by_user(current_user.id, search)
    else:
        all_projects = Project.get_by_user(current_user.id)
    
    # Manual pagination since we're using Firebase
    total = len(all_projects)
    start = (page - 1) * per_page
    end = start + per_page
    items = all_projects[start:end]
    
    # Create a mock pagination object
    class MockPagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None
            
        def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
            last = self.pages
            for num in range(1, last + 1):
                if num <= left_edge or \
                   (self.page - left_current - 1 < num < self.page + right_current) or \
                   num > last - right_edge:
                    yield num
    
    projects = MockPagination(items, page, per_page, total)
    
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
