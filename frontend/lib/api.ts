/**
 * API client – auth via httpOnly cookie (credentials: include).
 * Token is NOT stored in localStorage / sessionStorage (XSS-resistant).
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** @deprecated Kept as no-op for gradual migration – do not store tokens in JS */
export function getToken(): string | null {
  return null;
}

/** @deprecated Tokens are set as httpOnly cookies by the API */
export function setToken(_token: string) {
  /* intentional no-op */
}

export function clearToken() {
  /* cookie cleared via POST /api/auth/logout */
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include", // send/receive httpOnly auth cookie
  });

  if (res.status === 401) {
    if (typeof window !== "undefined" && !path.includes("/auth/login")) {
      // session expired / not logged in
    }
    const err = await res.json().catch(() => ({ detail: "Not authenticated" }));
    throw new Error(typeof err.detail === "string" ? err.detail : "Not authenticated");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join(", ")
          : `Request failed (${res.status})`;
    throw new Error(msg);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export async function logout(): Promise<void> {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } catch {
    /* ignore */
  }
}

export { API_URL };
