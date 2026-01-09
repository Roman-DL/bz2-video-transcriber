import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';

export function useInbox() {
  return useQuery({
    queryKey: ['inbox'],
    queryFn: async () => {
      const { data } = await apiClient.get<string[]>('/api/inbox');
      return data;
    },
    refetchInterval: 30000,
  });
}
