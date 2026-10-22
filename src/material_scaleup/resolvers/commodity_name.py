from collections.abc import Mapping, Sequence
from difflib import SequenceMatcher
from math import isclose

__all__ = ["resolve_commodity_name"]

_MIN_SIMILARITY = 0.95
_MIN_MARGIN = 0.05


def _normalize(name: str) -> str:
    return " ".join(name.casefold().split())


def resolve_commodity_name(
    commodity: str,
    *,
    commodities: Sequence[str],
    aliases: Mapping[str, str],
) -> str | None:
    """Return a catalog name using aliases, exact lookup, then conservative similarity.

    Similarity scores are lexical heuristics, not chemical-equivalence probabilities.
    Missing alias targets, ambiguous names, and weak matches remain unresolved.
    """
    query = _normalize(commodity)
    if not query:
        return None

    catalog: dict[str, set[str]] = {}
    for name in commodities:
        normalized = _normalize(name)
        if normalized:
            catalog.setdefault(normalized, set()).add(name)

    def canonical_name(normalized: str) -> str | None:
        names = catalog.get(normalized, set())
        return next(iter(names)) if len(names) == 1 else None

    for alias, target in aliases.items():
        if _normalize(alias) == query:
            return canonical_name(_normalize(target))

    if query in catalog:
        return canonical_name(query)

    ranked = sorted(
        ((SequenceMatcher(None, query, name, autojunk=False).ratio(), name) for name in catalog),
        key=lambda match: (-match[0], match[1]),
    )
    if not ranked:
        return None

    score, name = ranked[0]
    if score < _MIN_SIMILARITY:
        return None
    if len(ranked) > 1:
        margin = score - ranked[1][0]
        if margin < _MIN_MARGIN and not isclose(margin, _MIN_MARGIN, abs_tol=1e-12):
            return None

    query_words = query.split()
    candidate_words = name.split()
    # Do not discard qualifiers or fuzzy-match short grade/region identifiers.
    if len(query_words) != len(candidate_words) or any(
        left != right and min(len(left), len(right)) <= 3
        for left, right in zip(query_words, candidate_words, strict=True)
    ):
        return None

    return canonical_name(name)
