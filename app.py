import os
import time
import requests
import urllib.parse
from flask import Flask, jsonify, render_template
from collections import Counter

app = Flask(__name__, static_folder='static', template_folder='templates')

# --- CONFIGURATION ---
API_KEY = os.environ.get("HENRIK_KEY") 
REGION = "eu" # Change to 'eu', 'ap', or 'latam' if needed

# YOUR ROSTER
ROSTER = [
    {"name": "Jilicuerda", "tag": "1734", "role": "Initiator"},
    {"name": "CriskXK", "tag": "PRESA", "role": "Duelist"},
    {"name": "Magic Tostada", "tag": "MCY", "role": "IGL"},
    {"name": "Cleezzy", "tag": "Reina", "role": "Smoker"},
    {"name": "mi abuela mola", "tag": "2981", "role": "Sentinel"}
]

cache = {
    "last_updated": 0,
    "team_matches": [],
    "roster_stats": [] 
}
CACHE_DURATION = 900  # 15 Minutes

def update_data():
    """Fetches data for all players, calculates stats, and finds team games."""
    print("--- STARTING UPDATE ---")
    all_team_matches = []
    processed_match_ids = set()
    updated_roster = []

    for player in ROSTER:
        # 1. Prepare the player object with defaults
        player_stats = player.copy()
        player_stats['rank'] = "Unranked"
        player_stats['main_agent'] = "Unknown"
        
        # 2. Fetch their matches
        safe_name = urllib.parse.quote(player['name'])
        safe_tag = urllib.parse.quote(player['tag'])
        url = f"https://api.henrikdev.xyz/valorant/v3/matches/{REGION}/{safe_name}/{safe_tag}"
        headers = {"Authorization": API_KEY}
        
        try:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                matches = data.get('data', [])
                
                if matches:
                    # --- CALCULATE STATS (Based on last 5 games) ---
                    # Get most recent Rank
                    last_match = matches[0]
                    for p in last_match['players']['all_players']:
                        if p['name'].lower() == player['name'].lower() and p['tag'].lower() == player['tag'].lower():
                            player_stats['rank'] = p['currenttier_patched']
                            break
                    
                    # Get Most Played Agent
                    agents_played = []
                    for m in matches:
                        for p in m['players']['all_players']:
                            if p['name'].lower() == player['name'].lower() and p['tag'].lower() == player['tag'].lower():
                                agents_played.append(p['character'])
                    
                    if agents_played:
                        most_common = Counter(agents_played).most_common(1)
                        player_stats['main_agent'] = most_common[0][0]

                    # --- CHECK FOR TEAM GAMES ---
                    for match in matches:
                        match_id = match['metadata']['matchid']
                        if match_id in processed_match_ids:
                            continue

                        # Check if 3+ roster members were in this match
                        all_player_names = [p['name'].lower() for p in match['players']['all_players']]
                        teammates_count = 0
                        for member in ROSTER:
                            if member['name'].lower() in all_player_names:
                                teammates_count += 1
                        
                        if teammates_count >= 3:
                            all_team_matches.append(match)
                            processed_match_ids.add(match_id)

            else:
                print(f"Failed to fetch {player['name']}: Status {r.status_code}")
                
            time.sleep(1) # Respect Rate Limits

        except Exception as e:
            print(f"Error processing {player['name']}: {e}")

        updated_roster.append(player_stats)

    return updated_roster, all_team_matches

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/team-history')
def get_history():
    current_time = time.time()
    
    # Refresh data if cache is old
    if current_time - cache["last_updated"] > CACHE_DURATION:
        roster_data, matches_data = update_data()
        if roster_data:
            cache["roster_stats"] = roster_data
            cache["team_matches"] = matches_data
            cache["last_updated"] = current_time
            
    return jsonify({
        "last_updated": cache["last_updated"],
        "roster": cache["roster_stats"], # This now contains the calculated Rank/Agent
        "matches": cache["team_matches"]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

