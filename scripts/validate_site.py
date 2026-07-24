from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "site-data.json").read_text(encoding="utf-8"))
HTML = (ROOT / "index.html").read_text(encoding="utf-8")

errors: list[str] = []
IGNORED_PARTS = {".git", "qa", "node_modules", "__pycache__"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".eps"}

APPROVED_LOGOS = {
    "assets/brand/LAAA_Team_Blue.png": {
        "sha256": "EBCED402DEE39F41C25DA2B2CF7124D1932A45DF95754675CC79E4658BF9A6D2",
        "bytes": 31373,
        "width": 1651,
        "height": 600,
        "slot": "header",
        "variant": "blue",
    },
    "assets/brand/LAAA_Team_White.png": {
        "sha256": "40439C1B03B8132B2E09832258CA22BC04B0F18F3796537C43F45F0FEF68E2F5",
        "bytes": 28342,
        "width": 1651,
        "height": 600,
        "slot": "footer",
        "variant": "white",
    },
}


def png_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()[:24]
    if len(payload) != 24 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise ValueError(f"Invalid PNG header: {path}")
    return struct.unpack(">II", payload[16:24])


def repository_bytes(path: Path) -> bytes:
    """Return bytes as Git stores them under `* text=auto eol=lf`."""
    payload = path.read_bytes()
    if path.suffix.lower() not in BINARY_SUFFIXES and b"\0" not in payload[:8192]:
        return payload.replace(b"\r\n", b"\n")
    return payload


for relative, approved in APPROVED_LOGOS.items():
    logo_path = ROOT / relative
    if not logo_path.exists():
        errors.append(f"Missing approved logo: {relative}")
        continue
    digest = hashlib.sha256(repository_bytes(logo_path)).hexdigest().upper()
    if digest != approved["sha256"]:
        errors.append(f"Logo hash mismatch: {relative}")
    if logo_path.stat().st_size != approved["bytes"]:
        errors.append(f"Logo byte-count mismatch: {relative}")
    try:
        if png_dimensions(logo_path) != (approved["width"], approved["height"]):
            errors.append(f"Logo dimensions mismatch: {relative}")
    except ValueError as exc:
        errors.append(str(exc))

    slot_pattern = re.compile(
        rf'<span[^>]*data-laaa-brand-slot="{approved["slot"]}"[^>]*'
        rf'data-logo-variant="{approved["variant"]}"[^>]*>\s*'
        rf'<img[^>]*src="{re.escape(relative)}"[^>]*>\s*</span>',
        re.IGNORECASE,
    )
    if not slot_pattern.search(HTML):
        errors.append(f"Approved {approved['slot']} brand slot is missing or malformed")

for slot in re.findall(r'<span[^>]*data-laaa-brand-slot="[^"]+"[^>]*>.*?</span>', HTML, re.I | re.S):
    if re.search(r'<(?:svg|canvas)\b|data:image|style=', slot, re.I):
        errors.append("Brand slot contains a prohibited synthesized or inline mark")
    visible = re.sub(r"<[^>]+>", "", slot).strip()
    if visible:
        errors.append("Brand slot contains styled text instead of an approved image")

for candidate in ROOT.rglob("*"):
    if not candidate.is_file() or any(part in IGNORED_PARTS for part in candidate.parts):
        continue
    relative = candidate.relative_to(ROOT).as_posix()
    if re.search(r"(?:laaa|logo|brand)", candidate.name, re.I) and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}:
        if relative not in APPROVED_LOGOS:
            errors.append(f"Unknown logo-like asset: {relative}")
price = DATA["meta"]["offering_price"]
current_monthly_rent = sum(unit["current_rent"] for unit in DATA["units"])
proforma_monthly_rent = sum(unit["market_rent"] for unit in DATA["units"])
monthly_rent_upside = proforma_monthly_rent - current_monthly_rent
current_gsr = current_monthly_rent * 12
proforma_gsr = proforma_monthly_rent * 12
current_expenses = sum(item["current"] for item in DATA["expenses"])
proforma_expenses = sum(item["pro_forma"] for item in DATA["expenses"])
current_noi = current_gsr - current_expenses
proforma_noi = proforma_gsr - proforma_expenses

