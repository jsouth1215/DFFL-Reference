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
def get_game_top_scorers(box_df):
    if box_df.empty:
        return {}
    slot_c = 'Slot' if 'Slot' in box_df.columns else ('Lineup_Slot' if 'Lineup_Slot' in box_df.columns else 'Position')
    name_c = 'Player_Name' if 'Player_Name' in box_df.columns else 'Player'
    pts_c = 'Actual_Points' if 'Actual_Points' in box_df.columns else 'Points'
    
    b_clean = box_df.copy()
    b_clean['Season_Str'] = b_clean['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    b_clean['Week_Num'] = pd.to_numeric(b_clean['Week'], errors='coerce').fillna(0).astype(int)
    b_clean['Team_Str'] = b_clean['Team_Name'].astype(str).str.strip()
    b_clean[pts_c] = pd.to_numeric(b_clean[pts_c], errors='coerce').fillna(0)
    
    is_starter = ~b_clean[slot_c].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])
    starters_box = b_clean[is_starter]
    
    top_starters = starters_box.sort_values(pts_c, ascending=False).drop_duplicates(subset=['Season_Str', 'Week_Num', 'Team_Str'])
    top_starters['Player_Label'] = top_starters.apply(lambda r: f"{r[name_c]} ({r[pts_c]:.1f})", axis=1)
    
    return dict(zip(
        zip(top_starters['Season_Str'], top_starters['Week_Num'], top_starters['Team_Str']),
        top_starters['Player_Label']
    ))

