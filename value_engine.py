import streamlit as st
import pandas as pd
import numpy as np

DEFAULT_REPLACEMENT = {
    'QB': 16.5,
    'RB': 9.5,
    'WR': 9.5,
    'TE': 6.5,
    'D/ST': 5.5,
    'K': 6.5
}

BENCH_CLOG_PENALTY = 0.50
ROSTER_SPOT_TAX_PER_WK = 1.50

def normalize_box_df(box_df):
    if box_df is None or box_df.empty:
        return pd.DataFrame()
    b = box_df.copy()
    name_c = 'Player_Name' if 'Player_Name' in b.columns else ('Player' if 'Player' in b.columns else None)
    pos_c = 'Position' if 'Position' in b.columns else ('Pos' if 'Pos' in b.columns else None)
    slot_c = 'Slot' if 'Slot' in b.columns else ('Lineup_Slot' if 'Lineup_Slot' in b.columns else None)
    pts_c = 'Actual_Points' if 'Actual_Points' in b.columns else ('Points' if 'Points' in b.columns else None)
    if not all([name_c, pos_c, slot_c, pts_c]):
        return pd.DataFrame()

    b['Szn'] = pd.to_numeric(b['Season'].astype(str).str.replace(r'\.0$', '', regex=True), errors='coerce').fillna(0).astype(int)
    b['Wk'] = pd.to_numeric(b['Week'], errors='coerce').fillna(0).astype(int)
    b['Mgr'] = b['Team_Name'].astype(str).str.strip().replace('1alexyoel15+', 'Matt')
    b['Pl'] = b[name_c].astype(str).str.strip()
    b['Pos'] = b[pos_c].astype(str).str.strip()
    b['Slot_Clean'] = b[slot_c].astype(str).str.strip().str.upper()
    b['Pts'] = pd.to_numeric(b[pts_c], errors='coerce').fillna(0.0)
    b = b[(b['Szn'] >= 2018) & (b['Wk'] >= 1)].copy()
    return b[['Szn', 'Wk', 'Mgr', 'Pl', 'Pos', 'Slot_Clean', 'Pts']]

def compute_weekly_scores(b):
    if b.empty:
        return b, DEFAULT_REPLACEMENT
    starters = b[~b['Slot_Clean'].isin(['BE', 'BENCH', 'IR'])].copy()
    rep_map = {}
    for (szn, pos), grp in starters.groupby(['Szn', 'Pos']):
        if len(grp) >= 5:
            rep_map[(szn, pos)] = float(np.percentile(grp['Pts'], 30))

    def get_rep(r):
        return rep_map.get((int(r['Szn']), str(r['Pos'])), DEFAULT_REPLACEMENT.get(str(r['Pos']), 8.5))

    b = b.copy()
    b['Rep_Base'] = b.apply(get_rep, axis=1)
    b['Is_Start'] = ~b['Slot_Clean'].isin(['BE', 'BENCH', 'IR'])
    b['Is_Bench_Clog'] = (b['Slot_Clean'].isin(['BE', 'BENCH'])) & (b['Pts'] > 0)

    def calc_wk_val(r):
        if r['Is_Start']:
            return float(r['Pts']) - float(r['Rep_Base'])
        elif r['Is_Bench_Clog']:
            return -BENCH_CLOG_PENALTY
        return 0.0

    b['Wk_Val'] = b.apply(calc_wk_val, axis=1)
    return b, rep_map

