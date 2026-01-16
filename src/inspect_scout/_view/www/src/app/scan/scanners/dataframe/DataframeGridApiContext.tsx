import { GridApi } from "ag-grid-community";
import {
  createContext,
  FC,
  ReactNode,
  useCallback,
  useContext,
  useState,
} from "react";

interface DataframeGridApiContextValue {
  gridApi: GridApi | null;
  setGridApi: (api: GridApi | null) => void;
}

const DataframeGridApiContext =
  createContext<DataframeGridApiContextValue | null>(null);

export const DataframeGridApiProvider: FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [gridApi, setGridApiState] = useState<GridApi | null>(null);

  const setGridApi = useCallback((api: GridApi | null) => {
    setGridApiState(api);
  }, []);

  return (
    <DataframeGridApiContext.Provider value={{ gridApi, setGridApi }}>
      {children}
    </DataframeGridApiContext.Provider>
  );
};

export const useDataframeGridApi = (): GridApi | null => {
  const context = useContext(DataframeGridApiContext);
  if (!context) {
    // Return null if not within provider - buttons will be disabled
    return null;
  }
  return context.gridApi;
};

export const useSetDataframeGridApi = (): ((api: GridApi | null) => void) => {
  const context = useContext(DataframeGridApiContext);
  if (!context) {
    // Return no-op if not within provider
    return () => {};
  }
  return context.setGridApi;
};
