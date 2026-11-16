import numpy as np
import pandas as pd
import streamlit as st

def _round5(val):
    return int(round(val / 5.0) * 5)

def prob_to_moneyline(p, is_clinched=False, is_elim=False):
    if is_clinched:
        return "CLINCHED"
    if is_elim:
        return "ELIM"
    p_clamped = min(max(float(p), 1.0 / 251.0), 250.0 / 251.0)
    if abs(p_clamped - 0.5) < 1e-6:
        return "+100"
    if p_clamped > 0.5:
        raw_ml = (p_clamped / (1.0 - p_clamped)) * 100.0
        ml = max(100, min(25000, _round5(raw_ml)))
        return f"-{ml}"
    else:
        raw_ml = ((1.0 - p_clamped) / p_clamped) * 100.0
        ml = max(100, min(25000, _round5(raw_ml)))
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

EXACT_2026_SCHEDULE = [(1, 'Brett', 'Cav'), (1, 'Lukas', 'Noah'), (1, 'David', 'Keith'), (1, 'Jack', 'Max'), (1, 'Austin', 'Matt'), (1, 'Eli', 'Sean'), (2, 'Brett', 'Noah'), (2, 'Cav', 'Keith'), (2, 'Lukas', 'Max'), (2, 'David', 'Matt'), (2, 'Eli', 'Jack'), (2, 'Austin', 'Sean'), (3, 'Brett', 'Keith'), (3, 'Max', 'Noah'), (3, 'Cav', 'Matt'), (3, 'Eli', 'Lukas'), (3, 'David', 'Sean'), (3, 'Austin', 'Jack'), (4, 'Brett', 'Max'), (4, 'Keith', 'Matt'), (4, 'Eli', 'Noah'), (4, 'Cav', 'Sean'), (4, 'Austin', 'Lukas'), (4, 'David', 'Jack'), (5, 'Brett', 'Matt'), (5, 'Eli', 'Max'), (5, 'Keith', 'Sean'), (5, 'Austin', 'Noah'), (5, 'Cav', 'Jack'), (5, 'David', 'Lukas'), (6, 'Brett', 'Eli'), (6, 'Matt', 'Sean'), (6, 'Austin', 'Max'), (6, 'Jack', 'Keith'), (6, 'David', 'Noah'), (6, 'Cav', 'Lukas'), (7, 'Brett', 'Sean'), (7, 'Austin', 'Eli'), (7, 'Jack', 'Matt'), (7, 'David', 'Max'), (7, 'Keith', 'Lukas'), (7, 'Cav', 'Noah'), (8, 'Austin', 'Brett'), (8, 'Jack', 'Sean'), (8, 'David', 'Eli'), (8, 'Lukas', 'Matt'), (8, 'Cav', 'Max'), (8, 'Keith', 'Noah'), (9, 'Brett', 'Jack'), (9, 'Austin', 'David'), (9, 'Lukas', 'Sean'), (9, 'Cav', 'Eli'), (9, 'Matt', 'Noah'), (9, 'Keith', 'Max'), (10, 'Brett', 'David'), (10, 'Jack', 'Lukas'), (10, 'Austin', 'Cav'), (10, 'Noah', 'Sean'), (10, 'Eli', 'Keith'), (10, 'Matt', 'Max'), (11, 'Brett', 'Lukas'), (11, 'Cav', 'David'), (11, 'Jack', 'Noah'), (11, 'Austin', 'Keith'), (11, 'Max', 'Sean'), (11, 'Eli', 'Matt'), (12, 'Brett', 'Cav'), (12, 'Lukas', 'Noah'), (12, 'David', 'Keith'), (12, 'Jack', 'Max'), (12, 'Austin', 'Matt'), (12, 'Eli', 'Sean'), (13, 'Brett', 'Noah'), (13, 'Cav', 'Keith'), (13, 'Lukas', 'Max'), (13, 'David', 'Matt'), (13, 'Eli', 'Jack'), (13, 'Austin', 'Sean'), (14, 'Brett', 'Keith'), (14, 'Max', 'Noah'), (14, 'Cav', 'Matt'), (14, 'Eli', 'Lukas'), (14, 'David', 'Sean'), (14, 'Austin', 'Jack')]

