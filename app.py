import os
import time
import requests
import urllib.parse
from flask import Flask, jsonify, render_template, request

app = Flask(__name__, static_folder='static', template_folder='templates')

API_KEY = os.environ.get("HENRIK_KEY") 
REGION = "eu"

ROSTER = [
    {"name": "Jilicuerda", "tag": "1734", "role": "Initiator", "fixed_agent": "Breach"},
    {"name": "CriskXK", "tag": "PRESA", "role": "Duelist", "fixed_agent": "Jett"},
    {"name": "Magic Tostada", "tag": "MCY", "role": "IGL", "fixed_agent": "Fade"},
    {"name": "Cleezzy", "tag": "Reina", "role": "Smoker", "fixed_agent": "Viper"},
    {"name": "mi abuela mola", "tag": "2981", "role": "Sentinel", "fixed_agent": "Sova"}
]

cache = {
    "last_updated": 0,
    "roster_data": [],
    "player_details": {} 
}

def get_headers():
    return {"Authorization": API_KEY}

def update_roster_ranks():
    print("--- 🔄 UPDATING ROSTER RANKS ---")
    updated_roster = []
    for player in ROSTER:
        stats = player.copy()
        stats['main_agent'] = player['fixed_agent']
        stats['rank'] = "Unranked"
        try:
            safe_name = urllib.parse.quote(player['name'])
            safe_tag = urllib.parse.quote(player['tag'])
            url = f"https://api.henrikdev.xyz/valorant/v2/mmr/{REGION}/{safe_name}/{safe_tag}"
            r = requests.get(url, headers=get_headers())
            if r.status_code == 200:
                data = r.json().get('data', {}).get('current_data', {})
                rank = data.get('currenttierpatched')
                if rank: stats['rank'] = rank
            time.sleep(0.5) 
        except Exception as e:
            print(f"❌ Error {player['name']}: {e}")
        updated_roster.append(stats)
    return updated_roster

def analyze_matches(matches):
    """
    Groups data by Agent AND Maps. Includes SAFETY CHECKS.
    """
    stats = {
        "wins": 0, "total": 0, 
        "kills": 0, "deaths": 0,
        "agents": {}, 
        "maps": {},
        "best_map": "N/A"
    }
    
    for m in matches:
        # --- SAFETY SHIELD: SKIP BROKEN MATCHES ---
        if 'meta' not in m or 'stats' not in m: continue
        if not m['meta'].get('character'): continue
        if not m['meta']['character'].get('name'): continue
        if not m['meta'].get('map'): continue
        if not m['meta']['map'].get('name'): continue
        if 'team' not in m['stats']: continue
        # ------------------------------------------

        stats['total'] += 1
        
        # 1. Data
        agent = m['meta']['character']['name']
        map_name = m['meta']['map']['name']
        k = m['stats'].get('kills', 0)
        d = m['stats'].get('deaths', 0)
        stats['kills'] += k
        stats['deaths'] += d

        # 2. Win Check
        my_team = m['stats']['team'].lower()
        blue = m['teams']['blue']
        red = m['teams']['red']
        winner = "blue" if blue > red else "red"
        is_win = (my_team == winner)
        
        if is_win: stats['wins'] += 1

        # 3. Agent Stats
        if agent not in stats['agents']:
            stats['agents'][agent] = {"matches": 0, "wins": 0}
        stats['agents'][agent]['matches'] += 1
        if is_win: stats['agents'][agent]['wins'] += 1

        # 4. Map Stats
        if map_name not in stats['maps']:
            stats['maps'][map_name] = {"matches": 0, "wins": 0, "kills": 0, "deaths": 0}
        stats['maps'][map_name]['matches'] += 1
        if is_win: stats['maps'][map_name]['wins'] += 1
        stats['maps'][map_name]['kills'] += k
        stats['maps'][map_name]['deaths'] += d

    # Final Calcs
    sorted_maps = []
    for m_name, m_data in stats['maps'].items():
        wr = int((m_data['wins'] / m_data['matches']) * 100) if m_data['matches'] > 0 else 0
        kd = round(m_data['kills'] / m_data['deaths'], 2) if m_data['deaths'] > 0 else m_data['kills']
        sorted_maps.append({"name": m_name, "matches": m_data['matches'], "win_rate": wr, "kd": kd})
    
    stats['top_maps'] = sorted(sorted_maps, key=lambda x: x['matches'], reverse=True)
    if stats['top_maps']: stats['best_map'] = stats['top_maps'][0]['name']

    sorted_agents = []
    for a_name, a_data in stats['agents'].items():
        wr = int((a_data['wins'] / a_data['matches']) * 100) if a_data['matches'] > 0 else 0
        sorted_agents.append({"name": a_name, "matches": a_data['matches'], "win_rate": wr})
    
    stats['top_agents'] = sorted(sorted_agents, key=lambda x: x['matches'], reverse=True)
    return stats

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/player')
def player_page():
    return render_template('player.html')

@app.route('/api/team-history')
def get_roster_history():
    current_time = time.time()
    if not cache["roster_data"] or (current_time - cache["last_updated"] > 1800):
        new_data = update_roster_ranks()
        if new_data:
            cache["roster_data"] = new_data
            cache["last_updated"] = current_time
    return jsonify({"roster": cache["roster_data"]})

@app.route('/api/player/<name>/<tag>')
def get_player_detail(name, tag):
    p_key = f"{name}#{tag}"
    current_time = time.time()
    
    # Check Cache (10 mins)
    if p_key in cache["player_details"] and (current_time - cache["player_details"][p_key]['time'] < 600):
        return jsonify(cache["player_details"][p_key]['data'])

    safe_name = urllib.parse.quote(name)
    safe_tag = urllib.parse.quote(tag)
    
    # Increased size to 60 to find more scrims
    url = f"https://api.henrikdev.xyz/valorant/v1/lifetime/matches/{REGION}/{safe_name}/{safe_tag}?size=60"
    r = requests.get(url, headers=get_headers())
    
    ranked_matches = []
    scrim_matches = []
    
    if r.status_code == 200:
        all_data = r.json().get('data', [])
        
        for m in all_data:
            mode = m['meta']['mode'].lower() # Case insensitive
            
            # FILTER 1: Ranked
            if mode == 'competitive':
                ranked_matches.append(m)
            
            # FILTER 2: Scrims (Custom Game + >13 Rounds)
            elif 'custom' in mode:
                blue = m['teams']['blue']
                red = m['teams']['red']
                if (blue + red) >= 13: 
                    scrim_matches.append(m)

    data = {
        "ranked": analyze_matches(ranked_matches),
        "scrims": analyze_matches(scrim_matches)
    }
    
    cache["player_details"][p_key] = {"time": current_time, "data": data}
    return jsonify(data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
