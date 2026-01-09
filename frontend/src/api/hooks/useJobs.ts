import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { ProcessingJob } from '../types';

export function useJobs() {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const { data } = await apiClient.get<ProcessingJob[]>('/api/jobs');
      return data;
    },
    refetchInterval: 5000,
  });
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ['jobs', jobId],
    queryFn: async () => {
      const { data } = await apiClient.get<ProcessingJob>(`/api/jobs/${jobId}`);
      return data;
    },
    enabled: !!jobId,
    refetchInterval: 2000,
  });
}
