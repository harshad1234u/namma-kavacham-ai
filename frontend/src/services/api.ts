import type { AnalyzeRequest, AnalyzeResponse } from "../types/analysis";

export type ApiErrorKind = "network" | "timeout" | "validation" | "too_large" | "unsupported_media" | "server";

export class ApiError extends Error {
  constructor(
    public readonly kind: ApiErrorKind,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const REQUEST_TIMEOUT_MS = 30_000;

export function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (configured) return configured.replace(/\/$/, "");
  // Same host as the page, so a phone on the LAN reaches the laptop's backend.
  return `${window.location.protocol}//${window.location.hostname}:8000`;
}

function detailText(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (d as { msg?: string }).msg ?? "").filter(Boolean).join("; ");
  return "";
}

// Shape check for the fields the report reads unconditionally; not a full schema validation.
function isAnalyzeResponse(data: unknown): data is AnalyzeResponse {
  const d = data as Partial<AnalyzeResponse> | null;
  return (
    !!d &&
    typeof d === "object" &&
    typeof d.risk?.level === "string" &&
    typeof d.risk.score === "number" &&
    typeof d.risk.assessment_status === "string" &&
    Array.isArray(d.evidence) &&
    Array.isArray(d.safe_next_steps) &&
    Array.isArray(d.missing_metadata) &&
    Array.isArray(d.limitations) &&
    typeof d.explanation?.en === "string" &&
    typeof d.government_claim?.claim_status === "string" &&
    Array.isArray(d.url_intelligence?.extracted_urls) &&
    typeof d.provider_flags === "object" &&
    d.provider_flags !== null
  );
}

export async function submitAnalysis(request: AnalyzeRequest): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("payload", JSON.stringify(request));

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/v1/analyze`, { method: "POST", body: form, signal: controller.signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw new ApiError("timeout", "The analysis took too long to respond.");
    throw new ApiError("network", "Could not reach the analysis service.");
  } finally {
    window.clearTimeout(timer);
  }

  if (response.ok) {
    const data: unknown = await response.json().catch(() => null);
    // A proxy page or a partial body would otherwise crash the report and blank the screen.
    if (!isAnalyzeResponse(data)) throw new ApiError("server", "The analysis service returned an unexpected response.");
    return data;
  }

  const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
  const detail = detailText(body.detail);
  switch (response.status) {
    case 413:
      throw new ApiError("too_large", detail || "The content or screenshot is too large.");
    case 415:
      throw new ApiError("unsupported_media", detail || "Unsupported file type.");
    case 422:
      throw new ApiError("validation", detail || "The request could not be accepted.");
    default:
      throw new ApiError("server", "The analysis service encountered an error.");
  }
}
