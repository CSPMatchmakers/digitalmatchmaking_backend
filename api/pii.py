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
from model.pii_quiz import ProfileQuiz
from flask_cors import CORS
pii_api = Blueprint('pii_api', __name__, url_prefix='/api/pii')
api = Api(pii_api)

class PIIAPI:
    
    class _SAVE_PROFILE(Resource):
        @token_required()
        def post(self):
            """Save or update user's PII quiz profile data to database."""
            current_user = g.current_user
            
            body = request.get_json() or {}
            profile_data = body.get('profile_data')
            
            if not profile_data:
                return {'message': 'No profile_data provided'}, 400
            
            # Validate profile_data is a list
            if not isinstance(profile_data, list):
                return {'message': 'profile_data must be an array'}, 400
            
            try:
                # Check if user already has a profile quiz
                existing_quiz = ProfileQuiz.get_by_user_id(current_user.id)
                
                if existing_quiz:
                    # Update existing record
                    existing_quiz.update(profile_data)
                    return {
                        'message': f'Profile data updated for {current_user.uid}',
                        'profile': existing_quiz.read()
                    }, 200
                else:
                    # Create new record
                    new_quiz = ProfileQuiz(
                        user_id=current_user.id,
                        profile_data=profile_data
                    )
                    new_quiz.create()
                    return {
                        'message': f'Profile data saved for {current_user.uid}',
                        'profile': new_quiz.read()
                    }, 201
                    
            except ValueError as e:
                return {'message': str(e)}, 409
            except Exception as e:
                return {'message': f'Error saving profile data: {str(e)}'}, 500
        
        @token_required()
        def get(self):
            """Retrieve the current user's PII quiz profile data."""
            current_user = g.current_user
            
            try:
                profile_quiz = ProfileQuiz.get_by_user_id(current_user.id)
                
                if not profile_quiz:
                    return {
                        'message': f'No profile data found for {current_user.uid}'
                    }, 404
                
                return {
                    'message': f'Profile data for {current_user.uid}',
                    'profile_data': profile_quiz.profile_data
                }, 200
                
            except Exception as e:
                return {'message': f'Error retrieving profile data: {str(e)}'}, 500
        
        @token_required()
        def delete(self):
            """Delete the current user's PII quiz profile data."""
            current_user = g.current_user
            
            try:
                profile_quiz = ProfileQuiz.get_by_user_id(current_user.id)
                
                if not profile_quiz:
                    return {
                        'message': f'No profile data found for {current_user.uid}'
                    }, 404
                
                profile_quiz.delete()
                return {
                    'message': f'Profile data deleted for {current_user.uid}'
                }, 200
                
            except Exception as e:
                return {'message': f'Error deleting profile data: {str(e)}'}, 500
    
    class _ALL_PROFILES(Resource):
        def get(self):
            """Get all users' profile quiz data (public endpoint for matchmaking)."""
            try:
                all_quizzes = ProfileQuiz.get_all()
                
                profiles = []
                for quiz in all_quizzes:
                    profile_data = quiz.read()
                    # Filter out PII for public endpoint
                    profile_data['profile_data'] = ProfileQuiz.filter_safe_data(profile_data['profile_data'])
                    profiles.append(profile_data)
                
                return {
                    'message': 'All profile data (PII filtered)',
                    'total_users': len(profiles),
                    'profiles': profiles
                }, 200
                
            except Exception as e:
                return {'message': f'Error retrieving all profiles: {str(e)}'}, 500
    
    class _SAFE_PROFILE(Resource):
        @token_required()
        def get(self):
            """Get user's safe profile data (PII filtered)."""
            current_user = g.current_user
            
            try:
                safe_profile = ProfileQuiz.get_safe_profile(current_user.id)
                
                if not safe_profile:
                    return {
                        'message': f'No profile data found for {current_user.uid}'
                    }, 404
                
                return {
                    'message': f'Safe profile data for {current_user.uid}',
                    'profile': safe_profile
                }, 200
                
            except Exception as e:
                return {'message': f'Error retrieving safe profile: {str(e)}'}, 500
    
    # Register all resources
    api.add_resource(_SAVE_PROFILE, '/profile')
    api.add_resource(_ALL_PROFILES, '/all-profiles')
    api.add_resource(_SAFE_PROFILE, '/safe-profile')