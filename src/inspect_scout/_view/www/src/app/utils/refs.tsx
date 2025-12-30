import { ReactNode, useMemo } from "react";

import { ChatView } from "../../chat/ChatView";
import { MarkdownReference } from "../../components/MarkdownDivWithReferences";
import { scanResultRoute } from "../../router/url";
import { TranscriptView } from "../../transcript/TranscriptView";
import { useScanRoute } from "../hooks";
import {
  ScanResultInputData,
  isEventInput,
  isEventsInput,
  isMessageInput,
  isMessagesInput,
  isTranscriptInput,
  ScanResultSummary,
} from "../types";

export type MakeReferenceUrl = (
  ref: string,
  type: "message" | "event"
) => string | undefined;

export const useMarkdownRefs = (
  summary?: ScanResultSummary,
  inputData?: ScanResultInputData
) => {
  const { scansDir, scanPath } = useScanRoute();
  // Build URL to the scan result with the appropriate query parameters
  const buildUrl = useMemo(() => {
    if (!summary?.uuid) {
      return (queryParams: string) => `?${queryParams}`;
    }

    return (queryParams: string) => {
      if (!scansDir) {
        return `?${queryParams}`;
      }
      const searchParams = new URLSearchParams(queryParams);
      return `#${scanResultRoute(scansDir, scanPath, summary.uuid, searchParams)}`;
    };
  }, [summary?.uuid, scanPath, scansDir]);

  const refs: MarkdownReference[] = summary
    ? toMarkdownRefs(
        summary,
        (refId: string, type: "message" | "event") => {
          if (type === "message") {
            return buildUrl(`tab=Result&message=${encodeURIComponent(refId)}`);
          } else {
            return buildUrl(`tab=Result&event=${encodeURIComponent(refId)}`);
          }
        },
        inputData
      )
    : [];
  return refs;
};

export const toMarkdownRefs = (
  summary: ScanResultSummary,
  makeReferenceUrl: MakeReferenceUrl,
  inputData?: ScanResultInputData
) => {
  const refLookup = referenceTable(inputData);

  const refs: MarkdownReference[] = [];
  for (const ref of summary.messageReferences) {
    const renderPreview = refLookup[ref.id];
    const refUrl = makeReferenceUrl(ref.id, "message");
    if (ref.cite && (renderPreview || refUrl)) {
      refs.push({
        id: ref.id,
        cite: ref.cite,
        citePreview: renderPreview,
        citeUrl: refUrl,
      });
    }
  }

  for (const ref of summary.eventReferences) {
    const renderPreview = refLookup[ref.id];
    const refUrl = makeReferenceUrl(ref.id, "event");
    if (ref.cite && (renderPreview || refUrl)) {
      refs.push({
        id: ref.id,
        cite: ref.cite,
        citePreview: renderPreview,
        citeUrl: refUrl,
      });
    }
  }
  return refs;
};

const referenceTable = (
  inputData?: ScanResultInputData
): Record<string, () => ReactNode> => {
  if (!inputData) {
    return {};
  }

  if (isMessageInput(inputData)) {
    if (!inputData.input.id) {
      return {};
    }
    return {
      [inputData.input.id]: () => {
        return (
          <ChatView
            messages={[inputData.input]}
            resolveToolCallsIntoPreviousMessage={false}
          />
        );
      },
    };
  } else if (isMessagesInput(inputData)) {
    return inputData.input.reduce<Record<string, () => ReactNode>>(
      (acc, msg) => {
        if (msg.id) {
          acc[msg.id] = () => {
            return (
              <ChatView
                messages={[msg]}
                resolveToolCallsIntoPreviousMessage={false}
              />
            );
          };
        }
        return acc;
      },
      {}
    );
  } else if (isEventInput(inputData)) {
    if (!inputData.input.uuid) {
      return {};
    }

    return {
      [inputData.input.uuid]: () => {
        return (
          <TranscriptView
            id={"input-event-preview"}
            events={[inputData.input]}
          />
        );
      },
    };
  } else if (isEventsInput(inputData)) {
    return inputData.input.reduce<Record<string, () => ReactNode>>(
      (acc, event, index) => {
        if (event.uuid) {
          acc[event.uuid] = () => {
            return (
              <TranscriptView
                id={`input-event-preview-${index}`}
                events={inputData.input}
              />
            );
          };
        }
        return acc;
      },
      {}
    );
  } else if (isTranscriptInput(inputData)) {
    const eventRefs = inputData.input.events.reduce<
      Record<string, () => ReactNode>
    >((acc, event) => {
      if (event.uuid) {
        acc[event.uuid] = () => {
          return <TranscriptView id={"input-event-preview"} events={[event]} />;
        };
      }
      return acc;
    }, {});

    const messageRefs = inputData.input.messages.reduce<
      Record<string, () => ReactNode>
    >((acc, msg) => {
      if (msg.id) {
        acc[msg.id] = () => {
          return (
            <ChatView
              messages={[msg]}
              resolveToolCallsIntoPreviousMessage={false}
            />
          );
        };
      }
      return acc;
    }, {});
    return { ...eventRefs, ...messageRefs };
  } else {
    return {};
  }
};
