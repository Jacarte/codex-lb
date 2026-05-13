import pytest

from app.modules.proxy.load_balancer import _classify_public_selection_error


pytestmark = pytest.mark.unit


def test_classify_public_selection_error_maps_generic_exhaustion_to_service_unavailable() -> None:
    assert _classify_public_selection_error("No available accounts") == (
        503,
        "service_unavailable",
        "server_error",
        None,
    )


def test_classify_public_selection_error_maps_rate_limit_message_to_rate_limit_error() -> None:
    assert _classify_public_selection_error("Rate limit exceeded. Try again in 42s") == (
        429,
        "rate_limit_exceeded",
        "rate_limit_error",
        42,
    )
