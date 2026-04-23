import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { motion } from "motion/react";
import { Search, Package, Receipt } from "lucide-react";
import { useItems } from "@/hooks/useItems";
import { Card, CardContent } from "@/components/ui/card";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";

const PER_PAGE = 24;
const SEARCH_DEBOUNCE_MS = 250;

export default function Items() {
  const [params, setParams] = useSearchParams();
  const urlSearch = params.get("q") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [search, setSearch] = useState(urlSearch);

  const { data, isLoading } = useItems({
    search: urlSearch || undefined,
    page,
    per_page: PER_PAGE,
  });

  const update = useCallback(
    (next: { q?: string; page?: number }) => {
      setParams(
        (prev) => {
          const p = new URLSearchParams(prev);
          if (next.q !== undefined) {
            if (next.q) p.set("q", next.q);
            else p.delete("q");
          }
          if (next.page !== undefined) {
            if (next.page <= 1) p.delete("page");
            else p.set("page", String(next.page));
          }
          return p;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  useEffect(() => {
    setSearch(urlSearch);
  }, [urlSearch]);

  useEffect(() => {
    if (search === urlSearch) return;
    const t = setTimeout(() => update({ q: search, page: 1 }), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [search, urlSearch, update]);

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Products</h1>

      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          className="w-full rounded-sm border border-border bg-surface py-2 pl-9 pr-3 text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
          placeholder="Search products..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {isLoading ? (
        <Spinner className="mt-12" />
      ) : !data?.items.length ? (
        <p className="py-16 text-center text-text-muted">
          {urlSearch ? "No products match your search." : "No products yet. Upload a receipt to get started."}
        </p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data.items.map((item, i) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.02, duration: 0.2 }}
              >
                <Link to={`/items/${item.id}`} className="block">
                  <Card className="transition-shadow hover:shadow-md">
                    <CardContent className="flex h-[116px] flex-col py-4">
                      {/* Top: image + name */}
                      <div className="flex items-start gap-3">
                        {item.image_path ? (
                          <img
                            src={`/files/${item.image_path}`}
                            alt={item.name}
                            className="h-10 w-10 shrink-0 rounded-sm object-cover"
                          />
                        ) : (
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm bg-accent/10">
                            <Package size={18} className="text-accent" />
                          </div>
                        )}
                        <span className="truncate font-medium">{item.name}</span>
                      </div>

                      {/* Middle: category — fills remaining space */}
                      <div className="mt-1.5 min-h-0 flex-1">
                        <p className="text-xs text-text-muted">
                          {item.category ?? "Uncategorized"}
                        </p>
                      </div>

                      {/* Bottom: receipt count — pinned to bottom */}
                      <div className="mt-1.5 flex items-center gap-1 text-xs text-text-muted">
                        <Receipt size={11} />
                        {item.receipt_count ?? 0}
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
