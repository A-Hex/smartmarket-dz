# backend/app/services/analytics/kpis.py
"""
KPI Engine.

Computes the business KPI suite from a generic transaction-level dataset.
Since column names vary per uploaded dataset, the caller supplies a column
mapping (KPIRequest). Every KPI is computed defensively: if its required
columns aren't present/valid, it comes back with status="insufficient_data"
and a `missing` list rather than raising, so the suite always returns
something useful (per section 10.7: "Missing inputs must be handled
gracefully").

Persisted KPI types are exactly the 7 values of the fixed `kpi_type` DB enum
(cltv, churn, take_rate, cac, wom, revenue_growth, gross_margin). Average
Order Value and Repeat Purchase Rate are computed too (spec section 10.7,
"Plus:") but returned as `supporting_metrics` rather than persisted `kpis`
rows, since the fixed schema's enum doesn't include them.
"""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class DataCoverage:
    rows_used: int
    rows_total: int
    coverage_ratio: float


@dataclass
class Trend:
    direction: str  # "up" | "down" | "flat"
    change_pct: Optional[float]


@dataclass
class KPIItem:
    kpi_type: str
    status: str  # "computed" | "insufficient_data"
    formula: str
    data_coverage: DataCoverage
    value: Optional[float] = None
    missing: list = field(default_factory=list)
    trend: Optional[Trend] = None
    interpretation: str = ""
    extra: Optional[dict] = None


@dataclass
class SupportingMetric:
    name: str
    formula: str
    status: str
    value: Optional[float] = None


@dataclass
class KPISuiteFitResult:
    kpis: list
    supporting_metrics: list
    interpretation: str = ""


def _coverage(used: int, total: int) -> DataCoverage:
    ratio = (used / total) if total > 0 else 0.0
    return DataCoverage(rows_used=used, rows_total=total, coverage_ratio=ratio)


def _insufficient(kpi_type: str, formula: str, total: int, missing: list) -> KPIItem:
    return KPIItem(
        kpi_type=kpi_type,
        status="insufficient_data",
        formula=formula,
        data_coverage=_coverage(0, total),
        missing=missing,
        interpretation=f"Donnees insuffisantes pour calculer ce KPI. Colonnes manquantes : {', '.join(missing)}.",
    )


def _trend_from_halves(dates: pd.Series, compute_scalar) -> Optional[Trend]:
    """Split rows chronologically in two halves and compare a recomputed scalar."""
    order = dates.sort_values().index
    n = len(order)
    if n < 10:
        return None
    mid = n // 2
    first_half_idx = order[:mid]
    second_half_idx = order[mid:]

    try:
        v1 = compute_scalar(first_half_idx)
        v2 = compute_scalar(second_half_idx)
    except Exception:
        return None

    if v1 is None or v2 is None:
        return None
    if v1 == 0:
        return Trend(direction="flat", change_pct=None)

    change_pct = ((v2 - v1) / abs(v1)) * 100
    direction = "flat" if abs(change_pct) < 1.0 else ("up" if change_pct > 0 else "down")
    return Trend(direction=direction, change_pct=float(change_pct))


