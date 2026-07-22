from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data" / "site-data.json").read_text(encoding="utf-8"))
TEMPLATE = (ROOT / "src" / "index.template").read_text(encoding="utf-8")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def money(value: float | int, decimals: int = 0) -> str:
    return f"${value:,.{decimals}f}"


def metric(value: float, suffix: str = "") -> str:
    return f"{value:,.2f}{suffix}"


def copy_blocks(key: str, css_class: str) -> str:
    return "".join(f"<p class='{css_class}'>{esc(paragraph)}</p>" for paragraph in DATA[key])


def highlight_cards() -> str:
    return "".join(
        f"<article><span>{index:02d}</span><div><h3>{esc(item['headline'])}</h3><p>{esc(item['detail'])}</p></div></article>"
        for index, item in enumerate(DATA["investment_highlights"], start=1)
    )


def unit_rows() -> str:
    rows = []
    for unit in DATA["units"]:
        current_psf = unit["current_rent"] / unit["unit_sf"]
        proforma_psf = unit["market_rent"] / unit["unit_sf"]
        upside = unit["market_rent"] - unit["current_rent"]
        upside_pct = upside / unit["current_rent"] * 100
        rows.append(
            "<tr>"
            f"<td class='unit-identity' data-label='Residence'><strong>{esc(unit['label'])}</strong><small>{esc(unit['type'])} · {unit['unit_sf']:,} SF</small></td>"
            f"<td class='desktop-unit-type' data-label='Unit type'>{esc(unit['type'])}</td>"
            f"<td class='desktop-unit-sf num' data-label='Unit SF'>{unit['unit_sf']:,}</td>"
            f"<td class='rent-value num' data-label='Current rent'><strong>{money(unit['current_rent'])}</strong><small>{money(current_psf, 2)} / SF</small></td>"
            f"<td class='desktop-rent-rate num' data-label='Current rent per SF'>{money(current_psf, 2)}</td>"
            f"<td class='rent-value num' data-label='Pro Forma rent'><strong>{money(unit['market_rent'])}</strong><small>{money(proforma_psf, 2)} / SF</small></td>"
            f"<td class='desktop-rent-rate num' data-label='Pro Forma rent per SF'>{money(proforma_psf, 2)}</td>"
            f"<td class='upside-value num' data-label='Upside'><strong>{money(upside)}</strong><small>{upside_pct:.1f}%</small></td>"
            "</tr>"
        )
    return "".join(rows)


def format_financial(value: float | int | None, kind: str, basis: str = "total") -> str:
    if value is None:
        return "—"
    if kind == "currency":
        if basis == "unit":
            return money(value / DATA["property"]["units"])
        if basis == "sf":
            return money(value / DATA["property"]["building_sf"], 2)
        return money(value)
    if kind == "percent":
        return metric(float(value), "%")
    if kind == "multiple":
        return metric(float(value), "x")
    return esc(value)


def financial_definition() -> list[dict[str, object]]:
    price = DATA["meta"]["offering_price"]
    current_gsr = sum(unit["current_rent"] for unit in DATA["units"]) * 12
    proforma_gsr = sum(unit["market_rent"] for unit in DATA["units"]) * 12
    current_expenses = sum(item["current"] for item in DATA["expenses"])
    proforma_expenses = sum(item["pro_forma"] for item in DATA["expenses"])
    current_noi = current_gsr - current_expenses
    proforma_noi = proforma_gsr - proforma_expenses
    rows: list[dict[str, object]] = [
        {"section": "Operating Data"},
        {"label": "Gross Scheduled Rent", "kind": "currency", "current": current_gsr, "proforma": proforma_gsr, "note": "Annualized from the reported current and broker-selected pro forma monthly rents."},
        {"label": "Total Expenses", "kind": "currency", "current": current_expenses, "proforma": proforma_expenses, "emphasis": "subtotal", "note": "Broker-estimated operating expenses; no seller T-12 was available."},
        {"label": "Net Operating Income", "kind": "currency", "current": current_noi, "proforma": proforma_noi, "emphasis": "noi", "note": "Gross scheduled rent less the displayed expense stack; no vacancy or financing is included."},
        {"section": "Returns"},
        {"label": "Cap Rate", "kind": "percent", "current": current_noi / price * 100, "proforma": proforma_noi / price * 100, "note": "NOI divided by the $1,095,000 offering price."},
        {"label": "GRM", "kind": "multiple", "current": price / current_gsr, "proforma": price / proforma_gsr, "note": "Offering price divided by gross scheduled rent."},
        {"section": "Expense Summary"},
        {"label": "Total Expenses", "kind": "currency", "current": current_expenses, "proforma": proforma_expenses, "emphasis": "subtotal"},
        {"label": "Expenses as % of GSR", "kind": "percent", "current": current_expenses / current_gsr * 100, "proforma": proforma_expenses / proforma_gsr * 100},
        {"section": "Detailed Expenses"},
    ]
    rows.extend(
        {"label": item["label"], "kind": "currency", "current": item["current"], "proforma": item["pro_forma"], "note": item["basis"]}
        for item in DATA["expenses"]
    )
    rows.append({"section": "Financing"})
    rows.append({"label": "Financing assumptions forthcoming.", "kind": "empty"})
    return rows


