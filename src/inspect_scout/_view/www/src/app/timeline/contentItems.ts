/**
 * Content item building for the timeline detail panel.
 *
 * Transforms a TimelineSpan's content and branches into a flat list of
 * ContentItems for rendering. Branch cards are inserted after the event
 * they forked from (matched by UUID).
 */

import type {
  TimelineBranch,
  TimelineEvent,
  TimelineSpan,
} from "../../components/transcript/timeline";

// =============================================================================
// Types
// =============================================================================

export interface EventItem {
  type: "event";
  eventNode: TimelineEvent;
}

export interface AgentCardItem {
  type: "agent_card";
  agentNode: TimelineSpan;
}

export interface BranchCardItem {
  type: "branch_card";
  branch: TimelineBranch;
}

export type ContentItem = EventItem | AgentCardItem | BranchCardItem;

// =============================================================================
// Main Function
// =============================================================================

/**
 * Builds a flat list of content items from a TimelineSpan.
 *
 * Walks the span's content chronologically, converting each child to either
 * an event item or agent card. Then inserts branch cards after the event
 * whose UUID matches `branch.forkedAt`. Branches with unresolvable UUIDs
 * are appended at the end.
 *
 * Utility spans are always included — filtering is a UI concern.
 */
export function buildContentItems(node: TimelineSpan): ContentItem[] {
  // 1. Walk content chronologically
  const items: ContentItem[] = node.content.map((child) =>
    child.type === "event"
      ? { type: "event" as const, eventNode: child }
      : { type: "agent_card" as const, agentNode: child }
  );

  // 2. Insert branch cards at fork points
  if (node.branches.length === 0) {
    return items;
  }

  return insertBranchCards(items, node.branches);
}

// =============================================================================
// Internal Helpers
// =============================================================================

/**
 * Inserts branch cards after the event matching each branch's `forkedAt` UUID.
 *
 * Groups branches by forkedAt so multiple branches at the same fork point
 * appear consecutively. Branches with no matching UUID are appended at the end.
 */
function insertBranchCards(
  items: ContentItem[],
  branches: TimelineBranch[]
): ContentItem[] {
  // Group branches by forkedAt
  const byForkPoint = new Map<string, TimelineBranch[]>();
  for (const branch of branches) {
    const existing = byForkPoint.get(branch.forkedAt);
    if (existing) {
      existing.push(branch);
    } else {
      byForkPoint.set(branch.forkedAt, [branch]);
    }
  }

  // Find insertion points (index after the matching event)
  const insertions: { afterIndex: number; branches: TimelineBranch[] }[] = [];
  const unmatched: TimelineBranch[] = [];

  for (const [forkedAt, forkBranches] of byForkPoint) {
    const index = findEventByUuid(items, forkedAt);
    if (index !== -1) {
      insertions.push({ afterIndex: index, branches: forkBranches });
    } else {
      unmatched.push(...forkBranches);
    }
  }

  // Sort insertions by position descending so we can insert back-to-front
  // without invalidating indices
  insertions.sort((a, b) => b.afterIndex - a.afterIndex);

  const result = [...items];

  for (const { afterIndex, branches: forkBranches } of insertions) {
    const cards: BranchCardItem[] = forkBranches.map((branch) => ({
      type: "branch_card" as const,
      branch,
    }));
    result.splice(afterIndex + 1, 0, ...cards);
  }

  // Append unmatched branches at the end
  for (const branch of unmatched) {
    result.push({ type: "branch_card", branch });
  }

  return result;
}

/**
 * Finds the index of the event item whose event UUID matches the given value.
 * Returns -1 if not found.
 */
function findEventByUuid(items: ContentItem[], uuid: string): number {
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (item && item.type === "event" && item.eventNode.event.uuid === uuid) {
      return i;
    }
  }
  return -1;
}