@st.cache_data
def load_rs_rankings(file_path, teams_list):
    try:
        df = pd.read_excel(file_path, sheet_name="All Time W-L", engine="pyxlsb", header=None)
        
        year_row_idx = None
        team_col_idx = None
        
        for i, row in df.iterrows():
            years_in_row = sum(1 for x in row if str(x).replace('.0','').strip().isdigit() and 2010 < int(str(x).replace('.0','').strip()) < 2030)
            if years_in_row >= 3:
                year_row_idx = i
                break
                
        for j in df.columns:
            matches = df[j].astype(str).apply(lambda x: x.strip() in teams_list).sum()
            if matches >= 5:
                team_col_idx = j
                break
                
        if year_row_idx is not None and team_col_idx is not None:
            headers = df.iloc[year_row_idx]
            data = df.iloc[year_row_idx+1:].copy()
            data.columns = headers
            
            data = data.rename(columns={headers[team_col_idx]: 'Team_Name'})
            year_cols = [c for c in data.columns if str(c).replace('.0','').strip().isdigit() and 2010 < int(str(c).replace('.0','').strip()) < 2030]
            
            ranks_df = data[['Team_Name'] + year_cols].copy()
            ranks_melt = ranks_df.melt(id_vars='Team_Name', var_name='Season', value_name='RS_Rank')
            ranks_melt['Season'] = ranks_melt['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            ranks_melt['RS_Rank'] = pd.to_numeric(ranks_melt['RS_Rank'], errors='coerce')
            ranks_melt = ranks_melt.dropna(subset=['RS_Rank'])
            ranks_melt['Team_Name'] = ranks_melt['Team_Name'].astype(str).str.strip()
            return ranks_melt
    except:
        pass
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
    
    games['Season'] = games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    games = games[games['Team_Name'].str.upper() != 'BYE']
    
    def map_game_type(row):
        gt = str(row.get('Game_Type_Str', '')).strip()
        pr = str(row.get('Playoff_Round', '')).lower()
        opp = str(row.get('Opponent_Team_Name', '')).strip().upper()
        
        if opp == 'BYE': return 4 
        if gt == 'Regular Season': return 1 
        if 'consolation' in pr or '3rd' in pr: return 3 
        return 2 

    games['Game_Type'] = games.apply(map_game_type, axis=1)
    
    games['Opp_Points'] = pd.to_numeric(games['Opp_Points'], errors='coerce').fillna(0)
    
    games['W'] = (games['Actual_Points'] > games['Opp_Points']).astype(int)
    games['L'] = (games['Actual_Points'] < games['Opp_Points']).astype(int)
    games['T'] = ((games['Actual_Points'] == games['Opp_Points']) & (games['Actual_Points'] > 0)).astype(int)
    
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
        (games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == b_szn_str) &
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
        
    team_roster = box_df[(box_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == b_szn_str) & (box_df['Week'] == b_wk_int) & (box_df['Team_Name'] == b_team)].copy()
    opp_roster = box_df[(box_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == b_szn_str) & (box_df['Week'] == b_wk_int) & (box_df['Team_Name'] == opp_name)].copy()
    
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
    game_top_map = get_game_top_scorers(box_df)
    
    teams = sorted(games['Team_Name'].dropna().unique().tolist())
    seasons_list = sorted(
        games['Season'].dropna().unique().tolist(),
        key=lambda x: int(x) if str(x).isdigit() else 0,
        reverse=True
    )
    
    rs_ranks_df = load_rs_rankings("FantasyOddsModel2026-v1_2.xlsb", teams)
    
    if rs_ranks_df.empty:
        reg = games[games['Game_Type'] == 1]
        szn_st = reg.groupby(['Season', 'Team_Name']).agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum'), PF=('Actual_Points', 'sum')).reset_index()
        szn_st['Win %'] = (szn_st['W'] / (szn_st['W'] + szn_st['L'] + szn_st['T'])).fillna(0)
        szn_st = szn_st.sort_values(['Season', 'Win %', 'PF'], ascending=[False, False, False])
        szn_st['RS_Rank'] = szn_st.groupby('Season').cumcount() + 1
        rs_ranks_df = szn_st[['Season', 'Team_Name', 'RS_Rank']].copy()
        
    rs_ranks_df['Season'] = rs_ranks_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

except Exception as e:
    st.error(f"Could not load data. Error: {e}")
    st.stop()

tab1, tab5, tab6, tab2, tab3, tab4 = st.tabs(["Franchise", "Schedule", "Box Scores", "Matchups", "Standings", "Records"])

with tab1:
    selected_team = st.selectbox("Select Manager", teams, label_visibility="collapsed")
    mgr_games = games[games['Team_Name'] == selected_team].sort_values(['Season_Num', 'Week_Num']).copy()
    
    mgr_games['Result'] = mgr_games.apply(lambda x: 'W' if x['W'] else ('L' if x['L'] else 'T'), axis=1)
    
    reg_season = mgr_games[mgr_games['Game_Type'] == 1]
    playoffs = mgr_games[mgr_games['Game_Type'] == 2]
    
    tw, tl, tt = reg_season['W'].sum(), reg_season['L'].sum(), reg_season['T'].sum()
    win_pct = tw / (tw + tl + tt) if (tw + tl + tt) > 0 else 0.0
    win_pct_str = f"{win_pct:.3f}".replace("0.", ".", 1) if win_pct < 1 else f"{win_pct:.3f}"
    
    if not mgr_games.empty:
        high_row = mgr_games.loc[mgr_games['Actual_Points'].idxmax()]
        high_score_str = f"{high_row['Actual_Points']:.1f} ({str(high_row['Season']).replace('.0','')}, W{high_row['Week']})"
    else:
        high_score_str = "N/A"
        
    comp_games = mgr_games[mgr_games['Game_Type'].isin([1, 2])]
    if not comp_games.empty:
        low_row = comp_games.loc[comp_games['Actual_Points'].idxmin()]
        low_score_str = f"{low_row['Actual_Points']:.1f} ({str(low_row['Season']).replace('.0','')}, W{low_row['Week']})"
        
        valid_opp_games = comp_games[comp_games['Opponent_Team_Name'].str.upper() != 'CAM']
        if not valid_opp_games.empty:
            opp_stats = valid_opp_games.groupby('Opponent_Team_Name').agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum')).reset_index()
            opp_stats['Games'] = opp_stats['W'] + opp_stats['L'] + opp_stats['T']
            opp_stats = opp_stats[opp_stats['Games'] > 0]
            
            if not opp_stats.empty:
                opp_stats['Win %'] = opp_stats['W'] / opp_stats['Games']
                
                max_wp = opp_stats['Win %'].max()
                easiest_df = opp_stats[opp_stats['Win %'] == max_wp]
                easiest_names = ", ".join(easiest_df['Opponent_Team_Name'].tolist())
                easiest_str = f"{easiest_names} ({max_wp:.3f})".replace("0.", ".", 1) if max_wp < 1 else f"{easiest_names} ({max_wp:.3f})"
                
                min_wp = opp_stats['Win %'].min()
                toughest_df = opp_stats[opp_stats['Win %'] == min_wp]
                toughest_names = ", ".join(toughest_df['Opponent_Team_Name'].tolist())
                toughest_str = f"{toughest_names} ({min_wp:.3f})".replace("0.", ".", 1) if min_wp < 1 else f"{toughest_names} ({min_wp:.3f})"
            else:
                easiest_str = "N/A"
                toughest_str = "N/A"
        else:
            easiest_str = "N/A"
            toughest_str = "N/A"
    else:
        low_score_str = "N/A"
        easiest_str = "N/A"
        toughest_str = "N/A"
    
    pw, pl, pt = playoffs['W'].sum(), playoffs['L'].sum(), playoffs['T'].sum()
    
    is_champ = playoffs['Playoff_Round'].astype(str).str.strip().str.lower().isin(['finals', 'championship'])
    champs = playoffs[is_champ & (playoffs['W'] == 1)]
    champ_years = sorted([str(s).replace('.0', '') for s in champs['Season'].unique()])
    champ_str = f"{len(champ_years)} ({', '.join(champ_years)})" if champ_years else "0"
    
    high_scorer_count = mgr_games['Is_High_Scorer'].sum()
    
    longest_w, w_span, longest_l, l_span = get_detailed_streaks(mgr_games[mgr_games['Game_Type'].isin([1, 2])])
    
    rs_team = rs_ranks_df[rs_ranks_df['Team_Name'] == selected_team]
    playoff_apps = 0
    playoff_byes = 0
    
    for _, row in rs_team.iterrows():
        szn_str = str(row['Season']).strip()
        if not szn_str.isdigit(): continue
        szn = int(szn_str)
        rank = float(row['RS_Rank'])
        
        if pd.isna(rank): continue
        if szn == 2017 and rank <= 4:
            playoff_apps += 1
        elif szn > 2017 and rank <= 6:
            playoff_apps += 1
            
        if szn >= 2018 and rank <= 2:
            playoff_byes += 1
            
    top_player_str = "N/A"
    top_qb_by_szn = {}
    top_rb_by_szn = {}
    top_wr_by_szn = {}
    top_te_by_szn = {}
    
    if not box_df.empty:
        slot_c = 'Slot' if 'Slot' in box_df.columns else ('Lineup_Slot' if 'Lineup_Slot' in box_df.columns else 'Position')
        name_c = 'Player_Name' if 'Player_Name' in box_df.columns else 'Player'
        pts_c = 'Actual_Points' if 'Actual_Points' in box_df.columns else 'Points'
        pos_c = 'Position' if 'Position' in box_df.columns else ('Pos' if 'Pos' in box_df.columns else slot_c)
        
        if slot_c in box_df.columns and name_c in box_df.columns and pts_c in box_df.columns:
            eligible_games = games[games['Game_Type'].isin([1, 2, 4])][['Season', 'Week', 'Team_Name']].copy()
            eligible_games['Season'] = eligible_games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            eligible_games['Week'] = pd.to_numeric(eligible_games['Week'], errors='coerce').fillna(0).astype(int)
            eligible_games['Team_Name'] = eligible_games['Team_Name'].astype(str).str.strip()
            
            box_eligible = box_df[box_df['Team_Name'] == selected_team].copy()
            box_eligible['Season'] = box_eligible['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            box_eligible['Week'] = pd.to_numeric(box_eligible['Week'], errors='coerce').fillna(0).astype(int)
            box_eligible['Team_Name'] = box_eligible['Team_Name'].astype(str).str.strip()
            
            is_starter = ~box_eligible[slot_c].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])
            starters_df = box_eligible[is_starter]
            
            counted_box = pd.merge(starters_df, eligible_games, on=['Season', 'Week', 'Team_Name'], how='inner')
            
            if not counted_box.empty:
                counted_box[pts_c] = pd.to_numeric(counted_box[pts_c], errors='coerce').fillna(0)
                counted_box['Clean_Pos'] = counted_box[pos_c].astype(str).str.strip().str.upper()
                
                player_totals = counted_box.groupby(name_c)[pts_c].sum().reset_index()
                if not player_totals.empty:
                    top_player_row = player_totals.sort_values(pts_c, ascending=False).iloc[0]
                    top_player_str = f"{top_player_row[name_c]} ({top_player_row[pts_c]:,.1f} pts)"
                
                def get_top_by_pos(target_pos):
                    pos_df = counted_box[counted_box['Clean_Pos'] == target_pos]
                    if pos_df.empty:
                        return {}
                    szn_pts = pos_df.groupby(['Season', name_c])[pts_c].sum().reset_index()
                    szn_pts = szn_pts.sort_values(['Season', pts_c], ascending=[True, False])
                    top_per_szn = szn_pts.drop_duplicates(subset=['Season'], keep='first')
                    return dict(zip(
                        top_per_szn['Season'],
                        top_per_szn.apply(lambda r: f"{r[name_c]} ({r[pts_c]:,.1f})", axis=1)
                    ))
                
                top_qb_by_szn = get_top_by_pos('QB')
                top_rb_by_szn = get_top_by_pos('RB')
                top_wr_by_szn = get_top_by_pos('WR')
                top_te_by_szn = get_top_by_pos('TE')
            
    st.markdown(f"**Championships:** {champ_str}")
    st.markdown(f"**Reg. Season Record:** {tw}-{tl}-{tt} ({win_pct_str})")
    st.markdown(f"**Playoff Record:** {pw}-{pl}-{pt}")
    st.markdown(f"**Playoff Appearances:** {playoff_apps}")
    st.markdown(f"**Playoff Byes:** {playoff_byes}")
    st.markdown(f"**Weekly Bags Won:** {high_scorer_count}")
    st.markdown(f"**Highest Game:** {high_score_str}")
    st.markdown(f"**Lowest Game:** {low_score_str}")
    st.markdown(f"**All-Time Top Scorer:** {top_player_str}")
    st.markdown(f"**Easiest Opponent:** {easiest_str}")
    st.markdown(f"**Toughest Opponent:** {toughest_str}")
    st.markdown(f"**Longest Win Streak:** {longest_w} games ({w_span})")
    st.markdown(f"**Longest Losing Streak:** {longest_l} games ({l_span})")
    st.divider()
    
    st.write("### Season-by-Season (Regular Season)")
    szn_stats = reg_season.groupby('Season').agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum'), PF=('Actual_Points', 'sum'), PA=('Opp_Points', 'sum')).reset_index()
    szn_stats['Win %'] = (szn_stats['W'] / (szn_stats['W'] + szn_stats['L'] + szn_stats['T'])).fillna(0)
    szn_stats['Win %'] = szn_stats['Win %'].apply(lambda x: f"{x:.3f}".replace("0.", ".", 1) if x < 1 else f"{x:.3f}")
    
    szn_stats['Games'] = szn_stats['W'] + szn_stats['L'] + szn_stats['T']
    szn_stats['PF/G'] = (szn_stats['PF'] / szn_stats['Games']).apply(lambda x: f"{x:.1f}")
    szn_stats['PA/G'] = (szn_stats['PA'] / szn_stats['Games']).apply(lambda x: f"{x:.1f}")
    
    szn_stats['PF'] = szn_stats['PF'].astype(int)
    szn_stats['PA'] = szn_stats['PA'].astype(int)
    
    all_reg = games[games['Game_Type'] == 1]
    pf_totals = all_reg.groupby(['Season', 'Team_Name']).agg(Actual_Points=('Actual_Points', 'sum'), Opp_Points=('Opp_Points', 'sum')).reset_index()
    pf_totals['PF_Rank'] = pf_totals.groupby('Season')['Actual_Points'].rank(ascending=False, method='min').astype(int)
    pf_totals['PA_Rank'] = pf_totals.groupby('Season')['Opp_Points'].rank(ascending=False, method='min').astype(int)
    
    pf_totals_team = pf_totals[pf_totals['Team_Name'] == selected_team][['Season', 'PF_Rank', 'PA_Rank']]
    szn_stats = pd.merge(szn_stats, pf_totals_team, on='Season', how='left')
    
    outcomes = []
    for s in szn_stats['Season']:
        s_playoffs = playoffs[playoffs['Season'] == s]
        outcomes.append(get_playoff_outcome(s_playoffs))
    szn_stats['Playoff Outcome'] = outcomes
    
    szn_stats['Season'] = szn_stats['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    mgr_games['Season_Str'] = mgr_games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    bags_per_szn = mgr_games.groupby('Season_Str')['Is_High_Scorer'].sum().to_dict()
    szn_stats['Weekly Bags'] = szn_stats['Season'].map(bags_per_szn).fillna(0).astype(int)
    
    rs_team_format = rs_team[['Season', 'RS_Rank']].copy()
    rs_team_format['Season'] = rs_team_format['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    szn_stats = pd.merge(szn_stats, rs_team_format, on='Season', how='left')
    
    szn_stats['Standings Finish'] = szn_stats['RS_Rank'].apply(
        lambda x: f"{int(x)}{'th' if 11 <= int(x) % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(int(x) % 10, 'th')}" if pd.notnull(x) else ""
    )
    
    szn_stats['Top QB'] = szn_stats['Season'].map(top_qb_by_szn).fillna("")
    szn_stats['Top RB'] = szn_stats['Season'].map(top_rb_by_szn).fillna("")
    szn_stats['Top WR'] = szn_stats['Season'].map(top_wr_by_szn).fillna("")
    szn_stats['Top TE'] = szn_stats['Season'].map(top_te_by_szn).fillna("")
    
    display_cols = [
        'Season', 'W', 'L', 'Win %', 'Standings Finish',
        'PF', 'PF/G', 'PF Rank', 'PA', 'PA/G', 'PA Rank',
        'Playoff Outcome', 'Weekly Bags',
        'Top QB', 'Top RB', 'Top WR', 'Top TE'
    ]
    display_df = szn_stats.rename(columns={'PF_Rank': 'PF Rank', 'PA_Rank': 'PA Rank'})[display_cols].sort_values('Season', ascending=False)
    
    styled_html = display_df.style.hide(axis='index').set_properties(**{
        'text-align': 'center',
        'padding': '6px 8px',
        'border': '1px solid #e6e6e6',
        'white-space': 'nowrap'
    }).set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center'), ('padding', '6px 8px'), ('border', '1px solid #e6e6e6'), ('white-space', 'nowrap')]},
        {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]}
    ]).to_html()
    
    st.markdown(styled_html, unsafe_allow_html=True)
    
    st.divider()
    st.write("### Playoff Game Log")
    display_playoffs = playoffs.sort_values(['Season_Num', 'Week_Num'], ascending=[False, False])
    if not display_playoffs.empty:
        display_playoffs['Season'] = display_playoffs['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        display_playoffs['Score'] = display_playoffs['Actual_Points'].round(1).astype(str) + " - " + display_playoffs['Opp_Points'].round(1).astype(str)
        
        po_display_df = display_playoffs[['Season', 'Week', 'Playoff_Round', 'Opponent_Team_Name', 'Result', 'Score']].rename(columns={'Opponent_Team_Name': 'Opponent', 'Playoff_Round': 'Round'})
        
        po_styled_html = po_display_df.style.hide(axis='index').set_properties(**{
            'text-align': 'center',
            'padding': '8px',
            'border': '1px solid #e6e6e6'
        }).set_table_styles([
            {'selector': 'th', 'props': [('text-align', 'center'), ('padding', '8px'), ('border', '1px solid #e6e6e6')]},
            {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]}
        ]).to_html()
        
        st.markdown(po_styled_html, unsafe_allow_html=True)
        
        display_playoffs['Game_Label'] = display_playoffs['Season'] + " Week " + display_playoffs['Week'].astype(str) + " vs " + display_playoffs['Opponent_Team_Name']
        view_po_wk = st.selectbox("Select Playoff Game to View Box Score:", ["Select..."] + display_playoffs['Game_Label'].tolist(), key="po_box")
        if view_po_wk != "Select...":
            po_row = display_playoffs[display_playoffs['Game_Label'] == view_po_wk].iloc[0]
            display_box_score(po_row['Season'], po_row['Week'], selected_team, box_df, games)
    else:
        st.write("No playoff appearances on record.")

