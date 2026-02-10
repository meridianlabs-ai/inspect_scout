import { FC, useEffect, useState } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { ApplicationIcons } from "../../components/icons";
import { LoadingBar } from "../../components/LoadingBar";
import { NoContentsPanel } from "../../components/NoContentsPanel";
import {
  ActiveScanInfo,
  ScannerSummary,
  ValidationResults,
} from "../../types/api-types";
import { useActiveScan } from "../server/useActiveScan";

import styles from "./RunScanPanel.module.css";

const formatMemory = (bytes: number): string => {
  const gb = bytes / (1024 * 1024 * 1024);
  const formatted = gb.toFixed(1).replace(/\.?0+$/, "");
  return `${formatted} GB`;
};

const formatDuration = (seconds: number): string => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0)
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
};

/**
 * Get validation accuracy from pre-computed ValidationResults.
 */
const getValidationScore = (
  validation: ValidationResults | null | undefined
): number | null => {
  if (validation?.metrics?.accuracy == null) return null;
  return validation.metrics.accuracy;
};

const getFirstMetricValue = (
  metrics: Record<string, Record<string, number>> | null
): number | null => {
  if (!metrics) return null;
  const firstNested = Object.values(metrics)[0];
  if (!firstNested) return null;
  return Object.values(firstNested)[0] ?? null;
};

const getMetricLabel = (scanners: Record<string, ScannerSummary>): string => {
  const names = new Set<string>();
  for (const scanner of Object.values(scanners)) {
    if (scanner.metrics) {
      const firstNested = Object.values(scanner.metrics)[0];
      if (firstNested) {
        const firstKey = Object.keys(firstNested)[0];
        if (firstKey) names.add(firstKey);
      }
    }
  }
  return names.size === 1 ? ([...names][0] ?? "metric") : "metric";
};

