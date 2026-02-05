import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, useRef } from "react";

import { TopicVersions } from "../../api/api";
import { useApi } from "../../state/store";

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
  const prevVersionsRef = useRef<TopicVersions | undefined>(undefined);

  useEffect(() => {
    if (versions === undefined) return;

    const changedTopics = Object.entries(versions).filter(
      ([topic, timestamp]) => prevVersionsRef.current?.[topic] !== timestamp
    );
    for (const [topic] of changedTopics) {
      const invKey = `${topic}-inv`;
      void queryClient.invalidateQueries({
        predicate: (query) => query.queryKey.includes(invKey),
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
  const api = useApi();
  const [versions, setVersions] = useState<TopicVersions | undefined>(
    undefined
  );

  useEffect(() => api.connectTopicUpdates(setVersions), [api, setVersions]);

  return versions;
};
