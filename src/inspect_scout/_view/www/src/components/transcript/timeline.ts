/**
 * Transcript nodes: hierarchical structure for visualization and scanning.
 *
 * Transforms flat event streams into a semantic tree with agent-centric interpretation.
 *
 * TypeScript port of Python's nodes.py, implementing our own span tree building
 * since we don't have access to inspect_ai's event_tree().
 */

import type { ChatMessage, Event } from "../../types/api-types";

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
  metadata?: Record<string, unknown>;
  children: TreeItem[];
  /** The original span_begin event, preserved for unrolling. */
  beginEvent: Event;
  /** The original span_end event (if any), preserved for unrolling. */
  endEvent?: Event;
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
 * Base interface for computed properties on all timeline nodes.
 */
interface TimelineNode {
  startTime: Date;
  endTime: Date;
  totalTokens: number;
}

/**
 * Wraps a single Event with computed timing and token properties.
 */
export interface TimelineEvent extends TimelineNode {
  type: "event";
  event: Event;
}

/**
 * A span of execution — agent, scorer, tool, or root.
 */
export interface TimelineSpan extends TimelineNode {
  type: "span";
  id: string;
  name: string;
  spanType: string | null;
  content: (TimelineEvent | TimelineSpan)[];
  branches: TimelineBranch[];
  description?: string;
  utility: boolean;
  outline?: Outline;
}

/**
 * A discarded alternative path from a branch point.
 */
export interface TimelineBranch extends TimelineNode {
  type: "branch";
  forkedAt: string;
  content: (TimelineEvent | TimelineSpan)[];
}

/**
 * A node in an agent's outline, referencing an event by UUID.
 */
export interface OutlineNode {
  event: string;
  children?: OutlineNode[];
}

/**
 * Hierarchical outline of events for an agent.
 */
export interface Outline {
  nodes: OutlineNode[];
}

/**
 * A named timeline view over a transcript.
 *
 * Multiple timelines allow different interpretations of the same event
 * stream — e.g. a default agent-centric view alongside an alternative
 * grouping or filtered view.
 */
export interface Timeline {
  name: string;
  description: string;
  root: TimelineSpan;
}

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
 * Every event has a required `timestamp` field.
 */
function getEventStartTime(event: Event): Date {
  const timestamp = (event as { timestamp?: string }).timestamp;
  const date = parseTimestamp(timestamp);
  if (!date) {
    throw new Error("Event missing required timestamp field");
  }
  return date;
}

/**
 * Get the end time for an event (completed if available, else timestamp).
 */
function getEventEndTime(event: Event): Date {
  const completed = (event as { completed?: string }).completed;
  if (completed) {
    const date = parseTimestamp(completed);
    if (date) return date;
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
      const cacheRead = usage.input_tokens_cache_read ?? 0;
      const cacheWrite = usage.input_tokens_cache_write ?? 0;
      const outputTokens = usage.output_tokens ?? 0;
      return inputTokens + cacheRead + cacheWrite + outputTokens;
    }
  }
  return 0;
}

/**
 * Return the earliest start time among nodes.
 * Requires at least one node (all nodes have non-null startTime).
 */
function minStartTime(nodes: TimelineNode[]): Date {
  const first = nodes[0];
  if (!first) {
    throw new Error("minStartTime requires at least one node");
  }
  return nodes.reduce(
    (min, n) => (n.startTime < min ? n.startTime : min),
    first.startTime
  );
}

/**
 * Return the latest end time among nodes.
 * Requires at least one node (all nodes have non-null endTime).
 */
function maxEndTime(nodes: TimelineNode[]): Date {
  const first = nodes[0];
  if (!first) {
    throw new Error("maxEndTime requires at least one node");
  }
  return nodes.reduce(
    (max, n) => (n.endTime > max ? n.endTime : max),
    first.endTime
  );
}

/**
 * Sum total tokens across all nodes.
 */
function sumTokens(nodes: TimelineNode[]): number {
  return nodes.reduce((sum, n) => sum + n.totalTokens, 0);
}

// =============================================================================
// Node Creation
// =============================================================================

/** Sentinel date for nodes with no content (e.g. empty spans). */
const EPOCH = new Date(0);

/**
 * Create a TimelineEvent from an Event.
 */
