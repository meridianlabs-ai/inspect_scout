import { clsx } from "clsx";
import { FC } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { ApplicationIcons } from "../../components/icons";
import { LoadingBar } from "../../components/LoadingBar";
import { NoContentsPanel } from "../../components/NoContentsPanel";
import { useServerActiveScans } from "../server/useServerActiveScans";

import styles from "./ActivePanel.module.css";

export const ActivePanel: FC = () => {
  const { loading, error, data: activeScans } = useServerActiveScans();

  const entries = activeScans ? Object.entries(activeScans) : [];

  return (
    <div className={clsx(styles.container)}>
      <LoadingBar loading={!!loading} />
      {error && (
        <ErrorPanel
          title="Error Loading Active Scans"
          error={{ message: error.message }}
        />
      )}
      {!activeScans && !error && (
        <NoContentsPanel icon={ApplicationIcons.running} text="Loading..." />
      )}
      {activeScans && !error && entries.length === 0 && (
        <NoContentsPanel
          icon={ApplicationIcons.running}
          text="No active scans"
        />
      )}
      {activeScans && !error && entries.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Scan ID</th>
              <th>Processes</th>
              <th>Tasks</th>
              <th>Completed</th>
              <th>Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([pid, info]) => (
              <tr key={pid}>
                <td>{info.scan_id}</td>
                <td>{info.metrics?.process_count ?? "-"}</td>
                <td>{info.metrics?.task_count ?? "-"}</td>
                <td>{info.metrics?.completed_scans ?? "-"}</td>
                <td>{info.last_updated}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
