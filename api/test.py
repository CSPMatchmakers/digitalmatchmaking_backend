from flask import Blueprint, jsonify, request,  current_app
from datetime import datetime
from functools import wraps
from model.user import User
from __init__ import app
from flask_cors import cross_origin


test_api = Blueprint('test_api', __name__, url_prefix='/api')


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-KEY")
        if api_key and api_key == current_app.config["TEST_API_KEY"]:
            return f(*args, **kwargs)
        return jsonify({"error": "Unauthorized"}), 401
    return decorated



@test_api.route('/joemamma', methods=['GET'])
def yor_mama():
    return jsonify("Joe Mama!")

@test_api.route('/bell', methods=['GET'])
@cross_origin() 
def get_bell_schedule():
    bell_schedule = {}

    bell_schedule["Monday, Tuesday, Thursday, Friday"] = [
        {"time": "8:35 AM - 9:41 AM", "period": "1st Period"},
        {"time": "9:46 AM - 10:55 AM", "period": "2nd Period"},
        {"time": "11:37 AM - 12:43 PM", "period": "3rd Period"},
        {"time": "12:43 PM - 1:13 PM", "period": "Lunch"},
        {"time": "1:18 PM - 2:24 PM", "period": "4th Period"},
        {"time": "2:29 PM - 3:35 PM", "period": "5th Period"},
    ]

    bell_schedule["Wednesday"] = [
        {"time": "9:35 AM - 10:35 AM", "period": "1st Period"},
        {"time": "10:39 AM - 11:38 AM", "period": "2nd Period"},
        {"time": "11:53 AM - 12:57 PM", "period": "3rd Period"},
        {"time": "12:57 PM - 1:27 PM", "period": "Lunch"},
        {"time": "1:32 PM - 2:31 PM", "period": "4th Period"},
        {"time": "2:36 PM - 3:35 PM", "period": "5th Period"},
    ]

    output = {
        "school": "DNHS",
       ## "bell_schedule": bell_schedule,
        "current_period": get_current_period(bell_schedule),
       ## "current_day": datetime.now().strftime("%A"),
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }

    return jsonify(output)

def get_current_period(schedule):
    now = datetime.now()
    current_time = now.time()
    current_day = now.strftime("%A")

    if current_day in ["Monday", "Tuesday", "Thursday", "Friday"]:
        today_schedule = schedule["Monday, Tuesday, Thursday, Friday"]
    elif current_day == "Wednesday":
        today_schedule = schedule["Wednesday"]
    else:
        today_schedule = None  # weekend
    
    if not today_schedule:
        return "No schedule available for today"
    
    for period in today_schedule:
        start_str, end_str = period["time"].split(" - ")
        start = datetime.strptime(start_str.strip(), "%I:%M %p").time()
        end = datetime.strptime(end_str.strip(), "%I:%M %p").time()

        if start <= current_time <= end:
            # build full datetime for today’s end time
            end_dt = datetime.combine(now.date(), end)
            time_left = end_dt - now

            # format time left as HH:MM:SS
            total_seconds = int(time_left.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_time_left = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            return {
                "period": period,
                "time_left": formatted_time_left,
                "seconds_left": total_seconds
            }
    
    return f"No class right now (current time: {now.strftime('%I:%M %p')})"