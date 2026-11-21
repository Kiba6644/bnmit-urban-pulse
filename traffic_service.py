import os
import requests
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from math import radians, cos, pi
from database import db, TrafficCache

TOMTOM_API_KEY = "VsXnMJumXmtMexnNupdZsK3NNjnhvX2k"

def get_coordinates_for_pincode(pincode: str):
    """
    Returns (longitude, latitude) for a given pincode.
    Uses Nominatim for geocoding.
    """
    geolocator = Nominatim(user_agent="traffic_api_app")
    try:
        # Search by postalcode specifically to avoid mismatches
        location = geolocator.geocode({"postalcode": pincode})
        if location:
            return location.longitude, location.latitude
        
        # Fallback to general search
        location = geolocator.geocode(pincode)
        if location:
            return location.longitude, location.latitude
            
    except GeocoderTimedOut:
        return None, None
        
    return None, None

def get_bounding_box(lon, lat, radius_km=5.0):
    """
    Returns a bounding box [minLon, minLat, maxLon, maxLat] around a given point.
    Approximation for small distances.
    """
    # 1 degree of latitude is ~111.111 km
    lat_degree_distance = 111.111
    lon_degree_distance = 111.111 * cos(radians(lat))
    
    delta_lat = radius_km / lat_degree_distance
    delta_lon = radius_km / lon_degree_distance
    
    minLon = lon - delta_lon
    minLat = lat - delta_lat
    maxLon = lon + delta_lon
    maxLat = lat + delta_lat
    
    return [minLon, minLat, maxLon, maxLat]

