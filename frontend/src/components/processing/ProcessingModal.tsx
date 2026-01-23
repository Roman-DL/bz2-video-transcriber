import { Modal } from '@/components/common/Modal';
import { StepByStep } from './StepByStep';
import { AutoProcessingCompact } from './AutoProcessingCompact';
import type { ProcessingMode } from '@/contexts/SettingsContext';
import type { SlideFile, VideoMetadata } from '@/api/types';

interface ProcessingModalProps {
  isOpen: boolean;
  filename: string | null;
  mode: ProcessingMode;
  slides: SlideFile[];
  onClose: () => void;
  onOpenArchive?: (metadata: VideoMetadata) => void;
}

export function ProcessingModal({
  isOpen,
  filename,
  mode,
  slides,
  onClose,
  onOpenArchive,
}: ProcessingModalProps) {
  if (!filename) return null;

  const isAutoRun = mode === 'auto';

  // Handle open archive - close modal and trigger callback
  const handleOpenArchive = (metadata: VideoMetadata) => {
    onClose();
    onOpenArchive?.(metadata);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      closable={!isAutoRun}
      size={isAutoRun ? 'md' : 'full'}
      noPadding
    >
      {isAutoRun ? (
        <AutoProcessingCompact
          filename={filename}
          initialSlides={slides}
          onCancel={onClose}
          onOpenArchive={handleOpenArchive}
          onComplete={onClose}
        />
      ) : (
        <StepByStep
          filename={filename}
          initialSlides={slides}
          onComplete={onClose}
          onCancel={onClose}
        />
      )}
    </Modal>
  );
}
