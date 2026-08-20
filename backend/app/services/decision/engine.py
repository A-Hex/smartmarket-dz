# backend/app/services/decision/engine.py
"""
Decision Engine — the product's differentiator.

A rule-based production system: it ingests the JSON results of already-completed
analysis jobs for a dataset (regression, validation, forecast, segmentation, kpi)
and emits prioritized, evidence-backed recommendations. Pure function of
(DecisionContext) -> list[DecisionCandidate]; no DB/HTTP here so every rule is
independently unit-testable, per the testing requirements (section 15).

`confidence` is not a column on the fixed `decisions` table schema (section 8),
so callers should fold it into the persisted `evidence` JSONB (see the API layer).
"""
from dataclasses import dataclass, field
from typing import Any, Optional

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class DecisionCandidate:
    priority: str  # "high" | "medium" | "low"
    category: str
    title: str
    description: str
    evidence: dict
    recommended_action: str
    confidence: str  # "high" | "medium" | "low"


@dataclass
class DecisionContext:
    """Bundles the latest completed job results available for a dataset. Any may be None."""

    regression: Optional[dict] = None
    validation: Optional[dict] = None
    forecast: Optional[dict] = None
    segmentation: Optional[dict] = None
    kpi: Optional[dict] = None


def _validation_confidence(ctx: DecisionContext) -> str:
    """Confidence is downgraded when the underlying model failed validation, per section 11."""
    if ctx.validation is None:
        return "medium"
    verdict = ctx.validation.get("overall_verdict")
    if verdict == "pass":
        return "high"
    if verdict == "fail":
        return "low"
    return "medium"


def _rule_significant_regression_drivers(ctx: DecisionContext) -> list:
    if not ctx.regression:
        return []
    candidates = []
    confidence = _validation_confidence(ctx)
    coefficients = [
        c for c in ctx.regression.get("coefficients", [])
        if c.get("significant") and c.get("term") != "Intercept"
    ]
    coefficients.sort(key=lambda c: abs(c.get("t_stat", 0)), reverse=True)

    for coef in coefficients[:3]:
        direction = "positif" if coef["coefficient"] > 0 else "négatif"
        action_verb = "Augmenter l'investissement dans" if coef["coefficient"] > 0 else "Réévaluer"
        candidates.append(
            DecisionCandidate(
                priority="high" if coef["p_value"] < 0.01 else "medium",
                category="regression",
                title=f"Levier identifié : {coef['term']}",
                description=(
                    f"{coef['term']} a un effet {direction} statistiquement significatif sur la cible "
                    f"(coefficient={coef['coefficient']:.4f}, p={coef['p_value']:.4f})."
                ),
                evidence={
                    "confidence": confidence,
                    "coefficient": coef["coefficient"],
                    "p_value": coef["p_value"],
                    "t_stat": coef.get("t_stat"),
                    "r_squared": ctx.regression.get("r_squared"),
                },
                recommended_action=f"{action_verb} {coef['term']} et suivre son impact sur la cible dans les prochaines périodes.",
                confidence=confidence,
            )
        )
    return candidates


def _rule_validation_remediation(ctx: DecisionContext) -> list:
    if not ctx.validation:
        return []
    candidates = []
    overall = ctx.validation.get("overall_verdict")
    remediation = ctx.validation.get("remediation", [])

    if overall == "fail" and remediation:
        candidates.append(
            DecisionCandidate(
                priority="high",
                category="model_quality",
                title="Le modèle de régression nécessite des corrections",
                description=(
                    "La suite de validation a détecté au moins un problème statistique majeur "
                    "(multicolinéarité, hétéroscédasticité, etc.) qui compromet la fiabilité du modèle."
                ),
                evidence={
                    "confidence": "high",  # high confidence *in the diagnosis itself*
                    "overall_verdict": overall,
                    "multicollinearity_verdict": ctx.validation.get("multicollinearity", {}).get("verdict"),
                    "heteroscedasticity_verdict": ctx.validation.get("heteroscedasticity", {}).get("verdict"),
                },
                recommended_action=" ; ".join(remediation),
                confidence="high",
            )
        )
    return candidates


def _rule_forecast_trend(ctx: DecisionContext) -> list:
    if not ctx.forecast:
        return []
    forecast = ctx.forecast.get("forecast", {})
    points = forecast.get("point", [])
    history = ctx.forecast.get("history", {})
    actual = [v for v in history.get("actual", []) if v is not None]

    if not points or not actual:
        return []

    last_actual = actual[-1]
    last_forecast = points[-1]
    if last_actual == 0:
        return []

    change_pct = (last_forecast - last_actual) / abs(last_actual) * 100
    ci_width = forecast.get("ci_upper_95", [0])[-1] - forecast.get("ci_lower_95", [0])[-1]
    confidence = "high" if ci_width < abs(last_forecast) * 0.5 else "medium"

    if abs(change_pct) < 3:
        return []

    if change_pct > 0:
        title = "Tendance de la demande à la hausse"
        action = (
            "Augmenter les niveaux de stock et anticiper une hausse de la demande sur l'horizon prévu ; "
            "envisager d'ajuster les prix à la hausse si la capacité est limitée."
        )
        priority = "medium"
    else:
        title = "Tendance de la demande à la baisse"
        action = (
            "Réduire les commandes d'approvisionnement et envisager des promotions pour stimuler la demande "
            "avant la baisse anticipée."
        )
        priority = "high"

    return [
        DecisionCandidate(
            priority=priority,
            category="forecast",
            title=title,
            description=(
                f"Le modèle {ctx.forecast.get('best_model', '').upper()} prévoit une variation de "
                f"{change_pct:+.1f}% par rapport à la dernière valeur observée, sur un horizon de "
                f"{ctx.forecast.get('horizon')} jours."
            ),
            evidence={
                "confidence": confidence,
                "change_pct": change_pct,
                "best_model": ctx.forecast.get("best_model"),
                "last_actual": last_actual,
                "last_forecast": last_forecast,
                "ci_width_95": ci_width,
            },
            recommended_action=action,
            confidence=confidence,
        )
    ]


