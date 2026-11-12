import importlib
import streamlit as st
import pandas as pd
import value_engine
importlib.reload(value_engine)

NFL_DRAFT_NORM = {
    'ARI': 'ARI', 'Ari': 'ARI', 'ATL': 'ATL', 'Atl': 'ATL',
    'BAL': 'BAL', 'Bal': 'BAL', 'BUF': 'BUF', 'Buf': 'BUF',
    'CAR': 'CAR', 'Car': 'CAR', 'CHI': 'CHI', 'Chi': 'CHI',
    'CIN': 'CIN', 'Cin': 'CIN', 'CLE': 'CLE', 'Cle': 'CLE',
    'DAL': 'DAL', 'Dal': 'DAL', 'DEN': 'DEN', 'Den': 'DEN',
    'DET': 'DET', 'Det': 'DET', 'GBP': 'GB',  'HOU': 'HOU',
    'Hou': 'HOU', 'IND': 'IND', 'Ind': 'IND', 'JAX': 'JAX',
    'Jax': 'JAX', 'KCC': 'KC',  'LAC': 'LAC', 'LAR': 'LAR',
    'LVR': 'LV',  'MIA': 'MIA', 'Mia': 'MIA', 'MIN': 'MIN',
    'Min': 'MIN', 'NEP': 'NE',  'NOL': 'NO',  'NYG': 'NYG',
    'NYJ': 'NYJ', 'PHI': 'PHI', 'Phi': 'PHI', 'PIT': 'PIT',
    'Pit': 'PIT', 'SEA': 'SEA', 'Sea': 'SEA', 'SF9': 'SF',
    'TBB': 'TB',  'TEN': 'TEN', 'Ten': 'TEN', 'WSH': 'WAS',
    'Wsh': 'WAS', 'FrA': 'FA',  'WAS': 'WAS', 'LV': 'LV',
    'GB': 'GB',   'KC': 'KC',   'NE': 'NE',   'NO': 'NO',
    'SF': 'SF',   'TB': 'TB'
}

DRAFT_DAY_OVERRIDES = {
    (2023, 'Austin Ekeler'): 'LAC',
    (2023, 'Saquon Barkley'): 'NYG',
    (2023, 'Josh Jacobs'): 'LV',
    (2023, 'Tony Pollard'): 'DAL',
    (2023, 'Derrick Henry'): 'TEN',
    (2023, 'Joe Mixon'): 'CIN',
    (2023, 'Calvin Ridley'): 'JAX',
    (2023, 'Keenan Allen'): 'LAC',
    (2023, 'Aaron Jones'): 'GB',
    (2023, 'Justin Fields'): 'CHI',
    (2023, 'Alexander Mattison'): 'MIN',
    (2023, 'Jerry Jeudy'): 'DEN',
    (2023, 'Mike Williams'): 'LAC',
    (2023, 'Cam Akers'): 'LAR',
    (2023, "D'Andre Swift"): 'PHI',
    (2023, 'Diontae Johnson'): 'PIT',
    (2023, 'Dalvin Cook'): 'NYJ',
    (2023, 'Gabriel Davis'): 'BUF',
    (2023, 'Hollywood Brown'): 'ARI',
    (2023, 'Antonio Gibson'): 'WAS',
    (2023, 'Van Jefferson'): 'LAR',
    (2023, 'Devin Singletary'): 'HOU',
    (2023, 'Darnell Mooney'): 'CHI',
    (2023, 'Mecole Hardman'): 'NYJ',
    (2023, 'Chase Claypool'): 'CHI',
    (2023, 'Kirk Cousins'): 'MIN',
    (2023, 'Curtis Samuel'): 'WAS',
    (2023, 'Brandon McManus'): 'JAX',
    (2022, 'Christian McCaffrey'): 'CAR',
    (2022, 'T.J. Hockenson'): 'DET',
    (2022, 'Chase Claypool'): 'PIT',
    (2022, 'Jeff Wilson Jr.'): 'SF',
    (2022, 'Nyheim Hines'): 'IND',
    (2021, 'Odell Beckham Jr.'): 'CLE',
    (2021, 'Zach Ertz'): 'PHI',
    (2021, 'Mark Ingram II'): 'HOU',
    (2020, 'Matthew Stafford'): 'DET',
    (2020, "Le'Veon Bell"): 'NYJ',
    (2025, 'Brian Robinson Jr.'): 'WAS',
    (2025, 'Davante Adams'): 'NYJ',
    (2025, 'Amari Cooper'): 'BUF',
    (2025, 'Stefon Diggs'): 'HOU',
    (2026, 'Brian Robinson Jr.'): 'WAS',
    (2026, 'Adonai Mitchell'): 'IND',
    (2026, 'A.J. Brown'): 'PHI',
    (2026, 'Stefon Diggs'): 'NE',
    (2026, 'Kenneth Walker III'): 'SEA',
    (2026, 'Travis Etienne Jr.'): 'JAX',
}

