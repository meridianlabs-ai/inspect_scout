import { useMemo } from "react";

import { attachSourceSpans } from "../../../app/timeline/timelineEventNodes";
import type { TimelineSpan } from "../../../components/transcript/timeline";
import type {
  Event,
  SpanBeginEvent,
  StepEvent,
  SubtaskEvent,
  ToolEvent,
} from "../../../types/api-types";
import { fixupEventStream, kSandboxSignalName } from "../transform/fixups";
import { treeifyEvents } from "../transform/treeify";
import { EventNode, EventType, kCollapsibleEventTypes } from "../types";

export const useEventNodes = (
  events: Event[],
  running: boolean,
  sourceSpans?: ReadonlyMap<string, TimelineSpan>,
  agentToolEvents?: ReadonlyMap<string, ToolEvent>
) => {
  // Normalize Events in a flattened filtered list
  const { eventTree, defaultCollapsedIds } = useMemo((): {
    eventTree: EventNode[];
    defaultCollapsedIds: Record<string, true>;
  } => {
    // Apply fixups to the event string
    const resolvedEvents = fixupEventStream(events, !running);

    // Build the event tree
    const rawEventTree = treeifyEvents(resolvedEvents, 0);

    // Attach source span references before filtering so filterEmpty
    // can preserve agent card nodes (which have no children by design).
    if (sourceSpans && sourceSpans.size > 0) {
      attachSourceSpans(rawEventTree, sourceSpans, agentToolEvents);
    }

    // Now filter the tree to remove empty spans
    const filterEmpty = (
      eventNodes: EventNode<EventType>[]
    ): EventNode<EventType>[] => {
      return eventNodes.filter((node) => {
        if (node.children && node.children.length > 0) {
          node.children = filterEmpty(node.children);
        }
        // Preserve nodes with a sourceSpan (e.g. agent cards)
        if (node.sourceSpan) return true;
        return (
          (node.event.event !== "span_begin" && node.event.event !== "step") ||
          (node.children && node.children.length > 0)
        );
      });
    };
    const eventTree = filterEmpty(rawEventTree);

    // Apply collapse filters to the event tree
    const defaultCollapsedIds: Record<string, true> = {};
    const findCollapsibleEvents = (nodes: EventNode[]) => {
      for (const node of nodes) {
        if (
          kCollapsibleEventTypes.includes(node.event.event) &&
          collapseFilters.some((filter) =>
            filter(
              node.event as
                | StepEvent
                | SpanBeginEvent
                | ToolEvent
                | SubtaskEvent
            )
          )
        ) {
          defaultCollapsedIds[node.id] = true;
        }

        // Recursively check children
        findCollapsibleEvents(node.children);
      }
    };
    findCollapsibleEvents(eventTree);

    return { eventTree, defaultCollapsedIds };
  }, [events, running, sourceSpans, agentToolEvents]);

  return { eventNodes: eventTree, defaultCollapsedIds };
};

const collapseFilters: Array<
  (event: StepEvent | SpanBeginEvent | ToolEvent | SubtaskEvent) => boolean
> = [
  (event: StepEvent | SpanBeginEvent | ToolEvent | SubtaskEvent) =>
    event.type === "solver" && event.name === "system_message",
  (event: StepEvent | SpanBeginEvent | ToolEvent | SubtaskEvent) => {
    if (event.event === "step" || event.event === "span_begin") {
      return (
        event.name === kSandboxSignalName ||
        event.name === "init" ||
        event.name === "sample_init"
      );
    }
    return false;
  },
  (event: StepEvent | SpanBeginEvent | ToolEvent | SubtaskEvent) =>
    event.event === "tool" && !event.agent && !event.failed,
  (event: StepEvent | SpanBeginEvent | ToolEvent | SubtaskEvent) =>
    event.event === "subtask",
];
