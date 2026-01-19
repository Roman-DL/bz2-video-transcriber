import type { Summary } from '@/api/types';
import { Badge } from '@/components/common/Badge';

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
  if (summary.key_concepts.length > 0) {
    lines.push('## Ключевые концепции');
    lines.push('');
    for (const concept of summary.key_concepts) {
      lines.push(`• ${concept}`);
    }
    lines.push('');
  }

  // Инструменты и методы
  if (summary.practical_tools.length > 0) {
    lines.push('## Инструменты и методы');
    lines.push('');
    for (const tool of summary.practical_tools) {
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
    <div className="space-y-4">
      <div className="text-xs text-gray-500 mb-2">
        Модель: <span className="font-mono">{summary.model_name}</span>
      </div>

      {/* Summary text as markdown */}
      <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
        {markdownText}
      </div>

      {/* Metadata footer */}
      <div className="pt-4 border-t border-gray-100">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div>
            <span className="text-gray-500">Раздел:</span>{' '}
            <span className="text-gray-900">
              {summary.section}
              {summary.subsection && ` / ${summary.subsection}`}
            </span>
          </div>

          {summary.tags.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Теги:</span>
              <div className="flex flex-wrap gap-1">
                {summary.tags.map((tag) => (
                  <Badge key={tag} variant="default">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
