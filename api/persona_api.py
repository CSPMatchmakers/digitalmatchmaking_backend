from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
from api.authorize import auth_required
from model.persona import Persona
from __init__ import db

persona_api = Blueprint('persona_api', __name__, url_prefix='/api')

# API docs https://flask-restful.readthedocs.io/en/latest/api.html
api = Api(persona_api)

class PersonaAPI:        
    
    class _Create(Resource):
        @auth_required(roles="Admin")
        def post(self):
            """Create a new persona"""
            body = request.get_json()
            
            # Validate required fields
            alias = body.get('alias')
            if alias is None or len(alias) < 2:
                return {'message': 'Alias is missing or is less than 2 characters'}, 400
            
            category = body.get('category')
            if category is None:
                return {'message': 'Category is required'}, 400
            
            bio_map = body.get('bio_map')
            if bio_map is None:
                return {'message': 'Bio map is required'}, 400
            
            # Validate bio_map has required fields
            if not bio_map.get('title'):
                return {'message': 'Bio map must include title'}, 400
            if not bio_map.get('description'):
                return {'message': 'Bio map must include description'}, 400
            
            empathy_map = body.get('empathy_map')
            
            # Create persona object
            persona_obj = Persona(
                _alias=alias,
                _category=category,
                _bio_map=bio_map,
                _empathy_map=empathy_map
            )
            
            # Add to database
            persona = persona_obj.create()
            if persona:
                return jsonify(persona.read())
            
            return {'message': f'Failed to create persona {alias}, possibly duplicate alias'}, 400
    
    class _Read(Resource):
        def get(self, id=None):
            """Get persona by ID or all personas"""
            if id is not None:
                # Get single persona by ID
                persona = Persona.query.get(id)
                if persona is None:
                    return {'message': f'Persona with id {id} not found'}, 404
                return jsonify(persona.read())
            else:
                # Get all personas
                personas = Persona.query.all()
                json_ready = [persona.read() for persona in personas]
                return jsonify(json_ready)
    
    class _Update(Resource):
        @auth_required(roles="Admin")
        def put(self, id):
            """Update an existing persona"""
            body = request.get_json()
            
            # Find the persona
            persona = Persona.query.get(id)
            if persona is None:
                return {'message': f'Persona with id {id} not found'}, 404
            
            # Update fields if provided
            if 'alias' in body:
                alias = body.get('alias')
                if alias and len(alias) >= 2:
                    persona._alias = alias
                else:
                    return {'message': 'Alias must be at least 2 characters'}, 400
            
            if 'category' in body:
                category = body.get('category')
                if category:
                    persona._category = category
            
            if 'bio_map' in body:
                bio_map = body.get('bio_map')
                if bio_map:
                    persona._bio_map = bio_map
            
            if 'empathy_map' in body:
                empathy_map = body.get('empathy_map')
                persona._empathy_map = empathy_map
            
            # Commit changes
            try:
                db.session.commit()
                return jsonify(persona.read())
            except Exception as e:
                db.session.rollback()
                return {'message': f'Error updating persona: {str(e)}'}, 500
    
    class _Delete(Resource):
        @auth_required(roles="Admin")
        def delete(self, id):
            """Delete a persona"""
            persona = Persona.query.get(id)
            if persona is None:
                return {'message': f'Persona with id {id} not found'}, 404
            
            json_data = persona.read()
            
            try:
                db.session.delete(persona)
                db.session.commit()
                return {'message': f'Deleted persona: {json_data["alias"]}', 'persona': json_data}, 200
            except Exception as e:
                db.session.rollback()
                return {'message': f'Error deleting persona: {str(e)}'}, 500
    
    # Building RESTful API endpoints
    api.add_resource(_Create, '/persona/create')
    api.add_resource(_Read, '/persona', '/persona/<int:id>')
    api.add_resource(_Update, '/persona/update/<int:id>')
    api.add_resource(_Delete, '/persona/delete/<int:id>')
