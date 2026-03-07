import { useMemo } from "react";

import { parsePackageName } from "../../../utils/python";
import { EventNode } from "../types";

import rowStyles from "./OutlineRow.module.css";
import outlineStyles from "./TranscriptOutline.module.css";

const kMinWidth = 120;
const kMaxWidth = 600;

// ---------------------------------------------------------------------------
// Hidden DOM container for natural-width measurement
// ---------------------------------------------------------------------------
//
// We build a hidden replica of the outline structure using the same CSS-module
// classes and inline styles as the real outline, then read its natural width. This
// avoids hardcoded padding/font constants — CSS is the single source of truth.

/** Lazily-created off-screen measurement container. Never removed. */
let measureRoot: HTMLDivElement | null = null;

function getOrCreateMeasureRoot(): HTMLDivElement {
  if (!measureRoot) {
    measureRoot = document.createElement("div");
    measureRoot.style.position = "fixed";
    measureRoot.style.top = "-9999px";
    measureRoot.style.left = "-9999px";
    measureRoot.style.visibility = "hidden";
    measureRoot.style.pointerEvents = "none";
    // Let the container be as wide as its content needs.
    measureRoot.style.width = "max-content";
    document.body.appendChild(measureRoot);
  }
  return measureRoot;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Computes the ideal outline column width by rendering labels into a hidden
 * DOM container that mirrors the real outline structure (same CSS-module
 * classes and inline styles), then reading its natural width.
 *
 * Result is clamped to [kMinWidth, kMaxWidth] px.
 */
export function useOutlineWidth(
  outlineNodes: EventNode[],
  _font?: string,
  agentName?: string,
  depthsWithToggles?: ReadonlySet<number>,
  depthsWithIcons?: ReadonlySet<number>
): number {
  return useMemo(() => {
    if (outlineNodes.length === 0 && !agentName) return kMinWidth;

    const root = getOrCreateMeasureRoot();

    // Clear previous measurement content.
    root.innerHTML = "";

    // Mirror `.eventsOutline` padding-left (from TimelineEventsView.module.css)
    // and add right padding so text doesn't butt against the separator.
    root.style.paddingLeft = "0.5rem";
    root.style.paddingRight = "0.5rem";

    // ── Header ──────────────────────────────────────────────────────────
    if (agentName) {
      const header = document.createElement("div");
      header.className = [
        outlineStyles.rootHeader ?? "",
        "text-size-smaller",
        "text-style-label",
      ].join(" ");
      // Override clipping styles so scrollWidth reports the natural text width.
      header.style.overflow = "visible";
      header.style.textOverflow = "clip";
      header.textContent = parsePackageName(agentName).module;
      root.appendChild(header);
    }

    // ── Rows ────────────────────────────────────────────────────────────
    // We measure at font-weight 800 (the selected-row weight) so the column
    // is wide enough for any row to be selected without clipping.
    for (const node of outlineNodes) {
      const row = document.createElement("div");

      const hasToggle = depthsWithToggles?.has(node.depth) ?? false;
      const hasIcon = depthsWithIcons?.has(node.depth) ?? false;

      const classes = [rowStyles.eventRow ?? "", "text-size-smaller"];
      if (hasToggle) classes.push(rowStyles.withToggles ?? "");
      if (hasIcon) classes.push(rowStyles.withIcons ?? "");
      row.className = classes.join(" ");
      row.style.paddingLeft = `${node.depth * 0.4}em`;
      row.style.fontWeight = "800";

      // Toggle column placeholder (empty — just reserves space)
      if (hasToggle) {
        const toggle = document.createElement("div");
        toggle.className = rowStyles.toggle ?? "";
        row.appendChild(toggle);
      }

      // Icon column placeholder
      if (hasIcon) {
        const icon = document.createElement("div");
        icon.className = rowStyles.iconSlot ?? "";
        row.appendChild(icon);
      }

      // Label column — use `white-space: nowrap; width: max-content` so it
      // doesn't collapse into the 1fr minimum.
      const label = document.createElement("div");
      label.className = rowStyles.label ?? "";
      label.style.overflow = "visible";
      label.style.width = "max-content";
      label.textContent = parsePackageName(labelForOutlineNode(node)).module;
      row.appendChild(label);

      root.appendChild(row);
    }

    // Force a layout pass and read the natural width.
    // Use getBoundingClientRect for sub-pixel precision (scrollWidth rounds down).
    const width = root.getBoundingClientRect().width;

    return Math.min(kMaxWidth, Math.max(kMinWidth, Math.ceil(width)));
  }, [outlineNodes, agentName, depthsWithToggles, depthsWithIcons]);
}

/**
 * Simplified label extraction matching OutlineRow's labelForNode.
 * Only needs the text content for width measurement.
 */
function labelForOutlineNode(node: EventNode): string {
  // Agent card nodes: use span name (matches OutlineRow's labelForNode)
  if (node.sourceSpan?.spanType === "agent") {
    return node.sourceSpan.name;
  }

  if (node.event.event === "span_begin") {
    return node.event.name;
  }

  switch (node.event.event) {
    case "subtask":
      return node.event.name;
    case "model":
      return `model${node.event.role ? ` (${node.event.role})` : ""}`;
    case "score":
      return "scoring";
    case "step":
      return node.event.name;
    default:
      return node.event.event;
  }
}
