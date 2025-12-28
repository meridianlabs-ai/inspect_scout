import { FC, ReactNode, useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import {
  getRelativePathFromParams,
  isValidTranscriptPath,
  transcriptRoute,
  transcriptsRoute,
} from "../../router/url";
import { useStore } from "../../state/store";
import { ApplicationIcons } from "../appearance/icons";

import { BreadCrumbs } from "./BreadCrumbs";
import { Navbar } from "./Navbar";
import { NavButton, NavButtons } from "./NavButtons";
import styles from "./TranscriptNavbar.module.css";

interface TranscriptNavbarProps {
  transcriptsDir?: string;
  bordered?: boolean;
  children?: ReactNode;
}

export const TranscriptNavbar: FC<TranscriptNavbarProps> = ({
  transcriptsDir,
  bordered = true,
  children,
}) => {
  const params = useParams<{ "*": string }>();
  const currentPath = getRelativePathFromParams(params);
  const singleFileMode = useStore((state) => state.singleFileMode);
  const [searchParams] = useSearchParams();

  // Check if we're on a scan result page and calculate the appropriate back URL
  const backUrl = !singleFileMode ? transcriptsRoute(searchParams) : undefined;

  const getRouteForSegment = (path: string): string => {
    if (!path) {
      return transcriptsRoute();
    }
    // Check if this segment path contains a valid scan_id pattern
    // If so, use scanRoute instead of scansRoute
    return isValidTranscriptPath(path)
      ? transcriptRoute(path, searchParams)
      : transcriptsRoute(searchParams);
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
        route: transcriptsRoute(),
      });
    }

    return buttons;
  }, [backUrl, singleFileMode]);

  return (
    <Navbar
      bordered={bordered}
      right={children}
      left={
        transcriptsDir ? (
          <div className={styles.leftContainer}>
            <NavButtons buttons={navButtons} />
            <BreadCrumbs
              baseDir={transcriptsDir}
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
