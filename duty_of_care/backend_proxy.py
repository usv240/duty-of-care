"""Strict proxy from the Replit product surface to the Google backend."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncIterator
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from . import replit_platform

MAX_REQUEST_BYTES = 2_000_000
MAX_RESPONSE_BYTES = 10_000_000
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 90.0
TOTAL_TIMEOUT_SECONDS = 120.0
STREAM_ERROR_RESERVE_BYTES = 512

ALLOWED: dict[str, frozenset[str]] = {
    "/v1/resources": frozenset({"GET"}),
    "/v1/guidance": frozenset({"GET"}),
    "/v1/presets": frozenset({"GET"}),
    "/v1/samples": frozenset({"GET"}),
    "/v1/review": frozenset({"POST"}),
    "/v1/review/stream": frozenset({"POST"}),
    "/v1/report": frozenset({"POST"}),
    "/v1/eval/latest": frozenset({"GET"}),
    "/v1/keys": frozenset({"POST"}),
}

REQUEST_HEADERS = frozenset({"accept", "authorization", "content-type", "x-api-key"})
RESPONSE_HEADERS = frozenset(
    {"cache-control", "content-disposition", "content-encoding", "content-type"}
)


def enabled() -> bool:
    """Proxy only on Replit when the Google retrieval stack is not local."""
    return bool(
        replit_platform.runtime()["on_replit"]
        and os.getenv("DUTY_OF_CARE_BACKEND_URL")
        and not os.getenv("VERTEX_SEARCH_DATA_STORE")
    )


def _upstream_url(path: str, query: str) -> str:
    configured = os.environ["DUTY_OF_CARE_BACKEND_URL"].strip()
    parsed = urlsplit(configured)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("DUTY_OF_CARE_BACKEND_URL must be an HTTPS origin without credentials")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("DUTY_OF_CARE_BACKEND_URL must not contain a path, query, or fragment")
    return urlunsplit((parsed.scheme, parsed.netloc, path, query, ""))


def _error(status: int, code: str, message: str, fix: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "ok": False,
            "error": {"code": code, "message": message, "fix": fix, "docs": "/docs"},
        },
    )


def _safe_response_headers(headers: httpx.Headers) -> dict[str, str]:
    return {key: value for key, value in headers.items() if key.lower() in RESPONSE_HEADERS}


async def _read_body(request: Request) -> bytes:
    declared = request.headers.get("content-length")
    if declared:
        try:
            if int(declared) > MAX_REQUEST_BYTES:
                raise OverflowError
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_REQUEST_BYTES:
            raise OverflowError
    return bytes(body)


async def _buffered_response(upstream: httpx.Response) -> Response:
    declared = upstream.headers.get("content-length")
    if declared:
        try:
            if int(declared) > MAX_RESPONSE_BYTES:
                raise OverflowError
        except ValueError as exc:
            raise httpx.ProtocolError("invalid upstream Content-Length") from exc
    content = bytearray()
    async for chunk in upstream.aiter_raw():
        content.extend(chunk)
        if len(content) > MAX_RESPONSE_BYTES:
            raise OverflowError
    return Response(
        content=bytes(content),
        status_code=upstream.status_code,
        headers=_safe_response_headers(upstream.headers),
    )


async def _stream_body(
    upstream: httpx.Response, client: httpx.AsyncClient, started: float
) -> AsyncIterator[bytes]:
    size = 0
    payload_limit = MAX_RESPONSE_BYTES - STREAM_ERROR_RESERVE_BYTES
    iterator = upstream.aiter_raw().__aiter__()
    try:
        while True:
            remaining = TOTAL_TIMEOUT_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError
            try:
                async with asyncio.timeout(remaining):
                    chunk = await iterator.__anext__()
            except StopAsyncIteration:
                break
            if size + len(chunk) > payload_limit:
                raise OverflowError
            size += len(chunk)
            yield chunk
    except (httpx.TimeoutException, TimeoutError):
        error = (
            json.dumps(
                {
                    "event": "error",
                    "ok": False,
                    "status": 504,
                    "error": {
                        "code": "backend_timeout",
                        "message": "The fixed backend stream exceeded the proxy deadline.",
                        "fix": "Retry shortly; no guidance result was fabricated.",
                        "docs": "/docs",
                    },
                }
            )
            + "\n"
        ).encode()
        if size + len(error) <= MAX_RESPONSE_BYTES:
            yield error
    except OverflowError:
        error = (
            json.dumps(
                {
                    "event": "error",
                    "ok": False,
                    "status": 502,
                    "error": {
                        "code": "backend_response_too_large",
                        "message": "The backend stream exceeded the proxy response limit.",
                        "fix": "Retry with a smaller review.",
                        "docs": "/docs",
                    },
                }
            )
            + "\n"
        ).encode()
        if size + len(error) <= MAX_RESPONSE_BYTES:
            yield error
    finally:
        await upstream.aclose()
        await client.aclose()


async def proxy_request(request: Request) -> Response | None:
    """Return a proxied response, or ``None`` when the local route should run."""
    if not enabled():
        return None
    methods = ALLOWED.get(request.url.path)
    if methods is None or request.method not in methods:
        return None

    try:
        url = _upstream_url(request.url.path, request.url.query)
        body = await _read_body(request)
    except OverflowError:
        return _error(
            413,
            "request_too_large",
            f"The proxy accepts at most {MAX_REQUEST_BYTES} request bytes.",
            "Send a smaller screenplay or request envelope.",
        )
    except ValueError as exc:
        return _error(
            503,
            "backend_proxy_not_configured",
            str(exc),
            "Set DUTY_OF_CARE_BACKEND_URL to the fixed HTTPS backend origin.",
        )

    headers = {
        key: value for key, value in request.headers.items() if key.lower() in REQUEST_HEADERS
    }
    # The proxy enforces limits on raw bytes. Avoid implicit compression, while
    # still preserving Content-Encoding if an upstream ignores this request.
    headers["accept-encoding"] = "identity"
    timeout = httpx.Timeout(
        connect=CONNECT_TIMEOUT_SECONDS,
        read=READ_TIMEOUT_SECONDS,
        write=CONNECT_TIMEOUT_SECONDS,
        pool=CONNECT_TIMEOUT_SECONDS,
    )
    client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)
    started = time.monotonic()
    upstream: httpx.Response | None = None
    handed_off = False
    try:
        async with asyncio.timeout(TOTAL_TIMEOUT_SECONDS):
            upstream = await client.send(
                client.build_request(request.method, url, headers=headers, content=body),
                stream=True,
            )
            if 300 <= upstream.status_code < 400:
                return _error(
                    502,
                    "backend_redirect_rejected",
                    "The configured backend returned a redirect.",
                    "Configure the secret with the backend's final HTTPS origin.",
                )
            declared = upstream.headers.get("content-length")
            if declared:
                try:
                    if int(declared) > MAX_RESPONSE_BYTES:
                        raise OverflowError
                except ValueError as exc:
                    raise httpx.ProtocolError("invalid upstream Content-Length") from exc
            if request.url.path == "/v1/review/stream":
                handed_off = True
                return StreamingResponse(
                    _stream_body(upstream, client, started),
                    status_code=upstream.status_code,
                    headers=_safe_response_headers(upstream.headers),
                )
            response = await _buffered_response(upstream)
        return response
    except (httpx.TimeoutException, TimeoutError):
        return _error(
            504,
            "backend_timeout",
            "The fixed backend did not answer within the proxy deadline.",
            "Retry shortly; no guidance result was fabricated.",
        )
    except OverflowError:
        return _error(
            502,
            "backend_response_too_large",
            "The backend response exceeded the proxy limit.",
            "Retry or request a smaller review.",
        )
    except httpx.HTTPError as exc:
        return _error(
            502,
            "backend_unreachable",
            f"The fixed backend could not be reached ({type(exc).__name__}).",
            "Retry shortly; the local product pages remain available.",
        )
    finally:
        if not handed_off:
            if upstream is not None:
                await upstream.aclose()
            await client.aclose()