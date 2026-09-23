"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface Website {
  id: string;
  domain: string;
  url: string;
  name: string | null;
  status: string;
  is_valid: boolean;
  validation_error: string | null;
  has_sitemap: boolean;
  has_robots: boolean;
  last_score: number | null;
}

interface CrawlRun {
  id: string;
  status: string;
  progress: number;
  current_step: string | null;
  message: string | null;
  pages_discovered: number;
  pages_crawled: number;
}

interface SEOScore {
  overall: number;
  technical: number;
  on_page: number;
  content: number;
  performance: number;
  indexability: number;
  structured_data: number;
  internal_linking: number;
  mobile: number;
  accessibility: number;
  authority: number;
  details?: Record<string, number>;
}

interface SEOIssue {
  id: string;
  category: string;
  code: string;
  severity: string;
  title: string;
  why_it_matters: string | null;
  recommended_fix: string | null;
  expected_impact: string | null;
  effort: string | null;
}

interface Keyword {
  id: string;
  keyword: string;
  type: string;
  search_intent: string | null;
  recommended_title: string | null;
  recommended_meta: string | null;
}

interface Recommendation {
  id: string;
  category: string;
  title: string;
  what: string;
  why: string;
  how: string;
  impact: string;
  effort: string;
  priority: number;
  auto_applicable: boolean;
  status: string;
}

interface Report {
  id: string;
  title: string;
  status: string;
  summary: string | null;
  content: any;
}

