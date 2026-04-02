import { useState, useEffect, useCallback } from "react";
import { ArrowRight, Search } from "lucide-react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface MergeDialogProps<T> {
  open: boolean;
  onClose: () => void;
  onConfirm: (selectedId: string) => void;
  title: string;
  searchPlaceholder: string;
  searchFn: (query: string) => Promise<T[]>;
  renderItem: (item: T) => React.ReactNode;
  getId: (item: T) => string;
  getName: (item: T) => string;
  currentName: string;
  loading?: boolean;
}

export function MergeDialog<T>({
  open,
  onClose,
  onConfirm,
  title,
  searchPlaceholder,
  searchFn,
  renderItem,
  getId,
  getName,
  currentName,
  loading = false,
}: MergeDialogProps<T>) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<T[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  const selectedItem = results.find((r) => getId(r) === selectedId);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const items = await searchFn(query);
        setResults(items);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query, searchFn]);

  // Reset on close
  useEffect(() => {
    if (!open) {
      setQuery("");
      setResults([]);
      setSelectedId(null);
      setConfirming(false);
    }
  }, [open]);

  const handleConfirm = useCallback(() => {
    if (selectedId) {
      onConfirm(selectedId);
    }
  }, [selectedId, onConfirm]);

  if (confirming && selectedItem) {
    return (
      <Dialog open={open} onClose={onClose} title="Confirm Merge">
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-sm">
            <div className="flex-1 rounded-sm border border-border p-2 text-center">
              <p className="text-xs text-text-muted">Will be absorbed</p>
              <p className="font-medium">{getName(selectedItem)}</p>
            </div>
            <ArrowRight size={16} className="shrink-0 text-text-muted" />
            <div className="flex-1 rounded-sm border border-accent/20 bg-accent/5 p-2 text-center">
              <p className="text-xs text-accent">Keep</p>
              <p className="font-medium">{currentName}</p>
            </div>
          </div>
          <p className="text-sm text-text-muted">
            All receipts, aliases, and data from{" "}
            <strong>{getName(selectedItem)}</strong> will be moved into{" "}
            <strong>{currentName}</strong>. This cannot be undone.
          </p>
          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => setConfirming(false)}
              disabled={loading}
            >
              Back
            </Button>
            <Button
              className="flex-1"
              onClick={handleConfirm}
              disabled={loading}
            >
              {loading ? "Merging..." : "Merge"}
            </Button>
          </div>
        </div>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onClose={onClose} title={title}>
      <div className="space-y-3">
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <input
            className="w-full rounded-sm border border-border bg-surface py-2 pl-9 pr-3 text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/30"
            placeholder={searchPlaceholder}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedId(null);
            }}
            autoFocus
          />
        </div>

        {searching && (
          <p className="text-center text-xs text-text-muted">Searching...</p>
        )}

        {results.length > 0 && (
          <div className="max-h-60 space-y-1 overflow-y-auto">
            {results.map((item) => {
              const id = getId(item);
              const isSelected = id === selectedId;
              return (
                <button
                  key={id}
                  onClick={() => setSelectedId(isSelected ? null : id)}
                  className={`w-full rounded-sm border px-3 py-2 text-left text-sm transition-colors ${
                    isSelected
                      ? "border-accent bg-accent/10"
                      : "border-border hover:bg-accent/5"
                  }`}
                >
                  {renderItem(item)}
                </button>
              );
            })}
          </div>
        )}

        {query && !searching && results.length === 0 && (
          <p className="text-center text-xs text-text-muted">No results found.</p>
        )}

        <Button
          className="w-full"
          disabled={!selectedId}
          onClick={() => setConfirming(true)}
        >
          Continue
        </Button>
      </div>
    </Dialog>
  );
}
