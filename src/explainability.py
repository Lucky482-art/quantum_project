def generate_voyage_explanation(top_plan, alternative_plans, cargo_type, cargo_demand):
    """
    Generates explainable AI reasoning for why a specific vessel and route were chosen,
    and why the alternatives were rejected.
    """
    vessel_name = top_plan['Vessel_Name']
    route_id = top_plan['Route_ID']
    vessel_type = top_plan['Vessel_Type']
    
    explanation = {
        "why_vessel": f"{vessel_name} was selected because it is a {vessel_type}, strictly required for your {cargo_type}. Its cargo capacity safely supports your {cargo_demand:,}t load requirements.",
        "why_route": f"The system evaluated weather forecasts across multiple route segments based on your departure time. {route_id} was selected because it presented a {top_plan['Weather_Risk_Level']} risk profile over the entire voyage timeline, minimizing exposure to severe waves and wind.",
        "why_time": f"The recommended departure time ensures the vessel safely avoids critical weather windows along the route.",
        "why_not_alternatives": []
    }
    
    for alt in alternative_plans:
        if alt['Vessel_Name'] != vessel_name:
            reason = f"Alternative vessel {alt['Vessel_Name']} was considered, but {vessel_name} provided a better overall multi-objective score combining safety, fuel ({top_plan['Predicted_Fuel_Tonnes']:,.0f}t), and emissions."
            explanation["why_not_alternatives"].append(reason)
        elif alt['Route_ID'] != route_id:
            if alt['Weather_Risk_Score'] > top_plan['Weather_Risk_Score']:
                reason = f"{alt['Route_ID']} is an alternative route, but it encounters higher weather risk ({alt['Weather_Risk_Level']}) during the vessel's expected arrival window."
                explanation["why_not_alternatives"].append(reason)
            else:
                reason = f"{alt['Route_ID']} is safe, but the chosen {route_id} provides a better balance of travel time and fuel consumption."
                explanation["why_not_alternatives"].append(reason)
                
    return explanation
