/**
 * Statistics view for pipeline processing results.
 *
 * Displays processing metrics in a table format:
 * - Time, tokens, cost per step
 * - Totals for all LLM operations
 * - Created files list (optional)
 *
 * Works with both StepData (step-by-step) and PipelineResults (archive).
 */

import {
  Clock,
  Sparkles,
  Coins,
  FileAudio,
  FileText,
  Layers,
  BookOpen,
  ListChecks,
  Heart,
  Presentation,
  Save,
  Cloud,
  Server,
  File,
} from 'lucide-react';
import { formatTime, formatCost, formatNumber } from '@/utils/formatUtils';
import type {
  RawTranscript,
  CleanedTranscript,
  SlidesExtractionResult,
  Longread,
  Summary,
  Story,
  SaveResult,
  TranscriptChunks,
  ContentType,
  TokensUsed,
} from '@/api/types';

// ═══════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════

interface StepStats {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  time?: number;
  model?: string;
  modelType?: 'local' | 'cloud';
  tokens?: TokensUsed;
  cost?: number;
}

interface StatisticsData {
  rawTranscript?: RawTranscript;
  cleanedTranscript?: CleanedTranscript;
  slidesExtraction?: SlidesExtractionResult;
  longread?: Longread;
  summary?: Summary;
  story?: Story;
  chunks?: TranscriptChunks;
  saveResult?: SaveResult;
  contentType?: ContentType;
}

