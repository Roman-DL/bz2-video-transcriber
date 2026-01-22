import { useState } from 'react';
import type { TranscriptChunks } from '@/api/types';
import { Badge } from '@/components/common/Badge';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { formatNumber } from '@/utils/formatUtils';

interface ChunksViewProps {
  chunks: TranscriptChunks;
}

export function ChunksView({ chunks }: ChunksViewProps) {
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null);

  return (
    <div className="h-full flex flex-col">
      {/* Header with metrics */}
      <div className="text-xs text-gray-500 mb-3 px-4 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          {chunks.total_chunks} чанков
        </span>
        {chunks.total_tokens !== undefined && (
          <span>
            {formatNumber(chunks.total_tokens)} токенов
          </span>
        )}
        <span className="ml-auto font-mono text-gray-400">
          {chunks.model_name}
        </span>
      </div>

      {/* Chunks list */}
      <div className="flex-1 overflow-y-auto divide-y divide-gray-100 -mx-4 min-h-0">
        {chunks.chunks.map((chunk) => (
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
                    {chunk.topic}
                  </span>
                  <span className="text-xs text-gray-400 ml-auto flex-shrink-0">
                    {formatNumber(chunk.word_count)} слов
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
