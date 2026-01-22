import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  useStepParse,
  useStepTranscribe,
  useStepClean,
  useStepChunk,
  useStepLongread,
  useStepSummarize,
  useStepStory,
  useStepSlides,
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
  SlidesExtractionResult,
  SlideInput,
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
import { SlidesResultView } from '@/components/results/SlidesResultView';
import { CompletionCard } from '@/components/processing/CompletionCard';
import { ComponentPromptSelector } from '@/components/settings/ComponentPromptSelector';
import { ModelSelector } from '@/components/settings/ModelSelector';
import { buildLLMOptions } from '@/utils/modelUtils';
import { formatTime } from '@/utils/formatUtils';
import { useSettings } from '@/contexts/SettingsContext';
import {
  CheckCircle,
  Circle,
  AlertCircle,
  Play,
  Save,
  FileText,
  Layers,
  Clock,
  RefreshCw,
  Loader2,
  FileAudio,
  Sparkles,
  BookOpen,
  ListChecks,
  FolderOutput,
  Heart,
  ChevronRight,
  Settings,
  Paperclip,
  Images,
} from 'lucide-react';

import type { SlideFile } from '@/api/types';

interface StepByStepProps {
  filename: string;
  onComplete: () => void;
  onCancel: () => void;
  autoRun?: boolean;
  initialSlides?: SlideFile[];
}

interface StepData {
  metadata?: VideoMetadata;
  rawTranscript?: RawTranscript;
  displayText?: string;
  audioPath?: string;
  cleanedTranscript?: CleanedTranscript;
  slidesResult?: SlidesExtractionResult;
  chunks?: TranscriptChunks;
  longread?: Longread;
  summary?: Summary;
  story?: Story;
  savedFiles?: string[];
}

type ResultTab = 'metadata' | 'rawTranscript' | 'cleanedTranscript' | 'slides' | 'chunks' | 'longread' | 'summary' | 'story';

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
  slides: Images,
  longread: BookOpen,
  summarize: ListChecks,
  story: Heart,
  chunk: Layers,
  save: FolderOutput,
};

// Tab icons mapping
const TAB_ICONS: Record<ResultTab, React.ComponentType<{ className?: string }>> = {
  metadata: FileText,
  rawTranscript: FileAudio,
  cleanedTranscript: Sparkles,
  slides: Images,
  longread: BookOpen,
  summary: ListChecks,
  story: Heart,
  chunks: Layers,
};

