import { StateStorage } from "zustand/middleware";

import { Results, Scans } from "../types";

export type ClientStorage = StateStorage;

export interface ScanApi {
  getScans(): Promise<Scans>;
  getScan(scanLocation: string): Promise<Results>;
  storage: ClientStorage;
}

export const NoPersistence: ClientStorage = {
  getItem: (_name: string): string | null => {
    return null;
  },
  setItem: (_name: string, _value: string): void => {},
  removeItem: (_name: string): void => {},
};
