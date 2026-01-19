import { useState } from 'react';
import { Modal } from '@/components/common/Modal';
import { CollapsibleCard } from '@/components/common/CollapsibleCard';
import { Spinner } from '@/components/common/Spinner';
import { Button } from '@/components/common/Button';
import { MetadataView } from '@/components/results/MetadataView';
import {
  RawTranscriptView,
  CleanedTranscriptView,
} from '@/components/results/TranscriptView';
import { ChunksView } from '@/components/results/ChunksView';
import { VideoSummaryView } from '@/components/results/VideoSummaryView';
import { useArchiveResults } from '@/api/hooks/useArchive';
import { AlertCircle, FileText, Zap, Layers, Clock } from 'lucide-react';
import type { ArchiveItemWithPath } from '@/api/types';

interface ArchiveResultsModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: ArchiveItemWithPath | null;
}

type BlockType =
  | 'metadata'
  | 'rawTranscript'
  | 'cleanedTranscript'
  | 'chunks'
  | 'summary';

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h > 0
    ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    : `${m}:${s.toString().padStart(2, '0')}`;
}

export function ArchiveResultsModal({
  isOpen,
  onClose,
  item,
}: ArchiveResultsModalProps) {
  const [expandedBlocks, setExpandedBlocks] = useState<Set<BlockType>>(
    new Set(['summary'])
  );

  const { data, isLoading, isError } = useArchiveResults(
    item?.year ?? null,
    item?.eventFolder ?? null,
    item?.topicFolder ?? null
  );

  const toggleBlock = (block: BlockType) => {
    setExpandedBlocks((prev) => {
      const next = new Set(prev);
      if (next.has(block)) {
        next.delete(block);
      } else {
        next.add(block);
      }
      return next;
    });
  };

  const title = item?.title || 'Результаты обработки';

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="xl">
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

      {data?.available && data.data && (
        <div className="space-y-3 max-h-[70vh] overflow-y-auto">
          {/* Metadata */}
          <CollapsibleCard
            title="Метаданные"
            icon={FileText}
            stats={
              data.data.metadata.duration_seconds ? (
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {formatDuration(data.data.metadata.duration_seconds)}
                </span>
              ) : null
            }
            expanded={expandedBlocks.has('metadata')}
            onToggle={() => toggleBlock('metadata')}
          >
            <MetadataView metadata={data.data.metadata} />
          </CollapsibleCard>

          {/* Raw Transcript */}
          <CollapsibleCard
            title="Сырая транскрипция"
            icon={FileText}
            stats={
              <>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {formatDuration(data.data.raw_transcript.duration_seconds)}
                </span>
                <span>
                  {data.data.raw_transcript.segments.length} сегментов
                </span>
              </>
            }
            expanded={expandedBlocks.has('rawTranscript')}
            onToggle={() => toggleBlock('rawTranscript')}
          >
            <RawTranscriptView
              transcript={data.data.raw_transcript}
              displayText={data.data.display_text}
            />
          </CollapsibleCard>

          {/* Cleaned Transcript */}
          <CollapsibleCard
            title="Очищенная транскрипция"
            icon={Zap}
            stats={
              <>
                <span>
                  {data.data.cleaned_transcript.cleaned_length.toLocaleString()}{' '}
                  симв.
                </span>
                <span>
                  -
                  {Math.round(
                    ((data.data.cleaned_transcript.original_length -
                      data.data.cleaned_transcript.cleaned_length) /
                      data.data.cleaned_transcript.original_length) *
                      100
                  )}
                  %
                </span>
              </>
            }
            expanded={expandedBlocks.has('cleanedTranscript')}
            onToggle={() => toggleBlock('cleanedTranscript')}
          >
            <CleanedTranscriptView transcript={data.data.cleaned_transcript} />
          </CollapsibleCard>

          {/* Chunks */}
          <CollapsibleCard
            title="Семантические чанки"
            icon={Layers}
            stats={
              <>
                <span>{data.data.chunks.total_chunks} чанков</span>
                <span>~{data.data.chunks.avg_chunk_size} слов/чанк</span>
              </>
            }
            expanded={expandedBlocks.has('chunks')}
            onToggle={() => toggleBlock('chunks')}
          >
            <ChunksView chunks={data.data.chunks} />
          </CollapsibleCard>

          {/* Summary */}
          <CollapsibleCard
            title="Саммари"
            icon={FileText}
            stats={
              <>
                <span>{data.data.summary.key_points.length} тезисов</span>
                <span>{data.data.summary.tags.length} тегов</span>
              </>
            }
            expanded={expandedBlocks.has('summary')}
            onToggle={() => toggleBlock('summary')}
          >
            <VideoSummaryView summary={data.data.summary} />
          </CollapsibleCard>
        </div>
      )}

      {/* Close button */}
      <div className="flex justify-end pt-4 border-t border-gray-200 mt-4">
        <Button onClick={onClose}>Закрыть</Button>
      </div>
    </Modal>
  );
}
