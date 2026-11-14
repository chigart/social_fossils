import asyncio
from collections.abc import AsyncIterator
from typing import cast
from urllib.parse import urlencode
from weakref import WeakValueDictionary

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.analytics_cache import (
    analytics_cache_key,
    analytics_revision,
    read_cached_response,
    store_cached_response,
)
from app.db import SessionLocal


def cacheable_request(request: Request) -> bool:
    return request.method == "GET" and (
        request.url.path.startswith("/api/analytics/")
        or request.url.path == "/api/identity-links"
    )


def lookup(key: str) -> tuple[str, str | None]:
    with SessionLocal() as db:
        revision = analytics_revision(db)
        return revision, read_cached_response(db, key, revision)


def store(key: str, revision: str, body: str) -> None:
    with SessionLocal() as db:
        store_cached_response(db, key, revision, body)


class AnalyticsCacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not cacheable_request(request):
            return await call_next(request)
        query = request.query_params
        key_query = urlencode(query.multi_items())
        key = analytics_cache_key(request.url.path, key_query)
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        async with lock:
            revision, cached = await run_in_threadpool(lookup, key)
            if cached is not None:
                return Response(content=cached, media_type="application/json")
            response = await call_next(request)
            if response.status_code != 200:
                return response
            body_iterator = getattr(response, "body_iterator", None)
            if body_iterator is not None:
                chunks = [
                    chunk
                    async for chunk in cast(
                        AsyncIterator[bytes | str], body_iterator
                    )
                ]
            else:
                chunks = [response.body]
            body = b"".join(
                chunk.encode("utf-8") if isinstance(chunk, str) else chunk
                for chunk in chunks
            )
            await run_in_threadpool(store, key, revision, body.decode("utf-8"))
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                background=response.background,
            )
