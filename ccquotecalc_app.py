import re

# --- Pricing Constants ---
BASE_PRICE = 140.00
SERVICE_CHARGE = 25.00
EXTRA_SQFT_RATE = 0.30  # per sq ft over 500
EXTRA_FLOOR_RATE = 25.00  # per floor after first
EXTRA_TIME_RATE = 25.00  # per 30 min
LARGE_ITEM_RATE = 25.00  # per item
AREA_RUG_RATE = 4.00  # per sq ft
PET_TREATMENT_RATE = 75.00  # per room
STAIN_GUARD_RATE = 50.00  # per room
MEMBERSHIP_6MO = 799.00
MEMBERSHIP_1YR = 1479.00
BUNDLE_DISCOUNT = 0.10  # 10%

# --- Helper ---
def parse_initial_description(desc):
    """Extract details from a natural language job description."""
    details = {}
    if not desc.strip():
        return details
    # Simple regex searches for numbers
    match = re.search(r'(\d+)\s*miles', desc)
    if match: details['miles'] = float(match.group(1))
    match = re.search(r'(\d+)\s*sq\s*ft', desc)
    if match: details['sqft'] = float(match.group(1))
    match = re.search(r'pet treatment.*?(\d+)\s*room', desc)
    if match: details['pet_rooms'] = int(match.group(1))
    match = re.search(r'(\d+)\s*large item', desc)
    if match: details['large_items'] = int(match.group(1))
    match = re.search(r'(\d+)\s*floors?', desc)
    if match: details['floors'] = int(match.group(1))
    match = re.search(r'(\d*\.?\d+)\s*hour', desc)
    if match: details['hours'] = float(match.group(1))
    match = re.search(r'discount.*?\$?(\d*\.?\d+)', desc)
    if match: details['discount'] = float(match.group(1))
    match = re.search(r'first[- ]time', desc, re.I)
    if match: details['first_time'] = True
    match = re.search(r'repeat client', desc, re.I)
    if match: details['first_time'] = False
    return details

def ask_if_missing(details, key, prompt, cast_type=str, default=None):
    if key not in details:
        val = input(prompt)
        if val.strip():
            details[key] = cast_type(val)
        elif default is not None:
            details[key] = default

# --- Main ---
print("Welcome to the Carpet Cleaning Quick Quote Calculator!")
print("You can describe the job (e.g., 'This client is 50 miles away, has 880 sq ft...').")
print("If you don't want to provide a description, just press Enter and we'll ask step-by-step.")

desc = input("Describe the job: ")
details = parse_initial_description(desc)

# Ask missing details
ask_if_missing(details, 'miles', "How many miles away is the client? ", float)
ask_if_missing(details, 'sqft', "Total carpet square footage? ", float)
ask_if_missing(details, 'pet_rooms', "Number of rooms for pet treatment (0 if none): ", int, 0)
ask_if_missing(details, 'large_items', "Number of large items to move (>50 lb)? ", int, 0)

# Rugs
if 'rugs' not in details:
    rugs = []
    while True:
        size = input("Enter rug size in sq ft (or blank to finish): ")
        if not size.strip():
            break
        rugs.append(float(size))
    details['rugs'] = rugs

ask_if_missing(details, 'floors', "Number of floors to clean? ", int, 1)
ask_if_missing(details, 'hours', "Estimated total job time (hours)? ", float)
ask_if_missing(details, 'discount', "Discount amount (0 if none)? ", float, 0.0)
ask_if_missing(details, 'first_time', "Is this a first-time customer? (y/n): ",
               lambda x: x.lower().startswith('y'))

# Extra services
stain_rooms = input("Number of rooms for stain-guard/protection (0 if none): ")
stain_rooms = int(stain_rooms) if stain_rooms.strip() else 0
membership = input("Membership? (y=6mo, a=1yr, n=none): ").lower()

# Upsell questions
uv_light = input("Show visible stains with UV light? (y/n): ").lower() == 'y'
sofa_clean = input("Clean sofa while here? (y/n): ").lower() == 'y'

# --- Calculate ---
total = 0
breakdown = []

# Base & service
breakdown.append(("Base Price (Standard)", BASE_PRICE))
total += BASE_PRICE
breakdown.append(("Service Charge (Standard)", SERVICE_CHARGE))
total += SERVICE_CHARGE

# Extra sq ft
extra_sqft = max(0, details['sqft'] - 500)
if extra_sqft > 0:
    cost = extra_sqft * EXTRA_SQFT_RATE
    breakdown.append((f"Additional sq ft ({extra_sqft} × ${EXTRA_SQFT_RATE:.2f})", cost))
    total += cost

# Floors
extra_floors = max(0, details['floors'] - 1)
if extra_floors > 0:
    cost = extra_floors * EXTRA_FLOOR_RATE
    breakdown.append((f"Difficulty Access ({extra_floors} extra floor)", cost))
    total += cost

# Extra time (beyond 2 hours)
extra_half_hours = max(0, (details['hours'] - 2) * 2)
if extra_half_hours > 0:
    cost = extra_half_hours * EXTRA_TIME_RATE
    breakdown.append((f"Extra cleaning time ({extra_half_hours} × 30min)", cost))
    total += cost

# Large items
if details['large_items'] > 0:
    cost = details['large_items'] * LARGE_ITEM_RATE
    breakdown.append((f"Large item manipulation (count={details['large_items']})", cost))
    total += cost

# Rugs
rug_total_sqft = sum(details['rugs'])
if rug_total_sqft > 0:
    cost = rug_total_sqft * AREA_RUG_RATE
    breakdown.append((f"Area rug cleaning ({rug_total_sqft} sq ft × ${AREA_RUG_RATE:.2f})", cost))
    total += cost

# Pet treatment
if details['pet_rooms'] > 0:
    cost = details['pet_rooms'] * PET_TREATMENT_RATE
    breakdown.append((f"Pet odor treatment ({details['pet_rooms']} rooms × ${PET_TREATMENT_RATE:.2f})", cost))
    total += cost

# Stain guard
if stain_rooms > 0:
    cost = stain_rooms * STAIN_GUARD_RATE
    breakdown.append((f"Stain guard ({stain_rooms} rooms × ${STAIN_GUARD_RATE:.2f})", cost))
    total += cost

# Membership
if membership == 'y':
    breakdown.append(("6-Month Membership Program", MEMBERSHIP_6MO))
    total += MEMBERSHIP_6MO
elif membership == 'a':
    breakdown.append(("1-Year Membership Program", MEMBERSHIP_1YR))
    total += MEMBERSHIP_1YR

# Bundle discount
bundle_services = sum([
    rug_total_sqft > 0,
    stain_rooms > 0,
    details['sqft'] > 0
])
bundle_discount_amount = 0
if bundle_services >= 3:
    bundle_discount_amount = total * BUNDLE_DISCOUNT
    breakdown.append((f"Bundle discount ({BUNDLE_DISCOUNT*100:.0f}% off)", -bundle_discount_amount))
    total -= bundle_discount_amount

# Additional discount
if details['discount'] > 0:
    breakdown.append(("Additional discount", -details['discount']))
    total -= details['discount']

# --- Output ---
print("\nDetailed Estimate:")
print("-" * 50)
for name, cost in breakdown:
    print(f"{name:<45} ${cost:,.2f}")
print("-" * 50)
print(f"Grand Total: {total:>35,.2f}")

# Upsell responses
print("\nUpsell Responses:")
print(f"- Show visible stains or odors with UV light → {'Accepted' if uv_light else 'Declined'}")
print(f"- Clean sofa while here → {'Accepted' if sofa_clean else 'Declined'}")
