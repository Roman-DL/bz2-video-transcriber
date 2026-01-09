import { useState } from 'react';
import { Modal } from '@/components/common/Modal';
import { Button } from '@/components/common/Button';
import { FullPipeline } from './FullPipeline';
import { StepByStep } from './StepByStep';
import { Zap, ListOrdered } from 'lucide-react';

interface ProcessingModalProps {
  isOpen: boolean;
  filename: string | null;
  onClose: () => void;
}

type Mode = 'select' | 'full' | 'step';

export function ProcessingModal({
  isOpen,
  filename,
  onClose,
}: ProcessingModalProps) {
  const [mode, setMode] = useState<Mode>('select');

  const handleClose = () => {
    setMode('select');
    onClose();
  };

  if (!filename) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={mode === 'select' ? 'Обработка видео' : undefined}
      size={mode === 'select' ? 'md' : 'xl'}
    >
      {mode === 'select' && (
        <ModeSelector
          filename={filename}
          onSelectFull={() => setMode('full')}
          onSelectStep={() => setMode('step')}
          onCancel={handleClose}
        />
      )}

      {mode === 'full' && (
        <FullPipeline
          filename={filename}
          onComplete={handleClose}
          onCancel={handleClose}
        />
      )}

      {mode === 'step' && (
        <StepByStep
          filename={filename}
          onComplete={handleClose}
          onCancel={handleClose}
        />
      )}
    </Modal>
  );
}

interface ModeSelectorProps {
  filename: string;
  onSelectFull: () => void;
  onSelectStep: () => void;
  onCancel: () => void;
}

function ModeSelector({
  filename,
  onSelectFull,
  onSelectStep,
  onCancel,
}: ModeSelectorProps) {
  const displayName = filename.replace(/\.[^/.]+$/, '');

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-gray-500 mb-1">Файл</h3>
        <p className="text-sm text-gray-900 truncate">{displayName}</p>
      </div>

      <div className="space-y-3">
        <button
          onClick={onSelectFull}
          className="w-full text-left p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors group"
        >
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-900">
                Полный pipeline
              </h4>
              <p className="text-xs text-gray-500 mt-1">
                Автоматически выполнит все этапы обработки. Прогресс будет
                отображаться в реальном времени.
              </p>
            </div>
          </div>
        </button>

        <button
          onClick={onSelectStep}
          className="w-full text-left p-4 border border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-colors group"
        >
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-lg bg-gray-100 text-gray-600 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
              <ListOrdered className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-900">
                Пошаговый режим
              </h4>
              <p className="text-xs text-gray-500 mt-1">
                Выполняйте этапы по одному и просматривайте результаты между
                ними. Подходит для отладки.
              </p>
            </div>
          </div>
        </button>
      </div>

      <div className="flex justify-end pt-4 border-t border-gray-200">
        <Button variant="secondary" onClick={onCancel}>
          Отмена
        </Button>
      </div>
    </div>
  );
}
