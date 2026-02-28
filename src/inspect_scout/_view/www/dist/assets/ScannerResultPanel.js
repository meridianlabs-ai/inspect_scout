import { r as reactExports, q as loading, v as data, a as useApi, b as useAsyncDataFromQuery, s as skipToken, j as jsxRuntimeExports, c as clsx, i as useSearchParams, w as useNavigate, u as useStore, x as transcriptRoute, A as ApplicationIcons, y as projectOrAppAliasedPath, m as useLoggingNavigate, l as scanResultRoute, p as getScannerParam, e as useAppConfig, z as getValidationParam, B as updateValidationParam, L as LoadingBar, E as ExtendedFindProvider } from "./index.js";
import { V as VscodeSplitLayout } from "./VscodeTreeItem.js";
import { A as ANSIDisplay, b as ModelUsagePanel, R as RecordTree, a as LabeledValue, M as MetaDataGrid, J as JSONPanel } from "./TranscriptViewNodes.js";
import { T as TaskName, a as TabSet, b as TabPanel } from "./TaskName.js";
import { f as formatNumber, T as ToolButton } from "./ToolButton.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { a as useScanRoute, u as useScansDir, S as ScansNavbar } from "./useScansDir.js";
import { l as useSelectedScanDataframe, o as parseScanResultData, k as useSelectedScanner, C as Card, a as CardHeader, b as CardBody, q as isTranscriptInput, s as isMessagesInput, t as isMessageInput, v as isEventsInput, w as isEventInput, u as useMarkdownRefs, V as Value, c as ValidationResult, E as Explanation, e as resultIdentifier, T as TranscriptView, m as useSelectedScan, n as getScanDisplayName } from "./refs.js";
import { C as ChatViewVirtualList, T as TimelineEventsView, N as NextPreviousNav, g as getTranscriptDisplayName, V as ValidationCaseEditor } from "./NextPreviousNav.js";
import { u as useTranscriptsDir } from "./useTranscriptsDir.js";
import { N as NoContentsPanel } from "./NoContentsPanel.js";
import "./_commonjsHelpers.js";
import "./chunk-DfAF0w94.js";
import "./Navbar.js";
import "./useMapAsyncData.js";
import "./array.js";
import "./object.js";
import "./Modal.js";
import "./FormFields.js";
import "./ValidationSplitSelector.js";
import "./useMutation.js";
import "./Chip.js";
import "./TimelineSwimLanes.js";
const useSelectedScanResultData = (scanResultUuid) => {
  const { data: columnTable } = useSelectedScanDataframe();
  return useScanResultData(columnTable, scanResultUuid);
};
const useScanResultData = (columnTable, rowIdentifier) => {
  const [scanResultData, setScanResultData] = reactExports.useState(void 0);
  const [isLoading, setIsLoading] = reactExports.useState(false);
  const filtered = reactExports.useMemo(() => {
    if (!rowIdentifier || !columnTable) {
      return void 0;
    }
    if (columnTable.columnNames().length === 0) {
      return void 0;
    }
    const filtered2 = columnTable.params({ targetIdentifier: rowIdentifier }).filter(
      (d, $) => d.identifier === $.targetIdentifier
    );
    if (filtered2.numRows() === 0) {
      return void 0;
    }
    return filtered2;
  }, [columnTable, rowIdentifier]);
  reactExports.useEffect(() => {
    if (!filtered) {
      setScanResultData(void 0);
      setIsLoading(false);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    const run = async () => {
      try {
        const result = await parseScanResultData(filtered);
        if (!cancelled) {
          setScanResultData(result);
          setIsLoading(false);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Error parsing scanner data:", error);
          setScanResultData(void 0);
          setIsLoading(false);
        }
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [filtered]);
  return isLoading ? loading : data(scanResultData);
};
const useScanDataframeInput = (params) => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: params === skipToken ? [skipToken] : ["scanDataframeInput", params, "scans-inv"],
    queryFn: params === skipToken ? skipToken : () => api.getScannerDataframeInput(
      params.scansDir,
      params.scanPath,
      params.scanner,
      params.uuid
    ),
    staleTime: Infinity
  });
};
const useSelectedScanResultInputData = (scanUuid) => {
  const { resolvedScansDir, scanPath } = useScanRoute();
  const scanner = useSelectedScanner();
  return useScanDataframeInput(
    resolvedScansDir && scanPath && scanner.data && scanUuid ? {
      scansDir: resolvedScansDir,
      scanPath,
      scanner: scanner.data,
      uuid: scanUuid
    } : skipToken
  );
};
const useHasTranscript = (params) => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: params === skipToken ? [skipToken] : ["has_transcript", params],
    queryFn: params === skipToken ? skipToken : () => api.hasTranscript(params.location, params.id),
    staleTime: Infinity
  });
};
const container$6 = "_container_1cz5u_1";
const traceback = "_traceback_1cz5u_5";
const styles$a = {
  container: container$6,
  traceback
};
const ErrorPanel = ({ error, traceback: traceback2 }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(Card, { className: clsx(styles$a.container), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(CardHeader, { type: "modern", children: "Error" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(CardBody, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-smaller"), children: error }),
      traceback2 && /* @__PURE__ */ jsxRuntimeExports.jsx(
        ANSIDisplay,
        {
          className: clsx(styles$a.traceback, "text-size-smaller"),
          output: traceback2
        }
      )
    ] })
  ] });
};
const table = "_table_z217i_1";
const tableTokens = "_tableTokens_z217i_5";
const tableH = "_tableH_z217i_9";
const model = "_model_z217i_14";
const cellContents = "_cellContents_z217i_18";
const styles$9 = {
  table,
  tableTokens,
  tableH,
  model,
  cellContents
};
const TokenTable = ({ className, children }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "table",
    {
      className: clsx(
        "table",
        "table-sm",
        "text-size-smaller",
        styles$9.table,
        className
      ),
      children
    }
  );
};
const TokenHeader = () => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("thead", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("td", {}),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "td",
        {
          colSpan: 3,
          className: clsx(
            "card-subheading",
            styles$9.tableTokens,
            "text-size-small",
            "text-style-label",
            "text-style-secondary"
          ),
          align: "center",
          children: "Tokens"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "th",
        {
          className: clsx(
            styles$9.tableH,
            "text-sixe-small",
            "text-style-label",
            "text-style-secondary"
          ),
          children: "Model"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "th",
        {
          className: clsx(
            styles$9.tableH,
            "text-sixe-small",
            "text-style-label",
            "text-style-secondary"
          ),
          children: "Usage"
        }
      )
    ] })
  ] });
};
const TokenRow = ({ model: model2, usage }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("td", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$9.model, styles$9.cellContents), children: model2 }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("td", { children: /* @__PURE__ */ jsxRuntimeExports.jsx(ModelUsagePanel, { usage, className: clsx(styles$9.cellContents) }) })
  ] });
};
const ModelTokenTable = ({
  model_usage,
  className
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(TokenTable, { className, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(TokenHeader, {}),
    /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: Object.keys(model_usage).map((key) => {
      if (!model_usage[key]) {
        return null;
      }
      return /* @__PURE__ */ jsxRuntimeExports.jsx(TokenRow, { model: key, usage: model_usage[key] }, key);
    }) })
  ] });
};
const scanInfo = "_scanInfo_76qrl_1";
const container$5 = "_container_76qrl_7";
const styles$8 = {
  scanInfo,
  container: container$5
};
const InfoPanel = ({ resultData }) => {
  return resultData && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$8.container), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(Card, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CardHeader, { label: "Scanner Info", type: "modern" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(CardBody, { children: /* @__PURE__ */ jsxRuntimeExports.jsx(ScannerInfoPanel, { resultData }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(Card, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CardHeader, { label: "Transcript Info", type: "modern" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(CardBody, { children: /* @__PURE__ */ jsxRuntimeExports.jsx(TranscriptInfoPanel, { resultData }) })
    ] }),
    resultData?.scanModelUsage && Object.keys(resultData?.scanModelUsage).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(Card, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CardHeader, { label: "Model Usage", type: "modern" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(CardBody, { children: Object.keys(resultData?.scanModelUsage).map((key) => {
        if (!resultData?.scanModelUsage[key]) {
          return null;
        }
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ModelTokenTable,
          {
            model_usage: resultData?.scanModelUsage[key]
          },
          key
        );
      }) })
    ] }),
    resultData?.scanMetadata && Object.keys(resultData.scanMetadata).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(Card, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CardHeader, { label: "Metadata", type: "modern" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(CardBody, { children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        RecordTree,
        {
          id: `scan-metadata-${resultData?.identifier}`,
          record: resultData?.scanMetadata || {}
        }
      ) })
    ] })
  ] });
};
const ScannerInfoPanel = ({ resultData }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx("text-size-small"), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$8.scanInfo), children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LabeledValue, { label: "Name", children: resultData?.scannerName }),
      resultData?.scannerFile && resultData.scannerFile !== null && /* @__PURE__ */ jsxRuntimeExports.jsx(LabeledValue, { label: "File", children: resultData?.scannerFile }),
      (resultData?.scanTotalTokens || 0) > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(LabeledValue, { label: "Tokens", children: resultData?.scanTotalTokens ? formatNumber(resultData.scanTotalTokens) : "" })
    ] }),
    resultData?.scanTags && resultData.scanTags.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(LabeledValue, { label: "Tags", children: (resultData?.scanTags || []).join(", ") }),
    resultData?.scannerParams && Object.keys(resultData.scannerParams).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(LabeledValue, { label: "Params", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      RecordTree,
      {
        id: `scanner-params-${resultData?.identifier}`,
        record: resultData?.scannerParams
      }
    ) })
  ] });
};
const TranscriptInfoPanel = ({ resultData }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-small"), children: /* @__PURE__ */ jsxRuntimeExports.jsx(
    MetaDataGrid,
    {
      entries: {
        "source id": resultData?.transcriptSourceId,
        source_uri: resultData?.transcriptSourceUri,
        date: resultData?.transcriptDate,
        model: resultData?.transcriptModel,
        agent: resultData?.transcriptAgent,
        "agent args": resultData?.transcriptAgentArgs,
        score: resultData?.transcriptScore,
        success: resultData?.transcriptSuccess,
        limit: resultData?.transcriptLimit,
        error: resultData?.transcriptError,
        message_count: resultData?.transcriptMessageCount,
        total_time: resultData?.transcriptTotalTime,
        total_tokens: resultData?.transcriptTotalTokens
      }
    }
  ) });
};
const container$4 = "_container_1o5t7_1";
const styles$7 = {
  container: container$4
};
const MetadataPanel = ({ resultData }) => {
  const hasMetadata = resultData && Object.keys(resultData?.metadata).length > 0;
  return resultData && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$7.container, "text-size-base"), children: [
    !hasMetadata && /* @__PURE__ */ jsxRuntimeExports.jsx(NoContentsPanel, { text: "No metadata available" }),
    hasMetadata && /* @__PURE__ */ jsxRuntimeExports.jsx(Card, { children: /* @__PURE__ */ jsxRuntimeExports.jsx(CardBody, { children: /* @__PURE__ */ jsxRuntimeExports.jsx(LabeledValue, { label: "Metadata", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      RecordTree,
      {
        id: `result-metadata-${resultData.identifier}`,
        record: resultData.metadata || {}
      }
    ) }) }) })
  ] });
};
const header$1 = "_header_m7jeh_1";
const actions = "_actions_m7jeh_11";
const iconButton = "_iconButton_m7jeh_18";
const styles$6 = {
  header: header$1,
  actions,
  iconButton
};
const ColumnHeader = ({ label, actions: actions2 }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$6.header), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: clsx(
          styles$6.label,
          "text-size-smallest",
          "text-style-label",
          "text-style-secondary"
        ),
        children: label
      }
    ),
    actions2 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$6.actions, children: actions2 })
  ] });
};
const ColumnHeaderButton = reactExports.forwardRef(({ icon, className, ...rest }, ref) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "button",
    {
      ref,
      type: "button",
      className: clsx(styles$6.iconButton, className),
      ...rest,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: icon })
    }
  );
});
ColumnHeaderButton.displayName = "ColumnHeaderButton";
const container$3 = "_container_193x9_1";
const scrollable = "_scrollable_193x9_8";
const chatInputContainer = "_chatInputContainer_193x9_15";
const styles$5 = {
  container: container$3,
  scrollable,
  chatInputContainer
};
const ResultBody = ({
  resultData,
  inputData,
  transcriptDir,
  hasTranscript
}) => {
  const scrollRef = reactExports.useRef(null);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialMessageId = searchParams.get("message");
  const initialEventId = searchParams.get("event");
  const highlightLabeled = useStore((state) => state.highlightLabeled);
  const handleNavigateToTranscript = reactExports.useCallback(() => {
    if (transcriptDir && resultData.transcriptId) {
      void navigate(transcriptRoute(transcriptDir, resultData.transcriptId));
    }
  }, [navigate, transcriptDir, resultData.transcriptId]);
  const canNavigateToTranscript = hasTranscript && transcriptDir.length > 0 && resultData.transcriptId;
  const transcriptAction = canNavigateToTranscript ? /* @__PURE__ */ jsxRuntimeExports.jsx(
    ColumnHeaderButton,
    {
      icon: ApplicationIcons.transcript,
      onClick: handleNavigateToTranscript,
      title: "View complete transcript"
    }
  ) : void 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$5.container, containerClass(inputData)), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(ColumnHeader, { label: "Input", actions: transcriptAction }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: scrollRef, className: clsx(styles$5.scrollable), children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      InputRenderer,
      {
        resultData,
        inputData,
        scrollRef,
        initialMessageId,
        initialEventId,
        highlightLabeled
      }
    ) })
  ] });
};
const containerClass = (inputData) => {
  if (isTranscriptInput(inputData)) {
    return styles$5.transcriptInputContainer;
  } else if (isEventsInput(inputData)) {
    return styles$5.eventsInputContainer;
  } else {
    return styles$5.chatInputContainer;
  }
};
const InputRenderer = ({
  resultData,
  inputData,
  className,
  scrollRef,
  initialMessageId,
  initialEventId,
  highlightLabeled
}) => {
  if (isTranscriptInput(inputData)) {
    if (inputData.input.messages && inputData.input.messages.length > 0) {
      const labels = resultData?.messageReferences.reduce(
        (acc, ref) => {
          if (ref.cite) {
            acc[ref.id] = ref.cite;
          }
          return acc;
        },
        {}
      );
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        ChatViewVirtualList,
        {
          messages: inputData.input.messages || [],
          allowLinking: false,
          id: "scan-input-virtual-list",
          toolCallStyle: "complete",
          indented: true,
          className,
          scrollRef,
          initialMessageId,
          showLabels: true,
          highlightLabeled,
          labels
        }
      );
    } else if (inputData.input.events && inputData.input.events.length > 0) {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        TimelineEventsView,
        {
          events: inputData.input.events,
          scrollRef,
          id: "scan-input-events",
          initialEventId
        }
      );
    } else {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(NoContentsPanel, { text: "No transcript input available" });
    }
  } else if (isMessagesInput(inputData)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      ChatViewVirtualList,
      {
        messages: inputData.input,
        allowLinking: false,
        id: "scan-input-virtual-list",
        toolCallStyle: "complete",
        indented: true,
        className,
        scrollRef,
        initialMessageId
      }
    );
  } else if (isMessageInput(inputData)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      ChatViewVirtualList,
      {
        messages: [inputData.input],
        allowLinking: false,
        id: "scan-input-virtual-list",
        toolCallStyle: "complete",
        indented: true,
        className,
        scrollRef,
        initialMessageId
      }
    );
  } else if (isEventsInput(inputData)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      TimelineEventsView,
      {
        events: inputData.input,
        scrollRef,
        id: "scan-input-events",
        initialEventId,
        timeline: false
      }
    );
  } else if (isEventInput(inputData)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      TimelineEventsView,
      {
        events: [inputData.input],
        scrollRef,
        id: "scan-input-events",
        initialEventId,
        timeline: false
      }
    );
  } else {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: "Unsupported Input Type" });
  }
};
const container$2 = "_container_19by0_1";
const styles$4 = {
  container: container$2
};
const sidebar = "_sidebar_17smp_1";
const container$1 = "_container_17smp_7";
const colspan = "_colspan_17smp_14";
const values = "_values_17smp_29";
const validation = "_validation_17smp_33";
const validationLabel = "_validationLabel_17smp_39";
const styles$3 = {
  sidebar,
  container: container$1,
  colspan,
  values,
  validation,
  validationLabel
};
const ResultSidebar = ({
  inputData,
  resultData
}) => {
  const refs = useMarkdownRefs(resultData, inputData);
  if (!resultData) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(NoContentsPanel, { text: "No result to display." });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$3.sidebar), children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$3.container, "text-size-small"), children: [
    resultData.label && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-style-label", "text-style-secondary"), children: "Label" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: resultData.label })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-style-label", "text-style-secondary"), children: "Value" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(
          resultData.validationResult !== void 0 ? styles$3.values : void 0
        ),
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            Value,
            {
              summary: resultData,
              style: "block",
              maxTableSize: 1e3,
              interactive: true,
              references: refs,
              options: { previewRefsOnHover: false }
            }
          ),
          resultData.validationResult !== void 0 && resultData.validationResult !== null ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$3.validation), children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "div",
              {
                className: clsx(
                  "text-style-label",
                  "text-style-secondary",
                  styles$3.validationLabel
                ),
                children: "Validation"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              ValidationResult,
              {
                result: resultData.validationResult,
                target: resultData.validationTarget,
                label: resultData.label
              }
            )
          ] }) : void 0
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$3.colspan), children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-style-label", "text-style-secondary"), children: "Explanation" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        Explanation,
        {
          summary: resultData,
          references: refs,
          options: { previewRefsOnHover: false }
        }
      )
    ] }),
    resultData.metadata && Object.keys(resultData.metadata).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-style-label", "text-style-secondary"), children: "Metadata" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        MetaDataGrid,
        {
          entries: resultData.metadata,
          references: refs,
          options: { previewRefsOnHover: false }
        }
      ) })
    ] })
  ] }) });
};
const ResultPanel = ({
  resultData,
  inputData,
  transcriptDir,
  hasTranscript
}) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$4.container, "text-size-base"), children: [
  /* @__PURE__ */ jsxRuntimeExports.jsx(ResultSidebar, { inputData, resultData }),
  inputData ? /* @__PURE__ */ jsxRuntimeExports.jsx(
    ResultBody,
    {
      resultData,
      inputData,
      transcriptDir,
      hasTranscript
    }
  ) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: "No Input Available" })
] });
const header = "_header_1m0jc_1";
const value = "_value_1m0jc_12";
const oneCol = "_oneCol_1m0jc_17";
const twoCol = "_twoCol_1m0jc_21";
const threeCol = "_threeCol_1m0jc_25";
const fourCol = "_fourCol_1m0jc_29";
const fiveCol = "_fiveCol_1m0jc_36";
const sixCol = "_sixCol_1m0jc_42";
const styles$2 = {
  header,
  value,
  oneCol,
  twoCol,
  threeCol,
  fourCol,
  fiveCol,
  sixCol
};
const ScannerResultHeader = ({
  scan,
  inputData,
  appConfig
}) => {
  const columns = colsForResult(appConfig, inputData, scan) || [];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$2.header, classForCols(columns.length)), children: [
    columns.map((col) => {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: clsx(
            "text-size-smallest",
            "text-style-label",
            "text-style-secondary",
            styles$2.label,
            col.className
          ),
          children: col.label
        },
        `header-label-${col.label}`
      );
    }),
    columns.map((col) => {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: clsx("text-size-small", styles$2.value, col.className),
          children: col.value
        },
        `header-val-${col.label}`
      );
    })
  ] });
};
const classForCols = (numCols) => {
  return clsx(
    numCols === 1 ? styles$2.oneCol : numCols === 2 ? styles$2.twoCol : numCols === 3 ? styles$2.threeCol : numCols === 4 ? styles$2.fourCol : numCols === 5 ? styles$2.fiveCol : styles$2.sixCol
  );
};
const colsForResult = (appConfig, inputData, status) => {
  if (!inputData) {
    return [];
  }
  if (isTranscriptInput(inputData)) {
    return transcriptCols(appConfig, inputData.input, status);
  } else if (isMessageInput(inputData)) {
    return messageCols(inputData.input, status);
  } else if (isMessagesInput(inputData)) {
    return messagesCols(inputData.input);
  } else if (isEventInput(inputData)) {
    return eventCols(inputData.input);
  } else if (isEventsInput(inputData)) {
    return eventsCols(inputData.input);
  } else {
    return [];
  }
};
const transcriptCols = (appConfig, transcript, status) => {
  const sourceUri = transcript.source_uri || transcript.metadata?.log || "";
  let resolvedSourceUrl = sourceUri;
  if (resolvedSourceUrl && resolvedSourceUrl.startsWith("/")) {
    resolvedSourceUrl = `file://${resolvedSourceUrl}`;
  }
  const displaySourceUri = projectOrAppAliasedPath(
    appConfig,
    resolvedSourceUrl
  );
  const transcriptModel = transcript.model || transcript.metadata?.model || "";
  const scanningModel = status?.spec.model?.model;
  const taskSet = transcript.task_set || transcript.metadata?.task_name || "";
  const taskId = transcript.task_id || transcript.metadata?.id || "";
  const taskRepeat = transcript.task_repeat || transcript.metadata?.epoch || -1;
  const cols = [
    {
      label: "Task",
      value: /* @__PURE__ */ jsxRuntimeExports.jsx(TaskName, { taskSet, taskId, taskRepeat })
    },
    {
      label: "Source",
      value: displaySourceUri
    },
    {
      label: "Model",
      value: transcriptModel
    }
  ];
  if (status?.spec.model?.model) {
    cols.push({
      label: "Scanning Model",
      value: scanningModel
    });
  }
  return cols;
};
const messageCols = (message, status) => {
  const cols = [
    {
      label: "Message ID",
      value: message.id
    }
  ];
  if (message.role === "assistant") {
    cols.push({
      label: "Model",
      value: message.model
    });
    cols.push({
      label: "Tool Calls",
      value: (message.tool_calls || []).length
    });
  } else {
    cols.push({
      label: "Role",
      value: message.role
    });
  }
  if (status?.spec.model?.model) {
    cols.push({
      label: "Scanning Model",
      value: status.spec.model.model
    });
  }
  return cols;
};
const messagesCols = (messages) => {
  return [
    {
      label: "Message Count",
      value: messages.length
    }
  ];
};
const eventCols = (event) => {
  return [
    {
      label: "Event Type",
      value: event.event
    },
    {
      label: "Timestamp",
      value: event.timestamp ? new Date(event.timestamp).toLocaleString() : void 0
    }
  ];
};
const eventsCols = (events) => {
  return [
    {
      label: "Event Count",
      value: events.length
    }
  ];
};
const ScannerResultNav = () => {
  const navigate = useLoggingNavigate("ScannerResultNav");
  const [searchParams] = useSearchParams();
  const { scansDir, scanPath, scanResultUuid } = useScanRoute();
  const visibleScannerResults = useStore(
    (state) => state.visibleScannerResults
  );
  const currentIndex = reactExports.useMemo(() => {
    if (!visibleScannerResults) {
      return -1;
    }
    return visibleScannerResults.findIndex(
      (s) => s.identifier === scanResultUuid
    );
  }, [visibleScannerResults, scanResultUuid]);
  const hasPrevious = currentIndex > 0;
  const hasNext = visibleScannerResults && currentIndex >= 0 && currentIndex < visibleScannerResults.length - 1;
  const handlePrevious = () => {
    if (!hasPrevious || !visibleScannerResults) {
      return;
    }
    const previousResult = visibleScannerResults[currentIndex - 1];
    if (!scansDir) {
      return;
    }
    const route = scanResultRoute(
      scansDir,
      scanPath,
      previousResult?.identifier,
      searchParams
    );
    void navigate(route);
  };
  const handleNext = () => {
    if (!hasNext || !visibleScannerResults) {
      return;
    }
    const nextResult = visibleScannerResults[currentIndex + 1];
    if (!scansDir) {
      return;
    }
    const route = scanResultRoute(
      scansDir,
      scanPath,
      nextResult?.identifier,
      searchParams
    );
    void navigate(route);
  };
  const result = visibleScannerResults && currentIndex !== -1 ? visibleScannerResults[currentIndex] : void 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    NextPreviousNav,
    {
      onPrevious: handlePrevious,
      onNext: handleNext,
      hasPrevious,
      hasNext: !!hasNext,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-size-smallest", children: visibleScannerResults && currentIndex !== -1 ? printIdentifier(resultIdentifier(result), result?.label) : void 0 })
    }
  );
};
const printIdentifier = (identifier, label) => {
  let val = "";
  if (identifier.epoch) {
    val = `${identifier.id} epoch ${identifier.epoch}`;
  } else {
    val = String(identifier.id);
  }
  if (label && label.length > 0) {
    val += ` (${label})`;
  }
  return val;
};
const root = "_root_g13hf_1";
const tabSet = "_tabSet_g13hf_13";
const tabControl = "_tabControl_g13hf_22";
const tabs = "_tabs_g13hf_26";
const fullHeight = "_fullHeight_g13hf_30";
const contentArea = "_contentArea_g13hf_34";
const tabSetWrapper = "_tabSetWrapper_g13hf_42";
const withValidation = "_withValidation_g13hf_51";
const splitLayout = "_splitLayout_g13hf_55";
const splitStart = "_splitStart_g13hf_60";
const validationSidebar = "_validationSidebar_g13hf_69";
const styles$1 = {
  root,
  tabSet,
  tabControl,
  tabs,
  fullHeight,
  contentArea,
  tabSetWrapper,
  withValidation,
  splitLayout,
  splitStart,
  validationSidebar
};
const container = "_container_1yw87_1";
const styles = {
  container
};
const TranscriptPanel = ({
  id,
  resultData,
  nodeFilter
}) => {
  const scrollRef = reactExports.useRef(null);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: scrollRef, className: clsx(styles.container), children: /* @__PURE__ */ jsxRuntimeExports.jsx(
    TranscriptView,
    {
      id,
      events: resultData?.scanEvents || [],
      scrollRef,
      nodeFilter
    }
  ) });
};
const kTabIdResult = "Result";
const kTabIdError = "Error";
const kTabIdInput = "Input";
const kTabIdInfo = "Info";
const kTabIdJson = "JSON";
const kTabIdTranscript = "transcript";
const kTabIdMetadata = "Metadata";
const ScannerResultPanel = () => {
  const { scanResultUuid } = useScanRoute();
  const [searchParams, setSearchParams] = useSearchParams();
  const { loading: scanLoading, data: selectedScan } = useSelectedScan();
  const { displayScansDir, resolvedScansDirSource, setScansDir } = useScansDir(true);
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  reactExports.useEffect(() => {
    const scannerParam = getScannerParam(searchParams);
    if (scannerParam) {
      setSelectedScanner(scannerParam);
    }
  }, [searchParams, setSelectedScanner]);
  const setSelectedScanResult = useStore(
    (state) => state.setSelectedScanResult
  );
  const setDisplayedScanResult = useStore(
    (state) => state.setDisplayedScanResult
  );
  reactExports.useEffect(() => {
    if (scanResultUuid) {
      setSelectedScanResult(scanResultUuid);
      setDisplayedScanResult(scanResultUuid);
    }
  }, [scanResultUuid, setSelectedScanResult, setDisplayedScanResult]);
  const appConfig = useAppConfig();
  const validationSidebarCollapsed = !getValidationParam(searchParams);
  const toggleValidationSidebar = reactExports.useCallback(() => {
    setSearchParams((prevParams) => {
      const isCurrentlyOpen = getValidationParam(prevParams);
      return updateValidationParam(prevParams, !isCurrentlyOpen);
    });
  }, [setSearchParams]);
  const selectedTab = useStore((state) => state.selectedResultTab);
  const visibleScannerResults = useStore(
    (state) => state.visibleScannerResults
  );
  const setSelectedResultTab = useStore((state) => state.setSelectedResultTab);
  const { data: selectedResult, loading: resultLoading } = useSelectedScanResultData(scanResultUuid);
  const { loading: inputLoading, data: inputData } = useSelectedScanResultInputData(selectedResult?.uuid);
  const taskName = inputData && isTranscriptInput(inputData) ? getTranscriptDisplayName(inputData.input) : void 0;
  useDocumentTitle(
    taskName,
    getScanDisplayName(selectedScan, appConfig.scans.dir),
    "Scans"
  );
  const { resolvedTranscriptsDir } = useTranscriptsDir(false);
  const { loading: hasTranscriptLoading, data: hasTranscript } = useHasTranscript(
    !selectedResult ? skipToken : { id: selectedResult.transcriptId, location: resolvedTranscriptsDir }
  );
  reactExports.useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam) {
      const validTabs = [
        kTabIdResult,
        kTabIdInput,
        kTabIdInfo,
        kTabIdJson,
        kTabIdTranscript
      ];
      if (validTabs.includes(tabParam)) {
        setSelectedResultTab(tabParam);
      }
    }
  }, [searchParams, setSelectedResultTab]);
  const handleTabChange = (tabId) => {
    setSelectedResultTab(tabId);
    const newParams = new URLSearchParams(searchParams);
    newParams.set("tab", tabId);
    setSearchParams(newParams);
  };
  const showEvents = reactExports.useMemo(() => {
    if (!selectedResult?.scanEvents) {
      return false;
    }
    const hasNonSpanEvents = selectedResult.scanEvents.some((event) => {
      return event.event !== "span_begin" && event.event !== "span_end";
    });
    return hasNonSpanEvents;
  }, [selectedResult?.scanEvents]);
  const hasError = selectedResult?.scanError !== void 0 && selectedResult?.scanError !== null;
  const highlightLabeled = useStore((state) => state.highlightLabeled);
  const setHighlightLabeled = useStore((state) => state.setHighlightLabeled);
  const toggleHighlightLabeled = reactExports.useCallback(() => {
    setHighlightLabeled(!highlightLabeled);
  }, [highlightLabeled, setHighlightLabeled]);
  const tools = reactExports.useMemo(() => {
    const toolButtons = [];
    if (selectedTab === kTabIdInput && selectedResult?.inputType === "transcript" && selectedResult?.messageReferences.length > 0) {
      toolButtons.push(
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ToolButton,
          {
            icon: ApplicationIcons.highlight,
            latched: !!highlightLabeled,
            onClick: toggleHighlightLabeled,
            label: "Highlight Refs"
          },
          "highlight-labeled"
        )
      );
    }
    if (selectedResult?.transcriptId) {
      toolButtons.push(
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ToolButton,
          {
            label: "Validation",
            icon: ApplicationIcons.edit,
            onClick: toggleValidationSidebar,
            title: validationSidebarCollapsed ? "Show validation editor" : "Hide validation editor",
            subtle: true
          },
          "validation-sidebar-toggle"
        )
      );
    }
    return toolButtons;
  }, [
    highlightLabeled,
    toggleHighlightLabeled,
    selectedTab,
    selectedResult,
    toggleValidationSidebar,
    validationSidebarCollapsed
  ]);
  const renderTabSet = (resultData) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
    TabSet,
    {
      id: "scan-result-tabs",
      type: "pills",
      tabPanelsClassName: clsx(styles$1.tabSet),
      tabControlsClassName: clsx(styles$1.tabControl),
      className: clsx(styles$1.tabs),
      tools,
      children: [
        hasError ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          TabPanel,
          {
            id: kTabIdError,
            selected: selectedTab === kTabIdError || selectedTab === void 0,
            title: "Error",
            onSelected: () => {
              handleTabChange(kTabIdError);
            },
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              ErrorPanel,
              {
                error: resultData.scanError,
                traceback: resultData.scanErrorTraceback
              }
            )
          }
        ) : void 0,
        !hasError ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          TabPanel,
          {
            id: kTabIdResult,
            selected: selectedTab === kTabIdResult || !hasError && selectedTab === void 0,
            title: "Result",
            scrollable: false,
            onSelected: () => {
              handleTabChange(kTabIdResult);
            },
            className: styles$1.fullHeight,
            children: resultData && inputData && /* @__PURE__ */ jsxRuntimeExports.jsx(
              ResultPanel,
              {
                resultData,
                inputData,
                transcriptDir: resolvedTranscriptsDir,
                hasTranscript: !!hasTranscript
              }
            )
          }
        ) : void 0,
        showEvents ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          TabPanel,
          {
            id: kTabIdTranscript,
            selected: selectedTab === kTabIdTranscript,
            title: "Events",
            onSelected: () => {
              handleTabChange(kTabIdTranscript);
            },
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              TranscriptPanel,
              {
                id: "scan-transcript",
                resultData,
                nodeFilter: skipScanSpan
              }
            )
          }
        ) : void 0,
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          TabPanel,
          {
            id: kTabIdMetadata,
            selected: selectedTab === kTabIdMetadata,
            title: "Metadata",
            onSelected: () => {
              handleTabChange(kTabIdMetadata);
            },
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(MetadataPanel, { resultData })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          TabPanel,
          {
            id: kTabIdInfo,
            selected: selectedTab === kTabIdInfo,
            title: "Info",
            onSelected: () => {
              handleTabChange(kTabIdInfo);
            },
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(InfoPanel, { resultData })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          TabPanel,
          {
            id: kTabIdJson,
            selected: selectedTab === kTabIdJson,
            title: "JSON",
            onSelected: () => {
              handleTabChange(kTabIdJson);
            },
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              JSONPanel,
              {
                id: "scan-result-json-contents",
                data: resultData,
                simple: true,
                className: styles$1.json
              }
            )
          }
        )
      ]
    }
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$1.root), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ScansNavbar,
      {
        scansDir: displayScansDir,
        scansDirSource: resolvedScansDirSource,
        setScansDir,
        children: visibleScannerResults.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(ScannerResultNav, {})
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      LoadingBar,
      {
        loading: scanLoading || resultLoading || inputLoading || hasTranscriptLoading
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ScannerResultHeader,
      {
        inputData,
        scan: selectedScan,
        appConfig
      }
    ),
    selectedResult && /* @__PURE__ */ jsxRuntimeExports.jsx(ExtendedFindProvider, { children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: clsx(
          styles$1.contentArea,
          !validationSidebarCollapsed && styles$1.withValidation
        ),
        children: validationSidebarCollapsed || !selectedResult.transcriptId ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.tabSetWrapper, children: renderTabSet(selectedResult) }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(
          VscodeSplitLayout,
          {
            className: styles$1.splitLayout,
            fixedPane: "end",
            initialHandlePosition: "80%",
            minEnd: "180px",
            minStart: "200px",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { slot: "start", className: styles$1.splitStart, children: renderTabSet(selectedResult) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { slot: "end", className: styles$1.validationSidebar, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                ValidationCaseEditor,
                {
                  transcriptId: selectedResult.transcriptId
                }
              ) })
            ]
          }
        )
      }
    ) })
  ] });
};
const skipScanSpan = (nodes) => {
  if (nodes.length === 1 && nodes[0]?.event.event === "span_begin") {
    return nodes[0].children;
  }
  return nodes;
};
export {
  ScannerResultPanel
};
//# sourceMappingURL=ScannerResultPanel.js.map
