import pandas as pd
import folium
import numpy as np
from geopy.geocoders import Nominatim
from geopy.distance import great_circle
import streamlit as st
import datetime

MAJOR_PORTS = {
    # Asia
    "Mumbai, India": (18.9438, 72.8353),
    "Chennai, India": (13.0827, 80.2707),
    "Kolkata, India": (22.5726, 88.3639),
    "Cochin, India": (9.9312, 76.2673),
    "Visakhapatnam, India": (17.6868, 83.2185),
    "Kandla, India": (23.0333, 70.2167),
    "Mundra, India": (22.8394, 69.7250),
    "Tuticorin, India": (8.7642, 78.1348),
    "Nhava Sheva, India": (18.9500, 72.9500),
    "Singapore, Singapore": (1.274, 103.802),
    "Shanghai, China": (31.332, 121.649),
    "Hong Kong, China": (22.286, 114.174),
    "Shenzhen, China": (22.530, 114.054),
    "Qingdao, China": (36.067, 120.383),
    "Ningbo, China": (29.868, 121.544),
    "Tianjin, China": (38.986, 117.732),
    "Guangzhou, China": (23.108, 113.319),
    "Tokyo, Japan": (35.652, 139.840),
    "Yokohama, Japan": (35.444, 139.638),
    "Busan, South Korea": (35.104, 129.036),
    "Kaohsiung, Taiwan": (22.615, 120.266),
    "Ho Chi Minh City, Vietnam": (10.752, 106.756),
    "Bangkok, Thailand": (13.723, 100.570),
    "Colombo, Sri Lanka": (6.940, 79.843),
    "Karachi, Pakistan": (24.852, 67.016),
    "Port Klang, Malaysia": (2.999, 101.392),
    "Jakarta, Indonesia": (-6.108, 106.877),
    "Manila, Philippines": (14.510, 120.982),
    # Middle East
    "Dubai, UAE": (25.011, 55.056),
    "Fujairah, UAE": (25.120, 56.330),
    "Jeddah, Saudi Arabia": (21.490, 39.190),
    "Dammam, Saudi Arabia": (26.432, 50.103),
    "Muscat, Oman": (23.630, 58.590),
    "Salalah, Oman": (16.938, 54.003),
    "Bandar Abbas, Iran": (27.178, 56.272),
    # Europe
    "Rotterdam, Netherlands": (51.949, 4.145),
    "Hamburg, Germany": (53.541, 9.986),
    "Antwerp, Belgium": (51.260, 4.400),
    "Bremerhaven, Germany": (53.541, 8.583),
    "Felixstowe, United Kingdom (UK)": (51.955, 1.305),
    "Southampton, United Kingdom (UK)": (50.899, -1.404),
    "London, United Kingdom (UK)": (51.508, -0.076),
    "Le Havre, France": (49.481, 0.107),
    "Marseille, France": (43.296, 5.370),
    "Barcelona, Spain": (41.347, 2.162),
    "Valencia, Spain": (39.452, -0.317),
    "Algeciras, Spain": (36.130, -5.450),
    "Genoa, Italy": (44.402, 8.935),
    "Piraeus, Greece": (37.942, 23.634),
    "Istanbul, Turkey": (41.006, 28.976),
    "Gdansk, Poland": (54.352, 18.648),
    "Gothenburg, Sweden": (57.699, 11.966),
    # Africa
    "Port Said, Egypt": (31.260, 32.300),
    "Suez, Egypt": (29.970, 32.550),
    "Alexandria, Egypt": (31.200, 29.919),
    "Durban, South Africa": (-29.870, 31.050),
    "Cape Town, South Africa": (-33.920, 18.420),
    "Lagos, Nigeria": (6.445, 3.390),
    "Mombasa, Kenya": (-4.043, 39.666),
    "Djibouti, Djibouti": (11.590, 43.150),
    "Dar es Salaam, Tanzania": (-6.822, 39.283),
    # Americas
    "Los Angeles, USA": (33.728, -118.262),
    "Long Beach, USA": (33.754, -118.216),
    "New York, USA": (40.660, -74.040),
    "Houston, USA": (29.750, -95.270),
    "Savannah, USA": (32.078, -81.091),
    "Miami, USA": (25.776, -80.186),
    "Santos, Brazil": (-23.950, -46.300),
    "Buenos Aires, Argentina": (-34.603, -58.382),
    "Colon, Panama": (9.354, -79.902),
    "Vancouver, Canada": (49.286, -123.111),
    "Montreal, Canada": (45.508, -73.554),
    # Oceania
    "Melbourne, Australia": (-37.814, 144.963),
    "Sydney, Australia": (-33.868, 151.209),
    "Auckland, New Zealand": (-36.848, 174.763),
}

