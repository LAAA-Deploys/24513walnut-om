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


def accounting_money(value: float | int, decimals: int = 0) -> str:
    formatted = money(abs(value), decimals)
    return f"({formatted})" if value < 0 else formatted


def metric(value: float, suffix: str = "") -> str:
    formatted = f"{abs(value):,.2f}{suffix}"
    return f"({formatted})" if value < 0 else formatted


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
    if kind == "accounting":
        if basis == "unit":
            return accounting_money(value / DATA["property"]["units"])
        if basis == "sf":
            return accounting_money(value / DATA["property"]["building_sf"], 2)
        return accounting_money(value)
    if kind == "percent":
        return metric(float(value), "%")
    if kind == "multiple":
        return metric(float(value), "x")
    if kind == "years":
        return f"{int(value)} Years"
    return esc(value)


FINANCIAL_LABELS = {
    "Gross Scheduled Rent": ("GSR", "Gross Scheduled Rent"),
    "Net Operating Income": ("NOI", "Net Operating Income"),
    "GRM": ("GRM", "Gross Rent Multiplier"),
    "Property taxes": ("Taxes", None),
    "Repairs & maintenance": ("R&M", "Repairs and Maintenance"),
    "Landscaping": ("Landscape", None),
    "General & administrative": ("G&A", "General and Administrative"),
    "Expenses as % of GSR": ("Expense Ratio", None),
    "Cash Flow After Debt Service": ("Cash Flow After DS", "Cash Flow After Debt Service"),
    "Debt Service Coverage Ratio": ("DSCR", "Debt Service Coverage Ratio"),
    "Cash-on-Cash Return": ("Cash-on-Cash", None),
}


def compact_financial_label(label: str) -> str:
    visible, expansion = FINANCIAL_LABELS.get(label, (label, None))
    if expansion:
        return f"<abbr title='{esc(expansion)}'>{esc(visible)}</abbr>"
    return esc(visible)


def financial_metrics() -> dict[str, float]:
    price = DATA["meta"]["offering_price"]
    current_gsr = sum(unit["current_rent"] for unit in DATA["units"]) * 12
    proforma_gsr = sum(unit["market_rent"] for unit in DATA["units"]) * 12
    current_expenses = sum(item["current"] for item in DATA["expenses"])
    proforma_expenses = sum(item["pro_forma"] for item in DATA["expenses"])
    return {
        "price": price,
        "current_gsr": current_gsr,
        "proforma_gsr": proforma_gsr,
        "current_expenses": current_expenses,
        "proforma_expenses": proforma_expenses,
        "current_noi": current_gsr - current_expenses,
        "proforma_noi": proforma_gsr - proforma_expenses,
    }


