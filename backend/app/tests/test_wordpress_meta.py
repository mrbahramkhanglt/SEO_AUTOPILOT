from app.integrations.wordpress import WordPressIntegration, YOAST_KEYS, RANK_MATH_KEYS


def test_build_meta_payload_yoast():
    wp = WordPressIntegration("https://example.com", "u", "p", seo_plugin="yoast")
    meta = wp.build_meta_payload(title="T", description="D")
    assert meta[YOAST_KEYS["title"]] == "T"
    assert meta[YOAST_KEYS["description"]] == "D"


def test_build_meta_payload_rankmath():
    wp = WordPressIntegration("https://example.com", "u", "p", seo_plugin="rankmath")
    meta = wp.build_meta_payload(title="T")
    assert meta[RANK_MATH_KEYS["title"]] == "T"


def test_https_required_for_non_local():
    wp = WordPressIntegration("http://example.com", "u", "p")
    try:
        wp._validate_url()
        assert False, "should raise"
    except ValueError as e:
        assert "HTTPS" in str(e)
