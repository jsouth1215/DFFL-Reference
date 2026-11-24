import json
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import odds_engine


def build_machine_payload(games):
    """Build a tiny (~3 KB) JSON payload for the client-side Playoff Machine."""
    if games is None or games.empty:
        return None

    df = games.copy()
    df["Season_Str"] = df["Season"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    df["Week_Num"] = pd.to_numeric(df["Week"], errors="coerce").fillna(0).astype(int)
    df["Pts_Num"] = pd.to_numeric(df["Actual_Points"], errors="coerce").fillna(0.0)
    df["Team_Clean"] = df["Team_Name"].astype(str).str.strip()

    reg = df[(df["Game_Type"] == 1) & (df["Pts_Num"] > 0) & (df["Team_Clean"].str.upper() != "CAM")].copy()
    if reg.empty:
        return None

    szn_nums = sorted(
        [int(s) for s in reg["Season_Str"].unique() if s.isdigit()],
        reverse=True,
    )
    if not szn_nums:
        return None

    szn_int = szn_nums[0]
    szn_str = str(szn_int)
    szn_reg = reg[reg["Season_Str"] == szn_str].copy()

    through_wk = int(szn_reg["Week_Num"].max())
    reg_total_wks = max(through_wk, 14 if szn_int >= 2021 else 13)

    teams_list = sorted(szn_reg["Team_Clean"].unique().tolist())
    rem_pairs = odds_engine._infer_remaining_schedule(
        szn_reg, through_wk, reg_total_wks, teams_list, szn_clean=szn_str
    )

    # Current team stats
    teams_data = []
    all_pts = szn_reg["Pts_Num"].values
    szn_min = float(np.min(all_pts)) if len(all_pts) else 60.0
    szn_max = float(np.max(all_pts)) if len(all_pts) else 170.0
    lg_mean = float(np.mean(all_pts)) if len(all_pts) else 105.0
    lg_std = float(np.std(all_pts, ddof=1)) if len(all_pts) > 1 else 20.0

    for tm in teams_list:
        sub = szn_reg[szn_reg["Team_Clean"] == tm]
        w = int(sub["W"].sum())
        l = int(sub["L"].sum())
        t = int(sub["T"].sum())
        pf = round(float(sub["Pts_Num"].sum()), 2)
        pts = sub["Pts_Num"].values
        n_g = len(pts)
        raw_mean = float(np.mean(pts)) if n_g else lg_mean
        raw_std = float(np.std(pts, ddof=1)) if n_g > 1 else lg_std
        # Light empirical-Bayes shrinkage toward league std so small-sample stds stay realistic
        shrunk_std = float(np.clip(0.75 * raw_std + 0.25 * lg_std, 10.0, 42.0))
        teams_data.append({
            "name": tm,
            "w": w,
            "l": l,
            "t": t,
            "pf": pf,
            "ppg": round(raw_mean, 2),
            "std": round(shrunk_std, 2),
        })

    # Sort initial order by current standings (W + 0.5*T, PF)
    teams_data.sort(key=lambda x: (x["w"] + 0.5 * x["t"], x["pf"]), reverse=True)
    name_to_idx = {x["name"]: i for i, x in enumerate(teams_data)}

    games_data = []
    for gi, (wk, t1, t2) in enumerate(sorted(rem_pairs, key=lambda x: (x[0], x[1]))):
        if t1 in name_to_idx and t2 in name_to_idx:
            games_data.append({
                "id": gi,
                "wk": int(wk),
                "t1": name_to_idx[t1],
                "t2": name_to_idx[t2],
            })

    return {
        "season": szn_str,
        "through_wk": through_wk,
        "reg_total_wks": reg_total_wks,
        "szn_min": round(szn_min, 1),
        "szn_max": round(szn_max, 1),
        "teams": teams_data,
        "games": games_data,
    }


def render_playoff_machine(games):
    payload = build_machine_payload(games)
    if not payload:
        st.info("No regular-season data available for the Playoff Machine.")
        return

    if not payload["games"]:
        st.info(
            f"The {payload['season']} regular season is complete (through Week {payload['through_wk']}). "
            "Switch to **Playoff Brackets** to view the finalized postseason."
        )
        return

    rem_wks = sorted({g["wk"] for g in payload["games"]})
    wk_range = f"Weeks {rem_wks[0]}–{rem_wks[-1]}" if len(rem_wks) > 1 else f"Week {rem_wks[0]}"

    st.markdown(f"### {payload['season']} DFFL Playoff Machine ({wk_range})")
    st.caption(
        "Pick winners or type exact scores for any remaining games to see **Playoff**, **Bye**, and **Last Place Game** "
        "odds update instantly in your browser (zero server reruns). Leave score boxes blank to draw realistic scores around each team's PPG."
    )

    payload_json = json.dumps(payload)
    # Auto-size iframe height so desktop shows standings, bracket, and matchups cleanly without double-scroll
    n_wks = len(rem_wks)
    iframe_height = 1040 if n_wks >= 2 else 980

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 2px 2px 12px 2px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a;
    background: transparent;
    font-size: 13px;
  }}

  /* Toolbar */
  .pm-toolbar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 10px;
  }}
  .pm-btn-group {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }}
  .pm-btn {{
    appearance: none;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: #0f172a;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.12s ease;
  }}
  .pm-btn:hover {{
    background: #f1f5f9;
    border-color: #94a3b8;
  }}
  .pm-btn.primary {{
    background: #0f172a;
    color: #ffffff;
    border-color: #0f172a;
  }}
  .pm-btn.primary:hover {{
    background: #1e293b;
  }}
  .pm-btn.danger {{
    color: #b91c1c;
    border-color: #fecaca;
    background: #fef2f2;
  }}
  .pm-btn.danger:hover {{
    background: #fee2e2;
  }}
  .pm-seg {{
    display: inline-flex;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    overflow: hidden;
    background: #ffffff;
  }}
  .pm-seg button {{
    border: none;
    background: transparent;
    padding: 5px 9px;
    font-size: 11.5px;
    font-weight: 600;
    color: #475569;
    cursor: pointer;
  }}
  .pm-seg button.active {{
    background: #0f172a;
    color: #ffffff;
  }}
  .pm-status {{
    font-size: 11.5px;
    color: #475569;
    font-weight: 600;
  }}
  .pm-status strong {{ color: #0f172a; }}

  /* Standings Table */
  .pm-table-wrap {{
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    overflow-x: auto;
    background: #ffffff;
    margin-bottom: 10px;
  }}
  table.pm-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
    white-space: nowrap;
  }}
  table.pm-table thead th {{
    background: #f8fafc;
    color: #334155;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 7px 8px;
    border-bottom: 1px solid #cbd5e1;
    text-align: center;
  }}
  table.pm-table thead th.left {{ text-align: left; }}
  table.pm-table tbody td {{
    padding: 5.5px 8px;
    border-bottom: 1px solid #f1f5f9;
    text-align: center;
    vertical-align: middle;
  }}
  table.pm-table tbody tr:last-child td {{ border-bottom: none; }}
  table.pm-table tbody tr:hover {{ background: #f8fafc; }}

  /* Cutline visual dividers */
  tr.cut-bye td {{ border-bottom: 2px solid #93c5fd !important; }}
  tr.cut-po td {{ border-bottom: 2px solid #64748b !important; }}
  tr.cut-lp td {{ border-top: 2px solid #fca5a5 !important; }}

  .seed-badge {{
    display: inline-block;
    min-width: 22px;
    padding: 1px 5px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 11.5px;
  }}
  .seed-bye {{ background: #dcfce7; color: #166534; }}
  .seed-po {{ background: #dbeafe; color: #1e40af; }}
  .seed-out {{ background: #f1f5f9; color: #475569; }}
  .seed-lp {{ background: #fee2e2; color: #991b1b; }}

  .tm-cell {{
    text-align: left !important;
    font-weight: 700;
    color: #0f172a;
  }}
  .rec-sub {{
    font-size: 10.5px;
    color: #64748b;
    font-weight: 500;
    margin-left: 3px;
  }}
  .pf-sub {{
    font-size: 10.5px;
    color: #0284c7;
    font-weight: 600;
    display: block;
    line-height: 1.1;
  }}

  .odds-main {{
    font-weight: 700;
    color: #0f172a;
  }}
  .odds-ml {{
    font-size: 11px;
    color: #475569;
    font-weight: 600;
    margin-left: 4px;
  }}
  .odds-clinched {{
    color: #15803d;
    font-weight: 800;
    font-size: 11.5px;
  }}
  .odds-elim {{
    color: #94a3b8;
    font-weight: 700;
    font-size: 11.5px;
  }}
  .odds-lp-lock {{
    color: #b91c1c;
    font-weight: 800;
    font-size: 11.5px;
  }}
  .delta {{
    display: inline-block;
    font-size: 10.5px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 4px;
    margin-left: 4px;
  }}
  .delta-up {{ background: #dcfce7; color: #15803d; }}
  .delta-dn {{ background: #fee2e2; color: #b91c1c; }}
  .delta-bad-up {{ background: #fee2e2; color: #b91c1c; }}
  .delta-bad-dn {{ background: #dcfce7; color: #15803d; }}

  /* Projected Week 15 Bracket */
  .pm-bracket-bar {{
    display: grid;
    grid-template-columns: repeat(4, minmax(180px, 1fr));
    gap: 8px;
    margin-bottom: 12px;
  }}
  .bk-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 10px;
  }}
  .bk-card.bk-bye {{ border-left: 3px solid #16a34a; }}
  .bk-card.bk-qf {{ border-left: 3px solid #2563eb; }}
  .bk-card.bk-lp {{ border-left: 3px solid #dc2626; }}
  .bk-title {{
    font-size: 10.5px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #64748b;
    margin-bottom: 5px;
  }}
  .bk-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 0;
  }}
  .bk-seed {{
    color: #64748b;
    font-size: 11px;
    margin-right: 4px;
  }}
  .bk-rec {{
    font-size: 11px;
    color: #475569;
    font-weight: 500;
  }}
  .bk-tie-warn {{
    margin-top: 4px;
    font-size: 10.5px;
    color: #b45309;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 4px;
    padding: 2px 6px;
    font-weight: 600;
  }}

  /* Matchup Grid */
  .pm-weeks-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
    gap: 10px;
  }}
  .wk-col {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px;
  }}
  .wk-hdr {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 2px 6px 2px;
    margin-bottom: 6px;
    border-bottom: 1px solid #e2e8f0;
  }}
  .wk-title {{
    font-weight: 800;
    font-size: 12.5px;
    color: #0f172a;
  }}
  .wk-clear {{
    border: none;
    background: transparent;
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    padding: 2px 5px;
    border-radius: 4px;
  }}
  .wk-clear:hover {{
    background: #e2e8f0;
    color: #0f172a;
  }}

  .gm-card {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 7px;
    padding: 6px 7px;
    margin-bottom: 6px;
    transition: border-color 0.12s ease;
  }}
  .gm-card:last-child {{ margin-bottom: 0; }}
  .gm-card.picked {{ border-color: #93c5fd; background: #fafdff; }}

  .gm-row {{
    display: grid;
    grid-template-columns: 1fr 48px 34px 48px 1fr;
    gap: 4px;
    align-items: center;
  }}
  .tm-btn {{
    appearance: none;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    border-radius: 5px;
    padding: 5px 5px;
    cursor: pointer;
    text-align: center;
    line-height: 1.15;
    transition: all 0.1s ease;
    color: #0f172a;
  }}
  .tm-btn:hover {{
    border-color: #64748b;
    background: #f8fafc;
  }}
  .tm-btn .t-nm {{
    display: block;
    font-weight: 700;
    font-size: 12px;
  }}
  .tm-btn .t-rc {{
    display: block;
    font-size: 10px;
    color: #64748b;
    font-weight: 600;
  }}
  .tm-btn.win {{
    background: #0f172a;
    border-color: #0f172a;
    color: #ffffff;
  }}
  .tm-btn.win .t-rc {{ color: #cbd5e1; }}
  .tm-btn.lose {{
    background: #f8fafc;
    border-color: #e2e8f0;
    color: #94a3b8;
  }}
  .tm-btn.lose .t-rc {{ color: #cbd5e1; }}
  .tm-btn.tie {{
    background: #fef3c7;
    border-color: #f59e0b;
    color: #92400e;
  }}

  .sim-btn {{
    appearance: none;
    border: 1px solid #e2e8f0;
    background: #f1f5f9;
    color: #475569;
    font-size: 10px;
    font-weight: 700;
    padding: 6px 2px;
    border-radius: 5px;
    cursor: pointer;
    text-transform: uppercase;
  }}
  .sim-btn.active {{
    background: #e0f2fe;
    border-color: #7dd3fc;
    color: #0369a1;
  }}
  .sim-btn:hover {{ background: #e2e8f0; }}

  .sc-in {{
    width: 100%;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 5px 3px;
    font-size: 11.5px;
    font-weight: 600;
    text-align: center;
    color: #0f172a;
    background: #ffffff;
    -moz-appearance: textfield;
  }}
  .sc-in::-webkit-outer-spin-button,
  .sc-in::-webkit-inner-spin-button {{ -webkit-appearance: none; margin: 0; }}
  .sc-in::placeholder {{ color: #cbd5e1; font-weight: 500; }}
  .sc-in:focus {{
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.14);
  }}
  .sc-in.has-val {{
    background: #eff6ff;
    border-color: #60a5fa;
    color: #1e3a8a;
  }}

  @media (max-width: 820px) {{
    .pm-bracket-bar {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
</head>
<body>
  <div class="pm-toolbar">
    <div class="pm-btn-group">
      <button class="pm-btn danger" id="btnReset">Reset All</button>
      <button class="pm-btn" id="btnChalk" title="Pick higher 2026 PPG team in every unpicked game">Chalk (PPG)</button>
      <button class="pm-btn" id="btnBestRec" title="Pick better current record in every unpicked game">Best Record</button>
      <button class="pm-btn" id="btnFillAvg" title="Fill blank score inputs with each team's 2026 PPG">Fill Avg Scores</button>
      <button class="pm-btn" id="btnRand" title="Randomize all remaining game winners">Randomize</button>
    </div>
    <div class="pm-btn-group">
      <div class="pm-seg" title="How unpicked games are simulated">
        <button id="modePpg" class="active">Sim: PPG-Weighted</button>
        <button id="modeCoin">Sim: 50/50 W-L</button>
      </div>
      <span class="pm-status" id="pmStatus">0 / 0 picked</span>
    </div>
  </div>

  <div class="pm-table-wrap">
    <table class="pm-table">
      <thead>
        <tr>
          <th>Seed</th>
          <th class="left">Team</th>
          <th>Record</th>
          <th>Proj PF</th>
          <th>Playoff Odds (% / ML)</th>
          <th>Bye Odds (% / ML)</th>
          <th>Last Place Game (% / ML)</th>
        </tr>
      </thead>
      <tbody id="pmStandingsBody"></tbody>
    </table>
  </div>

  <div class="pm-bracket-bar" id="pmBracketBar"></div>
  <div class="pm-weeks-grid" id="pmWeeksGrid"></div>

<script>
const DATA = {payload_json};
const TEAMS = DATA.teams;
const GAMES = DATA.games;
const N_TEAMS = TEAMS.length;
const N_GAMES = GAMES.length;
const PLAYOFF_SPOTS = N_TEAMS >= 10 ? 6 : 4;
const BYE_SPOTS = 2;
const LPG_START = Math.max(1, N_TEAMS - 1); // 11th & 12th (1-based)
const N_SIM = 4000;

// State per game: pick = 0 (sim), 1 (t1 wins), 2 (t2 wins), 3 (tie via equal scores); s1, s2 = null or number
const state = GAMES.map(() => ({{ pick: 0, s1: null, s2: null }}));
let simMode = "ppg"; // "ppg" or "coin"
let baseline = null;

// Deterministic PRNG (Mulberry32) so clicks produce zero random jitter
function mulberry32(a) {{
  return function() {{
    let t = a += 0x6D2B79F5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }};
}}

function randNorm(rng) {{
  let u = 0, v = 0;
  while (u === 0) u = rng();
  while (v === 0) v = rng();
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
}}

function clamp(v, lo, hi) {{
  return v < lo ? lo : (v > hi ? hi : v);
}}

function round5(val) {{
  return Math.round(val / 5.0) * 5;
}}

function probToML(p, isClinched, isElim, blankIfElim) {{
  if (isClinched) return "CLINCHED";
  if (isElim) return blankIfElim ? "" : "ELIM";
  if (p >= 0.9999) return "-100000";
  if (p <= 0.0001) return "+100000";
  const pc = clamp(p, 1.0 / 1001.0, 1000.0 / 1001.0);
  if (Math.abs(pc - 0.5) < 1e-6) return "+100";
  if (pc > 0.5) {{
    const ml = clamp(round5((pc / (1.0 - pc)) * 100.0), 100, 100000);
    return "-" + ml;
  }} else {{
    const ml = clamp(round5(((1.0 - pc) / pc) * 100.0), 100, 100000);
    return "+" + ml;
  }}
}}

function fmtProb(p, isClinched, isElim, blankIfElim) {{
  if (isClinched) return "100.0%*";
  if (isElim) return blankIfElim ? "" : "0.0%*";
  if (p >= 0.9995) return ">99.9%";
  if (p <= 0.0005) return "<0.1%";
  return (p * 100.0).toFixed(1) + "%";
}}

function drawConditionalScores(i1, i2, forcedWinner, s1Lock, s2Lock, rng) {{
  const m1 = TEAMS[i1].ppg, sd1 = TEAMS[i1].std;
  const m2 = TEAMS[i2].ppg, sd2 = TEAMS[i2].std;

  if (s1Lock !== null && s2Lock !== null) {{
    return [s1Lock, s2Lock];
  }}
  if (s1Lock !== null) {{
    let x2 = clamp(m2 + sd2 * randNorm(rng), 35, 240);
    if (forcedWinner === 1 && x2 >= s1Lock) {{
      for (let k = 0; k < 6 && x2 >= s1Lock; k++) x2 = clamp(m2 + sd2 * randNorm(rng), 35, 240);
      if (x2 >= s1Lock) x2 = Math.max(0, s1Lock - (2 + rng() * 12));
    }} else if (forcedWinner === 2 && x2 <= s1Lock) {{
      for (let k = 0; k < 6 && x2 <= s1Lock; k++) x2 = clamp(m2 + sd2 * randNorm(rng), 35, 240);
      if (x2 <= s1Lock) x2 = s1Lock + (2 + rng() * 12);
    }}
    return [s1Lock, x2];
  }}
  if (s2Lock !== null) {{
    let x1 = clamp(m1 + sd1 * randNorm(rng), 35, 240);
    if (forcedWinner === 1 && x1 <= s2Lock) {{
      for (let k = 0; k < 6 && x1 <= s2Lock; k++) x1 = clamp(m1 + sd1 * randNorm(rng), 35, 240);
      if (x1 <= s2Lock) x1 = s2Lock + (2 + rng() * 12);
    }} else if (forcedWinner === 2 && x1 >= s2Lock) {{
      for (let k = 0; k < 6 && x1 >= s2Lock; k++) x1 = clamp(m1 + sd1 * randNorm(rng), 35, 240);
      if (x1 >= s2Lock) x1 = Math.max(0, s2Lock - (2 + rng() * 12));
    }}
    return [x1, s2Lock];
  }}

  // Neither score locked
  let x1 = clamp(m1 + sd1 * randNorm(rng), 35, 240);
  let x2 = clamp(m2 + sd2 * randNorm(rng), 35, 240);
  if (forcedWinner === 0) return [x1, x2];

  if (forcedWinner === 1) {{
    for (let k = 0; k < 8 && x1 <= x2; k++) {{
      x1 = clamp(m1 + sd1 * randNorm(rng), 35, 240);
      x2 = clamp(m2 + sd2 * randNorm(rng), 35, 240);
    }}
    if (x1 <= x2) {{
      const mid = 0.5 * (x1 + x2);
      const gap = 0.35 * Math.abs(x1 - x2) + 2.5 + rng() * 6.0;
      x1 = mid + gap;
      x2 = Math.max(35, mid - gap);
    }}
  }} else if (forcedWinner === 2) {{
    for (let k = 0; k < 8 && x2 <= x1; k++) {{
      x1 = clamp(m1 + sd1 * randNorm(rng), 35, 240);
      x2 = clamp(m2 + sd2 * randNorm(rng), 35, 240);
    }}
    if (x2 <= x1) {{
      const mid = 0.5 * (x1 + x2);
      const gap = 0.35 * Math.abs(x1 - x2) + 2.5 + rng() * 6.0;
      x2 = mid + gap;
      x1 = Math.max(35, mid - gap);
    }}
  }}
  return [x1, x2];
}}

// Stress test extreme win-out (500 pts/wk) or lose-out (10 pts/wk) respecting all user picks & typed scores
function stressCheck(targetIdx, mode, curState) {{
  const rng = mulberry32(9001 + targetIdx * 17 + (mode === "win" ? 0 : 500));
  const N_STRESS = 1800;
  let anyPo = false, allPo = true;
  let anyBye = false, allBye = true;
  let anySafeLp = false, allSafeLp = true;

  // Precompute current locked wins for bias
  const baseEffW = TEAMS.map(t => t.w + 0.5 * t.t);
  const effW = new Float64Array(N_TEAMS);
  const pf = new Float64Array(N_TEAMS);
  const score = new Float64Array(N_TEAMS);

  for (let tr = 0; tr < N_STRESS; tr++) {{
    for (let i = 0; i < N_TEAMS; i++) {{
      effW[i] = baseEffW[i];
      pf[i] = TEAMS[i].pf;
    }}
    const biased = tr >= (N_STRESS >> 1);

    for (let g = 0; g < N_GAMES; g++) {{
      const gm = GAMES[g];
      const st = curState[g];
      const i1 = gm.t1, i2 = gm.t2;

      // Respect exact typed scores first
      if (st.s1 !== null && st.s2 !== null) {{
        pf[i1] += st.s1;
        pf[i2] += st.s2;
        if (st.s1 > st.s2) effW[i1] += 1;
        else if (st.s2 > st.s1) effW[i2] += 1;
        else {{ effW[i1] += 0.5; effW[i2] += 0.5; }}
        continue;
      }}

      // Determine outcome (respect user pick if set)
      let wChoice = st.pick; // 1, 2, 3, or 0
      if (wChoice === 0) {{
        if (i1 === targetIdx) {{
          wChoice = (mode === "win") ? 1 : 2;
        }} else if (i2 === targetIdx) {{
          wChoice = (mode === "win") ? 2 : 1;
        }} else if (biased) {{
          const better1 = baseEffW[i1] >= baseEffW[i2];
          let pick1 = (mode === "lose") ? better1 : !better1;
          if (rng() < 0.25) pick1 = !pick1;
          wChoice = pick1 ? 1 : 2;
        }} else {{
          wChoice = rng() < 0.5 ? 1 : 2;
        }}
      }}

      if (wChoice === 1) effW[i1] += 1;
      else if (wChoice === 2) effW[i2] += 1;
      else {{ effW[i1] += 0.5; effW[i2] += 0.5; }}

      // Hostile PF assignment (respect single typed score if provided)
      const p1 = (st.s1 !== null) ? st.s1 : ((i1 === targetIdx) ? (mode === "win" ? 500 : 10) : (mode === "win" ? DATA.szn_min : DATA.szn_max));
      const p2 = (st.s2 !== null) ? st.s2 : ((i2 === targetIdx) ? (mode === "win" ? 500 : 10) : (mode === "win" ? DATA.szn_min : DATA.szn_max));
      pf[i1] += p1;
      pf[i2] += p2;
    }}

    for (let i = 0; i < N_TEAMS; i++) score[i] = effW[i] * 1e6 + pf[i];
    const tScore = score[targetIdx];
    let rank = 1;
    for (let i = 0; i < N_TEAMS; i++) {{
      if (i !== targetIdx && score[i] > tScore) rank++;
    }}

    const inPo = rank <= PLAYOFF_SPOTS;
    const inBye = rank <= BYE_SPOTS;
    const safeLp = rank < LPG_START;
    if (inPo) anyPo = true; else allPo = false;
    if (inBye) anyBye = true; else allBye = false;
    if (safeLp) anySafeLp = true; else allSafeLp = false;
  }}

  return mode === "win"
    ? {{ canPo: anyPo, canBye: anyBye, canEscapeLp: anySafeLp }}
    : {{ alwaysPo: allPo, alwaysBye: allBye, alwaysSafeLp: allSafeLp }};
}}

function runSimulation(curState) {{
  const rng = mulberry32(20261124);
  const poCnt = new Int32Array(N_TEAMS);
  const byeCnt = new Int32Array(N_TEAMS);
  const lpCnt = new Int32Array(N_TEAMS);
  const sumW = new Float64Array(N_TEAMS);
  const sumPF = new Float64Array(N_TEAMS);
  const sumRank = new Float64Array(N_TEAMS);

  const wArr = new Float64Array(N_TEAMS);
  const pfArr = new Float64Array(N_TEAMS);
  const comp = new Float64Array(N_TEAMS);
  const order = new Int32Array(N_TEAMS);

  let unpickedGames = 0;
  let untypedGames = 0;
  for (let g = 0; g < N_GAMES; g++) {{
    if (curState[g].pick === 0 && (curState[g].s1 === null || curState[g].s2 === null)) unpickedGames++;
    if (curState[g].s1 === null || curState[g].s2 === null) untypedGames++;
  }}

  for (let tr = 0; tr < N_SIM; tr++) {{
    for (let i = 0; i < N_TEAMS; i++) {{
      wArr[i] = TEAMS[i].w + 0.5 * TEAMS[i].t;
      pfArr[i] = TEAMS[i].pf;
      order[i] = i;
    }}

    for (let g = 0; g < N_GAMES; g++) {{
      const gm = GAMES[g];
      const st = curState[g];
      const i1 = gm.t1, i2 = gm.t2;

      let forced = st.pick;
      if (forced === 0 && st.s1 === null && st.s2 === null && simMode === "coin") {{
        forced = rng() < 0.5 ? 1 : 2;
      }}

      const [sc1, sc2] = drawConditionalScores(i1, i2, forced === 3 ? 0 : forced, st.s1, st.s2, rng);
      pfArr[i1] += sc1;
      pfArr[i2] += sc2;

      if (st.s1 !== null && st.s2 !== null) {{
        if (sc1 > sc2) wArr[i1] += 1;
        else if (sc2 > sc1) wArr[i2] += 1;
        else {{ wArr[i1] += 0.5; wArr[i2] += 0.5; }}
      }} else if (forced === 1) {{
        wArr[i1] += 1;
      }} else if (forced === 2) {{
        wArr[i2] += 1;
      }} else {{
        if (sc1 > sc2) wArr[i1] += 1;
        else if (sc2 > sc1) wArr[i2] += 1;
        else {{ wArr[i1] += 0.5; wArr[i2] += 0.5; }}
      }}
    }}

    for (let i = 0; i < N_TEAMS; i++) comp[i] = wArr[i] * 1e6 + pfArr[i];
    // Insertion sort on 12 items (faster than JS Array.sort)
    for (let a = 1; a < N_TEAMS; a++) {{
      const key = order[a];
      const kv = comp[key];
      let b = a - 1;
      while (b >= 0 && comp[order[b]] < kv) {{
        order[b + 1] = order[b];
        b--;
      }}
      order[b + 1] = key;
    }}

    for (let r = 0; r < N_TEAMS; r++) {{
      const ti = order[r];
      const rk = r + 1;
      sumRank[ti] += rk;
      sumW[ti] += wArr[ti];
      sumPF[ti] += pfArr[ti];
      if (rk <= PLAYOFF_SPOTS) poCnt[ti]++;
      if (rk <= BYE_SPOTS) byeCnt[ti]++;
      if (rk >= LPG_START) lpCnt[ti]++;
    }}
  }}

  // Locked record delta per team (from picked games)
  const lockW = new Int32Array(N_TEAMS);
  const lockL = new Int32Array(N_TEAMS);
  const lockT = new Int32Array(N_TEAMS);
  const typedPF = new Float64Array(N_TEAMS);
  for (let g = 0; g < N_GAMES; g++) {{
    const gm = GAMES[g], st = curState[g];
    if (st.s1 !== null) typedPF[gm.t1] += st.s1;
    if (st.s2 !== null) typedPF[gm.t2] += st.s2;
    if (st.pick === 1) {{ lockW[gm.t1]++; lockL[gm.t2]++; }}
    else if (st.pick === 2) {{ lockW[gm.t2]++; lockL[gm.t1]++; }}
    else if (st.pick === 3) {{ lockT[gm.t1]++; lockT[gm.t2]++; }}
  }}

  const allDeterministic = (unpickedGames === 0 && untypedGames === 0);
  const results = [];

  for (let i = 0; i < N_TEAMS; i++) {{
    const poP = poCnt[i] / N_SIM;
    const byeP = byeCnt[i] / N_SIM;
    const lpP = lpCnt[i] / N_SIM;

    let poClinch = false, poElim = false;
    let byeClinch = false, byeElim = false;
    let lpLock = false, lpSafe = false;

    if (allDeterministic) {{
      poClinch = poCnt[i] === N_SIM;
      poElim = poCnt[i] === 0;
      byeClinch = byeCnt[i] === N_SIM;
      byeElim = byeCnt[i] === 0;
      lpLock = lpCnt[i] === N_SIM;
      lpSafe = lpCnt[i] === 0;
    }} else {{
      const needLoseTest = (poCnt[i] === N_SIM || byeCnt[i] === N_SIM || lpCnt[i] === 0);
      const needWinTest = (poCnt[i] === 0 || byeCnt[i] === 0 || lpCnt[i] === N_SIM);
      if (needLoseTest) {{
        const lt = stressCheck(i, "lose", curState);
        if (poCnt[i] === N_SIM && lt.alwaysPo) poClinch = true;
        if (byeCnt[i] === N_SIM && lt.alwaysBye) byeClinch = true;
        if (lpCnt[i] === 0 && lt.alwaysSafeLp) lpSafe = true;
      }}
      if (needWinTest) {{
        const wt = stressCheck(i, "win", curState);
        if (poCnt[i] === 0 && !wt.canPo) poElim = true;
        if (byeCnt[i] === 0 && !wt.canBye) byeElim = true;
        if (lpCnt[i] === N_SIM && !wt.canEscapeLp) lpLock = true;
      }}
    }}

    results.push({{
      idx: i,
      name: TEAMS[i].name,
      curW: TEAMS[i].w,
      curL: TEAMS[i].l,
      curT: TEAMS[i].t,
      lockW: lockW[i],
      lockL: lockL[i],
      lockT: lockT[i],
      expW: sumW[i] / N_SIM,
      expPF: sumPF[i] / N_SIM,
      typedPF: typedPF[i],
      avgRank: sumRank[i] / N_SIM,
      poP, byeP, lpP,
      poClinch, poElim, byeClinch, byeElim, lpLock, lpSafe
    }});
  }}

  // Sort standings: if all games picked, sort by exact final W + projected PF; otherwise sort by Playoff %, Bye %, Exp W, Exp PF
  if (unpickedGames === 0) {{
    results.sort((a, b) => {{
      const wa = (a.curW + a.lockW) + 0.5 * (a.curT + a.lockT);
      const wb = (b.curW + b.lockW) + 0.5 * (b.curT + b.lockT);
      if (wb !== wa) return wb - wa;
      return b.expPF - a.expPF;
    }});
  }} else {{
    results.sort((a, b) => {{
      if (Math.abs(b.poP - a.poP) > 1e-4) return b.poP - a.poP;
      if (Math.abs(b.byeP - a.byeP) > 1e-4) return b.byeP - a.byeP;
      if (Math.abs(b.expW - a.expW) > 1e-3) return b.expW - a.expW;
      return b.expPF - a.expPF;
    }});
  }}

  return {{ results, unpickedGames, untypedGames }};
}}

function fmtDelta(curP, baseP, invertColor) {{
  if (baseP === null || baseP === undefined) return "";
  const d = (curP - baseP) * 100.0;
  if (Math.abs(d) < 0.45) return "";
  const sign = d > 0 ? "+" : "";
  const cls = invertColor
    ? (d > 0 ? "delta-bad-up" : "delta-bad-dn")
    : (d > 0 ? "delta-up" : "delta-dn");
  return `<span class="delta ${{cls}}">${{sign}}${{d.toFixed(1)}}%</span>`;
}}

function renderOddsCell(p, baseP, isClinched, isElim, blankIfElim, isLp) {{
  const deltaHtml = fmtDelta(p, baseP, isLp);
  if (isClinched) {{
    const lbl = isLp ? "LOCKED" : "CLINCHED";
    const cls = isLp ? "odds-lp-lock" : "odds-clinched";
    return `<span class="${{cls}}">100.0%* / ${{lbl}}</span>${{deltaHtml}}`;
  }}
  if (isElim) {{
    if (blankIfElim) return deltaHtml ? deltaHtml : "";
    return `<span class="odds-elim">0.0%* / ELIM</span>${{deltaHtml}}`;
  }}
  const pct = fmtProb(p, false, false, false);
  const ml = probToML(p, false, false, false);
  return `<span class="odds-main">${{pct}}</span><span class="odds-ml">(${{ml}})</span>${{deltaHtml}}`;
}}

function renderAll() {{
  const sim = runSimulation(state);
  const rows = sim.results;
  const pickedCnt = N_GAMES - sim.unpickedGames;

  const statusEl = document.getElementById("pmStatus");
  statusEl.innerHTML = `<strong>${{pickedCnt}} / ${{N_GAMES}}</strong> picked` +
    (sim.unpickedGames === 0 ? " &middot; <strong>Final Projection</strong>" : "");

  // Build baseline map by team idx
  const baseMap = {{}};
  if (baseline) {{
    baseline.results.forEach(r => {{ baseMap[r.idx] = r; }});
  }}

  // 1. Render Standings Table
  const tbody = document.getElementById("pmStandingsBody");
  let html = "";
  rows.forEach((r, idx) => {{
    const seed = idx + 1;
    let seedCls = "seed-out";
    if (seed <= BYE_SPOTS) seedCls = "seed-bye";
    else if (seed <= PLAYOFF_SPOTS) seedCls = "seed-po";
    else if (seed >= LPG_START) seedCls = "seed-lp";

    let rowCls = "";
    if (seed === BYE_SPOTS) rowCls = "cut-bye";
    else if (seed === PLAYOFF_SPOTS) rowCls = "cut-po";
    else if (seed === LPG_START) rowCls = "cut-lp";

    const totW = r.curW + r.lockW;
    const totL = r.curL + r.lockL;
    const totT = r.curT + r.lockT;
    const recMain = `${{totW}}-${{totL}}${{totT ? "-" + totT : ""}}`;
    const hasLocks = (r.lockW + r.lockL + r.lockT) > 0;
    const recSub = hasLocks
      ? `<span class="rec-sub">(was ${{r.curW}}-${{r.curL}})</span>`
      : `<span class="rec-sub">(proj ${{r.expW.toFixed(1)}}W)</span>`;

    const pfHtml = `${{r.expPF.toFixed(1)}}` +
      (r.typedPF > 0 ? `<span class="pf-sub">+${{r.typedPF.toFixed(1)}} entered</span>` : "");

    const b = baseMap[r.idx] || null;
    const poCell = renderOddsCell(r.poP, b ? b.poP : null, r.poClinch, r.poElim, false, false);
    const byeCell = renderOddsCell(r.byeP, b ? b.byeP : null, r.byeClinch, r.byeElim, true, false);
    const lpCell = renderOddsCell(r.lpP, b ? b.lpP : null, r.lpLock, r.lpSafe, true, true);

    html += `<tr class="${{rowCls}}">
      <td><span class="seed-badge ${{seedCls}}">#${{seed}}</span></td>
      <td class="tm-cell">${{r.name}}</td>
      <td><strong>${{recMain}}</strong>${{recSub}}</td>
      <td>${{pfHtml}}</td>
      <td>${{poCell}}</td>
      <td>${{byeCell}}</td>
      <td>${{lpCell}}</td>
    </tr>`;
  }});
  tbody.innerHTML = html;

  // 2. Render Projected Week 15 Bracket Bar
  const bBar = document.getElementById("pmBracketBar");
  const recStr = (r) => `${{r.curW + r.lockW}}-${{r.curL + r.lockL}}${{(r.curT + r.lockT) ? "-" + (r.curT + r.lockT) : ""}}`;
  const tieWarn = (a, b) => {{
    if (!a || !b) return "";
    const wa = (a.curW + a.lockW) + 0.5 * (a.curT + a.lockT);
    const wb = (b.curW + b.lockW) + 0.5 * (b.curT + b.lockT);
    const diff = Math.abs(a.expPF - b.expPF);
    if (sim.unpickedGames === 0 && wa === wb && diff < 35) {{
      return `<div class="bk-tie-warn">PF Tiebreaker: ${{a.name}} +${{diff.toFixed(1)}} over ${{b.name}}</div>`;
    }}
    return "";
  }};

  const r1 = rows[0], r2 = rows[1], r3 = rows[2], r4 = rows[3], r5 = rows[4], r6 = rows[5], r7 = rows[6];
  const r10 = rows[N_TEAMS - 3], r11 = rows[N_TEAMS - 2], r12 = rows[N_TEAMS - 1];

  bBar.innerHTML = `
    <div class="bk-card bk-bye">
      <div class="bk-title">First-Round Byes</div>
      <div class="bk-row"><span><span class="bk-seed">#1</span>${{r1.name}}</span><span class="bk-rec">${{recStr(r1)}} &middot; ${{r1.expPF.toFixed(0)}} PF</span></div>
      <div class="bk-row"><span><span class="bk-seed">#2</span>${{r2.name}}</span><span class="bk-rec">${{recStr(r2)}} &middot; ${{r2.expPF.toFixed(0)}} PF</span></div>
      ${{tieWarn(r2, r3)}}
    </div>
    <div class="bk-card bk-qf">
      <div class="bk-title">Quarterfinal 1 (W15)</div>
      <div class="bk-row"><span><span class="bk-seed">#3</span>${{r3.name}}</span><span class="bk-rec">${{recStr(r3)}} &middot; ${{r3.expPF.toFixed(0)}} PF</span></div>
      <div class="bk-row"><span><span class="bk-seed">#6</span>${{r6.name}}</span><span class="bk-rec">${{recStr(r6)}} &middot; ${{r6.expPF.toFixed(0)}} PF</span></div>
      ${{tieWarn(r6, r7)}}
    </div>
    <div class="bk-card bk-qf">
      <div class="bk-title">Quarterfinal 2 (W15)</div>
      <div class="bk-row"><span><span class="bk-seed">#4</span>${{r4.name}}</span><span class="bk-rec">${{recStr(r4)}} &middot; ${{r4.expPF.toFixed(0)}} PF</span></div>
      <div class="bk-row"><span><span class="bk-seed">#5</span>${{r5.name}}</span><span class="bk-rec">${{recStr(r5)}} &middot; ${{r5.expPF.toFixed(0)}} PF</span></div>
    </div>
    <div class="bk-card bk-lp">
      <div class="bk-title">Last Place Game (W15)</div>
      <div class="bk-row"><span><span class="bk-seed">#${{N_TEAMS - 1}}</span>${{r11.name}}</span><span class="bk-rec">${{recStr(r11)}} &middot; ${{r11.expPF.toFixed(0)}} PF</span></div>
      <div class="bk-row"><span><span class="bk-seed">#${{N_TEAMS}}</span>${{r12.name}}</span><span class="bk-rec">${{recStr(r12)}} &middot; ${{r12.expPF.toFixed(0)}} PF</span></div>
      ${{tieWarn(r10, r11)}}
    </div>
  `;

  // 3. Sync Matchup Card visual states
  GAMES.forEach((gm, g) => {{
    const st = state[g];
    const card = document.getElementById(`gm_${{g}}`);
    const b1 = document.getElementById(`b1_${{g}}`);
    const b2 = document.getElementById(`b2_${{g}}`);
    const bs = document.getElementById(`bs_${{g}}`);
    const i1 = document.getElementById(`s1_${{g}}`);
    const i2 = document.getElementById(`s2_${{g}}`);

    const isPicked = st.pick !== 0 || st.s1 !== null || st.s2 !== null;
    card.classList.toggle("picked", isPicked);

    b1.className = "tm-btn" + (st.pick === 1 ? " win" : (st.pick === 2 ? " lose" : (st.pick === 3 ? " tie" : "")));
    b2.className = "tm-btn" + (st.pick === 2 ? " win" : (st.pick === 1 ? " lose" : (st.pick === 3 ? " tie" : "")));
    bs.className = "sim-btn" + (!isPicked ? " active" : "");

    i1.classList.toggle("has-val", st.s1 !== null);
    i2.classList.toggle("has-val", st.s2 !== null);
    if (document.activeElement !== i1) i1.value = st.s1 !== null ? st.s1 : "";
    if (document.activeElement !== i2) i2.value = st.s2 !== null ? st.s2 : "";
  }});
}}

function buildMatchupsDOM() {{
  const grid = document.getElementById("pmWeeksGrid");
  const weeks = [...new Set(GAMES.map(g => g.wk))].sort((a, b) => a - b);
  let html = "";

  weeks.forEach(wk => {{
    const wkGames = GAMES.map((gm, idx) => ({{ gm, idx }})).filter(x => x.gm.wk === wk);
    html += `<div class="wk-col">
      <div class="wk-hdr">
        <span class="wk-title">Week ${{wk}}</span>
        <button class="wk-clear" data-wk="${{wk}}">Clear W${{wk}}</button>
      </div>`;

    wkGames.forEach(({{ gm, idx }}) => {{
      const t1 = TEAMS[gm.t1], t2 = TEAMS[gm.t2];
      html += `<div class="gm-card" id="gm_${{idx}}">
        <div class="gm-row">
          <button class="tm-btn" id="b1_${{idx}}" data-g="${{idx}}" data-side="1">
            <span class="t-nm">${{t1.name}}</span>
            <span class="t-rc">${{t1.w}}-${{t1.l}}</span>
          </button>
          <input class="sc-in" id="s1_${{idx}}" data-g="${{idx}}" data-side="1" type="number" step="0.1" min="0" max="400" placeholder="${{t1.ppg.toFixed(0)}}" title="Optional score for ${{t1.name}} (PPG: ${{t1.ppg.toFixed(1)}})" />
          <button class="sim-btn active" id="bs_${{idx}}" data-g="${{idx}}" data-side="0" title="Reset game to Sim">Sim</button>
          <input class="sc-in" id="s2_${{idx}}" data-g="${{idx}}" data-side="2" type="number" step="0.1" min="0" max="400" placeholder="${{t2.ppg.toFixed(0)}}" title="Optional score for ${{t2.name}} (PPG: ${{t2.ppg.toFixed(1)}})" />
          <button class="tm-btn" id="b2_${{idx}}" data-g="${{idx}}" data-side="2">
            <span class="t-nm">${{t2.name}}</span>
            <span class="t-rc">${{t2.w}}-${{t2.l}}</span>
          </button>
        </div>
      </div>`;
    }});
    html += `</div>`;
  }});

  grid.innerHTML = html;

  // Bind winner / sim buttons
  grid.querySelectorAll(".tm-btn, .sim-btn").forEach(btn => {{
    btn.addEventListener("click", () => {{
      const g = parseInt(btn.dataset.g, 10);
      const side = parseInt(btn.dataset.side, 10);
      const st = state[g];
      if (side === 0) {{
        st.pick = 0; st.s1 = null; st.s2 = null;
      }} else {{
        // Clicking the already-selected winner toggles back to Sim (unless scores lock it)
        if (st.pick === side && st.s1 === null && st.s2 === null) {{
          st.pick = 0;
        }} else {{
          st.pick = side;
          // If both scores were previously entered favoring the opposite side, clear them so the click wins cleanly
          if (st.s1 !== null && st.s2 !== null) {{
            if ((side === 1 && st.s1 <= st.s2) || (side === 2 && st.s2 <= st.s1)) {{
              st.s1 = null; st.s2 = null;
            }}
          }}
        }}
      }}
      renderAll();
    }});
  }});

  // Bind optional score inputs
  let scoreTimer = null;
  grid.querySelectorAll(".sc-in").forEach(inp => {{
    inp.addEventListener("input", () => {{
      const g = parseInt(inp.dataset.g, 10);
      const side = parseInt(inp.dataset.side, 10);
      const st = state[g];
      const raw = inp.value.trim();
      const val = raw === "" ? null : parseFloat(raw);
      const cleanVal = (val !== null && !isNaN(val) && val >= 0) ? val : null;

      if (side === 1) st.s1 = cleanVal; else st.s2 = cleanVal;

      if (st.s1 !== null && st.s2 !== null) {{
        if (st.s1 > st.s2) st.pick = 1;
        else if (st.s2 > st.s1) st.pick = 2;
        else st.pick = 3;
      }} else if (st.s1 === null && st.s2 === null && st.pick === 3) {{
        st.pick = 0;
      }}

      clearTimeout(scoreTimer);
      scoreTimer = setTimeout(renderAll, 90);
    }});
  }});

  // Bind Clear Week buttons
  grid.querySelectorAll(".wk-clear").forEach(btn => {{
    btn.addEventListener("click", () => {{
      const wk = parseInt(btn.dataset.wk, 10);
      GAMES.forEach((gm, g) => {{
        if (gm.wk === wk) {{
          state[g].pick = 0; state[g].s1 = null; state[g].s2 = null;
        }}
      }});
      renderAll();
    }});
  }});
}}

// Toolbar bindings
document.getElementById("btnReset").addEventListener("click", () => {{
  state.forEach(s => {{ s.pick = 0; s.s1 = null; s.s2 = null; }});
  renderAll();
}});

document.getElementById("btnChalk").addEventListener("click", () => {{
  GAMES.forEach((gm, g) => {{
    if (state[g].pick === 0 && state[g].s1 === null && state[g].s2 === null) {{
      state[g].pick = TEAMS[gm.t1].ppg >= TEAMS[gm.t2].ppg ? 1 : 2;
    }}
  }});
  renderAll();
}});

document.getElementById("btnBestRec").addEventListener("click", () => {{
  GAMES.forEach((gm, g) => {{
    if (state[g].pick === 0 && state[g].s1 === null && state[g].s2 === null) {{
      const t1 = TEAMS[gm.t1], t2 = TEAMS[gm.t2];
      const w1 = t1.w + 0.5 * t1.t, w2 = t2.w + 0.5 * t2.t;
      state[g].pick = (w1 > w2 || (w1 === w2 && t1.pf >= t2.pf)) ? 1 : 2;
    }}
  }});
  renderAll();
}});

document.getElementById("btnFillAvg").addEventListener("click", () => {{
  GAMES.forEach((gm, g) => {{
    const st = state[g];
    if (st.s1 === null) st.s1 = Number(TEAMS[gm.t1].ppg.toFixed(1));
    if (st.s2 === null) st.s2 = Number(TEAMS[gm.t2].ppg.toFixed(1));
    st.pick = st.s1 > st.s2 ? 1 : (st.s2 > st.s1 ? 2 : 3);
  }});
  renderAll();
}});

document.getElementById("btnRand").addEventListener("click", () => {{
  GAMES.forEach((gm, g) => {{
    state[g].s1 = null;
    state[g].s2 = null;
    state[g].pick = Math.random() < 0.5 ? 1 : 2;
  }});
  renderAll();
}});

document.getElementById("modePpg").addEventListener("click", () => {{
  if (simMode === "ppg") return;
  simMode = "ppg";
  document.getElementById("modePpg").classList.add("active");
  document.getElementById("modeCoin").classList.remove("active");
  baseline = runSimulation(GAMES.map(() => ({{ pick: 0, s1: null, s2: null }})));
  renderAll();
}});

document.getElementById("modeCoin").addEventListener("click", () => {{
  if (simMode === "coin") return;
  simMode = "coin";
  document.getElementById("modeCoin").classList.add("active");
  document.getElementById("modePpg").classList.remove("active");
  baseline = runSimulation(GAMES.map(() => ({{ pick: 0, s1: null, s2: null }})));
  renderAll();
}});

// Initial boot
buildMatchupsDOM();
baseline = runSimulation(GAMES.map(() => ({{ pick: 0, s1: null, s2: null }})));
renderAll();
</script>
</body>
</html>
"""

    components.html(html, height=iframe_height, scrolling=True)
