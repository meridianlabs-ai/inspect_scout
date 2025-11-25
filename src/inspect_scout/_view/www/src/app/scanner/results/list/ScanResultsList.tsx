import { ColumnTable } from "arquero";
import clsx from "clsx";
import { FC, useCallback, useEffect, useMemo, useRef } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { VirtuosoHandle } from "react-virtuoso";

import { ActivityBar } from "../../../../components/ActivityBar";
import { LiveVirtualList } from "../../../../components/LiveVirtualList";
import { NoContentsPanel } from "../../../../components/NoContentsPanel";
import {
  getRelativePathFromParams,
  parseScanResultPath,
  scanResultRoute,
} from "../../../../router/url";
import { useStore } from "../../../../state/store";
import { basename } from "../../../../utils/path";
import { useScannerPreviews } from "../../../hooks";
import { ScannerCore, SortColumn } from "../../../types";
import {
  resultIdentifier,
  resultIdentifierStr,
  resultLog,
} from "../../../utils/results";
import {
  kFilterAllResults,
  kFilterPositiveResults,
} from "../ScanResultsFilter";

import { ScanResultsHeader } from "./ScanHeader";
import { ScanResultGroup } from "./ScanResultsGroup";
import styles from "./ScanResultsList.module.css";
import { ScanResultsRow } from "./ScanResultsRow";

export interface GridDescriptor {
  gridStyle: Record<string, string>;
  columns: string[];
}

