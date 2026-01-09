import { useEffect, useRef, useState, useCallback } from 'react';
import { getWsUrl } from './client';
import type { ProgressMessage } from './types';

interface UseJobWebSocketOptions {
  onMessage?: (message: ProgressMessage) => void;
  onComplete?: (message: ProgressMessage) => void;
  onError?: (error: Event) => void;
}

export function useJobWebSocket(
  jobId: string | null,
  options: UseJobWebSocketOptions = {}
) {
  const [progress, setProgress] = useState<ProgressMessage | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (!jobId) {
      disconnect();
      return;
    }

    const ws = new WebSocket(getWsUrl(`/ws/${jobId}`));
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const message: ProgressMessage = JSON.parse(event.data);

      // Skip heartbeat
      if (message.type === 'heartbeat') return;

      setProgress(message);
      optionsRef.current.onMessage?.(message);

      if (message.status === 'completed' || message.status === 'failed') {
        optionsRef.current.onComplete?.(message);
      }
    };

    ws.onerror = (error) => {
      optionsRef.current.onError?.(error);
    };

    ws.onclose = () => {
      setIsConnected(false);
      wsRef.current = null;
    };

    return () => {
      ws.close();
    };
  }, [jobId, disconnect]);

  return { progress, isConnected, disconnect };
}
