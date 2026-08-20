# backend/app/services/reports/pdf_report.py
"""
Executive PDF report generator (ReportLab).

Pure-ish function: takes already-fetched data as plain dicts (company name,
KPI suite result, validation result, forecast result, top decisions) and
returns the PDF as bytes. No DB/HTTP here, so it's independently testable.
"""
import io
from datetime import datetime, timezone
from typing import Any, Optional

from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PRIORITY_COLORS = {"high": colors.HexColor("#DC2626"), "medium": colors.HexColor("#D97706"), "low": colors.HexColor("#6B7280")}


def _forecast_chart(forecast: dict) -> Optional[Drawing]:
    history = forecast.get("history", {})
    fc = forecast.get("forecast", {})
    actual = [v for v in history.get("actual", []) if v is not None]
    point = fc.get("point", [])
    if not actual or not point:
        return None

    # Downsample history to the last 40 points so the chart stays legible.
    actual_tail = actual[-40:]
    combined = actual_tail + point
    max_v, min_v = max(combined), min(combined)
    padding = (max_v - min_v) * 0.1 or 1

    drawing = Drawing(420, 180)
    chart = HorizontalLineChart()
    chart.x, chart.y = 40, 20
    chart.width, chart.height = 360, 140
    chart.data = [actual_tail + [None] * len(point), [None] * len(actual_tail) + point]
    chart.lines[0].strokeColor = colors.HexColor("#2563EB")
    chart.lines[1].strokeColor = colors.HexColor("#DC2626")
    chart.lines[0].strokeWidth = 1.5
    chart.lines[1].strokeWidth = 1.5
    chart.valueAxis.valueMin = min_v - padding
    chart.valueAxis.valueMax = max_v + padding
    chart.categoryAxis.labels.fontSize = 6
    chart.categoryAxis.visibleTicks = False
    n_points = len(combined)
    chart.categoryAxis.categoryNames = [""] * n_points
    drawing.add(chart)
    return drawing


def build_executive_pdf(
    company_name: str,
    dataset_name: str,
    kpi_result: Optional[dict],
    validation_result: Optional[dict],
    forecast_result: Optional[dict],
    decisions: list,
) -> bytes:
    """Render the executive PDF report and return it as raw bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleFR", parent=styles["Title"], fontSize=20)
    h2 = ParagraphStyle("H2FR", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    body = styles["BodyText"]

    story = []
    story.append(Paragraph(company_name, title_style))
    story.append(Paragraph(f"Rapport exécutif — {dataset_name}", styles["Heading3"]))
    story.append(Paragraph(f"Généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC", body))
    story.append(Spacer(1, 0.5 * cm))

    # --- KPI summary -----------------------------------------------------------
    story.append(Paragraph("Synthèse des indicateurs clés (KPI)", h2))
    if kpi_result and kpi_result.get("kpis"):
        rows = [["Indicateur", "Valeur", "Statut"]]
        for k in kpi_result["kpis"]:
            value_str = f"{k['value']:.2f}" if k.get("value") is not None else "—"
            rows.append([k["kpi_type"].upper(), value_str, "Calculé" if k["status"] == "computed" else "Données insuffisantes"])
        table = Table(rows, colWidths=[6 * cm, 4 * cm, 6 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("Aucun KPI disponible pour ce jeu de données.", body))

    # --- Model validation verdicts ---------------------------------------------
    story.append(Paragraph("Validation du modèle statistique", h2))
    if validation_result:
        rows = [["Test", "Verdict"]]
        for label, key in [
            ("Normalité des résidus", "normality"), ("Hétéroscédasticité", "heteroscedasticity"),
            ("Autocorrélation", "autocorrelation"), ("Multicolinéarité", "multicollinearity"),
            ("Points influents", "influence"),
        ]:
            verdict = (validation_result.get(key) or {}).get("verdict", "—").upper()
            rows.append([label, verdict])
        rows.append(["Verdict global", validation_result.get("overall_verdict", "—").upper()])
        table = Table(rows, colWidths=[10 * cm, 6 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("Aucune validation de modèle disponible pour ce jeu de données.", body))

    # --- Forecast chart ----------------------------------------------------------
    story.append(Paragraph("Prévision de la demande", h2))
    if forecast_result:
        story.append(
            Paragraph(
                f"Modèle recommandé : {forecast_result.get('best_model', '—').upper()} "
                f"(horizon : {forecast_result.get('horizon', '—')} jours).",
                body,
            )
        )
        chart = _forecast_chart(forecast_result)
        if chart:
            story.append(chart)
    else:
        story.append(Paragraph("Aucune prévision disponible pour ce jeu de données.", body))

    # --- Top 5 recommendations -----------------------------------------------------
    story.append(Paragraph("Top 5 des recommandations", h2))
    if decisions:
        for d in decisions[:5]:
            color = PRIORITY_COLORS.get(d.get("priority", "low"), colors.black)
            story.append(
                Paragraph(
                    f'<font color="{color.hexval()}"><b>[{d["priority"].upper()}]</b></font> {d["title"]}',
                    body,
                )
            )
            story.append(Paragraph(d["description"], body))
            story.append(Paragraph(f"<i>Action recommandée :</i> {d['recommended_action']}", body))
            story.append(Spacer(1, 0.3 * cm))
    else:
        story.append(Paragraph("Aucune recommandation disponible pour ce jeu de données.", body))

    doc.build(story)
    return buffer.getvalue()
