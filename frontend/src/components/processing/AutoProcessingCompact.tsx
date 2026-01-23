import { usePipelineProcessor, formatETA } from '@/hooks/usePipelineProcessor';
import type { PipelineStep, SlideFile, VideoMetadata } from '@/api/types';
import { STEP_LABELS } from '@/api/types';
import {
  CheckCircle,
  AlertCircle,
  Loader2,
  FolderOpen,
  RefreshCw,
  X,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════

interface AutoProcessingCompactProps {
  filename: string;
  initialSlides?: SlideFile[];
  onCancel: () => void;
  onOpenArchive: (metadata: VideoMetadata) => void;
  onComplete?: () => void;
}

type CompactStepStatus = 'pending' | 'running' | 'completed' | 'error';

// ═══════════════════════════════════════════════════════════════════════════
// StepItem Component
// ═══════════════════════════════════════════════════════════════════════════

interface StepItemProps {
  label: string;
  status: CompactStepStatus;
  isLast: boolean;
}

function StepItem({ label, status, isLast }: StepItemProps) {
  const getIcon = () => {
    switch (status) {
      case 'completed':
        return (
          <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
            <CheckCircle className="w-3 h-3 text-white" strokeWidth={3} />
          </div>
        );
      case 'running':
        return (
          <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
            <Loader2 className="w-3 h-3 text-white animate-spin" />
          </div>
        );
      case 'error':
        return (
          <div className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center flex-shrink-0">
            <X className="w-3 h-3 text-white" strokeWidth={3} />
          </div>
        );
      default:
        return (
          <div className="w-5 h-5 rounded-full border-2 border-stone-300 flex-shrink-0" />
        );
    }
  };

  return (
    <div className="flex items-center gap-3 py-1.5">
      {/* Icon with connector line */}
      <div className="relative flex flex-col items-center">
        {getIcon()}
        {!isLast && (
          <div className={`absolute top-5 w-0.5 h-4 ${
            status === 'completed' ? 'bg-emerald-500' : 'bg-stone-200'
          }`} />
        )}
      </div>

      {/* Label */}
      <span className={`text-[13px] ${
        status === 'completed' ? 'text-stone-700' :
        status === 'running' ? 'text-blue-600 font-medium' :
        status === 'error' ? 'text-red-600' :
        'text-stone-400'
      }`}>
        {label}
      </span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ProgressHeader Component
// ═══════════════════════════════════════════════════════════════════════════

interface ProgressHeaderProps {
  status: 'running' | 'completed' | 'error';
  currentStep: number;
  totalSteps: number;
  stepLabel: string;
  progress: number | null;
  timeRemaining: string | null;
  errorMessage?: string | null;
}

function ProgressHeader({
  status,
  currentStep,
  totalSteps,
  stepLabel,
  progress,
  timeRemaining,
  errorMessage,
}: ProgressHeaderProps) {
  if (status === 'completed') {
    return (
      <div className="flex items-center gap-3 py-3">
        <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center flex-shrink-0">
          <CheckCircle className="w-6 h-6 text-emerald-600" />
        </div>
        <div>
          <div className="text-sm font-medium text-emerald-600">УСПЕШНО ЗАВЕРШЕНО</div>
          <div className="text-xs text-stone-500">Все этапы выполнены</div>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="flex items-center gap-3 py-3">
        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
          <AlertCircle className="w-6 h-6 text-red-600" />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-medium text-red-600">ОШИБКА</div>
          <div className="text-xs text-stone-500 truncate" title={errorMessage || stepLabel}>
            {errorMessage || stepLabel}
          </div>
        </div>
      </div>
    );
  }

  // Running state
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
          <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-blue-600 uppercase tracking-wide">Выполняется</div>
          <div className="text-sm text-stone-900 truncate">{stepLabel} ({currentStep}/{totalSteps})</div>
        </div>
        {timeRemaining && (
          <div className="text-xs text-stone-400 flex-shrink-0">{timeRemaining}</div>
        )}
      </div>

      {/* Progress bar */}
      {progress !== null && (
        <div className="flex items-center gap-3">
          <div className="flex-1 h-1.5 bg-stone-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${Math.round(progress)}%` }}
            />
          </div>
          <span className="text-xs text-stone-500 w-10 text-right">{Math.round(progress)}%</span>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════════════════════

export function AutoProcessingCompact({
  filename,
  initialSlides = [],
  onCancel,
  onOpenArchive,
  onComplete,
}: AutoProcessingCompactProps) {
  const processor = usePipelineProcessor({
    filename,
    initialSlides,
    autoRun: true,
  });

  const {
    status,
    currentStep,
    currentStepIndex,
    pipelineSteps,
    progressInfo,
    error,
    data,
    isInitializing,
    parseError,
  } = processor;

  // Map processor status to compact status
  const compactStatus: 'running' | 'completed' | 'error' =
    status === 'completed' ? 'completed' :
    status === 'error' ? 'error' : 'running';

  // Get step status for list
  const getCompactStepStatus = (step: PipelineStep): CompactStepStatus => {
    const stepIndex = pipelineSteps.indexOf(step);
    if (error && stepIndex === currentStepIndex) return 'error';
    if (stepIndex < currentStepIndex) return 'completed';
    if (stepIndex === currentStepIndex && status === 'running') return 'running';
    if (stepIndex === currentStepIndex && status === 'completed') return 'completed';
    return 'pending';
  };

  // Format time remaining
  const timeRemaining = progressInfo.estimatedSeconds !== null && progressInfo.elapsedSeconds !== null
    ? formatETA(progressInfo.estimatedSeconds, progressInfo.elapsedSeconds)
    : null;

  // Handle open archive
  const handleOpenArchive = () => {
    if (data.metadata) {
      onOpenArchive(data.metadata);
    }
    onComplete?.();
  };

  // Handle retry
  const handleRetry = () => {
    processor.retry();
  };

  // Handle close on error
  const handleClose = () => {
    onCancel();
  };

  // Loading state during auto-parse
  if (isInitializing) {
    return (
      <div className="w-full bg-white overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-stone-50 border-b border-stone-200">
          <span className="text-xs font-medium text-stone-500 uppercase tracking-wide">
            Автоматическая обработка
          </span>
        </div>

        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-3" />
            <p className="text-sm text-stone-600">Анализ метаданных...</p>
          </div>
        </div>
      </div>
    );
  }

  // Parse error state
  if (parseError) {
    return (
      <div className="w-full bg-white overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-stone-50 border-b border-stone-200">
          <span className="text-xs font-medium text-stone-500 uppercase tracking-wide">
            Автоматическая обработка
          </span>
        </div>

        {/* Error */}
        <div className="px-4 py-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <div className="text-sm font-medium text-red-600">Ошибка парсинга</div>
              <div className="text-xs text-stone-500">{parseError}</div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-4 py-3 bg-stone-50 border-t border-stone-200">
          <button
            onClick={handleClose}
            className="w-full px-4 py-2 text-sm font-medium text-stone-700 bg-white border border-stone-300 rounded-lg hover:bg-stone-50 transition-colors"
          >
            Закрыть
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-stone-50 border-b border-stone-200">
        <span className="text-xs font-medium text-stone-500 uppercase tracking-wide">
          Автоматическая обработка
        </span>
        {compactStatus === 'running' && (
          <button
            onClick={onCancel}
            className="px-3 py-1 text-xs font-medium text-stone-500 hover:text-stone-700 hover:bg-stone-200 rounded-lg transition-colors"
          >
            Отменить
          </button>
        )}
      </div>

      {/* File name */}
      <div className="px-4 py-2 border-b border-stone-100">
        <p className="text-sm font-medium text-stone-900 truncate" title={filename}>
          {filename}
        </p>
      </div>

      {/* Progress section */}
      <div className="px-4 py-3 border-b border-stone-100">
        <ProgressHeader
          status={compactStatus}
          currentStep={currentStepIndex + 1}
          totalSteps={pipelineSteps.length}
          stepLabel={STEP_LABELS[currentStep]}
          progress={progressInfo.progress}
          timeRemaining={timeRemaining}
          errorMessage={error}
        />
      </div>

      {/* Steps list */}
      <div className="px-4 py-2">
        {pipelineSteps.map((step, index) => (
          <StepItem
            key={step}
            label={STEP_LABELS[step]}
            status={getCompactStepStatus(step)}
            isLast={index === pipelineSteps.length - 1}
          />
        ))}
      </div>

      {/* Footer - completed */}
      {compactStatus === 'completed' && (
        <div className="px-4 py-3 bg-stone-50 border-t border-stone-200 flex gap-3">
          <button
            onClick={handleOpenArchive}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors"
          >
            <FolderOpen className="w-4 h-4" />
            Открыть в архиве
          </button>
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium text-stone-700 bg-white border border-stone-300 rounded-lg hover:bg-stone-50 transition-colors"
          >
            Закрыть
          </button>
        </div>
      )}

      {/* Footer - error */}
      {compactStatus === 'error' && (
        <div className="px-4 py-3 bg-stone-50 border-t border-stone-200 flex gap-3">
          <button
            onClick={handleRetry}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Повторить
          </button>
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium text-stone-700 bg-white border border-stone-300 rounded-lg hover:bg-stone-50 transition-colors"
          >
            Закрыть
          </button>
        </div>
      )}
    </div>
  );
}
