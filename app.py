import os
import time
import requests
import urllib.parse # Added this to handle spaces in names (e.g. Magic Tostada)
from flask import Flask, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
API_KEY = os.environ.get("HENRIK_KEY") 
REGION = "na" # <--- IMPORTANT: Change this to 'eu' if you are in Europe!

# YOUR ACTUAL ROSTER
ROSTER = [
    {"name": "Jilicuerda", "tag": "1734", "role": "Initiator"},
    {"name": "CriskXK", "tag": "PRESA", "role": "Duelist"},
    {"name": "Magic Tostada", "tag": "MCY", "role": "IGL"},
    {"name": "Cleezzy", "tag": "Reina", "role": "Smoker"},
    {"name": "mi abuela mola", "tag": "2981", "role": "Sentinel"}
]

cache = {
    "last_updated": 0,
    "data": []
}
CACHE_DURATION = 900 

def fetch_team_matches():
    team_matches = []
    processed_ids = set()
    
    print("Refreshing data from Riot/Henrik...")
    
    for player in ROSTER:
        # We encode the name to handle spaces (e.g. "Magic Tostada" -> "Magic%20Tostada")
        safe_name = urllib.parse.quote(player['name'])
        safe_tag = urllib.parse.quote(player['tag'])
        
        url = f"https://api.henrikdev.xyz/valorant/v3/matches/{REGION}/{safe_name}/{safe_tag}"
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
                    
                    # We check against our roster list
                    for member in ROSTER:
                        if member['name'].lower() in all_players:
                            teammates_count += 1
                            
                    if teammates_count >= 3:
                        team_matches.append(match)
                        processed_ids.add(match_id)
            
            time.sleep(1) 
            
        except Exception as e:
            print(f"Error fetching {player['name']}: {e}")

    return team_matches

@app.route('/')
def home():
    # OLD: return "Valorant Team API is Running!"
    # NEW:
    return render_template('index.html')

@app.route('/api/team-history')
def get_history():
    current_time = time.time()
    
    if current_time - cache["last_updated"] > CACHE_DURATION:
        new_data = fetch_team_matches()
        if new_data: 
            cache["data"] = new_data
            cache["last_updated"] = current_time
            
    return jsonify({
        "last_updated": cache["last_updated"],
        "roster": ROSTER, # Sending the roster to the frontend helps display roles!
        "matches": cache["data"]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))

    app.run(host='0.0.0.0', port=port)

