#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Signifikanztests + Effektstärken für Metriken über mehrere Runs und Modelle.

Design:
- Pro Run existieren Messwerte für mehrere Modelle => "within-subject"/repeated measures.
- Daher:
  - Normalverteilung (Shapiro) pro Modell x Metrik
  - Sphärizität ist bei n=5 schwierig; wir reporten trotzdem RM-ANOVA (AnovaRM) + Friedman robust
  - Paarweise Vergleiche: gepaarter t-Test (parametrisch) bzw. Wilcoxon (robust)
Effektstärken:
- RM-ANOVA: partielles Eta-Quadrat aus F und Freiheitsgraden
- Friedman: Kendall's W
- Paarweise: Cohen's dz (paired), zusätzlich rank-biserial r für Wilcoxon (optional)
"""

import json
import math
from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.anova import AnovaRM


# ----------------------------
# Konfiguration
# ----------------------------
JSON_PATH = Path("summaries_by_run.json")  # passe ggf. an
METRICS = ["accuracy", "precision", "recall", "f1Score"]
ALPHA = 0.05

# Modelle ausschließen, die in ALLEN Runs nur 0 liefern (typisch: harte Fehlerläufe)
EXCLUDE_ALL_ZERO_MODELS = True


# ----------------------------
# Hilfsfunktionen: Effektstärken
# ----------------------------
def cohen_dz_paired(x, y):
    """Cohen's dz für gepaarte Stichproben."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    d = x - y
    sd = d.std(ddof=1)
    if sd == 0:
        return np.nan
    return d.mean() / sd


def partial_eta_squared_from_F(F, df_effect, df_error):
    """partielles Eta^2 aus F und df."""
    if np.isnan(F):
        return np.nan
    return (F * df_effect) / (F * df_effect + df_error)


def kendalls_w_from_friedman(chi2, n, k):
    """Kendall's W aus Friedman Chi^2, n=Subjects (Runs), k=Groups (Modelle)."""
    # W = chi2 / (n*(k-1))
    return chi2 / (n * (k - 1))


