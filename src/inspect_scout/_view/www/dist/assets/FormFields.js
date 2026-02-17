import { r as reactExports, j as jsxRuntimeExports } from "./index.js";
import { h as VscodeLabel, i as VscodeFormHelper, f as VscodeTextfield, k as VscodeTextarea, d as VscodeSingleSelect, e as VscodeOption } from "./VscodeTreeItem.js";
const container = "_container_1ch30_1";
const headerRow = "_headerRow_1ch30_7";
const conflictBanner = "_conflictBanner_1ch30_11";
const loading = "_loading_1ch30_15";
const error = "_error_1ch30_16";
const splitLayout = "_splitLayout_1ch30_20";
const header = "_header_1ch30_7";
const detail = "_detail_1ch30_38";
const conflictActions = "_conflictActions_1ch30_56";
const treeNav = "_treeNav_1ch30_69";
const navList = "_navList_1ch30_75";
const navListItem = "_navListItem_1ch30_81";
const navGroup = "_navGroup_1ch30_87";
const navItem = "_navItem_1ch30_100";
const scrollContent = "_scrollContent_1ch30_122";
const field = "_field_1ch30_130";
const section = "_section_1ch30_146";
const sectionHeader = "_sectionHeader_1ch30_153";
const styles = {
  container,
  headerRow,
  conflictBanner,
  loading,
  error,
  splitLayout,
  header,
  detail,
  conflictActions,
  treeNav,
  navList,
  navListItem,
  navGroup,
  navItem,
  scrollContent,
  field,
  section,
  sectionHeader
};
function getInputValue(e) {
  return e.target.value;
}
function getSelectValue(e) {
  return e.target.value;
}
function createSpellcheckRef(selector) {
  return (el) => {
    if (!el) return;
    el.setAttribute("spellcheck", "false");
    const shadowEl = el.shadowRoot?.querySelector(selector);
    if (shadowEl) {
      shadowEl.setAttribute("spellcheck", "false");
    }
  };
}
const TextField = ({
  id,
  label,
  helper,
  value,
  onChange,
  placeholder,
  disabled,
  validate
}) => {
  const [debouncedError, setDebouncedError] = reactExports.useState(null);
  const errorMessage = validate && !disabled ? validate(value ?? null) : null;
  reactExports.useEffect(() => {
    if (errorMessage) {
      const timer = setTimeout(() => setDebouncedError(errorMessage), 1e3);
      return () => clearTimeout(timer);
    } else {
      setDebouncedError(null);
    }
  }, [errorMessage]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: label }),
    helper && /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: helper }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      VscodeTextfield,
      {
        id,
        ref: createSpellcheckRef("input"),
        value: value ?? "",
        disabled,
        onInput: (e) => onChange(getInputValue(e) || null),
        placeholder,
        spellCheck: false,
        autocomplete: "off"
      }
    ),
    debouncedError && /* @__PURE__ */ jsxRuntimeExports.jsx(
      VscodeFormHelper,
      {
        style: { color: "var(--vscode-errorForeground)", marginTop: "4px" },
        children: debouncedError
      }
    )
  ] });
};
function objectToKeyValueLines(value) {
  if (!value) return "";
  if (typeof value === "string") return value;
  return Object.entries(value).map(([k, v]) => `${k}=${String(v)}`).join("\n");
}
function parseKeyValueLines(text) {
  if (!text?.trim()) return null;
  const trimmed = text.trim();
  if (trimmed.startsWith("/") || trimmed.startsWith("./") || trimmed.startsWith("~") || /^[a-zA-Z]:\\/.test(trimmed)) {
    return trimmed;
  }
  const result = {};
  for (const line of text.split("\n")) {
    const lineTrimmed = line.trim();
    if (!lineTrimmed) continue;
    const eqIndex = lineTrimmed.indexOf("=");
    if (eqIndex > 0) {
      const key = lineTrimmed.slice(0, eqIndex).trim();
      const val = lineTrimmed.slice(eqIndex + 1).trim();
      if (key) {
        const num = Number(val);
        if (val !== "" && !isNaN(num)) {
          result[key] = num;
        } else {
          result[key] = val;
        }
      }
    }
  }
  return Object.keys(result).length > 0 ? result : null;
}
const KeyValueField = ({
  id,
  label,
  helper,
  value,
  onChange,
  placeholder = "key=value",
  disabled,
  rows = 3
}) => {
  const [text, setText] = reactExports.useState(() => objectToKeyValueLines(value));
  reactExports.useEffect(() => {
    const configText = objectToKeyValueLines(value);
    const currentParsed = parseKeyValueLines(text);
    const valueParsed = parseKeyValueLines(configText);
    if (JSON.stringify(currentParsed) !== JSON.stringify(valueParsed)) {
      setText(configText);
    }
  }, [value]);
  const handleInput = (newText) => {
    setText(newText);
    onChange(parseKeyValueLines(newText));
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: label }),
    helper && /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: helper }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      VscodeTextarea,
      {
        id,
        ref: createSpellcheckRef("textarea"),
        value: text,
        disabled,
        onInput: (e) => handleInput(getInputValue(e)),
        placeholder,
        rows,
        spellCheck: false,
        autocomplete: "off"
      }
    )
  ] });
};
const NumberField = ({
  id,
  label,
  helper,
  value,
  onChange,
  placeholder,
  disabled,
  step
}) => {
  const handleInput = (e) => {
    const val = getInputValue(e);
    const num = step ? parseFloat(val) : parseInt(val, 10);
    onChange(isNaN(num) ? null : num);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: label }),
    helper && /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: helper }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      VscodeTextfield,
      {
        id,
        type: "number",
        step,
        value: value?.toString() ?? "",
        disabled,
        onInput: handleInput,
        placeholder,
        spellCheck: false,
        autocomplete: "off"
      }
    )
  ] });
};
function SelectField({
  id,
  label,
  helper,
  value,
  options,
  onChange,
  disabled,
  defaultLabel = "Default"
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: label }),
    helper && /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: helper }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      VscodeSingleSelect,
      {
        id,
        value: value ?? "",
        disabled,
        onChange: (e) => {
          const val = getSelectValue(e);
          onChange(val ? val : null);
        },
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "", children: defaultLabel }),
          options.map((opt) => /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: opt, children: opt }, opt))
        ]
      }
    )
  ] });
}
function Field({ label, helper, children }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.field, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeLabel, { children: label }),
    helper && /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeFormHelper, { children: helper }),
    children
  ] });
}
export {
  Field as F,
  KeyValueField as K,
  NumberField as N,
  SelectField as S,
  TextField as T,
  styles as s
};
//# sourceMappingURL=FormFields.js.map
