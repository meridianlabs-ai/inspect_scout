import { r as reactExports, j as jsxRuntimeExports, c as clsx, $ as Link, A as ApplicationIcons, u as useStore, i as useSearchParams } from "./index.js";
import { m as useCollapseTranscriptEvent, P as PulsingDots, n as kSandboxSignalName, E as EventNode, o as TYPE_SCORERS, p as TYPE_SCORER, q as useVirtuosoState, f as useTranscriptNavigation, s as flatTree, t as kTranscriptOutlineCollapseScope, v as useScrollTrack, Y as Yr, l as useProperty } from "./TranscriptViewNodes.js";
import { g as formatDuration, a as formatPrettyDecimal, h as formatDurationShort, P as PopOver, e as formatTime } from "./ToolButton.js";
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
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$3.label), "data-depth": node.depth, children: [
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
        ] })
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
const labelForNode = (node) => {
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
  onHasNodesChange
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
function isSpanNode(item) {
  return typeof item === "object" && item !== null && "children" in item && Array.isArray(item.children);
}
function parseTimestamp(timestamp) {
  if (!timestamp) return null;
  const date = new Date(timestamp);
  return isNaN(date.getTime()) ? null : date;
}
function getEventStartTime(event) {
  const timestamp = event.timestamp;
  const date = parseTimestamp(timestamp);
  if (!date) {
    throw new Error("Event missing required timestamp field");
  }
  return date;
}
function getEventEndTime(event) {
  const completed = event.completed;
  if (completed) {
    const date = parseTimestamp(completed);
    if (date) return date;
  }
  return getEventStartTime(event);
}
function getEventTokens(event) {
  if (event.event === "model") {
    const usage = event.output?.usage;
    if (usage) {
      const inputTokens = usage.input_tokens ?? 0;
      const cacheRead = usage.input_tokens_cache_read ?? 0;
      const cacheWrite = usage.input_tokens_cache_write ?? 0;
      const outputTokens = usage.output_tokens ?? 0;
      return inputTokens + cacheRead + cacheWrite + outputTokens;
    }
  }
  return 0;
}
function minStartTime(nodes) {
  const first = nodes[0];
  if (!first) {
    throw new Error("minStartTime requires at least one node");
  }
  return nodes.reduce(
    (min, n) => n.startTime < min ? n.startTime : min,
    first.startTime
  );
}
function maxEndTime(nodes) {
  const first = nodes[0];
  if (!first) {
    throw new Error("maxEndTime requires at least one node");
  }
  return nodes.reduce(
    (max, n) => n.endTime > max ? n.endTime : max,
    first.endTime
  );
}
function sumTokens(nodes) {
  return nodes.reduce((sum, n) => sum + n.totalTokens, 0);
}
function computeIdleTime(content, startTime, endTime) {
  const wallClockMs = endTime.getTime() - startTime.getTime();
  let totalActiveMs = 0;
  for (const child of content) {
    const childDurationMs = child.endTime.getTime() - child.startTime.getTime();
    const childActiveMs = childDurationMs - child.idleTime * 1e3;
    totalActiveMs += childActiveMs;
  }
  return Math.max(0, (wallClockMs - totalActiveMs) / 1e3);
}
function createTimelineEvent(event) {
  return {
    type: "event",
    event,
    startTime: getEventStartTime(event),
    endTime: getEventEndTime(event),
    totalTokens: getEventTokens(event),
    idleTime: 0
  };
}
function createTimelineSpan(id, name, spanType, content, utility = false, branches = [], description) {
  if (content.length === 0) {
    throw new Error(
      `createTimelineSpan called with empty content for span "${name}" (id=${id}). Callers must guard against empty content before calling the factory.`
    );
  }
  const startTime = minStartTime(content);
  const endTime = maxEndTime(content);
  return {
    type: "span",
    id,
    name: name.toLowerCase(),
    spanType,
    content,
    branches,
    description,
    utility,
    startTime,
    endTime,
    totalTokens: sumTokens(content),
    idleTime: computeIdleTime(content, startTime, endTime)
  };
}
function createBranch(forkedAt, content) {
  if (content.length === 0) {
    throw new Error(
      "createBranch called with empty content. Callers must guard against empty content before calling the factory."
    );
  }
  const startTime = minStartTime(content);
  const endTime = maxEndTime(content);
  return {
    type: "branch",
    forkedAt,
    content,
    startTime,
    endTime,
    totalTokens: sumTokens(content),
    idleTime: computeIdleTime(content, startTime, endTime)
  };
}
function buildSpanTree(events) {
  const root = [];
  const spansById = /* @__PURE__ */ new Map();
  const spanStack = [];
  for (const event of events) {
    if (event.event === "span_begin") {
      const span = {
        id: event.id,
        name: event.name,
        type: event.type ?? void 0,
        parentId: event.parent_id,
        metadata: event.metadata ?? void 0,
        children: [],
        beginEvent: event
      };
      spansById.set(span.id, span);
      if (span.parentId && spansById.has(span.parentId)) {
        spansById.get(span.parentId).children.push(span);
      } else if (spanStack.length > 0) {
        const currentSpan = spanStack[spanStack.length - 1];
        if (currentSpan) {
          currentSpan.children.push(span);
        }
      } else {
        root.push(span);
      }
      spanStack.push(span);
    } else if (event.event === "span_end") {
      const endSpan = spansById.get(event.id);
      if (endSpan) {
        endSpan.endEvent = event;
      }
      if (spanStack.length > 0) {
        spanStack.pop();
      }
    } else {
      const spanId = event.span_id;
      if (spanId && spansById.has(spanId)) {
        spansById.get(spanId).children.push(event);
      } else if (spanStack.length > 0) {
        const currentSpan = spanStack[spanStack.length - 1];
        if (currentSpan) {
          currentSpan.children.push(event);
        }
      } else {
        root.push(event);
      }
    }
  }
  return root;
}
function eventSequence(items) {
  const events = [];
  for (const item of items) {
    if (isSpanNode(item)) {
      events.push(...eventSequence(item.children));
    } else {
      events.push(item);
    }
  }
  return events;
}
function containsModelEvents(span) {
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
function eventToNode(event) {
  if (event.event === "tool") {
    const agentName = event.agent;
    const nestedEvents = event.events;
    if (agentName && nestedEvents && nestedEvents.length > 0) {
      const nestedContent = nestedEvents.map(
        (e) => eventToNode(e)
      );
      if (nestedContent.length > 0) {
        return createTimelineSpan(
          `tool-agent-${event.id}`,
          agentName,
          "agent",
          nestedContent
        );
      }
    }
  }
  return createTimelineEvent(event);
}
function isAgentSpan(span) {
  if (span.type === "agent" || span.type === "solver") {
    return true;
  }
  if (span.type === "tool" && containsModelEvents(span)) {
    return true;
  }
  return false;
}
function treeItemToNode(item, hasExplicitBranches) {
  if (isSpanNode(item)) {
    if (item.type === "agent" || item.type === "solver") {
      return buildSpanFromAgentSpan(item, hasExplicitBranches);
    } else {
      return buildSpanFromGenericSpan(item, hasExplicitBranches);
    }
  } else {
    return eventToNode(item);
  }
}
function buildSpanFromAgentSpan(span, hasExplicitBranches, extraItems) {
  const content = [];
  if (extraItems) {
    for (const item of extraItems) {
      if (isSpanNode(item) && !isAgentSpan(item)) {
        unrollSpan(item, content, hasExplicitBranches);
      } else {
        const node = treeItemToNode(item, hasExplicitBranches);
        if (node !== null) {
          content.push(node);
        }
      }
    }
  }
  const [childContent, branches] = processChildren(
    span.children,
    hasExplicitBranches
  );
  content.push(...childContent);
  if (content.length === 0) {
    return null;
  }
  const description = typeof span.metadata?.description === "string" ? span.metadata.description : void 0;
  return createTimelineSpan(
    span.id,
    span.name,
    "agent",
    content,
    false,
    branches,
    description
  );
}
function buildSpanFromGenericSpan(span, hasExplicitBranches) {
  const [content, branches] = processChildren(
    span.children,
    hasExplicitBranches
  );
  if (content.length === 0) {
    return null;
  }
  const spanType = span.type === "tool" && containsModelEvents(span) ? "agent" : span.type ?? null;
  return createTimelineSpan(
    span.id,
    span.name,
    spanType,
    content,
    false,
    branches
  );
}
function buildAgentFromSolversSpan(solversSpan, hasExplicitBranches) {
  if (solversSpan.children.length === 0) {
    return null;
  }
  const agentSpans = [];
  const otherItems = [];
  for (const child of solversSpan.children) {
    if (isSpanNode(child) && isAgentSpan(child)) {
      agentSpans.push(child);
    } else {
      otherItems.push(child);
    }
  }
  if (agentSpans.length > 0) {
    const firstAgentSpan = agentSpans[0];
    if (agentSpans.length === 1 && firstAgentSpan) {
      const result = buildSpanFromAgentSpan(
        firstAgentSpan,
        hasExplicitBranches,
        otherItems
      );
      if (result !== null) {
        return result;
      }
      return {
        type: "span",
        id: firstAgentSpan.id,
        name: firstAgentSpan.name.toLowerCase(),
        spanType: "agent",
        content: [],
        branches: [],
        utility: false,
        startTime: /* @__PURE__ */ new Date(0),
        endTime: /* @__PURE__ */ new Date(0),
        totalTokens: 0,
        idleTime: 0
      };
    } else {
      const children = [];
      for (const span of agentSpans) {
        const node = buildSpanFromAgentSpan(span, hasExplicitBranches);
        if (node !== null) {
          children.push(node);
        }
      }
      for (const item of otherItems) {
        if (isSpanNode(item) && !isAgentSpan(item)) {
          const orphanContent = [];
          unrollSpan(item, orphanContent, hasExplicitBranches);
          for (let i = orphanContent.length - 1; i >= 0; i--) {
            children.unshift(orphanContent[i]);
          }
        } else {
          const node = treeItemToNode(item, hasExplicitBranches);
          if (node !== null) {
            children.unshift(node);
          }
        }
      }
      if (children.length === 0) {
        return null;
      }
      return createTimelineSpan("root", "main", "agent", children);
    }
  } else {
    const [content, branches] = processChildren(
      solversSpan.children,
      hasExplicitBranches
    );
    if (content.length === 0) {
      return null;
    }
    return createTimelineSpan(
      solversSpan.id,
      solversSpan.name,
      "agent",
      content,
      false,
      branches
    );
  }
}
function buildAgentFromTree(tree, hasExplicitBranches) {
  const [content, branches] = processChildren(tree, hasExplicitBranches);
  if (content.length === 0) {
    return null;
  }
  return createTimelineSpan("main", "main", "agent", content, false, branches);
}
function unrollSpan(span, into, hasExplicitBranches) {
  into.push(createTimelineEvent(span.beginEvent));
  for (const child of span.children) {
    if (isSpanNode(child)) {
      if (isAgentSpan(child)) {
        const node = treeItemToNode(child, hasExplicitBranches);
        if (node !== null) {
          into.push(node);
        }
      } else {
        unrollSpan(child, into, hasExplicitBranches);
      }
    } else {
      into.push(eventToNode(child));
    }
  }
  if (span.endEvent) {
    into.push(createTimelineEvent(span.endEvent));
  }
}
function processChildren(children, hasExplicitBranches) {
  if (!hasExplicitBranches) {
    const content2 = [];
    for (const item of children) {
      if (isSpanNode(item) && !isAgentSpan(item)) {
        unrollSpan(item, content2, hasExplicitBranches);
      } else {
        const node = treeItemToNode(item, hasExplicitBranches);
        if (node === null) continue;
        content2.push(node);
      }
    }
    return [content2, []];
  }
  const content = [];
  const branches = [];
  let branchRun = [];
  function flushBranchRun(run, parentContent) {
    const result = [];
    for (const span of run) {
      const branchContent = [];
      for (const child of span.children) {
        if (isSpanNode(child) && !isAgentSpan(child)) {
          unrollSpan(child, branchContent, hasExplicitBranches);
        } else {
          const node = treeItemToNode(child, hasExplicitBranches);
          if (node === null) continue;
          branchContent.push(node);
        }
      }
      if (branchContent.length === 0) continue;
      const branchInput = getBranchInput(branchContent);
      const forkedAt = branchInput !== null ? findForkedAt(parentContent, branchInput) : "";
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
      if (isSpanNode(item) && !isAgentSpan(item)) {
        unrollSpan(item, content, hasExplicitBranches);
      } else {
        const node = treeItemToNode(item, hasExplicitBranches);
        if (node === null) continue;
        content.push(node);
      }
    }
  }
  if (branchRun.length > 0) {
    branches.push(...flushBranchRun(branchRun, content));
  }
  return [content, branches];
}
function findForkedAt(agentContent, branchInput) {
  if (branchInput.length === 0) return "";
  const lastMsg = branchInput[branchInput.length - 1];
  if (!lastMsg) return "";
  if (lastMsg.role === "tool") {
    const toolCallId = lastMsg.tool_call_id;
    if (toolCallId) {
      for (const item of agentContent) {
        if (item.type === "event" && item.event.event === "tool" && item.event.id === toolCallId) {
          return item.event.uuid ?? "";
        }
      }
    }
    return "";
  }
  if (lastMsg.role === "assistant") {
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
  return "";
}
function getBranchInput(content) {
  for (const item of content) {
    if (item.type === "event" && item.event.event === "model") {
      return item.event.input ?? null;
    }
  }
  return null;
}
function messageFingerprint(msg, cache) {
  if (cache) {
    const cached = cache.get(msg);
    if (cached !== void 0) return cached;
  }
  const role = msg.role;
  let serialized;
  if (typeof msg.content === "string") {
    serialized = msg.content;
  } else {
    serialized = JSON.stringify(msg.content);
  }
  const result = `${role}:${serialized}`;
  if (cache) {
    cache.set(msg, result);
  }
  return result;
}
function inputFingerprint(messages, cache) {
  return messages.map((m) => messageFingerprint(m, cache)).join("|");
}
function detectAutoBranches(span) {
  const fpCache = /* @__PURE__ */ new WeakMap();
  const regions = [];
  let regionStart = 0;
  for (let i = 0; i < span.content.length; i++) {
    const item = span.content[i];
    if (item && item.type === "event" && item.event.event === "compaction") {
      regions.push([regionStart, i]);
      regionStart = i + 1;
    }
  }
  regions.push([regionStart, span.content.length]);
  const branchRanges = [];
  for (const [rStart, rEnd] of regions) {
    const modelIndices = [];
    for (let i = rStart; i < rEnd; i++) {
      const item = span.content[i];
      if (item && item.type === "event" && item.event.event === "model") {
        const inputMsgs = item.event.input;
        if (!inputMsgs || inputMsgs.length === 0) continue;
        const fp = inputFingerprint(inputMsgs, fpCache);
        modelIndices.push([i, fp]);
      }
    }
    const fingerprintGroups = /* @__PURE__ */ new Map();
    for (const [idx, fp] of modelIndices) {
      const group = fingerprintGroups.get(fp);
      if (group) {
        group.push(idx);
      } else {
        fingerprintGroups.set(fp, [idx]);
      }
    }
    for (const [, indices] of fingerprintGroups) {
      if (indices.length <= 1) continue;
      const firstItem = span.content[indices[0]];
      if (!firstItem || firstItem.type !== "event" || firstItem.event.event !== "model") {
        continue;
      }
      const sharedInput = firstItem.event.input ?? [];
      for (let i = 0; i < indices.length - 1; i++) {
        const branchStart = indices[i];
        const nextReroll = indices[i + 1];
        branchRanges.push([branchStart, nextReroll, sharedInput]);
      }
    }
  }
  if (branchRanges.length === 0) return;
  branchRanges.sort((a, b) => b[0] - a[0]);
  for (const [start, end, sharedInput] of branchRanges) {
    const branchContent = span.content.slice(start, end);
    if (branchContent.length > 0) {
      const forkedAt = findForkedAt(span.content, sharedInput);
      span.branches.push(createBranch(forkedAt, branchContent));
    }
    span.content.splice(start, end - start);
  }
  span.branches.reverse();
  span.totalTokens = sumTokens(span.content);
  span.idleTime = computeIdleTime(span.content, span.startTime, span.endTime);
}
function classifyBranches(span, hasExplicitBranches, isRoot = true) {
  if (!hasExplicitBranches && !isRoot) {
    detectAutoBranches(span);
  }
  for (const item of span.content) {
    if (item.type === "span") {
      classifyBranches(item, hasExplicitBranches, false);
    }
  }
  for (const branch of span.branches) {
    for (const item of branch.content) {
      if (item.type === "span") {
        classifyBranches(item, hasExplicitBranches, false);
      }
    }
  }
  span.totalTokens = sumTokens(span.content);
  span.idleTime = computeIdleTime(span.content, span.startTime, span.endTime);
}
function getSystemPrompt(span) {
  for (const item of span.content) {
    if (item.type === "event" && item.event.event === "model") {
      const input = item.event.input;
      if (input) {
        for (const msg of input) {
          if (msg.role === "system") {
            if (typeof msg.content === "string") {
              return msg.content;
            }
            if (Array.isArray(msg.content)) {
              const parts = [];
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
      return null;
    }
  }
  return null;
}
function isSingleTurn(span) {
  const directEvents = [];
  for (const item of span.content) {
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
  if (modelCount === 1) {
    return true;
  }
  if (modelCount === 2 && toolCount >= 1) {
    const firstModel = directEvents.indexOf("model");
    const secondModel = directEvents.lastIndexOf("model");
    const between = directEvents.slice(firstModel + 1, secondModel);
    return between.includes("tool");
  }
  return false;
}
function classifyUtilityAgents(node, parentSystemPrompt = null) {
  const agentSystemPrompt = getSystemPrompt(node);
  if (parentSystemPrompt !== null && agentSystemPrompt !== null) {
    if (agentSystemPrompt !== parentSystemPrompt && isSingleTurn(node)) {
      node.utility = true;
    }
  }
  const effectivePrompt = agentSystemPrompt ?? parentSystemPrompt;
  for (const item of node.content) {
    if (item.type === "span") {
      classifyUtilityAgents(item, effectivePrompt);
    }
  }
}
function buildTimeline(events) {
  if (events.length === 0) {
    const emptyRoot = {
      type: "span",
      id: "root",
      name: "main",
      spanType: null,
      content: [],
      branches: [],
      utility: false,
      startTime: /* @__PURE__ */ new Date(0),
      endTime: /* @__PURE__ */ new Date(0),
      totalTokens: 0,
      idleTime: 0
    };
    return { name: "Default", description: "", root: emptyRoot };
  }
  const hasExplicitBranches = events.some(
    (e) => e.event === "span_begin" && e.type === "branch"
  );
  const tree = buildSpanTree(events);
  const topSpans = /* @__PURE__ */ new Map();
  for (const item of tree) {
    if (isSpanNode(item) && (item.name === "init" || item.name === "solvers" || item.name === "scorers")) {
      topSpans.set(item.name, item);
    }
  }
  const hasPhaseSpans = topSpans.has("init") || topSpans.has("solvers") || topSpans.has("scorers");
  let root;
  if (hasPhaseSpans) {
    const initSpan = topSpans.get("init");
    const solversSpan = topSpans.get("solvers");
    const scorersSpan = topSpans.get("scorers");
    let initSpanObj = null;
    if (initSpan) {
      const initContent = eventSequence(initSpan.children).map(
        (e) => createTimelineEvent(e)
      );
      if (initContent.length > 0) {
        initSpanObj = createTimelineSpan(
          initSpan.id,
          "init",
          "init",
          initContent
        );
      }
    }
    const agentNode = solversSpan ? buildAgentFromSolversSpan(solversSpan, hasExplicitBranches) : null;
    let scoringSpan = null;
    if (scorersSpan) {
      const scoringContent = eventSequence(scorersSpan.children).map(
        (e) => createTimelineEvent(e)
      );
      if (scoringContent.length > 0) {
        scoringSpan = createTimelineSpan(
          scorersSpan.id,
          "scoring",
          "scorers",
          scoringContent
        );
      }
    }
    if (agentNode) {
      if (!hasExplicitBranches) detectAutoBranches(agentNode);
      classifyUtilityAgents(agentNode);
      classifyBranches(agentNode, hasExplicitBranches);
      if (initSpanObj) {
        agentNode.content = [initSpanObj, ...agentNode.content];
        agentNode.startTime = minStartTime(agentNode.content);
        agentNode.endTime = maxEndTime(agentNode.content);
        agentNode.totalTokens = sumTokens(agentNode.content);
        agentNode.idleTime = computeIdleTime(
          agentNode.content,
          agentNode.startTime,
          agentNode.endTime
        );
      }
      if (scoringSpan) {
        agentNode.content.push(scoringSpan);
        agentNode.startTime = minStartTime(agentNode.content);
        agentNode.endTime = maxEndTime(agentNode.content);
        agentNode.totalTokens = sumTokens(agentNode.content);
        agentNode.idleTime = computeIdleTime(
          agentNode.content,
          agentNode.startTime,
          agentNode.endTime
        );
      }
      root = agentNode;
    } else {
      const rootContent = [];
      if (initSpanObj) {
        rootContent.push(initSpanObj);
      }
      if (scoringSpan) {
        rootContent.push(scoringSpan);
      }
      if (rootContent.length > 0) {
        root = createTimelineSpan("root", "main", null, rootContent);
      } else {
        root = {
          type: "span",
          id: "root",
          name: "main",
          spanType: null,
          content: [],
          branches: [],
          utility: false,
          startTime: /* @__PURE__ */ new Date(0),
          endTime: /* @__PURE__ */ new Date(0),
          totalTokens: 0,
          idleTime: 0
        };
      }
    }
  } else {
    const agentRoot = buildAgentFromTree(tree, hasExplicitBranches);
    if (agentRoot) {
      if (!hasExplicitBranches) detectAutoBranches(agentRoot);
      classifyUtilityAgents(agentRoot);
      classifyBranches(agentRoot, hasExplicitBranches);
      root = agentRoot;
    } else {
      root = {
        type: "span",
        id: "root",
        name: "main",
        spanType: null,
        content: [],
        branches: [],
        utility: false,
        startTime: /* @__PURE__ */ new Date(0),
        endTime: /* @__PURE__ */ new Date(0),
        totalTokens: 0,
        idleTime: 0
      };
    }
  }
  return { name: "Default", description: "", root };
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
  const envelope = computeTimeEnvelope(branches);
  const duration = formatDuration(envelope.startTime, envelope.endTime);
  const label2 = count === 1 ? "1 branch" : `${count} branches`;
  return `${label2} (${tokenStr}, ${duration})`;
}
function formatCompactTokens(tokens2) {
  return `${formatTokenCount(tokens2)} tokens`;
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
function partitionIntoClusters(sorted) {
  if (sorted.length === 0) return [];
  const clusters = [];
  let current = [sorted[0]];
  let clusterEnd = sorted[0].endTime.getTime();
  for (let i = 1; i < sorted.length; i++) {
    const span = sorted[i];
    if (span.startTime.getTime() < clusterEnd + OVERLAP_TOLERANCE_MS) {
      current.push(span);
      clusterEnd = Math.max(clusterEnd, span.endTime.getTime());
    } else {
      clusters.push(current);
      current = [span];
      clusterEnd = span.endTime.getTime();
    }
  }
  clusters.push(current);
  return clusters;
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
  const rowSpans = partitionIntoClusters(sorted).map(
    (cluster) => cluster.length === 1 ? { agent: cluster[0] } : { agents: cluster }
  );
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
function drillableChildCount(span) {
  if (isParallelSpan(span)) return span.agents.length;
  if (isSingleSpan(span)) {
    return span.agent.content.filter(
      (item) => item.type === "span" && !item.utility
    ).length;
  }
  return 0;
}
function computeTimeEnvelope(items) {
  const first = items[0];
  let startTime = first.startTime;
  let endTime = first.endTime;
  for (let i = 1; i < items.length; i++) {
    const item = items[i];
    if (item.startTime < startTime) startTime = item.startTime;
    if (item.endTime > endTime) endTime = item.endTime;
  }
  return { startTime, endTime };
}
function formatTokenCount(tokens2) {
  if (tokens2 >= 999950) {
    return `${formatPrettyDecimal(tokens2 / 1e6, 1)}M`;
  }
  if (tokens2 >= 1e3) {
    return `${formatPrettyDecimal(tokens2 / 1e3, 1)}k`;
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
        const drillable = !isParent && isDrillable(rowSpan);
        return {
          bar: bar2,
          drillable,
          childCount: drillable ? drillableChildCount(rowSpan) : 0,
          parallelCount: null,
          description: rowSpan.agent.description ?? null
        };
      }
      const agents = rowSpan.agents;
      const envelope = computeTimeEnvelope(agents);
      const bar = computeBarPosition(
        envelope.startTime,
        envelope.endTime,
        viewStart,
        viewEnd
      );
      return {
        bar,
        drillable: !isParent,
        childCount: !isParent ? agents.length : 0,
        parallelCount: agents.length,
        description: null
      };
    });
    const markers = collectRowMarkers(row2, markerDepth, viewStart, viewEnd);
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
function spanHasEvents(span) {
  for (const item of span.content) {
    if (item.type === "event") return true;
    if (item.type === "span" && spanHasEvents(item)) return true;
  }
  return false;
}
function rowHasEvents(row2) {
  return row2.spans.some((rowSpan) => getAgents(rowSpan).some(spanHasEvents));
}
function collectRowMarkers(row2, depth, viewStart, viewEnd) {
  const allMarkers = [];
  for (const rowSpan of row2.spans) {
    const agents = getAgents(rowSpan);
    for (const agent of agents) {
      const markers = collectMarkers(agent, depth);
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
  const { startTime, endTime } = computeTimeEnvelope(agents);
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
    totalTokens,
    idleTime: computeIdleTime(numberedAgents, startTime, endTime)
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
    totalTokens: branch.totalTokens,
    idleTime: branch.idleTime
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
  const selected2 = reactExports.useMemo(() => {
    if (selectedParam !== null) return selectedParam;
    return rows[0]?.name ?? null;
  }, [selectedParam, rows]);
  const breadcrumbs = reactExports.useMemo(
    () => buildBreadcrumbs(pathString, timeline),
    [pathString, timeline]
  );
  const drillDown2 = reactExports.useCallback(
    (name, spanIndex) => {
      const segment = spanIndex ? `${name}-${spanIndex}` : name;
      const newPath = pathString ? `${pathString}/${segment}` : segment;
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set(kPathParam, newPath);
        next.delete(kSelectedParam);
        next.delete("event");
        next.delete("message");
        return next;
      });
    },
    [pathString, setSearchParams]
  );
  const goUp = reactExports.useCallback(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("event");
      next.delete("message");
      if (next.has(kSelectedParam)) {
        next.delete(kSelectedParam);
        return next;
      }
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
      return next;
    });
  }, [pathString, setSearchParams]);
  const navigateTo = reactExports.useCallback(
    (path) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (path) {
          next.set(kPathParam, path);
        } else {
          next.delete(kPathParam);
        }
        next.delete(kSelectedParam);
        next.delete("event");
        next.delete("message");
        return next;
      });
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
          next.delete("event");
          next.delete("message");
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
    selected: selected2,
    drillDown: drillDown2,
    goUp,
    navigateTo,
    select
  };
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
  selection
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
  const timeRightLabel = formatDuration(root.startTime, root.endTime);
  const tokenRightLabel = formatTokenCount(root.totalTokens);
  const sectionLabel = selection && isTokenMode ? formatTokenCount(selection.totalTokens) : selection ? useShortFormat ? formatDurationShort(selection.startTime, selection.endTime) : formatDuration(selection.startTime, selection.endTime) : "";
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
const swimlane = "_swimlane_8a9rm_1";
const pinnedSection = "_pinnedSection_8a9rm_17";
const scrollSection = "_scrollSection_8a9rm_25";
const collapsibleSection = "_collapsibleSection_8a9rm_40";
const collapsibleCollapsed = "_collapsibleCollapsed_8a9rm_53";
const noAnimation = "_noAnimation_8a9rm_60";
const swimlaneSticky = "_swimlaneSticky_8a9rm_65";
const collapsibleInner = "_collapsibleInner_8a9rm_72";
const collapseToggle = "_collapseToggle_8a9rm_82";
const row = "_row_8a9rm_110";
const label = "_label_8a9rm_116";
const labelChild = "_labelChild_8a9rm_128";
const labelSelected = "_labelSelected_8a9rm_132";
const barArea = "_barArea_8a9rm_138";
const barInner = "_barInner_8a9rm_144";
const fill = "_fill_8a9rm_150";
const fillParent = "_fillParent_8a9rm_168";
const fillSelected = "_fillSelected_8a9rm_172";
const parallelBadge = "_parallelBadge_8a9rm_177";
const drillDown = "_drillDown_8a9rm_184";
const marker = "_marker_8a9rm_209";
const markerError = "_markerError_8a9rm_229";
const markerCompaction = "_markerCompaction_8a9rm_250";
const markerBranch = "_markerBranch_8a9rm_262";
const branchPopover = "_branchPopover_8a9rm_269";
const branchEntry = "_branchEntry_8a9rm_275";
const branchLabel = "_branchLabel_8a9rm_295";
const branchMeta = "_branchMeta_8a9rm_299";
const breadcrumbRow = "_breadcrumbRow_8a9rm_311";
const breadcrumbBack = "_breadcrumbBack_8a9rm_321";
const breadcrumbGroup = "_breadcrumbGroup_8a9rm_344";
const breadcrumbLink = "_breadcrumbLink_8a9rm_351";
const breadcrumbCurrent = "_breadcrumbCurrent_8a9rm_364";
const breadcrumbSelection = "_breadcrumbSelection_8a9rm_378";
const breadcrumbDivider = "_breadcrumbDivider_8a9rm_392";
const tokens = "_tokens_8a9rm_400";
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
  parallelBadge,
  drillDown,
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
  selected: selected2,
  node,
  onSelect,
  onDrillDown,
  onGoUp,
  minimap: minimap2,
  breadcrumb,
  isSticky,
  forceCollapsed,
  noAnimation: noAnimation2,
  showErrorMarkers,
  onMarkerNavigate
}) => {
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
      showErrorMarkers,
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
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.pinnedSection, children: breadcrumb && /* @__PURE__ */ jsxRuntimeExports.jsx(BreadcrumbRow, { ...breadcrumb, minimap: minimap2 }) }),
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
                breadcrumb?.atRoot && parentRow.name === "solvers" ? "main" : void 0
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
  showErrorMarkers,
  onMarkerNavigate
}) => {
  const hasSelectedSpan = layout.spans.some(
    (_, i) => isSpanSelected(layout, i, parsedSelection)
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.row, role: "row", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(
          styles.label,
          !layout.isParent && styles.labelChild,
          hasSelectedSpan && styles.labelSelected
        ),
        children: [
          displayName ?? layout.name,
          layout.parallelCount !== null && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles.parallelBadge, children: [
            "(",
            layout.parallelCount,
            ")"
          ] })
        ]
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
      layout.markers.filter((m) => showErrorMarkers || m.kind !== "error").map((marker2, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(
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
    ),
    span.drillable && /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        className: styles.drillDown,
        style: {
          left: `${span.bar.left + span.bar.width}%`
        },
        onClick: handleChevronClick,
        title: `Drill down (${span.childCount} sub-agent${span.childCount !== 1 ? "s" : ""})`,
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.chevron.right })
      }
    )
  ] });
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
function findRowByName(rows, name) {
  return rows.find((r) => r.name.toLowerCase() === name.toLowerCase());
}
function getSelectedSpans(rows, selected2) {
  if (!selected2) return [];
  const { name, spanIndex } = parsePathSegment(selected2);
  const row2 = findRowByName(rows, name);
  if (!row2) return [];
  const result = [];
  const targetIndex = spanIndex !== null ? spanIndex - 1 : null;
  for (let i = 0; i < row2.spans.length; i++) {
    const rowSpan = row2.spans[i];
    if (isSingleSpan(rowSpan)) {
      if (targetIndex === null || i === targetIndex) {
        result.push(rowSpan.agent);
      }
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
function computeMinimapSelection(rows, selected2) {
  if (!selected2) return void 0;
  const { name, spanIndex } = parsePathSegment(selected2);
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
      const envelope = computeTimeEnvelope(agents);
      const tokens2 = agents.reduce((sum, a) => sum + a.totalTokens, 0);
      return { ...envelope, totalTokens: tokens2 };
    }
  }
  return void 0;
}
function collectRawEvents(spans) {
  const events = [];
  if (spans.length === 1) {
    collectFromContent(spans[0].content, events);
  } else {
    collectFromContent(spans, events);
  }
  return events;
}
function collectFromContent(content, out) {
  for (const item of content) {
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
export {
  TimelineSwimLanes as T,
  collectRawEvents as a,
  buildTimeline as b,
  computeRowLayouts as c,
  computeMinimapSelection as d,
  TranscriptOutline as e,
  getSelectedSpans as g,
  rowHasEvents as r,
  useTimeline as u
};
//# sourceMappingURL=timelineEventNodes.js.map
