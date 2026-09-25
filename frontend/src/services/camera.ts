// Browser camera capture. Frames stay on the device: a captured photo only feeds local OCR.
export type CameraErrorKind =
  | "insecure"
  | "unsupported"
  | "denied"
  | "dismissed"
  | "not_found"
  | "unavailable"
  | "failed"
  | "capture"
  | "conversion";

export class CameraError extends Error {
  constructor(public readonly kind: CameraErrorKind) {
    super(`Camera ${kind}`);
    this.name = "CameraError";
  }
}

export const CAMERA_CONSTRAINTS: MediaStreamConstraints = {
  audio: false,
  // "ideal", not "exact": devices or browsers without a rear camera fall back to any camera.
  video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
};

// Larger frames add OCR time and memory without improving recognition of message text.
export const MAX_CAPTURE_EDGE = 2000;

function classify(err: unknown): CameraErrorKind {
  const name = (err as { name?: string } | null)?.name;
  const message = String((err as { message?: string } | null)?.message ?? "");
  // Chrome reports a closed permission prompt as NotAllowedError with "Permission dismissed".
  if (name === "NotAllowedError" || name === "PermissionDeniedError" || name === "SecurityError") {
    return /dismiss/i.test(message) ? "dismissed" : "denied";
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError" || name === "OverconstrainedError") return "not_found";
  if (name === "NotReadableError" || name === "TrackStartError" || name === "AbortError") return "unavailable";
  return "failed";
}

export async function openCamera(): Promise<MediaStream> {
  // Checked first: on plain HTTP, browsers hide navigator.mediaDevices entirely.
  if (window.isSecureContext === false) throw new CameraError("insecure");
  if (!navigator.mediaDevices?.getUserMedia) throw new CameraError("unsupported");
  try {
    return await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS);
  } catch (err) {
    // Some older browsers reject the constraint object itself; retry asking for any camera.
    if ((err as { name?: string })?.name !== "OverconstrainedError" && !(err instanceof TypeError)) throw new CameraError(classify(err));
    try {
      return await navigator.mediaDevices.getUserMedia({ audio: false, video: true });
    } catch (retryErr) {
      throw new CameraError(classify(retryErr));
    }
  }
}

export function stopStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}

export async function captureFrame(video: HTMLVideoElement): Promise<File> {
  const { videoWidth: w, videoHeight: h } = video;
  if (!w || !h) throw new CameraError("capture"); // no frame yet, or the stream ended
  const scale = Math.min(1, MAX_CAPTURE_EDGE / Math.max(w, h));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(w * scale);
  canvas.height = Math.round(h * scale);
  try {
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new CameraError("capture");
    try {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    } catch {
      throw new CameraError("capture");
    }
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
    if (!blob || blob.size === 0) throw new CameraError("conversion");
    // Browsers that cannot encode JPEG fall back to PNG; keep the real type. Generic name: never sent anywhere.
    const type = blob.type || "image/jpeg";
    return new File([blob], type === "image/png" ? "camera-photo.png" : "camera-photo.jpg", { type });
  } finally {
    canvas.width = canvas.height = 0; // release the pixel buffer right away
  }
}
