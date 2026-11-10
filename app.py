import streamlit as st
import pandas as pd

st.set_page_config(page_title="DFFL Hub", page_icon="🏈", layout="wide")

# ================= UI & FORMATTING HELPERS =================
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

def format_ordinal(val):
    if pd.isna(val) or val == "" or str(val).strip() == "":
        return ""
    try:
        n = int(float(val))
        suffix = 'th' if 11 <= (n % 100) <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"
    except Exception:
        return str(val)

def format_ranges(nums):
    try:
        clean_nums = sorted(list({int(x) for x in nums if pd.notnull(x)}))
    except Exception:
        return ""
    if len(clean_nums) == 0:
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

def apply_competition_rank(df, score_col, round_digits=2):
    if df.empty or score_col not in df.columns:
        return df
    ranks = []
    prev_val = None
    current_rank = 1
    for i, val in enumerate(df[score_col]):
        if pd.isna(val):
            ranks.append("")
            continue
        val_key = round(float(val), round_digits) if round_digits is not None and isinstance(val, (int, float)) else val
        if i == 0:
            ranks.append(str(current_rank))
            prev_val = val_key
        else:
            if val_key == prev_val:
                ranks.append("")
            else:
                current_rank = i + 1
                ranks.append(str(current_rank))
                prev_val = val_key
    df['Rank'] = ranks
    return df

NFL_32_DEFENSES = [
    ("Arizona Cardinals", ["CARDINALS"], ["ARI"]),
    ("Atlanta Falcons", ["FALCONS"], ["ATL"]),
    ("Baltimore Ravens", ["RAVENS"], ["BAL"]),
    ("Buffalo Bills", ["BILLS"], ["BUF"]),
    ("Carolina Panthers", ["PANTHERS"], ["CAR"]),
    ("Chicago Bears", ["BEARS"], ["CHI"]),
    ("Cincinnati Bengals", ["BENGALS"], ["CIN"]),
    ("Cleveland Browns", ["BROWNS"], ["CLE"]),
    ("Dallas Cowboys", ["COWBOYS"], ["DAL"]),
    ("Denver Broncos", ["BRONCOS"], ["DEN"]),
    ("Detroit Lions", ["LIONS"], ["DET"]),
    ("Green Bay Packers", ["PACKERS"], ["GB"]),
    ("Houston Texans", ["TEXANS"], ["HOU"]),
    ("Indianapolis Colts", ["COLTS"], ["IND"]),
    ("Jacksonville Jaguars", ["JAGUARS"], ["JAX", "JAC"]),
    ("Kansas City Chiefs", ["CHIEFS"], ["KC"]),
    ("Las Vegas Raiders", ["RAIDERS"], ["LV", "OAK"]),
    ("Los Angeles Chargers", ["CHARGERS"], ["LAC", "SD"]),
    ("Los Angeles Rams", ["RAMS"], ["LAR", "LA", "STL"]),
    ("Miami Dolphins", ["DOLPHINS"], ["MIA"]),
    ("Minnesota Vikings", ["VIKINGS"], ["MIN"]),
    ("New England Patriots", ["PATRIOTS"], ["NE"]),
    ("New Orleans Saints", ["SAINTS"], ["NO"]),
    ("New York Giants", ["GIANTS", "NYG"], ["NYG"]),
    ("New York Jets", ["JETS", "NYJ"], ["NYJ"]),
    ("Philadelphia Eagles", ["EAGLES"], ["PHI"]),
    ("Pittsburgh Steelers", ["STEELERS"], ["PIT"]),
    ("San Francisco 49ers", ["49ERS"], ["SF"]),
    ("Seattle Seahawks", ["SEAHAWKS"], ["SEA"]),
    ("Tampa Bay Buccaneers", ["BUCCANEERS", "BUCS"], ["TB"]),
    ("Tennessee Titans", ["TITANS"], ["TEN"]),
    ("Washington Commanders", ["COMMANDERS", "REDSKINS", "FOOTBALL TEAM"], ["WAS", "WSH"]),
]

NFL_ABBR_TO_FULL = {
    'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens',
    'BUF': 'Buffalo Bills', 'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears',
    'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'DAL': 'Dallas Cowboys',
    'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers',
    'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars',
    'JAC': 'Jacksonville Jaguars', 'KC': 'Kansas City Chiefs', 'LV': 'Las Vegas Raiders',
    'OAK': 'Las Vegas Raiders', 'LAC': 'Los Angeles Chargers', 'SD': 'Los Angeles Chargers',
    'LAR': 'Los Angeles Rams', 'LA': 'Los Angeles Rams', 'STL': 'Los Angeles Rams',
    'MIA': 'Miami Dolphins', 'MIN': 'Minnesota Vikings', 'NE': 'New England Patriots',
    'NO': 'New Orleans Saints', 'NYG': 'New York Giants', 'NYJ': 'New York Jets',
    'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers', 'SF': 'San Francisco 49ers',
    'SEA': 'Seattle Seahawks', 'TB': 'Tampa Bay Buccaneers', 'TEN': 'Tennessee Titans',
    'WAS': 'Washington Commanders', 'WSH': 'Washington Commanders'
}

ALL_32_NFL_TEAMS = sorted(list(set(NFL_ABBR_TO_FULL.values())))

def get_unstarted_defenses(dst_df, name_col):
    started = set()
    if not dst_df.empty:
        for _, r in dst_df.iterrows():
            p_name = str(r[name_col]).upper()
            nfl_t = str(r.get('NFL_Team_Clean', '')).upper().strip()
            for full_name, nicks, abbrs in NFL_32_DEFENSES:
                if (nfl_t and nfl_t in abbrs) or any(nick in p_name for nick in nicks):
                    started.add(full_name)
    return [team[0] for team in NFL_32_DEFENSES if team[0] not in started]

