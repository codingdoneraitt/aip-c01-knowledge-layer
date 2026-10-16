"""Polite HTTP client: identifies itself, honors robots.txt, rate limits per host,
retries transient failures and caches responses on disk."""

from __future__ import annotations

import gzip
import hashlib
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

DEFAULT_USER_AGENT = "aip-c01-knowledge-layer/0.1 (personal study project; public sources only)"
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class FetchError(Exception):
    """Base class for fetch failures."""


class NotFound(FetchError):
    """The server answered 404 or 410."""


class RobotsDisallowed(FetchError):
    """robots.txt forbids fetching this URL."""


@dataclass(frozen=True)
class Response:
    url: str
    status: int
    content: bytes
    from_cache: bool = False

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


class RateLimiter:
    """Guarantees a minimum interval between requests to the same host."""

    def __init__(
        self,
        min_interval: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._next_slot: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> None:
        with self._lock:
            now = self._clock()
            slot = max(now, self._next_slot.get(host, now))
            self._next_slot[host] = slot + self._min_interval
        delay = slot - now
        if delay > 0:
            self._sleep(delay)


class DiskCache:
    def __init__(self, directory: Path | None) -> None:
        self._dir = directory

    def _path(self, url: str) -> Path | None:
        if self._dir is None:
            return None
        return self._dir / hashlib.sha256(url.encode()).hexdigest()

    def get(self, url: str) -> bytes | None:
        path = self._path(url)
        if not (path and path.exists()):
            return None
        raw = path.read_bytes()
        try:
            return gzip.decompress(raw)
        except gzip.BadGzipFile:  # entry written before compression was introduced
            return raw

    def put(self, url: str, content: bytes) -> None:
        path = self._path(url)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.compress(content, compresslevel=3))


class PoliteClient:
    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        min_interval: float = 0.25,
        cache_dir: Path | None = None,
        refresh: bool = False,
        max_retries: int = 4,
        timeout: float = 30.0,
        respect_robots: bool = True,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._http = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )
        self._user_agent = user_agent
        self._limiter = RateLimiter(min_interval, sleep=sleep)
        self._cache = DiskCache(cache_dir)
        self._refresh = refresh
        self._max_retries = max_retries
        self._respect_robots = respect_robots
        self._sleep = sleep
        self._robots: dict[str, RobotFileParser | None] = {}
        self._robots_lock = threading.Lock()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get(self, url: str, *, refresh: bool = False) -> Response:
        if not (refresh or self._refresh) and (cached := self._cache.get(url)) is not None:
            return Response(url, 200, cached, from_cache=True)
        self._check_robots(url)
        response = self._request_with_retry(url)
        self._cache.put(url, response.content)
        return response

    def _request_with_retry(self, url: str) -> Response:
        host = urlparse(url).netloc
        last_error = "no attempt made"
        for attempt in range(self._max_retries + 1):
            self._limiter.wait(host)
            try:
                resp = self._http.get(url)
            except httpx.TransportError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if resp.status_code in (404, 410):
                    raise NotFound(f"{resp.status_code} for {url}")
                if resp.status_code not in _RETRY_STATUS:
                    if resp.status_code >= 400:
                        raise FetchError(f"HTTP {resp.status_code} for {url}")
                    return Response(str(resp.url), resp.status_code, resp.content)
                last_error = f"HTTP {resp.status_code}"
            if attempt < self._max_retries:
                self._sleep(2**attempt)
        raise FetchError(f"giving up on {url}: {last_error}")

    def _check_robots(self, url: str) -> None:
        if not self._respect_robots:
            return
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        with self._robots_lock:
            if origin not in self._robots:
                self._robots[origin] = self._load_robots(origin)
            parser = self._robots[origin]
        if parser is not None and not parser.can_fetch(self._user_agent, url):
            raise RobotsDisallowed(f"robots.txt disallows {url}")

    def _load_robots(self, origin: str) -> RobotFileParser | None:
        try:
            resp = self._http.get(f"{origin}/robots.txt")
        except httpx.TransportError:
            return None
        if resp.status_code != 200:
            return None  # no usable robots.txt: everything allowed
        parser = RobotFileParser()
        parser.parse(resp.text.splitlines())
        return parser
