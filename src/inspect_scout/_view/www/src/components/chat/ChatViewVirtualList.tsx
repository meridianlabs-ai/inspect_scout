import clsx from "clsx";
import {
  FC,
  memo,
  ReactNode,
  RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
} from "react";
import { ContextProp, ItemProps, VirtuosoHandle } from "react-virtuoso";

import { ChatMessage } from "../../types/api-types";
import { LiveVirtualList } from "../LiveVirtualList";

import { ChatMessageRow } from "./ChatMessageRow";
import styles from "./ChatViewVirtualList.module.css";
import { ResolvedMessage, resolveMessages } from "./messages";
import { messageSearchText } from "./messageSearchText";
import { ChatViewToolCallStyle } from "./types";

interface ChatViewVirtualListProps {
  id: string;
  className?: string | string[];
  messages: ChatMessage[];
  initialMessageId?: string | null;
  topOffset?: number;
  toolCallStyle: ChatViewToolCallStyle;
  indented: boolean;
  numbered?: boolean;
  scrollRef?: RefObject<HTMLDivElement | null>;
  running?: boolean;
  getMessageUrl?: (id: string) => string | undefined;
  allowLinking?: boolean;
  labels?: Record<string, string>;
  showLabels?: boolean;
  highlightLabeled?: boolean;
}

interface ChatViewVirtualListComponentProps extends ChatViewVirtualListProps {
  listHandle: RefObject<VirtuosoHandle | null>;
}

export const ChatViewVirtualList: FC<ChatViewVirtualListProps> = memo(
  ({
    id,
    messages,
    initialMessageId,
    topOffset,
    className,
    toolCallStyle,
    indented,
    scrollRef,
    running,
    allowLinking = true,
    labels,
    showLabels = true,
    highlightLabeled = false,
  }) => {
    const listHandle = useRef<VirtuosoHandle>(null);

    useEffect(() => {
      const handleKeyDown = (event: KeyboardEvent) => {
        if (event.metaKey || event.ctrlKey) {
          if (event.key === "ArrowUp") {
            listHandle.current?.scrollToIndex({ index: 0, align: "center" });
            event.preventDefault();
          } else if (event.key === "ArrowDown") {
            listHandle.current?.scrollToIndex({
              index: Math.min(messages.length - 5, 0),
              align: "center",
            });

            // This is needed to allow measurement to complete before finding
            // the last item to scroll to it properly. The timing isn't magical sadly
            // it is just a heuristic.
            setTimeout(() => {
              listHandle.current?.scrollToIndex({
                index: messages.length - 1,
                align: "end",
              });
            }, 250);
            event.preventDefault();
          }
        }
      };

      const scrollElement = scrollRef?.current;
      if (scrollElement) {
        scrollElement.addEventListener("keydown", handleKeyDown);
        // Make the element focusable so it can receive keyboard events
        if (!scrollElement.hasAttribute("tabIndex")) {
          scrollElement.setAttribute("tabIndex", "0");
        }

        return () => {
          scrollElement.removeEventListener("keydown", handleKeyDown);
        };
      }
    }, [scrollRef, messages]);

    return (
      <ChatViewVirtualListComponent
        id={id}
        listHandle={listHandle}
        className={className}
        scrollRef={scrollRef}
        messages={messages}
        initialMessageId={initialMessageId}
        topOffset={topOffset}
        toolCallStyle={toolCallStyle}
        indented={indented}
        running={running}
        allowLinking={allowLinking}
        labels={labels}
        showLabels={showLabels}
        highlightLabeled={highlightLabeled}
      />
    );
  }
);

/**
 * Renders the ChatViewVirtualList component.
 */
export const ChatViewVirtualListComponent: FC<ChatViewVirtualListComponentProps> =
  memo(
    ({
      id,
      listHandle,
      messages,
      initialMessageId,
      topOffset,
      className,
      toolCallStyle,
      indented,
      scrollRef,
      running,
      allowLinking = true,
      labels,
      showLabels = true,
      highlightLabeled,
    }) => {
      const collapsedMessages = useMemo(() => {
        return resolveMessages(messages);
      }, [messages]);

      const initialMessageIndex = useMemo(() => {
        if (initialMessageId === null || initialMessageId === undefined) {
          return undefined;
        }

        const index = collapsedMessages.findIndex((message) => {
          const messageId = message.message.id === initialMessageId;
          if (messageId) {
            return true;
          }

          if (message.toolMessages.find((tm) => tm.id === initialMessageId)) {
            return true;
          }
        });
        return index !== -1 ? index : undefined;
      }, [initialMessageId, collapsedMessages]);

      const renderRow = useCallback(
        (index: number, item: ResolvedMessage): ReactNode => {
          return (
            <ChatMessageRow
              index={index}
              parentName={id || "chat-virtual-list"}
              showLabels={showLabels}
              highlightLabeled={highlightLabeled}
              labels={labels}
              resolvedMessage={item}
              indented={indented}
              toolCallStyle={toolCallStyle}
              highlightUserMessage={true}
              allowLinking={allowLinking}
            />
          );
        },
        // TODO: lint react-hooks/exhaustive-deps
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [
          id,
          showLabels,
          labels,
          indented,
          toolCallStyle,
          collapsedMessages,
          highlightLabeled,
          allowLinking,
        ]
      );

      const Item = ({
        children,
        ...props
      }: ItemProps<any> & ContextProp<any>) => {
        return (
          <div
            className={clsx(styles.item)}
            data-index={props["data-index"]}
            data-item-group-index={props["data-item-group-index"]}
            data-item-index={props["data-item-index"]}
            data-known-size={props["data-known-size"]}
            style={props.style}
          >
            {children}
          </div>
        );
      };

      return (
        <LiveVirtualList<ResolvedMessage>
          id="chat-virtual-list"
          listHandle={listHandle}
          className={className}
          scrollRef={scrollRef}
          data={collapsedMessages}
          renderRow={renderRow}
          initialTopMostItemIndex={initialMessageIndex}
          offsetTop={topOffset}
          live={running}
          showProgress={running}
          components={{ Item }}
          animation={false}
          itemSearchText={messageSearchText}
        />
      );
    }
  );
