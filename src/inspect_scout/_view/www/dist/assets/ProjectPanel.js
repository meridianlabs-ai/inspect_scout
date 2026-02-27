import { a as useApi, b as useAsyncDataFromQuery, P as useQueryClient, r as reactExports, j as jsxRuntimeExports, X as useBlocker, N as ApiError, Y as appAliasedPath } from "./index.js";
import { h as VscodeLabel, i as VscodeFormHelper, f as VscodeTextfield, j as VscodeCheckbox, a as VscodeButton } from "./VscodeTreeItem.js";
import { M as Modal } from "./Modal.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { u as useMutation } from "./useMutation.js";
import { s as styles, T as TextField, N as NumberField, K as KeyValueField, S as SelectField } from "./FormFields.js";
import "./_commonjsHelpers.js";
const useProjectConfig = () => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: ["project-config", "project-config-inv"],
    queryFn: () => api.getProjectConfig(),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false
  });
};
const useUpdateProjectConfig = () => {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ config, etag }) => api.updateProjectConfig(config, etag),
    onSuccess: (data) => {
      queryClient.setQueryData(["project-config", "project-config-inv"], data);
      queryClient.invalidateQueries({ queryKey: ["config", "project-config-inv"] }).catch(console.log);
    }
  });
};
function configsEqual(a, b) {
  if (a === b) return true;
  if (!a || !b) return false;
  return JSON.stringify(a) === JSON.stringify(b);
}
function isEmpty(value) {
  if (value === null || value === void 0) return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.keys(value).length === 0;
  return false;
}
function filterNullValues(obj) {
  return Object.fromEntries(
    Object.entries(obj).filter(([, v]) => v !== null && v !== void 0)
  );
}
function deepCopy(obj) {
  return JSON.parse(JSON.stringify(obj));
}
function cleanNestedConfig(edited, original) {
  if (typeof edited === "boolean" || typeof edited === "number") {
    return edited;
  }
  if (edited === null || edited === void 0) {
    if (original !== null && original !== void 0) {
      return null;
    }
    return void 0;
  }
  const result = {};
  const originalObj = typeof original === "object" && original !== null ? original : {};
  for (const [key, value] of Object.entries(edited)) {
    const origValue = originalObj[key];
    const valueChanged = JSON.stringify(value) !== JSON.stringify(origValue);
    if (valueChanged) {
      result[key] = value;
    } else if (!isEmpty(value)) {
      result[key] = value;
    }
  }
  if (Object.keys(result).length === 0) {
    if (original !== null && original !== void 0) {
      return true;
    }
    return void 0;
  }
  return result;
}
function cleanGenerateConfig(edited, original) {
  if (edited === null || edited === void 0 || typeof edited === "object" && Object.keys(edited).length === 0) {
    const originalHasContent = original !== null && original !== void 0 && typeof original === "object" && Object.keys(original).length > 0;
    if (originalHasContent) {
      return null;
    }
    return void 0;
  }
  const result = {};
  const originalObj = original ?? {};
  for (const key of Object.keys(edited)) {
    const editedValue = edited[key];
    const originalValue = originalObj[key];
    if (key === "cache" || key === "batch") {
      const cleanedNested = cleanNestedConfig(
        editedValue,
        originalValue
      );
      if (cleanedNested !== void 0) {
        result[key] = cleanedNested;
      }
      continue;
    }
    if (editedValue === null || editedValue === void 0) {
      const originalHadContent = originalValue !== null && originalValue !== void 0 && (typeof originalValue !== "object" || Object.keys(originalValue).length > 0);
      if (originalHadContent) {
        result[key] = null;
      }
      continue;
    }
    result[key] = editedValue;
  }
  if (Object.keys(result).length === 0) {
    return void 0;
  }
  return result;
}
function computeConfigToSave(edited, original, serverConfig) {
  const result = {};
  const allKeys = /* @__PURE__ */ new Set([
    ...Object.keys(edited),
    ...Object.keys(serverConfig)
  ]);
  for (const key of allKeys) {
    const editedValue = edited[key];
    const originalValue = original[key];
    if (key === "generate_config") {
      const cleanedGenConfig = cleanGenerateConfig(
        editedValue,
        originalValue
      );
      if (cleanedGenConfig !== void 0) {
        result[key] = cleanedGenConfig;
      }
      continue;
    }
    const valueChanged = JSON.stringify(editedValue) !== JSON.stringify(originalValue);
    if (valueChanged) {
      result[key] = editedValue;
    } else if (!isEmpty(editedValue)) {
      result[key] = editedValue;
    }
  }
  return result;
}
function initializeEditedConfig(serverConfig) {
  return {
    transcripts: serverConfig.transcripts ?? null,
    filter: serverConfig.filter ?? null,
    scans: serverConfig.scans ?? null,
    max_transcripts: serverConfig.max_transcripts ?? null,
    max_processes: serverConfig.max_processes ?? null,
    limit: serverConfig.limit ?? null,
    shuffle: serverConfig.shuffle ?? null,
    tags: serverConfig.tags ?? null,
    metadata: serverConfig.metadata ?? null,
    log_level: serverConfig.log_level ?? null,
    model: serverConfig.model ?? null,
    model_base_url: serverConfig.model_base_url ?? null,
    model_args: serverConfig.model_args ?? null,
    generate_config: serverConfig.generate_config ?? null
  };
}
const STABLE_EMPTY_OBJECT = {};
function useNestedConfig(configValue, updateParent) {
  const enabled = configValue !== null && configValue !== void 0 && configValue !== false;
  const config = reactExports.useMemo(() => {
    if (typeof configValue === "object" && configValue !== null) {
      return { ...configValue };
    }
    return {};
  }, [configValue]);
  const setEnabled = reactExports.useCallback(
    (newEnabled) => {
      if (newEnabled) {
        updateParent(true);
      } else {
        updateParent(null);
      }
    },
    [updateParent]
  );
  const updateConfig = reactExports.useCallback(
    (updates) => {
      const existingConfig = typeof configValue === "object" && configValue !== null ? filterNullValues(configValue) : {};
      updateParent({
        ...existingConfig,
        ...updates
      });
    },
    [configValue, updateParent]
  );
  return {
    enabled,
    config,
    setEnabled,
    updateConfig
  };
}
function useBatchConfig(configValue, updateParent) {
  const base = useNestedConfig(configValue, updateParent);
  const simpleBatchSize = typeof configValue === "number" ? configValue : null;
  const updateConfig = reactExports.useCallback(
    (updates) => {
      const existingConfig = typeof configValue === "object" && configValue !== null ? filterNullValues(configValue) : {};
      const size = typeof configValue === "number" ? configValue : existingConfig.size;
      updateParent({
        ...size !== void 0 ? { size } : {},
        ...existingConfig,
        ...updates
      });
    },
    [configValue, updateParent]
  );
  const currentBatchSize = reactExports.useMemo(() => {
    if (typeof configValue === "object" && configValue !== null) {
      return configValue.size;
    }
    return simpleBatchSize ?? void 0;
  }, [configValue, simpleBatchSize]);
  return {
    ...base,
    updateConfig,
    currentBatchSize
  };
}
const LOG_LEVELS = [
  "debug",
  "http",
  "sandbox",
  "info",
  "warning",
  "error",
  "critical",
  "notset"
];
const VERBOSITY_OPTIONS = ["low", "medium", "high"];
const EFFORT_OPTIONS = ["low", "medium", "high"];
const REASONING_EFFORT_OPTIONS = [
  "none",
  "minimal",
  "low",
  "medium",
  "high",
  "xhigh"
];
const REASONING_SUMMARY_OPTIONS = [
  "none",
  "concise",
  "detailed",
  "auto"
];
const REASONING_HISTORY_OPTIONS = ["none", "all", "last", "auto"];
const CACHE_EXPIRY_PATTERN = /^\d+[MHDWmhdw]$/;
function validateCacheExpiry(value) {
  if (!value) return null;
  if (CACHE_EXPIRY_PATTERN.test(value)) return null;
  return "Invalid format. Use a number followed by M, H, D, or W (e.g., 30M, 24H, 7D, 1W)";
}
const SettingsContent = ({
  config,
  onChange
}) => {
  const generateConfig = config.generate_config ?? STABLE_EMPTY_OBJECT;
  const updateGenerateConfig = reactExports.useCallback(
    (updates) => {
      const merged = {
        ...filterNullValues(generateConfig),
        ...updates
      };
      const cleaned = filterNullValues(merged);
      const hasContent = Object.keys(cleaned).length > 0;
      onChange({
        generate_config: hasContent ? cleaned : null
      });
    },
    [generateConfig, onChange]
  );
  const cache = useNestedConfig(
    generateConfig.cache,
    reactExports.useCallback(
      (value) => updateGenerateConfig({ cache: value }),
      [updateGenerateConfig]
    )
  );
  const batch = useBatchConfig(
    generateConfig.batch,
    reactExports.useCallback(
      (value) => updateGenerateConfig({ batch: value }),
      [updateGenerateConfig]
    )
  );
  const cacheOptionsRef = reactExports.useRef(null);
  const batchOptionsRef = reactExports.useRef(null);
  const scrollToBottom = reactExports.useCallback((element) => {
    if (!element) return;
    let scrollContainer = element.parentElement;
    while (scrollContainer) {
      const overflow = getComputedStyle(scrollContainer).overflowY;
      if (overflow === "auto" || overflow === "scroll") {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight,
          behavior: "smooth"
        });
        return;
      }
      scrollContainer = scrollContainer.parentElement;
    }
  }, []);
  const handleCacheEnabled = reactExports.useCallback(() => {
    setTimeout(() => {
      scrollToBottom(cacheOptionsRef.current);
    }, 150);
  }, [scrollToBottom]);
  const handleBatchEnabled = reactExports.useCallback(() => {
    setTimeout(() => {
      scrollToBottom(batchOptionsRef.current);
    }, 150);
  }, [scrollToBottom]);
  const [tagsText, setTagsText] = reactExports.useState(
    () => Array.isArray(config.tags) ? config.tags.join(", ") : config.tags ?? ""
  );
  reactExports.useEffect(() => {
    const configValue = Array.isArray(config.tags) ? config.tags.join(", ") : config.tags ?? "";
    const currentParsed = tagsText.split(",").map((t) => t.trim()).filter((t) => t.length > 0);
    const configParsed = Array.isArray(config.tags) ? config.tags : [];
    if (JSON.stringify(currentParsed) !== JSON.stringify(configParsed)) {
      setTagsText(configValue);
    }
  }, [config.tags, tagsText]);
  const handleTagsInput = (value) => {
    setTagsText(value);
    const tags = value.split(",").map((t) => t.trim()).filter((t) => t.length > 0);
    onChange({ tags: tags.length > 0 ? tags : null });
  };
  const shuffleEnabled = config.shuffle !== null && config.shuffle !== void 0;
  const shuffleSeed = typeof config.shuffle === "number" ? config.shuffle : null;
  const handleShuffleToggle = (enabled) => {
    onChange({ shuffle: enabled ? true : null });
  };
  const handleShuffleSeedChange = (value) => {
    const num = parseInt(value, 10);
    onChange({ shuffle: isNaN(num) ? true : num });
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id: "locations", className: styles.section, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sectionHeader, children: "Locations" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        TextField,
        {
          id: "field-transcripts",
          label: "Transcripts",
          helper: "Transcripts to scan (filesystem, S3 bucket, etc.)",
          value: config.transcripts,
          onChange: (v) => onChange({ transcripts: v }),
          placeholder: "Path to transcripts"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        TextField,
        {
          id: "field-scans",
          label: "Scans",
          helper: "Location to write scan results (filesystem, S3 bucket, etc.)",
          value: config.scans,
          onChange: (v) => onChange({ scans: v }),
          placeholder: "Path to scans output"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id: "scanning", className: styles.section, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sectionHeader, children: "Scanning" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: "Filter" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: "SQL WHERE clause(s) for filtering transcripts. This will constrain any scan done within the project (i.e. filters applied to individual scans will be AND combined with this filter)." }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          VscodeTextfield,
          {
            id: "field-filter",
            value: Array.isArray(config.filter) ? config.filter.join("; ") : config.filter ?? "",
            onInput: (e) => onChange({
              filter: e.target.value || void 0
            }),
            placeholder: "Filter expression",
            spellCheck: false,
            autocomplete: "off"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-limit",
          label: "Limit",
          helper: "Limit the number of transcripts processed per scanner",
          value: config.limit,
          onChange: (v) => onChange({ limit: v }),
          placeholder: "No limit"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: "Shuffle" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: "Shuffle the order of transcripts (optionally specify a seed)" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { style: { display: "flex", gap: "0.5rem", alignItems: "center" }, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeCheckbox,
            {
              id: "field-shuffle",
              checked: shuffleEnabled,
              onChange: (e) => handleShuffleToggle(e.target.checked),
              children: "Enabled"
            }
          ),
          shuffleEnabled && /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeTextfield,
            {
              id: "field-shuffle-seed",
              type: "number",
              value: shuffleSeed?.toString() ?? "",
              onInput: (e) => handleShuffleSeedChange(e.target.value),
              placeholder: "Seed (optional)",
              style: { width: "120px" },
              spellCheck: false,
              autocomplete: "off"
            }
          )
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id: "concurrency", className: styles.section, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sectionHeader, children: "Concurrency" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-max-transcripts",
          label: "Max Transcripts",
          helper: "Maximum number of transcripts to process concurrently (default: 25)",
          value: config.max_transcripts,
          onChange: (v) => onChange({ max_transcripts: v }),
          placeholder: "25"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-max-processes",
          label: "Max Processes",
          helper: "Maximum number of concurrent processes for multiprocessing (default: 4)",
          value: config.max_processes,
          onChange: (v) => onChange({ max_processes: v }),
          placeholder: "4"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id: "miscellaneous", className: styles.section, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sectionHeader, children: "Miscellaneous" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: "Tags" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: "One or more tags to apply to scans (comma-separated)" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          VscodeTextfield,
          {
            id: "field-tags",
            value: tagsText,
            onInput: (e) => handleTagsInput(e.target.value),
            placeholder: "tag1, tag2, tag3",
            spellCheck: false,
            autocomplete: "off"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        KeyValueField,
        {
          id: "field-metadata",
          label: "Metadata",
          helper: "Key/value pairs to apply to scans (one per line)",
          value: config.metadata,
          onChange: (v) => onChange({ metadata: v }),
          placeholder: "key=value"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SelectField,
        {
          id: "field-log-level",
          label: "Log Level",
          helper: "Level for logging to the console (default: warning)",
          value: config.log_level,
          options: LOG_LEVELS,
          onChange: (v) => onChange({ log_level: v }),
          defaultLabel: "Default (warning)"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id: "model", className: styles.section, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sectionHeader, children: "Model" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(VscodeFormHelper, { style: { marginBottom: "-5px" }, children: [
        "Model configuration specifies the defaults for the model used by the LLM scanner, as well as the model returned by calls to",
        " ",
        /* @__PURE__ */ jsxRuntimeExports.jsx("code", { children: "get_model()" }),
        " in custom scanners."
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        TextField,
        {
          id: "field-model",
          label: "Model",
          helper: "Default model for LLM scanning (scanners can override as required)",
          value: config.model,
          onChange: (v) => onChange({ model: v }),
          placeholder: "e.g., openai/gpt-5"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        TextField,
        {
          id: "field-model-base-url",
          label: "Model Base URL",
          helper: "Base URL for communicating with the model API",
          value: config.model_base_url,
          onChange: (v) => onChange({ model_base_url: v }),
          placeholder: "API base URL"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        KeyValueField,
        {
          id: "field-model-args",
          label: "Model Args",
          helper: "Model creation args (key=value per line, or path to config file)",
          value: config.model_args,
          onChange: (v) => onChange({ model_args: v }),
          placeholder: "key=value or /path/to/config.yaml"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id: "connection", className: styles.section, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sectionHeader, children: "Connection" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-max-connections",
          label: "Max Connections",
          helper: "Maximum concurrent connections to Model API (defaults to max_transcripts)",
          value: generateConfig.max_connections,
          onChange: (v) => updateGenerateConfig({ max_connections: v }),
          placeholder: "Default"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-max-retries",
          label: "Max Retries",
          helper: "Maximum number of times to retry request (defaults to unlimited)",
          value: generateConfig.max_retries,
          onChange: (v) => updateGenerateConfig({ max_retries: v }),
          placeholder: "Unlimited"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-timeout",
          label: "Timeout",
          helper: "Timeout (seconds) for entire request including retries",
          value: generateConfig.timeout,
          onChange: (v) => updateGenerateConfig({ timeout: v }),
          placeholder: "No timeout"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-attempt-timeout",
          label: "Attempt Timeout",
          helper: "Timeout (seconds) for any given attempt before retrying",
          value: generateConfig.attempt_timeout,
          onChange: (v) => updateGenerateConfig({ attempt_timeout: v }),
          placeholder: "No timeout"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id: "generation", className: styles.section, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sectionHeader, children: "Generation" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-max-tokens",
          label: "Max Tokens",
          helper: "Maximum tokens that can be generated in the completion",
          value: generateConfig.max_tokens,
          onChange: (v) => updateGenerateConfig({ max_tokens: v }),
          placeholder: "Model default"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-temperature",
          label: "Temperature",
          helper: "Sampling temperature (0-2). Higher = more random",
          value: generateConfig.temperature,
          onChange: (v) => updateGenerateConfig({ temperature: v }),
          placeholder: "Model default",
          step: 0.1
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-top-p",
          label: "Top P",
          helper: "Nucleus sampling probability mass",
          value: generateConfig.top_p,
          onChange: (v) => updateGenerateConfig({ top_p: v }),
          placeholder: "Model default",
          step: 0.1
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-top-k",
          label: "Top K",
          helper: "Sample from top K most likely next tokens",
          value: generateConfig.top_k,
          onChange: (v) => updateGenerateConfig({ top_k: v }),
          placeholder: "Model default"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-frequency-penalty",
          label: "Frequency Penalty",
          helper: "Penalize tokens based on frequency (-2 to 2)",
          value: generateConfig.frequency_penalty,
          onChange: (v) => updateGenerateConfig({ frequency_penalty: v }),
          placeholder: "Model default",
          step: 0.1
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-presence-penalty",
          label: "Presence Penalty",
          helper: "Penalize new tokens based on presence (-2 to 2)",
          value: generateConfig.presence_penalty,
          onChange: (v) => updateGenerateConfig({ presence_penalty: v }),
          placeholder: "Model default",
          step: 0.1
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-seed",
          label: "Seed",
          helper: "Random seed for reproducibility",
          value: generateConfig.seed,
          onChange: (v) => updateGenerateConfig({ seed: v }),
          placeholder: "Random"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SelectField,
        {
          id: "field-verbosity",
          label: "Verbosity",
          helper: "Response verbosity (GPT 5.x models only)",
          value: generateConfig.verbosity,
          options: VERBOSITY_OPTIONS,
          onChange: (v) => updateGenerateConfig({ verbosity: v })
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SelectField,
        {
          id: "field-effort",
          label: "Effort",
          helper: "Response thoroughness (Claude Opus 4.5 only)",
          value: generateConfig.effort,
          options: EFFORT_OPTIONS,
          onChange: (v) => updateGenerateConfig({ effort: v })
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id: "reasoning", className: styles.section, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sectionHeader, children: "Reasoning" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SelectField,
        {
          id: "field-reasoning-effort",
          label: "Reasoning Effort",
          helper: "Constrains effort on reasoning (varies by provider/model)",
          value: generateConfig.reasoning_effort,
          options: REASONING_EFFORT_OPTIONS,
          onChange: (v) => updateGenerateConfig({ reasoning_effort: v })
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        NumberField,
        {
          id: "field-reasoning-tokens",
          label: "Reasoning Tokens",
          helper: "Maximum tokens for reasoning (Anthropic/Google only)",
          value: generateConfig.reasoning_tokens,
          onChange: (v) => updateGenerateConfig({ reasoning_tokens: v }),
          placeholder: "Model default"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SelectField,
        {
          id: "field-reasoning-summary",
          label: "Reasoning Summary",
          helper: "Summary of reasoning steps (OpenAI reasoning models only)",
          value: generateConfig.reasoning_summary,
          options: REASONING_SUMMARY_OPTIONS,
          onChange: (v) => updateGenerateConfig({ reasoning_summary: v })
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SelectField,
        {
          id: "field-reasoning-history",
          label: "Reasoning History",
          helper: "Include reasoning in chat message history",
          value: generateConfig.reasoning_history,
          options: REASONING_HISTORY_OPTIONS,
          onChange: (v) => updateGenerateConfig({ reasoning_history: v })
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id: "cache", className: styles.section, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sectionHeader, children: "Cache" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          VscodeCheckbox,
          {
            id: "field-cache-enabled",
            checked: cache.enabled,
            onChange: (e) => {
              const checked = e.target.checked;
              cache.setEnabled(checked);
              if (checked) handleCacheEnabled();
            },
            children: "Enable Caching"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: "Cache model responses to improve performance and reduce API costs" })
      ] }),
      cache.enabled && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { ref: cacheOptionsRef, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          TextField,
          {
            id: "field-cache-expiry",
            label: "Expiry",
            helper: "Cache expiration. Use a number followed by: M (minutes), H (hours), D (days), or W (weeks).",
            value: cache.config.expiry,
            onChange: (v) => cache.updateConfig({ expiry: v }),
            placeholder: "1W (default)",
            validate: validateCacheExpiry
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: "Per Epoch" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: "Maintain separate cache entries per epoch" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeCheckbox,
            {
              id: "field-cache-per-epoch",
              checked: cache.config.per_epoch ?? true,
              onChange: (e) => cache.updateConfig({
                per_epoch: e.target.checked
              }),
              children: "Enabled"
            }
          )
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id: "batch", className: styles.section, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.sectionHeader, children: "Batch" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          VscodeCheckbox,
          {
            id: "field-batch-enabled",
            checked: batch.enabled,
            onChange: (e) => {
              const checked = e.target.checked;
              batch.setEnabled(checked);
              if (checked) handleBatchEnabled();
            },
            children: "Enable Batch Processing"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: "Process multiple requests in batches for improved throughput" })
      ] }),
      batch.enabled && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { ref: batchOptionsRef, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          NumberField,
          {
            id: "field-batch-size",
            label: "Batch Size",
            helper: "Number of requests per batch",
            value: batch.currentBatchSize,
            onChange: (v) => batch.updateConfig({ size: v }),
            placeholder: "Default"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          NumberField,
          {
            id: "field-batch-max-size",
            label: "Max Size",
            helper: "Maximum batch size allowed",
            value: batch.config.max_size,
            onChange: (v) => batch.updateConfig({ max_size: v }),
            placeholder: "No limit"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          NumberField,
          {
            id: "field-batch-max-batches",
            label: "Max Batches",
            helper: "Maximum number of batches to process",
            value: batch.config.max_batches,
            onChange: (v) => batch.updateConfig({ max_batches: v }),
            placeholder: "No limit"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          NumberField,
          {
            id: "field-batch-send-delay",
            label: "Send Delay",
            helper: "Delay (seconds) before sending batch",
            value: batch.config.send_delay,
            onChange: (v) => batch.updateConfig({ send_delay: v }),
            placeholder: "0",
            step: 0.1
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          NumberField,
          {
            id: "field-batch-tick",
            label: "Tick",
            helper: "Tick interval (seconds) for batch processing",
            value: batch.config.tick,
            onChange: (v) => batch.updateConfig({ tick: v }),
            placeholder: "Default",
            step: 0.1
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          NumberField,
          {
            id: "field-batch-max-check-failures",
            label: "Max Check Failures",
            helper: "Maximum consecutive check failures before abort",
            value: batch.config.max_consecutive_check_failures,
            onChange: (v) => batch.updateConfig({ max_consecutive_check_failures: v }),
            placeholder: "No limit"
          }
        )
      ] })
    ] })
  ] });
};
const NAV_SECTIONS = [
  {
    group: "General",
    items: [
      { id: "locations", label: "Locations" },
      { id: "scanning", label: "Scanning" },
      { id: "concurrency", label: "Concurrency" },
      { id: "miscellaneous", label: "Miscellaneous" }
    ]
  },
  {
    group: "Model",
    items: [
      { id: "model", label: "Model" },
      { id: "connection", label: "Connection" },
      { id: "generation", label: "Generation" },
      { id: "reasoning", label: "Reasoning" },
      { id: "cache", label: "Cache" },
      { id: "batch", label: "Batch" }
    ]
  }
];
const ProjectPanel = ({ config }) => {
  useDocumentTitle("Project");
  const containerRef = reactExports.useRef(null);
  const scrollContentRef = reactExports.useRef(null);
  const focusedFieldIdRef = reactExports.useRef(null);
  const saveRef = reactExports.useRef(() => {
  });
  const lastSavedEtagRef = reactExports.useRef(null);
  const handleSaveMouseDown = reactExports.useCallback(() => {
    const el = document.activeElement;
    if (el && el !== document.body && el.id) {
      focusedFieldIdRef.current = el.id;
    } else {
      focusedFieldIdRef.current = null;
    }
  }, []);
  const scrollToSection = reactExports.useCallback((sectionId) => {
    const container = scrollContentRef.current;
    const element = document.getElementById(sectionId);
    if (container && element) {
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();
      const scrollTop = container.scrollTop + (elementRect.top - containerRect.top);
      container.scrollTo({ top: scrollTop, behavior: "smooth" });
    }
  }, []);
  const queryClient = useQueryClient();
  const { loading, error, data } = useProjectConfig();
  const mutation = useUpdateProjectConfig();
  reactExports.useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        if (!mutation.isPending) {
          const el = document.activeElement;
          if (el && el !== document.body && el.id) {
            focusedFieldIdRef.current = el.id;
          } else {
            focusedFieldIdRef.current = null;
          }
          saveRef.current();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mutation.isPending]);
  const [editedConfig, setEditedConfig] = reactExports.useState(null);
  const [originalConfig, setOriginalConfig] = reactExports.useState(null);
  const [conflictError, setConflictError] = reactExports.useState(false);
  reactExports.useEffect(() => {
    if (!data) return;
    if (!editedConfig) {
      const initialized2 = initializeEditedConfig(
        data.config
      );
      setEditedConfig(initialized2);
      setOriginalConfig(deepCopy(initialized2));
      lastSavedEtagRef.current = data.etag;
      return;
    }
    if (data.etag === lastSavedEtagRef.current) {
      return;
    }
    const initialized = initializeEditedConfig(
      data.config
    );
    setEditedConfig(initialized);
    setOriginalConfig(deepCopy(initialized));
    lastSavedEtagRef.current = data.etag;
  }, [data, editedConfig]);
  const hasChanges = reactExports.useMemo(() => {
    return !configsEqual(editedConfig, originalConfig);
  }, [editedConfig, originalConfig]);
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) => hasChanges && currentLocation.pathname !== nextLocation.pathname
  );
  const handleConfigChange = reactExports.useCallback(
    (updates) => {
      setEditedConfig((prev) => ({
        ...prev,
        ...updates
      }));
    },
    []
  );
  const handleSave = reactExports.useCallback(
    (force = false) => {
      if (!data || !editedConfig || !originalConfig) return;
      const updatedConfig = computeConfigToSave(
        editedConfig,
        originalConfig,
        data.config
      );
      mutation.mutate(
        { config: updatedConfig, etag: force ? null : data.etag },
        {
          onSuccess: (responseData) => {
            setConflictError(false);
            lastSavedEtagRef.current = responseData.etag;
            setOriginalConfig(deepCopy(editedConfig));
            const fieldId = focusedFieldIdRef.current;
            setTimeout(() => {
              if (fieldId) {
                const field = document.getElementById(fieldId);
                if (field) {
                  field.focus();
                }
              }
            }, 100);
          },
          onError: (err) => {
            if (err instanceof ApiError && err.status === 412) {
              setConflictError(true);
            }
          }
        }
      );
    },
    [data, editedConfig, originalConfig, mutation]
  );
  reactExports.useEffect(() => {
    saveRef.current = () => handleSave(false);
  }, [handleSave]);
  const handleSaveWithFocusRestore = (force = false) => {
    if (!data || !editedConfig || !originalConfig) return;
    const updatedConfig = computeConfigToSave(
      editedConfig,
      originalConfig,
      data.config
    );
    mutation.mutate(
      { config: updatedConfig, etag: force ? null : data.etag },
      {
        onSuccess: (responseData) => {
          setConflictError(false);
          lastSavedEtagRef.current = responseData.etag;
          setOriginalConfig(deepCopy(editedConfig));
          const fieldId = focusedFieldIdRef.current;
          setTimeout(() => {
            if (fieldId) {
              const field = document.getElementById(fieldId);
              if (field) {
                field.focus();
              }
            }
          }, 100);
        },
        onError: (err) => {
          if (err instanceof ApiError && err.status === 412) {
            setConflictError(true);
          }
        }
      }
    );
  };
  const handleSaveAndNavigate = () => {
    if (!data || !editedConfig || !originalConfig) {
      blocker.proceed?.();
      return;
    }
    const updatedConfig = computeConfigToSave(
      editedConfig,
      originalConfig,
      data.config
    );
    mutation.mutate(
      { config: updatedConfig, etag: data.etag },
      {
        onSuccess: (responseData) => {
          setConflictError(false);
          lastSavedEtagRef.current = responseData.etag;
          setOriginalConfig(deepCopy(editedConfig));
          blocker.proceed?.();
        },
        onError: (err) => {
          if (err instanceof ApiError && err.status === 412) {
            setConflictError(true);
          }
          blocker.reset?.();
        }
      }
    );
  };
  const handleReload = () => {
    setConflictError(false);
    setEditedConfig(null);
    setOriginalConfig(null);
    lastSavedEtagRef.current = null;
    void queryClient.invalidateQueries({ queryKey: ["project-config-inv"] });
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { ref: containerRef, className: styles.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.headerRow, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.header, children: "Project Settings" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.detail, children: [
          appAliasedPath(config, config.project_dir),
          "/scout.yaml"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        VscodeButton,
        {
          disabled: !hasChanges || mutation.isPending,
          onMouseDown: handleSaveMouseDown,
          onClick: () => handleSaveWithFocusRestore(false),
          children: mutation.isPending ? "Saving..." : "Save Changes"
        }
      )
    ] }),
    conflictError && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.conflictBanner, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "Configuration was modified externally." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.conflictActions, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { secondary: true, onClick: handleReload, children: "Discard My Changes" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { onClick: () => handleSaveWithFocusRestore(true), children: "Keep My Changes" })
      ] })
    ] }),
    loading && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.loading, children: "Loading..." }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.error, children: [
      "Error loading config: ",
      error.message
    ] }),
    editedConfig && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.splitLayout, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("nav", { className: styles.treeNav, children: /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: styles.navList, children: NAV_SECTIONS.map((section) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: styles.navListItem, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles.navGroup, children: section.group }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: styles.navList, children: section.items.map((item) => /* @__PURE__ */ jsxRuntimeExports.jsx("li", { className: styles.navListItem, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: styles.navItem,
            onClick: () => scrollToSection(item.id),
            children: item.label
          }
        ) }, item.id)) })
      ] }, section.group)) }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { ref: scrollContentRef, className: styles.scrollContent, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { style: { marginBottom: "10px" }, children: "Project settings provide default options for scans run from the project directory. You can override some or all of the defaults for each scan using command line parameters or a scan job config file." }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          SettingsContent,
          {
            config: editedConfig,
            onChange: handleConfigChange
          }
        )
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Modal,
      {
        show: blocker.state === "blocked",
        onHide: () => blocker.reset?.(),
        title: "Unsaved Changes",
        footer: /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { secondary: true, onClick: () => blocker.proceed?.(), children: "Don't Save" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { secondary: true, onClick: () => blocker.reset?.(), children: "Cancel" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { "data-autofocus": true, onClick: handleSaveAndNavigate, children: "Save" })
        ] }),
        children: "You have unsaved changes. Do you want to save before leaving?"
      }
    )
  ] });
};
export {
  ProjectPanel
};
//# sourceMappingURL=ProjectPanel.js.map
