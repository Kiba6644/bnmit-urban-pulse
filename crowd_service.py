import random
from traffic_service import get_coordinates_for_pincode

def get_crowd_density(pincode: str):
    """
    Returns simulated TelecomML-based crowd density data for a given pincode.
    In a real-world scenario, this would query a telco API using the lat/lon.
    """
    lon, lat = get_coordinates_for_pincode(pincode)
    if lon is None or lat is None:
        return {"error": "Could not geocode the provided pincode"}
        
    # Standard labels for hackathon mock
    density_levels = ["Low", "Moderate", "High", "Critical (Overcrowded)"]
    
    # Generate realistic-looking mock data for multiple sectors in the pincode
    sectors = ["Sector A (Commercial)", "Sector B (Residential)", "Sector C (Transit Hub)", "Sector D (Marketplace)"]
    
    mock_data = []
    for sector in sectors:
        # Heavily weight commercial/transit to be higher
        if "Transit" in sector or "Market" in sector:
            level = random.choice(["High", "Critical (Overcrowded)", "Moderate"])
        else:
            level = random.choice(["Low", "Moderate", "High"])
            
        mock_data.append({
            "pincode": pincode,
            "sub_location": sector,
            "telecom_node_id": f"NODE-{random.randint(1000, 9999)}",
            "estimated_people_count": random.randint(500, 5000) if level in ["High", "Critical (Overcrowded)"] else random.randint(50, 499),
            "density_status": level
        })
        
    return {
        "source": "TelecomML-Simulated",
        "regional_overview": f"Crowd modeling for area {pincode}",
        "sector_data": mock_data
    }
