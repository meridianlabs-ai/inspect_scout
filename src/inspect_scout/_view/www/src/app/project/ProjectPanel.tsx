import { useQueryClient } from "@tanstack/react-query";
import { VscodeButton } from "@vscode-elements/react-elements";
import { FC, useCallback, useEffect, useMemo, useState } from "react";
import { useBlocker } from "react-router-dom";

import { ApiError } from "../../api/request";
import { Modal } from "../../components/Modal";
import { NavPills } from "../../components/NavPills";
import { AppConfig, ProjectConfigInput } from "../../types/api-types";
import { appAliasedPath } from "../server/useConfig";
import {
  useProjectConfig,
  useUpdateProjectConfig,
} from "../server/useProjectConfig";

import styles from "./ProjectPanel.module.css";
import { BatchTab } from "./tabs/BatchTab";
import { CacheTab } from "./tabs/CacheTab";
import { GeneralTab } from "./tabs/GeneralTab";
import { ModelTab } from "./tabs/ModelTab";

interface ProjectPanelProps {
  config: AppConfig;
}

// Deep equality check for config objects
function configsEqual(
  a: Partial<ProjectConfigInput> | null,
  b: Partial<ProjectConfigInput> | null
): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return JSON.stringify(a) === JSON.stringify(b);
}

// Check if a value is "empty" (null, undefined, or empty object/array)
function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.keys(value).length === 0;
  return false;
}

// Compute the config to save by comparing edited values against original server state
// Rules:
// - If value changed from original: include it (even if now null - user cleared it)
// - If value unchanged and is null/empty: don't include it (avoid writing defaults)
// - If value unchanged and has content: include it
function computeConfigToSave(
  edited: Partial<ProjectConfigInput>,
  original: Partial<ProjectConfigInput>,
  serverConfig: ProjectConfigInput
): ProjectConfigInput {
  const result: Record<string, unknown> = {};

  // Get all keys from both edited and server config
  const allKeys = new Set([
    ...Object.keys(edited),
    ...Object.keys(serverConfig),
  ]);

  for (const key of allKeys) {
    const editedValue = edited[key as keyof ProjectConfigInput];
    const originalValue = original[key as keyof ProjectConfigInput];
    const serverValue = serverConfig[key as keyof ProjectConfigInput];

    // Special handling for nested generate_config
    if (key === "generate_config") {
      const cleanedGenConfig = cleanGenerateConfig(
        editedValue as Record<string, unknown> | null | undefined,
        originalValue as Record<string, unknown> | null | undefined,
        serverValue as Record<string, unknown> | null | undefined
      );
      if (cleanedGenConfig !== undefined) {
        result[key] = cleanedGenConfig;
      }
      continue;
    }

    // Check if value changed from original
    const valueChanged =
      JSON.stringify(editedValue) !== JSON.stringify(originalValue);

    if (valueChanged) {
      // Value changed - include it (even if null, to clear the field)
      result[key] = editedValue;
    } else if (!isEmpty(editedValue)) {
      // Value unchanged but has content - include it
      result[key] = editedValue;
    }
    // If unchanged and empty, don't include (let server use defaults)
  }

  return result as ProjectConfigInput;
}

// Clean up generate_config, only including fields that have values or were explicitly changed
function cleanGenerateConfig(
  edited: Record<string, unknown> | null | undefined,
  original: Record<string, unknown> | null | undefined,
  _server: Record<string, unknown> | null | undefined
): Record<string, unknown> | null | undefined {
  // If edited is null/undefined or empty object
  if (edited === null || edited === undefined ||
      (typeof edited === "object" && Object.keys(edited).length === 0)) {
    // If original had actual content, user cleared it - return null to clear
    const originalHasContent = original !== null && original !== undefined &&
      typeof original === "object" && Object.keys(original).length > 0;
    if (originalHasContent) {
      return null;
    }
    // Otherwise, don't include at all
    return undefined;
  }

  const result: Record<string, unknown> = {};
  const editedObj = edited;
  const originalObj = original ?? {};

  for (const key of Object.keys(editedObj)) {
    const editedValue = editedObj[key];
    const originalValue = originalObj[key];

    // Special handling for nested cache and batch objects
    if (key === "cache" || key === "batch") {
      const cleanedNested = cleanNestedConfig(
        editedValue as Record<string, unknown> | boolean | number | null | undefined,
        originalValue as Record<string, unknown> | boolean | number | null | undefined
      );
      if (cleanedNested !== undefined) {
        result[key] = cleanedNested;
      }
      continue;
    }

    // Skip null/undefined values unless user explicitly cleared a previously-set value
    if (editedValue === null || editedValue === undefined) {
      // Only include null if original had actual content (user cleared it)
      const originalHadContent = originalValue !== null &&
        originalValue !== undefined &&
        (typeof originalValue !== "object" || Object.keys(originalValue).length > 0);
      if (originalHadContent) {
        result[key] = null; // Explicitly clear
      }
      // Otherwise skip - don't include null values
      continue;
    }

    // Include non-null values
    result[key] = editedValue;
  }

  // If result is empty, don't include generate_config at all
  if (Object.keys(result).length === 0) {
    return undefined;
  }

  return result;
}