def financial_definition() -> list[dict[str, object]]:
    values = financial_metrics()
    financing = DATA["financing"]
    current_financing = financing["current"]
    proforma_financing = financing["pro_forma"]
    rows: list[dict[str, object]] = [
        {"section": "Operating Data"},
        {"label": "Gross Scheduled Rent", "kind": "currency", "current": values["current_gsr"], "proforma": values["proforma_gsr"], "note": "Annualized from the reported current and broker-selected pro forma monthly rents."},
        {"label": "Total Expenses", "kind": "currency", "current": values["current_expenses"], "proforma": values["proforma_expenses"], "emphasis": "subtotal", "note": "Selected seller-provided and broker-estimated operating expenses; no seller T-12 was available."},
        {"label": "Net Operating Income", "kind": "currency", "current": values["current_noi"], "proforma": values["proforma_noi"], "emphasis": "noi", "note": "Gross scheduled rent less the displayed expense stack; no vacancy is included."},
        {"label": "Debt Service", "kind": "currency", "current": financing["annual_debt_service"], "proforma": financing["annual_debt_service"], "note": "Annual principal and interest under the displayed illustrative financing assumptions."},
        {"label": "Cash Flow After Debt Service", "kind": "accounting", "current": current_financing["cash_flow_after_debt_service"], "proforma": proforma_financing["cash_flow_after_debt_service"], "note": "Net operating income less annual debt service."},
        {"label": "Principal Reduction", "kind": "currency", "current": current_financing["principal_reduction"], "proforma": proforma_financing["principal_reduction"], "note": "Modeled principal reduction from the approved financing model."},
        {"label": "Total Return", "kind": "accounting", "current": current_financing["total_return"], "proforma": proforma_financing["total_return"], "emphasis": "subtotal", "note": "Cash flow after debt service plus modeled principal reduction."},
        {"section": "Returns"},
        {"label": "Cap Rate", "kind": "percent", "current": values["current_noi"] / values["price"] * 100, "proforma": values["proforma_noi"] / values["price"] * 100, "note": "NOI divided by the $1,095,000 offering price."},
        {"label": "GRM", "kind": "multiple", "current": values["price"] / values["current_gsr"], "proforma": values["price"] / values["proforma_gsr"], "note": "Offering price divided by gross scheduled rent."},
        {"label": "Cash-on-Cash Return", "kind": "percent", "current": current_financing["cash_on_cash"] * 100, "proforma": proforma_financing["cash_on_cash"] * 100, "note": "Cash flow after debt service divided by the modeled down payment."},
        {"label": "Debt Service Coverage Ratio", "kind": "multiple", "current": current_financing["dscr"], "proforma": proforma_financing["dscr"], "note": "NOI divided by annual debt service."},
        {"label": "Total Return", "kind": "percent", "current": current_financing["total_return_rate"] * 100, "proforma": proforma_financing["total_return_rate"] * 100, "note": "Cash flow after debt service plus principal reduction, divided by the modeled down payment."},
        {"section": "Detailed Expenses"},
    ]
    rows.extend(
        {"label": item["label"], "kind": "currency", "current": item["current"], "proforma": item["pro_forma"], "note": item["basis"]}
        for item in DATA["expenses"]
    )
    rows.extend([
        {"section": "Financing"},
        {"label": "Loan Amount", "kind": "currency", "current": financing["loan_amount"], "proforma": financing["loan_amount"], "static_basis": True, "note": "Illustrative new first loan at 75% of the offering price."},
        {"label": "Down Payment", "kind": "currency", "current": financing["down_payment"], "proforma": financing["down_payment"], "static_basis": True, "note": "Illustrative equity contribution equal to 25% of the offering price."},
        {"label": "Loan Type", "kind": "text", "current": financing["loan_type"], "proforma": financing["loan_type"], "static_basis": True, "note": "Illustrative new financing."},
        {"label": "LTV", "kind": "percent", "current": financing["ltv"] * 100, "proforma": financing["ltv"] * 100, "static_basis": True, "note": "Loan-to-value ratio."},
        {"label": "Interest Rate", "kind": "percent", "current": financing["interest_rate"] * 100, "proforma": financing["interest_rate"] * 100, "static_basis": True, "note": "Illustrative annual interest rate."},
        {"label": "Amortization", "kind": "years", "current": financing["amortization_years"], "proforma": financing["amortization_years"], "static_basis": True, "note": "Illustrative amortization period."},
        {"label": "Annual Debt Service", "kind": "currency", "current": financing["annual_debt_service"], "proforma": financing["annual_debt_service"], "static_basis": True, "note": "Illustrative annual principal and interest."},
        {"label": "Year Due", "kind": "text", "current": financing["maturity_year"], "proforma": financing["maturity_year"], "static_basis": True, "note": "Illustrative maturity year."},
    ])
    return rows


def financial_summary_rows() -> str:
    price = DATA["meta"]["offering_price"]
    property_data = DATA["property"]
    financing = DATA["financing"]
    rows = [
        ("Price", money(price)),
        ("Down Payment", f"{money(financing['down_payment'])} · {metric((1 - financing['ltv']) * 100, '%')}"),
        ("Units", f"{property_data['units']:,}"),
        ("Building SF", f"{property_data['building_sf']:,}"),
        ("Lot SF", f"{property_data['lot_sf']:,}"),
        ("Price / Unit", money(price / property_data["units"])),
        ("Price / SF", money(price / property_data["building_sf"], 2)),
        ("Year Built", esc(property_data["year_built"])),
    ]
    return "".join(f"<tr><th scope='row'>{esc(label)}</th><td>{value}</td></tr>" for label, value in rows)


