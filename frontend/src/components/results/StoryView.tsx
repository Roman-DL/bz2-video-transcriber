import type { Story } from '@/api/types';
import { Badge } from '@/components/common/Badge';

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

function formatSpeed(speed: string): { text: string; color: string } {
  switch (speed) {
    case 'быстро':
      return { text: '< 3 лет', color: 'text-green-600' };
    case 'средне':
      return { text: '3-7 лет', color: 'text-blue-600' };
    case 'долго':
      return { text: '7-15 лет', color: 'text-yellow-600' };
    case 'очень долго':
      return { text: '> 15 лет', color: 'text-red-600' };
    default:
      return { text: speed, color: 'text-gray-600' };
  }
}

function formatBusinessFormat(format: string): string {
  switch (format) {
    case 'клуб':
      return 'Клубный формат';
    case 'онлайн':
      return 'Онлайн';
    case 'гибрид':
      return 'Гибрид';
    default:
      return format;
  }
}

export function StoryView({ story }: StoryViewProps) {
  const speed = formatSpeed(story.speed);

  return (
    <div className="space-y-6">
      {/* Header with main insight */}
      <div className="border-l-4 border-indigo-500 pl-4 py-2">
        <div className="text-sm text-gray-500 mb-1">
          {story.current_status}: {story.names}
        </div>
        {story.main_insight && (
          <div className="text-lg font-medium text-gray-900">
            {story.main_insight}
          </div>
        )}
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-gray-50 rounded-lg">
        <div>
          <div className="text-xs text-gray-500 uppercase">Время в бизнесе</div>
          <div className="font-medium">{story.time_in_business || '—'}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase">До статуса</div>
          <div className={`font-medium ${speed.color}`}>
            {story.time_to_status || '—'} ({speed.text})
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase">Формат</div>
          <div className="font-medium">{formatBusinessFormat(story.business_format)}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase">Особенности</div>
          <div className="flex flex-wrap gap-1">
            {story.is_family && <Badge variant="info">Семья</Badge>}
            {story.had_stagnation && (
              <Badge variant="warning">
                Стагнация {story.stagnation_years > 0 && `${story.stagnation_years} г.`}
              </Badge>
            )}
            {story.had_restart && <Badge variant="error">Рестарт</Badge>}
          </div>
        </div>
      </div>

      {/* Mentor & Pattern */}
      {(story.mentor || story.key_pattern) && (
        <div className="flex flex-wrap gap-4 text-sm">
          {story.mentor && (
            <div>
              <span className="text-gray-500">Наставник:</span>{' '}
              <span className="font-medium">{story.mentor}</span>
            </div>
          )}
          {story.key_pattern && (
            <div>
              <span className="text-gray-500">Паттерн:</span>{' '}
              <span className="font-medium">{story.key_pattern}</span>
            </div>
          )}
        </div>
      )}

      {/* 8 blocks */}
      <div className="space-y-4">
        {story.blocks.map((block) => (
          <div key={block.block_number} className="border rounded-lg overflow-hidden">
            <div className="bg-gray-100 px-4 py-2 border-b">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 bg-indigo-500 text-white rounded-full flex items-center justify-center text-sm font-medium">
                  {block.block_number}
                </span>
                <span className="font-medium text-gray-900">
                  {block.block_name || BLOCK_NAMES[block.block_number]}
                </span>
              </div>
            </div>
            <div className="p-4 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
              {block.content}
            </div>
          </div>
        ))}
      </div>

      {/* Metadata footer */}
      <div className="pt-4 border-t border-gray-100">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div>
            <span className="text-gray-500">Уровень доступа:</span>{' '}
            <span className="text-gray-900">{story.access_level}</span>
          </div>
          {story.tags.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Теги:</span>
              <div className="flex flex-wrap gap-1">
                {story.tags.map((tag) => (
                  <Badge key={tag} variant="default">{tag}</Badge>
                ))}
              </div>
            </div>
          )}
          {story.related.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Связанные:</span>
              <div className="flex flex-wrap gap-1">
                {story.related.map((rel) => (
                  <Badge key={rel} variant="info">{rel}</Badge>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="text-xs text-gray-500 mt-2">
          Модель: <span className="font-mono">{story.model_name}</span>
        </div>
      </div>
    </div>
  );
}
