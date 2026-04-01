const formatters = new Map<string, Intl.NumberFormat>();

function getFormatter(currency: string): Intl.NumberFormat {
  let fmt = formatters.get(currency);
  if (!fmt) {
    fmt = new Intl.NumberFormat("en-CA", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
    });
    formatters.set(currency, fmt);
  }
  return fmt;
}

export function formatMoney(
  cents: number | null | undefined,
  currency = "CAD",
): string {
  if (cents == null) return "—";
  return getFormatter(currency).format(cents / 100);
}
