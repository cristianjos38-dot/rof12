from app.domain.enums import Decision, DenyReason


def test_decision_is_default_deny_compatible():
    assert Decision.DENY.value == "DENY"
    assert DenyReason.DEFAULT_DENY.value == "DEFAULT_DENY"

