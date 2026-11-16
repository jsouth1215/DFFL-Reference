import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import zoneinfo
import pandas as pd
import requests
from espn_api.football import League

LEAGUE_ID = int(os.environ.get("DFFL_LEAGUE_ID", 1526656))
SWID = os.environ.get("DFFL_SWID", "{4D7861F6-0AE9-4ABC-8FD8-BB6F4FAC5C76}")
ESPN_S2 = os.environ.get(
    "DFFL_ESPN_S2",
    "AEA6y9DW%2FgDc3GZpma58YSBv6gsp99sEno3IWucriDiTLT4pn7MaaCbABcEuskUKeYctXSkVv1kd1DwgcpiGnxU09m8xdSNHFiiNyyNPMADoD1CzRAL45n3qeyWqSyztV%2BuHYZ%2BqJZMSNFDH5K7UmTTSX5CIpaB8lNHNTxob4arW9NnuDlJVqDOwJsClw%2F%2FK6uN5DzU4rWz09MwHcuvPw4Nz3r765gppahhHzX7vAoOxrxyv8z56Eo5CSH7EQ1plYk%2F9C74JOc9j4ldrNE5vf%2B6gErdO4obMMOC5%2FEnzJFXjxw%3D%3D"
)
SEASON = int(os.environ.get("DFFL_SEASON", 2026))
STATS_FILE = "espn_fantasy_complete_stats_2017_2026.xlsx"
TX_FILE = "espn_transactions_2019_2026.xlsx"

TEAM_DICT = {
    1: "Jack", 2: "Eli", 3: "Brett", 4: "David", 5: "Cav", 6: "Max",
    7: "Austin", 8: "Matt", 9: "Sean", 10: "Keith", 11: "Noah", 12: "Lukas", 13: "Cam"
}

MATCHUP_DICT = {
    (1, 2): 1, (1, 3): 2, (1, 4): 3, (1, 5): 4, (1, 6): 5, (1, 7): 6, (1, 8): 7, (1, 9): 8, (1, 10): 9, (1, 11): 10, (1, 12): 11,
    (2, 3): 12, (2, 4): 13, (2, 5): 14, (2, 6): 15, (2, 7): 16, (2, 8): 17, (2, 9): 18, (2, 10): 19, (2, 11): 20, (2, 12): 21,
    (3, 4): 22, (3, 5): 23, (3, 6): 24, (3, 7): 25, (3, 8): 26, (3, 9): 27, (3, 10): 28, (3, 11): 29, (3, 12): 30,
    (4, 5): 31, (4, 6): 32, (4, 7): 33, (4, 8): 34, (4, 9): 35, (4, 10): 36, (4, 11): 37, (4, 12): 38,
    (5, 6): 39, (5, 7): 40, (5, 8): 41, (5, 9): 42, (5, 10): 43, (5, 11): 44, (5, 12): 45,
    (6, 7): 46, (6, 8): 47, (6, 9): 48, (6, 10): 49, (6, 11): 50, (6, 12): 51,
    (7, 8): 52, (7, 9): 53, (7, 10): 54, (7, 11): 55, (7, 12): 56,
    (8, 9): 57, (8, 10): 58, (8, 11): 59, (8, 12): 60,
    (9, 10): 61, (9, 11): 62, (9, 12): 63,
    (10, 11): 64, (10, 12): 65,
    (11, 12): 66,
    (1, 13): 67, (2, 13): 68, (4, 13): 69, (5, 13): 70, (6, 13): 71, (7, 13): 72, (8, 13): 73, (9, 13): 74, (10, 13): 75
}

