import clsx from "clsx";
import { FC, useEffect, useMemo, useState } from "react";

import { ApiError } from "../../api/request";
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
  const { loading, error, data } = useProjectConfig();
  const mutation = useUpdateProjectConfig();

  // Form state - track edited values separately from server data
  const [editedConfig, setEditedConfig] =
    useState<Partial<ProjectConfigInput> | null>(null);
  const [conflictError, setConflictError] = useState(false);

  // Initialize form state when data loads
  useEffect(() => {
    if (data && !editedConfig) {
      setEditedConfig({
        transcripts: data.config.transcripts,
        scans: data.config.scans,
        model: data.config.model,
      });
    }
  }, [data, editedConfig]);

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
        },
        onError: (err) => {
          if (err instanceof ApiError && err.status === 412) {
            setConflictError(true);
          }
        },
      }
    );
  };

  const handleReload = () => {
    setConflictError(false);
    setEditedConfig(null);
    // The query will refetch automatically, or we could invalidate
  };

  return (
    <div className={clsx(styles.container)}>
      <div className={styles.headerRow}>
        <div>
          <div className={styles.header}>Project</div>
          <div className={styles.detail}>
            {appAliasedPath(config, config.project_dir)}
          </div>
        </div>
        <button
          className={styles.saveButton}
          disabled={!hasChanges || mutation.isPending}
          onClick={() => handleSave(false)}
        >
          {mutation.isPending ? "Saving..." : "Save Changes"}
        </button>
      </div>

      {conflictError && (
        <div className={styles.conflictBanner}>
          <span>Configuration was modified externally.</span>
          <div className={styles.conflictActions}>
            <button className={styles.discardButton} onClick={handleReload}>
              Discard My Changes
            </button>
            <button
              className={styles.forceSaveButton}
              onClick={() => handleSave(true)}
            >
              Keep My Changes
            </button>
          </div>
        </div>
      )}

      {loading && <div className={styles.loading}>Loading...</div>}

      {error && (
        <div className={styles.error}>
          Error loading config: {error.message}
        </div>
      )}

      {editedConfig && (
        <div className={styles.form}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Transcripts</label>
            <input
              type="text"
              className={styles.input}
              value={editedConfig.transcripts ?? ""}
              onChange={(e) =>
                setEditedConfig((prev) => ({
                  ...prev,
                  transcripts: e.target.value || null,
                }))
              }
              placeholder="Path to transcripts directory"
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>Scans</label>
            <input
              type="text"
              className={styles.input}
              value={editedConfig.scans ?? ""}
              onChange={(e) =>
                setEditedConfig((prev) => ({
                  ...prev,
                  scans: e.target.value || null,
                }))
              }
              placeholder="Path to scans output directory"
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>Model</label>
            <input
              type="text"
              className={styles.input}
              value={editedConfig.model ?? ""}
              onChange={(e) =>
                setEditedConfig((prev) => ({
                  ...prev,
                  model: e.target.value || null,
                }))
              }
              placeholder="Default model (e.g., openai/gpt-4)"
            />
          </div>
        </div>
      )}
    </div>
  );
};
