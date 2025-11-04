import clsx from "clsx";
import { useStore } from "../../../state/store";
import { FC, useCallback } from "react";

import styles from "./ScanResultsTOC.module.css";
import { Results } from "../../../types";
import { ApplicationIcons } from "../../appearance/icons";
import { useSelectedScanner } from "./hooks";

interface TOCEntry {
  icon?: string;
  title: string;
  count: number;
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
      count: summary?.results || 0,
    });
  }
  return entries;
};

export const ScanResultsTOC: FC = () => {
  const results = useStore((state) => state.selectedResults);
  const entries = toEntries(results);

  const selectedScanner = useSelectedScanner();

  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  const handleClick = useCallback(
    (title: string) => {
      setSelectedScanner(title);
    },
    [setSelectedScanner]
  );

  return (
    <div className={clsx(styles.container)}>
      {entries.map((entry) => {
        return (
          <div
            key={entry.title}
            className={clsx(
              styles.entry,
              "text-size-smaller",
              selectedScanner === entry.title ? styles.selected : null
            )}
            onClick={() => {
              handleClick(entry.title);
            }}
          >
            <div>
              {entry.icon && <i className={clsx(styles.icon, entry.icon)} />}
            </div>
            <div className={clsx(styles.title)}>{entry.title}</div>
            <div className={clsx(styles.count)}>({entry.count} results)</div>
          </div>
        );
      })}
    </div>
  );
};
