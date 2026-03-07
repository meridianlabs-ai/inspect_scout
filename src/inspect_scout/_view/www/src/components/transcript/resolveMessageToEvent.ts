/**
 * Resolves a message ID to the best matching event in a TimelineSpan tree.
 *
 * Used by the timeline view to navigate from a citation (which references a
 * message ID) to the corresponding event — either scrolling directly to it,
 * scrolling to an agent card that displays it, or selecting a swimlane first.
 */

import type { TimelineEvent, TimelineSpan } from "./timeline";

// =============================================================================
// Public API
// =============================================================================

export interface ResolvedMessageEvent {
  /** The event/node ID to scroll to in the visible event list. */
  eventId: string;
  /**
   * If non-null, the immediate child agent span that must be selected first.
   * The UI selects this span's swimlane row (which changes the visible
   * event list), then scrolls to `eventId` within it.
   */
  agentSpanId: string | null;
}

/**
 * Resolves a message ID to the best matching event in the timeline tree.
 *
 * Returns the event/node ID to scroll to and, if the match is inside a child
 * agent span, the agent span ID to select first. Returns undefined if no
 * match is found.
 */
export function resolveMessageToEvent(
  messageId: string,
  root: TimelineSpan
): ResolvedMessageEvent | undefined {
  const best = walkContent(messageId, root.content, null);
  if (!best) return undefined;
  return { eventId: best.eventId, agentSpanId: best.agentSpanId };
}

// =============================================================================
// Match priorities — lower number = higher priority
// =============================================================================

const PRIORITY_MODEL_OUTPUT = 1;
const PRIORITY_AGENT_CARD_RESULT = 2;
const PRIORITY_TOOL_MESSAGE_ID = 3;
const PRIORITY_TOOL_CALL_BRIDGE = 3.5;
const PRIORITY_MODEL_INPUT = 4;

interface Match {
  priority: number;
  eventId: string;
  agentSpanId: string | null;
}

// =============================================================================
// Tree walking
// =============================================================================

/**
 * Walk content items, collecting matches and returning the highest priority.
 *
 * `agentContext` tracks the immediate child agent span we're inside (if any).
 * For deeply nested agents, this stays as the first agent below root —
 * we navigate one level at a time.
 */
function walkContent(
  messageId: string,
  content: ReadonlyArray<TimelineEvent | TimelineSpan>,
  agentContext: string | null
): Match | null {
  let best: Match | null = null;

  // Pre-collect agent span IDs at this level for agent card result detection
  const agentSpanIds = new Set<string>();
  // Pre-collect tool event IDs (tool call IDs) at this level for tool_call_id bridge
  // Maps tool_call_id → event uuid
  const toolCallIdToUuid = new Map<string, string>();
  for (const item of content) {
    if (item.type === "span" && item.spanType === "agent") {
      agentSpanIds.add(item.id);
    } else if (item.type === "event" && item.event.event === "tool") {
      const toolEvent = item.event;
      if (toolEvent.uuid && toolEvent.id) {
        toolCallIdToUuid.set(toolEvent.id, toolEvent.uuid);
      }
    }
  }

  for (const item of content) {
    if (item.type === "event") {
      // Check this event for message ID matches
      const matches = matchEvent(
        messageId,
        item,
        agentContext,
        agentSpanIds,
        toolCallIdToUuid
      );
      for (const m of matches) {
        if (!best || m.priority < best.priority) {
          best = m;
        }
      }
    } else {
      // TimelineSpan — determine context for recursion
      if (item.spanType === "agent") {
        // Agent span: set agent context if not already inside one
        const childContext = agentContext ?? item.id;
        const childBest = walkContent(messageId, item.content, childContext);
        if (childBest && (!best || childBest.priority < best.priority)) {
          best = childBest;
        }
      } else {
        // Non-agent span (init, scoring, tool): transparent — inherit context
        const childBest = walkContent(messageId, item.content, agentContext);
        if (childBest && (!best || childBest.priority < best.priority)) {
          best = childBest;
        }
      }
    }
  }

  return best;
}

// =============================================================================
// Event matching
// =============================================================================

/**
 * Check a single event for message ID matches. Returns all matches found
 * (there can be multiple, e.g. same ID in input and output).
 */
function matchEvent(
  messageId: string,
  item: TimelineEvent,
  agentContext: string | null,
  agentSpanIds: ReadonlySet<string>,
  toolCallIdToUuid: ReadonlyMap<string, string>
): Match[] {
  const event = item.event;
  const matches: Match[] = [];

  if (event.event === "model") {
    const uuid = event.uuid;
    if (!uuid) return matches;

    // Priority 1: ModelEvent output
    if (event.output?.choices) {
      for (const choice of event.output.choices) {
        if (choice.message?.id === messageId) {
          matches.push({
            priority: PRIORITY_MODEL_OUTPUT,
            eventId: uuid,
            agentSpanId: agentContext,
          });
        }
      }
    }

    // Priority 2: Agent card result via bridge flow
    // Priority 3.5: Tool call bridge — tool-role message whose tool_call_id
    // matches a sibling ToolEvent's id. Redirects to the ToolEvent.
    if (event.input) {
      for (const msg of event.input) {
        if (msg.role === "tool" && msg.id === messageId) {
          const toolCallId = (msg as { tool_call_id?: string | null })
            .tool_call_id;
          if (toolCallId) {
            // Check agent card result first (highest priority of the two)
            const candidateSpanId = `agent-${toolCallId}`;
            if (agentSpanIds.has(candidateSpanId)) {
              matches.push({
                priority: PRIORITY_AGENT_CARD_RESULT,
                eventId: candidateSpanId,
                agentSpanId: agentContext,
              });
              continue; // Don't also match as model input or tool bridge
            }

            // Check tool call bridge — redirect to the tool event that produced this result
            const toolUuid = toolCallIdToUuid.get(toolCallId);
            if (toolUuid) {
              matches.push({
                priority: PRIORITY_TOOL_CALL_BRIDGE,
                eventId: toolUuid,
                agentSpanId: agentContext,
              });
              continue; // Don't also match as model input
            }
          }
        }
      }
    }

    // Priority 4: ModelEvent input
    if (event.input) {
      for (const msg of event.input) {
        if (msg.id === messageId) {
          // Skip if already matched as agent card result or tool bridge
          if (
            matches.some(
              (m) =>
                (m.priority === PRIORITY_AGENT_CARD_RESULT ||
                  m.priority === PRIORITY_TOOL_CALL_BRIDGE) &&
                m.eventId !== uuid
            )
          ) {
            continue;
          }
          matches.push({
            priority: PRIORITY_MODEL_INPUT,
            eventId: uuid,
            agentSpanId: agentContext,
          });
          break; // One input match is sufficient
        }
      }
    }
  } else if (event.event === "tool") {
    const uuid = event.uuid;
    if (!uuid) return matches;

    // Priority 2: Agent card result via span-based flow
    // ToolEvent with agent_span_id matching an agent span
    if (
      event.message_id === messageId &&
      event.agent_span_id &&
      agentSpanIds.has(event.agent_span_id)
    ) {
      matches.push({
        priority: PRIORITY_AGENT_CARD_RESULT,
        eventId: event.agent_span_id,
        agentSpanId: agentContext,
      });
    } else if (event.message_id === messageId) {
      // Priority 3: Regular ToolEvent.message_id match
      matches.push({
        priority: PRIORITY_TOOL_MESSAGE_ID,
        eventId: uuid,
        agentSpanId: agentContext,
      });
    }
  }

  return matches;
}
