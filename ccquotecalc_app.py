import sys
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ---------- Helper for asking only if missing ----------
def ask_if_missing(data, key, prompt, cast=str):
    if data.get(key) is None:
        val = input(prompt)
        if val.strip():
            data[key] = cast(val)
    return data

# ---------- Pricing logic ----------
def calculate_quote(data):
    items = []
    total = 0

    # Base price
    base_price = 140.00
    items.append(("Base Price (Standard)", base_price))
    total += base_price

    # Service charge
    service_charge = 25.00
    items.append(("Service Charge (Standard)", service_charge))
    total += service_charge

    # Additional sq ft
    if data["sq_ft"] > 500:
        extra_sqft = data["sq_ft"] - 500
        extra_price = extra_sqft * 0.30
        items.append((f"Additional sq ft ({extra_sqft:.1f} × $0.30)", extra_price))
        total += extra_price

    # Floors (extra beyond first)
    if data["floors"] > 1:
        floor_price = (data["floors"] - 1) * 25
        items.append((f"Difficulty Access ({data['floors']-1} extra floors)", floor_price))
        total += floor_price

    # Extra cleaning time (over 3 hrs)
    if data["hours"] > 3:
        extra_half_hours = int((data["hours"] - 3) / 0.5)
        extra_time_price = extra_half_hours * 25
        items.append((f"Extra cleaning time ({extra_half_hours} × 30min)", extra_time_price))
        total += extra_time_price

    # Large items
    if data["large_items"] > 0:
        large_price = data["large_items"] * 25
        items.append((f"Large item manipulation (count={data['large_items']})", large_price))
        total += large_price

    # Rugs
    if data["rugs"]:
        total_rug_sqft = sum(data["rugs"])
        rug_price = total_rug_sqft * 4.00
        items.append((f"Area rug cleaning ({total_rug_sqft:.1f} sq ft × $4.00)", rug_price))
        total += rug_price

    # Pet odor treatment
    if data["pet_rooms"] > 0:
        pet_price = data["pet_rooms"] * 75
        items.append((f"Pet odor treatment ({data['pet_rooms']} rooms × $75.00)", pet_price))
        total += pet_price

    # Stain guard
    if data["stain_guard_rooms"] > 0:
        sg_price = data["stain_guard_rooms"] * 50
        items.append((f"Stain guard ({data['stain_guard_rooms']} rooms × $50.00)", sg_price))
        total += sg_price

    # Membership
    membership_prices = {"y": 799, "a": 1479}
    if data["membership"] in membership_prices:
        mem_price = membership_prices[data["membership"]]
        duration = "6-Month" if data["membership"] == "y" else "1-Year"
        items.append((f"{duration} Membership Program", mem_price))
        total += mem_price

    # Bundle discount
    if data["sq_ft"] > 0 and data["rugs"] and data["stain_guard_rooms"] > 0:
        bundle_discount = total * 0.10
        items.append(("Bundle discount (10% off)", -bundle_discount))
        total -= bundle_discount

    # Additional discount
    if data["extra_discount"] > 0:
        items.append(("Additional discount", -data["extra_discount"]))
        total -= data["extra_discount"]

    return items, total

# ---------- Terminal color print ----------
def print_quote(items, total):
    print("-" * 60)
    print(f"{'Service Description':<45} {'Price (USD)':>12}")
    print("-" * 60)
    for desc, price in items:
        if price < 0:
            print(f"\033[32m{desc:<45} ${price:>10.2f}\033[0m")
        else:
            print(f"{desc:<45} ${price:>10.2f}")
    print("-" * 60)
    print(f"\033[1;33m{'GRAND TOTAL:':<45} ${total:>10.2f}\033[0m")
    print("-" * 60)

# ---------- PDF generation ----------
def save_quote_pdf(client_name, items, total, data):
    filename = f"Carpet_Cleaning_Quote_{client_name.replace(' ', '_')}_{datetime.now().date()}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Carpet Cleaning Quick Quote")
    y -= 20
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Client: {client_name}")
    y -= 15
    c.drawString(50, y, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    y -= 30

    # Table header
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Service Description")
    c.drawString(400, y, "Price (USD)")
    y -= 15
    c.line(50, y, 550, y)
    y -= 15

    # Items
    c.setFont("Helvetica", 12)
    for desc, price in items:
        c.drawString(50, y, desc)
        c.drawRightString(550, y, f"${price:,.2f}")
        y -= 15

    y -= 10
    c.line(50, y, 550, y)
    y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "GRAND TOTAL:")
    c.drawRightString(550, y, f"${total:,.2f}")
    y -= 30

    # Upsell responses
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Upsell Responses:")
    y -= 15
    c.setFont("Helvetica", 12)
    for q, resp in data["upsells"].items():
        c.drawString(50, y, f"- {q} → {resp}")
        y -= 15

    c.save()
    print(f"\nPDF saved as: {filename}")

# ---------- Main ----------
def main():
    if sys.stdin.isatty():
        # Interactive mode
        print("Welcome to the Carpet Cleaning Quick Quote Calculator!")
        desc = input("Describe the job (or press Enter to skip): ")
        data = {}
        data = ask_if_missing(data, "client_name", "Client name: ")
        data = ask_if_missing(data, "miles", "Client distance (miles): ", float)
        data = ask_if_missing(data, "sq_ft", "Total sq ft carpet cleaning: ", float)
        data = ask_if_missing(data, "large_items", "Number of large items to move: ", int)
        data = ask_if_missing(data, "floors", "Number of floors: ", int)
        data = ask_if_missing(data, "hours", "Estimated job hours: ", float)
        data = ask_if_missing(data, "extra_discount", "Extra discount amount: ", float)
        data["rugs"] = []
        while True:
            r = input("Enter rug size in sq ft (or Enter to stop): ")
            if not r.strip():
                break
            data["rugs"].append(float(r))
        data = ask_if_missing(data, "pet_rooms", "Pet treatment rooms: ", int)
        data = ask_if_missing(data, "stain_guard_rooms", "Rooms for stain guard: ", int)
        data = ask_if_missing(data, "membership", "Membership (y=6mo/a=1yr/n=none): ")
        data["upsells"] = {
            "Show visible stains or odors with UV light": "Yes" if input("Show stains? (y/n): ") == "y" else "No",
            "Clean sofa": "Yes" if input("Clean sofa? (y/n): ") == "y" else "No",
        }
    else:
        # Render fallback mode
        data = {
            "client_name": "John Smith",
            "miles": 43,
            "sq_ft": 599,
            "large_items": 2,
            "floors": 3,
            "hours": 3.5,
            "extra_discount": 40.00,
            "rugs": [18, 18, 30.5, 8],
            "pet_rooms": 3,
            "stain_guard_rooms": 1,
            "membership": "a",
            "upsells": {
                "Show visible stains or odors with UV light": "Yes",
                "Clean sofa": "Yes",
            },
        }

    items, total = calculate_quote(data)
    print_quote(items, total)
    save_quote_pdf(data["client_name"], items, total, data)

if __name__ == "__main__":
    main()
