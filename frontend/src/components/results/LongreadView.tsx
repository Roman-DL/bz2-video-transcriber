import { Columns } from 'lucide-react';
import type { Longread } from '@/api/types';
import { Badge } from '@/components/common/Badge';
import { ResultFooter } from '@/components/common/ResultFooter';
import { InlineDiffView } from '@/components/common/InlineDiffView';
import { formatNumber, formatTime } from '@/utils/formatUtils';

interface LongreadViewProps {
  longread: Longread;
  cleanedText?: string;
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
  showDiff = false,
  onToggleDiff,
}: LongreadViewProps) {
  const markdownText = formatLongreadAsMarkdown(longread);

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
          {formatNumber(longread.total_word_count)} слов
        </span>
        {longread.processing_time_sec !== undefined && (
          <span>
            {formatTime(longread.processing_time_sec)}
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

      {/* Tags metadata */}
      {(longread.topic_area.length > 0 || longread.tags.length > 0) && (
        <div className="pt-3 border-t border-gray-100 mt-3 shrink-0">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            {longread.topic_area.length > 0 && (
              <div>
                <span className="text-gray-500">Область:</span>{' '}
                <span className="text-gray-900">
                  {longread.topic_area.join(' / ')}
                </span>
              </div>
            )}
            {longread.tags.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Теги:</span>
                <div className="flex flex-wrap gap-1">
                  {longread.tags.map((tag) => (
                    <Badge key={tag} variant="default">{tag}</Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer with LLM metrics */}
      <ResultFooter
        tokensUsed={longread.tokens_used}
        cost={longread.cost}
        model={longread.model_name}
      />
    </div>
  );
}
