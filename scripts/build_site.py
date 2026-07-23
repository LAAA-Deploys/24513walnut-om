from __future__ import annotations

import html
import json
from datetime import date
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


def date_label(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"


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
            f"<button class='comp-summary{selected}' type='button' data-comp-select='{esc(comp['id'])}' aria-pressed='{'true' if index == 0 else 'false'}' "
            f"aria-label='Select comparable {esc(comp['map_label'])}, {esc(comp['address'])}, sold for {money(comp['price'])}'>"
            f"<span class='comp-thumb'><img src='{esc(comp['image'])}' alt='{esc(comp['image_alt'])}' loading='lazy'><b aria-hidden='true'>{esc(comp['map_label'])}</b><small>{esc(comp['image_credit'])}</small></span>"
            "<span class='comp-summary-copy'>"
            f"<span class='comp-summary-role'>{esc(comp['role'])}</span><strong>{esc(comp['address'])}</strong>"
            f"<span class='comp-summary-place'>{esc(comp['city'])} · {esc(comp['distance'])}</span>"
            f"<span class='comp-summary-price'>{money(comp['price'])}<small>Closed {date_label(comp['close_date'])}</small></span>"
            f"<span class='comp-summary-metrics'><span><b>{esc(comp['units'])}</b> units</span><span><b>{money(comp['ppu'])}</b> / unit</span><span><b>{money(comp['ppsf'])}</b> / SF</span></span>"
            "</span>"
            "</button>"
        )
    return "".join(items)


def comp_selected_analyses() -> str:
    analyses = []
    for index, comp in enumerate(DATA["sale_comps"]):
        hidden = "" if index == 0 else " hidden"
        support = "".join(f"<li>{esc(item)}</li>" for item in comp["strengths"])
        cautions = "".join(f"<li>{esc(item)}</li>" for item in comp["cautions"])
        analyses.append(
            f"<article class='selected-comp' data-comp-preview='{esc(comp['id'])}'{hidden}>"
            f"<figure><img src='{esc(comp['image'])}' alt='{esc(comp['image_alt'])}' loading='lazy'><figcaption>{esc(comp['image_credit'])}</figcaption><b aria-hidden='true'>{esc(comp['map_label'])}</b></figure>"
            "<div class='selected-comp-body'>"
            f"<div class='selected-comp-heading'><div><p class='eyebrow'>{esc(comp['role'])}</p><h3>{esc(comp['address'])}</h3><p>{esc(comp['city'])} · {esc(comp['distance'])}</p></div><strong>{money(comp['price'])}<small>Closed {date_label(comp['close_date'])}</small></strong></div>"
            "<dl class='selected-comp-metrics'>"
            f"<div><dt>Units</dt><dd>{esc(comp['units'])}</dd></div><div><dt>Building</dt><dd>{comp['sf']:,} SF</dd></div><div><dt>Lot</dt><dd>{comp['lot_sf']:,} SF</dd></div>"
            f"<div><dt>Price / Unit</dt><dd>{money(comp['ppu'])}</dd></div><div><dt>Price / SF</dt><dd>{money(comp['ppsf'])}</dd></div><div><dt>Built</dt><dd>{esc(comp['year_built'])}</dd></div>"
            "</dl>"
            f"<section class='selected-comparison'><h4>How it compares to Walnut</h4><p>{esc(comp['note'])}</p><p><b>Rent rules:</b> {esc(comp['rent_rules'])}</p><p><b>Occupancy at sale:</b> {esc(comp['occupancy'])}</p><p><b>Physical profile:</b> {esc(comp['condition'])}</p></section>"
            f"<div class='selected-evidence'><section><h4>Support</h4><ul>{support}</ul></section><section><h4>Cautions</h4><ul>{cautions}</ul></section></div>"
            f"<div class='selected-actions'><a class='button primary' href='#comp-{esc(comp['id'])}'>Review complete profile</a><a class='button outline' href='{esc(comp['map_url'])}' target='_blank' rel='noopener'>Open in Google Maps</a></div>"
            "</div></article>"
        )
    return "".join(analyses)


