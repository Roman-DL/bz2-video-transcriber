import type { Story } from '@/api/types';

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
    <div className="space-y-4">
      <div className="text-xs text-gray-500 mb-2">
        Модель: <span className="font-mono">{story.model_name}</span>
      </div>

      {/* Story text as markdown */}
      <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
        {markdownText}
      </div>

      {/* Metadata footer */}
      <div className="pt-4 border-t border-gray-100">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div>
            <span className="text-gray-500">Уровень доступа:</span>{' '}
            <span className="text-gray-900">{story.access_level}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
