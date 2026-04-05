import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router";
import { motion } from "motion/react";
import { ArrowLeft, Trash2, GitMerge, TrendingUp, MoreHorizontal, Upload, ImageOff, X, Plus, Receipt } from "lucide-react";
import { useItem, useItemReceipts, useUpdateItem, useDeleteItem, useUploadItemImage, useDeleteItemImage, useFetchItemImage, useMergeItem } from "@/hooks/useItems";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { MergeDialog } from "@/components/ui/merge-dialog";
import { useToastStore } from "@/stores/toastStore";
import { api } from "@/services/api";
import type { CanonicalItem, PaginatedResponse, ReceiptListItem } from "@/lib/types";

export default function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: item, isLoading, refetch } = useItem(id);
  const updateItem = useUpdateItem();
  const deleteItem = useDeleteItem();
  const uploadImage = useUploadItemImage();
  const deleteImage = useDeleteItemImage();
  const fetchImage = useFetchItemImage();
  const mergeItem = useMergeItem();
  const addToast = useToastStore((s) => s.addToast);

  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [productUrl, setProductUrl] = useState("");
  const [newAlias, setNewAlias] = useState("");
  const [dirty, setDirty] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [showMerge, setShowMerge] = useState(false);
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const moreMenuRef = useRef<HTMLDivElement>(null);
  const [receiptPageMap, setReceiptPageMap] = useState<Record<number, ReceiptListItem[]>>({});
  const [receiptPage, setReceiptPage] = useState(1);
  const [expanded, setExpanded] = useState(false);

  const { data: receiptData } = useItemReceipts(id, receiptPage, 10);

  useEffect(() => {
    if (receiptData?.items) {
      setReceiptPageMap((prev) => ({ ...prev, [receiptPage]: receiptData.items }));
    }
  }, [receiptData, receiptPage]);

  useEffect(() => {
    setReceiptPageMap({});
    setReceiptPage(1);
    setExpanded(false);
  }, [id]);

  const allReceipts = useMemo(() => {
    const pages = Object.keys(receiptPageMap)
      .map(Number)
      .sort((a, b) => a - b)
      .flatMap((k) => receiptPageMap[k]);
    if (receiptData?.items && receiptPage === 1) {
      return receiptData.items;
    }
    return pages;
  }, [receiptPageMap, receiptData, receiptPage]);

  const hasMore = receiptData ? allReceipts.length < receiptData.total : false;

  useEffect(() => {
    if (!showMoreMenu) return;
    const handler = (e: MouseEvent) => {
      if (moreMenuRef.current && !moreMenuRef.current.contains(e.target as Node)) {
        setShowMoreMenu(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showMoreMenu]);

  const searchItems = useCallback(async (query: string): Promise<CanonicalItem[]> => {
    const res = await api.get<PaginatedResponse<CanonicalItem>>("/items", {
      search: query,
      per_page: "10",
    });
    return res.items.filter((i) => i.id !== id);
  }, [id]);

  // Sync form state when item loads
  if (item && !dirty) {
    if (name !== item.name) { setName(item.name); }
    if (category !== (item.category ?? "")) { setCategory(item.category ?? ""); }
    if (productUrl !== (item.product_url ?? "")) { setProductUrl(item.product_url ?? ""); }
  }

  if (isLoading) return <Spinner className="mt-20" />;
  if (!item) return <p className="p-6 text-text-muted">Product not found.</p>;

  const handleSave = async () => {
    await updateItem.mutateAsync({
      id: item.id,
      name,
      category: category || null,
      product_url: productUrl || null,
    });
    setDirty(false);
    refetch();
  };

  const handleAddAlias = async () => {
    if (!newAlias.trim()) return;
    const aliases = [...(item.aliases ?? []), newAlias.trim()];
    await updateItem.mutateAsync({ id: item.id, aliases });
    setNewAlias("");
    refetch();
  };

  const handleRemoveAlias = async (alias: string) => {
    const aliases = (item.aliases ?? []).filter((a) => a !== alias);
    await updateItem.mutateAsync({ id: item.id, aliases });
    refetch();
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    await uploadImage.mutateAsync({ id: item.id, formData });
    refetch();
  };

  const handleDelete = async () => {
    await deleteItem.mutateAsync(item.id);
    navigate("/items");
  };

  const handleMerge = async (selectedId: string) => {
    try {
      await mergeItem.mutateAsync({ id: item.id, duplicate_ids: [selectedId] });
      addToast({ type: "success", title: "Product merged successfully" });
      setShowMerge(false);
      refetch();
    } catch (err) {
      addToast({
        type: "error",
        title: err instanceof Error ? err.message : "Failed to merge product",
      });
    }
  };

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
        <div className="mb-6 flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/items")}>
            <ArrowLeft size={18} />
          </Button>
          <h1 className="min-w-0 flex-1 truncate font-serif text-2xl" title={item.name}>
            {item.name}
          </h1>
          {/* More actions dropdown */}
          <div className="relative shrink-0" ref={moreMenuRef}>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setShowMoreMenu((v) => !v)}
              aria-label="More actions"
            >
              <MoreHorizontal size={16} />
            </Button>
                {showMoreMenu && (
                  <div className="absolute right-0 top-full z-20 mt-1.5 min-w-36 rounded-sm border border-border bg-surface py-1 shadow-lg">
                    {(item.receipt_count ?? 0) > 0 && (
                      <button
                        className="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-text hover:bg-accent/5"
                        onClick={() => { setShowMoreMenu(false); navigate(`/price-tracker?item=${item.id}`); }}
                      >
                        <TrendingUp size={14} className="text-text-muted" /> Prices
                      </button>
                    )}
                    <button
                      className="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-text hover:bg-accent/5"
                      onClick={() => { setShowMoreMenu(false); setShowMerge(true); }}
                    >
                      <GitMerge size={14} className="text-text-muted" /> Merge
                    </button>
                  </div>
                )}
          </div>
          <Button variant="destructive" size="sm" className="shrink-0" onClick={() => setShowDelete(true)}>
            <Trash2 size={14} /> Delete
          </Button>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Product image */}
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-6">
              {item.image_path ? (
                <img
                  src={`/files/${item.image_path}`}
                  alt={item.name}
                  className="h-40 w-40 rounded-sm object-cover"
                />
              ) : (
                <div className="flex h-40 w-40 items-center justify-center rounded-sm bg-accent/5">
                  <ImageOff size={40} className="text-text-muted" />
                </div>
              )}

              <div className="flex items-center gap-2 text-sm text-text-muted">
                <Receipt size={14} className="shrink-0" />
                <span>
                  {item.receipt_count ?? 0} receipt{(item.receipt_count ?? 0) !== 1 ? "s" : ""}
                </span>
              </div>

              <div className="flex gap-2">
                <label className="cursor-pointer">
                  <span className="inline-flex h-8 items-center gap-2 rounded-sm border border-border px-3 text-xs font-medium hover:bg-accent/5">
                    <Upload size={14} /> Upload
                  </span>
                  <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
                </label>
                {item.image_path && (
                  <Button variant="ghost" size="sm" onClick={() => { deleteImage.mutate(item.id); refetch(); }}>
                    Remove
                  </Button>
                )}
                <Button variant="outline" size="sm" onClick={() => { fetchImage.mutate(item.id); refetch(); }}>
                  Auto-fetch
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Edit form */}
          <Card className="lg:col-span-2">
            <CardHeader><h2 className="text-sm font-medium">Details</h2></CardHeader>
            <CardContent className="space-y-4">
              <Input label="Name" value={name} onChange={(e) => { setName(e.target.value); setDirty(true); }} />
              <Input label="Category" value={category} onChange={(e) => { setCategory(e.target.value); setDirty(true); }} placeholder="e.g. Dairy, Produce" />
              <Input label="Product URL" value={productUrl} onChange={(e) => { setProductUrl(e.target.value); setDirty(true); }} placeholder="https://..." />

              {dirty && (
                <Button size="sm" onClick={handleSave} disabled={updateItem.isPending}>
                  {updateItem.isPending ? "Saving..." : "Save Changes"}
                </Button>
              )}

              {/* Aliases */}
              <div>
                <p className="mb-2 text-sm font-medium">Aliases</p>
                <div className="flex flex-wrap gap-2">
                  {(item.aliases ?? []).map((alias) => (
                    <span
                      key={alias}
                      className="inline-flex items-center gap-1 rounded-sm bg-accent/10 px-2 py-1 text-xs"
                    >
                      {alias}
                      <button onClick={() => handleRemoveAlias(alias)}>
                        <X size={12} className="text-text-muted hover:text-destructive" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="mt-2 flex gap-2">
                  <input
                    className="flex-1 rounded-sm border border-border bg-surface px-2 py-1 text-sm"
                    placeholder="Add alias..."
                    value={newAlias}
                    onChange={(e) => setNewAlias(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddAlias()}
                  />
                  <Button variant="outline" size="sm" onClick={handleAddAlias}>
                    <Plus size={14} />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Receipts list */}
        {(item.receipt_count ?? 0) > 0 && (
          <Card className="mt-6">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium">Receipts</h2>
                <span className="text-xs text-text-muted">{item.receipt_count ?? 0}</span>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div
                className={`transition-[max-height] duration-300 overflow-hidden ${
                  expanded ? "max-h-[2000px]" : "max-h-[160px]"
                }`}
              >
                {allReceipts.length === 0 && receiptData?.items === undefined ? (
                  <div className="flex items-center justify-center py-6">
                    <Spinner className="text-text-muted" />
                  </div>
                ) : allReceipts.length === 0 ? (
                  <p className="py-4 text-center text-sm text-text-muted">No receipts found.</p>
                ) : (
                  <div className="divide-y divide-border">
                    {allReceipts.map((r) => (
                      <button
                        key={r.id}
                        className="flex w-full items-center justify-between gap-3 py-3 text-left hover:bg-accent/5 rounded-sm px-2 -mx-2 transition-colors"
                        onClick={() => navigate(`/receipts/${r.id}`)}
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">
                            {r.store?.name ?? "Unknown"}
                          </p>
                          <p className="text-xs text-text-muted">
                            {r.transaction_date
                              ? new Date(r.transaction_date).toLocaleDateString()
                              : "No date"}
                          </p>
                        </div>
                        <span className="shrink-0 text-xs text-text-muted">
                          {r.total != null ? `${(r.total / 100).toFixed(2)} ${r.currency}` : "—"}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {allReceipts.length > 0 && (
                <div className="mt-2 flex justify-center">
                  {!expanded && allReceipts.length > 4 ? (
                    <button
                      className="text-xs text-accent hover:underline"
                      onClick={() => setExpanded(true)}
                    >
                      Show more
                    </button>
                  ) : hasMore ? (
                    <button
                      className="text-xs text-accent hover:underline"
                      onClick={() => setReceiptPage((p) => p + 1)}
                    >
                      Load more
                    </button>
                  ) : (
                    <span className="text-xs text-text-muted">No more receipts</span>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </motion.div>

      <ConfirmDialog
        open={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={handleDelete}
        title="Delete Product"
        message="Are you sure you want to delete this product? This cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        loading={deleteItem.isPending}
      />

      <MergeDialog<CanonicalItem>
        open={showMerge}
        onClose={() => setShowMerge(false)}
        onConfirm={handleMerge}
        title="Merge Product"
        searchPlaceholder="Search for product to merge..."
        searchFn={searchItems}
        renderItem={(i) => (
          <div className="flex items-center gap-2">
            {i.image_path ? (
              <img src={`/files/${i.image_path}`} alt={i.name} className="h-6 w-6 rounded-sm object-cover" />
            ) : (
              <div className="h-6 w-6 rounded-sm bg-accent/10" />
            )}
            <span className="font-medium">{i.name}</span>
            {i.category && <span className="text-xs text-text-muted">{i.category}</span>}
          </div>
        )}
        getId={(i) => i.id}
        getName={(i) => i.name}
        currentName={item.name}
        loading={mergeItem.isPending}
      />
    </div>
  );
}
