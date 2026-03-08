from __future__ import annotations


def validate_proxy_link(link: str) -> bool:
    return link.startswith("https://t.me/proxy?") or link.startswith("tg://proxy?")


def parse_request_id(data: str | None, prefix: str) -> int | None:
    if data is None or not data.startswith(prefix):
        return None

    raw_request_id = data.split(":", maxsplit=1)[1]
    try:
        return int(raw_request_id)
    except ValueError:
        return None


def username_or_dash(username: str | None) -> str:
    return f"@{username}" if username else "-"
