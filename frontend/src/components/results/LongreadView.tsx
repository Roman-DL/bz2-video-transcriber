import type { Longread } from '@/api/types';
import { Badge } from '@/components/common/Badge';

interface LongreadViewProps {
  longread: Longread;
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

export function LongreadView({ longread }: LongreadViewProps) {
  const markdownText = formatLongreadAsMarkdown(longread);

  return (
    <div className="space-y-4">
      <div className="text-xs text-gray-500 mb-2">
        Модель: <span className="font-mono">{longread.model_name}</span>
      </div>

      {/* Longread text as markdown */}
      <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
        {markdownText}
      </div>

      {/* Metadata footer */}
      <div className="pt-4 border-t border-gray-100">
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
    </div>
  );
}
