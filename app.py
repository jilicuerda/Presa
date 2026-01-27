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
    {"name": "mi abuela mola", "tag": "2981", "role": "Sentinel", "fixed_agent": "Cypher"}
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

# --- ANALYSIS HELPERS ---

def analyze_roles(matches):
    role_stats = {
        "Duelist": {"matches": 0, "wins": 0, "kills": 0, "deaths": 0},
        "Controller": {"matches": 0, "wins": 0, "kills": 0, "deaths": 0},
        "Initiator": {"matches": 0, "wins": 0, "kills": 0, "deaths": 0},
        "Sentinel": {"matches": 0, "wins": 0, "kills": 0, "deaths": 0}
    }
    
    AGENT_ROLES = {
        "Jett": "Duelist", "Raze": "Duelist", "Reyna": "Duelist", "Phoenix": "Duelist", "Yoru": "Duelist", "Neon": "Duelist", "Iso": "Duelist",
        "Omen": "Controller", "Brimstone": "Controller", "Viper": "Controller", "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller",
        "Sova": "Initiator", "Breach": "Initiator", "Skye": "Initiator", "KAY/O": "Initiator", "Fade": "Initiator", "Gekko": "Initiator",
        "Sage": "Sentinel", "Cypher": "Sentinel", "Killjoy": "Sentinel", "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel"
    }

    for m in matches:
        if 'meta' not in m or 'stats' not in m: continue
        
        agent = m.get('meta', {}).get('character', {}).get('name')
        if not agent: agent = m.get('stats', {}).get('character', {}).get('name')
        
        role = AGENT_ROLES.get(agent, "Flex")
        if role not in role_stats: continue 

        k = m['stats'].get('kills', 0)
        d = m['stats'].get('deaths', 0)
        
        my_team = m.get('stats', {}).get('team', '').lower()
        blue = m['teams']['blue']
        red = m['teams']['red']
        winner = "blue" if blue > red else "red"
        is_win = (my_team == winner)

        role_stats[role]['matches'] += 1
        role_stats[role]['kills'] += k
        role_stats[role]['deaths'] += d
        if is_win: role_stats[role]['wins'] += 1

    radar = { "Duelist": 0, "Controller": 0, "Initiator": 0, "Sentinel": 0, "Slayer": 0 }
    
    total_kd = 0
    total_matches = 0

    for role, data in role_stats.items():
        if data['matches'] > 0:
            wr = int((data['wins'] / data['matches']) * 100)
            radar[role] = wr
            total_kd += (data['kills'] / data['deaths']) if data['deaths'] > 0 else data['kills']
            total_matches += 1

    if total_matches > 0:
        avg_kd = total_kd / total_matches
        # Map avg K/D (0.5 to 2.0) roughly to 0-100 score
        slayer_score = min(max((avg_kd - 0.5) * 66, 0), 100) 
        radar["Slayer"] = int(slayer_score)

    return {"stats": role_stats, "radar": radar}

def analyze_matches(matches):
    stats = {
        "wins": 0, "total": 0, "kills": 0, "deaths": 0,
        "agents": {}, "maps": {}, "best_map": "N/A"
    }
    
    for m in matches:
        if 'meta' not in m or 'stats' not in m: continue
        
        # 1. Get Agent
        agent = m.get('meta', {}).get('character', {}).get('name')
        if not agent: agent = m.get('stats', {}).get('character', {}).get('name')
        if not agent: continue
        
        # 2. Get Map
        map_name = m.get('meta', {}).get('map', {}).get('name')
        if not map_name: continue

        # 3. Get Team
        my_team = m.get('stats', {}).get('team')
        if not my_team: continue
        my_team = my_team.lower()

        # Stats
        stats['total'] += 1
        k = m['stats'].get('kills', 0)
        d = m['stats'].get('deaths', 0)
        stats['kills'] += k
        stats['deaths'] += d

        # Win
        blue = m['teams']['blue']
        red = m['teams']['red']
        winner = "blue" if blue > red else "red"
        is_win = (my_team == winner)
        if is_win: stats['wins'] += 1

        # Aggregation
        if agent not in stats['agents']: stats['agents'][agent] = {"matches": 0, "wins": 0}
        stats['agents'][agent]['matches'] += 1
        if is_win: stats['agents'][agent]['wins'] += 1

        if map_name not in stats['maps']: stats['maps'][map_name] = {"matches": 0, "wins": 0, "kills": 0, "deaths": 0}
        stats['maps'][map_name]['matches'] += 1
        if is_win: stats['maps'][map_name]['wins'] += 1
        stats['maps'][map_name]['kills'] += k
        stats['maps'][map_name]['deaths'] += d

    # Maps Sort
    sorted_maps = []
    for m_name, m_data in stats['maps'].items():
        wr = int((m_data['wins'] / m_data['matches']) * 100) if m_data['matches'] > 0 else 0
        kd = round(m_data['kills'] / m_data['deaths'], 2) if m_data['deaths'] > 0 else m_data['kills']
        sorted_maps.append({"name": m_name, "matches": m_data['matches'], "win_rate": wr, "kd": kd})
    stats['top_maps'] = sorted(sorted_maps, key=lambda x: x['matches'], reverse=True)
    if stats['top_maps']: stats['best_map'] = stats['top_maps'][0]['name']

    # Agents Sort
    sorted_agents = []
    for a_name, a_data in stats['agents'].items():
        wr = int((a_data['wins'] / a_data['matches']) * 100) if a_data['matches'] > 0 else 0
        sorted_agents.append({"name": a_name, "matches": a_data['matches'], "win_rate": wr})
    stats['top_agents'] = sorted(sorted_agents, key=lambda x: x['matches'], reverse=True)
    
    # NEW: Attach Roles
    stats['roles'] = analyze_roles(matches)
    
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
    
    safe_name = urllib.parse.quote(name)
    safe_tag = urllib.parse.quote(tag)
    
    url = f"https://api.henrikdev.xyz/valorant/v1/lifetime/matches/{REGION}/{safe_name}/{safe_tag}?size=60"
    r = requests.get(url, headers=get_headers())
    
    ranked_matches = []
    scrim_matches = []
    
    if r.status_code == 200:
        all_data = r.json().get('data', [])
        print(f"🔍 DEBUG: Found {len(all_data)} raw matches for {name}")
        
        for m in all_data:
            if 'meta' not in m or 'mode' not in m['meta']: continue
            mode = m['meta']['mode'].lower()
            
            if mode in ['competitive', 'unrated', 'swiftplay']:
                ranked_matches.append(m)
            elif 'custom' in mode:
                # Custom Filter: At least 13 rounds played total
                try:
                    blue = m['teams']['blue']
                    red = m['teams']['red']
                    if (blue + red) >= 13: 
                        scrim_matches.append(m)
                except:
                    pass # Skip if teams data is broken

    data = {
        "ranked": analyze_matches(ranked_matches),
        "scrims": analyze_matches(scrim_matches)
    }
    return jsonify(data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