function createTimelineEvent(event: Event): TimelineEvent {
  return {
    type: "event",
    event,
    startTime: getEventStartTime(event),
    endTime: getEventEndTime(event),
    totalTokens: getEventTokens(event),
  };
}

/**
 * Create a TimelineSpan with computed properties.
 */
function createTimelineSpan(
  id: string,
  name: string,
  spanType: string | null,
  content: (TimelineEvent | TimelineSpan)[],
  utility: boolean = false,
  branches: TimelineBranch[] = [],
  description?: string
): TimelineSpan {
  return {
    type: "span",
    id,
    name: name.toLowerCase(),
    spanType,
    content,
    branches,
    description,
    utility,
    startTime: content.length > 0 ? minStartTime(content) : EPOCH,
    endTime: content.length > 0 ? maxEndTime(content) : EPOCH,
    totalTokens: sumTokens(content),
  };
}

/**
 * Create a TimelineBranch with computed properties.
 */
function createBranch(
  forkedAt: string,
  content: (TimelineEvent | TimelineSpan)[]
): TimelineBranch {
  return {
    type: "branch",
    forkedAt,
    content,
    startTime: content.length > 0 ? minStartTime(content) : EPOCH,
    endTime: content.length > 0 ? maxEndTime(content) : EPOCH,
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
        metadata: event.metadata ?? undefined,
        children: [],
        beginEvent: event,
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
      // Store end event on the span and pop the stack
      const endSpan = spansById.get(event.id);
      if (endSpan) {
        endSpan.endEvent = event;
      }
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
 * Convert an Event to a TimelineEvent or TimelineSpan.
 *
 * Handles ToolEvents that spawn nested agents, recursively processing
 * nested events to detect further agent spawning.
 */
function eventToNode(event: Event): TimelineEvent | TimelineSpan {
  if (event.event === "tool") {
    const agentName = event.agent;
    const nestedEvents = event.events as Event[] | undefined;

    if (agentName && nestedEvents && nestedEvents.length > 0) {
      // Recursively process nested events to handle nested tool agents
      const nestedContent: (TimelineEvent | TimelineSpan)[] = nestedEvents.map(
        (e) => eventToNode(e)
      );

      return createTimelineSpan(
        `tool-agent-${event.id}`,
        agentName,
        "agent",
        nestedContent
      );
    }
  }
  return createTimelineEvent(event);
}

/**
 * Check if a SpanNode represents an agent trajectory.
 *
 * Agent spans are:
 * - Explicit agent spans (type="agent")
 * - Solver spans (type="solver")
 * - Tool spans containing model events (tool-spawned agents)
 */
function isAgentSpan(span: SpanNode): boolean {
  if (span.type === "agent" || span.type === "solver") {
    return true;
  }
  if (span.type === "tool" && containsModelEvents(span)) {
    return true;
  }
  return false;
}

/**
 * Convert a tree item (SpanNode or Event) to a TimelineEvent or TimelineSpan.
 */
function treeItemToNode(
  item: TreeItem,
  hasExplicitBranches: boolean
): TimelineEvent | TimelineSpan {
  if (isSpanNode(item)) {
    if (item.type === "agent" || item.type === "solver") {
      return buildSpanFromAgentSpan(item, hasExplicitBranches);
    } else {
      // Non-agent span - may be tool span with model events
      return buildSpanFromGenericSpan(item, hasExplicitBranches);
    }
  } else {
    return eventToNode(item);
  }
}

/**
 * Build a TimelineSpan from a SpanNode with type='agent'.
 */
function buildSpanFromAgentSpan(
  span: SpanNode,
  hasExplicitBranches: boolean,
  extraItems?: TreeItem[]
): TimelineSpan {
  const content: (TimelineEvent | TimelineSpan)[] = [];

  // Add any extra items first (orphan events)
  if (extraItems) {
    for (const item of extraItems) {
      if (isSpanNode(item) && !isAgentSpan(item)) {
        unrollSpan(item, content, hasExplicitBranches);
      } else {
        content.push(treeItemToNode(item, hasExplicitBranches));
      }
    }
  }

  // Process span children with branch awareness
  const [childContent, branches] = processChildren(
    span.children,
    hasExplicitBranches
  );
  content.push(...childContent);

  const description =
    typeof span.metadata?.description === "string"
      ? span.metadata.description
      : undefined;

  return createTimelineSpan(
    span.id,
    span.name,
    "agent",
    content,
    false,
    branches,
    description
  );
}

/**
 * Build a TimelineSpan from a non-agent SpanNode.
 *
 * If the span is a tool span (type="tool") containing model events,
 * we treat it as a tool-spawned agent (spanType="agent").
 */
function buildSpanFromGenericSpan(
  span: SpanNode,
  hasExplicitBranches: boolean
): TimelineSpan {
  const [content, branches] = processChildren(
    span.children,
    hasExplicitBranches
  );

  // Determine the spanType based on span type and content
  const spanType: string | null =
    span.type === "tool" && containsModelEvents(span)
      ? "agent"
      : (span.type ?? null);

  return createTimelineSpan(
    span.id,
    span.name,
    spanType,
    content,
    false,
    branches
  );
}

/**
 * Build agent hierarchy from the solvers span.
 *
 * Looks for explicit agent spans (type='agent') within the solvers span.
 * If found, builds the agent tree from those spans. If not found, uses
 * the solvers span itself as the agent container.
 */
function buildAgentFromSolversSpan(
  solversSpan: SpanNode,
  hasExplicitBranches: boolean
): TimelineSpan | null {
  if (solversSpan.children.length === 0) {
    return null;
  }

  // Look for agent spans within solvers
  const agentSpans: SpanNode[] = [];
  const otherItems: TreeItem[] = [];

  for (const child of solversSpan.children) {
    if (isSpanNode(child) && isAgentSpan(child)) {
      agentSpans.push(child);
    } else {
      otherItems.push(child);
    }
  }

  if (agentSpans.length > 0) {
    // Build from explicit agent spans
    const firstAgentSpan = agentSpans[0];
    if (agentSpans.length === 1 && firstAgentSpan) {
      return buildSpanFromAgentSpan(
        firstAgentSpan,
        hasExplicitBranches,
        otherItems
      );
    } else {
      // Multiple agent spans - create root containing all
      const children: (TimelineEvent | TimelineSpan)[] = agentSpans.map(
        (span) => buildSpanFromAgentSpan(span, hasExplicitBranches)
      );
      // Add any orphan events at the start
      for (const item of otherItems) {
        if (isSpanNode(item) && !isAgentSpan(item)) {
          const orphanContent: (TimelineEvent | TimelineSpan)[] = [];
          unrollSpan(item, orphanContent, hasExplicitBranches);
          for (let i = orphanContent.length - 1; i >= 0; i--) {
            children.unshift(orphanContent[i]!);
          }
        } else {
          children.unshift(treeItemToNode(item, hasExplicitBranches));
        }
      }
      return createTimelineSpan("root", "root", "agent", children);
    }
  } else {
    // No explicit agent spans - use solvers span itself as the agent container
    const [content, branches] = processChildren(
      solversSpan.children,
      hasExplicitBranches
    );
    return createTimelineSpan(
      solversSpan.id,
      solversSpan.name,
      "agent",
      content,
      false,
      branches
    );
  }
}

/**
 * Build agent from a list of tree items when no explicit phase spans exist.
 *
 * Creates a synthetic "main" agent containing all tree items as content.
 */
function buildAgentFromTree(
  tree: TreeItem[],
  hasExplicitBranches: boolean
): TimelineSpan {
  const [content, branches] = processChildren(tree, hasExplicitBranches);

  return createTimelineSpan("main", "main", "agent", content, false, branches);
}

/**
 * Dissolve a non-agent span, emitting its begin/end as regular events.
 *
 * Recursively unrolls nested non-agent spans while preserving any
 * nested agent spans as TimelineSpan nodes.
 */
function unrollSpan(
  span: SpanNode,
  into: (TimelineEvent | TimelineSpan)[],
  hasExplicitBranches: boolean
): void {
  // Emit span begin event
  into.push(createTimelineEvent(span.beginEvent));

  // Process children: recurse into non-agent spans, keep agent spans
  for (const child of span.children) {
    if (isSpanNode(child)) {
      if (isAgentSpan(child)) {
        const node = treeItemToNode(child, hasExplicitBranches);
        if (node.type === "span" && node.content.length === 0) {
          // skip empty agent spans
        } else {
          into.push(node);
        }
      } else {
        unrollSpan(child, into, hasExplicitBranches);
      }
    } else {
      into.push(eventToNode(child));
    }
  }

  // Emit span end event
  if (span.endEvent) {
    into.push(createTimelineEvent(span.endEvent));
  }
}

// =============================================================================
// TimelineBranch Processing
// =============================================================================

/**
 * Process a span's children with branch awareness.
 *
 * When explicit branches are active, collects adjacent type="branch" SpanNode
 * runs and builds TimelineBranch objects from them. Otherwise, standard processing.
 */
function processChildren(
  children: TreeItem[],
  hasExplicitBranches: boolean
): [(TimelineEvent | TimelineSpan)[], TimelineBranch[]] {
  if (!hasExplicitBranches) {
    // Standard processing - no branch detection at build time
    const content: (TimelineEvent | TimelineSpan)[] = [];
    for (const item of children) {
      if (isSpanNode(item) && !isAgentSpan(item)) {
        // Unroll: dissolve non-agent span wrapper into parent,
        // emitting begin/end as events and preserving nested agents
        unrollSpan(item, content, hasExplicitBranches);
      } else {
        const node = treeItemToNode(item, hasExplicitBranches);
        // Skip empty spans (e.g. agent spans with no nested events)
        if (node.type === "span" && node.content.length === 0) continue;
        content.push(node);
      }
    }
    return [content, []];
  }

  // Explicit branch mode: collect branch spans and build TimelineBranch objects
  const content: (TimelineEvent | TimelineSpan)[] = [];
  const branches: TimelineBranch[] = [];
  let branchRun: SpanNode[] = [];

  function flushBranchRun(
    run: SpanNode[],
    parentContent: (TimelineEvent | TimelineSpan)[]
  ): TimelineBranch[] {
    const result: TimelineBranch[] = [];
    for (const span of run) {
      const branchContent: (TimelineEvent | TimelineSpan)[] = [];
      for (const child of span.children) {
        if (isSpanNode(child) && !isAgentSpan(child)) {
          unrollSpan(child, branchContent, hasExplicitBranches);
        } else {
          const node = treeItemToNode(child, hasExplicitBranches);
          if (node.type === "span" && node.content.length === 0) continue;
          branchContent.push(node);
        }
      }
      const branchInput = getBranchInput(branchContent);
      const forkedAt =
        branchInput !== null ? findForkedAt(parentContent, branchInput) : "";
      result.push(createBranch(forkedAt, branchContent));
    }
    return result;
  }

  for (const item of children) {
    if (isSpanNode(item) && item.type === "branch") {
      branchRun.push(item);
    } else {
      if (branchRun.length > 0) {
        branches.push(...flushBranchRun(branchRun, content));
        branchRun = [];
      }
      if (isSpanNode(item) && !isAgentSpan(item)) {
        // Unroll: dissolve non-agent span wrapper into parent,
        // emitting begin/end as events and preserving nested agents
        unrollSpan(item, content, hasExplicitBranches);
      } else {
        const node = treeItemToNode(item, hasExplicitBranches);
        if (node.type === "span" && node.content.length === 0) continue;
        content.push(node);
      }
    }
  }

  if (branchRun.length > 0) {
    branches.push(...flushBranchRun(branchRun, content));
  }

  return [content, branches];
}

/**
 * Determine the fork point by matching the last shared input message.
 */
function findForkedAt(
  agentContent: (TimelineEvent | TimelineSpan)[],
  branchInput: ChatMessage[]
): string {
  if (branchInput.length === 0) return "";

  const lastMsg = branchInput[branchInput.length - 1];
  if (!lastMsg) return "";

  if (lastMsg.role === "tool") {
    // Match tool_call_id to a ToolEvent.id
    const toolCallId = lastMsg.tool_call_id;
    if (toolCallId) {
      for (const item of agentContent) {
        if (
          item.type === "event" &&
          item.event.event === "tool" &&
          item.event.id === toolCallId
        ) {
          return item.event.uuid ?? "";
        }
      }
    }
    return "";
  }

  if (lastMsg.role === "assistant") {
    // Match message id to ModelEvent.output.choices[0].message.id
    const msgId = lastMsg.id;
    if (msgId) {
      for (const item of agentContent) {
        if (item.type === "event" && item.event.event === "model") {
          const outMsg = item.event.output?.choices?.[0]?.message;
          if (outMsg && outMsg.id === msgId) {
            return item.event.uuid ?? "";
          }
        }
      }
    }
    // Fallback: compare content
    const msgContent = lastMsg.content;
    if (msgContent) {
      for (const item of agentContent) {
        if (item.type === "event" && item.event.event === "model") {
          const outMsg = item.event.output?.choices?.[0]?.message;
          if (outMsg && outMsg.content === msgContent) {
            return item.event.uuid ?? "";
          }
        }
      }
    }
    return "";
  }

  // ChatMessageUser / ChatMessageSystem - fork at beginning
  return "";
}

/**
 * Extract the input from the first ModelEvent in branch content.
 */
function getBranchInput(
  content: (TimelineEvent | TimelineSpan)[]
): ChatMessage[] | null {
  for (const item of content) {
    if (item.type === "event" && item.event.event === "model") {
      return item.event.input ?? null;
    }
  }
  return null;
}

// =============================================================================
// TimelineBranch Auto-Detection
// =============================================================================

/**
 * Compute a fingerprint for a single ChatMessage.
 *
 * Serializes role + content, ignoring auto-generated fields.
 * Uses full string as fingerprint (no crypto hash needed in TS).
 */
function messageFingerprint(
  msg: ChatMessage,
  cache?: WeakMap<ChatMessage, string>
): string {
  if (cache) {
    const cached = cache.get(msg);
    if (cached !== undefined) return cached;
  }

  const role = msg.role;
  let serialized: string;
  if (typeof msg.content === "string") {
    serialized = msg.content;
  } else {
    serialized = JSON.stringify(msg.content);
  }
  const result = `${role}:${serialized}`;

  if (cache) {
    cache.set(msg, result);
  }
  return result;
}

/**
 * Compute a fingerprint for a sequence of input messages.
 */
function inputFingerprint(
  messages: ChatMessage[],
  cache?: WeakMap<ChatMessage, string>
): string {
  return messages.map((m) => messageFingerprint(m, cache)).join("|");
}

/**
 * Detect re-rolled ModelEvents with identical inputs and create branches.
 *
 * CompactionEvents act as hard boundaries: fingerprint grouping is done
 * independently within each region separated by compaction events, so
 * re-rolls are never matched across a compaction boundary.
 *
 * Mutates span in-place.
 */
function detectAutoBranches(span: TimelineSpan): void {
  // Cache message fingerprints by object identity to avoid re-serializing
  const fpCache = new WeakMap<ChatMessage, string>();

  // Split content into regions at compaction boundaries
  const regions: [number, number][] = [];
  let regionStart = 0;
  for (let i = 0; i < span.content.length; i++) {
    const item = span.content[i];
    if (item && item.type === "event" && item.event.event === "compaction") {
      regions.push([regionStart, i]);
      regionStart = i + 1;
    }
  }
  regions.push([regionStart, span.content.length]);

  // Collect branch ranges across all regions
  const branchRanges: [number, number, ChatMessage[]][] = [];

  for (const [rStart, rEnd] of regions) {
    // Find ModelEvent indices and their fingerprints within this region
    const modelIndices: [number, string][] = [];
    for (let i = rStart; i < rEnd; i++) {
      const item = span.content[i];
      if (item && item.type === "event" && item.event.event === "model") {
        const inputMsgs = item.event.input;
        if (!inputMsgs || inputMsgs.length === 0) continue;
        const fp = inputFingerprint(inputMsgs, fpCache);
        modelIndices.push([i, fp]);
      }
    }

    // Group by fingerprint within this region
    const fingerprintGroups = new Map<string, number[]>();
    for (const [idx, fp] of modelIndices) {
      const group = fingerprintGroups.get(fp);
      if (group) {
        group.push(idx);
      } else {
        fingerprintGroups.set(fp, [idx]);
      }
    }

    // Only process groups with duplicates
    for (const [, indices] of fingerprintGroups) {
      if (indices.length <= 1) continue;

      const firstItem = span.content[indices[0]!];
      if (
        !firstItem ||
        firstItem.type !== "event" ||
        firstItem.event.event !== "model"
      ) {
        continue;
      }
      const sharedInput = firstItem.event.input ?? [];

      for (let i = 0; i < indices.length - 1; i++) {
        const branchStart = indices[i]!;
        const nextReroll = indices[i + 1]!;
        branchRanges.push([branchStart, nextReroll, sharedInput]);
      }
    }
  }

  if (branchRanges.length === 0) return;

  // Sort by start index descending so we can remove from the end first
  branchRanges.sort((a, b) => b[0] - a[0]);

  for (const [start, end, sharedInput] of branchRanges) {
    const branchContent = span.content.slice(start, end);
    const forkedAt = findForkedAt(span.content, sharedInput);
    span.branches.push(createBranch(forkedAt, branchContent));
    span.content.splice(start, end - start);
  }

  // Reverse branches so they're in original order
  span.branches.reverse();

  // Recompute totalTokens since content was modified
  span.totalTokens = sumTokens(span.content);
}

/**
 * Recursively detect branches in the span tree.
 *
 * Skips root since _classify_spans already ran detectAutoBranches on it
 * before branch classification.
 */
function classifyBranches(
  span: TimelineSpan,
  hasExplicitBranches: boolean,
  isRoot: boolean = true
): void {
  if (!hasExplicitBranches && !isRoot) {
    detectAutoBranches(span);
  }

  // Recurse into child spans in content
  for (const item of span.content) {
    if (item.type === "span") {
      classifyBranches(item, hasExplicitBranches, false);
    }
  }

  // Recurse into spans within branches
  for (const branch of span.branches) {
    for (const item of branch.content) {
      if (item.type === "span") {
        classifyBranches(item, hasExplicitBranches, false);
      }
    }
  }

  // Recompute totalTokens since child spans may have changed
  span.totalTokens = sumTokens(span.content);
}

// =============================================================================
// Utility Agent Classification
// =============================================================================

/**
 * Extract system prompt from the first ModelEvent in span's direct content.
 */
function getSystemPrompt(span: TimelineSpan): string | null {
  for (const item of span.content) {
    if (item.type === "event" && item.event.event === "model") {
      const input = item.event.input;
      if (input) {
        for (const msg of input) {
          if (msg.role === "system") {
            if (typeof msg.content === "string") {
              return msg.content;
            }
            if (Array.isArray(msg.content)) {
              const parts: string[] = [];
              for (const c of msg.content) {
                if ("text" in c && typeof c.text === "string") {
                  parts.push(c.text);
                }
              }
              return parts.length > 0 ? parts.join("\n") : null;
            }
          }
        }
      }
      return null; // ModelEvent found but no system message
    }
  }
  return null; // No ModelEvent found
}

/**
 * Check if span has a single turn or single tool-calling turn.
 *
 * A single turn is 1 ModelEvent with no ToolEvents.
 * A single tool-calling turn is 2 ModelEvents with a ToolEvent between them.
 */
function isSingleTurn(span: TimelineSpan): boolean {
  // Collect direct events (not child spans) with their types
  const directEvents: string[] = [];
  for (const item of span.content) {
    if (item.type === "event") {
      if (item.event.event === "model") {
        directEvents.push("model");
      } else if (item.event.event === "tool") {
        directEvents.push("tool");
      }
    }
  }

  const modelCount = directEvents.filter((e) => e === "model").length;
  const toolCount = directEvents.filter((e) => e === "tool").length;

  // Single turn: exactly 1 model event
  if (modelCount === 1) {
    return true;
  }

  // Single tool-calling turn: 2 model events with tool event(s) between
  if (modelCount === 2 && toolCount >= 1) {
    const firstModel = directEvents.indexOf("model");
    const secondModel = directEvents.lastIndexOf("model");
    const between = directEvents.slice(firstModel + 1, secondModel);
    return between.includes("tool");
  }

  return false;
}

/**
 * Classify utility agents in the tree via post-processing.
 *
 * An agent is utility if it has a single turn (or single tool-calling turn)
 * and a different system prompt than its parent.
 */
function classifyUtilityAgents(
  node: TimelineSpan,
  parentSystemPrompt: string | null = null
): void {
  const agentSystemPrompt = getSystemPrompt(node);

  // Classify this node (root agent is never utility)
  if (parentSystemPrompt !== null && agentSystemPrompt !== null) {
    if (agentSystemPrompt !== parentSystemPrompt && isSingleTurn(node)) {
      node.utility = true;
    }
  }

  // Recurse into child spans
  const effectivePrompt = agentSystemPrompt ?? parentSystemPrompt;
  for (const item of node.content) {
    if (item.type === "span") {
      classifyUtilityAgents(item, effectivePrompt);
    }
  }
}

// =============================================================================
// Main Builder
// =============================================================================

/**
 * Build a Timeline from a flat event list.
 *
 * Transforms a flat event stream into a hierarchical Timeline tree
 * with agent-centric interpretation. The pipeline has two phases:
 *
 * **Phase 1 — Structure extraction:**
 *
 * Parses span_begin/span_end events into a tree, then looks for
 * top-level phase spans ("init", "solvers", "scorers"):
 * - If present, partitions events into init (setup), agent (solvers),
 *   and scoring sections.
 * - If absent, treats the entire event stream as the agent.
 *
 * **Phase 2 — Agent classification:**
 *
 * Within the agent section, spans are classified as agents or unrolled:
 * - type="agent"                → TimelineSpan (spanType="agent")
 * - type="solver"               → TimelineSpan (spanType="agent")
 * - type="tool" + ModelEvents   → TimelineSpan (spanType="agent")
 * - ToolEvent with agent field  → TimelineSpan (spanType="agent")
 * - type="tool" (no models)     → Unrolled into parent
 * - Any other span type         → Unrolled into parent
 *
 * "Unrolled" means the span wrapper is removed and its child events
 * dissolve into the parent's content list.
 *
 * **Phase 3 — Post-processing passes:**
 * - Auto-branch detection (re-rolled ModelEvents with identical inputs)
 * - Utility agent classification (single-turn, different system prompt)
 * - Recursive branch classification
 */
export function buildTimeline(events: Event[]): Timeline {
  if (events.length === 0) {
    return {
      name: "Default",
      description: "",
      root: createTimelineSpan("root", "main", null, []),
    };
  }

  // Detect explicit branches globally
  const hasExplicitBranches = events.some(
    (e) => e.event === "span_begin" && e.type === "branch"
  );

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

  let root: TimelineSpan;

  if (hasPhaseSpans) {
    // Use spans to partition events
    const initSpan = topSpans.get("init");
    const solversSpan = topSpans.get("solvers");
    const scorersSpan = topSpans.get("scorers");

    // Build init span
    let initSpanObj: TimelineSpan | null = null;
    if (initSpan) {
      const initContent = eventSequence(initSpan.children).map((e) =>
        createTimelineEvent(e)
      );
      if (initContent.length > 0) {
        initSpanObj = createTimelineSpan(
          initSpan.id,
          "init",
          "init",
          initContent
        );
      }
    }

    // Build agent node from solvers
    const agentNode = solversSpan
      ? buildAgentFromSolversSpan(solversSpan, hasExplicitBranches)
      : null;

    // Build scoring span
    let scoringSpan: TimelineSpan | null = null;
    if (scorersSpan) {
      const scoringContent = eventSequence(scorersSpan.children).map((e) =>
        createTimelineEvent(e)
      );
      if (scoringContent.length > 0) {
        scoringSpan = createTimelineSpan(
          scorersSpan.id,
          "scoring",
          "scorers",
          scoringContent
        );
      }
    }

    if (agentNode) {
      if (!hasExplicitBranches) detectAutoBranches(agentNode);
      classifyUtilityAgents(agentNode);
      classifyBranches(agentNode, hasExplicitBranches);

      // Prepend init span to agent content
      if (initSpanObj) {
        agentNode.content = [initSpanObj, ...agentNode.content];
        // Recompute timing
        agentNode.startTime = minStartTime(agentNode.content);
        agentNode.endTime = maxEndTime(agentNode.content);
        agentNode.totalTokens = sumTokens(agentNode.content);
      }

      // Append scoring as a child span
      if (scoringSpan) {
        agentNode.content.push(scoringSpan);
        agentNode.endTime = maxEndTime(agentNode.content);
        agentNode.totalTokens = sumTokens(agentNode.content);
      }

      root = agentNode;
    } else {
      // No solvers span — build root from init + scoring
      const rootContent: (TimelineEvent | TimelineSpan)[] = [];
      if (initSpanObj) {
        rootContent.push(initSpanObj);
      }
      if (scoringSpan) {
        rootContent.push(scoringSpan);
      }
      root = createTimelineSpan("root", "root", null, rootContent);
    }
  } else {
    // No phase spans - treat entire tree as agent
    root = buildAgentFromTree(tree, hasExplicitBranches);
    if (!hasExplicitBranches) detectAutoBranches(root);
    classifyUtilityAgents(root);
    classifyBranches(root, hasExplicitBranches);
  }

  return { name: "Default", description: "", root };
}
