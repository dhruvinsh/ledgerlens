import { motion } from "motion/react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Receipt, DollarSign, Package, Store } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { formatMoney } from "@/lib/money";
import {
  useDashboardSummary,
  useSpendingByStore,
  useSpendingByMonth,
  useSpendingByCategory,
} from "@/hooks/useDashboard";

const PIE_COLORS = ["#b45309", "#d97706", "#f59e0b", "#16a34a", "#2563eb", "#7c3aed", "#dc2626", "#78716c"];

const stagger = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
};

export default function Dashboard() {
  const { data: summary, isLoading: loadingSummary } = useDashboardSummary();
  const { data: byStore } = useSpendingByStore();
  const { data: byMonth } = useSpendingByMonth();
  const { data: byCategory } = useSpendingByCategory();

  if (loadingSummary) return <Spinner className="mt-20" />;

  const summaryCards = [
    { label: "Receipts", value: summary?.total_receipts ?? 0, icon: Receipt, fmt: String },
    { label: "Total Spent", value: summary?.total_spent ?? 0, icon: DollarSign, fmt: (v: number) => formatMoney(v) },
    { label: "Products", value: summary?.total_items ?? 0, icon: Package, fmt: String },
    { label: "Stores", value: summary?.total_stores ?? 0, icon: Store, fmt: String },
  ];

  const storeData = (byStore ?? []).map((s) => ({
    name: s.store_name,
    total: s.total / 100,
  }));

  const monthData = (byMonth ?? []).map((m) => ({
    month: m.month,
    total: m.total / 100,
  }));

  const categoryData = (byCategory ?? []).map((c) => ({
    name: c.category,
    value: c.total / 100,
  }));

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Dashboard</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {summaryCards.map((card, i) => (
          <motion.div
            key={card.label}
            {...stagger}
            transition={{ delay: i * 0.05, duration: 0.3 }}
          >
            <Card>
              <CardContent className="flex items-center gap-3 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-sm bg-accent/10">
                  <card.icon size={20} className="text-accent" />
                </div>
                <div>
                  <p className="text-xs text-text-muted">{card.label}</p>
                  <p className="font-mono text-lg font-semibold">{card.fmt(card.value)}</p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Spending by store */}
        <motion.div {...stagger} transition={{ delay: 0.2, duration: 0.3 }}>
          <Card>
            <CardHeader>
              <h2 className="text-sm font-medium text-text-muted">Spending by Store</h2>
            </CardHeader>
            <CardContent>
              {storeData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={storeData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--color-text-muted)" }} />
                    <YAxis tick={{ fontSize: 12, fill: "var(--color-text-muted)" }} />
                    <Tooltip
                      contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "2px" }}
                      formatter={(v: number) => [`$${v.toFixed(2)}`, "Total"]}
                    />
                    <Bar dataKey="total" fill="var(--color-accent)" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-8 text-center text-sm text-text-muted">No data yet</p>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Spending by month */}
        <motion.div {...stagger} transition={{ delay: 0.25, duration: 0.3 }}>
          <Card>
            <CardHeader>
              <h2 className="text-sm font-medium text-text-muted">Monthly Spending</h2>
            </CardHeader>
            <CardContent>
              {monthData.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={monthData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="month" tick={{ fontSize: 12, fill: "var(--color-text-muted)" }} />
                    <YAxis tick={{ fontSize: 12, fill: "var(--color-text-muted)" }} />
                    <Tooltip
                      contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "2px" }}
                      formatter={(v: number) => [`$${v.toFixed(2)}`, "Total"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="total"
                      stroke="var(--color-accent)"
                      strokeWidth={2}
                      dot={{ fill: "var(--color-accent)", r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-8 text-center text-sm text-text-muted">No data yet</p>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Spending by category */}
        <motion.div {...stagger} transition={{ delay: 0.3, duration: 0.3 }} className="lg:col-span-2">
          <Card>
            <CardHeader>
              <h2 className="text-sm font-medium text-text-muted">Spending by Category</h2>
            </CardHeader>
            <CardContent>
              {categoryData.length > 0 ? (
                <div className="flex flex-col items-center gap-4 md:flex-row md:justify-center">
                  <ResponsiveContainer width={280} height={250}>
                    <PieChart>
                      <Pie
                        data={categoryData}
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        dataKey="value"
                        stroke="var(--color-surface)"
                        strokeWidth={2}
                      >
                        {categoryData.map((_, i) => (
                          <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => `$${v.toFixed(2)}`} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex flex-wrap gap-3">
                    {categoryData.map((c, i) => (
                      <div key={c.name} className="flex items-center gap-2 text-sm">
                        <div
                          className="h-3 w-3 rounded-sm"
                          style={{ background: PIE_COLORS[i % PIE_COLORS.length] }}
                        />
                        <span className="text-text-muted">{c.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-text-muted">No data yet</p>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
