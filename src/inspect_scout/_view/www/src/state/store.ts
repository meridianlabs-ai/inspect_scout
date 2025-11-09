import { GridState } from "ag-grid-community";
import { ColumnTable } from "arquero";
import { createContext, useContext } from "react";
import { StateSnapshot } from "react-virtuoso";
import { create } from "zustand";
import { createJSONStorage, devtools, persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

import { ScanApi } from "../api/api";
import { Results, Status } from "../types";
import { debounce } from "../utils/sync";

interface StoreState {
  scans: Status[];
  selectedResults?: Results;
  selectedScanLocation?: string;

  selectedScanResult?: string;
  selectedScanResultData?: ColumnTable;

  resultsDir?: string;
  properties: Record<string, Record<string, unknown> | undefined>;
  scrollPositions: Record<string, number>;
  listPositions: Record<string, StateSnapshot>;
  visibleRanges: Record<string, { startIndex: number; endIndex: number }>;
  gridStates: Record<string, GridState>;
  singleFileMode?: boolean;
  hasInitializedEmbeddedData?: boolean;
  hasInitializedRouting?: boolean;
  loading: number;

  // Scan specific properties (clear when switching scans)
  selectedResultsTab?: string;
  selectedResultTab?: string;
  collapsedBuckets: Record<string, Record<string, boolean>>;
  selectedScanner?: string;
  selectedResultsView?: string;
  selectedFilter?: string;

  // Transcript
  transcriptCollapsedEvents: Record<string, Record<string, boolean>>;
  transcriptOutlineId?: string;

  setScans: (scans: Status[]) => void;
  setSelectedResults: (results: Results) => void;
  setSelectedScanLocation: (location: string) => void;
  setSelectedScanResult: (result: string) => void;
  setSelectedScanResultData: (data: ColumnTable) => void;

  setResultsDir: (dir: string) => void;

  setPropertyValue: <T>(id: string, propertyName: string, value: T) => void;
  getPropertyValue: <T>(
    id: string,
    propertyName: string,
    defaultValue?: T
  ) => T | undefined;
  removePropertyValue: (id: string, propertyName: string) => void;

  setCollapsed: (bucket: string, key: string, value: boolean) => void;
  clearCollapsed: (bucket: string) => void;

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
  setHasInitializedRouting: (initialized: boolean) => void;

  setLoading: (loading: boolean) => void;

  setSelectedResultsTab: (tab: string) => void;
  setSelectedResultTab: (tab: string) => void;

  setSelectedScanner: (scanner: string) => void;

  setTranscriptOutlineId: (id: string) => void;
  clearTranscriptOutlineId: () => void;

  setTranscriptCollapsedEvent: (
    scope: string,
    event: string,
    collapsed: boolean
  ) => void;
  setTranscriptCollapsedEvents: (
    scope: string,
    events: Record<string, boolean>
  ) => void;
  clearTranscriptCollapsedEvents: (scope: string) => void;

  setSelectedResultsView: (view: string) => void;

  setSelectedFilter: (filter: string) => void;

  clearScanState: () => void;
}

const createDebouncedPersistStorage = (
  storage: ReturnType<typeof createJSONStorage>,
  delay = 2000
) => {
  type StorageValue = Parameters<typeof storage.setItem>[1];

  const debouncedSetItem = debounce((key: string, value: StorageValue) => {
    storage.setItem(key, value);
  }, delay);

  return {
    ...storage,
    setItem: (key: string, value: StorageValue) => {
      debouncedSetItem(key, value);
    },
  };
};

export const createStore = (api: ScanApi) =>
  create<StoreState>()(
    devtools(
      persist(
        immer((set, get) => ({
          // Initial state
          scans: [],
          properties: {},
          scrollPositions: {},
          listPositions: {},
          visibleRanges: {},
          gridStates: {},
          loading: 0,
          collapsedBuckets: {},
          transcriptCollapsedEvents: {},

          // Actions
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
          setSelectedScanResult: (result: string) =>
            set((state) => {
              state.selectedScanResult = result;
            }),
          setSelectedScanResultData: (data: ColumnTable) =>
            set((state) => {
              state.selectedScanResultData = data;
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
          setHasInitializedRouting: (initialized: boolean) => {
            set((state) => {
              state.hasInitializedRouting = initialized;
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
          setSelectedResultTab: (tab: string) => {
            set((state) => {
              state.selectedResultTab = tab;
            });
          },
          setCollapsed: (bucket: string, key: string, value: boolean) => {
            set((state) => {
              state.collapsedBuckets[bucket] =
                state.collapsedBuckets[bucket] || {};
              state.collapsedBuckets[bucket][key] = value;
            });
          },
          clearCollapsed: (bucket: string) => {
            set((state) => {
              state.collapsedBuckets[bucket] = {};
            });
          },
          setSelectedScanner: (scanner: string) => {
            set((state) => {
              state.selectedScanner = scanner;
            });
          },
          setTranscriptOutlineId: (id: string) => {
            set((state) => {
              state.transcriptOutlineId = id;
            });
          },
          clearTranscriptOutlineId: () => {
            set((state) => {
              state.transcriptOutlineId = undefined;
            });
          },
          setTranscriptCollapsedEvent: (
            scope: string,
            event: string,
            collapsed: boolean
          ) => {
            set((state) => {
              if (!state.transcriptCollapsedEvents[scope]) {
                state.transcriptCollapsedEvents[scope] = {};
              }
              state.transcriptCollapsedEvents[scope][event] = collapsed;
            });
          },
          setTranscriptCollapsedEvents: (
            scope: string,
            events: Record<string, boolean>
          ) => {
            set((state) => {
              state.transcriptCollapsedEvents[scope] = events;
            });
          },
          clearTranscriptCollapsedEvents: (scope: string) => {
            set((state) => {
              state.transcriptCollapsedEvents[scope] = {};
            });
          },
          setSelectedResultsView: (view: string) => {
            set((state) => {
              state.selectedResultsView = view;
            });
          },
          setSelectedFilter: (filter: string) => {
            set((state) => {
              state.selectedFilter = filter;
            });
          },
          clearScanState: () => {
            set((state) => {
              state.selectedResults = undefined;
              state.selectedResultsTab = undefined;
              state.collapsedBuckets = {};
              state.selectedScanner = undefined;
              state.transcriptCollapsedEvents = {};
              state.transcriptOutlineId = undefined;
              state.selectedResults = undefined;
              state.selectedResultsView = undefined;
              state.selectedFilter = undefined;
            });
          },
        })),
        {
          name: "inspect-scout-storage",
          storage: createDebouncedPersistStorage(
            createJSONStorage(() => api.storage)
          ),
          version: 1,
          partialize: (state) => {
            // Exclude runtime-only flags from persistence
            const { hasInitializedRouting, ...persistedState } = state;
            return persistedState;
          },
        }
      )
    )
  );

type StoreApi = ReturnType<typeof createStore>;

const StoreContext = createContext<StoreApi | null>(null);
const ApiContext = createContext<ScanApi | null>(null);

export const StoreProvider = StoreContext.Provider;
export const ApiProvider = ApiContext.Provider;

export const useStore = <T>(selector?: (state: StoreState) => T) => {
  const store = useContext(StoreContext);
  if (!store) throw new Error("useStore must be used within StoreProvider");

  // If no selector is provided, return the whole state
  if (!selector) {
    return store((state) => state) as T;
  }

  return store(selector);
};

export const useApi = (): ScanApi => {
  const api = useContext(ApiContext);
  if (!api) throw new Error("useApi must be used within ApiProvider");
  return api;
};
