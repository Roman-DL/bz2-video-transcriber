import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { AvailableModelsResponse, DefaultModelsResponse, ModelsConfigResponse } from '../types';

/**
 * Fetch available models from Ollama and Whisper services.
 * @param enabled - Whether to enable the query (default: true)
 */
export function useAvailableModels(enabled = true) {
  return useQuery({
    queryKey: ['models', 'available'],
    queryFn: async () => {
      const { data } = await apiClient.get<AvailableModelsResponse>('/api/models/available');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled,
  });
}

/**
 * Fetch default models from server settings.
 * @param enabled - Whether to enable the query (default: true)
 */
export function useDefaultModels(enabled = true) {
  return useQuery({
    queryKey: ['models', 'default'],
    queryFn: async () => {
      const { data } = await apiClient.get<DefaultModelsResponse>('/api/models/default');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled,
  });
}

/**
 * Fetch model configurations from models.yaml.
 */
export function useModelsConfig() {
  return useQuery({
    queryKey: ['models', 'config'],
    queryFn: async () => {
      const { data } = await apiClient.get<ModelsConfigResponse>('/api/models/config');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
