export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function api<T = any>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (options?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(`${API}${path}`, {
      ...options,
      cache: "no-store",
      credentials: "include",
      headers,
    });
  } catch {
    throw new Error(
      `Cannot reach the OrgMemory API at ${API}. Check that the backend is running and refresh the page.`,
    );
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

export function formatDate(value?: string) {
  return value ? new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "—";
}
