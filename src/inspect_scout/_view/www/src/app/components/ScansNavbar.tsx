import { FC, ReactNode, useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import {
  getRelativePathFromParams,
  isValidScanPath,
  parseScanResultPath,
  scanRoute,
  scansRoute,
} from "../../router/url";
import { useStore } from "../../state/store";
import { dirname } from "../../utils/path";
import { ApplicationIcons } from "../appearance/icons";

import { BreadCrumbs } from "./BreadCrumbs";
import { Navbar } from "./Navbar";
import { NavButton, NavButtons } from "./NavButtons";
import styles from "./ScansNavbar.module.css";

interface ScansNavbarProps {
  resultsDir?: string;
  children?: ReactNode;
  bordered?: boolean;
}

export const ScansNavbar: FC<ScansNavbarProps> = ({
  resultsDir,
  bordered = true,
  children,
}) => {
  const params = useParams<{ "*": string }>();
  const currentPath = getRelativePathFromParams(params);
  const singleFileMode = useStore((state) => state.singleFileMode);
  const [searchParams] = useSearchParams();

  // Check if we're on a scan result page and calculate the appropriate back URL
  const { scanPath, scanResultUuid } = parseScanResultPath(currentPath);
  const backUrl = scanResultUuid
    ? scanRoute(scanPath, searchParams)
    : !singleFileMode
      ? scansRoute(dirname(currentPath || ""))
      : undefined;

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

  const navButtons: NavButton[] = useMemo(() => {
    const buttons: NavButton[] = [];

    if (backUrl) {
      buttons.push({
        title: "Back",
        icon: ApplicationIcons.navbar.back,
        route: backUrl,
      });
    }

    if (!singleFileMode) {
      buttons.push({
        title: "Home",
        icon: ApplicationIcons.navbar.home,
        route: scansRoute(),
      });
    }

    return buttons;
  }, [backUrl, singleFileMode]);

  return (
    <Navbar
      bordered={bordered}
      right={children}
      left={
        resultsDir ? (
          <div className={styles.leftContainer}>
            <NavButtons buttons={navButtons} />
            <BreadCrumbs
              baseDir={resultsDir}
              relativePath={currentPath}
              getRouteForSegment={getRouteForSegment}
              disableLastSegment={!singleFileMode}
            />
          </div>
        ) : undefined
      }
    />
  );
};
