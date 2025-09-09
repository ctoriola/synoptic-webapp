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
            # Generation is now free - no token check needed
            
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
            # No token usage for generation - tokens are only for exports
            
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
    deleted_users = User.get_deleted_users(limit=100)
    return render_template('dashboard/admin_users.html', users=users, deleted_users=deleted_users)

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
        response.headers['Content-Disposition'] = 'attachment; filename=PitchPerfectAI-data-export.json'
        
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
        
        # Delete user account using the User model's delete method
        if current_user.delete():
            # Logout user
            from flask_login import logout_user
            logout_user()
            return jsonify({'success': True, 'message': 'Account deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete user account'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Failed to delete account: {str(e)}'}), 500


@dashboard_bp.route('/survey')
@login_required
def survey():
    """Display survey for waitlisted users"""
    if current_user.account_tier != 'waitlisted':
        flash('Survey is only available for waitlisted users.', 'info')
        return redirect(url_for('dashboard.index'))
    
    if current_user.survey_completed:
        flash('You have already completed the survey.', 'info')
        return redirect(url_for('dashboard.index'))
    
    from firebase_models import Survey
    active_survey = Survey.get_active()
    
    if not active_survey:
        flash('No survey is currently available.', 'info')
        return redirect(url_for('dashboard.index'))
    
    return render_template('dashboard/survey.html', survey=active_survey)


@dashboard_bp.route('/survey/submit', methods=['POST'])
@login_required
def submit_survey():
    """Submit survey responses"""
    if current_user.account_tier != 'waitlisted':
        return jsonify({'error': 'Survey is only available for waitlisted users'}), 403
    
    if current_user.survey_completed:
        return jsonify({'error': 'You have already completed the survey'}), 400
    
    try:
        from firebase_models import Survey, SurveyResponse
        
        active_survey = Survey.get_active()
        if not active_survey:
            return jsonify({'error': 'No active survey found'}), 404
        
        # Get responses from form
        responses = {}
        for i, question in enumerate(active_survey.questions):
            response_key = f'question_{i}'
            if response_key in request.form:
                responses[str(i)] = request.form[response_key]
        
        # Save survey response
        survey_response = SurveyResponse(
            survey_id=active_survey.id,
            user_id=current_user.id,
            responses=responses
        )
        
        if survey_response.save():
            # Mark user as having completed survey
            current_user.survey_completed = True
            current_user.save()
            
            flash('Survey completed successfully! You can now export your pitch deck.', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            return jsonify({'error': 'Failed to save survey responses'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Failed to submit survey: {str(e)}'}), 500


# Admin routes for survey management
@dashboard_bp.route('/admin/surveys')
@login_required
@admin_required
def admin_surveys():
    """Admin survey management"""
    from firebase_models import Survey
    surveys = Survey.get_all()
    return render_template('dashboard/admin_surveys.html', surveys=surveys)


@dashboard_bp.route('/admin/surveys/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_new_survey():
    """Create new survey with Gemini-generated questions"""
    if request.method == 'POST':
        try:
            import google.generativeai as genai
            import os
            
            # Configure Gemini AI
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            model = genai.GenerativeModel('gemini-pro')
            
            survey_title = request.form.get('title', 'User Feedback Survey')
            
            # Generate survey questions using Gemini
            prompt = """
            Generate 8-10 survey questions for users of a pitch deck generation AI tool. 
            The questions should help us understand:
            1. User's business background and experience
            2. What they're looking for in a pitch deck tool
            3. Their pain points with current solutions
            4. Feature preferences and priorities
            5. Feedback on AI-generated content quality
            
            Return the questions as a JSON array of objects with this format:
            [
                {"question": "What is your primary role?", "type": "multiple_choice", "options": ["Entrepreneur", "Startup Founder", "Business Analyst", "Other"]},
                {"question": "How would you rate the quality of AI-generated content?", "type": "rating", "scale": 5},
                {"question": "What features are most important to you?", "type": "text"}
            ]
            
            Question types can be: "text", "multiple_choice", "rating", "yes_no"
            """
            
            response = model.generate_content(prompt)
            
            # Parse the JSON response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if json_match:
                questions_json = json_match.group()
                questions = json.loads(questions_json)
            else:
                # Fallback questions if Gemini fails
                questions = [
                    {"question": "What is your primary role?", "type": "multiple_choice", "options": ["Entrepreneur", "Startup Founder", "Business Analyst", "Investor", "Other"]},
                    {"question": "How many pitch decks have you created before?", "type": "multiple_choice", "options": ["0", "1-3", "4-10", "10+"]},
                    {"question": "What's your biggest challenge in creating pitch decks?", "type": "text"},
                    {"question": "How important is AI-generated content quality to you?", "type": "rating", "scale": 5},
                    {"question": "Would you recommend this tool to others?", "type": "yes_no"},
                    {"question": "What features would you like to see added?", "type": "text"},
                    {"question": "How satisfied are you with the current tool?", "type": "rating", "scale": 5},
                    {"question": "What's your industry or business sector?", "type": "text"}
                ]
            
            # Create and save survey
            from firebase_models import Survey
            
            # Deactivate existing surveys
            existing_surveys = Survey.get_all()
            for survey in existing_surveys:
                if survey.is_active:
                    survey.is_active = False
                    survey.save()
            
            new_survey = Survey(
                title=survey_title,
                questions=questions,
                is_active=True
            )
            
            if new_survey.save():
                flash('Survey created successfully with AI-generated questions!', 'success')
                return redirect(url_for('dashboard.admin_surveys'))
            else:
                flash('Failed to save survey', 'error')
        
        except Exception as e:
            flash(f'Failed to create survey: {str(e)}', 'error')
    
    return render_template('dashboard/admin_new_survey.html')


@dashboard_bp.route('/admin/surveys/<survey_id>/responses')
@login_required
@admin_required
def admin_survey_responses(survey_id):
    """View survey responses and analytics"""
    from firebase_models import Survey, SurveyResponse, User
    
    survey = Survey.get(survey_id)
    if not survey:
        flash('Survey not found', 'error')
        return redirect(url_for('dashboard.admin_surveys'))
    
    responses = SurveyResponse.get_all_by_survey(survey_id)
    
    # Get user details for responses
    response_data = []
    for response in responses:
        user = User.get(response.user_id)
        response_data.append({
            'response': response,
            'user': user
        })
    
    # Generate analytics
    analytics = {
        'total_responses': len(responses),
        'question_analytics': {}
    }
    
    # Analyze each question
    for i, question in enumerate(survey.questions):
        question_responses = []
        for response in responses:
            if str(i) in response.responses:
                question_responses.append(response.responses[str(i)])
        
        analytics['question_analytics'][i] = {
            'question': question,
            'responses': question_responses,
            'response_count': len(question_responses)
        }
        
        # Add specific analytics based on question type
        if question.get('type') == 'rating':
            if question_responses:
                ratings = [int(r) for r in question_responses if r.isdigit()]
                if ratings:
                    analytics['question_analytics'][i]['average_rating'] = sum(ratings) / len(ratings)
        
        elif question.get('type') == 'multiple_choice':
            from collections import Counter
            analytics['question_analytics'][i]['option_counts'] = dict(Counter(question_responses))
    
    return render_template('dashboard/admin_survey_responses.html', 
                         survey=survey, 
                         response_data=response_data,
                         analytics=analytics)


# Admin routes for coupon management
@dashboard_bp.route('/admin/coupons')
@login_required
@admin_required
def admin_coupons():
    """Admin coupon management"""
    from firebase_models import Coupon
    coupons = Coupon.get_all()
    return render_template('dashboard/admin_coupons.html', coupons=coupons)


@dashboard_bp.route('/admin/coupons/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_new_coupon():
    """Create new coupon"""
    if request.method == 'POST':
        try:
            from firebase_models import Coupon
            from datetime import datetime, timedelta
            
            code = request.form.get('code', '').upper()
            discount_type = request.form.get('discount_type', 'percentage')
            discount_value = float(request.form.get('discount_value', 0))
            applies_to = request.form.get('applies_to', 'all')
            max_uses = request.form.get('max_uses')
            expires_days = request.form.get('expires_days')
            
            # Validate required fields
            if not code:
                flash('Coupon code is required', 'error')
                return render_template('dashboard/admin_new_coupon.html')
            
            # Check if coupon code already exists
            existing_coupon = Coupon.get_by_code(code)
            if existing_coupon:
                flash('Coupon code already exists', 'error')
                return render_template('dashboard/admin_new_coupon.html')
            
            # Calculate expiration date
            expires_at = None
            if expires_days:
                expires_at = datetime.utcnow() + timedelta(days=int(expires_days))
            
            # Create coupon
            coupon = Coupon(
                code=code,
                discount_type=discount_type,
                discount_value=discount_value,
                applies_to=applies_to,
                max_uses=int(max_uses) if max_uses else None,
                expires_at=expires_at
            )
            
            if coupon.save():
                flash(f'Coupon "{code}" created successfully!', 'success')
                return redirect(url_for('dashboard.admin_coupons'))
            else:
                flash('Failed to create coupon', 'error')
        
        except Exception as e:
            flash(f'Failed to create coupon: {str(e)}', 'error')
    
    return render_template('dashboard/admin_new_coupon.html')


@dashboard_bp.route('/admin/coupons/<coupon_id>/toggle', methods=['POST'])
@login_required
@admin_required
def admin_toggle_coupon(coupon_id):
    """Toggle coupon active status"""
    try:
        from firebase_models import Coupon
        
        coupon = Coupon.get_by_code(coupon_id)  # coupon_id is actually the code
        if not coupon:
            return jsonify({'error': 'Coupon not found'}), 404
        
        coupon.is_active = not coupon.is_active
        if coupon.save():
            return jsonify({'success': True, 'is_active': coupon.is_active})
        else:
            return jsonify({'error': 'Failed to update coupon'}), 500
    
    except Exception as e:
        return jsonify({'error': f'Failed to toggle coupon: {str(e)}'}), 500
