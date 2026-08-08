"""Unit tests for the pure search / index helpers."""

from demo import search


def test_location_index_roundtrip():
    text = "ab\ncd\nefgh\n"
    for index in range(len(text)):
        location = search.index_to_location(text, index)
        assert search.location_to_index(text, location) == index


def test_index_to_location():
    text = "ab\ncd\nefgh\n"
    assert search.index_to_location(text, 0) == (0, 0)
    assert search.index_to_location(text, 1) == (0, 1)
    assert search.index_to_location(text, 3) == (1, 0)
    assert search.index_to_location(text, 5) == (1, 2)
    assert search.index_to_location(text, 6) == (2, 0)
    assert search.index_to_location(text, 10) == (2, 4)


def test_location_to_index():
    text = "ab\ncd\nefgh\n"
    assert search.location_to_index(text, (0, 0)) == 0
    assert search.location_to_index(text, (1, 0)) == 3
    assert search.location_to_index(text, (2, 4)) == 10
    # Clamping
    assert search.location_to_index(text, (2, 99)) == 10
    assert search.location_to_index(text, (99, 0)) == len(text)


def test_find_all():
    text = "Foo foo FOO"
    matches = search.find_all(text, "foo")
    assert matches == [(0, 3), (4, 7), (8, 11)]


def test_find_all_case_sensitive():
    text = "Foo foo"
    assert search.find_all(text, "foo", case_sensitive=True) == [(4, 7)]


def test_find_all_empty_query():
    assert search.find_all("anything", "") == []


def test_next_match_forward():
    text = "a b a b"
    assert search.next_match(text, "a", 0) == (0, 1)
    assert search.next_match(text, "a", 1) == (4, 5)
    assert search.next_match(text, "a", 5) == (0, 1)  # wraps


def test_next_match_backward():
    text = "a b a b"
    assert search.next_match(text, "a", 6, direction=-1) == (4, 5)
    assert search.next_match(text, "a", 1, direction=-1) == (4, 5)  # wraps past the end
    assert search.next_match(text, "a", 5, direction=-1) == (0, 1)
    assert search.next_match(text, "a", 4, direction=-1) == (0, 1)  # excludes current match


def test_next_match_no_match():
    assert search.next_match("abc", "z", 0) is None
