import { Modal } from '@/components/common/Modal';
import { StepByStep } from './StepByStep';
import type { ProcessingMode } from '@/contexts/SettingsContext';
import type { SlideFile } from '@/api/types';

interface ProcessingModalProps {
  isOpen: boolean;
  filename: string | null;
  mode: ProcessingMode;
  slides: SlideFile[];
  onClose: () => void;
}

export function ProcessingModal({ isOpen, filename, mode, slides, onClose }: ProcessingModalProps) {
  if (!filename) return null;

  const isAutoRun = mode === 'auto';

  return (
    <Modal isOpen={isOpen} onClose={onClose} closable={!isAutoRun} size="full" noPadding>
      <StepByStep
        filename={filename}
        autoRun={isAutoRun}
        initialSlides={slides}
        onComplete={onClose}
        onCancel={onClose}
      />
    </Modal>
  );
}
