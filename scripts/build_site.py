from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "site-data.json").read_text(encoding="utf-8"))
TEMPLATE = (ROOT / "src" / "index.template").read_text(encoding="utf-8")


def money(value: float | int) -> str:
    return f"${value:,.0f}"


def metric(value: float, suffix: str = "") -> str:
    return f"{value:,.2f}{suffix}"


def unit_rows() -> str:
    rows = []
    for unit in DATA["units"]:
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(unit['label'])}</strong></td>"
            f"<td>{html.escape(unit['type'])}</td>"
            f"<td>{money(unit['current_rent'])}</td>"
            f"<td>{money(unit['market_rent'])}</td>"
            f"<td><span class='status-pill'>{html.escape(unit['status'])}</span></td>"
            "</tr>"
        )
    return "".join(rows)


def expense_rows() -> str:
    rows = []
    for expense in DATA["expenses"]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(expense['label'])}<small>{html.escape(expense['basis'])}</small></td>"
            f"<td>{money(expense['current'])}</td>"
            f"<td>{money(expense['pro_forma'])}</td>"
            "</tr>"
        )
    return "".join(rows)


def comp_cards() -> str:
    cards = []
    for comp in DATA["sale_comps"]:
        cards.append(
            "<article class='comp-card'>"
            f"<span class='eyebrow'>{html.escape(comp['role'])}</span>"
            f"<h3>{html.escape(comp['address'])}</h3>"
            f"<p class='comp-meta'>{html.escape(comp['city'])} · Closed {html.escape(comp['close_date'])}</p>"
            f"<p class='comp-price'>{money(comp['price'])}</p>"
            "<div class='comp-stats'>"
            f"<span><b>{money(comp['ppu'])}</b> / unit</span>"
            f"<span><b>{money(comp['ppsf'])}</b> / SF</span>"
            f"<span><b>{comp['units']}</b> units</span>"
            "</div>"
            f"<p>{html.escape(comp['note'])}</p>"
            "</article>"
        )
    return "".join(cards)


def rent_rows() -> str:
    rows = []
    for item in DATA["rent_evidence"]:
        median = money(item["median"]) if item["median"] is not None else "—"
        p25 = money(item["percentile_25"]) if item["percentile_25"] is not None else "—"
        selected = money(item["selected"]) if item["selected"] is not None else "Cross-check"
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(item['segment'])}</strong><small>{html.escape(item['sample'])}</small></td>"
            f"<td>{median}</td><td>{p25}</td><td>{selected}</td>"
            f"<td>{html.escape(item['note'])}</td>"
            "</tr>"
        )
    return "".join(rows)


def gallery_items() -> str:
    items = []
    for i, image in enumerate(DATA["gallery"]):
        loading = "eager" if i == 0 else "lazy"
        items.append(
            "<figure class='gallery-item'>"
            f"<img src='{html.escape(image['src'])}' alt='{html.escape(image['alt'])}' loading='{loading}'>"
            f"<figcaption>{html.escape(image['caption'])}</figcaption>"
            "</figure>"
        )
    return "".join(items)


def contact_cards() -> str:
    cards = []
    for contact in DATA["contacts"]:
        phone_href = "+1" + "".join(c for c in contact["phone"] if c.isdigit())
        cards.append(
            "<article class='contact-card'>"
            f"<img src='{html.escape(contact['image'])}' alt='Portrait of {html.escape(contact['name'])}'>"
            "<div>"
            f"<h3>{html.escape(contact['name'])}</h3>"
            f"<p>{html.escape(contact['title'])}<br><span>{html.escape(contact['license'])}</span></p>"
            f"<a href='tel:{phone_href}'>{html.escape(contact['phone'])}</a>"
            f"<a href='mailto:{html.escape(contact['email'])}'>{html.escape(contact['email'])}</a>"
            "</div></article>"
        )
    return "".join(cards)


price = DATA["meta"]["offering_price"]
current_gsr = sum(unit["current_rent"] for unit in DATA["units"]) * 12
proforma_gsr = sum(unit["market_rent"] for unit in DATA["units"]) * 12
current_expenses = sum(item["current"] for item in DATA["expenses"])
proforma_expenses = sum(item["pro_forma"] for item in DATA["expenses"])
current_noi = current_gsr - current_expenses
proforma_noi = proforma_gsr - proforma_expenses

replacements = {
    "{{TITLE}}": DATA["meta"]["title"],
    "{{DESCRIPTION}}": DATA["meta"]["description"],
    "{{PRICE}}": money(price),
    "{{ADDRESS}}": DATA["property"]["address"],
    "{{CITY_STATE_ZIP}}": DATA["property"]["city_state_zip"],
    "{{UNIT_ROWS}}": unit_rows(),
    "{{EXPENSE_ROWS}}": expense_rows(),
    "{{COMP_CARDS}}": comp_cards(),
    "{{RENT_ROWS}}": rent_rows(),
    "{{GALLERY_ITEMS}}": gallery_items(),
    "{{CONTACT_CARDS}}": contact_cards(),
    "{{CURRENT_GSR}}": money(current_gsr),
    "{{PROFORMA_GSR}}": money(proforma_gsr),
    "{{CURRENT_EXPENSES}}": money(current_expenses),
    "{{PROFORMA_EXPENSES}}": money(proforma_expenses),
    "{{CURRENT_NOI}}": money(current_noi),
    "{{PROFORMA_NOI}}": money(proforma_noi),
    "{{CURRENT_CAP}}": metric(current_noi / price * 100, "%"),
    "{{PROFORMA_CAP}}": metric(proforma_noi / price * 100, "%"),
    "{{CURRENT_GRM}}": metric(price / current_gsr, "x"),
    "{{PROFORMA_GRM}}": metric(price / proforma_gsr, "x"),
    "{{PPU}}": money(price / DATA["property"]["units"]),
    "{{PPSF}}": money(price / DATA["property"]["building_sf"]),
}

output = TEMPLATE
for token, value in replacements.items():
    output = output.replace(token, str(value))

if "{{" in output or "}}" in output:
    raise RuntimeError("Unresolved template token found")

(ROOT / "index.html").write_text(output, encoding="utf-8", newline="\n")
print(f"Built {ROOT / 'index.html'}")
