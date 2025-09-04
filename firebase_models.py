from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from firebase_config import get_db
from firebase_admin import firestore
import uuid

class User(UserMixin):
    def __init__(self, id=None, username=None, email=None, password_hash=None, is_admin=False, account_tier='free', tokens=0, github_id=None, github_username=None, github_token=None, created_at=None, is_deleted=False):
        self.id = id or str(uuid.uuid4())
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin
        self.account_tier = account_tier  # 'free', 'basic', 'pro'
        self.tokens = tokens  # Available tokens for pitch deck generation
        self.github_id = github_id
        self.github_username = github_username
        self.github_token = github_token
        self.created_at = created_at or datetime.utcnow()
        self.is_deleted = is_deleted
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_tier_limits(self):
        """Get token limits for account tiers"""
        limits = {
            'free': 0,
            'basic': 10,
            'pro': 50
        }
        return limits.get(self.account_tier, 0)
    
    def can_export_files(self):
        """Check if user has tokens available for file exports"""
        return self.tokens > 0
    
    def use_token(self):
        """Deduct one token for file export"""
        if self.tokens > 0:
            self.tokens -= 1
            self.save()
            return True
        return False
    
    def upgrade_account(self, new_tier):
        """Upgrade user account tier and reset tokens"""
        tier_tokens = {
            'free': 0,
            'basic': 10,
            'pro': 50
        }
        if new_tier in tier_tokens:
            self.account_tier = new_tier
            self.tokens = tier_tokens[new_tier]
            self.save()
            return True
        return False
    
    def to_dict(self):
        """Convert user to dictionary for Firestore"""
        return {
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'is_admin': self.is_admin,
            'account_tier': self.account_tier,
            'tokens': self.tokens,
            'github_id': self.github_id,
            'github_username': self.github_username,
            'github_token': self.github_token,
            'created_at': self.created_at,
            'is_deleted': self.is_deleted
        }
    
    def save(self):
        """Save user to Firestore"""
        db = get_db()
        if db:
            user_data = self.to_dict()
            db.collection('users').document(self.id).set(user_data)
            return True
        return False
    
    @staticmethod
    def get(user_id):
        """Get user by ID"""
        db = get_db()
        if db:
            doc = db.collection('users').document(user_id).get()
            if doc.exists:
                data = doc.to_dict()
                return User(
                    id=user_id,
                    username=data.get('username'),
                    email=data.get('email'),
                    password_hash=data.get('password_hash'),
                    is_admin=data.get('is_admin', False),
                    account_tier=data.get('account_tier', 'free'),
                    tokens=data.get('tokens', 0),
                    github_id=data.get('github_id'),
                    github_username=data.get('github_username'),
                    github_token=data.get('github_token'),
                    created_at=data.get('created_at'),
                    is_deleted=data.get('is_deleted', False)
                )
        return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        db = get_db()
        if db:
            users = db.collection('users').where('email', '==', email).limit(1).stream()
            for user in users:
                data = user.to_dict()
                return User(
                    id=user.id,
                    email=data.get('email'),
                    username=data.get('username'),
                    password_hash=data.get('password_hash'),
                    is_admin=data.get('is_admin', False),
                    account_tier=data.get('account_tier', 'free'),
                    tokens=data.get('tokens', 0),
                    github_id=data.get('github_id'),
                    github_username=data.get('github_username'),
                    github_token=data.get('github_token'),
                    created_at=data.get('created_at'),
                    is_deleted=data.get('is_deleted', False)
                )
        return None
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        db = get_db()
        if db:
            users = db.collection('users').where('username', '==', username).limit(1).stream()
            for user in users:
                data = user.to_dict()
                return User(
                    id=user.id,
                    email=data.get('email'),
                    username=data.get('username'),
                    password_hash=data.get('password_hash'),
                    is_admin=data.get('is_admin', False),
                    account_tier=data.get('account_tier', 'free'),
                    tokens=data.get('tokens', 0),
                    github_id=data.get('github_id'),
                    github_username=data.get('github_username'),
                    github_token=data.get('github_token'),
                    created_at=data.get('created_at'),
                    is_deleted=data.get('is_deleted', False)
                )
        return None
    
    @staticmethod
    def get_by_github_id(github_id):
        """Get user by GitHub ID"""
        db = get_db()
        if db:
            users = db.collection('users').where('github_id', '==', github_id).limit(1).stream()
            for user in users:
                data = user.to_dict()
                return User(
                    id=user.id,
                    email=data.get('email'),
                    username=data.get('username'),
                    password_hash=data.get('password_hash'),
                    is_admin=data.get('is_admin', False),
                    account_tier=data.get('account_tier', 'free'),
                    tokens=data.get('tokens', 0),
                    github_id=data.get('github_id'),
                    github_username=data.get('github_username'),
                    github_token=data.get('github_token'),
                    created_at=data.get('created_at'),
                    is_deleted=data.get('is_deleted', False)
                )
        return None
    
    @staticmethod
    def get_all_users(limit=100):
        """Get all users for admin dashboard (excluding deleted users)"""
        db = get_db()
        users = []
        if db:
            docs = db.collection('users').where('is_deleted', '==', False).limit(limit).stream()
            for doc in docs:
                data = doc.to_dict()
                users.append(User(
                    id=doc.id,
                    email=data.get('email'),
                    username=data.get('username'),
                    password_hash=data.get('password_hash'),
                    is_admin=data.get('is_admin', False),
                    account_tier=data.get('account_tier', 'free'),
                    tokens=data.get('tokens', 0),
                    created_at=data.get('created_at'),
                    is_deleted=data.get('is_deleted', False)
                ))
        return users
    
    @staticmethod
    def get_user_count():
        """Get total number of users"""
        db = get_db()
        if db:
            users = list(db.collection('users').stream())
            return len(users)
        return 0
    
    @staticmethod
    def get_deleted_users(limit=100):
        """Get all deleted users for admin dashboard"""
        db = get_db()
        users = []
        if db:
            docs = db.collection('users').where('is_deleted', '==', True).limit(limit).stream()
            for doc in docs:
                data = doc.to_dict()
                users.append(User(
                    id=doc.id,
                    email=data.get('email'),
                    username=data.get('username'),
                    password_hash=data.get('password_hash'),
                    is_admin=data.get('is_admin', False),
                    account_tier=data.get('account_tier', 'free'),
                    tokens=data.get('tokens', 0),
                    github_id=data.get('github_id'),
                    github_username=data.get('github_username'),
                    github_token=data.get('github_token'),
                    created_at=data.get('created_at'),
                    is_deleted=data.get('is_deleted', False)
                ))
        return users
    
    def delete(self):
        """Mark user as deleted instead of completely removing from Firestore"""
        self.is_deleted = True
        self.github_token = None  # Clear GitHub token
        self.email = None  # Clear email to prevent conflicts
        self.password_hash = None  # Clear password
        return self.save()

