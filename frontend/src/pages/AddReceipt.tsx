import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { motion } from "motion/react";
import { Camera, Upload, FileUp } from "lucide-react";
import { useUploadReceipt } from "@/hooks/useReceipts";
import { useToastStore } from "@/stores/toastStore";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function AddReceipt() {
  const navigate = useNavigate();
  const upload = useUploadReceipt();
  const addToast = useToastStore((s) => s.addToast);
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback(
    async (file: File, source: "camera" | "upload") => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("source", source);
      try {
        await upload.mutateAsync(formData);
        addToast({
          type: "info",
          title: "Receipt uploaded",
          message: "Processing has started — you'll be notified when it's done",
        });
        navigate("/receipts");
      } catch {
        addToast({
          type: "error",
          title: "Upload failed",
          message: "Could not upload the receipt. Please try again.",
        });
      }
    },
    [upload, navigate, addToast],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file, "upload");
    },
    [handleFile],
  );

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Add Receipt</h1>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {/* Drop zone */}
        <Card
          className={`cursor-pointer transition-colors ${dragOver ? "border-accent bg-accent/5" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
        >
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent/10">
              <FileUp size={28} className="text-accent" />
            </div>
            <div className="text-center">
              <p className="font-medium">Drop a receipt here or click to browse</p>
              <p className="mt-1 text-sm text-text-muted">
                Supports JPEG, PNG, HEIC, and PDF
              </p>
            </div>
            {upload.isPending && (
              <p className="text-sm text-accent">Uploading...</p>
            )}
            {upload.isError && (
              <p className="text-sm text-destructive">
                {upload.error instanceof Error ? upload.error.message : "Upload failed"}
              </p>
            )}
          </CardContent>
        </Card>

        <input
          ref={fileRef}
          type="file"
          accept="image/*,.pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file, "upload");
          }}
        />

        {/* Camera capture (mobile) */}
        <div className="mt-4 flex gap-3">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => cameraRef.current?.click()}
          >
            <Camera size={18} /> Take Photo
          </Button>
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => fileRef.current?.click()}
          >
            <Upload size={18} /> Choose File
          </Button>
        </div>

        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file, "camera");
          }}
        />
      </motion.div>
    </div>
  );
}
