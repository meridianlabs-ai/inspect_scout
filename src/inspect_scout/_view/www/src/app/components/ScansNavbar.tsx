import { FC, ReactNode, useMemo } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import {
  getRelativePathFromParams,
  parseScanResultPath,
  scanRoute,
  scansRoute,
} from "../../router/url";
import { useStore } from "../../state/store";
import { dirname } from "../../utils/path";
import { ApplicationIcons } from "../appearance/icons";

import { EditablePath } from "./EditablePath";
import { Navbar } from "./Navbar";
import { NavButton } from "./NavButtons";

interface ScansNavbarProps {
  scansDir?: string;
  setScansDir: (path: string) => void;
  children?: ReactNode;
  bordered?: boolean;
}

export const ScansNavbar: FC<ScansNavbarProps> = ({
  scansDir,
  setScansDir,
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

  const navButtons: NavButton[] = useMemo(() => {
    const buttons: NavButton[] = [];

    if (backUrl) {
      buttons.push({
        title: "Back",
        icon: ApplicationIcons.navbar.back,
        route: backUrl,
        enabled: !!scanPath,
      });
    }

    if (!singleFileMode) {
      buttons.push({
        title: "Home",
        icon: ApplicationIcons.navbar.home,
        route: scansRoute(),
        enabled: !!scanPath,
      });
    }

    return buttons;
  }, [backUrl, singleFileMode, scanPath]);

  return (
    <Navbar
      bordered={bordered}
      right={children}
      leftButtons={navButtons}
      left={
        scansDir ? (
          <EditablePath
            path={scansDir}
            label="Scans"
            icon={ApplicationIcons.scanner}
            onPathChanged={setScansDir}
            placeholder="Select Scans Folder"
            className="text-size-smallest"
            editable={false}
          />
        ) : undefined
      }
    />
  );
};
