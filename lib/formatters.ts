/**
 * Funções utilitárias para formatação de números e valores
 * Com proteção contra valores undefined/null/NaN
 */

/**
 * Formata número para locale pt-BR com fallback seguro
 */
export function formatNumberBR(
  value: number | string | null | undefined,
  options?: Intl.NumberFormatOptions
): string {
  const n = Number(value ?? 0);
  if (Number.isNaN(n)) return "0";
  
  if (options) {
    return n.toLocaleString("pt-BR", options);
  }
  
  return n.toLocaleString("pt-BR");
}

/**
 * Formata número como moeda (R$) com fallback seguro
 */
export function formatCurrencyBR(
  value: number | string | null | undefined
): string {
  return formatNumberBR(value, {
    style: "currency",
    currency: "BRL",
  });
}

/**
 * Formata número como percentual com fallback seguro
 */
export function formatPercentBR(
  value: number | string | null | undefined,
  decimals: number = 1
): string {
  const n = Number(value ?? 0);
  if (Number.isNaN(n)) return "0%";
  
  return `${n.toFixed(decimals)}%`;
}

/**
 * Garante que um valor seja um número válido
 */
export function safeNumber(
  value: number | string | null | undefined,
  defaultValue: number = 0
): number {
  const n = Number(value ?? defaultValue);
  return Number.isNaN(n) ? defaultValue : n;
}

