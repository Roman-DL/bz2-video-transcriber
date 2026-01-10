import { useState, useEffect } from 'react';
import { Modal } from '@/components/common/Modal';
import { StepByStep } from './StepByStep';
import { Button } from '@/components/common/Button';
import { Play, Footprints } from 'lucide-react';

type ProcessingMode = 'select' | 'step-by-step' | 'auto-run';

interface ProcessingModalProps {
  isOpen: boolean;
  filename: string | null;
  onClose: () => void;
}

export function ProcessingModal({
  isOpen,
  filename,
  onClose,
}: ProcessingModalProps) {
  const [mode, setMode] = useState<ProcessingMode>('select');

  // Reset mode when modal closes
  useEffect(() => {
    if (!isOpen) {
      setMode('select');
    }
  }, [isOpen]);

  const handleClose = () => {
    setMode('select');
    onClose();
  };

  if (!filename) return null;

  // Mode selection screen
  if (mode === 'select') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} size="md">
        <ModeSelector
          filename={filename}
          onSelectMode={setMode}
          onCancel={handleClose}
        />
      </Modal>
    );
  }

  // Processing screen (step-by-step or auto-run)
  const isAutoRun = mode === 'auto-run';

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      closable={!isAutoRun}
      size="xl"
    >
      <StepByStep
        filename={filename}
        autoRun={isAutoRun}
        onComplete={handleClose}
        onCancel={handleClose}
      />
    </Modal>
  );
}

interface ModeSelectorProps {
  filename: string;
  onSelectMode: (mode: ProcessingMode) => void;
  onCancel: () => void;
}

function ModeSelector({ filename, onSelectMode, onCancel }: ModeSelectorProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-medium text-gray-900">Обработка видео</h3>
        <p className="text-sm text-gray-500 mt-1 truncate">{filename}</p>
      </div>

      {/* Mode options */}
      <div className="space-y-3">
        <button
          onClick={() => onSelectMode('step-by-step')}
          className="w-full p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-colors text-left group"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 bg-gray-100 rounded-lg group-hover:bg-blue-100">
              <Footprints className="w-5 h-5 text-gray-600 group-hover:text-blue-600" />
            </div>
            <div>
              <h4 className="font-medium text-gray-900">Пошагово</h4>
              <p className="text-sm text-gray-500 mt-1">
                Контроль каждого этапа. Просмотр результатов и повтор шагов.
              </p>
            </div>
          </div>
        </button>

        <button
          onClick={() => onSelectMode('auto-run')}
          className="w-full p-4 border border-gray-200 rounded-lg hover:border-green-300 hover:bg-green-50 transition-colors text-left group"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 bg-gray-100 rounded-lg group-hover:bg-green-100">
              <Play className="w-5 h-5 text-gray-600 group-hover:text-green-600" />
            </div>
            <div>
              <h4 className="font-medium text-gray-900">Автоматически</h4>
              <p className="text-sm text-gray-500 mt-1">
                Все этапы без остановок. Быстрая обработка от начала до конца.
              </p>
            </div>
          </div>
        </button>
      </div>

      {/* Cancel button */}
      <div className="flex justify-end pt-4 border-t border-gray-200">
        <Button variant="secondary" onClick={onCancel}>
          Отмена
        </Button>
      </div>
    </div>
  );
}
