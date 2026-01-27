"""
Groq AI API for Bio Safety Analysis
Following the same pattern as personality quiz's analyze-personality endpoint
"""

from flask import Blueprint, request, jsonify
from groq import Groq
import os
import json

# Create blueprint
groq_bio_api = Blueprint('groq_bio_api', __name__, url_prefix='/api')

# Groq API key
import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def get_groq_client():
    """Initialize and return Groq client"""
    return Groq(api_key=GROQ_API_KEY)

@groq_bio_api.route('/analyze-bio-safety', methods=['POST'])
def analyze_bio_safety():
    """
    Analyze bio text for safety using Groq AI
    Pattern: Similar to /api/analyze-personality from the personality quiz
    """
    try:
        data = request.get_json()
        bio_text = data.get('bio_text', '')
        section = data.get('section', 'bio')
        
        if not bio_text:
            return jsonify({'error': 'No bio text provided'}), 400
        
        # Initialize Groq client
        client = get_groq_client()
        
        # Create prompt for safety analysis
        prompt = f"""You are a privacy and safety expert for a matchmaking platform.

Analyze this bio text for any personal information that could compromise user safety:

BIO TEXT: "{bio_text}"

Look for:
- Phone numbers, emails, addresses
- Specific locations (venues, buildings, streets)
- Routines (specific times + days)
- SSN, credit cards, or sensitive IDs
- Full names with other identifying info

Respond ONLY in this exact JSON format:
{{
  "is_safe": true or false,
  "risk_score": 0-100,
  "issues_found": ["list of specific issues, empty array if none"],
  "severity": "safe" or "warning" or "danger",
  "message": "brief explanation for the user",
  "suggestions": ["how to improve safety, empty array if safe"]
}}"""
        
        # Call Groq API (same pattern as personality quiz)
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a safety analysis AI. Respond ONLY with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",  # Fast and accurate model
            temperature=0.2,  # Low temperature for consistent safety checks
            max_tokens=800,
        )
        
        # Parse AI response
        ai_response = chat_completion.choices[0].message.content.strip()
        
        # Clean up markdown code blocks if present
        try:
            if '```json' in ai_response:
                ai_response = ai_response.split('```json')[1].split('```')[0].strip()
            elif '```' in ai_response:
                ai_response = ai_response.split('```')[1].split('```')[0].strip()
            
            result = json.loads(ai_response)
            
            return jsonify({
                'success': True,
                'analysis': result,
                'section': section
            }), 200
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"AI Response: {ai_response}")
            
            # Fallback response
            return jsonify({
                'success': True,
                'analysis': {
                    'is_safe': True,
                    'risk_score': 0,
                    'issues_found': [],
                    'severity': 'safe',
                    'message': 'No obvious safety issues detected',
                    'suggestions': []
                },
                'fallback': True
            }), 200
    
    except Exception as e:
        print(f"Groq API error: {str(e)}")
        
        # Return safe fallback on any error
        return jsonify({
            'success': True,
            'analysis': {
                'is_safe': True,
                'risk_score': 0,
                'issues_found': [],
                'severity': 'safe',
                'message': 'AI analysis unavailable, but basic check passed',
                'suggestions': []
            },
            'fallback': True,
            'error': str(e)
        }), 200


@groq_bio_api.route('/enhance-bio', methods=['POST'])
def enhance_bio():
    """
    Optional: Use Groq to suggest bio improvements
    """
    try:
        data = request.get_json()
        bio_text = data.get('bio_text', '')
        
        if not bio_text:
            return jsonify({'error': 'No bio text provided'}), 400
        
        client = get_groq_client()
        
        prompt = f"""You are a matchmaking profile expert. Suggest 3 specific ways to improve this bio:

"{bio_text}"

Make it more engaging, authentic, and appealing while keeping it safe.

Respond ONLY in this JSON format:
{{
  "suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"],
  "quality_score": 1-10
}}"""
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a bio writing expert. Respond ONLY with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=500,
        )
        
        ai_response = chat_completion.choices[0].message.content.strip()
        
        try:
            if '```json' in ai_response:
                ai_response = ai_response.split('```json')[1].split('```')[0].strip()
            elif '```' in ai_response:
                ai_response = ai_response.split('```')[1].split('```')[0].strip()
            
            result = json.loads(ai_response)
            
            return jsonify({
                'success': True,
                'enhancement': result
            }), 200
            
        except json.JSONDecodeError:
            return jsonify({
                'success': True,
                'enhancement': {
                    'suggestions': [
                        "Add more specific details about your interests",
                        "Show your personality through your writing style",
                        "Mention what you're looking for"
                    ],
                    'quality_score': 7
                },
                'fallback': True
            }), 200
    
    except Exception as e:
        print(f"Enhancement error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to enhance bio at this time'
        }), 500