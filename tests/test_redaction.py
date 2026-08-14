from weypay.redaction import redact


def test_redacts_top_level_secret_key() -> None:
    result = redact({"MbWayKey": "secret-123", "canal": "03"}, frozenset({"MbWayKey"}))
    assert result == {"MbWayKey": "***", "canal": "03"}


def test_redacts_nested_dict() -> None:
    payload = {"beneficiaries": [{"externKey": "secret-1"}, {"externKey": "secret-2"}]}
    result = redact(payload, frozenset({"externKey"}))
    assert result == {"beneficiaries": [{"externKey": "***"}, {"externKey": "***"}]}


def test_does_not_touch_keys_not_listed() -> None:
    result = redact({"amount": "20.00", "identifier": "abc"}, frozenset({"chave"}))
    assert result == {"amount": "20.00", "identifier": "abc"}


def test_leaves_non_dict_non_list_values_untouched() -> None:
    assert redact("plain string", frozenset({"x"})) == "plain string"
    assert redact(42, frozenset({"x"})) == 42
    assert redact(None, frozenset({"x"})) is None


def test_no_secret_survives_deeply_nested_structure() -> None:
    payload = {
        "level1": {"level2": [{"level3": {"MbWayKey": "leak"}}, {"other": "MbWayKey"}]},
    }
    result = redact(payload, frozenset({"MbWayKey"}))
    assert "leak" not in str(result)
    # a string "MbWayKey" como *valor* (não chave) não é um segredo e não é tocada
    assert result["level1"]["level2"][1]["other"] == "MbWayKey"
