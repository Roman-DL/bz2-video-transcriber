import type { RawTranscript, CleanedTranscript } from '@/api/types';

interface RawTranscriptViewProps {
  transcript: RawTranscript;
  displayText: string;
}

export function RawTranscriptView({ transcript, displayText }: RawTranscriptViewProps) {
  return (
    <div className="h-full flex flex-col">
      <div className="text-xs text-gray-500 mb-2 shrink-0">
        Модель: <span className="font-mono">{transcript.whisper_model}</span>
      </div>
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap break-words min-h-0">
        {displayText}
      </div>
    </div>
  );
}

interface CleanedTranscriptViewProps {
  transcript: CleanedTranscript;
}

export function CleanedTranscriptView({ transcript }: CleanedTranscriptViewProps) {
  return (
    <div className="h-full flex flex-col">
      <div className="text-xs text-gray-500 mb-2 shrink-0">
        Модель: <span className="font-mono">{transcript.model_name}</span>
      </div>
      <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap break-words min-h-0">
        {transcript.text}
      </div>
    </div>
  );
}
