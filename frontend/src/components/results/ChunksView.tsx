import { useMemo, useState } from 'react';
import type { TranscriptChunks } from '@/api/types';
import { Badge } from '@/components/common/Badge';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { formatNumber } from '@/utils/formatUtils';

interface ChunksViewProps {
  chunks: TranscriptChunks;
  description?: string;
  shortDescription?: string;
}

export function ChunksView({ chunks, description, shortDescription }: ChunksViewProps) {
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null);

  // Build display topics with (N/M) suffix for split sections
  const displayTopics = useMemo(() => {
    const topicCounts = new Map<string, number>();
    chunks.chunks.forEach(c => topicCounts.set(c.topic, (topicCounts.get(c.topic) || 0) + 1));
    const topicSeen = new Map<string, number>();

    return chunks.chunks.map(chunk => {
      const totalParts = topicCounts.get(chunk.topic) || 1;
      const seen = (topicSeen.get(chunk.topic) || 0) + 1;
      topicSeen.set(chunk.topic, seen);
      return totalParts > 1
        ? `${chunk.topic} (${seen}/${totalParts})`
        : chunk.topic;
    });
  }, [chunks.chunks]);

  return (
    <div className="h-full flex flex-col">
      {/* Описания */}
      {(shortDescription || description) && (
        <div className="mb-3 shrink-0 space-y-2">
          {shortDescription && (
            <div className="bg-blue-50 border border-blue-100 rounded-lg px-3.5 py-2.5">
              <span className="text-[10px] font-semibold text-blue-400 uppercase tracking-wide">Краткое описание</span>
              <p className="text-sm font-medium text-gray-900 mt-0.5">{shortDescription}</p>
            </div>
          )}
          {description && (
            <div className="bg-gray-50 border border-gray-150 rounded-lg px-3.5 py-2.5">
              <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Описание</span>
              <p className="text-xs text-gray-600 leading-relaxed mt-0.5">{description}</p>
            </div>
          )}
        </div>
      )}

      {/* Header with metrics */}
      <div className="text-xs text-gray-500 mb-3 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          {chunks.totalChunks} чанков
        </span>
        {chunks.totalTokens !== undefined && (
          <span>
            {formatNumber(chunks.totalTokens)} токенов
          </span>
        )}
        {chunks.avgChunkSize !== undefined && (
          <span>
            ~{chunks.avgChunkSize} слов/чанк
          </span>
        )}
        <span className="ml-auto font-mono text-gray-400">
          {chunks.modelName}
        </span>
      </div>

      {/* Chunks list */}
      <div className="flex-1 overflow-y-auto divide-y divide-gray-100 -mx-4 min-h-0">
        {chunks.chunks.map((chunk, i) => (
          <div key={chunk.id} className="px-4 py-3">
            <button
              className="w-full flex items-start gap-2 text-left"
              onClick={() =>
                setExpandedChunk(expandedChunk === chunk.id ? null : chunk.id)
              }
            >
              {expandedChunk === chunk.id ? (
                <ChevronDown className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <Badge variant="info">#{chunk.index}</Badge>
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {displayTopics[i]}
                  </span>
                  <span className="text-xs text-gray-400 ml-auto flex-shrink-0">
                    {formatNumber(chunk.wordCount)} слов
                  </span>
                </div>
              </div>
            </button>
            {expandedChunk === chunk.id && (
              <div className="mt-2 ml-6 text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 rounded-lg p-3 max-h-80 overflow-y-auto">
                {chunk.text}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
