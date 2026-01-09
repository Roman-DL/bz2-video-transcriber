import { clsx } from 'clsx';
import type { ProcessingStatus } from '@/api/types';

interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  children: React.ReactNode;
}

export function Badge({ variant = 'default', children }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
        {
          'bg-gray-100 text-gray-700': variant === 'default',
          'bg-green-100 text-green-700': variant === 'success',
          'bg-yellow-100 text-yellow-700': variant === 'warning',
          'bg-red-100 text-red-700': variant === 'error',
          'bg-blue-100 text-blue-700': variant === 'info',
        }
      )}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  const variants: Record<ProcessingStatus, BadgeProps['variant']> = {
    pending: 'default',
    parsing: 'info',
    transcribing: 'info',
    cleaning: 'info',
    chunking: 'info',
    summarizing: 'info',
    saving: 'info',
    completed: 'success',
    failed: 'error',
  };

  const labels: Record<ProcessingStatus, string> = {
    pending: 'Ожидание',
    parsing: 'Парсинг',
    transcribing: 'Транскрипция',
    cleaning: 'Очистка',
    chunking: 'Разбиение',
    summarizing: 'Суммаризация',
    saving: 'Сохранение',
    completed: 'Завершено',
    failed: 'Ошибка',
  };

  return <Badge variant={variants[status]}>{labels[status]}</Badge>;
}
