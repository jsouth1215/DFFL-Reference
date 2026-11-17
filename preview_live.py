import pandas as pd
from espn_api.football import League
import app
import update_weekly
import get_recap

# 1. Initialize API
league = League(league_id=update_weekly.LEAGUE_ID, year=2026, espn_s2=update_weekly.ESPN_S2, swid=update_weekly.SWID)

# 2. Fetch Box Scores (This endpoint stays active during rollover!)
bs = league.box_scores(10)

live_games = []
live_boxes = []

# 3. Build the final team scores and player stats manually
for m in bs:
    if not m.home_team or not m.away_team: continue
    
    t1 = update_weekly.TEAM_DICT.get(m.home_team.team_id, m.home_team.team_name)
    t2 = update_weekly.TEAM_DICT.get(m.away_team.team_id, m.away_team.team_name)
    
    s1 = m.home_score
    s2 = m.away_score
    
    is_t1_w = s1 > s2
    margin = abs(s1 - s2)
    
    live_games.append({'Season': 2026, 'Week': 10, 'Game_Type': 1, 'Team_Name': t1, 'Opponent_Team_Name': t2, 'Actual_Points': s1, 'Opp_Points': s2, 'W': 1 if is_t1_w else 0, 'L': 0 if is_t1_w else 1, 'T': 0, 'Margin': margin})
    live_games.append({'Season': 2026, 'Week': 10, 'Game_Type': 1, 'Team_Name': t2, 'Opponent_Team_Name': t1, 'Actual_Points': s2, 'Opp_Points': s1, 'W': 0 if is_t1_w else 1, 'L': 1 if is_t1_w else 0, 'T': 0, 'Margin': margin})
    
    for tm_obj, lineup in [(m.home_team, m.home_lineup), (m.away_team, m.away_lineup)]:
        tm_name = update_weekly.TEAM_DICT.get(tm_obj.team_id, tm_obj.team_name)
        for p in lineup:
            live_boxes.append({'Season': 2026, 'Week': 10, 'Team_Name': tm_name, 'Player_Name': p.name, 'Slot': p.slot_position, 'Pos': p.position, 'Actual_Points': p.points})

if not live_games:
    print("ESPN returned empty box scores.")
else:
    df_live_games = pd.DataFrame(live_games)
    df_live_boxes = pd.DataFrame(live_boxes)

    # 4. Inject live data into app.py's memory, wiping out any incomplete Week 10 ghosts
    games = app.games.copy()
    box = app.box_df.copy()
    
    games = games[~((games['Season'].astype(str).str.contains('2026')) & (pd.to_numeric(games['Week'], errors='coerce') == 10))]
    box = box[~((box['Season'].astype(str).str.contains('2026')) & (pd.to_numeric(box['Week'], errors='coerce') == 10))]
    
    app.games = pd.concat([games, df_live_games], ignore_index=True)
    app.box_df = pd.concat([box, df_live_boxes], ignore_index=True)

    print("\n⚡ Bypassing ESPN Rollover: Injecting Live Final Scores into Memory...\n")
    
    # 5. Run the Recap!
    get_recap.generate_recap(szn="2026", wk=10)
