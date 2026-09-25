import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CAMERA_CONSTRAINTS, MAX_CAPTURE_EDGE, captureFrame, openCamera, stopStream } from "../services/camera";

const getUserMedia = vi.fn();
const domError = (name: string, message = "") => Object.assign(new Error(message), { name });

function setCameraEnv({ secure = true, mediaDevices = true }: { secure?: boolean; mediaDevices?: boolean } = {}) {
  Object.defineProperty(window, "isSecureContext", { value: secure, configurable: true });
  Object.defineProperty(navigator, "mediaDevices", { value: mediaDevices ? { getUserMedia } : undefined, configurable: true });
}

function fakeVideo(w: number, h: number) {
  return { videoWidth: w, videoHeight: h } as HTMLVideoElement;
}

beforeEach(() => {
  getUserMedia.mockReset();
  setCameraEnv();
});
afterEach(() => vi.restoreAllMocks());

describe("openCamera", () => {
  it("asks for the rear camera without making it mandatory, and no audio", async () => {
    const stream = {} as MediaStream;
    getUserMedia.mockResolvedValueOnce(stream);
    await expect(openCamera()).resolves.toBe(stream);
    expect(getUserMedia).toHaveBeenCalledWith(CAMERA_CONSTRAINTS);
    expect(CAMERA_CONSTRAINTS).toMatchObject({ audio: false, video: { facingMode: { ideal: "environment" } } });
  });

  it("falls back to any camera when the browser rejects the constraints", async () => {
    const stream = {} as MediaStream;
    getUserMedia.mockRejectedValueOnce(domError("OverconstrainedError")).mockResolvedValueOnce(stream);
    await expect(openCamera()).resolves.toBe(stream);
    expect(getUserMedia).toHaveBeenLastCalledWith({ audio: false, video: true });
  });

  it("requires a secure context before touching the camera", async () => {
    setCameraEnv({ secure: false, mediaDevices: false });
    await expect(openCamera()).rejects.toMatchObject({ kind: "insecure" });
  });

  it("reports browsers without getUserMedia as unsupported", async () => {
    setCameraEnv({ mediaDevices: false });
    await expect(openCamera()).rejects.toMatchObject({ kind: "unsupported" });
  });

  it.each([
    [domError("NotAllowedError", "Permission denied"), "denied"],
    [domError("NotAllowedError", "Permission dismissed"), "dismissed"],
    [domError("SecurityError"), "denied"],
    [domError("NotFoundError"), "not_found"],
    [domError("NotReadableError", "Device in use"), "unavailable"],
    [domError("AbortError"), "unavailable"],
    [new Error("boom"), "failed"],
  ])("classifies %s as %s", async (err, kind) => {
    getUserMedia.mockRejectedValueOnce(err);
    await expect(openCamera()).rejects.toMatchObject({ kind });
  });

  it("reports no camera when the any-camera retry also fails", async () => {
    getUserMedia.mockRejectedValueOnce(domError("OverconstrainedError")).mockRejectedValueOnce(domError("NotFoundError"));
    await expect(openCamera()).rejects.toMatchObject({ kind: "not_found" });
  });
});

describe("stopStream", () => {
  it("stops every track and tolerates no stream", () => {
    const tracks = [{ stop: vi.fn() }, { stop: vi.fn() }];
    stopStream({ getTracks: () => tracks } as unknown as MediaStream);
    tracks.forEach((t) => expect(t.stop).toHaveBeenCalled());
    expect(() => stopStream(null)).not.toThrow();
  });
});

describe("captureFrame", () => {
  const drawImage = vi.fn();
  let blob: Blob | null;

  beforeEach(() => {
    drawImage.mockReset();
    blob = new Blob(["jpeg-bytes"], { type: "image/jpeg" });
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ drawImage } as unknown as CanvasRenderingContext2D);
    vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(function (cb) {
      cb(blob);
    });
  });

  it("converts the current frame to a JPEG file with a generic name", async () => {
    const file = await captureFrame(fakeVideo(1280, 720));
    expect(file).toBeInstanceOf(File);
    expect(file.type).toBe("image/jpeg");
    expect(file.name).toBe("camera-photo.jpg");
    expect(HTMLCanvasElement.prototype.toBlob).toHaveBeenCalledWith(expect.any(Function), "image/jpeg", 0.92);
    expect(drawImage).toHaveBeenCalledWith(expect.anything(), 0, 0, 1280, 720);
  });

  it("downscales very large frames", async () => {
    await captureFrame(fakeVideo(4000, 3000));
    expect(drawImage).toHaveBeenCalledWith(expect.anything(), 0, 0, MAX_CAPTURE_EDGE, 1500);
  });

  it("keeps a PNG fallback type from browsers that cannot encode JPEG", async () => {
    blob = new Blob(["png-bytes"], { type: "image/png" });
    const file = await captureFrame(fakeVideo(640, 480));
    expect(file.type).toBe("image/png");
  });

  it("fails capture when there is no frame yet", async () => {
    await expect(captureFrame(fakeVideo(0, 0))).rejects.toMatchObject({ kind: "capture" });
  });

  it("fails capture when drawing the frame throws", async () => {
    drawImage.mockImplementationOnce(() => {
      throw new Error("InvalidStateError");
    });
    await expect(captureFrame(fakeVideo(640, 480))).rejects.toMatchObject({ kind: "capture" });
  });

  it("fails conversion on an empty or missing image", async () => {
    blob = null;
    await expect(captureFrame(fakeVideo(640, 480))).rejects.toMatchObject({ kind: "conversion" });
    blob = new Blob([], { type: "image/jpeg" });
    await expect(captureFrame(fakeVideo(640, 480))).rejects.toMatchObject({ kind: "conversion" });
  });
});
