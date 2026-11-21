from datetime import datetime, timedelta

def get_upcoming_events(pincode: str):
    """
    Returns hardcoded upcoming Indian festivals/events and associated venue types.
    The response uses the Hindu/Indian calendar context.
    """
    today = datetime.now()
    
    # Hardcoded mock list of upcoming events for the hackathon
    # Dates are roughly approximated for the coming months
    upcoming_events = [
        {
            "event_name": "Ramzan (Eid-ul-Fitr)",
            "date": (today + timedelta(days=15)).strftime("%Y-%m-%d"),
            "religion_or_type": "Islamic",
            "venue_type": "Mosques"
        },
        {
            "event_name": "Ugadi",
            "date": (today + timedelta(days=20)).strftime("%Y-%m-%d"),
            "religion_or_type": "Hindu",
            "venue_type": "Temples"
        },
        {
            "event_name": "Rama Navami",
            "date": (today + timedelta(days=35)).strftime("%Y-%m-%d"),
            "religion_or_type": "Hindu",
            "venue_type": "Temples"
        },
        {
            "event_name": "Ganesha Chaturthi",
            "date": "2026-09-14",
            "religion_or_type": "Hindu",
            "venue_type": "Pandals / Temples"
        },
        {
            "event_name": "Deepavali",
            "date": "2026-11-08",
            "religion_or_type": "Hindu",
            "venue_type": "Temples / Markets"
        }
    ]
    
    # Filter out events that have already passed in the specific mock year
    future_events = [e for e in upcoming_events if e["date"] >= today.strftime("%Y-%m-%d")]
    
    return {
        "pincode_target": pincode,
        "calendar_source": "Jyotisham/Indian-Calendar-Mock",
        "events": future_events
    }
