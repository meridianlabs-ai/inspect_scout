import {
  VscodeCheckbox,
  VscodeFormHelper,
  VscodeLabel,
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC } from "react";

import {
  BatchConfig,
  CachePolicy,
  GenerateConfigInput,
  ProjectConfigInput,
} from "../../types/api-types";

import styles from "./ProjectPanel.module.css";

// Constants
const LOG_LEVELS = [
  "debug",
  "http",
  "sandbox",
  "info",
  "warning",
  "error",
  "critical",
  "notset",
] as const;

const VERBOSITY_OPTIONS = ["low", "medium", "high"] as const;
const EFFORT_OPTIONS = ["low", "medium", "high"] as const;
const REASONING_EFFORT_OPTIONS = [
  "none",
  "minimal",
  "low",
  "medium",
  "high",
  "xhigh",
] as const;
const REASONING_SUMMARY_OPTIONS = [
  "none",
  "concise",
  "detailed",
  "auto",
] as const;
const REASONING_HISTORY_OPTIONS = ["none", "all", "last", "auto"] as const;

export interface SettingsContentProps {
  config: Partial<ProjectConfigInput>;
  onChange: (updates: Partial<ProjectConfigInput>) => void;
}

// Filter out null/undefined values from an object
function filterNullValues<T extends Record<string, unknown>>(
  obj: T
): Partial<T> {
  return Object.fromEntries(
    Object.entries(obj).filter(([, v]) => v !== null && v !== undefined)
  ) as Partial<T>;
}

