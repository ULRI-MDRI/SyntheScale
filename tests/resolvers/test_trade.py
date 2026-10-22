from material_scaleup.models.trade import TradeProduct
from material_scaleup.resolvers.trade import find_trade_matches

CATALOG = [
    TradeProduct(code="281511", description="Sodium hydroxide (caustic soda); solid"),
    TradeProduct(code="281512", description="Sodium hydroxide; aqueous solution"),
    TradeProduct(code="283911", description="Sodium metasilicates"),
    TradeProduct(code="283919", description="Sodium silicates; other"),
    TradeProduct(code="284190", description="Oxometallic salts; other"),
]


def test_pilot_candidates_require_confirmation_and_preserve_form():
    candidates = find_trade_matches(" SODIUM  HYDROXIDE ", CATALOG)
    assert [item.product.code for item in candidates] == ["281511", "281512"]
    assert all(item.requires_confirmation for item in candidates)
    assert all(item.relationship == "broader" for item in candidates)
    assert "solid" in candidates[0].reason


def test_broad_aluminate_does_not_become_exact_material():
    candidates = find_trade_matches("sodium aluminate", CATALOG)
    assert candidates[0].product.code == "284190"
    assert candidates[0].relationship == "broader"


def test_generic_similar_search_never_asserts_chemical_equivalence():
    candidates = find_trade_matches("sodium hydroxid", CATALOG)
    assert candidates
    assert all(
        item.relationship == "candidate" and item.requires_confirmation for item in candidates
    )


def test_no_mapping_or_empty_input():
    assert find_trade_matches("", CATALOG) == []
    assert find_trade_matches("unobtainium", CATALOG) == []
    assert find_trade_matches("sodium aluminate", []) == []


def test_user_entered_hs_code_still_requires_scope_confirmation():
    candidates = find_trade_matches("281511", CATALOG)
    assert candidates[0].product.code == "281511"
    assert candidates[0].requires_confirmation
