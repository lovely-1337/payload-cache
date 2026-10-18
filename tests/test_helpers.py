from app.service import compute_input_hash, interleave


def test_interleave_alternates_items():
    assert interleave(["a", "b"], ["x", "y"]) == ["a", "x", "b", "y"]


def test_interleave_empty_lists():
    assert interleave([], []) == []


def test_hash_is_deterministic():
    assert compute_input_hash(["a"], ["b"]) == compute_input_hash(["a"], ["b"])


def test_hash_depends_on_list_order():
    # (a, b) и (b, a) дают разный output, значит, хэши обязаны различаться.
    assert compute_input_hash(["a"], ["b"]) != compute_input_hash(["b"], ["a"])


def test_hash_has_no_delimiter_collisions():
    # При наивной склейке через запятую эти входы совпали бы.
    assert compute_input_hash(["a,b"], []) != compute_input_hash(["a"], ["b"])