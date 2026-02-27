import { r as reactExports, j as jsxRuntimeExports, c as clsx, $ as Link, A as ApplicationIcons, u as useStore } from "./index.js";
import { x as useCollapseTranscriptEvent, P as PulsingDots, y as kSandboxSignalName, E as EventNode, z as TYPE_SCORERS, B as TYPE_SCORER, F as useVirtuosoState, m as useTranscriptNavigation, G as flatTree, H as kTranscriptOutlineCollapseScope, I as useScrollTrack, Y as Yr, w as useProperty, K as computeBarPosition, N as formatTokenCount, O as findBranchesByForkedAt, Q as parsePathSegment, U as createBranchSpan } from "./TranscriptViewNodes.js";
import { e as formatTime, g as formatDuration, h as formatDurationShort, P as PopOver } from "./ToolButton.js";
const parsePackageName = (name) => {
  if (name.includes("/")) {
    const [packageName, moduleName] = name.split("/", 2);
    return { package: packageName || "", module: moduleName || "" };
  }
  return { package: "", module: name };
};
const eventRow = "_eventRow_1j0jk_1";
const selected = "_selected_1j0jk_8";
const toggle = "_toggle_1j0jk_12";
const eventLink = "_eventLink_1j0jk_17";
const label$1 = "_label_1j0jk_28";
const icon = "_icon_1j0jk_34";
const progress = "_progress_1j0jk_38";
const styles$3 = {
  eventRow,
  selected,
  toggle,
  eventLink,
  label: label$1,
  icon,
  progress
};
const OutlineRow = ({
  node,
  collapseScope,
  running,
  selected: selected2,
  getEventUrl,
  onSelect
}) => {
  const [collapsed, setCollapsed] = useCollapseTranscriptEvent(
    collapseScope,
    node.id
  );
  const icon2 = iconForNode(node);
  const toggle2 = toggleIcon(node, collapsed);
  const ref = reactExports.useRef(null);
  const eventUrl = getEventUrl?.(node.id);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: clsx(
        styles$3.eventRow,
        "text-size-smaller",
        selected2 ? styles$3.selected : ""
      ),
      style: { paddingLeft: `${node.depth * 0.4}em` },
      "data-unsearchable": true,
      onClick: () => onSelect?.(node.id),
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(styles$3.toggle),
            onClick: () => {
              setCollapsed(!collapsed);
            },
            children: toggle2 ? /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(toggle2) }) : void 0
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            className: clsx(styles$3.label),
            "data-depth": node.depth,
            title: tooltipForNode(node),
            children: [
              icon2 ? /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(icon2, styles$3.icon) }) : void 0,
              eventUrl ? /* @__PURE__ */ jsxRuntimeExports.jsx(Link, { to: eventUrl, className: clsx(styles$3.eventLink), ref, children: parsePackageName(labelForNode(node)).module }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { ref, children: parsePackageName(labelForNode(node)).module }),
              running ? /* @__PURE__ */ jsxRuntimeExports.jsx(
                PulsingDots,
                {
                  size: "small",
                  className: clsx(styles$3.progress),
                  subtle: false
                }
              ) : void 0
            ]
          }
        )
      ]
    }
  ) });
};
const toggleIcon = (node, collapsed) => {
  if (node.children.length > 0) {
    return collapsed ? ApplicationIcons.chevron.right : ApplicationIcons.chevron.down;
  }
};
const iconForNode = (node) => {
  switch (node.event.event) {
    case "sample_limit":
      return ApplicationIcons.limits.custom;
    case "score":
      return ApplicationIcons.scorer;
    case "error":
      return ApplicationIcons.error;
  }
};
const tooltipForNode = (node) => {
  if (node.sourceSpan?.spanType === "agent" && node.sourceSpan.description) {
    return node.sourceSpan.description;
  }
};
const labelForNode = (node) => {
  if (node.sourceSpan?.spanType === "agent") {
    return node.sourceSpan.name.toLowerCase();
  }
  if (node.event.event === "span_begin") {
    switch (node.event.type) {
      case "solver":
        return node.event.name;
      case "tool":
        return node.event.name;
      default: {
        if (node.event.name === kSandboxSignalName) {
          return "sandbox events";
        }
        return node.event.name;
      }
    }
  } else {
    switch (node.event.event) {
      case "subtask":
        return node.event.name;
      case "approval":
        switch (node.event.decision) {
          case "approve":
            return "approved";
          case "reject":
            return "rejected";
          case "escalate":
            return "escalated";
          case "modify":
            return "modified";
          case "terminate":
            return "terminated";
          default:
            return node.event.decision;
        }
      case "model":
        return `model${node.event.role ? ` (${node.event.role})` : ""}`;
      case "score":
        return "scoring";
      case "step":
        if (node.event.name === kSandboxSignalName) {
          return "sandbox events";
        }
        return node.event.name;
      default:
        return node.event.event;
    }
  }
};
const styles$2 = {};
const kTurnType = "turn";
const kTurnsType = "turns";
const kCollapsedScoring = "scorings";
const removeNodeVisitor = (event) => {
  return {
    visit: (node) => {
      if (node.event.event === event) {
        return [];
      }
      return [node];
    }
  };
};
const removeStepSpanNameVisitor = (name) => {
  return {
    visit: (node) => {
      if ((node.event.event === "step" || node.event.event === "span_begin") && node.event.name === name) {
        return [];
      }
      return [node];
    }
  };
};
const noScorerChildren = () => {
  let inScorers = false;
  let inScorer = false;
  let currentDepth = -1;
  return {
    visit: (node) => {
      if (node.event.event === "span_begin" && node.event.type === TYPE_SCORERS) {
        inScorers = true;
        return [node];
      }
      if ((node.event.event === "step" || node.event.event === "span_begin") && node.event.type === TYPE_SCORER) {
        inScorer = true;
        currentDepth = node.depth;
        return [node];
      }
      if (inScorers && inScorer && node.depth === currentDepth + 1) {
        return [];
      }
      return [node];
    }
  };
};
const makeTurns = (eventNodes) => {
  const results = [];
  let modelNode = null;
  const toolNodes = [];
  let turnCount = 1;
  const makeTurn = (force) => {
    if (modelNode !== null && (force || toolNodes.length > 0)) {
      const turnNode = new EventNode(
        modelNode.id,
        {
          id: modelNode.id,
          event: "span_begin",
          type: kTurnType,
          name: `turn ${turnCount++}`,
          pending: false,
          working_start: modelNode.event.working_start,
          timestamp: modelNode.event.timestamp,
          parent_id: null,
          span_id: modelNode.event.span_id,
          uuid: null,
          metadata: null
        },
        modelNode.depth
      );
      turnNode.children = [modelNode, ...toolNodes];
      results.push(turnNode);
    }
    modelNode = null;
    toolNodes.length = 0;
  };
  for (const node of eventNodes) {
    if (node.event.event === "model") {
      if (modelNode !== null && toolNodes.length === 0) {
        makeTurn(true);
      } else {
        makeTurn();
        modelNode = node;
      }
    } else if (node.event.event === "tool") {
      toolNodes.push(node);
    } else {
      makeTurn();
      results.push(node);
    }
  }
  makeTurn();
  return results;
};
const collapseTurns = (eventNodes) => {
  const results = [];
  const collecting = [];
  const collect = () => {
    if (collecting.length > 0) {
      const numberOfTurns = collecting.length;
      const firstTurn = collecting[0];
      if (!firstTurn) {
        return;
      }
      const turnNode = new EventNode(
        firstTurn.id,
        {
          ...firstTurn.event,
          name: `${numberOfTurns} ${numberOfTurns === 1 ? "turn" : "turns"}`,
          type: kTurnsType
        },
        firstTurn.depth
      );
      results.push(turnNode);
      collecting.length = 0;
    }
  };
  for (const node of eventNodes) {
    if (node.event.event === "span_begin" && node.event.type === kTurnType) {
      if (collecting.length > 0 && collecting[0]?.depth !== node.depth) {
        collect();
      }
      collecting.push(node);
    } else {
      collect();
      results.push(node);
    }
  }
  collect();
  return results;
};
const collapseScoring = (eventNodes) => {
  const results = [];
  const collecting = [];
  const collect = () => {
    if (collecting.length > 0) {
      const firstScore = collecting[0];
      if (!firstScore) {
        return;
      }
      const turnNode = new EventNode(
        firstScore.id,
        {
          ...firstScore.event,
          name: "scoring",
          type: kCollapsedScoring
        },
        firstScore.depth
      );
      results.push(turnNode);
      collecting.length = 0;
    }
  };
  for (const node of eventNodes) {
    if (node.event.event === "score") {
      collecting.push(node);
    } else {
      collect();
      results.push(node);
    }
  }
  collect();
  return results;
};
const kMinWidth = 120;
const kMaxWidth = 400;
const kHorizontalPadding = 70;
const kDepthIndentPx = 5.5;
let measureCanvas = null;
function getMeasureContext(font) {
  if (!measureCanvas) {
    measureCanvas = document.createElement("canvas");
  }
  const ctx = measureCanvas.getContext("2d");
  if (ctx) ctx.font = font;
  return ctx;
}
function useOutlineWidth(outlineNodes, font) {
  return reactExports.useMemo(() => {
    if (outlineNodes.length === 0) return kMinWidth;
    const resolvedFont = '600 0.8rem -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    const ctx = getMeasureContext(resolvedFont);
    if (!ctx) return kMinWidth;
    let maxWidth = 0;
    for (const node of outlineNodes) {
      const label2 = parsePackageName(labelForOutlineNode(node)).module;
      const textWidth = ctx.measureText(label2).width;
      const depthPx = node.depth * kDepthIndentPx;
      const totalWidth = textWidth + depthPx + kHorizontalPadding;
      if (totalWidth > maxWidth) maxWidth = totalWidth;
    }
    return Math.min(kMaxWidth, Math.max(kMinWidth, Math.ceil(maxWidth)));
  }, [outlineNodes, font]);
}
function labelForOutlineNode(node) {
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
const EventPaddingNode = {
  id: "padding",
  event: {
    event: "info",
    source: "",
    data: "",
    timestamp: "",
    pending: false,
    working_start: 0,
    span_id: null,
    uuid: null,
    metadata: null
  },
  depth: 0,
  children: []
};
const TranscriptOutline = ({
  eventNodes,
  defaultCollapsedIds,
  running,
  className,
  scrollRef,
  style,
  onHasNodesChange,
  onWidthChange
}) => {
  const id = "transcript-tree";
  const listHandle = reactExports.useRef(null);
  const { getRestoreState } = useVirtuosoState(listHandle, id);
  const { getEventUrl } = useTranscriptNavigation();
  const collapsedEvents = useStore((state) => state.transcriptCollapsedEvents);
  const setCollapsedEvents = useStore(
    (state) => state.setTranscriptCollapsedEvents
  );
  const selectedOutlineId = useStore((state) => state.transcriptOutlineId);
  const setSelectedOutlineId = useStore(
    (state) => state.setTranscriptOutlineId
  );
  const sampleDetailNavigation = { event: void 0 };
  const isProgrammaticScrolling = reactExports.useRef(false);
  reactExports.useRef(null);
  reactExports.useRef(0);
  reactExports.useEffect(() => {
  }, [sampleDetailNavigation.event, setSelectedOutlineId, scrollRef]);
  const outlineNodeList = reactExports.useMemo(() => {
    const nodeList = flatTree(
      eventNodes,
      (collapsedEvents ? collapsedEvents[kTranscriptOutlineCollapseScope] : void 0) || defaultCollapsedIds,
      [
        // Strip specific nodes
        removeNodeVisitor("logger"),
        removeNodeVisitor("info"),
        removeNodeVisitor("state"),
        removeNodeVisitor("store"),
        removeNodeVisitor("approval"),
        removeNodeVisitor("input"),
        removeNodeVisitor("sandbox"),
        // Strip the sandbox wrapper (and children)
        removeStepSpanNameVisitor(kSandboxSignalName),
        // Remove child events for scorers
        noScorerChildren()
      ]
    );
    return collapseScoring(collapseTurns(makeTurns(nodeList)));
  }, [eventNodes, collapsedEvents, defaultCollapsedIds]);
  const hasOutlineNodes = outlineNodeList.length > 0;
  reactExports.useEffect(() => {
    onHasNodesChange?.(hasOutlineNodes);
  }, [hasOutlineNodes, onHasNodesChange]);
  const outlineWidth = useOutlineWidth(outlineNodeList);
  reactExports.useEffect(() => {
    onWidthChange?.(outlineWidth);
  }, [outlineWidth, onWidthChange]);
  const allNodesList = reactExports.useMemo(() => {
    return flatTree(eventNodes, null);
  }, [eventNodes]);
  const elementIds = allNodesList.map((node) => node.id);
  const findNearestOutlineAbove = reactExports.useCallback(
    (targetId) => {
      const targetIndex = allNodesList.findIndex(
        (node) => node.id === targetId
      );
      if (targetIndex === -1) return null;
      const outlineIds = new Set(outlineNodeList.map((node) => node.id));
      for (let i = targetIndex; i >= 0; i--) {
        const node = allNodesList[i];
        if (node !== void 0 && node.id) {
          if (outlineIds.has(node.id)) {
            return node;
          }
        }
      }
      return null;
    },
    [allNodesList, outlineNodeList]
  );
  useScrollTrack(
    elementIds,
    (id2) => {
      if (!isProgrammaticScrolling.current) {
        const parentNode = findNearestOutlineAbove(id2);
        if (parentNode) {
          setSelectedOutlineId(parentNode.id);
        }
      }
    },
    scrollRef
  );
  reactExports.useEffect(() => {
    if (!collapsedEvents && Object.keys(defaultCollapsedIds).length > 0) {
      setCollapsedEvents(kTranscriptOutlineCollapseScope, defaultCollapsedIds);
    }
  }, [defaultCollapsedIds, collapsedEvents, setCollapsedEvents]);
  const renderRow = reactExports.useCallback(
    (index, node) => {
      if (node === EventPaddingNode) {
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(styles$2.eventPadding),
            style: { height: "2em" }
          },
          node.id
        );
      } else {
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          OutlineRow,
          {
            collapseScope: kTranscriptOutlineCollapseScope,
            node,
            running: running && index === outlineNodeList.length - 1,
            selected: selectedOutlineId ? selectedOutlineId === node.id : index === 0,
            getEventUrl,
            onSelect: setSelectedOutlineId
          },
          node.id
        );
      }
    },
    [
      outlineNodeList,
      running,
      selectedOutlineId,
      getEventUrl,
      setSelectedOutlineId
    ]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    Yr,
    {
      ref: listHandle,
      customScrollParent: scrollRef?.current ? scrollRef.current : void 0,
      id,
      style: { ...style },
      data: [...outlineNodeList, EventPaddingNode],
      defaultItemHeight: 50,
      itemContent: renderRow,
      atBottomThreshold: 30,
      increaseViewportBy: { top: 300, bottom: 300 },
      overscan: {
        main: 10,
        reverse: 10
      },
      className: clsx(className, "transcript-outline"),
      skipAnimationFrameInResizeObserver: true,
      restoreStateFrom: getRestoreState(),
      tabIndex: 0
    }
  );
};
const GAP_THRESHOLD_MS = 3e5;
const GAP_PERCENT = 0;
const MAX_TOTAL_GAP_PERCENT = 0;
function createIdentityMapping(viewStart, viewEnd) {
  const startMs = viewStart.getTime();
  const endMs = viewEnd.getTime();
  const range = endMs - startMs;
  return {
    toPercent(timestamp) {
      if (range <= 0) return 0;
      const offset = timestamp.getTime() - startMs;
      return Math.max(0, Math.min(100, offset / range * 100));
    },
    hasCompression: false,
    gaps: []
  };
}
function computeTimeMapping(node) {
  if (node.idleTime === 0) {
    return createIdentityMapping(node.startTime, node.endTime);
  }
  const nodeStartMs = node.startTime.getTime();
  const nodeEndMs = node.endTime.getTime();
  const nodeRange = nodeEndMs - nodeStartMs;
  if (nodeRange <= 0) {
    return createIdentityMapping(node.startTime, node.endTime);
  }
  const intervals = extractIntervals(node.content);
  if (intervals.length === 0) {
    return createIdentityMapping(node.startTime, node.endTime);
  }
  const activeRegions = mergeIntervals(intervals);
  const rawGaps = findGaps(nodeStartMs, nodeEndMs, activeRegions);
  if (rawGaps.length === 0) {
    return createIdentityMapping(node.startTime, node.endTime);
  }
  const totalActiveMs = activeRegions.reduce(
    (sum, r) => sum + (r.endMs - r.startMs),
    0
  );
  let gapPercentEach = GAP_PERCENT;
  const totalGapPercent = rawGaps.length * gapPercentEach;
  if (totalGapPercent > MAX_TOTAL_GAP_PERCENT) {
    gapPercentEach = MAX_TOTAL_GAP_PERCENT / rawGaps.length;
  }
  const actualTotalGapPercent = rawGaps.length * gapPercentEach;
  const activePercent = 100 - actualTotalGapPercent;
  const segments = [];
  const gapRegions = [];
  let currentPercent = 0;
  let gapIdx = 0;
  if (rawGaps.length > 0 && rawGaps[0].startMs === nodeStartMs) {
    const gap = rawGaps[0];
    const percentEnd = currentPercent + gapPercentEach;
    segments.push({
      startMs: gap.startMs,
      endMs: gap.endMs,
      percentStart: currentPercent,
      percentEnd
    });
    gapRegions.push({
      startMs: gap.startMs,
      endMs: gap.endMs,
      durationMs: gap.endMs - gap.startMs,
      percentStart: currentPercent,
      percentEnd
    });
    currentPercent = percentEnd;
    gapIdx = 1;
  }
  for (let i = 0; i < activeRegions.length; i++) {
    const region = activeRegions[i];
    const regionDurationMs = region.endMs - region.startMs;
    const regionPercent = totalActiveMs > 0 ? regionDurationMs / totalActiveMs * activePercent : activePercent / activeRegions.length;
    const percentEnd = currentPercent + regionPercent;
    segments.push({
      startMs: region.startMs,
      endMs: region.endMs,
      percentStart: currentPercent,
      percentEnd
    });
    currentPercent = percentEnd;
    if (gapIdx < rawGaps.length) {
      const gap = rawGaps[gapIdx];
      if (gap.startMs >= region.endMs - 1) {
        const gapPercentEnd = currentPercent + gapPercentEach;
        segments.push({
          startMs: gap.startMs,
          endMs: gap.endMs,
          percentStart: currentPercent,
          percentEnd: gapPercentEnd
        });
        gapRegions.push({
          startMs: gap.startMs,
          endMs: gap.endMs,
          durationMs: gap.endMs - gap.startMs,
          percentStart: currentPercent,
          percentEnd: gapPercentEnd
        });
        currentPercent = gapPercentEnd;
        gapIdx++;
      }
    }
  }
  const frozenSegments = segments;
  return {
    toPercent(timestamp) {
      const ms = timestamp.getTime();
      if (ms <= nodeStartMs) return 0;
      if (ms >= nodeEndMs) return 100;
      const seg = findSegment(frozenSegments, ms);
      if (!seg) return 0;
      const segRange = seg.endMs - seg.startMs;
      if (segRange <= 0) return seg.percentStart;
      const t = (ms - seg.startMs) / segRange;
      return seg.percentStart + t * (seg.percentEnd - seg.percentStart);
    },
    hasCompression: true,
    gaps: gapRegions
  };
}
function computeActiveTime(mapping, startMs, endMs) {
  const wallClockMs = endMs - startMs;
  let gapMs = 0;
  for (const gap of mapping.gaps) {
    const overlapStart = Math.max(gap.startMs, startMs);
    const overlapEnd = Math.min(gap.endMs, endMs);
    if (overlapEnd > overlapStart) {
      gapMs += overlapEnd - overlapStart;
    }
  }
  return Math.max(0, (wallClockMs - gapMs) / 1e3);
}
function extractIntervals(content) {
  const intervals = [];
  for (const item of content) {
    if (item.type === "event") {
      intervals.push({
        startMs: item.startTime.getTime(),
        endMs: item.endTime.getTime()
      });
    } else {
      const childIntervals = extractIntervals(item.content);
      if (childIntervals.length > 0) {
        intervals.push(...childIntervals);
      } else {
        intervals.push({
          startMs: item.startTime.getTime(),
          endMs: item.endTime.getTime()
        });
      }
    }
  }
  return intervals;
}
function mergeIntervals(intervals) {
  if (intervals.length === 0) return [];
  const sorted = [...intervals].sort((a, b) => a.startMs - b.startMs);
  const merged = [{ ...sorted[0] }];
  for (let i = 1; i < sorted.length; i++) {
    const current = sorted[i];
    const last = merged[merged.length - 1];
    if (current.startMs <= last.endMs) {
      last.endMs = Math.max(last.endMs, current.endMs);
    } else {
      merged.push({ ...current });
    }
  }
  return merged;
}
function findGaps(nodeStartMs, nodeEndMs, activeRegions) {
  const gaps = [];
  if (activeRegions.length > 0) {
    const firstStart = activeRegions[0].startMs;
    if (firstStart - nodeStartMs > GAP_THRESHOLD_MS) {
      gaps.push({ startMs: nodeStartMs, endMs: firstStart });
    }
  }
  for (let i = 1; i < activeRegions.length; i++) {
    const prevEnd = activeRegions[i - 1].endMs;
    const nextStart = activeRegions[i].startMs;
    if (nextStart - prevEnd > GAP_THRESHOLD_MS) {
      gaps.push({ startMs: prevEnd, endMs: nextStart });
    }
  }
  if (activeRegions.length > 0) {
    const lastEnd = activeRegions[activeRegions.length - 1].endMs;
    if (nodeEndMs - lastEnd > GAP_THRESHOLD_MS) {
      gaps.push({ startMs: lastEnd, endMs: nodeEndMs });
    }
  }
  return gaps;
}
function findSegment(segments, ms) {
  let lo = 0;
  let hi = segments.length - 1;
  while (lo <= hi) {
    const mid = lo + hi >>> 1;
    const seg = segments[mid];
    if (ms < seg.startMs) {
      hi = mid - 1;
    } else if (ms > seg.endMs) {
      lo = mid + 1;
    } else {
      return seg;
    }
  }
  if (lo < segments.length) return segments[lo];
  if (hi >= 0) return segments[hi];
  return null;
}
const container = "_container_t8wdo_3";
const stableLabel = "_stableLabel_t8wdo_17";
const alignRight = "_alignRight_t8wdo_32";
const alignLeft = "_alignLeft_t8wdo_36";
const hidden = "_hidden_t8wdo_40";
const minimap = "_minimap_t8wdo_44";
const track = "_track_t8wdo_52";
const selectionRegion = "_selectionRegion_t8wdo_69";
const regionFill = "_regionFill_t8wdo_78";
const marker$1 = "_marker_t8wdo_91";
const markerLeft = "_markerLeft_t8wdo_102";
const markerRight = "_markerRight_t8wdo_106";
const sectionTime = "_sectionTime_t8wdo_111";
const sectionTimePill = "_sectionTimePill_t8wdo_123";
const styles$1 = {
  container,
  stableLabel,
  alignRight,
  alignLeft,
  hidden,
  minimap,
  track,
  selectionRegion,
  regionFill,
  marker: marker$1,
  markerLeft,
  markerRight,
  sectionTime,
  sectionTimePill
};
const TimelineMinimap = ({
  root,
  selection,
  mapping
}) => {
  const [showTokens, setShowTokens] = useProperty(
    "timeline",
    "minimapShowTokens",
    { defaultValue: false, cleanup: false }
  );
  const isTokenMode = !!showTokens;
  const toggle2 = reactExports.useCallback(
    (e) => {
      e.stopPropagation();
      setShowTokens(!isTokenMode);
    },
    [isTokenMode, setShowTokens]
  );
  const bar = selection ? computeBarPosition(
    selection.startTime,
    selection.endTime,
    root.startTime,
    root.endTime
  ) : null;
  const showRegion = bar !== null;
  const useShortFormat = bar !== null && bar.width <= 15;
  const hasCompression = mapping?.hasCompression ?? false;
  const timeRightLabel = hasCompression && mapping ? formatTime(
    computeActiveTime(
      mapping,
      root.startTime.getTime(),
      root.endTime.getTime()
    )
  ) : formatDuration(root.startTime, root.endTime);
  const tokenRightLabel = formatTokenCount(root.totalTokens);
  const computeSectionLabel = () => {
    if (!selection) return "";
    if (isTokenMode) return formatTokenCount(selection.totalTokens);
    if (hasCompression && mapping) {
      return formatTime(
        computeActiveTime(
          mapping,
          selection.startTime.getTime(),
          selection.endTime.getTime()
        )
      );
    }
    return useShortFormat ? formatDurationShort(selection.startTime, selection.endTime) : formatDuration(selection.startTime, selection.endTime);
  };
  const sectionLabel = computeSectionLabel();
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$1.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(styles$1.stableLabel, styles$1.alignRight),
        onClick: toggle2,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: isTokenMode ? styles$1.hidden : void 0, children: "time" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: isTokenMode ? void 0 : styles$1.hidden, children: "tokens" })
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$1.minimap, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.track }),
      showRegion && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: styles$1.selectionRegion,
          style: {
            left: `${bar.left + bar.width / 2}%`,
            width: `${bar.width}%`
          },
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.regionFill }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$1.marker, styles$1.markerLeft) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$1.marker, styles$1.markerRight) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.sectionTime, children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.sectionTimePill, onClick: toggle2, children: sectionLabel }) })
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(styles$1.stableLabel, styles$1.alignLeft),
        onClick: toggle2,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: isTokenMode ? styles$1.hidden : void 0, children: timeRightLabel }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: isTokenMode ? void 0 : styles$1.hidden, children: tokenRightLabel })
        ]
      }
    )
  ] });
};
const swimlane = "_swimlane_12tiy_1";
const pinnedSection = "_pinnedSection_12tiy_17";
const scrollSection = "_scrollSection_12tiy_25";
const collapsibleSection = "_collapsibleSection_12tiy_40";
const collapsibleCollapsed = "_collapsibleCollapsed_12tiy_53";
const noAnimation = "_noAnimation_12tiy_60";
const swimlaneSticky = "_swimlaneSticky_12tiy_65";
const collapsibleInner = "_collapsibleInner_12tiy_72";
const collapseToggle = "_collapseToggle_12tiy_82";
const row = "_row_12tiy_110";
const label = "_label_12tiy_116";
const labelChild = "_labelChild_12tiy_128";
const labelSelected = "_labelSelected_12tiy_132";
const barArea = "_barArea_12tiy_138";
const barInner = "_barInner_12tiy_144";
const fill = "_fill_12tiy_150";
const fillParent = "_fillParent_12tiy_168";
const fillSelected = "_fillSelected_12tiy_172";
const marker = "_marker_12tiy_184";
const markerError = "_markerError_12tiy_204";
const markerCompaction = "_markerCompaction_12tiy_225";
const markerBranch = "_markerBranch_12tiy_237";
const branchPopover = "_branchPopover_12tiy_244";
const branchEntry = "_branchEntry_12tiy_250";
const branchLabel = "_branchLabel_12tiy_270";
const branchMeta = "_branchMeta_12tiy_274";
const breadcrumbRow = "_breadcrumbRow_12tiy_286";
const breadcrumbBack = "_breadcrumbBack_12tiy_296";
const breadcrumbGroup = "_breadcrumbGroup_12tiy_319";
const breadcrumbLink = "_breadcrumbLink_12tiy_326";
const breadcrumbCurrent = "_breadcrumbCurrent_12tiy_339";
const breadcrumbSelection = "_breadcrumbSelection_12tiy_353";
const breadcrumbDivider = "_breadcrumbDivider_12tiy_367";
const tokens = "_tokens_12tiy_375";
const styles = {
  swimlane,
  pinnedSection,
  scrollSection,
  collapsibleSection,
  collapsibleCollapsed,
  noAnimation,
  swimlaneSticky,
  collapsibleInner,
  collapseToggle,
  row,
  label,
  labelChild,
  labelSelected,
  barArea,
  barInner,
  fill,
  fillParent,
  fillSelected,
  marker,
  markerError,
  markerCompaction,
  markerBranch,
  branchPopover,
  branchEntry,
  branchLabel,
  branchMeta,
  breadcrumbRow,
  breadcrumbBack,
  breadcrumbGroup,
  breadcrumbLink,
  breadcrumbCurrent,
  breadcrumbSelection,
  breadcrumbDivider,
  tokens
};
function parseSelected(selected2) {
  if (!selected2) return null;
  return parsePathSegment(selected2);
}
function isSpanSelected(layout, spanIndex, parsed) {
  if (!parsed) return false;
  if (layout.name.toLowerCase() !== parsed.name.toLowerCase()) return false;
  if (layout.spans.length === 1) {
    return true;
  }
  const selectedIdx = parsed.spanIndex ?? 1;
  return selectedIdx === spanIndex + 1;
}
const MARKER_ICONS = {
  error: { icon: ApplicationIcons.error, tooltip: "Error event" },
  compaction: {
    icon: ApplicationIcons.compactionMarker,
    tooltip: "Context compaction"
  },
  branch: { icon: ApplicationIcons.fork, tooltip: "View branches" }
};
const TimelineSwimLanes = ({
  layouts,
  timeline,
  header,
  isSticky,
  forceCollapsed,
  noAnimation: noAnimation2,
  onMarkerNavigate
}) => {
  const {
    node,
    selected: selected2,
    select: onSelect,
    drillDown: onDrillDown,
    goUp: onGoUp
  } = timeline;
  const parsedSelection = reactExports.useMemo(() => parseSelected(selected2), [selected2]);
  const [collapsed, setCollapsed] = useProperty(
    "timeline",
    "swimlanesCollapsed",
    { cleanup: false }
  );
  const isFlat = layouts.length <= 1;
  const isCollapsed = forceCollapsed ? collapsed !== false : collapsed ?? isFlat;
  const toggleCollapsed = reactExports.useCallback(() => {
    setCollapsed(!isCollapsed);
  }, [isCollapsed, setCollapsed]);
  const [branchPopover2, setBranchPopover] = reactExports.useState(null);
  const handleBranchHover = reactExports.useCallback(
    (forkedAt, element) => {
      setBranchPopover({ forkedAt, element });
    },
    []
  );
  const handleBranchLeave = reactExports.useCallback(() => {
    setBranchPopover(null);
  }, []);
  const handleBranchSelect = reactExports.useCallback(
    (branchSegment) => {
      const lookup = findBranchesByForkedAt(
        node,
        branchPopover2?.forkedAt ?? ""
      );
      setBranchPopover(null);
      if (lookup && lookup.ownerPath.length > 0) {
        const fullSegment = [...lookup.ownerPath, branchSegment].join("/");
        onDrillDown(fullSegment);
      } else {
        onDrillDown(branchSegment);
      }
    },
    [onDrillDown, node, branchPopover2?.forkedAt]
  );
  const handleKeyDown = reactExports.useCallback(
    (e) => {
      const rowNames = layouts.map((l) => l.name);
      const currentRowName = parsedSelection?.name.toLowerCase() ?? null;
      const currentIndex = currentRowName ? rowNames.findIndex((n) => n.toLowerCase() === currentRowName) : -1;
      switch (e.key) {
        case "ArrowDown": {
          e.preventDefault();
          const next = currentIndex < rowNames.length - 1 ? currentIndex + 1 : currentIndex;
          const name = rowNames[next];
          if (name !== void 0) onSelect(name);
          break;
        }
        case "ArrowUp": {
          e.preventDefault();
          const prev = currentIndex > 0 ? currentIndex - 1 : 0;
          const name = rowNames[prev];
          if (name !== void 0) onSelect(name);
          break;
        }
        case "Enter": {
          e.preventDefault();
          if (parsedSelection) {
            const layout = layouts.find(
              (l) => l.name.toLowerCase() === parsedSelection.name.toLowerCase()
            );
            if (layout && layout.spans.some((s) => s.drillable)) {
              onDrillDown(layout.name, parsedSelection.spanIndex ?? void 0);
            }
          }
          break;
        }
        case "Escape": {
          e.preventDefault();
          if (branchPopover2) {
            setBranchPopover(null);
          } else {
            onGoUp();
          }
          break;
        }
      }
    },
    [layouts, parsedSelection, onSelect, onDrillDown, onGoUp, branchPopover2]
  );
  const branchLookup = reactExports.useMemo(() => {
    if (!branchPopover2) return null;
    return findBranchesByForkedAt(node, branchPopover2.forkedAt);
  }, [branchPopover2, node]);
  const parentRow = layouts[0];
  const childRows = layouts.slice(1);
  const renderRow = (layout, rowIndex, displayName) => /* @__PURE__ */ jsxRuntimeExports.jsx(
    SwimlaneRow,
    {
      layout,
      displayName,
      parsedSelection,
      onSelect: (spanIndex) => {
        if (layout.spans.length > 1) {
          onSelect(layout.name, spanIndex + 1);
        } else {
          onSelect(layout.name);
        }
      },
      onDrillDown: (spanIndex) => onDrillDown(
        layout.name,
        layout.spans.length > 1 ? spanIndex + 1 : void 0
      ),
      onBranchHover: handleBranchHover,
      onBranchLeave: handleBranchLeave,
      onMarkerNavigate
    },
    `${layout.name}-${rowIndex}`
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: clsx(styles.swimlane, isSticky && styles.swimlaneSticky),
      tabIndex: 0,
      onKeyDown: handleKeyDown,
      role: "grid",
      "aria-label": "Timeline swimlane",
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.pinnedSection, children: header && /* @__PURE__ */ jsxRuntimeExports.jsx(BreadcrumbRow, { ...header, selected: selected2, onGoUp }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              styles.collapsibleSection,
              isCollapsed && styles.collapsibleCollapsed,
              noAnimation2 && styles.noAnimation
            ),
            children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.collapsibleInner, children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.pinnedSection, children: parentRow && renderRow(
                parentRow,
                0,
                header?.atRoot && parentRow.name === "solvers" ? "main" : void 0
              ) }),
              childRows.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.scrollSection, children: childRows.map((layout, i) => renderRow(layout, i + 1)) })
            ] })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: styles.collapseToggle,
            onClick: toggleCollapsed,
            title: isCollapsed ? "Expand swimlanes" : "Collapse swimlanes",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              "i",
              {
                className: isCollapsed ? ApplicationIcons.expand.down : ApplicationIcons.collapse.up
              }
            )
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          BranchPopover,
          {
            isOpen: branchPopover2 !== null && branchLookup !== null,
            anchor: branchPopover2?.element ?? null,
            branches: branchLookup?.branches ?? [],
            onSelect: handleBranchSelect,
            onClose: () => setBranchPopover(null)
          }
        )
      ]
    }
  );
};
const SwimlaneRow = ({
  layout,
  displayName,
  parsedSelection,
  onSelect,
  onDrillDown,
  onBranchHover,
  onBranchLeave,
  onMarkerNavigate
}) => {
  const hasSelectedSpan = layout.spans.some(
    (_, i) => isSpanSelected(layout, i, parsedSelection)
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.row, role: "row", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: clsx(
          styles.label,
          !layout.isParent && styles.labelChild,
          hasSelectedSpan && styles.labelSelected
        ),
        children: displayName ?? layout.name
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.barArea, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.barInner, children: [
      layout.spans.map((span, spanIndex) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        BarFill,
        {
          span,
          isParent: layout.isParent,
          isSelected: isSpanSelected(layout, spanIndex, parsedSelection),
          onSelect: () => onSelect(spanIndex),
          onDrillDown: () => onDrillDown(spanIndex)
        },
        spanIndex
      )),
      layout.markers.map((marker2, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        MarkerGlyph,
        {
          marker: marker2,
          onBranchHover,
          onBranchLeave,
          onMarkerNavigate
        },
        i
      ))
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.tokens, children: formatTokenCount(layout.totalTokens) })
  ] });
};
const BreadcrumbRow = ({
  breadcrumbs,
  atRoot,
  onGoUp,
  onNavigate,
  minimap: minimap2,
  selected: selected2,
  onScrollToTop
}) => {
  const selectedLabel = selected2 ? parsePathSegment(selected2).name : null;
  const lastBreadcrumb = breadcrumbs[breadcrumbs.length - 1];
  const showSelection = selectedLabel !== null && selectedLabel.toLowerCase() !== lastBreadcrumb?.label.toLowerCase();
  const handleNavigate = reactExports.useCallback(
    (path) => {
      onNavigate(path);
      onScrollToTop?.();
    },
    [onNavigate, onScrollToTop]
  );
  const handleGoUp = reactExports.useCallback(() => {
    onGoUp();
    onScrollToTop?.();
  }, [onGoUp, onScrollToTop]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.breadcrumbRow, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        className: styles.breadcrumbBack,
        onClick: handleGoUp,
        disabled: atRoot && !showSelection,
        title: "Go up one level (Escape)",
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.navbar.back })
      }
    ),
    breadcrumbs.map((segment, i) => {
      const isLast = i === breadcrumbs.length - 1;
      const label2 = i === 0 && segment.label === "solvers" ? "main" : segment.label;
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles.breadcrumbGroup, children: [
        i > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles.breadcrumbDivider, children: "›" }),
        isLast && !showSelection ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: styles.breadcrumbCurrent,
            onClick: () => {
              handleNavigate(segment.path);
            },
            children: label2
          }
        ) : /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: styles.breadcrumbLink,
            onClick: () => handleNavigate(segment.path),
            children: label2
          }
        )
      ] }, segment.path + i);
    }),
    showSelection && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles.breadcrumbGroup, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles.breadcrumbDivider, children: "›" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          className: styles.breadcrumbSelection,
          onClick: onScrollToTop,
          children: selectedLabel
        }
      )
    ] }),
    minimap2 && /* @__PURE__ */ jsxRuntimeExports.jsx(TimelineMinimap, { ...minimap2 })
  ] });
};
const BarFill = ({
  span,
  isParent,
  isSelected,
  onSelect,
  onDrillDown
}) => {
  const handleClick = reactExports.useCallback(
    (e) => {
      e.stopPropagation();
      onSelect();
    },
    [onSelect]
  );
  const handleDoubleClick = reactExports.useCallback(
    (e) => {
      e.stopPropagation();
      if (span.drillable) {
        onDrillDown();
      }
    },
    [span.drillable, onDrillDown]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: clsx(
        styles.fill,
        isParent && styles.fillParent,
        isSelected && styles.fillSelected
      ),
      style: {
        left: `${span.bar.left}%`,
        width: `${span.bar.width}%`
      },
      title: span.description ?? void 0,
      onClick: handleClick,
      onDoubleClick: handleDoubleClick
    }
  );
};
const MarkerGlyph = ({
  marker: marker2,
  onBranchHover,
  onBranchLeave,
  onMarkerNavigate
}) => {
  const icon2 = MARKER_ICONS[marker2.kind]?.icon ?? "bi bi-question-circle";
  const kindClass = marker2.kind === "error" ? styles.markerError : marker2.kind === "compaction" ? styles.markerCompaction : styles.markerBranch;
  const handleClick = reactExports.useCallback(
    (e) => {
      if (marker2.kind === "branch") {
        e.stopPropagation();
        onBranchHover(marker2.reference, e.currentTarget);
      } else if (marker2.reference && onMarkerNavigate) {
        e.stopPropagation();
        onMarkerNavigate(marker2.reference);
      }
    },
    [marker2.kind, marker2.reference, onMarkerNavigate, onBranchHover]
  );
  const handleKeyDown = reactExports.useCallback(
    (e) => {
      if (marker2.kind === "branch" && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        e.stopPropagation();
        onBranchHover(marker2.reference, e.currentTarget);
      }
    },
    [marker2.kind, marker2.reference, onBranchHover]
  );
  const handleMouseEnter = reactExports.useCallback(
    (e) => {
      if (marker2.kind === "branch") {
        onBranchHover(marker2.reference, e.currentTarget);
      }
    },
    [marker2.kind, marker2.reference, onBranchHover]
  );
  const handleMouseLeave = reactExports.useCallback(() => {
    if (marker2.kind === "branch") {
      onBranchLeave();
    }
  }, [marker2.kind, onBranchLeave]);
  const isBranch = marker2.kind === "branch";
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "span",
    {
      className: clsx(styles.marker, kindClass),
      style: { left: `${marker2.left}%` },
      title: isBranch ? void 0 : marker2.tooltip,
      onClick: handleClick,
      onKeyDown: isBranch ? handleKeyDown : void 0,
      onMouseEnter: isBranch ? handleMouseEnter : void 0,
      onMouseLeave: isBranch ? handleMouseLeave : void 0,
      tabIndex: isBranch ? 0 : void 0,
      role: isBranch ? "button" : void 0,
      "aria-haspopup": isBranch ? "true" : void 0,
      "aria-label": isBranch ? "Show branches" : void 0,
      children: marker2.kind !== "error" && /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: icon2 })
    }
  );
};
const BranchPopover = ({
  isOpen,
  anchor,
  branches,
  onSelect,
  onClose
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    PopOver,
    {
      id: "branch-popover",
      isOpen,
      setIsOpen: (open) => {
        if (!open) onClose();
      },
      positionEl: anchor,
      placement: "bottom",
      showArrow: true,
      hoverDelay: 0,
      closeOnMouseLeave: true,
      styles: { padding: "4px 0" },
      children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.branchPopover, children: branches.map(({ branch, index }) => {
        const span = createBranchSpan(branch, index);
        const durationSec = (branch.endTime.getTime() - branch.startTime.getTime()) / 1e3;
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            className: styles.branchEntry,
            onClick: () => onSelect(`@branch-${index}`),
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles.branchLabel, children: span.name }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles.branchMeta, children: [
                formatTokenCount(branch.totalTokens),
                " · ",
                formatTime(durationSec)
              ] })
            ]
          },
          `branch-${index}`
        );
      }) })
    }
  );
};
export {
  TimelineSwimLanes as T,
  TranscriptOutline as a,
  computeTimeMapping as c
};
//# sourceMappingURL=TimelineSwimLanes.js.map
