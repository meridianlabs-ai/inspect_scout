import { FC, useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { ApplicationIcons } from "../../components/icons";
import { transcriptsRoute } from "../../router/url";
import { useStore } from "../../state/store";

import { EditablePath } from "./EditablePath";
import { Navbar } from "./Navbar";
import { NavButton } from "./NavButtons";

interface TranscriptsNavbarProps {
  transcriptsDir?: string | null;
  setTranscriptsDir: (path: string) => void;
  bordered?: boolean;
  children?: React.ReactNode;
}

export const TranscriptsNavbar: FC<TranscriptsNavbarProps> = ({
  transcriptsDir,
  setTranscriptsDir,
  bordered = true,
  children,
}) => {
  const singleFileMode = useStore((state) => state.singleFileMode);
  const [searchParams] = useSearchParams();

  const params = useParams<{ "*": string }>();
  const transcriptId = params["transcriptId"];

  // Check if we're on a scan result page and calculate the appropriate back URL
  const backUrl = !singleFileMode ? transcriptsRoute(searchParams) : undefined;

  const navButtons: NavButton[] = useMemo(() => {
    const buttons: NavButton[] = [];

    if (backUrl) {
      buttons.push({
        title: "Back",
        icon: ApplicationIcons.navbar.back,
        route: backUrl,
        enabled: !!transcriptId,
      });
    }

    if (!singleFileMode) {
      buttons.push({
        title: "Home",
        icon: ApplicationIcons.navbar.home,
        route: transcriptsRoute(),
        enabled: !!transcriptId,
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
          path={transcriptsDir}
          label="Transcripts"
          icon={ApplicationIcons.transcript}
          onPathChanged={setTranscriptsDir}
          placeholder="Select Transcripts Folder"
          className="text-size-smallest"
          editable={false}
        />
      }
      right={children}
    />
  );
};
