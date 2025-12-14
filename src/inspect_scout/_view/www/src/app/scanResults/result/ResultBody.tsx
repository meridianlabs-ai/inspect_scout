import clsx from "clsx";
import { FC, useRef } from "react";
import { useSearchParams } from "react-router-dom";

import { ChatViewVirtualList } from "../../../chat/ChatViewVirtualList";
import { useStore } from "../../../state/store";
import { TranscriptView } from "../../../transcript/TranscriptView";
import { ColumnHeader } from "../../components/ColumnHeader";
import {
  ScanResultInputData,
  isEventInput,
  isEventsInput,
  isMessageInput,
  isMessagesInput,
  isTranscriptInput,
  ScanResultData,
} from "../../types";

import styles from "./ResultBody.module.css";

export interface ResultBodyProps {
  resultData?: ScanResultData;
  inputData?: ScanResultInputData;
}

export const ResultBody: FC<ResultBodyProps> = ({ resultData, inputData }) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [searchParams] = useSearchParams();

  // Get message or event ID from query params
  const initialMessageId = searchParams.get("message");
  const initialEventId = searchParams.get("event");

  const highlightLabeled = useStore((state) => state.highlightLabeled);

  return (
    <div className={styles.container}>
      <ColumnHeader label="Input" />
      <div ref={scrollRef} className={clsx(styles.scrollable)}>
        <InputRenderer
          resultData={resultData}
          inputData={inputData}
          scrollRef={scrollRef}
          initialMessageId={initialMessageId}
          initialEventId={initialEventId}
          highlightLabeled={highlightLabeled}
        />
      </div>
    </div>
  );
};

interface InputRendererProps {
  className?: string | string[];
  resultData?: ScanResultData;
  inputData?: ScanResultInputData;
  scrollRef?: React.RefObject<HTMLDivElement | null>;
  initialMessageId?: string | null;
  initialEventId?: string | null;
  highlightLabeled?: boolean;
}

const InputRenderer: FC<InputRendererProps> = ({
  resultData,
  inputData,
  className,
  scrollRef,
  initialMessageId,
  initialEventId,
  highlightLabeled,
}) => {
  const loading = useStore((state) => state.loading);
  const loadingData = useStore((state) => state.loadingData);
  if (!inputData) {
    return loading || loadingData ? undefined : <div>No Input Available</div>;
  }

  if (isTranscriptInput(inputData)) {
    if (inputData.input.messages.length > 0) {
      const labels = resultData?.messageReferences.reduce(
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
          messages={inputData.input.messages}
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
    } else if (inputData.input.events.length > 0) {
      return (
        <TranscriptView
          id={"scan-input-transcript"}
          events={inputData.input.events}
          scrollRef={scrollRef}
          initialEventId={initialEventId}
        />
      );
    } else {
      return <div>No Transcript Input Available</div>;
    }
  } else if (isMessagesInput(inputData)) {
    return (
      <ChatViewVirtualList
        messages={inputData.input}
        allowLinking={false}
        id={"scan-input-virtual-list"}
        toolCallStyle={"complete"}
        indented={true}
        className={className}
        scrollRef={scrollRef}
        initialMessageId={initialMessageId}
      />
    );
  } else if (isMessageInput(inputData)) {
    return (
      <ChatViewVirtualList
        messages={[inputData.input]}
        allowLinking={false}
        id={"scan-input-virtual-list"}
        toolCallStyle={"complete"}
        indented={true}
        className={className}
        scrollRef={scrollRef}
        initialMessageId={initialMessageId}
      />
    );
  } else if (isEventsInput(inputData)) {
    return (
      <TranscriptView
        id={"scan-input-transcript"}
        events={inputData.input}
        scrollRef={scrollRef}
        initialEventId={initialEventId}
      />
    );
  } else if (isEventInput(inputData)) {
    return (
      <TranscriptView
        id={"scan-input-transcript"}
        events={[inputData.input]}
        scrollRef={scrollRef}
        initialEventId={initialEventId}
      />
    );
  } else {
    return <div>Unsupported Input Type</div>;
  }
};
