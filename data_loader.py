import streamlit as st
import pandas as pd

@st.cache_data(ttl=600)
def load_box_scores():
    try:
        return pd.read_excel("espn_fantasy_complete_stats_2017_2026.xlsx", sheet_name="Box_Scores", engine="openpyxl")
    except:
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def load_nfl_monday_teams():
    lookup = set()
    try:
        url = "https://github.com/nflverse/nflverse-data/releases/download/schedules/schedules.csv"
        sched = pd.read_csv(url, usecols=['season', 'week', 'weekday', 'away_team', 'home_team', 'gameday'])
        mon_mask = sched['weekday'].fillna('').astype(str).str.strip().str.capitalize() == 'Monday'
        if 'gameday' in sched.columns:
            try:
                mon_mask = mon_mask | (pd.to_datetime(sched['gameday']).dt.weekday == 0)
            except:
                pass
        mon_games = sched[mon_mask]
        alias_map = {
            'WSH': 'WAS', 'WAS': 'WSH', 'JAX': 'JAC', 'JAC': 'JAX',
            'OAK': 'LV', 'LV': 'OAK', 'LA': 'LAR', 'LAR': 'LA',
            'SD': 'LAC', 'LAC': 'SD'
        }
        for _, r in mon_games.iterrows():
            s, w = str(r['season']).strip(), int(r['week'])
            for tm_col in ['away_team', 'home_team']:
                tm = str(r[tm_col]).strip().upper()
                lookup.add((s, w, tm))
                if tm in alias_map: lookup.add((s, w, alias_map[tm]))
    except Exception:
        pass
    return lookup

@st.cache_data(ttl=600)
def get_game_top_scorers(box_df):
    if box_df.empty: return {}
    slot_c = 'Slot' if 'Slot' in box_df.columns else ('Lineup_Slot' if 'Lineup_Slot' in box_df.columns else 'Position')
    name_c = 'Player_Name' if 'Player_Name' in box_df.columns else 'Player'
    pts_c = 'Actual_Points' if 'Actual_Points' in box_df.columns else 'Points'
    
    b_clean = box_df.copy()
    b_clean['Season_Str'] = b_clean['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    b_clean['Week_Num'] = pd.to_numeric(b_clean['Week'], errors='coerce').fillna(0).astype(int)
    b_clean['Team_Str'] = b_clean['Team_Name'].astype(str).str.strip()
    b_clean[pts_c] = pd.to_numeric(b_clean[pts_c], errors='coerce').fillna(0)
    
    starters = b_clean[~b_clean[slot_c].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])]
    top = starters.sort_values(pts_c, ascending=False).drop_duplicates(subset=['Season_Str', 'Week_Num', 'Team_Str'])
    top['Player_Label'] = top.apply(lambda r: f"{r[name_c]} ({r[pts_c]:.1f})", axis=1)
    return dict(zip(zip(top['Season_Str'], top['Week_Num'], top['Team_Str']), top['Player_Label']))

