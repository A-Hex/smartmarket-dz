# backend/app/services/analytics/validation.py
"""
Model Validation suite.

Runs the mandatory six-test diagnostic package on a fitted OLS model (never
report R² alone, per the product spec):
1. Normality of residuals   - Shapiro-Wilk + Jarque-Bera + QQ-plot points
2. Heteroscedasticity       - Breusch-Pagan AND White test
3. Autocorrelation          - Durbin-Watson statistic + zone
4. Multicollinearity        - VIF per feature (WARN >5, FAIL >10)
5. Influence                - Cook's distance, flagged observations
6. Residual-vs-fitted + residual histogram data, for frontend plots

Every test returns {statistic, p_value, threshold, verdict, meaning}. Pure
function of (DataFrame, regression config) -> ValidationSuiteResult: it refits
the model itself (the fitted statsmodels object isn't persisted), reusing the
exact same design-matrix prep as the Regression engine so the diagnostics are
computed against the identical data the coefficients were estimated on.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from statsmodels.stats.diagnostic import het_breuschpagan, het_white
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson

from app.services.analytics.regression import RegressionError, fit_ols_model

Verdict = str  # "pass" | "warn" | "fail"


class ValidationError(ValueError):
    """Raised when the validation suite cannot be run (e.g. bad model config)."""


@dataclass
class TestResult:
    statistic: float
    p_value: Optional[float]
    threshold: str
    verdict: Verdict
    meaning: str


@dataclass
class VIFResult:
    feature: str
    vif: float
    verdict: Verdict


@dataclass
class MulticollinearityResult:
    vif: list[VIFResult]
    verdict: Verdict
    meaning: str


@dataclass
class InfluenceResult:
    threshold: float
    influential_count: int
    influential_ratio: float
    influential_indices: list[int]
    verdict: Verdict
    meaning: str


@dataclass
class ValidationSuiteResult:
    normality: TestResult
    qq_plot: dict
    heteroscedasticity: TestResult
    autocorrelation: TestResult
    multicollinearity: MulticollinearityResult
    influence: InfluenceResult
    residual_vs_fitted: dict
    residual_histogram: dict
    overall_verdict: Verdict
    remediation: list[str] = field(default_factory=list)


def _verdict_from_p(p_value: float, warn_below: float = 0.05, fail_below: float = 0.01) -> Verdict:
    """Lower p-values -> stronger evidence against the null -> worse verdict."""
    if p_value < fail_below:
        return "fail"
    if p_value < warn_below:
        return "warn"
    return "pass"


def _worst(*verdicts: Verdict) -> Verdict:
    order = {"pass": 0, "warn": 1, "fail": 2}
    return max(verdicts, key=lambda v: order[v])


def _normality_test(residuals: np.ndarray) -> tuple[TestResult, dict]:
    shapiro_stat, shapiro_p = scipy_stats.shapiro(residuals)
    jb_stat, jb_p = scipy_stats.jarque_bera(residuals)[:2]

    combined_p = min(float(shapiro_p), float(jb_p))
    verdict = _verdict_from_p(combined_p)

    meaning = (
        f"Shapiro-Wilk (W={shapiro_stat:.4f}, p={shapiro_p:.4f}) et Jarque-Bera "
        f"(JB={jb_stat:.4f}, p={jb_p:.4f}) testent la normalité des résidus. "
    )
    if verdict == "pass":
        meaning += "Les résidus suivent une distribution approximativement normale."
    elif verdict == "warn":
        meaning += "Écart modéré à la normalité des résidus, à surveiller."
    else:
        meaning += (
            "Écart significatif à la normalité des résidus : les p-values et intervalles de "
            "confiance du modèle peuvent être peu fiables."
        )

    theoretical, sample = scipy_stats.probplot(residuals, dist="norm")[0]
    qq_plot = {"theoretical": [float(x) for x in theoretical], "sample": [float(x) for x in sample]}

    return TestResult(
        statistic=float(shapiro_stat), p_value=combined_p, threshold="p >= 0.05",
        verdict=verdict, meaning=meaning,
    ), qq_plot


def _heteroscedasticity_test(residuals: np.ndarray, exog: pd.DataFrame) -> TestResult:
    bp_stat, bp_p, _, _ = het_breuschpagan(residuals, exog)
    try:
        white_stat, white_p, _, _ = het_white(residuals, exog)
    except Exception:
        white_stat, white_p = bp_stat, bp_p

    combined_p = min(float(bp_p), float(white_p))
    verdict = _verdict_from_p(combined_p)

    meaning = (
        f"Breusch-Pagan (p={bp_p:.4f}) et White (p={white_p:.4f}) testent l'homoscédasticité. "
    )
    if verdict == "pass":
        meaning += "Aucune hétéroscédasticité détectée."
    elif verdict == "warn":
        meaning += "Hétéroscédasticité modérée, envisager des erreurs-types robustes (HC)."
    else:
        meaning += (
            "Hétéroscédasticité significative détectée : les erreurs-types classiques sont "
            "probablement sous-estimées. Utiliser des erreurs-types robustes (HC) ou transformer la cible."
        )

    return TestResult(
        statistic=float(bp_stat), p_value=combined_p, threshold="p >= 0.05",
        verdict=verdict, meaning=meaning,
    )


def _autocorrelation_test(residuals: np.ndarray) -> TestResult:
    dw = float(durbin_watson(residuals))

    if 1.5 <= dw <= 2.5:
        verdict, zone = "pass", "aucune autocorrélation notable"
    elif 1.0 <= dw < 1.5 or 2.5 < dw <= 3.0:
        verdict = "warn"
        zone = "autocorrélation légère " + ("positive" if dw < 1.5 else "négative")
    else:
        verdict = "fail"
        zone = "autocorrélation marquée " + ("positive" if dw < 1.0 else "négative")

    meaning = (
        f"Durbin-Watson = {dw:.3f} ({zone}). Zone de référence : 0-1.5 = autocorrélation positive, "
        f"~2 = aucune, 2.5-4 = autocorrélation négative."
    )
    if verdict == "fail":
        meaning += " Envisager d'ajouter une variable retardée (lag) ou un modèle de séries temporelles."

    return TestResult(
        statistic=dw, p_value=None, threshold="1.5 <= DW <= 2.5", verdict=verdict, meaning=meaning,
    )


def _clean_term_name(term: str) -> str:
    """Strip patsy's Q('col') quoting wrapper for readable display names."""
    return re.sub(r"Q\('([^']+)'\)", r"\1", term)


