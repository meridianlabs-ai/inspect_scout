import { describe, expect, it } from "vitest";

import type { TimelineEvent } from "../../components/transcript/timeline";
import type { CompactionEvent, InfoEvent } from "../../types/api-types";

import { ts } from "./testHelpers";
import {
  buildSelectionKey,
  computeCompactionRegions,
  parseSelection,
} from "./timelineEventNodes";

// =============================================================================
// Test helpers
// =============================================================================

function makeTimelineEvent(
  eventType: string,
  startSec: number,
  endSec: number,
  tokens = 10
): TimelineEvent {
  const event =
    eventType === "compaction"
      ? ({
          event: "compaction",
          timestamp: ts(startSec).toISOString(),
          working_start: startSec,
          pending: false,
          span_id: null,
          uuid: `compaction-${startSec}`,
          metadata: null,
          source: "",
          tokens_before: null,
          tokens_after: null,
          type: "summary",
        } satisfies CompactionEvent)
      : ({
          event: "info",
          timestamp: ts(startSec).toISOString(),
          working_start: startSec,
          pending: false,
          span_id: null,
          uuid: `info-${startSec}`,
          metadata: null,
          source: "",
          data: "",
        } satisfies InfoEvent);

  return {
    type: "event",
    event,
    startTime: ts(startSec),
    endTime: ts(endSec),
    totalTokens: tokens,
    idleTime: 0,
  };
}

// =============================================================================
// parseSelection
// =============================================================================

describe("parseSelection", () => {
  it("returns null for null input", () => {
    expect(parseSelection(null)).toBeNull();
  });

  it("returns null for empty string", () => {
    expect(parseSelection("")).toBeNull();
  });

  it("parses a bare row key", () => {
    expect(parseSelection("agent")).toEqual({
      rowKey: "agent",
      spanIndex: null,
      regionIndex: null,
    });
  });

  it("parses a row key with span index", () => {
    expect(parseSelection("agent:1")).toEqual({
      rowKey: "agent",
      spanIndex: 1,
      regionIndex: null,
    });
  });

  it("parses a row key with region index", () => {
    expect(parseSelection("agent@2")).toEqual({
      rowKey: "agent",
      spanIndex: null,
      regionIndex: 2,
    });
  });

  it("parses a row key with span and region index", () => {
    expect(parseSelection("agent:1@3")).toEqual({
      rowKey: "agent",
      spanIndex: 1,
      regionIndex: 3,
    });
  });

  it("handles zero-based indices", () => {
    expect(parseSelection("key:0@0")).toEqual({
      rowKey: "key",
      spanIndex: 0,
      regionIndex: 0,
    });
  });

  it("handles hierarchical row keys with slashes", () => {
    expect(parseSelection("solvers/agent:2@1")).toEqual({
      rowKey: "solvers/agent",
      spanIndex: 2,
      regionIndex: 1,
    });
  });

  it("treats negative region as no region (invalid)", () => {
    // Negative numbers should not parse as valid region indices
    const result = parseSelection("agent@-1");
    expect(result).toEqual({
      rowKey: "agent@-1",
      spanIndex: null,
      regionIndex: null,
    });
  });

  it("treats non-numeric region suffix as part of the key", () => {
    const result = parseSelection("agent@abc");
    expect(result).toEqual({
      rowKey: "agent@abc",
      spanIndex: null,
      regionIndex: null,
    });
  });
});

// =============================================================================
// buildSelectionKey
// =============================================================================

describe("buildSelectionKey", () => {
  it("builds a bare row key", () => {
    expect(buildSelectionKey("agent")).toBe("agent");
  });

  it("builds a key with span index", () => {
    expect(buildSelectionKey("agent", 1)).toBe("agent:1");
  });

  it("builds a key with region index only", () => {
    expect(buildSelectionKey("agent", undefined, 2)).toBe("agent@2");
  });

  it("builds a key with span and region index", () => {
    expect(buildSelectionKey("agent", 1, 3)).toBe("agent:1@3");
  });

  it("roundtrips through parseSelection", () => {
    const key = buildSelectionKey("solvers/sub", 2, 4);
    const parsed = parseSelection(key);
    expect(parsed).toEqual({
      rowKey: "solvers/sub",
      spanIndex: 2,
      regionIndex: 4,
    });
  });
});

