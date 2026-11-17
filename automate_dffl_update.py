import os
import win32com.client
import update_weekly
from espn_api.football import League

def automate_excel_update():
    excel_path = os.path.abspath("FantasyOddsModel2026-v1_2.xlsb")
    print(f"Opening master Excel model: {excel_path}")
    
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    
    try:
        wb = excel.Workbooks.Open(excel_path)
        
        # 1. Update Inputs!B20 to 10 weeks played
        try:
            ws_inputs = wb.Sheets("Inputs")
            ws_inputs.Range("B20").Value = 10
            print("✔ Updated Inputs!B20 to 10 weeks played.")
        except Exception as e:
            print("Note on Inputs!B20 update:", e)
            
        # 2. Fetch live Week 10 box scores from ESPN
        print("Fetching Week 10 scoring data from ESPN API...")
        league = League(league_id=update_weekly.LEAGUE_ID, year=2026, espn_s2=update_weekly.ESPN_S2, swid=update_weekly.SWID)
        bs = league.box_scores(10)
        
        scores_map = {}
        for m in bs:
            if m.home_team and m.away_team:
                t1 = update_weekly.TEAM_DICT.get(m.home_team.team_id, m.home_team.team_name)
                t2 = update_weekly.TEAM_DICT.get(m.away_team.team_id, m.away_team.team_name)
                scores_map[t1] = m.home_score
                scores_map[t2] = m.away_score

        # 3. Update MatchupHistory with robust numeric/string parsing
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
            
            # Target 2026 Week 10 schedule rows
            if yr_val == 2026 and wk_val == 10:
                t1 = str(ws_mh.Cells(row, 3).Value or "").strip() # Col C
                t2 = str(ws_mh.Cells(row, 5).Value or "").strip() # Col E
                
                # Input Scores into Col D and Col F
                if t1 in scores_map:
                    ws_mh.Cells(row, 4).Value = scores_map[t1]
                if t2 in scores_map:
                    ws_mh.Cells(row, 6).Value = scores_map[t2]
                
                # Drag down formulas for columns I through AP (cols 9 to 42)
                for col in range(9, 43):
                    prev_formula = ws_mh.Cells(row - 1, col).Formula
                    if prev_formula and str(prev_formula).startswith("="):
                        ws_mh.Cells(row, col).Formula = prev_formula
                        
                updated_count += 1
                
        print(f"✔ Populated scores and dragged down formulas for {updated_count} matchups in MatchupHistory.")

        # 4. Save Workbook
        wb.Save()
        wb.Close()
        print("✔ Master Excel model successfully updated and saved!")

    except Exception as e:
        print("❌ Error during Excel automation:", e)
    finally:
        excel.Quit()

if __name__ == "__main__":
    automate_excel_update()
