from flask import Blueprint, request, jsonify, current_app
import requests
import json
import re


anthropic_api = Blueprint('anthropic_api', __name__)


# FIXED PERSONALITY TYPES FOR CONSISTENT MATCHING
PERSONALITY_TYPES = {
   "The Leader": {
       "type_name": "The Leader",
       "emoji": "👑",
       "description": "Natural-born leaders who thrive on organizing and inspiring others. You bring structure and vision to any group, making decisive choices with confidence.",
       "strengths": [
           "Strong decision-making skills",
           "Natural authority and charisma",
           "Goal-oriented and driven",
           "Excellent at organizing people and projects"
       ],
       "recommendations": [
           "Works best with supportive and detail-oriented partners",
           "Compatible with Empaths and Analysts who complement leadership",
           "Seeks relationships where both can grow and achieve together"
       ]
   },
   "The Empath": {
       "type_name": "The Empath",
       "emoji": "💖",
       "description": "Deeply caring individuals who prioritize emotional connections and harmony. You have an innate ability to understand and support others' feelings.",
       "strengths": [
           "Exceptional emotional intelligence",
           "Compassionate and supportive",
           "Strong interpersonal skills",
           "Natural peacemaker in conflicts"
       ],
       "recommendations": [
           "Thrives with partners who value emotional depth",
           "Compatible with Leaders and Adventurers who appreciate sensitivity",
           "Seeks meaningful, heart-centered relationships"
       ]
   },
   "The Analyst": {
       "type_name": "The Analyst",
       "emoji": "🧠",
       "description": "Logical thinkers who excel at problem-solving and strategic planning. You approach life with curiosity and a desire to understand how things work.",
       "strengths": [
           "Strong analytical and critical thinking",
           "Detail-oriented and precise",
           "Independent and self-sufficient",
           "Innovative problem-solver"
       ],
       "recommendations": [
           "Matches well with partners who appreciate intellectual depth",
           "Compatible with Creatives and Leaders who value logic",
           "Seeks stimulating conversations and shared interests"
       ]
   },
   "The Adventurer": {
       "type_name": "The Adventurer",
       "emoji": "🌟",
       "description": "Spontaneous and energetic souls who embrace new experiences with enthusiasm. You bring excitement and optimism to every situation.",
       "strengths": [
           "Adaptable and flexible",
           "Optimistic and enthusiastic",
           "Open to new experiences",
           "Natural risk-taker and innovator"
       ],
       "recommendations": [
           "Best matched with partners who enjoy spontaneity",
           "Compatible with Empaths and Creatives who share openness",
           "Seeks fun, dynamic relationships with room for growth"
       ]
   },
   "The Creative": {
       "type_name": "The Creative",
       "emoji": "🎨",
       "description": "Imaginative visionaries who see the world through a unique lens. You express yourself through originality and appreciate beauty in all forms.",
       "strengths": [
           "Highly creative and artistic",
           "Original thinking and innovation",
           "Strong aesthetic appreciation",
           "Expressive and authentic"
       ],
       "recommendations": [
           "Thrives with partners who appreciate uniqueness",
           "Compatible with Adventurers and Empaths who value expression",
           "Seeks relationships that encourage creative growth"
       ]
   },
   "The Peacemaker": {
       "type_name": "The Peacemaker",
       "emoji": "🕊️",
       "description": "Calm, balanced individuals who bring harmony wherever they go. You value stability and work to create peaceful environments for everyone.",
       "strengths": [
           "Diplomatic and fair-minded",
           "Patient and understanding",
           "Excellent mediator",
           "Creates harmonious environments"
       ],
       "recommendations": [
           "Matches well with all types due to adaptability",
           "Especially compatible with Leaders and Analysts",
           "Seeks stable, balanced relationships"
       ]
   },
   "The Guardian": {
       "type_name": "The Guardian",
       "emoji": "🛡️",
       "description": "Reliable protectors who prioritize duty and care for their loved ones. You create security through dedication and thoughtful planning.",
       "strengths": [
           "Highly dependable and loyal",
           "Strong sense of responsibility",
           "Practical and organized",
           "Protective of loved ones"
       ],
       "recommendations": [
           "Compatible with partners who value loyalty",
           "Works well with Empaths and Peacemakers",
           "Seeks committed, long-term relationships"
       ]
   },
   "The Visionary": {
       "type_name": "The Visionary",
       "emoji": "🔮",
       "description": "Forward-thinking dreamers who imagine possibilities beyond the present. You inspire others with your innovative ideas and big-picture thinking.",
       "strengths": [
           "Strategic long-term thinking",
           "Innovative and forward-looking",
           "Inspirational and motivating",
           "Sees connections others miss"
       ],
       "recommendations": [
           "Thrives with partners who support big dreams",
           "Compatible with Creatives and Analysts",
           "Seeks relationships that encourage mutual growth"
       ]
   }
}