// =============================================================================
// computeCompactionRegions
// =============================================================================

describe("computeCompactionRegions", () => {
  it("returns a single region when there are no compaction events", () => {
    const events = [
      makeTimelineEvent("info", 0, 1),
      makeTimelineEvent("info", 1, 2),
      makeTimelineEvent("info", 2, 3),
    ];

    const regions = computeCompactionRegions(events);
    expect(regions).toHaveLength(1);
    expect(regions[0]).toEqual(events);
  });

  it("returns empty single region for empty content", () => {
    const regions = computeCompactionRegions([]);
    expect(regions).toHaveLength(1);
    expect(regions[0]).toEqual([]);
  });

  it("splits at one compaction event into two regions", () => {
    const e1 = makeTimelineEvent("info", 0, 1);
    const compaction = makeTimelineEvent("compaction", 1, 1);
    const e2 = makeTimelineEvent("info", 1, 2);

    const regions = computeCompactionRegions([e1, compaction, e2]);
    expect(regions).toHaveLength(2);
    expect(regions[0]).toEqual([e1]);
    expect(regions[1]).toEqual([e2]);
  });

  it("splits at multiple compaction events", () => {
    const e1 = makeTimelineEvent("info", 0, 1);
    const c1 = makeTimelineEvent("compaction", 1, 1);
    const e2 = makeTimelineEvent("info", 1, 2);
    const c2 = makeTimelineEvent("compaction", 2, 2);
    const e3 = makeTimelineEvent("info", 2, 3);
    const c3 = makeTimelineEvent("compaction", 3, 3);
    const e4 = makeTimelineEvent("info", 3, 4);

    const regions = computeCompactionRegions([e1, c1, e2, c2, e3, c3, e4]);
    expect(regions).toHaveLength(4);
    expect(regions[0]).toEqual([e1]);
    expect(regions[1]).toEqual([e2]);
    expect(regions[2]).toEqual([e3]);
    expect(regions[3]).toEqual([e4]);
  });

  it("handles consecutive compactions (empty regions)", () => {
    const e1 = makeTimelineEvent("info", 0, 1);
    const c1 = makeTimelineEvent("compaction", 1, 1);
    const c2 = makeTimelineEvent("compaction", 1, 1);
    const e2 = makeTimelineEvent("info", 1, 2);

    const regions = computeCompactionRegions([e1, c1, c2, e2]);
    expect(regions).toHaveLength(3);
    expect(regions[0]).toEqual([e1]);
    expect(regions[1]).toEqual([]); // empty region between consecutive compactions
    expect(regions[2]).toEqual([e2]);
  });

  it("handles compaction at the start", () => {
    const c = makeTimelineEvent("compaction", 0, 0);
    const e = makeTimelineEvent("info", 0, 1);

    const regions = computeCompactionRegions([c, e]);
    expect(regions).toHaveLength(2);
    expect(regions[0]).toEqual([]); // empty region before the compaction
    expect(regions[1]).toEqual([e]);
  });

  it("handles compaction at the end", () => {
    const e = makeTimelineEvent("info", 0, 1);
    const c = makeTimelineEvent("compaction", 1, 1);

    const regions = computeCompactionRegions([e, c]);
    expect(regions).toHaveLength(2);
    expect(regions[0]).toEqual([e]);
    expect(regions[1]).toEqual([]); // empty region after the compaction
  });

  it("excludes compaction events from regions", () => {
    const e1 = makeTimelineEvent("info", 0, 1);
    const c = makeTimelineEvent("compaction", 1, 1);
    const e2 = makeTimelineEvent("info", 1, 2);

    const regions = computeCompactionRegions([e1, c, e2]);
    // Compaction events should not appear in any region
    for (const region of regions) {
      for (const item of region) {
        if (item.type === "event") {
          expect(item.event.event).not.toBe("compaction");
        }
      }
    }
  });
});
