import os
import time
import requests
import urllib.parse
from functools import wraps
from flask import Flask, jsonify, render_template, request, Response
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

API_KEY = os.environ.get("HENRIK_KEY") 
REGION = "eu"

# --- SUPABASE SETUP ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        clean_url = SUPABASE_URL.split('/rest/v1')[0].rstrip('/')
        supabase = create_client(clean_url, SUPABASE_KEY)
        print("✅ Supabase connection initialized.")
    except Exception as e:
        print(f"❌ Supabase init error: {e}")

# --- ADMIN AUTHENTICATION ---
def check_auth(username, password): return username == 'admin' and password == 'presa'
def authenticate(): return Response('Access Denied.', 401, {'WWW-Authenticate': 'Basic realm="Presa Command Center"'})
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password): return authenticate()
        return f(*args, **kwargs)
    return decorated

# --- ROSTERS ---
ROSTERS = {
    "main": [
        {"name": "POGOツ", "tag": "OMEGA", "role": "Controller", "fixed_agent": "Astra", "type": "player"},
        {"name": "Obito", "tag": "ASCK", "role": "Sentinel", "fixed_agent": "Cypher", "type": "player"},
        {"name": "CoRa", "tag": "FGR", "role": "Initiator", "fixed_agent": "Fade", "type": "player"},
        {"name": "Oby", "tag": "F4W", "role": "Duelist", "fixed_agent": "Jett", "type": "player"},
        {"name": "21 Swiss", "tag": "EMEA", "role": "Initiator", "fixed_agent": "Breach", "type": "player"},
    ],
    "academy": [
        {"name": "Magic Tostada", "tag": "MCY", "role": "IGL", "fixed_agent": "Fade", "type": "player"},
        {"name": "Cleezzy", "tag": "Reina", "role": "Duelist", "fixed_agent": "Jett", "type": "player"},
        {"name": "PRESA MKultra", "tag": "mykei", "role": "Initiator", "fixed_agent": "Yoru", "type": "player"},
        {"name": "H0KAGE", "tag": "Nyx", "role": "Smoker", "fixed_agent": "Omen", "type": "player"},
        {"name": "FNC MrFreezer", "tag": "ily", "role": "Sentinel", "fixed_agent": "Cypher", "type": "player"},
        {"name": "IsRasson", "tag": "SSJ", "role": "Sentinel", "fixed_agent": "Sova", "type": "sub"},
        {"name": "CriskXK", "tag": "PRESA", "role": "Flex", "fixed_agent": "Waylay", "type": "sub"},
        {"name": "zaka", "tag": "1734", "role": "Coach", "fixed_agent": "Kayo", "type": "coach"}
    ]
}

cache = {
    "last_updated": {"main": 0, "academy": 0},
    "roster_data": {"main": [], "academy": []},
    "player_details": {},
    "news": {"last_updated": 0, "data": []}
}

def get_headers(): return {"Authorization": API_KEY}

# --- CRASH-PROOF API FETCHER ---
def fetch_with_retry(url):
    """Fails fast to prevent Render from crashing the app due to 30s timeout."""
    try:
        r = requests.get(url, headers=get_headers(), timeout=5)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 429:
            # Try exactly once more after 1 second, then give up
            time.sleep(1)
            r2 = requests.get(url, headers=get_headers(), timeout=5)
            if r2.status_code == 200:
                return r2.json()
    except: pass
    return None

def update_roster_ranks(team_id):
    updated_roster = []
    if team_id not in ROSTERS: return []
    for player in ROSTERS[team_id]:
        stats = player.copy()
        stats['main_agent'] = player['fixed_agent']
        stats['rank'] = "Unranked"
        
        safe_name, safe_tag = urllib.parse.quote(player['name']), urllib.parse.quote(player['tag'])
        url = f"https://api.henrikdev.xyz/valorant/v2/mmr/{REGION}/{safe_name}/{safe_tag}"
        
        data_json = fetch_with_retry(url)
        if data_json:
            rank = data_json.get('data', {}).get('current_data', {}).get('currenttierpatched')
            if rank: stats['rank'] = rank
            
        time.sleep(0.3) 
        updated_roster.append(stats)
    return updated_roster

