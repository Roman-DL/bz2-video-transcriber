import type { RawTranscript, CleanedTranscript } from '@/api/types';
import { Card, CardContent, CardHeader } from '@/components/common/Card';
import { FileText, Clock, Zap } from 'lucide-react';

interface RawTranscriptViewProps {
  transcript: RawTranscript;
}

export function RawTranscriptView({ transcript }: RawTranscriptViewProps) {
  const formatDuration = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return h > 0 ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}` : `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-500" />
            <h3 className="text-sm font-medium text-gray-900">
              Сырая транскрипция
            </h3>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {formatDuration(transcript.duration_seconds)}
            </span>
            <span>{transcript.segments.length} сегментов</span>
            <span className="font-mono">{transcript.whisper_model}</span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="max-h-64 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
          {transcript.text_with_timestamps}
        </div>
      </CardContent>
    </Card>
  );
}

interface CleanedTranscriptViewProps {
  transcript: CleanedTranscript;
}

export function CleanedTranscriptView({ transcript }: CleanedTranscriptViewProps) {
  const reduction = Math.round(
    ((transcript.original_length - transcript.cleaned_length) /
      transcript.original_length) *
      100
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-gray-500" />
            <h3 className="text-sm font-medium text-gray-900">
              Очищенная транскрипция
            </h3>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>
              {transcript.cleaned_length.toLocaleString()} символов (-{reduction}
              %)
            </span>
            {transcript.corrections_made.length > 0 && (
              <span>{transcript.corrections_made.length} исправлений</span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="max-h-64 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap">
          {transcript.text}
        </div>
        {transcript.corrections_made.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <h4 className="text-xs font-medium text-gray-500 mb-2">
              Исправления:
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
      </CardContent>
    </Card>
  );
}
