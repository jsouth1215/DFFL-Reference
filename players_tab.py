import importlib
import streamlit as st
import pandas as pd
import numpy as np
import value_engine
importlib.reload(value_engine)

POS_COLORS = {
    'RB': ('#cfe2f3', '#0b5394'),
    'WR': ('#d9ead3', '#274e13'),
    'QB': ('#f4cccc', '#783f04'),
    'TE': ('#fce5cd', '#b45f06'),
    'D/ST': ('#d9d2e9', '#351c75'),
    'K': ('#efefef', '#444444')
}

def render_table(df, left_align_cols=None, highlight_fn=None):
    if df is None or df.empty:
        return
    styler = df.style.hide(axis='index')
    styler = styler.set_properties(**{
        'text-align': 'center',
        'padding': '7px 10px',
        'border': '1px solid #e2e8f0',
        'white-space': 'nowrap',
        'font-size': '13.5px'
    })
    if left_align_cols:
        valid_cols = [c for c in left_align_cols if c in df.columns]
        if valid_cols:
            styler = styler.set_properties(subset=valid_cols, **{
                'text-align': 'left',
                'white-space': 'normal',
                'min-width': '160px',
                'max-width': '340px',
                'line-height': '1.35'
            })
    if highlight_fn:
        styler = styler.apply(highlight_fn, axis=1)

    styled_html = styler.set_table_styles([
        {'selector': 'th', 'props': [
            ('text-align', 'center'),
            ('padding', '8px 10px'),
            ('border', '1px solid #cbd5e1'),
            ('background-color', '#f8fafc'),
            ('color', '#0f172a'),
            ('font-weight', '700'),
            ('font-size', '13px'),
            ('white-space', 'nowrap')
        ]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#fcfcfd')]},
        {'selector': 'table', 'props': [
            ('width', '100%'),
            ('border-collapse', 'collapse'),
            ('margin', '0')
        ]}
    ]).to_html()

    wrapper_html = (
        "<style>"
        ".dffl-tbl-wrap { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; "
        "margin: 6px 0 18px 0; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; }"
        ".dffl-tbl-wrap table { width: 100%; border-collapse: collapse; }"
        "@media (max-width: 768px) {"
        "  .dffl-tbl-wrap th, .dffl-tbl-wrap td { padding: 5px 7px !important; font-size: 12px !important; }"
        "  .dffl-tbl-wrap td:first-child, .dffl-tbl-wrap th:first-child { "
        "    position: sticky; left: 0; background-color: #f8fafc; z-index: 1; border-right: 2px solid #cbd5e1 !important; "
        "  }"
        "}"
        "</style>"
        f'<div class="dffl-tbl-wrap">{styled_html}</div>'
    )
    st.markdown(wrapper_html, unsafe_allow_html=True)

render_html_table = render_table

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
            dfs_b = []
            for fn, sn in [("espn_fantasy_complete_stats_2017_2026.xlsx", "Box_Scores"), ("reconstructed_2018_box_scores.xlsx", "Box_Scores_2018"), ("reconstructed_2017_box_scores.xlsx", "Box_Scores_2017")]:
                try:
                    dfs_b.append(pd.read_excel(fn, sheet_name=sn, engine="openpyxl"))
                except Exception:
                    pass
            if dfs_b:
                box_df = pd.concat(dfs_b, ignore_index=True)

    b_norm = value_engine.normalize_box_df(box_df)
    b_scored, _ = value_engine.compute_weekly_scores(b_norm)

    draft_df, tx_df, trades_df, dva_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        import draft_tab
        draft_df = draft_tab.load_draft_data(box_df)
    except Exception:
        pass

    try:
        import transactions_tab
        tx_df, trades_df = transactions_tab.load_transactions_data(box_df)
    except Exception:
        pass

    if not draft_df.empty and not b_scored.empty:
        try:
            dva_df = value_engine.compute_draft_value_added(draft_df, box_df, trades_df)
        except Exception:
            pass

    if b_scored.empty and draft_df.empty:
        st.warning("No player scoring or draft data available.")
        return

    pos_rk_lookup = {}
    if not b_scored.empty:
        b_dedup = b_scored.sort_values('Is_Start', ascending=False).drop_duplicates(subset=['Szn', 'Wk', 'Pl'])
        pt_agg = b_dedup.groupby(['Szn', 'Pos', 'Pl'])['Pts'].sum().reset_index()
        pt_agg['Rk'] = pt_agg.groupby(['Szn', 'Pos'])['Pts'].rank(ascending=False, method='min').astype(int)
        for _, r in pt_agg[pt_agg['Pts'] > 0].iterrows():
            pos_rk_lookup[(int(r['Szn']), str(r['Pl']))] = f"{r['Pos']}{int(r['Rk'])}"

    player_view = st.radio(
        "Players View:",
        [
            "NFL Player Profile",
            "All-Time Career Leaders",
            "Single-Season Legends",
            "Weekly Boom Games & Records",
            "Player-Manager Connection"
        ],
        horizontal=True,
        key="players_main_view_v2"
    )
    st.write("---")

    # ================= VIEW 1: NFL PLAYER PROFILE =================
    if player_view == "NFL Player Profile":
        draft_players = set(draft_df['Player'].dropna().unique()) if not draft_df.empty else set()
        box_players = set(b_scored['Pl'].dropna().unique()) if not b_scored.empty else set()
        tx_players = set(tx_df['Player'].dropna().unique()) if not tx_df.empty else set()
        all_players = sorted([p for p in (draft_players | box_players | tx_players) if p and p != '(Redacted / Empty)'])

        default_idx = all_players.index("Christian McCaffrey") if "Christian McCaffrey" in all_players else 0
        sel_player = st.selectbox("Search / Select Player (All-Time DFFL Database):", all_players, index=default_idx, key="pcd_player")

        p_draft = (dva_df[dva_df['Player'] == sel_player] if not dva_df.empty else (draft_df[draft_df['Player'] == sel_player] if not draft_df.empty else pd.DataFrame())).sort_values('Year', ascending=False).copy()
        p_box = b_scored[b_scored['Pl'] == sel_player].copy() if not b_scored.empty else pd.DataFrame()
        p_tx = tx_df[(tx_df['Player'] == sel_player) & (tx_df['Status'] == 'EXECUTED') & (tx_df['Action'].isin(['ADD', 'DROP', 'TRADE']))].copy() if not tx_df.empty else pd.DataFrame()
        p_trades = trades_df[
            trades_df['Manager 1 Receives'].astype(str).str.contains(sel_player, regex=False, na=False) |
            trades_df['Manager 2 Receives'].astype(str).str.contains(sel_player, regex=False, na=False)
        ].copy() if not trades_df.empty else pd.DataFrame()

        p_starts = p_box[p_box['Is_Start']] if not p_box.empty else pd.DataFrame()
        tot_starts = len(p_starts)
        tot_start_pts = p_starts['Pts'].sum() if not p_starts.empty else 0.0
        career_pps = (tot_start_pts / tot_starts) if tot_starts > 0 else 0.0
        tot_bench_wks = int((~p_box['Is_Start']).sum()) if not p_box.empty else 0
        career_val_score = p_box['Wk_Val'].sum() if not p_box.empty else 0.0

        pos_str = p_box['Pos'].mode().iloc[0] if (not p_box.empty and not p_box['Pos'].mode().empty) else (
            p_draft['Position'].mode().iloc[0] if (not p_draft.empty and not p_draft['Position'].mode().empty) else 'NFL'
        )
        pos_bg, pos_fg = POS_COLORS.get(pos_str, ('#e2e8f0', '#1e293b'))

        times_drafted = len(p_draft)
        if times_drafted > 0:
            adp_val = p_draft['Overall Pick'].mean()
            best_pick = int(p_draft['Overall Pick'].min())
            draft_summary_str = f"{times_drafted}x (ADP #{adp_val:.1f}, High #{best_pick})"
        else:
            draft_summary_str = "Undrafted"

        adds_cnt = len(p_tx[p_tx['Action'] == 'ADD']) if not p_tx.empty else 0
        drops_cnt = len(p_tx[p_tx['Action'] == 'DROP']) if not p_tx.empty else 0
        trades_cnt = len(p_trades)

        if not p_starts.empty:
            best_row = p_starts.loc[p_starts['Pts'].idxmax()]
            best_gm_str = f"{best_row['Pts']:.1f} pts ({int(best_row['Szn'])} W{int(best_row['Wk'])}, {best_row['Mgr']})"
            mgr_pts = p_starts.groupby('Mgr').agg(GS=('Wk', 'count'), Pts=('Pts', 'sum')).sort_values('Pts', ascending=False)
            top_mgr_str = f"{mgr_pts.index[0]} ({int(mgr_pts.iloc[0]['GS'])} GS, {mgr_pts.iloc[0]['Pts']:,.1f} pts)"
            uniq_mgrs_started = p_starts['Mgr'].nunique()
        else:
            best_gm_str = "N/A"
            top_mgr_str = "N/A"
            uniq_mgrs_started = 0

        szn_set = sorted(
            list(set(p_draft['Year'].unique().tolist() if not p_draft.empty else []) |
                 set(p_box['Szn'].unique().tolist() if not p_box.empty else [])),
            reverse=True
        )
        best_szn_rk_str = "N/A"
        best_rk_num = 999
        for syr in szn_set:
            rk_lbl = pos_rk_lookup.get((int(syr), sel_player), "-")
            if rk_lbl != "-":
                num_part = ''.join(filter(str.isdigit, rk_lbl))
                if num_part and int(num_part) < best_rk_num:
                    best_rk_num = int(num_part)
                    best_szn_rk_str = f"{rk_lbl} ({syr})"

        st.markdown(
            f"<div style='display:flex; align-items:center; gap:10px; margin: 4px 0 12px 0;'>"
            f"<span style='font-size:22px; font-weight:800; color:#0f172a;'>{sel_player}</span>"
            f"<span style='background:{pos_bg}; color:{pos_fg}; padding:3px 9px; border-radius:5px; font-weight:700; font-size:13px;'>{pos_str}</span>"
            f"<span style='font-size:13px; color:#64748b;'>Active Seasons: {len(szn_set)} ({min(szn_set) if szn_set else '-'}–{max(szn_set) if szn_set else '-'})</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Career Starts (Bench):** {tot_starts} GS ({tot_bench_wks} BE)")
            st.markdown(f"**Career Starter Points:** {tot_start_pts:,.1f} ({career_pps:.1f} Pts/Start)")
            st.markdown(f"**Career Value Score:** {fmt_signed(career_val_score)}")
        with c2:
            st.markdown(f"**Peak Season Finish:** {best_szn_rk_str}")
            st.markdown(f"**Career High Game:** {best_gm_str}")
            st.markdown(f"**Top DFFL Manager:** {top_mgr_str}")
        with c3:
            st.markdown(f"**Draft History:** {draft_summary_str}")
            st.markdown(f"**Transactions:** {adds_cnt} Adds • {drops_cnt} Drops • {trades_cnt} Trades")
            st.markdown(f"**Franchises Started For:** {uniq_mgrs_started} Managers")

        st.divider()

        dossier_sub = st.radio(
            "Profile Section:",
            [
                "Season-by-Season & Manager Breakdown",
                "Draft & Transaction Timeline",
                "Weekly Game Log & Best Performances"
            ],
            horizontal=True,
            key="pcd_sub_sec"
        )

        if dossier_sub == "Season-by-Season & Manager Breakdown":
            st.write(f"#### {sel_player} — Season-by-Season Career Log")
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
                s_vs = b_szn['Wk_Val'].sum() if not b_szn.empty else 0.0
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
                    'Value Score': fmt_signed(s_vs),
                    'Pick DVA': pick_dva_str,
                    'Trade-Adj DVA': tr_dva_str,
                    'Managers Started For': mgrs_started_str
                })

            if szn_rows:
                render_table(pd.DataFrame(szn_rows), left_align_cols=['Draft Status', 'Managers Started For'])

            st.write(f"#### {sel_player} — Production by DFFL Manager")
            if not p_box.empty:
                m_rows = []
                for mgr, grp in p_box.groupby('Mgr'):
                    st_g = grp[grp['Is_Start']]
                    gs = len(st_g)
                    be = len(grp) - gs
                    pts = st_g['Pts'].sum()
                    pps = (pts / gs) if gs > 0 else 0.0
                    vs = grp['Wk_Val'].sum()
                    max_gm = grp['Pts'].max() if not grp.empty else 0.0
                    szns_str = ", ".join(str(y) for y in sorted(grp['Szn'].unique(), reverse=True))
                    m_rows.append({
                        'Manager': mgr,
                        'Starts': gs,
                        'Bench Wks': be,
                        'Pts_Num': pts,
                        'Starter Pts': f"{pts:.1f}",
                        'Pts / Start': f"{pps:.1f}",
                        'Best Game': f"{max_gm:.1f}",
                        'Value Score': fmt_signed(vs),
                        'Seasons Rostered': szns_str
                    })
                m_df = pd.DataFrame(m_rows).sort_values(['Pts_Num', 'Starts'], ascending=[False, False]).reset_index(drop=True)
                render_table(m_df[['Manager', 'Starts', 'Bench Wks', 'Starter Pts', 'Pts / Start', 'Best Game', 'Value Score', 'Seasons Rostered']], left_align_cols=['Seasons Rostered'])
            else:
                st.info("No box score appearances recorded.")

        elif dossier_sub == "Draft & Transaction Timeline":
            c_left, c_right = st.columns([1.15, 1.85])
            with c_left:
                st.write(f"#### {sel_player} — Draft History")
                if not p_draft.empty:
                    p_d = p_draft.copy()
                    if 'Pick_DVA' in p_d.columns:
                        p_d['Starts'] = p_d['Total_Starts'].astype(int)
                        p_d['Pts / Start'] = p_d['Pts_Per_Start'].apply(lambda x: f"{x:.1f}")
                        p_d['Pick DVA'] = p_d['Pick_DVA'].apply(fmt_signed)
                        p_d['Trade-Adj DVA'] = p_d['Trade_Adj_DVA'].apply(fmt_signed)
                        d_disp = p_d[['Year', 'Round', 'Overall Pick', 'Team', 'NFL Team', 'Starts', 'Pts / Start', 'Pick DVA', 'Trade-Adj DVA']].rename(
                            columns={'Overall Pick': 'Pick #', 'Team': 'Drafted By'}
                        )
                    else:
                        d_disp = p_d[['Year', 'Round', 'Overall Pick', 'Team', 'NFL Team']].rename(
                            columns={'Overall Pick': 'Pick #', 'Team': 'Drafted By'}
                        )
                    render_table(d_disp)
                else:
                    st.info("Never drafted in DFFL (2017–2026).")

            with c_right:
                st.write(f"#### {sel_player} — Complete Transaction & Trade Log")
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

        elif dossier_sub == "Weekly Game Log & Best Performances":
            if p_box.empty:
                st.info("No weekly box score records found for this player.")
            else:
                c1, c2 = st.columns([1.2, 1.8])
                with c1:
                    st.write("#### Top 10 Highest-Scoring Weeks")
                    top_wks = p_box.sort_values('Pts', ascending=False).head(10).reset_index(drop=True)
                    top_wks['Rank'] = top_wks.index + 1
                    top_wks['Status'] = np.where(top_wks['Is_Start'], 'Started (' + top_wks['Slot_Clean'] + ')', 'Bench')
                    top_wks['Points'] = top_wks['Pts'].apply(lambda x: f"{x:.2f}")
                    top_wks['Value Score'] = top_wks['Wk_Val'].apply(fmt_signed)
                    top_wks['Wk Pos Rk'] = top_wks.apply(lambda r: f"{r['Pos']}{int(r['Wk_Pos_Rk'])}", axis=1)
                    render_table(top_wks[['Rank', 'Szn', 'Wk', 'Mgr', 'Status', 'Points', 'Wk Pos Rk', 'Value Score']].rename(
                        columns={'Szn': 'Season', 'Wk': 'Week', 'Mgr': 'Manager'}
                    ))

                with c2:
                    szn_opts = ["All Seasons"] + [str(y) for y in sorted(p_box['Szn'].unique(), reverse=True)]
                    sel_log_szn = st.selectbox("Filter Game Log by Season:", szn_opts, key="pcd_gmlog_szn")
                    g_sub = p_box.copy() if sel_log_szn == "All Seasons" else p_box[p_box['Szn'] == int(sel_log_szn)].copy()
                    g_sub = g_sub.sort_values(['Szn', 'Wk'], ascending=[False, True]).reset_index(drop=True)
                    g_sub['Status'] = np.where(g_sub['Is_Start'], 'Started (' + g_sub['Slot_Clean'] + ')', 'Bench (' + g_sub['Slot_Clean'] + ')')
                    g_sub['Points'] = g_sub['Pts'].apply(lambda x: f"{x:.2f}")
                    g_sub['Rep Baseline'] = g_sub['Rep_Base'].apply(lambda x: f"{x:.1f}")
                    g_sub['Value Score'] = g_sub['Wk_Val'].apply(fmt_signed)
                    g_sub['Wk Pos Rk'] = g_sub.apply(lambda r: f"{r['Pos']}{int(r['Wk_Pos_Rk'])}", axis=1)
                    render_table(g_sub[['Szn', 'Wk', 'Mgr', 'Status', 'Points', 'Wk Pos Rk', 'Rep Baseline', 'Value Score']].rename(
                        columns={'Szn': 'Season', 'Wk': 'Week', 'Mgr': 'Manager'}
                    ))

    # ================= VIEW 2: ALL-TIME CAREER LEADERS =================
    elif player_view == "All-Time Career Leaders":
        st.caption("All-time career DFFL production across 2017–2026. **Value Score** sums weekly starter points above positional replacement (minus -0.5 pt/wk healthy bench clog).")
        c1, c2, c3 = st.columns(3)
        pos_f = c1.selectbox("Position Filter:", ["Skill Players (QB/RB/WR/TE)", "All Positions", "QB", "RB", "WR", "TE", "D/ST", "K"], key="acl_pos")
        sort_by = c2.selectbox("Rank By:", ["Total Value Score", "Total Starter Points", "Total Career Starts", "Career Pts / Start (Min. 15 Starts)"], key="acl_sort")
        mgr_f = c3.selectbox("Filter by Manager (Optional):", ["All Managers (League-Wide)"] + sorted(b_scored['Mgr'].unique().tolist()), key="acl_mgr")

        base = b_scored.copy()
        if pos_f == "Skill Players (QB/RB/WR/TE)":
            base = base[~base['Pos'].isin(['D/ST', 'K'])]
        elif pos_f != "All Positions":
            base = base[base['Pos'] == pos_f]
        if not mgr_f.startswith("All Managers"):
            base = base[base['Mgr'] == mgr_f]

        st_only = base[base['Is_Start']]
        starts_agg = st_only.groupby('Pl').agg(
            Starts=('Wk', 'count'),
            Starter_Pts=('Pts', 'sum')
        ).reset_index()

        all_agg = base.groupby('Pl').agg(
            Pos=('Pos', lambda s: s.mode().iloc[0] if not s.mode().empty else ''),
            Seasons=('Szn', 'nunique'),
            Roster_Wks=('Wk', 'count'),
            Value_Score=('Wk_Val', 'sum'),
            Unique_Mgrs=('Mgr', 'nunique'),
            Top_Mgr=('Mgr', lambda s: f"{s.value_counts().index[0]} ({s.value_counts().iloc[0]}w)")
        ).reset_index()

        merged = all_agg.merge(starts_agg, on='Pl', how='left')
        merged['Starts'] = merged['Starts'].fillna(0).astype(int)
        merged['Starter_Pts'] = merged['Starter_Pts'].fillna(0.0)
        merged['Bench_Wks'] = merged['Roster_Wks'] - merged['Starts']
        merged['PPS'] = np.where(merged['Starts'] > 0, merged['Starter_Pts'] / merged['Starts'], 0.0)

        if sort_by == "Total Value Score":
            merged = merged.sort_values('Value_Score', ascending=False)
        elif sort_by == "Total Starter Points":
            merged = merged.sort_values('Starter_Pts', ascending=False)
        elif sort_by == "Total Career Starts":
            merged = merged.sort_values(['Starts', 'Starter_Pts'], ascending=[False, False])
        else:
            merged = merged[merged['Starts'] >= 15].sort_values('PPS', ascending=False)

        top_df = merged.head(35).reset_index(drop=True)
        top_df['Rank'] = top_df.index + 1
        top_df['Starter Pts'] = top_df['Starter_Pts'].apply(lambda x: f"{x:,.1f}")
        top_df['Pts / Start'] = top_df['PPS'].apply(lambda x: f"{x:.1f}")
        top_df['Value Score'] = top_df['Value_Score'].apply(fmt_signed)
        disp = top_df[['Rank', 'Pl', 'Pos', 'Seasons', 'Starts', 'Bench_Wks', 'Starter Pts', 'Pts / Start', 'Value Score', 'Unique_Mgrs', 'Top_Mgr']].rename(
            columns={'Pl': 'Player', 'Bench_Wks': 'Bench Wks', 'Unique_Mgrs': 'Managers', 'Top_Mgr': 'Most Rostered By'}
        )
        render_table(disp, left_align_cols=['Player', 'Most Rostered By'])

    # ================= VIEW 3: SINGLE-SEASON LEGENDS =================
    elif player_view == "Single-Season Legends":
        st.caption("Greatest individual player-seasons in DFFL history (2017–2026).")
        c1, c2, c3 = st.columns(3)
        s_yr = c1.selectbox("Season:", ["All-Time (2017–2026)"] + [str(y) for y in sorted(b_scored['Szn'].unique(), reverse=True)], key="ssl_yr")
        s_pos = c2.selectbox("Position:", ["Skill Players (QB/RB/WR/TE)", "All Positions", "QB", "RB", "WR", "TE", "D/ST", "K"], key="ssl_pos")
        s_sort = c3.selectbox("Rank By:", ["Season Value Score", "Season Starter Points", "Pts / Start (Min. 8 Starts)"], key="ssl_sort")

        base = b_scored.copy()
        if not s_yr.startswith("All-Time"):
            base = base[base['Szn'] == int(s_yr)]
        if s_pos == "Skill Players (QB/RB/WR/TE)":
            base = base[~base['Pos'].isin(['D/ST', 'K'])]
        elif s_pos != "All Positions":
            base = base[base['Pos'] == s_pos]

        st_only = base[base['Is_Start']]
        st_agg = st_only.groupby(['Szn', 'Pl']).agg(
            Starts=('Wk', 'count'),
            Starter_Pts=('Pts', 'sum'),
            Mgrs=('Mgr', lambda s: ", ".join(f"{k} ({v} GS)" for k, v in s.value_counts().items()))
        ).reset_index()

        tot_agg = base.groupby(['Szn', 'Pl']).agg(
            Pos=('Pos', lambda s: s.mode().iloc[0] if not s.mode().empty else ''),
            Roster_Wks=('Wk', 'count'),
            Value_Score=('Wk_Val', 'sum')
        ).reset_index()

        szn_m = tot_agg.merge(st_agg, on=['Szn', 'Pl'], how='left')
        szn_m['Starts'] = szn_m['Starts'].fillna(0).astype(int)
        szn_m['Starter_Pts'] = szn_m['Starter_Pts'].fillna(0.0)
        szn_m['Mgrs'] = szn_m['Mgrs'].fillna('-')
        szn_m['PPS'] = np.where(szn_m['Starts'] > 0, szn_m['Starter_Pts'] / szn_m['Starts'], 0.0)
        szn_m['Pos Rank'] = szn_m.apply(lambda r: pos_rk_lookup.get((int(r['Szn']), str(r['Pl'])), '-'), axis=1)

        if s_sort == "Season Value Score":
            szn_m = szn_m.sort_values('Value_Score', ascending=False)
        elif s_sort == "Season Starter Points":
            szn_m = szn_m.sort_values('Starter_Pts', ascending=False)
        else:
            szn_m = szn_m[szn_m['Starts'] >= 8].sort_values('PPS', ascending=False)

        top_szn = szn_m.head(35).reset_index(drop=True)
        top_szn['Rank'] = top_szn.index + 1
        top_szn['Starter Pts'] = top_szn['Starter_Pts'].apply(lambda x: f"{x:.1f}")
        top_szn['Pts / Start'] = top_szn['PPS'].apply(lambda x: f"{x:.1f}")
        top_szn['Value Score'] = top_szn['Value_Score'].apply(fmt_signed)
        disp = top_szn[['Rank', 'Szn', 'Pl', 'Pos', 'Pos Rank', 'Starts', 'Starter Pts', 'Pts / Start', 'Value Score', 'Mgrs']].rename(
            columns={'Szn': 'Season', 'Pl': 'Player', 'Mgrs': 'Started By'}
        )
        render_table(disp, left_align_cols=['Player', 'Started By'])

    # ================= VIEW 4: WEEKLY BOOM GAMES & RECORDS =================
    elif player_view == "Weekly Boom Games & Records":
        boom_mode = st.radio(
            "Select Weekly Record View:",
            [
                "Highest Single-Game Starter Scores",
                "Most Career 25+ Point Starter Games",
                "Biggest Bench Heartbreaks (Highest Scores Left on Bench)"
            ],
            horizontal=True,
            key="wb_mode"
        )

        c1, c2 = st.columns(2)
        b_yr = c1.selectbox("Season:", ["All-Time (2017–2026)"] + [str(y) for y in sorted(b_scored['Szn'].unique(), reverse=True)], key="wb_yr")
        b_pos = c2.selectbox("Position:", ["Skill Players (QB/RB/WR/TE)", "All Positions", "QB", "RB", "WR", "TE", "D/ST", "K"], key="wb_pos")

        sub = b_scored.copy()
        if not b_yr.startswith("All-Time"):
            sub = sub[sub['Szn'] == int(b_yr)]
        if b_pos == "Skill Players (QB/RB/WR/TE)":
            sub = sub[~sub['Pos'].isin(['D/ST', 'K'])]
        elif b_pos != "All Positions":
            sub = sub[sub['Pos'] == b_pos]

        if boom_mode == "Highest Single-Game Starter Scores":
            st_sub = sub[sub['Is_Start']].sort_values('Pts', ascending=False).head(35).reset_index(drop=True)
            st_sub['Rank'] = st_sub.index + 1
            st_sub['Points'] = st_sub['Pts'].apply(lambda x: f"{x:.2f}")
            st_sub['Value Score'] = st_sub['Wk_Val'].apply(fmt_signed)
            st_sub['Wk Pos Rk'] = st_sub.apply(lambda r: f"{r['Pos']}{int(r['Wk_Pos_Rk'])}", axis=1)
            render_table(st_sub[['Rank', 'Szn', 'Wk', 'Mgr', 'Pl', 'Pos', 'Points', 'Wk Pos Rk', 'Value Score']].rename(
                columns={'Szn': 'Season', 'Wk': 'Week', 'Mgr': 'Manager', 'Pl': 'Player'}
            ), left_align_cols=['Player'])

        elif boom_mode == "Most Career 25+ Point Starter Games":
            st_sub = sub[sub['Is_Start']].copy()
            st_sub['Is_25'] = st_sub['Pts'] >= 25.0
            st_sub['Is_30'] = st_sub['Pts'] >= 30.0
            boom_agg = st_sub.groupby(['Pl', 'Pos']).agg(
                Starts=('Wk', 'count'),
                Games_25=('Is_25', 'sum'),
                Games_30=('Is_30', 'sum'),
                Max_Pts=('Pts', 'max'),
                Mgrs=('Mgr', lambda s: ", ".join(s.unique().tolist()))
            ).reset_index()
            boom_agg = boom_agg[boom_agg['Games_25'] > 0].sort_values(['Games_25', 'Games_30', 'Max_Pts'], ascending=[False, False, False]).head(30).reset_index(drop=True)
            boom_agg['Rank'] = boom_agg.index + 1
            boom_agg['Boom % (25+)'] = (boom_agg['Games_25'] / boom_agg['Starts'] * 100.0).apply(lambda x: f"{x:.1f}%")
            boom_agg['Career High'] = boom_agg['Max_Pts'].apply(lambda x: f"{x:.2f}")
            render_table(boom_agg[['Rank', 'Pl', 'Pos', 'Starts', 'Games_25', 'Games_30', 'Boom % (25+)', 'Career High', 'Mgrs']].rename(
                columns={'Pl': 'Player', 'Games_25': '25+ Pt Starts', 'Games_30': '30+ Pt Starts', 'Mgrs': 'Managers'}
            ), left_align_cols=['Player', 'Managers'])

        else:
            be_sub = sub[~sub['Is_Start']].sort_values('Pts', ascending=False).head(35).reset_index(drop=True)
            be_sub['Rank'] = be_sub.index + 1
            be_sub['Bench Points'] = be_sub['Pts'].apply(lambda x: f"{x:.2f}")
            be_sub['Wk Pos Rk'] = be_sub.apply(lambda r: f"{r['Pos']}{int(r['Wk_Pos_Rk'])}", axis=1)
            render_table(be_sub[['Rank', 'Szn', 'Wk', 'Mgr', 'Pl', 'Pos', 'Bench Points', 'Wk Pos Rk']].rename(
                columns={'Szn': 'Season', 'Wk': 'Week', 'Mgr': 'Manager', 'Pl': 'Player'}
            ), left_align_cols=['Player'])

    # ================= VIEW 5: PLAYER-MANAGER CONNECTION =================
    elif player_view == "Player-Manager Connection":
        st.caption("The most iconic Manager + Player duos in DFFL history—ranked by total points or Value Score generated for a single franchise.")
        c1, c2, c3 = st.columns(3)
        mgr_sel = c1.selectbox("Filter by Manager:", ["All Managers"] + sorted(b_scored['Mgr'].unique().tolist()), key="pmc_mgr")
        pos_sel = c2.selectbox("Filter by Position:", ["Skill Players (QB/RB/WR/TE)", "All Positions", "QB", "RB", "WR", "TE", "D/ST", "K"], key="pmc_pos")
        duo_sort = c3.selectbox("Rank Duos By:", ["Total Starter Points Together", "Total Value Score Together", "Most Starts Together"], key="pmc_sort")

        sub = b_scored.copy()
        if mgr_sel != "All Managers":
            sub = sub[sub['Mgr'] == mgr_sel]
        if pos_sel == "Skill Players (QB/RB/WR/TE)":
            sub = sub[~sub['Pos'].isin(['D/ST', 'K'])]
        elif pos_sel != "All Positions":
            sub = sub[sub['Pos'] == pos_sel]

        st_sub = sub[sub['Is_Start']]
        st_duo = st_sub.groupby(['Mgr', 'Pl']).agg(
            Starts=('Wk', 'count'),
            Starter_Pts=('Pts', 'sum')
        ).reset_index()

        all_duo = sub.groupby(['Mgr', 'Pl']).agg(
            Pos=('Pos', lambda s: s.mode().iloc[0] if not s.mode().empty else ''),
            Seasons=('Szn', lambda s: ", ".join(str(y) for y in sorted(s.unique(), reverse=True))),
            Roster_Wks=('Wk', 'count'),
            Value_Score=('Wk_Val', 'sum')
        ).reset_index()

        duo_df = all_duo.merge(st_duo, on=['Mgr', 'Pl'], how='left')
        duo_df['Starts'] = duo_df['Starts'].fillna(0).astype(int)
        duo_df['Starter_Pts'] = duo_df['Starter_Pts'].fillna(0.0)
        duo_df['PPS'] = np.where(duo_df['Starts'] > 0, duo_df['Starter_Pts'] / duo_df['Starts'], 0.0)

        if duo_sort == "Total Starter Points Together":
            duo_df = duo_df.sort_values('Starter_Pts', ascending=False)
        elif duo_sort == "Total Value Score Together":
            duo_df = duo_df.sort_values('Value_Score', ascending=False)
        else:
            duo_df = duo_df.sort_values(['Starts', 'Starter_Pts'], ascending=[False, False])

        top_duo = duo_df.head(35).reset_index(drop=True)
        top_duo['Rank'] = top_duo.index + 1
        top_duo['Starter Pts'] = top_duo['Starter_Pts'].apply(lambda x: f"{x:,.1f}")
        top_duo['Pts / Start'] = top_duo['PPS'].apply(lambda x: f"{x:.1f}")
        top_duo['Value Score'] = top_duo['Value_Score'].apply(fmt_signed)
        disp = top_duo[['Rank', 'Mgr', 'Pl', 'Pos', 'Starts', 'Starter Pts', 'Pts / Start', 'Value Score', 'Seasons']].rename(
            columns={'Mgr': 'Manager', 'Pl': 'Player'}
        )
        render_table(disp, left_align_cols=['Player', 'Seasons'])

    elif player_view == "Player Records":
        import app as _app_mod
        _app_mod.render_player_records_section(box_df)