# ================= DATA LOADERS =================
@st.cache_data(ttl=600)
def load_box_scores():
    try:
        return pd.read_excel("espn_fantasy_complete_stats_2017_2026.xlsx", sheet_name="Box_Scores", engine="openpyxl")
    except Exception:
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
            except Exception:
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
                if tm in alias_map:
                    lookup.add((s, w, alias_map[tm]))
    except Exception:
        pass
    return lookup

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
            curr_w, curr_l = 0, 0
            w_start, l_start = None, None
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
        st.warning("Player data not found.")
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
        opp_name, team_pts, opp_pts, sel_gt, sel_szn_num, sel_gt_str = "Unknown", 0.0, 0.0, 1, 2026.0, "Matchup"
        
    if opp_name.upper() != 'BYE' and opp_name != "Unknown":
        bold_a = "font-weight: 800; color: #111;" if team_pts > opp_pts else "font-weight: 500; color: #555;"
        bold_b = "font-weight: 800; color: #111;" if opp_pts > team_pts else "font-weight: 500; color: #555;"
        
        mask_a = ((games['Team_Name'] == b_team) & (games['Season'] == b_szn_str) & (games['Game_Type'].isin([1, 2])) & ((games['Game_Type'] < sel_gt) | ((games['Game_Type'] == sel_gt) & (games['Week_Num'] <= b_wk_int))))
        g_a = games[mask_a]
        rec_a_str = f"{g_a['W'].sum()}-{g_a['L'].sum()}" + (f"-{g_a['T'].sum()}" if g_a['T'].sum() > 0 else "")
        
        mask_b = ((games['Team_Name'] == opp_name) & (games['Season'] == b_szn_str) & (games['Game_Type'].isin([1, 2])) & ((games['Game_Type'] < sel_gt) | ((games['Game_Type'] == sel_gt) & (games['Week_Num'] <= b_wk_int))))
        g_b = games[mask_b]
        rec_b_str = f"{g_b['W'].sum()}-{g_b['L'].sum()}" + (f"-{g_b['T'].sum()}" if g_b['T'].sum() > 0 else "")
        
        h2h = games[(games['Team_Name'] == b_team) & (games['Opponent_Team_Name'] == opp_name) & (games['Game_Type'].isin([1, 2]))]
        mask_h2h = ((h2h['Season_Num'] < sel_szn_num) | ((h2h['Season_Num'] == sel_szn_num) & (h2h['Game_Type'] < sel_gt)) | ((h2h['Season_Num'] == sel_szn_num) & (h2h['Game_Type'] == sel_gt) & (h2h['Week_Num'] <= b_wk_int)))
        g_h2h = h2h[mask_h2h]
        tw, tl, tt = g_h2h['W'].sum(), g_h2h['L'].sum(), g_h2h['T'].sum()
        h2h_str = f"{b_team} leads {tw}-{tl}" if tw > tl else (f"{opp_name} leads {tl}-{tw}" if tl > tw else f"Series tied {tw}-{tl}")
        if tt > 0: h2h_str += f"-{tt}"
            
        st.markdown(f'''
        <div style="background-color: rgba(128, 128, 128, 0.05); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 14px 20px; margin: 10px 0 20px 0; text-align: center;">
            <div style="font-size: 13px; font-weight: 700; color: #6c757d; text-transform: uppercase; margin-bottom: 8px;">{b_szn_str} &bull; Week {b_wk_int} &bull; {sel_gt_str}</div>
            <div style="display: flex; justify-content: center; gap: 50px; margin-bottom: 8px;">
                <div style="min-width: 140px;">
                    <div style="font-size: 18px; font-weight: 700;">{b_team}</div>
                    <div style="font-size: 34px; {bold_a};">{team_pts:.1f}</div>
                    <div style="font-size: 14px; color: #495057;">{rec_a_str}</div>
                </div>
                <div style="min-width: 140px;">
                    <div style="font-size: 18px; font-weight: 700;">{opp_name}</div>
                    <div style="font-size: 34px; {bold_b};">{opp_pts:.1f}</div>
                    <div style="font-size: 14px; color: #495057;">{rec_b_str}</div>
                </div>
            </div>
            <div style="font-size: 13px; font-weight: 600; color: #495057; border-top: 1px solid rgba(128, 128, 128, 0.2); padding-top: 6px; display: inline-block;">H2H through this game: {h2h_str}</div>
        </div>''', unsafe_allow_html=True)
    elif opp_name.upper() == 'BYE':
        st.markdown(f'''
        <div style="background-color: rgba(128, 128, 128, 0.05); border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 8px; padding: 14px 20px; margin: 10px 0 20px 0; text-align: center;">
            <div style="font-size: 13px; font-weight: 700; color: #6c757d; text-transform: uppercase; margin-bottom: 6px;">{b_szn_str} &bull; Week {b_wk_int} &bull; Playoff Bye</div>
            <div style="font-size: 18px; font-weight: 700;">{b_team}</div>
            <div style="font-size: 34px; font-weight: 800;">{team_pts:.1f}</div>
        </div>''', unsafe_allow_html=True)

    team_roster = box_df[(box_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == b_szn_str) & (box_df['Week'] == b_wk_int) & (box_df['Team_Name'] == b_team)].copy()
    opp_roster = box_df[(box_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == b_szn_str) & (box_df['Week'] == b_wk_int) & (box_df['Team_Name'] == opp_name)].copy()
    
    if team_roster.empty and opp_roster.empty:
        st.info("No player box score details available.")
        return
        
    def format_roster(df):
        if df.empty: return pd.DataFrame(), pd.DataFrame()
        slot_c = 'Slot' if 'Slot' in df.columns else ('Lineup_Slot' if 'Lineup_Slot' in df.columns else 'Position')
        name_c = 'Player_Name' if 'Player_Name' in df.columns else 'Player'
        pts_c = 'Actual_Points' if 'Actual_Points' in df.columns else 'Points'
        nfl_c = next((c for c in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev', 'Team_Abbr', 'Pro_Team_Abbrev', 'Pro Team', 'NFL Team'] if c in df.columns), None)
        df['NFL Team'] = df[nfl_c].fillna('').astype(str).str.strip() if nfl_c else ""
        
        stat_map = {
            'Passing_Yards': 'Pass Yds', 'Passing_TDs': 'Pass TD', 'Passing_Interceptions': 'INT',
            'Rushing_Yards': 'Rush Yds', 'Rushing_TDs': 'Rush TD',
            'Receptions': 'Rec', 'Receiving_Yards': 'Rec Yds', 'Receiving_TDs': 'Rec TD'
        }
        def make_blurb(row):
            b = []
            for k, lbl in stat_map.items():
                if k in df.columns and pd.notnull(row[k]) and float(row[k]) != 0:
                    v = int(float(row[k])) if float(row[k]).is_integer() else float(row[k])
                    b.append(f"{v} {lbl}")
            return ", ".join(b)
            
        df['Stats'] = df.apply(make_blurb, axis=1)
        slot_order = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4, 'FLEX': 5, 'D/ST': 6, 'K': 7}
        df['sort_val'] = df[slot_c].map(lambda x: slot_order.get(str(x).strip().upper(), 99))
        is_bench = df[slot_c].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])
        starters = df[~is_bench].sort_values(['sort_val', pts_c], ascending=[True, False]).copy()
        bench = df[is_bench].sort_values(pts_c, ascending=False).copy()
        
        cols = [name_c, 'NFL Team', slot_c, pts_c, 'Stats']
        s_disp = starters[cols].rename(columns={name_c: 'Player', slot_c: 'Slot', pts_c: 'Pts'})
        b_disp = bench[cols].rename(columns={name_c: 'Player', slot_c: 'Slot', pts_c: 'Pts'})
        if not s_disp.empty:
            tot = pd.DataFrame([{'Player': 'TOTAL', 'NFL Team': '', 'Slot': '', 'Pts': s_disp['Pts'].sum(), 'Stats': ''}])
            s_disp = pd.concat([s_disp, tot], ignore_index=True)
        s_disp['Pts'] = s_disp['Pts'].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) and x != '' else "")
        b_disp['Pts'] = b_disp['Pts'].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) and x != '' else "")
        return s_disp, b_disp

    t_start, t_bench = format_roster(team_roster)
    o_start, o_bench = format_roster(opp_roster)
    hl = lambda r: ['font-weight: bold;' if str(r.get('Player','')).upper() == 'TOTAL' else '' for _ in r.index]
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"#### {b_team}")
        if not t_start.empty: render_html_table(t_start, hl, left_align_cols=['Stats'])
        if not t_bench.empty:
            st.markdown("**Bench**")
            render_html_table(t_bench, left_align_cols=['Stats'])
    with col_b:
        if opp_name != "Unknown" and opp_name.upper() != 'BYE':
            st.markdown(f"#### {opp_name}")
            if not o_start.empty: render_html_table(o_start, hl, left_align_cols=['Stats'])
            if not o_bench.empty:
                st.markdown("**Bench**")
                render_html_table(o_bench, left_align_cols=['Stats'])

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
    
    nfl_c = next((c for c in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev', 'Team_Abbr', 'Pro_Team_Abbrev', 'Pro Team', 'NFL Team'] if c in b_c.columns), None)
    b_c['NFL Team'] = b_c[nfl_c].fillna('').astype(str).str.strip() if nfl_c else ""
    
    starters = b_c[~b_c[slot_col].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])].copy()
    starters['Points_Num'] = pd.to_numeric(starters[pts_col], errors='coerce').fillna(0)
    
    def clean_p(v):
        p = str(v).strip().upper()
        if p in ['K', 'PK']: return 'K'
        if p in ['D/ST', 'DST', 'DEF', 'DP']: return 'D/ST'
        return p if p in ['QB', 'RB', 'WR', 'TE'] else p
    starters['Pos'] = starters[pos_col].apply(clean_p)
    
    cols_to_drop = [c for c in ['Opponent_Team_Name', 'Opponent', 'Outcome'] if c in starters.columns]
    if cols_to_drop:
        starters = starters.drop(columns=cols_to_drop)

    el_g = games[games['Game_Type'].isin([1, 2, 4]) & (games['Team_Name'].str.upper() != 'CAM')].copy()
    el_g['Season_Str'] = el_g['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    el_g['Week_Num'] = pd.to_numeric(el_g['Week'], errors='coerce').fillna(0).astype(int)
    el_g['Team_Str'] = el_g['Team_Name'].astype(str).str.strip()
    el_g['Outcome'] = el_g.apply(
        lambda r: f"BYE ({float(r['Actual_Points']):.1f})" if r['Game_Type'] == 4 else f"{'W' if r['W']==1 else ('L' if r['L']==1 else 'T')} ({float(r['Actual_Points']):.1f} - {float(r['Opp_Points']):.1f})", 
        axis=1
    )
    
    el_g_sub = el_g[['Season_Str', 'Week_Num', 'Team_Str', 'Opponent_Team_Name', 'Outcome']].drop_duplicates(subset=['Season_Str', 'Week_Num', 'Team_Str'])
    merged = pd.merge(starters, el_g_sub, on=['Season_Str', 'Week_Num', 'Team_Str'], how='inner')
    
    opp_col = next((c for c in ['Opponent_Team_Name', 'Opponent_Team_Name_y', 'Opponent_Team_Name_x', 'Opponent'] if c in merged.columns), None)
    out_col = next((c for c in ['Outcome', 'Outcome_y', 'Outcome_x'] if c in merged.columns), None)

    merged['Player'] = merged[name_col]
    merged['Season'] = merged['Season_Str']
    merged['Week'] = merged['Week_Num']
    merged['Team'] = merged['Team_Str']
    merged['Opponent'] = merged[opp_col] if opp_col else ""
    merged['Outcome'] = merged[out_col] if out_col else ""
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
    nfl_c = next((c for c in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev', 'Team_Abbr', 'Pro_Team_Abbrev', 'Pro Team', 'NFL Team'] if c in b_c.columns), None)
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

# ================= TAB DECLARATIONS =================
tab1, tab5, tab6, tab2, tab3, tab4, tab_player = st.tabs([
    "Franchise", "Schedule", "Box Scores", "Matchups", "Standings", "Records", "Detailed Player Scoring"
])

# ================= TAB 1: FRANCHISE =================
with tab1:
    selected_team = st.selectbox("Select Manager", teams, label_visibility="collapsed")
    mgr_games = games[games['Team_Name'] == selected_team].sort_values(['Season_Num', 'Week_Num']).copy()
    mgr_games['Result'] = mgr_games.apply(lambda x: 'W' if x['W'] else ('L' if x['L'] else 'T'), axis=1)
    
    reg_season = mgr_games[mgr_games['Game_Type'] == 1]
    playoffs = mgr_games[mgr_games['Game_Type'] == 2]
    
    tw, tl, tt = reg_season['W'].sum(), reg_season['L'].sum(), reg_season['T'].sum()
    win_pct = tw / (tw + tl + tt) if (tw + tl + tt) > 0 else 0.0
    win_pct_str = f"{win_pct:.3f}".replace("0.", ".", 1) if win_pct < 1 else f"{win_pct:.3f}"
    
    high_score_str = f"{mgr_games.loc[mgr_games['Actual_Points'].idxmax()]['Actual_Points']:.1f} ({str(mgr_games.loc[mgr_games['Actual_Points'].idxmax()]['Season']).replace('.0','')}, W{mgr_games.loc[mgr_games['Actual_Points'].idxmax()]['Week']})" if not mgr_games.empty else "N/A"
    
    comp_games = mgr_games[mgr_games['Game_Type'].isin([1, 2])]
    if not comp_games.empty:
        comp_valid = comp_games[comp_games['Actual_Points'] > 0]
        low_score_str = f"{comp_valid.loc[comp_valid['Actual_Points'].idxmin()]['Actual_Points']:.1f} ({str(comp_valid.loc[comp_valid['Actual_Points'].idxmin()]['Season']).replace('.0','')}, W{comp_valid.loc[comp_valid['Actual_Points'].idxmin()]['Week']})" if not comp_valid.empty else "N/A"
        valid_opp = comp_games[comp_games['Opponent_Team_Name'].str.upper() != 'CAM']
        if not valid_opp.empty:
            opp_stats = valid_opp.groupby('Opponent_Team_Name').agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum')).reset_index()
            opp_stats['Games'] = opp_stats['W'] + opp_stats['L'] + opp_stats['T']
            opp_stats = opp_stats[opp_stats['Games'] > 0]
            if not opp_stats.empty:
                opp_stats['Win %'] = opp_stats['W'] / opp_stats['Games']
                def fmt_opp(df_sub):
                    recs = [f"{int(r['W'])}-{int(r['L'])}" + (f"-{int(r['T'])}" if r['T']>0 else "") for _, r in df_sub.iterrows()]
                    return f"{', '.join(df_sub['Opponent_Team_Name'])} ({recs[0]})" if len(set(recs))==1 else ", ".join([f"{r['Opponent_Team_Name']} ({rec})" for (_, r), rec in zip(df_sub.iterrows(), recs)])
                easiest_str = fmt_opp(opp_stats[opp_stats['Win %'] == opp_stats['Win %'].max()])
                toughest_str = fmt_opp(opp_stats[opp_stats['Win %'] == opp_stats['Win %'].min()])
            else: easiest_str, toughest_str = "N/A", "N/A"
        else: easiest_str, toughest_str = "N/A", "N/A"
    else: low_score_str, easiest_str, toughest_str = "N/A", "N/A", "N/A"
    
    pw, pl, pt = playoffs['W'].sum(), playoffs['L'].sum(), playoffs['T'].sum()
    champs = sorted([str(s).replace('.0', '') for s in playoffs[playoffs['Playoff_Round'].astype(str).str.strip().str.lower().isin(['finals', 'championship']) & (playoffs['W'] == 1)]['Season'].unique()])
    champ_str = f"{len(champs)} ({', '.join(champs)})" if champs else "0"
    
    longest_w, w_span, longest_l, l_span = get_detailed_streaks(comp_games)
    
    if not rs_ranks_df.empty and 'Team_Name' in rs_ranks_df.columns:
        rs_team = rs_ranks_df[rs_ranks_df['Team_Name'] == selected_team].copy()
    else:
        rs_team = pd.DataFrame(columns=['Team_Name', 'Season', 'RS_Rank'])

    playoff_apps, playoff_byes = 0, 0
    for _, row in rs_team.iterrows():
        szn = str(row['Season']).strip()
        if szn.isdigit() and szn in completed_playoff_seasons:
            s_int, rk = int(szn), float(row['RS_Rank'])
            if pd.notnull(rk):
                if (s_int == 2017 and rk <= 4) or (s_int > 2017 and rk <= 6): playoff_apps += 1
                if s_int >= 2018 and rk <= 2: playoff_byes += 1
                
    top_pos_all_time = {'QB': 'N/A', 'RB': 'N/A', 'WR': 'N/A', 'TE': 'N/A', 'D/ST': 'N/A', 'K': 'N/A'}
    top_per_szn = {'QB': {}, 'RB': {}, 'WR': {}, 'TE': {}}
    if not box_df.empty:
        slot_c = 'Slot' if 'Slot' in box_df.columns else ('Lineup_Slot' if 'Lineup_Slot' in box_df.columns else 'Position')
        name_c = 'Player_Name' if 'Player_Name' in box_df.columns else 'Player'
        pts_c = 'Actual_Points' if 'Actual_Points' in box_df.columns else 'Points'
        pos_c = 'Position' if 'Position' in box_df.columns else ('Pos' if 'Pos' in box_df.columns else slot_c)
        
        el_g = games[games['Game_Type'].isin([1, 2, 4])][['Season', 'Week', 'Team_Name']].drop_duplicates()
        el_g['Season'] = el_g['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        el_g['Week'] = pd.to_numeric(el_g['Week'], errors='coerce').fillna(0).astype(int)
        
        b_team_df = box_df[box_df['Team_Name'] == selected_team].copy()
        b_team_df['Season'] = b_team_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        b_team_df['Week'] = pd.to_numeric(b_team_df['Week'], errors='coerce').fillna(0).astype(int)
        starters = b_team_df[~b_team_df[slot_c].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])]
        counted = pd.merge(starters, el_g, on=['Season', 'Week', 'Team_Name'], how='inner')
        if not counted.empty:
            counted[pts_c] = pd.to_numeric(counted[pts_c], errors='coerce').fillna(0)
            def clean_p(v):
                p = str(v).strip().upper()
                if p in ['K', 'PK']: return 'K'
                if p in ['D/ST', 'DST', 'DEF', 'DP']: return 'D/ST'
                return p
            counted['Clean_Pos'] = counted[pos_c].apply(clean_p)
            for p_target in ['QB', 'RB', 'WR', 'TE', 'D/ST', 'K']:
                sub_pos = counted[counted['Clean_Pos'] == p_target]
                if not sub_pos.empty:
                    tot = sub_pos.groupby(name_c)[pts_c].sum().reset_index().sort_values(pts_c, ascending=False)
                    if not tot.empty: top_pos_all_time[p_target] = f"{tot.iloc[0][name_c]} ({tot.iloc[0][pts_c]:,.1f} pts)"
            for p_target in ['QB', 'RB', 'WR', 'TE']:
                sub_pos = counted[counted['Clean_Pos'] == p_target]
                if not sub_pos.empty:
                    s_totals = sub_pos.groupby(['Season', name_c])[pts_c].sum().reset_index().sort_values(['Season', pts_c], ascending=[True, False]).drop_duplicates(subset=['Season'])
                    top_per_szn[p_target] = dict(zip(s_totals['Season'], s_totals.apply(lambda r: f"{r[name_c]} ({r[pts_c]:,.1f})", axis=1)))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Championships:** {champ_str}")
        st.markdown(f"**Reg. Season Record:** {tw}-{tl}-{tt} ({win_pct_str})")
        st.markdown(f"**Playoff Record:** {pw}-{pl}-{pt}")
        st.markdown(f"**Playoff Appearances:** {playoff_apps}")
        st.markdown(f"**Playoff Byes:** {playoff_byes}")
        st.markdown(f"**Weekly Bags Won:** {mgr_games['Is_High_Scorer'].sum()}")
    with c2:
        st.markdown(f"**Highest Scoring Game:** {high_score_str}")
        st.markdown(f"**Lowest Scoring Game:** {low_score_str}")
        st.markdown(f"**Easiest Opponent:** {easiest_str}")
        st.markdown(f"**Toughest Opponent:** {toughest_str}")
        st.markdown(f"**Longest Win Streak:** {longest_w} games ({w_span})")
        st.markdown(f"**Longest Losing Streak:** {longest_l} games ({l_span})")
    with c3:
        st.markdown(f"**Top Scoring QB:** {top_pos_all_time['QB']}")
        st.markdown(f"**Top Scoring RB:** {top_pos_all_time['RB']}")
        st.markdown(f"**Top Scoring WR:** {top_pos_all_time['WR']}")
        st.markdown(f"**Top Scoring TE:** {top_pos_all_time['TE']}")
        st.markdown(f"**Top Scoring D/ST:** {top_pos_all_time['D/ST']}")
        st.markdown(f"**Top Scoring K:** {top_pos_all_time['K']}")
    st.divider()

    st.write("### Season-by-Season (Regular Season)")
    szn_stats = reg_season.groupby('Season').agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum'), PF=('Actual_Points', 'sum'), PA=('Opp_Points', 'sum')).reset_index()
    szn_stats['Win %'] = (szn_stats['W'] / (szn_stats['W'] + szn_stats['L'] + szn_stats['T'])).fillna(0).apply(lambda x: f"{x:.3f}".replace("0.", ".", 1) if x < 1 else f"{x:.3f}")
    szn_stats['Games'] = szn_stats['W'] + szn_stats['L'] + szn_stats['T']
    szn_stats['PF/G'] = (szn_stats['PF'] / szn_stats['Games']).apply(lambda x: f"{x:.1f}")
    szn_stats['PA/G'] = (szn_stats['PA'] / szn_stats['Games']).apply(lambda x: f"{x:.1f}")
    szn_stats['PF'] = szn_stats['PF'].astype(int)
    szn_stats['PA'] = szn_stats['PA'].astype(int)
    
    all_reg = games[games['Game_Type'] == 1].copy()
    all_reg['Season_Str'] = all_reg['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    pf_ranks = all_reg.groupby(['Season_Str', 'Team_Name'])['Actual_Points'].sum().groupby('Season_Str').rank(ascending=False, method='min').astype(int).reset_index()
    pa_ranks = all_reg.groupby(['Season_Str', 'Team_Name'])['Opp_Points'].sum().groupby('Season_Str').rank(ascending=False, method='min').astype(int).reset_index()
    pf_team = pf_ranks[pf_ranks['Team_Name'] == selected_team].rename(columns={'Season_Str': 'Season', 'Actual_Points': 'PF Rank'})
    pa_team = pa_ranks[pa_ranks['Team_Name'] == selected_team].rename(columns={'Season_Str': 'Season', 'Opp_Points': 'PA Rank'})
    szn_stats = pd.merge(pd.merge(szn_stats, pf_team[['Season', 'PF Rank']], on='Season', how='left'), pa_team[['Season', 'PA Rank']], on='Season', how='left')
    
    szn_stats['Playoff Outcome'] = [get_playoff_outcome(playoffs[playoffs['Season'] == s]) for s in szn_stats['Season']]
    mgr_games['Season_Str'] = mgr_games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    szn_stats['Weekly Bags'] = szn_stats['Season'].map(mgr_games.groupby('Season_Str')['Is_High_Scorer'].sum().to_dict()).fillna(0).astype(int)
    
    all_reg['Weekly_Rank'] = all_reg.groupby(['Season_Str', 'Week_Num'])['Actual_Points'].rank(ascending=False, method='average')
    all_reg['N_Teams'] = all_reg.groupby(['Season_Str', 'Week_Num'])['Team_Name'].transform('count')
    all_reg['Exp_Win'] = all_reg.apply(lambda r: (r['N_Teams'] - r['Weekly_Rank']) / (r['N_Teams'] - 1) if r['N_Teams'] > 1 else 0.0, axis=1)
    xw = all_reg.groupby(['Season_Str', 'Team_Name'])['Exp_Win'].sum().reset_index()
    xw_team = xw[xw['Team_Name'] == selected_team].rename(columns={'Season_Str': 'Season', 'Exp_Win': 'Exp_Win_Total'})
    szn_stats = pd.merge(szn_stats, xw_team[['Season', 'Exp_Win_Total']], on='Season', how='left')
    szn_stats['Expected Wins'] = szn_stats['Exp_Win_Total'].fillna(0).apply(lambda x: f"{x:.1f}")
    szn_stats['Luck Factor'] = szn_stats.apply(lambda r: "0.0" if pd.isna(r['Exp_Win_Total']) or abs(r['W']-r['Exp_Win_Total'])<0.05 else f"{r['W']-r['Exp_Win_Total']:+.1f}", axis=1)
    
    if not rs_team.empty and 'RS_Rank' in rs_team.columns:
        rs_format = rs_team[['Season', 'RS_Rank']].copy()
        rs_format['Season'] = rs_format['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        szn_stats = pd.merge(szn_stats, rs_format, on='Season', how='left')
        szn_stats['Standings Finish'] = szn_stats['RS_Rank'].apply(lambda x: f"{int(x)}{'th' if 11 <= int(x)%100 <= 13 else {1:'st',2:'nd',3:'rd'}.get(int(x)%10, 'th')}" if pd.notnull(x) else "")
    else:
        szn_stats['Standings Finish'] = ""
    
    for p in ['QB', 'RB', 'WR', 'TE']:
        szn_stats[f'Top {p}'] = szn_stats['Season'].map(top_per_szn[p]).fillna("")
        
    disp_cols = ['Season', 'W', 'L', 'Win %', 'Standings Finish', 'PF', 'PF/G', 'PF Rank', 'PA', 'PA/G', 'PA Rank', 'Playoff Outcome', 'Weekly Bags', 'Expected Wins', 'Luck Factor', 'Top QB', 'Top RB', 'Top WR', 'Top TE']
    hl_cells = lambda row: ['background-color: #ebebeb; color: #888888;' if str(row.get('Season','')).strip() in ['2017', '2018'] and c in ['Weekly Bags', 'Top QB', 'Top RB', 'Top WR', 'Top TE'] else '' for c in row.index]
    render_html_table(szn_stats[disp_cols].sort_values('Season', ascending=False), highlight_fn=hl_cells)
    
    st.divider()
    st.write("### Playoff Game Log")
    po_disp = playoffs.sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).copy()
    if not po_disp.empty:
        po_disp['Season'] = po_disp['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        po_disp['Score'] = po_disp['Actual_Points'].round(1).astype(str) + " - " + po_disp['Opp_Points'].round(1).astype(str)
        render_html_table(po_disp[['Season', 'Week', 'Playoff_Round', 'Opponent_Team_Name', 'Result', 'Score']].rename(columns={'Opponent_Team_Name': 'Opponent', 'Playoff_Round': 'Round'}))
        po_disp['Game_Label'] = po_disp['Season'] + " Week " + po_disp['Week'].astype(str) + " vs " + po_disp['Opponent_Team_Name']
        vk = st.selectbox("Select Playoff Game to View Box Score:", ["Select..."] + po_disp['Game_Label'].tolist(), key="po_box")
        if vk != "Select...":
            row = po_disp[po_disp['Game_Label'] == vk].iloc[0]
            display_box_score(row['Season'], row['Week'], selected_team, box_df, games)
    else:
        st.write("No playoff appearances on record.")
        
    st.divider()
    st.write("### Head-to-Head vs. All Opponents")
    opp_list = []
    for opp in sorted([t for t in teams if t != selected_team]):
        og = games[(games['Team_Name'] == selected_team) & (games['Opponent_Team_Name'] == opp) & (games['Game_Type'].isin([1, 2]))]
        if og.empty: continue
        w_cnt, l_cnt, t_cnt = int(og['W'].sum()), int(og['L'].sum()), int(og['T'].sum())
        tot_g = w_cnt + l_cnt + t_cnt
        wp = w_cnt / tot_g if tot_g > 0 else 0.0
        po_g = og[og['Game_Type'] == 2]
        po_rec = f"{int(po_g['W'].sum())}-{int(po_g['L'].sum())}" + (f"-{int(po_g['T'].sum())}" if po_g['T'].sum()>0 else "") if len(po_g)>0 else "-"
        opp_list.append({'Opponent': opp, 'GP': tot_g, 'W': w_cnt, 'L': l_cnt, 'T': t_cnt, 'Win_Pct_Raw': wp, 'Win %': f"{wp:.3f}".replace("0.", ".", 1) if wp < 1 else f"{wp:.3f}", 'PF': int(round(og['Actual_Points'].sum())), 'PA': int(round(og['Opp_Points'].sum())), 'Playoff Record': po_rec})
    if opp_list:
        render_html_table(pd.DataFrame(opp_list).sort_values(['Win_Pct_Raw', 'W', 'GP'], ascending=[False, False, False])[['Opponent', 'GP', 'W', 'L', 'Win %', 'PF', 'PA', 'Playoff Record']])

# ================= TAB 5: SCHEDULE =================
with tab5:
    c1, c2 = st.columns(2)
    s_szn = c1.selectbox("Season", seasons_list, key='sched_szn')
    s_team = c2.selectbox("Manager", teams, key='sched_team')
    sched = games[(games['Season'] == str(s_szn)) & (games['Team_Name'] == s_team)].sort_values(['Game_Type', 'Week_Num']).copy()
    if not sched.empty:
        sched['Type'] = sched['Game_Type'].map({1: 'Regular Season', 2: 'Playoffs', 3: 'Consolation', 4: 'Playoff Bye'})
        sched['Result'] = sched.apply(lambda x: 'BYE' if x['Game_Type'] == 4 else ('W' if x['W'] else ('L' if x['L'] else 'T')), axis=1)
        t_col, o_col = f'{s_team} Score', 'Opponent Score'
        sched[t_col] = sched['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        sched[o_col] = sched.apply(lambda x: f"{float(x['Opp_Points']):.1f}" if x['Game_Type'] != 4 else "-", axis=1)
        sched['Margin'] = sched.apply(lambda r: "-" if r['Game_Type']==4 else f"{r['Actual_Points']-r['Opp_Points']:+.1f}", axis=1)
        sched['Opponent'] = sched['Opponent_Team_Name']
        
        s_str = str(s_szn).replace('.0', '').strip()
        sched['Week_Num_Int'] = pd.to_numeric(sched['Week'], errors='coerce').fillna(0).astype(int)
        sched[f'{s_team} Top Scorer'] = sched.apply(lambda r: game_top_map.get((s_str, r['Week_Num_Int'], str(r['Team_Name']).strip()), ""), axis=1)
        sched['Opponent Top Scorer'] = sched.apply(lambda r: game_top_map.get((s_str, r['Week_Num_Int'], str(r['Opponent_Team_Name']).strip()), "") if str(r['Opponent_Team_Name']).upper() != 'BYE' else "", axis=1)
        
        cols = ['Week', 'Type', 'Opponent', 'Result', t_col, o_col, 'Margin', f'{s_team} Top Scorer', 'Opponent Top Scorer']
        hl = lambda row: ['font-weight: bold;' if (c == t_col and row['Result'] == 'W') or (c == o_col and row['Result'] == 'L') else '' for c in row.index]
        render_html_table(sched[cols], hl)
        
        vwk = st.selectbox("Select Week to View Box Score:", ["Select..."] + sched['Week'].unique().tolist(), key="sch_box")
        if vwk != "Select...": display_box_score(s_szn, vwk, s_team, box_df, games)
    else:
        st.write("No schedule found.")

# ================= TAB 6: BOX SCORES =================
with tab6:
    if box_df.empty:
        st.warning("Player data not found.")
    else:
        c1, c2, c3 = st.columns(3)
        b_season = c1.selectbox("Season", seasons_list, key="b_szn")
        weeks = sorted(box_df[box_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == str(b_season)]['Week'].dropna().unique().tolist())
        b_week = c2.selectbox("Week", weeks, key="b_wk")
        avail_teams = sorted(box_df[(box_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == str(b_season)) & (box_df['Week'] == b_week)]['Team_Name'].dropna().unique().tolist())
        b_team = c3.selectbox("Manager", avail_teams, key="b_tm")
        if b_team:
            display_box_score(b_season, b_week, b_team, box_df, games)

# ================= TAB 2: MATCHUPS =================
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        team_a = st.selectbox("Team A", teams)
        team_b = st.selectbox("Team B", [t for t in teams if t != team_a])
    h2h = games[(games['Team_Name'] == team_a) & (games['Opponent_Team_Name'] == team_b) & (games['Game_Type'].isin([1, 2]))].copy()
    if not h2h.empty:
        w, l, t = h2h['W'].sum(), h2h['L'].sum(), h2h['T'].sum()
        p_h2h = h2h[h2h['Game_Type'] == 2]
        pw, pl, pt = p_h2h['W'].sum(), p_h2h['L'].sum(), p_h2h['T'].sum()
        with c2:
            st.write(f"### {team_a} vs. {team_b}")
            leader = f"{team_a} leads {w}-{l}" if w > l else (f"{team_b} leads {l}-{w}" if l > w else f"Tied {w}-{l}")
            st.markdown(f"**Series Leader:** {leader}" + (f"-{t}" if t > 0 else ""))
            if len(p_h2h) == 0: st.markdown("**Playoff Record:** No playoff matchups have occurred")
            else:
                p_lead = f"{team_a} leads {pw}-{pl}" if pw > pl else (f"{team_b} leads {pl}-{pw}" if pl > pw else f"Tied {pw}-{pl}")
                st.markdown(f"**Playoff Record:** {p_lead}" + (f"-{pt}" if pt > 0 else ""))
        st.divider()
        h2h = h2h.sort_values(['Season_Num', 'Week_Num'], ascending=[False, False])
        h2h['Season_Str'] = h2h['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        h2h['Winner'] = h2h.apply(lambda x: x['Team_Name'] if x['W'] == 1 else (x['Opponent_Team_Name'] if x['L'] == 1 else 'Tie'), axis=1)
        h2h['Type'] = h2h['Game_Type'].map({1: 'Regular Season', 2: 'Playoffs'}).fillna(h2h['Game_Type_Str'])
        col_a, col_b = f'{team_a} Pts', f'{team_b} Pts'
        h2h[col_a] = h2h['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        h2h[col_b] = h2h['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
        h2h['Margin'] = h2h['Margin'].apply(lambda x: f"{float(x):.1f}")
        h2h[f'{team_a} Top Scorer'] = h2h.apply(lambda r: game_top_map.get((r['Season_Str'], int(r['Week_Num']), str(team_a).strip()), ""), axis=1)
        h2h[f'{team_b} Top Scorer'] = h2h.apply(lambda r: game_top_map.get((r['Season_Str'], int(r['Week_Num']), str(team_b).strip()), ""), axis=1)
        hl = lambda r: ['font-weight: bold;' if (c == col_a and r['Winner'] == team_a) or (c == col_b and r['Winner'] == team_b) else '' for c in r.index]
        render_html_table(h2h[['Season_Str', 'Week', 'Type', 'Winner', col_a, col_b, 'Margin', f'{team_a} Top Scorer', f'{team_b} Top Scorer']].rename(columns={'Season_Str': 'Season'}), hl)
    else:
        st.write("No matchups found between these teams.")

# ================= TAB 3: STANDINGS =================
with tab3:
    sel_szn = st.selectbox("Select Season", seasons_list, key='stnd_szn')
    szn_data = games[(games['Season'] == str(sel_szn)) & (games['Game_Type'] == 1)]
    if not szn_data.empty:
        max_wk = int(szn_data['Week_Num'].max())
        sel_wk = st.slider("Standings Through Week:", min_value=1, max_value=max_wk, value=max_wk)
        szn_games = szn_data[szn_data['Week_Num'] <= sel_wk].copy()
        szn_games['Weekly_Rank'] = szn_games.groupby('Week_Num')['Actual_Points'].rank(ascending=False, method='average')
        szn_games['N_Teams'] = szn_games.groupby('Week_Num')['Team_Name'].transform('count')
        szn_games['Exp_Win'] = szn_games.apply(lambda r: (r['N_Teams'] - r['Weekly_Rank']) / (r['N_Teams'] - 1) if r['N_Teams'] > 1 else 0.0, axis=1)
        
        stnd = szn_games.groupby('Team_Name').agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum'), PF=('Actual_Points', 'sum'), PA=('Opp_Points', 'sum'), Exp_Win_Total=('Exp_Win', 'sum')).reset_index()
        stnd['Win_Pct_Raw'] = (stnd['W'] / (stnd['W'] + stnd['L'] + stnd['T'])).fillna(0)
        stnd = stnd.sort_values(['Win_Pct_Raw', 'PF'], ascending=[False, False]).reset_index(drop=True)
        stnd['Rank'] = (stnd.index + 1).map(lambda x: f"{x}{'th' if 11 <= x % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(x % 10, 'th')}")
        stnd['Win %'] = stnd['Win_Pct_Raw'].apply(lambda x: f"{x:.3f}".replace("0.", ".", 1) if x < 1 else f"{x:.3f}")
        stnd['PF'] = stnd['PF'].apply(lambda x: f"{float(x):.1f}")
        stnd['PA'] = stnd['PA'].apply(lambda x: f"{float(x):.1f}")
        stnd['Expected Wins'] = stnd['Exp_Win_Total'].apply(lambda x: f"{float(x):.1f}")
        stnd['Luck Factor'] = stnd.apply(lambda r: "0.0" if abs(r['W']-r['Exp_Win_Total'])<0.05 else f"{r['W']-r['Exp_Win_Total']:+.1f}", axis=1)
        render_html_table(stnd[['Rank', 'Team_Name', 'W', 'L', 'T', 'Win %', 'PF', 'PA', 'Expected Wins', 'Luck Factor']].rename(columns={'Team_Name': 'Team'}))
    else:
        st.write("No regular season data found.")

# ================= TAB 4: RECORDS =================
with tab4:
    rec_categories = {
        "Game Records": [
            "Highest Scoring Weeks",
            "Lowest Scoring Weeks",
            "Lowest Scoring Weekly Bags",
            "Largest Monday Night Comebacks",
            "Biggest Blowouts",
            "Closest Games"
        ],
        "Player Records": [
            "Highest Scoring Players",
            "Lowest Scoring Players",
            "Highest Scoring Stacks",
            "Most Unique Players Started",
            "Least Unique Players Started",
            "Most Fantasy Teams Started For",
            "Started on Same Fantasy Team for 3+ NFL Teams"
        ],
        "Season Records": [
            "Most Points Per Game in a Season",
            "Least Points Per Game in a Season",
            "Longest Win Streak",
            "Longest Losing Streak",
            "Highest Season Luck Factor",
            "Lowest Season Luck Factor"
        ],
        "Franchise Records": [
            "Team Record - Highest Score",
            "Team Record - Lowest Score",
            "Weekly Bag by Team",
            "Weekly Last Place Score by Team",
            "Playoff Record by Team",
            "Longest Head-to-Head Streaks"
        ],
        "Other": [
            "Weekly Scoring Rank Heatmap",
            "NFL Franchise Usage Matrix (12 Teams x 32 NFL Teams)"
        ]
    }
    if 'Top_2_Game' in games.columns:
        rec_categories["Game Records"].append("Top 2 Matchups")
    if 'Bottom_2_Game' in games.columns:
        rec_categories["Game Records"].append("Bottom 2 Matchups")

    sel_grp = st.radio("Record Category:", list(rec_categories.keys()), horizontal=True, key="rec_cat_group")
    rec_type = st.radio("Select Record:", rec_categories[sel_grp], horizontal=True, key="rec_sub_type")
    st.write("---")

    bag_szns = sorted([str(s).replace('.0','').strip() for s in games['Season'].unique() if str(s).replace('.0','').strip().isdigit() and int(str(s).replace('.0','').strip()) >= 2019], key=lambda x: int(x))
    lp_szns = sorted([str(s).replace('.0','').strip() for s in games['Season'].unique() if str(s).replace('.0','').strip().isdigit() and int(str(s).replace('.0','').strip()) >= 2017], key=lambda x: int(x))

    rs_map = {(str(r['Season']).replace('.0','').strip(), str(r['Team_Name']).strip()): format_ordinal(r['RS_Rank']) for _, r in rs_ranks_df.iterrows()} if not rs_ranks_df.empty and 'Team_Name' in rs_ranks_df.columns else {}
    po_all = games[games['Game_Type'] == 2]
    po_map = {(str(s).replace('.0','').strip(), str(t).strip()): get_playoff_outcome(grp) for (s, t), grp in po_all.groupby(['Season', 'Team_Name'])} if not po_all.empty else {}

    all_reg = games[games['Game_Type'] == 1].copy()
    if not all_reg.empty:
        all_reg['Season_Str'] = all_reg['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        all_reg['Weekly_Rank'] = all_reg.groupby(['Season_Str', 'Week_Num'])['Actual_Points'].rank(ascending=False, method='average')
        all_reg['N_Teams'] = all_reg.groupby(['Season_Str', 'Week_Num'])['Team_Name'].transform('count')
        all_reg['Exp_Win'] = all_reg.apply(lambda r: (r['N_Teams'] - r['Weekly_Rank']) / (r['N_Teams'] - 1) if r['N_Teams'] > 1 else 0.0, axis=1)
        
        s_agg = all_reg.groupby(['Season_Str', 'Team_Name']).agg(
            W=('W', 'sum'),
            L=('L', 'sum'),
            T=('T', 'sum'),
            PF=('Actual_Points', 'sum'),
            Exp_Win_Total=('Exp_Win', 'sum'),
            Games_Count=('W', 'count')
        ).reset_index()
        s_agg['Record'] = s_agg.apply(lambda r: f"{int(r['W'])}-{int(r['L'])}" + (f"-{int(r['T'])}" if r['T']>0 else ""), axis=1)
        s_agg['Luck_Num'] = s_agg['W'] - s_agg['Exp_Win_Total']
        s_agg['Expected Wins'] = s_agg['Exp_Win_Total'].apply(lambda x: f"{float(x):.1f}")
        s_agg['Luck Factor'] = s_agg['Luck_Num'].apply(lambda x: "0.0" if abs(x)<0.05 else f"{x:+.1f}")
        s_agg['PF_Formatted'] = s_agg['PF'].apply(lambda x: f"{float(x):.1f}")
        s_agg['PPG_Num'] = s_agg['PF'] / s_agg['Games_Count']
        s_agg['PF/G'] = s_agg['PPG_Num'].apply(lambda x: f"{float(x):.1f}")
        s_agg['Regular Season Finish'] = s_agg.apply(lambda r: rs_map.get((str(r['Season_Str']).strip(), str(r['Team_Name']).strip()), ""), axis=1)
        s_agg['Playoff Outcome'] = s_agg.apply(lambda r: po_map.get((str(r['Season_Str']).strip(), str(r['Team_Name']).strip()), ""), axis=1)
        s_agg = s_agg.rename(columns={'Season_Str': 'Season', 'Team_Name': 'Team'})
    else:
        s_agg = pd.DataFrame()

    s_comp = s_agg[s_agg['Season'].isin(completed_playoff_seasons)].copy() if not s_agg.empty else pd.DataFrame()

    if rec_type == "Highest Scoring Weeks":
        df = games[games['Game_Type'].isin([1, 2, 4])].copy()
        df['Points_Num'] = pd.to_numeric(df['Actual_Points'], errors='coerce')
        df = df.sort_values(['Points_Num', 'Season_Num', 'Week_Num'], ascending=[False, False, False]).head(15).reset_index(drop=True)
        df = apply_competition_rank(df, 'Points_Num', round_digits=1)
        df['Points'] = df['Points_Num'].apply(lambda x: f"{float(x):.1f}")
        render_html_table(df[['Rank', 'Season', 'Week', 'Team_Name', 'Points', 'Opponent_Team_Name']].rename(columns={'Team_Name': 'Team', 'Opponent_Team_Name': 'Opponent'}))

    elif rec_type == "Lowest Scoring Weeks":
        df = games[(games['Actual_Points'] > 0) & (games['Game_Type'].isin([1, 2]))].copy()
        df['Points_Num'] = pd.to_numeric(df['Actual_Points'], errors='coerce')
        df = df.sort_values(['Points_Num', 'Season_Num', 'Week_Num'], ascending=[True, False, False]).head(15).reset_index(drop=True)
        df = apply_competition_rank(df, 'Points_Num', round_digits=1)
        df['Points'] = df['Points_Num'].apply(lambda x: f"{float(x):.1f}")
        render_html_table(df[['Rank', 'Season', 'Week', 'Team_Name', 'Points', 'Opponent_Team_Name']].rename(columns={'Team_Name': 'Team', 'Opponent_Team_Name': 'Opponent'}))

    elif rec_type == "Lowest Scoring Weekly Bags":
        df = games[games['Is_High_Scorer']].copy()
        if not df.empty:
            df['Points_Num'] = pd.to_numeric(df['Actual_Points'], errors='coerce')
            df = df.sort_values(['Points_Num', 'Season_Num', 'Week_Num'], ascending=[True, False, False]).head(15).reset_index(drop=True)
            df = apply_competition_rank(df, 'Points_Num', round_digits=1)
            df['Points'] = df['Points_Num'].apply(lambda x: f"{float(x):.1f}")
            render_html_table(df[['Rank', 'Season', 'Week', 'Team_Name', 'Points', 'Opponent_Team_Name']].rename(columns={'Team_Name': 'Team', 'Opponent_Team_Name': 'Opponent'}))

    elif rec_type == "Largest Monday Night Comebacks":
        df = get_monday_comebacks(box_df, games)
        if not df.empty:
            df = apply_competition_rank(df, 'Deficit_Num', round_digits=1)
            cols = ['Rank', 'Deficit Overcome', 'Final Score', 'Winner', 'Loser', 'Season', 'Week', 'Winning Team Monday Players', 'Losing Team Monday Players']
            render_html_table(df[cols], left_align_cols=['Winning Team Monday Players', 'Losing Team Monday Players'])
        else:
            st.info("No Monday night comebacks found.")

    elif rec_type == "Biggest Blowouts":
        df = games[(games['W'] == 1) & (games['Game_Type'].isin([1, 2]))].copy()
        df['Margin_Num'] = pd.to_numeric(df['Margin'], errors='coerce')
        df = df.sort_values(['Margin_Num', 'Season_Num', 'Week_Num'], ascending=[False, False, False]).head(15).reset_index(drop=True)
        df = apply_competition_rank(df, 'Margin_Num', round_digits=1)
        df['Winner Pts'] = df['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        df['Loser Pts'] = df['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
        df['Margin_Disp'] = df['Margin_Num'].apply(lambda x: f"{float(x):.1f}")
        render_html_table(df[['Rank', 'Season', 'Week', 'Team_Name', 'Winner Pts', 'Opponent_Team_Name', 'Loser Pts', 'Margin_Disp']].rename(columns={'Team_Name': 'Winner', 'Opponent_Team_Name': 'Loser', 'Margin_Disp': 'Margin'}))

    elif rec_type == "Closest Games":
        df = games[(games['W'] == 1) & (games['Margin'] > 0) & (games['Margin'] <= 1.00) & (games['Game_Type'].isin([1, 2]))].copy()
        if not df.empty:
            df['Margin_Num'] = pd.to_numeric(df['Margin'], errors='coerce')
            df = df.sort_values(['Margin_Num', 'Season_Num', 'Week_Num'], ascending=[True, False, False]).reset_index(drop=True)
            df = apply_competition_rank(df, 'Margin_Num', round_digits=2)
            df['Winner Pts'] = df['Actual_Points'].apply(lambda x: f"{float(x):.2f}")
            df['Loser Pts'] = df['Opp_Points'].apply(lambda x: f"{float(x):.2f}")
            df['Margin_Disp'] = df['Margin_Num'].apply(lambda x: f"{float(x):.2f}")
            render_html_table(df[['Rank', 'Season', 'Week', 'Team_Name', 'Winner Pts', 'Opponent_Team_Name', 'Loser Pts', 'Margin_Disp']].rename(columns={'Team_Name': 'Winner', 'Opponent_Team_Name': 'Loser', 'Margin_Disp': 'Margin'}))
        else:
            st.info("No games decided by 1.00 point or less.")

    elif rec_type == "Top 2 Matchups":
        if 'Top_2_Game' in games.columns:
            top2_mask = games['Top_2_Game'].astype(str).str.strip().str.lower().isin(['1', '1.0', 'yes', 'true', 'y'])
            top2 = games[top2_mask].sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).drop_duplicates(subset=['Season', 'Week']).copy()
            top2['Season'] = top2['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            top2['Actual_Points'] = top2['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
            top2['Opp_Points'] = top2['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
            top2['Margin'] = top2['Margin'].apply(lambda x: f"{float(x):.1f}")
            render_html_table(top2[['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points', 'Margin']].rename(columns={'Team_Name': 'Team 1', 'Actual_Points': 'Team 1 Pts', 'Opponent_Team_Name': 'Team 2', 'Opp_Points': 'Team 2 Pts'}))

    elif rec_type == "Bottom 2 Matchups":
        if 'Bottom_2_Game' in games.columns:
            bot2_mask = games['Bottom_2_Game'].astype(str).str.strip().str.lower().isin(['1', '1.0', 'yes', 'true', 'y'])
            bot2 = games[bot2_mask].sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).drop_duplicates(subset=['Season', 'Week']).copy()
            bot2['Season'] = bot2['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            bot2['Actual_Points'] = bot2['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
            bot2['Opp_Points'] = bot2['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
            bot2['Margin'] = bot2['Margin'].apply(lambda x: f"{float(x):.1f}")
            render_html_table(bot2[['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points', 'Margin']].rename(columns={'Team_Name': 'Team 1', 'Actual_Points': 'Team 1 Pts', 'Opponent_Team_Name': 'Team 2', 'Opp_Points': 'Team 2 Pts'}))

    elif rec_type == "Highest Scoring Players":
        p = get_starter_performances(box_df, games)
        if not p.empty:
            top = p.sort_values(['Points_Num', 'Season', 'Week'], ascending=[False, False, False]).head(15).reset_index(drop=True)
            top = apply_competition_rank(top, 'Points_Num', round_digits=1)
            top['Points'] = top['Points_Num'].apply(lambda x: f"{float(x):.1f}")
            render_html_table(top[['Rank', 'Player', 'Pos', 'NFL Team', 'Points', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']])

    elif rec_type == "Lowest Scoring Players":
        p = get_starter_performances(box_df, games)
        if not p.empty:
            st.write("### Lowest Scoring Starters (All Positions)")
            low = p.sort_values(['Points_Num', 'Season', 'Week'], ascending=[True, False, False]).head(15).reset_index(drop=True)
            low = apply_competition_rank(low, 'Points_Num', round_digits=1)
            low['Points'] = low['Points_Num'].apply(lambda x: f"{float(x):.1f}")
            render_html_table(low[['Rank', 'Player', 'Pos', 'NFL Team', 'Points', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']])

            st.write("### Negative Point Starters (Non-Defense)")
            neg = p[(~p['Pos'].isin(['D/ST', 'DST', 'DEF', 'DP'])) & (p['Points_Num'] < 0)].sort_values(['Points_Num', 'Season', 'Week'], ascending=[True, False, False]).reset_index(drop=True)
            if not neg.empty:
                neg = apply_competition_rank(neg, 'Points_Num', round_digits=1)
                neg['Points'] = neg['Points_Num'].apply(lambda x: f"{float(x):.1f}")
                render_html_table(neg[['Rank', 'Player', 'Pos', 'NFL Team', 'Points', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']])

    elif rec_type == "Highest Scoring Stacks":
        p = get_starter_performances(box_df, games)
        if not p.empty:
            stks = []
            for (s, w, tm), g_df in p.groupby(['Season', 'Week', 'Team']):
                qbs, catchers = g_df[g_df['Pos'] == 'QB'], g_df[g_df['Pos'].isin(['WR', 'TE'])]
                for _, qr in qbs.iterrows():
                    nfl = str(qr['NFL Team']).strip()
                    if nfl and nfl not in ['-', 'FA']:
                        for _, cr in catchers[catchers['NFL Team'].astype(str).str.strip() == nfl].iterrows():
                            comb = float(qr['Points_Num']) + float(cr['Points_Num'])
                            stks.append({
                                'QB': f"{qr['Player']} ({float(qr['Points_Num']):.1f})",
                                'Pass Catcher': f"{cr['Player']} ({float(cr['Points_Num']):.1f})",
                                'Pos': cr['Pos'],
                                'NFL Team': nfl,
                                'Combined_Num': comb,
                                'Combined Pts': f"{comb:.1f}",
                                'Season': s,
                                'Week': w,
                                'Team': tm,
                                'Opponent': qr['Opponent'],
                                'Outcome': qr['Outcome']
                            })
            if stks:
                res = pd.DataFrame(stks).sort_values(['Combined_Num', 'Season', 'Week'], ascending=[False, False, False]).head(15).reset_index(drop=True)
                res = apply_competition_rank(res, 'Combined_Num', round_digits=1)
                render_html_table(res[['Rank', 'QB', 'Pass Catcher', 'Pos', 'NFL Team', 'Combined Pts', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']])

    elif rec_type in ["Most Unique Players Started", "Least Unique Players Started"]:
        is_least = (rec_type == "Least Unique Players Started")
        st_data, name_col = get_unique_starters_records(box_df, games, completed_only=is_least, completed_playoff_seasons=completed_playoff_seasons)
        if not st_data.empty:
            pf = st.radio("Position Filter:", ["All Positions", "QB", "RB", "WR", "TE", "K", "D/ST"], horizontal=True, key=f"pos_{rec_type}")
            sub = st_data if pf == "All Positions" else st_data[st_data['Clean_Pos'] == pf]
            rows = []
            for (s, tm), grp in sub.groupby(['Season_Str', 'Team_Str']):
                pl = sorted(list(set(str(x).strip() for x in grp[name_col].dropna().unique() if str(x).strip())))
                rows.append({
                    'Season': s,
                    'Team': tm,
                    'Players Started': len(pl),
                    'Regular Season Finish': rs_map.get((s, tm), ""),
                    'Playoff Outcome': po_map.get((s, tm), ""),
                    'Player List': ", ".join(pl)
                })
            if rows:
                df = pd.DataFrame(rows).sort_values(['Players Started', 'Season'], ascending=[is_least, False]).head(15).reset_index(drop=True)
                df = apply_competition_rank(df, 'Players Started', round_digits=0)
                render_html_table(df[['Rank', 'Season', 'Team', 'Players Started', 'Regular Season Finish', 'Playoff Outcome', 'Player List']], left_align_cols=['Player List'])

    elif rec_type == "Most Fantasy Teams Started For":
        p = get_starter_performances(box_df, games)
        if not p.empty:
            trav = [{'Player': pl, 'Pos': grp['Pos'].mode().iloc[0], 'Teams Count': len(set(grp['Team'])), 'Fantasy Teams': ", ".join(sorted(set(grp['Team'])))} for pl, grp in p[~p['Pos'].isin(['D/ST', 'DST', 'DEF', 'DP'])].groupby('Player') if len(set(grp['Team'])) > 1]
            if trav:
                df = pd.DataFrame(trav).sort_values(['Teams Count', 'Player'], ascending=[False, True]).head(15).reset_index(drop=True)
                df = apply_competition_rank(df, 'Teams Count', round_digits=0)
                render_html_table(df[['Rank', 'Player', 'Pos', 'Teams Count', 'Fantasy Teams']], left_align_cols=['Fantasy Teams'])

    elif rec_type == "Started on Same Fantasy Team for 3+ NFL Teams":
        p = get_starter_performances(box_df, games)
        if not p.empty:
            journeys = []
            for (pl, tm), grp in p[~p['Pos'].isin(['D/ST', 'DST', 'DEF', 'DP'])].groupby(['Player', 'Team']):
                nfls = sorted(set(t for t in grp['NFL Team'] if t and t not in ['-', 'FA', 'NONE']))
                if len(nfls) >= 3:
                    journeys.append({
                        'Player': pl,
                        'Pos': grp['Pos'].mode().iloc[0],
                        'Fantasy Team': tm,
                        'NFL Teams Count': len(nfls),
                        'NFL Teams': ", ".join(nfls)
                    })
            if journeys:
                df = pd.DataFrame(journeys).sort_values(['NFL Teams Count', 'Player'], ascending=[False, True]).reset_index(drop=True)
                df = apply_competition_rank(df, 'NFL Teams Count', round_digits=0)
                render_html_table(df[['Rank', 'Player', 'Pos', 'Fantasy Team', 'NFL Teams Count', 'NFL Teams']], left_align_cols=['NFL Teams'])

    elif rec_type == "Most Points Per Game in a Season":
        if not s_agg.empty:
            top = s_agg.sort_values(['PPG_Num', 'Season'], ascending=[False, False]).head(15).reset_index(drop=True)
            top = apply_competition_rank(top, 'PPG_Num', round_digits=1)
            top['Season_Display'] = top['Season'].apply(lambda s: f"{s}*" if str(s) == '2026' else str(s))
            render_html_table(
                top[['Rank', 'Season_Display', 'Team', 'Record', 'PF/G', 'PF_Formatted', 'Regular Season Finish', 'Playoff Outcome']].rename(columns={'Season_Display': 'Season', 'PF_Formatted': 'PF'}),
                highlight_fn=lambda r: ['font-style: italic; color: #1e3a8a;' if '*' in str(r.get('Season','')) else '' for _ in r.index]
            )
            if any(top['Season'] == '2026'):
                st.caption(r"\* *Active season*")

    elif rec_type == "Least Points Per Game in a Season":
        if not s_agg.empty:
            low = s_agg[s_agg['Season'] != '2017'].sort_values(['PPG_Num', 'Season'], ascending=[True, False]).head(20).reset_index(drop=True)
            low = apply_competition_rank(low, 'PPG_Num', round_digits=1)
            low['Season_Display'] = low['Season'].apply(lambda s: f"{s}*" if str(s) == '2026' else str(s))
            render_html_table(
                low[['Rank', 'Season_Display', 'Team', 'Record', 'PF/G', 'PF_Formatted', 'Regular Season Finish', 'Playoff Outcome']].rename(columns={'Season_Display': 'Season', 'PF_Formatted': 'PF'}),
                highlight_fn=lambda r: ['font-style: italic; color: #1e3a8a;' if '*' in str(r.get('Season','')) else '' for _ in r.index]
            )
            if any(low['Season'] == '2026'):
                st.caption(r"\* *Active season*")

    elif rec_type == "Longest Win Streak":
        w_df, _ = get_all_streaks_records(games)
        if not w_df.empty:
            df = w_df.sort_values(['Length', 'Season'], ascending=[False, False]).head(15).reset_index(drop=True)
            df = apply_competition_rank(df, 'Length', round_digits=0)
            df['Regular Season Finish'] = df.apply(lambda r: rs_map.get((str(r['Season']).strip(), str(r['Team']).strip()), ""), axis=1)
            df['Playoff Outcome'] = df.apply(lambda r: po_map.get((str(r['Season']).strip(), str(r['Team']).strip()), ""), axis=1)
            render_html_table(df[['Rank', 'Team', 'Season', 'Length', 'Span', 'Regular Season Finish', 'Playoff Outcome']].rename(columns={'Length': 'Streak'}))

    elif rec_type == "Longest Losing Streak":
        _, l_df = get_all_streaks_records(games)
        if not l_df.empty:
            df = l_df[l_df['Length'] >= 6].sort_values(['Length', 'Season'], ascending=[False, False]).reset_index(drop=True)
            if not df.empty:
                df = apply_competition_rank(df, 'Length', round_digits=0)
                df['Regular Season Finish'] = df.apply(lambda r: rs_map.get((str(r['Season']).strip(), str(r['Team']).strip()), ""), axis=1)
                df['Playoff Outcome'] = df.apply(lambda r: po_map.get((str(r['Season']).strip(), str(r['Team']).strip()), ""), axis=1)
                render_html_table(df[['Rank', 'Team', 'Season', 'Length', 'Span', 'Regular Season Finish', 'Playoff Outcome']].rename(columns={'Length': 'Streak'}))
            else:
                st.info("No losing streaks of 6 or more games on record.")

    elif rec_type == "Highest Season Luck Factor":
        if not s_comp.empty:
            df = s_comp[s_comp['Luck_Num'].round(1) >= 2.0].sort_values(['Luck_Num', 'Season'], ascending=[False, False]).reset_index(drop=True)
            if not df.empty:
                df = apply_competition_rank(df, 'Luck_Num', round_digits=1)
                render_html_table(df[['Rank', 'Season', 'Team', 'Record', 'Expected Wins', 'Luck Factor', 'Regular Season Finish', 'Playoff Outcome']])
            else:
                st.info("No completed seasons with a Luck Factor of +2.0 or higher.")

    elif rec_type == "Lowest Season Luck Factor":
        if not s_comp.empty:
            df = s_comp[s_comp['Luck_Num'].round(1) <= -2.0].sort_values(['Luck_Num', 'Season'], ascending=[True, False]).reset_index(drop=True)
            if not df.empty:
                df = apply_competition_rank(df, 'Luck_Num', round_digits=1)
                render_html_table(df[['Rank', 'Season', 'Team', 'Record', 'Expected Wins', 'Luck Factor', 'Regular Season Finish', 'Playoff Outcome']])
            else:
                st.info("No completed seasons with a Luck Factor of -2.0 or lower.")

    elif rec_type == "Team Record - Highest Score":
        scores = [{'Team': t, 'Points_Num': float(games[games['Team_Name']==t].loc[games[games['Team_Name']==t]['Actual_Points'].idxmax()]['Actual_Points']), 'Points': f"{float(games[games['Team_Name']==t].loc[games[games['Team_Name']==t]['Actual_Points'].idxmax()]['Actual_Points']):.1f}", 'Season': str(games[games['Team_Name']==t].loc[games[games['Team_Name']==t]['Actual_Points'].idxmax()]['Season']).replace('.0',''), 'Week': games[games['Team_Name']==t].loc[games[games['Team_Name']==t]['Actual_Points'].idxmax()]['Week'], 'Opponent': games[games['Team_Name']==t].loc[games[games['Team_Name']==t]['Actual_Points'].idxmax()]['Opponent_Team_Name']} for t in teams_no_cam if not games[games['Team_Name']==t].empty]
        if scores:
            df = pd.DataFrame(scores).sort_values(['Points_Num', 'Season'], ascending=[False, False]).reset_index(drop=True)
            df = apply_competition_rank(df, 'Points_Num', round_digits=1)
            render_html_table(df[['Rank', 'Team', 'Points', 'Season', 'Week', 'Opponent']])

    elif rec_type == "Team Record - Lowest Score":
        scores = [{'Team': t, 'Points_Num': float(games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].loc[games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)]['Actual_Points'].idxmin()]['Actual_Points']), 'Points': f"{float(games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].loc[games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)]['Actual_Points'].idxmin()]['Actual_Points']):.1f}", 'Season': str(games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].loc[games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)]['Actual_Points'].idxmin()]['Season']).replace('.0',''), 'Week': games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].loc[games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)]['Actual_Points'].idxmin()]['Week'], 'Opponent': games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].loc[games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)]['Actual_Points'].idxmin()]['Opponent_Team_Name']} for t in teams_no_cam if not games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].empty]
        if scores:
            df = pd.DataFrame(scores).sort_values(['Points_Num', 'Season'], ascending=[True, False]).reset_index(drop=True)
            df = apply_competition_rank(df, 'Points_Num', round_digits=1)
            render_html_table(df[['Rank', 'Team', 'Points', 'Season', 'Week', 'Opponent']])

    elif rec_type == "Weekly Bag by Team":
        data = [{'Team': t, **{s: int(games[(games['Team_Name']==t) & (games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()==s) & (games['Is_High_Scorer'])]['Is_High_Scorer'].sum()) for s in bag_szns}, 'Total': int(games[(games['Team_Name']==t) & (games['Season'].isin(bag_szns)) & (games['Is_High_Scorer'])]['Is_High_Scorer'].sum())} for t in teams_no_cam]
        render_html_table(pd.DataFrame(data).sort_values(['Total', 'Team'], ascending=[False, True])[['Team'] + bag_szns + ['Total']])

    elif rec_type == "Weekly Last Place Score by Team":
        reg = games[(games['Game_Type'] == 1) & (games['Season_Num'] >= 2017)].copy()
        min_p = reg.groupby(['Season', 'Week'])['Actual_Points'].transform('min')
        reg['Is_Low'] = (reg['Actual_Points'] == min_p)
        data = [{'Team': t, **{s: int(reg[(reg['Team_Name']==t) & (reg['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()==s)]['Is_Low'].sum()) for s in lp_szns}, 'Total': int(reg[(reg['Team_Name']==t) & (reg['Season'].isin(lp_szns))]['Is_Low'].sum())} for t in teams]
        render_html_table(pd.DataFrame(data).sort_values(['Total', 'Team'], ascending=[False, True])[['Team'] + lp_szns + ['Total']])

    elif rec_type == "Playoff Record by Team":
        po_rows = []
        for t in teams_no_cam:
            apps, byes = 0, 0
            if not rs_ranks_df.empty and 'Team_Name' in rs_ranks_df.columns:
                for _, r in rs_ranks_df[rs_ranks_df['Team_Name'] == t].iterrows():
                    szn = str(r['Season']).strip()
                    if szn.isdigit() and szn in completed_playoff_seasons:
                        s_int, rk = int(szn), float(r['RS_Rank'])
                        if pd.notnull(rk):
                            if (s_int == 2017 and rk <= 4) or (s_int > 2017 and rk <= 6): apps += 1
                            if s_int >= 2018 and rk <= 2: byes += 1
            pg = games[(games['Team_Name'] == t) & (games['Game_Type'] == 2)]
            r_str = pg['Playoff_Round'].astype(str).str.strip().str.lower()
            qf, sf, f = pg[r_str.str.contains('quarter')], pg[r_str.str.contains('semi')], pg[r_str.str.contains('final|champ') & ~r_str.str.contains('quarter|semi')]
            po_rows.append({
                'Team': t,
                'Appearances': apps,
                'Byes': byes,
                'Total_W': int(qf['W'].sum() + sf['W'].sum() + f['W'].sum()),
                'Total_L': int(qf['L'].sum() + sf['L'].sum() + f['L'].sum()),
                'QF_W': int(qf['W'].sum()),
                'QF_L': int(qf['L'].sum()),
                'SF_W': int(sf['W'].sum()),
                'SF_L': int(sf['L'].sum()),
                'F_W': int(f['W'].sum()),
                'F_L': int(f['L'].sum())
            })
        df_po = pd.DataFrame(po_rows).sort_values(['Appearances', 'Total_W', 'Byes'], ascending=[False, False, False])
        po_html = '<table style="width: 100%; border-collapse: collapse; text-align: center;"><thead><tr><th rowspan="2" style="border: 1px solid #e6e6e6;">Team</th><th rowspan="2" style="border: 1px solid #e6e6e6;">Playoff Appearances</th><th rowspan="2" style="border: 1px solid #e6e6e6;">Byes</th><th colspan="2" style="border: 1px solid #e6e6e6;">Total Postseason</th><th colspan="2" style="border: 1px solid #e6e6e6;">Quarterfinals</th><th colspan="2" style="border: 1px solid #e6e6e6;">Semifinals</th><th colspan="2" style="border: 1px solid #e6e6e6;">Finals</th></tr><tr><th style="border: 1px solid #e6e6e6;">W</th><th style="border: 1px solid #e6e6e6;">L</th><th style="border: 1px solid #e6e6e6;">W</th><th style="border: 1px solid #e6e6e6;">L</th><th style="border: 1px solid #e6e6e6;">W</th><th style="border: 1px solid #e6e6e6;">L</th><th style="border: 1px solid #e6e6e6;">W</th><th style="border: 1px solid #e6e6e6;">L</th></tr></thead><tbody>' + "".join([f'<tr><td style="border: 1px solid #e6e6e6;">{r["Team"]}</td><td style="border: 1px solid #e6e6e6;">{r["Appearances"]}</td><td style="border: 1px solid #e6e6e6;">{r["Byes"]}</td><td style="border: 1px solid #e6e6e6;">{r["Total_W"]}</td><td style="border: 1px solid #e6e6e6;">{r["Total_L"]}</td><td style="border: 1px solid #e6e6e6;">{r["QF_W"]}</td><td style="border: 1px solid #e6e6e6;">{r["QF_L"]}</td><td style="border: 1px solid #e6e6e6;">{r["SF_W"]}</td><td style="border: 1px solid #e6e6e6;">{r["SF_L"]}</td><td style="border: 1px solid #e6e6e6;">{r["F_W"]}</td><td style="border: 1px solid #e6e6e6;">{r["F_L"]}</td></tr>' for _, r in df_po.iterrows()]) + '</tbody></table>'
        st.markdown(po_html, unsafe_allow_html=True)

    elif rec_type == "Longest Head-to-Head Streaks":
        st.write("### Longest Head-to-Head Streaks")
        st.write("Longest consecutive head-to-head winning streaks of 6 or more games by one manager over another (Regular Season & Championship Playoffs only; consolation games excluded).")

        comp_g = games[
            games['Game_Type'].isin([1, 2]) & 
            (games['Team_Name'].str.upper() != 'CAM') & 
            (games['Opponent_Team_Name'].str.upper() != 'CAM')
        ].copy()
        comp_g['Season_Num'] = pd.to_numeric(comp_g['Season'], errors='coerce')
        comp_g['Week_Num'] = pd.to_numeric(comp_g['Week'], errors='coerce')
        comp_g = comp_g.sort_values(['Season_Num', 'Week_Num', 'Game_Type'])

        h2h_streaks = []
        for (tm, opp), m_grp in comp_g.groupby(['Team_Name', 'Opponent_Team_Name']):
            m_list = m_grp.to_dict('records')
            curr_streak = 0
            po_games = []
            start_r = None
            end_r = None
            
            for row in m_list:
                if row['W'] == 1:
                    if curr_streak == 0:
                        start_r = row
                        po_games = []
                    curr_streak += 1
                    if row['Game_Type'] == 2:
                        rnd = str(row.get('Playoff_Round', '')).strip()
                        szn = str(row['Season']).replace('.0', '').strip()
                        rnd_clean = rnd.title() if rnd else "Playoffs"
                        po_games.append(f"{rnd_clean} {szn}")
                    end_r = row
                else:
                    if curr_streak >= 6:
                        s_lbl = f"{str(start_r['Season']).replace('.0','')}, W{start_r['Week']}"
                        e_lbl = f"{str(end_r['Season']).replace('.0','')}, W{end_r['Week']}"
                        span_str = s_lbl if curr_streak == 1 else f"{s_lbl} to {e_lbl}"
                        po_str = ", ".join(po_games)
                        h2h_streaks.append({
                            'Team': tm,
                            'Opponent': opp,
                            'Streak_Num': curr_streak,
                            'Streak': str(curr_streak),
                            'Span': span_str,
                            'Playoffs': po_str,
                            'Is_Active': False,
                            'End_Season': float(end_r['Season_Num']),
                            'End_Week': float(end_r['Week_Num'])
                        })
                    curr_streak = 0
                    po_games = []
                    start_r = None
                    end_r = None
                    
            if curr_streak >= 6:
                s_lbl = f"{str(start_r['Season']).replace('.0','')}, W{start_r['Week']}"
                e_lbl = f"{str(end_r['Season']).replace('.0','')}, W{end_r['Week']}"
                span_str = s_lbl if curr_streak == 1 else f"{s_lbl} to {e_lbl}"
                po_str = ", ".join(po_games)
                h2h_streaks.append({
                    'Team': tm,
                    'Opponent': opp,
                    'Streak_Num': curr_streak,
                    'Streak': f"{curr_streak}*",
                    'Span': span_str,
                    'Playoffs': po_str,
                    'Is_Active': True,
                    'End_Season': float(end_r['Season_Num']),
                    'End_Week': float(end_r['Week_Num'])
                })

        if h2h_streaks:
            df_h2h = pd.DataFrame(h2h_streaks)
            df_h2h = df_h2h.sort_values(['Streak_Num', 'End_Season', 'End_Week'], ascending=[False, False, False]).reset_index(drop=True)
            df_h2h = apply_competition_rank(df_h2h, 'Streak_Num', round_digits=0)
            
            hl_active = lambda r: ['font-weight: bold; color: #1e3a8a;' if '*' in str(r.get('Streak','')) else '' for _ in r.index]
            render_html_table(df_h2h[['Rank', 'Team', 'Opponent', 'Streak', 'Span', 'Playoffs']], highlight_fn=hl_active)
            if any(df_h2h['Is_Active']):
                st.caption(r"\* *Active streak unbroken through the most recent head-to-head matchup.*")
        else:
            st.info("No head-to-head streaks of 6 or more games on record.")

    elif rec_type == "Weekly Scoring Rank Heatmap":
        st.write("### Weekly Scoring Rank Heatmap")
        st.write("Weekly score rankings of each team during the regular season. Green indicates a matchup win and red indicates a loss. The dashed line divides the top half from the bottom half.")

        c1, c2 = st.columns([2, 2])
        with c1:
            sel_heat_szn = st.selectbox("Select Season:", seasons_list, key="heat_szn_select")
        with c2:
            st.write("")
            st.write("")
            show_pts = st.checkbox("Show Points with Team Name", value=False, key="heat_show_pts")

        szn_g = games[(games['Season'] == str(sel_heat_szn)) & (games['Game_Type'] == 1)].copy()
        if not szn_g.empty:
            weeks_in_szn = sorted(szn_g['Week_Num'].dropna().unique().astype(int))
            all_teams_in_szn = sorted(szn_g['Team_Name'].dropna().unique().tolist())
            total_teams = len(all_teams_in_szn)
            median_rank = total_teams // 2 if total_teams > 0 else 6

            week_rankings = {}
            for w in weeks_in_szn:
                wk_df = szn_g[szn_g['Week_Num'] == w].sort_values(by=['Actual_Points'], ascending=False).reset_index(drop=True)
                for r_idx, row in wk_df.iterrows():
                    r_num = r_idx + 1
                    t_name = str(row['Team_Name']).strip()
                    pts = float(row['Actual_Points'])
                    outcome = 'win' if row['W'] == 1 else ('loss' if row['L'] == 1 else 'tie')
                    week_rankings[(r_num, w)] = (t_name, pts, outcome)

            html_rows = []
            header_cells = '<th style="border: 1px solid #c0c0c0; background-color: #f2f2f2; padding: 6px 12px; font-weight: 700;">Rank</th>'
            for w in weeks_in_szn:
                header_cells += f'<th style="border: 1px solid #c0c0c0; background-color: #f2f2f2; padding: 6px 14px; font-weight: 700;">{w}</th>'
            html_rows.append(f'<thead><tr>{header_cells}</tr></thead><tbody>')

            for r_num in range(1, total_teams + 1):
                is_median_row = (r_num == median_rank)
                row_border_style = "border-bottom: 2.5px dashed #111111;" if is_median_row else "border-bottom: 1px solid #c0c0c0;"
                
                cells = f'<td style="border: 1px solid #c0c0c0; {row_border_style} background-color: #f9f9f9; font-weight: 700; padding: 6px 10px;">{r_num}</td>'
                for w in weeks_in_szn:
                    entry = week_rankings.get((r_num, w), None)
                    if entry:
                        t_name, pts, outcome = entry
                        if outcome == 'win':
                            bg_color = "#d9ead3"
                            text_color = "#155724"
                        elif outcome == 'loss':
                            bg_color = "#f4cccc"
                            text_color = "#721c24"
                        else:
                            bg_color = "#fff2cc"
                            text_color = "#7f6000"
                        
                        disp_text = f"{t_name} ({pts:.1f})" if show_pts else t_name
                        cells += f'<td style="border: 1px solid #c0c0c0; {row_border_style} background-color: {bg_color}; color: {text_color}; padding: 6px 10px; white-space: nowrap;">{disp_text}</td>'
                    else:
                        cells += f'<td style="border: 1px solid #c0c0c0; {row_border_style} background-color: #ffffff; color: #888888; padding: 6px 10px;">-</td>'

                html_rows.append(f'<tr>{cells}</tr>')

            html_rows.append('</tbody>')
            full_table_html = f'<table style="width: auto; border-collapse: collapse; text-align: center; font-size: 14px; margin-top: 15px;">{"".join(html_rows)}</table>'
            st.markdown(full_table_html, unsafe_allow_html=True)
        else:
            st.info("No regular season matchup data found for the selected season.")

    elif rec_type == "NFL Franchise Usage Matrix (12 Teams x 32 NFL Teams)":
        st.write("### NFL Franchise Usage Matrix (12 Fantasy Teams x 32 NFL Teams)")
        st.write("Cross-tabulated reliance of all 12 fantasy franchises across all 32 NFL teams (Starters in Regular Season & Playoffs).")

        c1, c2 = st.columns([1.5, 2])
        with c1:
            sel_nfl_szn = st.selectbox("Season:", ["All-Time"] + seasons_list, key="nfl_mat_szn")
        with c2:
            sel_nfl_met = st.radio("Metric:", ["Total Fantasy Points", "Total Starts"], horizontal=True, key="nfl_mat_met")

        slot_c = 'Slot' if 'Slot' in box_df.columns else ('Lineup_Slot' if 'Lineup_Slot' in box_df.columns else 'Position')
        name_c = 'Player_Name' if 'Player_Name' in box_df.columns else 'Player'
        pts_c = 'Actual_Points' if 'Actual_Points' in box_df.columns else 'Points'
        nfl_c = next((c for c in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev', 'Team_Abbr', 'Pro_Team_Abbrev', 'Pro Team', 'NFL Team'] if c in box_df.columns), None)

        b_mat = box_df.copy()
        b_mat['Season_Str'] = b_mat['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        b_mat['Week_Num'] = pd.to_numeric(b_mat['Week'], errors='coerce').fillna(0).astype(int)
        b_mat['Team_Str'] = b_mat['Team_Name'].astype(str).str.strip()
        b_mat['NFL_Clean'] = b_mat[nfl_c].fillna('').astype(str).str.strip().str.upper() if nfl_c else ""
        b_mat['Pts_Num'] = pd.to_numeric(b_mat[pts_c], errors='coerce').fillna(0)

        starters_mat = b_mat[~b_mat[slot_c].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])].copy()

        el_games_mat = games[games['Game_Type'].isin([1, 2, 4]) & (games['Team_Name'].str.upper() != 'CAM')][['Season', 'Week', 'Team_Name']].drop_duplicates()
        el_games_mat['Season_Str'] = el_games_mat['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        el_games_mat['Week_Num'] = pd.to_numeric(el_games_mat['Week'], errors='coerce').fillna(0).astype(int)
        el_games_mat['Team_Str'] = el_games_mat['Team_Name'].astype(str).str.strip()

        merged_mat = pd.merge(
            starters_mat,
            el_games_mat[['Season_Str', 'Week_Num', 'Team_Str']],
            on=['Season_Str', 'Week_Num', 'Team_Str'],
            how='inner'
        )

        if sel_nfl_szn != "All-Time":
            merged_mat = merged_mat[merged_mat['Season_Str'] == str(sel_nfl_szn)]

        def map_mat_nfl(row):
            abbr = row['NFL_Clean']
            if abbr in NFL_ABBR_TO_FULL:
                return NFL_ABBR_TO_FULL[abbr]
            p_str = str(row[name_c]).upper()
            for full_name, nicks, abbrs in NFL_32_DEFENSES:
                if abbr in abbrs or any(nick in p_str for nick in nicks):
                    return full_name
            return None

        merged_mat['Mapped_NFL_Team'] = merged_mat.apply(map_mat_nfl, axis=1)
        valid_mat = merged_mat[merged_mat['Mapped_NFL_Team'].notnull()].copy()

        if not valid_mat.empty:
            agg_mat = valid_mat.groupby(['Mapped_NFL_Team', 'Team_Str']).agg(
                Starts=('Pts_Num', 'count'),
                Points=('Pts_Num', 'sum')
            ).reset_index()

            val_metric = 'Points' if sel_nfl_met == "Total Fantasy Points" else 'Starts'
            pivot_mat = agg_mat.pivot(index='Mapped_NFL_Team', columns='Team_Str', values=val_metric).fillna(0)

            pivot_mat = pivot_mat.reindex(ALL_32_NFL_TEAMS, fill_value=0.0)
            for tm in teams_no_cam:
                if tm not in pivot_mat.columns:
                    pivot_mat[tm] = 0.0
            pivot_mat = pivot_mat[teams_no_cam]

            table_mat = pivot_mat.copy()
            table_mat['Total'] = table_mat[teams_no_cam].sum(axis=1)
            table_mat = table_mat.sort_values('Total', ascending=False)

            table_disp = pd.DataFrame(index=table_mat.index)
            for col in table_mat.columns:
                if val_metric == 'Points':
                    table_disp[col] = table_mat[col].apply(lambda v: f"{float(v):,.1f}")
                else:
                    table_disp[col] = table_mat[col].apply(lambda v: f"{int(v):,}")

            table_disp = table_disp.reset_index().rename(columns={'Mapped_NFL_Team': 'NFL Team'})
            
            tot_row = {'NFL Team': 'TOTAL'}
            for col in teams_no_cam + ['Total']:
                raw_sum = table_mat[col].sum()
                tot_row[col] = f"{raw_sum:,.1f}" if val_metric == 'Points' else f"{int(raw_sum):,}"
            
            table_disp = pd.concat([table_disp, pd.DataFrame([tot_row])], ignore_index=True)
            hl_tot = lambda r: ['font-weight: bold; background-color: #f2f2f2;' if str(r.get('NFL Team','')).upper() == 'TOTAL' else '' for _ in r.index]
            render_html_table(table_disp, left_align_cols=['NFL Team'], highlight_fn=hl_tot)
        else:
            st.info("No starter data found for the selected season.")

# ================= TAB 7: DETAILED PLAYER SCORING =================
with tab_player:
    if box_df.empty:
        st.warning("Player data not found.")
    else:
        c1, c2, c3 = st.columns([1.5, 1.5, 2])
        d_team = c1.selectbox("Select Manager", teams, key="dps_team")
        d_year = c2.selectbox("Season", ["All-Time"] + seasons_list, key="dps_year")
        d_pos = c3.selectbox("Position View", ["All Positions", "QB", "RB", "WR", "TE", "K", "D/ST"], key="dps_pos")
        col_dyn = "Years" if d_year == "All-Time" else "Weeks"

        b_clean = box_df.copy()
        b_clean['Season_Str'] = b_clean['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        b_clean['Week_Num'] = pd.to_numeric(b_clean['Week'], errors='coerce').fillna(0).astype(int)
        b_clean['Team_Str'] = b_clean['Team_Name'].astype(str).str.strip()

        el_g = games[(games['Team_Name'] == d_team) & (games['Game_Type'].isin([1, 2, 4]))][['Season', 'Week', 'Team_Name']].drop_duplicates()
        el_g['Season_Str'] = el_g['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        el_g['Week_Num'] = pd.to_numeric(el_g['Week'], errors='coerce').fillna(0).astype(int)
        el_g['Team_Str'] = el_g['Team_Name'].astype(str).str.strip()

        slot_c = 'Slot' if 'Slot' in b_clean.columns else ('Lineup_Slot' if 'Lineup_Slot' in b_clean.columns else 'Position')
        name_c = 'Player_Name' if 'Player_Name' in b_clean.columns else 'Player'
        pts_c = 'Actual_Points' if 'Actual_Points' in b_clean.columns else 'Points'
        pos_c = 'Position' if 'Position' in b_clean.columns else ('Pos' if 'Pos' in b_clean.columns else slot_c)
        nfl_c = next((c for c in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev', 'Team_Abbr', 'Pro_Team_Abbrev', 'Pro Team', 'NFL Team'] if c in b_clean.columns), None)
        b_clean['NFL_Team_Clean'] = b_clean[nfl_c].fillna('').astype(str).str.strip() if nfl_c else ""

        starters = b_clean[(b_clean['Team_Str'] == d_team) & (~b_clean[slot_c].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH']))]
        counted = pd.merge(starters, el_g[['Season_Str', 'Week_Num', 'Team_Str']], on=['Season_Str', 'Week_Num', 'Team_Str'], how='inner')
        if d_year != "All-Time": 
            counted = counted[counted['Season_Str'] == str(d_year)]

        def clean_p(v):
            p = str(v).strip().upper()
            if p in ['K', 'PK']: return 'K'
            if p in ['D/ST', 'DST', 'DEF', 'DP']: return 'D/ST'
            return p if p in ['QB', 'RB', 'WR', 'TE'] else p
        counted['Clean_Pos'] = counted[pos_c].apply(clean_p)
        counted[pts_c] = pd.to_numeric(counted[pts_c], errors='coerce').fillna(0)

        def find_c(cands, fallback_kws=None, fallback_exclude=None):
            for cand in cands:
                cn = str(cand).lower().replace('_', '').replace(' ', '').replace('/', '').replace('-', '').strip()
                for c in counted.columns:
                    c_norm = str(c).lower().replace('_', '').replace(' ', '').replace('/', '').replace('-', '').strip()
                    if c_norm == cn:
                        return c
            if fallback_kws:
                for c in counted.columns:
                    c_str = str(c).lower().replace(' ', '_')
                    if all(kw in c_str for kw in fallback_kws):
                        if fallback_exclude and any(ex in c_str for ex in fallback_exclude):
                            continue
                        return c
            return None

        c_pyd = find_c(['Passing_Yards', 'Pass_Yds', 'Pass_Yards', 'Passing_Yds', 'Passing Yards', 'Pass Yds'], fallback_kws=['pass', 'yd'])
        c_ptd = find_c(['Passing_TDs', 'Pass_TD', 'Pass_TDs', 'Passing_Touchdowns', 'Passing TDs', 'Pass TD'], fallback_kws=['pass', 'td'], fallback_exclude=['rush', 'rec', 'def'])
        c_int = find_c(['Passing_Interceptions', 'Passing_Int', 'Pass_Int', 'Interceptions', 'INT', 'Pass INT'], fallback_kws=['int'], fallback_exclude=['def'])
        c_ryd = find_c(['Rushing_Yards', 'Rush_Yds', 'Rush_Yards', 'Rushing_Yds', 'Rushing Yards', 'Rush Yds'], fallback_kws=['rush', 'yd'])
        c_rtd = find_c(['Rushing_TDs', 'Rush_TD', 'Rush_TDs', 'Rushing_Touchdowns', 'Rushing TDs', 'Rush TD'], fallback_kws=['rush', 'td'], fallback_exclude=['pass', 'rec', 'def'])
        c_rec = find_c(['Receptions', 'Rec', 'Catches'], fallback_kws=['rec'], fallback_exclude=['yard', 'td', 'pass', 'rush', 'def', 'fum', 'int'])
        c_eyd = find_c(['Receiving_Yards', 'Rec_Yds', 'Rec_Yards', 'Receiving_Yds', 'Receiving Yards', 'Rec Yds'], fallback_kws=['rec', 'yd'], fallback_exclude=['pass', 'rush'])
        c_etd = find_c(['Receiving_TDs', 'Rec_TD', 'Rec_TDs', 'Receiving_Touchdowns', 'Receiving TDs', 'Rec TD'], fallback_kws=['rec', 'td'], fallback_exclude=['pass', 'rush', 'def', 'int', 'fum'])
        c_sck = find_c(['Sacks', 'Sack'])
        c_dint = find_c(['Defensive_Interceptions', 'Def_INT', 'Defensive_Int'], fallback_kws=['def', 'int'])
        c_fr = find_c(['Fumbles_Recovered', 'FR', 'Fum_Rec'], fallback_kws=['fum', 'rec'])
        c_dtd = find_c(['Defensive_TDs', 'Def_TD', 'Def_TDs'], fallback_kws=['def', 'td'])
        c_fgm = find_c(['Field_Goals_Made', 'FGM', 'FG_Made'], fallback_kws=['fg', 'made'])
        c_xpm = find_c(['Extra_Points_Made', 'XPM', 'XP_Made'], fallback_kws=['xp', 'made'])
        
        def s_sum(grp, col): 
            if col and col in grp.columns:
                return int(round(pd.to_numeric(grp[col], errors='coerce').fillna(0).sum()))
            return 0

        def build_table(p_target):
            sub = counted[counted['Clean_Pos'] == p_target]
            if sub.empty: return pd.DataFrame()
            rows = []
            for player, grp in sub.groupby(name_c):
                pts = pd.to_numeric(grp[pts_c], errors='coerce').fillna(0).sum()
                if pts <= 0: continue
                starts = len(grp)
                tms = ", ".join(sorted(set(t for t in grp['NFL_Team_Clean'] if t))) or "-"
                t_str = ", ".join(sorted(set(grp['Season_Str']), key=lambda x: int(x) if x.isdigit() else 0)) if d_year == "All-Time" else format_ranges(grp['Week_Num'].dropna().tolist())
                row = {'Player': player, 'NFL Team': tms, 'Starts': starts, 'Points_Num': pts, 'Points': f"{pts:.1f}", 'PPG': f"{pts/starts:.1f}", col_dyn: t_str}
                if p_target == 'QB': row.update({'Pass Yds': s_sum(grp, c_pyd), 'Pass TD': s_sum(grp, c_ptd), 'INT': s_sum(grp, c_int), 'Rush Yds': s_sum(grp, c_ryd), 'Rush TD': s_sum(grp, c_rtd)})
                elif p_target == 'RB': row.update({'Rush Yds': s_sum(grp, c_ryd), 'Rush TD': s_sum(grp, c_rtd), 'Rec': s_sum(grp, c_rec), 'Rec Yds': s_sum(grp, c_eyd), 'Rec TD': s_sum(grp, c_etd)})
                elif p_target in ['WR', 'TE']:
                    row.update({'Rec': s_sum(grp, c_rec), 'Rec Yds': s_sum(grp, c_eyd), 'Rec TD': s_sum(grp, c_etd)})
                    if p_target == 'WR': row.update({'Rush Yds': s_sum(grp, c_ryd), 'Rush TD': s_sum(grp, c_rtd)})
                elif p_target == 'K':
                    if c_fgm: row['FGM'] = s_sum(grp, c_fgm)
                    if c_xpm: row['XPM'] = s_sum(grp, c_xpm)
                elif p_target == 'D/ST':
                    if c_sck: row['Sacks'] = s_sum(grp, c_sck)
                    if c_dint: row['INT'] = s_sum(grp, c_dint)
                    if c_fr: row['FR'] = s_sum(grp, c_fr)
                    if c_dtd: row['TD'] = s_sum(grp, c_dtd)
                rows.append(row)
            if not rows: return pd.DataFrame()
            df = pd.DataFrame(rows).sort_values(['Points_Num', 'Starts'], ascending=[False, False]).reset_index(drop=True)
            base = ['Player', 'NFL Team', 'Starts'] if p_target != 'D/ST' else ['Player', 'Starts']
            stats_cols = {
                'QB': ['Pass Yds', 'Pass TD', 'INT', 'Rush Yds', 'Rush TD'],
                'RB': ['Rush Yds', 'Rush TD', 'Rec', 'Rec Yds', 'Rec TD'],
                'WR': ['Rec', 'Rec Yds', 'Rec TD', 'Rush Yds', 'Rush TD'],
                'TE': ['Rec', 'Rec Yds', 'Rec TD'],
                'K': [c for c in ['FGM', 'XPM'] if c in df.columns],
                'D/ST': [c for c in ['Sacks', 'INT', 'FR', 'TD'] if c in df.columns]
            }.get(p_target, [])
            return df[[c for c in base + stats_cols + ['Points', 'PPG', col_dyn] if c in df.columns]]

        pos_list = ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST'] if d_pos == "All Positions" else [d_pos]
        titles = {
            'QB': 'Quarterbacks (QB)',
            'RB': 'Running Backs (RB)',
            'WR': 'Wide Receivers (WR)',
            'TE': 'Tight Ends (TE)',
            'K': 'Kickers (K)',
            'D/ST': 'Defense / Special Teams (D/ST)'
        }

        for p_code in pos_list:
            st.write(f"### {titles[p_code]}")
            tbl = build_table(p_code)
            if not tbl.empty: 
                render_html_table(tbl)
            else: 
                st.info(f"No {titles[p_code]} on record.")

            if p_code == 'D/ST' and d_year == "All-Time":
                dst_counted = counted[counted['Clean_Pos'] == 'D/ST']
                unstarted = get_unstarted_defenses(dst_counted, name_c)
                if unstarted:
                    st.markdown(
                        f"<div style='margin-top: 10px; font-size: 14px;'><b>Defenses Never Started ({len(unstarted)}):</b> {', '.join(unstarted)}</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        "<div style='margin-top: 10px; font-size: 14px;'><b>Defenses Never Started:</b> None (All 32 NFL team defenses have been started)</div>",
                        unsafe_allow_html=True
                    )

            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

        # ================= 32-TEAM NFL FRANCHISE PRODUCTION TABLE =================
        st.divider()
        st.write(f"### NFL Franchise Production Breakdown ({d_year})")

        def map_row_to_nfl_team(r):
            abbr = str(r.get('NFL_Team_Clean', '')).strip().upper()
            if abbr in NFL_ABBR_TO_FULL:
                return NFL_ABBR_TO_FULL[abbr]
            p_name = str(r.get(name_c, '')).upper()
            for full_name, nicks, abbrs in NFL_32_DEFENSES:
                if abbr in abbrs or any(nick in p_name for nick in nicks):
                    return full_name
            return None

        counted_nfl = counted.copy()
        counted_nfl['Mapped_NFL_Team'] = counted_nfl.apply(map_row_to_nfl_team, axis=1)

        total_mgr_pts = counted_nfl[pts_c].sum()

        nfl_summary_rows = []
        for nfl_team in ALL_32_NFL_TEAMS:
            t_data = counted_nfl[counted_nfl['Mapped_NFL_Team'] == nfl_team]
            starts_cnt = len(t_data)
            tot_pts = t_data[pts_c].sum()
            pts_per_start = tot_pts / starts_cnt if starts_cnt > 0 else 0.0
            pct_pts = (tot_pts / total_mgr_pts * 100) if total_mgr_pts > 0 else 0.0
            
            if not t_data.empty and tot_pts > 0:
                p_lead = t_data.groupby(name_c)[pts_c].sum().sort_values(ascending=False)
                top_player_str = f"{p_lead.index[0]} ({p_lead.iloc[0]:.1f})"
            else:
                top_player_str = "-"

            nfl_summary_rows.append({
                'NFL Team': nfl_team,
                'Starts': starts_cnt,
                'Points_Num': tot_pts,
                'Points': f"{tot_pts:.1f}",
                'Pts / Start': f"{pts_per_start:.1f}",
                '% of Team Pts': f"{pct_pts:.1f}%",
                'Top Contributor': top_player_str
            })

        df_nfl = pd.DataFrame(nfl_summary_rows).sort_values(['Points_Num', 'Starts', 'NFL Team'], ascending=[False, False, True]).reset_index(drop=True)
        df_nfl = apply_competition_rank(df_nfl, 'Points_Num', round_digits=1)

        render_html_table(
            df_nfl[['Rank', 'NFL Team', 'Starts', 'Points', 'Pts / Start', '% of Team Pts', 'Top Contributor']],
            left_align_cols=['NFL Team', 'Top Contributor']
        )
        
