import { j as jsxRuntimeExports, r as reactExports, c as clsx } from "./index.js";
import { x as useStatefulScrollPosition } from "./TranscriptViewNodes.js";
const tabs = "_tabs_tfvnu_1";
const tabContents = "_tabContents_tfvnu_5";
const scrollable = "_scrollable_tfvnu_10";
const tab = "_tab_tfvnu_1";
const tabItem = "_tabItem_tfvnu_26";
const tabIcon = "_tabIcon_tfvnu_30";
const tabTools = "_tabTools_tfvnu_34";
const tabStyle = "_tabStyle_tfvnu_44";
const moduleStyles = {
  tabs,
  tabContents,
  scrollable,
  tab,
  tabItem,
  tabIcon,
  tabTools,
  tabStyle
};
const TabSet = ({
  id,
  type = "tabs",
  className,
  tabPanelsClassName,
  tabControlsClassName,
  tools,
  tabsRef,
  children
}) => {
  const validTabs = flattenChildren(children);
  if (validTabs.length === 0) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "ul",
      {
        ref: tabsRef,
        id,
        className: clsx(
          "nav",
          `nav-${type}`,
          type === "tabs" ? moduleStyles.tabStyle : void 0,
          className,
          moduleStyles.tabs
        ),
        role: "tablist",
        "aria-orientation": "horizontal",
        children: [
          validTabs.map((tab2, index) => /* @__PURE__ */ jsxRuntimeExports.jsx(
            Tab,
            {
              index,
              type,
              tab: tab2,
              className: clsx(tabControlsClassName)
            },
            tab2.props.id
          )),
          tools && /* @__PURE__ */ jsxRuntimeExports.jsx(TabTools, { tools })
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(TabPanels, { id, tabs: validTabs, className: tabPanelsClassName })
  ] });
};
const Tab = ({ type = "tabs", tab: tab2, index, className }) => {
  const tabId = tab2.props.id || computeTabId("tabset", index);
  const tabContentsId = computeTabContentsId(tab2.props.id);
  const isActive = tab2.props.selected;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("li", { role: "presentation", className: clsx("nav-item", moduleStyles.tabItem), children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "button",
    {
      id: tabId,
      className: clsx(
        "nav-link",
        className,
        isActive && "active",
        type === "pills" ? moduleStyles.pill : moduleStyles.tab,
        "text-size-small",
        "text-style-label"
      ),
      type: "button",
      role: "tab",
      "aria-controls": tabContentsId,
      "aria-selected": isActive,
      onClick: tab2.props.onSelected,
      children: [
        tab2.props.icon && /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(tab2.props.icon, moduleStyles.tabIcon) }),
        tab2.props.title
      ]
    }
  ) });
};
const TabPanels = ({ id, tabs: tabs2, className }) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("tab-content", className), id: `${id}-content`, children: tabs2.map((tab2, index) => /* @__PURE__ */ jsxRuntimeExports.jsx(TabPanel, { ...tab2.props, index }, tab2.props.id)) });
const TabPanel = ({
  id,
  selected,
  style,
  scrollable: scrollable2 = true,
  scrollRef,
  className,
  children
}) => {
  const tabContentsId = computeTabContentsId(id);
  const panelRef = reactExports.useRef(null);
  const tabContentsRef = scrollRef || panelRef;
  useStatefulScrollPosition(tabContentsRef, tabContentsId, 1e3, scrollable2);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      id: tabContentsId,
      ref: tabContentsRef,
      className: clsx(
        "tab-pane",
        selected && "show active",
        className,
        moduleStyles.tabContents,
        scrollable2 && moduleStyles.scrollable
      ),
      style,
      children: selected ? children : null
    }
  );
};
const TabTools = ({ tools }) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("tab-tools", moduleStyles.tabTools), children: tools });
const computeTabId = (id, index) => `${id}-${index}`;
const computeTabContentsId = (id) => `${id}-contents`;
const flattenChildren = (children) => {
  return reactExports.Children.toArray(children).flatMap((child) => {
    if (reactExports.isValidElement(child)) {
      const element = child;
      if (element.type === reactExports.Fragment) {
        return flattenChildren(element.props.children);
      }
      return element;
    }
    return [];
  });
};
const TaskName = ({
  taskSet,
  taskId,
  taskRepeat
}) => {
  if (!taskSet && !taskId && taskRepeat === void 0) {
    return "<unknown>";
  }
  const results = [];
  if (taskSet) {
    results.push(/* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: taskSet }, "task-column-task-set"));
  }
  if (taskId !== void 0 && taskId !== null) {
    results.push("/", /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: taskId }, "task-column-task-id"));
  }
  if (taskRepeat !== void 0 && taskRepeat !== null) {
    results.push(
      " ",
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "span",
        {
          className: clsx("text-style-secondary", "text-size-smallest"),
          children: `(${taskRepeat})`
        },
        "task-column-task-repeat"
      )
    );
  }
  return results;
};
export {
  TaskName as T,
  TabSet as a,
  TabPanel as b
};
//# sourceMappingURL=TaskName.js.map
