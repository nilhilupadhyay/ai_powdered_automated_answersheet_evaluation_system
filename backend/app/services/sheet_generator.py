import base64
import io
import logging

import qrcode
from jinja2 import Template

try:
    from weasyprint import HTML
except (ImportError, OSError) as e:
    logging.warning(f"Failed to import WeasyPrint: {e}. PDF generation will return a mock PDF.")
    HTML = None


SHEET_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <style>
      body { font-family: Arial, sans-serif; margin: 24px; }
      .header { margin-bottom: 16px; }
      .meta { font-size: 14px; color: #333; margin-bottom: 12px; }
      .roll-box { border: 1px solid #222; padding: 8px; margin-bottom: 14px; width: 260px; }
      .question { border: 1px solid #bbb; border-radius: 6px; min-height: 54px; margin-bottom: 10px; padding: 8px; }
      .qr-wrap { margin-top: 20px; border-top: 1px dashed #888; padding-top: 10px; display: flex; align-items: center; gap: 12px; }
      .small { font-size: 12px; color: #666; }
    </style>
  </head>
  <body>
    <div class="header">
      <h2>Answer Sheet</h2>
      <div class="meta">Exam ID: {{ exam_id }} | Session: {{ sheet_session_id }}</div>
    </div>
    {% if include_roll_number_box %}
    <div class="roll-box">Roll Number: ____________________________</div>
    {% endif %}
    {% for q_no in question_numbers %}
    <div class="question">
      <strong>Q{{ q_no }}.</strong>
      <div class="small">Write your answer in this box.</div>
    </div>
    {% endfor %}
    <div class="qr-wrap">
      <img src="data:image/png;base64,{{ qr_code_base64 }}" width="110" height="110" alt="qr-code">
      <div>
        <div><strong>Scan ID:</strong> {{ qr_payload }}</div>
        <div class="small">QR encodes only sheet session metadata.</div>
      </div>
    </div>
  </body>
</html>
"""


def create_qr_base64(payload: str) -> str:
    image = qrcode.make(payload)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def render_sheet_pdf_base64(
    *,
    exam_id: str,
    sheet_session_id: str,
    total_questions: int,
    include_roll_number_box: bool,
) -> tuple[str, str]:
    qr_payload = f"sheet_session:{sheet_session_id}|exam:{exam_id}"
    qr_code_base64 = create_qr_base64(qr_payload)

    template = Template(SHEET_TEMPLATE)
    rendered_html = template.render(
        exam_id=exam_id,
        sheet_session_id=sheet_session_id,
        question_numbers=list(range(1, total_questions + 1)),
        include_roll_number_box=include_roll_number_box,
        qr_code_base64=qr_code_base64,
        qr_payload=qr_payload,
    )
    if HTML is None:
        # Return a dummy PDF
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n5 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n72 712 Td\n(Mock PDF (WeasyPrint failed to load)) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000214 00000 n \n0000000302 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n397\n%%EOF"
    else:
        pdf_bytes = HTML(string=rendered_html).write_pdf()
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    return qr_payload, pdf_base64
