import streamlit as st
import pandas as pd
from utils import render_html_table

def render(games, box_df, game_top_map, teams):
    c1, c2 = st.columns(2)
    with c1:
        team_a = st.selectbox("Team A", teams)
        team_b = st.selectbox("Team B", [t for t in teams if t != team_a])
    h2h = games[(games['Team_Name'] == team_a) & (games['Opponent_Team_Name'] == team_b) & (games['Game_Type'].isin([1, 2]))].copy()
    if not h2h.empty:
        w, l, t = h2h['W'].sum(), h2h['L'].sum(), h2h['T'].sum()
        p_h2h = h2h[h2h['Game_Type'] == 2]
        pw, pl, pt = p_h2h['W'].sum(), p_h2h['L'].sum(), p_h2h['T'].sum()
        with c2:
            st.write(f"### {team_a} vs. {team_b}")
            leader = f"{team_a} leads {w}-{l}" if w > l else (f"{team_b} leads {l}-{w}" if l > w else f"Tied {w}-{l}")
            st.markdown(f"**Series Leader:** {leader}" + (f"-{t}" if t > 0 else ""))
            if len(p_h2h) == 0: st.markdown("**Playoff Record:** No playoff matchups have occurred")
            else:
                p_lead = f"{team_a} leads {pw}-{pl}" if pw > pl else (f"{team_b} leads {pl}-{pw}" if pl > pw else f"Tied {pw}-{pl}")
                st.markdown(f"**Playoff Record:** {p_lead}" + (f"-{pt}" if pt > 0 else ""))
        st.divider()
        h2h = h2h.sort_values(['Season_Num', 'Week_Num'], ascending=[False, False])
        h2h['Season_Str'] = h2h['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        h2h['Winner'] = h2h.apply(lambda x: x['Team_Name'] if x['W'] == 1 else (x['Opponent_Team_Name'] if x['L'] == 1 else 'Tie'), axis=1)
        h2h['Type'] = h2h['Game_Type'].map({1: 'Regular Season', 2: 'Playoffs'}).fillna(h2h['Game_Type_Str'])
        col_a, col_b = f'{team_a} Pts', f'{team_b} Pts'
        h2h[col_a] = h2h['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        h2h[col_b] = h2h['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
        h2h['Margin'] = h2h['Margin'].apply(lambda x: f"{float(x):.1f}")
        h2h[f'{team_a} Top Scorer'] = h2h.apply(lambda r: game_top_map.get((r['Season_Str'], int(r['Week_Num']), str(team_a).strip()), ""), axis=1)
        h2h[f'{team_b} Top Scorer'] = h2h.apply(lambda r: game_top_map.get((r['Season_Str'], int(r['Week_Num']), str(team_b).strip()), ""), axis=1)
        hl = lambda r: ['font-weight: bold;' if (c == col_a and r['Winner'] == team_a) or (c == col_b and r['Winner'] == team_b) else '' for c in r.index]
        render_html_table(h2h[['Season_Str', 'Week', 'Type', 'Winner', col_a, col_b, 'Margin', f'{team_a} Top Scorer', f'{team_b} Top Scorer']].rename(columns={'Season_Str': 'Season'}), hl)
    else:
        st.write("No matchups found between these teams.")
