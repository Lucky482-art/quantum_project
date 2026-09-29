# Standard emission factors (tonnes of CO2 per tonne of fuel)
# Well-to-wake lifecycle emissions estimates
EMISSION_FACTORS = {
    'HFO': 3.114,       # Heavy Fuel Oil
    'LNG': 2.75,        # Liquefied Natural Gas (Well-to-wake approx)
    'Methanol': 1.4,    # Assuming a mix of grey/green methanol for the prototype
}

import requests
import time

# Base fallback prices in case the API is unreachable
FUEL_PRICES = {
    'HFO': 600.0,
    'LNG': 850.0,
    'Methanol': 750.0
}

# Cache to avoid hitting the API rate limits on every single calculation
_price_cache = {}
_cache_time = 0

def get_live_fuel_price(fuel_type):
    """
    Fetches real-time marine fuel prices from OilPriceAPI.
    Uses an in-memory cache valid for 1 hour to prevent rate limiting.
    """
    global _price_cache, _cache_time
    
    # Refresh cache every hour
    if time.time() - _cache_time > 3600 or not _price_cache:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("OIL_PRICE_API_KEY")
        headers = {"Authorization": f"Token {api_key}"}
        
        try:
            # Fetch HFO 380 (Metric Ton)
            res_hfo = requests.get('https://api.oilpriceapi.com/v1/prices/latest?by_code=HFO_380_USD', headers=headers, timeout=5)
            if res_hfo.status_code == 200:
                _price_cache['HFO'] = float(res_hfo.json()['data']['price'])
                
            # Fetch Methanol (Metric Ton)
            res_meth = requests.get('https://api.oilpriceapi.com/v1/prices/latest?by_code=METHANOL_USD', headers=headers, timeout=5)
            if res_meth.status_code == 200:
                _price_cache['Methanol'] = float(res_meth.json()['data']['price'])
                
            # Fetch LNG (Returns in MMBtu, so we multiply by 52 to convert to Metric Tonnes)
            res_lng = requests.get('https://api.oilpriceapi.com/v1/prices/latest?by_code=LNG_USD', headers=headers, timeout=5)
            if res_lng.status_code == 200:
                mmbtu_price = float(res_lng.json()['data']['price'])
                _price_cache['LNG'] = mmbtu_price * 52.0  # Approx 52 MMBtu per Metric Ton of LNG
                
            _cache_time = time.time()
        except Exception as e:
            pass # Silently fallback to base prices if API fails
            
    # Return live price if available, else fallback
    return _price_cache.get(fuel_type, FUEL_PRICES.get(fuel_type, 600.0))

def calculate_emissions(fuel_amount, fuel_type):
    """
    Calculate the well-to-wake CO2 emissions for a given amount of fuel.
    """
    factor = EMISSION_FACTORS.get(fuel_type, 3.114) # Default to HFO if unknown
    return fuel_amount * factor

def calculate_fuel_cost(fuel_amount, fuel_type):
    """
    Calculate the total cost for a given amount of fuel using simulated live API prices.
    """
    live_price = get_live_fuel_price(fuel_type)
    return fuel_amount * live_price
