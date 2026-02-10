// When NEXT_PUBLIC_API_URL is set, use it (local dev / Render).
// When empty (CloudFront deploy), use relative /api path.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function apiFetch<T>(
  path: string,
  params?: Record<string, string | number | undefined>
): Promise<T> {
  const fullPath = API_BASE ? `${API_BASE}${path}` : `/api${path}`;
  const url = new URL(fullPath, typeof window !== "undefined" ? window.location.origin : "http://localhost:3000");
  if (params) {
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        url.searchParams.set(key, String(val));
      }
    });
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
