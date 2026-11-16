import numpy as np
import pandas as pd
import streamlit as st

def prob_to_moneyline(p, is_clinched=False, is_elim=False):
    if is_clinched:
        return "CLINCHED"
    if is_elim:
        return "ELIM"
    # Clamp empirical 0% or 100% when not mathematically locked
    if p >= 0.9995:
        return "-10000"
    if p <= 0.0005:
        return "+10000"
    if abs(p - 0.5) < 1e-6:
        return "+100"
    if p > 0.5:
        ml = -int(round((p / (1.0 - p)) * 100.0))
        return f"{ml}"
    else:
        ml = int(round(((1.0 - p) / p) * 100.0))
        return f"+{ml}"

def fmt_prob(p, is_clinched=False, is_elim=False):
    if is_clinched:
        return "100.0%*"
    if is_elim:
        return "0.0%*"
    if p >= 0.9995:
        return ">99.9%"
    if p <= 0.0005:
        return "<0.1%"
    return f"{p * 100.0:.1f}%"

def _infer_remaining_schedule(szn_data, played_wk, reg_total_wks, teams_list):
    """
    Pulls remaining regular-season games (Week > played_wk) from szn_data if present.
    If future unplayed weeks are not yet in szn_data (e.g. mid-season 2026),
    infers remaining pairings using standard ESPN 12-team cyclic schedule rotation
    (where Week 12+ repeats Weeks 1, 2, 3...).
    """
    rem_pairs = []
    future_df = szn_data[szn_data["Week_Num"] > played_wk].copy()
    weeks_found = set()

    if not future_df.empty:
        for wk, grp in future_df.groupby("Week_Num"):
            if wk > reg_total_wks:
                continue
            seen = set()
            for _, r in grp.iterrows():
                t1 = str(r["Team_Name"]).strip()
                t2 = str(r["Opponent_Team_Name"]).strip()
                if not t1 or not t2 or t1 == t2 or t2.upper() == "BYE":
                    continue
                pair = tuple(sorted([t1, t2]))
                if pair not in seen:
                    seen.add(pair)
                    rem_pairs.append((int(wk), pair[0], pair[1]))
            if seen:
                weeks_found.add(int(wk))

    # For any remaining regular season week not in future_df, infer from played rotation
    played_df = szn_data[szn_data["Week_Num"] <= played_wk].copy()
    played_by_wk = {}
    pair_counts = {}
    for wk, grp in played_df.groupby("Week_Num"):
        seen = set()
        for _, r in grp.iterrows():
            t1 = str(r["Team_Name"]).strip()
            t2 = str(r["Opponent_Team_Name"]).strip()
            if t1 and t2 and t1 != t2 and t2.upper() != "BYE":
                pair = tuple(sorted([t1, t2]))
                if pair not in seen:
                    seen.add(pair)
                    played_by_wk.setdefault(int(wk), []).append(pair)
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1

    n_teams = len(teams_list)
    cycle_len = max(1, n_teams - 1)  # 11 weeks for 12-team league

    for wk in range(played_wk + 1, reg_total_wks + 1):
        if wk in weeks_found:
            continue
        mirror_wk = ((wk - 1) % cycle_len) + 1
        if mirror_wk in played_by_wk:
            for p0, p1 in played_by_wk[mirror_wk]:
                rem_pairs.append((int(wk), p0, p1))
        else:
            # Greedy minimum-played matching fallback for unplayed cycle weeks
            avail = list(teams_list)
            while len(avail) >= 2:
                t1 = avail.pop(0)
                best_t2 = min(avail, key=lambda cand: pair_counts.get(tuple(sorted([t1, cand])), 0))
                avail.remove(best_t2)
                pair = tuple(sorted([t1, best_t2]))
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
                rem_pairs.append((int(wk), pair[0], pair[1]))

    return rem_pairs

