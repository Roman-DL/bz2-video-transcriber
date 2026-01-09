import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { ServicesHealth } from '../types';

export function useServices() {
  return useQuery({
    queryKey: ['services'],
    queryFn: async () => {
      const { data } = await apiClient.get<ServicesHealth>('/health/services');
      return data;
    },
    refetchInterval: 60000,
    staleTime: 30000,
  });
}
