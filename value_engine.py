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

ESPN_TEAM_TO_MGR = {
    'austin': 'Austin', 'austin cunney': 'Austin', 'comfort king': 'Austin',
    'tanking for 2020': 'Austin', 'no problem noah!': 'Austin', 'the dark knight rises': 'Austin',
    'brett': 'Brett', 'brett gardner': 'Brett', 'gg ff': 'Brett', 'oopsies': 'Brett', 'b💣💣mdoom': 'Brett',
    'cameron': 'Cameron', 'cameron crabbe': 'Cameron', 'team cam': 'Cameron', 'cam': 'Cameron',
    'cav': 'Cav', 'cav meininger': 'Cav', 'jim beans jeans': 'Cav', "rex ryan's tasty toes": 'Cav',
    'king of queens': 'Cav', 'for whom le bell tolls': 'Cav',
    'david': 'David', 'david klotz': 'David', 'purple nurples for you ii': 'David',
    'purple nurples for you iii': 'David', 'great group of guys': 'David',
    'lousy rotten group of guys': 'David', 'the monarch butterflies': 'David',
    'the monarch bootyflies': 'David', 'joe cranberry + the berry boys': 'David',
    'put ya hands up fbi!': 'David', 'no pasa nadaaaa': 'David',
    'eli': 'Eli', 'eli  jacobowitz': 'Eli', 'eli jacobowitz': 'Eli', 'snick mcglick': 'Eli',
    'michael thomas is trash': 'Eli', 'team eli': 'Eli',
    'jack': 'Jack', 'jack southard': 'Jack', 'earl tackys khakis': 'Jack',
    'cav eats little pieces of shit': 'Jack',
    'keith': 'Keith', 'keith  bivas': 'Keith', 'keith bivas': 'Keith', 'stoooooooopittt .': 'Keith',
    'this is how i  win': 'Keith', "fleckin '": 'Keith', 'kevin moskowitz': 'Keith',
    'guiteau gang': 'Keith', 'the pancake house': 'Keith', 'team keith': 'Keith',
    'lukas': 'Lukas', 'lukas repetti': 'Lukas', 'chief shmeef': 'Lukas',
    'ronaiah tuiasosopo': 'Lukas', 'doctor shots': 'Lukas',
    'matt': 'Matt', 'matthew berube': 'Matt', 'berube ;)': 'Matt', '1alexyoel15+': 'Matt',
    '1alexyoel15+ 1alexyoel15+': 'Matt',
    'max': 'Max', 'max sackett': 'Max', 'ligma fucking nuts': 'Max', 'russel wilsuckmydick': 'Max',
    'noah': 'Noah', 'noah jacobowitz': 'Noah', 'snickersbotz mcgleezaks': 'Noah',
    'outcoached and flecked': 'Noah', 'thank you austin!': 'Noah',
    'sean': 'Sean', 'sean nicholson': 'Sean', 'sean morris': 'Sean', 'who but': 'Sean',
    'taylor park boys': 'Sean', 'under  repair': 'Sean', 'medical tent': 'Sean',
    'brooklyn bandits': 'Sean', 'harlem havoc': 'Sean', "sean's team": 'Sean',
    'lemme get a graham': 'Sean'
}

def map_team_to_mgr(val):
    s = str(val).strip()
    low = s.lower()
    if low in ESPN_TEAM_TO_MGR:
        return ESPN_TEAM_TO_MGR[low]
    for k, mgr in ESPN_TEAM_TO_MGR.items():
        if len(k) > 4 and k in low:
            return mgr
    return s

