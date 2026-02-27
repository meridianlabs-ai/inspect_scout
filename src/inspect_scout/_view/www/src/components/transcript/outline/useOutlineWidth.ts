import { useMemo } from "react";

import { parsePackageName } from "../../../utils/python";
import { EventNode } from "../types";

const kMinWidth = 120;
const kMaxWidth = 400;

// Padding: toggle column (10px) + column gap (3px) + icon (~14px) + icon margin (3px)
// + container left padding (0.5rem ≈ 8px) + toggle button right (~24px) + buffer
const kHorizontalPadding = 70;

// Approximate em-to-px conversion for depth indent at the outline's font size
const kDepthIndentPx = 5.5; // 0.4em * ~13.6px per em

// Module-level canvas reused across all hook instances for text measurement.
// This is never attached to the DOM — it exists solely for measureText().
let measureCanvas: HTMLCanvasElement | null = null;

function getMeasureContext(font: string): CanvasRenderingContext2D | null {
  if (!measureCanvas) {
    measureCanvas = document.createElement("canvas");
  }
  const ctx = measureCanvas.getContext("2d");
  if (ctx) ctx.font = font;
  return ctx;
}

/**
 * Computes the ideal outline column width from the outline node labels.
 *
 * Uses a hidden canvas to measure text widths without triggering layout,
 * then adds padding for icons, depth indentation, and container chrome.
 * Result is clamped to [120, 400] px.
 */
export function useOutlineWidth(
  outlineNodes: EventNode[],
  font?: string
): number {
  return useMemo(() => {
    if (outlineNodes.length === 0) return kMinWidth;

    // Match the outline's font: text-size-smaller class uses
    // --inspect-font-size-smaller which is typically ~0.8rem.
    // The default body font is the Bootstrap/system font stack.
    const resolvedFont =
      font ??
      '600 0.8rem -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    const ctx = getMeasureContext(resolvedFont);
    if (!ctx) return kMinWidth;

    let maxWidth = 0;
    for (const node of outlineNodes) {
      const label = parsePackageName(labelForOutlineNode(node)).module;
      const textWidth = ctx.measureText(label).width;
      const depthPx = node.depth * kDepthIndentPx;
      const totalWidth = textWidth + depthPx + kHorizontalPadding;
      if (totalWidth > maxWidth) maxWidth = totalWidth;
    }

    return Math.min(kMaxWidth, Math.max(kMinWidth, Math.ceil(maxWidth)));
  }, [outlineNodes, font]);
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
