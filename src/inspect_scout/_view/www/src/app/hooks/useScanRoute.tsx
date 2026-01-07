import { useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";

import { parseScanParams } from "../../router/url";
import { useStore } from "../../state/store";
import { join } from "../../utils/uri";
import { useServerScansDir } from "../server/hooks";

export const useScanRoute = (): {
  scansDir?: string;
  relativePath: string;
  scanPath: string;
  scanResultUuid?: string;
  resolvedScansDir?: string;
  location?: string;
} => {
  const params = useParams<{ scansDir?: string; "*": string }>();
  const setUserScansDir = useStore((state) => state.setUserScansDir);
  const resultsDir = useServerScansDir();

  const route = useMemo(() => parseScanParams(params), [params]);
  const resolvedScansDir = route.scansDir || resultsDir;
  const location = resolvedScansDir
    ? join(route.scanPath, resolvedScansDir)
    : undefined;

  useEffect(() => {
    if (route.scansDir) {
      setUserScansDir(route.scansDir);
    }
  }, [route.scansDir, setUserScansDir]);

  return {
    ...route,
    resolvedScansDir,
    location,
  };
};