@st.cache_data(ttl=600)
def compute_draft_value_added(draft_df, box_df):
    b = normalize_box_df(box_df)
    if b.empty or draft_df is None or draft_df.empty:
        return pd.DataFrame()
    b, _ = compute_weekly_scores(b)

    full_szn = b.groupby(['Szn', 'Pl']).agg(
        Total_Starts=('Is_Start', 'sum'),
        Bench_Wks=('Is_Bench_Clog', 'sum'),
        Starter_Pts=('Pts', lambda s: s[b.loc[s.index, 'Is_Start']].sum()),
        Full_Raw_Val=('Wk_Val', 'sum')
    ).reset_index()

    mgr_szn = b.groupby(['Szn', 'Mgr', 'Pl']).agg(
        Mgr_Starts=('Is_Start', 'sum'),
        Mgr_Bench_Wks=('Is_Bench_Clog', 'sum'),
        Mgr_Raw_Val=('Wk_Val', 'sum')
    ).reset_index()

    d = draft_df.copy()
    d = d.merge(full_szn, left_on=['Year', 'Player'], right_on=['Szn', 'Pl'], how='left')
    d = d.merge(mgr_szn, left_on=['Year', 'Team', 'Player'], right_on=['Szn', 'Mgr', 'Pl'], how='left')

    for col in ['Total_Starts', 'Bench_Wks', 'Starter_Pts', 'Full_Raw_Val', 'Mgr_Starts', 'Mgr_Bench_Wks', 'Mgr_Raw_Val']:
        d[col] = d[col].fillna(0.0)

    max_szn_wks = b.groupby('Szn')['Wk'].max().to_dict()
    def get_szn_scale(yr):
        wks = max_szn_wks.get(int(yr), 16)
        return min(1.0, float(wks) / 16.0)

    d['Szn_Scale'] = d['Year'].apply(get_szn_scale)
    d['Expected_Val'] = d.apply(
        lambda r: (145.0 * np.exp(-0.028 * (float(r['Overall Pick']) - 1.0))) * float(r['Szn_Scale']),
        axis=1
    )

    d['Pick_DVA'] = d['Full_Raw_Val'] - d['Expected_Val']
    d['Manager_DVA'] = d['Mgr_Raw_Val'] - d['Expected_Val']
    return d

@st.cache_data(ttl=600)
def compute_waiver_value_added(tx_df, box_df):
    b = normalize_box_df(box_df)
    if b.empty or tx_df is None or tx_df.empty:
        return pd.DataFrame()
    b, _ = compute_weekly_scores(b)

    adds = tx_df[(tx_df['Status'] == 'EXECUTED') & (tx_df['Action'] == 'ADD') & (tx_df['Type'].isin(['WAIVER', 'FREEAGENT']))].copy()
    if adds.empty:
        return pd.DataFrame()

    b_idx = {k: grp.sort_values('Wk') for k, grp in b.groupby(['Szn', 'Mgr', 'Pl'])}
    out_moves = tx_df[(tx_df['Status'] == 'EXECUTED') & (tx_df['Action'].isin(['DROP', 'TRADE']))].copy()
    out_idx = {k: sorted(grp['Week'].tolist()) for k, grp in out_moves.groupby(['Season', 'From_Team', 'Player'])}

    rows = []
    for _, r in adds.iterrows():
        szn = int(r['Season'])
        wk_add = int(r['Week'])
        mgr = str(r['To_Team']).strip()
        pl = str(r['Player']).strip()
        pos = str(r['Position']).strip()
        tx_type = str(r['Type']).strip()
        bid = int(r['Bid_Amount']) if szn >= 2026 and tx_type == 'WAIVER' else 0

        drop_wks = [w for w in out_idx.get((szn, mgr, pl), []) if w > wk_add]
        end_wk = drop_wks[0] if drop_wks else 99

        p_logs = b_idx.get((szn, mgr, pl))
        if p_logs is not None and not p_logs.empty:
            stint = p_logs[(p_logs['Wk'] >= max(1, wk_add)) & (p_logs['Wk'] <= end_wk)]
            starts = int(stint['Is_Start'].sum())
            bench_wks = int(stint['Is_Bench_Clog'].sum())
            start_pts = float(stint[stint['Is_Start']]['Pts'].sum())
            raw_val = float(stint['Wk_Val'].sum())
        else:
            starts, bench_wks, start_pts, raw_val = 0, 0, 0.0, 0.0

        if tx_type == 'FREEAGENT':
            hurdle = 0.0
            acq_lbl = 'FA'
        elif szn >= 2026:
            hurdle = round(0.40 * bid, 2)
            acq_lbl = f'FAAB (${bid})'
        else:
            hurdle = 3.0
            acq_lbl = 'Waiver'

        wva = raw_val - hurdle
        rows.append({
            'Season': szn,
            'Week': wk_add,
            'Manager': mgr,
            'Player': pl,
            'Pos': pos,
            'Acquisition': acq_lbl,
            'Type': tx_type,
            'Bid_Amount': bid,
            'Starts': starts,
            'Bench_Wks': bench_wks,
            'Starter_Pts': round(start_pts, 1),
            'Hurdle': round(hurdle, 1),
            'WVA': round(wva, 2)
        })

    return pd.DataFrame(rows)

