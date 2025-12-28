import clsx from "clsx";
import { FC } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import {
  getRelativePathFromParams,
  scansRoute,
  isValidScanPath,
  scanRoute,
} from "../../../router/url";
import { useStore } from "../../../state/store";
import { Status } from "../../../types";
import { BreadCrumbs } from "../../components/BreadCrumbs";
import { Footer } from "../../components/Footer";
import { useSelectedScanDataframe, useSelectedScanner } from "../../hooks";
import { useServerScansDir } from "../../server/hooks";

import { ScanResultsBody } from "./ScanResultsBody";
import { ScanResultsOutline } from "./ScanResultsOutline";
import styles from "./ScanResultsPanel.module.css";

export const ScanResultsPanel: FC<{ selectedScan: Status }> = ({
  selectedScan,
}) => {
  const visibleItemsCount = useStore(
    (state) => state.visibleScannerResultsCount
  );
  const selectedScanner = useSelectedScanner();
  const { data: scansDir } = useServerScansDir();

  const {
    data: columnTable,
    loading: isLoading,
    error,
  } = useSelectedScanDataframe();
  const selectedScannerInfo = {
    columnTable,
    isLoading,
    error: error?.message,
  };

  const params = useParams<{ "*": string }>();
  const currentPath = getRelativePathFromParams(params);
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
      <ScanResultsOutline selectedScan={selectedScan} />
      <ScanResultsBody
        // TODO: This is slightly bogus. It really needs to be a scannerid since
        // nothing prevents two scanners from having the same name.
        scannerId={selectedScanner.data ?? "unknown"}
        selectedScan={selectedScan}
        selectedScanner={selectedScannerInfo}
      />
      <Footer
        id={""}
        left={
          <BreadCrumbs
            baseDir={scansDir}
            relativePath={currentPath}
            getRouteForSegment={getRouteForSegment}
            className={clsx("text-size-smallest", styles.breadcrumbs)}
            disableLastSegment={true}
          />
        }
        className={styles.footer}
        itemCount={visibleItemsCount}
        paginated={false}
        labels={{
          singular: "result",
          plural: "results",
        }}
      />
    </div>
  );
};