def fetch_live_traffic_from_tomtom(minLon, minLat, maxLon, maxLat):
    """
    Fetches traffic incidents (which includes jams/traffic) within a bounding box.
    """
    if not TOMTOM_API_KEY:
        return {"error": "TOMTOM_API_KEY not configured on server"}
        
    url = f"https://api.tomtom.com/traffic/services/5/incidentDetails"
    bbox_str = f"{minLon},{minLat},{maxLon},{maxLat}"
    
    params = {
        "key": TOMTOM_API_KEY,
        "bbox": bbox_str,
        "fields": "{incidents{properties{id,iconCategory,magnitudeOfDelay,events{description},from,to}}}"
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return {"error": f"TomTom API returned status code {response.status_code}", "details": response.text}
    except Exception as e:
        return {"error": str(e)}

def parse_live_traffic(tomtom_response, pincode):
    """
    Parses the raw TomTom incident response into our standardized JSON format.
    """
    if "error" in tomtom_response:
        return tomtom_response
        
    incidents = tomtom_response.get("incidents", [])
    
    results = []
    for inc in incidents:
        props = inc.get("properties", {})
        
        # Extract road/location info from 'from' and 'to'
        from_loc = props.get("from", "Unknown")
        to_loc = props.get("to", "Unknown")
        road = f"{from_loc} to {to_loc}" if from_loc and to_loc else (from_loc or to_loc or "Unknown location")
        
        # magnitudeOfDelay: 0=Unknown, 1=Minor, 2=Moderate, 3=Major, 4=Undefined
        delay_magnitude = props.get("magnitudeOfDelay", 0)
        delay_map = {0: "Unknown", 1: "Minor", 2: "Moderate", 3: "Major", 4: "Undefined"}
        
        # Look at events for detailed description
        events = props.get("events", [])
        descriptions = [e.get("description", "") for e in events]
        traffic_desc = " | ".join(filter(None, descriptions)) if descriptions else "Traffic anomaly"
        
        results.append({
            "pincode": pincode,
            "location": road,
            "traffic_severity": delay_map.get(delay_magnitude, "Unknown"),
            "details": traffic_desc
        })
        
    return results

def get_live_traffic(pincode):
    """
    High-level function to get live traffic utilizing a 5-hour DB cache.
    """
    cache_key = f"traffic_pincode_{pincode}"
    cache_entry = TrafficCache.query.filter_by(query_key=cache_key).first()
    
    # Check if we have valid cache < 5 hours old
    if cache_entry and cache_entry.timestamp > (datetime.utcnow() - timedelta(hours=5)):
        return cache_entry.response_json

    lon, lat = get_coordinates_for_pincode(pincode)
    if lon is None or lat is None:
        return {"error": "Could not geocode the provided pincode"}
        
    # Get bounding box for ~5km radius
    bbox = get_bounding_box(lon, lat, radius_km=5.0)
    
    # Fetch from TomTom
    raw_data = fetch_live_traffic_from_tomtom(*bbox)
    
    # Parse
    parsed_data = parse_live_traffic(raw_data, pincode)
    
    # Update cache
    if isinstance(parsed_data, list): # Only cache successful list responses
        if not cache_entry:
            cache_entry = TrafficCache(query_key=cache_key)
            db.session.add(cache_entry)
        cache_entry.response_json = parsed_data
        cache_entry.timestamp = datetime.utcnow()
        db.session.commit()
        
    return parsed_data

def get_top_5_traffic():
    """
    Iterates over the cached traffic data to find the top 5 highest severity incidents.
    """
    all_caches = TrafficCache.query.all()
    all_incidents = []
    
    for c in all_caches:
        if isinstance(c.response_json, list):
            all_incidents.extend(c.response_json)
            
    # Define severity ranking
    severity_rank = {"Unknown": 0, "Undefined": 0, "Minor": 1, "Moderate": 2, "Major": 3}
    
    # Sort by descending severity, then simple string details length as tie breaker for bigger impact
    all_incidents.sort(key=lambda x: (severity_rank.get(x.get("traffic_severity", "Unknown"), 0), len(x.get("details", ""))), reverse=True)
    
    # Return top 5, removing potential duplicates by location
    unique_top = []
    seen_locations = set()
    for inc in all_incidents:
        if inc["location"] not in seen_locations:
            seen_locations.add(inc["location"])
            unique_top.append(inc)
        if len(unique_top) >= 5:
            break
            
    return unique_top

def calculate_traffic_score(location, expected_crowd):
    """
    Generates a 1-100 traffic risk score based on location severity and crowd size.
    """
    lon, lat = get_coordinates_for_pincode(location)
    if lon is None or lat is None:
        # Fallback score if we can't geocode
        return min(100, 10 + (expected_crowd // 500))
        
    # We do a direct fetch since location isn't a pincode (though it might hit API if un-cached)
    bbox = get_bounding_box(lon, lat, radius_km=2.0)
    raw_data = fetch_live_traffic_from_tomtom(*bbox)
    parsed = parse_live_traffic(raw_data, location)
    
    severity_multiplier = 1.0
    if isinstance(parsed, list) and len(parsed) > 0:
        # Check highest severity in the 2km radius
        severities = [inc.get("traffic_severity", "Unknown") for inc in parsed]
        if "Major" in severities:
            severity_multiplier = 3.0
        elif "Moderate" in severities:
            severity_multiplier = 2.0
        elif "Minor" in severities:
            severity_multiplier = 1.5
            
    base_score = 10
    crowd_factor = expected_crowd / 100.0  # +1 score per 100 people
    
    raw_score = (base_score + crowd_factor) * severity_multiplier
    
    # Cap between 1 and 100
    return int(max(1, min(100, raw_score)))

def get_peak_traffic(pincode):
    """
    Returns static/mock 'peak hour' traffic. Since free TomTom API doesn't 
    trivially give this historical slice in a simple call, we approximate or mock it.
    """
    lon, lat = get_coordinates_for_pincode(pincode)
    if lon is None or lat is None:
        return {"error": "Could not geocode the provided pincode"}
        
    # Mock some standard roads that are typically congested in this area
    # In a real app, this might query a database or run complex routing simulations
    mock_peak_data = [
        {
            "pincode": pincode,
            "location": "Main Arterial Road",
            "peak_traffic_severity": "Major",
            "details": "Heavy congestion typically from 9:00 AM - 11:00 AM and 5:00 PM - 8:00 PM."
        },
        {
            "pincode": pincode,
            "location": "Market Crossroad",
            "peak_traffic_severity": "Moderate",
            "details": "Moderate slowdowns during evening rush hours."
        },
        {
            "pincode": pincode,
            "location": "Highway Access Ramp",
            "peak_traffic_severity": "Major",
            "details": "Bottleneck at peak commuting hours."
        }
    ]
    
    return mock_peak_data
