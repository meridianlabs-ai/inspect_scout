import { r as reactExports, h as reactDomExports, j as jsxRuntimeExports } from "./index.js";
const backdrop = "_backdrop_wrdr6_1";
const modal = "_modal_wrdr6_12";
const header = "_header_wrdr6_25";
const title = "_title_wrdr6_34";
const closeButton = "_closeButton_wrdr6_41";
const body = "_body_wrdr6_57";
const footer = "_footer_wrdr6_64";
const styles = {
  backdrop,
  modal,
  header,
  title,
  closeButton,
  body,
  footer
};
const Modal = ({
  show,
  onHide,
  onSubmit,
  title: title2,
  children,
  footer: footer2
}) => {
  const modalRef = reactExports.useRef(null);
  reactExports.useEffect(() => {
    const handleKeyDown = (e) => {
      if (!show) return;
      if (e.key === "Escape") {
        onHide();
      } else if (e.key === "Enter" && onSubmit) {
        e.preventDefault();
        onSubmit();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [show, onHide, onSubmit]);
  reactExports.useEffect(() => {
    if (show && modalRef.current) {
      const autofocusEl = modalRef.current.querySelector(
        "[autofocus], [data-autofocus]"
      );
      if (autofocusEl) {
        setTimeout(() => autofocusEl.focus(), 0);
      }
    }
  }, [show]);
  if (!show) return null;
  return reactDomExports.createPortal(
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.backdrop, onClick: onHide, children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        ref: modalRef,
        className: styles.modal,
        onClick: (e) => e.stopPropagation(),
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles.header, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: styles.title, children: title2 }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("button", { className: styles.closeButton, onClick: onHide, children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: "codicon codicon-close" }) })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.body, children }),
          footer2 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles.footer, children: footer2 })
        ]
      }
    ) }),
    document.body
  );
};
export {
  Modal as M
};
//# sourceMappingURL=Modal.js.map
