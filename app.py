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
        comp_valid = comp_games[comp_games['Actual_Points'] > 0]
        if not comp_valid.empty:
            low_row = comp_valid.loc[comp_valid['Actual_Points'].idxmin()]
            low_score_str = f"{low_row['Actual_Points']:.1f} ({str(low_row['Season']).replace('.0','')}, W{low_row['Week']})"
        else:
            low_score_str = "N/A"
        
        valid_opp_games = comp_games[comp_games['Opponent_Team_Name'].str.upper() != 'CAM']
        if not valid_opp_games.empty:
            opp_stats = valid_opp_games.groupby('Opponent_Team_Name').agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum')).reset_index()
            opp_stats['Games'] = opp_stats['W'] + opp_stats['L'] + opp_stats['T']
            opp_stats = opp_stats[opp_stats['Games'] > 0]
            
            if not opp_stats.empty:
                opp_stats['Win %'] = opp_stats['W'] / opp_stats['Games']
                
                def format_opp_list(df_sub):
                    records = [f"{int(r['W'])}-{int(r['L'])}-{int(r['T'])}" if r['T'] > 0 else f"{int(r['W'])}-{int(r['L'])}" for _, r in df_sub.iterrows()]
                    if len(set(records)) == 1:
                        names = ", ".join(df_sub['Opponent_Team_Name'].tolist())
                        return f"{names} ({records[0]})"
                    else:
                        items = [f"{r['Opponent_Team_Name']} ({rec})" for (_, r), rec in zip(df_sub.iterrows(), records)]
                        return ", ".join(items)

                max_wp = opp_stats['Win %'].max()
                easiest_candidates = opp_stats[opp_stats['Win %'] == max_wp]
                max_games_easiest = easiest_candidates['Games'].max()
                easiest_final = easiest_candidates[easiest_candidates['Games'] == max_games_easiest]
                easiest_str = format_opp_list(easiest_final)
                
                min_wp = opp_stats['Win %'].min()
                toughest_candidates = opp_stats[opp_stats['Win %'] == min_wp]
                max_games_toughest = toughest_candidates['Games'].max()
                toughest_final = toughest_candidates[toughest_candidates['Games'] == max_games_toughest]
                toughest_str = format_opp_list(toughest_final)
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
        if szn_str not in completed_playoff_seasons: continue
        szn = int(szn_str)
        rank = float(row['RS_Rank'])
        
        if pd.isna(rank): continue
        if szn == 2017 and rank <= 4:
            playoff_apps += 1
        elif szn > 2017 and rank <= 6:
            playoff_apps += 1
            
        if szn >= 2018 and rank <= 2:
            playoff_byes += 1
            
    all_time_qb_str = "N/A"
    all_time_rb_str = "N/A"
    all_time_wr_str = "N/A"
    all_time_te_str = "N/A"
    all_time_dst_str = "N/A"
    all_time_k_str = "N/A"
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
                
                def get_all_time_top(target_positions):
                    pos_df = counted_box[counted_box['Clean_Pos'].isin(target_positions)]
                    if pos_df.empty:
                        return "N/A"
                    p_totals = pos_df.groupby(name_c)[pts_c].sum().reset_index()
                    if p_totals.empty:
                        return "N/A"
                    top_row = p_totals.sort_values(pts_c, ascending=False).iloc[0]
                    return f"{top_row[name_c]} ({top_row[pts_c]:,.1f} pts)"
                
                all_time_qb_str = get_all_time_top(['QB'])
                all_time_rb_str = get_all_time_top(['RB'])
                all_time_wr_str = get_all_time_top(['WR'])
                all_time_te_str = get_all_time_top(['TE'])
                all_time_dst_str = get_all_time_top(['D/ST', 'DST', 'DEF', 'DP'])
                all_time_k_str = get_all_time_top(['K', 'PK'])
                
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
            
    c_stat1, c_stat2, c_stat3 = st.columns(3)
    with c_stat1:
        st.markdown(f"**Championships:** {champ_str}")
        st.markdown(f"**Reg. Season Record:** {tw}-{tl}-{tt} ({win_pct_str})")
        st.markdown(f"**Playoff Record:** {pw}-{pl}-{pt}")
        st.markdown(f"**Playoff Appearances:** {playoff_apps}")
        st.markdown(f"**Playoff Byes:** {playoff_byes}")
        st.markdown(f"**Weekly Bags Won:** {high_scorer_count}")
    with c_stat2:
        st.markdown(f"**Highest Scoring Game:** {high_score_str}")
        st.markdown(f"**Lowest Scoring Game:** {low_score_str}")
        st.markdown(f"**Easiest Opponent:** {easiest_str}")
        st.markdown(f"**Toughest Opponent:** {toughest_str}")
        st.markdown(f"**Longest Win Streak:** {longest_w} games ({w_span})")
        st.markdown(f"**Longest Losing Streak:** {longest_l} games ({l_span})")
    with c_stat3:
        st.markdown(f"**Top Scoring QB:** {all_time_qb_str}")
        st.markdown(f"**Top Scoring RB:** {all_time_rb_str}")
        st.markdown(f"**Top Scoring WR:** {all_time_wr_str}")
        st.markdown(f"**Top Scoring TE:** {all_time_te_str}")
        st.markdown(f"**Top Scoring D/ST:** {all_time_dst_str}")
        st.markdown(f"**Top Scoring K:** {all_time_k_str}")
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
    
    all_reg = games[games['Game_Type'] == 1].copy()
    all_reg['Season_Str'] = all_reg['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    pf_totals = all_reg.groupby(['Season_Str', 'Team_Name']).agg(Actual_Points=('Actual_Points', 'sum'), Opp_Points=('Opp_Points', 'sum')).reset_index()
    pf_totals['PF_Rank'] = pf_totals.groupby('Season_Str')['Actual_Points'].rank(ascending=False, method='min').astype(int)
    pf_totals['PA_Rank'] = pf_totals.groupby('Season_Str')['Opp_Points'].rank(ascending=False, method='min').astype(int)
    
    pf_totals_team = pf_totals[pf_totals['Team_Name'] == selected_team][['Season_Str', 'PF_Rank', 'PA_Rank']].rename(columns={'Season_Str': 'Season'})
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
    
    all_reg['Weekly_Rank'] = all_reg.groupby(['Season_Str', 'Week_Num'])['Actual_Points'].rank(ascending=False, method='average')
    all_reg['N_Teams'] = all_reg.groupby(['Season_Str', 'Week_Num'])['Team_Name'].transform('count')
    all_reg['Exp_Win'] = all_reg.apply(
        lambda r: (r['N_Teams'] - r['Weekly_Rank']) / (r['N_Teams'] - 1) if r['N_Teams'] > 1 else 0.0,
        axis=1
    )
    
    xw_totals = all_reg.groupby(['Season_Str', 'Team_Name'])['Exp_Win'].sum().reset_index()
    xw_totals_team = xw_totals[xw_totals['Team_Name'] == selected_team].rename(columns={'Season_Str': 'Season', 'Exp_Win': 'Exp_Win_Total'})
    
    szn_stats = pd.merge(szn_stats, xw_totals_team[['Season', 'Exp_Win_Total']], on='Season', how='left')
    szn_stats['Expected Wins'] = szn_stats['Exp_Win_Total'].fillna(0).apply(lambda x: f"{x:.1f}")
    
    def calc_luck(r):
        w = r['W']
        xw = r['Exp_Win_Total']
        if pd.isna(xw):
            return "0.0"
        diff = w - xw
        if abs(diff) < 0.05:
            return "0.0"
        return f"{diff:+.1f}"
        
    szn_stats['Luck Factor'] = szn_stats.apply(calc_luck, axis=1)
    
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
        'Playoff Outcome', 'Weekly Bags', 'Expected Wins', 'Luck Factor',
        'Top QB', 'Top RB', 'Top WR', 'Top TE'
    ]
    display_df = szn_stats.rename(columns={'PF_Rank': 'PF Rank', 'PA_Rank': 'PA Rank'})[display_cols].sort_values('Season', ascending=False)
    
    def highlight_szn_cells(row):
        styles = ['' for _ in row.index]
        szn_val = str(row.get('Season', '')).replace('.0', '').strip()
        if szn_val in ['2017', '2018']:
            gray_cols = ['Weekly Bags', 'Top QB', 'Top RB', 'Top WR', 'Top TE']
            for col in gray_cols:
                if col in row.index:
                    idx = row.index.get_loc(col)
                    styles[idx] = 'background-color: #ebebeb; color: #888888;'
        return styles

    render_html_table(display_df, highlight_fn=highlight_szn_cells)
    
    st.divider()
    st.write("### Playoff Game Log")
    display_playoffs = playoffs.sort_values(['Season_Num', 'Week_Num'], ascending=[False, False])
    if not display_playoffs.empty:
        display_playoffs['Season'] = display_playoffs['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        display_playoffs['Score'] = display_playoffs['Actual_Points'].round(1).astype(str) + " - " + display_playoffs['Opp_Points'].round(1).astype(str)
        
        po_display_df = display_playoffs[['Season', 'Week', 'Playoff_Round', 'Opponent_Team_Name', 'Result', 'Score']].rename(columns={'Opponent_Team_Name': 'Opponent', 'Playoff_Round': 'Round'})
        render_html_table(po_display_df)
        
        display_playoffs['Game_Label'] = display_playoffs['Season'] + " Week " + display_playoffs['Week'].astype(str) + " vs " + display_playoffs['Opponent_Team_Name']
        view_po_wk = st.selectbox("Select Playoff Game to View Box Score:", ["Select..."] + display_playoffs['Game_Label'].tolist(), key="po_box")
        if view_po_wk != "Select...":
            po_row = display_playoffs[display_playoffs['Game_Label'] == view_po_wk].iloc[0]
            display_box_score(po_row['Season'], po_row['Week'], selected_team, box_df, games)
    else:
        st.write("No playoff appearances on record.")
        
    st.divider()
    st.write("### Head-to-Head vs. All Opponents")
    all_opponents = sorted([t for t in teams if t != selected_team])
    h2h_summary_list = []
    for opp in all_opponents:
        opp_games = games[(games['Team_Name'] == selected_team) & (games['Opponent_Team_Name'] == opp) & (games['Game_Type'].isin([1, 2]))]
        if opp_games.empty:
            continue
        tot_w = int(opp_games['W'].sum())
        tot_l = int(opp_games['L'].sum())
        tot_t = int(opp_games['T'].sum())
        tot_g = tot_w + tot_l + tot_t
        win_p = tot_w / tot_g if tot_g > 0 else 0.0
        win_p_str = f"{win_p:.3f}".replace("0.", ".", 1) if win_p < 1 else f"{win_p:.3f}"
        pf_sum = int(round(opp_games['Actual_Points'].sum()))
        pa_sum = int(round(opp_games['Opp_Points'].sum()))
        
        po_g = opp_games[opp_games['Game_Type'] == 2]
        po_w = int(po_g['W'].sum())
        po_l = int(po_g['L'].sum())
        po_t = int(po_g['T'].sum())
        if (po_w + po_l + po_t) > 0:
            po_rec_str = f"{po_w}-{po_l}-{po_t}" if po_t > 0 else f"{po_w}-{po_l}"
        else:
            po_rec_str = "-"
            
        row_dict = {
            'Opponent': opp,
            'GP': tot_g,
            'W': tot_w,
            'L': tot_l,
            'T': tot_t,
            'Win_Pct_Raw': win_p,
            'Win %': win_p_str,
            'PF': pf_sum,
            'PA': pa_sum,
            'Playoff Record': po_rec_str
        }
        h2h_summary_list.append(row_dict)
        
    if h2h_summary_list:
        h2h_summary_df = pd.DataFrame(h2h_summary_list)
        h2h_summary_df = h2h_summary_df.sort_values(['Win_Pct_Raw', 'W', 'GP'], ascending=[False, False, False]).reset_index(drop=True)
        disp_h2h_cols = ['Opponent', 'GP', 'W', 'L', 'Win %', 'PF', 'PA', 'Playoff Record']
        render_html_table(h2h_summary_df[disp_h2h_cols])
    else:
        st.write("No head-to-head matchup history found.")

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
        
        render_html_table(disp_sched, highlight_sched_winners)
        
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
        b_season = c1.selectbox("Season", seasons_list, key="b_szn")
        avail_weeks = sorted(box_df[box_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == str(b_season)]['Week'].dropna().unique().tolist())
        b_week = c2.selectbox("Week", avail_weeks, key="b_wk")
        avail_teams = sorted(box_df[(box_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == str(b_season)) & (box_df['Week'] == b_week)]['Team_Name'].dropna().unique().tolist())
        b_team = c3.selectbox("Manager", avail_teams, key="b_tm")
        
        if b_team:
            display_box_score(b_season, b_week, b_team, box_df, games)

with tab2:
    top_col1, top_col2 = st.columns(2)
    with top_col1:
        team_a = st.selectbox("Team A", teams)
        avail_opps = [t for t in teams if t != team_a]
        team_b = st.selectbox("Team B", avail_opps)
        
    h2h_games = games[(games['Team_Name'] == team_a) & (games['Opponent_Team_Name'] == team_b) & (games['Game_Type'].isin([1, 2]))].copy()
    if not h2h_games.empty:
        w, l, t = h2h_games['W'].sum(), h2h_games['L'].sum(), h2h_games['T'].sum()
        
        po_h2h = h2h_games[h2h_games['Game_Type'] == 2]
        pw, pl, pt = po_h2h['W'].sum(), po_h2h['L'].sum(), po_h2h['T'].sum()
        
        with top_col2:
            st.write(f"### {team_a} vs. {team_b}")
            if w > l:
                st.markdown(f"**Series Leader:** {team_a} leads {w}-{l}-{t}" if t > 0 else f"**Series Leader:** {team_a} leads {w}-{l}")
            elif l > w:
                st.markdown(f"**Series Leader:** {team_b} leads {l}-{w}-{t}" if t > 0 else f"**Series Leader:** {team_b} leads {l}-{w}")
            else:
                st.markdown(f"**Series Leader:** Tied {w}-{l}-{t}" if t > 0 else f"**Series Leader:** Tied {w}-{l}")
                
            if (pw + pl + pt) == 0:
                st.markdown("**Playoff Record:** No playoff matchups have occurred")
            elif pw > pl:
                st.markdown(f"**Playoff Record:** {team_a} leads {pw}-{pl}-{pt}" if pt > 0 else f"**Playoff Record:** {team_a} leads {pw}-{pl}")
            elif pl > pw:
                st.markdown(f"**Playoff Record:** {team_b} leads {pl}-{pw}-{pt}" if pt > 0 else f"**Playoff Record:** {team_b} leads {pl}-{pw}")
            else:
                st.markdown(f"**Playoff Record:** Tied {pw}-{pl}-{pt}" if pt > 0 else f"**Playoff Record:** Tied {pw}-{pl}")
                
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
        
        render_html_table(disp_table, highlight_winners)
    else:
        st.write("No matchups found between these teams.")

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
        
