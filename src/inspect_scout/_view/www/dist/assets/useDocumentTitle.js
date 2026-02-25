import { r as reactExports } from "./index.js";
const APP_NAME = "Inspect Scout";
function useDocumentTitle(...segments) {
  const filtered = segments.filter((s) => Boolean(s));
  const title = filtered.length > 0 ? `${filtered.join(" - ")} - ${APP_NAME}` : APP_NAME;
  reactExports.useEffect(() => {
    document.title = title;
  }, [title]);
}
export {
  useDocumentTitle as u
};
//# sourceMappingURL=useDocumentTitle.js.map
