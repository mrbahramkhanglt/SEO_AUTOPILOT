import pytest
from app.security.password import validate_password_strength, hash_password, verify_password
from app.security.ssrf import validate_url_for_crawl, SSRFError


def test_password_too_short():
    with pytest.raises(ValueError):
        validate_password_strength("Ab1!")


def test_password_ok():
    validate_password_strength("testpass123")
    h = hash_password("testpass123")
    assert verify_password("testpass123", h)
    assert not verify_password("wrong", h)


def test_ssrf_blocks_localhost():
    with pytest.raises(SSRFError):
        validate_url_for_crawl("http://127.0.0.1/")
    with pytest.raises(SSRFError):
        validate_url_for_crawl("http://localhost/")


def test_ssrf_blocks_metadata_host():
    with pytest.raises(SSRFError):
        validate_url_for_crawl("http://metadata.google.internal/")


def test_ssrf_allows_public_https():
    # May resolve; if network blocked in CI, skip
    try:
        u = validate_url_for_crawl("https://example.com/")
        assert u.startswith("https://")
    except SSRFError as e:
        if "resolve" in str(e).lower():
            pytest.skip("DNS unavailable")
        raise