def _infer_remaining_schedule(szn_data, played_wk, reg_total_wks, teams_list, szn_clean="2026"):
    if str(szn_clean) == "2026" and EXACT_2026_SCHEDULE:
        return [(wk, t1, t2) for (wk, t1, t2) in EXACT_2026_SCHEDULE if played_wk < wk <= reg_total_wks]
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
    cycle_len = max(1, n_teams - 1)

    for wk in range(played_wk + 1, reg_total_wks + 1):
        if wk in weeks_found:
            continue
        mirror_wk = ((wk - 1) % cycle_len) + 1
        if mirror_wk in played_by_wk:
            for p0, p1 in played_by_wk[mirror_wk]:
                rem_pairs.append((int(wk), p0, p1))
        else:
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
    n_wl_scenarios=5000,
    n_score_passes=10,
    seed=42
):
    df_all = pd.DataFrame(szn_games_records)
    if df_all.empty:
        return pd.DataFrame(), {}

    szn_clean = str(szn_str).replace(".0", "").strip()
    szn_int = int(szn_clean) if szn_clean.isdigit() else 2026
    max_wk_in_data = int(df_all["Week_Num"].max())
    reg_total_wks = max(max_wk_in_data, 14 if szn_int >= 2021 else 13)

    played = df_all[(df_all["Week_Num"] <= through_wk) & (df_all["Actual_Points"] > 0)].copy()
    if played.empty:
        return pd.DataFrame(), {}

    teams_list = sorted(played["Team_Name"].dropna().astype(str).str.strip().unique().tolist())
    n_teams = len(teams_list)
    team_to_idx = {t: i for i, t in enumerate(teams_list)}

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

    rem_pairs = _infer_remaining_schedule(df_all, through_wk, reg_total_wks, teams_list, szn_clean=szn_clean)
    indexed_pairs = [(team_to_idx[t1], team_to_idx[t2]) for _, t1, t2 in rem_pairs if t1 in team_to_idx and t2 in team_to_idx]
    n_rem_games = len(indexed_pairs)
    rem_wks_cnt = max(0, reg_total_wks - through_wk)

    rem_games_per_team = np.zeros(n_teams, dtype=int)
    for i1, i2 in indexed_pairs:
        rem_games_per_team[i1] += 1
        rem_games_per_team[i2] += 1

    playoff_spots = 6 if n_teams >= 10 else 4
    bye_spots = 2
    lpg_cutoff_rank = max(1, n_teams - 1)

    max_poss_wins = cur_w + 0.5 * cur_t + rem_games_per_team
    min_poss_wins = cur_w + 0.5 * cur_t

    clinched_playoffs = np.zeros(n_teams, dtype=bool)
    elim_playoffs = np.zeros(n_teams, dtype=bool)
    clinched_bye = np.zeros(n_teams, dtype=bool)
    elim_bye = np.zeros(n_teams, dtype=bool)
    clinched_lpg = np.zeros(n_teams, dtype=bool)
    elim_lpg = np.zeros(n_teams, dtype=bool)

    if n_rem_games == 0:
        final_order = sorted(range(n_teams), key=lambda i: (cur_w[i] + 0.5 * cur_t[i], cur_pf[i]), reverse=True)
        rank_of = {tm_i: rk + 1 for rk, tm_i in enumerate(final_order)}
        for i in range(n_teams):
            rk = rank_of[i]
            clinched_playoffs[i] = (rk <= playoff_spots)
            elim_playoffs[i] = (rk > playoff_spots)
            clinched_bye[i] = (rk <= bye_spots)
            elim_bye[i] = (rk > bye_spots)
            clinched_lpg[i] = (rk >= lpg_cutoff_rank)
            elim_lpg[i] = (rk < lpg_cutoff_rank)
    else:
        for i in range(n_teams):
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
            if can_fall_below_i_best <= 1:
                clinched_lpg[i] = True
            if strictly_below_i_worst >= 2:
                elim_lpg[i] = True

    rng = np.random.default_rng(seed + through_wk * 100 + szn_int)

    div_idx_groups = []
    if div_groups:
        for d_name, d_members in div_groups:
            idxs = [team_to_idx[m] for m in d_members if m in team_to_idx]
            if idxs:
                div_idx_groups.append(idxs)

    if n_rem_games == 0:
        tot_runs = 1
        eff_w_mat = (cur_w + 0.5 * cur_t)[None, :]
        pf_mat = cur_pf[None, :]
    else:
        tot_runs = n_wl_scenarios * n_score_passes
        # 1. Vectorized Layer 1: (n_wl_scenarios, n_rem_games) coin flips -> (n_wl_scenarios, n_teams) wins
        flips = rng.integers(0, 2, size=(n_wl_scenarios, n_rem_games))
        t1_arr = np.array([p[0] for p in indexed_pairs], dtype=int)
        t2_arr = np.array([p[1] for p in indexed_pairs], dtype=int)

        inc_t1 = np.zeros((n_rem_games, n_teams), dtype=np.float64)
        inc_t2 = np.zeros((n_rem_games, n_teams), dtype=np.float64)
        inc_t1[np.arange(n_rem_games), t1_arr] = 1.0
        inc_t2[np.arange(n_rem_games), t2_arr] = 1.0

        w_added = flips @ inc_t1 + (1 - flips) @ inc_t2
        w_scen = cur_w[None, :] + w_added
        eff_w_mat = np.repeat(w_scen + 0.5 * cur_t[None, :], n_score_passes, axis=0)

        # 2. Vectorized Layer 2: 3-Regime Scoring Draws across (tot_runs, n_teams, max_rem_g)
        max_rem_g = int(np.max(rem_games_per_team))
        lg_lo = max(30.0, lg_mean - 2.0 * lg_sd)
        lg_hi = lg_mean + 2.0 * lg_sd
        tm_lo = np.maximum(30.0, tm_mean - 2.0 * tm_sd)
        tm_hi = tm_mean + 2.0 * tm_sd

        regimes = rng.integers(0, 3, size=(tot_runs, n_teams, max_rem_g))
        u = rng.random(size=(tot_runs, n_teams, max_rem_g))

        s0 = szn_min + u * (szn_max - szn_min)
        s1 = lg_lo + u * (lg_hi - lg_lo)
        s2 = tm_lo[None, :, None] + u * (tm_hi - tm_lo)[None, :, None]

        draws = np.where(regimes == 0, s0, np.where(regimes == 1, s1, s2))
        valid_mask = np.arange(max_rem_g)[None, :] < rem_games_per_team[:, None]
        pf_added = np.sum(draws * valid_mask[None, :, :], axis=2)
        pf_mat = cur_pf[None, :] + pf_added

    # 3. Vectorized Ranking across all 4,980 runs simultaneously
    comp_score = eff_w_mat * 1e6 + pf_mat
    if div_idx_groups and n_rem_games > 0:
        # Boost division winner composite score if a division has no team in top 6
        order_init = np.argsort(-comp_score, axis=1)
        for d_grp in div_idx_groups:
            d_arr = np.array(d_grp, dtype=int)
            d_scores = comp_score[:, d_arr]
            best_in_div = d_arr[np.argmax(d_scores, axis=1)]
            # Check if best_in_div is outside top `playoff_spots`
            Sixth_score = comp_score[np.arange(tot_runs), order_init[:, playoff_spots - 1]]
            best_div_score = comp_score[np.arange(tot_runs), best_in_div]
            needs_promo = best_div_score < Sixth_score
            if np.any(needs_promo):
                comp_score[needs_promo, best_in_div[needs_promo]] = Sixth_score[needs_promo] + 1e-2

    order_mat = np.argsort(-comp_score, axis=1)
    ranks_mat = np.argsort(order_mat, axis=1) + 1  # (tot_runs, n_teams) 1-indexed ranks

    po_probs = np.mean(ranks_mat <= playoff_spots, axis=0)
    bye_probs = np.mean(ranks_mat <= bye_spots, axis=0)
    lpg_probs = np.mean(ranks_mat >= lpg_cutoff_rank, axis=0)
    avg_ranks = np.mean(ranks_mat, axis=0)

    rows = []
    for i, tm in enumerate(teams_list):
        p_po = float(po_probs[i])
        p_bye = float(bye_probs[i])
        p_lpg = float(lpg_probs[i])
        avg_rk = float(avg_ranks[i])
        cur_rec = f"{int(cur_w[i])}-{int(cur_l[i])}" + (f"-{int(cur_t[i])}" if cur_t[i] > 0 else "")

        rows.append({
            "Team": tm,
            "Current Record": cur_rec,
            "Current PF": f"{cur_pf[i]:.1f}",
            "Avg Seed": f"{avg_rk:.1f}",
            "Playoff %": fmt_prob(p_po, clinched_playoffs[i], elim_playoffs[i]),
            "Playoff ML": prob_to_moneyline(p_po, clinched_playoffs[i], elim_playoffs[i]),
            "First-Round Bye %": fmt_prob(p_bye, clinched_bye[i], elim_bye[i]),
            "Bye ML": prob_to_moneyline(p_bye, clinched_bye[i], elim_bye[i]),
            "Last Place Game %": fmt_prob(p_lpg, clinched_lpg[i], elim_lpg[i]),
            "Last Place Game ML": prob_to_moneyline(p_lpg, clinched_lpg[i], elim_lpg[i]),
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
        "total_runs": tot_runs,
        "rem_games": n_rem_games,
        "rem_weeks": rem_wks_cnt,
        "szn_min": szn_min,
        "szn_max": szn_max,
        "lg_mean": lg_mean,
        "lg_sd": lg_sd,
        "reg_total_wks": reg_total_wks
    }
    return out_df, meta


def run_playoff_odds_simulation_cached(*args, **kwargs):
    import os, pickle
    
    szn_clean = args[0] if len(args) > 0 else kwargs.get("szn_clean", "2026")
    through_wk = args[1] if len(args) > 1 else kwargs.get("through_wk", 1)
    
    cache_file = "historical_odds_cache.pkl"
    if szn_clean is not None and through_wk is not None:
        key = (str(szn_clean).replace('.0', '').strip(), int(through_wk))
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    cache = pickle.load(f)
                if key in cache:
                    return cache[key]
            except Exception:
                pass
                
    return run_playoff_odds_simulation(*args, **kwargs)
