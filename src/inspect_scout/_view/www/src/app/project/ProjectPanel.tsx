import { useQueryClient } from "@tanstack/react-query";
import {
  VscodeButton,
  VscodeFormHelper,
  VscodeLabel,
  VscodeTextfield,
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

interface ProjectPanelProps {
  config: AppConfig;
}

export const ProjectPanel: FC<ProjectPanelProps> = ({ config }) => {
  const queryClient = useQueryClient();
  const { loading, error, data } = useProjectConfig();
  const mutation = useUpdateProjectConfig();

  // Form state - track edited values separately from server data
  const [editedConfig, setEditedConfig] =
    useState<Partial<ProjectConfigInput> | null>(null);
  const [conflictError, setConflictError] = useState(false);

  // Ref for focusing the first input
  const firstInputRef = useRef<HTMLElement | null>(null);
  const focusFirstInput = useCallback(() => {
    setTimeout(() => firstInputRef.current?.focus(), 0);
  }, []);

  // Initialize form state when data loads
  useEffect(() => {
    if (data && !editedConfig) {
      setEditedConfig({
        transcripts: data.config.transcripts,
        scans: data.config.scans,
        model: data.config.model,
      });
      focusFirstInput();
    }
  }, [data, editedConfig, focusFirstInput]);

  // Reset form when data changes (e.g., after successful save or refresh)
  useEffect(() => {
    if (data) {
      setEditedConfig({
        transcripts: data.config.transcripts,
        scans: data.config.scans,
        model: data.config.model,
      });
    }
  }, [data?.etag]);

  // Compute if there are unsaved changes
  const hasChanges = useMemo(() => {
    if (!editedConfig || !data) return false;
    return (
      editedConfig.transcripts !== data.config.transcripts ||
      editedConfig.scans !== data.config.scans ||
      editedConfig.model !== data.config.model
    );
  }, [editedConfig, data]);

  // Navigation blocking when there are unsaved changes
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasChanges && currentLocation.pathname !== nextLocation.pathname
  );

  const handleSave = (force = false) => {
    if (!data || !editedConfig) return;

    // Merge edited fields with full config
    // Type assertion needed because Output type has slightly broader types than Input
    const updatedConfig: ProjectConfigInput = {
      ...(data.config as ProjectConfigInput),
      ...editedConfig,
    };

    mutation.mutate(
      { config: updatedConfig, etag: force ? null : data.etag },
      {
        onSuccess: () => {
          setConflictError(false);
          focusFirstInput();
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
    if (!data || !editedConfig) {
      blocker.proceed?.();
      return;
    }

    const updatedConfig: ProjectConfigInput = {
      ...(data.config as ProjectConfigInput),
      ...editedConfig,
    };

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
    // Explicitly refetch since automatic refetching is disabled for optimistic locking
    void queryClient.invalidateQueries({ queryKey: ["project-config"] });
    // Focus will happen via the useEffect when editedConfig is re-initialized
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

      {/* Form */}
      {editedConfig && (
        <div className={styles.form}>
          <div className={styles.field}>
            <VscodeLabel>Transcripts</VscodeLabel>
            <VscodeFormHelper>
              Directory containing conversation transcripts to analyze
            </VscodeFormHelper>
            <VscodeTextfield
              ref={(el) => {
                firstInputRef.current = el;
              }}
              value={editedConfig.transcripts ?? ""}
              onInput={(e) =>
                setEditedConfig((prev) => ({
                  ...prev,
                  transcripts: (e.target as HTMLInputElement).value || null,
                }))
              }
              placeholder="Path to transcripts directory"
              spellCheck={false}
            />
          </div>

          <div className={styles.field}>
            <VscodeLabel>Scans</VscodeLabel>
            <VscodeFormHelper>
              Output directory for scan results and reports
            </VscodeFormHelper>
            <VscodeTextfield
              value={editedConfig.scans ?? ""}
              onInput={(e) =>
                setEditedConfig((prev) => ({
                  ...prev,
                  scans: (e.target as HTMLInputElement).value || null,
                }))
              }
              placeholder="Path to scans output directory"
              spellCheck={false}
            />
          </div>

          <div className={styles.field}>
            <VscodeLabel>Model</VscodeLabel>
            <VscodeFormHelper>
              Default language model for analysis (e.g., openai/gpt-4o)
            </VscodeFormHelper>
            <VscodeTextfield
              value={editedConfig.model ?? ""}
              onInput={(e) =>
                setEditedConfig((prev) => ({
                  ...prev,
                  model: (e.target as HTMLInputElement).value || null,
                }))
              }
              placeholder="Default model"
              spellCheck={false}
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
