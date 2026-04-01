import { useState } from "react";
import { motion } from "motion/react";
import { Search } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useItems, useItemPrices } from "@/hooks/useItems";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { formatMoney } from "@/lib/money";

export default function PriceTracker() {
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: items } = useItems({ search: search || undefined, per_page: 10 });
  const { data: priceData, isLoading: loadingPrices } = useItemPrices(selectedId ?? undefined);

  const chartData = (priceData?.data_points ?? []).map((p) => ({
    date: p.date,
    price: p.price / 100,
    store: p.store_name,
  }));

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Price Tracker</h1>

      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          className="w-full rounded-sm border border-border bg-surface py-2 pl-9 pr-3 text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
          placeholder="Search for a product..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {search && items?.items && items.items.length > 0 && !selectedId && (
        <Card>
          <div className="divide-y divide-border">
            {items.items.map((item) => (
              <button
                key={item.id}
                className="w-full px-5 py-3 text-left text-sm hover:bg-accent/5"
                onClick={() => { setSelectedId(item.id); setSearch(item.name); }}
              >
                <span className="font-medium">{item.name}</span>
                {item.category && (
                  <span className="ml-2 text-xs text-text-muted">{item.category}</span>
                )}
              </button>
            ))}
          </div>
        </Card>
      )}

      {selectedId && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium">
                  Price History — {priceData?.item?.name}
                </h2>
                <button
                  className="text-xs text-text-muted hover:text-text"
                  onClick={() => { setSelectedId(null); setSearch(""); }}
                >
                  Clear
                </button>
              </div>
            </CardHeader>
            <CardContent>
              {loadingPrices ? (
                <Spinner className="py-8" />
              ) : chartData.length === 0 ? (
                <p className="py-8 text-center text-sm text-text-muted">
                  No price data available for this product.
                </p>
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} />
                      <YAxis tick={{ fontSize: 11, fill: "var(--color-text-muted)" }} tickFormatter={(v) => `$${v}`} />
                      <Tooltip
                        contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "2px" }}
                        formatter={(v: number) => [`$${v.toFixed(2)}`, "Price"]}
                      />
                      <Line type="monotone" dataKey="price" stroke="var(--color-accent)" strokeWidth={2} dot={{ fill: "var(--color-accent)", r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>

                  {/* Price table */}
                  <div className="mt-4 max-h-48 overflow-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left text-xs text-text-muted">
                          <th className="py-2">Date</th>
                          <th>Store</th>
                          <th className="text-right">Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(priceData?.data_points ?? []).map((p, i) => (
                          <tr key={i} className="border-b border-border/50">
                            <td className="py-1.5">{p.date}</td>
                            <td>{p.store_name}</td>
                            <td className="text-right font-mono">{formatMoney(p.price)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
