import { j as jsxRuntimeExports, r as reactExports, c as clsx, A as ApplicationIcons, i as useSearchParams, u as useStore, I as getValidationSetParam, f as ErrorPanel, L as LoadingBar, e as useAppConfig, J as useQueryClient, K as updateValidationSetParam, z as getValidationParam, B as updateValidationParam, s as skipToken } from "./index.js";
import { a as VscodeButton, b as VscodeRadioGroup, c as VscodeRadio, d as VscodeSingleSelect, e as VscodeOption, f as VscodeTextfield, g as VscodeDivider } from "./VscodeTreeItem.js";
import { M as Modal } from "./Modal.js";
import { F as Field } from "./FormFields.js";
import { u as useDropdownPosition, s as styles$7, a as useValidationSets, b as useValidationCase, c as useValidationCases, d as useCreateValidationSet, e as useDeleteValidationCase, f as useUpdateValidationCase, v as validationQueryKeys, i as isValidFilename, h as hasValidationSetExtension, V as ValidationSetSelector, g as extractUniqueLabels, j as ValidationSplitSelector, k as extractUniqueSplits } from "./ValidationSplitSelector.js";
import { C as Chip, A as AutocompleteInput } from "./Chip.js";
import { P as PopOver } from "./ToolButton.js";
import { r as resolveMessages, g as ChatMessageRow, L as LiveVirtualList, h as buildTimeline, j as useTimeline, k as rowHasEvents, l as computeRowLayouts, m as getSelectedSpans, n as collectRawEvents, o as computeMinimapSelection, p as buildSpanSelectKeys, u as useEventNodes, q as kTranscriptCollapseScope, s as useProperty, t as TimelineSelectContext, T as TranscriptViewNodes, v as kCollapsibleEventTypes } from "./TranscriptViewNodes.js";
import { N as NoContentsPanel } from "./NoContentsPanel.js";
import { c as computeTimeMapping, T as TimelineSwimLanes, a as TranscriptOutline } from "./TimelineSwimLanes.js";
function formatTaskName(parts) {
  const { taskSet, taskId, taskRepeat } = parts;
  if (!taskSet && !taskId && taskRepeat === void 0) {
    return void 0;
  }
  const nameParts = [];
  if (taskSet) {
    nameParts.push(taskSet);
  }
  if (taskId !== void 0 && taskId !== null) {
    if (nameParts.length > 0) {
      nameParts.push("/");
    }
    nameParts.push(String(taskId));
  }
  if (taskRepeat !== void 0 && taskRepeat !== null) {
    nameParts.push(` (${taskRepeat})`);
  }
  return nameParts.length > 0 ? nameParts.join("") : void 0;
}
function getTranscriptDisplayName(transcript) {
  if (!transcript) return void 0;
  const formattedName = formatTaskName({
    taskSet: transcript.task_set,
    taskId: transcript.task_id,
    taskRepeat: transcript.task_repeat
  });
  return formattedName ?? transcript.task_id ?? void 0;
}
const content$1 = "_content_10rzs_1";
const warning = "_warning_10rzs_11";
const styles$6 = {
  content: content$1,
  warning
};
const ConfirmationDialog = ({
  show,
  onHide,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  confirmingLabel = "Confirming...",
  isConfirming = false,
  warning: warning2
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    Modal,
    {
      show,
      onHide,
      onSubmit: isConfirming ? void 0 : onConfirm,
      title,
      footer: /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { secondary: true, onClick: onHide, children: cancelLabel }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { onClick: onConfirm, disabled: isConfirming, children: isConfirming ? confirmingLabel : confirmLabel })
      ] }),
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$6.content, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: message }),
        warning2 && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: styles$6.warning, children: warning2 })
      ] })
    }
  );
};
const wrapper = "_wrapper_poq0z_1";
const iconButton = "_iconButton_poq0z_6";
const backdrop = "_backdrop_poq0z_33";
const menu = "_menu_poq0z_42";
const menuItem = "_menuItem_poq0z_60";
const styles$5 = {
  wrapper,
  iconButton,
  backdrop,
  menu,
  menuItem
};
const MenuActionButton = ({
  items,
  onSelect,
  disabled: disabled2,
  title
}) => {
  const [showMenu, setShowMenu] = reactExports.useState(false);
  const handleSelect = (value) => {
    setShowMenu(false);
    onSelect(value);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$5.wrapper, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        className: styles$5.iconButton,
        onClick: () => setShowMenu((prev) => !prev),
        title,
        disabled: disabled2,
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: "bi-three-dots" })
      }
    ),
    showMenu && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$5.backdrop, onClick: () => setShowMenu(false) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$5.menu, children: items.map((item2) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          className: styles$5.menuItem,
          onClick: () => handleSelect(item2.value),
          disabled: item2.disabled,
          children: [
            item2.icon && /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: item2.icon }),
            item2.label
          ]
        },
        item2.value
      )) })
    ] })
  ] });
};
const container$1 = "_container_oam2j_1";
const header = "_header_oam2j_7";
const headerTitle = "_headerTitle_oam2j_18";
const headerIcon = "_headerIcon_oam2j_26";
const headerSecondary = "_headerSecondary_oam2j_30";
const content = "_content_oam2j_35";
const panel = "_panel_oam2j_52";
const clickable = "_clickable_oam2j_69";
const idLabel = "_idLabel_oam2j_73";
const saveStatusContainer = "_saveStatusContainer_oam2j_77";
const saveStatusHidden = "_saveStatusHidden_oam2j_90";
const saveStatusError = "_saveStatusError_oam2j_94";
const saveStatus = "_saveStatus_oam2j_77";
const createError = "_createError_oam2j_107";
const infoBox = "_infoBox_oam2j_142";
const idField = "_idField_oam2j_148";
const idValue = "_idValue_oam2j_153";
const styles$4 = {
  container: container$1,
  header,
  headerTitle,
  headerIcon,
  headerSecondary,
  content,
  panel,
  clickable,
  idLabel,
  saveStatusContainer,
  saveStatusHidden,
  saveStatusError,
  saveStatus,
  createError,
  infoBox,
  idField,
  idValue
};
const inputContainer = "_inputContainer_1nqcj_1";
const labelChip = "_labelChip_1nqcj_14";
const popoverContent = "_popoverContent_1nqcj_18";
const popoverField = "_popoverField_1nqcj_25";
const popoverLabel = "_popoverLabel_1nqcj_31";
const popoverActions = "_popoverActions_1nqcj_35";
const styles$3 = {
  inputContainer,
  labelChip,
  popoverContent,
  popoverField,
  popoverLabel,
  popoverActions
};
const ValidationCaseLabelsEditor = ({ labels, availableLabels, onChange }) => {
  const [isPopoverOpen, setIsPopoverOpen] = reactExports.useState(false);
  const [newLabelName, setNewLabelName] = reactExports.useState("");
  const [newLabelValue, setNewLabelValue] = reactExports.useState("true");
  const addChipRef = reactExports.useRef(null);
  const labelEntries = labels ? Object.entries(labels) : [];
  const handleToggleLabel = reactExports.useCallback(
    (labelKey) => {
      if (!labels) return;
      onChange({ ...labels, [labelKey]: !labels[labelKey] });
    },
    [labels, onChange]
  );
  const handleRemoveLabel = reactExports.useCallback(
    (labelKey) => {
      if (!labels) return;
      const updated = { ...labels };
      delete updated[labelKey];
      onChange(Object.keys(updated).length === 0 ? null : updated);
    },
    [labels, onChange]
  );
  const handleAddLabel = reactExports.useCallback(() => {
    const trimmed = newLabelName.trim();
    if (!trimmed) return;
    const updated = { ...labels ?? {}, [trimmed]: newLabelValue === "true" };
    onChange(updated);
    setNewLabelName("");
    setNewLabelValue("true");
    setIsPopoverOpen(false);
  }, [newLabelName, newLabelValue, labels, onChange]);
  const handleCancel = reactExports.useCallback(() => {
    setNewLabelName("");
    setNewLabelValue("true");
    setIsPopoverOpen(false);
  }, []);
  const handleOpenPopover = reactExports.useCallback(() => {
    setNewLabelName("");
    setNewLabelValue("true");
    setIsPopoverOpen(true);
  }, []);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.inputContainer, children: [
      labelEntries.map(([key, value]) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        Chip,
        {
          label: key,
          value: value ? "true" : "false",
          title: `Click to toggle "${key}" to ${value ? "false" : "true"}`,
          closeTitle: `Remove label "${key}"`,
          className: clsx(styles$3.labelChip, "text-size-smallest"),
          onClick: () => handleToggleLabel(key),
          onClose: () => handleRemoveLabel(key)
        },
        key
      )),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        Chip,
        {
          ref: addChipRef,
          icon: ApplicationIcons.add,
          value: "Add",
          title: "Add a new label",
          className: clsx(styles$3.labelChip, "text-size-smallest"),
          onClick: handleOpenPopover
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      PopOver,
      {
        id: "validation-labels-add",
        isOpen: isPopoverOpen,
        setIsOpen: setIsPopoverOpen,
        positionEl: addChipRef.current,
        placement: "bottom-start",
        showArrow: true,
        hoverDelay: -1,
        closeOnMouseLeave: false,
        styles: {
          padding: "0.4rem",
          backgroundColor: "var(--bs-light)"
        },
        children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.popoverContent, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.popoverField, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "label",
              {
                htmlFor: "validation-label-name",
                className: clsx("text-size-smallest", styles$3.popoverLabel),
                children: "Label"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              AutocompleteInput,
              {
                id: "validation-label-name",
                value: newLabelName,
                onChange: setNewLabelName,
                onCommit: handleAddLabel,
                onCancel: handleCancel,
                suggestions: availableLabels,
                placeholder: "Label name",
                autoFocus: true,
                allowBrowse: availableLabels.length > 0
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.popoverField, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: clsx("text-size-smallest", styles$3.popoverLabel), children: "Value" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              VscodeRadioGroup,
              {
                onChange: (e) => setNewLabelValue(e.target.value),
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    VscodeRadio,
                    {
                      name: "label-value",
                      label: "True",
                      value: "true",
                      checked: newLabelValue === "true"
                    }
                  ),
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    VscodeRadio,
                    {
                      name: "label-value",
                      label: "False",
                      value: "false",
                      checked: newLabelValue === "false"
                    }
                  )
                ]
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.popoverActions, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { secondary: true, onClick: handleCancel, children: "Cancel" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              VscodeButton,
              {
                onClick: handleAddLabel,
                disabled: !newLabelName.trim(),
                children: "Add"
              }
            )
          ] })
        ] })
      }
    )
  ] });
};
const PREDICATES = [
  { value: "eq", label: "Equal (eq)" },
  { value: "ne", label: "Not equal (ne)" },
  { value: "gt", label: "Greater than (gt)" },
  { value: "gte", label: "Greater or equal (gte)" },
  { value: "lt", label: "Less than (lt)" },
  { value: "lte", label: "Less or equal (lte)" },
  { value: "contains", label: "Contains" },
  { value: "startswith", label: "Starts with" },
  { value: "endswith", label: "Ends with" },
  { value: "icontains", label: "Contains (case-insensitive)" },
  { value: "iequals", label: "Equal (case-insensitive)" }
];
const ValidationCasePredicateSelector = ({ value, onChange, disabled: disabled2 = false, existingPredicates }) => {
  const { ref, position } = useDropdownPosition({
    optionCount: PREDICATES.length
  });
  const defaultValue = existingPredicates && existingPredicates.length === 1 ? existingPredicates[0] : "eq";
  const handleChange = (e) => {
    const newValue = e.target.value;
    onChange(newValue);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref, className: styles$7.container, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
    VscodeSingleSelect,
    {
      position,
      value: value ?? defaultValue,
      onChange: handleChange,
      className: styles$7.select,
      disabled: disabled2,
      children: PREDICATES.map((predicate) => /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: predicate.value, children: predicate.label }, predicate.value))
    }
  ) });
};
const extractUniquePredicates = (cases) => {
  const predicateSet = /* @__PURE__ */ new Set();
  const predicates = PREDICATES.map((p) => p.value);
  for (const c of cases) {
    if (c.predicate && predicates.includes(c.predicate)) {
      predicateSet.add(c.predicate);
    }
  }
  return Array.from(predicateSet).sort();
};
var freeGlobal = typeof global == "object" && global && global.Object === Object && global;
var freeSelf = typeof self == "object" && self && self.Object === Object && self;
var root$1 = freeGlobal || freeSelf || Function("return this")();
var Symbol$1 = root$1.Symbol;
var objectProto$1 = Object.prototype;
var hasOwnProperty = objectProto$1.hasOwnProperty;
var nativeObjectToString$1 = objectProto$1.toString;
var symToStringTag$1 = Symbol$1 ? Symbol$1.toStringTag : void 0;
function getRawTag(value) {
  var isOwn = hasOwnProperty.call(value, symToStringTag$1), tag = value[symToStringTag$1];
  try {
    value[symToStringTag$1] = void 0;
    var unmasked = true;
  } catch (e) {
  }
  var result = nativeObjectToString$1.call(value);
  if (unmasked) {
    if (isOwn) {
      value[symToStringTag$1] = tag;
    } else {
      delete value[symToStringTag$1];
    }
  }
  return result;
}
var objectProto = Object.prototype;
var nativeObjectToString = objectProto.toString;
function objectToString(value) {
  return nativeObjectToString.call(value);
}
var nullTag = "[object Null]", undefinedTag = "[object Undefined]";
var symToStringTag = Symbol$1 ? Symbol$1.toStringTag : void 0;
function baseGetTag(value) {
  if (value == null) {
    return value === void 0 ? undefinedTag : nullTag;
  }
  return symToStringTag && symToStringTag in Object(value) ? getRawTag(value) : objectToString(value);
}
function isObjectLike(value) {
  return value != null && typeof value == "object";
}
var symbolTag = "[object Symbol]";
function isSymbol(value) {
  return typeof value == "symbol" || isObjectLike(value) && baseGetTag(value) == symbolTag;
}
var reWhitespace = /\s/;
function trimmedEndIndex(string) {
  var index = string.length;
  while (index-- && reWhitespace.test(string.charAt(index))) {
  }
  return index;
}
var reTrimStart = /^\s+/;
function baseTrim(string) {
  return string ? string.slice(0, trimmedEndIndex(string) + 1).replace(reTrimStart, "") : string;
}
function isObject(value) {
  var type = typeof value;
  return value != null && (type == "object" || type == "function");
}
var NAN = 0 / 0;
var reIsBadHex = /^[-+]0x[0-9a-f]+$/i;
var reIsBinary = /^0b[01]+$/i;
var reIsOctal = /^0o[0-7]+$/i;
var freeParseInt = parseInt;
function toNumber(value) {
  if (typeof value == "number") {
    return value;
  }
  if (isSymbol(value)) {
    return NAN;
  }
  if (isObject(value)) {
    var other = typeof value.valueOf == "function" ? value.valueOf() : value;
    value = isObject(other) ? other + "" : other;
  }
  if (typeof value != "string") {
    return value === 0 ? value : +value;
  }
  value = baseTrim(value);
  var isBinary = reIsBinary.test(value);
  return isBinary || reIsOctal.test(value) ? freeParseInt(value.slice(2), isBinary ? 2 : 8) : reIsBadHex.test(value) ? NAN : +value;
}
var now = function() {
  return root$1.Date.now();
};
var FUNC_ERROR_TEXT = "Expected a function";
var nativeMax = Math.max, nativeMin = Math.min;
function debounce(func, wait, options) {
  var lastArgs, lastThis, maxWait, result, timerId, lastCallTime, lastInvokeTime = 0, leading = false, maxing = false, trailing = true;
  if (typeof func != "function") {
    throw new TypeError(FUNC_ERROR_TEXT);
  }
  wait = toNumber(wait) || 0;
  if (isObject(options)) {
    leading = !!options.leading;
    maxing = "maxWait" in options;
    maxWait = maxing ? nativeMax(toNumber(options.maxWait) || 0, wait) : maxWait;
    trailing = "trailing" in options ? !!options.trailing : trailing;
  }
  function invokeFunc(time) {
    var args = lastArgs, thisArg = lastThis;
    lastArgs = lastThis = void 0;
    lastInvokeTime = time;
    result = func.apply(thisArg, args);
    return result;
  }
  function leadingEdge(time) {
    lastInvokeTime = time;
    timerId = setTimeout(timerExpired, wait);
    return leading ? invokeFunc(time) : result;
  }
  function remainingWait(time) {
    var timeSinceLastCall = time - lastCallTime, timeSinceLastInvoke = time - lastInvokeTime, timeWaiting = wait - timeSinceLastCall;
    return maxing ? nativeMin(timeWaiting, maxWait - timeSinceLastInvoke) : timeWaiting;
  }
  function shouldInvoke(time) {
    var timeSinceLastCall = time - lastCallTime, timeSinceLastInvoke = time - lastInvokeTime;
    return lastCallTime === void 0 || timeSinceLastCall >= wait || timeSinceLastCall < 0 || maxing && timeSinceLastInvoke >= maxWait;
  }
  function timerExpired() {
    var time = now();
    if (shouldInvoke(time)) {
      return trailingEdge(time);
    }
    timerId = setTimeout(timerExpired, remainingWait(time));
  }
  function trailingEdge(time) {
    timerId = void 0;
    if (trailing && lastArgs) {
      return invokeFunc(time);
    }
    lastArgs = lastThis = void 0;
    return result;
  }
  function cancel() {
    if (timerId !== void 0) {
      clearTimeout(timerId);
    }
    lastInvokeTime = 0;
    lastArgs = lastCallTime = lastThis = timerId = void 0;
  }
  function flush() {
    return timerId === void 0 ? result : trailingEdge(now());
  }
  function debounced() {
    var time = now(), isInvoking = shouldInvoke(time);
    lastArgs = arguments;
    lastThis = this;
    lastCallTime = time;
    if (isInvoking) {
      if (timerId === void 0) {
        return leadingEdge(lastCallTime);
      }
      if (maxing) {
        clearTimeout(timerId);
        timerId = setTimeout(timerExpired, wait);
        return invokeFunc(lastCallTime);
      }
    }
    if (timerId === void 0) {
      timerId = setTimeout(timerExpired, wait);
    }
    return result;
  }
  debounced.cancel = cancel;
  debounced.flush = flush;
  return debounced;
}
function useDebouncedCallback(callback, delay) {
  const callbackRef = reactExports.useRef(callback);
  reactExports.useLayoutEffect(() => {
    callbackRef.current = callback;
  });
  const debouncedFn = reactExports.useMemo(
    () => debounce((...args) => {
      callbackRef.current(...args);
    }, delay),
    [delay]
  );
  reactExports.useEffect(() => {
    return () => {
      debouncedFn.cancel();
    };
  }, [debouncedFn]);
  return debouncedFn;
}
function getTargetMode(target) {
  if (target === void 0 || target === null) {
    return "unset";
  }
  if (target === "true" || target === true) {
    return "true";
  }
  if (target === "false" || target === false) {
    return "false";
  }
  return "other";
}
const ValidationCaseTargetEditor = ({ target, onChange, onModeChange }) => {
  const [mode, setMode] = reactExports.useState(() => getTargetMode(target));
  reactExports.useEffect(() => {
    onModeChange?.(mode === "other");
  }, [mode, onModeChange]);
  const [customValue, setCustomValue] = reactExports.useState(
    () => getTargetMode(target) === "other" ? String(target ?? "") : ""
  );
  const [isTyping, setIsTyping] = reactExports.useState(false);
  reactExports.useEffect(() => {
    if (isTyping) return;
    if (target === void 0 || target === null) return;
    const newMode = getTargetMode(target);
    setMode(newMode);
    if (newMode === "other") {
      setCustomValue(String(target ?? ""));
    }
  }, [target, isTyping]);
  const debouncedOnChange = useDebouncedCallback((value) => {
    onChange(value);
    setIsTyping(false);
  }, 600);
  const handleRadioChange = (value) => {
    const newMode = value;
    setMode(newMode);
    if (newMode === "other") {
      onChange(customValue || "");
    } else {
      onChange(newMode);
    }
  };
  const handleCustomValueChange = (value) => {
    setIsTyping(true);
    setCustomValue(value);
    debouncedOnChange(value);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      VscodeRadioGroup,
      {
        onChange: (e) => handleRadioChange(e.target.value),
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeRadio,
            {
              name: "target-mode",
              label: "True",
              value: "true",
              checked: mode === "true"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeRadio,
            {
              name: "target-mode",
              label: "False",
              value: "false",
              checked: mode === "false"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeRadio,
            {
              name: "target-mode",
              label: "Other",
              value: "other",
              checked: mode === "other"
            }
          )
        ]
      }
    ),
    mode === "other" && /* @__PURE__ */ jsxRuntimeExports.jsx(
      VscodeTextfield,
      {
        value: customValue,
        placeholder: "Enter target value",
        onInput: (e) => handleCustomValueChange(e.target.value),
        style: { marginTop: "8px" }
      }
    )
  ] });
};
const ValidationCaseEditor = ({
  transcriptId,
  className
}) => {
  const [searchParams] = useSearchParams();
  const editorValidationSetUri = useStore(
    (state) => state.editorSelectedValidationSetUri
  );
  const setEditorSelectedValidationSetUri = useStore(
    (state) => state.setEditorSelectedValidationSetUri
  );
  const {
    data: setsData,
    loading: setsLoading,
    error: setsError
  } = useValidationSets();
  const {
    data: caseData,
    loading: caseLoading,
    error: caseError
  } = useValidationCase(
    !editorValidationSetUri ? skipToken : {
      url: editorValidationSetUri,
      caseId: transcriptId
    }
  );
  const {
    data: casesData,
    loading: casesLoading,
    error: casesError
  } = useValidationCases(
    editorValidationSetUri ? editorValidationSetUri : skipToken
  );
  reactExports.useEffect(() => {
    if (!setsData || setsData.length === 0) return;
    const validationSetParam = getValidationSetParam(searchParams);
    if (validationSetParam && setsData.includes(validationSetParam)) {
      if (editorValidationSetUri !== validationSetParam) {
        setEditorSelectedValidationSetUri(validationSetParam);
      }
    } else if (!editorValidationSetUri) {
      setEditorSelectedValidationSetUri(setsData[0]);
    }
  }, [
    setsData,
    searchParams,
    editorValidationSetUri,
    setEditorSelectedValidationSetUri
  ]);
  const error = setsError || casesError || caseError;
  const loading = setsLoading || casesLoading || !!editorValidationSetUri && caseLoading;
  const showPanel = !setsLoading;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    error && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ErrorPanel,
      {
        title: "Error Loading Validation Sets",
        error: { message: error.message }
      }
    ),
    !error && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoadingBar, { loading }),
      showPanel && setsData && /* @__PURE__ */ jsxRuntimeExports.jsx(
        ValidationCaseEditorComponent,
        {
          transcriptId,
          validationSets: setsData,
          editorValidationSetUri,
          validationCase: caseData,
          validationCases: casesData,
          className
        }
      )
    ] })
  ] });
};
const ValidationCaseEditorComponent = ({
  transcriptId,
  validationSets,
  editorValidationSetUri,
  validationCase: caseData,
  validationCases,
  className
}) => {
  const config = useAppConfig();
  const queryClient = useQueryClient();
  const setEditorSelectedValidationSetUri = useStore(
    (state) => state.setEditorSelectedValidationSetUri
  );
  const [, setSearchParams] = useSearchParams();
  const [saveStatus2, setSaveStatus] = reactExports.useState("idle");
  const [saveError, setSaveError] = reactExports.useState(null);
  const [createError2, setCreateError] = reactExports.useState(null);
  const createSetMutation = useCreateValidationSet();
  const [showDeleteModal, setShowDeleteModal] = reactExports.useState(false);
  const [isOtherModeSelected, setIsOtherModeSelected] = reactExports.useState(false);
  const [validationTypeOverride, setValidationTypeOverride] = reactExports.useState(null);
  const caseHasTarget = caseData?.target != null && caseData.target !== "";
  const caseHasLabels = caseData?.labels != null;
  const setUsesLabels = validationCases?.some((c) => c.labels != null) ?? false;
  const defaultValidationType = caseHasLabels ? "labels" : caseHasTarget ? "target" : setUsesLabels ? "labels" : "target";
  const validationType = validationTypeOverride ?? defaultValidationType;
  const deleteCaseMutation = useDeleteValidationCase(
    editorValidationSetUri ?? ""
  );
  const updateValidationCaseMutation = useUpdateValidationCase(
    editorValidationSetUri ?? ""
  );
  const handleFieldChange = reactExports.useCallback(
    (field, value) => {
      if (!editorValidationSetUri) return;
      const clearOpposite = field === "target" ? isOtherTarget(value) ? {
        labels: null,
        ...!caseData?.predicate && { predicate: "eq" }
      } : { labels: null, predicate: null } : field === "labels" ? { target: null, predicate: null } : {};
      const updatedCase = caseData ? { ...caseData, ...clearOpposite, [field]: value } : {
        id: transcriptId,
        labels: null,
        predicate: null,
        split: null,
        target: null,
        [field]: value
      };
      const hasEmptyTarget = updatedCase.target == null || updatedCase.target === "";
      const hadPreviousTarget = caseData?.target != null && caseData.target !== "";
      const isNewEmptyCase = hasEmptyTarget && updatedCase.labels == null && !hadPreviousTarget;
      if (isNewEmptyCase) {
        queryClient.setQueryData(
          validationQueryKeys.case({
            url: editorValidationSetUri,
            caseId: transcriptId
          }),
          updatedCase
        );
        return;
      }
      const request = {
        id: updatedCase.id,
        target: updatedCase.target,
        labels: updatedCase.labels,
        predicate: updatedCase.predicate,
        split: updatedCase.split
      };
      setSaveStatus("saving");
      setSaveError(null);
      updateValidationCaseMutation.mutate(
        { caseId: transcriptId, data: request },
        {
          onSuccess: () => {
            setSaveStatus("saved");
            setTimeout(() => setSaveStatus("idle"), 1500);
          },
          onError: (error) => {
            setSaveStatus("error");
            setSaveError(error.message);
          }
        }
      );
    },
    [
      editorValidationSetUri,
      transcriptId,
      caseData,
      queryClient,
      updateValidationCaseMutation
    ]
  );
  const handleValidationTypeChange = reactExports.useCallback(
    (newType) => {
      if (newType !== "target" && newType !== "labels") return;
      if (newType === validationType) return;
      setValidationTypeOverride(newType);
    },
    [validationType]
  );
  const handleValidationSetSelect = reactExports.useCallback(
    (uri) => {
      setEditorSelectedValidationSetUri(uri);
      setSearchParams(
        (prevParams) => updateValidationSetParam(prevParams, uri),
        { replace: true }
      );
    },
    [setEditorSelectedValidationSetUri, setSearchParams]
  );
  const closeValidationSidebar = reactExports.useCallback(() => {
    setSearchParams((prevParams) => {
      const isCurrentlyOpen = getValidationParam(prevParams);
      return updateValidationParam(prevParams, !isCurrentlyOpen);
    });
  }, [setSearchParams]);
  const handleCreateSet = reactExports.useCallback(
    async (name) => {
      setCreateError(null);
      const validation = isValidFilename(name);
      if (!validation.isValid) {
        setCreateError(validation.error ?? "Invalid filename");
        return;
      }
      const filename = hasValidationSetExtension(name) ? name : `${name}.csv`;
      const newUri = `${config.project_dir}/${filename}`;
      if (validationSets?.includes(newUri)) {
        setCreateError("A validation set with this name already exists");
        return;
      }
      try {
        await createSetMutation.mutateAsync({ path: newUri, cases: [] });
        setCreateError(null);
        handleValidationSetSelect(newUri);
      } catch (err) {
        setCreateError(
          err instanceof Error ? err.message : "Failed to create set"
        );
      }
    },
    [
      config.project_dir,
      validationSets,
      createSetMutation,
      handleValidationSetSelect
    ]
  );
  const handleDeleteCase = reactExports.useCallback(async () => {
    if (!transcriptId || !editorValidationSetUri) return;
    try {
      await deleteCaseMutation.mutateAsync(transcriptId);
      setShowDeleteModal(false);
      queryClient.setQueryData(
        validationQueryKeys.case({
          url: editorValidationSetUri,
          caseId: transcriptId
        }),
        null
      );
    } catch {
    }
  }, [transcriptId, editorValidationSetUri, deleteCaseMutation, queryClient]);
  const isEditable = caseData?.target === void 0 || caseData?.target === null || !Array.isArray(caseData.target) && typeof caseData.target !== "object";
  const hasCaseData = caseData?.target != null && caseData.target !== "" || caseData?.labels != null;
  const actions = hasCaseData ? /* @__PURE__ */ jsxRuntimeExports.jsx(
    MenuActionButton,
    {
      items: [
        {
          icon: ApplicationIcons.trash,
          label: "Delete validation case",
          value: "delete",
          disabled: deleteCaseMutation.isPending
        }
      ],
      onSelect: (value) => {
        if (value === "delete") setShowDeleteModal(true);
      },
      title: "More actions"
    }
  ) : void 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$4.container, className), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      SidebarHeader,
      {
        title: "Validation Case",
        icon: ApplicationIcons.validation,
        actions,
        onClose: closeValidationSidebar
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$4.content, children: /* @__PURE__ */ jsxRuntimeExports.jsxs(SidebarPanel, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(SecondaryDisplayValue, { label: "ID", value: transcriptId }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(Field, { label: "Validation Set", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ValidationSetSelector,
          {
            validationSets: validationSets || [],
            selectedUri: editorValidationSetUri,
            onSelect: handleValidationSetSelect,
            allowCreate: true,
            onCreate: (name) => void handleCreateSet(name),
            appConfig: config
          }
        ),
        createError2 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$4.createError, children: createError2 })
      ] }),
      !isEditable && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeDivider, {}),
        /* @__PURE__ */ jsxRuntimeExports.jsx(InfoBox, { children: "Validation sets with dictionary or list targets aren't editable using this UI." })
      ] }),
      editorValidationSetUri && isEditable && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          Field,
          {
            label: "Type",
            helper: "Choose single-value validation or label-based validation.",
            children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
              VscodeRadioGroup,
              {
                onChange: (e) => handleValidationTypeChange(
                  e.target.value
                ),
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    VscodeRadio,
                    {
                      name: "validation-type",
                      label: "Values",
                      value: "target",
                      checked: validationType === "target"
                    }
                  ),
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    VscodeRadio,
                    {
                      name: "validation-type",
                      label: "Labels",
                      value: "labels",
                      checked: validationType === "labels"
                    }
                  )
                ]
              }
            )
          }
        ),
        validationType === "target" && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            Field,
            {
              label: "Target",
              helper: "The expected value for this case.",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                ValidationCaseTargetEditor,
                {
                  target: caseData?.target,
                  onChange: (target) => handleFieldChange("target", target),
                  onModeChange: setIsOtherModeSelected
                }
              )
            }
          ),
          isOtherModeSelected && /* @__PURE__ */ jsxRuntimeExports.jsx(
            Field,
            {
              label: "Predicate",
              helper: "Specifies the comparison logic for individual cases (by default, comparison is for equality).",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                ValidationCasePredicateSelector,
                {
                  value: caseData?.predicate || null,
                  onChange: (predicate) => handleFieldChange("predicate", predicate),
                  existingPredicates: extractUniquePredicates(
                    validationCases || []
                  )
                }
              )
            }
          )
        ] }),
        validationType === "labels" && /* @__PURE__ */ jsxRuntimeExports.jsx(
          Field,
          {
            label: "Labels",
            helper: "Labels that must be present or absent.",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              ValidationCaseLabelsEditor,
              {
                labels: caseData?.labels ?? null,
                availableLabels: extractUniqueLabels(validationCases || []),
                onChange: (labels) => handleFieldChange("labels", labels)
              }
            )
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          Field,
          {
            label: "Split",
            helper: 'Split for this case (e.g., "dev", "test").',
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              ValidationSplitSelector,
              {
                value: caseData?.split || null,
                existingSplits: extractUniqueSplits(validationCases || []),
                onChange: (split) => handleFieldChange("split", split)
              }
            )
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ConfirmationDialog,
          {
            show: showDeleteModal,
            onHide: () => setShowDeleteModal(false),
            onConfirm: () => void handleDeleteCase(),
            title: "Delete Case",
            message: "Are you sure you want to delete this validation case?",
            confirmLabel: "Delete",
            confirmingLabel: "Deleting...",
            isConfirming: deleteCaseMutation.isPending
          }
        )
      ] })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(SaveStatus, { status: saveStatus2, error: saveError })
  ] });
};
const SidebarPanel = ({ children }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$4.panel, children });
};
const SidebarHeader = ({
  icon,
  title,
  secondary,
  actions,
  onClose
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$4.header, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("h3", { className: styles$4.headerTitle, children: [
      icon && /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(icon, styles$4.headerIcon) }),
      title
    ] }),
    secondary && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$4.headerSecondary, children: secondary }),
    (actions || onClose) && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$4.headerActions, children: [
      actions,
      onClose && /* @__PURE__ */ jsxRuntimeExports.jsx(
        "i",
        {
          className: clsx(ApplicationIcons.close, styles$4.clickable),
          onClick: onClose
        }
      )
    ] })
  ] });
};
const SecondaryDisplayValue = ({
  label,
  value
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: clsx(
        styles$4.idField,
        "text-size-smaller",
        "text-style-secondary"
      ),
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$4.idLabel, children: [
          label,
          ":"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$4.idValue, children: value })
      ]
    }
  );
};
const InfoBox = ({ children }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx("text-size-smaller", styles$4.infoBox), children: [
  /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(ApplicationIcons.info, styles$4.infoIcon) }),
  /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children })
] });
const SaveStatus = ({ status, error }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: clsx(
        styles$4.saveStatusContainer,
        status === "error" && styles$4.saveStatusError,
        status === "idle" && styles$4.saveStatusHidden
      ),
      children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$4.saveStatus, children: status === "saving" ? "Saving..." : status === "saved" ? "Saved" : status === "error" ? error || "Error saving changes" : "" })
    }
  );
};
const isOtherTarget = (target) => {
  if (target === null || target === void 0) {
    return false;
  }
  if (target === "") {
    return true;
  }
  if (typeof target === "boolean") {
    return false;
  }
  if (typeof target === "string") {
    const lower = target.toLowerCase();
    return lower !== "true" && lower !== "false";
  }
  return true;
};
const item = "_item_5fj0m_6";
const styles$2 = {
  item
};
const messageSearchText = (resolved) => {
  const texts = [];
  texts.push(...extractContentText(resolved.message.content));
  if (resolved.message.role === "assistant" && "tool_calls" in resolved.message && resolved.message.tool_calls) {
    for (const toolCall of resolved.message.tool_calls) {
      if (toolCall.function) {
        texts.push(toolCall.function);
      }
      if (toolCall.arguments) {
        texts.push(JSON.stringify(toolCall.arguments));
      }
    }
  }
  for (const toolMsg of resolved.toolMessages) {
    if (toolMsg.function) {
      texts.push(toolMsg.function);
    }
    texts.push(...extractContentText(toolMsg.content));
    if (toolMsg.error?.message) {
      texts.push(toolMsg.error.message);
    }
  }
  return texts;
};
const extractContentText = (content2) => {
  if (typeof content2 === "string") {
    return [content2];
  }
  const texts = [];
  for (const item2 of content2) {
    switch (item2.type) {
      case "text":
        texts.push(item2.text);
        break;
      case "reasoning": {
        const reasoning = item2;
        if (reasoning.reasoning) {
          texts.push(reasoning.reasoning);
        } else if (reasoning.summary) {
          texts.push(reasoning.summary);
        }
        break;
      }
      case "tool_use": {
        const toolUse = item2;
        if (toolUse.name) {
          texts.push(toolUse.name);
        }
        if (toolUse.arguments) {
          texts.push(JSON.stringify(toolUse.arguments));
        }
        break;
      }
    }
  }
  return texts;
};
const ChatViewVirtualList = reactExports.memo(
  ({
    id,
    messages,
    initialMessageId,
    topOffset,
    className,
    toolCallStyle,
    indented,
    scrollRef,
    running,
    allowLinking = true,
    labels,
    showLabels = true,
    highlightLabeled = false
  }) => {
    const listHandle = reactExports.useRef(null);
    reactExports.useEffect(() => {
      const handleKeyDown = (event) => {
        if (event.metaKey || event.ctrlKey) {
          if (event.key === "ArrowUp") {
            listHandle.current?.scrollToIndex({ index: 0, align: "center" });
            event.preventDefault();
          } else if (event.key === "ArrowDown") {
            listHandle.current?.scrollToIndex({
              index: Math.min(messages.length - 5, 0),
              align: "center"
            });
            setTimeout(() => {
              listHandle.current?.scrollToIndex({
                index: messages.length - 1,
                align: "end"
              });
            }, 250);
            event.preventDefault();
          }
        }
      };
      const scrollElement = scrollRef?.current;
      if (scrollElement) {
        scrollElement.addEventListener("keydown", handleKeyDown);
        if (!scrollElement.hasAttribute("tabIndex")) {
          scrollElement.setAttribute("tabIndex", "0");
        }
        return () => {
          scrollElement.removeEventListener("keydown", handleKeyDown);
        };
      }
    }, [scrollRef, messages]);
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      ChatViewVirtualListComponent,
      {
        id,
        listHandle,
        className,
        scrollRef,
        messages,
        initialMessageId,
        topOffset,
        toolCallStyle,
        indented,
        running,
        allowLinking,
        labels,
        showLabels,
        highlightLabeled
      }
    );
  }
);
const ChatViewVirtualListComponent = reactExports.memo(
  ({
    id,
    listHandle,
    messages,
    initialMessageId,
    topOffset,
    className,
    toolCallStyle,
    indented,
    scrollRef,
    running,
    allowLinking = true,
    labels,
    showLabels = true,
    highlightLabeled
  }) => {
    const collapsedMessages = reactExports.useMemo(() => {
      return resolveMessages(messages);
    }, [messages]);
    const initialMessageIndex = reactExports.useMemo(() => {
      if (initialMessageId === null || initialMessageId === void 0) {
        return void 0;
      }
      const index = collapsedMessages.findIndex((message) => {
        const messageId = message.message.id === initialMessageId;
        if (messageId) {
          return true;
        }
        if (message.toolMessages.find((tm) => tm.id === initialMessageId)) {
          return true;
        }
      });
      return index !== -1 ? index : void 0;
    }, [initialMessageId, collapsedMessages]);
    const renderRow = reactExports.useCallback(
      (index, item2) => {
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ChatMessageRow,
          {
            index,
            parentName: id || "chat-virtual-list",
            showLabels,
            highlightLabeled,
            labels,
            resolvedMessage: item2,
            indented,
            toolCallStyle,
            highlightUserMessage: true,
            allowLinking
          }
        );
      },
      // TODO: lint react-hooks/exhaustive-deps
      // eslint-disable-next-line react-hooks/exhaustive-deps
      [
        id,
        showLabels,
        labels,
        indented,
        toolCallStyle,
        collapsedMessages,
        highlightLabeled,
        allowLinking
      ]
    );
    const Item = ({
      children,
      ...props
    }) => {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: clsx(styles$2.item),
          "data-index": props["data-index"],
          "data-item-group-index": props["data-item-group-index"],
          "data-item-index": props["data-item-index"],
          "data-known-size": props["data-known-size"],
          style: props.style,
          children
        }
      );
    };
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      LiveVirtualList,
      {
        id: "chat-virtual-list",
        listHandle,
        className,
        scrollRef,
        data: collapsedMessages,
        renderRow,
        initialTopMostItemIndex: initialMessageIndex,
        offsetTop: topOffset,
        live: running,
        showProgress: running,
        components: { Item },
        animation: false,
        itemSearchText: messageSearchText
      }
    );
  }
);
const StickyScroll = ({
  children,
  scrollRef,
  offsetTop = 0,
  zIndex = 100,
  className = "",
  stickyClassName = "is-sticky",
  onStickyChange,
  preserveHeight = false
}) => {
  const wrapperRef = reactExports.useRef(null);
  const contentRef = reactExports.useRef(null);
  const [isSticky, setIsSticky] = reactExports.useState(false);
  const [dimensions, setDimensions] = reactExports.useState({
    width: 0,
    height: 0,
    left: 0,
    stickyTop: 0,
    // Store the position where the element should stick
    preStickHeight: 0
    // Height captured just before entering sticky mode
  });
  reactExports.useEffect(() => {
    const wrapper2 = wrapperRef.current;
    const content2 = contentRef.current;
    const scrollContainer = scrollRef.current;
    if (!wrapper2 || !content2 || !scrollContainer) {
      return;
    }
    const sentinel = document.createElement("div");
    sentinel.style.position = "absolute";
    sentinel.style.top = "0px";
    sentinel.style.left = "0";
    sentinel.style.width = "1px";
    sentinel.style.height = "1px";
    sentinel.style.pointerEvents = "none";
    wrapper2.prepend(sentinel);
    const widthTracker = document.createElement("div");
    widthTracker.style.position = "absolute";
    widthTracker.style.top = "0";
    widthTracker.style.left = "0";
    widthTracker.style.width = "100%";
    widthTracker.style.height = "0";
    widthTracker.style.pointerEvents = "none";
    widthTracker.style.visibility = "hidden";
    wrapper2.prepend(widthTracker);
    const updateDimensions = () => {
      if (wrapper2 && scrollContainer) {
        const contentRect = content2.getBoundingClientRect();
        const containerRect = scrollContainer.getBoundingClientRect();
        const trackerRect = widthTracker.getBoundingClientRect();
        const stickyTop = containerRect.top + offsetTop;
        setDimensions((prev) => ({
          ...prev,
          // Use the width tracker to get the right width that respects
          // the parent container's current width, rather than the content's width
          width: trackerRect.width,
          height: contentRect.height,
          left: trackerRect.left,
          stickyTop
        }));
      }
    };
    updateDimensions();
    const resizeObserver = new ResizeObserver(() => {
      requestAnimationFrame(() => {
        updateDimensions();
        if (isSticky) {
          handleScroll();
        }
      });
    });
    resizeObserver.observe(wrapper2);
    resizeObserver.observe(scrollContainer);
    resizeObserver.observe(content2);
    const handleScroll = () => {
      const sentinelRect = sentinel.getBoundingClientRect();
      const containerRect = scrollContainer.getBoundingClientRect();
      const shouldBeSticky = sentinelRect.top < containerRect.top + offsetTop;
      if (shouldBeSticky !== isSticky) {
        if (shouldBeSticky && preserveHeight && content2) {
          const capturedHeight = content2.getBoundingClientRect().height;
          setDimensions((prev) => ({
            ...prev,
            preStickHeight: capturedHeight
          }));
        }
        updateDimensions();
        setIsSticky(shouldBeSticky);
        if (onStickyChange) {
          onStickyChange(shouldBeSticky);
        }
      }
    };
    scrollContainer.addEventListener("scroll", handleScroll);
    handleScroll();
    return () => {
      resizeObserver.disconnect();
      scrollContainer.removeEventListener("scroll", handleScroll);
      if (sentinel.parentNode) {
        sentinel.parentNode.removeChild(sentinel);
      }
      if (widthTracker.parentNode) {
        widthTracker.parentNode.removeChild(widthTracker);
      }
    };
  }, [scrollRef, offsetTop, onStickyChange, isSticky, preserveHeight]);
  const wrapperStyle = {
    position: "relative",
    height: isSticky ? `${preserveHeight ? dimensions.preStickHeight : dimensions.height}px` : "auto"
    // Don't constrain width - let it flow naturally with the content
  };
  const contentStyle = isSticky ? {
    position: "fixed",
    top: `${dimensions.stickyTop}px`,
    left: `${dimensions.left}px`,
    width: `${dimensions.width}px`,
    // Keep explicit width to prevent expanding to 100%
    maxHeight: `calc(100vh - ${dimensions.stickyTop}px)`,
    zIndex
  } : {};
  const contentClassName = isSticky && stickyClassName ? `${className} ${stickyClassName}`.trim() : className;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: wrapperRef, style: wrapperStyle, children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: contentRef, className: contentClassName, style: contentStyle, children }) });
};
const emptySourceSpans = /* @__PURE__ */ new Map();
function useTranscriptTimeline(events) {
  const timeline = reactExports.useMemo(() => buildTimeline(events), [events]);
  const state = useTimeline(timeline);
  const prevTimelineRef = reactExports.useRef(timeline);
  reactExports.useEffect(() => {
    if (prevTimelineRef.current !== timeline) {
      prevTimelineRef.current = timeline;
      state.navigateTo("");
    }
  }, [timeline]);
  const visibleRows = reactExports.useMemo(
    () => state.rows.filter((row, i) => i === 0 || rowHasEvents(row)),
    [state.rows]
  );
  const timeMapping = reactExports.useMemo(
    () => computeTimeMapping(state.node),
    [state.node]
  );
  const rootTimeMapping = reactExports.useMemo(
    () => computeTimeMapping(timeline.root),
    [timeline.root]
  );
  const layouts = reactExports.useMemo(
    () => computeRowLayouts(visibleRows, timeMapping, "direct"),
    [visibleRows, timeMapping]
  );
  const { selectedEvents, sourceSpans } = reactExports.useMemo(() => {
    const spans = getSelectedSpans(state.rows, state.selected);
    if (spans.length === 0) {
      return { selectedEvents: events, sourceSpans: emptySourceSpans };
    }
    const collected = collectRawEvents(spans);
    return {
      selectedEvents: collected.events,
      sourceSpans: collected.sourceSpans
    };
  }, [events, state.rows, state.selected]);
  const minimapSelection = reactExports.useMemo(
    () => computeMinimapSelection(state.rows, state.selected),
    [state.rows, state.selected]
  );
  const hasTimeline = timeline.root.content.length > 0 && timeline.root.content.some((item2) => item2.type === "span");
  return {
    timeline: hasTimeline ? timeline : null,
    state,
    layouts,
    timeMapping,
    rootTimeMapping,
    selectedEvents,
    sourceSpans,
    minimapSelection,
    hasTimeline
  };
}
const root = "_root_f0ryp_1";
const eventsContainer = "_eventsContainer_f0ryp_9";
const outlineCollapsed = "_outlineCollapsed_f0ryp_17";
const eventsOutline = "_eventsOutline_f0ryp_21";
const outlineToggle = "_outlineToggle_f0ryp_26";
const eventsSeparator = "_eventsSeparator_f0ryp_40";
const eventsList = "_eventsList_f0ryp_44";
const styles$1 = {
  root,
  eventsContainer,
  outlineCollapsed,
  eventsOutline,
  outlineToggle,
  eventsSeparator,
  eventsList
};
const collectAllCollapsibleIds = (nodes) => {
  const result = {};
  const traverse = (nodeList) => {
    for (const node of nodeList) {
      if (kCollapsibleEventTypes.includes(node.event.event)) {
        result[node.id] = true;
      }
      if (node.children.length > 0) {
        traverse(node.children);
      }
    }
  };
  traverse(nodes);
  return result;
};
const TimelineEventsView = reactExports.forwardRef(function TimelineEventsView2({
  events,
  scrollRef,
  offsetTop = 0,
  initialEventId,
  defaultOutlineExpanded = false,
  id,
  collapsed,
  onMarkerNavigate,
  className
}, ref) {
  const {
    timeline: timelineData,
    state: timelineState,
    layouts: timelineLayouts,
    rootTimeMapping,
    selectedEvents,
    sourceSpans,
    minimapSelection,
    hasTimeline
  } = useTranscriptTimeline(events);
  const spanSelectKeys = reactExports.useMemo(
    () => buildSpanSelectKeys(timelineState.rows),
    [timelineState.rows]
  );
  const {
    select: timelineSelect,
    drillDownAndSelect: timelineDrillDownAndSelect
  } = timelineState;
  const selectBySpanId = reactExports.useCallback(
    (spanId) => {
      const key = spanSelectKeys.get(spanId);
      if (!key) return;
      if (key.parallel && key.spanIndex) {
        timelineDrillDownAndSelect(key.name, `${key.name} ${key.spanIndex}`);
      } else {
        timelineSelect(key.name, key.spanIndex);
      }
    },
    [spanSelectKeys, timelineSelect, timelineDrillDownAndSelect]
  );
  const suppressCollapseRef = reactExports.useRef(false);
  const [markerNavSticky, setMarkerNavSticky] = reactExports.useState(false);
  const [isSwimLaneSticky, setIsSwimLaneSticky] = reactExports.useState(false);
  const [stickySwimLaneHeight, setStickySwimLaneHeight] = reactExports.useState(0);
  const swimLaneStickyContentRef = reactExports.useRef(null);
  reactExports.useImperativeHandle(
    ref,
    () => ({
      suppressNextCollapse: () => {
        suppressCollapseRef.current = true;
      }
    }),
    []
  );
  const handleSwimLaneStickyChange = reactExports.useCallback((sticky) => {
    setIsSwimLaneSticky(sticky);
    if (sticky && suppressCollapseRef.current) {
      suppressCollapseRef.current = false;
      setMarkerNavSticky(true);
    } else if (!sticky) {
      setStickySwimLaneHeight(0);
      setMarkerNavSticky(false);
    }
  }, []);
  reactExports.useEffect(() => {
    const el = swimLaneStickyContentRef.current;
    if (!isSwimLaneSticky || !el) {
      return;
    }
    const observer = new ResizeObserver(() => {
      setStickySwimLaneHeight(el.getBoundingClientRect().height);
    });
    observer.observe(el);
    setStickySwimLaneHeight(el.getBoundingClientRect().height);
    return () => observer.disconnect();
  }, [isSwimLaneSticky]);
  const { eventNodes, defaultCollapsedIds } = useEventNodes(
    selectedEvents,
    false,
    sourceSpans
  );
  const hasMatchingEvents = eventNodes.length > 0;
  reactExports.useEffect(() => {
    if (!initialEventId) {
      scrollRef.current?.scrollTo({ top: 0 });
    }
  }, [selectedEvents, initialEventId, scrollRef]);
  const setCollapsedEvents = useStore(
    (state) => state.setTranscriptCollapsedEvents
  );
  reactExports.useEffect(() => {
    if (events.length <= 0 || collapsed === void 0) {
      return;
    }
    if (!collapsed && Object.keys(defaultCollapsedIds).length > 0) {
      setCollapsedEvents(kTranscriptCollapseScope, defaultCollapsedIds);
    } else if (collapsed) {
      const allCollapsibleIds = collectAllCollapsibleIds(eventNodes);
      setCollapsedEvents(kTranscriptCollapseScope, allCollapsibleIds);
    }
  }, [
    defaultCollapsedIds,
    eventNodes,
    collapsed,
    setCollapsedEvents,
    events.length
  ]);
  const [outlineCollapsed2, setOutlineCollapsed] = useProperty(
    "timelineEvents",
    "outlineCollapsed",
    { defaultValue: !defaultOutlineExpanded, cleanup: false }
  );
  const isOutlineCollapsed = outlineCollapsed2 ?? !defaultOutlineExpanded;
  const [reportedHasNodes, setReportedHasNodes] = reactExports.useState(true);
  const outlineHasNodes = isOutlineCollapsed ? hasMatchingEvents : reportedHasNodes;
  const [outlineWidth, setOutlineWidth] = reactExports.useState();
  const handleOutlineHasNodesChange = reactExports.useCallback(
    (hasNodes) => {
      setReportedHasNodes(hasNodes);
      if (!hasNodes && !isOutlineCollapsed) {
        setOutlineCollapsed(true);
      }
    },
    [isOutlineCollapsed, setOutlineCollapsed]
  );
  const atRoot = timelineState.breadcrumbs.length <= 1;
  const scrollToTop = reactExports.useCallback(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [scrollRef]);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(TimelineSelectContext.Provider, { value: selectBySpanId, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$1.root, className), children: [
    hasTimeline && timelineData && /* @__PURE__ */ jsxRuntimeExports.jsx(
      StickyScroll,
      {
        scrollRef,
        offsetTop,
        zIndex: 500,
        preserveHeight: true,
        onStickyChange: handleSwimLaneStickyChange,
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: swimLaneStickyContentRef, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          TimelineSwimLanes,
          {
            layouts: timelineLayouts,
            timeline: timelineState,
            header: {
              breadcrumbs: timelineState.breadcrumbs,
              atRoot,
              onNavigate: timelineState.navigateTo,
              onScrollToTop: scrollToTop,
              minimap: {
                root: timelineData.root,
                selection: minimapSelection,
                mapping: rootTimeMapping
              }
            },
            onMarkerNavigate,
            isSticky: isSwimLaneSticky,
            forceCollapsed: isSwimLaneSticky && !markerNavSticky,
            noAnimation: isSwimLaneSticky && !markerNavSticky
          }
        ) })
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(
          styles$1.eventsContainer,
          isOutlineCollapsed && styles$1.outlineCollapsed
        ),
        style: !isOutlineCollapsed && outlineWidth ? { "--outline-width": `${outlineWidth}px` } : void 0,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            StickyScroll,
            {
              scrollRef,
              className: styles$1.eventsOutline,
              offsetTop: offsetTop + stickySwimLaneHeight,
              children: [
                !isOutlineCollapsed && /* @__PURE__ */ jsxRuntimeExports.jsx(
                  TranscriptOutline,
                  {
                    eventNodes,
                    defaultCollapsedIds,
                    scrollRef,
                    onHasNodesChange: handleOutlineHasNodesChange,
                    onWidthChange: setOutlineWidth
                  }
                ),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    type: "button",
                    className: styles$1.outlineToggle,
                    onClick: outlineHasNodes ? () => setOutlineCollapsed(!isOutlineCollapsed) : void 0,
                    "aria-disabled": !outlineHasNodes,
                    title: outlineHasNodes ? void 0 : "No outline available for the current filter",
                    "aria-label": isOutlineCollapsed ? "Show outline" : "Hide outline",
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.sidebar })
                  }
                )
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.eventsSeparator }),
          hasMatchingEvents ? /* @__PURE__ */ jsxRuntimeExports.jsx(
            TranscriptViewNodes,
            {
              id,
              eventNodes,
              defaultCollapsedIds,
              initialEventId,
              offsetTop: offsetTop + stickySwimLaneHeight,
              className: styles$1.eventsList,
              scrollRef
            }
          ) : /* @__PURE__ */ jsxRuntimeExports.jsx(NoContentsPanel, { text: "No events match the current filter" })
        ]
      }
    )
  ] }) });
});
const container = "_container_1i4o7_1";
const nav = "_nav_1i4o7_9";
const disabled = "_disabled_1i4o7_9";
const center = "_center_1i4o7_18";
const styles = {
  container,
  nav,
  disabled,
  center
};
const NextPreviousNav = ({
  onPrevious,
  onNext,
  hasPrevious,
  hasNext,
  children,
  enableKeyboardNav = true
}) => {
  reactExports.useEffect(() => {
    if (!enableKeyboardNav) {
      return;
    }
    const handleGlobalKeyDown = (e) => {
      const activeElement = document.activeElement;
      const isInputFocused = activeElement && (activeElement.tagName === "INPUT" || activeElement.tagName === "TEXTAREA" || activeElement.tagName === "SELECT");
      if (isInputFocused) {
        return;
      }
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
        return;
      }
      if (e.key === "ArrowLeft" && hasPrevious && onPrevious) {
        e.preventDefault();
        onPrevious();
      } else if (e.key === "ArrowRight" && hasNext && onNext) {
        e.preventDefault();
        onNext();
      }
    };
    document.addEventListener("keydown", handleGlobalKeyDown, true);
    return () => {
      document.removeEventListener("keydown", handleGlobalKeyDown, true);
    };
  }, [enableKeyboardNav, hasPrevious, hasNext, onPrevious, onNext]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        onClick: hasPrevious ? onPrevious : void 0,
        tabIndex: hasPrevious ? 0 : void 0,
        className: clsx(styles.nav, !hasPrevious && styles.disabled),
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.previous })
      }
    ),
    children && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.center, children }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        onClick: hasNext ? onNext : void 0,
        tabIndex: hasNext ? 0 : void 0,
        className: clsx(styles.nav, !hasNext && styles.disabled),
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.next })
      }
    )
  ] });
};
export {
  ChatViewVirtualList as C,
  NextPreviousNav as N,
  TimelineEventsView as T,
  ValidationCaseEditor as V,
  getTranscriptDisplayName as g
};
//# sourceMappingURL=NextPreviousNav.js.map
