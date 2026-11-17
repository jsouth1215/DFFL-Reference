import pandas as pd

excel_path = "FantasyOddsModel2026-v1_2.xlsb"
wb_sheets = pd.ExcelFile(excel_path, engine="pyxlsb").sheet_names
print("All Sheet Names:", wb_sheets)

# Find the exact Player Scoring Data sheet name
psd_sheet = [s for s in wb_sheets if "Player" in s or "Scoring" in s or "Raw" in s][0]
print(f"\nInspecting sheet: '{psd_sheet}'")

df_psd = pd.read_excel(excel_path, sheet_name=psd_sheet, engine="pyxlsb", header=None)
print(f"Total rows in {psd_sheet}: {len(df_psd)}")

print("\n--- First 3 Rows (Headers) across all columns ---")
for col_idx in range(df_psd.shape[1]):
    col_letter = chr(65 + col_idx) if col_idx < 26 else chr(64 + col_idx // 26) + chr(65 + col_idx % 26)
    h0 = df_psd.iloc[0, col_idx]
    h1 = df_psd.iloc[1, col_idx]
    h2 = df_psd.iloc[2, col_idx]
    print(f"Col {col_idx+1} ({col_letter}): Row1={repr(h0)} | Row2={repr(h1)} | Row3={repr(h2)}")

print("\n--- Last 5 Populated Rows of Player Scoring Data ---")
tail_df = df_psd.dropna(how='all').iloc[-5:]
tail_df.index = tail_df.index + 1
print(tail_df.to_string())

print("\n--- Checking update_weekly.py structure ---")
with open("update_weekly.py", "r", encoding="utf-8") as f:
    print(f.read()[:2500])
