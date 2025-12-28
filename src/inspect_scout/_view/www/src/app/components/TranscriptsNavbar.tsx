import { FC, useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import {
  getRelativePathFromParams,
  transcriptsRoute,
  isValidTranscriptPath,
  transcriptRoute,
} from "../../router/url";
import { useStore } from "../../state/store";
import { ApplicationIcons } from "../appearance/icons";

import { EditablePath } from "./EditablePath";
import { Navbar } from "./Navbar";
import { NavButton, NavButtons } from "./NavButtons";
import styles from "./TranscriptsNavbar.module.css";

interface TranscriptsNavbarProps {
  transcriptDir?: string;
  setTranscriptDir: (path: string) => void;
  bordered?: boolean;
  children?: React.ReactNode;
}

export const TranscriptsNavbar: FC<TranscriptsNavbarProps> = ({
  transcriptDir,
  setTranscriptDir,
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
        enabled: false,
      });
    }

    if (!singleFileMode) {
      buttons.push({
        title: "Home",
        icon: ApplicationIcons.navbar.home,
        route: transcriptsRoute(),
        enabled: false,
      });
    }

    return buttons;
  }, [backUrl, singleFileMode]);

  return (
    <Navbar
      bordered={bordered}
      left={
        <div className={styles.leftContainer}>
          <NavButtons buttons={navButtons} />
          <div className={styles.divider} />
          <EditablePath
            path={transcriptDir}
            label="Transcripts"
            icon={ApplicationIcons.transcript}
            onPathChanged={setTranscriptDir}
            placeholder="Select Transcripts Folder"
            className="text-size-smallest"
          />
        </div>
      }
      right={children}
    />
  );
};
