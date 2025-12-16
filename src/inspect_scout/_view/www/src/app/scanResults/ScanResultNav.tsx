import clsx from "clsx";
import { FC, useEffect, useMemo } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import {
  getRelativePathFromParams,
  parseScanResultPath,
  scanResultRoute,
} from "../../router/url";
import { useStore } from "../../state/store";
import { ApplicationIcons } from "../appearance/icons";
import { IdentifierInfo, resultIdentifier } from "../utils/results";

import styles from "./ScanResultNav.module.css";

export const ScanResultNav: FC = () => {
  const navigate = useNavigate();
  const params = useParams<{ "*": string }>();
  const [searchParams] = useSearchParams();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath } = parseScanResultPath(relativePath);
  const { scanResultUuid } = parseScanResultPath(relativePath);

  const visibleScannerResults = useStore(
    (state) => state.visibleScannerResults
  );

  const currentIndex = useMemo(() => {
    if (!visibleScannerResults) {
      return -1;
    }
    return visibleScannerResults.findIndex((s) => s.uuid === scanResultUuid);
  }, [visibleScannerResults, scanResultUuid]);

  const hasPrevious = currentIndex > 0;
  const hasNext =
    visibleScannerResults &&
    currentIndex >= 0 &&
    currentIndex < visibleScannerResults.length - 1;

  const handlePrevious = () => {
    if (!hasPrevious || !visibleScannerResults) {
      return;
    }
    const previousResult = visibleScannerResults[currentIndex - 1];
    const route = scanResultRoute(scanPath, previousResult?.uuid, searchParams);
    void navigate(route);
  };

  const handleNext = () => {
    if (!hasNext || !visibleScannerResults) {
      return;
    }
    const nextResult = visibleScannerResults[currentIndex + 1];
    const route = scanResultRoute(scanPath, nextResult?.uuid, searchParams);
    void navigate(route);
  };

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
        if (e.key === "ArrowLeft") {
          if (
            hasPrevious &&
            !e.metaKey &&
            !e.ctrlKey &&
            !e.shiftKey &&
            !e.altKey
          ) {
            e.preventDefault();
            handlePrevious();
          }
        } else if (
          e.key === "ArrowRight" &&
          !e.metaKey &&
          !e.ctrlKey &&
          !e.shiftKey &&
          !e.altKey
        ) {
          if (hasNext) {
            e.preventDefault();
            handleNext();
          }
        }
      }
    };

    // Use capture phase to catch event before it reaches other handlers
    document.addEventListener("keydown", handleGlobalKeyDown, true);

    return () => {
      document.removeEventListener("keydown", handleGlobalKeyDown, true);
    };
  }, [hasPrevious, hasNext, handlePrevious, handleNext]);

  const result =
    visibleScannerResults && currentIndex !== -1
      ? visibleScannerResults[currentIndex]
      : undefined;

  return (
    <div className={clsx(styles.resultNav)}>
      <div
        onClick={handlePrevious}
        tabIndex={0}
        className={clsx(!hasPrevious && styles.disabled, styles.nav)}
      >
        <i className={clsx(ApplicationIcons.previous)} />
      </div>
      <div className={clsx(styles.sampleInfo, "text-size-smallest")}>
        {visibleScannerResults && currentIndex !== -1
          ? printIdentifier(resultIdentifier(result), result?.label)
          : undefined}
      </div>
      <div
        onClick={handleNext}
        tabIndex={0}
        className={clsx(!hasNext && styles.disabled, styles.nav)}
      >
        <i className={clsx(ApplicationIcons.next)} />
      </div>
    </div>
  );
};

const printIdentifier = (
  identifier: IdentifierInfo,
  label?: string
): string => {
  let val = "";
  if (identifier.epoch) {
    val = `${identifier.id} epoch ${identifier.epoch}`;
  } else {
    val = identifier.id;
  }

  if (label && label.length > 0) {
    val += ` (${label})`;
  }
  return val;
};
