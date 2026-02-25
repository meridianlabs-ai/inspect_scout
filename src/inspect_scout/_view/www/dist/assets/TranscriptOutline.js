import { r as reactExports, j as jsxRuntimeExports, c as clsx, $ as Link, A as ApplicationIcons, u as useStore } from "./index.js";
import { l as useCollapseTranscriptEvent, P as PulsingDots, m as kSandboxSignalName, E as EventNode, n as TYPE_SCORERS, o as TYPE_SCORER, p as useVirtuosoState, q as useTranscriptNavigation, s as flatTree, t as kTranscriptOutlineCollapseScope, v as useScrollTrack, Y as Yr } from "./TranscriptViewNodes.js";
import "./ToolButton.js";
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
const label = "_label_1j0jk_28";
const icon = "_icon_1j0jk_34";
const progress = "_progress_1j0jk_38";
const styles$1 = {
  eventRow,
  selected,
  toggle,
  eventLink,
  label,
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
        styles$1.eventRow,
        "text-size-smaller",
        selected2 ? styles$1.selected : ""
      ),
      style: { paddingLeft: `${node.depth * 0.4}em` },
      "data-unsearchable": true,
      onClick: () => onSelect?.(node.id),
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(styles$1.toggle),
            onClick: () => {
              setCollapsed(!collapsed);
            },
            children: toggle2 ? /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(toggle2) }) : void 0
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$1.label), "data-depth": node.depth, children: [
          icon2 ? /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(icon2, styles$1.icon) }) : void 0,
          eventUrl ? /* @__PURE__ */ jsxRuntimeExports.jsx(Link, { to: eventUrl, className: clsx(styles$1.eventLink), ref, children: parsePackageName(labelForNode(node)).module }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { ref, children: parsePackageName(labelForNode(node)).module }),
          running ? /* @__PURE__ */ jsxRuntimeExports.jsx(
            PulsingDots,
            {
              size: "small",
              className: clsx(styles$1.progress),
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
const styles = {};
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
  style
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
            className: clsx(styles.eventPadding),
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
export {
  TranscriptOutline as T
};
//# sourceMappingURL=TranscriptOutline.js.map
