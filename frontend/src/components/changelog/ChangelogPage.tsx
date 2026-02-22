import { useChangelog } from '@/api/hooks/useChangelog';
import { Modal } from '@/components/common/Modal';
import { Spinner } from '@/components/common/Spinner';
import { Button } from '@/components/common/Button';
import type { ChangelogEntry } from '@/api/types';

const MONTHS = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
];

function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-');
  const monthIdx = parseInt(month, 10) - 1;
  return `${parseInt(day, 10)} ${MONTHS[monthIdx]} ${year}`;
}

const BADGE_CONFIG: Record<ChangelogEntry['type'], { label: string; className: string }> = {
  feat: { label: 'Новое', className: 'bg-green-100 text-green-700' },
  fix: { label: 'Исправление', className: 'bg-red-100 text-red-700' },
  refactor: { label: 'Улучшение', className: 'bg-gray-100 text-gray-600' },
  docs: { label: 'Документация', className: 'bg-gray-100 text-gray-600' },
  perf: { label: 'Производительность', className: 'bg-gray-100 text-gray-600' },
};

interface ChangelogModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChangelogModal({ isOpen, onClose }: ChangelogModalProps) {
  const { data, isLoading, isError, refetch } = useChangelog();

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Журнал изменений" size="xl">
      <div className="max-h-[70vh] overflow-y-auto space-y-4">
        {isLoading && (
          <div className="flex justify-center py-8">
            <Spinner size="lg" />
          </div>
        )}

        {isError && (
          <div className="text-center py-8 space-y-3">
            <p className="text-gray-500">Не удалось загрузить историю изменений</p>
            <Button variant="secondary" size="sm" onClick={() => refetch()}>
              Повторить
            </Button>
          </div>
        )}

        {data && data.versions.length === 0 && (
          <p className="text-center py-8 text-gray-400">
            История изменений пока недоступна
          </p>
        )}

        {data && data.versions.length > 0 && data.versions.map((ver) => (
          <div key={ver.version} className="border border-gray-100 rounded-lg p-4">
            <div className="flex items-baseline justify-between mb-3">
              <span className="text-base font-semibold text-gray-900">v{ver.version}</span>
              <span className="text-sm text-gray-400">{formatDate(ver.date)}</span>
            </div>
            <ul className="space-y-2">
              {ver.changes.map((entry, i) => {
                const badge = BADGE_CONFIG[entry.type];
                return (
                  <li key={i} className="flex items-start gap-2">
                    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded shrink-0 ${badge.className}`}>
                      {badge.label}
                    </span>
                    <span className="text-sm text-gray-700">{entry.description}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </Modal>
  );
}
