#!/usr/bin/env python3
import os
import sys
import smtplib
from datetime import datetime
from email.message import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ---------- Configuration ----------
DEFAULT_SENDER = os.environ.get("SMTP_USERNAME", "candshproperties@gmail.com")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
AUTO_EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT")  # optional auto-send on non-interactive

# ---------- Helpers ----------
def is_interactive():
    return sys.stdin.isatty()

def safe_input(prompt, cast=str, default=None):
    """Input wrapper that won't block in non-interactive mode."""
    if is_interactive():
        val = input(prompt)
        if val.strip() == "":
            return default
        try:
            return cast(val)
        except Exception:
            return default
    else:
        return default

# ---------- Quote calculation ----------
def calculate_quote(data):
    items = []
    total = 0.0

    base_price = 140.00
    items.append(("Base Price (Standard)", base_price))
    total += base_price

    service_charge = 25.00
    items.append(("Service Charge (Standard)", service_charge))
    total += service_charge

    # Additional sqft (over 500)
    extra_sqft = max(0.0, data["sq_ft"] - 500.0)
    if extra_sqft > 0:
        extra_price = extra_sqft * 0.30
        items.append((f"Additional sq ft ({extra_sqft:.1f} × $0.30)", extra_price))
        total += extra_price

    # Extra floors beyond first
    if data["floors"] > 1:
        floor_price = (data["floors"] - 1) * 25.00
        items.append((f"Difficulty Access ({data['floors']-1} extra floors)", floor_price))
        total += floor_price

    # Extra time (beyond 2 hours included; using 30-min increments priced at $25 per half-hour)
    # Historically earlier examples used 2 or 3 hours; here we treat first 2 hours included.
    if data["hours"] > 2:
        extra_half_hours = int(round((data["hours"] - 2) / 0.5))
        extra_time_price = extra_half_hours * 25.00
        items.append((f"Extra cleaning time ({extra_half_hours} × 30min)", extra_time_price))
        total += extra_time_price

    # Large items manipulation
    if data["large_items"] > 0:
        large_item_price = data["large_items"] * 25.00
        items.append((f"Large item manipulation (count={data['large_items']})", large_item_price))
        total += large_item_price

    # Rugs
    if data["rugs"]:
        total_rug_sqft = sum(data["rugs"])
        rug_price = total_rug_sqft * 4.00
        items.append((f"Area rug cleaning ({total_rug_sqft:.1f} sq ft × $4.00)", rug_price))
        total += rug_price

    # Pet treatment
    if data["pet_rooms"] > 0:
        pet_price = data["pet_rooms"] * 75.00
        items.append((f"Pet odor treatment ({data['pet_rooms']} rooms × $75.00)", pet_price))
        total += pet_price

    # Stain guard
    if data["stain_guard_rooms"] > 0:
        sg_price = data["stain_guard_rooms"] * 50.00
        items.append((f"Stain guard ({data['stain_guard_rooms']} rooms × $50.00)", sg_price))
        total += sg_price

    # Membership
    membership_prices = {"y": 799.00, "a": 1479.00}
    if data.get("membership") in membership_prices:
        mem_price = membership_prices[data["membership"]]
        label = "6-Month Membership Program" if data["membership"] == "y" else "1-Year Membership Program"
        items.append((label, mem_price))
        total += mem_price

    # Bundle discount: if carpet + rugs + stain guard present
    bundle_discount = 0.0
    if data["sq_ft"] > 0 and data["rugs"] and data["stain_guard_rooms"] > 0:
        bundle_discount = total * 0.10
        items.append(("Bundle discount (10% off)", -bundle_discount))
        total -= bundle_discount

    # Additional discount (fundraiser etc.)
    if data.get("extra_discount", 0.0) > 0:
        items.append(("Additional discount", -data["extra_discount"]))
        total -= data["extra_discount"]

    return items, total

# ---------- Terminal pretty-print ----------
def print_quote(items, total):
    RESET = "\033[0m"
    GREEN = "\033[32m"
    BOLD_YELLOW = "\033[1;33m"

    print("-" * 66)
    print(f"{'Service Description':<50}{'Price (USD)':>16}")
    print("-" * 66)
    for desc, amt in items:
        if amt < 0:
            # discount green, show as negative
            print(f"{GREEN}{desc:<50}{amt:>16,.2f}{RESET}")
        else:
            print(f"{desc:<50}{amt:>16,.2f}")
    print("-" * 66)
    print(f"{BOLD_YELLOW}{'GRAND TOTAL:':<50}{total:>16,.2f}{RESET}")
    print("-" * 66)

