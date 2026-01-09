import { useEffect, useState } from 'react';
import { useStartProcessing } from '@/api/hooks/useProcess';
import { useJobWebSocket } from '@/api/websocket';
import { ProgressBar } from '@/components/common/ProgressBar';
import { Button } from '@/components/common/Button';
import { PIPELINE_STEPS, STEP_LABELS, STATUS_LABELS } from '@/api/types';
import type { ProgressMessage } from '@/api/types';
import { CheckCircle, Circle, AlertCircle, Loader2 } from 'lucide-react';

interface FullPipelineProps {
  filename: string;
  onComplete: () => void;
  onCancel: () => void;
}

type StepStatus = 'pending' | 'active' | 'completed' | 'error';

export function FullPipeline({
  filename,
  onComplete,
  onCancel,
}: FullPipelineProps) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [stepStatuses, setStepStatuses] = useState<Record<string, StepStatus>>(
    () => Object.fromEntries(PIPELINE_STEPS.map((s) => [s, 'pending']))
  );
  const [finalMessage, setFinalMessage] = useState<ProgressMessage | null>(
    null
  );

  const startProcessing = useStartProcessing();

  const { progress, isConnected } = useJobWebSocket(jobId, {
    onMessage: (msg) => {
      // Update step statuses based on current status
      const statusToStep: Record<string, string> = {
        parsing: 'parse',
        transcribing: 'transcribe',
        cleaning: 'clean',
        chunking: 'chunk',
        summarizing: 'summarize',
        saving: 'save',
      };

      const currentStep = statusToStep[msg.status];
      if (currentStep) {
        setStepStatuses((prev) => {
          const updated = { ...prev };
          // Mark previous steps as completed
          let foundCurrent = false;
          for (const step of PIPELINE_STEPS) {
            if (step === currentStep) {
              updated[step] = 'active';
              foundCurrent = true;
            } else if (!foundCurrent) {
              updated[step] = 'completed';
            }
          }
          return updated;
        });
      }
    },
    onComplete: (msg) => {
      setFinalMessage(msg);
      if (msg.status === 'completed') {
        setStepStatuses(
          Object.fromEntries(PIPELINE_STEPS.map((s) => [s, 'completed']))
        );
      }
    },
  });

  // Start processing on mount
  useEffect(() => {
    startProcessing.mutate(
      { video_filename: filename },
      {
        onSuccess: (job) => {
          setJobId(job.job_id);
        },
      }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filename]);

  const isComplete = finalMessage?.status === 'completed';
  const isFailed = finalMessage?.status === 'failed';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-sm font-medium text-gray-500 mb-1">
          Обработка файла
        </h3>
        <p className="text-sm text-gray-900 truncate">{filename}</p>
      </div>

      {/* Progress */}
      {!isComplete && !isFailed && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">
              {progress ? STATUS_LABELS[progress.status] : 'Запуск...'}
            </span>
            {isConnected && (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                Подключено
              </span>
            )}
          </div>
          <ProgressBar
            progress={progress?.progress ?? 0}
            showLabel
            size="md"
          />
          {progress?.message && (
            <p className="mt-2 text-xs text-gray-500">{progress.message}</p>
          )}
        </div>
      )}

      {/* Steps */}
      <div className="space-y-2">
        {PIPELINE_STEPS.map((step) => (
          <StepItem
            key={step}
            label={STEP_LABELS[step]}
            status={stepStatuses[step]}
          />
        ))}
      </div>

      {/* Result */}
      {isComplete && finalMessage?.result && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-green-700 mb-2">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">Обработка завершена</span>
          </div>
          <ul className="text-sm text-green-600 space-y-1">
            <li>Чанков: {finalMessage.result.chunks_count}</li>
            <li>Создано файлов: {finalMessage.result.files_created.length}</li>
          </ul>
        </div>
      )}

      {isFailed && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-700 mb-2">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">Ошибка обработки</span>
          </div>
          <p className="text-sm text-red-600">{finalMessage?.error}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
        {isComplete || isFailed ? (
          <Button onClick={onComplete}>Закрыть</Button>
        ) : (
          <Button variant="secondary" onClick={onCancel}>
            Отменить
          </Button>
        )}
      </div>
    </div>
  );
}

function StepItem({ label, status }: { label: string; status: StepStatus }) {
  return (
    <div className="flex items-center gap-3">
      {status === 'pending' && (
        <Circle className="w-4 h-4 text-gray-300" />
      )}
      {status === 'active' && (
        <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
      )}
      {status === 'completed' && (
        <CheckCircle className="w-4 h-4 text-green-600" />
      )}
      {status === 'error' && (
        <AlertCircle className="w-4 h-4 text-red-600" />
      )}
      <span
        className={`text-sm ${
          status === 'active'
            ? 'text-blue-600 font-medium'
            : status === 'completed'
            ? 'text-green-600'
            : status === 'error'
            ? 'text-red-600'
            : 'text-gray-400'
        }`}
      >
        {label}
      </span>
    </div>
  );
}
