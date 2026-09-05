"""The Replit surface proxies only fixed, bounded backend requests."""

from __future__ import annotations

import gzip

import httpx
import pytest
from fastapi.testclient import TestClient

from duty_of_care import backend_proxy
from duty_of_care.main import app

_ORIGINAL_ASYNC_CLIENT = httpx.AsyncClient


class _BytesStream(httpx.AsyncByteStream):
    def __init__(self, content: bytes) -> None:
        self.content = content

    async def __aiter__(self):
        yield self.content


class _SlowStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        import asyncio

        await asyncio.sleep(0.02)
        yield b'{"event":"result","ok":true}\n'


@pytest.fixture
def proxy_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("REPL_ID", "replit-test")
    monkeypatch.setenv("DUTY_OF_CARE_BACKEND_URL", "https://backend.example")
    monkeypatch.delenv("VERTEX_SEARCH_DATA_STORE", raising=False)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.headers["accept-encoding"] == "identity"
        if request.url.path == "/v1/presets":
            return httpx.Response(307, headers={"location": "https://evil.example"})
        if request.url.path == "/health":
            return httpx.Response(
                200,
                headers={"content-type": "application/json", "content-encoding": "gzip"},
                stream=_BytesStream(gzip.compress(b'{"status":"healthy"}')),
            )
        if request.url.path == "/v1/review/stream":
            return httpx.Response(
                200,
                headers={
                    "content-type": "application/x-ndjson",
                    "content-encoding": "gzip",
                    "location": "https://evil.example",
                },
                stream=_BytesStream(
                    gzip.compress(b'{"event":"parsed"}\n{"event":"result","ok":true}\n')
                ),
            )
        content = (
            '{"proxied":true,"path":"'
            + request.url.path
            + '","query":"'
            + request.url.query.decode()
            + '"}'
        ).encode()
        return httpx.Response(
            200,
            headers={"content-type": "application/json", "x-upstream-secret": "hidden"},
            stream=_BytesStream(content),
        )

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        backend_proxy.httpx,
        "AsyncClient",
        lambda **kwargs: _ORIGINAL_ASYNC_CLIENT(transport=transport, **kwargs),
    )
    return TestClient(app), seen


def test_exact_allowlist_uses_only_fixed_origin(proxy_client) -> None:
    client, seen = proxy_client
    response = client.get("/v1/resources?region=US")
    assert response.status_code == 200
    assert response.json()["proxied"] is True
    assert str(seen[0].url) == "https://backend.example/v1/resources?region=US"
    assert "x-upstream-secret" not in response.headers

    # Writer identity and persistence endpoints always remain on this app.
    assert client.get("/v1/me").json()["data"]["runtime"]["on_replit"] is True
    assert len(seen) == 1


def test_stream_is_proxied_without_forwarding_unsafe_headers(proxy_client) -> None:
    client, seen = proxy_client
    response = client.post("/v1/review/stream", json={"screenplay": "INT. ROOM\nA safe line."})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert "location" not in response.headers
    assert response.text.endswith('{"event":"result","ok":true}\n')
    assert seen[0].url.path == "/v1/review/stream"


def test_compressed_buffered_response_remains_usable(proxy_client) -> None:
    client, seen = proxy_client
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert response.headers["content-encoding"] == "gzip"
    assert seen[0].headers["accept-encoding"] == "identity"


def test_oversized_request_is_rejected_before_network(proxy_client, monkeypatch) -> None:
    client, seen = proxy_client
    monkeypatch.setattr(backend_proxy, "MAX_REQUEST_BYTES", 20)
    response = client.post("/v1/review", content=b"x" * 21)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"
    assert seen == []


def test_non_allowlisted_method_stays_local(proxy_client) -> None:
    client, seen = proxy_client
    assert client.get("/v1/review").status_code == 405
    assert seen == []


def test_invalid_backend_origin_fails_closed(proxy_client, monkeypatch) -> None:
    client, seen = proxy_client
    monkeypatch.setenv("DUTY_OF_CARE_BACKEND_URL", "https://backend.example/attacker-path")
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "backend_proxy_not_configured"
    assert seen == []


def test_backend_redirect_is_not_followed(proxy_client) -> None:
    client, seen = proxy_client
    response = client.get("/v1/presets")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "backend_redirect_rejected"
    assert seen[0].url == "https://backend.example/v1/presets"


def test_oversized_stream_ends_with_explicit_error(proxy_client, monkeypatch) -> None:
    client, _seen = proxy_client
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "application/x-ndjson"},
            stream=_BytesStream(b"x" * 600),
        )
    )
    monkeypatch.setattr(
        backend_proxy.httpx,
        "AsyncClient",
        lambda **kwargs: _ORIGINAL_ASYNC_CLIENT(transport=transport, **kwargs),
    )
    monkeypatch.setattr(backend_proxy, "MAX_RESPONSE_BYTES", 512)
    response = client.post("/v1/review/stream", json={"screenplay": "INT. ROOM\nLine."})
    assert '"event": "error"' in response.text
    assert "backend_response_too_large" in response.text
    assert len(response.content) <= backend_proxy.MAX_RESPONSE_BYTES


def test_timed_out_stream_ends_with_explicit_error(
    proxy_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _seen = proxy_client
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "application/x-ndjson"},
            stream=_SlowStream(),
        )
    )
    monkeypatch.setattr(
        backend_proxy.httpx,
        "AsyncClient",
        lambda **kwargs: _ORIGINAL_ASYNC_CLIENT(transport=transport, **kwargs),
    )
    monkeypatch.setattr(backend_proxy, "TOTAL_TIMEOUT_SECONDS", 0.005)
    response = client.post("/v1/review/stream", json={"screenplay": "INT. ROOM\nLine."})
    assert '"event": "error"' in response.text
    assert "backend_timeout" in response.text
    assert '"event":"result"' not in response.text