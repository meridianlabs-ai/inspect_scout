/**
 * Transcript nodes: hierarchical structure for visualization and scanning.
 *
 * Transforms flat event streams into a semantic tree with agent-centric interpretation
 * and phase separation (init/agent/scoring).
 *
 * TypeScript port of Python's nodes.py, implementing our own span tree building
 * since we don't have access to inspect_ai's event_tree().
 */

import type { Event, ToolEvent } from "../../types/api-types";

// =============================================================================
// Agent Source Types
// =============================================================================

/**
 * Agent detected via explicit span with type='agent'.
 */
export interface AgentSourceSpan {
  source: "span";
  spanId: string;
}

/**
 * Agent inferred from tool call spawning nested events.
 */
export interface AgentSourceTool {
  source: "tool";
  toolEvent?: ToolEvent;
}

export type AgentSource = AgentSourceSpan | AgentSourceTool;

// =============================================================================
// Span Tree Types (internal)
// =============================================================================

/**
 * Internal representation of a span node built from span_begin/span_end events.
 */
interface SpanNode {
  id: string;
  name: string;
  type?: string;
  parentId?: string | null;
  children: TreeItem[];
}

type TreeItem = SpanNode | Event;

function isSpanNode(item: TreeItem): item is SpanNode {
  return (
    typeof item === "object" &&
    item !== null &&
    "children" in item &&
    Array.isArray(item.children)
  );
}

// =============================================================================
// Node Types
// =============================================================================

/**
 * Base interface for computed properties on all transcript nodes.
 */
interface TranscriptNodeBase {
  startTime: Date | null;
  endTime: Date | null;
  totalTokens: number;
}

/**
 * Wraps a single Event with computed timing and token properties.
 */
export interface EventNodeType extends TranscriptNodeBase {
  type: "event";
  event: Event;
}

/**
 * Represents an agent with nested content (events and child agents).
 */
export interface AgentNodeType extends TranscriptNodeBase {
  type: "agent";
  id: string;
  name: string;
  source: AgentSource;
  content: (EventNodeType | AgentNodeType)[];
  taskDescription?: string;
}

/**
 * Section node for init or scoring phases (EventNodes only).
 */
export interface SectionNodeType extends TranscriptNodeBase {
  type: "section";
  section: "init" | "scoring";
  content: EventNodeType[];
}

/**
 * Root container for transcript node hierarchy.
 */
export interface TranscriptNodes {
  init: SectionNodeType | null;
  agent: AgentNodeType | null;
  scoring: SectionNodeType | null;
  startTime: Date | null;
  endTime: Date | null;
  totalTokens: number;
}

export type TranscriptNode = EventNodeType | AgentNodeType | SectionNodeType;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Parse a timestamp string to Date, handling null/undefined.
 */
function parseTimestamp(timestamp: string | null | undefined): Date | null {
  if (!timestamp) return null;
  const date = new Date(timestamp);
  return isNaN(date.getTime()) ? null : date;
}

/**
 * Get the start time for an event.
 */
function getEventStartTime(event: Event): Date | null {
  const timestamp = (event as { timestamp?: string }).timestamp;
  return parseTimestamp(timestamp);
}

/**
 * Get the end time for an event (completed if available, else timestamp).
 */
function getEventEndTime(event: Event): Date | null {
  const completed = (event as { completed?: string }).completed;
  if (completed) {
    return parseTimestamp(completed);
  }
  return getEventStartTime(event);
}

/**
 * Get tokens from an event (ModelEvent only).
 */
function getEventTokens(event: Event): number {
  if (event.event === "model") {
    const usage = event.output?.usage;
    if (usage) {
      const inputTokens = usage.input_tokens ?? 0;
      const outputTokens = usage.output_tokens ?? 0;
      return inputTokens + outputTokens;
    }
  }
  return 0;
}

/**
 * Return the earliest start time among nodes.
 */
function minStartTime(
  nodes: (TranscriptNode | TranscriptNodeBase)[]
): Date | null {
  const times = nodes
    .map((n) => n.startTime)
    .filter((t): t is Date => t !== null);
  if (times.length === 0) return null;
  return times.reduce((min, t) => (t < min ? t : min));
}

