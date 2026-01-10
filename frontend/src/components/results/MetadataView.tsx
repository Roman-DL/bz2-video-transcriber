import type { VideoMetadata } from '@/api/types';

interface MetadataViewProps {
  metadata: VideoMetadata;
}

export function MetadataView({ metadata }: MetadataViewProps) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
      <dt className="text-gray-500">Дата</dt>
      <dd className="text-gray-900">{metadata.date}</dd>

      <dt className="text-gray-500">Мероприятие</dt>
      <dd className="text-gray-900">{metadata.event_type}</dd>

      {metadata.stream && (
        <>
          <dt className="text-gray-500">Часть</dt>
          <dd className="text-gray-900">{metadata.stream}</dd>
        </>
      )}

      <dt className="text-gray-500">Тема</dt>
      <dd className="text-gray-900">{metadata.title}</dd>

      <dt className="text-gray-500">Спикер</dt>
      <dd className="text-gray-900">{metadata.speaker}</dd>

      <dt className="text-gray-500">Video ID</dt>
      <dd className="text-gray-900 font-mono text-xs">{metadata.video_id}</dd>
    </dl>
  );
}
