import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Check,
  X,
  ArrowRight,
  Package,
  Store as StoreIcon,
  ScanSearch,
  CheckCheck,
  CircleCheck,
  MapPin,
  Receipt,
  Square,
  CheckSquare,
} from "lucide-react";
import {
  useSuggestions,
  useAcceptSuggestion,
  useRejectSuggestion,
} from "@/hooks/useMatchSuggestions";
import {
  useStoreMergeSuggestions,
  useAcceptStoreMerge,
  useRejectStoreMerge,
  useScanDuplicates,
} from "@/hooks/useReview";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useToastStore } from "@/stores/toastStore";
import type { MatchSuggestion, StoreMergeSuggestion } from "@/lib/types";

type Tab = "products" | "stores";

function confidenceVariant(score: number) {
  if (score >= 85) return "success";
  if (score >= 65) return "warning";
  return "destructive";
}

// ── Product Match Card ──

function ProductMatchCard({
  suggestion,
  selected,
  onToggle,
  onAccept,
  onReject,
  isPending,
}: {
  suggestion: MatchSuggestion;
  selected: boolean;
  onToggle: () => void;
  onAccept: () => void;
  onReject: () => void;
  isPending: boolean;
}) {
  const ci = suggestion.canonical_item;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -100 }}
      transition={{ duration: 0.2 }}
    >
      <Card className={selected ? "ring-2 ring-accent/40" : ""}>
        <CardContent className="py-4">
          <div className="mb-3 flex items-center gap-3">
            <button onClick={onToggle} className="text-text-muted hover:text-accent transition-colors">
              {selected ? <CheckSquare size={18} className="text-accent" /> : <Square size={18} />}
            </button>
            <Badge variant={confidenceVariant(suggestion.confidence)}>
              {Math.round(suggestion.confidence)}% match
            </Badge>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            {/* Line item (left) */}
            <div className="flex-1 space-y-1 rounded-sm border border-border p-3">
              <p className="text-xs font-medium text-text-muted">Line Item</p>
              <p className="font-medium">{suggestion.line_item_name ?? "Unknown"}</p>
              {suggestion.line_item_raw_name &&
                suggestion.line_item_raw_name !== suggestion.line_item_name && (
                  <p className="text-xs text-text-muted">
                    OCR: {suggestion.line_item_raw_name}
                  </p>
                )}
            </div>

            <ArrowRight size={16} className="hidden shrink-0 text-text-muted sm:block" />

            {/* Canonical item (right) */}
            <div className="flex flex-1 items-center gap-3 rounded-sm border border-accent/20 bg-accent/5 p-3">
              {ci?.image_path ? (
                <img
                  src={`/files/${ci.image_path}`}
                  alt={ci.name}
                  className="h-10 w-10 rounded-sm object-cover"
                />
              ) : (
                <div className="flex h-10 w-10 items-center justify-center rounded-sm bg-accent/10">
                  <Package size={16} className="text-accent" />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="font-medium">{ci?.name}</p>
                {ci?.category && (
                  <p className="text-xs text-text-muted">{ci.category}</p>
                )}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-3 flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onReject}
              disabled={isPending}
            >
              <X size={14} /> Not a match
            </Button>
            <Button size="sm" onClick={onAccept} disabled={isPending}>
              <Check size={14} /> Link
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ── Store Merge Card ──

function StoreMergeCard({
  suggestion,
  selected,
  onToggle,
  onAccept,
  onReject,
  isPending,
}: {
  suggestion: StoreMergeSuggestion;
  selected: boolean;
  onToggle: () => void;
  onAccept: () => void;
  onReject: () => void;
  isPending: boolean;
}) {
  const { store_a, store_b } = suggestion;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -100 }}
      transition={{ duration: 0.2 }}
    >
      <Card className={selected ? "ring-2 ring-accent/40" : ""}>
        <CardContent className="py-4">
          <div className="mb-3 flex items-center gap-3">
            <button onClick={onToggle} className="text-text-muted hover:text-accent transition-colors">
              {selected ? <CheckSquare size={18} className="text-accent" /> : <Square size={18} />}
            </button>
            <Badge variant={confidenceVariant(suggestion.confidence)}>
              {Math.round(suggestion.confidence)}% match
            </Badge>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            {/* Store A — keep */}
            <div className="flex-1 space-y-1.5 rounded-sm border border-accent/20 bg-accent/5 p-3">
              <p className="text-xs font-medium text-accent">Keep</p>
              <div className="flex items-center gap-2">
                <StoreIcon size={14} className="text-accent" />
                <span className="font-medium">{store_a.name}</span>
              </div>
              {store_a.address && (
                <div className="flex items-start gap-1.5 text-xs text-text-muted">
                  <MapPin size={11} className="mt-0.5 shrink-0" />
                  {store_a.address}
                </div>
              )}
              <div className="flex items-center gap-3 text-xs text-text-muted">
                <span className="flex items-center gap-1">
                  <Receipt size={11} /> {store_a.receipt_count}
                </span>
                {store_a.aliases.length > 0 && (
                  <span>{store_a.aliases.length} alias(es)</span>
                )}
              </div>
            </div>

            <div className="flex items-center justify-center">
              <ArrowRight size={16} className="hidden rotate-180 text-text-muted sm:block" />
            </div>

            {/* Store B — merge into A */}
            <div className="flex-1 space-y-1.5 rounded-sm border border-border p-3">
              <p className="text-xs font-medium text-text-muted">Absorb into Keep</p>
              <div className="flex items-center gap-2">
                <StoreIcon size={14} className="text-text-muted" />
                <span className="font-medium">{store_b.name}</span>
              </div>
              {store_b.address && (
                <div className="flex items-start gap-1.5 text-xs text-text-muted">
                  <MapPin size={11} className="mt-0.5 shrink-0" />
                  {store_b.address}
                </div>
              )}
              <div className="flex items-center gap-3 text-xs text-text-muted">
                <span className="flex items-center gap-1">
                  <Receipt size={11} /> {store_b.receipt_count}
                </span>
                {store_b.aliases.length > 0 && (
                  <span>{store_b.aliases.length} alias(es)</span>
                )}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-3 flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onReject}
              disabled={isPending}
            >
              <X size={14} /> Skip
            </Button>
            <Button size="sm" onClick={onAccept} disabled={isPending}>
              <Check size={14} /> Merge
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ── Main Review Page ──

