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
          {slidesExtraction.slidesCount} слайдов
        </span>
        <span>
          {formatNumber(slidesExtraction.charsCount)} симв.
        </span>
        <span>
          {formatNumber(slidesExtraction.wordsCount)} слов
        </span>
        {slidesExtraction.tablesCount > 0 && (
          <span>
            {slidesExtraction.tablesCount} таблиц
          </span>
        )}
      </div>

      {/* Extracted text as markdown */}
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap leading-relaxed min-h-0">
        {slidesExtraction.extractedText}
      </div>

      {/* Footer with LLM metrics */}
      <ResultFooter
        tokensUsed={slidesExtraction.tokensUsed}
        cost={slidesExtraction.cost}
        model={slidesExtraction.model}
      />
    </div>
  );
}
