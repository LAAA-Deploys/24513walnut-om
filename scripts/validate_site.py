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


for relative, approved in APPROVED_LOGOS.items():
    logo_path = ROOT / relative
    if not logo_path.exists():
        errors.append(f"Missing approved logo: {relative}")
        continue
    digest = hashlib.sha256(logo_path.read_bytes()).hexdigest().upper()
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
current_gsr = sum(unit["current_rent"] for unit in DATA["units"]) * 12
proforma_gsr = sum(unit["market_rent"] for unit in DATA["units"]) * 12
current_expenses = sum(item["current"] for item in DATA["expenses"])
proforma_expenses = sum(item["pro_forma"] for item in DATA["expenses"])
current_noi = current_gsr - current_expenses
proforma_noi = proforma_gsr - proforma_expenses

expected = {
    "price": 1095000,
    "current_gsr": 68400,
    "proforma_gsr": 83400,
    "current_expenses": 24377,
    "proforma_expenses": 24377,
    "current_noi": 44023,
    "proforma_noi": 59023,
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

required_strings = [
    "$1,095,000", "$68,400", "$83,400", "$44,023", "$59,023",
    "4.02%", "5.39%", "16.01x", "13.13x", "CA 01962976", "CA 01905352",
    "noindex, nofollow, noarchive"
]
for value in required_strings:
    if value not in HTML:
        errors.append(f"Missing required rendered value: {value}")

for stale in ["$1,249,000", "3.99%", "30 trains", "Why the LAAA Team", "expected sale", "price reduction"]:
    if stale.lower() in HTML.lower():
        errors.append(f"Stale or seller-facing phrase present: {stale}")

for image in DATA["gallery"]:
    if not (ROOT / image["src"]).exists():
        errors.append(f"Missing image: {image['src']}")

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
for path in sorted(ROOT.rglob("*")):
    if (
        not path.is_file()
        or any(part in IGNORED_PARTS for part in path.parts)
        or path.name == "site-manifest.json"
    ):
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    files.append({"path": path.relative_to(ROOT).as_posix(), "sha256": digest, "bytes": path.stat().st_size})
(ROOT / "site-manifest.json").write_text(json.dumps({"files": files}, indent=2) + "\n", encoding="utf-8")

if errors:
    print("VALIDATION FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("VALIDATION PASSED")
print(json.dumps(actual, indent=2))
print(f"Manifest files: {len(files)}")
