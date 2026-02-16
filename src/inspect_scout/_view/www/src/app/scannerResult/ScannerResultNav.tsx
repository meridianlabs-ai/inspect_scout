import { FC, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useLoggingNavigate } from "../../debugging/navigationDebugging";
import { scanResultRoute } from "../../router/url";
import { useStore } from "../../state/store";
import { NextPreviousNav } from "../components/NextPreviousNav";
import { useScanRoute } from "../hooks/useScanRoute";
import { IdentifierInfo, resultIdentifier } from "../utils/results";

export const ScannerResultNav: FC = () => {
  const navigate = useLoggingNavigate("ScannerResultNav");
  const [searchParams] = useSearchParams();
  const { scansDir, scanPath, scanResultUuid } = useScanRoute();

  const visibleScannerResults = useStore(
    (state) => state.visibleScannerResults
  );

  const currentIndex = useMemo(() => {
    if (!visibleScannerResults) {
      return -1;
    }
    return visibleScannerResults.findIndex(
      (s) => s._rowIdentifier === scanResultUuid
    );
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
    if (!scansDir) {
      return;
    }
    const route = scanResultRoute(
      scansDir,
      scanPath,
      previousResult?._rowIdentifier,
      searchParams
    );
    void navigate(route);
  };

  const handleNext = () => {
    if (!hasNext || !visibleScannerResults) {
      return;
    }
    const nextResult = visibleScannerResults[currentIndex + 1];
    if (!scansDir) {
      return;
    }
    const route = scanResultRoute(
      scansDir,
      scanPath,
      nextResult?._rowIdentifier,
      searchParams
    );
    void navigate(route);
  };

  const result =
    visibleScannerResults && currentIndex !== -1
      ? visibleScannerResults[currentIndex]
      : undefined;

  return (
    <NextPreviousNav
      onPrevious={handlePrevious}
      onNext={handleNext}
      hasPrevious={hasPrevious}
      hasNext={!!hasNext}
    >
      <span className="text-size-smallest">
        {visibleScannerResults && currentIndex !== -1
          ? printIdentifier(resultIdentifier(result), result?.label)
          : undefined}
      </span>
    </NextPreviousNav>
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
    val = String(identifier.id);
  }

  if (label && label.length > 0) {
    val += ` (${label})`;
  }
  return val;
};
