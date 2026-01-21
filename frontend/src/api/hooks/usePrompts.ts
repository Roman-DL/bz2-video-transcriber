import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { StagePromptsResponse } from '../types';

/**
 * Fetch prompt variants for a specific pipeline stage.
 * Returns available prompt files grouped by component (system, user, etc.)
 */
export function useStagePrompts(stage: string, enabled = true) {
  return useQuery({
    queryKey: ['prompts', stage],
    queryFn: async () => {
      const { data } = await apiClient.get<StagePromptsResponse>(`/api/prompts/${stage}`);
      return data;
    },
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
