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
  useServerScans();
  const loading = useStore((state) => state.loading);
  const error = useStore((state) => state.scopedErrors["scanjobs"]);
  const visibleScanJobCount = useStore((state) => state.visibleScanJobCount);
  const resultsDir = useStore((state) => state.resultsDir);

  // Clear scan state from store on mount
  const clearScansState = useStore((state) => state.clearScansState);
  useEffect(() => {
    clearScansState();
  }, []);

  return (
    <div className={clsx(styles.container)}>
      <Navbar bordered={false} resultsDir={resultsDir} />
      <ActivityBar animating={!!loading} />
      <ExtendedFindProvider>
        {error && (
          <ErrorPanel title="Error Loading Scans" error={{ message: error }} />
        )}
        {!error && <ScanJobGrid resultsDir={resultsDir} />}
        <Footer
          id={"scan-job-footer"}
          itemCount={visibleScanJobCount || 0}
          paginated={false}
        />
      </ExtendedFindProvider>
    </div>
  );
};
