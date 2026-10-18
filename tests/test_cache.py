from app.service import get_transformed


def test_transforms_each_unique_string_once(session, transformer):
    result = get_transformed(session, ["a", "b", "a"], transformer)

    assert result == {"a": "A", "b": "B"}
    # "a" встретилась дважды, но вызов был один.
    assert sorted(transformer.calls) == ["a", "b"]


def test_reuses_cached_strings(session, transformer):
    get_transformed(session, ["a", "b"], transformer)
    transformer.calls.clear()

    result = get_transformed(session, ["a", "c"], transformer)

    assert result == {"a": "A", "c": "C"}
    # Из кэша взяли "a", transformer вызван только для новой "c".
    assert transformer.calls == ["c"]


def test_empty_input_does_nothing(session, transformer):
    assert get_transformed(session, [], transformer) == {}
    assert transformer.calls == []
