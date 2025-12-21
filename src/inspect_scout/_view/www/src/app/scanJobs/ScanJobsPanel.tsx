import { clsx } from "clsx";
import { FC, useEffect } from "react";

import { ActivityBar } from "../../components/ActivityBar";
import { ErrorPanel } from "../../components/ErrorPanel";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { useStore } from "../../state/store";
import { Footer } from "../components/Footer";
import { Navbar } from "../components/Navbar";
import { useServerScans } from "../server/hooks";

import { ScanJobGrid } from "./ScanJobGrid";
import styles from "./ScanJobsPanel.module.css";

export const ScanJobsPanel: FC = () => {
  // Load scans data
  const { loading, error, data: scans } = useServerScans();
  const visibleScanJobCount = useStore((state) => state.visibleScanJobCount);

  // Clear scan state from store on mount
  const clearScansState = useStore((state) => state.clearScansState);
  useEffect(() => {
    clearScansState();
  }, []);

  return (
    <div className={clsx(styles.container)}>
      <Navbar bordered={false} resultsDir={scans?.results_dir} />
      <ActivityBar animating={loading} />
      <ExtendedFindProvider>
        {error && (
          <ErrorPanel
            title="Error Loading Scans"
            error={{ message: error.message }}
          />
        )}
        {scans && <ScanJobGrid scans={scans} />}
        <Footer
          id={"scan-job-footer"}
          itemCount={visibleScanJobCount || 0}
          paginated={false}
        />
      </ExtendedFindProvider>
    </div>
  );
};
