/**
 * Swimlane row computation for the timeline UI.
 *
 * Transforms an AgentNode's children into SwimLaneRow[] for rendering
 * as horizontal swimlane bars. Handles sequential, iterative (multiple spans),
 * and parallel (overlapping) agent patterns.
 */

import type { AgentNode, SectionNode } from "../../components/transcript/nodes";

// =============================================================================
// Types
// =============================================================================

export interface SingleSpan {
  agent: AgentNode;
}

export interface ParallelSpan {
  agents: AgentNode[];
}

export type TimelineSpan = SingleSpan | ParallelSpan;

export interface SwimLaneRow {
  name: string;
  spans: TimelineSpan[];
  totalTokens: number;
  startTime: Date;
  endTime: Date;
}

// =============================================================================
// Type Guards
// =============================================================================

export function isSingleSpan(span: TimelineSpan): span is SingleSpan {
  return "agent" in span;
}

export function isParallelSpan(span: TimelineSpan): span is ParallelSpan {
  return "agents" in span;
}

// =============================================================================
// SectionNode → AgentNode Conversion
// =============================================================================

/**
 * Converts a SectionNode (init/scoring) into an AgentNode so that all
 * swimlane logic operates uniformly on AgentNodes.
 */
export function sectionToAgent(section: SectionNode): AgentNode {
  const name =
    section.section.charAt(0).toUpperCase() + section.section.slice(1);
  return {
    type: "agent",
    id: section.section,
    name,
    source: { source: "span", spanId: section.section },
    content: section.content,
    branches: [],
    utility: false,
    startTime: section.startTime,
    endTime: section.endTime,
    totalTokens: section.totalTokens,
  };
}

// =============================================================================
// Overlap Detection
// =============================================================================

/** Tolerance in milliseconds for considering two agents as overlapping. */
const OVERLAP_TOLERANCE_MS = 100;

/**
 * Returns true if two agents overlap in time, within the tolerance.
 * Two agents overlap if A starts before B ends and B starts before A ends.
 */
function agentsOverlap(a: AgentNode, b: AgentNode): boolean {
  return (
    a.startTime.getTime() < b.endTime.getTime() + OVERLAP_TOLERANCE_MS &&
    b.startTime.getTime() < a.endTime.getTime() + OVERLAP_TOLERANCE_MS
  );
}

/**
 * Returns true if any pair of agents in the group overlap.
 */
function groupHasOverlap(agents: AgentNode[]): boolean {
  for (let i = 0; i < agents.length; i++) {
    for (let j = i + 1; j < agents.length; j++) {
      const a = agents[i];
      const b = agents[j];
      if (a && b && agentsOverlap(a, b)) {
        return true;
      }
    }
  }
  return false;
}

// =============================================================================
// Main Computation
// =============================================================================

/**
 * Computes swimlane rows from an AgentNode's children.
 *
 * The caller is responsible for folding init/scoring into the node's content
 * (via `sectionToAgent`) before calling this function.
 *
 * @returns Array of SwimLaneRow, with the parent row always first,
 *          followed by child rows ordered by earliest start time.
 */
export function computeSwimLaneRows(node: AgentNode): SwimLaneRow[] {
  // Parent row is always first
  const parentRow = buildParentRow(node);

  // Collect non-utility child agents
  const children = node.content.filter(
    (item): item is AgentNode => item.type === "agent" && !item.utility
  );

  if (children.length === 0) {
    return [parentRow];
  }

  // Group by name (case-insensitive)
  const groups = groupByName(children);

  // Build rows from groups
  const childRows: SwimLaneRow[] = [];
  for (const [displayName, agents] of groups) {
    const row = buildRowFromGroup(displayName, agents);
    if (row) {
      childRows.push(row);
    }
  }

  // Sort child rows by earliest start time
  childRows.sort((a, b) => a.startTime.getTime() - b.startTime.getTime());

  return [parentRow, ...childRows];
}

// =============================================================================
// Internal Helpers
// =============================================================================

function buildParentRow(node: AgentNode): SwimLaneRow {
  return {
    name: node.name,
    spans: [{ agent: node }],
    totalTokens: node.totalTokens,
    startTime: node.startTime,
    endTime: node.endTime,
  };
}

/**
 * Groups agents by name (case-insensitive), preserving the display name
 * from the first agent encountered in each group.
 *
 * Returns entries in insertion order (first-seen order).
 */
function groupByName(agents: AgentNode[]): [string, AgentNode[]][] {
  const map = new Map<string, { displayName: string; agents: AgentNode[] }>();

  for (const agent of agents) {
    const key = agent.name.toLowerCase();
    const existing = map.get(key);
    if (existing) {
      existing.agents.push(agent);
    } else {
      map.set(key, { displayName: agent.name, agents: [agent] });
    }
  }

  return Array.from(map.values()).map((g) => [g.displayName, g.agents]);
}

function buildRowFromGroup(
  displayName: string,
  agents: AgentNode[]
): SwimLaneRow | null {
  // Sort agents by start time
  const sorted = [...agents].sort(
    (a, b) => a.startTime.getTime() - b.startTime.getTime()
  );

  const first = sorted[0];
  if (!first) {
    return null;
  }

  // Determine spans based on overlap
  let spans: TimelineSpan[];
  if (sorted.length === 1) {
    spans = [{ agent: first }];
  } else if (groupHasOverlap(sorted)) {
    // Any overlap → entire group is one ParallelSpan
    spans = [{ agents: sorted }];
  } else {
    // No overlap → each agent is a separate SingleSpan (iterative)
    spans = sorted.map((agent) => ({ agent }));
  }

  // Compute aggregated time range and tokens
  const startTime = first.startTime;
  const endTime = sorted.reduce(
    (latest, agent) =>
      agent.endTime.getTime() > latest.getTime() ? agent.endTime : latest,
    first.endTime
  );
  const totalTokens = sorted.reduce((sum, agent) => sum + agent.totalTokens, 0);

  return {
    name: displayName,
    spans,
    totalTokens,
    startTime,
    endTime,
  };
}
