import { ApiError, apiBaseUrl } from "./api";

// Official-source retrieval can take a while on a cold server; stay generous but bounded.
const TIMEOUT_MS = 60_000;

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, { ...init, signal: controller.signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw new ApiError("timeout", "The service took too long to respond.");
    throw new ApiError("network", "Could not reach the service.");
  } finally {
    window.clearTimeout(timer);
  }
  const body: unknown = await response.json().catch(() => null);
  if (response.ok) {
    if (body === null) throw new ApiError("server", "The service returned an unexpected response.");
    return body as T;
  }
  const detail = (body as { detail?: unknown } | null)?.detail;
  const text = typeof detail === "string" ? detail : "";
  if (response.status === 413) throw new ApiError("too_large", text || "The upload is too large.");
  if (response.status === 415) throw new ApiError("unsupported_media", text || "Unsupported file type.");
  if (response.status === 422) throw new ApiError("validation", text || "Please check the form and try again.");
  if (response.status === 404) throw new ApiError("validation", text || "Not found.");
  throw new ApiError("server", "The service encountered an error.");
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const getJson = <T>(path: string) => request<T>(path);
export const postJson = <T>(path: string, body: unknown) => request<T>(path, json(body));
export const postForm = <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form });

export function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined && v !== "") q.set(k, String(v));
  const s = q.toString();
  return s ? `?${s}` : "";
}