DST_MAPPING = {
    "Cardinals D/ST": 1, "Falcons D/ST": 2, "Ravens D/ST": 3, "Bills D/ST": 4,
    "Panthers D/ST": 5, "Bears D/ST": 6, "Bengals D/ST": 7, "Browns D/ST": 8,
    "Cowboys D/ST": 9, "Broncos D/ST": 10, "Lions D/ST": 11, "Packers D/ST": 12,
    "Texans D/ST": 13, "Colts D/ST": 14, "Jaguars D/ST": 15, "Chiefs D/ST": 16,
    "Raiders D/ST": 17, "Chargers D/ST": 18, "Rams D/ST": 19, "Dolphins D/ST": 20,
    "Vikings D/ST": 21, "Patriots D/ST": 22, "Saints D/ST": 23, "Giants D/ST": 24,
    "Jets D/ST": 25, "Eagles D/ST": 26, "Steelers D/ST": 27, "49ers D/ST": 28,
    "Seahawks D/ST": 29, "Buccaneers D/ST": 30, "Titans D/ST": 31,
    "Commanders D/ST": 32, "Washington D/ST": 32, "Redskins D/ST": 32, "Football Team D/ST": 32
}

POS_MAP = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "D/ST"}

def normalize_abbrev(abbr):
    if not abbr:
        return "FA"
    abbr = str(abbr).upper()
    mapping = {"WSH": "WAS", "LAR": "LA", "JAX": "JAC", "OAK": "LV", "SD": "LAC"}
    return mapping.get(abbr, abbr)

def is_nfl_week_complete(session, season, week):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={season}&seasontype=2&week={week}"
    try:
        r = session.get(url, timeout=8)
        if r.status_code == 200:
            events = r.json().get("events", [])
            if not events:
                return False
            all_done = all(
                ev.get("status", {}).get("type", {}).get("completed", False)
                for ev in events
            )
            return all_done
    except Exception:
        pass
    return False