def financial_returns_rows() -> str:
    values = financial_metrics()
    financing = DATA["financing"]
    rows = [
        ("Cap Rate", metric(values["current_noi"] / values["price"] * 100, "%"), metric(values["proforma_noi"] / values["price"] * 100, "%")),
        ("GRM", metric(values["price"] / values["current_gsr"], "x"), metric(values["price"] / values["proforma_gsr"], "x")),
        ("Cash-on-Cash Return", metric(financing["current"]["cash_on_cash"] * 100, "%"), metric(financing["pro_forma"]["cash_on_cash"] * 100, "%")),
        ("Debt Service Coverage Ratio", metric(financing["current"]["dscr"], "x"), metric(financing["pro_forma"]["dscr"], "x")),
        ("Total Return", metric(financing["current"]["total_return_rate"] * 100, "%"), metric(financing["pro_forma"]["total_return_rate"] * 100, "%")),
    ]
    return "".join(
        f"<tr><th scope='row'>{compact_financial_label(label)}</th><td>{current}</td><td>{proforma}</td></tr>"
        for label, current, proforma in rows
    )


def financial_operating_rows() -> str:
    values = financial_metrics()
    financing = DATA["financing"]
    rows = [
        ("Gross Scheduled Rent", values["current_gsr"], values["proforma_gsr"], "", "Annualized from the reported current and broker-selected pro forma monthly rents.", False),
        ("Total Expenses", values["current_expenses"], values["proforma_expenses"], "subtotal", "Selected seller-provided and broker-estimated operating expenses; no seller T-12 was available.", False),
        ("Net Operating Income", values["current_noi"], values["proforma_noi"], "noi", "Gross scheduled rent less the displayed expense stack; no vacancy is included.", False),
        ("Debt Service", financing["annual_debt_service"], financing["annual_debt_service"], "", "Annual principal and interest under the displayed illustrative financing assumptions.", False),
        ("Cash Flow After Debt Service", financing["current"]["cash_flow_after_debt_service"], financing["pro_forma"]["cash_flow_after_debt_service"], "", "Net operating income less annual debt service.", True),
        ("Principal Reduction", financing["current"]["principal_reduction"], financing["pro_forma"]["principal_reduction"], "", "Modeled principal reduction from the approved financing model.", False),
        ("Total Return", financing["current"]["total_return"], financing["pro_forma"]["total_return"], "subtotal", "Cash flow after debt service plus modeled principal reduction.", True),
    ]
    return "".join(
        f"<tr class='financial-row {css}'><th scope='row'>{compact_financial_label(label)}</th>"
        f"<td>{accounting_money(current) if signed else money(current)}</td><td>{accounting_money(proforma) if signed else money(proforma)}</td></tr>"
        for label, current, proforma, css, note, signed in rows
    )


def financial_financing_rows() -> str:
    financing = DATA["financing"]
    rows = [
        ("Loan Amount", money(financing["loan_amount"])),
        ("Down Payment", money(financing["down_payment"])),
        ("Loan Type", esc(financing["loan_type"])),
        ("LTV", metric(financing["ltv"] * 100, "%")),
        ("Interest Rate", metric(financing["interest_rate"] * 100, "%")),
        ("Amortization", f"{financing['amortization_years']} Years"),
        ("Annual Debt Service", money(financing["annual_debt_service"])),
        ("Year Due", f"{financing['maturity_year']}"),
    ]
    return "".join(f"<tr><th scope='row'>{esc(label)}</th><td>{value}</td></tr>" for label, value in rows)


def financial_expense_summary_rows() -> str:
    values = financial_metrics()
    rows = [
        ("Total Expenses", money(values["current_expenses"]), money(values["proforma_expenses"])),
        ("Expense Ratio", metric(values["current_expenses"] / values["current_gsr"] * 100, "%"), metric(values["proforma_expenses"] / values["proforma_gsr"] * 100, "%")),
        ("/ Unit", format_financial(values["current_expenses"], "currency", "unit"), format_financial(values["proforma_expenses"], "currency", "unit")),
        ("/ SF", format_financial(values["current_expenses"], "currency", "sf"), format_financial(values["proforma_expenses"], "currency", "sf")),
    ]
    return "".join(
        f"<tr><th scope='row'>{esc(label)}</th><td>{current}</td><td>{proforma}</td></tr>"
        for label, current, proforma in rows
    )


