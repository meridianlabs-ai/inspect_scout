import { j as jsxRuntimeExports, c as clsx, A as ApplicationIcons } from "./index.js";
const panel = "_panel_twp3v_1";
const container = "_container_twp3v_7";
const styles = {
  panel,
  container
};
const NoContentsPanel = ({ text, icon }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles.panel), children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles.container, "text-size-smaller"), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: icon || ApplicationIcons.noSamples }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: text })
  ] }) });
};
export {
  NoContentsPanel as N
};
//# sourceMappingURL=NoContentsPanel.js.map