def info_control(label: str, note: str | None) -> str:
    if not note:
        return esc(label)
    return (
        f"<span>{esc(label)}</span><details class='row-note'><summary aria-label='Calculation note for {esc(label)}'>i</summary>"
        f"<p>{esc(note)}</p></details>"
    )


def financial_desktop_rows() -> str:
    output = []
    for row in financial_definition():
        if "section" in row:
            output.append(f"<tr class='financial-band'><th colspan='5' scope='colgroup'>{esc(row['section'])}</th></tr>")
            continue
        if row["kind"] == "empty":
            output.append(f"<tr class='financial-empty'><th scope='row'>{esc(row['label'])}</th><td colspan='4'>—</td></tr>")
            continue
        css = f"financial-row {row.get('emphasis', '')}".strip()
        label = info_control(str(row["label"]), row.get("note"))
        output.append(
            f"<tr class='{css}'><th scope='row'>{label}</th>"
            f"<td>{format_financial(row['current'], str(row['kind']))}</td>"
            f"<td>{format_financial(row['proforma'], str(row['kind']))}</td>"
            f"<td>{format_financial(row['proforma'], str(row['kind']), 'unit') if row['kind'] == 'currency' else '—'}</td>"
            f"<td>{format_financial(row['proforma'], str(row['kind']), 'sf') if row['kind'] == 'currency' else '—'}</td></tr>"
        )
    return "".join(output)


def financial_mobile_rows() -> str:
    output = []
    for row in financial_definition():
        if "section" in row:
            output.append(f"<tr class='financial-band'><th colspan='3' scope='colgroup'>{esc(row['section'])}</th></tr>")
            continue
        if row["kind"] == "empty":
            output.append(f"<tr class='financial-empty'><th scope='row'>{esc(row['label'])}</th><td colspan='2'>—</td></tr>")
            continue
        label = info_control(str(row["label"]), row.get("note"))
        current_values = {basis: format_financial(row["current"], str(row["kind"]), basis) for basis in ("total", "unit", "sf")}
        proforma_values = {basis: format_financial(row["proforma"], str(row["kind"]), basis) for basis in ("total", "unit", "sf")}
        if row["kind"] in {"percent", "multiple"}:
            current_values["unit"] = current_values["sf"] = current_values["total"]
            proforma_values["unit"] = proforma_values["sf"] = proforma_values["total"]
        css = f"financial-row {row.get('emphasis', '')}".strip()
        output.append(
            f"<tr class='{css}'><th scope='row'>{label}</th>"
            f"<td data-fin-value data-total='{esc(current_values['total'])}' data-unit='{esc(current_values['unit'])}' data-sf='{esc(current_values['sf'])}'>{current_values['total']}</td>"
            f"<td data-fin-value data-total='{esc(proforma_values['total'])}' data-unit='{esc(proforma_values['unit'])}' data-sf='{esc(proforma_values['sf'])}'>{proforma_values['total']}</td></tr>"
        )
    return "".join(output)


def comp_summary_items() -> str:
    items = []
    for index, comp in enumerate(DATA["sale_comps"]):
        selected = " is-selected" if index == 0 else ""
        items.append(
            f"<button class='comp-summary{selected}' type='button' data-comp-select='{esc(comp['id'])}' aria-pressed='{'true' if index == 0 else 'false'}'>"
            f"<span class='comp-thumb'><img src='{esc(comp['image'])}' alt='{esc(comp['image_alt'])}' loading='lazy'><b aria-hidden='true'>{esc(comp['map_label'])}</b></span>"
            f"<span class='comp-summary-copy'><strong>{esc(comp['address'])}</strong><small>{money(comp['price'])} · {money(comp['ppu'])}/unit · {money(comp['ppsf'])}/SF</small><em>{esc(comp['role'])}</em></span>"
            "</button>"
        )
    return "".join(items)


def comp_previews() -> str:
    previews = []
    for index, comp in enumerate(DATA["sale_comps"]):
        hidden = "" if index == 0 else " hidden"
        previews.append(
            f"<article class='comp-preview' data-comp-preview='{esc(comp['id'])}'{hidden}>"
            f"<img src='{esc(comp['image'])}' alt='{esc(comp['image_alt'])}' loading='lazy'><div><span>{esc(comp['map_label'])} · {esc(comp['role'])}</span>"
            f"<strong>{esc(comp['address'])}</strong><small>{money(comp['price'])} · {esc(comp['distance'])}</small>"
            f"<a href='#comp-{esc(comp['id'])}'>View full comparison</a></div></article>"
        )
    return "".join(previews)


