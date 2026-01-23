import { useStore } from "../../state/store";
import { useScanRoute } from "../hooks/useScanRoute";
import { appAliasedPath, useAppConfig } from "../server/useAppConfig";

interface UseScansDirResult {
  displayScansDir: string;
  resolvedScansDir: string;
  resolvedScansDirSource: "route" | "user" | "project" | "cli";
  setScansDir: (path: string) => void;
}

export function useScansDir(useRouteParam = false): UseScansDirResult {
  const config = useAppConfig();
  const { scansDir: routeScansDir } = useScanRoute();
  const userScansDir = useStore((state) => state.userScansDir);
  const setUserScansDir = useStore((state) => state.setUserScansDir);

  // TODO: || "" is a smell. Fix them
  const resolvedPath =
    (useRouteParam ? routeScansDir : null) ||
    userScansDir ||
    config.scans.dir ||
    "";

  const scanDirSource =
    useRouteParam && routeScansDir
      ? "route"
      : userScansDir
        ? "user"
        : config.scans.source === "cli"
          ? "cli"
          : "project";

  const displayPath = appAliasedPath(config, resolvedPath) || "";

  return {
    displayScansDir: displayPath,
    resolvedScansDir: resolvedPath,
    resolvedScansDirSource: scanDirSource,
    setScansDir: setUserScansDir,
  };
}
