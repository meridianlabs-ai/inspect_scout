import { StateStorage } from "zustand/middleware";

import { Scans, Status } from "../types";

export type ClientStorage = StateStorage;

export interface ScanApi {
  getScans(): Promise<Scans>;
  getScan(scanLocation: string): Promise<Status>;
  getScannerDataframe(
    scanLocation: string,
    scanner: string,
    excludeColumns?: string[]
  ): Promise<ArrayBuffer | Uint8Array>;
  getScannerField(
    scanLocation: string,
    scanner: string,
    row: string,
    column: string
  ): Promise<any>;
  storage: ClientStorage;
}

export const NoPersistence: ClientStorage = {
  getItem: (_name: string): string | null => {
    return null;
  },
  setItem: (_name: string, _value: string): void => {},
  removeItem: (_name: string): void => {},
};
