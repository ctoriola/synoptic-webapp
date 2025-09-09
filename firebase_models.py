from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from firebase_config import get_db
from firebase_admin import firestore
import uuid

class User(UserMixin):
    def __init__(self, id=None, email=None, username=None, password_hash=None, 
                 is_admin=False, account_tier='free', tokens=0, github_id=None, 
                 github_username=None, github_token=None, created_at=None, is_deleted=False, is_whitelisted=False,
                 stripe_customer_id=None, stripe_subscription_id=None, survey_completed=False, 
                 survey_export_used=False, coupon_code=None):
        self.id = id or str(uuid.uuid4())
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin
        self.account_tier = account_tier
        self.tokens = tokens
        self.github_id = github_id
        self.github_username = github_username
        self.github_token = github_token
        self.created_at = created_at or datetime.utcnow()
        self.is_deleted = is_deleted
        self.is_whitelisted = is_whitelisted
        self.stripe_customer_id = stripe_customer_id
        self.stripe_subscription_id = stripe_subscription_id
        self.survey_completed = survey_completed
        self.survey_export_used = survey_export_used
        self.coupon_code = coupon_code
    
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
            'waitlisted': 0,
            'basic': 10,
            'pro': 50
        }
        return limits.get(self.account_tier, 0)
    
    def can_export_files(self):
        """Check if user has tokens available for file exports"""
        if self.account_tier == 'waitlisted':
            return self.survey_completed and not self.survey_export_used
        return self.tokens > 0
    
    def use_token(self):
        """Deduct one token for file export or mark survey export as used"""
        if self.account_tier == 'waitlisted':
            if self.survey_completed and not self.survey_export_used:
                self.survey_export_used = True
                self.save()
                return True
            return False
        elif self.tokens > 0:
            self.tokens -= 1
            self.save()
            return True
        return False
    
    def upgrade_account(self, new_tier):
        """Upgrade user account tier and reset tokens"""
        tier_tokens = {
            'free': 0,
            'waitlisted': 0,
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
            'email': self.email,
            'username': self.username,
            'password_hash': self.password_hash,
            'is_admin': self.is_admin,
            'account_tier': self.account_tier,
            'tokens': self.tokens,
            'github_id': self.github_id,
            'github_username': self.github_username,
            'github_token': self.github_token,
            'created_at': self.created_at,
            'is_deleted': self.is_deleted,
            'is_whitelisted': self.is_whitelisted,
            'stripe_customer_id': self.stripe_customer_id,
            'stripe_subscription_id': self.stripe_subscription_id,
            'survey_completed': self.survey_completed,
            'survey_export_used': self.survey_export_used,
            'coupon_code': self.coupon_code
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
                    is_deleted=data.get('is_deleted', False),
                    survey_completed=data.get('survey_completed', False),
                    survey_export_used=data.get('survey_export_used', False),
                    coupon_code=data.get('coupon_code'),
                    is_whitelisted=data.get('is_whitelisted', False),
                    stripe_customer_id=data.get('stripe_customer_id'),
                    stripe_subscription_id=data.get('stripe_subscription_id')
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
                    is_deleted=data.get('is_deleted', False),
                    survey_completed=data.get('survey_completed', False),
                    survey_export_used=data.get('survey_export_used', False),
                    coupon_code=data.get('coupon_code')
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
                    is_deleted=data.get('is_deleted', False),
                    survey_completed=data.get('survey_completed', False),
                    survey_export_used=data.get('survey_export_used', False),
                    coupon_code=data.get('coupon_code')
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
                    is_deleted=data.get('is_deleted', False),
                    survey_completed=data.get('survey_completed', False),
                    survey_export_used=data.get('survey_export_used', False),
                    coupon_code=data.get('coupon_code')
                )
        return None
    
    @staticmethod
    def get_by_stripe_customer_id(stripe_customer_id):
        """Get user by Stripe customer ID"""
        db = get_db()
        if db:
            users = db.collection('users').where('stripe_customer_id', '==', stripe_customer_id).limit(1).stream()
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
                    is_deleted=data.get('is_deleted', False),
                    survey_completed=data.get('survey_completed', False),
                    survey_export_used=data.get('survey_export_used', False),
                    coupon_code=data.get('coupon_code'),
                    is_whitelisted=data.get('is_whitelisted', False),
                    stripe_customer_id=data.get('stripe_customer_id'),
                    stripe_subscription_id=data.get('stripe_subscription_id')
                )
        return None
    
    @staticmethod
    def get_all_users(limit=100):
        """Get all users for admin dashboard (excluding deleted users)"""
        db = get_db()
        users = []
        if db:
            # Get all users and filter out deleted ones in Python since some users may not have is_deleted field
            docs = db.collection('users').limit(limit).stream()
            for doc in docs:
                data = doc.to_dict()
                # Skip users that are explicitly marked as deleted
                if data.get('is_deleted', False):
                    continue
                    
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
                    is_deleted=data.get('is_deleted', False),
                    survey_completed=data.get('survey_completed', False),
                    survey_export_used=data.get('survey_export_used', False),
                    coupon_code=data.get('coupon_code'),
                    is_whitelisted=data.get('is_whitelisted', False)
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
                    is_deleted=data.get('is_deleted', False),
                    survey_completed=data.get('survey_completed', False),
                    survey_export_used=data.get('survey_export_used', False),
                    coupon_code=data.get('coupon_code'),
                    is_whitelisted=data.get('is_whitelisted', False)
                ))
        return users
    
    def delete(self):
        """Mark user as deleted instead of completely removing from Firestore"""
        self.is_deleted = True
        self.github_token = None  # Clear GitHub token
        self.email = None  # Clear email to prevent conflicts
        self.password_hash = None  # Clear password
        return False