/**
 * Return the latest end time among nodes.
 */
function maxEndTime(
  nodes: (TranscriptNode | TranscriptNodeBase)[]
): Date | null {
  const times = nodes
    .map((n) => n.endTime)
    .filter((t): t is Date => t !== null);
  if (times.length === 0) return null;
  return times.reduce((max, t) => (t > max ? t : max));
}

/**
 * Sum total tokens across all nodes.
 */
function sumTokens(nodes: (TranscriptNode | TranscriptNodeBase)[]): number {
  return nodes.reduce((sum, n) => sum + n.totalTokens, 0);
}

// =============================================================================
// Node Creation
// =============================================================================

/**
 * Create an EventNode from an Event.
 */
function createEventNode(event: Event): EventNodeType {
  return {
    type: "event",
    event,
    startTime: getEventStartTime(event),
    endTime: getEventEndTime(event),
    totalTokens: getEventTokens(event),
  };
}

/**
 * Create an AgentNode with computed properties.
 */
function createAgentNode(
  id: string,
  name: string,
  source: AgentSource,
  content: (EventNodeType | AgentNodeType)[]
): AgentNodeType {
  return {
    type: "agent",
    id,
    name,
    source,
    content,
    startTime: minStartTime(content),
    endTime: maxEndTime(content),
    totalTokens: sumTokens(content),
  };
}

/**
 * Create a SectionNode with computed properties.
 */
function createSectionNode(
  section: "init" | "scoring",
  content: EventNodeType[]
): SectionNodeType {
  return {
    type: "section",
    section,
    content,
    startTime: minStartTime(content),
    endTime: maxEndTime(content),
    totalTokens: sumTokens(content),
  };
}

// =============================================================================
// Span Tree Building
// =============================================================================

/**
 * Build a span tree from a flat event list.
 *
 * Parses span_begin/span_end events to create hierarchical structure.
 * Events are associated with spans via their span_id field.
 */
function buildSpanTree(events: Event[]): TreeItem[] {
  const root: TreeItem[] = [];
  const spansById = new Map<string, SpanNode>();
  const spanStack: SpanNode[] = [];

  for (const event of events) {
    if (event.event === "span_begin") {
      const span: SpanNode = {
        id: event.id,
        name: event.name,
        type: event.type ?? undefined,
        parentId: event.parent_id,
        children: [],
      };
      spansById.set(span.id, span);

      // Determine where to place this span
      if (span.parentId && spansById.has(span.parentId)) {
        // Parent span exists - add as child
        spansById.get(span.parentId)!.children.push(span);
      } else if (spanStack.length > 0) {
        // No explicit parent but we have an open span - add to current span
        const currentSpan = spanStack[spanStack.length - 1];
        if (currentSpan) {
          currentSpan.children.push(span);
        }
      } else {
        // Top-level span
        root.push(span);
      }
      spanStack.push(span);
    } else if (event.event === "span_end") {
      // Pop the span stack when we see span_end
      if (spanStack.length > 0) {
        spanStack.pop();
      }
    } else {
      // Regular event - add to appropriate span based on span_id
      const spanId = (event as { span_id?: string | null }).span_id;

      if (spanId && spansById.has(spanId)) {
        spansById.get(spanId)!.children.push(event);
      } else if (spanStack.length > 0) {
        // No span_id but we have an open span - add to current span
        const currentSpan = spanStack[spanStack.length - 1];
        if (currentSpan) {
          currentSpan.children.push(event);
        }
      } else {
        // No span context - add to root
        root.push(event);
      }
    }
  }

  return root;
}

/**
 * Flatten a tree item recursively to get all events.
 */
function eventSequence(items: TreeItem[]): Event[] {
  const events: Event[] = [];
  for (const item of items) {
    if (isSpanNode(item)) {
      events.push(...eventSequence(item.children));
    } else {
      events.push(item);
    }
  }
  return events;
}

/**
 * Check if a span contains any ModelEvent (recursively).
 */
