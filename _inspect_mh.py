import pandas as pd

excel_path = "FantasyOddsModel2026-v1_2.xlsb"
df = pd.read_excel(excel_path, sheet_name="MatchupHistory", engine="pyxlsb", header=None)

print(f"Total rows in MatchupHistory: {len(df)}")
print("\n--- First 3 Rows (Headers/Top) ---")
print(df.iloc[:3, :10])

print("\n--- Searching for '2026' across all cells ---")
mask_2026 = df.astype(str).apply(lambda x: x.str.contains('2026', na=False)).any(axis=1)
df_2026 = df[mask_2026]
print(f"Found {len(df_2026)} rows containing '2026'.")

if not df_2026.empty:
    print("\n--- Sample 2026 Rows (Last 15 rows of 2026, Cols 0 to 9) ---")
    # Show Excel row numbers (index + 1)
    sample = df_2026.iloc[-15:, :10].copy()
    sample.index = sample.index + 1
    print(sample)
else:
    print("\n--- Last 15 Rows of the Entire Sheet (Cols 0 to 9) ---")
    sample = df.iloc[-15:, :10].copy()
    sample.index = sample.index + 1
    print(sample)