interface ScanResultsListProps {
  id: string;
  columnTable?: ColumnTable;
}
export const ScanResultsList: FC<ScanResultsListProps> = ({
  id,
  columnTable,
}) => {
  // Url data
  const navigate = useNavigate();
  const params = useParams<{ "*": string }>();
  const [searchParams] = useSearchParams();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath } = parseScanResultPath(relativePath);

  // Data
  const { data: scannerSummaries, isLoading } = useScannerPreviews(columnTable);
  const isLoadingData = useStore((state) => state.loadingData);
  const busy = isLoading || isLoadingData;

  // Options / State
  const listHandle = useRef<VirtuosoHandle | null>(null);
  const selectedScanResult = useStore((state) => state.selectedScanResult);
  const selectedFilter = useStore((state) => state.selectedFilter);
  const groupResultsBy = useStore((state) => state.groupResultsBy);
  const scansSearchText = useStore((state) => state.scansSearchText);
  const selectedStatus = useStore((state) => state.selectedScanStatus);

  // Setters
  const setVisibleScannerResults = useStore(
    (state) => state.setVisibleScannerResults
  );
  const setSelectedScanResult = useStore(
    (state) => state.setSelectedScanResult
  );
  const setSelectedFilter = useStore((state) => state.setSelectedFilter);

  // Sorting
  const sortResults = useStore((state) => state.sortResults);
  const setSortResults = useStore((state) => state.setSortResults);

  useEffect(() => {
    if (selectedFilter === undefined && selectedStatus?.complete === false) {
      setSelectedFilter(kFilterAllResults);
    }
  }, [selectedStatus, selectedFilter, setSelectedFilter]);

  // Apply text filtering to the scanner summaries
  const filteredSummaries = useMemo(() => {
    let textFiltered = scannerSummaries;
    if (scansSearchText && scansSearchText.length > 0) {
      const lowerSearch = scansSearchText.toLowerCase();
      textFiltered = scannerSummaries.filter((s) => {
        const idStr = resultIdentifierStr(s) || "";
        const logStr = resultLog(s) || "";
        const labelStr = s.label || "";
        return (
          idStr.toLowerCase().includes(lowerSearch) ||
          logStr.toLowerCase().includes(lowerSearch) ||
          labelStr.toLowerCase().includes(lowerSearch)
        );
      });
    }

    // Filter positives results if needed
    const resultsFiltered =
      selectedFilter === kFilterPositiveResults || selectedFilter === undefined
        ? textFiltered.filter((s) => !!s.value)
        : textFiltered;

    // Return filtered sorted summaries
    if (sortResults === undefined || sortResults.length === 0) {
      return resultsFiltered;
    } else {
      return [...resultsFiltered].sort((a, b) =>
        sortByColumns(a, b, sortResults)
      );
    }
  }, [scannerSummaries, selectedFilter, scansSearchText, sortResults]);

  // Set the default sort order when the filter changes (if there isn't an explicit order)
  useEffect(() => {
    if (filteredSummaries.length === 0 || sortResults) {
      return;
    }

    if (
      selectedFilter === kFilterAllResults &&
      filteredSummaries.some((s) => !!s.scanError)
    ) {
      // Default sort for error filter: errors first, then by identifier
      setSortResults([{ column: "Error", direction: "desc" }]);
    }
  }, [sortResults, selectedFilter, filteredSummaries]);

  // Compute the optimal column layout based on the current data
  const gridDescriptor = useMemo(() => {
    const descriptor = optimalColumnLayout(filteredSummaries);
    return descriptor;
  }, [filteredSummaries]);

  interface ResultGroup {
    type: "group";
    label: string;
  }

  // Type guard to check if entry is a ResultGroup
  const isResultGroup = (
    entry: ResultGroup | ScannerCore
  ): entry is ResultGroup => {
    return "type" in entry && entry.type === "group";
  };

  const rows: Array<ResultGroup | ScannerCore> = useMemo(() => {
    // No grouping
    if (!groupResultsBy || groupResultsBy === "none") {
      return filteredSummaries;
    }

    const groups = new Map<string, ScannerCore[]>();

    for (const item of filteredSummaries) {
      // Insert group header when group changes
      const groupKey =
        groupResultsBy === "source"
          ? basename(resultLog(item) || "") || "Unknown"
          : groupResultsBy === "label"
            ? item.label || "Unlabeled"
            : resultIdentifierStr(item) || "Unknown";

      // Insert group header when group changes
      if (!groups.has(groupKey)) {
        groups.set(groupKey, []);
      }
      groups.get(groupKey)?.push(item);
    }

    // Sort group keys alphabetically and emit
    const sortedGroupKeys = Array.from(groups.keys()).sort();
    const result: Array<ResultGroup | ScannerCore> = [];

    for (const groupKey of sortedGroupKeys) {
      result.push({ type: "group", label: groupKey });
      result.push(...(groups.get(groupKey) || []));
    }

    return result;
  }, [filteredSummaries, groupResultsBy]);

  const currentIndex = useMemo(() => {
    if (selectedScanResult) {
      return filteredSummaries.findIndex((s) => s.uuid === selectedScanResult);
    }
    return -1;
  }, [selectedScanResult, filteredSummaries]);

  const handleNext = useCallback(() => {
    if (currentIndex >= 0 && currentIndex < filteredSummaries.length - 1) {
      const nextResult = filteredSummaries[currentIndex + 1];
      if (nextResult?.uuid) {
        setSelectedScanResult(nextResult.uuid);
      }
    }
  }, [currentIndex, filteredSummaries, setSelectedScanResult]);

  const handlePrevious = useCallback(() => {
    if (currentIndex > 0) {
      const previousResult = filteredSummaries[currentIndex - 1];
      if (previousResult?.uuid) {
        setSelectedScanResult(previousResult.uuid);
      }
    }
  }, [currentIndex, filteredSummaries, setSelectedScanResult]);

  const handleEnter = useCallback(
    (newWindow?: boolean) => {
      const selectedResult = filteredSummaries[currentIndex];
      const route = scanResultRoute(
        scanPath,
        selectedResult?.uuid,
        searchParams
      );
      if (newWindow) {
        window.open(route, "_blank");
      } else {
        void navigate(route);
      }
    },
    [currentIndex, filteredSummaries, navigate, scanPath, searchParams]
  );

  const hasPrevious = currentIndex > 0;
  const hasNext =
    currentIndex >= 0 && currentIndex < filteredSummaries.length - 1;

  // Global keydown handler for keyboard shortcuts
  useEffect(() => {
    const handleGlobalKeyDown = (e: globalThis.KeyboardEvent) => {
      // Don't handle keyboard events if focus is on an input, textarea, or select element
      const activeElement = document.activeElement;
      const isInputFocused =
        activeElement &&
        (activeElement.tagName === "INPUT" ||
          activeElement.tagName === "TEXTAREA" ||
          activeElement.tagName === "SELECT");

      if (!isInputFocused) {
        // Navigation shortcuts (only when not in an input field)
        if (e.key === "ArrowUp") {
          if (e.metaKey || e.ctrlKey) {
            // Cmd/Ctrl+ArrowUp: Go to first item
            if (filteredSummaries.length > 0 && filteredSummaries[0]?.uuid) {
              e.preventDefault();
              setSelectedScanResult(filteredSummaries[0].uuid);
            }
          } else if (hasPrevious) {
            e.preventDefault();
            handlePrevious();
          }
        } else if (e.key === "ArrowDown") {
          if (e.metaKey || e.ctrlKey) {
            // Cmd/Ctrl+ArrowDown: Go to last item
            if (filteredSummaries.length > 0) {
              e.preventDefault();
              const uuid =
                filteredSummaries[filteredSummaries.length - 1]?.uuid;
              if (uuid) {
                setSelectedScanResult(uuid);
              }
            }
          } else if (hasNext) {
            e.preventDefault();
            handleNext();
          }
        } else if (e.key === "Enter") {
          e.preventDefault();
          handleEnter(e.metaKey || e.ctrlKey);
        }
      }
    };

    // Use capture phase to catch event before it reaches other handlers
    document.addEventListener("keydown", handleGlobalKeyDown, true);

    return () => {
      document.removeEventListener("keydown", handleGlobalKeyDown, true);
    };
  }, [
    hasPrevious,
    hasNext,
    handlePrevious,
    handleNext,
    handleEnter,
    filteredSummaries,
    setSelectedScanResult,
  ]);

  useEffect(() => {
    // Only set if nothing is selected and we have results
    if (
      !selectedScanResult &&
      filteredSummaries.length > 0 &&
      filteredSummaries[0]?.uuid
    ) {
      setSelectedScanResult(filteredSummaries[0].uuid);
    }
  }, [filteredSummaries, selectedScanResult, setSelectedScanResult]);

  useEffect(() => {
    setVisibleScannerResults(filteredSummaries);
  }, [filteredSummaries, setVisibleScannerResults]);

  const selectedItemIndex = useMemo(() => {
    if (selectedScanResult) {
      const selectedIndex = filteredSummaries.findIndex(
        (s) => s.uuid === selectedScanResult
      );
      if (selectedIndex >= 0) {
        return selectedIndex;
      }
    }
    return undefined;
  }, [selectedScanResult, filteredSummaries]);

  useEffect(() => {
    setTimeout(() => {
      listHandle.current?.scrollToIndex({
        index: selectedItemIndex ?? 0,
        align: "center",
        behavior: "auto",
      });
    }, 5);
  }, [selectedItemIndex]);

  const renderRow = useCallback(
    (index: number, entry: ScannerCore | ResultGroup) => {
      if (isResultGroup(entry)) {
        return <ScanResultGroup group={entry.label} />;
      }

      // TypeScript now knows entry is ScannerCore here
      return (
        <ScanResultsRow
          index={index}
          entry={entry}
          gridDescriptor={gridDescriptor}
        />
      );
    },
    [gridDescriptor, isResultGroup]
  );

  let noContentMessage: string | undefined = undefined;
  if (!busy && scannerSummaries.length === 0) {
    noContentMessage = "No scan results are available.";
  } else if (
    !busy &&
    filteredSummaries.length === 0 &&
    selectedFilter !== kFilterAllResults &&
    !scansSearchText
  ) {
    noContentMessage = "No positive scan results were found.";
  } else if (!busy && filteredSummaries.length === 0) {
    noContentMessage = "No scan results match the current filter.";
  }

  return (
    <div className={clsx(styles.container)}>
      <ScanResultsHeader gridDescriptor={gridDescriptor} />
      <ActivityBar animating={isLoading} />
      {noContentMessage && <NoContentsPanel text={noContentMessage} />}
      {!busy && filteredSummaries.length > 0 && (
        <LiveVirtualList<ScannerCore | ResultGroup>
          id={id}
          listHandle={listHandle}
          data={rows}
          renderRow={renderRow}
          className={clsx(styles.list)}
          animation={false}
        />
      )}
    </div>
  );
};

