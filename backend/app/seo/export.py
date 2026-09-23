"""Export SEO report as Markdown and print-ready HTML."""
from __future__ import annotations

from html import escape
from typing import Any


def report_to_markdown(report: dict[str, Any]) -> str:
    site = report.get("website") or {}
    score = report.get("seo_score") or {}
    lines = [
        f"# {report.get('title') or 'SEO Audit Report'}",
        "",
        f"**Generated:** {report.get('generated_at')}",
        f"**Website:** {site.get('url')}",
        "",
        "## Executive Summary",
        "",
        report.get("executive_summary") or "",
        "",
        "## SEO Score",
        "",
        f"- **Overall:** {score.get('overall', '—')}/100",
        f"- Technical: {score.get('technical', '—')}",
        f"- On-Page: {score.get('on_page', '—')}",
        f"- Content: {score.get('content', '—')}",
        f"- Performance: {score.get('performance', '—')}",
        f"- Indexability: {score.get('indexability', '—')}",
        f"- Structured Data: {score.get('structured_data', '—')}",
        f"- Internal Linking: {score.get('internal_linking', '—')}",
        "",
        "## Critical Issues",
        "",
    ]
    for i in report.get("critical_issues") or []:
        lines.append(f"- **{i.get('title')}** — {i.get('recommended_fix') or ''}")
    if not report.get("critical_issues"):
        lines.append("_None_")

    lines += ["", "## High Issues", ""]
    for i in report.get("high_issues") or []:
        lines.append(f"- **{i.get('title')}** — {i.get('recommended_fix') or ''}")
    if not report.get("high_issues"):
        lines.append("_None_")

    lines += ["", "## Top Recommendations", ""]
    for r in (report.get("top_recommendations") or [])[:12]:
        lines.append(f"### {r.get('title')}")
        lines.append(f"- **What:** {r.get('what')}")
        lines.append(f"- **Why:** {r.get('why')}")
        lines.append(f"- **How:** {r.get('how')}")
        lines.append(f"- Impact: {r.get('impact')} · Effort: {r.get('effort')}")
        lines.append("")

    lines += ["", "## Next Steps", ""]
    for s in report.get("next_steps") or []:
        lines.append(f"1. {s}")

    lines += [
        "",
        "## Disclaimer",
        "",
        report.get("disclaimer")
        or "Recommended optimizations and estimated impact only. Rankings are never guaranteed.",
        "",
    ]
    return "\n".join(lines)


def report_to_html(report: dict[str, Any]) -> str:
    md_title = escape(str(report.get("title") or "SEO Audit Report"))
    summary = escape(str(report.get("executive_summary") or ""))
    site = report.get("website") or {}
    score = report.get("seo_score") or {}
    disclaimer = escape(
        str(
            report.get("disclaimer")
            or "Recommended optimizations and estimated impact only. Rankings are never guaranteed."
        )
    )

    def issues_html(items: list) -> str:
        if not items:
            return "<p><em>None</em></p>"
        parts = ["<ul>"]
        for i in items:
            parts.append(
                f"<li><strong>{escape(str(i.get('title') or ''))}</strong>"
                f" — {escape(str(i.get('recommended_fix') or ''))}</li>"
            )
        parts.append("</ul>")
        return "\n".join(parts)

    recs = report.get("top_recommendations") or []
    rec_html = []
    for r in recs[:12]:
        rec_html.append(
            f"<div class='rec'><h3>{escape(str(r.get('title') or ''))}</h3>"
            f"<p><strong>What:</strong> {escape(str(r.get('what') or ''))}</p>"
            f"<p><strong>Why:</strong> {escape(str(r.get('why') or ''))}</p>"
            f"<p><strong>How:</strong> {escape(str(r.get('how') or ''))}</p>"
            f"<p class='meta'>Impact: {escape(str(r.get('impact') or ''))} · "
            f"Effort: {escape(str(r.get('effort') or ''))}</p></div>"
        )

    next_steps = "".join(
        f"<li>{escape(str(s))}</li>" for s in (report.get("next_steps") or [])
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{md_title}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #111; line-height: 1.5; }}
  h1 {{ font-size: 1.6rem; }}
  h2 {{ margin-top: 2rem; border-bottom: 1px solid #ddd; padding-bottom: 0.3rem; }}
  .score {{ display: flex; gap: 1rem; flex-wrap: wrap; }}
  .score div {{ background: #f4f4f5; padding: 0.75rem 1rem; border-radius: 8px; min-width: 100px; }}
  .score strong {{ display: block; font-size: 1.4rem; }}
  .rec {{ border: 1px solid #e4e4e7; border-radius: 8px; padding: 1rem; margin: 0.75rem 0; }}
  .meta {{ color: #71717a; font-size: 0.9rem; }}
  .disclaimer {{ background: #fffbeb; border: 1px solid #fcd34d; padding: 1rem; border-radius: 8px; margin-top: 2rem; }}
  @media print {{ body {{ margin: 0; }} }}
</style>
</head>
<body>
  <h1>{md_title}</h1>
  <p><strong>Website:</strong> {escape(str(site.get('url') or ''))}<br/>
  <strong>Generated:</strong> {escape(str(report.get('generated_at') or ''))}</p>

  <h2>Executive Summary</h2>
  <p>{summary}</p>

  <h2>SEO Score</h2>
  <div class="score">
    <div><span>Overall</span><strong>{escape(str(score.get('overall', '—')))}</strong></div>
    <div><span>Technical</span><strong>{escape(str(score.get('technical', '—')))}</strong></div>
    <div><span>On-Page</span><strong>{escape(str(score.get('on_page', '—')))}</strong></div>
    <div><span>Content</span><strong>{escape(str(score.get('content', '—')))}</strong></div>
    <div><span>Structured Data</span><strong>{escape(str(score.get('structured_data', '—')))}</strong></div>
  </div>

  <h2>Critical Issues</h2>
  {issues_html(report.get('critical_issues') or [])}

  <h2>High Issues</h2>
  {issues_html(report.get('high_issues') or [])}

  <h2>Top Recommendations</h2>
  {''.join(rec_html) or '<p><em>None</em></p>'}

  <h2>Next Steps</h2>
  <ol>{next_steps}</ol>

  <div class="disclaimer"><strong>Disclaimer:</strong> {disclaimer}</div>
</body>
</html>
"""
