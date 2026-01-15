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

  // Initialize config state when data loads or etag changes
  useEffect(() => {
    if (!data) return;

    // Only initialize if we haven't yet, or if etag changed (external modification)
    const shouldInitialize = !editedConfig;
    const etagChanged = data.etag !== undefined; // etag dependency handles re-init

    if (shouldInitialize || etagChanged) {
      const initialized = initializeEditedConfig(
        data.config as ProjectConfigInput
      );
      setEditedConfig(initialized);
      setOriginalConfig(deepCopy(initialized));
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
              Project configuration provides default options for scans run from
              the directory. You can override some or all of the defaults for
              each scan using command line parameters or a scan job config file.
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
