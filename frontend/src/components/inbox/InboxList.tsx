import { useInbox } from '@/api/hooks/useInbox';
import { Card, CardContent, CardHeader } from '@/components/common/Card';
import { Spinner } from '@/components/common/Spinner';
import { VideoItem } from './VideoItem';
import { Inbox, RefreshCw } from 'lucide-react';
import { Button } from '@/components/common/Button';

interface InboxListProps {
  onProcessVideo: (filename: string) => void;
}

export function InboxList({ onProcessVideo }: InboxListProps) {
  const { data: files, isLoading, isError, refetch, isFetching } = useInbox();

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Inbox className="w-5 h-5 text-gray-500" />
            <h2 className="text-lg font-medium text-gray-900">Inbox</h2>
            {files && (
              <span className="text-sm text-gray-500">
                ({files.length} видео)
              </span>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            <RefreshCw
              className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`}
            />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Spinner />
          </div>
        ) : isError ? (
          <div className="text-center py-8 text-red-600">
            Ошибка загрузки списка видео
          </div>
        ) : files && files.length > 0 ? (
          <div className="divide-y divide-gray-100">
            {files.map((filename) => (
              <VideoItem
                key={filename}
                filename={filename}
                onProcess={onProcessVideo}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            Inbox пуст — добавьте видео для обработки
          </div>
        )}
      </CardContent>
    </Card>
  );
}
