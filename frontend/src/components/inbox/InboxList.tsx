import { useInbox } from '@/api/hooks/useInbox';
import { Spinner } from '@/components/common/Spinner';
import { VideoItem } from './VideoItem';
import { Inbox, RefreshCw } from 'lucide-react';
import { useSettings, type ProcessingMode } from '@/contexts/SettingsContext';

interface InboxListProps {
  onProcessVideo: (filename: string, mode: ProcessingMode) => void;
}

export function InboxList({ onProcessVideo }: InboxListProps) {
  const { data: files, isLoading, isError, refetch, isFetching } = useInbox();
  const { processingMode, setProcessingMode } = useSettings();

  return (
    <aside className="w-80 flex flex-col bg-white border-r border-gray-200">
      {/* Inbox Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <Inbox className="w-5 h-5 text-gray-400" />
          <h2 className="font-medium text-gray-900">Inbox</h2>
          {files && (
            <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
              {files.length}
            </span>
          )}
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Current mode indicator */}
      <div className="px-4 py-2 bg-gray-50 border-b border-gray-100">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span>Режим по умолчанию:</span>
          <span className={`font-medium ${processingMode === 'step' ? 'text-blue-600' : 'text-emerald-600'}`}>
            {processingMode === 'step' ? 'Пошагово' : 'Авто'}
          </span>
        </div>
      </div>

      {/* Inbox Files */}
      <div className="flex-1 p-4 space-y-3 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Spinner />
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center h-full text-red-500">
            <p className="text-sm">Ошибка загрузки</p>
          </div>
        ) : files && files.length > 0 ? (
          files.map((filename) => (
            <VideoItem
              key={filename}
              filename={filename}
              defaultMode={processingMode}
              onProcess={onProcessVideo}
              onModeChange={setProcessingMode}
            />
          ))
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <Inbox className="w-12 h-12 mb-3 opacity-40" />
            <p className="text-sm">Нет файлов для обработки</p>
          </div>
        )}
      </div>
    </aside>
  );
}