def subject_baseline() -> str:
    price = DATA["meta"]["offering_price"]
    units = DATA["property"]["units"]
    building_sf = DATA["property"]["building_sf"]
    current_gsr = sum(unit["current_rent"] for unit in DATA["units"]) * 12
    proforma_gsr = sum(unit["market_rent"] for unit in DATA["units"]) * 12
    current_expenses = sum(item["current"] for item in DATA["expenses"])
    proforma_expenses = sum(item["pro_forma"] for item in DATA["expenses"])
    current_noi = current_gsr - current_expenses
    proforma_noi = proforma_gsr - proforma_expenses
    return (
        "<article class='subject-baseline'>"
        "<figure><img src='assets/images/hero-front-aerial.jpg' alt='Aerial view of 24513–24519 Walnut Street' loading='lazy'><b aria-hidden='true'>S</b><figcaption>Subject property · archived listing photography</figcaption></figure>"
        "<div class='subject-baseline-body'>"
        "<p class='eyebrow'>Subject Property</p>"
        f"<div class='subject-baseline-heading'><div><h3>{esc(DATA['property']['address'])}</h3><p>{esc(DATA['property']['city_state_zip'])}</p></div><strong>{money(price)}<small>Offering price</small></strong></div>"
        "<dl class='subject-baseline-metrics'>"
        f"<div><dt>Units</dt><dd>{units}</dd></div><div><dt>Building</dt><dd>{building_sf:,} SF</dd></div><div><dt>Lot</dt><dd>{DATA['property']['lot_sf']:,} SF</dd></div>"
        f"<div><dt>Price / Unit</dt><dd>{money(price / units)}</dd></div><div><dt>Price / SF</dt><dd>{money(price / building_sf, 2)}</dd></div><div><dt>Rent Rules</dt><dd>{esc(DATA['property']['rent_rules'])}</dd></div>"
        "</dl>"
        "<div class='subject-income-comparison'>"
        f"<div><span>Current NOI</span><b>{money(current_noi)}</b><small>{metric(current_noi / price * 100, '%')} cap rate</small></div>"
        f"<div><span>Pro Forma NOI</span><b>{money(proforma_noi)}</b><small>{metric(proforma_noi / price * 100, '%')} cap rate</small></div>"
        f"</div><a class='subject-map-action' href='{esc(DATA['property']['map_url'])}' target='_blank' rel='noopener'>View Walnut Street in Google Maps <span aria-hidden='true'>↗</span></a></div></article>"
    )


def subject_baseline_strip() -> str:
    price = DATA["meta"]["offering_price"]
    units = DATA["property"]["units"]
    building_sf = DATA["property"]["building_sf"]
    return (
        "<div class='subject-baseline-strip' aria-label='Walnut subject-property comparison baseline'>"
        "<span><b>S</b><span>Walnut Street<small>Subject offering</small></span></span>"
        f"<dl><div><dt>Price</dt><dd>{money(price)}</dd></div><div><dt>Per Unit</dt><dd>{money(price / units)}</dd></div><div><dt>Per SF</dt><dd>{money(price / building_sf)}</dd></div></dl>"
        f"<a href='{esc(DATA['property']['map_url'])}' target='_blank' rel='noopener' aria-label='Open Walnut Street in Google Maps'>Map <span aria-hidden='true'>↗</span></a>"
        "</div>"
    )


def comparison_metric_panels() -> str:
    subject_values = {
        "price": DATA["meta"]["offering_price"],
        "ppu": DATA["meta"]["offering_price"] / DATA["property"]["units"],
        "ppsf": DATA["meta"]["offering_price"] / DATA["property"]["building_sf"],
    }
    metrics = [
        ("price", "Sale / Offering Price", "Price", 0),
        ("ppu", "Price Per Unit", "Price / Unit", 0),
        ("ppsf", "Price Per Square Foot", "Price / SF", 0),
    ]
    panels = []
    for metric_id, title, label, decimals in metrics:
        values = [subject_values[metric_id]] + [float(comp[metric_id]) for comp in DATA["sale_comps"]]
        maximum = max(values)
        rows = [
            "<div class='comparison-bar subject-row'>"
            "<span class='comparison-bar-label'><b>S</b><span>Walnut Street<small>Subject offering</small></span></span>"
            f"<span class='comparison-bar-track'><i style='--bar:{subject_values[metric_id] / maximum * 100:.2f}%'></i></span>"
            f"<strong>{money(subject_values[metric_id], decimals)}</strong></div>"
        ]
        for comp in DATA["sale_comps"]:
            rows.append(
                f"<button class='comparison-bar' type='button' data-comp-select='{esc(comp['id'])}' aria-pressed='false' aria-label='Select {esc(comp['address'])} in the {esc(label)} comparison'>"
                f"<span class='comparison-bar-label'><b>{esc(comp['map_label'])}</b><span>{esc(comp['address'])}<small>{esc(comp['role'])}</small></span></span>"
                f"<span class='comparison-bar-track'><i style='--bar:{float(comp[metric_id]) / maximum * 100:.2f}%'></i></span>"
                f"<strong>{money(comp[metric_id], decimals)}</strong></button>"
            )
        hidden = "" if metric_id == "price" else " hidden"
        panels.append(
            f"<section class='comparison-metric-panel' data-comp-metric-panel='{metric_id}'{hidden}><h4>{title}</h4>{''.join(rows)}</section>"
        )
    return "".join(panels)


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
            f"<p class='comp-analysis'><b>How it compares to Walnut.</b> {esc(comp['note'])}</p>"
            "<div class='comp-profile-disclosures'>"
            f"<details data-profile-detail open><summary>Transaction</summary><dl><div><dt>Closed</dt><dd>{date_label(comp['close_date'])}</dd></div><div><dt>Days on market</dt><dd>{esc(comp['dom'])}</dd></div><div><dt>Sale-to-list</dt><dd>{esc(comp['sp_lp'])}</dd></div><div><dt>GRM</dt><dd>{esc(comp['grm'])}</dd></div><div><dt>Cap rate</dt><dd>{esc(comp['cap'])}</dd></div></dl></details>"
            f"<details data-profile-detail open><summary>Property and Occupancy</summary><p><b>Configuration:</b> {esc(comp['bed_bath'])}</p><p><b>Physical profile:</b> {esc(comp['condition'])}</p><p><b>Occupancy at sale:</b> {esc(comp['occupancy'])}</p></details>"
            f"<details data-profile-detail open><summary>Comparison</summary><p><b>Rent rules:</b> {esc(comp['rent_rules'])}</p><p><b>Overall relationship:</b> {esc(comp['verdict'])}</p></details>"
            f"<details data-profile-detail open><summary>Support and Cautions</summary><div class='profile-support-grid'><div><h4>Support</h4><ul>{strengths}</ul></div><div><h4>Cautions</h4><ul>{cautions}</ul></div></div></details>"
            f"<details data-profile-detail open><summary>Sources</summary><p>{esc(comp['source'])}</p><a href='{esc(comp['map_url'])}' target='_blank' rel='noopener'>Open in Google Maps <span aria-hidden='true'>↗</span></a></details>"
            "</div>"
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