def fetch_week_boxscores(league, session, eastern_tz, target_week, player_directory):
    try:
        box_scores = league.box_scores(target_week)
    except Exception as e:
        print(f"  [!] Could not fetch box_scores for Week {target_week}: {e}")
        return []

    if not box_scores:
        return []

    team_schedule = {}
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={SEASON}&seasontype=2&week={target_week}"
    try:
        r = session.get(url, timeout=8)
        if r.status_code == 200:
            for event in r.json().get("events", []):
                date_str = event.get("date")
                if not date_str:
                    continue
                try:
                    dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    g_date = dt.astimezone(eastern_tz).strftime("%Y-%m-%d")
                except Exception:
                    g_date = "N/A"
                for comp in event.get("competitions", []):
                    for competitor in comp.get("competitors", []):
                        abbrev = competitor.get("team", {}).get("abbreviation")
                        if abbrev:
                            team_schedule[normalize_abbrev(abbrev)] = g_date
    except Exception:
        pass

    rows = []
    for matchup in box_scores:
        m_type = getattr(matchup, "matchup_type", "NONE").upper()
        for team, opponent, lineup in [
            (matchup.home_team, matchup.away_team, matchup.home_lineup),
            (matchup.away_team, matchup.home_team, matchup.away_lineup)
        ]:
            if not team:
                continue
            if not opponent:
                game_type_code = 4
            elif "CONSOLATION" in m_type:
                game_type_code = 3
            elif "WINNER" in m_type or "PLAYOFF" in m_type:
                game_type_code = 2
            else:
                game_type_code = 1

            matchup_id = "N/A"
            opp_team_name = "None"
            if opponent:
                pair = tuple(sorted([team.team_id, opponent.team_id]))
                matchup_id = MATCHUP_DICT.get(pair, "N/A")
                opp_team_name = TEAM_DICT.get(opponent.team_id, opponent.team_name)

            real_team_name = TEAM_DICT.get(team.team_id, team.team_name)

            for player in lineup:
                pid = getattr(player, "playerId", None)
                pname = getattr(player, "name", "Unknown")
                pos = getattr(player, "position", "Unknown")
                pro_team = getattr(player, "proTeam", "FA")
                is_dst = ("D/ST" in str(pname) or pos == "D/ST")

                if not is_dst and (not pid or pid <= 0):
                    continue
                if is_dst:
                    pid = DST_MAPPING.get(pname, 99)

                if pid not in player_directory:
                    player_directory[pid] = {
                        "Player_ID": pid,
                        "Player_Name": pname,
                        "Position": pos,
                        "Date_of_Birth": "N/A",
                        "needs_lookup": True
                    }

                pass_yds = pass_td = rush_yds = rush_td = 0
                receptions = rec_yds = rec_td = other_td = 0
                interceptions = fumbles_lost = 0

                if not is_dst:
                    raw_stats = {}
                    if hasattr(player, "stats") and isinstance(player.stats, dict):
                        w_stats = player.stats.get(target_week, {})
                        raw_stats = w_stats.get("breakdown") or w_stats.get("raw") or {}

                    def s(keys):
                        for k in (keys if isinstance(keys, list) else [keys]):
                            if k in raw_stats:
                                return raw_stats[k]
                        return 0

                    pass_yds = s(["passingYards", 3, "3"])
                    pass_td = s(["passingTouchdowns", 4, "4"])
                    rush_yds = s(["rushingYards", 24, "24"])
                    rush_td = s(["rushingTouchdowns", 25, "25"])
                    receptions = s(["receivingReceptions", 53, "53", 41, "41"])
                    rec_yds = s(["receivingYards", 42, "42"])
                    rec_td = s(["receivingTouchdowns", 43, "43"])
                    interceptions = s(["passingInterceptions", 20, "20"])
                    fumbles_lost = s(["fumblesLost", 72, "72", 68, "68", 69, "69", 70, "70", 71, "71"])
                    other_td = (
                        s(["kickReturnTouchdowns", 72, "72"]) +
                        s(["puntReturnTouchdowns", 80, "80"]) +
                        s(["fumbleReturnTouchdowns", 115, "115"]) +
                        s(["defensiveTouchdowns", 105, "105"])
                    )

                game_date = team_schedule.get(normalize_abbrev(pro_team), "N/A")
                rows.append({
                    "Season": SEASON, "Week": int(target_week), "Game_Type": game_type_code,
                    "Game_Date": game_date, "Matchup_ID": matchup_id,
                    "Team_ID": team.team_id, "Team_Name": real_team_name,
                    "Opponent_Team_ID": opponent.team_id if opponent else None,
                    "Opponent_Team_Name": opp_team_name,
                    "Player_ID": pid, "Player_Name": pname, "Position": pos,
                    "Slot": getattr(player, "slot_position", "Unknown"),
                    "NFL_Team": pro_team, "NFL_Opponent": getattr(player, "pro_opponent", "None"),
                    "Pass_Yards": int(pass_yds) if pass_yds else 0,
                    "Pass_TD": int(pass_td) if pass_td else 0,
                    "Rush_Yards": int(rush_yds) if rush_yds else 0,
                    "Rush_TD": int(rush_td) if rush_td else 0,
                    "Receptions": int(receptions) if receptions else 0,
                    "Receiving_Yards": int(rec_yds) if rec_yds else 0,
                    "Receiving_TD": int(rec_td) if rec_td else 0,
                    "Other_TD": int(other_td) if other_td else 0,
                    "Interceptions": int(interceptions) if interceptions else 0,
                    "Fumbles_Lost": int(fumbles_lost) if fumbles_lost else 0,
                    "Actual_Points": round(float(getattr(player, "points", 0.0)), 2)
                })

    # Verify the week actually has non-zero points before committing it
    total_pts = sum(r["Actual_Points"] for r in rows)
    if total_pts <= 0:
        return []
    return rows