with tab5:
    col1, col2 = st.columns(2)
    sched_season = col1.selectbox("Season", seasons_list, key='sched_szn')
    sched_team = col2.selectbox("Manager", teams, key='sched_team')
    
    sched = games[(games['Season'] == str(sched_season)) & (games['Team_Name'] == sched_team)].sort_values(['Game_Type', 'Week_Num']).copy()
    if not sched.empty:
        type_mapping = {1: 'Regular Season', 2: 'Playoffs', 3: 'Consolation', 4: 'Playoff Bye'}
        sched['Type'] = sched['Game_Type'].map(type_mapping)
        
        sched['Result'] = sched.apply(lambda x: 'BYE' if x['Game_Type'] == 4 else ('W' if x['W'] else ('L' if x['L'] else 'T')), axis=1)
        
        team_score_col = f'{sched_team} Score'
        opp_score_col = 'Opponent Score'
        
        sched[team_score_col] = sched['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        sched[opp_score_col] = sched.apply(
            lambda x: f"{float(x['Opp_Points']):.1f}" if x['Game_Type'] != 4 else "-", axis=1
        )
        
        def calc_rel_margin(r):
            if r['Game_Type'] == 4:
                return "-"
            diff = r['Actual_Points'] - r['Opp_Points']
            if diff > 0:
                return f"+{diff:.1f}"
            elif diff < 0:
                return f"{diff:.1f}"
            else:
                return "0.0"
                
        sched['Margin'] = sched.apply(calc_rel_margin, axis=1)
        sched['Opponent'] = sched['Opponent_Team_Name']
        
        s_szn_str = str(sched_season).replace('.0', '').strip()
        sched['Team_Str'] = sched['Team_Name'].astype(str).str.strip()
        sched['Opp_Str'] = sched['Opponent_Team_Name'].astype(str).str.strip()
        sched['Week_Num_Int'] = pd.to_numeric(sched['Week'], errors='coerce').fillna(0).astype(int)
        
        sched[f'{sched_team} Top Scorer'] = sched.apply(
            lambda r: game_top_map.get((s_szn_str, r['Week_Num_Int'], r['Team_Str']), ""), axis=1
        )
        sched['Opponent Top Scorer'] = sched.apply(
            lambda r: game_top_map.get((s_szn_str, r['Week_Num_Int'], r['Opp_Str']), "") if r['Opp_Str'].upper() != 'BYE' else "", axis=1
        )
        
        cols = ['Week', 'Type', 'Opponent', 'Result', team_score_col, opp_score_col, 'Margin', f'{sched_team} Top Scorer', 'Opponent Top Scorer']
        disp_sched = sched[cols]
        
        def highlight_sched_winners(row):
            styles = ['' for _ in row.index]
            col_team_idx = row.index.get_loc(team_score_col)
            col_opp_idx = row.index.get_loc(opp_score_col)
            if row['Result'] == 'W':
                styles[col_team_idx] = 'font-weight: bold;'
            elif row['Result'] == 'L':
                styles[col_opp_idx] = 'font-weight: bold;'
            return styles
        
        sched_styled_html = disp_sched.style.hide(axis='index').apply(highlight_sched_winners, axis=1).set_properties(**{
            'text-align': 'center',
            'padding': '6px 8px',
            'border': '1px solid #e6e6e6',
            'white-space': 'nowrap'
        }).set_table_styles([
            {'selector': 'th', 'props': [('text-align', 'center'), ('padding', '6px 8px'), ('border', '1px solid #e6e6e6'), ('white-space', 'nowrap')]},
            {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]}
        ]).to_html()
        
        st.markdown(sched_styled_html, unsafe_allow_html=True)
        
        view_sch_wk = st.selectbox("Select Week to View Box Score:", ["Select..."] + sched['Week'].unique().tolist(), key="sch_box")
        if view_sch_wk != "Select...":
            display_box_score(sched_season, view_sch_wk, sched_team, box_df, games)
    else:
        st.write("No schedule found.")

