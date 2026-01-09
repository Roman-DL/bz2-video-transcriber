import { clsx } from 'clsx';
import type { ReactNode } from 'react';

interface CardProps {
  className?: string;
  children: ReactNode;
}

export function Card({ className, children }: CardProps) {
  return (
    <div
      className={clsx(
        'bg-white rounded-lg border border-gray-200 shadow-sm',
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children }: CardProps) {
  return (
    <div className={clsx('px-4 py-3 border-b border-gray-100', className)}>
      {children}
    </div>
  );
}

export function CardContent({ className, children }: CardProps) {
  return <div className={clsx('p-4', className)}>{children}</div>;
}
