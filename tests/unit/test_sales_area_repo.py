from datetime import date

from app.repositories.sales_area_repo import _filter_conditions


def test_no_filters_returns_nothing():
    args: list = []
    assert _filter_conditions(None, None, None, None, None, args) == []
    assert args == []


def test_placeholders_continue_from_existing_args():
    """Callers pre-seed args (e.g. area = $1); filters must number from $2."""
    args: list = ["Indore"]
    conditions = _filter_conditions(date(2024, 1, 1), None, "Widget A", None, None, args)
    assert conditions == ["month >= $2", "item = $3"]
    assert args == ["Indore", date(2024, 1, 1), "Widget A"]


def test_all_filters_in_fixed_order():
    args: list = []
    conditions = _filter_conditions(
        date(2024, 1, 1), date(2024, 12, 31), "Widget A", ["G1", "G2"], "452001", args
    )
    assert conditions == [
        "month >= $1",
        "month <= $2",
        "item = $3",
        "stock_group = ANY($4)",
        "pincode = $5",
    ]
    assert args[3] == ["G1", "G2"]


def test_empty_stock_group_list_is_ignored():
    args: list = []
    assert _filter_conditions(None, None, None, [], None, args) == []
    assert args == []


def test_empty_strings_are_ignored():
    args: list = []
    assert _filter_conditions(None, None, "", None, "", args) == []
