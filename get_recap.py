import os
import argparse
import pandas as pd
import app
import odds_engine

def generate_recap(szn="2026", wk=None):
    games = app.games
    box = app.box_df
    
    # Clean up games data
    comp_games = games[games['Game_Type'].isin([1, 2])].copy()
    comp_games['Season_Str'] = comp_games['Season'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    comp_games['Week_Num'] = pd.to_numeric(comp_games['Week'], errors='coerce')
    comp_games['Pts_Num'] = pd.to_numeric(comp_games['Actual_Points'], errors='coerce')
    
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
        
        # H2H (All-Time)
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
    # Deduplicate teams (curr has W and L rows)
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
        szn_g = comp_games[(comp_games['Season_Str'] == szn) & (comp_games['Game_Type'] == 1)]
        
        # Odds for Current Week
        recs_curr = szn_g[szn_g['Week_Num'] <= wk][['Week_Num', 'Team_Name', 'Opponent_Team_Name', 'Actual_Points', 'Opp_Points', 'W', 'L', 'T']].to_dict('records')
        odds_curr, _ = odds_engine.run_playoff_odds_simulation_cached(szn, wk, recs_curr, n_wl_scenarios=5000)
        
        # Odds for Previous Week
        recs_prev = szn_g[szn_g['Week_Num'] <= wk - 1][['Week_Num', 'Team_Name', 'Opponent_Team_Name', 'Actual_Points', 'Opp_Points', 'W', 'L', 'T']].to_dict('records')
        odds_prev, _ = odds_engine.run_playoff_odds_simulation_cached(szn, wk - 1, recs_prev, n_wl_scenarios=5000)
        
        merged = odds_curr.merge(odds_prev, on='Team', suffixes=('_c', '_p'))
        odds_updates = []
        
        for _, r in merged.iterrows():
            tm = r['Team']
            pct_c = str(r['Playoff %_c'])
            pct_p = str(r['Playoff %_p'])
            
            if ">99.9" in pct_c and ">99.9" not in pct_p:
                odds_updates.append(f"  🎉 **CLINCHED:** {tm} has officially locked up a playoff spot!")
            elif "<0.1" in pct_c and "<0.1" not in pct_p:
                odds_updates.append(f"  🪦 **ELIMINATED:** {tm} is mathematically out of the playoff hunt.")
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

    # 6. All-Time & Franchise Records
    top15_alltime = comp_games['Pts_Num'].nlargest(15).min()
    bot15_alltime = comp_games[comp_games['Pts_Num'] > 0]['Pts_Num'].nsmallest(15).max()
    
    records_flagged = False
    recap_lines.append("🏆 **Record Book Watch:**")
    
    for _, g in curr.iterrows():
        tm = g['Team_Name']
        pts = g['Pts_Num']
        
        if pts >= top15_alltime:
            recap_lines.append(f"  🔥 **Historic High:** {tm} dropped {pts:.1f} pts, entering the Top 15 highest scores in DFFL history.")
            records_flagged = True
        elif pts > 0 and pts <= bot15_alltime:
            recap_lines.append(f"  🧊 **Historic Low:** {tm} struggled with {pts:.1f} pts, entering the Bottom 15 scores in DFFL history.")
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
        recap_lines.append("  *No franchise or all-time records broken this week.*")
    recap_lines.append("")
    
    # 7. Brutal Beats
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
    
    # Output
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
