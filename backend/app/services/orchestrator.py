"""Master orchestrator – runs full SEO pipeline for a website."""
from __future__ import annotations

import traceback
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.agent import ContentAgent
from app.core.config import get_settings
from app.crawler.engine import CrawlerEngine
from app.keywords.agent import KeywordAgent
from app.models.crawl import CrawlRun, Page
from app.models.keyword import Keyword
from app.models.recommendation import Recommendation
from app.models.seo import SEOIssue, SEOScore
from app.models.website import Website
from app.schema.agent import SchemaAgent
from app.seo.recommendations import RecommendationAgent
from app.seo.autofix import AutoFixEngine
from app.seo.report import ReportGenerator
from app.seo.internal_links import InternalLinkAgent
from app.models.report import Report
from app.seo.score import compute_seo_score
from app.seo.technical import TechnicalSEOAgent

settings = get_settings()


async def run_full_pipeline(
    db: AsyncSession,
    website_id: str,
    crawl_run_id: str,
) -> None:
    result = await db.execute(select(Website).where(Website.id == website_id))
    website = result.scalar_one_or_none()
    if not website:
        return

    result = await db.execute(select(CrawlRun).where(CrawlRun.id == crawl_run_id))
    crawl = result.scalar_one_or_none()
    if not crawl:
        return

    async def on_progress(step: str, progress: int, message: str, extra: dict):
        crawl.progress = progress
        crawl.current_step = step
        crawl.message = message
        if extra.get("pages_crawled") is not None:
            crawl.pages_crawled = extra["pages_crawled"]
        if extra.get("pages_discovered") is not None:
            crawl.pages_discovered = extra["pages_discovered"]
        await db.commit()

    try:
        crawl.status = "running"
        crawl.started_at = datetime.now(timezone.utc)
        crawl.progress = 1
        crawl.current_step = "starting"
        crawl.message = "Pipeline started"
        website.status = "crawling"
        await db.commit()

        max_pages = (crawl.config or {}).get("max_pages") or website.max_pages or settings.max_pages_per_crawl
        max_depth = (crawl.config or {}).get("max_depth") or website.crawl_depth or settings.max_crawl_depth

        engine = CrawlerEngine(
            start_url=website.url,
            max_pages=int(max_pages),
            max_depth=int(max_depth),
            delay=settings.crawl_delay_seconds,
            timeout=settings.crawl_timeout_seconds,
            on_progress=on_progress,
        )
        crawl_result = await engine.crawl()
        pages_data = crawl_result.get("pages") or []

        # Persist pages
        crawl.current_step = "saving_pages"
        crawl.message = f"Saving {len(pages_data)} pages"
        crawl.progress = 88
        await db.commit()

        page_id_by_url: dict[str, str] = {}
        for pdata in pages_data:
            page = Page(
                website_id=website.id,
                crawl_run_id=crawl.id,
                url=pdata.get("url") or "",
                canonical_url=pdata.get("canonical_url"),
                status_code=pdata.get("status_code"),
                title=pdata.get("title"),
                meta_description=pdata.get("meta_description"),
                h1=pdata.get("h1"),
                headings=pdata.get("headings"),
                word_count=pdata.get("word_count"),
                is_indexable=pdata.get("is_indexable", True),
                is_canonical=pdata.get("is_canonical", True),
                has_structured_data=pdata.get("has_structured_data", False),
                structured_data=pdata.get("structured_data"),
                open_graph=pdata.get("open_graph"),
                twitter_card=pdata.get("twitter_card"),
                page_size_bytes=pdata.get("page_size_bytes"),
                is_thin_content=pdata.get("is_thin_content", False),
                signals={
                    "images_total": pdata.get("images_total"),
                    "images_missing_alt": pdata.get("images_missing_alt"),
                    "internal_links_count": len(pdata.get("internal_links") or []),
                    "robots_meta": pdata.get("robots_meta"),
                },
                depth=pdata.get("depth") or 0,
                crawled_at=datetime.now(timezone.utc),
            )
            db.add(page)
            await db.flush()
            page_id_by_url[page.url] = page.id

        # Technical SEO
        crawl.current_step = "technical_seo"
        crawl.message = "Technical SEO analysis"
        crawl.progress = 90
        await db.commit()

        tech_agent = TechnicalSEOAgent()
        issues = tech_agent.analyze(crawl_result, website.url)

        for iss in issues:
            db.add(
                SEOIssue(
                    website_id=website.id,
                    crawl_run_id=crawl.id,
                    category=iss["category"],
                    code=iss["code"],
                    severity=iss["severity"],
                    title=iss["title"],
                    description=iss["description"],
                    why_it_matters=iss.get("why_it_matters"),
                    recommended_fix=iss.get("recommended_fix"),
                    expected_impact=iss.get("expected_impact"),
                    effort=iss.get("effort"),
                    priority_score=iss.get("priority_score"),
                    data=iss.get("data"),
                    status="open",
                )
            )

        # Keywords
        crawl.current_step = "keywords"
        crawl.message = "Keyword research"
        crawl.progress = 92
        await db.commit()

        kw_agent = KeywordAgent()
        keyword_rows = kw_agent.analyze_site(pages_data)
        for kw in keyword_rows:
            page_id = page_id_by_url.get(kw.get("page_url") or "")
            db.add(
                Keyword(
                    website_id=website.id,
                    page_id=page_id,
                    keyword=kw["keyword"],
                    type=kw.get("type") or "primary",
                    search_intent=kw.get("search_intent"),
                    recommended_title=kw.get("recommended_title"),
                    recommended_h1=kw.get("recommended_h1"),
                    recommended_meta=kw.get("recommended_meta"),
                )
            )
            # stamp primary on page
            if kw.get("type") == "primary" and page_id:
                # update via later if needed
                pass

        # Schema
        crawl.current_step = "schema"
        crawl.message = "Schema recommendations"
        crawl.progress = 94
        await db.commit()

        schema_agent = SchemaAgent()
        schema_recs = schema_agent.analyze_site(pages_data, website.url, website.name)

        # Content
        crawl.current_step = "content"
        crawl.message = "Content opportunities"
        crawl.progress = 95
        await db.commit()

        content_agent = ContentAgent()
        content_opps = content_agent.analyze_site(pages_data, keyword_rows)

        # Recommendations
        crawl.current_step = "recommendations"
        crawl.message = "Prioritizing recommendations"
        crawl.progress = 96
        await db.commit()

        rec_agent = RecommendationAgent()
        recommendations = rec_agent.build(issues, schema_recs, content_opps, keyword_rows)
        for r in recommendations:
            db.add(
                Recommendation(
                    website_id=website.id,
                    category=r["category"],
                    title=r["title"],
                    what=r["what"],
                    why=r["why"],
                    how=r["how"],
                    impact=r["impact"],
                    effort=r["effort"],
                    priority=r["priority"],
                    auto_applicable=r["auto_applicable"],
                    requires_approval=r["requires_approval"],
                    status="pending",
                    suggested_change=r.get("suggested_change"),
                )
            )

        # Internal links
        crawl.current_step = "internal_links"
        crawl.message = "Building internal link graph"
        crawl.progress = 96
        await db.commit()
        link_agent = InternalLinkAgent()
        link_graph = link_agent.build_graph(pages_data)

        # Auto-fix artifacts
        crawl.current_step = "autofix"
        crawl.message = "Generating auto-fix artifacts"
        crawl.progress = 97
        await db.commit()
        autofix_engine = AutoFixEngine()
        autofix = autofix_engine.generate(
            website.url,
            pages_data,
            schema_recs,
            keyword_rows,
            website.domain,
        )

        # Score
        crawl.current_step = "scoring"
        crawl.message = "Computing SEO score"
        crawl.progress = 98
        await db.commit()

        score_data = compute_seo_score(crawl_result, issues)
        score = SEOScore(
            website_id=website.id,
            crawl_run_id=crawl.id,
            overall=score_data["overall"],
            technical=score_data["technical"],
            on_page=score_data["on_page"],
            content=score_data["content"],
            performance=score_data["performance"],
            indexability=score_data["indexability"],
            structured_data=score_data["structured_data"],
            internal_linking=score_data["internal_linking"],
            mobile=score_data["mobile"],
            accessibility=score_data["accessibility"],
            authority=score_data["authority"],
            details={
                **(score_data.get("details") or {}),
                "keywords_found": len(keyword_rows),
                "schema_recommendations": len(schema_recs),
                "content_opportunities": len(content_opps),
                "recommendations": len(recommendations),
                "orphan_pages": len(link_graph.get("orphans") or []),
                "autofix_metadata_rows": len(autofix.get("metadata_fixes") or []),
            },
        )
        db.add(score)

        # Report
        crawl.current_step = "report"
        crawl.message = "Generating SEO report"
        crawl.progress = 99
        await db.commit()
        report_gen = ReportGenerator()
        report_payload = report_gen.generate(
            website={
                "url": website.url,
                "domain": website.domain,
                "name": website.name,
                "has_sitemap": website.has_sitemap,
                "has_robots": website.has_robots,
                "technology_stack": website.technology_stack,
            },
            score=score_data,
            issues=issues,
            keywords=keyword_rows,
            recommendations=recommendations,
            crawl={
                "pages_crawled": crawl_result.get("pages_crawled"),
                "pages_discovered": crawl_result.get("pages_discovered"),
            },
            autofix_summary=autofix.get("summary"),
        )
        # Attach graphs/artifacts into report content
        report_payload["internal_link_graph"] = {
            "orphans": link_graph.get("orphans"),
            "weak_pages": link_graph.get("weak_pages"),
            "important_pages": link_graph.get("important_pages"),
            "opportunities_count": len(link_graph.get("opportunities") or []),
            "edges_count": link_graph.get("edges_count"),
        }
        report_payload["autofix"] = {
            "robots_txt": autofix.get("robots_txt"),
            "sitemap_xml_preview": (autofix.get("sitemap_xml") or "")[:2000],
            "metadata_fixes_count": len(autofix.get("metadata_fixes") or []),
            "schema_blocks_count": len(autofix.get("schema_blocks") or []),
            "internal_link_suggestions_count": len(autofix.get("internal_link_suggestions") or []),
            "metadata_fixes": autofix.get("metadata_fixes"),
            "schema_blocks": autofix.get("schema_blocks")[:20],
            "internal_link_suggestions": autofix.get("internal_link_suggestions")[:20],
            "robots_txt_full": autofix.get("robots_txt"),
            "sitemap_xml_full": autofix.get("sitemap_xml"),
        }
        db.add(
            Report(
                website_id=website.id,
                crawl_run_id=crawl.id,
                title=report_payload["title"],
                report_type="full_audit",
                status="ready",
                content=report_payload,
                summary=report_payload.get("executive_summary"),
            )
        )

        website.last_crawled_at = datetime.now(timezone.utc)
        website.last_score = score_data["overall"]
        website.status = "ready"
        if crawl_result.get("robots_txt"):
            website.has_robots = True
        if crawl_result.get("sitemap_urls"):
            website.has_sitemap = True
            website.sitemap_url = crawl_result["sitemap_urls"][0]

        crawl.status = "completed"
        crawl.progress = 100
        crawl.current_step = "completed"
        crawl.message = (
            f"Done – score {score_data['overall']}/100 · "
            f"{len(issues)} issues · {len(recommendations)} recommendations"
        )
        crawl.pages_crawled = crawl_result.get("pages_crawled") or 0
        crawl.pages_discovered = crawl_result.get("pages_discovered") or 0
        crawl.finished_at = datetime.now(timezone.utc)
        await db.commit()

    except Exception as e:
        crawl.status = "failed"
        crawl.error = str(e)[:2000]
        crawl.message = "Pipeline failed"
        crawl.finished_at = datetime.now(timezone.utc)
        website.status = "error"
        await db.commit()
        traceback.print_exc()
