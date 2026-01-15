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

import {
  computeConfigToSave,
  configsEqual,
  deepCopy,
  initializeEditedConfig,
} from "./configUtils";
import styles from "./ProjectPanel.module.css";
import { SettingsContent } from "./SettingsContent";

interface ProjectPanelProps {
  config: AppConfig;
}

// Navigation structure for the settings panel
interface NavItem {
  id: string;
  label: string;
}

interface NavSection {
  group: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    group: "General",
    items: [
      { id: "locations", label: "Locations" },
      { id: "filtering", label: "Filtering" },
      { id: "concurrency", label: "Concurrency" },
      { id: "miscellaneous", label: "Miscellaneous" },
    ],
  },
  {
    group: "Model",
    items: [
      { id: "model", label: "Model" },
      { id: "connection", label: "Connection" },
      { id: "generation", label: "Generation" },
      { id: "reasoning", label: "Reasoning" },
      { id: "cache", label: "Cache" },
      { id: "batch", label: "Batch" },
    ],
  },
];

export const ProjectPanel: FC<ProjectPanelProps> = ({ config }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollContentRef = useRef<HTMLDivElement>(null);
  const focusedBeforeSaveRef = useRef<Element | null>(null);
  const saveRef = useRef<() => void>(() => {});
  // Track the etag from our own saves to skip re-initialization
  const lastSavedEtagRef = useRef<string | null>(null);

  // Capture focused element on mousedown (before click moves focus to button)
  const handleSaveMouseDown = useCallback(() => {
    focusedBeforeSaveRef.current = document.activeElement;
  }, []);

  // Ctrl/Cmd+S keyboard shortcut to save
  // Always handle since project panel is the only active UI when visible
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        saveRef.current();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

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

  // Initialize config state when data loads
  // Skips re-init if this is our own save (etag matches what we just saved)
  useEffect(() => {
    if (!data) return;

    // If editedConfig is null (initial load or after reload), initialize
    if (!editedConfig) {
      const initialized = initializeEditedConfig(
        data.config as ProjectConfigInput
      );
      setEditedConfig(initialized);
      setOriginalConfig(deepCopy(initialized));
      lastSavedEtagRef.current = data.etag;
      return;
    }

    // If etag matches what we just saved, skip re-init (this is our own save)
    if (data.etag === lastSavedEtagRef.current) {
      return;
    }

    // Etag changed unexpectedly - reinitialize
    // (With current flow this shouldn't happen since external changes
    // are detected via 412 on save, but handle it just in case)
    const initialized = initializeEditedConfig(
      data.config as ProjectConfigInput
    );
    setEditedConfig(initialized);
    setOriginalConfig(deepCopy(initialized));
    lastSavedEtagRef.current = data.etag;
  }, [data?.etag, editedConfig]);

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

  const handleSave = useCallback(
    (force = false) => {
      if (!data || !editedConfig || !originalConfig) return;

      const updatedConfig = computeConfigToSave(
        editedConfig,
        originalConfig,
        data.config as ProjectConfigInput
      );

      mutation.mutate(
        { config: updatedConfig, etag: force ? null : data.etag },
        {
          onSuccess: (responseData) => {
            setConflictError(false);
            // Mark this etag as expected so the init effect skips re-init
            lastSavedEtagRef.current = responseData.etag;
            // Update originalConfig to match what we saved, so hasChanges becomes false
            setOriginalConfig(deepCopy(editedConfig));
          },
          onError: (err) => {
            if (err instanceof ApiError && err.status === 412) {
              setConflictError(true);
            }
          },
        }
      );
    },
    [data, editedConfig, originalConfig, mutation]
  );

  // Keep saveRef updated for keyboard shortcut
  useEffect(() => {
    saveRef.current = () => handleSave(false);
  }, [handleSave]);

  const handleSaveWithFocusRestore = (force = false) => {
    if (!data || !editedConfig || !originalConfig) return;

    // Use the element that was focused before mousedown on save button
    const focusedElement = focusedBeforeSaveRef.current as HTMLElement | null;

    const updatedConfig = computeConfigToSave(
      editedConfig,
      originalConfig,
      data.config as ProjectConfigInput
    );

    mutation.mutate(
      { config: updatedConfig, etag: force ? null : data.etag },
      {
        onSuccess: (responseData) => {
          setConflictError(false);
          // Mark this etag as expected so the init effect skips re-init
          lastSavedEtagRef.current = responseData.etag;
          // Update originalConfig to match what we saved, so hasChanges becomes false
          setOriginalConfig(deepCopy(editedConfig));
          // Restore focus after the click event fully completes
          requestAnimationFrame(() => {
            focusedElement?.focus?.();
          });
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
        onSuccess: (responseData) => {
          setConflictError(false);
          // Mark this etag as expected so the init effect skips re-init
          lastSavedEtagRef.current = responseData.etag;
          // Update originalConfig to match what we saved, so hasChanges becomes false
          setOriginalConfig(deepCopy(editedConfig));
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
    // Reset expected etag so the init effect will re-initialize from server
    lastSavedEtagRef.current = null;
    void queryClient.invalidateQueries({ queryKey: ["project-config"] });
  };

  return (
    <div ref={containerRef} className={styles.container}>
      {/* Header */}
      <div className={styles.headerRow}>
        <div>
          <div className={styles.header}>Project Settings</div>
          <div className={styles.detail}>
            {appAliasedPath(config, config.project_dir)}/scout.yaml
          </div>
        </div>
        <VscodeButton
          disabled={!hasChanges || mutation.isPending}
          onMouseDown={handleSaveMouseDown}
          onClick={() => handleSaveWithFocusRestore(false)}
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
            <VscodeButton onClick={() => handleSaveWithFocusRestore(true)}>
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
              {NAV_SECTIONS.map((section) => (
                <li key={section.group} className={styles.navListItem}>
                  <span className={styles.navGroup}>{section.group}</span>
                  <ul className={styles.navList}>
                    {section.items.map((item) => (
                      <li key={item.id} className={styles.navListItem}>
                        <button
                          className={styles.navItem}
                          onClick={() => scrollToSection(item.id)}
                        >
                          {item.label}
                        </button>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </nav>

          {/* Scrollable Content */}
          <div ref={scrollContentRef} className={styles.scrollContent}>
            <VscodeFormHelper style={{ marginBottom: "10px" }}>
              Project settings provide default options for scans run from the
              project directory. You can override some or all of the defaults
              for each scan using command line parameters or a scan job config
              file.
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
