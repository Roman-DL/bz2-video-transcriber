import { useState, useEffect, useRef, useMemo } from 'react';
import {
  useStepParse,
  useStepTranscribe,
  useStepClean,
  useStepChunk,
  useStepLongread,
  useStepSummarize,
  useStepStory,
  useStepSave,
} from '@/api/hooks/useSteps';
import { useStagePrompts } from '@/api/hooks/usePrompts';
import { useAvailableModels, useDefaultModels } from '@/api/hooks/useModels';
import type {
  VideoMetadata,
  RawTranscript,
  CleanedTranscript,
  TranscriptChunks,
  Longread,
  Summary,
  Story,
  PipelineStep,
  PromptOverrides,
  StagePromptsResponse,
} from '@/api/types';
import { STEP_LABELS, EDUCATIONAL_STEPS, LEADERSHIP_STEPS } from '@/api/types';
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
import { StoryView } from '@/components/results/StoryView';
import { ComponentPromptSelector } from '@/components/settings/ComponentPromptSelector';
import { ModelSelector } from '@/components/settings/ModelSelector';
import { buildLLMOptions } from '@/utils/modelUtils';
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
  story?: Story;
  savedFiles?: string[];
}

type BlockType = 'metadata' | 'rawTranscript' | 'cleanedTranscript' | 'chunks' | 'longread' | 'summary' | 'story';

// Stages that support prompt selection
const STAGES_WITH_PROMPTS = ['clean', 'longread', 'summarize', 'story'] as const;
type StageWithPrompts = (typeof STAGES_WITH_PROMPTS)[number];

// Stages that support model selection (same as prompts)
type StageWithModels = StageWithPrompts;

// Prompt overrides state per stage
type StagePromptOverrides = Record<StageWithPrompts, PromptOverrides>;

// Model overrides state per stage
type StageModelOverrides = Record<StageWithModels, string | undefined>;

