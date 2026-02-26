import { G as useParams, s as skipToken, r as reactExports, q as loading, v as data, a as useApi, b as useAsyncDataFromQuery, j as jsxRuntimeExports, u as useStore, c as clsx, w as useNavigate, i as useSearchParams, z as getValidationParam, B as updateValidationParam, A as ApplicationIcons, m as useLoggingNavigate, x as transcriptRoute, e as useAppConfig, L as LoadingBar, f as ErrorPanel, H as ApiError } from "./index.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { u as useFilterConditions, T as TranscriptsNavbar } from "./useFilterConditions.js";
import { u as useServerTranscriptsInfinite, T as TRANSCRIPTS_INFINITE_SCROLL_CONFIG } from "./constants.js";
import { C as ChatViewVirtualList, V as ValidationCaseEditor, N as NextPreviousNav, g as getTranscriptDisplayName } from "./NextPreviousNav.js";
import { u as useTranscriptsDir } from "./useTranscriptsDir.js";
import { V as VscodeSplitLayout } from "./VscodeTreeItem.js";
import { e as eventTypeValues, f as useTranscriptNavigation, u as useEventNodes, k as kTranscriptCollapseScope, T as TranscriptViewNodes, M as MetaDataGrid, D as DisplayModeContext, g as kCollapsibleEventTypes, S as ScoreValue } from "./TranscriptViewNodes.js";
import { N as NoContentsPanel } from "./NoContentsPanel.js";
import { b as TabPanel, a as TabSet, T as TaskName } from "./TaskName.js";
import { P as PopOver, T as ToolButton, d as formatDateTime, f as formatNumber, e as formatTime } from "./ToolButton.js";
import { T as ToolDropdownButton } from "./ToolDropdownButton.js";
import { u as useTimeline, r as rowHasEvents, c as computeRowLayouts, g as getSelectedSpans, a as collectRawEvents, b as computeMinimapSelection, T as TimelineSwimLanes, d as TranscriptOutline } from "./timelineEventNodes.js";
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
function createTimelineEvent(event) {
  return {
    type: "event",
    event,
    startTime: getEventStartTime(event),
    endTime: getEventEndTime(event),
    totalTokens: getEventTokens(event)
  };
}
function createTimelineSpan(id, name, spanType, content, utility = false, branches = [], description) {
  if (content.length === 0) {
    throw new Error(
      `createTimelineSpan called with empty content for span "${name}" (id=${id}). Callers must guard against empty content before calling the factory.`
    );
  }
  return {
    type: "span",
    id,
    name: name.toLowerCase(),
    spanType,
    content,
    branches,
    description,
    utility,
    startTime: minStartTime(content),
    endTime: maxEndTime(content),
    totalTokens: sumTokens(content)
  };
}
function createBranch(forkedAt, content) {
  if (content.length === 0) {
    throw new Error(
      "createBranch called with empty content. Callers must guard against empty content before calling the factory."
    );
  }
  return {
    type: "branch",
    forkedAt,
    content,
    startTime: minStartTime(content),
    endTime: maxEndTime(content),
    totalTokens: sumTokens(content)
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
        totalTokens: 0
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
      totalTokens: 0
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
      }
      if (scoringSpan) {
        agentNode.content.push(scoringSpan);
        agentNode.endTime = maxEndTime(agentNode.content);
        agentNode.totalTokens = sumTokens(agentNode.content);
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
          totalTokens: 0
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
        totalTokens: 0
      };
    }
  }
  return { name: "Default", description: "", root };
}
function isParentSelected(selected2, parentRowName) {
  if (selected2 === null || parentRowName === void 0) return true;
  return selected2.toLowerCase() === parentRowName.toLowerCase();
}
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
  const layouts = reactExports.useMemo(
    () => computeRowLayouts(
      visibleRows,
      state.node.startTime,
      state.node.endTime,
      "direct"
    ),
    [visibleRows, state.node.startTime, state.node.endTime]
  );
  const parentRowName = state.rows[0]?.name;
  const parentSelected = isParentSelected(state.selected, parentRowName);
  const selectedEvents = reactExports.useMemo(() => {
    if (parentSelected) return events;
    const spans = getSelectedSpans(state.rows, state.selected);
    return collectRawEvents(spans);
  }, [events, parentSelected, state.rows, state.selected]);
  const minimapSelection = reactExports.useMemo(
    () => computeMinimapSelection(state.rows, state.selected),
    [state.rows, state.selected]
  );
  const hasTimeline = timeline.root.content.length > 0 && timeline.root.content.some((item) => item.type === "span");
  return {
    timeline: hasTimeline ? timeline : null,
    state,
    layouts,
    selectedEvents,
    minimapSelection,
    hasTimeline
  };
}
const tabs = "_tabs_vgk45_7";
const chatTab = "_chatTab_vgk45_24";
const metadata = "_metadata_vgk45_32";
const scrollable = "_scrollable_vgk45_37";
const eventsSeparator = "_eventsSeparator_vgk45_43";
const eventsList = "_eventsList_vgk45_47";
const eventsContainer = "_eventsContainer_vgk45_51";
const outlineCollapsed = "_outlineCollapsed_vgk45_60";
const eventsTab = "_eventsTab_vgk45_64";
const eventsTabContent = "_eventsTabContent_vgk45_68";
const eventsOutline = "_eventsOutline_vgk45_76";
const outlineToggle = "_outlineToggle_vgk45_81";
const tabTool = "_tabTool_vgk45_95";
const splitLayout = "_splitLayout_vgk45_100";
const splitStart = "_splitStart_vgk45_105";
const validationSidebar = "_validationSidebar_vgk45_110";
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
    selectedEvents,
    minimapSelection,
    hasTimeline
  } = useTranscriptTimeline(filteredEvents);
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
    false
  );
  const hasMatchingEvents = eventNodes.length > 0;
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
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$4.eventsTabContent, children: [
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
                    selection: minimapSelection
                  },
                  breadcrumb: {
                    breadcrumbs: timelineState.breadcrumbs,
                    atRoot,
                    onGoUp: timelineState.goUp,
                    onNavigate: timelineState.navigateTo,
                    selected: timelineState.selected
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
                          onHasNodesChange: handleOutlineHasNodesChange
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
                    className: styles$4.eventsList,
                    scrollRef
                  }
                ) : /* @__PURE__ */ jsxRuntimeExports.jsx(NoContentsPanel, { text: "No events match the current filter" })
              ]
            }
          )
        ] }),
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
