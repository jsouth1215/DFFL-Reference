import streamlit as st
import pandas as pd
from utils import render_html_table

def render(games, seasons_list):
    sel_szn = st.selectbox("Select Season", seasons_list, key='stnd_szn')
    szn_data = games[(games['Season'] == str(sel_szn)) & (games['Game_Type'] == 1)]
    if not szn_data.empty:
        max_wk = int(szn_data['Week_Num'].max())
        sel_wk = st.slider("Standings Through Week:", min_value=1, max_value=max_wk, value=max_wk)
        szn_games = szn_data[szn_data['Week_Num'] <= sel_wk].copy()
        szn_games['Weekly_Rank'] = szn_games.groupby('Week_Num')['Actual_Points'].rank(ascending=False, method='average')
        szn_games['N_Teams'] = szn_games.groupby('Week_Num')['Team_Name'].transform('count')
        szn_games['Exp_Win'] = szn_games.apply(lambda r: (r['N_Teams'] - r['Weekly_Rank']) / (r['N_Teams'] - 1) if r['N_Teams'] > 1 else 0.0, axis=1)
        
        stnd = szn_games.groupby('Team_Name').agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum'), PF=('Actual_Points', 'sum'), PA=('Opp_Points', 'sum'), Exp_Win_Total=('Exp_Win', 'sum')).reset_index()
        stnd['Win_Pct_Raw'] = (stnd['W'] / (stnd['W'] + stnd['L'] + stnd['T'])).fillna(0)
        stnd = stnd.sort_values(['Win_Pct_Raw', 'PF'], ascending=[False, False]).reset_index(drop=True)
        stnd['Rank'] = (stnd.index + 1).map(lambda x: f"{x}{'th' if 11 <= x % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(x % 10, 'th')}")
        stnd['Win %'] = stnd['Win_Pct_Raw'].apply(lambda x: f"{x:.3f}".replace("0.", ".", 1) if x < 1 else f"{x:.3f}")
        stnd['PF'] = stnd['PF'].apply(lambda x: f"{float(x):.1f}")
        stnd['PA'] = stnd['PA'].apply(lambda x: f"{float(x):.1f}")
        stnd['Expected Wins'] = stnd['Exp_Win_Total'].apply(lambda x: f"{float(x):.1f}")
        stnd['Luck Factor'] = stnd.apply(lambda r: "0.0" if abs(r['W']-r['Exp_Win_Total'])<0.05 else f"{r['W']-r['Exp_Win_Total']:+.1f}", axis=1)
        render_html_table(stnd[['Rank', 'Team_Name', 'W', 'L', 'T', 'Win %', 'PF', 'PA', 'Expected Wins', 'Luck Factor']].rename(columns={'Team_Name': 'Team'}))
    else:
        st.write("No regular season data found.")
