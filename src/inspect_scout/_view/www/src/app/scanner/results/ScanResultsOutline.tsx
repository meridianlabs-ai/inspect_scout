import clsx from "clsx";
import { FC, useCallback, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { VirtuosoHandle } from "react-virtuoso";

import { LabeledValue } from "../../../components/LabeledValue";
import { LiveVirtualList } from "../../../components/LiveVirtualList";
import { updateScannerParam } from "../../../router/url";
import { useStore } from "../../../state/store";
import { Results } from "../../../types";
import { ApplicationIcons } from "../../appearance/icons";
import { useSelectedResults, useSelectedScanner } from "../../hooks";

import styles from "./ScanResultsOutline.module.css";

export const ScanResultsOutline: FC = () => {
  const results = useSelectedResults();
  const entries = toEntries(results);

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
  const selectedScanner = useSelectedScanner();
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
        {entry.params.length > 0 && (
          <div className={clsx("text-size-smallest", styles.subTitle)}>
            {entry.params.join("")}
          </div>
        )}
      </div>

      <LabeledValue
        label="Results"
        layout="row"
        className={clsx("text-size-smallest")}
      >
        {entry.results}
      </LabeledValue>

      {!!entry.errors && (
        <LabeledValue
          label="Errors"
          layout="row"
          className={clsx("text-size-smallest")}
        >
          {entry.errors}
        </LabeledValue>
      )}

      {!!entry.validations && (
        <LabeledValue
          label="Validations"
          layout="row"
          className={clsx("text-size-smallest")}
        >
          {entry.validations}
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
  validations?: number;
  errors?: number;
  params?: string[];
}

const toEntries = (results?: Results): ScanResultsOutlineEntry[] => {
  if (!results) {
    return [];
  }
  const entries: ScanResultsOutlineEntry[] = [];
  for (const scanner of Object.keys(results.summary.scanners)) {
    // The summary
    const summary = results.summary.scanners[scanner];

    // The configuration
    const scanInfo = results.spec.scanners[scanner];

    const formattedParams: string[] = [];
    if (scanInfo) {
      const params = scanInfo.params || {};
      for (const [key, value] of Object.entries(params)) {
        formattedParams.push(`${key}=${JSON.stringify(value)}`);
      }
    }

    entries.push({
      icon: ApplicationIcons.scorer,
      title: scanner,
      results: summary?.results || 0,
      scans: summary?.scans || 0,
      tokens: summary?.tokens,
      errors: summary?.errors,
      params: formattedParams,
    });
  }
  return entries;
};
