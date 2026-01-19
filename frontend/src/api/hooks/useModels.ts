import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import type { AvailableModelsResponse, DefaultModelsResponse, ModelsConfigResponse } from '../types';

/**
 * Fetch available models from Ollama and Whisper services.
 */
export function useAvailableModels() {
  return useQuery({
    queryKey: ['models', 'available'],
    queryFn: async () => {
      const { data } = await apiClient.get<AvailableModelsResponse>('/api/models/available');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch default models from server settings.
 */
export function useDefaultModels() {
  return useQuery({
    queryKey: ['models', 'default'],
    queryFn: async () => {
      const { data } = await apiClient.get<DefaultModelsResponse>('/api/models/default');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
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
