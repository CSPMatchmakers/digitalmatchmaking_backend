from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from __init__ import app, db
from model.user import User
import json
from sqlalchemy import JSON
from sqlalchemy.orm import validates
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

# Route to display the matchmakers data management page
@app.route('/matchmakers/', methods=['GET'])
@login_required
def matchmakers_page():
    """Display the matchmakers data management page."""
    matchmakers_records = MatchmakersData.query.all()
    return render_template('matchmakers.html', 
                         matchmakers_records=matchmakers_records,
                         current_user=current_user)

# Route to get a specific matchmakers data record by ID
@app.route('/matchmakers/<int:id>', methods=['GET'])
@login_required
def get_matchmaker_record(id):
    """Get a specific matchmakers data record by ID."""
    try:
        record = MatchmakersData.query.get_or_404(id)
        
        # Get user uid
        user_uid = ''
        if record.user:
            user_uid = record.user.uid
        
        return jsonify({
            'id': record.id,
            'user_id': record.user_id,
            'user_uid': user_uid,
            'section': record.section,
            'data': json.dumps(record.data, indent=2) if isinstance(record.data, dict) else record.data,
            'created_at': record.created_at.isoformat() if record.created_at else None,
            'updated_at': record.updated_at.isoformat() if record.updated_at else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route to update a matchmakers data record
@app.route('/matchmakers/update/<int:id>', methods=['PUT'])
@login_required
def update_matchmaker_record(id):
    """Update a matchmakers data record."""
    # Check if user is admin
    if current_user.role != 'Admin':
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        record = MatchmakersData.query.get_or_404(id)
        
        # Get data from request
        request_data = request.get_json()
        if not request_data or 'data' not in request_data:
            return jsonify({'message': 'No data provided'}), 400
        
        # Update the record
        new_data = request_data['data']
        record.update(new_data)
        
        return jsonify({
            'message': 'Record updated successfully',
            'id': record.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating record: {str(e)}'}), 500

# Route to delete a matchmakers data record
@app.route('/matchmakers/delete/<int:id>', methods=['DELETE'])
@login_required
def delete_matchmaker_record(id):
    """Delete a matchmakers data record."""
    # Check if user is admin
    if current_user.role != 'Admin':
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        record = MatchmakersData.query.get_or_404(id)
        
        # Delete the record
        db.session.delete(record)
        db.session.commit()
        
        return jsonify({
            'message': 'Record deleted successfully',
            'id': id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting record: {str(e)}'}), 500

# Optional: Route to create a new matchmakers data record
@app.route('/matchmakers/create', methods=['POST'])
@login_required
def create_matchmaker_record():
    """Create a new matchmakers data record."""
    # Check if user is admin
    if current_user.role != 'Admin':
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        request_data = request.get_json()
        
        # Validate required fields
        if not all(k in request_data for k in ['user_id', 'section', 'data']):
            return jsonify({'message': 'Missing required fields'}), 400
        
        # Get user
        user = User.query.get(request_data['user_id'])
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Create new record
        new_record = MatchmakersData(
            user=user,
            section=request_data['section'],
            data=request_data['data']
        )
        new_record.create()
        
        return jsonify({
            'message': 'Record created successfully',
            'id': new_record.id
        }), 201
        
    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating record: {str(e)}'}), 500


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
    data = db.Column(db.JSON, nullable=False)  # Stores PII data as JSON object
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