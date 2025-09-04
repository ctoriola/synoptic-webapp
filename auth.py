from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from werkzeug.security import generate_password_hash, check_password_hash
from firebase_models import User
import os
import requests

auth_bp = Blueprint('auth', __name__)

# Initialize OAuth
oauth = OAuth()

def init_oauth(app):
    oauth.init_app(app)
    github = oauth.register(
        name='github',
        client_id=os.getenv('GITHUB_CLIENT_ID'),
        client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
        api_base_url='https://api.github.com/',
        client_kwargs={
            'scope': 'user:email'
        },
    )
    return github

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.get_by_email(email)
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required', 'error')
        elif password != confirm_password:
            flash('Passwords do not match', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
        elif User.get_by_email(email):
            flash('Email already registered', 'error')
        elif User.get_by_username(username):
            flash('Username already taken', 'error')
        else:
            try:
                # Create new user
                user = User(
                    username=username,
                    email=email
                )
                user.set_password(password)
                
                if user.save():
                    login_user(user)
                    flash('Registration successful! Welcome to PitchPerfectAI.', 'success')
                    return redirect(url_for('dashboard.index'))
                else:
                    flash('Registration failed. Please try again.', 'error')
            except Exception as e:
                flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/github')
def github_login():
    github = oauth.create_client('github')
    redirect_uri = url_for('auth.github_callback', _external=True)
    return github.authorize_redirect(redirect_uri)

@auth_bp.route('/github/callback')
def github_callback():
    """Handle GitHub OAuth callback"""
    try:
        github = oauth.create_client('github')
        token = github.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            # Fetch user info manually if not in token
            resp = github.get('user', token=token)
            user_info = resp.json()
        
        github_id = str(user_info.get('id'))
        email = user_info.get('email')
        username = user_info.get('login')
        
        if not github_id:
            flash('Failed to get GitHub user information', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if this is connecting GitHub to existing user
        connect_existing = session.pop('github_connect_existing', False)
        
        if connect_existing and current_user.is_authenticated:
            # Connect GitHub to current user
            current_user.github_id = github_id
            current_user.github_username = username
            current_user.github_token = token.get('access_token')
            current_user.save()
            flash('GitHub account connected successfully!', 'success')
            return redirect(url_for('dashboard.index'))
        
        # Check if user already exists with this GitHub ID
        existing_user = User.get_by_github_id(github_id)
        
        if existing_user:
            user = existing_user
        else:
            # Check if user exists with same email
            if email:
                user = User.get_by_email(email)
                if user:
                    # Link GitHub account to existing user
                    user.github_id = github_id
                    user.github_username = username
                    user.github_token = token.get('access_token')
                    user.save()
                else:
                    # Create new user
                    user = User(
                        email=email,
                        username=username or f"github_{github_id}",
                        github_id=github_id,
                        github_username=username,
                        github_token=token.get('access_token')
                    )
                    user.save()
            else:
                # Create user without email
                user = User(
                    username=username or f"github_{github_id}",
                    github_id=github_id,
                    github_username=username,
                    github_token=token.get('access_token')
                )
                user.save()
        
        # Update GitHub info if changed
        user.github_id = user_info.get('id')
        user.github_username = user_info.get('login')
        user.github_token = token.get('access_token')
        user.save()
        
        login_user(user)
        flash('Successfully logged in with GitHub!', 'success')
        
        # Always redirect to dashboard after initial login
        return redirect(url_for('dashboard.index'))
            
    except Exception as e:
        flash('GitHub authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/request-repo-access')
@login_required
def request_repo_access():
    """Display page explaining repo access request"""
    if not current_user.github_id:
        flash('GitHub authentication required', 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/request_repo_access.html')

@auth_bp.route('/github-repo-auth')
@login_required
def github_repo_auth():
    """Initiate GitHub OAuth for repository access"""
    if not current_user.github_id:
        flash('GitHub authentication required', 'error')
        return redirect(url_for('auth.login'))
    
    # Store intent for repo access
    session['requesting_repo_access'] = True
    
    # Create OAuth client with repo scope
    github = oauth.create_client('github')
    redirect_uri = url_for('auth.github_repo_callback', _external=True)
    
    # Request repo access with explicit scope
    return github.authorize_redirect(redirect_uri, scope='repo')

@auth_bp.route('/github-repo-callback')
@login_required
def github_repo_callback():
    """Handle GitHub OAuth callback for repository access"""
    try:
        github = oauth.create_client('github')
        token = github.authorize_access_token()
        
        # Update user's GitHub token with repo access
        current_user.github_token = token.get('access_token')
        current_user.save()
        
        # Clear session flag
        session.pop('requesting_repo_access', False)
        
        flash('Repository access granted! You can now select repositories for pitch deck generation.', 'success')
        return redirect(url_for('auth.select_repo'))
        
    except Exception as e:
        flash('Failed to grant repository access. Please try again.', 'error')
        return redirect(url_for('auth.request_repo_access'))

@auth_bp.route('/select-repo')
@login_required
def select_repo():
    """Display GitHub repository selection page"""
    if not current_user.github_token:
        flash('Repository access required', 'error')
        return redirect(url_for('auth.request_repo_access'))
    
    # Test if the token has repo access by trying to fetch repositories
    headers = {
        'Authorization': f'token {current_user.github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        # Get user's repositories (both owned and collaborated)
        response = requests.get('https://api.github.com/user/repos', 
                              headers=headers, 
                              params={'sort': 'updated', 'per_page': 100})
        
        if response.status_code == 200:
            repositories = response.json()
            # Filter out forks unless they have significant activity
            filtered_repos = [repo for repo in repositories 
                            if not repo['fork'] or repo['stargazers_count'] > 0]
            return render_template('auth/select_repo.html', repositories=filtered_repos)
        elif response.status_code == 403:
            # Token exists but doesn't have repo permissions
            flash('Repository access required to view your repositories', 'error')
            return redirect(url_for('auth.request_repo_access'))
        else:
            flash('Failed to fetch repositories from GitHub', 'error')
            return redirect(url_for('auth.request_repo_access'))
            
    except Exception as e:
        flash('Error connecting to GitHub API', 'error')
        return redirect(url_for('auth.request_repo_access'))

@auth_bp.route('/select-repo', methods=['POST'])
@login_required
def select_repo_post():
    """Handle repository selection and create project"""
    repo_url = request.form.get('repo_url')
    repo_name = request.form.get('repo_name')
    repo_owner = request.form.get('repo_owner')
    
    if not all([repo_url, repo_name, repo_owner]):
        flash('Invalid repository selection', 'error')
        return redirect(url_for('auth.select_repo'))
    
    # Store repository info in session for project creation
    session['selected_repo'] = {
        'url': repo_url,
        'name': repo_name,
        'owner': repo_owner
    }
    
    # Redirect to project creation with pre-filled data
    return redirect(url_for('dashboard.generator', from_github='true'))

@auth_bp.route('/connect-github')
@login_required
def connect_github():
    """Connect GitHub account to existing user"""
    # Store the intent to connect GitHub (not create new account)
    session['github_connect_existing'] = True
    return redirect(url_for('auth.github_login'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('main.index'))
