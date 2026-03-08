from __future__ import annotations

from axiomai_proxy.infrastructure.telegram.common import parse_request_id, username_or_dash, validate_proxy_link


def test_validate_proxy_link_accepts_t_me_link() -> None:
    assert validate_proxy_link("https://t.me/proxy?server=1.1.1.1&port=443&secret=abc") is True


def test_validate_proxy_link_accepts_tg_link() -> None:
    assert validate_proxy_link("tg://proxy?server=1.1.1.1&port=443&secret=abc") is True


def test_validate_proxy_link_rejects_other_links() -> None:
    assert validate_proxy_link("https://example.com/proxy") is False


def test_parse_request_id_returns_int() -> None:
    assert parse_request_id("bank_confirm:123", "bank_confirm:") == 123


def test_parse_request_id_returns_none_for_invalid_data() -> None:
    assert parse_request_id("bank_confirm:abc", "bank_confirm:") is None
    assert parse_request_id("bank_reject:1", "bank_confirm:") is None
    assert parse_request_id(None, "bank_confirm:") is None


def test_username_or_dash_formats_username() -> None:
    assert username_or_dash("kirill") == "@kirill"
    assert username_or_dash(None) == "-"
    assert username_or_dash("") == "-"
