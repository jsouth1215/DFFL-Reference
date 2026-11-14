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

@st.cache_data(ttl=600)
def load_deadball_data():
    out = {}
    try:
        xls = pd.ExcelFile("deadball_era_data.xlsx", engine="openpyxl")
        for sh in xls.sheet_names:
            out[sh] = pd.read_excel(xls, sheet_name=sh)
    except Exception:
        pass
    return out

def render():
    st.markdown("### The Deadball Era Archive (2011-2014)")
    st.caption(
        "Historical archive from the league's early 12-team seasons (2011-2014). "
        "In 2011, 12 solo managers competed across 12 teams. From 2012 to 2014, 13 managers competed for 12 franchise spots, with the two bottom consolation finishers from the prior year co-managing a shared franchise."
    )

    data = load_deadball_data()
    if not data:
        st.warning("Upload `deadball_era_data.xlsx` to the repository root to view the Deadball Era archive.")
        return

    sub_view = st.radio(
        "Deadball Era View:",
        [
            "Season Standings & Summary (2011-2014)",
            "Deadball Draft Boards (2012-2014)",
            "2014 Scoreboards, Box Scores & Waivers",
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
            "* **2012 Season:** **Matt** won back-to-back titles as the #6 seed (`6-7`), defeating **Lukas**, **Noah**, and **Sean**. **Eli** won the regular-season scoring title. *(Shared Franchise: **Jack & Austin**)*\n"
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

    elif sub_view == "2014 Scoreboards, Box Scores & Waivers":
        b14_df = data.get("Box_Scores_2014", pd.DataFrame())
        if not b14_df.empty:
            st.write("#### 2014 Matchup Box Score Archive (Jack's Matchups: Weeks 1-16)")
            st.caption("Weeks 1-7 are official ESPN box scores. Weeks 8-16 are Thursday preview starting lineups scored with 2014 NFL actual stats (with original Thursday projections shown for reference).")
            bwks = sorted(b14_df["Week"].unique().tolist())
            sel_bwk = st.selectbox("Select 2014 Week Box Score:", bwks, key="db_box14_wk")
            wk_b = b14_df[b14_df["Week"] == int(sel_bwk)].copy()
            mgrs_in_wk = wk_b["Manager"].unique().tolist()
            bc1, bc2 = st.columns(2)
            for idx_m, m_name in enumerate(mgrs_in_wk[:2]):
                target_col = bc1 if idx_m == 0 else bc2
                with target_col:
                    m_rows = wk_b[wk_b["Manager"] == m_name].copy()
                    tot_pts = m_rows["Points"].sum()
                    src_tag = m_rows["Source"].iloc[0] if not m_rows.empty else ""
                    st.markdown(f"**{m_name}** | Starter Total: **{tot_pts:.1f} pts** *({src_tag})*")
                    m_rows["Pts"] = m_rows["Points"].apply(lambda x: f"{float(x):.1f}")
                    if "Email_Proj" in m_rows.columns and m_rows["Email_Proj"].notnull().any():
                        m_rows["Thu Proj"] = m_rows["Email_Proj"].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) else "-")
                        render_table(m_rows[["Slot", "Player", "Pts", "Thu Proj"]], left_align_cols=["Player"])
                    else:
                        render_table(m_rows[["Slot", "Player", "Pts"]], left_align_cols=["Player"])
            st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.write("#### 2014 Weekly Matchup Results (Weeks 1-16)")
            m_df = data.get("Matchups_2014", pd.DataFrame())
            if not m_df.empty:
                wks = sorted(m_df["Week"].unique().tolist())
                sel_wk = st.selectbox("Select Week:", ["All Weeks (1-16)"] + [str(w) for w in wks], key="db_wk_sel")
                sub_m = m_df.copy() if sel_wk.startswith("All") else m_df[m_df["Week"] == int(sel_wk)].copy()
                sub_m["Score_1"] = sub_m["Score_1"].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) else "-")
                sub_m["Score_2"] = sub_m["Score_2"].apply(lambda x: f"{float(x):.1f}" if pd.notnull(x) else "-")
                if "Notes" not in sub_m.columns:
                    sub_m["Notes"] = sub_m["Week"].apply(lambda w: "Official Scoreboard" if int(w) <= 7 else "Thu Lineup + NFL Actuals")
                render_table(sub_m[["Week", "Manager_1", "Score_1", "Manager_2", "Score_2", "Notes"]], left_align_cols=["Notes"])
        with c2:
            st.write("#### 2014 Waiver & Free Agency Log (Weeks 1-17)")
            tx_df = data.get("Transactions_2014", pd.DataFrame())
            if not tx_df.empty:
                mgrs = ["All Managers"] + sorted(tx_df["Manager"].astype(str).unique().tolist())
                sel_m = st.selectbox("Filter Manager:", mgrs, key="db_tx_mgr")
                sub_tx = tx_df if sel_m == "All Managers" else tx_df[tx_df["Manager"] == sel_m]
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
