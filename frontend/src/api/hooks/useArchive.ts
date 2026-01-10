import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { ArchiveResponse } from '../types';

export function useArchive() {
  return useQuery({
    queryKey: ['archive'],
    queryFn: async () => {
      const { data } = await apiClient.get<ArchiveResponse>('/api/archive');
      return data;
    },
    refetchInterval: 30000,
  });
}
