import { ReactNode, useCallback, useRef } from "react";
import {
  ExtendedFindContext,
  ExtendedFindContextType,
  ExtendedFindFn,
} from "./ExtendedFindContext";

interface ExtendedFindProviderProps {
  children: ReactNode;
}

export const ExtendedFindProvider = ({
  children,
}: ExtendedFindProviderProps) => {
  // The virtual lists that are currently active
  const virtualLists = useRef<Map<string, ExtendedFindFn>>(new Map());

  // Perform the extended search, then wait for the DOM to be ready
  // (e.g. the item scrolled into view) before resolving/finishing the
  // search.
  const extendedFindTerm = useCallback(
    async (
      term: string,
      direction: "forward" | "backward"
    ): Promise<boolean> => {
      // Try each registered virtual list
      for (const [, searchFn] of virtualLists.current) {
        const found = await new Promise<boolean>((resolve) => {
          let callbackFired = false;

          const onContentReady = () => {
            if (!callbackFired) {
              callbackFired = true;
              resolve(true);
            }
          };

          searchFn(term, direction, onContentReady)
            .then((found) => {
              if (!found && !callbackFired) {
                callbackFired = true;
                resolve(false);
              }
            })
            .catch(() => {
              if (!callbackFired) {
                callbackFired = true;
                resolve(false);
              }
            });
        });

        if (found) {
          return true;
        }
      }
      return false;
    },
    []
  );

  const registerVirtualList = useCallback(
    (id: string, searchFn: ExtendedFindFn): (() => void) => {
      virtualLists.current.set(id, searchFn);
      return () => {
        virtualLists.current.delete(id);
      };
    },
    []
  );

  const contextValue: ExtendedFindContextType = {
    extendedFindTerm,
    registerVirtualList,
  };

  return (
    <ExtendedFindContext.Provider value={contextValue}>
      {children}
    </ExtendedFindContext.Provider>
  );
};
