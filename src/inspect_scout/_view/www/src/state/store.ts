import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import { Scan } from "../types";
import { ScanApi } from "../api/api";
import { StateSnapshot } from "react-virtuoso";
import { GridState } from "ag-grid-community";

interface StoreState {
  api?: ScanApi;
  scans: Scan[];
  selectedScan?: Scan;
  selectedScanLocation?: string;
  resultsDir?: string;
  properties: Record<string, Record<string, unknown>>;
  scrollPositions: Record<string, number>;
  listPositions: Record<string, StateSnapshot>;
  visibleRanges: Record<string, { startIndex: number; endIndex: number }>;
  gridStates: Record<string, GridState>;
  singleFileMode?: boolean;
  hasInitializedEmbeddedData?: boolean;
  loading: number;

  setApi(api: ScanApi): void;
  setScans: (scans: Scan[]) => void;
  setSelectedScan: (scan: Scan) => void;
  setSelectedScanLocation: (location: string) => void;
  setResultsDir: (dir: string) => void;

  setPropertyValue: <T>(id: string, propertyName: string, value: T) => void;
  getPropertyValue: <T>(
    id: string,
    propertyName: string,
    defaultValue?: T
  ) => T | undefined;
  removePropertyValue: (id: string, propertyName: string) => void;

  getScrollPosition: (path: string) => number | undefined;
  setScrollPosition: (path: string, position: number) => void;

  setListPosition: (name: string, position: StateSnapshot) => void;
  clearListPosition: (name: string) => void;

  setGridState: (name: string, state: GridState) => void;
  clearGridState: (name: string) => void;

  getVisibleRange: (name: string) => { startIndex: number; endIndex: number };
  setVisibleRange: (
    name: string,
    value: { startIndex: number; endIndex: number }
  ) => void;
  clearVisibleRange: (name: string) => void;

  setSingleFileMode: (enabled: boolean) => void;
  setHasInitializedEmbeddedData: (initialized: boolean) => void;

  setLoading: (loading: boolean) => void;
}

export const useStore = create<StoreState>()(
  devtools(
    persist(
      immer((set, get) => ({
        // Initial state
        scans: [],
        api: undefined,
        properties: {},
        scrollPositions: {},
        listPositions: {},
        visibleRanges: {},
        gridStates: {},
        loading: 0,

        // Actions
        setApi: (api: ScanApi) =>
          set((state) => {
            state.api = api;
          }),
        setScans: (scans: Scan[]) =>
          set((state) => {
            state.scans = scans;
          }),
        setSelectedScan: (scan: Scan) =>
          set((state) => {
            state.selectedScan = scan;
          }),
        setSelectedScanLocation: (location: string) =>
          set((state) => {
            state.selectedScanLocation = location;
          }),

        setResultsDir: (dir: string) =>
          set((state) => {
            state.resultsDir = dir;
          }),

        setPropertyValue<T>(id: string, propertyName: string, value: T) {
          set((state) => {
            if (!state.properties[id]) {
              state.properties[id] = {};
            }
            state.properties[id][propertyName] = value;
          });
        },

        getPropertyValue<T>(
          id: string,
          propertyName: string,
          defaultValue: T
        ): T | undefined {
          const value = get().properties[id]?.[propertyName];
          return value !== undefined ? (value as T) : defaultValue;
        },

        removePropertyValue(id: string, propertyName: string) {
          set((state) => {
            if (state.properties[id]) {
              // TODO: Revisit
              // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
              delete state.properties[id][propertyName];
              if (Object.keys(state.properties[id]).length === 0) {
                // TODO: Revisit
                // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
                delete state.properties[id];
              }
            }
          });
        },
        getScrollPosition(path) {
          const state = get();
          return state.scrollPositions[path];
        },
        setScrollPosition(path, position) {
          set((state) => {
            state.scrollPositions[path] = position;
          });
        },
        setListPosition: (name: string, position: StateSnapshot) => {
          set((state) => {
            state.listPositions[name] = position;
          });
        },
        clearListPosition: (name: string) => {
          set((state) => {
            // Remove the key
            const newListPositions = { ...state.listPositions };
            // TODO: Revisit
            // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
            delete newListPositions[name];

            return {
              app: {
                ...state,
                listPositions: newListPositions,
              },
            };
          });
        },
        getVisibleRange: (name: string) => {
          return get().visibleRanges[name] ?? { startIndex: 0, endIndex: 0 };
        },
        setVisibleRange: (
          name: string,
          value: { startIndex: number; endIndex: number }
        ) => {
          set((state) => {
            state.visibleRanges[name] = value;
          });
        },
        clearVisibleRange: (name: string) => {
          set((state) => {
            // Remove the key
            const newVisibleRanges = { ...state.visibleRanges };
            // TODO: Revisit
            // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
            delete newVisibleRanges[name];

            return {
              ...state,
              visibleRanges: newVisibleRanges,
            };
          });
        },
        setGridState: (name: string, gridState: GridState) => {
          set((state) => {
            state.gridStates[name] = gridState;
          });
        },
        clearGridState: (name: string) => {
          set((state) => {
            const newGridStates = { ...state.gridStates };
            // TODO: Revisit
            // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
            delete newGridStates[name];

            return {
              ...state,
              gridStates: newGridStates,
            };
          });
        },
        setSingleFileMode: (enabled: boolean) => {
          set((state) => {
            state.singleFileMode = enabled;
          });
        },
        setHasInitializedEmbeddedData: (initialized: boolean) => {
          set((state) => {
            state.hasInitializedEmbeddedData = initialized;
          });
        },
        setLoading: (loading: boolean) => {
          set((state) => {
            // increment or decrement loading counter
            if (loading) {
              state.loading += 1;
            } else {
              state.loading = Math.max(0, state.loading - 1);
            }
          });
        },
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
