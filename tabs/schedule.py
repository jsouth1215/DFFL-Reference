import streamlit as st
import pandas as pd
from utils import render_html_table, display_box_score

def render(games, box_df, game_top_map, teams, seasons_list):
    c1, c2 = st.columns(2)
    s_szn = c1.selectbox("Season", seasons_list, key='sched_szn')
    s_team = c2.selectbox("Manager", teams, key='sched_team')
    sched = games[(games['Season'] == str(s_szn)) & (games['Team_Name'] == s_team)].sort_values(['Game_Type', 'Week_Num']).copy()
    if not sched.empty:
        sched['Type'] = sched['Game_Type'].map({1: 'Regular Season', 2: 'Playoffs', 3: 'Consolation', 4: 'Playoff Bye'})
        sched['Result'] = sched.apply(lambda x: 'BYE' if x['Game_Type'] == 4 else ('W' if x['W'] else ('L' if x['L'] else 'T')), axis=1)
        t_col, o_col = f'{s_team} Score', 'Opponent Score'
        sched[t_col] = sched['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        sched[o_col] = sched.apply(lambda x: f"{float(x['Opp_Points']):.1f}" if x['Game_Type'] != 4 else "-", axis=1)
        sched['Margin'] = sched.apply(lambda r: "-" if r['Game_Type']==4 else f"{r['Actual_Points']-r['Opp_Points']:+.1f}", axis=1)
        sched['Opponent'] = sched['Opponent_Team_Name']
        
        s_str = str(s_szn).replace('.0', '').strip()
        sched['Week_Num_Int'] = pd.to_numeric(sched['Week'], errors='coerce').fillna(0).astype(int)
        sched[f'{s_team} Top Scorer'] = sched.apply(lambda r: game_top_map.get((s_str, r['Week_Num_Int'], str(r['Team_Name']).strip()), ""), axis=1)
        sched['Opponent Top Scorer'] = sched.apply(lambda r: game_top_map.get((s_str, r['Week_Num_Int'], str(r['Opponent_Team_Name']).strip()), "") if str(r['Opponent_Team_Name']).upper() != 'BYE' else "", axis=1)
        
        cols = ['Week', 'Type', 'Opponent', 'Result', t_col, o_col, 'Margin', f'{s_team} Top Scorer', 'Opponent Top Scorer']
        hl = lambda row: ['font-weight: bold;' if (c == t_col and row['Result'] == 'W') or (c == o_col and row['Result'] == 'L') else '' for c in row.index]
        render_html_table(sched[cols], hl)
        
        vwk = st.selectbox("Select Week to View Box Score:", ["Select..."] + sched['Week'].unique().tolist(), key="sch_box")
        if vwk != "Select...": display_box_score(s_szn, vwk, s_team, box_df, games)
    else:
        st.write("No schedule found.")
