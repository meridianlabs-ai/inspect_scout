import { useEffect, useState } from "react";

/**
 * Subscribes to SSE config version stream.
 * Returns current version string, auto-reconnects on disconnect.
 */
export const useConfigVersionStream = (): string | undefined => {
  const [version, setVersion] = useState<string | undefined>(undefined);

  useEffect(() => {
    const connect = () => {
      const es = new EventSource("/api/v2/config-version/stream");
      es.onmessage = (e) => setVersion(e.data);
      es.onerror = () => {
        es.close();
        setTimeout(connect, 5000);
      };
      return es;
    };
    const es = connect();
    return () => es.close();
  }, []);

  return version;
};
