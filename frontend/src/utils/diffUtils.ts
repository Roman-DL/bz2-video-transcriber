import { diffWords } from 'diff';

export interface DiffToken {
  text: string;
  type: 'equal' | 'added' | 'removed';
}

export interface WordDiffResult {
  leftTokens: DiffToken[];
  rightTokens: DiffToken[];
}

interface Replacement {
  from: string;
  to: string;
  count: number;
}

export interface DiffReport {
  replacements: Replacement[];
  deletions: { text: string; count: number }[];
  additions: { text: string; count: number }[];
  totalChanges: number;
}

export interface ReportMeta {
  modelName?: string;
}

/**
 * Compute word-level diff between two texts.
 * Returns separate token arrays for left (original) and right (cleaned) panels.
 */
export function computeWordDiff(left: string, right: string): WordDiffResult {
  const changes = diffWords(left, right);

  const leftTokens: DiffToken[] = [];
  const rightTokens: DiffToken[] = [];

  for (const change of changes) {
    if (change.added) {
      rightTokens.push({ text: change.value, type: 'added' });
    } else if (change.removed) {
      leftTokens.push({ text: change.value, type: 'removed' });
    } else {
      leftTokens.push({ text: change.value, type: 'equal' });
      rightTokens.push({ text: change.value, type: 'equal' });
    }
  }

  return { leftTokens, rightTokens };
}

/**
 * Aggregate diff changes into structured report data.
 * Adjacent removed+added pairs become replacements; lone ones become deletions/additions.
 */
export function aggregateDiffChanges(left: string, right: string): DiffReport {
  const changes = diffWords(left, right);

  const replacementsMap = new Map<string, Replacement>();
  const deletionsMap = new Map<string, number>();
  const additionsMap = new Map<string, number>();

  for (let i = 0; i < changes.length; i++) {
    const change = changes[i];

    if (change.removed) {
      const next = changes[i + 1];
      const removedText = change.value.trim();

      if (next?.added) {
        // Adjacent removed+added = replacement
        const addedText = next.value.trim();
        if (removedText && addedText) {
          const key = `${removedText}→${addedText}`;
          const existing = replacementsMap.get(key);
          if (existing) {
            existing.count++;
          } else {
            replacementsMap.set(key, { from: removedText, to: addedText, count: 1 });
          }
        }
        i++; // skip the added part
      } else if (removedText) {
        // Lone removal = deletion
        deletionsMap.set(removedText, (deletionsMap.get(removedText) || 0) + 1);
      }
    } else if (change.added) {
      const addedText = change.value.trim();
      if (addedText) {
        additionsMap.set(addedText, (additionsMap.get(addedText) || 0) + 1);
      }
    }
  }

  const replacements = [...replacementsMap.values()].sort((a, b) => b.count - a.count);
  const deletions = [...deletionsMap.entries()]
    .map(([text, count]) => ({ text, count }))
    .sort((a, b) => b.count - a.count);
  const additions = [...additionsMap.entries()]
    .map(([text, count]) => ({ text, count }))
    .sort((a, b) => b.count - a.count);

  const totalChanges = replacements.reduce((s, r) => s + r.count, 0)
    + deletions.reduce((s, d) => s + d.count, 0)
    + additions.reduce((s, a) => s + a.count, 0);

  return { replacements, deletions, additions, totalChanges };
}

function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(w => w.length > 0).length;
}

/**
 * Generate a markdown report for clipboard.
 */
export function generateDiffReport(left: string, right: string, meta?: ReportMeta): string {
  const report = aggregateDiffChanges(left, right);
  const leftWords = countWords(left);
  const rightWords = countWords(right);
  const wordDiff = rightWords - leftWords;
  const wordDiffPercent = leftWords > 0
    ? ((wordDiff / leftWords) * 100).toFixed(1)
    : '0';

  const lines: string[] = ['## Отчёт об очистке'];

  const metaParts: string[] = [];
  if (meta?.modelName) metaParts.push(`Модель: ${meta.modelName}`);
  metaParts.push(`Слов: ${leftWords} → ${rightWords} (${wordDiff > 0 ? '+' : ''}${wordDiffPercent}%)`);
  metaParts.push(`Замен: ${report.totalChanges}`);
  lines.push(metaParts.join(' | '));

  if (report.replacements.length > 0) {
    lines.push('', '### Замены (сгруппированные)');
    for (const r of report.replacements) {
      lines.push(`${r.from} → ${r.to} (×${r.count})`);
    }
  }

  if (report.deletions.length > 0) {
    lines.push('', '### Удаления');
    lines.push(report.deletions.map(d => `${d.text} (×${d.count})`).join(' | '));
  }

  if (report.additions.length > 0) {
    lines.push('', '### Вставки');
    lines.push(report.additions.map(a => `${a.text} (×${a.count})`).join(' | '));
  }

  return lines.join('\n');
}
