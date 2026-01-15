import {
  VscodeCheckbox,
  VscodeFormHelper,
  VscodeLabel,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC } from "react";

import {
  BatchConfig,
  GenerateConfigInput,
  ProjectConfigInput,
} from "../../../types/api-types";

import styles from "./tabs.module.css";

export interface BatchTabProps {
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

export const BatchTab: FC<BatchTabProps> = ({ config, onChange }) => {
  const generateConfig = config.generate_config ?? {};
  const batch = generateConfig.batch;

  // Determine batch state
  const isEnabled = batch !== null && batch !== undefined && batch !== false;
  const batchConfig: Partial<BatchConfig> =
    typeof batch === "object" && batch !== null ? batch : {};
  const simpleBatchSize = typeof batch === "number" ? batch : null;

  // Helper to update generate_config
  // Filter out null values before spreading to avoid polluting config with server defaults
  const updateGenerateConfig = (updates: Partial<GenerateConfigInput>) => {
    onChange({
      generate_config: {
        ...filterNullValues(generateConfig),
        ...updates,
      },
    });
  };

  // Enable/disable batch
  const handleEnableChange = (enabled: boolean) => {
    if (enabled) {
      // Enable with simple true value (not an object with nulls)
      updateGenerateConfig({ batch: true });
    } else {
      updateGenerateConfig({ batch: null });
    }
  };

  // Update batch config field
  const updateBatchConfig = (updates: Partial<BatchConfig>) => {
    // Get existing non-null values
    const existingConfig = typeof batch === "object" && batch !== null
      ? filterNullValues(batch)
      : {};
    const size = typeof batch === "number" ? batch : (existingConfig as Partial<BatchConfig>).size;

    updateGenerateConfig({
      batch: {
        ...(size !== undefined ? { size } : {}),
        ...existingConfig,
        ...updates,
      } as BatchConfig,
    });
  };

  // Get the current size value (from config or simple number mode)
  const currentSize =
    typeof batch === "object" ? batchConfig.size : simpleBatchSize;

  return (
    <div className={styles.tabContent}>
      <div className={styles.section}>
        <div className={styles.field}>
          <VscodeCheckbox
            checked={isEnabled}
            onChange={(e) =>
              handleEnableChange((e.target as HTMLInputElement).checked)
            }
          >
            Enable Batch Processing
          </VscodeCheckbox>
          <VscodeFormHelper>
            Process multiple requests in batches for improved throughput
          </VscodeFormHelper>
        </div>

        {isEnabled && (
          <div className={styles.twoColumnGrid}>
            <div className={styles.field}>
              <VscodeLabel>Batch Size</VscodeLabel>
              <VscodeFormHelper>Number of requests per batch</VscodeFormHelper>
              <VscodeTextfield
                value={currentSize?.toString() ?? ""}
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
                value={batchConfig.max_size?.toString() ?? ""}
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
                value={batchConfig.max_batches?.toString() ?? ""}
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
                value={batchConfig.send_delay?.toString() ?? ""}
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
                value={batchConfig.tick?.toString() ?? ""}
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
                value={batchConfig.max_consecutive_check_failures?.toString() ?? ""}
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
        )}
      </div>
    </div>
  );
};
