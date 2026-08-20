# backend/app/services/analytics/anova.py
"""
One-way ANOVA engine, with Tukey HSD post-hoc pairwise comparisons.

Pure function of (DataFrame, factor, response) -> ANOVAFitResult.
"""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

ALPHA = 0.05


class ANOVAError(ValueError):
    """Raised when the requested ANOVA cannot be computed."""


@dataclass
class TukeyPair:
    group1: str
    group2: str
    mean_diff: float
    p_adj: float
    lower: float
    upper: float
    reject_null: bool


@dataclass
class ANOVAFitResult:
    factor: str
    response: str
    groups: list[str]
    ss_between: float
    ss_within: float
    df_between: int
    df_within: int
    ms_between: float
    ms_within: float
    f_statistic: float
    p_value: float
    eta_squared: float
    significant: bool
    tukey: list[TukeyPair] = field(default_factory=list)
    interpretation: str = ""


def compute_anova(
    df: pd.DataFrame, factor: str, response: str, post_hoc: bool = True
) -> ANOVAFitResult:
    """
    Run a one-way ANOVA of `response` (numeric) across the groups of `factor`
    (categorical), followed by Tukey HSD post-hoc pairwise comparisons when
    there are >=3 groups and the overall F-test is significant.
    """
    if factor not in df.columns or response not in df.columns:
        missing = [c for c in [factor, response] if c not in df.columns]
        raise ANOVAError(f"Colonnes inconnues : {', '.join(missing)}")

    working = df[[factor, response]].copy()
    working[response] = pd.to_numeric(working[response], errors="coerce")
    working = working.dropna()
    working[factor] = working[factor].astype(str)

    groups = sorted(working[factor].unique())
    if len(groups) < 2:
        raise ANOVAError("Le facteur doit comporter au moins 2 groupes distincts.")

    samples = [working.loc[working[factor] == g, response].values for g in groups]
    if any(len(s) < 2 for s in samples):
        raise ANOVAError("Chaque groupe doit contenir au moins 2 observations valides.")

    f_stat, p_value = scipy_stats.f_oneway(*samples)

    grand_mean = working[response].mean()
    ss_between = sum(len(s) * (s.mean() - grand_mean) ** 2 for s in samples)
    ss_within = sum(((s - s.mean()) ** 2).sum() for s in samples)
    ss_total = ss_between + ss_within

    df_between = len(groups) - 1
    df_within = len(working) - len(groups)
    ms_between = ss_between / df_between if df_between > 0 else float("nan")
    ms_within = ss_within / df_within if df_within > 0 else float("nan")
    eta_squared = ss_between / ss_total if ss_total > 0 else 0.0

    significant = bool(p_value < ALPHA)

    tukey_results: list[TukeyPair] = []
    if post_hoc and len(groups) >= 3 and significant:
        tukey = pairwise_tukeyhsd(working[response].values, working[factor].values, alpha=ALPHA)
        for row in tukey.summary().data[1:]:
            group1, group2, mean_diff, p_adj, lower, upper, reject = row
            tukey_results.append(
                TukeyPair(
                    group1=str(group1),
                    group2=str(group2),
                    mean_diff=float(mean_diff),
                    p_adj=float(p_adj),
                    lower=float(lower),
                    upper=float(upper),
                    reject_null=bool(reject),
                )
            )

    if significant:
        interpretation = (
            f"Il existe une différence statistiquement significative de « {response} » entre les groupes "
            f"de « {factor} » (F={f_stat:.3f}, p={p_value:.4f}, η²={eta_squared:.3f}). "
        )
        if tukey_results:
            sig_pairs = [t for t in tukey_results if t.reject_null]
            if sig_pairs:
                pairs_str = ", ".join(f"{t.group1} vs {t.group2}" for t in sig_pairs)
                interpretation += f"Le test post-hoc de Tukey identifie des différences significatives pour : {pairs_str}."
            else:
                interpretation += (
                    "Le test post-hoc de Tukey ne confirme cependant aucune paire de groupes "
                    "significativement différente après correction."
                )
    else:
        interpretation = (
            f"Aucune différence statistiquement significative de « {response} » entre les groupes "
            f"de « {factor} » n'a été détectée (F={f_stat:.3f}, p={p_value:.4f})."
        )

    return ANOVAFitResult(
        factor=factor,
        response=response,
        groups=[str(g) for g in groups],
        ss_between=float(ss_between),
        ss_within=float(ss_within),
        df_between=df_between,
        df_within=df_within,
        ms_between=float(ms_between),
        ms_within=float(ms_within),
        f_statistic=float(f_stat),
        p_value=float(p_value),
        eta_squared=float(eta_squared),
        significant=significant,
        tukey=tukey_results,
        interpretation=interpretation,
    )
