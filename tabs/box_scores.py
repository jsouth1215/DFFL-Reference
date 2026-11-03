import streamlit as st
from utils import display_box_score

def render(games, box_df, teams, seasons_list):
    if box_df.empty:
        st.warning("Player data not found.")
        return
    c1, c2, c3 = st.columns(3)
    b_season = c1.selectbox("Season", seasons_list, key="b_szn")
    weeks = sorted(box_df[box_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == str(b_season)]['Week'].dropna().unique().tolist())
    b_week = c2.selectbox("Week", weeks, key="b_wk")
    avail_teams = sorted(box_df[(box_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == str(b_season)) & (box_df['Week'] == b_week)]['Team_Name'].dropna().unique().tolist())
    b_team = c3.selectbox("Manager", avail_teams, key="b_tm")
    if b_team:
        display_box_score(b_season, b_week, b_team, box_df, games)
