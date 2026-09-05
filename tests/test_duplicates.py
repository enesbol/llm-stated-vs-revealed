from stated_vs_revealed import check_duplicates


def test_no_duplicates():
    rep = check_duplicates.detect("A", ["one", "two", "three"])
    assert rep.duplicate_rate == 0.0
    assert rep.exact_duplicate_indices == []


def test_exact_duplicate_detected_once_per_repeat():
    rep = check_duplicates.detect("A", ["x", "x", "y", "x"])
    assert rep.exact_duplicate_indices == [1, 3]
    assert rep.duplicate_rate == 2 / 4


def test_normalized_duplicate_catches_whitespace_and_case_variants():
    rep = check_duplicates.detect("A", ["Hello World", "hello   world", "different"])
    assert rep.normalized_duplicate_indices == [1]
    assert rep.exact_duplicate_indices == []


def test_over_threshold():
    rep = check_duplicates.detect("A", ["x", "x", "y", "z"])
    assert check_duplicates.over_threshold(rep, 0.15) is True
    assert check_duplicates.over_threshold(rep, 0.30) is False


def test_empty_input():
    rep = check_duplicates.detect("A", [])
    assert rep.duplicate_rate == 0.0