def normalize_box_df(box_df):
    if box_df is None or box_df.empty:
        return pd.DataFrame()
    b = box_df.copy()
    name_c = 'Player_Name' if 'Player_Name' in b.columns else ('Player' if 'Player' in b.columns else None)
    pos_c = 'Position' if 'Position' in b.columns else ('Pos' if 'Pos' in b.columns else None)
    slot_c = 'Slot' if 'Slot' in b.columns else ('Lineup_Slot' if 'Lineup_Slot' in b.columns else None)
    pts_c = 'Actual_Points' if 'Actual_Points' in b.columns else ('Points' if 'Points' in b.columns else None)
    tm_c = 'Manager' if 'Manager' in b.columns else ('Team_Name' if 'Team_Name' in b.columns else None)
    if not all([name_c, pos_c, slot_c, pts_c, tm_c]):
        return pd.DataFrame()

    b['Szn'] = pd.to_numeric(b['Season'].astype(str).str.replace(r'\.0$', '', regex=True), errors='coerce').fillna(0).astype(int)
    b['Wk'] = pd.to_numeric(b['Week'], errors='coerce').fillna(0).astype(int)
    b['Mgr'] = b[tm_c].apply(map_team_to_mgr)
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
    b['Is_Active_Gm'] = (b['Pts'] != 0) | b['Is_Start']
    b['Is_Bench_Clog'] = (b['Slot_Clean'].isin(['BE', 'BENCH'])) & (b['Pts'] > 0)

    def calc_wk_val(r):
        if r['Is_Start']:
            return float(r['Pts']) - float(r['Rep_Base'])
        elif r['Is_Bench_Clog']:
            return -BENCH_CLOG_PENALTY
        return 0.0

    b['Wk_Val'] = b.apply(calc_wk_val, axis=1)
    b['Wk_Pos_Rk'] = b.groupby(['Szn', 'Wk', 'Pos'])['Pts'].rank(ascending=False, method='min')
    return b, rep_map

@st.cache_data(ttl=600)
def parse_trade_side_players(side_str):
    items = []
    for part in str(side_str).split(','):
        part = part.strip()
        if '(' in part and part.endswith(')'):
            items.append(part[:part.rfind('(')].strip())
        elif part:
            items.append(part)
    return items

