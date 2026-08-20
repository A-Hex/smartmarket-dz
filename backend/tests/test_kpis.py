# backend/tests/test_kpis.py
"""Unit tests for app.services.analytics.kpis (pure functions)."""
import numpy as np
import pandas as pd

from app.services.analytics.kpis import compute_kpi_suite


def _make_transactions(n_customers=50, orders_per_customer=3, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    base_date = pd.Timestamp("2024-01-01")
    for cust in range(n_customers):
        n_orders = rng.integers(1, orders_per_customer + 1)
        for _ in range(n_orders):
            rows.append(
                {
                    "customer_id": f"C{cust}",
                    "date": base_date + pd.Timedelta(days=int(rng.integers(0, 300))),
                    "revenue": float(rng.uniform(50, 500)),
                    "cost": float(rng.uniform(20, 300)),
                    "marketing_spend": float(rng.uniform(1, 20)),
                    "nps": float(rng.integers(-100, 100)),
                }
            )
    return pd.DataFrame(rows)


def test_all_kpis_computed_when_all_columns_present():
    df = _make_transactions()
    result = compute_kpi_suite(
        df, date_column="date", customer_id_column="customer_id",
        revenue_column="revenue", cost_column="cost",
        marketing_spend_column="marketing_spend", nps_column="nps",
    )
    statuses = {k.kpi_type: k.status for k in result.kpis}
    # take_rate has no fee_column/commission_rate supplied -> insufficient by design
    assert statuses["take_rate"] == "insufficient_data"
    for kpi_type in ["cltv", "churn", "cac", "wom", "revenue_growth", "gross_margin"]:
        assert statuses[kpi_type] == "computed", f"{kpi_type} should be computed"


def test_missing_columns_yield_insufficient_data_not_crash():
    df = pd.DataFrame({"x": [1, 2, 3]})
    result = compute_kpi_suite(df)  # no column mapping at all
    assert len(result.kpis) == 7
    assert all(k.status == "insufficient_data" for k in result.kpis)
    assert all(k.missing for k in result.kpis)


def test_cltv_value_is_positive_and_reasonable():
    df = _make_transactions()
    result = compute_kpi_suite(
        df, date_column="date", customer_id_column="customer_id", revenue_column="revenue"
    )
    cltv = next(k for k in result.kpis if k.kpi_type == "cltv")
    assert cltv.status == "computed"
    assert cltv.value > 0


def test_take_rate_with_flat_commission_rate():
    df = _make_transactions()
    result = compute_kpi_suite(df, commission_rate=0.15)
    take_rate = next(k for k in result.kpis if k.kpi_type == "take_rate")
    assert take_rate.status == "computed"
    assert abs(take_rate.value - 15.0) < 1e-6


def test_gross_margin_computation():
    df = pd.DataFrame({"revenue": [100.0, 200.0, 300.0], "cost": [60.0, 100.0, 150.0]})
    result = compute_kpi_suite(df, revenue_column="revenue", cost_column="cost")
    margin = next(k for k in result.kpis if k.kpi_type == "gross_margin")
    assert margin.status == "computed"
    assert margin.value > 0


def test_supporting_metrics_present():
    df = _make_transactions()
    result = compute_kpi_suite(df, customer_id_column="customer_id", revenue_column="revenue")
    names = {m.name for m in result.supporting_metrics}
    assert names == {"average_order_value", "repeat_purchase_rate"}
    for m in result.supporting_metrics:
        assert m.status == "computed"
        assert m.value is not None


def test_churn_cohort_table_present_when_computed():
    df = _make_transactions(n_customers=80, orders_per_customer=4, seed=7)
    result = compute_kpi_suite(df, date_column="date", customer_id_column="customer_id")
    churn = next(k for k in result.kpis if k.kpi_type == "churn")
    if churn.status == "computed":
        assert churn.extra is not None
        assert "cohort_table" in churn.extra
