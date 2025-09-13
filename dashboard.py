from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, current_user
from firebase_models import Project, User, Survey, SurveyResponse, Coupon
from datetime import datetime
from functools import wraps

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def _has_generation_access(user):
    """Check if user has access to generate pitch decks"""
    # Free tier users have no access
    if user.account_tier == 'free':
        return user.tokens and user.tokens > 0
    
    # Waitlisted users can generate if they completed survey and haven't used export
    if user.account_tier == 'waitlisted':
        return user.survey_completed and not user.survey_export_used
    
    # Basic and Pro users need tokens
    if user.account_tier in ['basic', 'pro']:
        return user.tokens and user.tokens > 0
    
    return False

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
        from api import try_fetch_readme_raw, try_fetch_readme_api, fetch_additional_repo_signals, analyze_repository_structure, build_gemini_prompt_from_code
        from firebase_models import Project
        import google.generativeai as genai
        import os
        import json
        from datetime import datetime
        
        try:
            repo_url = selected_repo['url']
            repo_owner = selected_repo['owner']
            repo_name = selected_repo['name']
            
            # Create a preliminary project to save user's work before generation
            preliminary_project = Project(
                title=repo_name,
                repo_url=repo_url,
                repo_owner=repo_owner,
                repo_name=repo_name,
                pitch_deck={
                    'content': 'Generation in progress...',
                    'generated_at': datetime.utcnow().isoformat(),
                    'version': '0.1',
                    'status': 'generating'
                },
                user_id=current_user.id
            )
            preliminary_project.save()
            
            # All users can generate projects - token checks only apply to exports
            
            # Debug session data
            print(f"DEBUG: Selected repo data: {selected_repo}")
            print(f"DEBUG: User token exists: {bool(current_user.github_token)}")
            print(f"DEBUG: Fetching README for {repo_owner}/{repo_name}")
            
            # Configure Gemini AI first (needed for both paths)
            GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
            if not GOOGLE_API_KEY:
                flash('AI service not configured', 'error')
                return redirect(url_for('dashboard.index'))
            
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Try to get README content
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
                print(f"DEBUG: No README found for {repo_owner}/{repo_name}, analyzing code structure instead")
                
                # Use code analysis instead of README
                repo_analysis = analyze_repository_structure(repo_owner, repo_name, user_token)
                
                if not repo_analysis.get("tech_stack") and repo_analysis.get("main_language") == "Unknown":
                    flash('Unable to analyze repository structure. Repository may be empty or inaccessible.', 'error')
                    return redirect(url_for('dashboard.generator'))
                
                # Generate content from code analysis
                prompt = build_gemini_prompt_from_code(repo_analysis, repo_name, extra_context=None)
                resp = model.generate_content(prompt)
                
                text = getattr(resp, 'text', None) or (resp.candidates[0].content.parts[0].text if getattr(resp, 'candidates', None) else None)
                if not text:
                    flash('Failed to generate content from AI service', 'error')
                    return redirect(url_for('dashboard.generator'))
                
                # Parse JSON response
                try:
                    parsed = json.loads(text.strip())
                except json.JSONDecodeError as e:
                    flash(f'Invalid response format from AI service: {str(e)}', 'error')
                    return redirect(url_for('dashboard.generator'))
                
                # Map the response to expected format (code analysis uses different keys)
                analysis_result = {
                    "title": parsed.get("project_title", repo_name),
                    "introduction": parsed.get("solution_overview", "Project analysis based on code structure."),
                    "problem_statement": parsed.get("problem_statement", "Problem inferred from code analysis."),
                    "solution_overview": parsed.get("solution_overview", "Solution based on technical implementation."),
                    "key_features": parsed.get("key_features", "Features inferred from codebase."),
                    "target_audience": parsed.get("target_audience", "Target audience based on technical stack."),
                    "technology_stack": parsed.get("technology_stack", "Technology stack detected from code."),
                    "future_scope": parsed.get("future_scope", "Future enhancements based on current foundation.")
                }
                
                content_source = "code_analysis"
                print(f"DEBUG: Generated content from code analysis for {repo_owner}/{repo_name}")
            else:
                # README found - process normally
                content_source = "readme"
                print(f"DEBUG: Found README for {repo_owner}/{repo_name}")
            
            
            # Generate pitch deck content based on source
            if content_source == "code_analysis":
                # Already have analysis_result from code analysis
                pass
            else:
                # Process README content normally
                user_token = current_user.github_token if current_user.is_authenticated else None
                extra = fetch_additional_repo_signals(repo_owner, repo_name, user_token)
                
                # Generate pitch deck content from README
                prompt = f"""Generate a comprehensive pitch deck for the following GitHub repository:

Project: {repo_name}
Repository: {repo_owner}/{repo_name}

README Content:\n{content}\n\n

Please generate a detailed pitch deck with the following slides. Use ONLY plain text formatting - NO markdown symbols like ** or ## or - bullets. Format each slide clearly with the slide number and title, followed by content in bullet points using simple dashes:

Slide 1: Title Slide
   Project name and compelling tagline
   Creator/team information
   Current date

Slide 2: Problem Statement
   What critical problem does this project solve
   Current pain points in the market
   Why this problem needs solving now

Slide 3: Solution Overview
   How this project uniquely addresses the problem
   Core features and key functionality
   What makes this solution different

Slide 4: Market Opportunity
   Target market size and potential
   Key user segments and personas
   Market trends supporting this solution

Slide 5: Product Demonstration
   Key features and capabilities
   Technical highlights and innovations
   User experience benefits

Slide 6: Business Model
   Revenue generation strategy
   Pricing approach and monetization
   Go-to-market strategy

Slide 7: Traction and Growth
   Current user adoption and metrics
   Performance indicators and milestones
   Community engagement and feedback

Slide 8: Competitive Analysis
   Current competitive landscape
   Key competitive advantages
   Market differentiation strategy

Slide 9: Technology Stack
   Technical architecture overview
   Scalability and performance considerations
   Security and reliability features

Slide 10: Team and Expertise
   Core team members and their roles
   Relevant experience and background
   Advisory support and partnerships

Slide 11: Financial Projections
   Revenue forecasts and growth projections
   Cost structure and unit economics
   Funding requirements and timeline

Slide 12: Investment Ask
   Specific funding amount requested
   Detailed use of funds breakdown
   Expected milestones and outcomes

Slide 13: Next Steps and Vision
   Immediate development milestones
   Long-term product vision
   Partnership and growth opportunities

Additional context: {extra}

IMPORTANT: Use only plain text formatting. No markdown symbols. Keep content concise and investor-focused. Each slide should have 3-5 key points maximum."""
            
            response = model.generate_content(prompt)
            pitch_deck_content = response.text
            
            # Update the preliminary project with the generated content
            preliminary_project.pitch_deck = {
                'content': pitch_deck_content,
                'generated_at': datetime.utcnow().isoformat(),
                'version': '1.0',
                'status': 'completed'
            }
            preliminary_project.save()
            # No token usage for generation - tokens are only for exports
            
            # Clear session data
            session.pop('selected_repo', None)
            
            flash('Pitch deck generated successfully!', 'success')
            return redirect(url_for('dashboard.project_detail', project_id=preliminary_project.id))
            
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
def admin():
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
            
            return jsonify({
                'success': True,
                'message': 'Survey completed successfully! You can now export your pitch deck.',
                'redirect': url_for('dashboard.index')
            })
        else:
            return jsonify({'error': 'Error saving survey response. Please try again.'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Error submitting survey: {str(e)}'}), 500


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
    """Create new survey with AI-generated or manual questions"""
    if request.method == 'POST':
        try:
            survey_title = request.form.get('title', 'User Feedback Survey')
            creation_method = request.form.get('creation_method', 'ai')
            
            if creation_method == 'manual':
                # Handle manual survey creation
                questions = []
                form_data = request.form
                
                # Extract questions from form data
                question_indices = set()
                for key in form_data.keys():
                    if key.startswith('questions[') and key.endswith('][text]'):
                        # Extract index from questions[0][text] format
                        index = key.split('[')[1].split(']')[0]
                        question_indices.add(int(index))
                
                for i in sorted(question_indices):
                    question_text = form_data.get(f'questions[{i}][text]', '').strip()
                    question_type = form_data.get(f'questions[{i}][type]', 'text')
                    question_options = form_data.get(f'questions[{i}][options]', '').strip()
                    
                    if question_text:  # Only add non-empty questions
                        question_data = {
                            "question": question_text,
                            "type": question_type
                        }
                        
                        # Add options for multiple choice questions
                        if question_type in ['radio', 'checkbox'] and question_options:
                            options = [opt.strip() for opt in question_options.split('\n') if opt.strip()]
                            question_data["options"] = options
                        elif question_type == 'rating':
                            question_data["scale"] = 5
                            
                        questions.append(question_data)
                
                if not questions:
                    flash('Please add at least one question.', 'error')
                    return render_template('dashboard/admin_new_survey.html')
                    
            else:
                # AI generation
                import google.generativeai as genai
                import os
                
                # Configure Gemini AI
                genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
                model = genai.GenerativeModel('gemini-1.5-flash')
            
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
            'response': {
                'id': response.id,
                'user_id': response.user_id,
                'responses': response.responses,
                'created_at': response.created_at.isoformat() if response.created_at else None
            },
            'user': {
                'id': user.id if user else None,
                'username': user.username if user else 'Unknown',
                'email': user.email if user else 'Unknown'
            }
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
            'question': {
                'question': question.get('question', ''),
                'type': question.get('type', ''),
                'options': question.get('options', [])
            },
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

@dashboard_bp.route('/admin/coupons/<coupon_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_coupon(coupon_id):
    coupon = Coupon.get_by_id(coupon_id)
    if not coupon:
        flash('Coupon not found', 'error')
        return redirect(url_for('dashboard.admin_coupons'))
    
    if request.method == 'POST':
        try:
            # Update coupon details
            coupon.discount_type = request.form.get('discount_type')
            coupon.discount_value = float(request.form.get('discount_value'))
            coupon.applies_to = request.form.get('applies_to')
            coupon.max_uses = int(request.form.get('max_uses', 0)) if request.form.get('max_uses') else None
            
            # Handle expiration date
            expires_at = request.form.get('expires_at')
            if expires_at:
                coupon.expires_at = datetime.strptime(expires_at, '%Y-%m-%d')
            else:
                coupon.expires_at = None
            
            coupon.save()
            flash('Coupon updated successfully!', 'success')
            return redirect(url_for('dashboard.admin_coupons'))
            
        except Exception as e:
            flash(f'Error updating coupon: {str(e)}', 'error')
    
    return render_template('dashboard/admin_edit_coupon.html', coupon=coupon)

@dashboard_bp.route('/admin/surveys/<survey_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_survey(survey_id):
    survey = Survey.get(survey_id)
    if not survey:
        flash('Survey not found', 'error')
        return redirect(url_for('dashboard.admin_surveys'))
    
    if request.method == 'POST':
        try:
            survey.title = request.form.get('title')
            
            # Parse questions from form
            questions = []
            question_count = int(request.form.get('question_count', 0))
            
            for i in range(question_count):
                question_text = request.form.get(f'question_{i}_text')
                question_type = request.form.get(f'question_{i}_type')
                
                if question_text and question_type:
                    question = {
                        'text': question_text,
                        'type': question_type
                    }
                    
                    # Add options for multiple choice questions
                    if question_type == 'multiple_choice':
                        options = []
                        for j in range(5):  # Max 5 options
                            option = request.form.get(f'question_{i}_option_{j}')
                            if option:
                                options.append(option)
                        question['options'] = options
                    
                    questions.append(question)
            
            survey.questions = questions
            survey.save()
            
            flash('Survey updated successfully!', 'success')
            return redirect(url_for('dashboard.admin_surveys'))
            
        except Exception as e:
            flash(f'Error updating survey: {str(e)}', 'error')
    
    return render_template('dashboard/admin_edit_survey.html', survey=survey)

@dashboard_bp.route('/admin/user-management')
@login_required
@admin_required
def admin_user_management():
    try:
        users = User.get_all_users()
        return render_template('dashboard/admin_user_management.html', users=users)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return redirect(url_for('dashboard.admin'))

@dashboard_bp.route('/admin/user-management/<user_id>/change-plan', methods=['POST'])
@login_required
@admin_required
def admin_change_user_plan(user_id):
    try:
        user = User.get(user_id)
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('dashboard.admin_user_management'))
        
        new_plan = request.form.get('new_plan')
        if new_plan not in ['free', 'basic', 'pro', 'waitlisted']:
            flash('Invalid plan selected', 'error')
            return redirect(url_for('dashboard.admin_user_management'))
        
        old_plan = user.account_tier
        user.account_tier = new_plan
        
        # Reset survey fields if changing to waitlisted
        if new_plan == 'waitlisted':
            user.survey_completed = False
            user.survey_export_used = False
        
        user.save()
        
        flash(f'User {user.username} plan changed from {old_plan} to {new_plan}', 'success')
        
    except Exception as e:
        flash(f'Error changing user plan: {str(e)}', 'error')
    
    return redirect(url_for('dashboard.admin_user_management'))

@dashboard_bp.route('/admin/survey-analytics')
@login_required
@admin_required
def admin_survey_analytics():
    try:
        surveys = Survey.get_all()
        analytics_data = []
        
        for survey in surveys:
            responses = SurveyResponse.get_all_by_survey(survey.id)
            
            # Calculate analytics
            total_responses = len(responses)
            completion_rate = 0
            avg_ratings = {}
            
            if total_responses > 0:
                # Calculate average ratings for rating questions
                for i, question in enumerate(survey.questions):
                    if question.get('type') == 'rating':
                        ratings = []
                        for response in responses:
                            # Use question index as key (stored as string)
                            answer = response.responses.get(str(i))
                            if answer and str(answer).isdigit():
                                ratings.append(int(answer))
                        
                        if ratings:
                            avg_ratings[question['question']] = sum(ratings) / len(ratings)
            
            analytics_data.append({
                'survey': survey,
                'total_responses': total_responses,
                'avg_ratings': avg_ratings,
                'responses': responses
            })
        
        return render_template('dashboard/admin_survey_analytics.html', analytics_data=analytics_data)
        
    except Exception as e:
        flash(f'Error loading survey analytics: {str(e)}', 'error')
        return redirect(url_for('dashboard.admin'))

@dashboard_bp.route('/out-of-tokens')
@login_required
def out_of_tokens():
    """Page shown when users are out of tokens"""
    try:
        # Get user's project count for stats
        user_projects = Project.get_by_user(current_user.id)
        user_projects_count = len(user_projects) if user_projects else 0
        
        # Check if there's an interrupted project in session
        interrupted_project_id = session.get('interrupted_project_id')
        interrupted_project = None
        if interrupted_project_id:
            interrupted_project = Project.get(interrupted_project_id)
            # Clear from session after retrieving
            session.pop('interrupted_project_id', None)
        
        return render_template('dashboard/out_of_tokens.html', 
                             user_projects_count=user_projects_count,
                             interrupted_project=interrupted_project)
    except Exception as e:
        flash(f'Error loading page: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))
