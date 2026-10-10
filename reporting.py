from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


INK = colors.HexColor("#173B35")
ACCENT = colors.HexColor("#167C72")
AMBER = colors.HexColor("#D98E04")
SLATE = colors.HexColor("#4C6EF5")
MINT = colors.HexColor("#EAF4F1")
TEXT = colors.HexColor("#263632")
MUTED = colors.HexColor("#64736F")
LINE = colors.HexColor("#D9E4E0")


def euro(value: float) -> str:
    return f"€ {value:,.0f}".replace(",", ".")


def percent(value: float) -> str:
    return f"{value:.2%}".replace(".", ",")


TOTAL_COST_NOTE = (
    "De waarden zijn de koopprijs. De kosten koper (overdrachtsbelasting en overige aankoopkosten) "
    "komen daar nog bovenop en zitten wel in de totale investering, samen met renovatie en "
    "eventuele financieringskosten."
)


def spread_positions(positions: list[float], min_gap: float, lo: float, hi: float) -> list[float]:
    """Zet labelmiddens minstens min_gap uit elkaar binnen [lo, hi]; volgorde blijft die van de invoer."""
    order = sorted(range(len(positions)), key=lambda index: positions[index])
    placed = [min(max(positions[index], lo), hi) for index in order]
    for index in range(1, len(placed)):
        placed[index] = max(placed[index], placed[index - 1] + min_gap)
    if placed:
        placed[-1] = min(placed[-1], hi)
    for index in range(len(placed) - 2, -1, -1):
        placed[index] = min(placed[index], placed[index + 1] - min_gap)
    result = [0.0] * len(positions)
    for slot, index in enumerate(order):
        result[index] = placed[slot]
    return result


def price_range(
    *,
    low: float,
    central: float,
    high: float,
    purchase_price: float,
    total_cost: float,
) -> dict[str, Any]:
    specs: list[tuple[str, str, float]] = [("central", "Centrale waarde", central)]
    if purchase_price > 0:
        specs.append(("purchase", "Koopprijs", purchase_price))
    if total_cost > 0:
        specs.append(("total", "Totale investering", total_cost))

    values = [low, high, *(value for _, _, value in specs)]
    value_min, value_max = min(values), max(values)
    span = (value_max - value_min) or max(abs(value_max), 1.0)
    scale_min = value_min - span * 0.08
    scale_max = value_max + span * 0.08

    def position(value: float) -> float:
        return (value - scale_min) / (scale_max - scale_min)

    markers = [
        {"key": key, "label": label, "value": value, "position": position(value)}
        for key, label, value in specs
    ]

    if purchase_price <= 0:
        verdict = "Geen koopprijs ingevuld; de aanschafprijs is gelijk aan de centrale waarde."
    elif purchase_price < low:
        verdict = "De koopprijs ligt onder de indicatieve waardeband."
    elif purchase_price > high:
        verdict = "De koopprijs ligt boven de indicatieve waardeband."
    else:
        verdict = "De koopprijs ligt binnen de indicatieve waardeband."

    return {
        "low": low,
        "high": high,
        "low_position": position(low),
        "high_position": position(high),
        "markers": markers,
        "verdict": verdict,
    }


MARKER_COLORS = {"central": ACCENT, "purchase": AMBER, "total": SLATE}


def marker_shape(key: str, x: float, y: float, size: float):
    color = MARKER_COLORS[key]
    style = {"fillColor": color, "strokeColor": colors.white, "strokeWidth": 1.2}
    half = size / 2
    if key == "central":
        return Polygon([x, y + half + 1, x + half + 1, y, x, y - half - 1, x - half - 1, y], **style)
    if key == "purchase":
        return Circle(x, y, half, **style)
    return Rect(x - half, y - half, size, size, **style)


def price_range_drawing(info: dict, width: float = 479, height: float = 90) -> Drawing:
    drawing = Drawing(width, height)
    x_min, x_max = 46.0, width - 46.0
    axis_y, band_height, marker_size = 48.0, 12.0, 9.0

    def x_at(position: float) -> float:
        return x_min + position * (x_max - x_min)

    drawing.add(Line(x_min - 12, axis_y, x_max + 12, axis_y, strokeColor=LINE, strokeWidth=1))
    band_left, band_right = x_at(info["low_position"]), x_at(info["high_position"])
    drawing.add(Rect(band_left, axis_y - band_height / 2, max(band_right - band_left, 2), band_height,
                     fillColor=MINT, strokeColor=ACCENT, strokeWidth=0.8))

    top_x = spread_positions([band_left, band_right], 62, x_min, x_max)
    for text_x, caption, value in zip(top_x, ("Laag", "Hoog"), (info["low"], info["high"])):
        drawing.add(String(text_x, 82, caption, fontName="Helvetica", fontSize=6.5, fillColor=MUTED, textAnchor="middle"))
        drawing.add(String(text_x, 72, euro(value), fontName="Helvetica-Bold", fontSize=7.5, fillColor=TEXT, textAnchor="middle"))

    markers = info["markers"]
    label_x = spread_positions([x_at(m["position"]) for m in markers], 80, x_min, x_max)
    for marker, text_x in zip(markers, label_x):
        color = MARKER_COLORS[marker["key"]]
        marker_x = x_at(marker["position"])
        drawing.add(Line(marker_x, axis_y - marker_size / 2 - 1, text_x, 34, strokeColor=color, strokeWidth=0.5))
        drawing.add(marker_shape(marker["key"], marker_x, axis_y, marker_size))
        name_width = stringWidth(marker["label"], "Helvetica", 6.5)
        drawing.add(String(text_x + 4, 24, marker["label"], fontName="Helvetica", fontSize=6.5, fillColor=color, textAnchor="middle"))
        drawing.add(marker_shape(marker["key"], text_x + 4 - name_width / 2 - 6, 26, 5))
        drawing.add(String(text_x, 13, euro(marker["value"]), fontName="Helvetica-Bold", fontSize=7.5, fillColor=TEXT, textAnchor="middle"))
    return drawing


