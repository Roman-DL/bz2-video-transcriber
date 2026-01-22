import type { SlidesExtractionResult } from '@/api/types';
import { ResultFooter } from '@/components/common/ResultFooter';
import { formatNumber, formatTime } from '@/utils/formatUtils';

interface SlidesResultViewProps {
  slidesResult: SlidesExtractionResult;
}

/**
 * Display slides extraction result with metrics and extracted text.
 * Shows header with stats, markdown content, and footer with tokens/cost.
 */
export function SlidesResultView({ slidesResult }: SlidesResultViewProps) {
  return (
    <div className="h-full flex flex-col">
      {/* Header with metrics */}
      <div className="text-xs text-gray-500 mb-2 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          {slidesResult.slides_count} слайдов
        </span>
        <span>
          {formatNumber(slidesResult.chars_count)} симв.
        </span>
        <span>
          {formatNumber(slidesResult.words_count)} слов
        </span>
        {slidesResult.tables_count > 0 && (
          <span>
            {slidesResult.tables_count} таблиц
          </span>
        )}
        {slidesResult.processing_time_sec !== undefined && (
          <span className="text-emerald-600">
            {formatTime(slidesResult.processing_time_sec)}
          </span>
        )}
      </div>

      {/* Extracted text as markdown */}
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap leading-relaxed min-h-0">
        {slidesResult.extracted_text}
      </div>

      {/* Footer with LLM metrics */}
      <ResultFooter
        tokensUsed={slidesResult.tokens_used}
        cost={slidesResult.cost}
        model={slidesResult.model}
      />
    </div>
  );
}