// Sorts scan results by multiple columns and directions.
// Applies sorting rules in order, falling back to the next rule if values are equal.
const sortByColumns = (
  a: ScannerCore,
  b: ScannerCore,
  sortColumns: SortColumn[]
): number => {
  for (const sortCol of sortColumns) {
    let comparison = 0;

    switch (sortCol.column.toLowerCase()) {
      case "id": {
        const identifierA = resultIdentifier(a);
        const identifierB = resultIdentifier(b);
        comparison = identifierA.id.localeCompare(identifierB.id);
        if (comparison === 0 && identifierA.epoch && identifierB.epoch) {
          comparison = identifierA.epoch.localeCompare(identifierB.epoch);
        }
        break;
      }
      case "explanation": {
        const explA = a.explanation || "";
        const explB = b.explanation || "";
        comparison = explA.localeCompare(explB);
        break;
      }
      case "label": {
        const labelA = a.label || "";
        const labelB = b.label || "";
        comparison = labelA.localeCompare(labelB);
        break;
      }
      case "value": {
        const valueA =
          a.value !== null && a.value !== undefined ? String(a.value) : "";
        const valueB =
          b.value !== null && b.value !== undefined ? String(b.value) : "";
        comparison = valueA.localeCompare(valueB);
        break;
      }
      case "error": {
        const errorA = a.scanError || "";
        const errorB = b.scanError || "";
        comparison = errorA.localeCompare(errorB);
        break;
      }
      default:
        // Unknown column, skip
        continue;
    }

    // Apply direction (asc or desc)
    if (comparison !== 0) {
      return sortCol.direction === "asc" ? comparison : -comparison;
    }
  }

  // All comparisons are equal
  return 0;
};

