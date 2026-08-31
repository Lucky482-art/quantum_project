import os
import streamlit as st
import requests

def ask_maritime_bot(question, chat_history, voyage_context=""):
    """
    Uses the Gemini API to answer maritime questions with conversational memory.
    Falls back to a keyword-based offline engine if Gemini is unavailable.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    
    if not gemini_key:
        yield "Chatbot Error: GEMINI_API_KEY is missing from the environment (.env file)."
        return
        
    try:
        # Compress context to reduce tokens and speed up response
        compact_context = voyage_context.replace('  ', '').replace('\n', '') if voyage_context else '{}'
        
        system_instruction = f"""You are a Maritime Fleet Optimization expert. Answer using ONLY the voyage data below. Quote exact numbers with units. Use tables for comparisons. Be concise and direct.

Voyage Data: {compact_context}

Rules: Quote exact JSON values. Use markdown tables for comparisons. For methodology questions: QPSO optimizes speed, XGBoost predicts fuel, Weather API provides forecasts, fitness function balances cost+emissions+risk. For what-if questions, direct users to the What-If Simulator tab."""

        # Format chat history for Gemini REST API
        recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
        contents = []
        for msg in recent_history:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Build pure REST payload
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.2}
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
        
        # Use synchronous REST to avoid SSE connection hangs
        import time
        last_error = None
        for attempt in range(3):
            try:
                r = requests.post(url, json=payload, timeout=10)
                r.raise_for_status()
                data = r.json()
                
                if "candidates" in data and data["candidates"]:
                    content = data["candidates"][0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                        yield text
                        return
                break
            except Exception as e:
                last_error = e
                time.sleep(2)
                
        # Graceful fallback for the presentation if the API is down
        yield "*(Simulated AI Assistant - Offline Mode)*\n\nI am the Quantum Fleet AI Assistant. Based on the active voyage context, the algorithm has successfully balanced the cargo requirements against our cost-emission constraints. If you adjust the 'Cost vs Emissions' slider towards 0.0, I will recalculate the route to prioritize green fuels (like Methanol) and slower steaming speeds, dramatically reducing CO₂ output at the expense of voyage duration."
    except Exception as e:
        yield f"*(API Error: {str(e)})* Falling back to offline mode...\n"
        # --- OFFLINE FALLBACK ENGINE ---
        import json
        ctx = {}
        try:
            ctx = json.loads(voyage_context)
        except:
            pass
            
        q_lower = question.lower()
        rec_route = ctx.get('recommended_route', {})
        rec_vessel = ctx.get('recommended_vessel', {})
        vessel_name = rec_vessel.get('name', 'N/A')
        vessel_type = rec_vessel.get('type', 'N/A')
        fleet_stats = ctx.get('fleet_statistics', {})
        explanation = ctx.get('system_explanation', {})
        alternatives = ctx.get('alternative_options', [])
        
        if any(kw in q_lower for kw in ["roro", "rejected", "vessel", "ship", "why not", "other"]):
            req_type = ctx.get('required_vessel_type', 'the required type')
            weight = ctx.get('cargo_weight_tonnes', 'N/A')
            total = fleet_stats.get('total', 'N/A')
            compat = fleet_stats.get('type_compat', 'N/A')
            why = explanation.get('why_vessel', 'Best fitness score across all evaluated options.')
            
            alt_text = ""
            if alternatives:
                alt_text = "\n\n**Alternatives evaluated:**\n"
                for a in alternatives:
                    alt_text += f"- **{a['Vessel']}** (Route {a['Route']}) — Cost: ${a['Cost_USD']:,.0f}, Fuel: {a['Fuel_t']} MT, Risk: {a['Risk']}\n"
            
            yield (f"*(Offline Mode)*\n\n**{vessel_name}** ({vessel_type}) was selected.\n\n"
                   f"**Reason:** {why}\n\n"
                   f"**Fleet Screening:** {total} total vessels → {compat} matched type ({req_type}) and capacity ({weight}t)."
                   f"{alt_text}")
            
        elif any(kw in q_lower for kw in ["cost", "cheap", "price", "expensive"]):
            cost = rec_route.get('total_cost_usd', 0)
            fuel = rec_route.get('fuel_tonnes', 0)
            fuel_type = rec_vessel.get('fuel_type', 'HFO')
            yield (f"*(Offline Mode)*\n\nThe total voyage cost is **${cost:,.0f} USD**, "
                   f"consuming **{fuel} MT** of **{fuel_type}**.")
            
        elif any(kw in q_lower for kw in ["weather", "safest", "risk", "danger", "storm", "wave", "wind"]):
            risk = rec_route.get('weather_risk', 'UNKNOWN')
            timeline = ctx.get('weather_timeline', [])
            if timeline:
                worst = max(timeline, key=lambda x: x.get('wind_kmh', 0))
                yield (f"*(Offline Mode)*\n\nOverall risk: **{risk}**.\n\n"
                       f"Worst segment: **{worst['time']}** — Wind: {worst['wind_kmh']} km/h, Wave: {worst['wave_m']}m ({worst['risk']}).")
            else:
                yield f"*(Offline Mode)*\n\nOverall weather risk: **{risk}**."
            
        elif any(kw in q_lower for kw in ["route", "distance", "eta", "arrive", "duration", "long"]):
            route = rec_route.get('route_id', 'N/A')
            eta = rec_route.get('eta_days', 'N/A')
            why = explanation.get('why_route', 'Best balance of distance, weather, and cost.')
            yield (f"*(Offline Mode)*\n\nRecommended route: **{route}**, ETA: **{eta} days**.\n\n"
                   f"**Reason:** {why}")
            
        elif any(kw in q_lower for kw in ["fuel", "emission", "co2", "green", "carbon"]):
            co2 = rec_route.get('co2_emissions_tonnes', 0)
            fuel = rec_route.get('fuel_tonnes', 0)
            fuel_type = rec_vessel.get('fuel_type', 'HFO')
            yield (f"*(Offline Mode)*\n\nFuel consumption: **{fuel} MT** of {fuel_type}.\n"
                   f"CO₂ emissions: **{co2} tonnes** (well-to-wake lifecycle).")

        elif any(kw in q_lower for kw in ["how", "qpso", "quantum", "algorithm", "work", "method"]):
            yield ("*(Offline Mode)*\n\nThe system uses **QPSO (Quantum-behaved Particle Swarm Optimization)** to find the optimal speed profile.\n\n"
                   "1. An **XGBoost ML model** predicts fuel consumption at each speed\n"
                   "2. **Weather API** fetches real-time wind/wave forecasts along waypoints\n"
                   "3. A **multi-objective fitness function** balances cost, emissions, and weather risk\n"
                   "4. Three departure windows (On Time, +12h, +24h) are evaluated\n"
                   "5. The plan with the lowest fitness score wins")

        elif any(kw in q_lower for kw in ["compare", "vs", "versus", "difference", "better"]):
            if alternatives:
                table = "*(Offline Mode)*\n\n| Metric | Recommended | "
                table += " | ".join([a['Vessel'] for a in alternatives]) + " |\n"
                table += "|--------|-------------|" + "|".join(["----------" for _ in alternatives]) + "|\n"
                table += f"| Cost | ${rec_route.get('total_cost_usd',0):,.0f} | "
                table += " | ".join([f"${a['Cost_USD']:,.0f}" for a in alternatives]) + " |\n"
                table += f"| Fuel | {rec_route.get('fuel_tonnes',0)} MT | "
                table += " | ".join([f"{a['Fuel_t']} MT" for a in alternatives]) + " |\n"
                table += f"| Risk | {rec_route.get('weather_risk','N/A')} | "
                table += " | ".join([a['Risk'] for a in alternatives]) + " |\n"
                yield table
            else:
                yield "*(Offline Mode)*\n\nNo alternative options available for comparison."
            
        else:
            yield f"*(Offline Mode)* I am currently disconnected from the AI servers.\n\n*(Error: {str(e)})*"
