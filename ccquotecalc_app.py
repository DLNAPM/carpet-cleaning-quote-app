from flask import Flask, render_template_string, request
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

app = Flask(__name__)

# -------------------------
# QUOTE CALCULATION LOGIC
# -------------------------
def calculate_quote(data):
    # Prices
    base_price = 140.0
    service_charge = 25.0
    extra_sqft_rate = 0.30
    extra_floor_charge = 25.0
    extra_time_rate = 25.0
    large_item_charge = 25.0
    rug_rate = 4.0
    pet_treatment_rate = 75.0
    stain_guard_rate = 50.0
    membership_6mo = 799.0
    membership_1yr = 1479.0
    bundle_discount_rate = 0.10

    # Calculation
    results = []
    total = 0.0

    results.append(("Base Price (Standard)", base_price))
    total += base_price

    results.append(("Service Charge (Standard)", service_charge))
    total += service_charge

    if data["sqft"] > 781:
        extra_sqft = data["sqft"] - 781
        charge = extra_sqft * extra_sqft_rate
        results.append((f"Additional sq ft ({extra_sqft} × ${extra_sqft_rate:.2f})", charge))
        total += charge

    if data["floors"] > 1:
        floors_extra = data["floors"] - 1
        charge = floors_extra * extra_floor_charge
        results.append((f"Difficulty Access ({floors_extra} extra floor)", charge))
        total += charge

    if data["extra_time_hours"] > 0:
        charge = data["extra_time_hours"] * 2 * extra_time_rate
        results.append((f"Extra cleaning time ({data['extra_time_hours']} hrs)", charge))
        total += charge

    if data["large_items"] > 0:
        charge = data["large_items"] * large_item_charge
        results.append((f"Large item manipulation (count={data['large_items']})", charge))
        total += charge

    if data["rug_sqft"] > 0:
        charge = data["rug_sqft"] * rug_rate
        results.append((f"Area rug cleaning ({data['rug_sqft']} sq ft × ${rug_rate:.2f})", charge))
        total += charge

    if data["pet_rooms"] > 0:
        charge = data["pet_rooms"] * pet_treatment_rate
        results.append((f"Pet odor treatment ({data['pet_rooms']} rooms × ${pet_treatment_rate:.2f})", charge))
        total += charge

    if data["stain_guard_rooms"] > 0:
        charge = data["stain_guard_rooms"] * stain_guard_rate
        results.append((f"Stain guard ({data['stain_guard_rooms']} rooms × ${stain_guard_rate:.2f})", charge))
        total += charge

    if data["membership"] == "6mo":
        results.append(("6-Month Membership Program", membership_6mo))
        total += membership_6mo
    elif data["membership"] == "1yr":
        results.append(("1-Year Membership Program", membership_1yr))
        total += membership_1yr

    bundle_discount = 0
    if data["sqft"] > 0 and data["rug_sqft"] > 0 and data["stain_guard_rooms"] > 0:
        bundle_discount = total * bundle_discount_rate
        results.append((f"Bundle discount ({bundle_discount_rate*100:.0f}% off)", -bundle_discount))
        total -= bundle_discount

    if data["extra_discount"] > 0:
        results.append(("Additional discount", -data["extra_discount"]))
        total -= data["extra_discount"]

    return results, total

# -------------------------
# PDF GENERATION
# -------------------------
def generate_pdf(client_name, results, total):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, f"Carpet Cleaning Quote for {client_name}")
    y -= 30

    p.setFont("Helvetica", 12)
    for item, amount in results:
        p.drawString(50, y, f"{item:<50} ${amount:,.2f}")
        y -= 20

    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, f"Grand Total: ${total:,.2f}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# -------------------------