class Survey:
    def __init__(self, id=None, title=None, questions=None, is_active=True, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.questions = questions or []
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self):
        """Convert survey to dictionary for Firestore"""
        return {
            'title': self.title,
            'questions': self.questions,
            'is_active': self.is_active,
            'created_at': self.created_at
        }
    
    def save(self):
        """Save survey to Firestore"""
        db = get_db()
        if db:
            survey_data = self.to_dict()
            db.collection('surveys').document(self.id).set(survey_data)
            return True
        return False
    
    @staticmethod
    def get(survey_id):
        """Get survey by ID"""
        db = get_db()
        if db:
            doc = db.collection('surveys').document(survey_id).get()
            if doc.exists:
                data = doc.to_dict()
                return Survey(
                    id=survey_id,
                    title=data.get('title'),
                    questions=data.get('questions', []),
                    is_active=data.get('is_active', True),
                    created_at=data.get('created_at')
                )
        return None
    
    @staticmethod
    def get_active():
        """Get active survey"""
        db = get_db()
        if db:
            surveys = db.collection('surveys').where('is_active', '==', True).limit(1).stream()
            for survey in surveys:
                data = survey.to_dict()
                return Survey(
                    id=survey.id,
                    title=data.get('title'),
                    questions=data.get('questions', []),
                    is_active=data.get('is_active', True),
                    created_at=data.get('created_at')
                )
        return None
    
    @staticmethod
    def get_all():
        """Get all surveys"""
        db = get_db()
        surveys = []
        if db:
            docs = db.collection('surveys').stream()
            for doc in docs:
                data = doc.to_dict()
                surveys.append(Survey(
                    id=doc.id,
                    title=data.get('title'),
                    questions=data.get('questions', []),
                    is_active=data.get('is_active', True),
                    created_at=data.get('created_at')
                ))
        return surveys