def compute_kpi_suite(
    df: pd.DataFrame,
    date_column: Optional[str] = None,
    customer_id_column: Optional[str] = None,
    revenue_column: Optional[str] = None,
    quantity_column: Optional[str] = None,
    price_column: Optional[str] = None,
    cost_column: Optional[str] = None,
    marketing_spend_column: Optional[str] = None,
    fee_column: Optional[str] = None,
    commission_rate: Optional[float] = None,
    nps_column: Optional[str] = None,
) -> KPISuiteFitResult:
    n_total = len(df)

    dates = None
    if date_column and date_column in df.columns:
        dates = pd.to_datetime(df[date_column], errors="coerce")

    revenue = None
    if revenue_column and revenue_column in df.columns:
        revenue = pd.to_numeric(df[revenue_column], errors="coerce")

    customers = df[customer_id_column] if customer_id_column and customer_id_column in df.columns else None

    kpis: list = []

    # --- Average Order Value (supporting metric) ---------------------------
    aov_value = None
    aov_status = "insufficient_data"
    if revenue is not None and revenue.notna().any():
        aov_value = float(revenue.dropna().mean())
        aov_status = "computed"
    supporting: list = [
        SupportingMetric(
            name="average_order_value", formula="moyenne(revenu par commande)",
            status=aov_status, value=aov_value,
        )
    ]

    # --- Repeat Purchase Rate (supporting metric) ---------------------------
    repeat_value = None
    repeat_status = "insufficient_data"
    if customers is not None and customers.notna().any():
        counts = customers.dropna().value_counts()
        repeat_value = float((counts > 1).sum() / len(counts) * 100) if len(counts) > 0 else None
        repeat_status = "computed" if repeat_value is not None else "insufficient_data"
    supporting.append(
        SupportingMetric(
            name="repeat_purchase_rate",
            formula="part des clients avec plus d'une commande (%)",
            status=repeat_status, value=repeat_value,
        )
    )

    # --- CLTV ----------------------------------------------------------------
    if revenue is None or customers is None:
        missing = []
        if revenue is None:
            missing.append("revenue_column")
        if customers is None:
            missing.append("customer_id_column")
        kpis.append(_insufficient("cltv", "AOV x frequence d'achat x duree de vie client", n_total, missing))
    else:
        valid = pd.DataFrame({"customer": customers, "revenue": revenue})
        if dates is not None:
            valid["date"] = dates
        valid = valid.dropna(subset=["customer", "revenue"])

        if valid.empty:
            kpis.append(_insufficient("cltv", "AOV x frequence d'achat x duree de vie client", n_total, ["revenue_column", "customer_id_column"]))
        else:
            n_customers = valid["customer"].nunique()
            n_orders = len(valid)
            aov = valid["revenue"].mean()
            orders_per_customer = n_orders / n_customers if n_customers > 0 else 0.0

            if "date" in valid.columns and valid["date"].notna().any():
                lifespans_days = (
                    valid.dropna(subset=["date"]).groupby("customer")["date"]
                    .agg(lambda s: (s.max() - s.min()).days)
                )
                lifespans_years = (lifespans_days.clip(lower=1) / 365.0)
                avg_lifespan_years = float(lifespans_years.mean())
            else:
                avg_lifespan_years = 1.0

            cltv = float(aov * orders_per_customer * avg_lifespan_years)
            kpis.append(
                KPIItem(
                    kpi_type="cltv",
                    status="computed",
                    value=cltv,
                    formula="Valeur moyenne de commande x commandes/client x duree de vie client (annees)",
                    data_coverage=_coverage(len(valid), n_total),
                    interpretation=(
                        f"CLTV estimee a {cltv:,.2f} par client, basee sur {n_customers} client(s) distincts "
                        f"et {n_orders} commande(s) (AOV={aov:,.2f}, {orders_per_customer:.2f} commandes/client, "
                        f"duree de vie moyenne={avg_lifespan_years:.2f} an(s))."
                    ),
                )
            )

    # --- Churn / Retention (cohort analysis) ----------------------------------
    if dates is None or customers is None:
        missing = []
        if dates is None:
            missing.append("date_column")
        if customers is None:
            missing.append("customer_id_column")
        kpis.append(_insufficient("churn", "1 - taux de retention de la derniere periode observee", n_total, missing))
    else:
        cohort_df = pd.DataFrame({"customer": customers, "date": dates}).dropna()
        if cohort_df.empty:
            kpis.append(_insufficient("churn", "1 - taux de retention de la derniere periode observee", n_total, ["date_column", "customer_id_column"]))
        else:
            cohort_df["period"] = cohort_df["date"].dt.to_period("M")
            first_purchase = cohort_df.groupby("customer")["period"].min().rename("cohort")
            cohort_df = cohort_df.join(first_purchase, on="customer")
            cohort_df["period_index"] = (
                cohort_df["period"].astype("int64") - cohort_df["cohort"].astype("int64")
            )

            cohort_sizes = cohort_df.groupby("cohort")["customer"].nunique()
            retention_table = (
                cohort_df.groupby(["cohort", "period_index"])["customer"].nunique().unstack(fill_value=0)
            )
            retention_pct = retention_table.div(cohort_sizes, axis=0) * 100

            max_period = int(cohort_df["period_index"].max())
            if max_period >= 1 and 1 in retention_pct.columns:
                month1_retention = float(retention_pct[1].mean())
                churn_rate = 100.0 - month1_retention
                cohort_extra = {
                    "cohort_labels": [str(c) for c in retention_pct.index],
                    "retention_matrix": retention_pct.round(1).fillna(0).values.tolist(),
                    "period_indices": [int(c) for c in retention_pct.columns],
                }
                kpis.append(
                    KPIItem(
                        kpi_type="churn",
                        status="computed",
                        value=float(churn_rate),
                        formula="100% - taux de retention moyen a M+1 (analyse de cohortes)",
                        data_coverage=_coverage(len(cohort_df), n_total),
                        interpretation=(
                            f"Taux de churn estime a {churn_rate:.1f}% (retention moyenne a M+1 = "
                            f"{month1_retention:.1f}%), sur {len(cohort_sizes)} cohorte(s) mensuelle(s)."
                        ),
                        extra={"cohort_table": cohort_extra},
                    )
                )
            else:
                kpis.append(
                    _insufficient(
                        "churn", "100% - taux de retention moyen a M+1 (analyse de cohortes)", n_total,
                        ["au moins deux periodes mensuelles distinctes par client"],
                    )
                )

    # --- Take Rate -------------------------------------------------------------
    if commission_rate is not None:
        kpis.append(
            KPIItem(
                kpi_type="take_rate", status="computed", value=float(commission_rate * 100),
                formula="Taux de commission fixe fourni", data_coverage=_coverage(n_total, n_total),
                interpretation=f"Taux de commission configure a {commission_rate * 100:.1f}%.",
            )
        )
    elif fee_column and fee_column in df.columns and revenue is not None:
        fee = pd.to_numeric(df[fee_column], errors="coerce")
        valid_mask = fee.notna() & revenue.notna() & (revenue != 0)
        if valid_mask.any():
            take_rate = float((fee[valid_mask] / revenue[valid_mask]).mean() * 100)
            kpis.append(
                KPIItem(
                    kpi_type="take_rate", status="computed", value=take_rate,
                    formula="moyenne(commission / revenu) x 100",
                    data_coverage=_coverage(int(valid_mask.sum()), n_total),
                    interpretation=f"Taux de commission moyen observe : {take_rate:.2f}%.",
                )
            )
        else:
            kpis.append(_insufficient("take_rate", "moyenne(commission / revenu) x 100", n_total, ["fee_column ou commission_rate"]))
    else:
        kpis.append(_insufficient("take_rate", "moyenne(commission / revenu) x 100", n_total, ["fee_column ou commission_rate"]))

    # --- CAC ---------------------------------------------------------------------
    if marketing_spend_column and marketing_spend_column in df.columns and customers is not None:
        spend = pd.to_numeric(df[marketing_spend_column], errors="coerce")
        total_spend = float(spend.dropna().sum())
        if dates is not None:
            first_purchase_dates = pd.DataFrame({"customer": customers, "date": dates}).dropna().groupby("customer")["date"].min()
            n_new_customers = len(first_purchase_dates)
        else:
            n_new_customers = int(customers.dropna().nunique())

        if n_new_customers > 0:
            cac = total_spend / n_new_customers
            kpis.append(
                KPIItem(
                    kpi_type="cac", status="computed", value=float(cac),
                    formula="depenses marketing totales / nombre de nouveaux clients",
                    data_coverage=_coverage(int(spend.notna().sum()), n_total),
                    interpretation=f"Cout d'acquisition client estime a {cac:,.2f} pour {n_new_customers} client(s).",
                )
            )
        else:
            kpis.append(_insufficient("cac", "depenses marketing totales / nombre de nouveaux clients", n_total, ["customer_id_column"]))
    else:
        missing = []
        if not marketing_spend_column or marketing_spend_column not in df.columns:
            missing.append("marketing_spend_column")
        if customers is None:
            missing.append("customer_id_column")
        kpis.append(_insufficient("cac", "depenses marketing totales / nombre de nouveaux clients", n_total, missing))

    # --- WOM (survey-based proxy) --------------------------------------------
    if nps_column and nps_column in df.columns:
        nps = pd.to_numeric(df[nps_column], errors="coerce")
        if nps.notna().any():
            wom = float(nps.dropna().mean())
            kpis.append(
                KPIItem(
                    kpi_type="wom", status="computed", value=wom,
                    formula="moyenne(score d'enquete / NPS)",
                    data_coverage=_coverage(int(nps.notna().sum()), n_total),
                    interpretation=f"Score de bouche-a-oreille (proxy NPS) moyen : {wom:.1f}.",
                )
            )
        else:
            kpis.append(_insufficient("wom", "moyenne(score d'enquete / NPS)", n_total, ["nps_column (aucune valeur valide)"]))
    else:
        kpis.append(_insufficient("wom", "moyenne(score d'enquete / NPS)", n_total, ["nps_column"]))

    # --- Revenue Growth --------------------------------------------------------
    if dates is not None and revenue is not None:
        rev_df = pd.DataFrame({"date": dates, "revenue": revenue}).dropna()
        if not rev_df.empty:
            monthly = rev_df.groupby(rev_df["date"].dt.to_period("M"))["revenue"].sum().sort_index()
            if len(monthly) >= 2:
                first, last = float(monthly.iloc[0]), float(monthly.iloc[-1])
                growth = ((last - first) / abs(first) * 100) if first != 0 else None
                if growth is not None:
                    kpis.append(
                        KPIItem(
                            kpi_type="revenue_growth", status="computed", value=float(growth),
                            formula="(revenu dernier mois - revenu premier mois) / revenu premier mois x 100",
                            data_coverage=_coverage(len(rev_df), n_total),
                            interpretation=(
                                f"Croissance du revenu de {growth:+.1f}% entre {monthly.index[0]} et {monthly.index[-1]}."
                            ),
                            trend=Trend(direction="up" if growth > 1 else ("down" if growth < -1 else "flat"), change_pct=float(growth)),
                        )
                    )
                else:
                    kpis.append(_insufficient("revenue_growth", "(revenu dernier mois - revenu premier mois) / revenu premier mois x 100", n_total, ["revenu du premier mois non nul"]))
            else:
                kpis.append(_insufficient("revenue_growth", "(revenu dernier mois - revenu premier mois) / revenu premier mois x 100", n_total, ["au moins deux mois distincts"]))
        else:
            kpis.append(_insufficient("revenue_growth", "(revenu dernier mois - revenu premier mois) / revenu premier mois x 100", n_total, ["date_column", "revenue_column"]))
    else:
        missing = []
        if dates is None:
            missing.append("date_column")
        if revenue is None:
            missing.append("revenue_column")
        kpis.append(_insufficient("revenue_growth", "(revenu dernier mois - revenu premier mois) / revenu premier mois x 100", n_total, missing))

    # --- Gross Margin ------------------------------------------------------------
    if revenue is not None and cost_column and cost_column in df.columns:
        cost = pd.to_numeric(df[cost_column], errors="coerce")
        valid_mask = revenue.notna() & cost.notna() & (revenue != 0)
        if valid_mask.any():
            margin = float(((revenue[valid_mask] - cost[valid_mask]) / revenue[valid_mask]).mean() * 100)
            trend = None
            if dates is not None:
                def _scalar(idx):
                    sub_rev, sub_cost = revenue.loc[idx], cost.loc[idx]
                    m = sub_rev.notna() & sub_cost.notna() & (sub_rev != 0)
                    if not m.any():
                        return None
                    return float(((sub_rev[m] - sub_cost[m]) / sub_rev[m]).mean() * 100)
                trend = _trend_from_halves(dates, _scalar)
            kpis.append(
                KPIItem(
                    kpi_type="gross_margin", status="computed", value=margin,
                    formula="moyenne((revenu - cout) / revenu) x 100",
                    data_coverage=_coverage(int(valid_mask.sum()), n_total),
                    interpretation=f"Marge brute moyenne : {margin:.1f}%.",
                    trend=trend,
                )
            )
        else:
            kpis.append(_insufficient("gross_margin", "moyenne((revenu - cout) / revenu) x 100", n_total, ["cost_column avec valeurs valides"]))
    else:
        missing = []
        if revenue is None:
            missing.append("revenue_column")
        if not cost_column or cost_column not in df.columns:
            missing.append("cost_column")
        kpis.append(_insufficient("gross_margin", "moyenne((revenu - cout) / revenu) x 100", n_total, missing))

    n_computed = sum(1 for k in kpis if k.status == "computed")
    overall_interpretation = (
        f"{n_computed} KPI(s) sur {len(kpis)} ont pu etre calcules a partir des colonnes fournies. "
        + (
            "Fournissez les colonnes manquantes pour completer les indicateurs restants."
            if n_computed < len(kpis)
            else "Tous les indicateurs ont pu etre calcules."
        )
    )

    return KPISuiteFitResult(kpis=kpis, supporting_metrics=supporting, interpretation=overall_interpretation)
