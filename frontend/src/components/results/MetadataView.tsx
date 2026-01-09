import type { VideoMetadata } from '@/api/types';
import { Card, CardContent, CardHeader } from '@/components/common/Card';
import { FileText } from 'lucide-react';

interface MetadataViewProps {
  metadata: VideoMetadata;
}

export function MetadataView({ metadata }: MetadataViewProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-gray-500" />
          <h3 className="text-sm font-medium text-gray-900">Метаданные</h3>
        </div>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500">Дата</dt>
          <dd className="text-gray-900">{metadata.date}</dd>

          <dt className="text-gray-500">Тип события</dt>
          <dd className="text-gray-900">{metadata.event_type}</dd>

          <dt className="text-gray-500">Поток</dt>
          <dd className="text-gray-900">{metadata.stream_full}</dd>

          <dt className="text-gray-500">Тема</dt>
          <dd className="text-gray-900">{metadata.title}</dd>

          <dt className="text-gray-500">Спикер</dt>
          <dd className="text-gray-900">{metadata.speaker}</dd>

          <dt className="text-gray-500">Video ID</dt>
          <dd className="text-gray-900 font-mono text-xs">
            {metadata.video_id}
          </dd>
        </dl>
      </CardContent>
    </Card>
  );
}