POS_COLORS = {
    'RB': ('#cfe2f3', '#0b5394'),
    'WR': ('#d9ead3', '#274e13'),
    'QB': ('#f4cccc', '#783f04'),
    'TE': ('#fce5cd', '#b45f06'),
    'D/ST': ('#d9d2e9', '#351c75'),
    'K': ('#efefef', '#444444')
}

def render_table(df, left_align_cols=None, highlight_fn=None):
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
def load_draft_data(box_df=None):
    try:
        df = pd.read_excel("Draft History.xlsx", sheet_name="Consolidated", header=1, engine="openpyxl")
    except Exception:
        return pd.DataFrame()

    df = df.dropna(subset=['Year', 'Player']).copy()
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce').astype(int)
    df['Round'] = pd.to_numeric(df['Round'], errors='coerce').astype(int)
    df['Overall Pick'] = pd.to_numeric(df['Overall Pick'], errors='coerce').astype(int)
    df['Round Pick'] = pd.to_numeric(df['Round Pick'], errors='coerce').astype(int)
    df['Team'] = df['Team'].astype(str).str.strip()
    df['Player'] = df['Player'].astype(str).str.strip()
    df['Position'] = df['Position'].astype(str).str.strip()
    df['NFL_Raw'] = df['NFL Team'].astype(str).str.strip()
    df['NFL Team'] = df['NFL_Raw'].map(NFL_DRAFT_NORM).fillna(df['NFL_Raw'].str.upper())

    wk1_lookup = {}
    if box_df is not None and not box_df.empty:
        name_c = 'Player_Name' if 'Player_Name' in box_df.columns else 'Player'
        nfl_c = next((c for c in ['Pro_Team', 'NFL_Team', 'ProTeam', 'NFL', 'Team_Abbrev', 'Team_Abbr'] if c in box_df.columns), None)
        if nfl_c and name_c in box_df.columns:
            b_sub = box_df.copy()
            b_sub['Szn_Int'] = pd.to_numeric(b_sub['Season'].astype(str).str.replace(r'\.0$', '', regex=True), errors='coerce')
            b_sub['Wk_Int'] = pd.to_numeric(b_sub['Week'], errors='coerce')
            b_wk1 = b_sub[b_sub['Wk_Int'] == 1].dropna(subset=['Szn_Int', name_c, nfl_c])
            for _, r in b_wk1.iterrows():
                raw_t = str(r[nfl_c]).strip()
                norm_t = NFL_DRAFT_NORM.get(raw_t, raw_t.upper())
                if norm_t and norm_t not in ['FA', 'NONE', '-', 'NAN']:
                    wk1_lookup[(int(r['Szn_Int']), str(r[name_c]).strip())] = norm_t

    def resolve_nfl(row):
        key = (int(row['Year']), str(row['Player']))
        if key in DRAFT_DAY_OVERRIDES:
            return DRAFT_DAY_OVERRIDES[key]
        if row['Position'] != 'D/ST' and key in wk1_lookup:
            return wk1_lookup[key]
        return row['NFL Team']

    df['NFL Team'] = df.apply(resolve_nfl, axis=1)
    df['Pick_Label'] = df.apply(lambda r: f"{int(r['Round'])}.{int(r['Round Pick']):02d} (#{int(r['Overall Pick'])})", axis=1)
    return df

def fmt_signed(val):
    if pd.isna(val):
        return "-"
    return f"+{val:.1f}" if val > 0 else f"{val:.1f}"

