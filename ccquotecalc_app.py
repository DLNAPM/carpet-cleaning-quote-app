# ccquotecalc_app.py
from flask import Flask, request, jsonify, render_template_string
import os, re

app = Flask(__name__)

# Pricing constants (same as earlier)
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

# Parsing helpers (same rules)
def parse_description(desc, details):
    if not desc:
        return details
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
                if details.get('sqft') is None or v != details['sqft']:
                    details['rugs'].append(v)
    if 'first-time' in desc.lower() or 'first time' in desc.lower(): details['first_time'] = True
    if 'repeat' in desc.lower(): details['first_time'] = False
    return details

def calc_quote(details, stain_rooms=0, membership='n'):
    breakdown = []; total = 0.0
    breakdown.append(("Base Price (Standard)", BASE_PRICE)); total += BASE_PRICE
    breakdown.append(("Service Charge (Standard)", SERVICE_CHARGE)); total += SERVICE_CHARGE
    extra_sqft = max(0, details['sqft'] - 500)
    if extra_sqft > 0:
        c = extra_sqft * EXTRA_SQFT_RATE
        breakdown.append((f"Additional sq ft ({extra_sqft} × ${EXTRA_SQFT_RATE:.2f})", c)); total += c
    extra_floors = max(0, details['floors'] - 1)
    if extra_floors > 0:
        c = extra_floors * EXTRA_FLOOR_RATE
        breakdown.append((f"Difficulty Access ({extra_floors} extra floor)", c)); total += c
    extra_half_hours = max(0, (details['hours'] - 2) * 2)
    if extra_half_hours > 0:
        c = extra_half_hours * EXTRA_TIME_RATE
        breakdown.append((f"Extra cleaning time ({extra_half_hours} × 30min)", c)); total += c
    if details['large_items'] > 0:
        c = details['large_items'] * LARGE_ITEM_RATE
        breakdown.append((f"Large item manipulation (count={details['large_items']})", c)); total += c
    rug_total_sqft = sum(details.get('rugs', []))
    if rug_total_sqft > 0:
        c = rug_total_sqft * AREA_RUG_RATE
        breakdown.append((f"Area rug cleaning ({rug_total_sqft} sq ft × ${AREA_RUG_RATE:.2f})", c)); total += c
    if details['pet_rooms'] > 0:
        c = details['pet_rooms'] * PET_TREATMENT_RATE
        breakdown.append((f"Pet odor treatment ({details['pet_rooms']} rooms × ${PET_TREATMENT_RATE:.2f})", c)); total += c
    if stain_rooms > 0:
        c = stain_rooms * STAIN_GUARD_RATE
        breakdown.append((f"Stain guard ({stain_rooms} rooms × ${STAIN_GUARD_RATE:.2f})", c)); total += c
    if membership == 'y':
        breakdown.append(("6-Month Membership Program", MEMBERSHIP_6MO)); total += MEMBERSHIP_6MO
    elif membership == 'a':
        breakdown.append(("1-Year Membership Program", MEMBERSHIP_1YR)); total += MEMBERSHIP_1YR
    bundle_services = sum([rug_total_sqft > 0, stain_rooms > 0, details['sqft'] > 0])
    if bundle_services >= 3:
        bd = total * BUNDLE_DISCOUNT
        breakdown.append((f"Bundle discount ({BUNDLE_DISCOUNT*100:.0f}% off)", -bd)); total -= bd
    if details.get('discount', 0) > 0:
        breakdown.append(("Additional discount", -details['discount'])); total -= details['discount']
    return breakdown, total

def find_missing(details):
    miss = [f for f in REQUIRED_FIELDS if f not in details]
    return miss

# Simple HTML page for manual testing
FORM_HTML = """
<!doctype html>
<title>Carpet Quote</title>
<h3>Carpet Cleaning Quick Quote</h3>
<form method="post" action="/quote">
  <label>Description (natural language):</label><br>
  <textarea name="description" rows="4" cols="60">{{description}}</textarea><br>
  <small>Or submit JSON to /quote as application/json</small><br>
  <button type="submit">Get quote</button>
</form>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(FORM_HTML, description='')

@app.route('/quote', methods=['POST'])
def quote():
    # Accept JSON or form
    data = {}
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    # If a "details" dict provided, use it
    details = {}
    if isinstance(data.get('details'), dict):
        details.update(data['details'])

    # Parse description if present
    desc = data.get('description') or data.get('desc') or ""
    details = parse_description(desc, details)

    # Accept direct fields via JSON
    for key in REQUIRED_FIELDS:
        if key in data and key not in details:
            details[key] = data[key]

    # Normalize some fields
    if 'rugs' in details and isinstance(details['rugs'], str):
        try:
            details['rugs'] = [float(x.strip()) for x in details['rugs'].split(',') if x.strip()]
        except:
            details['rugs'] = []
    details.setdefault('rugs', [])
    details.setdefault('pet_rooms', 0)
    details.setdefault('large_items', 0)
    details.setdefault('floors', 1)
    details.setdefault('discount', 0.0)
    details.setdefault('hours', 2.0)
    details.setdefault('first_time', False)

    missing = find_missing(details)
    # If essential numeric fields are missing, return missing list
    if missing:
        return jsonify({
            "status": "need_more_info",
            "missing": missing,
            "message": "Provide the missing fields in JSON or include more in 'description'."
        }), 400

    # Extras
    stain_rooms = int(data.get('stain_rooms', 0))
    membership = data.get('membership', 'n')
    uv = data.get('uv_light', False)
    sofa = data.get('sofa_clean', False)

    breakdown, total = calc_quote(details, stain_rooms=stain_rooms, membership=membership)

    return jsonify({
        "status": "ok",
        "details": details,
        "breakdown": [{"name": n, "amount": a} for n,a in breakdown],
        "total": total,
        "upsells": {
            "uv_light": bool(uv),
            "sofa_clean": bool(sofa)
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