# ---------- PDF generation ----------
def save_quote_pdf(client_name, items, total, data):
    safe_name = client_name.strip() if client_name else "Client"
    safe_name = "_".join(safe_name.split())
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"Carpet_Cleaning_Quote_{safe_name}_{date_str}.pdf"

    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    x_left = 50
    x_right = 520
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_left, y, "Carpet Cleaning Quick Quote")
    y -= 22
    c.setFont("Helvetica", 11)
    c.drawString(x_left, y, f"Client: {client_name}")
    c.drawString(x_right - 200, y, f"Date: {date_str}")
    y -= 22

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_left, y, "Service Description")
    c.drawString(x_right - 40, y, "Price (USD)")
    y -= 12
    c.line(x_left, y, x_right, y)
    y -= 18

    c.setFont("Helvetica", 10)
    for desc, amt in items:
        # wrap long descriptions if necessary (simple truncation)
        c.drawString(x_left, y, desc if len(desc) <= 70 else desc[:67] + "...")
        c.drawRightString(x_right, y, f"${amt:,.2f}")
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)

    y -= 6
    c.line(x_left, y, x_right, y)
    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_left, y, "GRAND TOTAL:")
    c.drawRightString(x_right, y, f"${total:,.2f}")
    y -= 26

    # Discount summary
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_left, y, "Discount summary:")
    y -= 14
    c.setFont("Helvetica", 10)
    # build discount summary from items
    for desc, amt in items:
        if amt < 0:
            c.drawString(x_left + 10, y, f"{desc}: ${-amt:,.2f}")
            y -= 12
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)

    y -= 8
    # Upsell responses
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_left, y, "Upsell Responses:")
    y -= 14
    c.setFont("Helvetica", 10)
    for q, r in data.get("upsells", {}).items():
        c.drawString(x_left + 10, y, f"- {q} → {r}")
        y -= 12
        if y < 80:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)

    c.save()
    return filename

# ---------- Email (SMTP) ----------
def send_email_with_attachment(sender, recipient, subject, body, attachment_path):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise RuntimeError("SMTP_USERNAME or SMTP_PASSWORD not configured in environment variables.")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    # Attach PDF
    with open(attachment_path, "rb") as f:
        data = f.read()
    msg.add_attachment(data, maintype="application", subtype="pdf", filename=os.path.basename(attachment_path))

    # Send via TLS
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(msg)

# ---------- Main flow ----------
def main():
    # Build data dictionary either interactively or from fallback example
    if is_interactive():
        print("Welcome to Carpet Cleaning Quick Quote Calculator (interactive).")
        client_name = safe_input("Client name: ", str, "Client")
        miles = safe_input("Client distance (miles): ", float, 0.0)
        sq_ft = safe_input("Total carpet square feet: ", float, 0.0)
        large_items = safe_input("Large items to move (>50 lb): ", int, 0)
        floors = safe_input("Number of floors: ", int, 1)
        hours = safe_input("Estimated job hours: ", float, 2.0)
        extra_discount = safe_input("Additional discount (dollars): ", float, 0.0)
        # rugs
        rugs = []
        rc = safe_input("Number of rugs (leave blank for 0): ", int, 0)
        for i in range(rc or 0):
            s = safe_input(f"  Size of rug #{i+1} (sq ft): ", float, 0.0)
            rugs.append(s)
        pet_rooms = safe_input("Number of rooms for pet treatment: ", int, 0)
        stain_guard_rooms = safe_input("Number of rooms for stain guard/protection: ", int, 0)
        membership = safe_input("Membership (y=6-month / a=1-year / n=none): ", str, "n").lower()
        upsells = {}
        upsells["Show visible stains or odors with UV light"] = "Accepted" if safe_input("UV light check? (y/n): ", str, "n").lower().startswith("y") else "Declined"
        upsells["Clean sofa while here"] = "Accepted" if safe_input("Clean sofa? (y/n): ", str, "n").lower().startswith("y") else "Declined"

        data = {
            "client_name": client_name,
            "miles": miles,
            "sq_ft": sq_ft,
            "large_items": large_items,
            "floors": floors,
            "hours": hours,
            "extra_discount": extra_discount or 0.0,
            "rugs": rugs,
            "pet_rooms": pet_rooms,
            "stain_guard_rooms": stain_guard_rooms,
            "membership": membership,
            "upsells": upsells,
        }

    else:
        # Non-interactive (Render): use your example scenario as fallback
        data = {
            "client_name": "John Smith",
            "miles": 43,
            "sq_ft": 599,
            "large_items": 2,
            "floors": 3,
            "hours": 3.5,
            "extra_discount": 40.0,
            "rugs": [18.0, 18.0, 30.5, 8.0],
            "pet_rooms": 3,
            "stain_guard_rooms": 1,
            "membership": "a",  # 1-year
            "upsells": {
                "Show visible stains or odors with UV light": "Accepted",
                "Clean sofa while here": "Accepted",
            },
        }

    # Calculate quote
    items, total = calculate_quote(data)

    # Print table to terminal/logs
    print_quote(items, total)

    # Save PDF
    client_name_for_file = data.get("client_name", "Client")
    pdf_path = save_quote_pdf(client_name_for_file, items, total, data)
    print(f"\nSaved PDF: {pdf_path}")

    # Email logic
    recipient = None
    if is_interactive():
        want_email = safe_input("Would you like to email this quote? (y/n): ", str, "n").lower().startswith("y")
        if want_email:
            recipient = safe_input("Recipient email address: ", str, "")
            if not recipient:
                print("No recipient provided. Skipping email.")
    else:
        # Non-interactive: auto-send only if EMAIL_RECIPIENT set in env
        if AUTO_EMAIL_RECIPIENT:
            recipient = AUTO_EMAIL_RECIPIENT

    # Attempt to send if recipient provided
    if recipient:
        subject = f"Carpet Cleaning Quote for {data.get('client_name', 'Client')}"
        body = f"Hello,\n\nAttached is your carpet cleaning quote for {data.get('client_name')}.\n\nThank you,\n{DEFAULT_SENDER}\n"
        try:
            send_email_with_attachment(DEFAULT_SENDER, recipient, subject, body, pdf_path)
            print(f"Email sent to {recipient}")
        except Exception as e:
            print(f"Failed to send email: {e}")
            # Do not crash; PDF was already saved.

if __name__ == "__main__":
    main()