export default function Review() {
  const [tab, setTab] = useState<Tab>("products");
  const [productPage, setProductPage] = useState(1);
  const [storePage, setStorePage] = useState(1);
  const [showBatchConfirm, setShowBatchConfirm] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const addToast = useToastStore((s) => s.addToast);

  // Product matches
  const { data: productData, isLoading: productsLoading } = useSuggestions(
    productPage,
    20,
  );
  const acceptSuggestion = useAcceptSuggestion();
  const rejectSuggestion = useRejectSuggestion();

  // Store merges
  const { data: storeData, isLoading: storesLoading } =
    useStoreMergeSuggestions(storePage, 20);
  const acceptStoreMerge = useAcceptStoreMerge();
  const rejectStoreMerge = useRejectStoreMerge();
  const scanDuplicates = useScanDuplicates();

  const productCount = productData?.total ?? 0;
  const storeCount = storeData?.total ?? 0;
  const currentItems =
    tab === "products" ? productData?.items : storeData?.items;
  const isLoading = tab === "products" ? productsLoading : storesLoading;

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (!currentItems?.length) return;
    const ids = currentItems.map((i) => i.id);
    const allSelected = ids.every((id) => selected.has(id));
    if (allSelected) {
      setSelected((prev) => {
        const next = new Set(prev);
        ids.forEach((id) => next.delete(id));
        return next;
      });
    } else {
      setSelected((prev) => new Set([...prev, ...ids]));
    }
  };

  const selectedCount = currentItems?.filter((i) => selected.has(i.id)).length ?? 0;

  const handleAcceptProduct = async (id: string) => {
    try {
      await acceptSuggestion.mutateAsync(id);
      setSelected((prev) => { const n = new Set(prev); n.delete(id); return n; });
      addToast({ type: "success", title: "Product linked" });
    } catch {
      addToast({ type: "error", title: "Failed to link product" });
    }
  };

  const handleRejectProduct = async (id: string) => {
    try {
      await rejectSuggestion.mutateAsync(id);
      setSelected((prev) => { const n = new Set(prev); n.delete(id); return n; });
    } catch {
      addToast({ type: "error", title: "Failed to reject suggestion" });
    }
  };

  const handleAcceptStore = async (id: string) => {
    try {
      await acceptStoreMerge.mutateAsync(id);
      setSelected((prev) => { const n = new Set(prev); n.delete(id); return n; });
      addToast({ type: "success", title: "Stores merged" });
    } catch {
      addToast({ type: "error", title: "Failed to merge stores" });
    }
  };

  const handleRejectStore = async (id: string) => {
    try {
      await rejectStoreMerge.mutateAsync(id);
      setSelected((prev) => { const n = new Set(prev); n.delete(id); return n; });
    } catch {
      addToast({ type: "error", title: "Failed to reject suggestion" });
    }
  };

  const handleBatchAccept = async () => {
    setShowBatchConfirm(false);
    const ids =
      selectedCount > 0
        ? currentItems!.filter((i) => selected.has(i.id)).map((i) => i.id)
        : currentItems!.map((i) => i.id);

    let accepted = 0;
    for (const id of ids) {
      try {
        if (tab === "products") {
          await acceptSuggestion.mutateAsync(id);
        } else {
          await acceptStoreMerge.mutateAsync(id);
        }
        accepted++;
      } catch {
        break;
      }
    }
    setSelected(new Set());
    addToast({
      type: "success",
      title: `Accepted ${accepted} of ${ids.length}`,
    });
  };

  const handleScan = async () => {
    try {
      const result = await scanDuplicates.mutateAsync();
      addToast({
        type: "info",
        title: `Scan complete: ${(result as { new_suggestions: number }).new_suggestions} new suggestion(s)`,
      });
    } catch {
      addToast({ type: "error", title: "Scan failed" });
    }
  };

  const batchLabel =
    selectedCount > 0
      ? `Accept ${selectedCount} Selected`
      : "Accept All";

  const batchCount = selectedCount > 0 ? selectedCount : (currentItems?.length ?? 0);

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Review</h1>

      {/* Tabs */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => { setTab("products"); setSelected(new Set()); }}
          className={`flex items-center gap-2 rounded-sm px-3 py-1.5 text-sm font-medium transition-colors ${
            tab === "products"
              ? "bg-accent/10 text-accent"
              : "text-text-muted hover:text-text"
          }`}
        >
          <Package size={14} />
          Product Matches
          {productCount > 0 && (
            <Badge variant="default">{productCount}</Badge>
          )}
        </button>
        <button
          onClick={() => { setTab("stores"); setSelected(new Set()); }}
          className={`flex items-center gap-2 rounded-sm px-3 py-1.5 text-sm font-medium transition-colors ${
            tab === "stores"
              ? "bg-accent/10 text-accent"
              : "text-text-muted hover:text-text"
          }`}
        >
          <StoreIcon size={14} />
          Store Duplicates
          {storeCount > 0 && <Badge variant="default">{storeCount}</Badge>}
        </button>

        <div className="ml-auto flex gap-2">
          {tab === "stores" && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleScan}
              disabled={scanDuplicates.isPending}
            >
              <ScanSearch size={14} />
              {scanDuplicates.isPending ? "Scanning..." : "Scan"}
            </Button>
          )}
          {(currentItems?.length ?? 0) > 1 && (
            <>
              <Button variant="outline" size="sm" onClick={toggleSelectAll}>
                {currentItems?.every((i) => selected.has(i.id))
                  ? <><CheckSquare size={14} /> Deselect All</>
                  : <><Square size={14} /> Select All</>}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowBatchConfirm(true)}
              >
                <CheckCheck size={14} /> {batchLabel}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <Spinner className="mt-12" />
      ) : !currentItems?.length ? (
        <div className="flex flex-col items-center gap-3 py-20 text-text-muted">
          <CircleCheck size={40} strokeWidth={1.5} />
          <p className="text-sm">All caught up — no pending reviews.</p>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            <AnimatePresence mode="popLayout">
              {tab === "products" &&
                (productData?.items ?? []).map((s) => (
                  <ProductMatchCard
                    key={s.id}
                    suggestion={s}
                    selected={selected.has(s.id)}
                    onToggle={() => toggleSelect(s.id)}
                    onAccept={() => handleAcceptProduct(s.id)}
                    onReject={() => handleRejectProduct(s.id)}
                    isPending={
                      acceptSuggestion.isPending || rejectSuggestion.isPending
                    }
                  />
                ))}
              {tab === "stores" &&
                (storeData?.items ?? []).map((s) => (
                  <StoreMergeCard
                    key={s.id}
                    suggestion={s}
                    selected={selected.has(s.id)}
                    onToggle={() => toggleSelect(s.id)}
                    onAccept={() => handleAcceptStore(s.id)}
                    onReject={() => handleRejectStore(s.id)}
                    isPending={
                      acceptStoreMerge.isPending || rejectStoreMerge.isPending
                    }
                  />
                ))}
            </AnimatePresence>
          </div>
          <Pagination
            page={tab === "products" ? productPage : storePage}
            totalPages={Math.ceil(
              ((tab === "products" ? productCount : storeCount) || 1) / 20,
            )}
            onPageChange={tab === "products" ? setProductPage : setStorePage}
          />
        </>
      )}

      <ConfirmDialog
        open={showBatchConfirm}
        onClose={() => setShowBatchConfirm(false)}
        onConfirm={handleBatchAccept}
        title={selectedCount > 0 ? "Accept Selected" : "Accept All on This Page"}
        message={`Accept ${batchCount} ${tab === "products" ? "product match(es)" : "store merge(s)"}?`}
        confirmLabel={batchLabel}
      />
    </div>
  );
}
