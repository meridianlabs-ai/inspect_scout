import { describe, expect, it } from "vitest";

import { makeSpan, ts } from "../testHelpers";

import {
  computeActiveTime,
  computeTimeMapping,
  createIdentityMapping,
  type GapRegion,
} from "./timeMapping";

// =============================================================================
// createIdentityMapping
// =============================================================================

describe("createIdentityMapping", () => {
  const start = ts(0);
  const end = ts(100);

  it("maps start to 0 and end to 100", () => {
    const m = createIdentityMapping(start, end);
    expect(m.toPercent(start)).toBe(0);
    expect(m.toPercent(end)).toBe(100);
  });

  it("maps midpoint to 50", () => {
    const m = createIdentityMapping(start, end);
    expect(m.toPercent(ts(50))).toBe(50);
  });

  it("clamps before start to 0", () => {
    const m = createIdentityMapping(start, end);
    expect(m.toPercent(ts(-10))).toBe(0);
  });

  it("clamps after end to 100", () => {
    const m = createIdentityMapping(start, end);
    expect(m.toPercent(ts(110))).toBe(100);
  });

  it("has no compression", () => {
    const m = createIdentityMapping(start, end);
    expect(m.hasCompression).toBe(false);
    expect(m.gaps).toHaveLength(0);
  });

  it("returns 0 for zero-duration range", () => {
    const m = createIdentityMapping(start, start);
    expect(m.toPercent(start)).toBe(0);
  });
});

// =============================================================================
// computeActiveTime
// =============================================================================

describe("computeActiveTime", () => {
  it("returns full wall-clock time when no gaps overlap the range", () => {
    const childA = makeSpan("A", 0, 60, 100);
    const childB = makeSpan("B", 660, 720, 100);
    const root = makeSpan("root", 0, 720, 200, [childA, childB]);
    root.idleTime = 600;
    const m = computeTimeMapping(root);

    // Query only the first active region (0-60s) — no gaps overlap
    const active = computeActiveTime(m, ts(0).getTime(), ts(60).getTime());
    expect(active).toBe(60);
  });

  it("subtracts gap time within the queried range", () => {
    const childA = makeSpan("A", 0, 60, 100);
    const childB = makeSpan("B", 660, 720, 100);
    const root = makeSpan("root", 0, 720, 200, [childA, childB]);
    root.idleTime = 600;
    const m = computeTimeMapping(root);

    // Full range: 720s wall-clock, 600s gap → 120s active
    const active = computeActiveTime(m, ts(0).getTime(), ts(720).getTime());
    expect(active).toBe(120);
  });

  it("handles partial gap overlap", () => {
    const childA = makeSpan("A", 0, 60, 100);
    const childB = makeSpan("B", 660, 720, 100);
    const root = makeSpan("root", 0, 720, 200, [childA, childB]);
    root.idleTime = 600;
    const m = computeTimeMapping(root);

    // Range 30-690: wall-clock 660s, gap overlap = min(660,690)-max(60,30) = 600s
    // Active = 660 - 600 = 60s
    const active = computeActiveTime(m, ts(30).getTime(), ts(690).getTime());
    expect(active).toBe(60);
  });

  it("returns 0 for a range entirely inside a gap", () => {
    const childA = makeSpan("A", 0, 60, 100);
    const childB = makeSpan("B", 660, 720, 100);
    const root = makeSpan("root", 0, 720, 200, [childA, childB]);
    root.idleTime = 600;
    const m = computeTimeMapping(root);

    // Range 100-600 is entirely within the gap (60-660)
    const active = computeActiveTime(m, ts(100).getTime(), ts(600).getTime());
    expect(active).toBe(0);
  });

  it("returns wall-clock time for identity mapping (no gaps)", () => {
    const m = createIdentityMapping(ts(0), ts(100));
    const active = computeActiveTime(m, ts(0).getTime(), ts(100).getTime());
    expect(active).toBe(100);
  });
});

// =============================================================================
// computeTimeMapping — no compression cases
// =============================================================================

