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
import { StoryView } from '@/components/results/StoryView';
import { useArchiveResults } from '@/api/hooks/useArchive';
import { AlertCircle, FileText, Zap, Layers, Clock, BookOpen, Users } from 'lucide-react';
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
  | 'longread'
  | 'summary'
  | 'story';

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h > 0
    ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    : `${m}:${s.toString().padStart(2, '0')}`;
}

/**
 * Format any object as readable text.
 * Handles arrays, nested objects, and primitives.
 */
function formatObjectAsText(obj: Record<string, unknown>, indent = 0): string {
  const lines: string[] = [];
  const prefix = '  '.repeat(indent);

  for (const [key, value] of Object.entries(obj)) {
    // Skip internal fields
    if (['video_id', 'model_name', 'access_level'].includes(key)) continue;

    const label = formatLabel(key);

    if (value === null || value === undefined || value === '') {
      continue;
    } else if (Array.isArray(value)) {
      if (value.length === 0) continue;
      // Check if array contains objects (like sections)
      if (typeof value[0] === 'object' && value[0] !== null) {
        lines.push(`${prefix}## ${label}`);
        lines.push('');
        for (const item of value) {
          if (typeof item === 'object' && item !== null) {
            const itemObj = item as Record<string, unknown>;
            // Handle section-like objects
            if ('title' in itemObj && 'content' in itemObj) {
              lines.push(`${prefix}### ${itemObj.title}`);
              lines.push('');
              lines.push(`${prefix}${itemObj.content}`);
              lines.push('');
            } else {
              lines.push(formatObjectAsText(itemObj, indent + 1));
            }
          }
        }
      } else {
        // Simple array of strings
        lines.push(`${prefix}## ${label}`);
        lines.push('');
        for (const item of value) {
          lines.push(`${prefix}• ${item}`);
        }
        lines.push('');
      }
    } else if (typeof value === 'object') {
      lines.push(`${prefix}## ${label}`);
      lines.push('');
      lines.push(formatObjectAsText(value as Record<string, unknown>, indent + 1));
    } else {
      // String or number - main content
      if (key === 'introduction' || key === 'conclusion' || key === 'essence' ||
          key === 'summary' || key === 'insight' || key === 'content') {
        if (label && key !== 'content') {
          lines.push(`${prefix}## ${label}`);
          lines.push('');
        }
        lines.push(`${prefix}${value}`);
        lines.push('');
      } else if (key === 'title' || key === 'speaker' || key === 'date') {
        // Skip metadata fields shown elsewhere
        continue;
      } else {
        lines.push(`${prefix}**${label}:** ${value}`);
        lines.push('');
      }
    }
  }

  return lines.join('\n');
}

/**
 * Convert snake_case key to readable label.
 */
function formatLabel(key: string): string {
  const labels: Record<string, string> = {
    introduction: 'Вступление',
    sections: 'Разделы',
    conclusion: 'Заключение',
    essence: 'Суть темы',
    key_concepts: 'Ключевые концепции',
    practical_tools: 'Инструменты и методы',
    quotes: 'Ключевые цитаты',
    insight: 'Главный инсайт',
    actions: 'Что сделать',
    summary: 'Краткое содержание',
    key_points: 'Ключевые тезисы',
    recommendations: 'Рекомендации',
    target_audience: 'Целевая аудитория',
    questions_answered: 'На какие вопросы отвечает',
    section: 'Раздел',
    subsection: 'Подраздел',
    tags: 'Теги',
  };
  return labels[key] || key.replace(/_/g, ' ');
}