@st.cache_data(ttl=3600, show_spinner=False)
def run_playoff_odds_simulation(
    szn_str,
    through_wk,
    szn_games_records,
    div_groups=None,
    n_wl_scenarios=498,
    n_score_passes=10,
    seed=42
):
    """
    Runs the 2-layer Monte Carlo Odds Model:
      - Layer 1: 498 independent 50/50 W-L schedule permutations across remaining games
      - Layer 2: 10 scoring passes per scenario drawing from:
          (a) Uniform(Season_Min, Season_Max)
          (b) Uniform(League_Mean - 2*League_SD, League_Mean + 2*League_SD)
          (c) Uniform(Team_Mean - 2*Team_SD, Team_Mean + 2*Team_SD)
    """
    df_all = pd.DataFrame(szn_games_records)
    if df_all.empty:
        return pd.DataFrame(), {}

    szn_clean = str(szn_str).replace(".0", "").strip()
    szn_int = int(szn_clean) if szn_clean.isdigit() else 2026
    # Standard ESPN regular season length: 14 weeks for 2021+, 13 weeks for 2012-2020
    max_wk_in_data = int(df_all["Week_Num"].max())
    reg_total_wks = max(max_wk_in_data, 14 if szn_int >= 2021 else 13)

    played = df_all[(df_all["Week_Num"] <= through_wk) & (df_all["Actual_Points"] > 0)].copy()
    if played.empty:
        return pd.DataFrame(), {}

    teams_list = sorted(played["Team_Name"].dropna().astype(str).str.strip().unique().tolist())
    n_teams = len(teams_list)
    team_to_idx = {t: i for i, t in enumerate(teams_list)}

    # Current W, L, T, PF through selected week
    cur_w = np.zeros(n_teams, dtype=np.float64)
    cur_l = np.zeros(n_teams, dtype=np.float64)
    cur_t = np.zeros(n_teams, dtype=np.float64)
    cur_pf = np.zeros(n_teams, dtype=np.float64)

    team_scores = {i: [] for i in range(n_teams)}
    all_scores = []

    for _, r in played.iterrows():
        tm = str(r["Team_Name"]).strip()
        if tm not in team_to_idx:
            continue
        idx = team_to_idx[tm]
        pts = float(r["Actual_Points"])
        cur_w[idx] += float(r.get("W", 0))
        cur_l[idx] += float(r.get("L", 0))
        cur_t[idx] += float(r.get("T", 0))
        cur_pf[idx] += pts
        team_scores[idx].append(pts)
        all_scores.append(pts)

    szn_min = float(np.min(all_scores)) if all_scores else 65.0
    szn_max = float(np.max(all_scores)) if all_scores else 165.0
    lg_mean = float(np.mean(all_scores)) if all_scores else 110.0
    lg_sd = float(np.std(all_scores, ddof=1)) if len(all_scores) > 1 else 20.0

    tm_mean = np.zeros(n_teams, dtype=np.float64)
    tm_sd = np.zeros(n_teams, dtype=np.float64)
    for i in range(n_teams):
        sc = team_scores[i]
        tm_mean[i] = float(np.mean(sc)) if sc else lg_mean
        tm_sd[i] = float(np.std(sc, ddof=1)) if len(sc) > 1 else lg_sd

    rem_pairs = _infer_remaining_schedule(df_all, through_wk, reg_total_wks, teams_list)
    n_rem_games = len(rem_pairs)
    rem_wks_cnt = max(0, reg_total_wks - through_wk)

    # Count remaining games per team
    rem_games_per_team = np.zeros(n_teams, dtype=int)
    for _, t1, t2 in rem_pairs:
        if t1 in team_to_idx and t2 in team_to_idx:
            rem_games_per_team[team_to_idx[t1]] += 1
            rem_games_per_team[team_to_idx[t2]] += 1

    playoff_spots = 6 if n_teams >= 10 else 4
    bye_spots = 2

    # Deterministic Mathematical Bounds Check (Best/Worst Possible Finish)
    # Using Graph/Opponent Bound: To check if Team i has Clinched Top K, assume Team i loses all remaining games
    # and scores szn_min each week, while all other teams score szn_max.
    max_poss_wins = cur_w + 0.5 * cur_t + rem_games_per_team
    min_poss_wins = cur_w + 0.5 * cur_t

    clinched_playoffs = np.zeros(n_teams, dtype=bool)
    elim_playoffs = np.zeros(n_teams, dtype=bool)
    clinched_bye = np.zeros(n_teams, dtype=bool)
    elim_bye = np.zeros(n_teams, dtype=bool)
    clinched_1st = np.zeros(n_teams, dtype=bool)
    elim_1st = np.zeros(n_teams, dtype=bool)
    clinched_last = np.zeros(n_teams, dtype=bool)
    elim_last = np.zeros(n_teams, dtype=bool)

    if n_rem_games == 0:
        # Season regular season is complete -> exact ranks
        final_order = sorted(range(n_teams), key=lambda i: (cur_w[i] + 0.5 * cur_t[i], cur_pf[i]), reverse=True)
        rank_of = {tm_i: rk + 1 for rk, tm_i in enumerate(final_order)}
        for i in range(n_teams):
            rk = rank_of[i]
            clinched_playoffs[i] = (rk <= playoff_spots)
            elim_playoffs[i] = (rk > playoff_spots)
            clinched_bye[i] = (rk <= bye_spots)
            elim_bye[i] = (rk > bye_spots)
            clinched_1st[i] = (rk == 1)
            elim_1st[i] = (rk > 1)
            clinched_last[i] = (rk == n_teams)
            elim_last[i] = (rk < n_teams)
    else:
        for i in range(n_teams):
            # Can team i be overtaken by at least `playoff_spots` teams even if i loses out?
            # Count how many other teams CANNOT be caught by i even if i wins out & scores szn_max
            i_best_w = max_poss_wins[i]
            i_best_pf = cur_pf[i] + rem_games_per_team[i] * szn_max
            i_worst_w = min_poss_wins[i]
            i_worst_pf = cur_pf[i] + rem_games_per_team[i] * szn_min

            strictly_above_i_best = sum(
                1 for j in range(n_teams) if j != i and (
                    min_poss_wins[j] > i_best_w or (min_poss_wins[j] == i_best_w and (cur_pf[j] + rem_games_per_team[j] * szn_min) > i_best_pf)
                )
            )
            can_pass_i_worst = sum(
                1 for j in range(n_teams) if j != i and (
                    max_poss_wins[j] > i_worst_w or (max_poss_wins[j] == i_worst_w and (cur_pf[j] + rem_games_per_team[j] * szn_max) >= i_worst_pf)
                )
            )
            strictly_below_i_worst = sum(
                1 for j in range(n_teams) if j != i and (
                    max_poss_wins[j] < i_worst_w or (max_poss_wins[j] == i_worst_w and (cur_pf[j] + rem_games_per_team[j] * szn_max) < i_worst_pf)
                )
            )
            can_fall_below_i_best = sum(
                1 for j in range(n_teams) if j != i and (
                    min_poss_wins[j] < i_best_w or (min_poss_wins[j] == i_best_w and (cur_pf[j] + rem_games_per_team[j] * szn_min) <= i_best_pf)
                )
            )

            if can_pass_i_worst < playoff_spots:
                clinched_playoffs[i] = True
            if strictly_above_i_best >= playoff_spots:
                elim_playoffs[i] = True

            if can_pass_i_worst < bye_spots:
                clinched_bye[i] = True
            if strictly_above_i_best >= bye_spots:
                elim_bye[i] = True

            if can_pass_i_worst == 0:
                clinched_1st[i] = True
            if strictly_above_i_best >= 1:
                elim_1st[i] = True

            if can_fall_below_i_best == 0:
                clinched_last[i] = True
            if strictly_below_i_worst >= 1:
                elim_last[i] = True

    # Run Monte Carlo (498 W/L scenarios x 10 independent 3-regime scoring passes = 4,980 runs)
    rng = np.random.default_rng(seed + through_wk * 100 + szn_int)
    tot_runs = n_wl_scenarios * n_score_passes if n_rem_games > 0 else 1

    po_counts = np.zeros(n_teams, dtype=np.int64)
    bye_counts = np.zeros(n_teams, dtype=np.int64)
    first_counts = np.zeros(n_teams, dtype=np.int64)
    last_counts = np.zeros(n_teams, dtype=np.int64)
    sim_w_sum = np.zeros(n_teams, dtype=np.float64)
    sim_pf_sum = np.zeros(n_teams, dtype=np.float64)
    sim_rank_sum = np.zeros(n_teams, dtype=np.float64)

    # Pre-index remaining pairs
    indexed_pairs = [(team_to_idx[t1], team_to_idx[t2]) for _, t1, t2 in rem_pairs if t1 in team_to_idx and t2 in team_to_idx]

    # Pre-compute scoring bounds per team for the 3 regimes:
    # Regime 1: Uniform(szn_min, szn_max)
    # Regime 2: Uniform(lg_mean - 2*lg_sd, lg_mean + 2*lg_sd)
    # Regime 3: Uniform(tm_mean[i] - 2*tm_sd[i], tm_mean[i] + 2*tm_sd[i])
    lg_lo = max(30.0, lg_mean - 2.0 * lg_sd)
    lg_hi = lg_mean + 2.0 * lg_sd
    tm_lo = np.maximum(30.0, tm_mean - 2.0 * tm_sd)
    tm_hi = tm_mean + 2.0 * tm_sd

    div_idx_groups = []
    if div_groups:
        for d_name, d_members in div_groups:
            idxs = [team_to_idx[m] for m in d_members if m in team_to_idx]
            if idxs:
                div_idx_groups.append(idxs)

    valid_runs = 0
    for sc_i in range(n_wl_scenarios if n_rem_games > 0 else 1):
        w_scen = cur_w.copy()
        l_scen = cur_l.copy()
        if n_rem_games > 0:
            flips = rng.integers(0, 2, size=len(indexed_pairs))
            for g_idx, (i1, i2) in enumerate(indexed_pairs):
                if flips[g_idx] == 1:
                    w_scen[i1] += 1.0
                    l_scen[i2] += 1.0
                else:
                    w_scen[i2] += 1.0
                    l_scen[i1] += 1.0

        passes = n_score_passes if n_rem_games > 0 else 1
        for p_i in range(passes):
            pf_scen = cur_pf.copy()
            if n_rem_games > 0:
                # For each team's remaining games, draw independent scores across the 3 regimes
                for tm_i in range(n_teams):
                    g_rem = rem_games_per_team[tm_i]
                    if g_rem <= 0:
                        continue
                    regime_choices = rng.integers(0, 3, size=g_rem)
                    for r_c in regime_choices:
                        if r_c == 0:
                            pf_scen[tm_i] += rng.uniform(szn_min, szn_max)
                        elif r_c == 1:
                            pf_scen[tm_i] += rng.uniform(lg_lo, lg_hi)
                        else:
                            pf_scen[tm_i] += rng.uniform(tm_lo[tm_i], tm_hi[tm_i])

            # Rank teams by (Wins + 0.5*Ties, Final PF)
            eff_w = w_scen + 0.5 * cur_t
            order = sorted(range(n_teams), key=lambda idx: (eff_w[idx], pf_scen[idx]), reverse=True)

            # Division check: if divisions apply, check if at least 1 team from each division is in Top 6 (or promote division leader)
            if div_idx_groups:
                top_set = set(order[:playoff_spots])
                if not all(any(d_m in top_set for d_m in d_grp) for d_grp in div_idx_groups):
                    # Ensure division winners are included
                    div_winners = [max(d_grp, key=lambda idx: (eff_w[idx], pf_scen[idx])) for d_grp in div_idx_groups]
                    rem_pool = [idx for idx in order if idx not in div_winners]
                    order = sorted(div_winners, key=lambda idx: (eff_w[idx], pf_scen[idx]), reverse=True) + rem_pool

            valid_runs += 1
            for rk_pos, tm_i in enumerate(order):
                rk = rk_pos + 1
                sim_rank_sum[tm_i] += rk
                sim_w_sum[tm_i] += w_scen[tm_i]
                sim_pf_sum[tm_i] += pf_scen[tm_i]
                if rk <= playoff_spots:
                    po_counts[tm_i] += 1
                if rk <= bye_spots:
                    bye_counts[tm_i] += 1
                if rk == 1:
                    first_counts[tm_i] += 1
                if rk == n_teams:
                    last_counts[tm_i] += 1

    denom = float(max(1, valid_runs))
    rows = []
    for i, tm in enumerate(teams_list):
        p_po = po_counts[i] / denom
        p_bye = bye_counts[i] / denom
        p_1st = first_counts[i] / denom
        p_last = last_counts[i] / denom

        avg_w = sim_w_sum[i] / denom
        avg_l = (cur_w[i] + cur_l[i] + rem_games_per_team[i]) - avg_w
        avg_pf = sim_pf_sum[i] / denom
        avg_rk = sim_rank_sum[i] / denom

        cur_rec = f"{int(cur_w[i])}-{int(cur_l[i])}" + (f"-{int(cur_t[i])}" if cur_t[i] > 0 else "")
        proj_rec = f"{avg_w:.1f}-{avg_l:.1f}"

        rows.append({
            "Team": tm,
            "Current Record": cur_rec,
            "Current PF": f"{cur_pf[i]:.1f}",
            "Proj Record": proj_rec,
            "Proj PF": f"{avg_pf:.1f}",
            "Avg Seed": f"{avg_rk:.1f}",
            "Playoff %": fmt_prob(p_po, clinched_playoffs[i], elim_playoffs[i]),
            "Playoff ML": prob_to_moneyline(p_po, clinched_playoffs[i], elim_playoffs[i]),
            "First-Round Bye %": fmt_prob(p_bye, clinched_bye[i], elim_bye[i]),
            "Bye ML": prob_to_moneyline(p_bye, clinched_bye[i], elim_bye[i]),
            "1st Seed %": fmt_prob(p_1st, clinched_1st[i], elim_1st[i]),
            "1st Seed ML": prob_to_moneyline(p_1st, clinched_1st[i], elim_1st[i]),
            "Last Place %": fmt_prob(p_last, clinched_last[i], elim_last[i]),
            "Last Place ML": prob_to_moneyline(p_last, clinched_last[i], elim_last[i]),
            "_sort_po": p_po,
            "_sort_bye": p_bye,
            "_sort_w": cur_w[i],
            "_sort_pf": cur_pf[i],
        })

    out_df = pd.DataFrame(rows).sort_values(
        ["_sort_po", "_sort_bye", "_sort_w", "_sort_pf"],
        ascending=[False, False, False, False]
    ).reset_index(drop=True)
    out_df["Rank"] = out_df.index + 1

    meta = {
        "n_wl_scenarios": n_wl_scenarios,
        "n_score_passes": n_score_passes,
        "total_runs": valid_runs,
        "rem_games": n_rem_games,
        "rem_weeks": rem_wks_cnt,
        "szn_min": szn_min,
        "szn_max": szn_max,
        "lg_mean": lg_mean,
        "lg_sd": lg_sd,
        "reg_total_wks": reg_total_wks
    }
    return out_df, meta
