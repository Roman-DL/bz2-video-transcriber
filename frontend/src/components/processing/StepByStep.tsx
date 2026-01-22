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
import { ProgressBar } from '@/components/common/ProgressBar';
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
  Play,
  Save,
  FileText,
  Zap,
  Layers,
  Clock,
  RefreshCw,
  X,
  Loader2,
  FileAudio,
  Sparkles,
  BookOpen,
  ListChecks,
  FolderOutput,
  Heart,
  ChevronDown,
  ChevronUp,
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

type ResultTab = 'metadata' | 'rawTranscript' | 'cleanedTranscript' | 'chunks' | 'longread' | 'summary' | 'story';

// Stages that support prompt selection
const STAGES_WITH_PROMPTS = ['clean', 'longread', 'summarize', 'story'] as const;
type StageWithPrompts = (typeof STAGES_WITH_PROMPTS)[number];

// Stages that support model selection (same as prompts)
type StageWithModels = StageWithPrompts;

// Prompt overrides state per stage
type StagePromptOverrides = Record<StageWithPrompts, PromptOverrides>;

// Model overrides state per stage
type StageModelOverrides = Record<StageWithModels, string | undefined>;

// Step icons mapping
const STEP_ICONS: Record<PipelineStep, React.ComponentType<{ className?: string }>> = {
  parse: FileText,
  transcribe: FileAudio,
  clean: Sparkles,
  longread: BookOpen,
  summarize: ListChecks,
  story: Heart,
  chunk: Layers,
  save: FolderOutput,
};

