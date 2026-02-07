const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["./lib-CBtriEt5.js","./chunk-DfAF0w94.js","./wgxpath.install-node-Csk64Aj9.js","./liteDOM-Cp0aN3bP.js","./_commonjsHelpers.js","./xypic-DrMJn58R.js","./tex-svg-full-BI3fonbT.js"])))=>i.map(i=>d[i]);
import { r as reactExports, bX as prismExports, j as jsxRuntimeExports, g as clsx, l as useStore, bY as debounce$1, bZ as createLogger, bP as useParams, b_ as parseTranscriptParams, m as useSearchParams, B as transcriptRoute, h as E, i as fo, e as ApplicationIcons, b$ as __vitePreload, n as useLoggingNavigate, c0 as iconForMimeType, c1 as isHostedEnvironment, bL as lib$1, c2 as useExtendedFind, bU as PulsingDots } from "./index.js";
import { T as ToolButton, P as PopOver, d as formatNumber, b as formatDateTime, e as formatTime$1 } from "./ToolButton.js";
import { l } from "./chunk-DfAF0w94.js";
import { N as NoContentsPanel } from "./NoContentsPanel.js";
const isAnsiOutput = (text2) => {
  const ansiRegex = (
    // eslint-disable-next-line no-control-regex
    /\x1b(?:\[[\x30-\x3f]*[\x20-\x2f]*[\x40-\x7e]|\].*?(?:\x07|\x1b\\)|[^[\]>])/g
  );
  return ansiRegex.test(text2);
};
const maybeBase64 = (str, minLen = 256) => {
  const base64Pattern = /^(?:[A-Za-z0-9+/]{4})*?(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
  return str.length > minLen && base64Pattern.test(str);
};
const useResizeObserver = (callback) => {
  const elementRef = reactExports.useRef(null);
  const observerRef = reactExports.useRef(null);
  reactExports.useEffect(() => {
    const element = elementRef.current;
    if (!element) return;
    observerRef.current = new ResizeObserver((entries) => {
      if (entries[0]) {
        callback(entries[0]);
      }
    });
    observerRef.current.observe(element);
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [callback]);
  return elementRef;
};
const decodeHtmlEntities = (text2) => {
  const parser = new DOMParser();
  const doc = parser.parseFromString(text2, "text/html");
  return doc.documentElement.textContent || text2;
};
const isJson = (text2) => {
  text2 = text2.trim();
  if (text2.startsWith("{") && text2.endsWith("}")) {
    try {
      JSON.parse(text2);
      return true;
    } catch {
      return false;
    }
  }
  return false;
};
const asJsonObjArray = (text2) => {
  text2 = text2.trim();
  if (text2.startsWith("[") && text2.endsWith("]")) {
    try {
      const arr = JSON.parse(text2);
      if (Array.isArray(arr) && arr.every((item) => typeof item === "object")) {
        return arr;
      } else {
        return void 0;
      }
    } catch {
      return void 0;
    }
  }
  return void 0;
};
const parsedJson = (text2) => {
  text2 = text2.trim();
  if (text2.startsWith("{") && text2.endsWith("}")) {
    try {
      return JSON.parse(text2);
    } catch {
      return void 0;
    }
  }
  return void 0;
};
const isImage = (mimeType) => {
  return mimeType.startsWith("image/");
};
const toArray = (val) => {
  if (Array.isArray(val)) {
    return val;
  } else {
    return [val];
  }
};
const isRecord = (value2) => {
  return typeof value2 === "object" && value2 !== null && !Array.isArray(value2);
};
const kPrismRenderMaxSize = 25e4;
const highlightCodeBlocks = (container2) => {
  const codeBlocks = container2.querySelectorAll("pre code");
  codeBlocks.forEach((block2) => {
    if (block2.hasAttribute("data-highlighted")) {
      return;
    }
    if (block2.className.includes("language-")) {
      block2.classList.add("sourceCode");
      prismExports.highlightElement(block2);
      block2.setAttribute("data-highlighted", "true");
    }
  });
};
const usePrismHighlight = (containerRef, contentLength) => {
  reactExports.useEffect(() => {
    if (contentLength <= 0 || containerRef.current === null || contentLength > kPrismRenderMaxSize) {
      return;
    }
    const container2 = containerRef.current;
    requestAnimationFrame(() => {
      highlightCodeBlocks(container2);
    });
    const observer = new MutationObserver((mutations) => {
      const hasNewCodeBlocks = mutations.some((mutation) => {
        if (mutation.type === "childList") {
          return Array.from(mutation.addedNodes).some((node2) => {
            if (node2.nodeType === Node.ELEMENT_NODE) {
              const el = node2;
              return el.querySelector?.("pre code") || el.matches?.("pre code");
            }
            return false;
          });
        }
        return false;
      });
      if (hasNewCodeBlocks) {
        highlightCodeBlocks(container2);
      }
    });
    observer.observe(container2, {
      childList: true,
      subtree: true
    });
    return () => {
      observer.disconnect();
    };
  }, [contentLength, containerRef]);
};
const kMaxStringValueDisplay = 1048576;
const JSONPanel = ({
  id,
  json,
  data,
  simple: simple2 = false,
  style: style2,
  className: className2
}) => {
  const sourceCode = reactExports.useMemo(() => {
    return json || data ? JSON.stringify(resolveBase64(data), void 0, 2) : "";
  }, [json, data]);
  const sourceCodeRef = reactExports.useRef(null);
  usePrismHighlight(sourceCodeRef, sourceCode.length);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: sourceCodeRef, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
    "pre",
    {
      className: clsx("json-panel", simple2 ? "simple" : "", className2),
      style: style2,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx("code", { id, className: clsx("source-code", "language-javascript"), children: sourceCode })
    }
  ) });
};
const resolveBase64 = (value2) => {
  const prefix = "data:image";
  if (Array.isArray(value2)) {
    return value2.map((v) => resolveBase64(v));
  }
  if (value2 && typeof value2 === "object") {
    const resolvedObject = {};
    for (const key2 of Object.keys(value2)) {
      const record = value2;
      resolvedObject[key2] = resolveBase64(record[key2]);
    }
    return resolvedObject;
  }
  if (typeof value2 === "string") {
    let resolvedValue = value2;
    if (resolvedValue.startsWith(prefix)) {
      resolvedValue = "[base64 image]";
    } else if (resolvedValue.length > kMaxStringValueDisplay) {
      resolvedValue = "[long data]";
    } else if (maybeBase64(resolvedValue)) {
      resolvedValue = "[base64 data]";
    }
    return resolvedValue;
  }
  return value2;
};
const log = createLogger("scrolling");
function useStatefulScrollPosition(elementRef, elementKey, delay = 1e3, scrollable2 = true) {
  const getScrollPosition = useStore((state) => state.getScrollPosition);
  const setScrollPosition = useStore((state) => state.setScrollPosition);
  const handleScrollInner = reactExports.useCallback(
    (e) => {
      const target = e.target;
      const position = target.scrollTop;
      log.debug(`Storing scroll position`, elementKey, position);
      setScrollPosition(elementKey, position);
    },
    [elementKey, setScrollPosition]
  );
  const handleScroll = reactExports.useMemo(
    () => debounce$1(handleScrollInner, delay),
    [handleScrollInner, delay]
  );
  const restoreScrollPosition = reactExports.useCallback(() => {
    const element = elementRef.current;
    const savedPosition = getScrollPosition(elementKey);
    if (element && savedPosition !== void 0) {
      requestAnimationFrame(() => {
        element.scrollTop = savedPosition;
        requestAnimationFrame(() => {
          if (element.scrollTop !== savedPosition) {
            element.scrollTop = savedPosition;
          }
        });
      });
    }
  }, [elementKey, getScrollPosition, elementRef]);
  reactExports.useEffect(() => {
    const element = elementRef.current;
    if (!element || !scrollable2) {
      return;
    }
    log.debug(`Restore Scroll Hook`, elementKey);
    const savedPosition = getScrollPosition(elementKey);
    if (savedPosition !== void 0) {
      log.debug(`Restoring scroll position`, savedPosition);
      const tryRestoreScroll = () => {
        if (element.scrollHeight > element.clientHeight) {
          if (element.scrollTop !== savedPosition) {
            element.scrollTop = savedPosition;
            log.debug(`Scroll position restored to ${savedPosition}`);
          }
          return true;
        }
        return false;
      };
      if (!tryRestoreScroll()) {
        let attempts = 0;
        const maxAttempts = 5;
        const pollForRender = () => {
          if (tryRestoreScroll() || attempts >= maxAttempts) {
            if (attempts >= maxAttempts) {
              log.debug(
                `Failed to restore scroll after ${maxAttempts} attempts`
              );
            }
            return;
          }
          attempts++;
          setTimeout(pollForRender, 1e3);
        };
        setTimeout(pollForRender, 1e3);
      }
    }
    if (element.addEventListener) {
      element.addEventListener("scroll", handleScroll);
    } else {
      log.warn("Element has no way to add event listener", element);
    }
    return () => {
      if (element.removeEventListener) {
        element.removeEventListener("scroll", handleScroll);
      } else {
        log.warn("Element has no way to remove event listener", element);
      }
    };
  }, [elementKey, elementRef, getScrollPosition, handleScroll, scrollable2]);
  return { restoreScrollPosition };
}
const useVirtuosoState = (virtuosoRef, elementKey, delay = 1e3) => {
  const restoreState = useStore(
    reactExports.useCallback((state) => state.listPositions[elementKey], [elementKey])
  );
  const setListPosition = useStore(
    reactExports.useCallback((state) => state.setListPosition, [])
  );
  const clearListPosition = useStore(
    reactExports.useCallback((state) => state.clearListPosition, [])
  );
  const debouncedFnRef = reactExports.useRef(null);
  const handleStateChange = reactExports.useCallback(
    (state) => {
      log.debug(`Storing list state: [${elementKey}]`, state);
      setListPosition(elementKey, state);
    },
    [elementKey, setListPosition]
  );
  reactExports.useEffect(() => {
    debouncedFnRef.current = debounce$1((isScrolling2) => {
      log.debug("List scroll", isScrolling2);
      const element = virtuosoRef.current;
      if (!element) {
        return;
      }
      element.getState(handleStateChange);
    }, delay);
    return () => {
      clearListPosition(elementKey);
    };
  }, [delay, elementKey, handleStateChange, clearListPosition, virtuosoRef]);
  const isScrolling = reactExports.useCallback((scrolling) => {
    if (!scrolling) {
      return;
    }
    if (debouncedFnRef.current) {
      debouncedFnRef.current(scrolling);
    }
  }, []);
  const stateRef = reactExports.useRef(restoreState);
  reactExports.useEffect(() => {
    stateRef.current = restoreState;
  }, [restoreState]);
  const getRestoreState = reactExports.useCallback(() => stateRef.current, []);
  const setVisibleRangeRaw = useStore((state) => state.setVisibleRange);
  const setVisibleRange = reactExports.useCallback(
    (value2) => {
      setVisibleRangeRaw(elementKey, value2);
    },
    [setVisibleRangeRaw, elementKey]
  );
  const visibleRanges = useStore((state) => state.visibleRanges);
  const visibleRange = reactExports.useMemo(() => {
    return visibleRanges[elementKey] || {
      startIndex: 0,
      endIndex: 0
    };
  }, [visibleRanges, elementKey]);
  return { getRestoreState, isScrolling, visibleRange, setVisibleRange };
};
function useRafThrottle(callback) {
  const rafRef = reactExports.useRef(null);
  const callbackRef = reactExports.useRef(callback);
  reactExports.useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);
  const throttledCallback = reactExports.useCallback((...args2) => {
    if (rafRef.current) {
      return;
    }
    rafRef.current = requestAnimationFrame(() => {
      callbackRef.current(...args2);
      rafRef.current = null;
    });
  }, []);
  reactExports.useEffect(() => {
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, []);
  return throttledCallback;
}
function useScrollTrack(elementIds, onElementVisible, scrollRef, options) {
  const currentVisibleRef = reactExports.useRef(null);
  const lastCheckRef = reactExports.useRef(0);
  const rafRef = reactExports.useRef(null);
  const findTopmostVisibleElement = reactExports.useCallback(() => {
    const container2 = scrollRef?.current;
    const containerRect = container2?.getBoundingClientRect();
    const topOffset = 50;
    const viewportTop = containerRect ? containerRect.top + topOffset : topOffset;
    const viewportBottom = containerRect ? containerRect.bottom : window.innerHeight;
    const viewportHeight = viewportBottom - viewportTop;
    let detectionPoint = viewportTop;
    if (container2) {
      const scrollHeight = container2.scrollHeight;
      const scrollTop = container2.scrollTop;
      const clientHeight = container2.clientHeight;
      const maxScroll = scrollHeight - clientHeight;
      const scrollProgress = maxScroll > 0 ? scrollTop / maxScroll : 0;
      const slideThreshold = 0.8;
      if (scrollProgress > slideThreshold) {
        const slideProgress = (scrollProgress - slideThreshold) / (1 - slideThreshold);
        const easedProgress = Math.pow(slideProgress, 3);
        detectionPoint = viewportTop + viewportHeight * 0.9 * easedProgress;
      }
      if (scrollProgress >= 0.99) {
        detectionPoint = viewportBottom - 50;
      }
    }
    let closestId = null;
    let closestDistance = Infinity;
    const elementIdSet = new Set(elementIds);
    const elements = container2 ? container2.querySelectorAll("[id]") : document.querySelectorAll("[id]");
    for (const element of elements) {
      const id = element.id;
      if (elementIdSet.has(id)) {
        const rect = element.getBoundingClientRect();
        if (rect.bottom >= viewportTop && rect.top <= viewportBottom) {
          const elementCenter = rect.top + rect.height / 2;
          const distance = Math.abs(elementCenter - detectionPoint);
          if (distance < closestDistance) {
            closestDistance = distance;
            closestId = id;
          }
        }
      }
    }
    return closestId;
  }, [elementIds, scrollRef, options?.topOffset]);
  const checkVisibility = reactExports.useCallback(() => {
    const now = Date.now();
    const checkInterval = 100;
    if (now - lastCheckRef.current < checkInterval) {
      return;
    }
    lastCheckRef.current = now;
    const topmostId = findTopmostVisibleElement();
    if (topmostId !== currentVisibleRef.current) {
      currentVisibleRef.current = topmostId;
      if (topmostId) {
        onElementVisible(topmostId);
      }
    }
  }, [findTopmostVisibleElement, onElementVisible, options?.checkInterval]);
  const handleScroll = reactExports.useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
    }
    rafRef.current = requestAnimationFrame(() => {
      checkVisibility();
      rafRef.current = null;
    });
  }, [checkVisibility]);
  reactExports.useEffect(() => {
    if (elementIds.length === 0) return;
    const scrollElement = scrollRef?.current || window;
    checkVisibility();
    scrollElement.addEventListener("scroll", handleScroll, { passive: true });
    const intervalId = setInterval(checkVisibility, 1e3);
    return () => {
      scrollElement.removeEventListener("scroll", handleScroll);
      clearInterval(intervalId);
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [elementIds, scrollRef, handleScroll, checkVisibility]);
}
const tabs = "_tabs_tfvnu_1";
const tabContents = "_tabContents_tfvnu_5";
const scrollable = "_scrollable_tfvnu_10";
const tab$1 = "_tab_tfvnu_1";
const tabItem = "_tabItem_tfvnu_26";
const tabIcon = "_tabIcon_tfvnu_30";
const tabTools = "_tabTools_tfvnu_34";
const tabStyle = "_tabStyle_tfvnu_44";
const moduleStyles = {
  tabs,
  tabContents,
  scrollable,
  tab: tab$1,
  tabItem,
  tabIcon,
  tabTools,
  tabStyle
};
const TabSet = ({
  id,
  type = "tabs",
  className: className2,
  tabPanelsClassName,
  tabControlsClassName,
  tools: tools2,
  tabsRef,
  children: children2
}) => {
  const validTabs = flattenChildren(children2);
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
          className2,
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
          tools2 && /* @__PURE__ */ jsxRuntimeExports.jsx(TabTools, { tools: tools2 })
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(TabPanels, { id, tabs: validTabs, className: tabPanelsClassName })
  ] });
};
const Tab = ({ type = "tabs", tab: tab2, index, className: className2 }) => {
  const tabId = tab2.props.id || computeTabId("tabset", index);
  const tabContentsId = computeTabContentsId(tab2.props.id);
  const isActive = tab2.props.selected;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("li", { role: "presentation", className: clsx("nav-item", moduleStyles.tabItem), children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "button",
    {
      id: tabId,
      className: clsx(
        "nav-link",
        className2,
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
const TabPanels = ({ id, tabs: tabs2, className: className2 }) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("tab-content", className2), id: `${id}-content`, children: tabs2.map((tab2, index) => /* @__PURE__ */ jsxRuntimeExports.jsx(TabPanel, { ...tab2.props, index }, tab2.props.id)) });
const TabPanel = ({
  id,
  selected,
  style: style2,
  scrollable: scrollable2 = true,
  scrollRef,
  className: className2,
  children: children2
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
        className2,
        moduleStyles.tabContents,
        scrollable2 && moduleStyles.scrollable
      ),
      style: style2,
      children: selected ? children2 : null
    }
  );
};
const TabTools = ({ tools: tools2 }) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("tab-tools", moduleStyles.tabTools), children: tools2 });
const computeTabId = (id, index) => `${id}-${index}`;
const computeTabContentsId = (id) => `${id}-contents`;
const flattenChildren = (children2) => {
  return reactExports.Children.toArray(children2).flatMap((child) => {
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
const grid$3 = "_grid_1vh2w_1";
const cell = "_cell_1vh2w_8";
const value = "_value_1vh2w_13";
const styles$N = {
  grid: grid$3,
  cell,
  value
};
function commonjsRequire(path) {
  throw new Error('Could not dynamically require "' + path + '". Please configure the dynamicRequireTargets or/and ignoreDynamicRequires option of @rollup/plugin-commonjs appropriately for this require call to work.');
}
var ansiOutput = { exports: {} };
var hasRequiredAnsiOutput;
function requireAnsiOutput() {
  if (hasRequiredAnsiOutput) return ansiOutput.exports;
  hasRequiredAnsiOutput = 1;
  (function(module, exports$12) {
    (function(factory) {
      {
        var v = factory(commonjsRequire, exports$12);
        if (v !== void 0) module.exports = v;
      }
    })(function(require2, exports$13) {
      Object.defineProperty(exports$13, "__esModule", { value: true });
      exports$13.ANSIOutput = exports$13.ANSIColor = exports$13.ANSIFont = exports$13.ANSIStyle = void 0;
      let counter = 0;
      const generateId = () => {
        return `${++counter}`.padStart(16, "0");
      };
      var ANSIStyle;
      (function(ANSIStyle2) {
        ANSIStyle2["Bold"] = "ansiBold";
        ANSIStyle2["Dim"] = "ansiDim";
        ANSIStyle2["Italic"] = "ansiItalic";
        ANSIStyle2["Underlined"] = "ansiUnderlined";
        ANSIStyle2["SlowBlink"] = "ansiSlowBlink";
        ANSIStyle2["RapidBlink"] = "ansiRapidBlink";
        ANSIStyle2["Hidden"] = "ansiHidden";
        ANSIStyle2["CrossedOut"] = "ansiCrossedOut";
        ANSIStyle2["Fraktur"] = "ansiFraktur";
        ANSIStyle2["DoubleUnderlined"] = "ansiDoubleUnderlined";
        ANSIStyle2["Framed"] = "ansiFramed";
        ANSIStyle2["Encircled"] = "ansiEncircled";
        ANSIStyle2["Overlined"] = "ansiOverlined";
        ANSIStyle2["Superscript"] = "ansiSuperscript";
        ANSIStyle2["Subscript"] = "ansiSubscript";
      })(ANSIStyle || (exports$13.ANSIStyle = ANSIStyle = {}));
      var ANSIFont;
      (function(ANSIFont2) {
        ANSIFont2["AlternativeFont1"] = "ansiAlternativeFont1";
        ANSIFont2["AlternativeFont2"] = "ansiAlternativeFont2";
        ANSIFont2["AlternativeFont3"] = "ansiAlternativeFont3";
        ANSIFont2["AlternativeFont4"] = "ansiAlternativeFont4";
        ANSIFont2["AlternativeFont5"] = "ansiAlternativeFont5";
        ANSIFont2["AlternativeFont6"] = "ansiAlternativeFont6";
        ANSIFont2["AlternativeFont7"] = "ansiAlternativeFont7";
        ANSIFont2["AlternativeFont8"] = "ansiAlternativeFont8";
        ANSIFont2["AlternativeFont9"] = "ansiAlternativeFont9";
      })(ANSIFont || (exports$13.ANSIFont = ANSIFont = {}));
      var ANSIColor;
      (function(ANSIColor2) {
        ANSIColor2["Black"] = "ansiBlack";
        ANSIColor2["Red"] = "ansiRed";
        ANSIColor2["Green"] = "ansiGreen";
        ANSIColor2["Yellow"] = "ansiYellow";
        ANSIColor2["Blue"] = "ansiBlue";
        ANSIColor2["Magenta"] = "ansiMagenta";
        ANSIColor2["Cyan"] = "ansiCyan";
        ANSIColor2["White"] = "ansiWhite";
        ANSIColor2["BrightBlack"] = "ansiBrightBlack";
        ANSIColor2["BrightRed"] = "ansiBrightRed";
        ANSIColor2["BrightGreen"] = "ansiBrightGreen";
        ANSIColor2["BrightYellow"] = "ansiBrightYellow";
        ANSIColor2["BrightBlue"] = "ansiBrightBlue";
        ANSIColor2["BrightMagenta"] = "ansiBrightMagenta";
        ANSIColor2["BrightCyan"] = "ansiBrightCyan";
        ANSIColor2["BrightWhite"] = "ansiBrightWhite";
      })(ANSIColor || (exports$13.ANSIColor = ANSIColor = {}));
      class ANSIOutput {
        //#region Private Properties
        /**
         * Gets or sets the parser state.
         */
        _parserState = ParserState.BufferingOutput;
        /**
         * Gets or sets the control sequence that's being parsed.
         */
        _controlSequence = "";
        /**
         * Gets or sets the SGR state.
         */
        _sgrState = void 0;
        /**
         * Gets or sets the current set of output lines.
         */
        _outputLines = [];
        /**
         * Gets or sets the output line.
         */
        _outputLine = 0;
        /**
         * Gets or sets the output column.
         */
        _outputColumn = 0;
        /**
         * Gets or sets the buffer.
         */
        _buffer = "";
        /**
         * Gets or sets a value which indicates whether there is a pending newline.
         */
        _pendingNewline = false;
        //#endregion Private Properties
        //#region Public Properties
        /**
         * Gets the output lines.
         */
        get outputLines() {
          this.flushBuffer();
          return this._outputLines;
        }
        //#endregion Public Properties
        //#region Public Static Methods
        /**
         * Processes output and returns the ANSIOutput lines of the output.
         * @param output The output to process.
         * @returns The ANSIOutput lines of the output.
         */
        static processOutput(output2) {
          const ansiOutput2 = new ANSIOutput();
          ansiOutput2.processOutput(output2);
          return ansiOutput2.outputLines;
        }
        //#endregion Public Static Methods
        //#region Public Methods
        /**
         * Processes output.
         * @param output The output to process.
         */
        processOutput(output2) {
          for (let i2 = 0; i2 < output2.length; i2++) {
            if (this._pendingNewline) {
              this.flushBuffer();
              this._outputLine++;
              this._outputColumn = 0;
              this._pendingNewline = false;
            }
            const char = output2.charAt(i2);
            if (this._parserState === ParserState.BufferingOutput) {
              if (char === "\x1B") {
                this.flushBuffer();
                this._parserState = ParserState.ControlSequenceStarted;
              } else if (char === "") {
                this.flushBuffer();
                this._parserState = ParserState.ParsingControlSequence;
              } else {
                this.processCharacter(char);
              }
            } else if (this._parserState === ParserState.ControlSequenceStarted) {
              if (char === "[") {
                this._parserState = ParserState.ParsingControlSequence;
              } else {
                this._parserState = ParserState.BufferingOutput;
                this.processCharacter(char);
              }
            } else if (this._parserState === ParserState.ParsingControlSequence) {
              this._controlSequence += char;
              if (char.match(/^[A-Za-z]$/)) {
                this.processControlSequence();
              }
            }
          }
          this.flushBuffer();
        }
        //#endregion Public Methods
        //#region Private Methods
        /**
         * Flushes the buffer to the output line.
         */
        flushBuffer() {
          for (let i2 = this._outputLines.length; i2 < this._outputLine + 1; i2++) {
            this._outputLines.push(new OutputLine());
          }
          if (this._buffer) {
            const outputLine = this._outputLines[this._outputLine];
            outputLine.insert(this._buffer, this._outputColumn, this._sgrState);
            this._outputColumn += this._buffer.length;
            this._buffer = "";
          }
        }
        /**
         * Processes a character.
         * @param char The character.
         */
        processCharacter(char) {
          switch (char) {
            // LF sets the pending newline flag.
            case "\n":
              this._pendingNewline = true;
              break;
            // CR flushes the buffer and sets the output column to 0.
            case "\r":
              this.flushBuffer();
              this._outputColumn = 0;
              break;
            // Buffer the character.
            default:
              this._buffer += char;
              break;
          }
        }
        /**
         * Processes a control sequence.
         */
        processControlSequence() {
          switch (this._controlSequence.charAt(this._controlSequence.length - 1)) {
            // CUU (Cursor Up).
            case "A":
              this.processCUU();
              break;
            // CUD (Cursor Down).
            case "B":
              this.processCUD();
              break;
            // CUF (Cursor Forward).
            case "C":
              this.processCUF();
              break;
            // CUB (Cursor Backward).
            case "D":
              this.processCUB();
              break;
            // CUP (Cursor Position).
            case "H":
              this.processCUP();
              break;
            // ED (Erase in Display).
            case "J":
              this.processED();
              break;
            // EL (Erase in Line).
            case "K":
              this.processEL();
              break;
            // SGR (Select Graphic Rendition).
            case "m":
              this.processSGR();
              break;
          }
          this._controlSequence = "";
          this._parserState = ParserState.BufferingOutput;
        }
        /**
         * Processes a CUU (Cursor Up) control sequence.
         */
        processCUU() {
          const match2 = this._controlSequence.match(/^([0-9]*)A$/);
          if (match2) {
            this._outputLine = Math.max(this._outputLine - rangeParam(match2[1], 1, 1), 0);
          }
        }
        /**
         * Processes a CUD (Cursor Down) control sequence.
         */
        processCUD() {
          const match2 = this._controlSequence.match(/^([0-9]*)B$/);
          if (match2) {
            this._outputLine = this._outputLine + rangeParam(match2[1], 1, 1);
          }
        }
        /**
         * Processes a CUF (Cursor Forward) control sequence.
         */
        processCUF() {
          const match2 = this._controlSequence.match(/^([0-9]*)C$/);
          if (match2) {
            this._outputColumn = this._outputColumn + rangeParam(match2[1], 1, 1);
          }
        }
        /**
         * Processes a CUB (Cursor Backward) control sequence.
         */
        processCUB() {
          const match2 = this._controlSequence.match(/^([0-9]*)D$/);
          if (match2) {
            this._outputColumn = Math.max(this._outputColumn - rangeParam(match2[1], 1, 1), 0);
          }
        }
        /**
         * Processes a CUP (Cursor Position) control sequence.
         */
        processCUP() {
          const match2 = this._controlSequence.match(/^([0-9]*)(?:;?([0-9]*))H$/);
          if (match2) {
            this._outputLine = rangeParam(match2[1], 1, 1) - 1;
            this._outputColumn = rangeParam(match2[2], 1, 1) - 1;
          }
        }
        /**
         * Processes an ED (Erase in Display) control sequence.
         */
        processED() {
          const match2 = this._controlSequence.match(/^([0-9]*)J$/);
          if (match2) {
            switch (getParam(match2[1], 0)) {
              // Clear from cursor to the end of the screen.
              case 0:
                this._outputLines[this._outputLine].clearToEndOfLine(this._outputColumn);
                for (let i2 = this._outputLine + 1; i2 < this._outputLines.length; i2++) {
                  this._outputLines[i2].clearEntireLine();
                }
                break;
              // Clear from cursor to the beginning of the screen.
              case 1:
                this._outputLines[this._outputLine].clearToBeginningOfLine(this._outputColumn);
                for (let i2 = 0; i2 < this._outputLine; i2++) {
                  this._outputLines[i2].clearEntireLine();
                }
                break;
              // Clear the entire screen.
              case 2:
                for (let i2 = 0; i2 < this._outputLines.length; i2++) {
                  this._outputLines[i2].clearEntireLine();
                }
                break;
            }
          }
        }
        /**
         * Processes an EL (Erase in Line) control sequence.
         */
        processEL() {
          const match2 = this._controlSequence.match(/^([0-9]*)K$/);
          if (match2) {
            const outputLine = this._outputLines[this._outputLine];
            switch (getParam(match2[1], 0)) {
              // Clear from cursor to the end of the line.
              case 0:
                outputLine.clearToEndOfLine(this._outputColumn);
                break;
              // Clear from cursor to the beginning of the line.
              case 1:
                outputLine.clearToBeginningOfLine(this._outputColumn);
                break;
              // Clear the entire line.
              case 2:
                outputLine.clearEntireLine();
                break;
            }
          }
        }
        /**
         * Processes an SGR (Select Graphic Rendition) control sequence.
         */
        processSGR() {
          const sgrState = this._sgrState ? this._sgrState.copy() : new SGRState();
          const sgrParams = this._controlSequence.slice(0, -1).split(";").map((sgrParam) => sgrParam === "" ? SGRParam.Reset : parseInt(sgrParam, 10));
          for (let index = 0; index < sgrParams.length; index++) {
            const sgrParam = sgrParams[index];
            const processSetColor = () => {
              if (index + 1 === sgrParams.length) {
                return void 0;
              }
              switch (sgrParams[++index]) {
                // SGRColorParam.Color256 is an indexed color.
                case SGRParamColor.Color256: {
                  if (index + 1 === sgrParams.length) {
                    return void 0;
                  }
                  const colorIndex = sgrParams[++index];
                  switch (colorIndex) {
                    case SGRParamIndexedColor.Black:
                      return ANSIColor.Black;
                    case SGRParamIndexedColor.Red:
                      return ANSIColor.Red;
                    case SGRParamIndexedColor.Green:
                      return ANSIColor.Green;
                    case SGRParamIndexedColor.Yellow:
                      return ANSIColor.Yellow;
                    case SGRParamIndexedColor.Blue:
                      return ANSIColor.Blue;
                    case SGRParamIndexedColor.Magenta:
                      return ANSIColor.Magenta;
                    case SGRParamIndexedColor.Cyan:
                      return ANSIColor.Cyan;
                    case SGRParamIndexedColor.White:
                      return ANSIColor.White;
                    case SGRParamIndexedColor.BrightBlack:
                      return ANSIColor.BrightBlack;
                    case SGRParamIndexedColor.BrightRed:
                      return ANSIColor.BrightRed;
                    case SGRParamIndexedColor.BrightGreen:
                      return ANSIColor.BrightGreen;
                    case SGRParamIndexedColor.BrightYellow:
                      return ANSIColor.BrightYellow;
                    case SGRParamIndexedColor.BrightBlue:
                      return ANSIColor.BrightBlue;
                    case SGRParamIndexedColor.BrightMagenta:
                      return ANSIColor.BrightMagenta;
                    case SGRParamIndexedColor.BrightCyan:
                      return ANSIColor.BrightCyan;
                    case SGRParamIndexedColor.BrightWhite:
                      return ANSIColor.BrightWhite;
                    // Process other color indexes.
                    default:
                      if (colorIndex % 1 !== 0) {
                        return void 0;
                      }
                      if (colorIndex >= 16 && colorIndex <= 231) {
                        let colorNumber = colorIndex - 16;
                        let blue = colorNumber % 6;
                        colorNumber = (colorNumber - blue) / 6;
                        let green = colorNumber % 6;
                        colorNumber = (colorNumber - green) / 6;
                        let red = colorNumber;
                        blue = Math.round(blue * 255 / 5);
                        green = Math.round(green * 255 / 5);
                        red = Math.round(red * 255 / 5);
                        return "#" + twoDigitHex(red) + twoDigitHex(green) + twoDigitHex(blue);
                      } else if (colorIndex >= 232 && colorIndex <= 255) {
                        const rgb = Math.round((colorIndex - 232) / 23 * 255);
                        const grayscale = twoDigitHex(rgb);
                        return "#" + grayscale + grayscale + grayscale;
                      } else {
                        return void 0;
                      }
                  }
                }
                // SGRParamColor.ColorRGB is an r;g;b color.
                case SGRParamColor.ColorRGB: {
                  const rgb = [0, 0, 0];
                  for (let i2 = 0; i2 < 3 && index + 1 < sgrParams.length; i2++) {
                    rgb[i2] = sgrParams[++index];
                  }
                  return "#" + twoDigitHex(rgb[0]) + twoDigitHex(rgb[1]) + twoDigitHex(rgb[2]);
                }
              }
              return void 0;
            };
            switch (sgrParam) {
              case SGRParam.Reset:
                sgrState.reset();
                break;
              case SGRParam.Bold:
                sgrState.setStyle(ANSIStyle.Bold);
                break;
              case SGRParam.Dim:
                sgrState.setStyle(ANSIStyle.Dim);
                break;
              case SGRParam.Italic:
                sgrState.setStyle(ANSIStyle.Italic);
                break;
              case SGRParam.Underlined:
                sgrState.setStyle(ANSIStyle.Underlined, ANSIStyle.DoubleUnderlined);
                break;
              case SGRParam.SlowBlink:
                sgrState.setStyle(ANSIStyle.SlowBlink, ANSIStyle.RapidBlink);
                break;
              case SGRParam.RapidBlink:
                sgrState.setStyle(ANSIStyle.RapidBlink, ANSIStyle.SlowBlink);
                break;
              case SGRParam.Reversed:
                sgrState.setReversed(true);
                break;
              case SGRParam.Hidden:
                sgrState.setStyle(ANSIStyle.Hidden);
                break;
              case SGRParam.CrossedOut:
                sgrState.setStyle(ANSIStyle.CrossedOut);
                break;
              case SGRParam.PrimaryFont:
                sgrState.setFont();
                break;
              case SGRParam.AlternativeFont1:
                sgrState.setFont(ANSIFont.AlternativeFont1);
                break;
              case SGRParam.AlternativeFont2:
                sgrState.setFont(ANSIFont.AlternativeFont2);
                break;
              case SGRParam.AlternativeFont3:
                sgrState.setFont(ANSIFont.AlternativeFont3);
                break;
              case SGRParam.AlternativeFont4:
                sgrState.setFont(ANSIFont.AlternativeFont4);
                break;
              case SGRParam.AlternativeFont5:
                sgrState.setFont(ANSIFont.AlternativeFont5);
                break;
              case SGRParam.AlternativeFont6:
                sgrState.setFont(ANSIFont.AlternativeFont6);
                break;
              case SGRParam.AlternativeFont7:
                sgrState.setFont(ANSIFont.AlternativeFont7);
                break;
              case SGRParam.AlternativeFont8:
                sgrState.setFont(ANSIFont.AlternativeFont8);
                break;
              case SGRParam.AlternativeFont9:
                sgrState.setFont(ANSIFont.AlternativeFont9);
                break;
              case SGRParam.Fraktur:
                sgrState.setStyle(ANSIStyle.Fraktur);
                break;
              case SGRParam.DoubleUnderlined:
                sgrState.setStyle(ANSIStyle.DoubleUnderlined, ANSIStyle.Underlined);
                break;
              case SGRParam.NormalIntensity:
                sgrState.deleteStyles(ANSIStyle.Bold, ANSIStyle.Dim);
                break;
              case SGRParam.NotItalicNotFraktur:
                sgrState.deleteStyles(ANSIStyle.Italic, ANSIStyle.Fraktur);
                break;
              case SGRParam.NotUnderlined:
                sgrState.deleteStyles(ANSIStyle.Underlined, ANSIStyle.DoubleUnderlined);
                break;
              case SGRParam.NotBlinking:
                sgrState.deleteStyles(ANSIStyle.SlowBlink, ANSIStyle.RapidBlink);
                break;
              case SGRParam.ProportionalSpacing:
                break;
              case SGRParam.NotReversed:
                sgrState.setReversed(false);
                break;
              case SGRParam.Reveal:
                sgrState.deleteStyles(ANSIStyle.Hidden);
                break;
              case SGRParam.NotCrossedOut:
                sgrState.deleteStyles(ANSIStyle.CrossedOut);
                break;
              case SGRParam.ForegroundBlack:
                sgrState.setForegroundColor(ANSIColor.Black);
                break;
              case SGRParam.ForegroundRed:
                sgrState.setForegroundColor(ANSIColor.Red);
                break;
              case SGRParam.ForegroundGreen:
                sgrState.setForegroundColor(ANSIColor.Green);
                break;
              case SGRParam.ForegroundYellow:
                sgrState.setForegroundColor(ANSIColor.Yellow);
                break;
              case SGRParam.ForegroundBlue:
                sgrState.setForegroundColor(ANSIColor.Blue);
                break;
              case SGRParam.ForegroundMagenta:
                sgrState.setForegroundColor(ANSIColor.Magenta);
                break;
              case SGRParam.ForegroundCyan:
                sgrState.setForegroundColor(ANSIColor.Cyan);
                break;
              case SGRParam.ForegroundWhite:
                sgrState.setForegroundColor(ANSIColor.White);
                break;
              case SGRParam.SetForeground: {
                const foregroundColor = processSetColor();
                if (foregroundColor) {
                  sgrState.setForegroundColor(foregroundColor);
                }
                break;
              }
              case SGRParam.DefaultForeground:
                sgrState.setForegroundColor();
                break;
              case SGRParam.BackgroundBlack:
                sgrState.setBackgroundColor(ANSIColor.Black);
                break;
              case SGRParam.BackgroundRed:
                sgrState.setBackgroundColor(ANSIColor.Red);
                break;
              case SGRParam.BackgroundGreen:
                sgrState.setBackgroundColor(ANSIColor.Green);
                break;
              case SGRParam.BackgroundYellow:
                sgrState.setBackgroundColor(ANSIColor.Yellow);
                break;
              case SGRParam.BackgroundBlue:
                sgrState.setBackgroundColor(ANSIColor.Blue);
                break;
              case SGRParam.BackgroundMagenta:
                sgrState.setBackgroundColor(ANSIColor.Magenta);
                break;
              case SGRParam.BackgroundCyan:
                sgrState.setBackgroundColor(ANSIColor.Cyan);
                break;
              case SGRParam.BackgroundWhite:
                sgrState.setBackgroundColor(ANSIColor.White);
                break;
              case SGRParam.SetBackground: {
                const backgroundColor = processSetColor();
                if (backgroundColor) {
                  sgrState.setBackgroundColor(backgroundColor);
                }
                break;
              }
              case SGRParam.DefaultBackground:
                sgrState.setBackgroundColor();
                break;
              case SGRParam.ForegroundBrightBlack:
                sgrState.setForegroundColor(ANSIColor.BrightBlack);
                break;
              case SGRParam.ForegroundBrightRed:
                sgrState.setForegroundColor(ANSIColor.BrightRed);
                break;
              case SGRParam.ForegroundBrightGreen:
                sgrState.setForegroundColor(ANSIColor.BrightGreen);
                break;
              case SGRParam.ForegroundBrightYellow:
                sgrState.setForegroundColor(ANSIColor.BrightYellow);
                break;
              case SGRParam.ForegroundBrightBlue:
                sgrState.setForegroundColor(ANSIColor.BrightBlue);
                break;
              case SGRParam.ForegroundBrightMagenta:
                sgrState.setForegroundColor(ANSIColor.BrightMagenta);
                break;
              case SGRParam.ForegroundBrightCyan:
                sgrState.setForegroundColor(ANSIColor.BrightCyan);
                break;
              case SGRParam.ForegroundBrightWhite:
                sgrState.setForegroundColor(ANSIColor.BrightWhite);
                break;
              case SGRParam.BackgroundBrightBlack:
                sgrState.setBackgroundColor(ANSIColor.BrightBlack);
                break;
              case SGRParam.BackgroundBrightRed:
                sgrState.setBackgroundColor(ANSIColor.BrightRed);
                break;
              case SGRParam.BackgroundBrightGreen:
                sgrState.setBackgroundColor(ANSIColor.BrightGreen);
                break;
              case SGRParam.BackgroundBrightYellow:
                sgrState.setBackgroundColor(ANSIColor.BrightYellow);
                break;
              case SGRParam.BackgroundBrightBlue:
                sgrState.setBackgroundColor(ANSIColor.BrightBlue);
                break;
              case SGRParam.BackgroundBrightMagenta:
                sgrState.setBackgroundColor(ANSIColor.BrightMagenta);
                break;
              case SGRParam.BackgroundBrightCyan:
                sgrState.setBackgroundColor(ANSIColor.BrightCyan);
                break;
              case SGRParam.BackgroundBrightWhite:
                sgrState.setBackgroundColor(ANSIColor.BrightWhite);
                break;
            }
          }
          if (!SGRState.equivalent(sgrState, this._sgrState)) {
            this._sgrState = sgrState;
          }
        }
      }
      exports$13.ANSIOutput = ANSIOutput;
      var SGRParam;
      (function(SGRParam2) {
        SGRParam2[SGRParam2["Reset"] = 0] = "Reset";
        SGRParam2[SGRParam2["Bold"] = 1] = "Bold";
        SGRParam2[SGRParam2["Dim"] = 2] = "Dim";
        SGRParam2[SGRParam2["Italic"] = 3] = "Italic";
        SGRParam2[SGRParam2["Underlined"] = 4] = "Underlined";
        SGRParam2[SGRParam2["SlowBlink"] = 5] = "SlowBlink";
        SGRParam2[SGRParam2["RapidBlink"] = 6] = "RapidBlink";
        SGRParam2[SGRParam2["Reversed"] = 7] = "Reversed";
        SGRParam2[SGRParam2["Hidden"] = 8] = "Hidden";
        SGRParam2[SGRParam2["CrossedOut"] = 9] = "CrossedOut";
        SGRParam2[SGRParam2["PrimaryFont"] = 10] = "PrimaryFont";
        SGRParam2[SGRParam2["AlternativeFont1"] = 11] = "AlternativeFont1";
        SGRParam2[SGRParam2["AlternativeFont2"] = 12] = "AlternativeFont2";
        SGRParam2[SGRParam2["AlternativeFont3"] = 13] = "AlternativeFont3";
        SGRParam2[SGRParam2["AlternativeFont4"] = 14] = "AlternativeFont4";
        SGRParam2[SGRParam2["AlternativeFont5"] = 15] = "AlternativeFont5";
        SGRParam2[SGRParam2["AlternativeFont6"] = 16] = "AlternativeFont6";
        SGRParam2[SGRParam2["AlternativeFont7"] = 17] = "AlternativeFont7";
        SGRParam2[SGRParam2["AlternativeFont8"] = 18] = "AlternativeFont8";
        SGRParam2[SGRParam2["AlternativeFont9"] = 19] = "AlternativeFont9";
        SGRParam2[SGRParam2["Fraktur"] = 20] = "Fraktur";
        SGRParam2[SGRParam2["DoubleUnderlined"] = 21] = "DoubleUnderlined";
        SGRParam2[SGRParam2["NormalIntensity"] = 22] = "NormalIntensity";
        SGRParam2[SGRParam2["NotItalicNotFraktur"] = 23] = "NotItalicNotFraktur";
        SGRParam2[SGRParam2["NotUnderlined"] = 24] = "NotUnderlined";
        SGRParam2[SGRParam2["NotBlinking"] = 25] = "NotBlinking";
        SGRParam2[SGRParam2["ProportionalSpacing"] = 26] = "ProportionalSpacing";
        SGRParam2[SGRParam2["NotReversed"] = 27] = "NotReversed";
        SGRParam2[SGRParam2["Reveal"] = 28] = "Reveal";
        SGRParam2[SGRParam2["NotCrossedOut"] = 29] = "NotCrossedOut";
        SGRParam2[SGRParam2["ForegroundBlack"] = 30] = "ForegroundBlack";
        SGRParam2[SGRParam2["ForegroundRed"] = 31] = "ForegroundRed";
        SGRParam2[SGRParam2["ForegroundGreen"] = 32] = "ForegroundGreen";
        SGRParam2[SGRParam2["ForegroundYellow"] = 33] = "ForegroundYellow";
        SGRParam2[SGRParam2["ForegroundBlue"] = 34] = "ForegroundBlue";
        SGRParam2[SGRParam2["ForegroundMagenta"] = 35] = "ForegroundMagenta";
        SGRParam2[SGRParam2["ForegroundCyan"] = 36] = "ForegroundCyan";
        SGRParam2[SGRParam2["ForegroundWhite"] = 37] = "ForegroundWhite";
        SGRParam2[SGRParam2["SetForeground"] = 38] = "SetForeground";
        SGRParam2[SGRParam2["DefaultForeground"] = 39] = "DefaultForeground";
        SGRParam2[SGRParam2["BackgroundBlack"] = 40] = "BackgroundBlack";
        SGRParam2[SGRParam2["BackgroundRed"] = 41] = "BackgroundRed";
        SGRParam2[SGRParam2["BackgroundGreen"] = 42] = "BackgroundGreen";
        SGRParam2[SGRParam2["BackgroundYellow"] = 43] = "BackgroundYellow";
        SGRParam2[SGRParam2["BackgroundBlue"] = 44] = "BackgroundBlue";
        SGRParam2[SGRParam2["BackgroundMagenta"] = 45] = "BackgroundMagenta";
        SGRParam2[SGRParam2["BackgroundCyan"] = 46] = "BackgroundCyan";
        SGRParam2[SGRParam2["BackgroundWhite"] = 47] = "BackgroundWhite";
        SGRParam2[SGRParam2["SetBackground"] = 48] = "SetBackground";
        SGRParam2[SGRParam2["DefaultBackground"] = 49] = "DefaultBackground";
        SGRParam2[SGRParam2["DisableProportionalSpacing"] = 50] = "DisableProportionalSpacing";
        SGRParam2[SGRParam2["Framed"] = 51] = "Framed";
        SGRParam2[SGRParam2["Encircled"] = 52] = "Encircled";
        SGRParam2[SGRParam2["Overlined"] = 53] = "Overlined";
        SGRParam2[SGRParam2["NotFramedNotEncircled"] = 54] = "NotFramedNotEncircled";
        SGRParam2[SGRParam2["NotOverlined"] = 55] = "NotOverlined";
        SGRParam2[SGRParam2["SetUnderline"] = 58] = "SetUnderline";
        SGRParam2[SGRParam2["DefaultUnderline"] = 59] = "DefaultUnderline";
        SGRParam2[SGRParam2["IdeogramUnderlineOrRightSideLine"] = 60] = "IdeogramUnderlineOrRightSideLine";
        SGRParam2[SGRParam2["IdeogramDoubleUnderlineOrDoubleRightSideLine"] = 61] = "IdeogramDoubleUnderlineOrDoubleRightSideLine";
        SGRParam2[SGRParam2["IdeogramOverlineOrLeftSideLine"] = 62] = "IdeogramOverlineOrLeftSideLine";
        SGRParam2[SGRParam2["IdeogramDoubleOverlineOrDoubleLeftSideLine"] = 63] = "IdeogramDoubleOverlineOrDoubleLeftSideLine";
        SGRParam2[SGRParam2["IdeogramStressMarking"] = 64] = "IdeogramStressMarking";
        SGRParam2[SGRParam2["NoIdeogramAttributes"] = 65] = "NoIdeogramAttributes";
        SGRParam2[SGRParam2["Superscript"] = 73] = "Superscript";
        SGRParam2[SGRParam2["Subscript"] = 74] = "Subscript";
        SGRParam2[SGRParam2["NotSuperscriptNotSubscript"] = 75] = "NotSuperscriptNotSubscript";
        SGRParam2[SGRParam2["ForegroundBrightBlack"] = 90] = "ForegroundBrightBlack";
        SGRParam2[SGRParam2["ForegroundBrightRed"] = 91] = "ForegroundBrightRed";
        SGRParam2[SGRParam2["ForegroundBrightGreen"] = 92] = "ForegroundBrightGreen";
        SGRParam2[SGRParam2["ForegroundBrightYellow"] = 93] = "ForegroundBrightYellow";
        SGRParam2[SGRParam2["ForegroundBrightBlue"] = 94] = "ForegroundBrightBlue";
        SGRParam2[SGRParam2["ForegroundBrightMagenta"] = 95] = "ForegroundBrightMagenta";
        SGRParam2[SGRParam2["ForegroundBrightCyan"] = 96] = "ForegroundBrightCyan";
        SGRParam2[SGRParam2["ForegroundBrightWhite"] = 97] = "ForegroundBrightWhite";
        SGRParam2[SGRParam2["BackgroundBrightBlack"] = 100] = "BackgroundBrightBlack";
        SGRParam2[SGRParam2["BackgroundBrightRed"] = 101] = "BackgroundBrightRed";
        SGRParam2[SGRParam2["BackgroundBrightGreen"] = 102] = "BackgroundBrightGreen";
        SGRParam2[SGRParam2["BackgroundBrightYellow"] = 103] = "BackgroundBrightYellow";
        SGRParam2[SGRParam2["BackgroundBrightBlue"] = 104] = "BackgroundBrightBlue";
        SGRParam2[SGRParam2["BackgroundBrightMagenta"] = 105] = "BackgroundBrightMagenta";
        SGRParam2[SGRParam2["BackgroundBrightCyan"] = 106] = "BackgroundBrightCyan";
        SGRParam2[SGRParam2["BackgroundBrightWhite"] = 107] = "BackgroundBrightWhite";
      })(SGRParam || (SGRParam = {}));
      var SGRParamColor;
      (function(SGRParamColor2) {
        SGRParamColor2[SGRParamColor2["Color256"] = 5] = "Color256";
        SGRParamColor2[SGRParamColor2["ColorRGB"] = 2] = "ColorRGB";
      })(SGRParamColor || (SGRParamColor = {}));
      var SGRParamIndexedColor;
      (function(SGRParamIndexedColor2) {
        SGRParamIndexedColor2[SGRParamIndexedColor2["Black"] = 0] = "Black";
        SGRParamIndexedColor2[SGRParamIndexedColor2["Red"] = 1] = "Red";
        SGRParamIndexedColor2[SGRParamIndexedColor2["Green"] = 2] = "Green";
        SGRParamIndexedColor2[SGRParamIndexedColor2["Yellow"] = 3] = "Yellow";
        SGRParamIndexedColor2[SGRParamIndexedColor2["Blue"] = 4] = "Blue";
        SGRParamIndexedColor2[SGRParamIndexedColor2["Magenta"] = 5] = "Magenta";
        SGRParamIndexedColor2[SGRParamIndexedColor2["Cyan"] = 6] = "Cyan";
        SGRParamIndexedColor2[SGRParamIndexedColor2["White"] = 7] = "White";
        SGRParamIndexedColor2[SGRParamIndexedColor2["BrightBlack"] = 8] = "BrightBlack";
        SGRParamIndexedColor2[SGRParamIndexedColor2["BrightRed"] = 9] = "BrightRed";
        SGRParamIndexedColor2[SGRParamIndexedColor2["BrightGreen"] = 10] = "BrightGreen";
        SGRParamIndexedColor2[SGRParamIndexedColor2["BrightYellow"] = 11] = "BrightYellow";
        SGRParamIndexedColor2[SGRParamIndexedColor2["BrightBlue"] = 12] = "BrightBlue";
        SGRParamIndexedColor2[SGRParamIndexedColor2["BrightMagenta"] = 13] = "BrightMagenta";
        SGRParamIndexedColor2[SGRParamIndexedColor2["BrightCyan"] = 14] = "BrightCyan";
        SGRParamIndexedColor2[SGRParamIndexedColor2["BrightWhite"] = 15] = "BrightWhite";
      })(SGRParamIndexedColor || (SGRParamIndexedColor = {}));
      var ParserState;
      (function(ParserState2) {
        ParserState2[ParserState2["BufferingOutput"] = 0] = "BufferingOutput";
        ParserState2[ParserState2["ControlSequenceStarted"] = 1] = "ControlSequenceStarted";
        ParserState2[ParserState2["ParsingControlSequence"] = 2] = "ParsingControlSequence";
      })(ParserState || (ParserState = {}));
      class SGRState {
        //#region Private Properties.
        /**
         * Gets or sets the styles.
         */
        _styles;
        /**
         * Gets or sets the foreground color.
         */
        _foregroundColor;
        /**
         * Gets or sets the background color.
         */
        _backgroundColor;
        /**
         * Gets or sets the underlined color.
         */
        _underlinedColor;
        /**
         * Gets or sets a value which indicates whether the foreground and background colors are
         * reversed.
         */
        _reversed;
        /**
         * Gets or sets the font.
         */
        _font;
        //#endregion Private Properties.
        //#region Public Methods
        /**
         * Resets the SGRState.
         */
        reset() {
          this._styles = void 0;
          this._foregroundColor = void 0;
          this._backgroundColor = void 0;
          this._underlinedColor = void 0;
          this._reversed = void 0;
          this._font = void 0;
        }
        /**
         * Creates a copy of the SGRState.
         * @returns The copy of the SGRState.
         */
        copy() {
          const copy = new SGRState();
          if (this._styles && this._styles.size) {
            const styles2 = /* @__PURE__ */ new Set();
            this._styles.forEach((style2) => styles2.add(style2));
            copy._styles = styles2;
          }
          copy._foregroundColor = this._foregroundColor;
          copy._backgroundColor = this._backgroundColor;
          copy._underlinedColor = this._underlinedColor;
          copy._reversed = this._reversed;
          copy._font = this._font;
          return copy;
        }
        /**
         * Sets a style.
         * @param style The style to set.
         * @param stylesToDelete The styles to delete.
         */
        setStyle(style2, ...stylesToDelete) {
          if (this._styles) {
            for (const style3 of stylesToDelete) {
              this._styles.delete(style3);
            }
          } else {
            this._styles = /* @__PURE__ */ new Set();
          }
          this._styles.add(style2);
        }
        /**
         * Deletes styles.
         * @param stylesToDelete The styles to delete.
         */
        deleteStyles(...stylesToDelete) {
          if (this._styles) {
            for (const style2 of stylesToDelete) {
              this._styles.delete(style2);
            }
            if (!this._styles.size) {
              this._styles = void 0;
            }
          }
        }
        /**
         * Sets the foreground color.
         * @param color The foreground color.
         */
        setForegroundColor(color) {
          if (!this._reversed) {
            this._foregroundColor = color;
          } else {
            this._backgroundColor = color;
          }
        }
        /**
         * Sets the background color.
         * @param color The background color.
         */
        setBackgroundColor(color) {
          if (!this._reversed) {
            this._backgroundColor = color;
          } else {
            this._foregroundColor = color;
          }
        }
        /**
         * Sets reversed.
         * @param reversed A value which indicates whether the foreground and background colors are
         * reversed.
         */
        setReversed(reversed) {
          if (reversed) {
            if (!this._reversed) {
              this._reversed = true;
              this.reverseForegroundAndBackgroundColors();
            }
          } else {
            if (this._reversed) {
              this._reversed = void 0;
              this.reverseForegroundAndBackgroundColors();
            }
          }
        }
        /**
         * Sets the font.
         * @param font The font.
         */
        setFont(font) {
          this._font = font;
        }
        /**
         *
         * @param left
         * @param right
         * @returns
         */
        static equivalent(left, right) {
          const setReplacer = (_, value2) => value2 instanceof Set ? !value2.size ? void 0 : [...value2] : value2;
          return left === right || JSON.stringify(left, setReplacer) === JSON.stringify(right, setReplacer);
        }
        //#endregion Public Methods
        //#region ANSIFormat Implementation
        /**
         * Gets the styles.
         */
        get styles() {
          return !this._styles ? void 0 : [...this._styles];
        }
        /**
         * Gets the foreground color.
         */
        get foregroundColor() {
          if (this._backgroundColor && !this._foregroundColor) {
            switch (this._backgroundColor) {
              case ANSIColor.Black:
              case ANSIColor.BrightBlack:
              case ANSIColor.Red:
              case ANSIColor.BrightRed:
                return ANSIColor.White;
              case ANSIColor.Green:
              case ANSIColor.BrightGreen:
              case ANSIColor.Yellow:
              case ANSIColor.BrightYellow:
              case ANSIColor.Blue:
              case ANSIColor.BrightBlue:
              case ANSIColor.Magenta:
              case ANSIColor.BrightMagenta:
              case ANSIColor.Cyan:
              case ANSIColor.BrightCyan:
              case ANSIColor.White:
              case ANSIColor.BrightWhite:
                return ANSIColor.Black;
            }
          }
          return this._foregroundColor;
        }
        /**
         * Gets the background color.
         */
        get backgroundColor() {
          return this._backgroundColor;
        }
        /**
         * Gets the underlined color.
         */
        get underlinedColor() {
          return this._underlinedColor;
        }
        /**
         * Gets the font.
         */
        get font() {
          return this._font;
        }
        //#endregion ANSIFormat Implementation
        //#region Private Methods
        /**
         * Reverses the foreground and background colors.
         */
        reverseForegroundAndBackgroundColors() {
          const foregroundColor = this._foregroundColor;
          this._foregroundColor = this._backgroundColor;
          this._backgroundColor = foregroundColor;
        }
      }
      class OutputLine {
        //#region Private Properties
        /**
         * Gets the identifier.
         */
        _id = generateId();
        /**
         * Gets or sets the output runs.
         */
        _outputRuns = [];
        /**
         * Gets or sets the total length.
         */
        _totalLength = 0;
        //#endregion Private Properties
        //#region Public Methods
        /**
         * Clears the entire output line.
         */
        clearEntireLine() {
          if (this._totalLength) {
            this._outputRuns = [new OutputRun2(" ".repeat(this._totalLength))];
          }
        }
        /**
         * Clears to the end of the output line.
         * @param column The column at which to clear from.
         */
        clearToEndOfLine(column2) {
          column2 = Math.max(column2, 0);
          if (column2 >= this._totalLength) {
            return;
          }
          if (column2 === 0) {
            this.clearEntireLine();
            return;
          }
          let leftOffset = 0;
          let leftOutputRun;
          let leftOutputRunIndex = void 0;
          for (let index = 0; index < this._outputRuns.length; index++) {
            const outputRun = this._outputRuns[index];
            if (column2 < leftOffset + outputRun.text.length) {
              leftOutputRun = outputRun;
              leftOutputRunIndex = index;
              break;
            }
            leftOffset += outputRun.text.length;
          }
          if (leftOutputRun === void 0 || leftOutputRunIndex === void 0) {
            return;
          }
          const leftTextLength = column2 - leftOffset;
          const erasureText = " ".repeat(this._totalLength - column2);
          const outputRuns = [];
          if (!leftTextLength) {
            outputRuns.push(new OutputRun2(erasureText));
          } else {
            const leftText = leftOutputRun.text.slice(0, leftTextLength);
            outputRuns.push(new OutputRun2(leftText, leftOutputRun.sgrState));
            outputRuns.push(new OutputRun2(erasureText));
          }
          this.outputRuns.splice(leftOutputRunIndex, this._outputRuns.length - leftOutputRunIndex, ...outputRuns);
        }
        /**
         * Clears to the beginning of the output line.
         * @param column The column at which to clear from.
         */
        clearToBeginningOfLine(column2) {
          column2 = Math.max(column2, 0);
          if (column2 === 0) {
            return;
          }
          if (column2 >= this._totalLength) {
            this.clearEntireLine();
            return;
          }
          let rightOffset = 0;
          let rightOutputRun;
          let rightOutputRunIndex = void 0;
          for (let index = this._outputRuns.length - 1; index >= 0; index--) {
            const outputRun = this._outputRuns[index];
            if (column2 >= rightOffset - outputRun.text.length) {
              rightOutputRun = outputRun;
              rightOutputRunIndex = index;
              break;
            }
            rightOffset -= outputRun.text.length;
          }
          if (rightOutputRun === void 0 || rightOutputRunIndex === void 0) {
            return;
          }
          const rightTextLength = rightOffset - column2;
          const erasureText = " ".repeat(column2);
          const outputRuns = [new OutputRun2(erasureText)];
          if (rightTextLength) {
            const rightOutputRunText = rightOutputRun.text.slice(-rightTextLength);
            outputRuns.push(new OutputRun2(rightOutputRunText, rightOutputRun.sgrState));
          }
          this.outputRuns.splice(0, this._outputRuns.length - rightOutputRunIndex, ...outputRuns);
        }
        /**
         * Inserts text into the output line.
         * @param text The text to insert.
         * @param column The column at which to insert the text.
         * @param sgrState The SGR state.
         */
        insert(text2, column2, sgrState) {
          if (!text2.length) {
            return;
          }
          if (column2 === this._totalLength) {
            this._totalLength += text2.length;
            if (this._outputRuns.length) {
              const lastOutputRun = this._outputRuns[this._outputRuns.length - 1];
              if (SGRState.equivalent(lastOutputRun.sgrState, sgrState)) {
                lastOutputRun.appendText(text2);
                return;
              }
            }
            this._outputRuns.push(new OutputRun2(text2, sgrState));
            return;
          }
          if (column2 > this._totalLength) {
            const spacer2 = " ".repeat(column2 - this._totalLength);
            this._totalLength += spacer2.length + text2.length;
            if (!sgrState && this._outputRuns.length) {
              const lastOutputRun = this._outputRuns[this._outputRuns.length - 1];
              if (!lastOutputRun.sgrState) {
                lastOutputRun.appendText(spacer2);
                lastOutputRun.appendText(text2);
                return;
              }
            }
            if (!sgrState) {
              this._outputRuns.push(new OutputRun2(spacer2 + text2));
            } else {
              this._outputRuns.push(new OutputRun2(spacer2));
              this._outputRuns.push(new OutputRun2(text2, sgrState));
            }
          }
          let leftOffset = 0;
          let leftOutputRunIndex = void 0;
          for (let index = 0; index < this._outputRuns.length; index++) {
            const outputRun = this._outputRuns[index];
            if (column2 < leftOffset + outputRun.text.length) {
              leftOutputRunIndex = index;
              break;
            }
            leftOffset += outputRun.text.length;
          }
          if (leftOutputRunIndex === void 0) {
            this._outputRuns.push(new OutputRun2(text2, sgrState));
            return;
          }
          if (column2 + text2.length >= this._totalLength) {
            const leftTextLength = column2 - leftOffset;
            const outputRuns2 = [];
            if (!leftTextLength) {
              outputRuns2.push(new OutputRun2(text2, sgrState));
            } else {
              const leftOutputRun = this._outputRuns[leftOutputRunIndex];
              const leftText = leftOutputRun.text.slice(0, leftTextLength);
              if (SGRState.equivalent(leftOutputRun.sgrState, sgrState)) {
                outputRuns2.push(new OutputRun2(leftText + text2, sgrState));
              } else {
                outputRuns2.push(new OutputRun2(leftText, leftOutputRun.sgrState));
                outputRuns2.push(new OutputRun2(text2, sgrState));
              }
            }
            this.outputRuns.splice(leftOutputRunIndex, 1, ...outputRuns2);
            this._totalLength = leftOffset + leftTextLength + text2.length;
            return;
          }
          let rightOffset = this._totalLength;
          let rightOutputRunIndex = void 0;
          for (let index = this._outputRuns.length - 1; index >= 0; index--) {
            const outputRun = this._outputRuns[index];
            if (column2 + text2.length > rightOffset - outputRun.text.length) {
              rightOutputRunIndex = index;
              break;
            }
            rightOffset -= outputRun.text.length;
          }
          if (rightOutputRunIndex === void 0) {
            this._outputRuns.push(new OutputRun2(text2, sgrState));
            return;
          }
          const outputRuns = [];
          const leftOutputRunTextLength = column2 - leftOffset;
          if (leftOutputRunTextLength) {
            const leftOutputRun = this._outputRuns[leftOutputRunIndex];
            const leftOutputRunText = leftOutputRun.text.slice(0, leftOutputRunTextLength);
            outputRuns.push(new OutputRun2(leftOutputRunText, leftOutputRun.sgrState));
          }
          outputRuns.push(new OutputRun2(text2, sgrState));
          const rightOutputRunTextLength = rightOffset - (column2 + text2.length);
          if (rightOutputRunTextLength) {
            const rightOutputRun = this._outputRuns[rightOutputRunIndex];
            const rightOutputRunText = rightOutputRun.text.slice(-rightOutputRunTextLength);
            outputRuns.push(new OutputRun2(rightOutputRunText, rightOutputRun.sgrState));
          }
          this._outputRuns.splice(leftOutputRunIndex, rightOutputRunIndex - leftOutputRunIndex + 1, ...outputRuns);
          if (this._outputRuns.length > 1) {
            this._outputRuns = OutputRun2.optimizeOutputRuns(this._outputRuns);
          }
          this._totalLength = this._outputRuns.reduce((totalLength, outputRun) => totalLength + outputRun.text.length, 0);
        }
        //#endregion Public Methods
        //#region ANSIOutputLine Implementation
        /**
         * Gets the identifier.
         */
        get id() {
          return this._id;
        }
        /**
         * Gets the output runs.
         */
        get outputRuns() {
          return this._outputRuns;
        }
      }
      class OutputRun2 {
        //#region Private Properties
        /**
         * Gets the identifier.
         */
        _id = generateId();
        /**
         * Gets the SGR state.
         */
        _sgrState;
        /**
         * Gets or sets the text.
         */
        _text;
        //#endregion Private Properties
        //#region Public Properties
        get sgrState() {
          return this._sgrState;
        }
        //#endregion Public Properties
        //#region Constructor
        /**
         * Constructor.
         * @param text The text.
         * @param sgrState The SGR state.
         */
        constructor(text2, sgrState) {
          this._sgrState = sgrState;
          this._text = text2;
        }
        //#endregion Constructor
        //#region Public Methods
        /**
         * Optimizes a an array of output runs by combining adjacent output runs with equivalent SGR
         * states.
         * @param outputRunsIn The output runs to optimize.
         * @returns The optimized output runs.
         */
        static optimizeOutputRuns(outputRunsIn) {
          const outputRunsOut = [outputRunsIn[0]];
          for (let i2 = 1, o = 0; i2 < outputRunsIn.length; i2++) {
            const outputRun = outputRunsIn[i2];
            if (SGRState.equivalent(outputRunsOut[o].sgrState, outputRun.sgrState)) {
              outputRunsOut[o]._text += outputRun.text;
            } else {
              outputRunsOut[++o] = outputRun;
            }
          }
          return outputRunsOut;
        }
        /**
         * Appends text to the end of the output run.
         * @param text The text to append.
         */
        appendText(text2) {
          this._text += text2;
        }
        //#endregion Public Methods
        //#region ANSIOutputRun Implementation
        /**
         * Gets the identifier.
         */
        get id() {
          return this._id;
        }
        /**
         * Gets the format.
         */
        get format() {
          return this._sgrState;
        }
        /**
         * Gets the text.
         */
        get text() {
          return this._text;
        }
      }
      const rangeParam = (value2, defaultValue, minValue) => {
        const param = getParam(value2, defaultValue);
        return Math.max(param, minValue);
      };
      const getParam = (value2, defaultValue) => {
        const param = parseInt(value2);
        return Number.isNaN(param) ? defaultValue : param;
      };
      const twoDigitHex = (value2) => {
        const hex = Math.max(Math.min(255, value2), 0).toString(16);
        return hex.length === 2 ? hex : "0" + hex;
      };
    });
  })(ansiOutput, ansiOutput.exports);
  return ansiOutput.exports;
}
var ansiOutputExports = requireAnsiOutput();
const ansiDisplayContainer = "_ansiDisplayContainer_sawhg_1";
const ansiDisplay = "_ansiDisplay_sawhg_1";
const ansiDisplayRaw = "_ansiDisplayRaw_sawhg_28";
const ansiDisplayToggle = "_ansiDisplayToggle_sawhg_33";
const styles$M = {
  ansiDisplayContainer,
  ansiDisplay,
  ansiDisplayRaw,
  ansiDisplayToggle
};
const ANSIDisplay = ({
  output: output2,
  style: style2,
  className: className2
}) => {
  const [showRaw, setShowRaw] = reactExports.useState(false);
  const ansiOutput2 = new ansiOutputExports.ANSIOutput();
  ansiOutput2.processOutput(output2);
  const getUniformBackgroundColor = () => {
    const backgroundColorCounts = /* @__PURE__ */ new Map();
    let totalLinesWithBackground = 0;
    for (const line of ansiOutput2.outputLines) {
      let lineBackgroundColor = void 0;
      for (const run of line.outputRuns) {
        if (run.format?.backgroundColor) {
          lineBackgroundColor = run.format.backgroundColor;
          break;
        }
      }
      if (lineBackgroundColor) {
        totalLinesWithBackground++;
        backgroundColorCounts.set(
          lineBackgroundColor,
          (backgroundColorCounts.get(lineBackgroundColor) || 0) + 1
        );
      }
    }
    if (totalLinesWithBackground === 0) {
      return void 0;
    }
    const backgroundColorPercentages = /* @__PURE__ */ new Map();
    for (const [color, count] of backgroundColorCounts.entries()) {
      backgroundColorPercentages.set(color, count / totalLinesWithBackground);
    }
    let dominantColor = void 0;
    let maxPercentage = 0;
    for (const [color, percentage] of backgroundColorPercentages.entries()) {
      if (percentage > maxPercentage) {
        maxPercentage = percentage;
        dominantColor = color;
      }
    }
    return maxPercentage > 0.8 ? dominantColor : void 0;
  };
  const uniformBackgroundColor = getUniformBackgroundColor();
  const backgroundStyle = uniformBackgroundColor ? computeForegroundBackgroundColor(kBackground, uniformBackgroundColor) : {};
  let firstOutput = false;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: clsx(styles$M.ansiDisplayContainer, className2),
      style: { ...style2 },
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ToolButton,
          {
            className: clsx(styles$M.ansiDisplayToggle, "text-size-smallest"),
            icon: "bi bi-code-slash",
            label: "",
            latched: showRaw,
            onClick: () => setShowRaw(!showRaw),
            title: showRaw ? "Show rendered output" : "Show raw output"
          }
        ),
        showRaw ? /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: clsx(styles$M.ansiDisplay, styles$M.ansiDisplayRaw), children: output2 }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$M.ansiDisplay), style: backgroundStyle, children: ansiOutput2.outputLines.map((line, index) => {
          firstOutput = firstOutput || !!line.outputRuns.length;
          return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$M.ansiDisplayLine), children: !line.outputRuns.length ? firstOutput ? /* @__PURE__ */ jsxRuntimeExports.jsx("br", {}) : null : line.outputRuns.map((outputRun) => /* @__PURE__ */ jsxRuntimeExports.jsx(OutputRun, { run: outputRun }, outputRun.id)) }, index);
        }) })
      ]
    }
  );
};
const kForeground = 0;
const kBackground = 1;
const OutputRun = ({ run }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { style: computeCSSProperties(run), children: run.text });
};
const computeCSSProperties = (outputRun) => {
  return !outputRun.format ? {} : {
    ...computeStyles(outputRun.format.styles || []),
    ...computeForegroundBackgroundColor(
      kForeground,
      outputRun.format.foregroundColor
    ),
    ...computeForegroundBackgroundColor(
      kBackground,
      outputRun.format.backgroundColor
    )
  };
};
const computeStyles = (styles2) => {
  let cssProperties = {};
  if (styles2) {
    styles2.forEach((style2) => {
      switch (style2) {
        // Bold.
        case ansiOutputExports.ANSIStyle.Bold:
          cssProperties = { ...cssProperties, ...{ fontWeight: "bold" } };
          break;
        // Dim.
        case ansiOutputExports.ANSIStyle.Dim:
          cssProperties = { ...cssProperties, ...{ fontWeight: "lighter" } };
          break;
        // Italic.
        case ansiOutputExports.ANSIStyle.Italic:
          cssProperties = { ...cssProperties, ...{ fontStyle: "italic" } };
          break;
        // Underlined.
        case ansiOutputExports.ANSIStyle.Underlined:
          cssProperties = {
            ...cssProperties,
            ...{
              textDecorationLine: "underline",
              textDecorationStyle: "solid"
            }
          };
          break;
        // Slow blink.
        case ansiOutputExports.ANSIStyle.SlowBlink:
          cssProperties = {
            ...cssProperties,
            ...{ animation: "ansi-display-run-blink 1s linear infinite" }
          };
          break;
        // Rapid blink.
        case ansiOutputExports.ANSIStyle.RapidBlink:
          cssProperties = {
            ...cssProperties,
            ...{ animation: "ansi-display-run-blink 0.5s linear infinite" }
          };
          break;
        // Hidden.
        case ansiOutputExports.ANSIStyle.Hidden:
          cssProperties = { ...cssProperties, ...{ visibility: "hidden" } };
          break;
        // CrossedOut.
        case ansiOutputExports.ANSIStyle.CrossedOut:
          cssProperties = {
            ...cssProperties,
            ...{
              textDecorationLine: "line-through",
              textDecorationStyle: "solid"
            }
          };
          break;
        // TODO Fraktur
        // DoubleUnderlined.
        case ansiOutputExports.ANSIStyle.DoubleUnderlined:
          cssProperties = {
            ...cssProperties,
            ...{
              textDecorationLine: "underline",
              textDecorationStyle: "double"
            }
          };
          break;
      }
    });
  }
  return cssProperties;
};
const computeForegroundBackgroundColor = (colorType, color) => {
  switch (color) {
    // Undefined.
    case void 0:
      return {};
    // One of the standard colors.
    case ansiOutputExports.ANSIColor.Black:
    case ansiOutputExports.ANSIColor.Red:
    case ansiOutputExports.ANSIColor.Green:
    case ansiOutputExports.ANSIColor.Yellow:
    case ansiOutputExports.ANSIColor.Blue:
    case ansiOutputExports.ANSIColor.Magenta:
    case ansiOutputExports.ANSIColor.Cyan:
    case ansiOutputExports.ANSIColor.White:
    case ansiOutputExports.ANSIColor.BrightBlack:
    case ansiOutputExports.ANSIColor.BrightRed:
    case ansiOutputExports.ANSIColor.BrightGreen:
    case ansiOutputExports.ANSIColor.BrightYellow:
    case ansiOutputExports.ANSIColor.BrightBlue:
    case ansiOutputExports.ANSIColor.BrightMagenta:
    case ansiOutputExports.ANSIColor.BrightCyan:
    case ansiOutputExports.ANSIColor.BrightWhite:
      if (colorType === kForeground) {
        return { color: `var(--${color})` };
      } else {
        return { background: `var(--${color})` };
      }
    // TODO@softwarenerd - This isn't hooked up.
    default:
      if (colorType === kForeground) {
        return { color };
      } else {
        return { background: color };
      }
  }
};
const Buckets = {
  first: 0,
  intermediate: 10,
  final: 1e3
};
function useProperty(id, propertyName, options) {
  const defaultValue = options?.defaultValue;
  const cleanup = options?.cleanup ?? true;
  const setPropertyValue = useStore((state) => state.setPropertyValue);
  const removePropertyValue = useStore((state) => state.removePropertyValue);
  const propertyValue = useStore(
    reactExports.useCallback(
      (state) => state.getPropertyValue(id, propertyName, defaultValue),
      [id, propertyName, defaultValue]
    )
  );
  const setValue = reactExports.useCallback(
    (value2) => {
      setPropertyValue(id, propertyName, value2);
    },
    [id, propertyName, setPropertyValue]
  );
  const removeValue = reactExports.useCallback(() => {
    removePropertyValue(id, propertyName);
  }, [id, propertyName, removePropertyValue]);
  reactExports.useEffect(() => {
    return () => {
      if (cleanup) {
        removePropertyValue(id, propertyName);
      }
    };
  }, [id, propertyName, removePropertyValue, cleanup]);
  return [propertyValue, setValue, removeValue];
}
const visible = "_visible_tm52u_1";
const hidden$1 = "_hidden_tm52u_5";
const pills = "_pills_tm52u_9";
const pill = "_pill_tm52u_9";
const styles$L = {
  visible,
  hidden: hidden$1,
  pills,
  pill
};
const NavPills = ({ id, children: children2 }) => {
  const defaultNav = children2 ? children2?.[0]?.props["title"] : "";
  const [activeItem, setActiveItem] = useProperty(id, "active", {
    defaultValue: defaultNav
  });
  if (!activeItem || !children2) {
    return void 0;
  }
  const navPills = children2.map((nav, idx) => {
    const title2 = typeof nav === "object" ? nav["props"]?.title || `Tab ${idx}` : `Tab ${idx}`;
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      NavPill,
      {
        title: title2,
        activeItem,
        setActiveItem
      },
      `nav-pill-contents-${idx}`
    );
  });
  const navBodies = children2.map((child, idx) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: child["props"]?.title === activeItem ? styles$L.visible : styles$L.hidden,
        children: child
      },
      `nav-pill-container-${idx}`
    );
  });
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "ul",
      {
        className: clsx("nav", "nav-pills", styles$L.pills),
        role: "tablist",
        "aria-orientation": "horizontal",
        children: navPills
      }
    ),
    navBodies
  ] });
};
const NavPill = ({
  title: title2,
  activeItem,
  setActiveItem,
  children: children2
}) => {
  const active = activeItem === title2;
  const handleClick = reactExports.useCallback(
    (e) => {
      const target = e.currentTarget.dataset.target;
      if (target) {
        setActiveItem(target);
      }
    },
    [setActiveItem]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "nav-item", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        type: "button",
        role: "tab",
        "aria-selected": active,
        className: clsx(
          "nav-link",
          "text-style-label",
          active ? "active " : "",
          styles$L.pill
        ),
        "data-target": title2,
        onClick: handleClick,
        children: title2
      }
    ),
    children2
  ] });
};
const toFullUrl = (route) => {
  return `${window.location.origin}${window.location.pathname}#${route}`;
};
const useTranscriptNavigation = () => {
  const params = useParams();
  const { transcriptsDir, transcriptId } = parseTranscriptParams(params);
  const [searchParams] = useSearchParams();
  const getEventUrl = reactExports.useCallback(
    (eventId) => {
      if (!transcriptsDir || !transcriptId) return void 0;
      const newParams = new URLSearchParams(searchParams);
      newParams.set("tab", "transcript-events");
      newParams.set("event", eventId);
      newParams.delete("message");
      return transcriptRoute(transcriptsDir, transcriptId, newParams);
    },
    [transcriptsDir, transcriptId, searchParams]
  );
  const getMessageUrl = reactExports.useCallback(
    (messageId) => {
      if (!transcriptsDir || !transcriptId) return void 0;
      const newParams = new URLSearchParams(searchParams);
      newParams.set("tab", "transcript-messages");
      newParams.set("message", messageId);
      newParams.delete("event");
      return transcriptRoute(transcriptsDir, transcriptId, newParams);
    },
    [transcriptsDir, transcriptId, searchParams]
  );
  const getFullEventUrl = reactExports.useCallback(
    (eventId) => {
      const route = getEventUrl(eventId);
      return route ? toFullUrl(route) : void 0;
    },
    [getEventUrl]
  );
  const getFullMessageUrl = reactExports.useCallback(
    (messageId) => {
      const route = getMessageUrl(messageId);
      return route ? toFullUrl(route) : void 0;
    },
    [getMessageUrl]
  );
  return { getEventUrl, getMessageUrl, getFullEventUrl, getFullMessageUrl };
};
const ve = 0, At = 1, Jt = 2, zn = 4;
function un(t2) {
  return () => t2;
}
function mo(t2) {
  t2();
}
function se(t2, e) {
  return (n2) => t2(e(n2));
}
function an(t2, e) {
  return () => t2(e);
}
function po(t2, e) {
  return (n2) => t2(e, n2);
}
function Ae(t2) {
  return t2 !== void 0;
}
function ho(...t2) {
  return () => {
    t2.map(mo);
  };
}
function Qt() {
}
function ye(t2, e) {
  return e(t2), t2;
}
function go(t2, e) {
  return e(t2);
}
function tt(...t2) {
  return t2;
}
function Y(t2, e) {
  return t2(At, e);
}
function D(t2, e) {
  t2(ve, e);
}
function We(t2) {
  t2(Jt);
}
function rt(t2) {
  return t2(zn);
}
function F(t2, e) {
  return Y(t2, po(e, ve));
}
function Et(t2, e) {
  const n2 = t2(At, (o) => {
    n2(), e(o);
  });
  return n2;
}
function dn(t2) {
  let e, n2;
  return (o) => (r2) => {
    e = r2, n2 && clearTimeout(n2), n2 = setTimeout(() => {
      o(e);
    }, t2);
  };
}
function On(t2, e) {
  return t2 === e;
}
function J(t2 = On) {
  let e;
  return (n2) => (o) => {
    t2(e, o) || (e = o, n2(o));
  };
}
function P$1(t2) {
  return (e) => (n2) => {
    t2(n2) && e(n2);
  };
}
function k(t2) {
  return (e) => se(e, t2);
}
function Ft(t2) {
  return (e) => () => {
    e(t2);
  };
}
function x(t2, ...e) {
  const n2 = Io(...e);
  return ((o, r2) => {
    switch (o) {
      case Jt:
        We(t2);
        return;
      case At:
        return Y(t2, n2(r2));
    }
  });
}
function Lt(t2, e) {
  return (n2) => (o) => {
    n2(e = t2(e, o));
  };
}
function Kt(t2) {
  return (e) => (n2) => {
    t2 > 0 ? t2-- : e(n2);
  };
}
function Gt(t2) {
  let e = null, n2;
  return (o) => (r2) => {
    e = r2, !n2 && (n2 = setTimeout(() => {
      n2 = void 0, o(e);
    }, t2));
  };
}
function $(...t2) {
  const e = new Array(t2.length);
  let n2 = 0, o = null;
  const r2 = Math.pow(2, t2.length) - 1;
  return t2.forEach((s, i2) => {
    const l2 = Math.pow(2, i2);
    Y(s, (u) => {
      const d = n2;
      n2 = n2 | l2, e[i2] = u, d !== r2 && n2 === r2 && o && (o(), o = null);
    });
  }), (s) => (i2) => {
    const l2 = () => {
      s([i2].concat(e));
    };
    n2 === r2 ? l2() : o = l2;
  };
}
function Io(...t2) {
  return (e) => t2.reduceRight(go, e);
}
function xo(t2) {
  let e, n2;
  const o = () => e == null ? void 0 : e();
  return function(r2, s) {
    switch (r2) {
      case At:
        return s ? n2 === s ? void 0 : (o(), n2 = s, e = Y(t2, s), e) : (o(), Qt);
      case Jt:
        o(), n2 = null;
        return;
    }
  };
}
function C(t2) {
  let e = t2;
  const n2 = U();
  return ((o, r2) => {
    switch (o) {
      case ve:
        e = r2;
        break;
      case At: {
        r2(e);
        break;
      }
      case zn:
        return e;
    }
    return n2(o, r2);
  });
}
function ht(t2, e) {
  return ye(C(e), (n2) => F(t2, n2));
}
function U() {
  const t2 = [];
  return ((e, n2) => {
    switch (e) {
      case ve:
        t2.slice().forEach((o) => {
          o(n2);
        });
        return;
      case Jt:
        t2.splice(0, t2.length);
        return;
      case At:
        return t2.push(n2), () => {
          const o = t2.indexOf(n2);
          o > -1 && t2.splice(o, 1);
        };
    }
  });
}
function bt(t2) {
  return ye(U(), (e) => F(t2, e));
}
function K(t2, e = [], { singleton: n2 } = { singleton: true }) {
  return {
    constructor: t2,
    dependencies: e,
    id: So(),
    singleton: n2
  };
}
const So = () => /* @__PURE__ */ Symbol();
function To(t2) {
  const e = /* @__PURE__ */ new Map(), n2 = ({ constructor: o, dependencies: r2, id: s, singleton: i2 }) => {
    if (i2 && e.has(s))
      return e.get(s);
    const l2 = o(r2.map((u) => n2(u)));
    return i2 && e.set(s, l2), l2;
  };
  return n2(t2);
}
function ut(...t2) {
  const e = U(), n2 = new Array(t2.length);
  let o = 0;
  const r2 = Math.pow(2, t2.length) - 1;
  return t2.forEach((s, i2) => {
    const l2 = Math.pow(2, i2);
    Y(s, (u) => {
      n2[i2] = u, o = o | l2, o === r2 && D(e, n2);
    });
  }), function(s, i2) {
    switch (s) {
      case Jt: {
        We(e);
        return;
      }
      case At:
        return o === r2 && i2(n2), Y(e, i2);
    }
  };
}
function V(t2, e = On) {
  return x(t2, J(e));
}
function Fe(...t2) {
  return function(e, n2) {
    switch (e) {
      case Jt:
        return;
      case At:
        return ho(...t2.map((o) => Y(o, n2)));
    }
  };
}
var Ct = /* @__PURE__ */ ((t2) => (t2[t2.DEBUG = 0] = "DEBUG", t2[t2.INFO = 1] = "INFO", t2[t2.WARN = 2] = "WARN", t2[t2.ERROR = 3] = "ERROR", t2))(Ct || {});
const Co = {
  0: "debug",
  3: "error",
  1: "log",
  2: "warn"
}, wo = () => typeof globalThis > "u" ? window : globalThis, Wt = K(
  () => {
    const t2 = C(
      3
      /* ERROR */
    );
    return {
      log: C((n2, o, r2 = 1) => {
        var i2;
        const s = (i2 = wo().VIRTUOSO_LOG_LEVEL) != null ? i2 : rt(t2);
        r2 >= s && console[Co[r2]](
          "%creact-virtuoso: %c%s %o",
          "color: #0253b3; font-weight: bold",
          "color: initial",
          n2,
          o
        );
      }),
      logLevel: t2
    };
  },
  [],
  { singleton: true }
);
function Vt$1(t2, e, n2) {
  return _e(t2, e, n2).callbackRef;
}
function _e(t2, e, n2) {
  const o = E.useRef(null);
  let r2 = (i2) => {
  };
  const s = E.useMemo(() => typeof ResizeObserver < "u" ? new ResizeObserver((i2) => {
    const l2 = () => {
      const u = i2[0].target;
      u.offsetParent !== null && t2(u);
    };
    n2 ? l2() : requestAnimationFrame(l2);
  }) : null, [t2, n2]);
  return r2 = (i2) => {
    i2 && e ? (s == null || s.observe(i2), o.current = i2) : (o.current && (s == null || s.unobserve(o.current)), o.current = null);
  }, { callbackRef: r2, ref: o };
}
function Fn(t2, e, n2, o, r2, s, i2, l2, u) {
  const d = E.useCallback(
    (m) => {
      const S = vo(m.children, e, l2 ? "offsetWidth" : "offsetHeight", r2);
      let h = m.parentElement;
      for (; !h.dataset.virtuosoScroller; )
        h = h.parentElement;
      const T = h.lastElementChild.dataset.viewportType === "window";
      let w;
      T && (w = h.ownerDocument.defaultView);
      const R = i2 ? l2 ? i2.scrollLeft : i2.scrollTop : T ? l2 ? w.scrollX || w.document.documentElement.scrollLeft : w.scrollY || w.document.documentElement.scrollTop : l2 ? h.scrollLeft : h.scrollTop, g = i2 ? l2 ? i2.scrollWidth : i2.scrollHeight : T ? l2 ? w.document.documentElement.scrollWidth : w.document.documentElement.scrollHeight : l2 ? h.scrollWidth : h.scrollHeight, f = i2 ? l2 ? i2.offsetWidth : i2.offsetHeight : T ? l2 ? w.innerWidth : w.innerHeight : l2 ? h.offsetWidth : h.offsetHeight;
      o({
        scrollHeight: g,
        scrollTop: Math.max(R, 0),
        viewportHeight: f
      }), s == null || s(
        l2 ? fn("column-gap", getComputedStyle(m).columnGap, r2) : fn("row-gap", getComputedStyle(m).rowGap, r2)
      ), S !== null && t2(S);
    },
    [t2, e, r2, s, i2, o, l2]
  );
  return _e(d, n2, u);
}
function vo(t2, e, n2, o) {
  const r2 = t2.length;
  if (r2 === 0)
    return null;
  const s = [];
  for (let i2 = 0; i2 < r2; i2++) {
    const l2 = t2.item(i2);
    if (l2.dataset.index === void 0)
      continue;
    const u = parseInt(l2.dataset.index), d = parseFloat(l2.dataset.knownSize), m = e(l2, n2);
    if (m === 0 && o("Zero-sized element, this should not happen", { child: l2 }, Ct.ERROR), m === d)
      continue;
    const S = s[s.length - 1];
    s.length === 0 || S.size !== m || S.endIndex !== u - 1 ? s.push({ endIndex: u, size: m, startIndex: u }) : s[s.length - 1].endIndex++;
  }
  return s;
}
function fn(t2, e, n2) {
  return e !== "normal" && !(e != null && e.endsWith("px")) && n2(`${t2} was not resolved to pixel value correctly`, e, Ct.WARN), e === "normal" ? 0 : parseInt(e != null ? e : "0", 10);
}
function Ne(t2, e, n2) {
  const o = E.useRef(null), r2 = E.useCallback(
    (u) => {
      if (!(u != null && u.offsetParent))
        return;
      const d = u.getBoundingClientRect(), m = d.width;
      let S, h;
      if (e) {
        const T = e.getBoundingClientRect(), w = d.top - T.top;
        h = T.height - Math.max(0, w), S = w + e.scrollTop;
      } else {
        const T = i2.current.ownerDocument.defaultView;
        h = T.innerHeight - Math.max(0, d.top), S = d.top + T.scrollY;
      }
      o.current = {
        offsetTop: S,
        visibleHeight: h,
        visibleWidth: m
      }, t2(o.current);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [t2, e]
  ), { callbackRef: s, ref: i2 } = _e(r2, true, n2), l2 = E.useCallback(() => {
    r2(i2.current);
  }, [r2, i2]);
  return E.useEffect(() => {
    var u;
    if (e) {
      e.addEventListener("scroll", l2);
      const d = new ResizeObserver(() => {
        requestAnimationFrame(l2);
      });
      return d.observe(e), () => {
        e.removeEventListener("scroll", l2), d.unobserve(e);
      };
    } else {
      const d = (u = i2.current) == null ? void 0 : u.ownerDocument.defaultView;
      return d == null || d.addEventListener("scroll", l2), d == null || d.addEventListener("resize", l2), () => {
        d == null || d.removeEventListener("scroll", l2), d == null || d.removeEventListener("resize", l2);
      };
    }
  }, [l2, e, i2]), s;
}
const It = K(
  () => {
    const t2 = U(), e = U(), n2 = C(0), o = U(), r2 = C(0), s = U(), i2 = U(), l2 = C(0), u = C(0), d = C(0), m = C(0), S = U(), h = U(), T = C(false), w = C(false), R = C(false);
    return F(
      x(
        t2,
        k(({ scrollTop: g }) => g)
      ),
      e
    ), F(
      x(
        t2,
        k(({ scrollHeight: g }) => g)
      ),
      i2
    ), F(e, r2), {
      deviation: n2,
      fixedFooterHeight: d,
      fixedHeaderHeight: u,
      footerHeight: m,
      headerHeight: l2,
      horizontalDirection: w,
      scrollBy: h,
      // input
      scrollContainerState: t2,
      scrollHeight: i2,
      scrollingInProgress: T,
      // signals
      scrollTo: S,
      scrollTop: e,
      skipAnimationFrameInResizeObserver: R,
      smoothScrollTargetReached: o,
      // state
      statefulScrollTop: r2,
      viewportHeight: s
    };
  },
  [],
  { singleton: true }
), ie = { lvl: 0 };
function Ln(t2, e) {
  const n2 = t2.length;
  if (n2 === 0)
    return [];
  let { index: o, value: r2 } = e(t2[0]);
  const s = [];
  for (let i2 = 1; i2 < n2; i2++) {
    const { index: l2, value: u } = e(t2[i2]);
    s.push({ end: l2 - 1, start: o, value: r2 }), o = l2, r2 = u;
  }
  return s.push({ end: 1 / 0, start: o, value: r2 }), s;
}
function X(t2) {
  return t2 === ie;
}
function le(t2, e) {
  if (!X(t2))
    return e === t2.k ? t2.v : e < t2.k ? le(t2.l, e) : le(t2.r, e);
}
function kt(t2, e, n2 = "k") {
  if (X(t2))
    return [-1 / 0, void 0];
  if (Number(t2[n2]) === e)
    return [t2.k, t2.v];
  if (Number(t2[n2]) < e) {
    const o = kt(t2.r, e, n2);
    return o[0] === -1 / 0 ? [t2.k, t2.v] : o;
  }
  return kt(t2.l, e, n2);
}
function yt(t2, e, n2) {
  return X(t2) ? Gn(e, n2, 1) : e === t2.k ? dt(t2, { k: e, v: n2 }) : e < t2.k ? mn(dt(t2, { l: yt(t2.l, e, n2) })) : mn(dt(t2, { r: yt(t2.r, e, n2) }));
}
function Zt() {
  return ie;
}
function Xt(t2, e, n2) {
  if (X(t2))
    return [];
  const o = kt(t2, e)[0];
  return yo(Ve(t2, o, n2));
}
function Le(t2, e) {
  if (X(t2)) return ie;
  const { k: n2, l: o, r: r2 } = t2;
  if (e === n2) {
    if (X(o))
      return r2;
    if (X(r2))
      return o;
    {
      const [s, i2] = Pn(o);
      return Se(dt(t2, { k: s, l: Vn(o), v: i2 }));
    }
  } else return e < n2 ? Se(dt(t2, { l: Le(o, e) })) : Se(dt(t2, { r: Le(r2, e) }));
}
function Dt(t2) {
  return X(t2) ? [] : [...Dt(t2.l), { k: t2.k, v: t2.v }, ...Dt(t2.r)];
}
function Ve(t2, e, n2) {
  if (X(t2))
    return [];
  const { k: o, l: r2, r: s, v: i2 } = t2;
  let l2 = [];
  return o > e && (l2 = l2.concat(Ve(r2, e, n2))), o >= e && o <= n2 && l2.push({ k: o, v: i2 }), o <= n2 && (l2 = l2.concat(Ve(s, e, n2))), l2;
}
function Se(t2) {
  const { l: e, lvl: n2, r: o } = t2;
  if (o.lvl >= n2 - 1 && e.lvl >= n2 - 1)
    return t2;
  if (n2 > o.lvl + 1) {
    if (Ee(e))
      return Mn(dt(t2, { lvl: n2 - 1 }));
    if (!X(e) && !X(e.r))
      return dt(e.r, {
        l: dt(e, { r: e.r.l }),
        lvl: n2,
        r: dt(t2, {
          l: e.r.r,
          lvl: n2 - 1
        })
      });
    throw new Error("Unexpected empty nodes");
  } else {
    if (Ee(t2))
      return Pe(dt(t2, { lvl: n2 - 1 }));
    if (!X(o) && !X(o.l)) {
      const r2 = o.l, s = Ee(r2) ? o.lvl - 1 : o.lvl;
      return dt(r2, {
        l: dt(t2, {
          lvl: n2 - 1,
          r: r2.l
        }),
        lvl: r2.lvl + 1,
        r: Pe(dt(o, { l: r2.r, lvl: s }))
      });
    } else
      throw new Error("Unexpected empty nodes");
  }
}
function dt(t2, e) {
  return Gn(
    e.k !== void 0 ? e.k : t2.k,
    e.v !== void 0 ? e.v : t2.v,
    e.lvl !== void 0 ? e.lvl : t2.lvl,
    e.l !== void 0 ? e.l : t2.l,
    e.r !== void 0 ? e.r : t2.r
  );
}
function Vn(t2) {
  return X(t2.r) ? t2.l : Se(dt(t2, { r: Vn(t2.r) }));
}
function Ee(t2) {
  return X(t2) || t2.lvl > t2.r.lvl;
}
function Pn(t2) {
  return X(t2.r) ? [t2.k, t2.v] : Pn(t2.r);
}
function Gn(t2, e, n2, o = ie, r2 = ie) {
  return { k: t2, l: o, lvl: n2, r: r2, v: e };
}
function mn(t2) {
  return Pe(Mn(t2));
}
function Mn(t2) {
  const { l: e } = t2;
  return !X(e) && e.lvl === t2.lvl ? dt(e, { r: dt(t2, { l: e.r }) }) : t2;
}
function Pe(t2) {
  const { lvl: e, r: n2 } = t2;
  return !X(n2) && !X(n2.r) && n2.lvl === e && n2.r.lvl === e ? dt(n2, { l: dt(t2, { r: n2.l }), lvl: e + 1 }) : t2;
}
function yo(t2) {
  return Ln(t2, ({ k: e, v: n2 }) => ({ index: e, value: n2 }));
}
function An(t2, e) {
  return !!(t2 && t2.startIndex === e.startIndex && t2.endIndex === e.endIndex);
}
function ce(t2, e) {
  return !!(t2 && t2[0] === e[0] && t2[1] === e[1]);
}
const De = K(
  () => ({ recalcInProgress: C(false) }),
  [],
  { singleton: true }
);
function Wn(t2, e, n2) {
  return t2[Ce(t2, e, n2)];
}
function Ce(t2, e, n2, o = 0) {
  let r2 = t2.length - 1;
  for (; o <= r2; ) {
    const s = Math.floor((o + r2) / 2), i2 = t2[s], l2 = n2(i2, e);
    if (l2 === 0)
      return s;
    if (l2 === -1) {
      if (r2 - o < 2)
        return s - 1;
      r2 = s - 1;
    } else {
      if (r2 === o)
        return s;
      o = s + 1;
    }
  }
  throw new Error(`Failed binary finding record in array - ${t2.join(",")}, searched for ${e}`);
}
function bo(t2, e, n2, o) {
  const r2 = Ce(t2, e, o), s = Ce(t2, n2, o, r2);
  return t2.slice(r2, s + 1);
}
function zt(t2, e) {
  return Math.round(t2.getBoundingClientRect()[e]);
}
function be(t2) {
  return !X(t2.groupOffsetTree);
}
function $e({ index: t2 }, e) {
  return e === t2 ? 0 : e < t2 ? -1 : 1;
}
function Ro() {
  return {
    groupIndices: [],
    groupOffsetTree: Zt(),
    lastIndex: 0,
    lastOffset: 0,
    lastSize: 0,
    offsetTree: [],
    sizeTree: Zt()
  };
}
function Ho(t2, e) {
  let n2 = X(t2) ? 0 : 1 / 0;
  for (const o of e) {
    const { endIndex: r2, size: s, startIndex: i2 } = o;
    if (n2 = Math.min(n2, i2), X(t2)) {
      t2 = yt(t2, 0, s);
      continue;
    }
    const l2 = Xt(t2, i2 - 1, r2 + 1);
    if (l2.some(Lo(o)))
      continue;
    let u = false, d = false;
    for (const { end: m, start: S, value: h } of l2)
      u ? (r2 >= S || s === h) && (t2 = Le(t2, S)) : (d = h !== s, u = true), m > r2 && r2 >= S && h !== s && (t2 = yt(t2, r2 + 1, h));
    d && (t2 = yt(t2, i2, s));
  }
  return [t2, n2];
}
function Eo(t2) {
  return typeof t2.groupIndex < "u";
}
function Bo({ offset: t2 }, e) {
  return e === t2 ? 0 : e < t2 ? -1 : 1;
}
function ue(t2, e, n2) {
  if (e.length === 0)
    return 0;
  const { index: o, offset: r2, size: s } = Wn(e, t2, $e), i2 = t2 - o, l2 = s * i2 + (i2 - 1) * n2 + r2;
  return l2 > 0 ? l2 + n2 : l2;
}
function _n(t2, e) {
  if (!be(e))
    return t2;
  let n2 = 0;
  for (; e.groupIndices[n2] <= t2 + n2; )
    n2++;
  return t2 + n2;
}
function Nn(t2, e, n2) {
  if (Eo(t2))
    return e.groupIndices[t2.groupIndex] + 1;
  {
    const o = t2.index === "LAST" ? n2 : t2.index;
    let r2 = _n(o, e);
    return r2 = Math.max(0, r2, Math.min(n2, r2)), r2;
  }
}
function ko(t2, e, n2, o = 0) {
  return o > 0 && (e = Math.max(e, Wn(t2, o, $e).offset)), Ln(bo(t2, e, n2, Bo), Fo);
}
function zo(t2, [e, n2, o, r2]) {
  e.length > 0 && o("received item sizes", e, Ct.DEBUG);
  const s = t2.sizeTree;
  let i2 = s, l2 = 0;
  if (n2.length > 0 && X(s) && e.length === 2) {
    const h = e[0].size, T = e[1].size;
    i2 = n2.reduce((w, R) => yt(yt(w, R, h), R + 1, T), i2);
  } else
    [i2, l2] = Ho(i2, e);
  if (i2 === s)
    return t2;
  const { lastIndex: u, lastOffset: d, lastSize: m, offsetTree: S } = Ge(t2.offsetTree, l2, i2, r2);
  return {
    groupIndices: n2,
    groupOffsetTree: n2.reduce((h, T) => yt(h, T, ue(T, S, r2)), Zt()),
    lastIndex: u,
    lastOffset: d,
    lastSize: m,
    offsetTree: S,
    sizeTree: i2
  };
}
function Oo(t2) {
  return Dt(t2).map(({ k: e, v: n2 }, o, r2) => {
    const s = r2[o + 1];
    return { endIndex: s ? s.k - 1 : 1 / 0, size: n2, startIndex: e };
  });
}
function pn(t2, e) {
  let n2 = 0, o = 0;
  for (; n2 < t2; )
    n2 += e[o + 1] - e[o] - 1, o++;
  return o - (n2 === t2 ? 0 : 1);
}
function Ge(t2, e, n2, o) {
  let r2 = t2, s = 0, i2 = 0, l2 = 0, u = 0;
  if (e !== 0) {
    u = Ce(r2, e - 1, $e), l2 = r2[u].offset;
    const m = kt(n2, e - 1);
    s = m[0], i2 = m[1], r2.length && r2[u].size === kt(n2, e)[1] && (u -= 1), r2 = r2.slice(0, u + 1);
  } else
    r2 = [];
  for (const { start: d, value: m } of Xt(n2, e, 1 / 0)) {
    const S = d - s, h = S * i2 + l2 + S * o;
    r2.push({
      index: d,
      offset: h,
      size: m
    }), s = d, l2 = h, i2 = m;
  }
  return {
    lastIndex: s,
    lastOffset: l2,
    lastSize: i2,
    offsetTree: r2
  };
}
function Fo(t2) {
  return { index: t2.index, value: t2 };
}
function Lo(t2) {
  const { endIndex: e, size: n2, startIndex: o } = t2;
  return (r2) => r2.start === o && (r2.end === e || r2.end === 1 / 0) && r2.value === n2;
}
const Vo = {
  offsetHeight: "height",
  offsetWidth: "width"
}, Pt = K(
  ([{ log: t2 }, { recalcInProgress: e }]) => {
    const n2 = U(), o = U(), r2 = ht(o, 0), s = U(), i2 = U(), l2 = C(0), u = C([]), d = C(void 0), m = C(void 0), S = C(void 0), h = C(void 0), T = C((c, p) => zt(c, Vo[p])), w = C(void 0), R = C(0), g = Ro(), f = ht(
      x(n2, $(u, t2, R), Lt(zo, g), J()),
      g
    ), a2 = ht(
      x(
        u,
        J(),
        Lt((c, p) => ({ current: p, prev: c.current }), {
          current: [],
          prev: []
        }),
        k(({ prev: c }) => c)
      ),
      []
    );
    F(
      x(
        u,
        P$1((c) => c.length > 0),
        $(f, R),
        k(([c, p, v]) => {
          const O = c.reduce((B, W, _) => yt(B, W, ue(W, p.offsetTree, v) || _), Zt());
          return {
            ...p,
            groupIndices: c,
            groupOffsetTree: O
          };
        })
      ),
      f
    ), F(
      x(
        o,
        $(f),
        P$1(([c, { lastIndex: p }]) => c < p),
        k(([c, { lastIndex: p, lastSize: v }]) => [
          {
            endIndex: p,
            size: v,
            startIndex: c
          }
        ])
      ),
      n2
    ), F(d, m);
    const I = ht(
      x(
        d,
        k((c) => c === void 0)
      ),
      true
    );
    F(
      x(
        m,
        P$1((c) => c !== void 0 && X(rt(f).sizeTree)),
        k((c) => {
          const p = rt(S), v = rt(u).length > 0;
          return p ? v ? [
            { endIndex: 0, size: p, startIndex: 0 },
            { endIndex: 1, size: c, startIndex: 1 }
          ] : [] : [{ endIndex: 0, size: c, startIndex: 0 }];
        })
      ),
      n2
    ), F(
      x(
        h,
        P$1((c) => c !== void 0 && c.length > 0 && X(rt(f).sizeTree)),
        k((c) => {
          const p = [];
          let v = c[0], O = 0;
          for (let B = 1; B < c.length; B++) {
            const W = c[B];
            W !== v && (p.push({
              endIndex: B - 1,
              size: v,
              startIndex: O
            }), v = W, O = B);
          }
          return p.push({
            endIndex: c.length - 1,
            size: v,
            startIndex: O
          }), p;
        })
      ),
      n2
    ), F(
      x(
        u,
        $(S, m),
        P$1(([, c, p]) => c !== void 0 && p !== void 0),
        k(([c, p, v]) => {
          const O = [];
          for (let B = 0; B < c.length; B++) {
            const W = c[B], _ = c[B + 1];
            O.push({
              startIndex: W,
              endIndex: W,
              size: p
            }), _ !== void 0 && O.push({
              startIndex: W + 1,
              endIndex: _ - 1,
              size: v
            });
          }
          return O;
        })
      ),
      n2
    );
    const b = bt(
      x(
        n2,
        $(f),
        Lt(
          ({ sizes: c }, [p, v]) => ({
            changed: v !== c,
            sizes: v
          }),
          { changed: false, sizes: g }
        ),
        k((c) => c.changed)
      )
    );
    Y(
      x(
        l2,
        Lt(
          (c, p) => ({ diff: c.prev - p, prev: p }),
          { diff: 0, prev: 0 }
        ),
        k((c) => c.diff)
      ),
      (c) => {
        const { groupIndices: p } = rt(f);
        if (c > 0)
          D(e, true), D(s, c + pn(c, p));
        else if (c < 0) {
          const v = rt(a2);
          v.length > 0 && (c -= pn(-c, v)), D(i2, c);
        }
      }
    ), Y(x(l2, $(t2)), ([c, p]) => {
      c < 0 && p(
        "`firstItemIndex` prop should not be set to less than zero. If you don't know the total count, just use a very high value",
        { firstItemIndex: l2 },
        Ct.ERROR
      );
    });
    const y = bt(s);
    F(
      x(
        s,
        $(f),
        k(([c, p]) => {
          const v = p.groupIndices.length > 0, O = [], B = p.lastSize;
          if (v) {
            const W = le(p.sizeTree, 0);
            let _ = 0, j = 0;
            for (; _ < c; ) {
              const M = p.groupIndices[j], et = p.groupIndices.length === j + 1 ? 1 / 0 : p.groupIndices[j + 1] - M - 1;
              O.push({
                endIndex: M,
                size: W,
                startIndex: M
              }), O.push({
                endIndex: M + 1 + et - 1,
                size: B,
                startIndex: M + 1
              }), j++, _ += et + 1;
            }
            const L = Dt(p.sizeTree);
            return _ !== c && L.shift(), L.reduce(
              (M, { k: et, v: wt }) => {
                let ft = M.ranges;
                return M.prevSize !== 0 && (ft = [
                  ...M.ranges,
                  {
                    endIndex: et + c - 1,
                    size: M.prevSize,
                    startIndex: M.prevIndex
                  }
                ]), {
                  prevIndex: et + c,
                  prevSize: wt,
                  ranges: ft
                };
              },
              {
                prevIndex: c,
                prevSize: 0,
                ranges: O
              }
            ).ranges;
          }
          return Dt(p.sizeTree).reduce(
            (W, { k: _, v: j }) => ({
              prevIndex: _ + c,
              prevSize: j,
              ranges: [...W.ranges, { endIndex: _ + c - 1, size: W.prevSize, startIndex: W.prevIndex }]
            }),
            {
              prevIndex: 0,
              prevSize: B,
              ranges: []
            }
          ).ranges;
        })
      ),
      n2
    );
    const z = bt(
      x(
        i2,
        $(f, R),
        k(([c, { offsetTree: p }, v]) => {
          const O = -c;
          return ue(O, p, v);
        })
      )
    );
    return F(
      x(
        i2,
        $(f, R),
        k(([c, p, v]) => {
          if (p.groupIndices.length > 0) {
            if (X(p.sizeTree))
              return p;
            let B = Zt();
            const W = rt(a2);
            let _ = 0, j = 0, L = 0;
            for (; _ < -c; ) {
              L = W[j];
              const M = W[j + 1] - L - 1;
              j++, _ += M + 1;
            }
            if (B = Dt(p.sizeTree).reduce((M, { k: et, v: wt }) => yt(M, Math.max(0, et + c), wt), B), _ !== -c) {
              const M = le(p.sizeTree, L);
              B = yt(B, 0, M);
              const et = kt(p.sizeTree, -c + 1)[1];
              B = yt(B, 1, et);
            }
            return {
              ...p,
              sizeTree: B,
              ...Ge(p.offsetTree, 0, B, v)
            };
          } else {
            const B = Dt(p.sizeTree).reduce((W, { k: _, v: j }) => yt(W, Math.max(0, _ + c), j), Zt());
            return {
              ...p,
              sizeTree: B,
              ...Ge(p.offsetTree, 0, B, v)
            };
          }
        })
      ),
      f
    ), {
      beforeUnshiftWith: y,
      // input
      data: w,
      defaultItemSize: m,
      firstItemIndex: l2,
      fixedItemSize: d,
      fixedGroupSize: S,
      gap: R,
      groupIndices: u,
      heightEstimates: h,
      itemSize: T,
      listRefresh: b,
      shiftWith: i2,
      shiftWithOffset: z,
      sizeRanges: n2,
      // output
      sizes: f,
      statefulTotalCount: r2,
      totalCount: o,
      trackItemSizes: I,
      unshiftWith: s
    };
  },
  tt(Wt, De),
  { singleton: true }
);
function Po(t2) {
  return t2.reduce(
    (e, n2) => (e.groupIndices.push(e.totalCount), e.totalCount += n2 + 1, e),
    {
      groupIndices: [],
      totalCount: 0
    }
  );
}
const Dn = K(
  ([{ groupIndices: t2, sizes: e, totalCount: n2 }, { headerHeight: o, scrollTop: r2 }]) => {
    const s = U(), i2 = U(), l2 = bt(x(s, k(Po)));
    return F(
      x(
        l2,
        k((u) => u.totalCount)
      ),
      n2
    ), F(
      x(
        l2,
        k((u) => u.groupIndices)
      ),
      t2
    ), F(
      x(
        ut(r2, e, o),
        P$1(([u, d]) => be(d)),
        k(([u, d, m]) => kt(d.groupOffsetTree, Math.max(u - m, 0), "v")[0]),
        J(),
        k((u) => [u])
      ),
      i2
    ), { groupCounts: s, topItemsIndexes: i2 };
  },
  tt(Pt, It)
), _t = K(
  ([{ log: t2 }]) => {
    const e = C(false), n2 = bt(
      x(
        e,
        P$1((o) => o),
        J()
      )
    );
    return Y(e, (o) => {
      o && rt(t2)("props updated", {}, Ct.DEBUG);
    }), { didMount: n2, propsReady: e };
  },
  tt(Wt),
  { singleton: true }
), Go = typeof document < "u" && "scrollBehavior" in document.documentElement.style;
function $n(t2) {
  const e = typeof t2 == "number" ? { index: t2 } : t2;
  return e.align || (e.align = "start"), (!e.behavior || !Go) && (e.behavior = "auto"), e.offset || (e.offset = 0), e;
}
const me = K(
  ([
    { gap: t2, listRefresh: e, sizes: n2, totalCount: o },
    {
      fixedFooterHeight: r2,
      fixedHeaderHeight: s,
      footerHeight: i2,
      headerHeight: l2,
      scrollingInProgress: u,
      scrollTo: d,
      smoothScrollTargetReached: m,
      viewportHeight: S
    },
    { log: h }
  ]) => {
    const T = U(), w = U(), R = C(0);
    let g = null, f = null, a2 = null;
    function I() {
      g && (g(), g = null), a2 && (a2(), a2 = null), f && (clearTimeout(f), f = null), D(u, false);
    }
    return F(
      x(
        T,
        $(n2, S, o, R, l2, i2, h),
        $(t2, s, r2),
        k(
          ([
            [b, y, z, c, p, v, O, B],
            W,
            _,
            j
          ]) => {
            const L = $n(b), { align: xt, behavior: M, offset: et } = L, wt = c - 1, ft = Nn(L, y, wt);
            let St = ue(ft, y.offsetTree, W) + v;
            xt === "end" ? (St += _ + kt(y.sizeTree, ft)[1] - z + j, ft === wt && (St += O)) : xt === "center" ? St += (_ + kt(y.sizeTree, ft)[1] - z + j) / 2 : St -= p, et && (St += et);
            const Mt = (pt) => {
              I(), pt ? (B("retrying to scroll to", { location: b }, Ct.DEBUG), D(T, b)) : (D(w, true), B("list did not change, scroll successful", {}, Ct.DEBUG));
            };
            if (I(), M === "smooth") {
              let pt = false;
              a2 = Y(e, (qt) => {
                pt = pt || qt;
              }), g = Et(m, () => {
                Mt(pt);
              });
            } else
              g = Et(x(e, Mo(150)), Mt);
            return f = setTimeout(() => {
              I();
            }, 1200), D(u, true), B("scrolling from index to", { behavior: M, index: ft, top: St }, Ct.DEBUG), { behavior: M, top: St };
          }
        )
      ),
      d
    ), {
      scrollTargetReached: w,
      scrollToIndex: T,
      topListHeight: R
    };
  },
  tt(Pt, It, Wt),
  { singleton: true }
);
function Mo(t2) {
  return (e) => {
    const n2 = setTimeout(() => {
      e(false);
    }, t2);
    return (o) => {
      o && (e(true), clearTimeout(n2));
    };
  };
}
function Ue(t2, e) {
  t2 == 0 ? e() : requestAnimationFrame(() => {
    Ue(t2 - 1, e);
  });
}
function Ke(t2, e) {
  const n2 = e - 1;
  return typeof t2 == "number" ? t2 : t2.index === "LAST" ? n2 : t2.index;
}
const pe = K(
  ([{ defaultItemSize: t2, listRefresh: e, sizes: n2 }, { scrollTop: o }, { scrollTargetReached: r2, scrollToIndex: s }, { didMount: i2 }]) => {
    const l2 = C(true), u = C(0), d = C(true);
    return F(
      x(
        i2,
        $(u),
        P$1(([m, S]) => !!S),
        Ft(false)
      ),
      l2
    ), F(
      x(
        i2,
        $(u),
        P$1(([m, S]) => !!S),
        Ft(false)
      ),
      d
    ), Y(
      x(
        ut(e, i2),
        $(l2, n2, t2, d),
        P$1(([[, m], S, { sizeTree: h }, T, w]) => m && (!X(h) || Ae(T)) && !S && !w),
        $(u)
      ),
      ([, m]) => {
        Et(r2, () => {
          D(d, true);
        }), Ue(4, () => {
          Et(o, () => {
            D(l2, true);
          }), D(s, m);
        });
      }
    ), {
      initialItemFinalLocationReached: d,
      initialTopMostItemIndex: u,
      scrolledToInitialItem: l2
    };
  },
  tt(Pt, It, me, _t),
  { singleton: true }
);
function Un(t2, e) {
  return Math.abs(t2 - e) < 1.01;
}
const ae = "up", oe = "down", Ao = "none", Wo = {
  atBottom: false,
  notAtBottomBecause: "NOT_SHOWING_LAST_ITEM",
  state: {
    offsetBottom: 0,
    scrollHeight: 0,
    scrollTop: 0,
    viewportHeight: 0
  }
}, _o = 0, he = K(([{ footerHeight: t2, headerHeight: e, scrollBy: n2, scrollContainerState: o, scrollTop: r2, viewportHeight: s }]) => {
  const i2 = C(false), l2 = C(true), u = U(), d = U(), m = C(4), S = C(_o), h = ht(
    x(
      Fe(x(V(r2), Kt(1), Ft(true)), x(V(r2), Kt(1), Ft(false), dn(100))),
      J()
    ),
    false
  ), T = ht(
    x(Fe(x(n2, Ft(true)), x(n2, Ft(false), dn(200))), J()),
    false
  );
  F(
    x(
      ut(V(r2), V(S)),
      k(([a2, I]) => a2 <= I),
      J()
    ),
    l2
  ), F(x(l2, Gt(50)), d);
  const w = bt(
    x(
      ut(o, V(s), V(e), V(t2), V(m)),
      Lt((a2, [{ scrollHeight: I, scrollTop: b }, y, z, c, p]) => {
        const v = b + y - I > -p, O = {
          scrollHeight: I,
          scrollTop: b,
          viewportHeight: y
        };
        if (v) {
          let W, _;
          return b > a2.state.scrollTop ? (W = "SCROLLED_DOWN", _ = a2.state.scrollTop - b) : (W = "SIZE_DECREASED", _ = a2.state.scrollTop - b || a2.scrollTopDelta), {
            atBottom: true,
            atBottomBecause: W,
            scrollTopDelta: _,
            state: O
          };
        }
        let B;
        return O.scrollHeight > a2.state.scrollHeight ? B = "SIZE_INCREASED" : y < a2.state.viewportHeight ? B = "VIEWPORT_HEIGHT_DECREASING" : b < a2.state.scrollTop ? B = "SCROLLING_UPWARDS" : B = "NOT_FULLY_SCROLLED_TO_LAST_ITEM_BOTTOM", {
          atBottom: false,
          notAtBottomBecause: B,
          state: O
        };
      }, Wo),
      J((a2, I) => a2 && a2.atBottom === I.atBottom)
    )
  ), R = ht(
    x(
      o,
      Lt(
        (a2, { scrollHeight: I, scrollTop: b, viewportHeight: y }) => {
          if (Un(a2.scrollHeight, I))
            return {
              changed: false,
              jump: 0,
              scrollHeight: I,
              scrollTop: b
            };
          {
            const z = I - (b + y) < 1;
            return a2.scrollTop !== b && z ? {
              changed: true,
              jump: a2.scrollTop - b,
              scrollHeight: I,
              scrollTop: b
            } : {
              changed: true,
              jump: 0,
              scrollHeight: I,
              scrollTop: b
            };
          }
        },
        { changed: false, jump: 0, scrollHeight: 0, scrollTop: 0 }
      ),
      P$1((a2) => a2.changed),
      k((a2) => a2.jump)
    ),
    0
  );
  F(
    x(
      w,
      k((a2) => a2.atBottom)
    ),
    i2
  ), F(x(i2, Gt(50)), u);
  const g = C(oe);
  F(
    x(
      o,
      k(({ scrollTop: a2 }) => a2),
      J(),
      Lt(
        (a2, I) => rt(T) ? { direction: a2.direction, prevScrollTop: I } : { direction: I < a2.prevScrollTop ? ae : oe, prevScrollTop: I },
        { direction: oe, prevScrollTop: 0 }
      ),
      k((a2) => a2.direction)
    ),
    g
  ), F(x(o, Gt(50), Ft(Ao)), g);
  const f = C(0);
  return F(
    x(
      h,
      P$1((a2) => !a2),
      Ft(0)
    ),
    f
  ), F(
    x(
      r2,
      Gt(100),
      $(h),
      P$1(([a2, I]) => I),
      Lt(([a2, I], [b]) => [I, b], [0, 0]),
      k(([a2, I]) => I - a2)
    ),
    f
  ), {
    atBottomState: w,
    atBottomStateChange: u,
    atBottomThreshold: m,
    atTopStateChange: d,
    atTopThreshold: S,
    isAtBottom: i2,
    isAtTop: l2,
    isScrolling: h,
    lastJumpDueToItemResize: R,
    scrollDirection: g,
    scrollVelocity: f
  };
}, tt(It)), de = "top", fe = "bottom", hn = "none";
function gn(t2, e, n2) {
  return typeof t2 == "number" ? n2 === ae && e === de || n2 === oe && e === fe ? t2 : 0 : n2 === ae ? e === de ? t2.main : t2.reverse : e === fe ? t2.main : t2.reverse;
}
function In(t2, e) {
  var n2;
  return typeof t2 == "number" ? t2 : (n2 = t2[e]) != null ? n2 : 0;
}
const je = K(
  ([{ deviation: t2, fixedHeaderHeight: e, headerHeight: n2, scrollTop: o, viewportHeight: r2 }]) => {
    const s = U(), i2 = C(0), l2 = C(0), u = C(0), d = ht(
      x(
        ut(
          V(o),
          V(r2),
          V(n2),
          V(s, ce),
          V(u),
          V(i2),
          V(e),
          V(t2),
          V(l2)
        ),
        k(
          ([
            m,
            S,
            h,
            [T, w],
            R,
            g,
            f,
            a2,
            I
          ]) => {
            const b = m - a2, y = g + f, z = Math.max(h - b, 0);
            let c = hn;
            const p = In(I, de), v = In(I, fe);
            return T -= a2, T += h + f, w += h + f, w -= a2, T > m + y - p && (c = ae), w < m - z + S + v && (c = oe), c !== hn ? [
              Math.max(b - h - gn(R, de, c) - p, 0),
              b - z - f + S + gn(R, fe, c) + v
            ] : null;
          }
        ),
        P$1((m) => m != null),
        J(ce)
      ),
      [0, 0]
    );
    return {
      increaseViewportBy: l2,
      // input
      listBoundary: s,
      overscan: u,
      topListHeight: i2,
      // output
      visibleRange: d
    };
  },
  tt(It),
  { singleton: true }
);
function No(t2, e, n2) {
  if (be(e)) {
    const o = _n(t2, e);
    return [
      { index: kt(e.groupOffsetTree, o)[0], offset: 0, size: 0 },
      { data: n2 == null ? void 0 : n2[0], index: o, offset: 0, size: 0 }
    ];
  }
  return [{ data: n2 == null ? void 0 : n2[0], index: t2, offset: 0, size: 0 }];
}
const Be = {
  bottom: 0,
  firstItemIndex: 0,
  items: [],
  offsetBottom: 0,
  offsetTop: 0,
  top: 0,
  topItems: [],
  topListHeight: 0,
  totalCount: 0
};
function Te(t2, e, n2, o, r2, s) {
  const { lastIndex: i2, lastOffset: l2, lastSize: u } = r2;
  let d = 0, m = 0;
  if (t2.length > 0) {
    d = t2[0].offset;
    const R = t2[t2.length - 1];
    m = R.offset + R.size;
  }
  const S = n2 - i2, h = l2 + S * u + (S - 1) * o, T = d, w = h - m;
  return {
    bottom: m,
    firstItemIndex: s,
    items: xn(t2, r2, s),
    offsetBottom: w,
    offsetTop: d,
    top: T,
    topItems: xn(e, r2, s),
    topListHeight: e.reduce((R, g) => g.size + R, 0),
    totalCount: n2
  };
}
function Kn(t2, e, n2, o, r2, s) {
  let i2 = 0;
  if (n2.groupIndices.length > 0)
    for (const m of n2.groupIndices) {
      if (m - i2 >= t2)
        break;
      i2++;
    }
  const l2 = t2 + i2, u = Ke(e, l2), d = Array.from({ length: l2 }).map((m, S) => ({
    data: s[S + u],
    index: S + u,
    offset: 0,
    size: 0
  }));
  return Te(d, [], l2, r2, n2, o);
}
function xn(t2, e, n2) {
  if (t2.length === 0)
    return [];
  if (!be(e))
    return t2.map((d) => ({ ...d, index: d.index + n2, originalIndex: d.index }));
  const o = t2[0].index, r2 = t2[t2.length - 1].index, s = [], i2 = Xt(e.groupOffsetTree, o, r2);
  let l2, u = 0;
  for (const d of t2) {
    (!l2 || l2.end < d.index) && (l2 = i2.shift(), u = e.groupIndices.indexOf(l2.start));
    let m;
    d.index === l2.start ? m = {
      index: u,
      type: "group"
    } : m = {
      groupIndex: u,
      index: d.index - (u + 1) + n2
    }, s.push({
      ...m,
      data: d.data,
      offset: d.offset,
      originalIndex: d.index,
      size: d.size
    });
  }
  return s;
}
function Sn(t2, e) {
  var n2;
  return t2 === void 0 ? 0 : typeof t2 == "number" ? t2 : (n2 = t2[e]) != null ? n2 : 0;
}
const jt = K(
  ([
    { data: t2, firstItemIndex: e, gap: n2, sizes: o, totalCount: r2 },
    s,
    { listBoundary: i2, topListHeight: l2, visibleRange: u },
    { initialTopMostItemIndex: d, scrolledToInitialItem: m },
    { topListHeight: S },
    h,
    { didMount: T },
    { recalcInProgress: w }
  ]) => {
    const R = C([]), g = C(0), f = U(), a2 = C(0);
    F(s.topItemsIndexes, R);
    const I = ht(
      x(
        ut(
          T,
          w,
          V(u, ce),
          V(r2),
          V(o),
          V(d),
          m,
          V(R),
          V(e),
          V(n2),
          V(a2),
          t2
        ),
        P$1(([c, p, , v, , , , , , , , O]) => {
          const B = O && O.length !== v;
          return c && !p && !B;
        }),
        k(
          ([
            ,
            ,
            [c, p],
            v,
            O,
            B,
            W,
            _,
            j,
            L,
            xt,
            M
          ]) => {
            var q, at, gt, Tt;
            const et = O, { offsetTree: wt, sizeTree: ft } = et, St = rt(g);
            if (v === 0)
              return { ...Be, totalCount: v };
            if (c === 0 && p === 0)
              return St === 0 ? { ...Be, totalCount: v } : Kn(St, B, O, j, L, M || []);
            if (X(ft))
              return St > 0 ? null : Te(
                No(Ke(B, v), et, M),
                [],
                v,
                L,
                et,
                j
              );
            const Mt = [];
            if (_.length > 0) {
              const st = _[0], it = _[_.length - 1];
              let mt = 0;
              for (const lt of Xt(ft, st, it)) {
                const Z2 = lt.value, nt = Math.max(lt.start, st), vt2 = Math.min(lt.end, it);
                for (let ct = nt; ct <= vt2; ct++)
                  Mt.push({ data: M == null ? void 0 : M[ct], index: ct, offset: mt, size: Z2 }), mt += Z2;
              }
            }
            if (!W)
              return Te([], Mt, v, L, et, j);
            const pt = _.length > 0 ? _[_.length - 1] + 1 : 0, qt = ko(wt, c, p, pt);
            if (qt.length === 0)
              return null;
            const ee = v - 1, Ot = ye([], (st) => {
              for (const it of qt) {
                const mt = it.value;
                let lt = mt.offset, Z2 = it.start;
                const nt = mt.size;
                if (mt.offset < c) {
                  Z2 += Math.floor((c - mt.offset + L) / (nt + L));
                  const ct = Z2 - it.start;
                  lt += ct * nt + ct * L;
                }
                Z2 < pt && (lt += (pt - Z2) * nt, Z2 = pt);
                const vt2 = Math.min(it.end, ee);
                for (let ct = Z2; ct <= vt2 && !(lt >= p); ct++)
                  st.push({ data: M == null ? void 0 : M[ct], index: ct, offset: lt, size: nt }), lt += nt + L;
              }
            }), ne = Sn(xt, de), H = Sn(xt, fe);
            if (Ot.length > 0 && (ne > 0 || H > 0)) {
              const st = Ot[0], it = Ot[Ot.length - 1];
              if (ne > 0 && st.index > pt) {
                const mt = Math.min(ne, st.index - pt), lt = [];
                let Z2 = st.offset;
                for (let nt = st.index - 1; nt >= st.index - mt; nt--) {
                  const ct = (at = (q = Xt(ft, nt, nt)[0]) == null ? void 0 : q.value) != null ? at : st.size;
                  Z2 -= ct + L, lt.unshift({ data: M == null ? void 0 : M[nt], index: nt, offset: Z2, size: ct });
                }
                Ot.unshift(...lt);
              }
              if (H > 0 && it.index < ee) {
                const mt = Math.min(H, ee - it.index);
                let lt = it.offset + it.size + L;
                for (let Z2 = it.index + 1; Z2 <= it.index + mt; Z2++) {
                  const vt2 = (Tt = (gt = Xt(ft, Z2, Z2)[0]) == null ? void 0 : gt.value) != null ? Tt : it.size;
                  Ot.push({ data: M == null ? void 0 : M[Z2], index: Z2, offset: lt, size: vt2 }), lt += vt2 + L;
                }
              }
            }
            return Te(Ot, Mt, v, L, et, j);
          }
        ),
        //@ts-expect-error filter needs to be fixed
        P$1((c) => c !== null),
        J()
      ),
      Be
    );
    F(
      x(
        t2,
        P$1(Ae),
        k((c) => c == null ? void 0 : c.length)
      ),
      r2
    ), F(
      x(
        I,
        k((c) => c.topListHeight)
      ),
      S
    ), F(S, l2), F(
      x(
        I,
        k((c) => [c.top, c.bottom])
      ),
      i2
    ), F(
      x(
        I,
        k((c) => c.items)
      ),
      f
    );
    const b = bt(
      x(
        I,
        P$1(({ items: c }) => c.length > 0),
        $(r2, t2),
        P$1(([{ items: c }, p]) => c[c.length - 1].originalIndex === p - 1),
        k(([, c, p]) => [c - 1, p]),
        J(ce),
        k(([c]) => c)
      )
    ), y = bt(
      x(
        I,
        Gt(200),
        P$1(({ items: c, topItems: p }) => c.length > 0 && c[0].originalIndex === p.length),
        k(({ items: c }) => c[0].index),
        J()
      )
    ), z = bt(
      x(
        I,
        P$1(({ items: c }) => c.length > 0),
        k(({ items: c }) => {
          let p = 0, v = c.length - 1;
          for (; c[p].type === "group" && p < v; )
            p++;
          for (; c[v].type === "group" && v > p; )
            v--;
          return {
            endIndex: c[v].index,
            startIndex: c[p].index
          };
        }),
        J(An)
      )
    );
    return {
      endReached: b,
      initialItemCount: g,
      itemsRendered: f,
      listState: I,
      minOverscanItemCount: a2,
      rangeChanged: z,
      startReached: y,
      topItemsIndexes: R,
      ...h
    };
  },
  tt(
    Pt,
    Dn,
    je,
    pe,
    me,
    he,
    _t,
    De
  ),
  { singleton: true }
), jn = K(
  ([{ fixedFooterHeight: t2, fixedHeaderHeight: e, footerHeight: n2, headerHeight: o }, { listState: r2 }]) => {
    const s = U(), i2 = ht(
      x(
        ut(n2, t2, o, e, r2),
        k(([l2, u, d, m, S]) => l2 + u + d + m + S.offsetBottom + S.bottom)
      ),
      0
    );
    return F(V(i2), s), { totalListHeight: i2, totalListHeightChanged: s };
  },
  tt(It, jt),
  { singleton: true }
), Do = K(
  ([{ viewportHeight: t2 }, { totalListHeight: e }]) => {
    const n2 = C(false), o = ht(
      x(
        ut(n2, t2, e),
        P$1(([r2]) => r2),
        k(([, r2, s]) => Math.max(0, r2 - s)),
        Gt(0),
        J()
      ),
      0
    );
    return { alignToBottom: n2, paddingTopAddition: o };
  },
  tt(It, jn),
  { singleton: true }
), qn = K(() => ({
  context: C(null)
})), $o = ({
  itemBottom: t2,
  itemTop: e,
  locationParams: { align: n2, behavior: o, ...r2 },
  viewportBottom: s,
  viewportTop: i2
}) => e < i2 ? { ...r2, align: n2 != null ? n2 : "start", behavior: o } : t2 > s ? { ...r2, align: n2 != null ? n2 : "end", behavior: o } : null, Yn = K(
  ([
    { gap: t2, sizes: e, totalCount: n2 },
    { fixedFooterHeight: o, fixedHeaderHeight: r2, headerHeight: s, scrollingInProgress: i2, scrollTop: l2, viewportHeight: u },
    { scrollToIndex: d }
  ]) => {
    const m = U();
    return F(
      x(
        m,
        $(e, u, n2, s, r2, o, l2),
        $(t2),
        k(([[S, h, T, w, R, g, f, a2], I]) => {
          const { align: b, behavior: y, calculateViewLocation: z = $o, done: c, ...p } = S, v = Nn(S, h, w - 1), O = ue(v, h.offsetTree, I) + R + g, B = O + kt(h.sizeTree, v)[1], W = a2 + g, _ = a2 + T - f, j = z({
            itemBottom: B,
            itemTop: O,
            locationParams: { align: b, behavior: y, ...p },
            viewportBottom: _,
            viewportTop: W
          });
          return j ? c && Et(
            x(
              i2,
              P$1((L) => !L),
              // skips the initial publish of false, and the cleanup call.
              // but if scrollingInProgress is true, we skip the initial publish.
              Kt(rt(i2) ? 1 : 2)
            ),
            c
          ) : c == null || c(), j;
        }),
        P$1((S) => S !== null)
      ),
      d
    ), {
      scrollIntoView: m
    };
  },
  tt(Pt, It, me, jt, Wt),
  { singleton: true }
);
function Tn(t2) {
  return t2 ? t2 === "smooth" ? "smooth" : "auto" : false;
}
const Uo = (t2, e) => typeof t2 == "function" ? Tn(t2(e)) : e && Tn(t2), Ko = K(
  ([
    { listRefresh: t2, totalCount: e, fixedItemSize: n2, data: o },
    { atBottomState: r2, isAtBottom: s },
    { scrollToIndex: i2 },
    { scrolledToInitialItem: l2 },
    { didMount: u, propsReady: d },
    { log: m },
    { scrollingInProgress: S },
    { context: h },
    { scrollIntoView: T }
  ]) => {
    const w = C(false), R = U();
    let g = null;
    function f(y) {
      D(i2, {
        align: "end",
        behavior: y,
        index: "LAST"
      });
    }
    Y(
      x(
        ut(x(V(e), Kt(1)), u),
        $(V(w), s, l2, S),
        k(([[y, z], c, p, v, O]) => {
          let B = z && v, W = "auto";
          return B && (W = Uo(c, p || O), B = B && !!W), { followOutputBehavior: W, shouldFollow: B, totalCount: y };
        }),
        P$1(({ shouldFollow: y }) => y)
      ),
      ({ followOutputBehavior: y, totalCount: z }) => {
        g && (g(), g = null), rt(n2) ? requestAnimationFrame(() => {
          rt(m)("following output to ", { totalCount: z }, Ct.DEBUG), f(y);
        }) : g = Et(t2, () => {
          rt(m)("following output to ", { totalCount: z }, Ct.DEBUG), f(y), g = null;
        });
      }
    );
    function a2(y) {
      const z = Et(r2, (c) => {
        y && !c.atBottom && c.notAtBottomBecause === "SIZE_INCREASED" && !g && (rt(m)("scrolling to bottom due to increased size", {}, Ct.DEBUG), f("auto"));
      });
      setTimeout(z, 100);
    }
    Y(
      x(
        ut(V(w), e, d),
        P$1(([y, , z]) => y && z),
        Lt(
          ({ value: y }, [, z]) => ({ refreshed: y === z, value: z }),
          { refreshed: false, value: 0 }
        ),
        P$1(({ refreshed: y }) => y),
        $(w, e)
      ),
      ([, y]) => {
        rt(l2) && a2(y !== false);
      }
    ), Y(R, () => {
      a2(rt(w) !== false);
    }), Y(ut(V(w), r2), ([y, z]) => {
      y && !z.atBottom && z.notAtBottomBecause === "VIEWPORT_HEIGHT_DECREASING" && f("auto");
    });
    const I = C(null), b = U();
    return F(
      Fe(
        x(
          V(o),
          k((y) => {
            var z;
            return (z = y == null ? void 0 : y.length) != null ? z : 0;
          })
        ),
        x(V(e))
      ),
      b
    ), Y(
      x(
        ut(x(b, Kt(1)), u),
        $(V(I), l2, S, h),
        k(([[y, z], c, p, v, O]) => z && p && (c == null ? void 0 : c({ context: O, totalCount: y, scrollingInProgress: v }))),
        P$1((y) => !!y),
        Gt(0)
      ),
      (y) => {
        g && (g(), g = null), rt(n2) ? requestAnimationFrame(() => {
          rt(m)("scrolling into view", {}), D(T, y);
        }) : g = Et(t2, () => {
          rt(m)("scrolling into view", {}), D(T, y), g = null;
        });
      }
    ), { autoscrollToBottom: R, followOutput: w, scrollIntoViewOnChange: I };
  },
  tt(
    Pt,
    he,
    me,
    pe,
    _t,
    Wt,
    It,
    qn,
    Yn
  )
), jo = K(
  ([{ data: t2, firstItemIndex: e, gap: n2, sizes: o }, { initialTopMostItemIndex: r2 }, { initialItemCount: s, listState: i2 }, { didMount: l2 }]) => (F(
    x(
      l2,
      $(s),
      P$1(([, u]) => u !== 0),
      $(r2, o, e, n2, t2),
      k(([[, u], d, m, S, h, T = []]) => Kn(u, d, m, S, h, T))
    ),
    i2
  ), {}),
  tt(Pt, pe, jt, _t),
  { singleton: true }
), qo = K(
  ([{ didMount: t2 }, { scrollTo: e }, { listState: n2 }]) => {
    const o = C(0);
    return Y(
      x(
        t2,
        $(o),
        P$1(([, r2]) => r2 !== 0),
        k(([, r2]) => ({ top: r2 }))
      ),
      (r2) => {
        Et(
          x(
            n2,
            Kt(1),
            P$1((s) => s.items.length > 1)
          ),
          () => {
            requestAnimationFrame(() => {
              D(e, r2);
            });
          }
        );
      }
    ), {
      initialScrollTop: o
    };
  },
  tt(_t, It, jt),
  { singleton: true }
), Zn = K(
  ([{ scrollVelocity: t2 }]) => {
    const e = C(false), n2 = U(), o = C(false);
    return F(
      x(
        t2,
        $(o, e, n2),
        P$1(([r2, s]) => !!s),
        k(([r2, s, i2, l2]) => {
          const { enter: u, exit: d } = s;
          if (i2) {
            if (d(r2, l2))
              return false;
          } else if (u(r2, l2))
            return true;
          return i2;
        }),
        J()
      ),
      e
    ), Y(
      x(ut(e, t2, n2), $(o)),
      ([[r2, s, i2], l2]) => {
        r2 && l2 && l2.change && l2.change(s, i2);
      }
    ), { isSeeking: e, scrollSeekConfiguration: o, scrollSeekRangeChanged: n2, scrollVelocity: t2 };
  },
  tt(he),
  { singleton: true }
), qe = K(([{ scrollContainerState: t2, scrollTo: e }]) => {
  const n2 = U(), o = U(), r2 = U(), s = C(false), i2 = C(void 0);
  return F(
    x(
      ut(n2, o),
      k(([{ scrollHeight: l2, scrollTop: u, viewportHeight: d }, { offsetTop: m }]) => ({
        scrollHeight: l2,
        scrollTop: Math.max(0, u - m),
        viewportHeight: d
      }))
    ),
    t2
  ), F(
    x(
      e,
      $(o),
      k(([l2, { offsetTop: u }]) => ({
        ...l2,
        top: l2.top + u
      }))
    ),
    r2
  ), {
    customScrollParent: i2,
    // config
    useWindowScroll: s,
    // input
    windowScrollContainerState: n2,
    // signals
    windowScrollTo: r2,
    windowViewportRect: o
  };
}, tt(It)), Yo = K(
  ([
    { sizeRanges: t2, sizes: e },
    { headerHeight: n2, scrollTop: o },
    { initialTopMostItemIndex: r2 },
    { didMount: s },
    { useWindowScroll: i2, windowScrollContainerState: l2, windowViewportRect: u }
  ]) => {
    const d = U(), m = C(void 0), S = C(null), h = C(null);
    return F(l2, S), F(u, h), Y(
      x(
        d,
        $(e, o, i2, S, h, n2)
      ),
      ([T, w, R, g, f, a2, I]) => {
        const b = Oo(w.sizeTree);
        g && f !== null && a2 !== null && (R = f.scrollTop - a2.offsetTop), R -= I, T({ ranges: b, scrollTop: R });
      }
    ), F(x(m, P$1(Ae), k(Zo)), r2), F(
      x(
        s,
        $(m),
        P$1(([, T]) => T !== void 0),
        J(),
        k(([, T]) => T.ranges)
      ),
      t2
    ), {
      getState: d,
      restoreStateFrom: m
    };
  },
  tt(Pt, It, pe, _t, qe)
);
function Zo(t2) {
  return { align: "start", index: 0, offset: t2.scrollTop };
}
const Xo = K(([{ topItemsIndexes: t2 }]) => {
  const e = C(0);
  return F(
    x(
      e,
      P$1((n2) => n2 >= 0),
      k((n2) => Array.from({ length: n2 }).map((o, r2) => r2))
    ),
    t2
  ), { topItemCount: e };
}, tt(jt));
function Xn(t2) {
  let e = false, n2;
  return (() => (e || (e = true, n2 = t2()), n2));
}
const Jo = Xn(() => /iP(ad|od|hone)/i.test(navigator.userAgent) && /WebKit/i.test(navigator.userAgent)), Qo = K(
  ([
    { deviation: t2, scrollBy: e, scrollingInProgress: n2, scrollTop: o },
    { isAtBottom: r2, isScrolling: s, lastJumpDueToItemResize: i2, scrollDirection: l2 },
    { listState: u },
    { beforeUnshiftWith: d, gap: m, shiftWithOffset: S, sizes: h },
    { log: T },
    { recalcInProgress: w }
  ]) => {
    const R = bt(
      x(
        u,
        $(i2),
        Lt(
          ([, f, a2, I], [{ bottom: b, items: y, offsetBottom: z, totalCount: c }, p]) => {
            const v = b + z;
            let O = 0;
            return a2 === c && f.length > 0 && y.length > 0 && (y[0].originalIndex === 0 && f[0].originalIndex === 0 || (O = v - I, O !== 0 && (O += p))), [O, y, c, v];
          },
          [0, [], 0, 0]
        ),
        P$1(([f]) => f !== 0),
        $(o, l2, n2, r2, T, w),
        P$1(([, f, a2, I, , , b]) => !b && !I && f !== 0 && a2 === ae),
        k(([[f], , , , , a2]) => (a2("Upward scrolling compensation", { amount: f }, Ct.DEBUG), f))
      )
    );
    function g(f) {
      f > 0 ? (D(e, { behavior: "auto", top: -f }), D(t2, 0)) : (D(t2, 0), D(e, { behavior: "auto", top: -f }));
    }
    return Y(x(R, $(t2, s)), ([f, a2, I]) => {
      I && Jo() ? D(t2, a2 - f) : g(-f);
    }), Y(
      x(
        ut(ht(s, false), t2, w),
        P$1(([f, a2, I]) => !f && !I && a2 !== 0),
        k(([f, a2]) => a2),
        Gt(1)
      ),
      g
    ), F(
      x(
        S,
        k((f) => ({ top: -f }))
      ),
      e
    ), Y(
      x(
        d,
        $(h, m),
        k(([f, { groupIndices: a2, lastSize: I, sizeTree: b }, y]) => {
          function z(c) {
            return c * (I + y);
          }
          if (a2.length === 0)
            return z(f);
          {
            let c = 0;
            const p = le(b, 0);
            let v = 0, O = 0;
            for (; v < f; ) {
              v++, c += p;
              let B = a2.length === O + 1 ? 1 / 0 : a2[O + 1] - a2[O] - 1;
              v + B > f && (c -= p, B = f - v + 1), v += B, c += z(B), O++;
            }
            return c;
          }
        })
      ),
      (f) => {
        D(t2, f), requestAnimationFrame(() => {
          D(e, { top: f }), requestAnimationFrame(() => {
            D(t2, 0), D(w, false);
          });
        });
      }
    ), { deviation: t2 };
  },
  tt(It, he, jt, Pt, Wt, De)
), tr = K(
  ([
    t2,
    e,
    n2,
    o,
    r2,
    s,
    i2,
    l2,
    u,
    d,
    m
  ]) => ({
    ...t2,
    ...e,
    ...n2,
    ...o,
    ...r2,
    ...s,
    ...i2,
    ...l2,
    ...u,
    ...d,
    ...m
  }),
  tt(
    je,
    jo,
    _t,
    Zn,
    jn,
    qo,
    Do,
    qe,
    Yn,
    Wt,
    qn
  )
), Jn = K(
  ([
    {
      data: t2,
      defaultItemSize: e,
      firstItemIndex: n2,
      fixedItemSize: o,
      fixedGroupSize: r2,
      gap: s,
      groupIndices: i2,
      heightEstimates: l2,
      itemSize: u,
      sizeRanges: d,
      sizes: m,
      statefulTotalCount: S,
      totalCount: h,
      trackItemSizes: T
    },
    { initialItemFinalLocationReached: w, initialTopMostItemIndex: R, scrolledToInitialItem: g },
    f,
    a2,
    I,
    b,
    { scrollToIndex: y },
    z,
    { topItemCount: c },
    { groupCounts: p },
    v
  ]) => {
    const { listState: O, minOverscanItemCount: B, topItemsIndexes: W, rangeChanged: _, ...j } = b;
    return F(_, v.scrollSeekRangeChanged), F(
      x(
        v.windowViewportRect,
        k((L) => L.visibleHeight)
      ),
      f.viewportHeight
    ), {
      data: t2,
      defaultItemHeight: e,
      firstItemIndex: n2,
      fixedItemHeight: o,
      fixedGroupHeight: r2,
      gap: s,
      groupCounts: p,
      heightEstimates: l2,
      initialItemFinalLocationReached: w,
      initialTopMostItemIndex: R,
      scrolledToInitialItem: g,
      sizeRanges: d,
      topItemCount: c,
      topItemsIndexes: W,
      // input
      totalCount: h,
      ...I,
      groupIndices: i2,
      itemSize: u,
      listState: O,
      minOverscanItemCount: B,
      scrollToIndex: y,
      // output
      statefulTotalCount: S,
      trackItemSizes: T,
      // exported from stateFlagsSystem
      rangeChanged: _,
      ...j,
      // the bag of IO from featureGroup1System
      ...v,
      ...f,
      sizes: m,
      ...a2
    };
  },
  tt(
    Pt,
    pe,
    It,
    Yo,
    Ko,
    jt,
    me,
    Qo,
    Xo,
    Dn,
    tr
  )
);
function er(t2, e) {
  const n2 = {}, o = {};
  let r2 = 0;
  const s = t2.length;
  for (; r2 < s; )
    o[t2[r2]] = 1, r2 += 1;
  for (const i2 in e)
    Object.hasOwn(o, i2) || (n2[i2] = e[i2]);
  return n2;
}
const Ie = typeof document < "u" ? E.useLayoutEffect : E.useEffect;
function Ye(t2, e, n2) {
  const o = Object.keys(e.required || {}), r2 = Object.keys(e.optional || {}), s = Object.keys(e.methods || {}), i2 = Object.keys(e.events || {}), l2 = E.createContext({});
  function u(f, a2) {
    f.propsReady && D(f.propsReady, false);
    for (const I of o) {
      const b = f[e.required[I]];
      D(b, a2[I]);
    }
    for (const I of r2)
      if (I in a2) {
        const b = f[e.optional[I]];
        D(b, a2[I]);
      }
    f.propsReady && D(f.propsReady, true);
  }
  function d(f) {
    return s.reduce((a2, I) => (a2[I] = (b) => {
      const y = f[e.methods[I]];
      D(y, b);
    }, a2), {});
  }
  function m(f) {
    return i2.reduce((a2, I) => (a2[I] = xo(f[e.events[I]]), a2), {});
  }
  const S = E.forwardRef((f, a2) => {
    const { children: I, ...b } = f, [y] = E.useState(() => ye(To(t2), (p) => {
      u(p, b);
    })), [z] = E.useState(an(m, y));
    Ie(() => {
      for (const p of i2)
        p in b && Y(z[p], b[p]);
      return () => {
        Object.values(z).map(We);
      };
    }, [b, z, y]), Ie(() => {
      u(y, b);
    }), E.useImperativeHandle(a2, un(d(y)));
    const c = n2;
    return /* @__PURE__ */ jsxRuntimeExports.jsx(l2.Provider, { value: y, children: n2 ? /* @__PURE__ */ jsxRuntimeExports.jsx(c, { ...er([...o, ...r2, ...i2], b), children: I }) : I });
  }), h = (f) => {
    const a2 = E.useContext(l2);
    return E.useCallback(
      (I) => {
        D(a2[f], I);
      },
      [a2, f]
    );
  }, T = (f) => {
    const I = E.useContext(l2)[f], b = E.useCallback(
      (y) => Y(I, y),
      [I]
    );
    return E.useSyncExternalStore(
      b,
      () => rt(I),
      () => rt(I)
    );
  }, w = (f) => {
    const I = E.useContext(l2)[f], [b, y] = E.useState(an(rt, I));
    return Ie(
      () => Y(I, (z) => {
        z !== b && y(un(z));
      }),
      [I, b]
    ), b;
  }, R = E.version.startsWith("18") ? T : w;
  return {
    Component: S,
    useEmitter: (f, a2) => {
      const b = E.useContext(l2)[f];
      Ie(() => Y(b, a2), [a2, b]);
    },
    useEmitterValue: R,
    usePublisher: h
  };
}
const Re = E.createContext(void 0), Qn = E.createContext(void 0), to = typeof document < "u" ? E.useLayoutEffect : E.useEffect;
function ke(t2) {
  return "self" in t2;
}
function nr(t2) {
  return "body" in t2;
}
function eo(t2, e, n2, o = Qt, r2, s) {
  const i2 = E.useRef(null), l2 = E.useRef(null), u = E.useRef(null), d = E.useCallback(
    (h) => {
      let T, w, R;
      const g = h.target;
      if (nr(g) || ke(g)) {
        const a2 = ke(g) ? g : g.defaultView;
        R = s ? a2.scrollX : a2.scrollY, T = s ? a2.document.documentElement.scrollWidth : a2.document.documentElement.scrollHeight, w = s ? a2.innerWidth : a2.innerHeight;
      } else
        R = s ? g.scrollLeft : g.scrollTop, T = s ? g.scrollWidth : g.scrollHeight, w = s ? g.offsetWidth : g.offsetHeight;
      const f = () => {
        t2({
          scrollHeight: T,
          scrollTop: Math.max(R, 0),
          viewportHeight: w
        });
      };
      h.suppressFlushSync ? f() : fo.flushSync(f), l2.current !== null && (R === l2.current || R <= 0 || R === T - w) && (l2.current = null, e(true), u.current && (clearTimeout(u.current), u.current = null));
    },
    [t2, e, s]
  );
  E.useEffect(() => {
    const h = r2 || i2.current;
    return o(r2 || i2.current), d({ suppressFlushSync: true, target: h }), h.addEventListener("scroll", d, { passive: true }), () => {
      o(null), h.removeEventListener("scroll", d);
    };
  }, [i2, d, n2, o, r2]);
  function m(h) {
    const T = i2.current;
    if (!T || (s ? "offsetWidth" in T && T.offsetWidth === 0 : "offsetHeight" in T && T.offsetHeight === 0))
      return;
    const w = h.behavior === "smooth";
    let R, g, f;
    ke(T) ? (g = Math.max(
      zt(T.document.documentElement, s ? "width" : "height"),
      s ? T.document.documentElement.scrollWidth : T.document.documentElement.scrollHeight
    ), R = s ? T.innerWidth : T.innerHeight, f = s ? window.scrollX : window.scrollY) : (g = T[s ? "scrollWidth" : "scrollHeight"], R = zt(T, s ? "width" : "height"), f = T[s ? "scrollLeft" : "scrollTop"]);
    const a2 = g - R;
    if (h.top = Math.ceil(Math.max(Math.min(a2, h.top), 0)), Un(R, g) || h.top === f) {
      t2({ scrollHeight: g, scrollTop: f, viewportHeight: R }), w && e(true);
      return;
    }
    w ? (l2.current = h.top, u.current && clearTimeout(u.current), u.current = setTimeout(() => {
      u.current = null, l2.current = null, e(true);
    }, 1e3)) : l2.current = null, s && (h = { behavior: h.behavior, left: h.top }), T.scrollTo(h);
  }
  function S(h) {
    s && (h = { behavior: h.behavior, left: h.top }), i2.current.scrollBy(h);
  }
  return { scrollByCallback: S, scrollerRef: i2, scrollToCallback: m };
}
const ze = "-webkit-sticky", Cn = "sticky", Ze = Xn(() => {
  if (typeof document > "u")
    return Cn;
  const t2 = document.createElement("div");
  return t2.style.position = ze, t2.style.position === ze ? ze : Cn;
});
function Xe(t2) {
  return t2;
}
const or = /* @__PURE__ */ K(() => {
  const t2 = C((l2) => `Item ${l2}`), e = C((l2) => `Group ${l2}`), n2 = C({}), o = C(Xe), r2 = C("div"), s = C(Qt), i2 = (l2, u = null) => ht(
    x(
      n2,
      k((d) => d[l2]),
      J()
    ),
    u
  );
  return {
    components: n2,
    computeItemKey: o,
    EmptyPlaceholder: i2("EmptyPlaceholder"),
    FooterComponent: i2("Footer"),
    GroupComponent: i2("Group", "div"),
    groupContent: e,
    HeaderComponent: i2("Header"),
    HeaderFooterTag: r2,
    ItemComponent: i2("Item", "div"),
    itemContent: t2,
    ListComponent: i2("List", "div"),
    ScrollerComponent: i2("Scroller", "div"),
    scrollerRef: s,
    ScrollSeekPlaceholder: i2("ScrollSeekPlaceholder"),
    TopItemListComponent: i2("TopItemList")
  };
}), rr = /* @__PURE__ */ K(
  ([t2, e]) => ({ ...t2, ...e }),
  tt(Jn, or)
), sr = ({ height: t2 }) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { style: { height: t2 } }), ir = { overflowAnchor: "none", position: Ze(), zIndex: 1 }, no = { overflowAnchor: "none" }, lr = { ...no, display: "inline-block", height: "100%" }, wn = /* @__PURE__ */ E.memo(function({ showTopList: e = false }) {
  const n2 = A("listState"), o = Rt("sizeRanges"), r2 = A("useWindowScroll"), s = A("customScrollParent"), i2 = Rt("windowScrollContainerState"), l2 = Rt("scrollContainerState"), u = s || r2 ? i2 : l2, d = A("itemContent"), m = A("context"), S = A("groupContent"), h = A("trackItemSizes"), T = A("itemSize"), w = A("log"), R = Rt("gap"), g = A("horizontalDirection"), { callbackRef: f } = Fn(
    o,
    T,
    h,
    e ? Qt : u,
    w,
    R,
    s,
    g,
    A("skipAnimationFrameInResizeObserver")
  ), [a2, I] = E.useState(0);
  tn("deviation", (L) => {
    a2 !== L && I(L);
  });
  const b = A("EmptyPlaceholder"), y = A("ScrollSeekPlaceholder") || sr, z = A("ListComponent"), c = A("ItemComponent"), p = A("GroupComponent"), v = A("computeItemKey"), O = A("isSeeking"), B = A("groupIndices").length > 0, W = A("alignToBottom"), _ = A("initialItemFinalLocationReached"), j = e ? {} : {
    boxSizing: "border-box",
    ...g ? {
      display: "inline-block",
      height: "100%",
      marginLeft: a2 !== 0 ? a2 : W ? "auto" : 0,
      paddingLeft: n2.offsetTop,
      paddingRight: n2.offsetBottom,
      whiteSpace: "nowrap"
    } : {
      marginTop: a2 !== 0 ? a2 : W ? "auto" : 0,
      paddingBottom: n2.offsetBottom,
      paddingTop: n2.offsetTop
    },
    ..._ ? {} : { visibility: "hidden" }
  };
  return !e && n2.totalCount === 0 && b ? /* @__PURE__ */ jsxRuntimeExports.jsx(b, { ...Q(b, m) }) : /* @__PURE__ */ jsxRuntimeExports.jsx(
    z,
    {
      ...Q(z, m),
      "data-testid": e ? "virtuoso-top-item-list" : "virtuoso-item-list",
      ref: f,
      style: j,
      children: (e ? n2.topItems : n2.items).map((L) => {
        const xt = L.originalIndex, M = v(xt + n2.firstItemIndex, L.data, m);
        return O ? /* @__PURE__ */ reactExports.createElement(
          y,
          {
            ...Q(y, m),
            height: L.size,
            index: L.index,
            key: M,
            type: L.type || "item",
            ...L.type === "group" ? {} : { groupIndex: L.groupIndex }
          }
        ) : L.type === "group" ? /* @__PURE__ */ reactExports.createElement(
          p,
          {
            ...Q(p, m),
            "data-index": xt,
            "data-item-index": L.index,
            "data-known-size": L.size,
            key: M,
            style: ir
          },
          S(L.index, m)
        ) : /* @__PURE__ */ reactExports.createElement(
          c,
          {
            ...Q(c, m),
            ...oo(c, L.data),
            "data-index": xt,
            "data-item-group-index": L.groupIndex,
            "data-item-index": L.index,
            "data-known-size": L.size,
            key: M,
            style: g ? lr : no
          },
          B ? d(L.index, L.groupIndex, L.data, m) : d(L.index, L.data, m)
        );
      })
    }
  );
}), cr = {
  height: "100%",
  outline: "none",
  overflowY: "auto",
  position: "relative",
  WebkitOverflowScrolling: "touch"
}, ur = {
  outline: "none",
  overflowX: "auto",
  position: "relative"
}, te = (t2) => ({
  height: "100%",
  position: "absolute",
  top: 0,
  width: "100%",
  ...t2 ? { display: "flex", flexDirection: "column" } : {}
}), ar = {
  position: Ze(),
  top: 0,
  width: "100%",
  zIndex: 1
};
function Q(t2, e) {
  if (typeof t2 != "string")
    return { context: e };
}
function oo(t2, e) {
  return { item: typeof t2 == "string" ? void 0 : e };
}
const dr = /* @__PURE__ */ E.memo(function() {
  const e = A("HeaderComponent"), n2 = Rt("headerHeight"), o = A("HeaderFooterTag"), r2 = Vt$1(
    E.useMemo(
      () => (i2) => {
        n2(zt(i2, "height"));
      },
      [n2]
    ),
    true,
    A("skipAnimationFrameInResizeObserver")
  ), s = A("context");
  return e ? /* @__PURE__ */ jsxRuntimeExports.jsx(o, { ref: r2, children: /* @__PURE__ */ jsxRuntimeExports.jsx(e, { ...Q(e, s) }) }) : null;
}), fr = /* @__PURE__ */ E.memo(function() {
  const e = A("FooterComponent"), n2 = Rt("footerHeight"), o = A("HeaderFooterTag"), r2 = Vt$1(
    E.useMemo(
      () => (i2) => {
        n2(zt(i2, "height"));
      },
      [n2]
    ),
    true,
    A("skipAnimationFrameInResizeObserver")
  ), s = A("context");
  return e ? /* @__PURE__ */ jsxRuntimeExports.jsx(o, { ref: r2, children: /* @__PURE__ */ jsxRuntimeExports.jsx(e, { ...Q(e, s) }) }) : null;
});
function Je({ useEmitter: t2, useEmitterValue: e, usePublisher: n2 }) {
  return E.memo(function({ children: s, style: i2, context: l2, ...u }) {
    const d = n2("scrollContainerState"), m = e("ScrollerComponent"), S = n2("smoothScrollTargetReached"), h = e("scrollerRef"), T = e("horizontalDirection") || false, { scrollByCallback: w, scrollerRef: R, scrollToCallback: g } = eo(
      d,
      S,
      m,
      h,
      void 0,
      T
    );
    return t2("scrollTo", g), t2("scrollBy", w), /* @__PURE__ */ jsxRuntimeExports.jsx(
      m,
      {
        "data-testid": "virtuoso-scroller",
        "data-virtuoso-scroller": true,
        ref: R,
        style: { ...T ? ur : cr, ...i2 },
        tabIndex: 0,
        ...u,
        ...Q(m, l2),
        children: s
      }
    );
  });
}
function Qe({ useEmitter: t2, useEmitterValue: e, usePublisher: n2 }) {
  return E.memo(function({ children: s, style: i2, context: l2, ...u }) {
    const d = n2("windowScrollContainerState"), m = e("ScrollerComponent"), S = n2("smoothScrollTargetReached"), h = e("totalListHeight"), T = e("deviation"), w = e("customScrollParent"), R = E.useRef(null), g = e("scrollerRef"), { scrollByCallback: f, scrollerRef: a2, scrollToCallback: I } = eo(
      d,
      S,
      m,
      g,
      w
    );
    return to(() => {
      var b;
      return a2.current = w || ((b = R.current) == null ? void 0 : b.ownerDocument.defaultView), () => {
        a2.current = null;
      };
    }, [a2, w]), t2("windowScrollTo", I), t2("scrollBy", f), /* @__PURE__ */ jsxRuntimeExports.jsx(
      m,
      {
        ref: R,
        "data-virtuoso-scroller": true,
        style: { position: "relative", ...i2, ...h !== 0 ? { height: h + T } : {} },
        ...u,
        ...Q(m, l2),
        children: s
      }
    );
  });
}
const mr = ({ children: t2 }) => {
  const e = E.useContext(Re), n2 = Rt("viewportHeight"), o = Rt("fixedItemHeight"), r2 = A("alignToBottom"), s = A("horizontalDirection"), i2 = E.useMemo(
    () => se(n2, (u) => zt(u, s ? "width" : "height")),
    [n2, s]
  ), l2 = Vt$1(i2, true, A("skipAnimationFrameInResizeObserver"));
  return E.useEffect(() => {
    e && (n2(e.viewportHeight), o(e.itemHeight));
  }, [e, n2, o]), /* @__PURE__ */ jsxRuntimeExports.jsx("div", { "data-viewport-type": "element", ref: l2, style: te(r2), children: t2 });
}, pr = ({ children: t2 }) => {
  const e = E.useContext(Re), n2 = Rt("windowViewportRect"), o = Rt("fixedItemHeight"), r2 = A("customScrollParent"), s = Ne(
    n2,
    r2,
    A("skipAnimationFrameInResizeObserver")
  ), i2 = A("alignToBottom");
  return E.useEffect(() => {
    e && (o(e.itemHeight), n2({ offsetTop: 0, visibleHeight: e.viewportHeight, visibleWidth: 100 }));
  }, [e, n2, o]), /* @__PURE__ */ jsxRuntimeExports.jsx("div", { "data-viewport-type": "window", ref: s, style: te(i2), children: t2 });
}, hr$1 = ({ children: t2 }) => {
  const e = A("TopItemListComponent") || "div", n2 = A("headerHeight"), o = { ...ar, marginTop: `${n2}px` }, r2 = A("context");
  return /* @__PURE__ */ jsxRuntimeExports.jsx(e, { style: o, ...Q(e, r2), children: t2 });
}, gr = /* @__PURE__ */ E.memo(function(e) {
  const n2 = A("useWindowScroll"), o = A("topItemsIndexes").length > 0, r2 = A("customScrollParent"), s = A("context");
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(r2 || n2 ? xr : Ir, { ...e, context: s, children: [
    o && /* @__PURE__ */ jsxRuntimeExports.jsx(hr$1, { children: /* @__PURE__ */ jsxRuntimeExports.jsx(wn, { showTopList: true }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(r2 || n2 ? pr : mr, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(dr, {}),
      /* @__PURE__ */ jsxRuntimeExports.jsx(wn, {}),
      /* @__PURE__ */ jsxRuntimeExports.jsx(fr, {})
    ] })
  ] });
}), {
  Component: ro,
  useEmitter: tn,
  useEmitterValue: A,
  usePublisher: Rt
} = /* @__PURE__ */ Ye(
  rr,
  {
    required: {},
    optional: {
      restoreStateFrom: "restoreStateFrom",
      context: "context",
      followOutput: "followOutput",
      scrollIntoViewOnChange: "scrollIntoViewOnChange",
      itemContent: "itemContent",
      groupContent: "groupContent",
      overscan: "overscan",
      increaseViewportBy: "increaseViewportBy",
      minOverscanItemCount: "minOverscanItemCount",
      totalCount: "totalCount",
      groupCounts: "groupCounts",
      topItemCount: "topItemCount",
      firstItemIndex: "firstItemIndex",
      initialTopMostItemIndex: "initialTopMostItemIndex",
      components: "components",
      atBottomThreshold: "atBottomThreshold",
      atTopThreshold: "atTopThreshold",
      computeItemKey: "computeItemKey",
      defaultItemHeight: "defaultItemHeight",
      fixedGroupHeight: "fixedGroupHeight",
      // Must be set above 'fixedItemHeight'
      fixedItemHeight: "fixedItemHeight",
      heightEstimates: "heightEstimates",
      itemSize: "itemSize",
      scrollSeekConfiguration: "scrollSeekConfiguration",
      headerFooterTag: "HeaderFooterTag",
      data: "data",
      initialItemCount: "initialItemCount",
      initialScrollTop: "initialScrollTop",
      alignToBottom: "alignToBottom",
      useWindowScroll: "useWindowScroll",
      customScrollParent: "customScrollParent",
      scrollerRef: "scrollerRef",
      logLevel: "logLevel",
      horizontalDirection: "horizontalDirection",
      skipAnimationFrameInResizeObserver: "skipAnimationFrameInResizeObserver"
    },
    methods: {
      scrollToIndex: "scrollToIndex",
      scrollIntoView: "scrollIntoView",
      scrollTo: "scrollTo",
      scrollBy: "scrollBy",
      autoscrollToBottom: "autoscrollToBottom",
      getState: "getState"
    },
    events: {
      isScrolling: "isScrolling",
      endReached: "endReached",
      startReached: "startReached",
      rangeChanged: "rangeChanged",
      atBottomStateChange: "atBottomStateChange",
      atTopStateChange: "atTopStateChange",
      totalListHeightChanged: "totalListHeightChanged",
      itemsRendered: "itemsRendered",
      groupIndices: "groupIndices"
    }
  },
  gr
), Ir = /* @__PURE__ */ Je({ useEmitter: tn, useEmitterValue: A, usePublisher: Rt }), xr = /* @__PURE__ */ Qe({ useEmitter: tn, useEmitterValue: A, usePublisher: Rt }), Yr = ro, Sr = /* @__PURE__ */ K(() => {
  const t2 = C((d) => /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { children: [
    "Item $",
    d
  ] })), e = C(null), n2 = C((d) => /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { colSpan: 1e3, children: [
    "Group ",
    d
  ] })), o = C(null), r2 = C(null), s = C({}), i2 = C(Xe), l2 = C(Qt), u = (d, m = null) => ht(
    x(
      s,
      k((S) => S[d]),
      J()
    ),
    m
  );
  return {
    components: s,
    computeItemKey: i2,
    context: e,
    EmptyPlaceholder: u("EmptyPlaceholder"),
    FillerRow: u("FillerRow"),
    fixedFooterContent: r2,
    fixedHeaderContent: o,
    itemContent: t2,
    groupContent: n2,
    ScrollerComponent: u("Scroller", "div"),
    scrollerRef: l2,
    ScrollSeekPlaceholder: u("ScrollSeekPlaceholder"),
    TableBodyComponent: u("TableBody", "tbody"),
    TableComponent: u("Table", "table"),
    TableFooterComponent: u("TableFoot", "tfoot"),
    TableHeadComponent: u("TableHead", "thead"),
    TableRowComponent: u("TableRow", "tr"),
    GroupComponent: u("Group", "tr")
  };
});
/* @__PURE__ */ K(
  ([t2, e]) => ({ ...t2, ...e }),
  tt(Jn, Sr)
);
({ position: Ze() });
const bn = {
  bottom: 0,
  itemHeight: 0,
  items: [],
  itemWidth: 0,
  offsetBottom: 0,
  offsetTop: 0,
  top: 0
}, kr = {
  bottom: 0,
  itemHeight: 0,
  items: [{ index: 0 }],
  itemWidth: 0,
  offsetBottom: 0,
  offsetTop: 0,
  top: 0
}, { ceil: Rn, floor: we, max: re, min: Oe, round: Hn } = Math;
function En(t2, e, n2) {
  return Array.from({ length: e - t2 + 1 }).map((o, r2) => ({ data: n2 === null ? null : n2[r2 + t2], index: r2 + t2 }));
}
function zr(t2) {
  return {
    ...kr,
    items: t2
  };
}
function xe(t2, e) {
  return t2 && t2.width === e.width && t2.height === e.height;
}
function Or(t2, e) {
  return t2 && t2.column === e.column && t2.row === e.row;
}
const Fr = /* @__PURE__ */ K(
  ([
    { increaseViewportBy: t2, listBoundary: e, overscan: n2, visibleRange: o },
    { footerHeight: r2, headerHeight: s, scrollBy: i2, scrollContainerState: l2, scrollTo: u, scrollTop: d, smoothScrollTargetReached: m, viewportHeight: S },
    h,
    T,
    { didMount: w, propsReady: R },
    { customScrollParent: g, useWindowScroll: f, windowScrollContainerState: a2, windowScrollTo: I, windowViewportRect: b },
    y
  ]) => {
    const z = C(0), c = C(0), p = C(bn), v = C({ height: 0, width: 0 }), O = C({ height: 0, width: 0 }), B = U(), W = U(), _ = C(0), j = C(null), L = C({ column: 0, row: 0 }), xt = U(), M = U(), et = C(false), wt = C(0), ft = C(true), St = C(false), Mt = C(false);
    Y(
      x(
        w,
        $(wt),
        P$1(([H, q]) => !!q)
      ),
      () => {
        D(ft, false);
      }
    ), Y(
      x(
        ut(w, ft, O, v, wt, St),
        P$1(([H, q, at, gt, , Tt]) => H && !q && at.height !== 0 && gt.height !== 0 && !Tt)
      ),
      ([, , , , H]) => {
        D(St, true), Ue(1, () => {
          D(B, H);
        }), Et(x(d), () => {
          D(e, [0, 0]), D(ft, true);
        });
      }
    ), F(
      x(
        M,
        P$1((H) => H != null && H.scrollTop > 0),
        Ft(0)
      ),
      c
    ), Y(
      x(
        w,
        $(M),
        P$1(([, H]) => H != null)
      ),
      ([, H]) => {
        H && (D(v, H.viewport), D(O, H.item), D(L, H.gap), H.scrollTop > 0 && (D(et, true), Et(x(d, Kt(1)), (q) => {
          D(et, false);
        }), D(u, { top: H.scrollTop })));
      }
    ), F(
      x(
        v,
        k(({ height: H }) => H)
      ),
      S
    ), F(
      x(
        ut(
          V(v, xe),
          V(O, xe),
          V(L, (H, q) => H && H.column === q.column && H.row === q.row),
          V(d)
        ),
        k(([H, q, at, gt]) => ({
          gap: at,
          item: q,
          scrollTop: gt,
          viewport: H
        }))
      ),
      xt
    ), F(
      x(
        ut(
          V(z),
          o,
          V(L, Or),
          V(O, xe),
          V(v, xe),
          V(j),
          V(c),
          V(et),
          V(ft),
          V(wt)
        ),
        P$1(([, , , , , , , H]) => !H),
        k(
          ([
            H,
            [q, at],
            gt,
            Tt,
            st,
            it,
            mt,
            ,
            lt,
            Z2
          ]) => {
            const { column: nt, row: vt2 } = gt, { height: ct, width: He } = Tt, { width: nn } = st;
            if (mt === 0 && (H === 0 || nn === 0))
              return bn;
            if (He === 0) {
              const cn = Ke(Z2, H), uo = cn + Math.max(mt - 1, 0);
              return zr(En(cn, uo, it));
            }
            const ge = io(nn, He, nt);
            let Yt, Nt;
            lt ? q === 0 && at === 0 && mt > 0 ? (Yt = 0, Nt = mt - 1) : (Yt = ge * we((q + vt2) / (ct + vt2)), Nt = ge * Rn((at + vt2) / (ct + vt2)) - 1, Nt = Oe(H - 1, re(Nt, ge - 1)), Yt = Oe(Nt, re(0, Yt))) : (Yt = 0, Nt = -1);
            const on = En(Yt, Nt, it), { bottom: rn, top: sn } = Bn(st, gt, Tt, on), ln = Rn(H / ge), co = ln * ct + (ln - 1) * vt2 - rn;
            return { bottom: rn, itemHeight: ct, items: on, itemWidth: He, offsetBottom: co, offsetTop: sn, top: sn };
          }
        )
      ),
      p
    ), F(
      x(
        j,
        P$1((H) => H !== null),
        k((H) => H.length)
      ),
      z
    ), F(
      x(
        ut(v, O, p, L),
        P$1(([H, q, { items: at }]) => at.length > 0 && q.height !== 0 && H.height !== 0),
        k(([H, q, { items: at }, gt]) => {
          const { bottom: Tt, top: st } = Bn(H, gt, q, at);
          return [st, Tt];
        }),
        J(ce)
      ),
      e
    );
    const pt = C(false);
    F(
      x(
        d,
        $(pt),
        k(([H, q]) => q || H !== 0)
      ),
      pt
    );
    const qt = bt(
      x(
        ut(p, z),
        P$1(([{ items: H }]) => H.length > 0),
        $(pt),
        P$1(([[H, q], at]) => {
          const Tt = H.items[H.items.length - 1].index === q - 1;
          return (at || H.bottom > 0 && H.itemHeight > 0 && H.offsetBottom === 0 && H.items.length === q) && Tt;
        }),
        k(([[, H]]) => H - 1),
        J()
      )
    ), ee = bt(
      x(
        V(p),
        P$1(({ items: H }) => H.length > 0 && H[0].index === 0),
        Ft(0),
        J()
      )
    ), Ot = bt(
      x(
        V(p),
        $(et),
        P$1(([{ items: H }, q]) => H.length > 0 && !q),
        k(([{ items: H }]) => ({
          endIndex: H[H.length - 1].index,
          startIndex: H[0].index
        })),
        J(An),
        Gt(0)
      )
    );
    F(Ot, T.scrollSeekRangeChanged), F(
      x(
        B,
        $(v, O, z, L),
        k(([H, q, at, gt, Tt]) => {
          const st = $n(H), { align: it, behavior: mt, offset: lt } = st;
          let Z2 = st.index;
          Z2 === "LAST" && (Z2 = gt - 1), Z2 = re(0, Z2, Oe(gt - 1, Z2));
          let nt = Me(q, Tt, at, Z2);
          return it === "end" ? nt = Hn(nt - q.height + at.height) : it === "center" && (nt = Hn(nt - q.height / 2 + at.height / 2)), lt && (nt += lt), { behavior: mt, top: nt };
        })
      ),
      u
    );
    const ne = ht(
      x(
        p,
        k((H) => H.offsetBottom + H.bottom)
      ),
      0
    );
    return F(
      x(
        b,
        k((H) => ({ height: H.visibleHeight, width: H.visibleWidth }))
      ),
      v
    ), {
      customScrollParent: g,
      // input
      data: j,
      deviation: _,
      footerHeight: r2,
      gap: L,
      headerHeight: s,
      increaseViewportBy: t2,
      initialItemCount: c,
      itemDimensions: O,
      overscan: n2,
      restoreStateFrom: M,
      scrollBy: i2,
      scrollContainerState: l2,
      scrollHeight: W,
      scrollTo: u,
      scrollToIndex: B,
      scrollTop: d,
      smoothScrollTargetReached: m,
      totalCount: z,
      useWindowScroll: f,
      viewportDimensions: v,
      windowScrollContainerState: a2,
      windowScrollTo: I,
      windowViewportRect: b,
      ...T,
      // output
      gridState: p,
      horizontalDirection: Mt,
      initialTopMostItemIndex: wt,
      totalListHeight: ne,
      ...h,
      endReached: qt,
      propsReady: R,
      rangeChanged: Ot,
      startReached: ee,
      stateChanged: xt,
      stateRestoreInProgress: et,
      ...y
    };
  },
  tt(je, It, he, Zn, _t, qe, Wt)
);
function io(t2, e, n2) {
  return re(1, we((t2 + n2) / (we(e) + n2)));
}
function Bn(t2, e, n2, o) {
  const { height: r2 } = n2;
  if (r2 === void 0 || o.length === 0)
    return { bottom: 0, top: 0 };
  const s = Me(t2, e, n2, o[0].index);
  return { bottom: Me(t2, e, n2, o[o.length - 1].index) + r2, top: s };
}
function Me(t2, e, n2, o) {
  const r2 = io(t2.width, n2.width, e.column), s = we(o / r2), i2 = s * n2.height + re(0, s - 1) * e.row;
  return i2 > 0 ? i2 + e.row : i2;
}
const Lr = /* @__PURE__ */ K(() => {
  const t2 = C((S) => `Item ${S}`), e = C({}), n2 = C(null), o = C("virtuoso-grid-item"), r2 = C("virtuoso-grid-list"), s = C(Xe), i2 = C("div"), l2 = C(Qt), u = (S, h = null) => ht(
    x(
      e,
      k((T) => T[S]),
      J()
    ),
    h
  ), d = C(false), m = C(false);
  return F(V(m), d), {
    components: e,
    computeItemKey: s,
    context: n2,
    FooterComponent: u("Footer"),
    HeaderComponent: u("Header"),
    headerFooterTag: i2,
    itemClassName: o,
    ItemComponent: u("Item", "div"),
    itemContent: t2,
    listClassName: r2,
    ListComponent: u("List", "div"),
    readyStateChanged: d,
    reportReadyState: m,
    ScrollerComponent: u("Scroller", "div"),
    scrollerRef: l2,
    ScrollSeekPlaceholder: u("ScrollSeekPlaceholder", "div")
  };
}), Vr = /* @__PURE__ */ K(
  ([t2, e]) => ({ ...t2, ...e }),
  tt(Fr, Lr)
), Pr = /* @__PURE__ */ E.memo(function() {
  const e = ot("gridState"), n2 = ot("listClassName"), o = ot("itemClassName"), r2 = ot("itemContent"), s = ot("computeItemKey"), i2 = ot("isSeeking"), l2 = Ht("scrollHeight"), u = ot("ItemComponent"), d = ot("ListComponent"), m = ot("ScrollSeekPlaceholder"), S = ot("context"), h = Ht("itemDimensions"), T = Ht("gap"), w = ot("log"), R = ot("stateRestoreInProgress"), g = Ht("reportReadyState"), f = Vt$1(
    E.useMemo(
      () => (a2) => {
        const I = a2.parentElement.parentElement.scrollHeight;
        l2(I);
        const b = a2.firstChild;
        if (b) {
          const { height: y, width: z } = b.getBoundingClientRect();
          h({ height: y, width: z });
        }
        T({
          column: kn("column-gap", getComputedStyle(a2).columnGap, w),
          row: kn("row-gap", getComputedStyle(a2).rowGap, w)
        });
      },
      [l2, h, T, w]
    ),
    true,
    false
  );
  return to(() => {
    e.itemHeight > 0 && e.itemWidth > 0 && g(true);
  }, [e]), R ? null : /* @__PURE__ */ jsxRuntimeExports.jsx(
    d,
    {
      className: n2,
      ref: f,
      ...Q(d, S),
      "data-testid": "virtuoso-item-list",
      style: { paddingBottom: e.offsetBottom, paddingTop: e.offsetTop },
      children: e.items.map((a2) => {
        const I = s(a2.index, a2.data, S);
        return i2 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          m,
          {
            ...Q(m, S),
            height: e.itemHeight,
            index: a2.index,
            width: e.itemWidth
          },
          I
        ) : /* @__PURE__ */ reactExports.createElement(
          u,
          {
            ...Q(u, S),
            className: o,
            "data-index": a2.index,
            key: I
          },
          r2(a2.index, a2.data, S)
        );
      })
    }
  );
}), Gr = E.memo(function() {
  const e = ot("HeaderComponent"), n2 = Ht("headerHeight"), o = ot("headerFooterTag"), r2 = Vt$1(
    E.useMemo(
      () => (i2) => {
        n2(zt(i2, "height"));
      },
      [n2]
    ),
    true,
    false
  ), s = ot("context");
  return e ? /* @__PURE__ */ jsxRuntimeExports.jsx(o, { ref: r2, children: /* @__PURE__ */ jsxRuntimeExports.jsx(e, { ...Q(e, s) }) }) : null;
}), Mr = E.memo(function() {
  const e = ot("FooterComponent"), n2 = Ht("footerHeight"), o = ot("headerFooterTag"), r2 = Vt$1(
    E.useMemo(
      () => (i2) => {
        n2(zt(i2, "height"));
      },
      [n2]
    ),
    true,
    false
  ), s = ot("context");
  return e ? /* @__PURE__ */ jsxRuntimeExports.jsx(o, { ref: r2, children: /* @__PURE__ */ jsxRuntimeExports.jsx(e, { ...Q(e, s) }) }) : null;
}), Ar = ({ children: t2 }) => {
  const e = E.useContext(Qn), n2 = Ht("itemDimensions"), o = Ht("viewportDimensions"), r2 = Vt$1(
    E.useMemo(
      () => (s) => {
        o(s.getBoundingClientRect());
      },
      [o]
    ),
    true,
    false
  );
  return E.useEffect(() => {
    e && (o({ height: e.viewportHeight, width: e.viewportWidth }), n2({ height: e.itemHeight, width: e.itemWidth }));
  }, [e, o, n2]), /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: r2, style: te(false), children: t2 });
}, Wr = ({ children: t2 }) => {
  const e = E.useContext(Qn), n2 = Ht("windowViewportRect"), o = Ht("itemDimensions"), r2 = ot("customScrollParent"), s = Ne(n2, r2, false);
  return E.useEffect(() => {
    e && (o({ height: e.itemHeight, width: e.itemWidth }), n2({ offsetTop: 0, visibleHeight: e.viewportHeight, visibleWidth: e.viewportWidth }));
  }, [e, n2, o]), /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: s, style: te(false), children: t2 });
}, _r = /* @__PURE__ */ E.memo(function({ ...e }) {
  const n2 = ot("useWindowScroll"), o = ot("customScrollParent"), r2 = o || n2 ? $r : Dr, s = o || n2 ? Wr : Ar, i2 = ot("context");
  return /* @__PURE__ */ jsxRuntimeExports.jsx(r2, { ...e, ...Q(r2, i2), children: /* @__PURE__ */ jsxRuntimeExports.jsxs(s, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(Gr, {}),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Pr, {}),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Mr, {})
  ] }) });
}), {
  useEmitter: lo,
  useEmitterValue: ot,
  usePublisher: Ht
} = /* @__PURE__ */ Ye(
  Vr,
  {
    optional: {
      context: "context",
      totalCount: "totalCount",
      overscan: "overscan",
      itemContent: "itemContent",
      components: "components",
      computeItemKey: "computeItemKey",
      data: "data",
      initialItemCount: "initialItemCount",
      scrollSeekConfiguration: "scrollSeekConfiguration",
      headerFooterTag: "headerFooterTag",
      listClassName: "listClassName",
      itemClassName: "itemClassName",
      useWindowScroll: "useWindowScroll",
      customScrollParent: "customScrollParent",
      scrollerRef: "scrollerRef",
      logLevel: "logLevel",
      restoreStateFrom: "restoreStateFrom",
      initialTopMostItemIndex: "initialTopMostItemIndex",
      increaseViewportBy: "increaseViewportBy"
    },
    methods: {
      scrollTo: "scrollTo",
      scrollBy: "scrollBy",
      scrollToIndex: "scrollToIndex"
    },
    events: {
      isScrolling: "isScrolling",
      endReached: "endReached",
      startReached: "startReached",
      rangeChanged: "rangeChanged",
      atBottomStateChange: "atBottomStateChange",
      atTopStateChange: "atTopStateChange",
      stateChanged: "stateChanged",
      readyStateChanged: "readyStateChanged"
    }
  },
  _r
), Dr = /* @__PURE__ */ Je({ useEmitter: lo, useEmitterValue: ot, usePublisher: Ht }), $r = /* @__PURE__ */ Qe({ useEmitter: lo, useEmitterValue: ot, usePublisher: Ht });
function kn(t2, e, n2) {
  return e !== "normal" && !(e != null && e.endsWith("px")) && n2(`${t2} was not resolved to pixel value correctly`, e, Ct.WARN), e === "normal" ? 0 : parseInt(e != null ? e : "0", 10);
}
const useCollapsibleIds = (key2) => {
  const collapsedIds = useStore((state) => state.collapsedBuckets[key2]);
  const setCollapsed = useStore((state) => state.setCollapsed);
  const collapseId = reactExports.useCallback(
    (id, value2) => {
      setCollapsed(key2, id, value2);
    },
    [key2, setCollapsed]
  );
  const clearCollapsedIds = useStore((state) => state.clearCollapsed);
  const clearIds = reactExports.useCallback(() => {
    clearCollapsedIds(key2);
  }, [clearCollapsedIds, key2]);
  return reactExports.useMemo(() => {
    return [collapsedIds || {}, collapseId, clearIds];
  }, [collapsedIds, collapseId, clearIds]);
};
const useCollapsedState = (id, defaultValue, scope) => {
  const resolvedScope = "collapse-state-scope";
  const collapsed = useStore(
    (state) => state.collapsedBuckets[resolvedScope]?.[id]
  );
  const setCollapsed = useStore((state) => state.setCollapsed);
  return reactExports.useMemo(() => {
    const set2 = (value2) => {
      setCollapsed(resolvedScope, id, value2);
    };
    return [collapsed ?? defaultValue ?? false, set2];
  }, [collapsed, resolvedScope, defaultValue, setCollapsed, id]);
};
const expandablePanel = "_expandablePanel_1ka1g_1";
const expandableBordered = "_expandableBordered_1ka1g_5";
const expandableCollapsed = "_expandableCollapsed_1ka1g_18";
const moreToggle = "_moreToggle_1ka1g_22";
const bordered = "_bordered_1ka1g_32";
const moreToggleButton = "_moreToggleButton_1ka1g_36";
const separator$4 = "_separator_1ka1g_44";
const inlineRight = "_inlineRight_1ka1g_50";
const blockLeft = "_blockLeft_1ka1g_56";
const styles$K = {
  expandablePanel,
  expandableBordered,
  expandableCollapsed,
  moreToggle,
  bordered,
  moreToggleButton,
  separator: separator$4,
  inlineRight,
  blockLeft
};
const ExpandablePanel = reactExports.memo(
  ({
    id,
    collapse,
    border,
    lines = 15,
    children: children2,
    className: className2,
    togglePosition: layout = "inline-right"
  }) => {
    const [collapsed, setCollapsed] = useCollapsedState(id, collapse);
    const [showToggle, setShowToggle] = reactExports.useState(false);
    const baseFontSizeRef = reactExports.useRef(0);
    const checkOverflow = reactExports.useCallback(
      (entry) => {
        const element = entry.target;
        if (baseFontSizeRef.current === 0) {
          const computedStyle = window.getComputedStyle(element);
          const rootFontSize = parseFloat(computedStyle.fontSize);
          baseFontSizeRef.current = rootFontSize;
        }
        const maxCollapsedHeight = baseFontSizeRef.current * lines;
        const contentHeight = element.scrollHeight;
        setShowToggle(contentHeight > maxCollapsedHeight);
      },
      [lines]
    );
    const contentRef = useResizeObserver(checkOverflow);
    const baseStyles = {
      overflow: "hidden",
      ...collapsed && {
        maxHeight: `${lines}rem`
      }
    };
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(className2), children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          style: baseStyles,
          ref: contentRef,
          className: clsx(
            styles$K.expandablePanel,
            collapsed ? styles$K.expandableCollapsed : void 0,
            border ? styles$K.expandableBordered : void 0,
            showToggle ? styles$K.padBottom : void 0,
            className2
          ),
          children: [
            children2,
            showToggle && layout === "inline-right" && /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              MoreToggle,
              {
                collapsed,
                setCollapsed,
                border: !border,
                position: "inline-right"
              }
            ) })
          ]
        }
      ),
      showToggle && layout === "block-left" && /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        MoreToggle,
        {
          collapsed,
          setCollapsed,
          border: !border,
          position: "block-left"
        }
      ) }),
      showToggle && layout === "inline-right" && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$K.separator) })
    ] });
  }
);
const MoreToggle = ({
  collapsed,
  border,
  setCollapsed,
  style: style2,
  position
}) => {
  const text2 = collapsed ? "more" : "less";
  const handleClick = reactExports.useCallback(() => {
    setCollapsed(!collapsed);
  }, [setCollapsed, collapsed]);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: clsx(
        styles$K.moreToggle,
        border ? styles$K.bordered : void 0,
        position === "inline-right" ? styles$K.inlineRight : styles$K.blockLeft
      ),
      style: style2,
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          className: clsx(styles$K.moreToggleButton, "text-size-smallest"),
          onClick: handleClick,
          children: [
            text2,
            "..."
          ]
        }
      )
    }
  );
};
ExpandablePanel.displayName = "ExpandablePanel";
const kStoreInstanceKey = /^(.+)?:([a-zA-Z0-9]{22}):instance$/;
const kStoreKey = /^(.+)?:([a-zA-Z0-9]{22}):(.+)$/;
const resolveStoreKeys = (record) => {
  const result2 = {};
  const storeInstances = {};
  const instanceKeys = /* @__PURE__ */ new Set();
  const entries = Object.entries(record);
  for (let i2 = 0; i2 < entries.length; i2++) {
    const entry = entries[i2];
    if (!entry) continue;
    const [key2, value2] = entry;
    const instanceInfo = parseStoreInstanceKey(key2, value2);
    if (instanceInfo) {
      const { storeName, instanceId } = instanceInfo;
      if (!storeName) {
        continue;
      }
      const instanceKey = storeKey(storeName, instanceId);
      if (!storeInstances[instanceKey]) {
        storeInstances[instanceKey] = {};
      }
      instanceKeys.add(key2);
      continue;
    } else {
      const storeKeyInfo = parseStoreKey(key2);
      if (storeKeyInfo) {
        const { storeName, instanceId, keyName } = storeKeyInfo;
        if (!storeName || !instanceId || !keyName) {
          continue;
        }
        const instanceKey = storeKey(storeName, instanceId);
        if (storeInstances[instanceKey]) {
          storeInstances[instanceKey][keyName] = value2;
          continue;
        }
      } else {
        result2[key2] = value2;
      }
    }
  }
  for (const [instanceKey, children2] of Object.entries(storeInstances)) {
    result2[instanceKey] = resolveStoreKeys(children2);
  }
  for (const [key2, value2] of Object.entries(result2)) {
    if (typeof value2 === "object" && value2 !== null && !Array.isArray(value2)) {
      result2[key2] = resolveStoreKeys(value2);
    }
  }
  return result2;
};
const parseStoreInstanceKey = (key2, value2) => {
  const match2 = key2.match(kStoreInstanceKey);
  if (match2) {
    const [, storeName, instanceId] = match2;
    if (typeof value2 === "string" && instanceId === value2) {
      return {
        storeName,
        instanceId
      };
    }
  }
  return null;
};
const parseStoreKey = (key2) => {
  const match2 = key2.match(kStoreKey);
  if (match2) {
    const [, storeName, instanceId, keyName] = match2;
    if (keyName !== "instance") {
      return {
        storeName,
        instanceId,
        keyName
      };
    }
  }
  return null;
};
const storeKey = (storeName, instanceId) => {
  return `${storeName || ""} (${instanceId})`;
};
const keyPairContainer = "_keyPairContainer_qjlxf_1";
const keyPairBordered = "_keyPairBordered_qjlxf_9";
const key = "_key_qjlxf_1";
const pre = "_pre_qjlxf_19";
const treeIcon = "_treeIcon_qjlxf_23";
const styles$J = {
  keyPairContainer,
  keyPairBordered,
  key,
  pre,
  treeIcon
};
const kRecordTreeKey = "record-tree-key";
const RecordTree = ({
  id,
  record,
  className: className2,
  scrollRef,
  defaultExpandLevel = 1,
  processStore = false,
  useBorders = true
}) => {
  const listHandle = reactExports.useRef(null);
  const { getRestoreState } = useVirtuosoState(
    listHandle,
    `metadata-grid-${id}`
  );
  const [collapsedIds, setCollapsed, clearIds] = useCollapsibleIds(id);
  const setCollapsedIds = reactExports.useCallback(
    (values) => {
      Object.entries(values).forEach(([key2, value2]) => {
        setCollapsed(key2, value2);
      });
    },
    [setCollapsed]
  );
  reactExports.useEffect(() => {
    return () => {
      clearIds();
    };
  }, [clearIds, id]);
  const items = reactExports.useMemo(() => {
    const items2 = toTreeItems(
      record,
      collapsedIds || {},
      processStore ? [resolveStoreKeys] : []
    );
    return items2;
  }, [record, collapsedIds, processStore]);
  reactExports.useEffect(() => {
    if (collapsedIds) {
      return;
    }
    const defaultCollapsedIds = items.reduce(
      (prev, item) => {
        if (item.depth >= defaultExpandLevel && item.hasChildren) {
          prev[item.id] = true;
        }
        return prev;
      },
      {}
    );
    setCollapsedIds(defaultCollapsedIds);
  }, [collapsedIds, items]);
  const keyUpHandler = reactExports.useCallback(
    (itemId, index) => {
      return (event) => {
        switch (event.key) {
          case "Enter":
            event.preventDefault();
            event.stopPropagation();
            setCollapsed(itemId, !collapsedIds?.[id]);
            break;
          case "ArrowDown": {
            event.preventDefault();
            event.stopPropagation();
            if (index === items.length - 1) {
              return;
            }
            const treeRoot = document.getElementById(id);
            const nextEl = treeRoot?.querySelector(
              `.${kRecordTreeKey}[data-index="${index + 1}"]`
            );
            if (nextEl) {
              nextEl.focus();
            }
            break;
          }
          case "ArrowUp": {
            event.preventDefault();
            event.stopPropagation();
            if (index === 0) {
              return;
            }
            const treeRoot = document.getElementById(id);
            const prevEl = treeRoot?.querySelector(
              `.${kRecordTreeKey}[data-index="${index - 1}"]`
            );
            if (prevEl) {
              prevEl.focus();
            }
            break;
          }
          case "ArrowRight":
            event.preventDefault();
            event.stopPropagation();
            setCollapsed(itemId, false);
            break;
          case "ArrowLeft":
            event.preventDefault();
            event.stopPropagation();
            setCollapsed(itemId, true);
            break;
        }
      };
    },
    [collapsedIds, items]
  );
  const renderRow = (index) => {
    const item = items[index];
    if (!item) {
      return null;
    }
    return /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(
          styles$J.keyPairContainer,
          index < items.length - 1 && useBorders ? styles$J.keyPairBordered : void 0,
          "text-size-small"
        ),
        style: {
          paddingLeft: `${item.depth * 20}px`
        },
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "div",
            {
              "data-index": index,
              className: clsx(
                kRecordTreeKey,
                styles$J.key,
                "font-monospace",
                "text-style-secondary"
              ),
              onKeyUp: keyUpHandler(item.id, index),
              tabIndex: 0,
              onClick: () => {
                setCollapsed(item.id, !collapsedIds?.[item.id]);
              },
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: item.hasChildren ? /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: clsx(styles$J.pre), children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "i",
                  {
                    className: clsx(
                      collapsedIds && collapsedIds[item.id] ? ApplicationIcons.tree.closed : ApplicationIcons.tree.open,
                      styles$J.treeIcon
                    )
                  }
                ) }) : void 0 }),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("pre", { className: clsx(styles$J.pre), children: [
                  item.key,
                  ":"
                ] })
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: item.value !== null && (!item.hasChildren || collapsedIds?.[item.id]) ? /* @__PURE__ */ jsxRuntimeExports.jsx(
            ExpandablePanel,
            {
              id: `${id}-collapse-${item.id}`,
              collapse: true,
              lines: 15,
              togglePosition: "block-left",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                RenderedContent,
                {
                  id: `${id}-value-${item.id}`,
                  entry: {
                    name: item.key,
                    value: item.value
                  },
                  renderOptions: { renderString: "pre" }
                }
              )
            }
          ) : void 0 })
        ]
      },
      item.id
    );
  };
  if (!collapsedIds) {
    return null;
  }
  if (!scrollRef) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        id,
        className: clsx(className2, "samples-list"),
        style: { width: "100%" },
        tabIndex: 0,
        children: items.map((_, index) => renderRow(index))
      }
    );
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    Yr,
    {
      ref: listHandle,
      customScrollParent: scrollRef?.current ? scrollRef.current : void 0,
      id,
      style: { width: "100%", height: "100%" },
      data: items,
      defaultItemHeight: 50,
      itemContent: renderRow,
      atBottomThreshold: 30,
      increaseViewportBy: { top: 300, bottom: 300 },
      overscan: {
        main: 10,
        reverse: 10
      },
      className: clsx(className2, "samples-list"),
      skipAnimationFrameInResizeObserver: true,
      restoreStateFrom: getRestoreState(),
      tabIndex: 0
    }
  );
};
const toTreeItems = (record, collapsedIds, recordProcessors = [], currentDepth = 0, currentPath = []) => {
  if (!record) {
    return [];
  }
  if (recordProcessors.length > 0) {
    for (const processor of recordProcessors) {
      record = processor(record);
    }
  }
  const result2 = [];
  Object.entries(record).forEach(([key2, value2], index) => {
    const itemSegment = index.toString();
    result2.push(
      ...processNodeRecursive(
        key2,
        value2,
        currentDepth,
        currentPath,
        itemSegment,
        collapsedIds
      )
    );
  });
  return result2;
};
const processNodeRecursive = (key2, value2, depth, parentPath, thisPath, collapsedIds) => {
  const items = [];
  const currentItemPath = [...parentPath, thisPath];
  const id = `${depth}.${currentItemPath.join(".")}`;
  if (isPrimitiveOrNull(value2)) {
    items.push({
      id,
      key: key2,
      value: value2 === void 0 ? null : value2,
      depth,
      hasChildren: false
    });
    return items;
  }
  let displayValue = null;
  let processChildren = false;
  if (Array.isArray(value2)) {
    processChildren = true;
    displayValue = `Array(${value2.length})`;
  } else if (typeof value2 === "object" && value2 !== null) {
    processChildren = true;
    displayValue = `Object(${Object.keys(value2).length})`;
  } else {
    displayValue = String(value2);
    processChildren = false;
  }
  items.push({ id, key: key2, value: displayValue, depth, hasChildren: true });
  if (processChildren && !collapsedIds[id]) {
    const childDepth = depth + 1;
    if (Array.isArray(value2)) {
      if (value2.length > 0) {
        value2.forEach((element, index) => {
          const elementKey = `[${index}]`;
          const elementIdentifier = `[${index}]`;
          items.push(
            ...processNodeRecursive(
              elementKey,
              element,
              childDepth,
              currentItemPath,
              elementIdentifier,
              collapsedIds
            )
          );
        });
      }
    } else if (typeof value2 === "object" && value2 !== null) {
      Object.entries(value2).forEach(
        ([childKey, childValue], index) => {
          const childIdentifier = index.toString();
          items.push(
            ...processNodeRecursive(
              childKey,
              childValue,
              childDepth,
              currentItemPath,
              childIdentifier,
              collapsedIds
            )
          );
        }
      );
    }
  }
  return items;
};
const isPrimitiveOrNull = (value2) => {
  return value2 === null || value2 === void 0 || typeof value2 === "string" || typeof value2 === "number" || typeof value2 === "boolean";
};
const copyButton = "_copyButton_1goi8_1";
const styles$I = {
  copyButton
};
const CopyButton = ({
  icon = ApplicationIcons.copy,
  title: title2,
  value: value2,
  onCopySuccess,
  onCopyError,
  className: className2 = "",
  ariaLabel = "Copy to clipboard"
}) => {
  const [isCopied, setIsCopied] = reactExports.useState(false);
  const handleClick = async () => {
    try {
      await navigator.clipboard.writeText(value2);
      setIsCopied(true);
      onCopySuccess?.();
      setTimeout(() => {
        setIsCopied(false);
      }, 1250);
    } catch (error2) {
      onCopyError?.(
        error2 instanceof Error ? error2 : new Error("Failed to copy")
      );
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "button",
    {
      type: "button",
      className: clsx("copy-button", styles$I.copyButton, className2),
      onClick: () => {
        void handleClick();
      },
      "aria-label": ariaLabel,
      disabled: isCopied,
      title: title2,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "i",
        {
          className: isCopied ? `${ApplicationIcons.confirm} primary` : icon,
          "aria-hidden": "true"
        }
      )
    }
  );
};
const labeledValue = "_labeledValue_6obbb_1";
const row = "_row_6obbb_6";
const column = "_column_6obbb_10";
const labeledValueLabel = "_labeledValueLabel_6obbb_14";
const styles$H = {
  labeledValue,
  row,
  column,
  labeledValueLabel
};
const LabeledValue = ({
  layout = "column",
  style: style2,
  label: label2,
  children: children2,
  valueStyle,
  className: className2
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: clsx(
        styles$H.labeledValue,
        layout === "column" ? styles$H.column : styles$H.row,
        className2
      ),
      style: {
        ...style2
      },
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              styles$H.labeledValueLabel,
              "text-style-label",
              "text-style-secondary"
            ),
            children: label2
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$H.labeledValueValue), style: { ...valueStyle }, children: children2 })
      ]
    }
  );
};
const message = "_message_b8oe1_1";
const systemRole = "_systemRole_b8oe1_8";
const messageGrid = "_messageGrid_b8oe1_12";
const toolMessageGrid = "_toolMessageGrid_b8oe1_20";
const messageContents = "_messageContents_b8oe1_24";
const indented = "_indented_b8oe1_29";
const copyLink$1 = "_copyLink_b8oe1_33";
const metadataLabel = "_metadataLabel_b8oe1_43";
const hover$1 = "_hover_b8oe1_47";
const styles$G = {
  message,
  systemRole,
  messageGrid,
  toolMessageGrid,
  messageContents,
  indented,
  copyLink: copyLink$1,
  metadataLabel,
  hover: hover$1
};
const decodeCache = {};
function getDecodeCache(exclude) {
  let cache = decodeCache[exclude];
  if (cache) {
    return cache;
  }
  cache = decodeCache[exclude] = [];
  for (let i2 = 0; i2 < 128; i2++) {
    const ch = String.fromCharCode(i2);
    cache.push(ch);
  }
  for (let i2 = 0; i2 < exclude.length; i2++) {
    const ch = exclude.charCodeAt(i2);
    cache[ch] = "%" + ("0" + ch.toString(16).toUpperCase()).slice(-2);
  }
  return cache;
}
function decode$1(string, exclude) {
  if (typeof exclude !== "string") {
    exclude = decode$1.defaultChars;
  }
  const cache = getDecodeCache(exclude);
  return string.replace(/(%[a-f0-9]{2})+/gi, function(seq) {
    let result2 = "";
    for (let i2 = 0, l2 = seq.length; i2 < l2; i2 += 3) {
      const b1 = parseInt(seq.slice(i2 + 1, i2 + 3), 16);
      if (b1 < 128) {
        result2 += cache[b1];
        continue;
      }
      if ((b1 & 224) === 192 && i2 + 3 < l2) {
        const b2 = parseInt(seq.slice(i2 + 4, i2 + 6), 16);
        if ((b2 & 192) === 128) {
          const chr = b1 << 6 & 1984 | b2 & 63;
          if (chr < 128) {
            result2 += "��";
          } else {
            result2 += String.fromCharCode(chr);
          }
          i2 += 3;
          continue;
        }
      }
      if ((b1 & 240) === 224 && i2 + 6 < l2) {
        const b2 = parseInt(seq.slice(i2 + 4, i2 + 6), 16);
        const b3 = parseInt(seq.slice(i2 + 7, i2 + 9), 16);
        if ((b2 & 192) === 128 && (b3 & 192) === 128) {
          const chr = b1 << 12 & 61440 | b2 << 6 & 4032 | b3 & 63;
          if (chr < 2048 || chr >= 55296 && chr <= 57343) {
            result2 += "���";
          } else {
            result2 += String.fromCharCode(chr);
          }
          i2 += 6;
          continue;
        }
      }
      if ((b1 & 248) === 240 && i2 + 9 < l2) {
        const b2 = parseInt(seq.slice(i2 + 4, i2 + 6), 16);
        const b3 = parseInt(seq.slice(i2 + 7, i2 + 9), 16);
        const b4 = parseInt(seq.slice(i2 + 10, i2 + 12), 16);
        if ((b2 & 192) === 128 && (b3 & 192) === 128 && (b4 & 192) === 128) {
          let chr = b1 << 18 & 1835008 | b2 << 12 & 258048 | b3 << 6 & 4032 | b4 & 63;
          if (chr < 65536 || chr > 1114111) {
            result2 += "����";
          } else {
            chr -= 65536;
            result2 += String.fromCharCode(55296 + (chr >> 10), 56320 + (chr & 1023));
          }
          i2 += 9;
          continue;
        }
      }
      result2 += "�";
    }
    return result2;
  });
}
decode$1.defaultChars = ";/?:@&=+$,#";
decode$1.componentChars = "";
const encodeCache = {};
function getEncodeCache(exclude) {
  let cache = encodeCache[exclude];
  if (cache) {
    return cache;
  }
  cache = encodeCache[exclude] = [];
  for (let i2 = 0; i2 < 128; i2++) {
    const ch = String.fromCharCode(i2);
    if (/^[0-9a-z]$/i.test(ch)) {
      cache.push(ch);
    } else {
      cache.push("%" + ("0" + i2.toString(16).toUpperCase()).slice(-2));
    }
  }
  for (let i2 = 0; i2 < exclude.length; i2++) {
    cache[exclude.charCodeAt(i2)] = exclude[i2];
  }
  return cache;
}
function encode$1(string, exclude, keepEscaped) {
  if (typeof exclude !== "string") {
    keepEscaped = exclude;
    exclude = encode$1.defaultChars;
  }
  if (typeof keepEscaped === "undefined") {
    keepEscaped = true;
  }
  const cache = getEncodeCache(exclude);
  let result2 = "";
  for (let i2 = 0, l2 = string.length; i2 < l2; i2++) {
    const code2 = string.charCodeAt(i2);
    if (keepEscaped && code2 === 37 && i2 + 2 < l2) {
      if (/^[0-9a-f]{2}$/i.test(string.slice(i2 + 1, i2 + 3))) {
        result2 += string.slice(i2, i2 + 3);
        i2 += 2;
        continue;
      }
    }
    if (code2 < 128) {
      result2 += cache[code2];
      continue;
    }
    if (code2 >= 55296 && code2 <= 57343) {
      if (code2 >= 55296 && code2 <= 56319 && i2 + 1 < l2) {
        const nextCode = string.charCodeAt(i2 + 1);
        if (nextCode >= 56320 && nextCode <= 57343) {
          result2 += encodeURIComponent(string[i2] + string[i2 + 1]);
          i2++;
          continue;
        }
      }
      result2 += "%EF%BF%BD";
      continue;
    }
    result2 += encodeURIComponent(string[i2]);
  }
  return result2;
}
encode$1.defaultChars = ";/?:@&=+$,-_.!~*'()#";
encode$1.componentChars = "-_.!~*'()";
function format$1(url) {
  let result2 = "";
  result2 += url.protocol || "";
  result2 += url.slashes ? "//" : "";
  result2 += url.auth ? url.auth + "@" : "";
  if (url.hostname && url.hostname.indexOf(":") !== -1) {
    result2 += "[" + url.hostname + "]";
  } else {
    result2 += url.hostname || "";
  }
  result2 += url.port ? ":" + url.port : "";
  result2 += url.pathname || "";
  result2 += url.search || "";
  result2 += url.hash || "";
  return result2;
}
function Url() {
  this.protocol = null;
  this.slashes = null;
  this.auth = null;
  this.port = null;
  this.hostname = null;
  this.hash = null;
  this.search = null;
  this.pathname = null;
}
const protocolPattern = /^([a-z0-9.+-]+:)/i;
const portPattern = /:[0-9]*$/;
const simplePathPattern = /^(\/\/?(?!\/)[^\?\s]*)(\?[^\s]*)?$/;
const delims = ["<", ">", '"', "`", " ", "\r", "\n", "	"];
const unwise = ["{", "}", "|", "\\", "^", "`"].concat(delims);
const autoEscape = ["'"].concat(unwise);
const nonHostChars = ["%", "/", "?", ";", "#"].concat(autoEscape);
const hostEndingChars = ["/", "?", "#"];
const hostnameMaxLen = 255;
const hostnamePartPattern = /^[+a-z0-9A-Z_-]{0,63}$/;
const hostnamePartStart = /^([+a-z0-9A-Z_-]{0,63})(.*)$/;
const hostlessProtocol = {
  javascript: true,
  "javascript:": true
};
const slashedProtocol = {
  http: true,
  https: true,
  ftp: true,
  gopher: true,
  file: true,
  "http:": true,
  "https:": true,
  "ftp:": true,
  "gopher:": true,
  "file:": true
};
function urlParse(url, slashesDenoteHost) {
  if (url && url instanceof Url) return url;
  const u = new Url();
  u.parse(url, slashesDenoteHost);
  return u;
}
Url.prototype.parse = function(url, slashesDenoteHost) {
  let lowerProto, hec, slashes;
  let rest = url;
  rest = rest.trim();
  if (!slashesDenoteHost && url.split("#").length === 1) {
    const simplePath = simplePathPattern.exec(rest);
    if (simplePath) {
      this.pathname = simplePath[1];
      if (simplePath[2]) {
        this.search = simplePath[2];
      }
      return this;
    }
  }
  let proto = protocolPattern.exec(rest);
  if (proto) {
    proto = proto[0];
    lowerProto = proto.toLowerCase();
    this.protocol = proto;
    rest = rest.substr(proto.length);
  }
  if (slashesDenoteHost || proto || rest.match(/^\/\/[^@\/]+@[^@\/]+/)) {
    slashes = rest.substr(0, 2) === "//";
    if (slashes && !(proto && hostlessProtocol[proto])) {
      rest = rest.substr(2);
      this.slashes = true;
    }
  }
  if (!hostlessProtocol[proto] && (slashes || proto && !slashedProtocol[proto])) {
    let hostEnd = -1;
    for (let i2 = 0; i2 < hostEndingChars.length; i2++) {
      hec = rest.indexOf(hostEndingChars[i2]);
      if (hec !== -1 && (hostEnd === -1 || hec < hostEnd)) {
        hostEnd = hec;
      }
    }
    let auth, atSign;
    if (hostEnd === -1) {
      atSign = rest.lastIndexOf("@");
    } else {
      atSign = rest.lastIndexOf("@", hostEnd);
    }
    if (atSign !== -1) {
      auth = rest.slice(0, atSign);
      rest = rest.slice(atSign + 1);
      this.auth = auth;
    }
    hostEnd = -1;
    for (let i2 = 0; i2 < nonHostChars.length; i2++) {
      hec = rest.indexOf(nonHostChars[i2]);
      if (hec !== -1 && (hostEnd === -1 || hec < hostEnd)) {
        hostEnd = hec;
      }
    }
    if (hostEnd === -1) {
      hostEnd = rest.length;
    }
    if (rest[hostEnd - 1] === ":") {
      hostEnd--;
    }
    const host = rest.slice(0, hostEnd);
    rest = rest.slice(hostEnd);
    this.parseHost(host);
    this.hostname = this.hostname || "";
    const ipv6Hostname = this.hostname[0] === "[" && this.hostname[this.hostname.length - 1] === "]";
    if (!ipv6Hostname) {
      const hostparts = this.hostname.split(/\./);
      for (let i2 = 0, l2 = hostparts.length; i2 < l2; i2++) {
        const part = hostparts[i2];
        if (!part) {
          continue;
        }
        if (!part.match(hostnamePartPattern)) {
          let newpart = "";
          for (let j = 0, k2 = part.length; j < k2; j++) {
            if (part.charCodeAt(j) > 127) {
              newpart += "x";
            } else {
              newpart += part[j];
            }
          }
          if (!newpart.match(hostnamePartPattern)) {
            const validParts = hostparts.slice(0, i2);
            const notHost = hostparts.slice(i2 + 1);
            const bit = part.match(hostnamePartStart);
            if (bit) {
              validParts.push(bit[1]);
              notHost.unshift(bit[2]);
            }
            if (notHost.length) {
              rest = notHost.join(".") + rest;
            }
            this.hostname = validParts.join(".");
            break;
          }
        }
      }
    }
    if (this.hostname.length > hostnameMaxLen) {
      this.hostname = "";
    }
    if (ipv6Hostname) {
      this.hostname = this.hostname.substr(1, this.hostname.length - 2);
    }
  }
  const hash = rest.indexOf("#");
  if (hash !== -1) {
    this.hash = rest.substr(hash);
    rest = rest.slice(0, hash);
  }
  const qm = rest.indexOf("?");
  if (qm !== -1) {
    this.search = rest.substr(qm);
    rest = rest.slice(0, qm);
  }
  if (rest) {
    this.pathname = rest;
  }
  if (slashedProtocol[lowerProto] && this.hostname && !this.pathname) {
    this.pathname = "";
  }
  return this;
};
Url.prototype.parseHost = function(host) {
  let port = portPattern.exec(host);
  if (port) {
    port = port[0];
    if (port !== ":") {
      this.port = port.substr(1);
    }
    host = host.substr(0, host.length - port.length);
  }
  if (host) {
    this.hostname = host;
  }
};
const mdurl = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  decode: decode$1,
  encode: encode$1,
  format: format$1,
  parse: urlParse
}, Symbol.toStringTag, { value: "Module" }));
const Any = /[\0-\uD7FF\uE000-\uFFFF]|[\uD800-\uDBFF][\uDC00-\uDFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF]/;
const Cc = /[\0-\x1F\x7F-\x9F]/;
const regex$1 = /[\xAD\u0600-\u0605\u061C\u06DD\u070F\u0890\u0891\u08E2\u180E\u200B-\u200F\u202A-\u202E\u2060-\u2064\u2066-\u206F\uFEFF\uFFF9-\uFFFB]|\uD804[\uDCBD\uDCCD]|\uD80D[\uDC30-\uDC3F]|\uD82F[\uDCA0-\uDCA3]|\uD834[\uDD73-\uDD7A]|\uDB40[\uDC01\uDC20-\uDC7F]/;
const P = /[!-#%-\*,-\/:;\?@\[-\]_\{\}\xA1\xA7\xAB\xB6\xB7\xBB\xBF\u037E\u0387\u055A-\u055F\u0589\u058A\u05BE\u05C0\u05C3\u05C6\u05F3\u05F4\u0609\u060A\u060C\u060D\u061B\u061D-\u061F\u066A-\u066D\u06D4\u0700-\u070D\u07F7-\u07F9\u0830-\u083E\u085E\u0964\u0965\u0970\u09FD\u0A76\u0AF0\u0C77\u0C84\u0DF4\u0E4F\u0E5A\u0E5B\u0F04-\u0F12\u0F14\u0F3A-\u0F3D\u0F85\u0FD0-\u0FD4\u0FD9\u0FDA\u104A-\u104F\u10FB\u1360-\u1368\u1400\u166E\u169B\u169C\u16EB-\u16ED\u1735\u1736\u17D4-\u17D6\u17D8-\u17DA\u1800-\u180A\u1944\u1945\u1A1E\u1A1F\u1AA0-\u1AA6\u1AA8-\u1AAD\u1B5A-\u1B60\u1B7D\u1B7E\u1BFC-\u1BFF\u1C3B-\u1C3F\u1C7E\u1C7F\u1CC0-\u1CC7\u1CD3\u2010-\u2027\u2030-\u2043\u2045-\u2051\u2053-\u205E\u207D\u207E\u208D\u208E\u2308-\u230B\u2329\u232A\u2768-\u2775\u27C5\u27C6\u27E6-\u27EF\u2983-\u2998\u29D8-\u29DB\u29FC\u29FD\u2CF9-\u2CFC\u2CFE\u2CFF\u2D70\u2E00-\u2E2E\u2E30-\u2E4F\u2E52-\u2E5D\u3001-\u3003\u3008-\u3011\u3014-\u301F\u3030\u303D\u30A0\u30FB\uA4FE\uA4FF\uA60D-\uA60F\uA673\uA67E\uA6F2-\uA6F7\uA874-\uA877\uA8CE\uA8CF\uA8F8-\uA8FA\uA8FC\uA92E\uA92F\uA95F\uA9C1-\uA9CD\uA9DE\uA9DF\uAA5C-\uAA5F\uAADE\uAADF\uAAF0\uAAF1\uABEB\uFD3E\uFD3F\uFE10-\uFE19\uFE30-\uFE52\uFE54-\uFE61\uFE63\uFE68\uFE6A\uFE6B\uFF01-\uFF03\uFF05-\uFF0A\uFF0C-\uFF0F\uFF1A\uFF1B\uFF1F\uFF20\uFF3B-\uFF3D\uFF3F\uFF5B\uFF5D\uFF5F-\uFF65]|\uD800[\uDD00-\uDD02\uDF9F\uDFD0]|\uD801\uDD6F|\uD802[\uDC57\uDD1F\uDD3F\uDE50-\uDE58\uDE7F\uDEF0-\uDEF6\uDF39-\uDF3F\uDF99-\uDF9C]|\uD803[\uDEAD\uDF55-\uDF59\uDF86-\uDF89]|\uD804[\uDC47-\uDC4D\uDCBB\uDCBC\uDCBE-\uDCC1\uDD40-\uDD43\uDD74\uDD75\uDDC5-\uDDC8\uDDCD\uDDDB\uDDDD-\uDDDF\uDE38-\uDE3D\uDEA9]|\uD805[\uDC4B-\uDC4F\uDC5A\uDC5B\uDC5D\uDCC6\uDDC1-\uDDD7\uDE41-\uDE43\uDE60-\uDE6C\uDEB9\uDF3C-\uDF3E]|\uD806[\uDC3B\uDD44-\uDD46\uDDE2\uDE3F-\uDE46\uDE9A-\uDE9C\uDE9E-\uDEA2\uDF00-\uDF09]|\uD807[\uDC41-\uDC45\uDC70\uDC71\uDEF7\uDEF8\uDF43-\uDF4F\uDFFF]|\uD809[\uDC70-\uDC74]|\uD80B[\uDFF1\uDFF2]|\uD81A[\uDE6E\uDE6F\uDEF5\uDF37-\uDF3B\uDF44]|\uD81B[\uDE97-\uDE9A\uDFE2]|\uD82F\uDC9F|\uD836[\uDE87-\uDE8B]|\uD83A[\uDD5E\uDD5F]/;
const regex = /[\$\+<->\^`\|~\xA2-\xA6\xA8\xA9\xAC\xAE-\xB1\xB4\xB8\xD7\xF7\u02C2-\u02C5\u02D2-\u02DF\u02E5-\u02EB\u02ED\u02EF-\u02FF\u0375\u0384\u0385\u03F6\u0482\u058D-\u058F\u0606-\u0608\u060B\u060E\u060F\u06DE\u06E9\u06FD\u06FE\u07F6\u07FE\u07FF\u0888\u09F2\u09F3\u09FA\u09FB\u0AF1\u0B70\u0BF3-\u0BFA\u0C7F\u0D4F\u0D79\u0E3F\u0F01-\u0F03\u0F13\u0F15-\u0F17\u0F1A-\u0F1F\u0F34\u0F36\u0F38\u0FBE-\u0FC5\u0FC7-\u0FCC\u0FCE\u0FCF\u0FD5-\u0FD8\u109E\u109F\u1390-\u1399\u166D\u17DB\u1940\u19DE-\u19FF\u1B61-\u1B6A\u1B74-\u1B7C\u1FBD\u1FBF-\u1FC1\u1FCD-\u1FCF\u1FDD-\u1FDF\u1FED-\u1FEF\u1FFD\u1FFE\u2044\u2052\u207A-\u207C\u208A-\u208C\u20A0-\u20C0\u2100\u2101\u2103-\u2106\u2108\u2109\u2114\u2116-\u2118\u211E-\u2123\u2125\u2127\u2129\u212E\u213A\u213B\u2140-\u2144\u214A-\u214D\u214F\u218A\u218B\u2190-\u2307\u230C-\u2328\u232B-\u2426\u2440-\u244A\u249C-\u24E9\u2500-\u2767\u2794-\u27C4\u27C7-\u27E5\u27F0-\u2982\u2999-\u29D7\u29DC-\u29FB\u29FE-\u2B73\u2B76-\u2B95\u2B97-\u2BFF\u2CE5-\u2CEA\u2E50\u2E51\u2E80-\u2E99\u2E9B-\u2EF3\u2F00-\u2FD5\u2FF0-\u2FFF\u3004\u3012\u3013\u3020\u3036\u3037\u303E\u303F\u309B\u309C\u3190\u3191\u3196-\u319F\u31C0-\u31E3\u31EF\u3200-\u321E\u322A-\u3247\u3250\u3260-\u327F\u328A-\u32B0\u32C0-\u33FF\u4DC0-\u4DFF\uA490-\uA4C6\uA700-\uA716\uA720\uA721\uA789\uA78A\uA828-\uA82B\uA836-\uA839\uAA77-\uAA79\uAB5B\uAB6A\uAB6B\uFB29\uFBB2-\uFBC2\uFD40-\uFD4F\uFDCF\uFDFC-\uFDFF\uFE62\uFE64-\uFE66\uFE69\uFF04\uFF0B\uFF1C-\uFF1E\uFF3E\uFF40\uFF5C\uFF5E\uFFE0-\uFFE6\uFFE8-\uFFEE\uFFFC\uFFFD]|\uD800[\uDD37-\uDD3F\uDD79-\uDD89\uDD8C-\uDD8E\uDD90-\uDD9C\uDDA0\uDDD0-\uDDFC]|\uD802[\uDC77\uDC78\uDEC8]|\uD805\uDF3F|\uD807[\uDFD5-\uDFF1]|\uD81A[\uDF3C-\uDF3F\uDF45]|\uD82F\uDC9C|\uD833[\uDF50-\uDFC3]|\uD834[\uDC00-\uDCF5\uDD00-\uDD26\uDD29-\uDD64\uDD6A-\uDD6C\uDD83\uDD84\uDD8C-\uDDA9\uDDAE-\uDDEA\uDE00-\uDE41\uDE45\uDF00-\uDF56]|\uD835[\uDEC1\uDEDB\uDEFB\uDF15\uDF35\uDF4F\uDF6F\uDF89\uDFA9\uDFC3]|\uD836[\uDC00-\uDDFF\uDE37-\uDE3A\uDE6D-\uDE74\uDE76-\uDE83\uDE85\uDE86]|\uD838[\uDD4F\uDEFF]|\uD83B[\uDCAC\uDCB0\uDD2E\uDEF0\uDEF1]|\uD83C[\uDC00-\uDC2B\uDC30-\uDC93\uDCA0-\uDCAE\uDCB1-\uDCBF\uDCC1-\uDCCF\uDCD1-\uDCF5\uDD0D-\uDDAD\uDDE6-\uDE02\uDE10-\uDE3B\uDE40-\uDE48\uDE50\uDE51\uDE60-\uDE65\uDF00-\uDFFF]|\uD83D[\uDC00-\uDED7\uDEDC-\uDEEC\uDEF0-\uDEFC\uDF00-\uDF76\uDF7B-\uDFD9\uDFE0-\uDFEB\uDFF0]|\uD83E[\uDC00-\uDC0B\uDC10-\uDC47\uDC50-\uDC59\uDC60-\uDC87\uDC90-\uDCAD\uDCB0\uDCB1\uDD00-\uDE53\uDE60-\uDE6D\uDE70-\uDE7C\uDE80-\uDE88\uDE90-\uDEBD\uDEBF-\uDEC5\uDECE-\uDEDB\uDEE0-\uDEE8\uDEF0-\uDEF8\uDF00-\uDF92\uDF94-\uDFCA]/;
const Z = /[ \xA0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000]/;
const ucmicro = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  Any,
  Cc,
  Cf: regex$1,
  P,
  S: regex,
  Z
}, Symbol.toStringTag, { value: "Module" }));
const htmlDecodeTree = new Uint16Array(
  // prettier-ignore
  'ᵁ<Õıʊҝջאٵ۞ޢߖࠏ੊ઑඡ๭༉༦჊ረዡᐕᒝᓃᓟᔥ\0\0\0\0\0\0ᕫᛍᦍᰒᷝ὾⁠↰⊍⏀⏻⑂⠤⤒ⴈ⹈⿎〖㊺㘹㞬㣾㨨㩱㫠㬮ࠀEMabcfglmnoprstu\\bfms¦³¹ÈÏlig耻Æ䃆P耻&䀦cute耻Á䃁reve;䄂Āiyx}rc耻Â䃂;䐐r;쀀𝔄rave耻À䃀pha;䎑acr;䄀d;橓Āgp¡on;䄄f;쀀𝔸plyFunction;恡ing耻Å䃅Ācs¾Ãr;쀀𝒜ign;扔ilde耻Ã䃃ml耻Ä䃄ЀaceforsuåûþėĜĢħĪĀcrêòkslash;或Ŷöø;櫧ed;挆y;䐑ƀcrtąċĔause;戵noullis;愬a;䎒r;쀀𝔅pf;쀀𝔹eve;䋘còēmpeq;扎܀HOacdefhilorsuōőŖƀƞƢƵƷƺǜȕɳɸɾcy;䐧PY耻©䂩ƀcpyŝŢźute;䄆Ā;iŧŨ拒talDifferentialD;慅leys;愭ȀaeioƉƎƔƘron;䄌dil耻Ç䃇rc;䄈nint;戰ot;䄊ĀdnƧƭilla;䂸terDot;䂷òſi;䎧rcleȀDMPTǇǋǑǖot;抙inus;抖lus;投imes;抗oĀcsǢǸkwiseContourIntegral;戲eCurlyĀDQȃȏoubleQuote;思uote;怙ȀlnpuȞȨɇɕonĀ;eȥȦ户;橴ƀgitȯȶȺruent;扡nt;戯ourIntegral;戮ĀfrɌɎ;愂oduct;成nterClockwiseContourIntegral;戳oss;樯cr;쀀𝒞pĀ;Cʄʅ拓ap;才րDJSZacefiosʠʬʰʴʸˋ˗ˡ˦̳ҍĀ;oŹʥtrahd;椑cy;䐂cy;䐅cy;䐏ƀgrsʿ˄ˇger;怡r;憡hv;櫤Āayː˕ron;䄎;䐔lĀ;t˝˞戇a;䎔r;쀀𝔇Āaf˫̧Ācm˰̢riticalȀADGT̖̜̀̆cute;䂴oŴ̋̍;䋙bleAcute;䋝rave;䁠ilde;䋜ond;拄ferentialD;慆Ѱ̽\0\0\0͔͂\0Ѕf;쀀𝔻ƀ;DE͈͉͍䂨ot;惜qual;扐blèCDLRUVͣͲ΂ϏϢϸontourIntegraìȹoɴ͹\0\0ͻ»͉nArrow;懓Āeo·ΤftƀARTΐΖΡrrow;懐ightArrow;懔eåˊngĀLRΫτeftĀARγιrrow;柸ightArrow;柺ightArrow;柹ightĀATϘϞrrow;懒ee;抨pɁϩ\0\0ϯrrow;懑ownArrow;懕erticalBar;戥ǹABLRTaВЪаўѿͼrrowƀ;BUНОТ憓ar;椓pArrow;懵reve;䌑eft˒к\0ц\0ѐightVector;楐eeVector;楞ectorĀ;Bљњ憽ar;楖ightǔѧ\0ѱeeVector;楟ectorĀ;BѺѻ懁ar;楗eeĀ;A҆҇护rrow;憧ĀctҒҗr;쀀𝒟rok;䄐ࠀNTacdfglmopqstuxҽӀӄӋӞӢӧӮӵԡԯԶՒ՝ՠեG;䅊H耻Ð䃐cute耻É䃉ƀaiyӒӗӜron;䄚rc耻Ê䃊;䐭ot;䄖r;쀀𝔈rave耻È䃈ement;戈ĀapӺӾcr;䄒tyɓԆ\0\0ԒmallSquare;旻erySmallSquare;斫ĀgpԦԪon;䄘f;쀀𝔼silon;䎕uĀaiԼՉlĀ;TՂՃ橵ilde;扂librium;懌Āci՗՚r;愰m;橳a;䎗ml耻Ë䃋Āipժկsts;戃onentialE;慇ʀcfiosօֈ֍ֲ׌y;䐤r;쀀𝔉lledɓ֗\0\0֣mallSquare;旼erySmallSquare;斪Ͱֺ\0ֿ\0\0ׄf;쀀𝔽All;戀riertrf;愱cò׋؀JTabcdfgorstר׬ׯ׺؀ؒؖ؛؝أ٬ٲcy;䐃耻>䀾mmaĀ;d׷׸䎓;䏜reve;䄞ƀeiy؇،ؐdil;䄢rc;䄜;䐓ot;䄠r;쀀𝔊;拙pf;쀀𝔾eater̀EFGLSTصلَٖٛ٦qualĀ;Lؾؿ扥ess;招ullEqual;执reater;檢ess;扷lantEqual;橾ilde;扳cr;쀀𝒢;扫ЀAacfiosuڅڋږڛڞڪھۊRDcy;䐪Āctڐڔek;䋇;䁞irc;䄤r;愌lbertSpace;愋ǰگ\0ڲf;愍izontalLine;攀Āctۃۅòکrok;䄦mpńېۘownHumðįqual;扏܀EJOacdfgmnostuۺ۾܃܇܎ܚܞܡܨ݄ݸދޏޕcy;䐕lig;䄲cy;䐁cute耻Í䃍Āiyܓܘrc耻Î䃎;䐘ot;䄰r;愑rave耻Ì䃌ƀ;apܠܯܿĀcgܴܷr;䄪inaryI;慈lieóϝǴ݉\0ݢĀ;eݍݎ戬Āgrݓݘral;戫section;拂isibleĀCTݬݲomma;恣imes;恢ƀgptݿރވon;䄮f;쀀𝕀a;䎙cr;愐ilde;䄨ǫޚ\0ޞcy;䐆l耻Ï䃏ʀcfosuެ޷޼߂ߐĀiyޱ޵rc;䄴;䐙r;쀀𝔍pf;쀀𝕁ǣ߇\0ߌr;쀀𝒥rcy;䐈kcy;䐄΀HJacfosߤߨ߽߬߱ࠂࠈcy;䐥cy;䐌ppa;䎚Āey߶߻dil;䄶;䐚r;쀀𝔎pf;쀀𝕂cr;쀀𝒦րJTaceflmostࠥࠩࠬࡐࡣ঳সে্਷ੇcy;䐉耻<䀼ʀcmnpr࠷࠼ࡁࡄࡍute;䄹bda;䎛g;柪lacetrf;愒r;憞ƀaeyࡗ࡜ࡡron;䄽dil;䄻;䐛Āfsࡨ॰tԀACDFRTUVarࡾࢩࢱࣦ࣠ࣼयज़ΐ४Ānrࢃ࢏gleBracket;柨rowƀ;BR࢙࢚࢞憐ar;懤ightArrow;懆eiling;挈oǵࢷ\0ࣃbleBracket;柦nǔࣈ\0࣒eeVector;楡ectorĀ;Bࣛࣜ懃ar;楙loor;挊ightĀAV࣯ࣵrrow;憔ector;楎Āerँगeƀ;AVउऊऐ抣rrow;憤ector;楚iangleƀ;BEतथऩ抲ar;槏qual;抴pƀDTVषूौownVector;楑eeVector;楠ectorĀ;Bॖॗ憿ar;楘ectorĀ;B॥०憼ar;楒ightáΜs̀EFGLSTॾঋকঝঢভqualGreater;拚ullEqual;扦reater;扶ess;檡lantEqual;橽ilde;扲r;쀀𝔏Ā;eঽা拘ftarrow;懚idot;䄿ƀnpw৔ਖਛgȀLRlr৞৷ਂਐeftĀAR০৬rrow;柵ightArrow;柷ightArrow;柶eftĀarγਊightáοightáϊf;쀀𝕃erĀLRਢਬeftArrow;憙ightArrow;憘ƀchtਾੀੂòࡌ;憰rok;䅁;扪Ѐacefiosuਗ਼੝੠੷੼અઋ઎p;椅y;䐜Ādl੥੯iumSpace;恟lintrf;愳r;쀀𝔐nusPlus;戓pf;쀀𝕄cò੶;䎜ҀJacefostuણધભીଔଙඑ඗ඞcy;䐊cute;䅃ƀaey઴હાron;䅇dil;䅅;䐝ƀgswે૰଎ativeƀMTV૓૟૨ediumSpace;怋hiĀcn૦૘ë૙eryThiî૙tedĀGL૸ଆreaterGreateòٳessLesóੈLine;䀊r;쀀𝔑ȀBnptଢନଷ଺reak;恠BreakingSpace;䂠f;愕ڀ;CDEGHLNPRSTV୕ୖ୪୼஡௫ఄ౞಄ದ೘ൡඅ櫬Āou୛୤ngruent;扢pCap;扭oubleVerticalBar;戦ƀlqxஃஊ஛ement;戉ualĀ;Tஒஓ扠ilde;쀀≂̸ists;戄reater΀;EFGLSTஶஷ஽௉௓௘௥扯qual;扱ullEqual;쀀≧̸reater;쀀≫̸ess;批lantEqual;쀀⩾̸ilde;扵umpń௲௽ownHump;쀀≎̸qual;쀀≏̸eĀfsఊధtTriangleƀ;BEచఛడ拪ar;쀀⧏̸qual;括s̀;EGLSTవశ఼ౄోౘ扮qual;扰reater;扸ess;쀀≪̸lantEqual;쀀⩽̸ilde;扴estedĀGL౨౹reaterGreater;쀀⪢̸essLess;쀀⪡̸recedesƀ;ESಒಓಛ技qual;쀀⪯̸lantEqual;拠ĀeiಫಹverseElement;戌ghtTriangleƀ;BEೋೌ೒拫ar;쀀⧐̸qual;拭ĀquೝഌuareSuĀbp೨೹setĀ;E೰ೳ쀀⊏̸qual;拢ersetĀ;Eഃആ쀀⊐̸qual;拣ƀbcpഓതൎsetĀ;Eഛഞ쀀⊂⃒qual;抈ceedsȀ;ESTലള഻െ抁qual;쀀⪰̸lantEqual;拡ilde;쀀≿̸ersetĀ;E൘൛쀀⊃⃒qual;抉ildeȀ;EFT൮൯൵ൿ扁qual;扄ullEqual;扇ilde;扉erticalBar;戤cr;쀀𝒩ilde耻Ñ䃑;䎝܀Eacdfgmoprstuvලෂ෉෕ෛ෠෧෼ขภยา฿ไlig;䅒cute耻Ó䃓Āiy෎ීrc耻Ô䃔;䐞blac;䅐r;쀀𝔒rave耻Ò䃒ƀaei෮ෲ෶cr;䅌ga;䎩cron;䎟pf;쀀𝕆enCurlyĀDQฎบoubleQuote;怜uote;怘;橔Āclวฬr;쀀𝒪ash耻Ø䃘iŬื฼de耻Õ䃕es;樷ml耻Ö䃖erĀBP๋๠Āar๐๓r;怾acĀek๚๜;揞et;掴arenthesis;揜Ҁacfhilors๿ງຊຏຒດຝະ໼rtialD;戂y;䐟r;쀀𝔓i;䎦;䎠usMinus;䂱Āipຢອncareplanåڝf;愙Ȁ;eio຺ູ໠໤檻cedesȀ;EST່້໏໚扺qual;檯lantEqual;扼ilde;找me;怳Ādp໩໮uct;戏ortionĀ;aȥ໹l;戝Āci༁༆r;쀀𝒫;䎨ȀUfos༑༖༛༟OT耻"䀢r;쀀𝔔pf;愚cr;쀀𝒬؀BEacefhiorsu༾གྷཇའཱིྦྷྪྭ႖ႩႴႾarr;椐G耻®䂮ƀcnrཎནབute;䅔g;柫rĀ;tཛྷཝ憠l;椖ƀaeyཧཬཱron;䅘dil;䅖;䐠Ā;vླྀཹ愜erseĀEUྂྙĀlq྇ྎement;戋uilibrium;懋pEquilibrium;楯r»ཹo;䎡ghtЀACDFTUVa࿁࿫࿳ဢဨၛႇϘĀnr࿆࿒gleBracket;柩rowƀ;BL࿜࿝࿡憒ar;懥eftArrow;懄eiling;按oǵ࿹\0စbleBracket;柧nǔည\0နeeVector;楝ectorĀ;Bဝသ懂ar;楕loor;挋Āerိ၃eƀ;AVဵံြ抢rrow;憦ector;楛iangleƀ;BEၐၑၕ抳ar;槐qual;抵pƀDTVၣၮၸownVector;楏eeVector;楜ectorĀ;Bႂႃ憾ar;楔ectorĀ;B႑႒懀ar;楓Āpuႛ႞f;愝ndImplies;楰ightarrow;懛ĀchႹႼr;愛;憱leDelayed;槴ڀHOacfhimoqstuფჱჷჽᄙᄞᅑᅖᅡᅧᆵᆻᆿĀCcჩხHcy;䐩y;䐨FTcy;䐬cute;䅚ʀ;aeiyᄈᄉᄎᄓᄗ檼ron;䅠dil;䅞rc;䅜;䐡r;쀀𝔖ortȀDLRUᄪᄴᄾᅉownArrow»ОeftArrow»࢚ightArrow»࿝pArrow;憑gma;䎣allCircle;战pf;쀀𝕊ɲᅭ\0\0ᅰt;戚areȀ;ISUᅻᅼᆉᆯ斡ntersection;抓uĀbpᆏᆞsetĀ;Eᆗᆘ抏qual;抑ersetĀ;Eᆨᆩ抐qual;抒nion;抔cr;쀀𝒮ar;拆ȀbcmpᇈᇛሉላĀ;sᇍᇎ拐etĀ;Eᇍᇕqual;抆ĀchᇠህeedsȀ;ESTᇭᇮᇴᇿ扻qual;檰lantEqual;扽ilde;承Tháྌ;我ƀ;esሒሓሣ拑rsetĀ;Eሜም抃qual;抇et»ሓրHRSacfhiorsሾቄ቉ቕ቞ቱቶኟዂወዑORN耻Þ䃞ADE;愢ĀHc቎ቒcy;䐋y;䐦Ābuቚቜ;䀉;䎤ƀaeyብቪቯron;䅤dil;䅢;䐢r;쀀𝔗Āeiቻ኉ǲኀ\0ኇefore;戴a;䎘Ācn኎ኘkSpace;쀀  Space;怉ldeȀ;EFTካኬኲኼ戼qual;扃ullEqual;扅ilde;扈pf;쀀𝕋ipleDot;惛Āctዖዛr;쀀𝒯rok;䅦ૡዷጎጚጦ\0ጬጱ\0\0\0\0\0ጸጽ፷ᎅ\0᏿ᐄᐊᐐĀcrዻጁute耻Ú䃚rĀ;oጇገ憟cir;楉rǣጓ\0጖y;䐎ve;䅬Āiyጞጣrc耻Û䃛;䐣blac;䅰r;쀀𝔘rave耻Ù䃙acr;䅪Ādiፁ፩erĀBPፈ፝Āarፍፐr;䁟acĀekፗፙ;揟et;掵arenthesis;揝onĀ;P፰፱拃lus;抎Āgp፻፿on;䅲f;쀀𝕌ЀADETadps᎕ᎮᎸᏄϨᏒᏗᏳrrowƀ;BDᅐᎠᎤar;椒ownArrow;懅ownArrow;憕quilibrium;楮eeĀ;AᏋᏌ报rrow;憥ownáϳerĀLRᏞᏨeftArrow;憖ightArrow;憗iĀ;lᏹᏺ䏒on;䎥ing;䅮cr;쀀𝒰ilde;䅨ml耻Ü䃜ҀDbcdefosvᐧᐬᐰᐳᐾᒅᒊᒐᒖash;披ar;櫫y;䐒ashĀ;lᐻᐼ抩;櫦Āerᑃᑅ;拁ƀbtyᑌᑐᑺar;怖Ā;iᑏᑕcalȀBLSTᑡᑥᑪᑴar;戣ine;䁼eparator;杘ilde;所ThinSpace;怊r;쀀𝔙pf;쀀𝕍cr;쀀𝒱dash;抪ʀcefosᒧᒬᒱᒶᒼirc;䅴dge;拀r;쀀𝔚pf;쀀𝕎cr;쀀𝒲Ȁfiosᓋᓐᓒᓘr;쀀𝔛;䎞pf;쀀𝕏cr;쀀𝒳ҀAIUacfosuᓱᓵᓹᓽᔄᔏᔔᔚᔠcy;䐯cy;䐇cy;䐮cute耻Ý䃝Āiyᔉᔍrc;䅶;䐫r;쀀𝔜pf;쀀𝕐cr;쀀𝒴ml;䅸ЀHacdefosᔵᔹᔿᕋᕏᕝᕠᕤcy;䐖cute;䅹Āayᕄᕉron;䅽;䐗ot;䅻ǲᕔ\0ᕛoWidtè૙a;䎖r;愨pf;愤cr;쀀𝒵௡ᖃᖊᖐ\0ᖰᖶᖿ\0\0\0\0ᗆᗛᗫᙟ᙭\0ᚕ᚛ᚲᚹ\0ᚾcute耻á䃡reve;䄃̀;Ediuyᖜᖝᖡᖣᖨᖭ戾;쀀∾̳;房rc耻â䃢te肻´̆;䐰lig耻æ䃦Ā;r²ᖺ;쀀𝔞rave耻à䃠ĀepᗊᗖĀfpᗏᗔsym;愵èᗓha;䎱ĀapᗟcĀclᗤᗧr;䄁g;樿ɤᗰ\0\0ᘊʀ;adsvᗺᗻᗿᘁᘇ戧nd;橕;橜lope;橘;橚΀;elmrszᘘᘙᘛᘞᘿᙏᙙ戠;榤e»ᘙsdĀ;aᘥᘦ戡ѡᘰᘲᘴᘶᘸᘺᘼᘾ;榨;榩;榪;榫;榬;榭;榮;榯tĀ;vᙅᙆ戟bĀ;dᙌᙍ抾;榝Āptᙔᙗh;戢»¹arr;捼Āgpᙣᙧon;䄅f;쀀𝕒΀;Eaeiop዁ᙻᙽᚂᚄᚇᚊ;橰cir;橯;扊d;手s;䀧roxĀ;e዁ᚒñᚃing耻å䃥ƀctyᚡᚦᚨr;쀀𝒶;䀪mpĀ;e዁ᚯñʈilde耻ã䃣ml耻ä䃤Āciᛂᛈoninôɲnt;樑ࠀNabcdefiklnoprsu᛭ᛱᜰ᜼ᝃᝈ᝸᝽០៦ᠹᡐᜍ᤽᥈ᥰot;櫭Ācrᛶ᜞kȀcepsᜀᜅᜍᜓong;扌psilon;䏶rime;怵imĀ;e᜚᜛戽q;拍Ŷᜢᜦee;抽edĀ;gᜬᜭ挅e»ᜭrkĀ;t፜᜷brk;掶Āoyᜁᝁ;䐱quo;怞ʀcmprtᝓ᝛ᝡᝤᝨausĀ;eĊĉptyv;榰séᜌnoõēƀahwᝯ᝱ᝳ;䎲;愶een;扬r;쀀𝔟g΀costuvwឍឝឳេ៕៛៞ƀaiuបពរðݠrc;旯p»፱ƀdptឤឨឭot;樀lus;樁imes;樂ɱឹ\0\0ើcup;樆ar;昅riangleĀdu៍្own;施p;斳plus;樄eåᑄåᒭarow;植ƀako៭ᠦᠵĀcn៲ᠣkƀlst៺֫᠂ozenge;槫riangleȀ;dlr᠒᠓᠘᠝斴own;斾eft;旂ight;斸k;搣Ʊᠫ\0ᠳƲᠯ\0ᠱ;斒;斑4;斓ck;斈ĀeoᠾᡍĀ;qᡃᡆ쀀=⃥uiv;쀀≡⃥t;挐Ȁptwxᡙᡞᡧᡬf;쀀𝕓Ā;tᏋᡣom»Ꮜtie;拈؀DHUVbdhmptuvᢅᢖᢪᢻᣗᣛᣬ᣿ᤅᤊᤐᤡȀLRlrᢎᢐᢒᢔ;敗;敔;敖;敓ʀ;DUduᢡᢢᢤᢦᢨ敐;敦;敩;敤;敧ȀLRlrᢳᢵᢷᢹ;敝;敚;敜;教΀;HLRhlrᣊᣋᣍᣏᣑᣓᣕ救;敬;散;敠;敫;敢;敟ox;槉ȀLRlrᣤᣦᣨᣪ;敕;敒;攐;攌ʀ;DUduڽ᣷᣹᣻᣽;敥;敨;攬;攴inus;抟lus;択imes;抠ȀLRlrᤙᤛᤝ᤟;敛;敘;攘;攔΀;HLRhlrᤰᤱᤳᤵᤷ᤻᤹攂;敪;敡;敞;攼;攤;攜Āevģ᥂bar耻¦䂦Ȁceioᥑᥖᥚᥠr;쀀𝒷mi;恏mĀ;e᜚᜜lƀ;bhᥨᥩᥫ䁜;槅sub;柈Ŭᥴ᥾lĀ;e᥹᥺怢t»᥺pƀ;Eeįᦅᦇ;檮Ā;qۜۛೡᦧ\0᧨ᨑᨕᨲ\0ᨷᩐ\0\0᪴\0\0᫁\0\0ᬡᬮ᭍᭒\0᯽\0ᰌƀcpr᦭ᦲ᧝ute;䄇̀;abcdsᦿᧀᧄ᧊᧕᧙戩nd;橄rcup;橉Āau᧏᧒p;橋p;橇ot;橀;쀀∩︀Āeo᧢᧥t;恁îړȀaeiu᧰᧻ᨁᨅǰ᧵\0᧸s;橍on;䄍dil耻ç䃧rc;䄉psĀ;sᨌᨍ橌m;橐ot;䄋ƀdmnᨛᨠᨦil肻¸ƭptyv;榲t脀¢;eᨭᨮ䂢räƲr;쀀𝔠ƀceiᨽᩀᩍy;䑇ckĀ;mᩇᩈ朓ark»ᩈ;䏇r΀;Ecefms᩟᩠ᩢᩫ᪤᪪᪮旋;槃ƀ;elᩩᩪᩭ䋆q;扗eɡᩴ\0\0᪈rrowĀlr᩼᪁eft;憺ight;憻ʀRSacd᪒᪔᪖᪚᪟»ཇ;擈st;抛irc;抚ash;抝nint;樐id;櫯cir;槂ubsĀ;u᪻᪼晣it»᪼ˬ᫇᫔᫺\0ᬊonĀ;eᫍᫎ䀺Ā;qÇÆɭ᫙\0\0᫢aĀ;t᫞᫟䀬;䁀ƀ;fl᫨᫩᫫戁îᅠeĀmx᫱᫶ent»᫩eóɍǧ᫾\0ᬇĀ;dኻᬂot;橭nôɆƀfryᬐᬔᬗ;쀀𝕔oäɔ脀©;sŕᬝr;愗Āaoᬥᬩrr;憵ss;朗Ācuᬲᬷr;쀀𝒸Ābpᬼ᭄Ā;eᭁᭂ櫏;櫑Ā;eᭉᭊ櫐;櫒dot;拯΀delprvw᭠᭬᭷ᮂᮬᯔ᯹arrĀlr᭨᭪;椸;椵ɰ᭲\0\0᭵r;拞c;拟arrĀ;p᭿ᮀ憶;椽̀;bcdosᮏᮐᮖᮡᮥᮨ截rcap;橈Āauᮛᮞp;橆p;橊ot;抍r;橅;쀀∪︀Ȁalrv᮵ᮿᯞᯣrrĀ;mᮼᮽ憷;椼yƀevwᯇᯔᯘqɰᯎ\0\0ᯒreã᭳uã᭵ee;拎edge;拏en耻¤䂤earrowĀlrᯮ᯳eft»ᮀight»ᮽeäᯝĀciᰁᰇoninôǷnt;戱lcty;挭ঀAHabcdefhijlorstuwz᰸᰻᰿ᱝᱩᱵᲊᲞᲬᲷ᳻᳿ᴍᵻᶑᶫᶻ᷆᷍rò΁ar;楥Ȁglrs᱈ᱍ᱒᱔ger;怠eth;愸òᄳhĀ;vᱚᱛ怐»ऊūᱡᱧarow;椏aã̕Āayᱮᱳron;䄏;䐴ƀ;ao̲ᱼᲄĀgrʿᲁr;懊tseq;橷ƀglmᲑᲔᲘ耻°䂰ta;䎴ptyv;榱ĀirᲣᲨsht;楿;쀀𝔡arĀlrᲳᲵ»ࣜ»သʀaegsv᳂͸᳖᳜᳠mƀ;oș᳊᳔ndĀ;ș᳑uit;晦amma;䏝in;拲ƀ;io᳧᳨᳸䃷de脀÷;o᳧ᳰntimes;拇nø᳷cy;䑒cɯᴆ\0\0ᴊrn;挞op;挍ʀlptuwᴘᴝᴢᵉᵕlar;䀤f;쀀𝕕ʀ;emps̋ᴭᴷᴽᵂqĀ;d͒ᴳot;扑inus;戸lus;戔quare;抡blebarwedgåúnƀadhᄮᵝᵧownarrowóᲃarpoonĀlrᵲᵶefôᲴighôᲶŢᵿᶅkaro÷གɯᶊ\0\0ᶎrn;挟op;挌ƀcotᶘᶣᶦĀryᶝᶡ;쀀𝒹;䑕l;槶rok;䄑Ādrᶰᶴot;拱iĀ;fᶺ᠖斿Āah᷀᷃ròЩaòྦangle;榦Āci᷒ᷕy;䑟grarr;柿ऀDacdefglmnopqrstuxḁḉḙḸոḼṉṡṾấắẽỡἪἷὄ὎὚ĀDoḆᴴoôᲉĀcsḎḔute耻é䃩ter;橮ȀaioyḢḧḱḶron;䄛rĀ;cḭḮ扖耻ê䃪lon;払;䑍ot;䄗ĀDrṁṅot;扒;쀀𝔢ƀ;rsṐṑṗ檚ave耻è䃨Ā;dṜṝ檖ot;檘Ȁ;ilsṪṫṲṴ檙nters;揧;愓Ā;dṹṺ檕ot;檗ƀapsẅẉẗcr;䄓tyƀ;svẒẓẕ戅et»ẓpĀ1;ẝẤĳạả;怄;怅怃ĀgsẪẬ;䅋p;怂ĀgpẴẸon;䄙f;쀀𝕖ƀalsỄỎỒrĀ;sỊị拕l;槣us;橱iƀ;lvỚớở䎵on»ớ;䏵ȀcsuvỪỳἋἣĀioữḱrc»Ḯɩỹ\0\0ỻíՈantĀglἂἆtr»ṝess»Ṻƀaeiἒ἖Ἒls;䀽st;扟vĀ;DȵἠD;橸parsl;槥ĀDaἯἳot;打rr;楱ƀcdiἾὁỸr;愯oô͒ĀahὉὋ;䎷耻ð䃰Āmrὓὗl耻ë䃫o;悬ƀcipὡὤὧl;䀡sôծĀeoὬὴctatioîՙnentialåչৡᾒ\0ᾞ\0ᾡᾧ\0\0ῆῌ\0ΐ\0ῦῪ \0 ⁚llingdotseñṄy;䑄male;晀ƀilrᾭᾳ῁lig;耀ﬃɩᾹ\0\0᾽g;耀ﬀig;耀ﬄ;쀀𝔣lig;耀ﬁlig;쀀fjƀaltῙ῜ῡt;晭ig;耀ﬂns;斱of;䆒ǰ΅\0ῳf;쀀𝕗ĀakֿῷĀ;vῼ´拔;櫙artint;樍Āao‌⁕Ācs‑⁒α‚‰‸⁅⁈\0⁐β•‥‧‪‬\0‮耻½䂽;慓耻¼䂼;慕;慙;慛Ƴ‴\0‶;慔;慖ʴ‾⁁\0\0⁃耻¾䂾;慗;慜5;慘ƶ⁌\0⁎;慚;慝8;慞l;恄wn;挢cr;쀀𝒻ࢀEabcdefgijlnorstv₂₉₟₥₰₴⃰⃵⃺⃿℃ℒℸ̗ℾ⅒↞Ā;lٍ₇;檌ƀcmpₐₕ₝ute;䇵maĀ;dₜ᳚䎳;檆reve;䄟Āiy₪₮rc;䄝;䐳ot;䄡Ȁ;lqsؾق₽⃉ƀ;qsؾٌ⃄lanô٥Ȁ;cdl٥⃒⃥⃕c;檩otĀ;o⃜⃝檀Ā;l⃢⃣檂;檄Ā;e⃪⃭쀀⋛︀s;檔r;쀀𝔤Ā;gٳ؛mel;愷cy;䑓Ȁ;Eajٚℌℎℐ;檒;檥;檤ȀEaesℛℝ℩ℴ;扩pĀ;p℣ℤ檊rox»ℤĀ;q℮ℯ檈Ā;q℮ℛim;拧pf;쀀𝕘Āci⅃ⅆr;愊mƀ;el٫ⅎ⅐;檎;檐茀>;cdlqr׮ⅠⅪⅮⅳⅹĀciⅥⅧ;檧r;橺ot;拗Par;榕uest;橼ʀadelsↄⅪ←ٖ↛ǰ↉\0↎proø₞r;楸qĀlqؿ↖lesó₈ií٫Āen↣↭rtneqq;쀀≩︀Å↪ԀAabcefkosy⇄⇇⇱⇵⇺∘∝∯≨≽ròΠȀilmr⇐⇔⇗⇛rsðᒄf»․ilôکĀdr⇠⇤cy;䑊ƀ;cwࣴ⇫⇯ir;楈;憭ar;意irc;䄥ƀalr∁∎∓rtsĀ;u∉∊晥it»∊lip;怦con;抹r;쀀𝔥sĀew∣∩arow;椥arow;椦ʀamopr∺∾≃≞≣rr;懿tht;戻kĀlr≉≓eftarrow;憩ightarrow;憪f;쀀𝕙bar;怕ƀclt≯≴≸r;쀀𝒽asè⇴rok;䄧Ābp⊂⊇ull;恃hen»ᱛૡ⊣\0⊪\0⊸⋅⋎\0⋕⋳\0\0⋸⌢⍧⍢⍿\0⎆⎪⎴cute耻í䃭ƀ;iyݱ⊰⊵rc耻î䃮;䐸Ācx⊼⊿y;䐵cl耻¡䂡ĀfrΟ⋉;쀀𝔦rave耻ì䃬Ȁ;inoܾ⋝⋩⋮Āin⋢⋦nt;樌t;戭fin;槜ta;愩lig;䄳ƀaop⋾⌚⌝ƀcgt⌅⌈⌗r;䄫ƀelpܟ⌏⌓inåގarôܠh;䄱f;抷ed;䆵ʀ;cfotӴ⌬⌱⌽⍁are;愅inĀ;t⌸⌹戞ie;槝doô⌙ʀ;celpݗ⍌⍐⍛⍡al;抺Āgr⍕⍙eróᕣã⍍arhk;樗rod;樼Ȁcgpt⍯⍲⍶⍻y;䑑on;䄯f;쀀𝕚a;䎹uest耻¿䂿Āci⎊⎏r;쀀𝒾nʀ;EdsvӴ⎛⎝⎡ӳ;拹ot;拵Ā;v⎦⎧拴;拳Ā;iݷ⎮lde;䄩ǫ⎸\0⎼cy;䑖l耻ï䃯̀cfmosu⏌⏗⏜⏡⏧⏵Āiy⏑⏕rc;䄵;䐹r;쀀𝔧ath;䈷pf;쀀𝕛ǣ⏬\0⏱r;쀀𝒿rcy;䑘kcy;䑔Ѐacfghjos␋␖␢␧␭␱␵␻ppaĀ;v␓␔䎺;䏰Āey␛␠dil;䄷;䐺r;쀀𝔨reen;䄸cy;䑅cy;䑜pf;쀀𝕜cr;쀀𝓀஀ABEHabcdefghjlmnoprstuv⑰⒁⒆⒍⒑┎┽╚▀♎♞♥♹♽⚚⚲⛘❝❨➋⟀⠁⠒ƀart⑷⑺⑼rò৆òΕail;椛arr;椎Ā;gঔ⒋;檋ar;楢ॣ⒥\0⒪\0⒱\0\0\0\0\0⒵Ⓔ\0ⓆⓈⓍ\0⓹ute;䄺mptyv;榴raîࡌbda;䎻gƀ;dlࢎⓁⓃ;榑åࢎ;檅uo耻«䂫rЀ;bfhlpst࢙ⓞⓦⓩ⓫⓮⓱⓵Ā;f࢝ⓣs;椟s;椝ë≒p;憫l;椹im;楳l;憢ƀ;ae⓿─┄檫il;椙Ā;s┉┊檭;쀀⪭︀ƀabr┕┙┝rr;椌rk;杲Āak┢┬cĀek┨┪;䁻;䁛Āes┱┳;榋lĀdu┹┻;榏;榍Ȁaeuy╆╋╖╘ron;䄾Ādi═╔il;䄼ìࢰâ┩;䐻Ȁcqrs╣╦╭╽a;椶uoĀ;rนᝆĀdu╲╷har;楧shar;楋h;憲ʀ;fgqs▋▌উ◳◿扤tʀahlrt▘▤▷◂◨rrowĀ;t࢙□aé⓶arpoonĀdu▯▴own»њp»०eftarrows;懇ightƀahs◍◖◞rrowĀ;sࣴࢧarpoonó྘quigarro÷⇰hreetimes;拋ƀ;qs▋ও◺lanôবʀ;cdgsব☊☍☝☨c;檨otĀ;o☔☕橿Ā;r☚☛檁;檃Ā;e☢☥쀀⋚︀s;檓ʀadegs☳☹☽♉♋pproøⓆot;拖qĀgq♃♅ôউgtò⒌ôছiíলƀilr♕࣡♚sht;楼;쀀𝔩Ā;Eজ♣;檑š♩♶rĀdu▲♮Ā;l॥♳;楪lk;斄cy;䑙ʀ;achtੈ⚈⚋⚑⚖rò◁orneòᴈard;楫ri;旺Āio⚟⚤dot;䅀ustĀ;a⚬⚭掰che»⚭ȀEaes⚻⚽⛉⛔;扨pĀ;p⛃⛄檉rox»⛄Ā;q⛎⛏檇Ā;q⛎⚻im;拦Ѐabnoptwz⛩⛴⛷✚✯❁❇❐Ānr⛮⛱g;柬r;懽rëࣁgƀlmr⛿✍✔eftĀar০✇ightá৲apsto;柼ightá৽parrowĀlr✥✩efô⓭ight;憬ƀafl✶✹✽r;榅;쀀𝕝us;樭imes;樴š❋❏st;戗áፎƀ;ef❗❘᠀旊nge»❘arĀ;l❤❥䀨t;榓ʀachmt❳❶❼➅➇ròࢨorneòᶌarĀ;d྘➃;業;怎ri;抿̀achiqt➘➝ੀ➢➮➻quo;怹r;쀀𝓁mƀ;egল➪➬;檍;檏Ābu┪➳oĀ;rฟ➹;怚rok;䅂萀<;cdhilqrࠫ⟒☹⟜⟠⟥⟪⟰Āci⟗⟙;檦r;橹reå◲mes;拉arr;楶uest;橻ĀPi⟵⟹ar;榖ƀ;ef⠀भ᠛旃rĀdu⠇⠍shar;楊har;楦Āen⠗⠡rtneqq;쀀≨︀Å⠞܀Dacdefhilnopsu⡀⡅⢂⢎⢓⢠⢥⢨⣚⣢⣤ઃ⣳⤂Dot;戺Ȁclpr⡎⡒⡣⡽r耻¯䂯Āet⡗⡙;時Ā;e⡞⡟朠se»⡟Ā;sျ⡨toȀ;dluျ⡳⡷⡻owîҌefôएðᏑker;斮Āoy⢇⢌mma;権;䐼ash;怔asuredangle»ᘦr;쀀𝔪o;愧ƀcdn⢯⢴⣉ro耻µ䂵Ȁ;acdᑤ⢽⣀⣄sôᚧir;櫰ot肻·Ƶusƀ;bd⣒ᤃ⣓戒Ā;uᴼ⣘;横ţ⣞⣡p;櫛ò−ðઁĀdp⣩⣮els;抧f;쀀𝕞Āct⣸⣽r;쀀𝓂pos»ᖝƀ;lm⤉⤊⤍䎼timap;抸ఀGLRVabcdefghijlmoprstuvw⥂⥓⥾⦉⦘⧚⧩⨕⨚⩘⩝⪃⪕⪤⪨⬄⬇⭄⭿⮮ⰴⱧⱼ⳩Āgt⥇⥋;쀀⋙̸Ā;v⥐௏쀀≫⃒ƀelt⥚⥲⥶ftĀar⥡⥧rrow;懍ightarrow;懎;쀀⋘̸Ā;v⥻ే쀀≪⃒ightarrow;懏ĀDd⦎⦓ash;抯ash;抮ʀbcnpt⦣⦧⦬⦱⧌la»˞ute;䅄g;쀀∠⃒ʀ;Eiop඄⦼⧀⧅⧈;쀀⩰̸d;쀀≋̸s;䅉roø඄urĀ;a⧓⧔普lĀ;s⧓ସǳ⧟\0⧣p肻 ଷmpĀ;e௹ఀʀaeouy⧴⧾⨃⨐⨓ǰ⧹\0⧻;橃on;䅈dil;䅆ngĀ;dൾ⨊ot;쀀⩭̸p;橂;䐽ash;怓΀;Aadqsxஒ⨩⨭⨻⩁⩅⩐rr;懗rĀhr⨳⨶k;椤Ā;oᏲᏰot;쀀≐̸uiöୣĀei⩊⩎ar;椨í஘istĀ;s஠டr;쀀𝔫ȀEest௅⩦⩹⩼ƀ;qs஼⩭௡ƀ;qs஼௅⩴lanô௢ií௪Ā;rஶ⪁»ஷƀAap⪊⪍⪑rò⥱rr;憮ar;櫲ƀ;svྍ⪜ྌĀ;d⪡⪢拼;拺cy;䑚΀AEadest⪷⪺⪾⫂⫅⫶⫹rò⥦;쀀≦̸rr;憚r;急Ȁ;fqs఻⫎⫣⫯tĀar⫔⫙rro÷⫁ightarro÷⪐ƀ;qs఻⪺⫪lanôౕĀ;sౕ⫴»శiíౝĀ;rవ⫾iĀ;eచథiäඐĀpt⬌⬑f;쀀𝕟膀¬;in⬙⬚⬶䂬nȀ;Edvஉ⬤⬨⬮;쀀⋹̸ot;쀀⋵̸ǡஉ⬳⬵;拷;拶iĀ;vಸ⬼ǡಸ⭁⭃;拾;拽ƀaor⭋⭣⭩rȀ;ast୻⭕⭚⭟lleì୻l;쀀⫽⃥;쀀∂̸lint;樔ƀ;ceಒ⭰⭳uåಥĀ;cಘ⭸Ā;eಒ⭽ñಘȀAait⮈⮋⮝⮧rò⦈rrƀ;cw⮔⮕⮙憛;쀀⤳̸;쀀↝̸ghtarrow»⮕riĀ;eೋೖ΀chimpqu⮽⯍⯙⬄୸⯤⯯Ȁ;cerല⯆ഷ⯉uå൅;쀀𝓃ortɭ⬅\0\0⯖ará⭖mĀ;e൮⯟Ā;q൴൳suĀbp⯫⯭å೸åഋƀbcp⯶ⰑⰙȀ;Ees⯿ⰀഢⰄ抄;쀀⫅̸etĀ;eഛⰋqĀ;qണⰀcĀ;eലⰗñസȀ;EesⰢⰣൟⰧ抅;쀀⫆̸etĀ;e൘ⰮqĀ;qൠⰣȀgilrⰽⰿⱅⱇìௗlde耻ñ䃱çృiangleĀlrⱒⱜeftĀ;eచⱚñదightĀ;eೋⱥñ೗Ā;mⱬⱭ䎽ƀ;esⱴⱵⱹ䀣ro;愖p;怇ҀDHadgilrsⲏⲔⲙⲞⲣⲰⲶⳓⳣash;抭arr;椄p;쀀≍⃒ash;抬ĀetⲨⲬ;쀀≥⃒;쀀>⃒nfin;槞ƀAetⲽⳁⳅrr;椂;쀀≤⃒Ā;rⳊⳍ쀀<⃒ie;쀀⊴⃒ĀAtⳘⳜrr;椃rie;쀀⊵⃒im;쀀∼⃒ƀAan⳰⳴ⴂrr;懖rĀhr⳺⳽k;椣Ā;oᏧᏥear;椧ቓ᪕\0\0\0\0\0\0\0\0\0\0\0\0\0ⴭ\0ⴸⵈⵠⵥ⵲ⶄᬇ\0\0ⶍⶫ\0ⷈⷎ\0ⷜ⸙⸫⸾⹃Ācsⴱ᪗ute耻ó䃳ĀiyⴼⵅrĀ;c᪞ⵂ耻ô䃴;䐾ʀabios᪠ⵒⵗǈⵚlac;䅑v;樸old;榼lig;䅓Ācr⵩⵭ir;榿;쀀𝔬ͯ⵹\0\0⵼\0ⶂn;䋛ave耻ò䃲;槁Ābmⶈ෴ar;榵Ȁacitⶕ⶘ⶥⶨrò᪀Āir⶝ⶠr;榾oss;榻nå๒;槀ƀaeiⶱⶵⶹcr;䅍ga;䏉ƀcdnⷀⷅǍron;䎿;榶pf;쀀𝕠ƀaelⷔ⷗ǒr;榷rp;榹΀;adiosvⷪⷫⷮ⸈⸍⸐⸖戨rò᪆Ȁ;efmⷷⷸ⸂⸅橝rĀ;oⷾⷿ愴f»ⷿ耻ª䂪耻º䂺gof;抶r;橖lope;橗;橛ƀclo⸟⸡⸧ò⸁ash耻ø䃸l;折iŬⸯ⸴de耻õ䃵esĀ;aǛ⸺s;樶ml耻ö䃶bar;挽ૡ⹞\0⹽\0⺀⺝\0⺢⺹\0\0⻋ຜ\0⼓\0\0⼫⾼\0⿈rȀ;astЃ⹧⹲຅脀¶;l⹭⹮䂶leìЃɩ⹸\0\0⹻m;櫳;櫽y;䐿rʀcimpt⺋⺏⺓ᡥ⺗nt;䀥od;䀮il;怰enk;怱r;쀀𝔭ƀimo⺨⺰⺴Ā;v⺭⺮䏆;䏕maô੶ne;明ƀ;tv⺿⻀⻈䏀chfork»´;䏖Āau⻏⻟nĀck⻕⻝kĀ;h⇴⻛;愎ö⇴sҀ;abcdemst⻳⻴ᤈ⻹⻽⼄⼆⼊⼎䀫cir;樣ir;樢Āouᵀ⼂;樥;橲n肻±ຝim;樦wo;樧ƀipu⼙⼠⼥ntint;樕f;쀀𝕡nd耻£䂣Ԁ;Eaceinosu່⼿⽁⽄⽇⾁⾉⾒⽾⾶;檳p;檷uå໙Ā;c໎⽌̀;acens່⽙⽟⽦⽨⽾pproø⽃urlyeñ໙ñ໎ƀaes⽯⽶⽺pprox;檹qq;檵im;拨iíໟmeĀ;s⾈ຮ怲ƀEas⽸⾐⽺ð⽵ƀdfp໬⾙⾯ƀals⾠⾥⾪lar;挮ine;挒urf;挓Ā;t໻⾴ï໻rel;抰Āci⿀⿅r;쀀𝓅;䏈ncsp;怈̀fiopsu⿚⋢⿟⿥⿫⿱r;쀀𝔮pf;쀀𝕢rime;恗cr;쀀𝓆ƀaeo⿸〉〓tĀei⿾々rnionóڰnt;樖stĀ;e【】䀿ñἙô༔઀ABHabcdefhilmnoprstux぀けさすムㄎㄫㅇㅢㅲㆎ㈆㈕㈤㈩㉘㉮㉲㊐㊰㊷ƀartぇおがròႳòϝail;検aròᱥar;楤΀cdenqrtとふへみわゔヌĀeuねぱ;쀀∽̱te;䅕iãᅮmptyv;榳gȀ;del࿑らるろ;榒;榥å࿑uo耻»䂻rր;abcfhlpstw࿜ガクシスゼゾダッデナp;極Ā;f࿠ゴs;椠;椳s;椞ë≝ð✮l;楅im;楴l;憣;憝Āaiパフil;椚oĀ;nホボ戶aló༞ƀabrョリヮrò៥rk;杳ĀakンヽcĀekヹ・;䁽;䁝Āes㄂㄄;榌lĀduㄊㄌ;榎;榐Ȁaeuyㄗㄜㄧㄩron;䅙Ādiㄡㄥil;䅗ì࿲âヺ;䑀Ȁclqsㄴㄷㄽㅄa;椷dhar;楩uoĀ;rȎȍh;憳ƀacgㅎㅟངlȀ;ipsླྀㅘㅛႜnåႻarôྩt;断ƀilrㅩဣㅮsht;楽;쀀𝔯ĀaoㅷㆆrĀduㅽㅿ»ѻĀ;l႑ㆄ;楬Ā;vㆋㆌ䏁;䏱ƀgns㆕ㇹㇼht̀ahlrstㆤㆰ㇂㇘㇤㇮rrowĀ;t࿜ㆭaéトarpoonĀduㆻㆿowîㅾp»႒eftĀah㇊㇐rrowó࿪arpoonóՑightarrows;應quigarro÷ニhreetimes;拌g;䋚ingdotseñἲƀahm㈍㈐㈓rò࿪aòՑ;怏oustĀ;a㈞㈟掱che»㈟mid;櫮Ȁabpt㈲㈽㉀㉒Ānr㈷㈺g;柭r;懾rëဃƀafl㉇㉊㉎r;榆;쀀𝕣us;樮imes;樵Āap㉝㉧rĀ;g㉣㉤䀩t;榔olint;樒arò㇣Ȁachq㉻㊀Ⴜ㊅quo;怺r;쀀𝓇Ābu・㊊oĀ;rȔȓƀhir㊗㊛㊠reåㇸmes;拊iȀ;efl㊪ၙᠡ㊫方tri;槎luhar;楨;愞ൡ㋕㋛㋟㌬㌸㍱\0㍺㎤\0\0㏬㏰\0㐨㑈㑚㒭㒱㓊㓱\0㘖\0\0㘳cute;䅛quï➺Ԁ;Eaceinpsyᇭ㋳㋵㋿㌂㌋㌏㌟㌦㌩;檴ǰ㋺\0㋼;檸on;䅡uåᇾĀ;dᇳ㌇il;䅟rc;䅝ƀEas㌖㌘㌛;檶p;檺im;择olint;樓iíሄ;䑁otƀ;be㌴ᵇ㌵担;橦΀Aacmstx㍆㍊㍗㍛㍞㍣㍭rr;懘rĀhr㍐㍒ë∨Ā;oਸ਼਴t耻§䂧i;䀻war;椩mĀin㍩ðnuóñt;朶rĀ;o㍶⁕쀀𝔰Ȁacoy㎂㎆㎑㎠rp;景Āhy㎋㎏cy;䑉;䑈rtɭ㎙\0\0㎜iäᑤaraì⹯耻­䂭Āgm㎨㎴maƀ;fv㎱㎲㎲䏃;䏂Ѐ;deglnprካ㏅㏉㏎㏖㏞㏡㏦ot;橪Ā;q኱ኰĀ;E㏓㏔檞;檠Ā;E㏛㏜檝;檟e;扆lus;樤arr;楲aròᄽȀaeit㏸㐈㐏㐗Āls㏽㐄lsetmé㍪hp;樳parsl;槤Ādlᑣ㐔e;挣Ā;e㐜㐝檪Ā;s㐢㐣檬;쀀⪬︀ƀflp㐮㐳㑂tcy;䑌Ā;b㐸㐹䀯Ā;a㐾㐿槄r;挿f;쀀𝕤aĀdr㑍ЂesĀ;u㑔㑕晠it»㑕ƀcsu㑠㑹㒟Āau㑥㑯pĀ;sᆈ㑫;쀀⊓︀pĀ;sᆴ㑵;쀀⊔︀uĀbp㑿㒏ƀ;esᆗᆜ㒆etĀ;eᆗ㒍ñᆝƀ;esᆨᆭ㒖etĀ;eᆨ㒝ñᆮƀ;afᅻ㒦ְrť㒫ֱ»ᅼaròᅈȀcemt㒹㒾㓂㓅r;쀀𝓈tmîñiì㐕aræᆾĀar㓎㓕rĀ;f㓔ឿ昆Āan㓚㓭ightĀep㓣㓪psiloîỠhé⺯s»⡒ʀbcmnp㓻㕞ሉ㖋㖎Ҁ;Edemnprs㔎㔏㔑㔕㔞㔣㔬㔱㔶抂;櫅ot;檽Ā;dᇚ㔚ot;櫃ult;櫁ĀEe㔨㔪;櫋;把lus;檿arr;楹ƀeiu㔽㕒㕕tƀ;en㔎㕅㕋qĀ;qᇚ㔏eqĀ;q㔫㔨m;櫇Ābp㕚㕜;櫕;櫓c̀;acensᇭ㕬㕲㕹㕻㌦pproø㋺urlyeñᇾñᇳƀaes㖂㖈㌛pproø㌚qñ㌗g;晪ڀ123;Edehlmnps㖩㖬㖯ሜ㖲㖴㗀㗉㗕㗚㗟㗨㗭耻¹䂹耻²䂲耻³䂳;櫆Āos㖹㖼t;檾ub;櫘Ā;dሢ㗅ot;櫄sĀou㗏㗒l;柉b;櫗arr;楻ult;櫂ĀEe㗤㗦;櫌;抋lus;櫀ƀeiu㗴㘉㘌tƀ;enሜ㗼㘂qĀ;qሢ㖲eqĀ;q㗧㗤m;櫈Ābp㘑㘓;櫔;櫖ƀAan㘜㘠㘭rr;懙rĀhr㘦㘨ë∮Ā;oਫ਩war;椪lig耻ß䃟௡㙑㙝㙠ዎ㙳㙹\0㙾㛂\0\0\0\0\0㛛㜃\0㜉㝬\0\0\0㞇ɲ㙖\0\0㙛get;挖;䏄rë๟ƀaey㙦㙫㙰ron;䅥dil;䅣;䑂lrec;挕r;쀀𝔱Ȁeiko㚆㚝㚵㚼ǲ㚋\0㚑eĀ4fኄኁaƀ;sv㚘㚙㚛䎸ym;䏑Ācn㚢㚲kĀas㚨㚮pproø዁im»ኬsðኞĀas㚺㚮ð዁rn耻þ䃾Ǭ̟㛆⋧es膀×;bd㛏㛐㛘䃗Ā;aᤏ㛕r;樱;樰ƀeps㛡㛣㜀á⩍Ȁ;bcf҆㛬㛰㛴ot;挶ir;櫱Ā;o㛹㛼쀀𝕥rk;櫚á㍢rime;怴ƀaip㜏㜒㝤dåቈ΀adempst㜡㝍㝀㝑㝗㝜㝟ngleʀ;dlqr㜰㜱㜶㝀㝂斵own»ᶻeftĀ;e⠀㜾ñम;扜ightĀ;e㊪㝋ñၚot;旬inus;樺lus;樹b;槍ime;樻ezium;揢ƀcht㝲㝽㞁Āry㝷㝻;쀀𝓉;䑆cy;䑛rok;䅧Āio㞋㞎xô᝷headĀlr㞗㞠eftarro÷ࡏightarrow»ཝऀAHabcdfghlmoprstuw㟐㟓㟗㟤㟰㟼㠎㠜㠣㠴㡑㡝㡫㢩㣌㣒㣪㣶ròϭar;楣Ācr㟜㟢ute耻ú䃺òᅐrǣ㟪\0㟭y;䑞ve;䅭Āiy㟵㟺rc耻û䃻;䑃ƀabh㠃㠆㠋ròᎭlac;䅱aòᏃĀir㠓㠘sht;楾;쀀𝔲rave耻ù䃹š㠧㠱rĀlr㠬㠮»ॗ»ႃlk;斀Āct㠹㡍ɯ㠿\0\0㡊rnĀ;e㡅㡆挜r»㡆op;挏ri;旸Āal㡖㡚cr;䅫肻¨͉Āgp㡢㡦on;䅳f;쀀𝕦̀adhlsuᅋ㡸㡽፲㢑㢠ownáᎳarpoonĀlr㢈㢌efô㠭ighô㠯iƀ;hl㢙㢚㢜䏅»ᏺon»㢚parrows;懈ƀcit㢰㣄㣈ɯ㢶\0\0㣁rnĀ;e㢼㢽挝r»㢽op;挎ng;䅯ri;旹cr;쀀𝓊ƀdir㣙㣝㣢ot;拰lde;䅩iĀ;f㜰㣨»᠓Āam㣯㣲rò㢨l耻ü䃼angle;榧ހABDacdeflnoprsz㤜㤟㤩㤭㦵㦸㦽㧟㧤㧨㧳㧹㧽㨁㨠ròϷarĀ;v㤦㤧櫨;櫩asèϡĀnr㤲㤷grt;榜΀eknprst㓣㥆㥋㥒㥝㥤㦖appá␕othinçẖƀhir㓫⻈㥙opô⾵Ā;hᎷ㥢ïㆍĀiu㥩㥭gmá㎳Ābp㥲㦄setneqĀ;q㥽㦀쀀⊊︀;쀀⫋︀setneqĀ;q㦏㦒쀀⊋︀;쀀⫌︀Āhr㦛㦟etá㚜iangleĀlr㦪㦯eft»थight»ၑy;䐲ash»ံƀelr㧄㧒㧗ƀ;beⷪ㧋㧏ar;抻q;扚lip;拮Ābt㧜ᑨaòᑩr;쀀𝔳tré㦮suĀbp㧯㧱»ജ»൙pf;쀀𝕧roð໻tré㦴Ācu㨆㨋r;쀀𝓋Ābp㨐㨘nĀEe㦀㨖»㥾nĀEe㦒㨞»㦐igzag;榚΀cefoprs㨶㨻㩖㩛㩔㩡㩪irc;䅵Ādi㩀㩑Ābg㩅㩉ar;機eĀ;qᗺ㩏;扙erp;愘r;쀀𝔴pf;쀀𝕨Ā;eᑹ㩦atèᑹcr;쀀𝓌ૣណ㪇\0㪋\0㪐㪛\0\0㪝㪨㪫㪯\0\0㫃㫎\0㫘ៜ៟tré៑r;쀀𝔵ĀAa㪔㪗ròσrò৶;䎾ĀAa㪡㪤ròθrò৫að✓is;拻ƀdptឤ㪵㪾Āfl㪺ឩ;쀀𝕩imåឲĀAa㫇㫊ròώròਁĀcq㫒ីr;쀀𝓍Āpt៖㫜ré។Ѐacefiosu㫰㫽㬈㬌㬑㬕㬛㬡cĀuy㫶㫻te耻ý䃽;䑏Āiy㬂㬆rc;䅷;䑋n耻¥䂥r;쀀𝔶cy;䑗pf;쀀𝕪cr;쀀𝓎Ācm㬦㬩y;䑎l耻ÿ䃿Ԁacdefhiosw㭂㭈㭔㭘㭤㭩㭭㭴㭺㮀cute;䅺Āay㭍㭒ron;䅾;䐷ot;䅼Āet㭝㭡træᕟa;䎶r;쀀𝔷cy;䐶grarr;懝pf;쀀𝕫cr;쀀𝓏Ājn㮅㮇;怍j;怌'.split("").map((c) => c.charCodeAt(0))
);
const xmlDecodeTree = new Uint16Array(
  // prettier-ignore
  "Ȁaglq	\x1Bɭ\0\0p;䀦os;䀧t;䀾t;䀼uot;䀢".split("").map((c) => c.charCodeAt(0))
);
var _a;
const decodeMap = /* @__PURE__ */ new Map([
  [0, 65533],
  // C1 Unicode control character reference replacements
  [128, 8364],
  [130, 8218],
  [131, 402],
  [132, 8222],
  [133, 8230],
  [134, 8224],
  [135, 8225],
  [136, 710],
  [137, 8240],
  [138, 352],
  [139, 8249],
  [140, 338],
  [142, 381],
  [145, 8216],
  [146, 8217],
  [147, 8220],
  [148, 8221],
  [149, 8226],
  [150, 8211],
  [151, 8212],
  [152, 732],
  [153, 8482],
  [154, 353],
  [155, 8250],
  [156, 339],
  [158, 382],
  [159, 376]
]);
const fromCodePoint$1 = (
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition, node/no-unsupported-features/es-builtins
  (_a = String.fromCodePoint) !== null && _a !== void 0 ? _a : function(codePoint) {
    let output2 = "";
    if (codePoint > 65535) {
      codePoint -= 65536;
      output2 += String.fromCharCode(codePoint >>> 10 & 1023 | 55296);
      codePoint = 56320 | codePoint & 1023;
    }
    output2 += String.fromCharCode(codePoint);
    return output2;
  }
);
function replaceCodePoint(codePoint) {
  var _a2;
  if (codePoint >= 55296 && codePoint <= 57343 || codePoint > 1114111) {
    return 65533;
  }
  return (_a2 = decodeMap.get(codePoint)) !== null && _a2 !== void 0 ? _a2 : codePoint;
}
var CharCodes;
(function(CharCodes2) {
  CharCodes2[CharCodes2["NUM"] = 35] = "NUM";
  CharCodes2[CharCodes2["SEMI"] = 59] = "SEMI";
  CharCodes2[CharCodes2["EQUALS"] = 61] = "EQUALS";
  CharCodes2[CharCodes2["ZERO"] = 48] = "ZERO";
  CharCodes2[CharCodes2["NINE"] = 57] = "NINE";
  CharCodes2[CharCodes2["LOWER_A"] = 97] = "LOWER_A";
  CharCodes2[CharCodes2["LOWER_F"] = 102] = "LOWER_F";
  CharCodes2[CharCodes2["LOWER_X"] = 120] = "LOWER_X";
  CharCodes2[CharCodes2["LOWER_Z"] = 122] = "LOWER_Z";
  CharCodes2[CharCodes2["UPPER_A"] = 65] = "UPPER_A";
  CharCodes2[CharCodes2["UPPER_F"] = 70] = "UPPER_F";
  CharCodes2[CharCodes2["UPPER_Z"] = 90] = "UPPER_Z";
})(CharCodes || (CharCodes = {}));
const TO_LOWER_BIT = 32;
var BinTrieFlags;
(function(BinTrieFlags2) {
  BinTrieFlags2[BinTrieFlags2["VALUE_LENGTH"] = 49152] = "VALUE_LENGTH";
  BinTrieFlags2[BinTrieFlags2["BRANCH_LENGTH"] = 16256] = "BRANCH_LENGTH";
  BinTrieFlags2[BinTrieFlags2["JUMP_TABLE"] = 127] = "JUMP_TABLE";
})(BinTrieFlags || (BinTrieFlags = {}));
function isNumber(code2) {
  return code2 >= CharCodes.ZERO && code2 <= CharCodes.NINE;
}
function isHexadecimalCharacter(code2) {
  return code2 >= CharCodes.UPPER_A && code2 <= CharCodes.UPPER_F || code2 >= CharCodes.LOWER_A && code2 <= CharCodes.LOWER_F;
}
function isAsciiAlphaNumeric(code2) {
  return code2 >= CharCodes.UPPER_A && code2 <= CharCodes.UPPER_Z || code2 >= CharCodes.LOWER_A && code2 <= CharCodes.LOWER_Z || isNumber(code2);
}
function isEntityInAttributeInvalidEnd(code2) {
  return code2 === CharCodes.EQUALS || isAsciiAlphaNumeric(code2);
}
var EntityDecoderState;
(function(EntityDecoderState2) {
  EntityDecoderState2[EntityDecoderState2["EntityStart"] = 0] = "EntityStart";
  EntityDecoderState2[EntityDecoderState2["NumericStart"] = 1] = "NumericStart";
  EntityDecoderState2[EntityDecoderState2["NumericDecimal"] = 2] = "NumericDecimal";
  EntityDecoderState2[EntityDecoderState2["NumericHex"] = 3] = "NumericHex";
  EntityDecoderState2[EntityDecoderState2["NamedEntity"] = 4] = "NamedEntity";
})(EntityDecoderState || (EntityDecoderState = {}));
var DecodingMode;
(function(DecodingMode2) {
  DecodingMode2[DecodingMode2["Legacy"] = 0] = "Legacy";
  DecodingMode2[DecodingMode2["Strict"] = 1] = "Strict";
  DecodingMode2[DecodingMode2["Attribute"] = 2] = "Attribute";
})(DecodingMode || (DecodingMode = {}));
class EntityDecoder {
  constructor(decodeTree, emitCodePoint, errors2) {
    this.decodeTree = decodeTree;
    this.emitCodePoint = emitCodePoint;
    this.errors = errors2;
    this.state = EntityDecoderState.EntityStart;
    this.consumed = 1;
    this.result = 0;
    this.treeIndex = 0;
    this.excess = 1;
    this.decodeMode = DecodingMode.Strict;
  }
  /** Resets the instance to make it reusable. */
  startEntity(decodeMode) {
    this.decodeMode = decodeMode;
    this.state = EntityDecoderState.EntityStart;
    this.result = 0;
    this.treeIndex = 0;
    this.excess = 1;
    this.consumed = 1;
  }
  /**
   * Write an entity to the decoder. This can be called multiple times with partial entities.
   * If the entity is incomplete, the decoder will return -1.
   *
   * Mirrors the implementation of `getDecoder`, but with the ability to stop decoding if the
   * entity is incomplete, and resume when the next string is written.
   *
   * @param string The string containing the entity (or a continuation of the entity).
   * @param offset The offset at which the entity begins. Should be 0 if this is not the first call.
   * @returns The number of characters that were consumed, or -1 if the entity is incomplete.
   */
  write(str, offset) {
    switch (this.state) {
      case EntityDecoderState.EntityStart: {
        if (str.charCodeAt(offset) === CharCodes.NUM) {
          this.state = EntityDecoderState.NumericStart;
          this.consumed += 1;
          return this.stateNumericStart(str, offset + 1);
        }
        this.state = EntityDecoderState.NamedEntity;
        return this.stateNamedEntity(str, offset);
      }
      case EntityDecoderState.NumericStart: {
        return this.stateNumericStart(str, offset);
      }
      case EntityDecoderState.NumericDecimal: {
        return this.stateNumericDecimal(str, offset);
      }
      case EntityDecoderState.NumericHex: {
        return this.stateNumericHex(str, offset);
      }
      case EntityDecoderState.NamedEntity: {
        return this.stateNamedEntity(str, offset);
      }
    }
  }
  /**
   * Switches between the numeric decimal and hexadecimal states.
   *
   * Equivalent to the `Numeric character reference state` in the HTML spec.
   *
   * @param str The string containing the entity (or a continuation of the entity).
   * @param offset The current offset.
   * @returns The number of characters that were consumed, or -1 if the entity is incomplete.
   */
  stateNumericStart(str, offset) {
    if (offset >= str.length) {
      return -1;
    }
    if ((str.charCodeAt(offset) | TO_LOWER_BIT) === CharCodes.LOWER_X) {
      this.state = EntityDecoderState.NumericHex;
      this.consumed += 1;
      return this.stateNumericHex(str, offset + 1);
    }
    this.state = EntityDecoderState.NumericDecimal;
    return this.stateNumericDecimal(str, offset);
  }
  addToNumericResult(str, start, end, base2) {
    if (start !== end) {
      const digitCount = end - start;
      this.result = this.result * Math.pow(base2, digitCount) + parseInt(str.substr(start, digitCount), base2);
      this.consumed += digitCount;
    }
  }
  /**
   * Parses a hexadecimal numeric entity.
   *
   * Equivalent to the `Hexademical character reference state` in the HTML spec.
   *
   * @param str The string containing the entity (or a continuation of the entity).
   * @param offset The current offset.
   * @returns The number of characters that were consumed, or -1 if the entity is incomplete.
   */
  stateNumericHex(str, offset) {
    const startIdx = offset;
    while (offset < str.length) {
      const char = str.charCodeAt(offset);
      if (isNumber(char) || isHexadecimalCharacter(char)) {
        offset += 1;
      } else {
        this.addToNumericResult(str, startIdx, offset, 16);
        return this.emitNumericEntity(char, 3);
      }
    }
    this.addToNumericResult(str, startIdx, offset, 16);
    return -1;
  }
  /**
   * Parses a decimal numeric entity.
   *
   * Equivalent to the `Decimal character reference state` in the HTML spec.
   *
   * @param str The string containing the entity (or a continuation of the entity).
   * @param offset The current offset.
   * @returns The number of characters that were consumed, or -1 if the entity is incomplete.
   */
  stateNumericDecimal(str, offset) {
    const startIdx = offset;
    while (offset < str.length) {
      const char = str.charCodeAt(offset);
      if (isNumber(char)) {
        offset += 1;
      } else {
        this.addToNumericResult(str, startIdx, offset, 10);
        return this.emitNumericEntity(char, 2);
      }
    }
    this.addToNumericResult(str, startIdx, offset, 10);
    return -1;
  }
  /**
   * Validate and emit a numeric entity.
   *
   * Implements the logic from the `Hexademical character reference start
   * state` and `Numeric character reference end state` in the HTML spec.
   *
   * @param lastCp The last code point of the entity. Used to see if the
   *               entity was terminated with a semicolon.
   * @param expectedLength The minimum number of characters that should be
   *                       consumed. Used to validate that at least one digit
   *                       was consumed.
   * @returns The number of characters that were consumed.
   */
  emitNumericEntity(lastCp, expectedLength) {
    var _a2;
    if (this.consumed <= expectedLength) {
      (_a2 = this.errors) === null || _a2 === void 0 ? void 0 : _a2.absenceOfDigitsInNumericCharacterReference(this.consumed);
      return 0;
    }
    if (lastCp === CharCodes.SEMI) {
      this.consumed += 1;
    } else if (this.decodeMode === DecodingMode.Strict) {
      return 0;
    }
    this.emitCodePoint(replaceCodePoint(this.result), this.consumed);
    if (this.errors) {
      if (lastCp !== CharCodes.SEMI) {
        this.errors.missingSemicolonAfterCharacterReference();
      }
      this.errors.validateNumericCharacterReference(this.result);
    }
    return this.consumed;
  }
  /**
   * Parses a named entity.
   *
   * Equivalent to the `Named character reference state` in the HTML spec.
   *
   * @param str The string containing the entity (or a continuation of the entity).
   * @param offset The current offset.
   * @returns The number of characters that were consumed, or -1 if the entity is incomplete.
   */
  stateNamedEntity(str, offset) {
    const { decodeTree } = this;
    let current = decodeTree[this.treeIndex];
    let valueLength = (current & BinTrieFlags.VALUE_LENGTH) >> 14;
    for (; offset < str.length; offset++, this.excess++) {
      const char = str.charCodeAt(offset);
      this.treeIndex = determineBranch(decodeTree, current, this.treeIndex + Math.max(1, valueLength), char);
      if (this.treeIndex < 0) {
        return this.result === 0 || // If we are parsing an attribute
        this.decodeMode === DecodingMode.Attribute && // We shouldn't have consumed any characters after the entity,
        (valueLength === 0 || // And there should be no invalid characters.
        isEntityInAttributeInvalidEnd(char)) ? 0 : this.emitNotTerminatedNamedEntity();
      }
      current = decodeTree[this.treeIndex];
      valueLength = (current & BinTrieFlags.VALUE_LENGTH) >> 14;
      if (valueLength !== 0) {
        if (char === CharCodes.SEMI) {
          return this.emitNamedEntityData(this.treeIndex, valueLength, this.consumed + this.excess);
        }
        if (this.decodeMode !== DecodingMode.Strict) {
          this.result = this.treeIndex;
          this.consumed += this.excess;
          this.excess = 0;
        }
      }
    }
    return -1;
  }
  /**
   * Emit a named entity that was not terminated with a semicolon.
   *
   * @returns The number of characters consumed.
   */
  emitNotTerminatedNamedEntity() {
    var _a2;
    const { result: result2, decodeTree } = this;
    const valueLength = (decodeTree[result2] & BinTrieFlags.VALUE_LENGTH) >> 14;
    this.emitNamedEntityData(result2, valueLength, this.consumed);
    (_a2 = this.errors) === null || _a2 === void 0 ? void 0 : _a2.missingSemicolonAfterCharacterReference();
    return this.consumed;
  }
  /**
   * Emit a named entity.
   *
   * @param result The index of the entity in the decode tree.
   * @param valueLength The number of bytes in the entity.
   * @param consumed The number of characters consumed.
   *
   * @returns The number of characters consumed.
   */
  emitNamedEntityData(result2, valueLength, consumed) {
    const { decodeTree } = this;
    this.emitCodePoint(valueLength === 1 ? decodeTree[result2] & ~BinTrieFlags.VALUE_LENGTH : decodeTree[result2 + 1], consumed);
    if (valueLength === 3) {
      this.emitCodePoint(decodeTree[result2 + 2], consumed);
    }
    return consumed;
  }
  /**
   * Signal to the parser that the end of the input was reached.
   *
   * Remaining data will be emitted and relevant errors will be produced.
   *
   * @returns The number of characters consumed.
   */
  end() {
    var _a2;
    switch (this.state) {
      case EntityDecoderState.NamedEntity: {
        return this.result !== 0 && (this.decodeMode !== DecodingMode.Attribute || this.result === this.treeIndex) ? this.emitNotTerminatedNamedEntity() : 0;
      }
      // Otherwise, emit a numeric entity if we have one.
      case EntityDecoderState.NumericDecimal: {
        return this.emitNumericEntity(0, 2);
      }
      case EntityDecoderState.NumericHex: {
        return this.emitNumericEntity(0, 3);
      }
      case EntityDecoderState.NumericStart: {
        (_a2 = this.errors) === null || _a2 === void 0 ? void 0 : _a2.absenceOfDigitsInNumericCharacterReference(this.consumed);
        return 0;
      }
      case EntityDecoderState.EntityStart: {
        return 0;
      }
    }
  }
}
function getDecoder(decodeTree) {
  let ret = "";
  const decoder = new EntityDecoder(decodeTree, (str) => ret += fromCodePoint$1(str));
  return function decodeWithTrie(str, decodeMode) {
    let lastIndex = 0;
    let offset = 0;
    while ((offset = str.indexOf("&", offset)) >= 0) {
      ret += str.slice(lastIndex, offset);
      decoder.startEntity(decodeMode);
      const len = decoder.write(
        str,
        // Skip the "&"
        offset + 1
      );
      if (len < 0) {
        lastIndex = offset + decoder.end();
        break;
      }
      lastIndex = offset + len;
      offset = len === 0 ? lastIndex + 1 : lastIndex;
    }
    const result2 = ret + str.slice(lastIndex);
    ret = "";
    return result2;
  };
}
function determineBranch(decodeTree, current, nodeIdx, char) {
  const branchCount = (current & BinTrieFlags.BRANCH_LENGTH) >> 7;
  const jumpOffset = current & BinTrieFlags.JUMP_TABLE;
  if (branchCount === 0) {
    return jumpOffset !== 0 && char === jumpOffset ? nodeIdx : -1;
  }
  if (jumpOffset) {
    const value2 = char - jumpOffset;
    return value2 < 0 || value2 >= branchCount ? -1 : decodeTree[nodeIdx + value2] - 1;
  }
  let lo2 = nodeIdx;
  let hi = lo2 + branchCount - 1;
  while (lo2 <= hi) {
    const mid = lo2 + hi >>> 1;
    const midVal = decodeTree[mid];
    if (midVal < char) {
      lo2 = mid + 1;
    } else if (midVal > char) {
      hi = mid - 1;
    } else {
      return decodeTree[mid + branchCount];
    }
  }
  return -1;
}
const htmlDecoder = getDecoder(htmlDecodeTree);
getDecoder(xmlDecodeTree);
function decodeHTML(str, mode = DecodingMode.Legacy) {
  return htmlDecoder(str, mode);
}
function _class$1(obj) {
  return Object.prototype.toString.call(obj);
}
function isString$1(obj) {
  return _class$1(obj) === "[object String]";
}
const _hasOwnProperty = Object.prototype.hasOwnProperty;
function has(object, key2) {
  return _hasOwnProperty.call(object, key2);
}
function assign$1(obj) {
  const sources = Array.prototype.slice.call(arguments, 1);
  sources.forEach(function(source) {
    if (!source) {
      return;
    }
    if (typeof source !== "object") {
      throw new TypeError(source + "must be object");
    }
    Object.keys(source).forEach(function(key2) {
      obj[key2] = source[key2];
    });
  });
  return obj;
}
function arrayReplaceAt(src, pos, newElements) {
  return [].concat(src.slice(0, pos), newElements, src.slice(pos + 1));
}
function isValidEntityCode(c) {
  if (c >= 55296 && c <= 57343) {
    return false;
  }
  if (c >= 64976 && c <= 65007) {
    return false;
  }
  if ((c & 65535) === 65535 || (c & 65535) === 65534) {
    return false;
  }
  if (c >= 0 && c <= 8) {
    return false;
  }
  if (c === 11) {
    return false;
  }
  if (c >= 14 && c <= 31) {
    return false;
  }
  if (c >= 127 && c <= 159) {
    return false;
  }
  if (c > 1114111) {
    return false;
  }
  return true;
}
function fromCodePoint(c) {
  if (c > 65535) {
    c -= 65536;
    const surrogate1 = 55296 + (c >> 10);
    const surrogate2 = 56320 + (c & 1023);
    return String.fromCharCode(surrogate1, surrogate2);
  }
  return String.fromCharCode(c);
}
const UNESCAPE_MD_RE = /\\([!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~])/g;
const ENTITY_RE = /&([a-z#][a-z0-9]{1,31});/gi;
const UNESCAPE_ALL_RE = new RegExp(UNESCAPE_MD_RE.source + "|" + ENTITY_RE.source, "gi");
const DIGITAL_ENTITY_TEST_RE = /^#((?:x[a-f0-9]{1,8}|[0-9]{1,8}))$/i;
function replaceEntityPattern(match2, name) {
  if (name.charCodeAt(0) === 35 && DIGITAL_ENTITY_TEST_RE.test(name)) {
    const code2 = name[1].toLowerCase() === "x" ? parseInt(name.slice(2), 16) : parseInt(name.slice(1), 10);
    if (isValidEntityCode(code2)) {
      return fromCodePoint(code2);
    }
    return match2;
  }
  const decoded = decodeHTML(match2);
  if (decoded !== match2) {
    return decoded;
  }
  return match2;
}
function unescapeMd(str) {
  if (str.indexOf("\\") < 0) {
    return str;
  }
  return str.replace(UNESCAPE_MD_RE, "$1");
}
function unescapeAll(str) {
  if (str.indexOf("\\") < 0 && str.indexOf("&") < 0) {
    return str;
  }
  return str.replace(UNESCAPE_ALL_RE, function(match2, escaped, entity2) {
    if (escaped) {
      return escaped;
    }
    return replaceEntityPattern(match2, entity2);
  });
}
const HTML_ESCAPE_TEST_RE = /[&<>"]/;
const HTML_ESCAPE_REPLACE_RE = /[&<>"]/g;
const HTML_REPLACEMENTS = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;"
};
function replaceUnsafeChar(ch) {
  return HTML_REPLACEMENTS[ch];
}
function escapeHtml(str) {
  if (HTML_ESCAPE_TEST_RE.test(str)) {
    return str.replace(HTML_ESCAPE_REPLACE_RE, replaceUnsafeChar);
  }
  return str;
}
const REGEXP_ESCAPE_RE = /[.?*+^$[\]\\(){}|-]/g;
function escapeRE$1(str) {
  return str.replace(REGEXP_ESCAPE_RE, "\\$&");
}
function isSpace(code2) {
  switch (code2) {
    case 9:
    case 32:
      return true;
  }
  return false;
}
function isWhiteSpace(code2) {
  if (code2 >= 8192 && code2 <= 8202) {
    return true;
  }
  switch (code2) {
    case 9:
    // \t
    case 10:
    // \n
    case 11:
    // \v
    case 12:
    // \f
    case 13:
    // \r
    case 32:
    case 160:
    case 5760:
    case 8239:
    case 8287:
    case 12288:
      return true;
  }
  return false;
}
function isPunctChar(ch) {
  return P.test(ch) || regex.test(ch);
}
function isMdAsciiPunct(ch) {
  switch (ch) {
    case 33:
    case 34:
    case 35:
    case 36:
    case 37:
    case 38:
    case 39:
    case 40:
    case 41:
    case 42:
    case 43:
    case 44:
    case 45:
    case 46:
    case 47:
    case 58:
    case 59:
    case 60:
    case 61:
    case 62:
    case 63:
    case 64:
    case 91:
    case 92:
    case 93:
    case 94:
    case 95:
    case 96:
    case 123:
    case 124:
    case 125:
    case 126:
      return true;
    default:
      return false;
  }
}
function normalizeReference(str) {
  str = str.trim().replace(/\s+/g, " ");
  if ("ẞ".toLowerCase() === "Ṿ") {
    str = str.replace(/ẞ/g, "ß");
  }
  return str.toLowerCase().toUpperCase();
}
const lib = { mdurl, ucmicro };
const utils = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  arrayReplaceAt,
  assign: assign$1,
  escapeHtml,
  escapeRE: escapeRE$1,
  fromCodePoint,
  has,
  isMdAsciiPunct,
  isPunctChar,
  isSpace,
  isString: isString$1,
  isValidEntityCode,
  isWhiteSpace,
  lib,
  normalizeReference,
  unescapeAll,
  unescapeMd
}, Symbol.toStringTag, { value: "Module" }));
function parseLinkLabel(state, start, disableNested) {
  let level, found, marker, prevPos;
  const max = state.posMax;
  const oldPos = state.pos;
  state.pos = start + 1;
  level = 1;
  while (state.pos < max) {
    marker = state.src.charCodeAt(state.pos);
    if (marker === 93) {
      level--;
      if (level === 0) {
        found = true;
        break;
      }
    }
    prevPos = state.pos;
    state.md.inline.skipToken(state);
    if (marker === 91) {
      if (prevPos === state.pos - 1) {
        level++;
      } else if (disableNested) {
        state.pos = oldPos;
        return -1;
      }
    }
  }
  let labelEnd = -1;
  if (found) {
    labelEnd = state.pos;
  }
  state.pos = oldPos;
  return labelEnd;
}
function parseLinkDestination(str, start, max) {
  let code2;
  let pos = start;
  const result2 = {
    ok: false,
    pos: 0,
    str: ""
  };
  if (str.charCodeAt(pos) === 60) {
    pos++;
    while (pos < max) {
      code2 = str.charCodeAt(pos);
      if (code2 === 10) {
        return result2;
      }
      if (code2 === 60) {
        return result2;
      }
      if (code2 === 62) {
        result2.pos = pos + 1;
        result2.str = unescapeAll(str.slice(start + 1, pos));
        result2.ok = true;
        return result2;
      }
      if (code2 === 92 && pos + 1 < max) {
        pos += 2;
        continue;
      }
      pos++;
    }
    return result2;
  }
  let level = 0;
  while (pos < max) {
    code2 = str.charCodeAt(pos);
    if (code2 === 32) {
      break;
    }
    if (code2 < 32 || code2 === 127) {
      break;
    }
    if (code2 === 92 && pos + 1 < max) {
      if (str.charCodeAt(pos + 1) === 32) {
        break;
      }
      pos += 2;
      continue;
    }
    if (code2 === 40) {
      level++;
      if (level > 32) {
        return result2;
      }
    }
    if (code2 === 41) {
      if (level === 0) {
        break;
      }
      level--;
    }
    pos++;
  }
  if (start === pos) {
    return result2;
  }
  if (level !== 0) {
    return result2;
  }
  result2.str = unescapeAll(str.slice(start, pos));
  result2.pos = pos;
  result2.ok = true;
  return result2;
}
function parseLinkTitle(str, start, max, prev_state) {
  let code2;
  let pos = start;
  const state = {
    // if `true`, this is a valid link title
    ok: false,
    // if `true`, this link can be continued on the next line
    can_continue: false,
    // if `ok`, it's the position of the first character after the closing marker
    pos: 0,
    // if `ok`, it's the unescaped title
    str: "",
    // expected closing marker character code
    marker: 0
  };
  if (prev_state) {
    state.str = prev_state.str;
    state.marker = prev_state.marker;
  } else {
    if (pos >= max) {
      return state;
    }
    let marker = str.charCodeAt(pos);
    if (marker !== 34 && marker !== 39 && marker !== 40) {
      return state;
    }
    start++;
    pos++;
    if (marker === 40) {
      marker = 41;
    }
    state.marker = marker;
  }
  while (pos < max) {
    code2 = str.charCodeAt(pos);
    if (code2 === state.marker) {
      state.pos = pos + 1;
      state.str += unescapeAll(str.slice(start, pos));
      state.ok = true;
      return state;
    } else if (code2 === 40 && state.marker === 41) {
      return state;
    } else if (code2 === 92 && pos + 1 < max) {
      pos++;
    }
    pos++;
  }
  state.can_continue = true;
  state.str += unescapeAll(str.slice(start, pos));
  return state;
}
const helpers = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  parseLinkDestination,
  parseLinkLabel,
  parseLinkTitle
}, Symbol.toStringTag, { value: "Module" }));
const default_rules = {};
default_rules.code_inline = function(tokens, idx, options, env, slf) {
  const token = tokens[idx];
  return "<code" + slf.renderAttrs(token) + ">" + escapeHtml(token.content) + "</code>";
};
default_rules.code_block = function(tokens, idx, options, env, slf) {
  const token = tokens[idx];
  return "<pre" + slf.renderAttrs(token) + "><code>" + escapeHtml(tokens[idx].content) + "</code></pre>\n";
};
default_rules.fence = function(tokens, idx, options, env, slf) {
  const token = tokens[idx];
  const info = token.info ? unescapeAll(token.info).trim() : "";
  let langName = "";
  let langAttrs = "";
  if (info) {
    const arr = info.split(/(\s+)/g);
    langName = arr[0];
    langAttrs = arr.slice(2).join("");
  }
  let highlighted;
  if (options.highlight) {
    highlighted = options.highlight(token.content, langName, langAttrs) || escapeHtml(token.content);
  } else {
    highlighted = escapeHtml(token.content);
  }
  if (highlighted.indexOf("<pre") === 0) {
    return highlighted + "\n";
  }
  if (info) {
    const i2 = token.attrIndex("class");
    const tmpAttrs = token.attrs ? token.attrs.slice() : [];
    if (i2 < 0) {
      tmpAttrs.push(["class", options.langPrefix + langName]);
    } else {
      tmpAttrs[i2] = tmpAttrs[i2].slice();
      tmpAttrs[i2][1] += " " + options.langPrefix + langName;
    }
    const tmpToken = {
      attrs: tmpAttrs
    };
    return `<pre><code${slf.renderAttrs(tmpToken)}>${highlighted}</code></pre>
`;
  }
  return `<pre><code${slf.renderAttrs(token)}>${highlighted}</code></pre>
`;
};
default_rules.image = function(tokens, idx, options, env, slf) {
  const token = tokens[idx];
  token.attrs[token.attrIndex("alt")][1] = slf.renderInlineAsText(token.children, options, env);
  return slf.renderToken(tokens, idx, options);
};
default_rules.hardbreak = function(tokens, idx, options) {
  return options.xhtmlOut ? "<br />\n" : "<br>\n";
};
default_rules.softbreak = function(tokens, idx, options) {
  return options.breaks ? options.xhtmlOut ? "<br />\n" : "<br>\n" : "\n";
};
default_rules.text = function(tokens, idx) {
  return escapeHtml(tokens[idx].content);
};
default_rules.html_block = function(tokens, idx) {
  return tokens[idx].content;
};
default_rules.html_inline = function(tokens, idx) {
  return tokens[idx].content;
};
function Renderer() {
  this.rules = assign$1({}, default_rules);
}
Renderer.prototype.renderAttrs = function renderAttrs(token) {
  let i2, l2, result2;
  if (!token.attrs) {
    return "";
  }
  result2 = "";
  for (i2 = 0, l2 = token.attrs.length; i2 < l2; i2++) {
    result2 += " " + escapeHtml(token.attrs[i2][0]) + '="' + escapeHtml(token.attrs[i2][1]) + '"';
  }
  return result2;
};
Renderer.prototype.renderToken = function renderToken(tokens, idx, options) {
  const token = tokens[idx];
  let result2 = "";
  if (token.hidden) {
    return "";
  }
  if (token.block && token.nesting !== -1 && idx && tokens[idx - 1].hidden) {
    result2 += "\n";
  }
  result2 += (token.nesting === -1 ? "</" : "<") + token.tag;
  result2 += this.renderAttrs(token);
  if (token.nesting === 0 && options.xhtmlOut) {
    result2 += " /";
  }
  let needLf = false;
  if (token.block) {
    needLf = true;
    if (token.nesting === 1) {
      if (idx + 1 < tokens.length) {
        const nextToken = tokens[idx + 1];
        if (nextToken.type === "inline" || nextToken.hidden) {
          needLf = false;
        } else if (nextToken.nesting === -1 && nextToken.tag === token.tag) {
          needLf = false;
        }
      }
    }
  }
  result2 += needLf ? ">\n" : ">";
  return result2;
};
Renderer.prototype.renderInline = function(tokens, options, env) {
  let result2 = "";
  const rules = this.rules;
  for (let i2 = 0, len = tokens.length; i2 < len; i2++) {
    const type = tokens[i2].type;
    if (typeof rules[type] !== "undefined") {
      result2 += rules[type](tokens, i2, options, env, this);
    } else {
      result2 += this.renderToken(tokens, i2, options);
    }
  }
  return result2;
};
Renderer.prototype.renderInlineAsText = function(tokens, options, env) {
  let result2 = "";
  for (let i2 = 0, len = tokens.length; i2 < len; i2++) {
    switch (tokens[i2].type) {
      case "text":
        result2 += tokens[i2].content;
        break;
      case "image":
        result2 += this.renderInlineAsText(tokens[i2].children, options, env);
        break;
      case "html_inline":
      case "html_block":
        result2 += tokens[i2].content;
        break;
      case "softbreak":
      case "hardbreak":
        result2 += "\n";
        break;
    }
  }
  return result2;
};
Renderer.prototype.render = function(tokens, options, env) {
  let result2 = "";
  const rules = this.rules;
  for (let i2 = 0, len = tokens.length; i2 < len; i2++) {
    const type = tokens[i2].type;
    if (type === "inline") {
      result2 += this.renderInline(tokens[i2].children, options, env);
    } else if (typeof rules[type] !== "undefined") {
      result2 += rules[type](tokens, i2, options, env, this);
    } else {
      result2 += this.renderToken(tokens, i2, options, env);
    }
  }
  return result2;
};
function Ruler() {
  this.__rules__ = [];
  this.__cache__ = null;
}
Ruler.prototype.__find__ = function(name) {
  for (let i2 = 0; i2 < this.__rules__.length; i2++) {
    if (this.__rules__[i2].name === name) {
      return i2;
    }
  }
  return -1;
};
Ruler.prototype.__compile__ = function() {
  const self = this;
  const chains = [""];
  self.__rules__.forEach(function(rule) {
    if (!rule.enabled) {
      return;
    }
    rule.alt.forEach(function(altName) {
      if (chains.indexOf(altName) < 0) {
        chains.push(altName);
      }
    });
  });
  self.__cache__ = {};
  chains.forEach(function(chain) {
    self.__cache__[chain] = [];
    self.__rules__.forEach(function(rule) {
      if (!rule.enabled) {
        return;
      }
      if (chain && rule.alt.indexOf(chain) < 0) {
        return;
      }
      self.__cache__[chain].push(rule.fn);
    });
  });
};
Ruler.prototype.at = function(name, fn2, options) {
  const index = this.__find__(name);
  const opt = options || {};
  if (index === -1) {
    throw new Error("Parser rule not found: " + name);
  }
  this.__rules__[index].fn = fn2;
  this.__rules__[index].alt = opt.alt || [];
  this.__cache__ = null;
};
Ruler.prototype.before = function(beforeName, ruleName, fn2, options) {
  const index = this.__find__(beforeName);
  const opt = options || {};
  if (index === -1) {
    throw new Error("Parser rule not found: " + beforeName);
  }
  this.__rules__.splice(index, 0, {
    name: ruleName,
    enabled: true,
    fn: fn2,
    alt: opt.alt || []
  });
  this.__cache__ = null;
};
Ruler.prototype.after = function(afterName, ruleName, fn2, options) {
  const index = this.__find__(afterName);
  const opt = options || {};
  if (index === -1) {
    throw new Error("Parser rule not found: " + afterName);
  }
  this.__rules__.splice(index + 1, 0, {
    name: ruleName,
    enabled: true,
    fn: fn2,
    alt: opt.alt || []
  });
  this.__cache__ = null;
};
Ruler.prototype.push = function(ruleName, fn2, options) {
  const opt = options || {};
  this.__rules__.push({
    name: ruleName,
    enabled: true,
    fn: fn2,
    alt: opt.alt || []
  });
  this.__cache__ = null;
};
Ruler.prototype.enable = function(list2, ignoreInvalid) {
  if (!Array.isArray(list2)) {
    list2 = [list2];
  }
  const result2 = [];
  list2.forEach(function(name) {
    const idx = this.__find__(name);
    if (idx < 0) {
      if (ignoreInvalid) {
        return;
      }
      throw new Error("Rules manager: invalid rule name " + name);
    }
    this.__rules__[idx].enabled = true;
    result2.push(name);
  }, this);
  this.__cache__ = null;
  return result2;
};
Ruler.prototype.enableOnly = function(list2, ignoreInvalid) {
  if (!Array.isArray(list2)) {
    list2 = [list2];
  }
  this.__rules__.forEach(function(rule) {
    rule.enabled = false;
  });
  this.enable(list2, ignoreInvalid);
};
Ruler.prototype.disable = function(list2, ignoreInvalid) {
  if (!Array.isArray(list2)) {
    list2 = [list2];
  }
  const result2 = [];
  list2.forEach(function(name) {
    const idx = this.__find__(name);
    if (idx < 0) {
      if (ignoreInvalid) {
        return;
      }
      throw new Error("Rules manager: invalid rule name " + name);
    }
    this.__rules__[idx].enabled = false;
    result2.push(name);
  }, this);
  this.__cache__ = null;
  return result2;
};
Ruler.prototype.getRules = function(chainName) {
  if (this.__cache__ === null) {
    this.__compile__();
  }
  return this.__cache__[chainName] || [];
};
function Token(type, tag, nesting) {
  this.type = type;
  this.tag = tag;
  this.attrs = null;
  this.map = null;
  this.nesting = nesting;
  this.level = 0;
  this.children = null;
  this.content = "";
  this.markup = "";
  this.info = "";
  this.meta = null;
  this.block = false;
  this.hidden = false;
}
Token.prototype.attrIndex = function attrIndex(name) {
  if (!this.attrs) {
    return -1;
  }
  const attrs = this.attrs;
  for (let i2 = 0, len = attrs.length; i2 < len; i2++) {
    if (attrs[i2][0] === name) {
      return i2;
    }
  }
  return -1;
};
Token.prototype.attrPush = function attrPush(attrData) {
  if (this.attrs) {
    this.attrs.push(attrData);
  } else {
    this.attrs = [attrData];
  }
};
Token.prototype.attrSet = function attrSet(name, value2) {
  const idx = this.attrIndex(name);
  const attrData = [name, value2];
  if (idx < 0) {
    this.attrPush(attrData);
  } else {
    this.attrs[idx] = attrData;
  }
};
Token.prototype.attrGet = function attrGet(name) {
  const idx = this.attrIndex(name);
  let value2 = null;
  if (idx >= 0) {
    value2 = this.attrs[idx][1];
  }
  return value2;
};
Token.prototype.attrJoin = function attrJoin(name, value2) {
  const idx = this.attrIndex(name);
  if (idx < 0) {
    this.attrPush([name, value2]);
  } else {
    this.attrs[idx][1] = this.attrs[idx][1] + " " + value2;
  }
};
function StateCore(src, md, env) {
  this.src = src;
  this.env = env;
  this.tokens = [];
  this.inlineMode = false;
  this.md = md;
}
StateCore.prototype.Token = Token;
const NEWLINES_RE = /\r\n?|\n/g;
const NULL_RE = /\0/g;
function normalize(state) {
  let str;
  str = state.src.replace(NEWLINES_RE, "\n");
  str = str.replace(NULL_RE, "�");
  state.src = str;
}
function block(state) {
  let token;
  if (state.inlineMode) {
    token = new state.Token("inline", "", 0);
    token.content = state.src;
    token.map = [0, 1];
    token.children = [];
    state.tokens.push(token);
  } else {
    state.md.block.parse(state.src, state.md, state.env, state.tokens);
  }
}
function inline(state) {
  const tokens = state.tokens;
  for (let i2 = 0, l2 = tokens.length; i2 < l2; i2++) {
    const tok = tokens[i2];
    if (tok.type === "inline") {
      state.md.inline.parse(tok.content, state.md, state.env, tok.children);
    }
  }
}
function isLinkOpen$1(str) {
  return /^<a[>\s]/i.test(str);
}
function isLinkClose$1(str) {
  return /^<\/a\s*>/i.test(str);
}
function linkify$1(state) {
  const blockTokens = state.tokens;
  if (!state.md.options.linkify) {
    return;
  }
  for (let j = 0, l2 = blockTokens.length; j < l2; j++) {
    if (blockTokens[j].type !== "inline" || !state.md.linkify.pretest(blockTokens[j].content)) {
      continue;
    }
    let tokens = blockTokens[j].children;
    let htmlLinkLevel = 0;
    for (let i2 = tokens.length - 1; i2 >= 0; i2--) {
      const currentToken = tokens[i2];
      if (currentToken.type === "link_close") {
        i2--;
        while (tokens[i2].level !== currentToken.level && tokens[i2].type !== "link_open") {
          i2--;
        }
        continue;
      }
      if (currentToken.type === "html_inline") {
        if (isLinkOpen$1(currentToken.content) && htmlLinkLevel > 0) {
          htmlLinkLevel--;
        }
        if (isLinkClose$1(currentToken.content)) {
          htmlLinkLevel++;
        }
      }
      if (htmlLinkLevel > 0) {
        continue;
      }
      if (currentToken.type === "text" && state.md.linkify.test(currentToken.content)) {
        const text2 = currentToken.content;
        let links = state.md.linkify.match(text2);
        const nodes = [];
        let level = currentToken.level;
        let lastPos = 0;
        if (links.length > 0 && links[0].index === 0 && i2 > 0 && tokens[i2 - 1].type === "text_special") {
          links = links.slice(1);
        }
        for (let ln = 0; ln < links.length; ln++) {
          const url = links[ln].url;
          const fullUrl = state.md.normalizeLink(url);
          if (!state.md.validateLink(fullUrl)) {
            continue;
          }
          let urlText = links[ln].text;
          if (!links[ln].schema) {
            urlText = state.md.normalizeLinkText("http://" + urlText).replace(/^http:\/\//, "");
          } else if (links[ln].schema === "mailto:" && !/^mailto:/i.test(urlText)) {
            urlText = state.md.normalizeLinkText("mailto:" + urlText).replace(/^mailto:/, "");
          } else {
            urlText = state.md.normalizeLinkText(urlText);
          }
          const pos = links[ln].index;
          if (pos > lastPos) {
            const token = new state.Token("text", "", 0);
            token.content = text2.slice(lastPos, pos);
            token.level = level;
            nodes.push(token);
          }
          const token_o = new state.Token("link_open", "a", 1);
          token_o.attrs = [["href", fullUrl]];
          token_o.level = level++;
          token_o.markup = "linkify";
          token_o.info = "auto";
          nodes.push(token_o);
          const token_t = new state.Token("text", "", 0);
          token_t.content = urlText;
          token_t.level = level;
          nodes.push(token_t);
          const token_c = new state.Token("link_close", "a", -1);
          token_c.level = --level;
          token_c.markup = "linkify";
          token_c.info = "auto";
          nodes.push(token_c);
          lastPos = links[ln].lastIndex;
        }
        if (lastPos < text2.length) {
          const token = new state.Token("text", "", 0);
          token.content = text2.slice(lastPos);
          token.level = level;
          nodes.push(token);
        }
        blockTokens[j].children = tokens = arrayReplaceAt(tokens, i2, nodes);
      }
    }
  }
}
const RARE_RE = /\+-|\.\.|\?\?\?\?|!!!!|,,|--/;
const SCOPED_ABBR_TEST_RE = /\((c|tm|r)\)/i;
const SCOPED_ABBR_RE = /\((c|tm|r)\)/ig;
const SCOPED_ABBR = {
  c: "©",
  r: "®",
  tm: "™"
};
function replaceFn(match2, name) {
  return SCOPED_ABBR[name.toLowerCase()];
}
function replace_scoped(inlineTokens) {
  let inside_autolink = 0;
  for (let i2 = inlineTokens.length - 1; i2 >= 0; i2--) {
    const token = inlineTokens[i2];
    if (token.type === "text" && !inside_autolink) {
      token.content = token.content.replace(SCOPED_ABBR_RE, replaceFn);
    }
    if (token.type === "link_open" && token.info === "auto") {
      inside_autolink--;
    }
    if (token.type === "link_close" && token.info === "auto") {
      inside_autolink++;
    }
  }
}
function replace_rare(inlineTokens) {
  let inside_autolink = 0;
  for (let i2 = inlineTokens.length - 1; i2 >= 0; i2--) {
    const token = inlineTokens[i2];
    if (token.type === "text" && !inside_autolink) {
      if (RARE_RE.test(token.content)) {
        token.content = token.content.replace(/\+-/g, "±").replace(/\.{2,}/g, "…").replace(/([?!])…/g, "$1..").replace(/([?!]){4,}/g, "$1$1$1").replace(/,{2,}/g, ",").replace(/(^|[^-])---(?=[^-]|$)/mg, "$1—").replace(/(^|\s)--(?=\s|$)/mg, "$1–").replace(/(^|[^-\s])--(?=[^-\s]|$)/mg, "$1–");
      }
    }
    if (token.type === "link_open" && token.info === "auto") {
      inside_autolink--;
    }
    if (token.type === "link_close" && token.info === "auto") {
      inside_autolink++;
    }
  }
}
function replace(state) {
  let blkIdx;
  if (!state.md.options.typographer) {
    return;
  }
  for (blkIdx = state.tokens.length - 1; blkIdx >= 0; blkIdx--) {
    if (state.tokens[blkIdx].type !== "inline") {
      continue;
    }
    if (SCOPED_ABBR_TEST_RE.test(state.tokens[blkIdx].content)) {
      replace_scoped(state.tokens[blkIdx].children);
    }
    if (RARE_RE.test(state.tokens[blkIdx].content)) {
      replace_rare(state.tokens[blkIdx].children);
    }
  }
}
const QUOTE_TEST_RE = /['"]/;
const QUOTE_RE = /['"]/g;
const APOSTROPHE = "’";
function replaceAt(str, index, ch) {
  return str.slice(0, index) + ch + str.slice(index + 1);
}
function process_inlines(tokens, state) {
  let j;
  const stack = [];
  for (let i2 = 0; i2 < tokens.length; i2++) {
    const token = tokens[i2];
    const thisLevel = tokens[i2].level;
    for (j = stack.length - 1; j >= 0; j--) {
      if (stack[j].level <= thisLevel) {
        break;
      }
    }
    stack.length = j + 1;
    if (token.type !== "text") {
      continue;
    }
    let text2 = token.content;
    let pos = 0;
    let max = text2.length;
    OUTER:
      while (pos < max) {
        QUOTE_RE.lastIndex = pos;
        const t2 = QUOTE_RE.exec(text2);
        if (!t2) {
          break;
        }
        let canOpen = true;
        let canClose = true;
        pos = t2.index + 1;
        const isSingle = t2[0] === "'";
        let lastChar = 32;
        if (t2.index - 1 >= 0) {
          lastChar = text2.charCodeAt(t2.index - 1);
        } else {
          for (j = i2 - 1; j >= 0; j--) {
            if (tokens[j].type === "softbreak" || tokens[j].type === "hardbreak") break;
            if (!tokens[j].content) continue;
            lastChar = tokens[j].content.charCodeAt(tokens[j].content.length - 1);
            break;
          }
        }
        let nextChar = 32;
        if (pos < max) {
          nextChar = text2.charCodeAt(pos);
        } else {
          for (j = i2 + 1; j < tokens.length; j++) {
            if (tokens[j].type === "softbreak" || tokens[j].type === "hardbreak") break;
            if (!tokens[j].content) continue;
            nextChar = tokens[j].content.charCodeAt(0);
            break;
          }
        }
        const isLastPunctChar = isMdAsciiPunct(lastChar) || isPunctChar(String.fromCharCode(lastChar));
        const isNextPunctChar = isMdAsciiPunct(nextChar) || isPunctChar(String.fromCharCode(nextChar));
        const isLastWhiteSpace = isWhiteSpace(lastChar);
        const isNextWhiteSpace = isWhiteSpace(nextChar);
        if (isNextWhiteSpace) {
          canOpen = false;
        } else if (isNextPunctChar) {
          if (!(isLastWhiteSpace || isLastPunctChar)) {
            canOpen = false;
          }
        }
        if (isLastWhiteSpace) {
          canClose = false;
        } else if (isLastPunctChar) {
          if (!(isNextWhiteSpace || isNextPunctChar)) {
            canClose = false;
          }
        }
        if (nextChar === 34 && t2[0] === '"') {
          if (lastChar >= 48 && lastChar <= 57) {
            canClose = canOpen = false;
          }
        }
        if (canOpen && canClose) {
          canOpen = isLastPunctChar;
          canClose = isNextPunctChar;
        }
        if (!canOpen && !canClose) {
          if (isSingle) {
            token.content = replaceAt(token.content, t2.index, APOSTROPHE);
          }
          continue;
        }
        if (canClose) {
          for (j = stack.length - 1; j >= 0; j--) {
            let item = stack[j];
            if (stack[j].level < thisLevel) {
              break;
            }
            if (item.single === isSingle && stack[j].level === thisLevel) {
              item = stack[j];
              let openQuote;
              let closeQuote;
              if (isSingle) {
                openQuote = state.md.options.quotes[2];
                closeQuote = state.md.options.quotes[3];
              } else {
                openQuote = state.md.options.quotes[0];
                closeQuote = state.md.options.quotes[1];
              }
              token.content = replaceAt(token.content, t2.index, closeQuote);
              tokens[item.token].content = replaceAt(
                tokens[item.token].content,
                item.pos,
                openQuote
              );
              pos += closeQuote.length - 1;
              if (item.token === i2) {
                pos += openQuote.length - 1;
              }
              text2 = token.content;
              max = text2.length;
              stack.length = j;
              continue OUTER;
            }
          }
        }
        if (canOpen) {
          stack.push({
            token: i2,
            pos: t2.index,
            single: isSingle,
            level: thisLevel
          });
        } else if (canClose && isSingle) {
          token.content = replaceAt(token.content, t2.index, APOSTROPHE);
        }
      }
  }
}
function smartquotes(state) {
  if (!state.md.options.typographer) {
    return;
  }
  for (let blkIdx = state.tokens.length - 1; blkIdx >= 0; blkIdx--) {
    if (state.tokens[blkIdx].type !== "inline" || !QUOTE_TEST_RE.test(state.tokens[blkIdx].content)) {
      continue;
    }
    process_inlines(state.tokens[blkIdx].children, state);
  }
}
function text_join(state) {
  let curr, last2;
  const blockTokens = state.tokens;
  const l2 = blockTokens.length;
  for (let j = 0; j < l2; j++) {
    if (blockTokens[j].type !== "inline") continue;
    const tokens = blockTokens[j].children;
    const max = tokens.length;
    for (curr = 0; curr < max; curr++) {
      if (tokens[curr].type === "text_special") {
        tokens[curr].type = "text";
      }
    }
    for (curr = last2 = 0; curr < max; curr++) {
      if (tokens[curr].type === "text" && curr + 1 < max && tokens[curr + 1].type === "text") {
        tokens[curr + 1].content = tokens[curr].content + tokens[curr + 1].content;
      } else {
        if (curr !== last2) {
          tokens[last2] = tokens[curr];
        }
        last2++;
      }
    }
    if (curr !== last2) {
      tokens.length = last2;
    }
  }
}
const _rules$2 = [
  ["normalize", normalize],
  ["block", block],
  ["inline", inline],
  ["linkify", linkify$1],
  ["replacements", replace],
  ["smartquotes", smartquotes],
  // `text_join` finds `text_special` tokens (for escape sequences)
  // and joins them with the rest of the text
  ["text_join", text_join]
];
function Core$1() {
  this.ruler = new Ruler();
  for (let i2 = 0; i2 < _rules$2.length; i2++) {
    this.ruler.push(_rules$2[i2][0], _rules$2[i2][1]);
  }
}
Core$1.prototype.process = function(state) {
  const rules = this.ruler.getRules("");
  for (let i2 = 0, l2 = rules.length; i2 < l2; i2++) {
    rules[i2](state);
  }
};
Core$1.prototype.State = StateCore;
function StateBlock(src, md, env, tokens) {
  this.src = src;
  this.md = md;
  this.env = env;
  this.tokens = tokens;
  this.bMarks = [];
  this.eMarks = [];
  this.tShift = [];
  this.sCount = [];
  this.bsCount = [];
  this.blkIndent = 0;
  this.line = 0;
  this.lineMax = 0;
  this.tight = false;
  this.ddIndent = -1;
  this.listIndent = -1;
  this.parentType = "root";
  this.level = 0;
  const s = this.src;
  for (let start = 0, pos = 0, indent = 0, offset = 0, len = s.length, indent_found = false; pos < len; pos++) {
    const ch = s.charCodeAt(pos);
    if (!indent_found) {
      if (isSpace(ch)) {
        indent++;
        if (ch === 9) {
          offset += 4 - offset % 4;
        } else {
          offset++;
        }
        continue;
      } else {
        indent_found = true;
      }
    }
    if (ch === 10 || pos === len - 1) {
      if (ch !== 10) {
        pos++;
      }
      this.bMarks.push(start);
      this.eMarks.push(pos);
      this.tShift.push(indent);
      this.sCount.push(offset);
      this.bsCount.push(0);
      indent_found = false;
      indent = 0;
      offset = 0;
      start = pos + 1;
    }
  }
  this.bMarks.push(s.length);
  this.eMarks.push(s.length);
  this.tShift.push(0);
  this.sCount.push(0);
  this.bsCount.push(0);
  this.lineMax = this.bMarks.length - 1;
}
StateBlock.prototype.push = function(type, tag, nesting) {
  const token = new Token(type, tag, nesting);
  token.block = true;
  if (nesting < 0) this.level--;
  token.level = this.level;
  if (nesting > 0) this.level++;
  this.tokens.push(token);
  return token;
};
StateBlock.prototype.isEmpty = function isEmpty(line) {
  return this.bMarks[line] + this.tShift[line] >= this.eMarks[line];
};
StateBlock.prototype.skipEmptyLines = function skipEmptyLines(from) {
  for (let max = this.lineMax; from < max; from++) {
    if (this.bMarks[from] + this.tShift[from] < this.eMarks[from]) {
      break;
    }
  }
  return from;
};
StateBlock.prototype.skipSpaces = function skipSpaces(pos) {
  for (let max = this.src.length; pos < max; pos++) {
    const ch = this.src.charCodeAt(pos);
    if (!isSpace(ch)) {
      break;
    }
  }
  return pos;
};
StateBlock.prototype.skipSpacesBack = function skipSpacesBack(pos, min) {
  if (pos <= min) {
    return pos;
  }
  while (pos > min) {
    if (!isSpace(this.src.charCodeAt(--pos))) {
      return pos + 1;
    }
  }
  return pos;
};
StateBlock.prototype.skipChars = function skipChars(pos, code2) {
  for (let max = this.src.length; pos < max; pos++) {
    if (this.src.charCodeAt(pos) !== code2) {
      break;
    }
  }
  return pos;
};
StateBlock.prototype.skipCharsBack = function skipCharsBack(pos, code2, min) {
  if (pos <= min) {
    return pos;
  }
  while (pos > min) {
    if (code2 !== this.src.charCodeAt(--pos)) {
      return pos + 1;
    }
  }
  return pos;
};
StateBlock.prototype.getLines = function getLines(begin, end, indent, keepLastLF) {
  if (begin >= end) {
    return "";
  }
  const queue = new Array(end - begin);
  for (let i2 = 0, line = begin; line < end; line++, i2++) {
    let lineIndent = 0;
    const lineStart = this.bMarks[line];
    let first2 = lineStart;
    let last2;
    if (line + 1 < end || keepLastLF) {
      last2 = this.eMarks[line] + 1;
    } else {
      last2 = this.eMarks[line];
    }
    while (first2 < last2 && lineIndent < indent) {
      const ch = this.src.charCodeAt(first2);
      if (isSpace(ch)) {
        if (ch === 9) {
          lineIndent += 4 - (lineIndent + this.bsCount[line]) % 4;
        } else {
          lineIndent++;
        }
      } else if (first2 - lineStart < this.tShift[line]) {
        lineIndent++;
      } else {
        break;
      }
      first2++;
    }
    if (lineIndent > indent) {
      queue[i2] = new Array(lineIndent - indent + 1).join(" ") + this.src.slice(first2, last2);
    } else {
      queue[i2] = this.src.slice(first2, last2);
    }
  }
  return queue.join("");
};
StateBlock.prototype.Token = Token;
const MAX_AUTOCOMPLETED_CELLS = 65536;
function getLine(state, line) {
  const pos = state.bMarks[line] + state.tShift[line];
  const max = state.eMarks[line];
  return state.src.slice(pos, max);
}
function escapedSplit(str) {
  const result2 = [];
  const max = str.length;
  let pos = 0;
  let ch = str.charCodeAt(pos);
  let isEscaped = false;
  let lastPos = 0;
  let current = "";
  while (pos < max) {
    if (ch === 124) {
      if (!isEscaped) {
        result2.push(current + str.substring(lastPos, pos));
        current = "";
        lastPos = pos + 1;
      } else {
        current += str.substring(lastPos, pos - 1);
        lastPos = pos;
      }
    }
    isEscaped = ch === 92;
    pos++;
    ch = str.charCodeAt(pos);
  }
  result2.push(current + str.substring(lastPos));
  return result2;
}
function table(state, startLine, endLine, silent) {
  if (startLine + 2 > endLine) {
    return false;
  }
  let nextLine = startLine + 1;
  if (state.sCount[nextLine] < state.blkIndent) {
    return false;
  }
  if (state.sCount[nextLine] - state.blkIndent >= 4) {
    return false;
  }
  let pos = state.bMarks[nextLine] + state.tShift[nextLine];
  if (pos >= state.eMarks[nextLine]) {
    return false;
  }
  const firstCh = state.src.charCodeAt(pos++);
  if (firstCh !== 124 && firstCh !== 45 && firstCh !== 58) {
    return false;
  }
  if (pos >= state.eMarks[nextLine]) {
    return false;
  }
  const secondCh = state.src.charCodeAt(pos++);
  if (secondCh !== 124 && secondCh !== 45 && secondCh !== 58 && !isSpace(secondCh)) {
    return false;
  }
  if (firstCh === 45 && isSpace(secondCh)) {
    return false;
  }
  while (pos < state.eMarks[nextLine]) {
    const ch = state.src.charCodeAt(pos);
    if (ch !== 124 && ch !== 45 && ch !== 58 && !isSpace(ch)) {
      return false;
    }
    pos++;
  }
  let lineText = getLine(state, startLine + 1);
  let columns = lineText.split("|");
  const aligns = [];
  for (let i2 = 0; i2 < columns.length; i2++) {
    const t2 = columns[i2].trim();
    if (!t2) {
      if (i2 === 0 || i2 === columns.length - 1) {
        continue;
      } else {
        return false;
      }
    }
    if (!/^:?-+:?$/.test(t2)) {
      return false;
    }
    if (t2.charCodeAt(t2.length - 1) === 58) {
      aligns.push(t2.charCodeAt(0) === 58 ? "center" : "right");
    } else if (t2.charCodeAt(0) === 58) {
      aligns.push("left");
    } else {
      aligns.push("");
    }
  }
  lineText = getLine(state, startLine).trim();
  if (lineText.indexOf("|") === -1) {
    return false;
  }
  if (state.sCount[startLine] - state.blkIndent >= 4) {
    return false;
  }
  columns = escapedSplit(lineText);
  if (columns.length && columns[0] === "") columns.shift();
  if (columns.length && columns[columns.length - 1] === "") columns.pop();
  const columnCount = columns.length;
  if (columnCount === 0 || columnCount !== aligns.length) {
    return false;
  }
  if (silent) {
    return true;
  }
  const oldParentType = state.parentType;
  state.parentType = "table";
  const terminatorRules = state.md.block.ruler.getRules("blockquote");
  const token_to = state.push("table_open", "table", 1);
  const tableLines = [startLine, 0];
  token_to.map = tableLines;
  const token_tho = state.push("thead_open", "thead", 1);
  token_tho.map = [startLine, startLine + 1];
  const token_htro = state.push("tr_open", "tr", 1);
  token_htro.map = [startLine, startLine + 1];
  for (let i2 = 0; i2 < columns.length; i2++) {
    const token_ho = state.push("th_open", "th", 1);
    if (aligns[i2]) {
      token_ho.attrs = [["style", "text-align:" + aligns[i2]]];
    }
    const token_il = state.push("inline", "", 0);
    token_il.content = columns[i2].trim();
    token_il.children = [];
    state.push("th_close", "th", -1);
  }
  state.push("tr_close", "tr", -1);
  state.push("thead_close", "thead", -1);
  let tbodyLines;
  let autocompletedCells = 0;
  for (nextLine = startLine + 2; nextLine < endLine; nextLine++) {
    if (state.sCount[nextLine] < state.blkIndent) {
      break;
    }
    let terminate = false;
    for (let i2 = 0, l2 = terminatorRules.length; i2 < l2; i2++) {
      if (terminatorRules[i2](state, nextLine, endLine, true)) {
        terminate = true;
        break;
      }
    }
    if (terminate) {
      break;
    }
    lineText = getLine(state, nextLine).trim();
    if (!lineText) {
      break;
    }
    if (state.sCount[nextLine] - state.blkIndent >= 4) {
      break;
    }
    columns = escapedSplit(lineText);
    if (columns.length && columns[0] === "") columns.shift();
    if (columns.length && columns[columns.length - 1] === "") columns.pop();
    autocompletedCells += columnCount - columns.length;
    if (autocompletedCells > MAX_AUTOCOMPLETED_CELLS) {
      break;
    }
    if (nextLine === startLine + 2) {
      const token_tbo = state.push("tbody_open", "tbody", 1);
      token_tbo.map = tbodyLines = [startLine + 2, 0];
    }
    const token_tro = state.push("tr_open", "tr", 1);
    token_tro.map = [nextLine, nextLine + 1];
    for (let i2 = 0; i2 < columnCount; i2++) {
      const token_tdo = state.push("td_open", "td", 1);
      if (aligns[i2]) {
        token_tdo.attrs = [["style", "text-align:" + aligns[i2]]];
      }
      const token_il = state.push("inline", "", 0);
      token_il.content = columns[i2] ? columns[i2].trim() : "";
      token_il.children = [];
      state.push("td_close", "td", -1);
    }
    state.push("tr_close", "tr", -1);
  }
  if (tbodyLines) {
    state.push("tbody_close", "tbody", -1);
    tbodyLines[1] = nextLine;
  }
  state.push("table_close", "table", -1);
  tableLines[1] = nextLine;
  state.parentType = oldParentType;
  state.line = nextLine;
  return true;
}
function code$3(state, startLine, endLine) {
  if (state.sCount[startLine] - state.blkIndent < 4) {
    return false;
  }
  let nextLine = startLine + 1;
  let last2 = nextLine;
  while (nextLine < endLine) {
    if (state.isEmpty(nextLine)) {
      nextLine++;
      continue;
    }
    if (state.sCount[nextLine] - state.blkIndent >= 4) {
      nextLine++;
      last2 = nextLine;
      continue;
    }
    break;
  }
  state.line = last2;
  const token = state.push("code_block", "code", 0);
  token.content = state.getLines(startLine, last2, 4 + state.blkIndent, false) + "\n";
  token.map = [startLine, state.line];
  return true;
}
function fence(state, startLine, endLine, silent) {
  let pos = state.bMarks[startLine] + state.tShift[startLine];
  let max = state.eMarks[startLine];
  if (state.sCount[startLine] - state.blkIndent >= 4) {
    return false;
  }
  if (pos + 3 > max) {
    return false;
  }
  const marker = state.src.charCodeAt(pos);
  if (marker !== 126 && marker !== 96) {
    return false;
  }
  let mem = pos;
  pos = state.skipChars(pos, marker);
  let len = pos - mem;
  if (len < 3) {
    return false;
  }
  const markup = state.src.slice(mem, pos);
  const params = state.src.slice(pos, max);
  if (marker === 96) {
    if (params.indexOf(String.fromCharCode(marker)) >= 0) {
      return false;
    }
  }
  if (silent) {
    return true;
  }
  let nextLine = startLine;
  let haveEndMarker = false;
  for (; ; ) {
    nextLine++;
    if (nextLine >= endLine) {
      break;
    }
    pos = mem = state.bMarks[nextLine] + state.tShift[nextLine];
    max = state.eMarks[nextLine];
    if (pos < max && state.sCount[nextLine] < state.blkIndent) {
      break;
    }
    if (state.src.charCodeAt(pos) !== marker) {
      continue;
    }
    if (state.sCount[nextLine] - state.blkIndent >= 4) {
      continue;
    }
    pos = state.skipChars(pos, marker);
    if (pos - mem < len) {
      continue;
    }
    pos = state.skipSpaces(pos);
    if (pos < max) {
      continue;
    }
    haveEndMarker = true;
    break;
  }
  len = state.sCount[startLine];
  state.line = nextLine + (haveEndMarker ? 1 : 0);
  const token = state.push("fence", "code", 0);
  token.info = params;
  token.content = state.getLines(startLine + 1, nextLine, len, true);
  token.markup = markup;
  token.map = [startLine, state.line];
  return true;
}
function blockquote(state, startLine, endLine, silent) {
  let pos = state.bMarks[startLine] + state.tShift[startLine];
  let max = state.eMarks[startLine];
  const oldLineMax = state.lineMax;
  if (state.sCount[startLine] - state.blkIndent >= 4) {
    return false;
  }
  if (state.src.charCodeAt(pos) !== 62) {
    return false;
  }
  if (silent) {
    return true;
  }
  const oldBMarks = [];
  const oldBSCount = [];
  const oldSCount = [];
  const oldTShift = [];
  const terminatorRules = state.md.block.ruler.getRules("blockquote");
  const oldParentType = state.parentType;
  state.parentType = "blockquote";
  let lastLineEmpty = false;
  let nextLine;
  for (nextLine = startLine; nextLine < endLine; nextLine++) {
    const isOutdented = state.sCount[nextLine] < state.blkIndent;
    pos = state.bMarks[nextLine] + state.tShift[nextLine];
    max = state.eMarks[nextLine];
    if (pos >= max) {
      break;
    }
    if (state.src.charCodeAt(pos++) === 62 && !isOutdented) {
      let initial = state.sCount[nextLine] + 1;
      let spaceAfterMarker;
      let adjustTab;
      if (state.src.charCodeAt(pos) === 32) {
        pos++;
        initial++;
        adjustTab = false;
        spaceAfterMarker = true;
      } else if (state.src.charCodeAt(pos) === 9) {
        spaceAfterMarker = true;
        if ((state.bsCount[nextLine] + initial) % 4 === 3) {
          pos++;
          initial++;
          adjustTab = false;
        } else {
          adjustTab = true;
        }
      } else {
        spaceAfterMarker = false;
      }
      let offset = initial;
      oldBMarks.push(state.bMarks[nextLine]);
      state.bMarks[nextLine] = pos;
      while (pos < max) {
        const ch = state.src.charCodeAt(pos);
        if (isSpace(ch)) {
          if (ch === 9) {
            offset += 4 - (offset + state.bsCount[nextLine] + (adjustTab ? 1 : 0)) % 4;
          } else {
            offset++;
          }
        } else {
          break;
        }
        pos++;
      }
      lastLineEmpty = pos >= max;
      oldBSCount.push(state.bsCount[nextLine]);
      state.bsCount[nextLine] = state.sCount[nextLine] + 1 + (spaceAfterMarker ? 1 : 0);
      oldSCount.push(state.sCount[nextLine]);
      state.sCount[nextLine] = offset - initial;
      oldTShift.push(state.tShift[nextLine]);
      state.tShift[nextLine] = pos - state.bMarks[nextLine];
      continue;
    }
    if (lastLineEmpty) {
      break;
    }
    let terminate = false;
    for (let i2 = 0, l2 = terminatorRules.length; i2 < l2; i2++) {
      if (terminatorRules[i2](state, nextLine, endLine, true)) {
        terminate = true;
        break;
      }
    }
    if (terminate) {
      state.lineMax = nextLine;
      if (state.blkIndent !== 0) {
        oldBMarks.push(state.bMarks[nextLine]);
        oldBSCount.push(state.bsCount[nextLine]);
        oldTShift.push(state.tShift[nextLine]);
        oldSCount.push(state.sCount[nextLine]);
        state.sCount[nextLine] -= state.blkIndent;
      }
      break;
    }
    oldBMarks.push(state.bMarks[nextLine]);
    oldBSCount.push(state.bsCount[nextLine]);
    oldTShift.push(state.tShift[nextLine]);
    oldSCount.push(state.sCount[nextLine]);
    state.sCount[nextLine] = -1;
  }
  const oldIndent = state.blkIndent;
  state.blkIndent = 0;
  const token_o = state.push("blockquote_open", "blockquote", 1);
  token_o.markup = ">";
  const lines = [startLine, 0];
  token_o.map = lines;
  state.md.block.tokenize(state, startLine, nextLine);
  const token_c = state.push("blockquote_close", "blockquote", -1);
  token_c.markup = ">";
  state.lineMax = oldLineMax;
  state.parentType = oldParentType;
  lines[1] = state.line;
  for (let i2 = 0; i2 < oldTShift.length; i2++) {
    state.bMarks[i2 + startLine] = oldBMarks[i2];
    state.tShift[i2 + startLine] = oldTShift[i2];
    state.sCount[i2 + startLine] = oldSCount[i2];
    state.bsCount[i2 + startLine] = oldBSCount[i2];
  }
  state.blkIndent = oldIndent;
  return true;
}
function hr(state, startLine, endLine, silent) {
  const max = state.eMarks[startLine];
  if (state.sCount[startLine] - state.blkIndent >= 4) {
    return false;
  }
  let pos = state.bMarks[startLine] + state.tShift[startLine];
  const marker = state.src.charCodeAt(pos++);
  if (marker !== 42 && marker !== 45 && marker !== 95) {
    return false;
  }
  let cnt = 1;
  while (pos < max) {
    const ch = state.src.charCodeAt(pos++);
    if (ch !== marker && !isSpace(ch)) {
      return false;
    }
    if (ch === marker) {
      cnt++;
    }
  }
  if (cnt < 3) {
    return false;
  }
  if (silent) {
    return true;
  }
  state.line = startLine + 1;
  const token = state.push("hr", "hr", 0);
  token.map = [startLine, state.line];
  token.markup = Array(cnt + 1).join(String.fromCharCode(marker));
  return true;
}
function skipBulletListMarker(state, startLine) {
  const max = state.eMarks[startLine];
  let pos = state.bMarks[startLine] + state.tShift[startLine];
  const marker = state.src.charCodeAt(pos++);
  if (marker !== 42 && marker !== 45 && marker !== 43) {
    return -1;
  }
  if (pos < max) {
    const ch = state.src.charCodeAt(pos);
    if (!isSpace(ch)) {
      return -1;
    }
  }
  return pos;
}
function skipOrderedListMarker(state, startLine) {
  const start = state.bMarks[startLine] + state.tShift[startLine];
  const max = state.eMarks[startLine];
  let pos = start;
  if (pos + 1 >= max) {
    return -1;
  }
  let ch = state.src.charCodeAt(pos++);
  if (ch < 48 || ch > 57) {
    return -1;
  }
  for (; ; ) {
    if (pos >= max) {
      return -1;
    }
    ch = state.src.charCodeAt(pos++);
    if (ch >= 48 && ch <= 57) {
      if (pos - start >= 10) {
        return -1;
      }
      continue;
    }
    if (ch === 41 || ch === 46) {
      break;
    }
    return -1;
  }
  if (pos < max) {
    ch = state.src.charCodeAt(pos);
    if (!isSpace(ch)) {
      return -1;
    }
  }
  return pos;
}
function markTightParagraphs(state, idx) {
  const level = state.level + 2;
  for (let i2 = idx + 2, l2 = state.tokens.length - 2; i2 < l2; i2++) {
    if (state.tokens[i2].level === level && state.tokens[i2].type === "paragraph_open") {
      state.tokens[i2 + 2].hidden = true;
      state.tokens[i2].hidden = true;
      i2 += 2;
    }
  }
}
function list(state, startLine, endLine, silent) {
  let max, pos, start, token;
  let nextLine = startLine;
  let tight = true;
  if (state.sCount[nextLine] - state.blkIndent >= 4) {
    return false;
  }
  if (state.listIndent >= 0 && state.sCount[nextLine] - state.listIndent >= 4 && state.sCount[nextLine] < state.blkIndent) {
    return false;
  }
  let isTerminatingParagraph = false;
  if (silent && state.parentType === "paragraph") {
    if (state.sCount[nextLine] >= state.blkIndent) {
      isTerminatingParagraph = true;
    }
  }
  let isOrdered;
  let markerValue;
  let posAfterMarker;
  if ((posAfterMarker = skipOrderedListMarker(state, nextLine)) >= 0) {
    isOrdered = true;
    start = state.bMarks[nextLine] + state.tShift[nextLine];
    markerValue = Number(state.src.slice(start, posAfterMarker - 1));
    if (isTerminatingParagraph && markerValue !== 1) return false;
  } else if ((posAfterMarker = skipBulletListMarker(state, nextLine)) >= 0) {
    isOrdered = false;
  } else {
    return false;
  }
  if (isTerminatingParagraph) {
    if (state.skipSpaces(posAfterMarker) >= state.eMarks[nextLine]) return false;
  }
  if (silent) {
    return true;
  }
  const markerCharCode = state.src.charCodeAt(posAfterMarker - 1);
  const listTokIdx = state.tokens.length;
  if (isOrdered) {
    token = state.push("ordered_list_open", "ol", 1);
    if (markerValue !== 1) {
      token.attrs = [["start", markerValue]];
    }
  } else {
    token = state.push("bullet_list_open", "ul", 1);
  }
  const listLines = [nextLine, 0];
  token.map = listLines;
  token.markup = String.fromCharCode(markerCharCode);
  let prevEmptyEnd = false;
  const terminatorRules = state.md.block.ruler.getRules("list");
  const oldParentType = state.parentType;
  state.parentType = "list";
  while (nextLine < endLine) {
    pos = posAfterMarker;
    max = state.eMarks[nextLine];
    const initial = state.sCount[nextLine] + posAfterMarker - (state.bMarks[nextLine] + state.tShift[nextLine]);
    let offset = initial;
    while (pos < max) {
      const ch = state.src.charCodeAt(pos);
      if (ch === 9) {
        offset += 4 - (offset + state.bsCount[nextLine]) % 4;
      } else if (ch === 32) {
        offset++;
      } else {
        break;
      }
      pos++;
    }
    const contentStart = pos;
    let indentAfterMarker;
    if (contentStart >= max) {
      indentAfterMarker = 1;
    } else {
      indentAfterMarker = offset - initial;
    }
    if (indentAfterMarker > 4) {
      indentAfterMarker = 1;
    }
    const indent = initial + indentAfterMarker;
    token = state.push("list_item_open", "li", 1);
    token.markup = String.fromCharCode(markerCharCode);
    const itemLines = [nextLine, 0];
    token.map = itemLines;
    if (isOrdered) {
      token.info = state.src.slice(start, posAfterMarker - 1);
    }
    const oldTight = state.tight;
    const oldTShift = state.tShift[nextLine];
    const oldSCount = state.sCount[nextLine];
    const oldListIndent = state.listIndent;
    state.listIndent = state.blkIndent;
    state.blkIndent = indent;
    state.tight = true;
    state.tShift[nextLine] = contentStart - state.bMarks[nextLine];
    state.sCount[nextLine] = offset;
    if (contentStart >= max && state.isEmpty(nextLine + 1)) {
      state.line = Math.min(state.line + 2, endLine);
    } else {
      state.md.block.tokenize(state, nextLine, endLine, true);
    }
    if (!state.tight || prevEmptyEnd) {
      tight = false;
    }
    prevEmptyEnd = state.line - nextLine > 1 && state.isEmpty(state.line - 1);
    state.blkIndent = state.listIndent;
    state.listIndent = oldListIndent;
    state.tShift[nextLine] = oldTShift;
    state.sCount[nextLine] = oldSCount;
    state.tight = oldTight;
    token = state.push("list_item_close", "li", -1);
    token.markup = String.fromCharCode(markerCharCode);
    nextLine = state.line;
    itemLines[1] = nextLine;
    if (nextLine >= endLine) {
      break;
    }
    if (state.sCount[nextLine] < state.blkIndent) {
      break;
    }
    if (state.sCount[nextLine] - state.blkIndent >= 4) {
      break;
    }
    let terminate = false;
    for (let i2 = 0, l2 = terminatorRules.length; i2 < l2; i2++) {
      if (terminatorRules[i2](state, nextLine, endLine, true)) {
        terminate = true;
        break;
      }
    }
    if (terminate) {
      break;
    }
    if (isOrdered) {
      posAfterMarker = skipOrderedListMarker(state, nextLine);
      if (posAfterMarker < 0) {
        break;
      }
      start = state.bMarks[nextLine] + state.tShift[nextLine];
    } else {
      posAfterMarker = skipBulletListMarker(state, nextLine);
      if (posAfterMarker < 0) {
        break;
      }
    }
    if (markerCharCode !== state.src.charCodeAt(posAfterMarker - 1)) {
      break;
    }
  }
  if (isOrdered) {
    token = state.push("ordered_list_close", "ol", -1);
  } else {
    token = state.push("bullet_list_close", "ul", -1);
  }
  token.markup = String.fromCharCode(markerCharCode);
  listLines[1] = nextLine;
  state.line = nextLine;
  state.parentType = oldParentType;
  if (tight) {
    markTightParagraphs(state, listTokIdx);
  }
  return true;
}
function reference(state, startLine, _endLine, silent) {
  let pos = state.bMarks[startLine] + state.tShift[startLine];
  let max = state.eMarks[startLine];
  let nextLine = startLine + 1;
  if (state.sCount[startLine] - state.blkIndent >= 4) {
    return false;
  }
  if (state.src.charCodeAt(pos) !== 91) {
    return false;
  }
  function getNextLine(nextLine2) {
    const endLine = state.lineMax;
    if (nextLine2 >= endLine || state.isEmpty(nextLine2)) {
      return null;
    }
    let isContinuation = false;
    if (state.sCount[nextLine2] - state.blkIndent > 3) {
      isContinuation = true;
    }
    if (state.sCount[nextLine2] < 0) {
      isContinuation = true;
    }
    if (!isContinuation) {
      const terminatorRules = state.md.block.ruler.getRules("reference");
      const oldParentType = state.parentType;
      state.parentType = "reference";
      let terminate = false;
      for (let i2 = 0, l2 = terminatorRules.length; i2 < l2; i2++) {
        if (terminatorRules[i2](state, nextLine2, endLine, true)) {
          terminate = true;
          break;
        }
      }
      state.parentType = oldParentType;
      if (terminate) {
        return null;
      }
    }
    const pos2 = state.bMarks[nextLine2] + state.tShift[nextLine2];
    const max2 = state.eMarks[nextLine2];
    return state.src.slice(pos2, max2 + 1);
  }
  let str = state.src.slice(pos, max + 1);
  max = str.length;
  let labelEnd = -1;
  for (pos = 1; pos < max; pos++) {
    const ch = str.charCodeAt(pos);
    if (ch === 91) {
      return false;
    } else if (ch === 93) {
      labelEnd = pos;
      break;
    } else if (ch === 10) {
      const lineContent = getNextLine(nextLine);
      if (lineContent !== null) {
        str += lineContent;
        max = str.length;
        nextLine++;
      }
    } else if (ch === 92) {
      pos++;
      if (pos < max && str.charCodeAt(pos) === 10) {
        const lineContent = getNextLine(nextLine);
        if (lineContent !== null) {
          str += lineContent;
          max = str.length;
          nextLine++;
        }
      }
    }
  }
  if (labelEnd < 0 || str.charCodeAt(labelEnd + 1) !== 58) {
    return false;
  }
  for (pos = labelEnd + 2; pos < max; pos++) {
    const ch = str.charCodeAt(pos);
    if (ch === 10) {
      const lineContent = getNextLine(nextLine);
      if (lineContent !== null) {
        str += lineContent;
        max = str.length;
        nextLine++;
      }
    } else if (isSpace(ch)) ;
    else {
      break;
    }
  }
  const destRes = state.md.helpers.parseLinkDestination(str, pos, max);
  if (!destRes.ok) {
    return false;
  }
  const href = state.md.normalizeLink(destRes.str);
  if (!state.md.validateLink(href)) {
    return false;
  }
  pos = destRes.pos;
  const destEndPos = pos;
  const destEndLineNo = nextLine;
  const start = pos;
  for (; pos < max; pos++) {
    const ch = str.charCodeAt(pos);
    if (ch === 10) {
      const lineContent = getNextLine(nextLine);
      if (lineContent !== null) {
        str += lineContent;
        max = str.length;
        nextLine++;
      }
    } else if (isSpace(ch)) ;
    else {
      break;
    }
  }
  let titleRes = state.md.helpers.parseLinkTitle(str, pos, max);
  while (titleRes.can_continue) {
    const lineContent = getNextLine(nextLine);
    if (lineContent === null) break;
    str += lineContent;
    pos = max;
    max = str.length;
    nextLine++;
    titleRes = state.md.helpers.parseLinkTitle(str, pos, max, titleRes);
  }
  let title2;
  if (pos < max && start !== pos && titleRes.ok) {
    title2 = titleRes.str;
    pos = titleRes.pos;
  } else {
    title2 = "";
    pos = destEndPos;
    nextLine = destEndLineNo;
  }
  while (pos < max) {
    const ch = str.charCodeAt(pos);
    if (!isSpace(ch)) {
      break;
    }
    pos++;
  }
  if (pos < max && str.charCodeAt(pos) !== 10) {
    if (title2) {
      title2 = "";
      pos = destEndPos;
      nextLine = destEndLineNo;
      while (pos < max) {
        const ch = str.charCodeAt(pos);
        if (!isSpace(ch)) {
          break;
        }
        pos++;
      }
    }
  }
  if (pos < max && str.charCodeAt(pos) !== 10) {
    return false;
  }
  const label2 = normalizeReference(str.slice(1, labelEnd));
  if (!label2) {
    return false;
  }
  if (silent) {
    return true;
  }
  if (typeof state.env.references === "undefined") {
    state.env.references = {};
  }
  if (typeof state.env.references[label2] === "undefined") {
    state.env.references[label2] = { title: title2, href };
  }
  state.line = nextLine;
  return true;
}
const block_names = [
  "address",
  "article",
  "aside",
  "base",
  "basefont",
  "blockquote",
  "body",
  "caption",
  "center",
  "col",
  "colgroup",
  "dd",
  "details",
  "dialog",
  "dir",
  "div",
  "dl",
  "dt",
  "fieldset",
  "figcaption",
  "figure",
  "footer",
  "form",
  "frame",
  "frameset",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "head",
  "header",
  "hr",
  "html",
  "iframe",
  "legend",
  "li",
  "link",
  "main",
  "menu",
  "menuitem",
  "nav",
  "noframes",
  "ol",
  "optgroup",
  "option",
  "p",
  "param",
  "search",
  "section",
  "summary",
  "table",
  "tbody",
  "td",
  "tfoot",
  "th",
  "thead",
  "title",
  "tr",
  "track",
  "ul"
];
const attr_name = "[a-zA-Z_:][a-zA-Z0-9:._-]*";
const unquoted = "[^\"'=<>`\\x00-\\x20]+";
const single_quoted = "'[^']*'";
const double_quoted = '"[^"]*"';
const attr_value = "(?:" + unquoted + "|" + single_quoted + "|" + double_quoted + ")";
const attribute = "(?:\\s+" + attr_name + "(?:\\s*=\\s*" + attr_value + ")?)";
const open_tag = "<[A-Za-z][A-Za-z0-9\\-]*" + attribute + "*\\s*\\/?>";
const close_tag = "<\\/[A-Za-z][A-Za-z0-9\\-]*\\s*>";
const comment = "<!---?>|<!--(?:[^-]|-[^-]|--[^>])*-->";
const processing = "<[?][\\s\\S]*?[?]>";
const declaration = "<![A-Za-z][^>]*>";
const cdata = "<!\\[CDATA\\[[\\s\\S]*?\\]\\]>";
const HTML_TAG_RE = new RegExp("^(?:" + open_tag + "|" + close_tag + "|" + comment + "|" + processing + "|" + declaration + "|" + cdata + ")");
const HTML_OPEN_CLOSE_TAG_RE = new RegExp("^(?:" + open_tag + "|" + close_tag + ")");
const HTML_SEQUENCES = [
  [/^<(script|pre|style|textarea)(?=(\s|>|$))/i, /<\/(script|pre|style|textarea)>/i, true],
  [/^<!--/, /-->/, true],
  [/^<\?/, /\?>/, true],
  [/^<![A-Z]/, />/, true],
  [/^<!\[CDATA\[/, /\]\]>/, true],
  [new RegExp("^</?(" + block_names.join("|") + ")(?=(\\s|/?>|$))", "i"), /^$/, true],
  [new RegExp(HTML_OPEN_CLOSE_TAG_RE.source + "\\s*$"), /^$/, false]
];
function html_block(state, startLine, endLine, silent) {
  let pos = state.bMarks[startLine] + state.tShift[startLine];
  let max = state.eMarks[startLine];
  if (state.sCount[startLine] - state.blkIndent >= 4) {
    return false;
  }
  if (!state.md.options.html) {
    return false;
  }
  if (state.src.charCodeAt(pos) !== 60) {
    return false;
  }
  let lineText = state.src.slice(pos, max);
  let i2 = 0;
  for (; i2 < HTML_SEQUENCES.length; i2++) {
    if (HTML_SEQUENCES[i2][0].test(lineText)) {
      break;
    }
  }
  if (i2 === HTML_SEQUENCES.length) {
    return false;
  }
  if (silent) {
    return HTML_SEQUENCES[i2][2];
  }
  let nextLine = startLine + 1;
  if (!HTML_SEQUENCES[i2][1].test(lineText)) {
    for (; nextLine < endLine; nextLine++) {
      if (state.sCount[nextLine] < state.blkIndent) {
        break;
      }
      pos = state.bMarks[nextLine] + state.tShift[nextLine];
      max = state.eMarks[nextLine];
      lineText = state.src.slice(pos, max);
      if (HTML_SEQUENCES[i2][1].test(lineText)) {
        if (lineText.length !== 0) {
          nextLine++;
        }
        break;
      }
    }
  }
  state.line = nextLine;
  const token = state.push("html_block", "", 0);
  token.map = [startLine, nextLine];
  token.content = state.getLines(startLine, nextLine, state.blkIndent, true);
  return true;
}
function heading(state, startLine, endLine, silent) {
  let pos = state.bMarks[startLine] + state.tShift[startLine];
  let max = state.eMarks[startLine];
  if (state.sCount[startLine] - state.blkIndent >= 4) {
    return false;
  }
  let ch = state.src.charCodeAt(pos);
  if (ch !== 35 || pos >= max) {
    return false;
  }
  let level = 1;
  ch = state.src.charCodeAt(++pos);
  while (ch === 35 && pos < max && level <= 6) {
    level++;
    ch = state.src.charCodeAt(++pos);
  }
  if (level > 6 || pos < max && !isSpace(ch)) {
    return false;
  }
  if (silent) {
    return true;
  }
  max = state.skipSpacesBack(max, pos);
  const tmp = state.skipCharsBack(max, 35, pos);
  if (tmp > pos && isSpace(state.src.charCodeAt(tmp - 1))) {
    max = tmp;
  }
  state.line = startLine + 1;
  const token_o = state.push("heading_open", "h" + String(level), 1);
  token_o.markup = "########".slice(0, level);
  token_o.map = [startLine, state.line];
  const token_i = state.push("inline", "", 0);
  token_i.content = state.src.slice(pos, max).trim();
  token_i.map = [startLine, state.line];
  token_i.children = [];
  const token_c = state.push("heading_close", "h" + String(level), -1);
  token_c.markup = "########".slice(0, level);
  return true;
}
function lheading(state, startLine, endLine) {
  const terminatorRules = state.md.block.ruler.getRules("paragraph");
  if (state.sCount[startLine] - state.blkIndent >= 4) {
    return false;
  }
  const oldParentType = state.parentType;
  state.parentType = "paragraph";
  let level = 0;
  let marker;
  let nextLine = startLine + 1;
  for (; nextLine < endLine && !state.isEmpty(nextLine); nextLine++) {
    if (state.sCount[nextLine] - state.blkIndent > 3) {
      continue;
    }
    if (state.sCount[nextLine] >= state.blkIndent) {
      let pos = state.bMarks[nextLine] + state.tShift[nextLine];
      const max = state.eMarks[nextLine];
      if (pos < max) {
        marker = state.src.charCodeAt(pos);
        if (marker === 45 || marker === 61) {
          pos = state.skipChars(pos, marker);
          pos = state.skipSpaces(pos);
          if (pos >= max) {
            level = marker === 61 ? 1 : 2;
            break;
          }
        }
      }
    }
    if (state.sCount[nextLine] < 0) {
      continue;
    }
    let terminate = false;
    for (let i2 = 0, l2 = terminatorRules.length; i2 < l2; i2++) {
      if (terminatorRules[i2](state, nextLine, endLine, true)) {
        terminate = true;
        break;
      }
    }
    if (terminate) {
      break;
    }
  }
  if (!level) {
    return false;
  }
  const content2 = state.getLines(startLine, nextLine, state.blkIndent, false).trim();
  state.line = nextLine + 1;
  const token_o = state.push("heading_open", "h" + String(level), 1);
  token_o.markup = String.fromCharCode(marker);
  token_o.map = [startLine, state.line];
  const token_i = state.push("inline", "", 0);
  token_i.content = content2;
  token_i.map = [startLine, state.line - 1];
  token_i.children = [];
  const token_c = state.push("heading_close", "h" + String(level), -1);
  token_c.markup = String.fromCharCode(marker);
  state.parentType = oldParentType;
  return true;
}
function paragraph(state, startLine, endLine) {
  const terminatorRules = state.md.block.ruler.getRules("paragraph");
  const oldParentType = state.parentType;
  let nextLine = startLine + 1;
  state.parentType = "paragraph";
  for (; nextLine < endLine && !state.isEmpty(nextLine); nextLine++) {
    if (state.sCount[nextLine] - state.blkIndent > 3) {
      continue;
    }
    if (state.sCount[nextLine] < 0) {
      continue;
    }
    let terminate = false;
    for (let i2 = 0, l2 = terminatorRules.length; i2 < l2; i2++) {
      if (terminatorRules[i2](state, nextLine, endLine, true)) {
        terminate = true;
        break;
      }
    }
    if (terminate) {
      break;
    }
  }
  const content2 = state.getLines(startLine, nextLine, state.blkIndent, false).trim();
  state.line = nextLine;
  const token_o = state.push("paragraph_open", "p", 1);
  token_o.map = [startLine, state.line];
  const token_i = state.push("inline", "", 0);
  token_i.content = content2;
  token_i.map = [startLine, state.line];
  token_i.children = [];
  state.push("paragraph_close", "p", -1);
  state.parentType = oldParentType;
  return true;
}
const _rules$1 = [
  // First 2 params - rule name & source. Secondary array - list of rules,
  // which can be terminated by this one.
  ["table", table, ["paragraph", "reference"]],
  ["code", code$3],
  ["fence", fence, ["paragraph", "reference", "blockquote", "list"]],
  ["blockquote", blockquote, ["paragraph", "reference", "blockquote", "list"]],
  ["hr", hr, ["paragraph", "reference", "blockquote", "list"]],
  ["list", list, ["paragraph", "reference", "blockquote"]],
  ["reference", reference],
  ["html_block", html_block, ["paragraph", "reference", "blockquote"]],
  ["heading", heading, ["paragraph", "reference", "blockquote"]],
  ["lheading", lheading],
  ["paragraph", paragraph]
];
function ParserBlock() {
  this.ruler = new Ruler();
  for (let i2 = 0; i2 < _rules$1.length; i2++) {
    this.ruler.push(_rules$1[i2][0], _rules$1[i2][1], { alt: (_rules$1[i2][2] || []).slice() });
  }
}
ParserBlock.prototype.tokenize = function(state, startLine, endLine) {
  const rules = this.ruler.getRules("");
  const len = rules.length;
  const maxNesting = state.md.options.maxNesting;
  let line = startLine;
  let hasEmptyLines = false;
  while (line < endLine) {
    state.line = line = state.skipEmptyLines(line);
    if (line >= endLine) {
      break;
    }
    if (state.sCount[line] < state.blkIndent) {
      break;
    }
    if (state.level >= maxNesting) {
      state.line = endLine;
      break;
    }
    const prevLine = state.line;
    let ok = false;
    for (let i2 = 0; i2 < len; i2++) {
      ok = rules[i2](state, line, endLine, false);
      if (ok) {
        if (prevLine >= state.line) {
          throw new Error("block rule didn't increment state.line");
        }
        break;
      }
    }
    if (!ok) throw new Error("none of the block rules matched");
    state.tight = !hasEmptyLines;
    if (state.isEmpty(state.line - 1)) {
      hasEmptyLines = true;
    }
    line = state.line;
    if (line < endLine && state.isEmpty(line)) {
      hasEmptyLines = true;
      line++;
      state.line = line;
    }
  }
};
ParserBlock.prototype.parse = function(src, md, env, outTokens) {
  if (!src) {
    return;
  }
  const state = new this.State(src, md, env, outTokens);
  this.tokenize(state, state.line, state.lineMax);
};
ParserBlock.prototype.State = StateBlock;
function StateInline(src, md, env, outTokens) {
  this.src = src;
  this.env = env;
  this.md = md;
  this.tokens = outTokens;
  this.tokens_meta = Array(outTokens.length);
  this.pos = 0;
  this.posMax = this.src.length;
  this.level = 0;
  this.pending = "";
  this.pendingLevel = 0;
  this.cache = {};
  this.delimiters = [];
  this._prev_delimiters = [];
  this.backticks = {};
  this.backticksScanned = false;
  this.linkLevel = 0;
}
StateInline.prototype.pushPending = function() {
  const token = new Token("text", "", 0);
  token.content = this.pending;
  token.level = this.pendingLevel;
  this.tokens.push(token);
  this.pending = "";
  return token;
};
StateInline.prototype.push = function(type, tag, nesting) {
  if (this.pending) {
    this.pushPending();
  }
  const token = new Token(type, tag, nesting);
  let token_meta = null;
  if (nesting < 0) {
    this.level--;
    this.delimiters = this._prev_delimiters.pop();
  }
  token.level = this.level;
  if (nesting > 0) {
    this.level++;
    this._prev_delimiters.push(this.delimiters);
    this.delimiters = [];
    token_meta = { delimiters: this.delimiters };
  }
  this.pendingLevel = this.level;
  this.tokens.push(token);
  this.tokens_meta.push(token_meta);
  return token;
};
StateInline.prototype.scanDelims = function(start, canSplitWord) {
  const max = this.posMax;
  const marker = this.src.charCodeAt(start);
  const lastChar = start > 0 ? this.src.charCodeAt(start - 1) : 32;
  let pos = start;
  while (pos < max && this.src.charCodeAt(pos) === marker) {
    pos++;
  }
  const count = pos - start;
  const nextChar = pos < max ? this.src.charCodeAt(pos) : 32;
  const isLastPunctChar = isMdAsciiPunct(lastChar) || isPunctChar(String.fromCharCode(lastChar));
  const isNextPunctChar = isMdAsciiPunct(nextChar) || isPunctChar(String.fromCharCode(nextChar));
  const isLastWhiteSpace = isWhiteSpace(lastChar);
  const isNextWhiteSpace = isWhiteSpace(nextChar);
  const left_flanking = !isNextWhiteSpace && (!isNextPunctChar || isLastWhiteSpace || isLastPunctChar);
  const right_flanking = !isLastWhiteSpace && (!isLastPunctChar || isNextWhiteSpace || isNextPunctChar);
  const can_open = left_flanking && (canSplitWord || !right_flanking || isLastPunctChar);
  const can_close = right_flanking && (canSplitWord || !left_flanking || isNextPunctChar);
  return { can_open, can_close, length: count };
};
StateInline.prototype.Token = Token;
function isTerminatorChar(ch) {
  switch (ch) {
    case 10:
    case 33:
    case 35:
    case 36:
    case 37:
    case 38:
    case 42:
    case 43:
    case 45:
    case 58:
    case 60:
    case 61:
    case 62:
    case 64:
    case 91:
    case 92:
    case 93:
    case 94:
    case 95:
    case 96:
    case 123:
    case 125:
    case 126:
      return true;
    default:
      return false;
  }
}
function text(state, silent) {
  let pos = state.pos;
  while (pos < state.posMax && !isTerminatorChar(state.src.charCodeAt(pos))) {
    pos++;
  }
  if (pos === state.pos) {
    return false;
  }
  if (!silent) {
    state.pending += state.src.slice(state.pos, pos);
  }
  state.pos = pos;
  return true;
}
const SCHEME_RE = /(?:^|[^a-z0-9.+-])([a-z][a-z0-9.+-]*)$/i;
function linkify(state, silent) {
  if (!state.md.options.linkify) return false;
  if (state.linkLevel > 0) return false;
  const pos = state.pos;
  const max = state.posMax;
  if (pos + 3 > max) return false;
  if (state.src.charCodeAt(pos) !== 58) return false;
  if (state.src.charCodeAt(pos + 1) !== 47) return false;
  if (state.src.charCodeAt(pos + 2) !== 47) return false;
  const match2 = state.pending.match(SCHEME_RE);
  if (!match2) return false;
  const proto = match2[1];
  const link2 = state.md.linkify.matchAtStart(state.src.slice(pos - proto.length));
  if (!link2) return false;
  let url = link2.url;
  if (url.length <= proto.length) return false;
  let urlEnd = url.length;
  while (urlEnd > 0 && url.charCodeAt(urlEnd - 1) === 42) {
    urlEnd--;
  }
  if (urlEnd !== url.length) {
    url = url.slice(0, urlEnd);
  }
  const fullUrl = state.md.normalizeLink(url);
  if (!state.md.validateLink(fullUrl)) return false;
  if (!silent) {
    state.pending = state.pending.slice(0, -proto.length);
    const token_o = state.push("link_open", "a", 1);
    token_o.attrs = [["href", fullUrl]];
    token_o.markup = "linkify";
    token_o.info = "auto";
    const token_t = state.push("text", "", 0);
    token_t.content = state.md.normalizeLinkText(url);
    const token_c = state.push("link_close", "a", -1);
    token_c.markup = "linkify";
    token_c.info = "auto";
  }
  state.pos += url.length - proto.length;
  return true;
}
function newline(state, silent) {
  let pos = state.pos;
  if (state.src.charCodeAt(pos) !== 10) {
    return false;
  }
  const pmax = state.pending.length - 1;
  const max = state.posMax;
  if (!silent) {
    if (pmax >= 0 && state.pending.charCodeAt(pmax) === 32) {
      if (pmax >= 1 && state.pending.charCodeAt(pmax - 1) === 32) {
        let ws = pmax - 1;
        while (ws >= 1 && state.pending.charCodeAt(ws - 1) === 32) ws--;
        state.pending = state.pending.slice(0, ws);
        state.push("hardbreak", "br", 0);
      } else {
        state.pending = state.pending.slice(0, -1);
        state.push("softbreak", "br", 0);
      }
    } else {
      state.push("softbreak", "br", 0);
    }
  }
  pos++;
  while (pos < max && isSpace(state.src.charCodeAt(pos))) {
    pos++;
  }
  state.pos = pos;
  return true;
}
const ESCAPED = [];
for (let i2 = 0; i2 < 256; i2++) {
  ESCAPED.push(0);
}
"\\!\"#$%&'()*+,./:;<=>?@[]^_`{|}~-".split("").forEach(function(ch) {
  ESCAPED[ch.charCodeAt(0)] = 1;
});
function escape(state, silent) {
  let pos = state.pos;
  const max = state.posMax;
  if (state.src.charCodeAt(pos) !== 92) return false;
  pos++;
  if (pos >= max) return false;
  let ch1 = state.src.charCodeAt(pos);
  if (ch1 === 10) {
    if (!silent) {
      state.push("hardbreak", "br", 0);
    }
    pos++;
    while (pos < max) {
      ch1 = state.src.charCodeAt(pos);
      if (!isSpace(ch1)) break;
      pos++;
    }
    state.pos = pos;
    return true;
  }
  let escapedStr = state.src[pos];
  if (ch1 >= 55296 && ch1 <= 56319 && pos + 1 < max) {
    const ch2 = state.src.charCodeAt(pos + 1);
    if (ch2 >= 56320 && ch2 <= 57343) {
      escapedStr += state.src[pos + 1];
      pos++;
    }
  }
  const origStr = "\\" + escapedStr;
  if (!silent) {
    const token = state.push("text_special", "", 0);
    if (ch1 < 256 && ESCAPED[ch1] !== 0) {
      token.content = escapedStr;
    } else {
      token.content = origStr;
    }
    token.markup = origStr;
    token.info = "escape";
  }
  state.pos = pos + 1;
  return true;
}
function backtick(state, silent) {
  let pos = state.pos;
  const ch = state.src.charCodeAt(pos);
  if (ch !== 96) {
    return false;
  }
  const start = pos;
  pos++;
  const max = state.posMax;
  while (pos < max && state.src.charCodeAt(pos) === 96) {
    pos++;
  }
  const marker = state.src.slice(start, pos);
  const openerLength = marker.length;
  if (state.backticksScanned && (state.backticks[openerLength] || 0) <= start) {
    if (!silent) state.pending += marker;
    state.pos += openerLength;
    return true;
  }
  let matchEnd = pos;
  let matchStart;
  while ((matchStart = state.src.indexOf("`", matchEnd)) !== -1) {
    matchEnd = matchStart + 1;
    while (matchEnd < max && state.src.charCodeAt(matchEnd) === 96) {
      matchEnd++;
    }
    const closerLength = matchEnd - matchStart;
    if (closerLength === openerLength) {
      if (!silent) {
        const token = state.push("code_inline", "code", 0);
        token.markup = marker;
        token.content = state.src.slice(pos, matchStart).replace(/\n/g, " ").replace(/^ (.+) $/, "$1");
      }
      state.pos = matchEnd;
      return true;
    }
    state.backticks[closerLength] = matchStart;
  }
  state.backticksScanned = true;
  if (!silent) state.pending += marker;
  state.pos += openerLength;
  return true;
}
function strikethrough_tokenize(state, silent) {
  const start = state.pos;
  const marker = state.src.charCodeAt(start);
  if (silent) {
    return false;
  }
  if (marker !== 126) {
    return false;
  }
  const scanned = state.scanDelims(state.pos, true);
  let len = scanned.length;
  const ch = String.fromCharCode(marker);
  if (len < 2) {
    return false;
  }
  let token;
  if (len % 2) {
    token = state.push("text", "", 0);
    token.content = ch;
    len--;
  }
  for (let i2 = 0; i2 < len; i2 += 2) {
    token = state.push("text", "", 0);
    token.content = ch + ch;
    state.delimiters.push({
      marker,
      length: 0,
      // disable "rule of 3" length checks meant for emphasis
      token: state.tokens.length - 1,
      end: -1,
      open: scanned.can_open,
      close: scanned.can_close
    });
  }
  state.pos += scanned.length;
  return true;
}
function postProcess$1(state, delimiters) {
  let token;
  const loneMarkers = [];
  const max = delimiters.length;
  for (let i2 = 0; i2 < max; i2++) {
    const startDelim = delimiters[i2];
    if (startDelim.marker !== 126) {
      continue;
    }
    if (startDelim.end === -1) {
      continue;
    }
    const endDelim = delimiters[startDelim.end];
    token = state.tokens[startDelim.token];
    token.type = "s_open";
    token.tag = "s";
    token.nesting = 1;
    token.markup = "~~";
    token.content = "";
    token = state.tokens[endDelim.token];
    token.type = "s_close";
    token.tag = "s";
    token.nesting = -1;
    token.markup = "~~";
    token.content = "";
    if (state.tokens[endDelim.token - 1].type === "text" && state.tokens[endDelim.token - 1].content === "~") {
      loneMarkers.push(endDelim.token - 1);
    }
  }
  while (loneMarkers.length) {
    const i2 = loneMarkers.pop();
    let j = i2 + 1;
    while (j < state.tokens.length && state.tokens[j].type === "s_close") {
      j++;
    }
    j--;
    if (i2 !== j) {
      token = state.tokens[j];
      state.tokens[j] = state.tokens[i2];
      state.tokens[i2] = token;
    }
  }
}
function strikethrough_postProcess(state) {
  const tokens_meta = state.tokens_meta;
  const max = state.tokens_meta.length;
  postProcess$1(state, state.delimiters);
  for (let curr = 0; curr < max; curr++) {
    if (tokens_meta[curr] && tokens_meta[curr].delimiters) {
      postProcess$1(state, tokens_meta[curr].delimiters);
    }
  }
}
const r_strikethrough = {
  tokenize: strikethrough_tokenize,
  postProcess: strikethrough_postProcess
};
function emphasis_tokenize(state, silent) {
  const start = state.pos;
  const marker = state.src.charCodeAt(start);
  if (silent) {
    return false;
  }
  if (marker !== 95 && marker !== 42) {
    return false;
  }
  const scanned = state.scanDelims(state.pos, marker === 42);
  for (let i2 = 0; i2 < scanned.length; i2++) {
    const token = state.push("text", "", 0);
    token.content = String.fromCharCode(marker);
    state.delimiters.push({
      // Char code of the starting marker (number).
      //
      marker,
      // Total length of these series of delimiters.
      //
      length: scanned.length,
      // A position of the token this delimiter corresponds to.
      //
      token: state.tokens.length - 1,
      // If this delimiter is matched as a valid opener, `end` will be
      // equal to its position, otherwise it's `-1`.
      //
      end: -1,
      // Boolean flags that determine if this delimiter could open or close
      // an emphasis.
      //
      open: scanned.can_open,
      close: scanned.can_close
    });
  }
  state.pos += scanned.length;
  return true;
}
function postProcess(state, delimiters) {
  const max = delimiters.length;
  for (let i2 = max - 1; i2 >= 0; i2--) {
    const startDelim = delimiters[i2];
    if (startDelim.marker !== 95 && startDelim.marker !== 42) {
      continue;
    }
    if (startDelim.end === -1) {
      continue;
    }
    const endDelim = delimiters[startDelim.end];
    const isStrong = i2 > 0 && delimiters[i2 - 1].end === startDelim.end + 1 && // check that first two markers match and adjacent
    delimiters[i2 - 1].marker === startDelim.marker && delimiters[i2 - 1].token === startDelim.token - 1 && // check that last two markers are adjacent (we can safely assume they match)
    delimiters[startDelim.end + 1].token === endDelim.token + 1;
    const ch = String.fromCharCode(startDelim.marker);
    const token_o = state.tokens[startDelim.token];
    token_o.type = isStrong ? "strong_open" : "em_open";
    token_o.tag = isStrong ? "strong" : "em";
    token_o.nesting = 1;
    token_o.markup = isStrong ? ch + ch : ch;
    token_o.content = "";
    const token_c = state.tokens[endDelim.token];
    token_c.type = isStrong ? "strong_close" : "em_close";
    token_c.tag = isStrong ? "strong" : "em";
    token_c.nesting = -1;
    token_c.markup = isStrong ? ch + ch : ch;
    token_c.content = "";
    if (isStrong) {
      state.tokens[delimiters[i2 - 1].token].content = "";
      state.tokens[delimiters[startDelim.end + 1].token].content = "";
      i2--;
    }
  }
}
function emphasis_post_process(state) {
  const tokens_meta = state.tokens_meta;
  const max = state.tokens_meta.length;
  postProcess(state, state.delimiters);
  for (let curr = 0; curr < max; curr++) {
    if (tokens_meta[curr] && tokens_meta[curr].delimiters) {
      postProcess(state, tokens_meta[curr].delimiters);
    }
  }
}
const r_emphasis = {
  tokenize: emphasis_tokenize,
  postProcess: emphasis_post_process
};
function link(state, silent) {
  let code2, label2, res, ref;
  let href = "";
  let title2 = "";
  let start = state.pos;
  let parseReference = true;
  if (state.src.charCodeAt(state.pos) !== 91) {
    return false;
  }
  const oldPos = state.pos;
  const max = state.posMax;
  const labelStart = state.pos + 1;
  const labelEnd = state.md.helpers.parseLinkLabel(state, state.pos, true);
  if (labelEnd < 0) {
    return false;
  }
  let pos = labelEnd + 1;
  if (pos < max && state.src.charCodeAt(pos) === 40) {
    parseReference = false;
    pos++;
    for (; pos < max; pos++) {
      code2 = state.src.charCodeAt(pos);
      if (!isSpace(code2) && code2 !== 10) {
        break;
      }
    }
    if (pos >= max) {
      return false;
    }
    start = pos;
    res = state.md.helpers.parseLinkDestination(state.src, pos, state.posMax);
    if (res.ok) {
      href = state.md.normalizeLink(res.str);
      if (state.md.validateLink(href)) {
        pos = res.pos;
      } else {
        href = "";
      }
      start = pos;
      for (; pos < max; pos++) {
        code2 = state.src.charCodeAt(pos);
        if (!isSpace(code2) && code2 !== 10) {
          break;
        }
      }
      res = state.md.helpers.parseLinkTitle(state.src, pos, state.posMax);
      if (pos < max && start !== pos && res.ok) {
        title2 = res.str;
        pos = res.pos;
        for (; pos < max; pos++) {
          code2 = state.src.charCodeAt(pos);
          if (!isSpace(code2) && code2 !== 10) {
            break;
          }
        }
      }
    }
    if (pos >= max || state.src.charCodeAt(pos) !== 41) {
      parseReference = true;
    }
    pos++;
  }
  if (parseReference) {
    if (typeof state.env.references === "undefined") {
      return false;
    }
    if (pos < max && state.src.charCodeAt(pos) === 91) {
      start = pos + 1;
      pos = state.md.helpers.parseLinkLabel(state, pos);
      if (pos >= 0) {
        label2 = state.src.slice(start, pos++);
      } else {
        pos = labelEnd + 1;
      }
    } else {
      pos = labelEnd + 1;
    }
    if (!label2) {
      label2 = state.src.slice(labelStart, labelEnd);
    }
    ref = state.env.references[normalizeReference(label2)];
    if (!ref) {
      state.pos = oldPos;
      return false;
    }
    href = ref.href;
    title2 = ref.title;
  }
  if (!silent) {
    state.pos = labelStart;
    state.posMax = labelEnd;
    const token_o = state.push("link_open", "a", 1);
    const attrs = [["href", href]];
    token_o.attrs = attrs;
    if (title2) {
      attrs.push(["title", title2]);
    }
    state.linkLevel++;
    state.md.inline.tokenize(state);
    state.linkLevel--;
    state.push("link_close", "a", -1);
  }
  state.pos = pos;
  state.posMax = max;
  return true;
}
function image$1(state, silent) {
  let code2, content2, label2, pos, ref, res, title2, start;
  let href = "";
  const oldPos = state.pos;
  const max = state.posMax;
  if (state.src.charCodeAt(state.pos) !== 33) {
    return false;
  }
  if (state.src.charCodeAt(state.pos + 1) !== 91) {
    return false;
  }
  const labelStart = state.pos + 2;
  const labelEnd = state.md.helpers.parseLinkLabel(state, state.pos + 1, false);
  if (labelEnd < 0) {
    return false;
  }
  pos = labelEnd + 1;
  if (pos < max && state.src.charCodeAt(pos) === 40) {
    pos++;
    for (; pos < max; pos++) {
      code2 = state.src.charCodeAt(pos);
      if (!isSpace(code2) && code2 !== 10) {
        break;
      }
    }
    if (pos >= max) {
      return false;
    }
    start = pos;
    res = state.md.helpers.parseLinkDestination(state.src, pos, state.posMax);
    if (res.ok) {
      href = state.md.normalizeLink(res.str);
      if (state.md.validateLink(href)) {
        pos = res.pos;
      } else {
        href = "";
      }
    }
    start = pos;
    for (; pos < max; pos++) {
      code2 = state.src.charCodeAt(pos);
      if (!isSpace(code2) && code2 !== 10) {
        break;
      }
    }
    res = state.md.helpers.parseLinkTitle(state.src, pos, state.posMax);
    if (pos < max && start !== pos && res.ok) {
      title2 = res.str;
      pos = res.pos;
      for (; pos < max; pos++) {
        code2 = state.src.charCodeAt(pos);
        if (!isSpace(code2) && code2 !== 10) {
          break;
        }
      }
    } else {
      title2 = "";
    }
    if (pos >= max || state.src.charCodeAt(pos) !== 41) {
      state.pos = oldPos;
      return false;
    }
    pos++;
  } else {
    if (typeof state.env.references === "undefined") {
      return false;
    }
    if (pos < max && state.src.charCodeAt(pos) === 91) {
      start = pos + 1;
      pos = state.md.helpers.parseLinkLabel(state, pos);
      if (pos >= 0) {
        label2 = state.src.slice(start, pos++);
      } else {
        pos = labelEnd + 1;
      }
    } else {
      pos = labelEnd + 1;
    }
    if (!label2) {
      label2 = state.src.slice(labelStart, labelEnd);
    }
    ref = state.env.references[normalizeReference(label2)];
    if (!ref) {
      state.pos = oldPos;
      return false;
    }
    href = ref.href;
    title2 = ref.title;
  }
  if (!silent) {
    content2 = state.src.slice(labelStart, labelEnd);
    const tokens = [];
    state.md.inline.parse(
      content2,
      state.md,
      state.env,
      tokens
    );
    const token = state.push("image", "img", 0);
    const attrs = [["src", href], ["alt", ""]];
    token.attrs = attrs;
    token.children = tokens;
    token.content = content2;
    if (title2) {
      attrs.push(["title", title2]);
    }
  }
  state.pos = pos;
  state.posMax = max;
  return true;
}
const EMAIL_RE = /^([a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*)$/;
const AUTOLINK_RE = /^([a-zA-Z][a-zA-Z0-9+.-]{1,31}):([^<>\x00-\x20]*)$/;
function autolink(state, silent) {
  let pos = state.pos;
  if (state.src.charCodeAt(pos) !== 60) {
    return false;
  }
  const start = state.pos;
  const max = state.posMax;
  for (; ; ) {
    if (++pos >= max) return false;
    const ch = state.src.charCodeAt(pos);
    if (ch === 60) return false;
    if (ch === 62) break;
  }
  const url = state.src.slice(start + 1, pos);
  if (AUTOLINK_RE.test(url)) {
    const fullUrl = state.md.normalizeLink(url);
    if (!state.md.validateLink(fullUrl)) {
      return false;
    }
    if (!silent) {
      const token_o = state.push("link_open", "a", 1);
      token_o.attrs = [["href", fullUrl]];
      token_o.markup = "autolink";
      token_o.info = "auto";
      const token_t = state.push("text", "", 0);
      token_t.content = state.md.normalizeLinkText(url);
      const token_c = state.push("link_close", "a", -1);
      token_c.markup = "autolink";
      token_c.info = "auto";
    }
    state.pos += url.length + 2;
    return true;
  }
  if (EMAIL_RE.test(url)) {
    const fullUrl = state.md.normalizeLink("mailto:" + url);
    if (!state.md.validateLink(fullUrl)) {
      return false;
    }
    if (!silent) {
      const token_o = state.push("link_open", "a", 1);
      token_o.attrs = [["href", fullUrl]];
      token_o.markup = "autolink";
      token_o.info = "auto";
      const token_t = state.push("text", "", 0);
      token_t.content = state.md.normalizeLinkText(url);
      const token_c = state.push("link_close", "a", -1);
      token_c.markup = "autolink";
      token_c.info = "auto";
    }
    state.pos += url.length + 2;
    return true;
  }
  return false;
}
function isLinkOpen(str) {
  return /^<a[>\s]/i.test(str);
}
function isLinkClose(str) {
  return /^<\/a\s*>/i.test(str);
}
function isLetter(ch) {
  const lc = ch | 32;
  return lc >= 97 && lc <= 122;
}
function html_inline(state, silent) {
  if (!state.md.options.html) {
    return false;
  }
  const max = state.posMax;
  const pos = state.pos;
  if (state.src.charCodeAt(pos) !== 60 || pos + 2 >= max) {
    return false;
  }
  const ch = state.src.charCodeAt(pos + 1);
  if (ch !== 33 && ch !== 63 && ch !== 47 && !isLetter(ch)) {
    return false;
  }
  const match2 = state.src.slice(pos).match(HTML_TAG_RE);
  if (!match2) {
    return false;
  }
  if (!silent) {
    const token = state.push("html_inline", "", 0);
    token.content = match2[0];
    if (isLinkOpen(token.content)) state.linkLevel++;
    if (isLinkClose(token.content)) state.linkLevel--;
  }
  state.pos += match2[0].length;
  return true;
}
const DIGITAL_RE = /^&#((?:x[a-f0-9]{1,6}|[0-9]{1,7}));/i;
const NAMED_RE = /^&([a-z][a-z0-9]{1,31});/i;
function entity(state, silent) {
  const pos = state.pos;
  const max = state.posMax;
  if (state.src.charCodeAt(pos) !== 38) return false;
  if (pos + 1 >= max) return false;
  const ch = state.src.charCodeAt(pos + 1);
  if (ch === 35) {
    const match2 = state.src.slice(pos).match(DIGITAL_RE);
    if (match2) {
      if (!silent) {
        const code2 = match2[1][0].toLowerCase() === "x" ? parseInt(match2[1].slice(1), 16) : parseInt(match2[1], 10);
        const token = state.push("text_special", "", 0);
        token.content = isValidEntityCode(code2) ? fromCodePoint(code2) : fromCodePoint(65533);
        token.markup = match2[0];
        token.info = "entity";
      }
      state.pos += match2[0].length;
      return true;
    }
  } else {
    const match2 = state.src.slice(pos).match(NAMED_RE);
    if (match2) {
      const decoded = decodeHTML(match2[0]);
      if (decoded !== match2[0]) {
        if (!silent) {
          const token = state.push("text_special", "", 0);
          token.content = decoded;
          token.markup = match2[0];
          token.info = "entity";
        }
        state.pos += match2[0].length;
        return true;
      }
    }
  }
  return false;
}
function processDelimiters(delimiters) {
  const openersBottom = {};
  const max = delimiters.length;
  if (!max) return;
  let headerIdx = 0;
  let lastTokenIdx = -2;
  const jumps = [];
  for (let closerIdx = 0; closerIdx < max; closerIdx++) {
    const closer = delimiters[closerIdx];
    jumps.push(0);
    if (delimiters[headerIdx].marker !== closer.marker || lastTokenIdx !== closer.token - 1) {
      headerIdx = closerIdx;
    }
    lastTokenIdx = closer.token;
    closer.length = closer.length || 0;
    if (!closer.close) continue;
    if (!openersBottom.hasOwnProperty(closer.marker)) {
      openersBottom[closer.marker] = [-1, -1, -1, -1, -1, -1];
    }
    const minOpenerIdx = openersBottom[closer.marker][(closer.open ? 3 : 0) + closer.length % 3];
    let openerIdx = headerIdx - jumps[headerIdx] - 1;
    let newMinOpenerIdx = openerIdx;
    for (; openerIdx > minOpenerIdx; openerIdx -= jumps[openerIdx] + 1) {
      const opener = delimiters[openerIdx];
      if (opener.marker !== closer.marker) continue;
      if (opener.open && opener.end < 0) {
        let isOddMatch = false;
        if (opener.close || closer.open) {
          if ((opener.length + closer.length) % 3 === 0) {
            if (opener.length % 3 !== 0 || closer.length % 3 !== 0) {
              isOddMatch = true;
            }
          }
        }
        if (!isOddMatch) {
          const lastJump = openerIdx > 0 && !delimiters[openerIdx - 1].open ? jumps[openerIdx - 1] + 1 : 0;
          jumps[closerIdx] = closerIdx - openerIdx + lastJump;
          jumps[openerIdx] = lastJump;
          closer.open = false;
          opener.end = closerIdx;
          opener.close = false;
          newMinOpenerIdx = -1;
          lastTokenIdx = -2;
          break;
        }
      }
    }
    if (newMinOpenerIdx !== -1) {
      openersBottom[closer.marker][(closer.open ? 3 : 0) + (closer.length || 0) % 3] = newMinOpenerIdx;
    }
  }
}
function link_pairs(state) {
  const tokens_meta = state.tokens_meta;
  const max = state.tokens_meta.length;
  processDelimiters(state.delimiters);
  for (let curr = 0; curr < max; curr++) {
    if (tokens_meta[curr] && tokens_meta[curr].delimiters) {
      processDelimiters(tokens_meta[curr].delimiters);
    }
  }
}
function fragments_join(state) {
  let curr, last2;
  let level = 0;
  const tokens = state.tokens;
  const max = state.tokens.length;
  for (curr = last2 = 0; curr < max; curr++) {
    if (tokens[curr].nesting < 0) level--;
    tokens[curr].level = level;
    if (tokens[curr].nesting > 0) level++;
    if (tokens[curr].type === "text" && curr + 1 < max && tokens[curr + 1].type === "text") {
      tokens[curr + 1].content = tokens[curr].content + tokens[curr + 1].content;
    } else {
      if (curr !== last2) {
        tokens[last2] = tokens[curr];
      }
      last2++;
    }
  }
  if (curr !== last2) {
    tokens.length = last2;
  }
}
const _rules = [
  ["text", text],
  ["linkify", linkify],
  ["newline", newline],
  ["escape", escape],
  ["backticks", backtick],
  ["strikethrough", r_strikethrough.tokenize],
  ["emphasis", r_emphasis.tokenize],
  ["link", link],
  ["image", image$1],
  ["autolink", autolink],
  ["html_inline", html_inline],
  ["entity", entity]
];
const _rules2 = [
  ["balance_pairs", link_pairs],
  ["strikethrough", r_strikethrough.postProcess],
  ["emphasis", r_emphasis.postProcess],
  // rules for pairs separate '**' into its own text tokens, which may be left unused,
  // rule below merges unused segments back with the rest of the text
  ["fragments_join", fragments_join]
];
function ParserInline() {
  this.ruler = new Ruler();
  for (let i2 = 0; i2 < _rules.length; i2++) {
    this.ruler.push(_rules[i2][0], _rules[i2][1]);
  }
  this.ruler2 = new Ruler();
  for (let i2 = 0; i2 < _rules2.length; i2++) {
    this.ruler2.push(_rules2[i2][0], _rules2[i2][1]);
  }
}
ParserInline.prototype.skipToken = function(state) {
  const pos = state.pos;
  const rules = this.ruler.getRules("");
  const len = rules.length;
  const maxNesting = state.md.options.maxNesting;
  const cache = state.cache;
  if (typeof cache[pos] !== "undefined") {
    state.pos = cache[pos];
    return;
  }
  let ok = false;
  if (state.level < maxNesting) {
    for (let i2 = 0; i2 < len; i2++) {
      state.level++;
      ok = rules[i2](state, true);
      state.level--;
      if (ok) {
        if (pos >= state.pos) {
          throw new Error("inline rule didn't increment state.pos");
        }
        break;
      }
    }
  } else {
    state.pos = state.posMax;
  }
  if (!ok) {
    state.pos++;
  }
  cache[pos] = state.pos;
};
ParserInline.prototype.tokenize = function(state) {
  const rules = this.ruler.getRules("");
  const len = rules.length;
  const end = state.posMax;
  const maxNesting = state.md.options.maxNesting;
  while (state.pos < end) {
    const prevPos = state.pos;
    let ok = false;
    if (state.level < maxNesting) {
      for (let i2 = 0; i2 < len; i2++) {
        ok = rules[i2](state, false);
        if (ok) {
          if (prevPos >= state.pos) {
            throw new Error("inline rule didn't increment state.pos");
          }
          break;
        }
      }
    }
    if (ok) {
      if (state.pos >= end) {
        break;
      }
      continue;
    }
    state.pending += state.src[state.pos++];
  }
  if (state.pending) {
    state.pushPending();
  }
};
ParserInline.prototype.parse = function(str, md, env, outTokens) {
  const state = new this.State(str, md, env, outTokens);
  this.tokenize(state);
  const rules = this.ruler2.getRules("");
  const len = rules.length;
  for (let i2 = 0; i2 < len; i2++) {
    rules[i2](state);
  }
};
ParserInline.prototype.State = StateInline;
function reFactory(opts) {
  const re2 = {};
  opts = opts || {};
  re2.src_Any = Any.source;
  re2.src_Cc = Cc.source;
  re2.src_Z = Z.source;
  re2.src_P = P.source;
  re2.src_ZPCc = [re2.src_Z, re2.src_P, re2.src_Cc].join("|");
  re2.src_ZCc = [re2.src_Z, re2.src_Cc].join("|");
  const text_separators = "[><｜]";
  re2.src_pseudo_letter = "(?:(?!" + text_separators + "|" + re2.src_ZPCc + ")" + re2.src_Any + ")";
  re2.src_ip4 = "(?:(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)";
  re2.src_auth = "(?:(?:(?!" + re2.src_ZCc + "|[@/\\[\\]()]).)+@)?";
  re2.src_port = "(?::(?:6(?:[0-4]\\d{3}|5(?:[0-4]\\d{2}|5(?:[0-2]\\d|3[0-5])))|[1-5]?\\d{1,4}))?";
  re2.src_host_terminator = "(?=$|" + text_separators + "|" + re2.src_ZPCc + ")(?!" + (opts["---"] ? "-(?!--)|" : "-|") + "_|:\\d|\\.-|\\.(?!$|" + re2.src_ZPCc + "))";
  re2.src_path = "(?:[/?#](?:(?!" + re2.src_ZCc + "|" + text_separators + `|[()[\\]{}.,"'?!\\-;]).|\\[(?:(?!` + re2.src_ZCc + "|\\]).)*\\]|\\((?:(?!" + re2.src_ZCc + "|[)]).)*\\)|\\{(?:(?!" + re2.src_ZCc + '|[}]).)*\\}|\\"(?:(?!' + re2.src_ZCc + `|["]).)+\\"|\\'(?:(?!` + re2.src_ZCc + "|[']).)+\\'|\\'(?=" + re2.src_pseudo_letter + "|[-])|\\.{2,}[a-zA-Z0-9%/&]|\\.(?!" + re2.src_ZCc + "|[.]|$)|" + (opts["---"] ? "\\-(?!--(?:[^-]|$))(?:-*)|" : "\\-+|") + // allow `,,,` in paths
  ",(?!" + re2.src_ZCc + "|$)|;(?!" + re2.src_ZCc + "|$)|\\!+(?!" + re2.src_ZCc + "|[!]|$)|\\?(?!" + re2.src_ZCc + "|[?]|$))+|\\/)?";
  re2.src_email_name = '[\\-;:&=\\+\\$,\\.a-zA-Z0-9_][\\-;:&=\\+\\$,\\"\\.a-zA-Z0-9_]*';
  re2.src_xn = "xn--[a-z0-9\\-]{1,59}";
  re2.src_domain_root = // Allow letters & digits (http://test1)
  "(?:" + re2.src_xn + "|" + re2.src_pseudo_letter + "{1,63})";
  re2.src_domain = "(?:" + re2.src_xn + "|(?:" + re2.src_pseudo_letter + ")|(?:" + re2.src_pseudo_letter + "(?:-|" + re2.src_pseudo_letter + "){0,61}" + re2.src_pseudo_letter + "))";
  re2.src_host = "(?:(?:(?:(?:" + re2.src_domain + ")\\.)*" + re2.src_domain + "))";
  re2.tpl_host_fuzzy = "(?:" + re2.src_ip4 + "|(?:(?:(?:" + re2.src_domain + ")\\.)+(?:%TLDS%)))";
  re2.tpl_host_no_ip_fuzzy = "(?:(?:(?:" + re2.src_domain + ")\\.)+(?:%TLDS%))";
  re2.src_host_strict = re2.src_host + re2.src_host_terminator;
  re2.tpl_host_fuzzy_strict = re2.tpl_host_fuzzy + re2.src_host_terminator;
  re2.src_host_port_strict = re2.src_host + re2.src_port + re2.src_host_terminator;
  re2.tpl_host_port_fuzzy_strict = re2.tpl_host_fuzzy + re2.src_port + re2.src_host_terminator;
  re2.tpl_host_port_no_ip_fuzzy_strict = re2.tpl_host_no_ip_fuzzy + re2.src_port + re2.src_host_terminator;
  re2.tpl_host_fuzzy_test = "localhost|www\\.|\\.\\d{1,3}\\.|(?:\\.(?:%TLDS%)(?:" + re2.src_ZPCc + "|>|$))";
  re2.tpl_email_fuzzy = "(^|" + text_separators + '|"|\\(|' + re2.src_ZCc + ")(" + re2.src_email_name + "@" + re2.tpl_host_fuzzy_strict + ")";
  re2.tpl_link_fuzzy = // Fuzzy link can't be prepended with .:/\- and non punctuation.
  // but can start with > (markdown blockquote)
  "(^|(?![.:/\\-_@])(?:[$+<=>^`|｜]|" + re2.src_ZPCc + "))((?![$+<=>^`|｜])" + re2.tpl_host_port_fuzzy_strict + re2.src_path + ")";
  re2.tpl_link_no_ip_fuzzy = // Fuzzy link can't be prepended with .:/\- and non punctuation.
  // but can start with > (markdown blockquote)
  "(^|(?![.:/\\-_@])(?:[$+<=>^`|｜]|" + re2.src_ZPCc + "))((?![$+<=>^`|｜])" + re2.tpl_host_port_no_ip_fuzzy_strict + re2.src_path + ")";
  return re2;
}
function assign(obj) {
  const sources = Array.prototype.slice.call(arguments, 1);
  sources.forEach(function(source) {
    if (!source) {
      return;
    }
    Object.keys(source).forEach(function(key2) {
      obj[key2] = source[key2];
    });
  });
  return obj;
}
function _class(obj) {
  return Object.prototype.toString.call(obj);
}
function isString(obj) {
  return _class(obj) === "[object String]";
}
function isObject(obj) {
  return _class(obj) === "[object Object]";
}
function isRegExp(obj) {
  return _class(obj) === "[object RegExp]";
}
function isFunction(obj) {
  return _class(obj) === "[object Function]";
}
function escapeRE(str) {
  return str.replace(/[.?*+^$[\]\\(){}|-]/g, "\\$&");
}
const defaultOptions = {
  fuzzyLink: true,
  fuzzyEmail: true,
  fuzzyIP: false
};
function isOptionsObj(obj) {
  return Object.keys(obj || {}).reduce(function(acc, k2) {
    return acc || defaultOptions.hasOwnProperty(k2);
  }, false);
}
const defaultSchemas = {
  "http:": {
    validate: function(text2, pos, self) {
      const tail = text2.slice(pos);
      if (!self.re.http) {
        self.re.http = new RegExp(
          "^\\/\\/" + self.re.src_auth + self.re.src_host_port_strict + self.re.src_path,
          "i"
        );
      }
      if (self.re.http.test(tail)) {
        return tail.match(self.re.http)[0].length;
      }
      return 0;
    }
  },
  "https:": "http:",
  "ftp:": "http:",
  "//": {
    validate: function(text2, pos, self) {
      const tail = text2.slice(pos);
      if (!self.re.no_http) {
        self.re.no_http = new RegExp(
          "^" + self.re.src_auth + // Don't allow single-level domains, because of false positives like '//test'
          // with code comments
          "(?:localhost|(?:(?:" + self.re.src_domain + ")\\.)+" + self.re.src_domain_root + ")" + self.re.src_port + self.re.src_host_terminator + self.re.src_path,
          "i"
        );
      }
      if (self.re.no_http.test(tail)) {
        if (pos >= 3 && text2[pos - 3] === ":") {
          return 0;
        }
        if (pos >= 3 && text2[pos - 3] === "/") {
          return 0;
        }
        return tail.match(self.re.no_http)[0].length;
      }
      return 0;
    }
  },
  "mailto:": {
    validate: function(text2, pos, self) {
      const tail = text2.slice(pos);
      if (!self.re.mailto) {
        self.re.mailto = new RegExp(
          "^" + self.re.src_email_name + "@" + self.re.src_host_strict,
          "i"
        );
      }
      if (self.re.mailto.test(tail)) {
        return tail.match(self.re.mailto)[0].length;
      }
      return 0;
    }
  }
};
const tlds_2ch_src_re = "a[cdefgilmnoqrstuwxz]|b[abdefghijmnorstvwyz]|c[acdfghiklmnoruvwxyz]|d[ejkmoz]|e[cegrstu]|f[ijkmor]|g[abdefghilmnpqrstuwy]|h[kmnrtu]|i[delmnoqrst]|j[emop]|k[eghimnprwyz]|l[abcikrstuvy]|m[acdeghklmnopqrstuvwxyz]|n[acefgilopruz]|om|p[aefghklmnrstwy]|qa|r[eosuw]|s[abcdeghijklmnortuvxyz]|t[cdfghjklmnortvwz]|u[agksyz]|v[aceginu]|w[fs]|y[et]|z[amw]";
const tlds_default = "biz|com|edu|gov|net|org|pro|web|xxx|aero|asia|coop|info|museum|name|shop|рф".split("|");
function resetScanCache(self) {
  self.__index__ = -1;
  self.__text_cache__ = "";
}
function createValidator(re2) {
  return function(text2, pos) {
    const tail = text2.slice(pos);
    if (re2.test(tail)) {
      return tail.match(re2)[0].length;
    }
    return 0;
  };
}
function createNormalizer() {
  return function(match2, self) {
    self.normalize(match2);
  };
}
function compile(self) {
  const re2 = self.re = reFactory(self.__opts__);
  const tlds2 = self.__tlds__.slice();
  self.onCompile();
  if (!self.__tlds_replaced__) {
    tlds2.push(tlds_2ch_src_re);
  }
  tlds2.push(re2.src_xn);
  re2.src_tlds = tlds2.join("|");
  function untpl(tpl) {
    return tpl.replace("%TLDS%", re2.src_tlds);
  }
  re2.email_fuzzy = RegExp(untpl(re2.tpl_email_fuzzy), "i");
  re2.link_fuzzy = RegExp(untpl(re2.tpl_link_fuzzy), "i");
  re2.link_no_ip_fuzzy = RegExp(untpl(re2.tpl_link_no_ip_fuzzy), "i");
  re2.host_fuzzy_test = RegExp(untpl(re2.tpl_host_fuzzy_test), "i");
  const aliases = [];
  self.__compiled__ = {};
  function schemaError(name, val) {
    throw new Error('(LinkifyIt) Invalid schema "' + name + '": ' + val);
  }
  Object.keys(self.__schemas__).forEach(function(name) {
    const val = self.__schemas__[name];
    if (val === null) {
      return;
    }
    const compiled = { validate: null, link: null };
    self.__compiled__[name] = compiled;
    if (isObject(val)) {
      if (isRegExp(val.validate)) {
        compiled.validate = createValidator(val.validate);
      } else if (isFunction(val.validate)) {
        compiled.validate = val.validate;
      } else {
        schemaError(name, val);
      }
      if (isFunction(val.normalize)) {
        compiled.normalize = val.normalize;
      } else if (!val.normalize) {
        compiled.normalize = createNormalizer();
      } else {
        schemaError(name, val);
      }
      return;
    }
    if (isString(val)) {
      aliases.push(name);
      return;
    }
    schemaError(name, val);
  });
  aliases.forEach(function(alias) {
    if (!self.__compiled__[self.__schemas__[alias]]) {
      return;
    }
    self.__compiled__[alias].validate = self.__compiled__[self.__schemas__[alias]].validate;
    self.__compiled__[alias].normalize = self.__compiled__[self.__schemas__[alias]].normalize;
  });
  self.__compiled__[""] = { validate: null, normalize: createNormalizer() };
  const slist = Object.keys(self.__compiled__).filter(function(name) {
    return name.length > 0 && self.__compiled__[name];
  }).map(escapeRE).join("|");
  self.re.schema_test = RegExp("(^|(?!_)(?:[><｜]|" + re2.src_ZPCc + "))(" + slist + ")", "i");
  self.re.schema_search = RegExp("(^|(?!_)(?:[><｜]|" + re2.src_ZPCc + "))(" + slist + ")", "ig");
  self.re.schema_at_start = RegExp("^" + self.re.schema_search.source, "i");
  self.re.pretest = RegExp(
    "(" + self.re.schema_test.source + ")|(" + self.re.host_fuzzy_test.source + ")|@",
    "i"
  );
  resetScanCache(self);
}
function Match$1(self, shift) {
  const start = self.__index__;
  const end = self.__last_index__;
  const text2 = self.__text_cache__.slice(start, end);
  this.schema = self.__schema__.toLowerCase();
  this.index = start + shift;
  this.lastIndex = end + shift;
  this.raw = text2;
  this.text = text2;
  this.url = text2;
}
function createMatch(self, shift) {
  const match2 = new Match$1(self, shift);
  self.__compiled__[match2.schema].normalize(match2, self);
  return match2;
}
function LinkifyIt(schemas, options) {
  if (!(this instanceof LinkifyIt)) {
    return new LinkifyIt(schemas, options);
  }
  if (!options) {
    if (isOptionsObj(schemas)) {
      options = schemas;
      schemas = {};
    }
  }
  this.__opts__ = assign({}, defaultOptions, options);
  this.__index__ = -1;
  this.__last_index__ = -1;
  this.__schema__ = "";
  this.__text_cache__ = "";
  this.__schemas__ = assign({}, defaultSchemas, schemas);
  this.__compiled__ = {};
  this.__tlds__ = tlds_default;
  this.__tlds_replaced__ = false;
  this.re = {};
  compile(this);
}
LinkifyIt.prototype.add = function add(schema, definition) {
  this.__schemas__[schema] = definition;
  compile(this);
  return this;
};
LinkifyIt.prototype.set = function set(options) {
  this.__opts__ = assign(this.__opts__, options);
  return this;
};
LinkifyIt.prototype.test = function test(text2) {
  this.__text_cache__ = text2;
  this.__index__ = -1;
  if (!text2.length) {
    return false;
  }
  let m, ml, me2, len, shift, next, re2, tld_pos, at_pos;
  if (this.re.schema_test.test(text2)) {
    re2 = this.re.schema_search;
    re2.lastIndex = 0;
    while ((m = re2.exec(text2)) !== null) {
      len = this.testSchemaAt(text2, m[2], re2.lastIndex);
      if (len) {
        this.__schema__ = m[2];
        this.__index__ = m.index + m[1].length;
        this.__last_index__ = m.index + m[0].length + len;
        break;
      }
    }
  }
  if (this.__opts__.fuzzyLink && this.__compiled__["http:"]) {
    tld_pos = text2.search(this.re.host_fuzzy_test);
    if (tld_pos >= 0) {
      if (this.__index__ < 0 || tld_pos < this.__index__) {
        if ((ml = text2.match(this.__opts__.fuzzyIP ? this.re.link_fuzzy : this.re.link_no_ip_fuzzy)) !== null) {
          shift = ml.index + ml[1].length;
          if (this.__index__ < 0 || shift < this.__index__) {
            this.__schema__ = "";
            this.__index__ = shift;
            this.__last_index__ = ml.index + ml[0].length;
          }
        }
      }
    }
  }
  if (this.__opts__.fuzzyEmail && this.__compiled__["mailto:"]) {
    at_pos = text2.indexOf("@");
    if (at_pos >= 0) {
      if ((me2 = text2.match(this.re.email_fuzzy)) !== null) {
        shift = me2.index + me2[1].length;
        next = me2.index + me2[0].length;
        if (this.__index__ < 0 || shift < this.__index__ || shift === this.__index__ && next > this.__last_index__) {
          this.__schema__ = "mailto:";
          this.__index__ = shift;
          this.__last_index__ = next;
        }
      }
    }
  }
  return this.__index__ >= 0;
};
LinkifyIt.prototype.pretest = function pretest(text2) {
  return this.re.pretest.test(text2);
};
LinkifyIt.prototype.testSchemaAt = function testSchemaAt(text2, schema, pos) {
  if (!this.__compiled__[schema.toLowerCase()]) {
    return 0;
  }
  return this.__compiled__[schema.toLowerCase()].validate(text2, pos, this);
};
LinkifyIt.prototype.match = function match(text2) {
  const result2 = [];
  let shift = 0;
  if (this.__index__ >= 0 && this.__text_cache__ === text2) {
    result2.push(createMatch(this, shift));
    shift = this.__last_index__;
  }
  let tail = shift ? text2.slice(shift) : text2;
  while (this.test(tail)) {
    result2.push(createMatch(this, shift));
    tail = tail.slice(this.__last_index__);
    shift += this.__last_index__;
  }
  if (result2.length) {
    return result2;
  }
  return null;
};
LinkifyIt.prototype.matchAtStart = function matchAtStart(text2) {
  this.__text_cache__ = text2;
  this.__index__ = -1;
  if (!text2.length) return null;
  const m = this.re.schema_at_start.exec(text2);
  if (!m) return null;
  const len = this.testSchemaAt(text2, m[2], m[0].length);
  if (!len) return null;
  this.__schema__ = m[2];
  this.__index__ = m.index + m[1].length;
  this.__last_index__ = m.index + m[0].length + len;
  return createMatch(this, 0);
};
LinkifyIt.prototype.tlds = function tlds(list2, keepOld) {
  list2 = Array.isArray(list2) ? list2 : [list2];
  if (!keepOld) {
    this.__tlds__ = list2.slice();
    this.__tlds_replaced__ = true;
    compile(this);
    return this;
  }
  this.__tlds__ = this.__tlds__.concat(list2).sort().filter(function(el, idx, arr) {
    return el !== arr[idx - 1];
  }).reverse();
  compile(this);
  return this;
};
LinkifyIt.prototype.normalize = function normalize2(match2) {
  if (!match2.schema) {
    match2.url = "http://" + match2.url;
  }
  if (match2.schema === "mailto:" && !/^mailto:/i.test(match2.url)) {
    match2.url = "mailto:" + match2.url;
  }
};
LinkifyIt.prototype.onCompile = function onCompile() {
};
const maxInt = 2147483647;
const base = 36;
const tMin = 1;
const tMax = 26;
const skew = 38;
const damp = 700;
const initialBias = 72;
const initialN = 128;
const delimiter = "-";
const regexPunycode = /^xn--/;
const regexNonASCII = /[^\0-\x7F]/;
const regexSeparators = /[\x2E\u3002\uFF0E\uFF61]/g;
const errors = {
  "overflow": "Overflow: input needs wider integers to process",
  "not-basic": "Illegal input >= 0x80 (not a basic code point)",
  "invalid-input": "Invalid input"
};
const baseMinusTMin = base - tMin;
const floor = Math.floor;
const stringFromCharCode = String.fromCharCode;
function error$1(type) {
  throw new RangeError(errors[type]);
}
function map(array, callback) {
  const result2 = [];
  let length = array.length;
  while (length--) {
    result2[length] = callback(array[length]);
  }
  return result2;
}
function mapDomain(domain, callback) {
  const parts = domain.split("@");
  let result2 = "";
  if (parts.length > 1) {
    result2 = parts[0] + "@";
    domain = parts[1];
  }
  domain = domain.replace(regexSeparators, ".");
  const labels = domain.split(".");
  const encoded = map(labels, callback).join(".");
  return result2 + encoded;
}
function ucs2decode(string) {
  const output2 = [];
  let counter = 0;
  const length = string.length;
  while (counter < length) {
    const value2 = string.charCodeAt(counter++);
    if (value2 >= 55296 && value2 <= 56319 && counter < length) {
      const extra = string.charCodeAt(counter++);
      if ((extra & 64512) == 56320) {
        output2.push(((value2 & 1023) << 10) + (extra & 1023) + 65536);
      } else {
        output2.push(value2);
        counter--;
      }
    } else {
      output2.push(value2);
    }
  }
  return output2;
}
const ucs2encode = (codePoints) => String.fromCodePoint(...codePoints);
const basicToDigit = function(codePoint) {
  if (codePoint >= 48 && codePoint < 58) {
    return 26 + (codePoint - 48);
  }
  if (codePoint >= 65 && codePoint < 91) {
    return codePoint - 65;
  }
  if (codePoint >= 97 && codePoint < 123) {
    return codePoint - 97;
  }
  return base;
};
const digitToBasic = function(digit, flag) {
  return digit + 22 + 75 * (digit < 26) - ((flag != 0) << 5);
};
const adapt = function(delta, numPoints, firstTime) {
  let k2 = 0;
  delta = firstTime ? floor(delta / damp) : delta >> 1;
  delta += floor(delta / numPoints);
  for (; delta > baseMinusTMin * tMax >> 1; k2 += base) {
    delta = floor(delta / baseMinusTMin);
  }
  return floor(k2 + (baseMinusTMin + 1) * delta / (delta + skew));
};
const decode = function(input) {
  const output2 = [];
  const inputLength = input.length;
  let i2 = 0;
  let n2 = initialN;
  let bias = initialBias;
  let basic = input.lastIndexOf(delimiter);
  if (basic < 0) {
    basic = 0;
  }
  for (let j = 0; j < basic; ++j) {
    if (input.charCodeAt(j) >= 128) {
      error$1("not-basic");
    }
    output2.push(input.charCodeAt(j));
  }
  for (let index = basic > 0 ? basic + 1 : 0; index < inputLength; ) {
    const oldi = i2;
    for (let w = 1, k2 = base; ; k2 += base) {
      if (index >= inputLength) {
        error$1("invalid-input");
      }
      const digit = basicToDigit(input.charCodeAt(index++));
      if (digit >= base) {
        error$1("invalid-input");
      }
      if (digit > floor((maxInt - i2) / w)) {
        error$1("overflow");
      }
      i2 += digit * w;
      const t2 = k2 <= bias ? tMin : k2 >= bias + tMax ? tMax : k2 - bias;
      if (digit < t2) {
        break;
      }
      const baseMinusT = base - t2;
      if (w > floor(maxInt / baseMinusT)) {
        error$1("overflow");
      }
      w *= baseMinusT;
    }
    const out = output2.length + 1;
    bias = adapt(i2 - oldi, out, oldi == 0);
    if (floor(i2 / out) > maxInt - n2) {
      error$1("overflow");
    }
    n2 += floor(i2 / out);
    i2 %= out;
    output2.splice(i2++, 0, n2);
  }
  return String.fromCodePoint(...output2);
};
const encode = function(input) {
  const output2 = [];
  input = ucs2decode(input);
  const inputLength = input.length;
  let n2 = initialN;
  let delta = 0;
  let bias = initialBias;
  for (const currentValue of input) {
    if (currentValue < 128) {
      output2.push(stringFromCharCode(currentValue));
    }
  }
  const basicLength = output2.length;
  let handledCPCount = basicLength;
  if (basicLength) {
    output2.push(delimiter);
  }
  while (handledCPCount < inputLength) {
    let m = maxInt;
    for (const currentValue of input) {
      if (currentValue >= n2 && currentValue < m) {
        m = currentValue;
      }
    }
    const handledCPCountPlusOne = handledCPCount + 1;
    if (m - n2 > floor((maxInt - delta) / handledCPCountPlusOne)) {
      error$1("overflow");
    }
    delta += (m - n2) * handledCPCountPlusOne;
    n2 = m;
    for (const currentValue of input) {
      if (currentValue < n2 && ++delta > maxInt) {
        error$1("overflow");
      }
      if (currentValue === n2) {
        let q = delta;
        for (let k2 = base; ; k2 += base) {
          const t2 = k2 <= bias ? tMin : k2 >= bias + tMax ? tMax : k2 - bias;
          if (q < t2) {
            break;
          }
          const qMinusT = q - t2;
          const baseMinusT = base - t2;
          output2.push(
            stringFromCharCode(digitToBasic(t2 + qMinusT % baseMinusT, 0))
          );
          q = floor(qMinusT / baseMinusT);
        }
        output2.push(stringFromCharCode(digitToBasic(q, 0)));
        bias = adapt(delta, handledCPCountPlusOne, handledCPCount === basicLength);
        delta = 0;
        ++handledCPCount;
      }
    }
    ++delta;
    ++n2;
  }
  return output2.join("");
};
const toUnicode = function(input) {
  return mapDomain(input, function(string) {
    return regexPunycode.test(string) ? decode(string.slice(4).toLowerCase()) : string;
  });
};
const toASCII = function(input) {
  return mapDomain(input, function(string) {
    return regexNonASCII.test(string) ? "xn--" + encode(string) : string;
  });
};
const punycode = {
  /**
   * A string representing the current Punycode.js version number.
   * @memberOf punycode
   * @type String
   */
  "version": "2.3.1",
  /**
   * An object of methods to convert from JavaScript's internal character
   * representation (UCS-2) to Unicode code points, and back.
   * @see <https://mathiasbynens.be/notes/javascript-encoding>
   * @memberOf punycode
   * @type Object
   */
  "ucs2": {
    "decode": ucs2decode,
    "encode": ucs2encode
  },
  "decode": decode,
  "encode": encode,
  "toASCII": toASCII,
  "toUnicode": toUnicode
};
const cfg_default = {
  options: {
    // Enable HTML tags in source
    html: false,
    // Use '/' to close single tags (<br />)
    xhtmlOut: false,
    // Convert '\n' in paragraphs into <br>
    breaks: false,
    // CSS language prefix for fenced blocks
    langPrefix: "language-",
    // autoconvert URL-like texts to links
    linkify: false,
    // Enable some language-neutral replacements + quotes beautification
    typographer: false,
    // Double + single quotes replacement pairs, when typographer enabled,
    // and smartquotes on. Could be either a String or an Array.
    //
    // For example, you can use '«»„“' for Russian, '„“‚‘' for German,
    // and ['«\xA0', '\xA0»', '‹\xA0', '\xA0›'] for French (including nbsp).
    quotes: "“”‘’",
    /* “”‘’ */
    // Highlighter function. Should return escaped HTML,
    // or '' if the source string is not changed and should be escaped externaly.
    // If result starts with <pre... internal wrapper is skipped.
    //
    // function (/*str, lang*/) { return ''; }
    //
    highlight: null,
    // Internal protection, recursion limit
    maxNesting: 100
  },
  components: {
    core: {},
    block: {},
    inline: {}
  }
};
const cfg_zero = {
  options: {
    // Enable HTML tags in source
    html: false,
    // Use '/' to close single tags (<br />)
    xhtmlOut: false,
    // Convert '\n' in paragraphs into <br>
    breaks: false,
    // CSS language prefix for fenced blocks
    langPrefix: "language-",
    // autoconvert URL-like texts to links
    linkify: false,
    // Enable some language-neutral replacements + quotes beautification
    typographer: false,
    // Double + single quotes replacement pairs, when typographer enabled,
    // and smartquotes on. Could be either a String or an Array.
    //
    // For example, you can use '«»„“' for Russian, '„“‚‘' for German,
    // and ['«\xA0', '\xA0»', '‹\xA0', '\xA0›'] for French (including nbsp).
    quotes: "“”‘’",
    /* “”‘’ */
    // Highlighter function. Should return escaped HTML,
    // or '' if the source string is not changed and should be escaped externaly.
    // If result starts with <pre... internal wrapper is skipped.
    //
    // function (/*str, lang*/) { return ''; }
    //
    highlight: null,
    // Internal protection, recursion limit
    maxNesting: 20
  },
  components: {
    core: {
      rules: [
        "normalize",
        "block",
        "inline",
        "text_join"
      ]
    },
    block: {
      rules: [
        "paragraph"
      ]
    },
    inline: {
      rules: [
        "text"
      ],
      rules2: [
        "balance_pairs",
        "fragments_join"
      ]
    }
  }
};
const cfg_commonmark = {
  options: {
    // Enable HTML tags in source
    html: true,
    // Use '/' to close single tags (<br />)
    xhtmlOut: true,
    // Convert '\n' in paragraphs into <br>
    breaks: false,
    // CSS language prefix for fenced blocks
    langPrefix: "language-",
    // autoconvert URL-like texts to links
    linkify: false,
    // Enable some language-neutral replacements + quotes beautification
    typographer: false,
    // Double + single quotes replacement pairs, when typographer enabled,
    // and smartquotes on. Could be either a String or an Array.
    //
    // For example, you can use '«»„“' for Russian, '„“‚‘' for German,
    // and ['«\xA0', '\xA0»', '‹\xA0', '\xA0›'] for French (including nbsp).
    quotes: "“”‘’",
    /* “”‘’ */
    // Highlighter function. Should return escaped HTML,
    // or '' if the source string is not changed and should be escaped externaly.
    // If result starts with <pre... internal wrapper is skipped.
    //
    // function (/*str, lang*/) { return ''; }
    //
    highlight: null,
    // Internal protection, recursion limit
    maxNesting: 20
  },
  components: {
    core: {
      rules: [
        "normalize",
        "block",
        "inline",
        "text_join"
      ]
    },
    block: {
      rules: [
        "blockquote",
        "code",
        "fence",
        "heading",
        "hr",
        "html_block",
        "lheading",
        "list",
        "reference",
        "paragraph"
      ]
    },
    inline: {
      rules: [
        "autolink",
        "backticks",
        "emphasis",
        "entity",
        "escape",
        "html_inline",
        "image",
        "link",
        "newline",
        "text"
      ],
      rules2: [
        "balance_pairs",
        "emphasis",
        "fragments_join"
      ]
    }
  }
};
const config = {
  default: cfg_default,
  zero: cfg_zero,
  commonmark: cfg_commonmark
};
const BAD_PROTO_RE = /^(vbscript|javascript|file|data):/;
const GOOD_DATA_RE = /^data:image\/(gif|png|jpeg|webp);/;
function validateLink(url) {
  const str = url.trim().toLowerCase();
  return BAD_PROTO_RE.test(str) ? GOOD_DATA_RE.test(str) : true;
}
const RECODE_HOSTNAME_FOR = ["http:", "https:", "mailto:"];
function normalizeLink(url) {
  const parsed = urlParse(url, true);
  if (parsed.hostname) {
    if (!parsed.protocol || RECODE_HOSTNAME_FOR.indexOf(parsed.protocol) >= 0) {
      try {
        parsed.hostname = punycode.toASCII(parsed.hostname);
      } catch (er2) {
      }
    }
  }
  return encode$1(format$1(parsed));
}
function normalizeLinkText(url) {
  const parsed = urlParse(url, true);
  if (parsed.hostname) {
    if (!parsed.protocol || RECODE_HOSTNAME_FOR.indexOf(parsed.protocol) >= 0) {
      try {
        parsed.hostname = punycode.toUnicode(parsed.hostname);
      } catch (er2) {
      }
    }
  }
  return decode$1(format$1(parsed), decode$1.defaultChars + "%");
}
function MarkdownIt(presetName, options) {
  if (!(this instanceof MarkdownIt)) {
    return new MarkdownIt(presetName, options);
  }
  if (!options) {
    if (!isString$1(presetName)) {
      options = presetName || {};
      presetName = "default";
    }
  }
  this.inline = new ParserInline();
  this.block = new ParserBlock();
  this.core = new Core$1();
  this.renderer = new Renderer();
  this.linkify = new LinkifyIt();
  this.validateLink = validateLink;
  this.normalizeLink = normalizeLink;
  this.normalizeLinkText = normalizeLinkText;
  this.utils = utils;
  this.helpers = assign$1({}, helpers);
  this.options = {};
  this.configure(presetName);
  if (options) {
    this.set(options);
  }
}
MarkdownIt.prototype.set = function(options) {
  assign$1(this.options, options);
  return this;
};
MarkdownIt.prototype.configure = function(presets) {
  const self = this;
  if (isString$1(presets)) {
    const presetName = presets;
    presets = config[presetName];
    if (!presets) {
      throw new Error('Wrong `markdown-it` preset "' + presetName + '", check name');
    }
  }
  if (!presets) {
    throw new Error("Wrong `markdown-it` preset, can't be empty");
  }
  if (presets.options) {
    self.set(presets.options);
  }
  if (presets.components) {
    Object.keys(presets.components).forEach(function(name) {
      if (presets.components[name].rules) {
        self[name].ruler.enableOnly(presets.components[name].rules);
      }
      if (presets.components[name].rules2) {
        self[name].ruler2.enableOnly(presets.components[name].rules2);
      }
    });
  }
  return this;
};
MarkdownIt.prototype.enable = function(list2, ignoreInvalid) {
  let result2 = [];
  if (!Array.isArray(list2)) {
    list2 = [list2];
  }
  ["core", "block", "inline"].forEach(function(chain) {
    result2 = result2.concat(this[chain].ruler.enable(list2, true));
  }, this);
  result2 = result2.concat(this.inline.ruler2.enable(list2, true));
  const missed = list2.filter(function(name) {
    return result2.indexOf(name) < 0;
  });
  if (missed.length && !ignoreInvalid) {
    throw new Error("MarkdownIt. Failed to enable unknown rule(s): " + missed);
  }
  return this;
};
MarkdownIt.prototype.disable = function(list2, ignoreInvalid) {
  let result2 = [];
  if (!Array.isArray(list2)) {
    list2 = [list2];
  }
  ["core", "block", "inline"].forEach(function(chain) {
    result2 = result2.concat(this[chain].ruler.disable(list2, true));
  }, this);
  result2 = result2.concat(this.inline.ruler2.disable(list2, true));
  const missed = list2.filter(function(name) {
    return result2.indexOf(name) < 0;
  });
  if (missed.length && !ignoreInvalid) {
    throw new Error("MarkdownIt. Failed to disable unknown rule(s): " + missed);
  }
  return this;
};
MarkdownIt.prototype.use = function(plugin) {
  const args2 = [this].concat(Array.prototype.slice.call(arguments, 1));
  plugin.apply(plugin, args2);
  return this;
};
MarkdownIt.prototype.parse = function(src, env) {
  if (typeof src !== "string") {
    throw new Error("Input data should be a String");
  }
  const state = new this.core.State(src, this, env);
  this.core.process(state);
  return state.tokens;
};
MarkdownIt.prototype.render = function(src, env) {
  env = env || {};
  return this.renderer.render(this.parse(src, env), this.options, env);
};
MarkdownIt.prototype.parseInline = function(src, env) {
  const state = new this.core.State(src, this, env);
  state.inlineMode = true;
  this.core.process(state);
  return state.tokens;
};
MarkdownIt.prototype.renderInline = function(src, env) {
  env = env || {};
  return this.renderer.render(this.parseInline(src, env), this.options, env);
};
const t = { "xmldom-sre": await __vitePreload(() => import("./lib-CBtriEt5.js"), true ? __vite__mapDeps([0,1]) : void 0, import.meta.url).then(l()), "wicked-good-xpath": await __vitePreload(() => import("./wgxpath.install-node-Csk64Aj9.js"), true ? __vite__mapDeps([2,1]) : void 0, import.meta.url).then(l()), commander: {}, fs: {} }, n = (e) => t[e];
globalThis.MathJax_require = n;
const r = { "mathjax/es5/adaptors/liteDOM.js": () => __vitePreload(() => import("./liteDOM-Cp0aN3bP.js").then((n2) => n2.l), true ? __vite__mapDeps([3,4]) : void 0, import.meta.url), "xyjax/build/xypic.js": () => __vitePreload(() => import("./xypic-DrMJn58R.js").then((n2) => n2.x), true ? __vite__mapDeps([5,4]) : void 0, import.meta.url) }, i = (e) => r[e]();
globalThis.MathJax = { loader: { source: {}, require: i, load: [`adaptors/liteDOM`, `[custom]/xypic`], paths: { mathjax: `mathjax/es5`, custom: `xyjax/build` } }, tex: { packages: { "[+]": [`xypic`] } }, svg: { fontCache: `none` }, startup: { typeset: false } }, await __vitePreload(() => import("./tex-svg-full-BI3fonbT.js").then((n2) => n2.t), true ? __vite__mapDeps([6,4]) : void 0, import.meta.url), await globalThis.MathJax.startup?.promise;
function a(e = ``, t2 = {}) {
  let n2 = globalThis.MathJax.tex2svg(e, { display: true, ...t2 }), r2 = globalThis.MathJax.startup.adaptor, i2 = r2.textContent(globalThis.MathJax.svgStylesheet()), a2 = r2.outerHTML(n2), o = `mjx-${Math.random().toString(16).substring(8)}`;
  return `
    <span id="${o}">
      <style>
      #${o}{
        display:contents;
        mjx-assistive-mml {
          user-select: text !important;
          clip: auto !important;
          color: rgba(0,0,0,0);
        }
        ${i2}
      }
      </style>
      ${a2}
    </span>
  `;
}
const import_mathxyjax3 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  tex2svgHtml: a
}, Symbol.toStringTag, { value: "Module" }));
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __esm = (fn2, res) => function() {
  return fn2 && (res = (0, fn2[__getOwnPropNames(fn2)[0]])(fn2 = 0)), res;
};
var __commonJS = (cb, mod) => function() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};
var __copyProps = (to2, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") for (var keys = __getOwnPropNames(from), i2 = 0, n2 = keys.length, key2; i2 < n2; i2++) {
    key2 = keys[i2];
    if (!__hasOwnProp.call(to2, key2) && key2 !== except) __defProp(to2, key2, {
      get: ((k2) => from[k2]).bind(null, key2),
      enumerable: !(desc = __getOwnPropDesc(from, key2)) || desc.enumerable
    });
  }
  return to2;
};
var __reExport = (target, mod, secondTarget) => (__copyProps(target, mod, "default"), secondTarget);
var mathjax_exports = {};
__reExport(mathjax_exports, import_mathxyjax3);
var init_mathjax = __esm({ "src/mathjax.mts": (() => {
}) });
var require_src = /* @__PURE__ */ __commonJS({ "src/index.ts": ((exports$12, module) => {
  init_mathjax();
  function isValidDelim(state, pos) {
    let max = state.posMax, can_open = true, can_close = true;
    const prevChar = pos > 0 ? state.src.charCodeAt(pos - 1) : -1, nextChar = pos + 1 <= max ? state.src.charCodeAt(pos + 1) : -1;
    if (prevChar === 32 || prevChar === 9 || nextChar >= 48 && nextChar <= 57) can_close = false;
    if (nextChar === 32 || nextChar === 9) can_open = false;
    return {
      can_open,
      can_close
    };
  }
  function math_inline(state, silent) {
    if (state.src[state.pos] !== "$") return false;
    let res = isValidDelim(state, state.pos);
    if (!res.can_open) {
      if (!silent) state.pending += "$";
      state.pos += 1;
      return true;
    }
    const start = state.pos + 1;
    let match2 = start;
    while ((match2 = state.src.indexOf("$", match2)) !== -1) {
      let pos = match2 - 1;
      while (state.src[pos] === "\\") pos -= 1;
      if ((match2 - pos) % 2 == 1) break;
      match2 += 1;
    }
    if (match2 === -1) {
      if (!silent) state.pending += "$";
      state.pos = start;
      return true;
    }
    if (match2 - start === 0) {
      if (!silent) state.pending += "$$";
      state.pos = start + 1;
      return true;
    }
    res = isValidDelim(state, match2);
    if (!res.can_close) {
      if (!silent) state.pending += "$";
      state.pos = start;
      return true;
    }
    if (!silent) {
      const token = state.push("math_inline", "math", 0);
      token.markup = "$";
      token.content = state.src.slice(start, match2);
    }
    state.pos = match2 + 1;
    return true;
  }
  function math_block(state, start, end, silent) {
    let next, lastPos;
    let found = false, pos = state.bMarks[start] + state.tShift[start], max = state.eMarks[start], lastLine = "";
    if (pos + 2 > max) return false;
    if (state.src.slice(pos, pos + 2) !== "$$") return false;
    pos += 2;
    let firstLine = state.src.slice(pos, max);
    if (silent) return true;
    if (firstLine.trim().slice(-2) === "$$") {
      firstLine = firstLine.trim().slice(0, -2);
      found = true;
    }
    for (next = start; !found; ) {
      next++;
      if (next >= end) break;
      pos = state.bMarks[next] + state.tShift[next];
      max = state.eMarks[next];
      if (pos < max && state.tShift[next] < state.blkIndent) break;
      if (state.src.slice(pos, max).trim().slice(-2) === "$$") {
        lastPos = state.src.slice(0, max).lastIndexOf("$$");
        lastLine = state.src.slice(pos, lastPos);
        found = true;
      }
    }
    state.line = next + 1;
    const token = state.push("math_block", "math", 0);
    token.block = true;
    token.content = (firstLine && firstLine.trim() ? firstLine + "\n" : "") + state.getLines(start + 1, next, state.tShift[start], true) + (lastLine && lastLine.trim() ? lastLine : "");
    token.map = [start, state.line];
    token.markup = "$$";
    return true;
  }
  const plugin = (md) => {
    md.inline.ruler.after("escape", "math_inline", math_inline);
    md.block.ruler.after("blockquote", "math_block", math_block, { alt: [
      "paragraph",
      "reference",
      "blockquote",
      "list"
    ] });
    md.renderer.rules.math_inline = function(tokens, idx) {
      return mathjax_exports.tex2svgHtml(tokens[idx].content, { display: false });
    };
    md.renderer.rules.math_block = function(tokens, idx) {
      return mathjax_exports.tex2svgHtml(tokens[idx].content, { display: true });
    };
  };
  plugin.default = plugin;
  module.exports = plugin;
}) });
const markdownitMathjax3 = require_src();
const MarkdownDivComponent = reactExports.forwardRef(
  ({ markdown, omitMedia, style: style2, className: className2, postProcess: postProcess2, onClick }, ref) => {
    const cacheKey = `${markdown}:${omitMedia ? "1" : "0"}`;
    const cachedHtml = renderCache.get(cacheKey);
    const applyPostProcess = (html) => {
      const processed = postProcess2 ? postProcess2(html) : html;
      return unescapeSupHtmlEntities(processed);
    };
    const [renderedHtml, setRenderedHtml] = reactExports.useState(() => {
      if (cachedHtml) {
        return applyPostProcess(cachedHtml);
      }
      return markdown.replace(/\n/g, "<br/>");
    });
    reactExports.useEffect(() => {
      if (cachedHtml) {
        const finalHtml = applyPostProcess(cachedHtml);
        if (renderedHtml !== finalHtml) {
          reactExports.startTransition(() => {
            setRenderedHtml(finalHtml);
          });
        }
        return;
      }
      setRenderedHtml(markdown.replace(/\n/g, "<br/>"));
      const { promise, cancel } = renderQueue.enqueue(async () => {
        const protectedContent = protectBackslashesInLatex(markdown);
        const escaped = escapeHtmlCharacters(protectedContent);
        const preRendered = preRenderText(escaped);
        const protectedText = protectMarkdown(preRendered);
        const preparedForMarkdown = restoreBackslashesForLatex(protectedText);
        let html = preparedForMarkdown;
        try {
          const md = omitMedia ? mdInstanceNoMedia : mdInstance;
          html = md.render(preparedForMarkdown);
        } catch (ex) {
          console.log("Unable to markdown render content");
          console.error(ex);
        }
        const unescaped = unprotectMarkdown(html);
        const finalContent = unescapeCodeHtmlEntities(unescaped);
        return Promise.resolve(finalContent);
      });
      promise.then((result2) => {
        if (renderCache.size >= MAX_CACHE_SIZE) {
          const firstKey = renderCache.keys().next().value;
          if (firstKey) {
            renderCache.delete(firstKey);
          }
        }
        renderCache.set(cacheKey, result2);
        const finalHtml = applyPostProcess(result2);
        reactExports.startTransition(() => {
          setRenderedHtml(finalHtml);
        });
      }).catch((error2) => {
        console.error("Markdown rendering error:", error2);
      });
      return () => {
        cancel();
      };
    }, [markdown, omitMedia, cachedHtml, renderedHtml, postProcess2]);
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        ref,
        dangerouslySetInnerHTML: { __html: renderedHtml },
        style: style2,
        className: clsx(className2, "markdown-content"),
        onClick
      }
    );
  }
);
MarkdownDivComponent.displayName = "MarkdownDivComponent";
const MarkdownDiv = reactExports.memo(MarkdownDivComponent);
const renderCache = /* @__PURE__ */ new Map();
const MAX_CACHE_SIZE = 500;
const mdInstance = MarkdownIt({ breaks: true, html: true }).use(
  markdownitMathjax3
);
const mdInstanceNoMedia = MarkdownIt({ breaks: true, html: true }).use(markdownitMathjax3).disable(["image"]);
class MarkdownRenderQueue {
  queue = [];
  activeCount = 0;
  maxConcurrent;
  constructor(maxConcurrent = 10) {
    this.maxConcurrent = maxConcurrent;
  }
  enqueue(task) {
    let cancelled = false;
    const promise = new Promise((resolve, reject) => {
      const wrappedTask = async () => {
        if (cancelled) {
          return;
        }
        try {
          const result2 = await task();
          if (!cancelled) {
            resolve(result2);
          }
        } catch (error2) {
          if (!cancelled) {
            reject(error2 instanceof Error ? error2 : new Error(String(error2)));
          }
        }
      };
      const queueTask = {
        task: wrappedTask,
        cancelled: false
      };
      this.queue.push(queueTask);
      void this.processQueue();
    });
    const cancel = () => {
      cancelled = true;
      const index = this.queue.findIndex((t2) => !t2.cancelled);
      if (index !== -1 && this.queue[index]) {
        this.queue[index].cancelled = true;
      }
    };
    return { promise, cancel };
  }
  async processQueue() {
    if (this.activeCount >= this.maxConcurrent || this.queue.length === 0) {
      return;
    }
    let queueTask;
    while (this.queue.length > 0) {
      const task = this.queue.shift();
      if (task && !task.cancelled) {
        queueTask = task;
        break;
      }
    }
    if (!queueTask) {
      return;
    }
    this.activeCount++;
    try {
      await queueTask.task();
    } finally {
      this.activeCount--;
      void this.processQueue();
    }
  }
}
const renderQueue = new MarkdownRenderQueue(10);
const kLetterListPattern = /^([a-zA-Z][).]\s.*?)$/gm;
const kCommonmarkReferenceLinkPattern = /\[([^\]]*)\]: (?!http)(.*)/g;
const protectBackslashesInLatex = (content2) => {
  if (!content2) return content2;
  try {
    const inlineRegex = /\$(.*?)\$/g;
    const blockRegex = /\$\$([\s\S]*?)\$\$/g;
    let result2 = content2.replace(inlineRegex, (_match, latex) => {
      const protectedTex = latex.replace(/\\/g, "___LATEX_BACKSLASH___").replace(/</g, "___LATEX_LT___").replace(/>/g, "___LATEX_GT___").replace(/&/g, "___LATEX_AMP___").replace(/'/g, "___LATEX_APOS___").replace(/"/g, "___LATEX_QUOT___");
      return `$${protectedTex}$`;
    });
    result2 = result2.replace(blockRegex, (_match, latex) => {
      const protectedTex = latex.replace(/\\/g, "___LATEX_BACKSLASH___").replace(/</g, "___LATEX_LT___").replace(/>/g, "___LATEX_GT___").replace(/&/g, "___LATEX_AMP___").replace(/'/g, "___LATEX_APOS___").replace(/"/g, "___LATEX_QUOT___");
      return `$$${protectedTex}$$`;
    });
    return result2;
  } catch (error2) {
    console.error("Error protecting LaTeX content:", error2);
    return content2;
  }
};
const restoreBackslashesForLatex = (content2) => {
  if (!content2) {
    return content2;
  }
  try {
    let result2 = content2.replace(/___LATEX_BACKSLASH___/g, "\\").replace(/___LATEX_LT___/g, "<").replace(/___LATEX_GT___/g, ">").replace(/___LATEX_AMP___/g, "&").replace(/___LATEX_APOS___/g, "'").replace(/___LATEX_QUOT___/g, '"');
    result2 = fixDotsNotation(result2);
    return result2;
  } catch (error2) {
    console.error("Error restoring LaTeX content:", error2);
    return content2;
  }
};
const fixDotsNotation = (content2) => {
  if (!content2) return content2;
  try {
    let result2 = content2.replace(/(\$[^$]*?)\\dots([^$]*?\$)/g, "$1\\ldots$2");
    result2 = result2.replace(/(\$\$[^$]*?)\\dots([^$]*?\$\$)/g, "$1\\ldots$2");
    return result2;
  } catch (error2) {
    console.error("Error fixing dots notation:", error2);
    return content2;
  }
};
const escapeHtmlCharacters = (content2) => {
  if (!content2) return content2;
  return content2.replace(/[<>&'"]/g, (c) => {
    switch (c) {
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case "&":
        return "&amp;";
      case "'":
        return "&apos;";
      case '"':
        return "&quot;";
      default:
        throw new Error("Matched a value that isn't replaceable");
    }
  });
};
const preRenderText = (txt) => {
  if (!txt) return txt;
  txt = txt.replace(/^[\u200B\u200C\u200D\u200E\u200F\uFEFF]/, "");
  return txt.replaceAll(
    kLetterListPattern,
    "<p class='markdown-ordered-list-item'>$1</p>"
  );
};
const protectMarkdown = (txt) => {
  if (!txt) return txt;
  return txt.replaceAll(
    kCommonmarkReferenceLinkPattern,
    "(open:767A125E)$1(close:767A125E) $2 "
  );
};
const unprotectMarkdown = (txt) => {
  if (!txt) return txt;
  txt = txt.replaceAll("(open:767A125E)", "[");
  txt = txt.replaceAll("(close:767A125E)", "]");
  return txt;
};
function unescapeSupHtmlEntities(str) {
  if (!str) {
    return str;
  }
  return str.replace(/&lt;sup&gt;/g, "<sup>").replace(/&lt;\/sup&gt;/g, "</sup>");
}
function unescapeCodeHtmlEntities(str) {
  if (!str) return str;
  const htmlEntities = {
    "&lt;": "<",
    "&gt;": ">",
    "&amp;": "&",
    "&#x5C;": "\\",
    "&quot;": '"'
  };
  return str.replace(
    /(<code[^>]*>)([\s\S]*?)(<\/code>)/gi,
    (_match, starttag, content2, endtag) => {
      return starttag + content2.replace(
        /&(?:amp|lt|gt|quot|#39|#x2F|#x5C|#96);/g,
        (entity2) => htmlEntities[entity2] || entity2
      ) + endtag;
    }
  );
}
const cite = "_cite_1t1bm_1";
const styles$F = {
  cite
};
const MarkdownDivWithReferences = reactExports.forwardRef(({ markdown, references, options, className: className2, style: style2, omitMedia }, ref) => {
  const containerRef = reactExports.useRef(null);
  const [positionEl, setPositionEl] = reactExports.useState(null);
  const [currentRef, setCurrentRef] = reactExports.useState(null);
  const showingRefPopover = useStore((state) => state.showingRefPopover);
  const setShowingRefPopover = useStore((state) => state.setShowingRefPopover);
  const clearShowingRefPopover = useStore(
    (state) => state.clearShowingRefPopover
  );
  const refMap = reactExports.useMemo(
    () => new Map(references?.map((ref2) => [ref2.id, ref2])),
    [references]
  );
  const navigate = useLoggingNavigate("MarkdownDivWithReferences");
  const handleLinkClick = reactExports.useCallback(
    (e) => {
      const anchor = e.target.closest("a");
      if (anchor) {
        const href = anchor.getAttribute("href");
        if (href?.startsWith("#/")) {
          e.preventDefault();
          void navigate(href.slice(1));
        }
      }
    },
    [navigate]
  );
  const postProcess2 = reactExports.useCallback(
    (html) => {
      let processedHtml = html;
      references?.forEach((ref2) => {
        const escapedCite = ref2.cite.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const regex2 = new RegExp(`${escapedCite}(?![a-zA-Z0-9])`, "g");
        const href = ref2.citeUrl || "javascript:void(0)";
        const replacement = `<a href="${href}" class="${styles$F.cite}" data-ref-id="${ref2.id}">${ref2.cite}</a>`;
        processedHtml = processedHtml.replace(regex2, replacement);
      });
      return processedHtml;
    },
    [references, styles$F.cite]
  );
  const memoizedMarkdown = reactExports.useMemo(
    () => /* @__PURE__ */ jsxRuntimeExports.jsx(
      MarkdownDiv,
      {
        ref,
        markdown,
        postProcess: postProcess2,
        style: style2,
        omitMedia,
        onClick: handleLinkClick
      }
    ),
    [markdown, postProcess2]
  );
  reactExports.useEffect(() => {
    const container2 = containerRef.current;
    if (!container2) {
      return;
    }
    if (options?.previewRefsOnHover === false) {
      return;
    }
    const citeLinks = container2.querySelectorAll(
      `.${styles$F.cite}`
    );
    const handleMouseEnter = (e) => {
      const el = e.currentTarget;
      const id = el.getAttribute("data-ref-id");
      if (!id) {
        return;
      }
      const ref2 = refMap.get(id);
      if (!ref2) {
        return;
      }
      if (!ref2.citePreview) {
        return;
      }
      setPositionEl(el);
      setCurrentRef(ref2);
      setShowingRefPopover(popoverKey(ref2));
    };
    const handleClick = (e) => {
      clearShowingRefPopover();
      setCurrentRef(null);
      setPositionEl(null);
      e.stopPropagation();
    };
    const cleanup = [];
    citeLinks.forEach((link2) => {
      link2.addEventListener("mouseenter", handleMouseEnter);
      link2.addEventListener("click", handleClick);
      cleanup.push(() => {
        link2.removeEventListener("mouseenter", handleMouseEnter);
        link2.removeEventListener("click", handleClick);
      });
    });
    return () => {
      cleanup.forEach((fn2) => fn2());
    };
  }, [
    markdown,
    refMap,
    styles$F.cite,
    setPositionEl,
    setCurrentRef,
    setShowingRefPopover,
    clearShowingRefPopover
  ]);
  const key2 = currentRef ? popoverKey(currentRef) : "unknown-markdown-ref-popover";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(className2), ref: containerRef, children: [
    memoizedMarkdown,
    positionEl && currentRef && /* @__PURE__ */ jsxRuntimeExports.jsx(
      PopOver,
      {
        id: key2,
        positionEl,
        isOpen: showingRefPopover === key2,
        setIsOpen: (isOpen) => {
          if (!isOpen) {
            clearShowingRefPopover();
            setCurrentRef(null);
            setPositionEl(null);
          }
        },
        placement: "auto",
        hoverDelay: 400,
        showArrow: true,
        children: currentRef.citePreview && currentRef.citePreview() || /* @__PURE__ */ jsxRuntimeExports.jsx(NoContentsPanel, { text: "No preview available." })
      }
    )
  ] });
});
MarkdownDivWithReferences.displayName = "MarkdownDivWithReferences";
const popoverKey = (ref) => `markdown-ref-popover-${ref.id}`;
const content$1 = "_content_13ihw_1";
const styles$E = {
  content: content$1
};
const Preformatted = reactExports.forwardRef(
  ({ text: text2, style: style2, className: className2 }, ref) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      "pre",
      {
        ref,
        className: clsx(styles$E.content, "text-size-smaller", className2),
        style: style2,
        children: text2
      }
    );
  }
);
Preformatted.displayName = "Preformatted";
const DisplayModeContext = reactExports.createContext(
  null
);
const useDisplayMode = () => {
  const context = reactExports.useContext(DisplayModeContext);
  return context?.displayMode ?? "rendered";
};
const RenderedText = reactExports.forwardRef(
  ({ markdown, references, style: style2, className: className2, forceRender, omitMedia, options }, ref) => {
    const displayMode = useDisplayMode();
    if (forceRender || displayMode === "rendered") {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        MarkdownDivWithReferences,
        {
          ref,
          markdown,
          references,
          options,
          style: style2,
          className: className2,
          omitMedia
        }
      );
    } else {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        Preformatted,
        {
          ref,
          text: markdown,
          style: style2,
          className: className2
        }
      );
    }
  }
);
RenderedText.displayName = "RenderedText";
const title$3 = "_title_1pwo3_1";
const content = "_content_1pwo3_11";
const grid$2 = "_grid_1pwo3_16";
const styles$D = {
  title: title$3,
  content,
  grid: grid$2
};
const kCompactionMetadata = "compaction_metadata";
const CompactionData = ({ id, data }) => {
  const compactionMetadata = data[kCompactionMetadata];
  let compactionContent = void 0;
  if (compactionMetadata.type === "anthropic_compact") {
    compactionContent = /* @__PURE__ */ jsxRuntimeExports.jsx(ExpandablePanel, { id: `${id}-compacted-content`, collapse: true, children: /* @__PURE__ */ jsxRuntimeExports.jsx(RenderedText, { markdown: String(compactionMetadata.content) }) });
  } else {
    compactionContent = /* @__PURE__ */ jsxRuntimeExports.jsx(
      MetaDataGrid,
      {
        id: `${id}-compacted-content-metadata`,
        className: styles$D.grid,
        entries: compactionMetadata
      }
    );
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$D.content, "text-size-small"), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: clsx(
          "text-style-label",
          "text-style-secondary",
          styles$D.title
        ),
        children: "Compacted Content"
      }
    ),
    compactionContent
  ] });
};
const contentData = "_contentData_1lrx1_1";
const styles$C = {
  contentData
};
const webSearch = "_webSearch_1376z_1";
const query$1 = "_query_1376z_8";
const styles$B = {
  webSearch,
  query: query$1
};
const WebSearch = ({ query: query2 }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$B.webSearch, "text-size-smaller"), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx("text-style-label", "text-style-secondary"), children: "Web Search:" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx(styles$B.query, "text-size-smallest"), children: query2 })
  ] });
};
const result$1 = "_result_1mixg_12";
const styles$A = {
  result: result$1
};
const WebSearchResults = ({
  results
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: clsx(
          styles$A.label,
          "text-style-label",
          "text-style-secondary",
          "text-size-smaller"
        ),
        children: "Results"
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx("ol", { className: clsx(styles$A.results, "text-size-smaller"), children: results.map((result2, index) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      "li",
      {
        className: clsx(styles$A.result, "text-style-secondary"),
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "a",
          {
            href: result2.url,
            target: "_blank",
            rel: "noopener noreferrer",
            title: result2.url + (result2.page_age ? `
(Age: ${result2.page_age})` : ""),
            children: result2.title
          }
        )
      },
      index
    )) })
  ] });
};
const ContentDataView = ({ id, contentData: contentData2 }) => {
  const renderableData = contentData2.data;
  const renderer = contentDataRenderers.find(
    (r2) => r2.canRender(renderableData)
  );
  if (!renderer) {
    const { encrypted_content, ...record } = renderableData;
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$C.contentData), children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      RecordTree,
      {
        id: `${id}-tree`,
        record,
        className: clsx(styles$C.data),
        defaultExpandLevel: 0
      }
    ) });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$C.contentData), children: renderer.render(id, renderableData) });
};
const compactionDataRenderer = {
  name: "Compaction",
  canRender: (data) => {
    return Object.hasOwn(data, kCompactionMetadata);
  },
  render: (id, data) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(CompactionData, { id, data });
  }
};
const webSearchServerToolRenderer = {
  name: "WebSearch",
  canRender: (data) => {
    return data.type === "server_tool_use" && data.name === "web_search";
  },
  render: (_id, data) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(WebSearch, { query: data.input.query });
  }
};
const webSearchResultsServerToolRenderer = {
  name: "WebSearchResults",
  canRender: (data) => {
    return data.type === "web_search_tool_result" && Array.isArray(data.content);
  },
  render: (_id, data) => {
    const results = data.content;
    return /* @__PURE__ */ jsxRuntimeExports.jsx(WebSearchResults, { results });
  }
};
const serverToolRenderer = {
  name: "ServerTool",
  canRender: (data) => data.type === "server_tool_use",
  render: (id, data) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: clsx(
            "text-style-label",
            "text-style-secondary",
            "text-size-smaller"
          ),
          children: "Server Tool"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        RecordTree,
        {
          id: `${id}-server-tool`,
          record: data,
          className: clsx(styles$C.data)
        }
      )
    ] });
  }
};
const contentDataRenderers = [
  compactionDataRenderer,
  webSearchServerToolRenderer,
  webSearchResultsServerToolRenderer,
  serverToolRenderer
];
const documentFrame = "_documentFrame_1576h_1";
const documentFrameTitle = "_documentFrameTitle_1576h_9";
const downloadLink = "_downloadLink_1576h_16";
const imageDocument = "_imageDocument_1576h_21";
const styles$z = {
  documentFrame,
  documentFrameTitle,
  downloadLink,
  imageDocument
};
const ContentDocumentView = ({
  id,
  document: document2
}) => {
  const canDownloadFiles = false;
  if (isImage(document2.mime_type || "")) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(ContentDocumentFrame, { document: document2, downloadable: canDownloadFiles, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      "img",
      {
        className: clsx(styles$z.imageDocument),
        src: document2.document,
        alt: document2.filename,
        id
      }
    ) });
  } else {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      ContentDocumentFrame,
      {
        document: document2,
        downloadable: canDownloadFiles
      }
    );
  }
};
const ContentDocumentFrame = ({
  document: document2,
  children: children2,
  downloadable
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: clsx(
        styles$z.documentFrame,
        "text-size-small",
        "text-style-secondary"
      ),
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$z.documentFrameTitle), children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(iconForMimeType(document2.mime_type || "")) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: downloadable ? /* @__PURE__ */ jsxRuntimeExports.jsx(
            "a",
            {
              className: clsx(styles$z.downloadLink),
              onClick: () => {
              },
              children: document2.filename
            }
          ) : document2.filename })
        ] }),
        children2
      ]
    }
  );
};
const jsonMessage = "_jsonMessage_oxf8d_1";
const styles$y = {
  jsonMessage
};
const JsonMessageContent = ({
  id,
  json,
  className: className2
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    RecordTree,
    {
      id,
      record: json,
      className: clsx(styles$y.jsonMessage, className2),
      useBorders: false
    }
  );
};
const citations = "_citations_1ggvf_1";
const citationLink = "_citationLink_1ggvf_9";
const styles$x = {
  citations,
  citationLink
};
const MessageCitations = ({ citations: citations2 }) => {
  if (citations2.length === 0) {
    return void 0;
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$x.citations, "text-size-smallest"), children: citations2.map((citation, index) => /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: index + 1 }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(MessageCitation, { citation })
  ] }, index)) });
};
const MessageCitation = ({ citation }) => {
  const innards = decodeHtmlEntities(
    citation.title ?? (typeof citation.cited_text === "string" ? citation.cited_text : citation.type === "url" ? citation.url : "")
  );
  return citation.type === "url" ? /* @__PURE__ */ jsxRuntimeExports.jsx(UrlCitation, { citation, children: innards }) : /* @__PURE__ */ jsxRuntimeExports.jsx(OtherCitation, { children: innards });
};
const UrlCitation = ({
  children: children2,
  citation
}) => /* @__PURE__ */ jsxRuntimeExports.jsx(
  "a",
  {
    href: citation.url,
    target: "_blank",
    rel: "noopener noreferrer",
    className: clsx(styles$x.citationLink),
    title: citation.cited_text && typeof citation.cited_text === "string" ? `${citation.cited_text}
${citation.url}` : citation.url,
    children: children2
  }
);
const OtherCitation = ({ children: children2 }) => /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: children2 });
const contentImage = "_contentImage_8rgix_1";
const reasoning = "_reasoning_8rgix_6";
const styles$w = {
  contentImage,
  reasoning
};
const mcpToolUse = "_mcpToolUse_1792k_1";
const title$2 = "_title_1792k_9";
const titleText = "_titleText_1792k_18";
const args = "_args_1792k_22";
const argLabel = "_argLabel_1792k_31";
const error = "_error_1792k_35";
const toolPanel = "_toolPanel_1792k_40";
const styles$v = {
  mcpToolUse,
  title: title$2,
  titleText,
  args,
  argLabel,
  error,
  toolPanel
};
const ServerToolCall = ({
  id,
  content: content2,
  className: className2
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(McpToolUse, { id, content: content2, className: className2 });
};
const McpToolUse = ({ id, content: content2, className: className2 }) => {
  const args2 = resolveArgs(content2);
  const titleStr = content2.context ? `${content2.context} — ${content2.name}()` : `${content2.name}()`;
  const listToolsResult = maybeListTools(content2);
  const webSearchResult = maybeWebSearchResult(content2);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { id, className: clsx(styles$v.mcpToolUse, className2), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(
          styles$v.title,
          "text-size-small",
          "text-style-secondary"
        ),
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.role.tool }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: styles$v.titleText, children: titleStr }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$v.type, children: content2.type })
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$v.args, children: [
      Object.keys(args2).map((key2, index) => {
        const value2 = args2[key2];
        let valueRecord = void 0;
        if (Array.isArray(value2)) {
          valueRecord = {};
          for (let i2 = 0; i2 < value2.length; i2++) {
            valueRecord[`[${i2}]`] = value2[i2];
          }
        } else if (value2 && typeof value2 === "object") {
          valueRecord = value2;
        }
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(LabelDiv, { label: key2 }),
          valueRecord ? /* @__PURE__ */ jsxRuntimeExports.jsx(RecordTree, { id: `${id}-val-${index}`, record: valueRecord }) : /* @__PURE__ */ jsxRuntimeExports.jsx(ValueDiv, { children: value2 })
        ] });
      }),
      webSearchResult ? /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(LabelDiv, { label: "results" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(ValueDiv, { children: webSearchResult.result.map((result2, index) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$v.result, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "a",
          {
            href: result2.url,
            target: "_blank",
            rel: "noopener noreferrer",
            children: result2.title
          }
        ) }, index)) })
      ] }) : void 0,
      listToolsResult ? listToolsResult.result.map((tool2, index) => /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
        ExpandablePanel,
        {
          id: `${id}-output`,
          collapse: true,
          className: clsx(styles$v.toolPanel),
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(LabelDiv, { label: tool2.name }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(ValueDiv, { children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: tool2.description }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                RecordTree,
                {
                  id: `${id}-tool-${index}`,
                  record: { schema: tool2.input_schema },
                  defaultExpandLevel: 0
                }
              )
            ] })
          ]
        }
      ) })) : void 0
    ] }),
    content2.error ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$v.error, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
      "Error: ",
      content2.error
    ] }) }) : !listToolsResult && !webSearchResult ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-small"), children: /* @__PURE__ */ jsxRuntimeExports.jsx(ExpandablePanel, { id: `${id}-output`, collapse: true, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      RenderedContent,
      {
        id: `${id}-output`,
        entry: { name: "Output", value: content2.result },
        renderOptions: { renderString: "markdown" }
      }
    ) }) }) : void 0
  ] });
};
const resolveArgs = (content2) => {
  if (typeof content2.arguments === "string") {
    if (isJson(content2.arguments)) {
      try {
        return JSON.parse(content2.arguments);
      } catch (e) {
        console.warn("Failed to parse arguments as JSON", e);
      }
    }
    if (content2.arguments) {
      return { arguments: content2.arguments };
    }
    return {};
  } else if (typeof content2.arguments === "object") {
    return content2.arguments;
  } else if (content2.arguments) {
    return { arguments: content2.arguments };
  } else {
    return {};
  }
};
const maybeWebSearchResult = (content2) => {
  if (content2.name !== "web_search") {
    return void 0;
  }
  const objArray = asJsonObjArray(content2.result);
  if (objArray !== void 0) {
    return { result: objArray };
  }
};
const maybeListTools = (content2) => {
  if (content2.name !== "mcp_list_tools") {
    return void 0;
  }
  const objArray = asJsonObjArray(content2.result);
  if (objArray !== void 0) {
    return { result: objArray };
  }
};
const LabelDiv = ({ label: label2 }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: clsx(
        styles$v.argLabel,
        "text-style-secondary",
        "text-size-smaller"
      ),
      children: /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { children: label2 })
    }
  );
};
const ValueDiv = ({ children: children2 }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-smaller"), children: children2 });
};
const toolImage = "_toolImage_qu6a9_1";
const output = "_output_qu6a9_6";
const textOutput = "_textOutput_qu6a9_10";
const textCode = "_textCode_qu6a9_18";
const styles$u = {
  toolImage,
  output,
  textOutput,
  textCode
};
const ToolOutput = ({ output: output2, className: className2 }) => {
  if (!output2) {
    return null;
  }
  const outputs = [];
  if (Array.isArray(output2)) {
    output2.forEach((out, idx) => {
      const key2 = `tool-output-${idx}`;
      if (out.type === "text") {
        outputs.push(/* @__PURE__ */ jsxRuntimeExports.jsx(ToolTextOutput, { text: out.text }, key2));
      } else {
        if (out.image.startsWith("data:")) {
          outputs.push(
            /* @__PURE__ */ jsxRuntimeExports.jsx("img", { className: clsx(styles$u.toolImage), src: out.image }, key2)
          );
        } else {
          outputs.push(/* @__PURE__ */ jsxRuntimeExports.jsx(ToolTextOutput, { text: String(out.image) }, key2));
        }
      }
    });
  } else {
    outputs.push(
      /* @__PURE__ */ jsxRuntimeExports.jsx(ToolTextOutput, { text: String(output2) }, "tool-output-single")
    );
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$u.output, className2), children: outputs });
};
const ToolTextOutput = ({ text: text2 }) => {
  if (isJson(text2)) {
    const obj = JSON.parse(text2);
    return /* @__PURE__ */ jsxRuntimeExports.jsx(JsonMessageContent, { id: `1-json`, json: obj });
  }
  if (isAnsiOutput(text2)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(ANSIDisplay, { className: styles$u.ansiOutput, output: text2 });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: clsx(styles$u.textOutput, "tool-output"), children: /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: clsx("sourceCode", styles$u.textCode), children: text2.trim() }) });
};
const isMessageContent = (content2) => {
  return typeof content2 === "object" && content2 !== null && "type" in content2 && typeof content2.type === "string";
};
const MessageContent = ({
  contents: contents2,
  context
}) => {
  const normalized = normalizeContent$2(contents2);
  if (Array.isArray(normalized)) {
    return normalized.map((content2, index) => {
      if (typeof content2 === "string") {
        return messageRenderers["text"]?.render(
          `text-content-${index}`,
          {
            type: "text",
            text: content2,
            refusal: null,
            internal: null,
            citations: null
          },
          index === contents2.length - 1,
          context
        );
      } else {
        if (content2) {
          const renderer = messageRenderers[content2.type];
          if (renderer) {
            return renderer.render(
              `text-${content2.type}-${index}`,
              content2,
              index === contents2.length - 1,
              context
            );
          } else {
            console.error(`Unknown message content type '${content2.type}'`);
          }
        }
      }
    });
  } else {
    const contentText = {
      type: "text",
      text: normalized,
      refusal: null,
      internal: null,
      citations: null
    };
    return messageRenderers["text"]?.render(
      "text-message-content",
      contentText,
      true,
      context
    );
  }
};
const messageRenderers = {
  text: {
    render: (key2, content2, isLast, _context) => {
      const c = content2;
      const cites = c.citations ?? [];
      if (!c.text && !cites.length) {
        return void 0;
      }
      const purgeInternalContainers = (text2) => {
        const internalTags = ["internal", "content-internal", "think"];
        internalTags.forEach((tag) => {
          const regex2 = new RegExp(`<${tag}[^>]*>[\\s\\S]*?<\\/${tag}>`, "gm");
          text2 = text2.replace(regex2, "");
        });
        return text2.trim();
      };
      if (isJson(c.text)) {
        const obj = JSON.parse(c.text);
        return /* @__PURE__ */ jsxRuntimeExports.jsx(JsonMessageContent, { id: `${key2}-json`, json: obj });
      } else {
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            RenderedText,
            {
              markdown: purgeInternalContainers(c.text) || "",
              className: isLast ? "no-last-para-padding" : ""
            }
          ),
          c.citations && c.citations.length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx(MessageCitations, { citations: c.citations }) : void 0
        ] }, key2);
      }
    }
  },
  reasoning: {
    render: (key2, content2, isLast, _context) => {
      const r2 = content2;
      let text2 = r2.reasoning;
      if (r2.redacted) {
        text2 = r2.summary || "Reasoning encrypted by model provider.";
      } else if (!text2) {
        text2 = r2.summary || "Reasoning text not provided.";
      }
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$w.reasoning, "text-size-small"), children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              "text-style-label",
              "text-style-secondary",
              isLast ? "no-last-para-padding" : ""
            ),
            children: "Reasoning"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(ExpandablePanel, { id: `${key2}-reasoning`, collapse: true, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(RenderedText, { markdown: text2 }),
          " "
        ] })
      ] }, key2);
    }
  },
  image: {
    render: (key2, content2, _isLast, _context) => {
      const c = content2;
      if (c.image.startsWith("data:")) {
        return /* @__PURE__ */ jsxRuntimeExports.jsx("img", { src: c.image, className: styles$w.contentImage }, key2);
      } else {
        return /* @__PURE__ */ jsxRuntimeExports.jsx("code", { children: c.image }, key2);
      }
    }
  },
  audio: {
    render: (key2, content2, _isLast, _context) => {
      const c = content2;
      return /* @__PURE__ */ jsxRuntimeExports.jsx("audio", { controls: true, children: /* @__PURE__ */ jsxRuntimeExports.jsx("source", { src: c.audio, type: mimeTypeForFormat(c.format) }) }, key2);
    }
  },
  video: {
    render: (key2, content2, _isLast, _context) => {
      const c = content2;
      return /* @__PURE__ */ jsxRuntimeExports.jsx("video", { width: "500", height: "375", controls: true, children: /* @__PURE__ */ jsxRuntimeExports.jsx("source", { src: c.video, type: mimeTypeForFormat(c.format) }) }, key2);
    }
  },
  tool: {
    render: (key2, content2, _isLast, _context) => {
      const c = content2;
      return /* @__PURE__ */ jsxRuntimeExports.jsx(ToolOutput, { output: c.content }, key2);
    }
  },
  // server-side tool use
  tool_use: {
    render: (key2, content2, _isLast, _context) => {
      const c = content2;
      return /* @__PURE__ */ jsxRuntimeExports.jsx(ServerToolCall, { id: key2, content: c });
    }
  },
  data: {
    render: (key2, content2, _isLast, _context) => {
      const c = content2;
      return /* @__PURE__ */ jsxRuntimeExports.jsx(ContentDataView, { id: key2, contentData: c });
    }
  },
  document: {
    render: (key2, content2, _isLast, _context) => {
      const c = content2;
      return /* @__PURE__ */ jsxRuntimeExports.jsx(ContentDocumentView, { id: key2, document: c });
    }
  }
};
const mimeTypeForFormat = (format2) => {
  switch (format2) {
    case "mov":
      return "video/quicktime";
    case "wav":
      return "audio/wav";
    case "mp3":
      return "audio/mpeg";
    case "mp4":
      return "video/mp4";
    case "mpeg":
      return "video/mpeg";
    default:
      return "video/mp4";
  }
};
const normalizeContent$2 = (contents2) => {
  if (typeof contents2 === "string") {
    return contents2;
  }
  if (contents2.length > 0 && typeof contents2[0] === "string") {
    return contents2;
  }
  const result2 = [];
  const collection = [];
  const collect = () => {
    if (collection.length > 0) {
      const filteredCitations = collection.flatMap((c) => c.citations || []);
      let citeCount = 0;
      const textWithCites = collection.map((c) => {
        const positionalCites = (c.citations ?? []).filter(isCitationWithRange).sort((a2, b) => b.cited_text[1] - a2.cited_text[1]);
        const endCites = c.citations?.filter(
          (citation) => !isCitationWithRange(citation)
        );
        let textWithCites2 = c.text;
        for (let i2 = 0; i2 < positionalCites.length; i2++) {
          const end_index = positionalCites[i2]?.cited_text[1];
          textWithCites2 = textWithCites2.slice(0, end_index) + `<sup>${positionalCites.length - i2}</sup>` + textWithCites2.slice(end_index);
        }
        citeCount = citeCount + positionalCites.length;
        const citeText = endCites?.map((_citation) => `${++citeCount}`);
        let inlineCites = "";
        if (citeText && citeText.length > 0) {
          inlineCites = `<sup>${citeText.join(",")}</sup>`;
        }
        return (textWithCites2 || "") + inlineCites;
      }).join("");
      result2.push({
        type: "text",
        text: textWithCites,
        refusal: null,
        internal: null,
        citations: filteredCitations
      });
      collection.length = 0;
    }
  };
  for (const content2 of contents2) {
    if (typeof content2 === "string") {
      result2.push({
        type: "text",
        text: content2,
        refusal: null,
        internal: null,
        citations: null
      });
      continue;
    }
    if (content2.type === "text") {
      collection.push(content2);
      continue;
    } else {
      collect();
      result2.push(content2);
    }
  }
  collect();
  return result2;
};
const isCitationWithRange = (citation) => Array.isArray(citation.cited_text);
const defaultContext = () => {
  return {
    citeOffset: 0,
    citations: []
  };
};
const MessageContents = ({ message: message2 }) => {
  const context = defaultContext();
  return /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: message2.content && /* @__PURE__ */ jsxRuntimeExports.jsx(MessageContent, { contents: message2.content, context }) });
};
const ChatMessage = reactExports.memo(
  ({ id, message: message2, indented: indented2, allowLinking = true }) => {
    const { getFullMessageUrl } = useTranscriptNavigation();
    const messageUrl = isHostedEnvironment() ? getFullMessageUrl(message2.id || "") : void 0;
    const collapse = message2.role === "system" || message2.role === "user";
    const [mouseOver, setMouseOver] = reactExports.useState(false);
    return /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(
          message2.role,
          "text-size-base",
          styles$G.message,
          message2.role === "system" ? styles$G.systemRole : void 0,
          message2.role === "user" ? styles$G.userRole : void 0,
          mouseOver ? styles$G.hover : void 0
        ),
        onMouseEnter: () => setMouseOver(true),
        onMouseLeave: () => setMouseOver(false),
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "div",
            {
              className: clsx(
                styles$G.messageGrid,
                message2.role === "tool" ? styles$G.toolMessageGrid : void 0,
                "text-style-label"
              ),
              children: [
                message2.role,
                message2.role === "tool" ? `: ${message2.function}` : "",
                messageUrl && allowLinking ? /* @__PURE__ */ jsxRuntimeExports.jsx(
                  CopyButton,
                  {
                    icon: ApplicationIcons.link,
                    value: messageUrl,
                    className: clsx(styles$G.copyLink)
                  }
                ) : ""
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "div",
            {
              className: clsx(
                styles$G.messageContents,
                indented2 ? styles$G.indented : void 0
              ),
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  ExpandablePanel,
                  {
                    id: `${id}-message`,
                    collapse,
                    lines: collapse ? 15 : 25,
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(MessageContents, { message: message2 }, `${id}-contents`)
                  }
                ),
                message2.metadata && Object.keys(message2.metadata).length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
                  LabeledValue,
                  {
                    label: "Metadata",
                    className: clsx(styles$G.metadataLabel, "text-size-smaller"),
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                      RecordTree,
                      {
                        record: message2.metadata,
                        id: `${id}-metadata`,
                        defaultExpandLevel: 0
                      }
                    )
                  }
                ) : ""
              ]
            }
          )
        ]
      }
    );
  }
);
const grid$1 = "_grid_17ltx_1";
const number = "_number_17ltx_8";
const user = "_user_17ltx_12";
const container$3 = "_container_17ltx_18";
const first = "_first_17ltx_26";
const last$1 = "_last_17ltx_33";
const label$1 = "_label_17ltx_40";
const highlight = "_highlight_17ltx_44";
const bottomMargin = "_bottomMargin_17ltx_48";
const styles$t = {
  grid: grid$1,
  number,
  user,
  container: container$3,
  first,
  last: last$1,
  label: label$1,
  highlight,
  bottomMargin
};
const kToolTodoContentType = "agent/todo-list";
const resolveToolInput = (fn2, toolArgs) => {
  const toolName = fn2;
  const inputDescriptor = extractInputMetadata(toolName);
  const { input, description: description2, args: args2 } = extractInput(toolArgs, inputDescriptor);
  const functionCall = args2.length > 0 ? `${toolName}(${args2.join(", ")})` : toolName;
  return {
    name: fn2,
    functionCall,
    input,
    description: description2,
    contentType: inputDescriptor?.contentType
  };
};
const extractInputMetadata = (toolName) => {
  if (toolName === "bash") {
    return {
      inputArg: "cmd",
      contentType: "bash"
    };
  } else if (toolName === "python") {
    return {
      inputArg: "code",
      contentType: "python"
    };
  } else if (toolName === "web_search") {
    return {
      inputArg: "query",
      contentType: "json"
    };
  } else if (toolName === "Bash") {
    return {
      inputArg: "command",
      descriptionArg: "description",
      contentType: "bash"
    };
  } else if (toolName === "shell") {
    return {
      inputArg: "command",
      contentType: "bash",
      inputToStr: (input) => {
        if (Array.isArray(input)) {
          return input.join(" ");
        }
        return void 0;
      }
    };
  } else if (toolName == "TodoWrite") {
    return {
      inputArg: "todos",
      contentType: kToolTodoContentType
    };
  } else if (toolName == "update_plan") {
    return {
      inputArg: "plan",
      contentType: kToolTodoContentType
    };
  } else {
    return void 0;
  }
};
const extractInput = (args2, inputDescriptor) => {
  const formatArg = (key2, value2) => {
    const quotedValue = value2 === null ? "None" : typeof value2 === "string" ? `"${value2}"` : typeof value2 === "object" || Array.isArray(value2) ? JSON.stringify(value2, void 0, 2) : String(value2);
    return `${key2}: ${quotedValue}`;
  };
  if (!args2) {
    return {
      args: []
    };
  }
  if (inputDescriptor) {
    const filterKeys = /* @__PURE__ */ new Set();
    const base2 = {};
    if (inputDescriptor.inputArg && args2[inputDescriptor.inputArg]) {
      filterKeys.add(inputDescriptor.inputArg);
      base2.input = inputDescriptor.inputToStr ? inputDescriptor.inputToStr(args2[inputDescriptor.inputArg]) || args2[inputDescriptor.inputArg] : args2[inputDescriptor.inputArg];
    }
    if (inputDescriptor.descriptionArg && args2[inputDescriptor.descriptionArg]) {
      filterKeys.add(inputDescriptor.descriptionArg);
      base2.description = String(args2[inputDescriptor.descriptionArg]);
    }
    const filteredArgs = Object.keys(args2).filter((key2) => {
      return !filterKeys.has(key2);
    }).map((key2) => {
      return formatArg(key2, args2[key2]);
    });
    return {
      ...base2,
      args: filteredArgs
    };
  } else {
    const formattedArgs = Object.keys(args2).map((key2) => {
      return formatArg(key2, args2[key2]);
    });
    return {
      args: formattedArgs
    };
  }
};
const sourcePanel = "_sourcePanel_bat6y_1";
const simple = "_simple_bat6y_6";
const code$2 = "_code_bat6y_11";
const styles$s = {
  sourcePanel,
  simple,
  code: code$2
};
const SourceCodePanel = ({
  id,
  code: code2,
  language,
  simple: simple2 = false,
  style: style2,
  className: className2
}) => {
  const sourceCodeRef = reactExports.useRef(null);
  usePrismHighlight(sourceCodeRef, code2.length);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: sourceCodeRef, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
    "pre",
    {
      className: clsx(
        styles$s.sourcePanel,
        simple2 ? styles$s.simple : "",
        className2
      ),
      style: style2,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "code",
        {
          id,
          className: clsx("source-code", styles$s.code, `language-${language}`),
          children: code2
        }
      )
    }
  ) });
};
const getCustomToolView = (props) => {
  if (props.tool === "answer") {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(AnswerToolCallView, { ...props });
  }
  return void 0;
};
const AnswerToolCallView = (props) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    SourceCodePanel,
    {
      code: props.functionCall,
      language: "python",
      id: props.id
    }
  );
};
const toolCallView = "_toolCallView_x6cus_1";
const styles$r = {
  toolCallView
};
const todoList = "_todoList_1t8rx_1";
const inProgress = "_inProgress_1t8rx_9";
const styles$q = {
  todoList,
  inProgress
};
const toToolTodos = (obj) => {
  if (Array.isArray(obj) && obj.every((item) => typeof item === "object") && obj.every(
    (item) => item !== null && ("content" in item || "step" in item) && "status" in item
  )) {
    return obj.map((o) => {
      return {
        content: o.content || o.step || "",
        status: o.status
      };
    });
  } else {
    return [];
  }
};
const TodoWriteInput = ({ contents: contents2, parentRef }) => {
  const todoItems = toToolTodos(contents2);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: parentRef, className: clsx(styles$q.todoList), children: todoItems.map((todo) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "i",
        {
          className: clsx(
            todo.status === "completed" ? ApplicationIcons.checkbox.checked : ApplicationIcons.checkbox.unchecked,
            "text-size-smallest"
          )
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "span",
        {
          className: clsx(
            styles$q.todoItem,
            "text-size-smallest",
            todo.status === "in_progress" ? styles$q.inProgress : void 0
          ),
          children: todo.content
        }
      )
    ] });
  }) });
};
const outputPre = "_outputPre_fhwyo_1";
const toolView = "_toolView_fhwyo_7";
const outputCode = "_outputCode_fhwyo_16";
const styles$p = {
  outputPre,
  toolView,
  outputCode
};
const ToolInput = (props) => {
  const { contentType, contents: contents2, toolCallView: toolCallView2, className: className2 } = props;
  const sourceCodeRef = reactExports.useRef(null);
  const sourceCodeLength = toolCallView2 ? toolCallView2.content?.length : contents2 ? typeof contents2 === "string" ? contents2.length : JSON.stringify(contents2).length : 0;
  usePrismHighlight(sourceCodeRef, sourceCodeLength || 0);
  if (!contents2 && !toolCallView2?.content) return null;
  if (toolCallView2) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      RenderedText,
      {
        markdown: toolCallView2.content || "",
        ref: sourceCodeRef,
        className: clsx("tool-output", styles$p.toolView, className2)
      }
    );
  } else {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      RenderTool,
      {
        contents: contents2,
        contentType: contentType || "",
        parentRef: sourceCodeRef,
        className: className2
      }
    );
  }
};
const RenderTool = ({
  contents: contents2,
  contentType,
  parentRef,
  className: className2
}) => {
  if (contentType === kToolTodoContentType) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(TodoWriteInput, { contents: contents2, parentRef });
  }
  const formattedContent = typeof contents2 === "object" ? JSON.stringify(contents2) : contents2;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: parentRef, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
    "pre",
    {
      className: clsx(
        "tool-output",
        styles$p.outputPre,
        styles$p.bottomMargin,
        className2
      ),
      children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "code",
        {
          className: clsx(
            "source-code",
            "sourceCode",
            contentType ? `language-${contentType}` : void 0,
            styles$p.outputCode
          ),
          children: formattedContent
        }
      )
    }
  ) });
};
const image = "_image_1vcac_1";
const toolTitle = "_toolTitle_1vcac_6";
const description = "_description_1vcac_10";
const styles$o = {
  image,
  toolTitle,
  description
};
const ToolTitle = ({ title: title2, description: description2 }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "i",
      {
        className: clsx("bi", "bi-tools", styles$o.image, "text-size-smaller")
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: clsx("text-size-smaller", styles$o.toolTitle), children: title2 }),
    description2 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: clsx(styles$o.description, "text-size-smallest"), children: [
      "- ",
      description2
    ] }) : void 0
  ] });
};
const ToolCallView = ({
  id,
  tool: tool2,
  functionCall,
  input,
  description: description2,
  contentType,
  view,
  output: output2,
  mode,
  collapsible = true
}) => {
  function isContentImage(value2) {
    if (value2 && typeof value2 === "object") {
      if (value2.type === "image") {
        return true;
      } else if (value2.type === "tool") {
        if (Array.isArray(value2.content) && value2.content.some(isContentImage)) {
          return true;
        }
      }
    }
    return false;
  }
  const collapse = Array.isArray(output2) ? output2.every((item) => !isContentImage(item)) : !isContentImage(output2);
  const normalizedContent = reactExports.useMemo(() => normalizeContent$1(output2), [output2]);
  const hasContent = normalizedContent.find((c) => {
    if (c.type === "tool") {
      for (const t2 of c.content) {
        if (t2.type === "text") {
          if (t2.text) {
            return true;
          }
        } else {
          return true;
        }
      }
      return false;
    } else {
      return true;
    }
  });
  const customToolView = getCustomToolView({
    id,
    tool: tool2,
    functionCall,
    input,
    description: description2,
    contentType,
    output: output2
  });
  if (customToolView) {
    return customToolView;
  }
  const contents2 = mode !== "compact" ? input : input || functionCall;
  const context = defaultContext();
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$r.toolCallView), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      mode !== "compact" && (!view || view.title) ? /* @__PURE__ */ jsxRuntimeExports.jsx(
        ToolTitle,
        {
          title: view?.title || functionCall,
          description: description2
        }
      ) : "",
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        ToolInput,
        {
          contentType,
          contents: contents2,
          toolCallView: view
        }
      )
    ] }),
    hasContent && collapsible ? /* @__PURE__ */ jsxRuntimeExports.jsx(
      ExpandablePanel,
      {
        id: `${id}-tool-input`,
        collapse,
        border: true,
        lines: 15,
        className: clsx("text-size-small"),
        children: /* @__PURE__ */ jsxRuntimeExports.jsx(MessageContent, { contents: normalizedContent, context })
      }
    ) : /* @__PURE__ */ jsxRuntimeExports.jsx(MessageContent, { contents: normalizedContent, context })
  ] });
};
const normalizeContent$1 = (output2) => {
  if (Array.isArray(output2)) {
    return output2;
  } else {
    return [
      {
        type: "tool",
        content: [
          {
            type: "text",
            text: String(output2),
            refusal: null,
            internal: null,
            citations: null
          }
        ]
      }
    ];
  }
};
const ChatMessageRow = ({
  index,
  parentName,
  showLabels,
  labels,
  highlightLabeled,
  resolvedMessage,
  toolCallStyle,
  indented: indented2,
  highlightUserMessage,
  allowLinking = true,
  className: className2
}) => {
  const views = [];
  const viewLabels = [];
  const useLabels = showLabels || Object.keys(labels || {}).length > 0;
  if (useLabels) {
    const number2 = index + 1;
    const maxlabelLen = labels ? Object.values(labels).reduce((curr, r2) => {
      return Math.max(r2.length, curr);
    }, 0) : 3;
    const chatMessageLabel = labels && resolvedMessage.message.id ? labels[resolvedMessage.message.id] || " ".repeat(maxlabelLen * 2) : String(number2) || void 0;
    viewLabels.push(chatMessageLabel);
  }
  views.push(
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ChatMessage,
      {
        id: `${parentName}-chat-messages`,
        message: resolvedMessage.message,
        toolMessages: resolvedMessage.toolMessages,
        indented: indented2,
        toolCallStyle,
        allowLinking
      }
    )
  );
  if (toolCallStyle !== "omit" && resolvedMessage.message.role === "assistant" && resolvedMessage.message.tool_calls && resolvedMessage.message.tool_calls.length) {
    const toolMessages = resolvedMessage.toolMessages || [];
    let idx = 0;
    for (const tool_call of resolvedMessage.message.tool_calls) {
      const { name, input, description: description2, functionCall, contentType } = resolveToolInput(tool_call.function, tool_call.arguments);
      let toolMessage;
      if (tool_call.id) {
        toolMessage = toolMessages.find((msg) => {
          return msg.tool_call_id === tool_call.id;
        });
      } else {
        toolMessage = toolMessages[idx];
      }
      const toolLabel = labels?.[toolMessage?.id || ""] || void 0;
      const resolvedToolOutput = resolveToolMessage(toolMessage);
      if (useLabels) {
        viewLabels.push(toolLabel);
      }
      if (toolCallStyle === "compact") {
        views.push(
          /* @__PURE__ */ jsxRuntimeExports.jsx(ToolCallViewCompact, { idx, functionCall })
        );
      } else {
        views.push(
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            ToolCallView,
            {
              id: `${index}-tool-call-${idx}`,
              tool: name,
              functionCall,
              input,
              description: description2,
              contentType,
              output: resolvedToolOutput,
              collapsible: false
            },
            `tool-call-${idx}`
          )
        );
      }
      idx++;
    }
  }
  if (useLabels) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$t.grid, className2), children: views.map((view, idx) => {
      const label2 = viewLabels[idx];
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              "text-size-smaller",
              "text-style-secondary",
              styles$t.number,
              styles$t.label
            ),
            children: label2
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              styles$t.container,
              highlightUserMessage && resolvedMessage.message.role === "user" ? styles$t.user : void 0,
              idx === 0 ? styles$t.first : void 0,
              idx === views.length - 1 ? styles$t.last : void 0,
              highlightLabeled && label2?.trim() ? styles$t.highlight : void 0
            ),
            children: view
          }
        )
      ] }, `chat-message-row-${index}-part-${idx}`);
    }) }) });
  } else {
    return views.map((view, idx) => {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: clsx(
            styles$t.container,
            idx === 0 ? styles$t.first : void 0,
            idx === views.length - 1 ? styles$t.last : void 0,
            idx === views.length - 1 ? styles$t.bottomMargin : void 0,
            className2,
            styles$t.simple,
            highlightUserMessage && resolvedMessage.message.role === "user" ? styles$t.user : void 0
          ),
          children: view
        },
        `chat-message-row-unlabeled-${index}-part-${idx}`
      );
    });
  }
};
const resolveToolMessage = (toolMessage) => {
  if (!toolMessage) {
    return [];
  }
  const content2 = toolMessage.error !== null && toolMessage.error ? toolMessage.error.message : toolMessage.content;
  if (typeof content2 === "string") {
    return [
      {
        type: "tool",
        content: [
          {
            type: "text",
            text: content2,
            refusal: null,
            internal: null,
            citations: null
          }
        ]
      }
    ];
  } else {
    const result2 = content2.map((con) => {
      if (typeof con === "string") {
        return {
          type: "tool",
          content: [
            {
              type: "text",
              text: con,
              refusal: null,
              internal: null,
              citations: null
            }
          ]
        };
      } else if (con.type === "text") {
        return {
          content: [con],
          type: "tool"
        };
      } else if (con.type === "image") {
        return {
          content: [con],
          type: "tool"
        };
      }
    }).filter((con) => con !== void 0);
    return result2;
  }
};
const ToolCallViewCompact = ({ idx, functionCall }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("code", { className: clsx(styles$t.codeCompact), children: [
    "tool: ",
    functionCall
  ] }) }, `tool-call-${idx}`);
};
const resolveMessages = (messages2) => {
  const resolvedMessages = [];
  let index = 0;
  for (const message2 of messages2) {
    if (message2.role === "tool") {
      if (resolvedMessages.length > 0) {
        const msg = resolvedMessages[resolvedMessages.length - 1];
        if (msg) {
          msg.toolMessages = msg.toolMessages || [];
          msg.toolMessages.push(message2);
        }
      }
    } else {
      resolvedMessages.push({ message: message2, toolMessages: [] });
    }
    if (message2.id === void 0) {
      message2.id = `msg-${index}`;
    }
    index++;
  }
  const systemMessages = [];
  const collapsedMessages = resolvedMessages.map((resolved) => {
    if (resolved.message.role === "system") {
      systemMessages.push(resolved.message);
    }
    return resolved;
  }).filter((resolved) => {
    return resolved.message.role !== "system";
  });
  const systemContent = [];
  for (const systemMessage2 of systemMessages) {
    const contents2 = Array.isArray(systemMessage2.content) ? systemMessage2.content : [systemMessage2.content];
    systemContent.push(...contents2.map(normalizeContent));
  }
  const systemMessage = {
    id: "sys-message-6815A84B062A",
    role: "system",
    content: systemContent,
    source: "input",
    metadata: null
  };
  if (systemMessage && systemMessage.content.length > 0) {
    collapsedMessages.unshift({ message: systemMessage, toolMessages: [] });
  }
  return collapsedMessages;
};
const normalizeContent = (content2) => {
  if (typeof content2 === "string") {
    return {
      type: "text",
      text: content2,
      refusal: null,
      internal: null,
      citations: null
    };
  } else {
    return content2;
  }
};
const ChatView = ({
  id,
  messages: messages2,
  toolCallStyle = "complete",
  resolveToolCallsIntoPreviousMessage = true,
  indented: indented2,
  labels,
  showLabels = true,
  highlightLabeled = false,
  className: className2,
  allowLinking = true
}) => {
  const collapsedMessages = resolveToolCallsIntoPreviousMessage ? resolveMessages(messages2) : messages2.map((msg) => {
    return {
      message: msg,
      toolMessages: []
    };
  });
  const result2 = /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(className2), children: collapsedMessages.map((msg, index) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      ChatMessageRow,
      {
        index,
        parentName: id || "chat-view",
        showLabels,
        labels,
        highlightLabeled,
        resolvedMessage: msg,
        indented: indented2,
        toolCallStyle,
        allowLinking
      },
      `${id}-msg-${index}`
    );
  }) });
  return result2;
};
const ChatMessageRenderer = {
  bucket: Buckets.first,
  canRender: (entry) => {
    const val = entry.value;
    return Array.isArray(val) && val.length > 0 && val[0]?.role !== void 0 && val[0]?.content !== void 0;
  },
  render: (id, entry) => {
    return {
      rendered: /* @__PURE__ */ jsxRuntimeExports.jsxs(NavPills, { id: `${id}-navpills`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(ChatSummary, { title: "Last Turn", id, messages: entry.value }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ChatView,
          {
            title: "All",
            id,
            messages: entry.value,
            allowLinking: false
          }
        )
      ] })
    };
  }
};
const ChatSummary = ({ id, messages: messages2 }) => {
  const summaryMessages = [];
  for (const message2 of messages2.slice().reverse()) {
    summaryMessages.unshift(message2);
    if (message2.role === "user") {
      break;
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx(ChatView, { id, messages: summaryMessages });
};
const query = "_query_seqs2_1";
const summary$3 = "_summary_seqs2_6";
const preWrap = "_preWrap_seqs2_10";
const preCompact = "_preCompact_seqs2_15";
const styles$n = {
  query,
  summary: summary$3,
  preWrap,
  preCompact
};
const RenderedContent = ({
  id,
  entry,
  references,
  renderOptions = { renderString: "markdown" },
  renderObject
}) => {
  if (entry.value === null) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("code", { children: "[null]" }) }) });
  }
  const renderers = contentRenderers(renderObject);
  const renderer = Object.keys(renderers).map((key2) => {
    return renderers[key2];
  }).sort((a2, b) => {
    if (!a2 || !b) {
      return 0;
    }
    return a2.bucket - b.bucket;
  }).find((renderer2) => {
    return renderer2?.canRender(entry);
  });
  if (renderer) {
    const { rendered } = renderer.render(id, entry, renderOptions, references);
    if (rendered !== void 0 && reactExports.isValidElement(rendered)) {
      return rendered;
    }
  }
  const displayValue = (() => {
    try {
      if (typeof entry.value === "object") {
        return JSON.stringify(entry.value);
      }
      return String(entry.value).trim();
    } catch (e) {
      return "[Unable to display value]";
    }
  })();
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: displayValue });
};
const contentRenderers = (renderObject) => {
  const contentRenderers2 = {
    AnsiString: {
      bucket: Buckets.first,
      canRender: (entry) => {
        return typeof entry.value === "string" && entry.value.indexOf("\x1B") > -1;
      },
      render: (_id, entry, _options) => {
        return {
          rendered: /* @__PURE__ */ jsxRuntimeExports.jsx(ANSIDisplay, { output: entry.value })
        };
      }
    },
    JsonString: {
      bucket: Buckets.first,
      canRender: (entry) => {
        if (typeof entry.value === "string") {
          const trimmed = entry.value.trim();
          return isJson(trimmed);
        }
        return false;
      },
      render: (_id, entry, _options) => {
        const obj = lib$1.parse(entry.value);
        return {
          rendered: /* @__PURE__ */ jsxRuntimeExports.jsx(JSONPanel, { data: obj })
        };
      }
    },
    Model: {
      bucket: Buckets.intermediate,
      canRender: (entry) => {
        return typeof entry.value === "object" && entry.value._model;
      },
      render: (_id, entry, _options) => {
        return {
          rendered: /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.model }),
            " ",
            entry.value._model
          ] })
        };
      }
    },
    Boolean: {
      bucket: Buckets.intermediate,
      canRender: (entry) => {
        return typeof entry.value === "boolean";
      },
      render: (id, entry, options) => {
        entry.value = entry.value.toString();
        return contentRenderers2.String?.render(id, entry, options) || {
          rendered: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: entry.value })
        };
      }
    },
    Number: {
      bucket: Buckets.intermediate,
      canRender: (entry) => {
        return typeof entry.value === "number";
      },
      render: (id, entry, options) => {
        entry.value = formatNumber(entry.value);
        return contentRenderers2.String?.render(id, entry, options) || {
          rendered: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: entry.value })
        };
      }
    },
    String: {
      bucket: Buckets.final,
      canRender: (entry) => {
        return typeof entry.value === "string";
      },
      render: (_id, entry, options, references) => {
        const rendered = entry.value.trim();
        if (options.renderString === "markdown") {
          return {
            rendered: /* @__PURE__ */ jsxRuntimeExports.jsx(
              RenderedText,
              {
                markdown: rendered,
                references,
                options: { previewRefsOnHover: options.previewRefsOnHover }
              }
            )
          };
        } else {
          return {
            rendered: /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: clsx(styles$n.preWrap, styles$n.preCompact), children: rendered })
          };
        }
      }
    },
    Array: {
      bucket: Buckets.intermediate,
      canRender: (entry) => {
        const isArray = Array.isArray(entry.value);
        if (isArray) {
          if (entry.value.length === 0 || entry.value.length === 1) {
            return true;
          }
          const types = new Set(
            entry.value.filter((e) => e !== null).map((e) => {
              return typeof e;
            })
          );
          return types.size === 1;
        } else {
          return false;
        }
      },
      render: (id, entry, _options) => {
        const arrayMap = {};
        entry.value.forEach((e, index) => {
          arrayMap[`[${index}]`] = e;
        });
        const arrayRendered = renderObject ? renderObject(arrayMap) : /* @__PURE__ */ jsxRuntimeExports.jsx(
          MetaDataGrid,
          {
            id,
            className: "font-size-small",
            entries: arrayMap,
            options: { plain: true }
          }
        );
        return { rendered: arrayRendered };
      }
    },
    ChatMessage: ChatMessageRenderer,
    web_search: {
      bucket: Buckets.intermediate,
      canRender: (entry) => {
        return typeof entry.value === "object" && entry.name === "web_search";
      },
      render: (_id, entry, _options) => {
        const results = [];
        results.push(
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$n.query, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.search }),
            " ",
            entry.value.query
          ] })
        );
        entry.value.results.forEach(
          (result2) => {
            results.push(
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("a", { href: result2.url, children: result2.url }) })
            );
            results.push(
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-smaller", styles$n.summary), children: result2.summary })
            );
          }
        );
        return {
          rendered: results
        };
      }
    },
    web_browser: {
      bucket: Buckets.intermediate,
      canRender: (entry) => {
        return typeof entry.value === "string" && entry.name?.startsWith("web_browser");
      },
      render: (_id, entry, _options) => {
        return {
          rendered: /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: styles$n.preWrap, children: entry.value })
        };
      }
    },
    Html: {
      bucket: Buckets.intermediate,
      canRender: (entry) => {
        return typeof entry.value === "object" && entry.value._html;
      },
      render: (_id, entry, _options) => {
        return {
          rendered: entry.value._html
        };
      }
    },
    MessageContent: {
      bucket: Buckets.first,
      canRender: (entry) => {
        return Array.isArray(entry.value) && entry.value.every((item) => {
          return isMessageContent(item);
        });
      },
      render: (_id, entry, _options) => {
        return {
          rendered: /* @__PURE__ */ jsxRuntimeExports.jsx(MessageContent, { contents: entry.value, context: defaultContext() })
        };
      }
    },
    Image: {
      bucket: Buckets.intermediate,
      canRender: (entry) => {
        return typeof entry.value === "string" && entry.value.startsWith("data:image/");
      },
      render: (_id, entry, _options) => {
        return {
          rendered: /* @__PURE__ */ jsxRuntimeExports.jsx("img", { src: entry.value })
        };
      }
    },
    Object: {
      bucket: Buckets.intermediate,
      canRender: (entry) => {
        return typeof entry.value === "object";
      },
      render: (id, entry, _options) => {
        if (renderObject) {
          return { rendered: renderObject(entry.value) };
        } else {
          return {
            rendered: /* @__PURE__ */ jsxRuntimeExports.jsx(
              MetaDataGrid,
              {
                id,
                className: "font-size-small",
                entries: entry.value,
                options: { plain: true }
              }
            )
          };
        }
      }
    }
  };
  return contentRenderers2;
};
const MetaDataGrid = ({
  id,
  entries,
  className: className2,
  references,
  style: style2,
  options
}) => {
  const baseId = "metadata-grid";
  const fontStyle = options?.size === "mini" ? "text-size-smallest" : "text-size-smaller";
  const entryEls = entryRecords(entries).map((entry, index) => {
    const id2 = `${baseId}-value-${index}`;
    return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
      index !== 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          style: {
            gridColumn: "1 / -1",
            borderBottom: `${!options?.plain ? "solid 1px var(--bs-light-border-subtle" : ""}`
          }
        }
      ) : void 0,
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: clsx(
            `${baseId}-key`,
            styles$N.cell,
            "text-style-label",
            "text-style-secondary",
            fontStyle
          ),
          children: entry?.name
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$N.value, `${baseId}-value`, fontStyle), children: entry && /* @__PURE__ */ jsxRuntimeExports.jsx(
        RenderedContent,
        {
          id: id2,
          entry,
          references,
          renderOptions: {
            renderString: "markdown",
            previewRefsOnHover: options?.previewRefsOnHover
          },
          renderObject: (obj) => {
            return /* @__PURE__ */ jsxRuntimeExports.jsx(
              MetaDataGrid,
              {
                id: id2,
                className: clsx(styles$N.nested),
                entries: obj,
                options,
                references
              }
            );
          }
        }
      ) })
    ] }, `${baseId}-record-${index}`);
  });
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { id, className: clsx(className2, styles$N.grid), style: style2, children: entryEls });
};
const entryRecords = (entries) => {
  if (!entries) {
    return [];
  }
  if (!Array.isArray(entries)) {
    return Object.entries(entries || {}).map(([key2, value2]) => {
      return { name: key2, value: value2 };
    });
  } else {
    return entries;
  }
};
const usePreviousValue = (value2) => {
  const [current, setCurrent] = reactExports.useState(value2);
  const [previous, setPrevious] = reactExports.useState(void 0);
  if (value2 !== current) {
    setPrevious(current);
    setCurrent(value2);
  }
  return previous;
};
const progressContainer = "_progressContainer_1cjjr_1";
const styles$m = {
  progressContainer
};
const LiveVirtualList = ({
  id,
  listHandle,
  className: className2,
  data,
  renderRow,
  scrollRef,
  live,
  showProgress,
  initialTopMostItemIndex,
  offsetTop,
  components,
  itemSearchText,
  animation = true
}) => {
  const { getRestoreState, isScrolling, visibleRange, setVisibleRange } = useVirtuosoState(listHandle, `live-virtual-list-${id}`);
  const { registerVirtualList } = useExtendedFind();
  const pendingSearchCallback = reactExports.useRef(null);
  const [isCurrentlyScrolling, setIsCurrentlyScrolling] = reactExports.useState(false);
  const [followOutput, setFollowOutput] = useProperty(
    id,
    "follow",
    {
      defaultValue: null
    }
  );
  const isAutoScrollingRef = reactExports.useRef(false);
  reactExports.useEffect(() => {
    if (followOutput === null) {
      setFollowOutput(!!live);
    }
  }, [followOutput, live, setFollowOutput]);
  const prevLive = usePreviousValue(live);
  reactExports.useEffect(() => {
    if (!live && prevLive && followOutput && scrollRef?.current) {
      setFollowOutput(false);
      setTimeout(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTo({ top: 0, behavior: "instant" });
        }
      }, 100);
    }
  }, [live, followOutput, prevLive, scrollRef, setFollowOutput]);
  const handleScroll = useRafThrottle(() => {
    if (isAutoScrollingRef.current) return;
    if (!live) return;
    if (scrollRef?.current && listHandle.current) {
      const parent = scrollRef.current;
      const isAtBottom = parent.scrollHeight - parent.scrollTop <= parent.clientHeight + 30;
      if (isAtBottom && !followOutput) {
        setFollowOutput(true);
      } else if (!isAtBottom && followOutput) {
        setFollowOutput(false);
      }
    }
  });
  const heightChanged = reactExports.useCallback(
    (height) => {
      requestAnimationFrame(() => {
        if (followOutput && live && scrollRef?.current) {
          isAutoScrollingRef.current = true;
          listHandle.current?.scrollTo({ top: height });
          requestAnimationFrame(() => {
            isAutoScrollingRef.current = false;
          });
        }
      });
    },
    [followOutput, live, scrollRef, listHandle]
  );
  const [, forceRender] = reactExports.useState({});
  const forceUpdate = reactExports.useCallback(() => forceRender({}), []);
  reactExports.useEffect(() => {
    const timer = setTimeout(() => {
      forceUpdate();
    }, 0);
    return () => clearTimeout(timer);
  }, [forceUpdate]);
  const defaultItemSearchText = reactExports.useCallback((item) => {
    try {
      return JSON.stringify(item);
    } catch {
      return "";
    }
  }, []);
  const searchInText = reactExports.useCallback(
    (text2, searchTerm) => {
      const lowerText = text2.toLowerCase();
      const prepared = prepareSearchTerm(searchTerm);
      if (lowerText.includes(prepared.simple)) {
        return true;
      }
      if (prepared.unquoted && lowerText.includes(prepared.unquoted)) {
        return true;
      }
      if (prepared.jsonEscaped && lowerText.includes(prepared.jsonEscaped)) {
        return true;
      }
      return false;
    },
    []
  );
  const searchInItem = reactExports.useCallback(
    (item, searchTerm) => {
      const getSearchText = itemSearchText ?? defaultItemSearchText;
      const texts = getSearchText(item);
      const textArray = Array.isArray(texts) ? texts : [texts];
      return textArray.some((text2) => searchInText(text2, searchTerm));
    },
    [itemSearchText, defaultItemSearchText, searchInText]
  );
  const searchInData = reactExports.useCallback(
    (term, direction, onContentReady) => {
      if (!data.length || !term) {
        return Promise.resolve(false);
      }
      const currentIndex = direction === "forward" ? visibleRange.endIndex : visibleRange.startIndex;
      const searchStart = direction === "forward" ? Math.max(0, currentIndex + 1) : Math.min(data.length - 1, currentIndex - 1);
      const step = direction === "forward" ? 1 : -1;
      for (let i2 = searchStart; i2 >= 0 && i2 < data.length; i2 += step) {
        const item = data[i2];
        if (item !== void 0 && searchInItem(item, term)) {
          pendingSearchCallback.current = onContentReady;
          listHandle.current?.scrollToIndex({
            index: i2,
            behavior: "auto",
            align: "center"
          });
          setTimeout(() => {
            if (pendingSearchCallback.current === onContentReady) {
              pendingSearchCallback.current = null;
              onContentReady();
            }
          }, 200);
          return Promise.resolve(true);
        }
      }
      return Promise.resolve(false);
    },
    [
      data,
      searchInItem,
      visibleRange.endIndex,
      visibleRange.startIndex,
      listHandle
    ]
  );
  reactExports.useEffect(() => {
    const unregister = registerVirtualList(id, searchInData);
    return unregister;
  }, [id, registerVirtualList, searchInData]);
  const Footer = () => {
    return showProgress ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$m.progressContainer), children: /* @__PURE__ */ jsxRuntimeExports.jsx(PulsingDots, { subtle: false, size: "medium" }) }) : void 0;
  };
  reactExports.useEffect(() => {
    const parent = scrollRef?.current;
    if (parent) {
      parent.addEventListener("scroll", handleScroll);
      return () => parent.removeEventListener("scroll", handleScroll);
    }
  }, [scrollRef, handleScroll]);
  const hasScrolled = reactExports.useRef(false);
  reactExports.useEffect(() => {
    if (initialTopMostItemIndex !== void 0 && listHandle.current) {
      const timer = setTimeout(() => {
        listHandle.current?.scrollToIndex({
          index: initialTopMostItemIndex,
          align: "start",
          behavior: !animation ? "auto" : !hasScrolled.current ? "auto" : "smooth",
          offset: offsetTop ? -offsetTop : void 0
        });
        hasScrolled.current = true;
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [initialTopMostItemIndex, listHandle, offsetTop]);
  reactExports.useEffect(() => {
    if (!isCurrentlyScrolling && pendingSearchCallback.current) {
      setTimeout(() => {
        const callback = pendingSearchCallback.current;
        pendingSearchCallback.current = null;
        callback?.();
      }, 100);
    }
  }, [isCurrentlyScrolling]);
  const handleScrollingChange = reactExports.useCallback(
    (scrolling) => {
      setIsCurrentlyScrolling(scrolling);
      isScrolling(scrolling);
    },
    [isScrolling]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    Yr,
    {
      ref: listHandle,
      customScrollParent: scrollRef?.current ? scrollRef.current : void 0,
      style: { height: "100%", width: "100%" },
      data,
      defaultItemHeight: 500,
      itemContent: renderRow,
      increaseViewportBy: { top: 1e3, bottom: 1e3 },
      overscan: { main: 5, reverse: 5 },
      className: clsx("transcript", className2),
      isScrolling: handleScrollingChange,
      rangeChanged: (range) => {
        setVisibleRange(range);
      },
      restoreStateFrom: getRestoreState(),
      totalListHeightChanged: heightChanged,
      components: {
        Footer,
        ...components
      }
    }
  );
};
const prepareSearchTerm = (term) => {
  const lower = term.toLowerCase();
  if (!term.includes('"') && !term.includes(":")) {
    return { simple: lower };
  }
  return {
    simple: lower,
    // Remove quotes
    unquoted: lower.replace(/"/g, ""),
    // Escape quotes for JSON
    jsonEscaped: lower.replace(/"/g, '\\"')
  };
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
const STEP = "step";
const ACTION_BEGIN = "begin";
const SPAN_BEGIN = "span_begin";
const SPAN_END = "span_end";
const TOOL = "tool";
const STORE = "store";
const STATE = "state";
const TYPE_TOOL = "tool";
const TYPE_SUBTASK = "subtask";
const TYPE_SOLVER = "solver";
const TYPE_SOLVERS = "solvers";
const TYPE_AGENT = "agent";
const TYPE_HANDOFF = "handoff";
const TYPE_SCORERS = "scorers";
const TYPE_SCORER = "scorer";
const hasSpans = (events) => {
  return events.some((event) => event.event === SPAN_BEGIN);
};
const kSandboxSignalName = "53787D8A-D3FC-426D-B383-9F880B70E4AA";
const fixupEventStream = (events, filterPending = true) => {
  const collapsed = processPendingEvents(events, filterPending);
  const fixedUp = collapseSampleInit(collapsed);
  return groupSandboxEvents(fixedUp);
};
const processPendingEvents = (events, filter) => {
  return filter ? events.filter((e) => !e.pending) : events.reduce((acc, event) => {
    if (!event.pending) {
      acc.push(event);
    } else {
      const lastIndex = acc.length - 1;
      if (lastIndex >= 0 && acc[lastIndex]?.pending && acc[lastIndex]?.event === event.event) {
        acc[lastIndex] = event;
      } else {
        acc.push(event);
      }
    }
    return acc;
  }, []);
};
const collapseSampleInit = (events) => {
  const hasSpans2 = events.some((e) => {
    return e.event === "span_begin" || e.event === "span_end";
  });
  if (hasSpans2) {
    return events;
  }
  const hasInitStep = events.findIndex((e) => {
    return e.event === "step" && e.name === "init";
  }) !== -1;
  if (hasInitStep) {
    return events;
  }
  const initEventIndex = events.findIndex((e) => {
    return e.event === "sample_init";
  });
  const initEvent = events[initEventIndex];
  if (!initEvent) {
    return events;
  }
  const fixedUp = [...events];
  fixedUp.splice(initEventIndex, 0, {
    timestamp: initEvent.timestamp,
    event: "step",
    action: "begin",
    type: null,
    name: "sample_init",
    pending: false,
    working_start: 0,
    span_id: initEvent.span_id,
    uuid: null,
    metadata: null
  });
  fixedUp.splice(initEventIndex + 2, 0, {
    timestamp: initEvent.timestamp,
    event: "step",
    action: "end",
    type: null,
    name: "sample_init",
    pending: false,
    working_start: 0,
    span_id: initEvent.span_id,
    uuid: null,
    metadata: null
  });
  return fixedUp;
};
const groupSandboxEvents = (events) => {
  const result2 = [];
  const pendingSandboxEvents = [];
  const useSpans = hasSpans(events);
  const pushPendingSandboxEvents = () => {
    const timestamp = pendingSandboxEvents[pendingSandboxEvents.length - 1]?.timestamp || "";
    if (useSpans) {
      result2.push(createSpanBegin(kSandboxSignalName, timestamp, null));
    } else {
      result2.push(createStepEvent(kSandboxSignalName, timestamp, "begin"));
    }
    result2.push(...pendingSandboxEvents);
    if (useSpans) {
      result2.push(createSpanEnd(kSandboxSignalName, timestamp));
    } else {
      result2.push(createStepEvent(kSandboxSignalName, timestamp, "end"));
    }
    pendingSandboxEvents.length = 0;
  };
  for (const event of events) {
    if (event.event === "sandbox") {
      pendingSandboxEvents.push(event);
      continue;
    }
    if (pendingSandboxEvents.length > 0) {
      pushPendingSandboxEvents();
    }
    result2.push(event);
  }
  if (pendingSandboxEvents.length > 0) {
    pushPendingSandboxEvents();
  }
  return result2;
};
const createStepEvent = (name, timestamp, action) => ({
  timestamp,
  event: "step",
  action,
  type: null,
  name,
  pending: false,
  working_start: 0,
  span_id: null,
  uuid: null,
  metadata: null
});
const createSpanBegin = (name, timestamp, parent_id) => {
  return {
    name,
    id: `${name}-begin`,
    span_id: name,
    parent_id,
    timestamp,
    event: "span_begin",
    type: null,
    pending: false,
    working_start: 0,
    uuid: null,
    metadata: null
  };
};
const createSpanEnd = (name, timestamp) => {
  return {
    id: `${name}-end`,
    timestamp,
    event: "span_end",
    pending: false,
    working_start: 0,
    span_id: name,
    uuid: null,
    metadata: null
  };
};
const kTranscriptCollapseScope = "transcript-collapse";
const kTranscriptOutlineCollapseScope = "transcript-outline";
const kCollapsibleEventTypes = [
  STEP,
  SPAN_BEGIN,
  TYPE_TOOL,
  TYPE_SUBTASK
];
const eventTypeValues = [
  "sample_init",
  "sample_limit",
  "state",
  "store",
  "model",
  "logger",
  "info",
  "step",
  "subtask",
  "score",
  "score_edit",
  "tool",
  "input",
  "error",
  "approval",
  "compaction",
  "sandbox",
  "span_begin",
  "span_end"
];
class EventNode {
  id;
  event;
  children = [];
  depth;
  constructor(id, event, depth) {
    this.id = id;
    this.event = event;
    this.depth = depth;
  }
}
const transformTree = (roots) => {
  const treeNodeTransformers = transformers();
  const visitNode = (node2) => {
    let currentNodes = [node2];
    currentNodes = currentNodes.map((n2) => {
      n2.children = n2.children.flatMap(visitNode);
      return n2;
    });
    for (const transformer of treeNodeTransformers) {
      const nextNodes = [];
      for (const currentNode of currentNodes) {
        if (transformer.matches(currentNode)) {
          const result2 = transformer.process(currentNode);
          if (Array.isArray(result2)) {
            nextNodes.push(...result2);
          } else {
            nextNodes.push(result2);
          }
        } else {
          nextNodes.push(currentNode);
        }
      }
      currentNodes = nextNodes;
    }
    return currentNodes && currentNodes.length === 1 && currentNodes[0] ? currentNodes[0] : currentNodes;
  };
  const processedRoots = roots.flatMap(visitNode);
  const flushedNodes = [];
  for (const transformer of treeNodeTransformers) {
    if (transformer.flush) {
      const flushResults = transformer.flush();
      if (flushResults && flushResults.length > 0) {
        flushedNodes.push(...flushResults);
      }
    }
  }
  return [...processedRoots, ...flushedNodes];
};
const transformers = () => {
  const treeNodeTransformers = [
    {
      name: "unwrap_tools",
      matches: (node2) => node2.event.event === SPAN_BEGIN && node2.event.type === TYPE_TOOL,
      process: (node2) => elevateChildNode(node2, TYPE_TOOL) || node2
    },
    {
      name: "unwrap_subtasks",
      matches: (node2) => node2.event.event === SPAN_BEGIN && node2.event.type === TYPE_SUBTASK,
      process: (node2) => elevateChildNode(node2, TYPE_SUBTASK) || node2
    },
    {
      name: "unwrap_agent_solver",
      matches: (node2) => node2.event.event === SPAN_BEGIN && node2.event["type"] === TYPE_SOLVER && node2.children.length === 2 && node2.children[0]?.event.event === SPAN_BEGIN && node2.children[0]?.event.type === TYPE_AGENT && node2.children[1]?.event.event === STATE,
      process: (node2) => skipFirstChildNode(node2)
    },
    {
      name: "unwrap_agent_solver w/store",
      matches: (node2) => node2.event.event === SPAN_BEGIN && node2.event["type"] === TYPE_SOLVER && node2.children.length === 3 && node2.children[0]?.event.event === SPAN_BEGIN && node2.children[0]?.event.type === TYPE_AGENT && node2.children[1]?.event.event === STATE && node2.children[2]?.event.event === STORE,
      process: (node2) => skipFirstChildNode(node2)
    },
    {
      name: "unwrap_handoff",
      matches: (node2) => {
        const isHandoffNode = node2.event.event === SPAN_BEGIN && node2.event["type"] === TYPE_HANDOFF;
        if (!isHandoffNode) {
          return false;
        }
        if (node2.children.length === 1) {
          return node2.children[0]?.event.event === TOOL && !!node2.children[0]?.event.agent;
        } else {
          return node2.children.length === 2 && node2.children[0]?.event.event === TOOL && node2.children[1]?.event.event === STORE && node2.children[0]?.children.length === 2 && node2.children[0]?.children[0]?.event.event === SPAN_BEGIN && node2.children[0]?.children[0]?.event.type === TYPE_AGENT;
        }
      },
      process: (node2) => skipThisNode(node2)
    },
    {
      name: "discard_solvers_span",
      matches: (Node2) => Node2.event.event === SPAN_BEGIN && Node2.event.type === TYPE_SOLVERS,
      process: (node2) => {
        const nodes = discardNode(node2);
        return nodes;
      }
    }
  ];
  return treeNodeTransformers;
};
const elevateChildNode = (node2, childEventType) => {
  const targetIndex = node2.children.findIndex(
    (child) => child.event.event === childEventType
  );
  if (targetIndex === -1) {
    console.log(
      `No ${childEventType} event found in a span, this is very unexpected.`
    );
    return null;
  }
  const targetNode = { ...node2.children[targetIndex] };
  const remainingChildren = node2.children.filter((_, i2) => i2 !== targetIndex);
  targetNode.depth = node2.depth;
  targetNode.children = setDepth(remainingChildren, node2.depth + 1);
  return targetNode;
};
const skipFirstChildNode = (node2) => {
  const agentSpan = node2.children.splice(0, 1)[0];
  node2.children.unshift(...reduceDepth(agentSpan?.children || []));
  return node2;
};
const skipThisNode = (node2) => {
  const newNode = { ...node2.children[0] };
  newNode.depth = node2.depth;
  newNode.children = reduceDepth(newNode.children || [], 2);
  return newNode;
};
const discardNode = (node2) => {
  const nodes = reduceDepth(node2.children, 1);
  return nodes;
};
const reduceDepth = (nodes, depth = 1) => {
  return nodes.map((node2) => {
    if (node2.children.length > 0) {
      node2.children = reduceDepth(node2.children, 1);
    }
    node2.depth = node2.depth - depth;
    return node2;
  });
};
const setDepth = (nodes, depth) => {
  return nodes.map((node2) => {
    if (node2.children.length > 0) {
      node2.children = setDepth(node2.children, depth + 1);
    }
    node2.depth = depth;
    return node2;
  });
};
function treeifyEvents(events, depth) {
  const useSpans = hasSpans(events);
  events = injectScorersSpan(events);
  const nodes = useSpans ? treeifyWithSpans(events, depth) : treeifyWithSteps(events, depth);
  return useSpans ? transformTree(nodes) : nodes;
}
const treeifyWithSpans = (events, depth) => {
  const { rootNodes, createNode } = createNodeFactory(depth);
  const spanNodes = /* @__PURE__ */ new Map();
  const processEvent = (event, parentOverride) => {
    if (event.event === SPAN_END) {
      return;
    }
    if (event.event === STEP && event.action !== ACTION_BEGIN) {
      return;
    }
    const resolvedParent = resolveParentForEvent(event, spanNodes);
    const parentNode = resolvedParent ?? null;
    const node2 = createNode(event, parentNode);
    if (event.event === SPAN_BEGIN) {
      const spanId = getEventSpanId(event);
      if (spanId !== null) {
        spanNodes.set(spanId, node2);
      }
    }
  };
  events.forEach((event) => processEvent(event));
  return rootNodes;
};
const treeifyWithSteps = (events, depth) => {
  const { rootNodes, createNode } = createNodeFactory(depth);
  const stack = [];
  const pushStack = (node2) => {
    stack.push(node2);
  };
  const popStack = () => {
    if (stack.length > 0) {
      stack.pop();
    }
  };
  const processEvent = (event) => {
    const parent = stack.length > 0 ? stack[stack.length - 1] : null;
    switch (event.event) {
      case STEP:
        if (event.action === ACTION_BEGIN) {
          const node2 = createNode(event, parent || null);
          pushStack(node2);
        } else {
          popStack();
        }
        break;
      case SPAN_BEGIN: {
        const node2 = createNode(event, parent || null);
        pushStack(node2);
        break;
      }
      case SPAN_END:
        popStack();
        break;
      default:
        createNode(event, parent || null);
        break;
    }
  };
  events.forEach(processEvent);
  return rootNodes;
};
const createNodeFactory = (depth) => {
  const rootNodes = [];
  const childCounts = /* @__PURE__ */ new Map();
  const pathByNode = /* @__PURE__ */ new Map();
  const createNode = (event, parent) => {
    const parentKey = parent ?? null;
    const nextIndex = childCounts.get(parentKey) ?? 0;
    childCounts.set(parentKey, nextIndex + 1);
    const parentPath = parent ? pathByNode.get(parent) : void 0;
    const path = parentPath !== void 0 ? `${parentPath}.${nextIndex}` : `${nextIndex}`;
    const eventId = event.uuid || `event_node_${path}`;
    const nodeDepth = parent ? parent.depth + 1 : depth;
    const node2 = new EventNode(eventId, event, nodeDepth);
    pathByNode.set(node2, path);
    if (parent) {
      parent.children.push(node2);
    } else {
      rootNodes.push(node2);
    }
    return node2;
  };
  return { rootNodes, createNode };
};
const resolveParentForEvent = (event, spanNodes) => {
  if (event.event === SPAN_BEGIN) {
    const parentId = event.parent_id;
    if (parentId) {
      return spanNodes.get(parentId) ?? null;
    }
    return null;
  }
  const spanId = getEventSpanId(event);
  if (spanId !== null) {
    return spanNodes.get(spanId) ?? null;
  }
  return null;
};
const getEventSpanId = (event) => {
  const spanId = event.span_id;
  return spanId ?? null;
};
const kBeginScorerId = "E617087FA405";
const kEndScorerId = "C39922B09481";
const kScorersSpanId = "C5A831026F2C";
const injectScorersSpan = (events) => {
  const results = [];
  const collectedScorerEvents = [];
  let hasCollectedScorers = false;
  let collecting = null;
  const flushCollected = () => {
    if (collectedScorerEvents.length > 0) {
      const beginSpan = {
        name: "scorers",
        id: kBeginScorerId,
        span_id: kScorersSpanId,
        event: SPAN_BEGIN,
        type: TYPE_SCORERS,
        timestamp: collectedScorerEvents[0]?.timestamp || "",
        working_start: collectedScorerEvents[0]?.working_start || 0,
        pending: false,
        parent_id: null,
        uuid: null,
        metadata: null
      };
      const scoreEvents = collectedScorerEvents.map(
        (event) => {
          return {
            ...event,
            parent_id: event.event === "span_begin" ? event.parent_id || kScorersSpanId : null
          };
        }
      );
      const endSpan = {
        id: kEndScorerId,
        span_id: kScorersSpanId,
        event: SPAN_END,
        pending: false,
        working_start: collectedScorerEvents[collectedScorerEvents.length - 1]?.working_start || 0,
        timestamp: collectedScorerEvents[collectedScorerEvents.length - 1]?.timestamp || "",
        uuid: null,
        metadata: null
      };
      collectedScorerEvents.length = 0;
      hasCollectedScorers = true;
      return [beginSpan, ...scoreEvents, endSpan];
    }
    return [];
  };
  for (const event of events) {
    if (event.event === SPAN_BEGIN && event.type === TYPE_SCORERS) {
      return events;
    }
    if (event.event === SPAN_BEGIN && event.type === TYPE_SCORER && !hasCollectedScorers) {
      collecting = event.span_id;
    }
    if (collecting) {
      if (event.event === SPAN_END && event.span_id === collecting) {
        collecting = null;
        results.push(...flushCollected());
        results.push(event);
      } else {
        collectedScorerEvents.push(event);
      }
    } else {
      results.push(event);
    }
  }
  return results;
};
const useEventNodes = (events, running) => {
  const { eventTree, defaultCollapsedIds } = reactExports.useMemo(() => {
    const resolvedEvents = fixupEventStream(events, !running);
    const rawEventTree = treeifyEvents(resolvedEvents, 0);
    const filterEmpty = (eventNodes) => {
      return eventNodes.filter((node2) => {
        if (node2.children && node2.children.length > 0) {
          node2.children = filterEmpty(node2.children);
        }
        return node2.event.event !== "span_begin" && node2.event.event !== "step" || node2.children && node2.children.length > 0;
      });
    };
    const eventTree2 = filterEmpty(rawEventTree);
    const defaultCollapsedIds2 = {};
    const findCollapsibleEvents = (nodes) => {
      for (const node2 of nodes) {
        if (kCollapsibleEventTypes.includes(node2.event.event) && collapseFilters.some(
          (filter) => filter(
            node2.event
          )
        )) {
          defaultCollapsedIds2[node2.id] = true;
        }
        findCollapsibleEvents(node2.children);
      }
    };
    findCollapsibleEvents(eventTree2);
    return { eventTree: eventTree2, defaultCollapsedIds: defaultCollapsedIds2 };
  }, [events, running]);
  return { eventNodes: eventTree, defaultCollapsedIds };
};
const collapseFilters = [
  (event) => event.type === "solver" && event.name === "system_message",
  (event) => {
    if (event.event === "step" || event.event === "span_begin") {
      return event.name === kSandboxSignalName || event.name === "init" || event.name === "sample_init";
    }
    return false;
  },
  (event) => event.event === "tool" && !event.agent && !event.failed,
  (event) => event.event === "subtask"
];
const styles$l = {};
const title$1 = "_title_19l1b_1";
const contents = "_contents_19l1b_8";
const styles$k = {
  title: title$1,
  contents
};
const EventRow = ({
  title: title2,
  icon,
  className: className2,
  children: children2
}) => {
  const contentEl = title2 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx("text-size-small", styles$k.title, className2), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: icon || ApplicationIcons.metadata }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-style-label"), children: title2 }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: children2 })
  ] }) : "";
  const card2 = /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("card", styles$k.contents), children: contentEl });
  return card2;
};
const ApprovalEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventRow,
    {
      title: decisionLabel(event.decision),
      icon: decisionIcon(event.decision),
      className: className2,
      children: event.explanation || ""
    }
  );
};
const decisionLabel = (decision) => {
  switch (decision) {
    case "approve":
      return "Approved";
    case "reject":
      return "Rejected";
    case "terminate":
      return "Terminated";
    case "escalate":
      return "Escalated";
    case "modify":
      return "Modified";
    default:
      return decision;
  }
};
const decisionIcon = (decision) => {
  switch (decision) {
    case "approve":
      return ApplicationIcons.approvals.approve;
    case "reject":
      return ApplicationIcons.approvals.reject;
    case "terminate":
      return ApplicationIcons.approvals.terminate;
    case "escalate":
      return ApplicationIcons.approvals.escalate;
    case "modify":
      return ApplicationIcons.approvals.modify;
    default:
      return ApplicationIcons.approve;
  }
};
const panel$1 = "_panel_8zdtn_1";
const styles$j = {
  panel: panel$1
};
const useCollapseTranscriptEvent = (scope, id) => {
  const collapsed = useStore((state) => state.transcriptCollapsedEvents);
  const collapseEvent = useStore((state) => state.setTranscriptCollapsedEvent);
  return reactExports.useMemo(() => {
    const isCollapsed = collapsed !== null && collapsed[scope]?.[id] === true;
    const set2 = (value2) => {
      collapseEvent(scope, id, value2);
    };
    return [isCollapsed, set2];
  }, [collapsed, collapseEvent, id]);
};
const tab = "_tab_1je38_1";
const styles$i = {
  tab
};
const EventNav = ({
  target,
  title: title2,
  selectedNav,
  setSelectedNav
}) => {
  const active = target === selectedNav;
  const handleClick = reactExports.useCallback(() => {
    setSelectedNav(target);
  }, [setSelectedNav, target]);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("li", { className: "nav-item", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
    "button",
    {
      type: "button",
      role: "tab",
      "aria-controls": target,
      "aria-selected": active,
      className: clsx(
        "nav-link",
        active ? "active " : "",
        "text-style-label",
        "text-size-small",
        styles$i.tab
      ),
      onClick: handleClick,
      children: title2
    }
  ) });
};
const navs$1 = "_navs_1vm6p_1";
const styles$h = {
  navs: navs$1
};
const EventNavs = ({
  navs: navs2,
  selectedNav,
  setSelectedNav
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "ul",
    {
      className: clsx("nav", "nav-pills", styles$h.navs),
      role: "tablist",
      "aria-orientation": "horizontal",
      children: navs2.map((nav) => {
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          EventNav,
          {
            target: nav.target,
            title: nav.title,
            selectedNav,
            setSelectedNav
          },
          nav.title
        );
      })
    }
  );
};
const label = "_label_1nn7f_1";
const navs = "_navs_1nn7f_6";
const card = "_card_1nn7f_12";
const cardContent = "_cardContent_1nn7f_20";
const hidden = "_hidden_1nn7f_25";
const copyLink = "_copyLink_1nn7f_33";
const hover = "_hover_1nn7f_41";
const root = "_root_1nn7f_45";
const bottomDongle = "_bottomDongle_1nn7f_50";
const dongleIcon = "_dongleIcon_1nn7f_67";
const styles$g = {
  label,
  navs,
  card,
  cardContent,
  hidden,
  copyLink,
  hover,
  root,
  bottomDongle,
  dongleIcon
};
const EventPanel = ({
  eventNodeId,
  depth,
  className: className2,
  title: title2,
  subTitle,
  text: text2,
  icon,
  children: children2,
  childIds,
  collapsibleContent,
  collapseControl = "top"
}) => {
  const [collapsed, setCollapsed] = useCollapseTranscriptEvent(
    kTranscriptCollapseScope,
    eventNodeId
  );
  const isCollapsible = (childIds || []).length > 0 || collapsibleContent;
  const useBottomDongle = isCollapsible && collapseControl === "bottom";
  const { getFullEventUrl } = useTranscriptNavigation();
  const url = isHostedEnvironment() ? getFullEventUrl(eventNodeId) : void 0;
  const pillId = (index) => {
    return `${eventNodeId}-nav-pill-${index}`;
  };
  const filteredArrChildren = (Array.isArray(children2) ? children2 : [children2]).filter((child) => !!child);
  const defaultPill = filteredArrChildren.findIndex((node2) => {
    return hasDataDefault(node2) && node2.props["data-default"];
  });
  const defaultPillId = defaultPill !== -1 ? pillId(defaultPill) : pillId(0);
  const [selectedNav, setSelectedNav] = useProperty(
    eventNodeId,
    "selectedNav",
    {
      defaultValue: defaultPillId
    }
  );
  const gridColumns = [];
  if (isCollapsible && !useBottomDongle) {
    gridColumns.push("minmax(0, max-content)");
  }
  if (icon) {
    gridColumns.push("max-content");
  }
  gridColumns.push("minmax(0, max-content)");
  if (url) {
    gridColumns.push("minmax(0, max-content)");
  }
  gridColumns.push("auto");
  gridColumns.push("minmax(0, max-content)");
  gridColumns.push("minmax(0, max-content)");
  const toggleCollapse = reactExports.useCallback(() => {
    setCollapsed(!collapsed);
  }, [setCollapsed, collapsed, childIds]);
  const [mouseOver, setMouseOver] = reactExports.useState(false);
  const titleEl = title2 || icon || filteredArrChildren.length > 1 ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      title: subTitle,
      className: clsx("text-size-small", mouseOver ? styles$g.hover : ""),
      style: {
        display: "grid",
        gridTemplateColumns: gridColumns.join(" "),
        columnGap: "0.3em",
        cursor: isCollapsible && !useBottomDongle ? "pointer" : void 0
      },
      onMouseEnter: () => setMouseOver(true),
      onMouseLeave: () => setMouseOver(false),
      children: [
        isCollapsible && !useBottomDongle ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          "i",
          {
            onClick: toggleCollapse,
            className: collapsed ? ApplicationIcons.chevron.right : ApplicationIcons.chevron.down
          }
        ) : "",
        icon ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          "i",
          {
            className: clsx(
              icon || ApplicationIcons.metadata,
              "text-style-secondary"
            ),
            onClick: toggleCollapse
          }
        ) : "",
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx("text-style-secondary", "text-style-label"),
            onClick: toggleCollapse,
            children: title2
          }
        ),
        url ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          CopyButton,
          {
            value: url,
            icon: ApplicationIcons.link,
            className: clsx(styles$g.copyLink)
          }
        ) : "",
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { onClick: toggleCollapse }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx("text-style-secondary", styles$g.label),
            onClick: toggleCollapse,
            children: collapsed ? text2 : ""
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$g.navs, children: isCollapsible && collapsibleContent && collapsed ? "" : filteredArrChildren && filteredArrChildren.length > 1 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          EventNavs,
          {
            navs: filteredArrChildren.map((child, index) => {
              const defaultTitle = `Tab ${index}`;
              const title22 = child && reactExports.isValidElement(child) ? child.props["data-name"] || defaultTitle : defaultTitle;
              return {
                id: `eventpanel-${eventNodeId}-${index}`,
                title: title22,
                target: pillId(index)
              };
            }),
            selectedNav: selectedNav || "",
            setSelectedNav
          }
        ) : "" })
      ]
    }
  ) : "";
  const card2 = /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      id: `event-panel-${eventNodeId}`,
      className: clsx(
        className2,
        styles$g.card,
        depth === 0 ? styles$g.root : void 0
      ),
      children: [
        titleEl,
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              "tab-content",
              styles$g.cardContent,
              isCollapsible && collapsed && collapsibleContent ? styles$g.hidden : void 0
            ),
            children: filteredArrChildren?.map((child, index) => {
              const id = pillId(index);
              const isSelected = id === selectedNav;
              return /* @__PURE__ */ jsxRuntimeExports.jsx(
                "div",
                {
                  id,
                  className: clsx("tab-pane", "show", isSelected ? "active" : ""),
                  children: child
                },
                `children-${id}-${index}`
              );
            })
          }
        ),
        isCollapsible && useBottomDongle ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            className: clsx(styles$g.bottomDongle, "text-size-smallest"),
            onClick: toggleCollapse,
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "i",
                {
                  className: clsx(
                    collapsed ? ApplicationIcons.chevron.right : ApplicationIcons.chevron.down,
                    styles$g.dongleIcon
                  )
                }
              ),
              "transcript (",
              childIds?.length,
              " ",
              childIds?.length === 1 ? "event" : "events",
              ")"
            ]
          }
        ) : void 0
      ]
    }
  );
  return card2;
};
function hasDataDefault(node2) {
  return reactExports.isValidElement(node2) && node2.props !== null && typeof node2.props === "object" && "data-default" in node2.props;
}
const formatTiming = (timestamp, working_start) => {
  if (working_start) {
    return `${formatDateTime(new Date(timestamp))}
@ working time: ${formatTime$1(working_start)}`;
  } else {
    return formatDateTime(new Date(timestamp));
  }
};
const formatTitle = (title2, total_tokens, working_start) => {
  const subItems = [];
  if (total_tokens) {
    subItems.push(`${formatNumber(total_tokens)} tokens`);
  }
  if (working_start) {
    subItems.push(`${formatTime$1(working_start)}`);
  }
  const subtitle = subItems.length > 0 ? ` (${subItems.join(", ")})` : "";
  return `${title2}${subtitle}`;
};
const CompactionEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  let data = {};
  if (event.tokens_before) {
    data["tokens_before"] = event.tokens_before;
  }
  if (event.tokens_after) {
    data["tokens_after"] = event.tokens_after;
  }
  data = { ...data, ...event.metadata || {} };
  const source = event.source && event.source !== "inspect" ? event.source : "";
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      title: formatTitle("Compaction" + source, void 0, event.working_start),
      className: className2,
      subTitle: formatDateTime(new Date(event.timestamp)),
      icon: ApplicationIcons.compaction,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx(MetaDataGrid, { entries: data, className: styles$j.panel })
    }
  );
};
const ErrorEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      title: "Error",
      className: className2,
      subTitle: event.timestamp ? formatDateTime(new Date(event.timestamp)) : void 0,
      icon: ApplicationIcons.error,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        ANSIDisplay,
        {
          output: event.error.traceback_ansi,
          style: {
            fontSize: "clamp(0.3rem, 1.1vw, 0.8rem)",
            margin: "0.5em 0"
          }
        }
      )
    }
  );
};
const panel = "_panel_vz394_1";
const styles$f = {
  panel
};
const InfoEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  const panels = [];
  if (typeof event.data === "string") {
    panels.push(
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        RenderedText,
        {
          markdown: event.data,
          className: clsx(styles$f.panel, "text-size-base")
        }
      )
    );
  } else {
    panels.push(/* @__PURE__ */ jsxRuntimeExports.jsx(JSONPanel, { data: event.data, className: styles$f.panel }));
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      title: "Info" + (event.source ? ": " + event.source : ""),
      className: className2,
      subTitle: event.timestamp ? formatDateTime(new Date(event.timestamp)) : void 0,
      icon: ApplicationIcons.info,
      children: panels
    }
  );
};
const InputEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      title: "Input",
      className: className2,
      subTitle: event.timestamp ? formatDateTime(new Date(event.timestamp)) : void 0,
      icon: ApplicationIcons.input,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        ANSIDisplay,
        {
          output: event.input_ansi,
          style: { fontSize: "clamp(0.4rem, 1.15vw, 0.9rem)" }
        }
      )
    }
  );
};
const grid = "_grid_1eq5o_1";
const styles$e = {
  grid
};
const LoggerEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  const obj = parsedJson(event.message.message);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventRow,
    {
      className: className2,
      title: event.message.level,
      icon: ApplicationIcons.logging[event.message.level.toLowerCase()] || ApplicationIcons.info,
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx("text-size-base", styles$e.grid), children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-smaller"), children: obj !== void 0 && obj !== null ? /* @__PURE__ */ jsxRuntimeExports.jsx(MetaDataGrid, { entries: obj }) : event.message.message }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx("text-size-smaller", "text-style-secondary"), children: [
          event.message.filename,
          ":",
          event.message.lineno
        ] })
      ] })
    }
  );
};
const wrapper$1 = "_wrapper_sq96g_1";
const col2$1 = "_col2_sq96g_8";
const col1_3$1 = "_col1_3_sq96g_12";
const col3$1 = "_col3_sq96g_16";
const separator$3 = "_separator_sq96g_20";
const padded = "_padded_sq96g_26";
const styles$d = {
  wrapper: wrapper$1,
  col2: col2$1,
  col1_3: col1_3$1,
  col3: col3$1,
  separator: separator$3,
  padded
};
const ModelUsagePanel = ({ usage, className: className2 }) => {
  if (!usage) {
    return null;
  }
  const rows = [];
  if (usage.reasoning_tokens) {
    rows.push({
      label: "Reasoning",
      value: usage.reasoning_tokens,
      secondary: false,
      bordered: true
    });
    rows.push({
      label: "---",
      value: void 0,
      secondary: false,
      padded: true
    });
  }
  rows.push({
    label: "input",
    value: usage.input_tokens,
    secondary: false
  });
  if (usage.input_tokens_cache_read) {
    rows.push({
      label: "cache_read",
      value: usage.input_tokens_cache_read,
      secondary: true
    });
  }
  if (usage.input_tokens_cache_write) {
    rows.push({
      label: "cache_write",
      value: usage.input_tokens_cache_write,
      secondary: true
    });
  }
  rows.push({
    label: "Output",
    value: usage.output_tokens,
    secondary: false,
    bordered: true
  });
  rows.push({
    label: "---",
    value: void 0,
    secondary: false
  });
  rows.push({
    label: "Total",
    value: usage.total_tokens,
    secondary: false
  });
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-small", styles$d.wrapper, className2), children: rows.map((row2, idx) => {
    if (row2.label === "---") {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: clsx(
            styles$d.separator,
            row2.padded ? styles$d.padded : void 0
          )
        },
        `$usage-sep-${idx}`
      );
    } else {
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              "text-style-label",
              "text-style-secondary",
              row2.secondary ? styles$d.col2 : styles$d.col1_3
            ),
            children: row2.label
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$d.col3, children: row2.value ? formatNumber(row2.value) : "" })
      ] }, `$usage-row-${idx}`);
    }
  }) });
};
const container$2 = "_container_1ww70_1";
const titleRow = "_titleRow_1ww70_5";
const title = "_title_1ww70_5";
const styles$c = {
  container: container$2,
  titleRow,
  title
};
const EventSection = ({
  title: title2,
  children: children2,
  copyContent,
  className: className2
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$c.container, className2), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$c.titleRow), children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx("text-size-small", "text-style-label", styles$c.title),
        children: [
          title2,
          copyContent ? /* @__PURE__ */ jsxRuntimeExports.jsx(CopyButton, { value: copyContent, ariaLabel: "Copy to clipboard" }) : null
        ]
      }
    ) }),
    children2
  ] });
};
const wrapper = "_wrapper_45f60_1";
const col2 = "_col2_45f60_8";
const col1_3 = "_col1_3_45f60_12";
const col3 = "_col3_45f60_16";
const separator$2 = "_separator_45f60_20";
const topMargin = "_topMargin_45f60_26";
const styles$b = {
  wrapper,
  col2,
  col1_3,
  col3,
  separator: separator$2,
  topMargin
};
const EventTimingPanel = ({
  timestamp,
  completed,
  working_start,
  working_time
}) => {
  const rows = [
    {
      label: "Clock Time",
      value: void 0,
      secondary: false
    },
    {
      label: "---",
      value: void 0,
      secondary: false
    }
  ];
  if (!completed) {
    rows.push({
      label: "Timestamp",
      value: formatDateTime(new Date(timestamp))
    });
  } else {
    rows.push({ label: "Start", value: formatDateTime(new Date(timestamp)) });
    rows.push({ label: "End", value: formatDateTime(new Date(completed)) });
  }
  if (working_start || working_time) {
    rows.push({
      label: "Working Time",
      value: void 0,
      secondary: false,
      topMargin: true
    });
    rows.push({
      label: "---",
      value: void 0,
      secondary: false
    });
    if (working_start) {
      rows.push({
        label: "Start",
        value: formatTime$1(working_start)
      });
    }
    if (working_time) {
      rows.push({
        label: "Duration",
        value: formatTime$1(working_time)
      });
    }
    if (working_start && working_time) {
      rows.push({
        label: "End",
        value: formatTime$1(
          Math.round(working_start * 10) / 10 + Math.round(working_time * 10) / 10
        )
      });
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-small", styles$b.wrapper), children: rows.map((row2, idx) => {
    if (row2.label === "---") {
      return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$b.separator }, `$usage-sep-${idx}`);
    } else {
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              "text-style-label",
              "text-style-secondary",
              row2.secondary ? styles$b.col2 : styles$b.col1_3,
              row2.topMargin ? styles$b.topMargin : void 0
            ),
            children: row2.label
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$b.col3, children: row2.value ? row2.value : "" })
      ] }, `$usage-row-${idx}`);
    }
  }) });
};
const container$1 = "_container_e0l2n_1";
const all = "_all_e0l2n_6";
const tableSelection = "_tableSelection_e0l2n_12";
const codePre = "_codePre_e0l2n_22";
const code$1 = "_code_e0l2n_22";
const progress$1 = "_progress_e0l2n_34";
const toolConfig = "_toolConfig_e0l2n_38";
const toolChoice = "_toolChoice_e0l2n_46";
const styles$a = {
  container: container$1,
  all,
  tableSelection,
  codePre,
  code: code$1,
  progress: progress$1,
  toolConfig,
  toolChoice
};
const ModelEventView = ({
  eventNode,
  showToolCalls,
  className: className2,
  context
}) => {
  const event = eventNode.event;
  const totalUsage = event.output.usage?.total_tokens;
  const callTime = event.output.time;
  const outputMessages = event.output.choices?.map((choice) => {
    return choice.message;
  });
  const entries = { ...event.config };
  delete entries["max_connections"];
  const userMessages = [];
  let offset = void 0;
  const lastMessage = event.input.at(-1);
  if (lastMessage?.role === "assistant") {
    userMessages.push(lastMessage);
    offset = -1;
  }
  for (const msg of event.input.slice(offset).reverse()) {
    if (msg.role === "user" && !msg.tool_call_id || msg.role === "system" || // If the client doesn't support tool events, then tools messages are allowed to be displayed
    // in this view, since no tool events will be shown. This pretty much happens for bridged agents
    // where tool events aren't captured.
    context?.hasToolEvents === false && msg.role === "tool") {
      userMessages.unshift(msg);
    } else {
      break;
    }
  }
  const panelTitle = event.role ? `Model Call (${event.role}): ${event.model}` : `Model Call: ${event.model}`;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      className: className2,
      title: formatTitle(panelTitle, totalUsage, callTime),
      subTitle: event.timestamp ? formatTiming(event.timestamp, event.working_start) : void 0,
      icon: ApplicationIcons.model,
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { "data-name": "Summary", className: styles$a.container, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            ChatView,
            {
              id: `${eventNode.id}-model-output`,
              messages: [...userMessages, ...outputMessages || []],
              toolCallStyle: showToolCalls ? "complete" : "omit",
              resolveToolCallsIntoPreviousMessage: context?.hasToolEvents !== false,
              allowLinking: false,
              showLabels: false
            }
          ),
          event.pending ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$a.progress), children: /* @__PURE__ */ jsxRuntimeExports.jsx(PulsingDots, { subtle: false, size: "medium" }) }) : void 0
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { "data-name": "All", className: styles$a.container, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: styles$a.all, children: [
            Object.keys(entries).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(
              EventSection,
              {
                title: "Configuration",
                className: styles$a.tableSelection,
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(MetaDataGrid, { entries, options: { plain: true } })
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: "Usage", className: styles$a.tableSelection, children: event.output.usage !== null ? /* @__PURE__ */ jsxRuntimeExports.jsx(ModelUsagePanel, { usage: event.output.usage }) : void 0 }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: "Timing", className: styles$a.tableSelection, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              EventTimingPanel,
              {
                timestamp: event.timestamp,
                completed: event.completed,
                working_start: event.working_start,
                working_time: event.working_time
              }
            ) })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: "Messages", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            ChatView,
            {
              id: `${eventNode.id}-model-input-full`,
              messages: [...event.input, ...outputMessages || []],
              resolveToolCallsIntoPreviousMessage: context?.hasToolEvents !== false,
              allowLinking: false
            }
          ) })
        ] }),
        event.tools.length > 1 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { "data-name": "Tools", className: styles$a.container, children: /* @__PURE__ */ jsxRuntimeExports.jsx(ToolsConfig, { tools: event.tools, toolChoice: event.tool_choice }) }),
        event.call ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          APIView,
          {
            "data-name": "API",
            call: event.call,
            className: styles$a.container
          }
        ) : ""
      ]
    }
  );
};
const APIView = ({ call, className: className2 }) => {
  const requestCode = reactExports.useMemo(() => {
    return JSON.stringify(call.request, void 0, 2);
  }, [call.request]);
  const responseCode = reactExports.useMemo(() => {
    return JSON.stringify(call.response, void 0, 2);
  }, [call.response]);
  if (!call) {
    return null;
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(className2), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: "Request", copyContent: requestCode, children: /* @__PURE__ */ jsxRuntimeExports.jsx(APICodeCell, { sourceCode: requestCode }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: "Response", copyContent: responseCode, children: /* @__PURE__ */ jsxRuntimeExports.jsx(APICodeCell, { sourceCode: responseCode }) })
  ] });
};
const APICodeCell = ({ id, sourceCode }) => {
  const sourceCodeRef = reactExports.useRef(null);
  usePrismHighlight(sourceCodeRef, sourceCode.length);
  if (!sourceCode) {
    return null;
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { ref: sourceCodeRef, className: clsx("model-call"), children: /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: clsx(styles$a.codePre), children: /* @__PURE__ */ jsxRuntimeExports.jsx(
    "code",
    {
      id,
      className: clsx("language-json", styles$a.code, "text-size-small"),
      children: sourceCode
    }
  ) }) });
};
const ToolsConfig = ({ tools: tools2, toolChoice: toolChoice2 }) => {
  const toolEls = tools2.map((tool2, idx) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-style-label", "text-style-secondary"), children: tool2.name }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: tool2.description })
    ] }, `${tool2.name}-${idx}`);
  });
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$a.toolConfig, "text-size-small"), children: toolEls }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$a.toolChoice, "text-size-small"), children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-style-label", "text-style-secondary"), children: "Tool Choice" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsx(ToolChoiceView, { toolChoice: toolChoice2 }) })
    ] })
  ] });
};
const ToolChoiceView = ({ toolChoice: toolChoice2 }) => {
  if (typeof toolChoice2 === "string") {
    return toolChoice2;
  } else {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("code", { children: [
      "`$",
      toolChoice2.name,
      "()`"
    ] });
  }
};
const noMargin = "_noMargin_1a3fk_1";
const code = "_code_1a3fk_5";
const sample = "_sample_1a3fk_10";
const section$1 = "_section_1a3fk_14";
const metadata = "_metadata_1a3fk_21";
const styles$9 = {
  noMargin,
  code,
  sample,
  section: section$1,
  metadata
};
const SampleInitEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  const stateObj = event.state;
  const sections = [];
  if (event.sample.files && Object.keys(event.sample.files).length > 0) {
    sections.push(
      /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: "Files", children: Object.keys(event.sample.files).map((file) => {
        return /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: styles$9.noMargin, children: file }, `sample-init-file-${file}`);
      }) }, `event-${eventNode.id}`)
    );
  }
  if (event.sample.setup) {
    sections.push(
      /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: "Setup", children: /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: styles$9.code, children: /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "sourceCode", children: event.sample.setup }) }) }, `${eventNode.id}-section-setup`)
    );
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      className: className2,
      title: "Sample",
      icon: ApplicationIcons.sample,
      subTitle: event.timestamp ? formatDateTime(new Date(event.timestamp)) : void 0,
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { "data-name": "Sample", className: styles$9.sample, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            ChatView,
            {
              messages: stateObj["messages"],
              allowLinking: false
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            event.sample.choices ? event.sample.choices.map((choice, index) => {
              return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                String.fromCharCode(65 + index),
                ") ",
                choice
              ] }, `$choice-{choice}`);
            }) : "",
            sections.length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$9.section, children: sections }) : "",
            event.sample.target ? /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: "Target", children: toArray(event.sample.target).map((target) => {
              return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-base"), children: target }, target);
            }) }) : void 0
          ] })
        ] }),
        event.sample.metadata && Object.keys(event.sample.metadata).length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          MetaDataGrid,
          {
            "data-name": "Metadata",
            className: styles$9.metadata,
            entries: event.sample.metadata
          }
        ) : ""
      ]
    }
  );
};
const SampleLimitEventView = ({
  eventNode,
  className: className2
}) => {
  const resolve_title = (type) => {
    switch (type) {
      case "custom":
        return "Custom Limit Exceeded";
      case "time":
        return "Time Limit Exceeded";
      case "message":
        return "Message Limit Exceeded";
      case "token":
        return "Token Limit Exceeded";
      case "operator":
        return "Operator Canceled";
      case "working":
        return "Execution Time Limit Exceeded";
      case "cost":
        return "Cost Limit Exceeded";
    }
  };
  const resolve_icon = (type) => {
    switch (type) {
      case "custom":
        return ApplicationIcons.limits.custom;
      case "time":
        return ApplicationIcons.limits.time;
      case "message":
        return ApplicationIcons.limits.messages;
      case "token":
        return ApplicationIcons.limits.tokens;
      case "operator":
        return ApplicationIcons.limits.operator;
      case "working":
        return ApplicationIcons.limits.execution;
      case "cost":
        return ApplicationIcons.limits.cost;
    }
  };
  const title2 = resolve_title(eventNode.event.type);
  const icon = resolve_icon(eventNode.event.type);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      title: title2,
      icon,
      className: className2,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-smaller"), children: eventNode.event.message })
    }
  );
};
const twoColumn = "_twoColumn_1irga_9";
const exec = "_exec_1irga_15";
const result = "_result_1irga_19";
const fileLabel = "_fileLabel_1irga_23";
const wrapPre = "_wrapPre_1irga_28";
const styles$8 = {
  twoColumn,
  exec,
  result,
  fileLabel,
  wrapPre
};
const SandboxEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      className: className2,
      title: `Sandbox: ${event.action}`,
      icon: ApplicationIcons.sandbox,
      subTitle: event.timestamp ? formatTiming(event.timestamp, event.working_start) : void 0,
      children: event.action === "exec" ? /* @__PURE__ */ jsxRuntimeExports.jsx(ExecView, { id: `${eventNode.id}-exec`, event }) : event.action === "read_file" ? /* @__PURE__ */ jsxRuntimeExports.jsx(ReadFileView, { id: `${eventNode.id}-read-file`, event }) : /* @__PURE__ */ jsxRuntimeExports.jsx(WriteFileView, { id: `${eventNode.id}-write-file`, event })
    }
  );
};
const ExecView = ({ id, event }) => {
  if (event.cmd === null) {
    return void 0;
  }
  const cmd = event.cmd;
  const options = event.options;
  const input = event.input;
  const result2 = event.result;
  const output2 = event.output ? event.output.trim() : void 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$8.exec), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: `Command`, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$8.twoColumn), children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: clsx(styles$8.wrapPre), children: cmd }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: clsx(styles$8.wrapPre), children: input !== null ? input?.trim() : void 0 }),
      options !== null && Object.keys(options).length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: `Options`, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        MetaDataGrid,
        {
          entries: options,
          options: { plain: true }
        }
      ) }) : void 0
    ] }) }),
    output2 || result2 !== null && result2 !== 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs(EventSection, { title: `Result`, children: [
      output2 ? /* @__PURE__ */ jsxRuntimeExports.jsx(ExpandablePanel, { id: `${id}-output`, collapse: false, children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        RenderedContent,
        {
          id: `${id}-output-content`,
          entry: { name: "sandbox_output", value: output2 }
        }
      ) }) : void 0,
      result2 !== 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$8.result, "text-size-base"), children: [
        "(exited with code ",
        result2,
        ")"
      ] }) : void 0
    ] }) : void 0
  ] });
};
const ReadFileView = ({ id, event }) => {
  if (event.file === null) {
    return void 0;
  }
  const file = event.file;
  const output2 = event.output;
  return /* @__PURE__ */ jsxRuntimeExports.jsx(FileView, { id, file, contents: output2?.trim() });
};
const WriteFileView = ({ id, event }) => {
  if (event.file === null) {
    return void 0;
  }
  const file = event.file;
  const input = event.input;
  return /* @__PURE__ */ jsxRuntimeExports.jsx(FileView, { id, file, contents: input?.trim() });
};
const FileView = ({ id, file, contents: contents2 }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: "File", children: /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: clsx(styles$8.fileLabel), children: file }) }),
    contents2 ? /* @__PURE__ */ jsxRuntimeExports.jsx(EventSection, { title: "Contents", children: /* @__PURE__ */ jsxRuntimeExports.jsx(ExpandablePanel, { id: `${id}-file`, collapse: false, children: /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { children: contents2 }) }) }) : void 0
  ] });
};
const ScoreValue = ({ score, className: className2 }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(className2), children: renderScore(score) });
};
const renderScore = (value2) => {
  if (Array.isArray(value2)) {
    return value2.join(", ");
  } else if (isRecord(value2) && typeof value2 === "object") {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(MetaDataGrid, { entries: value2 });
  } else {
    return String(value2);
  }
};
const container = "_container_io1r0_1";
const wrappingContent$1 = "_wrappingContent_io1r0_8";
const separator$1 = "_separator_io1r0_13";
const unchanged = "_unchanged_io1r0_22";
const section = "_section_io1r0_27";
const spacer = "_spacer_io1r0_31";
const styles$7 = {
  container,
  wrappingContent: wrappingContent$1,
  separator: separator$1,
  unchanged,
  section,
  spacer
};
const kUnchangedSentinel = "UNCHANGED";
const ScoreEditEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  const subtitle = event.edit.provenance ? `[${event.edit.provenance.timestamp ? formatDateTime(new Date(event.edit.provenance.timestamp)) : void 0}] ${event.edit.provenance.author}: ${event.edit.provenance.reason || ""}` : void 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      title: "Edit Score",
      className: clsx(className2, "text-size-small"),
      subTitle: subtitle,
      collapsibleContent: true,
      icon: ApplicationIcons.edit,
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { "data-name": "Summary", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: clsx(
              "text-style-label",
              "text-style-secondary",
              styles$7.section
            ),
            children: "Updated Values"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$7.container), children: [
          event.edit.value ? /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.separator) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-style-label", children: "Value" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(ScoreValue, { score: event.edit.value })
          ] }) : "",
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.separator) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-style-label", children: "Answer" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.wrappingContent), children: event.edit.answer === kUnchangedSentinel ? /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: clsx(styles$7.unchanged), children: "[unchanged]" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(RenderedText, { markdown: event.edit.answer || "" }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.separator) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-style-label", children: "Explanation" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.wrappingContent), children: /* @__PURE__ */ jsxRuntimeExports.jsx(RenderedText, { markdown: event.edit.explanation || "" }) })
        ] }),
        event.edit.provenance ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$7.container), children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: clsx(
                "text-style-label",
                "text-style-secondary",
                styles$7.section
              ),
              children: "Provenance"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.spacer) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.separator) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-style-label", children: "Author" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.wrappingContent), children: /* @__PURE__ */ jsxRuntimeExports.jsx(RenderedText, { markdown: event.edit.provenance.author }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.separator) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-style-label", children: "Reason" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.wrappingContent), children: /* @__PURE__ */ jsxRuntimeExports.jsx(RenderedText, { markdown: event.edit.provenance.reason || "" }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.separator) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-style-label", children: "Time" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$7.wrappingContent), children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            RenderedText,
            {
              markdown: event.edit.provenance.timestamp ? formatDateTime(new Date(event.edit.provenance.timestamp)) : ""
            }
          ) })
        ] }) : "",
        event.edit.metadata && event.edit.metadata !== kUnchangedSentinel ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { "data-name": "Metadata", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          RecordTree,
          {
            id: `${eventNode.id}-score-metadata`,
            record: event.edit.metadata || {},
            className: styles$7.metadataTree,
            defaultExpandLevel: 0
          }
        ) }) : void 0
      ] })
    }
  );
};
const explanation = "_explanation_1k2k0_1";
const wrappingContent = "_wrappingContent_1k2k0_8";
const separator = "_separator_1k2k0_13";
const styles$6 = {
  explanation,
  wrappingContent,
  separator
};
const ScoreEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  const resolvedTarget = event.target ? Array.isArray(event.target) ? event.target.join("\n") : event.target : void 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      title: (event.intermediate ? "Intermediate " : "") + "Score",
      className: clsx(className2, "text-size-small"),
      subTitle: event.timestamp ? formatDateTime(new Date(event.timestamp)) : void 0,
      icon: ApplicationIcons.scorer,
      collapsibleContent: true,
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { "data-name": "Explanation", className: clsx(styles$6.explanation), children: [
          event.target ? /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$6.separator) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-style-label", children: "Target" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsx(RenderedText, { markdown: resolvedTarget || "" }) })
          ] }) : "",
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$6.separator) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-style-label", children: "Answer" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$6.wrappingContent), children: /* @__PURE__ */ jsxRuntimeExports.jsx(RenderedText, { markdown: event.score.answer || "" }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$6.separator) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-style-label", children: "Explanation" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$6.wrappingContent), children: /* @__PURE__ */ jsxRuntimeExports.jsx(RenderedText, { markdown: event.score.explanation || "" }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$6.separator) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-style-label", children: "Score" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(ScoreValue, { score: event.score.value }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$6.separator) })
        ] }),
        event.score.metadata ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { "data-name": "Metadata", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          RecordTree,
          {
            id: `${eventNode.id}-score-metadata`,
            record: event.score.metadata,
            className: styles$6.metadataTree,
            defaultExpandLevel: 0
          }
        ) }) : void 0
      ]
    }
  );
};
const SpanEventView = ({
  eventNode,
  children: children2,
  className: className2
}) => {
  const event = eventNode.event;
  const descriptor = spanDescriptor(event);
  const title2 = descriptor.name || `${event.type ? event.type + ": " : "Step: "}${event.name}`;
  const text2 = reactExports.useMemo(() => summarize$1(children2), [children2]);
  const childIds = reactExports.useMemo(() => children2.map((child) => child.id), [children2]);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      childIds,
      className: clsx("transcript-span", className2),
      title: title2,
      subTitle: event.timestamp ? formatDateTime(new Date(event.timestamp)) : void 0,
      text: text2,
      icon: descriptor.icon
    }
  );
};
const summarize$1 = (children2) => {
  if (children2.length === 0) {
    return "(no events)";
  }
  const formatEvent = (event, count) => {
    if (count === 1) {
      return `${count} ${event} event`;
    } else {
      return `${count} ${event} events`;
    }
  };
  const typeCount = {};
  children2.forEach((child) => {
    const currentCount = typeCount[child.event.event] || 0;
    typeCount[child.event.event] = currentCount + 1;
  });
  const numberOfTypes = Object.keys(typeCount).length;
  if (numberOfTypes < 3) {
    return Object.keys(typeCount).map((key2) => {
      return formatEvent(key2, typeCount[key2] || 0);
    }).join(", ");
  }
  if (children2.length === 1) {
    return "1 event";
  } else {
    return `${children2.length} events`;
  }
};
const spanDescriptor = (event) => {
  const rootStepDescriptor = {
    endSpace: true
  };
  if (event.type === "solver") {
    switch (event.name) {
      case "chain_of_thought":
        return {
          ...rootStepDescriptor
        };
      case "generate":
        return {
          ...rootStepDescriptor
        };
      case "self_critique":
        return {
          ...rootStepDescriptor
        };
      case "system_message":
        return {
          ...rootStepDescriptor
        };
      case "use_tools":
        return {
          ...rootStepDescriptor
        };
      case "multiple_choice":
        return {
          ...rootStepDescriptor
        };
      default:
        return {
          ...rootStepDescriptor
        };
    }
  } else if (event.type === "scorer") {
    return {
      ...rootStepDescriptor
    };
  } else if (event.event === "span_begin") {
    if (event.span_id === kSandboxSignalName) {
      return {
        ...rootStepDescriptor,
        name: "Sandbox Events"
      };
    } else if (event.name === "init") {
      return {
        ...rootStepDescriptor,
        name: "Init"
      };
    } else {
      return {
        ...rootStepDescriptor
      };
    }
  } else {
    switch (event.name) {
      case "sample_init":
        return {
          ...rootStepDescriptor,
          name: "Sample Init"
        };
      default:
        return {
          endSpace: false
        };
    }
  }
};
function cloneRegExp(re2) {
  var _a2;
  const regexMatch = /^\/(.*)\/([gimyu]*)$/.exec(re2.toString());
  if (!regexMatch) {
    throw new Error("Invalid RegExp");
  }
  return new RegExp((_a2 = regexMatch[1]) !== null && _a2 !== void 0 ? _a2 : "", regexMatch[2]);
}
function clone(arg) {
  if (typeof arg !== "object") {
    return arg;
  }
  if (arg === null) {
    return null;
  }
  if (Array.isArray(arg)) {
    return arg.map(clone);
  }
  if (arg instanceof Date) {
    return new Date(arg.getTime());
  }
  if (arg instanceof RegExp) {
    return cloneRegExp(arg);
  }
  const cloned = {};
  for (const name in arg) {
    if (Object.prototype.hasOwnProperty.call(arg, name)) {
      cloned[name] = clone(arg[name]);
    }
  }
  return cloned;
}
function assertNonEmptyArray(arr, message2) {
  if (arr.length === 0) {
    throw new Error("Expected a non-empty array");
  }
}
function assertArrayHasAtLeast2(arr, message2) {
  if (arr.length < 2) {
    throw new Error("Expected an array with at least 2 items");
  }
}
const lastNonEmpty = (arr) => arr[arr.length - 1];
class Context {
  setResult(result2) {
    this.result = result2;
    this.hasResult = true;
    return this;
  }
  exit() {
    this.exiting = true;
    return this;
  }
  push(child, name) {
    child.parent = this;
    if (typeof name !== "undefined") {
      child.childName = name;
    }
    child.root = this.root || this;
    child.options = child.options || this.options;
    if (!this.children) {
      this.children = [child];
      this.nextAfterChildren = this.next || null;
      this.next = child;
    } else {
      assertNonEmptyArray(this.children);
      lastNonEmpty(this.children).next = child;
      this.children.push(child);
    }
    child.next = this;
    return this;
  }
}
class DiffContext extends Context {
  constructor(left, right) {
    super();
    this.left = left;
    this.right = right;
    this.pipe = "diff";
  }
  prepareDeltaResult(result2) {
    var _a2, _b, _c, _d;
    if (typeof result2 === "object") {
      if (((_a2 = this.options) === null || _a2 === void 0 ? void 0 : _a2.omitRemovedValues) && Array.isArray(result2) && result2.length > 1 && (result2.length === 2 || // modified
      result2[2] === 0 || // deleted
      result2[2] === 3)) {
        result2[0] = 0;
      }
      if ((_b = this.options) === null || _b === void 0 ? void 0 : _b.cloneDiffValues) {
        const clone$1 = typeof ((_c = this.options) === null || _c === void 0 ? void 0 : _c.cloneDiffValues) === "function" ? (_d = this.options) === null || _d === void 0 ? void 0 : _d.cloneDiffValues : clone;
        if (typeof result2[0] === "object") {
          result2[0] = clone$1(result2[0]);
        }
        if (typeof result2[1] === "object") {
          result2[1] = clone$1(result2[1]);
        }
      }
    }
    return result2;
  }
  setResult(result2) {
    this.prepareDeltaResult(result2);
    return super.setResult(result2);
  }
}
class PatchContext extends Context {
  constructor(left, delta) {
    super();
    this.left = left;
    this.delta = delta;
    this.pipe = "patch";
  }
}
class ReverseContext extends Context {
  constructor(delta) {
    super();
    this.delta = delta;
    this.pipe = "reverse";
  }
}
class Pipe {
  constructor(name) {
    this.name = name;
    this.filters = [];
  }
  process(input) {
    if (!this.processor) {
      throw new Error("add this pipe to a processor before using it");
    }
    const debug = this.debug;
    const length = this.filters.length;
    const context = input;
    for (let index = 0; index < length; index++) {
      const filter = this.filters[index];
      if (!filter)
        continue;
      if (debug) {
        this.log(`filter: ${filter.filterName}`);
      }
      filter(context);
      if (typeof context === "object" && context.exiting) {
        context.exiting = false;
        break;
      }
    }
    if (!context.next && this.resultCheck) {
      this.resultCheck(context);
    }
  }
  log(msg) {
    console.log(`[jsondiffpatch] ${this.name} pipe, ${msg}`);
  }
  append(...args2) {
    this.filters.push(...args2);
    return this;
  }
  prepend(...args2) {
    this.filters.unshift(...args2);
    return this;
  }
  indexOf(filterName) {
    if (!filterName) {
      throw new Error("a filter name is required");
    }
    for (let index = 0; index < this.filters.length; index++) {
      const filter = this.filters[index];
      if ((filter === null || filter === void 0 ? void 0 : filter.filterName) === filterName) {
        return index;
      }
    }
    throw new Error(`filter not found: ${filterName}`);
  }
  list() {
    return this.filters.map((f) => f.filterName);
  }
  after(filterName, ...params) {
    const index = this.indexOf(filterName);
    this.filters.splice(index + 1, 0, ...params);
    return this;
  }
  before(filterName, ...params) {
    const index = this.indexOf(filterName);
    this.filters.splice(index, 0, ...params);
    return this;
  }
  replace(filterName, ...params) {
    const index = this.indexOf(filterName);
    this.filters.splice(index, 1, ...params);
    return this;
  }
  remove(filterName) {
    const index = this.indexOf(filterName);
    this.filters.splice(index, 1);
    return this;
  }
  clear() {
    this.filters.length = 0;
    return this;
  }
  shouldHaveResult(should) {
    if (should === false) {
      this.resultCheck = null;
      return this;
    }
    if (this.resultCheck) {
      return this;
    }
    this.resultCheck = (context) => {
      if (!context.hasResult) {
        console.log(context);
        const error2 = new Error(`${this.name} failed`);
        error2.noResult = true;
        throw error2;
      }
    };
    return this;
  }
}
class Processor {
  constructor(options) {
    this.selfOptions = options || {};
    this.pipes = {};
  }
  options(options) {
    if (options) {
      this.selfOptions = options;
    }
    return this.selfOptions;
  }
  pipe(name, pipeArg) {
    let pipe = pipeArg;
    if (typeof name === "string") {
      if (typeof pipe === "undefined") {
        return this.pipes[name];
      }
      this.pipes[name] = pipe;
    }
    if (name && name.name) {
      pipe = name;
      if (pipe.processor === this) {
        return pipe;
      }
      this.pipes[pipe.name] = pipe;
    }
    if (!pipe) {
      throw new Error(`pipe is not defined: ${name}`);
    }
    pipe.processor = this;
    return pipe;
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  process(input, pipe) {
    let context = input;
    context.options = this.options();
    let nextPipe = pipe || input.pipe || "default";
    let lastPipe = void 0;
    while (nextPipe) {
      if (typeof context.nextAfterChildren !== "undefined") {
        context.next = context.nextAfterChildren;
        context.nextAfterChildren = null;
      }
      if (typeof nextPipe === "string") {
        nextPipe = this.pipe(nextPipe);
      }
      nextPipe.process(context);
      lastPipe = nextPipe;
      nextPipe = null;
      if (context) {
        if (context.next) {
          context = context.next;
          nextPipe = context.pipe || lastPipe;
        }
      }
    }
    return context.hasResult ? context.result : void 0;
  }
}
const defaultMatch = (array1, array2, index1, index2) => array1[index1] === array2[index2];
const lengthMatrix = (array1, array2, match2, context) => {
  var _a2, _b, _c;
  const len1 = array1.length;
  const len2 = array2.length;
  let x2;
  let y;
  const matrix = new Array(len1 + 1);
  for (x2 = 0; x2 < len1 + 1; x2++) {
    const matrixNewRow = new Array(len2 + 1);
    for (y = 0; y < len2 + 1; y++) {
      matrixNewRow[y] = 0;
    }
    matrix[x2] = matrixNewRow;
  }
  matrix.match = match2;
  for (x2 = 1; x2 < len1 + 1; x2++) {
    const matrixRowX = matrix[x2];
    if (matrixRowX === void 0) {
      throw new Error("LCS matrix row is undefined");
    }
    const matrixRowBeforeX = matrix[x2 - 1];
    if (matrixRowBeforeX === void 0) {
      throw new Error("LCS matrix row is undefined");
    }
    for (y = 1; y < len2 + 1; y++) {
      if (match2(array1, array2, x2 - 1, y - 1, context)) {
        matrixRowX[y] = ((_a2 = matrixRowBeforeX[y - 1]) !== null && _a2 !== void 0 ? _a2 : 0) + 1;
      } else {
        matrixRowX[y] = Math.max((_b = matrixRowBeforeX[y]) !== null && _b !== void 0 ? _b : 0, (_c = matrixRowX[y - 1]) !== null && _c !== void 0 ? _c : 0);
      }
    }
  }
  return matrix;
};
const backtrack = (matrix, array1, array2, context) => {
  let index1 = array1.length;
  let index2 = array2.length;
  const subsequence = {
    sequence: [],
    indices1: [],
    indices2: []
  };
  while (index1 !== 0 && index2 !== 0) {
    if (matrix.match === void 0) {
      throw new Error("LCS matrix match function is undefined");
    }
    const sameLetter = matrix.match(array1, array2, index1 - 1, index2 - 1, context);
    if (sameLetter) {
      subsequence.sequence.unshift(array1[index1 - 1]);
      subsequence.indices1.unshift(index1 - 1);
      subsequence.indices2.unshift(index2 - 1);
      --index1;
      --index2;
    } else {
      const matrixRowIndex1 = matrix[index1];
      if (matrixRowIndex1 === void 0) {
        throw new Error("LCS matrix row is undefined");
      }
      const valueAtMatrixAbove = matrixRowIndex1[index2 - 1];
      if (valueAtMatrixAbove === void 0) {
        throw new Error("LCS matrix value is undefined");
      }
      const matrixRowBeforeIndex1 = matrix[index1 - 1];
      if (matrixRowBeforeIndex1 === void 0) {
        throw new Error("LCS matrix row is undefined");
      }
      const valueAtMatrixLeft = matrixRowBeforeIndex1[index2];
      if (valueAtMatrixLeft === void 0) {
        throw new Error("LCS matrix value is undefined");
      }
      if (valueAtMatrixAbove > valueAtMatrixLeft) {
        --index2;
      } else {
        --index1;
      }
    }
  }
  return subsequence;
};
const get = (array1, array2, match2, context) => {
  const innerContext = context || {};
  const matrix = lengthMatrix(array1, array2, match2 || defaultMatch, innerContext);
  return backtrack(matrix, array1, array2, innerContext);
};
const lcs = {
  get
};
const ARRAY_MOVE = 3;
function arraysHaveMatchByRef(array1, array2, len1, len2) {
  for (let index1 = 0; index1 < len1; index1++) {
    const val1 = array1[index1];
    for (let index2 = 0; index2 < len2; index2++) {
      const val2 = array2[index2];
      if (index1 !== index2 && val1 === val2) {
        return true;
      }
    }
  }
  return false;
}
function matchItems(array1, array2, index1, index2, context) {
  const value1 = array1[index1];
  const value2 = array2[index2];
  if (value1 === value2) {
    return true;
  }
  if (typeof value1 !== "object" || typeof value2 !== "object") {
    return false;
  }
  const objectHash = context.objectHash;
  if (!objectHash) {
    return context.matchByPosition && index1 === index2;
  }
  context.hashCache1 = context.hashCache1 || [];
  let hash1 = context.hashCache1[index1];
  if (typeof hash1 === "undefined") {
    context.hashCache1[index1] = hash1 = objectHash(value1, index1);
  }
  if (typeof hash1 === "undefined") {
    return false;
  }
  context.hashCache2 = context.hashCache2 || [];
  let hash2 = context.hashCache2[index2];
  if (typeof hash2 === "undefined") {
    context.hashCache2[index2] = hash2 = objectHash(value2, index2);
  }
  if (typeof hash2 === "undefined") {
    return false;
  }
  return hash1 === hash2;
}
const diffFilter$3 = function arraysDiffFilter(context) {
  var _a2, _b, _c, _d, _e2;
  if (!context.leftIsArray) {
    return;
  }
  const matchContext = {
    objectHash: (_a2 = context.options) === null || _a2 === void 0 ? void 0 : _a2.objectHash,
    matchByPosition: (_b = context.options) === null || _b === void 0 ? void 0 : _b.matchByPosition
  };
  let commonHead = 0;
  let commonTail = 0;
  let index;
  let index1;
  let index2;
  const array1 = context.left;
  const array2 = context.right;
  const len1 = array1.length;
  const len2 = array2.length;
  let child;
  if (len1 > 0 && len2 > 0 && !matchContext.objectHash && typeof matchContext.matchByPosition !== "boolean") {
    matchContext.matchByPosition = !arraysHaveMatchByRef(array1, array2, len1, len2);
  }
  while (commonHead < len1 && commonHead < len2 && matchItems(array1, array2, commonHead, commonHead, matchContext)) {
    index = commonHead;
    child = new DiffContext(array1[index], array2[index]);
    context.push(child, index);
    commonHead++;
  }
  while (commonTail + commonHead < len1 && commonTail + commonHead < len2 && matchItems(array1, array2, len1 - 1 - commonTail, len2 - 1 - commonTail, matchContext)) {
    index1 = len1 - 1 - commonTail;
    index2 = len2 - 1 - commonTail;
    child = new DiffContext(array1[index1], array2[index2]);
    context.push(child, index2);
    commonTail++;
  }
  let result2;
  if (commonHead + commonTail === len1) {
    if (len1 === len2) {
      context.setResult(void 0).exit();
      return;
    }
    result2 = result2 || {
      _t: "a"
    };
    for (index = commonHead; index < len2 - commonTail; index++) {
      result2[index] = [array2[index]];
      context.prepareDeltaResult(result2[index]);
    }
    context.setResult(result2).exit();
    return;
  }
  if (commonHead + commonTail === len2) {
    result2 = result2 || {
      _t: "a"
    };
    for (index = commonHead; index < len1 - commonTail; index++) {
      const key2 = `_${index}`;
      result2[key2] = [array1[index], 0, 0];
      context.prepareDeltaResult(result2[key2]);
    }
    context.setResult(result2).exit();
    return;
  }
  matchContext.hashCache1 = void 0;
  matchContext.hashCache2 = void 0;
  const trimmed1 = array1.slice(commonHead, len1 - commonTail);
  const trimmed2 = array2.slice(commonHead, len2 - commonTail);
  const seq = lcs.get(trimmed1, trimmed2, matchItems, matchContext);
  const removedItems = [];
  result2 = result2 || {
    _t: "a"
  };
  for (index = commonHead; index < len1 - commonTail; index++) {
    if (seq.indices1.indexOf(index - commonHead) < 0) {
      const key2 = `_${index}`;
      result2[key2] = [array1[index], 0, 0];
      context.prepareDeltaResult(result2[key2]);
      removedItems.push(index);
    }
  }
  let detectMove = true;
  if (((_c = context.options) === null || _c === void 0 ? void 0 : _c.arrays) && context.options.arrays.detectMove === false) {
    detectMove = false;
  }
  let includeValueOnMove = false;
  if ((_e2 = (_d = context.options) === null || _d === void 0 ? void 0 : _d.arrays) === null || _e2 === void 0 ? void 0 : _e2.includeValueOnMove) {
    includeValueOnMove = true;
  }
  const removedItemsLength = removedItems.length;
  for (index = commonHead; index < len2 - commonTail; index++) {
    const indexOnArray2 = seq.indices2.indexOf(index - commonHead);
    if (indexOnArray2 < 0) {
      let isMove = false;
      if (detectMove && removedItemsLength > 0) {
        for (let removeItemIndex1 = 0; removeItemIndex1 < removedItemsLength; removeItemIndex1++) {
          index1 = removedItems[removeItemIndex1];
          const resultItem = index1 === void 0 ? void 0 : result2[`_${index1}`];
          if (index1 !== void 0 && resultItem && matchItems(trimmed1, trimmed2, index1 - commonHead, index - commonHead, matchContext)) {
            resultItem.splice(1, 2, index, ARRAY_MOVE);
            resultItem.splice(1, 2, index, ARRAY_MOVE);
            if (!includeValueOnMove) {
              resultItem[0] = "";
            }
            index2 = index;
            child = new DiffContext(array1[index1], array2[index2]);
            context.push(child, index2);
            removedItems.splice(removeItemIndex1, 1);
            isMove = true;
            break;
          }
        }
      }
      if (!isMove) {
        result2[index] = [array2[index]];
        context.prepareDeltaResult(result2[index]);
      }
    } else {
      if (seq.indices1[indexOnArray2] === void 0) {
        throw new Error(`Invalid indexOnArray2: ${indexOnArray2}, seq.indices1: ${seq.indices1}`);
      }
      index1 = seq.indices1[indexOnArray2] + commonHead;
      if (seq.indices2[indexOnArray2] === void 0) {
        throw new Error(`Invalid indexOnArray2: ${indexOnArray2}, seq.indices2: ${seq.indices2}`);
      }
      index2 = seq.indices2[indexOnArray2] + commonHead;
      child = new DiffContext(array1[index1], array2[index2]);
      context.push(child, index2);
    }
  }
  context.setResult(result2).exit();
};
diffFilter$3.filterName = "arrays";
const compare = {
  numerically(a2, b) {
    return a2 - b;
  },
  numericallyBy(name) {
    return (a2, b) => a2[name] - b[name];
  }
};
const patchFilter$3 = function nestedPatchFilter(context) {
  var _a2;
  if (!context.nested) {
    return;
  }
  const nestedDelta = context.delta;
  if (nestedDelta._t !== "a") {
    return;
  }
  let index;
  let index1;
  const delta = nestedDelta;
  const array = context.left;
  let toRemove = [];
  let toInsert = [];
  const toModify = [];
  for (index in delta) {
    if (index !== "_t") {
      if (index[0] === "_") {
        const removedOrMovedIndex = index;
        if (delta[removedOrMovedIndex] !== void 0 && (delta[removedOrMovedIndex][2] === 0 || delta[removedOrMovedIndex][2] === ARRAY_MOVE)) {
          toRemove.push(Number.parseInt(index.slice(1), 10));
        } else {
          throw new Error(`only removal or move can be applied at original array indices, invalid diff type: ${(_a2 = delta[removedOrMovedIndex]) === null || _a2 === void 0 ? void 0 : _a2[2]}`);
        }
      } else {
        const numberIndex = index;
        if (delta[numberIndex].length === 1) {
          toInsert.push({
            index: Number.parseInt(numberIndex, 10),
            value: delta[numberIndex][0]
          });
        } else {
          toModify.push({
            index: Number.parseInt(numberIndex, 10),
            delta: delta[numberIndex]
          });
        }
      }
    }
  }
  toRemove = toRemove.sort(compare.numerically);
  for (index = toRemove.length - 1; index >= 0; index--) {
    index1 = toRemove[index];
    if (index1 === void 0)
      continue;
    const indexDiff = delta[`_${index1}`];
    const removedValue = array.splice(index1, 1)[0];
    if ((indexDiff === null || indexDiff === void 0 ? void 0 : indexDiff[2]) === ARRAY_MOVE) {
      toInsert.push({
        index: indexDiff[1],
        value: removedValue
      });
    }
  }
  toInsert = toInsert.sort(compare.numericallyBy("index"));
  const toInsertLength = toInsert.length;
  for (index = 0; index < toInsertLength; index++) {
    const insertion = toInsert[index];
    if (insertion === void 0)
      continue;
    array.splice(insertion.index, 0, insertion.value);
  }
  const toModifyLength = toModify.length;
  if (toModifyLength > 0) {
    for (index = 0; index < toModifyLength; index++) {
      const modification = toModify[index];
      if (modification === void 0)
        continue;
      const child = new PatchContext(array[modification.index], modification.delta);
      context.push(child, modification.index);
    }
  }
  if (!context.children) {
    context.setResult(array).exit();
    return;
  }
  context.exit();
};
patchFilter$3.filterName = "arrays";
const collectChildrenPatchFilter$1 = function collectChildrenPatchFilter(context) {
  if (!context || !context.children) {
    return;
  }
  const deltaWithChildren = context.delta;
  if (deltaWithChildren._t !== "a") {
    return;
  }
  const array = context.left;
  const length = context.children.length;
  for (let index = 0; index < length; index++) {
    const child = context.children[index];
    if (child === void 0)
      continue;
    const arrayIndex = child.childName;
    array[arrayIndex] = child.result;
  }
  context.setResult(array).exit();
};
collectChildrenPatchFilter$1.filterName = "arraysCollectChildren";
const reverseFilter$3 = function arraysReverseFilter(context) {
  if (!context.nested) {
    const nonNestedDelta = context.delta;
    if (nonNestedDelta[2] === ARRAY_MOVE) {
      const arrayMoveDelta = nonNestedDelta;
      context.newName = `_${arrayMoveDelta[1]}`;
      context.setResult([
        arrayMoveDelta[0],
        Number.parseInt(context.childName.substring(1), 10),
        ARRAY_MOVE
      ]).exit();
    }
    return;
  }
  const nestedDelta = context.delta;
  if (nestedDelta._t !== "a") {
    return;
  }
  const arrayDelta = nestedDelta;
  for (const name in arrayDelta) {
    if (name === "_t") {
      continue;
    }
    const child = new ReverseContext(arrayDelta[name]);
    context.push(child, name);
  }
  context.exit();
};
reverseFilter$3.filterName = "arrays";
const reverseArrayDeltaIndex = (delta, index, itemDelta) => {
  if (typeof index === "string" && index[0] === "_") {
    return Number.parseInt(index.substring(1), 10);
  }
  if (Array.isArray(itemDelta) && itemDelta[2] === 0) {
    return `_${index}`;
  }
  let reverseIndex = +index;
  for (const deltaIndex in delta) {
    const deltaItem = delta[deltaIndex];
    if (Array.isArray(deltaItem)) {
      if (deltaItem[2] === ARRAY_MOVE) {
        const moveFromIndex = Number.parseInt(deltaIndex.substring(1), 10);
        const moveToIndex = deltaItem[1];
        if (moveToIndex === +index) {
          return moveFromIndex;
        }
        if (moveFromIndex <= reverseIndex && moveToIndex > reverseIndex) {
          reverseIndex++;
        } else if (moveFromIndex >= reverseIndex && moveToIndex < reverseIndex) {
          reverseIndex--;
        }
      } else if (deltaItem[2] === 0) {
        const deleteIndex = Number.parseInt(deltaIndex.substring(1), 10);
        if (deleteIndex <= reverseIndex) {
          reverseIndex++;
        }
      } else if (deltaItem.length === 1 && Number.parseInt(deltaIndex, 10) <= reverseIndex) {
        reverseIndex--;
      }
    }
  }
  return reverseIndex;
};
const collectChildrenReverseFilter$1 = (context) => {
  if (!context || !context.children) {
    return;
  }
  const deltaWithChildren = context.delta;
  if (deltaWithChildren._t !== "a") {
    return;
  }
  const arrayDelta = deltaWithChildren;
  const length = context.children.length;
  const delta = {
    _t: "a"
  };
  for (let index = 0; index < length; index++) {
    const child = context.children[index];
    if (child === void 0)
      continue;
    let name = child.newName;
    if (typeof name === "undefined") {
      if (child.childName === void 0) {
        throw new Error("child.childName is undefined");
      }
      name = reverseArrayDeltaIndex(arrayDelta, child.childName, child.result);
    }
    if (delta[name] !== child.result) {
      delta[name] = child.result;
    }
  }
  context.setResult(delta).exit();
};
collectChildrenReverseFilter$1.filterName = "arraysCollectChildren";
const diffFilter$2 = function datesDiffFilter(context) {
  if (context.left instanceof Date) {
    if (context.right instanceof Date) {
      if (context.left.getTime() !== context.right.getTime()) {
        context.setResult([context.left, context.right]);
      } else {
        context.setResult(void 0);
      }
    } else {
      context.setResult([context.left, context.right]);
    }
    context.exit();
  } else if (context.right instanceof Date) {
    context.setResult([context.left, context.right]).exit();
  }
};
diffFilter$2.filterName = "dates";
const collectChildrenDiffFilter = (context) => {
  if (!context || !context.children) {
    return;
  }
  const length = context.children.length;
  let result2 = context.result;
  for (let index = 0; index < length; index++) {
    const child = context.children[index];
    if (child === void 0)
      continue;
    if (typeof child.result === "undefined") {
      continue;
    }
    result2 = result2 || {};
    if (child.childName === void 0) {
      throw new Error("diff child.childName is undefined");
    }
    result2[child.childName] = child.result;
  }
  if (result2 && context.leftIsArray) {
    result2._t = "a";
  }
  context.setResult(result2).exit();
};
collectChildrenDiffFilter.filterName = "collectChildren";
const objectsDiffFilter = (context) => {
  var _a2;
  if (context.leftIsArray || context.leftType !== "object") {
    return;
  }
  const left = context.left;
  const right = context.right;
  const propertyFilter = (_a2 = context.options) === null || _a2 === void 0 ? void 0 : _a2.propertyFilter;
  for (const name in left) {
    if (!Object.prototype.hasOwnProperty.call(left, name)) {
      continue;
    }
    if (propertyFilter && !propertyFilter(name, context)) {
      continue;
    }
    const child = new DiffContext(left[name], right[name]);
    context.push(child, name);
  }
  for (const name in right) {
    if (!Object.prototype.hasOwnProperty.call(right, name)) {
      continue;
    }
    if (propertyFilter && !propertyFilter(name, context)) {
      continue;
    }
    if (typeof left[name] === "undefined") {
      const child = new DiffContext(void 0, right[name]);
      context.push(child, name);
    }
  }
  if (!context.children || context.children.length === 0) {
    context.setResult(void 0).exit();
    return;
  }
  context.exit();
};
objectsDiffFilter.filterName = "objects";
const patchFilter$2 = function nestedPatchFilter2(context) {
  if (!context.nested) {
    return;
  }
  const nestedDelta = context.delta;
  if (nestedDelta._t) {
    return;
  }
  const objectDelta = nestedDelta;
  for (const name in objectDelta) {
    const child = new PatchContext(context.left[name], objectDelta[name]);
    context.push(child, name);
  }
  context.exit();
};
patchFilter$2.filterName = "objects";
const collectChildrenPatchFilter2 = function collectChildrenPatchFilter3(context) {
  if (!context || !context.children) {
    return;
  }
  const deltaWithChildren = context.delta;
  if (deltaWithChildren._t) {
    return;
  }
  const object = context.left;
  const length = context.children.length;
  for (let index = 0; index < length; index++) {
    const child = context.children[index];
    if (child === void 0)
      continue;
    const property = child.childName;
    if (Object.prototype.hasOwnProperty.call(context.left, property) && child.result === void 0) {
      delete object[property];
    } else if (object[property] !== child.result) {
      object[property] = child.result;
    }
  }
  context.setResult(object).exit();
};
collectChildrenPatchFilter2.filterName = "collectChildren";
const reverseFilter$2 = function nestedReverseFilter(context) {
  if (!context.nested) {
    return;
  }
  const nestedDelta = context.delta;
  if (nestedDelta._t) {
    return;
  }
  const objectDelta = context.delta;
  for (const name in objectDelta) {
    const child = new ReverseContext(objectDelta[name]);
    context.push(child, name);
  }
  context.exit();
};
reverseFilter$2.filterName = "objects";
const collectChildrenReverseFilter = (context) => {
  if (!context || !context.children) {
    return;
  }
  const deltaWithChildren = context.delta;
  if (deltaWithChildren._t) {
    return;
  }
  const length = context.children.length;
  const delta = {};
  for (let index = 0; index < length; index++) {
    const child = context.children[index];
    if (child === void 0)
      continue;
    const property = child.childName;
    if (delta[property] !== child.result) {
      delta[property] = child.result;
    }
  }
  context.setResult(delta).exit();
};
collectChildrenReverseFilter.filterName = "collectChildren";
const TEXT_DIFF = 2;
const DEFAULT_MIN_LENGTH = 60;
let cachedDiffPatch = null;
function getDiffMatchPatch(options, required) {
  var _a2;
  if (!cachedDiffPatch) {
    let instance;
    if ((_a2 = options === null || options === void 0 ? void 0 : options.textDiff) === null || _a2 === void 0 ? void 0 : _a2.diffMatchPatch) {
      instance = new options.textDiff.diffMatchPatch();
    } else {
      if (!required) {
        return null;
      }
      const error2 = new Error("The diff-match-patch library was not provided. Pass the library in through the options or use the `jsondiffpatch/with-text-diffs` entry-point.");
      error2.diff_match_patch_not_found = true;
      throw error2;
    }
    cachedDiffPatch = {
      diff: (txt1, txt2) => instance.patch_toText(instance.patch_make(txt1, txt2)),
      patch: (txt1, patch) => {
        const results = instance.patch_apply(instance.patch_fromText(patch), txt1);
        for (const resultOk of results[1]) {
          if (!resultOk) {
            const error2 = new Error("text patch failed");
            error2.textPatchFailed = true;
            throw error2;
          }
        }
        return results[0];
      }
    };
  }
  return cachedDiffPatch;
}
const diffFilter$1 = function textsDiffFilter(context) {
  var _a2, _b;
  if (context.leftType !== "string") {
    return;
  }
  const left = context.left;
  const right = context.right;
  const minLength = ((_b = (_a2 = context.options) === null || _a2 === void 0 ? void 0 : _a2.textDiff) === null || _b === void 0 ? void 0 : _b.minLength) || DEFAULT_MIN_LENGTH;
  if (left.length < minLength || right.length < minLength) {
    context.setResult([left, right]).exit();
    return;
  }
  const diffMatchPatch = getDiffMatchPatch(context.options);
  if (!diffMatchPatch) {
    context.setResult([left, right]).exit();
    return;
  }
  const diff2 = diffMatchPatch.diff;
  context.setResult([diff2(left, right), 0, TEXT_DIFF]).exit();
};
diffFilter$1.filterName = "texts";
const patchFilter$1 = function textsPatchFilter(context) {
  if (context.nested) {
    return;
  }
  const nonNestedDelta = context.delta;
  if (nonNestedDelta[2] !== TEXT_DIFF) {
    return;
  }
  const textDiffDelta = nonNestedDelta;
  const patch = getDiffMatchPatch(context.options, true).patch;
  context.setResult(patch(context.left, textDiffDelta[0])).exit();
};
patchFilter$1.filterName = "texts";
const textDeltaReverse = (delta) => {
  var _a2, _b, _c;
  const headerRegex = /^@@ +-(\d+),(\d+) +\+(\d+),(\d+) +@@$/;
  const lines = delta.split("\n");
  for (let i2 = 0; i2 < lines.length; i2++) {
    const line = lines[i2];
    if (line === void 0)
      continue;
    const lineStart = line.slice(0, 1);
    if (lineStart === "@") {
      const header = headerRegex.exec(line);
      if (header !== null) {
        const lineHeader = i2;
        lines[lineHeader] = `@@ -${header[3]},${header[4]} +${header[1]},${header[2]} @@`;
      }
    } else if (lineStart === "+") {
      lines[i2] = `-${(_a2 = lines[i2]) === null || _a2 === void 0 ? void 0 : _a2.slice(1)}`;
      if (((_b = lines[i2 - 1]) === null || _b === void 0 ? void 0 : _b.slice(0, 1)) === "+") {
        const lineTmp = lines[i2];
        lines[i2] = lines[i2 - 1];
        lines[i2 - 1] = lineTmp;
      }
    } else if (lineStart === "-") {
      lines[i2] = `+${(_c = lines[i2]) === null || _c === void 0 ? void 0 : _c.slice(1)}`;
    }
  }
  return lines.join("\n");
};
const reverseFilter$1 = function textsReverseFilter(context) {
  if (context.nested) {
    return;
  }
  const nonNestedDelta = context.delta;
  if (nonNestedDelta[2] !== TEXT_DIFF) {
    return;
  }
  const textDiffDelta = nonNestedDelta;
  context.setResult([textDeltaReverse(textDiffDelta[0]), 0, TEXT_DIFF]).exit();
};
reverseFilter$1.filterName = "texts";
const diffFilter = function trivialMatchesDiffFilter(context) {
  if (context.left === context.right) {
    context.setResult(void 0).exit();
    return;
  }
  if (typeof context.left === "undefined") {
    if (typeof context.right === "function") {
      throw new Error("functions are not supported");
    }
    context.setResult([context.right]).exit();
    return;
  }
  if (typeof context.right === "undefined") {
    context.setResult([context.left, 0, 0]).exit();
    return;
  }
  if (typeof context.left === "function" || typeof context.right === "function") {
    throw new Error("functions are not supported");
  }
  context.leftType = context.left === null ? "null" : typeof context.left;
  context.rightType = context.right === null ? "null" : typeof context.right;
  if (context.leftType !== context.rightType) {
    context.setResult([context.left, context.right]).exit();
    return;
  }
  if (context.leftType === "boolean" || context.leftType === "number") {
    context.setResult([context.left, context.right]).exit();
    return;
  }
  if (context.leftType === "object") {
    context.leftIsArray = Array.isArray(context.left);
  }
  if (context.rightType === "object") {
    context.rightIsArray = Array.isArray(context.right);
  }
  if (context.leftIsArray !== context.rightIsArray) {
    context.setResult([context.left, context.right]).exit();
    return;
  }
  if (context.left instanceof RegExp) {
    if (context.right instanceof RegExp) {
      context.setResult([context.left.toString(), context.right.toString()]).exit();
    } else {
      context.setResult([context.left, context.right]).exit();
    }
  }
};
diffFilter.filterName = "trivial";
const patchFilter = function trivialMatchesPatchFilter(context) {
  if (typeof context.delta === "undefined") {
    context.setResult(context.left).exit();
    return;
  }
  context.nested = !Array.isArray(context.delta);
  if (context.nested) {
    return;
  }
  const nonNestedDelta = context.delta;
  if (nonNestedDelta.length === 1) {
    context.setResult(nonNestedDelta[0]).exit();
    return;
  }
  if (nonNestedDelta.length === 2) {
    if (context.left instanceof RegExp) {
      const regexArgs = /^\/(.*)\/([gimyu]+)$/.exec(nonNestedDelta[1]);
      if (regexArgs === null || regexArgs === void 0 ? void 0 : regexArgs[1]) {
        context.setResult(new RegExp(regexArgs[1], regexArgs[2])).exit();
        return;
      }
    }
    context.setResult(nonNestedDelta[1]).exit();
    return;
  }
  if (nonNestedDelta.length === 3 && nonNestedDelta[2] === 0) {
    context.setResult(void 0).exit();
  }
};
patchFilter.filterName = "trivial";
const reverseFilter = function trivialReferseFilter(context) {
  if (typeof context.delta === "undefined") {
    context.setResult(context.delta).exit();
    return;
  }
  context.nested = !Array.isArray(context.delta);
  if (context.nested) {
    return;
  }
  const nonNestedDelta = context.delta;
  if (nonNestedDelta.length === 1) {
    context.setResult([nonNestedDelta[0], 0, 0]).exit();
    return;
  }
  if (nonNestedDelta.length === 2) {
    context.setResult([nonNestedDelta[1], nonNestedDelta[0]]).exit();
    return;
  }
  if (nonNestedDelta.length === 3 && nonNestedDelta[2] === 0) {
    context.setResult([nonNestedDelta[0]]).exit();
  }
};
reverseFilter.filterName = "trivial";
class DiffPatcher {
  constructor(options) {
    this.processor = new Processor(options);
    this.processor.pipe(new Pipe("diff").append(collectChildrenDiffFilter, diffFilter, diffFilter$2, diffFilter$1, objectsDiffFilter, diffFilter$3).shouldHaveResult());
    this.processor.pipe(new Pipe("patch").append(collectChildrenPatchFilter2, collectChildrenPatchFilter$1, patchFilter, patchFilter$1, patchFilter$2, patchFilter$3).shouldHaveResult());
    this.processor.pipe(new Pipe("reverse").append(collectChildrenReverseFilter, collectChildrenReverseFilter$1, reverseFilter, reverseFilter$1, reverseFilter$2, reverseFilter$3).shouldHaveResult());
  }
  options(options) {
    return this.processor.options(options);
  }
  diff(left, right) {
    return this.processor.process(new DiffContext(left, right));
  }
  patch(left, delta) {
    return this.processor.process(new PatchContext(left, delta));
  }
  reverse(delta) {
    return this.processor.process(new ReverseContext(delta));
  }
  unpatch(right, delta) {
    return this.patch(right, this.reverse(delta));
  }
  clone(value2) {
    return clone(value2);
  }
}
let defaultInstance$1;
function diff$1(left, right) {
  if (!defaultInstance$1) {
    defaultInstance$1 = new DiffPatcher();
  }
  return defaultInstance$1.diff(left, right);
}
class BaseFormatter {
  format(delta, left) {
    const context = {};
    this.prepareContext(context);
    const preparedContext = context;
    this.recurse(preparedContext, delta, left);
    return this.finalize(preparedContext);
  }
  prepareContext(context) {
    context.buffer = [];
    context.out = function(...args2) {
      if (!this.buffer) {
        throw new Error("context buffer is not initialized");
      }
      this.buffer.push(...args2);
    };
  }
  typeFormattterNotFound(_context, deltaType) {
    throw new Error(`cannot format delta type: ${deltaType}`);
  }
  /* eslint-disable @typescript-eslint/no-unused-vars */
  typeFormattterErrorFormatter(_context, _err, _delta, _leftValue, _key, _leftKey, _movedFrom) {
  }
  /* eslint-enable @typescript-eslint/no-unused-vars */
  finalize({ buffer: buffer2 }) {
    if (Array.isArray(buffer2)) {
      return buffer2.join("");
    }
    return "";
  }
  recurse(context, delta, left, key2, leftKey, movedFrom, isLast) {
    const useMoveOriginHere = delta && movedFrom;
    const leftValue = useMoveOriginHere ? movedFrom.value : left;
    if (typeof delta === "undefined" && typeof key2 === "undefined") {
      return void 0;
    }
    const type = this.getDeltaType(delta, movedFrom);
    const nodeType = type === "node" ? delta._t === "a" ? "array" : "object" : "";
    if (typeof key2 !== "undefined") {
      this.nodeBegin(context, key2, leftKey, type, nodeType, isLast !== null && isLast !== void 0 ? isLast : false);
    } else {
      this.rootBegin(context, type, nodeType);
    }
    let typeFormattter;
    try {
      typeFormattter = type !== "unknown" ? this[`format_${type}`] : this.typeFormattterNotFound(context, type);
      typeFormattter.call(this, context, delta, leftValue, key2, leftKey, movedFrom);
    } catch (err) {
      this.typeFormattterErrorFormatter(context, err, delta, leftValue, key2, leftKey, movedFrom);
      if (typeof console !== "undefined" && console.error) {
        console.error(err.stack);
      }
    }
    if (typeof key2 !== "undefined") {
      this.nodeEnd(context, key2, leftKey, type, nodeType, isLast !== null && isLast !== void 0 ? isLast : false);
    } else {
      this.rootEnd(context, type, nodeType);
    }
  }
  formatDeltaChildren(context, delta, left) {
    this.forEachDeltaKey(delta, left, (key2, leftKey, movedFrom, isLast) => {
      this.recurse(context, delta[key2], left ? left[leftKey] : void 0, key2, leftKey, movedFrom, isLast);
    });
  }
  forEachDeltaKey(delta, left, fn2) {
    const keys = [];
    const arrayKeys = delta._t === "a";
    if (!arrayKeys) {
      const deltaKeys = Object.keys(delta);
      if (typeof left === "object" && left !== null) {
        keys.push(...Object.keys(left));
      }
      for (const key2 of deltaKeys) {
        if (keys.indexOf(key2) >= 0)
          continue;
        keys.push(key2);
      }
      for (let index = 0; index < keys.length; index++) {
        const key2 = keys[index];
        if (key2 === void 0)
          continue;
        const isLast = index === keys.length - 1;
        fn2(
          // for object diff, the delta key and left key are the same
          key2,
          key2,
          // there's no "move" in object diff
          void 0,
          isLast
        );
      }
      return;
    }
    const movedFrom = {};
    for (const key2 in delta) {
      if (Object.prototype.hasOwnProperty.call(delta, key2)) {
        const value2 = delta[key2];
        if (Array.isArray(value2) && value2[2] === 3) {
          const movedDelta = value2;
          movedFrom[movedDelta[1]] = Number.parseInt(key2.substring(1));
        }
      }
    }
    const arrayDelta = delta;
    let leftIndex = 0;
    let rightIndex = 0;
    const leftArray = Array.isArray(left) ? left : void 0;
    const leftLength = leftArray ? leftArray.length : (
      // if we don't have the original array,
      // use a length that ensures we'll go thru all delta keys
      Object.keys(arrayDelta).reduce((max, key2) => {
        if (key2 === "_t")
          return max;
        const isLeftKey = key2.substring(0, 1) === "_";
        if (isLeftKey) {
          const itemDelta = arrayDelta[key2];
          const leftIndex3 = Number.parseInt(key2.substring(1));
          const rightIndex3 = Array.isArray(itemDelta) && itemDelta.length >= 3 && itemDelta[2] === 3 ? itemDelta[1] : void 0;
          const maxIndex2 = Math.max(leftIndex3, rightIndex3 !== null && rightIndex3 !== void 0 ? rightIndex3 : 0);
          return maxIndex2 > max ? maxIndex2 : max;
        }
        const rightIndex2 = Number.parseInt(key2);
        const leftIndex2 = movedFrom[rightIndex2];
        const maxIndex = Math.max(leftIndex2 !== null && leftIndex2 !== void 0 ? leftIndex2 : 0, rightIndex2 !== null && rightIndex2 !== void 0 ? rightIndex2 : 0);
        return maxIndex > max ? maxIndex : max;
      }, 0) + 1
    );
    let rightLength = leftLength;
    let previousFnArgs;
    const addKey = (...args2) => {
      if (previousFnArgs) {
        fn2(...previousFnArgs);
      }
      previousFnArgs = args2;
    };
    const flushLastKey = () => {
      if (!previousFnArgs) {
        return;
      }
      fn2(previousFnArgs[0], previousFnArgs[1], previousFnArgs[2], true);
    };
    while (leftIndex < leftLength || rightIndex < rightLength || `${rightIndex}` in arrayDelta) {
      let hasDelta = false;
      const leftIndexKey = `_${leftIndex}`;
      const rightIndexKey = `${rightIndex}`;
      const movedFromIndex = rightIndex in movedFrom ? movedFrom[rightIndex] : void 0;
      if (leftIndexKey in arrayDelta) {
        hasDelta = true;
        const itemDelta = arrayDelta[leftIndexKey];
        addKey(leftIndexKey, movedFromIndex !== null && movedFromIndex !== void 0 ? movedFromIndex : leftIndex, movedFromIndex ? {
          key: `_${movedFromIndex}`,
          value: leftArray ? leftArray[movedFromIndex] : void 0
        } : void 0, false);
        if (Array.isArray(itemDelta)) {
          if (itemDelta[2] === 0) {
            rightLength--;
            leftIndex++;
          } else if (itemDelta[2] === 3) {
            leftIndex++;
          } else {
            leftIndex++;
          }
        } else {
          leftIndex++;
        }
      }
      if (rightIndexKey in arrayDelta) {
        hasDelta = true;
        const itemDelta = arrayDelta[rightIndexKey];
        const isItemAdded = Array.isArray(itemDelta) && itemDelta.length === 1;
        addKey(rightIndexKey, movedFromIndex !== null && movedFromIndex !== void 0 ? movedFromIndex : leftIndex, movedFromIndex ? {
          key: `_${movedFromIndex}`,
          value: leftArray ? leftArray[movedFromIndex] : void 0
        } : void 0, false);
        if (isItemAdded) {
          rightLength++;
          rightIndex++;
        } else if (movedFromIndex === void 0) {
          leftIndex++;
          rightIndex++;
        } else {
          rightIndex++;
        }
      }
      if (!hasDelta) {
        if (leftArray && movedFromIndex === void 0 || this.includeMoveDestinations !== false) {
          addKey(rightIndexKey, movedFromIndex !== null && movedFromIndex !== void 0 ? movedFromIndex : leftIndex, movedFromIndex ? {
            key: `_${movedFromIndex}`,
            value: leftArray ? leftArray[movedFromIndex] : void 0
          } : void 0, false);
        }
        if (movedFromIndex !== void 0) {
          rightIndex++;
        } else {
          leftIndex++;
          rightIndex++;
        }
      }
    }
    flushLastKey();
  }
  getDeltaType(delta, movedFrom) {
    if (typeof delta === "undefined") {
      if (typeof movedFrom !== "undefined") {
        return "movedestination";
      }
      return "unchanged";
    }
    if (Array.isArray(delta)) {
      if (delta.length === 1) {
        return "added";
      }
      if (delta.length === 2) {
        return "modified";
      }
      if (delta.length === 3 && delta[2] === 0) {
        return "deleted";
      }
      if (delta.length === 3 && delta[2] === 2) {
        return "textdiff";
      }
      if (delta.length === 3 && delta[2] === 3) {
        return "moved";
      }
    } else if (typeof delta === "object") {
      return "node";
    }
    return "unknown";
  }
  parseTextDiff(value2) {
    var _a2;
    const output2 = [];
    const lines = value2.split("\n@@ ");
    for (const line of lines) {
      const lineOutput = {
        pieces: []
      };
      const location = (_a2 = /^(?:@@ )?[-+]?(\d+),(\d+)/.exec(line)) === null || _a2 === void 0 ? void 0 : _a2.slice(1);
      if (!location) {
        throw new Error("invalid text diff format");
      }
      assertArrayHasAtLeast2(location);
      lineOutput.location = {
        line: location[0],
        chr: location[1]
      };
      const pieces = line.split("\n").slice(1);
      for (let pieceIndex = 0, piecesLength = pieces.length; pieceIndex < piecesLength; pieceIndex++) {
        const piece = pieces[pieceIndex];
        if (piece === void 0 || !piece.length) {
          continue;
        }
        const pieceOutput = {
          type: "context"
        };
        if (piece.substring(0, 1) === "+") {
          pieceOutput.type = "added";
        } else if (piece.substring(0, 1) === "-") {
          pieceOutput.type = "deleted";
        }
        pieceOutput.text = piece.slice(1);
        lineOutput.pieces.push(pieceOutput);
      }
      output2.push(lineOutput);
    }
    return output2;
  }
}
class HtmlFormatter extends BaseFormatter {
  typeFormattterErrorFormatter(context, err) {
    const message2 = typeof err === "object" && err !== null && "message" in err && typeof err.message === "string" ? err.message : String(err);
    context.out(`<pre class="jsondiffpatch-error">${htmlEscape(message2)}</pre>`);
  }
  formatValue(context, value2) {
    const valueAsHtml = typeof value2 === "undefined" ? "undefined" : htmlEscape(JSON.stringify(value2, null, 2));
    context.out(`<pre>${valueAsHtml}</pre>`);
  }
  formatTextDiffString(context, value2) {
    const lines = this.parseTextDiff(value2);
    context.out('<ul class="jsondiffpatch-textdiff">');
    for (let i2 = 0, l2 = lines.length; i2 < l2; i2++) {
      const line = lines[i2];
      if (line === void 0)
        return;
      context.out(`<li><div class="jsondiffpatch-textdiff-location"><span class="jsondiffpatch-textdiff-line-number">${line.location.line}</span><span class="jsondiffpatch-textdiff-char">${line.location.chr}</span></div><div class="jsondiffpatch-textdiff-line">`);
      const pieces = line.pieces;
      for (let pieceIndex = 0, piecesLength = pieces.length; pieceIndex < piecesLength; pieceIndex++) {
        const piece = pieces[pieceIndex];
        if (piece === void 0)
          return;
        context.out(`<span class="jsondiffpatch-textdiff-${piece.type}">${htmlEscape(decodeURI(piece.text))}</span>`);
      }
      context.out("</div></li>");
    }
    context.out("</ul>");
  }
  rootBegin(context, type, nodeType) {
    const nodeClass = `jsondiffpatch-${type}${nodeType ? ` jsondiffpatch-child-node-type-${nodeType}` : ""}`;
    context.out(`<div class="jsondiffpatch-delta ${nodeClass}">`);
  }
  rootEnd(context) {
    context.out(`</div>${context.hasArrows ? `<script type="text/javascript">setTimeout(${adjustArrows.toString()},10);<\/script>` : ""}`);
  }
  nodeBegin(context, key2, leftKey, type, nodeType) {
    const nodeClass = `jsondiffpatch-${type}${nodeType ? ` jsondiffpatch-child-node-type-${nodeType}` : ""}`;
    const label2 = typeof leftKey === "number" && key2.substring(0, 1) === "_" ? key2.substring(1) : key2;
    context.out(`<li class="${nodeClass}" data-key="${htmlEscape(key2)}"><div class="jsondiffpatch-property-name">${htmlEscape(label2)}</div>`);
  }
  nodeEnd(context) {
    context.out("</li>");
  }
  format_unchanged(context, _delta, left) {
    if (typeof left === "undefined") {
      return;
    }
    context.out('<div class="jsondiffpatch-value">');
    this.formatValue(context, left);
    context.out("</div>");
  }
  format_movedestination(context, _delta, left) {
    if (typeof left === "undefined") {
      return;
    }
    context.out('<div class="jsondiffpatch-value">');
    this.formatValue(context, left);
    context.out("</div>");
  }
  format_node(context, delta, left) {
    const nodeType = delta._t === "a" ? "array" : "object";
    context.out(`<ul class="jsondiffpatch-node jsondiffpatch-node-type-${nodeType}">`);
    this.formatDeltaChildren(context, delta, left);
    context.out("</ul>");
  }
  format_added(context, delta) {
    context.out('<div class="jsondiffpatch-value">');
    this.formatValue(context, delta[0]);
    context.out("</div>");
  }
  format_modified(context, delta) {
    context.out('<div class="jsondiffpatch-value jsondiffpatch-left-value">');
    this.formatValue(context, delta[0]);
    context.out('</div><div class="jsondiffpatch-value jsondiffpatch-right-value">');
    this.formatValue(context, delta[1]);
    context.out("</div>");
  }
  format_deleted(context, delta) {
    context.out('<div class="jsondiffpatch-value">');
    this.formatValue(context, delta[0]);
    context.out("</div>");
  }
  format_moved(context, delta) {
    context.out('<div class="jsondiffpatch-value">');
    this.formatValue(context, delta[0]);
    context.out(`</div><div class="jsondiffpatch-moved-destination">${delta[1]}</div>`);
    context.out(
      /* jshint multistr: true */
      `<div class="jsondiffpatch-arrow" style="position: relative; left: -34px;">
          <svg width="30" height="60" style="position: absolute; display: none;">
          <defs>
              <marker id="markerArrow" markerWidth="8" markerHeight="8"
                 refx="2" refy="4" stroke="#88f"
                     orient="auto" markerUnits="userSpaceOnUse">
                  <path d="M1,1 L1,7 L7,4 L1,1" style="fill: #339;" />
              </marker>
          </defs>
          <path d="M30,0 Q-10,25 26,50"
            style="stroke: #88f; stroke-width: 2px; fill: none; stroke-opacity: 0.5; marker-end: url(#markerArrow);"
          ></path>
          </svg>
      </div>`
    );
    context.hasArrows = true;
  }
  format_textdiff(context, delta) {
    context.out('<div class="jsondiffpatch-value">');
    this.formatTextDiffString(context, delta[0]);
    context.out("</div>");
  }
}
function htmlEscape(value2) {
  if (typeof value2 === "number")
    return value2;
  let html = String(value2);
  const replacements = [
    [/&/g, "&amp;"],
    [/</g, "&lt;"],
    [/>/g, "&gt;"],
    [/'/g, "&apos;"],
    [/"/g, "&quot;"]
  ];
  for (const replacement of replacements) {
    html = html.replace(replacement[0], replacement[1]);
  }
  return html;
}
const adjustArrows = function jsondiffpatchHtmlFormatterAdjustArrows(nodeArg) {
  const node2 = nodeArg || document;
  const getElementText = ({ textContent, innerText }) => textContent || innerText;
  const eachByQuery = (el, query2, fn2) => {
    const elems = el.querySelectorAll(query2);
    for (let i2 = 0, l2 = elems.length; i2 < l2; i2++) {
      fn2(elems[i2]);
    }
  };
  const eachChildren = ({ children: children2 }, fn2) => {
    for (let i2 = 0, l2 = children2.length; i2 < l2; i2++) {
      const element = children2[i2];
      if (!element)
        continue;
      fn2(element, i2);
    }
  };
  eachByQuery(node2, ".jsondiffpatch-arrow", ({ parentNode, children: children2, style: style2 }) => {
    const arrowParent = parentNode;
    const svg = children2[0];
    const path = svg.children[1];
    svg.style.display = "none";
    const moveDestinationElem = arrowParent.querySelector(".jsondiffpatch-moved-destination");
    if (!(moveDestinationElem instanceof HTMLElement))
      return;
    const destination = getElementText(moveDestinationElem);
    const container2 = arrowParent.parentNode;
    if (!container2)
      return;
    let destinationElem;
    eachChildren(container2, (child) => {
      if (child.getAttribute("data-key") === destination) {
        destinationElem = child;
      }
    });
    if (!destinationElem) {
      return;
    }
    try {
      const distance = destinationElem.offsetTop - arrowParent.offsetTop;
      svg.setAttribute("height", `${Math.abs(distance) + 6}`);
      style2.top = `${-8 + (distance > 0 ? 0 : distance)}px`;
      const curve = distance > 0 ? `M30,0 Q-10,${Math.round(distance / 2)} 26,${distance - 4}` : `M30,${-distance} Q-10,${Math.round(-distance / 2)} 26,4`;
      path.setAttribute("d", curve);
      svg.style.display = "";
    } catch (err) {
      console.debug(`[jsondiffpatch] error adjusting arrows: ${err}`);
    }
  });
};
let defaultInstance;
function format(delta, left) {
  if (!defaultInstance) {
    defaultInstance = new HtmlFormatter();
  }
  return defaultInstance.format(delta, left);
}
const StateDiffView = ({
  before,
  after,
  className: className2
}) => {
  const state_diff = diff$1(sanitizeKeys(before), sanitizeKeys(after));
  const html_result = format(state_diff) || "Unable to render differences";
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      dangerouslySetInnerHTML: { __html: unescapeNewlines(html_result) },
      className: clsx(className2)
    }
  );
};
function unescapeNewlines(obj) {
  if (typeof obj === "string") {
    return obj.replace(/\\n/g, "\n");
  }
  if (obj === null || typeof obj !== "object") {
    return obj;
  }
  if (Array.isArray(obj)) {
    return obj.map((item) => unescapeNewlines(item));
  }
  return Object.fromEntries(
    Object.entries(obj).map(([key2, value2]) => [
      key2,
      unescapeNewlines(value2)
    ])
  );
}
function sanitizeKeys(obj) {
  if (typeof obj !== "object" || obj === null) {
    return obj;
  }
  if (Array.isArray(obj)) {
    return obj.map((item) => sanitizeKeys(item));
  }
  return Object.fromEntries(
    Object.entries(obj).map(([key2, value2]) => [
      key2.replace(/</g, "&lt;").replace(/>/g, "&gt;"),
      sanitizeKeys(value2)
    ])
  );
}
function parseNpt(time) {
  if (typeof time === "number") {
    return time;
  } else if (typeof time === "string") {
    return time.split(":").reverse().map(parseFloat).reduce((sum, n2, i2) => sum + n2 * Math.pow(60, i2));
  } else {
    return void 0;
  }
}
function debounce(f, delay) {
  let timeout;
  return function() {
    for (var _len = arguments.length, args2 = new Array(_len), _key = 0; _key < _len; _key++) {
      args2[_key] = arguments[_key];
    }
    clearTimeout(timeout);
    timeout = setTimeout(() => f.apply(this, args2), delay);
  };
}
function throttle(f, interval) {
  let enableCall = true;
  return function() {
    if (!enableCall) return;
    enableCall = false;
    for (var _len2 = arguments.length, args2 = new Array(_len2), _key2 = 0; _key2 < _len2; _key2++) {
      args2[_key2] = arguments[_key2];
    }
    f.apply(this, args2);
    setTimeout(() => enableCall = true, interval);
  };
}
class DummyLogger {
  log() {
  }
  debug() {
  }
  info() {
  }
  warn() {
  }
  error() {
  }
}
class PrefixedLogger {
  constructor(logger, prefix) {
    this.logger = logger;
    this.prefix = prefix;
  }
  log(message2) {
    for (var _len = arguments.length, args2 = new Array(_len > 1 ? _len - 1 : 0), _key = 1; _key < _len; _key++) {
      args2[_key - 1] = arguments[_key];
    }
    this.logger.log(`${this.prefix}${message2}`, ...args2);
  }
  debug(message2) {
    for (var _len2 = arguments.length, args2 = new Array(_len2 > 1 ? _len2 - 1 : 0), _key2 = 1; _key2 < _len2; _key2++) {
      args2[_key2 - 1] = arguments[_key2];
    }
    this.logger.debug(`${this.prefix}${message2}`, ...args2);
  }
  info(message2) {
    for (var _len3 = arguments.length, args2 = new Array(_len3 > 1 ? _len3 - 1 : 0), _key3 = 1; _key3 < _len3; _key3++) {
      args2[_key3 - 1] = arguments[_key3];
    }
    this.logger.info(`${this.prefix}${message2}`, ...args2);
  }
  warn(message2) {
    for (var _len4 = arguments.length, args2 = new Array(_len4 > 1 ? _len4 - 1 : 0), _key4 = 1; _key4 < _len4; _key4++) {
      args2[_key4 - 1] = arguments[_key4];
    }
    this.logger.warn(`${this.prefix}${message2}`, ...args2);
  }
  error(message2) {
    for (var _len5 = arguments.length, args2 = new Array(_len5 > 1 ? _len5 - 1 : 0), _key5 = 1; _key5 < _len5; _key5++) {
      args2[_key5 - 1] = arguments[_key5];
    }
    this.logger.error(`${this.prefix}${message2}`, ...args2);
  }
}
let wasm;
function addHeapObject(obj) {
  if (heap_next === heap.length) heap.push(heap.length + 1);
  const idx = heap_next;
  heap_next = heap[idx];
  heap[idx] = obj;
  return idx;
}
function debugString(val) {
  const type = typeof val;
  if (type == "number" || type == "boolean" || val == null) {
    return `${val}`;
  }
  if (type == "string") {
    return `"${val}"`;
  }
  if (type == "symbol") {
    const description2 = val.description;
    if (description2 == null) {
      return "Symbol";
    } else {
      return `Symbol(${description2})`;
    }
  }
  if (type == "function") {
    const name = val.name;
    if (typeof name == "string" && name.length > 0) {
      return `Function(${name})`;
    } else {
      return "Function";
    }
  }
  if (Array.isArray(val)) {
    const length = val.length;
    let debug = "[";
    if (length > 0) {
      debug += debugString(val[0]);
    }
    for (let i2 = 1; i2 < length; i2++) {
      debug += ", " + debugString(val[i2]);
    }
    debug += "]";
    return debug;
  }
  const builtInMatches = /\[object ([^\]]+)\]/.exec(toString.call(val));
  let className2;
  if (builtInMatches && builtInMatches.length > 1) {
    className2 = builtInMatches[1];
  } else {
    return toString.call(val);
  }
  if (className2 == "Object") {
    try {
      return "Object(" + JSON.stringify(val) + ")";
    } catch (_) {
      return "Object";
    }
  }
  if (val instanceof Error) {
    return `${val.name}: ${val.message}
${val.stack}`;
  }
  return className2;
}
function dropObject(idx) {
  if (idx < 132) return;
  heap[idx] = heap_next;
  heap_next = idx;
}
function getArrayU32FromWasm0(ptr, len) {
  ptr = ptr >>> 0;
  return getUint32ArrayMemory0().subarray(ptr / 4, ptr / 4 + len);
}
let cachedDataViewMemory0 = null;
function getDataViewMemory0() {
  if (cachedDataViewMemory0 === null || cachedDataViewMemory0.buffer.detached === true || cachedDataViewMemory0.buffer.detached === void 0 && cachedDataViewMemory0.buffer !== wasm.memory.buffer) {
    cachedDataViewMemory0 = new DataView(wasm.memory.buffer);
  }
  return cachedDataViewMemory0;
}
function getStringFromWasm0(ptr, len) {
  ptr = ptr >>> 0;
  return decodeText(ptr, len);
}
let cachedUint32ArrayMemory0 = null;
function getUint32ArrayMemory0() {
  if (cachedUint32ArrayMemory0 === null || cachedUint32ArrayMemory0.byteLength === 0) {
    cachedUint32ArrayMemory0 = new Uint32Array(wasm.memory.buffer);
  }
  return cachedUint32ArrayMemory0;
}
let cachedUint8ArrayMemory0 = null;
function getUint8ArrayMemory0() {
  if (cachedUint8ArrayMemory0 === null || cachedUint8ArrayMemory0.byteLength === 0) {
    cachedUint8ArrayMemory0 = new Uint8Array(wasm.memory.buffer);
  }
  return cachedUint8ArrayMemory0;
}
function getObject(idx) {
  return heap[idx];
}
let heap = new Array(128).fill(void 0);
heap.push(void 0, null, true, false);
let heap_next = heap.length;
function passStringToWasm0(arg, malloc, realloc) {
  if (realloc === void 0) {
    const buf = cachedTextEncoder.encode(arg);
    const ptr2 = malloc(buf.length, 1) >>> 0;
    getUint8ArrayMemory0().subarray(ptr2, ptr2 + buf.length).set(buf);
    WASM_VECTOR_LEN = buf.length;
    return ptr2;
  }
  let len = arg.length;
  let ptr = malloc(len, 1) >>> 0;
  const mem = getUint8ArrayMemory0();
  let offset = 0;
  for (; offset < len; offset++) {
    const code2 = arg.charCodeAt(offset);
    if (code2 > 127) break;
    mem[ptr + offset] = code2;
  }
  if (offset !== len) {
    if (offset !== 0) {
      arg = arg.slice(offset);
    }
    ptr = realloc(ptr, len, len = offset + arg.length * 3, 1) >>> 0;
    const view = getUint8ArrayMemory0().subarray(ptr + offset, ptr + len);
    const ret = cachedTextEncoder.encodeInto(arg, view);
    offset += ret.written;
    ptr = realloc(ptr, len, offset, 1) >>> 0;
  }
  WASM_VECTOR_LEN = offset;
  return ptr;
}
function takeObject(idx) {
  const ret = getObject(idx);
  dropObject(idx);
  return ret;
}
let cachedTextDecoder = new TextDecoder("utf-8", {
  ignoreBOM: true,
  fatal: true
});
cachedTextDecoder.decode();
const MAX_SAFARI_DECODE_BYTES = 2146435072;
let numBytesDecoded = 0;
function decodeText(ptr, len) {
  numBytesDecoded += len;
  if (numBytesDecoded >= MAX_SAFARI_DECODE_BYTES) {
    cachedTextDecoder = new TextDecoder("utf-8", {
      ignoreBOM: true,
      fatal: true
    });
    cachedTextDecoder.decode();
    numBytesDecoded = len;
  }
  return cachedTextDecoder.decode(getUint8ArrayMemory0().subarray(ptr, ptr + len));
}
const cachedTextEncoder = new TextEncoder();
if (!("encodeInto" in cachedTextEncoder)) {
  cachedTextEncoder.encodeInto = function(arg, view) {
    const buf = cachedTextEncoder.encode(arg);
    view.set(buf);
    return {
      read: arg.length,
      written: buf.length
    };
  };
}
let WASM_VECTOR_LEN = 0;
const VtFinalization = typeof FinalizationRegistry === "undefined" ? {
  register: () => {
  },
  unregister: () => {
  }
} : new FinalizationRegistry((ptr) => wasm.__wbg_vt_free(ptr >>> 0, 1));
class Vt {
  static __wrap(ptr) {
    ptr = ptr >>> 0;
    const obj = Object.create(Vt.prototype);
    obj.__wbg_ptr = ptr;
    VtFinalization.register(obj, obj.__wbg_ptr, obj);
    return obj;
  }
  __destroy_into_raw() {
    const ptr = this.__wbg_ptr;
    this.__wbg_ptr = 0;
    VtFinalization.unregister(this);
    return ptr;
  }
  free() {
    const ptr = this.__destroy_into_raw();
    wasm.__wbg_vt_free(ptr, 0);
  }
  /**
   * @param {string} s
   * @returns {any}
   */
  feed(s) {
    const ptr0 = passStringToWasm0(s, wasm.__wbindgen_export, wasm.__wbindgen_export2);
    const len0 = WASM_VECTOR_LEN;
    const ret = wasm.vt_feed(this.__wbg_ptr, ptr0, len0);
    return takeObject(ret);
  }
  /**
   * @param {number} cols
   * @param {number} rows
   * @returns {any}
   */
  resize(cols, rows) {
    const ret = wasm.vt_resize(this.__wbg_ptr, cols, rows);
    return takeObject(ret);
  }
  /**
   * @returns {Uint32Array}
   */
  getSize() {
    try {
      const retptr = wasm.__wbindgen_add_to_stack_pointer(-16);
      wasm.vt_getSize(retptr, this.__wbg_ptr);
      var r0 = getDataViewMemory0().getInt32(retptr + 4 * 0, true);
      var r1 = getDataViewMemory0().getInt32(retptr + 4 * 1, true);
      var v1 = getArrayU32FromWasm0(r0, r1).slice();
      wasm.__wbindgen_export3(r0, r1 * 4, 4);
      return v1;
    } finally {
      wasm.__wbindgen_add_to_stack_pointer(16);
    }
  }
  /**
   * @param {number} row
   * @param {boolean} cursor_on
   * @returns {any}
   */
  getLine(row2, cursor_on) {
    const ret = wasm.vt_getLine(this.__wbg_ptr, row2, cursor_on);
    return takeObject(ret);
  }
  /**
   * @returns {any}
   */
  getCursor() {
    const ret = wasm.vt_getCursor(this.__wbg_ptr);
    return takeObject(ret);
  }
}
if (Symbol.dispose) Vt.prototype[Symbol.dispose] = Vt.prototype.free;
function create$1(cols, rows, scrollback_limit, bold_is_bright) {
  const ret = wasm.create(cols, rows, scrollback_limit, bold_is_bright);
  return Vt.__wrap(ret);
}
const EXPECTED_RESPONSE_TYPES = /* @__PURE__ */ new Set(["basic", "cors", "default"]);
async function __wbg_load(module, imports) {
  if (typeof Response === "function" && module instanceof Response) {
    if (typeof WebAssembly.instantiateStreaming === "function") {
      try {
        return await WebAssembly.instantiateStreaming(module, imports);
      } catch (e) {
        const validResponse = module.ok && EXPECTED_RESPONSE_TYPES.has(module.type);
        if (validResponse && module.headers.get("Content-Type") !== "application/wasm") {
          console.warn("`WebAssembly.instantiateStreaming` failed because your server does not serve Wasm with `application/wasm` MIME type. Falling back to `WebAssembly.instantiate` which is slower. Original error:\n", e);
        } else {
          throw e;
        }
      }
    }
    const bytes = await module.arrayBuffer();
    return await WebAssembly.instantiate(bytes, imports);
  } else {
    const instance = await WebAssembly.instantiate(module, imports);
    if (instance instanceof WebAssembly.Instance) {
      return {
        instance,
        module
      };
    } else {
      return instance;
    }
  }
}
function __wbg_get_imports() {
  const imports = {};
  imports.wbg = {};
  imports.wbg.__wbg___wbindgen_debug_string_adfb662ae34724b6 = function(arg0, arg1) {
    const ret = debugString(getObject(arg1));
    const ptr1 = passStringToWasm0(ret, wasm.__wbindgen_export, wasm.__wbindgen_export2);
    const len1 = WASM_VECTOR_LEN;
    getDataViewMemory0().setInt32(arg0 + 4 * 1, len1, true);
    getDataViewMemory0().setInt32(arg0 + 4 * 0, ptr1, true);
  };
  imports.wbg.__wbg___wbindgen_throw_dd24417ed36fc46e = function(arg0, arg1) {
    throw new Error(getStringFromWasm0(arg0, arg1));
  };
  imports.wbg.__wbg_new_13317ed16189158e = function() {
    const ret = new Array();
    return addHeapObject(ret);
  };
  imports.wbg.__wbg_new_4ceb6a766bf78b04 = function() {
    const ret = new Object();
    return addHeapObject(ret);
  };
  imports.wbg.__wbg_set_3f1d0b984ed272ed = function(arg0, arg1, arg2) {
    getObject(arg0)[takeObject(arg1)] = takeObject(arg2);
  };
  imports.wbg.__wbg_set_8b6a9a61e98a8881 = function(arg0, arg1, arg2) {
    getObject(arg0)[arg1 >>> 0] = takeObject(arg2);
  };
  imports.wbg.__wbindgen_cast_2241b6af4c4b2941 = function(arg0, arg1) {
    const ret = getStringFromWasm0(arg0, arg1);
    return addHeapObject(ret);
  };
  imports.wbg.__wbindgen_cast_4625c577ab2ec9ee = function(arg0) {
    const ret = BigInt.asUintN(64, arg0);
    return addHeapObject(ret);
  };
  imports.wbg.__wbindgen_cast_d6cd19b81560fd6e = function(arg0) {
    const ret = arg0;
    return addHeapObject(ret);
  };
  imports.wbg.__wbindgen_object_clone_ref = function(arg0) {
    const ret = getObject(arg0);
    return addHeapObject(ret);
  };
  imports.wbg.__wbindgen_object_drop_ref = function(arg0) {
    takeObject(arg0);
  };
  return imports;
}
function __wbg_finalize_init(instance, module) {
  wasm = instance.exports;
  __wbg_init.__wbindgen_wasm_module = module;
  cachedDataViewMemory0 = null;
  cachedUint32ArrayMemory0 = null;
  cachedUint8ArrayMemory0 = null;
  return wasm;
}
function initSync(module) {
  if (wasm !== void 0) return wasm;
  if (typeof module !== "undefined") {
    if (Object.getPrototypeOf(module) === Object.prototype) {
      ({
        module
      } = module);
    } else {
      console.warn("using deprecated parameters for `initSync()`; pass a single object instead");
    }
  }
  const imports = __wbg_get_imports();
  if (!(module instanceof WebAssembly.Module)) {
    module = new WebAssembly.Module(module);
  }
  const instance = new WebAssembly.Instance(module, imports);
  return __wbg_finalize_init(instance, module);
}
async function __wbg_init(module_or_path) {
  if (wasm !== void 0) return wasm;
  if (typeof module_or_path !== "undefined") {
    if (Object.getPrototypeOf(module_or_path) === Object.prototype) {
      ({
        module_or_path
      } = module_or_path);
    } else {
      console.warn("using deprecated parameters for the initialization function; pass a single object instead");
    }
  }
  const imports = __wbg_get_imports();
  if (typeof module_or_path === "string" || typeof Request === "function" && module_or_path instanceof Request || typeof URL === "function" && module_or_path instanceof URL) {
    module_or_path = fetch(module_or_path);
  }
  const {
    instance,
    module
  } = await __wbg_load(await module_or_path, imports);
  return __wbg_finalize_init(instance, module);
}
var exports$1 = /* @__PURE__ */ Object.freeze({
  __proto__: null,
  Vt,
  create: create$1,
  default: __wbg_init,
  initSync
});
const base64codes = [62, 0, 0, 0, 63, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 0, 0, 0, 0, 0, 0, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51];
function getBase64Code(charCode) {
  return base64codes[charCode - 43];
}
function base64Decode(str) {
  let missingOctets = str.endsWith("==") ? 2 : str.endsWith("=") ? 1 : 0;
  let n2 = str.length;
  let result2 = new Uint8Array(3 * (n2 / 4));
  let buffer2;
  for (let i2 = 0, j = 0; i2 < n2; i2 += 4, j += 3) {
    buffer2 = getBase64Code(str.charCodeAt(i2)) << 18 | getBase64Code(str.charCodeAt(i2 + 1)) << 12 | getBase64Code(str.charCodeAt(i2 + 2)) << 6 | getBase64Code(str.charCodeAt(i2 + 3));
    result2[j] = buffer2 >> 16;
    result2[j + 1] = buffer2 >> 8 & 255;
    result2[j + 2] = buffer2 & 255;
  }
  return result2.subarray(0, result2.length - missingOctets);
}
var vtWasmModule = base64Decode("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CAgJCgsODA4NDgsgAkGoAWpBASABKAIAIAEoAgRB1NzAABCBASABIAIpA6gBNwIAIABBADoAAAwYCyACQbABakEBIAEoAgAgASgCBEHk3MAAEIEBIAEgAikDsAE3AgAgAEEBOgAADBcLIAJBuAFqQQEgASgCACABKAIEQfTcwAAQgQEgASACKQO4ATcCACAAQQI6AAAMFgsgAkHAAWpBASABKAIAIAEoAgRBhN3AABCBASABIAIpA8ABNwIAIABBAzoAAAwVCyACQcgBakEBIAEoAgAgASgCBEGU3cAAEIEBIAEgAikDyAE3AgAgAEEEOgAADBQLIAJB0AFqQQEgASgCACABKAIEQaTdwAAQgQEgASACKQPQATcCACAAQQU6AAAMEwsgAkHYAWpBASABKAIAIAEoAgRBtN3AABCBASABIAIpA9gBNwIAIABBBjoAAAwSCyACQeABakEBIAEoAgAgASgCBEHE3cAAEIEBIAEgAikD4AE3AgAgAEEHOgAADBELIAJB6AFqQQEgASgCACABKAIEQdTdwAAQgQEgASACKQPoATcCACAAQQg6AAAMEAsgAkHwAWpBASABKAIAIAEoAgRB5N3AABCBASABIAIpA/ABNwIAIABBCToAAAwPCyACQfgBakEBIAEoAgAgASgCBEH03cAAEIEBIAEgAikD+AE3AgAgAEEKOgAADA4LIAJBgAJqQQEgASgCACABKAIEQYTewAAQgQEgASACKQOAAjcCACAAQQs6AAAMDQsgAkGIAmpBASABKAIAIAEoAgRBlN7AABCBASABIAIpA4gCNwIAIABBDDoAAAwMCyACQZACakEBIAEoAgAgASgCBEGk3sAAEIEBIAEgAikDkAI3AgAgAEENOgAADAsLAkACQCADQR5rQf//A3FBCE8EQCADQSZrDgIBCAILIAJBCGpBASABKAIAIAEoAgRBxODAABCBASABIAIpAwg3AgAgACADQR5rOgACIABBDjsAAAwMCwJAIAEoAgQiA0ECTwRAIAJBmAFqIAEoAgBBEGoQaSACKAKYASIDDQEgASgCBCEDCyACQegAakEBIAEoAgAgA0G03sAAEIEBIAIoAmwhAyACKAJoIQQMDQsCQAJAAkAgAigCnAFBAUcNACADLwEAQQJrDgQBAAACAAsgAkHwAGpBASABKAIAIAEoAgRBhN/AABCB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ACABQQRqIQwgAkFAayENIAJBJWohDiACQRxqIQ8gASgCJCEFIAEoAhQhECABKAIQIQMCQAJAAn8CQANAIAEoAgAhBiABQYCAgIB4NgIAIAEoAgQhCwJAAkACQAJAAkAgBkGAgICAeEcEQCABKQIIIREgCyEHDAELAkAgAyAQRgRAQYCAgIB4IQYMAQsgASADQRBqIgg2AhAgAykCCCERIAMoAgQhByADKAIAIQYgCCEDC0GAgICAeCALEKMBIAZBgICAgHhGDQELIAIgBzYCDCACIAY2AgggAiARNwIQIBFCIIghEkF/IAUgEaciBEcgBCAFSxtB/wFxDgICAwELQYCAgIB4IAcQowEgAEGAgICAeDYCACABQYCAgIB4NgIADAcLAkAgEqdBAXENACAFIAQgByAEEDRrIgMgAyAFSRsiAyAESw0AIAIgAzYCECADIQQLAn9BgICAgHggBCAFTQ0AGgJAAkAgByAEIAVBuNrAABCQASgCBEUEQCACQThqIgMgAkEIaiIIIAVBAWsQPyACQTBqIANBCGooAgA2AgAgAiACKQI4NwMoIAItABQhBCADQRBqIAIoAgwgAigCECIHIAdBAWtB2NrAABCQASIHQRBqLwEAOwEAIAJCoICAgBA3AjggAiAHKQIINwJAIAggA0Ho2sAAEFcgAiAEOgA0IAItABRBAXFFDQEMAgsgAkE4aiIDIAJBCGogBRA/IAJBMGogA0EIaigCADYCACACIAIpAjg3AyggAiACLQAUIgM6ADQgAw0BCyACQShqEIsBCyACKAIwBEAgAkFAayACQTRqKAIANgIAIAJBAToAFCACIAIpAiw3AzggAigCKAwBCyACKAIoIAIoAixBBEEUEJ8BQYCAgIB4CyEDQYCAgIB4IAsQowEgASADNgIAIAwgAikDODcCACAMQQhqIAJBQGsoAgA2AgAgAEEIaiACQRBqKQIANwIAIAAgAikCCDcCAAwGCyAAIBE3AgggACAHNgIEIAAgBjYCAAwFCwJAIAMgEEcEQCABIANBEGoiCDYCECADKAIAIgZBgICAgHhHDQELIAJBADsAQCACQQI6ADwgAkECOgA4IAJBCGoiASAFIAJBOGoQQSAAIAIpAgg3AgAgAkEAOgAUIABBCGogAUEIaikCADcCAAwFCyADQQxqKAIAIQkgDyADKQIENwIAIA9BCGogCTYCACACIAY2AhggBSAEayIJRQ0BIBKnQQFxRQRAIAJBADsAQCACQQI6ADwgAkECOgA4IAJBCGogBSACQThqEEEMAgsgAi0AJEUEQCACQRhqEIsBCyACKAIcIQMgAigCICIKIAlNBEAgAkEIaiIEIAMgChCAAQJAIAItACQiBg0AIAJBADoAFCACKAIQIAVPDQAgAkEAOwBAIAJBAjoAPCACQQI6ADggBCAFIAJBOGoQQQsgAigCGCADQQRBFBCfASAGRQ0EQYCAgIB4IAsQowEgAUEIaiACQRBqKQIANwIAIAEgAikCCDcCAEGAgICAeCACEKMBIAghAwwBCwsgAyAKIAlB+NnAABCQASgCBEUEQCANQQhqIAcgBCAEQQFrQYjawAAQkAEiCEEQai8BADsBACANIAgpAgg3AgAgAkKggICAEDcCOCACQQhqIAJBOGpBmNrAABBXIAlBAWshCQsgCSAKTQRAIAJBCGogAyAJEIABIAIoAhghBiADIAogCRCIASAGQYCAgIB4Rg0DIAogCiAJayIIIAggCksbIQQgAi0AJAwCCyAJIApBqNrAABCzAQALIAJBKmogDkECai0AADoAACACIA4vAAA7ASggAigCICEEIAIoAhwhAyACLQAkCyEIQYCAgIB4IAsQowEgASAIOgAMIAEgBDYCCCABIAM2AgQgASAGNgIAIAEgAi8BKDsADSABQQ9qIAJBKmotAAA6AAALIAAgAikCCDcCACAAQQhqIAJBEGopAgA3AgALIAJB0ABqJAAL5QoCEH8BfiMAQZABayICJAAgACgCbCIFIAAoAhwiBmsiAUEAIAEgACgCFCIHIAZrIAVqTRshDSAFIAdqIQMgB0EEdCIBIAAoAhAiCmohDyAAKAIYIQwgACgCaCEOIAAoAqABIQsgACgCnAEhCCAKIQQDQAJAIAMgBkYNACABRQ0AIAkgDGpBACAELQAMIhAbIQkgA0EBayEDIAFBEGshASAEQRBqIQQgDSAQQQFzaiENDAELCyAIIAxHBEBBACEFIABBADYCFCACIAg2AjggAkEANgI0IAIgBzYCMCACIABBDGoiDDYCLCACIA82AiggAiAKNgIkIAJBgICAgHg2AhQgAkHIAGogAkEUaiIBEBACfyACKAJIQYCAgIB4RgRAIAEQoQFBBCEEQQAMAQsgAkEIakEE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QQlJDQEgA0UEQCABIQMDQCADIAVqIgEgAyACEGogASEDIAIgACACayIATQ0ACwwBCwtBACAAQQR0IgNrIQUDQCABIAVqIAEgABBqIAEgA2ohASACIABrIgIgAE8NAAsMAQsLIAEgAEEEdCIFayIDIAJBBHQiBmohByAAIAJLDQEgBEEQaiIAIAMgBRAWGiADIAEgBhASIAcgACAFEBYaDAILIARBCGoiByABIABBBHRrIgZBCGopAgA3AwAgBCAGKQIANwMAIAJBBHQhCCACIgUhAQNAIAYgAUEEdGohAwNAIARBGGoiCSADQQhqIgopAgA3AwAgBCADKQIANwMQIAcpAwAhDSADIAQpAwA3AgAgCiANNwIAIAcgCSkDADcDACAEIAQpAxA3AwAgACABSwRAIAMgCGohAyABIAJqIQEMAQsLIAEgAGsiAQRAIAEgBSABIAVJGyEFDAEFIAQpAwAhDSAGQQhqIARBCGoiBykDADcCACAGIA03AgBBASAFIAVBAU0bIQlBASEBA0AgASAJRg0EIAYgAUEEdGoiBSkCACENIAcgBUEIaiIKKQIANwMAIAQgDTcDACABIAJqIQMDQCAEQRhqIgsgBiADQQR0aiIIQQhqIgwpAgA3AwAgBCAIKQIANwMQIAcpAwAhDSAIIAQpAwA3AgAgDCANNwIAIAcgCykDADcDACAEIAQpAxA3AwAgACADSwRAIAIgA2ohAwwBCyADIABrIgMgAUcNAAsgBCkDACENIAogBykDADcCACAFIA03AgAgAUEBaiEBDAALAAsACwALIARBEGoiACABIAYQFhogByADIAUQEiADIAAgBhAWGgsgBEGQAWokAAuQBQEIfwJAIAJBEEkEQCAAIQMMAQsCQEEAIABrQQNxIgYgAGoiBSAATQ0AIAZBAWsgACEDIAEhBCAGBEAgBiEHA0AgAyAELQAAOgAAIARBAWohBCADQQFqIQMgB0EBayIHDQALC0EHSQ0AA0AgAyAELQAAOgAAIANBAWogBEEBai0AADoAACADQQJqIARBAmotAAA6AAAgA0EDaiAEQQNqLQAAOgAAIANBBGogBEEEai0AADoAACADQQVqIARBBWotAAA6AAAgA0EGaiAEQQZqLQAAOgAAIANBB2ogBEEHai0AADoAACAEQQhqIQQgBSADQQhqIgNHDQALCyACIAZr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AygCHCIAIAEgAhAlIANBKGogAEHgAGooAgAgAEHkAGooAgAQIyADQRBqIAAQJCADIAMpAxA3AjQgA0EIaiADKAIsIAMoAjAQWyADKAIMIQAgAygCCEEBcQRAIAMgADYCPCADQTxqQezCwAAQQgALIANBKGoQbiADKAIgIAMoAiQQsgEgA0FAayQAIAALmQEBA38gAUFsbCECIAFB/////wNxIQMgACABQRRsaiEBQQAhAAJAA0AgAkUNAQJAIAFBFGsiBCgCAEEgRw0AIAFBEGsoAgBBAUcNACABQQxrLQAAQQJHDQAgAUEIay0AAEECRw0AIAFBBGstAAANACABQQNrLQAAQR9xDQAgAkEUaiECIABBAWohACAEIQEMAQsLIAAhAwsgAwuxAQECfyMAQRBrIgIkAAJAIAFFDQAgAUEDakECdiEBAkAgAEEETQRAIAFBAWsiA0GAAkkNAQsgAkGsssEAKAIANgIIIAEgACACQQhqQaiqwQBBBEEFEE8hAEGsssEAIAIoAgg2AgAMAQsgAkGsssEANgIEIAIgA0ECdEGsqsEAaiIDKAIANgIMIAEgACACQQxqIAJBBGpBBkEHEE8hACADIAIoAgw2AgALIAJBEGokACAAC6ABAQN/IwBBEGsiBSQAIAVBCGogACABIAJB4M7AABBnIAUoAgwiBiADIAIgAWsiByADIAdJGyIDTwRAIAYgA2siBiAFKAIIIAZBBHRqIAMQFSAAIAEgASADaiAEECogAQRAIAAgAUEBa0HwzsAAEGJBADoADAsgACACQQFrQYDPwAAQYkEAOgAMIAVBEGokAA8LQczJwABBIUHwycAAEHEAC6gBAQF/IwBBQGoiAyQAIANBCGogACgCABACIAMoAgghACADIAMoAgw2AgQgAyAANgIAIANBATYCMCADQQI2AhggA0GYqsEANgIUIANCATcCICADIAMoAgQiADYCPCADIAMoAgA2AjggAyAANgI0IAMgA0E0ajYCLCADIANBLGo2AhwgASACIANBFGoQFyADKAI0IgEEQCADKAI4QQEgARA4CyADQUBrJAALpAEBAX8jAEEQayIDJAACQCAARQ0AIAJFDQACQCABQQRNBEAgAkEDakECdkEBayIBQYACSQ0BCyADQayywQAoAgA2AgggACADQQhqQaiqwQBBAhAxQayywQAgAygC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BDYCBCAAIAE2AgALOAACQCABaUEBRw0AQYCAgIB4IAFrIABJDQAgAARAQeyywQAtAAAaIAEgABA1IgFFDQELIAEPCwALOAACQCACQYCAxABGDQAgACACIAEoAhARAgBFDQBBAQ8LIANFBEBBAA8LIAAgA0EAIAEoAgwRAwALLQEBfyABIAAoAgBPBH8gACgCBCECIAAtAAhFBEAgASACTQ8LIAEgAkkFQQALC3ABA38gACgCACIEIAAoAggiBUYEQCMAQRBrIgMkACADQQhqIAAgBEEBQQJBCBAmIAMoAggiBEGBgICAeEcEQCADKAIMGiAEIAIQrgEACyADQRBqJAALIAAgBUEBajYCCCAAKAIEIAVBA3RqIAE3AQALNAEBfyAAKAIIIgMgACgCAEYEQCAAIAIQawsgACADQQFqNgIIIAAoAgQgA0ECdGogATYCAAsuAQF/IwBBEGsiAiQAIAJBCGogASAAEIwBIAIoAggiAARAIAJBEGokACAADwsACzcBAX8jAEEgayIBJAAgAUEANgIYIAFBATYCDCABQYzpwAA2AgggAUIENwIQIAFBCGogABCKAQALKgEBfyACIAMQNSIEBEAgBCAAIAEgAyABIANJGxAWGiAAIAIgARA4CyAECysAIAIgA0kEQCADIAIgBBC0AQALIAAgAiADazYCBCAAIAEgA0EUbGo2AgALLwEBfyAAIAIQjgEgACgCBCAAKAIIIgNBFGxqIAEgAkEUbBAWGiAAIAIgA2o2AggLKwAgASADSwRAIAEgAyAEELQBAAsgACADIAFrNgIEIAAgAiABQQR0ajYCAAsvAAJAAkAgA2lBAUcNAEGAgICAeCADayABSQ0AIAAgASADIAIQfiIADQELAAsgAAsuAANAIAEEQCAAKAIAIABBBGooAgBBBEEUEJ8BIAFBAWshASAAQRBqIQAMAQsLCzIBAX8gACgCCCECIAEgACgCAEECai0AABCbASEBIAAoAgQgAiABEAEgACACQQFqNgIICyoAIAAgACgCaCABaiIBIAAoApwBIgBBAWsgACABSxtBACABQQBOGzYCaAszAQJ/IAAgACgCqAEiAiAAKAKsAUEBaiIDIAEgAEGyAWoQNiAAKAJgIAAoAmQgAiADEFMLMwECfyAAIAAoAqgBIgIgACgCrAFBAWoiAyABIABBsgFqEB0gACgCYCAAKAJkIAIgAxBTCyoAIAEgAkkEQEGkyMAAQSNBvMnAABBxAAsgAiAAIAJBFGxqIAEgAmsQGQs1ACAAIAApAnQ3AmggACAAKQF8NwGyASAAIAAvAYYBOwG+ASAAQboBaiAAQYQBai8BADsBAAvsAQICfwF+IwBBEGsiAiQAIAJBATsBDCACIAE2AgggAiAANgIEIwBBEGsiASQAIAJBBGoiACkCACEEIAEgADYCDCABIAQ3AgQjAEEQayIAJAAgAUEEaiIBKAIAIgIoAgwhAwJAAkACQAJAIAIoAgQOAgABAgsgAw0BQQEhAkEAIQMMAgsgAw0AIAIoAgAiAigCBCEDIAIoAgAhAgwBCyAAQYCAgIB4NgIAIAAgATYCDCABKAIIIgEtAAkaIABBGyABLQAIEEoACyAAIAM2AgQgACACNgIAIAEoAggiAS0ACRogAEEcIAEtAAgQSgALKwECfwJAIAAoAgQgACgCCCIBEDQiAkUNACABIAJJDQAgACABIAJrNgIICwsmACACBEBB7LLBAC0AABogASACEDUhAQsgACACNgIEIAAgATYCAAsjAQF/IAEgACgCACAAKAIIIgJrSwRAIAAgAiABQQRBEBBtCwsjAQF/IAEgACgCACAAKAIIIgJrSwRAIAAgAiABQQRBFBBtCwslACAAQQE2AgQgACABKAIEIAEoAgBrQQR2IgE2AgggACABNgIACxsAIAEgAk0EQCACIAEgAxBLAAsgACACQRRsagsgACABIAJNBEAgAiABQeTjwAAQSwALIAAgAmpBAToAAAsbACABIAJNBEAgAiABIAMQSwALIAAgAkEEdGoLAwAACwMAAAsDAAALAwAACwMAAAsDAAALGgBB7LLBAC0AABpBBCAAEDUiAARAIAAPCwALIQAgAEUEQEGc68AAQTIQuQEACyAAIAIgAyABKAIQEQEACxYAIAFBAXFFBEAgALgQCQ8LIACtEAoLRgEBfyAAIAAoAgBBAWsiATYCACABRQRAIABBDGoQRwJAIABBf0YNACAAIAAoAgRBAWsiATYCBCABDQAgAEEEQZwGEDgLCwsfACAARQRAQZzrwABBMhC5AQALIAAgAiABKAIQEQIACyEBAX8gACgCECIBIAAoAhQQgwEgACgCDCABQQRBEBCfAQsSACAABEAgASACIAAgA2wQOAsLIQEBfyAAKAIEIgEgACgCCBCDASAAKAIAIAFBBEEQEJ8BCxYAIABBEGoQWCAAKAIAIAAoAgQQowELFAAgACAAKAIAQQFrNgIAIAEQnAELGQAgAEGAgICAeEcEQCAAIAFBBEEUEJ8BCwsUACABBEBBgICAgHggARCjAQsgAQsZACABKAIcQcjlwABBDiABKAIgKAIMEQMACw8AIAIEQCAAIAEgAhA4CwsPACABBEAgACACIAEQOAsLEwAgAARADwtBpKnBAEEbELkBAAsPACAAQYQBTwRAIAAQAwsLEwAgACgCCCAAKAIAQQJBAhCfAQsVACACIAIQpAEaIABBgICAgHg2AgALFAAgACgCACABIAAoAgQoAgwRAgALEAAgASAAKAIEIAAoAggQDws8ACAARQRAIwBBIGsiACQAIABBADYCGCAAQQE2AgwgAEHQxMAANgIIIABCBDcCECAAQQhqIAEQigEACwALFAAgAEEANgIIIABCgICAgBA3AgALEgAgACABQZDNwAAQYkEBOgAMCxAAIAEgACgCACAAKAIEEA8LDgAgAEEANgIAIAEQnAELawEBfyMAQTBrIgMkACADIAE2AgQgAyAANgIAIANBAjYCDCADQejpwAA2AgggA0ICNwIUIAMgA0EEaq1CgICAgOABhDcDKCADIAOtQoCAgIDgAYQ3AyAgAyADQSBqNgIQIANBCGogAhCKAQALawEBfyMAQTBrIgMkACADIAE2AgQgAyAANgIAIANBAjYCDCADQcjpwAA2AgggA0ICNwIUIAMgA0EEaq1CgICAgOABhDcDKCADIAOtQoCAgIDgAYQ3AyAgAyADQSBqNgIQIANBCGogAhCKAQALawEBfyMAQTBrIgMkACADIAE2AgQgAyAANgIAIANBAjYCDCADQZzqwAA2AgggA0ICNwIUIAMgA0EEaq1CgICAgOABhDcDKCADIAOtQoCAgIDgAYQ3AyAgAyADQSBqNgIQIANBCGogAhCKAQALDgBB8OXAAEErIAAQcQALCwAgACMAaiQAIwALDgBBv6nBAEHPABC5AQALCQAgACABEAcACw0AIABB9ObAACABEBcLDAAgACABKQIANwMACwoAIAAoAgAQqQELDQAgAEGAgICAeDYCAAsJACAAQQA2AgALBgAgABBYCwUAQYAECwQAQQELBAAgAQsEAEEACwvSbSAAQYCAwAALQB0AAAAEAAAABAAAAB4AAABjYWxsZWQgYFJlc3VsdDo6dW53cmFwKClgIG9uIGFuIGBFcnJgIHZhbHVlRXJyb3IAQb+JwAALAXgAQeCJwAALEP////////////////////8AQYaKwAALDwEAAAAAACAAAAAAAAAAAgBBwIrAAAsg//////////////////////////////////////////8AQaSLwAALCBAAAAAAAAABAEHAuMAACwL/BwBB1LjAAAsHDwD////1/wBBgLnAAAsW////////////////////////////AwBBoLnAAAsd/////////////////////////////////////w8AQf+5wAALGPz//////////////////////////////wBBoLrAAAs+//////////////////////////////////////////////////////////////////////////////////8AQYy7wAALOP////////////////////////////////////////////////////////////////////////9/AEHgu8AAC9EB/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wMAQcC9wAALJ///////////////////////////////////////////////////DwBBwMDAAAvBI3NyYy9saWIucnMAAAEADwDwGg8AAAAAAOIlAADlJQAAAAAAALDgAACz4AAAAAAAADz7AQBp+wEAAAAAAGr7AQBs+wEAAAAAAIAlAACfJQAAAAAAAAD7AQA7+wEAAAAAAGF0dGVtcHRlZCB0byB0YWtlIG93bmVyc2hpcCBvZiBSdXN0IHZhbHVlIHdoaWxlIGl0IHdhcyBib3Jyb3dlZGJndGV4dGNvZGVwb2ludHNyYXN0ZXJfc3ltYm9s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FVFVVVVVVVVVAAAAAAAAQFVVVVVVVVVVVdVXVVVVVVVVVVVVVVUFAABUVVVVVVVVVVVVVVVVVRUAAFVVUVVVVVVVBRAAAAEBUFVVVVVVVVVVVVUBVVVVVVX/////f1VVVVBVAABVVVVVVVVVVVVVBQBBwPzAAAuYBEBVVVVVVVVVVVVVVVVVRVQBAFRRAQBVVQVVVVVVVVVVUVVVVVVVVVVVVVVVVVVVRAFUVVFVFVVVBVVVVVVVVUVBVVVVVVVVVVVVVVVVVVVUQRUUUFFVVVVVVVVVUFFVVUFVVVVVVVVVVVVVVVVVVVQBEFRRVVVVVQVVVVVVVQUAUVVVVVVVVVVVVVVVVVVVBAFUVVFVAVVVBVVVVVVVVVVFVVVVVVVVVVVVVVVVVVVFVFVVUVUVVVVVVVVVVVVVVVRUVVVVVVVVVVVVVVVVVQRUBQRQVUFVVQVVVVVVVVVVUVVVVVVVVVVVVVVVVVVVFEQFBFBVQVVVBVVVVVVVVVVQVVVVVVVVVVVVVVVVVRVEAVRVQVUVVVUFVVVVVVVVVVFVVVVVVVVVVVVVVVVVVVVVVUUVBURVFVVVVVVVVVVVVVVVVVVVVVVVVVVVUQBAVVUVAEBVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVRAABUVVUAQFVVVVVVVVVVVVVVVVVVVVVVVVBVVVVVVVURUVVVVVVVVVVVVVVVVVUBAABAAARVAQAAAQAAAAAAAAAAVFVFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVQEEAEFBVVVVVVVVUAVUVVVVAVRVVUVBVVFVVVVRVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqAEGAgcEAC5ADVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUBVVVVVVVVVVVVVVVVBVRVVVVVVVUFVVVVVVVVVQVVVVVVVVVVBVVVVX///ff//ddfd9bV11UQAFBVRQEAAFVXUVVVVVVVVVVVVVUVAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVQVVVVVVVVVVVUVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVQBVUVUVVAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVcVFFVVVVVVVVVVVVVVVVVVRQBARAEAVBUAABRVVVVVVVVVVVVVVVUAAAAAAAAAQFVVVVVVVVVVVVVVVQBVVVVVVVVVVVVVVVUAAFAFVVVVVVVVVVVVFQAAVVVVUFVVVVVVVVUFUBBQVVVVVVVVVVVVVVVVVUVQEVBVVVVVVVVVVVVVVVVVVQAABVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVQAAAAAQAVFFVVFBVVVVVVVVVVVVVVVVVVVVVVQBBoITBAAuTCFVVFQBVVVVVVVUFQFVVVVVVVVVVVVVVVQAAAABVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUAAAAAAAAAAFRVVVVVVVVVVVX1VVVVaVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV/VfXVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX1VVVVVVV9VVVVVVVVVVVVVVVX///9VVVVVVVVVVVVV1VVVVVXVVVVVXVX1VVVVVX1VX1V1VVdVVVVVdVX1XXVdVV31VVVVVVVVVVdVVVVVVVVVVXfV31VVVVVVVVVVVVVVVVVVVf1VVVVVVVVXVVXVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVdVXVVVVVVVVVVVVVVVVV11VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVFVBVVVVVVVVVVVVVVVVVVVX9////////////////X1XVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVQAAAAAAAAAAqqqqqqqqmqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpVVVWqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqlpVVVVVVVWqqqqqqqqqqqqqqqqqqgoAqqqqaqmqqqqqqqqqqqqqqqqqqqqqqqqqqmqBqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqlWpqqqqqqqqqqqqqqmqqqqqqqqqqqqqqqqoqqqqqqqqqqqqaqqqqqqqqqqqqqqqqqqqqqqqqqqqqlVVlaqqqqqqqqqqqqqqaqqqqqqqqqqqqqpVVaqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpVVVVVVVVVVVVVVVVVVVVVqqqqVqqqqqqqqqqqqqqqqqpqVVVVVVVVVVVVVVVVVV9VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUVQAAAUFVVVVVVVVUFVVVVVVVVVVVVVVVVVVVVVVVVVVVQVVVVRUUVVVVVVVVVQVVUVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVBVVVVVVVUAAAAAUFVFFVVVVVVVVVVVVQUAUFVVVVVVFQAAUFVVVaqqqqqqqqpWQFVVVVVVVVVVVVVVFQVQUFVVVVVVVVVVVVFVVVVVVVVVVVVVVVVVVVVVAUBBQVVVFVVVVFVVVVVVVVVVVVVVVFVVVVVVVVVVVVVVVQQUVAVRVVVVVVVVVVVVVVBVRVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVFUUVVVVVWqqqqqqqqqqqpVVVUAAAAAAEAVAEG/jMEAC+EMVVVVVVVVVVVFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVAAAA8KqqWlUAAAAAqqqqqqqqqqpqqqqqqmqqVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVFamqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqlZVVVVVVVVVVVVVVVVVVQVUVVVVVVVVVVVVVVVVVVVVqmpVVQAAVFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVRVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUFQFUBQVUAVVVVVVVVVVVVVUAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVBVVVVVVVV1VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUVVFVVVVVVVVVVVVVVVVVVVVVVVVUBVVVVVVVVVVVVVVVVVVVVVVUFAABUVVVVVVVVVVVVVVUFUFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVFVVVVVVVVVVVVVVVVVAAAAQFVVVVVVVVVVVVUUVFUVUFVVVVVVVVVVVVVVFUBBVUVVVVVVVVVVVVVVVVVVVVVAVVVVVVVVVVUVAAEAVFVVVVVVVVVVVVVVVVVVFVVVVVBVVVVVVVVVVVVVVVUFAEAFVQEUVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUVUARVRVFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVRUVAEBVVVVVVVBVVVVVVVVVVVVVVVVVFURUVVVVVRVVVVUFAFQAVFVVVVVVVVVVVVVVVVVVVVUAAAVEVVVVVVVFVVVVVVVVVVVVVVVVVVVVVVVVVVUUAEQRBFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVFQVQVRBUVVVVVVVVUFVVVVVVVVVVVVVVVVVVVVVVVVVVFQBAEVRVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVFVEAEFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUBBRAAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUVAABBVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUVRUEEVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVQAFVVRVVVVVVVVVAQBAVVVVVVVVVVVVFQAEQFUVVVUBQAFVVVVVVVVVVVVVAAAAAEBQVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVQBAABBVVVVVVVVVVVVVVVVVVVVVVVVVVQUAAAAAAAUABEFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUBQEUQAABVVVVVVVVVVVVVVVVVVVVVVVVQEVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVRVUVVVAVVVVVVVVVVVVVVVVBUBVRFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUFQAAAFBVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVQBUVVVVVVVVVVVVVVVVVVUAQFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUVVVVVVVVVVVVVVVVVVVVVFUBVVVVVVVVVVVVVVVVVVVVVVVVVqlRVVVpVVVWqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpVVaqqqqqqqqqqqqqqqqqqqqqqqqqqqlpVVVVVVVVVVVVVqqpWVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVqqmqaaqqqqqqqqqqalVVVWVVVVVVVVVVallVVVWqVVWqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqlVVVVVVVVVVQQBVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVQBBq5nBAAt1UAAAAAAAQFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVRFQBQAAAABAAQBVVVVVVVVVBVBVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUFVFVVVVVVVVVVVVVVVVVVAEGtmsEACwJAFQBBu5rBAAvFBlRVUVVVVVRVVVVVFQABAAAAVVVVVVVVVVVVVVVVVVVVVVVVVVUAQAAAAAAUABAEQFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVRVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVFVVVVVVVVVVVVVVVVVVVVAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUAVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVAEBVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVUAQFVVVVVVVVVVVVVVVVVVV1VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVXVVVVVVVVVVVVVVVVVVVVVdf3/f1VVVVVVVVVVVVVVVVVVVVVVVfX///////9uVVVVqqq6qqqqqur6v79VqqpWVV9VVVWqWlVVVVVVVf//////////V1VV/f/f///////////////////////3//////9VVVX/////////////f9X/VVVV/////1dX//////////////////////9/9//////////////////////////////////////////////////////////////X////////////////////X1VV1X////////9VVVVVdVVVVVVVVX1VVVVXVVVVVVVVVVVVVVVVVVVVVVVVVVXV////////////////////////////VVVVVVVVVVVVVVVV//////////////////////9fVVd//VX/VVXVV1X//1dVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX///9VV1VVVVVVVf//////////////f///3/////////////////////////////////////////////////////////////9VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV////V///V1X//////////////9//X1X1////Vf//V1X//1dVqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqlpVVVVVVVVVVVmWVWGqpVmqVVVVVVWVVVVVVVVVVZVVVQBBjqHBAAsBAwBBnKHBAAuJCVVVVVVVlVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVFQCWalpaaqoFQKZZlWVVVVVVVVVVVQAAAABVVlVVqVZVVVVVVVVVVVVWVVVVVVVVVVUAAAAAAAAAAFRVVVWVWVlVVWVVVWlVVVVVVVVVVVVVVZVWlWqqqqpVqqpaVVVVWVWqqqpVVVVVZVVVWlVVVVWlZVZVVVWVVVVVVVVVppaalllZZamWqqpmVapVWllVWlZlVVVVaqqlpVpVVVWlqlpVVVlZVVVZVVVVVVWVVVVVVVVVVVVVVVVVVVVVVVVVVVVlVfVVVVVpVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqpVqqqqqqqqqqqqVVVVqqqqqqVaVVWaqlpVpaVVWlqllqVaVVVVpVpVlVVVVX1VaVmlVV9VZlVVVVVVVVVVZlX///9VVVWammqaVVVV1VVVVVXVVVWlXVX1VVVVVb1Vr6q6qquqqppVuqr6rrquVV31VVVVVVVVVVdVVVVVWVVVVXfV31VVVVVVVVWlqqpVVVVVVVXVV1VVVVVVVVVVVVVVVVetWlVVVVVVVVVVVaqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqAAAAwKqqWlUAAAAAqqqqqqqqqqpqqqqqqmqqVVVVVVVVVVVVVVVVBVRVVVVVVVVVVVVVVVVVVVWqalVVAABUWaqqalWqqqqqqqqqWqqqqqqqqqqqqqqqqqqqWlWqqqqqqqqquv7/v6qqqqpWVVVVVVVVVVVVVVVVVfX///////8vbml4L3N0b3JlLzI4aHl6ZmwzMzhrczRhbWhhN3ZwcG5sYnExczFucWF2LXJ1c3QtZGVmYXVsdC0xLjg1LjAvbGliL3J1c3RsaWIvc3JjL3J1c3QvbGlicmFyeS9hbGxvYy9zcmMvcmF3X3ZlYy5ycy9ob21lL3J1bm5lci8uY2FyZ28vcmVnaXN0cnkvc3JjL2luZGV4LmNyYXRlcy5pby0xOTQ5Y2Y4YzZiNWI1NTdmL3dhc20tYmluZGdlbi0wLjIuMTA2L3NyYy9jb252ZXJ0L3NsaWNlcy5ycy9ob21lL3J1bm5lci8uY2FyZ28vcmVnaXN0cnkvc3JjL2luZGV4LmNyYXRlcy5pby0xOTQ5Y2Y4YzZiNWI1NTdmL3dhc20tYmluZGdlbi0wLjIuMTA2L3NyYy9leHRlcm5yZWYucnMdVBAAZwAAAH8AAAARAAAAHVQQAGcAAACMAAAAEQAAAG51bGwgcG9pbnRlciBwYXNzZWQgdG8gcnVzdHJlY3Vyc2l2ZSB1c2Ugb2YgYW4gb2JqZWN0IGRldGVjdGVkIHdoaWNoIHdvdWxkIGxlYWQgdG8gdW5zYWZlIGFsaWFzaW5nIGluIHJ1c3RKc1ZhbHVlKCkADlUQAAgAAAAWVRAAAQBBqKrBAAsBBABICXByb2R1Y2VycwEMcHJvY2Vzc2VkLWJ5AgZ3YWxydXMGMC4yNC40DHdhc20tYmluZGdlbhMwLjIuMTA2ICgxMTgzMWZiODkp");
async function init(options) {
  await __wbg_init({
    module_or_path: await options.module,
    memory: options.memory
  });
  return exports$1;
}
class Clock {
  constructor() {
    let speed = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : 1;
    this.speed = speed;
    this.startTime = performance.now();
  }
  getTime() {
    return this.speed * (performance.now() - this.startTime) / 1e3;
  }
  setTime(time) {
    this.startTime = performance.now() - time / this.speed * 1e3;
  }
}
class NullClock {
  constructor() {
  }
  getTime(_speed) {
  }
  setTime(_time) {
  }
}
class Stream {
  constructor(input, xfs) {
    this.input = typeof input.next === "function" ? input : input[Symbol.iterator]();
    this.xfs = xfs ?? [];
  }
  map(f) {
    return this.transform(Map$1(f));
  }
  flatMap(f) {
    return this.transform(FlatMap(f));
  }
  filter(f) {
    return this.transform(Filter(f));
  }
  take(n2) {
    return this.transform(Take(n2));
  }
  drop(n2) {
    return this.transform(Drop(n2));
  }
  transform(f) {
    return new Stream(this.input, this.xfs.concat([f]));
  }
  multiplex(other, comparator) {
    return new Stream(new Multiplexer(this[Symbol.iterator](), other[Symbol.iterator](), comparator));
  }
  toArray() {
    return Array.from(this);
  }
  [Symbol.iterator]() {
    let v = 0;
    let values = [];
    let flushed = false;
    const xf = compose(this.xfs, (val) => values.push(val));
    return {
      next: () => {
        if (v === values.length) {
          values = [];
          v = 0;
        }
        while (values.length === 0) {
          const next = this.input.next();
          if (next.done) {
            break;
          } else {
            xf.step(next.value);
          }
        }
        if (values.length === 0 && !flushed) {
          xf.flush();
          flushed = true;
        }
        if (values.length > 0) {
          return {
            done: false,
            value: values[v++]
          };
        } else {
          return {
            done: true
          };
        }
      }
    };
  }
}
function Map$1(f) {
  return (emit) => {
    return (input) => {
      emit(f(input));
    };
  };
}
function FlatMap(f) {
  return (emit) => {
    return (input) => {
      f(input).forEach(emit);
    };
  };
}
function Filter(f) {
  return (emit) => {
    return (input) => {
      if (f(input)) {
        emit(input);
      }
    };
  };
}
function Take(n2) {
  let c = 0;
  return (emit) => {
    return (input) => {
      if (c < n2) {
        emit(input);
      }
      c += 1;
    };
  };
}
function Drop(n2) {
  let c = 0;
  return (emit) => {
    return (input) => {
      c += 1;
      if (c > n2) {
        emit(input);
      }
    };
  };
}
function compose(xfs, push) {
  return xfs.reverse().reduce((next, curr) => {
    const xf = toXf(curr(next.step));
    return {
      step: xf.step,
      flush: () => {
        xf.flush();
        next.flush();
      }
    };
  }, toXf(push));
}
function toXf(xf) {
  if (typeof xf === "function") {
    return {
      step: xf,
      flush: () => {
      }
    };
  } else {
    return xf;
  }
}
class Multiplexer {
  constructor(left, right, comparator) {
    this.left = left;
    this.right = right;
    this.comparator = comparator;
  }
  [Symbol.iterator]() {
    let leftItem;
    let rightItem;
    return {
      next: () => {
        if (leftItem === void 0 && this.left !== void 0) {
          const result2 = this.left.next();
          if (result2.done) {
            this.left = void 0;
          } else {
            leftItem = result2.value;
          }
        }
        if (rightItem === void 0 && this.right !== void 0) {
          const result2 = this.right.next();
          if (result2.done) {
            this.right = void 0;
          } else {
            rightItem = result2.value;
          }
        }
        if (leftItem === void 0 && rightItem === void 0) {
          return {
            done: true
          };
        } else if (leftItem === void 0) {
          const value2 = rightItem;
          rightItem = void 0;
          return {
            done: false,
            value: value2
          };
        } else if (rightItem === void 0) {
          const value2 = leftItem;
          leftItem = void 0;
          return {
            done: false,
            value: value2
          };
        } else if (this.comparator(leftItem, rightItem)) {
          const value2 = leftItem;
          leftItem = void 0;
          return {
            done: false,
            value: value2
          };
        } else {
          const value2 = rightItem;
          rightItem = void 0;
          return {
            done: false,
            value: value2
          };
        }
      }
    };
  }
}
async function parse$2(data) {
  if (data instanceof Response) {
    const text2 = await data.text();
    const result2 = parseJsonl(text2);
    if (result2 !== void 0) {
      const {
        header,
        events
      } = result2;
      if (header.version === 2) {
        return parseAsciicastV2(header, events);
      } else if (header.version === 3) {
        return parseAsciicastV3(header, events);
      } else {
        throw new Error(`asciicast v${header.version} format not supported`);
      }
    } else {
      const header = JSON.parse(text2);
      if (header.version === 1) {
        return parseAsciicastV1(header);
      }
    }
  } else if (typeof data === "object" && data.version === 1) {
    return parseAsciicastV1(data);
  } else if (Array.isArray(data)) {
    const header = data[0];
    if (header.version === 2) {
      const events = data.slice(1, data.length);
      return parseAsciicastV2(header, events);
    } else if (header.version === 3) {
      const events = data.slice(1, data.length);
      return parseAsciicastV3(header, events);
    } else {
      throw new Error(`asciicast v${header.version} format not supported`);
    }
  }
  throw new Error("invalid data");
}
function parseJsonl(jsonl) {
  const lines = jsonl.split("\n");
  let header;
  try {
    header = JSON.parse(lines[0]);
  } catch (_error) {
    return;
  }
  const events = new Stream(lines).drop(1).filter((l2) => l2[0] === "[").map(JSON.parse);
  return {
    header,
    events
  };
}
function parseAsciicastV1(data) {
  let time = 0;
  const events = new Stream(data.stdout).map((e) => {
    time += e[0];
    return [time, "o", e[1]];
  });
  return {
    cols: data.width,
    rows: data.height,
    events
  };
}
function parseAsciicastV2(header, events) {
  return {
    cols: header.width,
    rows: header.height,
    theme: parseTheme$1(header.theme),
    events,
    idleTimeLimit: header.idle_time_limit
  };
}
function parseAsciicastV3(header, events) {
  if (!(events instanceof Stream)) {
    events = new Stream(events);
  }
  let time = 0;
  events = events.map((e) => {
    time += e[0];
    return [time, e[1], e[2]];
  });
  return {
    cols: header.term.cols,
    rows: header.term.rows,
    theme: parseTheme$1(header.term?.theme),
    events,
    idleTimeLimit: header.idle_time_limit
  };
}
function parseTheme$1(theme) {
  if (theme === void 0) return;
  const colorRegex = /^#[0-9A-Fa-f]{6}$/;
  const paletteRegex = /^(#[0-9A-Fa-f]{6}:){7,}#[0-9A-Fa-f]{6}$/;
  const fg = theme?.fg;
  const bg = theme?.bg;
  const palette = theme?.palette;
  if (colorRegex.test(fg) && colorRegex.test(bg) && paletteRegex.test(palette)) {
    return {
      foreground: fg,
      background: bg,
      palette: palette.split(":")
    };
  }
}
function unparseAsciicastV2(recording2) {
  const header = JSON.stringify({
    version: 2,
    width: recording2.cols,
    height: recording2.rows
  });
  const events = recording2.events.map(JSON.stringify).join("\n");
  return `${header}
${events}
`;
}
function recording(src, _ref, _ref2) {
  let {
    feed,
    resize,
    onInput,
    onMarker,
    setState,
    logger
  } = _ref;
  let {
    speed,
    idleTimeLimit,
    startAt,
    loop,
    posterTime,
    markers: markers_,
    pauseOnMarkers,
    cols: initialCols,
    rows: initialRows,
    audioUrl
  } = _ref2;
  let cols;
  let rows;
  let events;
  let markers;
  let duration;
  let effectiveStartAt;
  let eventTimeoutId;
  let nextEventIndex = 0;
  let lastEventTime = 0;
  let startTime;
  let pauseElapsedTime;
  let playCount = 0;
  let waitingForAudio = false;
  let waitingTimeout;
  let shouldResumeOnAudioPlaying = false;
  let now = () => performance.now() * speed;
  let audioCtx;
  let audioElement;
  let audioSeekable = false;
  async function init2() {
    const timeout = setTimeout(() => {
      setState("loading");
    }, 3e3);
    try {
      let metadata2 = loadRecording(src, logger, {
        idleTimeLimit,
        startAt,
        markers_
      });
      const hasAudio = await loadAudio(audioUrl);
      metadata2 = await metadata2;
      return {
        ...metadata2,
        hasAudio
      };
    } finally {
      clearTimeout(timeout);
    }
  }
  async function loadRecording(src2, logger2, opts) {
    const {
      parser,
      minFrameTime,
      inputOffset,
      dumpFilename,
      encoding = "utf-8"
    } = src2;
    const data = await doFetch(src2);
    const recording2 = prepare(await parser(data, {
      encoding
    }), logger2, {
      ...opts,
      minFrameTime,
      inputOffset
    });
    ({
      cols,
      rows,
      events,
      duration,
      effectiveStartAt
    } = recording2);
    initialCols = initialCols ?? cols;
    initialRows = initialRows ?? rows;
    if (events.length === 0) {
      throw new Error("recording is missing events");
    }
    if (dumpFilename !== void 0) {
      dump(recording2, dumpFilename);
    }
    const poster = posterTime !== void 0 ? getPoster(posterTime) : void 0;
    markers = events.filter((e) => e[1] === "m").map((e) => [e[0], e[2].label]);
    return {
      cols,
      rows,
      duration,
      theme: recording2.theme,
      poster,
      markers
    };
  }
  async function loadAudio(audioUrl2) {
    if (!audioUrl2) return false;
    audioElement = await createAudioElement(audioUrl2);
    audioSeekable = !Number.isNaN(audioElement.duration) && audioElement.duration !== Infinity && audioElement.seekable.length > 0 && audioElement.seekable.end(audioElement.seekable.length - 1) === audioElement.duration;
    if (audioSeekable) {
      audioElement.addEventListener("playing", onAudioPlaying);
      audioElement.addEventListener("waiting", onAudioWaiting);
    } else {
      logger.warn(`audio is not seekable - you must enable range request support on the server providing ${audioElement.src} for audio seeking to work`);
    }
    return true;
  }
  async function doFetch(_ref3) {
    let {
      url,
      data,
      fetchOpts = {}
    } = _ref3;
    if (typeof url === "string") {
      return await doFetchOne(url, fetchOpts);
    } else if (Array.isArray(url)) {
      return await Promise.all(url.map((url2) => doFetchOne(url2, fetchOpts)));
    } else if (data !== void 0) {
      if (typeof data === "function") {
        data = data();
      }
      if (!(data instanceof Promise)) {
        data = Promise.resolve(data);
      }
      const value2 = await data;
      if (typeof value2 === "string" || value2 instanceof ArrayBuffer) {
        return new Response(value2);
      } else {
        return value2;
      }
    } else {
      throw new Error("failed fetching recording file: url/data missing in src");
    }
  }
  async function doFetchOne(url, fetchOpts) {
    const response = await fetch(url, fetchOpts);
    if (!response.ok) {
      throw new Error(`failed fetching recording from ${url}: ${response.status} ${response.statusText}`);
    }
    return response;
  }
  function scheduleNextEvent() {
    const nextEvent = events[nextEventIndex];
    if (nextEvent) {
      eventTimeoutId = scheduleAt(runNextEvent, nextEvent[0]);
    } else {
      onEnd();
    }
  }
  function scheduleAt(f, targetTime) {
    let timeout = (targetTime * 1e3 - (now() - startTime)) / speed;
    if (timeout < 0) {
      timeout = 0;
    }
    return setTimeout(f, timeout);
  }
  function runNextEvent() {
    let event = events[nextEventIndex];
    let elapsedWallTime;
    do {
      lastEventTime = event[0];
      nextEventIndex++;
      const stop = executeEvent2(event);
      if (stop) {
        return;
      }
      event = events[nextEventIndex];
      elapsedWallTime = now() - startTime;
    } while (event && elapsedWallTime > event[0] * 1e3);
    scheduleNextEvent();
  }
  function cancelNextEvent() {
    clearTimeout(eventTimeoutId);
    eventTimeoutId = null;
  }
  function executeEvent2(event) {
    const [time, type, data] = event;
    if (type === "o") {
      feed(data);
    } else if (type === "i") {
      onInput(data);
    } else if (type === "r") {
      const [cols2, rows2] = data.split("x");
      resize(cols2, rows2);
    } else if (type === "m") {
      onMarker(data);
      if (pauseOnMarkers) {
        pause();
        pauseElapsedTime = time * 1e3;
        setState("idle", {
          reason: "paused"
        });
        return true;
      }
    }
    return false;
  }
  function onEnd() {
    cancelNextEvent();
    playCount++;
    if (loop === true || typeof loop === "number" && playCount < loop) {
      nextEventIndex = 0;
      startTime = now();
      feed("\x1Bc");
      resizeTerminalToInitialSize();
      scheduleNextEvent();
      if (audioElement) {
        audioElement.currentTime = 0;
      }
    } else {
      pauseElapsedTime = duration * 1e3;
      setState("ended");
      if (audioElement) {
        audioElement.pause();
      }
    }
  }
  async function play() {
    if (eventTimeoutId) throw new Error("already playing");
    if (events[nextEventIndex] === void 0) throw new Error("already ended");
    if (effectiveStartAt !== null) {
      seek(effectiveStartAt);
    }
    await resume();
    return true;
  }
  function pause() {
    shouldResumeOnAudioPlaying = false;
    if (audioElement) {
      audioElement.pause();
    }
    if (!eventTimeoutId) return true;
    cancelNextEvent();
    pauseElapsedTime = now() - startTime;
    return true;
  }
  async function resume() {
    if (audioElement && !audioCtx) setupAudioCtx();
    startTime = now() - pauseElapsedTime;
    pauseElapsedTime = null;
    scheduleNextEvent();
    if (audioElement) {
      await audioElement.play();
    }
  }
  async function seek(where) {
    if (waitingForAudio) {
      return false;
    }
    const isPlaying = !!eventTimeoutId;
    pause();
    if (audioElement) {
      audioElement.pause();
    }
    const currentTime = (pauseElapsedTime ?? 0) / 1e3;
    if (typeof where === "string") {
      if (where === "<<") {
        where = currentTime - 5;
      } else if (where === ">>") {
        where = currentTime + 5;
      } else if (where === "<<<") {
        where = currentTime - 0.1 * duration;
      } else if (where === ">>>") {
        where = currentTime + 0.1 * duration;
      } else if (where[where.length - 1] === "%") {
        where = parseFloat(where.substring(0, where.length - 1)) / 100 * duration;
      }
    } else if (typeof where === "object") {
      if (where.marker === "prev") {
        where = findMarkerTimeBefore(currentTime) ?? 0;
        if (isPlaying && currentTime - where < 1) {
          where = findMarkerTimeBefore(where) ?? 0;
        }
      } else if (where.marker === "next") {
        where = findMarkerTimeAfter(currentTime) ?? duration;
      } else if (typeof where.marker === "number") {
        const marker = markers[where.marker];
        if (marker === void 0) {
          throw new Error(`invalid marker index: ${where.marker}`);
        } else {
          where = marker[0];
        }
      }
    }
    const targetTime = Math.min(Math.max(where, 0), duration);
    if (targetTime * 1e3 === pauseElapsedTime) return false;
    if (targetTime < lastEventTime) {
      feed("\x1Bc");
      resizeTerminalToInitialSize();
      nextEventIndex = 0;
      lastEventTime = 0;
    }
    let event = events[nextEventIndex];
    while (event && event[0] <= targetTime) {
      if (event[1] === "o" || event[1] === "r") {
        executeEvent2(event);
      }
      lastEventTime = event[0];
      event = events[++nextEventIndex];
    }
    pauseElapsedTime = targetTime * 1e3;
    effectiveStartAt = null;
    if (audioElement && audioSeekable) {
      audioElement.currentTime = targetTime / speed;
    }
    if (isPlaying) {
      await resume();
    } else if (events[nextEventIndex] === void 0) {
      onEnd();
    }
    return true;
  }
  function findMarkerTimeBefore(time) {
    if (markers.length == 0) return;
    let i2 = 0;
    let marker = markers[i2];
    let lastMarkerTimeBefore;
    while (marker && marker[0] < time) {
      lastMarkerTimeBefore = marker[0];
      marker = markers[++i2];
    }
    return lastMarkerTimeBefore;
  }
  function findMarkerTimeAfter(time) {
    if (markers.length == 0) return;
    let i2 = markers.length - 1;
    let marker = markers[i2];
    let firstMarkerTimeAfter;
    while (marker && marker[0] > time) {
      firstMarkerTimeAfter = marker[0];
      marker = markers[--i2];
    }
    return firstMarkerTimeAfter;
  }
  function step(n2) {
    if (n2 === void 0) {
      n2 = 1;
    }
    let nextEvent;
    let targetIndex;
    if (n2 > 0) {
      let index = nextEventIndex;
      nextEvent = events[index];
      for (let i2 = 0; i2 < n2; i2++) {
        while (nextEvent !== void 0 && nextEvent[1] !== "o") {
          nextEvent = events[++index];
        }
        if (nextEvent !== void 0 && nextEvent[1] === "o") {
          targetIndex = index;
        }
      }
    } else {
      let index = Math.max(nextEventIndex - 2, 0);
      nextEvent = events[index];
      for (let i2 = n2; i2 < 0; i2++) {
        while (nextEvent !== void 0 && nextEvent[1] !== "o") {
          nextEvent = events[--index];
        }
        if (nextEvent !== void 0 && nextEvent[1] === "o") {
          targetIndex = index;
        }
      }
      if (targetIndex !== void 0) {
        feed("\x1Bc");
        resizeTerminalToInitialSize();
        nextEventIndex = 0;
      }
    }
    if (targetIndex === void 0) return;
    while (nextEventIndex <= targetIndex) {
      nextEvent = events[nextEventIndex++];
      if (nextEvent[1] === "o" || nextEvent[1] === "r") {
        executeEvent2(nextEvent);
      }
    }
    lastEventTime = nextEvent[0];
    pauseElapsedTime = lastEventTime * 1e3;
    effectiveStartAt = null;
    if (audioElement && audioSeekable) {
      audioElement.currentTime = lastEventTime / speed;
    }
    if (events[targetIndex + 1] === void 0) {
      onEnd();
    }
  }
  async function restart() {
    if (eventTimeoutId) throw new Error("still playing");
    if (events[nextEventIndex] !== void 0) throw new Error("not ended");
    seek(0);
    await resume();
    return true;
  }
  function getPoster(time) {
    return events.filter((e) => e[0] < time && e[1] === "o").map((e) => e[2]);
  }
  function getCurrentTime() {
    if (eventTimeoutId) {
      return (now() - startTime) / 1e3;
    } else {
      return (pauseElapsedTime ?? 0) / 1e3;
    }
  }
  function resizeTerminalToInitialSize() {
    resize(initialCols, initialRows);
  }
  function setupAudioCtx() {
    audioCtx = new AudioContext({
      latencyHint: "interactive"
    });
    const src2 = audioCtx.createMediaElementSource(audioElement);
    src2.connect(audioCtx.destination);
    now = audioNow;
  }
  function audioNow() {
    if (!audioCtx) throw new Error("audio context not started - can't tell time!");
    const {
      contextTime,
      performanceTime
    } = audioCtx.getOutputTimestamp();
    return performanceTime === 0 ? contextTime * 1e3 : contextTime * 1e3 + (performance.now() - performanceTime);
  }
  function onAudioWaiting() {
    logger.debug("audio buffering");
    waitingForAudio = true;
    shouldResumeOnAudioPlaying = !!eventTimeoutId;
    waitingTimeout = setTimeout(() => setState("loading"), 1e3);
    if (!eventTimeoutId) return true;
    logger.debug("pausing session playback");
    cancelNextEvent();
    pauseElapsedTime = now() - startTime;
  }
  function onAudioPlaying() {
    logger.debug("audio resumed");
    clearTimeout(waitingTimeout);
    setState("playing");
    if (!waitingForAudio) return;
    waitingForAudio = false;
    if (shouldResumeOnAudioPlaying) {
      logger.debug("resuming session playback");
      startTime = now() - pauseElapsedTime;
      pauseElapsedTime = null;
      scheduleNextEvent();
    }
  }
  function mute() {
    if (audioElement) {
      audioElement.muted = true;
      return true;
    }
  }
  function unmute() {
    if (audioElement) {
      audioElement.muted = false;
      return true;
    }
  }
  return {
    init: init2,
    play,
    pause,
    seek,
    step,
    restart,
    stop: pause,
    mute,
    unmute,
    getCurrentTime
  };
}
function batcher(logger) {
  let minFrameTime = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : 1 / 60;
  let prevEvent;
  return (emit) => {
    let ic = 0;
    let oc = 0;
    return {
      step: (event) => {
        ic++;
        if (prevEvent === void 0) {
          prevEvent = event;
          return;
        }
        if (event[1] === "o" && prevEvent[1] === "o" && event[0] - prevEvent[0] < minFrameTime) {
          prevEvent[2] += event[2];
        } else {
          emit(prevEvent);
          prevEvent = event;
          oc++;
        }
      },
      flush: () => {
        if (prevEvent !== void 0) {
          emit(prevEvent);
          oc++;
        }
        logger.debug(`batched ${ic} frames to ${oc} frames`);
      }
    };
  };
}
function prepare(recording2, logger, _ref4) {
  let {
    startAt = 0,
    idleTimeLimit,
    minFrameTime,
    inputOffset,
    markers_
  } = _ref4;
  let {
    events
  } = recording2;
  if (!(events instanceof Stream)) {
    events = new Stream(events);
  }
  idleTimeLimit = idleTimeLimit ?? recording2.idleTimeLimit ?? Infinity;
  const limiterOutput = {
    offset: 0
  };
  events = events.transform(batcher(logger, minFrameTime)).map(timeLimiter(idleTimeLimit, startAt, limiterOutput)).map(markerWrapper());
  if (markers_ !== void 0) {
    markers_ = new Stream(markers_).map(normalizeMarker);
    events = events.filter((e) => e[1] !== "m").multiplex(markers_, (a2, b) => a2[0] < b[0]).map(markerWrapper());
  }
  events = events.toArray();
  if (inputOffset !== void 0) {
    events = events.map((e) => e[1] === "i" ? [e[0] + inputOffset, e[1], e[2]] : e);
    events.sort((a2, b) => a2[0] - b[0]);
  }
  const duration = events[events.length - 1][0];
  const effectiveStartAt = startAt - limiterOutput.offset;
  return {
    ...recording2,
    events,
    duration,
    effectiveStartAt
  };
}
function normalizeMarker(m) {
  return typeof m === "number" ? [m, "m", ""] : [m[0], "m", m[1]];
}
function timeLimiter(idleTimeLimit, startAt, output2) {
  let prevT = 0;
  let shift = 0;
  return function(e) {
    const delay = e[0] - prevT;
    const delta = delay - idleTimeLimit;
    prevT = e[0];
    if (delta > 0) {
      shift += delta;
      if (e[0] < startAt) {
        output2.offset += delta;
      }
    }
    return [e[0] - shift, e[1], e[2]];
  };
}
function markerWrapper() {
  let i2 = 0;
  return function(e) {
    if (e[1] === "m") {
      return [e[0], e[1], {
        index: i2++,
        time: e[0],
        label: e[2]
      }];
    } else {
      return e;
    }
  };
}
function dump(recording2, filename) {
  const link2 = document.createElement("a");
  const events = recording2.events.map((e) => e[1] === "m" ? [e[0], e[1], e[2].label] : e);
  const asciicast = unparseAsciicastV2({
    ...recording2,
    events
  });
  link2.href = URL.createObjectURL(new Blob([asciicast], {
    type: "text/plain"
  }));
  link2.download = filename;
  link2.click();
}
async function createAudioElement(src) {
  const audio = new Audio();
  audio.preload = "metadata";
  audio.loop = false;
  audio.crossOrigin = "anonymous";
  let resolve;
  const canPlay = new Promise((resolve_) => {
    resolve = resolve_;
  });
  function onCanPlay() {
    resolve();
    audio.removeEventListener("canplay", onCanPlay);
  }
  audio.addEventListener("canplay", onCanPlay);
  audio.src = src;
  audio.load();
  await canPlay;
  return audio;
}
function clock(_ref, _ref2, _ref3) {
  let {
    hourColor = 3,
    minuteColor = 4,
    separatorColor = 9
  } = _ref;
  let {
    feed
  } = _ref2;
  let {
    cols = 5,
    rows = 1
  } = _ref3;
  const middleRow = Math.floor(rows / 2);
  const leftPad = Math.floor(cols / 2) - 2;
  const setupCursor = `\x1B[?25l\x1B[1m\x1B[${middleRow}B`;
  let intervalId;
  const getCurrentTime = () => {
    const d = /* @__PURE__ */ new Date();
    const h = d.getHours();
    const m = d.getMinutes();
    const seqs = [];
    seqs.push("\r");
    for (let i2 = 0; i2 < leftPad; i2++) {
      seqs.push(" ");
    }
    seqs.push(`\x1B[3${hourColor}m`);
    if (h < 10) {
      seqs.push("0");
    }
    seqs.push(`${h}`);
    seqs.push(`\x1B[3${separatorColor};5m:\x1B[25m`);
    seqs.push(`\x1B[3${minuteColor}m`);
    if (m < 10) {
      seqs.push("0");
    }
    seqs.push(`${m}`);
    return seqs;
  };
  const updateTime = () => {
    getCurrentTime().forEach(feed);
  };
  return {
    init: () => {
      const duration = 24 * 60;
      const poster = [setupCursor].concat(getCurrentTime());
      return {
        cols,
        rows,
        duration,
        poster
      };
    },
    play: () => {
      feed(setupCursor);
      updateTime();
      intervalId = setInterval(updateTime, 1e3);
      return true;
    },
    stop: () => {
      clearInterval(intervalId);
    },
    getCurrentTime: () => {
      const d = /* @__PURE__ */ new Date();
      return d.getHours() * 60 + d.getMinutes();
    }
  };
}
function random(src, _ref, _ref2) {
  let {
    feed
  } = _ref;
  let {
    speed
  } = _ref2;
  const base2 = " ".charCodeAt(0);
  const range = "~".charCodeAt(0) - base2;
  let timeoutId;
  const schedule = () => {
    const t2 = Math.pow(5, Math.random() * 4);
    timeoutId = setTimeout(print, t2 / speed);
  };
  const print = () => {
    schedule();
    const char = String.fromCharCode(base2 + Math.floor(Math.random() * range));
    feed(char);
  };
  return () => {
    schedule();
    return () => clearInterval(timeoutId);
  };
}
function benchmark(_ref, _ref2) {
  let {
    url,
    iterations = 10
  } = _ref;
  let {
    feed,
    setState
  } = _ref2;
  let data;
  let byteCount = 0;
  return {
    async init() {
      const recording2 = await parse$2(await fetch(url));
      const {
        cols,
        rows,
        events
      } = recording2;
      data = Array.from(events).filter((_ref3) => {
        let [_time, type, _text] = _ref3;
        return type === "o";
      }).map((_ref4) => {
        let [time, _type, text2] = _ref4;
        return [time, text2];
      });
      const duration = data[data.length - 1][0];
      for (const [_, text2] of data) {
        byteCount += new Blob([text2]).size;
      }
      return {
        cols,
        rows,
        duration
      };
    },
    play() {
      const startTime = performance.now();
      for (let i2 = 0; i2 < iterations; i2++) {
        for (const [_, text2] of data) {
          feed(text2);
        }
        feed("\x1Bc");
      }
      const endTime = performance.now();
      const duration = (endTime - startTime) / 1e3;
      const throughput = byteCount * iterations / duration;
      const throughputMbs = byteCount / (1024 * 1024) * iterations / duration;
      console.info("benchmark: result", {
        byteCount,
        iterations,
        duration,
        throughput,
        throughputMbs
      });
      setTimeout(() => {
        setState("stopped", {
          reason: "ended"
        });
      }, 0);
      return true;
    }
  };
}
class Queue {
  constructor() {
    this.items = [];
    this.onPush = void 0;
  }
  push(item) {
    this.items.push(item);
    if (this.onPush !== void 0) {
      this.onPush(this.popAll());
      this.onPush = void 0;
    }
  }
  popAll() {
    if (this.items.length > 0) {
      const items = this.items;
      this.items = [];
      return items;
    } else {
      const thiz = this;
      return new Promise((resolve) => {
        thiz.onPush = resolve;
      });
    }
  }
}
function getBuffer(bufferTime, feed, resize, onInput, onMarker, setTime, baseStreamTime, minFrameTime, logger) {
  const execute = executeEvent(feed, resize, onInput, onMarker);
  if (bufferTime === 0) {
    logger.debug("using no buffer");
    return nullBuffer(execute);
  } else {
    bufferTime = bufferTime ?? {};
    let getBufferTime;
    if (typeof bufferTime === "number") {
      logger.debug(`using fixed time buffer (${bufferTime} ms)`);
      getBufferTime = (_latency) => bufferTime;
    } else if (typeof bufferTime === "function") {
      logger.debug("using custom dynamic buffer");
      getBufferTime = bufferTime({
        logger
      });
    } else {
      logger.debug("using adaptive buffer", bufferTime);
      getBufferTime = adaptiveBufferTimeProvider({
        logger
      }, bufferTime);
    }
    return buffer(getBufferTime, execute, setTime, logger, baseStreamTime ?? 0, minFrameTime);
  }
}
function nullBuffer(execute) {
  return {
    pushEvent(event) {
      execute(event[1], event[2]);
    },
    pushText(text2) {
      execute("o", text2);
    },
    stop() {
    }
  };
}
function executeEvent(feed, resize, onInput, onMarker) {
  return function(code2, data) {
    if (code2 === "o") {
      feed(data);
    } else if (code2 === "i") {
      onInput(data);
    } else if (code2 === "r") {
      resize(data.cols, data.rows);
    } else if (code2 === "m") {
      onMarker(data);
    }
  };
}
function buffer(getBufferTime, execute, setTime, logger, baseStreamTime) {
  let minFrameTime = arguments.length > 5 && arguments[5] !== void 0 ? arguments[5] : 1 / 60;
  let epoch = performance.now() - baseStreamTime * 1e3;
  let bufferTime = getBufferTime(0);
  const queue = new Queue();
  minFrameTime *= 1e3;
  let prevElapsedStreamTime = -minFrameTime;
  let stop = false;
  function elapsedWallTime() {
    return performance.now() - epoch;
  }
  setTimeout(async () => {
    while (!stop) {
      const events = await queue.popAll();
      if (stop) return;
      for (const event of events) {
        const elapsedStreamTime = event[0] * 1e3 + bufferTime;
        if (elapsedStreamTime - prevElapsedStreamTime < minFrameTime) {
          execute(event[1], event[2]);
          continue;
        }
        const delay = elapsedStreamTime - elapsedWallTime();
        if (delay > 0) {
          await sleep(delay);
          if (stop) return;
        }
        setTime(event[0]);
        execute(event[1], event[2]);
        prevElapsedStreamTime = elapsedStreamTime;
      }
    }
  }, 0);
  return {
    pushEvent(event) {
      let latency = elapsedWallTime() - event[0] * 1e3;
      if (latency < 0) {
        logger.debug(`correcting epoch by ${latency} ms`);
        epoch += latency;
        latency = 0;
      }
      bufferTime = getBufferTime(latency);
      queue.push(event);
    },
    pushText(text2) {
      queue.push([elapsedWallTime() / 1e3, "o", text2]);
    },
    stop() {
      stop = true;
      queue.push(void 0);
    }
  };
}
function sleep(t2) {
  return new Promise((resolve) => {
    setTimeout(resolve, t2);
  });
}
function adaptiveBufferTimeProvider() {
  let {
    logger
  } = arguments.length > 0 && arguments[0] !== void 0 ? arguments[0] : {};
  let {
    minBufferTime = 50,
    bufferLevelStep = 100,
    maxBufferLevel = 50,
    transitionDuration = 500,
    peakHalfLifeUp = 100,
    peakHalfLifeDown = 1e4,
    floorHalfLifeUp = 5e3,
    floorHalfLifeDown = 100,
    idealHalfLifeUp = 1e3,
    idealHalfLifeDown = 5e3,
    safetyMultiplier = 1.2,
    minImprovementDuration = 3e3
  } = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {};
  function levelToMs(level) {
    return level === 0 ? minBufferTime : bufferLevelStep * level;
  }
  let bufferLevel = 1;
  let bufferTime = levelToMs(bufferLevel);
  let lastUpdateTime = performance.now();
  let smoothedPeakLatency = null;
  let smoothedFloorLatency = null;
  let smoothedIdealBufferTime = null;
  let stableSince = null;
  let targetBufferTime = null;
  let transitionRate = null;
  return function(latency) {
    const now = performance.now();
    const dt2 = Math.max(0, now - lastUpdateTime);
    lastUpdateTime = now;
    if (smoothedPeakLatency === null) {
      smoothedPeakLatency = latency;
    } else if (latency > smoothedPeakLatency) {
      const alphaUp = 1 - Math.pow(2, -dt2 / peakHalfLifeUp);
      smoothedPeakLatency += alphaUp * (latency - smoothedPeakLatency);
    } else {
      const alphaDown = 1 - Math.pow(2, -dt2 / peakHalfLifeDown);
      smoothedPeakLatency += alphaDown * (latency - smoothedPeakLatency);
    }
    smoothedPeakLatency = Math.max(smoothedPeakLatency, 0);
    if (smoothedFloorLatency === null) {
      smoothedFloorLatency = latency;
    } else if (latency > smoothedFloorLatency) {
      const alphaUp = 1 - Math.pow(2, -dt2 / floorHalfLifeUp);
      smoothedFloorLatency += alphaUp * (latency - smoothedFloorLatency);
    } else {
      const alphaDown = 1 - Math.pow(2, -dt2 / floorHalfLifeDown);
      smoothedFloorLatency += alphaDown * (latency - smoothedFloorLatency);
    }
    smoothedFloorLatency = Math.max(smoothedFloorLatency, 0);
    const jitter = smoothedPeakLatency - smoothedFloorLatency;
    const idealBufferTime = safetyMultiplier * (smoothedPeakLatency + jitter);
    if (smoothedIdealBufferTime === null) {
      smoothedIdealBufferTime = idealBufferTime;
    } else if (idealBufferTime > smoothedIdealBufferTime) {
      const alphaUp = 1 - Math.pow(2, -dt2 / idealHalfLifeUp);
      smoothedIdealBufferTime += +alphaUp * (idealBufferTime - smoothedIdealBufferTime);
    } else {
      const alphaDown = 1 - Math.pow(2, -dt2 / idealHalfLifeDown);
      smoothedIdealBufferTime += +alphaDown * (idealBufferTime - smoothedIdealBufferTime);
    }
    let newBufferLevel;
    if (smoothedIdealBufferTime <= minBufferTime) {
      newBufferLevel = 0;
    } else {
      newBufferLevel = clamp(Math.ceil(smoothedIdealBufferTime / bufferLevelStep), 1, maxBufferLevel);
    }
    if (latency > bufferTime) {
      logger.debug("buffer underrun", {
        latency,
        bufferTime
      });
    }
    if (newBufferLevel > bufferLevel) {
      if (latency > bufferTime) {
        bufferLevel = Math.min(newBufferLevel, bufferLevel + 3);
      } else {
        bufferLevel += 1;
      }
      targetBufferTime = levelToMs(bufferLevel);
      transitionRate = (targetBufferTime - bufferTime) / transitionDuration;
      stableSince = null;
      logger.debug("raising buffer", {
        latency,
        bufferTime,
        targetBufferTime
      });
    } else if (newBufferLevel < bufferLevel) {
      if (stableSince == null) stableSince = now;
      if (now - stableSince >= minImprovementDuration) {
        bufferLevel -= 1;
        targetBufferTime = levelToMs(bufferLevel);
        transitionRate = (targetBufferTime - bufferTime) / transitionDuration;
        stableSince = now;
        logger.debug("lowering buffer", {
          latency,
          bufferTime,
          targetBufferTime
        });
      }
    } else {
      stableSince = null;
    }
    if (targetBufferTime !== null) {
      bufferTime += transitionRate * dt2;
      if (transitionRate >= 0 && bufferTime > targetBufferTime || transitionRate < 0 && bufferTime < targetBufferTime) {
        bufferTime = targetBufferTime;
        targetBufferTime = null;
      }
    }
    return bufferTime;
  };
}
function clamp(x2, lo2, hi) {
  return Math.min(hi, Math.max(lo2, x2));
}
const ONE_SEC_IN_USEC = 1e6;
function alisHandler(logger) {
  const outputDecoder = new TextDecoder();
  const inputDecoder = new TextDecoder();
  let handler = parseMagicString;
  let lastEventTime;
  let markerIndex = 0;
  function parseMagicString(buffer2) {
    const text2 = new TextDecoder().decode(buffer2);
    if (text2 === "ALiS") {
      handler = parseFirstFrame;
    } else {
      throw new Error("not an ALiS v1 live stream");
    }
  }
  function parseFirstFrame(buffer2) {
    const view = new BinaryReader(new DataView(buffer2));
    const type = view.getUint8();
    if (type !== 1) throw new Error(`expected reset (0x01) frame, got ${type}`);
    return parseResetFrame(view, buffer2);
  }
  function parseResetFrame(view, buffer2) {
    view.decodeVarUint();
    let time = view.decodeVarUint();
    lastEventTime = time;
    time = time / ONE_SEC_IN_USEC;
    markerIndex = 0;
    const cols = view.decodeVarUint();
    const rows = view.decodeVarUint();
    const themeFormat = view.getUint8();
    let theme;
    if (themeFormat === 8) {
      const len = (2 + 8) * 3;
      theme = parseTheme(new Uint8Array(buffer2, view.offset, len));
      view.forward(len);
    } else if (themeFormat === 16) {
      const len = (2 + 16) * 3;
      theme = parseTheme(new Uint8Array(buffer2, view.offset, len));
      view.forward(len);
    } else if (themeFormat !== 0) {
      throw new Error(`alis: invalid theme format (${themeFormat})`);
    }
    const initLen = view.decodeVarUint();
    let init2;
    if (initLen > 0) {
      init2 = outputDecoder.decode(new Uint8Array(buffer2, view.offset, initLen));
    }
    handler = parseFrame2;
    return {
      time,
      term: {
        size: {
          cols,
          rows
        },
        theme,
        init: init2
      }
    };
  }
  function parseFrame2(buffer2) {
    const view = new BinaryReader(new DataView(buffer2));
    const type = view.getUint8();
    if (type === 1) {
      return parseResetFrame(view, buffer2);
    } else if (type === 111) {
      return parseOutputFrame(view, buffer2);
    } else if (type === 105) {
      return parseInputFrame(view, buffer2);
    } else if (type === 114) {
      return parseResizeFrame(view);
    } else if (type === 109) {
      return parseMarkerFrame(view, buffer2);
    } else if (type === 4) {
      handler = parseFirstFrame;
      return false;
    } else {
      logger.debug(`alis: unknown frame type: ${type}`);
    }
  }
  function parseOutputFrame(view, buffer2) {
    view.decodeVarUint();
    const relTime = view.decodeVarUint();
    lastEventTime += relTime;
    const len = view.decodeVarUint();
    const text2 = outputDecoder.decode(new Uint8Array(buffer2, view.offset, len));
    return [lastEventTime / ONE_SEC_IN_USEC, "o", text2];
  }
  function parseInputFrame(view, buffer2) {
    view.decodeVarUint();
    const relTime = view.decodeVarUint();
    lastEventTime += relTime;
    const len = view.decodeVarUint();
    const text2 = inputDecoder.decode(new Uint8Array(buffer2, view.offset, len));
    return [lastEventTime / ONE_SEC_IN_USEC, "i", text2];
  }
  function parseResizeFrame(view) {
    view.decodeVarUint();
    const relTime = view.decodeVarUint();
    lastEventTime += relTime;
    const cols = view.decodeVarUint();
    const rows = view.decodeVarUint();
    return [lastEventTime / ONE_SEC_IN_USEC, "r", {
      cols,
      rows
    }];
  }
  function parseMarkerFrame(view, buffer2) {
    view.decodeVarUint();
    const relTime = view.decodeVarUint();
    lastEventTime += relTime;
    const len = view.decodeVarUint();
    const decoder = new TextDecoder();
    const index = markerIndex++;
    const time = lastEventTime / ONE_SEC_IN_USEC;
    const label2 = decoder.decode(new Uint8Array(buffer2, view.offset, len));
    return [time, "m", {
      index,
      time,
      label: label2
    }];
  }
  return function(buffer2) {
    return handler(buffer2);
  };
}
function parseTheme(arr) {
  const colorCount = arr.length / 3;
  const foreground = hexColor(arr[0], arr[1], arr[2]);
  const background = hexColor(arr[3], arr[4], arr[5]);
  const palette = [];
  for (let i2 = 2; i2 < colorCount; i2++) {
    palette.push(hexColor(arr[i2 * 3], arr[i2 * 3 + 1], arr[i2 * 3 + 2]));
  }
  return {
    foreground,
    background,
    palette
  };
}
function hexColor(r2, g, b) {
  return `#${byteToHex(r2)}${byteToHex(g)}${byteToHex(b)}`;
}
function byteToHex(value2) {
  return value2.toString(16).padStart(2, "0");
}
class BinaryReader {
  constructor(inner) {
    let offset = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : 0;
    this.inner = inner;
    this.offset = offset;
  }
  forward(delta) {
    this.offset += delta;
  }
  getUint8() {
    const value2 = this.inner.getUint8(this.offset);
    this.offset += 1;
    return value2;
  }
  decodeVarUint() {
    let number2 = BigInt(0);
    let shift = BigInt(0);
    let byte = this.getUint8();
    while (byte > 127) {
      byte &= 127;
      number2 += BigInt(byte) << shift;
      shift += BigInt(7);
      byte = this.getUint8();
    }
    number2 = number2 + (BigInt(byte) << shift);
    return Number(number2);
  }
}
function ascicastV2Handler() {
  let parse2 = parseHeader;
  function parseHeader(buffer2) {
    const header = JSON.parse(buffer2);
    if (header.version !== 2) {
      throw new Error("not an asciicast v2 stream");
    }
    parse2 = parseEvent;
    return {
      time: 0,
      term: {
        size: {
          cols: header.width,
          rows: header.height
        }
      }
    };
  }
  function parseEvent(buffer2) {
    const event = JSON.parse(buffer2);
    if (event[1] === "r") {
      const [cols, rows] = event[2].split("x");
      return [event[0], "r", {
        cols: parseInt(cols, 10),
        rows: parseInt(rows, 10)
      }];
    } else {
      return event;
    }
  }
  return function(buffer2) {
    return parse2(buffer2);
  };
}
function ascicastV3Handler() {
  let parse2 = parseHeader;
  let currentTime = 0;
  function parseHeader(buffer2) {
    const header = JSON.parse(buffer2);
    if (header.version !== 3) {
      throw new Error("not an asciicast v3 stream");
    }
    parse2 = parseEvent;
    const term = {
      size: {
        cols: header.term.cols,
        rows: header.term.rows
      }
    };
    if (header.term.theme) {
      term.theme = {
        foreground: header.term.theme.fg,
        background: header.term.theme.bg,
        palette: header.term.theme.palette.split(":")
      };
    }
    return {
      time: 0,
      term
    };
  }
  function parseEvent(buffer2) {
    const event = JSON.parse(buffer2);
    const [interval, eventType, data] = event;
    currentTime += interval;
    if (eventType === "r") {
      const [cols, rows] = data.split("x");
      return [currentTime, "r", {
        cols: parseInt(cols, 10),
        rows: parseInt(rows, 10)
      }];
    } else {
      return [currentTime, eventType, data];
    }
  }
  return function(buffer2) {
    return parse2(buffer2);
  };
}
function rawHandler() {
  const outputDecoder = new TextDecoder();
  let parse2 = parseSize;
  function parseSize(buffer2) {
    const text2 = outputDecoder.decode(buffer2, {
      stream: true
    });
    const [cols, rows] = sizeFromResizeSeq(text2) ?? sizeFromScriptStartMessage(text2) ?? [80, 24];
    parse2 = parseOutput;
    return {
      time: 0,
      term: {
        size: {
          cols,
          rows
        },
        init: text2
      }
    };
  }
  function parseOutput(buffer2) {
    return outputDecoder.decode(buffer2, {
      stream: true
    });
  }
  return function(buffer2) {
    return parse2(buffer2);
  };
}
function sizeFromResizeSeq(text2) {
  const match2 = text2.match(/\x1b\[8;(\d+);(\d+)t/);
  if (match2 !== null) {
    return [parseInt(match2[2], 10), parseInt(match2[1], 10)];
  }
}
function sizeFromScriptStartMessage(text2) {
  const match2 = text2.match(/\[.*COLUMNS="(\d{1,3})" LINES="(\d{1,3})".*\]/);
  if (match2 !== null) {
    return [parseInt(match2[1], 10), parseInt(match2[2], 10)];
  }
}
const RECONNECT_DELAY_BASE = 500;
const RECONNECT_DELAY_CAP = 1e4;
function exponentialDelay(attempt) {
  const base2 = Math.min(RECONNECT_DELAY_BASE * Math.pow(2, attempt), RECONNECT_DELAY_CAP);
  return Math.random() * base2;
}
function websocket(_ref, _ref2, _ref3) {
  let {
    url,
    bufferTime,
    reconnectDelay = exponentialDelay,
    minFrameTime
  } = _ref;
  let {
    feed,
    reset,
    resize,
    onInput,
    onMarker,
    setState,
    logger
  } = _ref2;
  let {
    audioUrl
  } = _ref3;
  logger = new PrefixedLogger(logger, "websocket: ");
  let socket;
  let buf;
  let clock2 = new NullClock();
  let reconnectAttempt = 0;
  let successfulConnectionTimeout;
  let stop = false;
  let wasOnline = false;
  let initTimeout;
  let audioElement;
  function connect() {
    socket = new WebSocket(url, ["v1.alis", "v2.asciicast", "v3.asciicast", "raw"]);
    socket.binaryType = "arraybuffer";
    socket.onopen = () => {
      const proto = socket.protocol || "raw";
      logger.info("opened");
      logger.info(`activating ${proto} protocol handler`);
      if (proto === "v1.alis") {
        socket.onmessage = onMessage(alisHandler(logger));
      } else if (proto === "v2.asciicast") {
        socket.onmessage = onMessage(ascicastV2Handler());
      } else if (proto === "v3.asciicast") {
        socket.onmessage = onMessage(ascicastV3Handler());
      } else if (proto === "raw") {
        socket.onmessage = onMessage(rawHandler());
      }
      successfulConnectionTimeout = setTimeout(() => {
        reconnectAttempt = 0;
      }, 1e3);
    };
    socket.onclose = (event) => {
      clearTimeout(initTimeout);
      stopBuffer();
      if (stop || event.code === 1e3 || event.code === 1005) {
        logger.info("closed");
        setState("ended", {
          message: "Stream ended"
        });
      } else if (event.code === 1002) {
        logger.debug(`close reason: ${event.reason}`);
        setState("ended", {
          message: "Err: Player not compatible with the server"
        });
      } else {
        clearTimeout(successfulConnectionTimeout);
        const delay = reconnectDelay(reconnectAttempt++);
        logger.info(`unclean close, reconnecting in ${delay}...`);
        setState("loading");
        setTimeout(connect, delay);
      }
    };
    wasOnline = false;
  }
  function onMessage(handler) {
    initTimeout = setTimeout(onStreamEnd, 5e3);
    return function(event) {
      try {
        const result2 = handler(event.data);
        if (buf) {
          if (Array.isArray(result2)) {
            buf.pushEvent(result2);
          } else if (typeof result2 === "string") {
            buf.pushText(result2);
          } else if (typeof result2 === "object" && !Array.isArray(result2)) {
            onStreamReset(result2);
          } else if (result2 === false) {
            onStreamEnd();
          } else if (result2 !== void 0) {
            throw new Error(`unexpected value from protocol handler: ${result2}`);
          }
        } else {
          if (typeof result2 === "object" && !Array.isArray(result2)) {
            onStreamReset(result2);
            clearTimeout(initTimeout);
          } else if (result2 === void 0) {
            clearTimeout(initTimeout);
            initTimeout = setTimeout(onStreamEnd, 1e3);
          } else {
            clearTimeout(initTimeout);
            throw new Error(`unexpected value from protocol handler: ${result2}`);
          }
        }
      } catch (e) {
        socket.close();
        throw e;
      }
    };
  }
  function onStreamReset(_ref4) {
    let {
      time,
      term
    } = _ref4;
    const {
      size,
      init: init2,
      theme
    } = term;
    const {
      cols,
      rows
    } = size;
    logger.info(`stream reset (${cols}x${rows} @${time})`);
    setState("playing");
    stopBuffer();
    buf = getBuffer(bufferTime, feed, resize, onInput, onMarker, (t2) => clock2.setTime(t2), time, minFrameTime, logger);
    reset(cols, rows, init2, theme);
    clock2 = new Clock();
    wasOnline = true;
    if (typeof time === "number") {
      clock2.setTime(time);
    }
  }
  function onStreamEnd() {
    stopBuffer();
    if (wasOnline) {
      logger.info("stream ended");
      setState("offline", {
        message: "Stream ended"
      });
    } else {
      logger.info("stream offline");
      setState("offline", {
        message: "Stream offline"
      });
    }
    clock2 = new NullClock();
  }
  function stopBuffer() {
    if (buf) buf.stop();
    buf = null;
  }
  function startAudio() {
    if (!audioUrl) return;
    audioElement = new Audio();
    audioElement.preload = "auto";
    audioElement.crossOrigin = "anonymous";
    audioElement.src = audioUrl;
    audioElement.play();
  }
  function stopAudio() {
    if (!audioElement) return;
    audioElement.pause();
  }
  function mute() {
    if (audioElement) {
      audioElement.muted = true;
      return true;
    }
  }
  function unmute() {
    if (audioElement) {
      audioElement.muted = false;
      return true;
    }
  }
  return {
    init: () => {
      return {
        hasAudio: !!audioUrl
      };
    },
    play: () => {
      connect();
      startAudio();
    },
    stop: () => {
      stop = true;
      stopBuffer();
      if (socket !== void 0) socket.close();
      stopAudio();
    },
    mute,
    unmute,
    getCurrentTime: () => clock2.getTime()
  };
}
function eventsource(_ref, _ref2) {
  let {
    url,
    bufferTime,
    minFrameTime
  } = _ref;
  let {
    feed,
    reset,
    resize,
    onInput,
    onMarker,
    setState,
    logger
  } = _ref2;
  logger = new PrefixedLogger(logger, "eventsource: ");
  let es;
  let buf;
  let clock2 = new NullClock();
  function initBuffer(baseStreamTime) {
    if (buf !== void 0) buf.stop();
    buf = getBuffer(bufferTime, feed, resize, onInput, onMarker, (t2) => clock2.setTime(t2), baseStreamTime, minFrameTime, logger);
  }
  return {
    play: () => {
      es = new EventSource(url);
      es.addEventListener("open", () => {
        logger.info("opened");
        initBuffer();
      });
      es.addEventListener("error", (e) => {
        logger.info("errored");
        logger.debug({
          e
        });
        setState("loading");
      });
      es.addEventListener("message", (event) => {
        const e = JSON.parse(event.data);
        if (Array.isArray(e)) {
          buf.pushEvent(e);
        } else if (e.cols !== void 0 || e.width !== void 0) {
          const cols = e.cols ?? e.width;
          const rows = e.rows ?? e.height;
          logger.debug(`vt reset (${cols}x${rows})`);
          setState("playing");
          initBuffer(e.time);
          reset(cols, rows, e.init ?? void 0);
          clock2 = new Clock();
          if (typeof e.time === "number") {
            clock2.setTime(e.time);
          }
        } else if (e.state === "offline") {
          logger.info("stream offline");
          setState("offline", {
            message: "Stream offline"
          });
          clock2 = new NullClock();
        }
      });
      es.addEventListener("done", () => {
        logger.info("closed");
        es.close();
        setState("ended", {
          message: "Stream ended"
        });
      });
    },
    stop: () => {
      if (buf !== void 0) buf.stop();
      if (es !== void 0) es.close();
    },
    getCurrentTime: () => clock2.getTime()
  };
}
async function parse$1(responses, _ref) {
  let {
    encoding
  } = _ref;
  const textDecoder = new TextDecoder(encoding);
  let cols;
  let rows;
  let timing = (await responses[0].text()).split("\n").filter((line) => line.length > 0).map((line) => line.split(" "));
  if (timing[0].length < 3) {
    timing = timing.map((entry) => ["O", entry[0], entry[1]]);
  }
  const buffer2 = await responses[1].arrayBuffer();
  const array = new Uint8Array(buffer2);
  const dataOffset = array.findIndex((byte) => byte == 10) + 1;
  const header = textDecoder.decode(array.subarray(0, dataOffset));
  const sizeMatch = header.match(/COLUMNS="(\d+)" LINES="(\d+)"/);
  if (sizeMatch !== null) {
    cols = parseInt(sizeMatch[1], 10);
    rows = parseInt(sizeMatch[2], 10);
  }
  const stdout = {
    array,
    cursor: dataOffset
  };
  let stdin = stdout;
  if (responses[2] !== void 0) {
    const buffer3 = await responses[2].arrayBuffer();
    const array2 = new Uint8Array(buffer3);
    stdin = {
      array: array2,
      cursor: dataOffset
    };
  }
  const events = [];
  let time = 0;
  for (const entry of timing) {
    time += parseFloat(entry[1]);
    if (entry[0] === "O") {
      const count = parseInt(entry[2], 10);
      const bytes = stdout.array.subarray(stdout.cursor, stdout.cursor + count);
      const text2 = textDecoder.decode(bytes);
      events.push([time, "o", text2]);
      stdout.cursor += count;
    } else if (entry[0] === "I") {
      const count = parseInt(entry[2], 10);
      const bytes = stdin.array.subarray(stdin.cursor, stdin.cursor + count);
      const text2 = textDecoder.decode(bytes);
      events.push([time, "i", text2]);
      stdin.cursor += count;
    } else if (entry[0] === "S" && entry[2] === "SIGWINCH") {
      const cols2 = parseInt(entry[4].slice(5), 10);
      const rows2 = parseInt(entry[3].slice(5), 10);
      events.push([time, "r", `${cols2}x${rows2}`]);
    } else if (entry[0] === "H" && entry[2] === "COLUMNS") {
      cols = parseInt(entry[3], 10);
    } else if (entry[0] === "H" && entry[2] === "LINES") {
      rows = parseInt(entry[3], 10);
    }
  }
  cols = cols ?? 80;
  rows = rows ?? 24;
  return {
    cols,
    rows,
    events
  };
}
async function parse(response, _ref) {
  let {
    encoding
  } = _ref;
  const textDecoder = new TextDecoder(encoding);
  const buffer2 = await response.arrayBuffer();
  const array = new Uint8Array(buffer2);
  const firstFrame = parseFrame(array);
  const baseTime = firstFrame.time;
  const firstFrameText = textDecoder.decode(firstFrame.data);
  const sizeMatch = firstFrameText.match(/\x1b\[8;(\d+);(\d+)t/);
  const events = [];
  let cols = 80;
  let rows = 24;
  if (sizeMatch !== null) {
    cols = parseInt(sizeMatch[2], 10);
    rows = parseInt(sizeMatch[1], 10);
  }
  let cursor = 0;
  let frame = parseFrame(array);
  while (frame !== void 0) {
    const time = frame.time - baseTime;
    const text2 = textDecoder.decode(frame.data);
    events.push([time, "o", text2]);
    cursor += frame.len;
    frame = parseFrame(array.subarray(cursor));
  }
  return {
    cols,
    rows,
    events
  };
}
function parseFrame(array) {
  if (array.length < 13) return;
  const time = parseTimestamp(array.subarray(0, 8));
  const len = parseNumber(array.subarray(8, 12));
  const data = array.subarray(12, 12 + len);
  return {
    time,
    data,
    len: len + 12
  };
}
function parseNumber(array) {
  return array[0] + array[1] * 256 + array[2] * 256 * 256 + array[3] * 256 * 256 * 256;
}
function parseTimestamp(array) {
  const sec = parseNumber(array.subarray(0, 4));
  const usec = parseNumber(array.subarray(4, 8));
  return sec + usec / 1e6;
}
const DEFAULT_COLS = 80;
const DEFAULT_ROWS = 24;
const vt = init({
  module: vtWasmModule
});
class State {
  constructor(core) {
    this.core = core;
    this.driver = core.driver;
  }
  onEnter(data) {
  }
  init() {
  }
  play() {
  }
  pause() {
  }
  togglePlay() {
  }
  mute() {
    if (this.driver && this.driver.mute()) {
      this.core._dispatchEvent("muted", true);
    }
  }
  unmute() {
    if (this.driver && this.driver.unmute()) {
      this.core._dispatchEvent("muted", false);
    }
  }
  seek(where) {
    return false;
  }
  step(n2) {
  }
  stop() {
    this.driver.stop();
  }
}
class UninitializedState extends State {
  async init() {
    try {
      await this.core._initializeDriver();
      return this.core._setState("idle");
    } catch (e) {
      this.core._setState("errored");
      throw e;
    }
  }
  async play() {
    this.core._dispatchEvent("play");
    const idleState = await this.init();
    await idleState.doPlay();
  }
  async togglePlay() {
    await this.play();
  }
  async seek(where) {
    const idleState = await this.init();
    return await idleState.seek(where);
  }
  async step(n2) {
    const idleState = await this.init();
    await idleState.step(n2);
  }
  stop() {
  }
}
class Idle extends State {
  onEnter(_ref) {
    let {
      reason,
      message: message2
    } = _ref;
    this.core._dispatchEvent("idle", {
      message: message2
    });
    if (reason === "paused") {
      this.core._dispatchEvent("pause");
    }
  }
  async play() {
    this.core._dispatchEvent("play");
    await this.doPlay();
  }
  async doPlay() {
    const stop = await this.driver.play();
    if (stop === true) {
      this.core._setState("playing");
    } else if (typeof stop === "function") {
      this.core._setState("playing");
      this.driver.stop = stop;
    }
  }
  async togglePlay() {
    await this.play();
  }
  seek(where) {
    return this.driver.seek(where);
  }
  step(n2) {
    this.driver.step(n2);
  }
}
class PlayingState extends State {
  onEnter() {
    this.core._dispatchEvent("playing");
  }
  pause() {
    if (this.driver.pause() === true) {
      this.core._setState("idle", {
        reason: "paused"
      });
    }
  }
  togglePlay() {
    this.pause();
  }
  seek(where) {
    return this.driver.seek(where);
  }
}
class LoadingState extends State {
  onEnter() {
    this.core._dispatchEvent("loading");
  }
}
class OfflineState extends State {
  onEnter(_ref2) {
    let {
      message: message2
    } = _ref2;
    this.core._dispatchEvent("offline", {
      message: message2
    });
  }
}
class EndedState extends State {
  onEnter(_ref3) {
    let {
      message: message2
    } = _ref3;
    this.core._dispatchEvent("ended", {
      message: message2
    });
  }
  async play() {
    this.core._dispatchEvent("play");
    if (await this.driver.restart()) {
      this.core._setState("playing");
    }
  }
  async togglePlay() {
    await this.play();
  }
  async seek(where) {
    if (await this.driver.seek(where) === true) {
      this.core._setState("idle");
      return true;
    }
    return false;
  }
}
class ErroredState extends State {
  onEnter() {
    this.core._dispatchEvent("errored");
  }
}
class Core {
  constructor(src, opts) {
    this.logger = opts.logger;
    this.state = new UninitializedState(this);
    this.stateName = "uninitialized";
    this.driver = getDriver(src);
    this.changedLines = /* @__PURE__ */ new Set();
    this.duration = void 0;
    this.cols = opts.cols;
    this.rows = opts.rows;
    this.speed = opts.speed;
    this.loop = opts.loop;
    this.autoPlay = opts.autoPlay;
    this.idleTimeLimit = opts.idleTimeLimit;
    this.preload = opts.preload;
    this.startAt = parseNpt(opts.startAt);
    this.poster = this._parsePoster(opts.poster);
    this.markers = this._normalizeMarkers(opts.markers);
    this.pauseOnMarkers = opts.pauseOnMarkers;
    this.audioUrl = opts.audioUrl;
    this.boldIsBright = opts.boldIsBright ?? false;
    this.commandQueue = Promise.resolve();
    this.needsClear = false;
    this.eventHandlers = /* @__PURE__ */ new Map([["ended", []], ["errored", []], ["idle", []], ["input", []], ["loading", []], ["marker", []], ["metadata", []], ["muted", []], ["offline", []], ["pause", []], ["play", []], ["playing", []], ["ready", []], ["seeked", []], ["vtUpdate", []]]);
  }
  async init() {
    this.wasm = await vt;
    const {
      memory
    } = await this.wasm.default();
    this.memory = memory;
    this._initializeVt(this.cols ?? DEFAULT_COLS, this.rows ?? DEFAULT_ROWS);
    const feed = this._feed.bind(this);
    const onInput = (data) => {
      this._dispatchEvent("input", {
        data
      });
    };
    const onMarker = (_ref4) => {
      let {
        index,
        time,
        label: label2
      } = _ref4;
      this._dispatchEvent("marker", {
        index,
        time,
        label: label2
      });
    };
    const reset = this._resetVt.bind(this);
    const resize = this._resizeVt.bind(this);
    const setState = this._setState.bind(this);
    const posterTime = this.poster.type === "npt" && !this.autoPlay ? this.poster.value : void 0;
    this.driver = this.driver({
      feed,
      onInput,
      onMarker,
      reset,
      resize,
      setState,
      logger: this.logger
    }, {
      cols: this.cols,
      rows: this.rows,
      speed: this.speed,
      idleTimeLimit: this.idleTimeLimit,
      startAt: this.startAt,
      loop: this.loop,
      posterTime,
      markers: this.markers,
      pauseOnMarkers: this.pauseOnMarkers,
      audioUrl: this.audioUrl
    });
    if (typeof this.driver === "function") {
      this.driver = {
        play: this.driver
      };
    }
    if (this.preload || posterTime !== void 0) {
      this._withState((state) => state.init());
    }
    const config2 = {
      isPausable: !!this.driver.pause,
      isSeekable: !!this.driver.seek
    };
    if (this.driver.init === void 0) {
      this.driver.init = () => {
        return {};
      };
    }
    if (this.driver.pause === void 0) {
      this.driver.pause = () => {
      };
    }
    if (this.driver.seek === void 0) {
      this.driver.seek = (where) => false;
    }
    if (this.driver.step === void 0) {
      this.driver.step = (n2) => {
      };
    }
    if (this.driver.stop === void 0) {
      this.driver.stop = () => {
      };
    }
    if (this.driver.restart === void 0) {
      this.driver.restart = () => {
      };
    }
    if (this.driver.mute === void 0) {
      this.driver.mute = () => {
      };
    }
    if (this.driver.unmute === void 0) {
      this.driver.unmute = () => {
      };
    }
    if (this.driver.getCurrentTime === void 0) {
      const play = this.driver.play;
      let clock2 = new NullClock();
      this.driver.play = () => {
        clock2 = new Clock(this.speed);
        return play();
      };
      this.driver.getCurrentTime = () => clock2.getTime();
    }
    this._dispatchEvent("ready", config2);
    if (this.autoPlay) {
      this.play();
    } else if (this.poster.type === "text") {
      this._feed(this.poster.value);
      this.needsClear = true;
    }
  }
  play() {
    this._clearIfNeeded();
    return this._withState((state) => state.play());
  }
  pause() {
    return this._withState((state) => state.pause());
  }
  togglePlay() {
    this._clearIfNeeded();
    return this._withState((state) => state.togglePlay());
  }
  seek(where) {
    this._clearIfNeeded();
    return this._withState(async (state) => {
      if (await state.seek(where)) {
        this._dispatchEvent("seeked");
      }
    });
  }
  step(n2) {
    this._clearIfNeeded();
    return this._withState((state) => state.step(n2));
  }
  stop() {
    return this._withState((state) => state.stop());
  }
  mute() {
    return this._withState((state) => state.mute());
  }
  unmute() {
    return this._withState((state) => state.unmute());
  }
  getLine(n2, cursorOn) {
    return this.vt.getLine(n2, cursorOn);
  }
  getDataView(_ref5, size) {
    let [ptr, len] = _ref5;
    return new DataView(this.memory.buffer, ptr, len * size);
  }
  getUint32Array(_ref6) {
    let [ptr, len] = _ref6;
    return new Uint32Array(this.memory.buffer, ptr, len);
  }
  getCursor() {
    const cursor = this.vt.getCursor();
    if (cursor) {
      return {
        col: cursor[0],
        row: cursor[1],
        visible: true
      };
    }
    return {
      col: 0,
      row: 0,
      visible: false
    };
  }
  getCurrentTime() {
    return this.driver.getCurrentTime();
  }
  getRemainingTime() {
    if (typeof this.duration === "number") {
      return this.duration - Math.min(this.getCurrentTime(), this.duration);
    }
  }
  getProgress() {
    if (typeof this.duration === "number") {
      return Math.min(this.getCurrentTime(), this.duration) / this.duration;
    }
  }
  getDuration() {
    return this.duration;
  }
  addEventListener(eventName, handler) {
    this.eventHandlers.get(eventName).push(handler);
  }
  removeEventListener(eventName, handler) {
    const handlers = this.eventHandlers.get(eventName);
    if (!handlers) return;
    const idx = handlers.indexOf(handler);
    if (idx !== -1) handlers.splice(idx, 1);
  }
  _dispatchEvent(eventName) {
    let data = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {};
    for (const h of this.eventHandlers.get(eventName)) {
      h(data);
    }
  }
  _withState(f) {
    return this._enqueueCommand(() => f(this.state));
  }
  _enqueueCommand(f) {
    this.commandQueue = this.commandQueue.then(f);
    return this.commandQueue;
  }
  _setState(newState) {
    let data = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {};
    if (this.stateName === newState) return this.state;
    this.stateName = newState;
    if (newState === "playing") {
      this.state = new PlayingState(this);
    } else if (newState === "idle") {
      this.state = new Idle(this);
    } else if (newState === "loading") {
      this.state = new LoadingState(this);
    } else if (newState === "ended") {
      this.state = new EndedState(this);
    } else if (newState === "offline") {
      this.state = new OfflineState(this);
    } else if (newState === "errored") {
      this.state = new ErroredState(this);
    } else {
      throw new Error(`invalid state: ${newState}`);
    }
    this.state.onEnter(data);
    return this.state;
  }
  _feed(data) {
    const changedRows = this.vt.feed(data);
    this._dispatchEvent("vtUpdate", {
      changedRows
    });
  }
  async _initializeDriver() {
    const meta = await this.driver.init();
    this.cols = this.cols ?? meta.cols ?? DEFAULT_COLS;
    this.rows = this.rows ?? meta.rows ?? DEFAULT_ROWS;
    this.duration = this.duration ?? meta.duration;
    this.markers = this._normalizeMarkers(meta.markers) ?? this.markers ?? [];
    if (this.cols === 0) {
      this.cols = DEFAULT_COLS;
    }
    if (this.rows === 0) {
      this.rows = DEFAULT_ROWS;
    }
    this._initializeVt(this.cols, this.rows);
    if (meta.poster !== void 0) {
      meta.poster.forEach((text2) => this.vt.feed(text2));
      this.needsClear = true;
    } else if (this.poster.type === "text") {
      this.vt.feed(this.poster.value);
      this.needsClear = true;
    }
    this._dispatchEvent("metadata", {
      size: {
        cols: this.cols,
        rows: this.rows
      },
      theme: meta.theme ?? null,
      duration: this.duration,
      markers: this.markers,
      hasAudio: meta.hasAudio
    });
    this._dispatchEvent("vtUpdate", {
      size: {
        cols: this.cols,
        rows: this.rows
      },
      theme: meta.theme ?? null,
      changedRows: Array.from({
        length: this.rows
      }, (_, i2) => i2)
    });
  }
  _clearIfNeeded() {
    if (this.needsClear) {
      this._feed("\x1Bc");
      this.needsClear = false;
    }
  }
  _resetVt(cols, rows) {
    let init2 = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : void 0;
    let theme = arguments.length > 3 && arguments[3] !== void 0 ? arguments[3] : void 0;
    this.logger.debug(`core: vt reset (${cols}x${rows})`);
    this.cols = cols;
    this.rows = rows;
    this._initializeVt(cols, rows);
    if (init2 !== void 0 && init2 !== "") {
      this.vt.feed(init2);
    }
    this._dispatchEvent("metadata", {
      size: {
        cols,
        rows
      },
      theme: theme ?? null
    });
    this._dispatchEvent("vtUpdate", {
      size: {
        cols,
        rows
      },
      theme: theme ?? null,
      changedRows: Array.from({
        length: rows
      }, (_, i2) => i2)
    });
  }
  _resizeVt(cols, rows) {
    if (cols === this.vt.cols && rows === this.vt.rows) return;
    const changedRows = this.vt.resize(cols, rows);
    this.vt.cols = cols;
    this.vt.rows = rows;
    this.logger.debug(`core: vt resize (${cols}x${rows})`);
    this._dispatchEvent("metadata", {
      size: {
        cols,
        rows
      }
    });
    this._dispatchEvent("vtUpdate", {
      size: {
        cols,
        rows
      },
      changedRows
    });
  }
  _initializeVt(cols, rows) {
    this.logger.debug("vt init", {
      cols,
      rows
    });
    this.vt = this.wasm.create(cols, rows, 100, this.boldIsBright);
    this.vt.cols = cols;
    this.vt.rows = rows;
  }
  _parsePoster(poster) {
    if (typeof poster !== "string") return {};
    if (poster.substring(0, 16) == "data:text/plain,") {
      return {
        type: "text",
        value: poster.substring(16)
      };
    } else if (poster.substring(0, 4) == "npt:") {
      return {
        type: "npt",
        value: parseNpt(poster.substring(4))
      };
    }
    return {};
  }
  _normalizeMarkers(markers) {
    if (Array.isArray(markers)) {
      return markers.map((m) => typeof m === "number" ? [m, ""] : m);
    }
  }
}
const DRIVERS = /* @__PURE__ */ new Map([["benchmark", benchmark], ["clock", clock], ["eventsource", eventsource], ["random", random], ["recording", recording], ["websocket", websocket]]);
const PARSERS = /* @__PURE__ */ new Map([["asciicast", parse$2], ["typescript", parse$1], ["ttyrec", parse]]);
function getDriver(src) {
  if (typeof src === "function") return src;
  if (typeof src === "string") {
    if (src.substring(0, 5) == "ws://" || src.substring(0, 6) == "wss://") {
      src = {
        driver: "websocket",
        url: src
      };
    } else if (src.substring(0, 6) == "clock:") {
      src = {
        driver: "clock"
      };
    } else if (src.substring(0, 7) == "random:") {
      src = {
        driver: "random"
      };
    } else if (src.substring(0, 10) == "benchmark:") {
      src = {
        driver: "benchmark",
        url: src.substring(10)
      };
    } else {
      src = {
        driver: "recording",
        url: src
      };
    }
  }
  if (src.driver === void 0) {
    src.driver = "recording";
  }
  if (src.driver == "recording") {
    if (src.parser === void 0) {
      src.parser = "asciicast";
    }
    if (typeof src.parser === "string") {
      if (PARSERS.has(src.parser)) {
        src.parser = PARSERS.get(src.parser);
      } else {
        throw new Error(`unknown parser: ${src.parser}`);
      }
    }
  }
  if (DRIVERS.has(src.driver)) {
    const driver = DRIVERS.get(src.driver);
    return (callbacks, opts) => driver(src, callbacks, opts);
  } else {
    throw new Error(`unsupported driver: ${JSON.stringify(src)}`);
  }
}
const IS_DEV = false;
const equalFn = (a2, b) => a2 === b;
const $PROXY = /* @__PURE__ */ Symbol("solid-proxy");
const $TRACK = /* @__PURE__ */ Symbol("solid-track");
const signalOptions = {
  equals: equalFn
};
let runEffects = runQueue;
const STALE = 1;
const PENDING = 2;
const UNOWNED = {
  owned: null,
  cleanups: null,
  context: null,
  owner: null
};
var Owner = null;
let Transition$1 = null;
let ExternalSourceConfig = null;
let Listener = null;
let Updates = null;
let Effects = null;
let ExecCount = 0;
function createRoot(fn2, detachedOwner) {
  const listener = Listener, owner = Owner, unowned = fn2.length === 0, current = detachedOwner === void 0 ? owner : detachedOwner, root2 = unowned ? UNOWNED : {
    owned: null,
    cleanups: null,
    context: current ? current.context : null,
    owner: current
  }, updateFn = unowned ? fn2 : () => fn2(() => untrack(() => cleanNode(root2)));
  Owner = root2;
  Listener = null;
  try {
    return runUpdates(updateFn, true);
  } finally {
    Listener = listener;
    Owner = owner;
  }
}
function createSignal(value2, options) {
  options = options ? Object.assign({}, signalOptions, options) : signalOptions;
  const s = {
    value: value2,
    observers: null,
    observerSlots: null,
    comparator: options.equals || void 0
  };
  const setter = (value3) => {
    if (typeof value3 === "function") {
      value3 = value3(s.value);
    }
    return writeSignal(s, value3);
  };
  return [readSignal.bind(s), setter];
}
function createComputed(fn2, value2, options) {
  const c = createComputation(fn2, value2, true, STALE);
  updateComputation(c);
}
function createRenderEffect(fn2, value2, options) {
  const c = createComputation(fn2, value2, false, STALE);
  updateComputation(c);
}
function createEffect(fn2, value2, options) {
  runEffects = runUserEffects;
  const c = createComputation(fn2, value2, false, STALE);
  c.user = true;
  Effects ? Effects.push(c) : updateComputation(c);
}
function createMemo(fn2, value2, options) {
  options = options ? Object.assign({}, signalOptions, options) : signalOptions;
  const c = createComputation(fn2, value2, true, 0);
  c.observers = null;
  c.observerSlots = null;
  c.comparator = options.equals || void 0;
  updateComputation(c);
  return readSignal.bind(c);
}
function batch(fn2) {
  return runUpdates(fn2, false);
}
function untrack(fn2) {
  if (Listener === null) return fn2();
  const listener = Listener;
  Listener = null;
  try {
    if (ExternalSourceConfig) ;
    return fn2();
  } finally {
    Listener = listener;
  }
}
function onMount(fn2) {
  createEffect(() => untrack(fn2));
}
function onCleanup(fn2) {
  if (Owner === null) ;
  else if (Owner.cleanups === null) Owner.cleanups = [fn2];
  else Owner.cleanups.push(fn2);
  return fn2;
}
function getListener() {
  return Listener;
}
function startTransition(fn2) {
  const l2 = Listener;
  const o = Owner;
  return Promise.resolve().then(() => {
    Listener = l2;
    Owner = o;
    let t2;
    runUpdates(fn2, false);
    Listener = Owner = null;
    return t2 ? t2.done : void 0;
  });
}
const [transPending] = /* @__PURE__ */ createSignal(false);
function useTransition() {
  return [transPending, startTransition];
}
function children(fn2) {
  const children2 = createMemo(fn2);
  const memo = createMemo(() => resolveChildren(children2()));
  memo.toArray = () => {
    const c = memo();
    return Array.isArray(c) ? c : c != null ? [c] : [];
  };
  return memo;
}
function readSignal() {
  if (this.sources && this.state) {
    if (this.state === STALE) updateComputation(this);
    else {
      const updates = Updates;
      Updates = null;
      runUpdates(() => lookUpstream(this), false);
      Updates = updates;
    }
  }
  if (Listener) {
    const sSlot = this.observers ? this.observers.length : 0;
    if (!Listener.sources) {
      Listener.sources = [this];
      Listener.sourceSlots = [sSlot];
    } else {
      Listener.sources.push(this);
      Listener.sourceSlots.push(sSlot);
    }
    if (!this.observers) {
      this.observers = [Listener];
      this.observerSlots = [Listener.sources.length - 1];
    } else {
      this.observers.push(Listener);
      this.observerSlots.push(Listener.sources.length - 1);
    }
  }
  return this.value;
}
function writeSignal(node2, value2, isComp) {
  let current = node2.value;
  if (!node2.comparator || !node2.comparator(current, value2)) {
    node2.value = value2;
    if (node2.observers && node2.observers.length) {
      runUpdates(() => {
        for (let i2 = 0; i2 < node2.observers.length; i2 += 1) {
          const o = node2.observers[i2];
          const TransitionRunning = Transition$1 && Transition$1.running;
          if (TransitionRunning && Transition$1.disposed.has(o)) ;
          if (TransitionRunning ? !o.tState : !o.state) {
            if (o.pure) Updates.push(o);
            else Effects.push(o);
            if (o.observers) markDownstream(o);
          }
          if (!TransitionRunning) o.state = STALE;
        }
        if (Updates.length > 1e6) {
          Updates = [];
          if (IS_DEV) ;
          throw new Error();
        }
      }, false);
    }
  }
  return value2;
}
function updateComputation(node2) {
  if (!node2.fn) return;
  cleanNode(node2);
  const time = ExecCount;
  runComputation(
    node2,
    node2.value,
    time
  );
}
function runComputation(node2, value2, time) {
  let nextValue;
  const owner = Owner, listener = Listener;
  Listener = Owner = node2;
  try {
    nextValue = node2.fn(value2);
  } catch (err) {
    if (node2.pure) {
      {
        node2.state = STALE;
        node2.owned && node2.owned.forEach(cleanNode);
        node2.owned = null;
      }
    }
    node2.updatedAt = time + 1;
    return handleError(err);
  } finally {
    Listener = listener;
    Owner = owner;
  }
  if (!node2.updatedAt || node2.updatedAt <= time) {
    if (node2.updatedAt != null && "observers" in node2) {
      writeSignal(node2, nextValue);
    } else node2.value = nextValue;
    node2.updatedAt = time;
  }
}
function createComputation(fn2, init2, pure, state = STALE, options) {
  const c = {
    fn: fn2,
    state,
    updatedAt: null,
    owned: null,
    sources: null,
    sourceSlots: null,
    cleanups: null,
    value: init2,
    owner: Owner,
    context: Owner ? Owner.context : null,
    pure
  };
  if (Owner === null) ;
  else if (Owner !== UNOWNED) {
    {
      if (!Owner.owned) Owner.owned = [c];
      else Owner.owned.push(c);
    }
  }
  return c;
}
function runTop(node2) {
  if (node2.state === 0) return;
  if (node2.state === PENDING) return lookUpstream(node2);
  if (node2.suspense && untrack(node2.suspense.inFallback)) return node2.suspense.effects.push(node2);
  const ancestors = [node2];
  while ((node2 = node2.owner) && (!node2.updatedAt || node2.updatedAt < ExecCount)) {
    if (node2.state) ancestors.push(node2);
  }
  for (let i2 = ancestors.length - 1; i2 >= 0; i2--) {
    node2 = ancestors[i2];
    if (node2.state === STALE) {
      updateComputation(node2);
    } else if (node2.state === PENDING) {
      const updates = Updates;
      Updates = null;
      runUpdates(() => lookUpstream(node2, ancestors[0]), false);
      Updates = updates;
    }
  }
}
function runUpdates(fn2, init2) {
  if (Updates) return fn2();
  let wait = false;
  if (!init2) Updates = [];
  if (Effects) wait = true;
  else Effects = [];
  ExecCount++;
  try {
    const res = fn2();
    completeUpdates(wait);
    return res;
  } catch (err) {
    if (!wait) Effects = null;
    Updates = null;
    handleError(err);
  }
}
function completeUpdates(wait) {
  if (Updates) {
    runQueue(Updates);
    Updates = null;
  }
  if (wait) return;
  const e = Effects;
  Effects = null;
  if (e.length) runUpdates(() => runEffects(e), false);
}
function runQueue(queue) {
  for (let i2 = 0; i2 < queue.length; i2++) runTop(queue[i2]);
}
function runUserEffects(queue) {
  let i2, userLength = 0;
  for (i2 = 0; i2 < queue.length; i2++) {
    const e = queue[i2];
    if (!e.user) runTop(e);
    else queue[userLength++] = e;
  }
  for (i2 = 0; i2 < userLength; i2++) runTop(queue[i2]);
}
function lookUpstream(node2, ignore) {
  node2.state = 0;
  for (let i2 = 0; i2 < node2.sources.length; i2 += 1) {
    const source = node2.sources[i2];
    if (source.sources) {
      const state = source.state;
      if (state === STALE) {
        if (source !== ignore && (!source.updatedAt || source.updatedAt < ExecCount))
          runTop(source);
      } else if (state === PENDING) lookUpstream(source, ignore);
    }
  }
}
function markDownstream(node2) {
  for (let i2 = 0; i2 < node2.observers.length; i2 += 1) {
    const o = node2.observers[i2];
    if (!o.state) {
      o.state = PENDING;
      if (o.pure) Updates.push(o);
      else Effects.push(o);
      o.observers && markDownstream(o);
    }
  }
}
function cleanNode(node2) {
  let i2;
  if (node2.sources) {
    while (node2.sources.length) {
      const source = node2.sources.pop(), index = node2.sourceSlots.pop(), obs = source.observers;
      if (obs && obs.length) {
        const n2 = obs.pop(), s = source.observerSlots.pop();
        if (index < obs.length) {
          n2.sourceSlots[s] = index;
          obs[index] = n2;
          source.observerSlots[index] = s;
        }
      }
    }
  }
  if (node2.tOwned) {
    for (i2 = node2.tOwned.length - 1; i2 >= 0; i2--) cleanNode(node2.tOwned[i2]);
    delete node2.tOwned;
  }
  if (node2.owned) {
    for (i2 = node2.owned.length - 1; i2 >= 0; i2--) cleanNode(node2.owned[i2]);
    node2.owned = null;
  }
  if (node2.cleanups) {
    for (i2 = node2.cleanups.length - 1; i2 >= 0; i2--) node2.cleanups[i2]();
    node2.cleanups = null;
  }
  node2.state = 0;
}
function castError(err) {
  if (err instanceof Error) return err;
  return new Error(typeof err === "string" ? err : "Unknown error", {
    cause: err
  });
}
function handleError(err, owner = Owner) {
  const error2 = castError(err);
  throw error2;
}
function resolveChildren(children2) {
  if (typeof children2 === "function" && !children2.length) return resolveChildren(children2());
  if (Array.isArray(children2)) {
    const results = [];
    for (let i2 = 0; i2 < children2.length; i2++) {
      const result2 = resolveChildren(children2[i2]);
      Array.isArray(result2) ? results.push.apply(results, result2) : results.push(result2);
    }
    return results;
  }
  return children2;
}
const FALLBACK = /* @__PURE__ */ Symbol("fallback");
function dispose(d) {
  for (let i2 = 0; i2 < d.length; i2++) d[i2]();
}
function mapArray(list2, mapFn, options = {}) {
  let items = [], mapped = [], disposers = [], len = 0, indexes = mapFn.length > 1 ? [] : null;
  onCleanup(() => dispose(disposers));
  return () => {
    let newItems = list2() || [], newLen = newItems.length, i2, j;
    newItems[$TRACK];
    return untrack(() => {
      let newIndices, newIndicesNext, temp, tempdisposers, tempIndexes, start, end, newEnd, item;
      if (newLen === 0) {
        if (len !== 0) {
          dispose(disposers);
          disposers = [];
          items = [];
          mapped = [];
          len = 0;
          indexes && (indexes = []);
        }
        if (options.fallback) {
          items = [FALLBACK];
          mapped[0] = createRoot((disposer) => {
            disposers[0] = disposer;
            return options.fallback();
          });
          len = 1;
        }
      } else if (len === 0) {
        mapped = new Array(newLen);
        for (j = 0; j < newLen; j++) {
          items[j] = newItems[j];
          mapped[j] = createRoot(mapper);
        }
        len = newLen;
      } else {
        temp = new Array(newLen);
        tempdisposers = new Array(newLen);
        indexes && (tempIndexes = new Array(newLen));
        for (start = 0, end = Math.min(len, newLen); start < end && items[start] === newItems[start]; start++) ;
        for (end = len - 1, newEnd = newLen - 1; end >= start && newEnd >= start && items[end] === newItems[newEnd]; end--, newEnd--) {
          temp[newEnd] = mapped[end];
          tempdisposers[newEnd] = disposers[end];
          indexes && (tempIndexes[newEnd] = indexes[end]);
        }
        newIndices = /* @__PURE__ */ new Map();
        newIndicesNext = new Array(newEnd + 1);
        for (j = newEnd; j >= start; j--) {
          item = newItems[j];
          i2 = newIndices.get(item);
          newIndicesNext[j] = i2 === void 0 ? -1 : i2;
          newIndices.set(item, j);
        }
        for (i2 = start; i2 <= end; i2++) {
          item = items[i2];
          j = newIndices.get(item);
          if (j !== void 0 && j !== -1) {
            temp[j] = mapped[i2];
            tempdisposers[j] = disposers[i2];
            indexes && (tempIndexes[j] = indexes[i2]);
            j = newIndicesNext[j];
            newIndices.set(item, j);
          } else disposers[i2]();
        }
        for (j = start; j < newLen; j++) {
          if (j in temp) {
            mapped[j] = temp[j];
            disposers[j] = tempdisposers[j];
            if (indexes) {
              indexes[j] = tempIndexes[j];
              indexes[j](j);
            }
          } else mapped[j] = createRoot(mapper);
        }
        mapped = mapped.slice(0, len = newLen);
        items = newItems.slice(0);
      }
      return mapped;
    });
    function mapper(disposer) {
      disposers[j] = disposer;
      if (indexes) {
        const [s, set2] = createSignal(j);
        indexes[j] = set2;
        return mapFn(newItems[j], s);
      }
      return mapFn(newItems[j]);
    }
  };
}
function createComponent(Comp, props) {
  return untrack(() => Comp(props || {}));
}
const narrowedError = (name) => `Stale read from <${name}>.`;
function For(props) {
  const fallback = "fallback" in props && {
    fallback: () => props.fallback
  };
  return createMemo(mapArray(() => props.each, props.children, fallback || void 0));
}
function Show(props) {
  const keyed = props.keyed;
  const conditionValue = createMemo(() => props.when, void 0, void 0);
  const condition = keyed ? conditionValue : createMemo(conditionValue, void 0, {
    equals: (a2, b) => !a2 === !b
  });
  return createMemo(
    () => {
      const c = condition();
      if (c) {
        const child = props.children;
        const fn2 = typeof child === "function" && child.length > 0;
        return fn2 ? untrack(
          () => child(
            keyed ? c : () => {
              if (!untrack(condition)) throw narrowedError("Show");
              return conditionValue();
            }
          )
        ) : child;
      }
      return props.fallback;
    },
    void 0,
    void 0
  );
}
function Switch(props) {
  const chs = children(() => props.children);
  const switchFunc = createMemo(() => {
    const ch = chs();
    const mps = Array.isArray(ch) ? ch : [ch];
    let func = () => void 0;
    for (let i2 = 0; i2 < mps.length; i2++) {
      const index = i2;
      const mp = mps[i2];
      const prevFunc = func;
      const conditionValue = createMemo(
        () => prevFunc() ? void 0 : mp.when,
        void 0,
        void 0
      );
      const condition = mp.keyed ? conditionValue : createMemo(conditionValue, void 0, {
        equals: (a2, b) => !a2 === !b
      });
      func = () => prevFunc() || (condition() ? [index, conditionValue, mp] : void 0);
    }
    return func;
  });
  return createMemo(
    () => {
      const sel = switchFunc()();
      if (!sel) return props.fallback;
      const [index, conditionValue, mp] = sel;
      const child = mp.children;
      const fn2 = typeof child === "function" && child.length > 0;
      return fn2 ? untrack(
        () => child(
          mp.keyed ? conditionValue() : () => {
            if (untrack(switchFunc)()?.[0] !== index) throw narrowedError("Match");
            return conditionValue();
          }
        )
      ) : child;
    },
    void 0,
    void 0
  );
}
function Match(props) {
  return props;
}
function reconcileArrays(parentNode, a2, b) {
  let bLength = b.length, aEnd = a2.length, bEnd = bLength, aStart = 0, bStart = 0, after = a2[aEnd - 1].nextSibling, map2 = null;
  while (aStart < aEnd || bStart < bEnd) {
    if (a2[aStart] === b[bStart]) {
      aStart++;
      bStart++;
      continue;
    }
    while (a2[aEnd - 1] === b[bEnd - 1]) {
      aEnd--;
      bEnd--;
    }
    if (aEnd === aStart) {
      const node2 = bEnd < bLength ? bStart ? b[bStart - 1].nextSibling : b[bEnd - bStart] : after;
      while (bStart < bEnd) parentNode.insertBefore(b[bStart++], node2);
    } else if (bEnd === bStart) {
      while (aStart < aEnd) {
        if (!map2 || !map2.has(a2[aStart])) a2[aStart].remove();
        aStart++;
      }
    } else if (a2[aStart] === b[bEnd - 1] && b[bStart] === a2[aEnd - 1]) {
      const node2 = a2[--aEnd].nextSibling;
      parentNode.insertBefore(b[bStart++], a2[aStart++].nextSibling);
      parentNode.insertBefore(b[--bEnd], node2);
      a2[aEnd] = b[bEnd];
    } else {
      if (!map2) {
        map2 = /* @__PURE__ */ new Map();
        let i2 = bStart;
        while (i2 < bEnd) map2.set(b[i2], i2++);
      }
      const index = map2.get(a2[aStart]);
      if (index != null) {
        if (bStart < index && index < bEnd) {
          let i2 = aStart, sequence = 1, t2;
          while (++i2 < aEnd && i2 < bEnd) {
            if ((t2 = map2.get(a2[i2])) == null || t2 !== index + sequence) break;
            sequence++;
          }
          if (sequence > index - bStart) {
            const node2 = a2[aStart];
            while (bStart < index) parentNode.insertBefore(b[bStart++], node2);
          } else parentNode.replaceChild(b[bStart++], a2[aStart++]);
        } else aStart++;
      } else a2[aStart++].remove();
    }
  }
}
const $$EVENTS = "_$DX_DELEGATE";
function render(code2, element, init2, options = {}) {
  let disposer;
  createRoot((dispose2) => {
    disposer = dispose2;
    element === document ? code2() : insert(element, code2(), element.firstChild ? null : void 0, init2);
  }, options.owner);
  return () => {
    disposer();
    element.textContent = "";
  };
}
function template(html, isImportNode, isSVG, isMathML) {
  let node2;
  const create2 = () => {
    const t2 = document.createElement("template");
    t2.innerHTML = html;
    return t2.content.firstChild;
  };
  const fn2 = isImportNode ? () => untrack(() => document.importNode(node2 || (node2 = create2()), true)) : () => (node2 || (node2 = create2())).cloneNode(true);
  fn2.cloneNode = fn2;
  return fn2;
}
function delegateEvents(eventNames, document2 = window.document) {
  const e = document2[$$EVENTS] || (document2[$$EVENTS] = /* @__PURE__ */ new Set());
  for (let i2 = 0, l2 = eventNames.length; i2 < l2; i2++) {
    const name = eventNames[i2];
    if (!e.has(name)) {
      e.add(name);
      document2.addEventListener(name, eventHandler);
    }
  }
}
function setAttribute(node2, name, value2) {
  if (value2 == null) node2.removeAttribute(name);
  else node2.setAttribute(name, value2);
}
function className(node2, value2) {
  if (value2 == null) node2.removeAttribute("class");
  else node2.className = value2;
}
function addEventListener(node2, name, handler, delegate) {
  {
    if (Array.isArray(handler)) {
      node2[`$$${name}`] = handler[0];
      node2[`$$${name}Data`] = handler[1];
    } else node2[`$$${name}`] = handler;
  }
}
function style(node2, value2, prev) {
  if (!value2) return prev ? setAttribute(node2, "style") : value2;
  const nodeStyle = node2.style;
  if (typeof value2 === "string") return nodeStyle.cssText = value2;
  typeof prev === "string" && (nodeStyle.cssText = prev = void 0);
  prev || (prev = {});
  value2 || (value2 = {});
  let v, s;
  for (s in prev) {
    value2[s] == null && nodeStyle.removeProperty(s);
    delete prev[s];
  }
  for (s in value2) {
    v = value2[s];
    if (v !== prev[s]) {
      nodeStyle.setProperty(s, v);
      prev[s] = v;
    }
  }
  return prev;
}
function use(fn2, element, arg) {
  return untrack(() => fn2(element, arg));
}
function insert(parent, accessor, marker, initial) {
  if (marker !== void 0 && !initial) initial = [];
  if (typeof accessor !== "function") return insertExpression(parent, accessor, initial, marker);
  createRenderEffect((current) => insertExpression(parent, accessor(), current, marker), initial);
}
function eventHandler(e) {
  let node2 = e.target;
  const key2 = `$$${e.type}`;
  const oriTarget = e.target;
  const oriCurrentTarget = e.currentTarget;
  const retarget = (value2) => Object.defineProperty(e, "target", {
    configurable: true,
    value: value2
  });
  const handleNode = () => {
    const handler = node2[key2];
    if (handler && !node2.disabled) {
      const data = node2[`${key2}Data`];
      data !== void 0 ? handler.call(node2, data, e) : handler.call(node2, e);
      if (e.cancelBubble) return;
    }
    node2.host && typeof node2.host !== "string" && !node2.host._$host && node2.contains(e.target) && retarget(node2.host);
    return true;
  };
  const walkUpTree = () => {
    while (handleNode() && (node2 = node2._$host || node2.parentNode || node2.host)) ;
  };
  Object.defineProperty(e, "currentTarget", {
    configurable: true,
    get() {
      return node2 || document;
    }
  });
  if (e.composedPath) {
    const path = e.composedPath();
    retarget(path[0]);
    for (let i2 = 0; i2 < path.length - 2; i2++) {
      node2 = path[i2];
      if (!handleNode()) break;
      if (node2._$host) {
        node2 = node2._$host;
        walkUpTree();
        break;
      }
      if (node2.parentNode === oriCurrentTarget) {
        break;
      }
    }
  } else walkUpTree();
  retarget(oriTarget);
}
function insertExpression(parent, value2, current, marker, unwrapArray) {
  while (typeof current === "function") current = current();
  if (value2 === current) return current;
  const t2 = typeof value2, multi = marker !== void 0;
  parent = multi && current[0] && current[0].parentNode || parent;
  if (t2 === "string" || t2 === "number") {
    if (t2 === "number") {
      value2 = value2.toString();
      if (value2 === current) return current;
    }
    if (multi) {
      let node2 = current[0];
      if (node2 && node2.nodeType === 3) {
        node2.data !== value2 && (node2.data = value2);
      } else node2 = document.createTextNode(value2);
      current = cleanChildren(parent, current, marker, node2);
    } else {
      if (current !== "" && typeof current === "string") {
        current = parent.firstChild.data = value2;
      } else current = parent.textContent = value2;
    }
  } else if (value2 == null || t2 === "boolean") {
    current = cleanChildren(parent, current, marker);
  } else if (t2 === "function") {
    createRenderEffect(() => {
      let v = value2();
      while (typeof v === "function") v = v();
      current = insertExpression(parent, v, current, marker);
    });
    return () => current;
  } else if (Array.isArray(value2)) {
    const array = [];
    const currentArray = current && Array.isArray(current);
    if (normalizeIncomingArray(array, value2, current, unwrapArray)) {
      createRenderEffect(() => current = insertExpression(parent, array, current, marker, true));
      return () => current;
    }
    if (array.length === 0) {
      current = cleanChildren(parent, current, marker);
      if (multi) return current;
    } else if (currentArray) {
      if (current.length === 0) {
        appendNodes(parent, array, marker);
      } else reconcileArrays(parent, current, array);
    } else {
      current && cleanChildren(parent);
      appendNodes(parent, array);
    }
    current = array;
  } else if (value2.nodeType) {
    if (Array.isArray(current)) {
      if (multi) return current = cleanChildren(parent, current, marker, value2);
      cleanChildren(parent, current, null, value2);
    } else if (current == null || current === "" || !parent.firstChild) {
      parent.appendChild(value2);
    } else parent.replaceChild(value2, parent.firstChild);
    current = value2;
  } else ;
  return current;
}
function normalizeIncomingArray(normalized, array, current, unwrap2) {
  let dynamic = false;
  for (let i2 = 0, len = array.length; i2 < len; i2++) {
    let item = array[i2], prev = current && current[normalized.length], t2;
    if (item == null || item === true || item === false) ;
    else if ((t2 = typeof item) === "object" && item.nodeType) {
      normalized.push(item);
    } else if (Array.isArray(item)) {
      dynamic = normalizeIncomingArray(normalized, item, prev) || dynamic;
    } else if (t2 === "function") {
      if (unwrap2) {
        while (typeof item === "function") item = item();
        dynamic = normalizeIncomingArray(
          normalized,
          Array.isArray(item) ? item : [item],
          Array.isArray(prev) ? prev : [prev]
        ) || dynamic;
      } else {
        normalized.push(item);
        dynamic = true;
      }
    } else {
      const value2 = String(item);
      if (prev && prev.nodeType === 3 && prev.data === value2) normalized.push(prev);
      else normalized.push(document.createTextNode(value2));
    }
  }
  return dynamic;
}
function appendNodes(parent, array, marker = null) {
  for (let i2 = 0, len = array.length; i2 < len; i2++) parent.insertBefore(array[i2], marker);
}
function cleanChildren(parent, current, marker, replacement) {
  if (marker === void 0) return parent.textContent = "";
  const node2 = replacement || document.createTextNode("");
  if (current.length) {
    let inserted = false;
    for (let i2 = current.length - 1; i2 >= 0; i2--) {
      const el = current[i2];
      if (node2 !== el) {
        const isParent = el.parentNode === parent;
        if (!inserted && !i2)
          isParent ? parent.replaceChild(node2, el) : parent.insertBefore(node2, marker);
        else isParent && el.remove();
      } else inserted = true;
    }
  } else parent.insertBefore(node2, marker);
  return [node2];
}
const $RAW = /* @__PURE__ */ Symbol("store-raw"), $NODE = /* @__PURE__ */ Symbol("store-node"), $HAS = /* @__PURE__ */ Symbol("store-has"), $SELF = /* @__PURE__ */ Symbol("store-self");
function wrap$1(value2) {
  let p = value2[$PROXY];
  if (!p) {
    Object.defineProperty(value2, $PROXY, {
      value: p = new Proxy(value2, proxyTraps$1)
    });
    if (!Array.isArray(value2)) {
      const keys = Object.keys(value2), desc = Object.getOwnPropertyDescriptors(value2);
      for (let i2 = 0, l2 = keys.length; i2 < l2; i2++) {
        const prop = keys[i2];
        if (desc[prop].get) {
          Object.defineProperty(value2, prop, {
            enumerable: desc[prop].enumerable,
            get: desc[prop].get.bind(p)
          });
        }
      }
    }
  }
  return p;
}
function isWrappable(obj) {
  let proto;
  return obj != null && typeof obj === "object" && (obj[$PROXY] || !(proto = Object.getPrototypeOf(obj)) || proto === Object.prototype || Array.isArray(obj));
}
function unwrap(item, set2 = /* @__PURE__ */ new Set()) {
  let result2, unwrapped, v, prop;
  if (result2 = item != null && item[$RAW]) return result2;
  if (!isWrappable(item) || set2.has(item)) return item;
  if (Array.isArray(item)) {
    if (Object.isFrozen(item)) item = item.slice(0);
    else set2.add(item);
    for (let i2 = 0, l2 = item.length; i2 < l2; i2++) {
      v = item[i2];
      if ((unwrapped = unwrap(v, set2)) !== v) item[i2] = unwrapped;
    }
  } else {
    if (Object.isFrozen(item)) item = Object.assign({}, item);
    else set2.add(item);
    const keys = Object.keys(item), desc = Object.getOwnPropertyDescriptors(item);
    for (let i2 = 0, l2 = keys.length; i2 < l2; i2++) {
      prop = keys[i2];
      if (desc[prop].get) continue;
      v = item[prop];
      if ((unwrapped = unwrap(v, set2)) !== v) item[prop] = unwrapped;
    }
  }
  return item;
}
function getNodes(target, symbol) {
  let nodes = target[symbol];
  if (!nodes)
    Object.defineProperty(target, symbol, {
      value: nodes = /* @__PURE__ */ Object.create(null)
    });
  return nodes;
}
function getNode(nodes, property, value2) {
  if (nodes[property]) return nodes[property];
  const [s, set2] = createSignal(value2, {
    equals: false,
    internal: true
  });
  s.$ = set2;
  return nodes[property] = s;
}
function proxyDescriptor$1(target, property) {
  const desc = Reflect.getOwnPropertyDescriptor(target, property);
  if (!desc || desc.get || !desc.configurable || property === $PROXY || property === $NODE)
    return desc;
  delete desc.value;
  delete desc.writable;
  desc.get = () => target[$PROXY][property];
  return desc;
}
function trackSelf(target) {
  getListener() && getNode(getNodes(target, $NODE), $SELF)();
}
function ownKeys(target) {
  trackSelf(target);
  return Reflect.ownKeys(target);
}
const proxyTraps$1 = {
  get(target, property, receiver) {
    if (property === $RAW) return target;
    if (property === $PROXY) return receiver;
    if (property === $TRACK) {
      trackSelf(target);
      return receiver;
    }
    const nodes = getNodes(target, $NODE);
    const tracked = nodes[property];
    let value2 = tracked ? tracked() : target[property];
    if (property === $NODE || property === $HAS || property === "__proto__") return value2;
    if (!tracked) {
      const desc = Object.getOwnPropertyDescriptor(target, property);
      if (getListener() && (typeof value2 !== "function" || target.hasOwnProperty(property)) && !(desc && desc.get))
        value2 = getNode(nodes, property, value2)();
    }
    return isWrappable(value2) ? wrap$1(value2) : value2;
  },
  has(target, property) {
    if (property === $RAW || property === $PROXY || property === $TRACK || property === $NODE || property === $HAS || property === "__proto__")
      return true;
    getListener() && getNode(getNodes(target, $HAS), property)();
    return property in target;
  },
  set() {
    return true;
  },
  deleteProperty() {
    return true;
  },
  ownKeys,
  getOwnPropertyDescriptor: proxyDescriptor$1
};
function setProperty(state, property, value2, deleting = false) {
  if (!deleting && state[property] === value2) return;
  const prev = state[property], len = state.length;
  if (value2 === void 0) {
    delete state[property];
    if (state[$HAS] && state[$HAS][property] && prev !== void 0) state[$HAS][property].$();
  } else {
    state[property] = value2;
    if (state[$HAS] && state[$HAS][property] && prev === void 0) state[$HAS][property].$();
  }
  let nodes = getNodes(state, $NODE), node2;
  if (node2 = getNode(nodes, property, prev)) node2.$(() => value2);
  if (Array.isArray(state) && state.length !== len) {
    for (let i2 = state.length; i2 < len; i2++) (node2 = nodes[i2]) && node2.$();
    (node2 = getNode(nodes, "length", len)) && node2.$(state.length);
  }
  (node2 = nodes[$SELF]) && node2.$();
}
function mergeStoreNode(state, value2) {
  const keys = Object.keys(value2);
  for (let i2 = 0; i2 < keys.length; i2 += 1) {
    const key2 = keys[i2];
    setProperty(state, key2, value2[key2]);
  }
}
function updateArray(current, next) {
  if (typeof next === "function") next = next(current);
  next = unwrap(next);
  if (Array.isArray(next)) {
    if (current === next) return;
    let i2 = 0, len = next.length;
    for (; i2 < len; i2++) {
      const value2 = next[i2];
      if (current[i2] !== value2) setProperty(current, i2, value2);
    }
    setProperty(current, "length", len);
  } else mergeStoreNode(current, next);
}
function updatePath(current, path, traversed = []) {
  let part, prev = current;
  if (path.length > 1) {
    part = path.shift();
    const partType = typeof part, isArray = Array.isArray(current);
    if (Array.isArray(part)) {
      for (let i2 = 0; i2 < part.length; i2++) {
        updatePath(current, [part[i2]].concat(path), traversed);
      }
      return;
    } else if (isArray && partType === "function") {
      for (let i2 = 0; i2 < current.length; i2++) {
        if (part(current[i2], i2)) updatePath(current, [i2].concat(path), traversed);
      }
      return;
    } else if (isArray && partType === "object") {
      const { from = 0, to: to2 = current.length - 1, by = 1 } = part;
      for (let i2 = from; i2 <= to2; i2 += by) {
        updatePath(current, [i2].concat(path), traversed);
      }
      return;
    } else if (path.length > 1) {
      updatePath(current[part], path, [part].concat(traversed));
      return;
    }
    prev = current[part];
    traversed = [part].concat(traversed);
  }
  let value2 = path[0];
  if (typeof value2 === "function") {
    value2 = value2(prev, traversed);
    if (value2 === prev) return;
  }
  if (part === void 0 && value2 == void 0) return;
  value2 = unwrap(value2);
  if (part === void 0 || isWrappable(prev) && isWrappable(value2) && !Array.isArray(value2)) {
    mergeStoreNode(prev, value2);
  } else setProperty(current, part, value2);
}
function createStore(...[store, options]) {
  const unwrappedStore = unwrap(store || {});
  const isArray = Array.isArray(unwrappedStore);
  const wrappedStore = wrap$1(unwrappedStore);
  function setStore(...args2) {
    batch(() => {
      isArray && args2.length === 1 ? updateArray(unwrappedStore, args2[0]) : updatePath(unwrappedStore, args2);
    });
  }
  return [wrappedStore, setStore];
}
const noop = () => {
};
const noopTransition = (el, done) => done();
function createSwitchTransition(source, options) {
  const initSource = untrack(source);
  const initReturned = initSource ? [initSource] : [];
  const { onEnter = noopTransition, onExit = noopTransition } = options;
  const [returned, setReturned] = createSignal(options.appear ? [] : initReturned);
  const [isTransitionPending] = useTransition();
  let next;
  let isExiting = false;
  function exitTransition2(el, after) {
    if (!el)
      return after && after();
    isExiting = true;
    onExit(el, () => {
      batch(() => {
        isExiting = false;
        setReturned((p) => p.filter((e) => e !== el));
        after && after();
      });
    });
  }
  function enterTransition2(after) {
    const el = next;
    if (!el)
      return after && after();
    next = void 0;
    setReturned((p) => [el, ...p]);
    onEnter(el, after ?? noop);
  }
  const triggerTransitions = options.mode === "out-in" ? (
    // exit -> enter
    // exit -> enter
    (prev) => isExiting || exitTransition2(prev, enterTransition2)
  ) : options.mode === "in-out" ? (
    // enter -> exit
    // enter -> exit
    (prev) => enterTransition2(() => exitTransition2(prev))
  ) : (
    // exit & enter
    // exit & enter
    (prev) => {
      exitTransition2(prev);
      enterTransition2();
    }
  );
  createComputed((prev) => {
    const el = source();
    if (untrack(isTransitionPending)) {
      isTransitionPending();
      return prev;
    }
    if (el !== prev) {
      next = el;
      batch(() => untrack(() => triggerTransitions(prev)));
    }
    return el;
  }, options.appear ? void 0 : initSource);
  return returned;
}
const defaultElementPredicate = (item) => item instanceof Element;
function getFirstChild(value2, predicate) {
  if (predicate(value2))
    return value2;
  if (typeof value2 === "function" && !value2.length)
    return getFirstChild(value2(), predicate);
  if (Array.isArray(value2)) {
    for (const item of value2) {
      const result2 = getFirstChild(item, predicate);
      if (result2)
        return result2;
    }
  }
  return null;
}
function resolveFirst(fn2, predicate = defaultElementPredicate, serverPredicate = defaultElementPredicate) {
  const children2 = createMemo(fn2);
  return createMemo(() => getFirstChild(children2(), predicate));
}
function createClassnames(props) {
  return createMemo(() => {
    const name = props.name || "s";
    return {
      enterActive: (props.enterActiveClass || name + "-enter-active").split(" "),
      enter: (props.enterClass || name + "-enter").split(" "),
      enterTo: (props.enterToClass || name + "-enter-to").split(" "),
      exitActive: (props.exitActiveClass || name + "-exit-active").split(" "),
      exit: (props.exitClass || name + "-exit").split(" "),
      exitTo: (props.exitToClass || name + "-exit-to").split(" "),
      move: (props.moveClass || name + "-move").split(" ")
    };
  });
}
function nextFrame(fn2) {
  requestAnimationFrame(() => requestAnimationFrame(fn2));
}
function enterTransition(classes, events, el, done) {
  const { onBeforeEnter, onEnter, onAfterEnter } = events;
  onBeforeEnter?.(el);
  el.classList.add(...classes.enter);
  el.classList.add(...classes.enterActive);
  queueMicrotask(() => {
    if (!el.parentNode)
      return done?.();
    onEnter?.(el, () => endTransition());
  });
  nextFrame(() => {
    el.classList.remove(...classes.enter);
    el.classList.add(...classes.enterTo);
    if (!onEnter || onEnter.length < 2) {
      el.addEventListener("transitionend", endTransition);
      el.addEventListener("animationend", endTransition);
    }
  });
  function endTransition(e) {
    if (!e || e.target === el) {
      done?.();
      el.removeEventListener("transitionend", endTransition);
      el.removeEventListener("animationend", endTransition);
      el.classList.remove(...classes.enterActive);
      el.classList.remove(...classes.enterTo);
      onAfterEnter?.(el);
    }
  }
}
function exitTransition(classes, events, el, done) {
  const { onBeforeExit, onExit, onAfterExit } = events;
  if (!el.parentNode)
    return done?.();
  onBeforeExit?.(el);
  el.classList.add(...classes.exit);
  el.classList.add(...classes.exitActive);
  onExit?.(el, () => endTransition());
  nextFrame(() => {
    el.classList.remove(...classes.exit);
    el.classList.add(...classes.exitTo);
    if (!onExit || onExit.length < 2) {
      el.addEventListener("transitionend", endTransition);
      el.addEventListener("animationend", endTransition);
    }
  });
  function endTransition(e) {
    if (!e || e.target === el) {
      done?.();
      el.removeEventListener("transitionend", endTransition);
      el.removeEventListener("animationend", endTransition);
      el.classList.remove(...classes.exitActive);
      el.classList.remove(...classes.exitTo);
      onAfterExit?.(el);
    }
  }
}
var TRANSITION_MODE_MAP = {
  inout: "in-out",
  outin: "out-in"
};
var Transition = (props) => {
  const classnames = createClassnames(props);
  return createSwitchTransition(
    resolveFirst(() => props.children),
    {
      mode: TRANSITION_MODE_MAP[props.mode],
      appear: props.appear,
      onEnter(el, done) {
        enterTransition(classnames(), props, el, done);
      },
      onExit(el, done) {
        exitTransition(classnames(), props, el, done);
      }
    }
  );
};
const _tmpl$$e = /* @__PURE__ */ template(`<div class="ap-term"><canvas></canvas><svg class="ap-term-symbols" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none" width="100%" height="100%" aria-hidden="true"><defs></defs><g></g></svg><pre class="ap-term-text" aria-live="off" tabindex="0"></pre></div>`, 12);
const SVG_NS = "http://www.w3.org/2000/svg";
const BLOCK_H_RES = 8;
const BLOCK_V_RES = 24;
const BOLD_MASK = 1;
const FAINT_MASK = 1 << 1;
const ITALIC_MASK = 1 << 2;
const UNDERLINE_MASK = 1 << 3;
const STRIKETHROUGH_MASK = 1 << 4;
const BLINK_MASK = 1 << 5;
var Terminal = ((props) => {
  const core = props.core;
  const textRowPool = [];
  const vectorSymbolRowPool = [];
  const vectorSymbolUsePool = [];
  const vectorSymbolDefCache = /* @__PURE__ */ new Set();
  const colorsCache = /* @__PURE__ */ new Map();
  const attrClassCache = /* @__PURE__ */ new Map();
  const [size, setSize] = createSignal({
    cols: props.cols,
    rows: props.rows
  }, {
    equals: (newVal, oldVal) => newVal.cols === oldVal.cols && newVal.rows === oldVal.rows
  });
  const [theme, setTheme] = createSignal(buildTheme(FALLBACK_THEME));
  const lineHeight = () => props.lineHeight ?? 1.3333333333;
  const [blinkOn, setBlinkOn] = createSignal(true);
  const cursorOn = createMemo(() => blinkOn() || cursorHold);
  const style$1 = createMemo(() => {
    return {
      width: `${size().cols}ch`,
      height: `${lineHeight() * size().rows}em`,
      "font-size": `${(props.scale || 1) * 100}%`,
      "--term-line-height": `${lineHeight()}em`,
      "--term-cols": size().cols,
      "--term-rows": size().rows
    };
  });
  let cursor = {
    col: 0,
    row: 0,
    visible: false
  };
  let pendingChanges = {
    size: void 0,
    theme: void 0,
    rows: /* @__PURE__ */ new Set()
  };
  let el;
  let canvasEl;
  let canvasCtx;
  let textEl;
  let vectorSymbolsEl;
  let vectorSymbolDefsEl;
  let vectorSymbolRowsEl;
  let frameRequestId;
  let blinkIntervalId;
  let cssTheme;
  let cursorHold = false;
  onMount(() => {
    setupCanvas();
    setInitialTheme();
    adjustTextRowNodeCount(size().rows);
    adjustSymbolRowNodeCount(size().rows);
    core.addEventListener("vtUpdate", onVtUpdate);
  });
  onCleanup(() => {
    core.removeEventListener("vtUpdate", onVtUpdate);
    clearInterval(blinkIntervalId);
    cancelAnimationFrame(frameRequestId);
  });
  createEffect(() => {
    if (props.blinking && blinkIntervalId === void 0) {
      blinkIntervalId = setInterval(toggleBlink, 600);
    } else {
      clearInterval(blinkIntervalId);
      blinkIntervalId = void 0;
      setBlinkOn(true);
    }
  });
  createEffect(() => {
    cursorOn();
    if (cursor.visible) {
      pendingChanges.rows.add(cursor.row);
      scheduleRender();
    }
  });
  function setupCanvas() {
    canvasCtx = canvasEl.getContext("2d");
    if (!canvasCtx) throw new Error("2D ctx not available");
    const {
      cols,
      rows
    } = size();
    canvasEl.width = cols * BLOCK_H_RES;
    canvasEl.height = rows * BLOCK_V_RES;
    canvasEl.style.imageRendering = "pixelated";
    canvasCtx.imageSmoothingEnabled = false;
  }
  function resizeCanvas(_ref) {
    let {
      cols,
      rows
    } = _ref;
    canvasEl.width = cols * BLOCK_H_RES;
    canvasEl.height = rows * BLOCK_V_RES;
    canvasCtx.imageSmoothingEnabled = false;
  }
  function setInitialTheme() {
    cssTheme = getCssTheme(el);
    pendingChanges.theme = cssTheme;
  }
  function onVtUpdate(_ref2) {
    let {
      size: newSize,
      theme: theme2,
      changedRows
    } = _ref2;
    let activity = false;
    if (changedRows !== void 0) {
      for (const row2 of changedRows) {
        pendingChanges.rows.add(row2);
        cursorHold = true;
        activity = true;
      }
    }
    if (theme2 !== void 0 && props.preferEmbeddedTheme) {
      pendingChanges.theme = theme2;
      for (let row2 = 0; row2 < size().rows; row2++) {
        pendingChanges.rows.add(row2);
      }
    }
    const newCursor = core.getCursor();
    if (newCursor.visible != cursor.visible || newCursor.col != cursor.col || newCursor.row != cursor.row) {
      if (cursor.visible) {
        pendingChanges.rows.add(cursor.row);
      }
      if (newCursor.visible) {
        pendingChanges.rows.add(newCursor.row);
      }
      cursor = newCursor;
      cursorHold = true;
      activity = true;
    }
    if (newSize !== void 0) {
      pendingChanges.size = newSize;
      for (const row2 of pendingChanges.rows) {
        if (row2 >= newSize.rows) {
          pendingChanges.rows.delete(row2);
        }
      }
    }
    if (activity && cursor.visible) {
      pendingChanges.rows.add(cursor.row);
    }
    scheduleRender();
  }
  function toggleBlink() {
    setBlinkOn((blink) => {
      if (!blink) cursorHold = false;
      return !blink;
    });
  }
  function scheduleRender() {
    if (frameRequestId === void 0) {
      frameRequestId = requestAnimationFrame(render2);
    }
  }
  function render2() {
    frameRequestId = void 0;
    const {
      size: newSize,
      theme: newTheme,
      rows
    } = pendingChanges;
    batch(function() {
      if (newSize !== void 0) {
        resizeCanvas(newSize);
        adjustTextRowNodeCount(newSize.rows);
        adjustSymbolRowNodeCount(newSize.rows);
        setSize(newSize);
      }
      if (newTheme !== void 0) {
        if (newTheme === null) {
          setTheme(buildTheme(cssTheme));
        } else {
          setTheme(buildTheme(newTheme));
        }
        colorsCache.clear();
      }
      const theme_ = theme();
      const cursorOn_ = blinkOn() || cursorHold;
      for (const r2 of rows) {
        renderRow(r2, theme_, cursorOn_);
      }
    });
    pendingChanges.size = void 0;
    pendingChanges.theme = void 0;
    pendingChanges.rows.clear();
    props.stats.renders += 1;
  }
  function renderRow(rowIndex, theme2, cursorOn2) {
    const line = core.getLine(rowIndex, cursorOn2);
    clearCanvasRow(rowIndex);
    renderRowBg(rowIndex, line.bg, theme2);
    renderRowRasterSymbols(rowIndex, line.raster_symbols, theme2);
    renderRowVectorSymbols(rowIndex, line.vector_symbols, theme2);
    renderRowText(rowIndex, line.text, line.codepoints, theme2);
  }
  function clearCanvasRow(rowIndex) {
    canvasCtx.clearRect(0, rowIndex * BLOCK_V_RES, size().cols * BLOCK_H_RES, BLOCK_V_RES);
  }
  function renderRowBg(rowIndex, spans, theme2) {
    const view = core.getDataView(spans, 8);
    const y = rowIndex * BLOCK_V_RES;
    let i2 = 0;
    while (i2 < view.byteLength) {
      const column2 = view.getUint16(i2 + 0, true);
      const width = view.getUint16(i2 + 2, true);
      const color = getColor(view, i2 + 4, theme2);
      i2 += 8;
      canvasCtx.fillStyle = color;
      canvasCtx.fillRect(column2 * BLOCK_H_RES, y, width * BLOCK_H_RES, BLOCK_V_RES);
    }
  }
  function renderRowRasterSymbols(rowIndex, symbols, theme2) {
    const view = core.getDataView(symbols, 12);
    const y = rowIndex * BLOCK_V_RES;
    let i2 = 0;
    while (i2 < view.byteLength) {
      const column2 = view.getUint16(i2 + 0, true);
      const codepoint = view.getUint32(i2 + 4, true);
      const color = getColor(view, i2 + 8, theme2) || theme2.fg;
      i2 += 12;
      canvasCtx.fillStyle = color;
      drawBlockGlyph(canvasCtx, codepoint, column2 * BLOCK_H_RES, y);
    }
  }
  function renderRowVectorSymbols(rowIndex, symbols, theme2) {
    const view = core.getDataView(symbols, 16);
    const frag = document.createDocumentFragment();
    const symbolRow = vectorSymbolRowsEl.children[rowIndex];
    let i2 = 0;
    while (i2 < view.byteLength) {
      const column2 = view.getUint16(i2 + 0, true);
      const codepoint = view.getUint32(i2 + 4, true);
      const color = getColor(view, i2 + 8, theme2);
      const attrs = view.getUint8(i2 + 12);
      i2 += 16;
      const blink = (attrs & BLINK_MASK) !== 0;
      const el2 = createVectorSymbolNode(codepoint, column2, color, blink);
      if (el2) {
        frag.appendChild(el2);
      }
    }
    recycleVectorSymbolUses(symbolRow);
    symbolRow.replaceChildren(frag);
  }
  function renderRowText(rowIndex, spans, codepoints, theme2) {
    const spansView = core.getDataView(spans, 12);
    const codepointsView = core.getUint32Array(codepoints);
    const frag = document.createDocumentFragment();
    let i2 = 0;
    while (i2 < spansView.byteLength) {
      const column2 = spansView.getUint16(i2 + 0, true);
      const codepointsStart = spansView.getUint16(i2 + 2, true);
      const len = spansView.getUint16(i2 + 4, true);
      const color = getColor(spansView, i2 + 6, theme2);
      const attrs = spansView.getUint8(i2 + 10);
      const text2 = String.fromCodePoint(...codepointsView.subarray(codepointsStart, codepointsStart + len));
      i2 += 12;
      const el2 = document.createElement("span");
      const style2 = el2.style;
      style2.setProperty("--offset", column2);
      el2.textContent = text2;
      if (color) {
        style2.color = color;
      }
      const cls = getAttrClass(attrs);
      if (cls !== null) {
        el2.className = cls;
      }
      frag.appendChild(el2);
    }
    textEl.children[rowIndex].replaceChildren(frag);
  }
  function getAttrClass(attrs) {
    let c = attrClassCache.get(attrs);
    if (c === void 0) {
      c = buildAttrClass(attrs);
      attrClassCache.set(attrs, c);
    }
    return c;
  }
  function buildAttrClass(attrs) {
    let cls = "";
    if ((attrs & BOLD_MASK) !== 0) {
      cls += "ap-bold ";
    } else if ((attrs & FAINT_MASK) !== 0) {
      cls += "ap-faint ";
    }
    if ((attrs & ITALIC_MASK) !== 0) {
      cls += "ap-italic ";
    }
    if ((attrs & UNDERLINE_MASK) !== 0) {
      cls += "ap-underline ";
    }
    if ((attrs & STRIKETHROUGH_MASK) !== 0) {
      cls += "ap-strike ";
    }
    if ((attrs & BLINK_MASK) !== 0) {
      cls += "ap-blink ";
    }
    return cls === "" ? null : cls;
  }
  function getColor(view, offset, theme2) {
    const tag = view.getUint8(offset);
    if (tag === 0) {
      return null;
    } else if (tag === 1) {
      return theme2.fg;
    } else if (tag === 2) {
      return theme2.bg;
    } else if (tag === 3) {
      return theme2.palette[view.getUint8(offset + 1)];
    } else if (tag === 4) {
      const key2 = view.getUint32(offset, true);
      let c = colorsCache.get(key2);
      if (c === void 0) {
        const r2 = view.getUint8(offset + 1);
        const g = view.getUint8(offset + 2);
        const b = view.getUint8(offset + 3);
        c = "rgb(" + r2 + "," + g + "," + b + ")";
        colorsCache.set(key2, c);
      }
      return c;
    } else {
      throw new Error(`invalid color tag: ${tag}`);
    }
  }
  function adjustTextRowNodeCount(rows) {
    let r2 = textEl.children.length;
    if (r2 < rows) {
      const frag = document.createDocumentFragment();
      while (r2 < rows) {
        const row2 = getNewRow();
        row2.style.setProperty("--row", r2);
        frag.appendChild(row2);
        r2 += 1;
      }
      textEl.appendChild(frag);
    }
    while (textEl.children.length > rows) {
      const row2 = textEl.lastElementChild;
      textEl.removeChild(row2);
      textRowPool.push(row2);
    }
  }
  function adjustSymbolRowNodeCount(rows) {
    let r2 = vectorSymbolRowsEl.children.length;
    if (r2 < rows) {
      const frag = document.createDocumentFragment();
      while (r2 < rows) {
        const row2 = getNewSymbolRow();
        row2.setAttribute("transform", `translate(0 ${r2})`);
        frag.appendChild(row2);
        r2 += 1;
      }
      vectorSymbolRowsEl.appendChild(frag);
    }
    while (vectorSymbolRowsEl.children.length > rows) {
      const row2 = vectorSymbolRowsEl.lastElementChild;
      vectorSymbolRowsEl.removeChild(row2);
      vectorSymbolRowPool.push(row2);
    }
  }
  function getNewRow() {
    let row2 = textRowPool.pop();
    if (row2 === void 0) {
      row2 = document.createElement("span");
      row2.className = "ap-line";
    }
    return row2;
  }
  function getNewSymbolRow() {
    let row2 = vectorSymbolRowPool.pop();
    if (row2 === void 0) {
      row2 = document.createElementNS(SVG_NS, "g");
      row2.setAttribute("class", "ap-symbol-line");
    }
    return row2;
  }
  function createVectorSymbolNode(codepoint, column2, fg, blink) {
    if (!ensureVectorSymbolDef(codepoint)) {
      return null;
    }
    const isPowerline = POWERLINE_SYMBOLS.has(codepoint);
    const symbolX = isPowerline ? column2 - POWERLINE_SYMBOL_NUDGE : column2;
    const symbolWidth = isPowerline ? 1 + POWERLINE_SYMBOL_NUDGE * 2 : 1;
    const node2 = getVectorSymbolUse();
    node2.setAttribute("href", `#sym-${codepoint}`);
    node2.setAttribute("x", symbolX);
    node2.setAttribute("y", 0);
    node2.setAttribute("width", symbolWidth);
    node2.setAttribute("height", "1");
    if (fg) {
      node2.style.setProperty("color", fg);
    } else {
      node2.style.removeProperty("color");
    }
    if (blink) {
      node2.classList.add("ap-blink");
    } else {
      node2.classList.remove("ap-blink");
    }
    return node2;
  }
  function recycleVectorSymbolUses(row2) {
    while (row2.firstChild) {
      const child = row2.firstChild;
      row2.removeChild(child);
      vectorSymbolUsePool.push(child);
    }
  }
  function getVectorSymbolUse() {
    let node2 = vectorSymbolUsePool.pop();
    if (node2 === void 0) {
      node2 = document.createElementNS(SVG_NS, "use");
    }
    return node2;
  }
  function ensureVectorSymbolDef(codepoint) {
    const content2 = getVectorSymbolDef(codepoint);
    if (!content2) {
      return false;
    }
    if (vectorSymbolDefCache.has(codepoint)) {
      return true;
    }
    const id = `sym-${codepoint}`;
    const symbol = document.createElementNS(SVG_NS, "symbol");
    symbol.setAttribute("id", id);
    symbol.setAttribute("viewBox", "0 0 1 1");
    symbol.setAttribute("preserveAspectRatio", "none");
    symbol.setAttribute("overflow", "visible");
    symbol.innerHTML = content2;
    vectorSymbolDefsEl.appendChild(symbol);
    vectorSymbolDefCache.add(codepoint);
    return true;
  }
  return (() => {
    const _el$ = _tmpl$$e.cloneNode(true), _el$2 = _el$.firstChild, _el$3 = _el$2.nextSibling, _el$4 = _el$3.firstChild, _el$5 = _el$4.nextSibling, _el$6 = _el$3.nextSibling;
    const _ref$ = el;
    typeof _ref$ === "function" ? use(_ref$, _el$) : el = _el$;
    const _ref$2 = canvasEl;
    typeof _ref$2 === "function" ? use(_ref$2, _el$2) : canvasEl = _el$2;
    const _ref$3 = vectorSymbolsEl;
    typeof _ref$3 === "function" ? use(_ref$3, _el$3) : vectorSymbolsEl = _el$3;
    const _ref$4 = vectorSymbolDefsEl;
    typeof _ref$4 === "function" ? use(_ref$4, _el$4) : vectorSymbolDefsEl = _el$4;
    const _ref$5 = vectorSymbolRowsEl;
    typeof _ref$5 === "function" ? use(_ref$5, _el$5) : vectorSymbolRowsEl = _el$5;
    const _ref$6 = textEl;
    typeof _ref$6 === "function" ? use(_ref$6, _el$6) : textEl = _el$6;
    createRenderEffect((_p$) => {
      const _v$ = style$1(), _v$2 = `0 0 ${size().cols} ${size().rows}`, _v$3 = !!blinkOn(), _v$4 = !!blinkOn();
      _p$._v$ = style(_el$, _v$, _p$._v$);
      _v$2 !== _p$._v$2 && setAttribute(_el$3, "viewBox", _p$._v$2 = _v$2);
      _v$3 !== _p$._v$3 && _el$3.classList.toggle("ap-blink", _p$._v$3 = _v$3);
      _v$4 !== _p$._v$4 && _el$6.classList.toggle("ap-blink", _p$._v$4 = _v$4);
      return _p$;
    }, {
      _v$: void 0,
      _v$2: void 0,
      _v$3: void 0,
      _v$4: void 0
    });
    return _el$;
  })();
});
function buildTheme(theme) {
  return {
    fg: theme.foreground,
    bg: theme.background,
    palette: [...theme.palette, ...FULL_PALETTE]
  };
}
function getCssTheme(el) {
  const style2 = getComputedStyle(el);
  const foreground = style2.getPropertyValue("--term-color-foreground");
  const background = style2.getPropertyValue("--term-color-background");
  const palette = [];
  for (let i2 = 0; i2 < 16; i2++) {
    const c = style2.getPropertyValue(`--term-color-${i2}`);
    if (c === void 0) throw new Error(`--term-color-${i2} has not been defined`);
    palette[i2] = c;
  }
  return {
    foreground,
    background,
    palette
  };
}
function drawBlockGlyph(ctx, codepoint, x2, y) {
  const unitX = BLOCK_H_RES / 8;
  const unitY = BLOCK_V_RES / 8;
  const halfX = BLOCK_H_RES / 2;
  const halfY = BLOCK_V_RES / 2;
  const sextantX = BLOCK_H_RES / 2;
  const sextantY = BLOCK_V_RES / 3;
  switch (codepoint) {
    case 9600:
      ctx.fillRect(x2, y, BLOCK_H_RES, halfY);
      break;
    case 9601:
      ctx.fillRect(x2, y + unitY * 7, BLOCK_H_RES, unitY);
      break;
    case 9602:
      ctx.fillRect(x2, y + unitY * 6, BLOCK_H_RES, unitY * 2);
      break;
    case 9603:
      ctx.fillRect(x2, y + unitY * 5, BLOCK_H_RES, unitY * 3);
      break;
    case 9604:
      ctx.fillRect(x2, y + halfY, BLOCK_H_RES, halfY);
      break;
    case 9605:
      ctx.fillRect(x2, y + unitY * 3, BLOCK_H_RES, unitY * 5);
      break;
    case 9606:
      ctx.fillRect(x2, y + unitY * 2, BLOCK_H_RES, unitY * 6);
      break;
    case 9607:
      ctx.fillRect(x2, y + unitY, BLOCK_H_RES, unitY * 7);
      break;
    case 9608:
      ctx.fillRect(x2, y, BLOCK_H_RES, BLOCK_V_RES);
      break;
    case 9632:
      ctx.fillRect(x2, y + unitY * 2, BLOCK_H_RES, unitY * 4);
      break;
    case 9609:
      ctx.fillRect(x2, y, unitX * 7, BLOCK_V_RES);
      break;
    case 9610:
      ctx.fillRect(x2, y, unitX * 6, BLOCK_V_RES);
      break;
    case 9611:
      ctx.fillRect(x2, y, unitX * 5, BLOCK_V_RES);
      break;
    case 9612:
      ctx.fillRect(x2, y, halfX, BLOCK_V_RES);
      break;
    case 9613:
      ctx.fillRect(x2, y, unitX * 3, BLOCK_V_RES);
      break;
    case 9614:
      ctx.fillRect(x2, y, unitX * 2, BLOCK_V_RES);
      break;
    case 9615:
      ctx.fillRect(x2, y, unitX, BLOCK_V_RES);
      break;
    case 9616:
      ctx.fillRect(x2 + halfX, y, halfX, BLOCK_V_RES);
      break;
    case 9617:
      ctx.save();
      ctx.globalAlpha = 0.25;
      ctx.fillRect(x2, y, BLOCK_H_RES, BLOCK_V_RES);
      ctx.restore();
      break;
    case 9618:
      ctx.save();
      ctx.globalAlpha = 0.5;
      ctx.fillRect(x2, y, BLOCK_H_RES, BLOCK_V_RES);
      ctx.restore();
      break;
    case 9619:
      ctx.save();
      ctx.globalAlpha = 0.75;
      ctx.fillRect(x2, y, BLOCK_H_RES, BLOCK_V_RES);
      ctx.restore();
      break;
    case 9620:
      ctx.fillRect(x2, y, BLOCK_H_RES, unitY);
      break;
    case 9621:
      ctx.fillRect(x2 + unitX * 7, y, unitX, BLOCK_V_RES);
      break;
    case 9622:
      ctx.fillRect(x2, y + halfY, halfX, halfY);
      break;
    case 9623:
      ctx.fillRect(x2 + halfX, y + halfY, halfX, halfY);
      break;
    case 9624:
      ctx.fillRect(x2, y, halfX, halfY);
      break;
    case 9625:
      ctx.fillRect(x2, y, halfX, BLOCK_V_RES);
      ctx.fillRect(x2 + halfX, y + halfY, halfX, halfY);
      break;
    case 9626:
      ctx.fillRect(x2, y, halfX, halfY);
      ctx.fillRect(x2 + halfX, y + halfY, halfX, halfY);
      break;
    case 9627:
      ctx.fillRect(x2, y, BLOCK_H_RES, halfY);
      ctx.fillRect(x2, y + halfY, halfX, halfY);
      break;
    case 9628:
      ctx.fillRect(x2, y, BLOCK_H_RES, halfY);
      ctx.fillRect(x2 + halfX, y + halfY, halfX, halfY);
      break;
    case 9629:
      ctx.fillRect(x2 + halfX, y, halfX, halfY);
      break;
    case 9630:
      ctx.fillRect(x2 + halfX, y, halfX, halfY);
      ctx.fillRect(x2, y + halfY, halfX, halfY);
      break;
    case 9631:
      ctx.fillRect(x2 + halfX, y, halfX, BLOCK_V_RES);
      ctx.fillRect(x2, y + halfY, halfX, halfY);
      break;
    case 129792:
      ctx.fillRect(x2, y, sextantX, sextantY);
      break;
    case 129793:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      break;
    case 129794:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      break;
    case 129795:
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY);
      break;
    case 129796:
      ctx.fillRect(x2, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY);
      break;
    case 129797:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY);
      break;
    case 129798:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY);
      break;
    case 129799:
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      break;
    case 129800:
      ctx.fillRect(x2, y, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      break;
    case 129801:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      break;
    case 129802:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      break;
    case 129803:
      ctx.fillRect(x2, y + sextantY, sextantX * 2, sextantY);
      break;
    case 129804:
      ctx.fillRect(x2, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX * 2, sextantY);
      break;
    case 129805:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX * 2, sextantY);
      break;
    case 129806:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX * 2, sextantY);
      break;
    case 129807:
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129808:
      ctx.fillRect(x2, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129809:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129810:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129811:
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY * 2);
      break;
    case 129812:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY * 2);
      break;
    case 129813:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY * 2);
      break;
    case 129814:
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129815:
      ctx.fillRect(x2, y, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129816:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY * 2);
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129817:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129818:
      ctx.fillRect(x2, y + sextantY, sextantX * 2, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129819:
      ctx.fillRect(x2, y, sextantX, sextantY * 3);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      break;
    case 129820:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX * 2, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129821:
      ctx.fillRect(x2, y, sextantX * 2, sextantY * 2);
      ctx.fillRect(x2, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129822:
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129823:
      ctx.fillRect(x2, y, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129824:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129825:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129826:
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129827:
      ctx.fillRect(x2, y, sextantX, sextantY * 2);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129828:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129829:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129830:
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY * 2);
      break;
    case 129831:
      ctx.fillRect(x2, y, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY * 2);
      break;
    case 129832:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY * 2);
      break;
    case 129833:
      ctx.fillRect(x2, y + sextantY, sextantX * 2, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129834:
      ctx.fillRect(x2, y, sextantX, sextantY * 2);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY * 2);
      break;
    case 129835:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX * 2, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129836:
      ctx.fillRect(x2, y, sextantX * 2, sextantY * 2);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129837:
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129838:
      ctx.fillRect(x2, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129839:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129840:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129841:
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129842:
      ctx.fillRect(x2, y, sextantX, sextantY * 2);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129843:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129844:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129845:
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129846:
      ctx.fillRect(x2, y, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129847:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY * 2);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129848:
      ctx.fillRect(x2, y, sextantX * 2, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY * 2, sextantX * 2, sextantY);
      break;
    case 129849:
      ctx.fillRect(x2, y + sextantY, sextantX * 2, sextantY * 2);
      break;
    case 129850:
      ctx.fillRect(x2, y, sextantX, sextantY * 3);
      ctx.fillRect(x2 + sextantX, y + sextantY, sextantX, sextantY);
      ctx.fillRect(x2 + sextantX, y + sextantY * 2, sextantX, sextantY);
      break;
    case 129851:
      ctx.fillRect(x2 + sextantX, y, sextantX, sextantY);
      ctx.fillRect(x2, y + sextantY, sextantX * 2, sextantY * 2);
      break;
  }
}
const SYMBOL_STROKE = 0.05;
const CELL_RATIO = 9.0375 / 20;
function getVectorSymbolDef(codepoint) {
  const stroke = `stroke="currentColor" stroke-width="${SYMBOL_STROKE}" stroke-linejoin="miter" stroke-linecap="square"`;
  const strokeButt = `stroke="currentColor" stroke-width="${SYMBOL_STROKE}" stroke-linejoin="miter" stroke-linecap="butt"`;
  const stroked = (d) => `<path d="${d}" fill="none" ${stroke}/>`;
  const third = 1 / 3;
  const twoThirds = 2 / 3;
  switch (codepoint) {
    // ◢ - black lower right triangle (https://symbl.cc/en/25E2/)
    case 9698:
      return '<path d="M1,1 L1,0 L0,1 Z" fill="currentColor"/>' + stroked("M1,1 L1,0 L0,1 Z");
    // ◣ - black lower left triangle (https://symbl.cc/en/25E3/)
    case 9699:
      return '<path d="M0,1 L0,0 L1,1 Z" fill="currentColor"/>' + stroked("M0,1 L0,0 L1,1 Z");
    // ◤ - black upper left triangle (https://symbl.cc/en/25E4/)
    case 9700:
      return '<path d="M0,0 L1,0 L0,1 Z" fill="currentColor"/>' + stroked("M0,0 L1,0 L0,1 Z");
    // ◥ - black upper right triangle (https://symbl.cc/en/25E5/)
    case 9701:
      return '<path d="M1,0 L1,1 L0,0 Z" fill="currentColor"/>' + stroked("M1,0 L1,1 L0,0 Z");
    case 9871: {
      const horizontalGap = 0.15;
      const verticalGap = 0.2;
      const lineHeight = 0.17;
      const halfHorizontalGap = horizontalGap / 2;
      const halfVerticalGap = verticalGap / 2;
      const toViewBoxY = (offset) => 0.5 + offset * CELL_RATIO;
      const leftX1 = 0.5 - halfHorizontalGap;
      const rightX0 = 0.5 + halfHorizontalGap;
      const rightX1 = 1 + 0.02;
      const topY0 = toViewBoxY(-halfVerticalGap - lineHeight);
      const topY1 = toViewBoxY(-halfVerticalGap);
      const bottomY0 = toViewBoxY(halfVerticalGap);
      const bottomY1 = toViewBoxY(halfVerticalGap + lineHeight);
      const rect = (x0, x1, y0, y1) => `M${x0},${y0} L${x1},${y0} L${x1},${y1} L${x0},${y1} Z`;
      return `<path d="${rect(0, leftX1, topY0, topY1)} ${rect(rightX0, rightX1, topY0, topY1)} ${rect(0, leftX1, bottomY0, bottomY1)} ${rect(rightX0, rightX1, bottomY0, bottomY1)}" fill="currentColor"/>`;
    }
    // 🬼 - lower left block diagonal lower middle left to lower centre (https://symbl.cc/en/1FB3C/)
    case 129852:
      return `<path d="M0,${twoThirds} L0,1 L0.5,1 Z" fill="currentColor"/>` + stroked(`M0,${twoThirds} L0,1 L0.5,1 Z`);
    // 🬽 - lower left block diagonal lower middle left to lower right (https://symbl.cc/en/1FB3D/)
    case 129853:
      return `<path d="M0,${twoThirds} L0,1 L1,1 Z" fill="currentColor"/>` + stroked(`M0,${twoThirds} L0,1 L1,1 Z`);
    // 🬾 - lower left block diagonal upper middle left to lower centre (https://symbl.cc/en/1FB3E/)
    case 129854:
      return `<path d="M0,${third} L0.5,1 L0,1 Z" fill="currentColor"/>` + stroked(`M0,${third} L0.5,1 L0,1 Z`);
    // 🬿 - lower left block diagonal upper middle left to lower right (https://symbl.cc/en/1FB3F/)
    case 129855:
      return `<path d="M0,${third} L1,1 L0,1 Z" fill="currentColor"/>` + stroked(`M0,${third} L1,1 L0,1 Z`);
    // 🭀 - lower left block diagonal upper left to lower centre (https://symbl.cc/en/1FB40/)
    case 129856:
      return '<path d="M0,0 L0.5,1 L0,1 Z" fill="currentColor"/>' + stroked("M0,0 L0.5,1 L0,1 Z");
    // 🭁 - lower right block diagonal upper middle left to upper centre (https://symbl.cc/en/1FB41/)
    case 129857:
      return `<path d="M0,${third} L0,1 L1,1 L1,0 L0.5,0 Z" fill="currentColor"/>` + stroked(`M0,${third} L0,1 L1,1 L1,0 L0.5,0 Z`);
    // 🭂 - lower right block diagonal upper middle left to upper right (https://symbl.cc/en/1FB42/)
    case 129858:
      return `<path d="M0,${third} L0,1 L1,1 L1,0 Z" fill="currentColor"/>` + stroked(`M0,${third} L0,1 L1,1 L1,0 Z`);
    // 🭃 - lower right block diagonal lower middle left to upper centre (https://symbl.cc/en/1FB43/)
    case 129859:
      return `<path d="M0,${twoThirds} L0,1 L1,1 L1,0 L0.5,0 Z" fill="currentColor"/>` + stroked(`M0,${twoThirds} L0,1 L1,1 L1,0 L0.5,0 Z`);
    // 🭄 - lower right block diagonal lower middle left to upper right (https://symbl.cc/en/1FB44/)
    case 129860:
      return `<path d="M0,${twoThirds} L0,1 L1,1 L1,0 Z" fill="currentColor"/>` + stroked(`M0,${twoThirds} L0,1 L1,1 L1,0 Z`);
    // 🭅 - lower right block diagonal lower left to upper centre (https://symbl.cc/en/1FB45/)
    case 129861:
      return '<path d="M0.5,0 L1,0 L1,1 L0,1 Z" fill="currentColor"/>' + stroked("M0.5,0 L1,0 L1,1 L0,1 Z");
    // 🭆 - lower right block diagonal lower middle left to upper middle right (https://symbl.cc/en/1FB46/)
    case 129862:
      return `<path d="M0,${twoThirds} L0,1 L1,1 L1,${third} Z" fill="currentColor"/>` + stroked(`M0,${twoThirds} L0,1 L1,1 L1,${third} Z`);
    // 🭇 - lower right block diagonal lower centre to lower middle right (https://symbl.cc/en/1FB47/)
    case 129863:
      return `<path d="M0.5,1 L1,1 L1,${twoThirds} Z" fill="currentColor"/>` + stroked(`M0.5,1 L1,1 L1,${twoThirds} Z`);
    // 🭈 - lower right block diagonal lower left to lower middle right (https://symbl.cc/en/1FB48/)
    case 129864:
      return `<path d="M0,1 L1,1 L1,${twoThirds} Z" fill="currentColor"/>` + stroked(`M0,1 L1,1 L1,${twoThirds} Z`);
    // 🭉 - lower right block diagonal lower centre to upper middle right (https://symbl.cc/en/1FB49/)
    case 129865:
      return `<path d="M0.5,1 L1,1 L1,${third} Z" fill="currentColor"/>` + stroked(`M0.5,1 L1,1 L1,${third} Z`);
    // 🭊 - lower right block diagonal lower left to upper middle right (https://symbl.cc/en/1FB4A/)
    case 129866:
      return `<path d="M0,1 L1,1 L1,${third} Z" fill="currentColor"/>` + stroked(`M0,1 L1,1 L1,${third} Z`);
    // 🭋 - lower right block diagonal lower centre to upper right (https://symbl.cc/en/1FB4B/)
    case 129867:
      return '<path d="M0.5,1 L1,0 L1,1 Z" fill="currentColor"/>' + stroked("M0.5,1 L1,0 L1,1 Z");
    // 🭌 - lower left block diagonal upper centre to upper middle right (https://symbl.cc/en/1FB4C/)
    case 129868:
      return `<path d="M0,0 L0.5,0 L1,${third} L1,1 L0,1 Z" fill="currentColor"/>` + stroked(`M0,0 L0.5,0 L1,${third} L1,1 L0,1 Z`);
    // 🭍 - lower left block diagonal upper left to upper middle right (https://symbl.cc/en/1FB4D/)
    case 129869:
      return `<path d="M0,0 L0,1 L1,1 L1,${third} Z" fill="currentColor"/>` + stroked(`M0,0 L0,1 L1,1 L1,${third} Z`);
    // 🭎 - lower left block diagonal upper centre to lower middle right (https://symbl.cc/en/1FB4E/)
    case 129870:
      return `<path d="M0,0 L0.5,0 L1,${twoThirds} L1,1 L0,1 Z" fill="currentColor"/>` + stroked(`M0,0 L0.5,0 L1,${twoThirds} L1,1 L0,1 Z`);
    // 🭏 - lower left block diagonal upper left to lower middle right (https://symbl.cc/en/1FB4F/)
    case 129871:
      return `<path d="M0,0 L1,${twoThirds} L1,1 L0,1 Z" fill="currentColor"/>` + stroked(`M0,0 L1,${twoThirds} L1,1 L0,1 Z`);
    // 🭐 - lower left block diagonal upper centre to lower right (https://symbl.cc/en/1FB50/)
    case 129872:
      return '<path d="M0,0 L0.5,0 L1,1 L0,1 Z" fill="currentColor"/>' + stroked("M0,0 L0.5,0 L1,1 L0,1 Z");
    // 🭑 - lower left block diagonal upper middle left to lower middle right (https://symbl.cc/en/1FB51/)
    case 129873:
      return `<path d="M0,${third} L1,${twoThirds} L1,1 L0,1 Z" fill="currentColor"/>` + stroked(`M0,${third} L1,${twoThirds} L1,1 L0,1 Z`);
    // 🭒 - upper right block diagonal lower middle left to lower centre (https://symbl.cc/en/1FB52/)
    case 129874:
      return `<path d="M0,${twoThirds} L0,0 L1,0 L1,1 L0.5,1 Z" fill="currentColor"/>` + stroked(`M0,${twoThirds} L0,0 L1,0 L1,1 L0.5,1 Z`);
    // 🭓 - upper right block diagonal lower middle left to lower right (https://symbl.cc/en/1FB53/)
    case 129875:
      return `<path d="M0,${twoThirds} L0,0 L1,0 L1,1 Z" fill="currentColor"/>` + stroked(`M0,${twoThirds} L0,0 L1,0 L1,1 Z`);
    // 🭔 - upper right block diagonal upper middle left to lower centre (https://symbl.cc/en/1FB54/)
    case 129876:
      return `<path d="M0,${third} L0,0 L1,0 L1,1 L0.5,1 Z" fill="currentColor"/>` + stroked(`M0,${third} L0,0 L1,0 L1,1 L0.5,1 Z`);
    // 🭕 - upper right block diagonal upper middle left to lower right (https://symbl.cc/en/1FB55/)
    case 129877:
      return `<path d="M0,${third} L0,0 L1,0 L1,1 Z" fill="currentColor"/>` + stroked(`M0,${third} L0,0 L1,0 L1,1 Z`);
    // 🭖 - upper right block diagonal upper left to lower centre (https://symbl.cc/en/1FB56/)
    case 129878:
      return '<path d="M0,0 L1,0 L1,1 L0.5,1 Z" fill="currentColor"/>' + stroked("M0,0 L1,0 L1,1 L0.5,1 Z");
    // 🭗 - upper left block diagonal upper middle left to upper centre (https://symbl.cc/en/1FB57/)
    case 129879:
      return `<path d="M0,${third} L0.5,0 L0,0 Z" fill="currentColor"/>` + stroked(`M0,${third} L0.5,0 L0,0 Z`);
    // 🭘 - upper left block diagonal upper middle left to upper right (https://symbl.cc/en/1FB58/)
    case 129880:
      return `<path d="M0,0 L1,0 L0,${third} Z" fill="currentColor"/>` + stroked(`M0,0 L1,0 L0,${third} Z`);
    // 🭙 - upper left block diagonal lower middle left to upper centre (https://symbl.cc/en/1FB59/)
    case 129881:
      return `<path d="M0,0 L0.5,0 L0,${twoThirds} Z" fill="currentColor"/>` + stroked(`M0,0 L0.5,0 L0,${twoThirds} Z`);
    // 🭚 - upper left block diagonal lower middle left to upper right (https://symbl.cc/en/1FB5A/)
    case 129882:
      return `<path d="M0,0 L1,0 L0,${twoThirds} Z" fill="currentColor"/>` + stroked(`M0,0 L1,0 L0,${twoThirds} Z`);
    // 🭛 - upper left block diagonal lower left to upper centre (https://symbl.cc/en/1FB5B/)
    case 129883:
      return '<path d="M0,0 L0.5,0 L0,1 Z" fill="currentColor"/>' + stroked("M0,0 L0.5,0 L0,1 Z");
    // 🭜 - upper left block diagonal lower middle left to upper middle right (https://symbl.cc/en/1FB5C/)
    case 129884:
      return `<path d="M0,0 L1,0 L1,${third} L0,${twoThirds} Z" fill="currentColor"/>` + stroked(`M0,0 L1,0 L1,${third} L0,${twoThirds} Z`);
    // 🭝 - upper left block diagonal lower centre to lower middle right (https://symbl.cc/en/1FB5D/)
    case 129885:
      return `<path d="M0,0 L1,0 L1,${twoThirds} L0.5,1 L0,1 Z" fill="currentColor"/>` + stroked(`M0,0 L1,0 L1,${twoThirds} L0.5,1 L0,1 Z`);
    // 🭞 - upper left block diagonal lower left to lower middle right (https://symbl.cc/en/1FB5E/)
    case 129886:
      return `<path d="M0,0 L1,0 L1,${twoThirds} L0,1 Z" fill="currentColor"/>` + stroked(`M0,0 L1,0 L1,${twoThirds} L0,1 Z`);
    // 🭟 - upper left block diagonal lower centre to upper middle right (https://symbl.cc/en/1FB5F/)
    case 129887:
      return `<path d="M0,0 L1,0 L1,${third} L0.5,1 L0,1 Z" fill="currentColor"/>` + stroked(`M0,0 L1,0 L1,${third} L0.5,1 L0,1 Z`);
    // 🭠 - upper left block diagonal lower left to upper middle right (https://symbl.cc/en/1FB60/)
    case 129888:
      return `<path d="M0,0 L1,0 L1,${third} L0,1 Z" fill="currentColor"/>` + stroked(`M0,0 L1,0 L1,${third} L0,1 Z`);
    // 🭡 - upper left block diagonal lower centre to upper right (https://symbl.cc/en/1FB61/)
    case 129889:
      return '<path d="M0,0 L1,0 L0.5,1 L0,1 Z" fill="currentColor"/>' + stroked("M0,0 L1,0 L0.5,1 L0,1 Z");
    // 🭢 - upper right block diagonal upper centre to upper middle right (https://symbl.cc/en/1FB62/)
    case 129890:
      return `<path d="M0.5,0 L1,0 L1,${third} Z" fill="currentColor"/>` + stroked(`M0.5,0 L1,0 L1,${third} Z`);
    // 🭣 - upper right block diagonal upper left to upper middle right (https://symbl.cc/en/1FB63/)
    case 129891:
      return `<path d="M0,0 L1,0 L1,${third} Z" fill="currentColor"/>` + stroked(`M0,0 L1,0 L1,${third} Z`);
    // 🭤 - upper right block diagonal upper centre to lower middle right (https://symbl.cc/en/1FB64/)
    case 129892:
      return `<path d="M0.5,0 L1,0 L1,${twoThirds} Z" fill="currentColor"/>` + stroked(`M0.5,0 L1,0 L1,${twoThirds} Z`);
    // 🭥 - upper right block diagonal upper left to lower middle right (https://symbl.cc/en/1FB65/)
    case 129893:
      return `<path d="M0,0 L1,0 L1,${twoThirds} Z" fill="currentColor"/>` + stroked(`M0,0 L1,0 L1,${twoThirds} Z`);
    // 🭦 - upper right block diagonal upper centre to lower right (https://symbl.cc/en/1FB66/)
    case 129894:
      return '<path d="M0.5,0 L1,0 L1,1 Z" fill="currentColor"/>' + stroked("M0.5,0 L1,0 L1,1 Z");
    // 🭧 - upper right block diagonal upper middle left to lower middle right (https://symbl.cc/en/1FB67/)
    case 129895:
      return `<path d="M0,${third} L0,0 L1,0 L1,${twoThirds} Z" fill="currentColor"/>` + stroked(`M0,${third} L0,0 L1,0 L1,${twoThirds} Z`);
    // 🭨 - upper and right and lower triangular three quarters block (https://symbl.cc/en/1FB68/)
    case 129896:
      return `<path fill-rule="evenodd" d="M0,0 L1,0 L1,1 L0,1 Z M0,0 L0,1 L0.5,0.5 Z" fill="currentColor"/><path d="M0,0 L1,0 M0,1 L1,1 M1,0 L1,1" fill="none" ${stroke}/><path d="M0,0 L0.5,0.5 M0,1 L0.5,0.5" fill="none" ${strokeButt}/>`;
    // 🭩 - left and lower and right triangular three quarters block (https://symbl.cc/en/1FB69/)
    case 129897:
      return `<path fill-rule="evenodd" d="M0,0 L1,0 L1,1 L0,1 Z M0,0 L1,0 L0.5,0.5 Z" fill="currentColor"/><path d="M0,0 L0,1 M1,0 L1,1 M0,1 L1,1" fill="none" ${stroke}/><path d="M0,0 L0.5,0.5 M1,0 L0.5,0.5" fill="none" ${strokeButt}/>`;
    // 🭪 - upper and left and lower triangular three quarters block (https://symbl.cc/en/1FB6A/)
    case 129898:
      return `<path fill-rule="evenodd" d="M0,0 L1,0 L1,1 L0,1 Z M1,0 L1,1 L0.5,0.5 Z" fill="currentColor"/><path d="M0,0 L1,0 M0,1 L1,1 M0,0 L0,1" fill="none" ${stroke}/><path d="M1,0 L0.5,0.5 M1,1 L0.5,0.5" fill="none" ${strokeButt}/>`;
    // 🭫 - left and upper and right triangular three quarters block (https://symbl.cc/en/1FB6B/)
    case 129899:
      return `<path fill-rule="evenodd" d="M0,0 L1,0 L1,1 L0,1 Z M0,1 L1,1 L0.5,0.5 Z" fill="currentColor"/><path d="M0,0 L1,0 M0,0 L0,1 M1,0 L1,1" fill="none" ${stroke}/><path d="M0,1 L0.5,0.5 M1,1 L0.5,0.5" fill="none" ${strokeButt}/>`;
    // 🭬 - left triangular one quarter block (https://symbl.cc/en/1FB6C/)
    case 129900:
      return '<path d="M0,0 L0,1 L0.5,0.5 Z" fill="currentColor"/>' + stroked("M0,0 L0,1 L0.5,0.5 Z");
    // powerline right full triangle (https://www.nerdfonts.com/cheat-sheet)
    case 57520:
      return '<path d="M0,0 L1,0.5 L0,1 Z" fill="currentColor"/>';
    // powerline right bracket (https://www.nerdfonts.com/cheat-sheet)
    case 57521:
      return '<path d="M0,0 L1,0.5 L0,1" fill="none" stroke="currentColor" stroke-width="0.07" stroke-linejoin="miter"/>';
    // powerline left full triangle (https://www.nerdfonts.com/cheat-sheet)
    case 57522:
      return '<path d="M1,0 L0,0.5 L1,1 Z" fill="currentColor"/>';
    // powerline left bracket (https://www.nerdfonts.com/cheat-sheet)
    case 57523:
      return '<path d="M1,0 L0,0.5 L1,1" fill="none" stroke="currentColor" stroke-width="0.07" stroke-linejoin="miter"/>';
    default:
      return null;
  }
}
const POWERLINE_SYMBOLS = /* @__PURE__ */ new Set([57520, 57521, 57522, 57523]);
const POWERLINE_SYMBOL_NUDGE = 0.02;
const FALLBACK_THEME = {
  foreground: "black",
  background: "black",
  palette: ["black", "black", "black", "black", "black", "black", "black", "black", "black", "black", "black", "black", "black", "black", "black", "black"]
};
const FULL_PALETTE = ["#000000", "#00005f", "#000087", "#0000af", "#0000d7", "#0000ff", "#005f00", "#005f5f", "#005f87", "#005faf", "#005fd7", "#005fff", "#008700", "#00875f", "#008787", "#0087af", "#0087d7", "#0087ff", "#00af00", "#00af5f", "#00af87", "#00afaf", "#00afd7", "#00afff", "#00d700", "#00d75f", "#00d787", "#00d7af", "#00d7d7", "#00d7ff", "#00ff00", "#00ff5f", "#00ff87", "#00ffaf", "#00ffd7", "#00ffff", "#5f0000", "#5f005f", "#5f0087", "#5f00af", "#5f00d7", "#5f00ff", "#5f5f00", "#5f5f5f", "#5f5f87", "#5f5faf", "#5f5fd7", "#5f5fff", "#5f8700", "#5f875f", "#5f8787", "#5f87af", "#5f87d7", "#5f87ff", "#5faf00", "#5faf5f", "#5faf87", "#5fafaf", "#5fafd7", "#5fafff", "#5fd700", "#5fd75f", "#5fd787", "#5fd7af", "#5fd7d7", "#5fd7ff", "#5fff00", "#5fff5f", "#5fff87", "#5fffaf", "#5fffd7", "#5fffff", "#870000", "#87005f", "#870087", "#8700af", "#8700d7", "#8700ff", "#875f00", "#875f5f", "#875f87", "#875faf", "#875fd7", "#875fff", "#878700", "#87875f", "#878787", "#8787af", "#8787d7", "#8787ff", "#87af00", "#87af5f", "#87af87", "#87afaf", "#87afd7", "#87afff", "#87d700", "#87d75f", "#87d787", "#87d7af", "#87d7d7", "#87d7ff", "#87ff00", "#87ff5f", "#87ff87", "#87ffaf", "#87ffd7", "#87ffff", "#af0000", "#af005f", "#af0087", "#af00af", "#af00d7", "#af00ff", "#af5f00", "#af5f5f", "#af5f87", "#af5faf", "#af5fd7", "#af5fff", "#af8700", "#af875f", "#af8787", "#af87af", "#af87d7", "#af87ff", "#afaf00", "#afaf5f", "#afaf87", "#afafaf", "#afafd7", "#afafff", "#afd700", "#afd75f", "#afd787", "#afd7af", "#afd7d7", "#afd7ff", "#afff00", "#afff5f", "#afff87", "#afffaf", "#afffd7", "#afffff", "#d70000", "#d7005f", "#d70087", "#d700af", "#d700d7", "#d700ff", "#d75f00", "#d75f5f", "#d75f87", "#d75faf", "#d75fd7", "#d75fff", "#d78700", "#d7875f", "#d78787", "#d787af", "#d787d7", "#d787ff", "#d7af00", "#d7af5f", "#d7af87", "#d7afaf", "#d7afd7", "#d7afff", "#d7d700", "#d7d75f", "#d7d787", "#d7d7af", "#d7d7d7", "#d7d7ff", "#d7ff00", "#d7ff5f", "#d7ff87", "#d7ffaf", "#d7ffd7", "#d7ffff", "#ff0000", "#ff005f", "#ff0087", "#ff00af", "#ff00d7", "#ff00ff", "#ff5f00", "#ff5f5f", "#ff5f87", "#ff5faf", "#ff5fd7", "#ff5fff", "#ff8700", "#ff875f", "#ff8787", "#ff87af", "#ff87d7", "#ff87ff", "#ffaf00", "#ffaf5f", "#ffaf87", "#ffafaf", "#ffafd7", "#ffafff", "#ffd700", "#ffd75f", "#ffd787", "#ffd7af", "#ffd7d7", "#ffd7ff", "#ffff00", "#ffff5f", "#ffff87", "#ffffaf", "#ffffd7", "#ffffff", "#080808", "#121212", "#1c1c1c", "#262626", "#303030", "#3a3a3a", "#444444", "#4e4e4e", "#585858", "#626262", "#6c6c6c", "#767676", "#808080", "#8a8a8a", "#949494", "#9e9e9e", "#a8a8a8", "#b2b2b2", "#bcbcbc", "#c6c6c6", "#d0d0d0", "#dadada", "#e4e4e4", "#eeeeee"];
const _tmpl$$d = /* @__PURE__ */ template(`<svg version="1.1" viewBox="0 0 12 12" class="ap-icon ap-icon-fullscreen-off"><path d="M7,5 L7,0 L9,2 L11,0 L12,1 L10,3 L12,5 Z"></path><path d="M5,7 L0,7 L2,9 L0,11 L1,12 L3,10 L5,12 Z"></path></svg>`, 6);
var ExpandIcon = ((props) => {
  return _tmpl$$d.cloneNode(true);
});
const _tmpl$$c = /* @__PURE__ */ template(`<svg version="1.1" viewBox="6 8 14 16" class="ap-icon"><path d="M0.938 8.313h22.125c0.5 0 0.938 0.438 0.938 0.938v13.5c0 0.5-0.438 0.938-0.938 0.938h-22.125c-0.5 0-0.938-0.438-0.938-0.938v-13.5c0-0.5 0.438-0.938 0.938-0.938zM1.594 22.063h20.813v-12.156h-20.813v12.156zM3.844 11.188h1.906v1.938h-1.906v-1.938zM7.469 11.188h1.906v1.938h-1.906v-1.938zM11.031 11.188h1.938v1.938h-1.938v-1.938zM14.656 11.188h1.875v1.938h-1.875v-1.938zM18.25 11.188h1.906v1.938h-1.906v-1.938zM5.656 15.031h1.938v1.938h-1.938v-1.938zM9.281 16.969v-1.938h1.906v1.938h-1.906zM12.875 16.969v-1.938h1.906v1.938h-1.906zM18.406 16.969h-1.938v-1.938h1.938v1.938zM16.531 20.781h-9.063v-1.906h9.063v1.906z"></path></svg>`, 4);
var KeyboardIcon = ((props) => {
  return _tmpl$$c.cloneNode(true);
});
const _tmpl$$b = /* @__PURE__ */ template(`<svg version="1.1" viewBox="0 0 12 12" class="ap-icon" aria-label="Pause" role="button"><path d="M1,0 L4,0 L4,12 L1,12 Z"></path><path d="M8,0 L11,0 L11,12 L8,12 Z"></path></svg>`, 6);
var PauseIcon = ((props) => {
  return _tmpl$$b.cloneNode(true);
});
const _tmpl$$a = /* @__PURE__ */ template(`<svg version="1.1" viewBox="0 0 12 12" class="ap-icon" aria-label="Play" role="button"><path d="M1,0 L11,6 L1,12 Z"></path></svg>`, 4);
var PlayIcon = ((props) => {
  return _tmpl$$a.cloneNode(true);
});
const _tmpl$$9 = /* @__PURE__ */ template(`<svg version="1.1" viewBox="0 0 12 12" class="ap-icon ap-icon-fullscreen-on"><path d="M12,0 L7,0 L9,2 L7,4 L8,5 L10,3 L12,5 Z"></path><path d="M0,12 L0,7 L2,9 L4,7 L5,8 L3,10 L5,12 Z"></path></svg>`, 6);
var ShrinkIcon = ((props) => {
  return _tmpl$$9.cloneNode(true);
});
const _tmpl$$8 = /* @__PURE__ */ template(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path d="M10.5 3.75a.75.75 0 0 0-1.264-.546L5.203 7H2.667a.75.75 0 0 0-.7.48A6.985 6.985 0 0 0 1.5 10c0 .887.165 1.737.468 2.52.111.29.39.48.7.48h2.535l4.033 3.796a.75.75 0 0 0 1.264-.546V3.75ZM16.45 5.05a.75.75 0 0 0-1.06 1.061 5.5 5.5 0 0 1 0 7.778.75.75 0 0 0 1.06 1.06 7 7 0 0 0 0-9.899Z"></path><path d="M14.329 7.172a.75.75 0 0 0-1.061 1.06 2.5 2.5 0 0 1 0 3.536.75.75 0 0 0 1.06 1.06 4 4 0 0 0 0-5.656Z"></path></svg>`, 6);
var SpeakerOnIcon = ((props) => {
  return _tmpl$$8.cloneNode(true);
});
const _tmpl$$7 = /* @__PURE__ */ template(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="size-5"><path d="M10.047 3.062a.75.75 0 0 1 .453.688v12.5a.75.75 0 0 1-1.264.546L5.203 13H2.667a.75.75 0 0 1-.7-.48A6.985 6.985 0 0 1 1.5 10c0-.887.165-1.737.468-2.52a.75.75 0 0 1 .7-.48h2.535l4.033-3.796a.75.75 0 0 1 .811-.142ZM13.78 7.22a.75.75 0 1 0-1.06 1.06L14.44 10l-1.72 1.72a.75.75 0 0 0 1.06 1.06l1.72-1.72 1.72 1.72a.75.75 0 1 0 1.06-1.06L16.56 10l1.72-1.72a.75.75 0 0 0-1.06-1.06L15.5 8.94l-1.72-1.72Z"></path></svg>`, 4);
var SpeakerOffIcon = ((props) => {
  return _tmpl$$7.cloneNode(true);
});
const _tmpl$$6 = /* @__PURE__ */ template(`<span class="ap-button ap-playback-button" tabindex="0"></span>`, 2), _tmpl$2$1 = /* @__PURE__ */ template(`<span class="ap-bar"><span class="ap-gutter ap-gutter-empty"></span><span class="ap-gutter ap-gutter-full"></span></span>`, 6), _tmpl$3$1 = /* @__PURE__ */ template(`<span class="ap-tooltip">Unmute (m)</span>`, 2), _tmpl$4$1 = /* @__PURE__ */ template(`<span class="ap-tooltip">Mute (m)</span>`, 2), _tmpl$5$1 = /* @__PURE__ */ template(`<span class="ap-button ap-speaker-button ap-tooltip-container" aria-label="Mute / unmute" role="button" tabindex="0"></span>`, 2), _tmpl$6$1 = /* @__PURE__ */ template(`<div class="ap-control-bar"><span class="ap-timer" aria-readonly="true" role="textbox" tabindex="0"><span class="ap-time-elapsed"></span><span class="ap-time-remaining"></span></span><span class="ap-progressbar"></span><span class="ap-button ap-kbd-button ap-tooltip-container" aria-label="Show keyboard shortcuts" role="button" tabindex="0"><span class="ap-tooltip">Keyboard shortcuts (?)</span></span><span class="ap-button ap-fullscreen-button ap-tooltip-container" aria-label="Toggle fullscreen mode" role="button" tabindex="0"><span class="ap-tooltip">Fullscreen (f)</span></span></div>`, 18), _tmpl$7$1 = /* @__PURE__ */ template(`<span class="ap-marker-container ap-tooltip-container"><span class="ap-marker"></span><span class="ap-tooltip"></span></span>`, 6);
function formatTime(seconds) {
  let s = Math.floor(seconds);
  const d = Math.floor(s / 86400);
  s %= 86400;
  const h = Math.floor(s / 3600);
  s %= 3600;
  const m = Math.floor(s / 60);
  s %= 60;
  if (d > 0) {
    return `${zeroPad(d)}:${zeroPad(h)}:${zeroPad(m)}:${zeroPad(s)}`;
  } else if (h > 0) {
    return `${zeroPad(h)}:${zeroPad(m)}:${zeroPad(s)}`;
  } else {
    return `${zeroPad(m)}:${zeroPad(s)}`;
  }
}
function zeroPad(n2) {
  return n2 < 10 ? `0${n2}` : n2.toString();
}
var ControlBar = ((props) => {
  const e = (f) => {
    return (e2) => {
      e2.preventDefault();
      f(e2);
    };
  };
  const currentTime = () => typeof props.currentTime === "number" ? formatTime(props.currentTime) : "--:--";
  const remainingTime = () => typeof props.remainingTime === "number" ? "-" + formatTime(props.remainingTime) : currentTime();
  const markers = createMemo(() => typeof props.duration === "number" ? props.markers.filter((m) => m[0] < props.duration) : []);
  const markerPosition = (m) => `${m[0] / props.duration * 100}%`;
  const markerText = (m) => {
    if (m[1] === "") {
      return formatTime(m[0]);
    } else {
      return `${formatTime(m[0])} - ${m[1]}`;
    }
  };
  const isPastMarker = (m) => typeof props.currentTime === "number" ? m[0] <= props.currentTime : false;
  const gutterBarStyle = () => {
    return {
      transform: `scaleX(${props.progress || 0}`
    };
  };
  const calcPosition = (e2) => {
    const barWidth = e2.currentTarget.offsetWidth;
    const rect = e2.currentTarget.getBoundingClientRect();
    const mouseX = e2.clientX - rect.left;
    const pos = Math.max(0, mouseX / barWidth);
    return `${pos * 100}%`;
  };
  const [mouseDown, setMouseDown] = createSignal(false);
  const throttledSeek = throttle(props.onSeekClick, 50);
  const onMouseDown = (e2) => {
    if (e2._marker) return;
    if (e2.altKey || e2.shiftKey || e2.metaKey || e2.ctrlKey || e2.button !== 0) return;
    setMouseDown(true);
    props.onSeekClick(calcPosition(e2));
  };
  const seekToMarker = (index) => {
    return e(() => {
      props.onSeekClick({
        marker: index
      });
    });
  };
  const onMove = (e2) => {
    if (e2.altKey || e2.shiftKey || e2.metaKey || e2.ctrlKey) return;
    if (mouseDown()) {
      throttledSeek(calcPosition(e2));
    }
  };
  const onDocumentMouseUp = () => {
    setMouseDown(false);
  };
  document.addEventListener("mouseup", onDocumentMouseUp);
  onCleanup(() => {
    document.removeEventListener("mouseup", onDocumentMouseUp);
  });
  return (() => {
    const _el$ = _tmpl$6$1.cloneNode(true), _el$3 = _el$.firstChild, _el$4 = _el$3.firstChild, _el$5 = _el$4.nextSibling, _el$6 = _el$3.nextSibling, _el$13 = _el$6.nextSibling, _el$14 = _el$13.firstChild, _el$15 = _el$13.nextSibling, _el$16 = _el$15.firstChild;
    const _ref$ = props.ref;
    typeof _ref$ === "function" ? use(_ref$, _el$) : props.ref = _el$;
    insert(_el$, createComponent(Show, {
      get when() {
        return props.isPausable;
      },
      get children() {
        const _el$2 = _tmpl$$6.cloneNode(true);
        addEventListener(_el$2, "click", e(props.onPlayClick));
        insert(_el$2, createComponent(Switch, {
          get children() {
            return [createComponent(Match, {
              get when() {
                return props.isPlaying;
              },
              get children() {
                return createComponent(PauseIcon, {});
              }
            }), createComponent(Match, {
              when: true,
              get children() {
                return createComponent(PlayIcon, {});
              }
            })];
          }
        }));
        return _el$2;
      }
    }), _el$3);
    insert(_el$4, currentTime);
    insert(_el$5, remainingTime);
    insert(_el$6, createComponent(Show, {
      get when() {
        return typeof props.progress === "number" || props.isSeekable;
      },
      get children() {
        const _el$7 = _tmpl$2$1.cloneNode(true), _el$8 = _el$7.firstChild, _el$9 = _el$8.nextSibling;
        _el$7.$$mousemove = onMove;
        _el$7.$$mousedown = onMouseDown;
        insert(_el$7, createComponent(For, {
          get each() {
            return markers();
          },
          children: (m, i2) => (() => {
            const _el$17 = _tmpl$7$1.cloneNode(true), _el$18 = _el$17.firstChild, _el$19 = _el$18.nextSibling;
            _el$17.$$mousedown = (e2) => {
              e2._marker = true;
            };
            addEventListener(_el$17, "click", seekToMarker(i2()));
            insert(_el$19, () => markerText(m));
            createRenderEffect((_p$) => {
              const _v$ = markerPosition(m), _v$2 = !!isPastMarker(m);
              _v$ !== _p$._v$ && _el$17.style.setProperty("left", _p$._v$ = _v$);
              _v$2 !== _p$._v$2 && _el$18.classList.toggle("ap-marker-past", _p$._v$2 = _v$2);
              return _p$;
            }, {
              _v$: void 0,
              _v$2: void 0
            });
            return _el$17;
          })()
        }), null);
        createRenderEffect((_$p) => style(_el$9, gutterBarStyle(), _$p));
        return _el$7;
      }
    }));
    insert(_el$, createComponent(Show, {
      get when() {
        return props.isMuted !== void 0;
      },
      get children() {
        const _el$10 = _tmpl$5$1.cloneNode(true);
        addEventListener(_el$10, "click", e(props.onMuteClick));
        insert(_el$10, createComponent(Switch, {
          get children() {
            return [createComponent(Match, {
              get when() {
                return props.isMuted === true;
              },
              get children() {
                return [createComponent(SpeakerOffIcon, {}), _tmpl$3$1.cloneNode(true)];
              }
            }), createComponent(Match, {
              get when() {
                return props.isMuted === false;
              },
              get children() {
                return [createComponent(SpeakerOnIcon, {}), _tmpl$4$1.cloneNode(true)];
              }
            })];
          }
        }));
        return _el$10;
      }
    }), _el$13);
    addEventListener(_el$13, "click", e(props.onHelpClick));
    insert(_el$13, createComponent(KeyboardIcon, {}), _el$14);
    addEventListener(_el$15, "click", e(props.onFullscreenClick));
    insert(_el$15, createComponent(ShrinkIcon, {}), _el$16);
    insert(_el$15, createComponent(ExpandIcon, {}), _el$16);
    createRenderEffect(() => _el$.classList.toggle("ap-seekable", !!props.isSeekable));
    return _el$;
  })();
});
delegateEvents(["click", "mousedown", "mousemove"]);
const _tmpl$$5 = /* @__PURE__ */ template(`<div class="ap-overlay ap-overlay-error"><span>💥</span></div>`, 4);
var ErrorOverlay = ((props) => {
  return _tmpl$$5.cloneNode(true);
});
const _tmpl$$4 = /* @__PURE__ */ template(`<div class="ap-overlay ap-overlay-loading"><span class="ap-loader"></span></div>`, 4);
var LoaderOverlay = ((props) => {
  return _tmpl$$4.cloneNode(true);
});
const _tmpl$$3 = /* @__PURE__ */ template(`<div class="ap-overlay ap-overlay-info"><span></span></div>`, 4);
var InfoOverlay = ((props) => {
  return (() => {
    const _el$ = _tmpl$$3.cloneNode(true), _el$2 = _el$.firstChild;
    insert(_el$2, () => props.message);
    createRenderEffect(() => _el$.classList.toggle("ap-was-playing", !!props.wasPlaying));
    return _el$;
  })();
});
const _tmpl$$2 = /* @__PURE__ */ template(`<div class="ap-overlay ap-overlay-start"><div class="ap-play-button"><div><span><svg version="1.1" viewBox="0 0 1000.0 1000.0" class="ap-icon"><defs><mask id="small-triangle-mask"><rect width="100%" height="100%" fill="white"></rect><polygon points="700.0 500.0, 400.00000000000006 326.7949192431122, 399.9999999999999 673.2050807568877" fill="black"></polygon></mask></defs><polygon points="1000.0 500.0, 250.0000000000001 66.98729810778059, 249.99999999999977 933.0127018922192" mask="url(#small-triangle-mask)" fill="white" class="ap-play-btn-fill"></polygon><polyline points="673.2050807568878 400.0, 326.7949192431123 600.0" stroke="white" stroke-width="90" class="ap-play-btn-stroke"></polyline></svg></span></div></div></div>`, 22);
var StartOverlay = ((props) => {
  const e = (f) => {
    return (e2) => {
      e2.preventDefault();
      f(e2);
    };
  };
  return (() => {
    const _el$ = _tmpl$$2.cloneNode(true);
    addEventListener(_el$, "click", e(props.onClick));
    return _el$;
  })();
});
delegateEvents(["click"]);
const _tmpl$$1 = /* @__PURE__ */ template(`<li><kbd>space</kbd> - pause / resume</li>`, 4), _tmpl$2 = /* @__PURE__ */ template(`<li><kbd>←</kbd> / <kbd>→</kbd> - rewind / fast-forward by 5 seconds</li>`, 6), _tmpl$3 = /* @__PURE__ */ template(`<li><kbd>Shift</kbd> + <kbd>←</kbd> / <kbd>→</kbd> - rewind / fast-forward by 10%</li>`, 8), _tmpl$4 = /* @__PURE__ */ template(`<li><kbd>[</kbd> / <kbd>]</kbd> - jump to the previous / next marker</li>`, 6), _tmpl$5 = /* @__PURE__ */ template(`<li><kbd>0</kbd>, <kbd>1</kbd>, <kbd>2</kbd> ... <kbd>9</kbd> - jump to 0%, 10%, 20% ... 90%</li>`, 10), _tmpl$6 = /* @__PURE__ */ template(`<li><kbd>,</kbd> / <kbd>.</kbd> - step back / forward, a frame at a time (when paused)</li>`, 6), _tmpl$7 = /* @__PURE__ */ template(`<li><kbd>m</kbd> - mute / unmute audio</li>`, 4), _tmpl$8 = /* @__PURE__ */ template(`<div class="ap-overlay ap-overlay-help"><div><div><p>Keyboard shortcuts</p><ul><li><kbd>f</kbd> - toggle fullscreen mode</li><li><kbd>?</kbd> - show this help popup</li></ul></div></div></div>`, 18);
var HelpOverlay = ((props) => {
  const e = (f) => {
    return (e2) => {
      e2.preventDefault();
      f(e2);
    };
  };
  return (() => {
    const _el$ = _tmpl$8.cloneNode(true), _el$2 = _el$.firstChild, _el$3 = _el$2.firstChild, _el$4 = _el$3.firstChild, _el$5 = _el$4.nextSibling, _el$12 = _el$5.firstChild, _el$14 = _el$12.nextSibling;
    addEventListener(_el$, "click", e(props.onClose));
    _el$2.$$click = (e2) => {
      e2.stopPropagation();
    };
    insert(_el$5, createComponent(Show, {
      get when() {
        return props.isPausable;
      },
      get children() {
        return _tmpl$$1.cloneNode(true);
      }
    }), _el$12);
    insert(_el$5, createComponent(Show, {
      get when() {
        return props.isSeekable;
      },
      get children() {
        return [_tmpl$2.cloneNode(true), _tmpl$3.cloneNode(true), _tmpl$4.cloneNode(true), _tmpl$5.cloneNode(true), _tmpl$6.cloneNode(true)];
      }
    }), _el$12);
    insert(_el$5, createComponent(Show, {
      get when() {
        return props.hasAudio;
      },
      get children() {
        return _tmpl$7.cloneNode(true);
      }
    }), _el$14);
    return _el$;
  })();
});
delegateEvents(["click"]);
const _tmpl$ = /* @__PURE__ */ template(`<div class="ap-wrapper" tabindex="-1"><div></div></div>`, 4);
const CONTROL_BAR_HEIGHT = 32;
var Player = ((props) => {
  const logger = props.logger;
  const core = props.core;
  const autoPlay = props.autoPlay;
  const charW = props.charW;
  const charH = props.charH;
  const bordersW = props.bordersW;
  const bordersH = props.bordersH;
  const themeOption = props.theme ?? "auto/asciinema";
  const preferEmbeddedTheme = themeOption.slice(0, 5) === "auto/";
  const themeName = preferEmbeddedTheme ? themeOption.slice(5) : themeOption;
  const [state, setState] = createStore({
    containerW: 0,
    containerH: 0,
    isPausable: true,
    isSeekable: true,
    isFullscreen: false,
    currentTime: null,
    remainingTime: null,
    progress: null
  });
  const [isPlaying, setIsPlaying] = createSignal(false);
  const [isMuted, setIsMuted] = createSignal(void 0);
  const [wasPlaying, setWasPlaying] = createSignal(false);
  const [overlay, setOverlay] = createSignal(!autoPlay ? "start" : null);
  const [infoMessage, setInfoMessage] = createSignal(null);
  const [blinking, setBlinking] = createSignal(false);
  const [terminalSize, setTerminalSize] = createSignal({
    cols: props.cols,
    rows: props.rows
  }, {
    equals: (newVal, oldVal) => newVal.cols === oldVal.cols && newVal.rows === oldVal.rows
  });
  const [duration, setDuration] = createSignal(null);
  const [markers, setMarkers] = createStore([]);
  const [userActive, setUserActive] = createSignal(false);
  const [isHelpVisible, setIsHelpVisible] = createSignal(false);
  const [originalTheme, setOriginalTheme] = createSignal(null);
  const terminalCols = createMemo(() => terminalSize().cols || 80);
  const terminalRows = createMemo(() => terminalSize().rows || 24);
  const controlBarHeight = () => props.controls === false ? 0 : CONTROL_BAR_HEIGHT;
  const controlsVisible = () => props.controls === true || props.controls === "auto" && userActive();
  let userActivityTimeoutId;
  let timeUpdateIntervalId;
  let wrapperRef;
  let playerRef;
  let controlBarRef;
  let resizeObserver;
  function onPlaying() {
    setBlinking(true);
    startTimeUpdates();
  }
  function onStopped() {
    setBlinking(false);
    stopTimeUpdates();
    updateTime();
  }
  let resolveCoreReady;
  const coreReady = new Promise((resolve) => {
    resolveCoreReady = resolve;
  });
  const onCoreReady = (_ref) => {
    let {
      isPausable,
      isSeekable
    } = _ref;
    setState({
      isPausable,
      isSeekable
    });
    resolveCoreReady();
  };
  const onCoreMetadata = (meta) => {
    batch(() => {
      if (meta.duration !== void 0) {
        setDuration(meta.duration);
      }
      if (meta.markers !== void 0) {
        setMarkers(meta.markers);
      }
      if (meta.hasAudio !== void 0) {
        setIsMuted(meta.hasAudio ? false : void 0);
      }
      if (meta.size !== void 0) {
        setTerminalSize(meta.size);
      }
      if (meta.theme !== void 0) {
        setOriginalTheme(meta.theme);
      }
    });
  };
  const onCorePlay = () => {
    setOverlay(null);
  };
  const onCorePlaying = () => {
    batch(() => {
      setIsPlaying(true);
      setWasPlaying(true);
      setOverlay(null);
      onPlaying();
    });
  };
  const onCoreIdle = () => {
    batch(() => {
      setIsPlaying(false);
      onStopped();
    });
  };
  const onCoreLoading = () => {
    batch(() => {
      setIsPlaying(false);
      onStopped();
      setOverlay("loader");
    });
  };
  const onCoreOffline = (_ref2) => {
    let {
      message: message2
    } = _ref2;
    batch(() => {
      setIsPlaying(false);
      onStopped();
      if (message2 !== void 0) {
        setInfoMessage(message2);
        setOverlay("info");
      }
    });
  };
  const onCoreMuted = (muted) => {
    setIsMuted(muted);
  };
  const stats = {
    terminal: {
      renders: 0
    }
  };
  const onCoreEnded = (_ref3) => {
    let {
      message: message2
    } = _ref3;
    batch(() => {
      setIsPlaying(false);
      onStopped();
      if (message2 !== void 0) {
        setInfoMessage(message2);
        setOverlay("info");
      }
    });
    logger.debug("stats", stats.terminal);
  };
  const onCoreErrored = () => {
    setOverlay("error");
  };
  const onCoreSeeked = () => {
    updateTime();
  };
  core.addEventListener("ready", onCoreReady);
  core.addEventListener("metadata", onCoreMetadata);
  core.addEventListener("play", onCorePlay);
  core.addEventListener("playing", onCorePlaying);
  core.addEventListener("idle", onCoreIdle);
  core.addEventListener("loading", onCoreLoading);
  core.addEventListener("offline", onCoreOffline);
  core.addEventListener("muted", onCoreMuted);
  core.addEventListener("ended", onCoreEnded);
  core.addEventListener("errored", onCoreErrored);
  core.addEventListener("seeked", onCoreSeeked);
  const setupResizeObserver = () => {
    resizeObserver = new ResizeObserver(debounce((_entries) => {
      setState({
        containerW: wrapperRef.offsetWidth,
        containerH: wrapperRef.offsetHeight
      });
      wrapperRef.dispatchEvent(new CustomEvent("resize", {
        detail: {
          el: playerRef
        }
      }));
    }, 10));
    resizeObserver.observe(wrapperRef);
  };
  onMount(async () => {
    logger.info("view: mounted");
    logger.debug("view: font measurements", {
      charW,
      charH
    });
    setupResizeObserver();
    setState({
      containerW: wrapperRef.offsetWidth,
      containerH: wrapperRef.offsetHeight
    });
  });
  onCleanup(() => {
    core.removeEventListener("ready", onCoreReady);
    core.removeEventListener("metadata", onCoreMetadata);
    core.removeEventListener("play", onCorePlay);
    core.removeEventListener("playing", onCorePlaying);
    core.removeEventListener("idle", onCoreIdle);
    core.removeEventListener("loading", onCoreLoading);
    core.removeEventListener("offline", onCoreOffline);
    core.removeEventListener("muted", onCoreMuted);
    core.removeEventListener("ended", onCoreEnded);
    core.removeEventListener("errored", onCoreErrored);
    core.removeEventListener("seeked", onCoreSeeked);
    core.stop();
    stopTimeUpdates();
    resizeObserver.disconnect();
  });
  const terminalElementSize = createMemo(() => {
    const terminalW = charW * terminalCols() + bordersW;
    const terminalH = charH * terminalRows() + bordersH;
    let fit = props.fit ?? "width";
    if (fit === "both" || state.isFullscreen) {
      const containerRatio = state.containerW / (state.containerH - controlBarHeight());
      const terminalRatio = terminalW / terminalH;
      if (containerRatio > terminalRatio) {
        fit = "height";
      } else {
        fit = "width";
      }
    }
    if (fit === false || fit === "none") {
      return {};
    } else if (fit === "width") {
      const scale = state.containerW / terminalW;
      return {
        scale,
        width: state.containerW,
        height: terminalH * scale + controlBarHeight()
      };
    } else if (fit === "height") {
      const scale = (state.containerH - controlBarHeight()) / terminalH;
      return {
        scale,
        width: terminalW * scale,
        height: state.containerH
      };
    } else {
      throw new Error(`unsupported fit mode: ${fit}`);
    }
  });
  const onFullscreenChange = () => {
    setState("isFullscreen", document.fullscreenElement ?? document.webkitFullscreenElement);
  };
  const toggleFullscreen = () => {
    if (state.isFullscreen) {
      (document.exitFullscreen ?? document.webkitExitFullscreen ?? (() => {
      })).apply(document);
    } else {
      (wrapperRef.requestFullscreen ?? wrapperRef.webkitRequestFullscreen ?? (() => {
      })).apply(wrapperRef);
    }
  };
  const toggleHelp = () => {
    if (isHelpVisible()) {
      setIsHelpVisible(false);
    } else {
      core.pause();
      setIsHelpVisible(true);
    }
  };
  const onKeyDown = (e) => {
    if (e.altKey || e.metaKey || e.ctrlKey) {
      return;
    }
    if (e.key == " ") {
      core.togglePlay();
    } else if (e.key == ",") {
      core.step(-1).then(updateTime);
    } else if (e.key == ".") {
      core.step().then(updateTime);
    } else if (e.key == "f") {
      toggleFullscreen();
    } else if (e.key == "m") {
      toggleMuted();
    } else if (e.key == "[") {
      core.seek({
        marker: "prev"
      });
    } else if (e.key == "]") {
      core.seek({
        marker: "next"
      });
    } else if (e.key.charCodeAt(0) >= 48 && e.key.charCodeAt(0) <= 57) {
      const pos = (e.key.charCodeAt(0) - 48) / 10;
      core.seek(`${pos * 100}%`);
    } else if (e.key == "?") {
      toggleHelp();
    } else if (e.key == "ArrowLeft") {
      if (e.shiftKey) {
        core.seek("<<<");
      } else {
        core.seek("<<");
      }
    } else if (e.key == "ArrowRight") {
      if (e.shiftKey) {
        core.seek(">>>");
      } else {
        core.seek(">>");
      }
    } else if (e.key == "Escape") {
      setIsHelpVisible(false);
    } else {
      return;
    }
    e.stopPropagation();
    e.preventDefault();
  };
  const wrapperOnMouseMove = () => {
    if (state.isFullscreen) {
      onUserActive(true);
    }
  };
  const playerOnMouseLeave = () => {
    if (!state.isFullscreen) {
      onUserActive(false);
    }
  };
  const startTimeUpdates = () => {
    timeUpdateIntervalId = setInterval(updateTime, 100);
  };
  const stopTimeUpdates = () => {
    clearInterval(timeUpdateIntervalId);
  };
  const updateTime = async () => {
    const currentTime = await core.getCurrentTime();
    const remainingTime = await core.getRemainingTime();
    const progress2 = await core.getProgress();
    setState({
      currentTime,
      remainingTime,
      progress: progress2
    });
  };
  const onUserActive = (show) => {
    clearTimeout(userActivityTimeoutId);
    if (show) {
      userActivityTimeoutId = setTimeout(() => onUserActive(false), 2e3);
    }
    setUserActive(show);
  };
  const embeddedTheme = createMemo(() => preferEmbeddedTheme ? originalTheme() : null);
  const playerStyle = () => {
    const style2 = {};
    if ((props.fit === false || props.fit === "none") && props.terminalFontSize !== void 0) {
      if (props.terminalFontSize === "small") {
        style2["font-size"] = "12px";
      } else if (props.terminalFontSize === "medium") {
        style2["font-size"] = "18px";
      } else if (props.terminalFontSize === "big") {
        style2["font-size"] = "24px";
      } else {
        style2["font-size"] = props.terminalFontSize;
      }
    }
    const size = terminalElementSize();
    if (size.width !== void 0) {
      style2["width"] = `${size.width}px`;
      style2["height"] = `${size.height}px`;
    }
    if (props.terminalFontFamily !== void 0) {
      style2["--term-font-family"] = props.terminalFontFamily;
    }
    const themeColors = embeddedTheme();
    if (themeColors) {
      style2["--term-color-foreground"] = themeColors.foreground;
      style2["--term-color-background"] = themeColors.background;
    }
    return style2;
  };
  const play = () => {
    coreReady.then(() => core.play());
  };
  const togglePlay = () => {
    coreReady.then(() => core.togglePlay());
  };
  const toggleMuted = () => {
    coreReady.then(() => {
      if (isMuted() === true) {
        core.unmute();
      } else {
        core.mute();
      }
    });
  };
  const seek = (pos) => {
    coreReady.then(() => core.seek(pos));
  };
  const playerClass = () => `ap-player ap-default-term-ff asciinema-player-theme-${themeName}`;
  const terminalScale = () => terminalElementSize()?.scale;
  const el = (() => {
    const _el$ = _tmpl$.cloneNode(true), _el$2 = _el$.firstChild;
    const _ref$ = wrapperRef;
    typeof _ref$ === "function" ? use(_ref$, _el$) : wrapperRef = _el$;
    _el$.addEventListener("webkitfullscreenchange", onFullscreenChange);
    _el$.addEventListener("fullscreenchange", onFullscreenChange);
    _el$.$$mousemove = wrapperOnMouseMove;
    _el$.$$keydown = onKeyDown;
    const _ref$2 = playerRef;
    typeof _ref$2 === "function" ? use(_ref$2, _el$2) : playerRef = _el$2;
    _el$2.$$mousemove = () => onUserActive(true);
    _el$2.addEventListener("mouseleave", playerOnMouseLeave);
    insert(_el$2, createComponent(Terminal, {
      get cols() {
        return terminalCols();
      },
      get rows() {
        return terminalRows();
      },
      get scale() {
        return terminalScale();
      },
      get blinking() {
        return blinking();
      },
      get lineHeight() {
        return props.terminalLineHeight;
      },
      preferEmbeddedTheme,
      core,
      get stats() {
        return stats.terminal;
      }
    }), null);
    insert(_el$2, createComponent(Show, {
      get when() {
        return props.controls !== false;
      },
      get children() {
        return createComponent(ControlBar, {
          get duration() {
            return duration();
          },
          get currentTime() {
            return state.currentTime;
          },
          get remainingTime() {
            return state.remainingTime;
          },
          get progress() {
            return state.progress;
          },
          markers,
          get isPlaying() {
            return isPlaying() || overlay() == "loader";
          },
          get isPausable() {
            return state.isPausable;
          },
          get isSeekable() {
            return state.isSeekable;
          },
          get isMuted() {
            return isMuted();
          },
          onPlayClick: togglePlay,
          onFullscreenClick: toggleFullscreen,
          onHelpClick: toggleHelp,
          onSeekClick: seek,
          onMuteClick: toggleMuted,
          ref(r$) {
            const _ref$3 = controlBarRef;
            typeof _ref$3 === "function" ? _ref$3(r$) : controlBarRef = r$;
          }
        });
      }
    }), null);
    insert(_el$2, createComponent(Switch, {
      get children() {
        return [createComponent(Match, {
          get when() {
            return overlay() == "start";
          },
          get children() {
            return createComponent(StartOverlay, {
              onClick: play
            });
          }
        }), createComponent(Match, {
          get when() {
            return overlay() == "loader";
          },
          get children() {
            return createComponent(LoaderOverlay, {});
          }
        }), createComponent(Match, {
          get when() {
            return overlay() == "error";
          },
          get children() {
            return createComponent(ErrorOverlay, {});
          }
        })];
      }
    }), null);
    insert(_el$2, createComponent(Transition, {
      name: "slide",
      get children() {
        return createComponent(Show, {
          get when() {
            return overlay() == "info";
          },
          get children() {
            return createComponent(InfoOverlay, {
              get message() {
                return infoMessage();
              },
              get wasPlaying() {
                return wasPlaying();
              }
            });
          }
        });
      }
    }), null);
    insert(_el$2, createComponent(Show, {
      get when() {
        return isHelpVisible();
      },
      get children() {
        return createComponent(HelpOverlay, {
          onClose: () => setIsHelpVisible(false),
          get isPausable() {
            return state.isPausable;
          },
          get isSeekable() {
            return state.isSeekable;
          },
          get hasAudio() {
            return isMuted() !== void 0;
          }
        });
      }
    }), null);
    createRenderEffect((_p$) => {
      const _v$ = !!controlsVisible(), _v$2 = playerClass(), _v$3 = playerStyle();
      _v$ !== _p$._v$ && _el$.classList.toggle("ap-hud", _p$._v$ = _v$);
      _v$2 !== _p$._v$2 && className(_el$2, _p$._v$2 = _v$2);
      _p$._v$3 = style(_el$2, _v$3, _p$._v$3);
      return _p$;
    }, {
      _v$: void 0,
      _v$2: void 0,
      _v$3: void 0
    });
    return _el$;
  })();
  return el;
});
delegateEvents(["keydown", "mousemove"]);
function mount(core, elem) {
  let opts = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : {};
  const metrics = measureTerminal(opts.terminalFontFamily, opts.terminalLineHeight);
  const props = {
    core,
    logger: opts.logger,
    cols: opts.cols,
    rows: opts.rows,
    fit: opts.fit,
    controls: opts.controls,
    autoPlay: opts.autoPlay,
    terminalFontSize: opts.terminalFontSize,
    terminalFontFamily: opts.terminalFontFamily,
    terminalLineHeight: opts.terminalLineHeight,
    theme: opts.theme,
    ...metrics
  };
  let el;
  const dispose2 = render(() => {
    el = createComponent(Player, props);
    return el;
  }, elem);
  return {
    el,
    dispose: dispose2
  };
}
function measureTerminal(fontFamily, lineHeight) {
  const cols = 80;
  const rows = 24;
  const playerDiv = document.createElement("div");
  playerDiv.className = "ap-default-term-ff";
  playerDiv.style.height = "0px";
  playerDiv.style.overflow = "hidden";
  playerDiv.style.fontSize = "15px";
  if (fontFamily !== void 0) {
    playerDiv.style.setProperty("--term-font-family", fontFamily);
  }
  const termDiv = document.createElement("div");
  termDiv.className = "ap-term";
  termDiv.style.width = `${cols}ch`;
  termDiv.style.height = `${rows * (lineHeight ?? 1.3333333333)}em`;
  termDiv.style.fontSize = "100%";
  playerDiv.appendChild(termDiv);
  document.body.appendChild(playerDiv);
  const metrics = {
    charW: termDiv.clientWidth / cols,
    charH: termDiv.clientHeight / rows,
    bordersW: termDiv.offsetWidth - termDiv.clientWidth,
    bordersH: termDiv.offsetHeight - termDiv.clientHeight
  };
  document.body.removeChild(playerDiv);
  return metrics;
}
const CORE_OPTS = ["audioUrl", "autoPlay", "autoplay", "boldIsBright", "cols", "idleTimeLimit", "loop", "markers", "pauseOnMarkers", "poster", "preload", "rows", "speed", "startAt"];
const UI_OPTS = ["autoPlay", "autoplay", "cols", "controls", "fit", "rows", "terminalFontFamily", "terminalFontSize", "terminalLineHeight", "theme"];
function coreOpts(inputOpts) {
  let overrides = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {};
  const opts = Object.fromEntries(Object.entries(inputOpts).filter((_ref) => {
    let [key2] = _ref;
    return CORE_OPTS.includes(key2);
  }));
  opts.autoPlay ??= opts.autoplay;
  opts.speed ??= 1;
  return {
    ...opts,
    ...overrides
  };
}
function uiOpts(inputOpts) {
  let overrides = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {};
  const opts = Object.fromEntries(Object.entries(inputOpts).filter((_ref2) => {
    let [key2] = _ref2;
    return UI_OPTS.includes(key2);
  }));
  opts.autoPlay ??= opts.autoplay;
  opts.controls ??= "auto";
  return {
    ...opts,
    ...overrides
  };
}
function create(src, elem) {
  let opts = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : {};
  const logger = opts.logger ?? new DummyLogger();
  const core = new Core(src, coreOpts(opts, {
    logger
  }));
  const {
    el,
    dispose: dispose2
  } = mount(core, elem, uiOpts(opts, {
    logger
  }));
  const ready = core.init();
  const player = {
    el,
    dispose: dispose2,
    getCurrentTime: () => ready.then(core.getCurrentTime.bind(core)),
    getDuration: () => ready.then(core.getDuration.bind(core)),
    play: () => ready.then(core.play.bind(core)),
    pause: () => ready.then(core.pause.bind(core)),
    seek: (pos) => ready.then(() => core.seek(pos))
  };
  player.addEventListener = (name, callback) => {
    return core.addEventListener(name, callback.bind(player));
  };
  return player;
}
const AsciinemaPlayer = ({
  id,
  rows,
  cols,
  inputUrl,
  outputUrl,
  timingUrl,
  fit,
  speed,
  autoPlay,
  loop,
  theme,
  idleTimeLimit = 2,
  style: style2
}) => {
  const playerContainerRef = reactExports.useRef(null);
  reactExports.useEffect(() => {
    if (!playerContainerRef.current) return;
    const player = create(
      {
        url: [timingUrl, outputUrl, inputUrl],
        parser: "typescript"
      },
      playerContainerRef.current,
      {
        rows,
        cols,
        autoPlay,
        loop,
        theme,
        speed,
        idleTimeLimit,
        fit
      }
    );
    player.play();
    return () => {
      player.dispose();
    };
  }, [
    timingUrl,
    outputUrl,
    inputUrl,
    rows,
    cols,
    autoPlay,
    loop,
    theme,
    speed,
    idleTimeLimit,
    fit
  ]);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      id: `asciinema-player-${id || "default"}`,
      ref: playerContainerRef,
      style: { ...style2 }
    }
  );
};
const carouselThumbs = "_carouselThumbs_1mvg8_1";
const carouselThumb = "_carouselThumb_1mvg8_1";
const carouselPlayIcon = "_carouselPlayIcon_1mvg8_16";
const lightboxOverlay = "_lightboxOverlay_1mvg8_20";
const lightboxContent = "_lightboxContent_1mvg8_33";
const lightboxButtonCloseWrapper = "_lightboxButtonCloseWrapper_1mvg8_45";
const lightboxButtonClose = "_lightboxButtonClose_1mvg8_45";
const lightboxPreviewButton = "_lightboxPreviewButton_1mvg8_63";
const styles$5 = {
  carouselThumbs,
  carouselThumb,
  carouselPlayIcon,
  lightboxOverlay,
  lightboxContent,
  lightboxButtonCloseWrapper,
  lightboxButtonClose,
  lightboxPreviewButton
};
const LightboxCarousel = ({ id, slides }) => {
  const [isOpen, setIsOpen] = useProperty(id, "isOpen", {
    defaultValue: false
  });
  const [currentIndex, setCurrentIndex] = useProperty(id, "currentIndex", {
    defaultValue: 0
  });
  const [showOverlay, setShowOverlay] = useProperty(id, "showOverlay", {
    defaultValue: false
  });
  const openLightbox = reactExports.useCallback(
    (index) => {
      setCurrentIndex(index);
      setShowOverlay(true);
      setTimeout(() => setIsOpen(true), 10);
    },
    [setIsOpen]
  );
  const closeLightbox = reactExports.useCallback(() => {
    setIsOpen(false);
  }, [setIsOpen]);
  reactExports.useEffect(() => {
    if (!isOpen && showOverlay) {
      const timer = setTimeout(() => {
        setShowOverlay(false);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isOpen, showOverlay, setShowOverlay]);
  const showNext = reactExports.useCallback(() => {
    setCurrentIndex((currentIndex || 0) + 1);
  }, [slides, setCurrentIndex]);
  const showPrev = reactExports.useCallback(() => {
    setCurrentIndex(((currentIndex || 0) - 1 + slides.length) % slides.length);
  }, [slides, setCurrentIndex]);
  reactExports.useEffect(() => {
    if (!isOpen) return;
    const handleKeyUp = (e) => {
      if (e.key === "Escape") {
        closeLightbox();
      } else if (e.key === "ArrowRight") {
        showNext();
      } else if (e.key === "ArrowLeft") {
        showPrev();
      }
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener("keyup", handleKeyUp, true);
    return () => window.removeEventListener("keyup", handleKeyUp);
  }, [isOpen, showNext, showPrev]);
  const handleThumbClick = reactExports.useCallback(
    (e) => {
      const index = Number(e.currentTarget.dataset.index);
      openLightbox(index);
    },
    [openLightbox]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx("lightbox-carousel-container"), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$5.carouselThumbs), children: slides.map((slide, index) => {
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          "data-index": index,
          className: clsx(styles$5.carouselThumb),
          onClick: handleThumbClick,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: slide.label }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              "i",
              {
                className: clsx(
                  ApplicationIcons.play,
                  styles$5.carouselPlayIcon
                )
              }
            ) })
          ]
        },
        index
      );
    }) }),
    showOverlay && /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: clsx(styles$5.lightboxOverlay, isOpen ? "open" : "closed"),
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$5.lightboxButtonCloseWrapper), children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              className: styles$5.lightboxButtonClose,
              onClick: closeLightbox,
              children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.close })
            }
          ) }),
          slides.length > 1 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              className: clsx(styles$5.lightboxPreviewButton, "prev"),
              onClick: showPrev,
              children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.previous })
            }
          ) : "",
          slides.length > 1 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              className: clsx(styles$5.lightboxPreviewButton, "next"),
              onClick: showNext,
              children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.next })
            }
          ) : "",
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: clsx(styles$5.lightboxContent, isOpen ? "open" : "closed"),
              children: slides[currentIndex || 0]?.render()
            },
            `carousel-slide-${currentIndex}`
          )
        ]
      }
    )
  ] });
};
const HumanBaselineView = ({
  started,
  runtime,
  answer,
  completed,
  running,
  sessionLogs
}) => {
  const player_fns = [];
  const revokableUrls = [];
  const revokableUrl = (data) => {
    const blob = new Blob([data], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    revokableUrls.push(url);
    return url;
  };
  reactExports.useEffect(() => {
    return () => {
      revokableUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);
  let count = 1;
  for (const sessionLog of sessionLogs) {
    const rows = extractSize(sessionLog.output, "LINES", 24);
    const cols = extractSize(sessionLog.output, "COLUMNS", 80);
    const currentCount = count;
    const title2 = sessionLogs.length === 1 ? "Terminal Session" : `Terminal Session ${currentCount}`;
    player_fns.push({
      label: title2,
      render: () => /* @__PURE__ */ jsxRuntimeExports.jsx(
        AsciinemaPlayer,
        {
          id: `player-${currentCount}`,
          inputUrl: revokableUrl(sessionLog.input),
          outputUrl: revokableUrl(sessionLog.output),
          timingUrl: revokableUrl(sessionLog.timing),
          rows,
          cols,
          className: "asciinema-player",
          style: {
            height: `${rows * 2}em`,
            width: `${cols * 2}em`
          },
          fit: "both"
        }
      )
    });
    count += 1;
  }
  const StatusMessage = ({
    completed: completed2,
    running: running2,
    answer: answer2
  }) => {
    if (running2) {
      return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-style-label", children: "Running" });
    } else if (completed2) {
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "span",
          {
            className: "text-style-label text-style-secondary asciinema-player-status",
            children: "Answer"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: answer2 })
      ] });
    } else {
      return "Unknown status";
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "asciinema-wrapper", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "asciinema-container", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "asciinema-header-left text-style-label", children: [
      started ? formatDateTime(started) : "",
      runtime ? ` (${formatTime$1(Math.floor(runtime))})` : ""
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "asciinema-header-center text-style-label" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "asciinema-header-right", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      StatusMessage,
      {
        completed,
        running,
        answer
      }
    ) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "asciinema-body", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LightboxCarousel, { id: "ascii-cinema", slides: player_fns }) })
  ] }) });
};
const extractSize = (value2, label2, defaultValue) => {
  const regex2 = new RegExp(`${label2}="(\\d+)"`);
  const match2 = value2.match(regex2);
  const size = match2 ? match2[1] : void 0;
  if (size) {
    return parseInt(size);
  } else {
    return defaultValue;
  }
};
const toolsGrid = "_toolsGrid_1qqm2_1";
const tools = "_tools_1qqm2_1";
const tool = "_tool_1qqm2_1";
const styles$4 = {
  toolsGrid,
  tools,
  tool
};
const system_msg_added_sig = {
  type: "system_message",
  signature: {
    remove: ["/messages/0/source"],
    replace: ["/messages/0/role", "/messages/0/content"],
    add: ["/messages/1"]
  },
  render: (_changes, resolvedState) => {
    const messages2 = resolvedState["messages"];
    const message2 = messages2[0];
    if (typeof message2 !== "object" || !message2) {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, {});
    }
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      ChatView,
      {
        id: "system_msg_event_preview",
        messages: [message2],
        allowLinking: false
      },
      "system_msg_event_preview"
    );
  }
};
const kToolPattern = "/tools/(\\d+)";
const use_tools = {
  type: "use_tools",
  signature: {
    add: ["/tools/0"],
    replace: ["/tool_choice"],
    remove: []
  },
  render: (changes, resolvedState) => {
    return renderTools(changes, resolvedState);
  }
};
const add_tools = {
  type: "add_tools",
  signature: {
    add: [kToolPattern],
    replace: [],
    remove: []
  },
  render: (changes, resolvedState) => {
    return renderTools(changes, resolvedState);
  }
};
const messages = {
  type: "messages",
  match: (changes) => {
    const allMessages = changes.every((change) => {
      if (isRecord(change.value) && change.op === "add" && change.path.match(/\/messages\/\d+/)) {
        return typeof change.value["role"] === "string" && ["user", "assistant", "system", "tool"].includes(change.value["role"]);
      }
      return false;
    });
    return allMessages;
  },
  render: (changes) => {
    const messages2 = changes.map((c) => c.value);
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      ChatView,
      {
        id: "system_msg_event_preview",
        messages: messages2,
        allowLinking: false
      },
      "system_msg_event_preview"
    );
  }
};
const humanAgentKey = (key2) => {
  return `HumanAgentState:${key2}`;
};
const human_baseline_session = {
  type: "human_baseline_session",
  signature: {
    add: ["HumanAgentState:logs"],
    replace: [],
    remove: []
  },
  render: (_changes, state) => {
    const started = state[humanAgentKey("started_running")];
    const runtime = state[humanAgentKey("accumulated_time")];
    const answer = state[humanAgentKey("answer")];
    const completed = !!answer;
    const running = state[humanAgentKey("running_state")];
    const rawSessions = state[humanAgentKey("logs")];
    const startedDate = started ? new Date(started * 1e3) : void 0;
    const sessions = {};
    if (rawSessions) {
      for (const key2 of Object.keys(rawSessions)) {
        const value2 = rawSessions[key2];
        const match2 = key2.match(/(.*)_(\d+_\d+)\.(.*)/);
        if (match2) {
          const user2 = match2[1];
          const timestamp = match2[2];
          const type = match2[3];
          if (timestamp) {
            sessions[timestamp] = sessions[timestamp];
            switch (type) {
              case "input":
                sessions[timestamp].input = value2;
                break;
              case "output":
                sessions[timestamp].output = value2;
                break;
              case "timing":
                sessions[timestamp].timing = value2;
                break;
              case "name":
                sessions[timestamp].name = value2;
                break;
            }
            if (user2) {
              sessions[timestamp].user = user2;
            }
          }
        }
      }
    }
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      HumanBaselineView,
      {
        started: startedDate,
        running,
        completed,
        answer,
        runtime,
        sessionLogs: Object.values(sessions)
      },
      "human_baseline_view"
    );
  }
};
const renderTools = (changes, resolvedState) => {
  const toolIndexes = [];
  for (const change of changes) {
    const match2 = change.path.match(kToolPattern);
    if (match2 && match2[1]) {
      toolIndexes.push(match2[1]);
    }
  }
  const toolName = (toolChoice2) => {
    if (typeof toolChoice2 === "object" && toolChoice2 && !Array.isArray(toolChoice2)) {
      return toolChoice2["name"] || "";
    } else {
      return String(toolChoice2);
    }
  };
  const toolsInfo = {};
  const hasToolChoice = changes.find((change) => {
    return change.path.startsWith("/tool_choice");
  });
  if (resolvedState.tool_choice && hasToolChoice) {
    toolsInfo["Tool Choice"] = /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx("text-size-smaller"), children: toolName(resolvedState.tool_choice) });
  }
  const tools2 = resolvedState.tools;
  if (tools2.length > 0) {
    if (toolIndexes.length === 0) {
      toolsInfo["Tools"] = /* @__PURE__ */ jsxRuntimeExports.jsx(Tools, { toolDefinitions: resolvedState.tools });
    } else {
      const filtered = tools2.filter((_, index) => {
        return toolIndexes.includes(index.toString());
      });
      toolsInfo["Tools"] = /* @__PURE__ */ jsxRuntimeExports.jsx(Tools, { toolDefinitions: filtered });
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$4.tools), children: Object.keys(toolsInfo).map((key2) => {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: clsx(
            "text-size-smaller",
            "text-style-label",
            "text-style-secondary"
          ),
          children: key2
        }
      ),
      toolsInfo[key2]
    ] }, key2);
  }) }, "state-diff-tools");
};
const createMessageRenderer = (name, role) => {
  return {
    type: name,
    match: (changes) => {
      if (changes.length === 1) {
        const change = changes[0];
        if (change && isRecord(change.value) && change.op === "add" && change.path.match(/\/messages\/\d+/)) {
          return change.value["role"] === role;
        }
      }
      return false;
    },
    render: (changes) => {
      const message2 = changes[0]?.value;
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        ChatView,
        {
          id: "system_msg_event_preview",
          messages: [message2],
          allowLinking: false
        },
        "system_msg_event_preview"
      );
    }
  };
};
const RenderableChangeTypes = [
  system_msg_added_sig,
  createMessageRenderer("assistant_msg", "assistant"),
  createMessageRenderer("user_msg", "user"),
  use_tools,
  add_tools,
  messages
];
const StoreSpecificRenderableTypes = [
  human_baseline_session
];
const Tools = ({ toolDefinitions }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: styles$4.toolsGrid, children: toolDefinitions.map((toolDefinition, idx) => {
    const toolName = toolDefinition.name;
    const toolArgs = toolDefinition.parameters?.properties ? Object.keys(toolDefinition.parameters.properties) : [];
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      Tool,
      {
        toolName,
        toolArgs
      },
      `${toolName}-${idx}`
    );
  }) });
};
const Tool = ({ toolName, toolArgs }) => {
  const functionCall = toolArgs && toolArgs.length > 0 ? `${toolName}(${toolArgs.join(", ")})` : toolName;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: clsx("text-size-smallest", styles$4.tool), children: functionCall });
};
const diff = "_diff_eobja_1";
const summary$2 = "_summary_eobja_6";
const styles$3 = {
  diff,
  summary: summary$2
};
const StateEventView = ({
  eventNode,
  className: className2
}) => {
  const event = eventNode.event;
  const summary2 = reactExports.useMemo(() => {
    return summarizeChanges(event.changes);
  }, [event.changes]);
  const [before, after] = reactExports.useMemo(() => {
    try {
      return synthesizeComparable(event.changes);
    } catch (e) {
      console.error(
        "Unable to synthesize comparable object to display state diffs.",
        e
      );
      return [{}, {}];
    }
  }, [event.changes]);
  const changePreview = reactExports.useMemo(() => {
    const isStore = eventNode.event.event === "store";
    const afterClone = structuredClone(after) || {};
    return generatePreview(event.changes, afterClone, isStore);
  }, [event.changes, after]);
  const title2 = event.event === "state" ? "State Updated" : "Store Updated";
  const collapseEvent = useStore((state) => state.setTranscriptCollapsedEvent);
  reactExports.useEffect(() => {
    if (changePreview === void 0) {
      collapseEvent(kTranscriptCollapseScope, eventNode.id, true);
    }
  }, [changePreview, collapseEvent]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      title: title2,
      className: className2,
      subTitle: event.timestamp ? formatDateTime(new Date(event.timestamp)) : void 0,
      text: !changePreview ? summary2 : void 0,
      collapsibleContent: true,
      children: [
        changePreview ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { "data-name": "Summary", className: clsx(styles$3.summary), children: changePreview }) : void 0,
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          StateDiffView,
          {
            before,
            after,
            "data-name": "Diff",
            className: clsx(styles$3.diff)
          }
        )
      ]
    }
  );
};
const generatePreview = (changes, resolvedState, isStore) => {
  const results = [];
  for (const changeType of [
    ...RenderableChangeTypes,
    ...isStore ? StoreSpecificRenderableTypes : []
  ]) {
    if (changeType.signature) {
      const requiredMatchCount = changeType.signature.remove.length + changeType.signature.replace.length + changeType.signature.add.length;
      let matchingOps = 0;
      for (const change of changes) {
        const op = change.op;
        switch (op) {
          case "add":
            if (changeType.signature.add && changeType.signature.add.length > 0) {
              changeType.signature.add.forEach((signature) => {
                if (change.path.match(signature)) {
                  matchingOps++;
                }
              });
            }
            break;
          case "remove":
            if (changeType.signature.remove && changeType.signature.remove.length > 0) {
              changeType.signature.remove.forEach((signature) => {
                if (change.path.match(signature)) {
                  matchingOps++;
                }
              });
            }
            break;
          case "replace":
            if (changeType.signature.replace && changeType.signature.replace.length > 0) {
              changeType.signature.replace.forEach((signature) => {
                if (change.path.match(signature)) {
                  matchingOps++;
                }
              });
            }
            break;
        }
      }
      if (matchingOps === requiredMatchCount) {
        const el = changeType.render(changes, resolvedState);
        results.push(el);
        break;
      }
    } else if (changeType.match) {
      const matches = changeType.match(changes);
      if (matches) {
        const el = changeType.render(changes, resolvedState);
        results.push(el);
        break;
      }
    }
  }
  return results.length > 0 ? results : void 0;
};
const summarizeChanges = (changes) => {
  const changeMap = {
    add: [],
    copy: [],
    move: [],
    replace: [],
    remove: [],
    test: []
  };
  for (const change of changes) {
    switch (change.op) {
      case "add":
        changeMap.add.push(change.path);
        break;
      case "copy":
        changeMap.copy.push(change.path);
        break;
      case "move":
        changeMap.move.push(change.path);
        break;
      case "replace":
        changeMap.replace.push(change.path);
        break;
      case "remove":
        changeMap.remove.push(change.path);
        break;
      case "test":
        changeMap.test.push(change.path);
        break;
    }
  }
  const changeList = [];
  const totalOpCount = Object.keys(changeMap).reduce((prev, current) => {
    return prev + changeMap[current].length;
  }, 0);
  if (totalOpCount > 2) {
    Object.keys(changeMap).forEach((key2) => {
      const opChanges = changeMap[key2];
      if (opChanges.length > 0) {
        changeList.push(`${key2} ${opChanges.length}`);
      }
    });
  } else {
    Object.keys(changeMap).forEach((key2) => {
      const opChanges = changeMap[key2];
      if (opChanges.length > 0) {
        changeList.push(`${key2} ${opChanges.join(", ")}`);
      }
    });
  }
  return changeList.join(", ");
};
const synthesizeComparable = (changes) => {
  const before = {};
  const after = {};
  for (const change of changes) {
    switch (change.op) {
      case "add":
        initializeArrays(before, change.path);
        initializeArrays(after, change.path);
        setPath(after, change.path, change.value);
        break;
      case "copy":
        setPath(before, change.path, change.value);
        setPath(after, change.path, change.value);
        break;
      case "move":
        setPath(before, change.from || "", change.value);
        setPath(after, change.path, change.value);
        break;
      case "remove":
        setPath(before, change.path, change.value);
        break;
      case "replace":
        initializeArrays(before, change.path);
        initializeArrays(after, change.path);
        setPath(before, change.path, change.replaced);
        setPath(after, change.path, change.value);
        break;
    }
  }
  return [before, after];
};
function setPath(target, path, value2) {
  const keys = parsePath(path);
  let current = target;
  for (let i2 = 0; i2 < keys.length - 1; i2++) {
    const key2 = keys[i2];
    if (key2 && !(key2 in current)) {
      const nextKey = keys[i2 + 1];
      if (nextKey) {
        current[key2] = isArrayIndex(nextKey) ? [] : {};
      }
      current = current[key2];
    }
  }
  const lastKey = keys[keys.length - 1];
  if (lastKey) {
    current[lastKey] = value2;
  }
}
function initializeArrays(target, path) {
  const keys = parsePath(path);
  let current = target;
  for (let i2 = 0; i2 < keys.length - 1; i2++) {
    const key2 = keys[i2];
    const nextKey = keys[i2 + 1];
    if (!key2 || !nextKey) {
      continue;
    }
    if (isArrayIndex(nextKey)) {
      current[key2] = initializeArray(
        current[key2],
        nextKey
      );
    } else {
      current[key2] = initializeObject(current[key2]);
    }
    current = current[key2];
  }
  const lastKey = keys[keys.length - 1];
  if (lastKey && isArrayIndex(lastKey)) {
    const lastValue = current[lastKey];
    initializeArray(lastValue, lastKey);
  }
}
function parsePath(path) {
  return path.split("/").filter(Boolean);
}
function isArrayIndex(key2) {
  return /^\d+$/.test(key2);
}
function initializeArray(current, nextKey) {
  if (!Array.isArray(current)) {
    current = [];
  }
  const nextKeyIndex = parseInt(nextKey, 10);
  while (current.length < nextKeyIndex) {
    current.push("");
  }
  return current;
}
function initializeObject(current) {
  return current ?? {};
}
const StepEventView = ({
  eventNode,
  children: children2,
  className: className2
}) => {
  const event = eventNode.event;
  const descriptor = stepDescriptor(event);
  const title2 = descriptor.name || `${event.type ? event.type + ": " : "Step: "}${event.name}`;
  const text2 = summarize(children2);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      childIds: children2.map((child) => child.id),
      className: clsx("transcript-step", className2),
      title: title2,
      subTitle: event.timestamp ? formatDateTime(new Date(event.timestamp)) : void 0,
      icon: descriptor.icon,
      text: text2
    }
  );
};
const summarize = (children2) => {
  if (children2.length === 0) {
    return "(no events)";
  }
  const formatEvent = (event, count) => {
    if (count === 1) {
      return `${count} ${event} event`;
    } else {
      return `${count} ${event} events`;
    }
  };
  const typeCount = {};
  children2.forEach((child) => {
    const currentCount = typeCount[child.event.event] || 0;
    typeCount[child.event.event] = currentCount + 1;
  });
  const numberOfTypes = Object.keys(typeCount).length;
  if (numberOfTypes < 3) {
    return Object.keys(typeCount).map((key2) => {
      return formatEvent(key2, typeCount[key2] || 0);
    }).join(", ");
  }
  if (children2.length === 1) {
    return "1 event";
  } else {
    return `${children2.length} events`;
  }
};
const stepDescriptor = (event) => {
  const rootStepDescriptor = {
    endSpace: true
  };
  if (event.type === "solver") {
    switch (event.name) {
      case "chain_of_thought":
        return {
          ...rootStepDescriptor
        };
      case "generate":
        return {
          ...rootStepDescriptor
        };
      case "self_critique":
        return {
          ...rootStepDescriptor
        };
      case "system_message":
        return {
          ...rootStepDescriptor
        };
      case "use_tools":
        return {
          ...rootStepDescriptor
        };
      case "multiple_choice":
        return {
          ...rootStepDescriptor
        };
      default:
        return {
          ...rootStepDescriptor
        };
    }
  } else if (event.type === "scorer") {
    return {
      ...rootStepDescriptor
    };
  } else if (event.event === "step") {
    if (event.name === kSandboxSignalName) {
      return {
        ...rootStepDescriptor,
        name: "Sandbox Events"
      };
    } else if (event.name === "init") {
      return {
        ...rootStepDescriptor,
        name: "Init"
      };
    } else {
      return {
        ...rootStepDescriptor
      };
    }
  } else {
    switch (event.name) {
      case "sample_init":
        return {
          ...rootStepDescriptor,
          name: "Sample Init"
        };
      default:
        return {
          endSpace: false
        };
    }
  }
};
const summary$1 = "_summary_ac4z2_1";
const summaryRendered = "_summaryRendered_ac4z2_6";
const subtaskSummary = "_subtaskSummary_ac4z2_10";
const subtaskLabel = "_subtaskLabel_ac4z2_17";
const styles$2 = {
  summary: summary$1,
  summaryRendered,
  subtaskSummary,
  subtaskLabel
};
const SubtaskEventView = ({
  eventNode,
  children: children2,
  className: className2
}) => {
  const event = eventNode.event;
  const body = [];
  if (event.type === "fork") {
    body.push(
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { title: "Summary", className: clsx(styles$2.summary), children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-style-label"), children: "Inputs" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$2.summaryRendered), children: /* @__PURE__ */ jsxRuntimeExports.jsx(Rendered, { values: event.input }) })
      ] })
    );
  } else {
    body.push(
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SubtaskSummary,
        {
          "data-name": "Summary",
          input: event.input,
          result: event.result
        }
      )
    );
  }
  const type = event.type === "fork" ? "Fork" : "Subtask";
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      className: className2,
      title: formatTitle(
        `${type}: ${event.name}`,
        void 0,
        event.working_time
      ),
      subTitle: event.timestamp ? formatTiming(event.timestamp, event.working_start) : void 0,
      childIds: children2.map((child) => child.id),
      collapseControl: "bottom",
      children: body
    }
  );
};
const SubtaskSummary = ({ input, result: result2 }) => {
  const output2 = typeof result2 === "object" ? result2 : { result: result2 };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: clsx(styles$2.subtaskSummary), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-style-label", "text-size-small"), children: "Input" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-large", styles$2.subtaskLabel) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-style-label", "text-size-small"), children: "Output" }),
    input ? /* @__PURE__ */ jsxRuntimeExports.jsx(Rendered, { values: input }) : void 0,
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("text-size-title-secondary", styles$2.subtaskLabel), children: /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: ApplicationIcons.arrows.right }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: output2 ? /* @__PURE__ */ jsxRuntimeExports.jsx(Rendered, { values: output2 }) : "-" })
  ] });
};
const Rendered = ({ values }) => {
  if (Array.isArray(values)) {
    return values.map((val, index) => {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(Rendered, { values: val }, index);
    });
  } else if (values && typeof values === "object") {
    if (Object.keys(values).length === 0) {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(None, {});
    } else {
      return /* @__PURE__ */ jsxRuntimeExports.jsx(MetaDataGrid, { entries: values });
    }
  } else {
    return String(values);
  }
};
const None = () => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: clsx("text-size-small", "text-style-secondary"), children: "[None]" });
};
const summary = "_summary_1qsnv_1";
const approval = "_approval_1qsnv_6";
const progress = "_progress_1qsnv_12";
const styles$1 = {
  summary,
  approval,
  progress
};
const ToolEventView = ({
  eventNode,
  children: children2,
  className: className2
}) => {
  const event = eventNode.event;
  const { name, input, description: description2, functionCall, contentType } = reactExports.useMemo(
    () => resolveToolInput(event.function, event.arguments),
    [event.function, event.arguments]
  );
  const { approvalNode, lastModelNode } = reactExports.useMemo(() => {
    const approvalNode2 = children2.find((e) => {
      return e.event.event === "approval";
    });
    const lastModelNode2 = children2.findLast((e) => {
      return e.event.event === "model";
    });
    return {
      approvalNode: approvalNode2,
      lastModelNode: lastModelNode2
    };
  }, [event.events]);
  const title2 = `Tool: ${event.view?.title || event.function}`;
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    EventPanel,
    {
      eventNodeId: eventNode.id,
      depth: eventNode.depth,
      title: formatTitle(title2, void 0, event.working_time),
      className: className2,
      subTitle: event.timestamp ? formatTiming(event.timestamp, event.working_start) : void 0,
      icon: ApplicationIcons.solvers.use_tools,
      childIds: children2.map((child) => child.id),
      collapseControl: "bottom",
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { "data-name": "Summary", className: styles$1.summary, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ToolCallView,
          {
            id: `${eventNode.id}-tool-call`,
            tool: name,
            functionCall,
            input,
            description: description2,
            contentType,
            output: event.error?.message || event.result || "",
            mode: "compact",
            view: event.view ? event.view : void 0
          }
        ),
        lastModelNode ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          ChatView,
          {
            id: `${eventNode.id}-toolcall-chatmessage`,
            messages: lastModelNode.event.output.choices.map((m) => m.message),
            toolCallStyle: "compact",
            allowLinking: false
          }
        ) : void 0,
        approvalNode ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          ApprovalEventView,
          {
            eventNode: approvalNode,
            className: styles$1.approval
          }
        ) : "",
        event.pending ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$1.progress), children: /* @__PURE__ */ jsxRuntimeExports.jsx(PulsingDots, { subtle: false, size: "medium" }) }) : void 0
      ] })
    }
  );
};
const eventSearchText = (node2) => {
  const texts = [];
  const event = node2.event;
  switch (event.event) {
    case "model": {
      const modelEvent = event;
      if (modelEvent.model) {
        texts.push(modelEvent.model);
      }
      if (modelEvent.output?.choices) {
        for (const choice of modelEvent.output.choices) {
          texts.push(...extractContentText(choice.message.content));
        }
      }
      if (modelEvent.input) {
        for (const msg of modelEvent.input) {
          if (msg.role === "user" || msg.role === "system") {
            texts.push(...extractContentText(msg.content));
          }
        }
      }
      break;
    }
    case "tool": {
      const toolEvent = event;
      if (toolEvent.view?.title) {
        texts.push(toolEvent.view.title);
      }
      if (toolEvent.function) {
        texts.push(toolEvent.function);
      }
      if (toolEvent.arguments) {
        texts.push(JSON.stringify(toolEvent.arguments));
      }
      if (toolEvent.result) {
        if (typeof toolEvent.result === "string") {
          texts.push(toolEvent.result);
        } else {
          texts.push(JSON.stringify(toolEvent.result));
        }
      }
      if (toolEvent.error?.message) {
        texts.push(toolEvent.error.message);
      }
      break;
    }
    case "error": {
      const errorEvent = event;
      if (errorEvent.error?.message) {
        texts.push(errorEvent.error.message);
      }
      if (errorEvent.error?.traceback) {
        texts.push(errorEvent.error.traceback);
      }
      break;
    }
    case "logger": {
      const loggerEvent = event;
      if (loggerEvent.message?.message) {
        texts.push(loggerEvent.message.message);
      }
      if (loggerEvent.message?.filename) {
        texts.push(loggerEvent.message.filename);
      }
      break;
    }
    case "info": {
      const infoEvent = event;
      if (infoEvent.source) {
        texts.push(infoEvent.source);
      }
      if (infoEvent.data) {
        if (typeof infoEvent.data === "string") {
          texts.push(infoEvent.data);
        } else {
          texts.push(JSON.stringify(infoEvent.data));
        }
      }
      break;
    }
    case "compaction": {
      const compactionEvent = event;
      if (compactionEvent.source) {
        texts.push(compactionEvent.source);
      }
      texts.push(JSON.stringify(compactionEvent));
      break;
    }
    case "step": {
      const stepEvent = event;
      if (stepEvent.name) {
        texts.push(stepEvent.name);
      }
      if (stepEvent.type) {
        texts.push(stepEvent.type);
      }
      break;
    }
    case "subtask": {
      const subtaskEvent = event;
      if (subtaskEvent.name) {
        texts.push(subtaskEvent.name);
      }
      if (subtaskEvent.type) {
        texts.push(subtaskEvent.type);
      }
      if (subtaskEvent.input) {
        texts.push(JSON.stringify(subtaskEvent.input));
      }
      if (subtaskEvent.result) {
        texts.push(JSON.stringify(subtaskEvent.result));
      }
      break;
    }
    case "span_begin": {
      const spanEvent = event;
      if (spanEvent.name) {
        texts.push(spanEvent.name);
      }
      if (spanEvent.type) {
        texts.push(spanEvent.type);
      }
      break;
    }
  }
  return texts;
};
const extractContentText = (content2) => {
  if (typeof content2 === "string") {
    return [content2];
  }
  const texts = [];
  for (const item of content2) {
    switch (item.type) {
      case "text":
        texts.push(item.text);
        break;
      case "reasoning": {
        const reasoning2 = item;
        if (reasoning2.reasoning) {
          texts.push(reasoning2.reasoning);
        } else if (reasoning2.summary) {
          texts.push(reasoning2.summary);
        }
        break;
      }
      case "tool_use": {
        const toolUse = item;
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
const node = "_node_engat_1";
const attached = "_attached_engat_5";
const attachedParent = "_attachedParent_engat_9";
const attachedChild = "_attachedChild_engat_16";
const last = "_last_engat_21";
const styles = {
  node,
  attached,
  attachedParent,
  attachedChild,
  last
};
const TranscriptVirtualListComponent = ({
  id,
  listHandle,
  eventNodes,
  scrollRef,
  running,
  initialEventId,
  offsetTop,
  className: className2
}) => {
  const initialEventIndex = reactExports.useMemo(() => {
    if (initialEventId === null || initialEventId === void 0) {
      return void 0;
    }
    const result2 = eventNodes.findIndex((event) => {
      return event.id === initialEventId;
    });
    return result2 === -1 ? void 0 : result2;
  }, [initialEventId, eventNodes]);
  const hasToolEventsAtCurrentDepth = reactExports.useCallback(
    (startIndex) => {
      for (let i2 = startIndex; i2 >= 0; i2--) {
        const node2 = eventNodes[i2];
        if (!node2 || !eventNodes[startIndex]) {
          return false;
        }
        if (node2.event.event === "tool") {
          return true;
        }
        if (node2.depth < eventNodes[startIndex].depth) {
          return false;
        }
      }
      return false;
    },
    [eventNodes]
  );
  const contextWithToolEvents = reactExports.useMemo(() => ({ hasToolEvents: true }), []);
  const contextWithoutToolEvents = reactExports.useMemo(
    () => ({ hasToolEvents: false }),
    []
  );
  const renderRow = reactExports.useCallback(
    (index, item) => {
      const paddingClass = index === 0 ? styles.first : void 0;
      const previousIndex = index - 1;
      const nextIndex = index + 1;
      const previous = previousIndex > 0 && previousIndex <= eventNodes.length ? eventNodes[previousIndex] : void 0;
      const next = nextIndex < eventNodes.length ? eventNodes[nextIndex] : void 0;
      const attached2 = item.event.event === "tool" && (previous?.event.event === "tool" || previous?.event.event === "model");
      const attachedParent2 = item.event.event === "model" && next?.event.event === "tool";
      const attachedClass = attached2 ? styles.attached : void 0;
      const attachedChildClass = attached2 ? styles.attachedChild : void 0;
      const attachedParentClass = attachedParent2 ? styles.attachedParent : void 0;
      const hasToolEvents = hasToolEventsAtCurrentDepth(index);
      const context = hasToolEvents ? contextWithToolEvents : contextWithoutToolEvents;
      const isLast = index === eventNodes.length - 1;
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          id: item.id,
          className: clsx(
            styles.node,
            paddingClass,
            isLast ? styles.last : void 0,
            attachedClass
          ),
          style: {
            paddingLeft: `${item.depth <= 1 ? item.depth * 0.7 : (0.7 + item.depth - 1) * 1}em`,
            paddingRight: `${item.depth === 0 ? void 0 : ".7em"} `
          },
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            RenderedEventNode,
            {
              node: item,
              next,
              className: clsx(attachedParentClass, attachedChildClass),
              context
            }
          )
        },
        item.id
      );
    },
    [
      eventNodes,
      hasToolEventsAtCurrentDepth,
      contextWithToolEvents,
      contextWithoutToolEvents
    ]
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    LiveVirtualList,
    {
      listHandle,
      className: className2,
      id,
      scrollRef,
      data: eventNodes,
      initialTopMostItemIndex: initialEventIndex,
      offsetTop,
      renderRow,
      live: running,
      animation: running,
      itemSearchText: eventSearchText
    }
  );
};
const TranscriptVirtualList = reactExports.memo(
  (props) => {
    const {
      id,
      scrollRef,
      eventNodes,
      listHandle,
      running,
      initialEventId,
      offsetTop,
      className: className2
    } = props;
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      TranscriptVirtualListComponent,
      {
        id,
        listHandle,
        eventNodes,
        initialEventId,
        offsetTop,
        scrollRef,
        running,
        className: className2
      }
    );
  }
);
const RenderedEventNode = reactExports.memo(
  ({ node: node2, next, className: className2, context }) => {
    switch (node2.event.event) {
      case "sample_init":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          SampleInitEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "sample_limit":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          SampleLimitEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "info":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          InfoEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "compaction":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          CompactionEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "logger":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          LoggerEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "model":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ModelEventView,
          {
            eventNode: node2,
            showToolCalls: next?.event.event !== "tool",
            className: className2,
            context
          }
        );
      case "score":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ScoreEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "score_edit":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ScoreEditEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "state":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          StateEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "span_begin":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          SpanEventView,
          {
            eventNode: node2,
            children: node2.children,
            className: className2
          }
        );
      case "step":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          StepEventView,
          {
            eventNode: node2,
            children: node2.children,
            className: className2
          }
        );
      case "store":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          StateEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "subtask":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          SubtaskEventView,
          {
            eventNode: node2,
            className: className2,
            children: node2.children
          }
        );
      case "tool":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ToolEventView,
          {
            eventNode: node2,
            className: className2,
            children: node2.children
          }
        );
      case "input":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          InputEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "error":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ErrorEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "approval":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ApprovalEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      case "sandbox":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          SandboxEventView,
          {
            eventNode: node2,
            className: className2
          }
        );
      default:
        return null;
    }
  }
);
const flatTree = (eventNodes, collapsed, visitors, parentNode) => {
  const result2 = [];
  for (const node2 of eventNodes) {
    if (visitors && visitors.length > 0) {
      let pendingNodes = [{ ...node2 }];
      for (const visitor of visitors) {
        const allResults = [];
        for (const pendingNode of pendingNodes) {
          const visitorResult = visitor.visit(pendingNode);
          if (parentNode) {
            parentNode.children = visitorResult;
          }
          allResults.push(...visitorResult);
        }
        pendingNodes = allResults;
      }
      for (const pendingNode of pendingNodes) {
        const children2 = flatTree(
          pendingNode.children,
          collapsed,
          visitors,
          pendingNode
        );
        pendingNode.children = children2;
        result2.push(pendingNode);
        if (collapsed === null || collapsed[pendingNode.id] !== true) {
          result2.push(...children2);
        }
      }
      for (const visitor of visitors) {
        if (visitor.flush) {
          const finalNodes = visitor.flush();
          result2.push(...finalNodes);
        }
      }
    } else {
      result2.push(node2);
      const children2 = flatTree(node2.children, collapsed, visitors, node2);
      if (collapsed === null || collapsed[node2.id] !== true) {
        result2.push(...children2);
      }
    }
  }
  return result2;
};
const TranscriptViewNodes = ({
  id,
  eventNodes,
  defaultCollapsedIds,
  nodeFilter,
  scrollRef,
  initialEventId,
  className: className2
}) => {
  const listHandle = reactExports.useRef(null);
  const collapsedEvents = useStore((state) => state.transcriptCollapsedEvents);
  const flattenedNodes = reactExports.useMemo(() => {
    return flatTree(
      nodeFilter ? nodeFilter(eventNodes) : eventNodes,
      (collapsedEvents ? collapsedEvents[kTranscriptCollapseScope] : void 0) || defaultCollapsedIds
    );
  }, [eventNodes, collapsedEvents, defaultCollapsedIds]);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    TranscriptVirtualList,
    {
      id,
      listHandle,
      eventNodes: flattenedNodes,
      scrollRef,
      offsetTop: 10,
      className: clsx(styles$l.listContainer, className2),
      initialEventId
    }
  );
};
export {
  ANSIDisplay as A,
  CopyButton as C,
  DisplayModeContext as D,
  EventNode as E,
  JSONPanel as J,
  LiveVirtualList as L,
  MetaDataGrid as M,
  RecordTree as R,
  ScoreValue as S,
  TaskName as T,
  Yr as Y,
  LabeledValue as a,
  TabSet as b,
  TabPanel as c,
  ModelUsagePanel as d,
  MarkdownDivWithReferences as e,
  TranscriptViewNodes as f,
  ChatView as g,
  useCollapseTranscriptEvent as h,
  isJson as i,
  TYPE_SCORERS as j,
  kSandboxSignalName as k,
  TYPE_SCORER as l,
  useVirtuosoState as m,
  useTranscriptNavigation as n,
  flatTree as o,
  kTranscriptOutlineCollapseScope as p,
  useScrollTrack as q,
  eventTypeValues as r,
  kTranscriptCollapseScope as s,
  kCollapsibleEventTypes as t,
  useEventNodes as u,
  resolveMessages as v,
  ChatMessageRow as w
};
//# sourceMappingURL=TranscriptViewNodes.js.map
