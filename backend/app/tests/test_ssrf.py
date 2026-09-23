"""SSRF protection unit tests."""
import pytest

from app.security.ssrf import SSRFError, is_ip_blocked, validate_url_for_crawl


def test_blocks_localhost():
    with pytest.raises(SSRFError):
        validate_url_for_crawl("http://localhost/")
    with pytest.raises(SSRFError):
        validate_url_for_crawl("http://127.0.0.1/")


def test_blocks_private_ips():
    assert is_ip_blocked("10.0.0.1") is True
    assert is_ip_blocked("192.168.1.1") is True
    assert is_ip_blocked("172.16.0.1") is True
    assert is_ip_blocked("169.254.169.254") is True


def test_blocks_metadata():
    with pytest.raises(SSRFError):
        validate_url_for_crawl("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(SSRFError):
        validate_url_for_crawl("http://metadata.google.internal/")


def test_allows_public_https():
    try:
        url = validate_url_for_crawl("https://example.com")
        assert url.startswith("https://example.com")
    except SSRFError as e:
        if "resolve" in str(e).lower():
            pytest.skip("DNS unavailable")
        raise


def test_normalizes_scheme():
    try:
        url = validate_url_for_crawl("example.com")
        assert url.startswith("https://")
    except SSRFError as e:
        if "resolve" in str(e).lower():
            pytest.skip("DNS unavailable")
        raise
