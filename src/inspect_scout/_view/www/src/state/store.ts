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

  // Scan specific properties (clear when switching scans)
  selectedResultsTab?: string;
  collapsedBuckets: Record<string, Record<string, boolean>>;
  selectedScanner?: string;
  transcriptCollapsedEvents: Record<string, Record<string, boolean>>;
  transcriptOutlineId?: string;

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

  setLoading: (loading: boolean) => void;

  setSelectedResultsTab: (tab: string) => void;

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

  clearScanState: () => void;
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
        collapsedBuckets: {},
        transcriptCollapsedEvents: {},

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
        clearScanState: () => {
          set((state) => {
            state.selectedResults = undefined;
            state.selectedResultsTab = undefined;
            state.collapsedBuckets = {};
            state.selectedScanner = undefined;
            state.transcriptCollapsedEvents = {};
            state.transcriptOutlineId = undefined;
            state.selectedResults = undefined;
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
