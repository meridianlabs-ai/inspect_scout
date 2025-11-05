import clsx from "clsx";
import { useStore } from "../../../state/store";
import { FC, useCallback, useRef } from "react";

import styles from "./ScanResultsTOC.module.css";
import { Results } from "../../../types";
import { ApplicationIcons } from "../../appearance/icons";
import { useSelectedScanner } from "./hooks";
import { LiveVirtualList } from "../../../components/LiveVirtualList";
import { VirtuosoHandle } from "react-virtuoso";
import { LabeledValue } from "../../../components/LabeledValue";

interface TOCEntry {
  icon?: string;
  title: string;
  tokens?: number;
  results: number;
  scans: number;
  validations?: number;
  errors?: number;
}

const toEntries = (results?: Results): TOCEntry[] => {
  if (!results) {
    return [];
  }
  const entries: TOCEntry[] = [];
  for (const scanner of Object.keys(results.summary.scanners)) {
    const summary = results.summary.scanners[scanner];
    entries.push({
      icon: ApplicationIcons.scorer,
      title: scanner,
      results: summary?.results || 0,
      scans: summary?.scans || 0,
      tokens: summary?.tokens,
      errors: summary?.errors,
    });
  }
  return entries;
};

export const ScanResultsTOC: FC = () => {
  const results = useStore((state) => state.selectedResults);
  const entries = toEntries(results);

  const scanListHandle = useRef<VirtuosoHandle | null>(null);
  const renderRow = useCallback((index: number, entry: TOCEntry) => {
    return <ScanResultsRow index={index} entry={entry} />;
  }, []);

  return (
    <div className={clsx(styles.container)}>
      <LiveVirtualList<TOCEntry>
        id={"scans-toc-list"}
        listHandle={scanListHandle}
        data={entries}
        renderRow={renderRow}
      />
    </div>
  );
};

const ScanResultsRow: FC<{ index: number; entry: TOCEntry }> = ({
  index,
  entry,
}) => {
  const selectedScanner = useSelectedScanner();
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  const handleClick = useCallback(
    (title: string) => {
      setSelectedScanner(title);
    },
    [setSelectedScanner]
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
      <div className={clsx("text-size-large", styles.title)}>{entry.title}</div>
      <LabeledValue
        label="Scans"
        layout="row"
        className={clsx("text-size-smallest")}
      >
        {entry.scans}
      </LabeledValue>

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
