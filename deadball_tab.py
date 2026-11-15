import streamlit as st
import pandas as pd

POS_COLORS = {
    'RB': ('#cfe2f3', '#0b5394'),
    'WR': ('#d9ead3', '#274e13'),
    'QB': ('#f4cccc', '#783f04'),
    'TE': ('#fce5cd', '#b45f06'),
    'D/ST': ('#d9d2e9', '#351c75'),
    'K': ('#efefef', '#444444')
}

def render_table(df, left_align_cols=None):
    if df is None or df.empty:
        return
    df = df.loc[:, ~df.columns.duplicated()].reset_index(drop=True).copy()
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
                'max-width': '440px',
                'line-height': '1.35'
            })
    styled_html = styler.set_table_styles([
        {'selector': 'th', 'props': [
            ('text-align', 'center'), ('padding', '8px 10px'),
            ('border', '1px solid #cbd5e1'), ('background-color', '#f8fafc'),
            ('color', '#0f172a'), ('font-weight', '700'), ('font-size', '13px')
        ]},
        {'selector': 'tbody tr:nth-child(even)', 'props': [('background-color', '#fcfcfd')]},
        {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse'), ('margin', '0')]}
    ]).to_html()
    st.markdown(f'<div style="width:100%; overflow-x:auto; margin:6px 0 18px 0; border:1px solid #e2e8f0; border-radius:8px; background:#fff;">{styled_html}</div>', unsafe_allow_html=True)

@st.cache_data(ttl=60)
def load_deadball_data_v6():
    out = {}
    try:
        xls = pd.ExcelFile("deadball_era_data.xlsx", engine="openpyxl")
        for sh in xls.sheet_names:
            out[sh] = pd.read_excel(xls, sheet_name=sh)
    except Exception:
        pass
    return out

def get_confidence_badge(yr, wk, m1, m2):
    yr_i, wk_i = int(yr), int(wk)
    if yr_i == 2012:
        if wk_i <= 13:
            return "[Official] Dec 2012 Stat Sheet"
        return "[Official] 2012 Playoff Bracket"
    if wk_i <= 7:
        return "[Official] ESPN Tuesday Recap"
    if m1 == "Jack" or m2 == "Jack":
        return "[High-Confidence] Thu Email Lineup + NFL Actuals"
    return "[Estimated] Mirrored Schedule + Roster Solver"

def render():
    st.markdown("### The Deadball Era Archive (2011-2014)")
    st.caption(
        "Historical archive from the league's early 12-team seasons (2011-2014). "
        "In 2011, 12 solo managers competed across 12 teams. From 2012 to 2014, 13 managers competed for 12 franchise spots, with the two bottom consolation finishers from the prior year co-managing a shared franchise."
    )

    data = load_deadball_data_v6()
    if not data:
        st.warning("Upload `deadball_era_data.xlsx` to the repository root to view the Deadball Era archive.")
        return

    sub_view = st.radio(
        "Deadball Era View:",
        [
            "Season Standings & Summary (2011-2014)",
            "Deadball Draft Boards (2012-2014)",
            "Team Schedules & Season Logs (2012 & 2014)",
            "Weekly Scoreboards & Box Scores (2012 & 2014)",
            "Waiver, Free Agency & Activity Logs (2012 & 2014)",
            "Trade & Proposal Archive (2011-2014)"
        ],
        horizontal=True,
        key="deadball_sub_view"
    )
    st.write("---")

    if sub_view == "Season Standings & Summary (2011-2014)":
        st.markdown(
            "#### Deadball Era Champions & Shared Franchises\n"
            "* **2011 Season:** **Matt** won the inaugural championship. *(12 solo managers; no shared franchises)*\n"
            "* **2012 Season:** **Matt** won back-to-back titles as the #6 seed (`6-7-0`, `1,190 PF`), defeating **Lukas**, **Noah**, and **Sean**. **Eli** (`10-3-0`, `1,429 PF`) won the regular-season scoring title. *(Shared Franchise: **Jack & Austin**)*\n"
            "* **2013 Season:** **Max & Keith** won the league championship, advancing out of a Semifinal field with **Jack**, **Cav**, and **Austin**. *(Shared Franchise: **Max & Keith**)*\n"
            "* **2014 Season:** **David** (`10-3-0`) won the championship, defeating **Jack** (`9-4-0`) in the Week 16 Final. *(Shared Franchise: **Cam & Eli**)*"
        )
        st_df = data.get("Standings_2012_2014", pd.DataFrame())
        if not st_df.empty:
            yr_sel = st.selectbox("Select Season Standings:", [2014, 2013, 2012], key="db_st_yr")
            sub_st = st_df[st_df["Season"] == int(yr_sel)][["Season", "Finish", "Seed", "Manager", "Record", "Notes"]]
            render_table(sub_st, left_align_cols=["Notes"])

    elif sub_view == "Deadball Draft Boards (2012-2014)":
        d_df = data.get("Drafts_2012_2014", pd.DataFrame())
        if d_df.empty:
            st.info("No draft data found.")
            return
        sel_yr = st.selectbox("Select Draft Year:", [2014, 2013, 2012], key="db_draft_yr")
        if int(sel_yr) == 2013:
            st.caption("2013 Offline Draft: Ordered by the official 2013 draft order (1. CJ through 12. Max/Keith) and post-draft roster entry.")

        yr_df = d_df[d_df["Year"] == int(sel_yr)].copy()
        r1 = yr_df[yr_df["Round"] == 1].sort_values("Draft Slot")
        draft_order = r1["Team"].tolist()
        max_round = int(yr_df["Round"].max())
        lookup = {(int(r["Round"]), str(r["Team"])): r for _, r in yr_df.iterrows()}

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
                    pos = str(pick_row["Position"])
                    bg, fg = POS_COLORS.get(pos, ("#ffffff", "#111111"))
                    p_name = str(pick_row["Player"])
                    ov = int(pick_row["Overall Pick"])
                    rp = int(pick_row["Round Pick"])
                    arrow = "->" if r_num % 2 == 1 else "<-"
                    cells += (
                        f'<td style="border: 1px solid #ccc; background-color: {bg}; color: {fg}; padding: 5px 6px; text-align: left; vertical-align: top; min-width: 115px;">'
                        f'<div style="font-size: 10px; opacity: 0.75; display: flex; justify-content: space-between;">'
                        f'<span>{r_num}.{rp:02d} ({arrow})</span><span>#{ov}</span></div>'
                        f'<div style="font-weight: 700; font-size: 12.5px; line-height: 1.2; margin: 2px 0;">{p_name}</div>'
                        f'<div style="font-size: 11px; font-weight: 600;">{pos}</div></td>'
                    )
                else:
                    cells += '<td style="border: 1px solid #ccc; background-color: #fff;">-</td>'
            rows_html.append(f"<tr>{cells}</tr>")

        st.markdown(
            '<div style="overflow-x: auto; margin-top: 10px; border: 1px solid #e2e8f0; border-radius: 8px;">'
            f'<table style="width: 100%; border-collapse: collapse;"><thead><tr>{header_cells}</tr></thead>'
            f'<tbody>{"".join(rows_html)}</tbody></table></div>',
            unsafe_allow_html=True
        )

    elif sub_view == "Team Schedules & Season Logs (2012 & 2014)":
        c_yr_s, c_tm1, c_tm2 = st.columns([1.0, 1.2, 2.5])
        sel_sched_yr = c_yr_s.selectbox("Select Season:", [2014, 2012], key="db_sched_yr_sel")
        m_df = data.get("Matchups_2014" if int(sel_sched_yr) == 2014 else "Matchups_2012", pd.DataFrame())
        b14_df = data.get("Box_Scores_2014" if int(sel_sched_yr) == 2014 else "Box_Scores_2012", pd.DataFrame())
        if m_df.empty:
            st.info(f"No {sel_sched_yr} matchup data found.")
            return

        all_mgrs = (
            ["Jack", "David", "Keith", "Cam/Eli", "Cav", "Austin", "Sean", "CJ", "Noah", "Matt", "Lukas", "Max"]
            if int(sel_sched_yr) == 2014 else
            ["Eli", "Noah", "Lukas", "Sean", "Cav", "Matt", "David", "Cam", "CJ", "Keith", "Max", "Jack/Austin"]
        )
        sel_mgr = c_tm1.selectbox(f"Select {sel_sched_yr} Franchise:", all_mgrs, key=f"db_{sel_sched_yr}_tm_sel")

        tm_games = m_df[(m_df["Manager_1"] == sel_mgr) | (m_df["Manager_2"] == sel_mgr)].sort_values("Week").copy()
        w_cnt, l_cnt = 0, 0
        pf_reg, pa_reg = 0.0, 0.0
        sched_rows = []

        for _, r in tm_games.iterrows():
            wk = int(r["Week"])
            is_m1 = (str(r["Manager_1"]) == sel_mgr)
            opp = str(r["Manager_2"]) if is_m1 else str(r["Manager_1"])
            tm_sc = float(r["Score_1"]) if is_m1 else float(r["Score_2"])
            op_sc = float(r["Score_2"]) if is_m1 else float(r["Score_1"])
            raw_note = str(r.get("Notes", ""))

            if opp == "BYE":
                res_str = "BYE"
                rec_str = f"{w_cnt}-{l_cnt}"
                score_str = f"{tm_sc:.1f}"
                opp_str = "-"
            else:
                won = tm_sc > op_sc
                if wk <= 13:
                    if won:
                        w_cnt += 1
                    else:
                        l_cnt += 1
                    pf_reg += tm_sc
                    pa_reg += op_sc
                    rec_str = f"{w_cnt}-{l_cnt}"
                else:
                    rec_str = "Playoffs"
                res_str = "W" if won else "L"
                if int(sel_sched_yr) == 2012 and wk >= 14:
                    score_str = "-"
                    opp_str = "-"
                elif int(sel_sched_yr) == 2012:
                    score_str = f"{int(tm_sc)}"
                    opp_str = f"{int(op_sc)}"
                else:
                    score_str = f"{tm_sc:.1f}"
                    opp_str = f"{op_sc:.1f}"

            conf = get_confidence_badge(sel_sched_yr, wk, sel_mgr, opp)
            if raw_note and any(k in raw_note for k in ["Playoff", "Championship", "Upset", "Thu Proj"]):
                conf = f"{conf} | {raw_note}"

            phase = f"Week {wk}" if wk <= 13 else (
                "Wk 14 (QF)" if wk == 14 else ("Wk 15 (Semis)" if wk == 15 else "Wk 16 (Final)")
            )
            sched_rows.append({
                "Week": phase,
                "Opponent": opp,
                "Result": res_str,
                "Team Score": score_str,
                "Opp Score": opp_str,
                "Reg. Record": rec_str,
                "Confidence & Source": conf
            })

        with c_tm2:
            st.markdown(
                f"**{sel_mgr} — {sel_sched_yr} Regular Season Summary:** "
                f"Record: **`{w_cnt}-{l_cnt}-0`** | "
                f"Points For: **`{pf_reg:.1f}`** (`{pf_reg/max(1, w_cnt+l_cnt):.1f}` PPG) | "
                f"Points Against: **`{pa_reg:.1f}`** (`{pa_reg/max(1, w_cnt+l_cnt):.1f}` PPG)"
            )
            if int(sel_sched_yr) == 2012:
                st.caption("2012 schedule & scores reconstructed via 2-way PF/PA matrix matching from the official December 2012 league stat sheet.")
            else:
                st.caption("Weeks 1-7 are 100% official scoreboard totals. Weeks 8-13 follow the 11-team round-robin + Weeks 12-13 rematch template and match official end-of-season standings.")

        render_table(pd.DataFrame(sched_rows), left_align_cols=["Data Source / Notes"])

        if not b14_df.empty:
            st.write(f"#### Inspect {sel_mgr}'s Weekly Starting Lineup (Weeks 1-16)")
            tm_wks = sorted(b14_df[b14_df["Manager"] == sel_mgr]["Week"].unique().tolist())
            if tm_wks:
                sel_twk = st.selectbox(f"Select Week for {sel_mgr}'s Box Score:", tm_wks, key="db_tm_wk_box")
                sub_b = b14_df[(b14_df["Week"] == int(sel_twk)) & (b14_df["Manager"] == sel_mgr)].copy()
                opp_name = str(sub_b["Opponent"].iloc[0]) if not sub_b.empty else "BYE"
                bc1, bc2 = st.columns(2)
                with bc1:
                    tot_a = sub_b["Points"].sum()
                    src_a = sub_b["Source"].iloc[0] if not sub_b.empty else ""
                    fmt_a = f"{int(round(tot_a))}" if int(sel_sched_yr) == 2012 else f"{tot_a:.1f}"
                    st.markdown(f"**{sel_mgr}** | Total: **{fmt_a} pts** *({src_a})*")
                    sub_b["Pts"] = sub_b["Points"].apply(lambda x: f"{int(round(float(x)))}" if int(sel_sched_yr) == 2012 else f"{float(x):.1f}")
                    if "Email_Proj" in sub_b.columns and sub_b["Email_Proj"].notnull().any():
                        sub_b["Thu Proj"] = sub_b["Email_Proj"].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) else "-")
                        render_table(sub_b[["Slot", "Player", "Pts", "Thu Proj"]], left_align_cols=["Player"])
                    else:
                        render_table(sub_b[["Slot", "Player", "Pts"]], left_align_cols=["Player"])
                with bc2:
                    if opp_name != "BYE":
                        opp_b = b14_df[(b14_df["Week"] == int(sel_twk)) & (b14_df["Manager"] == opp_name)].copy()
                        if not opp_b.empty:
                            tot_b = opp_b["Points"].sum()
                            src_b = opp_b["Source"].iloc[0]
                            fmt_b = f"{int(round(tot_b))}" if int(sel_sched_yr) == 2012 else f"{tot_b:.1f}"
                            st.markdown(f"**{opp_name}** | Total: **{fmt_b} pts** *({src_b})*")
                            opp_b["Pts"] = opp_b["Points"].apply(lambda x: f"{int(round(float(x)))}" if int(sel_sched_yr) == 2012 else f"{float(x):.1f}")
                            if "Email_Proj" in opp_b.columns and opp_b["Email_Proj"].notnull().any():
                                opp_b["Thu Proj"] = opp_b["Email_Proj"].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) else "-")
                                render_table(opp_b[["Slot", "Player", "Pts", "Thu Proj"]], left_align_cols=["Player"])
                            else:
                                render_table(opp_b[["Slot", "Player", "Pts"]], left_align_cols=["Player"])

    elif sub_view == "Weekly Scoreboards & Box Scores (2012 & 2014)":
        c_byr, c_top1, c_top2 = st.columns([1, 1, 2])
        sel_board_yr = c_byr.selectbox("Select Season:", [2014, 2012], key="db_board_yr_sel")
        m_df = data.get("Matchups_2014" if int(sel_board_yr) == 2014 else "Matchups_2012", pd.DataFrame())
        b14_df = data.get("Box_Scores_2014" if int(sel_board_yr) == 2014 else "Box_Scores_2012", pd.DataFrame())
        if not m_df.empty:
            wks = sorted(m_df["Week"].unique().tolist())
            sel_wk = c_top1.selectbox(f"Select {sel_board_yr} Week:", wks, key=f"db_wk_board_sel_{sel_board_yr}")

            st.write(f"#### {sel_board_yr} Week {sel_wk} League Scoreboard")
            sub_m = m_df[m_df["Week"] == int(sel_wk)].copy()
            if int(sel_board_yr) == 2012 and int(sel_wk) >= 14:
                sub_m["Score_1"] = "WIN"
                sub_m["Score_2"] = "LOSS"
            elif int(sel_board_yr) == 2012:
                sub_m["Score_1"] = sub_m["Score_1"].apply(lambda x: f"{int(float(x))}" if pd.notnull(x) else "-")
                sub_m["Score_2"] = sub_m["Score_2"].apply(lambda x: f"{int(float(x))}" if pd.notnull(x) else "-")
            else:
                sub_m["Score_1"] = sub_m["Score_1"].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) else "-")
                sub_m["Score_2"] = sub_m["Score_2"].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) else "-")
            sub_m["Confidence & Source"] = sub_m.apply(
                lambda r: f"{get_confidence_badge(sel_board_yr, r['Week'], r['Manager_1'], r['Manager_2'])}" + (f" | {r['Notes']}" if "Playoff" in str(r.get("Notes", "")) or "Championship" in str(r.get("Notes", "")) else ""),
                axis=1
            )
            render_table(sub_m[["Week", "Manager_1", "Score_1", "Manager_2", "Score_2", "Confidence & Source"]], left_align_cols=["Confidence & Source"])

            if not b14_df.empty:
                wk_b = b14_df[b14_df["Week"] == int(sel_wk)].copy()
                pairs_seen = []
                pair_labels = []
                pair_map = {}
                for _, r_b in wk_b[["Manager", "Opponent"]].drop_duplicates().iterrows():
                    m_a, m_b = str(r_b["Manager"]), str(r_b["Opponent"])
                    key_set = frozenset([m_a, m_b])
                    if key_set not in pairs_seen:
                        pairs_seen.append(key_set)
                        lbl = f"{m_a} vs. {m_b}"
                        pair_labels.append(lbl)
                        pair_map[lbl] = [m_a] if m_b == "BYE" else [m_a, m_b]

                sel_pair = c_top2.selectbox("Select Week Matchup Box Score:", pair_labels, key=f"db_box14_pair_{sel_wk}")
                st.write(f"#### Week {sel_wk} Box Score: {sel_pair}")
                mgrs_in_wk = pair_map.get(sel_pair, [])
                bc1, bc2 = st.columns(2)
                for idx_m, m_name in enumerate(mgrs_in_wk[:2]):
                    target_col = bc1 if idx_m == 0 else bc2
                    with target_col:
                        m_rows = wk_b[wk_b["Manager"] == m_name].copy()
                        tot_pts = m_rows["Points"].sum()
                        src_tag = m_rows["Source"].iloc[0] if not m_rows.empty else ""
                        fmt_p = f"{int(round(tot_pts))}" if int(sel_board_yr) == 2012 else f"{tot_pts:.1f}"
                        st.markdown(f"**{m_name}** | Starter Total: **{fmt_p} pts** *({src_tag})*")
                        m_rows["Pts"] = m_rows["Points"].apply(lambda x: f"{int(round(float(x)))}" if int(sel_board_yr) == 2012 else f"{float(x):.1f}")
                        if "Email_Proj" in m_rows.columns and m_rows["Email_Proj"].notnull().any():
                            m_rows["Thu Proj"] = m_rows["Email_Proj"].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) else "-")
                            render_table(m_rows[["Slot", "Player", "Pts", "Thu Proj"]], left_align_cols=["Player"])
                        else:
                            render_table(m_rows[["Slot", "Player", "Pts"]], left_align_cols=["Player"])

    elif sub_view == "Waiver, Free Agency & Activity Logs (2012 & 2014)":
        act12_df = data.get("Activity_2012", pd.DataFrame())
        if not act12_df.empty:
            st.write("#### 2012 Full-Season Roster Activity Totals (Trades, Adds, Drops & Activations)")
            st.caption("Extracted from the December 2012 league stat sheet.")
            render_table(act12_df[["Season", "Manager", "Trades", "Acquisitions", "Drops", "Activations"]])
            st.divider()
        st.write("#### 2014 Waiver & Free Agency Transaction Log (Weeks 1-17)")
        tx_df = data.get("Transactions_2014", pd.DataFrame())
        if not tx_df.empty:
            c_tx1, c_tx2 = st.columns(2)
            mgrs = ["All Managers"] + sorted(tx_df["Manager"].astype(str).unique().tolist())
            sel_m = c_tx1.selectbox("Filter by Manager:", mgrs, key="db_tx_mgr")
            q_pl = c_tx2.text_input("Search Player Name:", "", key="db_tx_search")
            sub_tx = tx_df.copy()
            if sel_m != "All Managers":
                sub_tx = sub_tx[sub_tx["Manager"] == sel_m]
            if q_pl.strip():
                sub_tx = sub_tx[sub_tx["Player"].astype(str).str.contains(q_pl.strip(), case=False, na=False)]
            render_table(sub_tx[["Report_Date", "Manager", "Action", "Player", "Position", "NFL_Team", "Method"]], left_align_cols=["Player"])

    elif sub_view == "Trade & Proposal Archive (2011-2014)":
        tr_df = data.get("Trades_2011_2014", pd.DataFrame())
        if not tr_df.empty:
            c1, c2 = st.columns(2)
            yr_f = c1.selectbox("Filter Season:", ["All Years (2011-2014)", "2014", "2013", "2012", "2011"], key="db_tr_yr")
            st_f = c2.selectbox("Filter Status:", ["All Emails", "Accepted / Upheld", "Proposal", "Declined"], key="db_tr_st")
            sub_tr = tr_df.copy()
            if not yr_f.startswith("All"):
                sub_tr = sub_tr[sub_tr["Year"] == int(yr_f)]
            if st_f != "All Emails":
                sub_tr = sub_tr[sub_tr["Status"] == st_f]
            render_table(sub_tr[["Year", "Date", "Status", "Proposer", "Recipient", "Trade_Details"]], left_align_cols=["Trade_Details"])
