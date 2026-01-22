import { useRef, useState, useCallback, useEffect } from 'react';
import { X, Upload, Image, FileText, Trash2 } from 'lucide-react';
import type { SlideFile } from '@/api/types';

interface SlidesModalProps {
  isOpen: boolean;
  onClose: () => void;
  slides: SlideFile[];
  onSlidesChange: (slides: SlideFile[]) => void;
  fileName: string;
}

// Limits
const MAX_FILES = 50;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const MAX_TOTAL_SIZE = 100 * 1024 * 1024; // 100 MB
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];

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
 * Get file type from MIME type.
 */
function getFileType(mimeType: string): 'image' | 'pdf' {
  return mimeType === 'application/pdf' ? 'pdf' : 'image';
}

/**
 * Generate unique ID for slide.
 */
function generateId(): string {
  return `slide-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Create preview data URL for image file.
 */
async function createPreview(file: File): Promise<string | undefined> {
  if (!file.type.startsWith('image/')) {
    return undefined;
  }

  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      resolve(e.target?.result as string);
    };
    reader.onerror = () => {
      resolve(undefined);
    };
    reader.readAsDataURL(file);
  });
}

/**
 * Modal for uploading and managing presentation slides.
 * Supports drag & drop, file picker, preview grid, and deletion.
 */
export function SlidesModal({
  isOpen,
  onClose,
  slides,
  onSlidesChange,
  fileName,
}: SlidesModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalSize = slides.reduce((acc, s) => acc + s.size, 0);

  // Reset error when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setError(null);
    }
  }, [isOpen]);

  // Block body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  const validateFiles = useCallback(
    (files: FileList | File[]): { valid: File[]; errors: string[] } => {
      const valid: File[] = [];
      const errors: string[] = [];
      const fileArray = Array.from(files);

      // Check total count limit
      if (slides.length + fileArray.length > MAX_FILES) {
        errors.push(`Максимум ${MAX_FILES} файлов. Сейчас: ${slides.length}, добавляется: ${fileArray.length}`);
        return { valid, errors };
      }

      let newTotalSize = totalSize;

      for (const file of fileArray) {
        // Check type
        if (!ACCEPTED_TYPES.includes(file.type)) {
          errors.push(`${file.name}: неподдерживаемый формат`);
          continue;
        }

        // Check single file size
        if (file.size > MAX_FILE_SIZE) {
          errors.push(`${file.name}: размер превышает 10 MB`);
          continue;
        }

        // Check total size
        if (newTotalSize + file.size > MAX_TOTAL_SIZE) {
          errors.push(`${file.name}: превышен общий лимит 100 MB`);
          continue;
        }

        valid.push(file);
        newTotalSize += file.size;
      }

      return { valid, errors };
    },
    [slides.length, totalSize]
  );

  const handleAddFiles = useCallback(
    async (files: FileList | File[]) => {
      const { valid, errors } = validateFiles(files);

      if (errors.length > 0) {
        setError(errors.join('. '));
      } else {
        setError(null);
      }

      if (valid.length === 0) return;

      // Create slide entries with previews
      const newSlides: SlideFile[] = await Promise.all(
        valid.map(async (file) => ({
          id: generateId(),
          name: file.name,
          size: file.size,
          type: getFileType(file.type),
          file,
          preview: await createPreview(file),
        }))
      );

      onSlidesChange([...slides, ...newSlides]);
    },
    [slides, onSlidesChange, validateFiles]
  );

  const handleRemove = useCallback(
    (id: string) => {
      onSlidesChange(slides.filter((s) => s.id !== id));
      setError(null);
    },
    [slides, onSlidesChange]
  );

  const handleClearAll = useCallback(() => {
    onSlidesChange([]);
    setError(null);
  }, [onSlidesChange]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      handleAddFiles(e.dataTransfer.files);
    },
    [handleAddFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        handleAddFiles(e.target.files);
      }
      // Reset input to allow selecting same file again
      e.target.value = '';
    },
    [handleAddFiles]
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 shrink-0">
          <div className="min-w-0 flex-1 pr-4">
            <h2 className="text-lg font-semibold text-gray-900">Слайды презентации</h2>
            <p className="text-sm text-gray-500 truncate" title={fileName}>
              {fileName}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drop Zone */}
        <div className="px-5 pt-4 shrink-0">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
              dragOver
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp,application/pdf"
              onChange={handleFileInputChange}
              className="hidden"
            />
            <div className="flex flex-col items-center gap-2">
              <div className={`p-3 rounded-full ${dragOver ? 'bg-blue-100' : 'bg-gray-100'}`}>
                <Upload className={`w-6 h-6 ${dragOver ? 'text-blue-600' : 'text-gray-400'}`} />
              </div>
              <p className="text-sm font-medium text-gray-700">Перетащите файлы сюда</p>
              <p className="text-xs text-gray-500">
                или <span className="text-blue-600 underline">выберите</span> на компьютере
              </p>
              <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
                <Image className="w-4 h-4" />
                <span>JPG, PNG, WebP</span>
                <span className="text-gray-300">•</span>
                <FileText className="w-4 h-4" />
                <span>PDF</span>
              </div>
            </div>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="px-5 pt-3 shrink-0">
            <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
              {error}
            </div>
          </div>
        )}

        {/* Slides Grid */}
        <div className="flex-1 overflow-y-auto px-5 py-4 min-h-0">
          {slides.length > 0 ? (
            <>
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-700">
                  Загружено: {slides.length} файлов ({formatFileSize(totalSize)})
                </span>
                <button
                  onClick={handleClearAll}
                  className="text-xs text-red-500 hover:text-red-600 transition-colors"
                >
                  Удалить все
                </button>
              </div>
              <div className="grid grid-cols-4 gap-3">
                {slides.map((slide, idx) => (
                  <div
                    key={slide.id}
                    className="group relative aspect-[4/3] rounded-lg overflow-hidden border border-gray-200 bg-gray-100"
                  >
                    {/* Preview or placeholder */}
                    {slide.preview ? (
                      <img
                        src={slide.preview}
                        alt={slide.name}
                        className="absolute inset-0 w-full h-full object-cover"
                      />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                        <FileText className="w-8 h-8 text-gray-400" />
                      </div>
                    )}

                    {/* Hover overlay with delete button */}
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <button
                        onClick={() => handleRemove(slide.id)}
                        className="p-1.5 bg-white rounded-lg text-gray-600 hover:text-red-600 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    {/* Index badge */}
                    <div className="absolute top-1 left-1 px-1.5 py-0.5 bg-black/60 rounded text-xs text-white font-medium">
                      {idx + 1}
                    </div>

                    {/* Filename at bottom */}
                    <div className="absolute bottom-0 left-0 right-0 px-2 py-1 bg-gradient-to-t from-black/60 to-transparent">
                      <p className="text-xs text-white truncate">{slide.name}</p>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <Image className="w-12 h-12 mb-3 opacity-40" />
              <p className="text-sm">Слайды не загружены</p>
              <p className="text-xs mt-1">Добавьте фото или PDF презентации</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-4 bg-gray-50 border-t border-gray-200 shrink-0">
          <p className="text-xs text-gray-500">
            {slides.length > 0
              ? 'Слайды будут обработаны на отдельном шаге перед генерацией лонгрида'
              : 'Слайды можно не добавлять — шаг будет пропущен'}
          </p>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-lg hover:bg-blue-600 transition-colors"
          >
            Готово
          </button>
        </div>
      </div>
    </div>
  );
}
