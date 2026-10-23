import streamlit as st
import pandas as pd

st.set_page_config(page_title="DFFL Hub", page_icon="🏈", layout="wide")

@st.cache_data
def load_box_scores():
    try:
        return pd.read_excel("espn_fantasy_complete_stats_2017_2026.xlsx", sheet_name="Box_Scores", engine="openpyxl")
    except:
        return pd.DataFrame()

@st.cache_data
def load_data():
    file_path = "FantasyOddsModel2026-v1_2.xlsb"
    df = pd.read_excel(file_path, sheet_name="MatchupHistory", engine="pyxlsb")
    df.columns = df.columns.astype(str).str.strip()
    
    if 'Winner' not in df.columns:
        df = pd.read_excel(file_path, sheet_name="MatchupHistory", engine="pyxlsb", header=1)
        df.columns = df.columns.astype(str).str.strip()
        
    top2_col = next((c for c in df.columns if 'top' in c.lower() and '2' in c.lower()), None)
    bot2_col = next((c for c in df.columns if 'bottom' in c.lower() and '2' in c.lower()), None)
    
    base_cols_win = ['Year', 'Matchup Week', 'Playoff Round', 'Game Type', 'Winner', 'Winner Points', 'Loser', 'Loser Points']
    base_cols_los = ['Year', 'Matchup Week', 'Playoff Round', 'Game Type', 'Loser', 'Loser Points', 'Winner', 'Winner Points']
    
    if top2_col: 
        base_cols_win.append(top2_col)
        base_cols_los.append(top2_col)
    if bot2_col: 
        base_cols_win.append(bot2_col)
        base_cols_los.append(bot2_col)
    
    col_names = ['Season', 'Week', 'Playoff_Round', 'Game_Type_Str', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points']
    if top2_col: col_names.append('Top_2_Game')
    if bot2_col: col_names.append('Bottom_2_Game')
    
    df_winners = df[base_cols_win].copy()
    df_winners.columns = col_names
    
    df_losers = df[base_cols_los].copy()
    df_losers.columns = col_names
    
    games = pd.concat([df_winners, df_losers], ignore_index=True)
    
    games = games.dropna(subset=['Team_Name', 'Actual_Points'])
    games = games[~((games['Actual_Points'] == 0) & (games['Opp_Points'] == 0))]
    games = games[(games['Team_Name'].str.upper() != 'BYE') & (games['Opponent_Team_Name'].str.upper() != 'BYE')]
    
    if 'Playoff_Round' in games.columns:
        games = games[~games['Playoff_Round'].astype(str).str.contains('Consolation|3rd', case=False, na=False)]
    
    games['W'] = (games['Actual_Points'] > games['Opp_Points']).astype(int)
    games['L'] = (games['Actual_Points'] < games['Opp_Points']).astype(int)
    games['T'] = ((games['Actual_Points'] == games['Opp_Points']) & (games['Actual_Points'] > 0)).astype(int)
    
    games['Game_Type'] = games['Game_Type_Str'].apply(lambda x: 1 if str(x).strip() == 'Regular Season' else 2)
    games['Margin'] = (games['Actual_Points'] - games['Opp_Points']).abs().round(2)
    
    games['Season_Num'] = pd.to_numeric(games['Season'], errors='coerce')
    games['Week_Num'] = pd.to_numeric(games['Week'], errors='coerce')
    
    max_scores = games.groupby(['Season', 'Week'])['Actual_Points'].transform('max')
    games['Is_High_Scorer'] = (games['Actual_Points'] == max_scores) & (games['Season_Num'] >= 2019)
    
    return games

def get_detailed_streaks(mgr_df):
    max_w, max_l = 0, 0
    best_w_span, best_l_span = "None", "None"
    
    curr_w, curr_l = 0, 0
    w_start, l_start = None, None
    
    for _, row in mgr_df.iterrows():
        s, w, res = row['Season'], row['Week'], row['Result']
        game_label = f"{str(s).replace('.0','')}, W{w}"
        
        if res == 'W':
            if curr_w == 0: w_start = game_label
            curr_w += 1
            curr_l = 0
            if curr_w > max_w:
                max_w = curr_w
                best_w_span = f"{w_start} to {game_label}" if curr_w > 1 else w_start
        elif res == 'L':
            if curr_l == 0: l_start = game_label
            curr_l += 1
            curr_w = 0
            if curr_l > max_l:
                max_l = curr_l
                best_l_span = f"{l_start} to {game_label}" if curr_l > 1 else l_start
        else:
            curr_w, curr_l = 0, 0
            w_start, l_start = None, None
            
    return max_w, best_w_span, max_l, best_l_span

def get_playoff_outcome(playoff_games_for_season):
    if playoff_games_for_season.empty:
        return ""
    
    rounds = playoff_games_for_season['Playoff_Round'].astype(str).str.strip().str.lower().tolist()
    wins = playoff_games_for_season['W'].tolist()
    
    is_champ, lost_finals, lost_semis, lost_quarters = False, False, False, False
    
    for r, w in zip(rounds, wins):
        if r in ['finals', 'championship']:
            if w == 1: is_champ = True
            else: lost_finals = True
        elif 'semi' in r:
            if w == 0: lost_semis = True
        elif 'quarter' in r:
            if w == 0: lost_quarters = True
            
    if is_champ: return "Champion"
    if lost_finals: return "Lost in Finals"
    if lost_semis: return "Lost in Semifinals"
    if lost_quarters: return "Lost in Quarterfinals"
    
    return "Made Playoffs"

def display_box_score(b_season, b_week, b_team, box_df, games):
    if box_df.empty:
        st.warning("Player data not found. Please ensure 'espn_fantasy_complete_stats_2017_2026.xlsx' is located in this folder.")
        return
        
    b_szn_str = str(b_season).replace('.0', '').strip()
    b_wk_int = int(b_week)
    b_team_clean = str(b_team).strip().lower()
    
    match_mask = (
        (games['Season'].astype(str).str.replace('.0', '', regex=False).str.strip() == b_szn_str) &
        (games['Week_Num'] == b_wk_int) &
        (games['Team_Name'].astype(str).str.strip().str.lower() == b_team_clean)
    )
    game_info = games[match_mask]
    
    if not game_info.empty:
        opp_name = game_info.iloc[0]['Opponent_Team_Name']
        team_pts = game_info.iloc[0]['Actual_Points']
        opp_pts = game_info.iloc[0]['Opp_Points']
    else:
        opp_name = "Unknown"
        team_pts = 0.0
        opp_pts = 0.0
        
    team_roster = box_df[(box_df['Season'].astype(str).str.replace('.0','') == b_szn_str) & (box_df['Week'] == b_wk_int) & (box_df['Team_Name'] == b_team)].copy()
    opp_roster = box_df[(box_df['Season'].astype(str).str.replace('.0','') == b_szn_str) & (box_df['Week'] == b_wk_int) & (box_df['Team_Name'] == opp_name)].copy()
    
    if team_roster.empty and opp_roster.empty:
        st.info(f"No player-level box score data available for {b_szn_str} Week {b_wk_int}.")
        return
        
    def format_roster(df):
        if df.empty: return pd.DataFrame(), pd.DataFrame()
        
        slot_col = 'Slot' if 'Slot' in df.columns else ('Lineup_Slot' if 'Lineup_Slot' in df.columns else 'Position')
        name_col = 'Player_Name' if 'Player_Name' in df.columns else 'Player'
        pts_col = 'Actual_Points' if 'Actual_Points' in df.columns else 'Points'
        
        stat_map = {
            'Passing_Yards': 'Pass Yds', 'Passing_TDs': 'Pass TD', 'Passing_Interceptions': 'INT',
            'Rushing_Yards': 'Rush Yds', 'Rushing_TDs': 'Rush TD',
            'Receptions': 'Rec', 'Receiving_Yards': 'Rec Yds', 'Receiving_TDs': 'Rec TD',
            'Sacks': 'Sacks', 'Defensive_Interceptions': 'Def INT', 'Fumbles_Lost': 'Fum Lost'
        }
        
        def make_stat_blurb(row):
            blurbs = []
            for k, label in stat_map.items():
                if k in df.columns:
                    v = row[k]
                    try:
                        if pd.notnull(v) and float(v) != 0:
                            v_fmt = int(float(v)) if float(v).is_integer() else float(v)
                            blurbs.append(f"{v_fmt} {label}")
                    except: pass
            for c in df.columns:
                if c not in stat_map and c not in [name_col, slot_col, pts_col, 'Season', 'Week', 'Team_Name', 'Opponent_Team_Name']:
                    c_str = str(c).lower()
                    if any(term in c_str for term in ['yard', 'td', 'rec', 'int', 'sack', 'fum']):
                        v = row[c]
                        try:
                            if pd.notnull(v) and float(v) != 0:
                                v_fmt = int(float(v)) if float(v).is_integer() else float(v)
                                lbl = str(c).replace('_', ' ')
                                blurbs.append(f"{v_fmt} {lbl}")
                        except: pass
            return ", ".join(blurbs)
        
        df['Stats'] = df.apply(make_stat_blurb, axis=1)
        slot_order = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4, 'RB/WR/TE': 5, 'FLEX': 5, 'DP': 6, 'D/ST': 6, 'DST': 6, 'K': 7}
        df['sort_val'] = df[slot_col].map(lambda x: slot_order.get(str(x).strip().upper(), 99))
        
        is_bench = df[slot_col].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])
        starters = df[~is_bench].sort_values(['sort_val', pts_col], ascending=[True, False])
        bench = df[is_bench].sort_values(pts_col, ascending=False)
        
        disp_cols = [name_col, slot_col, pts_col, 'Stats']
        start_disp = starters[disp_cols].rename(columns={name_col: 'Player', pts_col: 'Pts'})
        bench_disp = bench[disp_cols].rename(columns={name_col: 'Player', pts_col: 'Pts'})
        
        if not start_disp.empty:
            total_row = pd.DataFrame([{'Player': 'TOTAL', 'Slot': '', 'Pts': start_disp['Pts'].sum(), 'Stats': ''}])
            start_disp = pd.concat([start_disp, total_row], ignore_index=True)
            
        return start_disp, bench_disp

    team_start, team_bench = format_roster(team_roster)
    opp_start, opp_bench = format_roster(opp_roster)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"#### {b_team} ({team_pts:.1f})")
        st.dataframe(team_start, use_container_width=True, hide_index=True)
        if not team_bench.empty:
            st.markdown("**Bench**")
            st.dataframe(team_bench, use_container_width=True, hide_index=True)
    with col_b:
        if opp_name != "Unknown":
            st.markdown(f"#### {opp_name} ({opp_pts:.1f})")
            st.dataframe(opp_start, use_container_width=True, hide_index=True)
            if not opp_bench.empty:
                st.markdown("**Bench**")
                st.dataframe(opp_bench, use_container_width=True, hide_index=True)
        else:
            st.markdown("#### Opponent Matchup Not Found")

st.title("🏈 DFFL History Hub")

try:
    games = load_data()
    box_df = load_box_scores()
except Exception as e:
    st.error(f"Could not load data. Error
    
