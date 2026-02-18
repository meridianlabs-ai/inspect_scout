import { u as useApi, a as useAsyncDataFromQuery, b as useQueryClient, y as skipToken, A as ApiError, r as reactExports, j as jsxRuntimeExports, k as reactDomExports, C as projectOrAppAliasedPath, bS as dirname } from "./index.js";
import { u as useMutation, b as VscodeTextfield, f as VscodeSingleSelect, g as VscodeOption } from "./VscodeTreeItem.js";
import { M as Modal } from "./Modal.js";
const validationQueryKeys = {
  sets: () => ["validationSets"],
  cases: (uri) => ["validationCases", uri],
  case: (params) => ["validationCase", params]
};
const useValidationSets = () => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: validationQueryKeys.sets(),
    queryFn: () => api.getValidationSets(),
    staleTime: 60 * 1e3
  });
};
const useValidationCases = (uri) => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: validationQueryKeys.cases(uri),
    queryFn: uri === skipToken ? skipToken : () => api.getValidationCases(uri),
    staleTime: 60 * 1e3,
    enabled: uri !== skipToken
  });
};
const useValidationCase = (params) => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: validationQueryKeys.case(params),
    queryFn: params === skipToken ? skipToken : async () => {
      try {
        return await api.getValidationCase(params.url, params.caseId);
      } catch (error2) {
        if (error2 instanceof ApiError && error2.status === 404) {
          return null;
        }
        throw error2;
      }
    },
    staleTime: 60 * 1e3
  });
};
const useCreateValidationSet = () => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation({
    mutationFn: (request) => api.createValidationSet(request),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.sets()
      });
    }
  });
};
const useUpdateValidationCase = (uri) => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation({
    mutationFn: ({ caseId, data }) => api.upsertValidationCase(uri, caseId, data),
    onMutate: ({ caseId, data }) => {
      void queryClient.cancelQueries({
        queryKey: validationQueryKeys.case({ url: uri, caseId })
      });
      void queryClient.cancelQueries({
        queryKey: validationQueryKeys.cases(uri)
      });
      const previousCase = queryClient.getQueryData(
        validationQueryKeys.case({ url: uri, caseId })
      );
      const previousCases = queryClient.getQueryData(
        validationQueryKeys.cases(uri)
      );
      if (previousCase) {
        queryClient.setQueryData(
          validationQueryKeys.case({ url: uri, caseId }),
          { ...previousCase, ...data }
        );
      }
      if (previousCases) {
        queryClient.setQueryData(
          validationQueryKeys.cases(uri),
          previousCases.map((c) => c.id === caseId ? { ...c, ...data } : c)
        );
      }
      return { previousCase, previousCases };
    },
    onError: (_err, { caseId }, context) => {
      if (context?.previousCase) {
        queryClient.setQueryData(
          validationQueryKeys.case({ url: uri, caseId }),
          context.previousCase
        );
      }
      if (context?.previousCases) {
        queryClient.setQueryData(
          validationQueryKeys.cases(uri),
          context.previousCases
        );
      }
    },
    onSuccess: (_data, { caseId }) => {
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.case({ url: uri, caseId })
      });
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.cases(uri)
      });
    }
  });
};
const useDeleteValidationCase = (uri) => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation({
    mutationFn: (caseId) => api.deleteValidationCase(uri, caseId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.cases(uri)
      });
    }
  });
};
const useBulkDeleteValidationCases = (uri) => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation({
    mutationFn: async (caseIds) => {
      const results = await Promise.allSettled(
        caseIds.map((id) => api.deleteValidationCase(uri, id))
      );
      const succeeded = results.filter((r) => r.status === "fulfilled").length;
      const failed = results.filter((r) => r.status === "rejected").length;
      if (succeeded > 0) {
        void queryClient.invalidateQueries({
          queryKey: validationQueryKeys.cases(uri)
        });
      }
      if (failed === results.length) {
        const errors = results.filter((r) => r.status === "rejected").map((r) => r.reason);
        throw new Error(`All deletions failed: ${errors.join(", ")}`);
      }
      return { succeeded, failed };
    }
  });
};
const useDeleteValidationSet = () => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation({
    mutationFn: (uri) => api.deleteValidationSet(uri),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.sets()
      });
    }
  });
};
const useRenameValidationSet = () => {
  const queryClient = useQueryClient();
  const api = useApi();
  return useMutation({
    mutationFn: ({ uri, newName }) => api.renameValidationSet(uri, newName),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.sets()
      });
    }
  });
};
const VALIDATION_SET_EXTENSIONS = [
  ".csv",
  ".json",
  ".jsonl",
  ".yml",
  ".yaml"
];
const hasValidationSetExtension = (name) => {
  const lower = name.toLowerCase();
  return VALIDATION_SET_EXTENSIONS.some((ext) => lower.endsWith(ext));
};
const getIdText = (id) => {
  return Array.isArray(id) ? id.join(", ") : id;
};
const getCaseKey = (id) => {
  return Array.isArray(id) ? id.join("|") : id;
};
const extractUniqueLabels = (cases) => {
  const labelKeys = /* @__PURE__ */ new Set();
  for (const c of cases) {
    if (c.labels) {
      for (const key of Object.keys(c.labels)) {
        labelKeys.add(key);
      }
    }
  }
  return Array.from(labelKeys).sort();
};
const extractUniqueSplits = (cases) => {
  const splitSet = /* @__PURE__ */ new Set();
  for (const c of cases) {
    if (c.split) {
      splitSet.add(c.split);
    }
  }
  return Array.from(splitSet).sort();
};
const getFilenameFromUri = (uri, stripExtension = false) => {
  const filename = uri.split("/").pop() ?? uri;
  if (stripExtension) {
    return filename.replace(/\.(csv|json|jsonl|yaml|yml)$/i, "");
  }
  return filename;
};
const getDirFromUri = (uri) => {
  const parts = uri.split("/");
  parts.pop();
  return parts.join("/");
};
const generateNewSetUri = (sourceUri, newName) => {
  const dir = getDirFromUri(sourceUri);
  return `${dir}/${newName}.csv`;
};
const INVALID_FILENAME_CHARS = /[/\\:*?"<>|]/;
const isValidFilename = (name) => {
  if (!name.trim()) {
    return { isValid: false, error: "Name cannot be empty" };
  }
  if (INVALID_FILENAME_CHARS.test(name)) {
    return {
      isValid: false,
      error: 'Name contains invalid characters: / \\ : * ? " < > |'
    };
  }
  if (name.startsWith(".")) {
    return { isValid: false, error: "Name cannot start with a dot" };
  }
  if (name.length > 255) {
    return { isValid: false, error: "Name is too long (max 255 characters)" };
  }
  return { isValid: true };
};
function useDropdownPosition(options) {
  const {
    optionCount,
    optionHeight = 22,
    maxVisibleOptions = 10,
    padding = 8
  } = options;
  const [element, setElement] = reactExports.useState(null);
  const [position, setPosition] = reactExports.useState("below");
  const ref = reactExports.useCallback(
    (node) => {
      setElement(node);
    },
    []
  );
  reactExports.useEffect(() => {
    if (!element) {
      return;
    }
    const calculatePosition = () => {
      const rect = element.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const visibleOptions = Math.min(optionCount, maxVisibleOptions);
      const estimatedHeight = visibleOptions * optionHeight + padding;
      setPosition(spaceBelow >= estimatedHeight ? "below" : "above");
    };
    calculatePosition();
    let timeoutId = null;
    const debouncedCalculate = () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      timeoutId = setTimeout(calculatePosition, 100);
    };
    window.addEventListener("resize", debouncedCalculate);
    window.addEventListener("scroll", debouncedCalculate, true);
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      window.removeEventListener("resize", debouncedCalculate);
      window.removeEventListener("scroll", debouncedCalculate, true);
    };
  }, [element, optionCount, optionHeight, maxVisibleOptions, padding]);
  return { ref, position };
}
const container = "_container_4r2t1_1";
const trigger = "_trigger_4r2t1_8";
const chevron = "_chevron_4r2t1_26";
const triggerContent = "_triggerContent_4r2t1_44";
const triggerSizer = "_triggerSizer_4r2t1_49";
const triggerPrimary = "_triggerPrimary_4r2t1_57";
const triggerPlaceholder = "_triggerPlaceholder_4r2t1_71";
const dropdown = "_dropdown_4r2t1_76";
const item = "_item_4r2t1_91";
const selected = "_selected_4r2t1_106";
const primaryText = "_primaryText_4r2t1_110";
const secondaryText = "_secondaryText_4r2t1_111";
const error = "_error_4r2t1_138";
const divider = "_divider_4r2t1_143";
const createOption = "_createOption_4r2t1_155";
const modalContent$1 = "_modalContent_4r2t1_173";
const hint = "_hint_4r2t1_183";
const modalButton$1 = "_modalButton_4r2t1_190";
const modalButtonPrimary$1 = "_modalButtonPrimary_4r2t1_209";
const styles$1 = {
  container,
  trigger,
  chevron,
  triggerContent,
  triggerSizer,
  triggerPrimary,
  triggerPlaceholder,
  dropdown,
  item,
  selected,
  primaryText,
  secondaryText,
  error,
  divider,
  createOption,
  modalContent: modalContent$1,
  hint,
  modalButton: modalButton$1,
  modalButtonPrimary: modalButtonPrimary$1
};
const ValidationSetSelector = ({
  validationSets,
  selectedUri,
  onSelect,
  autoSize = false,
  allowCreate = false,
  onCreate,
  appConfig
}) => {
  const [isOpen, setIsOpen] = reactExports.useState(false);
  const [dropdownStyle, setDropdownStyle] = reactExports.useState({});
  const containerRef = reactExports.useRef(null);
  const triggerRef = reactExports.useRef(null);
  const dropdownRef = reactExports.useRef(null);
  const [showCreateModal, setShowCreateModal] = reactExports.useState(false);
  const [newSetName, setNewSetName] = reactExports.useState("");
  const [validationError, setValidationError] = reactExports.useState(null);
  const getDisplayName = (uri) => {
    return getFilenameFromUri(uri);
  };
  const longestDisplayName = reactExports.useMemo(() => {
    if (validationSets.length === 0) return "";
    return validationSets.reduce((longest, uri) => {
      const name = getDisplayName(uri);
      return name.length > longest.length ? name : longest;
    }, "");
  }, [validationSets]);
  const getDisplayPath = (uri, appConfig2) => {
    let path = appConfig2 ? projectOrAppAliasedPath(appConfig2, dirname(uri)) : dirname(uri);
    if (path && path.startsWith("file://")) {
      path = path.slice(7);
    }
    return path ?? uri;
  };
  reactExports.useEffect(() => {
    if (isOpen && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setDropdownStyle({
        position: "fixed",
        top: rect.bottom + 2,
        left: rect.left,
        width: rect.width
      });
    }
  }, [isOpen]);
  reactExports.useEffect(() => {
    if (!isOpen || !triggerRef.current) return;
    let initialCall = true;
    const observer = new ResizeObserver(() => {
      if (initialCall) {
        initialCall = false;
        return;
      }
      setIsOpen(false);
    });
    observer.observe(triggerRef.current);
    return () => observer.disconnect();
  }, [isOpen]);
  reactExports.useEffect(() => {
    const handleClickOutside = (e) => {
      const target = e.target;
      const isOutsideContainer = containerRef.current && !containerRef.current.contains(target);
      const isOutsideDropdown = dropdownRef.current && !dropdownRef.current.contains(target);
      if (isOutsideContainer && isOutsideDropdown) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);
  const handleSelect = (uri) => {
    if (uri === "__create_new__") {
      setShowCreateModal(true);
      setNewSetName("");
      setValidationError(null);
      setIsOpen(false);
    } else {
      onSelect(uri);
      setIsOpen(false);
    }
  };
  const hasAnyExtension = (name) => {
    const lastDot = name.lastIndexOf(".");
    return lastDot > 0 && lastDot < name.length - 1;
  };
  const isTypingExtension = (name) => {
    const lastDot = name.lastIndexOf(".");
    return lastDot > 0;
  };
  const isValidPartialExtension = (name) => {
    const lastDot = name.lastIndexOf(".");
    if (lastDot <= 0) return true;
    const partialExt = name.slice(lastDot).toLowerCase();
    return VALIDATION_SET_EXTENSIONS.some((ext) => ext.startsWith(partialExt));
  };
  const getExtensionError = (name) => {
    const trimmed = name.trim();
    if (!trimmed) return null;
    if (isTypingExtension(trimmed) && !isValidPartialExtension(trimmed)) {
      return `Invalid extension. Valid extensions: ${VALIDATION_SET_EXTENSIONS.join(", ")}`;
    }
    return null;
  };
  const handleNameInput = (e) => {
    setNewSetName(e.target.value);
    setValidationError(null);
  };
  const handleCreateSubmit = () => {
    const trimmedName = newSetName.trim();
    if (!trimmedName) return;
    if (hasAnyExtension(trimmedName) && !hasValidationSetExtension(trimmedName)) {
      setValidationError(
        `Invalid extension. Valid extensions: ${VALIDATION_SET_EXTENSIONS.join(", ")}`
      );
      return;
    }
    onCreate?.(trimmedName);
    setShowCreateModal(false);
    setNewSetName("");
    setValidationError(null);
  };
  const handleModalClose = () => {
    setShowCreateModal(false);
    setNewSetName("");
    setValidationError(null);
  };
  const handleKeyDown = (e) => {
    if (!isOpen) {
      if (e.key === "Enter" || e.key === " " || e.key === "ArrowDown") {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }
    const currentIndex = selectedUri ? validationSets.indexOf(selectedUri) : -1;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const nextIndex = Math.min(currentIndex + 1, validationSets.length - 1);
      onSelect(validationSets[nextIndex]);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prevIndex = Math.max(currentIndex - 1, 0);
      onSelect(validationSets[prevIndex]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    } else if (e.key === "Enter") {
      setIsOpen(false);
    }
  };
  const hasNonRootDir = validationSets.some((uri) => {
    return !!getDisplayPath(uri, appConfig);
  });
  const dropdown2 = isOpen ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      ref: dropdownRef,
      className: styles$1.dropdown,
      style: dropdownStyle,
      role: "listbox",
      children: [
        validationSets.map((uri) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            role: "option",
            "aria-selected": selectedUri === uri,
            className: `${styles$1.item} ${selectedUri === uri ? styles$1.selected : ""}`,
            onClick: () => handleSelect(uri),
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.primaryText, children: getDisplayName(uri) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.secondaryText, children: getDisplayPath(uri, appConfig) || (hasNonRootDir ? " " : "") })
            ]
          },
          uri
        )),
        allowCreate && onCreate && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          validationSets.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.divider }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              role: "option",
              "aria-selected": false,
              className: `${styles$1.item} ${styles$1.createOption}`,
              onClick: () => handleSelect("__create_new__"),
              children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$1.primaryText, children: "Create new set..." })
            }
          )
        ] })
      ]
    }
  ) : null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { ref: containerRef, className: styles$1.container, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          ref: triggerRef,
          className: styles$1.trigger,
          onClick: () => setIsOpen(!isOpen),
          onKeyDown: handleKeyDown,
          "aria-expanded": isOpen,
          "aria-haspopup": "listbox",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$1.triggerContent, children: [
              autoSize && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.triggerSizer, "aria-hidden": "true", children: longestDisplayName }),
              selectedUri ? /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.triggerPrimary, children: getDisplayName(selectedUri) }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.triggerPlaceholder, children: "Select validation set..." })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.chevron, "aria-hidden": "true", children: "⌃" })
          ]
        }
      ),
      reactDomExports.createPortal(dropdown2, document.body)
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Modal,
      {
        show: showCreateModal,
        onHide: handleModalClose,
        onSubmit: newSetName.trim() ? handleCreateSubmit : void 0,
        title: "Create New Validation Set",
        footer: /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { className: styles$1.modalButton, onClick: handleModalClose, children: "Cancel" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              className: `${styles$1.modalButton} ${styles$1.modalButtonPrimary}`,
              onClick: handleCreateSubmit,
              disabled: !newSetName.trim(),
              children: "Create"
            }
          )
        ] }),
        children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$1.modalContent, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "Enter a name for the new validation set:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeTextfield,
            {
              value: newSetName,
              onInput: handleNameInput,
              placeholder: "validation-set-name",
              "data-autofocus": true
            }
          ),
          (() => {
            const trimmedName = newSetName.trim();
            const extensionError = getExtensionError(trimmedName);
            const displayError = validationError || extensionError;
            const displayDir = appConfig?.project_dir?.startsWith("file://") ? appConfig?.project_dir.slice(7) : appConfig?.project_dir;
            if (trimmedName && !displayError && displayDir) {
              const filename = isTypingExtension(trimmedName) ? trimmedName : `${trimmedName}.csv`;
              return /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$1.hint, children: [
                displayDir,
                "/",
                filename
              ] });
            }
            if (displayError) {
              return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.error, children: displayError });
            }
            return null;
          })()
        ] })
      }
    )
  ] });
};
const modalContent = "_modalContent_cmqyy_2";
const modalButton = "_modalButton_cmqyy_12";
const modalButtonPrimary = "_modalButtonPrimary_cmqyy_26";
const styles = {
  modalContent,
  modalButton,
  modalButtonPrimary
};
const ValidationSplitSelector = ({
  value,
  existingSplits,
  onChange,
  disabled = false,
  className,
  noSplitLabel = "(Optional)",
  newSplitLabel = "New split..."
}) => {
  const [showCustomModal, setShowCustomModal] = reactExports.useState(false);
  const [customSplitValue, setCustomSplitValue] = reactExports.useState("");
  const effectiveSplits = reactExports.useMemo(() => {
    if (value && !existingSplits.includes(value)) {
      return [...existingSplits, value].sort();
    }
    return existingSplits;
  }, [existingSplits, value]);
  const { ref, position } = useDropdownPosition({
    optionCount: effectiveSplits.length + 2
  });
  const selectValue = value ?? "__none__";
  const handleSelectChange = (e) => {
    const newValue = e.target.value;
    if (newValue === "__custom__") {
      setShowCustomModal(true);
      setCustomSplitValue("");
    } else if (newValue === "__none__") {
      onChange(null);
    } else {
      onChange(newValue);
    }
  };
  const handleCustomInput = (e) => {
    setCustomSplitValue(e.target.value);
  };
  const handleCustomSubmit = () => {
    if (customSplitValue.trim()) {
      onChange(customSplitValue.trim());
    }
    setShowCustomModal(false);
    setCustomSplitValue("");
  };
  const handleModalClose = () => {
    setShowCustomModal(false);
    setCustomSplitValue("");
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref, children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
      VscodeSingleSelect,
      {
        value: selectValue,
        onChange: handleSelectChange,
        className,
        disabled,
        position,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "__none__", children: noSplitLabel }),
          effectiveSplits.map((s) => /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: s, children: s }, s)),
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "__custom__", children: newSplitLabel })
        ]
      }
    ) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Modal,
      {
        show: showCustomModal,
        onHide: handleModalClose,
        onSubmit: customSplitValue.trim() ? handleCustomSubmit : void 0,
        title: "New Split",
        footer: /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { className: styles.modalButton, onClick: handleModalClose, children: "Cancel" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              className: `${styles.modalButton} ${styles.modalButtonPrimary}`,
              onClick: handleCustomSubmit,
              disabled: !customSplitValue.trim(),
              children: "Create"
            }
          )
        ] }),
        children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.modalContent, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "Enter a name for the new split:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeTextfield,
            {
              value: customSplitValue,
              onInput: handleCustomInput,
              placeholder: "Split name",
              "data-autofocus": true
            }
          )
        ] })
      }
    )
  ] });
};
export {
  ValidationSetSelector as V,
  useValidationSets as a,
  useValidationCase as b,
  useValidationCases as c,
  useCreateValidationSet as d,
  useDeleteValidationCase as e,
  useUpdateValidationCase as f,
  extractUniqueLabels as g,
  hasValidationSetExtension as h,
  isValidFilename as i,
  ValidationSplitSelector as j,
  extractUniqueSplits as k,
  useBulkDeleteValidationCases as l,
  getFilenameFromUri as m,
  generateNewSetUri as n,
  getCaseKey as o,
  getIdText as p,
  useDeleteValidationSet as q,
  useRenameValidationSet as r,
  styles$1 as s,
  useDropdownPosition as u,
  validationQueryKeys as v
};
//# sourceMappingURL=ValidationSplitSelector.js.map
