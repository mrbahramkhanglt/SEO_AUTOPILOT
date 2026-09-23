"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, logout } from "@/lib/api";

interface Website {
  id: string;
  domain: string;
  url: string;
  name: string | null;
  status: string;
  last_score: number | null;
  is_valid: boolean;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [websites, setWebsites] = useState<Website[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newUrl, setNewUrl] = useState("");
  const [user, setUser] = useState<{ email?: string; is_superuser?: boolean } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const me = await api<{ email?: string; is_superuser?: boolean }>("/api/auth/me");
        setUser(me);
        loadWebsites();
      } catch {
        router.replace("/auth/login");
      }
    })();
  }, [router]);

  async function loadWebsites() {
    try {
      const data = await api<{ items: Website[] }>("/api/websites");
      setWebsites(data.items);
    } catch (err: any) {
      if (err.message?.includes("401") || err.message?.includes("Not authenticated")) {
        await logout();
        router.replace("/auth/login");
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function addWebsite(e: React.FormEvent) {
    e.preventDefault();
    if (!newUrl.trim()) return;
    try {
      const website = await api<Website>("/api/websites", {
        method: "POST",
        body: JSON.stringify({ url: newUrl.trim() }),
      });
      setNewUrl("");
      await api(`/api/websites/${website.id}/crawl`, {
        method: "POST",
        body: JSON.stringify({ max_pages: 30, max_depth: 3 }),
      }).catch(() => null);
      router.push(`/dashboard/websites/${website.id}`);
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <header className="border-b border-white/5 px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-xs font-bold">
              SA
            </div>
            <span className="font-semibold">SEO Autopilot AI</span>
          </div>
          <div className="flex items-center gap-4">
            {user?.is_superuser && (
              <a href="/dashboard/admin" className="text-sm text-indigo-400 hover:text-indigo-300">
                Admin
              </a>
            )}
            {user?.email && (
              <span className="hidden text-xs text-zinc-500 sm:inline">{user.email}</span>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="text-sm text-zinc-400 hover:text-white"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Your Websites</h1>
        </div>

        <form onSubmit={addWebsite} className="mt-6 flex gap-3">
          <input
            type="text"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            placeholder="https://example.com"
            className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm outline-none focus:border-indigo-500/50"
          />
          <button
            type="submit"
            className="rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold hover:bg-indigo-500"
          >
            Add website
          </button>
        </form>

        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

        {loading ? (
          <p className="mt-10 text-zinc-500">Loading…</p>
        ) : websites.length === 0 ? (
          <div className="mt-16 text-center text-zinc-500">
            <p>No websites yet.</p>
            <p className="mt-1 text-sm">Enter a URL above to start SEO Autopilot.</p>
          </div>
        ) : (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {websites.map((w) => (
              <a
                key={w.id}
                href={`/dashboard/websites/${w.id}`}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 transition hover:border-indigo-500/40 hover:bg-white/[0.05]"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold">{w.name || w.domain}</h3>
                    <p className="mt-0.5 text-xs text-zinc-500 truncate max-w-[200px]">
                      {w.url}
                    </p>
                  </div>
                  {w.last_score != null && (
                    <div className="rounded-lg bg-indigo-500/20 px-2 py-1 text-sm font-bold text-indigo-300">
                      {w.last_score}
                    </div>
                  )}
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      w.status === "ready" || w.status === "monitoring"
                        ? "bg-emerald-400"
                        : w.status === "error"
                        ? "bg-red-400"
                        : "bg-amber-400"
                    }`}
                  />
                  <span className="text-xs capitalize text-zinc-400">{w.status}</span>
                </div>
              </a>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
