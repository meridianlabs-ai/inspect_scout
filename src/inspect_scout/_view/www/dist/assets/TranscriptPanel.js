import { G as useParams, s as skipToken, r as reactExports, q as loading, v as data, a as useApi, b as useAsyncDataFromQuery, u as useStore, j as jsxRuntimeExports, c as clsx, w as useNavigate, i as useSearchParams, z as getValidationParam, B as updateValidationParam, A as ApplicationIcons, m as useLoggingNavigate, x as transcriptRoute, e as useAppConfig, L as LoadingBar, f as ErrorPanel, H as ApiError } from "./index.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { u as useFilterConditions, T as TranscriptsNavbar } from "./useFilterConditions.js";
import { u as useServerTranscriptsInfinite, T as TRANSCRIPTS_INFINITE_SCROLL_CONFIG } from "./constants.js";
import { C as ChatViewVirtualList, T as TimelineEventsView, V as ValidationCaseEditor, N as NextPreviousNav, g as getTranscriptDisplayName } from "./NextPreviousNav.js";
import { u as useTranscriptsDir } from "./useTranscriptsDir.js";
import { V as VscodeSplitLayout } from "./VscodeTreeItem.js";
import { e as eventTypeValues, f as useTranscriptNavigation, M as MetaDataGrid, D as DisplayModeContext, S as ScoreValue } from "./TranscriptViewNodes.js";
import { b as TabPanel, a as TabSet, T as TaskName } from "./TaskName.js";
import { P as PopOver, T as ToolButton, d as formatDateTime, f as formatNumber, e as formatTime } from "./ToolButton.js";
import { T as ToolDropdownButton } from "./ToolDropdownButton.js";
import "./_commonjsHelpers.js";
import "./Navbar.js";
import "./index2.js";
import "./Modal.js";
import "./FormFields.js";
import "./ValidationSplitSelector.js";
import "./useMutation.js";
import "./Chip.js";
import "./NoContentsPanel.js";
import "./TimelineSwimLanes.js";
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
const tabs = "_tabs_1o3dx_7";
const chatTab = "_chatTab_1o3dx_24";
const metadata = "_metadata_1o3dx_32";
const scrollable = "_scrollable_1o3dx_37";
const eventsTab = "_eventsTab_1o3dx_43";
const tabTool = "_tabTool_1o3dx_47";
const splitLayout = "_splitLayout_1o3dx_52";
const splitStart = "_splitStart_1o3dx_57";
const validationSidebar = "_validationSidebar_1o3dx_62";
const styles$4 = {
  tabs,
  chatTab,
  metadata,
  scrollable,
  eventsTab,
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
  const viewRef = reactExports.useRef(null);
  const handleMarkerNavigate = reactExports.useCallback(
    (eventId) => {
      const url = getEventUrl(eventId);
      if (!url) return;
      viewRef.current?.suppressNextCollapse();
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
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          TimelineEventsView,
          {
            ref: viewRef,
            events: filteredEvents,
            scrollRef,
            offsetTop: 40,
            initialEventId: eventParam,
            defaultOutlineExpanded: true,
            id: "transcript-events-list",
            collapsed: eventsCollapsed,
            onMarkerNavigate: handleMarkerNavigate
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