const optimalColumnLayout = (
  scannerSummaries: ScannerCore[]
): GridDescriptor => {
  const columns: string[] = [];
  const gridColParts: string[] = [];

  // The id column
  columns.push("id");
  const maxIdLen = scannerSummaries.reduce((max, s) => {
    return Math.max(max, resultIdentifier(s).id.length);
  }, 0);
  gridColParts.push(
    `minmax(${Math.min(Math.max(maxIdLen * 8, 50), 250)}px, 1fr)`
  );

  // The explanation column, if any explanations exist
  const hasExplanation = scannerSummaries.some((s) => !!s.explanation);
  if (hasExplanation) {
    columns.push("explanation");
    gridColParts.push("10fr");
  }

  // The label column, if any labels exist
  const hasLabel = scannerSummaries.some((s) => !!s.label);
  if (hasLabel) {
    columns.push("label");

    const maxlabelLen = scannerSummaries.reduce((max, s) => {
      return Math.max(max, resultIdentifier(s).id.length);
    }, 0);
    gridColParts.push(
      `minmax(${Math.min(Math.max(maxlabelLen * 4, 50), 250)}px, 1fr)`
    );
  }

  // The value column
  columns.push("value");
  const hasValueObjs = scannerSummaries.some((s) => s.valueType === "object");
  if (hasValueObjs) {
    gridColParts.push("5fr");
  } else {
    const maxValueLen = scannerSummaries.reduce((max: number, s) => {
      if (s.valueType === "array") {
        const len = (s.value as unknown[]).reduce<number>((prev, val) => {
          const valStr = val !== undefined && val !== null ? String(val) : "";
          return Math.max(prev, valStr.length);
        }, 0);
        return Math.max(max, len);
      } else {
        const valStr =
          s.value !== undefined && s.value !== null ? String(s.value) : "";
        return Math.max(max, valStr.length);
      }
    }, 0);
    gridColParts.push(
      `minmax(${Math.min(Math.max(maxValueLen * 4, 50), 300)}px, 1fr)`
    );
  }

  const hasErrors = scannerSummaries.some((s) => !!s.scanError);
  if (hasErrors) {
    const maxErrorLen = scannerSummaries.reduce((max, s) => {
      return Math.max(max, s.scanError ? s.scanError.length : 0);
    }, 0);

    columns.push("error");
    gridColParts.push(
      `minmax(${Math.min(Math.max(maxErrorLen * 4, 50), 250)}px, 1fr)`
    );
  }

  // Special case - if there is only an id and value column, divide space evenly
  if (columns.length === 2 && columns[0] === "id" && columns[1] === "value") {
    gridColParts[0] = "1fr";
    gridColParts[1] = "1fr";
  }

  return {
    gridStyle: {
      gridTemplateColumns: gridColParts.join(" "),
      display: "grid",
      columnGap: "0.5rem",
    },
    columns,
  };
};
