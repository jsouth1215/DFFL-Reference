import streamlit as st
import pandas as pd

st.set_page_config(page_title="DFFL Hub", page_icon="🏈", layout="wide")

def render_html_table(df, highlight_fn=None, left_align_cols=None):
    styler = df.style.hide(axis='index')
    styler = styler.set_properties(**{
        'text-align': 'center',
        'padding': '6px 8px',
        'border': '1px solid #e6e6e6',
        'white-space': 'nowrap'
    })
    if left_align_cols:
        valid_cols = [c for c in left_align_cols if c in df.columns]
        if valid_cols:
            styler = styler.set_properties(subset=valid_cols, **{'text-align': 'left'})
    if highlight_fn:
        styler = styler.apply(highlight_fn, axis=1)
        
    styled_html = styler.set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center'), ('padding', '6px 8px'), ('border', '1px solid #e6e6e6'), ('white-space', 'nowrap')]},
        {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse')]}
    ]).to_html()
    st.markdown(styled_html, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_box_scores():
    try:
        return pd.read_excel("espn_fantasy_complete_stats_2017_2026.xlsx", sheet_name="Box_Scores", engine="openpyxl")
    except:
        return pd.DataFrame()

@st.cache_data(ttl=600)
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

@st.cache_data(ttl=600)
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

@st.cache_data(ttl=600)
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
    prev_season = None
    
    for _, row in mgr_df.iterrows():
        s = str(row['Season']).replace('.0', '').strip()
        w = row['Week']
        res = row['Result']
        
        if prev_season is not None and s != prev_season:
            curr_w = 0
            curr_l = 0
            w_start = None
            l_start = None
        prev_season = s
        
        game_label = f"{s}, W{w}"
        
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
        row = game_info.iloc[0]
        opp_name = row['Opponent_Team_Name']
        team_pts = float(row['Actual_Points'])
        opp_pts = float(row['Opp_Points'])
        sel_gt = int(row['Game_Type'])
        sel_szn_num = float(row['Season_Num'])
        sel_gt_str = str(row.get('Game_Type_Str', 'Regular Season')).strip()
    else:
        opp_name = "Unknown"
        team_pts = 0.0
        opp_pts = 0.0
        sel_gt = 1
        sel_szn_num = float(b_season) if str(b_season).isdigit() else 2026.0
        sel_gt_str = "Matchup"
        
    if opp_name.upper() != 'BYE' and opp_name != "Unknown":
        bold_a = "font-weight: 800; color: #111;" if team_pts > opp_pts else ("font-weight: 500; color: #555;" if opp_pts > team_pts else "font-weight: 700; color: #111;")
        bold_b = "font-weight: 800; color: #111;" if opp_pts > team_pts else ("font-weight: 500; color: #555;" if team_pts > opp_pts else "font-weight: 700; color: #111;")
        
        mask_a_szn = (
            (games['Team_Name'] == b_team) &
            (games['Season'] == b_szn_str) &
            (games['Game_Type'].isin([1, 2])) &
            ((games['Game_Type'] < sel_gt) | ((games['Game_Type'] == sel_gt) & (games['Week_Num'] <= b_wk_int)))
        )
        g_a_thru = games[mask_a_szn]
        rec_a_w, rec_a_l, rec_a_t = g_a_thru['W'].sum(), g_a_thru['L'].sum(), g_a_thru['T'].sum()
        rec_a_str = f"{rec_a_w}-{rec_a_l}-{rec_a_t}" if rec_a_t > 0 else f"{rec_a_w}-{rec_a_l}"
        
        mask_b_szn = (
            (games['Team_Name'] == opp_name) &
            (games['Season'] == b_szn_str) &
            (games['Game_Type'].isin([1, 2])) &
            ((games['Game_Type'] < sel_gt) | ((games['Game_Type'] == sel_gt) & (games['Week_Num'] <= b_wk_int)))
        )
        g_b_thru = games[mask_b_szn]
        rec_b_w, rec_b_l, rec_b_t = g_b_thru['W'].sum(), g_b_thru['L'].sum(), g_b_thru['T'].sum()
        rec_b_str = f"{rec_b_w}-{rec_b_l}-{rec_b_t}" if rec_b_t > 0 else f"{rec_b_w}-{rec_b_l}"
        
        h2h_all = games[(games['Team_Name'] == b_team) & (games['Opponent_Team_Name'] == opp_name) & (games['Game_Type'].isin([1, 2]))]
        mask_h2h_thru = (
            (h2h_all['Season_Num'] < sel_szn_num) |
            ((h2h_all['Season_Num'] == sel_szn_num) & (h2h_all['Game_Type'] < sel_gt)) |
            ((h2h_all['Season_Num'] == sel_szn_num) & (h2h_all['Game_Type'] == sel_gt) & (h2h_all['Week_Num'] <= b_wk_int))
        )
        g_h2h_thru = h2h_all[mask_h2h_thru]
        thru_w, thru_l, thru_t = g_h2h_thru['W'].sum(), g_h2h_thru['L'].sum(), g_h2h_thru['T'].sum()
        if thru_w > thru_l:
            h2h_thru_str = f"{b_team} leads series {thru_w}-{thru_l}" + (f"-{thru_t}" if thru_t > 0 else "")
        elif thru_l > thru_w:
            h2h_thru_str = f"{opp_name} leads series {thru_l}-{thru_w}" + (f"-{thru_t}" if thru_t > 0 else "")
        else:
            h2h_thru_str = f"Series tied {thru_w}-{thru_l}" + (f"-{thru_t}" if thru_t > 0 else "")
            
        header_html = (
            '<div style="background-color: rgba(128, 128, 128, 0.05); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 14px 20px; margin: 10px 0 20px 0; text-align: center;">'
            f'<div style="font-size: 13px; font-weight: 700; color: #6c757d; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px;">{b_szn_str} &bull; Week {b_wk_int} &bull; {sel_gt_str}</div>'
            '<div style="display: flex; justify-content: center; align-items: flex-start; gap: 50px; margin-bottom: 8px;">'
            '<div style="min-width: 140px; text-align: center;">'
            f'<div style="font-size: 18px; font-weight: 700; color: #111; margin-bottom: 2px;">{b_team}</div>'
            f'<div style="font-size: 34px; {bold_a}; line-height: 1.1;">{team_pts:.1f}</div>'
            f'<div style="font-size: 14px; font-weight: 500; color: #495057; margin-top: 2px;">{rec_a_str}</div>'
            '</div>'
            '<div style="min-width: 140px; text-align: center;">'
            f'<div style="font-size: 18px; font-weight: 700; color: #111; margin-bottom: 2px;">{opp_name}</div>'
            f'<div style="font-size: 34px; {bold_b}; line-height: 1.1;">{opp_pts:.1f}</div>'
            f'<div style="font-size: 14px; font-weight: 500; color: #495057; margin-top: 2px;">{rec_b_str}</div>'
            '</div>'
            '</div>'
            f'<div style="font-size: 13px; font-weight: 600; color: #495057; border-top: 1px solid rgba(128, 128, 128, 0.2); padding-top: 6px; display: inline-block;">H2H Series through this game: {h2h_thru_str}</div>'
            '</div>'
        )
        st.markdown(header_html, unsafe_allow_html=True)
    elif opp_name.upper() == 'BYE':
        st.markdown(
            '<div style="background-color: rgba(128, 128, 128, 0.05); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 14px 20px; margin: 10px 0 20px 0; text-align: center;">'
            f'<div style="font-size: 13px; font-weight: 700; color: #6c757d; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px;">{b_szn_str} &bull; Week {b_wk_int} &bull; Playoff Bye</div>'
            f'<div style="font-size: 18px; font-weight: 700; color: #111; margin-bottom: 2px;">{b_team}</div>'
            f'<div style="font-size: 34px; font-weight: 800; color: #111; line-height: 1.1;">{team_pts:.1f}</div>'
            '</div>',
            unsafe_allow_html=True
        )
        
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
        
        nfl_col = None
        for cand in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev', 'Team_Abbr', 'Pro_Team_Abbrev', 'Pro Team', 'NFL Team']:
            if cand in df.columns:
                nfl_col = cand
                break
        if not nfl_col and 'Team' in df.columns and 'Team_Name' in df.columns:
            nfl_col = 'Team'
            
        df['NFL Team'] = df[nfl_col].fillna('').astype(str).str.strip() if nfl_col else ""
        
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
                if c not in stat_map and c not in [name_col, slot_col, pts_col, 'NFL Team', 'Season', 'Week', 'Team_Name', 'Opponent_Team_Name']:
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
        starters = df[~is_bench].sort_values(['sort_val', pts_col], ascending=[True, False]).copy()
        bench = df[is_bench].sort_values(pts_col, ascending=False).copy()
        
        disp_cols = [name_col, 'NFL Team', slot_col, pts_col, 'Stats']
        start_disp = starters[disp_cols].rename(columns={name_col: 'Player', slot_col: 'Slot', pts_col: 'Pts'})
        bench_disp = bench[disp_cols].rename(columns={name_col: 'Player', slot_col: 'Slot', pts_col: 'Pts'})
        
        if not start_disp.empty:
            total_val = start_disp['Pts'].sum()
            total_row = pd.DataFrame([{'Player': 'TOTAL', 'NFL Team': '', 'Slot': '', 'Pts': total_val, 'Stats': ''}])
            start_disp = pd.concat([start_disp, total_row], ignore_index=True)
            
        start_disp['Pts'] = start_disp['Pts'].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) and x != '' else "")
        bench_disp['Pts'] = bench_disp['Pts'].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) and x != '' else "")
        
        return start_disp, bench_disp

    team_start, team_bench = format_roster(team_roster)
    opp_start, opp_bench = format_roster(opp_roster)
    
    def highlight_total_row(row):
        if str(row.get('Player', '')).strip().upper() == 'TOTAL':
            return ['font-weight: bold;' for _ in row.index]
        return ['' for _ in row.index]
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"#### {b_team}")
        if not team_start.empty:
            render_html_table(team_start, highlight_total_row, left_align_cols=['Stats'])
        if not team_bench.empty:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown("**Bench**")
            render_html_table(team_bench, left_align_cols=['Stats'])
    with col_b:
        if opp_name != "Unknown" and opp_name.upper() != 'BYE':
            st.markdown(f"#### {opp_name}")
            if not opp_start.empty:
                render_html_table(opp_start, highlight_total_row, left_align_cols=['Stats'])
            if not opp_bench.empty:
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.markdown("**Bench**")
                render_html_table(opp_bench, left_align_cols=['Stats'])
        elif opp_name.upper() == 'BYE':
            st.markdown("#### BYE")
        else:
            st.markdown("#### Opponent Matchup Not Found")