def render(box_df=None):
    if box_df is None or box_df.empty:
        try:
            import app
            box_df = app.load_box_scores()
        except Exception:
            pass

    df = load_draft_data(box_df)
    if df.empty:
        st.warning("Could not load 'Draft History.xlsx' (sheet: 'Consolidated'). Make sure it is uploaded to the repository root.")
        return

    trades_df = pd.DataFrame()
    try:
        import transactions_tab
        importlib.reload(transactions_tab)
        _, trades_df = transactions_tab.load_transactions_data(box_df)
    except Exception:
        pass

    try:
        dva_df = value_engine.compute_draft_value_added(df, box_df, trades_df)
    except TypeError:
        dva_df = value_engine.compute_draft_value_added(df, box_df)

    if not dva_df.empty and 'Trade_Adj_DVA' not in dva_df.columns:
        dva_df['Trade_Adj_DVA'] = dva_df['Manager_DVA'] if 'Manager_DVA' in dva_df.columns else dva_df['Pick_DVA']

    draft_view = st.radio(
        "Draft View:",
        [
            "Yearly Draft Board",
            "Draft Value Added (DVA)",
            "Player Draft Ledger",
            "Manager Draft Room",
            "Draft Records & Loyalty"
        ],
        horizontal=True,
        key="draft_sub_view_v6"
    )
    st.write("---")

    years_avail = sorted(df['Year'].unique().tolist(), reverse=True)
    managers_avail = sorted(df['Team'].unique().tolist())

    if draft_view == "Yearly Draft Board":
        c1, c2 = st.columns([1.5, 4])
        with c1:
            sel_yr = st.selectbox("Select Draft Year:", years_avail, key="db_yr")
        with c2:
            st.markdown(
                "<div style='margin-top: 28px; font-size: 13px;'>"
                "<span style='background:#cfe2f3; color:#0b5394; padding:3px 8px; border-radius:4px; font-weight:600; margin-right:6px;'>RB</span>"
                "<span style='background:#d9ead3; color:#274e13; padding:3px 8px; border-radius:4px; font-weight:600; margin-right:6px;'>WR</span>"
                "<span style='background:#f4cccc; color:#783f04; padding:3px 8px; border-radius:4px; font-weight:600; margin-right:6px;'>QB</span>"
                "<span style='background:#fce5cd; color:#b45f06; padding:3px 8px; border-radius:4px; font-weight:600; margin-right:6px;'>TE</span>"
                "<span style='background:#d9d2e9; color:#351c75; padding:3px 8px; border-radius:4px; font-weight:600; margin-right:6px;'>D/ST</span>"
                "<span style='background:#efefef; color:#444444; padding:3px 8px; border-radius:4px; font-weight:600;'>K</span>"
                "</div>",
                unsafe_allow_html=True
            )

        yr_df = df[df['Year'] == int(sel_yr)].copy()
        r1 = yr_df[yr_df['Round'] == 1].sort_values('Round Pick')
        draft_order = r1['Team'].tolist()
        max_round = int(yr_df['Round'].max())

        lookup = {}
        for _, r in yr_df.iterrows():
            lookup[(int(r['Round']), str(r['Team']))] = r

        th_style = "border: 1px solid #ccc; background-color: #f8f9fa; padding: 6px 4px; font-size: 13px; font-weight: 700; text-align: center;"
        header_cells = f'<th style="{th_style} width: 45px;">Rd</th>'
        for idx, tm in enumerate(draft_order):
            header_cells += f'<th style="{th_style}">{idx+1}. {tm}</th>'

        rows_html = []
        for r_num in range(1, max_round + 1):
            cells = f'<td style="border: 1px solid #ccc; background-color: #f8f9fa; font-weight: 700; font-size: 13px; text-align: center;">{r_num}</td>'
            for tm in draft_order:
                pick_row = lookup.get((r_num, tm))
                if pick_row is not None:
                    pos = str(pick_row['Position'])
                    bg, fg = POS_COLORS.get(pos, ('#ffffff', '#111111'))
                    p_name = str(pick_row['Player'])
                    nfl = str(pick_row['NFL Team'])
                    ov = int(pick_row['Overall Pick'])
                    rp = int(pick_row['Round Pick'])
                    arrow = "→" if r_num % 2 == 1 else "←"
                    cells += (
                        f'<td style="border: 1px solid #ccc; background-color: {bg}; color: {fg}; padding: 5px 6px; text-align: left; vertical-align: top; min-width: 115px;">'
                        f'<div style="font-size: 10px; opacity: 0.75; display: flex; justify-content: space-between;">'
                        f'<span>{r_num}.{rp:02d} ({arrow})</span><span>#{ov}</span></div>'
                        f'<div style="font-weight: 700; font-size: 12.5px; line-height: 1.2; margin: 2px 0;">{p_name}</div>'
                        f'<div style="font-size: 11px; font-weight: 600;">{pos} &bull; {nfl}</div>'
                        f'</td>'
                    )
                else:
                    cells += '<td style="border: 1px solid #ccc; background-color: #fff;">-</td>'
            rows_html.append(f'<tr>{cells}</tr>')

        board_html = (
            '<div style="overflow-x: auto; margin-top: 10px;">'
            f'<table style="width: 100%; border-collapse: collapse;"><thead><tr>{header_cells}</tr></thead>'
            f'<tbody>{"".join(rows_html)}</tbody></table></div>'
        )
        st.markdown(board_html, unsafe_allow_html=True)

    elif draft_view == "Draft Value Added (DVA)":
        st.caption(
            "**Pick DVA** grades the draft pick across the full season regardless of who owned the player later. "
            "**Trade-Adj DVA** grades the full-season return realized by the drafting manager (pre-trade starts + allocated post-trade value of players acquired in return, minus the pick's slot hurdle)."
        )
        if dva_df.empty:
            st.info("Box score data is required to compute Draft Value Added.")
            return

        dva_mode = st.radio(
            "Select DVA Leaderboard:",
            [
                "Biggest Draft Steals (Top Pick DVA)",
                "Biggest Draft Busts (Lowest Pick DVA)",
                "Best Trade-Adjusted Draft Picks (Top Trade-Adj DVA)",
                "Manager Draft Value Leaderboard"
            ],
            horizontal=True,
            key="dva_mode_sel_v6"
        )

        c1, c2, c3 = st.columns(3)
        sel_yr = c1.selectbox("Season:", ["All-Time (2018–2026)"] + [str(y) for y in years_avail], key="dva_yr")
        sel_pos = c2.selectbox("Position:", ["Skill Players (QB/RB/WR/TE)", "All Positions", "QB", "RB", "WR", "TE", "D/ST", "K"], key="dva_pos")
        sel_mgr = c3.selectbox("Manager:", ["All Managers"] + managers_avail, key="dva_mgr")

        sub = dva_df.copy()
        if not sel_yr.startswith("All-Time"):
            sub = sub[sub['Year'] == int(sel_yr)]
        if sel_pos == "Skill Players (QB/RB/WR/TE)":
            sub = sub[~sub['Position'].isin(['D/ST', 'K'])]
        elif sel_pos != "All Positions":
            sub = sub[sub['Position'] == sel_pos]
        if sel_mgr != "All Managers":
            sub = sub[sub['Team'] == sel_mgr]

        if dva_mode in [
            "Biggest Draft Steals (Top Pick DVA)",
            "Biggest Draft Busts (Lowest Pick DVA)",
            "Best Trade-Adjusted Draft Picks (Top Trade-Adj DVA)"
        ]:
            sort_col = 'Trade_Adj_DVA' if "Trade-Adjusted" in dva_mode else 'Pick_DVA'
            asc = (dva_mode == "Biggest Draft Busts (Lowest Pick DVA)")
            ranked = sub.sort_values(sort_col, ascending=asc).head(30).reset_index(drop=True)
            ranked['Rank'] = ranked.index + 1
            ranked['Starts'] = ranked['Total_Starts'].astype(int)
            ranked['Pts / Start'] = ranked['Pts_Per_Start'].apply(lambda x: f"{x:.1f}")
            ranked['Slot Hurdle'] = ranked['Expected_Val'].apply(lambda x: f"{x:.1f}")
            ranked['Pick DVA'] = ranked['Pick_DVA'].apply(fmt_signed)
            ranked['Trade-Adj DVA'] = ranked['Trade_Adj_DVA'].apply(fmt_signed)
            disp = ranked[['Rank', 'Year', 'Round', 'Overall Pick', 'Team', 'Player', 'Position', 'Starts', 'Pts / Start', 'Pos_Rank', 'Slot Hurdle', 'Pick DVA', 'Trade-Adj DVA']].rename(
                columns={'Overall Pick': 'Pick #', 'Team': 'Drafted By', 'Position': 'Pos', 'Pos_Rank': 'Pos Rank'}
            )
            render_table(disp, left_align_cols=['Player'])

        else:
            mgr_rows = []
            for mgr in managers_avail:
                m_sub = sub[sub['Team'] == mgr]
                if m_sub.empty:
                    continue
                tot_pick_dva = m_sub['Pick_DVA'].sum()
                tot_tr_dva = m_sub['Trade_Adj_DVA'].sum()
                avg_pick_dva = m_sub['Pick_DVA'].mean()
                hit_rate = (m_sub['Pick_DVA'] > 0).mean() * 100.0
                best_row = m_sub.loc[m_sub['Pick_DVA'].idxmax()]
                worst_row = m_sub.loc[m_sub['Pick_DVA'].idxmin()]
                mgr_rows.append({
                    'Manager': mgr,
                    'Picks': len(m_sub),
                    'Pick_DVA_Num': tot_pick_dva,
                    'Total Pick DVA': fmt_signed(tot_pick_dva),
                    'Total Trade-Adj DVA': fmt_signed(tot_tr_dva),
                    'Avg Pick DVA': fmt_signed(avg_pick_dva),
                    'Hit Rate (>0 DVA)': f"{hit_rate:.1f}%",
                    'Best Pick': f"{best_row['Player']} ({int(best_row['Year'])} Rd {int(best_row['Round'])}, {fmt_signed(best_row['Pick_DVA'])})",
                    'Worst Bust': f"{worst_row['Player']} ({int(worst_row['Year'])} Rd {int(worst_row['Round'])}, {fmt_signed(worst_row['Pick_DVA'])})"
                })
            m_df = pd.DataFrame(mgr_rows).sort_values('Pick_DVA_Num', ascending=False).reset_index(drop=True)
            m_df['Rank'] = m_df.index + 1
            cols = ['Rank', 'Manager', 'Picks', 'Total Pick DVA', 'Total Trade-Adj DVA', 'Avg Pick DVA', 'Hit Rate (>0 DVA)', 'Best Pick', 'Worst Bust']
            render_table(m_df[cols], left_align_cols=['Best Pick', 'Worst Bust'])

  elif draft_view == "Player Draft Ledger":
        b_norm = value_engine.normalize_box_df(box_df)
        b_scored, _ = value_engine.compute_weekly_scores(b_norm)

        tx_df = pd.DataFrame()
        try:
            import transactions_tab
            tx_df, trades_df = transactions_tab.load_transactions_data(box_df)
        except Exception:
            pass

        draft_players = set(df['Player'].dropna().unique()) if not df.empty else set()
        box_players = set(b_scored['Pl'].dropna().unique()) if not b_scored.empty else set()
        tx_players = set(tx_df['Player'].dropna().unique()) if not tx_df.empty else set()
        all_players = sorted([p for p in (draft_players | box_players | tx_players) if p and p != '(Redacted / Empty)'])

        default_idx = all_players.index("Christian McCaffrey") if "Christian McCaffrey" in all_players else 0
        sel_player = st.selectbox("Search / Select Player (All-Time DFFL Database):", all_players, index=default_idx, key="dl_player_full")

        p_draft = (dva_df[dva_df['Player'] == sel_player] if not dva_df.empty else df[df['Player'] == sel_player]).sort_values('Year', ascending=False).copy()
        p_box = b_scored[b_scored['Pl'] == sel_player].copy() if not b_scored.empty else pd.DataFrame()
        p_tx = tx_df[(tx_df['Player'] == sel_player) & (tx_df['Status'] == 'EXECUTED') & (tx_df['Action'].isin(['ADD', 'DROP', 'TRADE']))].copy() if not tx_df.empty else pd.DataFrame()
        p_trades = trades_df[
            trades_df['Manager 1 Receives'].astype(str).str.contains(sel_player, regex=False, na=False) |
            trades_df['Manager 2 Receives'].astype(str).str.contains(sel_player, regex=False, na=False)
        ].copy() if not trades_df.empty else pd.DataFrame()

        # --- 1. TOP-LEVEL CAREER KPI BANNER ---
        p_starts = p_box[p_box['Is_Start']] if not p_box.empty else pd.DataFrame()
        tot_starts = len(p_starts)
        tot_start_pts = p_starts['Pts'].sum() if not p_starts.empty else 0.0
        career_pps = (tot_start_pts / tot_starts) if tot_starts > 0 else 0.0
        tot_bench_wks = int((~p_box['Is_Start']).sum()) if not p_box.empty else 0
        career_vor = p_box['Wk_Val'].sum() if not p_box.empty else 0.0

        times_drafted = len(p_draft)
        adp_str = f"#{p_draft['Overall Pick'].mean():.1f}" if times_drafted > 0 else "Undrafted"
        adds_cnt = len(p_tx[p_tx['Action'] == 'ADD']) if not p_tx.empty else 0
        trades_cnt = len(p_trades)

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("Career Starts (Bench)", f"{tot_starts} ({tot_bench_wks} BE)")
        k2.metric("Starter Points", f"{tot_start_pts:,.1f}")
        k3.metric("Career Pts / Start", f"{career_pps:.1f}")
        k4.metric("Career Value Over Rep", fmt_signed(career_vor))
        k5.metric("Drafted (ADP)", f"{times_drafted}x ({adp_str})")
        k6.metric("Adds / Trades", f"{adds_cnt} Adds • {trades_cnt} Trades")

        st.write("---")

        # --- 2. SEASON-BY-SEASON CAREER LOG (ALL SEASONS DRAFTED OR ROSTERED) ---
        st.write(f"#### {sel_player} — Season-by-Season Summary")
        szn_set = sorted(
            list(set(p_draft['Year'].unique().tolist() if not p_draft.empty else []) |
                 set(p_box['Szn'].unique().tolist() if not p_box.empty else [])),
            reverse=True
        )

        pos_rk_lookup = {}
        if not b_scored.empty:
            b_dedup = b_scored.sort_values('Is_Start', ascending=False).drop_duplicates(subset=['Szn', 'Wk', 'Pl'])
            pt_agg = b_dedup.groupby(['Szn', 'Pos', 'Pl'])['Pts'].sum().reset_index()
            pt_agg['Rk'] = pt_agg.groupby(['Szn', 'Pos'])['Pts'].rank(ascending=False, method='min').astype(int)
            for _, r in pt_agg[pt_agg['Pts'] > 0].iterrows():
                pos_rk_lookup[(int(r['Szn']), str(r['Pl']))] = f"{r['Pos']}{int(r['Rk'])}"

        szn_rows = []
        for syr in szn_set:
            d_row = p_draft[p_draft['Year'] == syr].iloc[0] if (not p_draft.empty and syr in p_draft['Year'].values) else None
            b_szn = p_box[p_box['Szn'] == syr] if not p_box.empty else pd.DataFrame()
            b_st = b_szn[b_szn['Is_Start']] if not b_szn.empty else pd.DataFrame()

            draft_str = f"Rd {int(d_row['Round'])}, #{int(d_row['Overall Pick'])} ({d_row['Team']})" if d_row is not None else "Undrafted (FA/Waivers)"
            pick_dva_str = fmt_signed(d_row['Pick_DVA']) if (d_row is not None and 'Pick_DVA' in d_row) else "-"
            tr_dva_str = fmt_signed(d_row['Trade_Adj_DVA']) if (d_row is not None and 'Trade_Adj_DVA' in d_row) else "-"

            s_cnt = len(b_st)
            be_cnt = int((~b_szn['Is_Start']).sum()) if not b_szn.empty else 0
            s_pts = b_st['Pts'].sum() if not b_st.empty else 0.0
            pps = (s_pts / s_cnt) if s_cnt > 0 else 0.0
            s_vor = b_szn['Wk_Val'].sum() if not b_szn.empty else 0.0
            pos_rk = pos_rk_lookup.get((int(syr), sel_player), d_row['Pos_Rank'] if (d_row is not None and 'Pos_Rank' in d_row) else "-")

            if not b_st.empty:
                m_bd = [f"{m} ({len(g)} GS, {g['Pts'].sum():.1f} pts)" for m, g in b_st.groupby('Mgr')]
                mgrs_started_str = ", ".join(m_bd)
            elif not b_szn.empty:
                m_be = sorted(b_szn['Mgr'].unique().tolist())
                mgrs_started_str = f"Bench only ({', '.join(m_be)})"
            else:
                mgrs_started_str = "-"

            szn_rows.append({
                'Season': syr,
                'Draft Status': draft_str,
                'Pos Rank': pos_rk,
                'Starts': s_cnt,
                'Bench Wks': be_cnt,
                'Starter Pts': f"{s_pts:.1f}",
                'Pts / Start': f"{pps:.1f}",
                'Lineup VOR': fmt_signed(s_vor),
                'Pick DVA': pick_dva_str,
                'Trade-Adj DVA': tr_dva_str,
                'Managers Started For': mgrs_started_str
            })

        if szn_rows:
            render_table(pd.DataFrame(szn_rows), left_align_cols=['Draft Status', 'Managers Started For'])

        # --- 3. FRANCHISE / MANAGER BREAKDOWN & TRANSACTION TIMELINE ---
        c_left, c_right = st.columns([1.15, 1.85])
        with c_left:
            st.write("#### Production by DFFL Manager")
            if not p_box.empty:
                m_rows = []
                for mgr, grp in p_box.groupby('Mgr'):
                    st_g = grp[grp['Is_Start']]
                    gs = len(st_g)
                    be = len(grp) - gs
                    pts = st_g['Pts'].sum()
                    pps = (pts / gs) if gs > 0 else 0.0
                    vor = grp['Wk_Val'].sum()
                    szns_str = ", ".join(str(y) for y in sorted(grp['Szn'].unique(), reverse=True))
                    m_rows.append({
                        'Manager': mgr,
                        'Starts': gs,
                        'Bench Wks': be,
                        'Pts_Num': pts,
                        'Starter Pts': f"{pts:.1f}",
                        'Pts / Start': f"{pps:.1f}",
                        'Value Over Rep': fmt_signed(vor),
                        'Seasons': szns_str
                    })
                m_df = pd.DataFrame(m_rows).sort_values(['Pts_Num', 'Starts'], ascending=[False, False]).reset_index(drop=True)
                render_table(m_df[['Manager', 'Starts', 'Bench Wks', 'Starter Pts', 'Pts / Start', 'Value Over Rep', 'Seasons']], left_align_cols=['Seasons'])
            else:
                st.info("No box score appearances recorded.")

        with c_right:
            st.write("#### Complete Transaction & Trade Log")
            tx_events = []
            if not p_tx.empty:
                for _, r in p_tx[p_tx['Action'].isin(['ADD', 'DROP'])].iterrows():
                    szn = int(r['Season'])
                    wk = int(r['Week'])
                    act = str(r['Action'])
                    tx_t = str(r['Type'])
                    bid = int(r['Bid_Amount'])
                    if act == 'ADD':
                        mgr = value_engine.map_team_to_mgr(r['To_Team'])
                        acq_type = f"FAAB Waiver (${bid})" if (szn >= 2026 and tx_t == 'WAIVER') else ("Priority Waiver" if tx_t == 'WAIVER' else "Free Agent Add")
                        detail = f"Added by {mgr}"
                    else:
                        mgr = value_engine.map_team_to_mgr(r['From_Team'])
                        acq_type = "Dropped"
                        detail = f"Dropped by {mgr}"
                    tx_events.append({
                        'Season': szn,
                        'Week': wk,
                        'Move Type': acq_type,
                        'Manager(s)': mgr,
                        'Transaction Details': detail
                    })

            if not p_trades.empty:
                for _, tr in p_trades.iterrows():
                    szn = int(tr['Season'])
                    wk = int(tr['Week'])
                    m1 = value_engine.map_team_to_mgr(tr['Manager 1'])
                    m2 = value_engine.map_team_to_mgr(tr['Manager 2'])
                    m1_rec = str(tr['Manager 1 Receives'])
                    m2_rec = str(tr['Manager 2 Receives'])
                    if sel_player in m1_rec:
                        from_m, to_m = m2, m1
                    else:
                        from_m, to_m = m1, m2
                    tx_events.append({
                        'Season': szn,
                        'Week': wk,
                        'Move Type': 'Trade',
                        'Manager(s)': f"{from_m} → {to_m}",
                        'Transaction Details': f"{m1} gets: {m1_rec}  |  {m2} gets: {m2_rec}"
                    })

            if tx_events:
                tx_ev_df = pd.DataFrame(tx_events).sort_values(['Season', 'Week'], ascending=[False, False]).reset_index(drop=True)
                render_table(tx_ev_df[['Season', 'Week', 'Move Type', 'Manager(s)', 'Transaction Details']], left_align_cols=['Transaction Details'])
            else:
                st.info("No waiver adds, drops, or trades recorded for this player.")

    elif draft_view == "Manager Draft Room":
        base_df = dva_df if not dva_df.empty else df
        c1, c2 = st.columns(2)
        sel_mgr = c1.selectbox("Select Manager:", managers_avail, key="mdr_mgr")
        sel_m_yr = c2.selectbox("Select Season:", ["All-Time Summary"] + [str(y) for y in years_avail], key="mdr_yr")

        m_df = base_df[base_df['Team'] == sel_mgr].copy()
        if sel_m_yr == "All-Time Summary":
            c_left, c_right = st.columns([1.3, 1.7])
            with c_left:
                st.write(f"#### {sel_mgr}'s Round 1 History")
                r1_df = m_df[m_df['Round'] == 1].sort_values('Year', ascending=False).copy()
                if 'Pick_DVA' in r1_df.columns:
                    r1_df['Pts / Start'] = r1_df['Pts_Per_Start'].apply(lambda x: f"{x:.1f}")
                    r1_df['Pick DVA'] = r1_df['Pick_DVA'].apply(fmt_signed)
                    r1_df['Trade-Adj DVA'] = r1_df['Trade_Adj_DVA'].apply(fmt_signed)
                    r1_disp = r1_df[['Year', 'Overall Pick', 'Player', 'Position', 'NFL Team', 'Pts / Start', 'Pos_Rank', 'Pick DVA', 'Trade-Adj DVA']].rename(
                        columns={'Overall Pick': 'Pick #', 'Pos_Rank': 'Pos Rank'}
                    )
                else:
                    r1_disp = r1_df[['Year', 'Overall Pick', 'Player', 'Position', 'NFL Team']].rename(columns={'Overall Pick': 'Pick #'})
                render_table(r1_disp, left_align_cols=['Player'])

                st.write("#### Position Breakdown (All Rounds)")
                pos_agg = m_df.groupby('Position').agg(
                    Picks=('Player', 'count'),
                    Avg_Round=('Round', 'mean')
                ).reset_index()
                pos_agg['% of Picks'] = (pos_agg['Picks'] / len(m_df) * 100).apply(lambda x: f"{x:.1f}%")
                pos_agg['Avg Round'] = pos_agg['Avg_Round'].apply(lambda x: f"{x:.1f}")
                pos_agg = pos_agg.sort_values('Picks', ascending=False)[['Position', 'Picks', '% of Picks', 'Avg Round']]
                render_table(pos_agg)

            with c_right:
                st.write(f"#### {sel_mgr}'s Draft Favorites (Drafted 2+ Times)")
                fav = m_df.groupby('Player').agg(
                    Pos=('Position', lambda s: s.mode().iloc[0] if not s.mode().empty else ''),
                    Times=('Year', 'count'),
                    Years=('Year', lambda s: ", ".join(str(y) for y in sorted(s, reverse=True))),
                    Best_Pick=('Overall Pick', 'min'),
                    Avg_Pick=('Overall Pick', 'mean')
                ).reset_index()
                fav = fav[fav['Times'] >= 2].sort_values(['Times', 'Avg_Pick'], ascending=[False, True]).reset_index(drop=True)
                if not fav.empty:
                    fav['Avg Pick'] = fav['Avg_Pick'].apply(lambda x: f"{x:.1f}")
                    fav['Best Pick'] = fav['Best_Pick'].apply(lambda x: f"#{int(x)}")
                    render_table(fav[['Player', 'Pos', 'Times', 'Best Pick', 'Avg Pick', 'Years']], left_align_cols=['Player', 'Years'])
                else:
                    st.info("No players drafted multiple times.")
        else:
            st.write(f"#### {sel_mgr}'s {sel_m_yr} Draft Class")
            yr_sub = m_df[m_df['Year'] == int(sel_m_yr)].sort_values('Round').copy()
            if 'Pick_DVA' in yr_sub.columns:
                yr_sub['Starts'] = yr_sub['Total_Starts'].astype(int)
                yr_sub['Pts / Start'] = yr_sub['Pts_Per_Start'].apply(lambda x: f"{x:.1f}")
                yr_sub['Pick DVA'] = yr_sub['Pick_DVA'].apply(fmt_signed)
                yr_sub['Trade-Adj DVA'] = yr_sub['Trade_Adj_DVA'].apply(fmt_signed)
                yr_disp = yr_sub[['Round', 'Round Pick', 'Overall Pick', 'Player', 'Position', 'NFL Team', 'Starts', 'Pts / Start', 'Pos_Rank', 'Pick DVA', 'Trade-Adj DVA']].rename(
                    columns={'Round Pick': 'Pick in Rd', 'Overall Pick': 'Overall #', 'Pos_Rank': 'Pos Rank'}
                )
            else:
                yr_disp = yr_sub[['Round', 'Round Pick', 'Overall Pick', 'Player', 'Position', 'NFL Team']].rename(
                    columns={'Round Pick': 'Pick in Rd', 'Overall Pick': 'Overall #'}
                )
            render_table(yr_disp, left_align_cols=['Player'])

    elif draft_view == "Draft Records & Loyalty":
        rec_mode = st.radio(
            "Select Draft Record:",
            [
                "Manager Draft Loyalty (Same Player 3+ Times)",
                "Most Drafted Players (League-Wide)",
                "All-Time #1 Overall Picks",
                "Mr. Irrelevant (Final Pick Each Year)",
                "Draft Slot History & Average Pick"
            ],
            horizontal=True,
            key="dr_rec_mode"
        )

        if rec_mode == "Manager Draft Loyalty (Same Player 3+ Times)":
            st.write("#### Players Drafted by the Same Manager 3+ Times (2018–2026)")
            loy = df.groupby(['Team', 'Player']).agg(
                Pos=('Position', lambda s: s.mode().iloc[0] if not s.mode().empty else ''),
                Times=('Year', 'count'),
                Years=('Year', lambda s: ", ".join(str(y) for y in sorted(s, reverse=True))),
                Best_Pick=('Overall Pick', 'min'),
                Avg_Pick=('Overall Pick', 'mean')
            ).reset_index()
            loy = loy[loy['Times'] >= 3].sort_values(['Times', 'Avg_Pick'], ascending=[False, True]).reset_index(drop=True)
            loy['Best Pick'] = loy['Best_Pick'].apply(lambda x: f"#{int(x)}")
            loy['Avg Pick'] = loy['Avg_Pick'].apply(lambda x: f"{x:.1f}")
            render_table(
                loy[['Team', 'Player', 'Pos', 'Times', 'Best Pick', 'Avg Pick', 'Years']].rename(columns={'Team': 'Manager'}),
                left_align_cols=['Player', 'Years']
            )

        elif rec_mode == "Most Drafted Players (League-Wide)":
            st.write("#### Most Frequently Drafted Players Across All Managers (7+ Times)")
            pop = df.groupby('Player').agg(
                Pos=('Position', lambda s: s.mode().iloc[0] if not s.mode().empty else ''),
                Times_Drafted=('Year', 'count'),
                Unique_Managers=('Team', 'nunique'),
                Avg_Pick=('Overall Pick', 'mean'),
                Best_Pick=('Overall Pick', 'min'),
                Drafted_By=('Team', lambda s: ", ".join(f"{k} ({v}x)" if v > 1 else k for k, v in s.value_counts().items()))
            ).reset_index()
            pop = pop[pop['Pos'] != 'D/ST']
            pop = pop[pop['Times_Drafted'] >= 7].sort_values(['Times_Drafted', 'Avg_Pick'], ascending=[False, True]).reset_index(drop=True)
            pop['ADP'] = pop['Avg_Pick'].apply(lambda x: f"{x:.1f}")
            pop['Highest Pick'] = pop['Best_Pick'].apply(lambda x: f"#{int(x)}")
            render_table(
                pop[['Player', 'Pos', 'Times_Drafted', 'Unique_Managers', 'Highest Pick', 'ADP', 'Drafted_By']].rename(
                    columns={'Times_Drafted': 'Times Drafted', 'Unique_Managers': 'Unique Managers', 'Drafted_By': 'Managers'}
                ),
                left_align_cols=['Player', 'Managers']
            )

        elif rec_mode == "All-Time #1 Overall Picks":
            st.write("#### Every #1 Overall Draft Pick (2018–2026)")
            p1 = df[df['Overall Pick'] == 1].sort_values('Year', ascending=False)[['Year', 'Team', 'Player', 'Position', 'NFL Team']].rename(
                columns={'Team': 'Manager'}
            )
            render_table(p1)

        elif rec_mode == "Mr. Irrelevant (Final Pick Each Year)":
            st.write("#### Mr. Irrelevant — Final Pick of Every Draft")
            idx_max = df.groupby('Year')['Overall Pick'].idxmax()
            irrel = df.loc[idx_max].sort_values('Year', ascending=False)[['Year', 'Round', 'Overall Pick', 'Team', 'Player', 'Position', 'NFL Team']].rename(
                columns={'Team': 'Manager', 'Overall Pick': 'Pick #'}
            )
            render_table(irrel)

        elif rec_mode == "Draft Slot History & Average Pick":
            st.write("#### Draft Slot History by Season (Round 1 Pick Order)")
            r1_all = df[df['Round'] == 1].copy()
            piv = r1_all.pivot(index='Team', columns='Year', values='Overall Pick')
            yr_cols = sorted(piv.columns.tolist(), reverse=True)
            piv['Avg Slot'] = piv[yr_cols].mean(axis=1).apply(lambda x: f"{x:.2f}")
            piv['#1 Picks'] = (piv[yr_cols] == 1).sum(axis=1)
            piv = piv.sort_values('Avg Slot')
            for y in yr_cols:
                piv[y] = piv[y].apply(lambda v: f"#{int(v)}" if pd.notnull(v) else "-")
            piv_disp = piv.reset_index().rename(columns={'Team': 'Manager'})[['Manager'] + yr_cols + ['Avg Slot', '#1 Picks']]
            render_table(piv_disp)
            
