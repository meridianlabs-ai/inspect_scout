import { r as reactExports, j as jsxRuntimeExports, g as clsx, e as ApplicationIcons } from "./index.js";
const container = "_container_1linb_1";
const input = "_input_1linb_17";
const withIcon = "_withIcon_1linb_25";
const icon = "_icon_1linb_29";
const clearText = "_clearText_1linb_33";
const hidden = "_hidden_1linb_42";
const styles = {
  container,
  input,
  withIcon,
  icon,
  clearText,
  hidden
};
const TextInput = reactExports.forwardRef(
  ({ value, onChange, onFocus, icon: icon2, placeholder, className }, ref) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(
          styles.container,
          className,
          icon2 ? styles.withIcon : ""
        ),
        children: [
          icon2 && /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(icon2, styles.icon) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value,
              onChange,
              ref,
              placeholder,
              className: clsx(styles.input),
              onFocus
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "i",
            {
              className: clsx(
                styles.clearText,
                value === "" ? styles.hidden : "",
                ApplicationIcons["clear-text"]
              ),
              onClick: () => {
                if (onChange && value !== "") {
                  onChange({
                    target: { value: "" }
                  });
                }
              },
              role: "button"
            }
          )
        ]
      }
    );
  }
);
TextInput.displayName = "TextInput";
export {
  TextInput as T
};
//# sourceMappingURL=TextInput.js.map
