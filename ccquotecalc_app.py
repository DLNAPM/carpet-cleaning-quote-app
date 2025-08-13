# app.py
from flask import Flask, render_template_string, request
from datetime import datetime
from quote_logic import calculate_quote, generate_pdf, send_email_with_attachment

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Carpet Cleaning Quote</title>
</head>
<body>
    <h1>Carpet Cleaning Quick Quote</h1>
    <form method="post">
        Client Name: <input type="text" name="client_name" required><br><br>
        Recipient Email (for PDF): <input type="email" name="recipient_email"><br><br>
        <button type="submit" name="action" value="show">Show Quote</button>
        <button type="submit" name="action" value="email">Email PDF</button>
    </form>
    {% if items %}
        <h2>Detailed Estimate for {{ client_name }}</h2>
        <table border="1" cellpadding="5">
            <tr><th>Description</th><th>Price</th></tr>
            {% for desc, price in items %}
                <tr>
                    <td>{{ desc }}</td>
                    <td>${{ "%.2f"|format(price) }}</td>
                </tr>
            {% endfor %}
            <tr><td><b>Grand Total</b></td><td><b>${{ "%.2f"|format(total) }}</b></td></tr>
        </table>
        <h3>Discount Summary:</h3>
        <ul>
            {% for line in discount_summary %}
                <li>{{ line }}</li>
            {% endfor %}
        </ul>
        <h3>Upsell Responses:</h3>
        <ul>
            {% for desc, resp in upsell_responses %}
                <li>{{ desc }} → {{ resp }}</li>
            {% endfor %}
        </ul>
        {% if email_sent %}
            <p style="color:green;">Quote emailed successfully to {{ recipient_email }}</p>
        {% endif %}
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        client_name = request.form["client_name"]
        recipient_email = request.form.get("recipient_email", "").strip()

        items, total, discount_summary, upsell_responses = calculate_quote({})

        if request.form["action"] == "show":
            return render_template_string(HTML_TEMPLATE, client_name=client_name,
                                          items=items, total=total,
                                          discount_summary=discount_summary,
                                          upsell_responses=upsell_responses,
                                          email_sent=False)

        elif request.form["action"] == "email" and recipient_email:
            pdf_bytes = generate_pdf(client_name, items, total, discount_summary, upsell_responses)
            filename = f"Carpet_Cleaning_Quote_{client_name}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
            send_email_with_attachment(
                recipient_email,
                f"Carpet Cleaning Quote for {client_name}",
                "Hello,\n\nAttached is your detailed carpet cleaning quote.\n\nThank you,\nC&S Properties",
                pdf_bytes,
                filename
            )
            return render_template_string(HTML_TEMPLATE, client_name=client_name,
                                          items=items, total=total,
                                          discount_summary=discount_summary,
                                          upsell_responses=upsell_responses,
                                          email_sent=True,
                                          recipient_email=recipient_email)
    return render_template_string(HTML_TEMPLATE, items=None)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
