# backend/app/services/analytics/descriptive.py
"""
Descriptive Statistics engine.

Pure function of (DataFrame, columns filter) -> DescriptiveResult. No DB/HTTP
concerns, independently unit-testable. Every finding ships with a plain-French
`interpretation` string, per the product requirement that results are always
explained, not just displayed.
"""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


@dataclass
class NumericStats:
    column: str
    count: int
    missing: int
    mean: Optional[float]
    median: Optional[float]
    mode: Optional[float]
    variance: Optional[float]
    std: Optional[float]
    skewness: Optional[float]
    kurtosis: Optional[float]
    q1: Optional[float]
    q3: Optional[float]
    iqr: Optional[float]
    min: Optional[float]
    max: Optional[float]
    interpretation: str


@dataclass
class CategoricalStats:
    column: str
    count: int
    missing: int
    unique: int
    frequency_table: dict
    interpretation: str


@dataclass
class Correlation:
    columns: list[str]
    pearson: list[list[Optional[float]]]
    spearman: list[list[Optional[float]]]


@dataclass
class DescriptiveResult:
    row_count: int
    numeric_columns: list[NumericStats] = field(default_factory=list)
    categorical_columns: list[CategoricalStats] = field(default_factory=list)
    correlation: Optional[Correlation] = None
    target_candidates: list[str] = field(default_factory=list)
    missingness_summary: dict = field(default_factory=dict)


def _skew_interpretation(skew: Optional[float]) -> str:
    if skew is None or np.isnan(skew):
        return "Asymétrie non calculable."
    if skew > 1:
        return "Distribution fortement asymétrique à droite (quelques valeurs élevées tirent la moyenne vers le haut)."
    if skew > 0.5:
        return "Distribution modérément asymétrique à droite."
    if skew < -1:
        return "Distribution fortement asymétrique à gauche."
    if skew < -0.5:
        return "Distribution modérément asymétrique à gauche."
    return "Distribution approximativement symétrique."


def _numeric_column_stats(series: pd.Series, name: str) -> NumericStats:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    missing = int(numeric.isna().sum())
    count = int(valid.count())

    if count == 0:
        return NumericStats(
            column=name, count=0, missing=missing, mean=None, median=None, mode=None,
            variance=None, std=None, skewness=None, kurtosis=None, q1=None, q3=None,
            iqr=None, min=None, max=None,
            interpretation="Aucune donnée numérique valide pour cette colonne.",
        )

    mean = float(valid.mean())
    median = float(valid.median())
    mode_series = valid.mode()
    mode = float(mode_series.iloc[0]) if not mode_series.empty else None
    variance = float(valid.var()) if count > 1 else 0.0
    std = float(valid.std()) if count > 1 else 0.0
    skew = float(scipy_stats.skew(valid)) if count > 2 else None
    kurt = float(scipy_stats.kurtosis(valid)) if count > 2 else None
    q1 = float(valid.quantile(0.25))
    q3 = float(valid.quantile(0.75))
    iqr = q3 - q1
    vmin = float(valid.min())
    vmax = float(valid.max())

    missing_ratio = missing / len(numeric) if len(numeric) else 0
    interpretation = (
        f"Moyenne de {mean:.2f}, médiane de {median:.2f}. {_skew_interpretation(skew)} "
        f"{missing:d} valeur(s) manquante(s) ({missing_ratio:.1%})."
    )

    return NumericStats(
        column=name, count=count, missing=missing, mean=mean, median=median, mode=mode,
        variance=variance, std=std, skewness=skew, kurtosis=kurt, q1=q1, q3=q3, iqr=iqr,
        min=vmin, max=vmax, interpretation=interpretation,
    )


def _categorical_column_stats(series: pd.Series, name: str) -> CategoricalStats:
    missing = int(series.isna().sum())
    count = int(series.notna().sum())
    value_counts = series.value_counts(dropna=True)
    unique = int(value_counts.shape[0])
    freq_table = {str(k): int(v) for k, v in value_counts.items()}

    top_label = "N/A"
    top_share = 0.0
    if not value_counts.empty and count > 0:
        top_label = str(value_counts.index[0])
        top_share = float(value_counts.iloc[0]) / count

    interpretation = (
        f"{unique} valeur(s) unique(s). Catégorie la plus fréquente : « {top_label} » "
        f"({top_share:.1%} des observations non manquantes)."
    )

    return CategoricalStats(
        column=name, count=count, missing=missing, unique=unique,
        frequency_table=freq_table, interpretation=interpretation,
    )


def compute_descriptive_stats(
    df: pd.DataFrame, columns: Optional[list[str]] = None
) -> DescriptiveResult:
    """
    Compute full descriptive statistics for the given columns (or all columns
    if none specified): per-column stats, frequency tables, correlation
    matrices (Pearson + Spearman) over numeric columns, missingness summary,
    and numeric target-variable candidates.
    """
    target_df = df[columns] if columns else df
    row_count = len(target_df)

    numeric_stats: list[NumericStats] = []
    categorical_stats: list[CategoricalStats] = []
    missingness: dict = {}

    numeric_col_names: list[str] = []

    for col in target_df.columns:
        series = target_df[col]
        missingness[str(col)] = int(series.isna().sum())

        if pd.api.types.is_numeric_dtype(series):
            numeric_stats.append(_numeric_column_stats(series, str(col)))
            numeric_col_names.append(str(col))
        else:
            # Attempt numeric coercion for object columns that are "numeric-like"
            coerced = pd.to_numeric(series, errors="coerce")
            if coerced.notna().sum() >= max(2, int(0.5 * series.notna().sum())):
                numeric_stats.append(_numeric_column_stats(series, str(col)))
                numeric_col_names.append(str(col))
            else:
                categorical_stats.append(_categorical_column_stats(series, str(col)))

    correlation: Optional[Correlation] = None
    if len(numeric_col_names) >= 2:
        numeric_df = target_df[numeric_col_names].apply(pd.to_numeric, errors="coerce")
        pearson_df = numeric_df.corr(method="pearson")
        spearman_df = numeric_df.corr(method="spearman")

        def _matrix(corr_df: pd.DataFrame) -> list[list[Optional[float]]]:
            return [
                [None if pd.isna(v) else float(v) for v in row]
                for row in corr_df.values
            ]

        correlation = Correlation(
            columns=numeric_col_names,
            pearson=_matrix(pearson_df),
            spearman=_matrix(spearman_df),
        )

    target_candidates = [
        s.column
        for s in numeric_stats
        if s.count > 0
        and row_count > 0
        and (s.missing / row_count) <= 0.10
        and s.std is not None
        and s.std > 0
    ]

    return DescriptiveResult(
        row_count=row_count,
        numeric_columns=numeric_stats,
        categorical_columns=categorical_stats,
        correlation=correlation,
        target_candidates=target_candidates,
        missingness_summary=missingness,
    )
