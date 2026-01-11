import { useState, useMemo } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { RawTranscript, CleanedTranscript } from '@/api/types';

interface RawTranscriptViewProps {
  transcript: RawTranscript;
}

export function RawTranscriptView({ transcript }: RawTranscriptViewProps) {
  return (
    <div>
      <div className="text-xs text-gray-500 mb-2">
        Модель: <span className="font-mono">{transcript.whisper_model}</span>
      </div>
      <div className="max-h-64 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
        {transcript.text_with_timestamps}
      </div>
    </div>
  );
}

interface CleanedTranscriptViewProps {
  transcript: CleanedTranscript;
}

export function CleanedTranscriptView({ transcript }: CleanedTranscriptViewProps) {
  const [expanded, setExpanded] = useState(false);

  const groupedCorrections = useMemo(() => {
    const counts = new Map<string, number>();
    transcript.corrections_made.forEach((c) =>
      counts.set(c, (counts.get(c) || 0) + 1)
    );
    return Array.from(counts.entries())
      .map(([text, count]) => ({ text, count }))
      .sort((a, b) => b.count - a.count);
  }, [transcript.corrections_made]);

  const totalReplacements = transcript.corrections_made.length;
  const uniqueReplacements = groupedCorrections.length;

  return (
    <div>
      <div className="max-h-64 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
        {transcript.text}
      </div>
      {totalReplacements > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors cursor-pointer"
          >
            {expanded ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
            <span>
              Замены глоссария ({totalReplacements} замен, {uniqueReplacements}{' '}
              уникальных)
            </span>
          </button>
          {expanded && (
            <ul className="mt-2 text-xs text-gray-600 space-y-1 max-h-48 overflow-y-auto">
              {groupedCorrections.map((c, i) => (
                <li key={i}>
                  • {c.text}
                  {c.count > 1 && (
                    <span className="text-gray-400 ml-1">(×{c.count})</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
