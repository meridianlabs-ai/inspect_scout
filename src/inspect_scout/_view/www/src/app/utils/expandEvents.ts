import type {
  ChatMessage,
  Event,
  EventsData,
  ModelEvent,
} from "../../types/api-types";

/**
 * Expand range-encoded refs against a pool.
 * Each ref is [start, endExclusive] → pool.slice(start, endExclusive).
 */
function expandRefs<T>(refs: [number, number][], pool: T[]): T[] {
  return refs.flatMap(([start, end]) => pool.slice(start, end));
}

function isModelEvent(event: Event): event is ModelEvent {
  return event.event === "model";
}

/**
 * Expand condensed ModelEvent input/call refs back to inline data.
 *
 * Pure function — returns a new array; input is not mutated.
 * Non-ModelEvents and ModelEvents without refs pass through unchanged.
 */
export function expandEvents(
  events: Event[],
  eventsData: EventsData | null
): Event[] {
  if (!eventsData) return events;

  const { messages, calls } = eventsData;
  const hasMessages = messages.length > 0;
  const hasCalls = calls.length > 0;
  if (!hasMessages && !hasCalls) return events;

  return events.map((event) => {
    if (!isModelEvent(event)) return event;

    let changed = false;
    let input: ChatMessage[] = event.input;
    let call: ModelEvent["call"] = event.call;

    // Expand input refs
    if (event.input_refs != null && hasMessages) {
      input = expandRefs(event.input_refs, messages);
      changed = true;
    }

    // Expand call refs
    if (call?.call_refs != null && hasCalls) {
      const key = call.call_key ?? "messages";
      const expandedMsgs = expandRefs(call.call_refs, calls);
      call = {
        ...call,
        request: { ...call.request, [key]: expandedMsgs },
        call_refs: null,
        call_key: null,
      };
      changed = true;
    }

    return changed ? { ...event, input, input_refs: null, call } : event;
  });
}
