import { Link, useSearchParams } from "react-router";
import { motion } from "motion/react";
import { Plus, Calendar, Store as StoreIcon } from "lucide-react";
import { useReceipts } from "@/hooks/useReceipts";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { formatMoney } from "@/lib/money";

const PER_PAGE = 20;
const STATUSES = ["", "pending", "processing", "processed", "reviewed", "failed"];

export default function Receipts() {
  const [params, setParams] = useSearchParams();
  const page = Math.max(1, Number(params.get("page")) || 1);
  const status = params.get("status") ?? "";

  const { data, isLoading } = useReceipts({
    page,
    per_page: PER_PAGE,
    status: status || undefined,
  });

  const update = (next: { page?: number; status?: string }) => {
    setParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        if (next.page !== undefined) {
          if (next.page <= 1) p.delete("page");
          else p.set("page", String(next.page));
        }
        if (next.status !== undefined) {
          if (next.status) p.set("status", next.status);
          else p.delete("status");
        }
        return p;
      },
      { replace: true },
    );
  };

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-2xl">Receipts</h1>
        <div className="flex gap-2">
          <Link to="/receipts/manual">
            <Button variant="outline" size="sm">Manual</Button>
          </Link>
          <Link to="/receipts/add">
            <Button size="sm"><Plus size={16} /> Upload</Button>
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => update({ status: s, page: 1 })}
            className={`rounded-sm px-3 py-1 text-xs font-medium transition-colors ${
              status === s
                ? "bg-accent text-accent-foreground"
                : "bg-surface border border-border text-text-muted hover:text-text"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {isLoading ? (
        <Spinner className="mt-12" />
      ) : !data?.items.length ? (
        <div className="py-16 text-center">
          <p className="text-text-muted">No receipts found.</p>
          <Link to="/receipts/add">
            <Button className="mt-4" size="sm">Upload your first receipt</Button>
          </Link>
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((r, i) => (
              <motion.div
                key={r.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03, duration: 0.25 }}
              >
                <Link to={`/receipts/${r.id}`}>
                  <Card className="transition-shadow hover:shadow-md">
                    <CardContent className="space-y-2 py-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <StoreIcon size={14} className="text-text-muted" />
                          <span className="text-sm font-medium">
                            {r.store?.name ?? "Unknown Store"}
                          </span>
                        </div>
                        <StatusBadge status={r.status} />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-xs text-text-muted">
                          <Calendar size={12} />
                          {r.transaction_date ?? "No date"}
                        </div>
                        <span className="font-mono text-sm font-semibold">
                          {formatMoney(r.total, r.currency)}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>
          <Pagination
            page={page}
            totalPages={Math.ceil((data.total ?? 0) / PER_PAGE)}
            onPageChange={(p) => update({ page: p })}
          />
        </>
      )}
    </div>
  );
}