expected = {
    "price": 1095000,
    "current_gsr": 70800,
    "proforma_gsr": 81420,
    "current_expenses": 24047,
    "proforma_expenses": 24047,
    "current_noi": 46753,
    "proforma_noi": 57373,
}
actual = {
    "price": price,
    "current_gsr": current_gsr,
    "proforma_gsr": proforma_gsr,
    "current_expenses": current_expenses,
    "proforma_expenses": proforma_expenses,
    "current_noi": current_noi,
    "proforma_noi": proforma_noi,
}
for key, value in expected.items():
    if actual[key] != value:
        errors.append(f"{key}: expected {value}, got {actual[key]}")

financial_source = DATA["meta"].get("financial_source", {})
expected_source_decisions = {
    "file": "24513 Walnut St Model (Glen approved).xlsm",
    "file_size": 1208338,
    "unit_sf": [728, 728, 908],
    "repairs_and_maintenance": 1800,
    "publish_financing": True,
}
for key, value in expected_source_decisions.items():
    if financial_source.get(key) != value:
        errors.append(f"Financial source decision {key}: expected {value}, got {financial_source.get(key)}")

required_strings = [
    "$1,095,000", "$70,800", "$81,420", "$46,753", "$57,373",
    "4.27%", "5.24%", "15.47x", "13.45x", "CA 01962976", "CA 01905352",
    "$821,250", "$273,750", "6.50%", "30 Years", "0.75x", "0.92x",
    "noindex, nofollow, noarchive",
    "The LAAA Team of Marcus &amp; Millichap is proud to present", "Same rent rules",
    "Three-Unit Residential Investment in Old Town Newhall", "228,430",
    "Pro Forma Below Survey Benchmarks", "AB 1482 Rent Framework",
    "Please do not disturb occupants or enter without a confirmed appointment"
]
for value in required_strings:
    if value not in HTML:
        errors.append(f"Missing required rendered value: {value}")

for stale in [
    "$1,249,000", "3.99%", "30 trains", "Why the LAAA Team", "expected sale", "price reduction",
    "Focus the evidence", "Same rent regime", "Main Street sample", "Fourth Street", "Chestnut Street",
    "Interactive Prototype", "buyers can audit", "responsive screen", "continuous table",
    "invented financing", "evidence tool", "false precision", "no unapproved assumption",
    "until Glen approves", "Financing assumptions forthcoming.",
    "229,159", "approximately 788 square feet", "788 SF per residence",
    "three one-car garages", "1 detached and 2 attached",
    "credible three-unit pricing", "meaningful differences",
    "DEMO_MAP_ID",
]:
    if stale.lower() in HTML.lower():
        errors.append(f"Stale or seller-facing phrase present: {stale}")

for image in DATA["gallery"]:
    if not (ROOT / image["src"]).exists():
        errors.append(f"Missing image: {image['src']}")

expected_unit_areas = [728, 728, 908]
actual_unit_areas = [unit.get("unit_sf") for unit in DATA["units"]]
if actual_unit_areas != expected_unit_areas:
    errors.append(f"Unit areas: expected {expected_unit_areas}, got {actual_unit_areas}")

financing = DATA.get("financing", {})
expected_financing = {
    "loan_amount": 821250,
    "down_payment": 273750,
    "ltv": 0.75,
    "interest_rate": 0.065,
    "amortization_years": 30,
    "maturity_year": 2056,
}
for key, value in expected_financing.items():
    if financing.get(key) != value:
        errors.append(f"Financing {key}: expected {value}, got {financing.get(key)}")
annual_debt_service = financing.get("annual_debt_service", 0)
for basis, noi in [("current", current_noi), ("pro_forma", proforma_noi)]:
    result = financing.get(basis, {})
    expected_cash_flow = noi - annual_debt_service
    expected_coc = expected_cash_flow / financing.get("down_payment", 1)
    expected_dscr = noi / annual_debt_service if annual_debt_service else 0
    expected_total_return = expected_cash_flow + result.get("principal_reduction", 0)
    expected_total_return_rate = expected_total_return / financing.get("down_payment", 1)
    for label, calculated, reported in [
        ("cash_flow_after_debt_service", expected_cash_flow, result.get("cash_flow_after_debt_service")),
        ("cash_on_cash", expected_coc, result.get("cash_on_cash")),
        ("dscr", expected_dscr, result.get("dscr")),
        ("total_return", expected_total_return, result.get("total_return")),
        ("total_return_rate", expected_total_return_rate, result.get("total_return_rate")),
    ]:
        if reported is None or abs(calculated - reported) > 0.01:
            errors.append(f"Financing {basis} {label}: expected {calculated}, got {reported}")
