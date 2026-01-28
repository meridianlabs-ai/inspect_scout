import clsx from "clsx";
import { FC, Fragment, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { VirtuosoHandle } from "react-virtuoso";

import { ApplicationIcons } from "../../../components/icons";
import { LabeledValue } from "../../../components/LabeledValue";
import { LiveVirtualList } from "../../../components/LiveVirtualList";
import { updateScannerParam } from "../../../router/url";
import { useStore } from "../../../state/store";
import { Status, ValidationResults } from "../../../types/api-types";
import { formatPercent, formatPrettyDecimal } from "../../../utils/format";
import { useSelectedScanner } from "../../hooks/useSelectedScanner";

import styles from "./ScannerSidebar.module.css";

export const ScannerSidebar: FC<{ selectedScan: Status }> = ({
  selectedScan,
}) => {
  const entries = toEntries(selectedScan);

  const scanListHandle = useRef<VirtuosoHandle | null>(null);
  const renderRow = useCallback(
    (index: number, entry: ScanResultsOutlineEntry) => {
      return <ScanResultsRow index={index} entry={entry} />;
    },
    []
  );

  return (
    <div className={clsx(styles.container)}>
      <LiveVirtualList<ScanResultsOutlineEntry>
        id={"scans-toc-list"}
        listHandle={scanListHandle}
        data={entries}
        renderRow={renderRow}
      />
    </div>
  );
};

const ScanResultsRow: FC<{ index: number; entry: ScanResultsOutlineEntry }> = ({
  index,
  entry,
}) => {
  const { data: selectedScanner } = useSelectedScanner();
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  const [searchParams, setSearchParams] = useSearchParams();
  const handleClick = useCallback(
    (title: string) => {
      setSelectedScanner(title);
      setSearchParams(updateScannerParam(searchParams, title), {
        replace: true,
      });
    },
    [setSelectedScanner, searchParams, setSearchParams]
  );

  return (
    <div
      className={clsx(
        styles.entry,
        selectedScanner === entry.title ? styles.selected : ""
      )}
      key={index}
      onClick={() => {
        handleClick(entry.title);
      }}
    >
      <div className={clsx(styles.titleBlock)}>
        <div className={clsx("text-size-large", styles.title)}>
          {entry.title}
        </div>
        {entry.params && entry.params.length > 0 && (
          <div className={clsx("text-size-smallest", styles.subTitle)}>
            {entry.params.join("")}
          </div>
        )}
      </div>

      <LabeledValue
        label="Positive Results"
        layout="row"
        className={clsx("text-size-smallest", styles.contents)}
      >
        {entry.results}
      </LabeledValue>

      {Object.keys(entry.metrics).map((key) => {
        return (
          <LabeledValue
            label={key}
            layout="row"
            className={clsx("text-size-smallest", styles.contents)}
          >
            {entry.metrics[key] !== undefined
              ? formatPrettyDecimal(entry.metrics[key])
              : "n/a"}
          </LabeledValue>
        );
      })}

      {!!entry.errors && (
        <LabeledValue
          label="Errors"
          layout="row"
          className={clsx("text-size-smallest", styles.contents)}
        >
          {entry.errors}
        </LabeledValue>
      )}

      {entry.validations !== undefined && (
        <LabeledValue
          label="Validation"
          layout="column"
          className={clsx("text-size-smallest", styles.validations)}
        >
          <NumericResultsTable
            results={entry.validations}
            formatter={(value) => formatPercent(value, 1)}
          />
        </LabeledValue>
      )}
    </div>
  );
};

interface ScanResultsOutlineEntry {
  icon?: string;
  title: string;
  tokens?: number;
  results: number;
  scans: number;
  validations?: Record<string, number>;
  errors?: number;
  params?: string[];
  metrics: Record<string, number>;
}

const toEntries = (status?: Status): ScanResultsOutlineEntry[] => {
  if (!status) {
    return [];
  }
  const entries: ScanResultsOutlineEntry[] = [];
  const scanners = status.summary.scanners || {};
  for (const scanner of Object.keys(scanners)) {
    // The summary
    const summary = scanners[scanner];

    // The configuration
    const scanInfo = status.spec.scanners[scanner];

    const formattedParams: string[] = [];
    if (scanInfo) {
      const params = scanInfo.params || {};
      for (const [key, value] of Object.entries(params)) {
        formattedParams.push(`${key}=${JSON.stringify(value)}`);
      }
    }

    const validations = resolveValidations(summary?.validation);

    const metrics =
      summary &&
      summary.metrics &&
      Object.keys(summary.metrics).includes(scanner)
        ? summary.metrics[scanner]!
        : {};

    entries.push({
      icon: ApplicationIcons.scorer,
      title: scanner,
      results: summary?.results || 0,
      scans: summary?.scans || 0,
      tokens: summary?.tokens,
      errors: summary?.errors,
      params: formattedParams,
      validations: validations,
      metrics,
    });
  }
  return entries;
};

/**
 * Extract validation metrics from pre-computed ValidationResults.
 */
const resolveValidations = (
  validation: ValidationResults | undefined | null
): Record<string, number> | undefined => {
  if (!validation?.metrics) {
    return undefined;
  }

  const m = validation.metrics;
  const result: Record<string, number> = {};

  // Add metrics in display order: accuracy, precision, recall, f1
  if (m.accuracy !== null && m.accuracy !== undefined) {
    result["accuracy"] = m.accuracy;
  }
  if (m.precision !== null && m.precision !== undefined) {
    result["precision"] = m.precision;
  }
  if (m.recall !== null && m.recall !== undefined) {
    result["recall"] = m.recall;
  }
  if (m.f1 !== null && m.f1 !== undefined) {
    result["f1"] = m.f1;
  }

  // Return undefined if we couldn't extract any metrics
  if (Object.keys(result).length === 0) {
    return undefined;
  }

  return result;
};

const NumericResultsTable: FC<{
  results: Record<string, number>;
  maxrows?: number;
  formatter?: (value: number) => string;
}> = ({ results: validations, formatter }) => {
  return (
    <div className={clsx(styles.numericResultTable)}>
      {Object.entries(validations).map(([key, value]) => (
        <Fragment key={key}>
          <div className={clsx(styles.numericResultKey)}>{key}</div>
          <div className={clsx(styles.numericResultValue)}>
            {formatter ? formatter(value) : value}
          </div>
        </Fragment>
      ))}
    </div>
  );
};