function containsModelEvents(span: SpanNode): boolean {
  for (const child of span.children) {
    if (isSpanNode(child)) {
      if (containsModelEvents(child)) {
        return true;
      }
    } else if (child.event === "model") {
      return true;
    }
  }
  return false;
}

// =============================================================================
// Node Building from Tree
// =============================================================================

/**
 * Convert an Event to an EventNode or AgentNode.
 *
 * Handles ToolEvents that spawn nested agents, recursively processing
 * nested events to detect further agent spawning.
 */
function eventToNode(event: Event): EventNodeType | AgentNodeType {
  if (event.event === "tool") {
    const agentName = event.agent;
    const nestedEvents = event.events as Event[] | undefined;

    if (agentName && nestedEvents && nestedEvents.length > 0) {
      // Recursively process nested events to handle nested tool agents
      const nestedContent: (EventNodeType | AgentNodeType)[] = nestedEvents.map(
        (e) => eventToNode(e)
      );

      return createAgentNode(
        `tool-agent-${event.id}`,
        agentName,
        { source: "tool", toolEvent: event },
        nestedContent
      );
    }
  }
  return createEventNode(event);
}

/**
 * Convert a tree item (SpanNode or Event) to an EventNode or AgentNode.
 */
function treeItemToNode(item: TreeItem): EventNodeType | AgentNodeType {
  if (isSpanNode(item)) {
    if (item.type === "agent") {
      return buildAgentFromSpan(item);
    } else {
      // Non-agent span - may be tool span with model events
      return buildAgentFromSpanGeneric(item);
    }
  } else {
    return eventToNode(item);
  }
}

/**
 * Build an AgentNode from a SpanNode with type='agent'.
 */
function buildAgentFromSpan(
  span: SpanNode,
  extraItems?: TreeItem[]
): AgentNodeType {
  const content: (EventNodeType | AgentNodeType)[] = [];

  // Add any extra items first (orphan events)
  if (extraItems) {
    for (const item of extraItems) {
      content.push(treeItemToNode(item));
    }
  }

  // Process span children
  for (const child of span.children) {
    content.push(treeItemToNode(child));
  }

  return createAgentNode(
    span.id,
    span.name,
    { source: "span", spanId: span.id },
    content
  );
}

/**
 * Build an AgentNode from a non-agent SpanNode.
 *
 * If the span is a tool span (type="tool") containing model events,
 * we treat it as a tool-spawned agent.
 */
function buildAgentFromSpanGeneric(span: SpanNode): AgentNodeType {
  const content: (EventNodeType | AgentNodeType)[] = [];

  for (const child of span.children) {
    content.push(treeItemToNode(child));
  }

  // Determine the source based on span type and content
  const source: AgentSource =
    span.type === "tool" && containsModelEvents(span)
      ? { source: "tool" }
      : { source: "span", spanId: span.id };

  return createAgentNode(span.id, span.name, source, content);
}

/**
 * Build a SectionNode from a SpanNode.
 *
 * Flattens any nested spans into a list of events.
 */
function buildSectionFromSpan(
  section: "init" | "scoring",
  span: SpanNode
): SectionNodeType {
  // Flatten the tree, extracting just the events
  const events = eventSequence(span.children);
  const content = events.map((e) => createEventNode(e));
  return createSectionNode(section, content);
}

/**
 * Build agent hierarchy from the solvers span.
 *
 * Looks for explicit agent spans (type='agent') within the solvers span.
 * If found, builds the agent tree from those spans. If not found, uses
 * the solvers span itself as the agent container.
 */
