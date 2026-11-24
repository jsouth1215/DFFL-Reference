import ast
import gc
import os
import re
import numpy as np
import pandas as pd

class _DummySt:
    @staticmethod
    def cache_data(*args, **kwargs):
        def _dec(fn):
            return fn
        return _dec

def _downcast_df(df):
    for col in df.columns:
        dt = df[col].dtype
        if pd.api.types.is_float_dtype(dt):
            df[col] = pd.to_numeric(df[col], downcast="float")
        elif pd.api.types.is_integer_dtype(dt):
            df[col] = pd.to_numeric(df[col], downcast="integer")
    return df

def _extract_load_box_scores_fn():
    with open("app.py", "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    fn_node = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "load_box_scores":
            fn_node = node
            break
    if fn_node is None:
        raise RuntimeError("Could not find load_box_scores in app.py")
    fn_node.decorator_list = []
    mod = ast.Module(body=[fn_node], type_ignores=[])
    ast.fix_missing_locations(mod)
    ns = {"pd": pd, "np": np, "gc": gc, "os": os, "re": re, "st": _DummySt}
    exec(compile(mod, "app.py", "exec"), ns)
    return ns["load_box_scores"]

def build_all():
    os.environ["DFFL_REBUILD_CACHE"] = "1"
    try:
        # 1. XLSB MatchupHistory & All-Time W-L Records (when FantasyOddsModel2026-v1_2.xlsb + pyxlsb exist)
        xlsb_path = "FantasyOddsModel2026-v1_2.xlsb"
        if os.path.exists(xlsb_path):
            try:
                mh = pd.read_excel(xlsb_path, sheet_name="MatchupHistory", engine="pyxlsb")
                _downcast_df(mh).to_pickle("cloud_cache_MatchupHistory.pkl")
                print(f"✔ cloud_cache_MatchupHistory.pkl ({len(mh)} rows, {os.path.getsize('cloud_cache_MatchupHistory.pkl')/1024:.0f} KB)")
            except Exception as e:
                print(f"  [Note] Skipped MatchupHistory xlsb refresh: {e}")
            try:
                at = pd.read_excel(xlsb_path, sheet_name="All-Time W-L Records", engine="pyxlsb")
                _downcast_df(at).to_pickle("cloud_cache_All_Time_W-L_Records.pkl")
                print(f"✔ cloud_cache_All_Time_W-L_Records.pkl ({len(at)} rows, {os.path.getsize('cloud_cache_All_Time_W-L_Records.pkl')/1024:.0f} KB)")
            except Exception as e:
                print(f"  [Note] Skipped All-Time W-L Records xlsb refresh: {e}")

        # 2. Cleaned & Downcasted Box Scores
        load_bs = _extract_load_box_scores_fn()
        box_df = load_bs()
        box_df = _downcast_df(box_df)
        box_df.to_pickle("cloud_cache_Box_Scores.pkl")
        print(f"✔ cloud_cache_Box_Scores.pkl ({len(box_df)} rows, {os.path.getsize('cloud_cache_Box_Scores.pkl')/1024:.0f} KB)")

        # 3. Raw combined Transactions
        tx_dfs = []
        if os.path.exists("espn_transactions_2019_2026.xlsx"):
            tx_dfs.append(pd.read_excel("espn_transactions_2019_2026.xlsx", sheet_name=0, engine="openpyxl"))
        if os.path.exists("espn_transactions_2018.xlsx"):
            try:
                tx_dfs.append(pd.read_excel("espn_transactions_2018.xlsx", sheet_name="Transactions", engine="openpyxl"))
            except Exception:
                tx_dfs.append(pd.read_excel("espn_transactions_2018.xlsx", sheet_name=0, engine="openpyxl"))
        if tx_dfs:
            raw_tx = pd.concat(tx_dfs, ignore_index=True)
            raw_tx.to_pickle("cloud_cache_Transactions.pkl")
            print(f"✔ cloud_cache_Transactions.pkl ({len(raw_tx)} rows, {os.path.getsize('cloud_cache_Transactions.pkl')/1024:.0f} KB)")

        # 4. Cleaned Transactions, Trades, WVA, TVA, and Drop Regret
        import transactions_tab
        import value_engine
        tx_clean, trades_df = transactions_tab.load_transactions_data.__wrapped__(box_df)
        tx_clean.to_pickle("cloud_cache_Transactions_Clean.pkl")
        trades_df.to_pickle("cloud_cache_Trades.pkl")
        print(f"✔ cloud_cache_Transactions_Clean.pkl ({len(tx_clean)} rows, {os.path.getsize('cloud_cache_Transactions_Clean.pkl')/1024:.0f} KB)")
        print(f"✔ cloud_cache_Trades.pkl ({len(trades_df)} trades, {os.path.getsize('cloud_cache_Trades.pkl')/1024:.0f} KB)")

        wva_df = value_engine.compute_waiver_value_added.__wrapped__(tx_clean, box_df)
        wva_df.to_pickle("cloud_cache_WVA.pkl")
        print(f"✔ cloud_cache_WVA.pkl ({len(wva_df)} rows, {os.path.getsize('cloud_cache_WVA.pkl')/1024:.0f} KB)")

        tva_df = value_engine.compute_trade_value_added.__wrapped__(trades_df, box_df)
        tva_df.to_pickle("cloud_cache_TVA.pkl")
        print(f"✔ cloud_cache_TVA.pkl ({len(tva_df)} rows, {os.path.getsize('cloud_cache_TVA.pkl')/1024:.0f} KB)")

        drops_df = value_engine.compute_drop_regret.__wrapped__(tx_clean, box_df)
        drops_df.to_pickle("cloud_cache_Drops.pkl")
        print(f"✔ cloud_cache_Drops.pkl ({len(drops_df)} rows, {os.path.getsize('cloud_cache_Drops.pkl')/1024:.0f} KB)")

        # 5. Refresh Zero-Point Starter classifications (nflverse snaps/injuries/byes)
        try:
            import build_zero_starters
            z_meta = build_zero_starters.build_zero_starters_meta(verbose=False)
            print(f"✔ zero_starters_meta.json ({len(z_meta)} entries, {os.path.getsize('zero_starters_meta.json')/1024:.0f} KB)")
        except Exception as e:
            print(f"  [Note] Skipped zero_starters_meta.json refresh: {e}")
    finally:
        os.environ.pop("DFFL_REBUILD_CACHE", None)

if __name__ == "__main__":
    build_all()
