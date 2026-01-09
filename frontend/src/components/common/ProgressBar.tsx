import { clsx } from 'clsx';

interface ProgressBarProps {
  progress: number;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function ProgressBar({
  progress,
  showLabel = true,
  size = 'md',
  className,
}: ProgressBarProps) {
  const clampedProgress = Math.min(100, Math.max(0, progress));

  return (
    <div className={clsx('w-full', className)}>
      <div
        className={clsx('w-full bg-gray-200 rounded-full overflow-hidden', {
          'h-1.5': size === 'sm',
          'h-2.5': size === 'md',
          'h-4': size === 'lg',
        })}
      >
        <div
          className="bg-blue-600 h-full rounded-full transition-all duration-300 ease-out"
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
      {showLabel && (
        <div className="mt-1 text-sm text-gray-600 text-right">
          {Math.round(clampedProgress)}%
        </div>
      )}
    </div>
  );
}
