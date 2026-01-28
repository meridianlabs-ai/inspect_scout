import {
  ColumnSizingState,
  RowSelectionState,
  SortingState,
} from "@tanstack/react-table";
import { GridState } from "ag-grid-community";
import { createContext, useContext } from "react";
import { StateSnapshot } from "react-virtuoso";
import { create } from "zustand";
import { createJSONStorage, devtools, persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";

import { ScanApi } from "../api/api";
import { ColumnSizingStrategyKey } from "../app/transcripts/columnSizing/types";
import {
  ErrorScope,
  ResultGroup,
  ScanResultSummary,
  SortColumn,
} from "../app/types";
import type { SimpleCondition } from "../query/types";
import { TranscriptInfo } from "../types/api-types";
import { debounce } from "../utils/sync";

// Filter types for columns
export type FilterType =
  | "string"
  | "number"
  | "boolean"
  | "date"
  | "datetime"
  | "duration"
  | "unknown";

// Column filter with metadata
export interface ColumnFilter {
  columnId: string;
  filterType: FilterType;
  condition: SimpleCondition | null;
}

// Transcripts table UI state
interface TranscriptsTableState {
  columnSizing: ColumnSizingState;
  columnOrder: string[];
  sorting: SortingState;
  rowSelection: RowSelectionState;
  focusedRowId: string | null;
  columnFilters: Record<string, ColumnFilter>;
  visibleColumns?: Array<keyof TranscriptInfo>;
  /** Current sizing strategy */
  sizingStrategy: ColumnSizingStrategyKey;
  /** Column IDs that have been manually resized by the user */
  manuallyResizedColumns: string[];
}

interface TranscriptState {
  excludedTypes?: string[];
  collapsed?: boolean;
  outlineCollapsed?: boolean;
  displayMode?: "rendered" | "raw";
  validationSidebarCollapsed?: boolean;
}

interface StoreState {
  // App status
  singleFileMode?: boolean;
  hasInitializedEmbeddedData?: boolean;
  hasInitializedRouting?: boolean;
  scopedErrors: Record<ErrorScope, string | undefined>;
  showFind?: boolean;

  // Scans
  visibleScanJobCount?: number;
  selectedScanLocation?: string;

  // Scanner
  visibleScannerResults: ScanResultSummary[];
  visibleScannerResultsCount: number;

  // Dataframes
  selectedScanResult?: string;

  // general UI state
  properties: Record<string, Record<string, unknown> | undefined>;
  scrollPositions: Record<string, number>;
  listPositions: Record<string, StateSnapshot>;
  visibleRanges: Record<string, { startIndex: number; endIndex: number }>;
  gridStates: Record<string, GridState>;

  // Scan specific properties (clear when switching scans)
  selectedResultsTab?: string;
  selectedResultTab?: string;
  collapsedBuckets: Record<string, Record<string, boolean>>;
  selectedScanner?: string;
  selectedResultsView?: string;
  selectedFilter?: string;
  showingRefPopover?: string;
  groupResultsBy?: ResultGroup;
  sortResults?: SortColumn[];
  scansSearchText?: string;
  highlightLabeled?: boolean;
  selectedResultRow?: number;
  dataframeWrapText?: boolean;
  dataframeShowFilterColumns?: boolean;
  dataframeFilterColumns?: string[];

  // Transcript
  transcriptCollapsedEvents: Record<string, Record<string, boolean>>;
  transcriptOutlineId?: string;

  // Transcript Detail properties (clear when switching transcripts)
  selectedTranscriptTab?: string;

  // User selected / visible transcript path
  userTranscriptsDir?: string;
  userScansDir?: string;

  // Transcript Data (loaded data + source directory)
  transcripts?: TranscriptInfo[];
  transcriptsDir?: string;
  transcriptsTableState: TranscriptsTableState;

  // Transcript Detail Data
  transcriptState: TranscriptState;

  // Validation state
  selectedValidationSetUri?: string;
  validationCaseSelection: Record<string, boolean>;
  validationSplitFilter?: string;
  validationSearchText?: string;

  // validationEditorState
  editorSelectedValidationSetUri?: string;

  // App initialization
  setShowFind: (show: boolean) => void;
  setSingleFileMode: (enabled: boolean) => void;
  setHasInitializedEmbeddedData: (initialized: boolean) => void;
  setHasInitializedRouting: (initialized: boolean) => void;
  setError: (scope: ErrorScope, error: string | undefined) => void;
  clearError: (scope: ErrorScope) => void;

  // List of scans
  setVisibleScanJobCount: (count: number) => void;

  // Selected scan location (for nav restoration)
  setSelectedScanLocation: (location: string) => void;

  // Track the select result and data
  setSelectedScanner: (scanner: string) => void;
  setSelectedScanResult: (result: string) => void;
  setVisibleScannerResults: (results: ScanResultSummary[]) => void;
  setVisibleScannerResultsCount: (count: number) => void;

  // Clearing state
  clearScanState: () => void;
  clearScansState: () => void;
  clearTranscriptState: () => void;

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

  setSelectedResultsTab: (tab: string) => void;
  setSelectedResultTab: (tab: string) => void;

  setTranscriptOutlineId: (id: string) => void;
  clearTranscriptOutlineId: () => void;

  setSelectedTranscriptTab: (tab: string) => void;

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
  setShowingRefPopover: (popoverKey: string) => void;
  clearShowingRefPopover: () => void;
  setGroupResultsBy: (groupBy: ResultGroup) => void;
  setSortResults: (sortColumns?: SortColumn[]) => void;
  setScansSearchText: (text: string) => void;
  setHighlightLabeled: (highlight: boolean) => void;
  setSelectedResultRow: (row: number) => void;
  setDataframeWrapText: (wrap: boolean) => void;
  setDataframeFilterColumns: (columns: string[]) => void;
  setDataframeShowFilterColumns: (show: boolean) => void;

  setUserScansDir: (path: string) => void;
  setUserTranscriptsDir: (path: string) => void;
  setTranscripts: (transcripts: TranscriptInfo[]) => void;
  setTranscriptsDir: (path: string) => void;
  setTranscriptsTableState: (
    updater:
      | TranscriptsTableState
      | ((prev: TranscriptsTableState) => TranscriptsTableState)
  ) => void;
  setTranscriptState: (
    updater: TranscriptState | ((prev: TranscriptState) => TranscriptState)
  ) => void;

  // Validation actions
  setSelectedValidationSetUri: (uri: string | undefined) => void;
  setValidationCaseSelection: (selection: Record<string, boolean>) => void;
  toggleValidationCaseSelection: (caseId: string) => void;
  setValidationSplitFilter: (split: string | undefined) => void;
  setValidationSearchText: (text: string | undefined) => void;
  clearValidationState: () => void;

  setEditorSelectedValidationSetUri: (uri: string | undefined) => void;
}

const createDebouncedPersistStorage = (
  storage: ReturnType<typeof createJSONStorage>,
  delay = 2000
) => {
  if (!storage) {
    throw new Error("Storage is required");
  }

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
          resultsStoredInRef: false,
          resultDataInState: false,
          properties: {},
          scrollPositions: {},
          listPositions: {},
          visibleRanges: {},
          gridStates: {},
          loading: 0,
          loadingData: 0,
          collapsedBuckets: {},
          transcriptCollapsedEvents: {},
          scopedErrors: {} as Record<ErrorScope, string>,
          visibleScannerResults: [],
          visibleScannerResultsCount: 0,
          highlightLabeled: false,
          transcriptsTableState: {
            columnSizing: {},
            columnOrder: [],
            sorting: [{ id: "date", desc: true }],
            rowSelection: {},
            focusedRowId: null,
            columnFilters: {},
            sizingStrategy: "fit-content",
            manuallyResizedColumns: [],
          },
          transcriptState: {},
          validationCaseSelection: {},

          // Actions
          setShowFind(show: boolean) {
            set((state) => {
              state.showFind = show;
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
          setError: (scope: ErrorScope, error: string | undefined) => {
            set((state) => {
              state.scopedErrors[scope] = error;
            });
          },
          clearError: (scope: ErrorScope) => {
            set((state) => {
              state.scopedErrors[scope] = undefined;
            });
          },
          setVisibleScanJobCount: (count: number) =>
            set((state) => {
              state.visibleScanJobCount = count;
            }),
          setSelectedScanLocation: (location: string) =>
            set((state) => {
              state.selectedScanLocation = location;
            }),
          setSelectedScanner: (scanner: string) => {
            set((state) => {
              state.selectedScanner = scanner;
            });
          },
          setSelectedScanResult: (result: string) =>
            set((state) => {
              state.selectedScanResult = result;
            }),
          setVisibleScannerResults: (results: ScanResultSummary[]) => {
            set((state) => {
              state.visibleScannerResults = results;
            });
          },
          setVisibleScannerResultsCount(count: number) {
            set((state) => {
              state.visibleScannerResultsCount = count;
            });
          },
          clearScanState: () => {
            set((state) => {
              state.selectedResultsTab = undefined;
              state.collapsedBuckets = {};
              state.transcriptCollapsedEvents = {};
              state.transcriptOutlineId = undefined;
              state.selectedResultTab = undefined;
              state.groupResultsBy = undefined;
              state.scansSearchText = undefined;
            });
          },
          clearScansState: () => {
            set((state) => {
              state.selectedResultsView = undefined;
              state.selectedFilter = undefined;
              state.selectedScanner = undefined;
              state.selectedScanResult = undefined;
              state.sortResults = undefined;
            });
          },
          clearTranscriptState: () => {
            set((state) => {
              state.selectedTranscriptTab = undefined;
            });
          },
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
                listPositions: newListPositions,
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
          setSelectedTranscriptTab: (tab: string) => {
            set((state) => {
              state.selectedTranscriptTab = tab;
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
          setShowingRefPopover: (popoverKey: string) => {
            set((state) => {
              state.showingRefPopover = popoverKey;
            });
          },
          clearShowingRefPopover: () => {
            set((state) => {
              state.showingRefPopover = undefined;
            });
          },
          setGroupResultsBy: (groupBy: ResultGroup) => {
            set((state) => {
              state.groupResultsBy = groupBy;
            });
          },
          setSortResults: (sortColumns?: SortColumn[]) => {
            set((state) => {
              state.sortResults = sortColumns;
            });
          },
          setScansSearchText: (text: string) => {
            set((state) => {
              state.scansSearchText = text;
            });
          },
          setHighlightLabeled: (highlight: boolean) => {
            set((state) => {
              state.highlightLabeled = highlight;
            });
          },
          setSelectedResultRow: (row: number) => {
            set((state) => {
              state.selectedResultRow = row;
            });
          },
          setDataframeWrapText: (wrap: boolean) => {
            set((state) => {
              state.dataframeWrapText = wrap;
            });
          },
          setDataframeFilterColumns: (columns: string[]) => {
            set((state) => {
              state.dataframeFilterColumns = columns;
            });
          },
          setDataframeShowFilterColumns: (show: boolean) => {
            set((state) => {
              state.dataframeShowFilterColumns = show;
            });
          },
          setUserScansDir: (path: string) => {
            set((state) => {
              state.userScansDir = path;
            });
          },
          setUserTranscriptsDir: (path: string) => {
            set((state) => {
              state.userTranscriptsDir = path;
            });
          },
          setTranscripts: (transcripts: TranscriptInfo[]) => {
            set((state) => {
              state.transcripts = transcripts;
            });
          },
          setTranscriptsDir: (path: string) => {
            set((state) => {
              state.transcriptsDir = path;
            });
          },
          setTranscriptsTableState: (updater) => {
            set((state) => {
              state.transcriptsTableState =
                typeof updater === "function"
                  ? updater(state.transcriptsTableState)
                  : updater;
            });
          },
          setTranscriptState(updater) {
            set((state) => {
              state.transcriptState =
                typeof updater === "function"
                  ? updater(state.transcriptState)
                  : updater;
            });
          },

          // Validation actions
          setSelectedValidationSetUri: (uri: string | undefined) => {
            set((state) => {
              state.selectedValidationSetUri = uri;
              // Clear case selection when switching validation sets
              state.validationCaseSelection = {};
            });
          },
          setValidationCaseSelection: (selection: Record<string, boolean>) => {
            set((state) => {
              state.validationCaseSelection = selection;
            });
          },
          toggleValidationCaseSelection: (caseId: string) => {
            set((state) => {
              const current = state.validationCaseSelection[caseId] ?? false;
              state.validationCaseSelection[caseId] = !current;
            });
          },
          setValidationSplitFilter: (split: string | undefined) => {
            set((state) => {
              state.validationSplitFilter = split;
            });
          },
          setValidationSearchText: (text: string | undefined) => {
            set((state) => {
              state.validationSearchText = text;
            });
          },
          clearValidationState: () => {
            set((state) => {
              state.selectedValidationSetUri = undefined;
              state.validationCaseSelection = {};
              state.validationSplitFilter = undefined;
              state.validationSearchText = undefined;
            });
          },
          setEditorSelectedValidationSetUri: (uri: string | undefined) => {
            set((state) => {
              state.editorSelectedValidationSetUri = uri;
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
            const {
              hasInitializedRouting,
              visibleScannerResults,
              ...persistedState
            } = state;
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
