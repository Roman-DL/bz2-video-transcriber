import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { ProcessingJob, ProcessRequest } from '../types';

export function useStartProcessing() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ProcessRequest) => {
      const { data } = await apiClient.post<ProcessingJob>('/api/process', request);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}