def _rule_high_churn_segment(ctx: DecisionContext) -> list:
    if not ctx.kpi:
        return []
    churn_kpi = next((k for k in ctx.kpi.get("kpis", []) if k.get("kpi_type") == "churn"), None)
    if not churn_kpi or churn_kpi.get("status") != "computed":
        return []

    churn_value = churn_kpi.get("value")
    if churn_value is None or churn_value < 40:
        return []

    target_segment = None
    if ctx.segmentation and ctx.segmentation.get("clusters"):
        # best-effort targeting: the largest cluster is the most impactful to retain
        target_segment = max(ctx.segmentation["clusters"], key=lambda c: c["share"])

    description = f"Le taux de churn estimé est de {churn_value:.1f}%, un niveau élevé."
    action = "Lancer une campagne de rétention ciblée (offres de fidélité, relance personnalisée)."
    if target_segment:
        description += f" Le segment le plus important ({target_segment['name']}, {target_segment['share']:.0%} de la base) est une cible prioritaire."
        action += f" Prioriser le segment « {target_segment['name']} »."

    return [
        DecisionCandidate(
            priority="high" if churn_value > 60 else "medium",
            category="retention",
            title="Taux de churn élevé détecté",
            description=description,
            evidence={
                "confidence": "medium",
                "churn_rate": churn_value,
                "target_segment": target_segment["name"] if target_segment else None,
            },
            recommended_action=action,
            confidence="medium",
        )
    ]


def _rule_low_cltv_segment(ctx: DecisionContext) -> list:
    if not ctx.kpi:
        return []
    cltv_kpi = next((k for k in ctx.kpi.get("kpis", []) if k.get("kpi_type") == "cltv"), None)
    cac_kpi = next((k for k in ctx.kpi.get("kpis", []) if k.get("kpi_type") == "cac"), None)
    if not cltv_kpi or cltv_kpi.get("status") != "computed":
        return []

    cltv_value = cltv_kpi.get("value")
    cac_value = cac_kpi.get("value") if cac_kpi and cac_kpi.get("status") == "computed" else None

    if cac_value is not None and cltv_value is not None and cac_value > cltv_value:
        return [
            DecisionCandidate(
                priority="high",
                category="pricing",
                title="Coût d'acquisition supérieur à la valeur vie client",
                description=(
                    f"Le CAC ({cac_value:,.2f}) dépasse la CLTV estimée ({cltv_value:,.2f}) : "
                    "l'acquisition de nouveaux clients coûte actuellement plus qu'elle ne rapporte."
                ),
                evidence={"confidence": "medium", "cltv": cltv_value, "cac": cac_value},
                recommended_action=(
                    "Revoir la stratégie d'acquisition (canaux, ciblage) et/ou augmenter la valeur par "
                    "client (upsell, rétention) avant d'accroître les dépenses marketing."
                ),
                confidence="medium",
            )
        ]
    return []


def _rule_kpi_anomalies(ctx: DecisionContext) -> list:
    if not ctx.kpi:
        return []
    candidates = []
    kpi_by_type = {k["kpi_type"]: k for k in ctx.kpi.get("kpis", []) if k.get("status") == "computed"}

    margin = kpi_by_type.get("gross_margin")
    if margin and margin.get("value") is not None and margin["value"] < 10:
        candidates.append(
            DecisionCandidate(
                priority="high",
                category="finance",
                title="Marge brute anormalement faible",
                description=f"La marge brute moyenne est de {margin['value']:.1f}%, sous le seuil de viabilité usuel de 10%.",
                evidence={"confidence": "medium", "gross_margin": margin["value"]},
                recommended_action="Revoir la structure de coûts et/ou la politique de prix pour restaurer une marge saine.",
                confidence="medium",
            )
        )

    growth = kpi_by_type.get("revenue_growth")
    if growth and growth.get("value") is not None and growth["value"] < 0:
        candidates.append(
            DecisionCandidate(
                priority="medium",
                category="finance",
                title="Revenu en baisse",
                description=f"Le revenu a diminué de {abs(growth['value']):.1f}% sur la période observée.",
                evidence={"confidence": "medium", "revenue_growth": growth["value"]},
                recommended_action="Analyser les causes de la baisse (mix produit, concurrence, saisonnalité) et ajuster le plan commercial.",
                confidence="medium",
            )
        )

    return candidates


RULES = [
    _rule_significant_regression_drivers,
    _rule_validation_remediation,
    _rule_forecast_trend,
    _rule_high_churn_segment,
    _rule_low_cltv_segment,
    _rule_kpi_anomalies,
]


def generate_decisions(ctx: DecisionContext) -> list:
    """Run every rule against the available context and return decisions sorted by priority."""
    candidates: list = []
    for rule in RULES:
        candidates.extend(rule(ctx))
    candidates.sort(key=lambda c: PRIORITY_ORDER.get(c.priority, 3))
    return candidates
