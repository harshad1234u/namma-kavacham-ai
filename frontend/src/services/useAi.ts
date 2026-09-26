import { useEffect, useState } from "react";
import type { AiStatus } from "../types/civic";
import { getJson } from "./civicApi";

let cached: AiStatus | null = null;

/** Whether the backend has NVIDIA NIM configured (so we only ask for AI consent when it can be used). */
export function useAiStatus(): AiStatus | null {
  const [status, setStatus] = useState<AiStatus | null>(cached);
  useEffect(() => {
    if (cached) return;
    getJson<AiStatus>("/v1/meta/ai")
      .then((s) => {
        cached = s;
        setStatus(s);
      })
      .catch(() => setStatus(null));
  }, []);
  return status;
}

export function resetAiStatusCache() {
  cached = null;
}
