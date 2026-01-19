import { useState, useEffect, useRef } from 'react';
import {
  useStepParse,
  useStepTranscribe,
  useStepClean,
  useStepChunk,
  useStepLongread,
  useStepSummarize,
  useStepSave,
} from '@/api/hooks/useSteps';
import type {
  VideoMetadata,
  RawTranscript,
  CleanedTranscript,
  TranscriptChunks,
  Longread,
  Summary,
  PipelineStep,
} from '@/api/types';
import { PIPELINE_STEPS, STEP_LABELS } from '@/api/types';
import { Button } from '@/components/common/Button';
import { Spinner } from '@/components/common/Spinner';
import { ProgressBar } from '@/components/common/ProgressBar';
import { CollapsibleCard } from '@/components/common/CollapsibleCard';
import { MetadataView } from '@/components/results/MetadataView';
import {
  RawTranscriptView,
  CleanedTranscriptView,
} from '@/components/results/TranscriptView';
import { ChunksView } from '@/components/results/ChunksView';
import { LongreadView } from '@/components/results/LongreadView';
import { SummaryView } from '@/components/results/SummaryView';
import { useSettings } from '@/contexts/SettingsContext';
import {
  CheckCircle,
  Circle,
  AlertCircle,
  ArrowRight,
  Save,
  FileText,
  Zap,
  Layers,
  Clock,
} from 'lucide-react';

interface StepByStepProps {
  filename: string;
  onComplete: () => void;
  onCancel: () => void;
  autoRun?: boolean;
}

interface StepData {
  metadata?: VideoMetadata;
  rawTranscript?: RawTranscript;
  displayText?: string;
  audioPath?: string;
  cleanedTranscript?: CleanedTranscript;
  chunks?: TranscriptChunks;
  longread?: Longread;
  summary?: Summary;
  savedFiles?: string[];
}

type BlockType = 'metadata' | 'rawTranscript' | 'cleanedTranscript' | 'chunks' | 'longread' | 'summary';

