import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../client';
import type {
  VideoMetadata,
  RawTranscript,
  CleanedTranscript,
  TranscriptChunks,
  VideoSummary,
  StepParseRequest,
  StepCleanRequest,
  StepChunkRequest,
  StepSummarizeRequest,
  StepSaveRequest,
} from '../types';

export function useStepParse() {
  return useMutation({
    mutationFn: async (request: StepParseRequest) => {
      const { data } = await apiClient.post<VideoMetadata>('/api/step/parse', request);
      return data;
    },
  });
}

export function useStepTranscribe() {
  return useMutation({
    mutationFn: async (request: StepParseRequest) => {
      const { data } = await apiClient.post<RawTranscript>('/api/step/transcribe', request);
      return data;
    },
  });
}

export function useStepClean() {
  return useMutation({
    mutationFn: async (request: StepCleanRequest) => {
      const { data } = await apiClient.post<CleanedTranscript>('/api/step/clean', request);
      return data;
    },
  });
}

export function useStepChunk() {
  return useMutation({
    mutationFn: async (request: StepChunkRequest) => {
      const { data } = await apiClient.post<TranscriptChunks>('/api/step/chunk', request);
      return data;
    },
  });
}

export function useStepSummarize() {
  return useMutation({
    mutationFn: async (request: StepSummarizeRequest) => {
      const { data } = await apiClient.post<VideoSummary>('/api/step/summarize', request);
      return data;
    },
  });
}

export function useStepSave() {
  return useMutation({
    mutationFn: async (request: StepSaveRequest) => {
      const { data } = await apiClient.post<string[]>('/api/step/save', request);
      return data;
    },
  });
}