def get_starter_performances(box_df, games):
    if box_df.empty or games.empty:
        return pd.DataFrame()
    b_c = box_df.copy()
    b_c['Season_Str'] = b_c['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    b_c['Week_Num'] = pd.to_numeric(b_c['Week'], errors='coerce').fillna(0).astype(int)
    b_c['Team_Str'] = b_c['Team_Name'].astype(str).str.strip()
    
    slot_col = 'Slot' if 'Slot' in b_c.columns else ('Lineup_Slot' if 'Lineup_Slot' in b_c.columns else 'Position')
    name_col = 'Player_Name' if 'Player_Name' in b_c.columns else 'Player'
    pts_col = 'Actual_Points' if 'Actual_Points' in b_c.columns else 'Points'
    pos_col = 'Position' if 'Position' in b_c.columns else ('Pos' if 'Pos' in b_c.columns else slot_col)
    
    nfl_c = None
    for cand in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev', 'Team_Abbr', 'Pro_Team_Abbrev', 'Pro Team', 'NFL Team']:
        if cand in b_c.columns:
            nfl_c = cand
            break
    if not nfl_c and 'Team' in b_c.columns and 'Team_Name' in b_c.columns:
        nfl_c = 'Team'
    b_c['NFL Team'] = b_c[nfl_c].fillna('').astype(str).str.strip() if nfl_c else ""

    is_start = ~b_c[slot_col].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])
    start_df = b_c[is_start].copy()
    start_df['Points_Num'] = pd.to_numeric(start_df[pts_col], errors='coerce').fillna(0)
    
    def clean_pos(val):
        p = str(val).strip().upper()
        if p == 'QB': return 'QB'
        if p == 'RB': return 'RB'
        if p == 'WR': return 'WR'
        if p == 'TE': return 'TE'
        if p in ['K', 'PK']: return 'K'
        if p in ['D/ST', 'DST', 'DEF', 'DP']: return 'D/ST'
        return p
    start_df['Pos'] = start_df[pos_col].apply(clean_pos)
    
    cols_to_drop = [c for c in ['Opponent_Team_Name', 'Opponent', 'Outcome'] if c in start_df.columns]
    if cols_to_drop:
        start_df = start_df.drop(columns=cols_to_drop)
    
    el_g = games[games['Game_Type'].isin([1, 2, 4]) & (games['Team_Name'].str.upper() != 'CAM')].copy()
    el_g['Season_Str'] = el_g['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    el_g['Week_Num'] = pd.to_numeric(el_g['Week'], errors='coerce').fillna(0).astype(int)
    el_g['Team_Str'] = el_g['Team_Name'].astype(str).str.strip()
    
    def make_outcome(r):
        if r['Game_Type'] == 4:
            return f"BYE ({float(r['Actual_Points']):.1f})"
        res = 'W' if r['W'] == 1 else ('L' if r['L'] == 1 else 'T')
        return f"{res} ({float(r['Actual_Points']):.1f} - {float(r['Opp_Points']):.1f})"
    el_g['Outcome'] = el_g.apply(make_outcome, axis=1)
    
    el_g_sub = el_g[['Season_Str', 'Week_Num', 'Team_Str', 'Opponent_Team_Name', 'Outcome']].drop_duplicates(subset=['Season_Str', 'Week_Num', 'Team_Str'])
    
    merged = pd.merge(
        start_df,
        el_g_sub,
        on=['Season_Str', 'Week_Num', 'Team_Str'],
        how='inner'
    )
    merged['Player'] = merged[name_col]
    merged['Season'] = merged['Season_Str']
    merged['Week'] = merged['Week_Num']
    merged['Team'] = merged['Team_Str']
    merged['Opponent'] = merged['Opponent_Team_Name']
    return merged

def get_all_streaks_records(games):
    streak_games = games[games['Game_Type'].isin([1, 2])].copy()
    streak_games['Season_Str'] = streak_games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    streak_games['Week_Num'] = pd.to_numeric(streak_games['Week'], errors='coerce').fillna(0).astype(int)
    streak_games = streak_games.sort_values(['Team_Name', 'Season_Num', 'Week_Num'])
    
    win_streaks = []
    loss_streaks = []
    
    for (tm, szn), grp in streak_games.groupby(['Team_Name', 'Season_Str']):
        curr_w = 0
        w_start_wk = None
        curr_l = 0
        l_start_wk = None
        prev_wk = None
        
        for _, r in grp.iterrows():
            wk = r['Week']
            res = 'W' if r['W'] == 1 else ('L' if r['L'] == 1 else 'T')
            
            if res == 'W':
                if curr_w == 0:
                    w_start_wk = wk
                curr_w += 1
                
                if curr_l > 0:
                    span_str = f"Week {l_start_wk} to Week {prev_wk}" if l_start_wk != prev_wk else f"Week {l_start_wk}"
                    loss_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_l, 'Span': span_str})
                    curr_l = 0
                    l_start_wk = None
            elif res == 'L':
                if curr_l == 0:
                    l_start_wk = wk
                curr_l += 1
                
                if curr_w > 0:
                    span_str = f"Week {w_start_wk} to Week {prev_wk}" if w_start_wk != prev_wk else f"Week {w_start_wk}"
                    win_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_w, 'Span': span_str})
                    curr_w = 0
                    w_start_wk = None
            else:
                if curr_w > 0:
                    span_str = f"Week {w_start_wk} to Week {prev_wk}" if w_start_wk != prev_wk else f"Week {w_start_wk}"
                    win_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_w, 'Span': span_str})
                    curr_w = 0
                    w_start_wk = None
                if curr_l > 0:
                    span_str = f"Week {l_start_wk} to Week {prev_wk}" if l_start_wk != prev_wk else f"Week {l_start_wk}"
                    loss_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_l, 'Span': span_str})
                    curr_l = 0
                    l_start_wk = None
            prev_wk = wk
            
        if curr_w > 0:
            span_str = f"Week {w_start_wk} to Week {prev_wk}" if w_start_wk != prev_wk else f"Week {w_start_wk}"
            win_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_w, 'Span': span_str})
        if curr_l > 0:
            span_str = f"Week {l_start_wk} to Week {prev_wk}" if l_start_wk != prev_wk else f"Week {l_start_wk}"
            loss_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_l, 'Span': span_str})
            
    return pd.DataFrame(win_streaks), pd.DataFrame(loss_streaks)

