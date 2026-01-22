import { CheckCircle } from 'lucide-react';
import { Button } from '@/components/common/Button';
import { formatTime, formatCost, formatNumber } from '@/utils/formatUtils';

interface TotalMetrics {
  totalTime: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalCost: number;
}

interface CompletionCardProps {
  files: string[];
  totals: TotalMetrics;
  onClose: () => void;
}

/**
 * Completion card showing saved files and total metrics.
 * Displayed after successful pipeline completion.
 */
export function CompletionCard({ files, totals, onClose }: CompletionCardProps) {
  return (
    <div className="p-4 bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 flex items-center justify-center bg-emerald-500 rounded-xl">
          <CheckCircle className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Успешно сохранено</h3>
          <p className="text-xs text-gray-500">{files.length} файлов</p>
        </div>
      </div>

      {/* Files list */}
      <div className="space-y-1 mb-4 max-h-40 overflow-y-auto">
        {files.map((file, i) => (
          <div
            key={i}
            className="px-2.5 py-1.5 bg-white rounded-lg border border-emerald-100 text-xs"
          >
            <span className="font-mono text-gray-700 break-all">{file}</span>
          </div>
        ))}
      </div>

      {/* Total metrics */}
      <div className="p-2.5 bg-white rounded-lg border border-emerald-100 mb-4 space-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="text-gray-500">Общее время:</span>
          <strong className="text-gray-700">{formatTime(totals.totalTime)}</strong>
        </div>
        {(totals.totalInputTokens > 0 || totals.totalOutputTokens > 0) && (
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Токены (вх./вых.):</span>
            <strong className="text-gray-700">
              {formatNumber(totals.totalInputTokens)} / {formatNumber(totals.totalOutputTokens)}
            </strong>
          </div>
        )}
        {totals.totalCost > 0 && (
          <div className="flex justify-between text-xs">
            <span className="text-gray-500">Стоимость:</span>
            <strong className="text-violet-600">{formatCost(totals.totalCost)}</strong>
          </div>
        )}
      </div>

      {/* Close button */}
      <Button onClick={onClose} className="w-full">
        Закрыть
      </Button>
    </div>
  );
}