def _multicollinearity_test(exog: pd.DataFrame) -> MulticollinearityResult:
    vif_results: list[VIFResult] = []
    exog_values = exog.values
    for i, col in enumerate(exog.columns):
        if col == "Intercept":
            continue
        try:
            vif = float(variance_inflation_factor(exog_values, i))
        except Exception:
            vif = float("inf")
        if vif > 10:
            v_verdict = "fail"
        elif vif > 5:
            v_verdict = "warn"
        else:
            v_verdict = "pass"
        vif_results.append(VIFResult(feature=_clean_term_name(col), vif=vif, verdict=v_verdict))

    overall = _worst(*(v.verdict for v in vif_results)) if vif_results else "pass"
    failing = [v.feature for v in vif_results if v.verdict == "fail"]
    warning = [v.feature for v in vif_results if v.verdict == "warn"]

    if overall == "pass":
        meaning = "Aucun problème de multicolinéarité : tous les VIF sont inférieurs à 5."
    elif overall == "warn":
        meaning = f"Multicolinéarité modérée détectée pour : {', '.join(warning)} (5 < VIF <= 10)."
    else:
        meaning = (
            f"Multicolinéarité sévère détectée pour : {', '.join(failing)} (VIF > 10). "
            "Envisager de retirer une des variables corrélées ou d'utiliser une régression régularisée."
        )

    return MulticollinearityResult(vif=vif_results, verdict=overall, meaning=meaning)