export function StepByStep({ filename, onComplete, onCancel, autoRun = false }: StepByStepProps) {
  const [currentStep, setCurrentStep] = useState<PipelineStep>('parse');
  const [data, setData] = useState<StepData>({});
  const [error, setError] = useState<string | null>(null);
  const [expandedBlocks, setExpandedBlocks] = useState<Set<BlockType>>(new Set());
  const { models } = useSettings();

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

  const expandOnlyBlock = (block: BlockType) => {
    setExpandedBlocks(new Set([block]));
  };

  // Hooks
  const stepParse = useStepParse();
  const stepTranscribe = useStepTranscribe();
  const stepClean = useStepClean();
  const stepChunk = useStepChunk();
  const stepLongread = useStepLongread();
  const stepSummarize = useStepSummarize();
  const stepSave = useStepSave();

  const isLoading =
    stepParse.isPending ||
    stepTranscribe.isPending ||
    stepClean.isPending ||
    stepChunk.isPending ||
    stepLongread.isPending ||
    stepSummarize.isPending ||
    stepSave.isPending;

  // Get current progress from active hook
  const getCurrentProgress = (): {
    progress: number | null;
    message: string | null;
    estimatedSeconds: number | null;
    elapsedSeconds: number | null;
  } => {
    switch (currentStep) {
      case 'transcribe':
        return {
          progress: stepTranscribe.progress,
          message: stepTranscribe.message,
          estimatedSeconds: stepTranscribe.estimatedSeconds,
          elapsedSeconds: stepTranscribe.elapsedSeconds,
        };
      case 'clean':
        return {
          progress: stepClean.progress,
          message: stepClean.message,
          estimatedSeconds: stepClean.estimatedSeconds,
          elapsedSeconds: stepClean.elapsedSeconds,
        };
      case 'chunk':
        return {
          progress: stepChunk.progress,
          message: stepChunk.message,
          estimatedSeconds: stepChunk.estimatedSeconds,
          elapsedSeconds: stepChunk.elapsedSeconds,
        };
      case 'longread':
        return {
          progress: stepLongread.progress,
          message: stepLongread.message,
          estimatedSeconds: stepLongread.estimatedSeconds,
          elapsedSeconds: stepLongread.elapsedSeconds,
        };
      case 'summarize':
        return {
          progress: stepSummarize.progress,
          message: stepSummarize.message,
          estimatedSeconds: stepSummarize.estimatedSeconds,
          elapsedSeconds: stepSummarize.elapsedSeconds,
        };
      default:
        return { progress: null, message: null, estimatedSeconds: null, elapsedSeconds: null };
    }
  };

  const { progress, message, estimatedSeconds, elapsedSeconds } = getCurrentProgress();

  const currentStepIndex = PIPELINE_STEPS.indexOf(currentStep);
  const isComplete = data.savedFiles !== undefined;

  // Helper: check if we have required data for step
  const hasDataForStep = (step: PipelineStep): boolean => {
    switch (step) {
      case 'parse': return true;
      case 'transcribe': return !!data.metadata;
      case 'clean': return !!data.rawTranscript && !!data.metadata;
      case 'chunk': return !!data.cleanedTranscript && !!data.metadata;
      case 'longread': return !!data.chunks && !!data.metadata;
      case 'summarize': return !!data.longread && !!data.metadata;
      case 'save': return !!data.metadata && !!data.rawTranscript && !!data.cleanedTranscript && !!data.chunks && !!data.longread && !!data.summary;
    }
  };

  // Ref to track if we're already running a step (prevent double execution)
  const isRunningRef = useRef(false);

  // Auto-run effect
  useEffect(() => {
    if (!autoRun) return;
    if (isLoading) return;
    if (isComplete) return;
    if (error) return;
    if (isRunningRef.current) return;

    if (hasDataForStep(currentStep)) {
      isRunningRef.current = true;
      runStep(currentStep).finally(() => {
        isRunningRef.current = false;
      });
    }
  }, [autoRun, currentStep, isLoading, isComplete, error, data]);

  const runStep = async (step: PipelineStep) => {
    setError(null);

    try {
      switch (step) {
        case 'parse':
          const metadata = await stepParse.mutateAsync({
            video_filename: filename,
            whisper_model: models.transcribe,
          });
          setData((prev) => ({ ...prev, metadata }));
          expandOnlyBlock('metadata');
          setCurrentStep('transcribe');
          break;

        case 'transcribe':
          const transcribeResult = await stepTranscribe.mutate({
            video_filename: filename,
            whisper_model: models.transcribe,
          });
          setData((prev) => ({
            ...prev,
            rawTranscript: transcribeResult.raw_transcript,
            displayText: transcribeResult.display_text,
            audioPath: transcribeResult.audio_path,
          }));
          expandOnlyBlock('rawTranscript');
          setCurrentStep('clean');
          break;

        case 'clean':
          if (!data.rawTranscript || !data.metadata) return;
          const cleanedTranscript = await stepClean.mutate({
            raw_transcript: data.rawTranscript,
            metadata: data.metadata,
            model: models.clean,
          });
          setData((prev) => ({ ...prev, cleanedTranscript }));
          expandOnlyBlock('cleanedTranscript');
          setCurrentStep('chunk');
          break;

        case 'chunk':
          if (!data.cleanedTranscript || !data.metadata) return;
          const chunks = await stepChunk.mutate({
            cleaned_transcript: data.cleanedTranscript,
            metadata: data.metadata,
            model: models.chunk,
          });
          setData((prev) => ({ ...prev, chunks }));
          expandOnlyBlock('chunks');
          setCurrentStep('longread');
          break;

        case 'longread':
          if (!data.chunks || !data.metadata) return;
          const longread = await stepLongread.mutate({
            chunks: data.chunks,
            metadata: data.metadata,
            model: models.summarize, // Use summarize model for longread
          });
          setData((prev) => ({ ...prev, longread }));
          expandOnlyBlock('longread');
          setCurrentStep('summarize');
          break;

        case 'summarize':
          if (!data.longread || !data.metadata) return;
          const summary = await stepSummarize.mutate({
            longread: data.longread,
            metadata: data.metadata,
            model: models.summarize,
          });
          setData((prev) => ({ ...prev, summary }));
          expandOnlyBlock('summary');
          setCurrentStep('save');
          break;

        case 'save':
          if (
            !data.metadata ||
            !data.rawTranscript ||
            !data.cleanedTranscript ||
            !data.chunks ||
            !data.longread ||
            !data.summary
          )
            return;
          const savedFiles = await stepSave.mutateAsync({
            metadata: data.metadata,
            raw_transcript: data.rawTranscript,
            cleaned_transcript: data.cleanedTranscript,
            chunks: data.chunks,
            longread: data.longread,
            summary: data.summary,
            audio_path: data.audioPath,
          });
          setData((prev) => ({ ...prev, savedFiles }));
          // Collapse all blocks after save
          setExpandedBlocks(new Set());
          break;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка выполнения');
    }
  };

  const getStepStatus = (step: PipelineStep): 'pending' | 'completed' | 'current' => {
    const stepIndex = PIPELINE_STEPS.indexOf(step);
    if (stepIndex < currentStepIndex) return 'completed';
    if (stepIndex === currentStepIndex) return 'current';
    return 'pending';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-sm font-medium text-gray-500 mb-1">
          {autoRun ? 'Автоматическая обработка' : 'Пошаговая обработка'}
        </h3>
        <p className="text-sm text-gray-900 truncate">{filename}</p>
      </div>

      {/* Steps indicator */}
      <div className="flex items-center gap-2">
        {PIPELINE_STEPS.map((step, index) => {
          const status = getStepStatus(step);
          return (
            <div key={step} className="flex items-center gap-2">
              {status === 'completed' ? (
                <CheckCircle className="w-5 h-5 text-green-600" />
              ) : status === 'current' ? (
                <div className="w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center">
                  <span className="text-xs text-white font-medium">
                    {index + 1}
                  </span>
                </div>
              ) : (
                <Circle className="w-5 h-5 text-gray-300" />
              )}
              {index < PIPELINE_STEPS.length - 1 && (
                <div
                  className={`w-8 h-0.5 ${
                    status === 'completed' ? 'bg-green-600' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Current step info */}
      {!isComplete && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex-1 mr-4">
              <h4 className="text-sm font-medium text-blue-900">
                Шаг {currentStepIndex + 1}: {STEP_LABELS[currentStep]}
              </h4>
              <p className="text-xs text-blue-700 mt-1">
                {isLoading && message ? message : getStepDescription(currentStep)}
              </p>
            </div>
            {!autoRun && (
              <Button
                onClick={() => runStep(currentStep)}
                disabled={isLoading}
                className="flex items-center gap-2 shrink-0"
              >
                {isLoading ? (
                  <Spinner size="sm" className="text-white" />
                ) : currentStep === 'save' ? (
                  <Save className="w-4 h-4" />
                ) : (
                  <ArrowRight className="w-4 h-4" />
                )}
                {isLoading ? 'Выполняется...' : 'Выполнить'}
              </Button>
            )}
            {autoRun && isLoading && (
              <Spinner size="sm" className="text-blue-600" />
            )}
          </div>

          {/* Progress bar for long-running operations */}
          {isLoading && progress !== null && (
            <div className="mt-3">
              <ProgressBar progress={progress} size="sm" showLabel={false} />
              <div className="mt-1 flex justify-between text-sm text-gray-600">
                <span>{Math.round(progress)}%</span>
                {estimatedSeconds !== null && elapsedSeconds !== null && estimatedSeconds > 0 && (
                  <span className="text-blue-600">
                    {formatETA(estimatedSeconds, elapsedSeconds)}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-700">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">Ошибка</span>
          </div>
          <p className="mt-1 text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Results - only show in step-by-step mode */}
      {!autoRun && (
        <div className="space-y-3">
          {data.metadata && (
            <CollapsibleCard
              title="Метаданные"
              icon={FileText}
              stats={
                data.metadata.duration_seconds ? (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {formatDuration(data.metadata.duration_seconds)}
                  </span>
                ) : null
              }
              expanded={expandedBlocks.has('metadata')}
              onToggle={() => toggleBlock('metadata')}
            >
              <MetadataView metadata={data.metadata} />
            </CollapsibleCard>
          )}

          {data.rawTranscript && (
            <CollapsibleCard
              title="Сырая транскрипция"
              icon={FileText}
              stats={
                <>
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {formatDuration(data.rawTranscript.duration_seconds)}
                  </span>
                  <span>{data.rawTranscript.segments.length} сегментов</span>
                </>
              }
              expanded={expandedBlocks.has('rawTranscript')}
              onToggle={() => toggleBlock('rawTranscript')}
            >
              <RawTranscriptView transcript={data.rawTranscript} displayText={data.displayText || ''} />
            </CollapsibleCard>
          )}

          {data.cleanedTranscript && (
            <CollapsibleCard
              title="Очищенная транскрипция"
              icon={Zap}
              stats={
                <>
                  <span>
                    {data.cleanedTranscript.cleaned_length.toLocaleString()} симв.
                  </span>
                  <span>
                    -{Math.round(((data.cleanedTranscript.original_length - data.cleanedTranscript.cleaned_length) / data.cleanedTranscript.original_length) * 100)}%
                  </span>
                </>
              }
              expanded={expandedBlocks.has('cleanedTranscript')}
              onToggle={() => toggleBlock('cleanedTranscript')}
            >
              <CleanedTranscriptView transcript={data.cleanedTranscript} />
            </CollapsibleCard>
          )}

          {data.chunks && (
            <CollapsibleCard
              title="Семантические чанки"
              icon={Layers}
              stats={
                <>
                  <span>{data.chunks.total_chunks} чанков</span>
                  <span>~{data.chunks.avg_chunk_size} слов/чанк</span>
                </>
              }
              expanded={expandedBlocks.has('chunks')}
              onToggle={() => toggleBlock('chunks')}
            >
              <ChunksView chunks={data.chunks} />
            </CollapsibleCard>
          )}

          {data.longread && (
            <CollapsibleCard
              title="Лонгрид"
              icon={FileText}
              stats={
                <>
                  <span>{data.longread.total_sections} секций</span>
                  <span>{data.longread.total_word_count} слов</span>
                </>
              }
              expanded={expandedBlocks.has('longread')}
              onToggle={() => toggleBlock('longread')}
            >
              <LongreadView longread={data.longread} />
            </CollapsibleCard>
          )}

          {data.summary && (
            <CollapsibleCard
              title="Конспект"
              icon={FileText}
              stats={
                <>
                  <span>{data.summary.key_concepts.length} концепций</span>
                  <span>{data.summary.quotes.length} цитат</span>
                </>
              }
              expanded={expandedBlocks.has('summary')}
              onToggle={() => toggleBlock('summary')}
            >
              <SummaryView summary={data.summary} />
            </CollapsibleCard>
          )}
        </div>
      )}

      {/* Saved files */}
      {isComplete && data.savedFiles && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-green-700 mb-2">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">Сохранено в архив</span>
          </div>
          <ul className="text-sm text-green-600 space-y-1">
            {data.savedFiles.map((file) => (
              <li key={file}>• {file}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
        {isComplete ? (
          <Button onClick={onComplete}>Закрыть</Button>
        ) : (
          <Button variant="secondary" onClick={onCancel} disabled={autoRun && isLoading}>
            {autoRun ? 'Прервать' : 'Отменить'}
          </Button>
        )}
      </div>
    </div>
  );
}

function getStepDescription(step: PipelineStep): string {
  switch (step) {
    case 'parse':
      return 'Извлечение метаданных из имени файла';
    case 'transcribe':
      return 'Извлечение аудио и транскрипция через Whisper (может занять несколько минут)';
    case 'clean':
      return 'Очистка текста с использованием глоссария и LLM';
    case 'chunk':
      return 'Разбиение на семантические чанки';
    case 'longread':
      return 'Генерация лонгрида из чанков (структурированный документ)';
    case 'summarize':
      return 'Генерация конспекта из лонгрида (краткое изложение)';
    case 'save':
      return 'Сохранение результатов в архив';
  }
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h > 0
    ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    : `${m}:${s.toString().padStart(2, '0')}`;
}

/**
 * Format estimated time remaining (ETA) for display.
 */
function formatETA(estimatedSeconds: number, elapsedSeconds: number): string {
  const remaining = estimatedSeconds - elapsedSeconds;

  // If elapsed > estimated * 1.2, show "longer than expected"
  if (elapsedSeconds > estimatedSeconds * 1.2) {
    return 'дольше ожидаемого...';
  }

  if (remaining <= 0) return 'завершается...';
  if (remaining < 5) return 'менее 5 сек';

  const minutes = Math.floor(remaining / 60);
  const seconds = Math.floor(remaining % 60);

  if (minutes >= 5) {
    return `~${minutes} мин`;
  }
  if (minutes >= 1) {
    return seconds > 0 ? `~${minutes} мин ${seconds} сек` : `~${minutes} мин`;
  }
  return `~${seconds} сек`;
}
