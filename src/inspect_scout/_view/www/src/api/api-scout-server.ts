import { Scans, Status } from "../types";

import { NoPersistence, ScanApi } from "./api";

export const apiScoutServer = (): ScanApi => {
  return {
    getScan: async (scanLocation: string): Promise<Status> => {
      const response = await fetch(
        `/api/scan/${encodeURIComponent(scanLocation)}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch scan: ${response.statusText}`);
      }
      const responsObj = (await response.json()) as Status;
      return responsObj;
    },
    getScans: async (): Promise<Scans> => {
      const response = await fetch("/api/scans?status_only=true");
      if (!response.ok) {
        throw new Error(`Failed to fetch scans: ${response.statusText}`);
      }
      const responseObj = (await response.json()) as Scans;

      return responseObj;
    },
    getScannerDataframe: async (
      scanLocation: string,
      scanner: string
    ): Promise<ArrayBuffer> => {
      const response = await fetch(
        `/api/scanner_df/${encodeURIComponent(
          scanLocation
        )}?scanner=${encodeURIComponent(scanner)}`
      );

      if (!response.ok) {
        throw new Error(
          `Failed to fetch scanner dataframe: ${response.statusText}`
        );
      }
      const arrayBuffer = await response.arrayBuffer();
      return arrayBuffer;
    },
    storage: NoPersistence,
  };
};
