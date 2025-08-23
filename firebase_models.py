from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from firebase_config import get_db
from firebase_admin import firestore
import uuid

class User(UserMixin):
    def __init__(self, id=None, email=None, username=None, password_hash=None, is_admin=False, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin
        self.created_at = created_at or datetime.utcnow()
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def save(self):
        """Save user to Firestore"""
        db = get_db()
        if db:
            user_data = {
                'email': self.email,
                'username': self.username,
                'password_hash': self.password_hash,
                'is_admin': self.is_admin,
                'created_at': self.created_at
            }
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
                    email=data.get('email'),
                    username=data.get('username'),
                    password_hash=data.get('password_hash'),
                    is_admin=data.get('is_admin', False),
                    created_at=data.get('created_at')
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
                    created_at=data.get('created_at')
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
                    created_at=data.get('created_at')
                )
        return None

class Project:
    def __init__(self, id=None, title=None, repo_url=None, repo_owner=None, repo_name=None, 
                 project_proposal=None, user_id=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.repo_url = repo_url
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.project_proposal = project_proposal or {}
        self.user_id = user_id
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def save(self):
        """Save project to Firestore"""
        db = get_db()
        if db:
            project_data = {
                'title': self.title,
                'repo_url': self.repo_url,
                'repo_owner': self.repo_owner,
                'repo_name': self.repo_name,
                'project_proposal': self.project_proposal,
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
                    project_proposal=data.get('project_proposal', {}),
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
            # Simple query without ordering to avoid index requirement
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
                    project_proposal=data.get('project_proposal', {}),
                    user_id=data.get('user_id'),
                    created_at=data.get('created_at'),
                    updated_at=data.get('updated_at')
                ))
            
            # Sort in Python instead of Firestore to avoid index requirement
            projects.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
        return projects
    
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
                        project_proposal=data.get('project_proposal', {}),
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
