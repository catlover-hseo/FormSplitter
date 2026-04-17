from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

try:
    from .constants import BRANDING_TEXT, PDF_SUFFIX, SCORE_LABELS
except ImportError:
    from constants import BRANDING_TEXT, PDF_SUFFIX, SCORE_LABELS


def register_pdf_fonts() -> None:
    font_candidates = ("HYGothic-Medium", "HYSMyeongJo-Medium")
    registered = set(pdfmetrics.getRegisteredFontNames())
    for font_name in font_candidates:
        if font_name not in registered:
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))


def build_pdf_styles() -> dict[str, ParagraphStyle]:
    register_pdf_fonts()
    base_styles = getSampleStyleSheet()

    return {
        "brand": ParagraphStyle(
            "brand",
            parent=base_styles["Normal"],
            fontName="HYGothic-Medium",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#7A5C46"),
            alignment=TA_CENTER,
        ),
        "title": ParagraphStyle(
            "title",
            parent=base_styles["Title"],
            fontName="HYSMyeongJo-Medium",
            fontSize=22,
            leading=28,
            textColor=colors.HexColor("#241913"),
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base_styles["Normal"],
            fontName="HYGothic-Medium",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#7F6757"),
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "section",
            parent=base_styles["Heading2"],
            fontName="HYGothic-Medium",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#412D21"),
            alignment=TA_LEFT,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base_styles["Normal"],
            fontName="HYGothic-Medium",
            fontSize=10.5,
            leading=16,
            textColor=colors.HexColor("#2C211B"),
            alignment=TA_LEFT,
        ),
        "feedback": ParagraphStyle(
            "feedback",
            parent=base_styles["Normal"],
            fontName="HYGothic-Medium",
            fontSize=10.3,
            leading=16,
            leftIndent=2,
            textColor=colors.HexColor("#2C211B"),
            alignment=TA_LEFT,
        ),
    }


def create_pdf_document(
    performer_name: str, averages: list[float | None], feedbacks: list[str], event_date_label: str
) -> bytes:
    styles = build_pdf_styles()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=performer_name,
        author="ADEO / ADeoOfficial",
    )

    story = [
        Paragraph(escape(BRANDING_TEXT), styles["brand"]),
        Spacer(1, 6),
        Paragraph(escape(performer_name), styles["title"]),
        Paragraph(
            escape(f"학내연주 {PDF_SUFFIX} | 학내일자 {event_date_label}"),
            styles["subtitle"],
        ),
        Spacer(1, 14),
    ]

    info_table = Table(
        [
            ["대상자", performer_name],
            ["문서 구분", PDF_SUFFIX],
            ["학내일자", event_date_label],
        ],
        colWidths=[35 * mm, 125 * mm],
        hAlign="LEFT",
    )
    info_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEE4D6")),
                ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#FBF8F3")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2B201A")),
                ("FONTNAME", (0, 0), (-1, -1), "HYGothic-Medium"),
                ("FONTSIZE", (0, 0), (-1, -1), 10.2),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CDBAA4")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDCEBE")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([info_table, Spacer(1, 14)])

    score_rows = [["평가 항목", "평균 점수"]]
    for label, value in zip(SCORE_LABELS, averages):
        score_rows.append([label, f"{value:.2f}" if value is not None else "평가 없음"])

    story.append(Paragraph("항목별 평균 점수", styles["section"]))
    score_table = Table(score_rows, colWidths=[105 * mm, 55 * mm], hAlign="LEFT")
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B6513A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFDFC")),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#241913")),
                ("FONTNAME", (0, 0), (-1, -1), "HYGothic-Medium"),
                ("FONTSIZE", (0, 0), (-1, -1), 10.5),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CDBAA4")),
                ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#E0D3C5")),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend(
        [score_table, Spacer(1, 12), HRFlowable(color=colors.HexColor("#D9C8B8")), Spacer(1, 10)]
    )

    story.append(Paragraph("익명 피드백 취합", styles["section"]))
    if feedbacks:
        feedback_items = [
            ListItem(
                Paragraph(escape(feedback).replace("\n", "<br/>"), styles["feedback"])
            )
            for feedback in feedbacks
        ]
        story.append(
            ListFlowable(
                feedback_items,
                bulletType="bullet",
                start="circle",
                bulletFontName="HYGothic-Medium",
                bulletFontSize=10,
                leftPadding=14,
            )
        )
    else:
        story.append(Paragraph("수집된 피드백이 없습니다.", styles["body"]))

    story.extend([Spacer(1, 14), HRFlowable(color=colors.HexColor("#D9C8B8")), Spacer(1, 6)])
    story.append(Paragraph("이 문서는 내부 공유 및 학생 전달용으로 자동 생성되었습니다.", styles["brand"]))

    document.build(story)
    buffer.seek(0)
    return buffer.getvalue()
