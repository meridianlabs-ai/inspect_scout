import { ReactNode, useMemo } from "react";
import { useParams } from "react-router-dom";

import { ChatView } from "../../chat/ChatView";
import { MarkdownReference } from "../../components/MarkdownDivWithReferences";
import {
  getRelativePathFromParams,
  parseScanResultPath,
  scanResultRoute,
} from "../../router/url";
import { TranscriptView } from "../../transcript/TranscriptView";
import { ScannerCore } from "../types";

export type MakeReferenceUrl = (
  ref: string,
  type: "message" | "event"
) => string | undefined;

export const useMarkdownRefs = (result?: ScannerCore) => {
  const params = useParams<{ "*": string }>();
  // Build URL to the scan result with the appropriate query parameters
  const buildUrl = useMemo(() => {
    if (!result?.uuid) {
      return (queryParams: string) => `?${queryParams}`;
    }

    // Get the scan path from the current URL params
    const relativePath = getRelativePathFromParams(params);
    const { scanPath } = parseScanResultPath(relativePath);

    return (queryParams: string) => {
      const searchParams = new URLSearchParams(queryParams);
      return `#${scanResultRoute(scanPath, result.uuid, searchParams)}`;
    };
  }, [result?.uuid, params]);

  const refs: MarkdownReference[] = result
    ? toMarkdownRefs(result, (refId: string, type: "message" | "event") => {
        if (type === "message") {
          return buildUrl(`tab=Result&message=${encodeURIComponent(refId)}`);
        } else {
          return buildUrl(`tab=Result&event=${encodeURIComponent(refId)}`);
        }
      })
    : [];
  return refs;
};

export const toMarkdownRefs = (
  core: ScannerCore,
  makeReferenceUrl: MakeReferenceUrl
) => {
  const refLookup = referenceTable(core);

  const refs: MarkdownReference[] = [];
  for (const ref of core.messageReferences) {
    const renderPreview = refLookup[ref.id];
    if (ref.cite && renderPreview) {
      refs.push({
        id: ref.id,
        cite: ref.cite,
        citePreview: renderPreview,
        citeUrl: makeReferenceUrl(ref.id, "message"),
      });
    }
  }

  for (const ref of core.eventReferences) {
    const renderPreview = refLookup[ref.id];
    if (ref.cite && renderPreview) {
      refs.push({
        id: ref.id,
        cite: ref.cite,
        citePreview: renderPreview,
        citeUrl: makeReferenceUrl(ref.id, "event"),
      });
    }
  }
  return refs;
};

const referenceTable = (
  result?: ScannerCore
): Record<string, () => ReactNode> => {
  if (!result) {
    return {};
  }

  if (!result.input) {
    return {};
  }

  if (result.inputType === "message") {
    if (!result.input.id) {
      return {};
    }
    return {
      [result.input.id]: () => {
        return (
          <ChatView
            messages={[result.input]}
            resolveToolCallsIntoPreviousMessage={false}
          />
        );
      },
    };
  } else if (result.inputType === "messages") {
    return result.input.reduce<Record<string, () => ReactNode>>((acc, msg) => {
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
  } else if (result.inputType === "event") {
    if (!result.input.uuid) {
      return {};
    }

    return {
      [result.input.uuid]: () => {
        return (
          <TranscriptView id={"input-event-preview"} events={[result.input]} />
        );
      },
    };
  } else if (result.inputType === "events") {
    return result.input.reduce<Record<string, () => ReactNode>>(
      (acc, event, index) => {
        if (event.uuid) {
          acc[event.uuid] = () => {
            return (
              <TranscriptView
                id={`input-event-preview-${index}`}
                events={result.input}
              />
            );
          };
        }
        return acc;
      },
      {}
    );
  } else if (result.inputType === "transcript") {
    const eventRefs = result.input.events.reduce<
      Record<string, () => ReactNode>
    >((acc, event) => {
      if (event.uuid) {
        acc[event.uuid] = () => {
          return <TranscriptView id={"input-event-preview"} events={[event]} />;
        };
      }
      return acc;
    }, {});

    const messageRefs = result.input.messages.reduce<
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
