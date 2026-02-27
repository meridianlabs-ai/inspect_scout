import { G as useParams, s as skipToken, r as reactExports, q as loading, v as data, a as useApi, b as useAsyncDataFromQuery, j as jsxRuntimeExports, u as useStore, c as clsx, w as useNavigate, i as useSearchParams, z as getValidationParam, B as updateValidationParam, A as ApplicationIcons, m as useLoggingNavigate, x as transcriptRoute, e as useAppConfig, L as LoadingBar, f as ErrorPanel, H as ApiError } from "./index.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { u as useFilterConditions, T as TranscriptsNavbar } from "./useFilterConditions.js";
import { u as useServerTranscriptsInfinite, T as TRANSCRIPTS_INFINITE_SCROLL_CONFIG } from "./constants.js";
import { C as ChatViewVirtualList, V as ValidationCaseEditor, N as NextPreviousNav, g as getTranscriptDisplayName } from "./NextPreviousNav.js";
import { u as useTranscriptsDir } from "./useTranscriptsDir.js";
import { V as VscodeSplitLayout } from "./VscodeTreeItem.js";
import { e as eventTypeValues, f as buildTimeline, g as useTimeline, r as rowHasEvents, h as computeRowLayouts, j as getSelectedSpans, k as collectRawEvents, l as computeMinimapSelection, m as useTranscriptNavigation, n as buildSpanSelectKeys, u as useEventNodes, o as kTranscriptCollapseScope, p as TimelineSelectContext, T as TranscriptViewNodes, M as MetaDataGrid, D as DisplayModeContext, q as kCollapsibleEventTypes, S as ScoreValue } from "./TranscriptViewNodes.js";
import { N as NoContentsPanel } from "./NoContentsPanel.js";
import { b as TabPanel, a as TabSet, T as TaskName } from "./TaskName.js";
import { P as PopOver, T as ToolButton, d as formatDateTime, f as formatNumber, e as formatTime } from "./ToolButton.js";
import { T as ToolDropdownButton } from "./ToolDropdownButton.js";
import { c as computeTimeMapping, T as TimelineSwimLanes, a as TranscriptOutline } from "./TimelineSwimLanes.js";
import "./_commonjsHelpers.js";
import "./Navbar.js";
import "./index2.js";
import "./Modal.js";
import "./FormFields.js";
import "./ValidationSplitSelector.js";
import "./useMutation.js";
import "./Chip.js";
import "./chunk-DfAF0w94.js";
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
  onStickyChange,
  preserveHeight = false
}) => {
  const wrapperRef = reactExports.useRef(null);
  const contentRef = reactExports.useRef(null);
  const [isSticky, setIsSticky] = reactExports.useState(false);
  const [dimensions, setDimensions] = reactExports.useState({
    width: 0,
    height: 0,
    left: 0,
    stickyTop: 0,
    // Store the position where the element should stick
    preStickHeight: 0
    // Height captured just before entering sticky mode
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
        setDimensions((prev) => ({
          ...prev,
          // Use the width tracker to get the right width that respects
          // the parent container's current width, rather than the content's width
          width: trackerRect.width,
          height: contentRect.height,
          left: trackerRect.left,
          stickyTop
        }));
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
        if (shouldBeSticky && preserveHeight && content) {
          const capturedHeight = content.getBoundingClientRect().height;
          setDimensions((prev) => ({
            ...prev,
            preStickHeight: capturedHeight
          }));
        }
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
  }, [scrollRef, offsetTop, onStickyChange, isSticky, preserveHeight]);
  const wrapperStyle = {
    position: "relative",
    height: isSticky ? `${preserveHeight ? dimensions.preStickHeight : dimensions.height}px` : "auto"
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
const emptySourceSpans = /* @__PURE__ */ new Map();
function useTranscriptTimeline(events) {
  const timeline = reactExports.useMemo(() => buildTimeline(events), [events]);
  const state = useTimeline(timeline);
  const prevTimelineRef = reactExports.useRef(timeline);
  reactExports.useEffect(() => {
    if (prevTimelineRef.current !== timeline) {
      prevTimelineRef.current = timeline;
      state.navigateTo("");
    }
  }, [timeline]);
  const visibleRows = reactExports.useMemo(
    () => state.rows.filter((row2, i) => i === 0 || rowHasEvents(row2)),
    [state.rows]
  );
  const timeMapping = reactExports.useMemo(
    () => computeTimeMapping(state.node),
    [state.node]
  );
  const rootTimeMapping = reactExports.useMemo(
    () => computeTimeMapping(timeline.root),
    [timeline.root]
  );
  const layouts = reactExports.useMemo(
    () => computeRowLayouts(visibleRows, timeMapping, "direct"),
    [visibleRows, timeMapping]
  );
  const { selectedEvents, sourceSpans } = reactExports.useMemo(() => {
    const spans = getSelectedSpans(state.rows, state.selected);
    if (spans.length === 0) {
      return { selectedEvents: events, sourceSpans: emptySourceSpans };
    }
    const collected = collectRawEvents(spans);
    return {
      selectedEvents: collected.events,
      sourceSpans: collected.sourceSpans
    };
  }, [events, state.rows, state.selected]);
  const minimapSelection = reactExports.useMemo(
    () => computeMinimapSelection(state.rows, state.selected),
    [state.rows, state.selected]
  );
  const hasTimeline = timeline.root.content.length > 0 && timeline.root.content.some((item) => item.type === "span");
  return {
    timeline: hasTimeline ? timeline : null,
    state,
    layouts,
    timeMapping,
    rootTimeMapping,
    selectedEvents,
    sourceSpans,
    minimapSelection,
    hasTimeline
  };
}
const tabs = "_tabs_48snv_7";
const chatTab = "_chatTab_48snv_24";
const metadata = "_metadata_48snv_32";
const scrollable = "_scrollable_48snv_37";
const eventsSeparator = "_eventsSeparator_48snv_43";
const eventsList = "_eventsList_48snv_47";
const eventsContainer = "_eventsContainer_48snv_51";
const outlineCollapsed = "_outlineCollapsed_48snv_59";
const eventsTab = "_eventsTab_48snv_63";
const eventsTabContent = "_eventsTabContent_48snv_67";
const eventsOutline = "_eventsOutline_48snv_75";
const outlineToggle = "_outlineToggle_48snv_80";
const tabTool = "_tabTool_48snv_94";
const splitLayout = "_splitLayout_48snv_99";
const splitStart = "_splitStart_48snv_104";
const validationSidebar = "_validationSidebar_48snv_109";
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
  eventsTabContent,
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
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { getEventUrl } = useTranscriptNavigation();
  const tabParam = searchParams.get("tab");
  const eventParam = searchParams.get("event");
  const messageParam = searchParams.get("message");
  const hasEvents = transcript.events && transcript.events.length > 0;
  const defaultTab = hasEvents ? kTranscriptEventsTabId : kTranscriptMessagesTabId;
  const selectedTranscriptTab = useStore(
    (state) => state.selectedTranscriptTab
  );
  const setSelectedTranscriptTab = useStore(
    (state) => state.setSelectedTranscriptTab
  );
  const resolvedSelectedTranscriptTab = tabParam || selectedTranscriptTab || defaultTab;
  const handleTabChange = reactExports.useCallback(
    (tabId) => {
      setSelectedTranscriptTab(tabId);
      setSearchParams((prevParams) => {
        const newParams = new URLSearchParams(prevParams);
        newParams.set("tab", tabId);
        newParams.delete("event");
        newParams.delete("message");
        return newParams;
      });
    },
    [setSelectedTranscriptTab, setSearchParams]
  );
  const suppressCollapseRef = reactExports.useRef(false);
  const [markerNavSticky, setMarkerNavSticky] = reactExports.useState(false);
  const handleMarkerNavigate = reactExports.useCallback(
    (eventId) => {
      const url = getEventUrl(eventId);
      if (!url) return;
      suppressCollapseRef.current = true;
      void navigate(url);
    },
    [getEventUrl, navigate]
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
    if (excludedEventTypes.length === 0) return transcript.events;
    return transcript.events.filter(
      (event) => !excludedEventTypes.includes(event.event)
    );
  }, [transcript.events, excludedEventTypes]);
  const {
    timeline: timelineData,
    state: timelineState,
    layouts: timelineLayouts,
    rootTimeMapping,
    selectedEvents,
    sourceSpans,
    minimapSelection,
    hasTimeline
  } = useTranscriptTimeline(filteredEvents);
  const spanSelectKeys = reactExports.useMemo(
    () => buildSpanSelectKeys(timelineState.rows),
    [timelineState.rows]
  );
  const {
    select: timelineSelect,
    drillDownAndSelect: timelineDrillDownAndSelect
  } = timelineState;
  const selectBySpanId = reactExports.useCallback(
    (spanId) => {
      const key = spanSelectKeys.get(spanId);
      if (!key) return;
      if (key.parallel && key.spanIndex) {
        timelineDrillDownAndSelect(key.name, `${key.name} ${key.spanIndex}`);
      } else {
        timelineSelect(key.name, key.spanIndex);
      }
    },
    [spanSelectKeys, timelineSelect, timelineDrillDownAndSelect]
  );
  const [isSwimLaneSticky, setIsSwimLaneSticky] = reactExports.useState(false);
  const [stickySwimLaneHeight, setStickySwimLaneHeight] = reactExports.useState(0);
  const swimLaneStickyContentRef = reactExports.useRef(null);
  const handleSwimLaneStickyChange = reactExports.useCallback((sticky) => {
    setIsSwimLaneSticky(sticky);
    if (sticky && suppressCollapseRef.current) {
      suppressCollapseRef.current = false;
      setMarkerNavSticky(true);
    } else if (!sticky) {
      setStickySwimLaneHeight(0);
      setMarkerNavSticky(false);
    }
  }, []);
  reactExports.useEffect(() => {
    const el = swimLaneStickyContentRef.current;
    if (!isSwimLaneSticky || !el) {
      return;
    }
    const observer = new ResizeObserver(() => {
      setStickySwimLaneHeight(el.getBoundingClientRect().height);
    });
    observer.observe(el);
    setStickySwimLaneHeight(el.getBoundingClientRect().height);
    return () => observer.disconnect();
  }, [isSwimLaneSticky]);
  const { eventNodes, defaultCollapsedIds } = useEventNodes(
    selectedEvents,
    false,
    sourceSpans
  );
  const hasMatchingEvents = eventNodes.length > 0;
  reactExports.useEffect(() => {
    if (!eventParam) {
      scrollRef.current?.scrollTo({ top: 0 });
    }
  }, [selectedEvents, eventParam, scrollRef]);
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
  const [outlineHasNodes, setOutlineHasNodes] = reactExports.useState(true);
  const [outlineWidth, setOutlineWidth] = reactExports.useState();
  const handleOutlineHasNodesChange = reactExports.useCallback(
    (hasNodes) => {
      setOutlineHasNodes(hasNodes);
      if (!hasNodes && !outlineCollapsed2) {
        toggleOutline(true);
      }
    },
    [outlineCollapsed2, toggleOutline]
  );
  reactExports.useEffect(() => {
    if (outlineCollapsed2) {
      setOutlineHasNodes(hasMatchingEvents);
    }
  }, [outlineCollapsed2, hasMatchingEvents, eventNodes]);
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
  const atRoot = timelineState.breadcrumbs.length <= 1;
  const scrollToTop = reactExports.useCallback(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [scrollRef]);
  const messagesPanel = /* @__PURE__ */ jsxRuntimeExports.jsx(
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
  );
  const eventsPanel = hasEvents ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
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
        /* @__PURE__ */ jsxRuntimeExports.jsx(TimelineSelectContext.Provider, { value: selectBySpanId, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$4.eventsTabContent, children: [
          hasTimeline && timelineData && /* @__PURE__ */ jsxRuntimeExports.jsx(
            StickyScroll,
            {
              scrollRef,
              offsetTop: 40,
              zIndex: 500,
              preserveHeight: true,
              onStickyChange: handleSwimLaneStickyChange,
              children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: swimLaneStickyContentRef, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                TimelineSwimLanes,
                {
                  layouts: timelineLayouts,
                  selected: timelineState.selected,
                  node: timelineState.node,
                  onSelect: timelineState.select,
                  onDrillDown: timelineState.drillDown,
                  onGoUp: timelineState.goUp,
                  minimap: {
                    root: timelineData.root,
                    selection: minimapSelection,
                    mapping: rootTimeMapping
                  },
                  breadcrumb: {
                    breadcrumbs: timelineState.breadcrumbs,
                    atRoot,
                    onGoUp: timelineState.goUp,
                    onNavigate: timelineState.navigateTo,
                    selected: timelineState.selected,
                    onScrollToTop: scrollToTop
                  },
                  onMarkerNavigate: handleMarkerNavigate,
                  isSticky: isSwimLaneSticky,
                  forceCollapsed: isSwimLaneSticky && !markerNavSticky,
                  noAnimation: isSwimLaneSticky && !markerNavSticky
                }
              ) })
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "div",
            {
              className: clsx(
                styles$4.eventsContainer,
                outlineCollapsed2 && styles$4.outlineCollapsed
              ),
              style: !outlineCollapsed2 && outlineWidth ? { "--outline-width": `${outlineWidth}px` } : void 0,
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs(
                  StickyScroll,
                  {
                    scrollRef,
                    className: styles$4.eventsOutline,
                    offsetTop: 40 + stickySwimLaneHeight,
                    children: [
                      !outlineCollapsed2 && /* @__PURE__ */ jsxRuntimeExports.jsx(
                        TranscriptOutline,
                        {
                          eventNodes,
                          defaultCollapsedIds,
                          scrollRef,
                          onHasNodesChange: handleOutlineHasNodesChange,
                          onWidthChange: setOutlineWidth
                        }
                      ),
                      /* @__PURE__ */ jsxRuntimeExports.jsx(
                        "button",
                        {
                          type: "button",
                          className: styles$4.outlineToggle,
                          onClick: outlineHasNodes ? () => toggleOutline(!outlineCollapsed2) : void 0,
                          "aria-disabled": !outlineHasNodes,
                          title: outlineHasNodes ? void 0 : "No outline available for the current filter",
                          "aria-label": outlineCollapsed2 ? "Show outline" : "Hide outline",
                          children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.sidebar })
                        }
                      )
                    ]
                  }
                ),
                /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$4.eventsSeparator }),
                hasMatchingEvents ? /* @__PURE__ */ jsxRuntimeExports.jsx(
                  TranscriptViewNodes,
                  {
                    id: "transcript-events-list",
                    eventNodes,
                    defaultCollapsedIds,
                    initialEventId: eventParam,
                    offsetTop: 40 + stickySwimLaneHeight,
                    className: styles$4.eventsList,
                    scrollRef
                  }
                ) : /* @__PURE__ */ jsxRuntimeExports.jsx(NoContentsPanel, { text: "No events match the current filter" })
              ]
            }
          )
        ] }) }),
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
  ) : null;
  const tabPanels = [...eventsPanel ? [eventsPanel] : [], messagesPanel];
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
  const [icon, setIcon] = reactExports.useState(ApplicationIcons.copy);
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
      icon,
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
