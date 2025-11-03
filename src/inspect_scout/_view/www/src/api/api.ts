import { Results, Scans } from "../types";

export interface ScanApi {
  getScans(): Promise<Scans>;
  getScan(scanLocation: string): Promise<Results>;
}
