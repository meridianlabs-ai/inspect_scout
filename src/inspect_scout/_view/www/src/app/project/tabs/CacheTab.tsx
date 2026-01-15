import {
  VscodeCheckbox,
  VscodeFormHelper,
  VscodeLabel,
  VscodeTextfield,
} from "@vscode-elements/react-elements";
import { FC } from "react";

import {
  CachePolicy,
  GenerateConfigInput,
  ProjectConfigInput,
} from "../../../types/api-types";

import styles from "./tabs.module.css";

export interface CacheTabProps {
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

export const CacheTab: FC<CacheTabProps> = ({ config, onChange }) => {
  const generateConfig = config.generate_config ?? {};
  const cache = generateConfig.cache;

  // Determine cache state
  const isEnabled = cache !== null && cache !== undefined && cache !== false;
  const cachePolicy: Partial<CachePolicy> =
    typeof cache === "object" && cache !== null ? cache : {};

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

  // Enable/disable cache
  const handleEnableChange = (enabled: boolean) => {
    if (enabled) {
      // Enable with simple true value (not an object with defaults)
      updateGenerateConfig({ cache: true });
    } else {
      updateGenerateConfig({ cache: null });
    }
  };

  // Update cache policy field
  const updateCachePolicy = (updates: Partial<CachePolicy>) => {
    // Get existing non-null values
    const existingConfig = typeof cache === "object" && cache !== null
      ? filterNullValues(cache)
      : {};

    updateGenerateConfig({
      cache: {
        ...existingConfig,
        ...updates,
      } as CachePolicy,
    });
  };

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
            Enable Caching
          </VscodeCheckbox>
          <VscodeFormHelper>
            Cache model responses to improve performance and reduce API costs
          </VscodeFormHelper>
        </div>

        {isEnabled && (
          <div className={styles.twoColumnGrid}>
            <div className={styles.field}>
              <VscodeLabel>Expiry</VscodeLabel>
              <VscodeFormHelper>
                Cache expiration duration (e.g., "1W" for one week, "1D" for one
                day)
              </VscodeFormHelper>
              <VscodeTextfield
                value={cachePolicy.expiry ?? "1W"}
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
        )}
      </div>
    </div>
  );
};
