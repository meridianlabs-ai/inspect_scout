import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import { Scan } from "../types";

interface StoreState {
  scans: Scan[];
  selectedScanLocation?: string;

  setScans: (scans: Scan[]) => void;
  setSelectedScanLocation: (location: string) => void;
}

export const useStore = create<StoreState>()(
  devtools(
    persist(
      immer((set, get, store) => ({
        // Initial state
        scans: [],

        // Actions
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
      }
    )
  )
);
