import streamlit as st
import pandas as pd

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
                
