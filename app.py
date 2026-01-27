import os
import time
import requests
import urllib.parse
from flask import Flask, jsonify, render_template, request

app = Flask(__name__, static_folder='static', template_folder='templates')

# --- CONFIGURATION ---
API_KEY = os.environ.get("HENRIK_KEY") 
REGION = "eu"

# YOUR FIXED ROSTER
ROSTER = [
    {"name": "Jilicuerda", "tag": "1734", "role": "Initiator", "fixed_agent": "Astra"},
    {"name": "CriskXK", "tag": "PRESA", "role": "Duelist", "fixed_agent": "Jett"},
    {"name": "Magic Tostada", "tag": "MCY", "role": "IGL", "fixed_agent": "Kayo"},
    {"name": "Cleezzy", "tag": "Reina", "role": "Smoker", "fixed_agent": "Viper"},
    {"name": "mi abuela mola", "tag": "2981", "role": "Sentinel", "fixed_agent": "Sova"}
]

# CACHE (Stores data to reduce API calls)
cache = {
    "last_updated": 0,
    "roster_data": [],
    "player_details": {} 
}

def get_headers():
    return {"Authorization": API_KEY}

# --- LOGIC: Roster Ranks ---
def update_roster_ranks():
    print("--- 🔄 UPDATING ROSTER RANKS ---")
    updated_roster = []

    for player in ROSTER:
        stats = player.copy()
        stats['main_agent'] = player['fixed_agent'] # Use Fixed Agent
        stats['rank'] = "Unranked"

        try:
            safe_name = urllib.parse.quote(player['name'])
            safe_tag = urllib.parse.quote(player['tag'])
            
            # MMR V2 (Fastest for Rank)
            url = f"https://api.henrikdev.xyz/valorant/v2/mmr/{REGION}/{safe_name}/{safe_tag}"
            r = requests.get(url, headers=get_headers())
            
            if r.status_code == 200:
                data = r.json().get('data', {}).get('current_data', {})
                rank = data.get('currenttierpatched')
                if rank: stats['rank'] = rank
            
            print(f"✅ {player['name']}: {stats['rank']}")
            time.sleep(1) 

        except Exception as e:
            print(f"❌ Error {player['name']}: {e}")
        
        updated_roster.append(stats)
    return updated_roster

# --- LOGIC: Detailed Stats (Ranked vs Scrims) ---
def analyze_matches(matches):
    """
    Advanced analysis: Groups data by Agent to find patterns.
    Returns: {
        "wins": int, "total": int,
        "kd": float,
        "agents": {
            "Jett": {"matches": 10, "wins": 6, "best_map": "Ascent"},
            ...
        }
    }
    """
    stats = {
        "wins": 0, "total": 0, 
        "kills": 0, "deaths": 0,
        "agents": {} # New: Stores stats per agent
    }
    
    for m in matches:
        stats['total'] += 1
        
        # 1. Who did they play?
        # Lifetime API puts agent in meta -> character -> name
        agent = m['meta']['character']['name']
        map_name = m['meta']['map']['name']
        
        # Initialize this agent if new
        if agent not in stats['agents']:
            stats['agents'][agent] = {
                "matches": 0, "wins": 0, "kills": 0, "deaths": 0,
                "maps": {} # Track map performance for this agent
            }
        
        agent_stats = stats['agents'][agent]
        agent_stats['matches'] += 1
        agent_stats['maps'][map_name] = agent_stats['maps'].get(map_name, 0) + 1
        
        # 2. Combat Stats
        if 'stats' in m:
            k = m['stats'].get('kills', 0)
            d = m['stats'].get('deaths', 0)
            stats['kills'] += k
            stats['deaths'] += d
            
            agent_stats['kills'] += k
            agent_stats['deaths'] += d

            # 3. Win Check
            my_team = m['stats']['team'].lower()
            blue = m['teams']['blue']
            red = m['teams']['red']
            winner = "blue" if blue > red else "red"
            
            if my_team == winner:
                stats['wins'] += 1
                agent_stats['wins'] += 1

    # 4. Final Calculations (Best Map per Agent)
    # We convert the raw map counts into a single "Best Map" string
    for agent, data in stats['agents'].items():
        if data['maps']:
            data['best_map'] = max(data['maps'], key=data['maps'].get)
        else:
            data['best_map'] = "N/A"
            
        # Add a formatted KD for that agent
        data['kd_ratio'] = round(data['kills'] / data['deaths'], 2) if data['deaths'] > 0 else data['kills']
        
        # Add Win Rate for that agent
        data['win_rate'] = int((data['wins'] / data['matches']) * 100)

    # Convert agents dict to a sorted list (Most played first)
    sorted_agents = sorted(
        [{"name": k, **v} for k, v in stats['agents'].items()],
        key=lambda x: x['matches'],
        reverse=True
    )
    
    stats['top_agents'] = sorted_agents
    return stats

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/player')
def player_page():
    return render_template('player.html')

@app.route('/api/team-history')
def get_roster_history():
    current_time = time.time()
    # Update every 30 mins
    if not cache["roster_data"] or (current_time - cache["last_updated"] > 1800):
        new_data = update_roster_ranks()
        if new_data:
            cache["roster_data"] = new_data
            cache["last_updated"] = current_time
    return jsonify({"roster": cache["roster_data"]})

@app.route('/api/player/<name>/<tag>')
def get_player_detail(name, tag):
    # Cache key for this specific player
    p_key = f"{name}#{tag}"
    current_time = time.time()
    
    # Check cache (Expires in 10 mins / 600s)
    if p_key in cache["player_details"] and (current_time - cache["player_details"][p_key]['time'] < 600):
        return jsonify(cache["player_details"][p_key]['data'])

    safe_name = urllib.parse.quote(name)
    safe_tag = urllib.parse.quote(tag)
    
    # Fetch last 40 Matches
    url = f"https://api.henrikdev.xyz/valorant/v1/lifetime/matches/{REGION}/{safe_name}/{safe_tag}?size=40"
    r = requests.get(url, headers=get_headers())
    
    ranked_matches = []
    scrim_matches = []
    
    if r.status_code == 200:
        all_data = r.json().get('data', [])
        for m in all_data:
            mode = m['meta']['mode']
            
            # FILTER: Ranked
            if mode == 'Competitive':
                ranked_matches.append(m)
            
            # FILTER: Scrims (Custom Game + at least 13 rounds played)
            elif mode == 'Custom Game':
                # Sometimes custom games end early, so we check round count
                # Note: 'rounds_played' is sometimes in 'stats' or derived from scores
                blue = m['teams']['blue']
                red = m['teams']['red']
                if (blue + red) >= 13: 
                    scrim_matches.append(m)

    # Calculate Stats
    data = {
        "ranked": analyze_matches(ranked_matches),
        "scrims": analyze_matches(scrim_matches)
    }
    
    # Save to cache
    cache["player_details"][p_key] = {"time": current_time, "data": data}
    
    return jsonify(data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

