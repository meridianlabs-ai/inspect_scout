import clsx from "clsx";
import { FC, useRef } from "react";
import { useSearchParams } from "react-router-dom";

import { ChatViewVirtualList } from "../../../chat/ChatViewVirtualList";
import { useStore } from "../../../state/store";
import { TranscriptView } from "../../../transcript/TranscriptView";
import { ScannerData } from "../../types";

import styles from "./ResultBody.module.css";

export interface ResultBodyProps {
  result?: ScannerData;
}

export const ResultBody: FC<ResultBodyProps> = ({ result }) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [searchParams] = useSearchParams();

  // Get message or event ID from query params
  const initialMessageId = searchParams.get("message");
  const initialEventId = searchParams.get("event");

  const highlightLabeled = useStore((state) => state.highlightLabeled);

  return (
    <div ref={scrollRef} className={clsx(styles.container)}>
      <InputRenderer
        result={result}
        scrollRef={scrollRef}
        initialMessageId={initialMessageId}
        initialEventId={initialEventId}
        highlightLabeled={highlightLabeled}
      />
    </div>
  );
};

interface InputRendererProps {
  className?: string | string[];
  result?: ScannerData;
  scrollRef?: React.RefObject<HTMLDivElement | null>;
  initialMessageId?: string | null;
  initialEventId?: string | null;
  highlightLabeled?: boolean;
}

const InputRenderer: FC<InputRendererProps> = ({
  result,
  className,
  scrollRef,
  initialMessageId,
  initialEventId,
  highlightLabeled,
}) => {
  switch (result?.inputType) {
    case "transcript": {
      if (result.input.messages.length > 0) {
        const labels = result?.messageReferences.reduce(
          (acc, ref) => {
            if (ref.cite) {
              acc[ref.id] = ref.cite;
            }
            return acc;
          },
          {} as Record<string, string>
        );

        return (
          <ChatViewVirtualList
            messages={result.input.messages}
            allowLinking={false}
            id={"scan-input-virtual-list"}
            toolCallStyle={"complete"}
            indented={true}
            className={className}
            scrollRef={scrollRef}
            initialMessageId={initialMessageId}
            showLabels={true}
            highlightLabeled={highlightLabeled}
            labels={labels}
          />
        );
      } else if (result.input.events.length > 0) {
        return (
          <TranscriptView
            id={"scan-input-transcript"}
            events={result.input.events}
            scrollRef={scrollRef}
            initialEventId={initialEventId}
          />
        );
      } else {
        return <div>No Transcript Input Available</div>;
      }
    }
    case "messages": {
      return (
        <ChatViewVirtualList
          messages={result.input}
          allowLinking={false}
          id={"scan-input-virtual-list"}
          toolCallStyle={"complete"}
          indented={true}
          className={className}
          scrollRef={scrollRef}
          initialMessageId={initialMessageId}
        />
      );
    }
    case "message": {
      return (
        <ChatViewVirtualList
          messages={[result.input]}
          allowLinking={false}
          id={"scan-input-virtual-list"}
          toolCallStyle={"complete"}
          indented={true}
          className={className}
          scrollRef={scrollRef}
          initialMessageId={initialMessageId}
        />
      );
    }
    case "events": {
      return (
        <TranscriptView
          id={"scan-input-transcript"}
          events={result.input}
          scrollRef={scrollRef}
          initialEventId={initialEventId}
        />
      );
    }
    case "event": {
      return (
        <TranscriptView
          id={"scan-input-transcript"}
          events={[result.input]}
          scrollRef={scrollRef}
          initialEventId={initialEventId}
        />
      );
    }
    default:
      return <div>Unknown Input Type</div>;
  }
};
