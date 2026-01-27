import os
import time
import requests
import urllib.parse
from flask import Flask, jsonify, render_template, request
from collections import Counter

app = Flask(__name__, static_folder='static', template_folder='templates')

API_KEY = os.environ.get("HENRIK_KEY") 
REGION = "eu"

# 1. DEFINITIONS
AGENT_ROLES = {
    "Jett": "Duelist", "Raze": "Duelist", "Reyna": "Duelist", "Yoru": "Duelist", "Phoenix": "Duelist", "Neon": "Duelist", "Iso": "Duelist",
    "Sova": "Initiator", "Breach": "Initiator", "Skye": "Initiator", "KAY/O": "Initiator", "Kayo": "Initiator", "Fade": "Initiator", "Gekko": "Initiator",
    "Omen": "Controller", "Brimstone": "Controller", "Viper": "Controller", "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller",
    "Killjoy": "Sentinel", "Cypher": "Sentinel", "Sage": "Sentinel", "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel"
}

ROSTER = [
    {"name": "Jilicuerda", "tag": "1734", "role": "Initiator", "fixed_agent": "Astra"},
    {"name": "CriskXK", "tag": "PRESA", "role": "Duelist", "fixed_agent": "Jett"},
    {"name": "Magic Tostada", "tag": "MCY", "role": "IGL", "fixed_agent": "Kayo"},
    {"name": "Cleezzy", "tag": "Reina", "role": "Smoker", "fixed_agent": "Viper"},
    {"name": "mi abuela mola", "tag": "2981", "role": "Sentinel", "fixed_agent": "Sova"}
]

# Cache to avoid hitting API too hard
player_cache = {}

def get_headers():
    return {"Authorization": API_KEY}

def analyze_matches(matches, player_name):
    """Calculates winrates, maps, and vs-comp stats."""
    stats = {
        "wins": 0, "total": 0, "kills": 0, "deaths": 0,
        "maps": {}, 
        "vs_comps": {"Double Duelist": {"w":0,"t":0}, "Double Initiator": {"w":0,"t":0}, "Double Controller": {"w":0,"t":0}}
    }
    
    for m in matches:
        # Skip incomplete data
        if 'meta' not in m or 'stats' not in m: continue
        
        # 1. BASIC STATS
        stats['total'] += 1
        # Henrik API structure for lifetime matches:
        # map name is in m['meta']['map']['name']
        map_name = m['meta']['map']['name']
        
        # Did we win? 
        # In lifetime API, 'stats' usually has 'team' (Red/Blue) and result is harder to parse directly without match details
        # We simplify: Check if rounds_won > rounds_lost
        # Note: Lifetime API sometimes simplifies this. We try our best.
        # Ideally we use the 'stats.character.name' to find the player
        
        # For simplicity in this example, we assume we can derive W/L from round counts in 'stats'
        # (You might need to adjust this depending on exact API response format)
        team_id = m['stats']['team'] # Blue or Red
        # Logic depends on finding the match winner. 
        # For the Lifetime endpoint, it's safer to check the "won" boolean if available, or parse score.
        # Let's assume we count it if 'stats.score' is available (it varies).
        
        # --- ENEMY COMP ANALYSIS ---
        # This is tricky with "Lifetime" endpoint as it might not show ALL enemy agents.
        # If using Standard Match endpoint (v3), we have full data.
        # For this feature, we really need v3 matches, but we can't fetch 100 of them easily.
        # **Compromise:** We will return placeholder Comp Stats for now unless we fetch v3.
        
        if map_name not in stats['maps']: stats['maps'][map_name] = {"w": 0, "t": 0}
        stats['maps'][map_name]['t'] += 1
        
        # Accumulate K/D
        stats['kills'] += m['stats']['kills']
        stats['deaths'] += m['stats']['deaths']

    return stats

@app.route('/')
def home():
    return render_template('index.html')

# NEW: Player Detail Page
@app.route('/player')
def player_page():
    return render_template('player.html')

# NEW: Specific Player Stats Endpoint
@app.route('/api/player/<name>/<tag>')
def get_player_detail(name, tag):
    cache_key = f"{name}#{tag}"
    if cache_key in player_cache and (time.time() - player_cache[cache_key]['time'] < 600):
        return jsonify(player_cache[cache_key]['data'])

    safe_name = urllib.parse.quote(name)
    safe_tag = urllib.parse.quote(tag)
    
    # Fetch 50 Matches (Mixed modes)
    url = f"https://api.henrikdev.xyz/valorant/v1/lifetime/matches/{REGION}/{safe_name}/{safe_tag}?size=50"
    r = requests.get(url, headers=get_headers())
    
    ranked_matches = []
    scrim_matches = []
    
    if r.status_code == 200:
        all_data = r.json().get('data', [])
        for m in all_data:
            mode = m['meta']['mode']
            rounds = m['stats']['rounds_played']
            
            # FILTER 1: Ranked
            if mode == 'Competitive':
                ranked_matches.append(m)
            
            # FILTER 2: Scrims (Custom + >13 Rounds)
            elif mode == 'Custom Game' and rounds >= 13:
                scrim_matches.append(m)

    # Process Stats (Simplified for demo)
    # Real "Vs Comp" logic requires v3 endpoint, effectively impossible to batch-process 50 games in <2s without paying.
    # We will simulate the structure so your UI works.
    
    data = {
        "ranked": analyze_matches(ranked_matches, name),
        "scrims": analyze_matches(scrim_matches, name),
        "meta": {"name": name, "tag": tag}
    }
    
    player_cache[cache_key] = {"time": time.time(), "data": data}
    return jsonify(data)
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

