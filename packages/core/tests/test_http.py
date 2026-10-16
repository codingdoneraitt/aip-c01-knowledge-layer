import httpx
import pytest
from aipc01_core.http import (
    FetchError,
    NotFound,
    PoliteClient,
    RateLimiter,
    RobotsDisallowed,
)


def client_for(handler, tmp_path=None, **kwargs) -> tuple[PoliteClient, list[float]]:
    sleeps: list[float] = []
    client = PoliteClient(
        transport=httpx.MockTransport(handler),
        min_interval=0,
        sleep=sleeps.append,
        cache_dir=tmp_path,
        **kwargs,
    )
    return client, sleeps


def test_get_returns_content():
    client, _ = client_for(lambda r: httpx.Response(200, text="hello"))
    assert client.get("https://example.com/a").text == "hello"


def test_retries_transient_errors_with_backoff():
    calls = {"n": 0}

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] < 3 else httpx.Response(200, text="ok")

    client, sleeps = client_for(handler)
    assert client.get("https://example.com/a").text == "ok"
    assert calls["n"] == 3
    assert sleeps == [1, 2]


def test_gives_up_after_max_retries():
    client, _ = client_for(lambda r: httpx.Response(500), max_retries=2)
    with pytest.raises(FetchError, match="giving up"):
        client.get("https://example.com/a")


def test_not_found_is_not_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404)

    client, _ = client_for(handler, respect_robots=False)
    with pytest.raises(NotFound):
        client.get("https://example.com/missing")
    assert calls["n"] == 1


def test_robots_disallow_blocks_fetch():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
        return httpx.Response(200, text="secret")

    client, _ = client_for(handler)
    with pytest.raises(RobotsDisallowed):
        client.get("https://example.com/private/page")
    assert client.get("https://example.com/public/page").text == "secret"


def test_missing_robots_allows_everything():
    client, _ = client_for(
        lambda r: httpx.Response(404 if "robots" in r.url.path else 200, text="x")
    )
    assert client.get("https://example.com/anything").text == "x"


def test_cache_avoids_second_request(tmp_path):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, text="body")

    client, _ = client_for(handler, tmp_path, respect_robots=False)
    first = client.get("https://example.com/a")
    second = client.get("https://example.com/a")
    assert (first.from_cache, second.from_cache) == (False, True)
    assert calls["n"] == 1


def test_refresh_bypasses_cache_but_rewrites_it(tmp_path):
    bodies = iter(["old", "new"])
    client, _ = client_for(
        lambda r: httpx.Response(200, text=next(bodies)),
        tmp_path,
        respect_robots=False,
        refresh=True,
    )
    assert client.get("https://example.com/a").text == "old"
    assert client.get("https://example.com/a").text == "new"


def test_rate_limiter_spaces_requests_per_host():
    now = {"t": 100.0}
    sleeps: list[float] = []
    limiter = RateLimiter(0.5, clock=lambda: now["t"], sleep=sleeps.append)
    limiter.wait("a.com")
    limiter.wait("a.com")
    limiter.wait("b.com")
    assert sleeps == [0.5]