def financial_expense_rows() -> str:
    values = financial_metrics()
    rows = [
        "<tr class='financial-band'><th colspan='6' scope='colgroup'>Income</th></tr>",
        "<tr class='financial-row'><th scope='row'><abbr title='Gross Scheduled Rent'>GSR</abbr></th>"
        f"<td>{money(values['current_gsr'])}</td><td>{money(values['proforma_gsr'])}</td><td>—</td>"
        f"<td>{format_financial(values['proforma_gsr'], 'currency', 'unit')}</td>"
        f"<td>{format_financial(values['proforma_gsr'], 'currency', 'sf')}</td></tr>",
        "<tr class='financial-band'><th colspan='6' scope='colgroup'>Expenses</th></tr>",
    ]
    for index, item in enumerate(DATA["expenses"], start=1):
        rows.append(
            "<tr class='financial-row'>"
            f"<th scope='row'>{compact_financial_label(str(item['label']))}</th>"
            f"<td>{money(item['current'])}</td>"
            f"<td>{money(item['pro_forma'])}</td>"
            f"<td><a class='note-reference' href='#financial-note-desktop-{index}' aria-label='Review note {index}'>[{index}]</a></td>"
            f"<td>{format_financial(item['pro_forma'], 'currency', 'unit')}</td>"
            f"<td>{format_financial(item['pro_forma'], 'currency', 'sf')}</td>"
            "</tr>"
        )
    rows.append(
        "<tr class='financial-row subtotal'><th scope='row'>Total Expenses</th>"
        f"<td>{money(values['current_expenses'])}</td>"
        f"<td>{money(values['proforma_expenses'])}</td>"
        "<td>—</td>"
        f"<td>{format_financial(values['proforma_expenses'], 'currency', 'unit')}</td>"
        f"<td>{format_financial(values['proforma_expenses'], 'currency', 'sf')}</td></tr>"
    )
    rows.append(
        "<tr class='financial-row'><th scope='row'>Expense Ratio</th>"
        f"<td>{metric(values['current_expenses'] / values['current_gsr'] * 100, '%')}</td>"
        f"<td>{metric(values['proforma_expenses'] / values['proforma_gsr'] * 100, '%')}</td>"
        "<td>—</td><td>—</td><td>—</td></tr>"
    )
    rows.append(
        "<tr class='financial-row noi'><th scope='row'><abbr title='Net Operating Income'>NOI</abbr></th>"
        f"<td>{money(values['current_noi'])}</td>"
        f"<td>{money(values['proforma_noi'])}</td>"
        "<td>—</td>"
        f"<td>{format_financial(values['proforma_noi'], 'currency', 'unit')}</td>"
        f"<td>{format_financial(values['proforma_noi'], 'currency', 'sf')}</td></tr>"
    )
    return "".join(rows)


def financial_notes(scope: str) -> str:
    notes = []
    for index, item in enumerate(DATA["expenses"], start=1):
        notes.append(
            f"<li id='financial-note-{scope}-{index}'><span>[{index}]</span><p><b>{compact_financial_label(str(item['label']))}.</b> {esc(item['basis'])}</p></li>"
        )
    return "".join(notes)


def financial_visuals() -> str:
    groups: dict[str, list[dict[str, object]]] = {}
    for unit in DATA["units"]:
        groups.setdefault(str(unit["type"]), []).append(unit)
    total_units = DATA["property"]["units"]
    mix_segments = []
    rent_rows = []
    max_rent = max(float(unit["market_rent"]) for unit in DATA["units"])
    for index, (unit_type, units) in enumerate(sorted(groups.items(), key=lambda item: -len(item[1]))):
        count = len(units)
        share = count / total_units * 100
        current = sum(float(unit["current_rent"]) for unit in units) / count
        proforma = sum(float(unit["market_rent"]) for unit in units) / count
        mix_segments.append(
            f"<span class='mix-segment mix-{index + 1}' style='--share:{share:.2f}%' "
            f"aria-label='{count} {esc(unit_type)} units, {share:.0f} percent of the property'></span>"
        )
        rent_rows.append(
            "<div class='rent-visual-row'>"
            f"<div><b>{esc(unit_type)}</b><small>{count} {'unit' if count == 1 else 'units'}</small></div>"
            "<div class='rent-visual-bars'>"
            f"<span class='rent-current' style='--bar:{current / max_rent * 100:.2f}%'><i></i><b>{money(current)}</b><small>Current</small></span>"
            f"<span class='rent-proforma' style='--bar:{proforma / max_rent * 100:.2f}%'><i></i><b>{money(proforma)}</b><small>Pro Forma</small></span>"
            "</div></div>"
        )
    mix_labels = "".join(
        f"<li><span class='mix-key mix-{index + 1}'></span><b>{len(units)} × {esc(unit_type)}</b><small>{len(units) / total_units * 100:.0f}%</small></li>"
        for index, (unit_type, units) in enumerate(sorted(groups.items(), key=lambda item: -len(item[1])))
    )
    return (
        "<section class='financial-visual-panel'><h4>Unit Mix</h4>"
        f"<div class='unit-mix-bar' role='img' aria-label='Unit mix: {', '.join(f'{len(units)} {unit_type}' for unit_type, units in groups.items())}'>{''.join(mix_segments)}</div>"
        f"<ul class='unit-mix-legend'>{mix_labels}</ul></section>"
        "<section class='financial-visual-panel'><h4>Average Monthly Rent</h4>"
        f"<div class='rent-visual'>{''.join(rent_rows)}</div></section>"
    )


