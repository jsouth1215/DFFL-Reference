import streamlit as st
import pandas as pd
from utils import render_html_table, format_ordinal, get_playoff_outcome
from data_loader import (
    get_starter_performances,
    get_unique_starters_records,
    get_all_streaks_records,
    get_monday_comebacks
)

def apply_competition_rank(df, score_col, round_digits=2):
    if df.empty or score_col not in df.columns:
        return df
    ranks = []
    prev_val = None
    current_rank = 1
    for i, val in enumerate(df[score_col]):
        if pd.isna(val):
            ranks.append("")
            continue
        val_key = round(float(val), round_digits) if round_digits is not None and isinstance(val, (int, float)) else val
        if i == 0:
            ranks.append(str(current_rank))
            prev_val = val_key
        else:
            if val_key == prev_val:
                ranks.append("")
            else:
                current_rank = i + 1
                ranks.append(str(current_rank))
                prev_val = val_key
    df['Rank'] = ranks
    return df

def render(games, box_df, rs_ranks_df, completed_playoff_seasons, teams, teams_no_cam):
    rec_categories = {
        "Game Records": [
            "Highest Scoring Weeks",
            "Lowest Scoring Weeks",
            "Lowest Scoring Weekly Bags",
            "Largest Monday Night Comebacks",
            "Biggest Blowouts",
            "Closest Games"
        ],
        "Player Records": [
            "Highest Scoring Players",
            "Lowest Scoring Players",
            "Highest Scoring Stacks",
            "Most Unique Players Started",
            "Least Unique Players Started",
            "Most Fantasy Teams Started For",
            "Started on Same Fantasy Team for 3+ NFL Teams"
        ],
        "Season Records": [
            "Most Points Per Game in a Season",
            "Least Points Per Game in a Season",
            "Longest Win Streak",
            "Longest Losing Streak",
            "Highest Season Luck Factor",
            "Lowest Season Luck Factor"
        ],
        "Franchise Records": [
            "Team Record - Highest Score",
            "Team Record - Lowest Score",
            "Weekly Bag by Team",
            "Weekly Last Place Score by Team",
            "Playoff Record by Team"
        ]
    }
    if 'Top_2_Game' in games.columns:
        rec_categories["Game Records"].append("Top 2 Matchups")
    if 'Bottom_2_Game' in games.columns:
        rec_categories["Game Records"].append("Bottom 2 Matchups")

    sel_grp = st.radio("Record Category:", list(rec_categories.keys()), horizontal=True, key="rec_cat_group")
    rec_type = st.radio("Select Record:", rec_categories[sel_grp], horizontal=True, key="rec_sub_type")
    st.write("---")

    bag_szns = sorted([str(s).replace('.0','').strip() for s in games['Season'].unique() if str(s).replace('.0','').strip().isdigit() and int(str(s).replace('.0','').strip()) >= 2019], key=lambda x: int(x))
    lp_szns = sorted([str(s).replace('.0','').strip() for s in games['Season'].unique() if str(s).replace('.0','').strip().isdigit() and int(str(s).replace('.0','').strip()) >= 2017], key=lambda x: int(x))

    rs_map = {(str(r['Season']).replace('.0','').strip(), str(r['Team_Name']).strip()): format_ordinal(r['RS_Rank']) for _, r in rs_ranks_df.iterrows()} if not rs_ranks_df.empty and 'Team_Name' in rs_ranks_df.columns else {}
    po_all = games[games['Game_Type'] == 2]
    po_map = {(str(s).replace('.0','').strip(), str(t).strip()): get_playoff_outcome(grp) for (s, t), grp in po_all.groupby(['Season', 'Team_Name'])} if not po_all.empty else {}

    all_reg = games[games['Game_Type'] == 1].copy()
    if not all_reg.empty:
        all_reg['Season_Str'] = all_reg['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        all_reg['Weekly_Rank'] = all_reg.groupby(['Season_Str', 'Week_Num'])['Actual_Points'].rank(ascending=False, method='average')
        all_reg['N_Teams'] = all_reg.groupby(['Season_Str', 'Week_Num'])['Team_Name'].transform('count')
        all_reg['Exp_Win'] = all_reg.apply(lambda r: (r['N_Teams'] - r['Weekly_Rank']) / (r['N_Teams'] - 1) if r['N_Teams'] > 1 else 0.0, axis=1)
        
        s_agg = all_reg.groupby(['Season_Str', 'Team_Name']).agg(
            W=('W', 'sum'),
            L=('L', 'sum'),
            T=('T', 'sum'),
            PF=('Actual_Points', 'sum'),
            Exp_Win_Total=('Exp_Win', 'sum'),
            Games_Count=('W', 'count')
        ).reset_index()
        s_agg['Record'] = s_agg.apply(lambda r: f"{int(r['W'])}-{int(r['L'])}" + (f"-{int(r['T'])}" if r['T']>0 else ""), axis=1)
        s_agg['Luck_Num'] = s_agg['W'] - s_agg['Exp_Win_Total']
        s_agg['Expected Wins'] = s_agg['Exp_Win_Total'].apply(lambda x: f"{float(x):.1f}")
        s_agg['Luck Factor'] = s_agg['Luck_Num'].apply(lambda x: "0.0" if abs(x)<0.05 else f"{x:+.1f}")
        s_agg['PF_Formatted'] = s_agg['PF'].apply(lambda x: f"{float(x):.1f}")
        s_agg['PPG_Num'] = s_agg['PF'] / s_agg['Games_Count']
        s_agg['PF/G'] = s_agg['PPG_Num'].apply(lambda x: f"{float(x):.1f}")
        s_agg['Regular Season Finish'] = s_agg.apply(lambda r: rs_map.get((str(r['Season_Str']).strip(), str(r['Team_Name']).strip()), ""), axis=1)
        s_agg['Playoff Outcome'] = s_agg.apply(lambda r: po_map.get((str(r['Season_Str']).strip(), str(r['Team_Name']).strip()), ""), axis=1)
        s_agg = s_agg.rename(columns={'Season_Str': 'Season', 'Team_Name': 'Team'})
    else:
        s_agg = pd.DataFrame()

    s_comp = s_agg[s_agg['Season'].isin(completed_playoff_seasons)].copy() if not s_agg.empty else pd.DataFrame()

    if rec_type == "Highest Scoring Weeks":
        df = games[games['Game_Type'].isin([1, 2, 4])].copy()
        df['Points_Num'] = pd.to_numeric(df['Actual_Points'], errors='coerce')
        df = df.sort_values(['Points_Num', 'Season_Num', 'Week_Num'], ascending=[False, False, False]).head(15).reset_index(drop=True)
        df = apply_competition_rank(df, 'Points_Num', round_digits=1)
        df['Points'] = df['Points_Num'].apply(lambda x: f"{float(x):.1f}")
        render_html_table(df[['Rank', 'Season', 'Week', 'Team_Name', 'Points', 'Opponent_Team_Name']].rename(columns={'Team_Name': 'Team', 'Opponent_Team_Name': 'Opponent'}))

    elif rec_type == "Lowest Scoring Weeks":
        df = games[(games['Actual_Points'] > 0) & (games['Game_Type'].isin([1, 2]))].copy()
        df['Points_Num'] = pd.to_numeric(df['Actual_Points'], errors='coerce')
        df = df.sort_values(['Points_Num', 'Season_Num', 'Week_Num'], ascending=[True, False, False]).head(15).reset_index(drop=True)
        df = apply_competition_rank(df, 'Points_Num', round_digits=1)
        df['Points'] = df['Points_Num'].apply(lambda x: f"{float(x):.1f}")
        render_html_table(df[['Rank', 'Season', 'Week', 'Team_Name', 'Points', 'Opponent_Team_Name']].rename(columns={'Team_Name': 'Team', 'Opponent_Team_Name': 'Opponent'}))

    elif rec_type == "Lowest Scoring Weekly Bags":
        df = games[games['Is_High_Scorer']].copy()
        if not df.empty:
            df['Points_Num'] = pd.to_numeric(df['Actual_Points'], errors='coerce')
            df = df.sort_values(['Points_Num', 'Season_Num', 'Week_Num'], ascending=[True, False, False]).head(15).reset_index(drop=True)
            df = apply_competition_rank(df, 'Points_Num', round_digits=1)
            df['Points'] = df['Points_Num'].apply(lambda x: f"{float(x):.1f}")
            render_html_table(df[['Rank', 'Season', 'Week', 'Team_Name', 'Points', 'Opponent_Team_Name']].rename(columns={'Team_Name': 'Team', 'Opponent_Team_Name': 'Opponent'}))

    elif rec_type == "Largest Monday Night Comebacks":
        df = get_monday_comebacks(box_df, games)
        if not df.empty:
            df = apply_competition_rank(df, 'Deficit_Num', round_digits=1)
            cols = ['Rank', 'Deficit Overcome', 'Final Score', 'Winner', 'Loser', 'Season', 'Week', 'Winning Team Monday Players', 'Losing Team Monday Players']
            render_html_table(df[cols], left_align_cols=['Winning Team Monday Players', 'Losing Team Monday Players'])
        else:
            st.info("No Monday night comebacks found.")

    elif rec_type == "Biggest Blowouts":
        df = games[(games['W'] == 1) & (games['Game_Type'].isin([1, 2]))].copy()
        df['Margin_Num'] = pd.to_numeric(df['Margin'], errors='coerce')
        df = df.sort_values(['Margin_Num', 'Season_Num', 'Week_Num'], ascending=[False, False, False]).head(15).reset_index(drop=True)
        df = apply_competition_rank(df, 'Margin_Num', round_digits=1)
        df['Winner Pts'] = df['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
        df['Loser Pts'] = df['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
        df['Margin_Disp'] = df['Margin_Num'].apply(lambda x: f"{float(x):.1f}")
        render_html_table(df[['Rank', 'Season', 'Week', 'Team_Name', 'Winner Pts', 'Opponent_Team_Name', 'Loser Pts', 'Margin_Disp']].rename(columns={'Team_Name': 'Winner', 'Opponent_Team_Name': 'Loser', 'Margin_Disp': 'Margin'}))

    elif rec_type == "Closest Games":
        df = games[(games['W'] == 1) & (games['Margin'] > 0) & (games['Margin'] <= 1.00) & (games['Game_Type'].isin([1, 2]))].copy()
        if not df.empty:
            df['Margin_Num'] = pd.to_numeric(df['Margin'], errors='coerce')
            df = df.sort_values(['Margin_Num', 'Season_Num', 'Week_Num'], ascending=[True, False, False]).reset_index(drop=True)
            df = apply_competition_rank(df, 'Margin_Num', round_digits=2)
            df['Winner Pts'] = df['Actual_Points'].apply(lambda x: f"{float(x):.2f}")
            df['Loser Pts'] = df['Opp_Points'].apply(lambda x: f"{float(x):.2f}")
            df['Margin_Disp'] = df['Margin_Num'].apply(lambda x: f"{float(x):.2f}")
            render_html_table(df[['Rank', 'Season', 'Week', 'Team_Name', 'Winner Pts', 'Opponent_Team_Name', 'Loser Pts', 'Margin_Disp']].rename(columns={'Team_Name': 'Winner', 'Opponent_Team_Name': 'Loser', 'Margin_Disp': 'Margin'}))
        else:
            st.info("No games decided by 1.00 point or less.")

    elif rec_type == "Top 2 Matchups":
        if 'Top_2_Game' in games.columns:
            top2_mask = games['Top_2_Game'].astype(str).str.strip().str.lower().isin(['1', '1.0', 'yes', 'true', 'y'])
            top2 = games[top2_mask].sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).drop_duplicates(subset=['Season', 'Week']).copy()
            top2['Season'] = top2['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            top2['Actual_Points'] = top2['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
            top2['Opp_Points'] = top2['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
            top2['Margin'] = top2['Margin'].apply(lambda x: f"{float(x):.1f}")
            render_html_table(top2[['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points', 'Margin']].rename(columns={'Team_Name': 'Team 1', 'Actual_Points': 'Team 1 Pts', 'Opponent_Team_Name': 'Team 2', 'Opp_Points': 'Team 2 Pts'}))

    elif rec_type == "Bottom 2 Matchups":
        if 'Bottom_2_Game' in games.columns:
            bot2_mask = games['Bottom_2_Game'].astype(str).str.strip().str.lower().isin(['1', '1.0', 'yes', 'true', 'y'])
            bot2 = games[bot2_mask].sort_values(['Season_Num', 'Week_Num'], ascending=[False, False]).drop_duplicates(subset=['Season', 'Week']).copy()
            bot2['Season'] = bot2['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            bot2['Actual_Points'] = bot2['Actual_Points'].apply(lambda x: f"{float(x):.1f}")
            bot2['Opp_Points'] = bot2['Opp_Points'].apply(lambda x: f"{float(x):.1f}")
            bot2['Margin'] = bot2['Margin'].apply(lambda x: f"{float(x):.1f}")
            render_html_table(bot2[['Season', 'Week', 'Team_Name', 'Actual_Points', 'Opponent_Team_Name', 'Opp_Points', 'Margin']].rename(columns={'Team_Name': 'Team 1', 'Actual_Points': 'Team 1 Pts', 'Opponent_Team_Name': 'Team 2', 'Opp_Points': 'Team 2 Pts'}))

    elif rec_type == "Highest Scoring Players":
        p = get_starter_performances(box_df, games)
        if not p.empty:
            top = p.sort_values(['Points_Num', 'Season', 'Week'], ascending=[False, False, False]).head(15).reset_index(drop=True)
            top = apply_competition_rank(top, 'Points_Num', round_digits=1)
            top['Points'] = top['Points_Num'].apply(lambda x: f"{float(x):.1f}")
            render_html_table(top[['Rank', 'Player', 'Pos', 'NFL Team', 'Points', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']])

    elif rec_type == "Lowest Scoring Players":
        p = get_starter_performances(box_df, games)
        if not p.empty:
            st.write("### Lowest Scoring Starters (All Positions)")
            low = p.sort_values(['Points_Num', 'Season', 'Week'], ascending=[True, False, False]).head(15).reset_index(drop=True)
            low = apply_competition_rank(low, 'Points_Num', round_digits=1)
            low['Points'] = low['Points_Num'].apply(lambda x: f"{float(x):.1f}")
            render_html_table(low[['Rank', 'Player', 'Pos', 'NFL Team', 'Points', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']])

            st.write("### Negative Point Starters (Non-Defense)")
            neg = p[(~p['Pos'].isin(['D/ST', 'DST', 'DEF', 'DP'])) & (p['Points_Num'] < 0)].sort_values(['Points_Num', 'Season', 'Week'], ascending=[True, False, False]).reset_index(drop=True)
            if not neg.empty:
                neg = apply_competition_rank(neg, 'Points_Num', round_digits=1)
                neg['Points'] = neg['Points_Num'].apply(lambda x: f"{float(x):.1f}")
                render_html_table(neg[['Rank', 'Player', 'Pos', 'NFL Team', 'Points', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']])

    elif rec_type == "Highest Scoring Stacks":
        p = get_starter_performances(box_df, games)
        if not p.empty:
            stks = []
            for (s, w, tm), g_df in p.groupby(['Season', 'Week', 'Team']):
                qbs, catchers = g_df[g_df['Pos'] == 'QB'], g_df[g_df['Pos'].isin(['WR', 'TE'])]
                for _, qr in qbs.iterrows():
                    nfl = str(qr['NFL Team']).strip()
                    if nfl and nfl not in ['-', 'FA']:
                        for _, cr in catchers[catchers['NFL Team'].astype(str).str.strip() == nfl].iterrows():
                            comb = float(qr['Points_Num']) + float(cr['Points_Num'])
                            stks.append({
                                'QB': f"{qr['Player']} ({float(qr['Points_Num']):.1f})",
                                'Pass Catcher': f"{cr['Player']} ({float(cr['Points_Num']):.1f})",
                                'Pos': cr['Pos'],
                                'NFL Team': nfl,
                                'Combined_Num': comb,
                                'Combined Pts': f"{comb:.1f}",
                                'Season': s,
                                'Week': w,
                                'Team': tm,
                                'Opponent': qr['Opponent'],
                                'Outcome': qr['Outcome']
                            })
            if stks:
                res = pd.DataFrame(stks).sort_values(['Combined_Num', 'Season', 'Week'], ascending=[False, False, False]).head(15).reset_index(drop=True)
                res = apply_competition_rank(res, 'Combined_Num', round_digits=1)
                render_html_table(res[['Rank', 'QB', 'Pass Catcher', 'Pos', 'NFL Team', 'Combined Pts', 'Season', 'Week', 'Team', 'Opponent', 'Outcome']])

    elif rec_type in ["Most Unique Players Started", "Least Unique Players Started"]:
        is_least = (rec_type == "Least Unique Players Started")
        st_data, name_col = get_unique_starters_records(box_df, games, completed_only=is_least, completed_playoff_seasons=completed_playoff_seasons)
        if not st_data.empty:
            pf = st.radio("Position Filter:", ["All Positions", "QB", "RB", "WR", "TE", "K", "D/ST"], horizontal=True, key=f"pos_{rec_type}")
            sub = st_data if pf == "All Positions" else st_data[st_data['Clean_Pos'] == pf]
            rows = []
            for (s, tm), grp in sub.groupby(['Season_Str', 'Team_Str']):
                pl = sorted(list(set(str(x).strip() for x in grp[name_col].dropna().unique() if str(x).strip())))
                rows.append({
                    'Season': s,
                    'Team': tm,
                    'Players Started': len(pl),
                    'Regular Season Finish': rs_map.get((s, tm), ""),
                    'Playoff Outcome': po_map.get((s, tm), ""),
                    'Player List': ", ".join(pl)
                })
            if rows:
                df = pd.DataFrame(rows).sort_values(['Players Started', 'Season'], ascending=[is_least, False]).head(15).reset_index(drop=True)
                df = apply_competition_rank(df, 'Players Started', round_digits=0)
                render_html_table(df[['Rank', 'Season', 'Team', 'Players Started', 'Regular Season Finish', 'Playoff Outcome', 'Player List']], left_align_cols=['Player List'])

    elif rec_type == "Most Fantasy Teams Started For":
        p = get_starter_performances(box_df, games)
        if not p.empty:
            trav = [{'Player': pl, 'Pos': grp['Pos'].mode().iloc[0], 'Teams Count': len(set(grp['Team'])), 'Fantasy Teams': ", ".join(sorted(set(grp['Team'])))} for pl, grp in p[~p['Pos'].isin(['D/ST', 'DST', 'DEF', 'DP'])].groupby('Player') if len(set(grp['Team'])) > 1]
            if trav:
                df = pd.DataFrame(trav).sort_values(['Teams Count', 'Player'], ascending=[False, True]).head(15).reset_index(drop=True)
                df = apply_competition_rank(df, 'Teams Count', round_digits=0)
                render_html_table(df[['Rank', 'Player', 'Pos', 'Teams Count', 'Fantasy Teams']], left_align_cols=['Fantasy Teams'])

    elif rec_type == "Started on Same Fantasy Team for 3+ NFL Teams":
        p = get_starter_performances(box_df, games)
        if not p.empty:
            journeys = []
            for (pl, tm), grp in p[~p['Pos'].isin(['D/ST', 'DST', 'DEF', 'DP'])].groupby(['Player', 'Team']):
                nfls = sorted(set(t for t in grp['NFL Team'] if t and t not in ['-', 'FA', 'NONE']))
                if len(nfls) >= 3:
                    journeys.append({
                        'Player': pl,
                        'Pos': grp['Pos'].mode().iloc[0],
                        'Fantasy Team': tm,
                        'NFL Teams Count': len(nfls),
                        'NFL Teams': ", ".join(nfls)
                    })
            if journeys:
                df = pd.DataFrame(journeys).sort_values(['NFL Teams Count', 'Player'], ascending=[False, True]).reset_index(drop=True)
                df = apply_competition_rank(df, 'NFL Teams Count', round_digits=0)
                render_html_table(df[['Rank', 'Player', 'Pos', 'Fantasy Team', 'NFL Teams Count', 'NFL Teams']], left_align_cols=['NFL Teams'])

    elif rec_type == "Most Points Per Game in a Season":
        if not s_agg.empty:
            top = s_agg.sort_values(['PPG_Num', 'Season'], ascending=[False, False]).head(15).reset_index(drop=True)
            top = apply_competition_rank(top, 'PPG_Num', round_digits=1)
            top['Season_Display'] = top['Season'].apply(lambda s: f"{s}*" if str(s) == '2026' else str(s))
            render_html_table(
                top[['Rank', 'Season_Display', 'Team', 'Record', 'PF/G', 'PF_Formatted', 'Regular Season Finish', 'Playoff Outcome']].rename(columns={'Season_Display': 'Season', 'PF_Formatted': 'PF'}),
                highlight_fn=lambda r: ['font-style: italic; color: #1e3a8a;' if '*' in str(r.get('Season','')) else '' for _ in r.index]
            )
            if any(top['Season'] == '2026'):
                st.caption(r"\* *Active season*")

    elif rec_type == "Least Points Per Game in a Season":
        if not s_agg.empty:
            low = s_agg[s_agg['Season'] != '2017'].sort_values(['PPG_Num', 'Season'], ascending=[True, False]).head(20).reset_index(drop=True)
            low = apply_competition_rank(low, 'PPG_Num', round_digits=1)
            low['Season_Display'] = low['Season'].apply(lambda s: f"{s}*" if str(s) == '2026' else str(s))
            render_html_table(
                low[['Rank', 'Season_Display', 'Team', 'Record', 'PF/G', 'PF_Formatted', 'Regular Season Finish', 'Playoff Outcome']].rename(columns={'Season_Display': 'Season', 'PF_Formatted': 'PF'}),
                highlight_fn=lambda r: ['font-style: italic; color: #1e3a8a;' if '*' in str(r.get('Season','')) else '' for _ in r.index]
            )
            if any(low['Season'] == '2026'):
                st.caption(r"\* *Active season*")

    elif rec_type == "Longest Win Streak":
        w_df, _ = get_all_streaks_records(games)
        if not w_df.empty:
            df = w_df.sort_values(['Length', 'Season'], ascending=[False, False]).head(15).reset_index(drop=True)
            df = apply_competition_rank(df, 'Length', round_digits=0)
            df['Regular Season Finish'] = df.apply(lambda r: rs_map.get((str(r['Season']).strip(), str(r['Team']).strip()), ""), axis=1)
            df['Playoff Outcome'] = df.apply(lambda r: po_map.get((str(r['Season']).strip(), str(r['Team']).strip()), ""), axis=1)
            render_html_table(df[['Rank', 'Team', 'Season', 'Length', 'Span', 'Regular Season Finish', 'Playoff Outcome']].rename(columns={'Length': 'Streak'}))

    elif rec_type == "Longest Losing Streak":
        _, l_df = get_all_streaks_records(games)
        if not l_df.empty:
            df = l_df[l_df['Length'] >= 6].sort_values(['Length', 'Season'], ascending=[False, False]).reset_index(drop=True)
            if not df.empty:
                df = apply_competition_rank(df, 'Length', round_digits=0)
                df['Regular Season Finish'] = df.apply(lambda r: rs_map.get((str(r['Season']).strip(), str(r['Team']).strip()), ""), axis=1)
                df['Playoff Outcome'] = df.apply(lambda r: po_map.get((str(r['Season']).strip(), str(r['Team']).strip()), ""), axis=1)
                render_html_table(df[['Rank', 'Team', 'Season', 'Length', 'Span', 'Regular Season Finish', 'Playoff Outcome']].rename(columns={'Length': 'Streak'}))
            else:
                st.info("No losing streaks of 6 or more games on record.")

    elif rec_type == "Highest Season Luck Factor":
        if not s_comp.empty:
            df = s_comp[s_comp['Luck_Num'].round(1) >= 2.0].sort_values(['Luck_Num', 'Season'], ascending=[False, False]).reset_index(drop=True)
            if not df.empty:
                df = apply_competition_rank(df, 'Luck_Num', round_digits=1)
                render_html_table(df[['Rank', 'Season', 'Team', 'Record', 'Expected Wins', 'Luck Factor', 'Regular Season Finish', 'Playoff Outcome']])
            else:
                st.info("No completed seasons with a Luck Factor of +2.0 or higher.")

    elif rec_type == "Lowest Season Luck Factor":
        if not s_comp.empty:
            df = s_comp[s_comp['Luck_Num'].round(1) <= -2.0].sort_values(['Luck_Num', 'Season'], ascending=[True, False]).reset_index(drop=True)
            if not df.empty:
                df = apply_competition_rank(df, 'Luck_Num', round_digits=1)
                render_html_table(df[['Rank', 'Season', 'Team', 'Record', 'Expected Wins', 'Luck Factor', 'Regular Season Finish', 'Playoff Outcome']])
            else:
                st.info("No completed seasons with a Luck Factor of -2.0 or lower.")

    elif rec_type == "Team Record - Highest Score":
        scores = [{'Team': t, 'Points_Num': float(games[games['Team_Name']==t].loc[games[games['Team_Name']==t]['Actual_Points'].idxmax()]['Actual_Points']), 'Points': f"{float(games[games['Team_Name']==t].loc[games[games['Team_Name']==t]['Actual_Points'].idxmax()]['Actual_Points']):.1f}", 'Season': str(games[games['Team_Name']==t].loc[games[games['Team_Name']==t]['Actual_Points'].idxmax()]['Season']).replace('.0',''), 'Week': games[games['Team_Name']==t].loc[games[games['Team_Name']==t]['Actual_Points'].idxmax()]['Week'], 'Opponent': games[games['Team_Name']==t].loc[games[games['Team_Name']==t]['Actual_Points'].idxmax()]['Opponent_Team_Name']} for t in teams_no_cam if not games[games['Team_Name']==t].empty]
        if scores:
            df = pd.DataFrame(scores).sort_values(['Points_Num', 'Season'], ascending=[False, False]).reset_index(drop=True)
            df = apply_competition_rank(df, 'Points_Num', round_digits=1)
            render_html_table(df[['Rank', 'Team', 'Points', 'Season', 'Week', 'Opponent']])

    elif rec_type == "Team Record - Lowest Score":
        scores = [{'Team': t, 'Points_Num': float(games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].loc[games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)]['Actual_Points'].idxmin()]['Actual_Points']), 'Points': f"{float(games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].loc[games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)]['Actual_Points'].idxmin()]['Actual_Points']):.1f}", 'Season': str(games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].loc[games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)]['Actual_Points'].idxmin()]['Season']).replace('.0',''), 'Week': games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].loc[games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)]['Actual_Points'].idxmin()]['Week'], 'Opponent': games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].loc[games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)]['Actual_Points'].idxmin()]['Opponent_Team_Name']} for t in teams_no_cam if not games[(games['Team_Name']==t) & (games['Game_Type'].isin([1, 2])) & (games['Actual_Points']>0)].empty]
        if scores:
            df = pd.DataFrame(scores).sort_values(['Points_Num', 'Season'], ascending=[True, False]).reset_index(drop=True)
            df = apply_competition_rank(df, 'Points_Num', round_digits=1)
            render_html_table(df[['Rank', 'Team', 'Points', 'Season', 'Week', 'Opponent']])

    elif rec_type == "Weekly Bag by Team":
        data = [{'Team': t, **{s: int(games[(games['Team_Name']==t) & (games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()==s) & (games['Is_High_Scorer'])]['Is_High_Scorer'].sum()) for s in bag_szns}, 'Total': int(games[(games['Team_Name']==t) & (games['Season'].isin(bag_szns)) & (games['Is_High_Scorer'])]['Is_High_Scorer'].sum())} for t in teams_no_cam]
        render_html_table(pd.DataFrame(data).sort_values(['Total', 'Team'], ascending=[False, True])[['Team'] + bag_szns + ['Total']])

    elif rec_type == "Weekly Last Place Score by Team":
        reg = games[(games['Game_Type'] == 1) & (games['Season_Num'] >= 2017)].copy()
        min_p = reg.groupby(['Season', 'Week'])['Actual_Points'].transform('min')
        reg['Is_Low'] = (reg['Actual_Points'] == min_p)
        data = [{'Team': t, **{s: int(reg[(reg['Team_Name']==t) & (reg['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()==s)]['Is_Low'].sum()) for s in lp_szns}, 'Total': int(reg[(reg['Team_Name']==t) & (reg['Season'].isin(lp_szns))]['Is_Low'].sum())} for t in teams]
        render_html_table(pd.DataFrame(data).sort_values(['Total', 'Team'], ascending=[False, True])[['Team'] + lp_szns + ['Total']])

    elif rec_type == "Playoff Record by Team":
        po_rows = []
        for t in teams_no_cam:
            apps, byes = 0, 0
            if not rs_ranks_df.empty and 'Team_Name' in rs_ranks_df.columns:
                for _, r in rs_ranks_df[rs_ranks_df['Team_Name'] == t].iterrows():
                    szn = str(r['Season']).strip()
                    if szn.isdigit() and szn in completed_playoff_seasons:
                        s_int, rk = int(szn), float(r['RS_Rank'])
                        if pd.notnull(rk):
                            if (s_int == 2017 and rk <= 4) or (s_int > 2017 and rk <= 6): apps += 1
                            if s_int >= 2018 and rk <= 2: byes += 1
            pg = games[(games['Team_Name'] == t) & (games['Game_Type'] == 2)]
            r_str = pg['Playoff_Round'].astype(str).str.strip().str.lower()
            qf, sf, f = pg[r_str.str.contains('quarter')], pg[r_str.str.contains('semi')], pg[r_str.str.contains('final|champ') & ~r_str.str.contains('quarter|semi')]
            po_rows.append({
                'Team': t,
                'Appearances': apps,
                'Byes': byes,
                'Total_W': int(qf['W'].sum() + sf['W'].sum() + f['W'].sum()),
                'Total_L': int(qf['L'].sum() + sf['L'].sum() + f['L'].sum()),
                'QF_W': int(qf['W'].sum()),
                'QF_L': int(qf['L'].sum()),
                'SF_W': int(sf['W'].sum()),
                'SF_L': int(sf['L'].sum()),
                'F_W': int(f['W'].sum()),
                'F_L': int(f['L'].sum())
            })
        df_po = pd.DataFrame(po_rows).sort_values(['Appearances', 'Total_W', 'Byes'], ascending=[False, False, False])
        po_html = '<table style="width: 100%; border-collapse: collapse; text-align: center;"><thead><tr><th rowspan="2" style="border: 1px solid #e6e6e6;">Team</th><th rowspan="2" style="border: 1px solid #e6e6e6;">Playoff Appearances</th><th rowspan="2" style="border: 1px solid #e6e6e6;">Byes</th><th colspan="2" style="border: 1px solid #e6e6e6;">Total Postseason</th><th colspan="2" style="border: 1px solid #e6e6e6;">Quarterfinals</th><th colspan="2" style="border: 1px solid #e6e6e6;">Semifinals</th><th colspan="2" style="border: 1px solid #e6e6e6;">Finals</th></tr><tr><th style="border: 1px solid #e6e6e6;">W</th><th style="border: 1px solid #e6e6e6;">L</th><th style="border: 1px solid #e6e6e6;">W</th><th style="border: 1px solid #e6e6e6;">L</th><th style="border: 1px solid #e6e6e6;">W</th><th style="border: 1px solid #e6e6e6;">L</th><th style="border: 1px solid #e6e6e6;">W</th><th style="border: 1px solid #e6e6e6;">L</th></tr></thead><tbody>' + "".join([f'<tr><td style="border: 1px solid #e6e6e6;">{r["Team"]}</td><td style="border: 1px solid #e6e6e6;">{r["Appearances"]}</td><td style="border: 1px solid #e6e6e6;">{r["Byes"]}</td><td style="border: 1px solid #e6e6e6;">{r["Total_W"]}</td><td style="border: 1px solid #e6e6e6;">{r["Total_L"]}</td><td style="border: 1px solid #e6e6e6;">{r["QF_W"]}</td><td style="border: 1px solid #e6e6e6;">{r["QF_L"]}</td><td style="border: 1px solid #e6e6e6;">{r["SF_W"]}</td><td style="border: 1px solid #e6e6e6;">{r["SF_L"]}</td><td style="border: 1px solid #e6e6e6;">{r["F_W"]}</td><td style="border: 1px solid #e6e6e6;">{r["F_L"]}</td></tr>' for _, r in df_po.iterrows()]) + '</tbody></table>'
        st.markdown(po_html, unsafe_allow_html=True)
        
