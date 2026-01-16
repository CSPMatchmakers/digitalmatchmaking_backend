from __init__ import app, db
from sqlalchemy import JSON
from sqlalchemy.orm import validates
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

class ProfileQuiz(db.Model):
    """
    ProfileQuiz Model
    
    Stores user responses from the PII security training quiz.
    Each user can have one profile quiz record that stores their responses.
    
    Attributes:
        id (Column): Primary key
        user_id (Column): Foreign key reference to users table
        profile_data (Column): JSON array of question/response objects
        created_at (Column): When the profile was first created
        updated_at (Column): When the profile was last updated
    """
    __tablename__ = 'profile_quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    profile_data = db.Column(JSON, nullable=False)  # Stores array of {question, response, type}
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship to User model
    user = db.relationship("User", backref=db.backref("profile_quiz", uselist=False, cascade="all, delete-orphan"))
    
    def __init__(self, user_id, profile_data):
        self.user_id = user_id
        self.profile_data = profile_data
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def create(self):
        """Create a new profile quiz record."""
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            raise ValueError(f"Profile quiz already exists for user_id {self.user_id}")
    
    def update(self, profile_data):
        """Update existing profile quiz data."""
        self.profile_data = profile_data
        self.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return self
    
    def read(self):
        """Read profile quiz data as dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'uid': self.user.uid if self.user else None,
            'profile_data': self.profile_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def delete(self):
        """Delete the profile quiz record."""
        db.session.delete(self)
        db.session.commit()
    
    @staticmethod
    def get_by_user_id(user_id):
        """Get profile quiz by user_id."""
        return ProfileQuiz.query.filter_by(user_id=user_id).first()
    
    @staticmethod
    def get_all():
        """Get all profile quizzes."""
        return ProfileQuiz.query.all()
    
    @staticmethod
    def filter_safe_data(profile_data):
        """
        Filter profile data to only return non-PII responses.
        Removes sensitive information like full name, SSN, address.
        
        Args:
            profile_data: List of response objects
            
        Returns:
            List of safe (non-PII) responses
        """
        if not profile_data or not isinstance(profile_data, list):
            return []
        
        # Keywords that indicate PII questions
        pii_keywords = ['full name', 'ssn', 'where do you live', 'address', 'ip']
        
        safe_responses = []
        for resp in profile_data:
            question_lower = (resp.get('question', '')).lower()
            
            # Check if question contains PII keywords
            is_pii = any(keyword in question_lower for keyword in pii_keywords)
            
            if not is_pii:
                safe_responses.append(resp)
        
        return safe_responses
    
    @staticmethod
    def get_safe_profile(user_id):
        """
        Get user's profile quiz with PII filtered out.
        
        Args:
            user_id: User's ID
            
        Returns:
            Dict with safe profile data or None
        """
        profile_quiz = ProfileQuiz.get_by_user_id(user_id)
        if not profile_quiz:
            return None
        
        data = profile_quiz.read()
        data['profile_data'] = ProfileQuiz.filter_safe_data(data['profile_data'])
        return data


def initProfileQuizzes():
    """Initialize the profile_quizzes table."""
    with app.app_context():
        db.create_all()
        print("ProfileQuiz table created successfully!")