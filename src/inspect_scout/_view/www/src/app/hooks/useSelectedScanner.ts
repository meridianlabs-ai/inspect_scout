import { useMemo } from "react";

import { useMapAsyncData } from "../../hooks/useMapAsyncData";
import { useStore } from "../../state/store";
import { Status } from "../../types/api-types";
import { AsyncData, data } from "../../utils/asyncData";

import { useSelectedScan } from "./useSelectedScan";

export const useSelectedScanner = (): AsyncData<string> => {
  const selectedScanner = useStore((state) => state.selectedScanner);
  // TODO: This is a little bogus since we really don't need to do the server fetch
  // if we found the selectedScanner from zustand. Alas, the rules of hooks.
  const defaultScanner = useMapAsyncData(
    useSelectedScan(),
    _get_default_scanner
  );

  const selectedScannerAsyncData = useMemo(
    () => (selectedScanner ? data(selectedScanner) : undefined),
    [selectedScanner]
  );

  return selectedScannerAsyncData ?? defaultScanner;
};

const _get_default_scanner = (s: Status): string => {
  const result = s.summary.scanners
    ? Object.keys(s.summary.scanners)[0]
    : undefined;
  if (!result) {
    throw new Error("Scan must have a scanner");
  }
  return result;
};
