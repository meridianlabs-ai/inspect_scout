import { createContext, useContext } from "react";

// The search context provides global search assistance. We generally use the
// browser to perform searches using 'find', but this allows for virtual lists
// and other virtualized components to register themselves to be notified when a
// search is requested and no matches are found. In this case, they can 'look ahead'
// and scroll an item into view if it is likely/certain to contain the search term.

// Find will call this when an extended find is requested
export type ExtendedFindFn = (
  term: string,
  direction: "forward" | "backward",
  onContentReady: () => void
) => Promise<boolean>;

// The context provides an extended search function and a way for the active
// virtual lists to register themselves.
export interface ExtendedFindContextType {
  extendedFindTerm: (
    term: string,
    direction: "forward" | "backward"
  ) => Promise<boolean>;
  registerVirtualList: (id: string, searchFn: ExtendedFindFn) => () => void;
}

export const ExtendedFindContext =
  createContext<ExtendedFindContextType | null>(null);

export const useExtendedFind = (): ExtendedFindContextType => {
  const context = useContext(ExtendedFindContext);
  if (!context) {
    throw new Error("useSearch must be used within a SearchProvider");
  }
  return context;
};
