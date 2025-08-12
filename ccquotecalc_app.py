# ccquotecalc_cli.py
import re
import os
import sys
import json
import argparse

# Pricing constants (same as before)
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

# Parsing helpers
def parse_description(desc, details):
    if not desc:
        return details
    # same pattern matches as previous versions
    m = re.search(r'(\d+)\s*miles?', desc)
    if m: details['miles'] = float(m.group(1))
    m = re.search(r'(\d+)\s*sq\s*ft', desc)
    if m: details['sqft'] = float(m.group(1))
    m = re.search(r'pet.*?(\d+)\s*room', desc)
    if m: details['pet_rooms'] = int(m.group(1))
    m = re.search(r'(\d+)\s*large item', desc)
    if m: details['large_items'] = int(m.group(1))
    m = re.search(r'(\d+)\s*floors?', desc)
    if m: details['floors'] = int(m.group(1))
    m = re.search(r'(\d*\.?\d+)\s*hour', desc)
    if m: details['hours'] = float(m.group(1))
    m = re.search(r'discount.*?\$?(\d*\.?\d+)', desc)
    if m: details['discount'] = float(m.group(1))
    if 'rug' in desc.lower():
        sizes = re.findall(r'(\d*\.?\d+)\s*sq\s*ft', desc)
        if sizes:
            details.setdefault('rugs', [])
            for s in sizes:
                v = float(s)
                # avoid matching main carpet sqft twice
                if details.get('sqft') is None or v != details['sqft']:
                    details['rugs'].append(v)
    if 'first-time' in desc.lower() or 'first time' in desc.lower(): details['first_time'] = True
    if 'repeat' in desc.lower(): details['first_time'] = False
    return details

def calc_quote(details, stain_rooms=0, membership='n'):
    breakdown = []
    total = 0.0
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
        breakdown.append(("6-Month Membership Program", MEMBERSHIP_6MO)); total += MEMBERSHIP_6MO
    elif membership == 'a':
        breakdown.append(("1-Year Membership Program", MEMBERSHIP_1YR)); total += MEMBERSHIP_1YR

    bundle_services = sum([rug_total_sqft > 0, stain_rooms > 0, details['sqft'] > 0])
    if bundle_services >= 3:
        bd = total * BUNDLE_DISCOUNT
        breakdown.append((f"Bundle discount ({BUNDLE_DISCOUNT*100:.0f}% off)", -bd)); total -= bd

    if details['discount'] > 0:
        breakdown.append(("Additional discount", -details['discount'])); total -= details['discount']

    return breakdown, total

def missing_fields(details):
    return [f for f in REQUIRED_FIELDS if f not in details]

def load_json_file(path):
    with open(path, 'r') as f:
        return json.load(f)

def pretty_print_quote(breakdown, total):
    print("\nDetailed Estimate:")
    print("-" * 50)
    for name, cost in breakdown:
        print(f"{name:<45} ${cost:,.2f}")
    print("-" * 50)
    print(f"Grand Total: {total:>35,.2f}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--desc', help='Job description (natural language)')
    parser.add_argument('--json', help='Path to JSON file containing "details" object')
    parser.add_argument('--stain_rooms', type=int, default=0)
    parser.add_argument('--membership', choices=['y','a','n'], default='n')
    args = parser.parse_args()

    details = {}

    # Priorities: CLI desc -> env JOB_DESC -> JSON file -> interactive
    desc = args.desc or os.environ.get('JOB_DESC')
    if args.json:
        obj = load_json_file(args.json)
        details.update(obj.get('details', obj))
    if desc:
        details = parse_description(desc, details)

    # If interactive (tty) continue conversation-like (keeps original behavior)
    if sys.stdin.isatty():
        # interactive flow (short)
        if not details:
            raw = input("Describe the job (or press Enter to be asked step-by-step): ")
            details = parse_description(raw, details)
        # ask missing fields interactively
        for field in REQUIRED_FIELDS:
            if field in details:
                continue
            if field == 'rugs':
                raw = input("Any rugs to clean? (enter sizes comma separated or blank for none): ").strip()
                if raw:
                    details['rugs'] = [float(s.strip()) for s in raw.split(',') if s.strip()]
                else:
                    details['rugs'] = []
            elif field == 'first_time':
                v = input("First-time customer? (y/n): ").lower().strip()
                details['first_time'] = v.startswith('y')
            else:
                raw = input(f"{field}? ").strip()
                if raw == '':
                    # set safe defaults
                    if field in ('pet_rooms','large_items','floors'):
                        details[field] = 0 if field != 'floors' else 1
                    elif field == 'discount':
                        details[field] = 0.0
                    else:
                        # try to parse
                        try:
                            details[field] = float(raw)
                        except:
                            details[field] = 0
                else:
                    # try best cast: int or float
                    if field in ('pet_rooms','large_items','floors'):
                        details[field] = int(float(raw))
                    elif field == 'rugs':
                        details['rugs'] = [float(s.strip()) for s in raw.split(',') if s.strip()]
                    elif field == 'first_time':
                        details['first_time'] = raw.lower().startswith('y')
                    elif field == 'discount':
                        details['discount'] = float(raw)
                    else:
                        details[field] = float(raw)
    else:
        # Non-interactive: ensure we have at least basic details or explain missing ones
        if not details:
            print("Non-interactive run and no description provided. Provide --desc or set JOB_DESC env var or use --json.")
            print("Example: export JOB_DESC=\"43 miles away, 599 sq ft, pet treatment in 3 rooms, 2 large items, rugs 18,30.5,8\"")
            sys.exit(2)
        # Fill missing fields with safe defaults where logical
        for f in REQUIRED_FIELDS:
            if f not in details:
                if f == 'rugs':
                    details['rugs'] = []
                elif f == 'floors':
                    details['floors'] = 1
                elif f in ('pet_rooms','large_items'):
                    details[f] = 0
                elif f == 'discount':
                    details[f] = 0.0
                elif f == 'first_time':
                    details[f] = False
                else:
                    # leave sqft and miles required when possible
                    pass

    # Validate mandatory numeric fields
    if 'sqft' not in details or 'miles' not in details:
        print("Missing required numeric fields: ", [f for f in ('sqft','miles') if f not in details])
        print("Provide them via --desc or JOB_DESC or --json.")
        sys.exit(3)

    breakdown, total = calc_quote(details, stain_rooms=args.stain_rooms, membership=args.membership)
    pretty_print_quote(breakdown, total)

if __name__ == "__main__":
    main()
