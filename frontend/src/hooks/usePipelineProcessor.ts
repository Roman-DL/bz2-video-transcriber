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
import type {
  VideoMetadata,
  RawTranscript,
  CleanedTranscript,
  TranscriptChunks,
  Longread,
  Summary,
  Story,
  SlidesExtractionResult,
  SaveResult,
  SlideInput,
  PipelineStep,
  ContentType,
  PromptOverrides,
} from '@/api/types';
import { EDUCATIONAL_STEPS, LEADERSHIP_STEPS } from '@/api/types';
import { useSettings } from '@/contexts/SettingsContext';

import type { SlideFile } from '@/api/types';

// ═══════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════

export interface StepData {
  metadata?: VideoMetadata;
  rawTranscript?: RawTranscript;
  displayText?: string;
  audioPath?: string;
  cleanedTranscript?: CleanedTranscript;
  slidesExtraction?: SlidesExtractionResult;
  chunks?: TranscriptChunks;
  longread?: Longread;
  summary?: Summary;
  story?: Story;
  saveResult?: SaveResult;
}

export type ProcessorStatus = 'idle' | 'running' | 'completed' | 'error';
export type StepStatus = 'pending' | 'completed' | 'current' | 'next' | 'running' | 'error';

export interface UsePipelineProcessorOptions {
  filename: string;
  initialSlides?: SlideFile[];
  autoRun?: boolean;
  onStepComplete?: (step: PipelineStep, data: StepData) => void;
}

export interface ProgressInfo {
  progress: number | null;
  message: string | null;
  estimatedSeconds: number | null;
  elapsedSeconds: number | null;
}

// Stages that support prompt/model selection
export const STAGES_WITH_PROMPTS = ['clean', 'longread', 'summarize', 'story'] as const;
export type StageWithPrompts = (typeof STAGES_WITH_PROMPTS)[number];

// Prompt overrides state per stage
export type StagePromptOverrides = Record<StageWithPrompts, PromptOverrides>;

// Model overrides state per stage
export type StageModelOverrides = Record<StageWithPrompts, string | undefined>;

export interface UsePipelineProcessorResult {
  // Status
  status: ProcessorStatus;
  currentStep: PipelineStep;
  currentStepIndex: number;
  pipelineSteps: PipelineStep[];
  isLoading: boolean;
  isComplete: boolean;
  isInitializing: boolean;
  parseError: string | null;

  // Data
  data: StepData;
  contentType: ContentType;
  hasSlides: boolean;

  // Progress
  progressInfo: ProgressInfo;
  error: string | null;

  // Step configuration (for step-by-step mode)
  promptOverrides: StagePromptOverrides;
  modelOverrides: StageModelOverrides;
  setPromptOverrides: React.Dispatch<React.SetStateAction<StagePromptOverrides>>;
  setModelOverrides: React.Dispatch<React.SetStateAction<StageModelOverrides>>;
  updatePromptOverride: (stage: StageWithPrompts, component: keyof PromptOverrides, value: string | undefined) => void;
  getModelForStage: (stage: StageWithPrompts) => string | undefined;

  // Actions
  runStep: (step: PipelineStep) => Promise<void>;
  retry: () => void;
  resetDataFromStep: (step: PipelineStep) => void;

  // Helpers
  getStepStatus: (step: PipelineStep) => StepStatus;
  hasDataForStep: (step: PipelineStep) => boolean;

