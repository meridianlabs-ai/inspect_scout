import { FC, useEffect } from "react";

import { ActivityBar } from "../../components/ActivityBar";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { useStore } from "../../state/store";
import { useServerScans } from "../hooks";
import { Navbar } from "../navbar/Navbar";

import { ScanJobGrid } from "./ScanJobGrid";

export const ScanJobsPanel: FC = () => {
  // Load scans data
  useServerScans();
  const loading = useStore((state) => state.loading);

  // Clear scan state from store on mount
  const clearScansState = useStore((state) => state.clearScansState);
  useEffect(() => {
    clearScansState();
  }, []);

  return (
    <>
      <Navbar bordered={false} />
      <ActivityBar animating={!!loading} />
      <ExtendedFindProvider>
        <ScanJobGrid />
      </ExtendedFindProvider>
    </>
  );
};