for unit in DATA["units"]:
    current_psf = f"${unit['current_rent'] / unit['unit_sf']:.2f}"
    proforma_psf = f"${unit['market_rent'] / unit['unit_sf']:.2f}"
    if current_psf not in HTML or proforma_psf not in HTML:
        errors.append(f"Missing calculated rent/SF for {unit['label']}: {current_psf} / {proforma_psf}")
rent_footer = re.search(r'<table class="rent-roll-table">.*?<tfoot>(.*?)</tfoot>', HTML, re.S)
expected_rent_footer_values = [
    f"${current_monthly_rent:,.0f}",
    f"${proforma_monthly_rent:,.0f}",
    f"${monthly_rent_upside:,.0f}",
    f"{monthly_rent_upside / current_monthly_rent * 100:.1f}%",
]
if not rent_footer:
    errors.append("Rent roll footer is missing")
elif any(value not in rent_footer.group(1) for value in expected_rent_footer_values):
    errors.append(f"Rent roll footer totals do not match source data: {expected_rent_footer_values}")

for narrative in ["investment_overview", "location_overview"]:
    paragraphs = DATA.get(narrative, [])
    if len(paragraphs) != 3:
        errors.append(f"{narrative} must contain exactly three paragraphs")
    if any(len(paragraph.split()) > 80 for paragraph in paragraphs):
        errors.append(f"{narrative} contains a paragraph over 80 words")
    if sum(len(paragraph.split()) for paragraph in paragraphs) > 240:
        errors.append(f"{narrative} exceeds 240 words")
if not DATA.get("investment_overview", [""])[0].startswith("The LAAA Team of Marcus & Millichap is proud to present"):
    errors.append("Investment Overview opening is not canonical")
if len(DATA.get("investment_highlights", [])) not in {5, 6}:
    errors.append("Investment highlights must contain five or six items")
for item in DATA.get("investment_highlights", []):
    if len(item.get("headline", "").split()) > 8 or len(item.get("detail", "").split()) > 40:
        errors.append(f"Investment highlight exceeds word limit: {item.get('headline')}")

diligence_cards = re.findall(r'<div class="container diligence-grid">(.*?)</div>', HTML, re.S)
if len(diligence_cards) != 1 or len(re.findall(r"<article>", diligence_cards[0])) != 8:
    errors.append("Buyer Due Diligence must render exactly eight verification categories")

if '<meta name="google-maps-browser-map-id" content="">' not in HTML:
    errors.append("Blank project-owned Google Maps Map ID configuration hook is missing")

rendered_ids = re.findall(r"""\bid=["']([^"']+)["']""", HTML, re.I)
duplicate_ids = sorted({value for value in rendered_ids if rendered_ids.count(value) > 1})
if duplicate_ids:
    errors.append(f"Rendered HTML contains duplicate IDs: {duplicate_ids}")

if len(DATA["sale_comps"]) != 6:
    errors.append(f"Expected six sale comparables, got {len(DATA['sale_comps'])}")
comp_ids = [comp.get("id") for comp in DATA["sale_comps"]]
if len(set(comp_ids)) != len(comp_ids):
    errors.append("Sale comparable IDs must be unique")
for comp in DATA["sale_comps"]:
    for required in ["id", "map_label", "latitude", "longitude", "image", "map_url", "verdict", "occupancy", "condition", "strengths", "cautions", "distance", "rent_rules", "source", "price", "units", "sf", "lot_sf", "ppu", "ppsf", "year_built"]:
        if not comp.get(required):
            errors.append(f"Sale comparable {comp.get('address', '(unknown)')} lacks {required}")
    if comp.get("image") and not (ROOT / comp["image"]).exists():
        errors.append(f"Missing sale comparable image: {comp['image']}")
    unit_match = re.match(r"(\d+)", str(comp.get("units", "")))
    if unit_match and abs(comp["ppu"] - round(comp["price"] / int(unit_match.group(1)))) > 1:
        errors.append(f"Price per unit does not reconcile for {comp['address']}")
    if abs(comp["ppsf"] - round(comp["price"] / comp["sf"])) > 1:
        errors.append(f"Price per square foot does not reconcile for {comp['address']}")
