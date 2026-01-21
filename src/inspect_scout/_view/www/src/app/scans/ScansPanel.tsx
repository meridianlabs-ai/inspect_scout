import { clsx } from "clsx";
import { FC, useEffect } from "react";

import { ErrorPanel } from "../../components/ErrorPanel";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { ApplicationIcons } from "../../components/icons";
import { LoadingBar } from "../../components/LoadingBar";
import { NoContentsPanel } from "../../components/NoContentsPanel";
import { useStore } from "../../state/store";
import { Footer } from "../components/Footer";
import { ScansNavbar } from "../components/ScansNavbar";
import { useConfig } from "../server/useConfig";
import { useScans } from "../server/useScans";
import { useScansDir } from "../utils/useScansDir";

import { ScansGrid } from "./ScansGrid";
import styles from "./ScansPanel.module.css";

export const ScansPanel: FC = () => {
  // Load scans data
  const { loading, error, data: scans } = useScans();
  const config = useConfig();
  const scanDir = config.scans.dir;
  const visibleScanJobCount = useStore((state) => state.visibleScanJobCount);
  const { displayScansDir, resolvedScansDirSource, setScansDir } =
    useScansDir();

  // Clear scan state from store on mount
  const clearScansState = useStore((state) => state.clearScansState);
  useEffect(() => {
    clearScansState();
  }, []);

  return (
    <div className={clsx(styles.container)}>
      <ScansNavbar
        scansDir={displayScansDir}
        scansDirSource={resolvedScansDirSource}
        setScansDir={setScansDir}
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
        {!scans && !error && (
          <NoContentsPanel icon={ApplicationIcons.running} text="Loading..." />
        )}
        {scans && !error && <ScansGrid scans={scans} resultsDir={scanDir} />}
        <Footer
          id={"scan-job-footer"}
          itemCount={visibleScanJobCount || 0}
          paginated={false}
        />
      </ExtendedFindProvider>
    </div>
  );
};