with tab6:
    if box_df.empty:
        st.warning("Player data not found. Please ensure 'espn_fantasy_complete_stats_2017_2026.xlsx' is located in this folder to view box scores.")
    else:
        c1, c2, c3 = st.columns(3)
        b_season = c1.selectbox("Season", sorted(box_df['Season'].dropna().unique().tolist(), reverse=True), key="b_szn")
        avail_weeks = sorted(box_df[box_df['Season'] == b_season]['Week'].dropna().unique().tolist())
        b_week = c2.selectbox("Week", avail_weeks, key="b_wk")
        avail_teams = sorted(box_df[(box_df['Season'] == b_season) & (box_df['Week'] == b_week)]['Team_Name'].dropna().unique().tolist())
        b_team = c3.selectbox("Manager", avail_teams, key="b_tm")
        
        if b_team:
            display_box_score(b_season, b_week, b_team, box_df, games)

with tab2:
    col1, col2 = st.columns(2)
    team_a = col1.selectbox("Team A", teams)
    team_b = col2.selectbox("Team B", [t for t in teams if t != team_a])
    
    h2h_games = games[(games['Team_Name'] == team_a) & (games['Opponent_Team_Name'] == team_b) & (games['Game_Type'].isin([1, 2]))].copy()
    if not h2h_games.empty:
        w, l, t = h2h_games['W'].sum(), h2h_games['L'].sum(), h2h_games['T'].sum()
        
        po_h2h = h2h_games[h2h_games['Game_Type'] == 2]
        pw, pl, pt = po_h2h['W'].sum(), po_h2h['L'].sum(), po_h2h['T'].sum()
        
        st.write(f"### {team_a} vs. {team_b}")
        if w > l:
            st.markdown(f"**{team_a} leads series {w}-{l}-{t}**")
        elif l > w:
            st.markdown(f"**{team_b} leads series {l}-{w}-{t}**")
        else:
            st.markdown(f"**Series tied {w}-{l}-{t}**")
            
        if (pw + pl + pt) == 0:
            st.markdown("**Playoff Record:** No playoff matchups have occurred")
        elif pw > pl:
            st.markdown(f"**Playoff Record:** {team_a} leads series {pw}-{pl}-{pt}")
        elif pl > pw:
            st.markdown(f"**Playoff Record:** {team_b} leads series {pl}-{pw}-{pt}")
        else:
            st.markdown(f"**Playoff Record:** Series tied {pw}-{pl}-{pt}")
            
        st.divider()
        
        display_h2h = h2h_games.sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).copy()
        display_h2h['Season_Str'] = display_h2h['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        display_h2h['Season'] = display_h2h['Season_Str']
        display_h2h['Winner'] = display_h2h.apply(lambda x: x['Team_Name'] if x['W'] == 1 else (x['Opponent_Team_Name'] if x['L'] == 1 else 'Tie'), axis=1)
        display_h2h['Type'] = display_h2h['Game_Type'].map({1: 'Regular Season', 2: 'Playoffs'}).fillna(display_h2h['Game_Type_Str'])
        
        display_h2h[f'{team_a} Pts'] = display_h2h['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        display_h2h[f'{team_b} Pts'] = display_h2h['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
        display_h2h['Margin'] = display_h2h['Margin'].apply(lambda x: f"{float(x):.1f}")
        
        display_h2h[f'{team_a} Top Scorer'] = display_h2h.apply(
            lambda r: game_top_map.get((r['Season_Str'], int(r['Week_Num']), str(team_a).strip()), ""), axis=1
        )
        display_h2h[f'{team_b} Top Scorer'] = display_h2h.apply(
            lambda r: game_top_map.get((r['Season_Str'], int(r['Week_Num']), str(team_b).strip()), ""), axis=1
        )
        
        cols = ['Season', 'Week', 'Type', 'Winner', f'{team_a} Pts', f'{team_b} Pts', 'Margin', f'{team_a} Top Scorer', f'{team_b} Top Scorer']
        disp_table = display_h2h[cols]
        
        def highlight_winners(row):
            styles = ['' for _ in row.index]
            col_a_idx = row.index.get_loc(f'{team_a} Pts')
            col_b_idx = row.index.get_loc(f'{team_b} Pts')
            if row['Winner'] == team_a:
                styles[col_a_idx] = 'font-weight: bold;'
            elif row['Winner'] == team_b:
                styles[col_b_idx] = 'font-weight: bold;'
            return styles
        
        h2h_styled_html = disp_table.style.hide(axis='index').apply(highlight_winners, axis=1).set_properties(**{
            'text-align': 'center',
            'padding': '6px 8px',
            'border': '1px solid #e6e6e6',
            'white-space': 'nowrap'
        }).set_table_styles([
            {'selector': 'th', 'props': [('text-align', 'center'), ('padding', '6px 8px'), ('border', '1px solid #e6e6e6'), ('white-space', 'nowrap')]},
            {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]}
        ]).to_html()
        
        st.markdown(h2h_styled_html, unsafe_allow_html=True)
    else:
        st.write("No matchups found between these teams.")

with tab3:
    selected_season = st.selectbox("Select Season", seasons_list, key='stnd_szn')
    szn_data = games[(games['Season'] == str(selected_season)) & (games['Game_Type'] == 1)]
    
    if not szn_data.empty:
        max_week = int(szn_data['Week_Num'].max())
        selected_week = st.slider("Standings Through Week:", min_value=1, max_value=max_week, value=max_week)
        
        szn_games = szn_data[szn_data['Week_Num'] <= selected_week]
        szn_st = szn_games.groupby('Team_Name').agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum'), PF=('Actual_Points', 'sum'), PA=('Opp_Points', 'sum')).reset_index()
        szn_st['Win %'] = (szn_st['W'] / (szn_st['W'] + szn_st['L'] + szn_st['T'])).round(3)
        szn_st['PF'] = szn_st['PF'].round(1)
        szn_st['PA'] = szn_st['PA'].round(1)
        szn_st = szn_st.sort_values(['Win %', 'PF'], ascending=[False, False])
        
        st.dataframe(szn_st[['Team_Name', 'W', 'L', 'T', 'Win %', 'PF', 'PA']].rename(columns={'Team_Name': 'Team'}), use_container_width=True, hide_index=True)
    else:
        st.write("No regular season data found.")

with tab4:
    record_options = ["Highest Scoring Weeks", "Lowest Scoring Weeks", "Biggest Blowouts", "Closest Games"]
    if 'Top_2_Game' in games.columns: record_options.append("Top 2 Matchups")
    if 'Bottom_2_Game' in games.columns: record_options.append("Bottom 2 Matchups")
    
    record_type = st.radio("Select Category:", record_options, horizontal=True)
    
    if record_type == "Highest Scoring Weeks":
        top_scores = games[['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name']].sort_values('Actual_Points', ascending=False).head(15)
        top_scores['Season'] = top_scores['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        st.dataframe(top_scores, use_container_width=True, hide_index=True)
        
    elif record_type == "Lowest Scoring Weeks":
        low_scores = games[games['Actual_Points'] > 0][['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name']].sort_values('Actual_Points', ascending=True).head(15)
        low_scores['Season'] = low_scores['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        st.dataframe(low_scores, use_container_width=True, hide_index=True)
        
    elif record_type == "Biggest Blowouts":
        blowouts = games[(games['W'] == 1) & (games['Game_Type'] != 4)][['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points', 'Margin']].sort_values('Margin', ascending=False).head(15)
        blowouts['Season'] = blowouts['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        st.dataframe(blowouts, use_container_width=True, hide_index=True)
        
    elif record_type == "Closest Games":
        closest = games[(games['W'] == 1) & (games['Margin'] > 0) & (games['Game_Type'] != 4)][['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points', 'Margin']].sort_values('Margin', ascending=True).head(15)
        closest['Season'] = closest['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        st.dataframe(closest, use_container_width=True, hide_index=True)
        
    elif record_type == "Top 2 Matchups":
        if 'Top_2_Game' in games.columns:
            top2_mask = games['Top_2_Game'].astype(str).str.strip().str.lower().isin(['1', '1.0', 'yes', 'true', 'y'])
            top2 = games[top2_mask].sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).drop_duplicates(subset=['Season', 'Week'])
            top2['Season'] = top2['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            st.dataframe(top2[['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points', 'Margin']].rename(columns={'Team_Name': 'Team 1', 'Actual_Points': 'Team 1 Pts', 'Opponent_Team_Name': 'Team 2', 'Opp_Points': 'Team 2 Pts'}), use_container_width=True, hide_index=True)
        
    elif record_type == "Bottom 2 Matchups":
        if 'Bottom_2_Game' in games.columns:
            bot2_mask = games['Bottom_2_Game'].astype(str).str.strip().str.lower().isin(['1', '1.0', 'yes', 'true', 'y'])
            bot2 = games[bot2_mask].sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).drop_duplicates(subset=['Season', 'Week'])
            bot2['Season'] = bot2['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            st.dataframe(bot2[['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points', 'Margin']].rename(columns={'Team_Name': 'Team 1', 'Actual_Points': 'Team 1 Pts', 'Opponent_Team_Name': 'Team 2', 'Opp_Points': 'Team 2 Pts'}), use_container_width=True, hide_index=True)
            
