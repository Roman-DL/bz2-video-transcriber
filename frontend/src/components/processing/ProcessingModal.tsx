import { Modal } from '@/components/common/Modal';
import { StepByStep } from './StepByStep';
import type { ProcessingMode } from '@/contexts/SettingsContext';

interface ProcessingModalProps {
  isOpen: boolean;
  filename: string | null;
  mode: ProcessingMode;
  onClose: () => void;
}

export function ProcessingModal({ isOpen, filename, mode, onClose }: ProcessingModalProps) {
  if (!filename) return null;

  const isAutoRun = mode === 'auto';

  return (
    <Modal isOpen={isOpen} onClose={onClose} closable={!isAutoRun} size="full" noPadding>
      <StepByStep filename={filename} autoRun={isAutoRun} onComplete={onClose} onCancel={onClose} />
    </Modal>
  );
}
