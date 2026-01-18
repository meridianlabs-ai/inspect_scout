import { createContext, useContext } from "react";

export type DisplayMode = "rendered" | "raw";

export interface DisplayModeContextType {
  displayMode: DisplayMode;
}

export const DisplayModeContext = createContext<DisplayModeContextType | null>(
  null
);

/**
 * Hook to access display mode. Returns default "rendered" if no provider exists.
 */
export const useDisplayMode = (): DisplayMode => {
  const context = useContext(DisplayModeContext);
  // Graceful fallback: if no provider, default to "rendered"
  return context?.displayMode ?? "rendered";
};
