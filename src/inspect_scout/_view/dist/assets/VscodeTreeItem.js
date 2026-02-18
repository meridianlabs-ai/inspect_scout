import { cd as Subscribable, ce as shallowEqualObjects, cf as hashKey, cg as getDefaultState, ch as notifyManager, b as useQueryClient, r as reactExports, ci as noop, cj as shouldThrowError, h as E$1 } from "./index.js";
var MutationObserver = class extends Subscribable {
  #client;
  #currentResult = void 0;
  #currentMutation;
  #mutateOptions;
  constructor(client, options) {
    super();
    this.#client = client;
    this.setOptions(options);
    this.bindMethods();
    this.#updateResult();
  }
  bindMethods() {
    this.mutate = this.mutate.bind(this);
    this.reset = this.reset.bind(this);
  }
  setOptions(options) {
    const prevOptions = this.options;
    this.options = this.#client.defaultMutationOptions(options);
    if (!shallowEqualObjects(this.options, prevOptions)) {
      this.#client.getMutationCache().notify({
        type: "observerOptionsUpdated",
        mutation: this.#currentMutation,
        observer: this
      });
    }
    if (prevOptions?.mutationKey && this.options.mutationKey && hashKey(prevOptions.mutationKey) !== hashKey(this.options.mutationKey)) {
      this.reset();
    } else if (this.#currentMutation?.state.status === "pending") {
      this.#currentMutation.setOptions(this.options);
    }
  }
  onUnsubscribe() {
    if (!this.hasListeners()) {
      this.#currentMutation?.removeObserver(this);
    }
  }
  onMutationUpdate(action) {
    this.#updateResult();
    this.#notify(action);
  }
  getCurrentResult() {
    return this.#currentResult;
  }
  reset() {
    this.#currentMutation?.removeObserver(this);
    this.#currentMutation = void 0;
    this.#updateResult();
    this.#notify();
  }
  mutate(variables, options) {
    this.#mutateOptions = options;
    this.#currentMutation?.removeObserver(this);
    this.#currentMutation = this.#client.getMutationCache().build(this.#client, this.options);
    this.#currentMutation.addObserver(this);
    return this.#currentMutation.execute(variables);
  }
  #updateResult() {
    const state = this.#currentMutation?.state ?? getDefaultState();
    this.#currentResult = {
      ...state,
      isPending: state.status === "pending",
      isSuccess: state.status === "success",
      isError: state.status === "error",
      isIdle: state.status === "idle",
      mutate: this.mutate,
      reset: this.reset
    };
  }
  #notify(action) {
    notifyManager.batch(() => {
      if (this.#mutateOptions && this.hasListeners()) {
        const variables = this.#currentResult.variables;
        const onMutateResult = this.#currentResult.context;
        const context = {
          client: this.#client,
          meta: this.options.meta,
          mutationKey: this.options.mutationKey
        };
        if (action?.type === "success") {
          try {
            this.#mutateOptions.onSuccess?.(
              action.data,
              variables,
              onMutateResult,
              context
            );
          } catch (e3) {
            void Promise.reject(e3);
          }
          try {
            this.#mutateOptions.onSettled?.(
              action.data,
              null,
              variables,
              onMutateResult,
              context
            );
          } catch (e3) {
            void Promise.reject(e3);
          }
        } else if (action?.type === "error") {
          try {
            this.#mutateOptions.onError?.(
              action.error,
              variables,
              onMutateResult,
              context
            );
          } catch (e3) {
            void Promise.reject(e3);
          }
          try {
            this.#mutateOptions.onSettled?.(
              void 0,
              action.error,
              variables,
              onMutateResult,
              context
            );
          } catch (e3) {
            void Promise.reject(e3);
          }
        }
      }
      this.listeners.forEach((listener) => {
        listener(this.#currentResult);
      });
    });
  }
};
function useMutation(options, queryClient) {
  const client = useQueryClient();
  const [observer] = reactExports.useState(
    () => new MutationObserver(
      client,
      options
    )
  );
  reactExports.useEffect(() => {
    observer.setOptions(options);
  }, [observer, options]);
  const result = reactExports.useSyncExternalStore(
    reactExports.useCallback(
      (onStoreChange) => observer.subscribe(notifyManager.batchCalls(onStoreChange)),
      [observer]
    ),
    () => observer.getCurrentResult(),
    () => observer.getCurrentResult()
  );
  const mutate = reactExports.useCallback(
    (variables, mutateOptions) => {
      observer.mutate(variables, mutateOptions).catch(noop);
    },
    [observer]
  );
  if (result.error && shouldThrowError(observer.options.throwOnError, [result.error])) {
    throw result.error;
  }
  return { ...result, mutate, mutateAsync: result.mutate };
}
const e$a = /* @__PURE__ */ new Set(["children", "localName", "ref", "style", "className"]), n$7 = /* @__PURE__ */ new WeakMap(), t$4 = (e3, t2, o2, l2, a2) => {
  const s4 = a2?.[t2];
  void 0 === s4 ? (e3[t2] = o2, null == o2 && t2 in HTMLElement.prototype && e3.removeAttribute(t2)) : o2 !== l2 && ((e4, t3, o3) => {
    let l3 = n$7.get(e4);
    void 0 === l3 && n$7.set(e4, l3 = /* @__PURE__ */ new Map());
    let a3 = l3.get(t3);
    void 0 !== o3 ? void 0 === a3 ? (l3.set(t3, a3 = { handleEvent: o3 }), e4.addEventListener(t3, a3)) : a3.handleEvent = o3 : void 0 !== a3 && (l3.delete(t3), e4.removeEventListener(t3, a3));
  })(e3, s4, o2);
}, o$7 = ({ react: n3, tagName: o2, elementClass: l2, events: a2, displayName: s4 }) => {
  const c2 = new Set(Object.keys(a2 ?? {})), r2 = n3.forwardRef(((s5, r3) => {
    const i4 = n3.useRef(/* @__PURE__ */ new Map()), d2 = n3.useRef(null), f2 = {}, u2 = {};
    for (const [n4, t2] of Object.entries(s5)) e$a.has(n4) ? f2["className" === n4 ? "class" : n4] = t2 : c2.has(n4) || n4 in l2.prototype ? u2[n4] = t2 : f2[n4] = t2;
    return n3.useLayoutEffect((() => {
      if (null === d2.current) return;
      const e3 = /* @__PURE__ */ new Map();
      for (const n4 in u2) t$4(d2.current, n4, s5[n4], i4.current.get(n4), a2), i4.current.delete(n4), e3.set(n4, s5[n4]);
      for (const [e4, n4] of i4.current) t$4(d2.current, e4, void 0, n4, a2);
      i4.current = e3;
    })), n3.useLayoutEffect((() => {
      d2.current?.removeAttribute("defer-hydration");
    }), []), f2.suppressHydrationWarning = true, n3.createElement(o2, { ...f2, ref: n3.useCallback(((e3) => {
      d2.current = e3, "function" == typeof r3 ? r3(e3) : null !== r3 && (r3.current = e3);
    }), [r3]) });
  }));
  return r2.displayName = s4 ?? l2.name, r2;
};
const t$3 = globalThis, e$9 = t$3.ShadowRoot && (void 0 === t$3.ShadyCSS || t$3.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, s$6 = /* @__PURE__ */ Symbol(), o$6 = /* @__PURE__ */ new WeakMap();
let n$6 = class n {
  constructor(t2, e3, o2) {
    if (this._$cssResult$ = true, o2 !== s$6) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
    this.cssText = t2, this.t = e3;
  }
  get styleSheet() {
    let t2 = this.o;
    const s4 = this.t;
    if (e$9 && void 0 === t2) {
      const e3 = void 0 !== s4 && 1 === s4.length;
      e3 && (t2 = o$6.get(s4)), void 0 === t2 && ((this.o = t2 = new CSSStyleSheet()).replaceSync(this.cssText), e3 && o$6.set(s4, t2));
    }
    return t2;
  }
  toString() {
    return this.cssText;
  }
};
const r$5 = (t2) => new n$6("string" == typeof t2 ? t2 : t2 + "", void 0, s$6), i$6 = (t2, ...e3) => {
  const o2 = 1 === t2.length ? t2[0] : e3.reduce((e4, s4, o3) => e4 + ((t3) => {
    if (true === t3._$cssResult$) return t3.cssText;
    if ("number" == typeof t3) return t3;
    throw Error("Value passed to 'css' function must be a 'css' function result: " + t3 + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
  })(s4) + t2[o3 + 1], t2[0]);
  return new n$6(o2, t2, s$6);
}, S$1 = (s4, o2) => {
  if (e$9) s4.adoptedStyleSheets = o2.map((t2) => t2 instanceof CSSStyleSheet ? t2 : t2.styleSheet);
  else for (const e3 of o2) {
    const o3 = document.createElement("style"), n3 = t$3.litNonce;
    void 0 !== n3 && o3.setAttribute("nonce", n3), o3.textContent = e3.cssText, s4.appendChild(o3);
  }
}, c$4 = e$9 ? (t2) => t2 : (t2) => t2 instanceof CSSStyleSheet ? ((t3) => {
  let e3 = "";
  for (const s4 of t3.cssRules) e3 += s4.cssText;
  return r$5(e3);
})(t2) : t2;
const { is: i$5, defineProperty: e$8, getOwnPropertyDescriptor: h$2, getOwnPropertyNames: r$4, getOwnPropertySymbols: o$5, getPrototypeOf: n$5 } = Object, a$1 = globalThis, c$3 = a$1.trustedTypes, l$1 = c$3 ? c$3.emptyScript : "", p$2 = a$1.reactiveElementPolyfillSupport, d$1 = (t2, s4) => t2, u$3 = { toAttribute(t2, s4) {
  switch (s4) {
    case Boolean:
      t2 = t2 ? l$1 : null;
      break;
    case Object:
    case Array:
      t2 = null == t2 ? t2 : JSON.stringify(t2);
  }
  return t2;
}, fromAttribute(t2, s4) {
  let i4 = t2;
  switch (s4) {
    case Boolean:
      i4 = null !== t2;
      break;
    case Number:
      i4 = null === t2 ? null : Number(t2);
      break;
    case Object:
    case Array:
      try {
        i4 = JSON.parse(t2);
      } catch (t3) {
        i4 = null;
      }
  }
  return i4;
} }, f$1 = (t2, s4) => !i$5(t2, s4), b$1 = { attribute: true, type: String, converter: u$3, reflect: false, useDefault: false, hasChanged: f$1 };
Symbol.metadata ??= /* @__PURE__ */ Symbol("metadata"), a$1.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
let y$1 = class y extends HTMLElement {
  static addInitializer(t2) {
    this._$Ei(), (this.l ??= []).push(t2);
  }
  static get observedAttributes() {
    return this.finalize(), this._$Eh && [...this._$Eh.keys()];
  }
  static createProperty(t2, s4 = b$1) {
    if (s4.state && (s4.attribute = false), this._$Ei(), this.prototype.hasOwnProperty(t2) && ((s4 = Object.create(s4)).wrapped = true), this.elementProperties.set(t2, s4), !s4.noAccessor) {
      const i4 = /* @__PURE__ */ Symbol(), h2 = this.getPropertyDescriptor(t2, i4, s4);
      void 0 !== h2 && e$8(this.prototype, t2, h2);
    }
  }
  static getPropertyDescriptor(t2, s4, i4) {
    const { get: e3, set: r2 } = h$2(this.prototype, t2) ?? { get() {
      return this[s4];
    }, set(t3) {
      this[s4] = t3;
    } };
    return { get: e3, set(s5) {
      const h2 = e3?.call(this);
      r2?.call(this, s5), this.requestUpdate(t2, h2, i4);
    }, configurable: true, enumerable: true };
  }
  static getPropertyOptions(t2) {
    return this.elementProperties.get(t2) ?? b$1;
  }
  static _$Ei() {
    if (this.hasOwnProperty(d$1("elementProperties"))) return;
    const t2 = n$5(this);
    t2.finalize(), void 0 !== t2.l && (this.l = [...t2.l]), this.elementProperties = new Map(t2.elementProperties);
  }
  static finalize() {
    if (this.hasOwnProperty(d$1("finalized"))) return;
    if (this.finalized = true, this._$Ei(), this.hasOwnProperty(d$1("properties"))) {
      const t3 = this.properties, s4 = [...r$4(t3), ...o$5(t3)];
      for (const i4 of s4) this.createProperty(i4, t3[i4]);
    }
    const t2 = this[Symbol.metadata];
    if (null !== t2) {
      const s4 = litPropertyMetadata.get(t2);
      if (void 0 !== s4) for (const [t3, i4] of s4) this.elementProperties.set(t3, i4);
    }
    this._$Eh = /* @__PURE__ */ new Map();
    for (const [t3, s4] of this.elementProperties) {
      const i4 = this._$Eu(t3, s4);
      void 0 !== i4 && this._$Eh.set(i4, t3);
    }
    this.elementStyles = this.finalizeStyles(this.styles);
  }
  static finalizeStyles(s4) {
    const i4 = [];
    if (Array.isArray(s4)) {
      const e3 = new Set(s4.flat(1 / 0).reverse());
      for (const s5 of e3) i4.unshift(c$4(s5));
    } else void 0 !== s4 && i4.push(c$4(s4));
    return i4;
  }
  static _$Eu(t2, s4) {
    const i4 = s4.attribute;
    return false === i4 ? void 0 : "string" == typeof i4 ? i4 : "string" == typeof t2 ? t2.toLowerCase() : void 0;
  }
  constructor() {
    super(), this._$Ep = void 0, this.isUpdatePending = false, this.hasUpdated = false, this._$Em = null, this._$Ev();
  }
  _$Ev() {
    this._$ES = new Promise((t2) => this.enableUpdating = t2), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((t2) => t2(this));
  }
  addController(t2) {
    (this._$EO ??= /* @__PURE__ */ new Set()).add(t2), void 0 !== this.renderRoot && this.isConnected && t2.hostConnected?.();
  }
  removeController(t2) {
    this._$EO?.delete(t2);
  }
  _$E_() {
    const t2 = /* @__PURE__ */ new Map(), s4 = this.constructor.elementProperties;
    for (const i4 of s4.keys()) this.hasOwnProperty(i4) && (t2.set(i4, this[i4]), delete this[i4]);
    t2.size > 0 && (this._$Ep = t2);
  }
  createRenderRoot() {
    const t2 = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
    return S$1(t2, this.constructor.elementStyles), t2;
  }
  connectedCallback() {
    this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(true), this._$EO?.forEach((t2) => t2.hostConnected?.());
  }
  enableUpdating(t2) {
  }
  disconnectedCallback() {
    this._$EO?.forEach((t2) => t2.hostDisconnected?.());
  }
  attributeChangedCallback(t2, s4, i4) {
    this._$AK(t2, i4);
  }
  _$ET(t2, s4) {
    const i4 = this.constructor.elementProperties.get(t2), e3 = this.constructor._$Eu(t2, i4);
    if (void 0 !== e3 && true === i4.reflect) {
      const h2 = (void 0 !== i4.converter?.toAttribute ? i4.converter : u$3).toAttribute(s4, i4.type);
      this._$Em = t2, null == h2 ? this.removeAttribute(e3) : this.setAttribute(e3, h2), this._$Em = null;
    }
  }
  _$AK(t2, s4) {
    const i4 = this.constructor, e3 = i4._$Eh.get(t2);
    if (void 0 !== e3 && this._$Em !== e3) {
      const t3 = i4.getPropertyOptions(e3), h2 = "function" == typeof t3.converter ? { fromAttribute: t3.converter } : void 0 !== t3.converter?.fromAttribute ? t3.converter : u$3;
      this._$Em = e3;
      const r2 = h2.fromAttribute(s4, t3.type);
      this[e3] = r2 ?? this._$Ej?.get(e3) ?? r2, this._$Em = null;
    }
  }
  requestUpdate(t2, s4, i4, e3 = false, h2) {
    if (void 0 !== t2) {
      const r2 = this.constructor;
      if (false === e3 && (h2 = this[t2]), i4 ??= r2.getPropertyOptions(t2), !((i4.hasChanged ?? f$1)(h2, s4) || i4.useDefault && i4.reflect && h2 === this._$Ej?.get(t2) && !this.hasAttribute(r2._$Eu(t2, i4)))) return;
      this.C(t2, s4, i4);
    }
    false === this.isUpdatePending && (this._$ES = this._$EP());
  }
  C(t2, s4, { useDefault: i4, reflect: e3, wrapped: h2 }, r2) {
    i4 && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(t2) && (this._$Ej.set(t2, r2 ?? s4 ?? this[t2]), true !== h2 || void 0 !== r2) || (this._$AL.has(t2) || (this.hasUpdated || i4 || (s4 = void 0), this._$AL.set(t2, s4)), true === e3 && this._$Em !== t2 && (this._$Eq ??= /* @__PURE__ */ new Set()).add(t2));
  }
  async _$EP() {
    this.isUpdatePending = true;
    try {
      await this._$ES;
    } catch (t3) {
      Promise.reject(t3);
    }
    const t2 = this.scheduleUpdate();
    return null != t2 && await t2, !this.isUpdatePending;
  }
  scheduleUpdate() {
    return this.performUpdate();
  }
  performUpdate() {
    if (!this.isUpdatePending) return;
    if (!this.hasUpdated) {
      if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
        for (const [t4, s5] of this._$Ep) this[t4] = s5;
        this._$Ep = void 0;
      }
      const t3 = this.constructor.elementProperties;
      if (t3.size > 0) for (const [s5, i4] of t3) {
        const { wrapped: t4 } = i4, e3 = this[s5];
        true !== t4 || this._$AL.has(s5) || void 0 === e3 || this.C(s5, void 0, i4, e3);
      }
    }
    let t2 = false;
    const s4 = this._$AL;
    try {
      t2 = this.shouldUpdate(s4), t2 ? (this.willUpdate(s4), this._$EO?.forEach((t3) => t3.hostUpdate?.()), this.update(s4)) : this._$EM();
    } catch (s5) {
      throw t2 = false, this._$EM(), s5;
    }
    t2 && this._$AE(s4);
  }
  willUpdate(t2) {
  }
  _$AE(t2) {
    this._$EO?.forEach((t3) => t3.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = true, this.firstUpdated(t2)), this.updated(t2);
  }
  _$EM() {
    this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = false;
  }
  get updateComplete() {
    return this.getUpdateComplete();
  }
  getUpdateComplete() {
    return this._$ES;
  }
  shouldUpdate(t2) {
    return true;
  }
  update(t2) {
    this._$Eq &&= this._$Eq.forEach((t3) => this._$ET(t3, this[t3])), this._$EM();
  }
  updated(t2) {
  }
  firstUpdated(t2) {
  }
};
y$1.elementStyles = [], y$1.shadowRootOptions = { mode: "open" }, y$1[d$1("elementProperties")] = /* @__PURE__ */ new Map(), y$1[d$1("finalized")] = /* @__PURE__ */ new Map(), p$2?.({ ReactiveElement: y$1 }), (a$1.reactiveElementVersions ??= []).push("2.1.2");
const t$2 = globalThis, i$4 = (t2) => t2, s$5 = t$2.trustedTypes, e$7 = s$5 ? s$5.createPolicy("lit-html", { createHTML: (t2) => t2 }) : void 0, h$1 = "$lit$", o$4 = `lit$${Math.random().toFixed(9).slice(2)}$`, n$4 = "?" + o$4, r$3 = `<${n$4}>`, l = document, c$2 = () => l.createComment(""), a = (t2) => null === t2 || "object" != typeof t2 && "function" != typeof t2, u$2 = Array.isArray, d = (t2) => u$2(t2) || "function" == typeof t2?.[Symbol.iterator], f = "[ 	\n\f\r]", v$1 = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, _ = /-->/g, m$1 = />/g, p$1 = RegExp(`>|${f}(?:([^\\s"'>=/]+)(${f}*=${f}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`, "g"), g = /'/g, $ = /"/g, y2 = /^(?:script|style|textarea|title)$/i, x = (t2) => (i4, ...s4) => ({ _$litType$: t2, strings: i4, values: s4 }), b = x(1), w = x(2), E = /* @__PURE__ */ Symbol.for("lit-noChange"), A = /* @__PURE__ */ Symbol.for("lit-nothing"), C = /* @__PURE__ */ new WeakMap(), P = l.createTreeWalker(l, 129);
function V(t2, i4) {
  if (!u$2(t2) || !t2.hasOwnProperty("raw")) throw Error("invalid template strings array");
  return void 0 !== e$7 ? e$7.createHTML(i4) : i4;
}
const N = (t2, i4) => {
  const s4 = t2.length - 1, e3 = [];
  let n3, l2 = 2 === i4 ? "<svg>" : 3 === i4 ? "<math>" : "", c2 = v$1;
  for (let i5 = 0; i5 < s4; i5++) {
    const s5 = t2[i5];
    let a2, u2, d2 = -1, f2 = 0;
    for (; f2 < s5.length && (c2.lastIndex = f2, u2 = c2.exec(s5), null !== u2); ) f2 = c2.lastIndex, c2 === v$1 ? "!--" === u2[1] ? c2 = _ : void 0 !== u2[1] ? c2 = m$1 : void 0 !== u2[2] ? (y2.test(u2[2]) && (n3 = RegExp("</" + u2[2], "g")), c2 = p$1) : void 0 !== u2[3] && (c2 = p$1) : c2 === p$1 ? ">" === u2[0] ? (c2 = n3 ?? v$1, d2 = -1) : void 0 === u2[1] ? d2 = -2 : (d2 = c2.lastIndex - u2[2].length, a2 = u2[1], c2 = void 0 === u2[3] ? p$1 : '"' === u2[3] ? $ : g) : c2 === $ || c2 === g ? c2 = p$1 : c2 === _ || c2 === m$1 ? c2 = v$1 : (c2 = p$1, n3 = void 0);
    const x2 = c2 === p$1 && t2[i5 + 1].startsWith("/>") ? " " : "";
    l2 += c2 === v$1 ? s5 + r$3 : d2 >= 0 ? (e3.push(a2), s5.slice(0, d2) + h$1 + s5.slice(d2) + o$4 + x2) : s5 + o$4 + (-2 === d2 ? i5 : x2);
  }
  return [V(t2, l2 + (t2[s4] || "<?>") + (2 === i4 ? "</svg>" : 3 === i4 ? "</math>" : "")), e3];
};
class S {
  constructor({ strings: t2, _$litType$: i4 }, e3) {
    let r2;
    this.parts = [];
    let l2 = 0, a2 = 0;
    const u2 = t2.length - 1, d2 = this.parts, [f2, v2] = N(t2, i4);
    if (this.el = S.createElement(f2, e3), P.currentNode = this.el.content, 2 === i4 || 3 === i4) {
      const t3 = this.el.content.firstChild;
      t3.replaceWith(...t3.childNodes);
    }
    for (; null !== (r2 = P.nextNode()) && d2.length < u2; ) {
      if (1 === r2.nodeType) {
        if (r2.hasAttributes()) for (const t3 of r2.getAttributeNames()) if (t3.endsWith(h$1)) {
          const i5 = v2[a2++], s4 = r2.getAttribute(t3).split(o$4), e4 = /([.?@])?(.*)/.exec(i5);
          d2.push({ type: 1, index: l2, name: e4[2], strings: s4, ctor: "." === e4[1] ? I : "?" === e4[1] ? L : "@" === e4[1] ? z : H }), r2.removeAttribute(t3);
        } else t3.startsWith(o$4) && (d2.push({ type: 6, index: l2 }), r2.removeAttribute(t3));
        if (y2.test(r2.tagName)) {
          const t3 = r2.textContent.split(o$4), i5 = t3.length - 1;
          if (i5 > 0) {
            r2.textContent = s$5 ? s$5.emptyScript : "";
            for (let s4 = 0; s4 < i5; s4++) r2.append(t3[s4], c$2()), P.nextNode(), d2.push({ type: 2, index: ++l2 });
            r2.append(t3[i5], c$2());
          }
        }
      } else if (8 === r2.nodeType) if (r2.data === n$4) d2.push({ type: 2, index: l2 });
      else {
        let t3 = -1;
        for (; -1 !== (t3 = r2.data.indexOf(o$4, t3 + 1)); ) d2.push({ type: 7, index: l2 }), t3 += o$4.length - 1;
      }
      l2++;
    }
  }
  static createElement(t2, i4) {
    const s4 = l.createElement("template");
    return s4.innerHTML = t2, s4;
  }
}
function M$1(t2, i4, s4 = t2, e3) {
  if (i4 === E) return i4;
  let h2 = void 0 !== e3 ? s4._$Co?.[e3] : s4._$Cl;
  const o2 = a(i4) ? void 0 : i4._$litDirective$;
  return h2?.constructor !== o2 && (h2?._$AO?.(false), void 0 === o2 ? h2 = void 0 : (h2 = new o2(t2), h2._$AT(t2, s4, e3)), void 0 !== e3 ? (s4._$Co ??= [])[e3] = h2 : s4._$Cl = h2), void 0 !== h2 && (i4 = M$1(t2, h2._$AS(t2, i4.values), h2, e3)), i4;
}
class R {
  constructor(t2, i4) {
    this._$AV = [], this._$AN = void 0, this._$AD = t2, this._$AM = i4;
  }
  get parentNode() {
    return this._$AM.parentNode;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  u(t2) {
    const { el: { content: i4 }, parts: s4 } = this._$AD, e3 = (t2?.creationScope ?? l).importNode(i4, true);
    P.currentNode = e3;
    let h2 = P.nextNode(), o2 = 0, n3 = 0, r2 = s4[0];
    for (; void 0 !== r2; ) {
      if (o2 === r2.index) {
        let i5;
        2 === r2.type ? i5 = new k(h2, h2.nextSibling, this, t2) : 1 === r2.type ? i5 = new r2.ctor(h2, r2.name, r2.strings, this, t2) : 6 === r2.type && (i5 = new Z(h2, this, t2)), this._$AV.push(i5), r2 = s4[++n3];
      }
      o2 !== r2?.index && (h2 = P.nextNode(), o2++);
    }
    return P.currentNode = l, e3;
  }
  p(t2) {
    let i4 = 0;
    for (const s4 of this._$AV) void 0 !== s4 && (void 0 !== s4.strings ? (s4._$AI(t2, s4, i4), i4 += s4.strings.length - 2) : s4._$AI(t2[i4])), i4++;
  }
}
class k {
  get _$AU() {
    return this._$AM?._$AU ?? this._$Cv;
  }
  constructor(t2, i4, s4, e3) {
    this.type = 2, this._$AH = A, this._$AN = void 0, this._$AA = t2, this._$AB = i4, this._$AM = s4, this.options = e3, this._$Cv = e3?.isConnected ?? true;
  }
  get parentNode() {
    let t2 = this._$AA.parentNode;
    const i4 = this._$AM;
    return void 0 !== i4 && 11 === t2?.nodeType && (t2 = i4.parentNode), t2;
  }
  get startNode() {
    return this._$AA;
  }
  get endNode() {
    return this._$AB;
  }
  _$AI(t2, i4 = this) {
    t2 = M$1(this, t2, i4), a(t2) ? t2 === A || null == t2 || "" === t2 ? (this._$AH !== A && this._$AR(), this._$AH = A) : t2 !== this._$AH && t2 !== E && this._(t2) : void 0 !== t2._$litType$ ? this.$(t2) : void 0 !== t2.nodeType ? this.T(t2) : d(t2) ? this.k(t2) : this._(t2);
  }
  O(t2) {
    return this._$AA.parentNode.insertBefore(t2, this._$AB);
  }
  T(t2) {
    this._$AH !== t2 && (this._$AR(), this._$AH = this.O(t2));
  }
  _(t2) {
    this._$AH !== A && a(this._$AH) ? this._$AA.nextSibling.data = t2 : this.T(l.createTextNode(t2)), this._$AH = t2;
  }
  $(t2) {
    const { values: i4, _$litType$: s4 } = t2, e3 = "number" == typeof s4 ? this._$AC(t2) : (void 0 === s4.el && (s4.el = S.createElement(V(s4.h, s4.h[0]), this.options)), s4);
    if (this._$AH?._$AD === e3) this._$AH.p(i4);
    else {
      const t3 = new R(e3, this), s5 = t3.u(this.options);
      t3.p(i4), this.T(s5), this._$AH = t3;
    }
  }
  _$AC(t2) {
    let i4 = C.get(t2.strings);
    return void 0 === i4 && C.set(t2.strings, i4 = new S(t2)), i4;
  }
  k(t2) {
    u$2(this._$AH) || (this._$AH = [], this._$AR());
    const i4 = this._$AH;
    let s4, e3 = 0;
    for (const h2 of t2) e3 === i4.length ? i4.push(s4 = new k(this.O(c$2()), this.O(c$2()), this, this.options)) : s4 = i4[e3], s4._$AI(h2), e3++;
    e3 < i4.length && (this._$AR(s4 && s4._$AB.nextSibling, e3), i4.length = e3);
  }
  _$AR(t2 = this._$AA.nextSibling, s4) {
    for (this._$AP?.(false, true, s4); t2 !== this._$AB; ) {
      const s5 = i$4(t2).nextSibling;
      i$4(t2).remove(), t2 = s5;
    }
  }
  setConnected(t2) {
    void 0 === this._$AM && (this._$Cv = t2, this._$AP?.(t2));
  }
}
class H {
  get tagName() {
    return this.element.tagName;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  constructor(t2, i4, s4, e3, h2) {
    this.type = 1, this._$AH = A, this._$AN = void 0, this.element = t2, this.name = i4, this._$AM = e3, this.options = h2, s4.length > 2 || "" !== s4[0] || "" !== s4[1] ? (this._$AH = Array(s4.length - 1).fill(new String()), this.strings = s4) : this._$AH = A;
  }
  _$AI(t2, i4 = this, s4, e3) {
    const h2 = this.strings;
    let o2 = false;
    if (void 0 === h2) t2 = M$1(this, t2, i4, 0), o2 = !a(t2) || t2 !== this._$AH && t2 !== E, o2 && (this._$AH = t2);
    else {
      const e4 = t2;
      let n3, r2;
      for (t2 = h2[0], n3 = 0; n3 < h2.length - 1; n3++) r2 = M$1(this, e4[s4 + n3], i4, n3), r2 === E && (r2 = this._$AH[n3]), o2 ||= !a(r2) || r2 !== this._$AH[n3], r2 === A ? t2 = A : t2 !== A && (t2 += (r2 ?? "") + h2[n3 + 1]), this._$AH[n3] = r2;
    }
    o2 && !e3 && this.j(t2);
  }
  j(t2) {
    t2 === A ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, t2 ?? "");
  }
}
class I extends H {
  constructor() {
    super(...arguments), this.type = 3;
  }
  j(t2) {
    this.element[this.name] = t2 === A ? void 0 : t2;
  }
}
class L extends H {
  constructor() {
    super(...arguments), this.type = 4;
  }
  j(t2) {
    this.element.toggleAttribute(this.name, !!t2 && t2 !== A);
  }
}
class z extends H {
  constructor(t2, i4, s4, e3, h2) {
    super(t2, i4, s4, e3, h2), this.type = 5;
  }
  _$AI(t2, i4 = this) {
    if ((t2 = M$1(this, t2, i4, 0) ?? A) === E) return;
    const s4 = this._$AH, e3 = t2 === A && s4 !== A || t2.capture !== s4.capture || t2.once !== s4.once || t2.passive !== s4.passive, h2 = t2 !== A && (s4 === A || e3);
    e3 && this.element.removeEventListener(this.name, this, s4), h2 && this.element.addEventListener(this.name, this, t2), this._$AH = t2;
  }
  handleEvent(t2) {
    "function" == typeof this._$AH ? this._$AH.call(this.options?.host ?? this.element, t2) : this._$AH.handleEvent(t2);
  }
}
class Z {
  constructor(t2, i4, s4) {
    this.element = t2, this.type = 6, this._$AN = void 0, this._$AM = i4, this.options = s4;
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AI(t2) {
    M$1(this, t2);
  }
}
const j = { I: k }, B = t$2.litHtmlPolyfillSupport;
B?.(S, k), (t$2.litHtmlVersions ??= []).push("3.3.2");
const D = (t2, i4, s4) => {
  const e3 = s4?.renderBefore ?? i4;
  let h2 = e3._$litPart$;
  if (void 0 === h2) {
    const t3 = s4?.renderBefore ?? null;
    e3._$litPart$ = h2 = new k(i4.insertBefore(c$2(), t3), t3, void 0, s4 ?? {});
  }
  return h2._$AI(t2), h2;
};
const s$4 = globalThis;
let i$3 = class i extends y$1 {
  constructor() {
    super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
  }
  createRenderRoot() {
    const t2 = super.createRenderRoot();
    return this.renderOptions.renderBefore ??= t2.firstChild, t2;
  }
  update(t2) {
    const r2 = this.render();
    this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(t2), this._$Do = D(r2, this.renderRoot, this.renderOptions);
  }
  connectedCallback() {
    super.connectedCallback(), this._$Do?.setConnected(true);
  }
  disconnectedCallback() {
    super.disconnectedCallback(), this._$Do?.setConnected(false);
  }
  render() {
    return E;
  }
};
i$3._$litElement$ = true, i$3["finalized"] = true, s$4.litElementHydrateSupport?.({ LitElement: i$3 });
const o$3 = s$4.litElementPolyfillSupport;
o$3?.({ LitElement: i$3 });
(s$4.litElementVersions ??= []).push("4.2.2");
const o$2 = { attribute: true, type: String, converter: u$3, reflect: false, hasChanged: f$1 }, r$2 = (t2 = o$2, e3, r2) => {
  const { kind: n3, metadata: i4 } = r2;
  let s4 = globalThis.litPropertyMetadata.get(i4);
  if (void 0 === s4 && globalThis.litPropertyMetadata.set(i4, s4 = /* @__PURE__ */ new Map()), "setter" === n3 && ((t2 = Object.create(t2)).wrapped = true), s4.set(r2.name, t2), "accessor" === n3) {
    const { name: o2 } = r2;
    return { set(r3) {
      const n4 = e3.get.call(this);
      e3.set.call(this, r3), this.requestUpdate(o2, n4, t2, true, r3);
    }, init(e4) {
      return void 0 !== e4 && this.C(o2, void 0, t2, e4), e4;
    } };
  }
  if ("setter" === n3) {
    const { name: o2 } = r2;
    return function(r3) {
      const n4 = this[o2];
      e3.call(this, r3), this.requestUpdate(o2, n4, t2, true, r3);
    };
  }
  throw Error("Unsupported decorator location: " + n3);
};
function n$3(t2) {
  return (e3, o2) => "object" == typeof o2 ? r$2(t2, e3, o2) : ((t3, e4, o3) => {
    const r2 = e4.hasOwnProperty(o3);
    return e4.constructor.createProperty(o3, t3), r2 ? Object.getOwnPropertyDescriptor(e4, o3) : void 0;
  })(t2, e3, o2);
}
function r$1(r2) {
  return n$3({ ...r2, state: true, attribute: false });
}
const e$6 = (e3, t2, c2) => (c2.configurable = true, c2.enumerable = true, Reflect.decorate && "object" != typeof t2 && Object.defineProperty(e3, t2, c2), c2);
function e$5(e3, r2) {
  return (n3, s4, i4) => {
    const o2 = (t2) => t2.renderRoot?.querySelector(e3) ?? null;
    if (r2) {
      const { get: e4, set: r3 } = "object" == typeof s4 ? n3 : i4 ?? /* @__PURE__ */ (() => {
        const t2 = /* @__PURE__ */ Symbol();
        return { get() {
          return this[t2];
        }, set(e5) {
          this[t2] = e5;
        } };
      })();
      return e$6(n3, s4, { get() {
        let t2 = e4.call(this);
        return void 0 === t2 && (t2 = o2(this), (null !== t2 || this.hasUpdated) && r3.call(this, t2)), t2;
      } });
    }
    return e$6(n3, s4, { get() {
      return o2(this);
    } });
  };
}
let e$4;
function r(r2) {
  return (n3, o2) => e$6(n3, o2, { get() {
    return (this.renderRoot ?? (e$4 ??= document.createDocumentFragment())).querySelectorAll(r2);
  } });
}
function o$1(o2) {
  return (e3, n3) => {
    const { slot: r2, selector: s4 } = o2 ?? {}, c2 = "slot" + (r2 ? `[name=${r2}]` : ":not([name])");
    return e$6(e3, n3, { get() {
      const t2 = this.renderRoot?.querySelector(c2), e4 = t2?.assignedElements(o2) ?? [];
      return void 0 === s4 ? e4 : e4.filter((t3) => t3.matches(s4));
    } });
  };
}
function n$2(n3) {
  return (o2, r2) => {
    const { slot: e3 } = {}, s4 = "slot" + (e3 ? `[name=${e3}]` : ":not([name])");
    return e$6(o2, r2, { get() {
      const t2 = this.renderRoot?.querySelector(s4);
      return t2?.assignedNodes(n3) ?? [];
    } });
  };
}
const VERSION = "2.5.0";
const CONFIG_KEY = "__vscodeElements_disableRegistryWarning__";
const warn = (message, componentInstance) => {
  const prefix = "[VSCode Elements] ";
  if (componentInstance) {
    console.warn(`${prefix}${message}
%o`, componentInstance);
  } else {
    console.warn(`${message}
%o`, componentInstance);
  }
};
class VscElement extends i$3 {
  /** VSCode Elements version */
  get version() {
    return VERSION;
  }
  warn(message) {
    warn(message, this);
  }
}
const customElement = (tagName) => {
  return (classOrTarget) => {
    const customElementClass = customElements.get(tagName);
    if (!customElementClass) {
      customElements.define(tagName, classOrTarget);
      return;
    }
    if (CONFIG_KEY in window) {
      return;
    }
    const el = document.createElement(tagName);
    const anotherVersion = el?.version;
    let message = "";
    if (!anotherVersion) {
      message += "is already registered by an unknown custom element handler class.";
    } else if (anotherVersion !== VERSION) {
      message += "is already registered by a different version of VSCode Elements. ";
      message += `This version is "${VERSION}", while the other one is "${anotherVersion}".`;
    } else {
      message += `is already registered by the same version of VSCode Elements (${VERSION}).`;
    }
    warn(`The custom element "${tagName}" ${message}
To suppress this warning, set window.${CONFIG_KEY} to true`);
  };
};
const defaultStyles = i$6`
  :host([hidden]) {
    display: none;
  }

  :host([disabled]),
  :host(:disabled) {
    cursor: not-allowed;
    opacity: 0.4;
    pointer-events: none;
  }
`;
const DEFAULT_LINE_HEIGHT = 16;
const DEFAULT_FONT_SIZE = 13;
const INPUT_LINE_HEIGHT_RATIO = DEFAULT_LINE_HEIGHT / DEFAULT_FONT_SIZE;
function getDefaultFontStack() {
  if (navigator.userAgent.indexOf("Linux") > -1) {
    return 'system-ui, "Ubuntu", "Droid Sans", sans-serif';
  } else if (navigator.userAgent.indexOf("Mac") > -1) {
    return "-apple-system, BlinkMacSystemFont, sans-serif";
  } else if (navigator.userAgent.indexOf("Windows") > -1) {
    return '"Segoe WPC", "Segoe UI", sans-serif';
  } else {
    return "sans-serif";
  }
}
const defaultFontStack$2 = r$5(getDefaultFontStack());
const styles$z = [
  defaultStyles,
  i$6`
    :host {
      display: inline-block;
    }

    .root {
      background-color: var(--vscode-badge-background, #616161);
      border: 1px solid var(--vscode-contrastBorder, transparent);
      border-radius: 2px;
      box-sizing: border-box;
      color: var(--vscode-badge-foreground, #f8f8f8);
      display: block;
      font-family: var(--vscode-font-family, ${defaultFontStack$2});
      font-size: 11px;
      font-weight: 400;
      line-height: 14px;
      min-width: 18px;
      padding: 2px 3px;
      text-align: center;
      white-space: nowrap;
    }

    :host([variant='counter']) .root {
      border-radius: 11px;
      line-height: 11px;
      min-height: 18px;
      min-width: 18px;
      padding: 3px 6px;
    }

    :host([variant='activity-bar-counter']) .root {
      background-color: var(--vscode-activityBarBadge-background, #0078d4);
      border-radius: 20px;
      color: var(--vscode-activityBarBadge-foreground, #ffffff);
      font-size: 9px;
      font-weight: 600;
      line-height: 16px;
      padding: 0 4px;
    }

    :host([variant='tab-header-counter']) .root {
      background-color: var(--vscode-activityBarBadge-background, #0078d4);
      border-radius: 10px;
      color: var(--vscode-activityBarBadge-foreground, #ffffff);
      line-height: 10px;
      min-height: 16px;
      min-width: 16px;
      padding: 3px 5px;
    }
  `
];
var __decorate$E = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeBadge = class VscodeBadge2 extends VscElement {
  constructor() {
    super(...arguments);
    this.variant = "default";
  }
  render() {
    return b`<div class="root"><slot></slot></div>`;
  }
};
VscodeBadge.styles = styles$z;
__decorate$E([
  n$3({ reflect: true })
], VscodeBadge.prototype, "variant", void 0);
VscodeBadge = __decorate$E([
  customElement("vscode-badge")
], VscodeBadge);
o$7({
  tagName: "vscode-badge",
  elementClass: VscodeBadge,
  react: E$1,
  displayName: "VscodeBadge"
});
const t$1 = { ATTRIBUTE: 1, CHILD: 2, PROPERTY: 3 }, e$3 = (t2) => (...e3) => ({ _$litDirective$: t2, values: e3 });
let i$2 = class i2 {
  constructor(t2) {
  }
  get _$AU() {
    return this._$AM._$AU;
  }
  _$AT(t2, e3, i4) {
    this._$Ct = t2, this._$AM = e3, this._$Ci = i4;
  }
  _$AS(t2, e3) {
    return this.update(t2, e3);
  }
  update(t2, e3) {
    return this.render(...e3);
  }
};
const e$2 = e$3(class extends i$2 {
  constructor(t2) {
    if (super(t2), t2.type !== t$1.ATTRIBUTE || "class" !== t2.name || t2.strings?.length > 2) throw Error("`classMap()` can only be used in the `class` attribute and must be the only part in the attribute.");
  }
  render(t2) {
    return " " + Object.keys(t2).filter((s4) => t2[s4]).join(" ") + " ";
  }
  update(s4, [i4]) {
    if (void 0 === this.st) {
      this.st = /* @__PURE__ */ new Set(), void 0 !== s4.strings && (this.nt = new Set(s4.strings.join(" ").split(/\s/).filter((t2) => "" !== t2)));
      for (const t2 in i4) i4[t2] && !this.nt?.has(t2) && this.st.add(t2);
      return this.render(i4);
    }
    const r2 = s4.element.classList;
    for (const t2 of this.st) t2 in i4 || (r2.remove(t2), this.st.delete(t2));
    for (const t2 in i4) {
      const s5 = !!i4[t2];
      s5 === this.st.has(t2) || this.nt?.has(t2) || (s5 ? (r2.add(t2), this.st.add(t2)) : (r2.remove(t2), this.st.delete(t2)));
    }
    return E;
  }
});
const o = (o2) => o2 ?? A;
class StylePropertyMap extends i$2 {
  constructor(partInfo) {
    super(partInfo);
    this._prevProperties = {};
    if (partInfo.type !== t$1.PROPERTY || partInfo.name !== "style") {
      throw new Error("The `stylePropertyMap` directive must be used in the `style` property");
    }
  }
  update(part, [styleProps]) {
    Object.entries(styleProps).forEach(([key, val]) => {
      if (this._prevProperties[key] !== val) {
        if (key.startsWith("--")) {
          part.element.style.setProperty(key, val);
        } else {
          part.element.style[key] = val;
        }
        this._prevProperties[key] = val;
      }
    });
    return E;
  }
  render(_styleProps) {
    return E;
  }
}
const stylePropertyMap = e$3(StylePropertyMap);
const styles$y = [
  defaultStyles,
  i$6`
    :host {
      color: var(--vscode-icon-foreground, #cccccc);
      display: inline-block;
    }

    .codicon[class*='codicon-'] {
      display: block;
    }

    .icon,
    .button {
      background-color: transparent;
      display: block;
      padding: 0;
    }

    .button {
      border-color: transparent;
      border-style: solid;
      border-width: 1px;
      border-radius: 5px;
      color: currentColor;
      cursor: pointer;
      padding: 2px;
    }

    .button:hover {
      background-color: var(
        --vscode-toolbar-hoverBackground,
        rgba(90, 93, 94, 0.31)
      );
    }

    .button:active {
      background-color: var(
        --vscode-toolbar-activeBackground,
        rgba(99, 102, 103, 0.31)
      );
    }

    .button:focus {
      outline: none;
    }

    .button:focus-visible {
      border-color: var(--vscode-focusBorder, #0078d4);
    }

    @keyframes icon-spin {
      100% {
        transform: rotate(360deg);
      }
    }

    .spin {
      animation-name: icon-spin;
      animation-timing-function: linear;
      animation-iteration-count: infinite;
    }
  `
];
var __decorate$D = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
var VscodeIcon_1;
let VscodeIcon = VscodeIcon_1 = class VscodeIcon2 extends VscElement {
  constructor() {
    super(...arguments);
    this.label = "";
    this.name = "";
    this.size = 16;
    this.spin = false;
    this.spinDuration = 1.5;
    this.actionIcon = false;
    this._onButtonClick = (ev) => {
      this.dispatchEvent(new CustomEvent("vsc-click", { detail: { originalEvent: ev } }));
    };
  }
  connectedCallback() {
    super.connectedCallback();
    const { href, nonce } = this._getStylesheetConfig();
    VscodeIcon_1.stylesheetHref = href;
    VscodeIcon_1.nonce = nonce;
  }
  /**
   * For using web fonts in web components, the font stylesheet must be included
   * twice: on the page and in the web component. This function looks for the
   * font stylesheet on the page and returns the stylesheet URL and the nonce
   * id.
   */
  _getStylesheetConfig() {
    const linkElement = document.getElementById("vscode-codicon-stylesheet");
    const href = linkElement?.getAttribute("href") || void 0;
    const nonce = linkElement?.nonce || void 0;
    if (!linkElement) {
      let msg = 'To use the Icon component, the codicons.css file must be included in the page with the id "vscode-codicon-stylesheet"! ';
      msg += "See https://vscode-elements.github.io/components/icon/ for more details.";
      this.warn(msg);
    }
    return { nonce, href };
  }
  render() {
    const { stylesheetHref, nonce } = VscodeIcon_1;
    const content = b`<span
      class=${e$2({
      codicon: true,
      ["codicon-" + this.name]: true,
      spin: this.spin
    })}
      .style=${stylePropertyMap({
      animationDuration: String(this.spinDuration) + "s",
      fontSize: this.size + "px",
      height: this.size + "px",
      width: this.size + "px"
    })}
    ></span>`;
    const wrapped = this.actionIcon ? b` <button
          class="button"
          @click=${this._onButtonClick}
          aria-label=${this.label}
        >
          ${content}
        </button>` : b` <span class="icon" aria-hidden="true" role="presentation"
          >${content}</span
        >`;
    return b`
      <link
        rel="stylesheet"
        href=${o(stylesheetHref)}
        nonce=${o(nonce)}
      />
      ${wrapped}
    `;
  }
};
VscodeIcon.styles = styles$y;
VscodeIcon.stylesheetHref = "";
VscodeIcon.nonce = "";
__decorate$D([
  n$3()
], VscodeIcon.prototype, "label", void 0);
__decorate$D([
  n$3({ type: String })
], VscodeIcon.prototype, "name", void 0);
__decorate$D([
  n$3({ type: Number })
], VscodeIcon.prototype, "size", void 0);
__decorate$D([
  n$3({ type: Boolean, reflect: true })
], VscodeIcon.prototype, "spin", void 0);
__decorate$D([
  n$3({ type: Number, attribute: "spin-duration" })
], VscodeIcon.prototype, "spinDuration", void 0);
__decorate$D([
  n$3({ type: Boolean, reflect: true, attribute: "action-icon" })
], VscodeIcon.prototype, "actionIcon", void 0);
VscodeIcon = VscodeIcon_1 = __decorate$D([
  customElement("vscode-icon")
], VscodeIcon);
const defaultFontStack$1 = r$5(getDefaultFontStack());
const styles$x = [
  defaultStyles,
  i$6`
    :host {
      cursor: pointer;
      display: inline-block;
      width: auto;
    }

    :host([block]) {
      display: block;
      width: 100%;
    }

    .base {
      align-items: center;
      background-color: var(--vscode-button-background, #0078d4);
      border-bottom-left-radius: var(--vsc-border-left-radius, 4px);
      border-bottom-right-radius: var(--vsc-border-right-radius, 4px);
      border-bottom-width: 1px;
      border-color: var(--vscode-button-border, transparent);
      border-left-width: var(--vsc-border-left-width, 1px);
      border-right-width: var(--vsc-border-right-width, 1px);
      border-style: solid;
      border-top-left-radius: var(--vsc-border-left-radius, 4px);
      border-top-right-radius: var(--vsc-border-right-radius, 4px);
      border-top-width: 1px;
      box-sizing: border-box;
      color: var(--vscode-button-foreground, #ffffff);
      display: flex;
      font-family: var(--vscode-font-family, ${defaultFontStack$1});
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      height: 100%;
      justify-content: center;
      line-height: 22px;
      overflow: hidden;
      padding: 1px calc(13px + var(--vsc-base-additional-right-padding, 0px))
        1px 13px;
      position: relative;
      user-select: none;
      white-space: nowrap;
      width: 100%;
    }

    :host([block]) .base {
      min-height: 28px;
      text-align: center;
      width: 100%;
    }

    .base:after {
      background-color: var(
        --vscode-button-separator,
        rgba(255, 255, 255, 0.4)
      );
      content: var(--vsc-base-after-content);
      display: var(--vsc-divider-display, none);
      position: absolute;
      right: 0;
      top: 4px;
      bottom: 4px;
      width: 1px;
    }

    :host([secondary]) .base:after {
      background-color: var(--vscode-button-secondaryForeground, #cccccc);
      opacity: 0.4;
    }

    :host([secondary]) .base {
      color: var(--vscode-button-secondaryForeground, #cccccc);
      background-color: var(--vscode-button-secondaryBackground, #313131);
      border-color: var(
        --vscode-button-border,
        var(--vscode-button-secondaryBackground, rgba(255, 255, 255, 0.07))
      );
    }

    :host([disabled]) {
      cursor: default;
      opacity: 0.4;
      pointer-events: none;
    }

    :host(:hover) .base {
      background-color: var(--vscode-button-hoverBackground, #026ec1);
    }

    :host([disabled]:hover) .base {
      background-color: var(--vscode-button-background, #0078d4);
    }

    :host([secondary]:hover) .base {
      background-color: var(--vscode-button-secondaryHoverBackground, #3c3c3c);
    }

    :host([secondary][disabled]:hover) .base {
      background-color: var(--vscode-button-secondaryBackground, #313131);
    }

    :host(:focus),
    :host(:active) {
      outline: none;
    }

    :host(:focus) .base {
      background-color: var(--vscode-button-hoverBackground, #026ec1);
      outline: 1px solid var(--vscode-focusBorder, #0078d4);
      outline-offset: 2px;
    }

    :host([disabled]:focus) .base {
      background-color: var(--vscode-button-background, #0078d4);
      outline: 0;
    }

    :host([secondary]:focus) .base {
      background-color: var(--vscode-button-secondaryHoverBackground, #3c3c3c);
    }

    :host([secondary][disabled]:focus) .base {
      background-color: var(--vscode-button-secondaryBackground, #313131);
    }

    ::slotted(*) {
      display: inline-block;
      margin-left: 4px;
      margin-right: 4px;
    }

    ::slotted(*:first-child) {
      margin-left: 0;
    }

    ::slotted(*:last-child) {
      margin-right: 0;
    }

    ::slotted(vscode-icon) {
      color: inherit;
    }

    .content {
      display: flex;
      position: relative;
      width: 100%;
      height: 100%;
      padding: 1px 13px;
    }

    :host(:empty) .base,
    .base.icon-only {
      min-height: 24px;
      min-width: 26px;
      padding: 1px 4px;
    }

    slot {
      align-items: center;
      display: flex;
      height: 100%;
    }

    .has-content-before slot[name='content-before'] {
      margin-right: 4px;
    }

    .has-content-after slot[name='content-after'] {
      margin-left: 4px;
    }

    .icon,
    .icon-after {
      color: inherit;
      display: block;
    }

    :host(:not(:empty)) .icon {
      margin-right: 3px;
    }

    :host(:not(:empty)) .icon-after,
    :host([icon]) .icon-after {
      margin-left: 3px;
    }
  `
];
var __decorate$C = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeButton$1 = class VscodeButton extends VscElement {
  get form() {
    return this._internals.form;
  }
  constructor() {
    super();
    this.autofocus = false;
    this.tabIndex = 0;
    this.secondary = false;
    this.block = false;
    this.role = "button";
    this.disabled = false;
    this.icon = "";
    this.iconSpin = false;
    this.iconAfter = "";
    this.iconAfterSpin = false;
    this.focused = false;
    this.name = void 0;
    this.iconOnly = false;
    this.type = "button";
    this.value = "";
    this._prevTabindex = 0;
    this._hasContentBefore = false;
    this._hasContentAfter = false;
    this._handleFocus = () => {
      this.focused = true;
    };
    this._handleBlur = () => {
      this.focused = false;
    };
    this.addEventListener("keydown", this._handleKeyDown.bind(this));
    this.addEventListener("click", this._handleClick.bind(this));
    this._internals = this.attachInternals();
  }
  connectedCallback() {
    super.connectedCallback();
    if (this.autofocus) {
      if (this.tabIndex < 0) {
        this.tabIndex = 0;
      }
      this.updateComplete.then(() => {
        this.focus();
        this.requestUpdate();
      });
    }
    this.addEventListener("focus", this._handleFocus);
    this.addEventListener("blur", this._handleBlur);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("focus", this._handleFocus);
    this.removeEventListener("blur", this._handleBlur);
  }
  update(changedProperties) {
    super.update(changedProperties);
    if (changedProperties.has("value")) {
      this._internals.setFormValue(this.value);
    }
    if (changedProperties.has("disabled")) {
      if (this.disabled) {
        this._prevTabindex = this.tabIndex;
        this.tabIndex = -1;
      } else {
        this.tabIndex = this._prevTabindex;
      }
    }
  }
  _executeAction() {
    if (this.type === "submit" && this._internals.form) {
      this._internals.form.requestSubmit();
    }
    if (this.type === "reset" && this._internals.form) {
      this._internals.form.reset();
    }
  }
  _handleKeyDown(event) {
    if ((event.key === "Enter" || event.key === " ") && !this.hasAttribute("disabled")) {
      const syntheticClick = new MouseEvent("click", {
        bubbles: true,
        cancelable: true
      });
      syntheticClick.synthetic = true;
      this.dispatchEvent(syntheticClick);
      this._executeAction();
    }
  }
  _handleClick(event) {
    if (event.synthetic) {
      return;
    }
    if (!this.hasAttribute("disabled")) {
      this._executeAction();
    }
  }
  _handleSlotChange(ev) {
    const slot = ev.target;
    if (slot.name === "content-before") {
      this._hasContentBefore = slot.assignedElements().length > 0;
    }
    if (slot.name === "content-after") {
      this._hasContentAfter = slot.assignedElements().length > 0;
    }
  }
  render() {
    const hasIcon = this.icon !== "";
    const hasIconAfter = this.iconAfter !== "";
    const baseClasses = {
      base: true,
      "icon-only": this.iconOnly,
      "has-content-before": this._hasContentBefore,
      "has-content-after": this._hasContentAfter
    };
    const iconElem = hasIcon ? b`<vscode-icon
          name=${this.icon}
          ?spin=${this.iconSpin}
          spin-duration=${o(this.iconSpinDuration)}
          class="icon"
        ></vscode-icon>` : A;
    const iconAfterElem = hasIconAfter ? b`<vscode-icon
          name=${this.iconAfter}
          ?spin=${this.iconAfterSpin}
          spin-duration=${o(this.iconAfterSpinDuration)}
          class="icon-after"
        ></vscode-icon>` : A;
    return b`
      <div
        class=${e$2(baseClasses)}
        part="base"
        @slotchange=${this._handleSlotChange}
      >
        <slot name="content-before"></slot>
        ${iconElem}
        <slot></slot>
        ${iconAfterElem}
        <slot name="content-after"></slot>
      </div>
    `;
  }
};
VscodeButton$1.styles = styles$x;
VscodeButton$1.formAssociated = true;
__decorate$C([
  n$3({ type: Boolean, reflect: true })
], VscodeButton$1.prototype, "autofocus", void 0);
__decorate$C([
  n$3({ type: Number, reflect: true })
], VscodeButton$1.prototype, "tabIndex", void 0);
__decorate$C([
  n$3({ type: Boolean, reflect: true })
], VscodeButton$1.prototype, "secondary", void 0);
__decorate$C([
  n$3({ type: Boolean, reflect: true })
], VscodeButton$1.prototype, "block", void 0);
__decorate$C([
  n$3({ reflect: true })
], VscodeButton$1.prototype, "role", void 0);
__decorate$C([
  n$3({ type: Boolean, reflect: true })
], VscodeButton$1.prototype, "disabled", void 0);
__decorate$C([
  n$3()
], VscodeButton$1.prototype, "icon", void 0);
__decorate$C([
  n$3({ type: Boolean, reflect: true, attribute: "icon-spin" })
], VscodeButton$1.prototype, "iconSpin", void 0);
__decorate$C([
  n$3({ type: Number, reflect: true, attribute: "icon-spin-duration" })
], VscodeButton$1.prototype, "iconSpinDuration", void 0);
__decorate$C([
  n$3({ attribute: "icon-after" })
], VscodeButton$1.prototype, "iconAfter", void 0);
__decorate$C([
  n$3({ type: Boolean, reflect: true, attribute: "icon-after-spin" })
], VscodeButton$1.prototype, "iconAfterSpin", void 0);
__decorate$C([
  n$3({
    type: Number,
    reflect: true,
    attribute: "icon-after-spin-duration"
  })
], VscodeButton$1.prototype, "iconAfterSpinDuration", void 0);
__decorate$C([
  n$3({ type: Boolean, reflect: true })
], VscodeButton$1.prototype, "focused", void 0);
__decorate$C([
  n$3({ type: String, reflect: true })
], VscodeButton$1.prototype, "name", void 0);
__decorate$C([
  n$3({ type: Boolean, reflect: true, attribute: "icon-only" })
], VscodeButton$1.prototype, "iconOnly", void 0);
__decorate$C([
  n$3({ reflect: true })
], VscodeButton$1.prototype, "type", void 0);
__decorate$C([
  n$3()
], VscodeButton$1.prototype, "value", void 0);
__decorate$C([
  r$1()
], VscodeButton$1.prototype, "_hasContentBefore", void 0);
__decorate$C([
  r$1()
], VscodeButton$1.prototype, "_hasContentAfter", void 0);
VscodeButton$1 = __decorate$C([
  customElement("vscode-button")
], VscodeButton$1);
const VscodeButton2 = o$7({
  tagName: "vscode-button",
  elementClass: VscodeButton$1,
  react: E$1,
  displayName: "VscodeButton"
});
const styles$w = [
  defaultStyles,
  i$6`
    :host {
      display: inline-block;
    }

    .root {
      align-items: stretch;
      display: flex;
      width: 100%;
    }

    ::slotted(vscode-button:not(:first-child)) {
      --vsc-border-left-width: 0;
      --vsc-border-left-radius: 0;
      --vsc-border-left-width: 0;
    }

    ::slotted(vscode-button:not(:last-child)) {
      --vsc-divider-display: block;
      --vsc-base-additional-right-padding: 1px;
      --vsc-base-after-content: '';
      --vsc-border-right-width: 0;
      --vsc-border-right-radius: 0;
      --vsc-border-right-width: 0;
    }

    ::slotted(vscode-button:focus) {
      z-index: 1;
    }

    ::slotted(vscode-button:not(:empty)) {
      width: 100%;
    }
  `
];
var __decorate$B = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeButtonGroup = class VscodeButtonGroup2 extends VscElement {
  render() {
    return b`<div class="root"><slot></slot></div>`;
  }
};
VscodeButtonGroup.styles = styles$w;
VscodeButtonGroup = __decorate$B([
  customElement("vscode-button-group")
], VscodeButtonGroup);
o$7({
  tagName: "vscode-button-group",
  elementClass: VscodeButtonGroup,
  react: E$1,
  displayName: "VscodeButtonGroup"
});
var __decorate$A = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
class FormButtonWidgetBase extends VscElement {
  constructor() {
    super();
    this.focused = false;
    this._prevTabindex = 0;
    this._handleFocus = () => {
      this.focused = true;
    };
    this._handleBlur = () => {
      this.focused = false;
    };
  }
  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("focus", this._handleFocus);
    this.addEventListener("blur", this._handleBlur);
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("focus", this._handleFocus);
    this.removeEventListener("blur", this._handleBlur);
  }
  attributeChangedCallback(name, oldVal, newVal) {
    super.attributeChangedCallback(name, oldVal, newVal);
    if (name === "disabled" && this.hasAttribute("disabled")) {
      this._prevTabindex = this.tabIndex;
      this.tabIndex = -1;
    } else if (name === "disabled" && !this.hasAttribute("disabled")) {
      this.tabIndex = this._prevTabindex;
    }
  }
}
__decorate$A([
  n$3({ type: Boolean, reflect: true })
], FormButtonWidgetBase.prototype, "focused", void 0);
var __decorate$z = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
const LabelledCheckboxOrRadioMixin = (superClass) => {
  class LabelledCheckboxOrRadio extends superClass {
    constructor() {
      super(...arguments);
      this._label = "";
      this._slottedText = "";
    }
    set label(val) {
      this._label = val;
      if (this._slottedText === "") {
        this.setAttribute("aria-label", val);
      }
    }
    get label() {
      return this._label;
    }
    _handleSlotChange() {
      this._slottedText = this.textContent ? this.textContent.trim() : "";
      if (this._slottedText !== "") {
        this.setAttribute("aria-label", this._slottedText);
      }
    }
    _renderLabelAttribute() {
      return this._slottedText === "" ? b`<span class="label-attr">${this._label}</span>` : b`${A}`;
    }
  }
  __decorate$z([
    n$3()
  ], LabelledCheckboxOrRadio.prototype, "label", null);
  return LabelledCheckboxOrRadio;
};
const baseStyles = [
  i$6`
    :host {
      display: inline-block;
    }

    :host(:focus) {
      outline: none;
    }

    :host([disabled]) {
      opacity: 0.4;
    }

    .wrapper {
      color: var(--vscode-foreground, #cccccc);
      cursor: pointer;
      display: block;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      line-height: 18px;
      margin-bottom: 4px;
      margin-top: 4px;
      min-height: 18px;
      position: relative;
      user-select: none;
    }

    :host([disabled]) .wrapper {
      cursor: default;
    }

    input {
      clip: rect(1px, 1px, 1px, 1px);
      height: 1px;
      left: 9px;
      margin: 0;
      overflow: hidden;
      position: absolute;
      top: 17px;
      white-space: nowrap;
      width: 1px;
    }

    .icon {
      align-items: center;
      background-color: var(--vscode-settings-checkboxBackground, #313131);
      background-size: 16px;
      border: 1px solid var(--vscode-settings-checkboxBorder, #3c3c3c);
      box-sizing: border-box;
      color: var(--vscode-settings-checkboxForeground, #cccccc);
      display: flex;
      height: 18px;
      justify-content: center;
      left: 0;
      margin-left: 0;
      margin-right: 9px;
      padding: 0;
      pointer-events: none;
      position: absolute;
      top: 0;
      width: 18px;
    }

    .icon.before-empty-label {
      margin-right: 0;
    }

    .label {
      cursor: pointer;
      display: block;
      min-height: 18px;
      min-width: 18px;
    }

    .label-inner {
      display: block;
      opacity: 0.9;
      padding-left: 27px;
    }

    .label-inner.empty {
      padding-left: 0;
    }

    :host([disabled]) .label {
      cursor: default;
    }
  `
];
const styles$v = [
  defaultStyles,
  baseStyles,
  i$6`
    :host(:invalid) .icon,
    :host([invalid]) .icon {
      background-color: var(--vscode-inputValidation-errorBackground, #5a1d1d);
      border-color: var(--vscode-inputValidation-errorBorder, #be1100);
    }

    .icon {
      border-radius: 3px;
    }

    .indeterminate-icon {
      background-color: currentColor;
      position: absolute;
      height: 1px;
      width: 12px;
    }

    :host(:focus):host(:not([disabled])) .icon {
      outline: 1px solid var(--vscode-focusBorder, #0078d4);
      outline-offset: -1px;
    }

    /* Toggle appearance */
    :host([toggle]) .icon {
      /* Track */
      width: 36px;
      height: 20px;
      border-radius: 999px;
      background-color: var(--vscode-button-secondaryBackground, #313131);
      border-color: var(--vscode-button-border, transparent);
      justify-content: flex-start;
      position: absolute;
    }

    :host(:focus):host([toggle]):host(:not([disabled])) .icon {
      outline-offset: 2px;
    }

    /* Reserve space for the wider toggle track so text doesn't overlap */
    :host([toggle]) .label-inner {
      padding-left: 45px; /* 36px track + 9px spacing */
    }

    :host([toggle]) .label {
      min-height: 20px;
    }

    :host([toggle]) .wrapper {
      min-height: 20px;
      line-height: 20px;
    }

    :host([toggle]) .thumb {
      /* Thumb */
      box-sizing: border-box;
      display: block;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background-color: var(--vscode-button-secondaryForeground, #cccccc);
      margin-left: 1px;
      transition: transform 120ms ease-in-out;
    }

    :host([toggle][checked]) .icon {
      background-color: var(--vscode-button-background, #04395e);
      border-color: var(--vscode-button-border, transparent);
    }

    :host([toggle][checked]) .thumb {
      transform: translateX(16px);
      background-color: var(--vscode-button-foreground, #ffffff);
    }

    :host([toggle]):host(:invalid) .icon {
      background-color: var(--vscode-inputValidation-errorBackground, #5a1d1d);
      border-color: var(--vscode-inputValidation-errorBorder, #be1100);
    }

    :host([toggle]):host(:invalid) .thumb {
      background-color: var(--vscode-inputValidation-errorBorder, #be1100);
    }

    :host([toggle]) .check-icon,
    :host([toggle]) .indeterminate-icon {
      display: none;
    }

    :host([toggle]:focus):host(:not([disabled])) .icon {
      outline: 1px solid var(--vscode-focusBorder, #0078d4);
      outline-offset: -1px;
    }
  `
];
var __decorate$y = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeCheckbox$1 = class VscodeCheckbox extends LabelledCheckboxOrRadioMixin(FormButtonWidgetBase) {
  set checked(newVal) {
    this._checked = newVal;
    this._manageRequired();
    this.requestUpdate();
  }
  get checked() {
    return this._checked;
  }
  set required(newVal) {
    this._required = newVal;
    this._manageRequired();
    this.requestUpdate();
  }
  get required() {
    return this._required;
  }
  get form() {
    return this._internals.form;
  }
  get validity() {
    return this._internals.validity;
  }
  get validationMessage() {
    return this._internals.validationMessage;
  }
  get willValidate() {
    return this._internals.willValidate;
  }
  /**
   * Returns `true` if the element's value is valid; otherwise, it returns `false`.
   * If the element's value is invalid, an invalid event is triggered on the element.
   *
   * [MDN Reference](https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/checkValidity)
   */
  checkValidity() {
    return this._internals.checkValidity();
  }
  /**
   * Returns `true` if the element's value is valid; otherwise, it returns `false`.
   * If the element's value is invalid, an invalid event is triggered on the element, and the
   * browser displays an error message to the user.
   *
   * [MDN Reference](https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/reportValidity)
   */
  reportValidity() {
    return this._internals.reportValidity();
  }
  constructor() {
    super();
    this.autofocus = false;
    this._checked = false;
    this.defaultChecked = false;
    this.invalid = false;
    this.name = void 0;
    this.toggle = false;
    this.value = "";
    this.disabled = false;
    this.indeterminate = false;
    this._required = false;
    this.type = "checkbox";
    this._handleClick = (ev) => {
      ev.preventDefault();
      if (this.disabled) {
        return;
      }
      this._toggleState();
    };
    this._handleKeyDown = (ev) => {
      if (!this.disabled && (ev.key === "Enter" || ev.key === " ")) {
        ev.preventDefault();
        if (ev.key === " ") {
          this._toggleState();
        }
        if (ev.key === "Enter") {
          this._internals.form?.requestSubmit();
        }
      }
    };
    this._internals = this.attachInternals();
  }
  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("keydown", this._handleKeyDown);
    this.updateComplete.then(() => {
      this._manageRequired();
      this._setActualFormValue();
    });
  }
  disconnectedCallback() {
    this.removeEventListener("keydown", this._handleKeyDown);
  }
  /** @internal */
  formResetCallback() {
    this.checked = this.defaultChecked;
  }
  /** @internal */
  formStateRestoreCallback(state, _mode) {
    if (state) {
      this.checked = true;
    }
  }
  // Sets the value of the control according to the native checkbox behavior.
  // - If the checkbox is unchecked, the value will be null, so the control will
  //   excluded from the form.
  // - If the control is checked but the value is not set, the value will be "on".
  // - If the control is checked and value is set, the value won't be changed.
  _setActualFormValue() {
    let actualValue = "";
    if (this.checked) {
      actualValue = !this.value ? "on" : this.value;
    } else {
      actualValue = null;
    }
    this._internals.setFormValue(actualValue);
  }
  _toggleState() {
    this.checked = !this.checked;
    this.indeterminate = false;
    this._setActualFormValue();
    this._manageRequired();
    this.dispatchEvent(new Event("change", { bubbles: true }));
  }
  _manageRequired() {
    if (!this.checked && this.required) {
      this._internals.setValidity({
        valueMissing: true
      }, "Please check this box if you want to proceed.", this._inputEl ?? void 0);
    } else {
      this._internals.setValidity({});
    }
  }
  render() {
    const iconClasses = e$2({
      icon: true,
      checked: this.checked,
      indeterminate: this.indeterminate
    });
    const labelInnerClasses = e$2({
      "label-inner": true
    });
    const icon = b`<svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      xmlns="http://www.w3.org/2000/svg"
      fill="currentColor"
      class="check-icon"
    >
      <path
        fill-rule="evenodd"
        clip-rule="evenodd"
        d="M14.431 3.323l-8.47 10-.79-.036-3.35-4.77.818-.574 2.978 4.24 8.051-9.506.764.646z"
      />
    </svg>`;
    const check = this.checked && !this.indeterminate ? icon : A;
    const indeterminate = this.indeterminate ? b`<span class="indeterminate-icon"></span>` : A;
    const iconContent = this.toggle ? b`<span class="thumb"></span>` : b`${indeterminate}${check}`;
    return b`
      <div class="wrapper">
        <input
          ?autofocus=${this.autofocus}
          id="input"
          class="checkbox"
          type="checkbox"
          ?checked=${this.checked}
          role=${o(this.toggle ? "switch" : void 0)}
          aria-checked=${o(this.toggle ? this.checked ? "true" : "false" : void 0)}
          value=${this.value}
        />
        <div class=${iconClasses}>${iconContent}</div>
        <label for="input" class="label" @click=${this._handleClick}>
          <span class=${labelInnerClasses}>
            ${this._renderLabelAttribute()}
            <slot @slotchange=${this._handleSlotChange}></slot>
          </span>
        </label>
      </div>
    `;
  }
};
VscodeCheckbox$1.styles = styles$v;
VscodeCheckbox$1.formAssociated = true;
VscodeCheckbox$1.shadowRootOptions = {
  ...i$3.shadowRootOptions,
  delegatesFocus: true
};
__decorate$y([
  n$3({ type: Boolean, reflect: true })
], VscodeCheckbox$1.prototype, "autofocus", void 0);
__decorate$y([
  n$3({ type: Boolean, reflect: true })
], VscodeCheckbox$1.prototype, "checked", null);
__decorate$y([
  n$3({ type: Boolean, reflect: true, attribute: "default-checked" })
], VscodeCheckbox$1.prototype, "defaultChecked", void 0);
__decorate$y([
  n$3({ type: Boolean, reflect: true })
], VscodeCheckbox$1.prototype, "invalid", void 0);
__decorate$y([
  n$3({ reflect: true })
], VscodeCheckbox$1.prototype, "name", void 0);
__decorate$y([
  n$3({ type: Boolean, reflect: true })
], VscodeCheckbox$1.prototype, "toggle", void 0);
__decorate$y([
  n$3()
], VscodeCheckbox$1.prototype, "value", void 0);
__decorate$y([
  n$3({ type: Boolean, reflect: true })
], VscodeCheckbox$1.prototype, "disabled", void 0);
__decorate$y([
  n$3({ type: Boolean, reflect: true })
], VscodeCheckbox$1.prototype, "indeterminate", void 0);
__decorate$y([
  n$3({ type: Boolean, reflect: true })
], VscodeCheckbox$1.prototype, "required", null);
__decorate$y([
  n$3()
], VscodeCheckbox$1.prototype, "type", void 0);
__decorate$y([
  e$5("#input")
], VscodeCheckbox$1.prototype, "_inputEl", void 0);
VscodeCheckbox$1 = __decorate$y([
  customElement("vscode-checkbox")
], VscodeCheckbox$1);
const VscodeCheckbox2 = o$7({
  tagName: "vscode-checkbox",
  elementClass: VscodeCheckbox$1,
  react: E$1,
  displayName: "VscodeCheckbox",
  events: {
    onChange: "change"
  }
});
const styles$u = [
  defaultStyles,
  i$6`
    :host {
      display: block;
    }

    .wrapper {
      display: flex;
      flex-wrap: wrap;
    }

    :host([variant='vertical']) .wrapper {
      display: block;
    }

    ::slotted(vscode-checkbox) {
      margin-right: 20px;
    }

    ::slotted(vscode-checkbox:last-child) {
      margin-right: 0;
    }

    :host([variant='vertical']) ::slotted(vscode-checkbox) {
      display: block;
      margin-bottom: 15px;
    }

    :host([variant='vertical']) ::slotted(vscode-checkbox:last-child) {
      margin-bottom: 0;
    }
  `
];
var __decorate$x = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeCheckboxGroup = class VscodeCheckboxGroup2 extends VscElement {
  constructor() {
    super(...arguments);
    this.role = "group";
    this.variant = "horizontal";
  }
  render() {
    return b`
      <div class="wrapper">
        <slot></slot>
      </div>
    `;
  }
};
VscodeCheckboxGroup.styles = styles$u;
__decorate$x([
  n$3({ reflect: true })
], VscodeCheckboxGroup.prototype, "role", void 0);
__decorate$x([
  n$3({ reflect: true })
], VscodeCheckboxGroup.prototype, "variant", void 0);
VscodeCheckboxGroup = __decorate$x([
  customElement("vscode-checkbox-group")
], VscodeCheckboxGroup);
o$7({
  tagName: "vscode-checkbox-group",
  elementClass: VscodeCheckboxGroup,
  react: E$1,
  displayName: "VscodeCheckboxGroup"
});
const styles$t = [
  defaultStyles,
  i$6`
    :host {
      display: block;
    }

    .collapsible {
      background-color: var(--vscode-sideBar-background, #181818);
    }

    .collapsible-header {
      align-items: center;
      background-color: var(--vscode-sideBarSectionHeader-background, #181818);
      cursor: pointer;
      display: flex;
      height: 22px;
      line-height: 22px;
      user-select: none;
    }

    .collapsible-header:focus {
      opacity: 1;
      outline-offset: -1px;
      outline-style: solid;
      outline-width: 1px;
      outline-color: var(--vscode-focusBorder, #0078d4);
    }

    .title {
      color: var(--vscode-sideBarTitle-foreground, #cccccc);
      display: block;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: 11px;
      font-weight: 700;
      margin: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .title .description {
      font-weight: 400;
      margin-left: 10px;
      text-transform: none;
      opacity: 0.6;
    }

    .header-icon {
      color: var(--vscode-icon-foreground, #cccccc);
      display: block;
      flex-shrink: 0;
      margin: 0 3px;
    }

    .collapsible.open .header-icon {
      transform: rotate(90deg);
    }

    .header-slots {
      align-items: center;
      display: flex;
      height: 22px;
      margin-left: auto;
      margin-right: 4px;
    }

    .actions {
      display: none;
    }

    .collapsible.open .actions.always-visible,
    .collapsible.open:hover .actions {
      display: block;
    }

    .header-slots slot {
      display: flex;
      max-height: 22px;
      overflow: hidden;
    }

    .header-slots slot::slotted(div) {
      align-items: center;
      display: flex;
    }

    .collapsible-body {
      display: none;
      overflow: hidden;
    }

    .collapsible.open .collapsible-body {
      display: block;
    }
  `
];
var __decorate$w = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeCollapsible = class VscodeCollapsible2 extends VscElement {
  constructor() {
    super(...arguments);
    this.alwaysShowHeaderActions = false;
    this.title = "";
    this.heading = "";
    this.description = "";
    this.open = false;
  }
  _emitToggleEvent() {
    this.dispatchEvent(new CustomEvent("vsc-collapsible-toggle", {
      detail: { open: this.open }
    }));
  }
  _onHeaderClick() {
    this.open = !this.open;
    this._emitToggleEvent();
  }
  _onHeaderKeyDown(event) {
    if (event.key === "Enter") {
      this.open = !this.open;
      this._emitToggleEvent();
    }
  }
  _onHeaderSlotClick(event) {
    event.stopPropagation();
  }
  render() {
    const classes = { collapsible: true, open: this.open };
    const actionsClasses = {
      actions: true,
      "always-visible": this.alwaysShowHeaderActions
    };
    const heading = this.heading ? this.heading : this.title;
    const icon = b`<svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      xmlns="http://www.w3.org/2000/svg"
      fill="currentColor"
      class="header-icon"
    >
      <path
        fill-rule="evenodd"
        clip-rule="evenodd"
        d="M10.072 8.024L5.715 3.667l.618-.62L11 7.716v.618L6.333 13l-.618-.619 4.357-4.357z"
      />
    </svg>`;
    const descriptionMarkup = this.description ? b`<span class="description">${this.description}</span>` : A;
    return b`
      <div class=${e$2(classes)}>
        <div
          class="collapsible-header"
          tabindex="0"
          @click=${this._onHeaderClick}
          @keydown=${this._onHeaderKeyDown}
        >
          ${icon}
          <h3 class="title">${heading}${descriptionMarkup}</h3>
          <div class="header-slots">
            <div class=${e$2(actionsClasses)}>
              <slot name="actions" @click=${this._onHeaderSlotClick}></slot>
            </div>
            <div class="decorations">
              <slot name="decorations" @click=${this._onHeaderSlotClick}></slot>
            </div>
          </div>
        </div>
        <div class="collapsible-body" part="body">
          <slot></slot>
        </div>
      </div>
    `;
  }
};
VscodeCollapsible.styles = styles$t;
__decorate$w([
  n$3({
    type: Boolean,
    reflect: true,
    attribute: "always-show-header-actions"
  })
], VscodeCollapsible.prototype, "alwaysShowHeaderActions", void 0);
__decorate$w([
  n$3({ type: String })
], VscodeCollapsible.prototype, "title", void 0);
__decorate$w([
  n$3()
], VscodeCollapsible.prototype, "heading", void 0);
__decorate$w([
  n$3()
], VscodeCollapsible.prototype, "description", void 0);
__decorate$w([
  n$3({ type: Boolean, reflect: true })
], VscodeCollapsible.prototype, "open", void 0);
VscodeCollapsible = __decorate$w([
  customElement("vscode-collapsible")
], VscodeCollapsible);
o$7({
  tagName: "vscode-collapsible",
  elementClass: VscodeCollapsible,
  react: E$1,
  displayName: "VscodeCollapsible"
});
const styles$s = [
  defaultStyles,
  i$6`
    :host {
      display: block;
      outline: none;
      position: relative;
    }

    .context-menu-item {
      background-color: var(--vscode-menu-background, #1f1f1f);
      color: var(--vscode-menu-foreground, #cccccc);
      display: flex;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      line-height: 1.4em;
      user-select: none;
      white-space: nowrap;
    }

    .ruler {
      border-bottom: 1px solid var(--vscode-menu-separatorBackground, #454545);
      display: block;
      margin: 0 0 4px;
      padding-top: 4px;
      width: 100%;
    }

    .context-menu-item a {
      align-items: center;
      border-color: transparent;
      border-radius: 3px;
      border-style: solid;
      border-width: 1px;
      box-sizing: border-box;
      color: var(--vscode-menu-foreground, #cccccc);
      cursor: pointer;
      display: flex;
      flex: 1 1 auto;
      height: 2em;
      margin-left: 4px;
      margin-right: 4px;
      outline: none;
      position: relative;
      text-decoration: inherit;
    }

    :host([selected]) .context-menu-item a {
      background-color: var(--vscode-menu-selectionBackground, #0078d4);
      border-color: var(--vscode-menu-selectionBorder, transparent);
      color: var(--vscode-menu-selectionForeground, #ffffff);
    }

    .label {
      background: none;
      display: flex;
      flex: 1 1 auto;
      font-size: 12px;
      line-height: 1;
      padding: 0 22px;
      text-decoration: none;
    }

    .keybinding {
      display: block;
      flex: 2 1 auto;
      line-height: 1;
      padding: 0 22px;
      text-align: right;
    }
  `
];
var __decorate$v = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeContextMenuItem = class VscodeContextMenuItem2 extends VscElement {
  constructor() {
    super(...arguments);
    this.label = "";
    this.keybinding = "";
    this.value = "";
    this.separator = false;
    this.tabindex = 0;
  }
  onItemClick() {
    this.dispatchEvent(new CustomEvent("vsc-click", {
      detail: {
        label: this.label,
        keybinding: this.keybinding,
        value: this.value || this.label,
        separator: this.separator,
        tabindex: this.tabindex
      },
      bubbles: true,
      composed: true
    }));
  }
  render() {
    return b`
      ${this.separator ? b`
            <div class="context-menu-item separator">
              <span class="ruler"></span>
            </div>
          ` : b`
            <div class="context-menu-item">
              <a @click=${this.onItemClick}>
                ${this.label ? b`<span class="label">${this.label}</span>` : A}
                ${this.keybinding ? b`<span class="keybinding">${this.keybinding}</span>` : A}
              </a>
            </div>
          `}
    `;
  }
};
VscodeContextMenuItem.styles = styles$s;
__decorate$v([
  n$3({ type: String })
], VscodeContextMenuItem.prototype, "label", void 0);
__decorate$v([
  n$3({ type: String })
], VscodeContextMenuItem.prototype, "keybinding", void 0);
__decorate$v([
  n$3({ type: String })
], VscodeContextMenuItem.prototype, "value", void 0);
__decorate$v([
  n$3({ type: Boolean, reflect: true })
], VscodeContextMenuItem.prototype, "separator", void 0);
__decorate$v([
  n$3({ type: Number })
], VscodeContextMenuItem.prototype, "tabindex", void 0);
VscodeContextMenuItem = __decorate$v([
  customElement("vscode-context-menu-item")
], VscodeContextMenuItem);
const styles$r = [
  defaultStyles,
  i$6`
    :host {
      display: block;
      position: relative;
    }

    .context-menu {
      background-color: var(--vscode-menu-background, #1f1f1f);
      border-color: var(--vscode-menu-border, #454545);
      border-radius: 5px;
      border-style: solid;
      border-width: 1px;
      box-shadow: 0 2px 8px var(--vscode-widget-shadow, rgba(0, 0, 0, 0.36));
      color: var(--vscode-menu-foreground, #cccccc);
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      line-height: 1.4em;
      padding: 4px 0;
      white-space: nowrap;
    }

    .context-menu:focus {
      outline: 0;
    }
  `
];
var __decorate$u = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeContextMenu = class VscodeContextMenu2 extends VscElement {
  set data(data) {
    this._data = data;
    const indexes = [];
    data.forEach((v2, i4) => {
      if (!v2.separator) {
        indexes.push(i4);
      }
    });
    this._clickableItemIndexes = indexes;
  }
  get data() {
    return this._data;
  }
  set show(show) {
    this._show = show;
    this._selectedClickableItemIndex = -1;
    if (show) {
      this.updateComplete.then(() => {
        if (this._wrapperEl) {
          this._wrapperEl.focus();
        }
        requestAnimationFrame(() => {
          document.addEventListener("click", this._onClickOutsideBound, {
            once: true
          });
        });
      });
    }
  }
  get show() {
    return this._show;
  }
  constructor() {
    super();
    this.preventClose = false;
    this.tabIndex = 0;
    this._selectedClickableItemIndex = -1;
    this._show = false;
    this._data = [];
    this._clickableItemIndexes = [];
    this._onClickOutsideBound = this._onClickOutside.bind(this);
    this.addEventListener("keydown", this._onKeyDown);
  }
  _onClickOutside(ev) {
    if (!ev.composedPath().includes(this)) {
      this.show = false;
    }
  }
  _onKeyDown(ev) {
    const { key } = ev;
    if (key === "ArrowUp" || key === "ArrowDown" || key === "Escape" || key === "Enter") {
      ev.preventDefault();
    }
    switch (key) {
      case "ArrowUp":
        this._handleArrowUp();
        break;
      case "ArrowDown":
        this._handleArrowDown();
        break;
      case "Escape":
        this._handleEscape();
        break;
      case "Enter":
        this._handleEnter();
        break;
    }
  }
  _handleArrowUp() {
    if (this._selectedClickableItemIndex === 0) {
      this._selectedClickableItemIndex = this._clickableItemIndexes.length - 1;
    } else {
      this._selectedClickableItemIndex -= 1;
    }
  }
  _handleArrowDown() {
    if (this._selectedClickableItemIndex + 1 < this._clickableItemIndexes.length) {
      this._selectedClickableItemIndex += 1;
    } else {
      this._selectedClickableItemIndex = 0;
    }
  }
  _handleEscape() {
    this.show = false;
    document.removeEventListener("click", this._onClickOutsideBound);
  }
  _dispatchSelectEvent(selectedOption) {
    const { keybinding, label, value, separator, tabindex } = selectedOption;
    this.dispatchEvent(new CustomEvent("vsc-context-menu-select", {
      detail: {
        keybinding,
        label,
        separator,
        tabindex,
        value
      }
    }));
  }
  _handleEnter() {
    if (this._selectedClickableItemIndex === -1) {
      return;
    }
    const realItemIndex = this._clickableItemIndexes[this._selectedClickableItemIndex];
    const options = this._wrapperEl.querySelectorAll("vscode-context-menu-item");
    const selectedOption = options[realItemIndex];
    this._dispatchSelectEvent(selectedOption);
    if (!this.preventClose) {
      this.show = false;
      document.removeEventListener("click", this._onClickOutsideBound);
    }
  }
  _onItemClick(event) {
    const et = event.currentTarget;
    this._dispatchSelectEvent(et);
    if (!this.preventClose) {
      this.show = false;
    }
  }
  _onItemMouseOver(event) {
    const el = event.target;
    const index = el.dataset.index ? +el.dataset.index : -1;
    const found = this._clickableItemIndexes.findIndex((item) => item === index);
    if (found !== -1) {
      this._selectedClickableItemIndex = found;
    }
  }
  _onItemMouseOut() {
    this._selectedClickableItemIndex = -1;
  }
  render() {
    if (!this._show) {
      return b`${A}`;
    }
    const selectedIndex = this._clickableItemIndexes[this._selectedClickableItemIndex];
    return b`
      <div class="context-menu" tabindex="0">
        ${this.data ? this.data.map(({ label = "", keybinding = "", value = "", separator = false, tabindex = 0 }, index) => b`
                <vscode-context-menu-item
                  label=${label}
                  keybinding=${keybinding}
                  value=${value}
                  ?separator=${separator}
                  ?selected=${index === selectedIndex}
                  tabindex=${tabindex}
                  @vsc-click=${this._onItemClick}
                  @mouseover=${this._onItemMouseOver}
                  @mouseout=${this._onItemMouseOut}
                  data-index=${index}
                ></vscode-context-menu-item>
              `) : b`<slot></slot>`}
      </div>
    `;
  }
};
VscodeContextMenu.styles = styles$r;
__decorate$u([
  n$3({ type: Array, attribute: false })
], VscodeContextMenu.prototype, "data", null);
__decorate$u([
  n$3({ type: Boolean, reflect: true, attribute: "prevent-close" })
], VscodeContextMenu.prototype, "preventClose", void 0);
__decorate$u([
  n$3({ type: Boolean, reflect: true })
], VscodeContextMenu.prototype, "show", null);
__decorate$u([
  n$3({ type: Number, reflect: true })
], VscodeContextMenu.prototype, "tabIndex", void 0);
__decorate$u([
  r$1()
], VscodeContextMenu.prototype, "_selectedClickableItemIndex", void 0);
__decorate$u([
  r$1()
], VscodeContextMenu.prototype, "_show", void 0);
__decorate$u([
  e$5(".context-menu")
], VscodeContextMenu.prototype, "_wrapperEl", void 0);
VscodeContextMenu = __decorate$u([
  customElement("vscode-context-menu")
], VscodeContextMenu);
o$7({
  tagName: "vscode-context-menu",
  elementClass: VscodeContextMenu,
  react: E$1,
  displayName: "VscodeContextMenu",
  events: {
    onVscContextMenuSelect: "vsc-context-menu-select"
  }
});
o$7({
  tagName: "vscode-context-menu-item",
  elementClass: VscodeContextMenuItem,
  react: E$1,
  displayName: "VscodeContextMenuItem"
});
const styles$q = [
  defaultStyles,
  i$6`
    :host {
      display: block;
      margin-bottom: 10px;
      margin-top: 10px;
    }

    div {
      background-color: var(--vscode-foreground, #cccccc);
      height: 1px;
      opacity: 0.4;
    }
  `
];
var __decorate$t = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeDivider$1 = class VscodeDivider extends VscElement {
  constructor() {
    super(...arguments);
    this.role = "separator";
  }
  render() {
    return b`<div></div>`;
  }
};
VscodeDivider$1.styles = styles$q;
__decorate$t([
  n$3({ reflect: true })
], VscodeDivider$1.prototype, "role", void 0);
VscodeDivider$1 = __decorate$t([
  customElement("vscode-divider")
], VscodeDivider$1);
const VscodeDivider2 = o$7({
  tagName: "vscode-divider",
  elementClass: VscodeDivider$1,
  react: E$1,
  displayName: "VscodeDivider"
});
const styles$p = [
  defaultStyles,
  i$6`
    :host {
      display: block;
      max-width: 727px;
    }
  `
];
var __decorate$s = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
var FormGroupLayout;
(function(FormGroupLayout2) {
  FormGroupLayout2["HORIZONTAL"] = "horizontal";
  FormGroupLayout2["VERTICAL"] = "vertical";
})(FormGroupLayout || (FormGroupLayout = {}));
let VscodeFormContainer = class VscodeFormContainer2 extends VscElement {
  constructor() {
    super(...arguments);
    this.breakpoint = 490;
    this._responsive = false;
    this._firstUpdateComplete = false;
    this._resizeObserverCallbackBound = this._resizeObserverCallback.bind(this);
  }
  set responsive(isResponsive) {
    this._responsive = isResponsive;
    if (this._firstUpdateComplete) {
      if (isResponsive) {
        this._activateResponsiveLayout();
      } else {
        this._deactivateResizeObserver();
      }
    }
  }
  get responsive() {
    return this._responsive;
  }
  _toggleCompactLayout(layout) {
    this._assignedFormGroups.forEach((group) => {
      if (!group.dataset.originalVariant) {
        group.dataset.originalVariant = group.variant;
      }
      const oVariant = group.dataset.originalVariant;
      if (layout === FormGroupLayout.VERTICAL && oVariant === "horizontal") {
        group.variant = "vertical";
      } else {
        group.variant = oVariant;
      }
      const checkboxOrRadioGroup = group.querySelectorAll("vscode-checkbox-group, vscode-radio-group");
      checkboxOrRadioGroup.forEach((widgetGroup) => {
        if (!widgetGroup.dataset.originalVariant) {
          widgetGroup.dataset.originalVariant = widgetGroup.variant;
        }
        const originalVariant = widgetGroup.dataset.originalVariant;
        if (layout === FormGroupLayout.HORIZONTAL && originalVariant === FormGroupLayout.HORIZONTAL) {
          widgetGroup.variant = "horizontal";
        } else {
          widgetGroup.variant = "vertical";
        }
      });
    });
  }
  _resizeObserverCallback(entries) {
    let wrapperWidth = 0;
    for (const entry of entries) {
      wrapperWidth = entry.contentRect.width;
    }
    const nextLayout = wrapperWidth < this.breakpoint ? FormGroupLayout.VERTICAL : FormGroupLayout.HORIZONTAL;
    if (nextLayout !== this._currentFormGroupLayout) {
      this._toggleCompactLayout(nextLayout);
      this._currentFormGroupLayout = nextLayout;
    }
  }
  _activateResponsiveLayout() {
    this._resizeObserver = new ResizeObserver(this._resizeObserverCallbackBound);
    this._resizeObserver.observe(this._wrapperElement);
  }
  _deactivateResizeObserver() {
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
  }
  firstUpdated() {
    this._firstUpdateComplete = true;
    if (this._responsive) {
      this._activateResponsiveLayout();
    }
  }
  render() {
    return b`
      <div class="wrapper">
        <slot></slot>
      </div>
    `;
  }
};
VscodeFormContainer.styles = styles$p;
__decorate$s([
  n$3({ type: Boolean, reflect: true })
], VscodeFormContainer.prototype, "responsive", null);
__decorate$s([
  n$3({ type: Number })
], VscodeFormContainer.prototype, "breakpoint", void 0);
__decorate$s([
  e$5(".wrapper")
], VscodeFormContainer.prototype, "_wrapperElement", void 0);
__decorate$s([
  o$1({ selector: "vscode-form-group" })
], VscodeFormContainer.prototype, "_assignedFormGroups", void 0);
VscodeFormContainer = __decorate$s([
  customElement("vscode-form-container")
], VscodeFormContainer);
o$7({
  tagName: "vscode-form-container",
  elementClass: VscodeFormContainer,
  react: E$1,
  displayName: "VscodeFormContainer"
});
const styles$o = [
  defaultStyles,
  i$6`
    :host {
      --label-right-margin: 14px;
      --label-width: 150px;

      display: block;
      margin: 15px 0;
    }

    :host([variant='settings-group']) {
      margin: 0;
      padding: 12px 14px 18px;
      max-width: 727px;
    }

    .wrapper {
      display: flex;
      flex-wrap: wrap;
    }

    :host([variant='vertical']) .wrapper,
    :host([variant='settings-group']) .wrapper {
      display: block;
    }

    :host([variant='horizontal']) ::slotted(vscode-checkbox-group),
    :host([variant='horizontal']) ::slotted(vscode-radio-group) {
      width: calc(100% - calc(var(--label-width) + var(--label-right-margin)));
    }

    :host([variant='horizontal']) ::slotted(vscode-label) {
      margin-right: var(--label-right-margin);
      text-align: right;
      width: var(--label-width);
    }

    :host([variant='settings-group']) ::slotted(vscode-label) {
      height: 18px;
      line-height: 18px;
      margin-bottom: 4px;
      margin-right: 0;
      padding: 0;
    }

    ::slotted(vscode-form-helper) {
      margin-left: calc(var(--label-width) + var(--label-right-margin));
    }

    :host([variant='vertical']) ::slotted(vscode-form-helper),
    :host([variant='settings-group']) ::slotted(vscode-form-helper) {
      display: block;
      margin-left: 0;
    }

    :host([variant='settings-group']) ::slotted(vscode-form-helper) {
      margin-bottom: 0;
      margin-top: 0;
    }

    :host([variant='vertical']) ::slotted(vscode-label),
    :host([variant='settings-group']) ::slotted(vscode-label) {
      display: block;
      margin-left: 0;
      text-align: left;
    }

    :host([variant='settings-group']) ::slotted(vscode-inputbox),
    :host([variant='settings-group']) ::slotted(vscode-textfield),
    :host([variant='settings-group']) ::slotted(vscode-textarea),
    :host([variant='settings-group']) ::slotted(vscode-single-select),
    :host([variant='settings-group']) ::slotted(vscode-multi-select) {
      margin-top: 9px;
    }

    ::slotted(vscode-button:first-child) {
      margin-left: calc(var(--label-width) + var(--label-right-margin));
    }

    :host([variant='vertical']) ::slotted(vscode-button) {
      margin-left: 0;
    }

    ::slotted(vscode-button) {
      margin-right: 4px;
    }
  `
];
var __decorate$r = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeFormGroup = class VscodeFormGroup2 extends VscElement {
  constructor() {
    super(...arguments);
    this.variant = "horizontal";
  }
  render() {
    return b`
      <div class="wrapper">
        <slot></slot>
      </div>
    `;
  }
};
VscodeFormGroup.styles = styles$o;
__decorate$r([
  n$3({ reflect: true })
], VscodeFormGroup.prototype, "variant", void 0);
VscodeFormGroup = __decorate$r([
  customElement("vscode-form-group")
], VscodeFormGroup);
o$7({
  tagName: "vscode-form-group",
  elementClass: VscodeFormGroup,
  react: E$1,
  displayName: "VscodeFormGroup"
});
const styles$n = [
  defaultStyles,
  i$6`
    :host {
      display: block;
      line-height: 1.4em;
      margin-bottom: 4px;
      margin-top: 4px;
      max-width: 720px;
      opacity: 0.9;
    }

    :host([vertical]) {
      margin-left: 0;
    }
  `
];
var __decorate$q = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
const lightDOMStyles = new CSSStyleSheet();
lightDOMStyles.replaceSync(`
  vscode-form-helper * {
    margin: 0;
  }

  vscode-form-helper *:not(:last-child) {
    margin-bottom: 8px;
  }
`);
let VscodeFormHelper$1 = class VscodeFormHelper extends VscElement {
  constructor() {
    super();
    this._injectLightDOMStyles();
  }
  _injectLightDOMStyles() {
    const found = document.adoptedStyleSheets.find((s4) => s4 === lightDOMStyles);
    if (!found) {
      document.adoptedStyleSheets.push(lightDOMStyles);
    }
  }
  render() {
    return b`<slot></slot>`;
  }
};
VscodeFormHelper$1.styles = styles$n;
VscodeFormHelper$1 = __decorate$q([
  customElement("vscode-form-helper")
], VscodeFormHelper$1);
const VscodeFormHelper2 = o$7({
  tagName: "vscode-form-helper",
  elementClass: VscodeFormHelper$1,
  react: E$1,
  displayName: "VscodeFormHelper"
});
o$7({
  tagName: "vscode-icon",
  elementClass: VscodeIcon,
  react: E$1,
  displayName: "VscodeIcon"
});
let counter = 0;
const uniqueId = (prefix = "") => {
  counter++;
  return `${prefix}${counter}`;
};
const styles$m = [
  defaultStyles,
  i$6`
    :host {
      display: block;
    }

    .wrapper {
      color: var(--vscode-foreground, #cccccc);
      cursor: default;
      display: block;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: 600;
      line-height: ${INPUT_LINE_HEIGHT_RATIO};
      padding: 5px 0;
    }

    .wrapper.required:after {
      content: ' *';
    }

    ::slotted(.normal) {
      font-weight: normal;
    }

    ::slotted(.lightened) {
      color: var(--vscode-foreground, #cccccc);
      opacity: 0.9;
    }
  `
];
var __decorate$p = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeLabel$1 = class VscodeLabel extends VscElement {
  constructor() {
    super(...arguments);
    this.required = false;
    this._id = "";
    this._htmlFor = "";
    this._connected = false;
  }
  set htmlFor(val) {
    this._htmlFor = val;
    this.setAttribute("for", val);
    if (this._connected) {
      this._connectWithTarget();
    }
  }
  get htmlFor() {
    return this._htmlFor;
  }
  set id(val) {
    this._id = val;
  }
  get id() {
    return this._id;
  }
  attributeChangedCallback(name, old, value) {
    super.attributeChangedCallback(name, old, value);
  }
  connectedCallback() {
    super.connectedCallback();
    this._connected = true;
    if (this._id === "") {
      this._id = uniqueId("vscode-label-");
      this.setAttribute("id", this._id);
    }
    this._connectWithTarget();
  }
  _getTarget() {
    let target = null;
    if (this._htmlFor) {
      const root = this.getRootNode({ composed: false });
      if (root) {
        target = root.querySelector(`#${this._htmlFor}`);
      }
    }
    return target;
  }
  async _connectWithTarget() {
    await this.updateComplete;
    const target = this._getTarget();
    if (["vscode-radio-group", "vscode-checkbox-group"].includes(target?.tagName.toLowerCase() ?? "")) {
      target.setAttribute("aria-labelledby", this._id);
    }
    let label = "";
    if (this.textContent) {
      label = this.textContent.trim();
    }
    if (target && "label" in target && [
      "vscode-textfield",
      "vscode-textarea",
      "vscode-single-select",
      "vscode-multi-select"
    ].includes(target?.tagName.toLowerCase() ?? "")) {
      target.label = label;
    }
  }
  _handleClick() {
    const target = this._getTarget();
    if (target && "focus" in target) {
      target.focus();
    }
  }
  render() {
    return b`
      <label
        class=${e$2({ wrapper: true, required: this.required })}
        @click=${this._handleClick}
        ><slot></slot
      ></label>
    `;
  }
};
VscodeLabel$1.styles = styles$m;
__decorate$p([
  n$3({ reflect: true, attribute: "for" })
], VscodeLabel$1.prototype, "htmlFor", null);
__decorate$p([
  n$3()
], VscodeLabel$1.prototype, "id", null);
__decorate$p([
  n$3({ type: Boolean, reflect: true })
], VscodeLabel$1.prototype, "required", void 0);
VscodeLabel$1 = __decorate$p([
  customElement("vscode-label")
], VscodeLabel$1);
const VscodeLabel2 = o$7({
  tagName: "vscode-label",
  elementClass: VscodeLabel$1,
  react: E$1,
  displayName: "VscodeLabel"
});
const chevronDownIcon = b`
  <span class="icon">
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      xmlns="http://www.w3.org/2000/svg"
      fill="currentColor"
    >
      <path
        fill-rule="evenodd"
        clip-rule="evenodd"
        d="M7.976 10.072l4.357-4.357.62.618L8.284 11h-.618L3 6.333l.619-.618 4.357 4.357z"
      />
    </svg>
  </span>
`;
const checkIcon = w`<svg
  width="16"
  height="16"
  viewBox="0 0 16 16"
  xmlns="http://www.w3.org/2000/svg"
  fill="currentColor"
>
  <path
    fill-rule="evenodd"
    clip-rule="evenodd"
    d="M14.431 3.323l-8.47 10-.79-.036-3.35-4.77.818-.574 2.978 4.24 8.051-9.506.764.646z"
  />
</svg>`;
const { I: t } = j, i$1 = (o2) => o2, s$3 = () => document.createComment(""), v = (o2, n3, e3) => {
  const l2 = o2._$AA.parentNode, d2 = void 0 === n3 ? o2._$AB : n3._$AA;
  if (void 0 === e3) {
    const i4 = l2.insertBefore(s$3(), d2), n4 = l2.insertBefore(s$3(), d2);
    e3 = new t(i4, n4, o2, o2.options);
  } else {
    const t2 = e3._$AB.nextSibling, n4 = e3._$AM, c2 = n4 !== o2;
    if (c2) {
      let t3;
      e3._$AQ?.(o2), e3._$AM = o2, void 0 !== e3._$AP && (t3 = o2._$AU) !== n4._$AU && e3._$AP(t3);
    }
    if (t2 !== d2 || c2) {
      let o3 = e3._$AA;
      for (; o3 !== t2; ) {
        const t3 = i$1(o3).nextSibling;
        i$1(l2).insertBefore(o3, d2), o3 = t3;
      }
    }
  }
  return e3;
}, u$1 = (o2, t2, i4 = o2) => (o2._$AI(t2, i4), o2), m = {}, p = (o2, t2 = m) => o2._$AH = t2, M = (o2) => o2._$AH, h = (o2) => {
  o2._$AR(), o2._$AA.remove();
};
const u = (e3, s4, t2) => {
  const r2 = /* @__PURE__ */ new Map();
  for (let l2 = s4; l2 <= t2; l2++) r2.set(e3[l2], l2);
  return r2;
}, c$1 = e$3(class extends i$2 {
  constructor(e3) {
    if (super(e3), e3.type !== t$1.CHILD) throw Error("repeat() can only be used in text expressions");
  }
  dt(e3, s4, t2) {
    let r2;
    void 0 === t2 ? t2 = s4 : void 0 !== s4 && (r2 = s4);
    const l2 = [], o2 = [];
    let i4 = 0;
    for (const s5 of e3) l2[i4] = r2 ? r2(s5, i4) : i4, o2[i4] = t2(s5, i4), i4++;
    return { values: o2, keys: l2 };
  }
  render(e3, s4, t2) {
    return this.dt(e3, s4, t2).values;
  }
  update(s4, [t2, r2, c2]) {
    const d2 = M(s4), { values: p$12, keys: a2 } = this.dt(t2, r2, c2);
    if (!Array.isArray(d2)) return this.ut = a2, p$12;
    const h$12 = this.ut ??= [], v$12 = [];
    let m2, y3, x2 = 0, j2 = d2.length - 1, k2 = 0, w2 = p$12.length - 1;
    for (; x2 <= j2 && k2 <= w2; ) if (null === d2[x2]) x2++;
    else if (null === d2[j2]) j2--;
    else if (h$12[x2] === a2[k2]) v$12[k2] = u$1(d2[x2], p$12[k2]), x2++, k2++;
    else if (h$12[j2] === a2[w2]) v$12[w2] = u$1(d2[j2], p$12[w2]), j2--, w2--;
    else if (h$12[x2] === a2[w2]) v$12[w2] = u$1(d2[x2], p$12[w2]), v(s4, v$12[w2 + 1], d2[x2]), x2++, w2--;
    else if (h$12[j2] === a2[k2]) v$12[k2] = u$1(d2[j2], p$12[k2]), v(s4, d2[x2], d2[j2]), j2--, k2++;
    else if (void 0 === m2 && (m2 = u(a2, k2, w2), y3 = u(h$12, x2, j2)), m2.has(h$12[x2])) if (m2.has(h$12[j2])) {
      const e3 = y3.get(a2[k2]), t3 = void 0 !== e3 ? d2[e3] : null;
      if (null === t3) {
        const e4 = v(s4, d2[x2]);
        u$1(e4, p$12[k2]), v$12[k2] = e4;
      } else v$12[k2] = u$1(t3, p$12[k2]), v(s4, d2[x2], t3), d2[e3] = null;
      k2++;
    } else h(d2[j2]), j2--;
    else h(d2[x2]), x2++;
    for (; k2 <= w2; ) {
      const e3 = v(s4, v$12[w2 + 1]);
      u$1(e3, p$12[k2]), v$12[k2++] = e3;
    }
    for (; x2 <= j2; ) {
      const e3 = d2[x2++];
      null !== e3 && h(e3);
    }
    return this.ut = a2, p(s4, v$12), E;
  }
});
function n$1(n3, r2, t2) {
  return n3 ? r2(n3) : t2?.(n3);
}
var __decorate$o = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeOption$1 = class VscodeOption extends VscElement {
  constructor() {
    super(...arguments);
    this.description = "";
    this.selected = false;
    this.disabled = false;
    this._initialized = false;
    this._handleSlotChange = () => {
      if (this._initialized) {
        this.dispatchEvent(new Event("vsc-option-state-change", { bubbles: true }));
      }
    };
  }
  connectedCallback() {
    super.connectedCallback();
    this.updateComplete.then(() => {
      this._initialized = true;
    });
  }
  willUpdate(changedProperties) {
    if (this._initialized && (changedProperties.has("description") || changedProperties.has("value") || changedProperties.has("selected") || changedProperties.has("disabled"))) {
      this.dispatchEvent(new Event("vsc-option-state-change", { bubbles: true }));
    }
  }
  render() {
    return b`<slot @slotchange=${this._handleSlotChange}></slot>`;
  }
};
VscodeOption$1.styles = defaultStyles;
__decorate$o([
  n$3({ type: String })
], VscodeOption$1.prototype, "value", void 0);
__decorate$o([
  n$3({ type: String })
], VscodeOption$1.prototype, "description", void 0);
__decorate$o([
  n$3({ type: Boolean, reflect: true })
], VscodeOption$1.prototype, "selected", void 0);
__decorate$o([
  n$3({ type: Boolean, reflect: true })
], VscodeOption$1.prototype, "disabled", void 0);
VscodeOption$1 = __decorate$o([
  customElement("vscode-option")
], VscodeOption$1);
const startsWithPerTermSearch = (subject, pattern) => {
  const result = {
    match: false,
    ranges: []
  };
  const lcSubject = subject.toLowerCase();
  const lcPattern = pattern.toLowerCase();
  const terms = lcSubject.split(" ");
  let offset = 0;
  terms.forEach((t2, i4) => {
    if (i4 > 0) {
      offset += terms[i4 - 1].length + 1;
    }
    if (result.match) {
      return;
    }
    const foundIndex = t2.indexOf(lcPattern);
    const patternLength = lcPattern.length;
    if (foundIndex === 0) {
      result.match = true;
      result.ranges.push([
        offset + foundIndex,
        Math.min(offset + foundIndex + patternLength, subject.length)
      ]);
    }
  });
  return result;
};
const startsWithSearch = (subject, pattern) => {
  const result = {
    match: false,
    ranges: []
  };
  const foundIndex = subject.toLowerCase().indexOf(pattern.toLowerCase());
  if (foundIndex === 0) {
    result.match = true;
    result.ranges = [[0, pattern.length]];
  }
  return result;
};
const containsSearch = (subject, pattern) => {
  const result = {
    match: false,
    ranges: []
  };
  const foundIndex = subject.toLowerCase().indexOf(pattern.toLowerCase());
  if (foundIndex > -1) {
    result.match = true;
    result.ranges = [[foundIndex, foundIndex + pattern.length]];
  }
  return result;
};
const fuzzySearch = (subject, pattern) => {
  const result = {
    match: false,
    ranges: []
  };
  let fromIndex = 0;
  let foundIndex = 0;
  const iMax = pattern.length - 1;
  const lcSubject = subject.toLowerCase();
  const lcPattern = pattern.toLowerCase();
  for (let i4 = 0; i4 <= iMax; i4++) {
    foundIndex = lcSubject.indexOf(lcPattern[i4], fromIndex);
    if (foundIndex === -1) {
      return {
        match: false,
        ranges: []
      };
    }
    result.match = true;
    result.ranges.push([foundIndex, foundIndex + 1]);
    fromIndex = foundIndex + 1;
  }
  return result;
};
const filterOptionsByPattern = (list, pattern, method) => {
  const filtered = [];
  list.forEach((op) => {
    let result;
    switch (method) {
      case "startsWithPerTerm":
        result = startsWithPerTermSearch(op.label, pattern);
        break;
      case "startsWith":
        result = startsWithSearch(op.label, pattern);
        break;
      case "contains":
        result = containsSearch(op.label, pattern);
        break;
      default:
        result = fuzzySearch(op.label, pattern);
    }
    if (result.match) {
      filtered.push({ ...op, ranges: result.ranges });
    }
  });
  return filtered;
};
const preventSpaces = (text) => {
  const res = [];
  if (text === " ") {
    res.push(b`&nbsp;`);
    return res;
  }
  if (text.indexOf(" ") === 0) {
    res.push(b`&nbsp;`);
  }
  res.push(b`${text.trimStart().trimEnd()}`);
  if (text.lastIndexOf(" ") === text.length - 1) {
    res.push(b`&nbsp;`);
  }
  return res;
};
const highlightRanges = (text, ranges) => {
  const res = [];
  const rl = ranges.length;
  if (rl < 1) {
    return b`${text}`;
  }
  ranges.forEach((r2, i4) => {
    const match = text.substring(r2[0], r2[1]);
    if (i4 === 0 && r2[0] !== 0) {
      res.push(...preventSpaces(text.substring(0, ranges[0][0])));
    }
    if (i4 > 0 && i4 < rl && r2[0] - ranges[i4 - 1][1] !== 0) {
      res.push(...preventSpaces(text.substring(ranges[i4 - 1][1], r2[0])));
    }
    res.push(b`<b>${preventSpaces(match)}</b>`);
    if (i4 === rl - 1 && r2[1] < text.length) {
      res.push(...preventSpaces(text.substring(r2[1], text.length)));
    }
  });
  return res;
};
class OptionListController {
  constructor(host) {
    this._activeIndex = -1;
    this._options = [];
    this._filterPattern = "";
    this._filterMethod = "fuzzy";
    this._combobox = false;
    this._indexByValue = /* @__PURE__ */ new Map();
    this._indexByLabel = /* @__PURE__ */ new Map();
    this._selectedIndex = -1;
    this._selectedIndexes = /* @__PURE__ */ new Set();
    this._multiSelect = false;
    this._numOfVisibleOptions = 0;
    (this._host = host).addController(this);
  }
  hostConnected() {
  }
  //#region getters/setters
  get activeIndex() {
    return this._activeIndex;
  }
  set activeIndex(index) {
    this._activeIndex = index;
    this._host.requestUpdate();
  }
  get relativeActiveIndex() {
    return this._options[this._activeIndex]?.filteredIndex ?? -1;
  }
  set comboboxMode(enabled) {
    this._combobox = enabled;
    this._host.requestUpdate();
  }
  get comboboxMode() {
    return this._combobox;
  }
  get multiSelect() {
    return this._multiSelect;
  }
  set multiSelect(multiSelect) {
    this._selectedIndex = -1;
    this._selectedIndexes.clear();
    this._multiSelect = multiSelect;
    this._host.requestUpdate();
  }
  get selectedIndex() {
    return this._selectedIndex;
  }
  set selectedIndex(index) {
    if (this._selectedIndex !== -1 && this._options[this._selectedIndex]) {
      this._options[this._selectedIndex].selected ??= false;
    }
    const op = this.getOptionByIndex(index);
    this._selectedIndex = op ? index : -1;
    this._host.requestUpdate();
  }
  get selectedIndexes() {
    return Array.from(this._selectedIndexes);
  }
  set selectedIndexes(value) {
    this._selectedIndexes.forEach((v2) => {
      this._options[v2].selected = false;
    });
    this._selectedIndexes = new Set(value);
    value.forEach((v2) => {
      if (this._options[v2] !== void 0) {
        this._options[v2].selected = true;
      }
    });
    this._host.requestUpdate();
  }
  set value(newValue) {
    if (this._multiSelect) {
      const valueList = newValue.map((v2) => this._indexByValue.get(v2)).filter((v2) => v2 !== void 0);
      this._selectedIndexes = new Set(valueList);
    } else {
      this._selectedIndex = this._indexByValue.get(newValue) ?? -1;
    }
    this._host.requestUpdate();
  }
  get value() {
    if (this._multiSelect) {
      return this._selectedIndexes.size > 0 ? Array.from(this._selectedIndexes).filter((i4) => i4 >= 0 && i4 < this._options.length).map((v2) => this._options[v2].value) : [];
    } else {
      return this._selectedIndex > -1 && this._selectedIndex < this._options.length ? this._options[this._selectedIndex].value : "";
    }
  }
  set multiSelectValue(newValue) {
    const valueList = newValue.map((v2) => this._indexByValue.get(v2)).filter((v2) => v2 !== void 0);
    this._selectedIndexes = new Set(valueList);
  }
  get multiSelectValue() {
    return this._selectedIndexes.size > 0 ? Array.from(this._selectedIndexes).map((v2) => this._options[v2].value) : [];
  }
  get filterPattern() {
    return this._filterPattern;
  }
  set filterPattern(pattern) {
    if (pattern !== this._filterPattern) {
      this._filterPattern = pattern;
      this._updateState();
    }
  }
  get filterMethod() {
    return this._filterMethod;
  }
  set filterMethod(method) {
    if (method !== this._filterMethod) {
      this._filterMethod = method;
      this._updateState();
    }
  }
  get options() {
    return this._options;
  }
  get numOfVisibleOptions() {
    return this._numOfVisibleOptions;
  }
  get numOptions() {
    return this._options.length;
  }
  //#endregion
  //#region public functions
  populate(options) {
    this._indexByValue.clear();
    this._indexByLabel.clear();
    this._options = options.map((op, index) => {
      this._indexByValue.set(op.value ?? "", index);
      this._indexByLabel.set(op.label ?? "", index);
      return {
        description: op.description ?? "",
        disabled: op.disabled ?? false,
        label: op.label ?? "",
        selected: op.selected ?? false,
        value: op.value ?? "",
        index,
        filteredIndex: index,
        ranges: [],
        visible: true
      };
    });
    this._numOfVisibleOptions = this._options.length;
  }
  add(option) {
    const nextIndex = this._options.length;
    const { description, disabled, label, selected, value } = option;
    let visible = true;
    let ranges = [];
    if (this._combobox && this._filterPattern !== "") {
      const res = this._searchByPattern(label ?? "");
      visible = res.match;
      ranges = res.ranges;
    }
    this._indexByValue.set(value ?? "", nextIndex);
    this._indexByLabel.set(label ?? "", nextIndex);
    if (selected) {
      this._selectedIndex = nextIndex;
      this._selectedIndexes.add(nextIndex);
      this._activeIndex = nextIndex;
    }
    this._options.push({
      index: nextIndex,
      filteredIndex: nextIndex,
      description: description ?? "",
      disabled: disabled ?? false,
      label: label ?? "",
      selected: selected ?? false,
      value: value ?? "",
      visible,
      ranges
    });
    if (visible) {
      this._numOfVisibleOptions += 1;
    }
  }
  clear() {
    this._options = [];
    this._indexByValue.clear();
    this._indexByLabel.clear();
    this._numOfVisibleOptions = 0;
    this._selectedIndex = -1;
    this._selectedIndexes.clear();
    this._activeIndex = -1;
  }
  getIsIndexSelected(index) {
    if (this._multiSelect) {
      return this._selectedIndexes.has(index);
    } else {
      return this._selectedIndex === index;
    }
  }
  expandMultiSelection(values) {
    values.forEach((v2) => {
      const foundIndex = this._indexByValue.get(v2) ?? -1;
      if (foundIndex !== -1) {
        this._selectedIndexes.add(foundIndex);
      }
    });
    this._host.requestUpdate();
  }
  toggleActiveMultiselectOption() {
    const activeOption = this._options[this._activeIndex] ?? null;
    if (!activeOption) {
      return;
    }
    const checked = this._selectedIndexes.has(activeOption.index);
    if (checked) {
      this._selectedIndexes.delete(activeOption.index);
    } else {
      this._selectedIndexes.add(activeOption.index);
    }
    this._host.requestUpdate();
  }
  toggleOptionSelected(optIndex) {
    const checked = this._selectedIndexes.has(optIndex);
    this._options[optIndex].selected = !this._options[optIndex].selected;
    if (checked) {
      this._selectedIndexes.delete(optIndex);
    } else {
      this._selectedIndexes.add(optIndex);
    }
    this._host.requestUpdate();
  }
  getActiveOption() {
    return this._options[this._activeIndex] ?? null;
  }
  getSelectedOption() {
    return this._options[this._selectedIndex] ?? null;
  }
  getOptionByIndex(index) {
    return this._options[index] ?? null;
  }
  findOptionIndex(value) {
    return this._indexByValue.get(value) ?? -1;
  }
  getOptionByValue(value, includeHiddenOptions = false) {
    const index = this._indexByValue.get(value) ?? -1;
    if (index === -1) {
      return null;
    }
    if (!includeHiddenOptions) {
      return this._options[index].visible ? this._options[index] : null;
    }
    return this._options[index];
  }
  getOptionByLabel(label) {
    const index = this._indexByLabel.get(label) ?? -1;
    if (index === -1) {
      return null;
    }
    return this._options[index];
  }
  next(fromIndex) {
    const from = fromIndex ?? this._activeIndex;
    let nextIndex = -1;
    for (let i4 = from + 1; i4 < this._options.length; i4++) {
      if (this._options[i4] && !this._options[i4].disabled && this._options[i4].visible) {
        nextIndex = i4;
        break;
      }
    }
    return nextIndex > -1 ? this._options[nextIndex] : null;
  }
  prev(fromIndex) {
    const from = fromIndex ?? this._activeIndex;
    let prevIndex = -1;
    for (let i4 = from - 1; i4 >= 0; i4--) {
      if (this._options[i4] && !this._options[i4].disabled && this._options[i4].visible) {
        prevIndex = i4;
        break;
      }
    }
    return prevIndex > -1 ? this._options[prevIndex] : null;
  }
  activateDefault() {
    if (this._multiSelect) {
      if (this._selectedIndexes.size > 0) {
        const indexes = this._selectedIndexes.values();
        const first = indexes.next();
        this._activeIndex = first.value ? first.value : 0;
      }
    } else {
      if (this._selectedIndex > -1) {
        this._activeIndex = this._selectedIndex;
      } else {
        this._activeIndex = 0;
      }
    }
    this._host.requestUpdate();
  }
  selectAll() {
    if (!this._multiSelect) {
      return;
    }
    this._options.forEach((_2, i4) => {
      this._options[i4].selected = true;
      this._selectedIndexes.add(i4);
    });
    this._host.requestUpdate();
  }
  selectNone() {
    if (!this._multiSelect) {
      return;
    }
    this._options.forEach((_2, i4) => {
      this._options[i4].selected = false;
    });
    this._selectedIndexes.clear();
    this._host.requestUpdate();
  }
  //#endregion
  //#region private functions
  _searchByPattern(text) {
    let result;
    switch (this._filterMethod) {
      case "startsWithPerTerm":
        result = startsWithPerTermSearch(text, this._filterPattern);
        break;
      case "startsWith":
        result = startsWithSearch(text, this._filterPattern);
        break;
      case "contains":
        result = containsSearch(text, this._filterPattern);
        break;
      default:
        result = fuzzySearch(text, this._filterPattern);
    }
    return result;
  }
  _updateState() {
    if (!this._combobox || this._filterPattern === "") {
      this._options.forEach((_2, i4) => {
        this._options[i4].visible = true;
        this._options[i4].ranges = [];
      });
      this._numOfVisibleOptions = this._options.length;
    } else {
      let filteredListNextIndex = -1;
      this._numOfVisibleOptions = 0;
      this._options.forEach(({ label }, i4) => {
        const result = this._searchByPattern(label);
        this._options[i4].visible = result.match;
        this._options[i4].ranges = result.ranges;
        this._options[i4].filteredIndex = result.match ? ++filteredListNextIndex : -1;
        if (result.match) {
          this._numOfVisibleOptions += 1;
        }
      });
    }
    this._host.requestUpdate();
  }
}
const styles$l = [
  defaultStyles,
  i$6`
    :host {
      display: block;
      position: relative;
    }

    .scrollable-container {
      height: 100%;
      overflow: auto;
    }

    .scrollable-container::-webkit-scrollbar {
      cursor: default;
      width: 0;
    }

    .scrollable-container {
      scrollbar-width: none;
    }

    .shadow {
      box-shadow: var(--vscode-scrollbar-shadow, #000000) 0 6px 6px -6px inset;
      display: none;
      height: 3px;
      left: 0;
      pointer-events: none;
      position: absolute;
      top: 0;
      z-index: 1;
      width: 100%;
    }

    .shadow.visible {
      display: block;
    }

    .scrollbar-track {
      height: 100%;
      position: absolute;
      right: 0;
      top: 0;
      width: 10px;
      z-index: 100;
    }

    .scrollbar-track.hidden {
      display: none;
    }

    .scrollbar-thumb {
      background-color: transparent;
      min-height: var(--min-thumb-height, 20px);
      opacity: 0;
      position: absolute;
      right: 0;
      width: 10px;
    }

    .scrollbar-thumb.visible {
      background-color: var(
        --vscode-scrollbarSlider-background,
        rgba(121, 121, 121, 0.4)
      );
      opacity: 1;
      transition: opacity 100ms;
    }

    .scrollbar-thumb.fade {
      background-color: var(
        --vscode-scrollbarSlider-background,
        rgba(121, 121, 121, 0.4)
      );
      opacity: 0;
      transition: opacity 800ms;
    }

    .scrollbar-thumb.visible:hover {
      background-color: var(
        --vscode-scrollbarSlider-hoverBackground,
        rgba(100, 100, 100, 0.7)
      );
    }

    .scrollbar-thumb.visible.active,
    .scrollbar-thumb.visible.active:hover {
      background-color: var(
        --vscode-scrollbarSlider-activeBackground,
        rgba(191, 191, 191, 0.4)
      );
    }

    .prevent-interaction {
      bottom: 0;
      left: 0;
      right: 0;
      top: 0;
      position: absolute;
      z-index: 99;
    }

    .content {
      overflow: hidden;
    }
  `
];
var __decorate$n = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeScrollable = class VscodeScrollable2 extends VscElement {
  /**
   * Scroll position.
   */
  set scrollPos(val) {
    this._scrollPos = this._limitScrollPos(val);
    this._updateScrollbar();
    this._updateThumbPosition();
    this.requestUpdate();
  }
  get scrollPos() {
    return this._scrollPos;
  }
  /**
   * The maximum amount of the `scrollPos`.
   */
  get scrollMax() {
    if (!this._scrollableContainer) {
      return 0;
    }
    return this._scrollableContainer.scrollHeight - this._scrollableContainer.clientHeight;
  }
  //#region lifecycle methods
  constructor() {
    super();
    this.alwaysVisible = false;
    this.fastScrollSensitivity = 5;
    this.minThumbSize = 20;
    this.mouseWheelScrollSensitivity = 1;
    this.shadow = true;
    this.scrolled = false;
    this._scrollPos = 0;
    this._isDragging = false;
    this._thumbHeight = 0;
    this._thumbY = 0;
    this._thumbVisible = false;
    this._thumbFade = false;
    this._thumbActive = false;
    this._componentHeight = 0;
    this._contentHeight = 0;
    this._scrollThumbStartY = 0;
    this._mouseStartY = 0;
    this._scrollbarVisible = true;
    this._scrollbarTrackZ = 0;
    this._resizeObserverCallback = () => {
      this._componentHeight = this.offsetHeight;
      this._contentHeight = this._contentElement.offsetHeight;
      this._updateScrollbar();
      this._updateThumbPosition();
    };
    this._handleSlotChange = () => {
      this._updateScrollbar();
      this._updateThumbPosition();
      this._zIndexFix();
    };
    this._handleScrollThumbMouseMove = (event) => {
      const rawThumbPos = this._scrollThumbStartY + (event.screenY - this._mouseStartY);
      this._thumbY = this._limitThumbPos(rawThumbPos);
      this.scrollPos = this._calculateScrollPosFromThumbPos(this._thumbY);
      this.dispatchEvent(new CustomEvent("vsc-scrollable-scroll", {
        detail: this.scrollPos
      }));
    };
    this._handleScrollThumbMouseUp = (event) => {
      this._isDragging = false;
      this._thumbActive = false;
      const cr = this.getBoundingClientRect();
      const { x: x2, y: y3, width, height } = cr;
      const { pageX, pageY } = event;
      if (pageX > x2 + width || pageX < x2 || pageY > y3 + height || pageY < y3) {
        this._thumbFade = true;
        this._thumbVisible = false;
      }
      document.removeEventListener("mousemove", this._handleScrollThumbMouseMove);
      document.removeEventListener("mouseup", this._handleScrollThumbMouseUp);
    };
    this._handleComponentMouseOver = () => {
      this._thumbVisible = true;
      this._thumbFade = false;
    };
    this._handleComponentMouseOut = () => {
      if (!this._thumbActive) {
        this._thumbVisible = false;
        this._thumbFade = true;
      }
    };
    this._handleComponentWheel = (ev) => {
      if (this._contentHeight <= this._componentHeight) {
        return;
      }
      ev.preventDefault();
      const multiplier = ev.altKey ? this.mouseWheelScrollSensitivity * this.fastScrollSensitivity : this.mouseWheelScrollSensitivity;
      this.scrollPos = this._limitScrollPos(this.scrollPos + ev.deltaY * multiplier);
      this.dispatchEvent(new CustomEvent("vsc-scrollable-scroll", {
        detail: this.scrollPos
      }));
    };
    this._handleScrollableContainerScroll = (ev) => {
      if (ev.currentTarget) {
        this.scrollPos = ev.currentTarget.scrollTop;
      }
    };
    this.addEventListener("mouseover", this._handleComponentMouseOver);
    this.addEventListener("mouseout", this._handleComponentMouseOut);
    this.addEventListener("wheel", this._handleComponentWheel);
  }
  connectedCallback() {
    super.connectedCallback();
    this._hostResizeObserver = new ResizeObserver(this._resizeObserverCallback);
    this._contentResizeObserver = new ResizeObserver(this._resizeObserverCallback);
    this.requestUpdate();
    this.updateComplete.then(() => {
      this._hostResizeObserver.observe(this);
      this._contentResizeObserver.observe(this._contentElement);
      this._updateThumbPosition();
    });
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._hostResizeObserver.unobserve(this);
    this._hostResizeObserver.disconnect();
    this._contentResizeObserver.unobserve(this._contentElement);
    this._contentResizeObserver.disconnect();
  }
  firstUpdated(_changedProperties) {
    this._updateThumbPosition();
  }
  _calcThumbHeight() {
    const componentHeight = this.offsetHeight;
    const contentHeight = this._contentElement?.offsetHeight ?? 0;
    const proposedSize = componentHeight * (componentHeight / contentHeight);
    return Math.max(this.minThumbSize, proposedSize);
  }
  _updateScrollbar() {
    const contentHeight = this._contentElement?.offsetHeight ?? 0;
    const componentHeight = this.offsetHeight;
    if (componentHeight >= contentHeight) {
      this._scrollbarVisible = false;
    } else {
      this._scrollbarVisible = true;
      this._thumbHeight = this._calcThumbHeight();
    }
    this.requestUpdate();
  }
  _zIndexFix() {
    let highestZ = 0;
    this._assignedElements.forEach((n3) => {
      if ("style" in n3) {
        const computedZIndex = window.getComputedStyle(n3).zIndex;
        const isNumber = /([0-9-])+/g.test(computedZIndex);
        if (isNumber) {
          highestZ = Number(computedZIndex) > highestZ ? Number(computedZIndex) : highestZ;
        }
      }
    });
    this._scrollbarTrackZ = highestZ + 1;
    this.requestUpdate();
  }
  _updateThumbPosition() {
    if (!this._scrollableContainer) {
      return;
    }
    this.scrolled = this.scrollPos > 0;
    const componentH = this.offsetHeight;
    const thumbH = this._thumbHeight;
    const contentH = this._contentElement.offsetHeight;
    const overflown = contentH - componentH;
    const ratio = this.scrollPos / overflown;
    const thumbYMax = componentH - thumbH;
    this._thumbY = Math.min(ratio * (componentH - thumbH), thumbYMax);
  }
  _calculateScrollPosFromThumbPos(scrollPos) {
    const cmpH = this.getBoundingClientRect().height;
    const thumbH = this._scrollThumbElement.getBoundingClientRect().height;
    const contentH = this._contentElement.getBoundingClientRect().height;
    const rawScrollPos = scrollPos / (cmpH - thumbH) * (contentH - cmpH);
    return this._limitScrollPos(rawScrollPos);
  }
  _limitScrollPos(newPos) {
    if (newPos < 0) {
      return 0;
    } else if (newPos > this.scrollMax) {
      return this.scrollMax;
    } else {
      return newPos;
    }
  }
  _limitThumbPos(newPos) {
    const cmpH = this.getBoundingClientRect().height;
    const thumbH = this._scrollThumbElement.getBoundingClientRect().height;
    if (newPos < 0) {
      return 0;
    } else if (newPos > cmpH - thumbH) {
      return cmpH - thumbH;
    } else {
      return newPos;
    }
  }
  _handleScrollThumbMouseDown(event) {
    const cmpCr = this.getBoundingClientRect();
    const thCr = this._scrollThumbElement.getBoundingClientRect();
    this._mouseStartY = event.screenY;
    this._scrollThumbStartY = thCr.top - cmpCr.top;
    this._isDragging = true;
    this._thumbActive = true;
    document.addEventListener("mousemove", this._handleScrollThumbMouseMove);
    document.addEventListener("mouseup", this._handleScrollThumbMouseUp);
  }
  _handleScrollbarTrackPress(ev) {
    if (ev.target !== ev.currentTarget) {
      return;
    }
    this._thumbY = ev.offsetY - this._thumbHeight / 2;
    this.scrollPos = this._calculateScrollPosFromThumbPos(this._thumbY);
  }
  //#endregion
  render() {
    return b`
      <div
        class="scrollable-container"
        .style=${stylePropertyMap({
      userSelect: this._isDragging ? "none" : "auto"
    })}
        .scrollTop=${this.scrollPos}
        @scroll=${this._handleScrollableContainerScroll}
      >
        <div
          class=${e$2({ shadow: true, visible: this.scrolled })}
          .style=${stylePropertyMap({
      zIndex: String(this._scrollbarTrackZ)
    })}
        ></div>
        ${this._isDragging ? b`<div class="prevent-interaction"></div>` : A}
        <div
          class=${e$2({
      "scrollbar-track": true,
      hidden: !this._scrollbarVisible
    })}
          @mousedown=${this._handleScrollbarTrackPress}
        >
          <div
            class=${e$2({
      "scrollbar-thumb": true,
      visible: this.alwaysVisible ? true : this._thumbVisible,
      fade: this.alwaysVisible ? false : this._thumbFade,
      active: this._thumbActive
    })}
            .style=${stylePropertyMap({
      height: `${this._thumbHeight}px`,
      top: `${this._thumbY}px`
    })}
            @mousedown=${this._handleScrollThumbMouseDown}
          ></div>
        </div>
        <div class="content">
          <slot @slotchange=${this._handleSlotChange}></slot>
        </div>
      </div>
    `;
  }
};
VscodeScrollable.styles = styles$l;
__decorate$n([
  n$3({ type: Boolean, reflect: true, attribute: "always-visible" })
], VscodeScrollable.prototype, "alwaysVisible", void 0);
__decorate$n([
  n$3({ type: Number, attribute: "fast-scroll-sensitivity" })
], VscodeScrollable.prototype, "fastScrollSensitivity", void 0);
__decorate$n([
  n$3({ type: Number, attribute: "min-thumb-size" })
], VscodeScrollable.prototype, "minThumbSize", void 0);
__decorate$n([
  n$3({ type: Number, attribute: "mouse-wheel-scroll-sensitivity" })
], VscodeScrollable.prototype, "mouseWheelScrollSensitivity", void 0);
__decorate$n([
  n$3({ type: Boolean, reflect: true })
], VscodeScrollable.prototype, "shadow", void 0);
__decorate$n([
  n$3({ type: Boolean, reflect: true })
], VscodeScrollable.prototype, "scrolled", void 0);
__decorate$n([
  n$3({ type: Number, attribute: "scroll-pos" })
], VscodeScrollable.prototype, "scrollPos", null);
__decorate$n([
  r$1()
], VscodeScrollable.prototype, "_isDragging", void 0);
__decorate$n([
  r$1()
], VscodeScrollable.prototype, "_thumbHeight", void 0);
__decorate$n([
  r$1()
], VscodeScrollable.prototype, "_thumbY", void 0);
__decorate$n([
  r$1()
], VscodeScrollable.prototype, "_thumbVisible", void 0);
__decorate$n([
  r$1()
], VscodeScrollable.prototype, "_thumbFade", void 0);
__decorate$n([
  r$1()
], VscodeScrollable.prototype, "_thumbActive", void 0);
__decorate$n([
  e$5(".content")
], VscodeScrollable.prototype, "_contentElement", void 0);
__decorate$n([
  e$5(".scrollbar-thumb", true)
], VscodeScrollable.prototype, "_scrollThumbElement", void 0);
__decorate$n([
  e$5(".scrollable-container")
], VscodeScrollable.prototype, "_scrollableContainer", void 0);
__decorate$n([
  o$1()
], VscodeScrollable.prototype, "_assignedElements", void 0);
VscodeScrollable = __decorate$n([
  customElement("vscode-scrollable")
], VscodeScrollable);
var __decorate$m = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
const VISIBLE_OPTS = 10;
const OPT_HEIGHT = 22;
class VscodeSelectBase extends VscElement {
  /**
   * Options can be filtered by typing into a text input field.
   */
  set combobox(enabled) {
    this._opts.comboboxMode = enabled;
  }
  get combobox() {
    return this._opts.comboboxMode;
  }
  /**
   * The element cannot be used and is not focusable.
   */
  set disabled(newState) {
    this._disabled = newState;
    this.ariaDisabled = newState ? "true" : "false";
    if (newState === true) {
      this._originalTabIndex = this.tabIndex;
      this.tabIndex = -1;
    } else {
      this.tabIndex = this._originalTabIndex ?? 0;
      this._originalTabIndex = void 0;
    }
    this.requestUpdate();
  }
  get disabled() {
    return this._disabled;
  }
  /**
   * Search method in the filtered list within the combobox mode.
   *
   * - contains - The list item includes the searched pattern at any position.
   * - fuzzy - The list item contains the letters of the search pattern in the same order, but at any position.
   * - startsWith - The search pattern matches the beginning of the searched text.
   * - startsWithPerTerm - The search pattern matches the beginning of any word in the searched text.
   *
   * @default 'fuzzy'
   */
  set filter(val) {
    const validValues = [
      "contains",
      "fuzzy",
      "startsWith",
      "startsWithPerTerm"
    ];
    let fm;
    if (validValues.includes(val)) {
      fm = val;
    } else {
      this.warn(`Invalid filter: "${val}", fallback to default. Valid values are: "contains", "fuzzy", "startsWith", "startsWithPerm".`);
      fm = "fuzzy";
    }
    this._opts.filterMethod = fm;
  }
  get filter() {
    return this._opts.filterMethod;
  }
  /**
   * @attr [options=[]]
   * @type {Option[]}
   */
  set options(opts) {
    this._opts.populate(opts);
  }
  get options() {
    return this._opts.options.map(({ label, value, description, selected, disabled }) => ({
      label,
      value,
      description,
      selected,
      disabled
    }));
  }
  //#region lifecycle callbacks
  constructor() {
    super();
    this.creatable = false;
    this.label = "";
    this.invalid = false;
    this.focused = false;
    this.open = false;
    this.position = "below";
    this._prevXPos = 0;
    this._prevYPos = 0;
    this._opts = new OptionListController(this);
    this._firstUpdateCompleted = false;
    this._currentDescription = "";
    this._filter = "fuzzy";
    this._selectedIndexes = [];
    this._options = [];
    this._value = "";
    this._values = [];
    this._isPlaceholderOptionActive = false;
    this._isBeingFiltered = false;
    this._optionListScrollPos = 0;
    this._isHoverForbidden = false;
    this._disabled = false;
    this._originalTabIndex = void 0;
    this._onMouseMove = () => {
      this._isHoverForbidden = false;
      window.removeEventListener("mousemove", this._onMouseMove);
    };
    this._onOptionListScroll = (ev) => {
      this._optionListScrollPos = ev.detail;
    };
    this._onComponentKeyDown = (event) => {
      if ([" ", "ArrowUp", "ArrowDown", "Escape"].includes(event.key)) {
        event.stopPropagation();
        event.preventDefault();
      }
      if (event.key === "Enter") {
        this._onEnterKeyDown(event);
      }
      if (event.key === " ") {
        this._onSpaceKeyDown();
      }
      if (event.key === "Escape") {
        this._onEscapeKeyDown();
      }
      if (event.key === "ArrowUp") {
        this._onArrowUpKeyDown();
      }
      if (event.key === "ArrowDown") {
        this._onArrowDownKeyDown();
      }
    };
    this._onComponentFocus = () => {
      this.focused = true;
    };
    this._onComponentBlur = () => {
      this.focused = false;
    };
    this._handleWindowScroll = () => {
      const { x: x2, y: y3 } = this.getBoundingClientRect();
      if (x2 !== this._prevXPos || y3 !== this._prevYPos) {
        this.open = false;
      }
    };
    this.addEventListener("vsc-option-state-change", (ev) => {
      ev.stopPropagation();
      this._setStateFromSlottedElements();
      this.requestUpdate();
    });
  }
  connectedCallback() {
    super.connectedCallback();
    this.addEventListener("keydown", this._onComponentKeyDown);
    this.addEventListener("focus", this._onComponentFocus);
    this.addEventListener("blur", this._onComponentBlur);
    this._setAutoFocus();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener("keydown", this._onComponentKeyDown);
    this.removeEventListener("focus", this._onComponentFocus);
    this.removeEventListener("blur", this._onComponentBlur);
  }
  firstUpdated(_changedProperties) {
    this._firstUpdateCompleted = true;
  }
  willUpdate(changedProperties) {
    if (changedProperties.has("required") && this._firstUpdateCompleted) {
      this._manageRequired();
    }
    if (changedProperties.has("open") && this._firstUpdateCompleted) {
      if (this.open) {
        this._dropdownEl.showPopover();
        const { x: x2, y: y3 } = this.getBoundingClientRect();
        this._prevXPos = x2;
        this._prevYPos = y3;
        window.addEventListener("scroll", this._handleWindowScroll, {
          capture: true
        });
        this._opts.activateDefault();
        this._scrollActiveElementToTop();
      } else {
        this._dropdownEl.hidePopover();
        window.removeEventListener("scroll", this._handleWindowScroll);
      }
    }
  }
  get _filteredOptions() {
    if (!this.combobox || this._opts.filterPattern === "") {
      return this._options;
    }
    return filterOptionsByPattern(this._options, this._opts.filterPattern, this._filter);
  }
  _setAutoFocus() {
    if (this.hasAttribute("autofocus")) {
      if (this.tabIndex < 0) {
        this.tabIndex = 0;
      }
      if (this.combobox) {
        this.updateComplete.then(() => {
          this.shadowRoot?.querySelector(".combobox-input").focus();
        });
      } else {
        this.updateComplete.then(() => {
          this.shadowRoot?.querySelector(".select-face").focus();
        });
      }
    }
  }
  get _isSuggestedOptionVisible() {
    if (!(this.combobox && this.creatable)) {
      return false;
    }
    const filterPatternExistsAsOption = this._opts.getOptionByValue(this._opts.filterPattern) !== null;
    const filtered = this._opts.filterPattern.length > 0;
    return !filterPatternExistsAsOption && filtered;
  }
  _manageRequired() {
  }
  _setStateFromSlottedElements() {
    const optionElements = this._assignedOptions ?? [];
    this._opts.clear();
    optionElements.forEach((el) => {
      const { innerText, description, disabled } = el;
      const value = typeof el.value === "string" ? el.value : innerText.trim();
      const selected = el.selected ?? false;
      const op = {
        label: innerText.trim(),
        value,
        description,
        selected,
        disabled
      };
      this._opts.add(op);
    });
  }
  _createSuggestedOption() {
    const nextSelectedIndex = this._opts.numOptions;
    const op = document.createElement("vscode-option");
    op.value = this._opts.filterPattern;
    D(this._opts.filterPattern, op);
    this.appendChild(op);
    return nextSelectedIndex;
  }
  _dispatchChangeEvent() {
    this.dispatchEvent(new Event("change"));
    this.dispatchEvent(new Event("input"));
  }
  async _createAndSelectSuggestedOption() {
  }
  _toggleComboboxDropdown() {
    this._opts.filterPattern = "";
    this.open = !this.open;
  }
  _scrollActiveElementToTop() {
    this._optionListScrollPos = Math.floor(this._opts.relativeActiveIndex * OPT_HEIGHT);
  }
  async _adjustOptionListScrollPos(direction, optionIndex) {
    let numOpts = this._opts.numOfVisibleOptions;
    const suggestedOptionVisible = this._isSuggestedOptionVisible;
    if (suggestedOptionVisible) {
      numOpts += 1;
    }
    if (numOpts <= VISIBLE_OPTS) {
      return;
    }
    this._isHoverForbidden = true;
    window.addEventListener("mousemove", this._onMouseMove);
    const ulScrollTop = this._optionListScrollPos;
    const liPosY = optionIndex * OPT_HEIGHT;
    const fullyVisible = liPosY >= ulScrollTop && liPosY <= ulScrollTop + VISIBLE_OPTS * OPT_HEIGHT - OPT_HEIGHT;
    if (direction === "down") {
      if (!fullyVisible) {
        this._optionListScrollPos = optionIndex * OPT_HEIGHT - (VISIBLE_OPTS - 1) * OPT_HEIGHT;
      }
    }
    if (direction === "up") {
      if (!fullyVisible) {
        this._optionListScrollPos = Math.floor(this._opts.relativeActiveIndex * OPT_HEIGHT);
      }
    }
  }
  //#region event handlers
  _onFaceClick() {
    this.open = !this.open;
  }
  _handleDropdownToggle(event) {
    this.open = event.newState === "open";
  }
  _onComboboxButtonClick() {
    this._toggleComboboxDropdown();
  }
  _onComboboxButtonKeyDown(ev) {
    if (ev.key === "Enter") {
      this._toggleComboboxDropdown();
    }
  }
  _onOptionMouseOver(ev) {
    if (this._isHoverForbidden) {
      return;
    }
    const el = ev.target;
    if (!el.matches(".option")) {
      return;
    }
    if (el.matches(".placeholder")) {
      this._isPlaceholderOptionActive = true;
      this._opts.activeIndex = -1;
    } else {
      this._isPlaceholderOptionActive = false;
      this._opts.activeIndex = +el.dataset.index;
    }
  }
  _onPlaceholderOptionMouseOut() {
    this._isPlaceholderOptionActive = false;
  }
  _onNoOptionsClick(ev) {
    ev.stopPropagation();
  }
  _onEnterKeyDown(ev) {
    this._isBeingFiltered = false;
    const clickedOnAcceptButton = ev?.composedPath ? ev.composedPath().find((el) => el.matches ? el.matches("vscode-button.button-accept") : false) : false;
    if (clickedOnAcceptButton) {
      return;
    }
  }
  _onSpaceKeyDown() {
    if (!this.open) {
      this.open = true;
      return;
    }
  }
  _onArrowUpKeyDown() {
    if (this.open) {
      if (this._opts.activeIndex <= 0 && !(this.combobox && this.creatable)) {
        return;
      }
      if (this._isPlaceholderOptionActive) {
        const optionIndex = this._opts.numOfVisibleOptions - 1;
        this._opts.activeIndex = optionIndex;
        this._isPlaceholderOptionActive = false;
      } else {
        const prevOp = this._opts.prev();
        if (prevOp !== null) {
          this._opts.activeIndex = prevOp?.index ?? -1;
          const prevSelectableIndex = prevOp?.filteredIndex ?? -1;
          if (prevSelectableIndex > -1) {
            this._adjustOptionListScrollPos("up", prevSelectableIndex);
          }
        }
      }
    } else {
      this.open = true;
      this._opts.activateDefault();
    }
  }
  _onArrowDownKeyDown() {
    let numOpts = this._opts.numOfVisibleOptions;
    const suggestedOptionVisible = this._isSuggestedOptionVisible;
    if (suggestedOptionVisible) {
      numOpts += 1;
    }
    if (this.open) {
      if (this._isPlaceholderOptionActive && this._opts.activeIndex === -1) {
        return;
      }
      const nextOp = this._opts.next();
      if (suggestedOptionVisible && nextOp === null) {
        this._isPlaceholderOptionActive = true;
        this._adjustOptionListScrollPos("down", numOpts - 1);
        this._opts.activeIndex = -1;
      } else if (nextOp !== null) {
        const nextSelectableIndex = nextOp?.filteredIndex ?? -1;
        this._opts.activeIndex = nextOp?.index ?? -1;
        if (nextSelectableIndex > -1) {
          this._adjustOptionListScrollPos("down", nextSelectableIndex);
        }
      }
    } else {
      this.open = true;
      this._opts.activateDefault();
    }
  }
  _onEscapeKeyDown() {
    this.open = false;
  }
  _onSlotChange() {
    this._setStateFromSlottedElements();
    this.requestUpdate();
  }
  _onComboboxInputFocus(ev) {
    ev.target.select();
    this._isBeingFiltered = false;
    this._opts.filterPattern = "";
  }
  _onComboboxInputBlur() {
    this._isBeingFiltered = false;
  }
  _onComboboxInputInput(ev) {
    this._isBeingFiltered = true;
    this._opts.filterPattern = ev.target.value;
    this._opts.activeIndex = -1;
    this.open = true;
  }
  _onComboboxInputClick() {
    this._isBeingFiltered = this._opts.filterPattern !== "";
    this.open = true;
  }
  _onComboboxInputSpaceKeyDown(ev) {
    if (ev.key === " ") {
      ev.stopPropagation();
    }
  }
  _onOptionClick(_ev) {
    this._isBeingFiltered = false;
    return;
  }
  //#endregion
  //#region render functions
  _renderCheckbox(checked, label) {
    const checkboxClasses = {
      "checkbox-icon": true,
      checked
    };
    return b`<span class=${e$2(checkboxClasses)}>${checkIcon}</span
      ><span class="option-label">${label}</span>`;
  }
  _renderOptions() {
    const list = this._opts.options;
    return b`
      <ul
        aria-label=${o(this.label ?? void 0)}
        aria-multiselectable=${o(this._opts.multiSelect ? "true" : void 0)}
        class="options"
        id="select-listbox"
        role="listbox"
        tabindex="-1"
        @click=${this._onOptionClick}
        @mouseover=${this._onOptionMouseOver}
      >
        ${c$1(list, (op) => op.index, (op, index) => {
      if (!op.visible) {
        return A;
      }
      const active = op.index === this._opts.activeIndex && !op.disabled;
      const selected = this._opts.getIsIndexSelected(op.index);
      const optionClasses = {
        active,
        disabled: op.disabled,
        option: true,
        "single-select": !this._opts.multiSelect,
        "multi-select": this._opts.multiSelect,
        selected
      };
      const labelText = op.ranges?.length ?? 0 > 0 ? highlightRanges(op.label, op.ranges ?? []) : op.label;
      return b`
              <li
                aria-selected=${selected ? "true" : "false"}
                class=${e$2(optionClasses)}
                data-index=${op.index}
                data-filtered-index=${index}
                id=${`op-${op.index}`}
                role="option"
                tabindex="-1"
              >
                ${n$1(this._opts.multiSelect, () => this._renderCheckbox(selected, labelText), () => labelText)}
              </li>
            `;
    })}
        ${this._renderPlaceholderOption(this._opts.numOfVisibleOptions < 1)}
      </ul>
    `;
  }
  _renderPlaceholderOption(isListEmpty) {
    if (!this.combobox) {
      return A;
    }
    const foundOption = this._opts.getOptionByLabel(this._opts.filterPattern);
    if (foundOption) {
      return A;
    }
    if (this.creatable && this._opts.filterPattern.length > 0) {
      return b`<li
        class=${e$2({
        option: true,
        placeholder: true,
        active: this._isPlaceholderOptionActive
      })}
        @mouseout=${this._onPlaceholderOptionMouseOut}
      >
        Add "${this._opts.filterPattern}"
      </li>`;
    } else {
      return isListEmpty ? b`<li class="no-options" @click=${this._onNoOptionsClick}>
            No options
          </li>` : A;
    }
  }
  _renderDescription() {
    const op = this._opts.getActiveOption();
    if (!op) {
      return A;
    }
    const { description } = op;
    return description ? b`<div class="description">${description}</div>` : A;
  }
  _renderSelectFace() {
    return b`${A}`;
  }
  _renderComboboxFace() {
    return b`${A}`;
  }
  _renderDropdownControls() {
    return b`${A}`;
  }
  _renderDropdown() {
    const classes = {
      dropdown: true,
      multiple: this._opts.multiSelect,
      open: this.open
    };
    const visibleOptions = this._isSuggestedOptionVisible || this._opts.numOfVisibleOptions === 0 ? this._opts.numOfVisibleOptions + 1 : this._opts.numOfVisibleOptions;
    const scrollPaneHeight = Math.min(visibleOptions * OPT_HEIGHT, VISIBLE_OPTS * OPT_HEIGHT);
    const cr = this.getBoundingClientRect();
    const dropdownStyles = {
      width: `${cr.width}px`,
      left: `${cr.left}px`,
      top: this.position === "below" ? `${cr.top + cr.height}px` : "unset",
      bottom: this.position === "below" ? "unset" : `${document.documentElement.clientHeight - cr.top}px`
    };
    return b`
      <div
        class=${e$2(classes)}
        popover="auto"
        @toggle=${this._handleDropdownToggle}
        .style=${stylePropertyMap(dropdownStyles)}
      >
        ${this.position === "above" ? this._renderDescription() : A}
        <vscode-scrollable
          always-visible
          class="scrollable"
          min-thumb-size="40"
          tabindex="-1"
          @vsc-scrollable-scroll=${this._onOptionListScroll}
          .scrollPos=${this._optionListScrollPos}
          .style=${stylePropertyMap({
      height: `${scrollPaneHeight}px`
    })}
        >
          ${this._renderOptions()} ${this._renderDropdownControls()}
        </vscode-scrollable>
        ${this.position === "below" ? this._renderDescription() : A}
      </div>
    `;
  }
}
__decorate$m([
  n$3({ type: Boolean, reflect: true })
], VscodeSelectBase.prototype, "creatable", void 0);
__decorate$m([
  n$3({ type: Boolean, reflect: true })
], VscodeSelectBase.prototype, "combobox", null);
__decorate$m([
  n$3({ reflect: true })
], VscodeSelectBase.prototype, "label", void 0);
__decorate$m([
  n$3({ type: Boolean, reflect: true })
], VscodeSelectBase.prototype, "disabled", null);
__decorate$m([
  n$3({ type: Boolean, reflect: true })
], VscodeSelectBase.prototype, "invalid", void 0);
__decorate$m([
  n$3()
], VscodeSelectBase.prototype, "filter", null);
__decorate$m([
  n$3({ type: Boolean, reflect: true })
], VscodeSelectBase.prototype, "focused", void 0);
__decorate$m([
  n$3({ type: Boolean, reflect: true })
], VscodeSelectBase.prototype, "open", void 0);
__decorate$m([
  n$3({ type: Array })
], VscodeSelectBase.prototype, "options", null);
__decorate$m([
  n$3({ reflect: true })
], VscodeSelectBase.prototype, "position", void 0);
__decorate$m([
  o$1({
    flatten: true,
    selector: "vscode-option"
  })
], VscodeSelectBase.prototype, "_assignedOptions", void 0);
__decorate$m([
  e$5(".dropdown", true)
], VscodeSelectBase.prototype, "_dropdownEl", void 0);
__decorate$m([
  r$1()
], VscodeSelectBase.prototype, "_currentDescription", void 0);
__decorate$m([
  r$1()
], VscodeSelectBase.prototype, "_filter", void 0);
__decorate$m([
  r$1()
], VscodeSelectBase.prototype, "_filteredOptions", null);
__decorate$m([
  r$1()
], VscodeSelectBase.prototype, "_selectedIndexes", void 0);
__decorate$m([
  r$1()
], VscodeSelectBase.prototype, "_options", void 0);
__decorate$m([
  r$1()
], VscodeSelectBase.prototype, "_value", void 0);
__decorate$m([
  r$1()
], VscodeSelectBase.prototype, "_values", void 0);
__decorate$m([
  r$1()
], VscodeSelectBase.prototype, "_isPlaceholderOptionActive", void 0);
__decorate$m([
  r$1()
], VscodeSelectBase.prototype, "_isBeingFiltered", void 0);
__decorate$m([
  r$1()
], VscodeSelectBase.prototype, "_optionListScrollPos", void 0);
const styles$k = [
  defaultStyles,
  i$6`
    :host {
      display: inline-block;
      max-width: 100%;
      outline: none;
      position: relative;
      width: 320px;
    }

    .main-slot {
      display: none;
    }

    .select-face,
    .combobox-face {
      background-color: var(--vscode-settings-dropdownBackground, #313131);
      border-color: var(--vscode-settings-dropdownBorder, #3c3c3c);
      border-radius: 4px;
      border-style: solid;
      border-width: 1px;
      box-sizing: border-box;
      color: var(--vscode-settings-dropdownForeground, #cccccc);
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      line-height: 18px;
      position: relative;
      user-select: none;
      width: 100%;
    }

    :host([invalid]) .select-face,
    :host(:invalid) .select-face,
    :host([invalid]) .combobox-face,
    :host(:invalid) .combobox-face {
      background-color: var(--vscode-inputValidation-errorBackground, #5a1d1d);
      border-color: var(--vscode-inputValidation-errorBorder, #be1100);
    }

    .select-face {
      cursor: pointer;
      display: block;
      padding: 3px 4px;
    }

    .select-face .text {
      display: block;
      height: 18px;
      overflow: hidden;
      padding-right: 20px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .select-face.multiselect {
      padding: 0;
    }

    .select-face-badge {
      background-color: var(--vscode-badge-background, #616161);
      border-radius: 2px;
      color: var(--vscode-badge-foreground, #f8f8f8);
      display: inline-block;
      flex-shrink: 0;
      font-size: 11px;
      line-height: 16px;
      margin: 2px;
      padding: 2px 3px;
      white-space: nowrap;
    }

    .select-face-badge.no-item {
      background-color: transparent;
      color: inherit;
    }

    .combobox-face {
      display: flex;
    }

    :host(:focus) .select-face,
    :host(:focus) .combobox-face,
    :host([focused]) .select-face,
    :host([focused]) .combobox-face {
      outline: none;
    }

    :host(:focus:not([open])) .select-face,
    :host(:focus:not([open])) .combobox-face,
    :host([focused]:not([open])) .select-face,
    :host([focused]:not([open])) .combobox-face {
      border-color: var(--vscode-focusBorder, #0078d4);
    }

    .combobox-input {
      background-color: transparent;
      box-sizing: border-box;
      border: 0;
      color: var(--vscode-foreground, #cccccc);
      display: block;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      line-height: 16px;
      padding: 4px;
      width: 100%;
    }

    .combobox-input:focus {
      outline: none;
    }

    .combobox-button {
      align-items: center;
      background-color: transparent;
      border: 0;
      border-radius: 2px;
      box-sizing: content-box;
      color: var(--vscode-foreground, #cccccc);
      cursor: pointer;
      display: flex;
      flex-shrink: 0;
      height: 16px;
      justify-content: center;
      margin: 1px 1px 0 0;
      padding: 3px;
      width: 22px;
    }

    .combobox-button:hover,
    .combobox-button:focus-visible {
      background-color: var(
        --vscode-toolbar-hoverBackground,
        rgba(90, 93, 94, 0.31)
      );
      outline-style: dashed;
      outline-color: var(--vscode-toolbar-hoverOutline, transparent);
    }

    .combobox-button:focus-visible {
      outline: none;
    }

    .icon {
      color: var(--vscode-foreground, #cccccc);
      display: block;
      height: 14px;
      pointer-events: none;
      width: 14px;
    }

    .select-face .icon {
      position: absolute;
      right: 6px;
      top: 5px;
    }

    .icon svg {
      color: var(--vscode-foreground, #cccccc);
      height: 100%;
      width: 100%;
    }

    .dropdown {
      background-color: var(--vscode-settings-dropdownBackground, #313131);
      border-color: var(--vscode-settings-dropdownListBorder, #454545);
      border-radius: 4px;
      border-style: solid;
      border-width: 1px;
      bottom: unset;
      box-shadow: 0 2px 8px var(--vscode-widget-shadow, rgba(0, 0, 0, 0.36));
      box-sizing: border-box;
      display: none;
      padding: 0;
      right: unset;
    }

    .dropdown.open {
      display: block;
    }

    :host([position='above']) .dropdown {
      bottom: 26px;
      padding-bottom: 0;
      padding-top: 2px;
      top: unset;
    }

    .scrollable {
      display: block;
      max-height: 222px;
      margin: 0;
      outline: none;
      overflow: hidden;
    }

    .options {
      box-sizing: border-box;
      cursor: pointer;
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .option {
      box-sizing: border-box;
      color: var(--vscode-foreground, #cccccc);
      cursor: pointer;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      height: 22px;
      line-height: 20px;
      min-height: calc(var(--vscode-font-size) * 1.3);
      padding: 1px 3px;
      user-select: none;
      outline-color: transparent;
      outline-offset: -1px;
      outline-style: solid;
      outline-width: 1px;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }

    .option.single-select {
      display: block;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }

    .option.multi-select {
      align-items: center;
      display: flex;
    }

    .option b {
      color: var(--vscode-list-highlightForeground, #2aaaff);
    }

    .option.active b {
      color: var(--vscode-list-focusHighlightForeground, #2aaaff);
    }

    .option:not(.disabled):hover {
      background-color: var(--vscode-list-hoverBackground, #2a2d2e);
      color: var(--vscode-list-hoverForeground, #ffffff);
    }

    :host-context(body[data-vscode-theme-kind='vscode-high-contrast'])
      .option:hover,
    :host-context(body[data-vscode-theme-kind='vscode-high-contrast-light'])
      .option:hover {
      outline-style: dotted;
      outline-color: var(--vscode-list-focusOutline, #0078d4);
      outline-width: 1px;
    }

    .option.disabled {
      cursor: not-allowed;
      opacity: 0.4;
    }

    .option.active,
    .option.active:hover {
      background-color: var(--vscode-list-activeSelectionBackground, #04395e);
      color: var(--vscode-list-activeSelectionForeground, #ffffff);
      outline-color: var(--vscode-list-activeSelectionBackground, #04395e);
      outline-style: solid;
      outline-width: 1px;
    }

    .no-options {
      align-items: center;
      border-color: transparent;
      border-style: solid;
      border-width: 1px;
      color: var(--vscode-foreground, #cccccc);
      cursor: default;
      display: flex;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      line-height: 18px;
      min-height: calc(var(--vscode-font-size) * 1.3);
      opacity: 0.85;
      padding: 1px 3px;
      user-select: none;
    }

    .placeholder {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .placeholder span {
      font-weight: bold;
    }

    .placeholder:not(.disabled):hover {
      color: var(--vscode-list-activeSelectionForeground, #ffffff);
    }

    :host-context(body[data-vscode-theme-kind='vscode-high-contrast'])
      .option.active,
    :host-context(body[data-vscode-theme-kind='vscode-high-contrast-light'])
      .option.active:hover {
      outline-color: var(--vscode-list-focusOutline, #0078d4);
      outline-style: dashed;
    }

    .option-label {
      display: block;
      overflow: hidden;
      pointer-events: none;
      text-overflow: ellipsis;
      white-space: nowrap;
      width: 100%;
    }

    .dropdown.multiple .option.selected {
      background-color: var(--vscode-list-hoverBackground, #2a2d2e);
      outline-color: var(--vscode-list-hoverBackground, #2a2d2e);
    }

    .dropdown.multiple .option.selected.active {
      background-color: var(--vscode-list-activeSelectionBackground, #04395e);
      color: var(--vscode-list-activeSelectionForeground, #ffffff);
      outline-color: var(--vscode-list-activeSelectionBackground, #04395e);
    }

    .checkbox-icon {
      align-items: center;
      background-color: var(--vscode-checkbox-background, #313131);
      border-radius: 2px;
      border: 1px solid var(--vscode-checkbox-border);
      box-sizing: border-box;
      color: var(--vscode-checkbox-foreground);
      display: flex;
      flex-basis: 15px;
      flex-shrink: 0;
      height: 15px;
      justify-content: center;
      margin-right: 5px;
      overflow: hidden;
      position: relative;
      width: 15px;
    }

    .checkbox-icon svg {
      display: none;
      height: 13px;
      width: 13px;
    }

    .checkbox-icon.checked svg {
      display: block;
    }

    .dropdown-controls {
      display: flex;
      justify-content: flex-end;
      padding: 4px;
    }

    .dropdown-controls :not(:last-child) {
      margin-right: 4px;
    }

    .action-icon {
      align-items: center;
      background-color: transparent;
      border: 0;
      color: var(--vscode-foreground, #cccccc);
      cursor: pointer;
      display: flex;
      height: 24px;
      justify-content: center;
      padding: 0;
      width: 24px;
    }

    .action-icon:focus {
      outline: none;
    }

    .action-icon:focus-visible {
      outline: 1px solid var(--vscode-focusBorder, #0078d4);
      outline-offset: -1px;
    }

    .description {
      border-color: var(--vscode-settings-dropdownBorder, #3c3c3c);
      border-style: solid;
      border-width: 1px 0 0;
      color: var(--vscode-foreground, #cccccc);
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      line-height: 1.3;
      padding: 6px 4px;
      word-wrap: break-word;
    }

    :host([position='above']) .description {
      border-width: 0 0 1px;
    }
  `
];
var __decorate$l = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeMultiSelect = class VscodeMultiSelect2 extends VscodeSelectBase {
  set selectedIndexes(val) {
    this._opts.selectedIndexes = val;
  }
  get selectedIndexes() {
    return this._opts.selectedIndexes;
  }
  set value(val) {
    this._opts.multiSelectValue = val;
    if (this._opts.selectedIndexes.length > 0) {
      this._requestedValueToSetLater = [];
    } else {
      this._requestedValueToSetLater = Array.isArray(val) ? val : [val];
    }
    this._setFormValue();
    this._manageRequired();
  }
  get value() {
    return this._opts.multiSelectValue;
  }
  get form() {
    return this._internals.form;
  }
  /** @internal */
  get type() {
    return "select-multiple";
  }
  get validity() {
    return this._internals.validity;
  }
  get validationMessage() {
    return this._internals.validationMessage;
  }
  get willValidate() {
    return this._internals.willValidate;
  }
  checkValidity() {
    return this._internals.checkValidity();
  }
  reportValidity() {
    return this._internals.reportValidity();
  }
  selectAll() {
    this._opts.selectAll();
  }
  selectNone() {
    this._opts.selectNone();
  }
  constructor() {
    super();
    this.defaultValue = [];
    this.required = false;
    this.name = void 0;
    this._requestedValueToSetLater = [];
    this._onOptionClick = (ev) => {
      const composedPath = ev.composedPath();
      const optEl = composedPath.find((et) => {
        if ("matches" in et) {
          return et.matches("li.option");
        }
        return false;
      });
      if (!optEl) {
        return;
      }
      const isPlaceholderOption = optEl.classList.contains("placeholder");
      if (isPlaceholderOption) {
        this._createAndSelectSuggestedOption();
        return;
      }
      const index = Number(optEl.dataset.index);
      this._opts.toggleOptionSelected(index);
      this._setFormValue();
      this._manageRequired();
      this._dispatchChangeEvent();
    };
    this._opts.multiSelect = true;
    this._internals = this.attachInternals();
  }
  connectedCallback() {
    super.connectedCallback();
    this.updateComplete.then(() => {
      this._setDefaultValue();
      this._manageRequired();
    });
  }
  /** @internal */
  formResetCallback() {
    this.updateComplete.then(() => {
      this.value = this.defaultValue;
    });
  }
  /** @internal */
  formStateRestoreCallback(state, _mode) {
    const entries = Array.from(state.entries()).map((e3) => String(e3[1]));
    this.updateComplete.then(() => {
      this.value = entries;
    });
  }
  _setDefaultValue() {
    if (Array.isArray(this.defaultValue) && this.defaultValue.length > 0) {
      const val = this.defaultValue.map((v2) => String(v2));
      this.value = val;
    }
  }
  _dispatchChangeEvent() {
    super._dispatchChangeEvent();
  }
  _onFaceClick() {
    super._onFaceClick();
    this._opts.activeIndex = 0;
  }
  _toggleComboboxDropdown() {
    super._toggleComboboxDropdown();
    this._opts.activeIndex = -1;
  }
  _manageRequired() {
    const { value } = this;
    if (value.length === 0 && this.required) {
      this._internals.setValidity({
        valueMissing: true
      }, "Please select an item in the list.", this._faceElement);
    } else {
      this._internals.setValidity({});
    }
  }
  _setFormValue() {
    const fd = new FormData();
    this._values.forEach((v2) => {
      fd.append(this.name ?? "", v2);
    });
    this._internals.setFormValue(fd);
  }
  async _createAndSelectSuggestedOption() {
    super._createAndSelectSuggestedOption();
    const nextIndex = this._createSuggestedOption();
    await this.updateComplete;
    this.selectedIndexes = [...this.selectedIndexes, nextIndex];
    this._dispatchChangeEvent();
    const opCreateEvent = new CustomEvent("vsc-multi-select-create-option", { detail: { value: this._opts.getOptionByIndex(nextIndex)?.value ?? "" } });
    this.dispatchEvent(opCreateEvent);
    this.open = false;
    this._isPlaceholderOptionActive = false;
  }
  //#region event handlers
  _onSlotChange() {
    super._onSlotChange();
    if (this._requestedValueToSetLater.length > 0) {
      this._opts.expandMultiSelection(this._requestedValueToSetLater);
      this._requestedValueToSetLater = this._requestedValueToSetLater.filter((v2) => this._opts.findOptionIndex(v2) === -1);
    }
  }
  _onEnterKeyDown(ev) {
    super._onEnterKeyDown(ev);
    if (!this.open) {
      this._opts.filterPattern = "";
      this.open = true;
    } else {
      if (this._isPlaceholderOptionActive) {
        this._createAndSelectSuggestedOption();
      } else {
        this._opts.toggleActiveMultiselectOption();
        this._setFormValue();
        this._manageRequired();
        this._dispatchChangeEvent();
      }
    }
  }
  _onMultiAcceptClick() {
    this.open = false;
  }
  _onMultiDeselectAllClick() {
    this._opts.selectedIndexes = [];
    this._values = [];
    this._options = this._options.map((op) => ({ ...op, selected: false }));
    this._manageRequired();
    this._dispatchChangeEvent();
  }
  _onMultiSelectAllClick() {
    this._opts.selectedIndexes = [];
    this._values = [];
    this._options = this._options.map((op) => ({ ...op, selected: true }));
    this._options.forEach((op, index) => {
      this._selectedIndexes.push(index);
      this._values.push(op.value);
      this._dispatchChangeEvent();
    });
    this._setFormValue();
    this._manageRequired();
  }
  _onComboboxInputBlur() {
    super._onComboboxInputBlur();
    this._opts.filterPattern = "";
  }
  //#endregion
  //#region render functions
  _renderLabel() {
    switch (this._opts.selectedIndexes.length) {
      case 0:
        return b`<span class="select-face-badge no-item">0 Selected</span>`;
      default:
        return b`<span class="select-face-badge"
          >${this._opts.selectedIndexes.length} Selected</span
        >`;
    }
  }
  _renderComboboxFace() {
    const activeDescendant = this._opts.activeIndex > -1 ? `op-${this._opts.activeIndex}` : "";
    const expanded = this.open ? "true" : "false";
    return b`
      <div class="combobox-face face">
        ${this._opts.multiSelect ? this._renderLabel() : A}
        <input
          aria-activedescendant=${activeDescendant}
          aria-autocomplete="list"
          aria-controls="select-listbox"
          aria-expanded=${expanded}
          aria-haspopup="listbox"
          aria-label=${o(this.label)}
          class="combobox-input"
          role="combobox"
          spellcheck="false"
          type="text"
          autocomplete="off"
          .value=${this._opts.filterPattern}
          @focus=${this._onComboboxInputFocus}
          @blur=${this._onComboboxInputBlur}
          @input=${this._onComboboxInputInput}
          @click=${this._onComboboxInputClick}
          @keydown=${this._onComboboxInputSpaceKeyDown}
        />
        <button
          aria-label="Open the list of options"
          class="combobox-button"
          type="button"
          @click=${this._onComboboxButtonClick}
          @keydown=${this._onComboboxButtonKeyDown}
          tabindex="-1"
        >
          ${chevronDownIcon}
        </button>
      </div>
    `;
  }
  _renderSelectFace() {
    const activeDescendant = this._opts.activeIndex > -1 ? `op-${this._opts.activeIndex}` : "";
    const expanded = this.open ? "true" : "false";
    return b`
      <div
        aria-activedescendant=${o(this._opts.multiSelect ? void 0 : activeDescendant)}
        aria-controls="select-listbox"
        aria-expanded=${o(this._opts.multiSelect ? void 0 : expanded)}
        aria-haspopup="listbox"
        aria-label=${o(this.label ?? void 0)}
        class="select-face face multiselect"
        @click=${this._onFaceClick}
        .tabIndex=${this.disabled ? -1 : 0}
      >
        ${this._renderLabel()} ${chevronDownIcon}
      </div>
    `;
  }
  _renderDropdownControls() {
    return this._filteredOptions.length > 0 ? b`
          <div class="dropdown-controls">
            <button
              type="button"
              @click=${this._onMultiSelectAllClick}
              title="Select all"
              class="action-icon"
              id="select-all"
            >
              <vscode-icon name="checklist"></vscode-icon>
            </button>
            <button
              type="button"
              @click=${this._onMultiDeselectAllClick}
              title="Deselect all"
              class="action-icon"
              id="select-none"
            >
              <vscode-icon name="clear-all"></vscode-icon>
            </button>
            <vscode-button
              class="button-accept"
              @click=${this._onMultiAcceptClick}
              >OK</vscode-button
            >
          </div>
        ` : b`${A}`;
  }
  render() {
    return b`
      <div class="multi-select">
        <slot class="main-slot" @slotchange=${this._onSlotChange}></slot>
        ${this.combobox ? this._renderComboboxFace() : this._renderSelectFace()}
        ${this._renderDropdown()}
      </div>
    `;
  }
};
VscodeMultiSelect.styles = styles$k;
VscodeMultiSelect.shadowRootOptions = {
  ...i$3.shadowRootOptions,
  delegatesFocus: true
};
VscodeMultiSelect.formAssociated = true;
__decorate$l([
  n$3({ type: Array, attribute: "default-value" })
], VscodeMultiSelect.prototype, "defaultValue", void 0);
__decorate$l([
  n$3({ type: Boolean, reflect: true })
], VscodeMultiSelect.prototype, "required", void 0);
__decorate$l([
  n$3({ reflect: true })
], VscodeMultiSelect.prototype, "name", void 0);
__decorate$l([
  n$3({ type: Array, attribute: false })
], VscodeMultiSelect.prototype, "selectedIndexes", null);
__decorate$l([
  n$3({ type: Array })
], VscodeMultiSelect.prototype, "value", null);
__decorate$l([
  e$5(".face")
], VscodeMultiSelect.prototype, "_faceElement", void 0);
VscodeMultiSelect = __decorate$l([
  customElement("vscode-multi-select")
], VscodeMultiSelect);
o$7({
  tagName: "vscode-multi-select",
  elementClass: VscodeMultiSelect,
  react: E$1,
  displayName: "VscodeMultiSelect",
  events: {
    onChange: "change",
    onInvalid: "invalid",
    onVscMultiSelectCreateOption: "vsc-multi-select-create-option"
  }
});
const VscodeOption2 = o$7({
  tagName: "vscode-option",
  elementClass: VscodeOption$1,
  react: E$1,
  displayName: "VscodeOption"
});
const styles$j = [
  defaultStyles,
  i$6`
    :host {
      display: block;
      height: 2px;
      width: 100%;
      outline: none;
    }

    .container {
      position: relative;
      width: 100%;
      height: 100%;
      overflow: hidden;
    }

    .track {
      position: absolute;
      inset: 0;
      background: transparent;
    }

    .indicator {
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      height: 100%;
      background: var(--vscode-progressBar-background, #0078d4);
      will-change: transform, width, left;
    }

    /* Determinate mode: width is set inline via style attribute */
    .discrete .indicator {
      transition: width 100ms linear;
    }

    /* Indeterminate mode: VS Code style progress bit */
    .infinite .indicator {
      width: 2%;
      animation-name: progress;
      animation-duration: 4s;
      animation-iteration-count: infinite;
      animation-timing-function: linear;
      transform: translate3d(0px, 0px, 0px);
    }

    /* Long running: reduce GPU pressure using stepped animation */
    .infinite.infinite-long-running .indicator {
      animation-timing-function: steps(100);
    }

    /* Keyframes adapted from VS Code */
    @keyframes progress {
      from {
        transform: translateX(0%) scaleX(1);
      }
      50% {
        transform: translateX(2500%) scaleX(3);
      }
      to {
        transform: translateX(4900%) scaleX(1);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .discrete .indicator {
        transition: none;
      }
      .infinite .indicator,
      .infinite-long-running .indicator {
        animation: none;
        width: 100%;
      }
    }
  `
];
var __decorate$k = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeProgressBar = class VscodeProgressBar2 extends VscElement {
  constructor() {
    super(...arguments);
    this.ariaLabel = "Loading";
    this.max = 100;
    this.indeterminate = false;
    this.longRunningThreshold = 15e3;
    this._longRunning = false;
  }
  get _isDeterminate() {
    return !this.indeterminate && typeof this.value === "number" && isFinite(this.value);
  }
  connectedCallback() {
    super.connectedCallback();
    this._maybeStartLongRunningTimer();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._clearLongRunningTimer();
  }
  willUpdate() {
    this._maybeStartLongRunningTimer();
  }
  render() {
    const max = this.max > 0 ? this.max : 100;
    const clamped = this._isDeterminate ? Math.min(Math.max(this.value ?? 0, 0), max) : 0;
    const percent2 = this._isDeterminate ? clamped / max * 100 : 0;
    const containerClasses = {
      container: true,
      discrete: this._isDeterminate,
      infinite: !this._isDeterminate,
      "infinite-long-running": this._longRunning && !this._isDeterminate
    };
    return b`
      <div
        class=${e$2(containerClasses)}
        part="container"
        role="progressbar"
        aria-label=${this.ariaLabel}
        aria-valuemin="0"
        aria-valuemax=${String(max)}
        aria-valuenow=${o(this._isDeterminate ? String(Math.round(clamped)) : void 0)}
      >
        <div class="track" part="track"></div>
        <div
          class="indicator"
          part="indicator"
          .style=${stylePropertyMap({
      width: this._isDeterminate ? `${percent2}%` : void 0
    })}
        ></div>
      </div>
    `;
  }
  _maybeStartLongRunningTimer() {
    const shouldRun = !this._isDeterminate && this.longRunningThreshold > 0 && this.isConnected;
    if (!shouldRun) {
      this._clearLongRunningTimer();
      this._longRunning = false;
      return;
    }
    if (this._longRunningHandle) {
      return;
    }
    this._longRunningHandle = setTimeout(() => {
      this._longRunning = true;
      this._longRunningHandle = void 0;
      this.requestUpdate();
    }, this.longRunningThreshold);
  }
  _clearLongRunningTimer() {
    if (this._longRunningHandle) {
      clearTimeout(this._longRunningHandle);
      this._longRunningHandle = void 0;
    }
  }
};
VscodeProgressBar.styles = styles$j;
__decorate$k([
  n$3({ reflect: true, attribute: "aria-label" })
], VscodeProgressBar.prototype, "ariaLabel", void 0);
__decorate$k([
  n$3({ type: Number, reflect: true })
], VscodeProgressBar.prototype, "value", void 0);
__decorate$k([
  n$3({ type: Number, reflect: true })
], VscodeProgressBar.prototype, "max", void 0);
__decorate$k([
  n$3({ type: Boolean, reflect: true })
], VscodeProgressBar.prototype, "indeterminate", void 0);
__decorate$k([
  n$3({ type: Number, attribute: "long-running-threshold" })
], VscodeProgressBar.prototype, "longRunningThreshold", void 0);
__decorate$k([
  r$1()
], VscodeProgressBar.prototype, "_longRunning", void 0);
VscodeProgressBar = __decorate$k([
  customElement("vscode-progress-bar")
], VscodeProgressBar);
o$7({
  tagName: "vscode-progress-bar",
  elementClass: VscodeProgressBar,
  react: E$1,
  displayName: "VscodeProgressBar"
});
const styles$i = [
  defaultStyles,
  i$6`
    :host {
      display: block;
      height: 28px;
      margin: 0;
      outline: none;
      width: 28px;
    }

    .progress {
      height: 100%;
      width: 100%;
    }

    .background {
      fill: none;
      stroke: transparent;
      stroke-width: 2px;
    }

    .indeterminate-indicator-1 {
      fill: none;
      stroke: var(--vscode-progressBar-background, #0078d4);
      stroke-width: 2px;
      stroke-linecap: square;
      transform-origin: 50% 50%;
      transform: rotate(-90deg);
      transition: all 0.2s ease-in-out;
      animation: spin-infinite 2s linear infinite;
    }

    @keyframes spin-infinite {
      0% {
        stroke-dasharray: 0.01px 43.97px;
        transform: rotate(0deg);
      }
      50% {
        stroke-dasharray: 21.99px 21.99px;
        transform: rotate(450deg);
      }
      100% {
        stroke-dasharray: 0.01px 43.97px;
        transform: rotate(1080deg);
      }
    }
  `
];
var __decorate$j = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeProgressRing = class VscodeProgressRing2 extends VscElement {
  constructor() {
    super(...arguments);
    this.ariaLabel = "Loading";
    this.ariaLive = "assertive";
    this.role = "alert";
  }
  render() {
    return b`<svg class="progress" part="progress" viewBox="0 0 16 16">
      <circle
        class="background"
        part="background"
        cx="8px"
        cy="8px"
        r="7px"
      ></circle>
      <circle
        class="indeterminate-indicator-1"
        part="indeterminate-indicator-1"
        cx="8px"
        cy="8px"
        r="7px"
      ></circle>
    </svg>`;
  }
};
VscodeProgressRing.styles = styles$i;
__decorate$j([
  n$3({ reflect: true, attribute: "aria-label" })
], VscodeProgressRing.prototype, "ariaLabel", void 0);
__decorate$j([
  n$3({ reflect: true, attribute: "aria-live" })
], VscodeProgressRing.prototype, "ariaLive", void 0);
__decorate$j([
  n$3({ reflect: true })
], VscodeProgressRing.prototype, "role", void 0);
VscodeProgressRing = __decorate$j([
  customElement("vscode-progress-ring")
], VscodeProgressRing);
o$7({
  tagName: "vscode-progress-ring",
  elementClass: VscodeProgressRing,
  react: E$1,
  displayName: "VscodeProgressRing"
});
const styles$h = [
  defaultStyles,
  baseStyles,
  i$6`
    :host(:invalid) .icon,
    :host([invalid]) .icon {
      background-color: var(--vscode-inputValidation-errorBackground, #5a1d1d);
      border-color: var(--vscode-inputValidation-errorBorder, #be1100);
    }

    .icon {
      border-radius: 9px;
    }

    .icon.checked:before {
      background-color: currentColor;
      border-radius: 4px;
      content: '';
      height: 8px;
      left: 50%;
      margin: -4px 0 0 -4px;
      position: absolute;
      top: 50%;
      width: 8px;
    }

    :host(:focus):host(:not([disabled])) .icon {
      outline: 1px solid var(--vscode-focusBorder, #0078d4);
      outline-offset: -1px;
    }
  `
];
var __decorate$i = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeRadio$1 = class VscodeRadio extends LabelledCheckboxOrRadioMixin(FormButtonWidgetBase) {
  get form() {
    return this._internals.form;
  }
  get validity() {
    return this._internals.validity;
  }
  get validationMessage() {
    return this._internals.validationMessage;
  }
  get willValidate() {
    return this._internals.willValidate;
  }
  //#endregion
  //#region lifecycle methods
  constructor() {
    super();
    this.autofocus = false;
    this.checked = false;
    this.defaultChecked = false;
    this.invalid = false;
    this.name = "";
    this.type = "radio";
    this.value = "";
    this.disabled = false;
    this.required = false;
    this.tabIndex = 0;
    this._slottedText = "";
    this._handleClick = () => {
      if (this.disabled) {
        return;
      }
      if (!this.checked) {
        this._checkButton();
        this._handleValueChange();
        this.dispatchEvent(new Event("change", { bubbles: true }));
      }
    };
    this._handleKeyDown = (ev) => {
      if (!this.disabled && (ev.key === "Enter" || ev.key === " ")) {
        ev.preventDefault();
        if (ev.key === " " && !this.checked) {
          this.checked = true;
          this._handleValueChange();
          this.dispatchEvent(new Event("change", { bubbles: true }));
        }
        if (ev.key === "Enter") {
          this._internals.form?.requestSubmit();
        }
      }
    };
    this._internals = this.attachInternals();
    this.addEventListener("keydown", this._handleKeyDown);
    this.addEventListener("click", this._handleClick);
  }
  connectedCallback() {
    super.connectedCallback();
    this._handleValueChange();
  }
  update(changedProperties) {
    super.update(changedProperties);
    if (changedProperties.has("checked")) {
      this._handleValueChange();
    }
    if (changedProperties.has("required")) {
      this._handleValueChange();
    }
  }
  //#endregion
  //#region public methods
  checkValidity() {
    return this._internals.checkValidity();
  }
  reportValidity() {
    return this._internals.reportValidity();
  }
  /** @internal */
  formResetCallback() {
    const radios = this._getRadios();
    radios.forEach((r2) => {
      r2.checked = r2.defaultChecked;
    });
    this.updateComplete.then(() => {
      this._handleValueChange();
    });
  }
  /** @internal */
  formStateRestoreCallback(state, _mode) {
    if (this.value === state && state !== "") {
      this.checked = true;
    }
  }
  /**
   * @internal
   */
  setComponentValidity(isValid) {
    if (isValid) {
      this._internals.setValidity({});
    } else {
      this._internals.setValidity({
        valueMissing: true
      }, "Please select one of these options.", this._inputEl);
    }
  }
  //#endregion
  //#region private methods
  _getRadios() {
    const root = this.getRootNode({ composed: false });
    if (!root) {
      return [];
    }
    const radios = root.querySelectorAll(`vscode-radio[name="${this.name}"]`);
    return Array.from(radios);
  }
  _uncheckOthers(radios) {
    radios.forEach((r2) => {
      if (r2 !== this) {
        r2.checked = false;
      }
    });
  }
  _checkButton() {
    const radios = this._getRadios();
    this.checked = true;
    radios.forEach((r2) => {
      if (r2 !== this) {
        r2.checked = false;
      }
    });
  }
  _setGroupValidity(radios, isValid) {
    this.updateComplete.then(() => {
      radios.forEach((r2) => {
        r2.setComponentValidity(isValid);
      });
    });
  }
  _setActualFormValue() {
    let actualValue = "";
    if (this.checked) {
      actualValue = !this.value ? "on" : this.value;
    } else {
      actualValue = null;
    }
    this._internals.setFormValue(actualValue);
  }
  //#endregion
  //#region  event handlers
  _handleValueChange() {
    const radios = this._getRadios();
    const anyRequired = radios.some((r2) => {
      return r2.required;
    });
    this._setActualFormValue();
    if (this.checked) {
      this._uncheckOthers(radios);
      this._setGroupValidity(radios, true);
    } else {
      const anyChecked = !!radios.find((r2) => r2.checked);
      const isInvalid = anyRequired && !anyChecked;
      this._setGroupValidity(radios, !isInvalid);
    }
  }
  //#endregion
  render() {
    const iconClasses = e$2({
      icon: true,
      checked: this.checked
    });
    const labelInnerClasses = e$2({
      "label-inner": true,
      "is-slot-empty": this._slottedText === ""
    });
    return b`
      <div class="wrapper">
        <input
          ?autofocus=${this.autofocus}
          id="input"
          class="radio"
          type="checkbox"
          ?checked=${this.checked}
          value=${this.value}
          tabindex=${this.tabIndex}
        />
        <div class=${iconClasses}></div>
        <label for="input" class="label" @click=${this._handleClick}>
          <span class=${labelInnerClasses}>
            ${this._renderLabelAttribute()}
            <slot @slotchange=${this._handleSlotChange}></slot>
          </span>
        </label>
      </div>
    `;
  }
};
VscodeRadio$1.styles = styles$h;
VscodeRadio$1.formAssociated = true;
VscodeRadio$1.shadowRootOptions = {
  ...i$3.shadowRootOptions,
  delegatesFocus: true
};
__decorate$i([
  n$3({ type: Boolean, reflect: true })
], VscodeRadio$1.prototype, "autofocus", void 0);
__decorate$i([
  n$3({ type: Boolean, reflect: true })
], VscodeRadio$1.prototype, "checked", void 0);
__decorate$i([
  n$3({ type: Boolean, reflect: true, attribute: "default-checked" })
], VscodeRadio$1.prototype, "defaultChecked", void 0);
__decorate$i([
  n$3({ type: Boolean, reflect: true })
], VscodeRadio$1.prototype, "invalid", void 0);
__decorate$i([
  n$3({ reflect: true })
], VscodeRadio$1.prototype, "name", void 0);
__decorate$i([
  n$3()
], VscodeRadio$1.prototype, "type", void 0);
__decorate$i([
  n$3()
], VscodeRadio$1.prototype, "value", void 0);
__decorate$i([
  n$3({ type: Boolean, reflect: true })
], VscodeRadio$1.prototype, "disabled", void 0);
__decorate$i([
  n$3({ type: Boolean, reflect: true })
], VscodeRadio$1.prototype, "required", void 0);
__decorate$i([
  n$3({ type: Number, reflect: true })
], VscodeRadio$1.prototype, "tabIndex", void 0);
__decorate$i([
  r$1()
], VscodeRadio$1.prototype, "_slottedText", void 0);
__decorate$i([
  e$5("#input")
], VscodeRadio$1.prototype, "_inputEl", void 0);
VscodeRadio$1 = __decorate$i([
  customElement("vscode-radio")
], VscodeRadio$1);
const VscodeRadio2 = o$7({
  tagName: "vscode-radio",
  elementClass: VscodeRadio$1,
  react: E$1,
  displayName: "VscodeRadio",
  events: {
    onChange: "change",
    onInvalid: "invalid"
  }
});
const styles$g = [
  defaultStyles,
  i$6`
    :host {
      display: block;
    }

    .wrapper {
      display: flex;
      flex-wrap: wrap;
    }

    :host([variant='vertical']) .wrapper {
      display: block;
    }

    ::slotted(vscode-radio) {
      margin-right: 20px;
    }

    ::slotted(vscode-radio:last-child) {
      margin-right: 0;
    }

    :host([variant='vertical']) ::slotted(vscode-radio) {
      display: block;
      margin-bottom: 15px;
    }

    :host([variant='vertical']) ::slotted(vscode-radio:last-child) {
      margin-bottom: 0;
    }
  `
];
var __decorate$h = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeRadioGroup$1 = class VscodeRadioGroup extends VscElement {
  //#endregion
  //#region lifecycle methods
  constructor() {
    super();
    this.variant = "horizontal";
    this.role = "radiogroup";
    this._focusedRadio = -1;
    this._checkedRadio = -1;
    this._firstContentLoaded = false;
    this._handleKeyDown = (ev) => {
      const { key } = ev;
      const listenedKeys2 = ["ArrowLeft", "ArrowUp", "ArrowRight", "ArrowDown"];
      if (listenedKeys2.includes(key)) {
        ev.preventDefault();
      }
      if (key === "ArrowRight" || key === "ArrowDown") {
        this._checkNext();
      }
      if (key === "ArrowLeft" || key === "ArrowUp") {
        this._checkPrev();
      }
    };
    this.addEventListener("keydown", this._handleKeyDown);
  }
  //#endregion
  //#region private methods
  _uncheckPreviousChecked(prevChecked, prevFocused) {
    if (prevChecked !== -1) {
      this._radios[prevChecked].checked = false;
    }
    if (prevFocused !== -1) {
      this._radios[prevFocused].tabIndex = -1;
    }
  }
  _afterCheck() {
    this._focusedRadio = this._checkedRadio;
    this._radios[this._checkedRadio].checked = true;
    this._radios[this._checkedRadio].tabIndex = 0;
    this._radios[this._checkedRadio].focus();
  }
  _checkPrev() {
    const prevChecked = this._radios.findIndex((r2) => r2.checked);
    const prevFocused = this._radios.findIndex((r2) => r2.focused);
    const startPos = prevFocused !== -1 ? prevFocused : prevChecked;
    this._uncheckPreviousChecked(prevChecked, prevFocused);
    if (startPos === -1) {
      this._checkedRadio = this._radios.length - 1;
    } else if (startPos - 1 >= 0) {
      this._checkedRadio = startPos - 1;
    } else {
      this._checkedRadio = this._radios.length - 1;
    }
    this._afterCheck();
  }
  _checkNext() {
    const prevChecked = this._radios.findIndex((r2) => r2.checked);
    const prevFocused = this._radios.findIndex((r2) => r2.focused);
    const startPos = prevFocused !== -1 ? prevFocused : prevChecked;
    this._uncheckPreviousChecked(prevChecked, prevFocused);
    if (startPos === -1) {
      this._checkedRadio = 0;
    } else if (startPos + 1 < this._radios.length) {
      this._checkedRadio = startPos + 1;
    } else {
      this._checkedRadio = 0;
    }
    this._afterCheck();
  }
  _handleChange(ev) {
    const clickedIndex = this._radios.findIndex((r2) => r2 === ev.target);
    if (clickedIndex !== -1) {
      if (this._focusedRadio !== -1) {
        this._radios[this._focusedRadio].tabIndex = -1;
      }
      if (this._checkedRadio !== -1 && this._checkedRadio !== clickedIndex) {
        this._radios[this._checkedRadio].checked = false;
      }
      this._focusedRadio = clickedIndex;
      this._checkedRadio = clickedIndex;
      this._radios[clickedIndex].tabIndex = 0;
    }
  }
  _handleSlotChange() {
    if (!this._firstContentLoaded) {
      const autoFocusedRadio = this._radios.findIndex((r2) => r2.autofocus);
      if (autoFocusedRadio > -1) {
        this._focusedRadio = autoFocusedRadio;
      }
      this._firstContentLoaded = true;
    }
    let indexOfDefaultCheckedRadio = -1;
    this._radios.forEach((r2, i4) => {
      if (this._focusedRadio > -1) {
        r2.tabIndex = i4 === this._focusedRadio ? 0 : -1;
      } else {
        r2.tabIndex = i4 === 0 ? 0 : -1;
      }
      if (r2.defaultChecked) {
        if (indexOfDefaultCheckedRadio > -1) {
          this._radios[indexOfDefaultCheckedRadio].defaultChecked = false;
        }
        indexOfDefaultCheckedRadio = i4;
      }
    });
    if (indexOfDefaultCheckedRadio > -1) {
      this._radios[indexOfDefaultCheckedRadio].checked = true;
    }
  }
  //#endregion
  render() {
    return b`
      <div class="wrapper">
        <slot
          @slotchange=${this._handleSlotChange}
          @change=${this._handleChange}
        ></slot>
      </div>
    `;
  }
};
VscodeRadioGroup$1.styles = styles$g;
__decorate$h([
  n$3({ reflect: true })
], VscodeRadioGroup$1.prototype, "variant", void 0);
__decorate$h([
  n$3({ reflect: true })
], VscodeRadioGroup$1.prototype, "role", void 0);
__decorate$h([
  o$1({ selector: "vscode-radio" })
], VscodeRadioGroup$1.prototype, "_radios", void 0);
__decorate$h([
  r$1()
], VscodeRadioGroup$1.prototype, "_focusedRadio", void 0);
__decorate$h([
  r$1()
], VscodeRadioGroup$1.prototype, "_checkedRadio", void 0);
VscodeRadioGroup$1 = __decorate$h([
  customElement("vscode-radio-group")
], VscodeRadioGroup$1);
const VscodeRadioGroup2 = o$7({
  tagName: "vscode-radio-group",
  elementClass: VscodeRadioGroup$1,
  react: E$1,
  displayName: "VscodeRadioGroup",
  events: {
    onChange: "change"
  }
});
o$7({
  tagName: "vscode-scrollable",
  elementClass: VscodeScrollable,
  react: E$1,
  displayName: "VscodeScrollable"
});
var __decorate$g = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeSingleSelect$1 = class VscodeSingleSelect extends VscodeSelectBase {
  set selectedIndex(val) {
    this._opts.selectedIndex = val;
    const op = this._opts.getOptionByIndex(val);
    if (op) {
      this._opts.activeIndex = val;
      this._value = op.value;
      this._internals.setFormValue(this._value);
      this._manageRequired();
    } else {
      this._value = "";
      this._internals.setFormValue("");
      this._manageRequired();
    }
  }
  get selectedIndex() {
    return this._opts.selectedIndex;
  }
  set value(val) {
    this._opts.value = val;
    if (this._opts.selectedIndex > -1) {
      this._requestedValueToSetLater = "";
    } else {
      this._requestedValueToSetLater = val;
    }
    this._internals.setFormValue(this._value);
    this._manageRequired();
  }
  get value() {
    return this._opts.value;
  }
  get validity() {
    return this._internals.validity;
  }
  get validationMessage() {
    return this._internals.validationMessage;
  }
  get willValidate() {
    return this._internals.willValidate;
  }
  checkValidity() {
    return this._internals.checkValidity();
  }
  reportValidity() {
    return this._internals.reportValidity();
  }
  updateInputValue() {
    if (!this.combobox) {
      return;
    }
    const input = this.renderRoot.querySelector(".combobox-input");
    if (input) {
      const selectedOption = this._opts.getSelectedOption();
      input.value = selectedOption?.label ?? "";
    }
  }
  constructor() {
    super();
    this.defaultValue = "";
    this.name = void 0;
    this.required = false;
    this._requestedValueToSetLater = "";
    this._opts.multiSelect = false;
    this._internals = this.attachInternals();
  }
  connectedCallback() {
    super.connectedCallback();
    this.updateComplete.then(() => {
      this._manageRequired();
    });
  }
  /** @internal */
  formResetCallback() {
    this.value = this.defaultValue;
  }
  /** @internal */
  formStateRestoreCallback(state, _mode) {
    this.updateComplete.then(() => {
      this.value = state;
    });
  }
  /** @internal */
  get type() {
    return "select-one";
  }
  get form() {
    return this._internals.form;
  }
  async _createAndSelectSuggestedOption() {
    const nextIndex = this._createSuggestedOption();
    await this.updateComplete;
    this._opts.selectedIndex = nextIndex;
    this._dispatchChangeEvent();
    const opCreateEvent = new CustomEvent("vsc-single-select-create-option", { detail: { value: this._opts.getOptionByIndex(nextIndex)?.value ?? "" } });
    this.dispatchEvent(opCreateEvent);
    this.open = false;
    this._isPlaceholderOptionActive = false;
  }
  _setStateFromSlottedElements() {
    super._setStateFromSlottedElements();
    if (!this.combobox && this._opts.selectedIndexes.length === 0) {
      this._opts.selectedIndex = this._opts.options.length > 0 ? 0 : -1;
    }
  }
  //#region event handlers
  _onSlotChange() {
    super._onSlotChange();
    if (this._requestedValueToSetLater) {
      const foundOption = this._opts.getOptionByValue(this._requestedValueToSetLater);
      if (foundOption) {
        this._opts.selectedIndex = foundOption.index;
        this._requestedValueToSetLater = "";
      }
    }
    if (this._opts.selectedIndex > -1 && this._opts.numOptions > 0) {
      this._internals.setFormValue(this._opts.value);
      this._manageRequired();
    } else {
      this._internals.setFormValue(null);
      this._manageRequired();
    }
  }
  _onEnterKeyDown(ev) {
    super._onEnterKeyDown(ev);
    let valueChanged = false;
    if (this.combobox) {
      if (this.open) {
        if (this._isPlaceholderOptionActive) {
          this._createAndSelectSuggestedOption();
        } else {
          valueChanged = this._opts.activeIndex !== this._opts.selectedIndex;
          this._opts.selectedIndex = this._opts.activeIndex;
          this.open = false;
        }
      } else {
        this.open = true;
        this._scrollActiveElementToTop();
      }
    } else {
      if (this.open) {
        valueChanged = this._opts.activeIndex !== this._opts.selectedIndex;
        this._opts.selectedIndex = this._opts.activeIndex;
        this.open = false;
      } else {
        this.open = true;
        this._scrollActiveElementToTop();
      }
    }
    if (valueChanged) {
      this._dispatchChangeEvent();
      this.updateInputValue();
      this._internals.setFormValue(this._opts.value);
      this._manageRequired();
    }
  }
  _onOptionClick(ev) {
    super._onOptionClick(ev);
    const composedPath = ev.composedPath();
    const optEl = composedPath.find((et) => {
      const el = et;
      if ("matches" in el) {
        return el.matches("li.option");
      }
      return;
    });
    if (!optEl || optEl.matches(".disabled")) {
      return;
    }
    const isPlaceholderOption = optEl.classList.contains("placeholder");
    if (isPlaceholderOption) {
      if (this.creatable) {
        this._createAndSelectSuggestedOption();
      }
    } else {
      this._opts.selectedIndex = Number(optEl.dataset.index);
      this.open = false;
      this._internals.setFormValue(this._value);
      this._manageRequired();
      this._dispatchChangeEvent();
    }
  }
  //#endregion
  _manageRequired() {
    const { value } = this;
    if (value === "" && this.required) {
      this._internals.setValidity({ valueMissing: true }, "Please select an item in the list.", this._face);
    } else {
      this._internals.setValidity({});
    }
  }
  //#region render functions
  _renderSelectFace() {
    const selectedOption = this._opts.getSelectedOption();
    const label = selectedOption?.label ?? "";
    const activeDescendant = this._opts.activeIndex > -1 ? `op-${this._opts.activeIndex}` : "";
    return b`
      <div
        aria-activedescendant=${activeDescendant}
        aria-controls="select-listbox"
        aria-expanded=${this.open ? "true" : "false"}
        aria-haspopup="listbox"
        aria-label=${o(this.label)}
        class="select-face face"
        @click=${this._onFaceClick}
        role="combobox"
        tabindex="0"
      >
        <span class="text">${label}</span> ${chevronDownIcon}
      </div>
    `;
  }
  _renderComboboxFace() {
    let inputVal = "";
    if (this._isBeingFiltered) {
      inputVal = this._opts.filterPattern;
    } else {
      const op = this._opts.getSelectedOption();
      inputVal = op?.label ?? "";
    }
    const activeDescendant = this._opts.activeIndex > -1 ? `op-${this._opts.activeIndex}` : "";
    const expanded = this.open ? "true" : "false";
    return b`
      <div class="combobox-face face">
        <input
          aria-activedescendant=${activeDescendant}
          aria-autocomplete="list"
          aria-controls="select-listbox"
          aria-expanded=${expanded}
          aria-haspopup="listbox"
          aria-label=${o(this.label)}
          class="combobox-input"
          role="combobox"
          spellcheck="false"
          type="text"
          autocomplete="off"
          .value=${inputVal}
          @focus=${this._onComboboxInputFocus}
          @blur=${this._onComboboxInputBlur}
          @input=${this._onComboboxInputInput}
          @click=${this._onComboboxInputClick}
          @keydown=${this._onComboboxInputSpaceKeyDown}
        />
        <button
          aria-label="Open the list of options"
          class="combobox-button"
          type="button"
          @click=${this._onComboboxButtonClick}
          @keydown=${this._onComboboxButtonKeyDown}
          tabindex="-1"
        >
          ${chevronDownIcon}
        </button>
      </div>
    `;
  }
  render() {
    return b`
      <div class="single-select">
        <slot class="main-slot" @slotchange=${this._onSlotChange}></slot>
        ${this.combobox ? this._renderComboboxFace() : this._renderSelectFace()}
        ${this._renderDropdown()}
      </div>
    `;
  }
};
VscodeSingleSelect$1.styles = styles$k;
VscodeSingleSelect$1.shadowRootOptions = {
  ...i$3.shadowRootOptions,
  delegatesFocus: true
};
VscodeSingleSelect$1.formAssociated = true;
__decorate$g([
  n$3({ attribute: "default-value" })
], VscodeSingleSelect$1.prototype, "defaultValue", void 0);
__decorate$g([
  n$3({ reflect: true })
], VscodeSingleSelect$1.prototype, "name", void 0);
__decorate$g([
  n$3({ type: Number, attribute: "selected-index" })
], VscodeSingleSelect$1.prototype, "selectedIndex", null);
__decorate$g([
  n$3({ type: String })
], VscodeSingleSelect$1.prototype, "value", null);
__decorate$g([
  n$3({ type: Boolean, reflect: true })
], VscodeSingleSelect$1.prototype, "required", void 0);
__decorate$g([
  e$5(".face")
], VscodeSingleSelect$1.prototype, "_face", void 0);
VscodeSingleSelect$1 = __decorate$g([
  customElement("vscode-single-select")
], VscodeSingleSelect$1);
const VscodeSingleSelect2 = o$7({
  tagName: "vscode-single-select",
  elementClass: VscodeSingleSelect$1,
  react: E$1,
  displayName: "VscodeSingleSelect",
  events: {
    onChange: "change",
    onInvalid: "invalid",
    onVscSingleSelectCreateOption: "vsc-single-select-create-option"
  }
});
const styles$f = [
  defaultStyles,
  i$6`
    :host {
      --separator-border: var(--vscode-editorWidget-border, #454545);

      border: 1px solid var(--vscode-editorWidget-border, #454545);
      display: block;
      overflow: hidden;
      position: relative;
    }

    ::slotted(*) {
      height: 100%;
      width: 100%;
    }

    ::slotted(vscode-split-layout) {
      border: 0;
    }

    .wrapper {
      display: flex;
      height: 100%;
      width: 100%;
    }

    .wrapper.horizontal {
      flex-direction: column;
    }

    .start {
      box-sizing: border-box;
      flex: 1;
      min-height: 0;
      min-width: 0;
    }

    :host([split='vertical']) .start {
      border-right: 1px solid var(--separator-border);
    }

    :host([split='horizontal']) .start {
      border-bottom: 1px solid var(--separator-border);
    }

    .end {
      flex: 1;
      min-height: 0;
      min-width: 0;
    }

    :host([split='vertical']) .start,
    :host([split='vertical']) .end {
      height: 100%;
    }

    :host([split='horizontal']) .start,
    :host([split='horizontal']) .end {
      width: 100%;
    }

    .handle-overlay {
      display: none;
      height: 100%;
      left: 0;
      position: absolute;
      top: 0;
      width: 100%;
      z-index: 1;
    }

    .handle-overlay.active {
      display: block;
    }

    .handle-overlay.split-vertical {
      cursor: ew-resize;
    }

    .handle-overlay.split-horizontal {
      cursor: ns-resize;
    }

    .handle {
      background-color: transparent;
      position: absolute;
      z-index: 2;
    }

    .handle.hover {
      transition: background-color 0.1s ease-out 0.3s;
      background-color: var(--vscode-sash-hoverBorder, #0078d4);
    }

    .handle.hide {
      background-color: transparent;
      transition: background-color 0.1s ease-out;
    }

    .handle.split-vertical {
      cursor: ew-resize;
      height: 100%;
    }

    .handle.split-horizontal {
      cursor: ns-resize;
      width: 100%;
    }
  `
];
var __decorate$f = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
var VscodeSplitLayout_1;
const DEFAULT_INITIAL_POSITION = "50%";
const DEFAULT_HANDLE_SIZE = 4;
const parseValue = (raw) => {
  if (!raw) {
    return { value: 0, unit: "pixel" };
  }
  let unit;
  let rawVal;
  if (raw.endsWith("%")) {
    unit = "percent";
    rawVal = +raw.substring(0, raw.length - 1);
  } else if (raw.endsWith("px")) {
    unit = "pixel";
    rawVal = +raw.substring(0, raw.length - 2);
  } else {
    unit = "pixel";
    rawVal = +raw;
  }
  const value = isNaN(rawVal) ? 0 : rawVal;
  return { unit, value };
};
const pxToPercent = (current, max) => {
  return max === 0 ? 0 : Math.min(100, current / max * 100);
};
const percentToPx = (current, max) => {
  return max * (current / 100);
};
let VscodeSplitLayout$1 = VscodeSplitLayout_1 = class VscodeSplitLayout extends VscElement {
  /**
   * Direction of the divider.
   */
  set split(newVal) {
    if (this._split === newVal) {
      return;
    }
    this._split = newVal;
    this.resetHandlePosition();
  }
  get split() {
    return this._split;
  }
  /**
   * Set the handle position programmatically. The value must include a unit,
   * either `%` or `px`. If no unit is specified, the value is interpreted as
   * `px`.
   */
  set handlePosition(newVal) {
    this._rawHandlePosition = newVal;
    this._handlePositionPropChanged();
  }
  get handlePosition() {
    return this._rawHandlePosition;
  }
  /**
   * The size of the fixed pane will not change when the component is resized.
   */
  set fixedPane(newVal) {
    this._fixedPane = newVal;
    this._fixedPanePropChanged();
  }
  get fixedPane() {
    return this._fixedPane;
  }
  /**
   * Sets the minimum size of the start pane. Accepts pixel or percentage values.
   */
  set minStart(newVal) {
    const normalized = newVal ?? void 0;
    if (this._minStart === normalized) {
      return;
    }
    this._minStart = normalized;
    this._applyMinSizeConstraints();
  }
  get minStart() {
    return this._minStart;
  }
  /**
   * Sets the minimum size of the end pane. Accepts pixel or percentage values.
   */
  set minEnd(newVal) {
    const normalized = newVal ?? void 0;
    if (this._minEnd === normalized) {
      return;
    }
    this._minEnd = normalized;
    this._applyMinSizeConstraints();
  }
  get minEnd() {
    return this._minEnd;
  }
  constructor() {
    super();
    this._split = "vertical";
    this.resetOnDblClick = false;
    this.handleSize = 4;
    this.initialHandlePosition = DEFAULT_INITIAL_POSITION;
    this._fixedPane = "none";
    this._handlePosition = 0;
    this._isDragActive = false;
    this._hover = false;
    this._hide = false;
    this._boundRect = new DOMRect();
    this._handleOffset = 0;
    this._wrapperObserved = false;
    this._fixedPaneSize = 0;
    this._handleResize = (entries) => {
      const rect = entries[0].contentRect;
      const { width, height } = rect;
      this._boundRect = rect;
      const max = this.split === "vertical" ? width : height;
      if (this.fixedPane === "start") {
        this._handlePosition = this._fixedPaneSize;
      }
      if (this.fixedPane === "end") {
        this._handlePosition = max - this._fixedPaneSize;
      }
      this._handlePosition = this._clampHandlePosition(this._handlePosition, max);
      this._updateFixedPaneSize(max);
    };
    this._handleMouseUp = (ev) => {
      this._isDragActive = false;
      if (ev.target !== this) {
        this._hover = false;
        this._hide = true;
      }
      window.removeEventListener("mouseup", this._handleMouseUp);
      window.removeEventListener("mousemove", this._handleMouseMove);
      const { width, height } = this._boundRect;
      const max = this.split === "vertical" ? width : height;
      const positionInPercentage = pxToPercent(this._handlePosition, max);
      this.dispatchEvent(new CustomEvent("vsc-split-layout-change", {
        detail: {
          position: this._handlePosition,
          positionInPercentage
        },
        composed: true
      }));
    };
    this._handleMouseMove = (event) => {
      const { clientX, clientY } = event;
      const { left, top, height, width } = this._boundRect;
      const vert = this.split === "vertical";
      const maxPos = vert ? width : height;
      const mousePos = vert ? clientX - left : clientY - top;
      const rawPosition = mousePos - this._handleOffset + this.handleSize / 2;
      this._handlePosition = this._clampHandlePosition(rawPosition, maxPos);
      this._updateFixedPaneSize(maxPos);
    };
    this._resizeObserver = new ResizeObserver(this._handleResize);
  }
  /**
   * Sets the handle position to the value specified in the `initialHandlePosition` property.
   */
  resetHandlePosition() {
    if (!this._wrapperEl) {
      this._handlePosition = 0;
      return;
    }
    const { width, height } = this._wrapperEl.getBoundingClientRect();
    const max = this.split === "vertical" ? width : height;
    const { value, unit } = parseValue(this.initialHandlePosition ?? DEFAULT_INITIAL_POSITION);
    const nextValue = unit === "percent" ? percentToPx(value, max) : value;
    this._handlePosition = this._clampHandlePosition(nextValue, max);
    this._updateFixedPaneSize(max);
  }
  connectedCallback() {
    super.connectedCallback();
  }
  firstUpdated(_changedProperties) {
    if (this.fixedPane !== "none") {
      this._resizeObserver.observe(this._wrapperEl);
      this._wrapperObserved = true;
    }
    this._boundRect = this._wrapperEl.getBoundingClientRect();
    const { value, unit } = this.handlePosition ? parseValue(this.handlePosition) : parseValue(this.initialHandlePosition);
    this._setPosition(value, unit);
    this._initFixedPane();
  }
  _handlePositionPropChanged() {
    if (this.handlePosition && this._wrapperEl) {
      this._boundRect = this._wrapperEl.getBoundingClientRect();
      const { value, unit } = parseValue(this.handlePosition);
      this._setPosition(value, unit);
    }
  }
  _fixedPanePropChanged() {
    if (!this._wrapperEl) {
      return;
    }
    this._initFixedPane();
  }
  _initFixedPane() {
    if (this.fixedPane === "none") {
      if (this._wrapperObserved) {
        this._resizeObserver.unobserve(this._wrapperEl);
        this._wrapperObserved = false;
      }
    } else {
      const { width, height } = this._boundRect;
      const max = this.split === "vertical" ? width : height;
      this._fixedPaneSize = this.fixedPane === "start" ? this._handlePosition : max - this._handlePosition;
      if (!this._wrapperObserved) {
        this._resizeObserver.observe(this._wrapperEl);
        this._wrapperObserved = true;
      }
    }
  }
  _applyMinSizeConstraints() {
    if (!this._wrapperEl) {
      return;
    }
    this._boundRect = this._wrapperEl.getBoundingClientRect();
    const { width, height } = this._boundRect;
    const max = this.split === "vertical" ? width : height;
    this._handlePosition = this._clampHandlePosition(this._handlePosition, max);
    this._updateFixedPaneSize(max);
  }
  _resolveMinSizePx(value, max) {
    if (!value) {
      return 0;
    }
    const { unit, value: parsedValue } = parseValue(value);
    const resolved = unit === "percent" ? percentToPx(parsedValue, max) : parsedValue;
    if (!isFinite(resolved)) {
      return 0;
    }
    return Math.max(0, Math.min(resolved, max));
  }
  _clampHandlePosition(value, max) {
    if (!isFinite(max) || max <= 0) {
      return 0;
    }
    const minStartPx = this._resolveMinSizePx(this._minStart, max);
    const minEndPx = this._resolveMinSizePx(this._minEnd, max);
    const lowerBound = Math.min(minStartPx, max);
    const upperBound = Math.max(lowerBound, max - minEndPx);
    const boundedValue = Math.max(lowerBound, Math.min(value, upperBound));
    return Math.max(0, Math.min(boundedValue, max));
  }
  _updateFixedPaneSize(max) {
    if (this.fixedPane === "start") {
      this._fixedPaneSize = this._handlePosition;
    } else if (this.fixedPane === "end") {
      this._fixedPaneSize = max - this._handlePosition;
    }
  }
  _setPosition(value, unit) {
    const { width, height } = this._boundRect;
    const max = this.split === "vertical" ? width : height;
    const nextValue = unit === "percent" ? percentToPx(value, max) : value;
    this._handlePosition = this._clampHandlePosition(nextValue, max);
    this._updateFixedPaneSize(max);
  }
  _handleMouseOver() {
    this._hover = true;
    this._hide = false;
  }
  _handleMouseOut(event) {
    if (event.buttons !== 1) {
      this._hover = false;
      this._hide = true;
    }
  }
  _handleMouseDown(event) {
    event.stopPropagation();
    event.preventDefault();
    this._boundRect = this._wrapperEl.getBoundingClientRect();
    const { left, top } = this._boundRect;
    const { left: handleLeft, top: handleTop } = this._handleEl.getBoundingClientRect();
    const mouseXLocal = event.clientX - left;
    const mouseYLocal = event.clientY - top;
    if (this.split === "vertical") {
      this._handleOffset = mouseXLocal - (handleLeft - left);
    }
    if (this.split === "horizontal") {
      this._handleOffset = mouseYLocal - (handleTop - top);
    }
    this._isDragActive = true;
    window.addEventListener("mouseup", this._handleMouseUp);
    window.addEventListener("mousemove", this._handleMouseMove);
  }
  _handleDblClick() {
    if (!this.resetOnDblClick) {
      return;
    }
    this.resetHandlePosition();
  }
  _handleSlotChange() {
    const nestedLayouts = [
      ...this._nestedLayoutsAtStart,
      ...this._nestedLayoutsAtEnd
    ];
    nestedLayouts.forEach((e3) => {
      if (e3 instanceof VscodeSplitLayout_1) {
        e3.resetHandlePosition();
      }
    });
  }
  render() {
    const { width, height } = this._boundRect;
    const maxPos = this.split === "vertical" ? width : height;
    const handlePosCss = this.fixedPane !== "none" ? `${this._handlePosition}px` : `${pxToPercent(this._handlePosition, maxPos)}%`;
    let startPaneSize = "";
    if (this.fixedPane === "start") {
      startPaneSize = `0 0 ${this._fixedPaneSize}px`;
    } else {
      startPaneSize = `1 1 ${pxToPercent(this._handlePosition, maxPos)}%`;
    }
    let endPaneSize = "";
    if (this.fixedPane === "end") {
      endPaneSize = `0 0 ${this._fixedPaneSize}px`;
    } else {
      endPaneSize = `1 1 ${pxToPercent(maxPos - this._handlePosition, maxPos)}%`;
    }
    const handleStylesPropObj = {
      left: this.split === "vertical" ? handlePosCss : "0",
      top: this.split === "vertical" ? "0" : handlePosCss
    };
    const handleSize = this.handleSize ?? DEFAULT_HANDLE_SIZE;
    if (this.split === "vertical") {
      handleStylesPropObj.marginLeft = `${0 - handleSize / 2}px`;
      handleStylesPropObj.width = `${handleSize}px`;
    }
    if (this.split === "horizontal") {
      handleStylesPropObj.height = `${handleSize}px`;
      handleStylesPropObj.marginTop = `${0 - handleSize / 2}px`;
    }
    const handleOverlayClasses = e$2({
      "handle-overlay": true,
      active: this._isDragActive,
      "split-vertical": this.split === "vertical",
      "split-horizontal": this.split === "horizontal"
    });
    const handleClasses = e$2({
      handle: true,
      hover: this._hover,
      hide: this._hide,
      "split-vertical": this.split === "vertical",
      "split-horizontal": this.split === "horizontal"
    });
    const wrapperClasses = {
      wrapper: true,
      horizontal: this.split === "horizontal"
    };
    return b`
      <div class=${e$2(wrapperClasses)}>
        <div class="start" .style=${stylePropertyMap({ flex: startPaneSize })}>
          <slot name="start" @slotchange=${this._handleSlotChange}></slot>
        </div>
        <div class="end" .style=${stylePropertyMap({ flex: endPaneSize })}>
          <slot name="end" @slotchange=${this._handleSlotChange}></slot>
        </div>
        <div class=${handleOverlayClasses}></div>
        <div
          class=${handleClasses}
          .style=${stylePropertyMap(handleStylesPropObj)}
          @mouseover=${this._handleMouseOver}
          @mouseout=${this._handleMouseOut}
          @mousedown=${this._handleMouseDown}
          @dblclick=${this._handleDblClick}
        ></div>
      </div>
    `;
  }
};
VscodeSplitLayout$1.styles = styles$f;
__decorate$f([
  n$3({ reflect: true })
], VscodeSplitLayout$1.prototype, "split", null);
__decorate$f([
  n$3({ type: Boolean, reflect: true, attribute: "reset-on-dbl-click" })
], VscodeSplitLayout$1.prototype, "resetOnDblClick", void 0);
__decorate$f([
  n$3({ type: Number, reflect: true, attribute: "handle-size" })
], VscodeSplitLayout$1.prototype, "handleSize", void 0);
__decorate$f([
  n$3({ reflect: true, attribute: "initial-handle-position" })
], VscodeSplitLayout$1.prototype, "initialHandlePosition", void 0);
__decorate$f([
  n$3({ attribute: "handle-position" })
], VscodeSplitLayout$1.prototype, "handlePosition", null);
__decorate$f([
  n$3({ attribute: "fixed-pane" })
], VscodeSplitLayout$1.prototype, "fixedPane", null);
__decorate$f([
  n$3({ attribute: "min-start" })
], VscodeSplitLayout$1.prototype, "minStart", null);
__decorate$f([
  n$3({ attribute: "min-end" })
], VscodeSplitLayout$1.prototype, "minEnd", null);
__decorate$f([
  r$1()
], VscodeSplitLayout$1.prototype, "_handlePosition", void 0);
__decorate$f([
  r$1()
], VscodeSplitLayout$1.prototype, "_isDragActive", void 0);
__decorate$f([
  r$1()
], VscodeSplitLayout$1.prototype, "_hover", void 0);
__decorate$f([
  r$1()
], VscodeSplitLayout$1.prototype, "_hide", void 0);
__decorate$f([
  e$5(".wrapper")
], VscodeSplitLayout$1.prototype, "_wrapperEl", void 0);
__decorate$f([
  e$5(".handle")
], VscodeSplitLayout$1.prototype, "_handleEl", void 0);
__decorate$f([
  o$1({ slot: "start", selector: "vscode-split-layout" })
], VscodeSplitLayout$1.prototype, "_nestedLayoutsAtStart", void 0);
__decorate$f([
  o$1({ slot: "end", selector: "vscode-split-layout" })
], VscodeSplitLayout$1.prototype, "_nestedLayoutsAtEnd", void 0);
VscodeSplitLayout$1 = VscodeSplitLayout_1 = __decorate$f([
  customElement("vscode-split-layout")
], VscodeSplitLayout$1);
const VscodeSplitLayout2 = o$7({
  tagName: "vscode-split-layout",
  elementClass: VscodeSplitLayout$1,
  react: E$1,
  displayName: "VscodeSplitLayout",
  events: {
    onVscSplitLayoutChange: "vsc-split-layout-change"
  }
});
const styles$e = [
  defaultStyles,
  i$6`
    :host {
      cursor: pointer;
      display: block;
      user-select: none;
    }

    .wrapper {
      align-items: center;
      border-bottom: 1px solid transparent;
      color: var(--vscode-foreground, #cccccc);
      display: flex;
      min-height: 20px;
      overflow: hidden;
      padding: 7px 8px;
      position: relative;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    :host([active]) .wrapper {
      border-bottom-color: var(--vscode-panelTitle-activeForeground, #cccccc);
      color: var(--vscode-panelTitle-activeForeground, #cccccc);
    }

    :host([panel]) .wrapper {
      border-bottom: 0;
      margin-bottom: 0;
      padding: 0;
    }

    :host(:focus-visible) {
      outline: none;
    }

    .wrapper {
      align-items: center;
      color: var(--vscode-foreground, #cccccc);
      display: flex;
      min-height: 20px;
      overflow: inherit;
      text-overflow: inherit;
      position: relative;
    }

    .wrapper.panel {
      color: var(--vscode-panelTitle-inactiveForeground, #9d9d9d);
    }

    .wrapper.panel.active,
    .wrapper.panel:hover {
      color: var(--vscode-panelTitle-activeForeground, #cccccc);
    }

    :host([panel]) .wrapper {
      display: flex;
      font-size: 11px;
      height: 31px;
      padding: 2px 10px;
      text-transform: uppercase;
    }

    .main {
      overflow: inherit;
      text-overflow: inherit;
    }

    .active-indicator {
      display: none;
    }

    .active-indicator.panel.active {
      border-top: 1px solid var(--vscode-panelTitle-activeBorder, #0078d4);
      bottom: 4px;
      display: block;
      left: 8px;
      pointer-events: none;
      position: absolute;
      right: 8px;
    }

    :host(:focus-visible) .wrapper {
      outline-color: var(--vscode-focusBorder, #0078d4);
      outline-offset: 3px;
      outline-style: solid;
      outline-width: 1px;
    }

    :host(:focus-visible) .wrapper.panel {
      outline-offset: -2px;
    }

    slot[name='content-before']::slotted(vscode-badge) {
      margin-right: 8px;
    }

    slot[name='content-after']::slotted(vscode-badge) {
      margin-left: 8px;
    }
  `
];
var __decorate$e = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTabHeader = class VscodeTabHeader2 extends VscElement {
  constructor() {
    super(...arguments);
    this.active = false;
    this.ariaControls = "";
    this.panel = false;
    this.role = "tab";
    this.tabId = -1;
  }
  attributeChangedCallback(name, old, value) {
    super.attributeChangedCallback(name, old, value);
    if (name === "active") {
      const active = value !== null;
      this.ariaSelected = active ? "true" : "false";
      this.tabIndex = active ? 0 : -1;
    }
  }
  render() {
    return b`
      <div
        class=${e$2({
      wrapper: true,
      active: this.active,
      panel: this.panel
    })}
      >
        <div class="before"><slot name="content-before"></slot></div>
        <div class="main"><slot></slot></div>
        <div class="after"><slot name="content-after"></slot></div>
        <span
          class=${e$2({
      "active-indicator": true,
      active: this.active,
      panel: this.panel
    })}
        ></span>
      </div>
    `;
  }
};
VscodeTabHeader.styles = styles$e;
__decorate$e([
  n$3({ type: Boolean, reflect: true })
], VscodeTabHeader.prototype, "active", void 0);
__decorate$e([
  n$3({ reflect: true, attribute: "aria-controls" })
], VscodeTabHeader.prototype, "ariaControls", void 0);
__decorate$e([
  n$3({ type: Boolean, reflect: true })
], VscodeTabHeader.prototype, "panel", void 0);
__decorate$e([
  n$3({ reflect: true })
], VscodeTabHeader.prototype, "role", void 0);
__decorate$e([
  n$3({ type: Number, reflect: true, attribute: "tab-id" })
], VscodeTabHeader.prototype, "tabId", void 0);
VscodeTabHeader = __decorate$e([
  customElement("vscode-tab-header")
], VscodeTabHeader);
o$7({
  tagName: "vscode-tab-header",
  elementClass: VscodeTabHeader,
  react: E$1,
  displayName: "VscTabHeader"
});
const px = (value) => value;
const percent = (value) => value;
const toPercent = (px2, container) => percent(px2 / container * 100);
const toPx = (p2, container) => px(p2 / 100 * container);
const parsers = [
  {
    test: (v2) => /^-?\d+(\.\d+)?%$/.test(v2),
    parse: (v2) => Number(v2.slice(0, -1))
  },
  {
    test: (v2) => /^-?\d+(\.\d+)?px$/.test(v2),
    parse: (v2, base) => Number(v2.slice(0, -2)) / base * 100
  },
  {
    test: (v2) => /^-?\d+(\.\d+)?$/.test(v2),
    parse: (v2, base) => Number(v2) / base * 100
  }
];
const parseSizeAttributeToPercent = (raw, base) => {
  if (!Number.isFinite(base) || base === 0) {
    return null;
  }
  if (typeof raw === "number") {
    return Number.isFinite(raw) ? percent(raw / base * 100) : null;
  }
  const value = raw.trim();
  const parser = parsers.find((p2) => p2.test(value));
  return parser ? percent(parser.parse(value, base)) : null;
};
const SPLITTER_HIT_WIDTH = 5;
const SPLITTER_VISIBLE_WIDTH = 1;
const styles$d = [
  defaultStyles,
  i$6`
    :host {
      display: block;
      --vsc-row-even-background: transparent;
      --vsc-row-odd-background: transparent;
      --vsc-row-border-bottom-width: 0;
      --vsc-row-border-top-width: 0;
      --vsc-row-display: table-row;
    }

    :host([bordered]),
    :host([bordered-rows]) {
      --vsc-row-border-bottom-width: 1px;
    }

    :host([compact]) {
      --vsc-row-display: block;
    }

    :host([bordered][compact]),
    :host([bordered-rows][compact]) {
      --vsc-row-border-bottom-width: 0;
      --vsc-row-border-top-width: 1px;
    }

    :host([zebra]) {
      --vsc-row-even-background: var(
        --vscode-keybindingTable-rowsBackground,
        rgba(204, 204, 204, 0.04)
      );
    }

    :host([zebra-odd]) {
      --vsc-row-odd-background: var(
        --vscode-keybindingTable-rowsBackground,
        rgba(204, 204, 204, 0.04)
      );
    }

    ::slotted(vscode-table-row) {
      width: 100%;
    }

    .wrapper {
      height: 100%;
      max-width: 100%;
      overflow: hidden;
      position: relative;
      width: 100%;
    }

    .wrapper.select-disabled {
      user-select: none;
    }

    .wrapper.resize-cursor {
      cursor: ew-resize;
    }

    .wrapper.compact-view .header-slot-wrapper {
      height: 0;
      overflow: hidden;
    }

    .scrollable {
      height: 100%;
    }

    .scrollable:before {
      background-color: transparent;
      content: '';
      display: block;
      height: 1px;
      position: absolute;
      width: 100%;
    }

    .wrapper:not(.compact-view) .scrollable:not([scrolled]):before {
      background-color: var(
        --vscode-editorGroup-border,
        rgba(255, 255, 255, 0.09)
      );
    }

    .sash {
      visibility: hidden;
    }

    :host([bordered-columns]) .sash,
    :host([bordered]) .sash {
      visibility: visible;
    }

    :host([resizable]) .wrapper:hover .sash {
      visibility: visible;
    }

    .sash {
      height: 100%;
      position: absolute;
      top: 0;
      width: 1px;
    }

    .wrapper.compact-view .sash {
      display: none;
    }

    .sash.resizable {
      cursor: ew-resize;
    }

    .sash-visible {
      background-color: var(
        --vscode-editorGroup-border,
        rgba(255, 255, 255, 0.09)
      );
      height: calc(100% - 30px);
      position: absolute;
      top: 30px;
      width: ${SPLITTER_VISIBLE_WIDTH}px;
    }

    .sash.hover .sash-visible {
      background-color: var(--vscode-sash-hoverBorder, #0078d4);
      transition: background-color 50ms linear 300ms;
    }

    .sash .sash-clickable {
      height: 100%;
      left: ${0 - (SPLITTER_HIT_WIDTH - SPLITTER_VISIBLE_WIDTH) / 2}px;
      position: absolute;
      width: ${SPLITTER_HIT_WIDTH}px;
    }
  `
];
function calculateColumnWidths(widths, splitterIndex, delta, minWidths) {
  const result = [...widths];
  if (delta === 0 || splitterIndex < 0 || splitterIndex >= widths.length - 1) {
    return result;
  }
  const absDelta = Math.abs(delta);
  let remaining = percent(absDelta);
  const leftIndices = [];
  const rightIndices = [];
  for (let i4 = splitterIndex; i4 >= 0; i4--) {
    leftIndices.push(i4);
  }
  for (let i4 = splitterIndex + 1; i4 < widths.length; i4++) {
    rightIndices.push(i4);
  }
  const shrinkingSide = delta > 0 ? rightIndices : leftIndices;
  const growingSide = delta > 0 ? leftIndices : rightIndices;
  let totalAvailable = percent(0);
  for (const i4 of shrinkingSide) {
    const available = Math.max(0, result[i4] - (minWidths.get(i4) ?? 0));
    totalAvailable = percent(totalAvailable + available);
  }
  if (totalAvailable < remaining) {
    return result;
  }
  for (const i4 of shrinkingSide) {
    if (remaining === 0) {
      break;
    }
    const available = Math.max(0, result[i4] - (minWidths.get(i4) ?? 0));
    const take = Math.min(available, remaining);
    result[i4] = percent(result[i4] - take);
    remaining = percent(remaining - take);
  }
  let toAdd = percent(absDelta);
  for (const i4 of growingSide) {
    if (toAdd === 0) {
      break;
    }
    result[i4] = percent(result[i4] + toAdd);
    toAdd = percent(0);
  }
  return result;
}
class ColumnResizeController {
  constructor(host) {
    this._hostWidth = px(0);
    this._hostX = px(0);
    this._activeSplitter = null;
    this._columnMinWidths = /* @__PURE__ */ new Map();
    this._columnWidths = [];
    this._dragState = null;
    this._cachedSplitterPositions = null;
    (this._host = host).addController(this);
  }
  hostConnected() {
    this.saveHostDimensions();
  }
  get isDragging() {
    return this._dragState !== null;
  }
  get splitterPositions() {
    if (this._cachedSplitterPositions) {
      return this._cachedSplitterPositions;
    }
    const result = [];
    let acc = percent(0);
    for (let i4 = 0; i4 < this._columnWidths.length - 1; i4++) {
      acc = percent(acc + this._columnWidths[i4]);
      result.push(acc);
    }
    this._cachedSplitterPositions = result;
    return result;
  }
  getActiveSplitterCalculatedPosition() {
    const splitterPositions = this.splitterPositions;
    if (!this._dragState) {
      return px(0);
    }
    const activeSplitterPos = splitterPositions[this._dragState.splitterIndex];
    const activeSplitterPosPx = this._toPx(activeSplitterPos);
    return activeSplitterPosPx;
  }
  get columnWidths() {
    return this._columnWidths;
  }
  get columnMinWidths() {
    return new Map(this._columnMinWidths);
  }
  saveHostDimensions() {
    const cr = this._host.getBoundingClientRect();
    const { width, x: x2 } = cr;
    this._hostWidth = px(width);
    this._hostX = px(x2);
    return this;
  }
  setActiveSplitter(splitter) {
    this._activeSplitter = splitter;
    return this;
  }
  getActiveSplitter() {
    return this._activeSplitter;
  }
  setColumnMinWidthAt(colIndex, value) {
    this._columnMinWidths.set(colIndex, value);
    this._host.requestUpdate();
    return this;
  }
  setColumWidths(widths) {
    this._columnWidths = widths;
    this._cachedSplitterPositions = null;
    this._host.requestUpdate();
    return this;
  }
  shouldDrag(event) {
    return +event.currentTarget.dataset.index === this._dragState?.splitterIndex;
  }
  startDrag(event) {
    event.stopPropagation();
    if (this._dragState) {
      return;
    }
    this._activeSplitter?.setPointerCapture(event.pointerId);
    const mouseX = event.pageX;
    const splitter = event.currentTarget;
    const splitterX = splitter.getBoundingClientRect().x;
    const xOffset = px(mouseX - splitterX);
    this._dragState = {
      dragOffset: px(xOffset),
      pointerId: event.pointerId,
      splitterIndex: +splitter.dataset.index,
      prevX: px(mouseX - xOffset)
    };
    this._host.requestUpdate();
  }
  drag(event) {
    event.stopPropagation();
    if (!event?.currentTarget?.hasPointerCapture?.(event.pointerId)) {
      return;
    }
    if (!this._dragState) {
      return;
    }
    if (event.pointerId !== this._dragState.pointerId) {
      return;
    }
    if (!this.shouldDrag(event)) {
      return;
    }
    const mouseX = event.pageX;
    const x2 = px(mouseX - this._dragState.dragOffset);
    const deltaPx = px(x2 - this._dragState.prevX);
    const delta = this._toPercent(deltaPx);
    this._dragState.prevX = x2;
    const splitterPos = this.getActiveSplitterCalculatedPosition();
    if (deltaPx <= 0 && mouseX > splitterPos + this._hostX || deltaPx > 0 && mouseX < splitterPos + this._hostX) {
      return;
    }
    this._columnWidths = calculateColumnWidths(this._columnWidths, this._dragState.splitterIndex, delta, this._columnMinWidths);
    this._cachedSplitterPositions = null;
    this._host.requestUpdate();
  }
  stopDrag(event) {
    event.stopPropagation();
    if (!this._dragState) {
      return;
    }
    const el = event.currentTarget;
    try {
      el.releasePointerCapture(this._dragState.pointerId);
    } catch (e3) {
    }
    this._dragState = null;
    this._activeSplitter = null;
    this._host.requestUpdate();
  }
  _toPercent(px2) {
    return toPercent(px2, this._hostWidth);
  }
  _toPx(percent2) {
    return toPx(percent2, this._hostWidth);
  }
}
var __decorate$d = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTable = class VscodeTable2 extends VscElement {
  /**
   * Initial column sizes in a JSON-encoded array.
   * Accepted values are:
   * - number
   * - string-type number (ex.: "100")
   * - px value (ex.: "100px")
   * - percentage value (ex.: "50%")
   * - percentage value (ex.: "50%")
   * - "auto" keyword
   */
  set columns(val) {
    if (!Array.isArray(val)) {
      this.warn('Invalid value for "columns": expected an array.');
      this._columns = [];
      return;
    }
    this._columns = val;
    if (this.isConnected) {
      this._initDefaultColumnSizes();
    }
  }
  get columns() {
    return this._columns;
  }
  constructor() {
    super();
    this.role = "table";
    this.resizable = false;
    this.responsive = false;
    this.bordered = false;
    this.borderedColumns = false;
    this.borderedRows = false;
    this.breakpoint = 300;
    this.minColumnWidth = "50px";
    this.delayedResizing = false;
    this.compact = false;
    this.zebra = false;
    this.zebraOdd = false;
    this._sashPositions = [];
    this._isDragging = false;
    this._sashHovers = [];
    this._columns = [];
    this._activeSashElementIndex = -1;
    this._componentH = 0;
    this._componentW = 0;
    this._headerCells = [];
    this._cellsOfFirstRow = [];
    this._prevHeaderHeight = 0;
    this._prevComponentHeight = 0;
    this._columnResizeController = new ColumnResizeController(this);
    this._componentResizeObserverCallback = () => {
      this._memoizeComponentDimensions();
      this._updateResizeHandlersSize();
      if (this.responsive) {
        this._toggleCompactView();
      }
      this._resizeTableBody();
    };
    this._headerResizeObserverCallback = () => {
      this._updateResizeHandlersSize();
    };
    this._bodyResizeObserverCallback = () => {
      this._resizeTableBody();
    };
    this._handleSplitterPointerMove = (event) => {
      if (!this._columnResizeController.shouldDrag(event)) {
        return;
      }
      this._columnResizeController.drag(event);
      if (!this.delayedResizing) {
        this._resizeColumns(true);
      } else {
        this._resizeColumns(false);
      }
    };
    this._handleSplitterPointerUp = (event) => {
      this._stopDrag(event);
    };
    this._handleSplitterPointerCancel = (event) => {
      this._stopDrag(event);
    };
    this._handleMinColumnWidthChange = (event) => {
      const { columnIndex, propertyValue } = event.detail;
      const value = parseSizeAttributeToPercent(propertyValue, this._componentW);
      if (value) {
        this._columnResizeController.setColumnMinWidthAt(columnIndex, value);
      }
    };
    this.addEventListener("vsc-table-change-min-column-width", this._handleMinColumnWidthChange);
  }
  connectedCallback() {
    super.connectedCallback();
    this._memoizeComponentDimensions();
    this._initDefaultColumnSizes();
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    this._componentResizeObserver?.unobserve(this);
    this._componentResizeObserver?.disconnect();
    this._bodyResizeObserver?.disconnect();
  }
  willUpdate(changedProperties) {
    if (changedProperties.has("minColumnWidth")) {
      const value = percent(parseSizeAttributeToPercent(this.minColumnWidth, this._componentW) ?? 0);
      const prevMap = this._columnResizeController.columnMinWidths;
      const widths = this._columnResizeController.columnWidths;
      for (let i4 = 0; i4 < widths.length; i4++) {
        if (!prevMap.has(i4)) {
          this._columnResizeController.setColumnMinWidthAt(i4, value);
        }
      }
    }
  }
  _memoizeComponentDimensions() {
    const cr = this.getBoundingClientRect();
    this._componentH = cr.height;
    this._componentW = cr.width;
  }
  _queryHeaderCells() {
    const headers = this._assignedHeaderElements;
    if (!(headers && headers[0])) {
      return [];
    }
    return Array.from(headers[0].querySelectorAll("vscode-table-header-cell"));
  }
  /**
   * Get cached header cells
   */
  _getHeaderCells() {
    if (!this._headerCells.length) {
      this._headerCells = this._queryHeaderCells();
    }
    return this._headerCells;
  }
  _queryCellsOfFirstRow() {
    const assignedBodyElements = this._assignedBodyElements;
    if (!(assignedBodyElements && assignedBodyElements[0])) {
      return [];
    }
    return Array.from(assignedBodyElements[0].querySelectorAll("vscode-table-row:first-child vscode-table-cell"));
  }
  /**
   * Get cached cells of first row
   */
  _getCellsOfFirstRow() {
    if (!this._cellsOfFirstRow.length) {
      this._cellsOfFirstRow = this._queryCellsOfFirstRow();
    }
    return this._cellsOfFirstRow;
  }
  _resizeTableBody() {
    let headerHeight = 0;
    let tbodyHeight = 0;
    const tableHeight = this.getBoundingClientRect().height;
    if (this._assignedHeaderElements && this._assignedHeaderElements.length) {
      headerHeight = this._assignedHeaderElements[0].getBoundingClientRect().height;
    }
    if (this._assignedBodyElements && this._assignedBodyElements.length) {
      tbodyHeight = this._assignedBodyElements[0].getBoundingClientRect().height;
    }
    const overflownContentHeight = tbodyHeight - headerHeight - tableHeight;
    this._scrollableElement.style.height = overflownContentHeight > 0 ? `${tableHeight - headerHeight}px` : "auto";
  }
  _initResizeObserver() {
    this._componentResizeObserver = new ResizeObserver(this._componentResizeObserverCallback);
    this._componentResizeObserver.observe(this);
    this._headerResizeObserver = new ResizeObserver(this._headerResizeObserverCallback);
    this._headerResizeObserver.observe(this._headerElement);
  }
  _calculateInitialColumnWidths() {
    const numCols = this._getHeaderCells().length;
    let cols = this.columns.slice(0, numCols);
    const numAutoCols = cols.filter((c2) => c2 === "auto").length + numCols - cols.length;
    let availablePercent = 100;
    cols = cols.map((col) => {
      const percentage = parseSizeAttributeToPercent(col, this._componentW);
      if (percentage === null) {
        return "auto";
      }
      availablePercent -= percentage;
      return percentage;
    });
    if (cols.length < numCols) {
      for (let i4 = cols.length; i4 < numCols; i4++) {
        cols.push("auto");
      }
    }
    cols = cols.map((col) => {
      if (col === "auto") {
        return availablePercent / numAutoCols;
      }
      return col;
    });
    return cols;
  }
  _initHeaderCellSizes(colWidths) {
    this._getHeaderCells().forEach((cell, index) => {
      cell.style.width = `${colWidths[index]}%`;
    });
  }
  _initBodyColumnSizes(colWidths) {
    this._getCellsOfFirstRow().forEach((cell, index) => {
      cell.style.width = `${colWidths[index]}%`;
    });
  }
  _initSashes(colWidths) {
    const l2 = colWidths.length;
    let prevHandlerPos = 0;
    this._sashPositions = [];
    colWidths.forEach((collW, index) => {
      if (index < l2 - 1) {
        const pos = prevHandlerPos + collW;
        this._sashPositions.push(pos);
        prevHandlerPos = pos;
      }
    });
  }
  _initDefaultColumnSizes() {
    const colWidths = this._calculateInitialColumnWidths();
    this._columnResizeController.setColumWidths(colWidths.map((c2) => percent(c2)));
    this._initHeaderCellSizes(colWidths);
    this._initBodyColumnSizes(colWidths);
    this._initSashes(colWidths);
  }
  _updateResizeHandlersSize() {
    const headerCr = this._headerElement.getBoundingClientRect();
    if (headerCr.height === this._prevHeaderHeight && this._componentH === this._prevComponentHeight) {
      return;
    }
    this._prevHeaderHeight = headerCr.height;
    this._prevComponentHeight = this._componentH;
    const bodyHeight = this._componentH - headerCr.height;
    this._sashVisibleElements.forEach((el) => {
      el.style.height = `${bodyHeight}px`;
      el.style.top = `${headerCr.height}px`;
    });
  }
  _applyCompactViewColumnLabels() {
    const headerCells = this._getHeaderCells();
    const labels = headerCells.map((c2) => c2.innerText);
    const rows = this.querySelectorAll("vscode-table-row");
    rows.forEach((r2) => {
      const cells = r2.querySelectorAll("vscode-table-cell");
      cells.forEach((c2, i4) => {
        c2.columnLabel = labels[i4];
        c2.compact = true;
      });
    });
  }
  _clearCompactViewColumnLabels() {
    this.querySelectorAll("vscode-table-cell").forEach((c2) => {
      c2.columnLabel = "";
      c2.compact = false;
    });
  }
  _toggleCompactView() {
    const cr = this.getBoundingClientRect();
    const nextCompactView = cr.width < this.breakpoint;
    if (this.compact !== nextCompactView) {
      this.compact = nextCompactView;
      if (nextCompactView) {
        this._applyCompactViewColumnLabels();
      } else {
        this._clearCompactViewColumnLabels();
      }
    }
  }
  _stopDrag(event) {
    const activeSplitter = this._columnResizeController.getActiveSplitter();
    if (activeSplitter) {
      activeSplitter.removeEventListener("pointermove", this._handleSplitterPointerMove);
      activeSplitter.removeEventListener("pointerup", this._handleSplitterPointerUp);
      activeSplitter.removeEventListener("pointercancel", this._handleSplitterPointerCancel);
    }
    this._columnResizeController.stopDrag(event);
    this._resizeColumns(true);
    this._sashHovers[this._activeSashElementIndex] = false;
    this._isDragging = false;
    this._activeSashElementIndex = -1;
  }
  _onDefaultSlotChange() {
    this._assignedElements.forEach((el) => {
      if (el.tagName.toLowerCase() === "vscode-table-header") {
        el.slot = "header";
        return;
      }
      if (el.tagName.toLowerCase() === "vscode-table-body") {
        el.slot = "body";
        return;
      }
    });
  }
  _onHeaderSlotChange() {
    this._headerCells = this._queryHeaderCells();
    const minWidths = [];
    minWidths.fill(percent(0), 0, this._headerCells.length - 1);
    this._headerCells.forEach((c2, i4) => {
      c2.index = i4;
      if (c2.minWidth) {
        const minWidth = parseSizeAttributeToPercent(c2.minWidth, this._componentW) ?? percent(0);
        this._columnResizeController.setColumnMinWidthAt(i4, minWidth);
      }
    });
  }
  _onBodySlotChange() {
    this._initDefaultColumnSizes();
    this._initResizeObserver();
    this._updateResizeHandlersSize();
    if (!this._bodyResizeObserver) {
      const tbody = this._assignedBodyElements[0] ?? null;
      if (tbody) {
        this._bodyResizeObserver = new ResizeObserver(this._bodyResizeObserverCallback);
        this._bodyResizeObserver.observe(tbody);
      }
    }
  }
  _onSashMouseOver(event) {
    if (this._isDragging) {
      return;
    }
    const target = event.currentTarget;
    const index = Number(target.dataset.index);
    this._sashHovers[index] = true;
    this.requestUpdate();
  }
  _onSashMouseOut(event) {
    event.stopPropagation();
    if (this._isDragging) {
      return;
    }
    const target = event.currentTarget;
    const index = Number(target.dataset.index);
    this._sashHovers[index] = false;
    this.requestUpdate();
  }
  _resizeColumns(resizeBodyCells = true) {
    const widths = this._columnResizeController.columnWidths;
    const headerCells = this._getHeaderCells();
    headerCells.forEach((h2, i4) => h2.style.width = `${widths[i4]}%`);
    if (resizeBodyCells) {
      const firstRowCells = this._getCellsOfFirstRow();
      firstRowCells.forEach((c2, i4) => c2.style.width = `${widths[i4]}%`);
    }
  }
  _handleSplitterPointerDown(event) {
    event.stopPropagation();
    const activeSplitter = event.currentTarget;
    this._columnResizeController.saveHostDimensions().setActiveSplitter(activeSplitter).startDrag(event);
    activeSplitter.addEventListener("pointermove", this._handleSplitterPointerMove);
    activeSplitter.addEventListener("pointerup", this._handleSplitterPointerUp);
    activeSplitter.addEventListener("pointercancel", this._handleSplitterPointerCancel);
  }
  render() {
    const splitterPositions = this._columnResizeController.splitterPositions;
    const sashes = splitterPositions.map((val, index) => {
      const classes = e$2({
        sash: true,
        hover: this._sashHovers[index],
        resizable: this.resizable
      });
      const left = `${val}%`;
      return this.resizable ? b`
            <div
              class=${classes}
              data-index=${index}
              .style=${stylePropertyMap({ left })}
              @pointerdown=${this._handleSplitterPointerDown}
              @mouseover=${this._onSashMouseOver}
              @mouseout=${this._onSashMouseOut}
            >
              <div class="sash-visible"></div>
              <div class="sash-clickable"></div>
            </div>
          ` : b`<div
            class=${classes}
            data-index=${index}
            .style=${stylePropertyMap({ left })}
          >
            <div class="sash-visible"></div>
          </div>`;
    });
    const wrapperClasses = e$2({
      wrapper: true,
      "select-disabled": this._columnResizeController.isDragging,
      "resize-cursor": this._columnResizeController.isDragging,
      "compact-view": this.compact
    });
    return b`
      <div class=${wrapperClasses}>
        <div class="header">
          <slot name="caption"></slot>
          <div class="header-slot-wrapper">
            <slot name="header" @slotchange=${this._onHeaderSlotChange}></slot>
          </div>
        </div>
        <vscode-scrollable class="scrollable">
          <div>
            <slot name="body" @slotchange=${this._onBodySlotChange}></slot>
          </div>
        </vscode-scrollable>
        ${sashes}
        <slot @slotchange=${this._onDefaultSlotChange}></slot>
      </div>
    `;
  }
};
VscodeTable.styles = styles$d;
__decorate$d([
  n$3({ reflect: true })
], VscodeTable.prototype, "role", void 0);
__decorate$d([
  n$3({ type: Boolean, reflect: true })
], VscodeTable.prototype, "resizable", void 0);
__decorate$d([
  n$3({ type: Boolean, reflect: true })
], VscodeTable.prototype, "responsive", void 0);
__decorate$d([
  n$3({ type: Boolean, reflect: true })
], VscodeTable.prototype, "bordered", void 0);
__decorate$d([
  n$3({ type: Boolean, reflect: true, attribute: "bordered-columns" })
], VscodeTable.prototype, "borderedColumns", void 0);
__decorate$d([
  n$3({ type: Boolean, reflect: true, attribute: "bordered-rows" })
], VscodeTable.prototype, "borderedRows", void 0);
__decorate$d([
  n$3({ type: Number })
], VscodeTable.prototype, "breakpoint", void 0);
__decorate$d([
  n$3({ type: Array })
], VscodeTable.prototype, "columns", null);
__decorate$d([
  n$3({ attribute: "min-column-width" })
], VscodeTable.prototype, "minColumnWidth", void 0);
__decorate$d([
  n$3({ type: Boolean, reflect: true, attribute: "delayed-resizing" })
], VscodeTable.prototype, "delayedResizing", void 0);
__decorate$d([
  n$3({ type: Boolean, reflect: true })
], VscodeTable.prototype, "compact", void 0);
__decorate$d([
  n$3({ type: Boolean, reflect: true })
], VscodeTable.prototype, "zebra", void 0);
__decorate$d([
  n$3({ type: Boolean, reflect: true, attribute: "zebra-odd" })
], VscodeTable.prototype, "zebraOdd", void 0);
__decorate$d([
  e$5(".header")
], VscodeTable.prototype, "_headerElement", void 0);
__decorate$d([
  e$5(".scrollable")
], VscodeTable.prototype, "_scrollableElement", void 0);
__decorate$d([
  r(".sash-visible")
], VscodeTable.prototype, "_sashVisibleElements", void 0);
__decorate$d([
  o$1({
    flatten: true,
    selector: "vscode-table-header, vscode-table-body"
  })
], VscodeTable.prototype, "_assignedElements", void 0);
__decorate$d([
  o$1({
    slot: "header",
    flatten: true,
    selector: "vscode-table-header"
  })
], VscodeTable.prototype, "_assignedHeaderElements", void 0);
__decorate$d([
  o$1({
    slot: "body",
    flatten: true,
    selector: "vscode-table-body"
  })
], VscodeTable.prototype, "_assignedBodyElements", void 0);
__decorate$d([
  r$1()
], VscodeTable.prototype, "_sashPositions", void 0);
__decorate$d([
  r$1()
], VscodeTable.prototype, "_isDragging", void 0);
VscodeTable = __decorate$d([
  customElement("vscode-table")
], VscodeTable);
o$7({
  tagName: "vscode-table",
  elementClass: VscodeTable,
  react: E$1,
  displayName: "VscodeTable"
});
const styles$c = [
  defaultStyles,
  i$6`
    :host {
      display: table;
      table-layout: fixed;
      width: 100%;
    }

    ::slotted(vscode-table-row:nth-child(even)) {
      background-color: var(--vsc-row-even-background);
    }

    ::slotted(vscode-table-row:nth-child(odd)) {
      background-color: var(--vsc-row-odd-background);
    }
  `
];
var __decorate$c = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTableBody = class VscodeTableBody2 extends VscElement {
  constructor() {
    super(...arguments);
    this.role = "rowgroup";
  }
  render() {
    return b` <slot></slot> `;
  }
};
VscodeTableBody.styles = styles$c;
__decorate$c([
  n$3({ reflect: true })
], VscodeTableBody.prototype, "role", void 0);
VscodeTableBody = __decorate$c([
  customElement("vscode-table-body")
], VscodeTableBody);
o$7({
  tagName: "vscode-table-body",
  elementClass: VscodeTableBody,
  react: E$1,
  displayName: "VscodeTableBody"
});
const styles$b = [
  defaultStyles,
  i$6`
    :host {
      border-bottom-color: var(
        --vscode-editorGroup-border,
        rgba(255, 255, 255, 0.09)
      );
      border-bottom-style: solid;
      border-bottom-width: var(--vsc-row-border-bottom-width);
      box-sizing: border-box;
      color: var(--vscode-foreground, #cccccc);
      display: table-cell;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      height: 24px;
      overflow: hidden;
      padding-left: 10px;
      text-overflow: ellipsis;
      vertical-align: middle;
      white-space: nowrap;
    }

    :host([compact]) {
      display: block;
      height: auto;
      padding-bottom: 5px;
      width: 100% !important;
    }

    :host([compact]:first-child) {
      padding-top: 10px;
    }

    :host([compact]:last-child) {
      padding-bottom: 10px;
    }

    .wrapper {
      overflow: inherit;
      text-overflow: inherit;
      white-space: inherit;
      width: 100%;
    }

    .column-label {
      font-weight: bold;
    }
  `
];
var __decorate$b = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTableCell = class VscodeTableCell2 extends VscElement {
  constructor() {
    super(...arguments);
    this.role = "cell";
    this.columnLabel = "";
    this.compact = false;
  }
  render() {
    const columnLabelElement = this.columnLabel ? b`<div class="column-label" role="presentation">
          ${this.columnLabel}
        </div>` : A;
    return b`
      <div class="wrapper">
        ${columnLabelElement}
        <slot></slot>
      </div>
    `;
  }
};
VscodeTableCell.styles = styles$b;
__decorate$b([
  n$3({ reflect: true })
], VscodeTableCell.prototype, "role", void 0);
__decorate$b([
  n$3({ attribute: "column-label" })
], VscodeTableCell.prototype, "columnLabel", void 0);
__decorate$b([
  n$3({ type: Boolean, reflect: true })
], VscodeTableCell.prototype, "compact", void 0);
VscodeTableCell = __decorate$b([
  customElement("vscode-table-cell")
], VscodeTableCell);
o$7({
  tagName: "vscode-table-cell",
  elementClass: VscodeTableCell,
  react: E$1,
  displayName: "VscodeTableCell"
});
const styles$a = [
  defaultStyles,
  i$6`
    :host {
      background-color: var(
        --vscode-keybindingTable-headerBackground,
        rgba(204, 204, 204, 0.04)
      );
      display: table;
      table-layout: fixed;
      width: 100%;
    }
  `
];
var __decorate$a = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTableHeader = class VscodeTableHeader2 extends VscElement {
  constructor() {
    super(...arguments);
    this.role = "rowgroup";
  }
  render() {
    return b` <slot></slot> `;
  }
};
VscodeTableHeader.styles = styles$a;
__decorate$a([
  n$3({ reflect: true })
], VscodeTableHeader.prototype, "role", void 0);
VscodeTableHeader = __decorate$a([
  customElement("vscode-table-header")
], VscodeTableHeader);
o$7({
  tagName: "vscode-table-header",
  elementClass: VscodeTableHeader,
  react: E$1,
  displayName: "VscodeTableHeader"
});
const styles$9 = [
  defaultStyles,
  i$6`
    :host {
      box-sizing: border-box;
      color: var(--vscode-foreground, #cccccc);
      display: table-cell;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: bold;
      line-height: 20px;
      overflow: hidden;
      padding-bottom: 5px;
      padding-left: 10px;
      padding-right: 0;
      padding-top: 5px;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .wrapper {
      box-sizing: inherit;
      overflow: inherit;
      text-overflow: inherit;
      white-space: inherit;
      width: 100%;
    }
  `
];
var __decorate$9 = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTableHeaderCell = class VscodeTableHeaderCell2 extends VscElement {
  constructor() {
    super(...arguments);
    this.minWidth = "0";
    this.index = -1;
    this.role = "columnheader";
  }
  willUpdate(changedProperties) {
    if (changedProperties.has("minWidth") && this.index > -1) {
      this.dispatchEvent(new CustomEvent("vsc-table-change-min-column-width", {
        detail: { columnIndex: this.index, propertyValue: this.minWidth },
        bubbles: true
      }));
    }
  }
  render() {
    return b`
      <div class="wrapper">
        <slot></slot>
      </div>
    `;
  }
};
VscodeTableHeaderCell.styles = styles$9;
__decorate$9([
  n$3({ attribute: "min-width" })
], VscodeTableHeaderCell.prototype, "minWidth", void 0);
__decorate$9([
  n$3({ type: Number })
], VscodeTableHeaderCell.prototype, "index", void 0);
__decorate$9([
  n$3({ reflect: true })
], VscodeTableHeaderCell.prototype, "role", void 0);
VscodeTableHeaderCell = __decorate$9([
  customElement("vscode-table-header-cell")
], VscodeTableHeaderCell);
o$7({
  tagName: "vscode-table-header-cell",
  elementClass: VscodeTableHeaderCell,
  react: E$1,
  displayName: "VscodeTableHeaderCell"
});
const styles$8 = [
  defaultStyles,
  i$6`
    :host {
      border-top-color: var(
        --vscode-editorGroup-border,
        rgba(255, 255, 255, 0.09)
      );
      border-top-style: solid;
      border-top-width: var(--vsc-row-border-top-width);
      display: var(--vsc-row-display);
      width: 100%;
    }
  `
];
var __decorate$8 = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTableRow = class VscodeTableRow2 extends VscElement {
  constructor() {
    super(...arguments);
    this.role = "row";
  }
  render() {
    return b` <slot></slot> `;
  }
};
VscodeTableRow.styles = styles$8;
__decorate$8([
  n$3({ reflect: true })
], VscodeTableRow.prototype, "role", void 0);
VscodeTableRow = __decorate$8([
  customElement("vscode-table-row")
], VscodeTableRow);
o$7({
  tagName: "vscode-table-row",
  elementClass: VscodeTableRow,
  react: E$1,
  displayName: "VscodeTableRow"
});
const styles$7 = [
  defaultStyles,
  i$6`
    :host {
      display: block;
      overflow: hidden;
    }

    :host(:focus-visible) {
      outline-color: var(--vscode-focusBorder, #0078d4);
      outline-offset: 3px;
      outline-style: solid;
      outline-width: 1px;
    }

    :host([panel]) {
      background-color: var(--vscode-panel-background, #181818);
    }
  `
];
var __decorate$7 = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTabPanel = class VscodeTabPanel2 extends VscElement {
  constructor() {
    super(...arguments);
    this.hidden = false;
    this.ariaLabelledby = "";
    this.panel = false;
    this.role = "tabpanel";
    this.tabIndex = 0;
  }
  render() {
    return b` <slot></slot> `;
  }
};
VscodeTabPanel.styles = styles$7;
__decorate$7([
  n$3({ type: Boolean, reflect: true })
], VscodeTabPanel.prototype, "hidden", void 0);
__decorate$7([
  n$3({ reflect: true, attribute: "aria-labelledby" })
], VscodeTabPanel.prototype, "ariaLabelledby", void 0);
__decorate$7([
  n$3({ type: Boolean, reflect: true })
], VscodeTabPanel.prototype, "panel", void 0);
__decorate$7([
  n$3({ reflect: true })
], VscodeTabPanel.prototype, "role", void 0);
__decorate$7([
  n$3({ type: Number, reflect: true })
], VscodeTabPanel.prototype, "tabIndex", void 0);
VscodeTabPanel = __decorate$7([
  customElement("vscode-tab-panel")
], VscodeTabPanel);
o$7({
  tagName: "vscode-tab-panel",
  elementClass: VscodeTabPanel,
  react: E$1,
  displayName: "VscodeTabPanel"
});
const styles$6 = [
  defaultStyles,
  i$6`
    :host {
      display: block;
    }

    .header {
      align-items: center;
      display: flex;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      width: 100%;
    }

    .header {
      border-bottom-color: var(--vscode-settings-headerBorder, #2b2b2b);
      border-bottom-style: solid;
      border-bottom-width: 1px;
    }

    .header.panel {
      background-color: var(--vscode-panel-background, #181818);
      border-bottom-width: 0;
      box-sizing: border-box;
      padding-left: 8px;
      padding-right: 8px;
    }

    .tablist {
      display: flex;
      margin-bottom: -1px;
    }

    slot[name='addons'] {
      display: block;
      margin-left: auto;
    }
  `
];
var __decorate$6 = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTabs = class VscodeTabs2 extends VscElement {
  constructor() {
    super();
    this.panel = false;
    this.selectedIndex = 0;
    this._tabHeaders = [];
    this._tabPanels = [];
    this._componentId = "";
    this._tabFocus = 0;
    this._componentId = uniqueId();
  }
  attributeChangedCallback(name, old, value) {
    super.attributeChangedCallback(name, old, value);
    if (name === "selected-index") {
      this._setActiveTab();
    }
    if (name === "panel") {
      this._tabHeaders.forEach((h2) => h2.panel = value !== null);
      this._tabPanels.forEach((p2) => p2.panel = value !== null);
    }
  }
  _dispatchSelectEvent() {
    this.dispatchEvent(new CustomEvent("vsc-tabs-select", {
      detail: {
        selectedIndex: this.selectedIndex
      },
      composed: true
    }));
  }
  _setActiveTab() {
    this._tabFocus = this.selectedIndex;
    this._tabPanels.forEach((el, i4) => {
      el.hidden = i4 !== this.selectedIndex;
    });
    this._tabHeaders.forEach((el, i4) => {
      el.active = i4 === this.selectedIndex;
    });
  }
  _focusPrevTab() {
    if (this._tabFocus === 0) {
      this._tabFocus = this._tabHeaders.length - 1;
    } else {
      this._tabFocus -= 1;
    }
  }
  _focusNextTab() {
    if (this._tabFocus === this._tabHeaders.length - 1) {
      this._tabFocus = 0;
    } else {
      this._tabFocus += 1;
    }
  }
  _onHeaderKeyDown(ev) {
    if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
      ev.preventDefault();
      this._tabHeaders[this._tabFocus].setAttribute("tabindex", "-1");
      if (ev.key === "ArrowLeft") {
        this._focusPrevTab();
      } else if (ev.key === "ArrowRight") {
        this._focusNextTab();
      }
      this._tabHeaders[this._tabFocus].setAttribute("tabindex", "0");
      this._tabHeaders[this._tabFocus].focus();
    }
    if (ev.key === "Enter") {
      ev.preventDefault();
      this.selectedIndex = this._tabFocus;
      this._dispatchSelectEvent();
    }
  }
  _moveHeadersToHeaderSlot() {
    const headers = this._mainSlotElements.filter((el) => el instanceof VscodeTabHeader);
    if (headers.length > 0) {
      headers.forEach((h2) => h2.setAttribute("slot", "header"));
    }
  }
  _onMainSlotChange() {
    this._moveHeadersToHeaderSlot();
    this._tabPanels = this._mainSlotElements.filter((el) => el instanceof VscodeTabPanel);
    this._tabPanels.forEach((el, i4) => {
      el.ariaLabelledby = `t${this._componentId}-h${i4}`;
      el.id = `t${this._componentId}-p${i4}`;
      el.panel = this.panel;
    });
    this._setActiveTab();
  }
  _onHeaderSlotChange() {
    this._tabHeaders = this._headerSlotElements.filter((el) => el instanceof VscodeTabHeader);
    this._tabHeaders.forEach((el, i4) => {
      el.tabId = i4;
      el.id = `t${this._componentId}-h${i4}`;
      el.ariaControls = `t${this._componentId}-p${i4}`;
      el.panel = this.panel;
      el.active = i4 === this.selectedIndex;
    });
  }
  _onHeaderClick(event) {
    const path = event.composedPath();
    const headerEl = path.find((et) => et instanceof VscodeTabHeader);
    if (headerEl) {
      this.selectedIndex = headerEl.tabId;
      this._setActiveTab();
      this._dispatchSelectEvent();
    }
  }
  render() {
    return b`
      <div
        class=${e$2({ header: true, panel: this.panel })}
        @click=${this._onHeaderClick}
        @keydown=${this._onHeaderKeyDown}
      >
        <div role="tablist" class="tablist">
          <slot
            name="header"
            @slotchange=${this._onHeaderSlotChange}
            role="tablist"
          ></slot>
        </div>
        <slot name="addons"></slot>
      </div>
      <slot @slotchange=${this._onMainSlotChange}></slot>
    `;
  }
};
VscodeTabs.styles = styles$6;
__decorate$6([
  n$3({ type: Boolean, reflect: true })
], VscodeTabs.prototype, "panel", void 0);
__decorate$6([
  n$3({ type: Number, reflect: true, attribute: "selected-index" })
], VscodeTabs.prototype, "selectedIndex", void 0);
__decorate$6([
  o$1({ slot: "header" })
], VscodeTabs.prototype, "_headerSlotElements", void 0);
__decorate$6([
  o$1()
], VscodeTabs.prototype, "_mainSlotElements", void 0);
VscodeTabs = __decorate$6([
  customElement("vscode-tabs")
], VscodeTabs);
o$7({
  tagName: "vscode-tabs",
  elementClass: VscodeTabs,
  react: E$1,
  events: {
    onVscTabsSelect: "vsc-tabs-select"
  },
  displayName: "VscodeTabs"
});
const styles$5 = [
  defaultStyles,
  i$6`
    :host {
      display: inline-block;
      height: auto;
      position: relative;
      width: 320px;
    }

    :host([cols]) {
      width: auto;
    }

    :host([rows]) {
      height: auto;
    }

    .shadow {
      box-shadow: var(--vscode-scrollbar-shadow, #000000) 0 6px 6px -6px inset;
      display: none;
      inset: 0 0 auto 0;
      height: 6px;
      pointer-events: none;
      position: absolute;
      width: 100%;
    }

    .shadow.visible {
      display: block;
    }

    textarea {
      background-color: var(--vscode-settings-textInputBackground, #313131);
      border-color: var(--vscode-settings-textInputBorder, transparent);
      border-radius: 4px;
      border-style: solid;
      border-width: 1px;
      box-sizing: border-box;
      color: var(--vscode-settings-textInputForeground, #cccccc);
      display: block;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      height: 100%;
      width: 100%;
    }

    :host([cols]) textarea {
      width: auto;
    }

    :host([rows]) textarea {
      height: auto;
    }

    :host([invalid]) textarea,
    :host(:invalid) textarea {
      background-color: var(--vscode-inputValidation-errorBackground, #5a1d1d);
      border-color: var(--vscode-inputValidation-errorBorder, #be1100);
    }

    textarea.monospace {
      background-color: var(--vscode-editor-background, #1f1f1f);
      color: var(--vscode-editor-foreground, #cccccc);
      font-family: var(--vscode-editor-font-family, monospace);
      font-size: var(--vscode-editor-font-size, 14px);
      font-weight: var(--vscode-editor-font-weight, normal);
    }

    .textarea.monospace::placeholder {
      color: var(
        --vscode-editor-inlineValuesForeground,
        rgba(255, 255, 255, 0.5)
      );
    }

    textarea.cursor-pointer {
      cursor: pointer;
    }

    textarea:focus {
      border-color: var(--vscode-focusBorder, #0078d4);
      outline: none;
    }

    textarea::placeholder {
      color: var(--vscode-input-placeholderForeground, #989898);
      opacity: 1;
    }

    textarea::-webkit-scrollbar-track {
      background-color: transparent;
    }

    textarea::-webkit-scrollbar {
      width: 14px;
    }

    textarea::-webkit-scrollbar-thumb {
      background-color: transparent;
    }

    textarea:hover::-webkit-scrollbar-thumb {
      background-color: var(
        --vscode-scrollbarSlider-background,
        rgba(121, 121, 121, 0.4)
      );
    }

    textarea::-webkit-scrollbar-thumb:hover {
      background-color: var(
        --vscode-scrollbarSlider-hoverBackground,
        rgba(100, 100, 100, 0.7)
      );
    }

    textarea::-webkit-scrollbar-thumb:active {
      background-color: var(
        --vscode-scrollbarSlider-activeBackground,
        rgba(191, 191, 191, 0.4)
      );
    }

    textarea::-webkit-scrollbar-corner {
      background-color: transparent;
    }

    textarea::-webkit-resizer {
      background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAcAAAAHCAYAAADEUlfTAAAAAXNSR0IB2cksfwAAAAlwSFlzAAALEwAACxMBAJqcGAAAACJJREFUeJxjYMAOZuIQZ5j5//9/rJJESczEKYGsG6cEXgAAsEEefMxkua4AAAAASUVORK5CYII=');
      background-repeat: no-repeat;
      background-position: right bottom;
    }
  `
];
var __decorate$5 = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTextarea$1 = class VscodeTextarea extends VscElement {
  set value(val) {
    this._value = val;
    this._internals.setFormValue(val);
  }
  get value() {
    return this._value;
  }
  /**
   * Getter for the inner textarea element if it needs to be accessed for some reason.
   */
  get wrappedElement() {
    return this._textareaEl;
  }
  get form() {
    return this._internals.form;
  }
  /** @internal */
  get type() {
    return "textarea";
  }
  get validity() {
    return this._internals.validity;
  }
  get validationMessage() {
    return this._internals.validationMessage;
  }
  get willValidate() {
    return this._internals.willValidate;
  }
  /**
   * Lowercase alias to minLength
   */
  set minlength(val) {
    this.minLength = val;
  }
  get minlength() {
    return this.minLength;
  }
  /**
   * Lowercase alias to maxLength
   */
  set maxlength(val) {
    this.maxLength = val;
  }
  get maxlength() {
    return this.maxLength;
  }
  // #endregion
  constructor() {
    super();
    this.autocomplete = void 0;
    this.autofocus = false;
    this.defaultValue = "";
    this.disabled = false;
    this.invalid = false;
    this.label = "";
    this.maxLength = void 0;
    this.minLength = void 0;
    this.rows = void 0;
    this.cols = void 0;
    this.name = void 0;
    this.placeholder = void 0;
    this.readonly = false;
    this.resize = "none";
    this.required = false;
    this.spellcheck = false;
    this.monospace = false;
    this._value = "";
    this._textareaPointerCursor = false;
    this._shadow = false;
    this._internals = this.attachInternals();
  }
  connectedCallback() {
    super.connectedCallback();
    this.updateComplete.then(() => {
      this._textareaEl.checkValidity();
      this._setValidityFromInput();
      this._internals.setFormValue(this._textareaEl.value);
    });
  }
  updated(changedProperties) {
    const validationRelatedProps = ["maxLength", "minLength", "required"];
    for (const key of changedProperties.keys()) {
      if (validationRelatedProps.includes(String(key))) {
        this.updateComplete.then(() => {
          this._setValidityFromInput();
        });
        break;
      }
    }
  }
  /** @internal */
  formResetCallback() {
    this.value = this.defaultValue;
  }
  /** @internal */
  formStateRestoreCallback(state, _mode) {
    this.updateComplete.then(() => {
      this._value = state;
    });
  }
  checkValidity() {
    return this._internals.checkValidity();
  }
  reportValidity() {
    return this._internals.reportValidity();
  }
  _setValidityFromInput() {
    this._internals.setValidity(this._textareaEl.validity, this._textareaEl.validationMessage, this._textareaEl);
  }
  _dataChanged() {
    this._value = this._textareaEl.value;
    this._internals.setFormValue(this._textareaEl.value);
  }
  _handleChange() {
    this._dataChanged();
    this._setValidityFromInput();
    this.dispatchEvent(new Event("change"));
  }
  _handleInput() {
    this._dataChanged();
    this._setValidityFromInput();
  }
  _handleMouseMove(ev) {
    if (this._textareaEl.clientHeight >= this._textareaEl.scrollHeight) {
      this._textareaPointerCursor = false;
      return;
    }
    const SCROLLBAR_WIDTH = 14;
    const BORDER_WIDTH = 1;
    const br = this._textareaEl.getBoundingClientRect();
    const x2 = ev.clientX;
    this._textareaPointerCursor = x2 >= br.left + br.width - SCROLLBAR_WIDTH - BORDER_WIDTH * 2;
  }
  _handleScroll() {
    this._shadow = this._textareaEl.scrollTop > 0;
  }
  render() {
    return b`
      <div
        class=${e$2({
      shadow: true,
      visible: this._shadow
    })}
      ></div>
      <textarea
        autocomplete=${o(this.autocomplete)}
        ?autofocus=${this.autofocus}
        ?disabled=${this.disabled}
        aria-label=${this.label}
        id="textarea"
        class=${e$2({
      monospace: this.monospace,
      "cursor-pointer": this._textareaPointerCursor
    })}
        maxlength=${o(this.maxLength)}
        minlength=${o(this.minLength)}
        rows=${o(this.rows)}
        cols=${o(this.cols)}
        name=${o(this.name)}
        placeholder=${o(this.placeholder)}
        ?readonly=${this.readonly}
        .style=${stylePropertyMap({
      resize: this.resize
    })}
        ?required=${this.required}
        spellcheck=${this.spellcheck}
        @change=${this._handleChange}
        @input=${this._handleInput}
        @mousemove=${this._handleMouseMove}
        @scroll=${this._handleScroll}
        .value=${this._value}
      ></textarea>
    `;
  }
};
VscodeTextarea$1.styles = styles$5;
VscodeTextarea$1.formAssociated = true;
VscodeTextarea$1.shadowRootOptions = {
  ...i$3.shadowRootOptions,
  delegatesFocus: true
};
__decorate$5([
  n$3()
], VscodeTextarea$1.prototype, "autocomplete", void 0);
__decorate$5([
  n$3({ type: Boolean, reflect: true })
], VscodeTextarea$1.prototype, "autofocus", void 0);
__decorate$5([
  n$3({ attribute: "default-value" })
], VscodeTextarea$1.prototype, "defaultValue", void 0);
__decorate$5([
  n$3({ type: Boolean, reflect: true })
], VscodeTextarea$1.prototype, "disabled", void 0);
__decorate$5([
  n$3({ type: Boolean, reflect: true })
], VscodeTextarea$1.prototype, "invalid", void 0);
__decorate$5([
  n$3({ attribute: false })
], VscodeTextarea$1.prototype, "label", void 0);
__decorate$5([
  n$3({ type: Number })
], VscodeTextarea$1.prototype, "maxLength", void 0);
__decorate$5([
  n$3({ type: Number })
], VscodeTextarea$1.prototype, "minLength", void 0);
__decorate$5([
  n$3({ type: Number })
], VscodeTextarea$1.prototype, "rows", void 0);
__decorate$5([
  n$3({ type: Number })
], VscodeTextarea$1.prototype, "cols", void 0);
__decorate$5([
  n$3()
], VscodeTextarea$1.prototype, "name", void 0);
__decorate$5([
  n$3()
], VscodeTextarea$1.prototype, "placeholder", void 0);
__decorate$5([
  n$3({ type: Boolean, reflect: true })
], VscodeTextarea$1.prototype, "readonly", void 0);
__decorate$5([
  n$3()
], VscodeTextarea$1.prototype, "resize", void 0);
__decorate$5([
  n$3({ type: Boolean, reflect: true })
], VscodeTextarea$1.prototype, "required", void 0);
__decorate$5([
  n$3({ type: Boolean })
], VscodeTextarea$1.prototype, "spellcheck", void 0);
__decorate$5([
  n$3({ type: Boolean, reflect: true })
], VscodeTextarea$1.prototype, "monospace", void 0);
__decorate$5([
  n$3()
], VscodeTextarea$1.prototype, "value", null);
__decorate$5([
  e$5("#textarea")
], VscodeTextarea$1.prototype, "_textareaEl", void 0);
__decorate$5([
  r$1()
], VscodeTextarea$1.prototype, "_value", void 0);
__decorate$5([
  r$1()
], VscodeTextarea$1.prototype, "_textareaPointerCursor", void 0);
__decorate$5([
  r$1()
], VscodeTextarea$1.prototype, "_shadow", void 0);
VscodeTextarea$1 = __decorate$5([
  customElement("vscode-textarea")
], VscodeTextarea$1);
const VscodeTextarea2 = o$7({
  tagName: "vscode-textarea",
  elementClass: VscodeTextarea$1,
  react: E$1,
  displayName: "VscodeTextarea",
  events: {
    onChange: "change",
    onInput: "input",
    onInvalid: "invalid"
  }
});
const defaultFontStack = r$5(getDefaultFontStack());
const styles$4 = [
  defaultStyles,
  i$6`
    :host {
      display: inline-block;
      width: 320px;
    }

    .root {
      align-items: center;
      background-color: var(--vscode-settings-textInputBackground, #313131);
      border-color: var(
        --vscode-settings-textInputBorder,
        var(--vscode-settings-textInputBackground, #3c3c3c)
      );
      border-radius: 4px;
      border-style: solid;
      border-width: 1px;
      box-sizing: border-box;
      color: var(--vscode-settings-textInputForeground, #cccccc);
      display: flex;
      max-width: 100%;
      position: relative;
      width: 100%;
    }

    :host([focused]) .root {
      border-color: var(--vscode-focusBorder, #0078d4);
    }

    :host([invalid]),
    :host(:invalid) {
      border-color: var(--vscode-inputValidation-errorBorder, #be1100);
    }

    :host([invalid]) input,
    :host(:invalid) input {
      background-color: var(--vscode-inputValidation-errorBackground, #5a1d1d);
    }

    ::slotted([slot='content-before']) {
      display: block;
      margin-left: 2px;
    }

    ::slotted([slot='content-after']) {
      display: block;
      margin-right: 2px;
    }

    slot[name='content-before'],
    slot[name='content-after'] {
      align-items: center;
      display: flex;
    }

    input {
      background-color: var(--vscode-settings-textInputBackground, #313131);
      border: 0;
      box-sizing: border-box;
      color: var(--vscode-settings-textInputForeground, #cccccc);
      display: block;
      font-family: var(--vscode-font-family, ${defaultFontStack});
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, 'normal');
      line-height: 18px;
      outline: none;
      padding-bottom: 3px;
      padding-left: 4px;
      padding-right: 4px;
      padding-top: 3px;
      width: 100%;
    }

    input:read-only:not([type='file']) {
      cursor: not-allowed;
    }

    input::placeholder {
      color: var(--vscode-input-placeholderForeground, #989898);
      opacity: 1;
    }

    input[type='file'] {
      line-height: 24px;
      padding-bottom: 0;
      padding-left: 2px;
      padding-top: 0;
    }

    input[type='file']::file-selector-button {
      background-color: var(--vscode-button-background, #0078d4);
      border: 0;
      border-radius: 2px;
      color: var(--vscode-button-foreground, #ffffff);
      cursor: pointer;
      font-family: var(--vscode-font-family, ${defaultFontStack});
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, 'normal');
      line-height: 20px;
      padding: 0 14px;
    }

    input[type='file']::file-selector-button:hover {
      background-color: var(--vscode-button-hoverBackground, #026ec1);
    }
  `
];
var __decorate$4 = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeTextfield$1 = class VscodeTextfield extends VscElement {
  /**
   * Same as the `type` of the native `<input>` element but only a subset of types are supported.
   * The supported ones are: `color`,`date`,`datetime-local`,`email`,`file`,`month`,`number`,`password`,`search`,`tel`,`text`,`time`,`url`,`week`
   */
  set type(val) {
    const validTypes = [
      "color",
      "date",
      "datetime-local",
      "email",
      "file",
      "month",
      "number",
      "password",
      "search",
      "tel",
      "text",
      "time",
      "url",
      "week"
    ];
    this._type = validTypes.includes(val) ? val : "text";
  }
  get type() {
    return this._type;
  }
  set value(val) {
    if (this.type !== "file") {
      this._value = val;
      this._internals.setFormValue(val);
    }
    this.updateComplete.then(() => {
      this._setValidityFromInput();
    });
  }
  get value() {
    return this._value;
  }
  /**
   * Lowercase alias to minLength
   */
  set minlength(val) {
    this.minLength = val;
  }
  get minlength() {
    return this.minLength;
  }
  /**
   * Lowercase alias to maxLength
   */
  set maxlength(val) {
    this.maxLength = val;
  }
  get maxlength() {
    return this.maxLength;
  }
  get form() {
    return this._internals.form;
  }
  get validity() {
    return this._internals.validity;
  }
  get validationMessage() {
    return this._internals.validationMessage;
  }
  get willValidate() {
    return this._internals.willValidate;
  }
  /**
   * Check the component's validity state when built-in validation is used.
   * Built-in validation is triggered when any validation-related attribute is set. Validation-related
   * attributes are: `max, maxlength, min, minlength, pattern, required, step`.
   * See this [the MDN reference](https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/checkValidity) for more details.
   * @returns {boolean}
   */
  checkValidity() {
    this._setValidityFromInput();
    return this._internals.checkValidity();
  }
  reportValidity() {
    this._setValidityFromInput();
    return this._internals.reportValidity();
  }
  get wrappedElement() {
    return this._inputEl;
  }
  constructor() {
    super();
    this.autocomplete = void 0;
    this.autofocus = false;
    this.defaultValue = "";
    this.disabled = false;
    this.focused = false;
    this.invalid = false;
    this.label = "";
    this.max = void 0;
    this.maxLength = void 0;
    this.min = void 0;
    this.minLength = void 0;
    this.multiple = false;
    this.name = void 0;
    this.pattern = void 0;
    this.placeholder = void 0;
    this.readonly = false;
    this.required = false;
    this.step = void 0;
    this._value = "";
    this._type = "text";
    this._internals = this.attachInternals();
  }
  connectedCallback() {
    super.connectedCallback();
    this.updateComplete.then(() => {
      this._inputEl.checkValidity();
      this._setValidityFromInput();
      this._internals.setFormValue(this._inputEl.value);
    });
  }
  attributeChangedCallback(name, old, value) {
    super.attributeChangedCallback(name, old, value);
    const validationRelatedAttributes = [
      "max",
      "maxlength",
      "min",
      "minlength",
      "pattern",
      "required",
      "step"
    ];
    if (validationRelatedAttributes.includes(name)) {
      this.updateComplete.then(() => {
        this._setValidityFromInput();
      });
    }
  }
  /** @internal */
  formResetCallback() {
    this.value = this.defaultValue;
    this.requestUpdate();
  }
  /** @internal */
  formStateRestoreCallback(state, _mode) {
    this.value = state;
  }
  _dataChanged() {
    this._value = this._inputEl.value;
    if (this.type === "file" && this._inputEl.files) {
      for (const f2 of this._inputEl.files) {
        this._internals.setFormValue(f2);
      }
    } else {
      this._internals.setFormValue(this._inputEl.value);
    }
  }
  _setValidityFromInput() {
    if (this._inputEl) {
      this._internals.setValidity(this._inputEl.validity, this._inputEl.validationMessage, this._inputEl);
    }
  }
  _onInput() {
    this._dataChanged();
    this._setValidityFromInput();
  }
  _onChange() {
    this._dataChanged();
    this._setValidityFromInput();
    this.dispatchEvent(new Event("change"));
  }
  _onFocus() {
    this.focused = true;
  }
  _onBlur() {
    this.focused = false;
  }
  _onKeyDown(ev) {
    if (ev.key === "Enter" && this._internals.form) {
      this._internals.form?.requestSubmit();
    }
  }
  render() {
    return b`
      <div class="root">
        <slot name="content-before"></slot>
        <input
          id="input"
          type=${this.type}
          ?autofocus=${this.autofocus}
          autocomplete=${o(this.autocomplete)}
          aria-label=${this.label}
          ?disabled=${this.disabled}
          max=${o(this.max)}
          maxlength=${o(this.maxLength)}
          min=${o(this.min)}
          minlength=${o(this.minLength)}
          ?multiple=${this.multiple}
          name=${o(this.name)}
          pattern=${o(this.pattern)}
          placeholder=${o(this.placeholder)}
          ?readonly=${this.readonly}
          ?required=${this.required}
          step=${o(this.step)}
          .value=${this._value}
          @blur=${this._onBlur}
          @change=${this._onChange}
          @focus=${this._onFocus}
          @input=${this._onInput}
          @keydown=${this._onKeyDown}
        />
        <slot name="content-after"></slot>
      </div>
    `;
  }
};
VscodeTextfield$1.styles = styles$4;
VscodeTextfield$1.formAssociated = true;
VscodeTextfield$1.shadowRootOptions = {
  ...i$3.shadowRootOptions,
  delegatesFocus: true
};
__decorate$4([
  n$3()
], VscodeTextfield$1.prototype, "autocomplete", void 0);
__decorate$4([
  n$3({ type: Boolean, reflect: true })
], VscodeTextfield$1.prototype, "autofocus", void 0);
__decorate$4([
  n$3({ attribute: "default-value" })
], VscodeTextfield$1.prototype, "defaultValue", void 0);
__decorate$4([
  n$3({ type: Boolean, reflect: true })
], VscodeTextfield$1.prototype, "disabled", void 0);
__decorate$4([
  n$3({ type: Boolean, reflect: true })
], VscodeTextfield$1.prototype, "focused", void 0);
__decorate$4([
  n$3({ type: Boolean, reflect: true })
], VscodeTextfield$1.prototype, "invalid", void 0);
__decorate$4([
  n$3({ attribute: false })
], VscodeTextfield$1.prototype, "label", void 0);
__decorate$4([
  n$3({ type: Number })
], VscodeTextfield$1.prototype, "max", void 0);
__decorate$4([
  n$3({ type: Number })
], VscodeTextfield$1.prototype, "maxLength", void 0);
__decorate$4([
  n$3({ type: Number })
], VscodeTextfield$1.prototype, "min", void 0);
__decorate$4([
  n$3({ type: Number })
], VscodeTextfield$1.prototype, "minLength", void 0);
__decorate$4([
  n$3({ type: Boolean, reflect: true })
], VscodeTextfield$1.prototype, "multiple", void 0);
__decorate$4([
  n$3({ reflect: true })
], VscodeTextfield$1.prototype, "name", void 0);
__decorate$4([
  n$3()
], VscodeTextfield$1.prototype, "pattern", void 0);
__decorate$4([
  n$3()
], VscodeTextfield$1.prototype, "placeholder", void 0);
__decorate$4([
  n$3({ type: Boolean, reflect: true })
], VscodeTextfield$1.prototype, "readonly", void 0);
__decorate$4([
  n$3({ type: Boolean, reflect: true })
], VscodeTextfield$1.prototype, "required", void 0);
__decorate$4([
  n$3({ type: Number })
], VscodeTextfield$1.prototype, "step", void 0);
__decorate$4([
  n$3({ reflect: true })
], VscodeTextfield$1.prototype, "type", null);
__decorate$4([
  n$3()
], VscodeTextfield$1.prototype, "value", null);
__decorate$4([
  e$5("#input")
], VscodeTextfield$1.prototype, "_inputEl", void 0);
__decorate$4([
  r$1()
], VscodeTextfield$1.prototype, "_value", void 0);
__decorate$4([
  r$1()
], VscodeTextfield$1.prototype, "_type", void 0);
VscodeTextfield$1 = __decorate$4([
  customElement("vscode-textfield")
], VscodeTextfield$1);
const VscodeTextfield2 = o$7({
  tagName: "vscode-textfield",
  elementClass: VscodeTextfield$1,
  react: E$1,
  displayName: "VscodeTextfield",
  events: {
    onChange: "change",
    onInput: "input",
    onInvalid: "invalid"
  }
});
const styles$3 = [
  defaultStyles,
  i$6`
    :host {
      display: inline-flex;
    }

    button {
      align-items: center;
      background-color: transparent;
      border: 0;
      border-radius: 5px;
      color: var(--vscode-foreground, #cccccc);
      cursor: pointer;
      display: flex;
      outline-offset: -1px;
      outline-width: 1px;
      padding: 0;
      user-select: none;
    }

    button:focus-visible {
      outline-color: var(--vscode-focusBorder, #0078d4);
      outline-style: solid;
    }

    button:hover {
      background-color: var(
        --vscode-toolbar-hoverBackground,
        rgba(90, 93, 94, 0.31)
      );
      outline-style: dashed;
      outline-color: var(--vscode-toolbar-hoverOutline, transparent);
    }

    button:active {
      background-color: var(
        --vscode-toolbar-activeBackground,
        rgba(99, 102, 103, 0.31)
      );
    }

    button.checked {
      background-color: var(
        --vscode-inputOption-activeBackground,
        rgba(36, 137, 219, 0.51)
      );
      outline-color: var(--vscode-inputOption-activeBorder, #2488db);
      outline-style: solid;
      color: var(--vscode-inputOption-activeForeground, #ffffff);
    }

    button.checked vscode-icon {
      color: var(--vscode-inputOption-activeForeground, #ffffff);
    }

    vscode-icon {
      display: block;
      padding: 3px;
    }

    slot:not(.empty) {
      align-items: center;
      display: flex;
      height: 22px;
      padding: 0 5px 0 2px;
    }

    slot.textOnly:not(.empty) {
      padding: 0 5px;
    }
  `
];
var __decorate$3 = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeToolbarButton = class VscodeToolbarButton2 extends VscElement {
  constructor() {
    super(...arguments);
    this.icon = "";
    this.label = void 0;
    this.toggleable = false;
    this.checked = false;
    this._isSlotEmpty = true;
  }
  _handleSlotChange() {
    this._isSlotEmpty = !((this._assignedNodes?.length ?? 0) > 0);
  }
  _handleButtonClick() {
    if (!this.toggleable) {
      return;
    }
    this.checked = !this.checked;
    this.dispatchEvent(new Event("change"));
  }
  render() {
    const checked = this.checked ? "true" : "false";
    return b`
      <button
        type="button"
        aria-label=${o(this.label)}
        role=${o(this.toggleable ? "switch" : void 0)}
        aria-checked=${o(this.toggleable ? checked : void 0)}
        class=${e$2({ checked: this.toggleable && this.checked })}
        @click=${this._handleButtonClick}
      >
        ${this.icon ? b`<vscode-icon name=${this.icon}></vscode-icon>` : A}
        <slot
          @slotchange=${this._handleSlotChange}
          class=${e$2({ empty: this._isSlotEmpty, textOnly: !this.icon })}
        ></slot>
      </button>
    `;
  }
};
VscodeToolbarButton.styles = styles$3;
__decorate$3([
  n$3({ reflect: true })
], VscodeToolbarButton.prototype, "icon", void 0);
__decorate$3([
  n$3()
], VscodeToolbarButton.prototype, "label", void 0);
__decorate$3([
  n$3({ type: Boolean, reflect: true })
], VscodeToolbarButton.prototype, "toggleable", void 0);
__decorate$3([
  n$3({ type: Boolean, reflect: true })
], VscodeToolbarButton.prototype, "checked", void 0);
__decorate$3([
  r$1()
], VscodeToolbarButton.prototype, "_isSlotEmpty", void 0);
__decorate$3([
  n$2()
], VscodeToolbarButton.prototype, "_assignedNodes", void 0);
VscodeToolbarButton = __decorate$3([
  customElement("vscode-toolbar-button")
], VscodeToolbarButton);
o$7({
  tagName: "vscode-toolbar-button",
  elementClass: VscodeToolbarButton,
  react: E$1,
  displayName: "VscodeToolbarButton",
  events: {
    onChange: "change"
  }
});
const styles$2 = [
  defaultStyles,
  i$6`
    :host {
      display: block;
    }

    div {
      gap: 4px;
      display: flex;
      align-items: center;
    }
  `
];
var __decorate$2 = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
let VscodeToolbarContainer = class VscodeToolbarContainer2 extends VscElement {
  render() {
    return b`<div><slot></slot></div>`;
  }
};
VscodeToolbarContainer.styles = styles$2;
VscodeToolbarContainer = __decorate$2([
  customElement("vscode-toolbar-container")
], VscodeToolbarContainer);
o$7({
  tagName: "vscode-toolbar-container",
  elementClass: VscodeToolbarContainer,
  react: E$1,
  displayName: "VscodeToolbarContainer"
});
let s$2 = class s extends Event {
  constructor(s4, t2, e3, o2) {
    super("context-request", { bubbles: true, composed: true }), this.context = s4, this.contextTarget = t2, this.callback = e3, this.subscribe = o2 ?? false;
  }
};
function n2(n3) {
  return n3;
}
let s$1 = class s2 {
  constructor(t2, s4, i4, h2) {
    if (this.subscribe = false, this.provided = false, this.value = void 0, this.t = (t3, s5) => {
      this.unsubscribe && (this.unsubscribe !== s5 && (this.provided = false, this.unsubscribe()), this.subscribe || this.unsubscribe()), this.value = t3, this.host.requestUpdate(), this.provided && !this.subscribe || (this.provided = true, this.callback && this.callback(t3, s5)), this.unsubscribe = s5;
    }, this.host = t2, void 0 !== s4.context) {
      const t3 = s4;
      this.context = t3.context, this.callback = t3.callback, this.subscribe = t3.subscribe ?? false;
    } else this.context = s4, this.callback = i4, this.subscribe = h2 ?? false;
    this.host.addController(this);
  }
  hostConnected() {
    this.dispatchRequest();
  }
  hostDisconnected() {
    this.unsubscribe && (this.unsubscribe(), this.unsubscribe = void 0);
  }
  dispatchRequest() {
    this.host.dispatchEvent(new s$2(this.context, this.host, this.t, this.subscribe));
  }
};
class s3 {
  get value() {
    return this.o;
  }
  set value(s4) {
    this.setValue(s4);
  }
  setValue(s4, t2 = false) {
    const i4 = t2 || !Object.is(s4, this.o);
    this.o = s4, i4 && this.updateObservers();
  }
  constructor(s4) {
    this.subscriptions = /* @__PURE__ */ new Map(), this.updateObservers = () => {
      for (const [s5, { disposer: t2 }] of this.subscriptions) s5(this.o, t2);
    }, void 0 !== s4 && (this.value = s4);
  }
  addCallback(s4, t2, i4) {
    if (!i4) return void s4(this.value);
    this.subscriptions.has(s4) || this.subscriptions.set(s4, { disposer: () => {
      this.subscriptions.delete(s4);
    }, consumerHost: t2 });
    const { disposer: h2 } = this.subscriptions.get(s4);
    s4(this.value, h2);
  }
  clearCallbacks() {
    this.subscriptions.clear();
  }
}
let e$1 = class e extends Event {
  constructor(t2, s4) {
    super("context-provider", { bubbles: true, composed: true }), this.context = t2, this.contextTarget = s4;
  }
};
class i3 extends s3 {
  constructor(s4, e3, i4) {
    super(void 0 !== e3.context ? e3.initialValue : i4), this.onContextRequest = (t2) => {
      if (t2.context !== this.context) return;
      const s5 = t2.contextTarget ?? t2.composedPath()[0];
      s5 !== this.host && (t2.stopPropagation(), this.addCallback(t2.callback, s5, t2.subscribe));
    }, this.onProviderRequest = (s5) => {
      if (s5.context !== this.context) return;
      if ((s5.contextTarget ?? s5.composedPath()[0]) === this.host) return;
      const e4 = /* @__PURE__ */ new Set();
      for (const [s6, { consumerHost: i5 }] of this.subscriptions) e4.has(s6) || (e4.add(s6), i5.dispatchEvent(new s$2(this.context, i5, s6, true)));
      s5.stopPropagation();
    }, this.host = s4, void 0 !== e3.context ? this.context = e3.context : this.context = e3, this.attachListeners(), this.host.addController?.(this);
  }
  attachListeners() {
    this.host.addEventListener("context-request", this.onContextRequest), this.host.addEventListener("context-provider", this.onProviderRequest);
  }
  hostConnected() {
    this.host.dispatchEvent(new e$1(this.context, this.host));
  }
}
function e2({ context: e3 }) {
  return (n3, i$12) => {
    const r2 = /* @__PURE__ */ new WeakMap();
    if ("object" == typeof i$12) return { get() {
      return n3.get.call(this);
    }, set(t2) {
      return r2.get(this).setValue(t2), n3.set.call(this, t2);
    }, init(n4) {
      return r2.set(this, new i3(this, { context: e3, initialValue: n4 })), n4;
    } };
    {
      n3.constructor.addInitializer(((n4) => {
        r2.set(n4, new i3(n4, { context: e3 }));
      }));
      const o2 = Object.getOwnPropertyDescriptor(n3, i$12);
      let s4;
      if (void 0 === o2) {
        const t2 = /* @__PURE__ */ new WeakMap();
        s4 = { get() {
          return t2.get(this);
        }, set(e4) {
          r2.get(this).setValue(e4), t2.set(this, e4);
        }, configurable: true, enumerable: true };
      } else {
        const t2 = o2.set;
        s4 = { ...o2, set(e4) {
          r2.get(this).setValue(e4), t2?.call(this, e4);
        } };
      }
      return void Object.defineProperty(n3, i$12, s4);
    }
  };
}
function c({ context: c2, subscribe: e3 }) {
  return (o2, n3) => {
    "object" == typeof n3 ? n3.addInitializer((function() {
      new s$1(this, { context: c2, callback: (t2) => {
        o2.set.call(this, t2);
      }, subscribe: e3 });
    })) : o2.constructor.addInitializer(((o3) => {
      new s$1(o3, { context: c2, callback: (t2) => {
        o3[n3] = t2;
      }, subscribe: e3 });
    }));
  };
}
const styles$1 = [
  defaultStyles,
  i$6`
    :host {
      --vsc-tree-item-arrow-display: flex;
      --internal-selectionBackground: var(
        --vscode-list-inactiveSelectionBackground,
        #37373d
      );
      --internal-selectionForeground: var(--vscode-foreground, #cccccc);
      --internal-selectionIconForeground: var(
        --vscode-icon-foreground,
        #cccccc
      );
      --internal-defaultIndentGuideDisplay: none;
      --internal-highlightedIndentGuideDisplay: block;

      display: block;
    }

    :host(:hover) {
      --internal-defaultIndentGuideDisplay: block;
      --internal-highlightedIndentGuideDisplay: block;
    }

    :host(:focus-within) {
      --internal-selectionBackground: var(
        --vscode-list-activeSelectionBackground,
        #04395e
      );
      --internal-selectionForeground: var(
        --vscode-list-activeSelectionForeground,
        #ffffff
      );
      --internal-selectionIconForeground: var(
        --vscode-list-activeSelectionIconForeground,
        #ffffff
      );
    }

    :host([hide-arrows]) {
      --vsc-tree-item-arrow-display: none;
    }

    :host([indent-guides='none']),
    :host([indent-guides='none']:hover) {
      --internal-defaultIndentGuideDisplay: none;
      --internal-highlightedIndentGuideDisplay: none;
    }

    :host([indent-guides='always']),
    :host([indent-guides='always']:hover) {
      --internal-defaultIndentGuideDisplay: block;
      --internal-highlightedIndentGuideDisplay: block;
    }
  `
];
const treeContext = n2("vscode-list");
const configContext = n2(/* @__PURE__ */ Symbol("configContext"));
const isTreeItem = (item) => item instanceof Element && item.matches("vscode-tree-item");
const isTreeRoot = (item) => item instanceof Element && item.matches("vscode-tree");
const initPathTrackerProps = (parentElement, items) => {
  const numChildren = items.length;
  const parentElementLevel = isTreeRoot(parentElement) ? -1 : parentElement.level;
  if ("branch" in parentElement) {
    parentElement.branch = numChildren > 0;
  }
  items.forEach((item, i4) => {
    if ("path" in parentElement) {
      item.path = [...parentElement.path, i4];
    } else {
      item.path = [i4];
    }
    item.level = parentElementLevel + 1;
    item.dataset.path = item.path.join(".");
  });
};
const findLastChildItem = (item) => {
  const lastItem = item.lastElementChild;
  if (!lastItem || !isTreeItem(lastItem)) {
    return item;
  }
  if (lastItem.branch && lastItem.open) {
    return findLastChildItem(lastItem);
  } else {
    return lastItem;
  }
};
const findClosestAncestorHasNextSibling = (item) => {
  if (!item.parentElement) {
    return null;
  }
  if (!isTreeItem(item.parentElement)) {
    return null;
  }
  const nextSiblingOfParent = findNextTreeItemElementSibling(item.parentElement);
  if (nextSiblingOfParent) {
    return nextSiblingOfParent;
  } else {
    return findClosestAncestorHasNextSibling(item.parentElement);
  }
};
const findNextTreeItemElementSibling = (item) => {
  let nextSibling = item.nextElementSibling;
  while (nextSibling && !isTreeItem(nextSibling)) {
    nextSibling = nextSibling.nextElementSibling;
  }
  return nextSibling;
};
const findNextItem = (item) => {
  const { parentElement } = item;
  if (!parentElement || !isTreeItem(item)) {
    return null;
  }
  let nextItem;
  if (item.branch && item.open) {
    const firstChildItem = item.querySelector("vscode-tree-item");
    if (!firstChildItem) {
      nextItem = findNextTreeItemElementSibling(item);
      if (!nextItem) {
        nextItem = findClosestAncestorHasNextSibling(item);
      }
    } else {
      nextItem = firstChildItem;
    }
  } else {
    nextItem = findNextTreeItemElementSibling(item);
    if (!nextItem) {
      nextItem = findClosestAncestorHasNextSibling(item);
    }
  }
  if (!nextItem) {
    return item;
  } else {
    return nextItem;
  }
};
const findPrevItem = (item) => {
  const { parentElement } = item;
  if (!parentElement || !isTreeItem(item)) {
    return null;
  }
  let prevSibling = item.previousElementSibling;
  while (prevSibling && !isTreeItem(prevSibling)) {
    prevSibling = prevSibling.previousElementSibling;
  }
  if (!prevSibling) {
    if (isTreeItem(parentElement)) {
      return parentElement;
    }
  }
  if (prevSibling && prevSibling.branch && prevSibling.open) {
    const lastChild = findLastChildItem(prevSibling);
    return lastChild;
  }
  return prevSibling;
};
function findParentItem(childItem) {
  if (!childItem.parentElement) {
    return null;
  }
  if (!isTreeItem(childItem.parentElement)) {
    return null;
  }
  return childItem.parentElement;
}
var __decorate$1 = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
const ExpandMode = {
  singleClick: "singleClick",
  doubleClick: "doubleClick"
};
const IndentGuides = {
  none: "none"
};
const listenedKeys = [
  " ",
  "ArrowDown",
  "ArrowUp",
  "ArrowLeft",
  "ArrowRight",
  "Enter",
  "Escape",
  "Shift"
];
let VscodeTree = class VscodeTree2 extends VscElement {
  //#endregion
  //#region lifecycle methods
  constructor() {
    super();
    this.expandMode = "singleClick";
    this.hideArrows = false;
    this.indent = 8;
    this.indentGuides = "onHover";
    this.multiSelect = false;
    this._treeContextState = {
      isShiftPressed: false,
      activeItem: null,
      selectedItems: /* @__PURE__ */ new Set(),
      hoveredItem: null,
      allItems: null,
      itemListUpToDate: false,
      focusedItem: null,
      prevFocusedItem: null,
      hasBranchItem: false,
      rootElement: this,
      highlightedItems: /* @__PURE__ */ new Set(),
      highlightIndentGuides: () => {
        this._highlightIndentGuides();
      },
      emitSelectEvent: () => {
        this._emitSelectEvent();
      }
    };
    this._configContext = {
      hideArrows: this.hideArrows,
      expandMode: this.expandMode,
      indent: this.indent,
      indentGuides: this.indentGuides,
      multiSelect: this.multiSelect
    };
    this._handleComponentKeyDown = (ev) => {
      const key = ev.key;
      if (listenedKeys.includes(key)) {
        ev.stopPropagation();
        ev.preventDefault();
      }
      switch (key) {
        case " ":
        case "Enter":
          this._handleEnterPress();
          break;
        case "ArrowDown":
          this._handleArrowDownPress();
          break;
        case "ArrowLeft":
          this._handleArrowLeftPress(ev);
          break;
        case "ArrowRight":
          this._handleArrowRightPress();
          break;
        case "ArrowUp":
          this._handleArrowUpPress();
          break;
        case "Shift":
          this._handleShiftPress();
          break;
      }
    };
    this._handleComponentKeyUp = (ev) => {
      if (ev.key === "Shift") {
        this._treeContextState.isShiftPressed = false;
      }
    };
    this._handleSlotChange = () => {
      this._treeContextState.itemListUpToDate = false;
      initPathTrackerProps(this, this._assignedTreeItems);
      this.updateComplete.then(() => {
        if (this._treeContextState.activeItem === null) {
          const firstChild = this.querySelector(":scope > vscode-tree-item");
          if (firstChild) {
            firstChild.active = true;
          }
        }
      });
    };
    this.addEventListener("keyup", this._handleComponentKeyUp);
    this.addEventListener("keydown", this._handleComponentKeyDown);
  }
  connectedCallback() {
    super.connectedCallback();
    this.role = "tree";
  }
  willUpdate(changedProperties) {
    this._updateConfigContext(changedProperties);
    if (changedProperties.has("multiSelect")) {
      this.ariaMultiSelectable = this.multiSelect ? "true" : "false";
    }
  }
  //#endregion
  //#region public methods
  /**
   * Expands all folders.
   */
  expandAll() {
    const children = this.querySelectorAll("vscode-tree-item");
    children.forEach((item) => {
      if (item.branch) {
        item.open = true;
      }
    });
  }
  /**
   * Collapses all folders.
   */
  collapseAll() {
    const children = this.querySelectorAll("vscode-tree-item");
    children.forEach((item) => {
      if (item.branch) {
        item.open = false;
      }
    });
  }
  /**
   * @internal
   * Updates `hasBranchItem` property in the context state in order to removing
   * extra padding before the leaf elements, if it is required.
   */
  updateHasBranchItemFlag() {
    const hasBranchItem = this._assignedTreeItems.some((li) => li.branch);
    this._treeContextState = { ...this._treeContextState, hasBranchItem };
  }
  //#endregion
  //#region private methods
  _emitSelectEvent() {
    const ev = new CustomEvent("vsc-tree-select", {
      detail: Array.from(this._treeContextState.selectedItems)
    });
    this.dispatchEvent(ev);
  }
  _highlightIndentGuideOfItem(item) {
    if (item.branch && item.open) {
      item.highlightedGuides = true;
      this._treeContextState.highlightedItems?.add(item);
    } else {
      const parent = findParentItem(item);
      if (parent) {
        parent.highlightedGuides = true;
        this._treeContextState.highlightedItems?.add(parent);
      }
    }
  }
  _highlightIndentGuides() {
    if (this.indentGuides === IndentGuides.none) {
      return;
    }
    this._treeContextState.highlightedItems?.forEach((i4) => i4.highlightedGuides = false);
    this._treeContextState.highlightedItems?.clear();
    if (this._treeContextState.activeItem) {
      this._highlightIndentGuideOfItem(this._treeContextState.activeItem);
    }
    this._treeContextState.selectedItems.forEach((item) => {
      this._highlightIndentGuideOfItem(item);
    });
  }
  _updateConfigContext(changedProperties) {
    const { hideArrows, expandMode, indent, indentGuides, multiSelect } = this;
    if (changedProperties.has("hideArrows")) {
      this._configContext = { ...this._configContext, hideArrows };
    }
    if (changedProperties.has("expandMode")) {
      this._configContext = { ...this._configContext, expandMode };
    }
    if (changedProperties.has("indent")) {
      this._configContext = { ...this._configContext, indent };
    }
    if (changedProperties.has("indentGuides")) {
      this._configContext = { ...this._configContext, indentGuides };
    }
    if (changedProperties.has("multiSelect")) {
      this._configContext = { ...this._configContext, multiSelect };
    }
  }
  _focusItem(item) {
    item.active = true;
    item.updateComplete.then(() => {
      item.focus();
      this._highlightIndentGuides();
    });
  }
  _focusPrevItem() {
    if (this._treeContextState.focusedItem) {
      const item = findPrevItem(this._treeContextState.focusedItem);
      if (item) {
        this._focusItem(item);
        if (this._treeContextState.isShiftPressed && this.multiSelect) {
          item.selected = !item.selected;
          this._emitSelectEvent();
        }
      }
    }
  }
  _focusNextItem() {
    if (this._treeContextState.focusedItem) {
      const item = findNextItem(this._treeContextState.focusedItem);
      if (item) {
        this._focusItem(item);
        if (this._treeContextState.isShiftPressed && this.multiSelect) {
          item.selected = !item.selected;
          this._emitSelectEvent();
        }
      }
    }
  }
  //#endregion
  //#region event handlers
  _handleArrowRightPress() {
    if (!this._treeContextState.focusedItem) {
      return;
    }
    const { focusedItem } = this._treeContextState;
    if (focusedItem.branch) {
      if (focusedItem.open) {
        this._focusNextItem();
      } else {
        focusedItem.open = true;
      }
    }
  }
  _handleArrowLeftPress(ev) {
    if (ev.ctrlKey) {
      this.collapseAll();
      return;
    }
    if (!this._treeContextState.focusedItem) {
      return;
    }
    const { focusedItem } = this._treeContextState;
    const parent = findParentItem(focusedItem);
    if (!focusedItem.branch) {
      if (parent && parent.branch) {
        this._focusItem(parent);
      }
    } else {
      if (focusedItem.open) {
        focusedItem.open = false;
      } else {
        if (parent && parent.branch) {
          this._focusItem(parent);
        }
      }
    }
  }
  _handleArrowDownPress() {
    if (this._treeContextState.focusedItem) {
      this._focusNextItem();
    } else {
      this._focusItem(this._assignedTreeItems[0]);
    }
  }
  _handleArrowUpPress() {
    if (this._treeContextState.focusedItem) {
      this._focusPrevItem();
    } else {
      this._focusItem(this._assignedTreeItems[0]);
    }
  }
  _handleEnterPress() {
    const { focusedItem } = this._treeContextState;
    if (focusedItem) {
      this._treeContextState.selectedItems.forEach((li) => li.selected = false);
      this._treeContextState.selectedItems.clear();
      this._highlightIndentGuides();
      focusedItem.selected = true;
      this._emitSelectEvent();
      if (focusedItem.branch) {
        focusedItem.open = !focusedItem.open;
      }
    }
  }
  _handleShiftPress() {
    this._treeContextState.isShiftPressed = true;
  }
  //#endregion
  render() {
    return b`<div>
      <slot @slotchange=${this._handleSlotChange}></slot>
    </div>`;
  }
};
VscodeTree.styles = styles$1;
__decorate$1([
  n$3({ type: String, attribute: "expand-mode" })
], VscodeTree.prototype, "expandMode", void 0);
__decorate$1([
  n$3({ type: Boolean, reflect: true, attribute: "hide-arrows" })
], VscodeTree.prototype, "hideArrows", void 0);
__decorate$1([
  n$3({ type: Number, reflect: true })
], VscodeTree.prototype, "indent", void 0);
__decorate$1([
  n$3({
    type: String,
    attribute: "indent-guides",
    useDefault: true,
    reflect: true
  })
], VscodeTree.prototype, "indentGuides", void 0);
__decorate$1([
  n$3({ type: Boolean, reflect: true, attribute: "multi-select" })
], VscodeTree.prototype, "multiSelect", void 0);
__decorate$1([
  e2({ context: treeContext })
], VscodeTree.prototype, "_treeContextState", void 0);
__decorate$1([
  e2({ context: configContext })
], VscodeTree.prototype, "_configContext", void 0);
__decorate$1([
  o$1({ selector: "vscode-tree-item" })
], VscodeTree.prototype, "_assignedTreeItems", void 0);
VscodeTree = __decorate$1([
  customElement("vscode-tree")
], VscodeTree);
o$7({
  tagName: "vscode-tree",
  elementClass: VscodeTree,
  react: E$1,
  displayName: "VscodeTree",
  events: {
    onVscTreeSelect: "vsc-tree-select"
  }
});
const styles = [
  defaultStyles,
  i$6`
    :host {
      --hover-outline-color: transparent;
      --hover-outline-style: solid;
      --hover-outline-width: 0;

      --selected-outline-color: transparent;
      --selected-outline-style: solid;
      --selected-outline-width: 0;

      cursor: pointer;
      display: block;
      user-select: none;
    }

    ::slotted(vscode-icon) {
      display: block;
    }

    .root {
      display: block;
    }

    .wrapper {
      align-items: flex-start;
      color: var(--vscode-foreground, #cccccc);
      display: flex;
      flex-wrap: nowrap;
      font-family: var(--vscode-font-family, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      font-weight: var(--vscode-font-weight, normal);
      line-height: 22px;
      min-height: 22px;
      outline-offset: -1px;
      padding-right: 12px;
    }

    .wrapper:hover {
      background-color: var(--vscode-list-hoverBackground, #2a2d2e);
      color: var(
        --vscode-list-hoverForeground,
        var(--vscode-foreground, #cccccc)
      );
    }

    :host([selected]) .wrapper {
      color: var(--internal-selectionForeground);
      background-color: var(--internal-selectionBackground);
    }

    :host([selected]) ::slotted(vscode-icon) {
      color: var(--internal-selectionForeground);
    }

    :host(:focus) {
      outline: none;
    }

    :host(:focus) .wrapper.active {
      outline-color: var(
        --vscode-list-focusAndSelectionOutline,
        var(--vscode-list-focusOutline, #0078d4)
      );
      outline-style: solid;
      outline-width: 1px;
    }

    .arrow-container {
      align-items: center;
      display: var(--vsc-tree-item-arrow-display);
      height: 22px;
      justify-content: center;
      padding-left: 8px;
      padding-right: 6px;
      width: 16px;
    }

    .arrow-container svg {
      display: block;
      fill: var(--vscode-icon-foreground, #cccccc);
    }

    .arrow-container.icon-rotated svg {
      transform: rotate(90deg);
    }

    :host([selected]) .arrow-container svg {
      fill: var(--internal-selectionIconForeground);
    }

    .icon-container {
      align-items: center;
      display: flex;
      justify-content: center;
      margin-right: 3px;
      min-height: 22px;
      overflow: hidden;
    }

    .icon-container slot {
      display: block;
    }

    .icon-container.has-icon {
      min-width: 22px;
      max-width: 22px;
      max-height: 22px;
    }

    :host(:is(:--show-actions, :state(show-actions))) .icon-container {
      overflow: visible;
    }

    .children {
      position: relative;
    }

    .children.guide:before {
      background-color: var(
        --vscode-tree-inactiveIndentGuidesStroke,
        rgba(88, 88, 88, 0.4)
      );
      content: '';
      display: none;
      height: 100%;
      left: var(--indentation-guide-left);
      pointer-events: none;
      position: absolute;
      width: 1px;
      z-index: 1;
    }

    .children.guide.default-guide:before {
      display: var(--internal-defaultIndentGuideDisplay);
    }

    .children.guide.highlighted-guide:before {
      display: var(--internal-highlightedIndentGuideDisplay);
      background-color: var(--vscode-tree-indentGuidesStroke, #585858);
    }

    .content {
      display: flex;
      align-items: center;
      flex-wrap: nowrap; /* prevent wrapping; allow ellipses via min-width: 0 */
      min-width: 0;
      width: 100%;
      line-height: 22px;
    }

    .label {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      flex: 0 1 auto;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .description {
      color: var(--vscode-foreground, #cccccc);
      opacity: 0.7;
      display: none;
      flex: 0 1 auto;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .content.has-description .description {
      display: flex;
      align-items: center;
      justify-content: flex-start;
      flex: 1 1 0%; /* description takes remaining space, yields first when shrinking */
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      margin-left: 0.5em;
    }

    .content.has-description .label {
      flex: 0 1 auto; /* label only grows when description missing */
    }

    .content:not(.has-description) .label {
      flex: 1 1 auto;
    }

    .label ::slotted(*) {
      display: inline-block;
      max-width: 100%;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .description ::slotted(*) {
      display: inline-block;
      max-width: 100%;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .actions {
      align-items: center;
      align-self: center;
      display: none;
      flex: 0 0 auto;
      gap: 2px;
      margin-left: auto;
      min-height: 22px;
      color: inherit;
    }

    .actions ::slotted(*) {
      align-items: center;
      display: inline-flex;
      height: 22px;
    }

    .actions ::slotted(button) {
      cursor: pointer;
    }

    .actions ::slotted([hidden]) {
      display: none !important;
    }

    :host(
        :is(
          :--has-actions:--show-actions,
          :--has-actions:state(show-actions),
          :state(has-actions):--show-actions,
          :state(has-actions):state(show-actions)
        )
      )
      .actions {
      display: inline-flex;
    }

    .decoration {
      align-items: center;
      align-self: center;
      color: inherit;
      display: none;
      flex: 0 0 auto;
      gap: 4px;
      margin-left: auto;
      min-height: 22px;
    }

    :host(:is(:--has-decoration, :state(has-decoration))) .decoration {
      display: inline-flex;
    }

    :host(:is(:--show-actions, :state(show-actions))) .decoration {
      margin-left: 6px;
    }

    :host([selected]) ::slotted([slot='decoration']),
    :host([selected]) ::slotted([slot='decoration']) * {
      color: inherit !important;
    }

    :host([selected]) .description {
      color: var(--internal-selectionForeground, #ffffff);
      opacity: 0.8;
    }

    :host([selected]) :is(:state(focus-visible), :--focus-visible) .description,
    :host([selected]:focus-within) .description {
      opacity: 0.95;
    }

    :host([branch]) ::slotted(vscode-tree-item) {
      display: none;
    }

    :host([branch][open]) ::slotted(vscode-tree-item) {
      display: block;
    }
  `
];
var __decorate = function(decorators, target, key, desc) {
  var c2 = arguments.length, r2 = c2 < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d2;
  if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r2 = Reflect.decorate(decorators, target, key, desc);
  else for (var i4 = decorators.length - 1; i4 >= 0; i4--) if (d2 = decorators[i4]) r2 = (c2 < 3 ? d2(r2) : c2 > 3 ? d2(target, key, r2) : d2(target, key)) || r2;
  return c2 > 3 && r2 && Object.defineProperty(target, key, r2), r2;
};
var VscodeTreeItem_1;
const BASE_INDENT = 3;
const ARROW_CONTAINER_WIDTH = 30;
const arrowIcon = b`<svg
  width="16"
  height="16"
  viewBox="0 0 16 16"
  xmlns="http://www.w3.org/2000/svg"
>
  <path
    fill-rule="evenodd"
    clip-rule="evenodd"
    d="M10.072 8.024L5.715 3.667l.618-.62L11 7.716v.618L6.333 13l-.618-.619 4.357-4.357z"
  />
</svg>`;
function getParentItem(childItem) {
  if (!childItem.parentElement) {
    return null;
  }
  if (!(childItem.parentElement instanceof VscodeTreeItem)) {
    return null;
  }
  return childItem.parentElement;
}
let VscodeTreeItem = VscodeTreeItem_1 = class VscodeTreeItem2 extends VscElement {
  set selected(selected) {
    this._selected = selected;
    if (selected) {
      this._treeContextState.selectedItems.add(this);
    } else {
      this._treeContextState.selectedItems.delete(this);
    }
    this.ariaSelected = selected ? "true" : "false";
    this._updateActionsVisibility();
  }
  get selected() {
    return this._selected;
  }
  set path(newPath) {
    this._path = newPath;
  }
  get path() {
    return this._path;
  }
  //#endregion
  //#region lifecycle methods
  constructor() {
    super();
    this.active = false;
    this.branch = false;
    this.hasActiveItem = false;
    this.hasSelectedItem = false;
    this.highlightedGuides = false;
    this.open = false;
    this.level = 0;
    this._selected = false;
    this._path = [];
    this._hasBranchIcon = false;
    this._hasBranchOpenedIcon = false;
    this._hasLeafIcon = false;
    this._hasDescriptionSlotContent = false;
    this._hasActionsSlotContent = false;
    this._hasDecorationSlotContent = false;
    this._treeContextState = {
      isShiftPressed: false,
      selectedItems: /* @__PURE__ */ new Set(),
      hoveredItem: null,
      allItems: null,
      itemListUpToDate: false,
      focusedItem: null,
      prevFocusedItem: null,
      hasBranchItem: false,
      rootElement: null,
      activeItem: null
    };
    this._isPointerInside = false;
    this._hasKeyboardFocus = false;
    this._handleMainSlotChange = () => {
      this._mainSlotChange();
      this._treeContextState.itemListUpToDate = false;
    };
    this._handleComponentFocus = () => {
      if (this._treeContextState.focusedItem && this._treeContextState.focusedItem !== this) {
        if (!this._treeContextState.isShiftPressed) {
          this._treeContextState.prevFocusedItem = this._treeContextState.focusedItem;
        }
        this._treeContextState.focusedItem = null;
      }
      this._treeContextState.focusedItem = this;
    };
    this._handlePointerEnter = () => {
      this._isPointerInside = true;
      this._claimHover();
    };
    this._handlePointerLeave = (ev) => {
      this._isPointerInside = false;
      if (this._treeContextState.hoveredItem === this) {
        this._treeContextState.hoveredItem = null;
      }
      this._clearHoverState();
      const relatedTarget = ev.relatedTarget;
      if (relatedTarget instanceof Element) {
        const nextItem = relatedTarget.closest("vscode-tree-item");
        if (nextItem && nextItem !== this && nextItem.isConnected) {
          nextItem._adoptHoverFromSibling();
        }
      }
    };
    this._handleFocusIn = () => {
      this._updateFocusState();
    };
    this._handleFocusOut = () => {
      this._updateFocusState();
    };
    this._internals = this.attachInternals();
    this.addEventListener("focus", this._handleComponentFocus);
    this.addEventListener("pointerenter", this._handlePointerEnter);
    this.addEventListener("pointerleave", this._handlePointerLeave);
    this.addEventListener("focusin", this._handleFocusIn);
    this.addEventListener("focusout", this._handleFocusOut);
  }
  connectedCallback() {
    super.connectedCallback();
    this._mainSlotChange();
    this.role = "treeitem";
    this.ariaDisabled = "false";
  }
  firstUpdated(changedProperties) {
    super.firstUpdated(changedProperties);
    this._refreshDescriptionSlotState();
    this._refreshActionsSlotState();
    this._refreshDecorationSlotState();
    if (this.matches(":hover")) {
      this._isPointerInside = true;
      this._claimHover();
    } else {
      this._updateActionsVisibility();
    }
  }
  willUpdate(changedProperties) {
    if (changedProperties.has("active")) {
      this._toggleActiveState();
    }
    if (changedProperties.has("open") || changedProperties.has("branch")) {
      this._setAriaExpanded();
    }
  }
  //#endregion
  //#region private methods
  _setAriaExpanded() {
    if (!this.branch) {
      this.ariaExpanded = null;
    } else {
      this.ariaExpanded = this.open ? "true" : "false";
    }
  }
  _setHasActiveItemFlagOnParent(childItem, value) {
    const parent = getParentItem(childItem);
    if (parent) {
      parent.hasActiveItem = value;
    }
  }
  _refreshDescriptionSlotState() {
    const hasContent = (this._descriptionSlotElements?.length ?? 0) > 0;
    this._hasDescriptionSlotContent = hasContent;
    this._setCustomState("has-description", hasContent);
  }
  _refreshActionsSlotState() {
    const hasContent = (this._actionsSlotElements?.length ?? 0) > 0;
    this._hasActionsSlotContent = hasContent;
    this._setCustomState("has-actions", hasContent);
    this._updateActionsVisibility();
  }
  _refreshDecorationSlotState() {
    const hasContent = (this._decorationSlotElements?.length ?? 0) > 0;
    const prevHasDecoration = this._hasDecorationSlotContent;
    this._hasDecorationSlotContent = hasContent;
    this._setCustomState("has-decoration", hasContent);
    if (prevHasDecoration !== hasContent) {
      this.requestUpdate();
    }
  }
  _setCustomState(stateName, present) {
    if (!this._internals?.states) {
      return;
    }
    try {
      if (present) {
        this._internals.states.add(stateName);
      } else {
        this._internals.states.delete(stateName);
      }
    } catch {
      if (present) {
        this._internals.states.add(`--${stateName}`);
      } else {
        this._internals.states.delete(`--${stateName}`);
      }
    }
  }
  _getActiveElement() {
    const root = this.getRootNode({ composed: true });
    if (root instanceof Document) {
      return root.activeElement instanceof Element ? root.activeElement : null;
    }
    if (root instanceof ShadowRoot) {
      return root.activeElement instanceof Element ? root.activeElement : null;
    }
    return null;
  }
  _isActiveElementInActions(activeElement) {
    if (!activeElement) {
      return false;
    }
    return (this._actionsSlotElements ?? []).some((element) => element === activeElement || element.contains(activeElement));
  }
  _updateActionsVisibility() {
    if (!this._hasActionsSlotContent) {
      this._setCustomState("show-actions", false);
      return;
    }
    const activeElement = this._getActiveElement();
    const isActionsFocused = this._isActiveElementInActions(activeElement);
    const shouldShow = this.selected || this._isPointerInside || this._hasKeyboardFocus || isActionsFocused;
    this._setCustomState("show-actions", shouldShow);
  }
  _updateFocusState() {
    const hostFocusVisible = this.matches(":focus-visible");
    this._setCustomState("focus-visible", hostFocusVisible);
    const activeElement = this._getActiveElement();
    let owner = null;
    if (activeElement instanceof Element) {
      owner = activeElement.closest("vscode-tree-item");
      if (!owner) {
        const root = activeElement.getRootNode();
        if (root instanceof ShadowRoot && root.host instanceof VscodeTreeItem_1) {
          owner = root.host;
        }
      }
    }
    const hasKeyboardFocus = owner === this;
    this._hasKeyboardFocus = hasKeyboardFocus;
    this._setCustomState("keyboard-focus", hasKeyboardFocus);
    this._updateActionsVisibility();
  }
  _clearHoverState() {
    this._isPointerInside = false;
    this._setCustomState("hover", false);
    this._updateActionsVisibility();
  }
  _adoptHoverFromSibling() {
    this._isPointerInside = true;
    this._claimHover();
  }
  _claimHover() {
    const treeState = this._treeContextState;
    if (treeState.hoveredItem && treeState.hoveredItem !== this) {
      treeState.hoveredItem._clearHoverState();
    }
    treeState.hoveredItem = this;
    this._setCustomState("hover", true);
    this._updateActionsVisibility();
  }
  _toggleActiveState() {
    if (this.active) {
      if (this._treeContextState.activeItem) {
        this._treeContextState.activeItem.active = false;
        this._setHasActiveItemFlagOnParent(this._treeContextState.activeItem, false);
      }
      this._treeContextState.activeItem = this;
      this._setHasActiveItemFlagOnParent(this, true);
      this.tabIndex = 0;
      this._setCustomState("active", true);
    } else {
      if (this._treeContextState.activeItem === this) {
        this._treeContextState.activeItem = null;
        this._setHasActiveItemFlagOnParent(this, false);
      }
      this.tabIndex = -1;
      this._setCustomState("active", false);
    }
  }
  _selectItem(isCtrlDown) {
    const { selectedItems } = this._treeContextState;
    const { multiSelect } = this._configContext;
    const prevSelected = new Set(selectedItems);
    if (multiSelect && isCtrlDown) {
      this.selected = !this.selected;
    } else {
      Array.from(selectedItems).forEach((li) => {
        if (li !== this) {
          li.selected = false;
        }
      });
      selectedItems.clear();
      this.selected = true;
    }
    const affected = /* @__PURE__ */ new Set([
      ...prevSelected,
      ...selectedItems
    ]);
    affected.add(this);
    affected.forEach((li) => li._updateActionsVisibility());
  }
  _selectRange() {
    const prevFocused = this._treeContextState.prevFocusedItem;
    if (!prevFocused || prevFocused === this) {
      return;
    }
    const prevSelected = new Set(this._treeContextState.selectedItems);
    if (!this._treeContextState.itemListUpToDate) {
      this._treeContextState.allItems = this._treeContextState.rootElement.querySelectorAll("vscode-tree-item");
      if (this._treeContextState.allItems) {
        this._treeContextState.allItems.forEach((li, i4) => {
          li.dataset.score = i4.toString();
        });
      }
      this._treeContextState.itemListUpToDate = true;
    }
    let from = +(prevFocused.dataset.score ?? -1);
    let to = +(this.dataset.score ?? -1);
    if (from > to) {
      [from, to] = [to, from];
    }
    Array.from(this._treeContextState.selectedItems).forEach((li) => li.selected = false);
    this._treeContextState.selectedItems.clear();
    this._selectItemsAndAllVisibleDescendants(from, to);
    const affected = /* @__PURE__ */ new Set([
      ...prevSelected,
      ...this._treeContextState.selectedItems
    ]);
    affected.add(this);
    affected.forEach((li) => li._updateActionsVisibility());
  }
  _selectItemsAndAllVisibleDescendants(from, to) {
    let i4 = from;
    while (i4 <= to) {
      if (this._treeContextState.allItems) {
        const item = this._treeContextState.allItems[i4];
        if (item.branch && !item.open) {
          item.selected = true;
          const numChildren = item.querySelectorAll("vscode-tree-item").length;
          i4 += numChildren;
        } else if (item.branch && item.open) {
          item.selected = true;
          i4 += this._selectItemsAndAllVisibleDescendants(i4 + 1, to);
        } else {
          item.selected = true;
          i4 += 1;
        }
      }
    }
    return i4;
  }
  _mainSlotChange() {
    this._initiallyAssignedTreeItems.forEach((li) => {
      li.setAttribute("slot", "children");
    });
  }
  //#endregion
  //#region event handlers
  _handleChildrenSlotChange() {
    initPathTrackerProps(this, this._childrenTreeItems);
    if (this._treeContextState.rootElement) {
      this._treeContextState.rootElement.updateHasBranchItemFlag();
    }
  }
  _handleDescriptionSlotChange() {
    this._refreshDescriptionSlotState();
  }
  _handleActionsSlotChange() {
    this._refreshActionsSlotState();
  }
  _handleDecorationSlotChange() {
    this._refreshDecorationSlotState();
  }
  _handleContentClick(ev) {
    ev.stopPropagation();
    const isCtrlDown = ev.ctrlKey || ev.metaKey;
    const isShiftDown = ev.shiftKey;
    if (isShiftDown && this._configContext.multiSelect) {
      this._selectRange();
      this._treeContextState.emitSelectEvent?.();
      this.updateComplete.then(() => {
        this._treeContextState.highlightIndentGuides?.();
      });
    } else {
      this._selectItem(isCtrlDown);
      this._treeContextState.emitSelectEvent?.();
      this.updateComplete.then(() => {
        this._treeContextState.highlightIndentGuides?.();
      });
      if (this._configContext.expandMode === ExpandMode.singleClick) {
        if (this.branch && !(this._configContext.multiSelect && isCtrlDown)) {
          this.open = !this.open;
        }
      }
    }
    this.active = true;
    if (!isShiftDown) {
      this._treeContextState.prevFocusedItem = this;
    }
  }
  _handleDoubleClick(ev) {
    if (this._configContext.expandMode === ExpandMode.doubleClick) {
      if (this.branch && !(this._configContext.multiSelect && (ev.ctrlKey || ev.metaKey))) {
        this.open = !this.open;
      }
    }
  }
  _handleIconSlotChange(ev) {
    const slot = ev.target;
    const hasContent = slot.assignedElements().length > 0;
    switch (slot.name) {
      case "icon-branch":
        this._hasBranchIcon = hasContent;
        break;
      case "icon-branch-opened":
        this._hasBranchOpenedIcon = hasContent;
        break;
      case "icon-leaf":
        this._hasLeafIcon = hasContent;
        break;
    }
  }
  //#endregion
  render() {
    const { hideArrows, indent, indentGuides } = this._configContext;
    const { hasBranchItem } = this._treeContextState;
    let indentation = BASE_INDENT + this.level * indent;
    const guideOffset = !hideArrows ? 13 : 3;
    const indentGuideX = BASE_INDENT + this.level * indent + guideOffset;
    if (!this.branch && !hideArrows && hasBranchItem) {
      indentation += ARROW_CONTAINER_WIDTH;
    }
    const hasVisibleIcon = this._hasBranchIcon && this.branch || this._hasBranchOpenedIcon && this.branch && this.open || this._hasLeafIcon && !this.branch;
    const wrapperClasses = {
      wrapper: true,
      active: this.active,
      "has-description": this._hasDescriptionSlotContent,
      "has-actions": this._hasActionsSlotContent,
      "has-decoration": this._hasDecorationSlotContent
    };
    const childrenClasses = {
      children: true,
      guide: indentGuides !== IndentGuides.none,
      "default-guide": indentGuides !== IndentGuides.none,
      "highlighted-guide": this.highlightedGuides
    };
    const iconContainerClasses = {
      "icon-container": true,
      "has-icon": hasVisibleIcon
    };
    const contentClasses = {
      content: true,
      "has-description": this._hasDescriptionSlotContent,
      "has-decoration": this._hasDecorationSlotContent
    };
    return b` <div class="root">
      <div
        class=${e$2(wrapperClasses)}
        part="wrapper"
        @click=${this._handleContentClick}
        @dblclick=${this._handleDoubleClick}
        .style=${stylePropertyMap({ paddingLeft: `${indentation}px` })}
      >
        ${this.branch && !hideArrows ? b`<div
              class=${e$2({
      "arrow-container": true,
      "icon-rotated": this.open
    })}
              part="arrow-icon-container"
            >
              ${arrowIcon}
            </div>` : A}
        <div class=${e$2(iconContainerClasses)} part="icon-container">
          ${this.branch && !this.open ? b`<slot
                name="icon-branch"
                @slotchange=${this._handleIconSlotChange}
              ></slot>` : A}
          ${this.branch && this.open ? b`<slot
                name="icon-branch-opened"
                @slotchange=${this._handleIconSlotChange}
              ></slot>` : A}
          ${!this.branch ? b`<slot
                name="icon-leaf"
                @slotchange=${this._handleIconSlotChange}
              ></slot>` : A}
        </div>
        <div class=${e$2(contentClasses)} part="content">
          <span class="label" part="label">
            <slot @slotchange=${this._handleMainSlotChange}></slot>
          </span>
          <span
            class="description"
            part="description"
            ?hidden=${!this._hasDescriptionSlotContent}
          >
            <slot
              name="description"
              @slotchange=${this._handleDescriptionSlotChange}
            ></slot>
          </span>
          <div class="actions" part="actions">
            <slot
              name="actions"
              @slotchange=${this._handleActionsSlotChange}
            ></slot>
          </div>
          <div class="decoration" part="decoration">
            <slot
              name="decoration"
              @slotchange=${this._handleDecorationSlotChange}
            ></slot>
          </div>
        </div>
      </div>
      <div
        class=${e$2(childrenClasses)}
        .style=${stylePropertyMap({
      "--indentation-guide-left": `${indentGuideX}px`
    })}
        role="group"
        part="children"
      >
        <slot
          name="children"
          @slotchange=${this._handleChildrenSlotChange}
        ></slot>
      </div>
    </div>`;
  }
};
VscodeTreeItem.styles = styles;
__decorate([
  n$3({ type: Boolean })
], VscodeTreeItem.prototype, "active", void 0);
__decorate([
  n$3({ type: Boolean, reflect: true })
], VscodeTreeItem.prototype, "branch", void 0);
__decorate([
  n$3({ type: Boolean })
], VscodeTreeItem.prototype, "hasActiveItem", void 0);
__decorate([
  n$3({ type: Boolean })
], VscodeTreeItem.prototype, "hasSelectedItem", void 0);
__decorate([
  n$3({ type: Boolean })
], VscodeTreeItem.prototype, "highlightedGuides", void 0);
__decorate([
  n$3({ type: Boolean, reflect: true })
], VscodeTreeItem.prototype, "open", void 0);
__decorate([
  n$3({ type: Number, reflect: true })
], VscodeTreeItem.prototype, "level", void 0);
__decorate([
  n$3({ type: Boolean, reflect: true })
], VscodeTreeItem.prototype, "selected", null);
__decorate([
  r$1()
], VscodeTreeItem.prototype, "_hasBranchIcon", void 0);
__decorate([
  r$1()
], VscodeTreeItem.prototype, "_hasBranchOpenedIcon", void 0);
__decorate([
  r$1()
], VscodeTreeItem.prototype, "_hasLeafIcon", void 0);
__decorate([
  r$1()
], VscodeTreeItem.prototype, "_hasDescriptionSlotContent", void 0);
__decorate([
  r$1()
], VscodeTreeItem.prototype, "_hasActionsSlotContent", void 0);
__decorate([
  r$1()
], VscodeTreeItem.prototype, "_hasDecorationSlotContent", void 0);
__decorate([
  c({ context: treeContext, subscribe: true })
], VscodeTreeItem.prototype, "_treeContextState", void 0);
__decorate([
  c({ context: configContext, subscribe: true })
], VscodeTreeItem.prototype, "_configContext", void 0);
__decorate([
  o$1({ selector: "vscode-tree-item" })
], VscodeTreeItem.prototype, "_initiallyAssignedTreeItems", void 0);
__decorate([
  o$1({ selector: "vscode-tree-item", slot: "children" })
], VscodeTreeItem.prototype, "_childrenTreeItems", void 0);
__decorate([
  o$1({ slot: "description", flatten: true })
], VscodeTreeItem.prototype, "_descriptionSlotElements", void 0);
__decorate([
  o$1({ slot: "actions", flatten: true })
], VscodeTreeItem.prototype, "_actionsSlotElements", void 0);
__decorate([
  o$1({ slot: "decoration", flatten: true })
], VscodeTreeItem.prototype, "_decorationSlotElements", void 0);
VscodeTreeItem = VscodeTreeItem_1 = __decorate([
  customElement("vscode-tree-item")
], VscodeTreeItem);
o$7({
  tagName: "vscode-tree-item",
  elementClass: VscodeTreeItem,
  react: E$1,
  displayName: "VscodeTreeItem"
});
export {
  VscodeLabel2 as V,
  VscodeFormHelper2 as a,
  VscodeTextfield2 as b,
  VscodeCheckbox2 as c,
  VscodeButton2 as d,
  VscodeTextarea2 as e,
  VscodeSingleSelect2 as f,
  VscodeOption2 as g,
  VscodeSplitLayout2 as h,
  VscodeRadioGroup2 as i,
  VscodeRadio2 as j,
  VscodeDivider2 as k,
  useMutation as u
};
//# sourceMappingURL=VscodeTreeItem.js.map