export const SettingsContent: FC<SettingsContentProps> = ({
  config,
  onChange,
}) => {
  const generateConfig = config.generate_config ?? {};

  // Helper to update generate_config fields
  const updateGenerateConfig = (updates: Partial<GenerateConfigInput>) => {
    onChange({
      generate_config: {
        ...filterNullValues(generateConfig),
        ...updates,
      },
    });
  };

  // ===== General Section Helpers =====
  const tagsValue = Array.isArray(config.tags)
    ? config.tags.join(", ")
    : (config.tags ?? "");

  const metadataValue = config.metadata
    ? JSON.stringify(config.metadata, null, 2)
    : "";

  const shuffleEnabled =
    config.shuffle !== null && config.shuffle !== undefined;
  const shuffleSeed =
    typeof config.shuffle === "number" ? config.shuffle : null;

  const handleTagsChange = (value: string) => {
    const tags = value
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    onChange({ tags: tags.length > 0 ? tags : null });
  };

  const handleMetadataChange = (value: string) => {
    if (!value.trim()) {
      onChange({ metadata: null });
      return;
    }
    try {
      const parsed = JSON.parse(value);
      onChange({ metadata: parsed });
    } catch {
      // Don't update if invalid JSON - user is still typing
    }
  };

  const handleShuffleToggle = (enabled: boolean) => {
    onChange({ shuffle: enabled ? true : null });
  };

  const handleShuffleSeedChange = (value: string) => {
    const num = parseInt(value, 10);
    onChange({ shuffle: isNaN(num) ? true : num });
  };

  // ===== Model Section Helpers =====
  const modelArgsValue =
    typeof config.model_args === "object"
      ? JSON.stringify(config.model_args, null, 2)
      : (config.model_args ?? "");

  const handleModelArgsChange = (value: string) => {
    if (!value.trim()) {
      onChange({ model_args: null });
      return;
    }
    if (value.trim().startsWith("{")) {
      try {
        const parsed = JSON.parse(value);
        onChange({ model_args: parsed });
      } catch {
        onChange({ model_args: value });
      }
    } else {
      onChange({ model_args: value });
    }
  };

  // ===== Cache Section Helpers =====
  const cache = generateConfig.cache;
  const cacheEnabled = cache !== null && cache !== undefined && cache !== false;
  const cachePolicy: Partial<CachePolicy> =
    typeof cache === "object" && cache !== null ? cache : {};

  const handleCacheEnableChange = (enabled: boolean) => {
    if (enabled) {
      updateGenerateConfig({ cache: true });
    } else {
      updateGenerateConfig({ cache: null });
    }
  };

  const updateCachePolicy = (updates: Partial<CachePolicy>) => {
    const existingConfig =
      typeof cache === "object" && cache !== null
        ? filterNullValues(cache)
        : {};
    updateGenerateConfig({
      cache: {
        ...existingConfig,
        ...updates,
      } as CachePolicy,
    });
  };

  // ===== Batch Section Helpers =====
  const batch = generateConfig.batch;
  const batchEnabled = batch !== null && batch !== undefined && batch !== false;
  const batchConfig: Partial<BatchConfig> =
    typeof batch === "object" && batch !== null ? batch : {};
  const simpleBatchSize = typeof batch === "number" ? batch : null;

  const handleBatchEnableChange = (enabled: boolean) => {
    if (enabled) {
      updateGenerateConfig({ batch: true });
    } else {
      updateGenerateConfig({ batch: null });
    }
  };

  const updateBatchConfig = (updates: Partial<BatchConfig>) => {
    const existingConfig =
      typeof batch === "object" && batch !== null
        ? filterNullValues(batch)
        : {};
    const size = typeof batch === "number" ? batch : existingConfig.size;
    updateGenerateConfig({
      batch: {
        ...(size !== undefined ? { size } : {}),
        ...existingConfig,
        ...updates,
      } as BatchConfig,
    });
  };

  const currentBatchSize =
    typeof batch === "object" ? batchConfig.size : simpleBatchSize;

  return (
    <>
      {/* ===== LOCATIONS SECTION ===== */}
      <div id="locations" className={styles.section}>
        <div className={styles.sectionHeader}>Locations</div>

        <div className={styles.field}>
          <VscodeLabel>Transcripts</VscodeLabel>
          <VscodeFormHelper>
            Transcripts to scan (filesystem, S3 bucket, etc.)
          </VscodeFormHelper>
          <VscodeTextfield
            value={config.transcripts ?? ""}
            onInput={(e) =>
              onChange({
                transcripts: (e.target as HTMLInputElement).value || null,
              })
            }
            placeholder="Path to transcripts"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Scans</VscodeLabel>
          <VscodeFormHelper>
            Location to write scan results (filesystem, S3 bucket, etc.)
          </VscodeFormHelper>
          <VscodeTextfield
            value={config.scans ?? ""}
            onInput={(e) =>
              onChange({
                scans: (e.target as HTMLInputElement).value || null,
              })
            }
            placeholder="Path to scans output"
            spellCheck={false}
          />
        </div>
      </div>

      {/* ===== FILTERING SECTION ===== */}
      <div id="filtering" className={styles.section}>
        <div className={styles.sectionHeader}>Filtering</div>

        <div className={styles.field}>
          <VscodeLabel>Filter</VscodeLabel>
          <VscodeFormHelper>
            SQL WHERE clause(s) for filtering transcripts
          </VscodeFormHelper>
          <VscodeTextfield
            value={
              Array.isArray(config.filter)
                ? config.filter.join("; ")
                : (config.filter ?? "")
            }
            onInput={(e) =>
              onChange({
                filter: (e.target as HTMLInputElement).value || "",
              })
            }
            placeholder="Filter expression"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Limit</VscodeLabel>
          <VscodeFormHelper>
            Limit the number of transcripts processed per scanner
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={config.limit?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              onChange({ limit: isNaN(num) ? null : num });
            }}
            placeholder="No limit"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Shuffle</VscodeLabel>
          <VscodeFormHelper>
            Shuffle the order of transcripts (optionally specify a seed)
          </VscodeFormHelper>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <VscodeCheckbox
              checked={shuffleEnabled}
              onChange={(e) =>
                handleShuffleToggle((e.target as HTMLInputElement).checked)
              }
            >
              Enabled
            </VscodeCheckbox>
            {shuffleEnabled && (
              <VscodeTextfield
                type="number"
                value={shuffleSeed?.toString() ?? ""}
                onInput={(e) =>
                  handleShuffleSeedChange((e.target as HTMLInputElement).value)
                }
                placeholder="Seed (optional)"
                style={{ width: "120px" }}
                spellCheck={false}
              />
            )}
          </div>
        </div>
      </div>

      {/* ===== CONCURRENCY SECTION ===== */}
      <div id="concurrency" className={styles.section}>
        <div className={styles.sectionHeader}>Concurrency</div>

        <div className={styles.field}>
          <VscodeLabel>Max Transcripts</VscodeLabel>
          <VscodeFormHelper>
            Maximum number of transcripts to process concurrently (default: 25)
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={config.max_transcripts?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              onChange({ max_transcripts: isNaN(num) ? null : num });
            }}
            placeholder="25"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Max Processes</VscodeLabel>
          <VscodeFormHelper>
            Maximum number of concurrent processes for multiprocessing (default:
            4)
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={config.max_processes?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              onChange({ max_processes: isNaN(num) ? null : num });
            }}
            placeholder="4"
            spellCheck={false}
          />
        </div>
      </div>

      {/* ===== MISCELLANEOUS SECTION ===== */}
      <div id="miscellaneous" className={styles.section}>
        <div className={styles.sectionHeader}>Miscellaneous</div>

        <div className={styles.field}>
          <VscodeLabel>Tags</VscodeLabel>
          <VscodeFormHelper>
            One or more tags to apply to scans (comma-separated)
          </VscodeFormHelper>
          <VscodeTextfield
            value={tagsValue}
            onInput={(e) =>
              handleTagsChange((e.target as HTMLInputElement).value)
            }
            placeholder="tag1, tag2, tag3"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Metadata</VscodeLabel>
          <VscodeFormHelper>
            Metadata (key/value) to apply to scans
          </VscodeFormHelper>
          <VscodeTextfield
            value={metadataValue}
            onInput={(e) =>
              handleMetadataChange((e.target as HTMLInputElement).value)
            }
            placeholder='{"key": "value"}'
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Log Level</VscodeLabel>
          <VscodeFormHelper>
            Level for logging to the console (default: warning)
          </VscodeFormHelper>
          <VscodeSingleSelect
            value={config.log_level ?? ""}
            onChange={(e) => {
              const val = (e.target as HTMLSelectElement).value;
              onChange({
                log_level: val ? (val as (typeof LOG_LEVELS)[number]) : null,
              });
            }}
          >
            <VscodeOption value="">Default (warning)</VscodeOption>
            {LOG_LEVELS.map((level) => (
              <VscodeOption key={level} value={level}>
                {level}
              </VscodeOption>
            ))}
          </VscodeSingleSelect>
        </div>
      </div>

      {/* ===== MODEL SECTION ===== */}
      <div id="model" className={styles.section}>
        <div className={styles.sectionHeader}>Model</div>
        <VscodeFormHelper>
          Model configuration affects the default model used by the LLM scanner,
          as well as the model returned by calls to <code>get_model()</code> in
          custom scanners.
        </VscodeFormHelper>
        <div className={styles.field}>
          <VscodeLabel>Model</VscodeLabel>
          <VscodeFormHelper>
            Default model for LLM scanning (scanners can override as required)
          </VscodeFormHelper>
          <VscodeTextfield
            value={config.model ?? ""}
            onInput={(e) =>
              onChange({
                model: (e.target as HTMLInputElement).value || null,
              })
            }
            placeholder="e.g., openai/gpt-4o"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Model Base URL</VscodeLabel>
          <VscodeFormHelper>
            Base URL for communicating with the model API
          </VscodeFormHelper>
          <VscodeTextfield
            value={config.model_base_url ?? ""}
            onInput={(e) =>
              onChange({
                model_base_url: (e.target as HTMLInputElement).value || null,
              })
            }
            placeholder="API base URL"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Model Args</VscodeLabel>
          <VscodeFormHelper>
            Model creation args (JSON object or path to config file)
          </VscodeFormHelper>
          <VscodeTextfield
            value={modelArgsValue}
            onInput={(e) =>
              handleModelArgsChange((e.target as HTMLInputElement).value)
            }
            placeholder='{"key": "value"} or /path/to/config.yaml'
            spellCheck={false}
          />
        </div>
      </div>

      {/* ===== CONNECTION SECTION ===== */}
      <div id="connection" className={styles.section}>
        <div className={styles.sectionHeader}>Connection</div>

        <div className={styles.field}>
          <VscodeLabel>Max Connections</VscodeLabel>
          <VscodeFormHelper>
            Maximum concurrent connections to Model API (defaults to
            max_transcripts)
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={generateConfig.max_connections?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateGenerateConfig({
                max_connections: isNaN(num) ? null : num,
              });
            }}
            placeholder="Default"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Max Retries</VscodeLabel>
          <VscodeFormHelper>
            Maximum number of times to retry request (defaults to unlimited)
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={generateConfig.max_retries?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateGenerateConfig({ max_retries: isNaN(num) ? null : num });
            }}
            placeholder="Unlimited"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Timeout</VscodeLabel>
          <VscodeFormHelper>
            Timeout (seconds) for entire request including retries
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={generateConfig.timeout?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateGenerateConfig({ timeout: isNaN(num) ? null : num });
            }}
            placeholder="No timeout"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Attempt Timeout</VscodeLabel>
          <VscodeFormHelper>
            Timeout (seconds) for any given attempt before retrying
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={generateConfig.attempt_timeout?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateGenerateConfig({
                attempt_timeout: isNaN(num) ? null : num,
              });
            }}
            placeholder="No timeout"
            spellCheck={false}
          />
        </div>
      </div>

      {/* ===== GENERATION SECTION ===== */}
      <div id="generation" className={styles.section}>
        <div className={styles.sectionHeader}>Generation</div>

        <div className={styles.field}>
          <VscodeLabel>Max Tokens</VscodeLabel>
          <VscodeFormHelper>
            Maximum tokens that can be generated in the completion
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={generateConfig.max_tokens?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateGenerateConfig({ max_tokens: isNaN(num) ? null : num });
            }}
            placeholder="Model default"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Temperature</VscodeLabel>
          <VscodeFormHelper>
            Sampling temperature (0-2). Higher = more random
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            step={0.1}
            value={generateConfig.temperature?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseFloat(val);
              updateGenerateConfig({ temperature: isNaN(num) ? null : num });
            }}
            placeholder="Model default"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Top P</VscodeLabel>
          <VscodeFormHelper>Nucleus sampling probability mass</VscodeFormHelper>
          <VscodeTextfield
            type="number"
            step={0.1}
            value={generateConfig.top_p?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseFloat(val);
              updateGenerateConfig({ top_p: isNaN(num) ? null : num });
            }}
            placeholder="Model default"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Top K</VscodeLabel>
          <VscodeFormHelper>
            Sample from top K most likely next tokens
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={generateConfig.top_k?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateGenerateConfig({ top_k: isNaN(num) ? null : num });
            }}
            placeholder="Model default"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Frequency Penalty</VscodeLabel>
          <VscodeFormHelper>
            Penalize tokens based on frequency (-2 to 2)
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            step={0.1}
            value={generateConfig.frequency_penalty?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseFloat(val);
              updateGenerateConfig({
                frequency_penalty: isNaN(num) ? null : num,
              });
            }}
            placeholder="Model default"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Presence Penalty</VscodeLabel>
          <VscodeFormHelper>
            Penalize new tokens based on presence (-2 to 2)
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            step={0.1}
            value={generateConfig.presence_penalty?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseFloat(val);
              updateGenerateConfig({
                presence_penalty: isNaN(num) ? null : num,
              });
            }}
            placeholder="Model default"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Seed</VscodeLabel>
          <VscodeFormHelper>Random seed for reproducibility</VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={generateConfig.seed?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateGenerateConfig({ seed: isNaN(num) ? null : num });
            }}
            placeholder="Random"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Verbosity</VscodeLabel>
          <VscodeFormHelper>
            Response verbosity (GPT 5.x models only)
          </VscodeFormHelper>
          <VscodeSingleSelect
            value={generateConfig.verbosity ?? ""}
            onChange={(e) => {
              const val = (e.target as HTMLSelectElement).value;
              updateGenerateConfig({
                verbosity: val
                  ? (val as (typeof VERBOSITY_OPTIONS)[number])
                  : null,
              });
            }}
          >
            <VscodeOption value="">Default</VscodeOption>
            {VERBOSITY_OPTIONS.map((opt) => (
              <VscodeOption key={opt} value={opt}>
                {opt}
              </VscodeOption>
            ))}
          </VscodeSingleSelect>
        </div>

        <div className={styles.field}>
          <VscodeLabel>Effort</VscodeLabel>
          <VscodeFormHelper>
            Response thoroughness (Claude Opus 4.5 only)
          </VscodeFormHelper>
          <VscodeSingleSelect
            value={generateConfig.effort ?? ""}
            onChange={(e) => {
              const val = (e.target as HTMLSelectElement).value;
              updateGenerateConfig({
                effort: val ? (val as (typeof EFFORT_OPTIONS)[number]) : null,
              });
            }}
          >
            <VscodeOption value="">Default</VscodeOption>
            {EFFORT_OPTIONS.map((opt) => (
              <VscodeOption key={opt} value={opt}>
                {opt}
              </VscodeOption>
            ))}
          </VscodeSingleSelect>
        </div>
      </div>

      {/* ===== REASONING SECTION ===== */}
      <div id="reasoning" className={styles.section}>
        <div className={styles.sectionHeader}>Reasoning</div>

        <div className={styles.field}>
          <VscodeLabel>Reasoning Effort</VscodeLabel>
          <VscodeFormHelper>
            Constrains effort on reasoning (varies by provider/model)
          </VscodeFormHelper>
          <VscodeSingleSelect
            value={generateConfig.reasoning_effort ?? ""}
            onChange={(e) => {
              const val = (e.target as HTMLSelectElement).value;
              updateGenerateConfig({
                reasoning_effort: val
                  ? (val as (typeof REASONING_EFFORT_OPTIONS)[number])
                  : null,
              });
            }}
          >
            <VscodeOption value="">Default</VscodeOption>
            {REASONING_EFFORT_OPTIONS.map((opt) => (
              <VscodeOption key={opt} value={opt}>
                {opt}
              </VscodeOption>
            ))}
          </VscodeSingleSelect>
        </div>

        <div className={styles.field}>
          <VscodeLabel>Reasoning Tokens</VscodeLabel>
          <VscodeFormHelper>
            Maximum tokens for reasoning (Anthropic/Google only)
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={generateConfig.reasoning_tokens?.toString() ?? ""}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateGenerateConfig({
                reasoning_tokens: isNaN(num) ? null : num,
              });
            }}
            placeholder="Model default"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Reasoning Summary</VscodeLabel>
          <VscodeFormHelper>
            Summary of reasoning steps (OpenAI reasoning models only)
          </VscodeFormHelper>
          <VscodeSingleSelect
            value={generateConfig.reasoning_summary ?? ""}
            onChange={(e) => {
              const val = (e.target as HTMLSelectElement).value;
              updateGenerateConfig({
                reasoning_summary: val
                  ? (val as (typeof REASONING_SUMMARY_OPTIONS)[number])
                  : null,
              });
            }}
          >
            <VscodeOption value="">Default</VscodeOption>
            {REASONING_SUMMARY_OPTIONS.map((opt) => (
              <VscodeOption key={opt} value={opt}>
                {opt}
              </VscodeOption>
            ))}
          </VscodeSingleSelect>
        </div>

        <div className={styles.field}>
          <VscodeLabel>Reasoning History</VscodeLabel>
          <VscodeFormHelper>
            Include reasoning in chat message history
          </VscodeFormHelper>
          <VscodeSingleSelect
            value={generateConfig.reasoning_history ?? ""}
            onChange={(e) => {
              const val = (e.target as HTMLSelectElement).value;
              updateGenerateConfig({
                reasoning_history: val
                  ? (val as (typeof REASONING_HISTORY_OPTIONS)[number])
                  : null,
              });
            }}
          >
            <VscodeOption value="">Default</VscodeOption>
            {REASONING_HISTORY_OPTIONS.map((opt) => (
              <VscodeOption key={opt} value={opt}>
                {opt}
              </VscodeOption>
            ))}
          </VscodeSingleSelect>
        </div>
      </div>

      {/* ===== CACHE SECTION ===== */}
      <div id="cache" className={styles.section}>
        <div className={styles.sectionHeader}>Cache</div>

        <div className={styles.field}>
          <VscodeCheckbox
            checked={cacheEnabled}
            onChange={(e) =>
              handleCacheEnableChange((e.target as HTMLInputElement).checked)
            }
          >
            Enable Caching
          </VscodeCheckbox>
          <VscodeFormHelper>
            Cache model responses to improve performance and reduce API costs
          </VscodeFormHelper>
        </div>

        <div className={styles.field}>
          <VscodeLabel>Expiry</VscodeLabel>
          <VscodeFormHelper>
            Cache expiration duration (e.g., "1W" for one week, "1D" for one
            day)
          </VscodeFormHelper>
          <VscodeTextfield
            value={cachePolicy.expiry ?? "1W"}
            disabled={!cacheEnabled}
            onInput={(e) =>
              updateCachePolicy({
                expiry: (e.target as HTMLInputElement).value || null,
              })
            }
            placeholder="1W"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Per Epoch</VscodeLabel>
          <VscodeFormHelper>
            Maintain separate cache entries per epoch
          </VscodeFormHelper>
          <VscodeCheckbox
            checked={cachePolicy.per_epoch ?? true}
            disabled={!cacheEnabled}
            onChange={(e) =>
              updateCachePolicy({
                per_epoch: (e.target as HTMLInputElement).checked,
              })
            }
          >
            Enabled
          </VscodeCheckbox>
        </div>
      </div>

      {/* ===== BATCH SECTION ===== */}
      <div id="batch" className={styles.section}>
        <div className={styles.sectionHeader}>Batch</div>

        <div className={styles.field}>
          <VscodeCheckbox
            checked={batchEnabled}
            onChange={(e) =>
              handleBatchEnableChange((e.target as HTMLInputElement).checked)
            }
          >
            Enable Batch Processing
          </VscodeCheckbox>
          <VscodeFormHelper>
            Process multiple requests in batches for improved throughput
          </VscodeFormHelper>
        </div>

        <div className={styles.field}>
          <VscodeLabel>Batch Size</VscodeLabel>
          <VscodeFormHelper>Number of requests per batch</VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={currentBatchSize?.toString() ?? ""}
            disabled={!batchEnabled}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateBatchConfig({ size: isNaN(num) ? null : num });
            }}
            placeholder="Default"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Max Size</VscodeLabel>
          <VscodeFormHelper>Maximum batch size allowed</VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={batchConfig.max_size?.toString() ?? ""}
            disabled={!batchEnabled}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateBatchConfig({ max_size: isNaN(num) ? null : num });
            }}
            placeholder="No limit"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Max Batches</VscodeLabel>
          <VscodeFormHelper>
            Maximum number of batches to process
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={batchConfig.max_batches?.toString() ?? ""}
            disabled={!batchEnabled}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateBatchConfig({ max_batches: isNaN(num) ? null : num });
            }}
            placeholder="No limit"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Send Delay</VscodeLabel>
          <VscodeFormHelper>
            Delay (seconds) before sending batch
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            step={0.1}
            value={batchConfig.send_delay?.toString() ?? ""}
            disabled={!batchEnabled}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseFloat(val);
              updateBatchConfig({ send_delay: isNaN(num) ? null : num });
            }}
            placeholder="0"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Tick</VscodeLabel>
          <VscodeFormHelper>
            Tick interval (seconds) for batch processing
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            step={0.1}
            value={batchConfig.tick?.toString() ?? ""}
            disabled={!batchEnabled}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseFloat(val);
              updateBatchConfig({ tick: isNaN(num) ? null : num });
            }}
            placeholder="Default"
            spellCheck={false}
          />
        </div>

        <div className={styles.field}>
          <VscodeLabel>Max Check Failures</VscodeLabel>
          <VscodeFormHelper>
            Maximum consecutive check failures before abort
          </VscodeFormHelper>
          <VscodeTextfield
            type="number"
            value={batchConfig.max_consecutive_check_failures?.toString() ?? ""}
            disabled={!batchEnabled}
            onInput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              const num = parseInt(val, 10);
              updateBatchConfig({
                max_consecutive_check_failures: isNaN(num) ? null : num,
              });
            }}
            placeholder="No limit"
            spellCheck={false}
          />
        </div>
      </div>
    </>
  );
};
