import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import { ScanApi } from "../api/api";
import { StateSnapshot } from "react-virtuoso";
import { GridState } from "ag-grid-community";
import { Results, Status } from "../types";

interface StoreState {
  api?: ScanApi;
  scans: Status[];
  selectedResults?: Results;
  selectedScanLocation?: string;
  resultsDir?: string;
  properties: Record<string, Record<string, unknown> | undefined>;
  scrollPositions: Record<string, number>;
  listPositions: Record<string, StateSnapshot>;
  visibleRanges: Record<string, { startIndex: number; endIndex: number }>;
  gridStates: Record<string, GridState>;
  singleFileMode?: boolean;
  hasInitializedEmbeddedData?: boolean;
  loading: number;
  selectedResultsTab?: string;
  collapsed: Record<string, boolean>;


  setApi(api: ScanApi): void;
  setScans: (scans: Status[]) => void;
  setSelectedResults: (results: Results) => void;
  setSelectedScanLocation: (location: string) => void;
  setResultsDir: (dir: string) => void;

  setPropertyValue: <T>(id: string, propertyName: string, value: T) => void;
  getPropertyValue: <T>(
    id: string,
    propertyName: string,
    defaultValue?: T
  ) => T | undefined;
  removePropertyValue: (id: string, propertyName: string) => void;

  getCollapsed: (name: string, defaultValue?: boolean) => boolean;
  setCollapsed: (name: string, value: boolean) => void;

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

  setSelectedResultsTab: (tab: string) => void;
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
        collapsed:{},

        // Actions
        setApi: (api: ScanApi) =>
          set((state) => {
            state.api = api;
          }),
        setScans: (scans: Status[]) =>
          set((state) => {
            state.scans = scans;
          }),
        setSelectedResults: (results: Results) =>
          set((state) => {
            state.selectedResults = results;
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
            const propertyGroup = state.properties[id];

            // No property, go ahead and return
            if (!propertyGroup || !propertyGroup[propertyName]) {
              return;
            }

            // Destructure to remove the property
            const { [propertyName]: _removed, ...remainingProperties } =
              propertyGroup;

            // If no remaining properties, remove the entire group
            if (Object.keys(remainingProperties).length === 0) {
              const { [id]: _removedGroup, ...remainingGroups } =
                state.properties;
              state.properties = remainingGroups;
              return;
            }

            // Update to the delete properties
            state.properties[id] = remainingProperties;
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
        setSelectedResultsTab: (tab: string) => {
          set((state) => {
            state.selectedResultsTab = tab;
          });
        },
        getCollapsed: (name: string, defaultValue?: boolean)  => {
          const state = get();
          return state.collapsed[name] ?? defaultValue ?? false;  
        },
        setCollapsed: (name: string, value: boolean)  => {
          set((state) => {
            state.collapsed[name] = value;
          });

        }
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
