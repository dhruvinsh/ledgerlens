import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { motion } from "motion/react";
import {
  X,
  Camera,
  Flashlight,
  FlashlightOff,
  RotateCcw,
  Check,
  CameraOff,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

type CameraState = "loading" | "preview" | "review" | "error" | "fallback";

interface CameraCaptureProps {
  onCapture: (file: File) => void;
  onClose: () => void;
}

export function CameraCapture({ onCapture, onClose }: CameraCaptureProps) {
  const [state, setState] = useState<CameraState>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [torchAvailable, setTorchAvailable] = useState(false);
  const [torchOn, setTorchOn] = useState(false);
  const [reviewSrc, setReviewSrc] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const cancelledRef = useRef(false);
  const blobRef = useRef<Blob | null>(null);
  const blobUrlRef = useRef<string | null>(null);
  const fallbackInputRef = useRef<HTMLInputElement>(null);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const revokeBlobUrl = useCallback(() => {
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = null;
      setReviewSrc(null);
    }
  }, []);

  const initCamera = useCallback(async () => {
    setState("loading");
    setTorchAvailable(false);
    setTorchOn(false);

    // Secure context check
    if (!window.isSecureContext) {
      setErrorMsg(
        "Camera requires a secure connection (HTTPS). Please access the app over HTTPS.",
      );
      setState("error");
      return;
    }

    // Permission pre-check (Safari doesn't support this — catch and skip)
    try {
      const perm = await navigator.permissions.query({
        name: "camera" as PermissionName,
      });
      if (perm.state === "denied") {
        setErrorMsg(
          "Camera access is blocked. Please enable it in your browser or device settings, then try again.",
        );
        setState("error");
        return;
      }
    } catch {
      // Safari/WebKit throws — proceed to getUserMedia
    }

    // Guard against component unmount during async init
    if (cancelledRef.current) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment",
          width: { ideal: 1920 },
          height: { ideal: 1080 },
          aspectRatio: { ideal: 16 / 9 },
        },
      });

      if (cancelledRef.current) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      // Check torch capability
      const track = stream.getVideoTracks()[0];
      if (track) {
        const caps = track.getCapabilities?.();
        if (caps && "torch" in caps) {
          setTorchAvailable(true);
        }
      }

      setState("preview");
    } catch {
      if (cancelledRef.current) return;
      // getUserMedia failed — offer fallback
      setState("fallback");
    }
  }, []);

  // Init on mount, cleanup on unmount
  useEffect(() => {
    cancelledRef.current = false;
    document.body.style.overflow = "hidden";
    initCamera();

    return () => {
      cancelledRef.current = true;
      stopStream();
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
      document.body.style.overflow = "";
    };
  }, [initCamera, stopStream]);

  // Escape to close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const handleCapture = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    // Size canvas to native video resolution
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          // toBlob can return null per spec
          setErrorMsg("Capture failed — please try again.");
          // Don't stop stream, user can retry
          return;
        }

        blobRef.current = blob;

        // Blob ready — now stop stream
        stopStream();

        const url = URL.createObjectURL(blob);
        blobUrlRef.current = url;
        setReviewSrc(url);
        setErrorMsg("");
        setState("review");
      },
      "image/jpeg",
      0.92,
    );
  }, [stopStream]);

  const handleRetake = useCallback(() => {
    revokeBlobUrl();
    blobRef.current = null;
    setTorchOn(false);
    initCamera();
  }, [revokeBlobUrl, initCamera]);

  const handleUsePhoto = useCallback(() => {
    const blob = blobRef.current;
    if (!blob) return;

    const file = new File([blob], "camera-capture.jpg", {
      type: "image/jpeg",
    });

    revokeBlobUrl();
    blobRef.current = null;
    onCapture(file);
  }, [onCapture, revokeBlobUrl]);

  const handleTorchToggle = useCallback(async () => {
    const track = streamRef.current?.getVideoTracks()[0];
    if (!track) return;
    const next = !torchOn;
    try {
      await track.applyConstraints({
        advanced: [{ torch: next } as MediaTrackConstraintSet],
      });
      setTorchOn(next);
    } catch {
      // Torch failed — hide button
      setTorchAvailable(false);
    }
  }, [torchOn]);

  const handleClose = useCallback(() => {
    stopStream();
    revokeBlobUrl();
    onClose();
  }, [stopStream, revokeBlobUrl, onClose]);

  const handleFallbackClick = useCallback(() => {
    fallbackInputRef.current?.click();
  }, []);

  const handleFallbackFile = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onCapture(file);
    },
    [onCapture],
  );

  return createPortal(
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-50 flex flex-col bg-black"
    >
      {/* Top bar */}
      <div className="relative z-10 flex items-center justify-between px-4 py-3">
        <button
          onClick={handleClose}
          className="rounded-full bg-white/10 p-2 text-white backdrop-blur-sm transition-colors hover:bg-white/20"
        >
          <X size={22} />
        </button>

        {state === "preview" && torchAvailable && (
          <button
            onClick={handleTorchToggle}
            className="rounded-full bg-white/10 p-2 text-white backdrop-blur-sm transition-colors hover:bg-white/20"
          >
            {torchOn ? <FlashlightOff size={22} /> : <Flashlight size={22} />}
          </button>
        )}
      </div>

      {/* Viewfinder / Review / States */}
      <div className="relative flex flex-1 items-center justify-center overflow-hidden">
        {/* Loading */}
        {state === "loading" && (
          <div className="flex flex-col items-center gap-4">
            <Spinner className="[&>div]:h-10 [&>div]:w-10 [&>div]:border-3 [&>div]:border-white/20 [&>div]:border-t-white" />
            <p className="text-sm text-white/60">Starting camera...</p>
          </div>
        )}

        {/* Live preview */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`h-full w-full object-cover ${state === "preview" ? "" : "hidden"}`}
          onLoadedMetadata={() => {
            // Ensure video plays once metadata is loaded
            videoRef.current?.play().catch(() => {});
          }}
        />

        {/* Capture error overlay (toBlob failed) */}
        {state === "preview" && errorMsg && (
          <div className="absolute inset-x-0 top-0 bg-red-600/90 px-4 py-2 text-center text-sm text-white">
            {errorMsg}
          </div>
        )}

        {/* Review captured image */}
        {state === "review" && reviewSrc && (
          <img
            src={reviewSrc}
            alt="Captured receipt"
            className="h-full w-full object-contain"
          />
        )}

        {/* Error state */}
        {state === "error" && (
          <div className="flex max-w-xs flex-col items-center gap-4 text-center">
            <div className="rounded-full bg-white/10 p-4">
              <CameraOff size={36} className="text-white/70" />
            </div>
            <p className="text-sm leading-relaxed text-white/80">{errorMsg}</p>
            <Button variant="outline" onClick={handleClose} className="border-white/20 text-white hover:bg-white/10">
              Go Back
            </Button>
          </div>
        )}

        {/* Fallback state */}
        {state === "fallback" && (
          <div className="flex max-w-xs flex-col items-center gap-4 text-center">
            <div className="rounded-full bg-white/10 p-4">
              <AlertTriangle size={36} className="text-amber-400" />
            </div>
            <p className="text-sm leading-relaxed text-white/80">
              In-app camera isn't available on this device. You can use the
              system camera instead.
            </p>
            <Button
              onClick={handleFallbackClick}
              className="bg-white text-black hover:bg-white/90"
            >
              <Camera size={18} /> Open System Camera
            </Button>
            <input
              ref={fallbackInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={handleFallbackFile}
            />
            <button
              onClick={handleClose}
              className="text-sm text-white/50 underline underline-offset-2"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Bottom controls */}
      {state === "preview" && (
        <div className="relative z-10 flex items-center justify-center pb-10 pt-6">
          <button
            onClick={handleCapture}
            className="group flex h-[72px] w-[72px] items-center justify-center rounded-full border-[3px] border-white transition-transform active:scale-95"
          >
            <div className="h-[58px] w-[58px] rounded-full bg-white transition-colors group-active:bg-white/80" />
          </button>
        </div>
      )}

      {state === "review" && (
        <div className="relative z-10 flex items-center justify-center gap-8 pb-10 pt-6">
          <button
            onClick={handleRetake}
            className="flex flex-col items-center gap-1.5 text-white/70 transition-colors hover:text-white"
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/10 backdrop-blur-sm">
              <RotateCcw size={22} />
            </div>
            <span className="text-xs">Retake</span>
          </button>

          <button
            onClick={handleUsePhoto}
            className="flex flex-col items-center gap-1.5 text-white transition-colors"
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent">
              <Check size={26} />
            </div>
            <span className="text-xs font-medium">Use Photo</span>
          </button>
        </div>
      )}

      {/* Hidden canvas for capture */}
      <canvas ref={canvasRef} className="hidden" />
    </motion.div>,
    document.body,
  );
}
