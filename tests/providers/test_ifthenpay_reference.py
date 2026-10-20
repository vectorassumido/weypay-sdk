import pytest

from weypay.providers.ifthenpay import reference


@pytest.mark.parametrize("system", ["bookwey", "p8a", "boxwey"])
def test_new_reference_has_the_right_prefix_and_length(system: str) -> None:
    ref = reference.new_reference(system)

    assert len(ref) == reference.REFERENCE_MAX_LENGTH
    assert ref.startswith(reference.SYSTEM_PREFIXES[system])
    assert ref.isdigit()  # o PINPAY exige um `id` numérico — ver pinpay.py


def test_new_reference_is_not_deterministic() -> None:
    assert reference.new_reference("bookwey") != reference.new_reference("bookwey")


def test_new_reference_unknown_system_raises() -> None:
    with pytest.raises(KeyError):
        reference.new_reference("unknown-system")


def test_has_prefix_true_for_matching_system() -> None:
    ref = reference.new_reference("boxwey")
    assert reference.has_prefix(ref, "boxwey") is True


def test_has_prefix_false_for_a_different_system() -> None:
    ref = reference.new_reference("boxwey")
    assert reference.has_prefix(ref, "p8a") is False


def test_has_prefix_unknown_system_raises() -> None:
    with pytest.raises(KeyError):
        reference.has_prefix("73" + "1" * 13, "unknown-system")


def test_system_prefixes_match_the_decided_values() -> None:
    assert reference.SYSTEM_PREFIXES == {"bookwey": "71", "p8a": "72", "boxwey": "73"}
