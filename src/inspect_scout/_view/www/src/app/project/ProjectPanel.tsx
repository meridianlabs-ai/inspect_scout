import { useQueryClient } from "@tanstack/react-query";
import {
  VscodeButton,
  VscodeFormHelper,
} from "@vscode-elements/react-elements";
import { FC, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBlocker } from "react-router-dom";

import { ApiError } from "../../api/request";
import { Modal } from "../../components/Modal";
import { AppConfig, ProjectConfigInput } from "../../types/api-types";
import { appAliasedPath } from "../server/useConfig";
import {
  useProjectConfig,
  useUpdateProjectConfig,
} from "../server/useProjectConfig";

import styles from "./ProjectPanel.module.css";
import { SettingsContent } from "./SettingsContent";

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
function computeConfigToSave(
  edited: Partial<ProjectConfigInput>,
  original: Partial<ProjectConfigInput>,
  serverConfig: ProjectConfigInput
): ProjectConfigInput {
  const result: Record<string, unknown> = {};

  const allKeys = new Set([
    ...Object.keys(edited),
    ...Object.keys(serverConfig),
  ]);

  for (const key of allKeys) {
    const editedValue = edited[key as keyof ProjectConfigInput];
    const originalValue = original[key as keyof ProjectConfigInput];
    const serverValue = serverConfig[key as keyof ProjectConfigInput];

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

    const valueChanged =
      JSON.stringify(editedValue) !== JSON.stringify(originalValue);

    if (valueChanged) {
      result[key] = editedValue;
    } else if (!isEmpty(editedValue)) {
      result[key] = editedValue;
    }
  }

  return result as ProjectConfigInput;
}

function cleanGenerateConfig(
  edited: Record<string, unknown> | null | undefined,
  original: Record<string, unknown> | null | undefined,
  _server: Record<string, unknown> | null | undefined
): Record<string, unknown> | null | undefined {
  if (
    edited === null ||
    edited === undefined ||
    (typeof edited === "object" && Object.keys(edited).length === 0)
  ) {
    const originalHasContent =
      original !== null &&
      original !== undefined &&
      typeof original === "object" &&
      Object.keys(original).length > 0;
    if (originalHasContent) {
      return null;
    }
    return undefined;
  }

  const result: Record<string, unknown> = {};
  const editedObj = edited;
  const originalObj = original ?? {};

  for (const key of Object.keys(editedObj)) {
    const editedValue = editedObj[key];
    const originalValue = originalObj[key];

    if (key === "cache" || key === "batch") {
      const cleanedNested = cleanNestedConfig(
        editedValue as
          | Record<string, unknown>
          | boolean
          | number
          | null
          | undefined,
        originalValue as
          | Record<string, unknown>
          | boolean
          | number
          | null
          | undefined
      );
      if (cleanedNested !== undefined) {
        result[key] = cleanedNested;
      }
      continue;
    }

    if (editedValue === null || editedValue === undefined) {
      const originalHadContent =
        originalValue !== null &&
        originalValue !== undefined &&
        (typeof originalValue !== "object" ||
          Object.keys(originalValue).length > 0);
      if (originalHadContent) {
        result[key] = null;
      }
      continue;
    }

    result[key] = editedValue;
  }

  if (Object.keys(result).length === 0) {
    return undefined;
  }

  return result;
}

function cleanNestedConfig(
  edited: Record<string, unknown> | boolean | number | null | undefined,
  original: Record<string, unknown> | boolean | number | null | undefined
): Record<string, unknown> | boolean | number | null | undefined {
  if (typeof edited === "boolean" || typeof edited === "number") {
    return edited;
  }

  if (edited === null || edited === undefined) {
    if (original !== null && original !== undefined) {
      return null;
    }
    return undefined;
  }

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
    if (original !== null && original !== undefined) {
      return true;
    }
    return undefined;
  }

  return result;
}

function initializeEditedConfig(
  serverConfig: ProjectConfigInput
): Partial<ProjectConfigInput> {
  return {
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
    model: serverConfig.model,
    model_base_url: serverConfig.model_base_url,
    model_args: serverConfig.model_args,
    generate_config: serverConfig.generate_config ?? null,
  };
}

