import { Paperclip, Plus, ChevronRight } from 'lucide-react';
import type { SlideFile } from '@/api/types';

interface SlidesAttachmentProps {
  slides: SlideFile[];
  onOpenModal: () => void;
}

/**
 * Format bytes to human readable file size.
 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return (bytes / 1024).toFixed(0) + ' KB';
  }
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Compact component to display slides attachment state in InboxCard.
 * Shows "Add slides" button when empty, or slides count + size when has slides.
 */
export function SlidesAttachment({ slides, onOpenModal }: SlidesAttachmentProps) {
  const hasSlides = slides.length > 0;
  const totalSize = slides.reduce((acc, s) => acc + s.size, 0);

  if (hasSlides) {
    return (
      <button
        onClick={onOpenModal}
        className="flex items-center gap-2 px-2 py-1.5 text-xs rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors w-full"
      >
        <Paperclip className="w-3.5 h-3.5 flex-shrink-0" />
        <span className="font-medium">{slides.length} слайдов</span>
        <span className="text-emerald-500">({formatFileSize(totalSize)})</span>
        <ChevronRight className="w-3.5 h-3.5 ml-auto text-emerald-400" />
      </button>
    );
  }

  return (
    <button
      onClick={onOpenModal}
      className="flex items-center gap-1.5 px-2 py-1.5 text-xs text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors w-full"
    >
      <Plus className="w-3.5 h-3.5" />
      <span>Добавить слайды</span>
    </button>
  );
}
