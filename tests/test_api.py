EXAMPLE = {
    "list_1": ["first string", "second string", "third string"],
    "list_2": ["other string", "another string", "last string"],
}
EXPECTED_OUTPUT = (
    "FIRST STRING, OTHER STRING, SECOND STRING, "
    "ANOTHER STRING, THIRD STRING, LAST STRING"
)


def test_create_then_read_payload(client):
    created = client.post("/payload", json=EXAMPLE)
    assert created.status_code == 201

    response = client.get(f"/payload/{created.json()['id']}")
    assert response.status_code == 200
    assert response.json() == {"output": EXPECTED_OUTPUT}


def test_repeated_post_reuses_id_and_skips_transformer(client, transformer):
    first = client.post("/payload", json=EXAMPLE)
    calls_after_first = len(transformer.calls)

    second = client.post("/payload", json=EXAMPLE)

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    # Повторный вход не должен вызывать transformer ни разу.
    assert len(transformer.calls) == calls_after_first


def test_partial_overlap_transforms_only_new_strings(client, transformer):
    client.post("/payload", json={"list_1": ["a", "b"], "list_2": ["c", "d"]})
    transformer.calls.clear()

    response = client.post("/payload", json={"list_1": ["a", "x"], "list_2": ["c", "y"]})

    assert response.status_code == 201
    # "a" и "c" уже в кэше, трансформируются только новые "x" и "y".
    assert sorted(transformer.calls) == ["x", "y"]


def test_duplicates_within_request_transformed_once(client, transformer):
    client.post("/payload", json={"list_1": ["a", "a"], "list_2": ["a", "b"]})

    assert sorted(transformer.calls) == ["a", "b"]


def test_different_order_creates_different_payload(client):
    first = client.post("/payload", json={"list_1": ["a"], "list_2": ["b"]})
    second = client.post("/payload", json={"list_1": ["b"], "list_2": ["a"]})

    assert first.json()["id"] != second.json()["id"]


def test_read_unknown_payload_returns_404(client):
    assert client.get("/payload/999").status_code == 404


def test_different_lengths_return_422(client):
    response = client.post("/payload", json={"list_1": ["a"], "list_2": []})

    assert response.status_code == 422


def test_empty_lists_give_empty_output(client):
    # Зафиксированное решение: пустой вход допустим и даёт пустой output.
    created = client.post("/payload", json={"list_1": [], "list_2": []})

    assert created.status_code == 201
    output = client.get(f"/payload/{created.json()['id']}").json()["output"]
    assert output == ""