export function StepByStep({ filename, onComplete, onCancel, autoRun = false }: StepByStepProps) {
  const [currentStep, setCurrentStep] = useState<PipelineStep>('parse');
  const [data, setData] = useState<StepData>({});
  const [error, setError] = useState<string | null>(null);
  const [expandedBlocks, setExpandedBlocks] = useState<Set<BlockType>>(new Set());
  const [isInitializing, setIsInitializing] = useState(true);
  const [parseError, setParseError] = useState<string | null>(null);
  const [promptOverrides, setPromptOverrides] = useState<StagePromptOverrides>({
    clean: {},
    longread: {},
    summarize: {},
    story: {},
  });
  const [modelOverrides, setModelOverrides] = useState<StageModelOverrides>({
    clean: undefined,
    longread: undefined,
    summarize: undefined,
    story: undefined,
  });
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

  // Step hooks
  const stepParse = useStepParse();
  const stepTranscribe = useStepTranscribe();
  const stepClean = useStepClean();
  const stepChunk = useStepChunk();
  const stepLongread = useStepLongread();
  const stepSummarize = useStepSummarize();
  const stepStory = useStepStory();
  const stepSave = useStepSave();

  // Model hooks (only in step-by-step mode)
  const { data: availableModels } = useAvailableModels(!autoRun);
  const { data: defaultModels } = useDefaultModels(!autoRun);

  // Build LLM options for model selector
  const llmOptions = useMemo(() => {
    if (autoRun) return [];
    return buildLLMOptions(availableModels?.ollama_models, availableModels?.claude_models);
  }, [availableModels, autoRun]);

  // Prompt hooks - fetch variants for each LLM stage (only in step-by-step mode)
  const { data: cleanPrompts } = useStagePrompts('cleaning', !autoRun);
  const { data: longreadPrompts } = useStagePrompts('longread', !autoRun);
  const { data: summaryPrompts } = useStagePrompts('summary', !autoRun);
  const { data: storyPrompts } = useStagePrompts('story', !autoRun);

  // Helper to get prompts data for current step
  const getPromptsForStep = (step: PipelineStep): StagePromptsResponse | undefined => {
    switch (step) {
      case 'clean': return cleanPrompts;
      case 'longread': return longreadPrompts;
      case 'summarize': return summaryPrompts;
      case 'story': return storyPrompts;
      default: return undefined;
    }
  };

  // Helper to check if stage has any selectable prompts (variants > 1)
  const hasSelectablePrompts = (prompts: StagePromptsResponse | undefined): boolean => {
    if (!prompts) return false;
    return prompts.components.some((c) => c.variants.length > 1);
  };

  // Helper to update prompt override for a stage
  const updatePromptOverride = (
    stage: StageWithPrompts,
    component: keyof PromptOverrides,
    value: string | undefined
  ) => {
    setPromptOverrides((prev) => ({
      ...prev,
      [stage]: {
        ...prev[stage],
        [component]: value,
      },
    }));
  };

  // Get current prompt overrides for API call (only non-empty values)
  const getPromptOverridesForApi = (stage: StageWithPrompts): PromptOverrides | undefined => {
    const overrides = promptOverrides[stage];
    const nonEmpty = Object.fromEntries(
      Object.entries(overrides).filter(([, v]) => v !== undefined)
    );
    return Object.keys(nonEmpty).length > 0 ? nonEmpty : undefined;
  };

  // Get effective model for a stage (per-step override > global settings > default)
  // Note: 'story' uses 'summarize' model as there's no separate story model setting
  const getModelForStage = (stage: StageWithModels): string | undefined => {
    const settingsKey = stage === 'story' ? 'summarize' : stage;
    return modelOverrides[stage] || models[settingsKey];
  };

  // Auto-parse on mount to determine content_type
  useEffect(() => {
    let mounted = true;

    const autoParse = async () => {
      try {
        const metadata = await stepParse.mutateAsync({
          video_filename: filename,
          whisper_model: models.transcribe,
        });
        if (mounted) {
          setData({ metadata });
          expandOnlyBlock('metadata');
          setCurrentStep('transcribe');
          setIsInitializing(false);
        }
      } catch (err) {
        if (mounted) {
          setParseError(err instanceof Error ? err.message : 'Ошибка парсинга');
          setIsInitializing(false);
        }
      }
    };

    autoParse();

    return () => { mounted = false; };
  }, [filename]);

  // Determine pipeline steps based on content type
  const contentType = data.metadata?.content_type || 'educational';
  const pipelineSteps = contentType === 'leadership' ? LEADERSHIP_STEPS : EDUCATIONAL_STEPS;

  const isLoading =
    stepParse.isPending ||
    stepTranscribe.isPending ||
    stepClean.isPending ||
    stepChunk.isPending ||
    stepLongread.isPending ||
    stepSummarize.isPending ||
    stepStory.isPending ||
    stepSave.isPending;

  // Get current progress from active hook (SSE steps only)
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
      case 'story':
        return {
          progress: stepStory.progress,
          message: stepStory.message,
          estimatedSeconds: stepStory.estimatedSeconds,
          elapsedSeconds: stepStory.elapsedSeconds,
        };
      default:
        // parse, chunk, save - instant operations, no progress
        return { progress: null, message: null, estimatedSeconds: null, elapsedSeconds: null };
    }
  };

  const { progress, message, estimatedSeconds, elapsedSeconds } = getCurrentProgress();

  const currentStepIndex = pipelineSteps.indexOf(currentStep);
  const isComplete = data.savedFiles !== undefined;

  // Helper: check if we have required data for step
  const hasDataForStep = (step: PipelineStep): boolean => {
    switch (step) {
      case 'parse': return true;
      case 'transcribe': return !!data.metadata;
      case 'clean': return !!data.rawTranscript && !!data.metadata;
      case 'longread': return !!data.cleanedTranscript && !!data.metadata;
      case 'summarize': return !!data.cleanedTranscript && !!data.metadata;
      case 'story': return !!data.cleanedTranscript && !!data.metadata;
      case 'chunk':
        if (contentType === 'leadership') {
          return !!data.story && !!data.metadata;
        }
        return !!data.longread && !!data.summary && !!data.metadata;
      case 'save':
        if (contentType === 'leadership') {
          return !!data.metadata && !!data.rawTranscript && !!data.cleanedTranscript && !!data.chunks && !!data.story;
        }
        return !!data.metadata && !!data.rawTranscript && !!data.cleanedTranscript && !!data.chunks && !!data.longread && !!data.summary;
    }
  };

  // Ref to track if we're already running a step (prevent double execution)
  const isRunningRef = useRef(false);

  // Auto-run effect
  useEffect(() => {
    if (!autoRun) return;
    if (isInitializing) return; // Wait for auto-parse to complete
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
  }, [autoRun, currentStep, isLoading, isComplete, error, data, isInitializing]);

  // Reset data from a specific step onwards (for re-running)
  const resetDataFromStep = (step: PipelineStep) => {
    const stepIndex = pipelineSteps.indexOf(step);
    const fieldsToReset: Record<PipelineStep, (keyof StepData)[]> = {
      parse: ['metadata'],
      transcribe: ['rawTranscript', 'displayText', 'audioPath'],
      clean: ['cleanedTranscript'],
      longread: ['longread'],
      summarize: ['summary'],
      story: ['story'],
      chunk: ['chunks'],
      save: ['savedFiles'],
    };

    setData((prev) => {
      const next = { ...prev };
      for (let i = stepIndex; i < pipelineSteps.length; i++) {
        fieldsToReset[pipelineSteps[i]]?.forEach((field) => {
          next[field] = undefined;
        });
      }
      return next;
    });
    setExpandedBlocks(new Set());
    setError(null);
  };

  // Handle click on completed step (re-run from that step)
  const handleStepClick = (step: PipelineStep) => {
    resetDataFromStep(step);
    setCurrentStep(step);
  };

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
            model: getModelForStage('clean'),
            prompt_overrides: getPromptOverridesForApi('clean'),
          });
          setData((prev) => ({ ...prev, cleanedTranscript }));
          expandOnlyBlock('cleanedTranscript');
          setCurrentStep(contentType === 'leadership' ? 'story' : 'longread');
          break;

        case 'longread':
          if (!data.cleanedTranscript || !data.metadata) return;
          const longread = await stepLongread.mutate({
            cleaned_transcript: data.cleanedTranscript,
            metadata: data.metadata,
            model: getModelForStage('longread'),
            prompt_overrides: getPromptOverridesForApi('longread'),
          });
          setData((prev) => ({ ...prev, longread }));
          expandOnlyBlock('longread');
          setCurrentStep('summarize');
          break;

        case 'summarize':
          if (!data.cleanedTranscript || !data.metadata) return;
          const summary = await stepSummarize.mutate({
            cleaned_transcript: data.cleanedTranscript,
            metadata: data.metadata,
            model: getModelForStage('summarize'),
            prompt_overrides: getPromptOverridesForApi('summarize'),
          });
          setData((prev) => ({ ...prev, summary }));
          expandOnlyBlock('summary');
          setCurrentStep('chunk');
          break;

        case 'story':
          if (!data.cleanedTranscript || !data.metadata) return;
          const story = await stepStory.mutate({
            cleaned_transcript: data.cleanedTranscript,
            metadata: data.metadata,
            model: getModelForStage('story'),
            prompt_overrides: getPromptOverridesForApi('story'),
          });
          setData((prev) => ({ ...prev, story }));
          expandOnlyBlock('story');
          setCurrentStep('chunk');
          break;

        case 'chunk':
          if (!data.metadata) return;
          let markdownContent: string;
          if (contentType === 'leadership') {
            if (!data.story) return;
            markdownContent = data.story.blocks
              .map(b => `## ${b.block_number}️⃣ ${b.block_name}\n\n${b.content}`)
              .join('\n\n');
          } else {
            if (!data.longread) return;
            markdownContent = data.longread.sections
              .map(s => `## ${s.title}\n\n${s.content}`)
              .join('\n\n');
          }
          const chunks = await stepChunk.mutateAsync({
            markdown_content: markdownContent,
            metadata: data.metadata,
          });
          setData((prev) => ({ ...prev, chunks }));
          expandOnlyBlock('chunks');
          setCurrentStep('save');
          break;

        case 'save':
          // Different validation based on content type
          if (contentType === 'leadership') {
            if (!data.metadata || !data.rawTranscript || !data.cleanedTranscript || !data.chunks || !data.story) return;
            const savedFilesLeadership = await stepSave.mutateAsync({
              metadata: data.metadata,
              raw_transcript: data.rawTranscript,
              cleaned_transcript: data.cleanedTranscript,
              chunks: data.chunks,
              story: data.story,
              audio_path: data.audioPath,
            });
            setData((prev) => ({ ...prev, savedFiles: savedFilesLeadership }));
          } else {
            if (!data.metadata || !data.rawTranscript || !data.cleanedTranscript || !data.chunks || !data.longread || !data.summary) return;
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
          }
          // Collapse all blocks after save
          setExpandedBlocks(new Set());
          break;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка выполнения');
    }
  };

  const getStepStatus = (step: PipelineStep): 'pending' | 'completed' | 'current' => {
    const stepIndex = pipelineSteps.indexOf(step);
    if (stepIndex < currentStepIndex) return 'completed';
    if (stepIndex === currentStepIndex) return 'current';
    return 'pending';
  };

  // Check if step supports model/prompt selection
  const isLLMStep = (step: PipelineStep): step is StageWithPrompts => {
    return STAGES_WITH_PROMPTS.includes(step as StageWithPrompts);
  };

  // Loading state during auto-parse
  if (isInitializing) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-1">
            Определение типа контента
          </h3>
          <p className="text-sm text-gray-900 truncate">{filename}</p>
        </div>

        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Spinner size="lg" />
            <p className="mt-4 text-sm text-gray-600">
              Анализ метаданных файла...
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Parse error state
  if (parseError) {
    return (
      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-1">
            Ошибка определения типа контента
          </h3>
          <p className="text-sm text-gray-900 truncate">{filename}</p>
        </div>

        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-700">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">Ошибка парсинга</span>
          </div>
          <p className="mt-1 text-sm text-red-600">{parseError}</p>
        </div>

        <div className="flex justify-end">
          <Button variant="secondary" onClick={onCancel}>
            Закрыть
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-sm font-medium text-gray-500 mb-1">
          {autoRun ? 'Автоматическая обработка' : 'Пошаговая обработка'}
          {contentType === 'leadership' && ' (Лидерская история)'}
        </h3>
        <p className="text-sm text-gray-900 truncate">{filename}</p>
      </div>

      {/* Steps indicator */}
      <div className="flex items-center gap-2">
        {pipelineSteps.map((step, index) => {
          const status = getStepStatus(step);
          const isClickable = status === 'completed' && !isLoading && !autoRun;
          return (
            <div key={step} className="flex items-center gap-2">
              {status === 'completed' ? (
                <button
                  onClick={() => isClickable && handleStepClick(step)}
                  disabled={!isClickable}
                  className={`p-0 border-0 bg-transparent ${
                    isClickable ? 'cursor-pointer hover:opacity-70' : 'cursor-default'
                  }`}
                  title={isClickable ? `Перезапустить с шага "${STEP_LABELS[step]}"` : undefined}
                >
                  <CheckCircle className="w-5 h-5 text-green-600" />
                </button>
              ) : status === 'current' ? (
                <div className="w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center">
                  <span className="text-xs text-white font-medium">
                    {index + 1}
                  </span>
                </div>
              ) : (
                <Circle className="w-5 h-5 text-gray-300" />
              )}
              {index < pipelineSteps.length - 1 && (
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

          {/* Model and prompt selectors for LLM stages (step-by-step mode only) */}
          {!autoRun && !isLoading && isLLMStep(currentStep) && (
            <div className="mt-3 pt-3 border-t border-blue-200">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-medium text-blue-800">Настройки:</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {/* Model selector - compact mode */}
                {llmOptions.length > 0 && (() => {
                  // 'story' uses 'summarize' model setting (no separate story model)
                  const settingsKey = currentStep === 'story' ? 'summarize' : currentStep;
                  return (
                    <ModelSelector
                      label="Модель"
                      value={modelOverrides[currentStep]}
                      defaultValue={defaultModels?.[settingsKey] || models[settingsKey] || ''}
                      options={llmOptions}
                      onChange={(value) => setModelOverrides((prev) => ({ ...prev, [currentStep]: value }))}
                      compact
                    />
                  );
                })()}

                {/* Prompt selectors */}
                {hasSelectablePrompts(getPromptsForStep(currentStep)) &&
                  getPromptsForStep(currentStep)?.components.map((comp) => (
                    <ComponentPromptSelector
                      key={comp.component}
                      label={comp.component}
                      componentData={comp}
                      value={promptOverrides[currentStep]?.[comp.component as keyof PromptOverrides]}
                      onChange={(value) =>
                        updatePromptOverride(
                          currentStep,
                          comp.component as keyof PromptOverrides,
                          value
                        )
                      }
                    />
                  ))}
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

          {data.story && (
            <CollapsibleCard
              title="Лидерская история"
              icon={FileText}
              stats={
                <>
                  <span>{data.story.total_blocks} блоков</span>
                  <span>{data.story.speed}</span>
                </>
              }
              expanded={expandedBlocks.has('story')}
              onToggle={() => toggleBlock('story')}
            >
              <StoryView story={data.story} />
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
    case 'longread':
      return 'Генерация лонгрида из очищенного транскрипта';
    case 'summarize':
      return 'Генерация конспекта из очищенного транскрипта';
    case 'story':
      return 'Генерация лидерской истории (8 блоков)';
    case 'chunk':
      return 'Разбиение на чанки по заголовкам H2 (детерминированно)';
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
