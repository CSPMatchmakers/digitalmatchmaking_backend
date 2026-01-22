"""
Control Panel API - Provides endpoints for monitoring, metrics, logs, and database operations
"""
from flask import Blueprint, jsonify, request, send_file, current_app
from flask_login import login_required, current_user
from functools import wraps
import json
from datetime import datetime, timedelta
import os
import io
from sqlalchemy import desc

from __init__ import db
from model.database_audit import (
    DatabaseMetrics, ErrorLog, FetchLog, ChangeLog, DatabaseStatus,
    get_database_metrics
)

control_panel_api = Blueprint('control_panel_api', __name__, url_prefix='/api/control-panel')


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


# ==================== METRICS ENDPOINTS ====================

@control_panel_api.route('/metrics', methods=['GET'])
@login_required
def get_metrics():
    """Get current database metrics"""
    try:
        metrics = get_database_metrics()
        
        # Get error count in last 24 hours
        error_count = ErrorLog.query.filter(
            ErrorLog.timestamp >= datetime.utcnow() - timedelta(days=1)
        ).count()
        
        # Get fetch count in last 24 hours
        fetch_count = FetchLog.query.filter(
            FetchLog.timestamp >= datetime.utcnow() - timedelta(days=1)
        ).count()
        
        metrics['errors_last_24h'] = error_count
        metrics['fetches_last_24h'] = fetch_count
        
        return jsonify({'success': True, 'data': metrics}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@control_panel_api.route('/metrics/history', methods=['GET'])
@login_required
def get_metrics_history():
    """Get historical metrics data"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        metrics = DatabaseMetrics.query.filter(
            DatabaseMetrics.timestamp >= datetime.utcnow() - timedelta(hours=hours)
        ).order_by(desc(DatabaseMetrics.timestamp)).limit(100).all()
        
        return jsonify({
            'success': True,
            'data': [m.to_dict() for m in metrics]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== ERROR LOG ENDPOINTS ====================

@control_panel_api.route('/error-logs', methods=['GET'])
@login_required
def get_error_logs():
    """Get recent error logs"""
    try:
        limit = request.args.get('limit', 50, type=int)
        hours = request.args.get('hours', 24, type=int)
        
        logs = ErrorLog.query.filter(
            ErrorLog.timestamp >= datetime.utcnow() - timedelta(hours=hours)
        ).order_by(desc(ErrorLog.timestamp)).limit(limit).all()
        
        return jsonify({
            'success': True,
            'count': len(logs),
            'data': [log.to_dict() for log in logs]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@control_panel_api.route('/error-logs', methods=['POST'])
@login_required
def log_error():
    """Log an error (can be called from frontend or backend)"""
    try:
        data = request.get_json()
        
        error_log = ErrorLog(
            error_type=data.get('error_type', 'Unknown'),
            endpoint=data.get('endpoint', ''),
            error_message=data.get('error_message', ''),
            status_code=data.get('status_code', 0),
            request_data=json.dumps(data.get('request_data', {})),
            user_id=current_user.id if current_user.is_authenticated else None
        )
        
        db.session.add(error_log)
        db.session.commit()
        
        return jsonify({'success': True, 'id': error_log.id}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== FETCH LOG ENDPOINTS ====================

@control_panel_api.route('/fetch-logs', methods=['GET'])
@login_required
def get_fetch_logs():
    """Get recent fetch logs"""
    try:
        limit = request.args.get('limit', 50, type=int)
        hours = request.args.get('hours', 24, type=int)
        error_only = request.args.get('error_only', False, type=bool)
        
        query = FetchLog.query.filter(
            FetchLog.timestamp >= datetime.utcnow() - timedelta(hours=hours)
        )
        
        if error_only:
            query = query.filter_by(is_error=True)
        
        logs = query.order_by(desc(FetchLog.timestamp)).limit(limit).all()
        
        return jsonify({
            'success': True,
            'count': len(logs),
            'data': [log.to_dict() for log in logs]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@control_panel_api.route('/fetch-logs', methods=['POST'])
@login_required
def log_fetch():
    """Log a fetch operation (can be called from frontend)"""
    try:
        data = request.get_json()
        
        fetch_log = FetchLog(
            endpoint=data.get('endpoint', ''),
            method=data.get('method', 'GET'),
            status_code=data.get('status_code', 0),
            response_time_ms=data.get('response_time_ms', 0),
            source_ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            user_id=current_user.id if current_user.is_authenticated else None,
            is_error=data.get('status_code', 200) >= 400
        )
        
        db.session.add(fetch_log)
        db.session.commit()
        
        return jsonify({'success': True, 'id': fetch_log.id}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== CHANGE LOG ENDPOINTS ====================

@control_panel_api.route('/change-logs', methods=['GET'])
@login_required
def get_change_logs():
    """Get recent changes"""
    try:
        limit = request.args.get('limit', 50, type=int)
        hours = request.args.get('hours', 24, type=int)
        entity_type = request.args.get('entity_type', None)
        
        query = ChangeLog.query.filter(
            ChangeLog.timestamp >= datetime.utcnow() - timedelta(hours=hours)
        )
        
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        
        logs = query.order_by(desc(ChangeLog.timestamp)).limit(limit).all()
        
        return jsonify({
            'success': True,
            'count': len(logs),
            'data': [log.to_dict() for log in logs]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@control_panel_api.route('/change-logs', methods=['POST'])
@login_required
def log_change():
    """Log a change (usually called from model operations)"""
    try:
        data = request.get_json()
        
        change_log = ChangeLog(
            entity_type=data.get('entity_type', ''),
            entity_id=data.get('entity_id', 0),
            action=data.get('action', 'update'),
            old_values=json.dumps(data.get('old_values', {})),
            new_values=json.dumps(data.get('new_values', {})),
            changed_by_user_id=current_user.id if current_user.is_authenticated else None
        )
        
        db.session.add(change_log)
        db.session.commit()
        
        return jsonify({'success': True, 'id': change_log.id}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== DATABASE STATUS ENDPOINTS ====================

@control_panel_api.route('/database-status', methods=['GET'])
@login_required
def get_database_status():
    """Get current database status"""
    try:
        status = DatabaseStatus.get_or_create()
        return jsonify({'success': True, 'data': status.to_dict()}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@control_panel_api.route('/database-status/pause', methods=['POST'])
@login_required
@admin_required
def pause_database():
    """Pause incoming data to the database (including matchmakers)"""
    try:
        reason = request.get_json().get('reason', 'User initiated pause')
        status = DatabaseStatus.pause_incoming_data(reason)
        # Also pause matchmakers data
        DatabaseStatus.pause_matchmakers_data(reason)
        
        return jsonify({
            'success': True,
            'message': 'Database paused (including matchmakers)',
            'data': status.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@control_panel_api.route('/database-status/resume', methods=['POST'])
@login_required
@admin_required
def resume_database():
    """Resume incoming data to the database (including matchmakers)"""
    try:
        status = DatabaseStatus.resume_incoming_data()
        # Also resume matchmakers data
        DatabaseStatus.resume_matchmakers_data()
        
        return jsonify({
            'success': True,
            'message': 'Database resumed (including matchmakers)',
            'data': status.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@control_panel_api.route('/database-status/pause-matchmakers', methods=['POST'])
@login_required
@admin_required
def pause_matchmakers():
    """Pause incoming matchmakers data only"""
    try:
        reason = request.get_json().get('reason', 'User initiated matchmakers pause')
        status = DatabaseStatus.pause_matchmakers_data(reason)
        
        return jsonify({
            'success': True,
            'message': 'Matchmakers data paused',
            'data': status.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@control_panel_api.route('/database-status/resume-matchmakers', methods=['POST'])
@login_required
@admin_required
def resume_matchmakers():
    """Resume incoming matchmakers data only"""
    try:
        status = DatabaseStatus.resume_matchmakers_data()
        
        return jsonify({
            'success': True,
            'message': 'Matchmakers data resumed',
            'data': status.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== EXPORT/IMPORT ENDPOINTS ====================

@control_panel_api.route('/export/data', methods=['GET'])
@login_required
@admin_required
def export_data():
    """Export database data as JSON"""
    try:
        from model.user import User
        from model.post import Post
        from model.persona import Persona
        from model.matchmakers import MatchmakersData
        
        export_data = {
            'exported_at': datetime.utcnow().isoformat(),
            'database_version': '1.0',
            'stats': {
                'users': User.query.count(),
                'posts': Post.query.count() if Post else 0,
                'personas': Persona.query.count() if Persona else 0,
                'matchmakers': MatchmakersData.query.count() if MatchmakersData else 0,
            }
        }
        
        # Create a JSON file in memory
        json_data = json.dumps(export_data, indent=2, default=str)
        
        # Return as downloadable file
        return jsonify({
            'success': True,
            'message': 'Export data generated',
            'preview': export_data
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@control_panel_api.route('/import/data', methods=['POST'])
@login_required
@admin_required
def import_data():
    """Import database data from JSON"""
    try:
        data = request.get_json()
        
        # Validate import data
        if not data or 'database_version' not in data:
            return jsonify({
                'success': False,
                'error': 'Invalid import file format'
            }), 400
        
        # Here you would implement the actual import logic
        # This is a placeholder for now
        
        return jsonify({
            'success': True,
            'message': 'Data import validation passed. Import ready to proceed.',
            'data': data.get('stats', {})
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== SUMMARY/DASHBOARD ENDPOINT ====================

@control_panel_api.route('/summary', methods=['GET'])
@login_required
def get_dashboard_summary():
    """Get complete dashboard summary"""
    try:
        metrics = get_database_metrics()
        status = DatabaseStatus.get_or_create()
        
        # Get error count in last 24 hours
        error_count = ErrorLog.query.filter(
            ErrorLog.timestamp >= datetime.utcnow() - timedelta(days=1)
        ).count()
        
        # Get fetch count in last 24 hours
        fetch_count = FetchLog.query.filter(
            FetchLog.timestamp >= datetime.utcnow() - timedelta(days=1)
        ).count()
        
        # Get recent changes (last 5)
        recent_changes = ChangeLog.query.order_by(
            desc(ChangeLog.timestamp)
        ).limit(5).all()
        
        # Get recent errors (last 5)
        recent_errors = ErrorLog.query.order_by(
            desc(ErrorLog.timestamp)
        ).limit(5).all()
        
        summary = {
            'metrics': metrics,
            'status': status.to_dict(),
            'errors_last_24h': error_count,
            'fetches_last_24h': fetch_count,
            'recent_changes': [c.to_dict() for c in recent_changes],
            'recent_errors': [e.to_dict() for e in recent_errors],
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        return jsonify({'success': True, 'data': summary}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
