import { useState, useEffect } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import type { LineItem } from "@/lib/types";

interface EditLineItemDialogProps {
  item: LineItem | null;
  onSave: (values: { name: string; quantity: number; total_price: number | null }) => void;
  onClose: () => void;
}

export function EditLineItemDialog({ item, onSave, onClose }: EditLineItemDialogProps) {
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [totalPrice, setTotalPrice] = useState("");

  useEffect(() => {
    if (item) {
      setName(item.name);
      setQuantity(String(item.quantity));
      setTotalPrice(item.total_price != null ? String(item.total_price / 100) : "");
    }
  }, [item]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const toCents = (v: string) => (v ? Math.round(parseFloat(v) * 100) : null);
    onSave({
      name,
      quantity: parseFloat(quantity) || 1,
      total_price: toCents(totalPrice),
    });
  };

  return (
    <Dialog open={item !== null} onClose={onClose} title="Edit Line Item">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-text-muted">
            Item Name
          </label>
          <input
            className="w-full rounded-sm border border-border bg-background px-3 py-2 text-sm focus:border-accent focus:outline-none"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-text-muted">
              Quantity
            </label>
            <input
              type="number"
              step="any"
              min="0"
              className="w-full rounded-sm border border-border bg-background px-3 py-2 text-right font-mono text-sm focus:border-accent focus:outline-none"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-text-muted">
              Total Price
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 font-mono text-sm text-text-muted">
                $
              </span>
              <input
                type="number"
                step="0.01"
                min="0"
                className="w-full rounded-sm border border-border bg-background py-2 pr-3 pl-7 text-right font-mono text-sm focus:border-accent focus:outline-none"
                value={totalPrice}
                onChange={(e) => setTotalPrice(e.target.value)}
                placeholder="0.00"
              />
            </div>
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <Button type="button" variant="outline" className="flex-1" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" className="flex-1">
            Save
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
