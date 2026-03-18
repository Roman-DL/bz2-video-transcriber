import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { ArchiveResponse, PipelineResultsResponse } from '../types';

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

/**
 * Fetch pipeline results for an archived video.
 * Returns null when params are not set (modal closed).
 */
export function useArchiveResults(
  year: string | null,
  eventGroup: string | null,
  topicFolder: string | null
) {
  return useQuery({
    queryKey: ['archive-results', year, eventGroup, topicFolder],
    queryFn: async () => {
      const { data } = await apiClient.get<PipelineResultsResponse>(
        '/api/archive/results',
        {
          params: {
            year,
            event_group: eventGroup,
            topic_folder: topicFolder,
          },
        }
      );
      return data;
    },
    enabled: !!(year && eventGroup && topicFolder),
  });
}
