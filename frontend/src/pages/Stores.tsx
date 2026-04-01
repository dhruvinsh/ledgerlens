import { useState } from "react";
import { motion } from "motion/react";
import { Search, MapPin, Store as StoreIcon } from "lucide-react";
import { useStores } from "@/hooks/useStores";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";

export default function Stores() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useStores({ search: search || undefined, page, per_page: 20 });

  return (
    <div className="space-y-6 p-6 pb-24 md:pb-6">
      <h1 className="font-serif text-2xl">Stores</h1>

      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          className="w-full rounded-sm border border-border bg-surface py-2 pl-9 pr-3 text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
          placeholder="Search stores..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
      </div>

      {isLoading ? (
        <Spinner className="mt-12" />
      ) : !data?.items.length ? (
        <p className="py-16 text-center text-text-muted">No stores found.</p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((store, i) => (
              <motion.div
                key={store.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.02, duration: 0.2 }}
              >
                <Card>
                  <CardContent className="space-y-2 py-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <StoreIcon size={16} className="text-accent" />
                        <span className="font-medium">{store.name}</span>
                      </div>
                      {store.is_verified && <Badge variant="success">Verified</Badge>}
                    </div>
                    {store.address && (
                      <div className="flex items-start gap-1.5 text-xs text-text-muted">
                        <MapPin size={12} className="mt-0.5 shrink-0" />
                        {store.address}
                      </div>
                    )}
                    {store.chain && (
                      <p className="text-xs text-text-muted">Chain: {store.chain}</p>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
          <Pagination
            page={page}
            totalPages={Math.ceil((data.total ?? 0) / 20)}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}
