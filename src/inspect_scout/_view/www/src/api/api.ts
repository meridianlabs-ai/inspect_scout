import { Results, Scans } from "../types";

export interface ClientStorage {
  getItem: <T>(name: string) => T | null;
  setItem: <T>(name: string, value: T) => void;
  removeItem: (name: string) => void;
}

export interface ScanApi {
  getScans(): Promise<Scans>;
  getScan(scanLocation: string): Promise<Results>;
  storage: ClientStorage;
}

export const NoPersistence: ClientStorage = {
  getItem: <T>(_name: string): T | null => {
    console.log("Get Item", _name);
    return null;
  },
  setItem: <T>(_name: string, _value: T): void => {
    console.log("Set Item", _name, _value);
  },
  removeItem: (_name: string): void => {
    console.log("Remove Item", _name);
  },
};
