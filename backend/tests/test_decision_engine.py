# backend/tests/test_decision_engine.py
"""Unit tests for app.services.decision.engine (pure rule functions)."""
from app.services.decision.engine import DecisionContext, generate_decisions


def test_no_context_yields_no_decisions():
    ctx = DecisionContext()
    assert generate_decisions(ctx) == []


def test_significant_regression_driver_produces_decision():
    ctx = DecisionContext(
        regression={
            "r_squared": 0.85,
            "coefficients": [
                {"term": "Intercept", "coefficient": 10.0, "p_value": 0.5, "significant": False, "t_stat": 1.0},
                {"term": "marketing_spend", "coefficient": 3.2, "p_value": 0.001, "significant": True, "t_stat": 8.5},
            ],
        }
    )
    decisions = generate_decisions(ctx)
    assert len(decisions) == 1
    assert decisions[0].category == "regression"
    assert "marketing_spend" in decisions[0].title
    assert decisions[0].priority == "high"  # p < 0.01
    assert decisions[0].evidence["p_value"] == 0.001


def test_validation_fail_produces_high_priority_remediation():
    ctx = DecisionContext(
        validation={
            "overall_verdict": "fail",
            "remediation": ["Supprimer une variable corrélée", "Utiliser des erreurs standards robustes"],
            "multicollinearity": {"verdict": "fail"},
            "heteroscedasticity": {"verdict": "pass"},
        }
    )
    decisions = generate_decisions(ctx)
    assert len(decisions) == 1
    assert decisions[0].category == "model_quality"
    assert decisions[0].priority == "high"
    assert decisions[0].confidence == "high"


def test_validation_pass_produces_no_remediation_decision():
    ctx = DecisionContext(validation={"overall_verdict": "pass", "remediation": []})
    decisions = generate_decisions(ctx)
    assert decisions == []


def test_forecast_upward_trend_produces_medium_priority_decision():
    ctx = DecisionContext(
        forecast={
            "best_model": "ets",
            "horizon": 14,
            "history": {"actual": [100, 105, 110, 115, 120]},
            "forecast": {
                "point": [130, 140, 150],
                "ci_lower_95": [120, 125, 130],
                "ci_upper_95": [140, 155, 170],
            },
        }
    )
    decisions = generate_decisions(ctx)
    assert len(decisions) == 1
    assert decisions[0].category == "forecast"
    assert "hausse" in decisions[0].title.lower()


def test_forecast_downward_trend_is_high_priority():
    ctx = DecisionContext(
        forecast={
            "best_model": "arima",
            "horizon": 14,
            "history": {"actual": [200, 190, 180, 170, 160]},
            "forecast": {
                "point": [100, 90, 80],
                "ci_lower_95": [70, 60, 50],
                "ci_upper_95": [130, 120, 110],
            },
        }
    )
    decisions = generate_decisions(ctx)
    assert len(decisions) == 1
    assert decisions[0].priority == "high"
    assert "baisse" in decisions[0].title.lower()


def test_high_churn_triggers_retention_decision_with_segment_targeting():
    ctx = DecisionContext(
        kpi={"kpis": [{"kpi_type": "churn", "status": "computed", "value": 65.0}]},
        segmentation={
            "clusters": [
                {"cluster": 0, "name": "Segment A", "share": 0.6, "size": 60},
                {"cluster": 1, "name": "Segment B", "share": 0.4, "size": 40},
            ]
        },
    )
    decisions = generate_decisions(ctx)
    assert len(decisions) == 1
    assert decisions[0].category == "retention"
    assert decisions[0].priority == "high"  # > 60
    assert "Segment A" in decisions[0].recommended_action


def test_low_churn_does_not_trigger_retention_decision():
    ctx = DecisionContext(kpi={"kpis": [{"kpi_type": "churn", "status": "computed", "value": 10.0}]})
    assert generate_decisions(ctx) == []


def test_cac_exceeds_cltv_triggers_pricing_decision():
    ctx = DecisionContext(
        kpi={
            "kpis": [
                {"kpi_type": "cltv", "status": "computed", "value": 100.0},
                {"kpi_type": "cac", "status": "computed", "value": 250.0},
            ]
        }
    )
    decisions = generate_decisions(ctx)
    assert len(decisions) == 1
    assert decisions[0].category == "pricing"
    assert decisions[0].priority == "high"


def test_low_gross_margin_triggers_finance_alert():
    ctx = DecisionContext(kpi={"kpis": [{"kpi_type": "gross_margin", "status": "computed", "value": 5.0}]})
    decisions = generate_decisions(ctx)
    assert any(d.category == "finance" for d in decisions)


def test_decisions_sorted_by_priority():
    ctx = DecisionContext(
        kpi={
            "kpis": [
                {"kpi_type": "gross_margin", "status": "computed", "value": 5.0},  # high
                {"kpi_type": "revenue_growth", "status": "computed", "value": -10.0},  # medium
                {"kpi_type": "churn", "status": "computed", "value": 45.0},  # medium
            ]
        }
    )
    decisions = generate_decisions(ctx)
    priorities = [d.priority for d in decisions]
    assert priorities == sorted(priorities, key=lambda p: {"high": 0, "medium": 1, "low": 2}[p])
