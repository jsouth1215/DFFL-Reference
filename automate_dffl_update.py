import argparse
import os
import win32com.client
import update_weekly
from espn_api.football import League

def automate_excel_update(target_week, season=2026):
    excel_path = os.path.abspath("FantasyOddsModel2026-v1_2.xlsb")
    print(f"Opening master Excel model for {season} Week {target_week}: {excel_path}")

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

        # 2. Fetch live box scores from ESPN API
        print(f"Fetching Week {target_week} scoring data from ESPN API...")
        league = League(league_id=update_weekly.LEAGUE_ID, year=season, espn_s2=update_weekly.ESPN_S2, swid=update_weekly.SWID)
        bs = league.box_scores(target_week)

        scores_map = {}
        for m in bs:
            if m.home_team and m.away_team:
                t1 = update_weekly.TEAM_DICT.get(m.home_team.team_id, m.home_team.team_name)
                t2 = update_weekly.TEAM_DICT.get(m.away_team.team_id, m.away_team.team_name)
                scores_map[t1] = round(float(m.home_score), 2)
                scores_map[t2] = round(float(m.away_score), 2)

        if not scores_map or sum(scores_map.values()) <= 0:
            raise RuntimeError(f"ESPN returned empty/zero scores for Week {target_week}.")

        # 3. Update MatchupHistory
        ws_mh = wb.Sheets("MatchupHistory")
        last_row = ws_mh.UsedRange.Rows.Count
        print(f"Scanning MatchupHistory sheet (Total rows: {last_row})...")

        updated_count = 0
        for row in range(2, last_row + 1):
            yr_raw = ws_mh.Cells(row, 1).Value
            wk_raw = ws_mh.Cells(row, 2).Value
            if yr_raw is None or wk_raw is None:
                continue
            try:
                yr_val = int(float(yr_raw))
                wk_val = int(float(wk_raw))
            except (ValueError, TypeError):
                continue

            if yr_val == int(season) and wk_val == int(target_week):
                t1 = str(ws_mh.Cells(row, 3).Value or "").strip()  # Col C
                t2 = str(ws_mh.Cells(row, 5).Value or "").strip()  # Col E

                if t1 in scores_map:
                    ws_mh.Cells(row, 4).Value = scores_map[t1]
                if t2 in scores_map:
                    ws_mh.Cells(row, 6).Value = scores_map[t2]

                # Drag down formulas for columns I through AP (cols 9 to 42) using R1C1 so relative refs shift cleanly
                for col in range(9, 43):
                    prev_f = ws_mh.Cells(row - 1, col).FormulaR1C1
                    if prev_f and str(prev_f).startswith("="):
                        ws_mh.Cells(row, col).FormulaR1C1 = prev_f

                print(f"  Week {target_week}: {t1} ({scores_map.get(t1, '?')}) vs. {t2} ({scores_map.get(t2, '?')})")
                updated_count += 1

        print(f"✔ Populated scores and formulas for {updated_count} matchups in MatchupHistory.")

        # 4. Force full recalculation so pyxlsb reads fresh cached formula values
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
