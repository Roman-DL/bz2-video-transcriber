import { clsx } from 'clsx';
import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface CollapsibleCardProps {
  title: string;
  icon: LucideIcon;
  stats?: ReactNode;
  expanded: boolean;
  onToggle: () => void;
  children: ReactNode;
  className?: string;
}

export function CollapsibleCard({
  title,
  icon: Icon,
  stats,
  expanded,
  onToggle,
  children,
  className,
}: CollapsibleCardProps) {
  return (
    <div
      className={clsx(
        'bg-white rounded-lg border border-gray-200 shadow-sm',
        className
      )}
    >
      {/* Header - always visible */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-colors rounded-t-lg"
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          )}
          <Icon className="w-4 h-4 text-gray-500" />
          <h3 className="text-sm font-medium text-gray-900">{title}</h3>
        </div>
        {stats && (
          <div className="flex items-center gap-4 text-xs text-gray-500">
            {stats}
          </div>
        )}
      </button>

      {/* Content - collapsible */}
      <div
        className={clsx(
          'overflow-hidden transition-all duration-200 ease-in-out',
          expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="border-t border-gray-100 p-4">{children}</div>
      </div>
    </div>
  );
}
