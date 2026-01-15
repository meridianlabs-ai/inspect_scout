import {
  VscodeCheckbox,
  VscodeFormHelper,
  VscodeLabel,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC, useCallback, useEffect, useState } from "react";

import {
  BatchConfig,
  CachePolicy,
  GenerateConfigInput,
  ProjectConfigInput,
} from "../../types/api-types";

import {
  KeyValueField,
  NumberField,
  SelectField,
  TextField,
} from "./components/FormFields";
import { useBatchConfig, useNestedConfig } from "./hooks/useNestedConfig";
import styles from "./ProjectPanel.module.css";

// Constants for select options
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

// Cache expiry validation: must be a number followed by M, H, D, or W
const CACHE_EXPIRY_PATTERN = /^\d+[MHDWmhdw]$/;

function validateCacheExpiry(value: string | null): string | null {
  if (!value) return null; // Empty is valid (will use default)
  if (CACHE_EXPIRY_PATTERN.test(value)) return null;
  return "Invalid format. Use a number followed by M, H, D, or W (e.g., 30M, 24H, 7D, 1W)";
}

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
  const updateGenerateConfig = useCallback(
    (updates: Partial<GenerateConfigInput>) => {
      const merged = {
        ...filterNullValues(generateConfig),
        ...updates,
      };

      // Filter out null values from the merged result
      const cleaned = filterNullValues(merged);

      // If no content remains, set generate_config to null
      const hasContent = Object.keys(cleaned).length > 0;

      onChange({
        generate_config: hasContent ? cleaned : null,
      });
    },
    [generateConfig, onChange]
  );

  // Cache config hook
  const cache = useNestedConfig<CachePolicy>(
    generateConfig.cache,
    useCallback(
      (value) => updateGenerateConfig({ cache: value }),
      [updateGenerateConfig]
    )
  );

  // Batch config hook
  const batch = useBatchConfig<BatchConfig>(
    generateConfig.batch,
    useCallback(
      (value) => updateGenerateConfig({ batch: value }),
      [updateGenerateConfig]
    )
  );

  // ===== General Section Helpers =====

  // Tags field - use local state to allow typing commas/spaces freely
  // but also update config on input so Ctrl+S saves correctly
  const [tagsText, setTagsText] = useState(() =>
    Array.isArray(config.tags) ? config.tags.join(", ") : (config.tags ?? "")
  );

  // Sync local state when config changes externally (e.g., after save)
  useEffect(() => {
    const configValue = Array.isArray(config.tags)
      ? config.tags.join(", ")
      : (config.tags ?? "");
    // Only sync if the parsed values differ (avoids cursor jump while typing)
    const currentParsed = tagsText
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    const configParsed = Array.isArray(config.tags) ? config.tags : [];
    if (JSON.stringify(currentParsed) !== JSON.stringify(configParsed)) {
      setTagsText(configValue);
    }
  }, [config.tags]);

  const handleTagsInput = (value: string) => {
    setTagsText(value);
    // Also update config immediately so Ctrl+S works
    const tags = value
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);
    onChange({ tags: tags.length > 0 ? tags : null });
  };

  const shuffleEnabled =
    config.shuffle !== null && config.shuffle !== undefined;
  const shuffleSeed =
    typeof config.shuffle === "number" ? config.shuffle : null;

  const handleShuffleToggle = (enabled: boolean) => {
    onChange({ shuffle: enabled ? true : null });
  };

  const handleShuffleSeedChange = (value: string) => {
    const num = parseInt(value, 10);
    onChange({ shuffle: isNaN(num) ? true : num });
  };

  return (
    <>
      {/* ===== LOCATIONS SECTION ===== */}
      <div id="locations" className={styles.section}>
        <div className={styles.sectionHeader}>Locations</div>

        <TextField
          label="Transcripts"
          helper="Transcripts to scan (filesystem, S3 bucket, etc.)"
          value={config.transcripts}
          onChange={(v) => onChange({ transcripts: v })}
          placeholder="Path to transcripts"
        />

        <TextField
          label="Scans"
          helper="Location to write scan results (filesystem, S3 bucket, etc.)"
          value={config.scans}
          onChange={(v) => onChange({ scans: v })}
          placeholder="Path to scans output"
        />
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
                filter: (e.target as HTMLInputElement).value || undefined,
              })
            }
            placeholder="Filter expression"
            spellCheck={false}
            autocomplete="off"
          />
        </div>

        <NumberField
          label="Limit"
          helper="Limit the number of transcripts processed per scanner"
          value={config.limit}
          onChange={(v) => onChange({ limit: v })}
          placeholder="No limit"
        />

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
                autocomplete="off"
              />
            )}
          </div>
        </div>
      </div>

      {/* ===== CONCURRENCY SECTION ===== */}
      <div id="concurrency" className={styles.section}>
        <div className={styles.sectionHeader}>Concurrency</div>

        <NumberField
          label="Max Transcripts"
          helper="Maximum number of transcripts to process concurrently (default: 25)"
          value={config.max_transcripts}
          onChange={(v) => onChange({ max_transcripts: v })}
          placeholder="25"
        />

        <NumberField
          label="Max Processes"
          helper="Maximum number of concurrent processes for multiprocessing (default: 4)"
          value={config.max_processes}
          onChange={(v) => onChange({ max_processes: v })}
          placeholder="4"
        />
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
            value={tagsText}
            onInput={(e) =>
              handleTagsInput((e.target as HTMLInputElement).value)
            }
            placeholder="tag1, tag2, tag3"
            spellCheck={false}
            autocomplete="off"
          />
        </div>

        <KeyValueField
          label="Metadata"
          helper="Key/value pairs to apply to scans (one per line)"
          value={config.metadata}
          onChange={(v) =>
            onChange({ metadata: v as Record<string, string> | null })
          }
          placeholder="key=value"
        />

        <SelectField
          label="Log Level"
          helper="Level for logging to the console (default: warning)"
          value={config.log_level}
          options={LOG_LEVELS}
          onChange={(v) => onChange({ log_level: v })}
          defaultLabel="Default (warning)"
        />
      </div>

      {/* ===== MODEL SECTION ===== */}
      <div id="model" className={styles.section}>
        <div className={styles.sectionHeader}>Model</div>
        <VscodeFormHelper style={{ marginBottom: "-5px" }}>
          Model configuration specifies the defaults for the model used by the
          LLM scanner, as well as the model returned by calls to{" "}
          <code>get_model()</code> in custom scanners.
        </VscodeFormHelper>

        <TextField
          label="Model"
          helper="Default model for LLM scanning (scanners can override as required)"
          value={config.model}
          onChange={(v) => onChange({ model: v })}
          placeholder="e.g., openai/gpt-5"
        />

        <TextField
          label="Model Base URL"
          helper="Base URL for communicating with the model API"
          value={config.model_base_url}
          onChange={(v) => onChange({ model_base_url: v })}
          placeholder="API base URL"
        />

        <KeyValueField
          label="Model Args"
          helper="Model creation args (key=value per line, or path to config file)"
          value={config.model_args}
          onChange={(v) => onChange({ model_args: v })}
          placeholder="key=value or /path/to/config.yaml"
        />
      </div>

      {/* ===== CONNECTION SECTION ===== */}
      <div id="connection" className={styles.section}>
        <div className={styles.sectionHeader}>Connection</div>

        <NumberField
          label="Max Connections"
          helper="Maximum concurrent connections to Model API (defaults to max_transcripts)"
          value={generateConfig.max_connections}
          onChange={(v) => updateGenerateConfig({ max_connections: v })}
          placeholder="Default"
        />

        <NumberField
          label="Max Retries"
          helper="Maximum number of times to retry request (defaults to unlimited)"
          value={generateConfig.max_retries}
          onChange={(v) => updateGenerateConfig({ max_retries: v })}
          placeholder="Unlimited"
        />

        <NumberField
          label="Timeout"
          helper="Timeout (seconds) for entire request including retries"
          value={generateConfig.timeout}
          onChange={(v) => updateGenerateConfig({ timeout: v })}
          placeholder="No timeout"
        />

        <NumberField
          label="Attempt Timeout"
          helper="Timeout (seconds) for any given attempt before retrying"
          value={generateConfig.attempt_timeout}
          onChange={(v) => updateGenerateConfig({ attempt_timeout: v })}
          placeholder="No timeout"
        />
      </div>

      {/* ===== GENERATION SECTION ===== */}
      <div id="generation" className={styles.section}>
        <div className={styles.sectionHeader}>Generation</div>

        <NumberField
          label="Max Tokens"
          helper="Maximum tokens that can be generated in the completion"
          value={generateConfig.max_tokens}
          onChange={(v) => updateGenerateConfig({ max_tokens: v })}
          placeholder="Model default"
        />

        <NumberField
          label="Temperature"
          helper="Sampling temperature (0-2). Higher = more random"
          value={generateConfig.temperature}
          onChange={(v) => updateGenerateConfig({ temperature: v })}
          placeholder="Model default"
          step={0.1}
        />

        <NumberField
          label="Top P"
          helper="Nucleus sampling probability mass"
          value={generateConfig.top_p}
          onChange={(v) => updateGenerateConfig({ top_p: v })}
          placeholder="Model default"
          step={0.1}
        />

        <NumberField
          label="Top K"
          helper="Sample from top K most likely next tokens"
          value={generateConfig.top_k}
          onChange={(v) => updateGenerateConfig({ top_k: v })}
          placeholder="Model default"
        />

        <NumberField
          label="Frequency Penalty"
          helper="Penalize tokens based on frequency (-2 to 2)"
          value={generateConfig.frequency_penalty}
          onChange={(v) => updateGenerateConfig({ frequency_penalty: v })}
          placeholder="Model default"
          step={0.1}
        />

        <NumberField
          label="Presence Penalty"
          helper="Penalize new tokens based on presence (-2 to 2)"
          value={generateConfig.presence_penalty}
          onChange={(v) => updateGenerateConfig({ presence_penalty: v })}
          placeholder="Model default"
          step={0.1}
        />

        <NumberField
          label="Seed"
          helper="Random seed for reproducibility"
          value={generateConfig.seed}
          onChange={(v) => updateGenerateConfig({ seed: v })}
          placeholder="Random"
        />

        <SelectField
          label="Verbosity"
          helper="Response verbosity (GPT 5.x models only)"
          value={generateConfig.verbosity}
          options={VERBOSITY_OPTIONS}
          onChange={(v) => updateGenerateConfig({ verbosity: v })}
        />

        <SelectField
          label="Effort"
          helper="Response thoroughness (Claude Opus 4.5 only)"
          value={generateConfig.effort}
          options={EFFORT_OPTIONS}
          onChange={(v) => updateGenerateConfig({ effort: v })}
        />
      </div>

      {/* ===== REASONING SECTION ===== */}
      <div id="reasoning" className={styles.section}>
        <div className={styles.sectionHeader}>Reasoning</div>

        <SelectField
          label="Reasoning Effort"
          helper="Constrains effort on reasoning (varies by provider/model)"
          value={generateConfig.reasoning_effort}
          options={REASONING_EFFORT_OPTIONS}
          onChange={(v) => updateGenerateConfig({ reasoning_effort: v })}
        />

        <NumberField
          label="Reasoning Tokens"
          helper="Maximum tokens for reasoning (Anthropic/Google only)"
          value={generateConfig.reasoning_tokens}
          onChange={(v) => updateGenerateConfig({ reasoning_tokens: v })}
          placeholder="Model default"
        />

        <SelectField
          label="Reasoning Summary"
          helper="Summary of reasoning steps (OpenAI reasoning models only)"
          value={generateConfig.reasoning_summary}
          options={REASONING_SUMMARY_OPTIONS}
          onChange={(v) => updateGenerateConfig({ reasoning_summary: v })}
        />

        <SelectField
          label="Reasoning History"
          helper="Include reasoning in chat message history"
          value={generateConfig.reasoning_history}
          options={REASONING_HISTORY_OPTIONS}
          onChange={(v) => updateGenerateConfig({ reasoning_history: v })}
        />
      </div>

      {/* ===== CACHE SECTION ===== */}
      <div id="cache" className={styles.section}>
        <div className={styles.sectionHeader}>Cache</div>

        <div className={styles.field}>
          <VscodeCheckbox
            checked={cache.enabled}
            onChange={(e) =>
              cache.setEnabled((e.target as HTMLInputElement).checked)
            }
          >
            Enable Caching
          </VscodeCheckbox>
          <VscodeFormHelper>
            Cache model responses to improve performance and reduce API costs
          </VscodeFormHelper>
        </div>

        <TextField
          label="Expiry"
          helper="Cache expiration. Use a number followed by: M (minutes), H (hours), D (days), or W (weeks)."
          value={cache.config.expiry}
          onChange={(v) => cache.updateConfig({ expiry: v })}
          placeholder="1W (default)"
          disabled={!cache.enabled}
          validate={validateCacheExpiry}
        />

        <div className={styles.field}>
          <VscodeLabel>Per Epoch</VscodeLabel>
          <VscodeFormHelper>
            Maintain separate cache entries per epoch
          </VscodeFormHelper>
          <VscodeCheckbox
            checked={cache.config.per_epoch ?? true}
            disabled={!cache.enabled}
            onChange={(e) =>
              cache.updateConfig({
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
            checked={batch.enabled}
            onChange={(e) =>
              batch.setEnabled((e.target as HTMLInputElement).checked)
            }
          >
            Enable Batch Processing
          </VscodeCheckbox>
          <VscodeFormHelper>
            Process multiple requests in batches for improved throughput
          </VscodeFormHelper>
        </div>

        <NumberField
          label="Batch Size"
          helper="Number of requests per batch"
          value={batch.currentBatchSize}
          onChange={(v) => batch.updateConfig({ size: v })}
          placeholder="Default"
          disabled={!batch.enabled}
        />

        <NumberField
          label="Max Size"
          helper="Maximum batch size allowed"
          value={batch.config.max_size}
          onChange={(v) => batch.updateConfig({ max_size: v })}
          placeholder="No limit"
          disabled={!batch.enabled}
        />

        <NumberField
          label="Max Batches"
          helper="Maximum number of batches to process"
          value={batch.config.max_batches}
          onChange={(v) => batch.updateConfig({ max_batches: v })}
          placeholder="No limit"
          disabled={!batch.enabled}
        />

        <NumberField
          label="Send Delay"
          helper="Delay (seconds) before sending batch"
          value={batch.config.send_delay}
          onChange={(v) => batch.updateConfig({ send_delay: v })}
          placeholder="0"
          disabled={!batch.enabled}
          step={0.1}
        />

        <NumberField
          label="Tick"
          helper="Tick interval (seconds) for batch processing"
          value={batch.config.tick}
          onChange={(v) => batch.updateConfig({ tick: v })}
          placeholder="Default"
          disabled={!batch.enabled}
          step={0.1}
        />

        <NumberField
          label="Max Check Failures"
          helper="Maximum consecutive check failures before abort"
          value={batch.config.max_consecutive_check_failures}
          onChange={(v) =>
            batch.updateConfig({ max_consecutive_check_failures: v })
          }
          placeholder="No limit"
          disabled={!batch.enabled}
        />
      </div>
    </>
  );
};
