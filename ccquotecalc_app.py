from flask import Flask, render_template_string, request
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import smtplib, os, io
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

app = Flask(__name__)

# -----------------------
# QUOTE CALCULATION LOGIC
# -----------------------
def calculate_quote(data):
    rows = []
    total = 0

    # Base price
    base_price = 140.00
    rows.append(("Base Price (Standard)", f"${base_price:.2f}"))
    total += base_price

    # Service charge
    service_charge = 25.00
    rows.append(("Service Charge (Standard)", f"${service_charge:.2f}"))
    total += service_charge

    # Additional sq ft
    if data["sq_ft"] > 781:
        extra_sqft = data["sq_ft"] - 781
        price_extra = extra_sqft * 0.30
        rows.append((f"Additional sq ft ({extra_sqft} × $0.30)", f"${price_extra:.2f}"))
        total += price_extra

    # Floors
    if data["floors"] > 1:
        diff_price = (data["floors"] - 1) * 25
        rows.append((f"Difficulty Access ({data['floors']-1} extra floor)", f"${diff_price:.2f}"))
        total += diff_price

    # Extra time
    if data["hours"] > 2.0:
        extra_time = int((data["hours"] - 2.0) * 2) * 25
        rows.append((f"Extra cleaning time", f"${extra_time:.2f}"))
        total += extra_time

    # Large items
    if data["large_items"] > 0:
        large_items_price = data["large_items"] * 25
        rows.append((f"Large item manipulation (count={data['large_items']})", f"${large_items_price:.2f}"))
        total += large_items_price

    # Rugs
    if data["total_rug_sqft"] > 0:
        rugs_price = data["total_rug_sqft"] * 4
        rows.append((f"Area rug cleaning ({data['total_rug_sqft']} sq ft × $4.00)", f"${rugs_price:.2f}"))
        total += rugs_price

    # Pet treatment
    if data["pet_rooms"] > 0:
        pet_price = data["pet_rooms"] * 75
        rows.append((f"Pet odor treatment ({data['pet_rooms']} rooms × $75.00)", f"${pet_price:.2f}"))
        total += pet_price

    # Stain guard
    if data["stain_guard_rooms"] > 0:
        sg_price = data["stain_guard_rooms"] * 50
        rows.append((f"Stain guard ({data['stain_guard_rooms']} rooms × $50.00)", f"${sg_price:.2f}"))
        total += sg_price

    # Membership
    if data["membership"] == "y":
        mem_price = 789
        rows.append(("6-Month Membership Program", f"${mem_price:.2f}"))
        total += mem_price
    elif data["membership"] == "a":
        mem_price = 1479
        rows.append(("1-Year Membership Program", f"${mem_price:.2f}"))
        total += mem_price

    # Discounts
    if data["discount"] > 0:
        rows.append(("Additional discount", f"$-{data['discount']:.2f}"))
        total -= data["discount"]

    return rows, total

# -----------------------
# PDF GENERATION
# -----------------------
def generate_pdf(client_name, rows, total):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, y, f"Carpet Cleaning Quote for {client_name}")
    y -= 40
    c.setFont("Helvetica", 12)
    for item, price in rows:
        c.drawString(50, y, item)
        c.drawRightString(550, y, price)
        y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Grand Total:")
    c.drawRightString(550, y, f"${total:.2f}")
    c.save()
    buffer.seek(0)
    return buffer

