import {
  VscodeFormHelper,
  VscodeLabel,
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC } from "react";

import { GenerateConfigInput, ProjectConfigInput } from "../../../types/api-types";

import styles from "./tabs.module.css";

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
const REASONING_SUMMARY_OPTIONS = ["none", "concise", "detailed", "auto"] as const;
const REASONING_HISTORY_OPTIONS = ["none", "all", "last", "auto"] as const;

export interface ModelTabProps {
  title: string;
  config: Partial<ProjectConfigInput>;
  onChange: (updates: Partial<ProjectConfigInput>) => void;
}

// Filter out null/undefined values from an object
function filterNullValues<T extends Record<string, unknown>>(obj: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(obj).filter(([, v]) => v !== null && v !== undefined)
  ) as Partial<T>;
}

export const ModelTab: FC<ModelTabProps> = ({ config, onChange }) => {
  const generateConfig = config.generate_config ?? {};

  // Helper to update generate_config fields
  // Filter out null values before spreading to avoid polluting config with server defaults
  const updateGenerateConfig = (updates: Partial<GenerateConfigInput>) => {
    onChange({
      generate_config: {
        ...filterNullValues(generateConfig),
        ...updates,
      },
    });
  };

  // Parse model_args for display
  const modelArgsValue =
    typeof config.model_args === "object"
      ? JSON.stringify(config.model_args, null, 2)
      : (config.model_args ?? "");

  const handleModelArgsChange = (value: string) => {
    if (!value.trim()) {
      onChange({ model_args: null });
      return;
    }
    // If it looks like JSON, try to parse it
    if (value.trim().startsWith("{")) {
      try {
        const parsed = JSON.parse(value);
        onChange({ model_args: parsed });
      } catch {
        // Keep as string if invalid JSON - user may be typing
        onChange({ model_args: value });
      }
    } else {
      // Treat as file path
      onChange({ model_args: value });
    }
  };

  return (
    <div className={styles.tabContent}>
      {/* Default Model Section */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>Default Model</div>
        <div className={styles.row}>
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
      </div>

      {/* Connection Section */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>Connection</div>
        <div className={styles.row}>
          <div className={styles.field}>
            <VscodeLabel>Max Connections</VscodeLabel>
            <VscodeFormHelper>
              Maximum concurrent connections to Model API (defaults to
              max_transcripts)
            </VscodeFormHelper>
            <VscodeTextfield
              value={generateConfig.max_connections?.toString() ?? ""}
              onInput={(e) => {
                const val = (e.target as HTMLInputElement).value;
                const num = parseInt(val, 10);
                updateGenerateConfig({ max_connections: isNaN(num) ? null : num });
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
              value={generateConfig.attempt_timeout?.toString() ?? ""}
              onInput={(e) => {
                const val = (e.target as HTMLInputElement).value;
                const num = parseInt(val, 10);
                updateGenerateConfig({ attempt_timeout: isNaN(num) ? null : num });
              }}
              placeholder="No timeout"
              spellCheck={false}
            />
          </div>
        </div>
      </div>

      {/* Generation Section */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>Generation</div>
        <div className={styles.twoColumnGrid}>
          <div className={styles.field}>
            <VscodeLabel>Max Tokens</VscodeLabel>
            <VscodeFormHelper>
              Maximum tokens that can be generated in the completion
            </VscodeFormHelper>
            <VscodeTextfield
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
              value={generateConfig.frequency_penalty?.toString() ?? ""}
              onInput={(e) => {
                const val = (e.target as HTMLInputElement).value;
                const num = parseFloat(val);
                updateGenerateConfig({ frequency_penalty: isNaN(num) ? null : num });
              }}
              placeholder="0"
              spellCheck={false}
            />
          </div>

          <div className={styles.field}>
            <VscodeLabel>Presence Penalty</VscodeLabel>
            <VscodeFormHelper>
              Penalize new tokens based on presence (-2 to 2)
            </VscodeFormHelper>
            <VscodeTextfield
              value={generateConfig.presence_penalty?.toString() ?? ""}
              onInput={(e) => {
                const val = (e.target as HTMLInputElement).value;
                const num = parseFloat(val);
                updateGenerateConfig({ presence_penalty: isNaN(num) ? null : num });
              }}
              placeholder="0"
              spellCheck={false}
            />
          </div>

          <div className={styles.field}>
            <VscodeLabel>Seed</VscodeLabel>
            <VscodeFormHelper>Random seed for reproducibility</VscodeFormHelper>
            <VscodeTextfield
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
      </div>

      {/* Reasoning Section */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>Reasoning</div>
        <div className={styles.twoColumnGrid}>
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
              value={generateConfig.reasoning_tokens?.toString() ?? ""}
              onInput={(e) => {
                const val = (e.target as HTMLInputElement).value;
                const num = parseInt(val, 10);
                updateGenerateConfig({ reasoning_tokens: isNaN(num) ? null : num });
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
      </div>
    </div>
  );
};