st.title("🏈 DFFL History Hub")

try:
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

tab1, tab5, tab6, tab2, tab3, tab4, tab_player = st.tabs([
    "Franchise", "Schedule", "Box Scores", "Matchups", "Standings", "Records", "Detailed Player Scoring"
])

with tab3:
    selected_season = st.selectbox("Select Season", seasons_list, key='stnd_szn')
    szn_data = games[(games['Season'] == str(selected_season)) & (games['Game_Type'] == 1)]
    
    if not szn_data.empty:
        max_week = int(szn_data['Week_Num'].max())
        selected_week = st.slider("Standings Through Week:", min_value=1, max_value=max_week, value=max_week)
        
        szn_games = szn_data[szn_data['Week_Num'] <= selected_week].copy()
        
        szn_games['Weekly_Rank'] = szn_games.groupby('Week_Num')['Actual_Points'].rank(ascending=False, method='average')
        szn_games['N_Teams'] = szn_games.groupby('Week_Num')['Team_Name'].transform('count')
        szn_games['Exp_Win'] = szn_games.apply(
            lambda r: (r['N_Teams'] - r['Weekly_Rank']) / (r['N_Teams'] - 1) if r['N_Teams'] > 1 else 0.0,
            axis=1
        )
        
        szn_st = szn_games.groupby('Team_Name').agg(
            W=('W', 'sum'),
            L=('L', 'sum'),
            T=('T', 'sum'),
            PF=('Actual_Points', 'sum'),
            PA=('Opp_Points', 'sum'),
            Exp_Win_Total=('Exp_Win', 'sum')
        ).reset_index()
        
        szn_st['Win_Pct_Raw'] = (szn_st['W'] / (szn_st['W'] + szn_st['L'] + szn_st['T'])).fillna(0)
        szn_st = szn_st.sort_values(['Win_Pct_Raw', 'PF'], ascending=[False, False]).reset_index(drop=True)
        
        szn_st['Rank'] = szn_st.index + 1
        szn_st['Rank'] = szn_st['Rank'].apply(lambda x: f"{x}{'th' if 11 <= x % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(x % 10, 'th')}")
        szn_st['Win %'] = szn_st['Win_Pct_Raw'].apply(lambda x: f"{x:.3f}".replace("0.", ".", 1) if x < 1 else f"{x:.3f}")
        szn_st['PF'] = szn_st['PF'].apply(lambda x: f"{float(x):.1f}")
        szn_st['PA'] = szn_st['PA'].apply(lambda x: f"{float(x):.1f}")
        szn_st['Expected Wins'] = szn_st['Exp_Win_Total'].apply(lambda x: f"{float(x):.1f}")
        
        def calc_stnd_luck(r):
            w = r['W']
            xw = r['Exp_Win_Total']
            diff = w - xw
            if abs(diff) < 0.05:
                return "0.0"
            return f"{diff:+.1f}"
            
        szn_st['Luck Factor'] = szn_st.apply(calc_stnd_luck, axis=1)
        szn_st = szn_st.rename(columns={'Team_Name': 'Team'})
        
        disp_cols = ['Rank', 'Team', 'W', 'L', 'T', 'Win %', 'PF', 'PA', 'Expected Wins', 'Luck Factor']
        render_html_table(szn_st[disp_cols])
    else:
        st.write("No regular season data found.")

