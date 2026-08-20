# backend/app/services/analytics/regression.py
"""
OLS Regression engine.

Pure function of (DataFrame, target, features, options) -> RegressionFitResult.
Fits via statsmodels.formula.api.ols using a patsy formula, so features are
selected the same way the frontend UI presents them (raw column names).
Every coefficient ships with a plain-French `interpretation` string.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ALPHA = 0.05


class RegressionError(ValueError):
    """Raised when the requested regression cannot be fit (bad columns, singular design, etc.)."""


@dataclass
class CoefficientFit:
    term: str
    coefficient: float
    std_error: float
    t_stat: float
    p_value: float
    ci_lower: float
    ci_upper: float
    significant: bool
    interpretation: str


@dataclass
class RegressionFitResult:
    formula: str
    n_observations: int
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_p_value: float
    aic: float
    bic: float
    coefficients: list[CoefficientFit] = field(default_factory=list)
    interpretation: str = ""
    # the fitted statsmodels object is intentionally NOT returned here (not JSON-serializable);
    # callers needing residuals/influence for the Model Validation suite (Phase 6) should refit
    # via `fit_ols_model` directly.


def _quote(col: str) -> str:
    """Wrap a column name in patsy's Q() so spaces/special chars/reserved words are safe."""
    return f"Q('{col}')"


def build_formula(
    target: str,
    features: list[str],
    log_target: bool = False,
    interactions: Optional[list[list[str]]] = None,
) -> str:
    """Build a patsy formula string, quoting every identifier for safety."""
    lhs = f"np.log1p({_quote(target)})" if log_target else _quote(target)
    terms = [_quote(f) for f in features]
    for pair in interactions or []:
        if len(pair) != 2:
            raise RegressionError("Each interaction must reference exactly two feature names.")
        terms.append(f"{_quote(pair[0])}:{_quote(pair[1])}")
    rhs = " + ".join(terms) if terms else "1"
    return f"{lhs} ~ {rhs}"


def prepare_regression_data(
    df: pd.DataFrame, target: str, features: list[str], log_target: bool = False
) -> pd.DataFrame:
    """
    Shared data-prep step: select target+features, coerce to numeric, drop rows
    with any missing values. Raises RegressionError on invalid input. Reused by
    both `fit_ols_model` (Phase 5) and the Model Validation suite (Phase 6) so
    both operate on the exact same design matrix.
    """
    missing = [c for c in [target, *features] if c not in df.columns]
    if missing:
        raise RegressionError(f"Colonnes inconnues : {', '.join(missing)}")

    working = df[[target, *features]].apply(pd.to_numeric, errors="coerce")
    working = working.dropna()
    if len(working) < len(features) + 2:
        raise RegressionError(
            "Pas assez d'observations valides (non manquantes et numériques) pour ajuster ce modèle."
        )
    if log_target and (working[target] < 0).any():
        raise RegressionError("log(target) impossible : la variable cible contient des valeurs négatives.")

    return working


def fit_ols_model(df: pd.DataFrame, target: str, features: list[str],
                   log_target: bool = False, interactions: Optional[list[list[str]]] = None):
    """
    Fit the OLS model and return the raw statsmodels results object (for reuse by
    the Model Validation suite, which needs residuals/leverage/influence, not just
    the summary table).
    """
    working = prepare_regression_data(df, target, features, log_target)

    formula = build_formula(target, features, log_target, interactions)
    try:
        model = smf.ols(formula=formula, data=working)
        fitted = model.fit()
    except Exception as exc:
        raise RegressionError(f"Échec de l'ajustement du modèle : {exc}") from exc

    return fitted, formula, len(working)


def _term_interpretation(term: str, coef: float, p_value: float) -> str:
    if term == "Intercept":
        return f"Constante du modèle : {coef:.4f}."
    clean_term = re.sub(r"Q\('([^']+)'\)", r"\1", term)
    if p_value < ALPHA:
        direction = "positif" if coef > 0 else "négatif"
        return (
            f"{clean_term} a un effet {direction} statistiquement significatif "
            f"sur la cible (coefficient={coef:.4f}, p={p_value:.4f})."
        )
    return (
        f"{clean_term} n'a pas d'effet statistiquement significatif sur la cible "
        f"(coefficient={coef:.4f}, p={p_value:.4f})."
    )


def compute_regression(
    df: pd.DataFrame,
    target: str,
    features: list[str],
    log_target: bool = False,
    interactions: Optional[list[list[str]]] = None,
) -> RegressionFitResult:
    """Fit an OLS model and return a fully-interpreted, JSON-serializable result."""
    fitted, formula, n_obs = fit_ols_model(df, target, features, log_target, interactions)

    conf_int = fitted.conf_int(alpha=ALPHA)
    coefficients: list[CoefficientFit] = []
    for term in fitted.params.index:
        p_value = float(fitted.pvalues[term])
        coef = float(fitted.params[term])
        coefficients.append(
            CoefficientFit(
                term=term,
                coefficient=coef,
                std_error=float(fitted.bse[term]),
                t_stat=float(fitted.tvalues[term]),
                p_value=p_value,
                ci_lower=float(conf_int.loc[term, 0]),
                ci_upper=float(conf_int.loc[term, 1]),
                significant=p_value < ALPHA,
                interpretation=_term_interpretation(term, coef, p_value),
            )
        )

    n_significant = sum(1 for c in coefficients if c.significant and c.term != "Intercept")
    overall_interpretation = (
        f"Le modèle explique {fitted.rsquared:.1%} de la variance de la cible "
        f"(R²={fitted.rsquared:.3f}, R² ajusté={fitted.rsquared_adj:.3f}). "
        f"{n_significant} variable(s) sur {len(features)} ont un effet statistiquement significatif "
        f"au seuil de 5%. Test F global : p={fitted.f_pvalue:.4f}"
        f"{' (le modèle est globalement significatif).' if fitted.f_pvalue < ALPHA else ' (le modèle n’est pas globalement significatif).'}"
    )

    return RegressionFitResult(
        formula=formula,
        n_observations=n_obs,
        r_squared=float(fitted.rsquared),
        adj_r_squared=float(fitted.rsquared_adj),
        f_statistic=float(fitted.fvalue) if fitted.fvalue is not None else float("nan"),
        f_p_value=float(fitted.f_pvalue) if fitted.f_pvalue is not None else float("nan"),
        aic=float(fitted.aic),
        bic=float(fitted.bic),
        coefficients=coefficients,
        interpretation=overall_interpretation,
    )
