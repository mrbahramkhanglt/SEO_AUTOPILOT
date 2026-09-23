"""SEO score and keyword agent unit tests."""
from app.seo.score import compute_seo_score
from app.keywords.agent import KeywordAgent, detect_intent
from app.seo.autofix import AutoFixEngine
from app.seo.internal_links import InternalLinkAgent


def test_score_empty():
    s = compute_seo_score({"pages": []}, [])
    assert 0 <= s["overall"] <= 100
    assert "technical" in s


def test_score_healthy_pages():
    pages = [
        {
            "status_code": 200,
            "title": "Age Calculator – Free Online Tool",
            "meta_description": "Calculate your exact age in years months and days with our free tool.",
            "h1": "Age Calculator",
            "is_indexable": True,
            "is_thin_content": False,
            "word_count": 400,
            "has_structured_data": True,
            "images_missing_alt": 0,
            "internal_links": [{"url": "/a"}, {"url": "/b"}],
        }
        for _ in range(5)
    ]
    crawl = {"pages": pages, "robots_txt": "User-agent: *", "sitemap_urls": ["https://x.com/sitemap.xml"]}
    s = compute_seo_score(crawl, [])
    assert s["overall"] >= 70
    assert s["on_page"] >= 80


def test_keyword_intent():
    assert detect_intent("buy shoes online") == "transactional"
    assert detect_intent("best crm software") == "commercial"
    assert detect_intent("how to calculate age") == "informational"


def test_keyword_agent_tool_page():
    agent = KeywordAgent()
    page = {
        "url": "https://utilpro.netlify.app/tools/age-calculator",
        "title": "Age Calculator – Free Online Tool",
        "h1": "Age Calculator",
        "meta_description": "Calculate exact age from date of birth.",
        "headings": {"h2": ["How to use", "Examples"], "h3": []},
        "status_code": 200,
    }
    kws = agent.analyze_page(page)
    assert any(k["type"] == "primary" for k in kws)
    assert "age" in kws[0]["keyword"].lower() or "calculator" in kws[0]["keyword"].lower()


def test_autofix_robots_sitemap():
    engine = AutoFixEngine()
    pages = [
        {"url": "https://example.com/", "status_code": 200, "is_indexable": True, "title": "Home"},
        {"url": "https://example.com/tools/bmi", "status_code": 200, "is_indexable": True, "title": "BMI"},
    ]
    out = engine.generate("https://example.com", pages)
    assert "User-agent" in out["robots_txt"]
    assert "Sitemap:" in out["robots_txt"]
    assert "<urlset" in out["sitemap_xml"]
    assert "https://example.com/" in out["sitemap_xml"]


def test_internal_link_orphans():
    agent = InternalLinkAgent()
    pages = [
        {
            "url": "https://ex.com/",
            "status_code": 200,
            "title": "Home",
            "word_count": 500,
            "internal_links": [{"url": "https://ex.com/a", "text": "A"}],
        },
        {
            "url": "https://ex.com/a",
            "status_code": 200,
            "title": "A",
            "word_count": 100,
            "internal_links": [],
        },
        {
            "url": "https://ex.com/orphan",
            "status_code": 200,
            "title": "Orphan",
            "word_count": 50,
            "internal_links": [],
        },
    ]
    graph = agent.build_graph(pages)
    assert "https://ex.com/orphan" in graph["orphans"]
