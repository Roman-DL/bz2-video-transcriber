import { Modal } from '@/components/common/Modal';
import { StepByStep } from './StepByStep';

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
  if (!filename) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <StepByStep
        filename={filename}
        onComplete={onClose}
        onCancel={onClose}
      />
    </Modal>
  );
}
