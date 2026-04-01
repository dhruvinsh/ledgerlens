import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { motion } from "motion/react";
import { ArrowLeft, RotateCw, Trash2, Pencil, Check, X, AlertTriangle } from "lucide-react";
import { useReceipt, useDeleteReceipt, useReprocessReceipt } from "@/hooks/useReceipts";
import { useToastStore } from "@/stores/toastStore";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
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
  const [editingItem, setEditingItem] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Record<string, string>>({});

  if (isLoading) return <Spinner className="mt-20" />;
  if (!receipt) return <p className="p-6 text-text-muted">Receipt not found.</p>;

  const handleDelete = async () => {
    if (!confirm("Delete this receipt?")) return;
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

  const startEditItem = (li: LineItem) => {
    setEditingItem(li.id);
    setEditValues({
      name: li.name,
      quantity: String(li.quantity),
      total_price: li.total_price != null ? String(li.total_price / 100) : "",
    });
  };

  const saveEditItem = async () => {
    if (!editingItem) return;
    const toCents = (v: string) => (v ? Math.round(parseFloat(v) * 100) : null);
    await api.patch(`/line-items/${editingItem}`, {
      name: editValues.name,
      quantity: parseFloat(editValues.quantity) || 1,
      total_price: toCents(editValues.total_price),
    });
    setEditingItem(null);
    refetch();
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
              <div key={li.id} className="flex items-center gap-3 px-5 py-3">
                {editingItem === li.id ? (
                  <>
                    <input
                      className="flex-1 rounded-sm border border-border bg-surface px-2 py-1 text-sm"
                      value={editValues.name}
                      onChange={(e) => setEditValues({ ...editValues, name: e.target.value })}
                    />
                    <input
                      className="w-14 rounded-sm border border-border bg-surface px-2 py-1 text-right font-mono text-sm"
                      value={editValues.quantity}
                      onChange={(e) => setEditValues({ ...editValues, quantity: e.target.value })}
                    />
                    <input
                      className="w-20 rounded-sm border border-border bg-surface px-2 py-1 text-right font-mono text-sm"
                      value={editValues.total_price}
                      onChange={(e) => setEditValues({ ...editValues, total_price: e.target.value })}
                      placeholder="$"
                    />
                    <Button variant="ghost" size="icon" onClick={saveEditItem}>
                      <Check size={16} className="text-success" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setEditingItem(null)}>
                      <X size={16} className="text-text-muted" />
                    </Button>
                  </>
                ) : (
                  <>
                    <span className="flex-1 text-sm">{li.name}</span>
                    <span className="text-xs text-text-muted">x{li.quantity}</span>
                    <span className="w-20 text-right font-mono text-sm">
                      {formatMoney(li.total_price, receipt.currency)}
                    </span>
                    <Button variant="ghost" size="icon" onClick={() => startEditItem(li)}>
                      <Pencil size={14} className="text-text-muted" />
                    </Button>
                  </>
                )}
              </div>
            ))}
            {(!receipt.line_items || receipt.line_items.length === 0) && (
              <p className="px-5 py-6 text-center text-sm text-text-muted">No line items</p>
            )}
          </div>
        </Card>

        {/* Actions */}
        <div className="flex flex-wrap gap-3">
          {receipt.file_path && (
            <Button variant="outline" size="sm" onClick={handleReprocess} disabled={reprocess.isPending}>
              <RotateCw size={14} /> {reprocess.isPending ? "Reprocessing..." : "Reprocess"}
            </Button>
          )}
          <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleteReceipt.isPending}>
            <Trash2 size={14} /> Delete
          </Button>
        </div>

        {/* OCR info */}
        {receipt.raw_ocr_text && (
          <Card className="mt-6">
            <CardHeader>
              <h2 className="text-sm font-medium text-text-muted">
                Raw OCR Text
                {receipt.ocr_confidence != null && (
                  <span className="ml-2 font-mono text-xs">
                    ({(receipt.ocr_confidence * 100).toFixed(0)}% confidence)
                  </span>
                )}
              </h2>
            </CardHeader>
            <CardContent>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap font-mono text-xs text-text-muted">
                {receipt.raw_ocr_text}
              </pre>
            </CardContent>
          </Card>
        )}
      </motion.div>
    </div>
  );
}
