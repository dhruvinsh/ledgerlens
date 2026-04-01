import { useState } from "react";
import { useNavigate } from "react-router";
import { motion } from "motion/react";
import { Plus, Trash2 } from "lucide-react";
import { useManualReceipt } from "@/hooks/useReceipts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";

interface LineItemDraft {
  name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
}

export default function ManualEntry() {
  const navigate = useNavigate();
  const create = useManualReceipt();
  const [storeName, setStoreName] = useState("");
  const [date, setDate] = useState("");
  const [subtotal, setSubtotal] = useState("");
  const [tax, setTax] = useState("");
  const [total, setTotal] = useState("");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<LineItemDraft[]>([
    { name: "", quantity: "1", unit_price: "", total_price: "" },
  ]);

  const addItem = () =>
    setItems([...items, { name: "", quantity: "1", unit_price: "", total_price: "" }]);

  const removeItem = (i: number) =>
    setItems(items.filter((_, idx) => idx !== i));

  const updateItem = (i: number, field: keyof LineItemDraft, value: string) => {
    const updated = [...items];
    updated[i] = { ...updated[i], [field]: value };
    setItems(updated);
  };

  const toCents = (v: string) => (v ? Math.round(parseFloat(v) * 100) : null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await create.mutateAsync({
      store_name: storeName || null,
      transaction_date: date || null,
      currency: "CAD",
      subtotal: toCents(subtotal),
      tax: toCents(tax),
      total: toCents(total),
      notes: notes || null,
      line_items: items
        .filter((li) => li.name.trim())
        .map((li) => ({
          name: li.name,
          quantity: parseFloat(li.quantity) || 1,
          unit_price: toCents(li.unit_price),
          total_price: toCents(li.total_price),
        })),
    });
    navigate("/receipts");
  };

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Manual Entry</h1>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          <Card>
            <CardContent className="grid gap-4 py-5 sm:grid-cols-2">
              <Input label="Store" value={storeName} onChange={(e) => setStoreName(e.target.value)} placeholder="Store name" />
              <Input label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
              <Input label="Subtotal" type="number" step="0.01" value={subtotal} onChange={(e) => setSubtotal(e.target.value)} placeholder="0.00" />
              <Input label="Tax" type="number" step="0.01" value={tax} onChange={(e) => setTax(e.target.value)} placeholder="0.00" />
              <Input label="Total" type="number" step="0.01" value={total} onChange={(e) => setTotal(e.target.value)} placeholder="0.00" />
              <Input label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional notes" />
            </CardContent>
          </Card>

          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium">Line Items</h2>
              <Button type="button" variant="outline" size="sm" onClick={addItem}>
                <Plus size={14} /> Add Item
              </Button>
            </div>

            <div className="space-y-2">
              {items.map((item, i) => (
                <Card key={i}>
                  <CardContent className="flex items-end gap-3 py-3">
                    <div className="flex-1">
                      <Input
                        placeholder="Item name"
                        value={item.name}
                        onChange={(e) => updateItem(i, "name", e.target.value)}
                      />
                    </div>
                    <div className="w-16">
                      <Input
                        placeholder="Qty"
                        type="number"
                        step="0.01"
                        value={item.quantity}
                        onChange={(e) => updateItem(i, "quantity", e.target.value)}
                      />
                    </div>
                    <div className="w-24">
                      <Input
                        placeholder="Price"
                        type="number"
                        step="0.01"
                        value={item.total_price}
                        onChange={(e) => updateItem(i, "total_price", e.target.value)}
                      />
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeItem(i)}
                      disabled={items.length === 1}
                    >
                      <Trash2 size={16} className="text-text-muted" />
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          <div className="flex gap-3">
            <Button type="button" variant="outline" onClick={() => navigate(-1)}>
              Cancel
            </Button>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Saving..." : "Save Receipt"}
            </Button>
          </div>

          {create.isError && (
            <p className="text-sm text-destructive">
              {create.error instanceof Error ? create.error.message : "Failed to save"}
            </p>
          )}
        </form>
      </motion.div>
    </div>
  );
}
