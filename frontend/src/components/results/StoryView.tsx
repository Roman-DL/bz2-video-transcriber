import type { Story } from '@/api/types';
import { ResultFooter } from '@/components/common/ResultFooter';
import { formatNumber, formatTime } from '@/utils/formatUtils';

interface StoryViewProps {
  story: Story;
}

// Block names in Russian
const BLOCK_NAMES: Record<number, string> = {
  1: 'Кто они',
  2: 'Путь в бизнес',
  3: 'Рост и вызовы',
  4: 'Ключ к статусу',
  5: 'Как устроен бизнес',
  6: 'Принципы и советы',
  7: 'Итоги',
  8: 'Заметки аналитика',
};

function formatStoryAsMarkdown(story: Story): string {
  const lines: string[] = [];

  // Main insight as quote
  if (story.main_insight) {
    lines.push(`> ${story.main_insight}`);
    lines.push('');
  }

  // Blocks
  for (const block of story.blocks) {
    const blockName = block.block_name || BLOCK_NAMES[block.block_number] || `Блок ${block.block_number}`;
    lines.push(`## ${block.block_number}. ${blockName}`);
    lines.push('');
    lines.push(block.content);
    lines.push('');
  }

  return lines.join('\n');
}

export function StoryView({ story }: StoryViewProps) {
  const markdownText = formatStoryAsMarkdown(story);

  return (
    <div className="h-full flex flex-col">
      {/* Header with metrics */}
      <div className="text-xs text-gray-500 mb-2 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          {formatNumber(story.chars)} симв.
        </span>
        <span>
          {story.total_blocks} блоков
        </span>
        {story.processing_time_sec !== undefined && (
          <span>
            {formatTime(story.processing_time_sec)}
          </span>
        )}
      </div>

      {/* Story text as markdown */}
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap leading-relaxed min-h-0">
        {markdownText}
      </div>

      {/* Metadata footer */}
      <div className="pt-3 border-t border-gray-100 mt-3 shrink-0">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div>
            <span className="text-gray-500">Уровень доступа:</span>{' '}
            <span className="text-gray-900">{story.access_level}</span>
          </div>
        </div>
      </div>

      {/* Footer with LLM metrics */}
      <ResultFooter
        tokensUsed={story.tokens_used}
        cost={story.cost}
        model={story.model_name}
      />
    </div>
  );
}
