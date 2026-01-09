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
  return (
    <div>
      <div className="max-h-64 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
        {transcript.text}
      </div>
      {transcript.corrections_made.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-xs font-medium text-gray-500 mb-2">
            Исправления ({transcript.corrections_made.length}):
          </h4>
          <ul className="text-xs text-gray-600 space-y-1">
            {transcript.corrections_made.slice(0, 5).map((c, i) => (
              <li key={i}>• {c}</li>
            ))}
            {transcript.corrections_made.length > 5 && (
              <li className="text-gray-400">
                ... и ещё {transcript.corrections_made.length - 5}
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
