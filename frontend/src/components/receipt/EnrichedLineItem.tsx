import { useState } from "react";
import { motion } from "motion/react";
import {
  ExternalLink,
  ImageOff,
  Pencil,
  Tag,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatMoney } from "@/lib/money";
import type { LineItem } from "@/lib/types";

interface EnrichedLineItemProps {
  item: LineItem;
  currency: string;
  onEdit: (item: LineItem) => void;
}

function ProductImage({ path, name }: { path: string; name: string }) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-border/30">
        <ImageOff size={18} className="text-text-muted/50" />
      </div>
    );
  }

  return (
    <img
      src={`/files/${path}`}
      alt={name}
      className="h-full w-full object-cover"
      onError={() => setFailed(true)}
    />
  );
}

export function EnrichedLineItem({ item, currency, onEdit }: EnrichedLineItemProps) {
  const ci = item.canonical_item;
  const hasEnrichment = ci !== null && ci !== undefined;

  // OCR name differs from canonical name
  const namesDiffer = hasEnrichment && ci.name.toLowerCase() !== item.name.toLowerCase();

  return (
    <div className="group px-5 py-3">
      {/* Main row */}
      <div className="flex items-center gap-3">
        {/* Product thumbnail */}
        {hasEnrichment && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
            className="hidden h-10 w-10 shrink-0 overflow-hidden rounded-sm border border-border sm:block"
          >
            {ci.image_path ? (
              <ProductImage path={ci.image_path} name={ci.name} />
            ) : (
              <div className="flex h-full w-full items-center justify-center bg-border/20">
                <ImageOff size={14} className="text-text-muted/40" />
              </div>
            )}
          </motion.div>
        )}

        {/* Name + meta */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium">
              {hasEnrichment ? ci.name : item.name}
            </span>
            {hasEnrichment && ci.category && (
              <Badge variant="muted" className="hidden shrink-0 sm:inline-flex">
                <Tag size={10} className="mr-1" />
                {ci.category}
              </Badge>
            )}
          </div>
          {namesDiffer && (
            <p className="truncate text-xs text-text-muted">
              <span className="font-mono opacity-60">{item.name}</span>
            </p>
          )}
        </div>

        {/* Quantity + price */}
        <span className="shrink-0 text-xs text-text-muted">x{item.quantity}</span>
        <span className="w-20 shrink-0 text-right font-mono text-sm">
          {formatMoney(item.total_price, currency)}
        </span>

        {/* Edit */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onEdit(item)}
          className="h-7 w-7 shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
        >
          <Pencil size={14} className="text-text-muted" />
        </Button>
      </div>

      {/* Enriched metadata — always visible when present */}
      {hasEnrichment && (ci.aliases.length > 0 || ci.product_url || ci.category) && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 pl-0 sm:pl-[3.25rem]"
        >
          {/* Category on mobile (hidden on desktop where it's in the main row) */}
          {ci.category && (
            <Badge variant="muted" className="sm:hidden">
              <Tag size={10} className="mr-1" />
              {ci.category}
            </Badge>
          )}

          {/* Product link */}
          {ci.product_url && (
            <a
              href={ci.product_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:text-accent-hover transition-colors"
            >
              View product <ExternalLink size={11} />
            </a>
          )}
        </motion.div>
      )}
    </div>
  );
}
