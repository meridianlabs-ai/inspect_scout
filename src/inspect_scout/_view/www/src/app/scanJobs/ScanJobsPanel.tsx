import { clsx } from "clsx";
import { FC, useEffect } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { LoadingBar } from "../../components/LoadingBar";
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

  // Clear scan state from store on mount
  const clearScansState = useStore((state) => state.clearScansState);
  useEffect(() => {
    clearScansState();
  }, []);

  return (
    <div className={clsx(styles.container)}>
      <Navbar bordered={false} />
      <LoadingBar loading={!!loading} />
      <ExtendedFindProvider>
        {error && (
          <ErrorPanel title="Error Loading Scans" error={{ message: error }} />
        )}
        {!error && <ScanJobGrid />}
        <Footer
          id={"scan-job-footer"}
          itemCount={visibleScanJobCount || 0}
          paginated={false}
        />
      </ExtendedFindProvider>
    </div>
  );
};
