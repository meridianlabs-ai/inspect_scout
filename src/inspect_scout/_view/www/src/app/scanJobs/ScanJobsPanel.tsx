import { FC } from "react";

import { ActivityBar } from "../../components/ActivityBar";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { useStore } from "../../state/store";
import { useServerScans } from "../hooks";
import { Navbar } from "../navbar/Navbar";

import { ScanJobGrid } from "./ScanJobGrid";

export const ScanJobsPanel: FC = () => {
  const loading = useStore((state) => state.loading);

  useServerScans();

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
