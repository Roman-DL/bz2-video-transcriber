import type { RawTranscript, CleanedTranscript } from '@/api/types';

interface RawTranscriptViewProps {
  transcript: RawTranscript;
  displayText: string;
}

export function RawTranscriptView({ transcript, displayText }: RawTranscriptViewProps) {
  return (
    <div>
      <div className="text-xs text-gray-500 mb-2">
        Модель: <span className="font-mono">{transcript.whisper_model}</span>
      </div>
      <div className="max-h-64 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
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
    <div>
      <div className="text-xs text-gray-500 mb-2">
        Модель: <span className="font-mono">{transcript.model_name}</span>
      </div>
      <div className="max-h-64 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
        {transcript.text}
      </div>
    </div>
  );
}
