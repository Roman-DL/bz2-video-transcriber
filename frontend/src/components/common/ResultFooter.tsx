import type { TokensUsed } from '@/api/types';
import { formatTokens, formatCost } from '@/utils/formatUtils';

interface ResultFooterProps {
  tokensUsed?: TokensUsed;
  cost?: number;
  model?: string;
}

/**
 * Footer component for LLM results showing token usage and cost.
 * Used in CleanedTranscriptView, LongreadView, SummaryView, StoryView.
 */
export function ResultFooter({ tokensUsed, cost, model }: ResultFooterProps) {
  // Don't render if no metrics available
  if (!tokensUsed && cost === undefined && !model) {
    return null;
  }

  return (
    <div className="mt-4 pt-3 border-t border-gray-100 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
      {tokensUsed && (
        <span>
          Токены: {formatTokens(tokensUsed.input, tokensUsed.output)}
        </span>
      )}
      {cost !== undefined && (
        <span>Стоимость: {formatCost(cost)}</span>
      )}
      {model && (
        <span className="ml-auto font-mono text-gray-400">{model}</span>
      )}
    </div>
  );
}
