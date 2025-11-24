import { ReactNode } from "react";

import { ChatView } from "../../chat/ChatView";
import { MarkdownReference } from "../../components/MarkdownDivWithReferences";
import { TranscriptView } from "../../transcript/TranscriptView";
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
            labeled={false}
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
              labeled={false}
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
              labeled={false}
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
