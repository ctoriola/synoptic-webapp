from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Project, db
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # Get user's recent projects
    recent_projects = Project.query.filter_by(user_id=current_user.id)\
                           .order_by(Project.updated_at.desc())\
                           .limit(5).all()
    
    stats = {
        'total_projects': current_user.project_count,
        'recent_count': len(recent_projects)
    }
    
    return render_template('dashboard/index.html', 
                         recent_projects=recent_projects, 
                         stats=stats)

@dashboard_bp.route('/generator')
@login_required
def generator():
    return render_template('dashboard/generator.html')

@dashboard_bp.route('/projects')
@login_required
def projects():
    page = request.args.get('page', 1, type=int)
    projects = Project.query.filter_by(user_id=current_user.id)\
                     .order_by(Project.updated_at.desc())\
                     .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('dashboard/projects.html', projects=projects)

@dashboard_bp.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    return render_template('dashboard/project_detail.html', project=project)

@dashboard_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    db.session.delete(project)
    db.session.commit()
    flash('Project deleted successfully', 'success')
    return redirect(url_for('dashboard.projects'))

@dashboard_bp.route('/settings')
@login_required
def settings():
    return render_template('dashboard/settings.html')
