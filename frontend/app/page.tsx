"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function HomePage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!url.trim()) {
      setError("Please enter a website URL");
      return;
    }
    setLoading(true);

    // For PHASE 1: if not authenticated, redirect to register/login flow.
    // Later we will support anonymous trial + full auth.
    try {
      // Auth via httpOnly cookie (credentials include)
      const meRes = await fetch(`${API_URL}/api/auth/me`, { credentials: "include" });
      if (!meRes.ok) {
        sessionStorage.setItem("pending_url", url.trim());
        router.push("/auth/register");
        return;
      }

      const res = await fetch(`${API_URL}/api/websites`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ url: url.trim() }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to onboard website");
      }

      const website = await res.json();
      await fetch(`${API_URL}/api/websites/${website.id}/crawl`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ max_pages: 30, max_depth: 3 }),
      }).catch(() => null);
      router.push(`/dashboard/websites/${website.id}`);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white selection:bg-indigo-500/30">
      {/* Ambient background */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[600px] w-[900px] -translate-x-1/2 rounded-full bg-indigo-600/20 blur-[120px]" />
        <div className="absolute bottom-0 right-0 h-[400px] w-[600px] rounded-full bg-violet-600/10 blur-[100px]" />
      </div>

      {/* Nav */}
      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 font-bold text-sm">
            SA
          </div>
          <span className="text-lg font-semibold tracking-tight">
            SEO Autopilot <span className="text-indigo-400">AI</span>
          </span>
        </div>
        <nav className="flex items-center gap-4 text-sm text-zinc-400">
          <a href="/docs" className="hover:text-white transition">
            Docs
          </a>
          <a
            href="/auth/login"
            className="rounded-lg border border-white/10 px-4 py-2 hover:bg-white/5 transition"
          >
            Sign in
          </a>
          <a
            href="/auth/register"
            className="rounded-lg bg-indigo-600 px-4 py-2 font-medium hover:bg-indigo-500 transition"
          >
            Get started
          </a>
        </nav>
      </header>

      {/* Hero */}
      <main className="relative z-10 mx-auto flex max-w-4xl flex-col items-center px-6 pt-20 pb-32 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-1.5 text-xs font-medium text-indigo-300">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Autonomous AI SEO Operating System
        </div>

        <h1 className="max-w-3xl text-5xl font-bold leading-tight tracking-tight sm:text-6xl">
          Enter a URL.
          <br />
          <span className="bg-gradient-to-r from-indigo-400 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
            We handle the rest.
          </span>
        </h1>

        <p className="mt-6 max-w-xl text-lg text-zinc-400">
          Crawl, audit, analyze, optimize and continuously improve your website&apos;s SEO —
          automatically. No more manual checklists.
        </p>

        {/* URL form */}
        <form
          onSubmit={handleStart}
          className="mt-12 w-full max-w-2xl"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com"
                className="w-full rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-base text-white placeholder:text-zinc-500 outline-none ring-indigo-500/50 transition focus:border-indigo-500/50 focus:ring-2"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 px-8 py-4 font-semibold shadow-lg shadow-indigo-500/25 transition hover:brightness-110 disabled:opacity-60"
            >
              {loading ? "Starting…" : "Start SEO Autopilot"}
            </button>
          </div>
          {error && (
            <p className="mt-3 text-sm text-red-400">{error}</p>
          )}
        </form>

        {/* Optional integrations teaser */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-3 text-xs text-zinc-500">
          <span>Optional integrations:</span>
          {["GitHub", "Netlify", "Vercel", "WordPress", "Search Console", "Analytics"].map(
            (name) => (
              <span
                key={name}
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1"
              >
                {name}
              </span>
            )
          )}
        </div>

        {/* Feature grid */}
        <div className="mt-24 grid w-full gap-6 text-left sm:grid-cols-3">
          {[
            {
              title: "Full Autonomous Crawl",
              desc: "Discovers pages, sitemaps, robots, tech stack and all SEO signals automatically.",
            },
            {
              title: "Specialized AI Agents",
              desc: "Technical, On-Page, Content, Keyword, Schema, Performance and Recommendation agents.",
            },
            {
              title: "Safe Auto-Fix Engine",
              desc: "Applies only approved, non-destructive SEO improvements with full audit trail.",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur"
            >
              <h3 className="font-semibold text-white">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-zinc-400">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="relative z-10 border-t border-white/5 py-8 text-center text-xs text-zinc-600">
        SEO Autopilot AI · Never claims guaranteed rankings · Built for humans first
      </footer>
    </div>
  );
}
