import re

# --- Pricing Constants ---
BASE_PRICE = 140.00
SERVICE_CHARGE = 25.00
EXTRA_SQFT_RATE = 0.30
EXTRA_FLOOR_RATE = 25.00
EXTRA_TIME_RATE = 25.00
LARGE_ITEM_RATE = 25.00
AREA_RUG_RATE = 4.00
PET_TREATMENT_RATE = 75.00
STAIN_GUARD_RATE = 50.00
MEMBERSHIP_6MO = 799.00
MEMBERSHIP_1YR = 1479.00
BUNDLE_DISCOUNT = 0.10

REQUIRED_FIELDS = [
    'miles', 'sqft', 'pet_rooms', 'large_items',
    'rugs', 'floors', 'hours', 'discount', 'first_time'
]

# --- Parsing Helper ---
def extract_details(text, details):
    """Pull out any numbers or known facts from a free-text answer."""
    # Miles
    m = re.search(r'(\d+)\s*miles?', text)
    if m: details['miles'] = float(m.group(1))
    # Sq ft
    m = re.search(r'(\d+)\s*sq\s*ft', text)
    if m: details['sqft'] = float(m.group(1))
    # Pet rooms
    m = re.search(r'pet.*?(\d+)\s*room', text)
    if m: details['pet_rooms'] = int(m.group(1))
    # Large items
    m = re.search(r'(\d+)\s*large item', text)
    if m: details['large_items'] = int(m.group(1))
    # Floors
    m = re.search(r'(\d+)\s*floors?', text)
    if m: details['floors'] = int(m.group(1))
    # Hours
    m = re.search(r'(\d*\.?\d+)\s*hour', text)
    if m: details['hours'] = float(m.group(1))
    # Discount
    m = re.search(r'discount.*?\$?(\d*\.?\d+)', text)
    if m: details['discount'] = float(m.group(1))
    # Rugs
    if 'rug' in text.lower():
        sizes = re.findall(r'(\d*\.?\d+)\s*sq\s*ft', text)
        if sizes:
            if 'rugs' not in details: details['rugs'] = []
            for s in sizes:
                size_val = float(s)
                if 'sqft' not in details or size_val != details['sqft']:
                    details['rugs'].append(size_val)
    # First time / repeat
    if 'first-time' in text.lower(): details['first_time'] = True
    if 'repeat' in text.lower(): details['first_time'] = False
    return details

# --- Quote Calculation ---
def calc_quote(details, stain_rooms, membership, uv_light, sofa_clean):
    breakdown = []
    total = 0

    breakdown.append(("Base Price (Standard)", BASE_PRICE)); total += BASE_PRICE
    breakdown.append(("Service Charge (Standard)", SERVICE_CHARGE)); total += SERVICE_CHARGE

    extra_sqft = max(0, details['sqft'] - 500)
    if extra_sqft > 0:
        cost = extra_sqft * EXTRA_SQFT_RATE
        breakdown.append((f"Additional sq ft ({extra_sqft} × ${EXTRA_SQFT_RATE:.2f})", cost))
        total += cost

    extra_floors = max(0, details['floors'] - 1)
    if extra_floors > 0:
        cost = extra_floors * EXTRA_FLOOR_RATE
        breakdown.append((f"Difficulty Access ({extra_floors} extra floor)", cost))
        total += cost

    extra_half_hours = max(0, (details['hours'] - 2) * 2)
    if extra_half_hours > 0:
        cost = extra_half_hours * EXTRA_TIME_RATE
        breakdown.append((f"Extra cleaning time ({extra_half_hours} × 30min)", cost))
        total += cost

    if details['large_items'] > 0:
        cost = details['large_items'] * LARGE_ITEM_RATE
        breakdown.append((f"Large item manipulation (count={details['large_items']})", cost))
        total += cost

    rug_total_sqft = sum(details.get('rugs', []))
    if rug_total_sqft > 0:
        cost = rug_total_sqft * AREA_RUG_RATE
        breakdown.append((f"Area rug cleaning ({rug_total_sqft} sq ft × ${AREA_RUG_RATE:.2f})", cost))
        total += cost

    if details['pet_rooms'] > 0:
        cost = details['pet_rooms'] * PET_TREATMENT_RATE
        breakdown.append((f"Pet odor treatment ({details['pet_rooms']} rooms × ${PET_TREATMENT_RATE:.2f})", cost))
        total += cost

    if stain_rooms > 0:
        cost = stain_rooms * STAIN_GUARD_RATE
        breakdown.append((f"Stain guard ({stain_rooms} rooms × ${STAIN_GUARD_RATE:.2f})", cost))
        total += cost

    if membership == 'y':
        breakdown.append(("6-Month Membership Program", MEMBERSHIP_6MO))
        total += MEMBERSHIP_6MO
    elif membership == 'a':
        breakdown.append(("1-Year Membership Program", MEMBERSHIP_1YR))
        total += MEMBERSHIP_1YR

    bundle_services = sum([
        rug_total_sqft > 0,
        stain_rooms > 0,
        details['sqft'] > 0
    ])
    if bundle_services >= 3:
        discount_amt = total * BUNDLE_DISCOUNT
        breakdown.append((f"Bundle discount ({BUNDLE_DISCOUNT*100:.0f}% off)", -discount_amt))
        total -= discount_amt

    if details['discount'] > 0:
        breakdown.append(("Additional discount", -details['discount']))
        total -= details['discount']

    return breakdown, total

