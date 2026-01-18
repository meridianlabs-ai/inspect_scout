import { useCallback } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { parseTranscriptParams, transcriptRoute } from "../../../router/url";

/**
 * Converts a hash-router relative URL to a full absolute URL.
 */
const toFullUrl = (route: string): string => {
  return `${window.location.origin}${window.location.pathname}#${route}`;
};

/**
 * Hook for generating deep link URLs to specific events or messages
 * within a transcript.
 *
 * @returns Functions to generate URLs for event and message deep links
 */
export const useTranscriptNavigation = () => {
  const params = useParams<{ transcriptsDir: string; transcriptId: string }>();
  const { transcriptsDir, transcriptId } = parseTranscriptParams(params);
  const [searchParams] = useSearchParams();

  const getEventUrl = useCallback(
    (eventId: string): string | undefined => {
      if (!transcriptsDir || !transcriptId) return undefined;
      const newParams = new URLSearchParams(searchParams);
      newParams.set("tab", "transcript-events");
      newParams.set("event", eventId);
      newParams.delete("message");
      return transcriptRoute(transcriptsDir, transcriptId, newParams);
    },
    [transcriptsDir, transcriptId, searchParams]
  );

  const getMessageUrl = useCallback(
    (messageId: string): string | undefined => {
      if (!transcriptsDir || !transcriptId) return undefined;
      const newParams = new URLSearchParams(searchParams);
      newParams.set("tab", "transcript-messages");
      newParams.set("message", messageId);
      newParams.delete("event");
      return transcriptRoute(transcriptsDir, transcriptId, newParams);
    },
    [transcriptsDir, transcriptId, searchParams]
  );

  const getFullEventUrl = useCallback(
    (eventId: string): string | undefined => {
      const route = getEventUrl(eventId);
      return route ? toFullUrl(route) : undefined;
    },
    [getEventUrl]
  );

  const getFullMessageUrl = useCallback(
    (messageId: string): string | undefined => {
      const route = getMessageUrl(messageId);
      return route ? toFullUrl(route) : undefined;
    },
    [getMessageUrl]
  );

  return { getEventUrl, getMessageUrl, getFullEventUrl, getFullMessageUrl };
};