def check_player_climb(name, tag):
    safe_name = urllib.parse.quote(name)
    safe_tag = urllib.parse.quote(tag)
    url = f"https://api.henrikdev.xyz/valorant/v1/mmr-history/{REGION}/{safe_name}/{safe_tag}"
    
    data_json = fetch_with_retry(url)
    if data_json:
        data = data_json.get('data', [])
        if len(data) >= 2:
            current_tier = data[0].get('currenttier')
            lookback = min(5, len(data)) - 1
            old_tier = data[lookback].get('currenttier')
            
            if current_tier and old_tier and current_tier > old_tier:
                return {
                    "climbed": True,
                    "current_rank": data[0].get('currenttierpatched'),
                    "old_rank": data[lookback].get('currenttierpatched')
                }
    return {"climbed": False}

def analyze_roles(matches, is_db=False):
    role_stats = {"Duelist": {"matches": 0, "wins": 0, "kills": 0, "deaths": 0}, "Controller": {"matches": 0, "wins": 0, "kills": 0, "deaths": 0}, "Initiator": {"matches": 0, "wins": 0, "kills": 0, "deaths": 0}, "Sentinel": {"matches": 0, "wins": 0, "kills": 0, "deaths": 0}}
    AGENT_ROLES = {"Jett": "Duelist", "Raze": "Duelist", "Reyna": "Duelist", "Phoenix": "Duelist", "Yoru": "Duelist", "Neon": "Duelist", "Iso": "Duelist", "Omen": "Controller", "Brimstone": "Controller", "Viper": "Controller", "Astra": "Controller", "Harbor": "Controller", "Clove": "Controller", "Sova": "Initiator", "Breach": "Initiator", "Skye": "Initiator", "KAY/O": "Initiator", "Kayo": "Initiator", "Fade": "Initiator", "Gekko": "Initiator", "Sage": "Sentinel", "Cypher": "Sentinel", "Killjoy": "Sentinel", "Chamber": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel"}
    for m in matches:
        if is_db:
            agent = m.get('agent')
            k, d = m.get('kills', 0), m.get('deaths', 0)
            is_win = m.get('team_won', False)
        else:
            if 'meta' not in m or 'stats' not in m: continue
            agent = m.get('meta', {}).get('character', {}).get('name') or m.get('stats', {}).get('character', {}).get('name')
            k, d = m['stats'].get('kills', 0), m['stats'].get('deaths', 0)
            my_team = m.get('stats', {}).get('team', '').lower()
            is_win = (my_team == ("blue" if m['teams']['blue'] > m['teams']['red'] else "red"))
        role = AGENT_ROLES.get(agent, "Flex")
        if role not in role_stats: continue 
        role_stats[role]['matches'] += 1
        role_stats[role]['kills'] += k
        role_stats[role]['deaths'] += d
        if is_win: role_stats[role]['wins'] += 1
    radar = { "Duelist": 0, "Controller": 0, "Initiator": 0, "Sentinel": 0, "Slayer": 0 }
    total_kd = 0; total_matches = 0
    for role, data in role_stats.items():
        if data['matches'] > 0:
            radar[role] = int((data['wins'] / data['matches']) * 100)
            total_kd += (data['kills'] / data['deaths']) if data['deaths'] > 0 else data['kills']
            total_matches += 1
    if total_matches > 0: radar["Slayer"] = int(min(max(((total_kd / total_matches) - 0.5) * 66, 0), 100))
    return {"stats": role_stats, "radar": radar}

def analyze_matches(matches, is_db=False):
    stats = {"wins": 0, "total": 0, "kills": 0, "deaths": 0, "agents": {}, "maps": {}, "best_map": "N/A"}
    for m in matches:
        if is_db:
            agent = m.get('agent')
            map_name = m.get('map_name')
            is_win = m.get('team_won', False)
            k, d = m.get('kills', 0), m.get('deaths', 0)
        else:
            if 'meta' not in m or 'stats' not in m: continue
            agent = m.get('meta', {}).get('character', {}).get('name') or m.get('stats', {}).get('character', {}).get('name')
            map_name = m.get('meta', {}).get('map', {}).get('name')
            my_team = m.get('stats', {}).get('team')
            if not agent or not map_name or not my_team: continue
            is_win = (my_team.lower() == ("blue" if m['teams']['blue'] > m['teams']['red'] else "red"))
            k, d = m['stats'].get('kills', 0), m['stats'].get('deaths', 0)
        stats['total'] += 1
        stats['kills'] += k
        stats['deaths'] += d
        if is_win: stats['wins'] += 1
        if agent not in stats['agents']: stats['agents'][agent] = {"matches": 0, "wins": 0}
        stats['agents'][agent]['matches'] += 1
        if is_win: stats['agents'][agent]['wins'] += 1
        if map_name not in stats['maps']: stats['maps'][map_name] = {"matches": 0, "wins": 0, "kills": 0, "deaths": 0}
        stats['maps'][map_name]['matches'] += 1
        if is_win: stats['maps'][map_name]['wins'] += 1
        stats['maps'][map_name]['kills'] += k
        stats['maps'][map_name]['deaths'] += d
    sorted_maps = [{"name": m, "matches": d['matches'], "win_rate": int((d['wins']/d['matches'])*100) if d['matches']>0 else 0, "kd": round(d['kills']/d['deaths'],2) if d['deaths']>0 else d['kills']} for m, d in stats['maps'].items()]
    stats['top_maps'] = sorted(sorted_maps, key=lambda x: x['matches'], reverse=True)
    if stats['top_maps']: stats['best_map'] = stats['top_maps'][0]['name']
    sorted_agents = [{"name": a, "matches": d['matches'], "win_rate": int((d['wins']/d['matches'])*100) if d['matches']>0 else 0} for a, d in stats['agents'].items()]
    stats['top_agents'] = sorted(sorted_agents, key=lambda x: x['matches'], reverse=True)
    stats['roles'] = analyze_roles(matches, is_db)
    return stats

# --- PUBLIC ROUTES ---
@app.route('/')
def home(): return render_template('index.html')

@app.route('/roster')
def roster_page(): return render_template('roster.html')

@app.route('/player')
def player_page(): return render_template('player.html')

@app.route('/api/team-history/<team_id>')
def get_roster_history(team_id):
    if team_id not in ROSTERS: return jsonify({"error": "Invalid team"}), 400
    current_time = time.time()
    
    try:
        if not cache["roster_data"][team_id] or (current_time - cache["last_updated"][team_id] > 1800):
            new_data = update_roster_ranks(team_id)
            if new_data:
                cache["roster_data"][team_id] = new_data
                cache["last_updated"][team_id] = current_time
    except Exception as e:
        print(f"Error fetching ranks: {e}")
        
    # Safe Fallback: If cache is completely empty, send a default structure so the page doesn't crash
    if not cache["roster_data"][team_id]:
        fallback = []
        for p in ROSTERS[team_id]:
            stat = p.copy()
            stat['main_agent'] = p['fixed_agent']
            stat['rank'] = "Unranked"
            fallback.append(stat)
        return jsonify({"roster": fallback})

    return jsonify({"roster": cache["roster_data"][team_id]})

@app.route('/api/tournaments/<team_id>')
def get_public_tournaments(team_id):
    if not supabase: return jsonify([])
    try:
        res = supabase.table('tournaments').select('*').eq('team_division', team_id).order('created_at', desc=True).execute()
        return jsonify(res.data)
    except: return jsonify([])

@app.route('/api/news')
def get_news_feed():
    current_time = time.time()
    if current_time - cache["news"]["last_updated"] < 3600 and cache["news"]["data"]:
        return jsonify(cache["news"]["data"])

    news_items = []
    start_processing_time = time.time()
    
    if supabase:
        try:
            res = supabase.table('tournaments').select('*').order('created_at', desc=True).limit(10).execute()
            for t in res.data:
                p = (t.get('placement') or '').lower()
                if any(word in p for word in ['1st', '2nd', '3rd', 'champion', 'runner', 'podium', 'winner']):
                    news_items.append({
                        "type": "tournament",
                        "event_name": t['name'],
                        "placement": t['placement'],
                        "division": t['team_division'],
                        "logo_url": t.get('logo_url')
                    })
        except: pass

    for div, players in ROSTERS.items():
        for p in players:
            # STOPWATCH: Abort if approaching Render's 30s timeout
            if time.time() - start_processing_time > 15:
                break
                
            if p.get('type') in ['player', 'sub']:
                climb = check_player_climb(p['name'], p['tag'])
                if climb["climbed"]:
                    old_r, curr_r = climb["old_rank"], climb["current_rank"]
                    msg = f"Congratulations to {p['name']} for getting out of {old_r}!"
                    if "1" in curr_r and "3" in old_r:
                        msg = f"Shout out to {p['name']} for hitting {curr_r}!"
                    elif "Immortal" in curr_r or "Radiant" in curr_r:
                        msg = f"Congratulations {p['name']} for your massive climb to {curr_r}!"
                    
                    news_items.append({
                        "type": "player_climb",
                        "message": msg,
                        "division": div,
                        "player": {
                            "name": p['name'], "tag": p['tag'], "role": p['role'],
                            "fixed_agent": p['fixed_agent'], "rank": curr_r
                        }
                    })
                time.sleep(0.2) 

    cache["news"]["data"] = news_items
    cache["news"]["last_updated"] = current_time
    return jsonify(news_items)

@app.route('/api/player/<name>/<tag>')
def get_player_detail(name, tag):
    p_key = f"{name}#{tag}"
    current_time = time.time()
    if p_key in cache["player_details"] and (current_time - cache["player_details"][p_key]['time'] < 600):
        return jsonify(cache["player_details"][p_key]['data'])
    
    safe_name, safe_tag = urllib.parse.quote(name), urllib.parse.quote(tag)
    url = f"https://api.henrikdev.xyz/valorant/v1/lifetime/matches/{REGION}/{safe_name}/{safe_tag}?size=40"
    ranked_matches = []
    
    data_json = fetch_with_retry(url)
    if data_json:
        for m in data_json.get('data', []):
            mode = m.get('meta', {}).get('mode', '').lower()
            if mode in ['competitive', 'unrated', 'swiftplay']: ranked_matches.append(m)

    scrim_matches = []
    tourney_matches = []
    if supabase:
        try:
            p_stats_res = supabase.table('player_match_stats').select('*').ilike('player_name', name).execute()
            if p_stats_res.data:
                match_ids = [s['match_id'] for s in p_stats_res.data]
                c_matches_res = supabase.table('custom_matches').select('id, tournament_id, map_name, team_won').in_('id', match_ids).execute()
                c_matches_dict = {m['id']: m for m in c_matches_res.data}
                tourney_ids = list(set([m['tournament_id'] for m in c_matches_res.data]))
                t_res = supabase.table('tournaments').select('id, match_type').in_('id', tourney_ids).execute()
                t_types = {t['id']: t['match_type'] for t in t_res.data}

                for stat in p_stats_res.data:
                    match_info = c_matches_dict.get(stat['match_id'])
                    if match_info:
                        combined = {"agent": stat['agent'], "kills": stat['kills'], "deaths": stat['deaths'], "map_name": match_info['map_name'], "team_won": match_info['team_won']}
                        if t_types.get(match_info['tournament_id'], 'tournament') == 'scrim': scrim_matches.append(combined)
                        else: tourney_matches.append(combined)
        except Exception as e: 
            print(f"Error fetching DB stats: {e}")

    data = {"ranked": analyze_matches(ranked_matches, is_db=False), "scrims": analyze_matches(scrim_matches, is_db=True), "tournaments": analyze_matches(tourney_matches, is_db=True)}
    cache["player_details"][p_key] = {"time": current_time, "data": data}
    return jsonify(data)

# --- ADMIN ROUTES ---
@app.route('/Presa_log')
@requires_auth
def admin_panel():
    tournaments = []
    if supabase:
        try:
            res = supabase.table('tournaments').select('*').order('created_at', desc=True).execute()
            tournaments = res.data
        except: pass
    return render_template('admin.html', tournaments=tournaments)

@app.route('/api/admin/add_tournament', methods=['POST'])
@requires_auth
def add_tournament():
    if not supabase: return jsonify({"error": "DB not connected"}), 500
    data = request.json
    try:
        res = supabase.table('tournaments').insert({"name": data.get("name"), "team_division": data.get("division"), "placement": data.get("placement"), "match_type": data.get("type", "tournament"), "logo_url": data.get("logo_url", "")}).execute()
        return jsonify({"success": True, "data": res.data})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/admin/ingest_match', methods=['POST'])
@requires_auth
def ingest_match():
    if not supabase: return jsonify({"error": "DB not connected"}), 500
    data = request.json
    tourney_id = data.get('tournament_id')
    tracker_url = data.get('tracker_url', '')
    match_id = tracker_url.split('/')[-1].split('?')[0].strip()
    if not match_id: return jsonify({"error": "Invalid Match ID"}), 400
    
    url = f"https://api.henrikdev.xyz/valorant/v2/match/{match_id}"
    data_json = fetch_with_retry(url)
    if not data_json: return jsonify({"error": "Match not found or API busy"}), 404
    match_data = data_json.get('data')
    
    try:
        t_res = supabase.table('tournaments').select('team_division').eq('id', tourney_id).execute()
        if not t_res.data: return jsonify({"error": "Tournament missing"}), 404
        
        presa_players_map = {}
        for roster_list in ROSTERS.values():
            for p in roster_list:
                presa_players_map[(p['name'].lower(), p['tag'].lower())] = p['name']
                
        meta = match_data.get('metadata', {})
        map_name = meta.get('map', 'Unknown')
        teams = match_data.get('teams', {})
        players = match_data.get('players', {}).get('all_players', [])
        
        presa_color = None
        for p in players:
            key = (p['name'].lower(), p['tag'].lower())
            if key in presa_players_map:
                presa_color = p['team'].lower()
                break
                
        if not presa_color: return jsonify({"error": f"No Presa organization players found in this match."}), 400
        
        our_score = teams.get(presa_color, {}).get('rounds_won', 0)
        enemy_score = teams.get('red' if presa_color=='blue' else 'blue', {}).get('rounds_won', 0)
        match_insert = supabase.table('custom_matches').insert({"tournament_id": tourney_id, "riot_match_id": match_id, "map_name": map_name, "team_won": teams.get(presa_color, {}).get('has_won', False), "team_score": our_score, "enemy_score": enemy_score}).execute()
        db_match_id = match_insert.data[0]['id']
        
        stats = []
        for p in players:
            key = (p['name'].lower(), p['tag'].lower())
            if key in presa_players_map:
                correct_roster_name = presa_players_map[key]
                stats.append({"match_id": db_match_id, "player_name": correct_roster_name, "agent": p['character'], "kills": p['stats']['kills'], "deaths": p['stats']['deaths'], "assists": p['stats']['assists']})
        if stats: supabase.table('player_match_stats').insert(stats).execute()
        return jsonify({"success": True})
    except: return jsonify({"error": "Error processing match or already in DB."}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
