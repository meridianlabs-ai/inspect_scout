import { FC, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { transcriptsRoute } from "../../router/url";
import { useStore } from "../../state/store";
import { ApplicationIcons } from "../appearance/icons";

import { EditablePath } from "./EditablePath";
import { Navbar } from "./Navbar";
import { NavButton } from "./NavButtons";

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
  const singleFileMode = useStore((state) => state.singleFileMode);
  const [searchParams] = useSearchParams();

  // Check if we're on a scan result page and calculate the appropriate back URL
  const backUrl = !singleFileMode ? transcriptsRoute(searchParams) : undefined;

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
      leftButtons={navButtons}
      left={
        <EditablePath
          path={transcriptDir}
          label="Transcripts Dir"
          icon={ApplicationIcons.transcript}
          onPathChanged={setTranscriptDir}
          placeholder="Select Transcripts Folder"
          className="text-size-smallest"
        />
      }
      right={children}
    />
  );
};
