import { useState } from "react";
import { motion } from "motion/react";
import { Plus, Trash2, TestTube, CheckCircle, XCircle, Power, Pencil } from "lucide-react";
import { useModels, useCreateModel, useUpdateModel, useDeleteModel, useTestModel } from "@/hooks/useAdmin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import type { ModelConfig } from "@/lib/types";

const BLANK_FORM = { name: "", provider_type: "openai", base_url: "", model_name: "", api_key: "", supports_vision: false };

export default function AdminModels() {
  const { data: models, isLoading } = useModels();
  const createModel = useCreateModel();
  const updateModel = useUpdateModel();
  const deleteModel = useDeleteModel();
  const testModel = useTestModel();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(BLANK_FORM);

  const handleCreate = async () => {
    await createModel.mutateAsync(form);
    setShowForm(false);
    setForm(BLANK_FORM);
  };

  const handleEdit = (mc: ModelConfig) => {
    setEditingId(mc.id);
    setForm({ name: mc.name, provider_type: mc.provider_type, base_url: mc.base_url, model_name: mc.model_name, api_key: "", supports_vision: mc.supports_vision });
    setShowForm(true);
  };

  const handleSave = async () => {
    const payload: Record<string, unknown> = { ...form };
    if (!payload.api_key) delete payload.api_key;
    await updateModel.mutateAsync({ id: editingId!, ...payload });
    setEditingId(null);
    setShowForm(false);
    setForm(BLANK_FORM);
  };

  const handleCancel = () => {
    setEditingId(null);
    setShowForm(false);
    setForm(BLANK_FORM);
  };

  if (isLoading) return <Spinner className="mt-20" />;

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-2xl">LLM Models</h1>
        <Button size="sm" onClick={() => { setEditingId(null); setForm(BLANK_FORM); setShowForm(!showForm || !!editingId); }}>
          <Plus size={14} /> Add Model
        </Button>
      </div>

      {showForm && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          transition={{ duration: 0.2 }}
        >
          <Card>
            <CardContent className="grid gap-4 py-5 sm:grid-cols-2">
              <Input label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Ollama Local" />
              <Input label="Provider Type" value={form.provider_type} onChange={(e) => setForm({ ...form, provider_type: e.target.value })} placeholder="openai" />
              <Input label="Base URL" value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} placeholder="http://localhost:11434/v1" />
              <Input label="Model Name" value={form.model_name} onChange={(e) => setForm({ ...form, model_name: e.target.value })} placeholder="llama3.2" />
              <Input label="API Key" type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder={editingId ? "Leave blank to keep existing key" : "Optional"} />
              <label className="col-span-full flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.supports_vision}
                  onChange={(e) => setForm({ ...form, supports_vision: e.target.checked })}
                  className="accent-primary h-4 w-4"
                />
                Supports Vision — send receipt images directly to this model
              </label>
              <div className="flex items-end gap-2">
                {editingId ? (
                  <Button onClick={handleSave} disabled={updateModel.isPending || !form.name || !form.base_url}>
                    {updateModel.isPending ? "Saving..." : "Save Changes"}
                  </Button>
                ) : (
                  <Button onClick={handleCreate} disabled={createModel.isPending || !form.name || !form.base_url}>
                    {createModel.isPending ? "Creating..." : "Create"}
                  </Button>
                )}
                <Button variant="outline" onClick={handleCancel}>Cancel</Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {!models?.length ? (
        <p className="py-12 text-center text-text-muted">
          No model configurations yet. Add one to enable LLM-powered receipt extraction.
        </p>
      ) : (
        <div className="space-y-3">
          {models.map((mc, i) => (
            <motion.div
              key={mc.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.2 }}
            >
              <Card className={mc.is_active ? "ring-2 ring-primary" : "opacity-70"}>
                <CardContent className="flex items-center gap-4 py-4">
                  <button
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-colors ${mc.is_active ? "bg-primary text-primary-foreground hover:bg-primary/80" : "bg-muted text-text-muted hover:bg-muted/80"}`}
                    onClick={() => updateModel.mutate({ id: mc.id, is_active: !mc.is_active })}
                    title={mc.is_active ? "Deactivate this model" : "Activate this model"}
                  >
                    <Power size={16} />
                  </button>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{mc.name}</span>
                      {mc.is_active && <Badge variant="success">Active</Badge>}
                      {mc.supports_vision && <Badge variant="muted">Vision</Badge>}
                    </div>
                    <p className="mt-1 text-xs text-text-muted">
                      {mc.provider_type} &middot; {mc.model_name} &middot; {mc.base_url}
                    </p>
                    {mc.health_status && (
                      <div className="mt-1 flex items-center gap-1 text-xs">
                        {mc.health_status === "healthy" ? (
                          <CheckCircle size={12} className="text-success" />
                        ) : (
                          <XCircle size={12} className="text-destructive" />
                        )}
                        <span className="text-text-muted capitalize">{mc.health_status}</span>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => testModel.mutate(mc.id)}
                    >
                      <TestTube size={14} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(mc)}
                    >
                      <Pencil size={14} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteModel.mutate(mc.id)}
                    >
                      <Trash2 size={14} className="text-destructive" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
