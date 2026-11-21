# Urban Pulse - Traffic, Crowd Density & Event Coordination Platform

Urban Pulse (BNMIT Hackathon) is an intelligent urban analytics and alert backend that tracks real-time traffic bottlenecks, crowd density metrics, and nearby events to provide live rerouting recommendations and automated SMS alerts via Twilio.

## Features
- **Live & Peak Traffic Analysis**: Pincode-level query endpoints to detect high-congestion arteries and calculate dynamic traffic severity scores.
- **Crowd Density Tracking**: Aggregates foot traffic and crowd clustering estimates across city hotspots.
- **Event Scheduling & Integration**: Matches user itinerary events against road conditions and congestion forecasts.
- **Automated Messaging**: Integrated Twilio webhook service for dispatching commuter status updates and reroute notices.

## Architecture
- `app.py`: Main Flask REST API and Twilio messaging endpoints.
- `traffic_service.py`: Computes traffic congestion, peak load modeling, and top congested corridors.
- `crowd_service.py`: Real-time density calculation heuristics.
- `event_service.py`: Manages upcoming community and metropolitan events.
- `database.py`: SQLAlchemy database models for user events and alert tracking.

## Getting Started

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server**:
   ```bash
   python app.py
   ```

3. The server starts on `http://127.0.0.1:5000` with endpoints:
   - `GET /api/traffic/live?pincode=<pin>`
   - `GET /api/traffic/peak?pincode=<pin>`
   - `GET /api/crowd/density?pincode=<pin>`
   - `GET /api/events/upcoming`
