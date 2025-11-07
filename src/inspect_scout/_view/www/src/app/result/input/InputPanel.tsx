import clsx from "clsx";
import { FC, useRef } from "react";

import { ChatViewVirtualList } from "../../../chat/ChatViewVirtualList";
import { TranscriptView } from "../../../transcript/TranscriptView";
import { ScannerData } from "../../types";

import styles from "./InputPanel.module.css";

export interface InputPanelProps {
  result?: ScannerData;
}

export const InputPanel: FC<InputPanelProps> = ({ result }) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  return (
    <div ref={scrollRef} className={clsx(styles.container)}>
      <InputRenderer result={result} scrollRef={scrollRef} />
    </div>
  );
};

interface InputRendererProps {
  className?: string | string[];
  result?: ScannerData;
  scrollRef?: React.RefObject<HTMLDivElement | null>;
}

const InputRenderer: FC<InputRendererProps> = ({
  result,
  className,
  scrollRef,
}) => {
  switch (result?.inputType) {
    case "transcript": {
      if (result.input.messages.length > 0) {
        return (
          <ChatViewVirtualList
            messages={result.input.messages}
            allowLinking={false}
            id={"scan-input-virtual-list"}
            toolCallStyle={"complete"}
            indented={true}
            className={className}
            scrollRef={scrollRef}
          />
        );
      } else if (result.input.events.length > 0) {
        return (
          <TranscriptView
            id={"scan-input-transcript"}
            events={result.input.events}
            scrollRef={scrollRef}
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
        />
      );
    }
    case "events": {
      return (
        <TranscriptView
          id={"scan-input-transcript"}
          events={result.input}
          scrollRef={scrollRef}
        />
      );
    }
    case "event": {
      return (
        <TranscriptView
          id={"scan-input-transcript"}
          events={[result.input]}
          scrollRef={scrollRef}
        />
      );
    }
    default:
      return <div>Unknown Input Type</div>;
  }
};