@st.cache_data(ttl=600)
def load_rs_rankings(file_path, teams_list, games=None):
    try:
        df = pd.read_excel(file_path, sheet_name="All Time W-L", engine="pyxlsb", header=None)
        year_row_idx, team_col_idx = None, None
        for i, row in df.iterrows():
            years_count = sum(
                1 for x in row 
                if str(x).replace('.0','').strip().isdigit() and 2010 < int(str(x).replace('.0','').strip()) < 2030
            )
            if years_count >= 3:
                year_row_idx = i
                break
        for j in df.columns:
            if df[j].astype(str).apply(lambda x: x.strip() in teams_list).sum() >= 5:
                team_col_idx = j
                break
        if year_row_idx is not None and team_col_idx is not None:
            headers = [str(x).replace('.0','').strip() for x in df.iloc[year_row_idx]]
            data = df.iloc[year_row_idx+1:].copy()
            data.columns = headers
            team_header = headers[team_col_idx]
            data = data.rename(columns={team_header: 'Team_Name'})
            year_cols = [c for c in data.columns if c.isdigit() and 2010 < int(c) < 2030]
            if year_cols:
                ranks = data[['Team_Name'] + year_cols].melt(id_vars='Team_Name', var_name='Season', value_name='RS_Rank')
                ranks['Season'] = ranks['Season'].astype(str).str.strip()
                ranks['RS_Rank'] = pd.to_numeric(ranks['RS_Rank'], errors='coerce')
                ranks['Team_Name'] = ranks['Team_Name'].astype(str).str.strip()
                ranks = ranks.dropna(subset=['RS_Rank'])
                if not ranks.empty:
                    return ranks
    except Exception:
        pass

    # Built-in Fallback: compute directly from regular season games
    if games is not None and not games.empty:
        reg = games[games['Game_Type'] == 1].copy()
        if not reg.empty:
            szn_st = reg.groupby(['Season', 'Team_Name']).agg(
                W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum'), PF=('Actual_Points', 'sum')
            ).reset_index()
            szn_st['Win %'] = (szn_st['W'] / (szn_st['W'] + szn_st['L'] + szn_st['T'])).fillna(0)
            szn_st = szn_st.sort_values(['Season', 'Win %', 'PF'], ascending=[False, False, False])
            szn_st['RS_Rank'] = szn_st.groupby('Season').cumcount() + 1
            res = szn_st[['Season', 'Team_Name', 'RS_Rank']].copy()
            res['Season'] = res['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            return res

    return pd.DataFrame(columns=['Team_Name', 'Season', 'RS_Rank'])

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
    base_cols_w = ['Year', 'Matchup Week', 'Playoff Round', 'Game Type', 'Winner', 'Winner Points', 'Loser', 'Loser Points']
    base_cols_l = ['Year', 'Matchup Week', 'Playoff Round', 'Game Type', 'Loser', 'Loser Points', 'Winner', 'Winner Points']
    if top2_col: base_cols_w.append(top2_col); base_cols_l.append(top2_col)
    if bot2_col: base_cols_w.append(bot2_col); base_cols_l.append(bot2_col)
    
    col_names = ['Season', 'Week', 'Playoff_Round', 'Game_Type_Str', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points']
    if top2_col: col_names.append('Top_2_Game')
    if bot2_col: col_names.append('Bottom_2_Game')
    
    w_df = df[base_cols_w].copy(); w_df.columns = col_names
    l_df = df[base_cols_l].copy(); l_df.columns = col_names
    games = pd.concat([w_df, l_df], ignore_index=True)
    games = games.dropna(subset=['Team_Name', 'Actual_Points'])
    games = games[~((games['Actual_Points'] == 0) & (games['Opp_Points'] == 0))]
    games['Season'] = games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    games = games[games['Team_Name'].str.upper() != 'BYE']
    
    def map_gt(r):
        gt = str(r.get('Game_Type_Str', '')).strip()
        pr = str(r.get('Playoff_Round', '')).lower()
        if str(r.get('Opponent_Team_Name', '')).strip().upper() == 'BYE': return 4
        if gt == 'Regular Season': return 1
        if 'consolation' in pr or '3rd' in pr: return 3
        return 2

    games['Game_Type'] = games.apply(map_gt, axis=1)
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

def get_starter_performances(box_df, games):
    if box_df.empty or games.empty: return pd.DataFrame()
    b_c = box_df.copy()
    b_c['Season_Str'] = b_c['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    b_c['Week_Num'] = pd.to_numeric(b_c['Week'], errors='coerce').fillna(0).astype(int)
    b_c['Team_Str'] = b_c['Team_Name'].astype(str).str.strip()
    slot_col = 'Slot' if 'Slot' in b_c.columns else ('Lineup_Slot' if 'Lineup_Slot' in b_c.columns else 'Position')
    name_col = 'Player_Name' if 'Player_Name' in b_c.columns else 'Player'
    pts_col = 'Actual_Points' if 'Actual_Points' in b_c.columns else 'Points'
    pos_col = 'Position' if 'Position' in b_c.columns else ('Pos' if 'Pos' in b_c.columns else slot_col)
    
    nfl_c = next((c for c in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev'] if c in b_c.columns), None)
    b_c['NFL Team'] = b_c[nfl_c].fillna('').astype(str).str.strip() if nfl_c else ""
    
    starters = b_c[~b_c[slot_col].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])].copy()
    starters['Points_Num'] = pd.to_numeric(starters[pts_col], errors='coerce').fillna(0)
    
    def clean_p(v):
        p = str(v).strip().upper()
        if p in ['K', 'PK']: return 'K'
        if p in ['D/ST', 'DST', 'DEF', 'DP']: return 'D/ST'
        return p if p in ['QB', 'RB', 'WR', 'TE'] else p
    starters['Pos'] = starters[pos_col].apply(clean_p)
    
    el_g = games[games['Game_Type'].isin([1, 2, 4]) & (games['Team_Name'].str.upper() != 'CAM')].copy()
    el_g['Season_Str'] = el_g['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    el_g['Week_Num'] = pd.to_numeric(el_g['Week'], errors='coerce').fillna(0).astype(int)
    el_g['Team_Str'] = el_g['Team_Name'].astype(str).str.strip()
    el_g['Outcome'] = el_g.apply(lambda r: f"BYE ({float(r['Actual_Points']):.1f})" if r['Game_Type'] == 4 else f"{'W' if r['W']==1 else ('L' if r['L']==1 else 'T')} ({float(r['Actual_Points']):.1f} - {float(r['Opp_Points']):.1f})", axis=1)
    
    merged = pd.merge(starters, el_g[['Season_Str', 'Week_Num', 'Team_Str', 'Opponent_Team_Name', 'Outcome']].drop_duplicates(), on=['Season_Str', 'Week_Num', 'Team_Str'], how='inner')
    merged['Player'] = merged[name_col]
    merged['Season'] = merged['Season_Str']
    merged['Week'] = merged['Week_Num']
    merged['Team'] = merged['Team_Str']
    merged['Opponent'] = merged['Opponent_Team_Name']
    return merged

def get_unique_starters_records(box_df, games, completed_only=False, completed_playoff_seasons=None):
    if box_df.empty or games.empty: return pd.DataFrame(), ""
    b_c = box_df.copy()
    b_c['Season_Str'] = b_c['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    b_c['Week_Num'] = pd.to_numeric(b_c['Week'], errors='coerce').fillna(0).astype(int)
    b_c['Team_Str'] = b_c['Team_Name'].astype(str).str.strip()
    slot_col = 'Slot' if 'Slot' in b_c.columns else ('Lineup_Slot' if 'Lineup_Slot' in b_c.columns else 'Position')
    name_col = 'Player_Name' if 'Player_Name' in b_c.columns else 'Player'
    pos_col = 'Position' if 'Position' in b_c.columns else ('Pos' if 'Pos' in b_c.columns else slot_col)
    
    def clean_p(v):
        p = str(v).strip().upper()
        if p in ['K', 'PK']: return 'K'
        if p in ['D/ST', 'DST', 'DEF', 'DP']: return 'D/ST'
        return p if p in ['QB', 'RB', 'WR', 'TE'] else p
    b_c['Clean_Pos'] = b_c[pos_col].apply(clean_p)
    starters = b_c[~b_c[slot_col].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])].copy()
    
    reg_g = games[games['Game_Type'] == 1].copy()
    reg_g['Season_Str'] = reg_g['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    reg_g['Week_Num'] = pd.to_numeric(reg_g['Week'], errors='coerce').fillna(0).astype(int)
    reg_g['Team_Str'] = reg_g['Team_Name'].astype(str).str.strip()
    if completed_only and completed_playoff_seasons:
        reg_g = reg_g[reg_g['Season_Str'].isin(completed_playoff_seasons)]
    return pd.merge(starters, reg_g[['Season_Str', 'Week_Num', 'Team_Str']].drop_duplicates(), on=['Season_Str', 'Week_Num', 'Team_Str'], how='inner'), name_col

def get_all_streaks_records(games):
    g = games[games['Game_Type'].isin([1, 2])].copy()
    g['Season_Str'] = g['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    g['Week_Num'] = pd.to_numeric(g['Week'], errors='coerce').fillna(0).astype(int)
    g = g.sort_values(['Team_Name', 'Season_Num', 'Week_Num'])
    win_streaks, loss_streaks = [], []
    for (tm, szn), grp in g.groupby(['Team_Name', 'Season_Str']):
        curr_w, curr_l, w_start, l_start, prev_w = 0, 0, None, None, None
        for _, r in grp.iterrows():
            wk, res = r['Week'], ('W' if r['W']==1 else ('L' if r['L']==1 else 'T'))
            if res == 'W':
                if curr_w == 0: w_start = wk
                curr_w += 1
                if curr_l > 0:
                    loss_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_l, 'Span': f"Week {l_start} to Week {prev_w}" if l_start != prev_w else f"Week {l_start}"})
                    curr_l, l_start = 0, None
            elif res == 'L':
                if curr_l == 0: l_start = wk
                curr_l += 1
                if curr_w > 0:
                    win_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_w, 'Span': f"Week {w_start} to Week {prev_w}" if w_start != prev_w else f"Week {w_start}"})
                    curr_w, w_start = 0, None
            else:
                if curr_w > 0:
                    win_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_w, 'Span': f"Week {w_start} to Week {prev_w}" if w_start != prev_w else f"Week {w_start}"})
                    curr_w, w_start = 0, None
                if curr_l > 0:
                    loss_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_l, 'Span': f"Week {l_start} to Week {prev_w}" if l_start != prev_w else f"Week {l_start}"})
                    curr_l, l_start = 0, None
            prev_w = wk
        if curr_w > 0: win_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_w, 'Span': f"Week {w_start} to Week {prev_w}" if w_start != prev_w else f"Week {w_start}"})
        if curr_l > 0: loss_streaks.append({'Team': tm, 'Season': szn, 'Length': curr_l, 'Span': f"Week {l_start} to Week {prev_w}" if l_start != prev_w else f"Week {l_start}"})
    return pd.DataFrame(win_streaks), pd.DataFrame(loss_streaks)

