"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface OrgSettings {
  organization_id: string;
  default_max_pages: number;
  default_max_depth: number;
  default_crawl_delay: number;
  ai_provider: string;
  ai_api_key_set: boolean;
  github_enabled: boolean;
  netlify_enabled: boolean;
  vercel_enabled: boolean;
  gsc_enabled: boolean;
  ga4_enabled: boolean;
  wordpress_enabled: boolean;
  auto_optimize_default: boolean;
  require_approval_default: boolean;
  max_websites_override: number | null;
  company_name: string | null;
  report_footer: string | null;
  alert_email: string | null;
  notify_on_crawl_complete: boolean;
  notify_on_score_drop: boolean;
  score_drop_threshold: number;
}

interface SystemInfo {
  app_name: string;
  version: string;
  environment: string;
  database: string;
  features: Record<string, boolean>;
  crawl_defaults: Record<string, unknown>;
  oauth_configured: Record<string, boolean>;
}

interface Stats {
  websites: number;
  crawls: number;
  users_in_org: number;
  plan: string;
  max_websites: number;
}

interface Member {
  user_id: string;
  email: string;
  full_name: string | null;
  role: string;
}

export default function AdminPage() {
  const router = useRouter();
  const [settings, setSettings] = useState<OrgSettings | null>(null);
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [tab, setTab] = useState<"overview" | "crawl" | "ai" | "integrations" | "safety" | "notifications" | "members">("overview");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [aiKey, setAiKey] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [netlifyToken, setNetlifyToken] = useState("");
  const [vercelToken, setVercelToken] = useState("");

  useEffect(() => {
    // auth enforced by cookie + /api/admin/* 401
    (async () => {
      try {
        const [s, sys, st, mem] = await Promise.all([
          api<OrgSettings>("/api/admin/settings"),
          api<SystemInfo>("/api/admin/system"),
          api<Stats>("/api/admin/stats"),
          api<Member[]>("/api/admin/members"),
        ]);
        setSettings(s);
        setSystem(sys);
        setStats(st);
        setMembers(mem);
      } catch (e: any) {
        setErr(e.message || "Failed to load admin");
      }
    })();
  }, [router]);

  async function save(patch: Partial<OrgSettings> & Record<string, unknown>) {
    setSaving(true);
    setMsg(null);
    setErr(null);
    try {
      const body: any = { ...patch };
      if (aiKey) body.ai_api_key = aiKey;
      if (githubToken) body.github_token = githubToken;
      if (netlifyToken) body.netlify_token = netlifyToken;
      if (vercelToken) body.vercel_token = vercelToken;
      const updated = await api<OrgSettings>("/api/admin/settings", {
        method: "PUT",
        body: JSON.stringify(body),
      });
      setSettings(updated);
      setAiKey("");
      setGithubToken("");
      setNetlifyToken("");
      setVercelToken("");
      setMsg("Settings saved");
    } catch (e: any) {
      setErr(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (!settings) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0f] text-zinc-500">
        {err || "Loading admin…"}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <header className="border-b border-white/5 px-6 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <div className="flex items-center gap-4">
            <a href="/dashboard" className="text-sm text-zinc-400 hover:text-white">← Dashboard</a>
            <span className="font-semibold">Admin Settings</span>
          </div>
          <span className="text-xs text-zinc-500">{system?.app_name} v{system?.version}</span>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {msg && <p className="mb-4 text-sm text-emerald-400">{msg}</p>}
        {err && <p className="mb-4 text-sm text-red-400">{err}</p>}

        <div className="flex flex-wrap gap-2 border-b border-white/5 pb-3">
          {(["overview", "crawl", "ai", "integrations", "safety", "notifications", "members"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-lg px-3 py-1.5 text-sm capitalize ${
                tab === t ? "bg-indigo-600" : "text-zinc-400 hover:bg-white/5"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {tab === "overview" && (
          <div className="mt-6 space-y-6">
            <div className="grid gap-3 sm:grid-cols-4">
              {[
                ["Websites", stats?.websites],
                ["Crawls", stats?.crawls],
                ["Members", stats?.users_in_org],
                ["Plan", stats?.plan],
              ].map(([l, v]) => (
                <div key={String(l)} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
                  <div className="text-xs text-zinc-500">{l}</div>
                  <div className="mt-1 text-xl font-semibold capitalize">{v ?? "—"}</div>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
              <h2 className="font-medium">Platform</h2>
              <p className="mt-2 text-sm text-zinc-400">
                Env: {system?.environment} · DB: {system?.database} · Max websites: {stats?.max_websites}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {system &&
                  Object.entries(system.features).map(([k, on]) => (
                    <span
                      key={k}
                      className={`rounded-md px-2 py-0.5 text-xs ${
                        on ? "bg-emerald-500/20 text-emerald-300" : "bg-zinc-500/20 text-zinc-400"
                      }`}
                    >
                      {k}
                    </span>
                  ))}
              </div>
              <div className="mt-4">
                <label className="text-xs text-zinc-500">Company name (reports)</label>
                <input
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
                  value={settings.company_name || ""}
                  onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}
                />
              </div>
              <div className="mt-3">
                <label className="text-xs text-zinc-500">Report footer</label>
                <textarea
                  className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
                  rows={2}
                  value={settings.report_footer || ""}
                  onChange={(e) => setSettings({ ...settings, report_footer: e.target.value })}
                />
              </div>
              <button
                disabled={saving}
                onClick={() =>
                  save({
                    company_name: settings.company_name,
                    report_footer: settings.report_footer,
                  })
                }
                className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
              >
                Save branding
              </button>
            </div>
          </div>
        )}

        {tab === "crawl" && (
          <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-5 space-y-4">
            <h2 className="font-medium">Crawl defaults</h2>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Max pages" type="number" value={settings.default_max_pages}
                onChange={(v) => setSettings({ ...settings, default_max_pages: Number(v) })} />
              <Field label="Max depth" type="number" value={settings.default_max_depth}
                onChange={(v) => setSettings({ ...settings, default_max_depth: Number(v) })} />
              <Field label="Delay (seconds)" type="number" value={settings.default_crawl_delay}
                onChange={(v) => setSettings({ ...settings, default_crawl_delay: Number(v) })} />
            </div>
            <button disabled={saving} onClick={() => save({
              default_max_pages: settings.default_max_pages,
              default_max_depth: settings.default_max_depth,
              default_crawl_delay: settings.default_crawl_delay,
            })} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500">
              Save crawl settings
            </button>
          </div>
        )}

        {tab === "ai" && (
          <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-5 space-y-4">
            <h2 className="font-medium">AI provider</h2>
            <p className="text-sm text-zinc-400">
              Default pipeline uses rules-based agents (no API cost). Optional LLM providers for richer content.
            </p>
            <select
              className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
              value={settings.ai_provider}
              onChange={(e) => setSettings({ ...settings, ai_provider: e.target.value })}
            >
              <option value="rules">Rules only (default)</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="gemini">Google Gemini</option>
              <option value="local">Local model</option>
            </select>
            <div>
              <label className="text-xs text-zinc-500">
                API key {settings.ai_api_key_set ? "(set — enter new to replace)" : "(not set)"}
              </label>
              <input
                type="password"
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
                placeholder="sk-…"
                value={aiKey}
                onChange={(e) => setAiKey(e.target.value)}
              />
            </div>
            <button disabled={saving} onClick={() => save({ ai_provider: settings.ai_provider })}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500">
              Save AI settings
            </button>
          </div>
        )}

        {tab === "integrations" && (
          <div className="mt-6 space-y-4">
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5 space-y-3">
              <h2 className="font-medium">Enable integrations</h2>
              {(
                [
                  ["github_enabled", "GitHub"],
                  ["netlify_enabled", "Netlify"],
                  ["vercel_enabled", "Vercel"],
                  ["gsc_enabled", "Google Search Console"],
                  ["ga4_enabled", "Google Analytics 4"],
                  ["wordpress_enabled", "WordPress"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="flex items-center justify-between text-sm">
                  <span>{label}</span>
                  <input
                    type="checkbox"
                    checked={Boolean(settings[key])}
                    onChange={(e) => setSettings({ ...settings, [key]: e.target.checked })}
                  />
                </label>
              ))}
              <button
                disabled={saving}
                onClick={() =>
                  save({
                    github_enabled: settings.github_enabled,
                    netlify_enabled: settings.netlify_enabled,
                    vercel_enabled: settings.vercel_enabled,
                    gsc_enabled: settings.gsc_enabled,
                    ga4_enabled: settings.ga4_enabled,
                    wordpress_enabled: settings.wordpress_enabled,
                  })
                }
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500"
              >
                Save toggles
              </button>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5 space-y-3">
              <h2 className="font-medium">Tokens (stored encrypted in org secrets — never shown again)</h2>
              <input type="password" placeholder="GitHub token" className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
                value={githubToken} onChange={(e) => setGithubToken(e.target.value)} />
              <input type="password" placeholder="Netlify token" className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
                value={netlifyToken} onChange={(e) => setNetlifyToken(e.target.value)} />
              <input type="password" placeholder="Vercel token" className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
                value={vercelToken} onChange={(e) => setVercelToken(e.target.value)} />
              <button disabled={saving} onClick={() => save({})}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500">
                Save tokens
              </button>
            </div>
            {system && (
              <p className="text-xs text-zinc-500">
                OAuth app configured — GitHub: {system.oauth_configured.github ? "yes" : "no"}, Google:{" "}
                {system.oauth_configured.google ? "yes" : "no"}
              </p>
            )}
          </div>
        )}

        {tab === "safety" && (
          <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-5 space-y-4">
            <h2 className="font-medium">Safety & approvals</h2>
            <label className="flex items-center justify-between text-sm">
              <span>Auto-optimize by default (safe fixes only)</span>
              <input type="checkbox" checked={settings.auto_optimize_default}
                onChange={(e) => setSettings({ ...settings, auto_optimize_default: e.target.checked })} />
            </label>
            <label className="flex items-center justify-between text-sm">
              <span>Require approval for risky changes</span>
              <input type="checkbox" checked={settings.require_approval_default}
                onChange={(e) => setSettings({ ...settings, require_approval_default: e.target.checked })} />
            </label>
            <p className="text-xs text-zinc-500">
              Never auto-applies: URL changes, deletes, redirects, major rewrites, production config.
              Rankings are never guaranteed in any report copy.
            </p>
            <button disabled={saving} onClick={() => save({
              auto_optimize_default: settings.auto_optimize_default,
              require_approval_default: settings.require_approval_default,
            })} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500">
              Save safety settings
            </button>
          </div>
        )}

        {tab === "notifications" && (
          <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-5 space-y-4">
            <h2 className="font-medium">Notifications</h2>
            <Field label="Alert email" type="email" value={settings.alert_email || ""}
              onChange={(v) => setSettings({ ...settings, alert_email: v })} />
            <label className="flex items-center justify-between text-sm">
              <span>Notify on crawl complete</span>
              <input type="checkbox" checked={settings.notify_on_crawl_complete}
                onChange={(e) => setSettings({ ...settings, notify_on_crawl_complete: e.target.checked })} />
            </label>
            <label className="flex items-center justify-between text-sm">
              <span>Notify on score drop</span>
              <input type="checkbox" checked={settings.notify_on_score_drop}
                onChange={(e) => setSettings({ ...settings, notify_on_score_drop: e.target.checked })} />
            </label>
            <Field label="Score drop threshold" type="number" value={settings.score_drop_threshold}
              onChange={(v) => setSettings({ ...settings, score_drop_threshold: Number(v) })} />
            <button disabled={saving} onClick={() => save({
              alert_email: settings.alert_email,
              notify_on_crawl_complete: settings.notify_on_crawl_complete,
              notify_on_score_drop: settings.notify_on_score_drop,
              score_drop_threshold: settings.score_drop_threshold,
            })} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500">
              Save notifications
            </button>
          </div>
        )}

        {tab === "members" && (
          <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <h2 className="font-medium">Team</h2>
            <div className="mt-4 space-y-2">
              {members.map((m) => (
                <div key={m.user_id} className="flex items-center justify-between rounded-lg border border-white/5 px-3 py-2 text-sm">
                  <div>
                    <div>{m.full_name || m.email}</div>
                    <div className="text-xs text-zinc-500">{m.email}</div>
                  </div>
                  <span className="rounded-md bg-zinc-500/20 px-2 py-0.5 text-xs capitalize">{m.role}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function Field({
  label, value, onChange, type = "text",
}: { label: string; value: string | number; onChange: (v: string) => void; type?: string }) {
  return (
    <div>
      <label className="text-xs text-zinc-500">{label}</label>
      <input
        type={type}
        className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
