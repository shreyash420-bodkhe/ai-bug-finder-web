from __future__ import annotations

from typing import Any


def create_pdf_report(source: str, result: dict[str, Any]) -> bytes:
    """Create a compact PDF report using reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from io import BytesIO

    buffer = BytesIO()
    document = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 48
    document.setTitle("AI Bug Finder Report")
    document.setFont("Helvetica-Bold", 16)
    document.drawString(48, y, "AI Bug Finder Report")
    y -= 28
    document.setFont("Helvetica", 10)
    document.drawString(48, y, f"Findings: {result['summary']['total']}  Errors: {result['summary']['errors']}  Warnings: {result['summary']['warnings']}")
    y -= 26
    for issue in result.get("issues", []):
        if y < 70:
            document.showPage()
            y = height - 48
        document.setFont("Helvetica-Bold", 10)
        document.drawString(48, y, f"Line {issue.get('line', 1)}: {issue['title']}")
        y -= 15
        document.setFont("Helvetica", 9)
        document.drawString(60, y, issue.get("message", "")[:100])
        y -= 14
        document.drawString(60, y, f"Fix: {issue.get('solution', '')[:90]}")
        y -= 24
    document.save()
    return buffer.getvalue()
