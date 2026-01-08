import { clsx } from "clsx";
import { FC, useEffect } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { LoadingBar } from "../../components/LoadingBar";
import { useStore } from "../../state/store";
import { Footer } from "../components/Footer";
import { ScansNavbar } from "../components/ScansNavbar";
import { useConfig } from "../server/useConfig";
import { useServerScans } from "../server/useServerScans";

import { ScansGrid } from "./ScansGrid";
import styles from "./ScansPanel.module.css";

export const ScansPanel: FC = () => {
  // Load scans data
  const { loading, error, data: scans } = useServerScans();
  const config = useConfig();
  const scanDir = config.scans_dir;
  const visibleScanJobCount = useStore((state) => state.visibleScanJobCount);
  const userScansDir = useStore((state) => state.userScansDir);
  const setScanDir = useStore((state) => state.setUserScansDir);

  // Clear scan state from store on mount
  const clearScansState = useStore((state) => state.clearScansState);
  useEffect(() => {
    clearScansState();
  }, []);

  return (
    <div className={clsx(styles.container)}>
      <ScansNavbar
        scansDir={userScansDir || scanDir}
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
        {scans && <ScansGrid scans={scans} resultsDir={scanDir} />}
        <Footer
          id={"scan-job-footer"}
          itemCount={visibleScanJobCount || 0}
          paginated={false}
        />
      </ExtendedFindProvider>
    </div>
  );
};
