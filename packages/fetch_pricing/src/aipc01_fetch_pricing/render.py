"""Price List JSON to markdown tables, one table per product family."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any


def format_price(raw: str) -> str:
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return raw
    text = f"{value:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _term_label(term: dict[str, Any]) -> str:
    attrs = term.get("termAttributes") or {}
    if not attrs:
        return "OnDemand"
    return "Reserved " + " ".join(
        v for v in (attrs.get("LeaseContractLength"), attrs.get("PurchaseOption")) if v
    )


def _escape(cell: str) -> str:
    return cell.replace("|", "\\|").replace("\n", " ").strip()


def _item(attrs: dict[str, str]) -> str:
    parts = [
        attrs.get(k, "") for k in ("model", "feature", "inferenceType", "usagetype") if attrs.get(k)
    ]
    return " / ".join(dict.fromkeys(parts[:3])) or attrs.get("usagetype", "")


def rows_by_family(offer: dict[str, Any]) -> dict[str, list[list[str]]]:
    """family -> table rows [item, term, unit, range, USD, description, usage type]."""
    products = offer.get("products", {})
    families: dict[str, list[list[str]]] = defaultdict(list)
    for term_type, by_sku in offer.get("terms", {}).items():
        for sku, terms in by_sku.items():
            product = products.get(sku)
            if not product:
                continue
            attrs = product.get("attributes", {})
            for term in terms.values():
                label = (
                    _term_label(term)
                    if term_type != "OnDemand" or term.get("termAttributes")
                    else "OnDemand"
                )
                for dim in term.get("priceDimensions", {}).values():
                    usd = dim.get("pricePerUnit", {}).get("USD")
                    if usd is None:
                        continue
                    begin, end = dim.get("beginRange", "0"), dim.get("endRange", "Inf")
                    tier = "" if (begin, end) == ("0", "Inf") else f"{begin} to {end}"
                    families[product.get("productFamily") or "Other"].append(
                        [
                            _item(attrs),
                            label,
                            dim.get("unit", ""),
                            tier,
                            format_price(usd),
                            dim.get("description", ""),
                            attrs.get("usagetype", ""),
                        ]
                    )
    return families


def render_family(family: str, rows: list[list[str]]) -> str:
    header = "| Item | Term | Unit | Tier | USD | Description | Usage type |"
    lines = [header, "|" + "---|" * 7]
    for row in sorted(rows):
        lines.append("| " + " | ".join(_escape(c) for c in row) + " |")
    return "\n".join(lines)
