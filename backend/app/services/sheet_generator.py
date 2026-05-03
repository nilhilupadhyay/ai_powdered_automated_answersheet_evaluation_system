"""
Answer-sheet PDF generator using **reportlab** (pure-Python, no system deps).

Produces an A4 PDF containing:
  • Header with exam title
  • Exam / Session metadata
  • Roll-number box (optional)
  • Numbered answer boxes for each question
  • QR code with sheet-session metadata at the bottom
"""

import base64
import io
import logging
from typing import Tuple

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

# ── colour palette ──────────────────────────────────────────────────────────
CLR_PRIMARY   = HexColor("#1a1a2e")
CLR_ACCENT    = HexColor("#16213e")
CLR_BORDER    = HexColor("#bbbbbb")
CLR_LIGHT_BG  = HexColor("#f5f5f5")
CLR_TEXT       = HexColor("#222222")
CLR_MUTED     = HexColor("#666666")

PAGE_W, PAGE_H = A4  # 595.27 × 841.89 pt
MARGIN = 30 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


# ── QR helper ───────────────────────────────────────────────────────────────

def create_qr_base64(payload: str) -> str:
    """Return a base-64 encoded PNG of a QR code encoding *payload*."""
    image = qrcode.make(payload)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _qr_image_reader(payload: str) -> ImageReader:
    """Return a reportlab-compatible ImageReader for the QR code."""
    image = qrcode.make(payload)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


# ── Drawing helpers ─────────────────────────────────────────────────────────

def _draw_header(c: canvas.Canvas, y: float, exam_id: str, sheet_session_id: str) -> float:
    """Draw the title and exam metadata.  Returns updated *y* position."""
    # Title
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(CLR_PRIMARY)
    c.drawString(MARGIN, y, "Answer Sheet")
    y -= 22

    # Decorative line
    c.setStrokeColor(CLR_ACCENT)
    c.setLineWidth(1.5)
    c.line(MARGIN, y, MARGIN + CONTENT_W, y)
    y -= 18

    # Metadata
    c.setFont("Helvetica", 10)
    c.setFillColor(CLR_TEXT)
    c.drawString(MARGIN, y, f"Exam ID: {exam_id}")
    c.drawString(MARGIN + CONTENT_W / 2, y, f"Session: {sheet_session_id}")
    y -= 20
    return y


def _draw_roll_number_box(c: canvas.Canvas, y: float) -> float:
    """Draw a roll-number entry box.  Returns updated *y*."""
    box_w = 260
    box_h = 28
    c.setStrokeColor(CLR_PRIMARY)
    c.setLineWidth(0.8)
    c.rect(MARGIN, y - box_h, box_w, box_h)
    c.setFont("Helvetica", 11)
    c.setFillColor(CLR_TEXT)
    c.drawString(MARGIN + 8, y - box_h + 8, "Roll Number: ____________________________")
    y -= box_h + 14
    return y


def _draw_question_box(c: canvas.Canvas, y: float, q_no: int) -> float:
    """Draw a single question answer box.  Returns updated *y*."""
    box_h = 54
    # Check page break
    if y - box_h < MARGIN + 100:
        c.showPage()
        y = PAGE_H - MARGIN

    c.setStrokeColor(CLR_BORDER)
    c.setLineWidth(0.6)
    # Rounded rectangle
    c.roundRect(MARGIN, y - box_h, CONTENT_W, box_h, 6, stroke=1, fill=0)

    # Question number label
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(CLR_TEXT)
    c.drawString(MARGIN + 8, y - 16, f"Q{q_no}.")

    # Hint text
    c.setFont("Helvetica", 8)
    c.setFillColor(CLR_MUTED)
    c.drawString(MARGIN + 8, y - box_h + 8, "Write your answer in this box.")

    y -= box_h + 8
    return y


def _draw_qr_section(c: canvas.Canvas, y: float, qr_payload: str) -> float:
    """Draw the QR code and scan-ID footer.  Returns updated *y*."""
    qr_size = 90
    # Ensure room — new page if needed
    if y - qr_size - 30 < MARGIN:
        c.showPage()
        y = PAGE_H - MARGIN

    # Dashed separator
    c.setStrokeColor(CLR_MUTED)
    c.setLineWidth(0.5)
    c.setDash(4, 3)
    c.line(MARGIN, y, MARGIN + CONTENT_W, y)
    c.setDash()  # reset
    y -= 12

    # QR image
    qr_reader = _qr_image_reader(qr_payload)
    c.drawImage(qr_reader, MARGIN, y - qr_size, qr_size, qr_size, mask="auto")

    # Labels
    text_x = MARGIN + qr_size + 14
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(CLR_TEXT)
    c.drawString(text_x, y - 20, f"Scan ID: {qr_payload}")

    c.setFont("Helvetica", 8)
    c.setFillColor(CLR_MUTED)
    c.drawString(text_x, y - 36, "QR encodes only sheet session metadata.")

    y -= qr_size + 14
    return y


# ── Public API ──────────────────────────────────────────────────────────────

def render_sheet_pdf_base64(
    *,
    exam_id: str,
    sheet_session_id: str,
    total_questions: int,
    include_roll_number_box: bool,
) -> Tuple[str, str]:
    """
    Generate an answer-sheet PDF and return ``(qr_payload, pdf_base64)``.

    Uses **reportlab** — a pure-Python PDF library — so it works on every OS
    without installing system-level dependencies like GTK / Pango.
    """
    qr_payload = f"sheet_session:{sheet_session_id}|exam:{exam_id}"

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Answer Sheet – {exam_id}")

    y = PAGE_H - MARGIN

    # Header
    y = _draw_header(c, y, exam_id, sheet_session_id)

    # Roll-number box
    if include_roll_number_box:
        y = _draw_roll_number_box(c, y)

    # Question boxes
    for q_no in range(1, total_questions + 1):
        y = _draw_question_box(c, y, q_no)

    # QR footer
    y = _draw_qr_section(c, y, qr_payload)

    c.save()

    pdf_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    logger.info(
        "Generated PDF for exam=%s session=%s  questions=%d  size=%d bytes",
        exam_id,
        sheet_session_id,
        total_questions,
        len(buf.getvalue()),
    )
    return qr_payload, pdf_base64
