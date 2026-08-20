# backend/app/services/analytics/panel_data.py
"""
Panel Data econometrics — interface stub (out of MVP scope per section 4.2).

Defines the typed contract for a future panel-data module (fixed-effects,
random-effects, difference-in-differences) built on `linearmodels` or
`statsmodels`, so it can plug into the existing analytics pipeline
(dataset -> config -> typed, JSON-serializable result) without touching
API routers, job orchestration, or the Decision Engine.

Panel data requires an (entity, time) index — e.g. (store_id, month) or
(customer_id, week) — which the current MVP's cross-sectional regression
(services/analytics/regression.py) does not model.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

import pandas as pd

PanelModelType = Literal["fixed_effects", "random_effects", "pooled_ols", "difference_in_differences"]


@dataclass
class PanelCoefficient:
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
class PanelFitResult:
    model_type: PanelModelType
    entity_column: str
    time_column: str
    formula: str
    n_observations: int
    n_entities: int
    n_periods: int
    r_squared_within: Optional[float] = None
    r_squared_between: Optional[float] = None
    r_squared_overall: Optional[float] = None
    coefficients: list[PanelCoefficient] = field(default_factory=list)
    hausman_test: Optional[dict[str, float]] = None  # fixed vs. random effects specification test
    interpretation: str = ""


class PanelDataService(ABC):
    """
    Abstract contract for a future panel-data regression implementation.

    A concrete implementation would wrap `linearmodels.PanelOLS` /
    `RandomEffects`, run a Hausman test to recommend fixed vs. random
    effects, and translate results into the typed objects above.
    """

    @abstractmethod
    def fit(
        self,
        df: pd.DataFrame,
        entity_column: str,
        time_column: str,
        target: str,
        features: list[str],
        model_type: PanelModelType = "fixed_effects",
    ) -> PanelFitResult:
        """
        Fit a panel-data model and return coefficient estimates plus a
        specification test (Hausman) recommending fixed vs. random effects
        when both were considered.

        Args:
            df: input dataset containing repeated observations per entity over time.
            entity_column: column identifying the cross-sectional unit (e.g. store, customer).
            time_column: column identifying the time period.
            target: response column.
            features: predictor columns.
            model_type: which panel estimator to use.

        Returns:
            PanelFitResult, JSON-serializable for `analysis_jobs.result`.
        """
        raise NotImplementedError

    @abstractmethod
    def difference_in_differences(
        self,
        df: pd.DataFrame,
        entity_column: str,
        time_column: str,
        target: str,
        treatment_column: str,
        post_period_column: str,
    ) -> PanelFitResult:
        """
        Estimate a difference-in-differences treatment effect (e.g. impact of
        a marketing campaign launched in specific regions at a specific time).

        Args:
            treatment_column: binary indicator, 1 for treated entities.
            post_period_column: binary indicator, 1 for post-treatment periods.

        Returns:
            PanelFitResult whose `coefficients` includes the
            treatment x post interaction term as the DiD estimate.
        """
        raise NotImplementedError
