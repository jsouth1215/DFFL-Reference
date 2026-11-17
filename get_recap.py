import os
import argparse
import pandas as pd
import app
import odds_engine

def generate_recap(szn="2026", wk=None):
    games = app.games
    box = app.box_df
    
    comp_games = games[games['Game_Type'].isin([0, 1, 2])].copy()
    comp_games['Season_Str'] = comp_games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    comp_games['Week_Num'] = pd.to_numeric(comp_games['Week'], errors='coerce')
    comp_games['Pts_Num'] = pd.to_numeric(comp_games['Actual_Points'], errors='coerce')
    
    comp_games = comp_games[comp_games['Pts_Num'] > 0]
    
    if wk is None:
        szn_games = comp_games[comp_games['Season_Str'] == szn]
        wk = int(szn_games['Week_Num'].max()) if not szn_games.empty else 1
        
    curr = comp_games[(comp_games['Season_Str'] == szn) & (comp_games['Week_Num'] == wk)]
    if curr.empty:
        print(f"No completed data found for {szn} Week {wk} yet.")
        return

    hist = comp_games[~((comp_games['Season_Str'] == szn) & (comp_games['Week_Num'] == wk))]
    
    recap_lines = [f"🏈 **DFFL {szn} Week {wk} Commissioner Briefing** 🏈\n"]
    
    # 1. Weekly Awards
    max_pts = curr['Pts_Num'].max()
    min_pts = curr[curr['Pts_Num'] > 0]['Pts_Num'].min()
    high_tm = curr[curr['Pts_Num'] == max_pts]['Team_Name'].iloc[0] if not curr.empty else "N/A"
    low_tm = curr[curr['Pts_Num'] == min_pts]['Team_Name'].iloc[0] if not curr.empty else "N/A"
    
    recap_lines.append(f"💰 **The Weekly Bag:** {high_tm} ({max_pts:.1f} pts)")
    recap_lines.append(f"🚽 **The Cellar:** {low_tm} ({min_pts:.1f} pts)\n")
    
    # 2. H2H & Matchup Margins
    recap_lines.append("⚔️ **Matchup Notes & H2H History:**")
    for _, g in curr[curr['W'] == 1].iterrows():
        margin = float(g['Margin'])
        w_tm = g['Team_Name']
        l_tm = g['Opponent_Team_Name']
        
        h2h = comp_games[((comp_games['Team_Name'] == w_tm) & (comp_games['Opponent_Team_Name'] == l_tm))]
        w_wins = h2h['W'].sum()
        l_wins = h2h['L'].sum()
        
        msg = f"  • **{w_tm}** defeated {l_tm} by {margin:.1f} pts. "
        if margin <= 1.5:
            msg = f"  😬 **Nail-Biter:** {w_tm} edged out {l_tm} by just {margin:.2f} pts! "
        elif margin >= 50.0:
            msg = f"  🚑 **Blowout:** {w_tm} demolished {l_tm} by {margin:.1f} pts. "
            
        if w_wins > l_wins:
            msg += f"(All-Time Series: {w_tm} leads {w_wins}-{l_wins})"
        elif l_wins > w_wins:
            msg += f"(All-Time Series: {l_tm} leads {l_wins}-{w_wins})"
        else:
            msg += f"(All-Time Series: Tied {w_wins}-{l_wins})"
            
        recap_lines.append(msg)
    recap_lines.append("")
    
    # 3. Streaks
    recap_lines.append("🚂 **Current Streaks:**")
    streak_lines = []
    for tm in curr['Team_Name'].unique():
        tm_games = comp_games[(comp_games['Team_Name'] == tm) & (comp_games['Season_Str'] == szn)].sort_values('Week_Num', ascending=False)
        if not tm_games.empty:
            results = tm_games['W'].tolist()
            streak = 0
            is_w = results[0] == 1
            for r in results:
                if (r == 1) == is_w: streak += 1
                else: break
            if streak >= 3:
                s_type = "Win" if is_w else "Losing"
                emoji = "🔥" if is_w else "🥶"
                streak_lines.append(f"  {emoji} {tm} is on a {streak}-game {s_type.lower()} streak.")
    
    if streak_lines:
        recap_lines.extend(sorted(streak_lines))
    else:
        recap_lines.append("  *No active streaks of 3+ games.*")
    recap_lines.append("")
    
    # 4. Monday Night Comebacks
    try:
        mnf_df = app.get_monday_comebacks(box, games)
        mnf_wk = mnf_df[(mnf_df['Season'].astype(str).str.contains(szn)) & (pd.to_numeric(mnf_df['Week']) == wk)]
        if not mnf_wk.empty:
            recap_lines.append("🌙 **Monday Night Miracles:**")
            for _, row in mnf_wk.iterrows():
                recap_lines.append(f"  • {row['Winner']} overcame a {row['Deficit Overcome']:.1f} pt deficit on MNF against {row['Loser']}!")
            recap_lines.append("")
    except Exception:
        pass

    # 5. Playoff Odds Changes & Clinches
    recap_lines.append("🔮 **Playoff Odds Watch (Week-Over-Week):**")
    try:
        szn_g = comp_games[(comp_games['Season_Str'] == szn) & (comp_games['Game_Type'].isin([0, 1]))].copy()
        recs_curr = szn_g[szn_g['Week_Num'] <= wk][['Week_Num', 'Team_Name', 'Opponent_Team_Name', 'Actual_Points', 'Opp_Points', 'W', 'L', 'T']].to_dict('records')
        odds_curr, _ = odds_engine.run_playoff_odds_simulation_cached(szn, wk, recs_curr, n_wl_scenarios=5000)
        recs_prev = szn_g[szn_g['Week_Num'] <= wk - 1][['Week_Num', 'Team_Name', 'Opponent_Team_Name', 'Actual_Points', 'Opp_Points', 'W', 'L', 'T']].to_dict('records')
        odds_prev, _ = odds_engine.run_playoff_odds_simulation_cached(szn, wk - 1, recs_prev, n_wl_scenarios=5000)
        
        merged = odds_curr.merge(odds_prev, on='Team', suffixes=('_c', '_p'))
        odds_updates = []
        for _, r in merged.iterrows():
            tm = r['Team']
            pct_c = str(r['Playoff %_c'])
            pct_p = str(r['Playoff %_p'])
            if ">99.9" in pct_c and ">99.9" not in pct_p:
                odds_updates.append(f"  🎉 **VIRTUAL LOCK:** {tm} has statistically clinched a playoff spot (>99.9% in sims)!")
            elif "<0.1" in pct_c and "<0.1" not in pct_p:
                odds_updates.append(f"  🪦 **FADE 'EM:** {tm} is statistically eliminated (<0.1% in sims).")
            else:
                try:
                    val_c = float(pct_c.replace('%', '').replace('>', '').replace('<', ''))
                    val_p = float(pct_p.replace('%', '').replace('>', '').replace('<', ''))
                    diff = val_c - val_p
                    if diff >= 12.0:
                        odds_updates.append(f"  📈 **Stock Up:** {tm}'s playoff odds jumped +{diff:.1f}% (Now {pct_c})")
                    elif diff <= -12.0:
                        odds_updates.append(f"  📉 **Stock Down:** {tm}'s playoff odds fell {abs(diff):.1f}% (Now {pct_c})")
                except:
                    pass
        if odds_updates:
            recap_lines.extend(odds_updates)
        else:
            recap_lines.append("  *No major swings (>12%) or clinches this week.*")
    except Exception as e:
        recap_lines.append(f"  *(Could not calculate week-over-week odds: {e})*")
    recap_lines.append("")

    # 6. League-Wide History Watch (2017+)
    recap_lines.append("🌍 **League-Wide History Watch (2017-Present):**")
    modern = comp_games[comp_games['Season_Str'].str.isnumeric()].copy()
    modern = modern[(modern['Season_Str'].astype(int) >= 2017) & (modern['Pts_Num'] > 0)]
    
    weekly_stats = []
    for (s, w), group in modern.groupby(['Season_Str', 'Week_Num']):
        scores = group['Pts_Num'].sort_values(ascending=False).tolist()
        if len(scores) >= 10:
            tot = sum(scores)
            bag = scores[0]
            second = scores[1]
            cellar = scores[-1]
            diff_1_last = bag - cellar
            diff_1_2 = bag - second
            weekly_stats.append({'Season': s, 'Week': w, 'Total': tot, 'Diff_1_Last': diff_1_last, 'Diff_1_2': diff_1_2})
            
    ws_df = pd.DataFrame(weekly_stats)
    league_flags = False
    
    if not ws_df.empty:
        curr_ws = ws_df[(ws_df['Season'] == str(szn)) & (ws_df['Week'] == wk)]
        if not curr_ws.empty:
            c_tot = curr_ws.iloc[0]['Total']
            c_dlast = curr_ws.iloc[0]['Diff_1_Last']
            c_d2 = curr_ws.iloc[0]['Diff_1_2']
            
            top10_tot = ws_df['Total'].nlargest(10).min()
            bot10_tot = ws_df['Total'].nsmallest(10).max()
            top10_diff = ws_df['Diff_1_Last'].nlargest(10).min()
            bot10_bag = ws_df[ws_df['Diff_1_2'] > 0]['Diff_1_2'].nsmallest(10).max()
            
            if c_tot >= top10_tot:
                recap_lines.append(f"  🌋 **Scoring Explosion:** The league dropped {c_tot:.1f} total pts, entering the Top 10 highest-scoring weeks since 2017!")
                league_flags = True
            elif c_tot <= bot10_tot:
                recap_lines.append(f"  📉 **Offensive Drought:** The league managed only {c_tot:.1f} total pts, entering the Top 10 lowest-scoring weeks since 2017.")
                league_flags = True
                
            if c_dlast >= top10_diff:
                recap_lines.append(f"  ⚖️ **The Great Divide:** The {c_dlast:.1f} pt gap between 1st ({high_tm}) and last ({low_tm}) is a Top 10 largest discrepancy since 2017!")
                league_flags = True
                
            if c_d2 <= bot10_bag:
                curr_sorted = curr.sort_values('Pts_Num', ascending=False)
                bag_pts = curr_sorted.iloc[0]['Pts_Num']
                
                # Multi-team bag battles: Find anyone within 3 points of the runner-up score
                contenders = curr_sorted[(curr_sorted['Pts_Num'] >= bag_pts - c_d2 - 3.0) & (curr_sorted['Team_Name'] != high_tm)]['Team_Name'].tolist()
                
                if len(contenders) > 2:
                    contender_str = ", ".join(contenders[:-1]) + f", and {contenders[-1]}"
                elif len(contenders) == 2:
                    contender_str = f"{contenders[0]} and {contenders[1]}"
                else:
                    contender_str = contenders[0]
                
                unpaid_str = " (Unpaid)*" if str(szn) in ["2017", "2018"] else ""
                recap_lines.append(f"  ⚔️ **Bloody Bag Battle:** {high_tm} edged out {contender_str} for the Weekly Bag{unpaid_str} by just {c_d2:.2f} pts—a Top 10 closest race for 1st since 2017!")
                league_flags = True
                
    if not league_flags:
        recap_lines.append("  *No league-wide scoring extremes breached this week.*")
    recap_lines.append("")

    # 7. Expanded Record Book Watch (Individual)
    top15_alltime = hist['Pts_Num'].nlargest(15).min()
    bot15_alltime = hist[hist['Pts_Num'] > 0]['Pts_Num'].nsmallest(15).max()
    losses = hist[hist['L'] == 1]
    wins = hist[(hist['W'] == 1) & (hist['Pts_Num'] > 0)]
    top15_loss = losses['Pts_Num'].nlargest(15).min() if not losses.empty else 999
    bot15_win = wins['Pts_Num'].nsmallest(15).max() if not wins.empty else 0
    top15_margin = hist['Margin'].nlargest(15).min()
    bot15_margin = hist[hist['Margin'] > 0]['Margin'].nsmallest(15).max()
    
    records_flagged = False
    recap_lines.append("🏆 **Individual Record Book Watch:**")
    for _, g in curr.iterrows():
        tm = g['Team_Name']
        pts = g['Pts_Num']
        is_win = g['W'] == 1
        margin = float(g['Margin'])
        if pts >= top15_alltime:
            recap_lines.append(f"  🔥 **Historic High:** {tm} dropped {pts:.1f} pts, entering the Top 15 highest scores in DFFL history.")
            records_flagged = True
        elif pts > 0 and pts <= bot15_alltime:
            recap_lines.append(f"  🧊 **Historic Low:** {tm} struggled with {pts:.1f} pts, entering the Bottom 15 scores in DFFL history.")
            records_flagged = True
        if not is_win and pts >= top15_loss:
            recap_lines.append(f"  😭 **Highest Scoring Loss:** {tm} lost despite scoring {pts:.1f} pts (a Top 15 Highest Scoring Loss all-time).")
            records_flagged = True
        if is_win and pts <= bot15_win:
            recap_lines.append(f"  🍀 **Lowest Scoring Win:** {tm} won with just {pts:.1f} pts (a Top 15 Lowest Scoring Win all-time).")
            records_flagged = True
        if is_win:
            if margin >= top15_margin:
                recap_lines.append(f"  🚑 **Historic Blowout:** {tm} won by {margin:.1f} pts (a Top 15 biggest blowout in league history).")
                records_flagged = True
            elif 0 < margin <= bot15_margin:
                recap_lines.append(f"  😬 **Historic Nail-Biter:** {tm} won by just {margin:.2f} pts (a Top 15 closest game in league history).")
                records_flagged = True
        tm_hist = hist[hist['Team_Name'] == tm]
        if not tm_hist.empty:
            tm_max = tm_hist['Pts_Num'].max()
            tm_min = tm_hist[tm_hist['Pts_Num'] > 0]['Pts_Num'].min()
            if pts > tm_max:
                recap_lines.append(f"  🚀 **Franchise Record:** {tm} set a new personal all-time high with {pts:.1f} pts! (Previous: {tm_max:.1f})")
                records_flagged = True
            elif pts > 0 and pts < tm_min:
                recap_lines.append(f"  📉 **Franchise Worst:** {tm} set a new personal all-time low with {pts:.1f} pts. (Previous: {tm_min:.1f})")
                records_flagged = True
    if not records_flagged:
        recap_lines.append("  *No franchise or individual all-time records broken this week.*")
    recap_lines.append("")
    
    # 8. Brutal Beats
    bad_beats = []
    box_curr = box[(box['Season'].astype(str).str.contains(szn)) & (pd.to_numeric(box['Week'], errors='coerce') == wk)].copy()
    starters = box_curr[~box_curr['Slot'].astype(str).str.upper().isin(['BE', 'IR', 'BENCH', 'RES'])].copy()
    starters['Pts_Num'] = pd.to_numeric(starters['Actual_Points'], errors='coerce').fillna(0.0)
    for _, g in curr[curr['L'] == 1].iterrows():
        tm = g['Team_Name']
        margin = float(g['Margin'])
        tm_starters = starters[starters['Team_Name'] == tm]
        neg_players = tm_starters[tm_starters['Pts_Num'] < 0]
        for _, p in neg_players.iterrows():
            p_pts = float(p['Pts_Num'])
            if margin < abs(p_pts):
                bad_beats.append(f"  💔 **Brutal Beat:** {tm} lost to {g['Opponent_Team_Name']} by {margin:.2f} pts, while starting {p['Player_Name']} ({p['Pos']}) who scored {p_pts:.1f}. Benching them would have won the week!")
    if bad_beats:
        recap_lines.append("🤬 **Bad Beats & Heartbreaks:**")
        recap_lines.extend(bad_beats)
    
    recap_text = "\n".join(recap_lines)
    print("\n" + recap_text + "\n")
    os.makedirs("recaps", exist_ok=True)
    filename = f"recaps/Week_{wk}_Recap.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(recap_text)
    print(f"(Saved to {filename})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", type=int, help="Specific week", default=None)
    args = parser.parse_args()
    generate_recap(wk=args.week)
