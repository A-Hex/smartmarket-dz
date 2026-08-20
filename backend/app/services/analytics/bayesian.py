# backend/app/services/analytics/bayesian.py
"""
Bayesian modeling — interface stub (out of MVP scope per section 4.2).

This module defines the typed contract that a future Bayesian regression
module (e.g. via `pymc` or `statsmodels`' Bayesian estimators) must implement
so it can be plugged into the existing analytics pipeline without touching
API routers, job orchestration, or the Decision Engine's rule interface.

The intended workflow mirrors `services/analytics/regression.py`:
    (DataFrame, target, features, prior config) -> BayesianFitResult
returning posterior summaries (mean, credible intervals) per coefficient
instead of frequentist point estimates + p-values, plus convergence
diagnostics (R-hat, effective sample size) in place of the OLS validation suite.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd


@dataclass
class PriorSpec:
    """Prior distribution specification for one coefficient."""

    distribution: str  # e.g. "normal", "student_t", "cauchy"
    params: dict[str, float]  # e.g. {"mu": 0.0, "sigma": 10.0}


@dataclass
class PosteriorCoefficient:
    """Posterior summary for a single coefficient, replacing the OLS point estimate + p-value."""

    term: str
    posterior_mean: float
    posterior_std: float
    credible_interval_lower: float  # e.g. 94% HDI lower bound
    credible_interval_upper: float
    probability_of_direction: float  # P(coefficient > 0) or < 0, whichever is larger
    interpretation: str


@dataclass
class ConvergenceDiagnostics:
    """MCMC sampler convergence diagnostics (replaces the OLS Model Validation suite)."""

    r_hat_max: float  # should be close to 1.0; >1.01 signals non-convergence
    effective_sample_size_min: int
    divergences: int
    verdict: str  # "converged" | "warn" | "failed"


@dataclass
class BayesianFitResult:
    formula: str
    n_observations: int
    coefficients: list[PosteriorCoefficient] = field(default_factory=list)
    convergence: Optional[ConvergenceDiagnostics] = None
    interpretation: str = ""


class BayesianRegressionService(ABC):
    """
    Abstract contract for a future Bayesian regression implementation.

    A concrete implementation (e.g. `PyMCBayesianRegressionService`) would
    wrap `pymc.Model` + NUTS sampling and translate the trace into the typed
    result objects above, keeping the API/job/decision layers unchanged.
    """

    @abstractmethod
    def fit(
        self,
        df: pd.DataFrame,
        target: str,
        features: list[str],
        priors: Optional[dict[str, PriorSpec]] = None,
        draws: int = 2000,
        chains: int = 4,
    ) -> BayesianFitResult:
        """
        Fit a Bayesian linear model and return posterior summaries.

        Args:
            df: input dataset.
            target: name of the response column.
            features: names of predictor columns.
            priors: optional per-coefficient prior overrides; unspecified
                terms fall back to a weakly-informative default (e.g. Normal(0, 10)).
            draws: number of posterior samples to draw per chain.
            chains: number of independent MCMC chains (for R-hat computation).

        Returns:
            BayesianFitResult with posterior coefficient summaries and
            convergence diagnostics, JSON-serializable for `analysis_jobs.result`.
        """
        raise NotImplementedError
