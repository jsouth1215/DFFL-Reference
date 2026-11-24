import io
import json
import re
import unicodedata
import pandas as pd
import requests

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})

TEAM_NORM = {
    "WSH": "WAS", "LAR": "LA", "JAX": "JAC", "OAK": "LV", "SD": "LAC", "STL": "LA",
    "ARZ": "ARI", "BLT": "BAL", "CLV": "CLE", "HST": "HOU", "SL": "LA"
}

NAME_ALIASES = {
    "gabe davis": "gabriel davis",
    "josh palmer": "joshua palmer",
    "ken walker": "kenneth walker",
    "mitch trubisky": "mitchell trubisky",
    "robbie anderson": "robby anderson",
    "chosen anderson": "robby anderson",
    "hollywood brown": "marquise brown",
    "tank dell": "nathaniel dell",
    "chig okonkwo": "chigoziem okonkwo",
    "scotty miller": "scott miller",
    "jeffery wilson": "jeff wilson",
    "benny snell": "benjamin snell",
    "bam knight": "zonovan knight",
    "bucky irving": "mar keise irving",
    "rob kelley": "robert kelley",
    "will fuller": "william fuller",
}

def norm_team(t):
    if pd.isna(t): return ""
    s = str(t).strip().upper()
    if s in ("NONE", "NAN", "N/A", "BYE", "FA", "", "-"): return ""
    return TEAM_NORM.get(s, s)