  // Totals for completion card
  calculateTotals: () => {
    totalTime: number;
    totalInputTokens: number;
    totalOutputTokens: number;
    totalCost: number;
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// Hook Implementation
// ═══════════════════════════════════════════════════════════════════════════

export function usePipelineProcessor({
  filename,
  initialSlides = [],
  autoRun = false,
  onStepComplete,
}: UsePipelineProcessorOptions): UsePipelineProcessorResult {
  const hasSlides = initialSlides.length > 0;
  const { models } = useSettings();

  // ─────────────────────────────────────────────────────────────────────────
  // State
  // ─────────────────────────────────────────────────────────────────────────
  const [currentStep, setCurrentStep] = useState<PipelineStep>('parse');
  const [data, setData] = useState<StepData>({});
  const [error, setError] = useState<string | null>(null);
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

  // ─────────────────────────────────────────────────────────────────────────
  // Step Hooks
  // ─────────────────────────────────────────────────────────────────────────
  const stepParse = useStepParse();
  const stepTranscribe = useStepTranscribe();
  const stepClean = useStepClean();
  const stepChunk = useStepChunk();
  const stepLongread = useStepLongread();
  const stepSummarize = useStepSummarize();
  const stepStory = useStepStory();
  const stepSlides = useStepSlides();
  const stepSave = useStepSave();

  // ─────────────────────────────────────────────────────────────────────────
  // Derived State
  // ─────────────────────────────────────────────────────────────────────────
  const contentType: ContentType = data.metadata?.contentType || 'educational';

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

  const currentStepIndex = pipelineSteps.indexOf(currentStep);
  const isComplete = data.saveResult !== undefined;

  // Status calculation
  const status: ProcessorStatus = useMemo(() => {
    if (isComplete) return 'completed';
    if (error) return 'error';
    if (isLoading) return 'running';
    return 'idle';
  }, [isComplete, error, isLoading]);

  // ─────────────────────────────────────────────────────────────────────────
  // Progress Tracking
  // ─────────────────────────────────────────────────────────────────────────
  const progressInfo: ProgressInfo = useMemo(() => {
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
        return { progress: null, message: null, estimatedSeconds: null, elapsedSeconds: null };
    }
  }, [currentStep, stepTranscribe, stepClean, stepLongread, stepSummarize, stepStory, stepSlides]);

  // ─────────────────────────────────────────────────────────────────────────
  // Helpers
  // ─────────────────────────────────────────────────────────────────────────
  const hasDataForStep = useCallback((step: PipelineStep): boolean => {
    switch (step) {
      case 'parse': return true;
      case 'transcribe': return !!data.metadata;
      case 'clean': return !!data.rawTranscript && !!data.metadata;
      case 'slides': return !!data.cleanedTranscript && !!data.metadata && hasSlides;
      case 'longread':
        if (hasSlides) {
          return !!data.cleanedTranscript && !!data.metadata && !!data.slidesExtraction;
        }
        return !!data.cleanedTranscript && !!data.metadata;
      case 'summarize': return !!data.cleanedTranscript && !!data.metadata;
      case 'story':
        if (hasSlides) {
          return !!data.cleanedTranscript && !!data.metadata && !!data.slidesExtraction;
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
  }, [data, hasSlides, contentType]);

  const getStepStatus = useCallback((step: PipelineStep): StepStatus => {
    const stepIndex = pipelineSteps.indexOf(step);
    if (error && stepIndex === currentStepIndex) return 'error';
    if (stepIndex < currentStepIndex) return 'completed';
    if (stepIndex === currentStepIndex) return isLoading ? 'running' : 'current';
    if (stepIndex === currentStepIndex + 1) return 'next';
    return 'pending';
  }, [pipelineSteps, currentStepIndex, isLoading, error]);

  const updatePromptOverride = useCallback((
    stage: StageWithPrompts,
    component: keyof PromptOverrides,
    value: string | undefined
  ) => {
    setPromptOverrides(prev => ({
      ...prev,
      [stage]: {
        ...prev[stage],
        [component]: value,
      },
    }));
  }, []);

  const getPromptOverridesForApi = useCallback((stage: StageWithPrompts): PromptOverrides | undefined => {
    const overrides = promptOverrides[stage];
    const nonEmpty = Object.fromEntries(
      Object.entries(overrides).filter(([, v]) => v !== undefined)
    );
    return Object.keys(nonEmpty).length > 0 ? nonEmpty : undefined;
  }, [promptOverrides]);

  const getModelForStage = useCallback((stage: StageWithPrompts): string | undefined => {
    const settingsKey = stage === 'story' ? 'summarize' : stage;
    return modelOverrides[stage] || models[settingsKey];
  }, [modelOverrides, models]);

  // Reset data from a specific step onwards
  const resetDataFromStep = useCallback((step: PipelineStep) => {
    const stepIndex = pipelineSteps.indexOf(step);
    const fieldsToReset: Record<PipelineStep, (keyof StepData)[]> = {
      parse: ['metadata'],
      transcribe: ['rawTranscript', 'displayText', 'audioPath'],
      clean: ['cleanedTranscript'],
      slides: ['slidesExtraction'],
      longread: ['longread'],
      summarize: ['summary'],
      story: ['story'],
      chunk: ['chunks'],
      save: ['saveResult'],
    };

    setData(prev => {
      const next = { ...prev };
      for (let i = stepIndex; i < pipelineSteps.length; i++) {
        fieldsToReset[pipelineSteps[i]]?.forEach(field => {
          next[field] = undefined;
        });
      }
      return next;
    });
    setError(null);
  }, [pipelineSteps]);

  // ─────────────────────────────────────────────────────────────────────────
  // Step Execution
  // ─────────────────────────────────────────────────────────────────────────
  const runStep = useCallback(async (step: PipelineStep) => {
    setError(null);

    try {
      switch (step) {
        case 'parse': {
          const metadata = await stepParse.mutateAsync({
            videoFilename: filename,
            whisperModel: models.transcribe,
          });
          setData(prev => ({ ...prev, metadata }));
          setCurrentStep('transcribe');
          onStepComplete?.('parse', { ...data, metadata });
          break;
        }

        case 'transcribe': {
          const transcribeResult = await stepTranscribe.mutate({
            videoFilename: filename,
            whisperModel: models.transcribe,
          });
          const newData = {
            ...data,
            rawTranscript: transcribeResult.rawTranscript,
            displayText: transcribeResult.displayText,
            audioPath: transcribeResult.audioPath,
          };
          setData(newData);
          setCurrentStep('clean');
          onStepComplete?.('transcribe', newData);
          break;
        }

        case 'clean': {
          if (!data.rawTranscript || !data.metadata) return;
          const cleanedTranscript = await stepClean.mutate({
            rawTranscript: data.rawTranscript,
            metadata: data.metadata,
            model: getModelForStage('clean'),
            promptOverrides: getPromptOverridesForApi('clean'),
          });
          const newData = { ...data, cleanedTranscript };
          setData(newData);
          if (hasSlides) {
            setCurrentStep('slides');
          } else {
            setCurrentStep(contentType === 'leadership' ? 'story' : 'longread');
          }
          onStepComplete?.('clean', newData);
          break;
        }

        case 'slides': {
          if (!data.cleanedTranscript || !data.metadata || !hasSlides) return;
          const slideInputs: SlideInput[] = await Promise.all(
            initialSlides.map(async slide => {
              if (!slide.file) throw new Error(`No file for slide: ${slide.name}`);
              const base64 = await fileToBase64(slide.file);
              return {
                filename: slide.name,
                contentType: slide.file.type,
                data: base64,
              };
            })
          );
          const slidesExtraction = await stepSlides.mutate({
            slides: slideInputs,
          });
          const newData = { ...data, slidesExtraction };
          setData(newData);
          setCurrentStep(contentType === 'leadership' ? 'story' : 'longread');
          onStepComplete?.('slides', newData);
          break;
        }

        case 'longread': {
          if (!data.cleanedTranscript || !data.metadata) return;
          const longread = await stepLongread.mutate({
            cleanedTranscript: data.cleanedTranscript,
            metadata: data.metadata,
            model: getModelForStage('longread'),
            promptOverrides: getPromptOverridesForApi('longread'),
            slidesText: data.slidesExtraction?.extractedText,
          });
          const newData = { ...data, longread };
          setData(newData);
          setCurrentStep('summarize');
          onStepComplete?.('longread', newData);
          break;
        }

        case 'summarize': {
          if (!data.cleanedTranscript || !data.metadata) return;
          const summary = await stepSummarize.mutate({
            cleanedTranscript: data.cleanedTranscript,
            metadata: data.metadata,
            model: getModelForStage('summarize'),
            promptOverrides: getPromptOverridesForApi('summarize'),
          });
          const newData = { ...data, summary };
          setData(newData);
          setCurrentStep('chunk');
          onStepComplete?.('summarize', newData);
          break;
        }

        case 'story': {
          if (!data.cleanedTranscript || !data.metadata) return;
          const story = await stepStory.mutate({
            cleanedTranscript: data.cleanedTranscript,
            metadata: data.metadata,
            model: getModelForStage('story'),
            promptOverrides: getPromptOverridesForApi('story'),
            slidesText: data.slidesExtraction?.extractedText,
          });
          const newData = { ...data, story };
          setData(newData);
          setCurrentStep('chunk');
          onStepComplete?.('story', newData);
          break;
        }

        case 'chunk': {
          if (!data.metadata) return;
          let markdownContent: string;
          if (contentType === 'leadership') {
            if (!data.story) return;
            markdownContent = data.story.blocks
              .map(b => `## ${b.blockNumber}️⃣ ${b.blockName}\n\n${b.content}`)
              .join('\n\n');
          } else {
            if (!data.longread) return;
            markdownContent = data.longread.sections
              .map(s => `## ${s.title}\n\n${s.content}`)
              .join('\n\n');
          }
          const chunks = await stepChunk.mutateAsync({
            markdownContent: markdownContent,
            metadata: data.metadata,
            summary: data.summary,
            longread: data.longread,
            story: data.story,
          });
          const newData = { ...data, chunks };
          setData(newData);
          setCurrentStep('save');
          onStepComplete?.('chunk', newData);
          break;
        }

        case 'save': {
          if (contentType === 'leadership') {
            if (!data.metadata || !data.rawTranscript || !data.cleanedTranscript || !data.chunks || !data.story) return;
            const saveResult = await stepSave.mutateAsync({
              metadata: data.metadata,
              rawTranscript: data.rawTranscript,
              cleanedTranscript: data.cleanedTranscript,
              chunks: data.chunks,
              story: data.story,
              audioPath: data.audioPath,
              slidesExtraction: data.slidesExtraction,
            });
            const newData = { ...data, saveResult };
            setData(newData);
            onStepComplete?.('save', newData);
          } else {
            if (!data.metadata || !data.rawTranscript || !data.cleanedTranscript || !data.chunks || !data.longread || !data.summary) return;
            const saveResult = await stepSave.mutateAsync({
              metadata: data.metadata,
              rawTranscript: data.rawTranscript,
              cleanedTranscript: data.cleanedTranscript,
              chunks: data.chunks,
              longread: data.longread,
              summary: data.summary,
              audioPath: data.audioPath,
              slidesExtraction: data.slidesExtraction,
            });
            const newData = { ...data, saveResult };
            setData(newData);
            onStepComplete?.('save', newData);
          }
          break;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка выполнения');
    }
  }, [
    filename,
    models,
    data,
    hasSlides,
    initialSlides,
    contentType,
    getModelForStage,
    getPromptOverridesForApi,
    stepParse,
    stepTranscribe,
    stepClean,
    stepSlides,
    stepLongread,
    stepSummarize,
    stepStory,
    stepChunk,
    stepSave,
    onStepComplete,
  ]);

  const retry = useCallback(() => {
    setError(null);
    runStep(currentStep);
  }, [currentStep, runStep]);

  // ─────────────────────────────────────────────────────────────────────────
  // Auto-parse on mount
  // ─────────────────────────────────────────────────────────────────────────
  useEffect(() => {
    let mounted = true;

    const autoParse = async () => {
      try {
        const metadata = await stepParse.mutateAsync({
          videoFilename: filename,
          whisperModel: models.transcribe,
        });
        if (mounted) {
          setData({ metadata });
          setCurrentStep('transcribe');
          setIsInitializing(false);
          onStepComplete?.('parse', { metadata });
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
    // Intentionally only depend on filename - we want to parse once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filename]);

  // ─────────────────────────────────────────────────────────────────────────
  // Auto-run effect (for autoRun mode - automatically executes pipeline steps)
  // ─────────────────────────────────────────────────────────────────────────
  const isRunningRef = useRef(false);

  useEffect(() => {
    if (!autoRun) return;
    if (isInitializing) return;
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
  }, [autoRun, currentStep, isLoading, isComplete, error, isInitializing, hasDataForStep, runStep]);

  // ─────────────────────────────────────────────────────────────────────────
  // Calculate Totals
  // ─────────────────────────────────────────────────────────────────────────
  const calculateTotals = useCallback(() => {
    let totalTime = 0;
    let totalInputTokens = 0;
    let totalOutputTokens = 0;
    let totalCost = 0;

    if (data.rawTranscript?.processingTimeSec) {
      totalTime += data.rawTranscript.processingTimeSec;
    }

    if (data.cleanedTranscript) {
      totalTime += data.cleanedTranscript.processingTimeSec || 0;
      totalInputTokens += data.cleanedTranscript.tokensUsed?.input || 0;
      totalOutputTokens += data.cleanedTranscript.tokensUsed?.output || 0;
      totalCost += data.cleanedTranscript.cost || 0;
    }

    if (data.slidesExtraction) {
      totalTime += data.slidesExtraction.processingTimeSec || 0;
      totalInputTokens += data.slidesExtraction.tokensUsed?.input || 0;
      totalOutputTokens += data.slidesExtraction.tokensUsed?.output || 0;
      totalCost += data.slidesExtraction.cost || 0;
    }

    if (data.longread) {
      totalTime += data.longread.processingTimeSec || 0;
      totalInputTokens += data.longread.tokensUsed?.input || 0;
      totalOutputTokens += data.longread.tokensUsed?.output || 0;
      totalCost += data.longread.cost || 0;
    }

    if (data.summary) {
      totalTime += data.summary.processingTimeSec || 0;
      totalInputTokens += data.summary.tokensUsed?.input || 0;
      totalOutputTokens += data.summary.tokensUsed?.output || 0;
      totalCost += data.summary.cost || 0;
    }

    if (data.story) {
      totalTime += data.story.processingTimeSec || 0;
      totalInputTokens += data.story.tokensUsed?.input || 0;
      totalOutputTokens += data.story.tokensUsed?.output || 0;
      totalCost += data.story.cost || 0;
    }

    if (data.chunks) {
      totalTime += data.chunks.describeProcessingTimeSec || 0;
      totalInputTokens += data.chunks.describeTokensUsed?.input || 0;
      totalOutputTokens += data.chunks.describeTokensUsed?.output || 0;
      totalCost += data.chunks.describeCost || 0;
    }

    return { totalTime, totalInputTokens, totalOutputTokens, totalCost };
  }, [data]);

  // ─────────────────────────────────────────────────────────────────────────
  // Return
  // ─────────────────────────────────────────────────────────────────────────
  return {
    // Status
    status,
    currentStep,
    currentStepIndex,
    pipelineSteps,
    isLoading,
    isComplete,
    isInitializing,
    parseError,

    // Data
    data,
    contentType,
    hasSlides,

    // Progress
    progressInfo,
    error,

    // Step configuration
    promptOverrides,
    modelOverrides,
    setPromptOverrides,
    setModelOverrides,
    updatePromptOverride,
    getModelForStage,

    // Actions
    runStep,
    retry,
    resetDataFromStep,

    // Helpers
    getStepStatus,
    hasDataForStep,
    calculateTotals,
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Convert File to base64 string (without data URL prefix).
 */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      const base64 = dataUrl.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Get human-readable description for a pipeline step.
 */
export function getStepDescription(step: PipelineStep): string {
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

/**
 * Format duration in seconds to MM:SS or H:MM:SS.
 */
export function formatDuration(seconds: number): string {
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
export function formatETA(estimatedSeconds: number, elapsedSeconds: number): string {
  const remaining = estimatedSeconds - elapsedSeconds;

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
 * Get step stats for display (e.g., "12:34", "4197 симв.").
 */
export function getStepStats(step: PipelineStep, data: StepData): string | null {
  switch (step) {
    case 'transcribe':
      return data.rawTranscript ? formatDuration(data.rawTranscript.durationSeconds) : null;
    case 'clean':
      return data.cleanedTranscript ? `${data.cleanedTranscript.cleanedLength.toLocaleString()} симв.` : null;
    case 'slides':
      return data.slidesExtraction ? `${data.slidesExtraction.slidesCount} слайдов` : null;
    case 'longread':
      return data.longread ? `${data.longread.totalSections} секций` : null;
    case 'summarize':
      return data.summary ? `${data.summary.keyConcepts.length} концепций` : null;
    case 'story':
      return data.story ? `${data.story.totalBlocks} блоков` : null;
    case 'chunk':
      return data.chunks ? `${data.chunks.totalChunks} чанков` : null;
    case 'save':
      return data.saveResult ? `${data.saveResult.files.length} файлов` : null;
    default:
      return null;
  }
}
