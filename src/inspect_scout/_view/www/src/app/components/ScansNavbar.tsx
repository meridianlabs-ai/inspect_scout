import { FC, ReactNode, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { scanRoute, scansRoute } from "../../router/url";
import { useStore } from "../../state/store";
import { dirname } from "../../utils/path";
import { ApplicationIcons } from "../appearance/icons";
import { useScanRoute } from "../hooks";

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
  const {
    relativePath,
    scanPath,
    scanResultUuid,
    scansDir: routeScansDir,
  } = useScanRoute();
  const singleFileMode = useStore((state) => state.singleFileMode);
  const [searchParams] = useSearchParams();

  // Check if we're on a scan result page and calculate the appropriate back URL
  const resolvedScansDir = routeScansDir || scansDir;

  const backUrl =
    resolvedScansDir && scanResultUuid
      ? scanRoute(resolvedScansDir, scanPath, searchParams)
      : !singleFileMode && resolvedScansDir
        ? scansRoute(resolvedScansDir, dirname(relativePath || ""))
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

    if (!singleFileMode && resolvedScansDir) {
      buttons.push({
        title: "Home",
        icon: ApplicationIcons.navbar.home,
        route: scansRoute(resolvedScansDir),
        enabled: !!scanPath,
      });
    }

    return buttons;
  }, [backUrl, singleFileMode, scanPath, resolvedScansDir]);

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
