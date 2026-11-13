import streamlit as st
import pandas as pd
import value_engine

AUSTIN_2018_TX_IDS = {
    '07665c7b-31c1-3522-becc-c8dbf658c6de', '1e73b042-7f5b-3a4b-b80f-9d36e5fce067',
    '2890ba27-3381-3a5c-9892-2c31d6da91f9', '350e6e9b-d32e-3807-9fd5-057ffb5bbffb',
    '37801877-9b94-3159-b82e-80427dc50d4a', '3931fa74-44a8-323b-b7ce-95351f30b6b0',
    '3c4fa8d5-993f-3c88-b831-9df38ea2e0de', '434c366a-687c-3069-9b7a-960915dd7c5f',
    '4a7c45f1-dc4e-309c-a861-61244658d160', '4bdcb8dd-621c-3044-8efd-15888e29ecb6',
    '5b09bfc2-a54c-3f90-a313-e6789320f1f2', '5e301ec0-6fbb-3de9-976b-36a143bdcbcd',
    '6076cc3e-b429-3a3c-8f84-c7d85c3686f1', '662979ff-51e9-3890-9b4e-2e1545316701',
    '6e8f8a1b-25af-38d0-acd3-e681629cdfc7', '7180c044-df2d-3e9b-abdb-0a14a734c3d4',
    '773fc339-c0d4-3778-90cb-e5a6d5d89118', '8589bd62-66f2-33f2-9f3a-3fcb2fcc4a89',
    '87fbb4bd-3979-313d-92f8-fee7233ebd9d', '905fe917-1afe-3513-956e-3b43530c2475',
    '9aa22c1f-0344-364a-84f8-7a5528ef0cc2', 'a23d7c63-5449-30ed-ad20-91240d1f4c23',
    'a497bf79-2c61-3bc0-9f69-b4b91366ea2d', 'aec2c9ce-d90d-300c-ac15-fd8a17bfdc77',
    'b1982b89-0996-35f7-9f9f-edb6aa108297', 'b3f803ab-66de-3c11-8936-31d701ed487b',
    'b714ce66-99d9-36b4-9342-09d90d22b37b', 'c2e1408d-27a9-3626-8902-90ed8b7d7fcf',
    'ccb7f748-d35a-3ba7-95f5-1eb832c517e4', 'ce702d35-d0bc-37e3-b27d-4f177718c957',
    'd09276c6-3304-365d-b5be-1318ed6698c4', 'd3033b54-12ea-31fc-b0f6-9fbd244640ae',
    'd4255d16-7423-34ef-85e3-19f06e19e34d', 'd6c0c156-f9b0-34fc-b71c-30868ed3f715',
    'd8fcf9e4-aff3-3255-a0a8-08bc08bb1a49', 'e41d9f37-9f2c-3dcf-8706-651690aec2ab',
    'e7b47bdf-7da1-3d6e-8dc1-3c9b921cda4b', 'f1f89d17-f8ff-3b5c-a970-dd532cd3ae9f',
    'fc185d7b-722a-33dd-9728-1252b7cb9d6c'
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
def fmt_signed(val):
    if pd.isna(val):
        return "-"
    return f"+{val:.1f}" if val > 0 else f"{val:.1f}"

def clean_2018_rows(df):
    if df.empty or 2018 not in df['Season'].values:
        return df

    df = df[df['Player'].astype(str).str.strip() != 'Player 100001'].copy()

    def fix_row(r):
        if int(r['Season']) != 2018:
            return r
        tx_id = str(r['Transaction_ID']).strip()
        pl = str(r['Player']).strip()
        tx_type = str(r['Type']).strip()
        init = str(r['Initiating_Team']).strip()
        frm = str(r['From_Team']).strip()
        to = str(r['To_Team']).strip()

        if tx_type == 'TRADE_ACCEPT':
            r['Status'] = 'EXECUTED'

        if init == 'Team -2147483648':
            init = to if to != 'Free Agency / Waivers' else frm

        if tx_id == '1116403b-4b04-35a2-a8d1-c6d3ddd25844':
            if pl in ['Cam Newton', 'Robby Anderson']:
                frm = 'Austin'
                if r['Action'] == 'TRADE':
                    to = 'Noah'
            elif pl in ['T.Y. Hilton', 'Chris Godwin']:
                frm = 'Noah'
                to = 'Austin'
            init = 'Austin'
        elif tx_id in AUSTIN_2018_TX_IDS:
            if init == 'Noah': init = 'Austin'
            if frm == 'Noah': frm = 'Austin'
            if to == 'Noah': to = 'Austin'

        r['Initiating_Team'] = init
        r['From_Team'] = frm
        r['To_Team'] = to
        return r

    return df.apply(fix_row, axis=1)

@st.cache_data(ttl=600)
def load_transactions_data(box_df=None):
    dfs = []
    try:
        df_merged = pd.read_excel("espn_transactions_2018_2026.xlsx", sheet_name="Transactions", engine="openpyxl")
        dfs.append(df_merged)
    except Exception:
        for fname in ["espn_transactions_2019_2026.xlsx", "espn_transactions_2018.xlsx"]:
            try:
                dfs.append(pd.read_excel(fname, sheet_name="Transactions", engine="openpyxl"))
            except Exception:
                pass

    if not dfs:
        return pd.DataFrame(), pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    df = df.drop_duplicates(subset=['Season', 'Transaction_ID', 'Action', 'Player']).copy()

    for col in ['Initiating_Team', 'From_Team', 'To_Team']:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str).str.strip().replace('1alexyoel15+', 'Matt')

    df['Season'] = pd.to_numeric(df['Season'], errors='coerce').fillna(0).astype(int)
    df['Week'] = pd.to_numeric(df['Week'], errors='coerce').fillna(0).astype(int)
    df['Bid_Amount'] = pd.to_numeric(df['Bid_Amount'], errors='coerce').fillna(0).astype(int)
    df['Player'] = df['Player'].fillna('').apply(value_engine.normalize_player_name)
    df['Position'] = df['Position'].fillna('').astype(str).str.strip()
    df['Status'] = df['Status'].fillna('').astype(str).str.strip()
    df['Type'] = df['Type'].fillna('').astype(str).str.strip()
    df['Action'] = df['Action'].fillna('').astype(str).str.strip()

    df = clean_2018_rows(df)

    trades_list = []
    seen_trade_pairs = set()

    exec_trades = df[(df['Type'] == 'TRADE_ACCEPT') & (df['Status'] == 'EXECUTED') & (df['Action'] == 'TRADE')]
    for tx_id, grp in exec_trades.groupby('Transaction_ID'):
        szn = int(grp['Season'].iloc[0])
        wk = int(grp['Week'].iloc[0])
        dt = str(grp['Date'].iloc[0]).split()[0]
        teams_involved = sorted(list(set(grp['From_Team'].tolist() + grp['To_Team'].tolist()) - {'', 'Free Agency / Waivers'}))
        if len(teams_involved) >= 2:
            t1, t2 = teams_involved[0], teams_involved[1]
            t1_gets = [f"{r['Player']} ({r['Position']})" for _, r in grp[grp['To_Team'] == t1].iterrows()]
            t2_gets = [f"{r['Player']} ({r['Position']})" for _, r in grp[grp['To_Team'] == t2].iterrows()]
            trades_list.append({
                'Season': szn,
                'Week': wk,
                'Date': dt,
                'Manager 1': t1,
                'Manager 1 Receives': ", ".join(t1_gets),
                'Manager 2': t2,
                'Manager 2 Receives': ", ".join(t2_gets),
                'Source': 'ESPN API'
            })
            for p in grp['Player'].unique():
                seen_trade_pairs.add((szn, wk, p))
                seen_trade_pairs.add((szn, wk + 1, p))

    if box_df is not None and not box_df.empty:
        name_c = 'Player_Name' if 'Player_Name' in box_df.columns else 'Player'
        pos_c = 'Position' if 'Position' in box_df.columns else ('Pos' if 'Pos' in box_df.columns else 'Slot')
        tm_c = 'Manager' if 'Manager' in box_df.columns else 'Team_Name'
        b_c = box_df.copy()
        b_c['Szn'] = pd.to_numeric(b_c['Season'].astype(str).str.replace(r'\.0$', '', regex=True), errors='coerce').fillna(0).astype(int)
        b_c['Wk'] = pd.to_numeric(b_c['Week'], errors='coerce').fillna(0).astype(int)
        b_c['Tm'] = b_c[tm_c].apply(value_engine.map_team_to_mgr)
        b_c['Pl'] = b_c[name_c].astype(str).str.strip()
        b_c['Pos_Clean'] = b_c[pos_c].astype(str).str.strip()

        exec_adds = df[(df['Status'] == 'EXECUTED') & (df['Action'] == 'ADD')]

        for szn in sorted(b_c['Szn'].unique()):
            if szn < 2018:
                continue
            szn_box = b_c[b_c['Szn'] == szn]
            weeks = sorted(szn_box['Wk'].unique())
            for i in range(len(weeks) - 1):
                w_prev, w_curr = weeks[i], weeks[i + 1]
                if w_curr - w_prev > 1:
                    continue
                r_prev = szn_box[szn_box['Wk'] == w_prev].set_index('Pl')[['Tm', 'Pos_Clean']].to_dict('index')
                r_curr = szn_box[szn_box['Wk'] == w_curr].set_index('Pl')[['Tm', 'Pos_Clean']].to_dict('index')

                swaps = {}
                for pl, curr_info in r_curr.items():
                    if pl in r_prev:
                        tm_old = r_prev[pl]['Tm']
                        tm_new = curr_info['Tm']
                        if tm_old != tm_new and (szn, w_curr, pl) not in seen_trade_pairs:
                            w_adds = exec_adds[
                                (exec_adds['Season'] == szn) &
                                (exec_adds['Week'].isin([w_prev, w_curr])) &
                                (exec_adds['To_Team'] == tm_new) &
                                (exec_adds['Player'] == pl)
                            ]
                            if w_adds.empty:
                                pair_key = tuple(sorted([tm_old, tm_new]))
                                swaps.setdefault(pair_key, {'t1_gets': [], 't2_gets': []})
                                lbl = f"{pl} ({curr_info['Pos_Clean']})"
                                if tm_new == pair_key[0]:
                                    swaps[pair_key]['t1_gets'].append(lbl)
                                else:
                                    swaps[pair_key]['t2_gets'].append(lbl)

                for (t1, t2), side_dict in swaps.items():
                    if side_dict['t1_gets'] and side_dict['t2_gets']:
                        trades_list.append({
                            'Season': szn,
                            'Week': w_curr,
                            'Date': f"{szn} W{w_curr}",
                            'Manager 1': t1,
                            'Manager 1 Receives': ", ".join(side_dict['t1_gets']),
                            'Manager 2': t2,
                            'Manager 2 Receives': ", ".join(side_dict['t2_gets']),
                            'Source': 'Roster Diff'
                        })

    trades_df = pd.DataFrame(trades_list)
    if not trades_df.empty:
        trades_df = trades_df.sort_values(['Season', 'Week'], ascending=[False, False]).reset_index(drop=True)

    return df, trades_df

