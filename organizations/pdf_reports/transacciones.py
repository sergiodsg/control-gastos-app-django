from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _money_style(value, positive_style, negative_style):
    return negative_style if value < 0 else positive_style


def build_transacciones_pdf(org, transactions, filter_label, now, report_totals):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleLarge",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1d4ed8"),
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
    )
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8.4, leading=10)
    amount_pos_style = ParagraphStyle(
        "AmountPos",
        parent=cell_style,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#047857"),
        fontName="Helvetica-Bold",
    )
    amount_neg_style = ParagraphStyle(
        "AmountNeg",
        parent=cell_style,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#b91c1c"),
        fontName="Helvetica-Bold",
    )

    story = [
        Paragraph("Balance General", title_style),
        Spacer(1, 8),
        Paragraph(f"Organizacion: {org.name}", subtitle_style),
        Paragraph(f"Generado el: {now:%d/%m/%Y %H:%M}", subtitle_style),
        Spacer(1, 10),
        Paragraph(f"<b>Filtro aplicado:</b> {filter_label}", styles["Normal"]),
        Spacer(1, 8),
    ]

    table_rows = [
        ["Fecha", "Descripcion", "Referencia", "Monto (BS)", "Tasa", "Monto (USD)", "Notas"]
    ]
    for trans in transactions:
        bs_style = _money_style(trans.amount_bs, amount_pos_style, amount_neg_style)
        usd_style = _money_style(trans.amount_usd, amount_pos_style, amount_neg_style)
        table_rows.append(
            [
                trans.date.strftime("%d/%m/%Y"),
                Paragraph((trans.description or "")[:220], cell_style),
                trans.reference_number or "---",
                Paragraph(f"{trans.amount_bs:.2f}", bs_style),
                f"{trans.daily_rate:.4f}",
                Paragraph(f"{trans.amount_usd:.2f}", usd_style),
                Paragraph((trans.notes or "")[:240], cell_style),
            ]
        )

    table_rows.append(
        [
            "",
            "",
            "BALANCE",
            f"{report_totals['bs']:.2f} Bs.",
            "",
            f"{report_totals['usd']:.2f} $",
            "",
        ]
    )

    col_widths = [2.4 * cm, 7.2 * cm, 2.8 * cm, 3.2 * cm, 2.2 * cm, 3.2 * cm, 6.3 * cm]
    table = Table(table_rows, colWidths=col_widths, repeatRows=1)
    last_row = len(table_rows) - 1
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (3, 1), (5, last_row), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, last_row), (-1, last_row), "Helvetica-Bold"),
                ("BACKGROUND", (0, last_row), (-1, last_row), colors.HexColor("#f8fafc")),
                ("LINEABOVE", (0, last_row), (-1, last_row), 1, colors.HexColor("#94a3b8")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)

    def _footer(canvas, document):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(
            document.pagesize[0] - document.rightMargin,
            0.9 * cm,
            "Reporte generado automaticamente por Control de Gastos",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
