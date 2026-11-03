import streamlit as st
from data_loader import load_data, load_box_scores, load_rs_rankings, get_game_top_scorers
from tabs import (
    franchise,
    schedule,
    box_scores,
    matchups,
    standings,
    records,
    player_scoring,
)

st.set_page_config(page_title="DFFL Hub", page_icon="🏈", layout="wide")
st.title("🏈 DFFL History Hub")

# 1. Global Data Ingestion
games = load_data()
box_df = load_box_scores()
game_top_map = get_game_top_scorers(box_df)

teams = sorted(games['Team_Name'].dropna().unique().tolist())
teams_no_cam = sorted([t for t in teams if str(t).strip().upper() != 'CAM'])
seasons_list = sorted(
    games['Season'].dropna().unique().tolist(),
    key=lambda x: int(x) if str(x).isdigit() else 0,
    reverse=True
)
completed_playoff_seasons = set(
    games[games['Game_Type'] == 2]['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().unique()
)
# Passing games enables automatic fallback calculation of regular season standings
rs_ranks_df = load_rs_rankings("FantasyOddsModel2026-v1_2.xlsb", teams, games)

# 2. Sequential Tab Declarations
tab1, tab5, tab6, tab2, tab3, tab4, tab_player = st.tabs([
    "Franchise", "Schedule", "Box Scores", "Matchups", "Standings", "Records", "Detailed Player Scoring"
])

# 3. Mount Modular Views
with tab1:
    franchise.render(games, box_df, rs_ranks_df, completed_playoff_seasons, teams, seasons_list)

with tab5:
    schedule.render(games, box_df, game_top_map, teams, seasons_list)

with tab6:
    box_scores.render(games, box_df, teams, seasons_list)

with tab2:
    matchups.render(games, box_df, game_top_map, teams)

with tab3:
    standings.render(games, seasons_list)

with tab4:
    records.render(games, box_df, rs_ranks_df, completed_playoff_seasons, teams, teams_no_cam)

with tab_player:
    player_scoring.render(games, box_df, teams, seasons_list)
    
