import { bP as useParams, r as reactExports, w as loading, x as data, y as skipToken, u as useApi, a as useAsyncDataFromQuery, j as jsxRuntimeExports, g as clsx, bT as Link, bU as PulsingDots, e as ApplicationIcons, l as useStore, m as useSearchParams, D as getValidationParam, F as updateValidationParam, n as useLoggingNavigate, B as transcriptRoute, f as useAppConfig, E as ErrorPanel, A as ApiError } from "./index.js";
import { P as PopOver, T as ToolButton, b as formatDateTime, d as formatNumber, e as formatTime, L as LoadingBar } from "./ToolButton.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { u as useFilterConditions, T as TranscriptsNavbar } from "./useFilterConditions.js";
import { u as useServerTranscriptsInfinite, T as TRANSCRIPTS_INFINITE_SCROLL_CONFIG } from "./constants.js";
import { C as ChatViewVirtualList, V as ValidationCaseEditor, N as NextPreviousNav, g as getTranscriptDisplayName } from "./NextPreviousNav.js";
import { u as useTranscriptsDir } from "./useTranscriptsDir.js";
import { h as VscodeSplitLayout } from "./VscodeTreeItem.js";
import { h as useCollapseTranscriptEvent, k as kSandboxSignalName, E as EventNode, j as TYPE_SCORERS, l as TYPE_SCORER, m as useVirtuosoState, n as useTranscriptNavigation, o as flatTree, p as kTranscriptOutlineCollapseScope, q as useScrollTrack, Y as Yr, r as eventTypeValues, u as useEventNodes, s as kTranscriptCollapseScope, c as TabPanel, f as TranscriptViewNodes, M as MetaDataGrid, b as TabSet, D as DisplayModeContext, t as kCollapsibleEventTypes, T as TaskName, S as ScoreValue } from "./TranscriptViewNodes.js";
import { T as ToolDropdownButton } from "./ToolDropdownButton.js";
import "./_commonjsHelpers.js";
import "./index2.js";
import "./Modal.js";
import "./FormFields.js";
import "./ValidationSplitSelector.js";
import "./Chip.js";
import "./chunk-DfAF0w94.js";
import "./NoContentsPanel.js";
const parsePackageName = (name) => {
  if (name.includes("/")) {
    const [packageName, moduleName] = name.split("/", 2);
    return { package: packageName || "", module: moduleName || "" };
  }
  return { package: "", module: name };
};
function useRequiredParams(...keys) {
  const params = useParams();
  const result = {};
  for (const key of keys) {
    const value2 = params[key];
    if (!value2) {
      throw new Error(`Missing required route param: ${key}`);
    }
    result[key] = value2;
  }
  return result;
}
const useAdjacentTranscriptIds = (id, location, pageSize, filter, sorting) => {
  const {
    data: queryData,
    error,
    isLoading,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage
  } = useServerTranscriptsInfinite(
    location ? { location, pageSize, filter, sorting } : skipToken
  );
  const pages = queryData?.pages;
  const position = reactExports.useMemo(
    () => pages ? findPosition(pages, id) : null,
    [pages, id]
  );
  const needsNextPage = pages !== void 0 && position !== null && isLastLoadedItem(pages, position) && hasNextPage && !isFetchingNextPage;
  reactExports.useEffect(() => {
    if (needsNextPage) {
      fetchNextPage().catch(console.error);
    }
  }, [needsNextPage, fetchNextPage]);
  if (isLoading) {
    return loading;
  }
  if (error) {
    return { loading: false, error };
  }
  if (pages === void 0 || position === null) {
    return loading;
  }
  return data(getAdjacentIds(pages, position));
};
const findPosition = (pages, id) => {
  for (let p = 0; p < pages.length; p++) {
    const page = pages[p];
    if (!page) continue;
    const i = page.items.findIndex((item) => item.transcript_id === id);
    if (i >= 0) return { pageIndex: p, itemIndex: i };
  }
  return null;
};
const getAdjacentIds = (pages, pos) => {
  const page = pages[pos.pageIndex];
  const prevId = pos.itemIndex > 0 ? page.items[pos.itemIndex - 1]?.transcript_id : pages[pos.pageIndex - 1]?.items.at(-1)?.transcript_id;
  const nextId = pos.itemIndex < page.items.length - 1 ? page.items[pos.itemIndex + 1]?.transcript_id : pages[pos.pageIndex + 1]?.items[0]?.transcript_id;
  return [prevId, nextId];
};
const isLastLoadedItem = (pages, pos) => pos.pageIndex === pages.length - 1 && pos.itemIndex === pages[pos.pageIndex].items.length - 1;
const useTranscript = (params) => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: params === skipToken ? [skipToken] : ["transcript", params],
    queryFn: params === skipToken ? skipToken : () => api.getTranscript(params.location, params.id),
    staleTime: Infinity
  });
};
const StickyScroll = ({
  children,
  scrollRef,
  offsetTop = 0,
  zIndex = 100,
  className = "",
  stickyClassName = "is-sticky",
  onStickyChange
}) => {
  const wrapperRef = reactExports.useRef(null);
  const contentRef = reactExports.useRef(null);
  const [isSticky, setIsSticky] = reactExports.useState(false);
  const [dimensions, setDimensions] = reactExports.useState({
    width: 0,
    height: 0,
    left: 0,
    stickyTop: 0
    // Store the position where the element should stick
  });
  reactExports.useEffect(() => {
    const wrapper = wrapperRef.current;
    const content = contentRef.current;
    const scrollContainer = scrollRef.current;
    if (!wrapper || !content || !scrollContainer) {
      return;
    }
    const sentinel = document.createElement("div");
    sentinel.style.position = "absolute";
    sentinel.style.top = "0px";
    sentinel.style.left = "0";
    sentinel.style.width = "1px";
    sentinel.style.height = "1px";
    sentinel.style.pointerEvents = "none";
    wrapper.prepend(sentinel);
    const widthTracker = document.createElement("div");
    widthTracker.style.position = "absolute";
    widthTracker.style.top = "0";
    widthTracker.style.left = "0";
    widthTracker.style.width = "100%";
    widthTracker.style.height = "0";
    widthTracker.style.pointerEvents = "none";
    widthTracker.style.visibility = "hidden";
    wrapper.prepend(widthTracker);
    const updateDimensions = () => {
      if (wrapper && scrollContainer) {
        const contentRect = content.getBoundingClientRect();
        const containerRect = scrollContainer.getBoundingClientRect();
        const trackerRect = widthTracker.getBoundingClientRect();
        const stickyTop = containerRect.top + offsetTop;
        setDimensions({
          // Use the width tracker to get the right width that respects
          // the parent container's current width, rather than the content's width
          width: trackerRect.width,
          height: contentRect.height,
          left: trackerRect.left,
          stickyTop
        });
      }
    };
    updateDimensions();
    const resizeObserver = new ResizeObserver(() => {
      requestAnimationFrame(() => {
        updateDimensions();
        if (isSticky) {
          handleScroll();
        }
      });
    });
    resizeObserver.observe(wrapper);
    resizeObserver.observe(scrollContainer);
    resizeObserver.observe(content);
    const handleScroll = () => {
      const sentinelRect = sentinel.getBoundingClientRect();
      const containerRect = scrollContainer.getBoundingClientRect();
      const shouldBeSticky = sentinelRect.top < containerRect.top + offsetTop;
      if (shouldBeSticky !== isSticky) {
        updateDimensions();
        setIsSticky(shouldBeSticky);
        if (onStickyChange) {
          onStickyChange(shouldBeSticky);
        }
      }
    };
    scrollContainer.addEventListener("scroll", handleScroll);
    handleScroll();
    return () => {
      resizeObserver.disconnect();
      scrollContainer.removeEventListener("scroll", handleScroll);
      if (sentinel.parentNode) {
        sentinel.parentNode.removeChild(sentinel);
      }
      if (widthTracker.parentNode) {
        widthTracker.parentNode.removeChild(widthTracker);
      }
    };
  }, [scrollRef, offsetTop, onStickyChange, isSticky]);
  const wrapperStyle = {
    position: "relative",
    height: isSticky ? `${dimensions.height}px` : "auto"
    // Don't constrain width - let it flow naturally with the content
  };
  const contentStyle = isSticky ? {
    position: "fixed",
    top: `${dimensions.stickyTop}px`,
    left: `${dimensions.left}px`,
    width: `${dimensions.width}px`,
    // Keep explicit width to prevent expanding to 100%
    maxHeight: `calc(100vh - ${dimensions.stickyTop}px)`,
    zIndex
  } : {};
  const contentClassName = isSticky && stickyClassName ? `${className} ${stickyClassName}`.trim() : className;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: wrapperRef, style: wrapperStyle, children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: contentRef, className: contentClassName, style: contentStyle, children }) });
};
const eventRow = "_eventRow_1j0jk_1";
const selected$1 = "_selected_1j0jk_8";
const toggle = "_toggle_1j0jk_12";
const eventLink = "_eventLink_1j0jk_17";
const label$1 = "_label_1j0jk_28";
const icon = "_icon_1j0jk_34";
const progress = "_progress_1j0jk_38";
const styles$6 = {
  eventRow,
  selected: selected$1,
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
  getEventUrl
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
        styles$6.eventRow,
        "text-size-smaller",
        selected2 ? styles$6.selected : ""
      ),
      style: { paddingLeft: `${node.depth * 0.4}em` },
      "data-unsearchable": true,
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(styles$6.toggle),
            onClick: () => {
              setCollapsed(!collapsed);
            },
            children: toggle2 ? /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(toggle2) }) : void 0
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$6.label), "data-depth": node.depth, children: [
          icon2 ? /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(icon2, styles$6.icon) }) : void 0,
          eventUrl ? /* @__PURE__ */ jsxRuntimeExports.jsx(Link, { to: eventUrl, className: clsx(styles$6.eventLink), ref, children: parsePackageName(labelForNode(node)).module }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { ref, children: parsePackageName(labelForNode(node)).module }),
          running ? /* @__PURE__ */ jsxRuntimeExports.jsx(
            PulsingDots,
            {
              size: "small",
              className: clsx(styles$6.progress),
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
const styles$5 = {};
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
            className: clsx(styles$5.eventPadding),
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
            getEventUrl
          },
          node.id
        );
      }
    },
    [outlineNodeList, running, selectedOutlineId, getEventUrl]
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
const messagesToStr = (messages, options) => {
  const opts = {};
  return messages.map((msg) => messageToStr(msg, opts)).filter((str) => str !== null).join("\n");
};
const messageToStr = (message, options) => {
  if (options.excludeSystem && message.role === "system") {
    return null;
  }
  const content = betterContentText(
    message.content,
    options.excludeToolUsage || false,
    options.excludeReasoning || false
  );
  if (!options.excludeToolUsage && message.role === "assistant" && message.tool_calls) {
    const assistantMsg = message;
    let entry = `${message.role.toUpperCase()}:
${content}
`;
    if (assistantMsg.tool_calls) {
      for (const tool of assistantMsg.tool_calls) {
        const funcName = tool.function;
        const args = tool.arguments;
        if (typeof args === "object" && args !== null) {
          const argsText = Object.entries(args).map(([k, v]) => `${k}: ${String(v)}`).join("\n");
          entry += `
Tool Call: ${funcName}
Arguments:
${argsText}
`;
        } else {
          entry += `
Tool Call: ${funcName}
`;
        }
      }
    }
    return entry;
  }
  if (message.role === "tool") {
    if (options.excludeToolUsage) {
      return null;
    }
    const toolMsg = message;
    const funcName = toolMsg.function || "unknown";
    const errorPart = toolMsg.error ? `

Error in tool call '${funcName}':
${toolMsg.error.message}
` : "";
    return `${message.role.toUpperCase()}:
${content}${errorPart}
`;
  }
  return `${message.role.toUpperCase()}:
${content}
`;
};
const textFromContent = (content, excludeToolUsage, excludeReasoning) => {
  switch (content.type) {
    case "text":
      return content.text;
    case "reasoning": {
      const reasoningContent = content;
      if (excludeReasoning) {
        return null;
      }
      const reasoning = reasoningContent.redacted ? reasoningContent.summary : reasoningContent.reasoning;
      if (!reasoning) {
        return null;
      }
      return `
<think>${reasoning}</think>`;
    }
    case "tool_use": {
      if (excludeToolUsage) {
        return null;
      }
      const toolUse = content;
      const errorStr = toolUse.error ? ` ${toolUse.error}` : "";
      return `
Tool Use: ${toolUse.name}(${toolUse.arguments}) -> ${toolUse.result}${errorStr}`;
    }
    case "image":
    case "audio":
    case "video":
    case "data":
    case "document":
      return `<${content.type} />`;
    default:
      return null;
  }
};
const betterContentText = (content, excludeToolUsage, excludeReasoning) => {
  if (typeof content === "string") {
    return content;
  }
  const allText = content.map((c) => textFromContent(c, excludeToolUsage, excludeReasoning)).filter((text) => text !== null);
  return allText.join("\n");
};
const kDefaultExcludedEventTypes = [
  "sample_init",
  "sandbox",
  "state",
  "store"
];
const useTranscriptColumnFilter = () => {
  const excludedEventTypes = useStore((state) => state.transcriptState.excludedTypes) || kDefaultExcludedEventTypes;
  const setTranscriptState = useStore((state) => state.setTranscriptState);
  const setExcludedEventTypes = reactExports.useCallback(
    (newTypes) => {
      setTranscriptState((prev) => ({
        ...prev,
        excludedTypes: [...newTypes]
      }));
    },
    [setTranscriptState]
  );
  const toggleEventType = reactExports.useCallback(
    (type, isCurrentlyExcluded) => {
      const newExcluded = new Set(
        excludedEventTypes
      );
      if (isCurrentlyExcluded) {
        newExcluded.delete(type);
      } else {
        newExcluded.add(type);
      }
      setExcludedEventTypes(Array.from(newExcluded));
    },
    [excludedEventTypes, setExcludedEventTypes]
  );
  const setDebugFilter = reactExports.useCallback(() => {
    setExcludedEventTypes([]);
  }, [setExcludedEventTypes]);
  const setDefaultFilter = reactExports.useCallback(() => {
    setExcludedEventTypes([...kDefaultExcludedEventTypes]);
  }, [setExcludedEventTypes]);
  const isDefaultFilter = reactExports.useMemo(() => {
    return excludedEventTypes.length === kDefaultExcludedEventTypes.length && excludedEventTypes.every(
      (type) => kDefaultExcludedEventTypes.includes(type)
    );
  }, [excludedEventTypes]);
  const isDebugFilter = reactExports.useMemo(() => {
    return excludedEventTypes.length === 0;
  }, [excludedEventTypes]);
  const arrangedEventTypes = reactExports.useCallback((columns = 1) => {
    const sortedKeys = [...eventTypeValues].sort((a, b) => {
      const aIsDefault = kDefaultExcludedEventTypes.includes(a);
      const bIsDefault = kDefaultExcludedEventTypes.includes(b);
      if (aIsDefault && !bIsDefault) return 1;
      if (!aIsDefault && bIsDefault) return -1;
      return a.localeCompare(b);
    });
    if (columns === 1) {
      return sortedKeys;
    }
    const itemsPerColumn = Math.ceil(sortedKeys.length / columns);
    const columnArrays = [];
    for (let col = 0; col < columns; col++) {
      const start = col * itemsPerColumn;
      const end = Math.min(start + itemsPerColumn, sortedKeys.length);
      columnArrays.push(sortedKeys.slice(start, end));
    }
    const arrangedKeys = [];
    const maxItemsInColumn = Math.max(...columnArrays.map((col) => col.length));
    for (let row2 = 0; row2 < maxItemsInColumn; row2++) {
      for (let col = 0; col < columns; col++) {
        const item = columnArrays[col]?.[row2];
        if (item !== void 0) {
          arrangedKeys.push(item);
        }
      }
    }
    return arrangedKeys;
  }, []);
  return {
    excludedEventTypes,
    isDefaultFilter,
    isDebugFilter,
    setDefaultFilter,
    setDebugFilter,
    toggleEventType,
    arrangedEventTypes
  };
};
const tabs = "_tabs_8gcnx_7";
const chatTab = "_chatTab_8gcnx_24";
const metadata = "_metadata_8gcnx_32";
const scrollable = "_scrollable_8gcnx_37";
const eventsSeparator = "_eventsSeparator_8gcnx_43";
const eventsList = "_eventsList_8gcnx_47";
const eventsContainer = "_eventsContainer_8gcnx_51";
const outlineCollapsed = "_outlineCollapsed_8gcnx_60";
const eventsTab = "_eventsTab_8gcnx_64";
const eventsOutline = "_eventsOutline_8gcnx_68";
const outlineToggle = "_outlineToggle_8gcnx_73";
const tabTool = "_tabTool_8gcnx_81";
const splitLayout = "_splitLayout_8gcnx_86";
const splitStart = "_splitStart_8gcnx_91";
const validationSidebar = "_validationSidebar_8gcnx_96";
const styles$4 = {
  tabs,
  chatTab,
  metadata,
  scrollable,
  eventsSeparator,
  eventsList,
  eventsContainer,
  outlineCollapsed,
  eventsTab,
  eventsOutline,
  outlineToggle,
  tabTool,
  splitLayout,
  splitStart,
  validationSidebar
};
const grid = "_grid_1ml4j_1";
const row = "_row_1ml4j_8";
const links = "_links_1ml4j_22";
const selected = "_selected_1ml4j_40";
const styles$3 = {
  grid,
  row,
  links,
  selected
};
const TranscriptFilterPopover = ({
  showing,
  positionEl,
  setShowing
}) => {
  const {
    excludedEventTypes,
    isDefaultFilter,
    isDebugFilter,
    setDefaultFilter,
    setDebugFilter,
    toggleEventType,
    arrangedEventTypes
  } = useTranscriptColumnFilter();
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    PopOver,
    {
      id: `transcript-filter-popover`,
      positionEl,
      isOpen: showing,
      setIsOpen: setShowing,
      placement: "bottom-end",
      hoverDelay: -1,
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$3.links, "text-size-smaller"), children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "a",
            {
              className: clsx(
                styles$3.link,
                isDefaultFilter ? styles$3.selected : void 0
              ),
              onClick: () => setDefaultFilter(),
              children: "Default"
            }
          ),
          "|",
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "a",
            {
              className: clsx(
                styles$3.link,
                isDebugFilter ? styles$3.selected : void 0
              ),
              onClick: () => setDebugFilter(),
              children: "Debug"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$3.grid, "text-size-smaller"), children: arrangedEventTypes(2).map((eventType) => {
          const isExcluded = excludedEventTypes.includes(eventType);
          return /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "div",
            {
              className: clsx(styles$3.row),
              onClick: () => {
                toggleEventType(eventType, isExcluded);
              },
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "input",
                  {
                    type: "checkbox",
                    checked: !isExcluded,
                    onChange: (e) => {
                      e.stopPropagation();
                      toggleEventType(eventType, isExcluded);
                    }
                  }
                ),
                eventType
              ]
            },
            eventType
          );
        }) })
      ]
    }
  );
};
const kTranscriptMessagesTabId = "transcript-messages";
const kTranscriptEventsTabId = "transcript-events";
const kTranscriptMetadataTabId = "transcript-metadata";
const kTranscriptInfoTabId = "transcript-info";
const collectAllCollapsibleIds = (nodes) => {
  const result = {};
  const traverse = (nodeList) => {
    for (const node of nodeList) {
      if (kCollapsibleEventTypes.includes(node.event.event)) {
        result[node.id] = true;
      }
      if (node.children.length > 0) {
        traverse(node.children);
      }
    }
  };
  traverse(nodes);
  return result;
};
const TranscriptBody = ({
  transcript,
  scrollRef
}) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const eventParam = searchParams.get("event");
  const messageParam = searchParams.get("message");
  const selectedTranscriptTab = useStore(
    (state) => state.selectedTranscriptTab
  );
  const setSelectedTranscriptTab = useStore(
    (state) => state.setSelectedTranscriptTab
  );
  const resolvedSelectedTranscriptTab = tabParam || selectedTranscriptTab || kTranscriptMessagesTabId;
  const handleTabChange = reactExports.useCallback(
    (tabId) => {
      setSelectedTranscriptTab(tabId);
      setSearchParams((prevParams) => {
        const newParams = new URLSearchParams(prevParams);
        newParams.set("tab", tabId);
        return newParams;
      });
    },
    [setSelectedTranscriptTab, setSearchParams]
  );
  reactExports.useEffect(() => {
    if (eventParam && resolvedSelectedTranscriptTab !== kTranscriptEventsTabId) {
      handleTabChange(kTranscriptEventsTabId);
    } else if (messageParam && resolvedSelectedTranscriptTab !== kTranscriptMessagesTabId) {
      handleTabChange(kTranscriptMessagesTabId);
    }
  }, [
    eventParam,
    messageParam,
    resolvedSelectedTranscriptTab,
    handleTabChange
  ]);
  const transcriptFilterButtonRef = reactExports.useRef(null);
  const [transcriptFilterShowing, setTranscriptFilterShowing] = reactExports.useState(false);
  const toggleTranscriptFilterShowing = reactExports.useCallback(() => {
    setTranscriptFilterShowing((prev) => !prev);
  }, []);
  const { excludedEventTypes, isDebugFilter, isDefaultFilter } = useTranscriptColumnFilter();
  const filteredEvents = reactExports.useMemo(() => {
    if (excludedEventTypes.length === 0) {
      return transcript.events;
    }
    return transcript.events.filter((event) => {
      return !excludedEventTypes.includes(event.event);
    });
  }, [transcript.events, excludedEventTypes]);
  const { eventNodes, defaultCollapsedIds } = useEventNodes(
    filteredEvents,
    false
  );
  const eventsCollapsed = useStore((state) => state.transcriptState.collapsed);
  const setTranscriptState = useStore((state) => state.setTranscriptState);
  const collapseEvents = reactExports.useCallback(
    (collapsed) => {
      setTranscriptState((prev) => ({
        ...prev,
        collapsed
      }));
    },
    [setTranscriptState]
  );
  const setCollapsedEvents = useStore(
    (state) => state.setTranscriptCollapsedEvents
  );
  const outlineCollapsed2 = useStore(
    (state) => state.transcriptState.outlineCollapsed
  );
  const toggleOutline = reactExports.useCallback(
    (collapsed) => {
      setTranscriptState((prev) => ({
        ...prev,
        outlineCollapsed: collapsed
      }));
    },
    [setTranscriptState]
  );
  const validationSidebarCollapsed = !getValidationParam(searchParams);
  const toggleValidationSidebar = reactExports.useCallback(() => {
    setSearchParams((prevParams) => {
      const isCurrentlyOpen = getValidationParam(prevParams);
      return updateValidationParam(prevParams, !isCurrentlyOpen);
    });
  }, [setSearchParams]);
  const displayMode = useStore(
    (state) => state.transcriptState.displayMode ?? "rendered"
  );
  const toggleDisplayMode = reactExports.useCallback(() => {
    setTranscriptState((prev) => ({
      ...prev,
      displayMode: prev.displayMode === "raw" ? "rendered" : "raw"
    }));
  }, [setTranscriptState]);
  const displayModeContextValue = reactExports.useMemo(
    () => ({ displayMode }),
    [displayMode]
  );
  reactExports.useEffect(() => {
    if (transcript.events.length <= 0 || eventsCollapsed === void 0) {
      return;
    }
    if (!eventsCollapsed && Object.keys(defaultCollapsedIds).length > 0) {
      setCollapsedEvents(kTranscriptCollapseScope, defaultCollapsedIds);
    } else if (eventsCollapsed) {
      const allCollapsibleIds = collectAllCollapsibleIds(eventNodes);
      setCollapsedEvents(kTranscriptCollapseScope, allCollapsibleIds);
    }
  }, [
    defaultCollapsedIds,
    eventNodes,
    eventsCollapsed,
    setCollapsedEvents,
    transcript.events.length
  ]);
  const tabTools = [];
  if (resolvedSelectedTranscriptTab === kTranscriptEventsTabId) {
    const label2 = isDebugFilter ? "Debug" : isDefaultFilter ? "Default" : "Custom";
    tabTools.push(
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        ToolButton,
        {
          label: `Events: ${label2}`,
          icon: ApplicationIcons.filter,
          onClick: toggleTranscriptFilterShowing,
          className: styles$4.tabTool,
          subtle: true,
          ref: transcriptFilterButtonRef
        },
        "events-filter-transcript"
      )
    );
    tabTools.push(
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        ToolButton,
        {
          label: eventsCollapsed ? "Expand" : "Collapse",
          icon: eventsCollapsed ? ApplicationIcons.expand.all : ApplicationIcons.collapse.all,
          onClick: () => {
            collapseEvents(!eventsCollapsed);
          },
          subtle: true
        },
        "event-collapse-transcript"
      )
    );
  }
  tabTools.push(
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ToolButton,
      {
        label: displayMode === "rendered" ? "Raw" : "Rendered",
        icon: ApplicationIcons.display,
        onClick: toggleDisplayMode,
        className: styles$4.tabTool,
        subtle: true,
        title: displayMode === "rendered" ? "Show raw text without markdown rendering" : "Show rendered markdown"
      },
      "display-mode-toggle"
    )
  );
  tabTools.push(
    /* @__PURE__ */ jsxRuntimeExports.jsx(CopyToolbarButton, { transcript, className: styles$4.tabTool })
  );
  tabTools.push(
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ToolButton,
      {
        label: "Validation",
        icon: ApplicationIcons.edit,
        onClick: toggleValidationSidebar,
        className: styles$4.tabTool,
        subtle: true,
        title: validationSidebarCollapsed ? "Show validation editor" : "Hide validation editor"
      },
      "validation-sidebar-toggle"
    )
  );
  const tabPanels = [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      TabPanel,
      {
        id: kTranscriptMessagesTabId,
        className: clsx(styles$4.chatTab),
        title: "Messages",
        onSelected: () => {
          handleTabChange(kTranscriptMessagesTabId);
        },
        selected: resolvedSelectedTranscriptTab === kTranscriptMessagesTabId,
        scrollable: false,
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          ChatViewVirtualList,
          {
            id: "transcript-id",
            messages: transcript.messages || [],
            initialMessageId: messageParam,
            toolCallStyle: "complete",
            indented: false,
            className: styles$4.chatList,
            scrollRef,
            showLabels: true
          }
        )
      },
      kTranscriptMessagesTabId
    )
  ];
  if (transcript.events && transcript.events.length > 0) {
    tabPanels.push(
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        TabPanel,
        {
          id: kTranscriptEventsTabId,
          className: clsx(styles$4.eventsTab),
          title: "Events",
          onSelected: () => {
            handleTabChange(kTranscriptEventsTabId);
          },
          selected: resolvedSelectedTranscriptTab === kTranscriptEventsTabId,
          scrollable: false,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "div",
              {
                className: clsx(
                  styles$4.eventsContainer,
                  outlineCollapsed2 ? styles$4.outlineCollapsed : void 0
                ),
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsxs(
                    StickyScroll,
                    {
                      scrollRef,
                      className: styles$4.eventsOutline,
                      offsetTop: 40,
                      children: [
                        !outlineCollapsed2 && /* @__PURE__ */ jsxRuntimeExports.jsx(
                          TranscriptOutline,
                          {
                            eventNodes,
                            defaultCollapsedIds,
                            scrollRef
                          }
                        ),
                        /* @__PURE__ */ jsxRuntimeExports.jsx(
                          "div",
                          {
                            className: styles$4.outlineToggle,
                            onClick: () => toggleOutline(!outlineCollapsed2),
                            children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.sidebar })
                          }
                        )
                      ]
                    }
                  ),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$4.eventsSeparator }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    TranscriptViewNodes,
                    {
                      id: "transcript-events-list",
                      eventNodes,
                      defaultCollapsedIds,
                      initialEventId: eventParam,
                      className: styles$4.eventsList,
                      scrollRef
                    }
                  )
                ]
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              TranscriptFilterPopover,
              {
                showing: transcriptFilterShowing,
                setShowing: setTranscriptFilterShowing,
                positionEl: transcriptFilterButtonRef.current
              }
            )
          ]
        },
        "transcript-events"
      )
    );
  }
  if (transcript.metadata && Object.keys(transcript.metadata).length > 0) {
    tabPanels.push(
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        TabPanel,
        {
          id: kTranscriptMetadataTabId,
          className: clsx(styles$4.metadataTab),
          title: "Metadata",
          onSelected: () => {
            handleTabChange(kTranscriptMetadataTabId);
          },
          selected: resolvedSelectedTranscriptTab === kTranscriptMetadataTabId,
          scrollable: false,
          children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$4.scrollable, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            MetaDataGrid,
            {
              id: "transcript-metadata-grid",
              entries: transcript.metadata || {},
              className: clsx(styles$4.metadata)
            }
          ) })
        },
        "transcript-metadata"
      )
    );
  }
  const { events, messages, metadata: metadata2, ...infoData } = transcript;
  tabPanels.push(
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      TabPanel,
      {
        id: kTranscriptInfoTabId,
        className: clsx(styles$4.infoTab),
        title: "Info",
        onSelected: () => {
          handleTabChange(kTranscriptInfoTabId);
        },
        selected: resolvedSelectedTranscriptTab === kTranscriptInfoTabId,
        scrollable: false,
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$4.scrollable, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          MetaDataGrid,
          {
            id: "transcript-info-grid",
            entries: infoData,
            className: clsx(styles$4.metadata)
          }
        ) })
      },
      "transcript-info"
    )
  );
  const tabSetContent = /* @__PURE__ */ jsxRuntimeExports.jsx(
    TabSet,
    {
      id: "transcript-body",
      type: "pills",
      tabPanelsClassName: clsx(styles$4.tabSet),
      tabControlsClassName: clsx(styles$4.tabControl),
      className: clsx(styles$4.tabs),
      tools: tabTools,
      children: tabPanels
    }
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx(DisplayModeContext.Provider, { value: displayModeContextValue, children: validationSidebarCollapsed ? tabSetContent : /* @__PURE__ */ jsxRuntimeExports.jsxs(
    VscodeSplitLayout,
    {
      className: styles$4.splitLayout,
      fixedPane: "end",
      initialHandlePosition: "80%",
      minEnd: "180px",
      minStart: "200px",
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { slot: "start", className: styles$4.splitStart, children: tabSetContent }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { slot: "end", className: styles$4.validationSidebar, children: /* @__PURE__ */ jsxRuntimeExports.jsx(ValidationCaseEditor, { transcriptId: transcript.transcript_id }) })
      ]
    }
  ) });
};
const CopyToolbarButton = ({ transcript, className }) => {
  const [icon2, setIcon] = reactExports.useState(ApplicationIcons.copy);
  const showCopyConfirmation = reactExports.useCallback(() => {
    setIcon(ApplicationIcons.confirm);
    setTimeout(() => setIcon(ApplicationIcons.copy), 1250);
  }, []);
  if (!transcript) {
    return void 0;
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    ToolDropdownButton,
    {
      label: "Copy",
      icon: icon2,
      className: clsx(className),
      dropdownClassName: "text-size-smallest",
      dropdownAlign: "right",
      subtle: true,
      items: {
        UUID: () => {
          if (transcript.transcript_id) {
            void navigator.clipboard.writeText(transcript.transcript_id);
            showCopyConfirmation();
          }
        },
        Transcript: () => {
          if (transcript.messages) {
            void navigator.clipboard.writeText(
              messagesToStr(transcript.messages)
            );
            showCopyConfirmation();
          }
        }
      }
    },
    "sample-copy"
  );
};
const TranscriptNav = ({
  transcriptsDir,
  transcript,
  prevId,
  nextId
}) => {
  const navigate = useLoggingNavigate("TranscriptNav");
  const [searchParams] = useSearchParams();
  const handlePrevious = () => {
    if (prevId) {
      void navigate(transcriptRoute(transcriptsDir, prevId, searchParams));
    }
  };
  const handleNext = () => {
    if (nextId) {
      void navigate(transcriptRoute(transcriptsDir, nextId, searchParams));
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    NextPreviousNav,
    {
      onPrevious: handlePrevious,
      onNext: handleNext,
      hasPrevious: !!prevId,
      hasNext: !!nextId,
      children: transcript && /* @__PURE__ */ jsxRuntimeExports.jsx(
        TaskName,
        {
          taskId: transcript.task_id,
          taskRepeat: transcript.task_repeat,
          taskSet: transcript.task_set
        }
      )
    }
  );
};
const container = "_container_godvv_1";
const transcriptContainer = "_transcriptContainer_godvv_7";
const styles$2 = {
  container,
  transcriptContainer
};
const headingGrid = "_headingGrid_1n1sm_1";
const headingCell = "_headingCell_1n1sm_6";
const horizontal = "_horizontal_1n1sm_13";
const vertical = "_vertical_1n1sm_19";
const label = "_label_1n1sm_25";
const value = "_value_1n1sm_31";
const styles$1 = {
  headingGrid,
  headingCell,
  horizontal,
  vertical,
  label,
  value
};
const HeadingGrid = ({
  headings,
  rows,
  columns,
  className,
  labelClassName,
  valueClassName
}) => {
  const actualColumns = columns ?? headings.length;
  const actualRows = rows ?? 1;
  const totalCells = actualRows * actualColumns;
  const gridItems = headings.slice(0, totalCells);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: clsx(styles$1.headingGrid, className),
      style: {
        gridTemplateColumns: `repeat(${actualColumns}, auto)`,
        gridTemplateRows: `repeat(${actualRows}, auto)`
      },
      children: gridItems.map((heading, index) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        HeadingCell,
        {
          heading,
          labelClassName,
          valueClassName
        },
        index
      ))
    }
  );
};
const HeadingCell = ({
  heading,
  labelClassName,
  valueClassName
}) => {
  const { label: label2, value: value2, labelPosition = "above" } = heading;
  switch (labelPosition) {
    case "left":
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$1.headingCell, styles$1.horizontal), children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx(styles$1.label, labelClassName), children: label2 }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx(styles$1.value, valueClassName), children: value2 })
      ] });
    case "right":
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$1.headingCell, styles$1.horizontal), children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx(styles$1.value, valueClassName), children: value2 }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx(styles$1.label, labelClassName), children: label2 })
      ] });
    case "above":
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$1.headingCell, styles$1.vertical), children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx(styles$1.label, labelClassName), children: label2 }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx(styles$1.value, valueClassName), children: value2 })
      ] });
    case "below":
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$1.headingCell, styles$1.vertical), children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx(styles$1.value, valueClassName), children: value2 }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx(styles$1.label, labelClassName), children: label2 })
      ] });
  }
};
const titleContainer = "_titleContainer_6mwxv_1";
const styles = {
  titleContainer
};
const TranscriptTitle = ({ transcript }) => {
  const cols = [
    {
      label: "Transcript",
      value: /* @__PURE__ */ jsxRuntimeExports.jsx(
        TaskName,
        {
          taskId: transcript.task_id,
          taskRepeat: transcript.task_repeat,
          taskSet: transcript.task_set
        }
      )
    }
  ];
  if (transcript.date) {
    cols.push({
      label: "Date",
      value: formatDateTime(new Date(transcript.date))
    });
  }
  if (transcript.agent) {
    cols.push({
      label: "Agent",
      value: transcript.agent
    });
  }
  if (transcript.model) {
    cols.push({
      label: "Model",
      value: transcript.model
    });
  }
  if (transcript.limit) {
    cols.push({
      label: "Limit",
      value: transcript.limit
    });
  }
  if (transcript.error) {
    cols.push({
      label: "Error",
      value: transcript.error
    });
  }
  if (transcript.total_tokens) {
    cols.push({
      label: "Tokens",
      value: formatNumber(transcript.total_tokens)
    });
  }
  if (transcript.total_time) {
    cols.push({
      label: "Time",
      value: formatTime(transcript.total_time)
    });
  }
  if (transcript.message_count) {
    cols.push({
      label: "Messages",
      value: transcript.message_count.toString()
    });
  }
  if (transcript.score) {
    cols.push({
      label: "Score",
      value: /* @__PURE__ */ jsxRuntimeExports.jsx(ScoreValue, { score: transcript.score })
    });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    HeadingGrid,
    {
      headings: cols,
      className: clsx(styles.titleContainer),
      labelClassName: clsx(
        "text-style-label",
        "text-size-smallestest",
        "text-style-secondary"
      ),
      valueClassName: clsx("text-size-small")
    }
  );
};
const TranscriptPanel = () => {
  const scrollRef = reactExports.useRef(null);
  const { transcriptId } = useRequiredParams("transcriptId");
  const {
    displayTranscriptsDir,
    resolvedTranscriptsDir,
    resolvedTranscriptsDirSource,
    setTranscriptsDir
  } = useTranscriptsDir(true);
  const config = useAppConfig();
  const {
    loading: loading2,
    data: transcript,
    error
  } = useTranscript(
    config.transcripts ? { location: config.transcripts.dir, id: transcriptId } : skipToken
  );
  const filter = Array.isArray(config.filter) ? config.filter.join(" ") : config.filter;
  useDocumentTitle(getTranscriptDisplayName(transcript), "Transcripts");
  const sorting = useStore((state) => state.transcriptsTableState.sorting);
  const condition = useFilterConditions();
  const adjacentIds = useAdjacentTranscriptIds(
    transcriptId,
    resolvedTranscriptsDir,
    TRANSCRIPTS_INFINITE_SCROLL_CONFIG.pageSize,
    condition,
    sorting
  );
  const [prevId, nextId] = adjacentIds.data ?? [void 0, void 0];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$2.container), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      TranscriptsNavbar,
      {
        transcriptsDir: displayTranscriptsDir || "",
        transcriptsDirSource: resolvedTranscriptsDirSource,
        filter,
        setTranscriptsDir,
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          TranscriptNav,
          {
            transcriptsDir: resolvedTranscriptsDir,
            transcript,
            nextId,
            prevId
          }
        )
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(LoadingBar, { loading: loading2 }),
    !error && transcript && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$2.transcriptContainer, ref: scrollRef, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(TranscriptTitle, { transcript }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(TranscriptBody, { transcript, scrollRef })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ErrorPanel,
      {
        title: error instanceof ApiError && error.status === 413 ? "Transcript Too Large" : "Error Loading Transcript",
        error: error instanceof ApiError && error.status === 413 ? { message: "This transcript exceeds the maximum size limit." } : error
      }
    )
  ] });
};
export {
  TranscriptPanel
};
//# sourceMappingURL=TranscriptPanel.js.map
