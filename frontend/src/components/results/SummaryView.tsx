import type { Summary } from '@/api/types';
import { ResultFooter } from '@/components/common/ResultFooter';
import { formatNumber } from '@/utils/formatUtils';

interface SummaryViewProps {
  summary: Summary;
}

function formatSummaryAsMarkdown(summary: Summary): string {
  const lines: string[] = [];

  // Суть темы
  lines.push('## Суть темы');
  lines.push('');
  lines.push(summary.essence);
  lines.push('');

  // Ключевые концепции
  if (summary.keyConcepts.length > 0) {
    lines.push('## Ключевые концепции');
    lines.push('');
    for (const concept of summary.keyConcepts) {
      lines.push(`• ${concept}`);
    }
    lines.push('');
  }

  // Инструменты и методы
  if (summary.practicalTools.length > 0) {
    lines.push('## Инструменты и методы');
    lines.push('');
    for (const tool of summary.practicalTools) {
      lines.push(`• ${tool}`);
    }
    lines.push('');
  }

  // Ключевые цитаты
  if (summary.quotes.length > 0) {
    lines.push('## Ключевые цитаты');
    lines.push('');
    for (const quote of summary.quotes) {
      lines.push(`> "${quote}"`);
      lines.push('');
    }
  }

  // Главный инсайт
  if (summary.insight) {
    lines.push('## Главный инсайт');
    lines.push('');
    lines.push(`**${summary.insight}**`);
    lines.push('');
  }

  // Что сделать
  if (summary.actions.length > 0) {
    lines.push('## Что сделать');
    lines.push('');
    summary.actions.forEach((action, i) => {
      lines.push(`${i + 1}. ${action}`);
    });
  }

  return lines.join('\n');
}

export function SummaryView({ summary }: SummaryViewProps) {
  const markdownText = formatSummaryAsMarkdown(summary);

  return (
    <div className="h-full flex flex-col">
      {/* Header with metrics */}
      <div className="text-xs text-gray-500 mb-2 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          {formatNumber(summary.chars)} симв.
        </span>
        <span>
          {formatNumber(summary.words)} слов
        </span>
      </div>

      {/* Summary text as markdown */}
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap leading-relaxed min-h-0">
        {markdownText}
      </div>

      {/* Footer with LLM metrics */}
      <ResultFooter
        tokensUsed={summary.tokensUsed}
        cost={summary.cost}
        model={summary.modelName}
      />
    </div>
  );
}
