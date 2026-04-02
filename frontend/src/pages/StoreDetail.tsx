import { useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Trash2,
  GitMerge,
  X,
  Plus,
  MapPin,
  ShieldCheck,
  ShieldOff,
  Receipt,
} from "lucide-react";
import {
  useStore,
  useUpdateStore,
  useDeleteStore,
  useMergeStore,
  useStoreAliases,
  useAddStoreAlias,
  useRemoveStoreAlias,
} from "@/hooks/useStores";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { MergeDialog } from "@/components/ui/merge-dialog";
import { useToastStore } from "@/stores/toastStore";
import { api } from "@/services/api";
import type { PaginatedResponse, Store } from "@/lib/types";

export default function StoreDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: store, isLoading, refetch } = useStore(id);
  const { data: aliases, refetch: refetchAliases } = useStoreAliases(id);
  const updateStore = useUpdateStore();
  const deleteStore = useDeleteStore();
  const addAlias = useAddStoreAlias();
  const removeAlias = useRemoveStoreAlias();
  const mergeStore = useMergeStore();
  const addToast = useToastStore((s) => s.addToast);

  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [chain, setChain] = useState("");
  const [newAlias, setNewAlias] = useState("");
  const [dirty, setDirty] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [showMerge, setShowMerge] = useState(false);

  // Sync form state when store loads
  if (store && !dirty) {
    if (name !== store.name) setName(store.name);
    if (address !== (store.address ?? "")) setAddress(store.address ?? "");
    if (chain !== (store.chain ?? "")) setChain(store.chain ?? "");
  }

  if (isLoading) return <Spinner className="mt-20" />;
  if (!store) return <p className="p-6 text-text-muted">Store not found.</p>;

  const handleSave = async () => {
    await updateStore.mutateAsync({
      id: store.id,
      name,
      address,
      chain,
    });
    setDirty(false);
    refetch();
  };

  const handleToggleVerified = async () => {
    await updateStore.mutateAsync({
      id: store.id,
      is_verified: !store.is_verified,
    });
    refetch();
  };

  const handleAddAlias = async () => {
    if (!newAlias.trim()) return;
    await addAlias.mutateAsync({ storeId: store.id, alias_name: newAlias.trim() });
    setNewAlias("");
    refetchAliases();
    refetch();
  };

  const handleRemoveAlias = async (aliasId: string) => {
    await removeAlias.mutateAsync({ storeId: store.id, aliasId });
    refetchAliases();
    refetch();
  };

  const handleMerge = async (selectedId: string) => {
    try {
      await mergeStore.mutateAsync({ id: store.id, duplicate_ids: [selectedId] });
      addToast({ type: "success", title: "Store merged successfully" });
      setShowMerge(false);
      refetch();
      refetchAliases();
    } catch (err) {
      addToast({
        type: "error",
        title: err instanceof Error ? err.message : "Failed to merge store",
      });
    }
  };

  const searchStores = useCallback(async (query: string): Promise<Store[]> => {
    const res = await api.get<PaginatedResponse<Store>>("/stores", {
      search: query,
      per_page: "10",
    });
    return res.items.filter((s) => s.id !== store.id);
  }, [store.id]);

  const handleDelete = async () => {
    try {
      setDeleteError("");
      await deleteStore.mutateAsync(store.id);
      navigate("/stores");
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Failed to delete store");
    }
  };

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
        <div className="mb-6 flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/stores")}>
            <ArrowLeft size={18} />
          </Button>
          <h1 className="flex-1 font-serif text-2xl">{store.name}</h1>
          <Button variant="outline" size="sm" onClick={() => setShowMerge(true)}>
            <GitMerge size={14} /> Merge
          </Button>
          <Button variant="destructive" size="sm" onClick={() => setShowDelete(true)}>
            <Trash2 size={14} /> Delete
          </Button>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Store info summary */}
          <Card>
            <CardContent className="space-y-4 py-6">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Verified</span>
                <button
                  onClick={handleToggleVerified}
                  className="flex items-center gap-1.5 rounded-sm px-2 py-1 text-xs transition-colors hover:bg-accent/5"
                >
                  {store.is_verified ? (
                    <>
                      <ShieldCheck size={14} className="text-success" />
                      <Badge variant="success">Verified</Badge>
                    </>
                  ) : (
                    <>
                      <ShieldOff size={14} className="text-text-muted" />
                      <Badge variant="muted">Unverified</Badge>
                    </>
                  )}
                </button>
              </div>

              {store.address && (
                <div className="flex items-start gap-2 text-sm text-text-muted">
                  <MapPin size={14} className="mt-0.5 shrink-0" />
                  <span>{store.address}</span>
                </div>
              )}

              <div className="flex items-center gap-2 text-sm text-text-muted">
                <Receipt size={14} className="shrink-0" />
                <span>
                  {store.receipt_count} receipt{store.receipt_count !== 1 ? "s" : ""}
                </span>
              </div>

              {store.chain && (
                <div className="text-sm">
                  <span className="text-text-muted">Chain:</span>{" "}
                  <Badge>{store.chain}</Badge>
                </div>
              )}

              {store.merged_into_id && (
                <Badge variant="warning">Merged into another store</Badge>
              )}
            </CardContent>
          </Card>

          {/* Edit form */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <h2 className="text-sm font-medium">Details</h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                label="Name"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setDirty(true);
                }}
              />
              <Input
                label="Address"
                value={address}
                onChange={(e) => {
                  setAddress(e.target.value);
                  setDirty(true);
                }}
                placeholder="123 Main St, City, Province"
              />
              <Input
                label="Chain"
                value={chain}
                onChange={(e) => {
                  setChain(e.target.value);
                  setDirty(true);
                }}
                placeholder="e.g. Walmart, Costco"
              />

              {dirty && (
                <Button size="sm" onClick={handleSave} disabled={updateStore.isPending}>
                  {updateStore.isPending ? "Saving..." : "Save Changes"}
                </Button>
              )}

              {/* Aliases */}
              <div>
                <p className="mb-2 text-sm font-medium">
                  Aliases
                  <span className="ml-1.5 text-text-muted font-normal">
                    (OCR name variations that map to this store)
                  </span>
                </p>
                <div className="flex flex-wrap gap-2">
                  {(aliases ?? []).map((alias) => (
                    <span
                      key={alias.id}
                      className="inline-flex items-center gap-1 rounded-sm bg-accent/10 px-2 py-1 text-xs"
                    >
                      <span>{alias.alias_name}</span>
                      <span className="text-text-muted">({alias.source})</span>
                      <button onClick={() => handleRemoveAlias(alias.id)}>
                        <X size={12} className="text-text-muted hover:text-destructive" />
                      </button>
                    </span>
                  ))}
                  {(!aliases || aliases.length === 0) && (
                    <span className="text-xs text-text-muted">No aliases yet</span>
                  )}
                </div>
                <div className="mt-2 flex gap-2">
                  <input
                    className="flex-1 rounded-sm border border-border bg-surface px-2 py-1 text-sm"
                    placeholder="Add alias..."
                    value={newAlias}
                    onChange={(e) => setNewAlias(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddAlias()}
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleAddAlias}
                    disabled={addAlias.isPending}
                  >
                    <Plus size={14} />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </motion.div>

      <ConfirmDialog
        open={showDelete}
        onClose={() => {
          setShowDelete(false);
          setDeleteError("");
        }}
        onConfirm={handleDelete}
        title="Delete Store"
        message={
          deleteError ||
          (store.receipt_count > 0
            ? `This store has ${store.receipt_count} receipt(s). You must reassign or merge them before deleting.`
            : "Are you sure you want to delete this store? This cannot be undone.")
        }
        confirmLabel={store.receipt_count > 0 ? "Cannot Delete" : "Delete"}
        variant="destructive"
        loading={deleteStore.isPending}
      />

      <MergeDialog<Store>
        open={showMerge}
        onClose={() => setShowMerge(false)}
        onConfirm={handleMerge}
        title="Merge Store"
        searchPlaceholder="Search for store to merge..."
        searchFn={searchStores}
        renderItem={(s) => (
          <div>
            <span className="font-medium">{s.name}</span>
            {s.address && (
              <span className="ml-2 text-xs text-text-muted">{s.address}</span>
            )}
            <span className="ml-2 text-xs text-text-muted">
              ({s.receipt_count} receipts)
            </span>
          </div>
        )}
        getId={(s) => s.id}
        getName={(s) => s.name}
        currentName={store.name}
        loading={mergeStore.isPending}
      />
    </div>
  );
}