const ActiveScanCard: FC<{ info: ActiveScanInfo }> = ({ info }) => {
  const { metrics, summary } = info;
  // Date.now() is intentionally impure here - we need the current time to calculate
  // live-updating elapsed/remaining durations. Safe for this client-only component.
  // eslint-disable-next-line react-hooks/purity
  const [now, setNow] = useState(Date.now());

  // Update time every second for elapsed/remaining
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);

  // Check if any scanner has validations or metrics (use scanner_names for iteration)
  const hasValidations = info.scanner_names.some(
    (name) => (summary.scanners[name]?.validation?.entries?.length ?? 0) > 0
  );
  const hasMetrics = info.scanner_names.some(
    (name) => summary.scanners[name]?.metrics !== null
  );
  const metricLabel = hasMetrics ? getMetricLabel(summary.scanners) : "";

  // Calculate scanner stats (iterate over scanner_names to show all rows from start)
  const scannerStats = info.scanner_names.map((name) => {
    const scanner = summary.scanners[name];
    const totalTokens = scanner
      ? Object.values(scanner.model_usage).reduce<number>(
          (sum, usage) => sum + (usage.total_tokens ?? 0),
          0
        )
      : 0;
    const tokensPerScan =
      scanner && scanner.scans > 0
        ? Math.round(totalTokens / scanner.scans)
        : 0;
    const validationScore = scanner
      ? getValidationScore(scanner.validation)
      : null;
    const metricValue = scanner
      ? getFirstMetricValue(scanner.metrics ?? null)
      : null;
    return {
      name,
      scanner,
      totalTokens,
      tokensPerScan,
      validationScore,
      metricValue,
    };
  });

  // Progress calculations
  const completed = metrics.completed_scans;
  const total = info.total_scans;
  const progressPct = total > 0 ? (completed / total) * 100 : 0;
  const elapsedSec = info.start_time > 0 ? now / 1000 - info.start_time : 0;
  const remainingSec =
    completed > 0 && total > completed
      ? (elapsedSec / completed) * (total - completed)
      : 0;

  // Batch processing
  const hasBatch = metrics.batch_oldest_created !== null;
  const batchAge = hasBatch
    ? Math.floor(now / 1000 - (metrics.batch_oldest_created ?? 0))
    : 0;

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div>
          <span className={styles.scanId}>
            {info.title || `scan: ${info.scan_id}`}
          </span>
          {info.config && (
            <div className={styles.configLine}>{info.config}</div>
          )}
        </div>
      </div>

      {total > 0 && (
        <div className={styles.progressSection}>
          <div className={styles.progressBar}>
            <div
              className={styles.progressFill}
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <div className={styles.progressStats}>
            <span>
              {completed.toLocaleString()}/{total.toLocaleString()}
            </span>
            <span>{formatDuration(elapsedSec)}</span>
            {remainingSec > 0 && <span>{formatDuration(remainingSec)}</span>}
          </div>
        </div>
      )}

      <div className={styles.content}>
        <div className={styles.mainSection}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>scanner</th>
                {hasMetrics && (
                  <th className={styles.numeric}>{metricLabel}</th>
                )}
                {hasValidations && (
                  <th className={styles.numeric}>validation</th>
                )}
                <th className={styles.numeric}>results</th>
                <th className={styles.numeric}>errors</th>
                <th className={styles.numeric}>tokens/scan</th>
                <th className={styles.numeric}>tokens</th>
              </tr>
            </thead>
            <tbody>
              {scannerStats.map(
                ({
                  name,
                  scanner,
                  totalTokens,
                  tokensPerScan,
                  validationScore,
                  metricValue,
                }) => (
                  <tr key={name}>
                    <td>{name}</td>
                    {hasMetrics && (
                      <td className={styles.numeric}>
                        {metricValue !== null
                          ? metricValue === Math.floor(metricValue)
                            ? metricValue.toLocaleString()
                            : metricValue.toFixed(2)
                          : "-"}
                      </td>
                    )}
                    {hasValidations && (
                      <td className={styles.numeric}>
                        {validationScore !== null
                          ? validationScore.toFixed(2)
                          : "-"}
                      </td>
                    )}
                    <td className={styles.numeric}>
                      {scanner?.results || "-"}
                    </td>
                    <td className={styles.numeric}>{scanner?.errors || "-"}</td>
                    <td className={styles.numeric}>
                      {tokensPerScan ? tokensPerScan.toLocaleString() : "-"}
                    </td>
                    <td className={styles.numeric}>
                      {totalTokens ? totalTokens.toLocaleString() : "-"}
                    </td>
                  </tr>
                )
              )}
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

          {hasBatch && (
            <div className={styles.sidebarSection}>
              <div className={styles.sidebarTitle}>batch processing</div>
              <div className={styles.stat}>
                <span>pending:</span>
                <span>{metrics.batch_pending.toLocaleString()}</span>
              </div>
              {metrics.batch_failures > 0 && (
                <div className={styles.stat}>
                  <span>failures:</span>
                  <span className={styles.error}>
                    {metrics.batch_failures.toLocaleString()}
                  </span>
                </div>
              )}
              <div className={styles.stat}>
                <span>max age:</span>
                <span>{formatDuration(batchAge)}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface Props {
  scanId: string | undefined;
}

export const ActiveScanView: FC<Props> = ({ scanId }) => {
  const { loading, error, data: scanInfo } = useActiveScan(scanId);

  return (
    <div className={styles.scansList}>
      <LoadingBar loading={!!scanId && !!loading} />
      {error && (
        <ErrorPanel
          title="Error Loading Active Scan"
          error={{ message: error.message }}
        />
      )}
      {!scanId && !error && (
        <NoContentsPanel
          icon={ApplicationIcons.running}
          text="No scan started"
        />
      )}
      {scanId && !scanInfo && !error && !loading && (
        <NoContentsPanel
          icon={ApplicationIcons.running}
          text="Scan not found"
        />
      )}
      {scanInfo && !error && <ActiveScanCard info={scanInfo} />}
    </div>
  );
};
