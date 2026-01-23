import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, useRef } from "react";

/** Topic versions: maps topic name to timestamp. */
type TopicVersions = Record<string, string>;

/**
 * Monitors topic updates via SSE and invalidates dependent queries on change.
 *
 * For each topic whose timestamp changes, invalidates all queries containing
 * that topic name in their query key.
 *
 * Call once at app root level.
 *
 * @returns true when first SSE message received (ready), false otherwise
 */
export const useTopicInvalidation = (): boolean => {
  const queryClient = useQueryClient();
  const versions = useTopicUpdates();
  const prevVersionsRef = useRef<TopicVersions>({});

  useEffect(() => {
    if (versions === undefined) return;

    const changedTopics = Object.entries(versions).filter(
      ([topic, timestamp]) => prevVersionsRef.current[topic] !== timestamp
    );
    for (const [topic] of changedTopics) {
      void queryClient.invalidateQueries({
        predicate: (query) => query.queryKey.includes(topic),
      });
    }

    prevVersionsRef.current = versions;
  }, [versions, queryClient]);

  return versions !== undefined;
};

/**
 * Subscribes to SSE topic updates stream.
 * Returns current topic versions dict, auto-reconnects on disconnect.
 */
const useTopicUpdates = (): TopicVersions | undefined => {
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
