import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../client';
import { fetchWithProgress } from '../sse';
import type {
  VideoMetadata,
  CleanedTranscript,
  TranscriptChunks,
  Longread,
  Summary,
  Story,
  TranscribeResult,
  SlidesExtractionResult,
  StepParseRequest,
  StepCleanRequest,
  StepChunkRequest,
  StepLongreadRequest,
  StepSummarizeRequest,
  StepStoryRequest,
  StepSlidesRequest,
  StepSaveRequest,
} from '../types';

/**
 * Hook state for step with progress tracking.
 */
interface UseStepWithProgressState<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  progress: number | null;
  message: string | null;
  estimatedSeconds: number | null;
  elapsedSeconds: number | null;
}

/**
 * Hook return type for step with progress.
 */
interface UseStepWithProgress<T, R> {
  mutate: (request: R) => Promise<T>;
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  isPending: boolean;
  progress: number | null;
  message: string | null;
  estimatedSeconds: number | null;
  elapsedSeconds: number | null;
  reset: () => void;
}

/**
 * Create a step hook with SSE progress tracking.
 */
function createStepWithProgress<T, R>(endpoint: string) {
  return function useStepWithProgress(): UseStepWithProgress<T, R> {
    const [state, setState] = useState<UseStepWithProgressState<T>>({
      data: null,
      error: null,
      isLoading: false,
      progress: null,
      message: null,
      estimatedSeconds: null,
      elapsedSeconds: null,
    });

    const mutate = useCallback(async (request: R): Promise<T> => {
      setState({
        data: null,
        error: null,
        isLoading: true,
        progress: 0,
        message: 'Starting...',
        estimatedSeconds: null,
        elapsedSeconds: null,
      });

      try {
        const result = await fetchWithProgress<T>(
          endpoint,
          request as object,
          (progress, message, estimatedSeconds, elapsedSeconds) => {
            setState((prev) => ({
              ...prev,
              progress,
              message,
              estimatedSeconds,
              elapsedSeconds,
            }));
          }
        );

        setState({
          data: result,
          error: null,
          isLoading: false,
          progress: 100,
          message: 'Complete',
          estimatedSeconds: null,
          elapsedSeconds: null,
        });

        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setState({
          data: null,
          error,
          isLoading: false,
          progress: null,
          message: null,
          estimatedSeconds: null,
          elapsedSeconds: null,
        });
        throw error;
      }
    }, []);

    const reset = useCallback(() => {
      setState({
        data: null,
        error: null,
        isLoading: false,
        progress: null,
        message: null,
        estimatedSeconds: null,
        elapsedSeconds: null,
      });
    }, []);

    return {
      mutate,
      data: state.data,
      error: state.error,
      isLoading: state.isLoading,
      isPending: state.isLoading, // Alias for react-query compatibility
      progress: state.progress,
      message: state.message,
      estimatedSeconds: state.estimatedSeconds,
      elapsedSeconds: state.elapsedSeconds,
      reset,
    };
  };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Step Hooks (Parse and Save are fast - no SSE needed)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Parse video filename to extract metadata.
 * Fast operation - uses regular HTTP.
 */
export function useStepParse() {
  return useMutation({
    mutationFn: async (request: StepParseRequest) => {
      const { data } = await apiClient.post<VideoMetadata>('/api/step/parse', request);
      return data;
    },
  });
}

/**
 * Transcribe video using Whisper API.
 * Extracts audio from video first, then sends to Whisper.
 * Long-running operation - uses SSE with progress.
 * Returns TranscribeResult with raw_transcript and audio_path.
 */
export const useStepTranscribe = createStepWithProgress<TranscribeResult, StepParseRequest>(
  '/api/step/transcribe'
);

/**
 * Clean raw transcript using glossary and LLM.
 * Uses SSE with progress.
 */
export const useStepClean = createStepWithProgress<CleanedTranscript, StepCleanRequest>(
  '/api/step/clean'
);

/**
 * Chunk markdown by H2 headers (deterministic).
 * Fast operation - uses regular HTTP.
 */
export function useStepChunk() {
  return useMutation({
    mutationFn: async (request: StepChunkRequest) => {
      const { data } = await apiClient.post<TranscriptChunks>('/api/step/chunk', request);
      return data;
    },
  });
}

/**
 * Generate longread document from cleaned transcript.
 * Uses SSE with progress.
 */
export const useStepLongread = createStepWithProgress<Longread, StepLongreadRequest>(
  '/api/step/longread'
);

/**
 * Generate summary (конспект) from cleaned transcript.
 * Uses SSE with progress.
 */
export const useStepSummarize = createStepWithProgress<Summary, StepSummarizeRequest>(
  '/api/step/summarize'
);

/**
 * Generate leadership story (8 blocks) from cleaned transcript.
 * Uses SSE with progress.
 * For content_type=LEADERSHIP only.
 */
export const useStepStory = createStepWithProgress<Story, StepStoryRequest>(
  '/api/step/story'
);

/**
 * Extract text from slides using vision API.
 * Uses SSE with progress.
 * Only appears when slides are attached.
 */
export const useStepSlides = createStepWithProgress<SlidesExtractionResult, StepSlidesRequest>(
  '/api/step/slides'
);

/**
 * Save all processing results to archive.
 * Fast operation - uses regular HTTP.
 */
export function useStepSave() {
  return useMutation({
    mutationFn: async (request: StepSaveRequest) => {
      const { data } = await apiClient.post<string[]>('/api/step/save', request);
      return data;
    },
  });
}
