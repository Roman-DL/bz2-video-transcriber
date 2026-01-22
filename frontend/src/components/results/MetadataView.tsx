import type { VideoMetadata } from '@/api/types';

interface MetadataViewProps {
  metadata: VideoMetadata;
}

export function MetadataView({ metadata }: MetadataViewProps) {
  return (
    <dl className="space-y-2.5 text-sm max-w-md">
      <div className="flex gap-4">
        <dt className="text-gray-500 w-28 shrink-0">Дата</dt>
        <dd className="text-gray-900 font-medium">{metadata.date}</dd>
      </div>

      <div className="flex gap-4">
        <dt className="text-gray-500 w-28 shrink-0">Мероприятие</dt>
        <dd className="text-gray-900 font-medium">{metadata.event_type}</dd>
      </div>

      {metadata.stream && (
        <div className="flex gap-4">
          <dt className="text-gray-500 w-28 shrink-0">Часть</dt>
          <dd className="text-gray-900 font-medium">{metadata.stream}</dd>
        </div>
      )}

      <div className="flex gap-4">
        <dt className="text-gray-500 w-28 shrink-0">Тема</dt>
        <dd className="text-gray-900 font-medium">{metadata.title}</dd>
      </div>

      <div className="flex gap-4">
        <dt className="text-gray-500 w-28 shrink-0">Спикер</dt>
        <dd className="text-gray-900 font-medium">{metadata.speaker}</dd>
      </div>

      <div className="flex gap-4">
        <dt className="text-gray-500 w-28 shrink-0">Video ID</dt>
        <dd className="text-gray-900 font-mono text-xs">{metadata.video_id}</dd>
      </div>

      {metadata.content_type && (
        <div className="flex gap-4">
          <dt className="text-gray-500 w-28 shrink-0">Тип контента</dt>
          <dd className="text-gray-900 font-medium">
            {metadata.content_type === 'educational' ? 'Обучающий' : 'Лидерская история'}
          </dd>
        </div>
      )}

      {metadata.event_category && (
        <div className="flex gap-4">
          <dt className="text-gray-500 w-28 shrink-0">Категория</dt>
          <dd className="text-gray-900 font-medium">
            {metadata.event_category === 'regular' ? 'Регулярное' : 'Выездное'}
          </dd>
        </div>
      )}
    </dl>
  );
}