@st.cache_data(ttl=600)
def compute_trade_value_added(trades_df, box_df):
    b = normalize_box_df(box_df)
    if b.empty or trades_df is None or trades_df.empty:
        return pd.DataFrame()
    b, _ = compute_weekly_scores(b)

    b_idx = {k: grp for k, grp in b.groupby(['Szn', 'Mgr', 'Pl'])}
    max_wk_map = b.groupby('Szn')['Wk'].max().to_dict()

    def parse_side(side_str):
        items = []
        for part in str(side_str).split(','):
            part = part.strip()
            if '(' in part and part.endswith(')'):
                p_name = part[:part.rfind('(')].strip()
                items.append(p_name)
            elif part:
                items.append(part)
        return items

    rows = []
    for _, r in trades_df.iterrows():
        szn = int(r['Season'])
        wk = int(r['Week'])
        m1 = str(r['Manager 1']).strip()
        m2 = str(r['Manager 2']).strip()
        m1_players = parse_side(r['Manager 1 Receives'])
        m2_players = parse_side(r['Manager 2 Receives'])

        m1_val, m1_starts = 0.0, 0
        for p in m1_players:
            logs = b_idx.get((szn, m1, p))
            if logs is not None:
                post = logs[logs['Wk'] >= wk]
                m1_val += float(post['Wk_Val'].sum())
                m1_starts += int(post['Is_Start'].sum())

        m2_val, m2_starts = 0.0, 0
        for p in m2_players:
            logs = b_idx.get((szn, m2, p))
            if logs is not None:
                post = logs[logs['Wk'] >= wk]
                m2_val += float(post['Wk_Val'].sum())
                m2_starts += int(post['Is_Start'].sum())

        rem_wks = max(1, min(6, max_wk_map.get(szn, 16) - wk + 1))
        diff_players = len(m1_players) - len(m2_players)
        m1_spot_tax = max(0, diff_players) * ROSTER_SPOT_TAX_PER_WK * (rem_wks / 2.0)
        m2_spot_tax = max(0, -diff_players) * ROSTER_SPOT_TAX_PER_WK * (rem_wks / 2.0)

        m1_adj = m1_val - m1_spot_tax
        m2_adj = m2_val - m2_spot_tax
        net_m1 = m1_adj - m2_adj

        if abs(net_m1) < 1.0:
            winner = "Even"
            win_margin = 0.0
        elif net_m1 > 0:
            winner = f"{m1} (+{net_m1:.1f})"
            win_margin = net_m1
        else:
            winner = f"{m2} (+{-net_m1:.1f})"
            win_margin = -net_m1

        rows.append({
            'Season': szn,
            'Week': wk,
            'Manager 1': m1,
            'Manager 1 Receives': r['Manager 1 Receives'],
            'M1_Starts': m1_starts,
            'M1_Val': round(m1_adj, 1),
            'M1_TVA': round(net_m1, 1),
            'Manager 2': m2,
            'Manager 2 Receives': r['Manager 2 Receives'],
            'M2_Starts': m2_starts,
            'M2_Val': round(m2_adj, 1),
            'M2_TVA': round(-net_m1, 1),
            'Trade Winner': winner,
            'Win_Margin': round(win_margin, 2)
        })

    return pd.DataFrame(rows)
  
