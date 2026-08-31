def get_base_wave_risk(wave_height):
    if wave_height < 2.0:
        return 0, 'LOW'
    elif wave_height < 3.0:
        return 30, 'MODERATE'
    elif wave_height < 4.0:
        return 70, 'HIGH'
    else:
        return 100, 'SEVERE'

def evaluate_segment_risk(vessel, weather_cond):
    """
    Evaluates risk for a single point in time/space based on MVP safety rules.
    """
    wave_h = weather_cond.get('wave_height_m', 0)
    wind_s = weather_cond.get('wind_speed_kmh', 0)
    
    v_type = vessel.get('Vessel_Type', '')
    v_length = float(vessel.get('length', 200))
    v_dwt = float(vessel.get('dwt', 50000))
    
    score, level = get_base_wave_risk(wave_h)
    warnings = []
    
    # Rule 1: Small vessels in high waves
    if wave_h > 3.0 and (v_length < 150 or v_dwt < 20000):
        score += 30
        warnings.append(f"Wave height {wave_h}m is hazardous for vessels under 150m/20k DWT.")
        
    # Rule 2: RoRo wind sensitivity
    if v_type == 'RoRo ships' and wind_s > 40.0:
        score += 40
        warnings.append(f"Wind speed {wind_s}km/h exceeds safe threshold for high-profile RoRo ships.")
        
    # Cap score
    score = min(score, 100)
    
    # Recalculate level
    if score >= 85:
        level = 'SEVERE'
    elif score >= 60:
        level = 'HIGH'
    elif score >= 30:
        level = 'MODERATE'
    else:
        level = 'LOW'
        
    return {
        'score': score,
        'level': level,
        'warnings': warnings
    }

def evaluate_vessel_weather_risk(vessel, route_weather_timeline):
    """
    Evaluates weather risk for a vessel across the ENTIRE voyage timeline.
    route_weather_timeline: list of dicts with weather conditions per segment.
    """
    segment_details = []
    max_score = 0
    all_warnings = []
    
    for segment in route_weather_timeline:
        risk = evaluate_segment_risk(vessel, segment)
        
        # Keep track of worst segment
        if risk['score'] > max_score:
            max_score = risk['score']
            
        for w in risk['warnings']:
            if w not in all_warnings:
                all_warnings.append(w)
                
        segment_details.append({
            'segment_id': segment.get('segment_id', 0),
            'timestamp': segment.get('timestamp'),
            'wave_height_m': segment.get('wave_height_m', 0),
            'wind_speed_kmh': segment.get('wind_speed_kmh', 0),
            'risk_level': risk['level'],
            'risk_score': risk['score']
        })
        
    if max_score >= 85:
        overall_level = 'SEVERE'
    elif max_score >= 60:
        overall_level = 'HIGH'
    elif max_score >= 30:
        overall_level = 'MODERATE'
    else:
        overall_level = 'LOW'
        
    return {
        'overall_risk_score': max_score,
        'overall_risk_level': overall_level,
        'segment_details': segment_details,
        'warnings': all_warnings
    }