def get_monday_comebacks(box_df, games):
    if box_df.empty or games.empty: return pd.DataFrame()
    b_c = box_df.copy()
    b_c['Season_Str'] = b_c['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    b_c['Week_Num'] = pd.to_numeric(b_c['Week'], errors='coerce').fillna(0).astype(int)
    b_c['Team_Str'] = b_c['Team_Name'].astype(str).str.strip()
    slot_col = 'Slot' if 'Slot' in b_c.columns else ('Lineup_Slot' if 'Lineup_Slot' in b_c.columns else 'Position')
    name_col = 'Player_Name' if 'Player_Name' in b_c.columns else 'Player'
    pts_col = 'Actual_Points' if 'Actual_Points' in b_c.columns else 'Points'
    nfl_c = next((c for c in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev'] if c in b_c.columns), None)
    b_c['NFL_Team_Clean'] = b_c[nfl_c].fillna('').astype(str).str.strip().str.upper() if nfl_c else ""
    
    date_col = next((c for c in b_c.columns if str(c).lower().strip() in ['game_date', 'date', 'weekday', 'day']), None)
    mon_lookup = load_nfl_monday_teams()
    def is_mon(r):
        if date_col and pd.notnull(r[date_col]):
            val = str(r[date_col]).strip()
            if any(m in val.lower() for m in ['mon', 'monday']): return True
            try: return pd.to_datetime(val).weekday() == 0
            except: pass
        return (r['Season_Str'], r['Week_Num'], r['NFL_Team_Clean']) in mon_lookup

    starters = b_c[~b_c[slot_col].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])].copy()
    starters['Points_Num'] = pd.to_numeric(starters[pts_col], errors='coerce').fillna(0)
    starters['Is_Monday'] = starters.apply(is_mon, axis=1)
    
    matches = games[games['Game_Type'].isin([1, 2]) & (games['W'] == 1)].copy()
    matches['Season_Str'] = matches['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    matches['Week_Num'] = pd.to_numeric(matches['Week'], errors='coerce').fillna(0).astype(int)
    
    cbs = []
    for _, m in matches.iterrows():
        s, w, win_tm, los_tm = m['Season_Str'], m['Week_Num'], str(m['Team_Name']).strip(), str(m['Opponent_Team_Name']).strip()
        w_rst = starters[(starters['Season_Str'] == s) & (starters['Week_Num'] == w) & (starters['Team_Str'] == win_tm)]
        l_rst = starters[(starters['Season_Str'] == s) & (starters['Week_Num'] == w) & (starters['Team_Str'] == los_tm)]
        if w_rst.empty or l_rst.empty: continue
        w_mon = w_rst[w_rst['Is_Monday']]
        l_mon = l_rst[l_rst['Is_Monday']]
        if w_mon.empty: continue
        
        w_sun = w_rst[~w_rst['Is_Monday']]['Points_Num'].sum()
        l_sun = l_rst[~l_rst['Is_Monday']]['Points_Num'].sum()
        if l_sun > w_sun:
            def str_pl(df_sub):
                if df_sub.empty: return "-"
                return ", ".join([f"{r[name_col]} ({float(r['Points_Num']):.1f})" for _, r in df_sub.sort_values('Points_Num', ascending=False).iterrows()])
            cbs.append({
                'Deficit_Num': l_sun - w_sun,
                'Deficit Overcome': f"{l_sun - w_sun:.1f}",
                'Final Score': f"{float(m['Actual_Points']):.1f} - {float(m['Opp_Points']):.1f}",
                'Winner': win_tm, 'Loser': los_tm, 'Season': s, 'Week': w,
                'Winning Team Monday Players': str_pl(w_mon),
                'Losing Team Monday Players': str_pl(l_mon)
            })
    if cbs:
        res = pd.DataFrame(cbs).sort_values('Deficit_Num', ascending=False).head(15).reset_index(drop=True)
        res['Rank'] = res.index + 1
        return res[['Rank', 'Deficit Overcome', 'Final Score', 'Winner', 'Loser', 'Season', 'Week', 'Winning Team Monday Players', 'Losing Team Monday Players']]
    return pd.DataFrame()
    