@anthropic_api.route('/api/analyze-personality', methods=['POST'])
def analyze_personality():
   """
   Personality analysis endpoint using Groq (FREE & FAST API).
   Classifies users into FIXED personality types for consistent matching.
   """
   try:
       # Get the responses from the request
       data = request.get_json()
       responses = data.get('responses', [])


       if not responses:
           return jsonify({'error': 'No responses provided'}), 400


       # Get Groq API key
       api_key = current_app.config.get('GROQ_API_KEY')


       if not api_key:
           print("⚠️ Groq API not configured, using fallback")
           return jsonify(PERSONALITY_TYPES["The Peacemaker"]), 200


       # Build the prompt with fixed types
       # Format responses, highlighting free-response answers for deeper analysis
       responses_text = []
       for r in responses:
           answer_type = r.get('type', 'multipleChoice')
           if answer_type == 'freeResponse':
               responses_text.append(f"Q: {r['question']}\nA (free response): {r['answer']}")
           else:
               responses_text.append(f"Q: {r['question']}\nA: {r['answer']}")


       responses_formatted = "\n\n".join(responses_text)


       types_list = "\n".join([f"- {name}: {info['description'][:100]}..." for name, info in PERSONALITY_TYPES.items()])


       prompt = f"""Based on these personality quiz responses (including some free-response answers), classify the person into ONE of these EXACT personality types:


{types_list}


Quiz Responses:
{responses_formatted}


Pay special attention to the free-response answers as they reveal deeper personality traits. Analyze all responses together and determine which ONE personality type fits best. Respond with ONLY the exact type name from the list above, nothing else. Choose from:
The Leader, The Empath, The Analyst, The Adventurer, The Creative, The Peacemaker, The Guardian, The Visionary"""


       # Call Groq API
       print(f"🔑 Calling Groq API for personality classification...")


       response = requests.post(
           "https://api.groq.com/openai/v1/chat/completions",
           headers={
               'Authorization': f'Bearer {api_key}',
               'Content-Type': 'application/json'
           },
           json={
               "model": "llama-3.3-70b-versatile",
               "messages": [
                   {
                       "role": "system",
                       "content": "You are a personality classification expert. Respond with ONLY the personality type name, nothing else."
                   },
                   {
                       "role": "user",
                       "content": prompt
                   }
               ],
               "temperature": 0.3,  # Lower temperature for more consistent classification
               "max_tokens": 50
           },
           timeout=30
       )


       print(f"📡 Groq API response status: {response.status_code}")


       if response.status_code == 200:
           api_data = response.json()
           classified_type = api_data['choices'][0]['message']['content'].strip()


           print(f"✅ AI classified as: {classified_type}")


           # Match to our fixed types
           if classified_type in PERSONALITY_TYPES:
               result = PERSONALITY_TYPES[classified_type]
               print(f"✨ Matched to personality type: {classified_type}")
               return jsonify(result), 200
           else:
               # Fuzzy match if exact match fails
               for type_name in PERSONALITY_TYPES.keys():
                   if type_name.lower() in classified_type.lower():
                       result = PERSONALITY_TYPES[type_name]
                       print(f"✨ Fuzzy matched to: {type_name}")
                       return jsonify(result), 200


               # Default to Peacemaker if no match
               print(f"⚠️ No match found, defaulting to Peacemaker")
               return jsonify(PERSONALITY_TYPES["The Peacemaker"]), 200


       else:
           print(f"❌ API Error, using default type")
           return jsonify(PERSONALITY_TYPES["The Peacemaker"]), 200


   except Exception as e:
       print(f"❌ Error in analyze-personality: {e}")
       return jsonify(PERSONALITY_TYPES["The Peacemaker"]), 200