def comp_cards() -> str:
    cards = []
    for comp in DATA["sale_comps"]:
        strengths = "".join(f"<li>{esc(item)}</li>" for item in comp["strengths"])
        cautions = "".join(f"<li>{esc(item)}</li>" for item in comp["cautions"])
        ppu_note = f"<small>{esc(comp['ppu_note'])}</small>" if comp.get("ppu_note") else ""
        sf_note = f"<small>{esc(comp['sf_note'])}</small>" if comp.get("sf_note") else ""
        cards.append(
            f"<article class='comp-profile' id='comp-{esc(comp['id'])}' data-comp-card data-comp-id='{esc(comp['id'])}'>"
            f"<figure><img src='{esc(comp['image'])}' alt='{esc(comp['image_alt'])}' loading='lazy'><figcaption>{esc(comp['image_credit'])}</figcaption><span aria-hidden='true'>{esc(comp['map_label'])}</span></figure>"
            "<div class='comp-profile-body'>"
            f"<div class='comp-profile-title'><div><p class='eyebrow'>{esc(comp['role'])}</p><h3>{esc(comp['address'])}</h3><p>{esc(comp['city'])} · {esc(comp['distance'])}</p></div><strong>{money(comp['price'])}</strong></div>"
            f"<div class='comp-kpis'><span><b>{money(comp['ppu'])}</b> / unit{ppu_note}</span><span><b>{money(comp['ppsf'])}</b> / SF{sf_note}</span><span><b>{esc(comp['units'])}</b> units</span><span><b>{comp['sf']:,}</b> building SF</span><span><b>{comp['lot_sf']:,}</b> lot SF</span><span><b>{esc(comp['year_built'])}</b> built</span></div>"
            f"<p class='comp-analysis'>{esc(comp['note'])}</p>"
            "<div class='comp-evidence-grid'>"
            f"<section><h4>Transaction</h4><dl><div><dt>Closed</dt><dd>{esc(comp['close_date'])}</dd></div><div><dt>Days on market</dt><dd>{esc(comp['dom'])}</dd></div><div><dt>Sale-to-list</dt><dd>{esc(comp['sp_lp'])}</dd></div><div><dt>GRM</dt><dd>{esc(comp['grm'])}</dd></div><div><dt>Cap rate</dt><dd>{esc(comp['cap'])}</dd></div></dl></section>"
            f"<section><h4>Comparison</h4><p><b>Rent rules:</b> {esc(comp['rent_rules'])}</p><p><b>Physical profile:</b> {esc(comp['bed_bath'])}; {esc(comp['condition'])}</p><p><b>Occupancy:</b> {esc(comp['occupancy'])}</p><p><b>Conclusion:</b> {esc(comp['verdict'])}</p></section>"
            f"<section><h4>Support</h4><ul>{strengths}</ul></section><section><h4>Cautions</h4><ul>{cautions}</ul></section>"
            "</div>"
            f"<div class='comp-source'><span>Source: {esc(comp['source'])}</span><a href='{esc(comp['map_url'])}' target='_blank' rel='noopener'>Open in Google Maps <span aria-hidden='true'>↗</span></a></div>"
            "</div></article>"
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
            f"<td data-label='Unit type / survey'><strong>{esc(item['segment'])}</strong><small>{esc(item['sample'])}</small></td>"
            f"<td data-label='Median'>{median}</td><td data-label='25th percentile'>{p25}</td><td data-label='Selected'>{selected}</td>"
            f"<td data-label='Interpretation'>{esc(item['note'])}</td></tr>"
        )
    return "".join(rows)


def gallery_items() -> str:
    items = []
    for index, image in enumerate(DATA["gallery"]):
        items.append(
            f"<figure class='gallery-item gallery-item-{index + 1}'>"
            f"<a href='{esc(image['src'])}' data-gallery-link data-gallery-index='{index}' aria-label='View larger: {esc(image['caption'])}'>"
            f"<img src='{esc(image['src'])}' alt='{esc(image['alt'])}' loading='{'eager' if index == 0 else 'lazy'}'>"
            f"<figcaption>{esc(image['caption'])}<span aria-hidden='true'>Expand +</span></figcaption></a></figure>"
        )
    return "".join(items)


