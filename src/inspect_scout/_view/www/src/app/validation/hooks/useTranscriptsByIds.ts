import { skipToken, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { Column } from "../../../query";
import { useApi } from "../../../state/store";
import { TranscriptInfo } from "../../../types/api-types";

/**
 * Hook to fetch transcripts by their IDs using an IN query.
 * Returns a map of transcript_id -> TranscriptInfo for quick lookups.
 */
export const useTranscriptsByIds = (
  transcriptsDir: string | undefined,
  ids: string[]
): {
  data: Map<string, TranscriptInfo> | undefined;
  loading: boolean;
  error: Error | null;
} => {
  const api = useApi();

  // Create the IN filter condition
  const filter = useMemo(() => {
    if (ids.length === 0) return undefined;
    return new Column("transcript_id").in(ids);
  }, [ids]);

  // Stable query key based on sorted IDs
  const queryKey = useMemo(() => {
    const sortedIds = [...ids].sort();
    return ["transcriptsByIds", transcriptsDir, sortedIds];
  }, [transcriptsDir, ids]);

  const query = useQuery({
    queryKey,
    queryFn:
      !transcriptsDir || ids.length === 0
        ? skipToken
        : async () => {
            const response = await api.getTranscripts(
              transcriptsDir,
              filter,
              undefined,
              { limit: ids.length, cursor: null, direction: "forward" }
            );
            return response.items;
          },
    staleTime: 60 * 1000,
  });

  // Convert array to map for quick lookups
  const transcriptMap = useMemo(() => {
    if (!query.data) return undefined;
    const map = new Map<string, TranscriptInfo>();
    for (const transcript of query.data) {
      map.set(transcript.transcript_id, transcript);
    }
    return map;
  }, [query.data]);

  return {
    data: transcriptMap,
    loading: query.isLoading,
    error: query.error,
  };
};