class Project:
    def __init__(self, id=None, title=None, repo_url=None, repo_owner=None, repo_name=None, 
                 pitch_deck=None, user_id=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.repo_url = repo_url
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.pitch_deck = pitch_deck or {}
        self.user_id = user_id
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    @property
    def deck_data(self):
        """Alias for pitch_deck to maintain template compatibility"""
        return self.pitch_deck or {}
    
    def save(self):
        """Save project to Firestore"""
        db = get_db()
        if db:
            project_data = {
                'title': self.title,
                'repo_url': self.repo_url,
                'repo_owner': self.repo_owner,
                'repo_name': self.repo_name,
                'pitch_deck': self.pitch_deck,
                'user_id': self.user_id,
                'created_at': self.created_at,
                'updated_at': datetime.utcnow()
            }
            db.collection('projects').document(self.id).set(project_data)
            return True
        return False
    
    @staticmethod
    def get(project_id):
        """Get project by ID"""
        db = get_db()
        if db:
            doc = db.collection('projects').document(project_id).get()
            if doc.exists:
                data = doc.to_dict()
                return Project(
                    id=project_id,
                    title=data.get('title'),
                    repo_url=data.get('repo_url'),
                    repo_owner=data.get('repo_owner'),
                    repo_name=data.get('repo_name'),
                    pitch_deck=data.get('pitch_deck', {}),
                    user_id=data.get('user_id'),
                    created_at=data.get('created_at'),
                    updated_at=data.get('updated_at')
                )
        return None
    
    @staticmethod
    def get_by_user(user_id, limit=50):
        """Get projects by user ID"""
        db = get_db()
        projects = []
        if db:
            docs = db.collection('projects').where('user_id', '==', user_id)\
                    .limit(limit).stream()
            
            for doc in docs:
                data = doc.to_dict()
                projects.append(Project(
                    id=doc.id,
                    title=data.get('title'),
                    repo_url=data.get('repo_url'),
                    repo_owner=data.get('repo_owner'),
                    repo_name=data.get('repo_name'),
                    pitch_deck=data.get('pitch_deck', {}),
                    user_id=data.get('user_id'),
                    created_at=data.get('created_at'),
                    updated_at=data.get('updated_at')
                ))
            
            projects.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
        return projects
    
    @staticmethod
    def get_all_projects(limit=100):
        """Get all projects for admin dashboard"""
        db = get_db()
        projects = []
        if db:
            docs = db.collection('projects').limit(limit).stream()
            for doc in docs:
                data = doc.to_dict()
                projects.append(Project(
                    id=doc.id,
                    title=data.get('title'),
                    repo_url=data.get('repo_url'),
                    repo_owner=data.get('repo_owner'),
                    repo_name=data.get('repo_name'),
                    pitch_deck=data.get('pitch_deck', {}),
                    user_id=data.get('user_id'),
                    created_at=data.get('created_at'),
                    updated_at=data.get('updated_at')
                ))
            
            projects.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
        return projects
    
    @staticmethod
    def get_project_count():
        """Get total number of projects"""
        db = get_db()
        if db:
            projects = list(db.collection('projects').stream())
            return len(projects)
        return 0
    
    @staticmethod
    def get_generation_count():
        """Get total number of AI generations (projects with pitch decks)"""
        db = get_db()
        if db:
            projects = list(db.collection('projects').stream())
            count = 0
            for project in projects:
                data = project.to_dict()
                if data.get('pitch_deck') and len(data.get('pitch_deck', {})) > 0:
                    count += 1
            return count
        return 0
    
    @staticmethod
    def search_by_user(user_id, query, limit=20):
        """Search projects by user and query"""
        db = get_db()
        projects = []
        if db:
            # Simple text search in title and repo_name
            docs = db.collection('projects').where('user_id', '==', user_id).stream()
            
            for doc in docs:
                data = doc.to_dict()
                title = data.get('title', '').lower()
                repo_name = data.get('repo_name', '').lower()
                
                if query.lower() in title or query.lower() in repo_name:
                    projects.append(Project(
                        id=doc.id,
                        title=data.get('title'),
                        repo_url=data.get('repo_url'),
                        repo_owner=data.get('repo_owner'),
                        repo_name=data.get('repo_name'),
                        pitch_deck=data.get('pitch_deck', {}),
                        user_id=data.get('user_id'),
                        created_at=data.get('created_at'),
                        updated_at=data.get('updated_at')
                    ))
                    
                    if len(projects) >= limit:
                        break
        
        return projects
    
    def delete(self):
        """Delete project from Firestore"""
        db = get_db()
        if db:
            db.collection('projects').document(self.id).delete()
            return True
        return False
