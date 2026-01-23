import { useState, useMemo, useCallback } from 'react';
import { useStagePrompts } from '@/api/hooks/usePrompts';
import { useAvailableModels, useDefaultModels } from '@/api/hooks/useModels';
import type {
  PipelineStep,
  PromptOverrides,
  StagePromptsResponse,
  SlideFile,
} from '@/api/types';
import { STEP_LABELS } from '@/api/types';
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
import { StatisticsView } from '@/components/results/StatisticsView';
import { CompletionCard } from '@/components/processing/CompletionCard';
import { ComponentPromptSelector } from '@/components/settings/ComponentPromptSelector';
import { ModelSelector } from '@/components/settings/ModelSelector';
import { buildLLMOptions } from '@/utils/modelUtils';
import { formatTime } from '@/utils/formatUtils';
import {
  usePipelineProcessor,
  formatETA,
  getStepDescription,
  type StageWithPrompts,
  STAGES_WITH_PROMPTS,
} from '@/hooks/usePipelineProcessor';
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
  BarChart3,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════

interface StepByStepProps {
  filename: string;
  onComplete: () => void;
  onCancel: () => void;
  initialSlides?: SlideFile[];
}

type ResultTab = 'metadata' | 'rawTranscript' | 'cleanedTranscript' | 'slides' | 'chunks' | 'longread' | 'summary' | 'story' | 'statistics';

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
  statistics: BarChart3,
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
  statistics: 'Статистика',
};

