"""
build_bpc_times.py — extract BPC per-group solve times + gaps from the baseline
paper (Riera-Ledesma & Salazar-Gonzalez 2021, COR) Tables 2–5, so the §6.2
runtime comparison uses BPC's *actual reported times*, not its 1-hour cap.

Tables (pages 11–14): T2=H1/H2, T3=H3/H4, T4=E1/E2, T5=E3/E4.
Family map H1..H4 → A,B,C,D ; E1..E4 → EA,EB,EC,ED.
Per algorithm (BPC-SRPS-E, BPC-SRPS-N) the columns are:
    CPU: RT OA   Gap: RT OA   #col (17) (18) #nod  ✓(solved/5)
We keep the **OA** (overall) CPU time and OA gap, and the solved count, for both
variants. Our `adaptive_master.csv:bpc_oa_gap_pct` equals the E-variant OA gap
(used here as a cross-check).

Usage:  python build_bpc_times.py
Output: results/analysis/bpc_times.csv   (+ validation printout)
"""
import csv, re
import pypdf

PDF = "docs/OPS_Riera-Ledesma_Salazar-Gonzalez_2021_COR.pdf"
PAGES = [10, 11, 12, 13]                      # 0-indexed → pages 11–14
FAM = {"H1": "A", "H2": "B", "H3": "C", "H4": "D",
       "E1": "EA", "E2": "EB", "E3": "EC", "E4": "ED"}
STUDY = {"B", "C", "D", "EB", "EC", "ED"}
ALPHAS = {"0.25", "0.50", "0.75"}


def main():
    r = pypdf.PdfReader(PDF)
    rows = []
    fam = None
    n = vk = None
    for pg in PAGES:
        for line in (r.pages[pg].extract_text() or "").splitlines():
            line = line.strip()
            gm = re.match(r"Group\s+([HE]\d)", line)
            if gm:
                fam = FAM[gm.group(1)]
                n = vk = None
                continue
            toks = line.split()
            if len(toks) < 20:
                continue
            # numeric row?
            try:
                float(toks[0])
            except ValueError:
                continue
            if toks[0] in ALPHAS:                 # alpha-row: a |V*| + 18
                if n is None:
                    continue
                a = toks[0]; rest = toks[1:]
            else:                                  # n-row: n |Vk| a |V*| + 18
                if len(toks) < 22:
                    continue
                n = toks[0]; vk = toks[1]; a = toks[2]; rest = toks[3:]
            if a not in ALPHAS or len(rest) < 19:
                continue
            blk = rest[1:19]                       # skip |V*|, take 18 cols
            E, N = blk[:9], blk[9:18]
            if fam not in STUDY:
                continue
            rows.append({
                "family": fam, "n": int(n), "alpha": float(a),
                "bpcE_cpu_oa_s": float(E[1]), "bpcE_gap_oa": float(E[3]),
                "bpcE_solved": int(float(E[8])),
                "bpcN_cpu_oa_s": float(N[1]), "bpcN_gap_oa": float(N[3]),
                "bpcN_solved": int(float(N[8])),
            })

    out = "results/analysis/bpc_times.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"Parsed {len(rows)} BPC group rows -> {out}\n")

    # ---- cross-check E-variant OA gap against our bpc_oa_gap_pct ----
    try:
        import pandas as pd
        d = pd.read_csv("results/adaptive_master.csv")
        key = d.drop_duplicates(["family", "n", "alpha"])[
            ["family", "n", "alpha", "bpc_oa_gap_pct"]]
        bp = pd.DataFrame(rows)
        m = bp.merge(key, on=["family", "n", "alpha"], how="left")
        m["match"] = (m["bpc_oa_gap_pct"].round(2) == m["bpcE_gap_oa"].round(2))
        ok = int(m["match"].sum()); tot = int(m["bpc_oa_gap_pct"].notna().sum())
        print(f"Validation: E-variant OA gap matches our bpc_oa_gap_pct on "
              f"{ok}/{tot} groups present in both.")
        bad = m[(~m["match"]) & m["bpc_oa_gap_pct"].notna()]
        if len(bad):
            print("Mismatches:")
            print(bad[["family", "n", "alpha", "bpcE_gap_oa",
                       "bpc_oa_gap_pct"]].to_string(index=False))
    except Exception as e:
        print("validation skipped:", e)


if __name__ == "__main__":
    main()
