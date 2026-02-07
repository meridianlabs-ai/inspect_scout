import { j as jsxRuntimeExports, g as clsx, e as ApplicationIcons } from "./index.js";
import { d as formatNumber } from "./ToolButton.js";
const footer = "_footer_1ykeg_1";
const spinnerContainer = "_spinnerContainer_1ykeg_11";
const spinner = "_spinner_1ykeg_11";
const label = "_label_1ykeg_25";
const right = "_right_1ykeg_30";
const left = "_left_1ykeg_39";
const center = "_center_1ykeg_48";
const styles$1 = {
  footer,
  spinnerContainer,
  spinner,
  label,
  right,
  left,
  center
};
const pager = "_pager_jzegk_1";
const item = "_item_jzegk_11";
const styles = {
  pager,
  item
};
const Pager = ({
  itemCount,
  page,
  setPage,
  itemsPerPage = 20
}) => {
  const pageCount = Math.ceil(itemCount / itemsPerPage);
  if (pageCount <= 1) {
    return null;
  }
  const currentPage = page || 0;
  const generatePaginationSegments = () => {
    const segments2 = [];
    if (pageCount <= 5) {
      for (let i = 0; i < pageCount; i++) {
        segments2.push({ type: "page", page: i, key: `page-${i}` });
      }
    } else {
      segments2.push({ type: "page", page: 0, key: "page-0" });
      const startPage = Math.max(1, currentPage - 1);
      const endPage = Math.min(pageCount - 2, currentPage + 1);
      if (startPage > 1) {
        segments2.push({ type: "ellipsis", key: "ellipsis-start" });
      }
      for (let i = startPage; i <= endPage; i++) {
        segments2.push({ type: "page", page: i, key: `page-${i}` });
      }
      if (endPage < pageCount - 2) {
        segments2.push({ type: "ellipsis", key: "ellipsis-end" });
      }
      segments2.push({
        type: "page",
        page: pageCount - 1,
        key: `page-${pageCount - 1}`
      });
    }
    return segments2;
  };
  const segments = generatePaginationSegments();
  return /* @__PURE__ */ jsxRuntimeExports.jsx("nav", { "aria-label": "Log Pagination", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("ul", { className: clsx("pagination", styles.pager), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("li", { className: clsx(currentPage === 0 ? "disabled" : "", styles.item), children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      "a",
      {
        className: clsx("page-link"),
        onClick: () => {
          if (currentPage > 0 && setPage) {
            setPage(currentPage - 1);
          }
        },
        children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(ApplicationIcons.navbar.back) })
      }
    ) }),
    segments.map((segment) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      "li",
      {
        className: clsx(
          segment.type === "page" && segment.page === currentPage ? "active" : void 0,
          segment.type === "ellipsis" ? "disabled" : void 0,
          styles.item
        ),
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "a",
          {
            className: clsx("page-link"),
            onClick: () => {
              if (segment.type === "page" && segment.page !== void 0 && setPage) {
                setPage(segment.page);
              }
            },
            children: segment.type === "page" ? (segment.page || 0) + 1 : "..."
          }
        )
      },
      segment.key
    )),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "li",
      {
        className: clsx(
          currentPage + 1 >= pageCount ? "disabled" : "",
          styles.item
        ),
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "a",
          {
            className: clsx("page-link"),
            onClick: () => {
              if (currentPage < pageCount && setPage) {
                setPage(currentPage + 1);
              }
            },
            children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(ApplicationIcons.navbar.forward) })
          }
        )
      }
    )
  ] }) });
};
const Footer = ({
  id,
  className,
  itemCount = 0,
  paginated,
  filteredCount,
  left: left2,
  progressText,
  progressBar,
  page,
  setPage,
  itemsPerPage = -1,
  labels = {
    singular: "item",
    plural: "items"
  }
}) => {
  const effectiveItemCount = filteredCount ?? itemCount;
  const currentPage = page || 0;
  const pageItemCount = Math.min(
    itemsPerPage,
    effectiveItemCount - currentPage * itemsPerPage
  );
  const startItem = effectiveItemCount > 0 ? currentPage * itemsPerPage + 1 : 0;
  const endItem = startItem + pageItemCount - 1;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      id,
      className: clsx("text-size-smaller", styles$1.footer, className),
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$1.left), children: progressText ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$1.spinnerContainer), children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: clsx("spinner-border", styles$1.spinner),
              role: "status",
              children: /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: clsx("visually-hidden"), children: [
                progressText,
                "..."
              ] })
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx("text-style-secondary", styles$1.label), children: [
            progressText,
            "..."
          ] })
        ] }) : left2 }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$1.center), children: paginated && /* @__PURE__ */ jsxRuntimeExports.jsx(
          Pager,
          {
            itemCount: effectiveItemCount,
            itemsPerPage,
            page,
            setPage
          }
        ) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$1.right), children: progressBar ? progressBar : paginated ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: effectiveItemCount === 0 ? "" : filteredCount !== void 0 && filteredCount !== itemCount ? `${startItem} - ${endItem} / ${effectiveItemCount} (${itemCount} total)` : `${startItem} - ${endItem} / ${effectiveItemCount}` }) : effectiveItemCount === 1 ? `${formatNumber(effectiveItemCount)} ${labels.singular}` : `${formatNumber(effectiveItemCount)} ${labels.plural}` })
      ]
    }
  );
};
export {
  Footer as F
};
//# sourceMappingURL=Footer.js.map
