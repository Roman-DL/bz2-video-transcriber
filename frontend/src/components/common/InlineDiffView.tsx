import { useRef, useState, useCallback } from 'react';
import { ArrowLeft, ArrowUpDown, Columns } from 'lucide-react';
import { formatNumber } from '@/utils/formatUtils';

interface InlineDiffViewProps {
  leftText: string;
  rightText: string;
  leftTitle: string;
  rightTitle: string;
  onClose: () => void;
}

function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(w => w.length > 0).length;
}

/**
 * Inline diff view component with synchronized scrolling.
 * Shows two text panels side by side for comparison.
 */
export function InlineDiffView({
  leftText,
  rightText,
  leftTitle,
  rightTitle,
  onClose,
}: InlineDiffViewProps) {
  const leftRef = useRef<HTMLDivElement>(null);
  const rightRef = useRef<HTMLDivElement>(null);
  const [syncScroll, setSyncScroll] = useState(true);
  const isScrolling = useRef(false);

  const handleScroll = useCallback((source: 'left' | 'right') => {
    if (!syncScroll || isScrolling.current) return;

    const sourceEl = source === 'left' ? leftRef.current : rightRef.current;
    const targetEl = source === 'left' ? rightRef.current : leftRef.current;

    if (sourceEl && targetEl) {
      isScrolling.current = true;
      const scrollHeight = sourceEl.scrollHeight - sourceEl.clientHeight;
      const scrollPercent = scrollHeight > 0 ? sourceEl.scrollTop / scrollHeight : 0;
      targetEl.scrollTop = scrollPercent * (targetEl.scrollHeight - targetEl.clientHeight);

      // Reset flag after a short delay to prevent scroll loop
      requestAnimationFrame(() => {
        isScrolling.current = false;
      });
    }
  }, [syncScroll]);

  const charDiff = rightText.length - leftText.length;
  const charDiffPercent = leftText.length > 0
    ? Math.round((charDiff / leftText.length) * 100)
    : 0;

  const leftWords = countWords(leftText);
  const rightWords = countWords(rightText);

  return (
    <div className="flex flex-col h-full bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-100 shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Назад
          </button>
          <div className="flex items-center gap-1.5 text-sm font-semibold text-gray-900">
            <Columns className="w-4 h-4 text-gray-400" />
            Сравнение текстов
          </div>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={syncScroll}
              onChange={(e) => setSyncScroll(e.target.checked)}
              className="w-3.5 h-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <ArrowUpDown className="w-3.5 h-3.5" />
            Синхронный скролл
          </label>
          <span className="text-xs text-gray-500">
            Разница:{' '}
            <strong className={charDiff < 0 ? 'text-emerald-600' : charDiff > 0 ? 'text-amber-600' : 'text-gray-600'}>
              {charDiff > 0 ? '+' : ''}{formatNumber(charDiff)} симв.
            </strong>
            {' '}
            <span className="text-gray-400">
              ({charDiffPercent > 0 ? '+' : ''}{charDiffPercent}%)
            </span>
          </span>
        </div>
      </div>

      {/* Content - two columns */}
      <div className="flex-1 flex min-h-0">
        {/* Left panel */}
        <div className="flex-1 flex flex-col border-r border-gray-200 min-h-0">
          <div className="px-3 py-2 bg-gray-100 border-b border-gray-200 shrink-0">
            <span className="text-xs font-medium text-gray-700">{leftTitle}</span>
            <span className="ml-2 text-xs text-gray-500">
              {formatNumber(leftText.length)} симв. · {formatNumber(leftWords)} слов
            </span>
          </div>
          <div
            ref={leftRef}
            onScroll={() => handleScroll('left')}
            className="flex-1 p-3 overflow-y-auto min-h-0"
          >
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {leftText}
            </p>
          </div>
        </div>

        {/* Right panel */}
        <div className="flex-1 flex flex-col min-h-0">
          <div className="px-3 py-2 bg-emerald-50 border-b border-emerald-100 shrink-0">
            <span className="text-xs font-medium text-emerald-700">{rightTitle}</span>
            <span className="ml-2 text-xs text-emerald-600">
              {formatNumber(rightText.length)} симв. · {formatNumber(rightWords)} слов
            </span>
          </div>
          <div
            ref={rightRef}
            onScroll={() => handleScroll('right')}
            className="flex-1 p-3 overflow-y-auto min-h-0"
          >
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
              {rightText}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
