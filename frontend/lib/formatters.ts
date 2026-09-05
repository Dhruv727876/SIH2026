/**
 * Hydration-safe formatting utilities with explicit 'en-US' locale
 * to guarantee identical server and client HTML rendering.
 */

const numFormatter2Dec = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const numFormatter0Dec = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

export function formatCurrency(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "0.00";
  return numFormatter2Dec.format(val);
}

export function formatInteger(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return "0";
  return numFormatter0Dec.format(val);
}

export function formatDecimal(val: number | null | undefined, decimals = 2): string {
  if (val === null || val === undefined || isNaN(val)) return "0.00";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(val);
}