// Map pipeline step to result tab
function getTabForStep(step: PipelineStep): ResultTab | null {
  switch (step) {
    case 'parse': return 'metadata';
    case 'transcribe': return 'rawTranscript';
    case 'clean': return 'cleanedTranscript';
    case 'slides': return 'slides';
    case 'longread': return 'longread';
    case 'summarize': return 'summary';
    case 'story': return 'story';
    case 'chunk': return 'chunks';
    case 'save': return 'statistics'; // Show statistics after save
    default: return null;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Component
// ═══════════════════════════════════════════════════════════════════════════

export function StepByStep({ filename, onComplete, onCancel, initialSlides = [] }: StepByStepProps) {
  // ─────────────────────────────────────────────────────────────────────────
  // Local UI State
  // ─────────────────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<ResultTab | null>(null);
  const [expandedSettings, setExpandedSettings] = useState<PipelineStep | null>(null);
  const [showCleanedDiff, setShowCleanedDiff] = useState(false);
  const [showLongreadDiff, setShowLongreadDiff] = useState(false);

  // Wrapper that resets diff mode when switching tabs
  const switchTab = useCallback((tab: ResultTab | null) => {
    setActiveTab(tab);
    setShowCleanedDiff(false);
    setShowLongreadDiff(false);
  }, []);

  // Auto-switch tab when step completes
  const handleStepComplete = useCallback((step: PipelineStep) => {
    const tabForStep = getTabForStep(step);
    if (tabForStep) {
      switchTab(tabForStep);
    }
  }, [switchTab]);

  // Use shared pipeline processor hook (step-by-step mode)
  const processor = usePipelineProcessor({
    filename,
    initialSlides,
    autoRun: false,
    onStepComplete: handleStepComplete,
  });

  const {
    currentStep,
    currentStepIndex,
    pipelineSteps,
    isLoading,
    isComplete,
    isInitializing,
    parseError,
    data,
    contentType,
    hasSlides,
    progressInfo,
    error,
    promptOverrides,
    modelOverrides,
    setModelOverrides,
    updatePromptOverride,
    getModelForStage,
    runStep,
    resetDataFromStep,
    getStepStatus,
  } = processor;

  // ─────────────────────────────────────────────────────────────────────────
  // Model & Prompt Hooks (step-by-step specific)
  // ─────────────────────────────────────────────────────────────────────────
  const { data: availableModels } = useAvailableModels(true);
  const { data: defaultModels } = useDefaultModels(true);

  const llmOptions = useMemo(() => {
    return buildLLMOptions(availableModels?.ollamaModels, availableModels?.claudeModels);
  }, [availableModels]);

  const { data: cleanPrompts } = useStagePrompts('cleaning', true);
  const { data: longreadPrompts } = useStagePrompts('longread', true);
  const { data: summaryPrompts } = useStagePrompts('summary', true);
  const { data: storyPrompts } = useStagePrompts('story', true);

  // ─────────────────────────────────────────────────────────────────────────
  // Helpers
  // ─────────────────────────────────────────────────────────────────────────
  const getPromptsForStep = (step: PipelineStep): StagePromptsResponse | undefined => {
    switch (step) {
      case 'clean': return cleanPrompts;
      case 'longread': return longreadPrompts;
      case 'summarize': return summaryPrompts;
      case 'story': return storyPrompts;
      default: return undefined;
    }
  };

  const hasSelectablePrompts = (prompts: StagePromptsResponse | undefined): boolean => {
    if (!prompts) return false;
    return prompts.components.some(c => c.variants.length > 1);
  };

  const isLLMStep = (step: PipelineStep): step is StageWithPrompts => {
    return STAGES_WITH_PROMPTS.includes(step as StageWithPrompts);
  };

  const getAvailableTabs = (): ResultTab[] => {
    const tabs: ResultTab[] = [];
    if (data.metadata) tabs.push('metadata');
    if (data.rawTranscript) tabs.push('rawTranscript');
    if (data.cleanedTranscript) tabs.push('cleanedTranscript');
    if (data.slidesExtraction) tabs.push('slides');
    if (data.longread) tabs.push('longread');
    if (data.summary) tabs.push('summary');
    if (data.story) tabs.push('story');
    if (data.chunks) tabs.push('chunks');
    // Show statistics tab after save
    if (data.savedFiles) tabs.push('statistics');
    return tabs;
  };

  // Rerun a step with current overrides
  const rerunStep = async (step: PipelineStep) => {
    setExpandedSettings(null);
    resetDataFromStep(step);
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Loading State
  // ─────────────────────────────────────────────────────────────────────────
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

  // ─────────────────────────────────────────────────────────────────────────
  // Main Layout
  // ─────────────────────────────────────────────────────────────────────────
  const availableTabs = getAvailableTabs();
  const { progress, estimatedSeconds, elapsedSeconds } = progressInfo;

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

          {/* Success card */}
          {isComplete && data.savedFiles && (
            <CompletionCard
              files={data.savedFiles}
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
                          if (tabForStep) switchTab(tabForStep);
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
                        ) : status === 'error' ? (
                          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
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
                            status === 'completed' ? 'text-gray-500' :
                            status === 'error' ? 'text-red-500' : 'text-gray-300'
                          }`} />
                          <span className={`text-sm font-medium ${
                            status === 'pending' || status === 'next' ? 'text-gray-400' :
                            status === 'error' ? 'text-red-600' : 'text-gray-900'
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
                                  {(modelOverrides[step] || defaultModels?.[settingsKey] || getModelForStage(step) || '').includes('claude') ? 'cloud' : 'local'}
                                </span>
                                <ModelSelector
                                  value={modelOverrides[step]}
                                  defaultValue={defaultModels?.[settingsKey] || getModelForStage(step) || ''}
                                  options={llmOptions}
                                  onChange={(value) => setModelOverrides(prev => ({ ...prev, [step]: value }))}
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
                      onClick={() => switchTab(tab)}
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
                      {data.metadata.durationSeconds && (
                        <div className="flex items-center gap-1 text-xs text-gray-500">
                          <Clock className="w-3 h-3" />
                          {formatDuration(data.metadata.durationSeconds)}
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
                      {data.rawTranscript.processingTimeSec !== undefined && (
                        <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                          {formatTime(data.rawTranscript.processingTimeSec)}
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
                        {data.cleanedTranscript.processingTimeSec !== undefined && (
                          <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                            {formatTime(data.cleanedTranscript.processingTimeSec)}
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

                {activeTab === 'slides' && data.slidesExtraction && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                      <h3 className="text-sm font-semibold text-gray-900">Извлечённые данные со слайдов</h3>
                      {data.slidesExtraction.processingTimeSec !== undefined && (
                        <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                          {formatTime(data.slidesExtraction.processingTimeSec)}
                        </span>
                      )}
                    </div>
                    <div className="p-4 flex-1 overflow-hidden min-h-0">
                      <SlidesResultView slidesExtraction={data.slidesExtraction} />
                    </div>
                  </div>
                )}

                {activeTab === 'longread' && data.longread && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    {!showLongreadDiff && (
                      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                        <h3 className="text-sm font-semibold text-gray-900">Лонгрид</h3>
                        {data.longread.processingTimeSec !== undefined && (
                          <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                            {formatTime(data.longread.processingTimeSec)}
                          </span>
                        )}
                      </div>
                    )}
                    <div className={showLongreadDiff ? 'flex-1 min-h-0' : 'p-4 flex-1 overflow-y-auto'}>
                      <LongreadView
                        longread={data.longread}
                        cleanedText={data.cleanedTranscript?.text}
                        cleanedChars={data.cleanedTranscript?.cleanedLength}
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
                      {data.summary.processingTimeSec !== undefined && (
                        <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded">
                          {formatTime(data.summary.processingTimeSec)}
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
                        <span>{data.story.totalBlocks} блоков</span>
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

                {activeTab === 'statistics' && data.savedFiles && (
                  <div className="bg-white border border-gray-200 rounded-lg overflow-hidden h-full flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
                      <h3 className="text-sm font-semibold text-gray-900">Статистика обработки</h3>
                    </div>
                    <div className="p-4 flex-1 overflow-hidden min-h-0">
                      <StatisticsView
                        data={{
                          rawTranscript: data.rawTranscript,
                          cleanedTranscript: data.cleanedTranscript,
                          slidesExtraction: data.slidesExtraction,
                          longread: data.longread,
                          summary: data.summary,
                          story: data.story,
                          chunks: data.chunks,
                          savedFiles: data.savedFiles,
                          contentType: data.metadata?.contentType,
                        }}
                      />
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

// ═══════════════════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════════════════

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h > 0
    ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    : `${m}:${s.toString().padStart(2, '0')}`;
}
