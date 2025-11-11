import { ReactNode } from "react";

import { ChatView } from "../../chat/ChatView";
import { TranscriptView } from "../../transcript/TranscriptView";
import { MarkdownReference } from "../components/MarkdownDivWithReferences";
import { ScannerCore } from "../types";

export type MakeReferenceUrl = (
  ref: string,
  type: "message" | "event"
) => string | undefined;

export const toMarkdownRefs = (
  core: ScannerCore,
  makeReferenceUrl: MakeReferenceUrl
) => {
  const refLookup = referenceTable(core);

  const refs: MarkdownReference[] = [];
  for (const ref of core.messageReferences) {
    refs.push({
      id: ref.id,
      cite: ref.cite,
      renderCitePreview: refLookup[ref.id],
      url: makeReferenceUrl(ref.id, "message"),
    });
  }

  for (const ref of core.eventReferences) {
    refs.push({
      id: ref.id,
      cite: ref.cite,
      renderCitePreview: refLookup[ref.id],
      url: makeReferenceUrl(ref.id, "event"),
    });
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
    return result.input.reduce<Record<string, () => ReactNode>>(
      (acc, event, index) => {
        acc[event.uuid] = () => {
          return (
            <TranscriptView
              id={`input-event-preview-${index}`}
              events={result.input}
            />
          );
        };
        return acc;
      },
      {}
    );
  } else if (result.inputType === "transcript") {
    const eventRefs = result.input.events.reduce<
      Record<string, () => ReactNode>
    >((acc, event) => {
      acc[event.uuid] = () => {
        return <TranscriptView id={"input-event-preview"} events={[event]} />;
      };
      return acc;
    }, {});

    const messageRefs = result.input.messages.reduce<
      Record<string, () => ReactNode>
    >((acc, msg) => {
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