def update_transactions_2026(session, eastern_tz, player_directory):
    if not os.path.exists(TX_FILE):
        print(f"Transactions file {TX_FILE} not found; skipping transaction sync.")
        return False

    df_tx = pd.read_excel(TX_FILE, engine="openpyxl")
    cookies = {"espn_s2": ESPN_S2, "SWID": SWID}
    url = f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}/segments/0/leagues/{LEAGUE_ID}?view=mTransactions2"
    try:
        r = session.get(url, cookies=cookies, timeout=12)
        if r.status_code != 200:
            print(f"  [!] Could not fetch 2026 transactions (HTTP {r.status_code})")
            return False
        tx_raw = r.json().get("transactions", [])
    except Exception as e:
        print(f"  [!] Error fetching 2026 transactions: {e}")
        return False

    existing_ids = set(df_tx[df_tx["Season"] == SEASON]["Transaction_ID"].astype(str).unique())
    new_tx_rows = []

    for t in tx_raw:
        tx_id = str(t.get("id", "")).strip()
        if not tx_id or tx_id in existing_ids:
            continue
        status = str(t.get("status", "UNKNOWN")).upper()
        if status != "EXECUTED":
            continue
        tx_type = str(t.get("type", "UNKNOWN")).upper()
        if tx_type in ("LINEUP", "ROSTER", "FUTURE_ROSTER"):
            continue

        t_date = t.get("processDate") or t.get("proposedDate") or t.get("date") or 0
        if t_date > 0:
            dt_est = datetime.datetime.fromtimestamp(t_date / 1000.0, tz=datetime.timezone.utc).astimezone(eastern_tz)
            date_str = dt_est.strftime("%Y-%m-%d %H:%M")
        else:
            date_str = "N/A"

        wk = int(t.get("scoringPeriodId", 1))
        init_tid = t.get("teamId")
        init_team = TEAM_DICT.get(init_tid, "Free Agency / Waivers")
        bid_amt = int(t.get("bidAmount", 0) or 0)

        for item in t.get("items", []):
            act = str(item.get("type", "")).upper()
            if act in ("LINEUP", ""):
                continue
            pid = item.get("playerId")
            from_tid = item.get("fromTeamId", 0)
            to_tid = item.get("toTeamId", 0)
            from_tm = TEAM_DICT.get(from_tid, "Free Agency / Waivers") if from_tid and from_tid > 0 else "Free Agency / Waivers"
            to_tm = TEAM_DICT.get(to_tid, "Free Agency / Waivers") if to_tid and to_tid > 0 else "Free Agency / Waivers"

            p_info = player_directory.get(pid, {})
            p_name = p_info.get("Player_Name", f"Player {pid}")
            p_pos = p_info.get("Position", "Unknown")

            new_tx_rows.append({
                "Season": SEASON,
                "Week": wk,
                "Date": date_str,
                "Transaction_ID": tx_id,
                "Type": tx_type,
                "Status": status,
                "Initiating_Team": init_team,
                "Action": act,
                "Player_ID": pid,
                "Player": p_name,
                "Position": p_pos,
                "From_Team": from_tm,
                "To_Team": to_tm,
                "Bid_Amount": bid_amt if act == "ADD" else 0
            })

    if not new_tx_rows:
        print("No new executed 2026 transactions to append.")
        return False

    df_updated_tx = pd.concat([df_tx, pd.DataFrame(new_tx_rows)], ignore_index=True)
    df_updated_tx.to_excel(TX_FILE, index=False, engine="openpyxl")
    print(f"Appended {len(new_tx_rows)} new transaction rows to {TX_FILE}!")
    return True

