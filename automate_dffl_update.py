import argparse
import os
import win32com.client
import update_weekly
from espn_api.football import League

def _fetch_week_scores(league, week_num):
    bs = league.box_scores(week_num)
    scores_map = {}
    for m in bs:
        if m.home_team and m.away_team:
            t1 = update_weekly.TEAM_DICT.get(m.home_team.team_id, m.home_team.team_name)
            t2 = update_weekly.TEAM_DICT.get(m.away_team.team_id, m.away_team.team_name)
            scores_map[t1] = round(float(m.home_score), 2)
            scores_map[t2] = round(float(m.away_score), 2)
    return scores_map

def automate_excel_update(target_week, season=2026, recheck_prev=True):
    excel_path = os.path.abspath("FantasyOddsModel2026-v1_2.xlsb")
    print(f"Opening master Excel model for {season} Week {target_week}: {excel_path}")

    league = League(league_id=update_weekly.LEAGUE_ID, year=season, espn_s2=update_weekly.ESPN_S2, swid=update_weekly.SWID)
    scores_map = _fetch_week_scores(league, target_week)
    if not scores_map or sum(scores_map.values()) <= 0:
        raise RuntimeError(f"ESPN returned empty/zero scores for Week {target_week}.")

    prev_scores_map = _fetch_week_scores(league, target_week - 1) if (recheck_prev and target_week > 1) else {}

    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False

    try:
        wb = excel.Workbooks.Open(excel_path)

        # 1. Update Inputs!B20 to target_week played
        try:
            ws_inputs = wb.Sheets("Inputs")
            ws_inputs.Range("B20").Value = int(target_week)
            print(f"✔ Updated Inputs!B20 to {target_week} weeks played.")
        except Exception as e:
            print("Note on Inputs!B20 update:", e)

        # 2. Scan MatchupHistory (Col 1 = Matchup Week, Col 2 = Year, Col 3/4 = Home Team/Pts, Col 5/6 = Away Team/Pts)
        ws_mh = wb.Sheets("MatchupHistory")
        last_row = ws_mh.UsedRange.Rows.Count
        last_col = max(42, ws_mh.UsedRange.Columns.Count)
        print(f"Scanning MatchupHistory (rows={last_row}, cols={last_col})...")

        updated_count = 0
        prev_corr_count = 0
        for row in range(2, last_row + 1):
            wk_raw = ws_mh.Cells(row, 1).Value
            yr_raw = ws_mh.Cells(row, 2).Value
            if wk_raw is None or yr_raw is None:
                continue
            try:
                wk_val = int(float(wk_raw))
                yr_val = int(float(yr_raw))
            except (ValueError, TypeError):
                continue

            if yr_val != int(season):
                continue

            t1 = str(ws_mh.Cells(row, 3).Value or "").strip()
            t2 = str(ws_mh.Cells(row, 5).Value or "").strip()

            # Check prior week for ESPN stat corrections
            if prev_scores_map and wk_val == int(target_week) - 1:
                for tm_n, col_idx in [(t1, 4), (t2, 6)]:
                    if tm_n in prev_scores_map:
                        old_v = ws_mh.Cells(row, col_idx).Value
                        new_v = prev_scores_map[tm_n]
                        if old_v is None or abs(float(old_v) - new_v) > 1e-4:
                            ws_mh.Cells(row, col_idx).Value = new_v
                            print(f"  [Stat Correction] Week {wk_val} {tm_n}: {old_v} -> {new_v}")
                            prev_corr_count += 1

            # Populate target week scores & fill down formula columns I..last_col
            if wk_val == int(target_week):
                if t1 in scores_map:
                    ws_mh.Cells(row, 4).Value = scores_map[t1]
                if t2 in scores_map:
                    ws_mh.Cells(row, 6).Value = scores_map[t2]

                for col in range(9, last_col + 1):
                    if ws_mh.Cells(row - 1, col).HasFormula:
                        ws_mh.Range(ws_mh.Cells(row - 1, col), ws_mh.Cells(row, col)).FillDown()

                print(f"  Week {target_week}: {t1} ({scores_map.get(t1, '?')}) vs. {t2} ({scores_map.get(t2, '?')})")
                updated_count += 1

        if updated_count == 0:
            raise RuntimeError(f"Matched 0 rows for {season} Week {target_week} in MatchupHistory!")

        print(f"✔ Populated {updated_count} Week {target_week} matchups (and {prev_corr_count} Week {target_week - 1} stat corrections).")

        # 3. Force full recalculation so pyxlsb reads fresh cached formula values
        excel.CalculateFull()
        wb.Save()
        wb.Close()
        print("✔ Recalculated and saved master Excel model!")

    except Exception as e:
        print("❌ Error during Excel automation:", e)
        raise
    finally:
        excel.Quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update FantasyOddsModel .xlsb for a completed week")
    parser.add_argument("--week", type=int, required=True, help="Target week number (e.g. --week 11)")
    parser.add_argument("--season", type=int, default=2026, help="Target season year (default 2026)")
    args = parser.parse_args()
    automate_excel_update(args.week, args.season)
