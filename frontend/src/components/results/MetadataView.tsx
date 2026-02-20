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
        <dd className="text-gray-900 font-medium">{metadata.eventType}</dd>
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
        <dd className="text-gray-900 font-mono text-xs">{metadata.videoId}</dd>
      </div>

      {metadata.contentType && (
        <div className="flex gap-4">
          <dt className="text-gray-500 w-28 shrink-0">Тип контента</dt>
          <dd className="text-gray-900 font-medium">
            {metadata.contentType === 'educational' ? 'Обучающий' : 'Лидерская история'}
          </dd>
        </div>
      )}

      {metadata.eventCategory && (
        <div className="flex gap-4">
          <dt className="text-gray-500 w-28 shrink-0">Категория</dt>
          <dd className="text-gray-900 font-medium">
            {metadata.eventCategory === 'regular' ? 'Регулярное' : 'Выездное'}
          </dd>
        </div>
      )}

      {metadata.speakerInfo && (metadata.speakerInfo.namedSpeakers.length > 0 || metadata.speakerInfo.anonymousSpeakers.length > 0) && (
        <>
          <div className="border-t border-gray-100 my-3" />
          <div className="flex gap-4">
            <dt className="text-gray-500 w-28 shrink-0">Спикеры</dt>
            <dd className="text-gray-900 font-medium">
              <div className="flex flex-col gap-1">
                {metadata.speakerInfo.namedSpeakers.map((name) => (
                  <span key={name}>{name}</span>
                ))}
                {metadata.speakerInfo.anonymousSpeakers.length > 0 && (
                  <span className="text-gray-500 text-xs">
                    + {metadata.speakerInfo.anonymousSpeakers.length} анонимных
                  </span>
                )}
              </div>
            </dd>
          </div>
          <div className="flex gap-4">
            <dt className="text-gray-500 w-28 shrink-0">Сценарий</dt>
            <dd className="text-gray-900 font-medium">{metadata.speakerInfo.scenario}</dd>
          </div>
        </>
      )}
    </dl>
  );
}
