import { CheckCircle } from 'lucide-react';
import { Button } from '@/components/common/Button';

interface CompletionCardProps {
  files: string[];
  onClose: () => void;
}

/**
 * Compact completion card showing success status.
 * Displayed after successful pipeline completion.
 *
 * Files list moved to Statistics tab (v0.59+).
 */
export function CompletionCard({ files, onClose }: CompletionCardProps) {
  return (
    <div className="p-4 bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 flex items-center justify-center bg-emerald-500 rounded-xl">
          <CheckCircle className="w-5 h-5 text-white" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Успешно сохранено</h3>
          <p className="text-xs text-gray-500">{files.length} файлов</p>
        </div>
      </div>

      {/* Close button */}
      <Button onClick={onClose} className="w-full">
        Закрыть
      </Button>
    </div>
  );
}