export default function WebsiteDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [website, setWebsite] = useState<Website | null>(null);
  const [crawls, setCrawls] = useState<CrawlRun[]>([]);
  const [score, setScore] = useState<SEOScore | null>(null);
  const [issues, setIssues] = useState<SEOIssue[]>([]);
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [autofix, setAutofix] = useState<any>(null);
  const [tab, setTab] = useState<"overview" | "issues" | "keywords" | "recs" | "autofix" | "report">("overview");
  const [loading, setLoading] = useState(true);
  const [crawling, setCrawling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [w, c, s, iss, kw, rc, rp, af] = await Promise.all([
        api<Website>(`/api/websites/${id}`),
        api<CrawlRun[]>(`/api/websites/${id}/crawls`),
        api<SEOScore | null>(`/api/websites/${id}/seo-score`).catch(() => null),
        api<SEOIssue[]>(`/api/websites/${id}/issues`).catch(() => []),
        api<Keyword[]>(`/api/websites/${id}/keywords`).catch(() => []),
        api<Recommendation[]>(`/api/websites/${id}/recommendations`).catch(() => []),
        api<Report | null>(`/api/websites/${id}/reports/latest`).catch(() => null),
        api<{ autofix: any }>(`/api/websites/${id}/autofix`).catch(() => ({ autofix: null })),
      ]);
      setWebsite(w);
      setCrawls(c);
      setScore(s);
      setIssues(iss || []);
      setKeywords(kw || []);
      setRecs(rc || []);
      setReport(rp);
      setAutofix(af?.autofix || null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    (async () => {
      try {
        await api("/api/auth/me");
        await load();
      } catch {
        router.replace("/auth/login");
      }
    })();
  }, [id, router, load]);

  useEffect(() => {
    const active = crawls.some((c) => c.status === "running" || c.status === "pending");
    if (!active) return;
    const t = setInterval(load, 2500);
    return () => clearInterval(t);
  }, [crawls, load]);

  async function startCrawl() {
    setCrawling(true);
    setError(null);
    try {
      await api(`/api/websites/${id}/crawl`, {
        method: "POST",
        body: JSON.stringify({ max_pages: 25, max_depth: 3 }),
      });
      await load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCrawling(false);
    }
  }

  function downloadText(filename: string, content: string) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0f] text-zinc-500">
        Loading…
      </div>
    );
  }

  if (!website) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0f] text-red-400">
        {error || "Website not found"}
      </div>
    );
  }

  const latest = crawls[0];
  const isRunning = latest && (latest.status === "running" || latest.status === "pending");
  const primaries = keywords.filter((k) => k.type === "primary").slice(0, 15);

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <header className="border-b border-white/5 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center gap-4">
          <a href="/dashboard" className="text-sm text-zinc-400 hover:text-white">
            ← Dashboard
          </a>
          <span className="text-zinc-600">/</span>
          <span className="font-medium">{website.domain}</span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold">{website.name || website.domain}</h1>
              <a href={website.url} target="_blank" rel="noopener noreferrer" className="mt-1 text-sm text-indigo-400 hover:underline">
                {website.url}
              </a>
              <div className="mt-3 flex flex-wrap gap-2">
                <Pill status={website.status} />
                {website.has_robots && <Tag>robots.txt</Tag>}
                {website.has_sitemap && <Tag>sitemap</Tag>}
              </div>
            </div>
            <div className="flex items-center gap-4">
              {score && (
                <div className="text-center">
                  <div className="text-4xl font-bold tabular-nums text-indigo-300">{score.overall}</div>
                  <div className="text-xs text-zinc-500">SEO Score</div>
                </div>
              )}
              <button
                onClick={startCrawl}
                disabled={crawling || isRunning || !website.is_valid}
                className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-3 text-sm font-semibold shadow-lg shadow-indigo-500/20 hover:brightness-110 disabled:opacity-50"
              >
                {crawling || isRunning ? "Crawling…" : "Start SEO Crawl"}
              </button>
            </div>
          </div>
        </div>

        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

        {latest && (
          <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Pill status={latest.status} />
                <span className="text-sm text-zinc-300">{latest.message || latest.current_step}</span>
              </div>
              <span className="font-mono text-sm text-zinc-500">{latest.progress}%</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all" style={{ width: `${latest.progress}%` }} />
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="mt-8 flex flex-wrap gap-2 border-b border-white/5 pb-2">
          {([
            ["overview", "Overview"],
            ["issues", `Issues (${issues.length})`],
            ["keywords", `Keywords (${keywords.length})`],
            ["recs", `Recommendations (${recs.length})`],
            ["autofix", "Auto-Fix"],
            ["report", "Report"],
          ] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`rounded-lg px-3 py-1.5 text-sm transition ${
                tab === key ? "bg-indigo-600 text-white" : "text-zinc-400 hover:bg-white/5 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "overview" && score && (
          <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {(
              [
                ["Technical", score.technical],
                ["On-Page", score.on_page],
                ["Content", score.content],
                ["Performance", score.performance],
                ["Indexability", score.indexability],
                ["Structured Data", score.structured_data],
                ["Internal Links", score.internal_linking],
                ["Mobile", score.mobile],
                ["Accessibility", score.accessibility],
                ["Authority", score.authority],
              ] as [string, number][]
            ).map(([label, val]) => (
              <div key={label} className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3">
                <div className="text-xs text-zinc-500">{label}</div>
                <div className="mt-1 text-xl font-semibold tabular-nums">{val}</div>
              </div>
            ))}
          </div>
        )}

        {tab === "issues" && (
          <div className="mt-6 space-y-3">
            {issues.length === 0 && <p className="text-sm text-zinc-500">No issues yet. Run a crawl.</p>}
            {issues.map((iss) => (
              <div key={iss.id} className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
                <div className="flex gap-2">
                  <Severity s={iss.severity} />
                  <span className="text-xs uppercase text-zinc-500">{iss.category}</span>
                </div>
                <h3 className="mt-2 font-medium">{iss.title}</h3>
                {iss.why_it_matters && <p className="mt-2 text-sm text-zinc-400"><span className="text-zinc-500">Why: </span>{iss.why_it_matters}</p>}
                {iss.recommended_fix && <p className="mt-1 text-sm text-zinc-400"><span className="text-zinc-500">Fix: </span>{iss.recommended_fix}</p>}
              </div>
            ))}
          </div>
        )}

        {tab === "keywords" && (
          <div className="mt-6 space-y-2">
            {primaries.length === 0 && <p className="text-sm text-zinc-500">No keywords yet.</p>}
            {primaries.map((k) => (
              <div key={k.id} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{k.keyword}</span>
                  <Tag>{k.type}</Tag>
                  {k.search_intent && <Tag>{k.search_intent}</Tag>}
                </div>
                {k.recommended_title && <p className="mt-2 text-sm text-zinc-400">Title → {k.recommended_title}</p>}
                {k.recommended_meta && <p className="mt-1 text-sm text-zinc-500">Meta → {k.recommended_meta}</p>}
              </div>
            ))}
          </div>
        )}

        {tab === "recs" && (
          <div className="mt-6 space-y-3">
            {recs.slice(0, 30).map((r) => (
              <div key={r.id} className="rounded-xl border border-white/10 bg-white/[0.02] p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <Severity s={r.impact === "high" ? "high" : r.impact === "low" ? "low" : "medium"} />
                  <span className="text-xs text-zinc-500">{r.category}</span>
                  {r.auto_applicable && <Tag>auto-applicable</Tag>}
                </div>
                <h3 className="mt-2 font-medium">{r.title}</h3>
                <p className="mt-2 text-sm text-zinc-400"><span className="text-zinc-500">What: </span>{r.what}</p>
                <p className="mt-1 text-sm text-zinc-400"><span className="text-zinc-500">Why: </span>{r.why}</p>
                <p className="mt-1 text-sm text-zinc-400"><span className="text-zinc-500">How: </span>{r.how}</p>
              </div>
            ))}
          </div>
        )}

        {tab === "autofix" && (
          <div className="mt-6 space-y-4">
            {!autofix && <p className="text-sm text-zinc-500">Run a crawl to generate auto-fix files.</p>}
            {autofix && (
              <>
                <div className="flex flex-wrap gap-3">
                  <button
                    className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
                    onClick={() => downloadText("robots.txt", autofix.robots_txt_full || autofix.robots_txt || "")}
                  >
                    Download robots.txt
                  </button>
                  <button
                    className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
                    onClick={() => downloadText("sitemap.xml", autofix.sitemap_xml_full || autofix.sitemap_xml_preview || "")}
                  >
                    Download sitemap.xml
                  </button>
                  <button
                    className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
                    onClick={() =>
                      downloadText(
                        "metadata-fixes.json",
                        JSON.stringify(autofix.metadata_fixes || [], null, 2)
                      )
                    }
                  >
                    Download metadata fixes
                  </button>
                  <button
                    className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
                    onClick={() =>
                      downloadText("schema-blocks.json", JSON.stringify(autofix.schema_blocks || [], null, 2))
                    }
                  >
                    Download schema JSON-LD
                  </button>
                </div>
                <p className="text-sm text-zinc-500">
                  Metadata rows: {autofix.metadata_fixes_count ?? (autofix.metadata_fixes || []).length} · Schema
                  blocks: {autofix.schema_blocks_count ?? (autofix.schema_blocks || []).length} · Internal link
                  suggestions: {autofix.internal_link_suggestions_count ?? (autofix.internal_link_suggestions || []).length}
                </p>
                <pre className="max-h-48 overflow-auto rounded-xl border border-white/10 bg-black/40 p-4 text-xs text-zinc-400">
                  {autofix.robots_txt_full || autofix.robots_txt}
                </pre>
              </>
            )}
          </div>
        )}

        {tab === "report" && (
          <div className="mt-6 space-y-4">
            {!report && <p className="text-sm text-zinc-500">No report yet. Run a crawl.</p>}
            {report && (
              <>
                <h2 className="text-xl font-semibold">{report.title}</h2>
                <p className="text-sm leading-relaxed text-zinc-300">{report.summary || report.content?.executive_summary}</p>
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-200/80">
                  {report.content?.disclaimer ||
                    "Recommended optimizations and estimated impact only. Rankings are never guaranteed."}
                </div>
                <h3 className="font-medium">Next steps</h3>
                <ul className="list-disc space-y-1 pl-5 text-sm text-zinc-400">
                  {(report.content?.next_steps || []).map((s: string, i: number) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
                <button
                  className="rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm hover:bg-white/10"
                  onClick={() => downloadText("seo-report.json", JSON.stringify(report.content || report, null, 2))}
                >
                  Download full report (JSON)
                </button>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function Pill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ready: "bg-emerald-500/20 text-emerald-300",
    completed: "bg-emerald-500/20 text-emerald-300",
    pending: "bg-amber-500/20 text-amber-300",
    running: "bg-indigo-500/20 text-indigo-300",
    crawling: "bg-indigo-500/20 text-indigo-300",
    failed: "bg-red-500/20 text-red-300",
    error: "bg-red-500/20 text-red-300",
  };
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-medium capitalize ${colors[status] || "bg-zinc-500/20 text-zinc-300"}`}>
      {status}
    </span>
  );
}

function Severity({ s }: { s: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-500/20 text-red-300",
    high: "bg-orange-500/20 text-orange-300",
    medium: "bg-amber-500/20 text-amber-300",
    low: "bg-zinc-500/20 text-zinc-300",
  };
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-semibold uppercase ${colors[s] || colors.low}`}>
      {s}
    </span>
  );
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="rounded-md bg-zinc-500/20 px-2 py-0.5 text-xs text-zinc-300">{children}</span>;
}
