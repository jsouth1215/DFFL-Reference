import streamlit as st
import pandas as pd

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
def load_transactions_data(box_df=None):
    try:
        df = pd.read_excel("espn_transactions_2019_2026.xlsx", sheet_name="Transactions", engine="openpyxl")
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

    for col in ['Initiating_Team', 'From_Team', 'To_Team']:
        if col in df.columns:
            df[col] = df[col].fillna('').astype(str).str.strip().replace('1alexyoel15+', 'Matt')

    df['Season'] = pd.to_numeric(df['Season'], errors='coerce').fillna(0).astype(int)
    df['Week'] = pd.to_numeric(df['Week'], errors='coerce').fillna(0).astype(int)
    df['Bid_Amount'] = pd.to_numeric(df['Bid_Amount'], errors='coerce').fillna(0).astype(int)
    df['Player'] = df['Player'].fillna('').astype(str).str.strip()
    df['Position'] = df['Position'].fillna('').astype(str).str.strip()
    df['Status'] = df['Status'].fillna('').astype(str).str.strip()
    df['Type'] = df['Type'].fillna('').astype(str).str.strip()
    df['Action'] = df['Action'].fillna('').astype(str).str.strip()

    trades_list = []
    seen_trade_pairs = set()

    # 1. Explicit EXECUTED trades from API
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

    # 2. Backfill redacted trades via week-over-week Box_Scores roster diffs
    if box_df is not None and not box_df.empty:
        name_c = 'Player_Name' if 'Player_Name' in box_df.columns else 'Player'
        pos_c = 'Position' if 'Position' in box_df.columns else ('Pos' if 'Pos' in box_df.columns else 'Slot')
        b_c = box_df.copy()
        b_c['Szn'] = pd.to_numeric(b_c['Season'].astype(str).str.replace(r'\.0$', '', regex=True), errors='coerce').fillna(0).astype(int)
        b_c['Wk'] = pd.to_numeric(b_c['Week'], errors='coerce').fillna(0).astype(int)
        b_c['Tm'] = b_c['Team_Name'].astype(str).str.strip().replace('1alexyoel15+', 'Matt')
        b_c['Pl'] = b_c[name_c].astype(str).str.strip()
        b_c['Pos_Clean'] = b_c[pos_c].astype(str).str.strip()

        exec_adds = df[(df['Status'] == 'EXECUTED') & (df['Action'] == 'ADD')]

        for szn in sorted(b_c['Szn'].unique()):
            if szn < 2019:
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
    df, trades_df = load_transactions_data(box_df)
    if df.empty:
        st.warning("Could not load 'espn_transactions_2019_2026.xlsx'. Make sure it is uploaded to the repository root.")
        return

    tx_view = st.radio(
        "Transactions View:",
        [
            "📊 Manager Activity Leaderboard",
            "🔥 Most Added & Dropped Players",
            "💰 FAAB & Waiver Wire Battles",
            "🤝 Trade History Log",
            "📜 Full Transaction Search"
        ],
        horizontal=True,
        key="tx_sub_view"
    )
    st.write("---")

    seasons_avail = sorted(df['Season'].unique().tolist(), reverse=True)
    exec_df = df[df['Status'] == 'EXECUTED'].copy()
    adds_df = exec_df[exec_df['Action'] == 'ADD'].copy()
    drops_df = exec_df[exec_df['Action'] == 'DROP'].copy()
    managers_list = sorted([m for m in adds_df['Initiating_Team'].unique() if m and m != 'Free Agency / Waivers'])

    # ================= VIEW 1: MANAGER LEADERBOARD =================
    if tx_view == "📊 Manager Activity Leaderboard":
        sel_szn = st.selectbox("Select Season:", ["All-Time (2019–2026)"] + [str(s) for s in seasons_avail], key="tx_ldr_szn")
        is_all_time = sel_szn.startswith("All-Time")
        show_faab = is_all_time or (int(sel_szn) >= 2026)

        sub_adds = adds_df if is_all_time else adds_df[adds_df['Season'] == int(sel_szn)]
        sub_drops = drops_df if is_all_time else drops_df[drops_df['Season'] == int(sel_szn)]
        sub_trades = trades_df if (trades_df.empty or is_all_time) else trades_df[trades_df['Season'] == int(sel_szn)]

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

            row_dict = {
                'Manager': mgr,
                'Total Adds': len(m_adds),
                'FA Pickups': len(fa_adds),
                'Waiver Claims': len(w_adds),
                'Total Drops': len(m_drops),
                'Trades Completed': t_cnt,
            }
            if show_faab:
                faab_col_lbl = 'FAAB Spent (2026+)' if is_all_time else 'FAAB Spent'
                max_col_lbl = 'Max Bid (2026+)' if is_all_time else 'Max Bid'
                row_dict[faab_col_lbl] = f"${int(faab_spent)}"
                row_dict[max_col_lbl] = f"${int(max_bid)}"

            rows.append(row_dict)

        ldr_df = pd.DataFrame(rows).sort_values('Total Adds', ascending=False).reset_index(drop=True)
        ldr_df['Rank'] = ldr_df.index + 1
        base_cols = ['Rank', 'Manager', 'Total Adds', 'FA Pickups', 'Waiver Claims', 'Total Drops', 'Trades Completed']
        if show_faab:
            faab_col_lbl = 'FAAB Spent (2026+)' if is_all_time else 'FAAB Spent'
            max_col_lbl = 'Max Bid (2026+)' if is_all_time else 'Max Bid'
            base_cols += [faab_col_lbl, max_col_lbl]
        render_table(ldr_df[base_cols])

    # ================= VIEW 2: MOST ADDED & DROPPED PLAYERS =================
    elif tx_view == "🔥 Most Added & Dropped Players":
        c1, c2, c3 = st.columns(3)
        sel_szn = c1.selectbox("Season:", ["All-Time (2019–2026)"] + [str(s) for s in seasons_avail], key="tx_pop_szn")
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

    # ================= VIEW 3: FAAB & WAIVER WIRE BATTLES =================
    elif tx_view == "💰 FAAB & Waiver Wire Battles":
        mode = st.radio(
            "Select Waiver View:",
            [
                "FAAB Bidding Wars (2026+)",
                "Largest Winning FAAB Bids (2026+)",
                "Priority Waiver Fights (2019–2025)"
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

        elif mode == "Priority Waiver Fights (2019–2025)":
            st.write("#### Pre-FAAB Priority Waiver Fights (2019–2025)")
            st.caption("Weeks where multiple managers submitted a waiver claim for the same player and the manager with higher waiver priority won the claim.")
            pre_szns = sorted([s for s in seasons_avail if s <= 2025], reverse=True)
            sel_pre_szn = st.selectbox("Filter Season:", ["All Pre-FAAB Seasons (2019–2025)"] + [str(s) for s in pre_szns], key="tx_pre_waiv_szn")

            w_pre = df[(df['Season'] <= 2025) & (df['Type'] == 'WAIVER') & (df['Action'] == 'ADD') & (df['Status'].isin(['EXECUTED', 'FAILED_INVALIDPLAYERSOURCE']))].copy()
            if not sel_pre_szn.startswith("All"):
                w_pre = w_pre[w_pre['Season'] == int(sel_pre_szn)]

            w_pre_dedup = w_pre.sort_values('Status').drop_duplicates(subset=['Season', 'Week', 'Player', 'To_Team'])
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

    # ================= VIEW 4: TRADE HISTORY LOG =================
    elif tx_view == "🤝 Trade History Log":
        st.write("#### Complete League Trade History (2019–2026)")
        if not trades_df.empty:
            c1, c2 = st.columns(2)
            t_szn = c1.selectbox("Filter by Season:", ["All Seasons"] + [str(s) for s in sorted(trades_df['Season'].unique(), reverse=True)], key="tr_szn")
            t_mgr = c2.selectbox("Filter by Manager:", ["All Managers"] + managers_list, key="tr_mgr")

            sub_t = trades_df.copy()
            if t_szn != "All Seasons":
                sub_t = sub_t[sub_t['Season'] == int(t_szn)]
            if t_mgr != "All Managers":
                sub_t = sub_t[(sub_t['Manager 1'] == t_mgr) | (sub_t['Manager 2'] == t_mgr)]

            render_table(
                sub_t[['Season', 'Week', 'Manager 1', 'Manager 1 Receives', 'Manager 2', 'Manager 2 Receives']],
                left_align_cols=['Manager 1 Receives', 'Manager 2 Receives']
            )
        else:
            st.info("No trades found.")

    # ================= VIEW 5: FULL TRANSACTION SEARCH =================
    elif tx_view == "📜 Full Transaction Search":
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
        
