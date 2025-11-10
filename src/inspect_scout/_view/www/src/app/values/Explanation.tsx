import { FC, ReactNode, useMemo } from "react";
import { useParams } from "react-router-dom";

import { ChatView } from "../../chat/ChatView";
import {
  getRelativePathFromParams,
  parseScanResultPath,
  scanResultRoute,
} from "../../router/url";
import { TranscriptView } from "../../transcript/TranscriptView";
import {
  MarkdownDivWithReferences,
  MarkdownReference,
} from "../components/MarkdownDivWithReferences";
import { ScannerCore } from "../types";

interface ExplanationProps {
  result?: ScannerCore;
}

export const Explanation: FC<ExplanationProps> = ({ result }): ReactNode => {
  const params = useParams<{ "*": string }>();
  const refLookup = referenceTable(result);

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

  const refs: MarkdownReference[] = [];
  for (const ref of result.messageReferences) {
    refs.push({
      id: ref.id,
      cite: ref.cite,
      renderCitePreview: refLookup[ref.id],
      url: buildUrl(`tab=Input&message=${encodeURIComponent(ref.id)}`),
    });
  }

  for (const ref of result.eventReferences) {
    refs.push({
      id: ref.id,
      cite: ref.cite,
      renderCitePreview: refLookup[ref.id],
      url: buildUrl(`tab=Input&event=${encodeURIComponent(ref.id)}`),
    });
  }

  return (
    <MarkdownDivWithReferences
      markdown={result.explanation || ""}
      references={refs}
    />
  );
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
    return result.input.reduce((acc, msg) => {
      acc[msg.id] = () => {
        return (
          <ChatView
            messages={[msg]}
            resolveToolCallsIntoPreviousMessage={false}
          />
        );
      };
      return acc;
    }, {});
  } else if (result.inputType === "event") {
    return {
      [result.input.uuid]: () => {
        return (
          <TranscriptView id={"input-event-preview"} events={[result.input]} />
        );
      },
    };
  } else if (result.inputType === "events") {
    return result.input.reduce((acc, event, index) => {
      acc[event.uuid] = () => {
        return (
          <TranscriptView
            id={`input-event-preview-${index}`}
            events={result.input}
          />
        );
      };
      return acc;
    }, {});
  } else if (result.inputType === "transcript") {
    const eventRefs = result.input.events.reduce((acc, event) => {
      acc[event.uuid] = () => {
        return <TranscriptView id={"input-event-preview"} events={[event]} />;
      };
      return acc;
    }, {});

    const messageRefs = result.input.messages.reduce((acc, msg) => {
      acc[msg.id] = () => {
        return (
          <ChatView
            messages={[msg]}
            resolveToolCallsIntoPreviousMessage={false}
          />
        );
      };
      return acc;
    }, {});
    return { ...eventRefs, ...messageRefs };
  } else {
    return {};
  }
};
