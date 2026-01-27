import os
import time
import requests
import urllib.parse
import threading
from flask import Flask, jsonify, render_template
from collections import Counter

app = Flask(__name__, static_folder='static', template_folder='templates')

# --- CONFIGURATION ---
API_KEY = os.environ.get("HENRIK_KEY") 
REGION = "eu"

ROSTER = [
    {"name": "Jilicuerda", "tag": "1734", "role": "Initiator"},
    {"name": "CriskXK", "tag": "PRESA", "role": "Duelist"},
    {"name": "Magic Tostada", "tag": "MCY", "role": "IGL"},
    {"name": "Cleezzy", "tag": "Reina", "role": "Smoker"},
    {"name": "mi abuela mola", "tag": "2981", "role": "Sentinel"}
]

# --- GLOBAL STORAGE ---
# We store the data here so the website can read it instantly
DATABASE = {
    "last_updated": 0,
    "roster_data": []
}

def get_headers():
    return {"Authorization": API_KEY}

def fetch_player_data(player):
    """Fetches DEEP history for a single player to find true stats."""
    safe_name = urllib.parse.quote(player['name'])
    safe_tag = urllib.parse.quote(player['tag'])
    
    # Default Defaults
    stats = player.copy()
    stats['rank'] = "Unranked"
    stats['main_agent'] = "Unknown"
    
    try:
        # 1. GET RANK (MMR Endpoint - Very fast)
        mmr_url = f"https://api.henrikdev.xyz/valorant/v2/mmr/{REGION}/{safe_name}/{safe_tag}"
        r_mmr = requests.get(mmr_url, headers=get_headers())
        
        if r_mmr.status_code == 200:
            data = r_mmr.json().get('data', {}).get('current_data', {})
            stats['rank'] = data.get('currenttierpatched', 'Unranked')

        # 2. GET DEEP HISTORY (Lifetime Endpoint - The "Hoarder")
        # We ask for the last 85 Competitive games. 
        # This covers months of play, filtering out DM/Customs.
        history_url = f"https://api.henrikdev.xyz/valorant/v1/lifetime/matches/{REGION}/{safe_name}/{safe_tag}?mode=competitive&size=85"
        r_hist = requests.get(history_url, headers=get_headers())
        
        if r_hist.status_code == 200:
            matches = r_hist.json().get('data', [])
            agents_played = []
            
            # Loop through all 85 matches
            for match in matches:
                # The lifetime API puts agent name in match['meta']['character']['name']
                if 'meta' in match and 'character' in match['meta']:
                    agent = match['meta']['character']['name']
                    agents_played.append(agent)
            
            # Calculate the winner
            if agents_played:
                most_common = Counter(agents_played).most_common(1)
                stats['main_agent'] = most_common[0][0] # e.g., "Astra"

        print(f"✅ Analyzed {len(agents_played)} games for {player['name']}: Main is {stats['main_agent']}")
        return stats

    except Exception as e:
        print(f"❌ Error for {player['name']}: {e}")
        return stats

def background_updater():
    """Runs in the background to keep data fresh."""
    print("--- 🔄 BACKGROUND UPDATE STARTED ---")
    
    new_roster_data = []
    for player in ROSTER:
        data = fetch_player_data(player)
        new_roster_data.append(data)
        time.sleep(2) # Sleep 2s between players to be nice to API
        
    # Update the global database
    DATABASE["roster_data"] = new_roster_data
    DATABASE["last_updated"] = time.time()
    print("--- ✨ UPDATE COMPLETE ---")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/team-history')
def get_history():
    # If the database is empty (first time running), trigger an update
    if not DATABASE["roster_data"]:
        background_updater()
    
    # Check if data is older than 30 minutes (1800 seconds)
    elif (time.time() - DATABASE["last_updated"]) > 1800:
        # In a real app we'd use a thread, but for now we update before sending
        # to ensure they get fresh data.
        background_updater()

    return jsonify({
        "last_updated": DATABASE["last_updated"],
        "roster": DATABASE["roster_data"]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
