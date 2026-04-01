import { useState } from "react";
import { Link } from "react-router";
import { motion } from "motion/react";
import { Search, Package } from "lucide-react";
import { useItems } from "@/hooks/useItems";
import { Card, CardContent } from "@/components/ui/card";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";

export default function Items() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useItems({ search: search || undefined, page, per_page: 24 });

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Products</h1>

      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          className="w-full rounded-sm border border-border bg-surface py-2 pl-9 pr-3 text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
          placeholder="Search products..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
      </div>

      {isLoading ? (
        <Spinner className="mt-12" />
      ) : !data?.items.length ? (
        <p className="py-16 text-center text-text-muted">
          {search ? "No products match your search." : "No products yet. Upload a receipt to get started."}
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
                <Link to={`/items/${item.id}`}>
                  <Card className="transition-shadow hover:shadow-md">
                    <CardContent className="flex items-center gap-3 py-4">
                      {item.image_path ? (
                        <img
                          src={`/files/${item.image_path}`}
                          alt={item.name}
                          className="h-10 w-10 rounded-sm object-cover"
                        />
                      ) : (
                        <div className="flex h-10 w-10 items-center justify-center rounded-sm bg-accent/10">
                          <Package size={18} className="text-accent" />
                        </div>
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{item.name}</p>
                        <p className="text-xs text-text-muted">
                          {item.category ?? "Uncategorized"}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>
          <Pagination
            page={page}
            totalPages={Math.ceil((data.total ?? 0) / 24)}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