# -----------------------
# EMAIL SENDING
# -----------------------
def send_email_with_attachment(to_email, subject, body, pdf_buffer, filename):
    try:
        msg = MIMEMultipart()
        msg["From"] = os.environ.get("SMTP_USERNAME")
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        part = MIMEApplication(pdf_buffer.read(), Name=filename)
        part["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(part)

        with smtplib.SMTP(os.environ.get("SMTP_SERVER"), int(os.environ.get("SMTP_PORT"))) as server:
            server.starttls()
            server.login(os.environ.get("SMTP_USERNAME"), os.environ.get("SMTP_PASSWORD"))
            server.send_message(msg)
        return True, "Email sent successfully."
    except Exception as e:
        return False, f"Failed to send email: {e}"

# -----------------------
# HTML TEMPLATE
# -----------------------
form_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Carpet Cleaning Quick Quote Calculator</title>
</head>
<body>
<h2>Carpet Cleaning Quick Quote Calculator</h2>
<form method="POST">
    Client Name: <input type="text" name="client_name" value="{{ data.client_name }}"><br>
    Distance (miles): <input type="number" step="0.1" name="miles" value="{{ data.miles }}"><br>
    Sq Ft: <input type="number" name="sq_ft" value="{{ data.sq_ft }}"><br>
    Pet treatment rooms: <input type="number" name="pet_rooms" value="{{ data.pet_rooms }}"><br>
    Large items: <input type="number" name="large_items" value="{{ data.large_items }}"><br>
    Total Rug Sq Ft: <input type="number" step="0.1" name="total_rug_sqft" value="{{ data.total_rug_sqft }}"><br>
    Floors: <input type="number" name="floors" value="{{ data.floors }}"><br>
    Hours: <input type="number" step="0.1" name="hours" value="{{ data.hours }}"><br>
    Stain Guard Rooms: <input type="number" name="stain_guard_rooms" value="{{ data.stain_guard_rooms }}"><br>
    Membership (n=none, y=6mo, a=1yr): <input type="text" name="membership" value="{{ data.membership }}"><br>
    Discount: <input type="number" step="0.01" name="discount" value="{{ data.discount }}"><br>
    Recipient Email (for PDF): <input type="email" name="recipient_email" value="{{ data.recipient_email }}"><br><br>

    <button type="submit" name="action" value="show">Show Quote</button>
    <button type="submit" name="action" value="email">Email PDF</button>
    <button type="submit" name="action" value="clear">Clear</button>
</form>

{% if rows %}
<h3>Detailed Estimate for {{ data.client_name }}</h3>
<table border="1" cellpadding="5" cellspacing="0">
<tr><th>Item</th><th>Price</th></tr>
{% for item, price in rows %}
<tr><td>{{ item }}</td><td>{{ price }}</td></tr>
{% endfor %}
<tr><th>Grand Total</th><th>${{ "%.2f"|format(total) }}</th></tr>
</table>
{% endif %}

{% if message %}
<p>{{ message }}</p>
{% endif %}
</body>
</html>
"""

# -----------------------
# ROUTES
# -----------------------
@app.route("/", methods=["GET", "POST"])
def home():
    default_data = {
        "client_name": "",
        "miles": "",
        "sq_ft": "",
        "pet_rooms": "",
        "large_items": "",
        "total_rug_sqft": "",
        "floors": "",
        "hours": "",
        "stain_guard_rooms": "",
        "membership": "",
        "discount": "",
        "recipient_email": ""
    }

    if request.method == "POST":
        action = request.form.get("action")

        if action == "clear":
            return render_template_string(form_template, data=default_data, rows=None, total=None, message=None)

        data = {k: request.form.get(k, "") for k in default_data}
        for key in ["miles", "sq_ft", "pet_rooms", "large_items", "total_rug_sqft", "floors", "hours", "stain_guard_rooms", "discount"]:
            try:
                data[key] = float(data[key]) if data[key] else 0
            except:
                data[key] = 0

        rows, total = calculate_quote(data)

        if action == "show":
            return render_template_string(form_template, data=data, rows=rows, total=total, message=None)

        elif action == "email":
            pdf_buffer = generate_pdf(data["client_name"], rows, total)
            success, msg = send_email_with_attachment(
                data["recipient_email"],
                f"Carpet Cleaning Quote for {data['client_name']}",
                "Please find attached your carpet cleaning quote.",
                pdf_buffer,
                "quote.pdf"
            )
            return render_template_string(form_template, data=data, rows=rows, total=total, message=msg)

    return render_template_string(form_template, data=default_data, rows=None, total=None, message=None)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
