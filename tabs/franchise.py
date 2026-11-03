import streamlit as st
import pandas as pd
from utils import render_html_table, get_detailed_streaks, get_playoff_outcome, display_box_score

def render(games, box_df, rs_ranks_df, completed_playoff_seasons, teams, seasons_list):
    selected_team = st.selectbox("Select Manager", teams, label_visibility="collapsed")
    mgr_games = games[games['Team_Name'] == selected_team].sort_values(['Season_Num', 'Week_Num']).copy()
    mgr_games['Result'] = mgr_games.apply(lambda x: 'W' if x['W'] else ('L' if x['L'] else 'T'), axis=1)
    
    reg_season = mgr_games[mgr_games['Game_Type'] == 1]
    playoffs = mgr_games[mgr_games['Game_Type'] == 2]
    
    tw, tl, tt = reg_season['W'].sum(), reg_season['L'].sum(), reg_season['T'].sum()
    win_pct = tw / (tw + tl + tt) if (tw + tl + tt) > 0 else 0.0
    win_pct_str = f"{win_pct:.3f}".replace("0.", ".", 1) if win_pct < 1 else f"{win_pct:.3f}"
    
    high_score_str = f"{mgr_games.loc[mgr_games['Actual_Points'].idxmax()]['Actual_Points']:.1f} ({str(mgr_games.loc[mgr_games['Actual_Points'].idxmax()]['Season']).replace('.0','')}, W{mgr_games.loc[mgr_games['Actual_Points'].idxmax()]['Week']})" if not mgr_games.empty else "N/A"
    
    comp_games = mgr_games[mgr_games['Game_Type'].isin([1, 2])]
    if not comp_games.empty:
        comp_valid = comp_games[comp_games['Actual_Points'] > 0]
        low_score_str = f"{comp_valid.loc[comp_valid['Actual_Points'].idxmin()]['Actual_Points']:.1f} ({str(comp_valid.loc[comp_valid['Actual_Points'].idxmin()]['Season']).replace('.0','')}, W{comp_valid.loc[comp_valid['Actual_Points'].idxmin()]['Week']})" if not comp_valid.empty else "N/A"
        valid_opp = comp_games[comp_games['Opponent_Team_Name'].str.upper() != 'CAM']
        if not valid_opp.empty:
            opp_stats = valid_opp.groupby('Opponent_Team_Name').agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum')).reset_index()
            opp_stats['Games'] = opp_stats['W'] + opp_stats['L'] + opp_stats['T']
            opp_stats = opp_stats[opp_stats['Games'] > 0]
            if not opp_stats.empty:
                opp_stats['Win %'] = opp_stats['W'] / opp_stats['Games']
                def fmt_opp(df_sub):
                    recs = [f"{int(r['W'])}-{int(r['L'])}" + (f"-{int(r['T'])}" if r['T']>0 else "") for _, r in df_sub.iterrows()]
                    return f"{', '.join(df_sub['Opponent_Team_Name'])} ({recs[0]})" if len(set(recs))==1 else ", ".join([f"{r['Opponent_Team_Name']} ({rec})" for (_, r), rec in zip(df_sub.iterrows(), recs)])
                easiest_str = fmt_opp(opp_stats[opp_stats['Win %'] == opp_stats['Win %'].max()])
                toughest_str = fmt_opp(opp_stats[opp_stats['Win %'] == opp_stats['Win %'].min()])
            else: easiest_str, toughest_str = "N/A", "N/A"
        else: easiest_str, toughest_str = "N/A", "N/A"
    else: low_score_str, easiest_str, toughest_str = "N/A", "N/A", "N/A"
    
    pw, pl, pt = playoffs['W'].sum(), playoffs['L'].sum(), playoffs['T'].sum()
    champs = sorted([str(s).replace('.0', '') for s in playoffs[playoffs['Playoff_Round'].astype(str).str.strip().str.lower().isin(['finals', 'championship']) & (playoffs['W'] == 1)]['Season'].unique()])
    champ_str = f"{len(champs)} ({', '.join(champs)})" if champs else "0"
    
    longest_w, w_span, longest_l, l_span = get_detailed_streaks(comp_games)
    
    rs_team = rs_ranks_df[rs_ranks_df['Team_Name'] == selected_team]
    playoff_apps, playoff_byes = 0, 0
    for _, row in rs_team.iterrows():
        szn = str(row['Season']).strip()
        if szn.isdigit() and szn in completed_playoff_seasons:
            s_int, rk = int(szn), float(row['RS_Rank'])
            if pd.notnull(rk):
                if (s_int == 2017 and rk <= 4) or (s_int > 2017 and rk <= 6): playoff_apps += 1
                if s_int >= 2018 and rk <= 2: playoff_byes += 1
                
    top_pos_all_time = {'QB': 'N/A', 'RB': 'N/A', 'WR': 'N/A', 'TE': 'N/A', 'D/ST': 'N/A', 'K': 'N/A'}
    top_per_szn = {'QB': {}, 'RB': {}, 'WR': {}, 'TE': {}}
    if not box_df.empty:
        slot_c = 'Slot' if 'Slot' in box_df.columns else ('Lineup_Slot' if 'Lineup_Slot' in box_df.columns else 'Position')
        name_c = 'Player_Name' if 'Player_Name' in box_df.columns else 'Player'
        pts_c = 'Actual_Points' if 'Actual_Points' in box_df.columns else 'Points'
        pos_c = 'Position' if 'Position' in box_df.columns else ('Pos' if 'Pos' in box_df.columns else slot_c)
        
        el_g = games[games['Game_Type'].isin([1, 2, 4])][['Season', 'Week', 'Team_Name']].drop_duplicates()
        el_g['Season'] = el_g['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        el_g['Week'] = pd.to_numeric(el_g['Week'], errors='coerce').fillna(0).astype(int)
        
        b_team_df = box_df[box_df['Team_Name'] == selected_team].copy()
        b_team_df['Season'] = b_team_df['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        b_team_df['Week'] = pd.to_numeric(b_team_df['Week'], errors='coerce').fillna(0).astype(int)
        starters = b_team_df[~b_team_df[slot_c].astype(str).str.strip().str.upper().isin(['BE', 'IR', 'BENCH'])]
        counted = pd.merge(starters, el_g, on=['Season', 'Week', 'Team_Name'], how='inner')
        if not counted.empty:
            counted[pts_c] = pd.to_numeric(counted[pts_c], errors='coerce').fillna(0)
            def clean_p(v):
                p = str(v).strip().upper()
                if p in ['K', 'PK']: return 'K'
                if p in ['D/ST', 'DST', 'DEF', 'DP']: return 'D/ST'
                return p
            counted['Clean_Pos'] = counted[pos_c].apply(clean_p)
            for p_target in ['QB', 'RB', 'WR', 'TE', 'D/ST', 'K']:
                sub_pos = counted[counted['Clean_Pos'] == p_target]
                if not sub_pos.empty:
                    tot = sub_pos.groupby(name_c)[pts_c].sum().reset_index().sort_values(pts_c, ascending=False)
                    if not tot.empty: top_pos_all_time[p_target] = f"{tot.iloc[0][name_c]} ({tot.iloc[0][pts_c]:,.1f} pts)"
            for p_target in ['QB', 'RB', 'WR', 'TE']:
                sub_pos = counted[counted['Clean_Pos'] == p_target]
                if not sub_pos.empty:
                    s_totals = sub_pos.groupby(['Season', name_c])[pts_c].sum().reset_index().sort_values(['Season', pts_c], ascending=[True, False]).drop_duplicates(subset=['Season'])
                    top_per_szn[p_target] = dict(zip(s_totals['Season'], s_totals.apply(lambda r: f"{r[name_c]} ({r[pts_c]:,.1f})", axis=1)))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Championships:** {champ_str}")
        st.markdown(f"**Reg. Season Record:** {tw}-{tl}-{tt} ({win_pct_str})")
        st.markdown(f"**Playoff Record:** {pw}-{pl}-{pt}")
        st.markdown(f"**Playoff Appearances:** {playoff_apps}")
        st.markdown(f"**Playoff Byes:** {playoff_byes}")
        st.markdown(f"**Weekly Bags Won:** {mgr_games['Is_High_Scorer'].sum()}")
    with c2:
        st.markdown(f"**Highest Scoring Game:** {high_score_str}")
        st.markdown(f"**Lowest Scoring Game:** {low_score_str}")
        st.markdown(f"**Easiest Opponent:** {easiest_str}")
        st.markdown(f"**Toughest Opponent:** {toughest_str}")
        st.markdown(f"**Longest Win Streak:** {longest_w} games ({w_span})")
        st.markdown(f"**Longest Losing Streak:** {longest_l} games ({l_span})")
    with c3:
        st.markdown(f"**Top Scoring QB:** {top_pos_all_time['QB']}")
        st.markdown(f"**Top Scoring RB:** {top_pos_all_time['RB']}")
        st.markdown(f"**Top Scoring WR:** {top_pos_all_time['WR']}")
        st.markdown(f"**Top Scoring TE:** {top_pos_all_time['TE']}")
        st.markdown(f"**Top Scoring D/ST:** {top_pos_all_time['D/ST']}")
        st.markdown(f"**Top Scoring K:** {top_pos_all_time['K']}")
    st.divider()

    st.write("### Season-by-Season (Regular Season)")
    szn_stats = reg_season.groupby('Season').agg(W=('W', 'sum'), L=('L', 'sum'), T=('T', 'sum'), PF=('Actual_Points', 'sum'), PA=('Opp_Points', 'sum')).reset_index()
    szn_stats['Win %'] = (szn_stats['W'] / (szn_stats['W'] + szn_stats['L'] + szn_stats['T'])).fillna(0).apply(lambda x: f"{x:.3f}".replace("0.", ".", 1) if x < 1 else f"{x:.3f}")
    szn_stats['Games'] = szn_stats['W'] + szn_stats['L'] + szn_stats['T']
    szn_stats['PF/G'] = (szn_stats['PF'] / szn_stats['Games']).apply(lambda x: f"{x:.1f}")
    szn_stats['PA/G'] = (szn_stats['PA'] / szn_stats['Games']).apply(lambda x: f"{x:.1f}")
    szn_stats['PF'] = szn_stats['PF'].astype(int)
    szn_stats['PA'] = szn_stats['PA'].astype(int)
    
    all_reg = games[games['Game_Type'] == 1].copy()
    all_reg['Season_Str'] = all_reg['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    pf_ranks = all_reg.groupby(['Season_Str', 'Team_Name'])['Actual_Points'].sum().groupby('Season_Str').rank(ascending=False, method='min').astype(int).reset_index()
    pa_ranks = all_reg.groupby(['Season_Str', 'Team_Name'])['Opp_Points'].sum().groupby('Season_Str').rank(ascending=False, method='min').astype(int).reset_index()
    pf_team = pf_ranks[pf_ranks['Team_Name'] == selected_team].rename(columns={'Season_Str': 'Season', 'Actual_Points': 'PF Rank'})
    pa_team = pa_ranks[pa_ranks['Team_Name'] == selected_team].rename(columns={'Season_Str': 'Season', 'Opp_Points': 'PA Rank'})
    szn_stats = pd.merge(pd.merge(szn_stats, pf_team[['Season', 'PF Rank']], on='Season', how='left'), pa_team[['Season', 'PA Rank']], on='Season', how='left')
    
    szn_stats['Playoff Outcome'] = [get_playoff_outcome(playoffs[playoffs['Season'] == s]) for s in szn_stats['Season']]
    mgr_games['Season_Str'] = mgr_games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    szn_stats['Weekly Bags'] = szn_stats['Season'].map(mgr_games.groupby('Season_Str')['Is_High_Scorer'].sum().to_dict()).fillna(0).astype(int)
    
    all_reg['Weekly_Rank'] = all_reg.groupby(['Season_Str', 'Week_Num'])['Actual_Points'].rank(ascending=False, method='average')
    all_reg['N_Teams'] = all_reg.groupby(['Season_Str', 'Week_Num'])['Team_Name'].transform('count')
    all_reg['Exp_Win'] = all_reg.apply(lambda r: (r['N_Teams'] - r['Weekly_Rank']) / (r['N_Teams'] - 1) if r['N_Teams'] > 1 else 0.0, axis=1)
    xw = all_reg.groupby(['Season_Str', 'Team_Name'])['Exp_Win'].sum().reset_index()
    xw_team = xw[xw['Team_Name'] == selected_team].rename(columns={'Season_Str': 'Season', 'Exp_Win': 'Exp_Win_Total'})
    szn_stats = pd.merge(szn_stats, xw_team[['Season', 'Exp_Win_Total']], on='Season', how='left')
    szn_stats['Expected Wins'] = szn_stats['Exp_Win_Total'].fillna(0).apply(lambda x: f"{x:.1f}")
    szn_stats['Luck Factor'] = szn_stats.apply(lambda r: "0.0" if pd.isna(r['Exp_Win_Total']) or abs(r['W']-r['Exp_Win_Total'])<0.05 else f"{r['W']-r['Exp_Win_Total']:+.1f}", axis=1)
    
    rs_format = rs_team[['Season', 'RS_Rank']].copy()
    rs_format['Season'] = rs_format['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    szn_stats = pd.merge(szn_stats, rs_format, on='Season', how='left')
    szn_stats['Standings Finish'] = szn_stats['RS_Rank'].apply(lambda x: f"{int(x)}{'th' if 11 <= int(x)%100 <= 13 else {1:'st',2:'nd',3:'rd'}.get(int(x)%10, 'th')}" if pd.notnull(x) else "")
    
    for p in ['QB', 'RB', 'WR', 'TE']:
        szn_stats[f'Top {p}'] = szn_stats['Season'].map(top_per_szn[p]).fillna("")
        
    disp_cols = ['Season', 'W', 'L', 'Win %', 'Standings Finish', 'PF', 'PF/G', 'PF Rank', 'PA', 'PA/G', 'PA Rank', 'Playoff Outcome', 'Weekly Bags', 'Expected Wins', 'Luck Factor', 'Top QB', 'Top RB', 'Top WR', 'Top TE']
    hl_cells = lambda row: ['background-color: #ebebeb; color: #888888;' if str(row.get('Season','')).strip() in ['2017', '2018'] and c in ['Weekly Bags', 'Top QB', 'Top RB', 'Top WR', 'Top TE'] else '' for c in row.index]
    render_html_table(szn_stats[disp_cols].sort_values('Season', ascending=False), highlight_fn=hl_cells)
    
    st.divider()
    st.write("### Playoff Game Log")
    po_disp = playoffs.sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).copy()
    if not po_disp.empty:
        po_disp['Season'] = po_disp['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        po_disp['Score'] = po_disp['Actual_Points'].round(1).astype(str) + " - " + po_disp['Opp_Points'].round(1).astype(str)
        render_html_table(po_disp[['Season', 'Week', 'Playoff_Round', 'Opponent_Team_Name', 'Result', 'Score']].rename(columns={'Opponent_Team_Name': 'Opponent', 'Playoff_Round': 'Round'}))
        po_disp['Game_Label'] = po_disp['Season'] + " Week " + po_disp['Week'].astype(str) + " vs " + po_disp['Opponent_Team_Name']
        vk = st.selectbox("Select Playoff Game to View Box Score:", ["Select..."] + po_disp['Game_Label'].tolist(), key="po_box")
        if vk != "Select...":
            row = po_disp[po_disp['Game_Label'] == vk].iloc[0]
            display_box_score(row['Season'], row['Week'], selected_team, box_df, games)
    else:
        st.write("No playoff appearances on record.")
        
    st.divider()
    st.write("### Head-to-Head vs. All Opponents")
    opp_list = []
    for opp in sorted([t for t in teams if t != selected_team]):
        og = games[(games['Team_Name'] == selected_team) & (games['Opponent_Team_Name'] == opp) & (games['Game_Type'].isin([1, 2]))]
        if og.empty: continue
        w_cnt, l_cnt, t_cnt = int(og['W'].sum()), int(og['L'].sum()), int(og['T'].sum())
        tot_g = w_cnt + l_cnt + t_cnt
        wp = w_cnt / tot_g if tot_g > 0 else 0.0
        po_g = og[og['Game_Type'] == 2]
        po_rec = f"{int(po_g['W'].sum())}-{int(po_g['L'].sum())}" + (f"-{int(po_g['T'].sum())}" if po_g['T'].sum()>0 else "") if len(po_g)>0 else "-"
        opp_list.append({'Opponent': opp, 'GP': tot_g, 'W': w_cnt, 'L': l_cnt, 'T': t_cnt, 'Win_Pct_Raw': wp, 'Win %': f"{wp:.3f}".replace("0.", ".", 1) if wp < 1 else f"{wp:.3f}", 'PF': int(round(og['Actual_Points'].sum())), 'PA': int(round(og['Opp_Points'].sum())), 'Playoff Record': po_rec})
    if opp_list:
        render_html_table(pd.DataFrame(opp_list).sort_values(['Win_Pct_Raw', 'W', 'GP'], ascending=[False, False, False])[['Opponent', 'GP', 'W', 'L', 'Win %', 'PF', 'PA', 'Playoff Record']])