export function ArchiveResultsModal({
  isOpen,
  onClose,
  item,
}: ArchiveResultsModalProps) {
  const [expandedBlocks, setExpandedBlocks] = useState<Set<BlockType>>(
    new Set(['summary', 'longread', 'story'])
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
  const results = data?.data;

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

      {results && (
        <div className="space-y-3 max-h-[70vh] overflow-y-auto">
          {/* Metadata */}
          {results.metadata && (
            <CollapsibleCard
              title="Метаданные"
              icon={FileText}
              stats={
                results.metadata.duration_seconds ? (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {formatDuration(results.metadata.duration_seconds)}
                  </span>
                ) : null
              }
              expanded={expandedBlocks.has('metadata')}
              onToggle={() => toggleBlock('metadata')}
            >
              <MetadataView metadata={results.metadata} />
            </CollapsibleCard>
          )}

          {/* Raw Transcript */}
          {results.raw_transcript && (
            <CollapsibleCard
              title="Сырая транскрипция"
              icon={FileText}
              stats={
                <>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {formatDuration(results.raw_transcript.duration_seconds)}
                  </span>
                  <span>
                    {results.raw_transcript.segments.length} сегментов
                  </span>
                </>
              }
              expanded={expandedBlocks.has('rawTranscript')}
              onToggle={() => toggleBlock('rawTranscript')}
            >
              <RawTranscriptView
                transcript={results.raw_transcript}
                displayText={results.display_text || results.raw_transcript.full_text}
              />
            </CollapsibleCard>
          )}

          {/* Cleaned Transcript */}
          {results.cleaned_transcript && (
            <CollapsibleCard
              title="Очищенная транскрипция"
              icon={Zap}
              stats={
                <>
                  <span>
                    {results.cleaned_transcript.cleaned_length.toLocaleString()}{' '}
                    симв.
                  </span>
                  <span>
                    -
                    {Math.round(
                      ((results.cleaned_transcript.original_length -
                        results.cleaned_transcript.cleaned_length) /
                        results.cleaned_transcript.original_length) *
                        100
                    )}
                    %
                  </span>
                </>
              }
              expanded={expandedBlocks.has('cleanedTranscript')}
              onToggle={() => toggleBlock('cleanedTranscript')}
            >
              <CleanedTranscriptView transcript={results.cleaned_transcript} />
            </CollapsibleCard>
          )}

          {/* Chunks */}
          {results.chunks && (
            <CollapsibleCard
              title="Семантические чанки"
              icon={Layers}
              stats={
                <>
                  <span>{results.chunks.total_chunks} чанков</span>
                  <span>~{results.chunks.avg_chunk_size} слов/чанк</span>
                </>
              }
              expanded={expandedBlocks.has('chunks')}
              onToggle={() => toggleBlock('chunks')}
            >
              <ChunksView chunks={results.chunks} />
            </CollapsibleCard>
          )}

          {/* Longread (new pipeline) */}
          {results.longread && (
            <CollapsibleCard
              title="Лонгрид"
              icon={BookOpen}
              expanded={expandedBlocks.has('longread')}
              onToggle={() => toggleBlock('longread')}
            >
              <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                {formatObjectAsText(results.longread)}
              </div>
            </CollapsibleCard>
          )}

          {/* Summary (any version) */}
          {results.summary && (
            <CollapsibleCard
              title="Конспект"
              icon={FileText}
              expanded={expandedBlocks.has('summary')}
              onToggle={() => toggleBlock('summary')}
            >
              <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
                {formatObjectAsText(results.summary)}
              </div>
            </CollapsibleCard>
          )}

          {/* Story (leadership content) */}
          {results.story && (
            <CollapsibleCard
              title="Лидерская история"
              icon={Users}
              stats={
                <>
                  <span>{results.story.total_blocks} блоков</span>
                  <span>{results.story.speed}</span>
                </>
              }
              expanded={expandedBlocks.has('story')}
              onToggle={() => toggleBlock('story')}
            >
              <StoryView story={results.story} />
            </CollapsibleCard>
          )}
        </div>
      )}

      {/* Close button */}
      <div className="flex justify-end pt-4 border-t border-gray-200 mt-4">
        <Button onClick={onClose}>Закрыть</Button>
      </div>
    </Modal>
  );
}
