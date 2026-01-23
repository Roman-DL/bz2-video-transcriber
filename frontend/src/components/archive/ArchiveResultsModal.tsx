import { useState, useEffect, useMemo, useCallback } from 'react';
import { Modal } from '@/components/common/Modal';
import { Spinner } from '@/components/common/Spinner';
import { Button } from '@/components/common/Button';
import { MetadataView } from '@/components/results/MetadataView';
import {
  RawTranscriptView,
  CleanedTranscriptView,
} from '@/components/results/TranscriptView';
import { ChunksView } from '@/components/results/ChunksView';
import { StoryView } from '@/components/results/StoryView';
import { LongreadView } from '@/components/results/LongreadView';
import { SummaryView } from '@/components/results/SummaryView';
import { SlidesResultView } from '@/components/results/SlidesResultView';
import { StatisticsView } from '@/components/results/StatisticsView';
import { useArchiveResults } from '@/api/hooks/useArchive';
import { formatTime } from '@/utils/formatUtils';
import {
  AlertCircle,
  FileText,
  FileAudio,
  Sparkles,
  Layers,
  Clock,
  BookOpen,
  Heart,
  ListChecks,
  Presentation,
  BarChart3,
} from 'lucide-react';
import type { ArchiveItemWithPath, PipelineResults } from '@/api/types';

interface ArchiveResultsModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: ArchiveItemWithPath | null;
}

type ResultTab =
  | 'metadata'
  | 'rawTranscript'
  | 'cleanedTranscript'
  | 'slides'
  | 'longread'
  | 'summary'
  | 'story'
  | 'chunks'
  | 'statistics';

const TAB_ICONS: Record<ResultTab, React.ComponentType<{ className?: string }>> = {
  metadata: FileText,
  rawTranscript: FileAudio,
  cleanedTranscript: Sparkles,
  slides: Presentation,
  longread: BookOpen,
  summary: ListChecks,
  story: Heart,
  chunks: Layers,
  statistics: BarChart3,
};

const TAB_LABELS: Record<ResultTab, string> = {
  metadata: 'Метаданные',
  rawTranscript: 'Транскрипт',
  cleanedTranscript: 'Очистка',
  slides: 'Слайды',
  longread: 'Лонгрид',
  summary: 'Конспект',
  story: 'История',
  chunks: 'Чанки',
  statistics: 'Статистика',
};

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h > 0
    ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    : `${m}:${s.toString().padStart(2, '0')}`;
}

function getAvailableTabs(results: PipelineResults): ResultTab[] {
  const tabs: ResultTab[] = [];
  if (results.metadata) tabs.push('metadata');
  if (results.rawTranscript) tabs.push('rawTranscript');
  if (results.cleanedTranscript) tabs.push('cleanedTranscript');
  if (results.slidesExtraction) tabs.push('slides');
  if (results.longread) tabs.push('longread');
  if (results.summary) tabs.push('summary');
  if (results.story) tabs.push('story');
  if (results.chunks) tabs.push('chunks');
  // Always show statistics if we have any processing data
  if (results.rawTranscript || results.cleanedTranscript) {
    tabs.push('statistics');
  }
  return tabs;
}