def financial_mobile_rows() -> str:
    sections: list[dict[str, object]] = []
    current_section: dict[str, object] | None = None
    for row in financial_definition():
        if "section" in row:
            current_section = {"title": str(row["section"]), "rows": []}
            sections.append(current_section)
            continue
        if current_section is None:
            continue
        current_section["rows"].append(row)

    output = []
    for section in sections:
        title = str(section["title"])
        rows = section["rows"]
        expanded = " open" if title in {"Operating Data", "Returns"} else ""
        if title == "Financing":
            body = "".join(
                f"<tr><th scope='row'>{compact_financial_label(str(row['label']))}</th>"
                f"<td>{format_financial(row['current'], str(row['kind']), 'total')}</td></tr>"
                for row in rows
            )
            table = (
                "<table class='financial-mobile-assumptions'><caption>Illustrative financing assumptions</caption>"
                f"<thead><tr><th>Term</th><th>Assumption</th></tr></thead><tbody>{body}</tbody></table>"
            )
        else:
            body_rows = []
            for row in rows:
                label = compact_financial_label(str(row["label"]))
                current_values = {basis: format_financial(row["current"], str(row["kind"]), basis) for basis in ("total", "unit", "sf")}
                proforma_values = {basis: format_financial(row["proforma"], str(row["kind"]), basis) for basis in ("total", "unit", "sf")}
                if row["kind"] in {"percent", "multiple", "years"} or row.get("static_basis"):
                    current_values["unit"] = current_values["sf"] = current_values["total"]
                    proforma_values["unit"] = proforma_values["sf"] = proforma_values["total"]
                css = f"financial-row {row.get('emphasis', '')}".strip()
                body_rows.append(
                    f"<tr class='{css}'><th scope='row'>{label}</th>"
                    f"<td data-fin-value data-total='{esc(current_values['total'])}' data-unit='{esc(current_values['unit'])}' data-sf='{esc(current_values['sf'])}'>{current_values['total']}</td>"
                    f"<td data-fin-value data-total='{esc(proforma_values['total'])}' data-unit='{esc(proforma_values['unit'])}' data-sf='{esc(proforma_values['sf'])}'>{proforma_values['total']}</td></tr>"
                )
            table = (
                f"<table class='financial-table mobile-financial-table'><caption>{esc(title)} by selected basis</caption>"
                f"<thead><tr><th>{esc(title)}</th><th>Current</th><th>Pro Forma</th></tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
            )
        output.append(
            f"<details class='financial-mobile-panel'{expanded}><summary>{esc(title)}<span aria-hidden='true'></span></summary>"
            f"<div class='financial-mobile-panel-body'>{table}</div></details>"
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
    "{{FINANCIAL_SUMMARY_ROWS}}": financial_summary_rows(),
    "{{FINANCIAL_RETURNS_ROWS}}": financial_returns_rows(),
    "{{FINANCIAL_FINANCING_ROWS}}": financial_financing_rows(),
    "{{FINANCIAL_OPERATING_ROWS}}": financial_operating_rows(),
    "{{FINANCIAL_EXPENSE_SUMMARY_ROWS}}": financial_expense_summary_rows(),
    "{{FINANCIAL_EXPENSE_ROWS}}": financial_expense_rows(),
    "{{FINANCIAL_DESKTOP_NOTES}}": financial_notes("desktop"),
    "{{FINANCIAL_MOBILE_NOTES}}": financial_notes("mobile"),
    "{{FINANCIAL_VISUALS}}": financial_visuals(),
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
