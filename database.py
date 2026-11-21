from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class TrafficCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query_key = db.Column(db.String(255), unique=True, nullable=False)
    response_json = db.Column(db.JSON, nullable=True) # Assuming JSON support
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UserEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(100), nullable=False)
    expected_crowd = db.Column(db.Integer, nullable=False)
    traffic_score = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
