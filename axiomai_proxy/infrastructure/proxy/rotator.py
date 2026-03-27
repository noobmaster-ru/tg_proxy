from __future__ import annotations

import asyncio
from dataclasses import dataclass
from secrets import token_hex

import docker  # type: ignore[import-untyped]


@dataclass(frozen=True)
class ProxyRotationResult:
    secret: str
    proxy_link: str


class ProxySecretRotator:
    def __init__(self, server: str, port: int, container_name: str) -> None:
        self._server = server
        self._port = port
        self._container_name = container_name

    async def rotate(self) -> ProxyRotationResult:
        return await asyncio.to_thread(self._rotate_sync)

    def _rotate_sync(self) -> ProxyRotationResult:
        secret = token_hex(16)

        client = docker.from_env()
        try:
            container = client.containers.get(self._container_name)
            exit_code, output = container.exec_run(
                [
                    "sh",
                    "-lc",
                    "printf '%s' \"$PROXY_SECRET\" > /data/secret && "
                    "printf '%s' \"$PROXY_SECRET\" > /data/proxy-secret",
                ],
                environment={"PROXY_SECRET": secret},
            )
            if exit_code != 0:
                error_text = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else str(output)
                raise RuntimeError(f"failed to update proxy secret inside container: {error_text}")

            container.restart(timeout=10)
        finally:
            client.close()

        return ProxyRotationResult(secret=secret, proxy_link=self._build_proxy_link(secret))

    def _build_proxy_link(self, secret: str) -> str:
        return f"https://t.me/proxy?server={self._server}&port={self._port}&secret={secret}"