export const ProjectPanel: FC<ProjectPanelProps> = ({ config }) => {
  const scrollContentRef = useRef<HTMLDivElement>(null);

  // Scroll to section - only scrolls within the scrollContent container
  const scrollToSection = useCallback((sectionId: string) => {
    const container = scrollContentRef.current;
    const element = document.getElementById(sectionId);
    if (container && element) {
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();
      const scrollTop =
        container.scrollTop + (elementRect.top - containerRect.top);
      container.scrollTo({ top: scrollTop, behavior: "smooth" });
    }
  }, []);
  const queryClient = useQueryClient();
  const { loading, error, data } = useProjectConfig();
  const mutation = useUpdateProjectConfig();

  const [editedConfig, setEditedConfig] =
    useState<Partial<ProjectConfigInput> | null>(null);
  const [originalConfig, setOriginalConfig] =
    useState<Partial<ProjectConfigInput> | null>(null);
  const [conflictError, setConflictError] = useState(false);

  useEffect(() => {
    if (data && !editedConfig) {
      const initialized = initializeEditedConfig(
        data.config as ProjectConfigInput
      );
      setEditedConfig(initialized);
      setOriginalConfig(JSON.parse(JSON.stringify(initialized)));
    }
  }, [data, editedConfig]);

  useEffect(() => {
    if (data) {
      const initialized = initializeEditedConfig(
        data.config as ProjectConfigInput
      );
      setEditedConfig(initialized);
      setOriginalConfig(JSON.parse(JSON.stringify(initialized)));
    }
  }, [data?.etag]);

  const hasChanges = useMemo(() => {
    return !configsEqual(editedConfig, originalConfig);
  }, [editedConfig, originalConfig]);

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasChanges && currentLocation.pathname !== nextLocation.pathname
  );

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

      {/* Split Layout: Tree + Content */}
      {editedConfig && (
        <div className={styles.splitLayout}>
          {/* Navigation */}
          <nav className={styles.treeNav}>
            <ul className={styles.navList}>
              {/* General Group */}
              <li className={styles.navGroup}>General</li>
              <li className={styles.navListItem}>
                <button
                  className={styles.navItem}
                  onClick={() => scrollToSection("locations")}
                >
                  Locations
                </button>
              </li>
              <li className={styles.navListItem}>
                <button
                  className={styles.navItem}
                  onClick={() => scrollToSection("filtering")}
                >
                  Filtering
                </button>
              </li>
              <li className={styles.navListItem}>
                <button
                  className={styles.navItem}
                  onClick={() => scrollToSection("concurrency")}
                >
                  Concurrency
                </button>
              </li>
              <li className={styles.navListItem}>
                <button
                  className={styles.navItem}
                  onClick={() => scrollToSection("miscellaneous")}
                >
                  Miscellaneous
                </button>
              </li>

              {/* Model Group */}
              <li className={styles.navGroup}>Model</li>
              <li className={styles.navListItem}>
                <button
                  className={styles.navItem}
                  onClick={() => scrollToSection("model")}
                >
                  Model
                </button>
              </li>
              <li className={styles.navListItem}>
                <button
                  className={styles.navItem}
                  onClick={() => scrollToSection("connection")}
                >
                  Connection
                </button>
              </li>
              <li className={styles.navListItem}>
                <button
                  className={styles.navItem}
                  onClick={() => scrollToSection("generation")}
                >
                  Generation
                </button>
              </li>
              <li className={styles.navListItem}>
                <button
                  className={styles.navItem}
                  onClick={() => scrollToSection("reasoning")}
                >
                  Reasoning
                </button>
              </li>
              <li className={styles.navListItem}>
                <button
                  className={styles.navItem}
                  onClick={() => scrollToSection("cache")}
                >
                  Cache
                </button>
              </li>
              <li className={styles.navListItem}>
                <button
                  className={styles.navItem}
                  onClick={() => scrollToSection("batch")}
                >
                  Batch
                </button>
              </li>
            </ul>
          </nav>

          {/* Scrollable Content */}
          <div ref={scrollContentRef} className={styles.scrollContent}>
            <VscodeFormHelper style={{ marginBottom: "10px" }}>
              Project configuration is written to a scout.yaml file in the
              project directory, and provides default configuration for scans
              run from the directory. You can override some or all of the
              project configuration for each scan using command line parameters
              or a scan job config file.
            </VscodeFormHelper>
            <SettingsContent
              config={editedConfig}
              onChange={handleConfigChange}
            />
          </div>
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
