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
  if (story.mainInsight) {
    lines.push(`> ${story.mainInsight}`);
    lines.push('');
  }

  // Blocks
  for (const block of story.blocks) {
    const blockName = block.blockName || BLOCK_NAMES[block.blockNumber] || `Блок ${block.blockNumber}`;
    lines.push(`## ${block.blockNumber}. ${blockName}`);
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
          {story.totalBlocks} блоков
        </span>
        {story.processingTimeSec !== undefined && (
          <span>
            {formatTime(story.processingTimeSec)}
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
            <span className="text-gray-900">{story.accessLevel}</span>
          </div>
        </div>
      </div>

      {/* Footer with LLM metrics */}
      <ResultFooter
        tokensUsed={story.tokensUsed}
        cost={story.cost}
        model={story.modelName}
      />
    </div>
  );
}
