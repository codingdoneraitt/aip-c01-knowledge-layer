import gzip

from aipc01_core.http import DiskCache


def test_roundtrip_is_compressed_on_disk(tmp_path):
    cache = DiskCache(tmp_path)
    cache.put("u", b"hello" * 100)
    assert cache.get("u") == b"hello" * 100
    assert len(next(tmp_path.iterdir()).read_bytes()) < 500


def test_reads_legacy_uncompressed_entries(tmp_path):
    cache = DiskCache(tmp_path)
    cache.put("u", b"x")
    next(tmp_path.iterdir()).write_bytes(b"legacy")
    assert cache.get("u") == b"legacy"
    assert gzip.decompress(gzip.compress(b"ok")) == b"ok"


def test_disabled_cache_returns_none():
    assert DiskCache(None).get("u") is None
