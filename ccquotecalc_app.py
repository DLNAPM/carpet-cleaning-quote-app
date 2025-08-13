from flask import Flask, render_template_string, request
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

app = Flask(__name__)

# -------------------
# DEFAULT PREFILLED DATA
# -------------------
default_data = {
    "client_name": "John Doe",
    "miles": 15,
    "sq_ft": 900,
    "pet_rooms": 2,
    "large_items": 1,
    "total_rug_sqft": 50,
    "floors": 2,
    "hours": 3.0,
    "stain_guard_rooms": 1,
    "membership": "n",
    "discount": 25.00,
    "recipient_email": "customer@example.com"
}

# -------------------
# QUOTE CALCULATION LOGIC
# -------------------
def calculate_quote(data):
    base_price = 140.00
    service_charge = 25.00
    prices = {
        "sq_ft_over_800": 0.30,
        "extra_floor": 25.00,
        "extra_time_per_30min": 25.00,
        "large_item": 25.00,
        "rug_sqft": 4.00,
        "pet_room": 75.00,
        "stain_guard": 50.00,
        "membership_6mo": 799.00,
        "membership_1yr": 1479.00
    }

    rows = []
    total = base_price
    rows.append(("Base Price (Standard)", base_price))
    total += service_charge
    rows.append(("Service Charge (Standard)", service_charge))

    if data["sq_ft"] > 800:
        extra_sqft = data["sq_ft"] - 800
        cost = extra_sqft * prices["sq_ft_over_800"]
        rows.append((f"Additional sq ft ({extra_sqft} * ${prices['sq_ft_over_800']:.2f})", cost))
        total += cost

    if data["floors"] > 1:
        extra_floors = data["floors"] - 1
        cost = extra_floors * prices["extra_floor"]
        rows.append((f"Difficulty Access ({extra_floors} extra floor)", cost))
        total += cost

    if data["hours"] > 2:
        extra_half_hours = int((data["hours"] - 2) / 0.5)
        cost = extra_half_hours * prices["extra_time_per_30min"]
        rows.append((f"Extra cleaning time ({extra_half_hours} × 30min)", cost))
        total += cost

    if data["large_items"] > 0:
        cost = data["large_items"] * prices["large_item"]
        rows.append((f"Large item manipulation (count={data['large_items']})", cost))
        total += cost

    if data["total_rug_sqft"] > 0:
        cost = data["total_rug_sqft"] * prices["rug_sqft"]
        rows.append((f"Area rug cleaning ({data['total_rug_sqft']} sq ft × ${prices['rug_sqft']:.2f})", cost))
        total += cost

    if data["pet_rooms"] > 0:
        cost = data["pet_rooms"] * prices["pet_room"]
        rows.append((f"Pet odor treatment ({data['pet_rooms']} rooms × ${prices['pet_room']:.2f})", cost))
        total += cost

    if data["stain_guard_rooms"] > 0:
        cost = data["stain_guard_rooms"] * prices["stain_guard"]
        rows.append((f"Stain guard ({data['stain_guard_rooms']} rooms × ${prices['stain_guard']:.2f})", cost))
        total += cost

    if data["membership"] == "y":
        rows.append(("6-Month Membership Program", prices["membership_6mo"]))
        total += prices["membership_6mo"]
    elif data["membership"] == "a":
        rows.append(("1-Year Membership Program", prices["membership_1yr"]))
        total += prices["membership_1yr"]

    if data["discount"] > 0:
        rows.append(("Additional discount", -data["discount"]))
        total -= data["discount"]

    return rows, total

# -------------------
# PDF GENERATION
# -------------------
def generate_pdf(data, rows, total):
    pdf_buffer = BytesIO()
    p = canvas.Canvas(pdf_buffer, pagesize=letter)
    p.setFont("Helvetica", 12)
    p.drawString(50, 750, f"Carpet Cleaning Quote for {data['client_name']}")
    p.drawString(50, 730, f"Distance: {data['miles']} miles")
    p.drawString(50, 710, f"Square Footage: {data['sq_ft']} sq ft")

    y = 680
    for desc, cost in rows:
        p.drawString(50, y, f"{desc}")
        p.drawRightString(550, y, f"${cost:,.2f}")
        y -= 20

    p.drawString(50, y-10, "-"*60)
    p.drawString(50, y-30, f"Grand Total:")
    p.drawRightString(550, y-30, f"${total:,.2f}")
    p.showPage()
    p.save()
    pdf_buffer.seek(0)
    return pdf_buffer

