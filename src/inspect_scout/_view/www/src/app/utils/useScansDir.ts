import { useStore } from "../../state/store";
import { useScanRoute } from "../hooks/useScanRoute";
import { appAliasedPath, useConfig } from "../server/useConfig";

interface UseScansDirResult {
  displayScansDir: string;
  resolvedScansDir: string;
  setScansDir: (path: string) => void;
}

export function useScansDir(useRouteParam = false): UseScansDirResult {
  const config = useConfig();
  const { scansDir: routeScansDir } = useScanRoute();
  const userScansDir = useStore((state) => state.userScansDir);
  const setUserScansDir = useStore((state) => state.setUserScansDir);

  // TODO: || "" is a smell. Fix them
  const resolvedPath =
    (useRouteParam ? routeScansDir : null) ||
    userScansDir ||
    config.scans_dir ||
    "";
  const displayPath = appAliasedPath(config, resolvedPath) || "";

  return {
    displayScansDir: displayPath,
    resolvedScansDir: resolvedPath,
    setScansDir: setUserScansDir,
  };
}
