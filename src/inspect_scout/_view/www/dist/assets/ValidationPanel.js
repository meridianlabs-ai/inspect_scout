import { j as jsxRuntimeExports, c as clsx, a as useApi, r as reactExports, U as useQuery, s as skipToken, J as useQueryClient, w as useNavigate, A as ApplicationIcons, x as transcriptRoute, u as useStore, e as useAppConfig } from "./index.js";
import { d as VscodeSingleSelect, e as VscodeOption, f as VscodeTextfield, a as VscodeButton, j as VscodeCheckbox } from "./VscodeTreeItem.js";
import { M as Modal } from "./Modal.js";
import { T as TextInput } from "./TextInput.js";
import { u as useDocumentTitle } from "./useDocumentTitle.js";
import { a as useValidationSets, c as useValidationCases, k as extractUniqueSplits, d as useCreateValidationSet, l as useBulkDeleteValidationCases, m as getFilenameFromUri, v as validationQueryKeys, i as isValidFilename, n as generateNewSetUri, o as getCaseKey, p as getIdText, j as ValidationSplitSelector, f as useUpdateValidationCase, q as useDeleteValidationSet, r as useRenameValidationSet, V as ValidationSetSelector } from "./ValidationSplitSelector.js";
import { C as Column } from "./transcriptColumns.js";
import "./_commonjsHelpers.js";
import "./useMutation.js";
const container$3 = "_container_cr35j_1";
const icon = "_icon_cr35j_17";
const title$1 = "_title_cr35j_23";
const description = "_description_cr35j_30";
const action = "_action_cr35j_37";
const styles$5 = {
  container: container$3,
  icon,
  title: title$1,
  description,
  action
};
const NonIdealState = ({
  icon: icon2,
  title: title2,
  description: description2,
  action: action2,
  className
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$5.container, className), children: [
    icon2 && /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(styles$5.icon, icon2) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$5.title, children: title2 }),
    description2 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$5.description, children: description2 }),
    action2 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$5.action, children: action2 })
  ] });
};
const useTranscriptsByIds = (transcriptsDir, ids) => {
  const api = useApi();
  const filter = reactExports.useMemo(() => {
    if (ids.length === 0) return void 0;
    return new Column("transcript_id").in(ids);
  }, [ids]);
  const queryKey = reactExports.useMemo(() => {
    const sortedIds = [...ids].sort();
    return ["transcriptsByIds", transcriptsDir, sortedIds];
  }, [transcriptsDir, ids]);
  const query = useQuery({
    queryKey,
    queryFn: !transcriptsDir || ids.length === 0 ? skipToken : async () => {
      const response = await api.getTranscripts(
        transcriptsDir,
        filter,
        void 0,
        { limit: ids.length, cursor: null, direction: "forward" }
      );
      return response.items;
    },
    staleTime: 60 * 1e3
  });
  const transcriptMap = reactExports.useMemo(() => {
    if (!query.data) return void 0;
    const map = /* @__PURE__ */ new Map();
    for (const transcript of query.data) {
      map.set(transcript.transcript_id, transcript);
    }
    return map;
  }, [query.data]);
  const sourceIds = reactExports.useMemo(() => {
    if (!query.data) return void 0;
    return new Set(ids);
  }, [query.data, ids]);
  return {
    data: transcriptMap,
    sourceIds,
    loading: query.isLoading,
    error: query.error
  };
};
const modalContent$3 = "_modalContent_x5gpr_1";
const fieldGroup = "_fieldGroup_x5gpr_12";
const label = "_label_x5gpr_18";
const select = "_select_x5gpr_23";
const textInput = "_textInput_x5gpr_27";
const hint = "_hint_x5gpr_31";
const error$1 = "_error_x5gpr_37";
const styles$4 = {
  modalContent: modalContent$3,
  fieldGroup,
  label,
  select,
  textInput,
  hint,
  error: error$1
};
const KEEP_ORIGINAL_SPLIT = "__keep__";
const NO_SPLIT = "__none__";
const CopyMoveCasesModal = ({
  show,
  mode,
  sourceUri,
  selectedIds,
  selectedCases,
  onHide,
  onSuccess
}) => {
  const api = useApi();
  const queryClient = useQueryClient();
  const [targetUri, setTargetUri] = reactExports.useState(void 0);
  const [targetSplit, setTargetSplit] = reactExports.useState(KEEP_ORIGINAL_SPLIT);
  const [showNewSetInput, setShowNewSetInput] = reactExports.useState(false);
  const [newSetName, setNewSetName] = reactExports.useState("");
  const [isProcessing, setIsProcessing] = reactExports.useState(false);
  const [error2, setError] = reactExports.useState(null);
  const { data: validationSets } = useValidationSets();
  const availableTargets = reactExports.useMemo(() => {
    return (validationSets ?? []).filter((uri) => uri !== sourceUri);
  }, [validationSets, sourceUri]);
  const { data: targetCases } = useValidationCases(targetUri ?? skipToken);
  const targetSplits = reactExports.useMemo(() => {
    return extractUniqueSplits(targetCases ?? []);
  }, [targetCases]);
  const createSetMutation = useCreateValidationSet();
  const deleteCasesMutation = useBulkDeleteValidationCases(sourceUri);
  const handleHide = reactExports.useCallback(() => {
    if (isProcessing) {
      return;
    }
    setTargetUri(void 0);
    setTargetSplit(KEEP_ORIGINAL_SPLIT);
    setShowNewSetInput(false);
    setNewSetName("");
    setError(null);
    onHide();
  }, [onHide, isProcessing]);
  const handleTargetChange = (e) => {
    const value = e.target.value;
    if (value === "__new__") {
      setShowNewSetInput(true);
      setNewSetName("");
      setTargetUri(void 0);
    } else {
      setShowNewSetInput(false);
      setTargetUri(value || void 0);
    }
    setTargetSplit(KEEP_ORIGINAL_SPLIT);
    setError(null);
  };
  const handleNewSetNameInput = (e) => {
    setNewSetName(e.target.value);
    setError(null);
  };
  const handleSplitChange = (e) => {
    const value = e.target.value;
    setTargetSplit(value);
  };
  const handleCreateNewSet = async () => {
    const trimmedName = newSetName.trim();
    const validation = isValidFilename(trimmedName);
    if (!validation.isValid) {
      setError(validation.error ?? "Invalid filename");
      return void 0;
    }
    const newUri = generateNewSetUri(sourceUri, trimmedName);
    if (newUri === sourceUri) {
      setError("Cannot copy/move to the same validation set");
      return void 0;
    }
    if (validationSets?.includes(newUri)) {
      setError("A validation set with this name already exists");
      return void 0;
    }
    try {
      await createSetMutation.mutateAsync({ path: newUri, cases: [] });
      return newUri;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create validation set";
      setError(message);
      return void 0;
    }
  };
  const getSplitForCase = (originalCase) => {
    if (targetSplit === KEEP_ORIGINAL_SPLIT) {
      return originalCase.split ?? null;
    }
    if (targetSplit === NO_SPLIT) {
      return null;
    }
    return targetSplit;
  };
  const copyCasesToTarget = async (destUri) => {
    const results = await Promise.allSettled(
      selectedCases.map(
        (c) => api.upsertValidationCase(destUri, getCaseKey(c.id), {
          id: c.id,
          target: c.target,
          labels: c.labels,
          split: getSplitForCase(c),
          predicate: c.predicate ?? void 0
        })
      )
    );
    const succeeded = results.filter((r) => r.status === "fulfilled").length;
    const failed = results.filter((r) => r.status === "rejected").length;
    if (failed > 0 && succeeded === 0) {
      setError(`All ${failed} copy operations failed`);
      return false;
    }
    if (failed > 0) {
      setError(
        `Warning: ${failed} of ${selectedIds.length} cases failed to copy. ${succeeded} succeeded.`
      );
    }
    return true;
  };
  const handleSubmit = async () => {
    setIsProcessing(true);
    setError(null);
    try {
      let finalTargetUri = targetUri;
      if (showNewSetInput) {
        finalTargetUri = await handleCreateNewSet();
        if (!finalTargetUri) {
          setIsProcessing(false);
          return;
        }
      }
      if (!finalTargetUri) {
        setError("Please select a target validation set");
        setIsProcessing(false);
        return;
      }
      const copySuccess = await copyCasesToTarget(finalTargetUri);
      if (!copySuccess) {
        setIsProcessing(false);
        return;
      }
      void queryClient.invalidateQueries({
        queryKey: validationQueryKeys.cases(finalTargetUri)
      });
      if (mode === "move") {
        try {
          await deleteCasesMutation.mutateAsync(selectedIds);
        } catch (err) {
          const message = err instanceof Error ? err.message : "Unknown error";
          setError(
            `Cases copied successfully, but failed to delete from source: ${message}`
          );
          setIsProcessing(false);
          return;
        }
      }
      onSuccess();
      handleHide();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Operation failed";
      setError(message);
    } finally {
      setIsProcessing(false);
    }
  };
  const title2 = mode === "copy" ? "Copy Cases" : "Move Cases";
  const actionLabel = mode === "copy" ? "Copy" : "Move";
  const processingLabel = mode === "copy" ? "Copying..." : "Moving...";
  const canSubmit = !isProcessing && (targetUri || showNewSetInput && newSetName.trim());
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    Modal,
    {
      show,
      onHide: handleHide,
      onSubmit: canSubmit ? () => void handleSubmit() : void 0,
      title: title2,
      footer: /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { secondary: true, onClick: handleHide, disabled: isProcessing, children: "Cancel" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          VscodeButton,
          {
            onClick: () => void handleSubmit(),
            disabled: !canSubmit,
            children: isProcessing ? processingLabel : actionLabel
          }
        )
      ] }),
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$4.modalContent, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { children: [
          actionLabel,
          " ",
          selectedIds.length,
          " ",
          selectedIds.length === 1 ? "case" : "cases",
          " to another validation set."
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$4.fieldGroup, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: styles$4.label, children: "Target validation set:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            VscodeSingleSelect,
            {
              value: showNewSetInput ? "__new__" : targetUri ?? "",
              onChange: handleTargetChange,
              disabled: isProcessing,
              className: styles$4.select,
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "", children: "Select a validation set..." }),
                availableTargets.map((uri) => /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: uri, children: getFilenameFromUri(uri) }, uri)),
                /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "__new__", children: "Create new set..." })
              ]
            }
          )
        ] }),
        showNewSetInput && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$4.fieldGroup, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: styles$4.label, children: "New set name:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeTextfield,
            {
              value: newSetName,
              onInput: handleNewSetNameInput,
              placeholder: "Enter name (without extension)",
              disabled: isProcessing,
              "data-autofocus": true,
              className: styles$4.textInput
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$4.hint, children: [
            "Will be created as ",
            newSetName.trim() || "name",
            ".csv"
          ] })
        ] }),
        (targetUri || showNewSetInput && newSetName.trim()) && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$4.fieldGroup, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: styles$4.label, children: "Split assignment:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            VscodeSingleSelect,
            {
              value: targetSplit,
              onChange: handleSplitChange,
              disabled: isProcessing,
              className: styles$4.select,
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: KEEP_ORIGINAL_SPLIT, children: "Keep original splits" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: NO_SPLIT, children: "No split" }),
                targetSplits.map((split) => /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: split, children: split }, split))
              ]
            }
          )
        ] }),
        error2 && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: styles$4.error, children: error2 })
      ] })
    }
  );
};
const card = "_card_1lurf_1";
const selected = "_selected_1lurf_21";
const checkbox = "_checkbox_1lurf_25";
const transcriptCell = "_transcriptCell_1lurf_32";
const idLink = "_idLink_1lurf_39";
const labelsCell = "_labelsCell_1lurf_62";
const targetCell = "_targetCell_1lurf_70";
const target = "_target_1lurf_70";
const targetTrue = "_targetTrue_1lurf_82";
const targetFalse = "_targetFalse_1lurf_95";
const splitSelect$1 = "_splitSelect_1lurf_109";
const actions = "_actions_1lurf_122";
const actionButton = "_actionButton_1lurf_130";
const detailsRow = "_detailsRow_1lurf_159";
const notFoundRow = "_notFoundRow_1lurf_167";
const modalContent$2 = "_modalContent_1lurf_182";
const warning$1 = "_warning_1lurf_192";
const modalButton = "_modalButton_1lurf_197";
const modalButtonPrimary = "_modalButtonPrimary_1lurf_211";
const styles$3 = {
  card,
  selected,
  checkbox,
  transcriptCell,
  idLink,
  labelsCell,
  targetCell,
  target,
  targetTrue,
  targetFalse,
  splitSelect: splitSelect$1,
  actions,
  actionButton,
  detailsRow,
  notFoundRow,
  modalContent: modalContent$2,
  warning: warning$1,
  modalButton,
  modalButtonPrimary
};
const formatTarget = (target2) => {
  if (typeof target2 === "string") {
    return target2;
  }
  if (typeof target2 === "number") {
    return String(target2);
  }
  if (Array.isArray(target2)) {
    return target2.map(String).join(", ");
  }
  if (target2 === null || target2 === void 0) {
    return "";
  }
  return JSON.stringify(target2);
};
const renderTarget = (target2, predicate) => {
  const showPredicate = predicate && predicate !== "eq";
  const predicatePrefix = showPredicate ? `(${predicate}) ` : "";
  if (typeof target2 === "boolean") {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      predicatePrefix,
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: target2 ? styles$3.targetTrue : styles$3.targetFalse, children: String(target2) })
    ] });
  }
  const targetText = formatTarget(target2);
  if (!targetText) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$3.target, children: [
    predicatePrefix,
    targetText
  ] });
};
const formatScore = (score) => {
  if (score === null || score === void 0) {
    return "—";
  }
  if (typeof score === "number") {
    return String(score);
  }
  if (typeof score === "boolean") {
    return score ? "1" : "0";
  }
  if (typeof score === "string") {
    return score;
  }
  return JSON.stringify(score);
};
const formatLabels = (labels) => {
  if (!labels) return "";
  const entries = Object.entries(labels);
  entries.sort(([, a], [, b]) => (b ? 1 : 0) - (a ? 1 : 0));
  return entries.map(([k, v]) => `${k}: ${v}`).join(", ");
};
const buildTranscriptDetails = (transcript) => {
  const parts = [];
  if (transcript.task_set || transcript.task_id) {
    let taskPart = "";
    if (transcript.task_set && transcript.task_id) {
      taskPart = `${transcript.task_set}/${transcript.task_id}`;
    } else if (transcript.task_set) {
      taskPart = transcript.task_set;
    } else if (transcript.task_id) {
      taskPart = transcript.task_id;
    }
    if (transcript.task_repeat !== null && transcript.task_repeat !== void 0) {
      taskPart += ` (${transcript.task_repeat})`;
    }
    parts.push(taskPart);
  }
  if (transcript.agent) {
    parts.push(transcript.agent);
  }
  if (transcript.model) {
    parts.push(transcript.model);
  }
  const scoreStr = formatScore(transcript.score);
  parts.push(`score: ${scoreStr}`);
  return parts.join(" - ");
};
const ValidationCaseCard = ({
  validationCase,
  transcript,
  transcriptsDir,
  validationSetUri,
  isSelected,
  onSelectionChange,
  existingSplits,
  onSplitChange,
  onDelete,
  isUpdating,
  isDeleting,
  showLabels,
  showTarget,
  gridStyle
}) => {
  const navigate = useNavigate();
  const { id, target: target2, split, predicate, labels } = validationCase;
  const [showDeleteModal, setShowDeleteModal] = reactExports.useState(false);
  const idText = getIdText(id);
  const targetElement = renderTarget(target2, predicate);
  const handleNavigateToTranscript = () => {
    const singleId = Array.isArray(id) ? id[0] : id;
    if (transcriptsDir && singleId) {
      void navigate(
        transcriptRoute(transcriptsDir, singleId, void 0, validationSetUri)
      );
    }
  };
  const handleCheckboxChange = (e) => {
    const checked = e.target.checked;
    onSelectionChange(checked);
  };
  const handleRowClick = (e) => {
    const target22 = e.target;
    if (target22.closest("button") || target22.closest("vscode-checkbox") || target22.closest("vscode-single-select")) {
      return;
    }
    onSelectionChange(!isSelected);
  };
  const handleDelete = () => {
    onDelete?.();
    setShowDeleteModal(false);
  };
  const labelsText = formatLabels(labels);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: `${styles$3.card} ${isSelected ? styles$3.selected : ""}`,
      style: gridStyle,
      onClick: handleRowClick,
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$3.checkbox, children: /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeCheckbox, { checked: isSelected, onChange: handleCheckboxChange }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.transcriptCell, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              className: styles$3.idLink,
              onClick: handleNavigateToTranscript,
              disabled: !transcriptsDir,
              title: transcriptsDir ? "View transcript" : "No transcripts directory",
              children: [
                "Transcript ID: ",
                idText
              ]
            }
          ),
          transcript ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$3.detailsRow, children: buildTranscriptDetails(transcript) }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.notFoundRow, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.logging.warning }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "Not found in project transcripts" })
          ] })
        ] }),
        showLabels && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$3.labelsCell, children: labelsText }),
        showTarget && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$3.targetCell, children: targetElement }),
        onSplitChange ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          ValidationSplitSelector,
          {
            value: split ?? null,
            existingSplits,
            onChange: onSplitChange,
            disabled: isUpdating,
            className: styles$3.splitSelect,
            noSplitLabel: "(No split)"
          }
        ) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$3.target, children: split ?? "—" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.actions, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              className: styles$3.actionButton,
              onClick: handleNavigateToTranscript,
              disabled: !transcriptsDir,
              title: "View transcript",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.edit })
            }
          ),
          onDelete && /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              className: styles$3.actionButton,
              onClick: () => setShowDeleteModal(true),
              disabled: isDeleting,
              title: "Delete case",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.trash })
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          Modal,
          {
            show: showDeleteModal,
            onHide: () => setShowDeleteModal(false),
            onSubmit: handleDelete,
            title: "Delete Case",
            footer: /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  className: styles$3.modalButton,
                  onClick: () => setShowDeleteModal(false),
                  children: "Cancel"
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  className: `${styles$3.modalButton} ${styles$3.modalButtonPrimary}`,
                  onClick: handleDelete,
                  disabled: isDeleting,
                  children: isDeleting ? "Deleting..." : "Delete"
                }
              )
            ] }),
            children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$3.modalContent, children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "Are you sure you want to delete this validation case?" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: styles$3.warning, children: "This action cannot be undone." })
            ] })
          }
        )
      ]
    }
  );
};
const container$2 = "_container_1xvfl_1";
const gridContainer = "_gridContainer_1xvfl_11";
const header = "_header_1xvfl_20";
const headerCheckbox = "_headerCheckbox_1xvfl_41";
const headerTranscript = "_headerTranscript_1xvfl_48";
const bulkActions = "_bulkActions_1xvfl_55";
const selectedCount = "_selectedCount_1xvfl_62";
const bulkButton = "_bulkButton_1xvfl_70";
const buttonText = "_buttonText_1xvfl_89";
const headerLabels = "_headerLabels_1xvfl_102";
const headerTarget = "_headerTarget_1xvfl_108";
const headerSplit = "_headerSplit_1xvfl_114";
const headerActions$1 = "_headerActions_1xvfl_118";
const list = "_list_1xvfl_125";
const emptyState$1 = "_emptyState_1xvfl_134";
const modalContent$1 = "_modalContent_1xvfl_141";
const splitSelector = "_splitSelector_1xvfl_152";
const warning = "_warning_1xvfl_162";
const styles$2 = {
  container: container$2,
  gridContainer,
  header,
  headerCheckbox,
  headerTranscript,
  bulkActions,
  selectedCount,
  bulkButton,
  buttonText,
  headerLabels,
  headerTarget,
  headerSplit,
  headerActions: headerActions$1,
  list,
  emptyState: emptyState$1,
  modalContent: modalContent$1,
  splitSelector,
  warning
};
const ValidationCasesList = ({
  cases,
  transcriptsDir,
  sourceUri,
  onBulkSplitChange,
  onBulkDelete,
  onSingleSplitChange,
  onSingleDelete,
  isUpdating,
  isDeleting
}) => {
  const selection = useStore((state) => state.validationCaseSelection);
  const setSelection = useStore((state) => state.setValidationCaseSelection);
  const toggleSelection = useStore(
    (state) => state.toggleValidationCaseSelection
  );
  const splitFilter2 = useStore((state) => state.validationSplitFilter);
  const searchText = useStore((state) => state.validationSearchText);
  const transcriptIds = reactExports.useMemo(() => {
    return cases.map((c) => Array.isArray(c.id) ? c.id[0] : c.id).filter((id) => id !== void 0);
  }, [cases]);
  const existingSplits = reactExports.useMemo(() => extractUniqueSplits(cases), [cases]);
  const hasLabels = reactExports.useMemo(
    () => cases.some((c) => c.labels !== null && c.labels !== void 0),
    [cases]
  );
  const hasTargets = reactExports.useMemo(
    () => cases.some((c) => c.target !== null && c.target !== void 0),
    [cases]
  );
  const gridColumns = reactExports.useMemo(() => {
    const cols = ["20px", "1fr"];
    if (hasLabels) cols.push("auto");
    if (hasTargets) cols.push("auto");
    cols.push("90px", "auto");
    return cols.join(" ");
  }, [hasLabels, hasTargets]);
  const gridStyle = { gridTemplateColumns: gridColumns };
  const {
    data: transcriptMap,
    sourceIds,
    loading: transcriptsLoading
  } = useTranscriptsByIds(transcriptsDir, transcriptIds);
  const getTranscriptSafely = reactExports.useCallback(
    (transcriptId) => {
      if (!transcriptId) return void 0;
      if (!transcriptMap) return void 0;
      if (sourceIds && !sourceIds.has(transcriptId)) {
        console.warn(
          `[ValidationCasesList] Stale transcript lookup detected: ID "${transcriptId}" not in sourceIds. sourceIds: [${[...sourceIds].join(", ")}], requested: [${transcriptIds.join(", ")}]`
        );
        return void 0;
      }
      return transcriptMap.get(transcriptId);
    },
    [transcriptMap, sourceIds, transcriptIds]
  );
  const filteredCases = reactExports.useMemo(() => {
    const filtered = cases.filter((c) => {
      if (splitFilter2 && c.split !== splitFilter2) {
        return false;
      }
      if (searchText) {
        const search = searchText.toLowerCase();
        const transcriptId = Array.isArray(c.id) ? c.id[0] : c.id;
        const transcript = getTranscriptSafely(transcriptId);
        const idText = getIdText(c.id).toLowerCase();
        if (idText.includes(search)) return true;
        if (transcript) {
          if (transcript.task_set?.toLowerCase().includes(search)) return true;
          if (transcript.task_id?.toLowerCase().includes(search)) return true;
          if (transcript.model?.toLowerCase().includes(search)) return true;
          if (transcript.agent?.toLowerCase().includes(search)) return true;
        }
        return false;
      }
      return true;
    });
    return filtered.sort((a, b) => {
      const splitA = a.split;
      const splitB = b.split;
      if (!splitA && splitB) return -1;
      if (splitA && !splitB) return 1;
      if (!splitA && !splitB) return 0;
      return splitA.localeCompare(splitB);
    });
  }, [cases, splitFilter2, searchText, getTranscriptSafely]);
  const filteredCaseKeys = reactExports.useMemo(() => {
    return filteredCases.map((c) => getCaseKey(c.id));
  }, [filteredCases]);
  const selectedIds = reactExports.useMemo(() => {
    return Object.entries(selection).filter(([, selected2]) => selected2).map(([id]) => id);
  }, [selection]);
  const selectedCases = reactExports.useMemo(() => {
    return filteredCases.filter((c) => selection[getCaseKey(c.id)]);
  }, [filteredCases, selection]);
  const allSelected = filteredCaseKeys.length > 0 && filteredCaseKeys.every((key) => selection[key]);
  const someSelected = filteredCaseKeys.some((key) => selection[key]) && !allSelected;
  const handleSelectAllChange = () => {
    if (allSelected) {
      const newSelection = { ...selection };
      filteredCaseKeys.forEach((key) => {
        delete newSelection[key];
      });
      setSelection(newSelection);
    } else {
      const newSelection = { ...selection };
      filteredCaseKeys.forEach((key) => {
        newSelection[key] = true;
      });
      setSelection(newSelection);
    }
  };
  const handleBulkSplitChange = (ids, split) => {
    onBulkSplitChange?.(ids, split);
    setSelection({});
  };
  const handleBulkDelete = (ids) => {
    onBulkDelete?.(ids);
    setSelection({});
  };
  const [activeModal, setActiveModal] = reactExports.useState("none");
  const [bulkSplitValue, setBulkSplitValue] = reactExports.useState(null);
  const handleAssignSplit = () => {
    handleBulkSplitChange(selectedIds, bulkSplitValue);
    setActiveModal("none");
    setBulkSplitValue(null);
  };
  const handleConfirmDelete = () => {
    handleBulkDelete(selectedIds);
    setActiveModal("none");
  };
  const closeModal = () => setActiveModal("none");
  const hasSelection = selectedIds.length > 0;
  const hasBulkActions = onBulkSplitChange && onBulkDelete;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$2.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$2.gridContainer, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$2.header, style: gridStyle, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.headerCheckbox, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          VscodeCheckbox,
          {
            checked: allSelected,
            indeterminate: someSelected,
            onChange: handleSelectAllChange,
            title: allSelected ? "Deselect all" : "Select all"
          }
        ) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$2.headerTranscript, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "Transcript" }),
          hasSelection && hasBulkActions && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$2.bulkActions, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: styles$2.selectedCount, children: [
              selectedIds.length,
              " selected"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              VscodeButton,
              {
                onClick: () => setActiveModal("split"),
                disabled: isUpdating || isDeleting,
                className: styles$2.bulkButton,
                title: "Assign Split",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.fork }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$2.buttonText, children: "Assign Split" })
                ]
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              VscodeButton,
              {
                onClick: () => setActiveModal("copy"),
                disabled: isUpdating || isDeleting,
                className: styles$2.bulkButton,
                title: "Copy",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.copy }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$2.buttonText, children: "Copy" })
                ]
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              VscodeButton,
              {
                onClick: () => setActiveModal("move"),
                disabled: isUpdating || isDeleting,
                className: styles$2.bulkButton,
                title: "Move",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.move }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$2.buttonText, children: "Move" })
                ]
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              VscodeButton,
              {
                onClick: () => setActiveModal("delete"),
                disabled: isUpdating || isDeleting,
                className: styles$2.bulkButton,
                title: "Delete",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.trash }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$2.buttonText, children: "Delete" })
                ]
              }
            )
          ] })
        ] }),
        hasLabels && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.headerLabels, children: "Labels" }),
        hasTargets && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.headerTarget, children: "Target" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.headerSplit, children: "Split" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.headerActions, children: "Actions" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.list, children: transcriptsLoading ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.emptyState, children: "Loading transcript details..." }) : filteredCases.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.emptyState, children: cases.length === 0 ? "No validation cases in this set." : "No cases match the current filters." }) : filteredCases.map((c) => {
        const caseKey = getCaseKey(c.id);
        const transcriptId = Array.isArray(c.id) ? c.id[0] : c.id;
        const transcript = getTranscriptSafely(transcriptId);
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ValidationCaseCard,
          {
            validationCase: c,
            transcript,
            transcriptsDir,
            validationSetUri: sourceUri,
            isSelected: selection[caseKey] ?? false,
            onSelectionChange: () => toggleSelection(caseKey),
            existingSplits,
            onSplitChange: onSingleSplitChange ? (split) => onSingleSplitChange(caseKey, split) : void 0,
            onDelete: onSingleDelete ? () => onSingleDelete(caseKey) : void 0,
            isUpdating,
            isDeleting,
            showLabels: hasLabels,
            showTarget: hasTargets,
            gridStyle
          },
          caseKey
        );
      }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Modal,
      {
        show: activeModal === "split",
        onHide: closeModal,
        title: "Assign Split",
        footer: /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { secondary: true, onClick: closeModal, children: "Cancel" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { onClick: handleAssignSplit, disabled: isUpdating, children: isUpdating ? "Assigning..." : "Assign" })
        ] }),
        children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$2.modalContent, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { children: [
            "Assign a split to ",
            selectedIds.length,
            " selected",
            " ",
            selectedIds.length === 1 ? "case" : "cases",
            "."
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$2.splitSelector, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            ValidationSplitSelector,
            {
              value: bulkSplitValue,
              existingSplits,
              onChange: setBulkSplitValue,
              noSplitLabel: "Remove split"
            }
          ) })
        ] })
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Modal,
      {
        show: activeModal === "delete",
        onHide: closeModal,
        title: "Confirm Delete",
        footer: /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { secondary: true, onClick: closeModal, children: "Cancel" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { onClick: handleConfirmDelete, disabled: isDeleting, children: isDeleting ? "Deleting..." : "Delete" })
        ] }),
        children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$2.modalContent, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { children: [
            "Are you sure you want to delete ",
            selectedIds.length,
            " ",
            selectedIds.length === 1 ? "case" : "cases",
            "?"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: styles$2.warning, children: "This action cannot be undone." })
        ] })
      }
    ),
    sourceUri && /* @__PURE__ */ jsxRuntimeExports.jsx(
      CopyMoveCasesModal,
      {
        show: activeModal === "copy",
        mode: "copy",
        sourceUri,
        selectedIds,
        selectedCases,
        onHide: closeModal,
        onSuccess: () => setSelection({})
      }
    ),
    sourceUri && /* @__PURE__ */ jsxRuntimeExports.jsx(
      CopyMoveCasesModal,
      {
        show: activeModal === "move",
        mode: "move",
        sourceUri,
        selectedIds,
        selectedCases,
        onHide: closeModal,
        onSuccess: () => setSelection({})
      }
    )
  ] });
};
const container$1 = "_container_1ph4q_1";
const separator = "_separator_1ph4q_10";
const styles$1 = {
  container: container$1,
  separator
};
const ValidationSummary = ({ cases }) => {
  const stats = reactExports.useMemo(() => {
    const splitCounts = /* @__PURE__ */ new Map();
    for (const c of cases) {
      if (c.split) {
        splitCounts.set(c.split, (splitCounts.get(c.split) ?? 0) + 1);
      }
    }
    const sortedSplits = Array.from(splitCounts.entries()).sort(
      ([a], [b]) => a.localeCompare(b)
    );
    return {
      totalCount: cases.length,
      splits: sortedSplits,
      hasSplits: splitCounts.size > 0
    };
  }, [cases]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$1.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
      stats.totalCount,
      " cases"
    ] }),
    stats.hasSplits && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles$1.separator, children: "|" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
        "Splits:",
        " ",
        stats.splits.map(([split, count], i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
          split,
          " (",
          count,
          ")",
          i < stats.splits.length - 1 && ", "
        ] }, split))
      ] })
    ] })
  ] });
};
const container = "_container_12me1_1";
const headerRow = "_headerRow_12me1_8";
const title = "_title_12me1_16";
const spacer = "_spacer_12me1_24";
const headerActions = "_headerActions_12me1_28";
const filterControls = "_filterControls_12me1_35";
const searchInput = "_searchInput_12me1_41";
const splitFilter = "_splitFilter_12me1_50";
const filterLabel = "_filterLabel_12me1_56";
const splitSelect = "_splitSelect_12me1_61";
const iconButton = "_iconButton_12me1_67";
const modalContent = "_modalContent_12me1_94";
const renameInput = "_renameInput_12me1_109";
const content = "_content_12me1_113";
const loading = "_loading_12me1_129";
const error = "_error_12me1_135";
const emptyState = "_emptyState_12me1_140";
const summaryWrapper = "_summaryWrapper_12me1_155";
const styles = {
  container,
  headerRow,
  title,
  spacer,
  headerActions,
  filterControls,
  searchInput,
  splitFilter,
  filterLabel,
  splitSelect,
  iconButton,
  modalContent,
  renameInput,
  content,
  loading,
  error,
  emptyState,
  summaryWrapper
};
const ValidationPanel = () => {
  useDocumentTitle("Validation");
  const config = useAppConfig();
  const transcriptsDir = config.transcripts?.dir ?? void 0;
  const selectedUri = useStore((state) => state.selectedValidationSetUri);
  const setSelectedUri = useStore((state) => state.setSelectedValidationSetUri);
  const clearValidationState = useStore((state) => state.clearValidationState);
  const splitFilter2 = useStore((state) => state.validationSplitFilter);
  const setSplitFilter = useStore((state) => state.setValidationSplitFilter);
  const searchText = useStore((state) => state.validationSearchText);
  const setSearchText = useStore((state) => state.setValidationSearchText);
  const [showDeleteModal, setShowDeleteModal] = reactExports.useState(false);
  const [showRenameModal, setShowRenameModal] = reactExports.useState(false);
  const [newName, setNewName] = reactExports.useState("");
  const {
    data: validationSets,
    loading: setsLoading,
    error: setsError
  } = useValidationSets();
  const {
    data: cases,
    loading: casesLoading,
    error: casesError
  } = useValidationCases(selectedUri ?? skipToken);
  reactExports.useEffect(() => {
    if (!selectedUri && validationSets && validationSets.length > 0) {
      setSelectedUri(validationSets[0]);
    }
  }, [selectedUri, validationSets, setSelectedUri]);
  const updateMutation = useUpdateValidationCase(selectedUri ?? "");
  const deleteCasesMutation = useBulkDeleteValidationCases(selectedUri ?? "");
  const deleteSetMutation = useDeleteValidationSet();
  const renameSetMutation = useRenameValidationSet();
  const handleSelectSet = (uri) => {
    clearValidationState();
    setSelectedUri(uri);
  };
  const handleBulkSplitChange = reactExports.useCallback(
    (ids, split) => {
      if (!selectedUri || !cases) return;
      const caseMap = new Map(cases.map((c) => [getCaseKey(c.id), c]));
      const updateCases = async () => {
        const results = await Promise.allSettled(
          ids.map((id) => {
            const existingCase = caseMap.get(id);
            if (!existingCase) return Promise.resolve();
            return updateMutation.mutateAsync({
              caseId: id,
              data: {
                ...existingCase,
                split
              }
            });
          })
        );
        const failed = results.filter((r) => r.status === "rejected").length;
        if (failed > 0) {
          console.error(
            `Bulk split update: ${failed} of ${ids.length} updates failed`
          );
        }
      };
      void updateCases();
    },
    [selectedUri, cases, updateMutation]
  );
  const handleBulkDelete = reactExports.useCallback(
    (ids) => {
      if (!selectedUri) return;
      deleteCasesMutation.mutate(ids);
    },
    [selectedUri, deleteCasesMutation]
  );
  const handleSingleSplitChange = reactExports.useCallback(
    (caseId, split) => {
      if (!selectedUri || !cases) return;
      const caseMap = new Map(cases.map((c) => [getCaseKey(c.id), c]));
      const existingCase = caseMap.get(caseId);
      if (!existingCase) return;
      updateMutation.mutate({
        caseId,
        data: {
          ...existingCase,
          split
        }
      });
    },
    [selectedUri, cases, updateMutation]
  );
  const handleSingleDelete = reactExports.useCallback(
    (caseId) => {
      if (!selectedUri) return;
      deleteCasesMutation.mutate([caseId]);
    },
    [selectedUri, deleteCasesMutation]
  );
  const handleDeleteSet = () => {
    if (!selectedUri) return;
    deleteSetMutation.mutate(selectedUri, {
      onSuccess: () => {
        setShowDeleteModal(false);
        clearValidationState();
        setSelectedUri(void 0);
      }
    });
  };
  const handleOpenRename = () => {
    if (selectedUri) {
      const currentName = getFilenameFromUri(selectedUri, true);
      setNewName(currentName);
      setShowRenameModal(true);
    }
  };
  const handleRenameSet = () => {
    if (!selectedUri || !newName.trim()) return;
    renameSetMutation.mutate(
      { uri: selectedUri, newName: newName.trim() },
      {
        onSuccess: (newUri) => {
          setShowRenameModal(false);
          setNewName("");
          setSelectedUri(newUri);
        }
      }
    );
  };
  const handleNameInput = (e) => {
    const value = e.target.value;
    setNewName(value);
  };
  const currentFilename = selectedUri ? getFilenameFromUri(selectedUri) : "";
  const splits = reactExports.useMemo(() => extractUniqueSplits(cases ?? []), [cases]);
  if (setsLoading) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.container });
  }
  const hasNoValidationSets = !setsError && validationSets?.length === 0;
  if (hasNoValidationSets) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.container, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      NonIdealState,
      {
        icon: ApplicationIcons.validation,
        title: "No Validation Sets in Project",
        description: "Validation sets enable you to check scanner results against labeled cases.",
        action: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "a",
          {
            href: "https://meridianlabs-ai.github.io/inspect_scout/validation.html",
            target: "_blank",
            rel: "noopener noreferrer",
            children: "Using Scout Validation"
          }
        )
      }
    ) });
  }
  const handleSplitFilterChange = (e) => {
    const value = e.target.value;
    setSplitFilter(value || void 0);
  };
  const handleSearchChange = (e) => {
    setSearchText(e.target.value || void 0);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.container, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.headerRow, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: styles.title, children: "Validation Set:" }),
      setsError ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.error, children: [
        "Error loading validation sets: ",
        setsError.message
      ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx(
        ValidationSetSelector,
        {
          validationSets: validationSets ?? [],
          selectedUri,
          onSelect: handleSelectSet,
          autoSize: true,
          appConfig: config
        }
      ),
      selectedUri && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.headerActions, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: styles.iconButton,
            onClick: handleOpenRename,
            title: "Rename validation set",
            disabled: renameSetMutation.isPending,
            children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.rename })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            className: styles.iconButton,
            onClick: () => setShowDeleteModal(true),
            title: "Delete validation set",
            disabled: deleteSetMutation.isPending,
            children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.trash })
          }
        )
      ] }),
      cases && cases.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.summaryWrapper, children: /* @__PURE__ */ jsxRuntimeExports.jsx(ValidationSummary, { cases }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.spacer }),
      selectedUri && cases && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.filterControls, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          TextInput,
          {
            icon: ApplicationIcons.search,
            value: searchText ?? "",
            onChange: handleSearchChange,
            placeholder: "Search...",
            className: styles.searchInput
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.splitFilter, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: styles.filterLabel, children: "Split:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            VscodeSingleSelect,
            {
              value: splitFilter2 ?? "",
              onChange: handleSplitFilterChange,
              className: styles.splitSelect,
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: "", children: "All" }),
                splits.map((split) => /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeOption, { value: split, children: split }, split))
              ]
            }
          )
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.content, children: [
      selectedUri && /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: casesLoading ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.loading, children: "Loading cases..." }) : casesError ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.error, children: [
        "Error loading cases: ",
        casesError.message
      ] }) : cases ? /* @__PURE__ */ jsxRuntimeExports.jsx(
        ValidationCasesList,
        {
          cases,
          transcriptsDir,
          sourceUri: selectedUri,
          onBulkSplitChange: handleBulkSplitChange,
          onBulkDelete: handleBulkDelete,
          onSingleSplitChange: handleSingleSplitChange,
          onSingleDelete: handleSingleDelete,
          isUpdating: updateMutation.isPending,
          isDeleting: deleteCasesMutation.isPending
        }
      ) : null }),
      !selectedUri && !setsLoading && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.emptyState, children: "Select a validation set to view its cases." })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Modal,
      {
        show: showDeleteModal,
        onHide: () => setShowDeleteModal(false),
        onSubmit: deleteSetMutation.isPending ? void 0 : handleDeleteSet,
        title: "Move to Trash",
        footer: /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { secondary: true, onClick: () => setShowDeleteModal(false), children: "Cancel" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeButton,
            {
              onClick: handleDeleteSet,
              disabled: deleteSetMutation.isPending,
              children: deleteSetMutation.isPending ? "Moving..." : "Move to Trash"
            }
          )
        ] }),
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.modalContent, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { children: [
          "Are you sure you want to move ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("strong", { children: currentFilename }),
          " to the trash?"
        ] }) })
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Modal,
      {
        show: showRenameModal,
        onHide: () => setShowRenameModal(false),
        onSubmit: renameSetMutation.isPending || !newName.trim() ? void 0 : handleRenameSet,
        title: "Rename Validation Set",
        footer: /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(VscodeButton, { secondary: true, onClick: () => setShowRenameModal(false), children: "Cancel" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeButton,
            {
              onClick: handleRenameSet,
              disabled: renameSetMutation.isPending || !newName.trim(),
              children: renameSetMutation.isPending ? "Renaming..." : "Rename"
            }
          )
        ] }),
        children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.modalContent, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "Enter a new name for the validation set:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            VscodeTextfield,
            {
              value: newName,
              onInput: handleNameInput,
              placeholder: "New name",
              className: styles.renameInput,
              "data-autofocus": true
            }
          )
        ] })
      }
    )
  ] });
};
export {
  ValidationPanel
};
//# sourceMappingURL=ValidationPanel.js.map
