import type { VideoSummary } from '@/api/types';
import { Badge } from '@/components/common/Badge';

interface SummaryViewProps {
  summary: VideoSummary;
}

function formatSummaryAsMarkdown(summary: VideoSummary): string {
  const lines: string[] = [];

  // Краткое содержание
  lines.push('## Краткое содержание');
  lines.push('');
  lines.push(summary.summary);
  lines.push('');

  // Ключевые тезисы
  if (summary.key_points.length > 0) {
    lines.push('## Ключевые тезисы');
    lines.push('');
    for (const point of summary.key_points) {
      lines.push(`• ${point}`);
    }
    lines.push('');
  }

  // Практические рекомендации
  if (summary.recommendations.length > 0) {
    lines.push('## Практические рекомендации');
    lines.push('');
    summary.recommendations.forEach((rec, i) => {
      lines.push(`${i + 1}. ${rec}`);
    });
    lines.push('');
  }

  // Для кого полезно
  lines.push('## Для кого полезно');
  lines.push('');
  lines.push(summary.target_audience);
  lines.push('');

  // Вопросы
  if (summary.questions_answered.length > 0) {
    lines.push('## Вопросы, на которые отвечает видео');
    lines.push('');
    for (const q of summary.questions_answered) {
      lines.push(`• ${q}`);
    }
  }

  return lines.join('\n');
}

export function SummaryView({ summary }: SummaryViewProps) {
  const markdownText = formatSummaryAsMarkdown(summary);

  return (
    <div className="space-y-4">
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
              {summary.section} / {summary.subsection}
            </span>
          </div>

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
        </div>
      </div>
    </div>
  );
}
