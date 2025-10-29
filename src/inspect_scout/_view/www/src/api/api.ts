import { Scan } from "../types";

export interface ScansInfo {
  results_dir: string;
  scans: Scan[];
}

export interface ScanApi {
  getScans(): Promise<ScansInfo>;
  getScan(scanLocation: string): Promise<Scan>;
}
