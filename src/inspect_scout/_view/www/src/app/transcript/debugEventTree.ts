/**
 * Debug utilities: print event structures as indented tree strings.
 *
 * - eventTree(selectedEvents)  — flat Event[] with span_begin/span_end depth
 * - eventNodeTree(eventNodes)  — EventNode[] tree (already has children)
 *
 * Usage:
 *   console.log(eventTree(selectedEvents));
 *   console.log(eventNodeTree(eventNodes));
 */

import type { EventNode } from "../../components/transcript/types";
import type { Event } from "../../types/api-types";

function label(ev: Event): string {
  switch (ev.event) {
    case "span_begin":
      return [
        "span_begin",
        ev.name,
        ev.type ? `type=${ev.type}` : null,
        `id=${ev.id}`,
      ]
        .filter(Boolean)
        .join(" ");

    case "span_end":
      return `span_end id=${ev.id}`;

    case "model":
      return [
        "model",
        ev.model,
        ev.role ? `role=${ev.role}` : null,
        ev.cache ? `cache=${ev.cache}` : null,
        ev.error ? "ERROR" : null,
      ]
        .filter(Boolean)
        .join(" ");

    case "tool":
      return [
        "tool",
        ev.function,
        ev.agent ? `agent=${ev.agent}` : null,
        ev.failed ? "FAILED" : null,
      ]
        .filter(Boolean)
        .join(" ");

    case "subtask":
      return ["subtask", ev.name, ev.type ? `type=${ev.type}` : null]
        .filter(Boolean)
        .join(" ");

    case "step":
      return `step ${ev.action} ${ev.name}${ev.type ? ` type=${ev.type}` : ""}`;

    case "score":
      return `score${ev.intermediate ? " (intermediate)" : ""}`;

    case "score_edit":
      return `score_edit ${ev.score_name}`;

    case "sample_init":
      return "sample_init";

    case "sample_limit":
      return `sample_limit ${ev.type} limit=${ev.limit ?? "?"}`;

    case "sandbox":
      return `sandbox ${ev.action}${ev.cmd ? ` cmd=${truncate(ev.cmd, 40)}` : ""}${ev.file ? ` file=${ev.file}` : ""}`;

    case "state":
      return `state (${ev.changes.length} change${ev.changes.length !== 1 ? "s" : ""})`;

    case "store":
      return `store (${ev.changes.length} change${ev.changes.length !== 1 ? "s" : ""})`;

    case "input":
      return `input ${truncate(ev.input, 50)}`;

    case "error":
      return `error ${ev.error.message}`;

    case "info":
      return `info${ev.source ? ` source=${ev.source}` : ""}`;

    case "logger":
      return `logger ${ev.message.level}`;

    case "approval":
      return `approval ${ev.decision} approver=${ev.approver}`;

    case "compaction":
      return `compaction${ev.source ? ` source=${ev.source}` : ""}`;

    default: {
      const exhaustive: never = ev;
      return (exhaustive as { event: string }).event;
    }
  }
}

function truncate(s: string, max: number): string {
  const single = s.replace(/\n/g, "\\n");
  return single.length <= max ? single : single.slice(0, max - 1) + "\u2026";
}

const INDENT = "  ";

export function eventTree(events: ReadonlyArray<Event>): string {
  const lines: string[] = [];
  let depth = 0;

  for (const ev of events) {
    if (ev.event === "span_end") {
      depth = Math.max(0, depth - 1);
    }

    lines.push(`${INDENT.repeat(depth)}${label(ev)}`);

    if (ev.event === "span_begin") {
      depth++;
    }
  }

  return lines.join("\n");
}

export function eventNodeTree(nodes: ReadonlyArray<EventNode>): string {
  const lines: string[] = [];

  function walk(node: EventNode, depth: number): void {
    const childCount = node.children.length;
    const suffix = childCount > 0 ? ` [${childCount}]` : "";
    lines.push(`${INDENT.repeat(depth)}${label(node.event)}${suffix}`);
    for (const child of node.children) {
      walk(child, depth + 1);
    }
  }

  for (const node of nodes) {
    walk(node, 0);
  }

  return lines.join("\n");
}