def report_pdf(
    object_name: str,
    report_date: str,
    inputs: dict[str, Any],
    result: dict[str, float],
) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=30,
        bottomMargin=34,
        title=f"Indicatieve waardering - {object_name}",
        author="Bedrijfspand berekening",
    )
    sample = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("ReportTitle", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.white, alignment=TA_LEFT),
        "date": ParagraphStyle("ReportDate", parent=sample["Normal"], fontSize=9, leading=12, textColor=colors.white, alignment=TA_RIGHT),
        "object": ParagraphStyle("ObjectName", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=19, leading=22, textColor=INK, spaceAfter=3),
        "eyebrow": ParagraphStyle("Eyebrow", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=ACCENT),
        "value": ParagraphStyle("HeroValue", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=INK),
        "metric_label": ParagraphStyle("MetricLabel", parent=sample["Normal"], fontSize=8, leading=10, textColor=MUTED),
        "metric_value": ParagraphStyle("MetricValue", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=TEXT),
        "section": ParagraphStyle("SectionTitle", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=INK, spaceBefore=4, spaceAfter=2),
        "label": ParagraphStyle("TableLabel", parent=sample["Normal"], fontSize=8, leading=10, textColor=MUTED),
        "cell_value": ParagraphStyle("TableValue", parent=sample["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=TEXT),
        "note": ParagraphStyle("ReportNote", parent=sample["Normal"], fontSize=7.5, leading=10, textColor=MUTED),
    }

    def detail_table(rows: list[tuple[str, str, str, str]]) -> Table:
        data = []
        for label_a, value_a, label_b, value_b in rows:
            data.append([
                Paragraph(escape(label_a), styles["label"]),
                Paragraph(escape(value_a), styles["cell_value"]),
                Paragraph(escape(label_b), styles["label"]),
                Paragraph(escape(value_b), styles["cell_value"]),
            ])
        table = Table(data, colWidths=[112, 115, 112, 130], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ("LINEBELOW", (0, 0), (-1, -1), 0.35, LINE),
        ]))
        return table

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(doc.leftMargin, 28, A4[0] - doc.rightMargin, 28)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(doc.leftMargin, 16, "Indicatief rapport op basis van ingevoerde aannames")
        canvas.drawRightString(A4[0] - doc.rightMargin, 16, f"Pagina {doc.page}")
        canvas.restoreState()

    header = Table(
        [[Paragraph("BEDRIJFSPAND / WAARDERING", styles["title"]), Paragraph(escape(report_date), styles["date"])]],
        colWidths=[365, 114],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), INK),
        ("BOX", (0, 0), (-1, -1), 0, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 15),
        ("RIGHTPADDING", (0, 0), (-1, -1), 15),
        ("TOPPADDING", (0, 0), (-1, -1), 13),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    hero = Table([
        [Paragraph("INDICATIEVE WAARDE", ParagraphStyle("HeroEyebrow", parent=styles["eyebrow"], alignment=TA_CENTER))],
        [Paragraph(f"{euro(result['value_range_low'])} - {euro(result['value_range_high'])}", ParagraphStyle("HeroAmount", parent=styles["value"], alignment=TA_CENTER))],
    ], colWidths=[479])
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MINT),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 11),
    ]))

    metric_specs = [
        ("Rendement op totale investering", percent(result["yield_on_total_cost"])),
        ("Kasstroom na rente en aflossing / jaar", euro(result["cash_flow_after_debt_service"])),
    ]
    metric_data = []
    for index in range(0, len(metric_specs), 2):
        metric_data.append([
            [Paragraph(escape(label), styles["metric_label"]), Paragraph(escape(value), styles["metric_value"])]
            for label, value in metric_specs[index:index + 2]
        ])
    metrics = Table(metric_data, colWidths=[239.5, 239.5])
    metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    input_expense_label = (
        "Gespecificeerd per kostenpost"
        if inputs["detailed_operating_costs"]
        else f"{percent(inputs['operating_cost_rate'])} van effectieve huur"
    )
    input_rows = [
        ("Verhuurbaar oppervlak", f"{inputs['area_m2']:,.0f} m2", "Markthuur per m2 / jaar", euro(inputs["rent_per_m2"])),
        ("Leegstand en oninbaar", percent(inputs["vacancy_rate"]), "Exploitatiekosten", input_expense_label),
        ("NAR-range", f"{percent(inputs['yield_rate_range'][0])} - {percent(inputs['yield_rate_range'][1])}", "Centrale NAR", percent(inputs["yield_rate"])),
        ("Type vastgoed", inputs.get("property_type", ""), "Koopprijs", euro(inputs["purchase_price"]) if inputs["purchase_price"] else "Niet opgegeven"),
        ("Overige aankoopkosten", euro(inputs["purchase_costs"]), "Investering / renovatie", euro(inputs["renovation_costs"])),
        ("Overdrachtsbelastingtarief", percent(inputs["transfer_tax_rate"]), "Loan-to-value", percent(inputs["loan_to_value"])),
        ("Financieringsrente", percent(inputs["financing_rate"]), "Aflossingsvorm / looptijd", f"{inputs['repayment_type_label']} / {inputs['loan_term_label']}"),
        ("Financieringskosten", percent(inputs["loan_fee_rate"]), "", ""),
    ]
    output_rows = [
        ("Bruto jaarhuur", euro(result["gross_rent"]), "Effectieve jaarhuur", euro(result["effective_rent"])),
        ("Exploitatiekosten / jaar", euro(result["annual_operating_costs"]), "Netto bedrijfsresultaat (NOI)", euro(result["noi"])),
        ("Indicatieve waarde (range)", f"{euro(result['value_range_low'])} - {euro(result['value_range_high'])}", "Centrale indicatieve waarde", euro(result["value"])),
        ("Aanschafprijs in berekening", euro(result["acquisition_price"]), "Grondslag overdrachtsbelasting", euro(result["transfer_tax_base"])),
        ("Overdrachtsbelasting", euro(result["transfer_tax"]), "Totale investering", euro(result["total_cost"])),
        ("LTV-grondslag", euro(result["financing_basis"]), "Financiering", euro(result["loan_amount"])),
        ("Financieringskosten", euro(result["financing_fees"]), "Rentelasten / jaar", euro(result["interest_cost"])),
        ("Aflossing eerste jaar", euro(result["principal_repayment"]), "Rente- en aflossingslasten / jaar", euro(result["annual_debt_service"])),
        ("Eigen inbreng", euro(result["equity_required"]), "Kasstroom na rente en aflossing / jaar", euro(result["cash_flow_after_debt_service"])),
        ("Rendement op totale investering", percent(result["yield_on_total_cost"]), "", ""),
    ]

    range_info = price_range(
        low=result["value_range_low"],
        central=result["value"],
        high=result["value_range_high"],
        purchase_price=inputs["purchase_price"],
        total_cost=result["total_cost"],
    )

    story = [
        header,
        Spacer(1, 10),
        Paragraph(escape(object_name or "Bedrijfspand"), styles["object"]),
        Paragraph("OBJECTOVERZICHT  |  INDICATIEVE BEREKENING", styles["eyebrow"]),
        Spacer(1, 6),
        hero,
        Spacer(1, 6),
        Paragraph("Waardeband en positie", styles["section"]),
        price_range_drawing(range_info),
        Paragraph(f"{escape(range_info['verdict'])} {escape(TOTAL_COST_NOTE)}", styles["note"]),
        Spacer(1, 4),
        Paragraph("Kernuitkomsten (berekend)", styles["section"]),
        metrics,
        Paragraph("Overige berekende uitkomsten", styles["section"]),
        detail_table(output_rows),
        Paragraph("Invoer en aannames", styles["section"]),
        detail_table(input_rows),
        Spacer(1, 6),
        Paragraph(
            "De overige uitkomsten gebruiken de centrale NAR (het midden van de range voor het gekozen "
            "type vastgoed). Deze indicatieve berekening gebruikt "
            "uitsluitend de hierboven vermelde invoer. "
            "De NAR-ranges en overige standaardwaarden zijn voorbeeld-aannames en geen gepubliceerde marktdata. "
            "Controleer de marktgegevens, fiscale grondslag, toepasselijke regels en financieringsvoorwaarden "
            "voordat je dit rapport voor een transactie gebruikt.",
            styles["note"],
        ),
    ]
    if inputs["detailed_operating_costs"]:
        expense_items = list(inputs["operating_cost_items"].items())
        expense_rows = []
        for index in range(0, len(expense_items), 2):
            label_a, amount_a = expense_items[index]
            if index + 1 < len(expense_items):
                label_b, amount_b = expense_items[index + 1]
            else:
                label_b, amount_b = "", 0
            expense_rows.append((label_a, euro(amount_a), label_b, euro(amount_b) if label_b else ""))
        story.extend([
            Paragraph("Uitsplitsing exploitatiekosten per jaar", styles["section"]),
            detail_table(expense_rows),
        ])

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()