interface StatisticsViewProps {
  data: StatisticsData;
  totalTime?: number;
  processedAt?: string;
  showFiles?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════════════════

function isCloudModel(model?: string): boolean {
  if (!model) return false;
  return model.startsWith('claude-');
}

function buildStepStats(data: StatisticsData): StepStats[] {
  const steps: StepStats[] = [];

  // Parse step (always fast, no metrics)
  steps.push({
    id: 'parse',
    name: 'Парсинг метаданных',
    icon: FileText,
  });

  // Transcribe step
  if (data.rawTranscript) {
    steps.push({
      id: 'transcribe',
      name: 'Транскрипция',
      icon: FileAudio,
      time: data.rawTranscript.processingTimeSec,
      model: data.rawTranscript.whisperModel,
      modelType: 'local',
    });
  }

  // Clean step
  if (data.cleanedTranscript) {
    const model = data.cleanedTranscript.modelName;
    steps.push({
      id: 'clean',
      name: 'Очистка текста',
      icon: Sparkles,
      time: data.cleanedTranscript.processingTimeSec,
      model,
      modelType: isCloudModel(model) ? 'cloud' : 'local',
      tokens: data.cleanedTranscript.tokensUsed,
      cost: data.cleanedTranscript.cost,
    });
  }

  // Slides step (conditional)
  if (data.slidesExtraction) {
    steps.push({
      id: 'slides',
      name: 'Извлечение слайдов',
      icon: Presentation,
      time: data.slidesExtraction.processingTimeSec,
      model: data.slidesExtraction.model,
      modelType: 'cloud',
      tokens: data.slidesExtraction.tokensUsed,
      cost: data.slidesExtraction.cost,
    });
  }

  // Content generation steps (depends on content type)
  const isLeadership = data.contentType === 'leadership' || data.story;

  if (isLeadership && data.story) {
    const model = data.story.modelName;
    steps.push({
      id: 'story',
      name: 'Генерация истории',
      icon: Heart,
      time: data.story.processingTimeSec,
      model,
      modelType: isCloudModel(model) ? 'cloud' : 'local',
      tokens: data.story.tokensUsed,
      cost: data.story.cost,
    });
  } else {
    if (data.longread) {
      const model = data.longread.modelName;
      steps.push({
        id: 'longread',
        name: 'Генерация лонгрида',
        icon: BookOpen,
        time: data.longread.processingTimeSec,
        model,
        modelType: isCloudModel(model) ? 'cloud' : 'local',
        tokens: data.longread.tokensUsed,
        cost: data.longread.cost,
      });
    }

    if (data.summary) {
      const model = data.summary.modelName;
      steps.push({
        id: 'summary',
        name: 'Генерация конспекта',
        icon: ListChecks,
        time: data.summary.processingTimeSec,
        model,
        modelType: isCloudModel(model) ? 'cloud' : 'local',
        tokens: data.summary.tokensUsed,
        cost: data.summary.cost,
      });
    }
  }

  // Chunk step (v0.62+: includes description generation metrics)
  if (data.chunks) {
    const model = data.chunks.describeModelName;
    steps.push({
      id: 'chunk',
      name: 'Разбиение на чанки',
      icon: Layers,
      time: data.chunks.describeProcessingTimeSec,
      model: model || undefined,
      modelType: model && isCloudModel(model) ? 'cloud' : undefined,
      tokens: data.chunks.describeTokensUsed,
      cost: data.chunks.describeCost,
    });
  }

  // Save step (v0.62+: pure file save, no LLM)
  if (data.saveResult) {
    steps.push({
      id: 'save',
      name: 'Сохранение в архив',
      icon: Save,
    });
  }

  return steps;
}

function calculateTotals(steps: StepStats[]): {
  totalTime: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalCost: number;
} {
  let totalTime = 0;
  let totalInputTokens = 0;
  let totalOutputTokens = 0;
  let totalCost = 0;

  for (const step of steps) {
    if (step.time) totalTime += step.time;
    if (step.tokens) {
      totalInputTokens += step.tokens.input || 0;
      totalOutputTokens += step.tokens.output || 0;
    }
    if (step.cost) totalCost += step.cost;
  }

  return { totalTime, totalInputTokens, totalOutputTokens, totalCost };
}

// ═══════════════════════════════════════════════════════════════════════════
// Component
// ═══════════════════════════════════════════════════════════════════════════

export function StatisticsView({
  data,
  totalTime: providedTotalTime,
  processedAt: _processedAt,
  showFiles = true,
}: StatisticsViewProps) {
  const steps = buildStepStats(data);
  const totals = calculateTotals(steps);

  // Use provided totalTime if available, otherwise calculated
  const displayTotalTime = providedTotalTime ?? totals.totalTime;

  return (
    <div className="h-full flex flex-col space-y-5 overflow-y-auto">
      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3 shrink-0">
        {/* Total Time */}
        <div className="p-3.5 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Clock className="w-3.5 h-3.5 text-blue-600" />
            <span className="text-[10px] font-semibold text-blue-600 uppercase tracking-wide">
              Общее время
            </span>
          </div>
          <div className="text-xl font-bold text-gray-900">
            {formatTime(displayTotalTime)}
          </div>
        </div>

        {/* Tokens */}
        <div className="p-3.5 bg-gradient-to-br from-violet-50 to-purple-50 rounded-xl border border-violet-100">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Sparkles className="w-3.5 h-3.5 text-violet-600" />
            <span className="text-[10px] font-semibold text-violet-600 uppercase tracking-wide">
              Токены
            </span>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-lg font-bold text-gray-900">
              {formatNumber(totals.totalInputTokens)}
            </span>
            <span className="text-[10px] text-gray-500">вх.</span>
            <span className="text-gray-300">/</span>
            <span className="text-lg font-bold text-gray-900">
              {formatNumber(totals.totalOutputTokens)}
            </span>
            <span className="text-[10px] text-gray-500">вых.</span>
          </div>
        </div>

        {/* Cost */}
        <div className="p-3.5 bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl border border-emerald-100">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Coins className="w-3.5 h-3.5 text-emerald-600" />
            <span className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wide">
              Стоимость
            </span>
          </div>
          <div className="text-xl font-bold text-gray-900">
            {formatCost(totals.totalCost)}
          </div>
        </div>
      </div>

      {/* Steps Table */}
      <div className="shrink-0">
        <h4 className="text-xs font-semibold text-gray-700 mb-2">
          Детализация по этапам
        </h4>
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-3 py-2 font-medium text-gray-500 text-[10px] uppercase tracking-wide">
                  Этап
                </th>
                <th className="text-left px-3 py-2 font-medium text-gray-500 text-[10px] uppercase tracking-wide">
                  Модель
                </th>
                <th className="text-right px-3 py-2 font-medium text-gray-500 text-[10px] uppercase tracking-wide">
                  Время
                </th>
                <th className="text-right px-3 py-2 font-medium text-gray-500 text-[10px] uppercase tracking-wide">
                  Токены
                </th>
                <th className="text-right px-3 py-2 font-medium text-gray-500 text-[10px] uppercase tracking-wide">
                  Стоимость
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {steps.map((step) => {
                const Icon = step.icon;
                const hasLLM = step.model && step.modelType === 'cloud';
                return (
                  <tr
                    key={step.id}
                    className="hover:bg-gray-50/50 transition-colors"
                  >
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-5 h-5 rounded-md flex items-center justify-center ${
                            hasLLM ? 'bg-violet-100' : 'bg-gray-100'
                          }`}
                        >
                          <Icon
                            className={`w-3 h-3 ${
                              hasLLM ? 'text-violet-600' : 'text-gray-500'
                            }`}
                          />
                        </div>
                        <span className="text-gray-900 font-medium text-xs">
                          {step.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      {step.model ? (
                        <div className="flex items-center gap-1">
                          {step.modelType === 'cloud' ? (
                            <Cloud className="w-3 h-3 text-violet-500" />
                          ) : (
                            <Server className="w-3 h-3 text-emerald-500" />
                          )}
                          <span className="font-mono text-[10px] text-gray-600">
                            {step.model}
                          </span>
                        </div>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {step.time !== undefined ? (
                        <span className="text-emerald-600 font-medium text-xs">
                          {formatTime(step.time)}
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-[10px]">
                      {step.tokens ? (
                        <span className="text-gray-600">
                          {formatNumber(step.tokens.input)} /{' '}
                          {formatNumber(step.tokens.output)}
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {step.cost ? (
                        <span className="text-violet-600 font-semibold text-xs">
                          {formatCost(step.cost)}
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="bg-gray-100 border-t-2 border-gray-200">
                <td className="px-3 py-2.5 font-semibold text-gray-900 text-xs">
                  Итого
                </td>
                <td className="px-3 py-2.5"></td>
                <td className="px-3 py-2.5 text-right font-semibold text-emerald-600 text-xs">
                  {formatTime(displayTotalTime)}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-[10px] font-semibold text-gray-900">
                  {formatNumber(totals.totalInputTokens)} /{' '}
                  {formatNumber(totals.totalOutputTokens)}
                </td>
                <td className="px-3 py-2.5 text-right font-semibold text-violet-600 text-xs">
                  {formatCost(totals.totalCost)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Files Created */}
      {showFiles && data.saveResult?.files && data.saveResult.files.length > 0 && (
        <div className="shrink-0">
          <h4 className="text-xs font-semibold text-gray-700 mb-2">
            Созданные файлы ({data.saveResult.files.length})
          </h4>
          <div className="grid grid-cols-2 gap-1.5">
            {data.saveResult.files.map((filename, idx) => (
              <div
                key={idx}
                className="flex items-center gap-1.5 px-2.5 py-1.5 bg-gray-50 rounded border border-gray-100"
              >
                <File className="w-3.5 h-3.5 text-gray-400" />
                <span className="font-mono text-[10px] text-gray-700 truncate">
                  {filename}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
