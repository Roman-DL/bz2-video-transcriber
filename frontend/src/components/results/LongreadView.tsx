import { useState, useRef, useEffect, useCallback } from 'react';
import { Columns, Pencil, Eye, Save, RotateCcw } from 'lucide-react';
import type { Longread, LongreadSection } from '@/api/types';
import { ResultFooter } from '@/components/common/ResultFooter';
import { InlineDiffView } from '@/components/common/InlineDiffView';
import { formatNumber } from '@/utils/formatUtils';

interface LongreadViewProps {
  longread: Longread;
  cleanedText?: string;
  cleanedChars?: number;
  showDiff?: boolean;
  onToggleDiff?: () => void;
  editable?: boolean;
  onLongreadUpdate?: (updated: Longread) => void;
}

export function formatLongreadAsMarkdown(longread: Longread): string {
  const lines: string[] = [];

  // Introduction
  if (longread.introduction) {
    lines.push(longread.introduction);
    lines.push('');
  }

  // Sections
  for (const section of longread.sections) {
    lines.push(`## ${section.title}`);
    lines.push('');
    lines.push(section.content);
    lines.push('');
  }

  // Conclusion
  if (longread.conclusion) {
    lines.push('---');
    lines.push('');
    lines.push(longread.conclusion);
  }

  return lines.join('\n');
}

function countWords(text: string): number {
  return text.split(/\s+/).filter(w => w.length > 0).length;
}

function parseMarkdownToLongread(markdown: string, original: Longread): Longread {
  // 1. Split by "---" → before = main content, after = conclusion
  const hrParts = markdown.split(/\n---\n/);
  const mainContent = hrParts[0];
  const conclusion = hrParts.length > 1 ? hrParts.slice(1).join('\n---\n').trim() : '';

  // 2. Split main content by "## " headings
  const sectionParts = mainContent.split(/^## /m);

  // First part (before any ## heading) = introduction
  const introduction = sectionParts[0].trim();

  // Remaining parts = sections
  const sections: LongreadSection[] = sectionParts.slice(1).map((part, idx) => {
    const lines = part.split('\n');
    const title = lines[0].trim();
    const content = lines.slice(1).join('\n').trim();
    return {
      index: idx,
      title,
      content,
      sourceChunks: original.sections[idx]?.sourceChunks ?? [],
      wordCount: countWords(content),
    };
  });

  // 3. Recalculate metrics
  const totalWordCount = countWords(introduction) + sections.reduce((sum, s) => sum + s.wordCount, 0) + countWords(conclusion);
  const fullText = [introduction, ...sections.map(s => s.content), conclusion].join(' ');

  return {
    ...original,
    introduction,
    sections,
    conclusion,
    totalSections: sections.length,
    totalWordCount,
    chars: fullText.length,
  };
}

export function LongreadView({
  longread,
  cleanedText,
  cleanedChars,
  showDiff = false,
  onToggleDiff,
  editable = false,
  onLongreadUpdate,
}: LongreadViewProps) {
  const markdownText = formatLongreadAsMarkdown(longread);

  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(markdownText);
  const [isModified, setIsModified] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Reset edit state when longread changes (e.g. rerun)
  useEffect(() => {
    const newMarkdown = formatLongreadAsMarkdown(longread);
    setEditedText(newMarkdown);
    setIsEditing(false);
    setIsModified(false);
  }, [longread]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current && isEditing) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [editedText, isEditing]);

  const handleSave = useCallback(() => {
    const updated = parseMarkdownToLongread(editedText, longread);
    onLongreadUpdate?.(updated);
    setIsEditing(false);
    setIsModified(true);
  }, [editedText, longread, onLongreadUpdate]);

  const handleReset = useCallback(() => {
    setEditedText(markdownText);
    setIsModified(false);
  }, [markdownText]);

  const handleToggleEdit = useCallback(() => {
    if (isEditing) {
      // Cancel editing — revert to current longread state
      setEditedText(formatLongreadAsMarkdown(longread));
    }
    setIsEditing(!isEditing);
  }, [isEditing, longread]);

  // Calculate reduction percentage if cleanedChars available
  const reductionPercent = cleanedChars && cleanedChars > 0
    ? Math.round((1 - longread.chars / cleanedChars) * 100)
    : null;

  // Show diff view if enabled
  if (showDiff && cleanedText && onToggleDiff) {
    return (
      <InlineDiffView
        leftText={cleanedText}
        rightText={markdownText}
        leftTitle="Очистка"
        rightTitle="Лонгрид"
        onClose={onToggleDiff}
      />
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with metrics */}
      <div className="text-xs text-gray-500 mb-2 shrink-0 flex flex-wrap items-center gap-x-3 gap-y-1">
        <span>
          {formatNumber(longread.chars)} симв.
        </span>
        <span>
          {formatNumber(longread.totalWordCount)} слов
        </span>
        {reductionPercent !== null && (
          <span className={reductionPercent > 0 ? 'text-emerald-600' : 'text-amber-600'}>
            {reductionPercent > 0 ? '-' : '+'}{Math.abs(reductionPercent)}%
          </span>
        )}
        {isModified && (
          <span className="text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded font-medium">
            изменено
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="mb-2 shrink-0 flex items-center gap-2 flex-wrap">
        {cleanedText && onToggleDiff && !isEditing && (
          <button
            onClick={onToggleDiff}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <Columns className="w-3.5 h-3.5" />
            Сравнить с очисткой
          </button>
        )}

        {editable && (
          <button
            onClick={handleToggleEdit}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
              isEditing
                ? 'text-gray-700 bg-gray-50 border-gray-200 hover:bg-gray-100'
                : 'text-amber-700 bg-amber-50 border-amber-200 hover:bg-amber-100'
            }`}
          >
            {isEditing ? (
              <>
                <Eye className="w-3.5 h-3.5" />
                Просмотр
              </>
            ) : (
              <>
                <Pencil className="w-3.5 h-3.5" />
                Редактировать
              </>
            )}
          </button>
        )}

        {isEditing && (
          <button
            onClick={handleSave}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            Сохранить
          </button>
        )}

        {isModified && !isEditing && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Сбросить
          </button>
        )}
      </div>

      {/* Longread content — view or edit */}
      {isEditing ? (
        <textarea
          ref={textareaRef}
          value={editedText}
          onChange={e => setEditedText(e.target.value)}
          className="flex-1 w-full text-sm text-gray-700 leading-relaxed font-mono p-3 border border-amber-200 rounded-lg bg-amber-50/30 focus:outline-none focus:ring-2 focus:ring-amber-300 focus:border-amber-300 resize-none min-h-0 overflow-y-auto"
          spellCheck={false}
        />
      ) : (
        <div className="flex-1 overflow-y-auto text-sm text-gray-700 whitespace-pre-wrap leading-relaxed min-h-0">
          {markdownText}
        </div>
      )}

      {/* Footer with LLM metrics */}
      <ResultFooter
        tokensUsed={longread.tokensUsed}
        cost={longread.cost}
        model={longread.modelName}
      />
    </div>
  );
}