def main():
    parser = argparse.ArgumentParser(description="Automated DFFL Weekly Updater")
    parser.add_argument("--week", type=int, default=None, help="Force update a specific week (e.g. --week 10)")
    parser.add_argument("--recheck-prev", action="store_true", default=True, help="Also refresh the most recently completed week for stat corrections")
    parser.add_argument("--push", action="store_true", help="Automatically git commit and push updated Excel files to origin/main")
    args = parser.parse_args()

    if not os.path.exists(STATS_FILE):
        print(f"Error: {STATS_FILE} not found in {os.getcwd()}")
        sys.exit(1)

    print(f"Loading {STATS_FILE}...")
    xls = pd.ExcelFile(STATS_FILE, engine="openpyxl")
    df_main = pd.read_excel(xls, sheet_name="Box_Scores")
    df_players = pd.read_excel(xls, sheet_name="Player_IDs")
    df_nfl_codes = pd.read_excel(xls, sheet_name="NFL_Codes") if "NFL_Codes" in xls.sheet_names else None

    df_szn = df_main[df_main["Season"] == SEASON]
    max_existing_wk = int(df_szn["Week"].max()) if not df_szn.empty else 0

    league = League(league_id=LEAGUE_ID, year=SEASON, espn_s2=ESPN_S2, swid=SWID)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    eastern_tz = zoneinfo.ZoneInfo("America/New_York")

    # Determine which weeks to pull/refresh
    weeks_to_sync = []
    if args.week is not None:
        weeks_to_sync = [args.week]
    else:
        # Refresh the last existing week (for stat corrections) + any newly completed weeks
        if max_existing_wk >= 1 and args.recheck_prev:
            weeks_to_sync.append(max_existing_wk)
        cand_wk = max_existing_wk + 1
        while cand_wk <= 17:
            if cand_wk < league.current_week or (cand_wk == league.current_week and is_nfl_week_complete(session, SEASON, cand_wk)):
                weeks_to_sync.append(cand_wk)
                cand_wk += 1
            else:
                break

    player_directory = df_players.set_index("Player_ID").to_dict("index")
    for pid in player_directory:
        player_directory[pid]["Player_ID"] = pid

    box_changed = False
    for wk in sorted(set(weeks_to_sync)):
        print(f"Syncing Season {SEASON}, Week {wk}...")
        rows = fetch_week_boxscores(league, session, eastern_tz, wk, player_directory)
        if not rows:
            print(f"  Week {wk} has no completed scores yet; skipping.")
            continue

        # Fetch birthdates for any newly discovered players
        new_pids = [pid for pid, d in player_directory.items() if d.get("needs_lookup")]
        for pid in new_pids:
            if pid <= 99:
                player_directory[pid].pop("needs_lookup", None)
                continue
            try:
                u = f"https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/athletes/{pid}"
                r = session.get(u, timeout=3)
                if r.status_code == 200:
                    raw_dob = r.json().get("dateOfBirth", "")
                    player_directory[pid]["Date_of_Birth"] = raw_dob.split("T")[0] if raw_dob else "N/A"
            except Exception:
                pass
            player_directory[pid].pop("needs_lookup", None)

        for r in rows:
            r["Date_of_Birth"] = player_directory.get(r["Player_ID"], {}).get("Date_of_Birth", "N/A")

        # Idempotent replace: remove any existing rows for (SEASON, wk) and append fresh rows
        df_main = df_main[~((df_main["Season"] == SEASON) & (pd.to_numeric(df_main["Week"], errors="coerce") == wk))].copy()
        df_main = pd.concat([df_main, pd.DataFrame(rows)], ignore_index=True)
        box_changed = True
        print(f"  Synced {len(rows)} player box-score rows for Week {wk}.")

    if box_changed:
        df_main = df_main.sort_values(["Season", "Week", "Matchup_ID", "Team_ID"]).reset_index(drop=True)
        player_cols = ["Player_ID", "Player_Name", "Position", "Date_of_Birth"]
        df_final_players = pd.DataFrame(list(player_directory.values()))[player_cols]

        with pd.ExcelWriter(STATS_FILE, engine="openpyxl") as writer:
            df_main.to_excel(writer, sheet_name="Box_Scores", index=False)
            df_final_players.to_excel(writer, sheet_name="Player_IDs", index=False)
            if df_nfl_codes is not None:
                df_nfl_codes.to_excel(writer, sheet_name="NFL_Codes", index=False)
        print(f"Saved updated {STATS_FILE} (preserving all sheets).")

    tx_changed = update_transactions_2026(session, eastern_tz, player_directory)

    # Clear local pickle cache if any data changed
    if box_changed or tx_changed:
        cache_dir = os.path.join(os.getcwd(), "_fast_cache")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
            print("Cleared _fast_cache/ binary cache.")

        if args.push:
            print("Committing and pushing updates to GitHub...")
            subprocess.run(["git", "add", STATS_FILE, TX_FILE], check=False)
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if status.stdout.strip():
                wks_str = ", ".join(str(w) for w in sorted(set(weeks_to_sync)))
                subprocess.run(["git", "commit", "-m", f"Auto-update {SEASON} Week {wks_str} box scores & transactions"], check=True)
                subprocess.run(["git", "push", "origin", "main"], check=True)
                print("Pushed update to origin/main!")
            else:
                print("No file changes detected by git.")
    else:
        print("Everything is already up to date.")

if __name__ == "__main__":
    main()
