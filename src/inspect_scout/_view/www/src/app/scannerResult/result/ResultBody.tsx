import clsx from "clsx";
import { FC, useCallback, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { ChatViewVirtualList } from "../../../components/chat/ChatViewVirtualList";
import { ApplicationIcons } from "../../../components/icons";
import { NoContentsPanel } from "../../../components/NoContentsPanel";
import { transcriptRoute } from "../../../router/url";
import { useStore } from "../../../state/store";
import {
  ColumnHeader,
  ColumnHeaderButton,
} from "../../components/ColumnHeader";
import { TimelineEventsView } from "../../timeline/components/TimelineEventsView";
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
  resultData: ScanResultData;
  inputData: ScanResultInputData;
  transcriptDir: string;
  hasTranscript: boolean;
}

export const ResultBody: FC<ResultBodyProps> = ({
  resultData,
  inputData,
  transcriptDir,
  hasTranscript,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Get message or event ID from query params
  const initialMessageId = searchParams.get("message");
  const initialEventId = searchParams.get("event");

  const highlightLabeled = useStore((state) => state.highlightLabeled);

  const handleNavigateToTranscript = useCallback(() => {
    if (transcriptDir && resultData.transcriptId) {
      void navigate(transcriptRoute(transcriptDir, resultData.transcriptId));
    }
  }, [navigate, transcriptDir, resultData.transcriptId]);

  // Only show the transcript button when we have both transcriptsDir and transcriptId
  const canNavigateToTranscript =
    hasTranscript && transcriptDir.length > 0 && resultData.transcriptId;
  const transcriptAction = canNavigateToTranscript ? (
    <ColumnHeaderButton
      icon={ApplicationIcons.transcript}
      onClick={handleNavigateToTranscript}
      title="View complete transcript"
    />
  ) : undefined;

  return (
    <div className={clsx(styles.container, containerClass(inputData))}>
      <ColumnHeader label="Input" actions={transcriptAction} />
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
  inputData: ScanResultInputData;
  scrollRef: React.RefObject<HTMLDivElement | null>;
  initialMessageId?: string | null;
  initialEventId?: string | null;
  highlightLabeled?: boolean;
}

const containerClass = (
  inputData: ScanResultInputData
): string | string[] | undefined => {
  if (isTranscriptInput(inputData)) {
    return styles.transcriptInputContainer;
  } else if (isEventsInput(inputData)) {
    return styles.eventsInputContainer;
  } else {
    return styles.chatInputContainer;
  }
};

const InputRenderer: FC<InputRendererProps> = ({
  resultData,
  inputData,
  className,
  scrollRef,
  initialMessageId,
  initialEventId,
  highlightLabeled,
}) => {
  if (isTranscriptInput(inputData)) {
    if (inputData.input.messages && inputData.input.messages.length > 0) {
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
          messages={inputData.input.messages || []}
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
    } else if (inputData.input.events && inputData.input.events.length > 0) {
      return (
        <TimelineEventsView
          events={inputData.input.events}
          scrollRef={scrollRef}
          id="scan-input-events"
          initialEventId={initialEventId}
        />
      );
    } else {
      return <NoContentsPanel text="No transcript input available" />;
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
      <TimelineEventsView
        events={inputData.input}
        scrollRef={scrollRef}
        id="scan-input-events"
        initialEventId={initialEventId}
      />
    );
  } else if (isEventInput(inputData)) {
    return (
      <TimelineEventsView
        events={[inputData.input]}
        scrollRef={scrollRef}
        id="scan-input-events"
        initialEventId={initialEventId}
      />
    );
  } else {
    return <div>Unsupported Input Type</div>;
  }
};
