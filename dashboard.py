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
    
    # If coming from GitHub selection, auto-generate immediately
    if from_github and selected_repo:
        # Import here to avoid circular imports
        from api import try_fetch_readme_raw, try_fetch_readme_api, fetch_additional_repo_signals
        from firebase_models import Project
        import google.generativeai as genai
        import os
        from datetime import datetime
        
        try:
            # Check if user has tokens
            if not current_user.can_generate_pitch_deck():
                flash('No tokens available for pitch deck generation', 'error')
                return redirect(url_for('dashboard.index'))
            
            repo_url = selected_repo['url']
            repo_owner = selected_repo['owner']
            repo_name = selected_repo['name']
            
            # Debug session data
            print(f"DEBUG: Selected repo data: {selected_repo}")
            print(f"DEBUG: User token exists: {bool(current_user.github_token)}")
            
            # For private repos, skip raw fetch and go directly to API with token
            user_token = current_user.github_token if current_user.is_authenticated else None
            if user_token:
                # Private repo - use API directly with user token
                content, source = try_fetch_readme_api(repo_owner, repo_name, user_token)
                print(f"DEBUG: API fetch result: {'Found' if content else 'Not found'}")
            else:
                # Public repo - try raw first, then API
                content, source = try_fetch_readme_raw(repo_owner, repo_name)
                if not content:
                    content, _ = try_fetch_readme_api(repo_owner, repo_name, user_token)
            
            if not content:
                flash(f'README not found in repository {repo_owner}/{repo_name}. This may be a private repository or it may not have a README file.', 'error')
                return redirect(url_for('dashboard.index'))
            
            # Configure Gemini AI
            GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
            if not GOOGLE_API_KEY:
                flash('AI service not configured', 'error')
                return redirect(url_for('dashboard.index'))
            
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Get additional repo signals
            user_token = current_user.github_token if current_user.is_authenticated else None
            extra = fetch_additional_repo_signals(repo_owner, repo_name, user_token)
            
            # Generate pitch deck content
            prompt = f"""Generate a comprehensive pitch deck for the following GitHub repository:

Project: {repo_name}
Repository: {repo_owner}/{repo_name}

README Content:\n{content}\n\n

Please generate a detailed pitch deck with the following slides:

**Slide 1: Title Slide**
   - Project name and tagline
   - Team/creator information
   - Date

**Slide 2: Problem**
   - What problem does this project solve?
   - Pain points and market gaps
   - Why this matters now

**Slide 3: Solution**
   - How does this project address the problem?
   - Key features and functionality
   - Unique value proposition

**Slide 4: Market Opportunity**
   - Target market size
   - User personas and segments
   - Market trends and timing

**Slide 5: Product Demo**
   - Key features walkthrough
   - Screenshots or code examples
   - User experience highlights

**Slide 6: Business Model**
   - Revenue streams
   - Pricing strategy
   - Go-to-market approach

**Slide 7: Traction & Metrics**
   - User adoption
   - Performance metrics
   - Community engagement

**Slide 8: Competition**
   - Competitive landscape
   - Competitive advantages
   - Market positioning

**Slide 9: Technology**
   - Technical architecture
   - Scalability considerations
   - Security and reliability

**Slide 10: Team**
   - Core team members
   - Relevant experience
   - Advisory board

**Slide 11: Financials**
   - Revenue projections
   - Cost structure
   - Funding requirements

**Slide 12: Funding Ask**
   - Amount seeking
   - Use of funds
   - Expected outcomes

**Slide 13: Next Steps**
   - Immediate milestones
   - Long-term vision
   - Call to action

Additional context: {extra}

Format the response as a comprehensive pitch deck with clear sections and professional language suitable for investors."""
            
            response = model.generate_content(prompt)
            pitch_deck_content = response.text
            
            # Create project
            project = Project(
                title=repo_name,
                repo_url=repo_url,
                repo_owner=repo_owner,
                repo_name=repo_name,
                pitch_deck={
                    'content': pitch_deck_content,
                    'generated_at': datetime.utcnow().isoformat(),
                    'version': '1.0'
                },
                user_id=current_user.id
            )
            
            project.save()
            current_user.use_token()
            
            # Clear session data
            session.pop('selected_repo', None)
            
            flash('Pitch deck generated successfully!', 'success')
            return redirect(url_for('dashboard.project_detail', project_id=project.id))
            
        except Exception as e:
            flash(f'Failed to generate pitch deck: {str(e)}', 'error')
            return redirect(url_for('dashboard.index'))
    
    # Regular generator page for manual URL entry
    return render_template('dashboard/generator.html', from_github=from_github)

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

