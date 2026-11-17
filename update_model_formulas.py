import os
import openpyxl
import update_weekly
from espn_api.football import League

def update_excel_model():
    excel_path = "FantasyOddsModel2026-v1_2.xlsx"
    if not os.path.exists(excel_path):
        excel_path = "FantasyOddsModel2026-v1_2.xlsb"
        print(f"Opening binary Excel model: {excel_path} (Note: openpyxl works best with .xlsx copies for structural writes)")
    
    wb = openpyxl.load_workbook(excel_path, keep_vba=True)
    
    # 1. Update Inputs!B20 to 10 weeks played
    if "Inputs" in wb.sheetnames:
        ws_inputs = wb["Inputs"]
        ws_inputs["B20"] = 10
        print("Updated Inputs!B20 to 10.")
    
    # 2. Fetch live Week 10 scores from ESPN
    league = League(league_id=update_weekly.LEAGUE_ID, year=2026, espn_s2=update_weekly.ESPN_S2, swid=update_weekly.SWID)
    bs = league.box_scores(10)
    
    scores_map = {}
    for m in bs:
        if m.home_team and m.away_team:
            t1 = update_weekly.TEAM_DICT.get(m.home_team.team_id, m.home_team.team_name)
            t2 = update_weekly.TEAM_DICT.get(m.away_team.team_id, m.away_team.team_name)
            scores_map[t1] = m.home_score
            scores_map[t2] = m.away_score

    # 3. Process MatchupHistory
    if "MatchupHistory" in wb.sheetnames:
        ws_mh = wb["MatchupHistory"]
        
        for row in range(2, ws_mh.max_row + 1):
            yr = ws_mh.cell(row=row, column=1).value
            wk = ws_mh.cell(row=row, column=2).value
            
            if yr and str(yr).startswith("2026") and wk and int(wk) == 10:
                t1 = str(ws_mh.cell(row=row, column=3).value or "").strip() # Col C
                t2 = str(ws_mh.cell(row=row, column=5).value or "").strip() # Col E
                
                # Fill Team 1 Score (Col D / 4) and Team 2 Score (Col F / 6)
                if t1 in scores_map:
                    ws_mh.cell(row=row, column=4).value = scores_map[t1]
                if t2 in scores_map:
                    ws_mh.cell(row=row, column=6).value = scores_map[t2]
                
                # Extend formulas down for columns I through AP (cols 9 to 42)
                for col in range(9, 43):
                    prev_cell = ws_mh.cell(row=row - 1, column=col)
                    curr_cell = ws_mh.cell(row=row, column=col)
                    if prev_cell.value and str(prev_cell.value).startswith("="):
                        curr_cell.value = prev_cell.value

        print("Successfully updated MatchupHistory scores and extended formulas through Week 10.")

    wb.save(excel_path)
    print("Workbook successfully saved!")

if __name__ == "__main__":
    update_excel_model()
