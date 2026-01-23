import type { SlidesExtractionResult } from '@/api/types';
import { ResultFooter } from '@/components/common/ResultFooter';
import { formatNumber } from '@/utils/formatUtils';

interface SlidesResultViewProps {
  slidesExtraction: SlidesExtractionResult;
}

/**
 * Display slides extraction result with metrics and extracted text.
 * Shows header with stats, markdown content, and footer with tokens/cost.
 */
export function SlidesResultView({ slidesExtraction }: SlidesResultViewProps) {
  return (
    <div className="h-full flex flex-col">
      {/* Header with metrics */}
      <div className="text-xs text-gray-500 mb-2 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          {slidesExtraction.slides_count} слайдов
        </span>
        <span>
          {formatNumber(slidesExtraction.chars_count)} симв.
        </span>
        <span>
          {formatNumber(slidesExtraction.words_count)} слов
        </span>
        {slidesExtraction.tables_count > 0 && (
          <span>
            {slidesExtraction.tables_count} таблиц
          </span>
        )}
      </div>

      {/* Extracted text as markdown */}
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap leading-relaxed min-h-0">
        {slidesExtraction.extracted_text}
      </div>

      {/* Footer with LLM metrics */}
      <ResultFooter
        tokensUsed={slidesExtraction.tokens_used}
        cost={slidesExtraction.cost}
        model={slidesExtraction.model}
      />
    </div>
  );
}
