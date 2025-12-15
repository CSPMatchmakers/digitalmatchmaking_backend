## Create Users, Get User Data, Store Data, Change Data

import jwt
from flask import Blueprint, app, request, jsonify, current_app, Response, g, Flask
from flask_restful import Api, Resource # used for REST API building
from datetime import datetime
from __init__ import app
from api.jwt_authorize import token_required
from model.user import User
from model.matchmaking import profile_setup_exists, create_profile_setup, get_profile_setup, _read_profile_setups, _write_profile_setups
from model.github import GitHubUser
import os
import json

matchmaking_api = Blueprint('matchmaking_api', __name__,
                   url_prefix='/api/match')

# API docs https://flask-restful.readthedocs.io/en/latest/api.html
api = Api(matchmaking_api)


class MatchmakingAPI:

    class _DATA(Resource):
        @token_required()
        def get(self):
            current_user = g.current_user
            uid = current_user.uid
            
            try:
                # Read all setups and find current user's data
                setups = _read_profile_setups()
                
                for setup in setups:
                    if setup['uid'] == uid:
                        return {
                            'message': f'Data for {uid}',
                            'setup': setup
                        }, 200
                
                # If no setup found, return empty data
                return {
                    'message': f'No data found for {uid}',
                    'setup': None
                }, 404
                
            except Exception as e:
                return {'message': f'Error retrieving data: {str(e)}'}, 500

    class _WRITE(Resource):
        @token_required()
        def post(self):
            return {"message": "hello"}

    class _SETUP(Resource):
        @token_required()
        def post(self):
            """Initialize profile setup for the current user.
            
            Checks if the user already has a profile setup record in the JSON file.
            If yes, returns an error (already created).
            If no, creates a new profile setup record in the JSON file.
            """

            current_user = g.current_user
            uid = current_user.uid

            # Check if profile setup already exists
            if profile_setup_exists(uid):
                return {'message': f'Profile setup for {uid} already created'}, 409  # 409 Conflict

            # Create new profile setup record
            try:
                setup = create_profile_setup(uid)
                
                if setup:
                    return {'message': f'Profile setup initialized for {uid}', 'setup': setup}, 201
                else:
                    return {'message': f'Failed to create profile setup for {uid}'}, 500
                    
            except Exception as e:
                return {'message': f'Error initializing profile setup: {str(e)}'}, 500

    class _ADD(Resource):
        @token_required()
        def post(self):
            """Add custom indexed data to the user's profile.
            
            Expects JSON body with:
            {
                "index": "name_of_field",
                "data": <any_data_here>
            }
            
            This will add/update the field under profile_setups.json
            """
            current_user = g.current_user
            uid = current_user.uid
            body = request.get_json() or {}
            
            # Validate required fields
            index = body.get('index')
            data = body.get('data')
            
            if not index:
                return {'message': 'index field is required'}, 400
            if data is None:
                return {'message': 'data field is required'}, 400
            
            try:
                # Read current setups
                setups = _read_profile_setups()
                
                # Find user's setup
                user_setup = None
                for setup in setups:
                    if setup['uid'] == uid:
                        user_setup = setup
                        break
                
                # If no setup exists, create one first
                if user_setup is None:
                    user_setup = {
                        'id': len(setups) + 1,
                        'uid': uid,
                        'created_at': datetime.utcnow().isoformat(),
                        'data': {}
                    }
                    setups.append(user_setup)
                else:
                    # Ensure data dict exists
                    if 'data' not in user_setup:
                        user_setup['data'] = {}
                
                # Add/update the indexed data
                user_setup['data'][index] = data
                
                # Write back to file
                _write_profile_setups(setups)
                
                return {
                    'message': f'Data added to profile for {uid}',
                    'index': index,
                    'data': data
                }, 201
                
            except Exception as e:
                return {'message': f'Error adding data: {str(e)}'}, 500

        @token_required()
        def delete(self):
            """Delete data by index from the user's profile.
            
            Expects JSON body with:
            {
                "index": "name_of_field"
            }
            
            If the index is not found, returns the full data and says index not found.
            """
            current_user = g.current_user
            uid = current_user.uid
            body = request.get_json() or {}
            
            # Validate required field
            index = body.get('index')
            
            if not index:
                return {'message': 'index field is required'}, 400
            
            try:
                # Read current setups
                setups = _read_profile_setups()
                
                # Find user's setup
                user_setup = None
                for setup in setups:
                    if setup['uid'] == uid:
                        user_setup = setup
                        break
                
                # If no setup exists, return error
                if user_setup is None:
                    return {'message': f'No profile setup found for {uid}'}, 404
                
                # Ensure data dict exists
                if 'data' not in user_setup:
                    user_setup['data'] = {}
                
                # Check if index exists
                if index not in user_setup['data']:
                    return {
                        'message': 'index not found',
                        'full_data': user_setup['data']
                    }, 404
                
                # Delete the indexed data
                deleted_data = user_setup['data'].pop(index)
                
                # Write back to file
                _write_profile_setups(setups)
                
                return {
                    'message': f'Data at index "{index}" deleted for {uid}',
                    'deleted_data': deleted_data,
                    'remaining_data': user_setup['data']
                }, 200
                
            except Exception as e:
                return {'message': f'Error deleting data: {str(e)}'}, 500

    class _ALL_DATA(Resource):
        # REMOVED @token_required() decorator to make this endpoint public
        def get(self):
            """Get all users' profile data.
            
            Returns all profile setups including id, uid, created_at, and data for each user.
            NOTE: This endpoint is public to allow matchmaking without authentication.
            """
            try:
                setups = _read_profile_setups()
                return {
                    'message': 'All profile data',
                    'total_users': len(setups),
                    'setups': setups
                }, 200
            except Exception as e:
                return {'message': f'Error retrieving all data: {str(e)}'}, 500

    class SaveProfileJSON(Resource):
        @token_required()
        def post(self):
            """Save frontend quiz/profile data to the JSON file

            Expects body:
            {
                "profile_data": [
                    {"question": "q1", "response": "r1"},
                    ...
                ]
            }
            """
            current_user = g.current_user
            uid = current_user.uid

            body = request.get_json() or {}
            profile_data = body.get('profile_data')
            if not profile_data:
                return {'message': 'No profile_data provided'}, 400

            try:
                setups = _read_profile_setups()

                # Find or create user's setup
                user_setup = next((s for s in setups if s['uid'] == uid), None)
                if user_setup is None:
                    create_profile_setup(uid)
                    setups = _read_profile_setups()  # refresh after creation
                    user_setup = next((s for s in setups if s['uid'] == uid), None)

                if 'data' not in user_setup:
                    user_setup['data'] = {}

                # Merge/overwrite profile_data items into user_setup['data']
                for item in profile_data:
                    q = item.get('question')
                    r = item.get('response')
                    if q is not None:
                        user_setup['data'][q] = r

                _write_profile_setups(setups)
                return {'message': f'Profile data saved for {uid}', 'setup': user_setup}, 201
            except Exception as e:
                return {'message': f'Error saving profile data: {str(e)}'}, 500


    api.add_resource(_DATA, '/data')
    api.add_resource(_WRITE, '/data-write')
    api.add_resource(_SETUP, '/setup')
    api.add_resource(_ADD, '/add')
    api.add_resource(_ALL_DATA, '/all-data')
    api.add_resource(SaveProfileJSON, '/save-profile-json')