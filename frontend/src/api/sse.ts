/**
 * SSE (Server-Sent Events) client for step-by-step processing with progress.
 *
 * Provides fetchWithProgress function that calls SSE endpoints
 * and reports progress via callback.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * SSE event types from backend.
 */
export interface SSEProgressEvent {
  type: 'progress';
  status: string;
  progress: number;
  message: string;
  estimated_seconds: number;
  elapsed_seconds: number;
}

export interface SSEResultEvent<T> {
  type: 'result';
  data: T;
}

export interface SSEErrorEvent {
  type: 'error';
  error: string;
}

export type SSEEvent<T> = SSEProgressEvent | SSEResultEvent<T> | SSEErrorEvent;

/**
 * Progress callback signature.
 * @param progress - Current progress percentage (0-100)
 * @param message - Human-readable progress message
 * @param estimatedSeconds - Total estimated time for this operation
 * @param elapsedSeconds - Time elapsed since operation started
 */
export type ProgressCallback = (
  progress: number,
  message: string,
  estimatedSeconds: number,
  elapsedSeconds: number
) => void;

/**
 * Fetch with SSE progress tracking.
 *
 * Makes POST request to SSE endpoint and reports progress via callback.
 * Returns the final result when complete.
 *
 * @param endpoint - API endpoint path (e.g., '/api/step/transcribe')
 * @param body - Request body object
 * @param onProgress - Callback for progress updates
 * @returns Promise with the result data
 * @throws Error if request fails or stream contains error event
 *
 * @example
 * ```ts
 * const result = await fetchWithProgress<RawTranscript>(
 *   '/api/step/transcribe',
 *   { video_filename: 'test.mp4' },
 *   (progress, message) => {
 *     setProgress(progress);
 *     setMessage(message);
 *   }
 * );
 * ```
 */
export async function fetchWithProgress<T>(
  endpoint: string,
  body: object,
  onProgress: ProgressCallback
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('No response body');
  }

  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events (separated by double newlines)
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const eventStr of events) {
        if (!eventStr.startsWith('data: ')) {
          continue;
        }

        const jsonStr = eventStr.slice(6); // Remove 'data: ' prefix
        const event = JSON.parse(jsonStr) as SSEEvent<T>;

        switch (event.type) {
          case 'progress':
            onProgress(
              event.progress,
              event.message,
              event.estimated_seconds,
              event.elapsed_seconds
            );
            break;

          case 'result':
            // Send 100% progress before returning (elapsed = estimated at completion)
            onProgress(100, 'Complete', 0, 0);
            return event.data;

          case 'error':
            throw new Error(event.error);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  throw new Error('Stream ended without result');
}
