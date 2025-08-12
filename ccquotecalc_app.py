import re

def ask_if_missing(data, key, prompt, cast_func=str):
    if key not in data or data[key] is None:
        val = input(prompt)
        if val.strip() != "":
            data[key] = cast_func(val)
    return data

def parse_description(desc):
    data = {}
    # Simple keyword matching
    miles_match = re.search(r"(\d+(\.\d+)?)\s*miles?", desc, re.I)
    if miles_match: data["miles"] = float(miles_match.group(1))

    sqft_match = re.search(r"(\d+(\.\d+)?)\s*sq\.?\s*ft", desc, re.I)
    if sqft_match: data["sqft"] = float(sqft_match.group(1))

    large_items_match = re.search(r"(\d+)\s+large\s+items?", desc, re.I)
    if large_items_match: data["large_items"] = int(large_items_match.group(1))

    floors_match = re.search(r"(\d+)\s+floors?", desc, re.I)
    if floors_match: data["floors"] = int(floors_match.group(1))

    pet_rooms_match = re.search(r"pet\s+treatment\s+in\s+(\d+)\s+rooms?", desc, re.I)
    if pet_rooms_match: data["pet_rooms"] = int(pet_rooms_match.group(1))

    rugs_match = re.findall(r"(\d+(\.\d+)?)\s*sq\.?\s*ft", desc, re.I)
    if rugs_match and len(rugs_match) > 1:
        data["rugs"] = [float(r[0]) for r in rugs_match[1:]]

    time_match = re.search(r"(\d+(\.\d+)?)\s*hours?", desc, re.I)
    if time_match: data["hours"] = float(time_match.group(1))

    return data

def print_quote(breakdown, total, discount_summary, upsell_responses):
    print("\n" + "-" * 60)
    print(f"{'Service Description':<45}{'Price (USD)':>15}")
    print("-" * 60)
    for desc, price in breakdown:
        print(f"{desc:<45}${price:>14.2f}")
    print("-" * 60)
    print(f"{'GRAND TOTAL:':<45}${total:>14.2f}")
    print("-" * 60)
    print("\nDiscount summary:", discount_summary)
    print("\nUpsell Responses:")
    for q, r in upsell_responses.items():
        print(f"- {q} → {r}")

def main():
    print("Welcome to the Carpet Cleaning Quick Quote Calculator!")
    try:
        desc = input("Describe the job (or press Enter to answer step-by-step): ")
    except EOFError:
        desc = ""  # For Render or environments without live input

    data = parse_description(desc)

    # Ask for missing info
    data = ask_if_missing(data, "miles", "Client distance (miles): ", float)
    data = ask_if_missing(data, "sqft", "Total carpet area (sq ft): ", float)
    data = ask_if_missing(data, "large_items", "Number of large items: ", int)
    data = ask_if_missing(data, "floors", "Number of floors: ", int)
    data = ask_if_missing(data, "pet_rooms", "Pet treatment in how many rooms: ", int)
    if "rugs" not in data:
        rug_count = input("How many rugs?: ")
        if rug_count.strip():
            rugs = []
            for i in range(int(rug_count)):
                rugs.append(float(input(f"Size of rug {i+1} (sq ft): ")))
            data["rugs"] = rugs
    data = ask_if_missing(data, "hours", "Estimated hours for the job: ", float)

    # Pricing rules
    breakdown = []
    breakdown.append(("Base Price (Standard)", 140.00))
    breakdown.append(("Service Charge (Standard)", 25.00))

    extra_sqft = max(0, data["sqft"] - 500)
    if extra_sqft > 0:
        breakdown.append((f"Additional sq ft ({extra_sqft} × $0.30)", extra_sqft * 0.30))

    if data["floors"] > 1:
        breakdown.append((f"Difficulty Access ({data['floors']-1} extra floors)", (data["floors"] - 1) * 25))

    extra_time = max(0, data["hours"] - 2)  # First 2 hours included
    if extra_time > 0:
        breakdown.append((f"Extra cleaning time ({extra_time:.1f} hr × $25/hr)", extra_time * 25))

    if data["large_items"] > 0:
        breakdown.append((f"Large item manipulation (count={data['large_items']})", data["large_items"] * 25))

    if "rugs" in data and data["rugs"]:
        total_rug_area = sum(data["rugs"])
        breakdown.append((f"Area rug cleaning ({total_rug_area} sq ft × $4.00)", total_rug_area * 4.00))

    if data["pet_rooms"] > 0:
        breakdown.append((f"Pet odor treatment ({data['pet_rooms']} rooms × $75.00)", data["pet_rooms"] * 75.00))

    # Upsells
    stain_guard_rooms = input("Number of rooms for stain-guard (0 if none): ")
    if stain_guard_rooms.strip() and int(stain_guard_rooms) > 0:
        breakdown.append((f"Stain guard ({int(stain_guard_rooms)} rooms × $50.00)", int(stain_guard_rooms) * 50))

    membership_choice = input("Membership program (y=6mo / a=1yr / n=none): ").lower()
    if membership_choice == "y":
        breakdown.append(("6-Month Membership Program", 789.00))
    elif membership_choice == "a":
        breakdown.append(("1-Year Membership Program", 1479.00))

    # Bundle discount
    services = [d[0] for d in breakdown]
    discount_summary = ""
    total_price = sum(price for _, price in breakdown)
    if any("carpet" in s.lower() for s in services) and any("rugs" in s.lower() or "rug" in s.lower() for s in services) and any("stain guard" in s.lower() for s in services):
        discount = total_price * 0.10
        breakdown.append(("Bundle discount (10% off)", -discount))
        discount_summary += f"Bundle discount applied: 10% off, saving ${discount:.2f}. "

    # Additional discount
    extra_discount = input("Additional discount amount (leave blank if none): ")
    if extra_discount.strip():
        breakdown.append(("Additional discount", -float(extra_discount)))
        discount_summary += f"Additional discount applied: saving ${float(extra_discount):.2f}."

    # Upsell questions
    upsell_responses = {}
    uv_choice = input("Show visible stains with UV light? (y/n): ").lower()
    upsell_responses["UV light inspection"] = "Accepted" if uv_choice == "y" else "Declined"
    sofa_choice = input("Clean sofa as well? (y/n): ").lower()
    upsell_responses["Sofa cleaning"] = "Accepted" if sofa_choice == "y" else "Declined"

    # Final total
    final_total = sum(price for _, price in breakdown)

    # Print results in nice table
    print_quote(breakdown, final_total, discount_summary, upsell_responses)

if __name__ == "__main__":
    main()
