import { fromArrow } from "arquero";
import { useMemo } from "react";

import { useStore } from "../../state/store";
import { useSelectedScanner } from "../scanner/results/hooks";
import { useScannerData } from "../scanner/results/list/hooks";

export const useSelectedResultsRow = (scanResultUuid: string) => {
  // TODO: Centralize this with a cache in the store
  const selectedScanner = useSelectedScanner();
  const selectedResults = useStore((state) => state.selectedResults);
  const scanner = selectedResults?.scanners[selectedScanner || ""];

  const columnTable = useMemo(() => {
    if (!scanner || !scanner.data) {
      return fromArrow(new ArrayBuffer(0));
    }

    // Decode base64 string to Uint8Array
    const binaryString = atob(scanner.data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Load Arrow data using Arquero
    const table = fromArrow(bytes.buffer);
    return table;
  }, [scanner]);

  const row = useMemo(() => {
    const rowData = columnTable.objects();
    const row = rowData.findIndex((r) => {
      return (r as Record<string, string>).uuid === scanResultUuid;
    });
    return row;
  }, [columnTable, scanResultUuid]);

  const scanData = useScannerData(row, columnTable);
  return scanData;
};
