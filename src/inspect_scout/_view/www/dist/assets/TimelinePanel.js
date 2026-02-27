import { j as jsxRuntimeExports, c as clsx, i as useSearchParams, r as reactExports, A as ApplicationIcons } from "./index.js";
import { d as VscodeSingleSelect, e as VscodeOption } from "./VscodeTreeItem.js";
import { j as useProperty, u as useEventNodes, T as TranscriptViewNodes } from "./TranscriptViewNodes.js";
import { T as TranscriptOutline } from "./TranscriptOutline.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { g as formatDuration, a as formatPrettyDecimal, h as formatDurationShort, P as PopOver, e as formatTime } from "./ToolButton.js";
import "./_commonjsHelpers.js";
import "./chunk-DfAF0w94.js";
import "./NoContentsPanel.js";
const pillRow = "_pillRow_1kmry_1";
const pill = "_pill_1kmry_1";
const pillActive = "_pillActive_1kmry_24";
const styles$3 = {
  pillRow,
  pill,
  pillActive
};
const TimelinePills = ({
  timelines,
  activeIndex,
  onSelect
}) => {
  if (timelines.length <= 1) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$3.pillRow, children: timelines.map((tl, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(
    "button",
    {
      className: clsx(styles$3.pill, i === activeIndex && styles$3.pillActive),
      onClick: () => onSelect(i),
      title: tl.description,
      children: tl.name
    },
    i
  )) });
};
function compareByTime(a, b) {
  return a.startTime.getTime() - b.startTime.getTime() || a.endTime.getTime() - b.endTime.getTime();
}
function isSingleSpan(span) {
  return "agent" in span;
}
function isParallelSpan(span) {
  return "agents" in span;
}
function getAgents(span) {
  return isSingleSpan(span) ? [span.agent] : span.agents;
}
const OVERLAP_TOLERANCE_MS = 100;
function spansOverlap(a, b) {
  return a.startTime.getTime() < b.endTime.getTime() + OVERLAP_TOLERANCE_MS && b.startTime.getTime() < a.endTime.getTime() + OVERLAP_TOLERANCE_MS;
}
function groupHasOverlap(spans) {
  for (let i = 0; i < spans.length; i++) {
    for (let j = i + 1; j < spans.length; j++) {
      const a = spans[i];
      const b = spans[j];
      if (a && b && spansOverlap(a, b)) {
        return true;
      }
    }
  }
  return false;
}
function computeSwimlaneRows(node) {
  const parentRow = buildParentRow(node);
  const children = node.content.filter(
    (item) => item.type === "span" && !item.utility
  );
  if (children.length === 0) {
    return [parentRow];
  }
  const groups = groupByName(children);
  const childRows = [];
  for (const [displayName, spans] of groups) {
    const row2 = buildRowFromGroup(displayName, spans);
    if (row2) {
      childRows.push(row2);
    }
  }
  childRows.sort(compareByTime);
  return [parentRow, ...childRows];
}
function buildParentRow(node) {
  return {
    name: node.name,
    spans: [{ agent: node }],
    totalTokens: node.totalTokens,
    startTime: node.startTime,
    endTime: node.endTime
  };
}
function groupByName(spans) {
  const map = /* @__PURE__ */ new Map();
  for (const span of spans) {
    const key = span.name.toLowerCase();
    const existing = map.get(key);
    if (existing) {
      existing.spans.push(span);
    } else {
      map.set(key, { displayName: span.name, spans: [span] });
    }
  }
  return Array.from(map.values()).map((g) => [g.displayName, g.spans]);
}
function buildRowFromGroup(displayName, spans) {
  const sorted = [...spans].sort(compareByTime);
  const first = sorted[0];
  if (!first) {
    return null;
  }
  let rowSpans;
  if (sorted.length === 1) {
    rowSpans = [{ agent: first }];
  } else if (groupHasOverlap(sorted)) {
    rowSpans = [{ agents: sorted }];
  } else {
    rowSpans = sorted.map((span) => ({ agent: span }));
  }
  const startTime = first.startTime;
  const endTime = sorted.reduce(
    (latest, span) => span.endTime.getTime() > latest.getTime() ? span.endTime : latest,
    first.endTime
  );
  const totalTokens = sorted.reduce((sum, span) => sum + span.totalTokens, 0);
  return {
    name: displayName,
    spans: rowSpans,
    totalTokens,
    startTime,
    endTime
  };
}
const kPathParam = "path";
const kSelectedParam = "selected";
function parsePathSegment(segment) {
  const match = /^(.+)-(\d+)$/.exec(segment);
  if (match) {
    const name = match[1];
    const index = parseInt(match[2], 10);
    if (index >= 1) {
      return { name, spanIndex: index };
    }
  }
  return { name: segment, spanIndex: null };
}
function resolvePath(timeline, pathString) {
  if (!pathString) return timeline.root;
  const segments = pathString.split("/").filter((s) => s.length > 0);
  if (segments.length === 0) return timeline.root;
  let current = timeline.root;
  for (const segment of segments) {
    const branchSpan = resolveBranchSegment(current, segment);
    if (branchSpan) {
      current = branchSpan;
      continue;
    }
    const { name, spanIndex } = parsePathSegment(segment);
    const child = findChildSpan(current, name, spanIndex);
    if (!child) return null;
    current = child;
  }
  return current;
}
function buildBreadcrumbs(pathString, timeline) {
  const crumbs = [{ label: timeline.root.name, path: "" }];
  if (!pathString) return crumbs;
  const segments = pathString.split("/").filter((s) => s.length > 0);
  let current = timeline.root;
  for (let i = 0; i < segments.length; i++) {
    const segment = segments[i];
    const path = segments.slice(0, i + 1).join("/");
    if (current) {
      const branchSpan = resolveBranchSegment(current, segment);
      if (branchSpan) {
        crumbs.push({ label: branchSpan.name, path });
        current = branchSpan;
      } else {
        const { name, spanIndex } = parsePathSegment(segment);
        const child = findChildSpan(current, name, spanIndex);
        if (child) {
          crumbs.push({ label: child.name, path });
          current = child;
        } else {
          crumbs.push({ label: segment, path });
          current = null;
        }
      }
    } else {
      crumbs.push({ label: segment, path });
    }
  }
  return crumbs;
}
function findChildSpan(parent, name, spanIndex) {
  const lowerName = name.toLowerCase();
  const matches = [];
  for (const item of parent.content) {
    if (item.type === "span" && item.name.toLowerCase() === lowerName) {
      matches.push(item);
    }
  }
  if (matches.length === 0) return null;
  if (spanIndex !== null) {
    return matches[spanIndex - 1] ?? null;
  }
  if (matches.length === 1) {
    return matches[0];
  }
  return createParallelContainer(matches);
}
function createParallelContainer(agents) {
  const displayName = agents[0].name;
  const startTime = agents.reduce(
    (min, a) => a.startTime.getTime() < min.getTime() ? a.startTime : min,
    agents[0].startTime
  );
  const endTime = agents.reduce(
    (max, a) => a.endTime.getTime() > max.getTime() ? a.endTime : max,
    agents[0].endTime
  );
  const totalTokens = agents.reduce((sum, a) => sum + a.totalTokens, 0);
  const sorted = [...agents].sort(compareByTime);
  const numberedAgents = sorted.map((agent, i) => ({
    ...agent,
    name: `${displayName} ${i + 1}`
  }));
  return {
    type: "span",
    id: `parallel-${displayName.toLowerCase()}`,
    name: displayName,
    spanType: "agent",
    content: numberedAgents,
    branches: [],
    utility: false,
    startTime,
    endTime,
    totalTokens
  };
}
const BRANCH_PREFIX = "@branch-";
function resolveBranchSegment(parent, segment) {
  if (!segment.startsWith(BRANCH_PREFIX)) return null;
  const indexStr = segment.slice(BRANCH_PREFIX.length);
  const index = parseInt(indexStr, 10);
  if (isNaN(index) || index < 1) return null;
  const branch = parent.branches[index - 1];
  if (!branch) return null;
  return createBranchSpan(branch, index);
}
function createBranchSpan(branch, index) {
  const label2 = deriveBranchLabel(branch, index);
  const childSpans = branch.content.filter(
    (item) => item.type === "span"
  );
  if (childSpans.length === 1) {
    return {
      ...childSpans[0],
      name: `↳ ${childSpans[0].name}`
    };
  }
  return {
    type: "span",
    id: `branch-${branch.forkedAt}-${index}`,
    name: `↳ ${label2}`,
    spanType: "branch",
    content: branch.content,
    branches: [],
    utility: false,
    startTime: branch.startTime,
    endTime: branch.endTime,
    totalTokens: branch.totalTokens
  };
}
function deriveBranchLabel(branch, index) {
  for (const item of branch.content) {
    if (item.type === "span") return item.name;
  }
  return `Branch ${index}`;
}
function findBranchesByForkedAt(node, forkedAt, pathSoFar = []) {
  const matches = [];
  for (let i = 0; i < node.branches.length; i++) {
    const branch = node.branches[i];
    if (branch.forkedAt === forkedAt) {
      matches.push({ branch, index: i + 1 });
    }
  }
  if (matches.length > 0) {
    return { owner: node, ownerPath: pathSoFar, branches: matches };
  }
  for (const item of node.content) {
    if (item.type === "span") {
      const found = findBranchesByForkedAt(item, forkedAt, [
        ...pathSoFar,
        item.name.toLowerCase()
      ]);
      if (found) return found;
    }
  }
  return null;
}
function useTimeline(timeline) {
  const [searchParams, setSearchParams] = useSearchParams();
  const pathString = searchParams.get(kPathParam) ?? "";
  const selectedParam = searchParams.get(kSelectedParam) ?? null;
  const resolved = reactExports.useMemo(
    () => resolvePath(timeline, pathString),
    [timeline, pathString]
  );
  const node = reactExports.useMemo(() => resolved ?? timeline.root, [timeline, resolved]);
  const rows = reactExports.useMemo(() => computeSwimlaneRows(node), [node]);
  const selected = reactExports.useMemo(() => {
    if (selectedParam !== null) return selectedParam;
    if (node.id.startsWith("parallel-") && rows.length > 1) {
      return rows[1].name;
    }
    return rows[0]?.name ?? null;
  }, [selectedParam, node.id, rows]);
  const breadcrumbs = reactExports.useMemo(
    () => buildBreadcrumbs(pathString, timeline),
    [pathString, timeline]
  );
  const drillDown = reactExports.useCallback(
    (name, spanIndex) => {
      const segment = spanIndex ? `${name}-${spanIndex}` : name;
      const newPath = pathString ? `${pathString}/${segment}` : segment;
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set(kPathParam, newPath);
          next.delete(kSelectedParam);
          return next;
        },
        { replace: true }
      );
    },
    [pathString, setSearchParams]
  );
  const goUp = reactExports.useCallback(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (pathString) {
          const segments = pathString.split("/");
          segments.pop();
          const newPath = segments.join("/");
          if (newPath) {
            next.set(kPathParam, newPath);
          } else {
            next.delete(kPathParam);
          }
        }
        next.delete(kSelectedParam);
        return next;
      },
      { replace: true }
    );
  }, [pathString, setSearchParams]);
  const navigateTo = reactExports.useCallback(
    (path) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (path) {
            next.set(kPathParam, path);
          } else {
            next.delete(kPathParam);
          }
          next.delete(kSelectedParam);
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );
  const select = reactExports.useCallback(
    (name, spanIndex) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (name) {
            const value = spanIndex ? `${name}-${spanIndex}` : name;
            next.set(kSelectedParam, value);
          } else {
            next.delete(kSelectedParam);
          }
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );
  return {
    node,
    rows,
    breadcrumbs,
    selected,
    drillDown,
    goUp,
    navigateTo,
    select
  };
}
function isErrorEvent(event) {
  if (event.event === "tool") {
    return event.error !== null;
  }
  if (event.event === "model") {
    return event.error !== null || event.output.error !== null;
  }
  return false;
}
function isCompactionEvent(event) {
  return event.event === "compaction";
}
function errorTooltip(event) {
  if (event.event === "tool") {
    const msg = event.error?.message ?? "Unknown error";
    return `Error (${event.function}): ${msg}`;
  }
  if (event.event === "model") {
    const msg = (typeof event.error === "string" ? event.error : null) ?? (typeof event.output.error === "string" ? event.output.error : null) ?? "Unknown error";
    return `Error (${event.model}): ${msg}`;
  }
  return "Error";
}
function collectMarkers(node, depth) {
  const markers = [];
  collectEventMarkers(node, depth, 0, markers);
  collectBranchMarkers(node, markers);
  markers.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  return markers;
}
function collectEventMarkers(node, depth, currentLevel, markers) {
  for (const item of node.content) {
    if (item.type === "event") {
      addEventMarker(item, markers);
    } else if (item.type === "span" && shouldDescend(depth, currentLevel)) {
      collectEventMarkers(item, depth, currentLevel + 1, markers);
    }
  }
}
function shouldDescend(depth, currentLevel) {
  if (depth === "direct") return false;
  if (depth === "children") return currentLevel === 0;
  return true;
}
function addEventMarker(eventNode, markers) {
  const event = eventNode.event;
  const uuid = event.uuid;
  if (isErrorEvent(event)) {
    markers.push({
      kind: "error",
      timestamp: eventNode.startTime,
      reference: uuid ?? "",
      tooltip: errorTooltip(event)
    });
  } else if (isCompactionEvent(event)) {
    const ce = event;
    const before = ce.tokens_before?.toLocaleString() ?? "?";
    const after = ce.tokens_after?.toLocaleString() ?? "?";
    markers.push({
      kind: "compaction",
      timestamp: eventNode.startTime,
      reference: uuid ?? "",
      tooltip: `Context compaction: ${before} → ${after} tokens`
    });
  }
}
function collectBranchMarkers(node, markers) {
  const groups = /* @__PURE__ */ new Map();
  for (const branch of node.branches) {
    const existing = groups.get(branch.forkedAt);
    if (existing) {
      existing.push(branch);
    } else {
      groups.set(branch.forkedAt, [branch]);
    }
  }
  for (const [forkedAt, branches] of groups) {
    const timestamp = resolveForkedAtTimestamp(node, forkedAt);
    if (timestamp) {
      markers.push({
        kind: "branch",
        timestamp,
        reference: forkedAt,
        tooltip: branchTooltip(branches)
      });
    }
  }
}
function branchTooltip(branches) {
  const count = branches.length;
  const totalTokens = branches.reduce((sum, b) => sum + b.totalTokens, 0);
  const tokenStr = formatCompactTokens(totalTokens);
  const earliest = branches.reduce(
    (min, b) => b.startTime < min ? b.startTime : min,
    branches[0].startTime
  );
  const latest = branches.reduce(
    (max, b) => b.endTime > max ? b.endTime : max,
    branches[0].endTime
  );
  const duration = formatDuration(earliest, latest);
  const label2 = count === 1 ? "1 branch" : `${count} branches`;
  return `${label2} (${tokenStr}, ${duration})`;
}
function formatCompactTokens(tokens2) {
  if (tokens2 >= 1e6) {
    return `${formatPrettyDecimal(tokens2 / 1e6)}M tokens`;
  }
  if (tokens2 >= 1e3) {
    return `${formatPrettyDecimal(tokens2 / 1e3)}k tokens`;
  }
  return `${tokens2} tokens`;
}
function resolveForkedAtTimestamp(node, forkedAt) {
  if (!forkedAt) return null;
  for (const item of node.content) {
    if (item.type === "event" && item.event.uuid === forkedAt) {
      return item.startTime;
    }
  }
  return null;
}
function timestampToPercent(timestamp, viewStart, viewEnd) {
  const range = viewEnd.getTime() - viewStart.getTime();
  if (range <= 0) return 0;
  const offset = timestamp.getTime() - viewStart.getTime();
  return Math.max(0, Math.min(100, offset / range * 100));
}
function computeBarPosition(spanStart, spanEnd, viewStart, viewEnd) {
  const left = timestampToPercent(spanStart, viewStart, viewEnd);
  const right = timestampToPercent(spanEnd, viewStart, viewEnd);
  return { left, width: Math.max(0, right - left) };
}
function isDrillable(span) {
  if (isParallelSpan(span)) return true;
  if (isSingleSpan(span)) {
    return span.agent.content.some(
      (item) => item.type === "span" && !item.utility
    );
  }
  return false;
}
function formatTokenCount(tokens2) {
  if (tokens2 >= 1e6) {
    return `${formatPrettyDecimal(tokens2 / 1e6)}M`;
  }
  if (tokens2 >= 1e3) {
    return `${formatPrettyDecimal(tokens2 / 1e3)}k`;
  }
  return String(tokens2);
}
function computeRowLayouts(rows, viewStart, viewEnd, markerDepth) {
  return rows.map((row2, index) => {
    const isParent = index === 0;
    const spans = row2.spans.map((rowSpan) => {
      if (isSingleSpan(rowSpan)) {
        const bar2 = computeBarPosition(
          rowSpan.agent.startTime,
          rowSpan.agent.endTime,
          viewStart,
          viewEnd
        );
        return {
          bar: bar2,
          drillable: !isParent && isDrillable(rowSpan),
          parallelCount: null,
          description: rowSpan.agent.description ?? null
        };
      }
      const agents = rowSpan.agents;
      const earliest = agents.reduce(
        (min, a) => a.startTime.getTime() < min.getTime() ? a.startTime : min,
        agents[0].startTime
      );
      const latest = agents.reduce(
        (max, a) => a.endTime.getTime() > max.getTime() ? a.endTime : max,
        agents[0].endTime
      );
      const bar = computeBarPosition(earliest, latest, viewStart, viewEnd);
      return {
        bar,
        drillable: !isParent,
        parallelCount: agents.length,
        description: null
      };
    });
    const markers = collectRowMarkers(
      row2,
      isParent,
      markerDepth,
      viewStart,
      viewEnd
    );
    const rowParallelCount = spans.length === 1 && spans[0].parallelCount !== null ? spans[0].parallelCount : null;
    return {
      name: row2.name,
      isParent,
      spans,
      markers,
      totalTokens: row2.totalTokens,
      parallelCount: rowParallelCount
    };
  });
}
function collectRowMarkers(row2, isParent, depth, viewStart, viewEnd) {
  const allMarkers = [];
  for (const rowSpan of row2.spans) {
    const agents = getAgents(rowSpan);
    for (const agent of agents) {
      const effectiveDepth = isParent ? depth : "direct";
      const markers = collectMarkers(agent, effectiveDepth);
      for (const m of markers) {
        allMarkers.push({
          left: timestampToPercent(m.timestamp, viewStart, viewEnd),
          kind: m.kind,
          reference: m.reference,
          tooltip: m.tooltip
        });
      }
    }
  }
  allMarkers.sort((a, b) => a.left - b.left);
  return allMarkers;
}
const container$1 = "_container_1s11p_3";
const stableLabel = "_stableLabel_1s11p_17";
const alignRight = "_alignRight_1s11p_32";
const alignLeft = "_alignLeft_1s11p_36";
const hidden = "_hidden_1s11p_40";
const minimap = "_minimap_1s11p_44";
const track = "_track_1s11p_52";
const regionFill = "_regionFill_1s11p_65";
const marker$1 = "_marker_1s11p_76";
const sectionTime = "_sectionTime_1s11p_88";
const sectionTimePill = "_sectionTimePill_1s11p_99";
const styles$2 = {
  container: container$1,
  stableLabel,
  alignRight,
  alignLeft,
  hidden,
  minimap,
  track,
  regionFill,
  marker: marker$1,
  sectionTime,
  sectionTimePill
};
const TimelineMinimap = ({
  root,
  selection
}) => {
  const [showTokens, setShowTokens] = useProperty(
    "timeline",
    "minimapShowTokens",
    { defaultValue: false, cleanup: false }
  );
  const isTokenMode = !!showTokens;
  const toggle = reactExports.useCallback(
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
  const timeRightLabel = formatDuration(root.startTime, root.endTime);
  const tokenRightLabel = formatTokenCount(root.totalTokens);
  const sectionLabel = selection && isTokenMode ? formatTokenCount(selection.totalTokens) : selection ? useShortFormat ? formatDurationShort(selection.startTime, selection.endTime) : formatDuration(selection.startTime, selection.endTime) : "";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$2.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(styles$2.stableLabel, styles$2.alignRight),
        onClick: toggle,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: isTokenMode ? styles$2.hidden : void 0, children: "time" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: isTokenMode ? void 0 : styles$2.hidden, children: "tokens" })
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$2.minimap, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.track }),
      showRegion && /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: styles$2.regionFill,
          style: { left: `${bar.left}%`, width: `${bar.width}%` }
        }
      ),
      showRegion && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.marker, style: { left: `${bar.left}%` } }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: styles$2.marker,
            style: { left: `${bar.left + bar.width}%` }
          }
        )
      ] }),
      showRegion && /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: styles$2.sectionTime,
          style: { left: `${bar.left}%`, width: `${bar.width}%` },
          children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$2.sectionTimePill, onClick: toggle, children: sectionLabel })
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(styles$2.stableLabel, styles$2.alignLeft),
        onClick: toggle,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: isTokenMode ? styles$2.hidden : void 0, children: timeRightLabel }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: isTokenMode ? void 0 : styles$2.hidden, children: tokenRightLabel })
        ]
      }
    )
  ] });
};
const swimlane = "_swimlane_srxcq_1";
const pinnedSection = "_pinnedSection_srxcq_17";
const scrollSection = "_scrollSection_srxcq_26";
const collapsibleSection = "_collapsibleSection_srxcq_42";
const collapsibleCollapsed = "_collapsibleCollapsed_srxcq_52";
const collapsibleInner = "_collapsibleInner_srxcq_57";
const collapseToggle = "_collapseToggle_srxcq_68";
const row = "_row_srxcq_96";
const label = "_label_srxcq_102";
const labelChild = "_labelChild_srxcq_114";
const labelSelected = "_labelSelected_srxcq_118";
const barArea = "_barArea_srxcq_124";
const fill = "_fill_srxcq_129";
const fillParent = "_fillParent_srxcq_147";
const fillSelected = "_fillSelected_srxcq_151";
const parallelBadge = "_parallelBadge_srxcq_156";
const chevron = "_chevron_srxcq_163";
const marker = "_marker_srxcq_190";
const markerError = "_markerError_srxcq_210";
const markerCompaction = "_markerCompaction_srxcq_217";
const markerBranch = "_markerBranch_srxcq_228";
const branchPopover = "_branchPopover_srxcq_235";
const branchEntry = "_branchEntry_srxcq_241";
const branchLabel = "_branchLabel_srxcq_261";
const branchMeta = "_branchMeta_srxcq_265";
const breadcrumbRow = "_breadcrumbRow_srxcq_277";
const breadcrumbBack = "_breadcrumbBack_srxcq_287";
const breadcrumbGroup = "_breadcrumbGroup_srxcq_310";
const breadcrumbLink = "_breadcrumbLink_srxcq_317";
const breadcrumbCurrent = "_breadcrumbCurrent_srxcq_330";
const breadcrumbSelection = "_breadcrumbSelection_srxcq_343";
const breadcrumbDivider = "_breadcrumbDivider_srxcq_349";
const tokens = "_tokens_srxcq_357";
const styles$1 = {
  swimlane,
  pinnedSection,
  scrollSection,
  collapsibleSection,
  collapsibleCollapsed,
  collapsibleInner,
  collapseToggle,
  row,
  label,
  labelChild,
  labelSelected,
  barArea,
  fill,
  fillParent,
  fillSelected,
  parallelBadge,
  chevron,
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
function parseSelected(selected) {
  if (!selected) return null;
  return parsePathSegment(selected);
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
  selected,
  node,
  onSelect,
  onDrillDown,
  onBranchDrillDown,
  onGoUp,
  minimap: minimap2,
  breadcrumb
}) => {
  const parsedSelection = reactExports.useMemo(() => parseSelected(selected), [selected]);
  const [collapsed, setCollapsed] = useProperty(
    "timeline",
    "swimlanesCollapsed",
    { defaultValue: false, cleanup: false }
  );
  const isCollapsed = !!collapsed;
  const toggleCollapsed = reactExports.useCallback(() => {
    setCollapsed(!isCollapsed);
  }, [isCollapsed, setCollapsed]);
  const [branchPopover2, setBranchPopover] = reactExports.useState(null);
  const handleBranchClick = reactExports.useCallback(
    (forkedAt, element) => {
      setBranchPopover(
        (prev) => prev?.forkedAt === forkedAt ? null : { forkedAt, element }
      );
    },
    []
  );
  const handleBranchSelect = reactExports.useCallback(
    (branchSegment) => {
      const lookup = findBranchesByForkedAt(
        node,
        branchPopover2?.forkedAt ?? ""
      );
      setBranchPopover(null);
      if (lookup && lookup.ownerPath.length > 0) {
        const fullSegment = [...lookup.ownerPath, branchSegment].join("/");
        onBranchDrillDown(fullSegment);
      } else {
        onBranchDrillDown(branchSegment);
      }
    },
    [onBranchDrillDown, node, branchPopover2?.forkedAt]
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
  const renderRow = (layout, rowIndex) => /* @__PURE__ */ jsxRuntimeExports.jsx(
    SwimlaneRow,
    {
      layout,
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
      onBranchClick: handleBranchClick
    },
    `${layout.name}-${rowIndex}`
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: styles$1.swimlane,
      tabIndex: 0,
      onKeyDown: handleKeyDown,
      role: "grid",
      "aria-label": "Timeline swimlane",
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.pinnedSection, children: breadcrumb && /* @__PURE__ */ jsxRuntimeExports.jsx(BreadcrumbRow, { ...breadcrumb, minimap: minimap2 }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              styles$1.collapsibleSection,
              isCollapsed && styles$1.collapsibleCollapsed
            ),
            children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$1.collapsibleInner, children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.pinnedSection, children: parentRow && renderRow(parentRow, 0) }),
              childRows.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.scrollSection, children: childRows.map((layout, i) => renderRow(layout, i + 1)) })
            ] })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: styles$1.collapseToggle,
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
  parsedSelection,
  onSelect,
  onDrillDown,
  onBranchClick
}) => {
  const hasSelectedSpan = layout.spans.some(
    (_, i) => isSpanSelected(layout, i, parsedSelection)
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$1.row, role: "row", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(
          styles$1.label,
          !layout.isParent && styles$1.labelChild,
          hasSelectedSpan && styles$1.labelSelected
        ),
        children: [
          layout.name,
          layout.parallelCount !== null && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$1.parallelBadge, children: [
            "(",
            layout.parallelCount,
            ")"
          ] })
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$1.barArea, children: [
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
      layout.markers.map((marker2, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(MarkerGlyph, { marker: marker2, onBranchClick }, i))
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.tokens, children: formatTokenCount(layout.totalTokens) })
  ] });
};
const BreadcrumbRow = ({
  breadcrumbs,
  atRoot,
  onGoUp,
  onNavigate,
  minimap: minimap2,
  selected
}) => {
  const selectedLabel = selected ? parsePathSegment(selected).name : null;
  const lastBreadcrumb = breadcrumbs[breadcrumbs.length - 1];
  const showSelection = selectedLabel !== null && selectedLabel.toLowerCase() !== lastBreadcrumb?.label.toLowerCase();
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$1.breadcrumbRow, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        className: styles$1.breadcrumbBack,
        onClick: onGoUp,
        disabled: atRoot,
        title: "Go up one level (Escape)",
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.navbar.back })
      }
    ),
    breadcrumbs.map((segment, i) => {
      const isLast = i === breadcrumbs.length - 1;
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$1.breadcrumbGroup, children: [
        i > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.breadcrumbDivider, children: "›" }),
        isLast ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: styles$1.breadcrumbCurrent,
            onClick: () => onNavigate(segment.path),
            children: segment.label
          }
        ) : /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: styles$1.breadcrumbLink,
            onClick: () => onNavigate(segment.path),
            children: segment.label
          }
        )
      ] }, segment.path + i);
    }),
    showSelection && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$1.breadcrumbGroup, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.breadcrumbDivider, children: "›" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.breadcrumbSelection, children: selectedLabel })
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
  const handleChevronClick = reactExports.useCallback(
    (e) => {
      e.stopPropagation();
      onDrillDown();
    },
    [onDrillDown]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: clsx(
          styles$1.fill,
          isParent && styles$1.fillParent,
          isSelected && styles$1.fillSelected
        ),
        style: {
          left: `${span.bar.left}%`,
          width: `${span.bar.width}%`
        },
        title: span.description ?? void 0,
        onClick: handleClick,
        onDoubleClick: handleDoubleClick
      }
    ),
    span.drillable && /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        className: styles$1.chevron,
        style: {
          left: `${span.bar.left + span.bar.width}%`
        },
        onClick: handleChevronClick,
        title: "Drill down",
        children: "›"
      }
    )
  ] });
};
const MarkerGlyph = ({ marker: marker2, onBranchClick }) => {
  const icon = MARKER_ICONS[marker2.kind]?.icon ?? "bi bi-question-circle";
  const kindClass = marker2.kind === "error" ? styles$1.markerError : marker2.kind === "compaction" ? styles$1.markerCompaction : styles$1.markerBranch;
  const handleClick = reactExports.useCallback(
    (e) => {
      if (marker2.kind === "branch") {
        e.stopPropagation();
        onBranchClick(marker2.reference, e.currentTarget);
      }
    },
    [marker2.kind, marker2.reference, onBranchClick]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "span",
    {
      className: clsx(styles$1.marker, kindClass),
      style: { left: `${marker2.left}%` },
      title: marker2.tooltip,
      onClick: handleClick,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: icon })
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
      hoverDelay: -1,
      closeOnMouseLeave: false,
      styles: { padding: "4px 0" },
      children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.branchPopover, children: branches.map(({ branch, index }) => {
        const span = createBranchSpan(branch, index);
        const durationSec = (branch.endTime.getTime() - branch.startTime.getTime()) / 1e3;
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            className: styles$1.branchEntry,
            onClick: () => onSelect(`@branch-${index}`),
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.branchLabel, children: span.name }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$1.branchMeta, children: [
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
function ts(baseMs, offsetSeconds) {
  return new Date(baseMs + offsetSeconds * 1e3);
}
const BASE = (/* @__PURE__ */ new Date("2025-01-15T10:00:00Z")).getTime();
const NULL_CONFIG = {
  attempt_timeout: null,
  batch: null,
  best_of: null,
  cache: null,
  cache_prompt: null,
  effort: null,
  extra_body: null,
  extra_headers: null,
  frequency_penalty: null,
  internal_tools: null,
  logit_bias: null,
  logprobs: null,
  max_connections: null,
  max_retries: null,
  max_tokens: null,
  max_tool_output: null,
  num_choices: null,
  parallel_tool_calls: null,
  presence_penalty: null,
  reasoning_effort: null,
  reasoning_history: null,
  reasoning_summary: null,
  reasoning_tokens: null,
  response_schema: null,
  seed: null,
  stop_seqs: null,
  system_message: null,
  temperature: null,
  timeout: null,
  top_k: null,
  top_logprobs: null,
  top_p: null,
  verbosity: null
};
function makeModelEventNode(content2, startSec, endSec, tokens2, uuid) {
  const event = {
    event: "model",
    model: "claude-sonnet-4-5-20250929",
    input: [],
    tools: [],
    tool_choice: "auto",
    config: NULL_CONFIG,
    output: {
      choices: [
        {
          message: {
            role: "assistant",
            content: content2,
            id: null,
            metadata: null,
            model: null,
            source: null,
            tool_calls: null
          },
          stop_reason: "stop",
          logprobs: null
        }
      ],
      completion: content2,
      error: null,
      metadata: null,
      model: "claude-sonnet-4-5-20250929",
      time: endSec - startSec,
      usage: {
        input_tokens: Math.floor(tokens2 * 0.6),
        output_tokens: Math.floor(tokens2 * 0.4),
        total_tokens: tokens2,
        input_tokens_cache_read: null,
        input_tokens_cache_write: null,
        reasoning_tokens: null,
        total_cost: null
      }
    },
    timestamp: ts(BASE, startSec).toISOString(),
    working_start: startSec,
    working_time: endSec - startSec,
    cache: null,
    call: null,
    completed: null,
    error: null,
    metadata: null,
    pending: null,
    retries: null,
    role: null,
    span_id: null,
    traceback: null,
    traceback_ansi: null,
    uuid: uuid ?? null
  };
  return {
    type: "event",
    event,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens2
  };
}
function makeToolEventNode(fn, args, result, startSec, endSec, tokens2) {
  const event = {
    event: "tool",
    type: "function",
    function: fn,
    id: `call-${fn}-${startSec}`,
    arguments: args,
    result,
    events: [],
    timestamp: ts(BASE, startSec).toISOString(),
    working_start: startSec,
    working_time: endSec - startSec,
    agent: null,
    completed: null,
    error: null,
    failed: null,
    message_id: null,
    metadata: null,
    pending: null,
    span_id: null,
    truncated: null,
    uuid: null,
    view: null
  };
  return {
    type: "event",
    event,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens2
  };
}
function makeToolErrorEventNode(fn, errorMsg, errorType, startSec, endSec, tokens2) {
  const event = {
    event: "tool",
    type: "function",
    function: fn,
    id: `call-${fn}-${startSec}`,
    arguments: {},
    result: `Error: ${errorMsg}`,
    events: [],
    timestamp: ts(BASE, startSec).toISOString(),
    working_start: startSec,
    working_time: endSec - startSec,
    error: { message: errorMsg, type: errorType },
    failed: true,
    agent: null,
    completed: null,
    message_id: null,
    metadata: null,
    pending: null,
    span_id: null,
    truncated: null,
    uuid: null,
    view: null
  };
  return {
    type: "event",
    event,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens2
  };
}
function makeModelErrorEventNode(_content, errorMsg, startSec, endSec, tokens2) {
  const event = {
    event: "model",
    model: "claude-sonnet-4-5-20250929",
    input: [],
    tools: [],
    tool_choice: "auto",
    config: NULL_CONFIG,
    output: {
      choices: [],
      completion: "",
      error: errorMsg,
      metadata: null,
      model: "claude-sonnet-4-5-20250929",
      time: endSec - startSec,
      usage: {
        input_tokens: Math.floor(tokens2 * 0.8),
        output_tokens: Math.floor(tokens2 * 0.2),
        total_tokens: tokens2,
        input_tokens_cache_read: null,
        input_tokens_cache_write: null,
        reasoning_tokens: null,
        total_cost: null
      }
    },
    timestamp: ts(BASE, startSec).toISOString(),
    working_start: startSec,
    working_time: endSec - startSec,
    cache: null,
    call: null,
    completed: null,
    error: errorMsg,
    metadata: null,
    pending: null,
    retries: null,
    role: null,
    span_id: null,
    traceback: null,
    traceback_ansi: null,
    uuid: null
  };
  return {
    type: "event",
    event,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens2
  };
}
function makeCompactionEventNode(tokensBefore, tokensAfter, startSec, endSec) {
  const event = {
    event: "compaction",
    type: "summary",
    tokens_before: tokensBefore,
    tokens_after: tokensAfter,
    timestamp: ts(BASE, startSec).toISOString(),
    working_start: startSec,
    metadata: null,
    pending: null,
    source: null,
    span_id: null,
    uuid: null
  };
  return {
    type: "event",
    event,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: 0
  };
}
function makeSpan(id, name, spanType, startSec, endSec, tokens2, content2 = [], options) {
  return {
    type: "span",
    id,
    name,
    spanType,
    content: content2,
    branches: options?.branches ?? [],
    description: options?.description,
    utility: options?.utility ?? false,
    startTime: ts(BASE, startSec),
    endTime: ts(BASE, endSec),
    totalTokens: tokens2
  };
}
function makeTimeline(root, options) {
  if (options?.scoring) {
    const scoring = options.scoring;
    const newContent = [...root.content, scoring];
    const endTime = scoring.endTime > root.endTime ? scoring.endTime : root.endTime;
    return {
      name: "Default",
      description: "",
      root: {
        ...root,
        content: newContent,
        endTime,
        totalTokens: root.totalTokens + scoring.totalTokens
      }
    };
  }
  return { name: "Default", description: "", root };
}
function sequentialAgents() {
  const explore = makeSpan(
    "explore",
    "Explore",
    "agent",
    2,
    14,
    8100,
    [
      makeModelEventNode("Let me examine the project structure.", 2, 5, 2400),
      makeToolEventNode(
        "bash",
        { cmd: "find . -type f" },
        "src/\nlib/\ntests/",
        5,
        7,
        800
      ),
      makeModelEventNode(
        "I see a standard project layout. Let me look at the main module.",
        7,
        10,
        2600
      ),
      makeToolEventNode(
        "read_file",
        { path: "src/main.py" },
        "def main(): ...",
        10,
        12,
        1200
      ),
      makeModelEventNode("The main entry point is clear.", 12, 14, 1100)
    ],
    {
      description: "Explore the project structure and understand the codebase"
    }
  );
  const plan = makeSpan(
    "plan",
    "Plan",
    "agent",
    15,
    24,
    5300,
    [
      makeModelEventNode(
        "Based on my exploration, I'll plan the implementation.",
        15,
        18,
        1800
      ),
      makeToolEventNode(
        "bash",
        { cmd: "wc -l src/*.py" },
        "142 total",
        18,
        19,
        400
      ),
      makeModelEventNode(
        "The plan is: 1) Refactor core module, 2) Add tests, 3) Update docs.",
        19,
        24,
        3100
      )
    ],
    {
      description: "Create an implementation plan based on exploration findings"
    }
  );
  const build = makeSpan(
    "build",
    "Build",
    "agent",
    25,
    52,
    31800,
    [
      makeModelEventNode(
        "Starting implementation of the refactored module.",
        25,
        29,
        4200
      ),
      makeToolEventNode(
        "write_file",
        { path: "src/core.py" },
        "File written successfully",
        29,
        32,
        2800
      ),
      makeModelEventNode(
        "Core module done. Now adding test coverage.",
        32,
        36,
        3600
      ),
      makeToolEventNode(
        "write_file",
        { path: "tests/test_core.py" },
        "File written successfully",
        36,
        40,
        3200
      ),
      makeToolEventNode(
        "bash",
        { cmd: "pytest tests/" },
        "5 passed",
        40,
        44,
        1e3
      ),
      makeModelEventNode(
        "All tests pass. Updating documentation.",
        44,
        48,
        3400
      ),
      makeToolEventNode(
        "write_file",
        { path: "docs/api.md" },
        "File written successfully",
        48,
        50,
        2600
      ),
      makeModelEventNode(
        "Implementation complete with full test coverage.",
        50,
        52,
        11e3
      )
    ],
    {
      description: "Implement the refactored module with tests and documentation"
    }
  );
  const scoring = makeSpan("scoring", "Scoring", "scorers", 53, 58, 3200);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    58,
    48500,
    [
      makeModelEventNode(
        "I'll work through this task step by step.",
        0,
        2,
        1500
      ),
      explore,
      plan,
      build,
      makeModelEventNode("All phases complete. Task finished.", 52, 53, 700)
    ]
  );
  return {
    name: "Sequential agents",
    description: "S1 — Explore → Plan → Build → Scoring",
    timeline: makeTimeline(transcript, { scoring })
  };
}
function iterativeAgents() {
  const explore1 = makeSpan("explore-1", "Explore", "agent", 2, 10, 7200, [
    makeModelEventNode("Initial exploration of the codebase.", 2, 5, 2800),
    makeToolEventNode(
      "bash",
      { cmd: "ls -la src/" },
      "core.py\nutils.py\nconfig.py",
      5,
      6,
      600
    ),
    makeModelEventNode("Found key files. Checking dependencies.", 6, 9, 2400),
    makeToolEventNode(
      "bash",
      { cmd: "pip list" },
      "requests==2.31\nflask==3.0",
      9,
      10,
      1400
    )
  ]);
  const plan1 = makeSpan("plan-1", "Plan", "agent", 11, 18, 4600, [
    makeModelEventNode(
      "First iteration plan: focus on core module.",
      11,
      14,
      2200
    ),
    makeToolEventNode(
      "read_file",
      { path: "src/core.py" },
      "class Core: ...",
      14,
      16,
      1e3
    ),
    makeModelEventNode("Need more info before finalizing plan.", 16, 18, 1400)
  ]);
  const explore2 = makeSpan("explore-2", "Explore", "agent", 19, 26, 7300, [
    makeModelEventNode(
      "Second exploration pass: checking edge cases.",
      19,
      22,
      2600
    ),
    makeToolEventNode(
      "bash",
      { cmd: "grep -r 'TODO' src/" },
      "core.py:12: TODO fix",
      22,
      23,
      800
    ),
    makeModelEventNode("Found TODOs. Reviewing test coverage.", 23, 26, 3900)
  ]);
  const plan2 = makeSpan("plan-2", "Plan", "agent", 27, 33, 4600, [
    makeModelEventNode("Revised plan with edge case handling.", 27, 30, 2400),
    makeModelEventNode(
      "Plan finalized: address TODOs and add error handling.",
      30,
      33,
      2200
    )
  ]);
  const build = makeSpan("build", "Build", "agent", 34, 55, 34600, [
    makeModelEventNode("Implementing planned changes.", 34, 38, 5200),
    makeToolEventNode(
      "write_file",
      { path: "src/core.py" },
      "File written",
      38,
      42,
      4800
    ),
    makeToolEventNode(
      "write_file",
      { path: "src/utils.py" },
      "File written",
      42,
      45,
      3600
    ),
    makeModelEventNode("Running tests to verify changes.", 45, 48, 3200),
    makeToolEventNode(
      "bash",
      { cmd: "pytest -v" },
      "8 passed, 0 failed",
      48,
      51,
      1200
    ),
    makeModelEventNode("All tests pass. Build complete.", 51, 55, 16600)
  ]);
  const scoring = makeSpan("scoring", "Scoring", "scorers", 56, 60, 3200);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    60,
    61500,
    [explore1, plan1, explore2, plan2, build]
  );
  return {
    name: "Iterative agents",
    description: "S2 — Explore and Plan with multiple spans",
    timeline: makeTimeline(transcript, { scoring })
  };
}
function deepNesting() {
  const generate = makeSpan("generate", "Generate", "agent", 46, 58, 5800, [
    makeModelEventNode("Generating test cases for the module.", 46, 50, 2400),
    makeToolEventNode(
      "write_file",
      { path: "tests/test_gen.py" },
      "File written",
      50,
      54,
      1800
    ),
    makeModelEventNode("Test cases generated successfully.", 54, 58, 1600)
  ]);
  const run = makeSpan("run", "Run", "agent", 59, 64, 400, [
    makeToolEventNode(
      "bash",
      { cmd: "pytest tests/test_gen.py" },
      "Running...",
      59,
      61,
      200
    ),
    makeToolErrorEventNode(
      "bash",
      "Process timed out after 30s",
      "timeout",
      61,
      64,
      200
    )
  ]);
  const evaluate = makeSpan("evaluate", "Evaluate", "agent", 65, 75, 4200, [
    makeModelEventNode(
      "Evaluating test results despite timeout.",
      65,
      69,
      1800
    ),
    makeToolEventNode(
      "read_file",
      { path: "tests/test_gen.py" },
      "def test_basic(): ...",
      69,
      71,
      600
    ),
    makeModelEventNode(
      "Test needs adjustment for timeout. Evaluation complete.",
      71,
      75,
      1800
    )
  ]);
  const code = makeSpan("code", "Code", "agent", 22, 44, 15200, [
    makeModelEventNode("Writing the core implementation.", 22, 26, 3200),
    makeToolEventNode(
      "write_file",
      { path: "src/module.py" },
      "File written",
      26,
      30,
      2800
    ),
    makeCompactionEventNode(12e3, 6500, 30, 31),
    makeModelEventNode("Continuing after context compaction.", 31, 36, 4400),
    makeToolEventNode(
      "write_file",
      { path: "src/helpers.py" },
      "File written",
      36,
      40,
      2400
    ),
    makeModelEventNode("Code implementation phase complete.", 40, 44, 2400)
  ]);
  const test = makeSpan("test", "Test", "agent", 45, 75, 10400, [
    makeModelEventNode("Setting up test infrastructure.", 45, 46, 600),
    generate,
    run,
    evaluate
  ]);
  const fix = makeSpan("fix", "Fix", "agent", 76, 88, 6200, [
    makeModelEventNode("Fixing the timeout issue in tests.", 76, 80, 2200),
    makeToolEventNode(
      "write_file",
      { path: "tests/test_gen.py" },
      "File updated",
      80,
      83,
      1800
    ),
    makeToolEventNode(
      "bash",
      { cmd: "pytest tests/" },
      "3 passed",
      83,
      86,
      800
    ),
    makeModelEventNode("All tests pass after fixes.", 86, 88, 1400)
  ]);
  const explore = makeSpan("explore", "Explore", "agent", 2, 18, 6400, [
    makeModelEventNode("Examining the project structure.", 2, 6, 2200),
    makeToolEventNode(
      "bash",
      { cmd: "find . -type f" },
      "src/\nlib/\ntests/",
      6,
      9,
      800
    ),
    makeModelEventNode("Project structure understood.", 9, 14, 2e3),
    makeToolEventNode(
      "read_file",
      { path: "src/main.py" },
      "def main(): ...",
      14,
      18,
      1400
    )
  ]);
  const build = makeSpan("build", "Build", "agent", 20, 88, 31800, [
    makeModelEventNode("Starting the build process.", 20, 22, 800),
    code,
    test,
    fix
  ]);
  const scoring = makeSpan("scoring", "Scoring", "scorers", 90, 95, 3200);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    95,
    41400,
    [explore, build]
  );
  return {
    name: "Deep nesting (3 levels)",
    description: "S3 — Explore → Build → Code/Test/Fix, Test → Generate/Run/Evaluate",
    timeline: makeTimeline(transcript, { scoring })
  };
}
function parallelAgents() {
  const explore1 = makeSpan(
    "explore-1",
    "Explore",
    "agent",
    2,
    14,
    8100,
    [
      makeModelEventNode("Exploring API documentation.", 2, 5, 2800),
      makeToolEventNode(
        "bash",
        { cmd: "curl api/docs" },
        '{"endpoints": [...]}',
        5,
        8,
        1400
      ),
      makeModelEventNode("API structure documented.", 8, 11, 2200),
      makeToolEventNode(
        "read_file",
        { path: "api/schema.json" },
        '{"type": "object"}',
        11,
        14,
        1700
      )
    ],
    { description: "Search for API documentation" }
  );
  const explore2 = makeSpan(
    "explore-2",
    "Explore",
    "agent",
    3,
    16,
    9400,
    [
      makeModelEventNode("Exploring database schema.", 3, 7, 3200),
      makeToolEventNode(
        "bash",
        { cmd: "sqlite3 db.sqlite .schema" },
        "CREATE TABLE users ...",
        7,
        10,
        1600
      ),
      makeModelEventNode("Database schema analyzed.", 10, 13, 2800),
      makeToolEventNode(
        "bash",
        { cmd: "sqlite3 db.sqlite 'SELECT count(*) FROM users'" },
        "1247",
        13,
        16,
        1800
      )
    ],
    { description: "Analyze existing database schema and data" }
  );
  const explore3 = makeSpan(
    "explore-3",
    "Explore",
    "agent",
    2,
    12,
    6800,
    [
      makeModelEventNode("Exploring frontend components.", 2, 5, 2400),
      makeToolEventNode(
        "bash",
        { cmd: "ls src/components/" },
        "Header.tsx\nFooter.tsx",
        5,
        7,
        800
      ),
      makeModelEventNode("Frontend component inventory complete.", 7, 10, 2200),
      makeToolEventNode(
        "read_file",
        { path: "src/App.tsx" },
        "function App() { ... }",
        10,
        12,
        1400
      )
    ],
    { description: "Inventory frontend components and architecture" }
  );
  const plan = makeSpan("plan", "Plan", "agent", 17, 25, 5300, [
    makeModelEventNode(
      "Synthesizing findings from all exploration tracks.",
      17,
      20,
      2400
    ),
    makeModelEventNode("Implementation plan ready.", 20, 25, 2900)
  ]);
  const build = makeSpan("build", "Build", "agent", 26, 52, 27600, [
    makeModelEventNode("Starting full-stack implementation.", 26, 30, 4200),
    makeToolEventNode(
      "write_file",
      { path: "src/api/routes.py" },
      "File written",
      30,
      34,
      3800
    ),
    makeToolEventNode(
      "write_file",
      { path: "src/components/Dashboard.tsx" },
      "File written",
      34,
      38,
      4200
    ),
    makeModelEventNode(
      "Core components built. Adding integration.",
      38,
      42,
      3600
    ),
    makeToolEventNode(
      "bash",
      { cmd: "npm run build" },
      "Build successful",
      42,
      46,
      1200
    ),
    makeModelEventNode("Build and integration complete.", 46, 52, 10600)
  ]);
  const scoring = makeSpan("scoring", "Scoring", "scorers", 53, 57, 3200);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    57,
    60400,
    [explore1, explore2, explore3, plan, build]
  );
  return {
    name: "Parallel agents",
    description: "S4 — Explore (3) parallel group + Plan + Build",
    timeline: makeTimeline(transcript, { scoring })
  };
}
function inlineMarkers() {
  const agent = makeSpan("agent", "Agent", "agent", 2, 55, 42e3, [
    makeModelEventNode("Starting work on the task.", 2, 6, 3200),
    makeToolEventNode(
      "bash",
      { cmd: "npm install" },
      "added 142 packages",
      6,
      10,
      1200
    ),
    makeModelEventNode("Dependencies installed. Writing code.", 10, 16, 4800),
    makeToolEventNode(
      "write_file",
      { path: "src/feature.ts" },
      "File written",
      16,
      20,
      3600
    ),
    makeModelErrorEventNode(
      "Attempting to call the API",
      "Rate limit exceeded: 429 Too Many Requests",
      20,
      24,
      2400
    ),
    makeModelEventNode(
      "Retrying after rate limit. Adjusting approach.",
      24,
      28,
      3200
    ),
    makeToolEventNode(
      "bash",
      { cmd: "curl -X POST api/endpoint" },
      '{"status": "ok"}',
      28,
      31,
      1400
    ),
    makeToolErrorEventNode(
      "bash",
      "Command timed out after 60s",
      "timeout",
      31,
      35,
      800
    ),
    makeModelEventNode(
      "Tool timed out. Working around the issue.",
      35,
      39,
      3800
    ),
    makeCompactionEventNode(15e3, 8e3, 39, 40),
    makeModelEventNode(
      "Context compacted. Continuing with reduced history.",
      40,
      45,
      5200
    ),
    makeToolEventNode(
      "write_file",
      { path: "src/feature.ts" },
      "File updated",
      45,
      49,
      4800
    ),
    makeModelEventNode("Feature implementation complete.", 49, 55, 7600)
  ]);
  const scoring = makeSpan("scoring", "Scoring", "scorers", 56, 60, 3200);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    60,
    45200,
    [agent]
  );
  return {
    name: "Inline markers",
    description: "S5 — Agent with error and compaction events",
    timeline: makeTimeline(transcript, { scoring })
  };
}
function flatTranscript() {
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    40,
    12400,
    [
      makeModelEventNode("Analyzing the user request.", 0, 4, 1800),
      makeToolEventNode(
        "bash",
        { cmd: "ls -la" },
        "total 42\ndrwxr-xr-x ...",
        4,
        6,
        600
      ),
      makeModelEventNode(
        "I see the project files. Let me read the config.",
        6,
        10,
        2200
      ),
      makeToolEventNode(
        "read_file",
        { path: "config.yaml" },
        "port: 8080\ndb: postgres",
        10,
        12,
        800
      ),
      makeModelEventNode(
        "Configuration loaded. Making the requested change.",
        12,
        18,
        2400
      ),
      makeToolEventNode(
        "write_file",
        { path: "config.yaml" },
        "port: 9090\ndb: postgres",
        18,
        20,
        600
      ),
      makeToolEventNode(
        "bash",
        { cmd: "python validate.py" },
        "Config valid",
        20,
        23,
        400
      ),
      makeModelEventNode(
        "Change applied and validated successfully.",
        23,
        28,
        1800
      ),
      makeToolEventNode(
        "bash",
        { cmd: "python -m pytest" },
        "12 passed",
        28,
        34,
        800
      ),
      makeModelEventNode("All tests pass. Task complete.", 34, 40, 900)
    ]
  );
  return {
    name: "Flat transcript",
    description: "S7 — Single agent, no children, just events",
    timeline: makeTimeline(transcript)
  };
}
function manyRows() {
  const names = [
    "Research",
    "Analyze",
    "Design",
    "Implement",
    "Test",
    "Review",
    "Refactor",
    "Deploy",
    "Monitor",
    "Cleanup"
  ];
  const agentEvents = [
    // Research
    [["bash", { cmd: "search docs" }, "Found 5 relevant docs"]],
    // Analyze
    [["read_file", { path: "src/main.py" }, "class Main: ..."]],
    // Design
    [["write_file", { path: "design.md" }, "Written"]],
    // Implement
    [["write_file", { path: "src/feature.py" }, "Written"]],
    // Test — model error agent
    [["bash", { cmd: "pytest" }, "3 passed, 1 failed"]],
    // Review
    [["bash", { cmd: "ruff check src/" }, "All checks passed"]],
    // Refactor — compaction agent
    [["write_file", { path: "src/refactored.py" }, "Written"]],
    // Deploy
    [["bash", { cmd: "docker build ." }, "Successfully built abc123"]],
    // Monitor
    [["bash", { cmd: "curl health" }, '{"status":"healthy"}']],
    // Cleanup
    [["bash", { cmd: "rm -rf tmp/" }, "Cleaned"]]
  ];
  const agents = [];
  let offset = 2;
  let totalTokens = 0;
  for (let i = 0; i < names.length; i++) {
    const duration = 4 + Math.floor(i * 0.5);
    const tokens2 = 2e3 + i * 1100;
    const name = names[i] ?? `Agent ${i}`;
    const evts = agentEvents[i] ?? [];
    const mid = offset + Math.floor(duration / 2);
    const content2 = [
      makeModelEventNode(
        `Starting ${name.toLowerCase()} phase.`,
        offset,
        mid,
        Math.floor(tokens2 * 0.4)
      )
    ];
    for (const [fn, args, result] of evts) {
      content2.push(
        makeToolEventNode(
          fn,
          args,
          result,
          mid,
          mid + 1,
          Math.floor(tokens2 * 0.2)
        )
      );
    }
    if (i === 4) {
      content2.push(
        makeModelErrorEventNode(
          "Attempting test analysis",
          "Context length exceeded",
          mid + 1,
          mid + 2,
          Math.floor(tokens2 * 0.1)
        )
      );
    }
    if (i === 6) {
      content2.push(makeCompactionEventNode(9e3, 5e3, mid + 1, mid + 2));
    }
    content2.push(
      makeModelEventNode(
        `${name} phase complete.`,
        offset + duration - 1,
        offset + duration,
        Math.floor(tokens2 * 0.3)
      )
    );
    agents.push(
      makeSpan(
        `agent-${i}`,
        name,
        "agent",
        offset,
        offset + duration,
        tokens2,
        content2
      )
    );
    totalTokens += tokens2;
    offset += duration + 1;
  }
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    offset,
    totalTokens,
    agents
  );
  return {
    name: "Many rows (8+)",
    description: "S8 — Tests 6-row cap / scrolling with 10 agents",
    timeline: makeTimeline(transcript)
  };
}
function utilityAgents() {
  const util1 = makeSpan(
    "util-1",
    "bash_checker",
    "agent",
    3,
    4,
    300,
    [
      makeToolEventNode(
        "bash",
        { cmd: "shellcheck script.sh" },
        "No issues",
        3,
        4,
        300
      )
    ],
    {
      utility: true
    }
  );
  const util2 = makeSpan(
    "util-2",
    "safety_validator",
    "agent",
    8,
    9,
    200,
    [makeToolEventNode("validate", { rule: "safety" }, "Pass", 8, 9, 200)],
    {
      utility: true
    }
  );
  const util3 = makeSpan(
    "util-3",
    "bash_checker",
    "agent",
    14,
    15,
    300,
    [
      makeToolEventNode(
        "bash",
        { cmd: "shellcheck deploy.sh" },
        "No issues",
        14,
        15,
        300
      )
    ],
    {
      utility: true
    }
  );
  const util4 = makeSpan(
    "util-4",
    "format_checker",
    "agent",
    20,
    21,
    250,
    [
      makeToolEventNode(
        "format",
        { target: "src/" },
        "All files formatted",
        20,
        21,
        250
      )
    ],
    {
      utility: true
    }
  );
  const mainAgent = makeSpan("main", "Build", "agent", 2, 45, 28e3, [
    makeModelEventNode("Starting build with safety checks.", 2, 3, 1200),
    util1,
    makeModelEventNode(
      "Bash check passed. Writing implementation.",
      4,
      8,
      3800
    ),
    util2,
    makeToolEventNode(
      "write_file",
      { path: "src/build.py" },
      "Written",
      9,
      13,
      4200
    ),
    makeModelEventNode(
      "Core written. Continuing with more code.",
      13,
      14,
      2400
    ),
    util3,
    makeToolEventNode(
      "write_file",
      { path: "src/deploy.py" },
      "Written",
      15,
      19,
      3600
    ),
    makeModelEventNode(
      "Deploy script ready. Running format check.",
      19,
      20,
      2200
    ),
    util4,
    makeModelEventNode("All checks passed. Build complete.", 21, 30, 4800),
    makeToolEventNode(
      "bash",
      { cmd: "python -m build" },
      "Build successful",
      30,
      40,
      2400
    ),
    makeModelEventNode("Package built and ready.", 40, 45, 3400)
  ]);
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    50,
    29050,
    [mainAgent]
  );
  return {
    name: "Utility agents",
    description: "S10 — Agent with multiple utility children",
    timeline: makeTimeline(transcript)
  };
}
function branchesSingleFork() {
  const branch1Refactor = makeSpan(
    "branch1-refactor",
    "Refactor",
    "agent",
    15,
    22,
    5200,
    [
      makeModelEventNode("Refactoring the module for clarity.", 15, 18, 2400),
      makeToolEventNode(
        "write_file",
        { path: "src/refactored.py" },
        "Written",
        18,
        20,
        1600
      ),
      makeModelEventNode("Refactoring complete.", 20, 22, 1200)
    ]
  );
  const branch1Validate = makeSpan(
    "branch1-validate",
    "Validate",
    "agent",
    23,
    28,
    3500,
    [
      makeModelEventNode("Validating the refactored code.", 23, 25, 1400),
      makeToolEventNode(
        "bash",
        { cmd: "pytest tests/" },
        "6 passed",
        25,
        27,
        800
      ),
      makeModelEventNode("Validation passed.", 27, 28, 1300)
    ]
  );
  const branch1 = {
    type: "branch",
    forkedAt: "model-call-5",
    content: [branch1Refactor, branch1Validate],
    startTime: ts(BASE, 15),
    endTime: ts(BASE, 28),
    totalTokens: 8700
  };
  const branch2Rewrite = makeSpan(
    "branch2-rewrite",
    "Rewrite",
    "agent",
    15,
    25,
    5100,
    [
      makeModelEventNode(
        "Taking a different approach: full rewrite.",
        15,
        19,
        2200
      ),
      makeToolEventNode(
        "write_file",
        { path: "src/rewritten.py" },
        "Written",
        19,
        22,
        1800
      ),
      makeModelEventNode("Rewrite approach complete.", 22, 25, 1100)
    ]
  );
  const branch2 = {
    type: "branch",
    forkedAt: "model-call-5",
    content: [branch2Rewrite],
    startTime: ts(BASE, 15),
    endTime: ts(BASE, 25),
    totalTokens: 5100
  };
  const code = makeSpan("code", "Code", "agent", 2, 24, 15200, [
    makeModelEventNode("Writing initial implementation.", 2, 6, 4200),
    makeToolEventNode(
      "write_file",
      { path: "src/module.py" },
      "Written",
      6,
      10,
      3200
    ),
    makeModelEventNode(
      "Initial code written. Iterating on design.",
      10,
      16,
      4400
    ),
    makeToolEventNode(
      "write_file",
      { path: "src/module.py" },
      "Updated",
      16,
      20,
      2e3
    ),
    makeModelEventNode("Code phase finalized.", 20, 24, 1400)
  ]);
  const test = makeSpan("test", "Test", "agent", 25, 40, 10400, [
    makeModelEventNode("Setting up test suite.", 25, 28, 2200),
    makeToolEventNode(
      "write_file",
      { path: "tests/test_module.py" },
      "Written",
      28,
      32,
      3400
    ),
    makeToolEventNode(
      "bash",
      { cmd: "pytest tests/" },
      "7 passed",
      32,
      36,
      1200
    ),
    makeModelEventNode("All tests passing.", 36, 40, 3600)
  ]);
  const build = makeSpan(
    "build",
    "Build",
    "agent",
    1,
    52,
    31800,
    [
      makeModelEventNode(
        "Starting build with branching strategy.",
        1,
        2,
        800,
        "model-call-5"
      ),
      code,
      test,
      makeModelEventNode("Build complete. Best branch selected.", 40, 52, 5400)
    ],
    {
      branches: [branch1, branch2]
    }
  );
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    55,
    31800,
    [build]
  );
  return {
    name: "Branches (single fork)",
    description: "S11 — Agent with 2 branches at one fork point",
    timeline: makeTimeline(transcript)
  };
}
function branchesMultipleForks() {
  const earlyAttempt = makeSpan(
    "early-attempt",
    "Attempt",
    "agent",
    8,
    14,
    4200,
    [
      makeModelEventNode("Early attempt at solving the problem.", 8, 11, 2e3),
      makeToolEventNode(
        "bash",
        { cmd: "python solve.py" },
        "Partial result",
        11,
        13,
        1200
      ),
      makeModelEventNode("Attempt did not fully succeed.", 13, 14, 1e3)
    ]
  );
  const earlyBranch = {
    type: "branch",
    forkedAt: "model-call-3",
    content: [earlyAttempt],
    startTime: ts(BASE, 8),
    endTime: ts(BASE, 14),
    totalTokens: 4200
  };
  const lateRetry = makeSpan("late-retry", "Retry", "agent", 30, 38, 3800, [
    makeModelEventNode("Retrying with modified parameters.", 30, 33, 1600),
    makeToolEventNode(
      "bash",
      { cmd: "python solve.py --retry" },
      "Better result",
      33,
      36,
      1e3
    ),
    makeModelEventNode("Retry showed improvement.", 36, 38, 1200)
  ]);
  const lateBranch1 = {
    type: "branch",
    forkedAt: "model-call-10",
    content: [lateRetry],
    startTime: ts(BASE, 30),
    endTime: ts(BASE, 38),
    totalTokens: 3800
  };
  const lateAlt = makeSpan("late-alt", "Alternative", "agent", 30, 42, 6100, [
    makeModelEventNode(
      "Trying a completely different algorithm.",
      30,
      34,
      2400
    ),
    makeToolEventNode(
      "write_file",
      { path: "src/alt_solver.py" },
      "Written",
      34,
      37,
      1800
    ),
    makeToolEventNode(
      "bash",
      { cmd: "python alt_solver.py" },
      "Success!",
      37,
      40,
      800
    ),
    makeModelEventNode("Alternative approach succeeded.", 40, 42, 1100)
  ]);
  const lateBranch2 = {
    type: "branch",
    forkedAt: "model-call-10",
    content: [lateAlt],
    startTime: ts(BASE, 30),
    endTime: ts(BASE, 42),
    totalTokens: 6100
  };
  const code = makeSpan("code", "Code", "agent", 2, 28, 15200, [
    makeModelEventNode("Beginning code implementation.", 2, 6, 3600),
    makeToolEventNode(
      "write_file",
      { path: "src/solver.py" },
      "Written",
      6,
      10,
      2800
    ),
    makeModelEventNode("Core solver implemented.", 10, 16, 4200),
    makeToolEventNode(
      "bash",
      { cmd: "python solver.py" },
      "Initial results",
      16,
      20,
      1400
    ),
    makeModelEventNode("Optimizing the solver.", 20, 28, 3200)
  ]);
  const test = makeSpan("test", "Test", "agent", 29, 48, 10400, [
    makeModelEventNode("Running comprehensive test suite.", 29, 33, 2800),
    makeToolEventNode(
      "bash",
      { cmd: "pytest tests/ -v" },
      "12 passed",
      33,
      38,
      1600
    ),
    makeModelEventNode("Tests validated. Checking edge cases.", 38, 43, 3200),
    makeToolEventNode(
      "bash",
      { cmd: "pytest tests/edge_cases.py" },
      "4 passed",
      43,
      46,
      1e3
    ),
    makeModelEventNode("All edge cases handled.", 46, 48, 1800)
  ]);
  const build = makeSpan(
    "build",
    "Build",
    "agent",
    1,
    55,
    31800,
    [
      makeModelEventNode(
        "Starting build with exploration branches.",
        1,
        2,
        600,
        "model-call-3"
      ),
      code,
      makeModelEventNode(
        "Evaluating approaches.",
        28,
        29,
        400,
        "model-call-10"
      ),
      test,
      makeModelEventNode(
        "Build finalized after exploring alternatives.",
        48,
        55,
        5800
      )
    ],
    {
      branches: [earlyBranch, lateBranch1, lateBranch2]
    }
  );
  const transcript = makeSpan(
    "transcript",
    "Transcript",
    "agent",
    0,
    58,
    31800,
    [build]
  );
  return {
    name: "Branches (multiple forks)",
    description: "S11 — Agent with branches at different fork points",
    timeline: makeTimeline(transcript)
  };
}
const timelineScenarios = [
  sequentialAgents(),
  iterativeAgents(),
  deepNesting(),
  parallelAgents(),
  inlineMarkers(),
  flatTranscript(),
  manyRows(),
  utilityAgents(),
  branchesSingleFork(),
  branchesMultipleForks()
];
function findRowByName(rows, name) {
  return rows.find((r) => r.name.toLowerCase() === name.toLowerCase());
}
function getSelectedSpans(rows, selected) {
  if (!selected) return [];
  const { name, spanIndex } = parsePathSegment(selected);
  const row2 = findRowByName(rows, name);
  if (!row2) return [];
  const result = [];
  for (const rowSpan of row2.spans) {
    if (isSingleSpan(rowSpan)) {
      result.push(rowSpan.agent);
    } else if (isParallelSpan(rowSpan)) {
      if (spanIndex !== null) {
        const agent = rowSpan.agents[spanIndex - 1];
        if (agent) result.push(agent);
      } else {
        result.push(...rowSpan.agents);
      }
    }
  }
  return result;
}
function computeMinimapSelection(rows, selected) {
  if (!selected) return void 0;
  const { name, spanIndex } = parsePathSegment(selected);
  const row2 = findRowByName(rows, name);
  if (!row2) return void 0;
  const targetIndex = (spanIndex ?? 1) - 1;
  for (const rowSpan of row2.spans) {
    if (isSingleSpan(rowSpan)) {
      const singleIndex = row2.spans.indexOf(rowSpan);
      if (singleIndex === targetIndex || row2.spans.length === 1) {
        const agent = rowSpan.agent;
        return {
          startTime: agent.startTime,
          endTime: agent.endTime,
          totalTokens: agent.totalTokens
        };
      }
    } else if (isParallelSpan(rowSpan)) {
      if (spanIndex !== null) {
        const agent = rowSpan.agents[spanIndex - 1];
        if (agent) {
          return {
            startTime: agent.startTime,
            endTime: agent.endTime,
            totalTokens: agent.totalTokens
          };
        }
      }
      const agents = getAgents(rowSpan);
      const first = agents[0];
      let start = first.startTime;
      let end = first.endTime;
      let tokens2 = first.totalTokens;
      for (let i = 1; i < agents.length; i++) {
        const a = agents[i];
        if (a.startTime < start) start = a.startTime;
        if (a.endTime > end) end = a.endTime;
        tokens2 += a.totalTokens;
      }
      return { startTime: start, endTime: end, totalTokens: tokens2 };
    }
  }
  return void 0;
}
function collectRawEvents(spans) {
  const events = [];
  for (const span of spans) {
    collectFromContent(span.content, events);
  }
  return events;
}
function collectFromContent(content2, out) {
  for (const item of content2) {
    if (item.type === "event") {
      out.push(item.event);
    } else {
      const beginEvent = {
        event: "span_begin",
        name: item.name,
        id: item.id,
        span_id: item.id,
        type: item.spanType,
        timestamp: item.startTime.toISOString(),
        parent_id: null,
        pending: false,
        working_start: 0,
        uuid: null,
        metadata: null
      };
      out.push(beginEvent);
      collectFromContent(item.content, out);
      const endEvent = {
        event: "span_end",
        id: `${item.id}-end`,
        span_id: item.id,
        timestamp: item.endTime.toISOString(),
        pending: false,
        working_start: 0,
        uuid: null,
        metadata: null
      };
      out.push(endEvent);
    }
  }
}
const container = "_container_1w6el_1";
const headerRow = "_headerRow_1w6el_8";
const title = "_title_1w6el_17";
const scenarioSelect = "_scenarioSelect_1w6el_25";
const markerDepthSelect = "_markerDepthSelect_1w6el_29";
const scenarioDescription = "_scenarioDescription_1w6el_33";
const content = "_content_1w6el_38";
const eventsContainer = "_eventsContainer_1w6el_45";
const outlineCollapsed = "_outlineCollapsed_1w6el_53";
const outlinePane = "_outlinePane_1w6el_57";
const outline = "_outline_1w6el_53";
const outlineToggle = "_outlineToggle_1w6el_70";
const eventsSeparator = "_eventsSeparator_1w6el_78";
const eventList = "_eventList_1w6el_82";
const emptyEvents = "_emptyEvents_1w6el_86";
const styles = {
  container,
  headerRow,
  title,
  scenarioSelect,
  markerDepthSelect,
  scenarioDescription,
  content,
  eventsContainer,
  outlineCollapsed,
  outlinePane,
  outline,
  outlineToggle,
  eventsSeparator,
  eventList,
  emptyEvents
};
const TimelinePanel = () => {
  useDocumentTitle("Timeline");
  const [selectedIndex, setSelectedIndex] = reactExports.useState(0);
  const [markerDepth, setMarkerDepth] = reactExports.useState("children");
  const [outlineCollapsed2, setOutlineCollapsed] = useProperty(
    "timeline",
    "outlineCollapsed",
    { defaultValue: true, cleanup: false }
  );
  const isOutlineCollapsed = !!outlineCollapsed2;
  const scenario = timelineScenarios[selectedIndex];
  const timeline = scenario?.timeline;
  const state = useTimeline(timeline);
  reactExports.useEffect(() => {
    state.navigateTo("");
  }, []);
  const layouts = reactExports.useMemo(
    () => computeRowLayouts(
      state.rows,
      state.node.startTime,
      state.node.endTime,
      markerDepth
    ),
    [state.rows, state.node.startTime, state.node.endTime, markerDepth]
  );
  const atRoot = state.breadcrumbs.length <= 1;
  const selectedSpans = reactExports.useMemo(
    () => getSelectedSpans(state.rows, state.selected),
    [state.rows, state.selected]
  );
  const minimapSelection = reactExports.useMemo(
    () => computeMinimapSelection(state.rows, state.selected),
    [state.rows, state.selected]
  );
  const rawEvents = reactExports.useMemo(
    () => collectRawEvents(selectedSpans),
    [selectedSpans]
  );
  const { eventNodes, defaultCollapsedIds } = useEventNodes(rawEvents, false);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.headerRow, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: styles.title, children: "Timeline" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        VscodeSingleSelect,
        {
          value: String(selectedIndex),
          onChange: (e) => {
            const target = e.target;
            setSelectedIndex(Number(target.value));
            state.navigateTo("");
          },
          className: styles.scenarioSelect,
          children: timelineScenarios.map((s, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: String(i), children: s.name }, i))
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        VscodeSingleSelect,
        {
          value: markerDepth,
          onChange: (e) => {
            const target = e.target;
            setMarkerDepth(target.value);
          },
          className: styles.markerDepthSelect,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "direct", children: "Markers: direct" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "children", children: "Markers: children" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "recursive", children: "Markers: recursive" })
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles.scenarioDescription, children: scenario?.description })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.content, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(TimelinePills, { timelines: [], activeIndex: 0, onSelect: () => {
      } }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        TimelineSwimLanes,
        {
          layouts,
          selected: state.selected,
          node: state.node,
          onSelect: state.select,
          onDrillDown: state.drillDown,
          onBranchDrillDown: state.drillDown,
          onGoUp: state.goUp,
          minimap: {
            root: timeline.root,
            selection: minimapSelection
          },
          breadcrumb: {
            breadcrumbs: state.breadcrumbs,
            atRoot,
            onGoUp: state.goUp,
            onNavigate: state.navigateTo,
            selected: state.selected
          }
        }
      ),
      eventNodes.length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: clsx(
            styles.eventsContainer,
            isOutlineCollapsed && styles.outlineCollapsed
          ),
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.outlinePane, children: [
              !isOutlineCollapsed && /* @__PURE__ */ jsxRuntimeExports.jsx(
                TranscriptOutline,
                {
                  eventNodes,
                  defaultCollapsedIds,
                  className: styles.outline
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "div",
                {
                  className: styles.outlineToggle,
                  onClick: () => setOutlineCollapsed(!isOutlineCollapsed),
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.sidebar })
                }
              )
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.eventsSeparator }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.eventList, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              TranscriptViewNodes,
              {
                id: "timeline-events",
                eventNodes,
                defaultCollapsedIds
              }
            ) })
          ]
        }
      ) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.emptyEvents, children: "Select a swimlane row to view events" })
    ] })
  ] });
};
export {
  TimelinePanel
};
//# sourceMappingURL=TimelinePanel.js.map
