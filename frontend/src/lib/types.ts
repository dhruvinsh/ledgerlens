// ── Data model types ──

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "member";
  household_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Household {
  id: string;
  name: string;
  owner_id: string;
  sharing_mode: "shared" | "private";
  users: User[];
  created_at: string;
}

export interface Store {
  id: string;
  name: string;
  address: string | null;
  chain: string | null;
  latitude: number | null;
  longitude: number | null;
  is_verified: boolean;
  merged_into_id: string | null;
  aliases: string[];
  receipt_count: number;
  created_at: string;
}

export interface StoreAlias {
  id: string;
  store_id: string;
  alias_name: string;
  source: string;
  created_at: string;
}

export interface Receipt {
  id: string;
  user_id: string;
  store_id: string | null;
  store: Store | null;
  transaction_date: string | null;
  currency: string;
  subtotal: number | null;
  tax: number | null;
  total: number | null;
  source: "camera" | "upload" | "manual";
  status: ReceiptStatus;
  file_path: string | null;
  thumbnail_path: string | null;
  page_count: number;
  ocr_confidence: number | null;
  extraction_source: "llm" | "vision" | "heuristic" | null;
  raw_ocr_text: string | null;
  duplicate_of: string | null;
  notes: string | null;
  line_items: LineItem[];
  created_at: string;
}

export type ReceiptStatus =
  | "pending"
  | "processing"
  | "processed"
  | "reviewed"
  | "failed"
  | "deleted";

export interface CanonicalItemSummary {
  id: string;
  name: string;
  category: string | null;
  aliases: string[];
  product_url: string | null;
  image_path: string | null;
}

export interface LineItem {
  id: string;
  receipt_id: string;
  canonical_item_id: string | null;
  canonical_item: CanonicalItemSummary | null;
  name: string;
  quantity: number;
  unit_price: number | null;
  total_price: number | null;
  confidence: number | null;
  position: number;
  is_corrected: boolean;
}

export interface CanonicalItem {
  id: string;
  name: string;
  category: string | null;
  aliases: string[];
  product_url: string | null;
  image_path: string | null;
  image_source: "user" | "auto" | null;
  image_fetch_status: string | null;
  created_at: string;
}

export interface MatchSuggestion {
  id: string;
  line_item_id: string;
  line_item_name: string | null;
  line_item_raw_name: string | null;
  canonical_item_id: string;
  canonical_item: CanonicalItem;
  confidence: number;
  status: "pending" | "accepted" | "rejected";
  created_at: string;
}

export interface StoreMergeSuggestion {
  id: string;
  store_a: Store;
  store_b: Store;
  confidence: number;
  status: string;
  created_at: string;
}

export interface ReviewCounts {
  match_suggestions: number;
  store_merges: number;
}

export interface ProcessingJob {
  id: string;
  receipt_id: string;
  status: "queued" | "running" | "completed" | "failed";
  stage: "ocr" | "extraction" | "done" | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ModelConfig {
  id: string;
  name: string;
  provider_type: string;
  base_url: string;
  model_name: string;
  is_active: boolean;
  supports_vision: boolean;
  timeout_seconds: number;
  max_retries: number;
  health_status: string | null;
  last_health_check: string | null;
}

// ── Batch upload types ──

export interface BatchUploadError {
  filename: string;
  detail: string;
}

export interface BatchUploadResponse {
  receipts: Receipt[];
  errors: BatchUploadError[];
}

// ── API types ──

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface PricePoint {
  date: string;
  price: number;
  store_name: string;
  receipt_id: string;
}
