"""Trade category candidates are not substituted chemical identities."""

import re
from difflib import SequenceMatcher

from material_scaleup.models.trade import TradeMatch, TradeProduct


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


# Pilot categories are deliberately broad or form-dependent.
PILOT_CATEGORIES: dict[str, tuple[tuple[str, ...], str]] = {
    "sodium aluminate": (
        ("284190",),
        "Other oxometallic/peroxometallic salts; not specific to sodium aluminate.",
    ),
    "sodium silicate": (
        ("283911", "283919"),
        "Distinguish sodium metasilicates from other sodium silicates.",
    ),
    "sodium hydroxide": (
        ("281511", "281512"),
        "Distinguish solid sodium hydroxide from aqueous solution.",
    ),
    "caustic soda": (
        ("281511", "281512"),
        "Distinguish solid sodium hydroxide from aqueous solution.",
    ),
    "urea": (("310210",), "This category includes urea whether or not in aqueous solution."),
}


def find_trade_matches(material: str, catalog: list[TradeProduct]) -> list[TradeMatch]:
    name = _normalize(material)
    if not name:
        return []
    products = {product.code: product for product in catalog}
    if name in PILOT_CATEGORIES:
        codes, reason = PILOT_CATEGORIES[name]
        return [
            TradeMatch(
                requested_material=material.strip(),
                product=products[code],
                relationship="broader",
                reason=reason,
            )
            for code in codes
            if code in products
        ]
    ranked: list[tuple[float, TradeProduct]] = []
    for product in catalog:
        description = _normalize(product.description)
        if name == product.code:
            score = 1.0
        else:
            tokens = set(name.split())
            overlap = len(tokens & set(description.split())) / len(tokens)
            similarity = SequenceMatcher(None, name, description).ratio()
            score = max(similarity, overlap * 0.85)
        if score >= 0.55:
            ranked.append((score, product))
    ranked.sort(key=lambda item: (-item[0], item[1].code))
    return [
        TradeMatch(
            requested_material=material.strip(),
            product=product,
            relationship="candidate",
            reason=(
                "Catalog search suggestion only, not verified chemical equivalence. "
                "Confirm form, concentration and category scope before use."
            ),
        )
        for _, product in ranked[:8]
    ]
