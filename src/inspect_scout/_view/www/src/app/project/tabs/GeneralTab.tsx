import {
  VscodeCheckbox,
  VscodeFormHelper,
  VscodeLabel,
  VscodeOption,
  VscodeSingleSelect,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC } from "react";

import { ProjectConfigInput } from "../../../types/api-types";

import styles from "./tabs.module.css";

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

export interface GeneralTabProps {
  title: string;
  config: Partial<ProjectConfigInput>;
  onChange: (updates: Partial<ProjectConfigInput>) => void;
}

export const GeneralTab: FC<GeneralTabProps> = ({ config, onChange }) => {
  // Parse tags from comma-separated string or array
  const tagsValue = Array.isArray(config.tags)
    ? config.tags.join(", ")
    : config.tags ?? "";

  // Parse metadata from object to JSON string
  const metadataValue = config.metadata
    ? JSON.stringify(config.metadata, null, 2)
    : "";

  // Handle shuffle which can be boolean | number | null
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

  return (
    <div className={styles.tabContent}>
      <div className={styles.twoColumnGrid}>
        {/* Column 1 */}
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

        {/* Column 2 */}
        <div className={styles.field}>
          <VscodeLabel>Limit</VscodeLabel>
          <VscodeFormHelper>
            Limit the number of transcripts processed per scanner
          </VscodeFormHelper>
          <VscodeTextfield
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

        <div className={styles.field}>
          <VscodeLabel>Scans</VscodeLabel>
          <VscodeFormHelper>
            Location to write scan results (filesystem or S3 bucket)
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
          <VscodeLabel>Max Transcripts</VscodeLabel>
          <VscodeFormHelper>
            Maximum number of transcripts to process concurrently (default: 25)
          </VscodeFormHelper>
          <VscodeTextfield
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
          <VscodeLabel>Metadata</VscodeLabel>
          <VscodeFormHelper>Metadata (key/value) to apply to scans</VscodeFormHelper>
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
          <VscodeLabel>Max Processes</VscodeLabel>
          <VscodeFormHelper>
            Maximum number of concurrent processes for multiprocessing (default:
            4)
          </VscodeFormHelper>
          <VscodeTextfield
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
                log_level: val
                  ? (val as (typeof LOG_LEVELS)[number])
                  : null,
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
    </div>
  );
};