# --- Continuous Listening Conversation ---
def conversation():
    details = {}
    print("Hi! Let’s build a carpet cleaning quote.")
    print("Tell me details in any order — I’ll keep listening until I have everything.")
    print("When you're done, say 'done'.")

    while True:
        # Check if we have all required fields
        missing = [f for f in REQUIRED_FIELDS if f not in details]
        if not missing:
            break

        # Ask about something missing
        if missing:
            # If this is the first turn, just ask open-ended
            if not details:
                user_input = input("You: ")
            else:
                # Ask specifically about the next missing detail
                if missing[0] == 'miles':
                    user_input = input("How far is the client in miles? ")
                elif missing[0] == 'sqft':
                    user_input = input("How many square feet of carpet? ")
                elif missing[0] == 'pet_rooms':
                    user_input = input("How many rooms need pet treatment? ")
                elif missing[0] == 'large_items':
                    user_input = input("How many large items to move (>50 lbs)? ")
                elif missing[0] == 'rugs':
                    user_input = input("Any rugs to clean? Give sizes in sq ft (comma separated) or 'no': ")
                    if user_input.lower().startswith('n'):
                        details['rugs'] = []
                        continue
                elif missing[0] == 'floors':
                    user_input = input("How many floors will we clean? ")
                elif missing[0] == 'hours':
                    user_input = input("Total estimated hours for the job? ")
                elif missing[0] == 'discount':
                    user_input = input("Any discount amount in dollars? (0 if none) ")
                elif missing[0] == 'first_time':
                    user_input = input("Is this a first-time customer? (y/n): ")

            if user_input.lower() == 'done':
                break

            details = extract_details(user_input, details)

    # Extras
    stain_rooms = int(input("How many rooms want stain-guard? (0 if none) ") or "0")
    membership = input("Membership program? (y=6mo, a=1yr, n=none): ").lower()
    uv_light = input("Would they like a UV light check? (y/n): ").lower() == 'y'
    sofa_clean = input("Shall we also clean the sofa? (y/n): ").lower() == 'y'

    # Show quote
    breakdown, total = calc_quote(details, stain_rooms, membership, uv_light, sofa_clean)

    print("\nDetailed Estimate:")
    print("-" * 50)
    for name, cost in breakdown:
        print(f"{name:<45} ${cost:,.2f}")
    print("-" * 50)
    print(f"Grand Total: {total:>35,.2f}")

    print("\nUpsell Responses:")
    print(f"- UV light check → {'Accepted' if uv_light else 'Declined'}")
    print(f"- Sofa cleaning → {'Accepted' if sofa_clean else 'Declined'}")

# Run
if __name__ == "__main__":
    conversation()