def _influence_test(fitted) -> InfluenceResult:
    influence = fitted.get_influence()
    cooks_d, _ = influence.cooks_distance
    n = len(cooks_d)
    threshold = 4.0 / n if n > 0 else float("inf")

    influential_mask = cooks_d > threshold
    influential_indices = [int(i) for i in np.where(influential_mask)[0]]
    influential_count = len(influential_indices)
    ratio = influential_count / n if n > 0 else 0.0

    if influential_count == 0:
        verdict = "pass"
    elif ratio <= 0.10:
        verdict = "warn"
    else:
        verdict = "fail"

    meaning = (
        f"{influential_count} observation(s) sur {n} dépassent le seuil de distance de Cook "
        f"(4/n = {threshold:.4f}), soit {ratio:.1%}. "
    )
    if verdict == "pass":
        meaning += "Aucune observation n'exerce une influence disproportionnée sur le modèle."
    elif verdict == "warn":
        meaning += "Quelques observations influentes, à examiner individuellement."
    else:
        meaning += "Une part importante des observations sont influentes, vérifier les valeurs extrêmes."

    return InfluenceResult(
        threshold=float(threshold), influential_count=influential_count,
        influential_ratio=float(ratio), influential_indices=influential_indices,
        verdict=verdict, meaning=meaning,
    )


def run_validation_suite(
    df: pd.DataFrame,
    target: str,
    features: list[str],
    log_target: bool = False,
    interactions: Optional[list[list[str]]] = None,
) -> ValidationSuiteResult:
    """Refit the given regression config and run the full six-test diagnostic suite."""
    try:
        fitted, formula, n_obs = fit_ols_model(df, target, features, log_target, interactions)
    except RegressionError as exc:
        raise ValidationError(str(exc)) from exc

    residuals = np.asarray(fitted.resid)
    fitted_values = np.asarray(fitted.fittedvalues)
    exog_names = fitted.model.exog_names
    exog_df = pd.DataFrame(fitted.model.exog, columns=exog_names)

    normality, qq_plot = _normality_test(residuals)
    heteroscedasticity = _heteroscedasticity_test(residuals, exog_df)
    autocorrelation = _autocorrelation_test(residuals)
    multicollinearity = _multicollinearity_test(exog_df)
    influence = _influence_test(fitted)

    counts, bin_edges = np.histogram(residuals, bins=20)
    residual_histogram = {
        "bin_edges": [float(x) for x in bin_edges],
        "counts": [int(x) for x in counts],
    }
    residual_vs_fitted = {
        "fitted": [float(x) for x in fitted_values],
        "residuals": [float(x) for x in residuals],
    }

    overall_verdict = _worst(
        normality.verdict, heteroscedasticity.verdict, autocorrelation.verdict,
        multicollinearity.verdict, influence.verdict,
    )

    remediation: list[str] = []
    if normality.verdict == "fail":
        remediation.append(
            "Envisager une transformation (log, Box-Cox) de la variable cible pour améliorer la normalité des résidus."
        )
    if heteroscedasticity.verdict == "fail":
        remediation.append(
            "Utiliser des erreurs-types robustes (HC) ou transformer la variable cible pour corriger l'hétéroscédasticité."
        )
    if autocorrelation.verdict == "fail":
        remediation.append("Ajouter une variable retardée (lag) ou passer à un modèle de séries temporelles adapté.")
    if multicollinearity.verdict == "fail":
        failing_features = [v.feature for v in multicollinearity.vif if v.verdict == "fail"]
        remediation.append(
            f"Retirer ou combiner les variables fortement corrélées ({', '.join(failing_features)}) "
            "pour réduire la multicolinéarité."
        )
    if influence.verdict == "fail":
        remediation.append("Examiner et, si justifié, retirer les observations très influentes (distance de Cook).")

    return ValidationSuiteResult(
        normality=normality,
        qq_plot=qq_plot,
        heteroscedasticity=heteroscedasticity,
        autocorrelation=autocorrelation,
        multicollinearity=multicollinearity,
        influence=influence,
        residual_vs_fitted=residual_vs_fitted,
        residual_histogram=residual_histogram,
        overall_verdict=overall_verdict,
        remediation=remediation,
    )
