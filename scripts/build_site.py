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
        tags = " ".join(comp["tags"])
        strengths = "".join(f"<li>{html.escape(item)}</li>" for item in comp["strengths"])
        cautions = "".join(f"<li>{html.escape(item)}</li>" for item in comp["cautions"])
        ppu_note = f"<small>{html.escape(comp['ppu_note'])}</small>" if comp.get("ppu_note") else ""
        sf_note = f"<small>{html.escape(comp['sf_note'])}</small>" if comp.get("sf_note") else ""
        cards.append(
            f"<article class='comp-card' data-comp-card data-comp-id='{html.escape(comp['id'])}' data-comp-tags='{html.escape(tags)}'>"
            f"<a class='comp-photo' href='{html.escape(comp['map_url'])}' target='_blank' rel='noopener' aria-label='Open {html.escape(comp['address'])} in Google Maps'>"
            f"<img src='{html.escape(comp['image'])}' alt='{html.escape(comp['image_alt'])}' loading='lazy'>"
            f"<span class='map-badge' aria-hidden='true'>{html.escape(comp['map_label'])}</span>"
            f"<small>{html.escape(comp['image_credit'])}</small></a>"
            "<div class='comp-body'>"
            f"<div class='comp-heading'><div><span class='eyebrow'>{html.escape(comp['role'])}</span><h3>{html.escape(comp['address'])}</h3>"
            f"<p class='comp-meta'>{html.escape(comp['city'])} · Closed {html.escape(comp['close_date'])} · {html.escape(comp['dom'])} DOM</p></div>"
            f"<span class='comp-verdict'>{html.escape(comp['verdict'])}</span></div>"
            f"<p class='comp-price'>{money(comp['price'])}</p>"
            "<div class='comp-stats'>"
            f"<span><b>{money(comp['ppu'])}</b> / unit{ppu_note}</span>"
            f"<span><b>{money(comp['ppsf'])}</b> / SF{sf_note}</span>"
            f"<span><b>{html.escape(str(comp['units']))}</b> units</span>"
            f"<span><b>{html.escape(comp['bed_bath'])}</b></span>"
            "</div>"
            f"<p class='comp-summary'>{html.escape(comp['note'])}</p>"
            "<details class='comp-details'><summary>Explore the full comparison</summary><div class='comp-detail-grid'>"
            "<section><h4>Sale and physical profile</h4><dl>"
            f"<div><dt>Sale-to-list</dt><dd>{html.escape(comp['sp_lp'])}</dd></div>"
            f"<div><dt>Building</dt><dd>{comp['sf']:,} SF</dd></div>"
            f"<div><dt>Lot</dt><dd>{comp['lot_sf']:,} SF</dd></div>"
            f"<div><dt>Year built</dt><dd>{html.escape(comp['year_built'])}</dd></div>"
            f"<div><dt>GRM</dt><dd>{html.escape(comp['grm'])}</dd></div>"
            f"<div><dt>Cap rate</dt><dd>{html.escape(comp['cap'])}</dd></div>"
            "</dl></section>"
            f"<section><h4>Occupancy and condition</h4><p><b>Occupancy:</b> {html.escape(comp['occupancy'])}</p><p><b>Condition:</b> {html.escape(comp['condition'])}</p></section>"
            f"<section><h4>What supports the sale</h4><ul>{strengths}</ul></section>"
            f"<section><h4>What limits comparability</h4><ul>{cautions}</ul></section>"
            "</div>"
            f"<a class='comp-map-link' href='{html.escape(comp['map_url'])}' target='_blank' rel='noopener'>Open this property in Google Maps <span aria-hidden='true'>↗</span></a>"
            "</details></div>"
            "</article>"
        )
    return "".join(cards)


def comp_map_legend() -> str:
    items = [
        "<div class='map-legend-subject'><span>S</span><div><b>Subject</b><small>24513-24519 Walnut Street</small></div></div>"
    ]
    for comp in DATA["sale_comps"]:
        items.append(
            f"<button type='button' data-comp-target='{html.escape(comp['id'])}' aria-label='Show details for {html.escape(comp['address'])}'>"
            f"<span>{html.escape(comp['map_label'])}</span><div><b>{html.escape(comp['address'])}</b>"
            f"<small>{money(comp['price'])} · {html.escape(comp['role'])}</small></div></button>"
        )
    return "".join(items)


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
            f"<a href='{html.escape(image['src'])}' data-gallery-link data-gallery-index='{i}' aria-label='View larger: {html.escape(image['caption'])}'>"
            f"<img src='{html.escape(image['src'])}' alt='{html.escape(image['alt'])}' loading='{loading}'>"
            f"<figcaption>{html.escape(image['caption'])}<span aria-hidden='true'>Expand +</span></figcaption></a>"
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
    "{{COMP_MAP_LEGEND}}": comp_map_legend(),
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