describe("computeTimeMapping — no compression", () => {
  it("returns identity mapping when idleTime is 0", () => {
    const span = makeSpan("root", 0, 100, 500);
    const m = computeTimeMapping(span);

    expect(m.hasCompression).toBe(false);
    expect(m.gaps).toHaveLength(0);
    expect(m.toPercent(ts(0))).toBe(0);
    expect(m.toPercent(ts(50))).toBe(50);
    expect(m.toPercent(ts(100))).toBe(100);
  });

  it("returns identity mapping for empty content with idle time", () => {
    // Edge case: idleTime > 0 but no content (shouldn't happen in practice)
    const span = makeSpan("root", 0, 100, 0);
    span.idleTime = 50;
    const m = computeTimeMapping(span);

    expect(m.hasCompression).toBe(false);
  });
});

// =============================================================================
// computeTimeMapping — gap detection
// =============================================================================

describe("computeTimeMapping — gap detection", () => {
  it("detects a single large gap between two children", () => {
    // Child A: 0-60s, Child B: 660-720s (10 min gap, > 5 min threshold)
    const childA = makeSpan("A", 0, 60, 100);
    const childB = makeSpan("B", 660, 720, 100);
    const root = makeSpan("root", 0, 720, 200, [childA, childB]);
    root.idleTime = 600; // 10 min gap in seconds

    const m = computeTimeMapping(root);

    expect(m.hasCompression).toBe(true);
    expect(m.gaps).toHaveLength(1);
    expect(m.gaps[0]!.startMs).toBe(ts(60).getTime());
    expect(m.gaps[0]!.endMs).toBe(ts(660).getTime());
  });

  it("does not compress gaps below 5 min threshold", () => {
    // Child A: 0-60s, Child B: 300-360s (4 min gap, < 5 min threshold)
    const childA = makeSpan("A", 0, 60, 100);
    const childB = makeSpan("B", 300, 360, 100);
    const root = makeSpan("root", 0, 360, 200, [childA, childB]);
    root.idleTime = 240; // Set idle time to trigger detection

    const m = computeTimeMapping(root);

    expect(m.hasCompression).toBe(false);
    expect(m.gaps).toHaveLength(0);
  });

  it("detects leading gap", () => {
    // Gap from root start to first child: 0 → 400s (6.67 min)
    const child = makeSpan("A", 400, 500, 100);
    const root = makeSpan("root", 0, 500, 100, [child]);
    root.idleTime = 400;

    const m = computeTimeMapping(root);

    expect(m.hasCompression).toBe(true);
    expect(m.gaps).toHaveLength(1);
    expect(m.gaps[0]!.startMs).toBe(ts(0).getTime());
    expect(m.gaps[0]!.endMs).toBe(ts(400).getTime());
  });

  it("detects trailing gap", () => {
    // Gap from last child end to root end: 100 → 500s (6.67 min)
    const child = makeSpan("A", 0, 100, 100);
    const root = makeSpan("root", 0, 500, 100, [child]);
    root.idleTime = 400;

    const m = computeTimeMapping(root);

    expect(m.hasCompression).toBe(true);
    expect(m.gaps).toHaveLength(1);
    expect(m.gaps[0]!.startMs).toBe(ts(100).getTime());
    expect(m.gaps[0]!.endMs).toBe(ts(500).getTime());
  });

  it("detects multiple gaps", () => {
    // Three children with two large gaps (each > 5 min)
    const childA = makeSpan("A", 0, 60, 100);
    const childB = makeSpan("B", 660, 720, 100); // 10 min gap before
    const childC = makeSpan("C", 1320, 1380, 100); // 10 min gap before
    const root = makeSpan("root", 0, 1380, 300, [childA, childB, childC]);
    root.idleTime = 1200;

    const m = computeTimeMapping(root);

    expect(m.hasCompression).toBe(true);
    expect(m.gaps).toHaveLength(2);
  });
});

// =============================================================================
// computeTimeMapping — recursive gap detection
// =============================================================================

describe("computeTimeMapping — recursive gap detection", () => {
  it("detects gaps within child spans (recursive)", () => {
    // Root has ONE child span covering full range, but child has two leaf spans
    // with a 10-min gap between them
    const leafA = makeSpan("leafA", 0, 60, 50);
    const leafB = makeSpan("leafB", 660, 720, 50);
    const child = makeSpan("child", 0, 720, 100, [leafA, leafB]);
    child.idleTime = 600;
    const root = makeSpan("root", 0, 720, 100, [child]);
    root.idleTime = 600;

    const m = computeTimeMapping(root);

    // Without recursive extraction, only one interval [0, 720] → no gaps
    // With recursive extraction, leaf intervals [0,60] and [660,720] → gap at 60-660
    expect(m.hasCompression).toBe(true);
    expect(m.gaps).toHaveLength(1);
  });
});

