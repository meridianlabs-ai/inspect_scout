import { StateStorage } from "zustand/middleware";

import { DataFrameInput } from "../app/types";
import { Scans, Status } from "../types";

export type ClientStorage = StateStorage;

export interface ScanApi {
  getScans(): Promise<Scans>;
  getScan(scanLocation: string): Promise<Status>;
  getScannerDataframe(
    scanLocation: string,
    scanner: string
  ): Promise<ArrayBuffer | Uint8Array>;
  getScannerDataframeInput(
    scanLocation: string,
    scanner: string,
    uuid: string
  ): Promise<DataFrameInput>;

  storage: ClientStorage;
}

export const NoPersistence: ClientStorage = {
  getItem: (_name: string): string | null => {
    return null;
  },
  setItem: (_name: string, _value: string): void => {},
  removeItem: (_name: string): void => {},
};