# -------------------
# EMAIL PDF
# -------------------
def send_email_with_attachment(recipient, pdf_buffer):
    sender = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = "Your Carpet Cleaning Quote"

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(pdf_buffer.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="quote.pdf"')
    msg.attach(part)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        return False, str(e)

# -------------------
# FLASK ROUTES
# -------------------
@app.route("/", methods=["GET", "POST"])
def index():
    form_data = default_data.copy()
    rows, total, email_status = None, None, None

    if request.method == "POST":
        action = request.form.get("action")
        if action == "clear":
            form_data = {k: "" for k in default_data}
        else:
            for k in default_data:
                val = request.form.get(k)
                if k in ["miles", "sq_ft", "pet_rooms", "large_items", "total_rug_sqft", "floors", "stain_guard_rooms"]:
                    try:
                        form_data[k] = int(val)
                    except:
                        form_data[k] = 0
                elif k in ["hours", "discount"]:
                    try:
                        form_data[k] = float(val)
                    except:
                        form_data[k] = 0.0
                else:
                    form_data[k] = val

            rows, total = calculate_quote(form_data)

            if action == "email":
                pdf_buffer = generate_pdf(form_data, rows, total)
                success, err = send_email_with_attachment(form_data["recipient_email"], pdf_buffer)
                email_status = "Email sent!" if success else f"Failed to send email: {err}"

    return render_template_string(TEMPLATE, data=form_data, rows=rows, total=total, email_status=email_status)

# -------------------
# HTML TEMPLATE WITH DARK THEME
# -------------------
TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Carpet Cleaning Quick Quote</title>
    <style>
        body {
            background-color: black;
            color: white;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }
        .container {
            display: flex;
            padding: 20px;
        }
        .form-container {
            flex: 1;
            background-color: #001f3f;
            padding: 20px;
            border-radius: 10px;
            margin-right: 20px;
        }
        .quote-container {
            flex: 1;
            background-color: #001f3f;
            padding: 20px;
            border-radius: 10px;
        }
        label { display: block; margin-top: 10px; }
        input, select {
            width: 100%;
            padding: 5px;
            margin-top: 3px;
            border-radius: 5px;
            border: none;
        }
        .buttons {
            margin-top: 15px;
        }
        button {
            padding: 10px 15px;
            margin-right: 5px;
            border: none;
            border-radius: 5px;
            background: linear-gradient(90deg, #0044cc, #0088ff);
            color: white;
            cursor: pointer;
        }
        table {
            width: 100%;
            color: white;
            border-collapse: collapse;
        }
        td {
            padding: 5px;
            border-bottom: 1px solid #555;
        }
        .total-row {
            font-weight: bold;
            border-top: 2px solid white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="form-container">
            <h2>Carpet Cleaning Job Details</h2>
            <form method="post">
                {% for field, value in data.items() %}
                    <label>{{ field.replace('_', ' ').title() }}:</label>
                    <input name="{{field}}" value="{{value}}">
                {% endfor %}
                <div class="buttons">
                    <button type="submit" name="action" value="show">Show Quote</button>
                    <button type="submit" name="action" value="email">Email PDF</button>
                    <button type="submit" name="action" value="clear">Clear</button>
                </div>
            </form>
            {% if email_status %}
                <p>{{email_status}}</p>
            {% endif %}
        </div>
        <div class="quote-container">
            {% if rows %}
                <h2>Quote Details</h2>
                <table>
                    {% for desc, cost in rows %}
                        <tr>
                            <td>{{desc}}</td>
                            <td style="text-align:right;">${{ "%.2f"|format(cost) }}</td>
                        </tr>
                    {% endfor %}
                    <tr class="total-row">
                        <td>Grand Total</td>
                        <td style="text-align:right;">${{ "%.2f"|format(total) }}</td>
                    </tr>
                </table>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
