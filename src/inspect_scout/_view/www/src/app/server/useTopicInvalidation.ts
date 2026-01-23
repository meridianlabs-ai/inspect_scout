import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { TopicVersions, useTopicUpdates } from "./useTopicUpdates";

/**
 * Monitors topic updates via SSE and invalidates dependent queries on change.
 *
 * For each topic whose timestamp changes, invalidates all queries containing
 * that topic name in their query key.
 *
 * Call once at app root level.
 */
export const useTopicInvalidation = (): void => {
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
};