class SurveyResponse:
    def __init__(self, id=None, survey_id=None, user_id=None, responses=None, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.survey_id = survey_id
        self.user_id = user_id
        self.responses = responses or {}
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self):
        """Convert survey response to dictionary for Firestore"""
        return {
            'survey_id': self.survey_id,
            'user_id': self.user_id,
            'responses': self.responses,
            'created_at': self.created_at
        }
    
    def save(self):
        """Save survey response to Firestore"""
        db = get_db()
        if db:
            response_data = self.to_dict()
            db.collection('survey_responses').document(self.id).set(response_data)
            return True
        return False
    
    @staticmethod
    def get_by_user_and_survey(user_id, survey_id):
        """Get survey response by user and survey"""
        db = get_db()
        if db:
            responses = db.collection('survey_responses')\
                         .where('user_id', '==', user_id)\
                         .where('survey_id', '==', survey_id)\
                         .limit(1).stream()
            for response in responses:
                data = response.to_dict()
                return SurveyResponse(
                    id=response.id,
                    survey_id=data.get('survey_id'),
                    user_id=data.get('user_id'),
                    responses=data.get('responses', {}),
                    created_at=data.get('created_at')
                )
        return None
    
    @staticmethod
    def get_all_by_survey(survey_id):
        """Get all responses for a survey"""
        db = get_db()
        responses = []
        if db:
            docs = db.collection('survey_responses').where('survey_id', '==', survey_id).stream()
            for doc in docs:
                data = doc.to_dict()
                responses.append(SurveyResponse(
                    id=doc.id,
                    survey_id=data.get('survey_id'),
                    user_id=data.get('user_id'),
                    responses=data.get('responses', {}),
                    created_at=data.get('created_at')
                ))
        return responses


class Coupon:
    def __init__(self, id=None, code=None, discount_type='percentage', discount_value=0, 
                 applies_to='all', max_uses=None, current_uses=0, expires_at=None, 
                 is_active=True, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.code = code
        self.discount_type = discount_type  # 'percentage' or 'fixed'
        self.discount_value = discount_value
        self.applies_to = applies_to  # 'all', 'basic', 'pro'
        self.max_uses = max_uses
        self.current_uses = current_uses
        self.expires_at = expires_at
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self):
        """Convert coupon to dictionary for Firestore"""
        return {
            'code': self.code,
            'discount_type': self.discount_type,
            'discount_value': self.discount_value,
            'applies_to': self.applies_to,
            'max_uses': self.max_uses,
            'current_uses': self.current_uses,
            'expires_at': self.expires_at,
            'is_active': self.is_active,
            'created_at': self.created_at
        }
    
    def save(self):
        """Save coupon to Firestore"""
        db = get_db()
        if db:
            coupon_data = self.to_dict()
            db.collection('coupons').document(self.id).set(coupon_data)
            return True
        return False
    
    def is_valid(self):
        """Check if coupon is valid for use"""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True
    
    def use_coupon(self):
        """Increment usage count"""
        if self.is_valid():
            self.current_uses += 1
            self.save()
            return True
        return False
    
    @staticmethod
    def get_by_code(code):
        """Get coupon by code"""
        db = get_db()
        if db:
            coupons = db.collection('coupons').where('code', '==', code).limit(1).stream()
            for coupon in coupons:
                data = coupon.to_dict()
                return Coupon(
                    id=coupon.id,
                    code=data.get('code'),
                    discount_type=data.get('discount_type', 'percentage'),
                    discount_value=data.get('discount_value', 0),
                    applies_to=data.get('applies_to', 'all'),
                    max_uses=data.get('max_uses'),
                    current_uses=data.get('current_uses', 0),
                    expires_at=data.get('expires_at'),
                    is_active=data.get('is_active', True),
                    created_at=data.get('created_at')
                )
        return None
    
    @staticmethod
    def get_all():
        """Get all coupons"""
        db = get_db()
        coupons = []
        if db:
            docs = db.collection('coupons').stream()
            for doc in docs:
                data = doc.to_dict()
                coupons.append(Coupon(
                    id=doc.id,
                    code=data.get('code'),
                    discount_type=data.get('discount_type', 'percentage'),
                    discount_value=data.get('discount_value', 0),
                    applies_to=data.get('applies_to', 'all'),
                    max_uses=data.get('max_uses'),
                    current_uses=data.get('current_uses', 0),
                    expires_at=data.get('expires_at'),
                    is_active=data.get('is_active', True),
                    created_at=data.get('created_at')
                ))
        return coupons


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
