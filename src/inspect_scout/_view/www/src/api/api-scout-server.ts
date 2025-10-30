import { Scan } from "../types";
import { ScanApi, ScansInfo } from "./api";

export const apiScoutServer = (): ScanApi => {
  return {
    getScan: async (scanLocation: string): Promise<Scan> => {
      const response = await fetch(
        `/api/scan/${encodeURIComponent(scanLocation)}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch scan: ${response.statusText}`);
      }
      const responsObj = (await response.json()) as Scan;
      return responsObj;
    },
    getScans: async (): Promise<ScansInfo> => {
      const response = await fetch("/api/scans");
      if (!response.ok) {
        throw new Error(`Failed to fetch scans: ${response.statusText}`);
      }
      const responseObj = (await response.json()) as ScansInfo;

      return responseObj;
    },
  };
};