def norm_name(n):
    s = unicodedata.normalize("NFKD", str(n or "")).encode("ascii", "ignore").decode("ascii").lower()
    # Strip periods and apostrophes without inserting spaces (D.K. -> dk, A.J. -> aj, D'Onta -> donta)
    s = re.sub(r"[.'’]", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return NAME_ALIASES.get(s, s)

def fetch_csv(url):
    try:
        r = SESSION.get(url, timeout=20)
        if r.status_code == 200 and len(r.content) > 100:
            return pd.read_csv(io.BytesIO(r.content), low_memory=False)
    except Exception:
        pass
    return pd.DataFrame()

def _lookup_with_fallback(table, by_sw_last, s, w, nn, nfl_tm):
    hit = table.get((s, w, nn))
    if hit is not None:
        return hit
    parts = nn.split()
    if len(parts) < 2:
        return None
    first, last = parts[0], parts[-1]
    cands = by_sw_last.get((s, w, last), [])
    if not cands:
        return None
    # Prefer same NFL team + first-name prefix / initial match
    for cand_nn, val in cands:
        c_first = cand_nn.split()[0]
        team_ok = (not nfl_tm) or (not val.get("team")) or (val.get("team") == nfl_tm)
        name_ok = c_first.startswith(first[:3]) or first.startswith(c_first[:3]) or (len(first) <= 2 and c_first.startswith(first[0]))
        if team_ok and name_ok:
            return val
    # Secondary: exact same team & unique last name if first initial matches
    for cand_nn, val in cands:
        c_first = cand_nn.split()[0]
        if nfl_tm and val.get("team") == nfl_tm and c_first[0] == first[0]:
            return val
    return None

def build_zero_starters_meta(verbose=True):
    # 1. Load eligible (Season, Week, Team) from MatchupHistory (Reg Season + Playoffs + Bye, excl Cam)
    mh_raw = pd.read_pickle("cloud_cache_MatchupHistory.pkl").iloc[:, :10].copy()
    hdr_idx = mh_raw.index[mh_raw.iloc[:, 0].astype(str).str.strip() == "Matchup Week"][0]
    mh_raw.columns = [str(c).strip() for c in mh_raw.iloc[hdr_idx]]
    mh = mh_raw.iloc[hdr_idx + 1:].reset_index(drop=True)
    for c in ["Matchup Week", "Year", "Home Total Points", "Away Total Points"]:
        mh[c] = pd.to_numeric(mh[c], errors="coerce")
    mh = mh.dropna(subset=["Matchup Week", "Year"]).copy()
    mh["GT_Str"] = mh["Game Type"].astype(str).str.strip().str.lower()

    eligible_keys = set()
    for _, r in mh.iterrows():
        gt = r["GT_Str"]
        if not (gt.startswith("regular") or gt.startswith("playoff") or "bye" in gt):
            continue
        s, w = int(r["Year"]), int(r["Matchup Week"])
        for col_t, col_p in [("Home Team", "Home Total Points"), ("Away Team", "Away Total Points")]:
            tm = str(r[col_t] or "").strip()
            if tm and tm.upper() not in ("NAN", "NONE", "CAM") and pd.notna(r[col_p]):
                eligible_keys.add((s, w, tm))

    # 2. Load ALL 2017-2026 zero-point starters from cloud_cache_Box_Scores.pkl
    bs = pd.read_pickle("cloud_cache_Box_Scores.pkl")
    bs["Pts"] = pd.to_numeric(bs["Actual_Points"], errors="coerce")
    bs["Season_Int"] = pd.to_numeric(bs["Season"], errors="coerce").fillna(0).astype(int)
    bs["Week_Int"] = pd.to_numeric(bs["Week"], errors="coerce").fillna(0).astype(int)
    bs["Team_Clean"] = bs["Team_Name"].astype(str).str.strip()
    bs["Player_Clean"] = bs["Player_Name"].astype(str).str.strip()
    is_st = ~bs["Slot"].astype(str).str.strip().str.upper().isin(["BE", "IR", "BENCH", "RES"])

    # Classify ALL 0.0 starters in box_df (so Regular Season, Playoffs, Bye, or any filter is covered)
    zeros_all = bs[is_st & (bs["Pts"] == 0.0)].copy()
    seasons = sorted([s for s in zeros_all["Season_Int"].unique().tolist() if s >= 2017])
    if verbose:
        print(f"Classifying {len(zeros_all)} total starter 0.0 rows across seasons {seasons}...")

    # 3. Fetch NFL schedules (nflverse games.csv + ESPN scoreboard fallback)
    games_csv = fetch_csv("https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv")
    played_teams_by_sw = {}
    if not games_csv.empty:
        reg_g = games_csv[games_csv["season"].isin(seasons) & (games_csv["game_type"] == "REG")]
        for _, r in reg_g.iterrows():
            key = (int(r["season"]), int(r["week"]))
            played_teams_by_sw.setdefault(key, set()).update([norm_team(r["home_team"]), norm_team(r["away_team"])])

    for (s, w) in sorted(set(zip(zeros_all["Season_Int"], zeros_all["Week_Int"]))):
        if (s, w) not in played_teams_by_sw or len(played_teams_by_sw[(s, w)]) < 10:
            try:
                u = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={s}&seasontype=2&week={w}"
                r = SESSION.get(u, timeout=10)
                if r.status_code == 200:
                    tms = set()
                    for ev in r.json().get("events", []):
                        for comp in ev.get("competitions", []):
                            for c in comp.get("competitors", []):
                                ab = norm_team(c.get("team", {}).get("abbreviation", ""))
                                if ab: tms.add(ab)
                    if tms:
                        played_teams_by_sw[(s, w)] = tms
            except Exception:
                pass

    # 4. Fetch nflverse snap counts, injuries, and weekly rosters per season (2017-2026)
    snap_lookup, snap_by_last = {}, {}
    inj_lookup, inj_by_last = {}, {}
    roster_lookup, roster_by_last = {}, {}
    has_snaps_szn = set()

    for s in seasons:
        df_sn = fetch_csv(f"https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{s}.csv")
        df_in = fetch_csv(f"https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{s}.csv")
        df_ro = fetch_csv(f"https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_{s}.csv")
        if verbose:
            print(f"  {s}: snaps={len(df_sn):5d} | injuries={len(df_in):5d} | rosters={len(df_ro):5d}")

        if not df_sn.empty:
            has_snaps_szn.add(s)
            for _, r in df_sn.iterrows():
                try:
                    w = int(r["week"])
                except Exception:
                    continue
                nn = norm_name(r.get("player", ""))
                if not nn: continue
                off_s = int(pd.to_numeric(r.get("offense_snaps", 0), errors="coerce") or 0)
                def_s = int(pd.to_numeric(r.get("defense_snaps", 0), errors="coerce") or 0)
                st_s = int(pd.to_numeric(r.get("st_snaps", 0), errors="coerce") or 0)
                tot = off_s + def_s + st_s
                val = {"snaps": tot, "off": off_s, "st": st_s, "team": norm_team(r.get("team", ""))}
                k = (s, w, nn)
                if k not in snap_lookup or tot > snap_lookup[k]["snaps"]:
                    snap_lookup[k] = val
                last = nn.split()[-1]
                snap_by_last.setdefault((s, w, last), []).append((nn, val))

        if not df_in.empty:
            for _, r in df_in.iterrows():
                try:
                    w = int(r["week"])
                except Exception:
                    continue
                nn = norm_name(r.get("full_name", ""))
                if not nn: continue
                st_txt = str(r.get("report_status", "") or "").strip()
                inj_txt = str(r.get("report_primary_injury", "") or "").strip()
                if st_txt.lower() in ("nan", "none"): st_txt = ""
                if inj_txt.lower() in ("nan", "none"): inj_txt = ""
                val = {"status": st_txt, "injury": inj_txt, "team": norm_team(r.get("team", ""))}
                inj_lookup[(s, w, nn)] = val
                last = nn.split()[-1]
                inj_by_last.setdefault((s, w, last), []).append((nn, val))

        if not df_ro.empty:
            for _, r in df_ro.iterrows():
                try:
                    w = int(r["week"])
                except Exception:
                    continue
                nn = norm_name(r.get("full_name", ""))
                if not nn: continue
                rst = str(r.get("status", "") or "").strip().upper()
                val = {"status": rst, "team": norm_team(r.get("team", ""))}
                roster_lookup[(s, w, nn)] = val
                last = nn.split()[-1]
                roster_by_last.setdefault((s, w, last), []).append((nn, val))

    # 5. Classify each zero-point starter
    stat_cols = [c for c in ["Pass_Yards", "Pass_TD", "Rush_Yards", "Rush_TD", "Receptions", "Receiving_Yards", "Receiving_TD", "Interceptions", "Fumbles_Lost"] if c in zeros_all.columns]
    nfl_c = "Pro_Team" if "Pro_Team" in zeros_all.columns else "NFL_Team"

    meta = {}
    elig_rows = []
    for _, r in zeros_all.iterrows():
        s = int(r["Season_Int"])
        w = int(r["Week_Int"])
        tm_f = r["Team_Clean"]
        pname = r["Player_Clean"]
        pos = str(r.get("Position", "")).strip().upper()
        nfl_tm = norm_team(r.get(nfl_c, "")) or norm_team(r.get("NFL_Team", ""))
        nfl_opp = norm_team(r.get("NFL_Opponent", ""))
        nn = norm_name(pname)

        is_dst = ("D/ST" in pos or "DEF" in pos or "D/ST" in pname)
        has_stats = any(abs(float(pd.to_numeric(r.get(c, 0), errors="coerce") or 0)) > 0 for c in stat_cols)

        wk_teams = played_teams_by_sw.get((s, w), set())
        sn = _lookup_with_fallback(snap_lookup, snap_by_last, s, w, nn, nfl_tm)
        inj = _lookup_with_fallback(inj_lookup, inj_by_last, s, w, nn, nfl_tm)
        ros = _lookup_with_fallback(roster_lookup, roster_by_last, s, w, nn, nfl_tm)

        eff_nfl_tm = (sn["team"] if sn and sn["team"] else (ros["team"] if ros and ros["team"] else (inj["team"] if inj and inj["team"] else nfl_tm)))
        on_bye = bool(eff_nfl_tm and wk_teams and eff_nfl_tm not in wk_teams)

        if is_dst:
            if on_bye:
                cat, detail = "Bye / No Game", f"Bye Week ({eff_nfl_tm})"
            else:
                opp_lbl = f" vs. {nfl_opp}" if nfl_opp else ""
                cat, detail = "Played (D/ST)", f"Played{opp_lbl}"
        elif has_stats:
            sn_str = f"{sn['snaps']} snaps, " if sn and sn["snaps"] > 0 else ""
            cat, detail = "Played (0.0)", f"Played ({sn_str}offsetting stats)"
        elif sn and sn["snaps"] > 0:
            sn_n = sn["snaps"]
            cat = "Played (0.0)"
            if pos != "K" and sn_n <= 15:
                detail = f"Played — {sn_n} snap{'s' if sn_n != 1 else ''} (early exit?)"
            else:
                detail = f"Played — {sn_n} snap{'s' if sn_n != 1 else ''}"
        elif on_bye:
            cat, detail = "Bye / No Game", f"Bye Week ({eff_nfl_tm})"
        elif not eff_nfl_tm or (ros and ros["status"] in ("CUT", "DEV", "RET", "EXE", "UFA", "TRD", "WAIVED")) or (ros is None and inj is None and s in has_snaps_szn):
            st_lbl = ros["status"] if ros else "FA / Off Roster"
            cat, detail = "Bye / No Game", f"No Game ({st_lbl})"
        elif inj and inj["status"].lower() in ("out", "doubtful", "ir", "injured reserve"):
            inj_note = f" - {inj['injury']}" if inj["injury"] else ""
            cat, detail = "Injured / Inactive (DNP)", f"{inj['status']}{inj_note}"
        elif ros and ros["status"] in ("INA", "RES", "PUP", "NFI", "IR", "SUS", "COV"):
            lbl_map = {"INA": "Inactive", "RES": "IR / Reserve", "PUP": "PUP", "NFI": "NFI", "IR": "IR", "SUS": "Suspended", "COV": "COVID/Reserve"}
            inj_note = f" ({inj['injury']})" if (inj and inj["injury"]) else ""
            cat, detail = "Injured / Inactive (DNP)", f"{lbl_map.get(ros['status'], ros['status'])}{inj_note}"
        elif s in has_snaps_szn:
            inj_note = f" ({inj['status']}: {inj['injury']})" if (inj and (inj["status"] or inj["injury"])) else ""
            cat, detail = "Injured / Inactive (DNP)", f"0 Snaps / DNP{inj_note}"
        else:
            cat, detail = "Unverified (0.0)", "Pending snap lookup"

        key = f"{s}|{w}|{tm_f}|{pname}"
        meta[key] = {"cat": cat, "detail": detail, "snaps": (sn["snaps"] if sn else 0)}
        if (s, w, tm_f) in eligible_keys:
            elig_rows.append({"Season": s, "Week": w, "Team": tm_f, "Player": pname, "Pos": pos, "NFL": eff_nfl_tm or nfl_tm, "Cat": cat, "Detail": detail})

    with open("zero_starters_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)

    if verbose:
        res_df = pd.DataFrame(elig_rows)
        print(f"\n=== ELIGIBLE (REG + PLAYOFFS + BYE, 2017-2026) TOTALS: {len(res_df)} rows ===")
        print(res_df["Cat"].value_counts().to_string())

        print("\n=== BY FANTASY TEAM (2017-2026) ===")
        piv = pd.crosstab(res_df["Team"], res_df["Cat"])
        piv["Total"] = piv.sum(axis=1)
        print(piv.sort_values("Total", ascending=False).to_string())

        print(f"\n=== ALL BYE / NO GAME ({len(res_df[res_df['Cat']=='Bye / No Game'])}) ===")
        print(res_df[res_df["Cat"] == "Bye / No Game"].sort_values(["Season", "Week"]).to_string(index=False))

        print(f"\n=== ALL INJURED / INACTIVE (DNP) ({len(res_df[res_df['Cat']=='Injured / Inactive (DNP)'])}) ===")
        print(res_df[res_df["Cat"] == "Injured / Inactive (DNP)"].sort_values(["Season", "Week"]).to_string(index=False))
    return meta

if __name__ == "__main__":
    build_zero_starters_meta(verbose=True)
