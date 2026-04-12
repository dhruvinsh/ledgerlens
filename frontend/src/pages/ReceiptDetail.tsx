import { useState, useRef, useEffect } from "react";
import { useNavigate, useParams } from "react-router";
import { motion } from "motion/react";
import { ArrowLeft, RotateCw, Trash2, AlertTriangle, Download, ChevronDown, FileDown, FileJson } from "lucide-react";
import { useReceipt, useDeleteReceipt, useReprocessReceipt } from "@/hooks/useReceipts";
import { useToastStore } from "@/stores/toastStore";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { EnrichedLineItem } from "@/components/receipt/EnrichedLineItem";
import { EditLineItemDialog } from "@/components/receipt/EditLineItemDialog";
import { formatMoney } from "@/lib/money";
import { api } from "@/services/api";
import type { LineItem } from "@/lib/types";

export default function ReceiptDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: receipt, isLoading, refetch } = useReceipt(id);
  const deleteReceipt = useDeleteReceipt();
  const reprocess = useReprocessReceipt();
  const addToast = useToastStore((s) => s.addToast);
  const [editingItem, setEditingItem] = useState<LineItem | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const downloadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!downloadOpen) return;
    function handleOutside(e: MouseEvent) {
      if (downloadRef.current && !downloadRef.current.contains(e.target as Node)) {
        setDownloadOpen(false);
      }
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, [downloadOpen]);

  if (isLoading) return <Spinner className="mt-20" />;
  if (!receipt) return <p className="p-6 text-text-muted">Receipt not found.</p>;

  const handleDelete = async () => {
    await deleteReceipt.mutateAsync(receipt.id);
    navigate("/receipts");
  };

  const handleReprocess = async () => {
    try {
      await reprocess.mutateAsync(receipt.id);
      addToast({
        type: "info",
        title: "Reprocessing started",
        message: "You'll be notified when processing completes",
      });
      refetch();
    } catch {
      addToast({
        type: "error",
        title: "Reprocess failed",
        message: "Could not start reprocessing",
      });
    }
  };

  const handleSaveItem = async (values: {
    name: string;
    quantity: number;
    total_price: number | null;
  }) => {
    if (!editingItem) return;
    await api.patch(`/line-items/${editingItem.id}`, values);
    setEditingItem(null);
    refetch();
  };

  const handleDownloadOriginal = () => {
    if (!receipt.file_path) return;
    const ext = receipt.file_path.split(".").pop() ?? "file";
    const storeName = receipt.store?.name ?? "receipt";
    const date = receipt.transaction_date ?? receipt.created_at.slice(0, 10);
    const filename = `${storeName}-${date}.${ext}`.toLowerCase().replace(/\s+/g, "-");
    const a = document.createElement("a");
    a.href = `/files/${receipt.file_path}`;
    a.download = filename;
    a.click();
    setDownloadOpen(false);
  };

  const handleDownloadJson = () => {
    const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const storeName = receipt.store?.name ?? "receipt";
    const date = receipt.transaction_date ?? receipt.created_at.slice(0, 10);
    const filename = `${storeName}-${date}.json`.toLowerCase().replace(/\s+/g, "-");
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setDownloadOpen(false);
  };

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
        {/* Header */}
        <div className="mb-6 flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/receipts")}>
            <ArrowLeft size={18} />
          </Button>
          <div className="flex-1">
            <h1 className="font-serif text-2xl">
              {receipt.store?.name ?? "Receipt"}
            </h1>
            <p className="text-sm text-text-muted">
              {receipt.transaction_date ?? "No date"} &middot; {receipt.source}
            </p>
          </div>
          <StatusBadge status={receipt.status} />
        </div>

        {/* Heuristic fallback warning */}
        {receipt.extraction_source === "heuristic" && receipt.source !== "manual" && (
          <div className="mb-4 flex items-start gap-3 rounded-sm border border-warning/30 bg-warning/5 px-4 py-3">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-warning" />
            <div>
              <p className="text-sm font-medium">Extracted using basic patterns</p>
              <p className="mt-0.5 text-xs text-text-muted">
                The LLM model was unavailable — data was extracted with heuristic rules and may be incomplete.
                Try reprocessing once the model is running.
              </p>
            </div>
          </div>
        )}

        {/* Totals */}
        <Card className="mb-6">
          <CardContent className="grid grid-cols-3 gap-4 py-4 text-center">
            <div>
              <p className="text-xs text-text-muted">Subtotal</p>
              <p className="font-mono font-semibold">{formatMoney(receipt.subtotal, receipt.currency)}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Tax</p>
              <p className="font-mono font-semibold">{formatMoney(receipt.tax, receipt.currency)}</p>
            </div>
            <div>
              <p className="text-xs text-text-muted">Total</p>
              <p className="font-mono text-lg font-bold text-accent">{formatMoney(receipt.total, receipt.currency)}</p>
            </div>
          </CardContent>
        </Card>

        {/* Line Items */}
        <Card className="mb-6">
          <CardHeader>
            <h2 className="text-sm font-medium text-text-muted">
              Line Items ({receipt.line_items?.length ?? 0})
            </h2>
          </CardHeader>
          <div className="divide-y divide-border">
            {(receipt.line_items ?? []).map((li) => (
              <EnrichedLineItem
                key={li.id}
                item={li}
                currency={receipt.currency}
                onEdit={setEditingItem}
              />
            ))}
            {(!receipt.line_items || receipt.line_items.length === 0) && (
              <p className="px-5 py-6 text-center text-sm text-text-muted">No line items</p>
            )}
          </div>
        </Card>

        {/* Actions */}
        <div className="flex flex-wrap gap-3">
          {/* Download dropdown */}
          <div className="relative" ref={downloadRef}>
            <Button variant="outline" size="sm" onClick={() => setDownloadOpen((o) => !o)}>
              <Download size={14} /> Download <ChevronDown size={12} className={`transition-transform duration-150 ${downloadOpen ? "rotate-180" : ""}`} />
            </Button>
            {downloadOpen && (
              <div className="absolute left-0 top-full z-20 mt-1 min-w-[188px] rounded-sm border border-border bg-surface shadow-lg">
                {receipt.file_path ? (
                  <button
                    className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-xs hover:bg-accent/5"
                    onClick={handleDownloadOriginal}
                  >
                    <FileDown size={13} className="shrink-0 text-text-muted" />
                    <span>
                      <span className="block font-medium">Original file</span>
                      <span className="text-text-muted">.{receipt.file_path.split(".").pop()?.toUpperCase()}</span>
                    </span>
                  </button>
                ) : (
                  <div className="flex items-center gap-2.5 px-3 py-2.5 text-xs text-text-muted opacity-50 cursor-not-allowed">
                    <FileDown size={13} className="shrink-0" />
                    <span>
                      <span className="block font-medium">Original file</span>
                      <span>No file attached</span>
                    </span>
                  </div>
                )}
                <div className="mx-3 border-t border-border" />
                <button
                  className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-xs hover:bg-accent/5"
                  onClick={handleDownloadJson}
                >
                  <FileJson size={13} className="shrink-0 text-text-muted" />
                  <span>
                    <span className="block font-medium">JSON data</span>
                    <span className="text-text-muted">All fields + line items</span>
                  </span>
                </button>
              </div>
            )}
          </div>

          {receipt.file_path && (
            <Button variant="outline" size="sm" onClick={handleReprocess} disabled={reprocess.isPending}>
              <RotateCw size={14} /> {reprocess.isPending ? "Reprocessing..." : "Reprocess"}
            </Button>
          )}
          <Button variant="destructive" size="sm" onClick={() => setDeleteOpen(true)} disabled={deleteReceipt.isPending}>
            <Trash2 size={14} /> Delete
          </Button>
        </div>

        {/* Extraction input */}
        {receipt.source !== "manual" && (receipt.raw_ocr_text || receipt.extraction_source === "vision") && (
          <Card className="mt-6">
            {receipt.extraction_source === "vision" ? (
              <>
                <CardHeader>
                  <h2 className="text-sm font-medium text-text-muted">
                    Extraction Input
                    <span className="ml-2 text-xs text-text-muted">&middot; vision</span>
                  </h2>
                </CardHeader>
                <CardContent>
                  {receipt.raw_ocr_text ? (
                    <pre className="max-h-48 overflow-auto whitespace-pre-wrap font-mono text-xs text-text-muted">
                      {receipt.raw_ocr_text}
                    </pre>
                  ) : (
                    <p className="text-xs text-text-muted italic">
                      Receipt image sent directly to the vision model — text not returned.
                    </p>
                  )}
                </CardContent>
              </>
            ) : (
              <>
                <CardHeader>
                  <h2 className="text-sm font-medium text-text-muted">
                    Extraction Input
                    {receipt.ocr_confidence != null && (
                      <span className="ml-2 font-mono text-xs">
                        ({(receipt.ocr_confidence * 100).toFixed(0)}% OCR confidence)
                      </span>
                    )}
                    {receipt.extraction_source && (
                      <span className="ml-2 text-xs text-text-muted">
                        &middot; {receipt.extraction_source === "llm" ? "LLM" : "heuristic"}
                      </span>
                    )}
                  </h2>
                </CardHeader>
                <CardContent>
                  <pre className="max-h-48 overflow-auto whitespace-pre-wrap font-mono text-xs text-text-muted">
                    {receipt.raw_ocr_text}
                  </pre>
                </CardContent>
              </>
            )}
          </Card>
        )}
      </motion.div>

      {/* Delete confirmation */}
      <ConfirmDialog
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onConfirm={handleDelete}
        title="Delete Receipt"
        message="This will permanently delete the receipt and all its line items. This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        loading={deleteReceipt.isPending}
      />

      {/* Edit dialog */}
      <EditLineItemDialog
        item={editingItem}
        onSave={handleSaveItem}
        onClose={() => setEditingItem(null)}
      />
    </div>
  );
}