@st.cache_data(ttl=600)
def compute_draft_value_added(draft_df, box_df, trades_df=None):
    b = normalize_box_df(box_df)
    if b.empty or draft_df is None or draft_df.empty:
        return pd.DataFrame()
    b, _ = compute_weekly_scores(b)

    b_dedup = b.sort_values('Is_Start', ascending=False).drop_duplicates(subset=['Szn', 'Wk', 'Pl'])

    pos_totals = b_dedup.groupby(['Szn', 'Pos', 'Pl']).agg(
        Szn_Total_Pts=('Pts', 'sum'),
        Active_Gms=('Is_Active_Gm', 'sum')
    ).reset_index()
    pos_totals['Pos_Rk_Int'] = pos_totals.groupby(['Szn', 'Pos'])['Szn_Total_Pts'].rank(ascending=False, method='min').astype(int)
    pos_totals['Pos_Rank'] = np.where(pos_totals['Szn_Total_Pts'] > 0, pos_totals['Pos'] + pos_totals['Pos_Rk_Int'].astype(str), '-')

    full_szn = b.groupby(['Szn', 'Pl']).agg(
        Total_Starts=('Is_Start', 'sum'),
        Total_Roster_Wks=('Wk', 'count'),
        Bench_Wks=('Is_Bench_Clog', 'sum'),
        Starter_Pts=('Pts', lambda s: s[b.loc[s.index, 'Is_Start']].sum()),
        Full_Raw_Val=('Wk_Val', 'sum')
    ).reset_index()
    full_szn['Pts_Per_Start'] = np.where(full_szn['Total_Starts'] > 0, full_szn['Starter_Pts'] / full_szn['Total_Starts'], 0.0)

    mgr_szn = b.groupby(['Szn', 'Mgr', 'Pl']).agg(
        Mgr_Starts=('Is_Start', 'sum'),
        Mgr_Roster_Wks=('Wk', 'count'),
        Mgr_Bench_Wks=('Is_Bench_Clog', 'sum'),
        Mgr_Starter_Pts=('Pts', lambda s: s[b.loc[s.index, 'Is_Start']].sum()),
        Mgr_Raw_Val=('Wk_Val', 'sum')
    ).reset_index()
    mgr_szn['Mgr_Pts_Per_Start'] = np.where(mgr_szn['Mgr_Starts'] > 0, mgr_szn['Mgr_Starter_Pts'] / mgr_szn['Mgr_Starts'], 0.0)

    d = draft_df.copy()
    d['Team'] = d['Team'].apply(map_team_to_mgr)
    d = d.merge(full_szn, left_on=['Year', 'Player'], right_on=['Szn', 'Pl'], how='left')
    d = d.merge(pos_totals[['Szn', 'Pl', 'Pos_Rank']], left_on=['Year', 'Player'], right_on=['Szn', 'Pl'], how='left')
    d = d.merge(mgr_szn, left_on=['Year', 'Team', 'Player'], right_on=['Szn', 'Mgr', 'Pl'], how='left')

    for col in [
        'Total_Starts', 'Total_Roster_Wks', 'Bench_Wks', 'Starter_Pts', 'Full_Raw_Val',
        'Pts_Per_Start', 'Mgr_Starts', 'Mgr_Roster_Wks', 'Mgr_Bench_Wks', 'Mgr_Starter_Pts',
        'Mgr_Raw_Val', 'Mgr_Pts_Per_Start'
    ]:
        d[col] = d[col].fillna(0.0)
    d['Pos_Rank'] = d['Pos_Rank'].fillna('-')

    max_szn_wks = b.groupby('Szn')['Wk'].max().to_dict()
    def get_szn_scale(yr):
        wks = max_szn_wks.get(int(yr), 16)
        return min(1.0, float(wks) / 16.0)

    d['Szn_Scale'] = d['Year'].apply(get_szn_scale)
    d['Expected_Val'] = d.apply(
        lambda r: (145.0 * np.exp(-0.028 * (float(r['Overall Pick']) - 1.0))) * float(r['Szn_Scale']),
        axis=1
    )

    # Allocate post-trade value of acquired players back to the traded draft pick
    trade_return_map = {}
    if trades_df is not None and not trades_df.empty:
        b_idx = {k: grp for k, grp in b.groupby(['Szn', 'Mgr', 'Pl'])}
        pick_weight_lookup = {
            (int(r['Year']), str(r['Player']).strip()): max(5.0, float(r['Expected_Val']))
            for _, r in d.iterrows()
        }

        t_sorted = trades_df.sort_values(['Season', 'Week'], ascending=[True, True])
        for _, tr in t_sorted.iterrows():
            szn = int(tr['Season'])
            wk = int(tr['Week'])
            m1 = map_team_to_mgr(tr['Manager 1'])
            m2 = map_team_to_mgr(tr['Manager 2'])
            m1_gets = parse_trade_side_players(tr['Manager 1 Receives'])
            m2_gets = parse_trade_side_players(tr['Manager 2 Receives'])

            m1_in_val = sum(
                float(b_idx[(szn, m1, p)][b_idx[(szn, m1, p)]['Wk'] >= wk]['Wk_Val'].sum())
                for p in m1_gets if (szn, m1, p) in b_idx
            )
            m2_in_val = sum(
                float(b_idx[(szn, m2, p)][b_idx[(szn, m2, p)]['Wk'] >= wk]['Wk_Val'].sum())
                for p in m2_gets if (szn, m2, p) in b_idx
            )

            rem_wks = max(1, min(6, max_szn_wks.get(szn, 16) - wk + 1))
            diff_p = len(m1_gets) - len(m2_gets)
            m1_in_adj = m1_in_val - (max(0, diff_p) * ROSTER_SPOT_TAX_PER_WK * (rem_wks / 2.0))
            m2_in_adj = m2_in_val - (max(0, -diff_p) * ROSTER_SPOT_TAX_PER_WK * (rem_wks / 2.0))

            if m2_gets:
                w_m1 = [pick_weight_lookup.get((szn, p), 10.0) for p in m2_gets]
                tot_w1 = sum(w_m1)
                for p, w in zip(m2_gets, w_m1):
                    if (szn, m1, p) not in trade_return_map:
                        trade_return_map[(szn, m1, p)] = m1_in_adj * (w / tot_w1)

            if m1_gets:
                w_m2 = [pick_weight_lookup.get((szn, p), 10.0) for p in m1_gets]
                tot_w2 = sum(w_m2)
                for p, w in zip(m1_gets, w_m2):
                    if (szn, m2, p) not in trade_return_map:
                        trade_return_map[(szn, m2, p)] = m2_in_adj * (w / tot_w2)

    def calc_trade_adj_dva(r):
        key = (int(r['Year']), str(r['Team']).strip(), str(r['Player']).strip())
        if key in trade_return_map:
            return float(r['Mgr_Raw_Val']) + float(trade_return_map[key]) - float(r['Expected_Val'])
        return float(r['Mgr_Raw_Val']) - float(r['Expected_Val'])

    d['Pick_DVA'] = d['Full_Raw_Val'] - d['Expected_Val']
    d['Trade_Adj_DVA'] = d.apply(calc_trade_adj_dva, axis=1)
    d['Manager_DVA'] = d['Trade_Adj_DVA']
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

    b_dedup = b.sort_values('Is_Start', ascending=False).drop_duplicates(subset=['Szn', 'Wk', 'Pl'])
    szn_pos_rk = b_dedup.groupby(['Szn', 'Pos', 'Pl'])['Pts'].sum().reset_index()
    szn_pos_rk['Rk'] = szn_pos_rk.groupby(['Szn', 'Pos'])['Pts'].rank(ascending=False, method='min').astype(int)
    pos_rk_map = {(int(r['Szn']), str(r['Pl'])): f"{r['Pos']}{int(r['Rk'])}" for _, r in szn_pos_rk[szn_pos_rk['Pts'] > 0].iterrows()}

    b_idx = {k: grp.sort_values('Wk') for k, grp in b.groupby(['Szn', 'Mgr', 'Pl'])}
    out_moves = tx_df[(tx_df['Status'] == 'EXECUTED') & (tx_df['Action'].isin(['DROP', 'TRADE']))].copy()
    out_idx = {k: sorted(grp['Week'].tolist()) for k, grp in out_moves.groupby(['Season', 'From_Team', 'Player'])}

    rows = []
    for _, r in adds.iterrows():
        szn = int(r['Season'])
        wk_add = int(r['Week'])
        mgr = map_team_to_mgr(r['To_Team'])
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
            pts_per_start = (start_pts / starts) if starts > 0 else 0.0
            raw_val = float(stint['Wk_Val'].sum())
            if starts > 0:
                avg_wk_rk = int(round(stint[stint['Is_Start']]['Wk_Pos_Rk'].mean()))
                pos_rk_str = f"{pos}{avg_wk_rk}"
            else:
                pos_rk_str = pos_rk_map.get((szn, pl), '-')
        else:
            starts, bench_wks, start_pts, pts_per_start, raw_val, pos_rk_str = 0, 0, 0.0, 0.0, 0.0, '-'

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
            'Pts_Per_Start': round(pts_per_start, 1),
            'Pos_Rank': pos_rk_str,
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
                p_pos = part[part.rfind('(')+1:-1].strip()
                items.append((p_name, p_pos))
            elif part:
                items.append((part, ''))
        return items

    def eval_side(szn, wk, mgr, player_tuples):
        tot_val, tot_starts, tot_start_pts = 0.0, 0, 0.0
        enriched_labels = []
        for p, pos in player_tuples:
            logs = b_idx.get((szn, mgr, p))
            if logs is not None and not logs.empty:
                post = logs[logs['Wk'] >= wk]
                st_rows = post[post['Is_Start']]
                starts = len(st_rows)
                s_pts = float(st_rows['Pts'].sum())
                val = float(post['Wk_Val'].sum())
                tot_val += val
                tot_starts += starts
                tot_start_pts += s_pts
                if starts > 0:
                    pps = s_pts / starts
                    avg_rk = int(round(st_rows['Wk_Pos_Rk'].mean()))
                    rk_lbl = f"{pos or post['Pos'].iloc[0]}{avg_rk}"
                    enriched_labels.append(f"{p} ({starts} GS, {pps:.1f} Pts/Start, {rk_lbl})")
                else:
                    enriched_labels.append(f"{p} (0 GS)")
            else:
                enriched_labels.append(f"{p} ({pos})" if pos else p)
        side_pps = (tot_start_pts / tot_starts) if tot_starts > 0 else 0.0
        return tot_val, tot_starts, side_pps, ", ".join(enriched_labels)

    rows = []
    for _, r in trades_df.iterrows():
        szn = int(r['Season'])
        wk = int(r['Week'])
        m1 = map_team_to_mgr(r['Manager 1'])
        m2 = map_team_to_mgr(r['Manager 2'])
        m1_tuples = parse_side(r['Manager 1 Receives'])
        m2_tuples = parse_side(r['Manager 2 Receives'])

        m1_val, m1_starts, m1_pps, m1_detail = eval_side(szn, wk, m1, m1_tuples)
        m2_val, m2_starts, m2_pps, m2_detail = eval_side(szn, wk, m2, m2_tuples)

        rem_wks = max(1, min(6, max_wk_map.get(szn, 16) - wk + 1))
        diff_players = len(m1_tuples) - len(m2_tuples)
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
            'Manager 1 Receives': m1_detail,
            'M1_Starts': m1_starts,
            'M1_PPS': round(m1_pps, 1),
            'M1_Val': round(m1_adj, 1),
            'M1_TVA': round(net_m1, 1),
            'Manager 2': m2,
            'Manager 2 Receives': m2_detail,
            'M2_Starts': m2_starts,
            'M2_PPS': round(m2_pps, 1),
            'M2_Val': round(m2_adj, 1),
            'M2_TVA': round(-net_m1, 1),
            'Trade Winner': winner,
            'Win_Margin': round(win_margin, 2)
        })

    return pd.DataFrame(rows)
    
