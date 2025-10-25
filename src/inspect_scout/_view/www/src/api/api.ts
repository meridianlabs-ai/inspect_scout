import { Scan } from '../types';

export interface ScanApi {
  getScans(): Promise<Scan[]>;
  getScan(scanLocation: string): Promise<Scan>;
}

export const scoutServerClient = (): ScanApi => {
  return {
    getScan: async (scanLocation: string): Promise<Scan> => {
      const response = await fetch(
        `/api/scan/${encodeURIComponent(scanLocation)}`
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch scan: ${response.statusText}`);
      }
      return (await response.json()) as Scan
    },
    getScans: async (): Promise<Scan[]> => {
      const response = await fetch('/api/scans');

      if (!response.ok) {
        throw new Error(`Failed to fetch scans: ${response.statusText}`);
      }
      const responseObj = await response.json() as { scans: Scan[] };
      return responseObj.scans;
    },
  };
};