if not DATA["property"].get("map_url"):
    errors.append("Subject property Google Maps action is missing")

subject_ppu = round(price / DATA["property"]["units"])
subject_ppsf = price / DATA["property"]["building_sf"]
for rendered in [f"${subject_ppu:,.0f}", f"${subject_ppsf:,.0f}"]:
    if rendered not in HTML:
        errors.append(f"Missing calculated subject comparison metric: {rendered}")

analysis = DATA.get("comparables_analysis", {})
for required in ["sale_conclusion", "rent_conclusion", "integrated_conclusion"]:
    if not analysis.get(required):
        errors.append(f"Missing comparables analysis narrative: {required}")

rent_evidence = DATA.get("rent_evidence", [])
if len(rent_evidence) != 3:
    errors.append(f"Expected two surveyed rent segments and one achieved-rent cross-check, got {len(rent_evidence)}")
else:
    expected_rents = {
        "1BR apartments": (15, 2093, 2210, 2195),
        "2BR apartments": (20, 2493, 3295, 2295),
    }
    for row in rent_evidence:
        if row["segment"] not in expected_rents:
            continue
        expected_sample, expected_p25, expected_median, expected_selected = expected_rents[row["segment"]]
        if str(expected_sample) not in row["sample"] or (row["percentile_25"], row["median"], row["selected"]) != (expected_p25, expected_median, expected_selected):
            errors.append(f"Rent evidence changed for {row['segment']}")

for required_map in ["map-newhall.jpg", "map-transit.jpg", "map-subject-satellite.jpg", "map-sale-comps.jpg", "walnut-street-view.jpg"]:
    if not (ROOT / "assets" / "images" / required_map).exists():
        errors.append(f"Missing locally committed map: {required_map}")
for required_comp in [
    "25252 Atwood Blvd", "1237 Coronel Street", "10427 Oro Vista Avenue",
    "10030 Pinewood Avenue", "11344 Santol Drive", "216 Harding Avenue",
]:
    if required_comp not in HTML:
        errors.append(f"Missing rendered sale comparable: {required_comp}")

for contact in DATA.get("contacts", []):
    if not (ROOT / contact.get("image", "")).exists():
        errors.append(f"Missing listing-agent headshot: {contact.get('name')}")
    for value in [contact.get("name"), contact.get("title"), contact.get("phone"), contact.get("email"), contact.get("license")]:
        if value and value not in HTML:
            errors.append(f"Missing rendered contact value: {value}")

for required_markup in [
    "data-fin-basis=\"total\"", "data-fin-basis=\"unit\"", "data-fin-basis=\"sf\"",
    "class=\"financial-overview-grid\"", "class=\"financial-ledger financial-expense-ledger\"",
    "financial-visuals", "class=\"rent-roll-groups\"", "class=\"rent-roll-mobile-head\"",
    "class=\"financial-ledger financial-expense-summary-ledger\"", "class='financial-mobile-panel'",
    "class=\"financial-notes\"", "class=\"container financial-assumptions\"",
    "<abbr title='Gross Scheduled Rent'>GSR</abbr>", "<abbr title='Net Operating Income'>NOI</abbr>",
    "<abbr title='Repairs and Maintenance'>R&amp;M</abbr>", "<abbr title='General and Administrative'>G&amp;A</abbr>",
    "<abbr title='Debt Service Coverage Ratio'>DSCR</abbr>", "<abbr title=\"Per Square Foot\">/ SF</abbr>",
    "class=\"financial-mini-table financial-financing-table\"",
    "data-comp-view=\"list\"", "data-comp-view=\"map\"", "data-location-view=\"district\"",
    "data-location-view=\"satellite\"", "data-location-view=\"transit\"", "data-location-view=\"street\"",
    "data-location-panel=\"street\"", "assets/images/walnut-street-view.jpg",
    "Street-level view of the Walnut Street frontage", "Open Interactive Street View in Google Maps",
    "data-google-map=\"location\"", "data-google-map=\"comps\"", "data-google-map=\"rents\"", "id=\"map-config\"",
    "data-map-fallback=\"rents\"", "data-comp-map-type=\"roadmap\"", "data-comp-map-type=\"satellite\"",
    "data-comp-metric=\"price\"", "data-comp-metric=\"ppu\"", "data-comp-metric=\"ppsf\"",
    "data-comp-metric-panel='price'", "data-comp-metric-panel='ppu'", "data-comp-metric-panel='ppsf'",
    "class='subject-baseline'", "class='subject-baseline-strip'", "class=\"comp-selected-stack\"", "class=\"rent-benchmark-cards\"",
    "class=\"map-pin pin-6\" style=\"--x:51%;--y:43%\"",
    "table-scroll-cue", "assets/images/glen-scher.jpg", "assets/images/filip-niculete.jpg",
]:
    if required_markup not in HTML:
        errors.append(f"Missing required responsive feature: {required_markup}")

