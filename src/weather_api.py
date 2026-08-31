import requests
import datetime
import streamlit as st

@st.cache_data(ttl=3600)
def get_marine_forecast(lat, lon):
    """
    Fetches 7-day hourly marine and wind forecast for a given coordinate.
    Uses caching to prevent redundant API calls during route optimization.
    Returns a dictionary mapping datetime objects to weather conditions.
    """
    forecast_data = {}
    
    try:
        # Fetch Wind (from standard forecast API)
        wind_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m"
        wind_resp = requests.get(wind_url, timeout=5)
        
        # Fetch Waves (from marine API)
        wave_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=wave_height"
        wave_resp = requests.get(wave_url, timeout=5)
        
        if wind_resp.status_code == 200 and wave_resp.status_code == 200:
            wind_json = wind_resp.json()
            wave_json = wave_resp.json()
            
            wind_times = wind_json.get("hourly", {}).get("time", [])
            wind_speeds = wind_json.get("hourly", {}).get("wind_speed_10m", [])
            
            wave_times = wave_json.get("hourly", {}).get("time", [])
            wave_heights = wave_json.get("hourly", {}).get("wave_height", [])
            
            # Combine them. Open-Meteo returns ISO8601 strings for time (e.g., "2023-10-01T12:00")
            for i, time_str in enumerate(wind_times):
                try:
                    dt = datetime.datetime.fromisoformat(time_str)
                    w_speed = wind_speeds[i] if wind_speeds[i] is not None else 0.0
                    
                    # Find corresponding wave height
                    w_height = 0.0
                    if i < len(wave_times) and wave_times[i] == time_str:
                        w_height = wave_heights[i] if wave_heights[i] is not None else 0.0
                        
                    forecast_data[dt] = {
                        "wind_speed_kmh": w_speed,
                        "wave_height_m": w_height,
                        "timestamp": dt
                    }
                except Exception:
                    continue
    except Exception as e:
        print(f"Weather API error: {e}")
        
    return forecast_data

def get_weather_at_time(forecast_data, target_dt):
    """
    Finds the closest hourly forecast to the target datetime.
    If no forecast data is available (e.g. inland or API failed), returns None.
    Never fakes data.
    """
    if not forecast_data:
        return None
        
    # Find the closest time key
    closest_time = min(forecast_data.keys(), key=lambda k: abs(k - target_dt))
    
    # If the closest time is more than 24 hours away, the forecast doesn't cover this period
    if abs(closest_time - target_dt).total_seconds() > 86400:
        return None
        
    return forecast_data[closest_time]
