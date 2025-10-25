import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import { Scan } from "../types";
import { ScanApi } from "../api/api";

interface StoreState {
  api?: ScanApi;
  scans: Scan[];
  selectedScanLocation?: string;

  setApi(api: ScanApi): void;
  setScans: (scans: Scan[]) => void;
  setSelectedScanLocation: (location: string) => void;
}

export const useStore = create<StoreState>()(
  devtools(
    persist(
      immer((set, _get, _store) => ({
        // Initial state
        scans: [],
        api: undefined,

        // Actions
        setApi: (api: ScanApi) =>
          set((state) => {
            state.api = api;
          }),
        setScans: (scans: Scan[]) =>
          set((state) => {
            state.scans = scans;
          }),

        setSelectedScanLocation: (location: string) =>
          set((state) => {
            state.selectedScanLocation = location;
          }),
      })),
      {
        name: "inspect-scout-storage",
        partialize: (state) => ({
          scans: state.scans,
          selectedScanLocation: state.selectedScanLocation,
          // Skip api, which isn't serializable
        }),
      }
    )
  )
);