// Clean nested cache/batch config objects
function cleanNestedConfig(
  edited: Record<string, unknown> | boolean | number | null | undefined,
  original: Record<string, unknown> | boolean | number | null | undefined
): Record<string, unknown> | boolean | number | null | undefined {
  // Handle boolean/number cases (simple enable)
  if (typeof edited === "boolean" || typeof edited === "number") {
    return edited;
  }

  // If edited is null/undefined
  if (edited === null || edited === undefined) {
    // If original had a value, user disabled it - return null
    if (original !== null && original !== undefined) {
      return null;
    }
    return undefined;
  }

  // edited is an object - clean it
  const result: Record<string, unknown> = {};
  const originalObj =
    typeof original === "object" && original !== null ? original : {};

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
    // If original was enabled (had content or was true), user might have cleared values
    // Return true to keep it enabled but with defaults
    if (original !== null && original !== undefined) {
      return true;
    }
    return undefined;
  }

  return result;
}

// Initialize edited config from server data
function initializeEditedConfig(
  serverConfig: ProjectConfigInput
): Partial<ProjectConfigInput> {
  return {
    // General tab fields
    transcripts: serverConfig.transcripts,
    filter: serverConfig.filter,
    scans: serverConfig.scans,
    max_transcripts: serverConfig.max_transcripts,
    max_processes: serverConfig.max_processes,
    limit: serverConfig.limit,
    shuffle: serverConfig.shuffle,
    tags: serverConfig.tags,
    metadata: serverConfig.metadata,
    log_level: serverConfig.log_level,
    // Model tab fields (top-level)
    model: serverConfig.model,
    model_base_url: serverConfig.model_base_url,
    model_args: serverConfig.model_args,
    // Nested generate_config (includes model, cache, batch settings)
    generate_config: serverConfig.generate_config ?? null,
  };
}

