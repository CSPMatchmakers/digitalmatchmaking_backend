"""
Database Audit and Monitoring Models

This module provides models for tracking database activity, metrics, and logs.
"""
from __init__ import db
from datetime import datetime, timedelta
from sqlalchemy import desc
import json

class DatabaseMetrics(db.Model):
    """
    Tracks database metrics including user counts, data statistics, etc.
    """
    __tablename__ = 'database_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # User metrics
    total_users = db.Column(db.Integer, default=0)
    active_users = db.Column(db.Integer, default=0)
    
    # Data metrics
    total_records = db.Column(db.Integer, default=0)
    total_posts = db.Column(db.Integer, default=0)
    total_personas = db.Column(db.Integer, default=0)
    total_matchmakers = db.Column(db.Integer, default=0)
    
    # Storage metrics
    database_size_mb = db.Column(db.Float, default=0)
    
    # Activity metrics
    requests_today = db.Column(db.Integer, default=0)
    errors_today = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'total_users': self.total_users,
            'active_users': self.active_users,
            'total_records': self.total_records,
            'total_posts': self.total_posts,
            'total_personas': self.total_personas,
            'total_matchmakers': self.total_matchmakers,
            'database_size_mb': self.database_size_mb,
            'requests_today': self.requests_today,
            'errors_today': self.errors_today,
        }


class ErrorLog(db.Model):
    """
    Tracks errors from API calls and database operations
    """
    __tablename__ = 'error_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    error_type = db.Column(db.String(100), index=True)  # e.g., 'FetchError', 'ValidationError', 'DatabaseError'
    endpoint = db.Column(db.String(255), index=True)
    error_message = db.Column(db.Text)
    status_code = db.Column(db.Integer)
    request_data = db.Column(db.Text)  # JSON string
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'error_type': self.error_type,
            'endpoint': self.endpoint,
            'error_message': self.error_message,
            'status_code': self.status_code,
            'user_id': self.user_id,
        }


class FetchLog(db.Model):
    """
    Tracks API fetch operations and their sources
    """
    __tablename__ = 'fetch_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    endpoint = db.Column(db.String(255), index=True)  # The API endpoint that was called
    method = db.Column(db.String(10))  # GET, POST, PUT, DELETE, etc.
    status_code = db.Column(db.Integer)
    response_time_ms = db.Column(db.Float)  # Response time in milliseconds
    source_ip = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_error = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'endpoint': self.endpoint,
            'method': self.method,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'source_ip': self.source_ip,
            'user_agent': self.user_agent,
            'user_id': self.user_id,
            'is_error': self.is_error,
        }


class ChangeLog(db.Model):
    """
    Tracks recent changes to data records
    """
    __tablename__ = 'change_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    entity_type = db.Column(db.String(100), index=True)  # e.g., 'User', 'Post', 'Matchmaker', 'Persona'
    entity_id = db.Column(db.Integer, index=True)
    action = db.Column(db.String(20), index=True)  # 'create', 'update', 'delete'
    
    old_values = db.Column(db.Text)  # JSON string of old data
    new_values = db.Column(db.Text)  # JSON string of new data
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'action': self.action,
            'changed_by_user_id': self.changed_by_user_id,
        }


class DatabaseStatus(db.Model):
    """
    Tracks the current status of the database (idle, processing, paused, etc.)
    """
    __tablename__ = 'database_status'
    
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50), default='idle', index=True)  # 'idle', 'processing', 'paused', 'maintenance'
    details = db.Column(db.Text)  # JSON with additional details
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_paused = db.Column(db.Boolean, default=False)  # Is incoming data paused?
    pause_reason = db.Column(db.String(255))
    
    def to_dict(self):
        details_obj = {}
        if self.details:
            try:
                details_obj = json.loads(self.details)
            except:
                details_obj = {'raw': self.details}
        
        return {
            'id': self.id,
            'status': self.status,
            'details': details_obj,
            'last_updated': self.last_updated.isoformat(),
            'is_paused': self.is_paused,
            'pause_reason': self.pause_reason,
        }
    
    @staticmethod
    def get_or_create():
        """Get the current database status or create one if it doesn't exist"""
        status = DatabaseStatus.query.first()
        if not status:
            status = DatabaseStatus()
            db.session.add(status)
            db.session.commit()
        return status
    
    @staticmethod
    def set_status(new_status, details=None):
        """Update the database status"""
        status = DatabaseStatus.get_or_create()
        status.status = new_status
        if details:
            status.details = json.dumps(details)
        status.last_updated = datetime.utcnow()
        db.session.commit()
        return status
    
    @staticmethod
    def pause_incoming_data(reason="User initiated pause"):
        """Pause incoming data"""
        status = DatabaseStatus.get_or_create()
        status.is_paused = True
        status.pause_reason = reason
        status.status = 'paused'
        status.last_updated = datetime.utcnow()
        db.session.commit()
        return status
    
    @staticmethod
    def resume_incoming_data():
        """Resume incoming data"""
        status = DatabaseStatus.get_or_create()
        status.is_paused = False
        status.pause_reason = None
        status.status = 'idle'
        status.last_updated = datetime.utcnow()
        db.session.commit()
        return status


def get_database_metrics():
    """Get current database metrics"""
    try:
        from model.user import User
        
        metrics = {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(active=True).count() if hasattr(User, 'active') else 0,
            'total_posts': 0,
            'total_personas': 0,
            'total_matchmakers': 0,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        # Try to get Post count
        try:
            from model.post import Post
            metrics['total_posts'] = Post.query.count()
        except:
            pass
        
        # Try to get Persona count
        try:
            from model.persona import Persona
            metrics['total_personas'] = Persona.query.count()
        except:
            pass
        
        # Try to get MatchmakersData count
        try:
            from model.matchmakers import MatchmakersData
            metrics['total_matchmakers'] = MatchmakersData.query.count()
        except:
            pass
        
        # Total records is sum of all
        metrics['total_records'] = (metrics['total_posts'] + 
                                   metrics['total_personas'] + 
                                   metrics['total_matchmakers'])
        
        return metrics
    except Exception as e:
        return {'error': str(e), 'timestamp': datetime.utcnow().isoformat()}

