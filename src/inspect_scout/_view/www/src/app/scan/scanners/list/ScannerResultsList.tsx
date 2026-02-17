import { ColumnTable } from "arquero";
import clsx from "clsx";
import { FC, useCallback, useEffect, useMemo, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { VirtuosoHandle } from "react-virtuoso";

import { LiveVirtualList } from "../../../../components/LiveVirtualList";
import { LoadingBar } from "../../../../components/LoadingBar";
import { NoContentsPanel } from "../../../../components/NoContentsPanel";
import { useLoggingNavigate } from "../../../../debugging/navigationDebugging";
import { scanResultRoute } from "../../../../router/url";
import { useStore } from "../../../../state/store";
import { Status } from "../../../../types/api-types";
import { basename } from "../../../../utils/path";
import { useScanResultSummaries } from "../../../hooks/useScanResultSummaries";
import { useScanRoute } from "../../../hooks/useScanRoute";
import { ScanResultSummary, SortColumn } from "../../../types";
import {
  resultIdentifier,
  resultIdentifierStr,
  resultLog,
} from "../../../utils/results";
import {
  kFilterAllResults,
  kFilterPositiveResults,
} from "../results/ScannerResultsFilter";

import { ScannerResultsGroup } from "./ScannerResultsGroup";
import { ScannerResultsHeader } from "./ScannerResultsHeader";
import styles from "./ScannerResultsList.module.css";
import { ScannerResultsRow } from "./ScannerResultsRow";

export interface GridDescriptor {
  gridStyle: Record<string, string>;
  columns: string[];
}

interface ResultGroup {
  type: "group";
  label: string;
}

// Type guard to check if entry is a ResultGroup
const isResultGroup = (
  entry: ResultGroup | ScanResultSummary
): entry is ResultGroup => {
  return "type" in entry && entry.type === "group";
};

interface ScannerResultsListProps {
  id: string;
  columnTable?: ColumnTable;
  selectedScan: Status;
}
export const ScannerResultsList: FC<ScannerResultsListProps> = ({
  id,
  columnTable,
  selectedScan,
}) => {
  // Url data
  const navigate = useLoggingNavigate("ScannerResultsList");
  const [searchParams] = useSearchParams();
  const { scansDir, scanPath } = useScanRoute();

  // Data
  const { data: scannerSummaries, isLoading } =
    useScanResultSummaries(columnTable);

  // Options / State
  const listHandle = useRef<VirtuosoHandle | null>(null);
  const selectedScanResult = useStore((state) => state.selectedScanResult);
  const selectedFilter = useStore((state) => state.selectedFilter);
  const groupResultsBy = useStore((state) => state.groupResultsBy);
  const scansSearchText = useStore((state) => state.scansSearchText);

  // Setters
  const setVisibleScannerResults = useStore(
    (state) => state.setVisibleScannerResults
  );
  const setVisibleScannerResultsCount = useStore(
    (state) => state.setVisibleScannerResultsCount
  );
  const setSelectedScanResult = useStore(
    (state) => state.setSelectedScanResult
  );
  const setSelectedFilter = useStore((state) => state.setSelectedFilter);

  // Sorting
  const sortResults = useStore((state) => state.sortResults);
  const setSortResults = useStore((state) => state.setSortResults);

  useEffect(() => {
    if (selectedFilter === undefined && selectedScan.complete === false) {
      setSelectedFilter(kFilterAllResults);
    }
  }, [selectedScan, selectedFilter, setSelectedFilter]);

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
    } else if (
      filteredSummaries.some((s) => s.validationResult !== undefined)
    ) {
      // Default sort for validations: validations first, then by identifier
      setSortResults([{ column: "Validation", direction: "desc" }]);
    }
  }, [sortResults, selectedFilter, filteredSummaries, setSortResults]);

  // Compute the optimal column layout based on the current data
  const gridDescriptor = useMemo(() => {
    const descriptor = optimalColumnLayout(filteredSummaries);
    return descriptor;
  }, [filteredSummaries]);

  const rows: Array<ResultGroup | ScanResultSummary> = useMemo(() => {
    // No grouping
    if (!groupResultsBy || groupResultsBy === "none") {
      return filteredSummaries;
    }

    const groups = new Map<string | number, ScanResultSummary[]>();

    for (const item of filteredSummaries) {
      // Insert group header when group changes
      const groupKey =
        groupResultsBy === "source"
          ? basename(resultLog(item) || "") || "Unknown"
          : groupResultsBy === "label"
            ? item.label || "Unlabeled"
            : groupResultsBy === "epoch"
              ? (item.transcriptMetadata.epoch as number)
              : groupResultsBy === "model"
                ? item.transcriptModel || "Unknown"
                : resultIdentifierStr(item) || "Unknown";

      // Insert group header when group changes
      if (!groups.has(groupKey)) {
        groups.set(groupKey, []);
      }
      groups.get(groupKey)?.push(item);
    }

    // Sort group keys (numerically if they're numbers, alphabetically otherwise)
    const sortedGroupKeys = Array.from(groups.keys()).sort((a, b) => {
      // If both are numbers, sort numerically
      if (typeof a === "number" && typeof b === "number") {
        return a - b;
      }
      // Otherwise, sort as strings
      return String(a).localeCompare(String(b));
    });
    const result: Array<ResultGroup | ScanResultSummary> = [];

    for (const groupKey of sortedGroupKeys) {
      const label =
        groupResultsBy === "epoch" ? `Epoch ${groupKey}` : String(groupKey);
      result.push({ type: "group", label: label });
      result.push(...(groups.get(groupKey) || []));
    }

    return result;
  }, [filteredSummaries, groupResultsBy]);

  const currentIndex = useMemo(() => {
    if (selectedScanResult) {
      return filteredSummaries.findIndex(
        (s) => s.identifier === selectedScanResult
      );
    }
    return -1;
  }, [selectedScanResult, filteredSummaries]);

  const handleNext = useCallback(() => {
    if (currentIndex >= 0 && currentIndex < filteredSummaries.length - 1) {
      const nextResult = filteredSummaries[currentIndex + 1];
      if (nextResult?.identifier) {
        setSelectedScanResult(nextResult.identifier);
      }
    }
  }, [currentIndex, filteredSummaries, setSelectedScanResult]);

  const handlePrevious = useCallback(() => {
    if (currentIndex > 0) {
      const previousResult = filteredSummaries[currentIndex - 1];
      if (previousResult?.identifier) {
        setSelectedScanResult(previousResult.identifier);
      }
    }
  }, [currentIndex, filteredSummaries, setSelectedScanResult]);

  const handleEnter = useCallback(
    (newWindow?: boolean) => {
      const selectedResult = filteredSummaries[currentIndex];
      if (!scansDir) {
        return;
      }
      const route = scanResultRoute(
        scansDir,
        scanPath,
        selectedResult?.identifier,
        searchParams
      );
      if (newWindow) {
        window.open(route, "_blank");
      } else {
        void navigate(route);
      }
    },
    [
      currentIndex,
      filteredSummaries,
      navigate,
      scanPath,
      searchParams,
      scansDir,
    ]
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
            if (
              filteredSummaries.length > 0 &&
              filteredSummaries[0]?.identifier
            ) {
              e.preventDefault();
              setSelectedScanResult(filteredSummaries[0].identifier);
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
                filteredSummaries[filteredSummaries.length - 1]?.identifier;
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
      filteredSummaries[0]?.identifier
    ) {
      setSelectedScanResult(filteredSummaries[0].identifier);
    }
  }, [filteredSummaries, selectedScanResult, setSelectedScanResult]);

  useEffect(() => {
    setVisibleScannerResults(filteredSummaries);
    setVisibleScannerResultsCount(filteredSummaries.length);
  }, [
    filteredSummaries,
    setVisibleScannerResults,
    setVisibleScannerResultsCount,
  ]);

  const selectedItemIndex = useMemo(() => {
    if (selectedScanResult) {
      const selectedIndex = filteredSummaries.findIndex(
        (s) => s.identifier === selectedScanResult
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
    (index: number, entry: ScanResultSummary | ResultGroup) => {
      if (isResultGroup(entry)) {
        return <ScannerResultsGroup group={entry.label} />;
      }

      return (
        <ScannerResultsRow
          index={index}
          summary={entry}
          gridDescriptor={gridDescriptor}
        />
      );
    },
    [gridDescriptor]
  );

  let noContentMessage: string | undefined = undefined;
  if (!isLoading && scannerSummaries.length === 0) {
    noContentMessage = "No scan results are available.";
  } else if (
    !isLoading &&
    filteredSummaries.length === 0 &&
    selectedFilter !== kFilterAllResults &&
    !scansSearchText
  ) {
    noContentMessage = "No positive scan results were found.";
  } else if (!isLoading && filteredSummaries.length === 0) {
    noContentMessage = "No scan results match the current filter.";
  }

  return (
    <div className={clsx(styles.container)}>
      <ScannerResultsHeader gridDescriptor={gridDescriptor} />
      <LoadingBar loading={isLoading} />
      {noContentMessage && <NoContentsPanel text={noContentMessage} />}
      {!isLoading && filteredSummaries.length > 0 && (
        <LiveVirtualList<ScanResultSummary | ResultGroup>
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
  a: ScanResultSummary,
  b: ScanResultSummary,
  sortColumns: SortColumn[]
): number => {
  for (const sortCol of sortColumns) {
    let comparison = 0;

    switch (sortCol.column.toLowerCase()) {
      case "id": {
        const identifierA = resultIdentifier(a);
        const identifierB = resultIdentifier(b);

        if (
          typeof identifierA.id === "number" &&
          typeof identifierB.id === "number"
        ) {
          comparison = identifierA.id - identifierB.id;
        } else {
          comparison = String(identifierA.id).localeCompare(
            String(identifierB.id)
          );
        }

        if (comparison === 0 && identifierA.epoch && identifierB.epoch) {
          comparison = identifierA.epoch - identifierB.epoch;
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
      case "validation": {
        const validationA = a.validationResult ? 1 : 0;
        const validationB = b.validationResult ? 1 : 0;
        comparison = validationA - validationB;
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
  scannerSummaries: ScanResultSummary[]
): GridDescriptor => {
  const columns: string[] = [];
  const gridColParts: string[] = [];

  // The explanation column, if any explanations exist
  columns.push("result");
  gridColParts.push("10fr");

  // The label column, if any labels exist
  const hasLabel = scannerSummaries.some((s) => !!s.label);
  if (hasLabel) {
    columns.push("label");

    const maxlabelLen = scannerSummaries.reduce((max, s) => {
      return Math.max(max, s.label ? s.label.length : 0);
    }, 0);
    gridColParts.push(
      `minmax(${Math.min(Math.max(maxlabelLen * 5, 75), 250)}px, 1fr)`
    );
  }

  // The value column
  columns.push("value");
  const hasValueObjs = scannerSummaries.some((s) => s.valueType === "object");
  if (hasValueObjs) {
    const obj = scannerSummaries[0]?.value;
    if (obj && typeof obj === "object" && !Array.isArray(obj)) {
      // measure the length of the longest key
      const maxKeyLen = Object.keys(obj).reduce((max, key) => {
        return Math.max(max, key.length);
      }, 0);

      // measure the length of the longest value
      const maxValueLen = Object.values(obj).reduce((max, val) => {
        const valStr = val !== undefined && val !== null ? String(val) : "";
        return Math.max(max, valStr.length);
      }, 0);

      gridColParts.push(
        `minmax(${Math.min(Math.max((maxKeyLen + maxValueLen) * 10, 135), 200)}px, 4fr)`
      );
    } else {
      gridColParts.push("3fr");
    }
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

  const hasValidations = scannerSummaries.some(
    (s) => s.validationResult !== undefined && s.validationResult !== null
  );
  if (hasValidations) {
    columns.push("validations");
    gridColParts.push("minmax(80px, 1fr)");
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
      columnGap: "1rem",
    },
    columns,
  };
};