export const ProjectPanel: FC<ProjectPanelProps> = ({ config }) => {
  const queryClient = useQueryClient();
  const { loading, error, data } = useProjectConfig();
  const mutation = useUpdateProjectConfig();

  // Form state - track edited values separately from server data
  const [editedConfig, setEditedConfig] =
    useState<Partial<ProjectConfigInput> | null>(null);
  const [originalConfig, setOriginalConfig] =
    useState<Partial<ProjectConfigInput> | null>(null);
  const [conflictError, setConflictError] = useState(false);

  // Initialize form state when data loads
  useEffect(() => {
    if (data && !editedConfig) {
      const initialized = initializeEditedConfig(
        data.config as ProjectConfigInput
      );
      setEditedConfig(initialized);
      // Deep clone for originalConfig to avoid shared references
      setOriginalConfig(JSON.parse(JSON.stringify(initialized)));
    }
  }, [data, editedConfig]);

  // Reset form when data changes (e.g., after successful save or refresh)
  useEffect(() => {
    if (data) {
      const initialized = initializeEditedConfig(
        data.config as ProjectConfigInput
      );
      setEditedConfig(initialized);
      // Deep clone for originalConfig to avoid shared references
      setOriginalConfig(JSON.parse(JSON.stringify(initialized)));
    }
  }, [data?.etag]);

  // Compute if there are unsaved changes using deep comparison
  const hasChanges = useMemo(() => {
    return !configsEqual(editedConfig, originalConfig);
  }, [editedConfig, originalConfig]);

  // Navigation blocking when there are unsaved changes
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasChanges && currentLocation.pathname !== nextLocation.pathname
  );

  // Handler for tab changes
  const handleConfigChange = useCallback(
    (updates: Partial<ProjectConfigInput>) => {
      setEditedConfig((prev) => ({
        ...prev,
        ...updates,
      }));
    },
    []
  );

  const handleSave = (force = false) => {
    if (!data || !editedConfig || !originalConfig) return;

    // Compute config to save by comparing against original state
    const updatedConfig = computeConfigToSave(
      editedConfig,
      originalConfig,
      data.config as ProjectConfigInput
    );

    mutation.mutate(
      { config: updatedConfig, etag: force ? null : data.etag },
      {
        onSuccess: () => {
          setConflictError(false);
        },
        onError: (err) => {
          if (err instanceof ApiError && err.status === 412) {
            setConflictError(true);
          }
        },
      }
    );
  };

  const handleSaveAndNavigate = () => {
    if (!data || !editedConfig || !originalConfig) {
      blocker.proceed?.();
      return;
    }

    // Compute config to save by comparing against original state
    const updatedConfig = computeConfigToSave(
      editedConfig,
      originalConfig,
      data.config as ProjectConfigInput
    );

    mutation.mutate(
      { config: updatedConfig, etag: data.etag },
      {
        onSuccess: () => {
          setConflictError(false);
          blocker.proceed?.();
        },
        onError: (err) => {
          if (err instanceof ApiError && err.status === 412) {
            setConflictError(true);
          }
          blocker.reset?.();
        },
      }
    );
  };

  const handleReload = () => {
    setConflictError(false);
    setEditedConfig(null);
    setOriginalConfig(null);
    // Explicitly refetch since automatic refetching is disabled for optimistic locking
    void queryClient.invalidateQueries({ queryKey: ["project-config"] });
  };

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div>
          <div className={styles.header}>Project Config</div>
          <div className={styles.detail}>
            {appAliasedPath(config, config.project_dir)}/scout.yaml
          </div>
        </div>
        <VscodeButton
          disabled={!hasChanges || mutation.isPending}
          onClick={() => handleSave(false)}
        >
          {mutation.isPending ? "Saving..." : "Save Changes"}
        </VscodeButton>
      </div>

      {/* Conflict Banner */}
      {conflictError && (
        <div className={styles.conflictBanner}>
          <span>Configuration was modified externally.</span>
          <div className={styles.conflictActions}>
            <VscodeButton secondary onClick={handleReload}>
              Discard My Changes
            </VscodeButton>
            <VscodeButton onClick={() => handleSave(true)}>
              Keep My Changes
            </VscodeButton>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && <div className={styles.loading}>Loading...</div>}

      {/* Error State */}
      {error && (
        <div className={styles.error}>
          Error loading config: {error.message}
        </div>
      )}

      {/* Tabbed Form */}
      {editedConfig && (
        <div className={styles.form}>
          <NavPills id="project-config-tabs">
            <GeneralTab
              title="General"
              config={editedConfig}
              onChange={handleConfigChange}
            />
            <ModelTab
              title="Model"
              config={editedConfig}
              onChange={handleConfigChange}
            />
            <CacheTab
              title="Cache"
              config={editedConfig}
              onChange={handleConfigChange}
            />
            <BatchTab
              title="Batch"
              config={editedConfig}
              onChange={handleConfigChange}
            />
          </NavPills>
        </div>
      )}

      {/* Unsaved Changes Modal */}
      <Modal
        show={blocker.state === "blocked"}
        onHide={() => blocker.reset?.()}
        title="Unsaved Changes"
        footer={
          <>
            <VscodeButton secondary onClick={() => blocker.proceed?.()}>
              Don't Save
            </VscodeButton>
            <VscodeButton secondary onClick={() => blocker.reset?.()}>
              Cancel
            </VscodeButton>
            <VscodeButton data-autofocus onClick={handleSaveAndNavigate}>
              Save
            </VscodeButton>
          </>
        }
      >
        You have unsaved changes. Do you want to save before leaving?
      </Modal>
    </div>
  );
};
