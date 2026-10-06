from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


INK = colors.HexColor("#173B35")
ACCENT = colors.HexColor("#167C72")
MINT = colors.HexColor("#EAF4F1")
TEXT = colors.HexColor("#263632")
MUTED = colors.HexColor("#64736F")
LINE = colors.HexColor("#D9E4E0")


def euro(value: float) -> str:
    return f"€ {value:,.0f}".replace(",", ".")


def percent(value: float) -> str:
    return f"{value:.2%}".replace(".", ",")


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
        topMargin=38,
        bottomMargin=42,
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
        "section": ParagraphStyle("SectionTitle", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=INK, spaceBefore=7, spaceAfter=4),
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
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
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
        [Paragraph("INDICATIEVE WAARDE", styles["eyebrow"])],
        [Paragraph(f"{euro(result['value_range_low'])} - {euro(result['value_range_high'])}", styles["value"])],
    ], colWidths=[479])
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MINT),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 11),
    ]))

    metric_specs = [
        ("Rendement op totale investering, excl. waardegroei", percent(result["yield_on_total_cost"])),
        ("Rendement op totale investering, incl. waardegroei", percent(result["yield_including_value_growth"])),
        ("Kasstroomrendement op eigen inbreng", percent(result["cash_on_cash_return"])),
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
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    input_expense_label = (
        "Gespecificeerd per kostenpost"
        if inputs["detailed_operating_costs"]
        else f"{percent(inputs['operating_cost_rate'])} van effectieve huur"
    )
    input_rows = [
        ("Verhuurbaar oppervlak", f"{inputs['area_m2']:,.0f} m2", "Markthuur per m2 / jaar", euro(inputs["rent_per_m2"])),
        ("Leegstand en oninbaar", percent(inputs["vacancy_rate"]), "Exploitatiekosten", input_expense_label),
        ("Rendementseis (range)", f"{percent(inputs['yield_rate_range'][0])} - {percent(inputs['yield_rate_range'][1])}", "Centrale rendementseis", percent(inputs["yield_rate"])),
        ("Verwachte waardestijging", percent(inputs["value_growth_rate"]), "Koopprijs", euro(inputs["purchase_price"]) if inputs["purchase_price"] else "Niet opgegeven"),
        ("Overige aankoopkosten", euro(inputs["purchase_costs"]), "Investering / renovatie", euro(inputs["renovation_costs"])),
        ("Overdrachtsbelastingtarief", percent(inputs["transfer_tax_rate"]), "Loan-to-value", percent(inputs["loan_to_value"])),
        ("Financieringsrente", percent(inputs["financing_rate"]), "Aflossingsvorm / looptijd", f"{inputs['repayment_type_label']} / {inputs['loan_term_label']}"),
        ("Financieringskosten", percent(inputs["loan_fee_rate"]), "", ""),
    ]
    output_rows = [
        ("Bruto jaarhuur", euro(result["gross_rent"]), "Effectieve jaarhuur", euro(result["effective_rent"])),
        ("Exploitatiekosten / jaar", euro(result["annual_operating_costs"]), "Netto bedrijfsresultaat (NOI)", euro(result["noi"])),
        ("Indicatieve waarde (range)", f"{euro(result['value_range_low'])} - {euro(result['value_range_high'])}", "Centrale indicatieve waarde", euro(result["value"])),
        ("Aanschafprijs in berekening", euro(result["acquisition_price"]), "Grondslag waardestijging", euro(result["value_growth_basis"])),
        ("Waardestijging / jaar", euro(result["annual_value_growth"]), "Grondslag overdrachtsbelasting", euro(result["transfer_tax_base"])),
        ("Overdrachtsbelasting", euro(result["transfer_tax"]), "Totale investering", euro(result["total_cost"])),
        ("LTV-grondslag", euro(result["financing_basis"]), "Financiering", euro(result["loan_amount"])),
        ("Financieringskosten", euro(result["financing_fees"]), "Rentelasten / jaar", euro(result["interest_cost"])),
        ("Aflossing eerste jaar", euro(result["principal_repayment"]), "Rente- en aflossingslasten / jaar", euro(result["annual_debt_service"])),
        ("Eigen inbreng", euro(result["equity_required"]), "Kasstroom na rente en aflossing / jaar", euro(result["cash_flow_after_debt_service"])),
        ("Kasstroomrendement op eigen inbreng", percent(result["cash_on_cash_return"]), "Rendement excl. waardegroei", percent(result["yield_on_total_cost"])),
        ("Rendement incl. waardegroei", percent(result["yield_including_value_growth"]), "", ""),
    ]

    story = [
        header,
        Spacer(1, 10),
        Paragraph(escape(object_name or "Bedrijfspand"), styles["object"]),
        Paragraph("OBJECTOVERZICHT  |  INDICATIEVE BEREKENING", styles["eyebrow"]),
        Spacer(1, 6),
        hero,
        Spacer(1, 6),
        Paragraph("Kernuitkomsten (berekend)", styles["section"]),
        metrics,
        Paragraph("Overige berekende uitkomsten", styles["section"]),
        detail_table(output_rows),
        Paragraph("Invoer en aannames", styles["section"]),
        detail_table(input_rows),
        Spacer(1, 6),
        Paragraph(
            "De overige uitkomsten gebruiken de centrale rendementseis (het midden van de range). "
            "Deze indicatieve berekening gebruikt uitsluitend de hierboven vermelde invoer. "
            "De standaardwaarden zijn voorbeeld-aannames en geen marktdata. Controleer de "
            "marktgegevens, fiscale grondslag, toepasselijke regels en financieringsvoorwaarden "
            "voordat je dit rapport voor een transactie gebruikt. Verwachte waardestijging is "
            "onzeker, geen kasstroom en geen gegarandeerd rendement.",
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