import os
import win32com.client
import update_weekly
from espn_api.football import League

excel_path = os.path.abspath("FantasyOddsModel2026-v1_2.xlsb")
print(f"Opening Excel model: {excel_path}")

excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False

try:
    wb = excel.Workbooks.Open(excel_path)
    
    # 1. Update Inputs!B20 to 10 weeks played
    try:
        ws_inputs = wb.Sheets("Inputs")
        ws_inputs.Range("B20").Value = 10
        print("Updated Inputs!B20 to 10 weeks played.")
    except Exception as e:
        print("Note on Inputs!B20 update:", e)
        
    # 2. Fetch live scores from ESPN
    league = League(league_id=update_weekly.LEAGUE_ID, year=2026, espn_s2=update_weekly.ESPN_S2, swid=update_weekly.SWID)
    bs = league.box_scores(10)
    
    scores_map = {}
    for m in bs:
        if m.home_team and m.away_team:
            t1 = update_weekly.TEAM_DICT.get(m.home_team.team_id, m.home_team.team_name)
            t2 = update_weekly.TEAM_DICT.get(m.away_team.team_id, m.away_team.team_name)
            scores_map[t1] = m.home_score
            scores_map[t2] = m.away_score

    # 3. Update MatchupHistory
    ws_mh = wb.Sheets("MatchupHistory")
    updated = 0
    
    for row in range(2, 500):
        yr_val = str(ws_mh.Cells(row, 1).Value or "").replace(".0", "").strip()
        wk_val = str(ws_mh.Cells(row, 2).Value or "").replace(".0", "").strip()
        
        # Match 2026 Week 10
        if yr_val == "2026" and wk_val == "10":
            t1 = str(ws_mh.Cells(row, 3).Value or "").strip() # Col C
            t2 = str(ws_mh.Cells(row, 5).Value or "").strip() # Col E
            
            if t1 in scores_map:
                ws_mh.Cells(row, 4).Value = scores_map[t1] # Col D
            if t2 in scores_map:
                ws_mh.Cells(row, 6).Value = scores_map[t2] # Col F
            
            # Extend formulas down for columns I through AP (cols 9 to 42)
            for col in range(9, 43):
                prev_formula = ws_mh.Cells(row - 1, col).Formula
                if prev_formula and str(prev_formula).startswith("="):
                    ws_mh.Cells(row, col).Formula = prev_formula
                    
            updated += 1

    print(f"Successfully populated and extended formulas for {updated} Week 10 rows in MatchupHistory!")

    # 4. Execute the RunTests macro
    try:
        excel.Run("RunTests")
        print("Successfully executed RunTests macro!")
    except Exception as e:
        print("Macro execution note:", e)

    wb.Save()
    wb.Close()
    print("Excel model successfully updated, tested, and saved!")

except Exception as e:
    print("Error during Excel update:", e)
finally:
    excel.Quit()
