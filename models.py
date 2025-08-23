from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import json

# Create db instance that will be initialized in app.py
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship with projects
    projects = db.relationship('Project', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def project_count(self):
        return len(self.projects)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    repo_url = db.Column(db.String(500), nullable=False)
    repo_owner = db.Column(db.String(100), nullable=False)
    repo_name = db.Column(db.String(100), nullable=False)
    
    # Store the full proposal data as JSON
    proposal_data_json = db.Column(db.Text)
    
    # Legacy fields for backward compatibility
    introduction = db.Column(db.Text)
    problem_statement = db.Column(db.Text)
    solution = db.Column(db.Text)
    target_audience = db.Column(db.Text)
    technology_stack = db.Column(db.Text)
    future_scope = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Project {self.title}>'
    
    @property
    def proposal_data(self):
        """Get proposal data as a dictionary"""
        if self.proposal_data_json:
            try:
                return json.loads(self.proposal_data_json)
            except json.JSONDecodeError:
                return None
        return None
    
    @proposal_data.setter
    def proposal_data(self, value):
        """Set proposal data from a dictionary"""
        if value is not None:
            self.proposal_data_json = json.dumps(value)
        else:
            self.proposal_data_json = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'repo_url': self.repo_url,
            'repo_owner': self.repo_owner,
            'repo_name': self.repo_name,
            'proposal_data': self.proposal_data,
            'introduction': self.introduction,
            'problem_statement': self.problem_statement,
            'solution': self.solution,
            'target_audience': self.target_audience,
            'technology_stack': self.technology_stack,
            'future_scope': self.future_scope,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
