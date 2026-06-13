import { useEffect, useRef, useCallback, useState } from "react";

export interface SSEEvent {
  id: string;
  type: string;
  payload: unknown;
}

export function useSSE(url: string) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(url);

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setEvents((prev) => [...prev.slice(-99), data]);
      } catch {
        // ignore parse errors
      }
    };

    esRef.current = es;

    return () => {
      es.close();
      esRef.current = null;
      setConnected(false);
    };
  }, [url]);

  const clear = useCallback(() => setEvents([]), []);

  return { events, connected, clear };
}
