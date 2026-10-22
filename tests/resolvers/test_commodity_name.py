from difflib import SequenceMatcher

import pytest

from material_scaleup.resolvers.commodity_name import resolve_commodity_name


@pytest.mark.parametrize(
    ("query", "catalog", "aliases", "expected"),
    [
        ("aluminium", ["Aluminum"], {"aluminium": "Aluminum"}, "Aluminum"),
        ("ore", ["Ore", "Copper"], {"ore": "Copper"}, "Copper"),
        ("ore", ["Ore"], {"ore": "Copper"}, None),
        ("aluminum", ["Aluminium"], {"aluminum": "Aluminum"}, None),
        ("  PHOSPHATE \t ROCK ", ["Phosphate rock"], {}, "Phosphate rock"),
        (
            "  PHOSPHATE \t ROCK ",
            ["Phosphate Rock"],
            {"phosphate rock": "Phosphate rock"},
            "Phosphate Rock",
        ),
        ("Gold", ["Gold"], {}, "Gold"),
        ("Phosphate rock", ["Phosphate rock", "Phosphate rocks"], {}, "Phosphate rock"),
        ("Phosphate rocck", ["Phosphate rock", "Copper"], {}, "Phosphate rock"),
        ("", ["Copper"], {}, None),
        (" \t\n", ["Copper"], {}, None),
        ("Copper", [], {}, None),
        ("Copper", ["", "  "], {}, None),
        ("unobtainium", ["Copper", "Aluminum"], {}, None),
        ("silicone", ["Silicon"], {}, None),
        ("silicon", ["Silicone"], {}, None),
        ("silica", ["Silicon"], {}, None),
        ("Natural gas (U.S.)", ["Natural gas (Canada)"], {}, None),
        ("Phosphate rock grade A", ["Phosphate rock grade B"], {}, None),
        ("Phosphate rock", ["Phosphate rock A"], {}, None),
        ("Nickel sulfate", ["Nickel"], {}, None),
        ("Copper", ["Copper", "COPPER"], {}, None),
        ("Phosphate rock", ["Phosphate rock", "Phosphate  rock"], {}, None),
        ("Phosphate rocck", ["Phosphate rock", "PHOSPHATE ROCK"], {}, None),
        ("ore", ["Copper", "COPPER"], {"ore": "Copper"}, None),
        ("Copper", ["Copper", "Copper"], {}, "Copper"),
    ],
)
def test_resolve_commodity_name(query, catalog, aliases, expected):
    assert resolve_commodity_name(query, commodities=catalog, aliases=aliases) == expected
    assert (
        resolve_commodity_name(query, commodities=list(reversed(catalog)), aliases=aliases)
        == expected
    )


@pytest.mark.parametrize(
    "catalog",
    [
        ["Phosphate rock grade A", "Phosphate rock grade B"],
        ["Phosphate rock", "Phosphate rocks"],
    ],
)
def test_rejects_ties_and_close_runner_up(catalog):
    query = "Phosphate rock grade C" if catalog[0].endswith(" A") else "Phosphate rocck"
    scores = sorted(
        [SequenceMatcher(None, query.casefold(), name.casefold()).ratio() for name in catalog],
        reverse=True,
    )
    assert scores[0] >= 0.95
    assert scores[0] - scores[1] < 0.05
    assert resolve_commodity_name(query, commodities=catalog, aliases={}) is None


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("abcdefghijklmnopqrsX", "abcdefghijklmnopqrst"),
        ("abcdefghijklmnopqrXX", None),
    ],
)
def test_similarity_threshold(query, expected):
    assert (
        resolve_commodity_name(query, commodities=["abcdefghijklmnopqrst"], aliases={}) == expected
    )


@pytest.mark.parametrize(
    ("runner_up", "expected"),
    [
        ("abcdefghijklmnopqrXX", "abcdefghijklmnopqrsX"),
        ("abcdefghijklmnopqrX", None),
    ],
)
def test_runner_up_margin_boundary(runner_up, expected):
    assert (
        resolve_commodity_name(
            "abcdefghijklmnopqrst",
            commodities=["abcdefghijklmnopqrsX", runner_up],
            aliases={},
        )
        == expected
    )


@pytest.mark.parametrize(
    ("query", "candidate"),
    [
        ("Phosphate rock grade", "Phosphate rock grade A"),
        ("Phosphate rock grade A", "Phosphate rock grade B"),
    ],
)
def test_preserves_qualifiers_even_above_similarity_threshold(query, candidate):
    assert SequenceMatcher(None, query, candidate).ratio() >= 0.95
    assert resolve_commodity_name(query, commodities=[candidate], aliases={}) is None
