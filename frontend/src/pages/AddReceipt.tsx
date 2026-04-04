import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "motion/react";
import {
  Camera,
  Upload,
  FileUp,
  X,
  FileText,
  ImageIcon,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { useUploadReceipt, useUploadReceiptBatch } from "@/hooks/useReceipts";
import { useToastStore } from "@/stores/toastStore";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CameraCapture } from "@/components/CameraCapture";
import type { BatchUploadError } from "@/lib/types";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileKey(f: File): string {
  return `${f.name}:${f.size}:${f.lastModified}`;
}

export default function AddReceipt() {
  const navigate = useNavigate();
  const singleUpload = useUploadReceipt();
  const batchUpload = useUploadReceiptBatch();
  const addToast = useToastStore((s) => s.addToast);
  const fileRef = useRef<HTMLInputElement>(null);

  const [dragOver, setDragOver] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [failedFiles, setFailedFiles] = useState<BatchUploadError[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [batchSuccess, setBatchSuccess] = useState(false);

  const isUploading = batchUpload.isPending || singleUpload.isPending;

  const addFiles = useCallback(
    (incoming: File[]) => {
      setSelectedFiles((prev) => {
        const existing = new Set(prev.map(fileKey));
        const unique: File[] = [];
        let dupeCount = 0;
        for (const f of incoming) {
          if (existing.has(fileKey(f))) {
            dupeCount++;
          } else {
            existing.add(fileKey(f));
            unique.push(f);
          }
        }
        if (dupeCount > 0) {
          addToast({
            type: "info",
            title: "Duplicates skipped",
            message: `${dupeCount} duplicate file${dupeCount > 1 ? "s" : ""} removed`,
          });
        }
        return [...prev, ...unique];
      });
      setFailedFiles([]);
    },
    [addToast],
  );

  const removeFile = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearAll = useCallback(() => {
    setSelectedFiles([]);
    setFailedFiles([]);
    setBatchSuccess(false);
    setUploadProgress(null);
  }, []);

  const handleBatchUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return;

    const formData = new FormData();
    for (const file of selectedFiles) {
      formData.append("files", file);
    }
    formData.append("source", "upload");

    setUploadProgress(0);
    setFailedFiles([]);
    setBatchSuccess(false);

    try {
      const result = await batchUpload.mutateAsync({
        formData,
        onProgress: setUploadProgress,
      });

      const successCount = result.receipts.length;
      const errorCount = result.errors.length;

      if (errorCount === 0) {
        // Full success — navigate away
        addToast({
          type: "info",
          title: `${successCount} receipt${successCount > 1 ? "s" : ""} uploaded`,
          message:
            "Queued for processing — you\u2019ll be notified when done",
        });
        navigate("/receipts");
      } else if (successCount > 0) {
        // Partial success — stay on page, show failures
        addToast({
          type: "warning",
          title: `${successCount} uploaded, ${errorCount} failed`,
          message: "Check the failed files below",
        });
        setFailedFiles(result.errors);
        // Remove successfully uploaded files, keep failed ones
        const failedNames = new Set(result.errors.map((e) => e.filename));
        setSelectedFiles((prev) =>
          prev.filter((f) => failedNames.has(f.name)),
        );
        setBatchSuccess(true);
      } else {
        // All failed
        addToast({
          type: "error",
          title: "All uploads failed",
          message: result.errors[0]?.detail ?? "Unknown error",
        });
        setFailedFiles(result.errors);
      }
    } catch {
      addToast({
        type: "error",
        title: "Upload failed",
        message: "Could not upload the receipts. Please try again.",
      });
    } finally {
      setUploadProgress(null);
    }
  }, [selectedFiles, batchUpload, navigate, addToast]);

  const handleCameraCapture = useCallback(
    async (file: File) => {
      setCameraOpen(false);
      const formData = new FormData();
      formData.append("file", file);
      formData.append("source", "camera");
      try {
        await singleUpload.mutateAsync(formData);
        addToast({
          type: "info",
          title: "Receipt uploaded",
          message:
            "Processing has started — you\u2019ll be notified when it\u2019s done",
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
    [singleUpload, navigate, addToast],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) addFiles(files);
    },
    [addFiles],
  );

  const onFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []);
      if (files.length > 0) addFiles(files);
      e.target.value = "";
    },
    [addFiles],
  );

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Add Receipts</h1>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="space-y-4"
      >
        {/* Drop zone */}
        <Card
          className={`cursor-pointer transition-colors ${dragOver ? "border-accent bg-accent/5" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => !isUploading && fileRef.current?.click()}
        >
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent/10">
              <FileUp size={28} className="text-accent" />
            </div>
            <div className="text-center">
              <p className="font-medium">
                Drop receipts here or click to browse
              </p>
              <p className="mt-1 text-sm text-text-muted">
                Supports JPEG, PNG, and PDF — select multiple files
              </p>
            </div>
          </CardContent>
        </Card>

        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,.pdf"
          multiple
          className="hidden"
          onChange={onFileInputChange}
        />

        {/* Action buttons */}
        <div className="flex gap-3">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => setCameraOpen(true)}
            disabled={isUploading}
          >
            <Camera size={18} /> Take Photo
          </Button>
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => fileRef.current?.click()}
            disabled={isUploading}
          >
            <Upload size={18} /> Choose Files
          </Button>
        </div>

        {/* Selected files list */}
        <AnimatePresence mode="popLayout">
          {selectedFiles.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-2"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-text-muted">
                  {selectedFiles.length} file
                  {selectedFiles.length !== 1 ? "s" : ""} selected
                </p>
                {!isUploading && (
                  <button
                    onClick={clearAll}
                    className="text-xs text-text-muted hover:text-destructive transition-colors"
                  >
                    Clear all
                  </button>
                )}
              </div>

              <div className="space-y-1.5">
                {selectedFiles.map((file, i) => {
                  const error = failedFiles.find(
                    (e) => e.filename === file.name,
                  );
                  const isPdf = file.type === "application/pdf";
                  return (
                    <motion.div
                      key={fileKey(file)}
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 12 }}
                      transition={{ delay: i * 0.03 }}
                      className={`flex items-center gap-3 rounded-md border px-3 py-2.5 ${
                        error
                          ? "border-destructive/30 bg-destructive/5"
                          : "border-border bg-surface"
                      }`}
                    >
                      {isPdf ? (
                        <FileText size={18} className="shrink-0 text-accent" />
                      ) : (
                        <ImageIcon
                          size={18}
                          className="shrink-0 text-processing"
                        />
                      )}

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">
                          {file.name}
                        </p>
                        <p className="text-xs text-text-muted">
                          {formatFileSize(file.size)}
                        </p>
                      </div>

                      {error && (
                        <Badge variant="destructive" className="shrink-0">
                          {error.detail}
                        </Badge>
                      )}

                      {!isUploading && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            removeFile(i);
                          }}
                          className="shrink-0 rounded p-1 text-text-muted hover:bg-border/50 hover:text-destructive transition-colors"
                        >
                          <X size={14} />
                        </button>
                      )}
                    </motion.div>
                  );
                })}
              </div>

              {/* Progress bar */}
              {uploadProgress !== null && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-text-muted">
                    <span className="flex items-center gap-1.5">
                      <Loader2 size={12} className="animate-spin" />
                      Uploading\u2026
                    </span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
                    <motion.div
                      className="h-full rounded-full bg-accent"
                      initial={{ width: 0 }}
                      animate={{ width: `${uploadProgress}%` }}
                      transition={{ duration: 0.2, ease: "easeOut" }}
                    />
                  </div>
                </div>
              )}

              {/* Upload button */}
              {uploadProgress === null && (
                <Button
                  className="w-full"
                  onClick={handleBatchUpload}
                  disabled={isUploading || selectedFiles.length === 0}
                >
                  {isUploading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Uploading\u2026
                    </>
                  ) : (
                    <>
                      <FileUp size={16} />
                      Upload {selectedFiles.length} file
                      {selectedFiles.length !== 1 ? "s" : ""}
                    </>
                  )}
                </Button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Queue position note */}
        {batchSuccess && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-2.5 rounded-md border border-success/20 bg-success/5 px-3 py-2.5"
          >
            <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-success" />
            <p className="text-sm text-text-muted">
              Receipts are queued for processing — they&apos;ll be processed one
              at a time. Check the{" "}
              <button
                onClick={() => navigate("/receipts")}
                className="font-medium text-accent hover:underline"
              >
                receipts page
              </button>{" "}
              for progress.
            </p>
          </motion.div>
        )}

        {/* Failed files summary (when no files selected but errors remain) */}
        {failedFiles.length > 0 && selectedFiles.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-2.5 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2.5"
          >
            <AlertCircle
              size={16}
              className="mt-0.5 shrink-0 text-destructive"
            />
            <div className="text-sm">
              <p className="font-medium text-destructive">
                {failedFiles.length} file{failedFiles.length !== 1 ? "s" : ""}{" "}
                failed
              </p>
              {failedFiles.map((e) => (
                <p key={e.filename} className="text-text-muted">
                  {e.filename}: {e.detail}
                </p>
              ))}
            </div>
          </motion.div>
        )}
      </motion.div>

      {cameraOpen && (
        <CameraCapture
          onCapture={handleCameraCapture}
          onClose={() => setCameraOpen(false)}
        />
      )}
    </div>
  );
}
