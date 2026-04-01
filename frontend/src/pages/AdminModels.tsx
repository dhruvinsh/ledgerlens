import { useState } from "react";
import { motion } from "motion/react";
import { Plus, Trash2, TestTube, CheckCircle, XCircle, Power } from "lucide-react";
import { useModels, useCreateModel, useUpdateModel, useDeleteModel, useTestModel } from "@/hooks/useAdmin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

export default function AdminModels() {
  const { data: models, isLoading } = useModels();
  const createModel = useCreateModel();
  const updateModel = useUpdateModel();
  const deleteModel = useDeleteModel();
  const testModel = useTestModel();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    provider_type: "openai",
    base_url: "",
    model_name: "",
    api_key: "",
  });

  const handleCreate = async () => {
    await createModel.mutateAsync(form);
    setShowForm(false);
    setForm({ name: "", provider_type: "openai", base_url: "", model_name: "", api_key: "" });
  };

  if (isLoading) return <Spinner className="mt-20" />;

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-2xl">LLM Models</h1>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
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
              <Input label="API Key" type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder="Optional" />
              <div className="flex items-end gap-2">
                <Button onClick={handleCreate} disabled={createModel.isPending || !form.name || !form.base_url}>
                  {createModel.isPending ? "Creating..." : "Create"}
                </Button>
                <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
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
