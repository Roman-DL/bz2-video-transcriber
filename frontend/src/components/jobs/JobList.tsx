import { useJobs } from '@/api/hooks/useJobs';
import { Card, CardContent, CardHeader } from '@/components/common/Card';
import { Spinner } from '@/components/common/Spinner';
import { JobCard } from './JobCard';
import { ListTodo } from 'lucide-react';

export function JobList() {
  const { data: jobs, isLoading, isError } = useJobs();

  // Sort jobs: active first, then by creation date desc
  const sortedJobs = jobs
    ? [...jobs].sort((a, b) => {
        const aActive =
          a.status !== 'completed' &&
          a.status !== 'failed' &&
          a.status !== 'pending';
        const bActive =
          b.status !== 'completed' &&
          b.status !== 'failed' &&
          b.status !== 'pending';

        if (aActive && !bActive) return -1;
        if (!aActive && bActive) return 1;

        return (
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
      })
    : [];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <ListTodo className="w-5 h-5 text-gray-500" />
          <h2 className="text-lg font-medium text-gray-900">Задачи</h2>
          {jobs && (
            <span className="text-sm text-gray-500">({jobs.length})</span>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Spinner />
          </div>
        ) : isError ? (
          <div className="text-center py-8 text-red-600">
            Ошибка загрузки задач
          </div>
        ) : sortedJobs.length > 0 ? (
          <div className="divide-y divide-gray-100">
            {sortedJobs.map((job) => (
              <JobCard key={job.job_id} job={job} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            Нет активных задач
          </div>
        )}
      </CardContent>
    </Card>
  );
}
