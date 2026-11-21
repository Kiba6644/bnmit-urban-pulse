from flask import Flask, request, jsonify
from traffic_service import get_live_traffic, get_peak_traffic, get_top_5_traffic, calculate_traffic_score
from crowd_service import get_crowd_density
from event_service import get_upcoming_events
from database import db, UserEvent
from twilio.twiml.messaging_response import MessagingResponse
import os
import json

app = Flask(__name__)
# Database Setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hackathon.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create tables before first request or explicitly
with app.app_context():
    db.create_all()

@app.route("/api/traffic/live", methods=["GET"])
def live_traffic():
    """
    Endpoint to fetch live traffic for a given pincode.
    Query parameters:
    - pincode: The postal code to search around.
    """
    pincode = request.args.get("pincode")
    if not pincode:
        return jsonify({"error": "Missing 'pincode' parameter"}), 400
        
    data = get_live_traffic(pincode)
    if isinstance(data, dict) and "error" in data:
        return jsonify(data), 500
        
    return jsonify({
        "status": "success",
        "route_type": "live_traffic",
        "data": data
    })

@app.route("/api/traffic/peak", methods=["GET"])
def peak_traffic():
    """
    Endpoint to fetch typical peak hour traffic for a given pincode.
    Query parameters:
    - pincode: The postal code to search around.
    """
    pincode = request.args.get("pincode")
    if not pincode:
        return jsonify({"error": "Missing 'pincode' parameter"}), 400
        
    data = get_peak_traffic(pincode)
    if isinstance(data, dict) and "error" in data:
        return jsonify(data), 500
        
    return jsonify({
        "status": "success",
        "route_type": "peak_hour_traffic",
        "data": data
    })


@app.route("/api/crowd", methods=["GET"])
def crowd_density():
    """
    Endpoint to fetch simulated TelecomML crowd density for a given pincode.
    Query parameters:
    - pincode: The postal code to search around.
    """
    pincode = request.args.get("pincode")
    if not pincode:
        return jsonify({"error": "Missing 'pincode' parameter"}), 400
        
    data = get_crowd_density(pincode)
    if isinstance(data, dict) and "error" in data:
        return jsonify(data), 500
        
    return jsonify({
        "status": "success",
        "route_type": "telecom_crowd_density",
        "data": data
    })

@app.route("/api/events", methods=["GET"])
def upcoming_events():
    """
    Endpoint to fetch upcoming calendar events and venue types for a pincode.
    Query parameters:
    - pincode: The postal code to search around.
    """
    pincode = request.args.get("pincode")
    if not pincode:
        return jsonify({"error": "Missing 'pincode' parameter"}), 400
        
    data = get_upcoming_events(pincode)
    
    # Append approved user events
    approved_user_events = UserEvent.query.filter_by(status='approved').all()
    for e in approved_user_events:
        data["events"].append({
            "event_name": e.event_name,
            "date": e.date,
            "religion_or_type": "User Submitted",
            "venue_type": e.location,
            "expected_crowd": e.expected_crowd,
            "traffic_score": e.traffic_score
        })
        
    return jsonify({
        "status": "success",
        "route_type": "upcoming_calendar_events",
        "data": data
    })

@app.route("/api/traffic/top5", methods=["GET"])
def top5_traffic():
    """
    Endpoint to retrieve the top 5 highest severity traffic incidents from the local 5-hour cache.
    """
    data = get_top_5_traffic()
    return jsonify({
        "status": "success",
        "route_type": "top_5_traffic",
        "data": data
    })

@app.route("/api/whatsapp/webhook", methods=["POST"])
def whatsapp_webhook():
    """
    Twilio Webhook Endpoint for WhatsApp.
    Expects message payload in format: <event name> <location> <date> <expected crowd>
    """
    incoming_msg = request.values.get('Body', '').strip()
    
    # Standard Twilio Response Object
    resp = MessagingResponse()
    msg = resp.message()
    
    parts = incoming_msg.split()
    if len(parts) >= 4:
        # Join words normally if event name uses underscores or if they just spaced it. 
        # A simple robust parse for hackathon: first word is event, next is location, date, crowd.
        event_name = parts[0]
        location = parts[1]
        date = parts[2]
        try:
            expected_crowd = int(parts[3])
        except ValueError:
            expected_crowd = 100 # default
            
        score = calculate_traffic_score(location, expected_crowd)
        
        new_event = UserEvent(
            event_name=event_name,
            location=location,
            date=date,
            expected_crowd=expected_crowd,
            traffic_score=score
        )
        db.session.add(new_event)
        db.session.commit()
        
        msg.body(f"Event '{event_name}' registered successfully! The projected Traffic Severity Score is: {score}/100. We'll monitor the area.")
    else:
        msg.body("Invalid format. Please send: <EventName> <Location_Pincode> <YYYY-MM-DD> <ExpectedCrowd> (e.g. 'TechFest 560070 2026-05-10 2000')")
        
    return str(resp)

@app.route("/api/user_events", methods=["GET"])
def get_user_events():
    """
    Retrieves all pending user events from the database.
    """
    events = UserEvent.query.filter_by(status='pending').all()
    event_list = [{
        "id": e.id,
        "event_name": e.event_name,
        "location": e.location,
        "date": e.date,
        "expected_crowd": e.expected_crowd,
        "traffic_score": e.traffic_score,
        "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for e in events]
    
    return jsonify({
        "status": "success",
        "route_type": "user_events",
        "data": event_list
    })

@app.route("/api/user_events/<int:id>/approve", methods=["POST"])
def approve_user_event(id):
    """
    Approves a user event.
    """
    event = UserEvent.query.get(id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
        
    req_data = request.get_json(silent=True) or {}
    if req_data.get("status") == "approved":
        event.status = "approved"
        db.session.commit()
        return jsonify({"status": "success", "message": "Event approved"}), 200
        
    return jsonify({"error": "Invalid status payload"}), 400

@app.route("/api/phonepe", methods=["GET"])
def phonepe_data():
    """
    Returns local PhonePe UPI quarterly data for Bangalore pincodes.
    Query parameters:
    - period: 'normal' or 'kadlekai'
    """
    period = request.args.get("period", "normal").lower()
    
    file_map = {
        "normal": "data/phonepe_normal.json",
        "kadlekai": "data/phonepe_kadlekai.json"
    }
    
    target_file = file_map.get(period)
    if not target_file:
        return jsonify({"error": "Invalid period. Use 'normal' or 'kadlekai'."}), 400
        
    file_path = os.path.join(os.path.dirname(__file__), target_file)
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            return jsonify({
                "status": "success",
                "route_type": "phonepe_upi_data",
                "data": data
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not Found"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5000, host='0.0.0.0')
