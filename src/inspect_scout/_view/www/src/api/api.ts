import { Scan } from '../types';

export interface ScansInfo {
  results_dir: string;
  scans: Scan[];
}

export interface ScanApi {
  getScans(): Promise<ScansInfo>;
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
      const responsObj = (await response.json()) as Scan;
      console.log('Fetch response for scan:', responsObj);
      return responsObj
    },
    getScans: async (): Promise<ScansInfo> => {
      const response = await fetch('/api/scans');
      if (!response.ok) {
        throw new Error(`Failed to fetch scans: ${response.statusText}`);
      }
      const responseObj = (await response.json()) as ScansInfo;
      console.log('Fetch response for scan2:', responseObj);

      return responseObj
    },
  };
};
