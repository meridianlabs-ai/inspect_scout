/**
 * Transcript nodes: hierarchical structure for visualization and scanning.
 *
 * Transforms flat event streams into a semantic tree with agent-centric interpretation
 * and phase separation (init/agent/scoring).
 *
 * TypeScript port of Python's nodes.py, implementing our own span tree building
 * since we don't have access to inspect_ai's event_tree().
 */

import type { ChatMessage, Event, ToolEvent } from "../../types/api-types";

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
export interface EventNode extends TranscriptNodeBase {
  type: "event";
  event: Event;
}

/**
 * Represents an agent with nested content (events and child agents).
 */
export interface AgentNode extends TranscriptNodeBase {
  type: "agent";
  id: string;
  name: string;
  source: AgentSource;
  content: (EventNode | AgentNode)[];
  branches: Branch[];
  taskDescription?: string;
  utility: boolean;
  outline?: Outline;
}

/**
 * A discarded alternative path from a branch point.
 */
export interface Branch extends TranscriptNodeBase {
  type: "branch";
  forkedAt: string;
  content: (EventNode | AgentNode)[];
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
 * Section node for init or scoring phases (EventNodes only).
 */
export interface SectionNode extends TranscriptNodeBase {
  type: "section";
  section: "init" | "scoring";
  content: EventNode[];
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
  transcript: TranscriptNodes;
}

/**
 * Root container for transcript node hierarchy.
 */
export interface TranscriptNodes {
  init: SectionNode | null;
  agent: AgentNode | null;
  scoring: SectionNode | null;
  startTime: Date | null;
  endTime: Date | null;
  totalTokens: number;
}

export type TranscriptNode = EventNode | AgentNode | SectionNode;

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
function createEventNode(event: Event): EventNode {
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
  content: (EventNode | AgentNode)[],
  utility: boolean = false,
  branches: Branch[] = []
): AgentNode {
  return {
    type: "agent",
    id,
    name,
    source,
    content,
    branches,
    utility,
    startTime: minStartTime(content),
    endTime: maxEndTime(content),
    totalTokens: sumTokens(content),
  };
}

/**
 * Create a Branch with computed properties.
 */
function createBranch(
  forkedAt: string,
  content: (EventNode | AgentNode)[]
): Branch {
  return {
    type: "branch",
    forkedAt,
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
  content: EventNode[]
): SectionNode {
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
function eventToNode(event: Event): EventNode | AgentNode {
  if (event.event === "tool") {
    const agentName = event.agent;
    const nestedEvents = event.events as Event[] | undefined;

    if (agentName && nestedEvents && nestedEvents.length > 0) {
      // Recursively process nested events to handle nested tool agents
      const nestedContent: (EventNode | AgentNode)[] = nestedEvents.map((e) =>
        eventToNode(e)
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
function treeItemToNode(
  item: TreeItem,
  hasExplicitBranches: boolean
): EventNode | AgentNode {
  if (isSpanNode(item)) {
    if (item.type === "agent") {
      return buildAgentFromSpan(item, hasExplicitBranches);
    } else {
      // Non-agent span - may be tool span with model events
      return buildAgentFromSpanGeneric(item, hasExplicitBranches);
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
  hasExplicitBranches: boolean,
  extraItems?: TreeItem[]
): AgentNode {
  const content: (EventNode | AgentNode)[] = [];

  // Add any extra items first (orphan events)
  if (extraItems) {
    for (const item of extraItems) {
      content.push(treeItemToNode(item, hasExplicitBranches));
    }
  }

  // Process span children with branch awareness
  const [childContent, branches] = processChildren(
    span.children,
    hasExplicitBranches
  );
  content.push(...childContent);

  return createAgentNode(
    span.id,
    span.name,
    { source: "span", spanId: span.id },
    content,
    false,
    branches
  );
}

/**
 * Build an AgentNode from a non-agent SpanNode.
 *
 * If the span is a tool span (type="tool") containing model events,
 * we treat it as a tool-spawned agent.
 */
function buildAgentFromSpanGeneric(
  span: SpanNode,
  hasExplicitBranches: boolean
): AgentNode {
  const [content, branches] = processChildren(
    span.children,
    hasExplicitBranches
  );

  // Determine the source based on span type and content
  const source: AgentSource =
    span.type === "tool" && containsModelEvents(span)
      ? { source: "tool" }
      : { source: "span", spanId: span.id };

  return createAgentNode(span.id, span.name, source, content, false, branches);
}

/**
 * Build a SectionNode from a SpanNode.
 *
 * Flattens any nested spans into a list of events.
 */
function buildSectionFromSpan(
  section: "init" | "scoring",
  span: SpanNode
): SectionNode {
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
  solversSpan: SpanNode,
  hasExplicitBranches: boolean
): AgentNode | null {
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
      return buildAgentFromSpan(
        firstAgentSpan,
        hasExplicitBranches,
        otherItems
      );
    } else {
      // Multiple agent spans - create root containing all
      const children: (EventNode | AgentNode)[] = agentSpans.map((span) =>
        buildAgentFromSpan(span, hasExplicitBranches)
      );
      // Add any orphan events at the start
      for (const item of otherItems) {
        children.unshift(treeItemToNode(item, hasExplicitBranches));
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
    const [content, branches] = processChildren(
      solversSpan.children,
      hasExplicitBranches
    );
    return createAgentNode(
      solversSpan.id,
      solversSpan.name,
      { source: "span", spanId: solversSpan.id },
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
): AgentNode {
  const [content, branches] = processChildren(tree, hasExplicitBranches);

  return createAgentNode(
    "main",
    "main",
    { source: "span", spanId: "main" },
    content,
    false,
    branches
  );
}

// =============================================================================
// Branch Processing
// =============================================================================

/**
 * Process a span's children with branch awareness.
 *
 * When explicit branches are active, collects adjacent type="branch" SpanNode
 * runs and builds Branch objects from them. Otherwise, standard processing.
 */
function processChildren(
  children: TreeItem[],
  hasExplicitBranches: boolean
): [(EventNode | AgentNode)[], Branch[]] {
  if (!hasExplicitBranches) {
    // Standard processing - no branch detection at build time
    const content: (EventNode | AgentNode)[] = [];
    for (const item of children) {
      content.push(treeItemToNode(item, hasExplicitBranches));
    }
    return [content, []];
  }

  // Explicit branch mode: collect branch spans and build Branch objects
  const content: (EventNode | AgentNode)[] = [];
  const branches: Branch[] = [];
  let branchRun: SpanNode[] = [];

  function flushBranchRun(
    run: SpanNode[],
    parentContent: (EventNode | AgentNode)[]
  ): Branch[] {
    const result: Branch[] = [];
    for (const span of run) {
      const branchContent: (EventNode | AgentNode)[] = [];
      for (const child of span.children) {
        branchContent.push(treeItemToNode(child, hasExplicitBranches));
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
      content.push(treeItemToNode(item, hasExplicitBranches));
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
  agentContent: (EventNode | AgentNode)[],
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
  content: (EventNode | AgentNode)[]
): ChatMessage[] | null {
  for (const item of content) {
    if (item.type === "event" && item.event.event === "model") {
      return item.event.input ?? null;
    }
  }
  return null;
}

// =============================================================================
// Branch Auto-Detection
// =============================================================================

/**
 * Compute a fingerprint for a single ChatMessage.
 *
 * Serializes role + content, ignoring auto-generated fields.
 * Uses full string as fingerprint (no crypto hash needed in TS).
 */
function messageFingerprint(msg: ChatMessage): string {
  const role = msg.role;
  let serialized: string;
  if (typeof msg.content === "string") {
    serialized = msg.content;
  } else {
    serialized = JSON.stringify(msg.content);
  }
  return `${role}:${serialized}`;
}

/**
 * Compute a fingerprint for a sequence of input messages.
 */
function inputFingerprint(messages: ChatMessage[]): string {
  return messages.map((m) => messageFingerprint(m)).join("|");
}

/**
 * Detect re-rolled ModelEvents with identical inputs and create branches.
 *
 * Mutates agent in-place.
 */
function detectAutoBranches(agent: AgentNode): void {
  // Find ModelEvent indices and their fingerprints (skip empty inputs)
  const modelIndices: [number, string][] = [];
  for (let i = 0; i < agent.content.length; i++) {
    const item = agent.content[i];
    if (item && item.type === "event" && item.event.event === "model") {
      const inputMsgs = item.event.input;
      if (!inputMsgs || inputMsgs.length === 0) continue;
      const fp = inputFingerprint(inputMsgs);
      modelIndices.push([i, fp]);
    }
  }

  // Group by fingerprint
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
  const branchRanges: [number, number, ChatMessage[]][] = [];

  for (const [, indices] of fingerprintGroups) {
    if (indices.length <= 1) continue;

    // Get the shared input from the first one
    const firstItem = agent.content[indices[0]!];
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

  if (branchRanges.length === 0) return;

  // Sort by start index descending so we can remove from the end first
  branchRanges.sort((a, b) => b[0] - a[0]);

  for (const [start, end, sharedInput] of branchRanges) {
    const branchContent = agent.content.slice(start, end);
    const forkedAt = findForkedAt(agent.content, sharedInput);
    agent.branches.push(createBranch(forkedAt, branchContent));
    agent.content.splice(start, end - start);
  }

  // Reverse branches so they're in original order
  agent.branches.reverse();
}

/**
 * Recursively detect branches in the agent tree.
 */
function classifyBranches(
  agent: AgentNode,
  hasExplicitBranches: boolean
): void {
  if (!hasExplicitBranches) {
    detectAutoBranches(agent);
  }

  // Recurse into child agents in content
  for (const item of agent.content) {
    if (item.type === "agent") {
      classifyBranches(item, hasExplicitBranches);
    }
  }

  // Recurse into agents within branches
  for (const branch of agent.branches) {
    for (const item of branch.content) {
      if (item.type === "agent") {
        classifyBranches(item, hasExplicitBranches);
      }
    }
  }
}

// =============================================================================
// Utility Agent Classification
// =============================================================================

/**
 * Extract system prompt from the first ModelEvent in agent's direct content.
 */
function getSystemPrompt(agent: AgentNode): string | null {
  for (const item of agent.content) {
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
 * Check if agent has a single turn or single tool-calling turn.
 *
 * A single turn is 1 ModelEvent with no ToolEvents.
 * A single tool-calling turn is 2 ModelEvents with a ToolEvent between them.
 */
function isSingleTurn(agent: AgentNode): boolean {
  // Collect direct events (not child agents) with their types
  const directEvents: string[] = [];
  for (const item of agent.content) {
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
  node: AgentNode,
  parentSystemPrompt: string | null = null
): void {
  const agentSystemPrompt = getSystemPrompt(node);

  // Classify this node (root agent is never utility)
  if (parentSystemPrompt !== null && agentSystemPrompt !== null) {
    if (agentSystemPrompt !== parentSystemPrompt && isSingleTurn(node)) {
      node.utility = true;
    }
  }

  // Recurse into child agents
  const effectivePrompt = agentSystemPrompt ?? parentSystemPrompt;
  for (const item of node.content) {
    if (item.type === "agent") {
      classifyUtilityAgents(item, effectivePrompt);
    }
  }
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

  let initSection: SectionNode | null = null;
  let agentNode: AgentNode | null = null;
  let scoringSection: SectionNode | null = null;

  if (hasPhaseSpans) {
    // Use spans to partition events
    const initSpan = topSpans.get("init");
    const solversSpan = topSpans.get("solvers");
    const scorersSpan = topSpans.get("scorers");

    initSection = initSpan ? buildSectionFromSpan("init", initSpan) : null;
    agentNode = solversSpan
      ? buildAgentFromSolversSpan(solversSpan, hasExplicitBranches)
      : null;
    scoringSection = scorersSpan
      ? buildSectionFromSpan("scoring", scorersSpan)
      : null;
  } else {
    // No phase spans - treat entire tree as agent
    agentNode = buildAgentFromTree(tree, hasExplicitBranches);
  }

  // Classify utility agents and branches
  if (agentNode) {
    classifyUtilityAgents(agentNode);
    classifyBranches(agentNode, hasExplicitBranches);
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