def rank_biserial_from_wilcoxon(x, y):
    """
    Rank-biserial correlation r_rb für Wilcoxon signed-rank.
    Näherung über Ranks der Differenzen (ohne Ties-Handling-Finessen).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    d = x - y
    d = d[d != 0]
    if len(d) == 0:
        return np.nan
    ranks = stats.rankdata(abs(d))
    Wpos = ranks[d > 0].sum()
    Wneg = ranks[d < 0].sum()
    return (Wpos - Wneg) / (Wpos + Wneg)


# ----------------------------
# Daten laden & in Long-Format bringen
# ----------------------------
def load_long_dataframe(json_path: Path) -> pd.DataFrame:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    runs = data["summariesByRun"]

    rows = []
    for run_id_str, entries in runs.items():
        run_id = int(run_id_str)
        for e in entries:
            label = e["label"]
            summ = e["summary"]
            row = {"run": run_id, "model": label}
            for m in METRICS:
                row[m] = summ.get(m, np.nan)
            rows.append(row)

    df = pd.DataFrame(rows)

    # optional: Modelle entfernen, die über alle Runs in allen Metriken 0 sind
    if EXCLUDE_ALL_ZERO_MODELS:
        model_stats = (
            df.groupby("model")[METRICS]
            .apply(lambda g: np.all(np.isclose(g.fillna(0).to_numpy(), 0)))
        )
        drop_models = model_stats[model_stats].index.tolist()
        if drop_models:
            df = df[~df["model"].isin(drop_models)].copy()
            print(f"[INFO] Excluded all-zero models: {drop_models}")

    # nur Runs behalten, die für alle Modelle vorhanden sind (saubere RM-Struktur)
    # (AnovaRM & Friedman benötigen vollständige Blöcke)
    models = sorted(df["model"].unique())
    counts_per_run = df.groupby("run")["model"].nunique()
    good_runs = counts_per_run[counts_per_run == len(models)].index.tolist()
    if len(good_runs) < df["run"].nunique():
        bad_runs = sorted(set(df["run"].unique()) - set(good_runs))
        print(f"[WARN] Dropping incomplete runs: {bad_runs}")
        df = df[df["run"].isin(good_runs)].copy()

    return df


# ----------------------------
# Analysen
# ----------------------------
def normality_tests(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for metric in METRICS:
        for model, g in df.groupby("model"):
            x = g.sort_values("run")[metric].to_numpy(dtype=float)
            # Shapiro braucht mindestens 3 Werte
            if np.sum(~np.isnan(x)) >= 3:
                W, p = stats.shapiro(x)
            else:
                W, p = np.nan, np.nan
            out.append({"metric": metric, "model": model, "shapiro_W": W, "shapiro_p": p, "n": len(x)})
    return pd.DataFrame(out).sort_values(["metric", "shapiro_p"], ascending=[True, True])


def rm_anova_and_friedman(df: pd.DataFrame) -> pd.DataFrame:
    """
    Repeated-measures ANOVA (AnovaRM) + Friedman als robuste Alternative.
    """
    results = []
    models = sorted(df["model"].unique())
    n_runs = df["run"].nunique()
    k = len(models)

    for metric in METRICS:
        sub = df[["run", "model", metric]].dropna()

        # RM-ANOVA (within = model, subject = run)
        try:
            aov = AnovaRM(data=sub, depvar=metric, subject="run", within=["model"]).fit()
            # statsmodels liefert Tabelle mit F Value und Num/Den DF
            table = aov.anova_table
            F = float(table.loc["model", "F Value"])
            df1 = float(table.loc["model", "Num DF"])
            df2 = float(table.loc["model", "Den DF"])
            p = float(table.loc["model", "Pr > F"])
            peta2 = partial_eta_squared_from_F(F, df1, df2)
        except Exception as ex:
            print(f"[WARN] RM-ANOVA failed for {metric}: {ex}")
            F, df1, df2, p, peta2 = np.nan, np.nan, np.nan, np.nan, np.nan

        # Friedman (block = run)
        wide = sub.pivot(index="run", columns="model", values=metric)
        # sichere Reihenfolge
        wide = wide[models]
        # Friedman verlangt volle Zeilen
        wide = wide.dropna(axis=0, how="any")
        if wide.shape[0] >= 2 and wide.shape[1] >= 2:
            chi2, p_fr = stats.friedmanchisquare(*[wide[c].to_numpy() for c in wide.columns])
            W = kendalls_w_from_friedman(chi2, n=wide.shape[0], k=wide.shape[1])
        else:
            chi2, p_fr, W = np.nan, np.nan, np.nan

        results.append({
            "metric": metric,
            "n_runs": n_runs,
            "k_models": k,
            "rm_anova_F": F,
            "rm_anova_df1": df1,
            "rm_anova_df2": df2,
            "rm_anova_p": p,
            "rm_anova_partial_eta2": peta2,
            "friedman_chi2": chi2,
            "friedman_p": p_fr,
            "kendalls_W": W
        })

    return pd.DataFrame(results)


def pairwise_tests(df: pd.DataFrame, adjust="holm") -> pd.DataFrame:
    """
    Paarweise Modellvergleiche je Metrik:
    - gepaarter t-Test (wenn beide Gruppen pro Run vorhanden)
    - Wilcoxon signed-rank (robust)
    - Effektstärken: Cohen's dz, rank-biserial r_rb
    p-Adjust (Holm oder Bonferroni) pro Metrik und Testfamilie.
    """
    models = sorted(df["model"].unique())
    pairs = list(combinations(models, 2))
    out_rows = []

    for metric in METRICS:
        # Pivot pro Run, damit Paarungen sauber sind
        wide = df.pivot(index="run", columns="model", values=metric)[models].dropna(axis=0, how="any")

        pvals_t = []
        pvals_w = []
        tmp_rows = []

        for a, b in pairs:
            x = wide[a].to_numpy(dtype=float)
            y = wide[b].to_numpy(dtype=float)

            # gepaarter t-Test
            t_stat, p_t = stats.ttest_rel(x, y, nan_policy="omit")
            dz = cohen_dz_paired(x, y)

            # Wilcoxon (bei sehr kleinen n robust, aber braucht mind. eine Nicht-Null-Differenz)
            try:
                w_stat, p_w = stats.wilcoxon(x, y, zero_method="wilcox", correction=False, alternative="two-sided")
                r_rb = rank_biserial_from_wilcoxon(x, y)
            except ValueError:
                w_stat, p_w, r_rb = np.nan, np.nan, np.nan

            tmp_rows.append({
                "metric": metric,
                "model_a": a,
                "model_b": b,
                "n_runs": len(x),
                "t_stat": t_stat,
                "p_t": p_t,
                "cohen_dz": dz,
                "wilcoxon_W": w_stat,
                "p_wilcoxon": p_w,
                "rank_biserial_r": r_rb
            })
            pvals_t.append(p_t)
            pvals_w.append(p_w)

        # p-Wert-Korrektur pro Metrik getrennt für t-Tests und Wilcoxon
        def adjust_pvals(pvals, method):
            pvals = np.array(pvals, dtype=float)
            mask = ~np.isnan(pvals)
            adj = np.full_like(pvals, np.nan)
            if mask.sum() == 0:
                return adj
            if method == "bonferroni":
                adj[mask] = np.minimum(pvals[mask] * mask.sum(), 1.0)
            elif method == "holm":
                # Holm step-down
                idx = np.argsort(pvals[mask])
                sorted_p = pvals[mask][idx]
                m = len(sorted_p)
                holm = np.empty(m)
                for i, pv in enumerate(sorted_p):
                    holm[i] = min((m - i) * pv, 1.0)
                # monotone
                for i in range(1, m):
                    holm[i] = max(holm[i], holm[i - 1])
                # zurückschreiben
                adj_vals = np.empty(m)
                adj_vals[idx] = holm
                adj[mask] = adj_vals
            else:
                raise ValueError("adjust must be 'holm' or 'bonferroni'")
            return adj

        adj_t = adjust_pvals(pvals_t, adjust)
        adj_w = adjust_pvals(pvals_w, adjust)

        for r, pt_adj, pw_adj in zip(tmp_rows, adj_t, adj_w):
            r["p_t_adj"] = pt_adj
            r["p_wilcoxon_adj"] = pw_adj
            out_rows.append(r)

    return pd.DataFrame(out_rows)


def main():
    df = load_long_dataframe(JSON_PATH)
    print(f"[INFO] Models: {sorted(df['model'].unique())}")
    print(f"[INFO] Runs used: {sorted(df['run'].unique())}")
    print()

    # Normalität
    norm = normality_tests(df)
    print("=== Shapiro-Wilk Normality (per model x metric) ===")
    print(norm.to_string(index=False))
    print()

    # RM-ANOVA + Friedman
    omnibus = rm_anova_and_friedman(df)
    print("=== Omnibus tests: RM-ANOVA + Friedman ===")
    print(omnibus.to_string(index=False))
    print()

    # Pairwise
    pairs = pairwise_tests(df, adjust="holm")
    # sinnvolle Sortierung: zuerst nach Metrik, dann nach korrigiertem p
    pairs_sorted = pairs.sort_values(["metric", "p_t_adj"], ascending=[True, True])
    print("=== Pairwise tests (paired t-test + Wilcoxon), Holm-adjusted p-values ===")
    print(pairs_sorted.to_string(index=False))
    print()

    # optional: als CSV speichern
    norm.to_csv("normality_shapiro.csv", index=False)
    omnibus.to_csv("omnibus_rm_anova_friedman.csv", index=False)
    pairs_sorted.to_csv("pairwise_tests.csv", index=False)
    print("[INFO] Wrote: normality_shapiro.csv, omnibus_rm_anova_friedman.csv, pairwise_tests.csv")


if __name__ == "__main__":
    main()