function buildAgentFromSolversSpan(
  solversSpan: SpanNode
): AgentNodeType | null {
  if (solversSpan.children.length === 0) {
    return null;
  }

  // Look for agent spans within solvers
  const agentSpans: SpanNode[] = [];
  const otherItems: TreeItem[] = [];

  for (const child of solversSpan.children) {
    if (isSpanNode(child) && child.type === "agent") {
      agentSpans.push(child);
    } else {
      otherItems.push(child);
    }
  }

  if (agentSpans.length > 0) {
    // Build from explicit agent spans
    const firstAgentSpan = agentSpans[0];
    if (agentSpans.length === 1 && firstAgentSpan) {
      return buildAgentFromSpan(firstAgentSpan, otherItems);
    } else {
      // Multiple agent spans - create root containing all
      const children: (EventNodeType | AgentNodeType)[] = agentSpans.map(
        (span) => buildAgentFromSpan(span)
      );
      // Add any orphan events at the start
      for (const item of otherItems) {
        children.unshift(treeItemToNode(item));
      }
      return createAgentNode(
        "root",
        "root",
        { source: "span", spanId: "root" },
        children
      );
    }
  } else {
    // No explicit agent spans - use solvers span itself as the agent container
    const content: (EventNodeType | AgentNodeType)[] = [];
    for (const item of solversSpan.children) {
      content.push(treeItemToNode(item));
    }
    return createAgentNode(
      solversSpan.id,
      solversSpan.name,
      { source: "span", spanId: solversSpan.id },
      content
    );
  }
}

/**
 * Build agent from a list of tree items when no explicit phase spans exist.
 *
 * Creates a synthetic "main" agent containing all tree items as content.
 */
function buildAgentFromTree(tree: TreeItem[]): AgentNodeType {
  const content: (EventNodeType | AgentNodeType)[] = [];

  for (const item of tree) {
    content.push(treeItemToNode(item));
  }

  return createAgentNode(
    "main",
    "main",
    { source: "span", spanId: "main" },
    content
  );
}

// =============================================================================
// Main Builder
// =============================================================================

/**
 * Build structured nodes from flat event list.
 *
 * Uses our span tree builder to parse span structure, then:
 * 1. Look for top-level spans: "init", "solvers", "scorers"
 * 2. If present, use them to partition events into sections
 * 3. If not present, treat the entire event stream as the agent
 *
 * Agent detection within the solvers section (or entire stream):
 * - Explicit agent spans (type='agent') -> AgentSourceSpan
 * - Tool spans/calls with model events -> AgentSourceTool
 */
export function buildTranscriptNodes(events: Event[]): TranscriptNodes {
  if (events.length === 0) {
    return {
      init: null,
      agent: null,
      scoring: null,
      startTime: null,
      endTime: null,
      totalTokens: 0,
    };
  }

  // Build span tree from events
  const tree = buildSpanTree(events);

  // Find top-level spans by name
  const topSpans = new Map<string, SpanNode>();
  for (const item of tree) {
    if (
      isSpanNode(item) &&
      (item.name === "init" ||
        item.name === "solvers" ||
        item.name === "scorers")
    ) {
      topSpans.set(item.name, item);
    }
  }

  // Check for explicit phase spans (init, solvers, or scorers)
  const hasPhaseSpans =
    topSpans.has("init") || topSpans.has("solvers") || topSpans.has("scorers");

  let initSection: SectionNodeType | null = null;
  let agentNode: AgentNodeType | null = null;
  let scoringSection: SectionNodeType | null = null;

  if (hasPhaseSpans) {
    // Use spans to partition events
    const initSpan = topSpans.get("init");
    const solversSpan = topSpans.get("solvers");
    const scorersSpan = topSpans.get("scorers");

    initSection = initSpan ? buildSectionFromSpan("init", initSpan) : null;
    agentNode = solversSpan ? buildAgentFromSolversSpan(solversSpan) : null;
    scoringSection = scorersSpan
      ? buildSectionFromSpan("scoring", scorersSpan)
      : null;
  } else {
    // No phase spans - treat entire tree as agent
    agentNode = buildAgentFromTree(tree);
  }

  // Compute root-level timing and tokens
  const sections: TranscriptNode[] = [];
  if (initSection) sections.push(initSection);
  if (agentNode) sections.push(agentNode);
  if (scoringSection) sections.push(scoringSection);

  return {
    init: initSection,
    agent: agentNode,
    scoring: scoringSection,
    startTime: minStartTime(sections),
    endTime: maxEndTime(sections),
    totalTokens: sumTokens(sections),
  };
}
