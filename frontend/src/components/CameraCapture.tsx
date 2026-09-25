import { AlertTriangle, Camera, Check, RotateCcw, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useLanguage } from "../i18n/LanguageContext";
import { CameraError, captureFrame, openCamera, stopStream, type CameraErrorKind } from "../services/camera";

type Phase = "starting" | "live" | "captured" | "error";

interface Props {
  onUsePhoto: (photo: File) => void;
  onCancel: () => void;
  onUploadInstead: () => void;
}

const btn = "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 font-semibold";
const primary = `${btn} bg-navy text-white hover:bg-navy-deep disabled:cursor-not-allowed disabled:opacity-40`;
const secondary = `${btn} bg-surface-high text-navy hover:bg-surface`;

// Mounted only after the user taps "Take a photo", so permission is never requested on page load.
export function CameraCapture({ onUsePhoto, onCancel, onUploadInstead }: Props) {
  const { t } = useLanguage();
  const boxRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [phase, setPhase] = useState<Phase>("starting");
  const [error, setError] = useState<CameraErrorKind | null>(null);
  const [photo, setPhoto] = useState<{ file: File; url: string } | null>(null);

  function stop() {
    stopStream(streamRef.current);
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }

  useEffect(() => {
    if (phase !== "starting") return;
    let cancelled = false;
    openCamera().then(
      (stream) => {
        // Unmounted or cancelled while the permission prompt was open: release the camera at once.
        if (cancelled || !videoRef.current) return stopStream(stream);
        streamRef.current = stream;
        videoRef.current.srcObject = stream;
        setPhase("live");
      },
      (err: unknown) => {
        if (cancelled) return;
        setError(err instanceof CameraError ? err.kind : "failed");
        setPhase("error");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [phase]);

  useEffect(() => stop, []); // unmount (tab switch, route change, parent closing the camera)

  // On a phone the camera opens below the fold; bring the preview and Capture button into view.
  // Block body: newer browsers return a Promise from scrollIntoView, which React would treat as a cleanup.
  useEffect(() => {
    boxRef.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }, []);

  useEffect(() => () => {
    if (photo) URL.revokeObjectURL(photo.url);
  }, [photo]);

  async function capture() {
    try {
      const file = await captureFrame(videoRef.current as HTMLVideoElement);
      setPhoto({ file, url: URL.createObjectURL(file) });
      setPhase("captured");
    } catch (err) {
      setError(err instanceof CameraError ? err.kind : "capture");
      setPhase("error");
    } finally {
      stop(); // the camera never stays on after a capture attempt
    }
  }

  function restart() {
    stop();
    setPhoto(null);
    setError(null);
    setPhase("starting");
  }

  const status =
    phase === "starting" ? t.cameraRequesting : phase === "live" ? t.cameraLive : phase === "captured" ? t.cameraCaptured : null;

  return (
    <div ref={boxRef} className="mt-3 flex scroll-mt-4 flex-col gap-3 rounded-md border border-line p-3" data-testid="camera">
      <p role="status" aria-live="polite" className="text-sm text-navy">
        {status}
      </p>

      {(phase === "starting" || phase === "live") && (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          aria-label={t.cameraPreviewLabel}
          className="block max-h-[50vh] min-h-40 w-full rounded-md bg-black object-contain"
        />
      )}
      {phase === "captured" && photo && (
        <img src={photo.url} alt={t.cameraPhotoLabel} className="block max-h-[50vh] w-full rounded-md border border-line object-contain" />
      )}
      {phase === "error" && error && (
        <p role="alert" className="flex gap-2 rounded-md border-l-4 border-red-300 bg-red-50 p-3 text-sm text-red-900">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            {t.cameraErrors[error]} {t.cameraUploadFallback}
          </span>
        </p>
      )}

      <p className="text-xs text-ink-muted">{t.cameraPrivacy}</p>

      <div className="flex flex-wrap gap-2">
        {(phase === "starting" || phase === "live") && (
          <button type="button" onClick={capture} disabled={phase !== "live"} className={primary}>
            <Camera className="size-4" aria-hidden /> {t.cameraCapture}
          </button>
        )}
        {phase === "captured" && photo && (
          <>
            <button type="button" onClick={() => onUsePhoto(photo.file)} className={primary}>
              <Check className="size-4" aria-hidden /> {t.cameraUsePhoto}
            </button>
            <button type="button" onClick={restart} className={secondary}>
              <RotateCcw className="size-4" aria-hidden /> {t.cameraRetake}
            </button>
          </>
        )}
        {phase === "error" && (
          <button type="button" onClick={restart} className={primary}>
            <RotateCcw className="size-4" aria-hidden /> {t.cameraRetry}
          </button>
        )}
        {phase !== "captured" && (
          <button type="button" onClick={() => (stop(), onUploadInstead())} className={secondary}>
            <Upload className="size-4" aria-hidden /> {t.cameraUploadInstead}
          </button>
        )}
        <button type="button" onClick={() => (stop(), onCancel())} className={`${btn} text-ink-muted hover:text-navy`}>
          <X className="size-4" aria-hidden /> {t.cameraCancel}
        </button>
      </div>
    </div>
  );
}
