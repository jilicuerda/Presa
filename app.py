import os
import time
import requests
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allows your frontend website to talk to this backend

# --- CONFIGURATION ---
# We will set the API KEY in Render later (Environment Variable)
API_KEY = os.environ.get("HENRIK_KEY") 
REGION = "na"  # Change to eu, ap, kr, etc.

# YOUR TEAM ROSTER
ROSTER = [
    {"name": "PlayerOne", "tag": "1234"},
    {"name": "PlayerTwo", "tag": "NA1"},
    {"name": "PlayerThree", "tag": "WIN"},
]

# IN-MEMORY CACHE (Simple storage so we don't spam the API)
cache = {
    "last_updated": 0,
    "data": []
}
CACHE_DURATION = 900  # Fetch new data every 15 minutes (900 seconds)

def fetch_team_matches():
    """Fetches matches where 3+ roster members played together."""
    team_matches = []
    processed_ids = set()
    
    print("Refreshing data from Riot/Henrik...")
    
    for player in ROSTER:
        url = f"https://api.henrikdev.xyz/valorant/v3/matches/{REGION}/{player['name']}/{player['tag']}"
        headers = {"Authorization": API_KEY}
        
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                matches = r.json().get('data', [])
                
                for match in matches:
                    match_id = match['metadata']['matchid']
                    if match_id in processed_ids:
                        continue
                        
                    # Check for 3+ teammates
                    all_players = [p['name'].lower() for p in match['players']['all_players']]
                    teammates_count = 0
                    for member in ROSTER:
                        if member['name'].lower() in all_players:
                            teammates_count += 1
                            
                    if teammates_count >= 3:
                        team_matches.append(match)
                        processed_ids.add(match_id)
            
            time.sleep(1) # Be nice to the API
            
        except Exception as e:
            print(f"Error fetching {player['name']}: {e}")

    return team_matches

@app.route('/')
def home():
    return "Valorant Team API is Running!"

@app.route('/api/team-history')
def get_history():
    current_time = time.time()
    
    # If cache is old, fetch new data
    if current_time - cache["last_updated"] > CACHE_DURATION:
        new_data = fetch_team_matches()
        if new_data: # Only update if we actually got data back
            cache["data"] = new_data
            cache["last_updated"] = current_time
            
    return jsonify({
        "last_updated": cache["last_updated"],
        "matches": cache["data"]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)