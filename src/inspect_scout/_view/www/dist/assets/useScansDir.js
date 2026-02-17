import { G as useParams, u as useStore, e as useAppConfig, r as reactExports, W as parseScanParams, i as useSearchParams, d as scanRoute, X as scansRoute, V as dirname, A as ApplicationIcons, j as jsxRuntimeExports, T as appAliasedPath } from "./index.js";
import { j as join, N as Navbar, E as EditablePath } from "./Navbar.js";
const useScanRoute = () => {
  const params = useParams();
  const setUserScansDir = useStore((state) => state.setUserScansDir);
  const config = useAppConfig();
  const scansDir = config.scans.dir;
  const route = reactExports.useMemo(() => parseScanParams(params), [params]);
  const resolvedScansDir = route.scansDir || scansDir;
  const location = resolvedScansDir ? join(route.scanPath, resolvedScansDir) : void 0;
  reactExports.useEffect(() => {
    if (route.scansDir) {
      setUserScansDir(route.scansDir);
    }
  }, [route.scansDir, setUserScansDir]);
  return {
    ...route,
    resolvedScansDir,
    location
  };
};
const ScansNavbar = ({
  scansDir,
  scansDirSource,
  setScansDir,
  bordered = true,
  children
}) => {
  const {
    relativePath,
    scanPath,
    scanResultUuid,
    scansDir: routeScansDir
  } = useScanRoute();
  const singleFileMode = useStore((state) => state.singleFileMode);
  const [searchParams] = useSearchParams();
  const resolvedScansDir = routeScansDir || scansDir;
  const backUrl = resolvedScansDir && scanResultUuid ? scanRoute(resolvedScansDir, scanPath, searchParams) : !singleFileMode && resolvedScansDir ? scansRoute(resolvedScansDir, dirname(relativePath || "")) : void 0;
  const navButtons = reactExports.useMemo(() => {
    const buttons = [];
    if (backUrl) {
      buttons.push({
        title: "Back",
        icon: ApplicationIcons.navbar.back,
        route: backUrl,
        enabled: !!scanPath
      });
    }
    if (!singleFileMode && resolvedScansDir) {
      buttons.push({
        title: "Home",
        icon: ApplicationIcons.navbar.home,
        route: scansRoute(resolvedScansDir),
        enabled: !!scanPath
      });
    }
    return buttons;
  }, [backUrl, singleFileMode, scanPath, resolvedScansDir]);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    Navbar,
    {
      bordered,
      right: children,
      leftButtons: navButtons.length > 0 ? navButtons : void 0,
      left: scansDir ? /* @__PURE__ */ jsxRuntimeExports.jsx(
        EditablePath,
        {
          path: scansDir,
          label: "Scans",
          icon: scansDirSource === "cli" ? ApplicationIcons.terminal : void 0,
          title: scansDirSource === "cli" ? "Scans directory set via command line" : void 0,
          onPathChanged: setScansDir,
          placeholder: "Select Scans Folder",
          className: "text-size-smallest",
          editable: false
        }
      ) : void 0
    }
  );
};
function useScansDir(useRouteParam = false) {
  const config = useAppConfig();
  const { scansDir: routeScansDir } = useScanRoute();
  const userScansDir = useStore((state) => state.userScansDir);
  const setUserScansDir = useStore((state) => state.setUserScansDir);
  const resolvedPath = (useRouteParam ? routeScansDir : null) || userScansDir || config.scans.dir || "";
  const scanDirSource = useRouteParam && routeScansDir ? "route" : userScansDir ? "user" : config.scans.source === "cli" ? "cli" : "project";
  const displayPath = appAliasedPath(config, resolvedPath) || "";
  return {
    displayScansDir: displayPath,
    resolvedScansDir: resolvedPath,
    resolvedScansDirSource: scanDirSource,
    setScansDir: setUserScansDir
  };
}
export {
  ScansNavbar as S,
  useScanRoute as a,
  useScansDir as u
};
//# sourceMappingURL=useScansDir.js.map