def contact_cards() -> str:
    cards = []
    for contact in DATA["contacts"]:
        phone_href = "+1" + "".join(character for character in contact["phone"] if character.isdigit())
        cards.append(
            "<article class='agent-card'>"
            f"<img src='{esc(contact['image'])}' alt='Headshot of {esc(contact['name'])}'>"
            f"<div><p class='eyebrow'>Listing agent</p><h3>{esc(contact['name'])}</h3><p>{esc(contact['title'])}<br><span>{esc(contact['license'])}</span></p>"
            f"<div class='agent-actions'><a href='tel:{phone_href}'>Call {esc(contact['name'].split()[0])}</a><a href='mailto:{esc(contact['email'])}'>Email</a></div>"
            f"<a class='agent-phone' href='tel:{phone_href}'>{esc(contact['phone'])}</a><a class='agent-email' href='mailto:{esc(contact['email'])}'>{esc(contact['email'])}</a></div></article>"
        )
    return "".join(cards)


def source_links() -> str:
    return "".join(
        f"<a href='{esc(source['url'])}' target='_blank' rel='noopener'>{esc(source['label'])}<span aria-hidden='true'>↗</span></a>"
        for source in DATA["location_sources"]
    )


def map_config_json() -> str:
    subject = {
        "id": "subject",
        "label": "S",
        "title": "24513–24519 Walnut Street",
        "lat": DATA["property"]["latitude"],
        "lng": DATA["property"]["longitude"],
    }
    locations = [
        subject,
        {"id": "station", "label": "T", "title": "Newhall Metrolink Station", "lat": 34.379125, "lng": -118.527363},
        {"id": "main", "label": "M", "title": "The MAIN", "lat": 34.3784335, "lng": -118.5274043},
        {"id": "library", "label": "L", "title": "Old Town Newhall Library", "lat": 34.3816793, "lng": -118.5301927},
        {"id": "park", "label": "P", "title": "William S. Hart Park", "lat": 34.3759169, "lng": -118.5263644},
    ]
    comps = [
        {
            "id": comp["id"],
            "label": comp["map_label"],
            "title": comp["address"],
            "lat": comp["latitude"],
            "lng": comp["longitude"],
        }
        for comp in DATA["sale_comps"]
    ]
    payload = {"subject": subject, "locations": locations, "comps": comps}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def validate_editorial_contract() -> None:
    for key in ("investment_overview", "location_overview"):
        paragraphs = DATA[key]
        if len(paragraphs) != 3:
            raise ValueError(f"{key} must contain exactly three paragraphs")
        if any(len(paragraph.split()) > 80 for paragraph in paragraphs):
            raise ValueError(f"{key} contains a paragraph over 80 words")
        if sum(len(paragraph.split()) for paragraph in paragraphs) > 240:
            raise ValueError(f"{key} exceeds 240 words")
    if not DATA["investment_overview"][0].startswith("The LAAA Team of Marcus & Millichap is proud to present"):
        raise ValueError("Investment Overview opening is not canonical")
    if len(DATA["investment_highlights"]) not in {5, 6}:
        raise ValueError("Investment highlights must contain five or six items")
    for item in DATA["investment_highlights"]:
        if len(item["headline"].split()) > 8 or len(item["detail"].split()) > 40:
            raise ValueError(f"Investment highlight exceeds word limit: {item['headline']}")


validate_editorial_contract()

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
    "{{INVESTMENT_OVERVIEW}}": copy_blocks("investment_overview", "narrative-paragraph"),
    "{{LOCATION_OVERVIEW}}": copy_blocks("location_overview", "narrative-paragraph"),
    "{{HIGHLIGHTS}}": highlight_cards(),
    "{{UNIT_ROWS}}": unit_rows(),
    "{{FINANCIAL_DESKTOP_ROWS}}": financial_desktop_rows(),
    "{{FINANCIAL_MOBILE_ROWS}}": financial_mobile_rows(),
    "{{COMP_SUMMARY_ITEMS}}": comp_summary_items(),
    "{{COMP_PREVIEWS}}": comp_previews(),
    "{{COMP_CARDS}}": comp_cards(),
    "{{RENT_ROWS}}": rent_rows(),
    "{{GALLERY_ITEMS}}": gallery_items(),
    "{{CONTACT_CARDS}}": contact_cards(),
    "{{LOCATION_SOURCES}}": source_links(),
    "{{MAP_CONFIG_JSON}}": map_config_json(),
    "{{CURRENT_NOI}}": money(current_noi),
    "{{PROFORMA_NOI}}": money(proforma_noi),
    "{{CURRENT_CAP}}": metric(current_noi / price * 100, "%"),
    "{{PROFORMA_CAP}}": metric(proforma_noi / price * 100, "%"),
}

output = TEMPLATE
for token, value in replacements.items():
    output = output.replace(token, str(value))

if "{{" in output or "}}" in output:
    raise RuntimeError("Unresolved template token found")

(ROOT / "index.html").write_text(output, encoding="utf-8", newline="\n")
print(f"Built {ROOT / 'index.html'}")
