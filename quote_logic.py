# quote_logic.py
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

def calculate_quote(data):
    """Run the same calculations as your CLI script."""
    # This is a simplified placeholder — replace with your full calculation logic
    # from your original app
    items = [
        ("Base Price (Standard)", 140.00),
        ("Service Charge (Standard)", 25.00),
        ("Additional sq ft (99.0 * $0.30)", 29.70),
        ("Difficulty Access (2 extra floor)", 50.00),
        ("Extra cleaning time (2 × 30min)", 50.00),
        ("Large item manipulation (count=2)", 50.00),
        ("Area rug cleaning (74.5 sq ft × $4.00)", 298.00),
        ("Pet odor treatment (3 rooms × $75.00)", 225.00),
        ("Stain guard (1 rooms × $50.00)", 50.00),
        ("1-Year Membership Program", 1479.00),
        ("Bundle discount (10% off)", -239.67),
        ("Additional discount", -40.00),
    ]
    total = sum(price for _, price in items)
    discount_summary = [
        "Bundle discount applied: 10% off, saving $239.67. "
        "Because you selected carpet cleaning, area rugs and stain guard together.",
        "Additional discount applied: saving $40.00."
    ]
    upsell_responses = [
        ("Show visible stains or odors with UV light or moisture meters.", "Accepted"),
        ("While I’m here, I can also clean this sofa — it traps a lot of allergens just like carpet.", "Accepted")
    ]
    return items, total, discount_summary, upsell_responses

def generate_pdf(client_name, items, total, discount_summary, upsell_responses):
    """Generate PDF as bytes."""
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, height - 50, f"Carpet Cleaning Quick Quote - {client_name}")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(72, height - 70, f"Date: {datetime.now().strftime('%Y-%m-%d')}")

    y = height - 100
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(72, y, "Detailed Estimate:")
    y -= 20

    pdf.setFont("Helvetica", 11)
    for desc, price in items:
        pdf.drawString(72, y, f"{desc}")
        pdf.drawRightString(width - 72, y, f"${price:,.2f}")
        y -= 18

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(72, y, f"Grand Total: ${total:,.2f}")

    y -= 30
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(72, y, "Discount Summary:")
    y -= 20
    pdf.setFont("Helvetica", 11)
    for line in discount_summary:
        pdf.drawString(72, y, f"- {line}")
        y -= 16

    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(72, y, "Upsell Responses:")
    y -= 20
    pdf.setFont("Helvetica", 11)
    for desc, resp in upsell_responses:
        pdf.drawString(72, y, f"- {desc} → {resp}")
        y -= 16

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()

def send_email_with_attachment(to_email, subject, body, attachment_bytes, filename):
    """Send PDF via Gmail SMTP using env vars."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    msg = MIMEMultipart()
    msg["From"] = smtp_username
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    part = MIMEApplication(attachment_bytes, Name=filename)
    part["Content-Disposition"] = f'attachment; filename="{filename}"'
    msg.attach(part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