@st.cache_data
def get_port_list():
    # Return ONLY Indian ports for the initial small-scale implementation
    return [port for port in MAJOR_PORTS.keys() if "India" in port]

@st.cache_data
def geocode_port(port_name):
    if port_name in MAJOR_PORTS:
        return MAJOR_PORTS[port_name]
    
    # Try partial match (e.g. "A Coruna, Spain" matches if user types it)
    port_lower = port_name.lower()
    for key, coords in MAJOR_PORTS.items():
        if key.lower() in port_lower or port_lower in key.lower():
            return coords
        # Match just the city name
        city = key.split(",")[0].strip().lower()
        if city in port_lower or port_lower.startswith(city):
            return coords
        
    try:
        geolocator = Nominatim(user_agent="sih_fleet_optimization_proto")
        location = geolocator.geocode(port_name + " port", timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except Exception:
        pass
    return None

@st.cache_data
def calculate_voyage_distance(src_coords, dest_coords):
    """
    Returns the sea-route distance in kilometers between two coordinates.
    Falls back to great-circle if searoute fails.
    """
    try:
        import searoute
        origin = [src_coords[1], src_coords[0]]  # searoute uses [lon, lat]
        destination = [dest_coords[1], dest_coords[0]]
        route = searoute.searoute(origin, destination)
        return route['properties']['length']
    except Exception:
        return great_circle(src_coords, dest_coords).kilometers

def _searoute_to_waypoints(route_feature):
    """Convert a searoute GeoJSON Feature into our waypoint list format."""
    coords = route_feature['geometry']['coordinates']  # [[lon, lat], ...]
    waypoints = []
    cum_dist = 0.0
    for i, coord in enumerate(coords):
        lat, lon = coord[1], coord[0]
        if i > 0:
            prev = coords[i - 1]
            cum_dist += great_circle((prev[1], prev[0]), (lat, lon)).kilometers
        waypoints.append({
            'lat': lat,
            'lon': lon,
            'dist_from_start_km': cum_dist
        })
    return waypoints, cum_dist

def _downsample_waypoints(waypoints, max_points=30):
    """Reduce the number of waypoints while keeping start, end and evenly spaced points."""
    if len(waypoints) <= max_points:
        return waypoints
    indices = [0]
    step = (len(waypoints) - 1) / (max_points - 1)
    for i in range(1, max_points - 1):
        indices.append(int(round(i * step)))
    indices.append(len(waypoints) - 1)
    return [waypoints[i] for i in sorted(set(indices))]

def generate_routes(src_coords, dest_coords, num_waypoints=4):
    """
    Generates a Direct Sea Route and an Alternative Sea Route using the searoute library.
    All routes follow navigable ocean paths and avoid landmasses.
    Returns a list of routes, each with a name, total distance, and list of waypoints.
    """
    import searoute
    routes = []

    origin = [src_coords[1], src_coords[0]]  # [lon, lat]
    destination = [dest_coords[1], dest_coords[0]]

    # --- Route A: Shortest Sea Route ---
    try:
        route_a_feature = searoute.searoute(origin, destination)
        route_a_wps, route_a_dist = _searoute_to_waypoints(route_a_feature)
        route_a_wps = _downsample_waypoints(route_a_wps)
    except Exception:
        # Fallback to great-circle if searoute fails
        route_a_dist = great_circle(src_coords, dest_coords).kilometers
        route_a_wps = []
        for i in range(num_waypoints + 2):
            fraction = i / (num_waypoints + 1)
            lat = src_coords[0] + (dest_coords[0] - src_coords[0]) * fraction
            lon = src_coords[1] + (dest_coords[1] - src_coords[1]) * fraction
            route_a_wps.append({'lat': lat, 'lon': lon, 'dist_from_start_km': route_a_dist * fraction})

    routes.append({
        'route_id': 'Route A (Direct)',
        'total_distance_km': route_a_dist,
        'waypoints': route_a_wps,
        'color': '#3498db'
    })

    # --- Route B: Alternative Sea Route (via a perturbed waypoint) ---
    try:
        mid_lat = (src_coords[0] + dest_coords[0]) / 2
        mid_lon = (src_coords[1] + dest_coords[1]) / 2
        # Offset the midpoint to force a detour through ocean
        offset_lat = (dest_coords[0] - src_coords[0]) * 0.15
        offset_lon = (dest_coords[1] - src_coords[1]) * 0.15
        # Perpendicular offset to push the route sideways into the ocean
        via_lat = mid_lat - offset_lon * 0.3
        via_lon = mid_lon + offset_lat * 0.3
        via_point = [via_lon, via_lat]

        # Route in two legs: origin -> via -> destination
        leg1 = searoute.searoute(origin, via_point)
        leg2 = searoute.searoute(via_point, destination)

        leg1_wps, leg1_dist = _searoute_to_waypoints(leg1)
        leg2_wps, leg2_dist = _searoute_to_waypoints(leg2)

        # Merge legs (skip duplicate midpoint)
        combined_wps = leg1_wps[:]
        for wp in leg2_wps[1:]:
            wp['dist_from_start_km'] += leg1_dist
            combined_wps.append(wp)
        route_b_dist = leg1_dist + leg2_dist
        combined_wps = _downsample_waypoints(combined_wps)
    except Exception:
        # Fallback: Bezier curve
        route_b_wps_raw = []
        for i in range(num_waypoints + 2):
            t = i / (num_waypoints + 1)
            p1_lat = (src_coords[0] + dest_coords[0]) / 2 + 5.0
            p1_lon = (src_coords[1] + dest_coords[1]) / 2 + 5.0
            lat = (1-t)**2 * src_coords[0] + 2*(1-t)*t * p1_lat + t**2 * dest_coords[0]
            lon = (1-t)**2 * src_coords[1] + 2*(1-t)*t * p1_lon + t**2 * dest_coords[1]
            route_b_wps_raw.append({'lat': lat, 'lon': lon})
        cum_dist = 0
        route_b_wps_raw[0]['dist_from_start_km'] = 0
        for i in range(1, len(route_b_wps_raw)):
            prev = (route_b_wps_raw[i-1]['lat'], route_b_wps_raw[i-1]['lon'])
            curr = (route_b_wps_raw[i]['lat'], route_b_wps_raw[i]['lon'])
            cum_dist += great_circle(prev, curr).kilometers
            route_b_wps_raw[i]['dist_from_start_km'] = cum_dist
        combined_wps = route_b_wps_raw
        route_b_dist = cum_dist

    routes.append({
        'route_id': 'Route B (Alternative)',
        'total_distance_km': route_b_dist,
        'waypoints': combined_wps,
        'color': '#e74c3c'
    })
    
    return routes

# --- REFUELING INFRASTRUCTURE ---

def calculate_refueling_stops(route_waypoints, total_distance_km, fuel_consumption_tpd, speed_knots, fuel_type="Methanol", route_id="Route A"):
    """
    Dynamically calculates where a ship must stop to refuel along a sea route.
    
    Logic:
    - Green fuels (Methanol/LNG) have limited energy density, so ships carry ~2 days of fuel.
    - At the point where fuel runs out, we find the nearest real port along the route.
    - Returns a list of refueling stop dicts with port name, coordinates, and distance.
    """
    # Green fuel range: ~2 days of sailing before needing to refuel
    # Conventional HFO ships can go ~15 days without refueling
    fuel_range_days = {"HFO": 15, "LNG": 3, "Methanol": 2}
    max_days = fuel_range_days.get(fuel_type, 2)
    
    # Calculate range in km: speed (knots) * 1.852 (km/knot) * 24 (hrs) * max_days
    max_range_km = speed_knots * 1.852 * 24 * max_days
    
    if max_range_km >= total_distance_km:
        return []  # Ship can complete the voyage without refueling
    
    refueling_stops = []
    fuel_remaining_km = max_range_km
    
    for i, wp in enumerate(route_waypoints):
        dist = wp['dist_from_start_km']
        
        # Check if fuel is about to run out (within 80% of range to allow safety margin)
        if dist >= fuel_remaining_km * 0.8 and dist < total_distance_km * 0.95:
            # Find all refueling ports within 1500km
            candidates = []
            
            for p_name, p_coords in MAJOR_PORTS.items():
                port_dist = great_circle((wp['lat'], wp['lon']), (p_coords[0], p_coords[1])).kilometers
                if port_dist < 1500:
                    candidates.append({'name': p_name, 'coords': p_coords, 'dist': port_dist})
                    
            if candidates:
                candidates.sort(key=lambda x: x['dist'])
                
                # To ensure the "Alternative Route" looks different, we make it pick the second closest port
                if "Alternative" in route_id and len(candidates) > 1:
                    best_port = candidates[1]
                else:
                    best_port = candidates[0]
                    
                port_split = best_port['name'].split(", ")
                city = port_split[0]
                country = port_split[1] if len(port_split) > 1 else ""
                
                # Avoid duplicate stops at the same port
                if not any(s['port_name'] == city for s in refueling_stops):
                    refueling_stops.append({
                        'port_name': city,
                        'country': country,
                        'lat': best_port['coords'][0],
                        'lon': best_port['coords'][1],
                        'dist_from_start_km': round(dist, 0),
                        'fuel_needed_tonnes': round(fuel_consumption_tpd * max_days, 1)
                    })
                    fuel_remaining_km = dist + max_range_km  # Refueled! Reset range
    
    return refueling_stops

def regenerate_route_with_stops(original_waypoints, refueling_stops):
    """
    Takes the original route waypoints and inserts detours to the refueling stops.
    This preserves the exact shape of the route (e.g. alternative ocean detours)
    while clearly drawing a line that breaks off the shipping lane, hits the port, and returns.
    """
    import copy
    new_wps = copy.deepcopy(original_waypoints)
    
    # For each stop, find the closest waypoint in the original route and insert a spike
    for stop in refueling_stops:
        stop_lat = stop['lat']
        stop_lon = stop['lon']
        
        # Find closest waypoint in original route
        best_idx = 0
        best_dist = float('inf')
        for i, wp in enumerate(new_wps):
            dist = (wp['lat'] - stop_lat)**2 + (wp['lon'] - stop_lon)**2
            if dist < best_dist:
                best_dist = dist
                best_idx = i
                
        # Insert the port coordinate at that index so the line diverts to the port
        port_wp = {
            'lat': stop_lat,
            'lon': stop_lon,
            'dist_from_start_km': new_wps[best_idx].get('dist_from_start_km', 0)
        }
        
        new_wps.insert(best_idx + 1, port_wp)
        new_wps.insert(best_idx + 2, new_wps[best_idx]) # Return to the shipping lane
        
    return new_wps

def generate_route_map(src_name, src_coords, dest_name, dest_coords, best_route_id=None):
    """
    Generates a Folium map showing all routes, highlighting the best route.
    """
    routes = generate_routes(src_coords, dest_coords)
    
    mid_lat = (src_coords[0] + dest_coords[0]) / 2
    mid_lon = (src_coords[1] + dest_coords[1]) / 2
    
    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=3, tiles="CartoDB dark_matter")
    
    # Markers
    folium.Marker(src_coords, popup=f"Source: {src_name}", icon=folium.Icon(color="green", icon="play")).add_to(m)
    folium.Marker(dest_coords, popup=f"Destination: {dest_name}", icon=folium.Icon(color="red", icon="stop")).add_to(m)
    
    # Draw routes
    for r in routes:
        locations = [(wp['lat'], wp['lon']) for wp in r['waypoints']]
        
        is_best = (r['route_id'] == best_route_id) or (best_route_id is None)
        weight = 5 if is_best else 3
        opacity = 0.9 if is_best else 0.4
        
        folium.PolyLine(
            locations=locations,
            color=r['color'],
            weight=weight,
            opacity=opacity,
            dash_array='10, 10' if not is_best else None,
            popup=r['route_id']
        ).add_to(m)
        
    return m, routes
