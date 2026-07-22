from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "site-data.json").read_text(encoding="utf-8"))
HTML = (ROOT / "index.html").read_text(encoding="utf-8")

errors: list[str] = []
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
    if not path.is_file() or ".git" in path.parts or "qa" in path.parts:
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
