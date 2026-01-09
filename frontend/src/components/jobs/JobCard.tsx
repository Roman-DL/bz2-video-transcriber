import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import type { ProcessingJob } from '@/api/types';
import { StatusBadge } from '@/components/common/Badge';
import { ProgressBar } from '@/components/common/ProgressBar';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';

interface JobCardProps {
  job: ProcessingJob;
}

export function JobCard({ job }: JobCardProps) {
  const filename = job.video_path.split('/').pop() || job.video_path;
  const displayName = filename.replace(/\.[^/.]+$/, '');

  const isActive =
    job.status !== 'completed' &&
    job.status !== 'failed' &&
    job.status !== 'pending';

  return (
    <div className="py-3 px-4 hover:bg-gray-50 rounded-lg transition-colors">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-900 truncate">
              {displayName}
            </span>
            <StatusBadge status={job.status} />
          </div>

          {isActive && (
            <div className="mt-2">
              <ProgressBar progress={job.progress} size="sm" showLabel={false} />
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-gray-500">
                  {job.current_stage}
                </span>
                <span className="text-xs text-gray-500">
                  {Math.round(job.progress)}%
                </span>
              </div>
            </div>
          )}

          {job.status === 'completed' && job.result && (
            <div className="flex items-center gap-1 mt-1 text-xs text-green-600">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Создано {job.result.files_created.length} файлов</span>
            </div>
          )}

          {job.status === 'failed' && job.error && (
            <div className="flex items-center gap-1 mt-1 text-xs text-red-600">
              <AlertCircle className="w-3.5 h-3.5" />
              <span className="truncate">{job.error}</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-1 text-xs text-gray-400 flex-shrink-0">
          <Clock className="w-3.5 h-3.5" />
          <span>
            {formatDistanceToNow(new Date(job.created_at), {
              addSuffix: true,
              locale: ru,
            })}
          </span>
        </div>
      </div>
    </div>
  );
}
