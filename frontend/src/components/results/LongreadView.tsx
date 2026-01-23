import { Columns } from 'lucide-react';
import type { Longread } from '@/api/types';
import { ResultFooter } from '@/components/common/ResultFooter';
import { InlineDiffView } from '@/components/common/InlineDiffView';
import { formatNumber } from '@/utils/formatUtils';

interface LongreadViewProps {
  longread: Longread;
  cleanedText?: string;
  cleanedChars?: number;
  showDiff?: boolean;
  onToggleDiff?: () => void;
}

function formatLongreadAsMarkdown(longread: Longread): string {
  const lines: string[] = [];

  // Introduction
  if (longread.introduction) {
    lines.push(longread.introduction);
    lines.push('');
  }

  // Sections
  for (const section of longread.sections) {
    lines.push(`## ${section.title}`);
    lines.push('');
    lines.push(section.content);
    lines.push('');
  }

  // Conclusion
  if (longread.conclusion) {
    lines.push('---');
    lines.push('');
    lines.push(longread.conclusion);
  }

  return lines.join('\n');
}

export function LongreadView({
  longread,
  cleanedText,
  cleanedChars,
  showDiff = false,
  onToggleDiff,
}: LongreadViewProps) {
  const markdownText = formatLongreadAsMarkdown(longread);

  // Calculate reduction percentage if cleanedChars available
  const reductionPercent = cleanedChars && cleanedChars > 0
    ? Math.round((1 - longread.chars / cleanedChars) * 100)
    : null;

  // Show diff view if enabled
  if (showDiff && cleanedText && onToggleDiff) {
    return (
      <InlineDiffView
        leftText={cleanedText}
        rightText={markdownText}
        leftTitle="Очистка"
        rightTitle="Лонгрид"
        onClose={onToggleDiff}
      />
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with metrics */}
      <div className="text-xs text-gray-500 mb-2 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          {formatNumber(longread.chars)} симв.
        </span>
        <span>
          {formatNumber(longread.totalWordCount)} слов
        </span>
        {reductionPercent !== null && (
          <span className={reductionPercent > 0 ? 'text-emerald-600' : 'text-amber-600'}>
            {reductionPercent > 0 ? '-' : '+'}{Math.abs(reductionPercent)}%
          </span>
        )}
      </div>

      {/* Diff button - only show if cleanedText available */}
      {cleanedText && onToggleDiff && (
        <div className="mb-2 shrink-0">
          <button
            onClick={onToggleDiff}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <Columns className="w-3.5 h-3.5" />
            Сравнить с очисткой
          </button>
        </div>
      )}

      {/* Longread text as markdown */}
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap leading-relaxed min-h-0">
        {markdownText}
      </div>

      {/* Footer with LLM metrics */}
      <ResultFooter
        tokensUsed={longread.tokensUsed}
        cost={longread.cost}
        model={longread.modelName}
      />
    </div>
  );
}
