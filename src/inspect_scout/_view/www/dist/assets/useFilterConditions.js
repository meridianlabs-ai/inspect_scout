import { r as reactExports, Y as AppModeContext, u as useStore, i as useSearchParams, G as useParams, Z as transcriptsRoute, A as ApplicationIcons, j as jsxRuntimeExports } from "./index.js";
import { N as Navbar, E as EditablePath } from "./Navbar.js";
const TranscriptsNavbar = ({
  transcriptsDir,
  transcriptsDirSource,
  filter,
  setTranscriptsDir,
  bordered = true,
  children
}) => {
  const appMode = reactExports.useContext(AppModeContext);
  const showNavButtons = appMode !== "workbench";
  const singleFileMode = useStore((state) => state.singleFileMode);
  const [searchParams] = useSearchParams();
  const params = useParams();
  const transcriptId = params["transcriptId"];
  const backUrl = !singleFileMode ? transcriptsRoute(searchParams) : void 0;
  const navButtons = reactExports.useMemo(() => {
    const buttons = [];
    if (backUrl) {
      buttons.push({
        title: "Back",
        icon: ApplicationIcons.navbar.back,
        route: backUrl,
        enabled: !!transcriptId
      });
    }
    if (!singleFileMode) {
      buttons.push({
        title: "Home",
        icon: ApplicationIcons.navbar.home,
        route: transcriptsRoute(),
        enabled: !!transcriptId
      });
    }
    return buttons;
  }, [backUrl, singleFileMode]);
  const editable = false;
  const filterText = filter && !filter?.startsWith("(") ? `(${filter})` : filter ? filter : void 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    Navbar,
    {
      bordered,
      leftButtons: showNavButtons ? navButtons : void 0,
      left: /* @__PURE__ */ jsxRuntimeExports.jsx(
        EditablePath,
        {
          path: transcriptsDir,
          secondaryText: filterText,
          label: "Transcripts",
          icon: transcriptsDirSource === "cli" ? ApplicationIcons.terminal : void 0,
          title: transcriptsDirSource === "cli" ? "Using transcripts directory from command line." : void 0,
          onPathChanged: setTranscriptsDir,
          placeholder: "No transcripts directory configured.",
          className: "text-size-smallest",
          editable
        }
      ),
      right: children
    }
  );
};
const useFilterConditions = (excludeColumnId) => {
  const columnFilters = useStore((state) => state.transcriptsTableState.columnFilters) ?? {};
  const filterConditions = Object.values(columnFilters).filter((filter) => !excludeColumnId || filter.columnId !== excludeColumnId).map((filter) => filter.condition).filter((condition2) => Boolean(condition2));
  const condition = filterConditions.reduce(
    (acc, condition2) => acc ? acc.and(condition2) : condition2,
    void 0
  );
  return condition;
};
export {
  TranscriptsNavbar as T,
  useFilterConditions as u
};
//# sourceMappingURL=useFilterConditions.js.map
