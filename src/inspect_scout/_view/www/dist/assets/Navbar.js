import { r as reactExports, j as jsxRuntimeExports, c as clsx, $ as Link } from "./index.js";
import { P as PopOver } from "./ToolButton.js";
const join = (file, dir) => {
  if (!dir) {
    return file;
  }
  let normalizedFile = file.replace(/\\/g, "/");
  if (normalizedFile.startsWith("./")) {
    normalizedFile = normalizedFile.slice(2);
  }
  const normalizedLogDir = dir.replace(/\\/g, "/");
  const dirWithSlash = normalizedLogDir.endsWith("/") ? normalizedLogDir : normalizedLogDir + "/";
  return dirWithSlash + normalizedFile;
};
const isUri = (value) => {
  if (!value) return false;
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
};
const prettyDirUri = (uri) => {
  if (uri.startsWith("file://")) {
    return uri.replace("file://", "");
  } else {
    return uri;
  }
};
const container = "_container_at9ra_1";
const labelContainer = "_labelContainer_at9ra_10";
const icon = "_icon_at9ra_22";
const text = "_text_at9ra_28";
const readOnly = "_readOnly_at9ra_41";
const placeholder = "_placeholder_at9ra_55";
const secondary = "_secondary_at9ra_60";
const mruPopover = "_mruPopover_at9ra_66";
const mruList = "_mruList_at9ra_73";
const mruItem = "_mruItem_at9ra_79";
const mruItemSelected = "_mruItemSelected_at9ra_90";
const styles$2 = {
  container,
  labelContainer,
  icon,
  text,
  readOnly,
  placeholder,
  secondary,
  mruPopover,
  mruList,
  mruItem,
  mruItemSelected
};
const EditableText = ({
  value,
  secondaryValue,
  onValueChanged,
  mru,
  mruMaxItems = 10,
  icon: icon2,
  label,
  title,
  placeholder: placeholder2,
  editable = true,
  className
}) => {
  const spanRef = reactExports.useRef(null);
  const initialValueRef = reactExports.useRef("");
  const containerRef = reactExports.useRef(null);
  const [showMruPopover, setShowMruPopover] = reactExports.useState(false);
  const [selectedMruIndex, setSelectedMruIndex] = reactExports.useState(-1);
  const [currentText, setCurrentText] = reactExports.useState("");
  const [isEditing, setIsEditing] = reactExports.useState(false);
  const [isFocused, setIsFocused] = reactExports.useState(false);
  const filteredMru = reactExports.useMemo(() => {
    if (!mru || mru.length === 0) return [];
    if (!isEditing || currentText === initialValueRef.current) {
      return mru.slice(0, mruMaxItems);
    }
    const filtered = mru.filter(
      (item) => item.toLowerCase().startsWith(currentText.toLowerCase())
    ).slice(0, mruMaxItems);
    return filtered.length > 0 ? filtered : mru.slice(0, mruMaxItems);
  }, [mru, mruMaxItems, currentText, isEditing]);
  reactExports.useEffect(() => {
    setShowMruPopover(filteredMru.length > 0 && isFocused);
  }, [filteredMru, isFocused]);
  const handleFocus = () => {
    if (spanRef.current) {
      initialValueRef.current = spanRef.current.textContent || "";
      setCurrentText(initialValueRef.current);
      setSelectedMruIndex(-1);
      setIsEditing(false);
      setIsFocused(true);
      const range = document.createRange();
      range.selectNodeContents(spanRef.current);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
    }
  };
  const commitChanges = reactExports.useCallback(() => {
    if (spanRef.current) {
      const newValue = spanRef.current.textContent?.trim() || "";
      if (newValue !== "" && newValue !== initialValueRef.current) {
        onValueChanged(newValue);
      } else if (newValue === "") {
        spanRef.current.textContent = initialValueRef.current;
      }
    }
    setShowMruPopover(false);
    setSelectedMruIndex(-1);
    setIsEditing(false);
  }, [onValueChanged]);
  const selectMruItem = reactExports.useCallback(
    (item) => {
      if (spanRef.current && item) {
        spanRef.current.textContent = item;
        setCurrentText(item);
        setShowMruPopover(false);
        setSelectedMruIndex(-1);
        setIsEditing(false);
        spanRef.current.blur();
        if (item !== initialValueRef.current) {
          onValueChanged(item);
        }
      }
    },
    [onValueChanged]
  );
  const handleBlur = () => {
    setTimeout(() => {
      setIsFocused(false);
      commitChanges();
    }, 150);
  };
  const handleKeyDown = (e) => {
    if (showMruPopover && filteredMru.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedMruIndex(
          (prev) => prev < filteredMru.length - 1 ? prev + 1 : prev
        );
        return;
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedMruIndex((prev) => prev > 0 ? prev - 1 : -1);
        return;
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (selectedMruIndex >= 0 && selectedMruIndex < filteredMru.length) {
          selectMruItem(filteredMru[selectedMruIndex]);
        } else {
          spanRef.current?.blur();
        }
        return;
      } else if (e.key === "Escape") {
        e.preventDefault();
        setShowMruPopover(false);
        setSelectedMruIndex(-1);
        if (spanRef.current) {
          spanRef.current.textContent = initialValueRef.current;
          setCurrentText(initialValueRef.current);
        }
        spanRef.current?.blur();
        return;
      }
    } else {
      if (e.key === "Enter") {
        e.preventDefault();
        spanRef.current?.blur();
      } else if (e.key === "Escape") {
        e.preventDefault();
        if (spanRef.current) {
          spanRef.current.textContent = initialValueRef.current;
          setCurrentText(initialValueRef.current);
        }
        spanRef.current?.blur();
      }
    }
  };
  const handleInput = () => {
    if (spanRef.current) {
      const text2 = spanRef.current.textContent || "";
      setCurrentText(text2);
      setSelectedMruIndex(-1);
      setIsEditing(true);
    }
    if (spanRef.current && spanRef.current.textContent === "") {
      spanRef.current.textContent = "";
    }
  };
  const displayValue = value || placeholder2 || "";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { ref: containerRef, className: clsx(styles$2.container, className), children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$2.labelContainer), title, children: [
        icon2 && /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: `${icon2} ${styles$2.icon}` }),
        label && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$2.label, children: label })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "span",
        {
          ref: spanRef,
          contentEditable: editable,
          className: clsx(
            styles$2.text,
            !value ? styles$2.placeholder : "",
            !editable ? styles$2.readOnly : ""
          ),
          onFocus: handleFocus,
          onBlur: handleBlur,
          onKeyDown: handleKeyDown,
          onInput: handleInput,
          suppressContentEditableWarning: true,
          children: displayValue
        }
      ),
      secondaryValue && /* @__PURE__ */ jsxRuntimeExports.jsx(
        "span",
        {
          className: clsx(
            styles$2.text,
            styles$2.placeholder,
            styles$2.secondary,
            !editable ? styles$2.readOnly : ""
          ),
          children: secondaryValue
        }
      )
    ] }),
    mru && mru.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(
      PopOver,
      {
        id: "editable-text-mru-popover",
        isOpen: showMruPopover,
        setIsOpen: setShowMruPopover,
        positionEl: spanRef.current,
        placement: "bottom-start",
        hoverDelay: 0,
        showArrow: false,
        offset: [0, 4],
        className: clsx(styles$2.mruPopover, "text-size-smallest"),
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.mruList, children: filteredMru.map((item, index) => /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              styles$2.mruItem,
              index === selectedMruIndex && styles$2.mruItemSelected
            ),
            onClick: () => selectMruItem(item),
            onMouseEnter: () => setSelectedMruIndex(index),
            children: item
          },
          index
        )) })
      }
    )
  ] });
};
const EditablePath = ({
  path,
  secondaryText,
  onPathChanged,
  mru,
  label,
  title,
  icon: icon2,
  placeholder: placeholder2,
  editable = true,
  className
}) => {
  const displayPath = prettyDirUri(path || "");
  const onValueChanged = (newDisplayPath) => {
    if (isUri(newDisplayPath)) {
      onPathChanged(newDisplayPath);
    } else {
      const newUri = `file://${newDisplayPath}`;
      onPathChanged(newUri);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EditableText,
    {
      value: displayPath,
      secondaryValue: secondaryText,
      onValueChanged,
      mru,
      label,
      title,
      icon: icon2,
      placeholder: placeholder2,
      className,
      editable
    }
  );
};
const header = "_header_1q9f5_1";
const bordered = "_bordered_1q9f5_10";
const left = "_left_1q9f5_14";
const leftButtons = "_leftButtons_1q9f5_20";
const rightButtons = "_rightButtons_1q9f5_29";
const hasChildren = "_hasChildren_1q9f5_38";
const styles$1 = {
  header,
  bordered,
  left,
  leftButtons,
  rightButtons,
  hasChildren
};
const toolbarButton = "_toolbarButton_1ldhr_1";
const disabled = "_disabled_1ldhr_9";
const styles = {
  toolbarButton,
  disabled
};
const NavButtons = ({ buttons }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: buttons.map(
    (button, index) => button.enabled !== false ? /* @__PURE__ */ jsxRuntimeExports.jsx(
      Link,
      {
        to: button.route,
        className: clsx(styles.toolbarButton),
        title: button.title,
        "aria-label": button.title,
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(button.icon) })
      },
      index
    ) : /* @__PURE__ */ jsxRuntimeExports.jsx(
      "span",
      {
        className: clsx(styles.toolbarButton, styles.disabled),
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(button.icon) })
      },
      index
    )
  ) });
};
const Navbar = ({
  bordered: bordered2 = true,
  left: left2,
  right,
  leftButtons: leftButtons2,
  rightButtons: rightButtons2
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "nav",
    {
      className: clsx(
        "text-size-smaller",
        "header-nav",
        styles$1.header,
        bordered2 ? styles$1.bordered : void 0
      ),
      "aria-label": "breadcrumb",
      "data-unsearchable": true,
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(leftButtons2 ? styles$1.leftButtons : void 0), children: leftButtons2 && /* @__PURE__ */ jsxRuntimeExports.jsx(NavButtons, { buttons: leftButtons2 }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(leftButtons2 ? styles$1.left : void 0), children: left2 }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(styles$1.right, right ? styles$1.hasChildren : void 0),
            children: right
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(rightButtons2 ? styles$1.rightButtons : void 0), children: rightButtons2 && /* @__PURE__ */ jsxRuntimeExports.jsx(NavButtons, { buttons: rightButtons2 }) })
      ]
    }
  );
};
export {
  EditablePath as E,
  Navbar as N,
  join as j,
  prettyDirUri as p
};
//# sourceMappingURL=Navbar.js.map