if HTML.count("class='financial-mobile-panel'") != 4:
    errors.append("Mobile financial presentation must contain four expandable sections")
if HTML.count("class='financial-visual-panel'") != 2:
    errors.append("Financial presentation must contain exactly two restrained analytical visuals")
if "class='row-note'" in HTML:
    errors.append("Legacy per-row information widgets remain in the financial presentation")

for verbose_financial_header in ["Pro Forma / Unit", "Pro Forma / SF"]:
    if verbose_financial_header in HTML:
        errors.append(f"Verbose financial header must use the compact label standard: {verbose_financial_header}")

if re.search(r'''(?:src|poster)=["']https?://''', HTML, re.I) or re.search(r"url\(\s*[\"']?https?://", HTML, re.I):
    errors.append("Runtime assets must remain local; external URLs may be links only")

contract = json.loads((ROOT / ".laaa-marketing.json").read_text(encoding="utf-8"))
map_dependencies = [item for item in contract.get("externalDependencies", []) if item.get("url") == "https://maps.googleapis.com/maps/api/js"]
if len(map_dependencies) != 1:
    errors.append("Google Maps JavaScript API must be declared exactly once")
elif set(map_dependencies[0].get("runtimeOrigins", [])) != {"https://maps.googleapis.com", "https://maps.gstatic.com"}:
    errors.append("Google Maps runtime origins are incomplete")
map_runtime = (ROOT / "assets" / "site.js").read_text(encoding="utf-8")
if "https://maps.googleapis.com/maps/api/js?key=" not in map_runtime or "callback=LAAAInitGoogleMaps" not in map_runtime:
    errors.append("Google Maps JavaScript API loader is missing")

if not re.search(r'<main\b', HTML):
    errors.append("Missing main landmark")
if HTML.count("<h1") != 1:
    errors.append("Expected exactly one h1")

public_text = "\n".join(
    path.read_text(encoding="utf-8", errors="ignore")
    for path in [
        ROOT / "index.html",
        ROOT / "src" / "index.template",
        ROOT / "data" / "site-data.json",
        ROOT / "README.md",
        ROOT / "assets" / "site.js",
        ROOT / "assets" / "styles.css",
    ]
)
for forbidden in ["voicemail", "human review packet", "internal evaluation memo", "tenant name"]:
    if forbidden.lower() in public_text.lower():
        errors.append(f"Confidential reference present: {forbidden}")

files = []
for path in sorted(ROOT.rglob("*"), key=lambda candidate: candidate.relative_to(ROOT).as_posix().casefold()):
    if (
        not path.is_file()
        or any(part in IGNORED_PARTS for part in path.parts)
        or path.name == "site-manifest.json"
    ):
        continue
    payload = repository_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": digest, "bytes": len(payload)})
(ROOT / "site-manifest.json").write_text(json.dumps({"files": files}, indent=2) + "\n", encoding="utf-8")

if errors:
    print("VALIDATION FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("VALIDATION PASSED")
print(json.dumps(actual, indent=2))
print(f"Manifest files: {len(files)}")