@dashboard_bp.route('/projects/<project_id>/rename', methods=['POST'])
@login_required
def rename_project(project_id):
    """Rename a project"""
    try:
        project = Project.get(project_id)
        if not project or project.user_id != current_user.id:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        new_title = data.get('title', '').strip()
        
        if not new_title:
            return jsonify({'error': 'Title is required'}), 400
        
        project.title = new_title
        project.save()
        
        return jsonify({'success': True, 'message': 'Project renamed successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to rename project: {str(e)}'}), 500

@dashboard_bp.route('/settings')
@login_required
def settings():
    # Get user's project statistics
    user_projects = Project.get_by_user(current_user.id)
    stats = {
        'total_projects': len(user_projects)
    }
    
    # Get user preferences from session
    preferences = session.get('user_preferences', {
        'default_style': 'investor',
        'slide_count': '12',
        'include_financials': True,
        'include_competition': True
    })
    
    return render_template('dashboard/settings.html', stats=stats, preferences=preferences)

@dashboard_bp.route('/settings/profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        
        if not username or not email:
            return jsonify({'error': 'Username and email are required'}), 400
        
        # Check if username is already taken by another user
        existing_user = User.get_by_username(username)
        if existing_user and existing_user.id != current_user.id:
            return jsonify({'error': 'Username already taken'}), 400
        
        # Check if email is already taken by another user
        existing_user = User.get_by_email(email)
        if existing_user and existing_user.id != current_user.id:
            return jsonify({'error': 'Email already taken'}), 400
        
        # Update user information
        current_user.username = username
        current_user.email = email
        current_user.save()
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

@dashboard_bp.route('/settings/password', methods=['POST'])
@login_required
def update_password():
    """Update user password"""
    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords are required'}), 400
        
        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Update password
        current_user.set_password(new_password)
        current_user.save()
        
        return jsonify({'success': True, 'message': 'Password updated successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to update password: {str(e)}'}), 500

@dashboard_bp.route('/settings/preferences', methods=['POST'])
@login_required
def update_preferences():
    """Update user preferences"""
    try:
        data = request.get_json()
        # For now, we'll store preferences in session or could extend User model
        # This is a placeholder for future preference storage
        session['user_preferences'] = {
            'default_style': data.get('default_style', 'investor'),
            'slide_count': data.get('slide_count', '12'),
            'include_financials': data.get('include_financials', True),
            'include_competition': data.get('include_competition', True)
        }
        
        return jsonify({'success': True, 'message': 'Preferences saved successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to save preferences: {str(e)}'}), 500

@dashboard_bp.route('/settings/disconnect-github', methods=['POST'])
@login_required
def disconnect_github():
    """Disconnect GitHub account"""
    try:
        current_user.github_id = None
        current_user.github_username = None
        current_user.github_token = None
        current_user.save()
        
        return jsonify({'success': True, 'message': 'GitHub account disconnected'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to disconnect GitHub: {str(e)}'}), 500

@dashboard_bp.route('/settings/export', methods=['POST'])
@login_required
def export_data():
    """Export user data"""
    try:
        # Get all user projects
        projects = Project.get_by_user(current_user.id)
        
        export_data = {
            'user': {
                'username': current_user.username,
                'email': current_user.email,
                'account_tier': current_user.account_tier,
                'tokens': current_user.tokens,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None
            },
            'projects': []
        }
        
        for project in projects:
            export_data['projects'].append({
                'id': project.id,
                'title': project.title,
                'repo_url': project.repo_url,
                'repo_owner': project.repo_owner,
                'repo_name': project.repo_name,
                'pitch_deck': project.pitch_deck,
                'created_at': project.created_at.isoformat() if project.created_at else None
            })
        
        from flask import make_response
        import json
        
        response = make_response(json.dumps(export_data, indent=2))
        response.headers['Content-Type'] = 'application/json'
        response.headers['Content-Disposition'] = 'attachment; filename=synoptic-data-export.json'
        
        return response
    
    except Exception as e:
        return jsonify({'error': f'Failed to export data: {str(e)}'}), 500

@dashboard_bp.route('/settings/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    try:
        # Delete all user projects
        projects = Project.get_by_user(current_user.id)
        for project in projects:
            project.delete()
        
        # Delete user account
        from firebase_config import get_db
        db = get_db()
        if db:
            db.collection('users').document(current_user.id).delete()
        
        # Logout user
        from flask_login import logout_user
        logout_user()
        
        return jsonify({'success': True, 'message': 'Account deleted successfully'})
    
    except Exception as e:
        return jsonify({'error': f'Failed to delete account: {str(e)}'}), 500
