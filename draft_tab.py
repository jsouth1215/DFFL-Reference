import streamlit as st
import pandas as pd

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

def render(box_df=None):
    df = load_draft_data(box_df)
    if df.empty:
        st.warning("Could not load 'Draft History.xlsx' (sheet: 'Consolidated'). Make sure it is uploaded to the repository root.")
        return

    draft_view = st.radio(
        "Draft View:",
        ["🏈 Yearly Draft Board", "📋 Player Draft Ledger", "👤 Manager Draft Room", "🏆 Draft Records & Loyalty"],
        horizontal=True,
        key="draft_sub_view"
    )
    st.write("---")

    years_avail = sorted(df['Year'].unique().tolist(), reverse=True)
    managers_avail = sorted(df['Team'].unique().tolist())

    if draft_view == "🏈 Yearly Draft Board":
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

    elif draft_view == "📋 Player Draft Ledger":
        all_players = sorted(df['Player'].unique().tolist())
        default_idx = all_players.index("Christian McCaffrey") if "Christian McCaffrey" in all_players else 0
        sel_player = st.selectbox("Search / Select Player:", all_players, index=default_idx, key="dl_player")

        p_df = df[df['Player'] == sel_player].sort_values('Year', ascending=False).copy()
        if not p_df.empty:
            times_drafted = len(p_df)
            avg_pick = p_df['Overall Pick'].mean()
            best_pick = p_df['Overall Pick'].min()
            top_mgrs = p_df['Team'].value_counts()
            max_cnt = top_mgrs.max()
            fav_mgrs = ", ".join(top_mgrs[top_mgrs == max_cnt].index.tolist()) + f" ({max_cnt}x)"

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Times Drafted", f"{times_drafted}")
            m2.metric("Average Overall Pick (ADP)", f"{avg_pick:.1f}")
            m3.metric("Highest Pick", f"#{best_pick}")
            m4.metric("Most Drafted By", fav_mgrs)

            disp = p_df[['Year', 'Round', 'Round Pick', 'Overall Pick', 'Team', 'Position', 'NFL Team']].rename(
                columns={'Team': 'Drafted By', 'Round Pick': 'Pick in Rd'}
            )
            render_table(disp)

    elif draft_view == "👤 Manager Draft Room":
        c1, c2 = st.columns(2)
        sel_mgr = c1.selectbox("Select Manager:", managers_avail, key="mdr_mgr")
        sel_m_yr = c2.selectbox("Select Season:", ["All-Time Summary"] + [str(y) for y in years_avail], key="mdr_yr")

        m_df = df[df['Team'] == sel_mgr].copy()
        if sel_m_yr == "All-Time Summary":
            c_left, c_right = st.columns([1.2, 1.8])
            with c_left:
                st.write(f"#### {sel_mgr}'s Round 1 History")
                r1_df = m_df[m_df['Round'] == 1].sort_values('Year', ascending=False)[['Year', 'Overall Pick', 'Player', 'Position', 'NFL Team']].rename(
                    columns={'Overall Pick': 'Pick #'}
                )
                render_table(r1_df)

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
            yr_sub = m_df[m_df['Year'] == int(sel_m_yr)].sort_values('Round')[['Round', 'Round Pick', 'Overall Pick', 'Player', 'Position', 'NFL Team']].rename(
                columns={'Round Pick': 'Pick in Rd', 'Overall Pick': 'Overall #'}
            )
            render_table(yr_sub, left_align_cols=['Player'])

    elif draft_view == "🏆 Draft Records & Loyalty":
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
            