export function ArchiveResultsModal({
  isOpen,
  onClose,
  item,
}: ArchiveResultsModalProps) {
  const [activeTab, setActiveTab] = useState<ResultTab>('metadata');
  const [showCleanedDiff, setShowCleanedDiff] = useState(false);
  const [showLongreadDiff, setShowLongreadDiff] = useState(false);

  const { data, isLoading, isError } = useArchiveResults(
    item?.year ?? null,
    item?.event_type ?? null,
    item?.mid_folder ?? null,
    item?.topicFolder ?? null
  );

  const title = item?.title || 'Результаты обработки';
  const results = data?.data;

  // Get available tabs (memoized to avoid re-creating on every render)
  const availableTabs = useMemo(() => {
    return results ? getAvailableTabs(results) : [];
  }, [results]);

  // Wrapper that resets diff mode when switching tabs
  const switchTab = useCallback((tab: ResultTab) => {
    setActiveTab(tab);
    setShowCleanedDiff(false);
    setShowLongreadDiff(false);
  }, []);

  // Auto-select preferred tab when data loads (valid sync pattern)
  useEffect(() => {
    if (availableTabs.length > 0 && !availableTabs.includes(activeTab)) {
      // Select summary/longread/story if available, otherwise first tab
      const preferredTab = availableTabs.find(t =>
        t === 'summary' || t === 'longread' || t === 'story'
      );
      // eslint-disable-next-line react-hooks/set-state-in-effect
      switchTab(preferredTab || availableTabs[0]);
    }
  }, [availableTabs, activeTab, switchTab]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="2xl">
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Spinner />
        </div>
      )}

      {isError && (
        <div className="text-center py-8 text-red-600">
          Ошибка загрузки результатов
        </div>
      )}

      {data && !data.available && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-amber-700">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">Данные недоступны</span>
          </div>
          <p className="mt-1 text-sm text-amber-600">
            {data.message ||
              'Результаты обработки недоступны для этого файла.'}
          </p>
        </div>
      )}

      {results && availableTabs.length > 0 && (
        <div className="flex flex-col h-[70vh]">
          {/* Tab bar */}
          <div className="flex gap-0.5 py-2 border-b border-gray-200 shrink-0 overflow-x-auto">
            {availableTabs.map(tab => {
              const Icon = TAB_ICONS[tab];
              return (
                <button
                  key={tab}
                  className={`flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-all ${
                    activeTab === tab
                      ? 'text-blue-600 bg-blue-50 border border-blue-200'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50 border border-transparent'
                  }`}
                  onClick={() => switchTab(tab)}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{TAB_LABELS[tab]}</span>
                </button>
              );
            })}
          </div>

          {/* Content area */}
          <div className="flex-1 py-3 overflow-y-auto min-h-0">
            {activeTab === 'metadata' && results.metadata && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                  <h3 className="text-sm font-semibold text-gray-900">Метаданные</h3>
                  {results.metadata.duration_seconds && (
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Clock className="w-3 h-3" />
                      {formatDuration(results.metadata.duration_seconds)}
                    </div>
                  )}
                </div>
                <div className="p-4 flex-1 overflow-y-auto">
                  <MetadataView metadata={results.metadata} />
                </div>
              </div>
            )}

            {activeTab === 'rawTranscript' && results.rawTranscript && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                  <h3 className="text-sm font-semibold text-gray-900">Сырая транскрипция</h3>
                  {results.rawTranscript.processing_time_sec !== undefined && (
                    <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                      {formatTime(results.rawTranscript.processing_time_sec)}
                    </span>
                  )}
                </div>
                <div className="p-4 flex-1 overflow-hidden min-h-0">
                  <RawTranscriptView
                    transcript={results.rawTranscript}
                    displayText={results.displayText || results.rawTranscript.full_text}
                  />
                </div>
              </div>
            )}

            {activeTab === 'cleanedTranscript' && results.cleanedTranscript && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                {!showCleanedDiff && (
                  <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                    <h3 className="text-sm font-semibold text-gray-900">Очищенная транскрипция</h3>
                    {results.cleanedTranscript.processing_time_sec !== undefined && (
                      <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                        {formatTime(results.cleanedTranscript.processing_time_sec)}
                      </span>
                    )}
                  </div>
                )}
                <div className={showCleanedDiff ? 'flex-1 min-h-0' : 'p-4 flex-1 overflow-hidden min-h-0'}>
                  <CleanedTranscriptView
                    transcript={results.cleanedTranscript}
                    rawText={results.displayText}
                    showDiff={showCleanedDiff}
                    onToggleDiff={() => setShowCleanedDiff(!showCleanedDiff)}
                  />
                </div>
              </div>
            )}

            {activeTab === 'slides' && results.slidesExtraction && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                  <h3 className="text-sm font-semibold text-gray-900">Извлечённый текст слайдов</h3>
                  {results.slidesExtraction.processing_time_sec !== undefined && (
                    <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                      {formatTime(results.slidesExtraction.processing_time_sec)}
                    </span>
                  )}
                </div>
                <div className="p-4 flex-1 overflow-y-auto">
                  <SlidesResultView slidesExtraction={results.slidesExtraction} />
                </div>
              </div>
            )}

            {activeTab === 'longread' && results.longread && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                {!showLongreadDiff && (
                  <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                    <h3 className="text-sm font-semibold text-gray-900">Лонгрид</h3>
                    {results.longread.processing_time_sec !== undefined && (
                      <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                        {formatTime(results.longread.processing_time_sec)}
                      </span>
                    )}
                  </div>
                )}
                <div className={showLongreadDiff ? 'flex-1 min-h-0' : 'p-4 flex-1 overflow-y-auto'}>
                  <LongreadView
                    longread={results.longread}
                    cleanedText={results.cleanedTranscript?.text}
                    cleanedChars={results.cleanedTranscript?.cleaned_length}
                    showDiff={showLongreadDiff}
                    onToggleDiff={() => setShowLongreadDiff(!showLongreadDiff)}
                  />
                </div>
              </div>
            )}

            {activeTab === 'summary' && results.summary && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                  <h3 className="text-sm font-semibold text-gray-900">Конспект</h3>
                  {results.summary.processing_time_sec !== undefined && (
                    <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                      {formatTime(results.summary.processing_time_sec)}
                    </span>
                  )}
                </div>
                <div className="p-4 flex-1 overflow-y-auto">
                  <SummaryView summary={results.summary} />
                </div>
              </div>
            )}

            {activeTab === 'story' && results.story && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                  <h3 className="text-sm font-semibold text-gray-900">Лидерская история</h3>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span>{results.story.total_blocks} блоков</span>
                    <span>{results.story.speed}</span>
                  </div>
                </div>
                <div className="p-4 flex-1 overflow-y-auto">
                  <StoryView story={results.story} />
                </div>
              </div>
            )}

            {activeTab === 'chunks' && results.chunks && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                  <h3 className="text-sm font-semibold text-gray-900">Чанки</h3>
                </div>
                <div className="p-4 flex-1 overflow-y-auto">
                  <ChunksView chunks={results.chunks} />
                </div>
              </div>
            )}

            {activeTab === 'statistics' && (
              <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                  <h3 className="text-sm font-semibold text-gray-900">Статистика обработки</h3>
                </div>
                <div className="p-4 flex-1 overflow-hidden min-h-0">
                  <StatisticsView
                    data={{
                      rawTranscript: results.rawTranscript,
                      cleanedTranscript: results.cleanedTranscript,
                      slidesExtraction: results.slidesExtraction,
                      longread: results.longread,
                      summary: results.summary,
                      story: results.story,
                      chunks: results.chunks,
                      contentType: results.contentType,
                    }}
                    processedAt={results.createdAt}
                    showFiles={false}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Close button */}
      <div className="flex justify-end pt-4 border-t border-gray-200 mt-4">
        <Button onClick={onClose}>Закрыть</Button>
      </div>
    </Modal>
  );
}
