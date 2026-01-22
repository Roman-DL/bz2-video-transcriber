/**
 * Formatting utilities for displaying metrics in UI.
 */

/**
 * Format time duration in human-readable format.
 * @param seconds - Duration in seconds
 * @returns Formatted string: "235мс" / "23с" / "1м 23с" / "1ч 5м"
 */
export function formatTime(seconds: number): string {
  if (seconds < 0) return '—';

  // Less than 1 second — show milliseconds
  if (seconds < 1) {
    const ms = Math.round(seconds * 1000);
    return `${ms}мс`;
  }

  // Less than 60 seconds — show seconds
  if (seconds < 60) {
    return `${Math.round(seconds)}с`;
  }

  // Less than 1 hour — show minutes and seconds
  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return secs > 0 ? `${minutes}м ${secs}с` : `${minutes}м`;
  }

  // 1 hour or more — show hours and minutes
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return minutes > 0 ? `${hours}ч ${minutes}м` : `${hours}ч`;
}

/**
 * Format cost in USD.
 * @param cost - Cost in dollars
 * @returns Formatted string: "бесплатно" / "~$0.03"
 */
export function formatCost(cost: number | null | undefined): string {
  if (cost === null || cost === undefined || cost === 0) {
    return 'бесплатно';
  }

  // Small costs — show with more precision
  if (cost < 0.01) {
    return `~$${cost.toFixed(4)}`;
  }

  // Normal costs — show 2 decimal places
  return `~$${cost.toFixed(2)}`;
}

/**
 * Format number with thousands separator.
 * Uses non-breaking space as separator (Russian standard).
 * @param n - Number to format
 * @returns Formatted string: "1 234 567"
 */
export function formatNumber(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';

  // Use Intl.NumberFormat for proper locale formatting
  return new Intl.NumberFormat('ru-RU').format(Math.round(n));
}

/**
 * Format tokens count with total calculation.
 * @param input - Input tokens
 * @param output - Output tokens
 * @returns Formatted string: "1 234 вх / 567 вых"
 */
export function formatTokens(input: number, output: number): string {
  return `${formatNumber(input)} вх / ${formatNumber(output)} вых`;
}
