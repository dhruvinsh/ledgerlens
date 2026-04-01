import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { motion } from "motion/react";
import { ArrowLeft, Trash2, Upload, ImageOff, X, Plus } from "lucide-react";
import { useItem, useUpdateItem, useDeleteItem, useUploadItemImage, useDeleteItemImage, useFetchItemImage } from "@/hooks/useItems";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

export default function ProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: item, isLoading, refetch } = useItem(id);
  const updateItem = useUpdateItem();
  const deleteItem = useDeleteItem();
  const uploadImage = useUploadItemImage();
  const deleteImage = useDeleteItemImage();
  const fetchImage = useFetchItemImage();

  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [productUrl, setProductUrl] = useState("");
  const [newAlias, setNewAlias] = useState("");
  const [dirty, setDirty] = useState(false);

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

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
        <div className="mb-6 flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/items")}>
            <ArrowLeft size={18} />
          </Button>
          <h1 className="flex-1 font-serif text-2xl">{item.name}</h1>
          <Button
            variant="destructive"
            size="sm"
            onClick={async () => {
              if (!confirm("Delete this product?")) return;
              await deleteItem.mutateAsync(item.id);
              navigate("/items");
            }}
          >
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
      </motion.div>
    </div>
  );
}
