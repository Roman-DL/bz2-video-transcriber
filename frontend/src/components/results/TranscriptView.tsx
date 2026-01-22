import { Columns } from 'lucide-react';
import type { RawTranscript, CleanedTranscript } from '@/api/types';
import { formatNumber } from '@/utils/formatUtils';
import { ResultFooter } from '@/components/common/ResultFooter';
import { InlineDiffView } from '@/components/common/InlineDiffView';

interface RawTranscriptViewProps {
  transcript: RawTranscript;
  displayText: string;
}

/**
 * Formats confidence as percentage (0-1 → 0-100%).
 */
function formatConfidence(confidence: number | undefined): string | null {
  if (confidence === undefined) return null;
  const percent = Math.round(confidence * 100);
  return `${percent}%`;
}

export function RawTranscriptView({ transcript, displayText }: RawTranscriptViewProps) {
  const confidence = formatConfidence(transcript.confidence);

  return (
    <div className="h-full flex flex-col">
      {/* Header with metrics */}
      <div className="text-xs text-gray-500 mb-2 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          Язык: <span className="text-gray-700">{transcript.language}</span>
        </span>
        <span>
          {formatNumber(transcript.chars)} симв.
        </span>
        <span>
          {formatNumber(transcript.words)} слов
        </span>
        {confidence && (
          <span title="Уверенность транскрипции (avg_logprob)">
            Уверенность: <span className="text-gray-700">{confidence}</span>
          </span>
        )}
        <span className="ml-auto font-mono text-gray-400">
          {transcript.whisper_model}
        </span>
      </div>

      {/* Transcript text */}
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap break-words min-h-0">
        {displayText}
      </div>
    </div>
  );
}

interface CleanedTranscriptViewProps {
  transcript: CleanedTranscript;
  rawText?: string;
  showDiff?: boolean;
  onToggleDiff?: () => void;
}

export function CleanedTranscriptView({
  transcript,
  rawText,
  showDiff = false,
  onToggleDiff,
}: CleanedTranscriptViewProps) {
  // Calculate change percent correctly: negative = reduction, positive = increase
  const changePercent = transcript.original_length > 0
    ? ((transcript.cleaned_length - transcript.original_length) / transcript.original_length) * 100
    : 0;

  // Show diff view if enabled
  if (showDiff && rawText && onToggleDiff) {
    return (
      <InlineDiffView
        leftText={rawText}
        rightText={transcript.text}
        leftTitle="Транскрипт"
        rightTitle="Очистка"
        onClose={onToggleDiff}
      />
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with metrics */}
      <div className="text-xs text-gray-500 mb-2 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          {formatNumber(transcript.cleaned_length)} симв.
        </span>
        <span>
          {formatNumber(transcript.words)} слов
        </span>
        <span
          title="Изменение объёма после очистки"
          className={changePercent < 0 ? 'text-emerald-600' : 'text-amber-600'}
        >
          {changePercent > 0 ? '+' : ''}{changePercent.toFixed(1)}%
        </span>
      </div>

      {/* Diff button - only show if rawText available */}
      {rawText && onToggleDiff && (
        <div className="mb-2 shrink-0">
          <button
            onClick={onToggleDiff}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <Columns className="w-3.5 h-3.5" />
            Сравнить с транскриптом
          </button>
        </div>
      )}

      {/* Cleaned text */}
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap break-words min-h-0">
        {transcript.text}
      </div>

      {/* Footer with LLM metrics */}
      <ResultFooter
        tokensUsed={transcript.tokens_used}
        cost={transcript.cost}
        model={transcript.model_name}
      />
    </div>
  );
}
