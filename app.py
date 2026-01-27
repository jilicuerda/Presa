import os
import time
import requests
import urllib.parse
from flask import Flask, jsonify, render_template

app = Flask(__name__, static_folder='static', template_folder='templates')

API_KEY = os.environ.get("HENRIK_KEY") 
REGION = "eu"

# WE DEFINE THE AGENT HERE (Fixed Agent)
ROSTER = [
    {"name": "Jilicuerda", "tag": "1734", "role": "Initiator", "fixed_agent": "Astra"},
    {"name": "CriskXK", "tag": "PRESA", "role": "Duelist", "fixed_agent": "Jett"},
    {"name": "Magic Tostada", "tag": "MCY", "role": "IGL", "fixed_agent": "Kayo"}, 
    {"name": "Cleezzy", "tag": "Reina", "role": "Smoker", "fixed_agent": "Viper"},
    {"name": "mi abuela mola", "tag": "2981", "role": "Sentinel", "fixed_agent": "Sova"}
]

# Simple cache to store the Ranks
cache = {
    "last_updated": 0,
    "roster_data": []
}

def update_data():
    print("--- 🔄 UPDATING RANKS ---")
    updated_roster = []

    for player in ROSTER:
        # Start with the data we already know (Role + Fixed Agent)
        player_stats = player.copy()
        player_stats['main_agent'] = player['fixed_agent']
        player_stats['rank'] = "Unranked" # Default

        # Only ask API for the Rank
        try:
            safe_name = urllib.parse.quote(player['name'])
            safe_tag = urllib.parse.quote(player['tag'])
            
            # MMR V2 Endpoint (Fastest for Rank)
            url = f"https://api.henrikdev.xyz/valorant/v2/mmr/{REGION}/{safe_name}/{safe_tag}"
            headers = {"Authorization": API_KEY}
            
            r = requests.get(url, headers=headers)
            
            if r.status_code == 200:
                data = r.json().get('data', {}).get('current_data', {})
                rank = data.get('currenttierpatched')
                if rank:
                    player_stats['rank'] = rank
            
            print(f"✅ {player['name']}: {player_stats['rank']}")
            time.sleep(1) # Small sleep to be safe

        except Exception as e:
            print(f"❌ Error {player['name']}: {e}")
        
        updated_roster.append(player_stats)

    return updated_roster

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/team-history')
def get_history():
    current_time = time.time()
    
    # Update every 30 minutes
    if not cache["roster_data"] or (current_time - cache["last_updated"] > 1800):
        new_data = update_data()
        if new_data:
            cache["roster_data"] = new_data
            cache["last_updated"] = current_time
            
    return jsonify({
        "roster": cache["roster_data"]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
