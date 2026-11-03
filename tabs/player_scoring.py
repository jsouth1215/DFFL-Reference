import streamlit as st
import pandas as pd
from utils import render_html_table, format_ranges

def render(games, box_df, teams, seasons_list):
    if box_df.empty:
        st.warning("Player data not found.")
        return
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
    nfl_c = next((c for c in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev'] if c in b_clean.columns), None)
    b_clean['NFL_Team_Clean'] = b_clean[nfl_c].fillna('').astype(str).str.strip() if nfl_c else ""

    starters = b_clean[(b_clean['Team_Str'] == d_team) & (~b_clean[slot_c].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH']))]
    counted = pd.merge(starters, el_g[['Season_Str', 'Week_Num', 'Team_Str']], on=['Season_Str', 'Week_Num', 'Team_Str'], how='inner')
    if d_year != "All-Time": counted = counted[counted['Season_Str'] == str(d_year)]

    def clean_p(v):
        p = str(v).strip().upper()
        if p in ['K', 'PK']: return 'K'
        if p in ['D/ST', 'DST', 'DEF', 'DP']: return 'D/ST'
        return p if p in ['QB', 'RB', 'WR', 'TE'] else p
    counted['Clean_Pos'] = counted[pos_c].apply(clean_p)
    counted[pts_c] = pd.to_numeric(counted[pts_c], errors='coerce').fillna(0)

    def find_c(cands):
        for cand in cands:
            cn = cand.lower().replace('_', '')
            for c in counted.columns:
                if str(c).lower().replace('_', '') == cn: return c
        return None

    c_pyd = find_c(['Passing_Yards', 'Pass_Yds'])
    c_ptd = find_c(['Passing_TDs', 'Pass_TD', 'Passing_Touchdowns'])
    c_int = find_c(['Passing_Interceptions', 'Passing_Int', 'INT'])
    c_ryd = find_c(['Rushing_Yards', 'Rush_Yds'])
    c_rtd = find_c(['Rushing_TDs', 'Rush_TD', 'Rushing_Touchdowns'])
    c_rec = find_c(['Receptions', 'Rec'])
    c_eyd = find_c(['Receiving_Yards', 'Rec_Yds'])
    c_etd = find_c(['Receiving_TDs', 'Rec_TD', 'Receiving_Touchdowns'])
    c_sck = find_c(['Sacks', 'Sack'])
    c_dint = find_c(['Defensive_Interceptions', 'Def_INT'])
    c_fr = find_c(['Fumbles_Recovered', 'FR'])
    c_dtd = find_c(['Defensive_TDs', 'Def_TD'])
    c_fgm = find_c(['Field_Goals_Made', 'FGM'])
    c_xpm = find_c(['Extra_Points_Made', 'XPM'])
    def s_sum(grp, col): return int(round(pd.to_numeric(grp[col], errors='coerce').fillna(0).sum())) if col and col in grp.columns else 0

    def build_table(p_target):
        sub = counted[counted['Clean_Pos'] == p_target]
        if sub.empty: return pd.DataFrame()
        rows = []
        for player, grp in sub.groupby(name_c):
            pts = pd.to_numeric(grp[pts_c], errors='coerce').fillna(0).sum()
            if pts <= 0: continue
            starts = len(grp)
            tms = ", ".join(sorted(set(t for t in grp['NFL_Team_Clean'] if t))) or "-"
            t_str = ", ".join(sorted(set(grp['Season_Str']), key=lambda x: int(x) if x.isdigit() else 0)) if d_year == "All-Time" else format_ranges(grp['Week_Num'])
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
        stats_cols = {'QB': ['Pass Yds', 'Pass TD', 'INT', 'Rush Yds', 'Rush TD'], 'RB': ['Rush Yds', 'Rush TD', 'Rec', 'Rec Yds', 'Rec TD'], 'WR': ['Rec', 'Rec Yds', 'Rec TD', 'Rush Yds', 'Rush TD'], 'TE': ['Rec', 'Rec Yds', 'Rec TD'], 'K': [c for c in ['FGM', 'XPM'] if c in df.columns], 'D/ST': [c for c in ['Sacks', 'INT', 'FR', 'TD'] if c in df.columns]}.get(p_target, [])
        return df[[c for c in base + stats_cols + ['Points', 'PPG', col_dyn] if c in df.columns]]

    pos_list = ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST'] if d_pos == "All Positions" else [d_pos]
    titles = {'QB': 'Quarterbacks (QB)', 'RB': 'Running Backs (RB)', 'WR': 'Wide Receivers (WR)', 'TE': 'Tight Ends (TE)', 'K': 'Kickers (K)', 'D/ST': 'Defense / Special Teams (D/ST)'}
    for p_code in pos_list:
        st.write(f"### {titles[p_code]}")
        tbl = build_table(p_code)
        if not tbl.empty: render_html_table(tbl)
        else: st.info(f"No {titles[p_code]} on record.")
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
