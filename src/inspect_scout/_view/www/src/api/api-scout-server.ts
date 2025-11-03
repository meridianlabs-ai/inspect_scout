import { Results, Scans } from "../types";
import { ScanApi } from "./api";

export const apiScoutServer = (): ScanApi => {
  return {
    getScan: async (scanLocation: string): Promise<Results> => {
      const response = await fetch(
        `/api/scan/${encodeURIComponent(scanLocation)}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch scan: ${response.statusText}`);
      }
      const responsObj = (await response.json()) as Results;
      return responsObj;
    },
    getScans: async (): Promise<Scans> => {
      const response = await fetch("/api/scans");
      if (!response.ok) {
        throw new Error(`Failed to fetch scans: ${response.statusText}`);
      }
      const responseObj = (await response.json()) as Scans;

      return responseObj;
    },
  };
};
