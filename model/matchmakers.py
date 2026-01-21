from __init__ import app, db
from sqlalchemy import JSON
from sqlalchemy.orm import validates
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

# PII sections - different categories of personally identifiable information
PII_SECTIONS = [
    'basic',        # Basic information like name, age, etc.
    'contact',      # Contact information like email, phone
    'preferences',  # User preferences for matchmaking
    'security',     # Security-related PII for verification
    'profile'       # Profile setup and general profile data
]

class MatchmakersData(db.Model):
    """
    MatchmakersData Model
    
    Stores personally identifiable information for users in the matchmaking system.
    Each user can have multiple sections of PII data stored as JSON.
    
    Attributes:
        id (Column): Primary key
        user_id (Column): Foreign key reference to users table
        section (Column): The category/section of PII data (e.g., 'basic', 'contact')
        data (Column): JSON object containing the PII data for this section
        created_at (Column): When the PII data was first created
        updated_at (Column): When the PII data was last updated
    """
    __tablename__ = 'matchmakers_data'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    section = db.Column(db.String(32), nullable=False)
    data = db.Column(JSON, nullable=False)  # Stores PII data as JSON object
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship to User model
    user = db.relationship("User", backref=db.backref("matchmakers_data_records", cascade="all, delete-orphan"))
    
    def __init__(self, user, section, data):
        self.user = user
        self.section = section
        self.data = data
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    @validates('section')
    def validate_section(self, key, value):
        """Validate that the section is one of the allowed PII sections."""
        if value not in PII_SECTIONS:
            raise ValueError(f"Invalid PII section '{value}'. Must be one of: {', '.join(PII_SECTIONS)}")
        return value
    
    def create(self):
        """Create a new matchmakers data record."""
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            raise ValueError(f"Matchmakers data record for user {self.user_id} and section '{self.section}' already exists")
    
    def update(self, data):
        """Update existing PII data."""
        self.data = data
        self.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return self
    
    def read(self):
        """Read matchmakers data."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'uid': self.user.uid if self.user else None,
            'section': self.section,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_user_matchmakers_data(user_id, section=None):
        """Get matchmakers data for a user, optionally filtered by section."""
        query = MatchmakersData.query.filter_by(user_id=user_id)
        if section:
            query = query.filter_by(section=section)
        return query.all()
    
    @staticmethod
    def get_all_matchmakers_data():
        """Get all matchmakers data records."""
        return MatchmakersData.query.all()


# Database initialization function
def initMatchmakersData():
    """Initialize sample matchmakers data for testing."""
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Sample matchmakers data can be added here if needed
        print("MatchmakersData table initialized")