with tab4:
    rec_categories = {
        "Game Records": [
            "Highest Scoring Weeks",
            "Lowest Scoring Weeks",
            "Lowest Scoring Weekly Bags",
            "Biggest Blowouts",
            "Closest Games"
        ],
        "Player Records": [
            "Highest Scoring Players",
            "Lowest Scoring Players",
            "Highest Scoring Stacks",
            "Most Fantasy Teams Started For",
            "Started on Same Fantasy Team for 3+ NFL Teams"
        ],
        "Season Records": [
            "Highest Season Luck Factor",
            "Lowest Season Luck Factor",
            "Most Points Per Game in a Season",
            "Least Points Per Game in a Season",
            "Longest Win Streak",
            "Longest Losing Streak"
        ],
        "Franchise Records": [
            "Team Record - Highest Score",
            "Team Record - Lowest Score",
            "Weekly Bag by Team",
            "Weekly Last Place Score by Team",
            "Playoff Record by Team"
        ]
    }
    
    if 'Top_2_Game' in games.columns:
        rec_categories["Game Records"].append("Top 2 Matchups")
    if 'Bottom_2_Game' in games.columns:
        rec_categories["Game Records"].append("Bottom 2 Matchups")

    selected_group = st.radio("Record Category:", list(rec_categories.keys()), horizontal=True, key="rec_cat_group")
    record_type = st.radio("Select Record:", rec_categories[selected_group], horizontal=True, key="rec_sub_type")
    st.write("---")
    
    bag_seasons = sorted(
        [str(s).replace('.0', '').strip() for s in games['Season'].unique() if str(s).replace('.0', '').strip().isdigit() and int(str(s).replace('.0', '').strip()) >= 2019],
        key=lambda x: int(x)
    )
    
    lp_seasons = sorted(
        [str(s).replace('.0', '').strip() for s in games['Season'].unique() if str(s).replace('.0', '').strip().isdigit() and int(str(s).replace('.0', '').strip()) >= 2017],
        key=lambda x: int(x)
    )

    all_reg_completed = games[(games['Game_Type'] == 1) & (games['Season'].isin(completed_playoff_seasons))].copy()
    if not all_reg_completed.empty:
        all_reg_completed['Season_Str'] = all_reg_completed['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        all_reg_completed['Weekly_Rank'] = all_reg_completed.groupby(['Season_Str', 'Week_Num'])['Actual_Points'].rank(ascending=False, method='average')
        all_reg_completed['N_Teams'] = all_reg_completed.groupby(['Season_Str', 'Week_Num'])['Team_Name'].transform('count')
        all_reg_completed['Exp_Win'] = all_reg_completed.apply(
            lambda r: (r['N_Teams'] - r['Weekly_Rank']) / (r['N_Teams'] - 1) if r['N_Teams'] > 1 else 0.0,
            axis=1
        )
        
        season_team_agg = all_reg_completed.groupby(['Season_Str', 'Team_Name']).agg(
            W=('W', 'sum'),
            L=('L', 'sum'),
            T=('T', 'sum'),
            PF=('Actual_Points', 'sum'),
            Exp_Win_Total=('Exp_Win', 'sum'),
            Games_Count=('W', 'count')
        ).reset_index()
        
        season_team_agg['Record'] = season_team_agg.apply(
            lambda r: f"{int(r['W'])}-{int(r['L'])}-{int(r['T'])}" if r['T'] > 0 else f"{int(r['W'])}-{int(r['L'])}",
            axis=1
        )
        season_team_agg['Luck_Num'] = season_team_agg['W'] - season_team_agg['Exp_Win_Total']
        season_team_agg['Expected Wins'] = season_team_agg['Exp_Win_Total'].apply(lambda x: f"{float(x):.1f}")
        season_team_agg['Luck Factor'] = season_team_agg['Luck_Num'].apply(lambda x: "0.0" if abs(x) < 0.05 else f"{x:+.1f}")
        season_team_agg['PF_Formatted'] = season_team_agg['PF'].apply(lambda x: f"{float(x):.1f}")
        season_team_agg['PPG_Num'] = season_team_agg['PF'] / season_team_agg['Games_Count']
        season_team_agg['PF/G'] = season_team_agg['PPG_Num'].apply(lambda x: f"{float(x):.1f}")
        season_team_agg = season_team_agg.rename(columns={'Season_Str': 'Season', 'Team_Name': 'Team'})
    else:
        season_team_agg = pd.DataFrame()
    
    if record_type == "Highest Scoring Weeks":
        top_scores = games[games['Game_Type'].isin([1, 2, 4])][['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name']].sort_values('Actual_Points', ascending=False).head(15).copy().reset_index(drop=True)
        top_scores['Rank'] = top_scores.index + 1
        top_scores['Season'] = top_scores['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        top_scores['Actual_Points'] = top_scores['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        top_scores = top_scores.rename(columns={'Team_Name': 'Team', 'Actual_Points': 'Points', 'Opponent_Team_Name': 'Opponent'})
        render_html_table(top_scores[['Rank', 'Season', 'Week', 'Team', 'Points', 'Opponent']])
        
    elif record_type == "Lowest Scoring Weeks":
        low_scores = games[(games['Actual_Points'] > 0) & (games['Game_Type'].isin([1, 2]))][['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name']].sort_values('Actual_Points', ascending=True).head(15).copy().reset_index(drop=True)
        low_scores['Rank'] = low_scores.index + 1
        low_scores['Season'] = low_scores['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        low_scores['Actual_Points'] = low_scores['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        low_scores = low_scores.rename(columns={'Team_Name': 'Team', 'Actual_Points': 'Points', 'Opponent_Team_Name': 'Opponent'})
        render_html_table(low_scores[['Rank', 'Season', 'Week', 'Team', 'Points', 'Opponent']])
        
    elif record_type == "Lowest Scoring Weekly Bags":
        bag_games = games[games['Is_High_Scorer']].copy()
        if not bag_games.empty:
            low_bags = bag_games.sort_values('Actual_Points', ascending=True).head(15).copy().reset_index(drop=True)
            low_bags['Rank'] = low_bags.index + 1
            low_bags['Season'] = low_bags['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            low_bags['Actual_Points'] = low_bags['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
            low_bags = low_bags.rename(columns={'Team_Name': 'Team', 'Actual_Points': 'Points', 'Opponent_Team_Name': 'Opponent'})
            render_html_table(low_bags[['Rank', 'Season', 'Week', 'Team', 'Points', 'Opponent']])
        else:
            st.write("No weekly bag records found.")
            
    elif record_type == "Biggest Blowouts":
        blowouts = games[(games['W'] == 1) & (games['Game_Type'].isin([1, 2]))][['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points', 'Margin']].sort_values('Margin', ascending=False).head(15).copy().reset_index(drop=True)
        blowouts['Rank'] = blowouts.index + 1
        blowouts['Season'] = blowouts['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        blowouts['Actual_Points'] = blowouts['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        blowouts['Opp_Points'] = blowouts['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
        blowouts['Margin'] = blowouts['Margin'].apply(lambda x: f"{float(x):.1f}")
        blowouts = blowouts.rename(columns={'Team_Name': 'Winner', 'Actual_Points': 'Winner Pts', 'Opponent_Team_Name': 'Loser', 'Opp_Points': 'Loser Pts'})
        render_html_table(blowouts[['Rank', 'Season', 'Week', 'Winner', 'Winner Pts', 'Loser', 'Loser Pts', 'Margin']])
        
    elif record_type == "Closest Games":
        closest = games[(games['W'] == 1) & (games['Margin'] > 0) & (games['Game_Type'].isin([1, 2]))][['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points', 'Margin']].sort_values('Margin', ascending=True).head(15).copy().reset_index(drop=True)
        closest['Rank'] = closest.index + 1
        closest['Season'] = closest['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        closest['Actual_Points'] = closest['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        closest['Opp_Points'] = closest['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
        closest['Margin'] = closest['Margin'].apply(lambda x: f"{float(x):.1f}")
        closest = closest.rename(columns={'Team_Name': 'Winner', 'Actual_Points': 'Winner Pts', 'Opponent_Team_Name': 'Loser', 'Opp_Points': 'Loser Pts'})
        render_html_table(closest[['Rank', 'Season', 'Week', 'Winner', 'Winner Pts', 'Loser', 'Loser Pts', 'Margin']])
        
    elif record_type == "Top 2 Matchups":
        if 'Top_2_Game' in games.columns:
            top2_mask = games['Top_2_Game'].astype(str).str.strip().str.lower().isin(['1', '1.0', 'yes', 'true', 'y'])
            top2 = games[top2_mask].sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).drop_duplicates(subset=['Season', 'Week']).copy()
            top2['Season'] = top2['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            top2['Actual_Points'] = top2['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
            top2['Opp_Points'] = top2['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
            top2['Margin'] = top2['Margin'].apply(lambda x: f"{float(x):.1f}")
            top2 = top2.rename(columns={'Team_Name': 'Team 1', 'Actual_Points': 'Team 1 Pts', 'Opponent_Team_Name': 'Team 2', 'Opp_Points': 'Team 2 Pts'})
            render_html_table(top2[['Season', 'Week', 'Team 1', 'Team 1 Pts', 'Team 2', 'Team 2 Pts', 'Margin']])
        
    elif record_type == "Bottom 2 Matchups":
        if 'Bottom_2_Game' in games.columns:
            bot2_mask = games['Bottom_2_Game'].astype(str).str.strip().str.lower().isin(['1', '1.0', 'yes', 'true', 'y'])
            bot2 = games[bot2_mask].sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).drop_duplicates(subset=['Season', 'Week'])
            bot2['Season'] = bot2['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            bot2['Actual_Points'] = bot2['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
            bot2['Opp_Points'] = bot2['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
            bot2['Margin'] = bot2['Margin'].apply(lambda x: f"{float(x):.1f}")
            bot2 = bot2.rename(columns={'Team_Name': 'Team 1', 'Actual_Points': 'Team 1 Pts', 'Opponent_Team_Name': 'Team 2', 'Opp_Points': 'Team 2 Pts'})
            render_html_table(bot2[['Season', 'Week', 'Team 1', 'Team 1 Pts', 'Team 2', 'Team 2 Pts', 'Margin']])

    elif record_type == "Highest Scoring Players":
        p_perf = get_starter_performances(box_df, games)
        if not p_perf.empty:
            top_players = p_perf.sort_values('Points_Num', ascending=False).head(15).copy().reset_index(drop=True)
            top_players['Rank'] = top_players.index + 1
            top_players['Points'] = top_players['Points_Num'].apply(lambda x: f"{float(x):.1f}")
            cols_disp = ['Rank', 'Player', 'Pos', 'NFL Team', 'Points', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']
            render_html_table(top_players[[c for c in cols_disp if c in top_players.columns]])
        else:
            st.info("No player scoring records available.")

    elif record_type == "Lowest Scoring Players":
        p_perf = get_starter_performances(box_df, games)
        if not p_perf.empty:
            st.write("### Lowest Scoring Starters (All Positions)")
            low_all = p_perf.sort_values('Points_Num', ascending=True).head(15).copy().reset_index(drop=True)
            low_all['Rank'] = low_all.index + 1
            low_all['Points'] = low_all['Points_Num'].apply(lambda x: f"{float(x):.1f}")
            cols_disp = ['Rank', 'Player', 'Pos', 'NFL Team', 'Points', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']
            render_html_table(low_all[[c for c in cols_disp if c in low_all.columns]])

            st.write("### Negative Point Starters (Non-Defense)")
            non_dst_neg = p_perf[(~p_perf['Pos'].isin(['D/ST', 'DST', 'DEF', 'DP'])) & (p_perf['Points_Num'] < 0)].sort_values('Points_Num', ascending=True).copy().reset_index(drop=True)
            if not non_dst_neg.empty:
                non_dst_neg['Rank'] = non_dst_neg.index + 1
                non_dst_neg['Points'] = non_dst_neg['Points_Num'].apply(lambda x: f"{float(x):.1f}")
                render_html_table(non_dst_neg[[c for c in cols_disp if c in non_dst_neg.columns]])
            else:
                st.info("No non-defense starters have scored negative points.")
        else:
            st.info("No player scoring records available.")

    elif record_type == "Highest Scoring Stacks":
        p_perf = get_starter_performances(box_df, games)
        if not p_perf.empty:
            stacks_list = []
            for (s, w, tm), g_df in p_perf.groupby(['Season', 'Week', 'Team']):
                qbs = g_df[g_df['Pos'] == 'QB']
                catchers = g_df[g_df['Pos'].isin(['WR', 'TE'])]
                if qbs.empty or catchers.empty:
                    continue
                for _, qb_r in qbs.iterrows():
                    qb_nfl = str(qb_r['NFL Team']).strip()
                    if not qb_nfl or qb_nfl in ['-', 'FA']:
                        continue
                    same_team_catchers = catchers[catchers['NFL Team'].astype(str).str.strip() == qb_nfl]
                    for _, c_r in same_team_catchers.iterrows():
                        comb_pts = float(qb_r['Points_Num']) + float(c_r['Points_Num'])
                        stacks_list.append({
                            'QB': f"{qb_r['Player']} ({float(qb_r['Points_Num']):.1f})",
                            'Pass Catcher': f"{c_r['Player']} ({float(c_r['Points_Num']):.1f})",
                            'Pos': c_r['Pos'],
                            'NFL Team': qb_nfl,
                            'Combined_Num': comb_pts,
                            'Combined Pts': f"{comb_pts:.1f}",
                            'Season': s,
                            'Week': w,
                            'Team': tm,
                            'Opponent': qb_r['Opponent'],
                            'Outcome': qb_r['Outcome']
                        })
            if stacks_list:
                stacks_df = pd.DataFrame(stacks_list).sort_values('Combined_Num', ascending=False).head(15).reset_index(drop=True)
                stacks_df['Rank'] = stacks_df.index + 1
                cols_stk = ['Rank', 'QB', 'Pass Catcher', 'Pos', 'NFL Team', 'Combined Pts', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']
                render_html_table(stacks_df[cols_stk])
            else:
                st.info("No starting QB/WR or QB/TE same-team stacks found.")
        else:
            st.info("No player scoring records available.")

    elif record_type == "Most Fantasy Teams Started For":
        p_perf = get_starter_performances(box_df, games)
        if not p_perf.empty:
            non_dst = p_perf[~p_perf['Pos'].isin(['D/ST', 'DST', 'DEF', 'DP'])].copy()
            travelers = []
            for player, grp in non_dst.groupby('Player'):
                f_teams = sorted(list(set(str(t).strip() for t in grp['Team'].unique() if str(t).strip())))
                if len(f_teams) > 1:
                    pos_val = grp['Pos'].mode().iloc[0] if not grp['Pos'].empty else ""
                    travelers.append({
                        'Player': player,
                        'Pos': pos_val,
                        'Teams Count': len(f_teams),
                        'Fantasy Teams': ", ".join(f_teams)
                    })
            if travelers:
                trav_df = pd.DataFrame(travelers).sort_values(['Teams Count', 'Player'], ascending=[False, True]).head(15).reset_index(drop=True)
                trav_df['Rank'] = trav_df.index + 1
                render_html_table(trav_df[['Rank', 'Player', 'Pos', 'Teams Count', 'Fantasy Teams']], left_align_cols=['Fantasy Teams'])
            else:
                st.info("No players found starting for multiple fantasy teams.")
        else:
            st.info("No player scoring records available.")

    elif record_type == "Started on Same Fantasy Team for 3+ NFL Teams":
        p_perf = get_starter_performances(box_df, games)
        if not p_perf.empty:
            non_dst = p_perf[~p_perf['Pos'].isin(['D/ST', 'DST', 'DEF', 'DP'])].copy()
            journeyman_records = []
            for (player, tm), grp in non_dst.groupby(['Player', 'Team']):
                nfl_tms = sorted(list(set(str(t).strip() for t in grp['NFL Team'].unique() if str(t).strip() and str(t).strip() not in ['-', 'FA', 'NONE', 'NAN'])))
                if len(nfl_tms) >= 3:
                    pos_val = grp['Pos'].mode().iloc[0] if not grp['Pos'].empty else ""
                    journeyman_records.append({
                        'Player': player,
                        'Pos': pos_val,
                        'Fantasy Team': tm,
                        'NFL Teams Count': len(nfl_tms),
                        'NFL Teams': ", ".join(nfl_tms)
                    })
            if journeyman_records:
                j_df = pd.DataFrame(journeyman_records).sort_values(['NFL Teams Count', 'Player'], ascending=[False, True]).reset_index(drop=True)
                render_html_table(j_df[['Player', 'Pos', 'Fantasy Team', 'NFL Teams Count', 'NFL Teams']], left_align_cols=['NFL Teams'])
            else:
                st.info("No players found who started for the same fantasy team across 3 or more different NFL teams.")
        else:
            st.info("No player scoring records available.")

    elif record_type == "Highest Season Luck Factor":
        if not season_team_agg.empty:
            top_luck = season_team_agg.sort_values('Luck_Num', ascending=False).head(15).reset_index(drop=True)
            top_luck['Rank'] = top_luck.index + 1
            render_html_table(top_luck[['Rank', 'Season', 'Team', 'Record', 'Expected Wins', 'Luck Factor']])
        else:
            st.info("No completed season records found.")

    elif record_type == "Lowest Season Luck Factor":
        if not season_team_agg.empty:
            low_luck = season_team_agg.sort_values('Luck_Num', ascending=True).head(15).reset_index(drop=True)
            low_luck['Rank'] = low_luck.index + 1
            render_html_table(low_luck[['Rank', 'Season', 'Team', 'Record', 'Expected Wins', 'Luck Factor']])
        else:
            st.info("No completed season records found.")

    elif record_type == "Most Points Per Game in a Season":
        if not season_team_agg.empty:
            top_ppg = season_team_agg.sort_values('PPG_Num', ascending=False).head(15).reset_index(drop=True)
            top_ppg['Rank'] = top_ppg.index + 1
            top_ppg['PF'] = top_ppg['PF_Formatted']
            render_html_table(top_ppg[['Rank', 'Season', 'Team', 'Record', 'PF/G', 'PF']])
        else:
            st.info("No completed season records found.")

    elif record_type == "Least Points Per Game in a Season":
        if not season_team_agg.empty:
            sub_least = season_team_agg[season_team_agg['Season'] != '2017'].copy()
            low_ppg = sub_least.sort_values('PPG_Num', ascending=True).head(15).reset_index(drop=True)
            low_ppg['Rank'] = low_ppg.index + 1
            low_ppg['PF'] = low_ppg['PF_Formatted']
            render_html_table(low_ppg[['Rank', 'Season', 'Team', 'Record', 'PF/G', 'PF']])
        else:
            st.info("No completed season records found.")

    elif record_type == "Longest Win Streak":
        w_df, _ = get_all_streaks_records(games)
        if not w_df.empty:
            top_wins = w_df.sort_values(['Length', 'Season'], ascending=[False, False]).head(15).reset_index(drop=True)
            top_wins['Rank'] = top_wins.index + 1
            top_wins = top_wins.rename(columns={'Length': 'Streak'})
            render_html_table(top_wins[['Rank', 'Team', 'Season', 'Streak', 'Span']])
        else:
            st.info("No streak records found.")

    elif record_type == "Longest Losing Streak":
        _, l_df = get_all_streaks_records(games)
        if not l_df.empty:
            top_loss = l_df.sort_values(['Length', 'Season'], ascending=[False, False]).head(15).reset_index(drop=True)
            top_loss['Rank'] = top_loss.index + 1
            top_loss = top_loss.rename(columns={'Length': 'Streak'})
            render_html_table(top_loss[['Rank', 'Team', 'Season', 'Streak', 'Span']])
        else:
            st.info("No streak records found.")

    elif record_type == "Team Record - Highest Score":
        high_scores_list = []
        for t in teams_no_cam:
            t_games = games[games['Team_Name'] == t]
            if not t_games.empty:
                best_r = t_games.loc[t_games['Actual_Points'].idxmax()]
                high_scores_list.append({
                    'Team': t,
                    'Points_Num': float(best_r['Actual_Points']),
                    'Points': f"{float(best_r['Actual_Points']):.1f}",
                    'Season': str(best_r['Season']).replace('.0', '').strip(),
                    'Week': best_r['Week'],
                    'Opponent': best_r['Opponent_Team_Name']
                })
        if high_scores_list:
            high_df = pd.DataFrame(high_scores_list).sort_values('Points_Num', ascending=False).reset_index(drop=True)
            high_df['Rank'] = high_df.index + 1
            render_html_table(high_df[['Rank', 'Team', 'Points', 'Season', 'Week', 'Opponent']])

    elif record_type == "Team Record - Lowest Score":
        low_scores_list = []
        for t in teams_no_cam:
            t_games = games[(games['Team_Name'] == t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points'] > 0)]
            if not t_games.empty:
                low_r = t_games.loc[t_games['Actual_Points'].idxmin()]
                low_scores_list.append({
                    'Team': t,
                    'Points_Num': float(low_r['Actual_Points']),
                    'Points': f"{float(low_r['Actual_Points']):.1f}",
                    'Season': str(low_r['Season']).replace('.0', '').strip(),
                    'Week': low_r['Week'],
                    'Opponent': low_r['Opponent_Team_Name']
                })
        if low_scores_list:
            low_df = pd.DataFrame(low_scores_list).sort_values('Points_Num', ascending=True).reset_index(drop=True)
            low_df['Rank'] = low_df.index + 1
            render_html_table(low_df[['Rank', 'Team', 'Points', 'Season', 'Week', 'Opponent']])

    elif record_type == "Weekly Bag by Team":
        bag_data = []
        for t in teams_no_cam:
            row = {'Team': t}
            tot = 0
            for s in bag_seasons:
                cnt = int(games[(games['Team_Name'] == t) & (games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == s) & (games['Is_High_Scorer'])]['Is_High_Scorer'].sum())
                row[s] = cnt
                tot += cnt
            row['Total'] = tot
            bag_data.append(row)
        bag_df = pd.DataFrame(bag_data).sort_values(['Total', 'Team'], ascending=[False, True]).reset_index(drop=True)
        render_html_table(bag_df[['Team'] + bag_seasons + ['Total']])

    elif record_type == "Weekly Last Place Score by Team":
        reg_games = games[(games['Game_Type'] == 1) & (games['Season_Num'] >= 2017)].copy()
        if not reg_games.empty:
            min_pts = reg_games.groupby(['Season', 'Week'])['Actual_Points'].transform('min')
            reg_games['Is_Low_Scorer'] = (reg_games['Actual_Points'] == min_pts)
            
            lp_data = []
            for t in teams:
                row = {'Team': t}
                tot = 0
                for s in lp_seasons:
                    cnt = int(reg_games[(reg_games['Team_Name'] == t) & (reg_games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == s)]['Is_Low_Scorer'].sum())
                    row[s] = cnt
                    tot += cnt
                row['Total'] = tot
                lp_data.append(row)
            lp_df = pd.DataFrame(lp_data).sort_values(['Total', 'Team'], ascending=[False, True]).reset_index(drop=True)
            render_html_table(lp_df[['Team'] + lp_seasons + ['Total']])

    elif record_type == "Playoff Record by Team":
        po_records_list = []
        for t in teams_no_cam:
            rs_team = rs_ranks_df[rs_ranks_df['Team_Name'] == t]
            apps = 0
            byes = 0
            for _, r in rs_team.iterrows():
                szn_str = str(r['Season']).strip()
                if not szn_str.isdigit(): continue
                if szn_str not in completed_playoff_seasons: continue
                szn = int(szn_str)
                rank = float(r['RS_Rank'])
                if pd.isna(rank): continue
                if szn == 2017 and rank <= 4:
                    apps += 1
                elif szn > 2017 and rank <= 6:
                    apps += 1
                if szn >= 2018 and rank <= 2:
                    byes += 1
                    
            po_games = games[(games['Team_Name'] == t) & (games['Game_Type'] == 2)]
            round_str = po_games['Playoff_Round'].astype(str).str.strip().str.lower()
            
            qf_games = po_games[round_str.str.contains('quarter')]
            qf_w = int(qf_games['W'].sum())
            qf_l = int(qf_games['L'].sum())
            
            sf_games = po_games[round_str.str.contains('semi')]
            sf_w = int(sf_games['W'].sum())
            sf_l = int(sf_games['L'].sum())
            
            f_games = po_games[round_str.str.contains('final|champ') & ~round_str.str.contains('quarter|semi')]
            f_w = int(f_games['W'].sum())
            f_l = int(f_games['L'].sum())
            
            tot_w = qf_w + sf_w + f_w
            tot_l = qf_l + sf_l + f_l
            
            po_records_list.append({
                'Team': t,
                'Appearances': apps,
                'Byes': byes,
                'Total_W': tot_w,
                'Total_L': tot_l,
                'QF_W': qf_w,
                'QF_L': qf_l,
                'SF_W': sf_w,
                'SF_L': sf_l,
                'F_W': f_w,
                'F_L': f_l
            })
            
        po_df = pd.DataFrame(po_records_list).sort_values(['Appearances', 'Total_W', 'Byes'], ascending=[False, False, False]).reset_index(drop=True)
        
        po_html = (
            '<table style="width: 100%; border-collapse: collapse; text-align: center;">'
            '<thead>'
            '<tr>'
            '<th rowspan="2" style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Team</th>'
            '<th rowspan="2" style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Playoff Appearances</th>'
            '<th rowspan="2" style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Byes</th>'
            '<th colspan="2" style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Total Postseason</th>'
            '<th colspan="2" style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Quarterfinals</th>'
            '<th colspan="2" style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Semifinals</th>'
            '<th colspan="2" style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Finals</th>'
            '</tr>'
            '<tr>'
            '<th style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Win</th>'
            '<th style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Loss</th>'
            '<th style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Win</th>'
            '<th style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Loss</th>'
            '<th style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Win</th>'
            '<th style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Loss</th>'
            '<th style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Win</th>'
            '<th style="text-align: center; padding: 6px 8px; border: 1px solid #e6e6e6;">Loss</th>'
            '</tr>'
            '</thead>'
            '<tbody>'
        )
        for _, r in po_df.iterrows():
            po_html += (
                '<tr>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["Team"]}</td>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["Appearances"]}</td>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["Byes"]}</td>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["Total_W"]}</td>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["Total_L"]}</td>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["QF_W"]}</td>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["QF_L"]}</td>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["SF_W"]}</td>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["SF_L"]}</td>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["F_W"]}</td>'
                f'<td style="padding: 6px 8px; border: 1px solid #e6e6e6; text-align: center;">{r["F_L"]}</td>'
                '</tr>'
            )
        po_html += '</tbody></table>'
        st.markdown(po_html, unsafe_allow_html=True)

with tab_player:
    if box_df.empty:
        st.warning("Player data not found. Please ensure 'espn_fantasy_complete_stats_2017_2026.xlsx' is located in this folder.")
    else:
        dps_c1, dps_c2, dps_c3 = st.columns([1.5, 1.5, 2])
        dps_team = dps_c1.selectbox("Select Manager", teams, key="dps_team")
        dps_year = dps_c2.selectbox("Season", ["All-Time"] + seasons_list, key="dps_year")
        dps_pos_view = dps_c3.selectbox("Position View", ["All Positions", "QB", "RB", "WR", "TE", "K", "D/ST"], key="dps_pos")

        col_dyn_header = "Years" if dps_year == "All-Time" else "Weeks"

        def format_ranges(nums):
            if not nums:
                return ""
            clean_nums = sorted(list(set(int(x) for x in nums if pd.notnull(x))))
            if not clean_nums:
                return ""
            ranges = []
            start = clean_nums[0]
            end = clean_nums[0]
            for n in clean_nums[1:]:
                if n == end + 1:
                    end = n
                else:
                    ranges.append(f"{start}-{end}" if start != end else f"{start}")
                    start = n
                    end = n
            ranges.append(f"{start}-{end}" if start != end else f"{start}")
            return ", ".join(ranges)

        b_clean = box_df.copy()
        b_clean['Season_Str'] = b_clean['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        b_clean['Week_Num'] = pd.to_numeric(b_clean['Week'], errors='coerce').fillna(0).astype(int)
        b_clean['Team_Str'] = b_clean['Team_Name'].astype(str).str.strip()

        el_games = games[(games['Team_Name'] == dps_team) & (games['Game_Type'].isin([1, 2, 4]))][['Season', 'Week', 'Team_Name']].drop_duplicates()
        el_games['Season_Str'] = el_games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        el_games['Week_Num'] = pd.to_numeric(el_games['Week'], errors='coerce').fillna(0).astype(int)
        el_games['Team_Str'] = el_games['Team_Name'].astype(str).str.strip()

        slot_c = 'Slot' if 'Slot' in b_clean.columns else ('Lineup_Slot' if 'Lineup_Slot' in b_clean.columns else 'Position')
        name_c = 'Player_Name' if 'Player_Name' in b_clean.columns else 'Player'
        pts_c = 'Actual_Points' if 'Actual_Points' in b_clean.columns else 'Points'
        pos_c = 'Position' if 'Position' in b_clean.columns else ('Pos' if 'Pos' in b_clean.columns else slot_c)

        nfl_col = None
        for cand in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev', 'Team_Abbr', 'Pro_Team_Abbrev', 'Pro Team', 'NFL Team']:
            if cand in b_clean.columns:
                nfl_col = cand
                break
        if not nfl_col and 'Team' in b_clean.columns and 'Team_Name' in b_clean.columns:
            nfl_col = 'Team'

        b_clean['NFL_Team_Clean'] = b_clean[nfl_col].fillna('').astype(str).str.strip() if nfl_col else ""

        is_starter = ~b_clean[slot_c].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])
        starters = b_clean[(b_clean['Team_Str'] == dps_team) & is_starter]

        counted_box = pd.merge(starters, el_games[['Season_Str', 'Week_Num', 'Team_Str']], on=['Season_Str', 'Week_Num', 'Team_Str'], how='inner')

        if dps_year != "All-Time":
            counted_box = counted_box[counted_box['Season_Str'] == str(dps_year)]

        def clean_pos_val(val):
            p = str(val).strip().upper()
            if p == 'QB': return 'QB'
            if p == 'RB': return 'RB'
            if p == 'WR': return 'WR'
            if p == 'TE': return 'TE'
            if p in ['K', 'PK']: return 'K'
            if p in ['D/ST', 'DST', 'DEF', 'DP']: return 'D/ST'
            return p

        counted_box['Clean_Pos'] = counted_box[pos_c].apply(clean_pos_val)
        counted_box[pts_c] = pd.to_numeric(counted_box[pts_c], errors='coerce').fillna(0)

        def find_col(cands, fallback_keywords=None, fallback_exclude=None):
            for cand in cands:
                cand_norm = cand.lower().replace('_', '').replace(' ', '')
                for c in counted_box.columns:
                    c_norm = str(c).lower().replace('_', '').replace(' ', '')
                    if c_norm == cand_norm:
                        return c
            if fallback_keywords:
                for c in counted_box.columns:
                    c_str = str(c).lower().replace(' ', '_')
                    if all(kw in c_str for kw in fallback_keywords):
                        if fallback_exclude and any(ex in c_str for ex in fallback_exclude):
                            continue
                        return c
            return None

        col_pass_yds = find_col(['Passing_Yards', 'Pass_Yards', 'Passing_Yds', 'Pass_Yds'], fallback_keywords=['pass', 'yard'])
        col_pass_td = find_col(['Passing_TDs', 'Passing_TD', 'Pass_TDs', 'Pass_TD', 'Passing_Touchdowns'], fallback_keywords=['pass', 'td'], fallback_exclude=['rush', 'rec', 'def'])
        col_pass_int = find_col(['Passing_Interceptions', 'Passing_Int', 'Pass_Int', 'Interceptions', 'INT'], fallback_keywords=['int'], fallback_exclude=['def'])
        col_rush_yds = find_col(['Rushing_Yards', 'Rush_Yards', 'Rushing_Yds', 'Rush_Yds'], fallback_keywords=['rush', 'yard'])
        col_rush_td = find_col(['Rushing_TDs', 'Rushing_TD', 'Rush_TDs', 'Rush_TD', 'Rushing_Touchdowns'], fallback_keywords=['rush', 'td'], fallback_exclude=['pass', 'rec', 'def'])
        col_rec = find_col(['Receptions', 'Reception', 'Rec', 'Catches'], fallback_keywords=['rec'], fallback_exclude=['yard', 'td', 'touchdown', 'pass', 'rush', 'def', 'fum', 'int'])
        col_rec_yds = find_col(['Receiving_Yards', 'Receiving_Yds', 'Rec_Yards', 'Rec_Yds'], fallback_keywords=['rec', 'yard'], fallback_exclude=['pass', 'rush'])
        col_rec_td = find_col(
            ['Receiving_TDs', 'Receiving_TD', 'Rec_TDs', 'Rec_TD', 'Receiving_Touchdowns', 'Receiving_Touchdown', 'Rec_Touchdowns', 'Rec_Touchdown', 'TD_Receiving', 'TD_Rec'],
            fallback_keywords=['rec', 'td'],
            fallback_exclude=['pass', 'rush', 'def', 'int', 'return', 'fum']
        )
        if not col_rec_td:
            col_rec_td = find_col([], fallback_keywords=['rec', 'touchdown'], fallback_exclude=['pass', 'rush', 'def', 'int', 'return', 'fum'])

        col_sacks = find_col(['Sacks', 'Sack'])
        col_def_int = find_col(['Defensive_Interceptions', 'Def_INT', 'Defensive_Int'], fallback_keywords=['def', 'int'])
        col_def_td = find_col(['Defensive_TDs', 'Defensive_TD', 'Def_TD', 'Def_TDs'], fallback_keywords=['def', 'td'])
        col_fum_rec = find_col(['Fumbles_Recovered', 'Fum_Rec', 'FR'], fallback_keywords=['fum', 'rec'])
        col_fgm = find_col(['Field_Goals_Made', 'FG_Made', 'FGM'], fallback_keywords=['fg', 'made'])
        col_xpm = find_col(['Extra_Points_Made', 'XP_Made', 'XPM'], fallback_keywords=['xp', 'made'])

        def get_stat_sum(grp, col):
            if col and col in grp.columns:
                return int(round(pd.to_numeric(grp[col], errors='coerce').fillna(0).sum()))
            return 0

        def build_pos_table(target_pos):
            pos_data = counted_box[counted_box['Clean_Pos'] == target_pos].copy()
            if pos_data.empty:
                return pd.DataFrame()

            rows = []
            for player, grp in pos_data.groupby(name_c):
                tot_pts = pd.to_numeric(grp[pts_c], errors='coerce').fillna(0).sum()
                if tot_pts <= 0:
                    continue
                starts = len(grp)
                ppg = tot_pts / starts if starts > 0 else 0.0

                nfl_teams_list = sorted(list(set(t for t in grp['NFL_Team_Clean'].tolist() if t)))
                nfl_tm_str = ", ".join(nfl_teams_list) if nfl_teams_list else "-"

                if dps_year == "All-Time":
                    seasons_arr = sorted(list(set(str(s) for s in grp['Season_Str'].dropna().unique())), key=lambda x: int(x) if x.isdigit() else 0)
                    time_str = ", ".join(seasons_arr)
                else:
                    weeks_arr = sorted(list(set(int(w) for w in grp['Week_Num'].dropna().unique())))
                    time_str = format_ranges(weeks_arr)

                row_item = {
                    'Player': player,
                    'NFL Team': nfl_tm_str,
                    'Starts': starts,
                    'Points_Num': tot_pts,
                    'Points': f"{tot_pts:.1f}",
                    'PPG': f"{ppg:.1f}",
                    col_dyn_header: time_str
                }

                if target_pos == 'QB':
                    row_item['Pass Yds'] = get_stat_sum(grp, col_pass_yds)
                    row_item['Pass TD'] = get_stat_sum(grp, col_pass_td)
                    row_item['INT'] = get_stat_sum(grp, col_pass_int)
                    row_item['Rush Yds'] = get_stat_sum(grp, col_rush_yds)
                    row_item['Rush TD'] = get_stat_sum(grp, col_rush_td)
                elif target_pos == 'RB':
                    row_item['Rush Yds'] = get_stat_sum(grp, col_rush_yds)
                    row_item['Rush TD'] = get_stat_sum(grp, col_rush_td)
                    row_item['Rec'] = get_stat_sum(grp, col_rec)
                    row_item['Rec Yds'] = get_stat_sum(grp, col_rec_yds)
                    row_item['Rec TD'] = get_stat_sum(grp, col_rec_td)
                elif target_pos in ['WR', 'TE']:
                    row_item['Rec'] = get_stat_sum(grp, col_rec)
                    row_item['Rec Yds'] = get_stat_sum(grp, col_rec_yds)
                    row_item['Rec TD'] = get_stat_sum(grp, col_rec_td)
                    if target_pos == 'WR':
                        row_item['Rush Yds'] = get_stat_sum(grp, col_rush_yds)
                        row_item['Rush TD'] = get_stat_sum(grp, col_rush_td)
                elif target_pos == 'K':
                    if col_fgm: row_item['FGM'] = get_stat_sum(grp, col_fgm)
                    if col_xpm: row_item['XPM'] = get_stat_sum(grp, col_xpm)
                elif target_pos == 'D/ST':
                    if col_sacks: row_item['Sacks'] = get_stat_sum(grp, col_sacks)
                    if col_def_int: row_item['INT'] = get_stat_sum(grp, col_def_int)
                    if col_fum_rec: row_item['FR'] = get_stat_sum(grp, col_fum_rec)
                    if col_def_td: row_item['TD'] = get_stat_sum(grp, col_def_td)

                rows.append(row_item)

            if not rows:
                return pd.DataFrame()

            df_pos = pd.DataFrame(rows).sort_values(['Points_Num', 'Starts'], ascending=[False, False]).reset_index(drop=True)

            if target_pos == 'QB':
                col_order = ['Player', 'NFL Team', 'Starts', 'Pass Yds', 'Pass TD', 'INT', 'Rush Yds', 'Rush TD', 'Points', 'PPG', col_dyn_header]
            elif target_pos == 'RB':
                col_order = ['Player', 'NFL Team', 'Starts', 'Rush Yds', 'Rush TD', 'Rec', 'Rec Yds', 'Rec TD', 'Points', 'PPG', col_dyn_header]
            elif target_pos == 'WR':
                col_order = ['Player', 'NFL Team', 'Starts', 'Rec', 'Rec Yds', 'Rec TD', 'Rush Yds', 'Rush TD', 'Points', 'PPG', col_dyn_header]
            elif target_pos == 'TE':
                col_order = ['Player', 'NFL Team', 'Starts', 'Rec', 'Rec Yds', 'Rec TD', 'Points', 'PPG', col_dyn_header]
            elif target_pos == 'K':
                col_order = ['Player', 'NFL Team', 'Starts']
                if col_fgm: col_order.append('FGM')
                if col_xpm: col_order.append('XPM')
                col_order.extend(['Points', 'PPG', col_dyn_header])
            elif target_pos == 'D/ST':
                col_order = ['Player', 'Starts']
                if col_sacks: col_order.append('Sacks')
                if col_def_int: col_order.append('INT')
                if col_fum_rec: col_order.append('FR')
                if col_def_td: col_order.append('TD')
                col_order.extend(['Points', 'PPG', col_dyn_header])

            return df_pos[[c for c in col_order if c in df_pos.columns]]

        positions_to_render = ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST'] if dps_pos_view == "All Positions" else [dps_pos_view]
        pos_titles = {
            'QB': 'Quarterbacks (QB)',
            'RB': 'Running Backs (RB)',
            'WR': 'Wide Receivers (WR)',
            'TE': 'Tight Ends (TE)',
            'K': 'Kickers (K)',
            'D/ST': 'Defense / Special Teams (D/ST)'
        }

        for p_code in positions_to_render:
            st.write(f"### {pos_titles[p_code]}")
            table_df = build_pos_table(p_code)
            if not table_df.empty:
                render_html_table(table_df)
            else:
                st.info(f"No {pos_titles[p_code]} with points scored on record for {dps_team} ({dps_year}).")
            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
            