def render(box_df=None):
    if box_df is None or box_df.empty:
        try:
            import app
            box_df = app.load_box_scores()
        except Exception:
            dfs_b = []
            for fn, sn in [("espn_fantasy_complete_stats_2017_2026.xlsx", "Box_Scores"), ("reconstructed_2018_box_scores.xlsx", "Box_Scores_2018")]:
                try:
                    dfs_b.append(pd.read_excel(fn, sheet_name=sn, engine="openpyxl"))
                except Exception:
                    pass
            if dfs_b:
                box_df = pd.concat(dfs_b, ignore_index=True)

    df, trades_df = load_transactions_data(box_df)
    if df.empty:
        st.warning("Could not load transaction data. Make sure 'espn_transactions_2019_2026.xlsx' and 'espn_transactions_2018.xlsx' are uploaded to the repository root.")
        return

    wva_df = value_engine.compute_waiver_value_added(df, box_df)
    tva_df = value_engine.compute_trade_value_added(trades_df, box_df)

    tx_view = st.radio(
        "Transactions View:",
        [
            "Manager Activity Leaderboard",
            "Waiver Value Added (WVA)",
            "Trade History & Value Added (TVA)",
            "Most Added & Dropped Players",
            "FAAB & Waiver Wire Battles",
            "Full Transaction Search"
        ],
        horizontal=True,
        key="tx_sub_view_v4"
    )
    st.write("---")

    seasons_avail = sorted(df['Season'].unique().tolist(), reverse=True)
    min_yr = min(seasons_avail) if seasons_avail else 2018
    max_yr = max(seasons_avail) if seasons_avail else 2026
    all_time_lbl = f"All-Time ({min_yr}–{max_yr})"

    exec_df = df[df['Status'] == 'EXECUTED'].copy()
    adds_df = exec_df[exec_df['Action'] == 'ADD'].copy()
    drops_df = exec_df[exec_df['Action'] == 'DROP'].copy()
    managers_list = sorted([m for m in adds_df['Initiating_Team'].unique() if m and m != 'Free Agency / Waivers'])

    # ================= VIEW 1: MANAGER LEADERBOARD =================
    if tx_view == "Manager Activity Leaderboard":
        sel_szn = st.selectbox("Select Season:", [all_time_lbl] + [str(s) for s in seasons_avail], key="tx_ldr_szn")
        is_all_time = sel_szn.startswith("All-Time")
        show_faab = is_all_time or (int(sel_szn) >= 2026)

        sub_adds = adds_df if is_all_time else adds_df[adds_df['Season'] == int(sel_szn)]
        sub_drops = drops_df if is_all_time else drops_df[drops_df['Season'] == int(sel_szn)]
        sub_trades = trades_df if (trades_df.empty or is_all_time) else trades_df[trades_df['Season'] == int(sel_szn)]
        sub_wva = wva_df if (wva_df.empty or is_all_time) else wva_df[wva_df['Season'] == int(sel_szn)]
        sub_tva = tva_df if (tva_df.empty or is_all_time) else tva_df[tva_df['Season'] == int(sel_szn)]

        rows = []
        for mgr in managers_list:
            m_adds = sub_adds[sub_adds['Initiating_Team'] == mgr]
            m_drops = sub_drops[sub_drops['Initiating_Team'] == mgr]
            w_adds = m_adds[m_adds['Type'] == 'WAIVER']
            fa_adds = m_adds[m_adds['Type'] == 'FREEAGENT']

            w_faab = w_adds[w_adds['Season'] >= 2026]
            faab_spent = w_faab.groupby('Transaction_ID')['Bid_Amount'].first().sum() if not w_faab.empty else 0
            max_bid = w_faab['Bid_Amount'].max() if not w_faab.empty else 0

            t_cnt = 0
            if not sub_trades.empty:
                t_cnt = len(sub_trades[(sub_trades['Manager 1'] == mgr) | (sub_trades['Manager 2'] == mgr)])

            tot_wva = sub_wva[sub_wva['Manager'] == mgr]['WVA'].sum() if not sub_wva.empty else 0.0
            tot_tva = 0.0
            if not sub_tva.empty:
                tot_tva = (
                    sub_tva[sub_tva['Manager 1'] == mgr]['M1_TVA'].sum() +
                    sub_tva[sub_tva['Manager 2'] == mgr]['M2_TVA'].sum()
                )

            row_dict = {
                'Manager': mgr,
                'Total Adds': len(m_adds),
                'FA Pickups': len(fa_adds),
                'Waiver Claims': len(w_adds),
                'Total Drops': len(m_drops),
                'Trades Completed': t_cnt,
                'Waiver Value Added': fmt_signed(tot_wva),
                'Trade Value Added': fmt_signed(tot_tva)
            }
            if show_faab:
                faab_col_lbl = 'FAAB Spent (2026+)' if is_all_time else 'FAAB Spent'
                max_col_lbl = 'Max Bid (2026+)' if is_all_time else 'Max Bid'
                row_dict[faab_col_lbl] = f"${int(faab_spent)}"
                row_dict[max_col_lbl] = f"${int(max_bid)}"

            rows.append(row_dict)

        ldr_df = pd.DataFrame(rows).sort_values('Total Adds', ascending=False).reset_index(drop=True)
        ldr_df['Rank'] = ldr_df.index + 1
        base_cols = ['Rank', 'Manager', 'Total Adds', 'FA Pickups', 'Waiver Claims', 'Total Drops', 'Trades Completed', 'Waiver Value Added', 'Trade Value Added']
        if show_faab:
            faab_col_lbl = 'FAAB Spent (2026+)' if is_all_time else 'FAAB Spent'
            max_col_lbl = 'Max Bid (2026+)' if is_all_time else 'Max Bid'
            base_cols += [faab_col_lbl, max_col_lbl]
        render_table(ldr_df[base_cols])

    # ================= VIEW 2: WAIVER VALUE ADDED (WVA) =================
    elif tx_view == "Waiver Value Added (WVA)":
        st.caption(
            "**Waiver Value Added (WVA)** measures starter points above positional replacement generated after picking a player up "
            "(minus -0.5 pt/wk for healthy bench weeks and an acquisition hurdle of 0.0 pts for FA adds, 3.0 pts for pre-2026 priority waivers, and 0.40 pts per $1 of FAAB)."
        )
        if wva_df.empty:
            st.info("Box score data is required to compute Waiver Value Added.")
            return

        wva_mode = st.radio(
            "Select WVA View:",
            [
                "Best Pickups (Top WVA)",
                "Worst Pickups & Overpays (Lowest WVA)",
                "Manager Waiver Efficiency"
            ],
            horizontal=True,
            key="wva_mode_sel"
        )

        c1, c2, c3 = st.columns(3)
        sel_szn = c1.selectbox("Season:", [all_time_lbl] + [str(s) for s in seasons_avail], key="wva_szn")
        sel_pos = c2.selectbox("Position:", ["Skill Players (QB/RB/WR/TE)", "All Positions", "QB", "RB", "WR", "TE", "D/ST", "K"], key="wva_pos")
        sel_mgr = c3.selectbox("Manager:", ["All Managers"] + managers_list, key="wva_mgr")

        sub = wva_df.copy()
        if not sel_szn.startswith("All-Time"):
            sub = sub[sub['Season'] == int(sel_szn)]
        if sel_pos == "Skill Players (QB/RB/WR/TE)":
            sub = sub[~sub['Pos'].isin(['D/ST', 'K'])]
        elif sel_pos != "All Positions":
            sub = sub[sub['Pos'] == sel_pos]
        if sel_mgr != "All Managers":
            sub = sub[sub['Manager'] == sel_mgr]

        if wva_mode in ["Best Pickups (Top WVA)", "Worst Pickups & Overpays (Lowest WVA)"]:
            asc = (wva_mode == "Worst Pickups & Overpays (Lowest WVA)")
            ranked = sub.sort_values('WVA', ascending=asc).head(30).reset_index(drop=True)
            ranked['Rank'] = ranked.index + 1
            ranked['Pts / Start'] = ranked['Pts_Per_Start'].apply(lambda x: f"{x:.1f}")
            ranked['WVA_Str'] = ranked['WVA'].apply(fmt_signed)
            ranked['Cost Hurdle'] = ranked['Hurdle'].apply(lambda x: f"{x:.1f}")
            disp = ranked[['Rank', 'Season', 'Week', 'Manager', 'Player', 'Pos', 'Acquisition', 'Starts', 'Pts / Start', 'Pos_Rank', 'Cost Hurdle', 'WVA_Str']].rename(
                columns={'Pos_Rank': 'Pos Rank', 'WVA_Str': 'Waiver Value Added'}
            )
            render_table(disp, left_align_cols=['Player'])
        else:
            m_rows = []
            for mgr in managers_list:
                m_sub = sub[sub['Manager'] == mgr]
                if m_sub.empty:
                    continue
                tot_wva = m_sub['WVA'].sum()
                avg_wva = m_sub['WVA'].mean()
                starts_gen = int(m_sub['Starts'].sum())
                best_r = m_sub.loc[m_sub['WVA'].idxmax()]
                m_rows.append({
                    'Manager': mgr,
                    'Pickups': len(m_sub),
                    'Starts Generated': starts_gen,
                    'WVA_Num': tot_wva,
                    'Total WVA': fmt_signed(tot_wva),
                    'Avg WVA / Pickup': fmt_signed(avg_wva),
                    'Best Pickup': f"{best_r['Player']} ({int(best_r['Season'])} W{int(best_r['Week'])}, {fmt_signed(best_r['WVA'])})"
                })
            m_df = pd.DataFrame(m_rows).sort_values('WVA_Num', ascending=False).reset_index(drop=True)
            m_df['Rank'] = m_df.index + 1
            render_table(m_df[['Rank', 'Manager', 'Pickups', 'Starts Generated', 'Total WVA', 'Avg WVA / Pickup', 'Best Pickup']], left_align_cols=['Best Pickup'])

    # ================= VIEW 3: TRADE HISTORY & VALUE ADDED (TVA) =================
    elif tx_view == "Trade History & Value Added (TVA)":
        st.caption(
            "**Trade Value Added (TVA)** compares post-trade starter value over positional replacement generated by each side, "
            "including each acquired player's starts, Pts/Start, and positional rank, plus a roster-spot consolidation adjustment on uneven trades (2-for-1, 3-for-2)."
        )
        t_mode = st.radio(
            "Select Trade View:",
            [
                "Complete Trade Log & TVA Grades",
                "Most Lopsided Trades (Biggest TVA Swings)",
                "Manager Trade Value Leaderboard"
            ],
            horizontal=True,
            key="tva_mode_sel"
        )

        base_t = tva_df if not tva_df.empty else trades_df
        if base_t.empty:
            st.info("No trades found.")
            return

        if t_mode in ["Complete Trade Log & TVA Grades", "Most Lopsided Trades (Biggest TVA Swings)"]:
            c1, c2 = st.columns(2)
            t_szn = c1.selectbox("Filter by Season:", ["All Seasons"] + [str(s) for s in sorted(base_t['Season'].unique(), reverse=True)], key="tr_szn")
            t_mgr = c2.selectbox("Filter by Manager:", ["All Managers"] + managers_list, key="tr_mgr")

            sub_t = base_t.copy()
            if t_szn != "All Seasons":
                sub_t = sub_t[sub_t['Season'] == int(t_szn)]
            if t_mgr != "All Managers":
                sub_t = sub_t[(sub_t['Manager 1'] == t_mgr) | (sub_t['Manager 2'] == t_mgr)]

            if "Win_Margin" in sub_t.columns:
                if t_mode == "Most Lopsided Trades (Biggest TVA Swings)":
                    sub_t = sub_t.sort_values('Win_Margin', ascending=False).head(25).reset_index(drop=True)
                sub_t['M1 Value'] = sub_t['M1_Val'].apply(fmt_signed)
                sub_t['M2 Value'] = sub_t['M2_Val'].apply(fmt_signed)
                render_table(
                    sub_t[['Season', 'Week', 'Manager 1', 'Manager 1 Receives', 'M1 Value', 'Manager 2', 'Manager 2 Receives', 'M2 Value', 'Trade Winner']],
                    left_align_cols=['Manager 1 Receives', 'Manager 2 Receives']
                )
            else:
                render_table(
                    sub_t[['Season', 'Week', 'Manager 1', 'Manager 1 Receives', 'Manager 2', 'Manager 2 Receives']],
                    left_align_cols=['Manager 1 Receives', 'Manager 2 Receives']
                )
        else:
            if tva_df.empty:
                st.info("Box score data is required to compute Manager Trade Value Added.")
            else:
                tm_rows = []
                for mgr in managers_list:
                    m1_sub = tva_df[tva_df['Manager 1'] == mgr]
                    m2_sub = tva_df[tva_df['Manager 2'] == mgr]
                    trades_cnt = len(m1_sub) + len(m2_sub)
                    net_tva = m1_sub['M1_TVA'].sum() + m2_sub['M2_TVA'].sum()
                    wins = int((m1_sub['M1_TVA'] > 1.0).sum() + (m2_sub['M2_TVA'] > 1.0).sum())
                    losses = int((m1_sub['M1_TVA'] < -1.0).sum() + (m2_sub['M2_TVA'] < -1.0).sum())
                    avg_tva = net_tva / trades_cnt if trades_cnt > 0 else 0.0
                    tm_rows.append({
                        'Manager': mgr,
                        'Trades': trades_cnt,
                        'Trade Record (W-L)': f"{wins}-{losses}",
                        'TVA_Num': net_tva,
                        'Net Trade Value Added': fmt_signed(net_tva),
                        'Avg TVA / Trade': fmt_signed(avg_tva)
                    })
                tm_df = pd.DataFrame(tm_rows).sort_values('TVA_Num', ascending=False).reset_index(drop=True)
                tm_df['Rank'] = tm_df.index + 1
                render_table(tm_df[['Rank', 'Manager', 'Trades', 'Trade Record (W-L)', 'Net Trade Value Added', 'Avg TVA / Trade']])

    # ================= VIEW 4: MOST ADDED & DROPPED PLAYERS =================
    elif tx_view == "Most Added & Dropped Players":
        c1, c2, c3 = st.columns(3)
        sel_szn = c1.selectbox("Season:", [all_time_lbl] + [str(s) for s in seasons_avail], key="tx_pop_szn")
        pos_filter = c2.selectbox("Position Filter:", ["Non-D/ST & K (Skill Players)", "All Positions", "QB", "RB", "WR", "TE", "D/ST", "K"], key="tx_pop_pos")
        act_filter = c3.radio("Action:", ["Most Added", "Most Dropped"], horizontal=True, key="tx_pop_act")

        base = adds_df if act_filter == "Most Added" else drops_df
        if not sel_szn.startswith("All-Time"):
            base = base[base['Season'] == int(sel_szn)]

        if pos_filter == "Non-D/ST & K (Skill Players)":
            base = base[~base['Position'].isin(['D/ST', 'K'])]
        elif pos_filter != "All Positions":
            base = base[base['Position'] == pos_filter]

        tm_col = 'To_Team' if act_filter == "Most Added" else 'From_Team'
        lbl_cnt = 'Times Added' if act_filter == "Most Added" else 'Times Dropped'

        pop = base.groupby(['Player', 'Position']).agg(
            Count=('Transaction_ID', 'count'),
            Unique_Managers=(tm_col, 'nunique'),
            Managers=(tm_col, lambda s: ", ".join(f"{k} ({v}x)" if v > 1 else k for k, v in s.value_counts().items()))
        ).reset_index().sort_values(['Count', 'Unique_Managers'], ascending=[False, False]).head(25).reset_index(drop=True)

        pop['Rank'] = pop.index + 1
        pop = pop.rename(columns={'Position': 'Pos', 'Count': lbl_cnt, 'Unique_Managers': 'Unique Managers', 'Managers': 'Managers Involved'})
        render_table(pop[['Rank', 'Player', 'Pos', lbl_cnt, 'Unique Managers', 'Managers Involved']], left_align_cols=['Player', 'Managers Involved'])

    # ================= VIEW 5: FAAB & WAIVER WIRE BATTLES =================
    elif tx_view == "FAAB & Waiver Wire Battles":
        mode = st.radio(
            "Select Waiver View:",
            [
                "FAAB Bidding Wars (2026+)",
                "Largest Winning FAAB Bids (2026+)",
                f"Priority Waiver Fights ({min_yr}–2025)"
            ],
            horizontal=True,
            key="tx_faab_mode"
        )

        if mode == "FAAB Bidding Wars (2026+)":
            st.write("#### 2026+ Contested FAAB Bidding Wars (Multiple Managers Bidding on the Same Player)")
            w_2026 = df[(df['Season'] >= 2026) & (df['Type'] == 'WAIVER') & (df['Action'] == 'ADD') & (df['Status'].isin(['EXECUTED', 'FAILED_INVALIDPLAYERSOURCE']))].copy()
            w_2026_dedup = w_2026.sort_values(['Status', 'Bid_Amount'], ascending=[True, False]).drop_duplicates(subset=['Season', 'Week', 'Player', 'To_Team'])

            faab_wars = []
            for (szn, wk, pl), grp in w_2026_dedup.groupby(['Season', 'Week', 'Player']):
                if len(grp) > 1 and ('EXECUTED' in grp['Status'].values):
                    win_row = grp[grp['Status'] == 'EXECUTED'].iloc[0]
                    losers = grp[(grp['Status'] != 'EXECUTED') & (grp['To_Team'] != win_row['To_Team'])].sort_values('Bid_Amount', ascending=False)
                    if not losers.empty:
                        loser_strs = [f"{r['To_Team']} (${int(r['Bid_Amount'])})" for _, r in losers.iterrows()]
                        faab_wars.append({
                            'Season': szn,
                            'Week': wk,
                            'Player': pl,
                            'Pos': win_row['Position'],
                            'Winner': win_row['To_Team'],
                            'Winning_Bid_Num': int(win_row['Bid_Amount']),
                            'Winning Bid': f"${int(win_row['Bid_Amount'])}",
                            'Bidders': 1 + len(losers),
                            'Outbid Managers': ", ".join(loser_strs)
                        })
            if faab_wars:
                fw_df = pd.DataFrame(faab_wars).sort_values(['Season', 'Winning_Bid_Num', 'Bidders'], ascending=[False, False, False]).reset_index(drop=True)
                render_table(fw_df[['Season', 'Week', 'Player', 'Pos', 'Winner', 'Winning Bid', 'Bidders', 'Outbid Managers']], left_align_cols=['Player', 'Outbid Managers'])
            else:
                st.info("No contested FAAB bidding wars found.")

        elif mode == "Largest Winning FAAB Bids (2026+)":
            st.write("#### Largest Winning FAAB Bids (2026+)")
            w_wins = adds_df[(adds_df['Type'] == 'WAIVER') & (adds_df['Season'] >= 2026)].sort_values(['Bid_Amount', 'Season', 'Week'], ascending=[False, False, False]).head(25).reset_index(drop=True)
            if not w_wins.empty:
                w_wins['Rank'] = w_wins.index + 1
                w_wins['Bid'] = w_wins['Bid_Amount'].apply(lambda x: f"${int(x)}")
                disp = w_wins[['Rank', 'Season', 'Week', 'To_Team', 'Player', 'Position', 'Bid', 'Date']].rename(columns={'To_Team': 'Manager', 'Position': 'Pos'})
                render_table(disp, left_align_cols=['Player'])
            else:
                st.info("No FAAB bids recorded.")

        else:
            st.write(f"#### Pre-FAAB Priority Waiver Fights ({min_yr}–2025)")
            st.caption("Weeks where multiple managers submitted a waiver claim for the same player and the manager with higher waiver priority won the claim.")
            pre_szns = sorted([s for s in seasons_avail if s <= 2025], reverse=True)
            sel_pre_szn = st.selectbox("Filter Season:", [f"All Pre-FAAB Seasons ({min_yr}–2025)"] + [str(s) for s in pre_szns], key="tx_pre_waiv_szn")

            w_pre = df[
                (df['Season'] <= 2025) &
                (df['Type'] == 'WAIVER') &
                (df['Action'] == 'ADD') &
                (
                    (df['Status'] == 'EXECUTED') |
                    (df['Status'] == 'FAILED_INVALIDPLAYERSOURCE') |
                    ((df['Season'] == 2018) & (df['Status'].isin(['PENDING', 'FAILED_MATCHUPACQUISITIONLIMIT'])))
                )
            ].copy()

            if not sel_pre_szn.startswith("All"):
                w_pre = w_pre[w_pre['Season'] == int(sel_pre_szn)]

            w_pre['is_exec'] = (w_pre['Status'] == 'EXECUTED').astype(int)
            w_pre_dedup = w_pre.sort_values('is_exec', ascending=False).drop_duplicates(subset=['Season', 'Week', 'Player', 'To_Team'])

            fights = []
            for (szn, wk, pl), grp in w_pre_dedup.groupby(['Season', 'Week', 'Player']):
                if len(grp) > 1 and ('EXECUTED' in grp['Status'].values):
                    win_row = grp[grp['Status'] == 'EXECUTED'].iloc[0]
                    losers = [m for m in grp[grp['Status'] != 'EXECUTED']['To_Team'].tolist() if m != win_row['To_Team']]
                    if losers:
                        fights.append({
                            'Season': szn,
                            'Week': wk,
                            'Player': pl,
                            'Pos': win_row['Position'],
                            'Priority Winner': win_row['To_Team'],
                            'Total Claimants': 1 + len(losers),
                            'Denied Claimants (Lower Priority)': ", ".join(losers)
                        })
            if fights:
                f_df = pd.DataFrame(fights).sort_values(['Total Claimants', 'Season', 'Week'], ascending=[False, False, False]).reset_index(drop=True)
                render_table(
                    f_df[['Season', 'Week', 'Player', 'Pos', 'Priority Winner', 'Total Claimants', 'Denied Claimants (Lower Priority)']],
                    left_align_cols=['Player', 'Denied Claimants (Lower Priority)']
                )
            else:
                st.info("No contested priority waiver claims found for the selected filter.")

    # ================= VIEW 6: FULL TRANSACTION SEARCH =================
    elif tx_view == "Full Transaction Search":
        c1, c2, c3 = st.columns(3)
        s_szn = c1.selectbox("Season:", ["All Seasons"] + [str(s) for s in seasons_avail], key="fs_szn")
        s_mgr = c2.selectbox("Manager:", ["All Managers"] + managers_list, key="fs_mgr")
        s_player = c3.text_input("Search Player Name:", "", key="fs_pl")

        sub = exec_df[exec_df['Action'].isin(['ADD', 'DROP', 'TRADE'])].copy()
        if s_szn != "All Seasons":
            sub = sub[sub['Season'] == int(s_szn)]
        if s_mgr != "All Managers":
            sub = sub[(sub['Initiating_Team'] == s_mgr) | (sub['From_Team'] == s_mgr) | (sub['To_Team'] == s_mgr)]
        if s_player.strip():
            sub = sub[sub['Player'].str.contains(s_player.strip(), case=False, na=False)]

        sub['FAAB Bid'] = sub.apply(
            lambda r: f"${int(r['Bid_Amount'])}" if (int(r['Season']) >= 2026 and r['Type'] == 'WAIVER' and r['Action'] == 'ADD') else "-",
            axis=1
        )
        disp = sub[['Season', 'Week', 'Date', 'Initiating_Team', 'Type', 'Action', 'Player', 'Position', 'From_Team', 'To_Team', 'FAAB Bid']].head(200).rename(
            columns={'Initiating_Team': 'Manager', 'Position': 'Pos', 'From_Team': 'From', 'To_Team': 'To'}
        )
        render_table(disp, left_align_cols=['Player'])
        
