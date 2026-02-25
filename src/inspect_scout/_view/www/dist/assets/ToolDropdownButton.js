import { r as reactExports, j as jsxRuntimeExports, c as clsx } from "./index.js";
const dropdownContainer = "_dropdownContainer_1fize_1";
const toolButton = "_toolButton_1fize_7";
const bodyColor = "_bodyColor_1fize_11";
const chevron = "_chevron_1fize_27";
const backdrop = "_backdrop_1fize_41";
const dropdownMenu = "_dropdownMenu_1fize_50";
const alignRight = "_alignRight_1fize_64";
const dropdownItem = "_dropdownItem_1fize_69";
const styles = {
  dropdownContainer,
  toolButton,
  bodyColor,
  chevron,
  backdrop,
  dropdownMenu,
  alignRight,
  dropdownItem
};
const ToolDropdownButton = reactExports.forwardRef(
  ({
    label,
    icon,
    className,
    items,
    dropdownAlign = "left",
    dropdownClassName,
    subtle,
    ...rest
  }, ref) => {
    const [isOpen, setIsOpen] = reactExports.useState(false);
    const handleItemClick = (fn) => {
      fn();
      setIsOpen(false);
    };
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles.dropdownContainer), children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          ref,
          type: "button",
          className: clsx(
            "btn",
            "btn-tools",
            styles.toolButton,
            subtle ? styles.bodyColor : void 0,
            className
          ),
          onClick: () => setIsOpen(!isOpen),
          ...rest,
          children: [
            icon && /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: `${icon}` }),
            label,
            /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx("bi-chevron-down", styles.chevron) })
          ]
        }
      ),
      isOpen && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.backdrop, onClick: () => setIsOpen(false) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              styles.dropdownMenu,
              dropdownAlign === "right" ? styles.alignRight : void 0,
              dropdownClassName
            ),
            children: Object.entries(items).map(([itemLabel, fn]) => /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                type: "button",
                className: styles.dropdownItem,
                onClick: () => handleItemClick(fn),
                children: itemLabel
              },
              itemLabel
            ))
          }
        )
      ] })
    ] });
  }
);
ToolDropdownButton.displayName = "ToolDropdownButton";
export {
  ToolDropdownButton as T
};
//# sourceMappingURL=ToolDropdownButton.js.map
