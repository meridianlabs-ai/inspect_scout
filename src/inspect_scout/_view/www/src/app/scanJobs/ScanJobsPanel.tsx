import { clsx } from "clsx";
import { FC, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { ErrorPanel } from "../../components/ErrorPanel";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { LoadingBar } from "../../components/LoadingBar";
import {
  scansRoute,
  isValidScanPath,
  scanRoute,
  getRelativePathFromParams,
} from "../../router/url";
import { useStore } from "../../state/store";
import { BreadCrumbs } from "../components/BreadCrumbs";
import { Footer } from "../components/Footer";
import { ScansNavbar } from "../components/ScansNavbar";
import { useServerScansDir, useServerScans } from "../server/hooks";

import { ScanJobGrid } from "./ScanJobGrid";
import styles from "./ScanJobsPanel.module.css";

export const ScanJobsPanel: FC = () => {
  // Load scans data
  const { loading, error, data: scans } = useServerScans();
  const { data: resultsDir } = useServerScansDir();
  const visibleScanJobCount = useStore((state) => state.visibleScanJobCount);
  const userScansDir = useStore((state) => state.userScansDir);
  const setScanDir = useStore((state) => state.setUserScansDir);

  // Clear scan state from store on mount
  const clearScansState = useStore((state) => state.clearScansState);
  useEffect(() => {
    clearScansState();
  }, []);

  const params = useParams<{ "*": string }>();
  const currentPath = getRelativePathFromParams(params);
  const singleFileMode = useStore((state) => state.singleFileMode);
  const [searchParams] = useSearchParams();

  const getRouteForSegment = (path: string): string => {
    if (!path) {
      return scansRoute();
    }
    // Check if this segment path contains a valid scan_id pattern
    // If so, use scanRoute instead of scansRoute
    return isValidScanPath(path)
      ? scanRoute(path, searchParams)
      : scansRoute(path);
  };

  return (
    <div className={clsx(styles.container)}>
      <ScansNavbar
        scansDir={userScansDir || resultsDir}
        setScansDir={setScanDir}
        bordered={false}
      />
      <LoadingBar loading={!!loading} />
      <ExtendedFindProvider>
        {error && (
          <ErrorPanel
            title="Error Loading Scans"
            error={{ message: error.message }}
          />
        )}
        {scans && <ScanJobGrid scans={scans} resultsDir={resultsDir} />}
        <Footer
          id={"scan-job-footer"}
          itemCount={visibleScanJobCount || 0}
          paginated={false}
          left={
            <BreadCrumbs
              baseDir={resultsDir}
              relativePath={currentPath}
              getRouteForSegment={getRouteForSegment}
              className={"text-size-smallest"}
            />
          }
        />
      </ExtendedFindProvider>
    </div>
  );
};
