import { a as useApi, b as useAsyncDataFromQuery, r as reactExports, j as jsxRuntimeExports, L as LoadingBar, f as ErrorPanel, A as ApplicationIcons, e as useAppConfig, c as clsx } from "./index.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { N as NoContentsPanel } from "./NoContentsPanel.js";
import { u as useMapAsyncData } from "./useMapAsyncData.js";
import { h as VscodeLabel, k as VscodeTextarea, d as VscodeSingleSelect, e as VscodeOption, j as VscodeCheckbox, a as VscodeButton } from "./VscodeTreeItem.js";
import { u as useScansDir, S as ScansNavbar } from "./useScansDir.js";
import { T as TranscriptsNavbar } from "./useFilterConditions.js";
import { u as useTranscriptsFilterBarProps, T as TranscriptFilterBar } from "./TranscriptFilterBar.js";
import { u as useMutation } from "./useMutation.js";
import { u as useTranscriptsDir } from "./useTranscriptsDir.js";
import "./_commonjsHelpers.js";
import "./Navbar.js";
import "./ToolButton.js";
import "./useFilterBarHandlers.js";
import "./ToolDropdownButton.js";
import "./Chip.js";
import "./transcriptColumns.js";
import "./array.js";
import "./object.js";
const useActiveScans = () => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: ["active-scans"],
    queryFn: async () => (await api.getActiveScans()).items,
    refetchInterval: 5e3
  });
};
const useActiveScan = (scanId2) => useMapAsyncData(
  useActiveScans(),
  reactExports.useCallback(
    (activeScans) => scanId2 ? activeScans[scanId2] ?? void 0 : void 0,
    [scanId2]
  )
);
const container = "_container_1g7rb_1";
const defineScannerSection = "_defineScannerSection_1g7rb_8";
const sectionTitle = "_sectionTitle_1g7rb_14";
const formRow = "_formRow_1g7rb_20";
const formColumn = "_formColumn_1g7rb_25";
const formGroup = "_formGroup_1g7rb_32";
const scannerRow = "_scannerRow_1g7rb_38";
const scannerDescription = "_scannerDescription_1g7rb_44";
const paramsPlaceholder = "_paramsPlaceholder_1g7rb_50";
const runScanRow = "_runScanRow_1g7rb_56";
const checkboxGroup = "_checkboxGroup_1g7rb_63";
const scansList = "_scansList_1g7rb_68";
const card = "_card_1g7rb_77";
const header = "_header_1g7rb_84";
const scanId = "_scanId_1g7rb_90";
const configLine = "_configLine_1g7rb_95";
const progressSection = "_progressSection_1g7rb_102";
const progressBar = "_progressBar_1g7rb_106";
const progressFill = "_progressFill_1g7rb_113";
const progressStats = "_progressStats_1g7rb_119";
const content = "_content_1g7rb_128";
const mainSection = "_mainSection_1g7rb_133";
const table = "_table_1g7rb_137";
const numeric = "_numeric_1g7rb_155";
const sidebar = "_sidebar_1g7rb_159";
const sidebarSection = "_sidebarSection_1g7rb_168";
const sidebarTitle = "_sidebarTitle_1g7rb_173";
const stat = "_stat_1g7rb_178";
const error = "_error_1g7rb_188";
const mutationStatus = "_mutationStatus_1g7rb_193";
const styles = {
  container,
  defineScannerSection,
  sectionTitle,
  formRow,
  formColumn,
  formGroup,
  scannerRow,
  scannerDescription,
  paramsPlaceholder,
  runScanRow,
  checkboxGroup,
  scansList,
  card,
  header,
  scanId,
  configLine,
  progressSection,
  progressBar,
  progressFill,
  progressStats,
  content,
  mainSection,
  table,
  numeric,
  sidebar,
  sidebarSection,
  sidebarTitle,
  stat,
  error,
  mutationStatus
};
const formatMemory = (bytes) => {
  const gb = bytes / (1024 * 1024 * 1024);
  const formatted = gb.toFixed(1).replace(/\.?0+$/, "");
  return `${formatted} GB`;
};
const formatDuration = (seconds) => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor(seconds % 3600 / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0)
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
};
const getValidationScore = (validation) => {
  if (validation?.metrics?.accuracy == null) return null;
  return validation.metrics.accuracy;
};
const getFirstMetricValue = (metrics) => {
  if (!metrics) return null;
  const firstNested = Object.values(metrics)[0];
  if (!firstNested) return null;
  return Object.values(firstNested)[0] ?? null;
};
const getMetricLabel = (scanners) => {
  const names = /* @__PURE__ */ new Set();
  for (const scanner of Object.values(scanners)) {
    if (scanner.metrics) {
      const firstNested = Object.values(scanner.metrics)[0];
      if (firstNested) {
        const firstKey = Object.keys(firstNested)[0];
        if (firstKey) names.add(firstKey);
      }
    }
  }
  return names.size === 1 ? [...names][0] ?? "metric" : "metric";
};
const ActiveScanCard = ({ info }) => {
  const { metrics, summary } = info;
  const [now, setNow] = reactExports.useState(Date.now());
  reactExports.useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1e3);
    return () => clearInterval(interval);
  }, []);
  const hasValidations = info.scanner_names.some(
    (name) => (summary.scanners[name]?.validation?.entries?.length ?? 0) > 0
  );
  const hasMetrics = info.scanner_names.some(
    (name) => summary.scanners[name]?.metrics !== null
  );
  const metricLabel = hasMetrics ? getMetricLabel(summary.scanners) : "";
  const scannerStats = info.scanner_names.map((name) => {
    const scanner = summary.scanners[name];
    const totalTokens = scanner ? Object.values(scanner.model_usage).reduce(
      (sum, usage) => sum + (usage.total_tokens ?? 0),
      0
    ) : 0;
    const tokensPerScan = scanner && scanner.scans > 0 ? Math.round(totalTokens / scanner.scans) : 0;
    const validationScore = scanner ? getValidationScore(scanner.validation) : null;
    const metricValue = scanner ? getFirstMetricValue(scanner.metrics ?? null) : null;
    return {
      name,
      scanner,
      totalTokens,
      tokensPerScan,
      validationScore,
      metricValue
    };
  });
  const completed = metrics.completed_scans;
  const total = info.total_scans;
  const progressPct = total > 0 ? completed / total * 100 : 0;
  const elapsedSec = info.start_time > 0 ? now / 1e3 - info.start_time : 0;
  const remainingSec = completed > 0 && total > completed ? elapsedSec / completed * (total - completed) : 0;
  const hasBatch = metrics.batch_oldest_created !== null;
  const batchAge = hasBatch ? Math.floor(now / 1e3 - (metrics.batch_oldest_created ?? 0)) : 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.card, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.header, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles.scanId, children: info.title || `scan: ${info.scan_id}` }),
      info.config && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.configLine, children: info.config })
    ] }) }),
    total > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.progressSection, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.progressBar, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: styles.progressFill,
          style: { width: `${progressPct}%` }
        }
      ) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.progressStats, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
          completed.toLocaleString(),
          "/",
          total.toLocaleString()
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: formatDuration(elapsedSec) }),
        remainingSec > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: formatDuration(remainingSec) })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.content, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.mainSection, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: styles.table, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { children: "scanner" }),
          hasMetrics && /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: styles.numeric, children: metricLabel }),
          hasValidations && /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: styles.numeric, children: "validation" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: styles.numeric, children: "results" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: styles.numeric, children: "errors" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: styles.numeric, children: "tokens/scan" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: styles.numeric, children: "tokens" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: scannerStats.map(
          ({
            name,
            scanner,
            totalTokens,
            tokensPerScan,
            validationScore,
            metricValue
          }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { children: name }),
            hasMetrics && /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: styles.numeric, children: metricValue !== null ? metricValue === Math.floor(metricValue) ? metricValue.toLocaleString() : metricValue.toFixed(2) : "-" }),
            hasValidations && /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: styles.numeric, children: validationScore !== null ? validationScore.toFixed(2) : "-" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: styles.numeric, children: scanner?.results || "-" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: styles.numeric, children: scanner?.errors || "-" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: styles.numeric, children: tokensPerScan ? tokensPerScan.toLocaleString() : "-" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: styles.numeric, children: totalTokens ? totalTokens.toLocaleString() : "-" })
          ] }, name)
        ) })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.sidebar, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.sidebarSection, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sidebarTitle, children: "workers" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.stat, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "parsing:" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: metrics.tasks_parsing })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.stat, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "scanning:" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: metrics.tasks_scanning })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.stat, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "idle:" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: metrics.tasks_idle })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.stat, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "memory:" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: formatMemory(metrics.memory_usage) })
          ] })
        ] }),
        hasBatch && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.sidebarSection, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sidebarTitle, children: "batch processing" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.stat, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "pending:" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: metrics.batch_pending.toLocaleString() })
          ] }),
          metrics.batch_failures > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.stat, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "failures:" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles.error, children: metrics.batch_failures.toLocaleString() })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.stat, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "max age:" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: formatDuration(batchAge) })
          ] })
        ] })
      ] })
    ] })
  ] });
};
const ActiveScanView = ({ scanId: scanId2 }) => {
  const { loading, error: error2, data: scanInfo } = useActiveScan(scanId2);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.scansList, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(LoadingBar, { loading: !!scanId2 && !!loading }),
    error2 && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ErrorPanel,
      {
        title: "Error Loading Active Scan",
        error: { message: error2.message }
      }
    ),
    !scanId2 && !error2 && /* @__PURE__ */ jsxRuntimeExports.jsx(
      NoContentsPanel,
      {
        icon: ApplicationIcons.running,
        text: "No scan started"
      }
    ),
    scanId2 && !scanInfo && !error2 && !loading && /* @__PURE__ */ jsxRuntimeExports.jsx(
      NoContentsPanel,
      {
        icon: ApplicationIcons.running,
        text: "Scan not found"
      }
    ),
    scanInfo && !error2 && /* @__PURE__ */ jsxRuntimeExports.jsx(ActiveScanCard, { info: scanInfo })
  ] });
};
const useScanners = () => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: ["scanners"],
    queryFn: async () => (await api.getScanners()).items,
    staleTime: 1e4
  });
};
const useStartScan = () => {
  const api = useApi();
  return useMutation({ mutationFn: (config) => api.startScan(config) });
};
function getInputValue(e) {
  return e.target.value;
}
function getSelectValue$1(e) {
  return e.target.value;
}
const placeholderByAnswerType = {
  boolean: "Enter a yes/no question to ask about each transcript...",
  numeric: "Enter a question that yields a numeric answer for each transcript...",
  string: "Enter a question to ask about each transcript..."
};
const LlmScannerParams = ({ value, onChange }) => {
  const update = (partial) => onChange({ ...value, ...partial });
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.formRow, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.formColumn, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.formGroup, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: "Question" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        VscodeTextarea,
        {
          rows: 4,
          placeholder: placeholderByAnswerType[value.answerType],
          value: value.question,
          onInput: (e) => update({ question: getInputValue(e) })
        }
      )
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.formColumn, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.formGroup, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: "Answer type" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          VscodeSingleSelect,
          {
            value: value.answerType,
            onChange: (e) => update({
              answerType: getSelectValue$1(e)
            }),
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "boolean", children: "Boolean" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "numeric", children: "Numeric" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "string", children: "String" })
            ]
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.formGroup, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: "Message filter" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.checkboxGroup, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeCheckbox,
            {
              checked: value.excludeSystem,
              onChange: (e) => update({
                excludeSystem: e.target.checked
              }),
              children: "Exclude system messages"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeCheckbox,
            {
              checked: value.excludeReasoning,
              onChange: (e) => update({
                excludeReasoning: e.target.checked
              }),
              children: "Exclude reasoning content"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeCheckbox,
            {
              checked: value.excludeToolUsage,
              onChange: (e) => update({
                excludeToolUsage: e.target.checked
              }),
              children: "Exclude tool usage"
            }
          )
        ] })
      ] })
    ] })
  ] });
};
const ScannerParamsPlaceholder = ({ scannerName }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.paramsPlaceholder, children: [
  "No parameter editor available for ",
  /* @__PURE__ */ jsxRuntimeExports.jsx("strong", { children: scannerName })
] });
function getSelectValue(e) {
  return e.target.value;
}
const defaultLlmParams = {
  question: "",
  answerType: "boolean",
  excludeSystem: true,
  excludeReasoning: false,
  excludeToolUsage: false
};
const DefineScannerSection = ({ onScanStarted }) => {
  const [selectedScanner, setSelectedScanner] = reactExports.useState(null);
  const [llmParams, setLlmParams] = reactExports.useState(defaultLlmParams);
  const { loading, data: scanners } = useScanners();
  const mutation = useStartScan();
  const config = useAppConfig();
  const filter = Array.isArray(config.filter) ? config.filter.join(" ") : config.filter;
  const {
    displayTranscriptsDir,
    resolvedTranscriptsDir,
    resolvedTranscriptsDirSource,
    setTranscriptsDir
  } = useTranscriptsDir(true);
  const { displayScansDir, resolvedScansDirSource, setScansDir } = useScansDir(true);
  const { filterCodeValues, filterSuggestions, onFilterColumnChange } = useTranscriptsFilterBarProps(resolvedTranscriptsDir);
  const effectiveScanner = selectedScanner ?? scanners?.[0]?.name;
  const selectedScannerInfo = scanners?.find(
    (s) => s.name === effectiveScanner
  );
  const canRunScan = effectiveScanner === "inspect_scout/llm_scanner" && llmParams.question.trim().length > 0 && !mutation.isPending;
  const handleRunScan = () => {
    mutation.mutate(
      {
        name: "inspect_scout/llm_scanner",
        filter: [],
        limit: 100,
        scanners: [
          {
            name: "inspect_scout/llm_scanner",
            version: 0,
            params: {
              question: llmParams.question,
              answer: llmParams.answerType,
              preprocessor: {
                exclude_system: llmParams.excludeSystem,
                exclude_reasoning: llmParams.excludeReasoning,
                exclude_tool_usage: llmParams.excludeToolUsage
              }
            }
          }
        ]
      },
      { onSuccess: (data) => onScanStarted(data.spec.scan_id) }
    );
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      TranscriptsNavbar,
      {
        transcriptsDir: displayTranscriptsDir,
        transcriptsDirSource: resolvedTranscriptsDirSource,
        filter,
        setTranscriptsDir
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      TranscriptFilterBar,
      {
        filterCodeValues,
        filterSuggestions,
        onFilterColumnChange,
        includeColumnPicker: false
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ScansNavbar,
      {
        scansDir: displayScansDir,
        setScansDir,
        scansDirSource: resolvedScansDirSource
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.defineScannerSection, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: styles.sectionTitle, children: "Define Scanner" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.formGroup, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: "Type" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.scannerRow, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeSingleSelect,
            {
              value: effectiveScanner ?? "",
              onChange: (e) => setSelectedScanner(getSelectValue(e)),
              disabled: loading,
              children: scanners?.map((s) => /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: s.name, children: s.name }, s.name))
            }
          ),
          selectedScannerInfo?.description && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.scannerDescription, children: selectedScannerInfo.description })
        ] })
      ] }),
      effectiveScanner === "inspect_scout/llm_scanner" ? /* @__PURE__ */ jsxRuntimeExports.jsx(LlmScannerParams, { value: llmParams, onChange: setLlmParams }) : effectiveScanner ? /* @__PURE__ */ jsxRuntimeExports.jsx(ScannerParamsPlaceholder, { scannerName: effectiveScanner }) : null,
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.runScanRow, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(VscodeButton, { disabled: !canRunScan, onClick: handleRunScan, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.play }),
          "Run Scan"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.mutationStatus, children: [
          "start scan status: ",
          mutation.status
        ] })
      ] })
    ] })
  ] });
};
const RunScanPanel = () => {
  useDocumentTitle("Run Scan");
  const [scanId2, setScanId] = reactExports.useState();
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles.container), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(DefineScannerSection, { onScanStarted: setScanId }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(ActiveScanView, { scanId: scanId2 })
  ] });
};
export {
  RunScanPanel
};
//# sourceMappingURL=RunScanPanel.js.map
