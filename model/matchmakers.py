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
        from sqlalchemy.orm.attributes import flag_modified
        
        self.data = data
        self.updated_at = datetime.now(timezone.utc)
        
        # Mark the JSON column as modified so SQLAlchemy knows to update it
        flag_modified(self, 'data')
        
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

        # Build staged matchmakers data linked to persona-created users
        from model.persona import UserPersona

        target_count = 25

        # Find users who already have personas assigned
        persona_user_ids = {up.user_id for up in UserPersona.query.all()}
        persona_users = []
        if persona_user_ids:
            persona_users = User.query.filter(User.id.in_(persona_user_ids)).all()

        users = list(persona_users)

        # If fewer than target, fill with other existing users
        if len(users) < target_count:
            remaining = target_count - len(users)
            if persona_user_ids:
                extra_users = User.query.filter(~User.id.in_(persona_user_ids)).limit(remaining).all()
            else:
                extra_users = User.query.limit(remaining).all()
            for u in extra_users:
                if u not in users:
                    users.append(u)

        users = users[:target_count]

        colors = ["Blue", "Green", "Red", "Purple", "Yellow", "Orange", "Teal", "Pink", "Indigo", "Gray"]
        animals = ["Birds", "Cats", "Dogs", "Dolphins", "Foxes", "Wolves", "Owls", "Turtles", "Horses", "Otters"]
        genres = ["Pop", "Rock", "Hip Hop", "Jazz", "Classical", "EDM", "Indie", "R&B", "Country", "Lo-fi"]
        artists = ["Michael Jackson", "Taylor Swift", "Adele", "Drake", "Coldplay", "BTS", "Billie Eilish", "Bruno Mars", "The Weeknd", "Daft Punk"]
        subjects = ["English", "Math", "Science", "History", "Computer Science", "Art", "Music", "PE", "Economics", "Biology"]

        professions = ["entrepreneur", "student", "designer", "developer", "researcher", "writer", "artist", "mentor", "builder", "analyst"]
        about_hobbies_1 = ["building things", "reading", "coding", "sketching", "music", "sports", "robotics", "gaming", "cooking", "traveling"]
        about_hobbies_2 = ["trying new experiences", "learning languages", "making videos", "designing apps", "volunteering", "photography", "debate", "hiking", "drawing", "tinkering"]
        activities = ["exploring new ideas", "working on projects", "collaborating", "brainstorming", "helping others", "testing prototypes", "researching", "planning", "iterating", "presenting"]
        values = ["making an impact", "creativity", "growth", "teamwork", "curiosity", "excellence", "community", "balance", "innovation", "integrity"]

        interest_h1 = ["drawing", "cycling", "playing board games", "baking", "filmmaking", "coding", "reading", "sports", "music", "3D printing"]
        interest_h2 = ["photography", "skateboarding", "puzzles", "writing", "gardening", "design", "volunteering", "gaming", "yoga", "robotics"]
        interest_h3 = ["chess", "running", "painting", "blogging", "travel", "swimming", "crafts", "podcasts", "DIY", "science fairs"]
        topics = ["philosophy", "technology", "psychology", "history", "entrepreneurship", "science", "music", "design", "sports", "nature"]

        skill1 = ["project management", "leadership", "time management", "public speaking", "problem solving", "team coordination", "analysis", "writing", "debugging", "design"]
        skill2 = ["communication", "creativity", "organization", "research", "collaboration", "testing", "mentoring", "data literacy", "UI/UX", "strategy"]
        skill3 = ["adaptability", "empathy", "focus", "planning", "prototyping", "iteration", "documentation", "presentation", "modeling", "optimization"]
        experience = ["1-2 years", "2-3 years", "3-4 years", "4-5 years", "5+ years"]
        aspects = ["learning new techniques", "leading teams", "building prototypes", "sharing ideas", "experimenting", "mentoring others", "iterating quickly", "solving puzzles", "shipping features", "reflecting on outcomes"]

        goal_interests = ["web development", "app development", "robotics", "data science", "game design", "AI", "cybersecurity", "product design", "music production", "entrepreneurship"]
        goals = ["collaborate on open-source projects", "build a portfolio", "launch a side project", "teach others", "win a hackathon", "publish research", "start a club", "create a startup", "improve skills", "ship an app"]
        goal_activities = ["work on coding projects together", "pair program regularly", "share ideas", "review designs", "prototype quickly", "study together", "test products", "practice presentations", "brainstorm features", "co-write docs"]

        for idx, user in enumerate(users):
            existing = MatchmakersData.query.filter_by(user_id=user.id, section='profile').first()
            if existing:
                continue

            # MBTI personality types for personality_quiz
            mbti_types = ["E_high", "E_moderate", "I_high", "I_moderate"]
            mbti_feeling = ["F_high", "F_moderate", "T_high", "T_moderate"]
            mbti_perception = ["J_high", "J_moderate", "P_high", "P_moderate"]
            mbti_sensing = ["S_high", "S_moderate", "N_high", "N_moderate"]
            
            personality_traits = ["Extroverted", "Introverted"]
            decision_traits = ["Empathetic", "Logical"]
            lifestyle_traits = ["Structured", "Spontaneous"]

            profile_data = {
                "profile_quiz": {
                    "personality_quiz": {
                        "1": mbti_types[idx % len(mbti_types)],
                        "2": mbti_feeling[idx % len(mbti_feeling)],
                        "3": mbti_perception[idx % len(mbti_perception)],
                        "4": mbti_sensing[idx % len(mbti_sensing)],
                        "5": mbti_sensing[(idx + 1) % len(mbti_sensing)],
                        "6": mbti_types[(idx + 1) % len(mbti_types)],
                        "7": mbti_feeling[(idx + 1) % len(mbti_feeling)],
                        "8": mbti_sensing[(idx + 2) % len(mbti_sensing)],
                        "9": mbti_sensing[(idx + 3) % len(mbti_sensing)],
                        "10": mbti_sensing[(idx + 4) % len(mbti_sensing)],
                        "11": mbti_feeling[(idx + 2) % len(mbti_feeling)],
                        "12": mbti_feeling[(idx + 3) % len(mbti_feeling)],
                        "13": mbti_feeling[(idx + 4) % len(mbti_feeling)]
                    },
                    "analysis": {
                        "focus": ["communication", "problem solving", "creativity", "leadership", "analysis"][idx % 5],
                        "depth": ["shallow", "moderate", "deep"][idx % 3],
                        "personalityTraits": {
                            "social": personality_traits[idx % len(personality_traits)],
                            "decision": decision_traits[idx % len(decision_traits)],
                            "lifestyle": lifestyle_traits[idx % len(lifestyle_traits)],
                            "socialScore": 0,
                            "introversionScore": 0,
                            "thinkingScore": 0,
                            "feelingScore": 0
                        },
                        "profileInsights": [
                            {
                                "category": "Color Preference",
                                "value": colors[idx % len(colors)]
                            },
                            {
                                "category": "Animal Preference",
                                "value": animals[idx % len(animals)]
                            },
                            {
                                "category": "Music Taste",
                                "value": genres[idx % len(genres)]
                            },
                            {
                                "category": "Academic Interest",
                                "value": subjects[idx % len(subjects)]
                            }
                        ]
                    }
                },
                "bio": {
                    "about": {
                        "profession": professions[idx % len(professions)],
                        "hobby1": about_hobbies_1[idx % len(about_hobbies_1)],
                        "hobby2": about_hobbies_2[idx % len(about_hobbies_2)],
                        "activity": activities[idx % len(activities)],
                        "value": values[idx % len(values)]
                    },
                    "interests": {
                        "hobby1": interest_h1[idx % len(interest_h1)],
                        "hobby2": interest_h2[idx % len(interest_h2)],
                        "hobby3": interest_h3[idx % len(interest_h3)],
                        "topic": topics[idx % len(topics)]
                    },
                    "skills": {
                        "skill1": skill1[idx % len(skill1)],
                        "skill2": skill2[idx % len(skill2)],
                        "skill3": skill3[idx % len(skill3)],
                        "experience": experience[idx % len(experience)],
                        "aspect": aspects[idx % len(aspects)]
                    },
                    "goals": {
                        "interest": goal_interests[idx % len(goal_interests)],
                        "goal": goals[idx % len(goals)],
                        "activity": goal_activities[idx % len(goal_activities)]
                    },
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "safety_checked": True,
                    "ai_verified": True
                },
                "matched_with": []
            }

            record = MatchmakersData(user=user, section='profile', data=profile_data)
            try:
                record.create()
            except ValueError:
                continue

        print(f"  > MatchmakersData table initialized with {len(users)} profile records")
        print("  > initMatchmakersData() completed successfully!")