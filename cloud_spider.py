import requests
import urllib.parse
import os
import time
from supabase import create_client, Client

# These will be securely injected by GitHub Actions
API_KEY = os.environ.get("HENRIK_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
REGION = "eu"

# Your complete roster (The "Anchor" players)
team_roster = [
    {"name": "PRESA MKULTRA", "tag": "MYKEI"}, {"name": "POGOツ", "tag": "OMEGA"},
    {"name": "Cleezzy", "tag": "Reina"}, {"name": "H0KAGE", "tag": "Nyx"},
    {"name": "Magic Tostada", "tag": "MCY"}, {"name": "Obito", "tag": "ASCK"},
    {"name": "CoRa", "tag": "FGR"}, {"name": "Oby", "tag": "F4W"},
    {"name": "21 Swiss", "tag": "EMEA"}, {"name": "FNC MrFreezer", "tag": "ily"},
    {"name": "IsRasson", "tag": "SSJ"}, {"name": "CriskXK", "tag": "PRESA"},
    {"name": "zaka", "tag": "1734"}
]

agent_roles = {
    'Jett': 'Duelist', 'Reyna': 'Duelist', 'Raze': 'Duelist', 'Phoenix': 'Duelist', 'Neon': 'Duelist', 'Yoru': 'Duelist', 'Iso': 'Duelist',
    'Omen': 'Controller', 'Brimstone': 'Controller', 'Viper': 'Controller', 'Astra': 'Controller', 'Harbor': 'Controller', 'Clove': 'Controller',
    'Sova': 'Initiator', 'Breach': 'Initiator', 'Skye': 'Initiator', 'KAY/O': 'Initiator', 'Kayo': 'Initiator', 'Fade': 'Initiator', 'Gekko': 'Initiator',
    'Killjoy': 'Sentinel', 'Cypher': 'Sentinel', 'Sage': 'Sentinel', 'Chamber': 'Sentinel', 'Deadlock': 'Sentinel', 'Vyse': 'Sentinel'
}

print("🕷️ Starting Autonomous Spider Harvester...")

# Fetch existing IDs to prevent duplicates
res = supabase.table('ml_spider_matches').select('db_id').execute()
saved_db_ids = {row['db_id'] for row in res.data} if res.data else set()

total_uploaded = 0

for anchor_player in team_roster:
    p_name, p_tag = anchor_player['name'], anchor_player['tag']
    url = f"https://api.henrikdev.xyz/valorant/v3/matches/{REGION}/{urllib.parse.quote(p_name)}/{urllib.parse.quote(p_tag)}?mode=competitive&size=10"
    
    try:
        response = requests.get(url, headers={"Authorization": API_KEY})
        if response.status_code == 200:
            matches = response.json().get('data', [])
            records_to_upload = []
            
            for match in matches:
                metadata = match['metadata']
                match_id = metadata['matchid']
                rounds_played = max(1, metadata['rounds_played'])
                
                # Pre-calculate First Bloods for the whole match
                first_kills_by_round = {}
                for kill in match.get('kills', []):
                    r_num = kill.get('round')
                    if r_num not in first_kills_by_round:
                        first_kills_by_round[r_num] = kill
                
                # SPIDER MANEUVER: Loop through ALL 10 players, not just Presa!
                for p in match['players']['all_players']:
                    player_name = p['name']
                    db_id = f"{match_id}_{player_name}" # Unique ID!
                    
                    if db_id in saved_db_ids or player_name.lower() == "unknown":
                        continue
                        
                    stats = p['stats']
                    agent = p['character']
                    team_color = p['team'].lower()
                    won_match = match.get('teams', {}).get(team_color, {}).get('has_won', False)
                    
                    # Math Calculations
                    kda_ratio = (stats['kills'] + stats['assists']) / max(1, stats['deaths'])
                    acs = stats['score'] / rounds_played
                    adr = p.get('damage_made', 0) / rounds_played
                    
                    hs, bs, ls = stats.get('headshots', 0), stats.get('bodyshots', 0), stats.get('legshots', 0)
                    hs_percent = (hs / (hs + bs + ls) * 100) if (hs + bs + ls) > 0 else 0
                    
                    fb = sum(1 for fk in first_kills_by_round.values() if fk.get('killer_puuid') == p['puuid'])
                    fd = sum(1 for fk in first_kills_by_round.values() if fk.get('victim_puuid') == p['puuid'])
                    
                    rounds_survived = rounds_played - stats['deaths']
                    kast = (min(rounds_played, stats['kills'] + stats['assists'] + rounds_survived) / rounds_played) * 100
                    
                    records_to_upload.append({
                        "db_id": db_id, "match_id": match_id, "player_name": player_name,
                        "agent": agent, "role": agent_roles.get(agent, "Flex"),
                        "rank": p.get('currenttier_patched', 'Unknown'), "map_name": metadata['map'],
                        "win": 1 if won_match else 0, "kills": stats['kills'], "deaths": stats['deaths'],
                        "kda": round(kda_ratio, 2), "acs": round(acs, 2), "kast": round(kast, 1),
                        "adr": int(adr), "hs_percent": int(hs_percent), "fb": fb, "fd": fd
                    })
                    saved_db_ids.add(db_id)
            
            # Push to Cloud
            if records_to_upload:
                supabase.table("ml_spider_matches").upsert(records_to_upload).execute()
                total_uploaded += len(records_to_upload)
                print(f"🕸️ -> Spider caught {len(records_to_upload)} new players from {p_name}'s lobbies.")
                
    except Exception as e:
        print(f"Error checking {p_name}: {e}")
        
    time.sleep(5)

print(f"✅ Spider Run Complete. {total_uploaded} new global rows added to database!")