export function StepByStep({ filename, onComplete, onCancel, autoRun = false }: StepByStepProps) {
  const [currentStep, setCurrentStep] = useState<PipelineStep>('parse');
  const [data, setData] = useState<StepData>({});
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ResultTab | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [parseError, setParseError] = useState<string | null>(null);
  const [showRerunSettings, setShowRerunSettings] = useState(false);
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
          setActiveTab('metadata');
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
    setError(null);
  };

  // Handle click on completed step (re-run from that step)
  const handleStepClick = (step: PipelineStep) => {
    resetDataFromStep(step);
    setCurrentStep(step);
    // Set active tab to the result of the step we're re-running
    const tabForStep = getTabForStep(step);
    if (tabForStep) setActiveTab(tabForStep);
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
          setActiveTab('metadata');
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
          setActiveTab('rawTranscript');
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
          setActiveTab('cleanedTranscript');
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
          setActiveTab('longread');
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
          setActiveTab('summary');
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
          setActiveTab('story');
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
          setActiveTab('chunks');
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
          break;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка выполнения');
    }
  };

  const getStepStatus = (step: PipelineStep): 'pending' | 'completed' | 'current' | 'running' => {
    const stepIndex = pipelineSteps.indexOf(step);
    if (stepIndex < currentStepIndex) return 'completed';
    if (stepIndex === currentStepIndex) return isLoading ? 'running' : 'current';
    return 'pending';
  };

  // Check if step supports model/prompt selection
  const isLLMStep = (step: PipelineStep): step is StageWithPrompts => {
    return STAGES_WITH_PROMPTS.includes(step as StageWithPrompts);
  };

  // Find the last completed LLM step before current step
  const getPreviousCompletedLLMStep = (): StageWithModels | null => {
    const currentIndex = pipelineSteps.indexOf(currentStep);
    for (let i = currentIndex - 1; i >= 0; i--) {
      const step = pipelineSteps[i];
      if (isLLMStep(step)) {
        // Check if step is actually completed (has result)
        const hasResult = (() => {
          switch (step) {
            case 'clean': return !!data.cleanedTranscript;
            case 'longread': return !!data.longread;
            case 'summarize': return !!data.summary;
            case 'story': return !!data.story;
            default: return false;
          }
        })();
        if (hasResult) return step as StageWithModels;
      }
    }
    return null;
  };

  // Rerun a step with current overrides
  const rerunStep = async (step: PipelineStep) => {
    resetDataFromStep(step);
    setCurrentStep(step);
    await runStep(step);
  };

  const previousLLMStep = getPreviousCompletedLLMStep();

  // Get tab for step result
  const getTabForStep = (step: PipelineStep): ResultTab | null => {
    switch (step) {
      case 'parse': return 'metadata';
      case 'transcribe': return 'rawTranscript';
      case 'clean': return 'cleanedTranscript';
      case 'longread': return 'longread';
      case 'summarize': return 'summary';
      case 'story': return 'story';
      case 'chunk': return 'chunks';
      default: return null;
    }
  };

  // Get available tabs based on data
  const getAvailableTabs = (): ResultTab[] => {
    const tabs: ResultTab[] = [];
    if (data.metadata) tabs.push('metadata');
    if (data.rawTranscript) tabs.push('rawTranscript');
    if (data.cleanedTranscript) tabs.push('cleanedTranscript');
    if (data.longread) tabs.push('longread');
    if (data.summary) tabs.push('summary');
    if (data.story) tabs.push('story');
    if (data.chunks) tabs.push('chunks');
    return tabs;
  };

  // Tab labels
  const TAB_LABELS: Record<ResultTab, string> = {
    metadata: 'Метаданные',
    rawTranscript: 'Транскрипт',
    cleanedTranscript: 'Очистка',
    longread: 'Лонгрид',
    summary: 'Конспект',
    story: 'История',
    chunks: 'Чанки',
  };

  // Get step stats for display
  const getStepStats = (step: PipelineStep): string | null => {
    switch (step) {
      case 'transcribe':
        return data.rawTranscript ? formatDuration(data.rawTranscript.duration_seconds) : null;
      case 'clean':
        return data.cleanedTranscript ? `${data.cleanedTranscript.cleaned_length.toLocaleString()} симв.` : null;
      case 'longread':
        return data.longread ? `${data.longread.total_sections} секций` : null;
      case 'summarize':
        return data.summary ? `${data.summary.key_concepts.length} концепций` : null;
      case 'story':
        return data.story ? `${data.story.total_blocks} блоков` : null;
      case 'chunk':
        return data.chunks ? `${data.chunks.total_chunks} чанков` : null;
      case 'save':
        return data.savedFiles ? `${data.savedFiles.length} файлов` : null;
      default:
        return null;
    }
  };

  // Loading state during auto-parse
  if (isInitializing) {
    return (
      <div className="flex items-center justify-center py-24" style={{ fontFamily: 'var(--font-body)' }}>
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl flex items-center justify-center" style={{ backgroundColor: 'var(--color-cream-dark)' }}>
            <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--color-accent)' }} />
          </div>
          <h3 className="text-lg font-medium mb-2" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
            Анализ метаданных
          </h3>
          <p className="text-sm" style={{ color: 'var(--color-warm-gray)' }}>
            {filename}
          </p>
        </div>
      </div>
    );
  }

  // Parse error state
  if (parseError) {
    return (
      <div className="py-12" style={{ fontFamily: 'var(--font-body)' }}>
        <div className="max-w-md mx-auto text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl flex items-center justify-center" style={{ backgroundColor: 'var(--color-error-light)' }}>
            <AlertCircle className="w-8 h-8" style={{ color: 'var(--color-error)' }} />
          </div>
          <h3 className="text-lg font-medium mb-2" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
            Ошибка парсинга
          </h3>
          <p className="text-sm mb-6" style={{ color: 'var(--color-warm-gray)' }}>
            {parseError}
          </p>
          <Button variant="secondary" onClick={onCancel}>
            Закрыть
          </Button>
        </div>
      </div>
    );
  }

  // Auto-run layout (single column, centered)
  if (autoRun) {
    return (
      <div className="py-6" style={{ fontFamily: 'var(--font-body)', backgroundColor: 'var(--color-cream)' }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-8 px-4">
          <div>
            <h2 className="text-xl font-semibold" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
              {isComplete ? 'Обработка завершена' : 'Автоматическая обработка'}
            </h2>
            <p className="text-sm mt-1 truncate max-w-md" style={{ color: 'var(--color-warm-gray)' }}>
              {filename}
            </p>
          </div>
          <button
            onClick={onCancel}
            disabled={isLoading && !isComplete}
            className="p-2 rounded-lg hover:bg-black/5 transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" style={{ color: 'var(--color-warm-gray)' }} />
          </button>
        </div>

        <div className="max-w-lg mx-auto px-4">
          {/* Current step card */}
          {!isComplete && (
            <div className="rounded-2xl p-6 mb-8" style={{ backgroundColor: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: 'var(--color-info-light)' }}>
                  <Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--color-info)' }} />
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide font-medium" style={{ color: 'var(--color-info)' }}>
                    Выполняется
                  </div>
                  <div className="font-medium" style={{ color: 'var(--color-charcoal)' }}>
                    Шаг {currentStepIndex + 1} из {pipelineSteps.length}: {STEP_LABELS[currentStep]}
                  </div>
                </div>
              </div>

              <p className="text-sm mb-4" style={{ color: 'var(--color-warm-gray)' }}>
                {message || getStepDescription(currentStep)}
              </p>

              {progress !== null && (
                <div>
                  <ProgressBar progress={progress} size="sm" showLabel={false} />
                  <div className="mt-2 flex justify-between text-xs" style={{ color: 'var(--color-warm-gray)' }}>
                    <span>{Math.round(progress)}%</span>
                    {estimatedSeconds !== null && elapsedSeconds !== null && estimatedSeconds > 0 && (
                      <span style={{ color: 'var(--color-info)' }}>
                        {formatETA(estimatedSeconds, elapsedSeconds)}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Success card */}
          {isComplete && data.savedFiles && (
            <div className="rounded-2xl p-6 mb-8" style={{ backgroundColor: 'var(--color-success-light)', border: '1px solid var(--color-success)' }}>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: 'white' }}>
                  <CheckCircle className="w-5 h-5" style={{ color: 'var(--color-success)' }} />
                </div>
                <div>
                  <div className="font-medium" style={{ color: 'var(--color-success)' }}>
                    Успешно сохранено
                  </div>
                </div>
              </div>

              <p className="text-sm mb-3" style={{ color: 'var(--color-charcoal)' }}>
                Файлы сохранены в архив:
              </p>
              <ul className="text-sm space-y-1" style={{ color: 'var(--color-warm-gray)' }}>
                {data.savedFiles.map((file) => (
                  <li key={file} className="flex items-center gap-2">
                    <span>•</span>
                    <span style={{ fontFamily: 'var(--font-mono)' }}>{file}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded-2xl p-6 mb-8" style={{ backgroundColor: 'var(--color-error-light)', border: '1px solid var(--color-error)' }}>
              <div className="flex items-center gap-3">
                <AlertCircle className="w-5 h-5" style={{ color: 'var(--color-error)' }} />
                <div className="font-medium" style={{ color: 'var(--color-error)' }}>
                  Ошибка
                </div>
              </div>
              <p className="mt-2 text-sm" style={{ color: 'var(--color-charcoal)' }}>{error}</p>
            </div>
          )}

          {/* Steps list */}
          <div className="mb-8">
            <h3 className="text-sm font-medium mb-4" style={{ color: 'var(--color-charcoal)' }}>
              Этапы обработки
            </h3>
            <div className="space-y-2">
              {pipelineSteps.map((step, index) => {
                const status = getStepStatus(step);
                const stats = getStepStats(step);
                const Icon = STEP_ICONS[step];

                return (
                  <div
                    key={step}
                    className="flex items-center gap-3 py-2"
                  >
                    <div className="w-6 h-6 flex items-center justify-center">
                      {status === 'completed' ? (
                        <CheckCircle className="w-5 h-5" style={{ color: 'var(--color-success)' }} />
                      ) : status === 'running' ? (
                        <Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--color-info)' }} />
                      ) : status === 'current' ? (
                        <div className="w-5 h-5 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--color-info)', color: 'white' }}>
                          <span className="text-xs font-medium">{index + 1}</span>
                        </div>
                      ) : (
                        <Circle className="w-5 h-5" style={{ color: 'var(--color-accent-light)' }} />
                      )}
                    </div>
                    <span style={{ color: status === 'pending' ? 'var(--color-accent-light)' : 'var(--color-warm-gray)' }}>
                      <Icon className="w-4 h-4" />
                    </span>
                    <span
                      className="flex-1 text-sm"
                      style={{ color: status === 'pending' ? 'var(--color-accent-light)' : 'var(--color-charcoal)' }}
                    >
                      {STEP_LABELS[step]}
                    </span>
                    {stats && (
                      <span className="text-xs" style={{ color: 'var(--color-warm-gray)', fontFamily: 'var(--font-mono)' }}>
                        {stats}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Actions */}
          {isComplete && (
            <div className="flex justify-center">
              <Button onClick={onComplete}>
                Закрыть
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Step-by-step layout (split view)
  const availableTabs = getAvailableTabs();

  return (
    <div style={{ fontFamily: 'var(--font-body)', backgroundColor: 'var(--color-cream)' }} className="h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'var(--color-cream-dark)' }}>
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-semibold" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
            Пошаговая обработка
          </h2>
          {contentType === 'leadership' && (
            <span className="px-2 py-1 rounded-md text-xs font-medium" style={{ backgroundColor: 'var(--color-accent-light)', color: 'var(--color-charcoal)' }}>
              Лидерская история
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm truncate max-w-xs" style={{ color: 'var(--color-warm-gray)' }}>
            {filename}
          </span>
          <button
            onClick={onCancel}
            className="p-2 rounded-lg hover:bg-black/5 transition-colors"
          >
            <X className="w-5 h-5" style={{ color: 'var(--color-warm-gray)' }} />
          </button>
        </div>
      </div>

      {/* Main content: split view */}
      <div className="flex" style={{ height: 'calc(100vh - 200px)', minHeight: '500px' }}>
        {/* Left panel: Pipeline Control */}
        <div className="w-[340px] shrink-0 border-r overflow-y-auto" style={{ borderColor: 'var(--color-cream-dark)', backgroundColor: 'white' }}>
          <div className="p-6">
            {/* Next step card */}
            {!isComplete && (
              <div className="rounded-xl p-5 mb-6" style={{ backgroundColor: 'var(--color-cream)', border: '1px solid var(--color-cream-dark)' }}>
                <div className="flex items-center gap-3 mb-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: isLoading ? 'var(--color-info-light)' : 'var(--color-accent-light)' }}
                  >
                    {isLoading ? (
                      <Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--color-info)' }} />
                    ) : (
                      <span className="text-lg font-semibold" style={{ color: 'var(--color-accent)' }}>
                        {currentStepIndex + 1}
                      </span>
                    )}
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide font-medium" style={{ color: isLoading ? 'var(--color-info)' : 'var(--color-accent)' }}>
                      {isLoading ? 'Выполняется' : 'Следующий шаг'}
                    </div>
                    <div className="font-medium" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
                      {STEP_LABELS[currentStep]}
                    </div>
                  </div>
                </div>

                <p className="text-sm mb-4" style={{ color: 'var(--color-warm-gray)' }}>
                  {message || getStepDescription(currentStep)}
                </p>

                {/* Progress for long-running steps */}
                {isLoading && progress !== null && (
                  <div className="mb-4">
                    <ProgressBar progress={progress} size="sm" showLabel={false} />
                    <div className="mt-2 flex justify-between text-xs" style={{ color: 'var(--color-warm-gray)' }}>
                      <span>{Math.round(progress)}%</span>
                      {estimatedSeconds !== null && elapsedSeconds !== null && estimatedSeconds > 0 && (
                        <span style={{ color: 'var(--color-info)' }}>
                          {formatETA(estimatedSeconds, elapsedSeconds)}
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Execute button */}
                {!isLoading && (
                  <Button
                    onClick={() => runStep(currentStep)}
                    className="w-full flex items-center justify-center gap-2"
                  >
                    {currentStep === 'save' ? (
                      <Save className="w-4 h-4" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    Выполнить
                  </Button>
                )}
              </div>
            )}

            {/* Success card */}
            {isComplete && data.savedFiles && (
              <div className="rounded-xl p-5 mb-6" style={{ backgroundColor: 'var(--color-success-light)', border: '1px solid var(--color-success)' }}>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: 'white' }}>
                    <CheckCircle className="w-5 h-5" style={{ color: 'var(--color-success)' }} />
                  </div>
                  <div className="font-medium" style={{ color: 'var(--color-success)' }}>
                    Успешно сохранено
                  </div>
                </div>
                <ul className="text-sm space-y-1 mb-4" style={{ color: 'var(--color-charcoal)' }}>
                  {data.savedFiles.map((file) => (
                    <li key={file} className="flex items-center gap-2">
                      <span>•</span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>{file}</span>
                    </li>
                  ))}
                </ul>
                <Button onClick={onComplete} className="w-full">
                  Закрыть
                </Button>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="rounded-xl p-4 mb-6" style={{ backgroundColor: 'var(--color-error-light)', border: '1px solid var(--color-error)' }}>
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="w-4 h-4" style={{ color: 'var(--color-error)' }} />
                  <span className="font-medium text-sm" style={{ color: 'var(--color-error)' }}>Ошибка</span>
                </div>
                <p className="text-sm" style={{ color: 'var(--color-charcoal)' }}>{error}</p>
              </div>
            )}

            {/* Steps list */}
            <div className="mb-6">
              <h3 className="text-xs uppercase tracking-wide font-medium mb-4" style={{ color: 'var(--color-warm-gray)' }}>
                Этапы обработки
              </h3>
              <div className="space-y-1">
                {pipelineSteps.map((step, index) => {
                  const status = getStepStatus(step);
                  const stats = getStepStats(step);
                  const Icon = STEP_ICONS[step];
                  const isClickable = status === 'completed' && !isLoading;

                  return (
                    <button
                      key={step}
                      onClick={() => isClickable && handleStepClick(step)}
                      disabled={!isClickable}
                      className={`w-full flex items-center gap-3 py-2.5 px-3 rounded-lg text-left transition-colors ${
                        isClickable ? 'hover:bg-black/5 cursor-pointer' : 'cursor-default'
                      } ${status === 'current' || status === 'running' ? 'bg-black/[0.03]' : ''}`}
                    >
                      <div className="w-6 h-6 flex items-center justify-center shrink-0">
                        {status === 'completed' ? (
                          <CheckCircle className="w-5 h-5" style={{ color: 'var(--color-success)' }} />
                        ) : status === 'running' ? (
                          <Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--color-info)' }} />
                        ) : status === 'current' ? (
                          <div className="w-5 h-5 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--color-info)', color: 'white' }}>
                            <span className="text-xs font-medium">{index + 1}</span>
                          </div>
                        ) : (
                          <Circle className="w-5 h-5" style={{ color: 'var(--color-accent-light)' }} />
                        )}
                      </div>
                      <span
                        className="shrink-0"
                        style={{ color: status === 'pending' ? 'var(--color-accent-light)' : 'var(--color-warm-gray)' }}
                      >
                        <Icon className="w-4 h-4" />
                      </span>
                      <span
                        className="flex-1 text-sm"
                        style={{ color: status === 'pending' ? 'var(--color-accent-light)' : 'var(--color-charcoal)' }}
                      >
                        {STEP_LABELS[step]}
                      </span>
                      {stats && (
                        <span
                          className="text-xs shrink-0"
                          style={{ color: 'var(--color-warm-gray)', fontFamily: 'var(--font-mono)' }}
                        >
                          {stats}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Rerun settings for previous LLM step */}
            {previousLLMStep && !isLoading && !isComplete && (
              <div className="border-t pt-4" style={{ borderColor: 'var(--color-cream-dark)' }}>
                <button
                  onClick={() => setShowRerunSettings(!showRerunSettings)}
                  className="w-full flex items-center justify-between py-2 text-sm hover:opacity-80 transition-opacity"
                >
                  <span className="flex items-center gap-2" style={{ color: 'var(--color-warm-gray)' }}>
                    <RefreshCw className="w-4 h-4" />
                    Перезапустить {STEP_LABELS[previousLLMStep]}
                  </span>
                  {showRerunSettings ? (
                    <ChevronUp className="w-4 h-4" style={{ color: 'var(--color-warm-gray)' }} />
                  ) : (
                    <ChevronDown className="w-4 h-4" style={{ color: 'var(--color-warm-gray)' }} />
                  )}
                </button>

                {showRerunSettings && (
                  <div className="mt-3 p-4 rounded-lg space-y-4" style={{ backgroundColor: 'var(--color-cream)' }}>
                    {/* Model selector */}
                    {llmOptions.length > 0 && (() => {
                      const settingsKey = previousLLMStep === 'story' ? 'summarize' : previousLLMStep;
                      return (
                        <ModelSelector
                          label="Модель"
                          value={modelOverrides[previousLLMStep]}
                          defaultValue={defaultModels?.[settingsKey] || models[settingsKey] || ''}
                          options={llmOptions}
                          onChange={(value) => setModelOverrides((prev) => ({ ...prev, [previousLLMStep]: value }))}
                          compact
                        />
                      );
                    })()}

                    {/* Prompt selectors */}
                    {hasSelectablePrompts(getPromptsForStep(previousLLMStep)) && (
                      <>
                        <div className="border-t border-dashed" style={{ borderColor: 'var(--color-cream-dark)' }} />
                        <div>
                          <span className="text-xs mb-2 block" style={{ color: 'var(--color-warm-gray)' }}>Промпты:</span>
                          <div className="grid grid-cols-2 gap-2">
                            {getPromptsForStep(previousLLMStep)?.components.map((comp) => (
                              <ComponentPromptSelector
                                key={comp.component}
                                label={comp.component}
                                componentData={comp}
                                value={promptOverrides[previousLLMStep]?.[comp.component as keyof PromptOverrides]}
                                onChange={(value) =>
                                  updatePromptOverride(
                                    previousLLMStep,
                                    comp.component as keyof PromptOverrides,
                                    value
                                  )
                                }
                              />
                            ))}
                          </div>
                        </div>
                      </>
                    )}

                    {/* Rerun button */}
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => rerunStep(previousLLMStep)}
                      className="w-full flex items-center justify-center gap-2"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      Перезапустить
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right panel: Results Viewer */}
        <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: 'var(--color-cream)' }}>
          {/* Tabs */}
          {availableTabs.length > 0 && (
            <div className="shrink-0 border-b px-6 pt-4" style={{ borderColor: 'var(--color-cream-dark)', backgroundColor: 'white' }}>
              <div className="flex gap-1 -mb-px">
                {availableTabs.map((tab) => {
                  const isActive = activeTab === tab;
                  return (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
                        isActive
                          ? 'bg-[var(--color-cream)] border border-b-0'
                          : 'hover:bg-black/5'
                      }`}
                      style={{
                        borderColor: isActive ? 'var(--color-cream-dark)' : 'transparent',
                        color: isActive ? 'var(--color-charcoal)' : 'var(--color-warm-gray)',
                      }}
                    >
                      {TAB_LABELS[tab]}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === 'metadata' && data.metadata && (
              <div className="rounded-xl p-6" style={{ backgroundColor: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                <div className="flex items-center gap-3 mb-4">
                  <FileText className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
                  <h3 className="font-medium" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
                    Метаданные
                  </h3>
                  {data.metadata.duration_seconds && (
                    <span className="ml-auto flex items-center gap-1 text-sm" style={{ color: 'var(--color-warm-gray)' }}>
                      <Clock className="w-3.5 h-3.5" />
                      {formatDuration(data.metadata.duration_seconds)}
                    </span>
                  )}
                </div>
                <MetadataView metadata={data.metadata} />
              </div>
            )}

            {activeTab === 'rawTranscript' && data.rawTranscript && (
              <div className="rounded-xl p-6" style={{ backgroundColor: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                <div className="flex items-center gap-3 mb-4">
                  <FileAudio className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
                  <h3 className="font-medium" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
                    Сырая транскрипция
                  </h3>
                  <div className="ml-auto flex items-center gap-3 text-sm" style={{ color: 'var(--color-warm-gray)' }}>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {formatDuration(data.rawTranscript.duration_seconds)}
                    </span>
                    <span>{data.rawTranscript.segments.length} сегментов</span>
                  </div>
                </div>
                <RawTranscriptView transcript={data.rawTranscript} displayText={data.displayText || ''} />
              </div>
            )}

            {activeTab === 'cleanedTranscript' && data.cleanedTranscript && (
              <div className="rounded-xl p-6" style={{ backgroundColor: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                <div className="flex items-center gap-3 mb-4">
                  <Zap className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
                  <h3 className="font-medium" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
                    Очищенная транскрипция
                  </h3>
                  <div className="ml-auto flex items-center gap-3 text-sm" style={{ color: 'var(--color-warm-gray)' }}>
                    <span>{data.cleanedTranscript.cleaned_length.toLocaleString()} симв.</span>
                    <span>
                      -{Math.round(((data.cleanedTranscript.original_length - data.cleanedTranscript.cleaned_length) / data.cleanedTranscript.original_length) * 100)}%
                    </span>
                  </div>
                </div>
                <CleanedTranscriptView transcript={data.cleanedTranscript} />
              </div>
            )}

            {activeTab === 'longread' && data.longread && (
              <div className="rounded-xl p-6" style={{ backgroundColor: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                <div className="flex items-center gap-3 mb-4">
                  <BookOpen className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
                  <h3 className="font-medium" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
                    Лонгрид
                  </h3>
                  <div className="ml-auto flex items-center gap-3 text-sm" style={{ color: 'var(--color-warm-gray)' }}>
                    <span>{data.longread.total_sections} секций</span>
                    <span>{data.longread.total_word_count} слов</span>
                  </div>
                </div>
                <LongreadView longread={data.longread} />
              </div>
            )}

            {activeTab === 'summary' && data.summary && (
              <div className="rounded-xl p-6" style={{ backgroundColor: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                <div className="flex items-center gap-3 mb-4">
                  <ListChecks className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
                  <h3 className="font-medium" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
                    Конспект
                  </h3>
                  <div className="ml-auto flex items-center gap-3 text-sm" style={{ color: 'var(--color-warm-gray)' }}>
                    <span>{data.summary.key_concepts.length} концепций</span>
                    <span>{data.summary.quotes.length} цитат</span>
                  </div>
                </div>
                <SummaryView summary={data.summary} />
              </div>
            )}

            {activeTab === 'story' && data.story && (
              <div className="rounded-xl p-6" style={{ backgroundColor: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                <div className="flex items-center gap-3 mb-4">
                  <Heart className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
                  <h3 className="font-medium" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
                    Лидерская история
                  </h3>
                  <div className="ml-auto flex items-center gap-3 text-sm" style={{ color: 'var(--color-warm-gray)' }}>
                    <span>{data.story.total_blocks} блоков</span>
                    <span>{data.story.speed}</span>
                  </div>
                </div>
                <StoryView story={data.story} />
              </div>
            )}

            {activeTab === 'chunks' && data.chunks && (
              <div className="rounded-xl p-6" style={{ backgroundColor: 'white', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                <div className="flex items-center gap-3 mb-4">
                  <Layers className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
                  <h3 className="font-medium" style={{ fontFamily: 'var(--font-display)', color: 'var(--color-charcoal)' }}>
                    Семантические чанки
                  </h3>
                  <div className="ml-auto flex items-center gap-3 text-sm" style={{ color: 'var(--color-warm-gray)' }}>
                    <span>{data.chunks.total_chunks} чанков</span>
                    <span>~{data.chunks.avg_chunk_size} слов/чанк</span>
                  </div>
                </div>
                <ChunksView chunks={data.chunks} />
              </div>
            )}

            {/* Empty state */}
            {availableTabs.length === 0 && (
              <div className="h-full flex items-center justify-center text-center">
                <div>
                  <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center" style={{ backgroundColor: 'var(--color-cream-dark)' }}>
                    <FileText className="w-8 h-8" style={{ color: 'var(--color-accent-light)' }} />
                  </div>
                  <p className="text-sm" style={{ color: 'var(--color-warm-gray)' }}>
                    Результаты обработки появятся здесь
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function getStepDescription(step: PipelineStep): string {
  switch (step) {
    case 'parse':
      return 'Извлечение метаданных из имени файла';
    case 'transcribe':
      return 'Извлечение аудио и транскрипция через Whisper';
    case 'clean':
      return 'Очистка текста с использованием глоссария и LLM';
    case 'longread':
      return 'Генерация структурированного текста из транскрипции';
    case 'summarize':
      return 'Создание конспекта с ключевыми тезисами';
    case 'story':
      return 'Генерация лидерской истории (8 блоков)';
    case 'chunk':
      return 'Разбиение на семантические чанки по H2 заголовкам';
    case 'save':
      return 'Сохранение всех результатов в архив';
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