export function StepByStep({ filename, onComplete, onCancel, autoRun = false, initialSlides = [] }: StepByStepProps) {
  // Track initial slides for future use in slides step (Phase 3)
  const hasSlides = initialSlides.length > 0;
  const [currentStep, setCurrentStep] = useState<PipelineStep>('parse');
  const [data, setData] = useState<StepData>({});
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ResultTab | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [parseError, setParseError] = useState<string | null>(null);
  const [expandedSettings, setExpandedSettings] = useState<PipelineStep | null>(null);
  const [showCleanedDiff, setShowCleanedDiff] = useState(false);
  const [showLongreadDiff, setShowLongreadDiff] = useState(false);
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
  const stepSlides = useStepSlides();
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

  // Determine pipeline steps based on content type and slides presence
  const contentType = data.metadata?.content_type || 'educational';
  const pipelineSteps = useMemo(() => {
    const baseSteps = contentType === 'leadership' ? LEADERSHIP_STEPS : EDUCATIONAL_STEPS;
    if (!hasSlides) return baseSteps;

    // Insert 'slides' between 'clean' and next step (longread/story)
    const cleanIdx = baseSteps.indexOf('clean');
    return [
      ...baseSteps.slice(0, cleanIdx + 1),
      'slides' as PipelineStep,
      ...baseSteps.slice(cleanIdx + 1),
    ];
  }, [contentType, hasSlides]);

  const isLoading =
    stepParse.isPending ||
    stepTranscribe.isPending ||
    stepClean.isPending ||
    stepSlides.isPending ||
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
      case 'slides':
        return {
          progress: stepSlides.progress,
          message: stepSlides.message,
          estimatedSeconds: stepSlides.estimatedSeconds,
          elapsedSeconds: stepSlides.elapsedSeconds,
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
      case 'slides': return !!data.cleanedTranscript && !!data.metadata && hasSlides;
      case 'longread':
        // If slides attached, need slidesResult; otherwise just cleanedTranscript
        if (hasSlides) {
          return !!data.cleanedTranscript && !!data.metadata && !!data.slidesResult;
        }
        return !!data.cleanedTranscript && !!data.metadata;
      case 'summarize': return !!data.cleanedTranscript && !!data.metadata;
      case 'story':
        // If slides attached, need slidesResult; otherwise just cleanedTranscript
        if (hasSlides) {
          return !!data.cleanedTranscript && !!data.metadata && !!data.slidesResult;
        }
        return !!data.cleanedTranscript && !!data.metadata;
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
      slides: ['slidesResult'],
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
          // Next step depends on slides presence
          if (hasSlides) {
            setCurrentStep('slides');
          } else {
            setCurrentStep(contentType === 'leadership' ? 'story' : 'longread');
          }
          break;

        case 'slides':
          if (!data.cleanedTranscript || !data.metadata || !hasSlides) return;
          // Convert SlideFile[] to SlideInput[] with base64
          const slideInputs: SlideInput[] = await Promise.all(
            initialSlides.map(async (slide) => {
              if (!slide.file) throw new Error(`No file for slide: ${slide.name}`);
              const base64 = await fileToBase64(slide.file);
              return {
                filename: slide.name,
                content_type: slide.file.type,
                data: base64,
              };
            })
          );
          const slidesResult = await stepSlides.mutate({
            slides: slideInputs,
          });
          setData((prev) => ({ ...prev, slidesResult }));
          setActiveTab('slides');
          setCurrentStep(contentType === 'leadership' ? 'story' : 'longread');
          break;

        case 'longread':
          if (!data.cleanedTranscript || !data.metadata) return;
          const longread = await stepLongread.mutate({
            cleaned_transcript: data.cleanedTranscript,
            metadata: data.metadata,
            model: getModelForStage('longread'),
            prompt_overrides: getPromptOverridesForApi('longread'),
            slides_text: data.slidesResult?.extracted_text,
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
            slides_text: data.slidesResult?.extracted_text,
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

  const getStepStatus = (step: PipelineStep): 'pending' | 'completed' | 'current' | 'next' | 'running' => {
    const stepIndex = pipelineSteps.indexOf(step);
    if (stepIndex < currentStepIndex) return 'completed';
    if (stepIndex === currentStepIndex) return isLoading ? 'running' : 'current';
    if (stepIndex === currentStepIndex + 1) return 'next';
    return 'pending';
  };

  // Check if step supports model/prompt selection
  const isLLMStep = (step: PipelineStep): step is StageWithPrompts => {
    return STAGES_WITH_PROMPTS.includes(step as StageWithPrompts);
  };

  // Rerun a step with current overrides
  const rerunStep = async (step: PipelineStep) => {
    setExpandedSettings(null);
    resetDataFromStep(step);
    setCurrentStep(step);
    await runStep(step);
  };

  // Get tab for step result
  const getTabForStep = (step: PipelineStep): ResultTab | null => {
    switch (step) {
      case 'parse': return 'metadata';
      case 'transcribe': return 'rawTranscript';
      case 'clean': return 'cleanedTranscript';
      case 'slides': return 'slides';
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
    if (data.slidesResult) tabs.push('slides');
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
    slides: 'Слайды',
    longread: 'Лонгрид',
    summary: 'Конспект',
    story: 'История',
    chunks: 'Чанки',
  };

  // Reset diff mode when tab changes
  useEffect(() => {
    setShowCleanedDiff(false);
    setShowLongreadDiff(false);
  }, [activeTab]);

  // Calculate totals for CompletionCard
  const calculateTotals = useCallback(() => {
    let totalTime = 0;
    let totalInputTokens = 0;
    let totalOutputTokens = 0;
    let totalCost = 0;

    // RawTranscript (transcription time)
    if (data.rawTranscript?.processing_time_sec) {
      totalTime += data.rawTranscript.processing_time_sec;
    }

    // CleanedTranscript
    if (data.cleanedTranscript) {
      totalTime += data.cleanedTranscript.processing_time_sec || 0;
      totalInputTokens += data.cleanedTranscript.tokens_used?.input || 0;
      totalOutputTokens += data.cleanedTranscript.tokens_used?.output || 0;
      totalCost += data.cleanedTranscript.cost || 0;
    }

    // SlidesResult
    if (data.slidesResult) {
      totalTime += data.slidesResult.processing_time_sec || 0;
      totalInputTokens += data.slidesResult.tokens_used?.input || 0;
      totalOutputTokens += data.slidesResult.tokens_used?.output || 0;
      totalCost += data.slidesResult.cost || 0;
    }

    // Longread (educational)
    if (data.longread) {
      totalTime += data.longread.processing_time_sec || 0;
      totalInputTokens += data.longread.tokens_used?.input || 0;
      totalOutputTokens += data.longread.tokens_used?.output || 0;
      totalCost += data.longread.cost || 0;
    }

    // Summary (educational)
    if (data.summary) {
      totalTime += data.summary.processing_time_sec || 0;
      totalInputTokens += data.summary.tokens_used?.input || 0;
      totalOutputTokens += data.summary.tokens_used?.output || 0;
      totalCost += data.summary.cost || 0;
    }

    // Story (leadership)
    if (data.story) {
      totalTime += data.story.processing_time_sec || 0;
      totalInputTokens += data.story.tokens_used?.input || 0;
      totalOutputTokens += data.story.tokens_used?.output || 0;
      totalCost += data.story.cost || 0;
    }

    return { totalTime, totalInputTokens, totalOutputTokens, totalCost };
  }, [data]);

  // Get step stats for display
  const getStepStats = (step: PipelineStep): string | null => {
    switch (step) {
      case 'transcribe':
        return data.rawTranscript ? formatDuration(data.rawTranscript.duration_seconds) : null;
      case 'clean':
        return data.cleanedTranscript ? `${data.cleanedTranscript.cleaned_length.toLocaleString()} симв.` : null;
      case 'slides':
        return data.slidesResult ? `${data.slidesResult.slides_count} слайдов` : null;
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
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-blue-50 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Анализ метаданных
          </h3>
          <p className="text-sm text-gray-500">
            {filename}
          </p>
        </div>
      </div>
    );
  }

  // Parse error state
  if (parseError) {
    return (
      <div className="py-12">
        <div className="max-w-md mx-auto text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-red-50 flex items-center justify-center">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Ошибка парсинга
          </h3>
          <p className="text-sm text-gray-500 mb-6">
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
      <div className="flex flex-col h-screen bg-slate-50">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200">
          <div className="flex flex-col gap-0.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              Автоматическая обработка
            </span>
            <h1 className="text-lg font-medium text-gray-900 truncate max-w-xl">
              {filename}
            </h1>
          </div>
          <button
            onClick={onCancel}
            disabled={isLoading && !isComplete}
            className="px-4 py-2 text-sm font-medium text-gray-600 bg-transparent border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Отменить
          </button>
        </header>

        {/* Main content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-lg mx-auto">
            {/* Current step card */}
            {!isComplete && (
              <div className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide font-semibold text-blue-600">
                      Выполняется
                    </div>
                    <div className="font-medium text-gray-900">
                      Шаг {currentStepIndex + 1} из {pipelineSteps.length}: {STEP_LABELS[currentStep]}
                    </div>
                  </div>
                </div>

                <p className="text-sm text-gray-600 mb-4">
                  {message || getStepDescription(currentStep)}
                </p>

                {progress !== null && (
                  <div>
                    <ProgressBar progress={progress} size="sm" showLabel={false} />
                    <div className="mt-2 flex justify-between text-xs text-gray-500">
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

            {/* Success card */}
            {isComplete && data.savedFiles && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 mb-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center">
                    <CheckCircle className="w-5 h-5 text-emerald-500" />
                  </div>
                  <div className="font-medium text-emerald-700">
                    Успешно сохранено
                  </div>
                </div>

                <p className="text-sm text-gray-700 mb-3">
                  Файлы сохранены в архив:
                </p>
                <ul className="text-sm space-y-1 text-gray-600">
                  {data.savedFiles.map((file) => (
                    <li key={file} className="flex items-center gap-2">
                      <span>•</span>
                      <span className="font-mono">{file}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-5 mb-6">
                <div className="flex items-center gap-3">
                  <AlertCircle className="w-5 h-5 text-red-500" />
                  <div className="font-medium text-red-700">Ошибка</div>
                </div>
                <p className="mt-2 text-sm text-gray-700">{error}</p>
              </div>
            )}

            {/* Steps list */}
            <div className="mb-8">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-4">
                Этапы обработки
              </h3>
              <div className="flex flex-col">
                {pipelineSteps.map((step, index) => {
                  const status = getStepStatus(step);
                  const stats = getStepStats(step);
                  const Icon = STEP_ICONS[step];

                  return (
                    <div key={step} className="relative">
                      <div className="flex items-start gap-3 px-3 py-2.5">
                        <div className="relative flex flex-col items-center pt-0.5">
                          {status === 'completed' ? (
                            <CheckCircle className="w-5 h-5 text-emerald-500 flex-shrink-0" />
                          ) : status === 'running' ? (
                            <Loader2 className="w-5 h-5 text-blue-500 animate-spin flex-shrink-0" />
                          ) : status === 'current' ? (
                            <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                              <ChevronRight className="w-3 h-3 text-white" />
                            </div>
                          ) : (
                            <Circle className="w-5 h-5 text-gray-300 flex-shrink-0" />
                          )}
                          {index < pipelineSteps.length - 1 && (
                            <div className={`absolute top-6 left-1/2 -translate-x-1/2 w-0.5 h-8 ${
                              status === 'completed' ? 'bg-emerald-500' : 'bg-gray-200'
                            }`} />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <Icon className={`w-4 h-4 ${
                              status === 'pending' ? 'text-gray-300' : 'text-gray-400'
                            }`} />
                            <span className={`text-sm font-medium ${
                              status === 'pending' ? 'text-gray-400' : 'text-gray-900'
                            }`}>
                              {STEP_LABELS[step]}
                            </span>
                          </div>
                        </div>
                        {stats && (
                          <span className="text-xs text-gray-400 font-mono">
                            {stats}
                          </span>
                        )}
                      </div>
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
      </div>
    );
  }

  // Step-by-step layout (split view)
  const availableTabs = getAvailableTabs();

  return (
    <div className="flex flex-col h-[85vh] min-h-[700px] max-h-[950px] bg-slate-50">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-3 bg-white border-b border-gray-200 shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex flex-col gap-0 min-w-0">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">
              Пошаговая обработка
            </span>
            <h1 className="text-sm font-medium text-gray-900 truncate">
              {filename}
            </h1>
          </div>
          {contentType === 'leadership' && (
            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-700 shrink-0">
              Лидерская история
            </span>
          )}
          {hasSlides && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 shrink-0">
              <Paperclip className="w-3 h-3" />
              {initialSlides.length} слайдов
            </span>
          )}
        </div>
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors shrink-0"
        >
          Отменить
        </button>
      </header>

      {/* Main content area */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left Panel - Pipeline Control */}
        <aside className="w-96 flex flex-col gap-3 p-4 bg-white border-r border-gray-200 overflow-y-auto shrink-0">
          {/* Next Step Action - Primary CTA */}
          {!isComplete && (
            <div className="p-5 bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-xl relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-blue-400" />
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-white px-2 py-1 rounded">
                  {isLoading ? 'Выполняется' : 'Следующий'}
                </span>
                <span className="text-xs text-blue-700 font-medium">
                  Шаг {currentStepIndex + 1}
                </span>
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-1">
                {STEP_LABELS[currentStep]}
              </h3>
              <p className="text-sm text-gray-600 mb-4 leading-relaxed">
                {getStepDescription(currentStep)}
              </p>

              {/* Progress for long-running steps */}
              {isLoading && progress !== null && (
                <div className="mb-4">
                  <ProgressBar progress={progress} size="sm" showLabel={false} />
                  <div className="mt-2 flex justify-between text-xs text-gray-500">
                    <span>{Math.round(progress)}%</span>
                    {estimatedSeconds !== null && elapsedSeconds !== null && estimatedSeconds > 0 && (
                      <span className="text-blue-600">
                        {formatETA(estimatedSeconds, elapsedSeconds)}
                      </span>
                    )}
                  </div>
                </div>
              )}

              {!isLoading && (
                <button
                  className="flex items-center justify-center gap-2 w-full px-5 py-3 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all shadow-md hover:shadow-lg disabled:opacity-70 disabled:cursor-not-allowed"
                  disabled={isLoading}
                  onClick={() => runStep(currentStep)}
                >
                  {currentStep === 'save' ? (
                    <Save className="w-4 h-4" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  Выполнить
                </button>
              )}

              {isLoading && (
                <div className="flex items-center justify-center gap-2 w-full px-5 py-3 text-sm font-semibold text-blue-600 bg-white/50 rounded-lg">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Выполняется...
                </div>
              )}
            </div>
          )}

          {/* Success card with totals */}
          {isComplete && data.savedFiles && (
            <CompletionCard
              files={data.savedFiles}
              totals={calculateTotals()}
              onClose={onComplete}
            />
          )}

          {/* Error */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="w-4 h-4 text-red-500" />
                <span className="font-medium text-sm text-red-700">Ошибка</span>
              </div>
              <p className="text-sm text-gray-700">{error}</p>
            </div>
          )}

          {/* Pipeline Steps */}
          <div className="flex-1 min-h-0">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              Этапы обработки
            </h4>
            <div className="flex flex-col">
              {pipelineSteps.map((step, index) => {
                const status = getStepStatus(step);
                const Icon = STEP_ICONS[step];
                const isExpanded = expandedSettings === step;
                const isCurrent = status === 'completed' && getTabForStep(step) === activeTab && !isLoading;
                const hasSettings = isLLMStep(step) && isCurrent;

                return (
                  <div key={step} className="relative">
                    <div
                      className={`flex items-start gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors ${
                        (status === 'completed') ? 'hover:bg-gray-50' : ''
                      }`}
                      onClick={() => {
                        if (status === 'completed') {
                          const tabForStep = getTabForStep(step);
                          if (tabForStep) setActiveTab(tabForStep);
                        }
                      }}
                    >
                      <div className="relative flex flex-col items-center">
                        {status === 'completed' ? (
                          <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        ) : status === 'running' ? (
                          <Loader2 className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" />
                        ) : status === 'current' ? (
                          <div className="w-4 h-4 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                            <ChevronRight className="w-2.5 h-2.5 text-white" />
                          </div>
                        ) : (
                          <Circle className="w-4 h-4 text-gray-300 flex-shrink-0" />
                        )}
                        {index < pipelineSteps.length - 1 && (
                          <div className={`absolute top-4 left-1/2 -translate-x-1/2 w-0.5 h-4 ${
                            status === 'completed' ? 'bg-emerald-500' : 'bg-gray-200'
                          }`} />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <Icon className={`w-4 h-4 ${
                            status === 'current' || status === 'running' ? 'text-blue-500' :
                            status === 'completed' ? 'text-gray-500' : 'text-gray-300'
                          }`} />
                          <span className={`text-sm font-medium ${
                            status === 'pending' || status === 'next' ? 'text-gray-400' : 'text-gray-900'
                          }`}>
                            {STEP_LABELS[step]}
                          </span>
                          {isCurrent && (
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600 bg-emerald-50 px-1 py-0.5 rounded">
                              текущий
                            </span>
                          )}
                        </div>
                        {hasSettings && (
                          <button
                            className="flex items-center gap-1 mt-1 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 bg-gray-100 rounded hover:bg-gray-200 transition-colors"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedSettings(isExpanded ? null : step);
                            }}
                          >
                            <Settings className="w-2.5 h-2.5" />
                            <span>Настройки</span>
                            <ChevronRight className={`w-2.5 h-2.5 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                          </button>
                        )}
                      </div>
                      {isCurrent && (
                        <button
                          className="p-1 text-gray-400 hover:text-orange-600 hover:bg-orange-50 rounded transition-colors"
                          onClick={(e) => {
                            e.stopPropagation();
                            rerunStep(step);
                          }}
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>

                    {/* Expanded Settings Panel */}
                    {isExpanded && hasSettings && isLLMStep(step) && (
                      <div className="ml-6 mt-1 mb-1 p-2 bg-gray-50 rounded-lg border border-gray-100 text-xs">
                        {/* Model selector */}
                        {llmOptions.length > 0 && (() => {
                          const settingsKey = step === 'story' ? 'summarize' : step;
                          return (
                            <div className="flex flex-col gap-1.5 mb-3">
                              <label className="text-xs font-semibold uppercase tracking-wider text-gray-400">Модель</label>
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-medium text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-mono">
                                  {(modelOverrides[step] || defaultModels?.[settingsKey] || models[settingsKey] || '').includes('claude') ? 'cloud' : 'local'}
                                </span>
                                <ModelSelector
                                  value={modelOverrides[step]}
                                  defaultValue={defaultModels?.[settingsKey] || models[settingsKey] || ''}
                                  options={llmOptions}
                                  onChange={(value) => setModelOverrides((prev) => ({ ...prev, [step]: value }))}
                                  compact
                                />
                              </div>
                            </div>
                          );
                        })()}

                        {/* Prompt selectors */}
                        {hasSelectablePrompts(getPromptsForStep(step)) && (
                          <>
                            <div className="h-px bg-gray-200 my-3" />
                            <div className="flex flex-col gap-1.5">
                              <label className="text-xs font-semibold uppercase tracking-wider text-gray-400">Промпты</label>
                              <div className="grid grid-cols-2 gap-2">
                                {getPromptsForStep(step)?.components.map((comp) => (
                                  <ComponentPromptSelector
                                    key={comp.component}
                                    label={comp.component}
                                    componentData={comp}
                                    value={promptOverrides[step]?.[comp.component as keyof PromptOverrides]}
                                    onChange={(value) =>
                                      updatePromptOverride(
                                        step,
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
                        <button
                          className="flex items-center justify-center gap-2 w-full mt-3 px-3 py-2 text-xs font-medium text-orange-600 bg-orange-50 border border-orange-200 rounded-lg hover:bg-orange-100 transition-colors"
                          onClick={() => rerunStep(step)}
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                          Перезапустить
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </aside>

        {/* Right Panel - Results Viewer */}
        <main className="flex-1 flex flex-col bg-slate-50 overflow-hidden">
          {availableTabs.length > 0 ? (
            <>
              {/* Tabs */}
              <div className="flex gap-0.5 px-3 py-2 bg-white border-b border-gray-200 shrink-0">
                {availableTabs.map(tab => {
                  const Icon = TAB_ICONS[tab];
                  return (
                    <button
                      key={tab}
                      className={`flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg whitespace-nowrap transition-all ${
                        activeTab === tab
                          ? 'text-blue-600 bg-blue-50 border border-blue-200'
                          : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50 border border-transparent'
                      }`}
                      onClick={() => setActiveTab(tab)}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{TAB_LABELS[tab]}</span>
                    </button>
                  );
                })}
              </div>

              {/* Content Area */}
              <div className="flex-1 p-3 overflow-y-auto min-h-0">
                {activeTab === 'metadata' && data.metadata && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                      <h3 className="text-sm font-semibold text-gray-900">Метаданные</h3>
                      {data.metadata.duration_seconds && (
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <Clock className="w-3 h-3" />
                          {formatDuration(data.metadata.duration_seconds)}
                        </div>
                      )}
                    </div>
                    <div className="p-4 flex-1 overflow-y-auto">
                      <MetadataView metadata={data.metadata} />
                    </div>
                  </div>
                )}

                {activeTab === 'rawTranscript' && data.rawTranscript && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                      <h3 className="text-sm font-semibold text-gray-900">Сырая транскрипция</h3>
                      {data.rawTranscript.processing_time_sec !== undefined && (
                        <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                          {formatTime(data.rawTranscript.processing_time_sec)}
                        </span>
                      )}
                    </div>
                    <div className="p-4 flex-1 overflow-hidden min-h-0">
                      <RawTranscriptView transcript={data.rawTranscript} displayText={data.displayText || ''} />
                    </div>
                  </div>
                )}

                {activeTab === 'cleanedTranscript' && data.cleanedTranscript && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    {!showCleanedDiff && (
                      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                        <h3 className="text-sm font-semibold text-gray-900">Очищенная транскрипция</h3>
                        {data.cleanedTranscript.processing_time_sec !== undefined && (
                          <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                            {formatTime(data.cleanedTranscript.processing_time_sec)}
                          </span>
                        )}
                      </div>
                    )}
                    <div className={showCleanedDiff ? 'flex-1 min-h-0' : 'p-4 flex-1 overflow-hidden min-h-0'}>
                      <CleanedTranscriptView
                        transcript={data.cleanedTranscript}
                        rawText={data.displayText}
                        showDiff={showCleanedDiff}
                        onToggleDiff={() => setShowCleanedDiff(!showCleanedDiff)}
                      />
                    </div>
                  </div>
                )}

                {activeTab === 'slides' && data.slidesResult && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                      <h3 className="text-sm font-semibold text-gray-900">Извлечённые данные со слайдов</h3>
                      {data.slidesResult.processing_time_sec !== undefined && (
                        <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                          {formatTime(data.slidesResult.processing_time_sec)}
                        </span>
                      )}
                    </div>
                    <div className="p-4 flex-1 overflow-hidden min-h-0">
                      <SlidesResultView slidesResult={data.slidesResult} />
                    </div>
                  </div>
                )}

                {activeTab === 'longread' && data.longread && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    {!showLongreadDiff && (
                      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                        <h3 className="text-sm font-semibold text-gray-900">Лонгрид</h3>
                        {data.longread.processing_time_sec !== undefined && (
                          <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                            {formatTime(data.longread.processing_time_sec)}
                          </span>
                        )}
                      </div>
                    )}
                    <div className={showLongreadDiff ? 'flex-1 min-h-0' : 'p-4 flex-1 overflow-y-auto'}>
                      <LongreadView
                        longread={data.longread}
                        cleanedText={data.cleanedTranscript?.text}
                        cleanedChars={data.cleanedTranscript?.cleaned_length}
                        showDiff={showLongreadDiff}
                        onToggleDiff={() => setShowLongreadDiff(!showLongreadDiff)}
                      />
                    </div>
                  </div>
                )}

                {activeTab === 'summary' && data.summary && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                      <h3 className="text-sm font-semibold text-gray-900">Конспект</h3>
                      {data.summary.processing_time_sec !== undefined && (
                        <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                          {formatTime(data.summary.processing_time_sec)}
                        </span>
                      )}
                    </div>
                    <div className="p-4 flex-1 overflow-y-auto">
                      <SummaryView summary={data.summary} />
                    </div>
                  </div>
                )}

                {activeTab === 'story' && data.story && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                      <h3 className="text-sm font-semibold text-gray-900">Лидерская история</h3>
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <span>{data.story.total_blocks} блоков</span>
                        <span>{data.story.speed}</span>
                      </div>
                    </div>
                    <div className="p-4 flex-1 overflow-y-auto">
                      <StoryView story={data.story} />
                    </div>
                  </div>
                )}

                {activeTab === 'chunks' && data.chunks && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                      <h3 className="text-sm font-semibold text-gray-900">Чанки</h3>
                    </div>
                    <div className="p-4 flex-1 overflow-y-auto">
                      <ChunksView chunks={data.chunks} />
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
              <FileText className="w-12 h-12 mb-3 opacity-40" />
              <p>Результаты появятся после выполнения первого шага</p>
            </div>
          )}
        </main>
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
    case 'slides':
      return 'Извлечение текста и таблиц со слайдов через Vision API';
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

/**
 * Convert File to base64 string (without data URL prefix).
 */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      // Remove "data:image/jpeg;base64," prefix
      const base64 = dataUrl.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
