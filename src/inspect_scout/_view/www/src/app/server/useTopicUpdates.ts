import { useEffect, useState } from "react";

/** Topic versions: maps topic name to timestamp. */
export type TopicVersions = Record<string, string>;

/**
 * Subscribes to SSE topic updates stream.
 * Returns current topic versions dict, auto-reconnects on disconnect.
 */
export const useTopicUpdates = (): TopicVersions | undefined => {
  const [versions, setVersions] = useState<TopicVersions | undefined>(
    undefined
  );

  useEffect(() => {
    const connect = () => {
      const es = new EventSource("/api/v2/topics/stream");
      es.onmessage = (e) => setVersions(JSON.parse(e.data) as TopicVersions);
      es.onerror = () => {
        es.close();
        setTimeout(connect, 5000);
      };
      return es;
    };
    const es = connect();
    return () => es.close();
  }, []);

  return versions;
};
