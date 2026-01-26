## Create Users, Get User Data, Store Data, Change Data

from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource
from datetime import datetime
from api.jwt_authorize import token_required
from model.user import User
from model.matchmakers import MatchmakersData
from model.database_audit import DatabaseStatus
import json
from functools import wraps

# Create the blueprint
matchmaking_bio_api = Blueprint('matchmaking_bio_api', __name__, url_prefix='/api/match')

# API docs https://flask-restful.readthedocs.io/en/latest/api.html
api = Api(matchmaking_bio_api)


def matchmakers_write_allowed():
    """Decorator to check if matchmakers data writes are allowed"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            status = DatabaseStatus.get_or_create()
            if status.is_matchmakers_paused:
                return {'message': f'Matchmakers data is currently paused. Reason: {status.matchmakers_pause_reason}'}, 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


class MatchmakingAPI:

    class _DATA(Resource):
        @token_required()
        def get(self):
            current_user = g.current_user
            uid = current_user.uid
            
            try:
                # Get user's matchmakers data
                user_data_records = MatchmakersData.get_user_matchmakers_data(current_user.id)
                
                if user_data_records:
                    # Combine all sections into a single response
                    data = {}
                    for record in user_data_records:
                        data[record.section] = record.data
                    
                    return {
                        'message': f'Data for {uid}',
                        'data': data
                    }, 200
                
                # If no data found, return empty
                return {
                    'message': f'No data found for {uid}',
                    'data': {}
                }, 404
                
            except Exception as e:
                return {'message': f'Error retrieving data: {str(e)}'}, 500

    class _WRITE(Resource):
        @token_required()
        @matchmakers_write_allowed()
        def post(self):
            """Write or update matchmakers data for a specific section."""
            current_user = g.current_user
            body = request.get_json() or {}
            
            # Validate required fields
            section = body.get('section')
            data = body.get('data')
            
            if not section:
                return {'message': 'section field is required'}, 400
            if data is None:
                return {'message': 'data field is required'}, 400
            
            try:
                # Check if record exists
                existing_records = MatchmakersData.get_user_matchmakers_data(current_user.id, section=section)
                
                if existing_records:
                    # Update existing
                    record = existing_records[0]
                    record.update(data)
                    message = f'Data updated for section {section}'
                else:
                    # Create new
                    record = MatchmakersData(current_user, section, data)
                    record.create()
                    message = f'Data created for section {section}'
                
                return {
                    'message': message,
                    'section': section,
                    'data': data
                }, 201
                
            except Exception as e:
                return {'message': f'Error writing data: {str(e)}'}, 500

    class _SETUP(Resource):
        @token_required()
        @matchmakers_write_allowed()
        def post(self):
            """Initialize profile setup for the current user."""
            current_user = g.current_user

            # Check if profile setup already exists
            existing_records = MatchmakersData.get_user_matchmakers_data(current_user.id)
            if existing_records:
                return {'message': f'Profile setup for {current_user.uid} already created'}, 409

            # Create new profile setup record
            try:
                setup_record = MatchmakersData(current_user, 'profile', {})
                setup_record.create()
                
                return {
                    'message': f'Profile setup initialized for {current_user.uid}', 
                    'data': setup_record.read()
                }, 201
                    
            except Exception as e:
                return {'message': f'Error initializing profile setup: {str(e)}'}, 500

    class _ADD(Resource):
        @token_required()
        @matchmakers_write_allowed()
        def post(self):
            """Add custom indexed data to the user's profile."""
            current_user = g.current_user
            body = request.get_json() or {}
            
            print(f"=== ADD ENDPOINT HIT ===")
            print(f"User: {current_user.uid}")
            print(f"Body: {body}")
            
            # Validate required fields
            index = body.get('index')
            data_value = body.get('data')
            
            if not index:
                return {'message': 'index field is required'}, 400
            if data_value is None:
                return {'message': 'data field is required'}, 400
            
            try:
                # Get user's profile record
                profile_records = MatchmakersData.get_user_matchmakers_data(current_user.id, section='profile')
                
                if not profile_records:
                    # Create profile record if it doesn't exist
                    print(f"Creating new profile for {current_user.uid}")
                    profile_record = MatchmakersData(current_user, 'profile', {})
                    profile_record.create()
                else:
                    profile_record = profile_records[0]
                    print(f"Found existing profile for {current_user.uid}")
                
                # Update the data dict
                current_data = profile_record.data if profile_record.data else {}
                current_data[index] = data_value
                
                # Update the record
                profile_record.update(current_data)
                
                print(f"Successfully saved data for {current_user.uid}")
                
                return {
                    'message': f'Data added to profile for {current_user.uid}',
                    'index': index,
                    'data': data_value
                }, 201
                
            except Exception as e:
                print(f"ERROR in _ADD: {str(e)}")
                import traceback
                traceback.print_exc()
                return {'message': f'Error adding data: {str(e)}'}, 500

        @token_required()
        @matchmakers_write_allowed()
        def delete(self):
            """Delete data by index from the user's profile."""
            current_user = g.current_user
            body = request.get_json() or {}
            
            # Validate required field
            index = body.get('index')
            
            if not index:
                return {'message': 'index field is required'}, 400
            
            try:
                # Get user's profile record
                profile_records = MatchmakersData.get_user_matchmakers_data(current_user.id, section='profile')
                
                if not profile_records:
                    return {'message': f'No profile setup found for {current_user.uid}'}, 404
                
                profile_record = profile_records[0]
                current_data = profile_record.data if profile_record.data else {}
                
                # Check if index exists
                if index not in current_data:
                    return {
                        'message': 'index not found',
                        'full_data': current_data
                    }, 404
                
                # Delete the indexed data
                deleted_data = current_data.pop(index)
                
                # Update the record
                profile_record.update(current_data)
                
                return {
                    'message': f'Data at index "{index}" deleted for {current_user.uid}',
                    'deleted_data': deleted_data,
                    'remaining_data': current_data
                }, 200
                
            except Exception as e:
                return {'message': f'Error deleting data: {str(e)}'}, 500

    class _ALL_DATA(Resource):
        def get(self):
            """Get all users' profile data (public endpoint)."""
            try:
                all_records = MatchmakersData.get_all_matchmakers_data()
                
                # Group by user
                user_data = {}
                for record in all_records:
                    uid = record.user.uid if record.user else f"user_{record.user_id}"
                    if uid not in user_data:
                        user_data[uid] = {
                            'id': record.user_id,
                            'uid': uid,
                            'data': {}
                        }
                    user_data[uid]['data'][record.section] = record.data
                
                return {
                    'message': 'All profile data',
                    'total_users': len(user_data),
                    'users': list(user_data.values())
                }, 200
            except Exception as e:
                return {'message': f'Error retrieving all data: {str(e)}'}, 500
    
    class _SAVE_PROFILE_JSON(Resource):
        @token_required()
        def post(self):
            """Save frontend quiz/profile data to the database"""
            current_user = g.current_user
            uid = current_user.uid

            body = request.get_json() or {}
            profile_data = body.get('profile_data')
            
            if not profile_data:
                return {'message': 'No profile_data provided'}, 400

            try:
                # Use MatchmakersData (DB) to store profile quiz under section 'profile'
                profile_records = MatchmakersData.get_user_matchmakers_data(current_user.id, section='profile')
                
                if not profile_records:
                    # create a new profile record with the quiz data
                    new_data = {'profile_quiz': profile_data}
                    profile_record = MatchmakersData(current_user, 'profile', new_data)
                    profile_record.create()
                else:
                    # Update existing record
                    profile_record = profile_records[0]
                    # PRESERVE existing data and add/update quiz responses
                    current_data = profile_record.data if profile_record.data else {}
                    current_data['profile_quiz'] = profile_data
                    profile_record.update(current_data)

                return {
                    'message': f'Profile data saved for {uid}', 
                    'data': profile_record.data
                }, 201
                
            except ValueError as ve:
                return {'message': f'Value error: {str(ve)}'}, 400
            except Exception as e:
                import traceback
                traceback.print_exc()
                return {'message': f'Error saving profile data: {str(e)}'}, 500

    # Register all resources
    api.add_resource(_DATA, '/data')
    api.add_resource(_WRITE, '/data-write')
    api.add_resource(_SETUP, '/setup')
    api.add_resource(_ADD, '/add')
    api.add_resource(_ALL_DATA, '/all-data')
    api.add_resource(_SAVE_PROFILE_JSON, '/save')