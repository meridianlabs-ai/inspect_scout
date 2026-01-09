import { clsx } from "clsx";
import { FC } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { ApplicationIcons } from "../../components/icons";
import { LoadingBar } from "../../components/LoadingBar";
import { NoContentsPanel } from "../../components/NoContentsPanel";
import { ActiveScanInfo } from "../../types/api-types";
import { useServerActiveScans } from "../server/useServerActiveScans";

import styles from "./ActivePanel.module.css";

const formatMemory = (bytes: number): string => {
  const gb = bytes / (1024 * 1024 * 1024);
  return `${gb.toFixed(1)} GB`;
};

const ActiveScanCard: FC<{ info: ActiveScanInfo }> = ({ info }) => {
  const { metrics, summary } = info;
  const scannerEntries = Object.entries(summary.scanners);

  // Calculate total tokens per scanner
  const scannerStats = scannerEntries.map(([name, scanner]) => {
    const totalTokens = Object.values(scanner.model_usage).reduce(
      (sum, usage) => sum + (usage.total_tokens ?? 0),
      0
    );
    const tokensPerScan = scanner.scans > 0 ? Math.round(totalTokens / scanner.scans) : 0;
    return { name, scanner, totalTokens, tokensPerScan };
  });

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.scanId}>scan: {info.scan_id}</span>
        <span className={styles.progress}>
          {metrics.completed_scans} completed
        </span>
      </div>

      <div className={styles.content}>
        <div className={styles.mainSection}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>scanner</th>
                <th className={styles.numeric}>results</th>
                <th className={styles.numeric}>errors</th>
                <th className={styles.numeric}>tokens/scan</th>
                <th className={styles.numeric}>tokens</th>
              </tr>
            </thead>
            <tbody>
              {scannerStats.map(({ name, scanner, totalTokens, tokensPerScan }) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td className={styles.numeric}>{scanner.results || "-"}</td>
                  <td className={styles.numeric}>{scanner.errors || "-"}</td>
                  <td className={styles.numeric}>
                    {tokensPerScan ? tokensPerScan.toLocaleString() : "-"}
                  </td>
                  <td className={styles.numeric}>
                    {totalTokens ? totalTokens.toLocaleString() : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className={styles.sidebar}>
          <div className={styles.sidebarSection}>
            <div className={styles.sidebarTitle}>workers</div>
            <div className={styles.stat}>
              <span>parsing:</span>
              <span>{metrics.tasks_parsing}</span>
            </div>
            <div className={styles.stat}>
              <span>scanning:</span>
              <span>{metrics.tasks_scanning}</span>
            </div>
            <div className={styles.stat}>
              <span>idle:</span>
              <span>{metrics.tasks_idle}</span>
            </div>
            <div className={styles.stat}>
              <span>memory:</span>
              <span>{formatMemory(metrics.memory_usage)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

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
      {activeScans &&
        !error &&
        entries.map(([pid, info]) => <ActiveScanCard key={pid} info={info} />)}
    </div>
  );
};