// =============================================================================
// computeTimeMapping — percent allocation
// =============================================================================

describe("computeTimeMapping — percent allocation", () => {
  it("gives active regions all the space (gaps are zero-width)", () => {
    // 60s active + 10 min gap + 60s active = 720s total
    // Gap should be collapsed to 0%, active gets 100%
    const childA = makeSpan("A", 0, 60, 100);
    const childB = makeSpan("B", 660, 720, 100);
    const root = makeSpan("root", 0, 720, 200, [childA, childB]);
    root.idleTime = 600;

    const m = computeTimeMapping(root);

    // Start of A should be at 0%
    expect(m.toPercent(ts(0))).toBeCloseTo(0, 0);

    // End of B should be at ~100%
    expect(m.toPercent(ts(720))).toBeCloseTo(100, 0);

    // The gap (60-660s) should be collapsed to 0%
    const gapStart = m.toPercent(ts(60));
    const gapEnd = m.toPercent(ts(660));
    expect(gapEnd - gapStart).toBeCloseTo(0, 0);

    // Active regions should share 100%
    const activeA = m.toPercent(ts(60)) - m.toPercent(ts(0));
    const activeB = m.toPercent(ts(720)) - m.toPercent(ts(660));
    // Both active regions are 60s, so they should be roughly equal (~50% each)
    expect(activeA).toBeCloseTo(50, 0);
    expect(activeB).toBeCloseTo(50, 0);
  });

  it("gaps take zero width even with many gaps", () => {
    // Create 10 gaps — all should be zero-width
    const children = Array.from({ length: 11 }, (_, i) => {
      const start = i * 400;
      return makeSpan(`C${i}`, start, start + 10, 10);
    });
    const lastEnd = 10 * 400 + 10;
    const root = makeSpan("root", 0, lastEnd, 110, children);
    root.idleTime = 3900; // Large idle time

    const m = computeTimeMapping(root);

    if (m.hasCompression) {
      // Sum of all gap widths should be 0%
      const totalGapPercent = m.gaps.reduce(
        (sum: number, g: GapRegion) => sum + (g.percentEnd - g.percentStart),
        0
      );
      expect(totalGapPercent).toBeCloseTo(0, 0);
    }
  });
});

// =============================================================================
// computeTimeMapping — monotonicity
// =============================================================================

describe("computeTimeMapping — monotonicity", () => {
  it("produces monotonically increasing percentages", () => {
    const childA = makeSpan("A", 0, 60, 100);
    const childB = makeSpan("B", 660, 720, 100);
    const root = makeSpan("root", 0, 720, 200, [childA, childB]);
    root.idleTime = 600;

    const m = computeTimeMapping(root);

    // Sample at regular intervals and verify monotonicity
    let prev = -1;
    for (let sec = 0; sec <= 720; sec += 10) {
      const pct = m.toPercent(ts(sec));
      expect(pct).toBeGreaterThanOrEqual(prev);
      prev = pct;
    }
  });

  it("clamps before start to 0 and after end to 100", () => {
    const childA = makeSpan("A", 0, 60, 100);
    const childB = makeSpan("B", 660, 720, 100);
    const root = makeSpan("root", 0, 720, 200, [childA, childB]);
    root.idleTime = 600;

    const m = computeTimeMapping(root);

    expect(m.toPercent(ts(-100))).toBe(0);
    expect(m.toPercent(ts(1000))).toBe(100);
  });
});

// =============================================================================
// computeTimeMapping — overlapping children
// =============================================================================

describe("computeTimeMapping — overlapping children", () => {
  it("merges overlapping intervals into single active region", () => {
    // Two overlapping children: A(0-100), B(50-150), gap, C(800-900)
    const childA = makeSpan("A", 0, 100, 100);
    const childB = makeSpan("B", 50, 150, 100);
    const childC = makeSpan("C", 800, 900, 100);
    const root = makeSpan("root", 0, 900, 300, [childA, childB, childC]);
    root.idleTime = 650;

    const m = computeTimeMapping(root);

    expect(m.hasCompression).toBe(true);
    // Should have one gap: 150 → 800 (10.8 min)
    expect(m.gaps).toHaveLength(1);
    expect(m.gaps[0]!.startMs).toBe(ts(150).getTime());
    expect(m.gaps[0]!.endMs).toBe(ts(800).getTime());
  });
});