def rent_benchmark_cards() -> str:
    cards = []
    for item in DATA["rent_evidence"]:
        if item["selected"] is None:
            continue
        maximum = max(item["median"], item["percentile_25"], item["selected"]) * 1.08
        bars = [
            ("Selected Pro Forma", item["selected"], "selected"),
            ("25th Percentile", item["percentile_25"], "p25"),
            ("Survey Median", item["median"], "median"),
        ]
        bar_markup = "".join(
            f"<div class='rent-benchmark-row {css}'><span>{label}</span><i><b style='--bar:{value / maximum * 100:.2f}%'></b></i><strong>{money(value)}</strong></div>"
            for label, value, css in bars
        )
        cards.append(
            "<article class='rent-benchmark-card'>"
            f"<header><div><p class='eyebrow'>{esc(item['sample'])}</p><h4>{esc(item['segment'])}</h4></div><strong>{money(item['selected'])}<small>Selected Pro Forma</small></strong></header>"
            f"<div class='rent-benchmark-bars'>{bar_markup}</div><p>{esc(item['note'])}</p></article>"
        )
    return "".join(cards)


def copy_paragraphs(items: list[str], css_class: str) -> str:
    return "".join(f"<p class='{css_class}'>{esc(item)}</p>" for item in items)


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
current_monthly_rent = sum(unit["current_rent"] for unit in DATA["units"])
proforma_monthly_rent = sum(unit["market_rent"] for unit in DATA["units"])
monthly_rent_upside = proforma_monthly_rent - current_monthly_rent
monthly_rent_upside_percent = monthly_rent_upside / current_monthly_rent * 100
current_gsr = current_monthly_rent * 12
proforma_gsr = proforma_monthly_rent * 12
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
    "{{CURRENT_MONTHLY_RENT}}": money(current_monthly_rent),
    "{{PROFORMA_MONTHLY_RENT}}": money(proforma_monthly_rent),
    "{{MONTHLY_RENT_UPSIDE}}": money(monthly_rent_upside),
    "{{MONTHLY_RENT_UPSIDE_PERCENT}}": f"{monthly_rent_upside_percent:.1f}%",
    "{{FINANCIAL_DESKTOP_ROWS}}": financial_desktop_rows(),
    "{{FINANCIAL_MOBILE_ROWS}}": financial_mobile_rows(),
    "{{SALE_COMPARABLE_CONCLUSION}}": copy_paragraphs(DATA["comparables_analysis"]["sale_conclusion"], "comparison-narrative"),
    "{{SUBJECT_BASELINE}}": subject_baseline(),
    "{{SUBJECT_BASELINE_STRIP}}": subject_baseline_strip(),
    "{{COMP_SUMMARY_ITEMS}}": comp_summary_items(),
    "{{COMP_SELECTED_ANALYSES}}": comp_selected_analyses(),
    "{{COMPARISON_METRIC_PANELS}}": comparison_metric_panels(),
    "{{COMP_CARDS}}": comp_cards(),
    "{{RENT_ROWS}}": rent_rows(),
    "{{RENT_BENCHMARK_CARDS}}": rent_benchmark_cards(),
    "{{RENT_COMPARABLE_CONCLUSION}}": DATA["comparables_analysis"]["rent_conclusion"],
    "{{INTEGRATED_COMPARABLE_CONCLUSION}}": DATA["comparables_analysis"]["integrated_conclusion"],
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
