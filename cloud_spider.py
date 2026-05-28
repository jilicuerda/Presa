import requests
import urllib.parse
import os
import time
import random
from supabase import create_client, Client

# Securely injected by GitHub Actions
API_KEY = os.environ.get("HENRIK_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
REGION = "eu"

# 1. YOUR ACTUAL TEAM (Will show up on your website frontend)
team_roster = [
    {"name": "PRESA MKULTRA", "tag": "MYKEI"}, {"name": "POGOツ", "tag": "OMEGA"},
    {"name": "Cleezzy", "tag": "Reina"}, {"name": "H0KAGE", "tag": "Nyx"},
    {"name": "Magic Tostada", "tag": "MCY"}, {"name": "Obito", "tag": "ASCK"},
    {"name": "CoRa", "tag": "FGR"}, {"name": "Oby", "tag": "F4W"},
    {"name": "21 Swiss", "tag": "EMEA"}, {"name": "FNC MrFreezer", "tag": "ily"},
    {"name": "IsRasson", "tag": "SSJ"}, {"name": "CriskXK", "tag": "PRESA"},
    {"name": "zaka", "tag": "1734"}
]

# 2. HIGH ELO DATA SEEDS (Purely used for AI training data background, won't show on frontend)
# Put any Radiant / Immortal / Ascendant players you want to harvest here!
high_elo_seeds = [
    {"name": "Boaster", "tag": "FNC"},
    {"name": "ScreaM", "tag": "KCORP"},
    {"name": "VASQUEZ", "tag": "0000"},
    {"name": "sunfloweR", "tag": "047"},
    {"name": "CB10", "tag": "Aegon"},
    {"name": "Donatell0", "tag": "GOAT"},
    {"name": "danifluchi", "tag": "dani2"},
    {"name": "XLG Merced", "tag": "0000"},
    {"name": "Buk Hy 蘭", "tag": "gift"},
    {"name": "尺ezzy", "tag": "0811"},
    {"name": "el wiki coino", "tag": "GDN"},
    {"name": "Borryng", "tag": "SPAIN"},
    {"name": "karizma", "tag": "kariz"},
    
    # Add more high-elo tracker names/tags here as you find them
]

roster_names = [p['name'].lower() for p in team_roster]
seed_names = [p['name'].lower() for p in high_elo_seeds]

agent_roles = {
    'Jett': 'Duelist', 'Reyna': 'Duelist', 'Raze': 'Duelist', 'Phoenix': 'Duelist', 'Neon': 'Duelist', 'Yoru': 'Duelist', 'Iso': 'Duelist',
    'Omen': 'Controller', 'Brimstone': 'Controller', 'Viper': 'Controller', 'Astra': 'Controller', 'Harbor': 'Controller', 'Clove': 'Controller',
    'Sova': 'Initiator', 'Breach': 'Initiator', 'Skye': 'Initiator', 'KAY/O': 'Initiator', 'Kayo': 'Initiator', 'Fade': 'Initiator', 'Gekko': 'Initiator',
    'Killjoy': 'Sentinel', 'Cypher': 'Sentinel', 'Sage': 'Sentinel', 'Chamber': 'Sentinel', 'Deadlock': 'Sentinel', 'Vyse': 'Sentinel'
}

print("🕷️ Starting Full Deep Spider with High-Elo Engine...")

res = supabase.table('ml_spider_matches').select('db_id').execute()
saved_db_ids = {row['db_id'] for row in res.data} if res.data else set()

total_uploaded = 0
strangers_found = set()

# Combine both groups for the match discovery layer
all_anchors = team_roster + high_elo_seeds

# --- PHASE 1: Scan Anchors (Team + High Elo Seeds) ---
print("-> PHASE 1: Scanning Anchors for Match Discovery...")
for anchor in all_anchors:
    p_name, p_tag = anchor['name'], anchor['tag']
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
                
                first_kills_by_round = {}
                for kill in match.get('kills', []):
                    r_num = kill.get('round')
                    if r_num not in first_kills_by_round:
                        first_kills_by_round[r_num] = kill
                
                for p in match['players']['all_players']:
                    player_name = p['name']
                    player_tag = p['tag']
                    db_id = f"{match_id}_{player_name}" 
                    
                    # Gather strangers for Phase 2 deep scanning
                    if player_name.lower() not in roster_names and player_name.lower() not in seed_names and player_name.lower() != "unknown":
                        strangers_found.add((player_name, player_tag))

                    if db_id in saved_db_ids or player_name.lower() == "unknown":
                        continue
                        
                    stats = p['stats']
                    agent = p['character']
                    team_color = p['team'].lower()
                    won_match = match.get('teams', {}).get(team_color, {}).get('has_won', False)
                    
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
            
            if records_to_upload:
                supabase.table("ml_spider_matches").upsert(records_to_upload).execute()
                total_uploaded += len(records_to_upload)
                
    except Exception as e:
        print(f"Error checking {p_name}: {e}")
        
    time.sleep(5)

print(f"-> Phase 1 Complete. Baseline rows synced.")

# --- PHASE 2: Deep Scan Every Rival ---
strangers_list = list(strangers_found)
total_strangers = len(strangers_list)
print(f"\n-> PHASE 2: Scanning {total_strangers} unique rivals found across all skill brackets.")

deep_rows_added = 0

for index, (s_name, s_tag) in enumerate(strangers_list, 1):
    time.sleep(7) # Safe execution gap
    url = f"https://api.henrikdev.xyz/valorant/v3/matches/{REGION}/{urllib.parse.quote(s_name)}/{urllib.parse.quote(s_tag)}?mode=competitive&size=10"
    
    try:
        response = requests.get(url, headers={"Authorization": API_KEY})
        if response.status_code == 200:
            matches = response.json().get('data', [])
            records_to_upload = []
            
            for match in matches:
                metadata = match['metadata']
                match_id = metadata['matchid']
                rounds_played = max(1, metadata['rounds_played'])
                
                first_kills_by_round = {}
                for kill in match.get('kills', []):
                    r_num = kill.get('round')
                    if r_num not in first_kills_by_round:
                        first_kills_by_round[r_num] = kill
                
                for p in match['players']['all_players']:
                    if p['name'] == s_name:
                        db_id = f"{match_id}_{s_name}"
                        
                        if db_id in saved_db_ids:
                            continue
                            
                        stats = p['stats']
                        agent = p['character']
                        team_color = p['team'].lower()
                        won_match = match.get('teams', {}).get(team_color, {}).get('has_won', False)
                        
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
                            "db_id": db_id, "match_id": match_id, "player_name": s_name,
                            "agent": agent, "role": agent_roles.get(agent, "Flex"),
                            "rank": p.get('currenttier_patched', 'Unknown'), "map_name": metadata['map'],
                            "win": 1 if won_match else 0, "kills": stats['kills'], "deaths": stats['deaths'],
                            "kda": round(kda_ratio, 2), "acs": round(acs, 2), "kast": round(kast, 1),
                            "adr": int(adr), "hs_percent": int(hs_percent), "fb": fb, "fd": fd
                        })
                        saved_db_ids.add(db_id)
            
            if records_to_upload:
                supabase.table("ml_spider_matches").upsert(records_to_upload).execute()
                deep_rows_added += len(records_to_upload)
            print(f"   [{index}/{total_strangers}] Processed rival: {s_name}")
    except Exception as e:
        print(f"   [{index}/{total_strangers}] Skipped profile: {s_name}")

print(f"\n✅ Pipeline Complete. Collected {total_uploaded + deep_rows_added} clean data tracks.")
