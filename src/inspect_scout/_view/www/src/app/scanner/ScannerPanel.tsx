import clsx from "clsx";
import React from "react";

import { ActivityBar } from "../../components/ActivityBar";
import { ExtendedFindProvider } from "../../components/ExtendedFindProvider";
import { useStore } from "../../state/store";
import { useServerScanner, useServerScans } from "../hooks";
import { Navbar } from "../navbar/Navbar";

import styles from "./ScannerPanel.module.css";
import { ScannerPanelBody } from "./ScannerPanelBody";
import { ScannerPanelTitle } from "./ScannerPanelTitle";

export const ScannerPanel: React.FC = () => {
  useServerScans();
  useServerScanner();

  const singleFileMode = useStore((state) => state.singleFileMode);
  const loading = useStore((state) => state.loading);

  return (
    <div className={clsx(styles.root)}>
      {singleFileMode || <Navbar />}
      <ActivityBar animating={!!loading} />
      <ScannerPanelTitle />
      <ExtendedFindProvider>
        <ScannerPanelBody />
      </ExtendedFindProvider>
    </div>
  );
};
