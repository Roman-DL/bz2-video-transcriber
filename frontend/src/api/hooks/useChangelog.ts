import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { ChangelogResponse } from '../types';

export function useChangelog() {
  return useQuery({
    queryKey: ['changelog'],
    queryFn: async () => {
      const { data } = await apiClient.get<ChangelogResponse>('/api/changelog');
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