# EMAIL SENDING
# -------------------------
def send_email_with_attachment(to_email, subject, body, pdf_buffer, filename):
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_server or not smtp_username or not smtp_password:
        return "SMTP settings are not configured."

    msg = MIMEMultipart()
    msg["From"] = smtp_username
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    part = MIMEApplication(pdf_buffer.read(), Name=filename)
    part["Content-Disposition"] = f'attachment; filename="{filename}"'
    msg.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        return f"Quote emailed to {to_email} successfully."
    except Exception as e:
        return f"Failed to send email: {str(e)}"

# -------------------------
# FLASK ROUTES
# -------------------------
HTML_FORM = """
<!doctype html>
<title>Carpet Cleaning Quick Quote</title>
<h1>Carpet Cleaning Quick Quote</h1>
<form method="post" action="/quote">
  Client Name: <input type="text" name="client_name" required><br>
  Distance (miles): <input type="number" step="0.1" name="miles" required><br>
  Square footage: <input type="number" step="0.1" name="sqft" required><br>
  Large items: <input type="number" name="large_items" value="0"><br>
  Area rug total sq ft: <input type="number" step="0.1" name="rug_sqft" value="0"><br>
  Pet treatment rooms: <input type="number" name="pet_rooms" value="0"><br>
  Floors: <input type="number" name="floors" value="1"><br>
  Extra time (hours): <input type="number" step="0.5" name="extra_time_hours" value="0"><br>
  Stain guard rooms: <input type="number" name="stain_guard_rooms" value="0"><br>
  Membership: <select name="membership">
    <option value="">None</option>
    <option value="6mo">6 Month</option>
    <option value="1yr">1 Year</option>
  </select><br>
  Extra discount: <input type="number" step="0.01" name="extra_discount" value="0"><br>
  <button type="submit" name="action" value="show">Show Quote</button>
  <button type="submit" name="action" value="email">Email PDF</button><br>
  Recipient Email (for PDF): <input type="email" name="recipient_email"><br>
</form>
{% if results %}
<h2>Quote for {{ client_name }}</h2>
<table border="1" cellpadding="5">
<tr><th>Item</th><th>Amount</th></tr>
{% for item, amount in results %}
<tr><td>{{ item }}</td><td>${{ "%.2f"|format(amount) }}</td></tr>
{% endfor %}
<tr><td><b>Grand Total</b></td><td><b>${{ "%.2f"|format(total) }}</b></td></tr>
</table>
{% if message %}<p>{{ message }}</p>{% endif %}
{% endif %}
"""

@app.route("/", methods=["GET"])
def form():
    return render_template_string(HTML_FORM)

@app.route("/quote", methods=["POST"])
def quote():
    data = {
        "client_name": request.form.get("client_name"),
        "miles": float(request.form.get("miles") or 0),
        "sqft": float(request.form.get("sqft") or 0),
        "large_items": int(request.form.get("large_items") or 0),
        "rug_sqft": float(request.form.get("rug_sqft") or 0),
        "pet_rooms": int(request.form.get("pet_rooms") or 0),
        "floors": int(request.form.get("floors") or 1),
        "extra_time_hours": float(request.form.get("extra_time_hours") or 0),
        "stain_guard_rooms": int(request.form.get("stain_guard_rooms") or 0),
        "membership": request.form.get("membership"),
        "extra_discount": float(request.form.get("extra_discount") or 0)
    }

    results, total = calculate_quote(data)
    message = ""

    if request.form.get("action") == "email":
        recipient = request.form.get("recipient_email")
        if recipient:
            pdf_buffer = generate_pdf(data["client_name"], results, total)
            message = send_email_with_attachment(
                recipient,
                f"Carpet Cleaning Quote for {data['client_name']}",
                "Hello,\n\nAttached is your detailed carpet cleaning quote.\n\nThank you.",
                pdf_buffer,
                f"Quote_{data['client_name']}.pdf"
            )
        else:
            message = "Recipient email not provided. PDF not sent."

    return render_template_string(HTML_FORM, results=results, total=total, client_name=data["client_name"], message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
