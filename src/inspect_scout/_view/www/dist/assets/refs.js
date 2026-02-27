import { a as useApi, b as useAsyncDataFromQuery, s as skipToken, u as useStore, r as reactExports, t as toRelativePath, j as jsxRuntimeExports, c as clsx, I as lib, J as asyncJsonParse, B as data$1, A as ApplicationIcons, m as useSearchParams, q as scanResultRoute } from "./index.js";
import { a as useScanRoute } from "./useScansDir.js";
import { u as useMapAsyncData } from "./useMapAsyncData.js";
import { i as isJson, c as MarkdownDivWithReferences, R as RecordTree, u as useEventNodes, T as TranscriptViewNodes, d as ChatView } from "./TranscriptViewNodes.js";
import { p as printArray } from "./array.js";
import { a as formatPrettyDecimal } from "./ToolButton.js";
import { p as printObject } from "./object.js";
const useScan = (params) => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: params === skipToken ? [skipToken] : ["scan", params.scansDir, params.scanPath, "scans-inv"],
    queryFn: params === skipToken ? skipToken : () => api.getScan(params.scansDir, params.scanPath),
    staleTime: 1e4
  });
};
const useSelectedScan = () => {
  const { resolvedScansDir, scanPath } = useScanRoute();
  const setSelectedScanLocation = useStore(
    (state) => state.setSelectedScanLocation
  );
  reactExports.useEffect(() => {
    if (scanPath) {
      setSelectedScanLocation(scanPath);
    }
  }, [scanPath, setSelectedScanLocation]);
  return useScan(
    resolvedScansDir && scanPath ? { scansDir: resolvedScansDir, scanPath } : skipToken
  );
};
function getScanDisplayName(scan2, scansDir) {
  if (!scan2) return void 0;
  if (scansDir && scan2.location) {
    const relativePath = toRelativePath(scan2.location, scansDir);
    if (relativePath) {
      return relativePath;
    }
  }
  return scan2.spec.scan_name === "job" ? "scan" : scan2.spec.scan_name;
}
const resultIdentifierStr = (summary) => {
  const identifier = resultIdentifier(summary);
  if (!identifier) {
    return void 0;
  }
  if (identifier.secondaryId || identifier.epoch) {
    const id = [];
    if (identifier.taskSet) {
      id.push(identifier.taskSet);
    }
    id.push(String(identifier.id));
    const result2 = [id.join("/")];
    if (identifier.secondaryId) {
      result2.push(String(identifier.secondaryId));
    }
    if (identifier.epoch) {
      result2.push(`(${String(identifier.epoch)})`);
    }
    return result2.join(" ");
  }
};
const resultIdentifier = (summary) => {
  if (!summary) {
    return {
      id: "unknown"
    };
  }
  if (summary.inputType === "transcript") {
    const sampleIdentifier = getSampleIdentifier(summary);
    if (sampleIdentifier) {
      return sampleIdentifier;
    }
  } else if (summary.inputType === "message") {
    const sampleIdentifier = getSampleIdentifier(summary);
    return {
      id: summary.transcriptSourceId,
      secondaryId: sampleIdentifier ? sampleIdentifier.id : void 0,
      epoch: sampleIdentifier ? sampleIdentifier.epoch : void 0
    };
  } else if (summary.inputType === "event") {
    const sampleIdentifier = getSampleIdentifier(summary);
    return {
      id: summary.transcriptSourceId,
      secondaryId: sampleIdentifier ? sampleIdentifier.id : void 0,
      epoch: sampleIdentifier ? sampleIdentifier.epoch : void 0
    };
  }
  return {
    id: summary.transcriptSourceId
  };
};
const getSampleIdentifier = (summary) => {
  const id = summary.transcriptTaskId;
  const epoch = summary.transcriptTaskRepeat;
  if (id && epoch) {
    const taskSet = summary.transcriptTaskSet;
    return {
      id,
      epoch,
      taskSet
    };
  }
  return void 0;
};
const resultLog = (summary) => {
  if (summary.inputType === "transcript") {
    return summary.transcriptMetadata["log"];
  }
  return void 0;
};
const CardHeader = ({
  id,
  icon,
  type,
  label,
  className,
  children
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: clsx(
        "card-header-container",
        "text-style-label",
        className,
        type === "modern" ? "card-header-modern" : ""
      ),
      id: id || "",
      children: [
        icon ? /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx("card-header-icon", icon) }) : /* @__PURE__ */ jsxRuntimeExports.jsx(
          "span",
          {
            className: clsx("card-header-icon", "card-header-icon-empty")
          }
        ),
        label ? label : "",
        " ",
        children
      ]
    }
  );
};
const CardBody = ({
  id,
  children,
  className,
  padded = true
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: clsx(
        "card-body",
        className,
        !padded ? "card-no-padding" : void 0
      ),
      id: id || "",
      children
    }
  );
};
const Card = ({ id, children, className }) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx("card", className), id, children });
};
function __awaiter(thisArg, _arguments, P, generator) {
  function adopt(value2) {
    return value2 instanceof P ? value2 : new P(function(resolve2) {
      resolve2(value2);
    });
  }
  return new (P || (P = Promise))(function(resolve2, reject) {
    function fulfilled(value2) {
      try {
        step(generator.next(value2));
      } catch (e) {
        reject(e);
      }
    }
    function rejected(value2) {
      try {
        step(generator["throw"](value2));
      } catch (e) {
        reject(e);
      }
    }
    function step(result2) {
      result2.done ? resolve2(result2.value) : adopt(result2.value).then(fulfilled, rejected);
    }
    step((generator = generator.apply(thisArg, _arguments || [])).next());
  });
}
function __values(o) {
  var s = typeof Symbol === "function" && Symbol.iterator, m = s && o[s], i = 0;
  if (m) return m.call(o);
  if (o && typeof o.length === "number") return {
    next: function() {
      if (o && i >= o.length) o = void 0;
      return { value: o && o[i++], done: !o };
    }
  };
  throw new TypeError(s ? "Object is not iterable." : "Symbol.iterator is not defined.");
}
function __await(v) {
  return this instanceof __await ? (this.v = v, this) : new __await(v);
}
function __asyncGenerator(thisArg, _arguments, generator) {
  if (!Symbol.asyncIterator) throw new TypeError("Symbol.asyncIterator is not defined.");
  var g = generator.apply(thisArg, _arguments || []), i, q = [];
  return i = Object.create((typeof AsyncIterator === "function" ? AsyncIterator : Object).prototype), verb("next"), verb("throw"), verb("return", awaitReturn), i[Symbol.asyncIterator] = function() {
    return this;
  }, i;
  function awaitReturn(f) {
    return function(v) {
      return Promise.resolve(v).then(f, reject);
    };
  }
  function verb(n, f) {
    if (g[n]) {
      i[n] = function(v) {
        return new Promise(function(a, b) {
          q.push([n, v, a, b]) > 1 || resume(n, v);
        });
      };
      if (f) i[n] = f(i[n]);
    }
  }
  function resume(n, v) {
    try {
      step(g[n](v));
    } catch (e) {
      settle(q[0][3], e);
    }
  }
  function step(r) {
    r.value instanceof __await ? Promise.resolve(r.value.v).then(fulfill, reject) : settle(q[0][2], r);
  }
  function fulfill(value2) {
    resume("next", value2);
  }
  function reject(value2) {
    resume("throw", value2);
  }
  function settle(f, v) {
    if (f(v), q.shift(), q.length) resume(q[0][0], q[0][1]);
  }
}
function __asyncDelegator(o) {
  var i, p;
  return i = {}, verb("next"), verb("throw", function(e) {
    throw e;
  }), verb("return"), i[Symbol.iterator] = function() {
    return this;
  }, i;
  function verb(n, f) {
    i[n] = o[n] ? function(v) {
      return (p = !p) ? { value: __await(o[n](v)), done: false } : f ? f(v) : v;
    } : f;
  }
}
function __asyncValues(o) {
  if (!Symbol.asyncIterator) throw new TypeError("Symbol.asyncIterator is not defined.");
  var m = o[Symbol.asyncIterator], i;
  return m ? m.call(o) : (o = typeof __values === "function" ? __values(o) : o[Symbol.iterator](), i = {}, verb("next"), verb("throw"), verb("return"), i[Symbol.asyncIterator] = function() {
    return this;
  }, i);
  function verb(n) {
    i[n] = o[n] && function(v) {
      return new Promise(function(resolve2, reject) {
        v = o[n](v), settle(resolve2, reject, v.done, v.value);
      });
    };
  }
  function settle(resolve2, reject, d, v) {
    Promise.resolve(v).then(function(v2) {
      resolve2({ value: v2, done: d });
    }, reject);
  }
}
typeof SuppressedError === "function" ? SuppressedError : function(error2, suppressed, message) {
  var e = new Error(message);
  return e.name = "SuppressedError", e.error = error2, e.suppressed = suppressed, e;
};
const decoder = new TextDecoder("utf-8");
const decodeUtf8$1 = decoder.decode.bind(decoder);
const encoder = new TextEncoder();
const encodeUtf8$1 = (value2) => encoder.encode(value2);
const isNumber$1 = (x) => typeof x === "number";
const isBoolean = (x) => typeof x === "boolean";
const isFunction$1 = (x) => typeof x === "function";
const isObject$1 = (x) => x != null && Object(x) === x;
const isPromise = (x) => {
  return isObject$1(x) && isFunction$1(x.then);
};
const isIterable$1 = (x) => {
  return isObject$1(x) && isFunction$1(x[Symbol.iterator]);
};
const isAsyncIterable = (x) => {
  return isObject$1(x) && isFunction$1(x[Symbol.asyncIterator]);
};
const isArrowJSON = (x) => {
  return isObject$1(x) && isObject$1(x["schema"]);
};
const isIteratorResult = (x) => {
  return isObject$1(x) && "done" in x && "value" in x;
};
const isFileHandle = (x) => {
  return isObject$1(x) && isFunction$1(x["stat"]) && isNumber$1(x["fd"]);
};
const isFetchResponse = (x) => {
  return isObject$1(x) && isReadableDOMStream(x["body"]);
};
const isReadableInterop = (x) => "_getDOMStream" in x && "_getNodeStream" in x;
const isWritableDOMStream = (x) => {
  return isObject$1(x) && isFunction$1(x["abort"]) && isFunction$1(x["getWriter"]) && !isReadableInterop(x);
};
const isReadableDOMStream = (x) => {
  return isObject$1(x) && isFunction$1(x["cancel"]) && isFunction$1(x["getReader"]) && !isReadableInterop(x);
};
const isWritableNodeStream = (x) => {
  return isObject$1(x) && isFunction$1(x["end"]) && isFunction$1(x["write"]) && isBoolean(x["writable"]) && !isReadableInterop(x);
};
const isReadableNodeStream = (x) => {
  return isObject$1(x) && isFunction$1(x["read"]) && isFunction$1(x["pipe"]) && isBoolean(x["readable"]) && !isReadableInterop(x);
};
const isFlatbuffersByteBuffer = (x) => {
  return isObject$1(x) && isFunction$1(x["clear"]) && isFunction$1(x["bytes"]) && isFunction$1(x["position"]) && isFunction$1(x["setPosition"]) && isFunction$1(x["capacity"]) && isFunction$1(x["getBufferIdentifier"]) && isFunction$1(x["createLong"]);
};
const SharedArrayBuf = typeof SharedArrayBuffer !== "undefined" ? SharedArrayBuffer : ArrayBuffer;
function collapseContiguousByteRanges(chunks) {
  const result2 = chunks[0] ? [chunks[0]] : [];
  let xOffset, yOffset, xLen, yLen;
  for (let x, y, i = 0, j = 0, n = chunks.length; ++i < n; ) {
    x = result2[j];
    y = chunks[i];
    if (!x || !y || x.buffer !== y.buffer || y.byteOffset < x.byteOffset) {
      y && (result2[++j] = y);
      continue;
    }
    ({ byteOffset: xOffset, byteLength: xLen } = x);
    ({ byteOffset: yOffset, byteLength: yLen } = y);
    if (xOffset + xLen < yOffset || yOffset + yLen < xOffset) {
      y && (result2[++j] = y);
      continue;
    }
    result2[j] = new Uint8Array(x.buffer, xOffset, yOffset - xOffset + yLen);
  }
  return result2;
}
function memcpy(target, source2, targetByteOffset = 0, sourceByteLength = source2.byteLength) {
  const targetByteLength = target.byteLength;
  const dst = new Uint8Array(target.buffer, target.byteOffset, targetByteLength);
  const src = new Uint8Array(source2.buffer, source2.byteOffset, Math.min(sourceByteLength, targetByteLength));
  dst.set(src, targetByteOffset);
  return target;
}
function joinUint8Arrays(chunks, size) {
  const result2 = collapseContiguousByteRanges(chunks);
  const byteLength = result2.reduce((x, b) => x + b.byteLength, 0);
  let source2, sliced, buffer2;
  let offset2 = 0, index = -1;
  const length2 = Math.min(size || Number.POSITIVE_INFINITY, byteLength);
  for (const n = result2.length; ++index < n; ) {
    source2 = result2[index];
    sliced = source2.subarray(0, Math.min(source2.length, length2 - offset2));
    if (length2 <= offset2 + sliced.length) {
      if (sliced.length < source2.length) {
        result2[index] = source2.subarray(sliced.length);
      } else if (sliced.length === source2.length) {
        index++;
      }
      buffer2 ? memcpy(buffer2, sliced, offset2) : buffer2 = sliced;
      break;
    }
    memcpy(buffer2 || (buffer2 = new Uint8Array(length2)), sliced, offset2);
    offset2 += sliced.length;
  }
  return [buffer2 || new Uint8Array(0), result2.slice(index), byteLength - (buffer2 ? buffer2.byteLength : 0)];
}
function toArrayBufferView(ArrayBufferViewCtor, input) {
  let value2 = isIteratorResult(input) ? input.value : input;
  if (value2 instanceof ArrayBufferViewCtor) {
    if (ArrayBufferViewCtor === Uint8Array) {
      return new ArrayBufferViewCtor(value2.buffer, value2.byteOffset, value2.byteLength);
    }
    return value2;
  }
  if (!value2) {
    return new ArrayBufferViewCtor(0);
  }
  if (typeof value2 === "string") {
    value2 = encodeUtf8$1(value2);
  }
  if (value2 instanceof ArrayBuffer) {
    return new ArrayBufferViewCtor(value2);
  }
  if (value2 instanceof SharedArrayBuf) {
    return new ArrayBufferViewCtor(value2);
  }
  if (isFlatbuffersByteBuffer(value2)) {
    return toArrayBufferView(ArrayBufferViewCtor, value2.bytes());
  }
  return !ArrayBuffer.isView(value2) ? ArrayBufferViewCtor.from(value2) : value2.byteLength <= 0 ? new ArrayBufferViewCtor(0) : new ArrayBufferViewCtor(value2.buffer, value2.byteOffset, value2.byteLength / ArrayBufferViewCtor.BYTES_PER_ELEMENT);
}
const toInt32Array = (input) => toArrayBufferView(Int32Array, input);
const toBigInt64Array = (input) => toArrayBufferView(BigInt64Array, input);
const toUint8Array = (input) => toArrayBufferView(Uint8Array, input);
const pump$1 = (iterator) => {
  iterator.next();
  return iterator;
};
function* toArrayBufferViewIterator(ArrayCtor, source2) {
  const wrap2 = function* (x) {
    yield x;
  };
  const buffers = typeof source2 === "string" ? wrap2(source2) : ArrayBuffer.isView(source2) ? wrap2(source2) : source2 instanceof ArrayBuffer ? wrap2(source2) : source2 instanceof SharedArrayBuf ? wrap2(source2) : !isIterable$1(source2) ? wrap2(source2) : source2;
  yield* pump$1((function* (it) {
    let r = null;
    do {
      r = it.next(yield toArrayBufferView(ArrayCtor, r));
    } while (!r.done);
  })(buffers[Symbol.iterator]()));
  return new ArrayCtor();
}
const toUint8ArrayIterator = (input) => toArrayBufferViewIterator(Uint8Array, input);
function toArrayBufferViewAsyncIterator(ArrayCtor, source2) {
  return __asyncGenerator(this, arguments, function* toArrayBufferViewAsyncIterator_1() {
    if (isPromise(source2)) {
      return yield __await(yield __await(yield* __asyncDelegator(__asyncValues(toArrayBufferViewAsyncIterator(ArrayCtor, yield __await(source2))))));
    }
    const wrap2 = function(x) {
      return __asyncGenerator(this, arguments, function* () {
        yield yield __await(yield __await(x));
      });
    };
    const emit = function(source3) {
      return __asyncGenerator(this, arguments, function* () {
        yield __await(yield* __asyncDelegator(__asyncValues(pump$1((function* (it) {
          let r = null;
          do {
            r = it.next(yield r === null || r === void 0 ? void 0 : r.value);
          } while (!r.done);
        })(source3[Symbol.iterator]())))));
      });
    };
    const buffers = typeof source2 === "string" ? wrap2(source2) : ArrayBuffer.isView(source2) ? wrap2(source2) : source2 instanceof ArrayBuffer ? wrap2(source2) : source2 instanceof SharedArrayBuf ? wrap2(source2) : isIterable$1(source2) ? emit(source2) : !isAsyncIterable(source2) ? wrap2(source2) : source2;
    yield __await(
      // otherwise if AsyncIterable, use it
      yield* __asyncDelegator(__asyncValues(pump$1((function(it) {
        return __asyncGenerator(this, arguments, function* () {
          let r = null;
          do {
            r = yield __await(it.next(yield yield __await(toArrayBufferView(ArrayCtor, r))));
          } while (!r.done);
        });
      })(buffers[Symbol.asyncIterator]()))))
    );
    return yield __await(new ArrayCtor());
  });
}
const toUint8ArrayAsyncIterator = (input) => toArrayBufferViewAsyncIterator(Uint8Array, input);
function rebaseValueOffsets(offset2, length2, valueOffsets) {
  if (offset2 !== 0) {
    valueOffsets = valueOffsets.slice(0, length2);
    for (let i = -1, n = valueOffsets.length; ++i < n; ) {
      valueOffsets[i] += offset2;
    }
  }
  return valueOffsets.subarray(0, length2);
}
function compareArrayLike(a, b) {
  let i = 0;
  const n = a.length;
  if (n !== b.length) {
    return false;
  }
  if (n > 0) {
    do {
      if (a[i] !== b[i]) {
        return false;
      }
    } while (++i < n);
  }
  return true;
}
const streamAdapters = {
  fromIterable(source2) {
    return pump(fromIterable$1(source2));
  },
  fromAsyncIterable(source2) {
    return pump(fromAsyncIterable(source2));
  },
  fromDOMStream(source2) {
    return pump(fromDOMStream(source2));
  },
  fromNodeStream(stream) {
    return pump(fromNodeStream(stream));
  },
  // @ts-ignore
  toDOMStream(source2, options) {
    throw new Error(`"toDOMStream" not available in this environment`);
  },
  // @ts-ignore
  toNodeStream(source2, options) {
    throw new Error(`"toNodeStream" not available in this environment`);
  }
};
const pump = (iterator) => {
  iterator.next();
  return iterator;
};
function* fromIterable$1(source2) {
  let done, threw = false;
  let buffers = [], buffer2;
  let cmd, size, bufferLength = 0;
  function byteRange() {
    if (cmd === "peek") {
      return joinUint8Arrays(buffers, size)[0];
    }
    [buffer2, buffers, bufferLength] = joinUint8Arrays(buffers, size);
    return buffer2;
  }
  ({ cmd, size } = (yield /* @__PURE__ */ (() => null)()) || { cmd: "read", size: 0 });
  const it = toUint8ArrayIterator(source2)[Symbol.iterator]();
  try {
    do {
      ({ done, value: buffer2 } = Number.isNaN(size - bufferLength) ? it.next() : it.next(size - bufferLength));
      if (!done && buffer2.byteLength > 0) {
        buffers.push(buffer2);
        bufferLength += buffer2.byteLength;
      }
      if (done || size <= bufferLength) {
        do {
          ({ cmd, size } = yield byteRange());
        } while (size < bufferLength);
      }
    } while (!done);
  } catch (e) {
    threw = true;
    typeof it.throw === "function" && it.throw(e);
  } finally {
    threw === false && typeof it.return === "function" && it.return(null);
  }
  return null;
}
function fromAsyncIterable(source2) {
  return __asyncGenerator(this, arguments, function* fromAsyncIterable_1() {
    let done, threw = false;
    let buffers = [], buffer2;
    let cmd, size, bufferLength = 0;
    function byteRange() {
      if (cmd === "peek") {
        return joinUint8Arrays(buffers, size)[0];
      }
      [buffer2, buffers, bufferLength] = joinUint8Arrays(buffers, size);
      return buffer2;
    }
    ({ cmd, size } = (yield yield __await(/* @__PURE__ */ (() => null)())) || { cmd: "read", size: 0 });
    const it = toUint8ArrayAsyncIterator(source2)[Symbol.asyncIterator]();
    try {
      do {
        ({ done, value: buffer2 } = Number.isNaN(size - bufferLength) ? yield __await(it.next()) : yield __await(it.next(size - bufferLength)));
        if (!done && buffer2.byteLength > 0) {
          buffers.push(buffer2);
          bufferLength += buffer2.byteLength;
        }
        if (done || size <= bufferLength) {
          do {
            ({ cmd, size } = yield yield __await(byteRange()));
          } while (size < bufferLength);
        }
      } while (!done);
    } catch (e) {
      threw = true;
      typeof it.throw === "function" && (yield __await(it.throw(e)));
    } finally {
      threw === false && typeof it.return === "function" && (yield __await(it.return(new Uint8Array(0))));
    }
    return yield __await(null);
  });
}
function fromDOMStream(source2) {
  return __asyncGenerator(this, arguments, function* fromDOMStream_1() {
    let done = false, threw = false;
    let buffers = [], buffer2;
    let cmd, size, bufferLength = 0;
    function byteRange() {
      if (cmd === "peek") {
        return joinUint8Arrays(buffers, size)[0];
      }
      [buffer2, buffers, bufferLength] = joinUint8Arrays(buffers, size);
      return buffer2;
    }
    ({ cmd, size } = (yield yield __await(/* @__PURE__ */ (() => null)())) || { cmd: "read", size: 0 });
    const it = new AdaptiveByteReader(source2);
    try {
      do {
        ({ done, value: buffer2 } = Number.isNaN(size - bufferLength) ? yield __await(it["read"]()) : yield __await(it["read"](size - bufferLength)));
        if (!done && buffer2.byteLength > 0) {
          buffers.push(toUint8Array(buffer2));
          bufferLength += buffer2.byteLength;
        }
        if (done || size <= bufferLength) {
          do {
            ({ cmd, size } = yield yield __await(byteRange()));
          } while (size < bufferLength);
        }
      } while (!done);
    } catch (e) {
      threw = true;
      yield __await(it["cancel"](e));
    } finally {
      threw === false ? yield __await(it["cancel"]()) : source2["locked"] && it.releaseLock();
    }
    return yield __await(null);
  });
}
class AdaptiveByteReader {
  constructor(source2) {
    this.source = source2;
    this.reader = null;
    this.reader = this.source["getReader"]();
    this.reader["closed"].catch(() => {
    });
  }
  get closed() {
    return this.reader ? this.reader["closed"].catch(() => {
    }) : Promise.resolve();
  }
  releaseLock() {
    if (this.reader) {
      this.reader.releaseLock();
    }
    this.reader = null;
  }
  cancel(reason) {
    return __awaiter(this, void 0, void 0, function* () {
      const { reader, source: source2 } = this;
      reader && (yield reader["cancel"](reason).catch(() => {
      }));
      source2 && (source2["locked"] && this.releaseLock());
    });
  }
  read(size) {
    return __awaiter(this, void 0, void 0, function* () {
      if (size === 0) {
        return { done: this.reader == null, value: new Uint8Array(0) };
      }
      const result2 = yield this.reader.read();
      !result2.done && (result2.value = toUint8Array(result2));
      return result2;
    });
  }
}
const onEvent = (stream, event) => {
  const handler = (_) => resolve2([event, _]);
  let resolve2;
  return [event, handler, new Promise((r) => (resolve2 = r) && stream["once"](event, handler))];
};
function fromNodeStream(stream) {
  return __asyncGenerator(this, arguments, function* fromNodeStream_1() {
    const events = [];
    let event = "error";
    let done = false, err = null;
    let cmd, size, bufferLength = 0;
    let buffers = [], buffer2;
    function byteRange() {
      if (cmd === "peek") {
        return joinUint8Arrays(buffers, size)[0];
      }
      [buffer2, buffers, bufferLength] = joinUint8Arrays(buffers, size);
      return buffer2;
    }
    ({ cmd, size } = (yield yield __await(/* @__PURE__ */ (() => null)())) || { cmd: "read", size: 0 });
    if (stream["isTTY"]) {
      yield yield __await(new Uint8Array(0));
      return yield __await(null);
    }
    try {
      events[0] = onEvent(stream, "end");
      events[1] = onEvent(stream, "error");
      do {
        events[2] = onEvent(stream, "readable");
        [event, err] = yield __await(Promise.race(events.map((x) => x[2])));
        if (event === "error") {
          break;
        }
        if (!(done = event === "end")) {
          if (!Number.isFinite(size - bufferLength)) {
            buffer2 = toUint8Array(stream["read"]());
          } else {
            buffer2 = toUint8Array(stream["read"](size - bufferLength));
            if (buffer2.byteLength < size - bufferLength) {
              buffer2 = toUint8Array(stream["read"]());
            }
          }
          if (buffer2.byteLength > 0) {
            buffers.push(buffer2);
            bufferLength += buffer2.byteLength;
          }
        }
        if (done || size <= bufferLength) {
          do {
            ({ cmd, size } = yield yield __await(byteRange()));
          } while (size < bufferLength);
        }
      } while (!done);
    } finally {
      yield __await(cleanup(events, event === "error" ? err : null));
    }
    return yield __await(null);
    function cleanup(events2, err2) {
      buffer2 = buffers = null;
      return new Promise((resolve2, reject) => {
        for (const [evt, fn] of events2) {
          stream["off"](evt, fn);
        }
        try {
          const destroy = stream["destroy"];
          destroy && destroy.call(stream, err2);
          err2 = void 0;
        } catch (e) {
          err2 = e || err2;
        } finally {
          err2 != null ? reject(err2) : resolve2();
        }
      });
    }
  });
}
var MetadataVersion;
(function(MetadataVersion2) {
  MetadataVersion2[MetadataVersion2["V1"] = 0] = "V1";
  MetadataVersion2[MetadataVersion2["V2"] = 1] = "V2";
  MetadataVersion2[MetadataVersion2["V3"] = 2] = "V3";
  MetadataVersion2[MetadataVersion2["V4"] = 3] = "V4";
  MetadataVersion2[MetadataVersion2["V5"] = 4] = "V5";
})(MetadataVersion || (MetadataVersion = {}));
var UnionMode$1;
(function(UnionMode2) {
  UnionMode2[UnionMode2["Sparse"] = 0] = "Sparse";
  UnionMode2[UnionMode2["Dense"] = 1] = "Dense";
})(UnionMode$1 || (UnionMode$1 = {}));
var Precision$1;
(function(Precision2) {
  Precision2[Precision2["HALF"] = 0] = "HALF";
  Precision2[Precision2["SINGLE"] = 1] = "SINGLE";
  Precision2[Precision2["DOUBLE"] = 2] = "DOUBLE";
})(Precision$1 || (Precision$1 = {}));
var DateUnit$1;
(function(DateUnit2) {
  DateUnit2[DateUnit2["DAY"] = 0] = "DAY";
  DateUnit2[DateUnit2["MILLISECOND"] = 1] = "MILLISECOND";
})(DateUnit$1 || (DateUnit$1 = {}));
var TimeUnit$1;
(function(TimeUnit2) {
  TimeUnit2[TimeUnit2["SECOND"] = 0] = "SECOND";
  TimeUnit2[TimeUnit2["MILLISECOND"] = 1] = "MILLISECOND";
  TimeUnit2[TimeUnit2["MICROSECOND"] = 2] = "MICROSECOND";
  TimeUnit2[TimeUnit2["NANOSECOND"] = 3] = "NANOSECOND";
})(TimeUnit$1 || (TimeUnit$1 = {}));
var IntervalUnit$1;
(function(IntervalUnit2) {
  IntervalUnit2[IntervalUnit2["YEAR_MONTH"] = 0] = "YEAR_MONTH";
  IntervalUnit2[IntervalUnit2["DAY_TIME"] = 1] = "DAY_TIME";
  IntervalUnit2[IntervalUnit2["MONTH_DAY_NANO"] = 2] = "MONTH_DAY_NANO";
})(IntervalUnit$1 || (IntervalUnit$1 = {}));
const SIZEOF_SHORT$1 = 2;
const SIZEOF_INT$1 = 4;
const FILE_IDENTIFIER_LENGTH = 4;
const SIZE_PREFIX_LENGTH = 4;
const int32$1 = new Int32Array(2);
const float32$1 = new Float32Array(int32$1.buffer);
const float64$1 = new Float64Array(int32$1.buffer);
const isLittleEndian$1 = new Uint16Array(new Uint8Array([1, 0]).buffer)[0] === 1;
var Encoding;
(function(Encoding2) {
  Encoding2[Encoding2["UTF8_BYTES"] = 1] = "UTF8_BYTES";
  Encoding2[Encoding2["UTF16_STRING"] = 2] = "UTF16_STRING";
})(Encoding || (Encoding = {}));
let ByteBuffer$2 = class ByteBuffer {
  /**
   * Create a new ByteBuffer with a given array of bytes (`Uint8Array`)
   */
  constructor(bytes_) {
    this.bytes_ = bytes_;
    this.position_ = 0;
    this.text_decoder_ = new TextDecoder();
  }
  /**
   * Create and allocate a new ByteBuffer with a given size.
   */
  static allocate(byte_size) {
    return new ByteBuffer(new Uint8Array(byte_size));
  }
  clear() {
    this.position_ = 0;
  }
  /**
   * Get the underlying `Uint8Array`.
   */
  bytes() {
    return this.bytes_;
  }
  /**
   * Get the buffer's position.
   */
  position() {
    return this.position_;
  }
  /**
   * Set the buffer's position.
   */
  setPosition(position) {
    this.position_ = position;
  }
  /**
   * Get the buffer's capacity.
   */
  capacity() {
    return this.bytes_.length;
  }
  readInt8(offset2) {
    return this.readUint8(offset2) << 24 >> 24;
  }
  readUint8(offset2) {
    return this.bytes_[offset2];
  }
  readInt16(offset2) {
    return this.readUint16(offset2) << 16 >> 16;
  }
  readUint16(offset2) {
    return this.bytes_[offset2] | this.bytes_[offset2 + 1] << 8;
  }
  readInt32(offset2) {
    return this.bytes_[offset2] | this.bytes_[offset2 + 1] << 8 | this.bytes_[offset2 + 2] << 16 | this.bytes_[offset2 + 3] << 24;
  }
  readUint32(offset2) {
    return this.readInt32(offset2) >>> 0;
  }
  readInt64(offset2) {
    return BigInt.asIntN(64, BigInt(this.readUint32(offset2)) + (BigInt(this.readUint32(offset2 + 4)) << BigInt(32)));
  }
  readUint64(offset2) {
    return BigInt.asUintN(64, BigInt(this.readUint32(offset2)) + (BigInt(this.readUint32(offset2 + 4)) << BigInt(32)));
  }
  readFloat32(offset2) {
    int32$1[0] = this.readInt32(offset2);
    return float32$1[0];
  }
  readFloat64(offset2) {
    int32$1[isLittleEndian$1 ? 0 : 1] = this.readInt32(offset2);
    int32$1[isLittleEndian$1 ? 1 : 0] = this.readInt32(offset2 + 4);
    return float64$1[0];
  }
  writeInt8(offset2, value2) {
    this.bytes_[offset2] = value2;
  }
  writeUint8(offset2, value2) {
    this.bytes_[offset2] = value2;
  }
  writeInt16(offset2, value2) {
    this.bytes_[offset2] = value2;
    this.bytes_[offset2 + 1] = value2 >> 8;
  }
  writeUint16(offset2, value2) {
    this.bytes_[offset2] = value2;
    this.bytes_[offset2 + 1] = value2 >> 8;
  }
  writeInt32(offset2, value2) {
    this.bytes_[offset2] = value2;
    this.bytes_[offset2 + 1] = value2 >> 8;
    this.bytes_[offset2 + 2] = value2 >> 16;
    this.bytes_[offset2 + 3] = value2 >> 24;
  }
  writeUint32(offset2, value2) {
    this.bytes_[offset2] = value2;
    this.bytes_[offset2 + 1] = value2 >> 8;
    this.bytes_[offset2 + 2] = value2 >> 16;
    this.bytes_[offset2 + 3] = value2 >> 24;
  }
  writeInt64(offset2, value2) {
    this.writeInt32(offset2, Number(BigInt.asIntN(32, value2)));
    this.writeInt32(offset2 + 4, Number(BigInt.asIntN(32, value2 >> BigInt(32))));
  }
  writeUint64(offset2, value2) {
    this.writeUint32(offset2, Number(BigInt.asUintN(32, value2)));
    this.writeUint32(offset2 + 4, Number(BigInt.asUintN(32, value2 >> BigInt(32))));
  }
  writeFloat32(offset2, value2) {
    float32$1[0] = value2;
    this.writeInt32(offset2, int32$1[0]);
  }
  writeFloat64(offset2, value2) {
    float64$1[0] = value2;
    this.writeInt32(offset2, int32$1[isLittleEndian$1 ? 0 : 1]);
    this.writeInt32(offset2 + 4, int32$1[isLittleEndian$1 ? 1 : 0]);
  }
  /**
   * Return the file identifier.   Behavior is undefined for FlatBuffers whose
   * schema does not include a file_identifier (likely points at padding or the
   * start of a the root vtable).
   */
  getBufferIdentifier() {
    if (this.bytes_.length < this.position_ + SIZEOF_INT$1 + FILE_IDENTIFIER_LENGTH) {
      throw new Error("FlatBuffers: ByteBuffer is too short to contain an identifier.");
    }
    let result2 = "";
    for (let i = 0; i < FILE_IDENTIFIER_LENGTH; i++) {
      result2 += String.fromCharCode(this.readInt8(this.position_ + SIZEOF_INT$1 + i));
    }
    return result2;
  }
  /**
   * Look up a field in the vtable, return an offset into the object, or 0 if the
   * field is not present.
   */
  __offset(bb_pos, vtable_offset) {
    const vtable = bb_pos - this.readInt32(bb_pos);
    return vtable_offset < this.readInt16(vtable) ? this.readInt16(vtable + vtable_offset) : 0;
  }
  /**
   * Initialize any Table-derived type to point to the union at the given offset.
   */
  __union(t2, offset2) {
    t2.bb_pos = offset2 + this.readInt32(offset2);
    t2.bb = this;
    return t2;
  }
  /**
   * Create a JavaScript string from UTF-8 data stored inside the FlatBuffer.
   * This allocates a new string and converts to wide chars upon each access.
   *
   * To avoid the conversion to string, pass Encoding.UTF8_BYTES as the
   * "optionalEncoding" argument. This is useful for avoiding conversion when
   * the data will just be packaged back up in another FlatBuffer later on.
   *
   * @param offset
   * @param opt_encoding Defaults to UTF16_STRING
   */
  __string(offset2, opt_encoding) {
    offset2 += this.readInt32(offset2);
    const length2 = this.readInt32(offset2);
    offset2 += SIZEOF_INT$1;
    const utf8bytes = this.bytes_.subarray(offset2, offset2 + length2);
    if (opt_encoding === Encoding.UTF8_BYTES)
      return utf8bytes;
    else
      return this.text_decoder_.decode(utf8bytes);
  }
  /**
   * Handle unions that can contain string as its member, if a Table-derived type then initialize it,
   * if a string then return a new one
   *
   * WARNING: strings are immutable in JS so we can't change the string that the user gave us, this
   * makes the behaviour of __union_with_string different compared to __union
   */
  __union_with_string(o, offset2) {
    if (typeof o === "string") {
      return this.__string(offset2);
    }
    return this.__union(o, offset2);
  }
  /**
   * Retrieve the relative offset stored at "offset"
   */
  __indirect(offset2) {
    return offset2 + this.readInt32(offset2);
  }
  /**
   * Get the start of data of a vector whose offset is stored at "offset" in this object.
   */
  __vector(offset2) {
    return offset2 + this.readInt32(offset2) + SIZEOF_INT$1;
  }
  /**
   * Get the length of a vector whose offset is stored at "offset" in this object.
   */
  __vector_len(offset2) {
    return this.readInt32(offset2 + this.readInt32(offset2));
  }
  __has_identifier(ident) {
    if (ident.length != FILE_IDENTIFIER_LENGTH) {
      throw new Error("FlatBuffers: file identifier must be length " + FILE_IDENTIFIER_LENGTH);
    }
    for (let i = 0; i < FILE_IDENTIFIER_LENGTH; i++) {
      if (ident.charCodeAt(i) != this.readInt8(this.position() + SIZEOF_INT$1 + i)) {
        return false;
      }
    }
    return true;
  }
  /**
   * A helper function for generating list for obj api
   */
  createScalarList(listAccessor, listLength) {
    const ret = [];
    for (let i = 0; i < listLength; ++i) {
      const val = listAccessor(i);
      if (val !== null) {
        ret.push(val);
      }
    }
    return ret;
  }
  /**
   * A helper function for generating list for obj api
   * @param listAccessor function that accepts an index and return data at that index
   * @param listLength listLength
   * @param res result list
   */
  createObjList(listAccessor, listLength) {
    const ret = [];
    for (let i = 0; i < listLength; ++i) {
      const val = listAccessor(i);
      if (val !== null) {
        ret.push(val.unpack());
      }
    }
    return ret;
  }
};
let Builder$3 = class Builder {
  /**
   * Create a FlatBufferBuilder.
   */
  constructor(opt_initial_size) {
    this.minalign = 1;
    this.vtable = null;
    this.vtable_in_use = 0;
    this.isNested = false;
    this.object_start = 0;
    this.vtables = [];
    this.vector_num_elems = 0;
    this.force_defaults = false;
    this.string_maps = null;
    this.text_encoder = new TextEncoder();
    let initial_size;
    if (!opt_initial_size) {
      initial_size = 1024;
    } else {
      initial_size = opt_initial_size;
    }
    this.bb = ByteBuffer$2.allocate(initial_size);
    this.space = initial_size;
  }
  clear() {
    this.bb.clear();
    this.space = this.bb.capacity();
    this.minalign = 1;
    this.vtable = null;
    this.vtable_in_use = 0;
    this.isNested = false;
    this.object_start = 0;
    this.vtables = [];
    this.vector_num_elems = 0;
    this.force_defaults = false;
    this.string_maps = null;
  }
  /**
   * In order to save space, fields that are set to their default value
   * don't get serialized into the buffer. Forcing defaults provides a
   * way to manually disable this optimization.
   *
   * @param forceDefaults true always serializes default values
   */
  forceDefaults(forceDefaults) {
    this.force_defaults = forceDefaults;
  }
  /**
   * Get the ByteBuffer representing the FlatBuffer. Only call this after you've
   * called finish(). The actual data starts at the ByteBuffer's current position,
   * not necessarily at 0.
   */
  dataBuffer() {
    return this.bb;
  }
  /**
   * Get the bytes representing the FlatBuffer. Only call this after you've
   * called finish().
   */
  asUint8Array() {
    return this.bb.bytes().subarray(this.bb.position(), this.bb.position() + this.offset());
  }
  /**
   * Prepare to write an element of `size` after `additional_bytes` have been
   * written, e.g. if you write a string, you need to align such the int length
   * field is aligned to 4 bytes, and the string data follows it directly. If all
   * you need to do is alignment, `additional_bytes` will be 0.
   *
   * @param size This is the of the new element to write
   * @param additional_bytes The padding size
   */
  prep(size, additional_bytes) {
    if (size > this.minalign) {
      this.minalign = size;
    }
    const align_size = ~(this.bb.capacity() - this.space + additional_bytes) + 1 & size - 1;
    while (this.space < align_size + size + additional_bytes) {
      const old_buf_size = this.bb.capacity();
      this.bb = Builder.growByteBuffer(this.bb);
      this.space += this.bb.capacity() - old_buf_size;
    }
    this.pad(align_size);
  }
  pad(byte_size) {
    for (let i = 0; i < byte_size; i++) {
      this.bb.writeInt8(--this.space, 0);
    }
  }
  writeInt8(value2) {
    this.bb.writeInt8(this.space -= 1, value2);
  }
  writeInt16(value2) {
    this.bb.writeInt16(this.space -= 2, value2);
  }
  writeInt32(value2) {
    this.bb.writeInt32(this.space -= 4, value2);
  }
  writeInt64(value2) {
    this.bb.writeInt64(this.space -= 8, value2);
  }
  writeFloat32(value2) {
    this.bb.writeFloat32(this.space -= 4, value2);
  }
  writeFloat64(value2) {
    this.bb.writeFloat64(this.space -= 8, value2);
  }
  /**
   * Add an `int8` to the buffer, properly aligned, and grows the buffer (if necessary).
   * @param value The `int8` to add the buffer.
   */
  addInt8(value2) {
    this.prep(1, 0);
    this.writeInt8(value2);
  }
  /**
   * Add an `int16` to the buffer, properly aligned, and grows the buffer (if necessary).
   * @param value The `int16` to add the buffer.
   */
  addInt16(value2) {
    this.prep(2, 0);
    this.writeInt16(value2);
  }
  /**
   * Add an `int32` to the buffer, properly aligned, and grows the buffer (if necessary).
   * @param value The `int32` to add the buffer.
   */
  addInt32(value2) {
    this.prep(4, 0);
    this.writeInt32(value2);
  }
  /**
   * Add an `int64` to the buffer, properly aligned, and grows the buffer (if necessary).
   * @param value The `int64` to add the buffer.
   */
  addInt64(value2) {
    this.prep(8, 0);
    this.writeInt64(value2);
  }
  /**
   * Add a `float32` to the buffer, properly aligned, and grows the buffer (if necessary).
   * @param value The `float32` to add the buffer.
   */
  addFloat32(value2) {
    this.prep(4, 0);
    this.writeFloat32(value2);
  }
  /**
   * Add a `float64` to the buffer, properly aligned, and grows the buffer (if necessary).
   * @param value The `float64` to add the buffer.
   */
  addFloat64(value2) {
    this.prep(8, 0);
    this.writeFloat64(value2);
  }
  addFieldInt8(voffset, value2, defaultValue) {
    if (this.force_defaults || value2 != defaultValue) {
      this.addInt8(value2);
      this.slot(voffset);
    }
  }
  addFieldInt16(voffset, value2, defaultValue) {
    if (this.force_defaults || value2 != defaultValue) {
      this.addInt16(value2);
      this.slot(voffset);
    }
  }
  addFieldInt32(voffset, value2, defaultValue) {
    if (this.force_defaults || value2 != defaultValue) {
      this.addInt32(value2);
      this.slot(voffset);
    }
  }
  addFieldInt64(voffset, value2, defaultValue) {
    if (this.force_defaults || value2 !== defaultValue) {
      this.addInt64(value2);
      this.slot(voffset);
    }
  }
  addFieldFloat32(voffset, value2, defaultValue) {
    if (this.force_defaults || value2 != defaultValue) {
      this.addFloat32(value2);
      this.slot(voffset);
    }
  }
  addFieldFloat64(voffset, value2, defaultValue) {
    if (this.force_defaults || value2 != defaultValue) {
      this.addFloat64(value2);
      this.slot(voffset);
    }
  }
  addFieldOffset(voffset, value2, defaultValue) {
    if (this.force_defaults || value2 != defaultValue) {
      this.addOffset(value2);
      this.slot(voffset);
    }
  }
  /**
   * Structs are stored inline, so nothing additional is being added. `d` is always 0.
   */
  addFieldStruct(voffset, value2, defaultValue) {
    if (value2 != defaultValue) {
      this.nested(value2);
      this.slot(voffset);
    }
  }
  /**
   * Structures are always stored inline, they need to be created right
   * where they're used.  You'll get this assertion failure if you
   * created it elsewhere.
   */
  nested(obj) {
    if (obj != this.offset()) {
      throw new TypeError("FlatBuffers: struct must be serialized inline.");
    }
  }
  /**
   * Should not be creating any other object, string or vector
   * while an object is being constructed
   */
  notNested() {
    if (this.isNested) {
      throw new TypeError("FlatBuffers: object serialization must not be nested.");
    }
  }
  /**
   * Set the current vtable at `voffset` to the current location in the buffer.
   */
  slot(voffset) {
    if (this.vtable !== null)
      this.vtable[voffset] = this.offset();
  }
  /**
   * @returns Offset relative to the end of the buffer.
   */
  offset() {
    return this.bb.capacity() - this.space;
  }
  /**
   * Doubles the size of the backing ByteBuffer and copies the old data towards
   * the end of the new buffer (since we build the buffer backwards).
   *
   * @param bb The current buffer with the existing data
   * @returns A new byte buffer with the old data copied
   * to it. The data is located at the end of the buffer.
   *
   * uint8Array.set() formally takes {Array<number>|ArrayBufferView}, so to pass
   * it a uint8Array we need to suppress the type check:
   * @suppress {checkTypes}
   */
  static growByteBuffer(bb) {
    const old_buf_size = bb.capacity();
    if (old_buf_size & 3221225472) {
      throw new Error("FlatBuffers: cannot grow buffer beyond 2 gigabytes.");
    }
    const new_buf_size = old_buf_size << 1;
    const nbb = ByteBuffer$2.allocate(new_buf_size);
    nbb.setPosition(new_buf_size - old_buf_size);
    nbb.bytes().set(bb.bytes(), new_buf_size - old_buf_size);
    return nbb;
  }
  /**
   * Adds on offset, relative to where it will be written.
   *
   * @param offset The offset to add.
   */
  addOffset(offset2) {
    this.prep(SIZEOF_INT$1, 0);
    this.writeInt32(this.offset() - offset2 + SIZEOF_INT$1);
  }
  /**
   * Start encoding a new object in the buffer.  Users will not usually need to
   * call this directly. The FlatBuffers compiler will generate helper methods
   * that call this method internally.
   */
  startObject(numfields) {
    this.notNested();
    if (this.vtable == null) {
      this.vtable = [];
    }
    this.vtable_in_use = numfields;
    for (let i = 0; i < numfields; i++) {
      this.vtable[i] = 0;
    }
    this.isNested = true;
    this.object_start = this.offset();
  }
  /**
   * Finish off writing the object that is under construction.
   *
   * @returns The offset to the object inside `dataBuffer`
   */
  endObject() {
    if (this.vtable == null || !this.isNested) {
      throw new Error("FlatBuffers: endObject called without startObject");
    }
    this.addInt32(0);
    const vtableloc = this.offset();
    let i = this.vtable_in_use - 1;
    for (; i >= 0 && this.vtable[i] == 0; i--) {
    }
    const trimmed_size = i + 1;
    for (; i >= 0; i--) {
      this.addInt16(this.vtable[i] != 0 ? vtableloc - this.vtable[i] : 0);
    }
    const standard_fields = 2;
    this.addInt16(vtableloc - this.object_start);
    const len = (trimmed_size + standard_fields) * SIZEOF_SHORT$1;
    this.addInt16(len);
    let existing_vtable = 0;
    const vt1 = this.space;
    outer_loop: for (i = 0; i < this.vtables.length; i++) {
      const vt2 = this.bb.capacity() - this.vtables[i];
      if (len == this.bb.readInt16(vt2)) {
        for (let j = SIZEOF_SHORT$1; j < len; j += SIZEOF_SHORT$1) {
          if (this.bb.readInt16(vt1 + j) != this.bb.readInt16(vt2 + j)) {
            continue outer_loop;
          }
        }
        existing_vtable = this.vtables[i];
        break;
      }
    }
    if (existing_vtable) {
      this.space = this.bb.capacity() - vtableloc;
      this.bb.writeInt32(this.space, existing_vtable - vtableloc);
    } else {
      this.vtables.push(this.offset());
      this.bb.writeInt32(this.bb.capacity() - vtableloc, this.offset() - vtableloc);
    }
    this.isNested = false;
    return vtableloc;
  }
  /**
   * Finalize a buffer, poiting to the given `root_table`.
   */
  finish(root_table, opt_file_identifier, opt_size_prefix) {
    const size_prefix = opt_size_prefix ? SIZE_PREFIX_LENGTH : 0;
    if (opt_file_identifier) {
      const file_identifier = opt_file_identifier;
      this.prep(this.minalign, SIZEOF_INT$1 + FILE_IDENTIFIER_LENGTH + size_prefix);
      if (file_identifier.length != FILE_IDENTIFIER_LENGTH) {
        throw new TypeError("FlatBuffers: file identifier must be length " + FILE_IDENTIFIER_LENGTH);
      }
      for (let i = FILE_IDENTIFIER_LENGTH - 1; i >= 0; i--) {
        this.writeInt8(file_identifier.charCodeAt(i));
      }
    }
    this.prep(this.minalign, SIZEOF_INT$1 + size_prefix);
    this.addOffset(root_table);
    if (size_prefix) {
      this.addInt32(this.bb.capacity() - this.space);
    }
    this.bb.setPosition(this.space);
  }
  /**
   * Finalize a size prefixed buffer, pointing to the given `root_table`.
   */
  finishSizePrefixed(root_table, opt_file_identifier) {
    this.finish(root_table, opt_file_identifier, true);
  }
  /**
   * This checks a required field has been set in a given table that has
   * just been constructed.
   */
  requiredField(table2, field2) {
    const table_start = this.bb.capacity() - table2;
    const vtable_start = table_start - this.bb.readInt32(table_start);
    const ok = field2 < this.bb.readInt16(vtable_start) && this.bb.readInt16(vtable_start + field2) != 0;
    if (!ok) {
      throw new TypeError("FlatBuffers: field " + field2 + " must be set");
    }
  }
  /**
   * Start a new array/vector of objects.  Users usually will not call
   * this directly. The FlatBuffers compiler will create a start/end
   * method for vector types in generated code.
   *
   * @param elem_size The size of each element in the array
   * @param num_elems The number of elements in the array
   * @param alignment The alignment of the array
   */
  startVector(elem_size, num_elems, alignment) {
    this.notNested();
    this.vector_num_elems = num_elems;
    this.prep(SIZEOF_INT$1, elem_size * num_elems);
    this.prep(alignment, elem_size * num_elems);
  }
  /**
   * Finish off the creation of an array and all its elements. The array must be
   * created with `startVector`.
   *
   * @returns The offset at which the newly created array
   * starts.
   */
  endVector() {
    this.writeInt32(this.vector_num_elems);
    return this.offset();
  }
  /**
   * Encode the string `s` in the buffer using UTF-8. If the string passed has
   * already been seen, we return the offset of the already written string
   *
   * @param s The string to encode
   * @return The offset in the buffer where the encoded string starts
   */
  createSharedString(s) {
    if (!s) {
      return 0;
    }
    if (!this.string_maps) {
      this.string_maps = /* @__PURE__ */ new Map();
    }
    if (this.string_maps.has(s)) {
      return this.string_maps.get(s);
    }
    const offset2 = this.createString(s);
    this.string_maps.set(s, offset2);
    return offset2;
  }
  /**
   * Encode the string `s` in the buffer using UTF-8. If a Uint8Array is passed
   * instead of a string, it is assumed to contain valid UTF-8 encoded data.
   *
   * @param s The string to encode
   * @return The offset in the buffer where the encoded string starts
   */
  createString(s) {
    if (s === null || s === void 0) {
      return 0;
    }
    let utf82;
    if (s instanceof Uint8Array) {
      utf82 = s;
    } else {
      utf82 = this.text_encoder.encode(s);
    }
    this.addInt8(0);
    this.startVector(1, utf82.length, 1);
    this.bb.setPosition(this.space -= utf82.length);
    this.bb.bytes().set(utf82, this.space);
    return this.endVector();
  }
  /**
   * Create a byte vector.
   *
   * @param v The bytes to add
   * @returns The offset in the buffer where the byte vector starts
   */
  createByteVector(v) {
    if (v === null || v === void 0) {
      return 0;
    }
    this.startVector(1, v.length, 1);
    this.bb.setPosition(this.space -= v.length);
    this.bb.bytes().set(v, this.space);
    return this.endVector();
  }
  /**
   * A helper function to pack an object
   *
   * @returns offset of obj
   */
  createObjectOffset(obj) {
    if (obj === null) {
      return 0;
    }
    if (typeof obj === "string") {
      return this.createString(obj);
    } else {
      return obj.pack(this);
    }
  }
  /**
   * A helper function to pack a list of object
   *
   * @returns list of offsets of each non null object
   */
  createObjectOffsetList(list2) {
    const ret = [];
    for (let i = 0; i < list2.length; ++i) {
      const val = list2[i];
      if (val !== null) {
        ret.push(this.createObjectOffset(val));
      } else {
        throw new TypeError("FlatBuffers: Argument for createObjectOffsetList cannot contain null.");
      }
    }
    return ret;
  }
  createStructOffsetList(list2, startFunc) {
    startFunc(this, list2.length);
    this.createObjectOffsetList(list2.slice().reverse());
    return this.endVector();
  }
};
var BodyCompressionMethod;
(function(BodyCompressionMethod2) {
  BodyCompressionMethod2[BodyCompressionMethod2["BUFFER"] = 0] = "BUFFER";
})(BodyCompressionMethod || (BodyCompressionMethod = {}));
var CompressionType;
(function(CompressionType2) {
  CompressionType2[CompressionType2["LZ4_FRAME"] = 0] = "LZ4_FRAME";
  CompressionType2[CompressionType2["ZSTD"] = 1] = "ZSTD";
})(CompressionType || (CompressionType = {}));
let BodyCompression$1 = class BodyCompression {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsBodyCompression(bb, obj) {
    return (obj || new BodyCompression()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsBodyCompression(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new BodyCompression()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  /**
   * Compressor library.
   * For LZ4_FRAME, each compressed buffer must consist of a single frame.
   */
  codec() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt8(this.bb_pos + offset2) : CompressionType.LZ4_FRAME;
  }
  /**
   * Indicates the way the record batch body was compressed
   */
  method() {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? this.bb.readInt8(this.bb_pos + offset2) : BodyCompressionMethod.BUFFER;
  }
  static startBodyCompression(builder2) {
    builder2.startObject(2);
  }
  static addCodec(builder2, codec) {
    builder2.addFieldInt8(0, codec, CompressionType.LZ4_FRAME);
  }
  static addMethod(builder2, method) {
    builder2.addFieldInt8(1, method, BodyCompressionMethod.BUFFER);
  }
  static endBodyCompression(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createBodyCompression(builder2, codec, method) {
    BodyCompression.startBodyCompression(builder2);
    BodyCompression.addCodec(builder2, codec);
    BodyCompression.addMethod(builder2, method);
    return BodyCompression.endBodyCompression(builder2);
  }
};
let Buffer$1 = class Buffer {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  /**
   * The relative offset into the shared memory page where the bytes for this
   * buffer starts
   */
  offset() {
    return this.bb.readInt64(this.bb_pos);
  }
  /**
   * The absolute length (in bytes) of the memory buffer. The memory is found
   * from offset (inclusive) to offset + length (non-inclusive). When building
   * messages using the encapsulated IPC message, padding bytes may be written
   * after a buffer, but such padding bytes do not need to be accounted for in
   * the size here.
   */
  length() {
    return this.bb.readInt64(this.bb_pos + 8);
  }
  static sizeOf() {
    return 16;
  }
  static createBuffer(builder2, offset2, length2) {
    builder2.prep(8, 16);
    builder2.writeInt64(BigInt(length2 !== null && length2 !== void 0 ? length2 : 0));
    builder2.writeInt64(BigInt(offset2 !== null && offset2 !== void 0 ? offset2 : 0));
    return builder2.offset();
  }
};
let FieldNode$1 = class FieldNode {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  /**
   * The number of value slots in the Arrow array at this level of a nested
   * tree
   */
  length() {
    return this.bb.readInt64(this.bb_pos);
  }
  /**
   * The number of observed nulls. Fields with null_count == 0 may choose not
   * to write their physical validity bitmap out as a materialized buffer,
   * instead setting the length of the bitmap buffer to 0.
   */
  nullCount() {
    return this.bb.readInt64(this.bb_pos + 8);
  }
  static sizeOf() {
    return 16;
  }
  static createFieldNode(builder2, length2, null_count) {
    builder2.prep(8, 16);
    builder2.writeInt64(BigInt(null_count !== null && null_count !== void 0 ? null_count : 0));
    builder2.writeInt64(BigInt(length2 !== null && length2 !== void 0 ? length2 : 0));
    return builder2.offset();
  }
};
let RecordBatch$2 = class RecordBatch {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsRecordBatch(bb, obj) {
    return (obj || new RecordBatch()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsRecordBatch(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new RecordBatch()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  /**
   * number of records / rows. The arrays in the batch should all have this
   * length
   */
  length() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt64(this.bb_pos + offset2) : BigInt("0");
  }
  /**
   * Nodes correspond to the pre-ordered flattened logical schema
   */
  nodes(index, obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? (obj || new FieldNode$1()).__init(this.bb.__vector(this.bb_pos + offset2) + index * 16, this.bb) : null;
  }
  nodesLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  /**
   * Buffers correspond to the pre-ordered flattened buffer tree
   *
   * The number of buffers appended to this list depends on the schema. For
   * example, most primitive arrays will have 2 buffers, 1 for the validity
   * bitmap and 1 for the values. For struct arrays, there will only be a
   * single buffer for the validity (nulls) bitmap
   */
  buffers(index, obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? (obj || new Buffer$1()).__init(this.bb.__vector(this.bb_pos + offset2) + index * 16, this.bb) : null;
  }
  buffersLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  /**
   * Optional compression of the message body
   */
  compression(obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 10);
    return offset2 ? (obj || new BodyCompression$1()).__init(this.bb.__indirect(this.bb_pos + offset2), this.bb) : null;
  }
  static startRecordBatch(builder2) {
    builder2.startObject(4);
  }
  static addLength(builder2, length2) {
    builder2.addFieldInt64(0, length2, BigInt("0"));
  }
  static addNodes(builder2, nodesOffset) {
    builder2.addFieldOffset(1, nodesOffset, 0);
  }
  static startNodesVector(builder2, numElems) {
    builder2.startVector(16, numElems, 8);
  }
  static addBuffers(builder2, buffersOffset) {
    builder2.addFieldOffset(2, buffersOffset, 0);
  }
  static startBuffersVector(builder2, numElems) {
    builder2.startVector(16, numElems, 8);
  }
  static addCompression(builder2, compressionOffset) {
    builder2.addFieldOffset(3, compressionOffset, 0);
  }
  static endRecordBatch(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
};
let DictionaryBatch$2 = class DictionaryBatch {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsDictionaryBatch(bb, obj) {
    return (obj || new DictionaryBatch()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsDictionaryBatch(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new DictionaryBatch()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  id() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt64(this.bb_pos + offset2) : BigInt("0");
  }
  data(obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? (obj || new RecordBatch$2()).__init(this.bb.__indirect(this.bb_pos + offset2), this.bb) : null;
  }
  /**
   * If isDelta is true the values in the dictionary are to be appended to a
   * dictionary with the indicated id. If isDelta is false this dictionary
   * should replace the existing dictionary.
   */
  isDelta() {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? !!this.bb.readInt8(this.bb_pos + offset2) : false;
  }
  static startDictionaryBatch(builder2) {
    builder2.startObject(3);
  }
  static addId(builder2, id) {
    builder2.addFieldInt64(0, id, BigInt("0"));
  }
  static addData(builder2, dataOffset) {
    builder2.addFieldOffset(1, dataOffset, 0);
  }
  static addIsDelta(builder2, isDelta) {
    builder2.addFieldInt8(2, +isDelta, 0);
  }
  static endDictionaryBatch(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
};
var Endianness$1;
(function(Endianness2) {
  Endianness2[Endianness2["Little"] = 0] = "Little";
  Endianness2[Endianness2["Big"] = 1] = "Big";
})(Endianness$1 || (Endianness$1 = {}));
var DictionaryKind;
(function(DictionaryKind2) {
  DictionaryKind2[DictionaryKind2["DenseArray"] = 0] = "DenseArray";
})(DictionaryKind || (DictionaryKind = {}));
class Int {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsInt(bb, obj) {
    return (obj || new Int()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsInt(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Int()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  bitWidth() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt32(this.bb_pos + offset2) : 0;
  }
  isSigned() {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? !!this.bb.readInt8(this.bb_pos + offset2) : false;
  }
  static startInt(builder2) {
    builder2.startObject(2);
  }
  static addBitWidth(builder2, bitWidth) {
    builder2.addFieldInt32(0, bitWidth, 0);
  }
  static addIsSigned(builder2, isSigned) {
    builder2.addFieldInt8(1, +isSigned, 0);
  }
  static endInt(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createInt(builder2, bitWidth, isSigned) {
    Int.startInt(builder2);
    Int.addBitWidth(builder2, bitWidth);
    Int.addIsSigned(builder2, isSigned);
    return Int.endInt(builder2);
  }
}
class DictionaryEncoding {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsDictionaryEncoding(bb, obj) {
    return (obj || new DictionaryEncoding()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsDictionaryEncoding(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new DictionaryEncoding()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  /**
   * The known dictionary id in the application where this data is used. In
   * the file or streaming formats, the dictionary ids are found in the
   * DictionaryBatch messages
   */
  id() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt64(this.bb_pos + offset2) : BigInt("0");
  }
  /**
   * The dictionary indices are constrained to be non-negative integers. If
   * this field is null, the indices must be signed int32. To maximize
   * cross-language compatibility and performance, implementations are
   * recommended to prefer signed integer types over unsigned integer types
   * and to avoid uint64 indices unless they are required by an application.
   */
  indexType(obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? (obj || new Int()).__init(this.bb.__indirect(this.bb_pos + offset2), this.bb) : null;
  }
  /**
   * By default, dictionaries are not ordered, or the order does not have
   * semantic meaning. In some statistical, applications, dictionary-encoding
   * is used to represent ordered categorical data, and we provide a way to
   * preserve that metadata here
   */
  isOrdered() {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? !!this.bb.readInt8(this.bb_pos + offset2) : false;
  }
  dictionaryKind() {
    const offset2 = this.bb.__offset(this.bb_pos, 10);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : DictionaryKind.DenseArray;
  }
  static startDictionaryEncoding(builder2) {
    builder2.startObject(4);
  }
  static addId(builder2, id) {
    builder2.addFieldInt64(0, id, BigInt("0"));
  }
  static addIndexType(builder2, indexTypeOffset) {
    builder2.addFieldOffset(1, indexTypeOffset, 0);
  }
  static addIsOrdered(builder2, isOrdered) {
    builder2.addFieldInt8(2, +isOrdered, 0);
  }
  static addDictionaryKind(builder2, dictionaryKind) {
    builder2.addFieldInt16(3, dictionaryKind, DictionaryKind.DenseArray);
  }
  static endDictionaryEncoding(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
}
class KeyValue {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsKeyValue(bb, obj) {
    return (obj || new KeyValue()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsKeyValue(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new KeyValue()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  key(optionalEncoding) {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.__string(this.bb_pos + offset2, optionalEncoding) : null;
  }
  value(optionalEncoding) {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? this.bb.__string(this.bb_pos + offset2, optionalEncoding) : null;
  }
  static startKeyValue(builder2) {
    builder2.startObject(2);
  }
  static addKey(builder2, keyOffset) {
    builder2.addFieldOffset(0, keyOffset, 0);
  }
  static addValue(builder2, valueOffset) {
    builder2.addFieldOffset(1, valueOffset, 0);
  }
  static endKeyValue(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createKeyValue(builder2, keyOffset, valueOffset) {
    KeyValue.startKeyValue(builder2);
    KeyValue.addKey(builder2, keyOffset);
    KeyValue.addValue(builder2, valueOffset);
    return KeyValue.endKeyValue(builder2);
  }
}
let Binary$1 = class Binary {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsBinary(bb, obj) {
    return (obj || new Binary()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsBinary(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Binary()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static startBinary(builder2) {
    builder2.startObject(0);
  }
  static endBinary(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createBinary(builder2) {
    Binary.startBinary(builder2);
    return Binary.endBinary(builder2);
  }
};
let Bool$1 = class Bool {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsBool(bb, obj) {
    return (obj || new Bool()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsBool(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Bool()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static startBool(builder2) {
    builder2.startObject(0);
  }
  static endBool(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createBool(builder2) {
    Bool.startBool(builder2);
    return Bool.endBool(builder2);
  }
};
let Date$1 = class Date2 {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsDate(bb, obj) {
    return (obj || new Date2()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsDate(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Date2()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  unit() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : DateUnit$1.MILLISECOND;
  }
  static startDate(builder2) {
    builder2.startObject(1);
  }
  static addUnit(builder2, unit) {
    builder2.addFieldInt16(0, unit, DateUnit$1.MILLISECOND);
  }
  static endDate(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createDate(builder2, unit) {
    Date2.startDate(builder2);
    Date2.addUnit(builder2, unit);
    return Date2.endDate(builder2);
  }
};
let Decimal$1 = class Decimal {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsDecimal(bb, obj) {
    return (obj || new Decimal()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsDecimal(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Decimal()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  /**
   * Total number of decimal digits
   */
  precision() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt32(this.bb_pos + offset2) : 0;
  }
  /**
   * Number of digits after the decimal point "."
   */
  scale() {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? this.bb.readInt32(this.bb_pos + offset2) : 0;
  }
  /**
   * Number of bits per value. The only accepted widths are 128 and 256.
   * We use bitWidth for consistency with Int::bitWidth.
   */
  bitWidth() {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? this.bb.readInt32(this.bb_pos + offset2) : 128;
  }
  static startDecimal(builder2) {
    builder2.startObject(3);
  }
  static addPrecision(builder2, precision) {
    builder2.addFieldInt32(0, precision, 0);
  }
  static addScale(builder2, scale) {
    builder2.addFieldInt32(1, scale, 0);
  }
  static addBitWidth(builder2, bitWidth) {
    builder2.addFieldInt32(2, bitWidth, 128);
  }
  static endDecimal(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createDecimal(builder2, precision, scale, bitWidth) {
    Decimal.startDecimal(builder2);
    Decimal.addPrecision(builder2, precision);
    Decimal.addScale(builder2, scale);
    Decimal.addBitWidth(builder2, bitWidth);
    return Decimal.endDecimal(builder2);
  }
};
let Duration$1 = class Duration {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsDuration(bb, obj) {
    return (obj || new Duration()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsDuration(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Duration()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  unit() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : TimeUnit$1.MILLISECOND;
  }
  static startDuration(builder2) {
    builder2.startObject(1);
  }
  static addUnit(builder2, unit) {
    builder2.addFieldInt16(0, unit, TimeUnit$1.MILLISECOND);
  }
  static endDuration(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createDuration(builder2, unit) {
    Duration.startDuration(builder2);
    Duration.addUnit(builder2, unit);
    return Duration.endDuration(builder2);
  }
};
let FixedSizeBinary$1 = class FixedSizeBinary {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsFixedSizeBinary(bb, obj) {
    return (obj || new FixedSizeBinary()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsFixedSizeBinary(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new FixedSizeBinary()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  /**
   * Number of bytes per value
   */
  byteWidth() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt32(this.bb_pos + offset2) : 0;
  }
  static startFixedSizeBinary(builder2) {
    builder2.startObject(1);
  }
  static addByteWidth(builder2, byteWidth) {
    builder2.addFieldInt32(0, byteWidth, 0);
  }
  static endFixedSizeBinary(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createFixedSizeBinary(builder2, byteWidth) {
    FixedSizeBinary.startFixedSizeBinary(builder2);
    FixedSizeBinary.addByteWidth(builder2, byteWidth);
    return FixedSizeBinary.endFixedSizeBinary(builder2);
  }
};
let FixedSizeList$1 = class FixedSizeList {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsFixedSizeList(bb, obj) {
    return (obj || new FixedSizeList()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsFixedSizeList(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new FixedSizeList()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  /**
   * Number of list items per value
   */
  listSize() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt32(this.bb_pos + offset2) : 0;
  }
  static startFixedSizeList(builder2) {
    builder2.startObject(1);
  }
  static addListSize(builder2, listSize) {
    builder2.addFieldInt32(0, listSize, 0);
  }
  static endFixedSizeList(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createFixedSizeList(builder2, listSize) {
    FixedSizeList.startFixedSizeList(builder2);
    FixedSizeList.addListSize(builder2, listSize);
    return FixedSizeList.endFixedSizeList(builder2);
  }
};
class FloatingPoint {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsFloatingPoint(bb, obj) {
    return (obj || new FloatingPoint()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsFloatingPoint(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new FloatingPoint()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  precision() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : Precision$1.HALF;
  }
  static startFloatingPoint(builder2) {
    builder2.startObject(1);
  }
  static addPrecision(builder2, precision) {
    builder2.addFieldInt16(0, precision, Precision$1.HALF);
  }
  static endFloatingPoint(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createFloatingPoint(builder2, precision) {
    FloatingPoint.startFloatingPoint(builder2);
    FloatingPoint.addPrecision(builder2, precision);
    return FloatingPoint.endFloatingPoint(builder2);
  }
}
class Interval {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsInterval(bb, obj) {
    return (obj || new Interval()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsInterval(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Interval()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  unit() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : IntervalUnit$1.YEAR_MONTH;
  }
  static startInterval(builder2) {
    builder2.startObject(1);
  }
  static addUnit(builder2, unit) {
    builder2.addFieldInt16(0, unit, IntervalUnit$1.YEAR_MONTH);
  }
  static endInterval(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createInterval(builder2, unit) {
    Interval.startInterval(builder2);
    Interval.addUnit(builder2, unit);
    return Interval.endInterval(builder2);
  }
}
let LargeBinary$1 = class LargeBinary {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsLargeBinary(bb, obj) {
    return (obj || new LargeBinary()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsLargeBinary(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new LargeBinary()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static startLargeBinary(builder2) {
    builder2.startObject(0);
  }
  static endLargeBinary(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createLargeBinary(builder2) {
    LargeBinary.startLargeBinary(builder2);
    return LargeBinary.endLargeBinary(builder2);
  }
};
let LargeUtf8$1 = class LargeUtf8 {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsLargeUtf8(bb, obj) {
    return (obj || new LargeUtf8()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsLargeUtf8(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new LargeUtf8()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static startLargeUtf8(builder2) {
    builder2.startObject(0);
  }
  static endLargeUtf8(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createLargeUtf8(builder2) {
    LargeUtf8.startLargeUtf8(builder2);
    return LargeUtf8.endLargeUtf8(builder2);
  }
};
let List$1 = class List {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsList(bb, obj) {
    return (obj || new List()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsList(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new List()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static startList(builder2) {
    builder2.startObject(0);
  }
  static endList(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createList(builder2) {
    List.startList(builder2);
    return List.endList(builder2);
  }
};
let Map$1 = class Map2 {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsMap(bb, obj) {
    return (obj || new Map2()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsMap(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Map2()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  /**
   * Set to true if the keys within each value are sorted
   */
  keysSorted() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? !!this.bb.readInt8(this.bb_pos + offset2) : false;
  }
  static startMap(builder2) {
    builder2.startObject(1);
  }
  static addKeysSorted(builder2, keysSorted) {
    builder2.addFieldInt8(0, +keysSorted, 0);
  }
  static endMap(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createMap(builder2, keysSorted) {
    Map2.startMap(builder2);
    Map2.addKeysSorted(builder2, keysSorted);
    return Map2.endMap(builder2);
  }
};
let Null$1 = class Null {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsNull(bb, obj) {
    return (obj || new Null()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsNull(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Null()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static startNull(builder2) {
    builder2.startObject(0);
  }
  static endNull(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createNull(builder2) {
    Null.startNull(builder2);
    return Null.endNull(builder2);
  }
};
class Struct_ {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsStruct_(bb, obj) {
    return (obj || new Struct_()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsStruct_(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Struct_()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static startStruct_(builder2) {
    builder2.startObject(0);
  }
  static endStruct_(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createStruct_(builder2) {
    Struct_.startStruct_(builder2);
    return Struct_.endStruct_(builder2);
  }
}
class Time {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsTime(bb, obj) {
    return (obj || new Time()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsTime(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Time()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  unit() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : TimeUnit$1.MILLISECOND;
  }
  bitWidth() {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? this.bb.readInt32(this.bb_pos + offset2) : 32;
  }
  static startTime(builder2) {
    builder2.startObject(2);
  }
  static addUnit(builder2, unit) {
    builder2.addFieldInt16(0, unit, TimeUnit$1.MILLISECOND);
  }
  static addBitWidth(builder2, bitWidth) {
    builder2.addFieldInt32(1, bitWidth, 32);
  }
  static endTime(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createTime(builder2, unit, bitWidth) {
    Time.startTime(builder2);
    Time.addUnit(builder2, unit);
    Time.addBitWidth(builder2, bitWidth);
    return Time.endTime(builder2);
  }
}
class Timestamp {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsTimestamp(bb, obj) {
    return (obj || new Timestamp()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsTimestamp(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Timestamp()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  unit() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : TimeUnit$1.SECOND;
  }
  timezone(optionalEncoding) {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? this.bb.__string(this.bb_pos + offset2, optionalEncoding) : null;
  }
  static startTimestamp(builder2) {
    builder2.startObject(2);
  }
  static addUnit(builder2, unit) {
    builder2.addFieldInt16(0, unit, TimeUnit$1.SECOND);
  }
  static addTimezone(builder2, timezoneOffset) {
    builder2.addFieldOffset(1, timezoneOffset, 0);
  }
  static endTimestamp(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createTimestamp(builder2, unit, timezoneOffset) {
    Timestamp.startTimestamp(builder2);
    Timestamp.addUnit(builder2, unit);
    Timestamp.addTimezone(builder2, timezoneOffset);
    return Timestamp.endTimestamp(builder2);
  }
}
class Union {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsUnion(bb, obj) {
    return (obj || new Union()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsUnion(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Union()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  mode() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : UnionMode$1.Sparse;
  }
  typeIds(index) {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? this.bb.readInt32(this.bb.__vector(this.bb_pos + offset2) + index * 4) : 0;
  }
  typeIdsLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  typeIdsArray() {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? new Int32Array(this.bb.bytes().buffer, this.bb.bytes().byteOffset + this.bb.__vector(this.bb_pos + offset2), this.bb.__vector_len(this.bb_pos + offset2)) : null;
  }
  static startUnion(builder2) {
    builder2.startObject(2);
  }
  static addMode(builder2, mode) {
    builder2.addFieldInt16(0, mode, UnionMode$1.Sparse);
  }
  static addTypeIds(builder2, typeIdsOffset) {
    builder2.addFieldOffset(1, typeIdsOffset, 0);
  }
  static createTypeIdsVector(builder2, data2) {
    builder2.startVector(4, data2.length, 4);
    for (let i = data2.length - 1; i >= 0; i--) {
      builder2.addInt32(data2[i]);
    }
    return builder2.endVector();
  }
  static startTypeIdsVector(builder2, numElems) {
    builder2.startVector(4, numElems, 4);
  }
  static endUnion(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createUnion(builder2, mode, typeIdsOffset) {
    Union.startUnion(builder2);
    Union.addMode(builder2, mode);
    Union.addTypeIds(builder2, typeIdsOffset);
    return Union.endUnion(builder2);
  }
}
let Utf8$1 = class Utf8 {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsUtf8(bb, obj) {
    return (obj || new Utf8()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsUtf8(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Utf8()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static startUtf8(builder2) {
    builder2.startObject(0);
  }
  static endUtf8(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static createUtf8(builder2) {
    Utf8.startUtf8(builder2);
    return Utf8.endUtf8(builder2);
  }
};
var Type$2;
(function(Type2) {
  Type2[Type2["NONE"] = 0] = "NONE";
  Type2[Type2["Null"] = 1] = "Null";
  Type2[Type2["Int"] = 2] = "Int";
  Type2[Type2["FloatingPoint"] = 3] = "FloatingPoint";
  Type2[Type2["Binary"] = 4] = "Binary";
  Type2[Type2["Utf8"] = 5] = "Utf8";
  Type2[Type2["Bool"] = 6] = "Bool";
  Type2[Type2["Decimal"] = 7] = "Decimal";
  Type2[Type2["Date"] = 8] = "Date";
  Type2[Type2["Time"] = 9] = "Time";
  Type2[Type2["Timestamp"] = 10] = "Timestamp";
  Type2[Type2["Interval"] = 11] = "Interval";
  Type2[Type2["List"] = 12] = "List";
  Type2[Type2["Struct_"] = 13] = "Struct_";
  Type2[Type2["Union"] = 14] = "Union";
  Type2[Type2["FixedSizeBinary"] = 15] = "FixedSizeBinary";
  Type2[Type2["FixedSizeList"] = 16] = "FixedSizeList";
  Type2[Type2["Map"] = 17] = "Map";
  Type2[Type2["Duration"] = 18] = "Duration";
  Type2[Type2["LargeBinary"] = 19] = "LargeBinary";
  Type2[Type2["LargeUtf8"] = 20] = "LargeUtf8";
  Type2[Type2["LargeList"] = 21] = "LargeList";
  Type2[Type2["RunEndEncoded"] = 22] = "RunEndEncoded";
})(Type$2 || (Type$2 = {}));
let Field$1 = class Field {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsField(bb, obj) {
    return (obj || new Field()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsField(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Field()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  name(optionalEncoding) {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.__string(this.bb_pos + offset2, optionalEncoding) : null;
  }
  /**
   * Whether or not this field can contain nulls. Should be true in general.
   */
  nullable() {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? !!this.bb.readInt8(this.bb_pos + offset2) : false;
  }
  typeType() {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? this.bb.readUint8(this.bb_pos + offset2) : Type$2.NONE;
  }
  /**
   * This is the type of the decoded value if the field is dictionary encoded.
   */
  type(obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 10);
    return offset2 ? this.bb.__union(obj, this.bb_pos + offset2) : null;
  }
  /**
   * Present only if the field is dictionary encoded.
   */
  dictionary(obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 12);
    return offset2 ? (obj || new DictionaryEncoding()).__init(this.bb.__indirect(this.bb_pos + offset2), this.bb) : null;
  }
  /**
   * children apply only to nested data types like Struct, List and Union. For
   * primitive types children will have length 0.
   */
  children(index, obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 14);
    return offset2 ? (obj || new Field()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset2) + index * 4), this.bb) : null;
  }
  childrenLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 14);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  /**
   * User-defined metadata
   */
  customMetadata(index, obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 16);
    return offset2 ? (obj || new KeyValue()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset2) + index * 4), this.bb) : null;
  }
  customMetadataLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 16);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  static startField(builder2) {
    builder2.startObject(7);
  }
  static addName(builder2, nameOffset) {
    builder2.addFieldOffset(0, nameOffset, 0);
  }
  static addNullable(builder2, nullable) {
    builder2.addFieldInt8(1, +nullable, 0);
  }
  static addTypeType(builder2, typeType) {
    builder2.addFieldInt8(2, typeType, Type$2.NONE);
  }
  static addType(builder2, typeOffset) {
    builder2.addFieldOffset(3, typeOffset, 0);
  }
  static addDictionary(builder2, dictionaryOffset) {
    builder2.addFieldOffset(4, dictionaryOffset, 0);
  }
  static addChildren(builder2, childrenOffset) {
    builder2.addFieldOffset(5, childrenOffset, 0);
  }
  static createChildrenVector(builder2, data2) {
    builder2.startVector(4, data2.length, 4);
    for (let i = data2.length - 1; i >= 0; i--) {
      builder2.addOffset(data2[i]);
    }
    return builder2.endVector();
  }
  static startChildrenVector(builder2, numElems) {
    builder2.startVector(4, numElems, 4);
  }
  static addCustomMetadata(builder2, customMetadataOffset) {
    builder2.addFieldOffset(6, customMetadataOffset, 0);
  }
  static createCustomMetadataVector(builder2, data2) {
    builder2.startVector(4, data2.length, 4);
    for (let i = data2.length - 1; i >= 0; i--) {
      builder2.addOffset(data2[i]);
    }
    return builder2.endVector();
  }
  static startCustomMetadataVector(builder2, numElems) {
    builder2.startVector(4, numElems, 4);
  }
  static endField(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
};
let Schema$1 = class Schema {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsSchema(bb, obj) {
    return (obj || new Schema()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsSchema(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Schema()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  /**
   * endianness of the buffer
   * it is Little Endian by default
   * if endianness doesn't match the underlying system then the vectors need to be converted
   */
  endianness() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : Endianness$1.Little;
  }
  fields(index, obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? (obj || new Field$1()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset2) + index * 4), this.bb) : null;
  }
  fieldsLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  customMetadata(index, obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? (obj || new KeyValue()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset2) + index * 4), this.bb) : null;
  }
  customMetadataLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  /**
   * Features used in the stream/file.
   */
  features(index) {
    const offset2 = this.bb.__offset(this.bb_pos, 10);
    return offset2 ? this.bb.readInt64(this.bb.__vector(this.bb_pos + offset2) + index * 8) : BigInt(0);
  }
  featuresLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 10);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  static startSchema(builder2) {
    builder2.startObject(4);
  }
  static addEndianness(builder2, endianness) {
    builder2.addFieldInt16(0, endianness, Endianness$1.Little);
  }
  static addFields(builder2, fieldsOffset) {
    builder2.addFieldOffset(1, fieldsOffset, 0);
  }
  static createFieldsVector(builder2, data2) {
    builder2.startVector(4, data2.length, 4);
    for (let i = data2.length - 1; i >= 0; i--) {
      builder2.addOffset(data2[i]);
    }
    return builder2.endVector();
  }
  static startFieldsVector(builder2, numElems) {
    builder2.startVector(4, numElems, 4);
  }
  static addCustomMetadata(builder2, customMetadataOffset) {
    builder2.addFieldOffset(2, customMetadataOffset, 0);
  }
  static createCustomMetadataVector(builder2, data2) {
    builder2.startVector(4, data2.length, 4);
    for (let i = data2.length - 1; i >= 0; i--) {
      builder2.addOffset(data2[i]);
    }
    return builder2.endVector();
  }
  static startCustomMetadataVector(builder2, numElems) {
    builder2.startVector(4, numElems, 4);
  }
  static addFeatures(builder2, featuresOffset) {
    builder2.addFieldOffset(3, featuresOffset, 0);
  }
  static createFeaturesVector(builder2, data2) {
    builder2.startVector(8, data2.length, 8);
    for (let i = data2.length - 1; i >= 0; i--) {
      builder2.addInt64(data2[i]);
    }
    return builder2.endVector();
  }
  static startFeaturesVector(builder2, numElems) {
    builder2.startVector(8, numElems, 8);
  }
  static endSchema(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static finishSchemaBuffer(builder2, offset2) {
    builder2.finish(offset2);
  }
  static finishSizePrefixedSchemaBuffer(builder2, offset2) {
    builder2.finish(offset2, void 0, true);
  }
  static createSchema(builder2, endianness, fieldsOffset, customMetadataOffset, featuresOffset) {
    Schema.startSchema(builder2);
    Schema.addEndianness(builder2, endianness);
    Schema.addFields(builder2, fieldsOffset);
    Schema.addCustomMetadata(builder2, customMetadataOffset);
    Schema.addFeatures(builder2, featuresOffset);
    return Schema.endSchema(builder2);
  }
};
var MessageHeader$1;
(function(MessageHeader2) {
  MessageHeader2[MessageHeader2["NONE"] = 0] = "NONE";
  MessageHeader2[MessageHeader2["Schema"] = 1] = "Schema";
  MessageHeader2[MessageHeader2["DictionaryBatch"] = 2] = "DictionaryBatch";
  MessageHeader2[MessageHeader2["RecordBatch"] = 3] = "RecordBatch";
  MessageHeader2[MessageHeader2["Tensor"] = 4] = "Tensor";
  MessageHeader2[MessageHeader2["SparseTensor"] = 5] = "SparseTensor";
})(MessageHeader$1 || (MessageHeader$1 = {}));
var Type$1;
(function(Type2) {
  Type2[Type2["NONE"] = 0] = "NONE";
  Type2[Type2["Null"] = 1] = "Null";
  Type2[Type2["Int"] = 2] = "Int";
  Type2[Type2["Float"] = 3] = "Float";
  Type2[Type2["Binary"] = 4] = "Binary";
  Type2[Type2["Utf8"] = 5] = "Utf8";
  Type2[Type2["Bool"] = 6] = "Bool";
  Type2[Type2["Decimal"] = 7] = "Decimal";
  Type2[Type2["Date"] = 8] = "Date";
  Type2[Type2["Time"] = 9] = "Time";
  Type2[Type2["Timestamp"] = 10] = "Timestamp";
  Type2[Type2["Interval"] = 11] = "Interval";
  Type2[Type2["List"] = 12] = "List";
  Type2[Type2["Struct"] = 13] = "Struct";
  Type2[Type2["Union"] = 14] = "Union";
  Type2[Type2["FixedSizeBinary"] = 15] = "FixedSizeBinary";
  Type2[Type2["FixedSizeList"] = 16] = "FixedSizeList";
  Type2[Type2["Map"] = 17] = "Map";
  Type2[Type2["Duration"] = 18] = "Duration";
  Type2[Type2["LargeBinary"] = 19] = "LargeBinary";
  Type2[Type2["LargeUtf8"] = 20] = "LargeUtf8";
  Type2[Type2["Dictionary"] = -1] = "Dictionary";
  Type2[Type2["Int8"] = -2] = "Int8";
  Type2[Type2["Int16"] = -3] = "Int16";
  Type2[Type2["Int32"] = -4] = "Int32";
  Type2[Type2["Int64"] = -5] = "Int64";
  Type2[Type2["Uint8"] = -6] = "Uint8";
  Type2[Type2["Uint16"] = -7] = "Uint16";
  Type2[Type2["Uint32"] = -8] = "Uint32";
  Type2[Type2["Uint64"] = -9] = "Uint64";
  Type2[Type2["Float16"] = -10] = "Float16";
  Type2[Type2["Float32"] = -11] = "Float32";
  Type2[Type2["Float64"] = -12] = "Float64";
  Type2[Type2["DateDay"] = -13] = "DateDay";
  Type2[Type2["DateMillisecond"] = -14] = "DateMillisecond";
  Type2[Type2["TimestampSecond"] = -15] = "TimestampSecond";
  Type2[Type2["TimestampMillisecond"] = -16] = "TimestampMillisecond";
  Type2[Type2["TimestampMicrosecond"] = -17] = "TimestampMicrosecond";
  Type2[Type2["TimestampNanosecond"] = -18] = "TimestampNanosecond";
  Type2[Type2["TimeSecond"] = -19] = "TimeSecond";
  Type2[Type2["TimeMillisecond"] = -20] = "TimeMillisecond";
  Type2[Type2["TimeMicrosecond"] = -21] = "TimeMicrosecond";
  Type2[Type2["TimeNanosecond"] = -22] = "TimeNanosecond";
  Type2[Type2["DenseUnion"] = -23] = "DenseUnion";
  Type2[Type2["SparseUnion"] = -24] = "SparseUnion";
  Type2[Type2["IntervalDayTime"] = -25] = "IntervalDayTime";
  Type2[Type2["IntervalYearMonth"] = -26] = "IntervalYearMonth";
  Type2[Type2["DurationSecond"] = -27] = "DurationSecond";
  Type2[Type2["DurationMillisecond"] = -28] = "DurationMillisecond";
  Type2[Type2["DurationMicrosecond"] = -29] = "DurationMicrosecond";
  Type2[Type2["DurationNanosecond"] = -30] = "DurationNanosecond";
  Type2[Type2["IntervalMonthDayNano"] = -31] = "IntervalMonthDayNano";
})(Type$1 || (Type$1 = {}));
var BufferType;
(function(BufferType2) {
  BufferType2[BufferType2["OFFSET"] = 0] = "OFFSET";
  BufferType2[BufferType2["DATA"] = 1] = "DATA";
  BufferType2[BufferType2["VALIDITY"] = 2] = "VALIDITY";
  BufferType2[BufferType2["TYPE"] = 3] = "TYPE";
})(BufferType || (BufferType = {}));
const undf = void 0;
function valueToString(x) {
  if (x === null) {
    return "null";
  }
  if (x === undf) {
    return "undefined";
  }
  switch (typeof x) {
    case "number":
      return `${x}`;
    case "bigint":
      return `${x}`;
    case "string":
      return `"${x}"`;
  }
  if (typeof x[Symbol.toPrimitive] === "function") {
    return x[Symbol.toPrimitive]("string");
  }
  if (ArrayBuffer.isView(x)) {
    if (x instanceof BigInt64Array || x instanceof BigUint64Array) {
      return `[${[...x].map((x2) => valueToString(x2))}]`;
    }
    return `[${x}]`;
  }
  return ArrayBuffer.isView(x) ? `[${x}]` : JSON.stringify(x, (_, y) => typeof y === "bigint" ? `${y}` : y);
}
function bigIntToNumber(number) {
  if (typeof number === "bigint" && (number < Number.MIN_SAFE_INTEGER || number > Number.MAX_SAFE_INTEGER)) {
    throw new TypeError(`${number} is not safe to convert to a number.`);
  }
  return Number(number);
}
function divideBigInts(number, divisor) {
  return bigIntToNumber(number / divisor) + bigIntToNumber(number % divisor) / bigIntToNumber(divisor);
}
const isArrowBigNumSymbol = /* @__PURE__ */ Symbol.for("isArrowBigNum");
function BigNum(x, ...xs) {
  if (xs.length === 0) {
    return Object.setPrototypeOf(toArrayBufferView(this["TypedArray"], x), this.constructor.prototype);
  }
  return Object.setPrototypeOf(new this["TypedArray"](x, ...xs), this.constructor.prototype);
}
BigNum.prototype[isArrowBigNumSymbol] = true;
BigNum.prototype.toJSON = function() {
  return `"${bigNumToString(this)}"`;
};
BigNum.prototype.valueOf = function(scale) {
  return bigNumToNumber(this, scale);
};
BigNum.prototype.toString = function() {
  return bigNumToString(this);
};
BigNum.prototype[Symbol.toPrimitive] = function(hint = "default") {
  switch (hint) {
    case "number":
      return bigNumToNumber(this);
    case "string":
      return bigNumToString(this);
    case "default":
      return bigNumToBigInt(this);
  }
  return bigNumToString(this);
};
function SignedBigNum(...args) {
  return BigNum.apply(this, args);
}
function UnsignedBigNum(...args) {
  return BigNum.apply(this, args);
}
function DecimalBigNum(...args) {
  return BigNum.apply(this, args);
}
Object.setPrototypeOf(SignedBigNum.prototype, Object.create(Int32Array.prototype));
Object.setPrototypeOf(UnsignedBigNum.prototype, Object.create(Uint32Array.prototype));
Object.setPrototypeOf(DecimalBigNum.prototype, Object.create(Uint32Array.prototype));
Object.assign(SignedBigNum.prototype, BigNum.prototype, { "constructor": SignedBigNum, "signed": true, "TypedArray": Int32Array, "BigIntArray": BigInt64Array });
Object.assign(UnsignedBigNum.prototype, BigNum.prototype, { "constructor": UnsignedBigNum, "signed": false, "TypedArray": Uint32Array, "BigIntArray": BigUint64Array });
Object.assign(DecimalBigNum.prototype, BigNum.prototype, { "constructor": DecimalBigNum, "signed": true, "TypedArray": Uint32Array, "BigIntArray": BigUint64Array });
const TWO_TO_THE_64 = BigInt(4294967296) * BigInt(4294967296);
const TWO_TO_THE_64_MINUS_1 = TWO_TO_THE_64 - BigInt(1);
function bigNumToNumber(bn, scale) {
  const { buffer: buffer2, byteOffset, byteLength, "signed": signed } = bn;
  const words = new BigUint64Array(buffer2, byteOffset, byteLength / 8);
  const negative = signed && words.at(-1) & BigInt(1) << BigInt(63);
  let number = BigInt(0);
  let i = 0;
  if (negative) {
    for (const word of words) {
      number |= (word ^ TWO_TO_THE_64_MINUS_1) * (BigInt(1) << BigInt(64 * i++));
    }
    number *= BigInt(-1);
    number -= BigInt(1);
  } else {
    for (const word of words) {
      number |= word * (BigInt(1) << BigInt(64 * i++));
    }
  }
  if (typeof scale === "number" && scale > 0) {
    const denominator = BigInt("1".padEnd(scale + 1, "0"));
    const quotient = number / denominator;
    const remainder = negative ? -(number % denominator) : number % denominator;
    const integerPart = bigIntToNumber(quotient);
    const fractionPart = `${remainder}`.padStart(scale, "0");
    const sign2 = negative && integerPart === 0 ? "-" : "";
    return +`${sign2}${integerPart}.${fractionPart}`;
  }
  return bigIntToNumber(number);
}
function bigNumToString(a) {
  if (a.byteLength === 8) {
    const bigIntArray = new a["BigIntArray"](a.buffer, a.byteOffset, 1);
    return `${bigIntArray[0]}`;
  }
  if (!a["signed"]) {
    return unsignedBigNumToString(a);
  }
  let array2 = new Uint16Array(a.buffer, a.byteOffset, a.byteLength / 2);
  const highOrderWord = new Int16Array([array2.at(-1)])[0];
  if (highOrderWord >= 0) {
    return unsignedBigNumToString(a);
  }
  array2 = array2.slice();
  let carry = 1;
  for (let i = 0; i < array2.length; i++) {
    const elem = array2[i];
    const updated = ~elem + carry;
    array2[i] = updated;
    carry &= elem === 0 ? 1 : 0;
  }
  const negated = unsignedBigNumToString(array2);
  return `-${negated}`;
}
function bigNumToBigInt(a) {
  if (a.byteLength === 8) {
    const bigIntArray = new a["BigIntArray"](a.buffer, a.byteOffset, 1);
    return bigIntArray[0];
  } else {
    return bigNumToString(a);
  }
}
function unsignedBigNumToString(a) {
  let digits = "";
  const base64 = new Uint32Array(2);
  let base32 = new Uint16Array(a.buffer, a.byteOffset, a.byteLength / 2);
  const checks = new Uint32Array((base32 = new Uint16Array(base32).reverse()).buffer);
  let i = -1;
  const n = base32.length - 1;
  do {
    for (base64[0] = base32[i = 0]; i < n; ) {
      base32[i++] = base64[1] = base64[0] / 10;
      base64[0] = (base64[0] - base64[1] * 10 << 16) + base32[i];
    }
    base32[i] = base64[1] = base64[0] / 10;
    base64[0] = base64[0] - base64[1] * 10;
    digits = `${base64[0]}${digits}`;
  } while (checks[0] || checks[1] || checks[2] || checks[3]);
  return digits !== null && digits !== void 0 ? digits : `0`;
}
class BN {
  /** @nocollapse */
  static new(num, isSigned) {
    switch (isSigned) {
      case true:
        return new SignedBigNum(num);
      case false:
        return new UnsignedBigNum(num);
    }
    switch (num.constructor) {
      case Int8Array:
      case Int16Array:
      case Int32Array:
      case BigInt64Array:
        return new SignedBigNum(num);
    }
    if (num.byteLength === 16) {
      return new DecimalBigNum(num);
    }
    return new UnsignedBigNum(num);
  }
  /** @nocollapse */
  static signed(num) {
    return new SignedBigNum(num);
  }
  /** @nocollapse */
  static unsigned(num) {
    return new UnsignedBigNum(num);
  }
  /** @nocollapse */
  static decimal(num) {
    return new DecimalBigNum(num);
  }
  constructor(num, isSigned) {
    return BN.new(num, isSigned);
  }
}
var _a$3, _b, _c, _d, _e, _f, _g, _h, _j, _k, _l, _m, _o, _p, _q, _r, _s, _t, _u, _v, _w, _x;
class DataType {
  /** @nocollapse */
  static isNull(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Null;
  }
  /** @nocollapse */
  static isInt(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Int;
  }
  /** @nocollapse */
  static isFloat(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Float;
  }
  /** @nocollapse */
  static isBinary(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Binary;
  }
  /** @nocollapse */
  static isLargeBinary(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.LargeBinary;
  }
  /** @nocollapse */
  static isUtf8(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Utf8;
  }
  /** @nocollapse */
  static isLargeUtf8(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.LargeUtf8;
  }
  /** @nocollapse */
  static isBool(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Bool;
  }
  /** @nocollapse */
  static isDecimal(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Decimal;
  }
  /** @nocollapse */
  static isDate(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Date;
  }
  /** @nocollapse */
  static isTime(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Time;
  }
  /** @nocollapse */
  static isTimestamp(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Timestamp;
  }
  /** @nocollapse */
  static isInterval(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Interval;
  }
  /** @nocollapse */
  static isDuration(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Duration;
  }
  /** @nocollapse */
  static isList(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.List;
  }
  /** @nocollapse */
  static isStruct(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Struct;
  }
  /** @nocollapse */
  static isUnion(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Union;
  }
  /** @nocollapse */
  static isFixedSizeBinary(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.FixedSizeBinary;
  }
  /** @nocollapse */
  static isFixedSizeList(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.FixedSizeList;
  }
  /** @nocollapse */
  static isMap(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Map;
  }
  /** @nocollapse */
  static isDictionary(x) {
    return (x === null || x === void 0 ? void 0 : x.typeId) === Type$1.Dictionary;
  }
  /** @nocollapse */
  static isDenseUnion(x) {
    return DataType.isUnion(x) && x.mode === UnionMode$1.Dense;
  }
  /** @nocollapse */
  static isSparseUnion(x) {
    return DataType.isUnion(x) && x.mode === UnionMode$1.Sparse;
  }
  constructor(typeId) {
    this.typeId = typeId;
  }
}
_a$3 = Symbol.toStringTag;
DataType[_a$3] = ((proto) => {
  proto.children = null;
  proto.ArrayType = Array;
  proto.OffsetArrayType = Int32Array;
  return proto[Symbol.toStringTag] = "DataType";
})(DataType.prototype);
class Null2 extends DataType {
  constructor() {
    super(Type$1.Null);
  }
  toString() {
    return `Null`;
  }
}
_b = Symbol.toStringTag;
Null2[_b] = ((proto) => proto[Symbol.toStringTag] = "Null")(Null2.prototype);
class Int_ extends DataType {
  constructor(isSigned, bitWidth) {
    super(Type$1.Int);
    this.isSigned = isSigned;
    this.bitWidth = bitWidth;
  }
  get ArrayType() {
    switch (this.bitWidth) {
      case 8:
        return this.isSigned ? Int8Array : Uint8Array;
      case 16:
        return this.isSigned ? Int16Array : Uint16Array;
      case 32:
        return this.isSigned ? Int32Array : Uint32Array;
      case 64:
        return this.isSigned ? BigInt64Array : BigUint64Array;
    }
    throw new Error(`Unrecognized ${this[Symbol.toStringTag]} type`);
  }
  toString() {
    return `${this.isSigned ? `I` : `Ui`}nt${this.bitWidth}`;
  }
}
_c = Symbol.toStringTag;
Int_[_c] = ((proto) => {
  proto.isSigned = null;
  proto.bitWidth = null;
  return proto[Symbol.toStringTag] = "Int";
})(Int_.prototype);
class Int32 extends Int_ {
  constructor() {
    super(true, 32);
  }
  get ArrayType() {
    return Int32Array;
  }
}
Object.defineProperty(Int32.prototype, "ArrayType", { value: Int32Array });
class Float extends DataType {
  constructor(precision) {
    super(Type$1.Float);
    this.precision = precision;
  }
  get ArrayType() {
    switch (this.precision) {
      case Precision$1.HALF:
        return Uint16Array;
      case Precision$1.SINGLE:
        return Float32Array;
      case Precision$1.DOUBLE:
        return Float64Array;
    }
    throw new Error(`Unrecognized ${this[Symbol.toStringTag]} type`);
  }
  toString() {
    return `Float${this.precision << 5 || 16}`;
  }
}
_d = Symbol.toStringTag;
Float[_d] = ((proto) => {
  proto.precision = null;
  return proto[Symbol.toStringTag] = "Float";
})(Float.prototype);
class Binary2 extends DataType {
  constructor() {
    super(Type$1.Binary);
  }
  toString() {
    return `Binary`;
  }
}
_e = Symbol.toStringTag;
Binary2[_e] = ((proto) => {
  proto.ArrayType = Uint8Array;
  return proto[Symbol.toStringTag] = "Binary";
})(Binary2.prototype);
class LargeBinary2 extends DataType {
  constructor() {
    super(Type$1.LargeBinary);
  }
  toString() {
    return `LargeBinary`;
  }
}
_f = Symbol.toStringTag;
LargeBinary2[_f] = ((proto) => {
  proto.ArrayType = Uint8Array;
  proto.OffsetArrayType = BigInt64Array;
  return proto[Symbol.toStringTag] = "LargeBinary";
})(LargeBinary2.prototype);
class Utf82 extends DataType {
  constructor() {
    super(Type$1.Utf8);
  }
  toString() {
    return `Utf8`;
  }
}
_g = Symbol.toStringTag;
Utf82[_g] = ((proto) => {
  proto.ArrayType = Uint8Array;
  return proto[Symbol.toStringTag] = "Utf8";
})(Utf82.prototype);
class LargeUtf82 extends DataType {
  constructor() {
    super(Type$1.LargeUtf8);
  }
  toString() {
    return `LargeUtf8`;
  }
}
_h = Symbol.toStringTag;
LargeUtf82[_h] = ((proto) => {
  proto.ArrayType = Uint8Array;
  proto.OffsetArrayType = BigInt64Array;
  return proto[Symbol.toStringTag] = "LargeUtf8";
})(LargeUtf82.prototype);
class Bool2 extends DataType {
  constructor() {
    super(Type$1.Bool);
  }
  toString() {
    return `Bool`;
  }
}
_j = Symbol.toStringTag;
Bool2[_j] = ((proto) => {
  proto.ArrayType = Uint8Array;
  return proto[Symbol.toStringTag] = "Bool";
})(Bool2.prototype);
class Decimal2 extends DataType {
  constructor(scale, precision, bitWidth = 128) {
    super(Type$1.Decimal);
    this.scale = scale;
    this.precision = precision;
    this.bitWidth = bitWidth;
  }
  toString() {
    return `Decimal[${this.precision}e${this.scale > 0 ? `+` : ``}${this.scale}]`;
  }
}
_k = Symbol.toStringTag;
Decimal2[_k] = ((proto) => {
  proto.scale = null;
  proto.precision = null;
  proto.ArrayType = Uint32Array;
  return proto[Symbol.toStringTag] = "Decimal";
})(Decimal2.prototype);
class Date_ extends DataType {
  constructor(unit) {
    super(Type$1.Date);
    this.unit = unit;
  }
  toString() {
    return `Date${(this.unit + 1) * 32}<${DateUnit$1[this.unit]}>`;
  }
  get ArrayType() {
    return this.unit === DateUnit$1.DAY ? Int32Array : BigInt64Array;
  }
}
_l = Symbol.toStringTag;
Date_[_l] = ((proto) => {
  proto.unit = null;
  return proto[Symbol.toStringTag] = "Date";
})(Date_.prototype);
class Time_ extends DataType {
  constructor(unit, bitWidth) {
    super(Type$1.Time);
    this.unit = unit;
    this.bitWidth = bitWidth;
  }
  toString() {
    return `Time${this.bitWidth}<${TimeUnit$1[this.unit]}>`;
  }
  get ArrayType() {
    switch (this.bitWidth) {
      case 32:
        return Int32Array;
      case 64:
        return BigInt64Array;
    }
    throw new Error(`Unrecognized ${this[Symbol.toStringTag]} type`);
  }
}
_m = Symbol.toStringTag;
Time_[_m] = ((proto) => {
  proto.unit = null;
  proto.bitWidth = null;
  return proto[Symbol.toStringTag] = "Time";
})(Time_.prototype);
class Timestamp_ extends DataType {
  constructor(unit, timezone) {
    super(Type$1.Timestamp);
    this.unit = unit;
    this.timezone = timezone;
  }
  toString() {
    return `Timestamp<${TimeUnit$1[this.unit]}${this.timezone ? `, ${this.timezone}` : ``}>`;
  }
}
_o = Symbol.toStringTag;
Timestamp_[_o] = ((proto) => {
  proto.unit = null;
  proto.timezone = null;
  proto.ArrayType = BigInt64Array;
  return proto[Symbol.toStringTag] = "Timestamp";
})(Timestamp_.prototype);
class Interval_ extends DataType {
  constructor(unit) {
    super(Type$1.Interval);
    this.unit = unit;
  }
  toString() {
    return `Interval<${IntervalUnit$1[this.unit]}>`;
  }
}
_p = Symbol.toStringTag;
Interval_[_p] = ((proto) => {
  proto.unit = null;
  proto.ArrayType = Int32Array;
  return proto[Symbol.toStringTag] = "Interval";
})(Interval_.prototype);
class Duration2 extends DataType {
  constructor(unit) {
    super(Type$1.Duration);
    this.unit = unit;
  }
  toString() {
    return `Duration<${TimeUnit$1[this.unit]}>`;
  }
}
_q = Symbol.toStringTag;
Duration2[_q] = ((proto) => {
  proto.unit = null;
  proto.ArrayType = BigInt64Array;
  return proto[Symbol.toStringTag] = "Duration";
})(Duration2.prototype);
class List2 extends DataType {
  constructor(child) {
    super(Type$1.List);
    this.children = [child];
  }
  toString() {
    return `List<${this.valueType}>`;
  }
  get valueType() {
    return this.children[0].type;
  }
  get valueField() {
    return this.children[0];
  }
  get ArrayType() {
    return this.valueType.ArrayType;
  }
}
_r = Symbol.toStringTag;
List2[_r] = ((proto) => {
  proto.children = null;
  return proto[Symbol.toStringTag] = "List";
})(List2.prototype);
class Struct extends DataType {
  constructor(children) {
    super(Type$1.Struct);
    this.children = children;
  }
  toString() {
    return `Struct<{${this.children.map((f) => `${f.name}:${f.type}`).join(`, `)}}>`;
  }
}
_s = Symbol.toStringTag;
Struct[_s] = ((proto) => {
  proto.children = null;
  return proto[Symbol.toStringTag] = "Struct";
})(Struct.prototype);
class Union_ extends DataType {
  constructor(mode, typeIds, children) {
    super(Type$1.Union);
    this.mode = mode;
    this.children = children;
    this.typeIds = typeIds = Int32Array.from(typeIds);
    this.typeIdToChildIndex = typeIds.reduce((typeIdToChildIndex, typeId, idx) => (typeIdToChildIndex[typeId] = idx) && typeIdToChildIndex || typeIdToChildIndex, /* @__PURE__ */ Object.create(null));
  }
  toString() {
    return `${this[Symbol.toStringTag]}<${this.children.map((x) => `${x.type}`).join(` | `)}>`;
  }
}
_t = Symbol.toStringTag;
Union_[_t] = ((proto) => {
  proto.mode = null;
  proto.typeIds = null;
  proto.children = null;
  proto.typeIdToChildIndex = null;
  proto.ArrayType = Int8Array;
  return proto[Symbol.toStringTag] = "Union";
})(Union_.prototype);
class FixedSizeBinary2 extends DataType {
  constructor(byteWidth) {
    super(Type$1.FixedSizeBinary);
    this.byteWidth = byteWidth;
  }
  toString() {
    return `FixedSizeBinary[${this.byteWidth}]`;
  }
}
_u = Symbol.toStringTag;
FixedSizeBinary2[_u] = ((proto) => {
  proto.byteWidth = null;
  proto.ArrayType = Uint8Array;
  return proto[Symbol.toStringTag] = "FixedSizeBinary";
})(FixedSizeBinary2.prototype);
class FixedSizeList2 extends DataType {
  constructor(listSize, child) {
    super(Type$1.FixedSizeList);
    this.listSize = listSize;
    this.children = [child];
  }
  get valueType() {
    return this.children[0].type;
  }
  get valueField() {
    return this.children[0];
  }
  get ArrayType() {
    return this.valueType.ArrayType;
  }
  toString() {
    return `FixedSizeList[${this.listSize}]<${this.valueType}>`;
  }
}
_v = Symbol.toStringTag;
FixedSizeList2[_v] = ((proto) => {
  proto.children = null;
  proto.listSize = null;
  return proto[Symbol.toStringTag] = "FixedSizeList";
})(FixedSizeList2.prototype);
class Map_ extends DataType {
  constructor(entries2, keysSorted = false) {
    var _y, _z, _0;
    super(Type$1.Map);
    this.children = [entries2];
    this.keysSorted = keysSorted;
    if (entries2) {
      entries2["name"] = "entries";
      if ((_y = entries2 === null || entries2 === void 0 ? void 0 : entries2.type) === null || _y === void 0 ? void 0 : _y.children) {
        const key2 = (_z = entries2 === null || entries2 === void 0 ? void 0 : entries2.type) === null || _z === void 0 ? void 0 : _z.children[0];
        if (key2) {
          key2["name"] = "key";
        }
        const val = (_0 = entries2 === null || entries2 === void 0 ? void 0 : entries2.type) === null || _0 === void 0 ? void 0 : _0.children[1];
        if (val) {
          val["name"] = "value";
        }
      }
    }
  }
  get keyType() {
    return this.children[0].type.children[0].type;
  }
  get valueType() {
    return this.children[0].type.children[1].type;
  }
  get childType() {
    return this.children[0].type;
  }
  toString() {
    return `Map<{${this.children[0].type.children.map((f) => `${f.name}:${f.type}`).join(`, `)}}>`;
  }
}
_w = Symbol.toStringTag;
Map_[_w] = ((proto) => {
  proto.children = null;
  proto.keysSorted = null;
  return proto[Symbol.toStringTag] = "Map_";
})(Map_.prototype);
const getId = /* @__PURE__ */ ((atomicDictionaryId) => () => ++atomicDictionaryId)(-1);
let Dictionary$1 = class Dictionary extends DataType {
  constructor(dictionary2, indices, id, isOrdered) {
    super(Type$1.Dictionary);
    this.indices = indices;
    this.dictionary = dictionary2;
    this.isOrdered = isOrdered || false;
    this.id = id == null ? getId() : bigIntToNumber(id);
  }
  get children() {
    return this.dictionary.children;
  }
  get valueType() {
    return this.dictionary;
  }
  get ArrayType() {
    return this.dictionary.ArrayType;
  }
  toString() {
    return `Dictionary<${this.indices}, ${this.dictionary}>`;
  }
};
_x = Symbol.toStringTag;
Dictionary$1[_x] = ((proto) => {
  proto.id = null;
  proto.indices = null;
  proto.isOrdered = null;
  proto.dictionary = null;
  return proto[Symbol.toStringTag] = "Dictionary";
})(Dictionary$1.prototype);
function strideForType(type) {
  const t2 = type;
  switch (type.typeId) {
    case Type$1.Decimal:
      return type.bitWidth / 32;
    case Type$1.Interval: {
      if (t2.unit === IntervalUnit$1.MONTH_DAY_NANO) {
        return 4;
      }
      return 1 + t2.unit;
    }
    // case Type.Int: return 1 + +((t as Int_).bitWidth > 32);
    // case Type.Time: return 1 + +((t as Time_).bitWidth > 32);
    case Type$1.FixedSizeList:
      return t2.listSize;
    case Type$1.FixedSizeBinary:
      return t2.byteWidth;
    default:
      return 1;
  }
}
class Visitor {
  visitMany(nodes, ...args) {
    return nodes.map((node, i) => this.visit(node, ...args.map((x) => x[i])));
  }
  visit(...args) {
    return this.getVisitFn(args[0], false).apply(this, args);
  }
  getVisitFn(node, throwIfNotFound = true) {
    return getVisitFn(this, node, throwIfNotFound);
  }
  getVisitFnByTypeId(typeId, throwIfNotFound = true) {
    return getVisitFnByTypeId(this, typeId, throwIfNotFound);
  }
  visitNull(_node, ..._args) {
    return null;
  }
  visitBool(_node, ..._args) {
    return null;
  }
  visitInt(_node, ..._args) {
    return null;
  }
  visitFloat(_node, ..._args) {
    return null;
  }
  visitUtf8(_node, ..._args) {
    return null;
  }
  visitLargeUtf8(_node, ..._args) {
    return null;
  }
  visitBinary(_node, ..._args) {
    return null;
  }
  visitLargeBinary(_node, ..._args) {
    return null;
  }
  visitFixedSizeBinary(_node, ..._args) {
    return null;
  }
  visitDate(_node, ..._args) {
    return null;
  }
  visitTimestamp(_node, ..._args) {
    return null;
  }
  visitTime(_node, ..._args) {
    return null;
  }
  visitDecimal(_node, ..._args) {
    return null;
  }
  visitList(_node, ..._args) {
    return null;
  }
  visitStruct(_node, ..._args) {
    return null;
  }
  visitUnion(_node, ..._args) {
    return null;
  }
  visitDictionary(_node, ..._args) {
    return null;
  }
  visitInterval(_node, ..._args) {
    return null;
  }
  visitDuration(_node, ..._args) {
    return null;
  }
  visitFixedSizeList(_node, ..._args) {
    return null;
  }
  visitMap(_node, ..._args) {
    return null;
  }
}
function getVisitFn(visitor, node, throwIfNotFound = true) {
  if (typeof node === "number") {
    return getVisitFnByTypeId(visitor, node, throwIfNotFound);
  }
  if (typeof node === "string" && node in Type$1) {
    return getVisitFnByTypeId(visitor, Type$1[node], throwIfNotFound);
  }
  if (node && node instanceof DataType) {
    return getVisitFnByTypeId(visitor, inferDType(node), throwIfNotFound);
  }
  if ((node === null || node === void 0 ? void 0 : node.type) && node.type instanceof DataType) {
    return getVisitFnByTypeId(visitor, inferDType(node.type), throwIfNotFound);
  }
  return getVisitFnByTypeId(visitor, Type$1.NONE, throwIfNotFound);
}
function getVisitFnByTypeId(visitor, dtype, throwIfNotFound = true) {
  let fn = null;
  switch (dtype) {
    case Type$1.Null:
      fn = visitor.visitNull;
      break;
    case Type$1.Bool:
      fn = visitor.visitBool;
      break;
    case Type$1.Int:
      fn = visitor.visitInt;
      break;
    case Type$1.Int8:
      fn = visitor.visitInt8 || visitor.visitInt;
      break;
    case Type$1.Int16:
      fn = visitor.visitInt16 || visitor.visitInt;
      break;
    case Type$1.Int32:
      fn = visitor.visitInt32 || visitor.visitInt;
      break;
    case Type$1.Int64:
      fn = visitor.visitInt64 || visitor.visitInt;
      break;
    case Type$1.Uint8:
      fn = visitor.visitUint8 || visitor.visitInt;
      break;
    case Type$1.Uint16:
      fn = visitor.visitUint16 || visitor.visitInt;
      break;
    case Type$1.Uint32:
      fn = visitor.visitUint32 || visitor.visitInt;
      break;
    case Type$1.Uint64:
      fn = visitor.visitUint64 || visitor.visitInt;
      break;
    case Type$1.Float:
      fn = visitor.visitFloat;
      break;
    case Type$1.Float16:
      fn = visitor.visitFloat16 || visitor.visitFloat;
      break;
    case Type$1.Float32:
      fn = visitor.visitFloat32 || visitor.visitFloat;
      break;
    case Type$1.Float64:
      fn = visitor.visitFloat64 || visitor.visitFloat;
      break;
    case Type$1.Utf8:
      fn = visitor.visitUtf8;
      break;
    case Type$1.LargeUtf8:
      fn = visitor.visitLargeUtf8;
      break;
    case Type$1.Binary:
      fn = visitor.visitBinary;
      break;
    case Type$1.LargeBinary:
      fn = visitor.visitLargeBinary;
      break;
    case Type$1.FixedSizeBinary:
      fn = visitor.visitFixedSizeBinary;
      break;
    case Type$1.Date:
      fn = visitor.visitDate;
      break;
    case Type$1.DateDay:
      fn = visitor.visitDateDay || visitor.visitDate;
      break;
    case Type$1.DateMillisecond:
      fn = visitor.visitDateMillisecond || visitor.visitDate;
      break;
    case Type$1.Timestamp:
      fn = visitor.visitTimestamp;
      break;
    case Type$1.TimestampSecond:
      fn = visitor.visitTimestampSecond || visitor.visitTimestamp;
      break;
    case Type$1.TimestampMillisecond:
      fn = visitor.visitTimestampMillisecond || visitor.visitTimestamp;
      break;
    case Type$1.TimestampMicrosecond:
      fn = visitor.visitTimestampMicrosecond || visitor.visitTimestamp;
      break;
    case Type$1.TimestampNanosecond:
      fn = visitor.visitTimestampNanosecond || visitor.visitTimestamp;
      break;
    case Type$1.Time:
      fn = visitor.visitTime;
      break;
    case Type$1.TimeSecond:
      fn = visitor.visitTimeSecond || visitor.visitTime;
      break;
    case Type$1.TimeMillisecond:
      fn = visitor.visitTimeMillisecond || visitor.visitTime;
      break;
    case Type$1.TimeMicrosecond:
      fn = visitor.visitTimeMicrosecond || visitor.visitTime;
      break;
    case Type$1.TimeNanosecond:
      fn = visitor.visitTimeNanosecond || visitor.visitTime;
      break;
    case Type$1.Decimal:
      fn = visitor.visitDecimal;
      break;
    case Type$1.List:
      fn = visitor.visitList;
      break;
    case Type$1.Struct:
      fn = visitor.visitStruct;
      break;
    case Type$1.Union:
      fn = visitor.visitUnion;
      break;
    case Type$1.DenseUnion:
      fn = visitor.visitDenseUnion || visitor.visitUnion;
      break;
    case Type$1.SparseUnion:
      fn = visitor.visitSparseUnion || visitor.visitUnion;
      break;
    case Type$1.Dictionary:
      fn = visitor.visitDictionary;
      break;
    case Type$1.Interval:
      fn = visitor.visitInterval;
      break;
    case Type$1.IntervalDayTime:
      fn = visitor.visitIntervalDayTime || visitor.visitInterval;
      break;
    case Type$1.IntervalYearMonth:
      fn = visitor.visitIntervalYearMonth || visitor.visitInterval;
      break;
    case Type$1.IntervalMonthDayNano:
      fn = visitor.visitIntervalMonthDayNano || visitor.visitInterval;
      break;
    case Type$1.Duration:
      fn = visitor.visitDuration;
      break;
    case Type$1.DurationSecond:
      fn = visitor.visitDurationSecond || visitor.visitDuration;
      break;
    case Type$1.DurationMillisecond:
      fn = visitor.visitDurationMillisecond || visitor.visitDuration;
      break;
    case Type$1.DurationMicrosecond:
      fn = visitor.visitDurationMicrosecond || visitor.visitDuration;
      break;
    case Type$1.DurationNanosecond:
      fn = visitor.visitDurationNanosecond || visitor.visitDuration;
      break;
    case Type$1.FixedSizeList:
      fn = visitor.visitFixedSizeList;
      break;
    case Type$1.Map:
      fn = visitor.visitMap;
      break;
  }
  if (typeof fn === "function")
    return fn;
  if (!throwIfNotFound)
    return () => null;
  throw new Error(`Unrecognized type '${Type$1[dtype]}'`);
}
function inferDType(type) {
  switch (type.typeId) {
    case Type$1.Null:
      return Type$1.Null;
    case Type$1.Int: {
      const { bitWidth, isSigned } = type;
      switch (bitWidth) {
        case 8:
          return isSigned ? Type$1.Int8 : Type$1.Uint8;
        case 16:
          return isSigned ? Type$1.Int16 : Type$1.Uint16;
        case 32:
          return isSigned ? Type$1.Int32 : Type$1.Uint32;
        case 64:
          return isSigned ? Type$1.Int64 : Type$1.Uint64;
      }
      return Type$1.Int;
    }
    case Type$1.Float:
      switch (type.precision) {
        case Precision$1.HALF:
          return Type$1.Float16;
        case Precision$1.SINGLE:
          return Type$1.Float32;
        case Precision$1.DOUBLE:
          return Type$1.Float64;
      }
      return Type$1.Float;
    case Type$1.Binary:
      return Type$1.Binary;
    case Type$1.LargeBinary:
      return Type$1.LargeBinary;
    case Type$1.Utf8:
      return Type$1.Utf8;
    case Type$1.LargeUtf8:
      return Type$1.LargeUtf8;
    case Type$1.Bool:
      return Type$1.Bool;
    case Type$1.Decimal:
      return Type$1.Decimal;
    case Type$1.Time:
      switch (type.unit) {
        case TimeUnit$1.SECOND:
          return Type$1.TimeSecond;
        case TimeUnit$1.MILLISECOND:
          return Type$1.TimeMillisecond;
        case TimeUnit$1.MICROSECOND:
          return Type$1.TimeMicrosecond;
        case TimeUnit$1.NANOSECOND:
          return Type$1.TimeNanosecond;
      }
      return Type$1.Time;
    case Type$1.Timestamp:
      switch (type.unit) {
        case TimeUnit$1.SECOND:
          return Type$1.TimestampSecond;
        case TimeUnit$1.MILLISECOND:
          return Type$1.TimestampMillisecond;
        case TimeUnit$1.MICROSECOND:
          return Type$1.TimestampMicrosecond;
        case TimeUnit$1.NANOSECOND:
          return Type$1.TimestampNanosecond;
      }
      return Type$1.Timestamp;
    case Type$1.Date:
      switch (type.unit) {
        case DateUnit$1.DAY:
          return Type$1.DateDay;
        case DateUnit$1.MILLISECOND:
          return Type$1.DateMillisecond;
      }
      return Type$1.Date;
    case Type$1.Interval:
      switch (type.unit) {
        case IntervalUnit$1.DAY_TIME:
          return Type$1.IntervalDayTime;
        case IntervalUnit$1.YEAR_MONTH:
          return Type$1.IntervalYearMonth;
        case IntervalUnit$1.MONTH_DAY_NANO:
          return Type$1.IntervalMonthDayNano;
      }
      return Type$1.Interval;
    case Type$1.Duration:
      switch (type.unit) {
        case TimeUnit$1.SECOND:
          return Type$1.DurationSecond;
        case TimeUnit$1.MILLISECOND:
          return Type$1.DurationMillisecond;
        case TimeUnit$1.MICROSECOND:
          return Type$1.DurationMicrosecond;
        case TimeUnit$1.NANOSECOND:
          return Type$1.DurationNanosecond;
      }
      return Type$1.Duration;
    case Type$1.Map:
      return Type$1.Map;
    case Type$1.List:
      return Type$1.List;
    case Type$1.Struct:
      return Type$1.Struct;
    case Type$1.Union:
      switch (type.mode) {
        case UnionMode$1.Dense:
          return Type$1.DenseUnion;
        case UnionMode$1.Sparse:
          return Type$1.SparseUnion;
      }
      return Type$1.Union;
    case Type$1.FixedSizeBinary:
      return Type$1.FixedSizeBinary;
    case Type$1.FixedSizeList:
      return Type$1.FixedSizeList;
    case Type$1.Dictionary:
      return Type$1.Dictionary;
  }
  throw new Error(`Unrecognized type '${Type$1[type.typeId]}'`);
}
Visitor.prototype.visitInt8 = null;
Visitor.prototype.visitInt16 = null;
Visitor.prototype.visitInt32 = null;
Visitor.prototype.visitInt64 = null;
Visitor.prototype.visitUint8 = null;
Visitor.prototype.visitUint16 = null;
Visitor.prototype.visitUint32 = null;
Visitor.prototype.visitUint64 = null;
Visitor.prototype.visitFloat16 = null;
Visitor.prototype.visitFloat32 = null;
Visitor.prototype.visitFloat64 = null;
Visitor.prototype.visitDateDay = null;
Visitor.prototype.visitDateMillisecond = null;
Visitor.prototype.visitTimestampSecond = null;
Visitor.prototype.visitTimestampMillisecond = null;
Visitor.prototype.visitTimestampMicrosecond = null;
Visitor.prototype.visitTimestampNanosecond = null;
Visitor.prototype.visitTimeSecond = null;
Visitor.prototype.visitTimeMillisecond = null;
Visitor.prototype.visitTimeMicrosecond = null;
Visitor.prototype.visitTimeNanosecond = null;
Visitor.prototype.visitDenseUnion = null;
Visitor.prototype.visitSparseUnion = null;
Visitor.prototype.visitIntervalDayTime = null;
Visitor.prototype.visitIntervalYearMonth = null;
Visitor.prototype.visitIntervalMonthDayNano = null;
Visitor.prototype.visitDuration = null;
Visitor.prototype.visitDurationSecond = null;
Visitor.prototype.visitDurationMillisecond = null;
Visitor.prototype.visitDurationMicrosecond = null;
Visitor.prototype.visitDurationNanosecond = null;
const f64$1 = new Float64Array(1);
const u32$1 = new Uint32Array(f64$1.buffer);
function uint16ToFloat64(h) {
  const expo = (h & 31744) >> 10;
  const sigf = (h & 1023) / 1024;
  const sign2 = Math.pow(-1, (h & 32768) >> 15);
  switch (expo) {
    case 31:
      return sign2 * (sigf ? Number.NaN : 1 / 0);
    case 0:
      return sign2 * (sigf ? 6103515625e-14 * sigf : 0);
  }
  return sign2 * Math.pow(2, expo - 15) * (1 + sigf);
}
function float64ToUint16(d) {
  if (d !== d) {
    return 32256;
  }
  f64$1[0] = d;
  const sign2 = (u32$1[1] & 2147483648) >> 16 & 65535;
  let expo = u32$1[1] & 2146435072, sigf = 0;
  if (expo >= 1089470464) {
    if (u32$1[0] > 0) {
      expo = 31744;
    } else {
      expo = (expo & 2080374784) >> 16;
      sigf = (u32$1[1] & 1048575) >> 10;
    }
  } else if (expo <= 1056964608) {
    sigf = 1048576 + (u32$1[1] & 1048575);
    sigf = 1048576 + (sigf << (expo >> 20) - 998) >> 21;
    expo = 0;
  } else {
    expo = expo - 1056964608 >> 10;
    sigf = (u32$1[1] & 1048575) + 512 >> 10;
  }
  return sign2 | expo | sigf & 65535;
}
class SetVisitor extends Visitor {
}
function wrapSet(fn) {
  return (data2, _1, _2) => {
    if (data2.setValid(_1, _2 != null)) {
      return fn(data2, _1, _2);
    }
  };
}
const setEpochMsToDays = (data2, index, epochMs) => {
  data2[index] = Math.floor(epochMs / 864e5);
};
const setVariableWidthBytes = (values2, valueOffsets, index, value2) => {
  if (index + 1 < valueOffsets.length) {
    const x = bigIntToNumber(valueOffsets[index]);
    const y = bigIntToNumber(valueOffsets[index + 1]);
    values2.set(value2.subarray(0, y - x), x);
  }
};
const setBool = ({ offset: offset2, values: values2 }, index, val) => {
  const idx = offset2 + index;
  val ? values2[idx >> 3] |= 1 << idx % 8 : values2[idx >> 3] &= ~(1 << idx % 8);
};
const setInt = ({ values: values2 }, index, value2) => {
  values2[index] = value2;
};
const setFloat = ({ values: values2 }, index, value2) => {
  values2[index] = value2;
};
const setFloat16 = ({ values: values2 }, index, value2) => {
  values2[index] = float64ToUint16(value2);
};
const setAnyFloat = (data2, index, value2) => {
  switch (data2.type.precision) {
    case Precision$1.HALF:
      return setFloat16(data2, index, value2);
    case Precision$1.SINGLE:
    case Precision$1.DOUBLE:
      return setFloat(data2, index, value2);
  }
};
const setDateDay = ({ values: values2 }, index, value2) => {
  setEpochMsToDays(values2, index, value2.valueOf());
};
const setDateMillisecond = ({ values: values2 }, index, value2) => {
  values2[index] = BigInt(value2);
};
const setFixedSizeBinary = ({ stride, values: values2 }, index, value2) => {
  values2.set(value2.subarray(0, stride), stride * index);
};
const setBinary = ({ values: values2, valueOffsets }, index, value2) => setVariableWidthBytes(values2, valueOffsets, index, value2);
const setUtf8 = ({ values: values2, valueOffsets }, index, value2) => setVariableWidthBytes(values2, valueOffsets, index, encodeUtf8$1(value2));
const setDate = (data2, index, value2) => {
  data2.type.unit === DateUnit$1.DAY ? setDateDay(data2, index, value2) : setDateMillisecond(data2, index, value2);
};
const setTimestampSecond = ({ values: values2 }, index, value2) => {
  values2[index] = BigInt(value2 / 1e3);
};
const setTimestampMillisecond = ({ values: values2 }, index, value2) => {
  values2[index] = BigInt(value2);
};
const setTimestampMicrosecond = ({ values: values2 }, index, value2) => {
  values2[index] = BigInt(value2 * 1e3);
};
const setTimestampNanosecond = ({ values: values2 }, index, value2) => {
  values2[index] = BigInt(value2 * 1e6);
};
const setTimestamp = (data2, index, value2) => {
  switch (data2.type.unit) {
    case TimeUnit$1.SECOND:
      return setTimestampSecond(data2, index, value2);
    case TimeUnit$1.MILLISECOND:
      return setTimestampMillisecond(data2, index, value2);
    case TimeUnit$1.MICROSECOND:
      return setTimestampMicrosecond(data2, index, value2);
    case TimeUnit$1.NANOSECOND:
      return setTimestampNanosecond(data2, index, value2);
  }
};
const setTimeSecond = ({ values: values2 }, index, value2) => {
  values2[index] = value2;
};
const setTimeMillisecond = ({ values: values2 }, index, value2) => {
  values2[index] = value2;
};
const setTimeMicrosecond = ({ values: values2 }, index, value2) => {
  values2[index] = value2;
};
const setTimeNanosecond = ({ values: values2 }, index, value2) => {
  values2[index] = value2;
};
const setTime = (data2, index, value2) => {
  switch (data2.type.unit) {
    case TimeUnit$1.SECOND:
      return setTimeSecond(data2, index, value2);
    case TimeUnit$1.MILLISECOND:
      return setTimeMillisecond(data2, index, value2);
    case TimeUnit$1.MICROSECOND:
      return setTimeMicrosecond(data2, index, value2);
    case TimeUnit$1.NANOSECOND:
      return setTimeNanosecond(data2, index, value2);
  }
};
const setDecimal = ({ values: values2, stride }, index, value2) => {
  values2.set(value2.subarray(0, stride), stride * index);
};
const setList = (data2, index, value2) => {
  const values2 = data2.children[0];
  const valueOffsets = data2.valueOffsets;
  const set = instance$5.getVisitFn(values2);
  if (Array.isArray(value2)) {
    for (let idx = -1, itr = valueOffsets[index], end = valueOffsets[index + 1]; itr < end; ) {
      set(values2, itr++, value2[++idx]);
    }
  } else {
    for (let idx = -1, itr = valueOffsets[index], end = valueOffsets[index + 1]; itr < end; ) {
      set(values2, itr++, value2.get(++idx));
    }
  }
};
const setMap = (data2, index, value2) => {
  const values2 = data2.children[0];
  const { valueOffsets } = data2;
  const set = instance$5.getVisitFn(values2);
  let { [index]: idx, [index + 1]: end } = valueOffsets;
  const entries2 = value2 instanceof Map ? value2.entries() : Object.entries(value2);
  for (const val of entries2) {
    set(values2, idx, val);
    if (++idx >= end)
      break;
  }
};
const _setStructArrayValue = (o, v) => (set, c, _, i) => c && set(c, o, v[i]);
const _setStructVectorValue = (o, v) => (set, c, _, i) => c && set(c, o, v.get(i));
const _setStructMapValue = (o, v) => (set, c, f, _) => c && set(c, o, v.get(f.name));
const _setStructObjectValue = (o, v) => (set, c, f, _) => c && set(c, o, v[f.name]);
const setStruct = (data2, index, value2) => {
  const childSetters = data2.type.children.map((f) => instance$5.getVisitFn(f.type));
  const set = value2 instanceof Map ? _setStructMapValue(index, value2) : value2 instanceof Vector ? _setStructVectorValue(index, value2) : Array.isArray(value2) ? _setStructArrayValue(index, value2) : _setStructObjectValue(index, value2);
  data2.type.children.forEach((f, i) => set(childSetters[i], data2.children[i], f, i));
};
const setUnion = (data2, index, value2) => {
  data2.type.mode === UnionMode$1.Dense ? setDenseUnion(data2, index, value2) : setSparseUnion(data2, index, value2);
};
const setDenseUnion = (data2, index, value2) => {
  const childIndex = data2.type.typeIdToChildIndex[data2.typeIds[index]];
  const child = data2.children[childIndex];
  instance$5.visit(child, data2.valueOffsets[index], value2);
};
const setSparseUnion = (data2, index, value2) => {
  const childIndex = data2.type.typeIdToChildIndex[data2.typeIds[index]];
  const child = data2.children[childIndex];
  instance$5.visit(child, index, value2);
};
const setDictionary = (data2, index, value2) => {
  var _a2;
  (_a2 = data2.dictionary) === null || _a2 === void 0 ? void 0 : _a2.set(data2.values[index], value2);
};
const setIntervalValue = (data2, index, value2) => {
  switch (data2.type.unit) {
    case IntervalUnit$1.YEAR_MONTH:
      return setIntervalYearMonth(data2, index, value2);
    case IntervalUnit$1.DAY_TIME:
      return setIntervalDayTime(data2, index, value2);
    case IntervalUnit$1.MONTH_DAY_NANO:
      return setIntervalMonthDayNano(data2, index, value2);
  }
};
const setIntervalDayTime = ({ values: values2 }, index, value2) => {
  values2.set(value2.subarray(0, 2), 2 * index);
};
const setIntervalYearMonth = ({ values: values2 }, index, value2) => {
  values2[index] = value2[0] * 12 + value2[1] % 12;
};
const setIntervalMonthDayNano = ({ values: values2, stride }, index, value2) => {
  values2.set(value2.subarray(0, stride), stride * index);
};
const setDurationSecond = ({ values: values2 }, index, value2) => {
  values2[index] = value2;
};
const setDurationMillisecond = ({ values: values2 }, index, value2) => {
  values2[index] = value2;
};
const setDurationMicrosecond = ({ values: values2 }, index, value2) => {
  values2[index] = value2;
};
const setDurationNanosecond = ({ values: values2 }, index, value2) => {
  values2[index] = value2;
};
const setDuration = (data2, index, value2) => {
  switch (data2.type.unit) {
    case TimeUnit$1.SECOND:
      return setDurationSecond(data2, index, value2);
    case TimeUnit$1.MILLISECOND:
      return setDurationMillisecond(data2, index, value2);
    case TimeUnit$1.MICROSECOND:
      return setDurationMicrosecond(data2, index, value2);
    case TimeUnit$1.NANOSECOND:
      return setDurationNanosecond(data2, index, value2);
  }
};
const setFixedSizeList = (data2, index, value2) => {
  const { stride } = data2;
  const child = data2.children[0];
  const set = instance$5.getVisitFn(child);
  if (Array.isArray(value2)) {
    for (let idx = -1, offset2 = index * stride; ++idx < stride; ) {
      set(child, offset2 + idx, value2[idx]);
    }
  } else {
    for (let idx = -1, offset2 = index * stride; ++idx < stride; ) {
      set(child, offset2 + idx, value2.get(idx));
    }
  }
};
SetVisitor.prototype.visitBool = wrapSet(setBool);
SetVisitor.prototype.visitInt = wrapSet(setInt);
SetVisitor.prototype.visitInt8 = wrapSet(setInt);
SetVisitor.prototype.visitInt16 = wrapSet(setInt);
SetVisitor.prototype.visitInt32 = wrapSet(setInt);
SetVisitor.prototype.visitInt64 = wrapSet(setInt);
SetVisitor.prototype.visitUint8 = wrapSet(setInt);
SetVisitor.prototype.visitUint16 = wrapSet(setInt);
SetVisitor.prototype.visitUint32 = wrapSet(setInt);
SetVisitor.prototype.visitUint64 = wrapSet(setInt);
SetVisitor.prototype.visitFloat = wrapSet(setAnyFloat);
SetVisitor.prototype.visitFloat16 = wrapSet(setFloat16);
SetVisitor.prototype.visitFloat32 = wrapSet(setFloat);
SetVisitor.prototype.visitFloat64 = wrapSet(setFloat);
SetVisitor.prototype.visitUtf8 = wrapSet(setUtf8);
SetVisitor.prototype.visitLargeUtf8 = wrapSet(setUtf8);
SetVisitor.prototype.visitBinary = wrapSet(setBinary);
SetVisitor.prototype.visitLargeBinary = wrapSet(setBinary);
SetVisitor.prototype.visitFixedSizeBinary = wrapSet(setFixedSizeBinary);
SetVisitor.prototype.visitDate = wrapSet(setDate);
SetVisitor.prototype.visitDateDay = wrapSet(setDateDay);
SetVisitor.prototype.visitDateMillisecond = wrapSet(setDateMillisecond);
SetVisitor.prototype.visitTimestamp = wrapSet(setTimestamp);
SetVisitor.prototype.visitTimestampSecond = wrapSet(setTimestampSecond);
SetVisitor.prototype.visitTimestampMillisecond = wrapSet(setTimestampMillisecond);
SetVisitor.prototype.visitTimestampMicrosecond = wrapSet(setTimestampMicrosecond);
SetVisitor.prototype.visitTimestampNanosecond = wrapSet(setTimestampNanosecond);
SetVisitor.prototype.visitTime = wrapSet(setTime);
SetVisitor.prototype.visitTimeSecond = wrapSet(setTimeSecond);
SetVisitor.prototype.visitTimeMillisecond = wrapSet(setTimeMillisecond);
SetVisitor.prototype.visitTimeMicrosecond = wrapSet(setTimeMicrosecond);
SetVisitor.prototype.visitTimeNanosecond = wrapSet(setTimeNanosecond);
SetVisitor.prototype.visitDecimal = wrapSet(setDecimal);
SetVisitor.prototype.visitList = wrapSet(setList);
SetVisitor.prototype.visitStruct = wrapSet(setStruct);
SetVisitor.prototype.visitUnion = wrapSet(setUnion);
SetVisitor.prototype.visitDenseUnion = wrapSet(setDenseUnion);
SetVisitor.prototype.visitSparseUnion = wrapSet(setSparseUnion);
SetVisitor.prototype.visitDictionary = wrapSet(setDictionary);
SetVisitor.prototype.visitInterval = wrapSet(setIntervalValue);
SetVisitor.prototype.visitIntervalDayTime = wrapSet(setIntervalDayTime);
SetVisitor.prototype.visitIntervalYearMonth = wrapSet(setIntervalYearMonth);
SetVisitor.prototype.visitIntervalMonthDayNano = wrapSet(setIntervalMonthDayNano);
SetVisitor.prototype.visitDuration = wrapSet(setDuration);
SetVisitor.prototype.visitDurationSecond = wrapSet(setDurationSecond);
SetVisitor.prototype.visitDurationMillisecond = wrapSet(setDurationMillisecond);
SetVisitor.prototype.visitDurationMicrosecond = wrapSet(setDurationMicrosecond);
SetVisitor.prototype.visitDurationNanosecond = wrapSet(setDurationNanosecond);
SetVisitor.prototype.visitFixedSizeList = wrapSet(setFixedSizeList);
SetVisitor.prototype.visitMap = wrapSet(setMap);
const instance$5 = new SetVisitor();
const kParent = /* @__PURE__ */ Symbol.for("parent");
const kRowIndex = /* @__PURE__ */ Symbol.for("rowIndex");
class StructRow {
  constructor(parent, rowIndex) {
    this[kParent] = parent;
    this[kRowIndex] = rowIndex;
    return new Proxy(this, structRowProxyHandler);
  }
  toArray() {
    return Object.values(this.toJSON());
  }
  toJSON() {
    const i = this[kRowIndex];
    const parent = this[kParent];
    const keys2 = parent.type.children;
    const json2 = {};
    for (let j = -1, n = keys2.length; ++j < n; ) {
      json2[keys2[j].name] = instance$4.visit(parent.children[j], i);
    }
    return json2;
  }
  toString() {
    return `{${[...this].map(([key2, val]) => `${valueToString(key2)}: ${valueToString(val)}`).join(", ")}}`;
  }
  [/* @__PURE__ */ Symbol.for("nodejs.util.inspect.custom")]() {
    return this.toString();
  }
  [Symbol.iterator]() {
    return new StructRowIterator(this[kParent], this[kRowIndex]);
  }
}
class StructRowIterator {
  constructor(data2, rowIndex) {
    this.childIndex = 0;
    this.children = data2.children;
    this.rowIndex = rowIndex;
    this.childFields = data2.type.children;
    this.numChildren = this.childFields.length;
  }
  [Symbol.iterator]() {
    return this;
  }
  next() {
    const i = this.childIndex;
    if (i < this.numChildren) {
      this.childIndex = i + 1;
      return {
        done: false,
        value: [
          this.childFields[i].name,
          instance$4.visit(this.children[i], this.rowIndex)
        ]
      };
    }
    return { done: true, value: null };
  }
}
Object.defineProperties(StructRow.prototype, {
  [Symbol.toStringTag]: { enumerable: false, configurable: false, value: "Row" },
  [kParent]: { writable: true, enumerable: false, configurable: false, value: null },
  [kRowIndex]: { writable: true, enumerable: false, configurable: false, value: -1 }
});
class StructRowProxyHandler {
  isExtensible() {
    return false;
  }
  deleteProperty() {
    return false;
  }
  preventExtensions() {
    return true;
  }
  ownKeys(row) {
    return row[kParent].type.children.map((f) => f.name);
  }
  has(row, key2) {
    return row[kParent].type.children.some((f) => f.name === key2);
  }
  getOwnPropertyDescriptor(row, key2) {
    if (row[kParent].type.children.some((f) => f.name === key2)) {
      return { writable: true, enumerable: true, configurable: true };
    }
    return;
  }
  get(row, key2) {
    if (Reflect.has(row, key2)) {
      return row[key2];
    }
    const idx = row[kParent].type.children.findIndex((f) => f.name === key2);
    if (idx !== -1) {
      const val = instance$4.visit(row[kParent].children[idx], row[kRowIndex]);
      Reflect.set(row, key2, val);
      return val;
    }
  }
  set(row, key2, val) {
    const idx = row[kParent].type.children.findIndex((f) => f.name === key2);
    if (idx !== -1) {
      instance$5.visit(row[kParent].children[idx], row[kRowIndex], val);
      return Reflect.set(row, key2, val);
    } else if (Reflect.has(row, key2) || typeof key2 === "symbol") {
      return Reflect.set(row, key2, val);
    }
    return false;
  }
}
const structRowProxyHandler = new StructRowProxyHandler();
class GetVisitor extends Visitor {
}
function wrapGet(fn) {
  return (data2, _1) => data2.getValid(_1) ? fn(data2, _1) : null;
}
const epochDaysToMs = (data2, index) => 864e5 * data2[index];
const getNull = (_data, _index) => null;
const getVariableWidthBytes = (values2, valueOffsets, index) => {
  if (index + 1 >= valueOffsets.length) {
    return null;
  }
  const x = bigIntToNumber(valueOffsets[index]);
  const y = bigIntToNumber(valueOffsets[index + 1]);
  return values2.subarray(x, y);
};
const getBool$1 = ({ offset: offset2, values: values2 }, index) => {
  const idx = offset2 + index;
  const byte = values2[idx >> 3];
  return (byte & 1 << idx % 8) !== 0;
};
const getDateDay = ({ values: values2 }, index) => epochDaysToMs(values2, index);
const getDateMillisecond = ({ values: values2 }, index) => bigIntToNumber(values2[index]);
const getNumeric = ({ stride, values: values2 }, index) => values2[stride * index];
const getFloat16 = ({ stride, values: values2 }, index) => uint16ToFloat64(values2[stride * index]);
const getBigInts = ({ values: values2 }, index) => values2[index];
const getFixedSizeBinary = ({ stride, values: values2 }, index) => values2.subarray(stride * index, stride * (index + 1));
const getBinary = ({ values: values2, valueOffsets }, index) => getVariableWidthBytes(values2, valueOffsets, index);
const getUtf8 = ({ values: values2, valueOffsets }, index) => {
  const bytes = getVariableWidthBytes(values2, valueOffsets, index);
  return bytes !== null ? decodeUtf8$1(bytes) : null;
};
const getInt = ({ values: values2 }, index) => values2[index];
const getFloat = ({ type, values: values2 }, index) => type.precision !== Precision$1.HALF ? values2[index] : uint16ToFloat64(values2[index]);
const getDate = (data2, index) => data2.type.unit === DateUnit$1.DAY ? getDateDay(data2, index) : getDateMillisecond(data2, index);
const getTimestampSecond = ({ values: values2 }, index) => 1e3 * bigIntToNumber(values2[index]);
const getTimestampMillisecond = ({ values: values2 }, index) => bigIntToNumber(values2[index]);
const getTimestampMicrosecond = ({ values: values2 }, index) => divideBigInts(values2[index], BigInt(1e3));
const getTimestampNanosecond = ({ values: values2 }, index) => divideBigInts(values2[index], BigInt(1e6));
const getTimestamp = (data2, index) => {
  switch (data2.type.unit) {
    case TimeUnit$1.SECOND:
      return getTimestampSecond(data2, index);
    case TimeUnit$1.MILLISECOND:
      return getTimestampMillisecond(data2, index);
    case TimeUnit$1.MICROSECOND:
      return getTimestampMicrosecond(data2, index);
    case TimeUnit$1.NANOSECOND:
      return getTimestampNanosecond(data2, index);
  }
};
const getTimeSecond = ({ values: values2 }, index) => values2[index];
const getTimeMillisecond = ({ values: values2 }, index) => values2[index];
const getTimeMicrosecond = ({ values: values2 }, index) => values2[index];
const getTimeNanosecond = ({ values: values2 }, index) => values2[index];
const getTime = (data2, index) => {
  switch (data2.type.unit) {
    case TimeUnit$1.SECOND:
      return getTimeSecond(data2, index);
    case TimeUnit$1.MILLISECOND:
      return getTimeMillisecond(data2, index);
    case TimeUnit$1.MICROSECOND:
      return getTimeMicrosecond(data2, index);
    case TimeUnit$1.NANOSECOND:
      return getTimeNanosecond(data2, index);
  }
};
const getDecimal = ({ values: values2, stride }, index) => BN.decimal(values2.subarray(stride * index, stride * (index + 1)));
const getList = (data2, index) => {
  const { valueOffsets, stride, children } = data2;
  const { [index * stride]: begin, [index * stride + 1]: end } = valueOffsets;
  const child = children[0];
  const slice2 = child.slice(begin, end - begin);
  return new Vector([slice2]);
};
const getMap = (data2, index) => {
  const { valueOffsets, children } = data2;
  const { [index]: begin, [index + 1]: end } = valueOffsets;
  const child = children[0];
  return new MapRow(child.slice(begin, end - begin));
};
const getStruct = (data2, index) => {
  return new StructRow(data2, index);
};
const getUnion = (data2, index) => {
  return data2.type.mode === UnionMode$1.Dense ? getDenseUnion(data2, index) : getSparseUnion(data2, index);
};
const getDenseUnion = (data2, index) => {
  const childIndex = data2.type.typeIdToChildIndex[data2.typeIds[index]];
  const child = data2.children[childIndex];
  return instance$4.visit(child, data2.valueOffsets[index]);
};
const getSparseUnion = (data2, index) => {
  const childIndex = data2.type.typeIdToChildIndex[data2.typeIds[index]];
  const child = data2.children[childIndex];
  return instance$4.visit(child, index);
};
const getDictionary = (data2, index) => {
  var _a2;
  return (_a2 = data2.dictionary) === null || _a2 === void 0 ? void 0 : _a2.get(data2.values[index]);
};
const getInterval = (data2, index) => data2.type.unit === IntervalUnit$1.MONTH_DAY_NANO ? getIntervalMonthDayNano(data2, index) : data2.type.unit === IntervalUnit$1.DAY_TIME ? getIntervalDayTime(data2, index) : getIntervalYearMonth(data2, index);
const getIntervalDayTime = ({ values: values2 }, index) => values2.subarray(2 * index, 2 * (index + 1));
const getIntervalYearMonth = ({ values: values2 }, index) => {
  const interval2 = values2[index];
  const int32s = new Int32Array(2);
  int32s[0] = Math.trunc(interval2 / 12);
  int32s[1] = Math.trunc(interval2 % 12);
  return int32s;
};
const getIntervalMonthDayNano = ({ values: values2 }, index) => values2.subarray(4 * index, 4 * (index + 1));
const getDurationSecond = ({ values: values2 }, index) => values2[index];
const getDurationMillisecond = ({ values: values2 }, index) => values2[index];
const getDurationMicrosecond = ({ values: values2 }, index) => values2[index];
const getDurationNanosecond = ({ values: values2 }, index) => values2[index];
const getDuration = (data2, index) => {
  switch (data2.type.unit) {
    case TimeUnit$1.SECOND:
      return getDurationSecond(data2, index);
    case TimeUnit$1.MILLISECOND:
      return getDurationMillisecond(data2, index);
    case TimeUnit$1.MICROSECOND:
      return getDurationMicrosecond(data2, index);
    case TimeUnit$1.NANOSECOND:
      return getDurationNanosecond(data2, index);
  }
};
const getFixedSizeList = (data2, index) => {
  const { stride, children } = data2;
  const child = children[0];
  const slice2 = child.slice(index * stride, stride);
  return new Vector([slice2]);
};
GetVisitor.prototype.visitNull = wrapGet(getNull);
GetVisitor.prototype.visitBool = wrapGet(getBool$1);
GetVisitor.prototype.visitInt = wrapGet(getInt);
GetVisitor.prototype.visitInt8 = wrapGet(getNumeric);
GetVisitor.prototype.visitInt16 = wrapGet(getNumeric);
GetVisitor.prototype.visitInt32 = wrapGet(getNumeric);
GetVisitor.prototype.visitInt64 = wrapGet(getBigInts);
GetVisitor.prototype.visitUint8 = wrapGet(getNumeric);
GetVisitor.prototype.visitUint16 = wrapGet(getNumeric);
GetVisitor.prototype.visitUint32 = wrapGet(getNumeric);
GetVisitor.prototype.visitUint64 = wrapGet(getBigInts);
GetVisitor.prototype.visitFloat = wrapGet(getFloat);
GetVisitor.prototype.visitFloat16 = wrapGet(getFloat16);
GetVisitor.prototype.visitFloat32 = wrapGet(getNumeric);
GetVisitor.prototype.visitFloat64 = wrapGet(getNumeric);
GetVisitor.prototype.visitUtf8 = wrapGet(getUtf8);
GetVisitor.prototype.visitLargeUtf8 = wrapGet(getUtf8);
GetVisitor.prototype.visitBinary = wrapGet(getBinary);
GetVisitor.prototype.visitLargeBinary = wrapGet(getBinary);
GetVisitor.prototype.visitFixedSizeBinary = wrapGet(getFixedSizeBinary);
GetVisitor.prototype.visitDate = wrapGet(getDate);
GetVisitor.prototype.visitDateDay = wrapGet(getDateDay);
GetVisitor.prototype.visitDateMillisecond = wrapGet(getDateMillisecond);
GetVisitor.prototype.visitTimestamp = wrapGet(getTimestamp);
GetVisitor.prototype.visitTimestampSecond = wrapGet(getTimestampSecond);
GetVisitor.prototype.visitTimestampMillisecond = wrapGet(getTimestampMillisecond);
GetVisitor.prototype.visitTimestampMicrosecond = wrapGet(getTimestampMicrosecond);
GetVisitor.prototype.visitTimestampNanosecond = wrapGet(getTimestampNanosecond);
GetVisitor.prototype.visitTime = wrapGet(getTime);
GetVisitor.prototype.visitTimeSecond = wrapGet(getTimeSecond);
GetVisitor.prototype.visitTimeMillisecond = wrapGet(getTimeMillisecond);
GetVisitor.prototype.visitTimeMicrosecond = wrapGet(getTimeMicrosecond);
GetVisitor.prototype.visitTimeNanosecond = wrapGet(getTimeNanosecond);
GetVisitor.prototype.visitDecimal = wrapGet(getDecimal);
GetVisitor.prototype.visitList = wrapGet(getList);
GetVisitor.prototype.visitStruct = wrapGet(getStruct);
GetVisitor.prototype.visitUnion = wrapGet(getUnion);
GetVisitor.prototype.visitDenseUnion = wrapGet(getDenseUnion);
GetVisitor.prototype.visitSparseUnion = wrapGet(getSparseUnion);
GetVisitor.prototype.visitDictionary = wrapGet(getDictionary);
GetVisitor.prototype.visitInterval = wrapGet(getInterval);
GetVisitor.prototype.visitIntervalDayTime = wrapGet(getIntervalDayTime);
GetVisitor.prototype.visitIntervalYearMonth = wrapGet(getIntervalYearMonth);
GetVisitor.prototype.visitIntervalMonthDayNano = wrapGet(getIntervalMonthDayNano);
GetVisitor.prototype.visitDuration = wrapGet(getDuration);
GetVisitor.prototype.visitDurationSecond = wrapGet(getDurationSecond);
GetVisitor.prototype.visitDurationMillisecond = wrapGet(getDurationMillisecond);
GetVisitor.prototype.visitDurationMicrosecond = wrapGet(getDurationMicrosecond);
GetVisitor.prototype.visitDurationNanosecond = wrapGet(getDurationNanosecond);
GetVisitor.prototype.visitFixedSizeList = wrapGet(getFixedSizeList);
GetVisitor.prototype.visitMap = wrapGet(getMap);
const instance$4 = new GetVisitor();
const kKeys = /* @__PURE__ */ Symbol.for("keys");
const kVals = /* @__PURE__ */ Symbol.for("vals");
const kKeysAsStrings = /* @__PURE__ */ Symbol.for("kKeysAsStrings");
const _kKeysAsStrings = /* @__PURE__ */ Symbol.for("_kKeysAsStrings");
class MapRow {
  constructor(slice2) {
    this[kKeys] = new Vector([slice2.children[0]]).memoize();
    this[kVals] = slice2.children[1];
    return new Proxy(this, new MapRowProxyHandler());
  }
  /** @ignore */
  get [kKeysAsStrings]() {
    return this[_kKeysAsStrings] || (this[_kKeysAsStrings] = Array.from(this[kKeys].toArray(), String));
  }
  [Symbol.iterator]() {
    return new MapRowIterator(this[kKeys], this[kVals]);
  }
  get size() {
    return this[kKeys].length;
  }
  toArray() {
    return Object.values(this.toJSON());
  }
  toJSON() {
    const keys2 = this[kKeys];
    const vals = this[kVals];
    const json2 = {};
    for (let i = -1, n = keys2.length; ++i < n; ) {
      json2[keys2.get(i)] = instance$4.visit(vals, i);
    }
    return json2;
  }
  toString() {
    return `{${[...this].map(([key2, val]) => `${valueToString(key2)}: ${valueToString(val)}`).join(", ")}}`;
  }
  [/* @__PURE__ */ Symbol.for("nodejs.util.inspect.custom")]() {
    return this.toString();
  }
}
class MapRowIterator {
  constructor(keys2, vals) {
    this.keys = keys2;
    this.vals = vals;
    this.keyIndex = 0;
    this.numKeys = keys2.length;
  }
  [Symbol.iterator]() {
    return this;
  }
  next() {
    const i = this.keyIndex;
    if (i === this.numKeys) {
      return { done: true, value: null };
    }
    this.keyIndex++;
    return {
      done: false,
      value: [
        this.keys.get(i),
        instance$4.visit(this.vals, i)
      ]
    };
  }
}
class MapRowProxyHandler {
  isExtensible() {
    return false;
  }
  deleteProperty() {
    return false;
  }
  preventExtensions() {
    return true;
  }
  ownKeys(row) {
    return row[kKeysAsStrings];
  }
  has(row, key2) {
    return row[kKeysAsStrings].includes(key2);
  }
  getOwnPropertyDescriptor(row, key2) {
    const idx = row[kKeysAsStrings].indexOf(key2);
    if (idx !== -1) {
      return { writable: true, enumerable: true, configurable: true };
    }
    return;
  }
  get(row, key2) {
    if (Reflect.has(row, key2)) {
      return row[key2];
    }
    const idx = row[kKeysAsStrings].indexOf(key2);
    if (idx !== -1) {
      const val = instance$4.visit(Reflect.get(row, kVals), idx);
      Reflect.set(row, key2, val);
      return val;
    }
  }
  set(row, key2, val) {
    const idx = row[kKeysAsStrings].indexOf(key2);
    if (idx !== -1) {
      instance$5.visit(Reflect.get(row, kVals), idx, val);
      return Reflect.set(row, key2, val);
    } else if (Reflect.has(row, key2)) {
      return Reflect.set(row, key2, val);
    }
    return false;
  }
}
Object.defineProperties(MapRow.prototype, {
  [Symbol.toStringTag]: { enumerable: false, configurable: false, value: "Row" },
  [kKeys]: { writable: true, enumerable: false, configurable: false, value: null },
  [kVals]: { writable: true, enumerable: false, configurable: false, value: null },
  [_kKeysAsStrings]: { writable: true, enumerable: false, configurable: false, value: null }
});
let tmp;
function clampRange(source2, begin, end, then) {
  const { length: len = 0 } = source2;
  let lhs = typeof begin !== "number" ? 0 : begin;
  let rhs = typeof end !== "number" ? len : end;
  lhs < 0 && (lhs = (lhs % len + len) % len);
  rhs < 0 && (rhs = (rhs % len + len) % len);
  rhs < lhs && (tmp = lhs, lhs = rhs, rhs = tmp);
  rhs > len && (rhs = len);
  return then ? then(source2, lhs, rhs) : [lhs, rhs];
}
const wrapIndex = (index, len) => index < 0 ? len + index : index;
const isNaNFast = (value2) => value2 !== value2;
function createElementComparator(search) {
  const typeofSearch = typeof search;
  if (typeofSearch !== "object" || search === null) {
    if (isNaNFast(search)) {
      return isNaNFast;
    }
    return (value2) => value2 === search;
  }
  if (search instanceof Date) {
    const valueOfSearch = search.valueOf();
    return (value2) => value2 instanceof Date ? value2.valueOf() === valueOfSearch : false;
  }
  if (ArrayBuffer.isView(search)) {
    return (value2) => value2 ? compareArrayLike(search, value2) : false;
  }
  if (search instanceof Map) {
    return createMapComparator(search);
  }
  if (Array.isArray(search)) {
    return createArrayLikeComparator(search);
  }
  if (search instanceof Vector) {
    return createVectorComparator(search);
  }
  return createObjectComparator(search, true);
}
function createArrayLikeComparator(lhs) {
  const comparators = [];
  for (let i = -1, n = lhs.length; ++i < n; ) {
    comparators[i] = createElementComparator(lhs[i]);
  }
  return createSubElementsComparator(comparators);
}
function createMapComparator(lhs) {
  let i = -1;
  const comparators = [];
  for (const v of lhs.values())
    comparators[++i] = createElementComparator(v);
  return createSubElementsComparator(comparators);
}
function createVectorComparator(lhs) {
  const comparators = [];
  for (let i = -1, n = lhs.length; ++i < n; ) {
    comparators[i] = createElementComparator(lhs.get(i));
  }
  return createSubElementsComparator(comparators);
}
function createObjectComparator(lhs, allowEmpty = false) {
  const keys2 = Object.keys(lhs);
  if (!allowEmpty && keys2.length === 0) {
    return () => false;
  }
  const comparators = [];
  for (let i = -1, n = keys2.length; ++i < n; ) {
    comparators[i] = createElementComparator(lhs[keys2[i]]);
  }
  return createSubElementsComparator(comparators, keys2);
}
function createSubElementsComparator(comparators, keys2) {
  return (rhs) => {
    if (!rhs || typeof rhs !== "object") {
      return false;
    }
    switch (rhs.constructor) {
      case Array:
        return compareArray(comparators, rhs);
      case Map:
        return compareObject(comparators, rhs, rhs.keys());
      case MapRow:
      case StructRow:
      case Object:
      case void 0:
        return compareObject(comparators, rhs, keys2 || Object.keys(rhs));
    }
    return rhs instanceof Vector ? compareVector(comparators, rhs) : false;
  };
}
function compareArray(comparators, arr) {
  const n = comparators.length;
  if (arr.length !== n) {
    return false;
  }
  for (let i = -1; ++i < n; ) {
    if (!comparators[i](arr[i])) {
      return false;
    }
  }
  return true;
}
function compareVector(comparators, vec) {
  const n = comparators.length;
  if (vec.length !== n) {
    return false;
  }
  for (let i = -1; ++i < n; ) {
    if (!comparators[i](vec.get(i))) {
      return false;
    }
  }
  return true;
}
function compareObject(comparators, obj, keys2) {
  const lKeyItr = keys2[Symbol.iterator]();
  const rKeyItr = obj instanceof Map ? obj.keys() : Object.keys(obj)[Symbol.iterator]();
  const rValItr = obj instanceof Map ? obj.values() : Object.values(obj)[Symbol.iterator]();
  let i = 0;
  const n = comparators.length;
  let rVal = rValItr.next();
  let lKey = lKeyItr.next();
  let rKey = rKeyItr.next();
  for (; i < n && !lKey.done && !rKey.done && !rVal.done; ++i, lKey = lKeyItr.next(), rKey = rKeyItr.next(), rVal = rValItr.next()) {
    if (lKey.value !== rKey.value || !comparators[i](rVal.value)) {
      break;
    }
  }
  if (i === n && lKey.done && rKey.done && rVal.done) {
    return true;
  }
  lKeyItr.return && lKeyItr.return();
  rKeyItr.return && rKeyItr.return();
  rValItr.return && rValItr.return();
  return false;
}
function getBool(_data, _index, byte, bit) {
  return (byte & 1 << bit) !== 0;
}
function getBit(_data, _index, byte, bit) {
  return (byte & 1 << bit) >> bit;
}
function truncateBitmap(offset2, length2, bitmap2) {
  const alignedSize = bitmap2.byteLength + 7 & -8;
  if (offset2 > 0 || bitmap2.byteLength < alignedSize) {
    const bytes = new Uint8Array(alignedSize);
    bytes.set(offset2 % 8 === 0 ? bitmap2.subarray(offset2 >> 3) : (
      // Otherwise iterate each bit from the offset and return a new one
      packBools(new BitIterator(bitmap2, offset2, length2, null, getBool)).subarray(0, alignedSize)
    ));
    return bytes;
  }
  return bitmap2;
}
function packBools(values2) {
  const xs = [];
  let i = 0, bit = 0, byte = 0;
  for (const value2 of values2) {
    value2 && (byte |= 1 << bit);
    if (++bit === 8) {
      xs[i++] = byte;
      byte = bit = 0;
    }
  }
  if (i === 0 || bit > 0) {
    xs[i++] = byte;
  }
  const b = new Uint8Array(xs.length + 7 & -8);
  b.set(xs);
  return b;
}
class BitIterator {
  constructor(bytes, begin, length2, context, get2) {
    this.bytes = bytes;
    this.length = length2;
    this.context = context;
    this.get = get2;
    this.bit = begin % 8;
    this.byteIndex = begin >> 3;
    this.byte = bytes[this.byteIndex++];
    this.index = 0;
  }
  next() {
    if (this.index < this.length) {
      if (this.bit === 8) {
        this.bit = 0;
        this.byte = this.bytes[this.byteIndex++];
      }
      return {
        value: this.get(this.context, this.index++, this.byte, this.bit++)
      };
    }
    return { done: true, value: null };
  }
  [Symbol.iterator]() {
    return this;
  }
}
function popcnt_bit_range(data2, lhs, rhs) {
  if (rhs - lhs <= 0) {
    return 0;
  }
  if (rhs - lhs < 8) {
    let sum = 0;
    for (const bit of new BitIterator(data2, lhs, rhs - lhs, data2, getBit)) {
      sum += bit;
    }
    return sum;
  }
  const rhsInside = rhs >> 3 << 3;
  const lhsInside = lhs + (lhs % 8 === 0 ? 0 : 8 - lhs % 8);
  return (
    // Get the popcnt of bits between the left hand side, and the next highest multiple of 8
    popcnt_bit_range(data2, lhs, lhsInside) + // Get the popcnt of bits between the right hand side, and the next lowest multiple of 8
    popcnt_bit_range(data2, rhsInside, rhs) + // Get the popcnt of all bits between the left and right hand sides' multiples of 8
    popcnt_array(data2, lhsInside >> 3, rhsInside - lhsInside >> 3)
  );
}
function popcnt_array(arr, byteOffset, byteLength) {
  let cnt = 0, pos = Math.trunc(byteOffset);
  const view = new DataView(arr.buffer, arr.byteOffset, arr.byteLength);
  const len = byteLength === void 0 ? arr.byteLength : pos + byteLength;
  while (len - pos >= 4) {
    cnt += popcnt_uint32(view.getUint32(pos));
    pos += 4;
  }
  while (len - pos >= 2) {
    cnt += popcnt_uint32(view.getUint16(pos));
    pos += 2;
  }
  while (len - pos >= 1) {
    cnt += popcnt_uint32(view.getUint8(pos));
    pos += 1;
  }
  return cnt;
}
function popcnt_uint32(uint322) {
  let i = Math.trunc(uint322);
  i = i - (i >>> 1 & 1431655765);
  i = (i & 858993459) + (i >>> 2 & 858993459);
  return (i + (i >>> 4) & 252645135) * 16843009 >>> 24;
}
const kUnknownNullCount = -1;
class Data {
  get typeId() {
    return this.type.typeId;
  }
  get ArrayType() {
    return this.type.ArrayType;
  }
  get buffers() {
    return [this.valueOffsets, this.values, this.nullBitmap, this.typeIds];
  }
  get nullable() {
    if (this._nullCount !== 0) {
      const { type } = this;
      if (DataType.isSparseUnion(type)) {
        return this.children.some((child) => child.nullable);
      } else if (DataType.isDenseUnion(type)) {
        return this.children.some((child) => child.nullable);
      }
      return this.nullBitmap && this.nullBitmap.byteLength > 0;
    }
    return true;
  }
  get byteLength() {
    let byteLength = 0;
    const { valueOffsets, values: values2, nullBitmap, typeIds } = this;
    valueOffsets && (byteLength += valueOffsets.byteLength);
    values2 && (byteLength += values2.byteLength);
    nullBitmap && (byteLength += nullBitmap.byteLength);
    typeIds && (byteLength += typeIds.byteLength);
    return this.children.reduce((byteLength2, child) => byteLength2 + child.byteLength, byteLength);
  }
  get nullCount() {
    if (DataType.isUnion(this.type)) {
      return this.children.reduce((nullCount2, child) => nullCount2 + child.nullCount, 0);
    }
    let nullCount = this._nullCount;
    let nullBitmap;
    if (nullCount <= kUnknownNullCount && (nullBitmap = this.nullBitmap)) {
      this._nullCount = nullCount = nullBitmap.length === 0 ? (
        // no null bitmap, so all values are valid
        0
      ) : this.length - popcnt_bit_range(nullBitmap, this.offset, this.offset + this.length);
    }
    return nullCount;
  }
  constructor(type, offset2, length2, nullCount, buffers, children = [], dictionary2) {
    this.type = type;
    this.children = children;
    this.dictionary = dictionary2;
    this.offset = Math.floor(Math.max(offset2 || 0, 0));
    this.length = Math.floor(Math.max(length2 || 0, 0));
    this._nullCount = Math.floor(Math.max(nullCount || 0, -1));
    let buffer2;
    if (buffers instanceof Data) {
      this.stride = buffers.stride;
      this.values = buffers.values;
      this.typeIds = buffers.typeIds;
      this.nullBitmap = buffers.nullBitmap;
      this.valueOffsets = buffers.valueOffsets;
    } else {
      this.stride = strideForType(type);
      if (buffers) {
        (buffer2 = buffers[0]) && (this.valueOffsets = buffer2);
        (buffer2 = buffers[1]) && (this.values = buffer2);
        (buffer2 = buffers[2]) && (this.nullBitmap = buffer2);
        (buffer2 = buffers[3]) && (this.typeIds = buffer2);
      }
    }
  }
  getValid(index) {
    const { type } = this;
    if (DataType.isUnion(type)) {
      const union2 = type;
      const child = this.children[union2.typeIdToChildIndex[this.typeIds[index]]];
      const indexInChild = union2.mode === UnionMode$1.Dense ? this.valueOffsets[index] : index;
      return child.getValid(indexInChild);
    }
    if (this.nullable && this.nullCount > 0) {
      const pos = this.offset + index;
      const val = this.nullBitmap[pos >> 3];
      return (val & 1 << pos % 8) !== 0;
    }
    return true;
  }
  setValid(index, value2) {
    let prev;
    const { type } = this;
    if (DataType.isUnion(type)) {
      const union2 = type;
      const child = this.children[union2.typeIdToChildIndex[this.typeIds[index]]];
      const indexInChild = union2.mode === UnionMode$1.Dense ? this.valueOffsets[index] : index;
      prev = child.getValid(indexInChild);
      child.setValid(indexInChild, value2);
    } else {
      let { nullBitmap } = this;
      const { offset: offset2, length: length2 } = this;
      const idx = offset2 + index;
      const mask = 1 << idx % 8;
      const byteOffset = idx >> 3;
      if (!nullBitmap || nullBitmap.byteLength <= byteOffset) {
        nullBitmap = new Uint8Array((offset2 + length2 + 63 & -64) >> 3).fill(255);
        if (this.nullCount > 0) {
          nullBitmap.set(truncateBitmap(offset2, length2, this.nullBitmap), 0);
          Object.assign(this, { nullBitmap });
        } else {
          Object.assign(this, { nullBitmap, _nullCount: 0 });
        }
      }
      const byte = nullBitmap[byteOffset];
      prev = (byte & mask) !== 0;
      nullBitmap[byteOffset] = value2 ? byte | mask : byte & ~mask;
    }
    if (prev !== !!value2) {
      this._nullCount = this.nullCount + (value2 ? -1 : 1);
    }
    return value2;
  }
  clone(type = this.type, offset2 = this.offset, length2 = this.length, nullCount = this._nullCount, buffers = this, children = this.children) {
    return new Data(type, offset2, length2, nullCount, buffers, children, this.dictionary);
  }
  slice(offset2, length2) {
    const { stride, typeId, children } = this;
    const nullCount = +(this._nullCount === 0) - 1;
    const childStride = typeId === 16 ? stride : 1;
    const buffers = this._sliceBuffers(offset2, length2, stride, typeId);
    return this.clone(
      this.type,
      this.offset + offset2,
      length2,
      nullCount,
      buffers,
      // Don't slice children if we have value offsets (the variable-width types)
      children.length === 0 || this.valueOffsets ? children : this._sliceChildren(children, childStride * offset2, childStride * length2)
    );
  }
  _changeLengthAndBackfillNullBitmap(newLength) {
    if (this.typeId === Type$1.Null) {
      return this.clone(this.type, 0, newLength, 0);
    }
    const { length: length2, nullCount } = this;
    const bitmap2 = new Uint8Array((newLength + 63 & -64) >> 3).fill(255, 0, length2 >> 3);
    bitmap2[length2 >> 3] = (1 << length2 - (length2 & -8)) - 1;
    if (nullCount > 0) {
      bitmap2.set(truncateBitmap(this.offset, length2, this.nullBitmap), 0);
    }
    const buffers = this.buffers;
    buffers[BufferType.VALIDITY] = bitmap2;
    return this.clone(this.type, 0, newLength, nullCount + (newLength - length2), buffers);
  }
  _sliceBuffers(offset2, length2, stride, typeId) {
    let arr;
    const { buffers } = this;
    (arr = buffers[BufferType.TYPE]) && (buffers[BufferType.TYPE] = arr.subarray(offset2, offset2 + length2));
    (arr = buffers[BufferType.OFFSET]) && (buffers[BufferType.OFFSET] = arr.subarray(offset2, offset2 + length2 + 1)) || // Otherwise if no offsets, slice the data buffer. Don't slice the data vector for Booleans, since the offset goes by bits not bytes
    (arr = buffers[BufferType.DATA]) && (buffers[BufferType.DATA] = typeId === 6 ? arr : arr.subarray(stride * offset2, stride * (offset2 + length2)));
    return buffers;
  }
  _sliceChildren(children, offset2, length2) {
    return children.map((child) => child.slice(offset2, length2));
  }
}
Data.prototype.children = Object.freeze([]);
class MakeDataVisitor extends Visitor {
  visit(props) {
    return this.getVisitFn(props["type"]).call(this, props);
  }
  visitNull(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0, ["length"]: length2 = 0 } = props;
    return new Data(type, offset2, length2, length2);
  }
  visitBool(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length2 = data2.length >> 3, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap]);
  }
  visitInt(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length2 = data2.length, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap]);
  }
  visitFloat(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length2 = data2.length, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap]);
  }
  visitUtf8(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const data2 = toUint8Array(props["data"]);
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toInt32Array(props["valueOffsets"]);
    const { ["length"]: length2 = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [valueOffsets, data2, nullBitmap]);
  }
  visitLargeUtf8(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const data2 = toUint8Array(props["data"]);
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toBigInt64Array(props["valueOffsets"]);
    const { ["length"]: length2 = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [valueOffsets, data2, nullBitmap]);
  }
  visitBinary(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const data2 = toUint8Array(props["data"]);
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toInt32Array(props["valueOffsets"]);
    const { ["length"]: length2 = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [valueOffsets, data2, nullBitmap]);
  }
  visitLargeBinary(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const data2 = toUint8Array(props["data"]);
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toBigInt64Array(props["valueOffsets"]);
    const { ["length"]: length2 = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [valueOffsets, data2, nullBitmap]);
  }
  visitFixedSizeBinary(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length2 = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap]);
  }
  visitDate(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length2 = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap]);
  }
  visitTimestamp(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length2 = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap]);
  }
  visitTime(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length2 = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap]);
  }
  visitDecimal(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length2 = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap]);
  }
  visitList(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0, ["child"]: child } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toInt32Array(props["valueOffsets"]);
    const { ["length"]: length2 = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [valueOffsets, void 0, nullBitmap], [child]);
  }
  visitStruct(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0, ["children"]: children = [] } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const { length: length2 = children.reduce((len, { length: length3 }) => Math.max(len, length3), 0), nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, void 0, nullBitmap], children);
  }
  visitUnion(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0, ["children"]: children = [] } = props;
    const typeIds = toArrayBufferView(type.ArrayType, props["typeIds"]);
    const { ["length"]: length2 = typeIds.length, ["nullCount"]: nullCount = -1 } = props;
    if (DataType.isSparseUnion(type)) {
      return new Data(type, offset2, length2, nullCount, [void 0, void 0, void 0, typeIds], children);
    }
    const valueOffsets = toInt32Array(props["valueOffsets"]);
    return new Data(type, offset2, length2, nullCount, [valueOffsets, void 0, void 0, typeIds], children);
  }
  visitDictionary(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.indices.ArrayType, props["data"]);
    const { ["dictionary"]: dictionary2 = new Vector([new MakeDataVisitor().visit({ type: type.dictionary })]) } = props;
    const { ["length"]: length2 = data2.length, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap], [], dictionary2);
  }
  visitInterval(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length2 = data2.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap]);
  }
  visitDuration(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0 } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const data2 = toArrayBufferView(type.ArrayType, props["data"]);
    const { ["length"]: length2 = data2.length, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, data2, nullBitmap]);
  }
  visitFixedSizeList(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0, ["child"]: child = new MakeDataVisitor().visit({ type: type.valueType }) } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const { ["length"]: length2 = child.length / strideForType(type), ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [void 0, void 0, nullBitmap], [child]);
  }
  visitMap(props) {
    const { ["type"]: type, ["offset"]: offset2 = 0, ["child"]: child = new MakeDataVisitor().visit({ type: type.childType }) } = props;
    const nullBitmap = toUint8Array(props["nullBitmap"]);
    const valueOffsets = toInt32Array(props["valueOffsets"]);
    const { ["length"]: length2 = valueOffsets.length - 1, ["nullCount"]: nullCount = props["nullBitmap"] ? -1 : 0 } = props;
    return new Data(type, offset2, length2, nullCount, [valueOffsets, void 0, nullBitmap], [child]);
  }
}
const makeDataVisitor = new MakeDataVisitor();
function makeData(props) {
  return makeDataVisitor.visit(props);
}
class ChunkedIterator {
  constructor(numChunks = 0, getChunkIterator) {
    this.numChunks = numChunks;
    this.getChunkIterator = getChunkIterator;
    this.chunkIndex = 0;
    this.chunkIterator = this.getChunkIterator(0);
  }
  next() {
    while (this.chunkIndex < this.numChunks) {
      const next = this.chunkIterator.next();
      if (!next.done) {
        return next;
      }
      if (++this.chunkIndex < this.numChunks) {
        this.chunkIterator = this.getChunkIterator(this.chunkIndex);
      }
    }
    return { done: true, value: null };
  }
  [Symbol.iterator]() {
    return this;
  }
}
function computeChunkNullable(chunks) {
  return chunks.some((chunk) => chunk.nullable);
}
function computeChunkNullCounts(chunks) {
  return chunks.reduce((nullCount, chunk) => nullCount + chunk.nullCount, 0);
}
function computeChunkOffsets(chunks) {
  return chunks.reduce((offsets, chunk, index) => {
    offsets[index + 1] = offsets[index] + chunk.length;
    return offsets;
  }, new Uint32Array(chunks.length + 1));
}
function sliceChunks(chunks, offsets, begin, end) {
  const slices = [];
  for (let i = -1, n = chunks.length; ++i < n; ) {
    const chunk = chunks[i];
    const offset2 = offsets[i];
    const { length: length2 } = chunk;
    if (offset2 >= end) {
      break;
    }
    if (begin >= offset2 + length2) {
      continue;
    }
    if (offset2 >= begin && offset2 + length2 <= end) {
      slices.push(chunk);
      continue;
    }
    const from2 = Math.max(0, begin - offset2);
    const to = Math.min(end - offset2, length2);
    slices.push(chunk.slice(from2, to - from2));
  }
  if (slices.length === 0) {
    slices.push(chunks[0].slice(0, 0));
  }
  return slices;
}
function binarySearch(chunks, offsets, idx, fn) {
  let lhs = 0, mid = 0, rhs = offsets.length - 1;
  do {
    if (lhs >= rhs - 1) {
      return idx < offsets[rhs] ? fn(chunks, lhs, idx - offsets[lhs]) : null;
    }
    mid = lhs + Math.trunc((rhs - lhs) * 0.5);
    idx < offsets[mid] ? rhs = mid : lhs = mid;
  } while (lhs < rhs);
}
function isChunkedValid(data2, index) {
  return data2.getValid(index);
}
function wrapChunkedCall1(fn) {
  function chunkedFn(chunks, i, j) {
    return fn(chunks[i], j);
  }
  return function(index) {
    const data2 = this.data;
    return binarySearch(data2, this._offsets, index, chunkedFn);
  };
}
function wrapChunkedCall2(fn) {
  let _2;
  function chunkedFn(chunks, i, j) {
    return fn(chunks[i], j, _2);
  }
  return function(index, value2) {
    const data2 = this.data;
    _2 = value2;
    const result2 = binarySearch(data2, this._offsets, index, chunkedFn);
    _2 = void 0;
    return result2;
  };
}
function wrapChunkedIndexOf(indexOf) {
  let _1;
  function chunkedIndexOf(data2, chunkIndex, fromIndex) {
    let begin = fromIndex, index = 0, total = 0;
    for (let i = chunkIndex - 1, n = data2.length; ++i < n; ) {
      const chunk = data2[i];
      if (~(index = indexOf(chunk, _1, begin))) {
        return total + index;
      }
      begin = 0;
      total += chunk.length;
    }
    return -1;
  }
  return function(element, offset2) {
    _1 = element;
    const data2 = this.data;
    const result2 = typeof offset2 !== "number" ? chunkedIndexOf(data2, 0, 0) : binarySearch(data2, this._offsets, offset2, chunkedIndexOf);
    _1 = void 0;
    return result2;
  };
}
class IndexOfVisitor extends Visitor {
}
function nullIndexOf(data2, searchElement) {
  return searchElement === null && data2.length > 0 ? 0 : -1;
}
function indexOfNull(data2, fromIndex) {
  const { nullBitmap } = data2;
  if (!nullBitmap || data2.nullCount <= 0) {
    return -1;
  }
  let i = 0;
  for (const isValid2 of new BitIterator(nullBitmap, data2.offset + (fromIndex || 0), data2.length, nullBitmap, getBool)) {
    if (!isValid2) {
      return i;
    }
    ++i;
  }
  return -1;
}
function indexOfValue(data2, searchElement, fromIndex) {
  if (searchElement === void 0) {
    return -1;
  }
  if (searchElement === null) {
    switch (data2.typeId) {
      // Unions don't have a nullBitmap of its own, so compare the `searchElement` to `get()`.
      case Type$1.Union:
        break;
      // Dictionaries do have a nullBitmap, but their dictionary could also have null elements.
      case Type$1.Dictionary:
        break;
      // All other types can iterate the null bitmap
      default:
        return indexOfNull(data2, fromIndex);
    }
  }
  const get2 = instance$4.getVisitFn(data2);
  const compare2 = createElementComparator(searchElement);
  for (let i = (fromIndex || 0) - 1, n = data2.length; ++i < n; ) {
    if (compare2(get2(data2, i))) {
      return i;
    }
  }
  return -1;
}
function indexOfUnion(data2, searchElement, fromIndex) {
  const get2 = instance$4.getVisitFn(data2);
  const compare2 = createElementComparator(searchElement);
  for (let i = (fromIndex || 0) - 1, n = data2.length; ++i < n; ) {
    if (compare2(get2(data2, i))) {
      return i;
    }
  }
  return -1;
}
IndexOfVisitor.prototype.visitNull = nullIndexOf;
IndexOfVisitor.prototype.visitBool = indexOfValue;
IndexOfVisitor.prototype.visitInt = indexOfValue;
IndexOfVisitor.prototype.visitInt8 = indexOfValue;
IndexOfVisitor.prototype.visitInt16 = indexOfValue;
IndexOfVisitor.prototype.visitInt32 = indexOfValue;
IndexOfVisitor.prototype.visitInt64 = indexOfValue;
IndexOfVisitor.prototype.visitUint8 = indexOfValue;
IndexOfVisitor.prototype.visitUint16 = indexOfValue;
IndexOfVisitor.prototype.visitUint32 = indexOfValue;
IndexOfVisitor.prototype.visitUint64 = indexOfValue;
IndexOfVisitor.prototype.visitFloat = indexOfValue;
IndexOfVisitor.prototype.visitFloat16 = indexOfValue;
IndexOfVisitor.prototype.visitFloat32 = indexOfValue;
IndexOfVisitor.prototype.visitFloat64 = indexOfValue;
IndexOfVisitor.prototype.visitUtf8 = indexOfValue;
IndexOfVisitor.prototype.visitLargeUtf8 = indexOfValue;
IndexOfVisitor.prototype.visitBinary = indexOfValue;
IndexOfVisitor.prototype.visitLargeBinary = indexOfValue;
IndexOfVisitor.prototype.visitFixedSizeBinary = indexOfValue;
IndexOfVisitor.prototype.visitDate = indexOfValue;
IndexOfVisitor.prototype.visitDateDay = indexOfValue;
IndexOfVisitor.prototype.visitDateMillisecond = indexOfValue;
IndexOfVisitor.prototype.visitTimestamp = indexOfValue;
IndexOfVisitor.prototype.visitTimestampSecond = indexOfValue;
IndexOfVisitor.prototype.visitTimestampMillisecond = indexOfValue;
IndexOfVisitor.prototype.visitTimestampMicrosecond = indexOfValue;
IndexOfVisitor.prototype.visitTimestampNanosecond = indexOfValue;
IndexOfVisitor.prototype.visitTime = indexOfValue;
IndexOfVisitor.prototype.visitTimeSecond = indexOfValue;
IndexOfVisitor.prototype.visitTimeMillisecond = indexOfValue;
IndexOfVisitor.prototype.visitTimeMicrosecond = indexOfValue;
IndexOfVisitor.prototype.visitTimeNanosecond = indexOfValue;
IndexOfVisitor.prototype.visitDecimal = indexOfValue;
IndexOfVisitor.prototype.visitList = indexOfValue;
IndexOfVisitor.prototype.visitStruct = indexOfValue;
IndexOfVisitor.prototype.visitUnion = indexOfValue;
IndexOfVisitor.prototype.visitDenseUnion = indexOfUnion;
IndexOfVisitor.prototype.visitSparseUnion = indexOfUnion;
IndexOfVisitor.prototype.visitDictionary = indexOfValue;
IndexOfVisitor.prototype.visitInterval = indexOfValue;
IndexOfVisitor.prototype.visitIntervalDayTime = indexOfValue;
IndexOfVisitor.prototype.visitIntervalYearMonth = indexOfValue;
IndexOfVisitor.prototype.visitIntervalMonthDayNano = indexOfValue;
IndexOfVisitor.prototype.visitDuration = indexOfValue;
IndexOfVisitor.prototype.visitDurationSecond = indexOfValue;
IndexOfVisitor.prototype.visitDurationMillisecond = indexOfValue;
IndexOfVisitor.prototype.visitDurationMicrosecond = indexOfValue;
IndexOfVisitor.prototype.visitDurationNanosecond = indexOfValue;
IndexOfVisitor.prototype.visitFixedSizeList = indexOfValue;
IndexOfVisitor.prototype.visitMap = indexOfValue;
const instance$3 = new IndexOfVisitor();
class IteratorVisitor extends Visitor {
}
function vectorIterator(vector) {
  const { type } = vector;
  if (vector.nullCount === 0 && vector.stride === 1 && // Don't defer to native iterator for timestamps since Numbers are expected
  // (DataType.isTimestamp(type)) && type.unit === TimeUnit.MILLISECOND ||
  (DataType.isInt(type) && type.bitWidth !== 64 || DataType.isTime(type) && type.bitWidth !== 64 || DataType.isFloat(type) && type.precision !== Precision$1.HALF)) {
    return new ChunkedIterator(vector.data.length, (chunkIndex) => {
      const data2 = vector.data[chunkIndex];
      return data2.values.subarray(0, data2.length)[Symbol.iterator]();
    });
  }
  let offset2 = 0;
  return new ChunkedIterator(vector.data.length, (chunkIndex) => {
    const data2 = vector.data[chunkIndex];
    const length2 = data2.length;
    const inner = vector.slice(offset2, offset2 + length2);
    offset2 += length2;
    return new VectorIterator(inner);
  });
}
class VectorIterator {
  constructor(vector) {
    this.vector = vector;
    this.index = 0;
  }
  next() {
    if (this.index < this.vector.length) {
      return {
        value: this.vector.get(this.index++)
      };
    }
    return { done: true, value: null };
  }
  [Symbol.iterator]() {
    return this;
  }
}
IteratorVisitor.prototype.visitNull = vectorIterator;
IteratorVisitor.prototype.visitBool = vectorIterator;
IteratorVisitor.prototype.visitInt = vectorIterator;
IteratorVisitor.prototype.visitInt8 = vectorIterator;
IteratorVisitor.prototype.visitInt16 = vectorIterator;
IteratorVisitor.prototype.visitInt32 = vectorIterator;
IteratorVisitor.prototype.visitInt64 = vectorIterator;
IteratorVisitor.prototype.visitUint8 = vectorIterator;
IteratorVisitor.prototype.visitUint16 = vectorIterator;
IteratorVisitor.prototype.visitUint32 = vectorIterator;
IteratorVisitor.prototype.visitUint64 = vectorIterator;
IteratorVisitor.prototype.visitFloat = vectorIterator;
IteratorVisitor.prototype.visitFloat16 = vectorIterator;
IteratorVisitor.prototype.visitFloat32 = vectorIterator;
IteratorVisitor.prototype.visitFloat64 = vectorIterator;
IteratorVisitor.prototype.visitUtf8 = vectorIterator;
IteratorVisitor.prototype.visitLargeUtf8 = vectorIterator;
IteratorVisitor.prototype.visitBinary = vectorIterator;
IteratorVisitor.prototype.visitLargeBinary = vectorIterator;
IteratorVisitor.prototype.visitFixedSizeBinary = vectorIterator;
IteratorVisitor.prototype.visitDate = vectorIterator;
IteratorVisitor.prototype.visitDateDay = vectorIterator;
IteratorVisitor.prototype.visitDateMillisecond = vectorIterator;
IteratorVisitor.prototype.visitTimestamp = vectorIterator;
IteratorVisitor.prototype.visitTimestampSecond = vectorIterator;
IteratorVisitor.prototype.visitTimestampMillisecond = vectorIterator;
IteratorVisitor.prototype.visitTimestampMicrosecond = vectorIterator;
IteratorVisitor.prototype.visitTimestampNanosecond = vectorIterator;
IteratorVisitor.prototype.visitTime = vectorIterator;
IteratorVisitor.prototype.visitTimeSecond = vectorIterator;
IteratorVisitor.prototype.visitTimeMillisecond = vectorIterator;
IteratorVisitor.prototype.visitTimeMicrosecond = vectorIterator;
IteratorVisitor.prototype.visitTimeNanosecond = vectorIterator;
IteratorVisitor.prototype.visitDecimal = vectorIterator;
IteratorVisitor.prototype.visitList = vectorIterator;
IteratorVisitor.prototype.visitStruct = vectorIterator;
IteratorVisitor.prototype.visitUnion = vectorIterator;
IteratorVisitor.prototype.visitDenseUnion = vectorIterator;
IteratorVisitor.prototype.visitSparseUnion = vectorIterator;
IteratorVisitor.prototype.visitDictionary = vectorIterator;
IteratorVisitor.prototype.visitInterval = vectorIterator;
IteratorVisitor.prototype.visitIntervalDayTime = vectorIterator;
IteratorVisitor.prototype.visitIntervalYearMonth = vectorIterator;
IteratorVisitor.prototype.visitIntervalMonthDayNano = vectorIterator;
IteratorVisitor.prototype.visitDuration = vectorIterator;
IteratorVisitor.prototype.visitDurationSecond = vectorIterator;
IteratorVisitor.prototype.visitDurationMillisecond = vectorIterator;
IteratorVisitor.prototype.visitDurationMicrosecond = vectorIterator;
IteratorVisitor.prototype.visitDurationNanosecond = vectorIterator;
IteratorVisitor.prototype.visitFixedSizeList = vectorIterator;
IteratorVisitor.prototype.visitMap = vectorIterator;
const instance$2 = new IteratorVisitor();
var _a$2;
const visitorsByTypeId = {};
const vectorPrototypesByTypeId = {};
class Vector {
  constructor(input) {
    var _b2, _c2, _d2;
    const data2 = input[0] instanceof Vector ? input.flatMap((x) => x.data) : input;
    if (data2.length === 0 || data2.some((x) => !(x instanceof Data))) {
      throw new TypeError("Vector constructor expects an Array of Data instances.");
    }
    const type = (_b2 = data2[0]) === null || _b2 === void 0 ? void 0 : _b2.type;
    switch (data2.length) {
      case 0:
        this._offsets = [0];
        break;
      case 1: {
        const { get: get2, set, indexOf } = visitorsByTypeId[type.typeId];
        const unchunkedData = data2[0];
        this.isValid = (index) => isChunkedValid(unchunkedData, index);
        this.get = (index) => get2(unchunkedData, index);
        this.set = (index, value2) => set(unchunkedData, index, value2);
        this.indexOf = (index) => indexOf(unchunkedData, index);
        this._offsets = [0, unchunkedData.length];
        break;
      }
      default:
        Object.setPrototypeOf(this, vectorPrototypesByTypeId[type.typeId]);
        this._offsets = computeChunkOffsets(data2);
        break;
    }
    this.data = data2;
    this.type = type;
    this.stride = strideForType(type);
    this.numChildren = (_d2 = (_c2 = type.children) === null || _c2 === void 0 ? void 0 : _c2.length) !== null && _d2 !== void 0 ? _d2 : 0;
    this.length = this._offsets.at(-1);
  }
  /**
   * The aggregate size (in bytes) of this Vector's buffers and/or child Vectors.
   */
  get byteLength() {
    return this.data.reduce((byteLength, data2) => byteLength + data2.byteLength, 0);
  }
  /**
   * Whether this Vector's elements can contain null values.
   */
  get nullable() {
    return computeChunkNullable(this.data);
  }
  /**
   * The number of null elements in this Vector.
   */
  get nullCount() {
    return computeChunkNullCounts(this.data);
  }
  /**
   * The Array or TypedArray constructor used for the JS representation
   *  of the element's values in {@link Vector.prototype.toArray `toArray()`}.
   */
  get ArrayType() {
    return this.type.ArrayType;
  }
  /**
   * The name that should be printed when the Vector is logged in a message.
   */
  get [Symbol.toStringTag]() {
    return `${this.VectorName}<${this.type[Symbol.toStringTag]}>`;
  }
  /**
   * The name of this Vector.
   */
  get VectorName() {
    return `${Type$1[this.type.typeId]}Vector`;
  }
  /**
   * Check whether an element is null.
   * @param index The index at which to read the validity bitmap.
   */
  // @ts-ignore
  isValid(index) {
    return false;
  }
  /**
   * Get an element value by position.
   * @param index The index of the element to read.
   */
  // @ts-ignore
  get(index) {
    return null;
  }
  /**
   * Get an element value by position.
   * @param index The index of the element to read. A negative index will count back from the last element.
   */
  at(index) {
    return this.get(wrapIndex(index, this.length));
  }
  /**
   * Set an element value by position.
   * @param index The index of the element to write.
   * @param value The value to set.
   */
  // @ts-ignore
  set(index, value2) {
    return;
  }
  /**
   * Retrieve the index of the first occurrence of a value in an Vector.
   * @param element The value to locate in the Vector.
   * @param offset The index at which to begin the search. If offset is omitted, the search starts at index 0.
   */
  // @ts-ignore
  indexOf(element, offset2) {
    return -1;
  }
  includes(element, offset2) {
    return this.indexOf(element, offset2) > -1;
  }
  /**
   * Iterator for the Vector's elements.
   */
  [Symbol.iterator]() {
    return instance$2.visit(this);
  }
  /**
   * Combines two or more Vectors of the same type.
   * @param others Additional Vectors to add to the end of this Vector.
   */
  concat(...others) {
    return new Vector(this.data.concat(others.flatMap((x) => x.data).flat(Number.POSITIVE_INFINITY)));
  }
  /**
   * Return a zero-copy sub-section of this Vector.
   * @param start The beginning of the specified portion of the Vector.
   * @param end The end of the specified portion of the Vector. This is exclusive of the element at the index 'end'.
   */
  slice(begin, end) {
    return new Vector(clampRange(this, begin, end, ({ data: data2, _offsets }, begin2, end2) => sliceChunks(data2, _offsets, begin2, end2)));
  }
  toJSON() {
    return [...this];
  }
  /**
   * Return a JavaScript Array or TypedArray of the Vector's elements.
   *
   * @note If this Vector contains a single Data chunk and the Vector's type is a
   *  primitive numeric type corresponding to one of the JavaScript TypedArrays, this
   *  method returns a zero-copy slice of the underlying TypedArray values. If there's
   *  more than one chunk, the resulting TypedArray will be a copy of the data from each
   *  chunk's underlying TypedArray values.
   *
   * @returns An Array or TypedArray of the Vector's elements, based on the Vector's DataType.
   */
  toArray() {
    const { type, data: data2, length: length2, stride, ArrayType } = this;
    switch (type.typeId) {
      case Type$1.Int:
      case Type$1.Float:
      case Type$1.Decimal:
      case Type$1.Time:
      case Type$1.Timestamp:
        switch (data2.length) {
          case 0:
            return new ArrayType();
          case 1:
            return data2[0].values.subarray(0, length2 * stride);
          default:
            return data2.reduce((memo, { values: values2, length: chunk_length }) => {
              memo.array.set(values2.subarray(0, chunk_length * stride), memo.offset);
              memo.offset += chunk_length * stride;
              return memo;
            }, { array: new ArrayType(length2 * stride), offset: 0 }).array;
        }
    }
    return [...this];
  }
  /**
   * Returns a string representation of the Vector.
   *
   * @returns A string representation of the Vector.
   */
  toString() {
    return `[${[...this].join(",")}]`;
  }
  /**
   * Returns a child Vector by name, or null if this Vector has no child with the given name.
   * @param name The name of the child to retrieve.
   */
  getChild(name2) {
    var _b2;
    return this.getChildAt((_b2 = this.type.children) === null || _b2 === void 0 ? void 0 : _b2.findIndex((f) => f.name === name2));
  }
  /**
   * Returns a child Vector by index, or null if this Vector has no child at the supplied index.
   * @param index The index of the child to retrieve.
   */
  getChildAt(index) {
    if (index > -1 && index < this.numChildren) {
      return new Vector(this.data.map(({ children }) => children[index]));
    }
    return null;
  }
  get isMemoized() {
    if (DataType.isDictionary(this.type)) {
      return this.data[0].dictionary.isMemoized;
    }
    return false;
  }
  /**
   * Adds memoization to the Vector's {@link get} method. For dictionary
   * vectors, this method return a vector that memoizes only the dictionary
   * values.
   *
   * Memoization is very useful when decoding a value is expensive such as
   * Utf8. The memoization creates a cache of the size of the Vector and
   * therefore increases memory usage.
   *
   * @returns A new vector that memoizes calls to {@link get}.
   */
  memoize() {
    if (DataType.isDictionary(this.type)) {
      const dictionary2 = new MemoizedVector(this.data[0].dictionary);
      const newData = this.data.map((data2) => {
        const cloned = data2.clone();
        cloned.dictionary = dictionary2;
        return cloned;
      });
      return new Vector(newData);
    }
    return new MemoizedVector(this);
  }
  /**
   * Returns a vector without memoization of the {@link get} method. If this
   * vector is not memoized, this method returns this vector.
   *
   * @returns A new vector without memoization.
   */
  unmemoize() {
    if (DataType.isDictionary(this.type) && this.isMemoized) {
      const dictionary2 = this.data[0].dictionary.unmemoize();
      const newData = this.data.map((data2) => {
        const newData2 = data2.clone();
        newData2.dictionary = dictionary2;
        return newData2;
      });
      return new Vector(newData);
    }
    return this;
  }
}
_a$2 = Symbol.toStringTag;
Vector[_a$2] = ((proto) => {
  proto.type = DataType.prototype;
  proto.data = [];
  proto.length = 0;
  proto.stride = 1;
  proto.numChildren = 0;
  proto._offsets = new Uint32Array([0]);
  proto[Symbol.isConcatSpreadable] = true;
  const typeIds = Object.keys(Type$1).map((T) => Type$1[T]).filter((T) => typeof T === "number" && T !== Type$1.NONE);
  for (const typeId of typeIds) {
    const get2 = instance$4.getVisitFnByTypeId(typeId);
    const set = instance$5.getVisitFnByTypeId(typeId);
    const indexOf = instance$3.getVisitFnByTypeId(typeId);
    visitorsByTypeId[typeId] = { get: get2, set, indexOf };
    vectorPrototypesByTypeId[typeId] = Object.create(proto, {
      ["isValid"]: { value: wrapChunkedCall1(isChunkedValid) },
      ["get"]: { value: wrapChunkedCall1(instance$4.getVisitFnByTypeId(typeId)) },
      ["set"]: { value: wrapChunkedCall2(instance$5.getVisitFnByTypeId(typeId)) },
      ["indexOf"]: { value: wrapChunkedIndexOf(instance$3.getVisitFnByTypeId(typeId)) }
    });
  }
  return "Vector";
})(Vector.prototype);
class MemoizedVector extends Vector {
  constructor(vector) {
    super(vector.data);
    const get2 = this.get;
    const set = this.set;
    const slice2 = this.slice;
    const cache = new Array(this.length);
    Object.defineProperty(this, "get", {
      value(index) {
        const cachedValue = cache[index];
        if (cachedValue !== void 0) {
          return cachedValue;
        }
        const value2 = get2.call(this, index);
        cache[index] = value2;
        return value2;
      }
    });
    Object.defineProperty(this, "set", {
      value(index, value2) {
        set.call(this, index, value2);
        cache[index] = value2;
      }
    });
    Object.defineProperty(this, "slice", {
      value: (begin, end) => new MemoizedVector(slice2.call(this, begin, end))
    });
    Object.defineProperty(this, "isMemoized", { value: true });
    Object.defineProperty(this, "unmemoize", {
      value: () => new Vector(this.data)
    });
    Object.defineProperty(this, "memoize", {
      value: () => this
    });
  }
}
class Block {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  /**
   * Index to the start of the RecordBlock (note this is past the Message header)
   */
  offset() {
    return this.bb.readInt64(this.bb_pos);
  }
  /**
   * Length of the metadata
   */
  metaDataLength() {
    return this.bb.readInt32(this.bb_pos + 8);
  }
  /**
   * Length of the data (this is aligned so there can be a gap between this and
   * the metadata).
   */
  bodyLength() {
    return this.bb.readInt64(this.bb_pos + 16);
  }
  static sizeOf() {
    return 24;
  }
  static createBlock(builder2, offset2, metaDataLength, bodyLength) {
    builder2.prep(8, 24);
    builder2.writeInt64(BigInt(bodyLength !== null && bodyLength !== void 0 ? bodyLength : 0));
    builder2.pad(4);
    builder2.writeInt32(metaDataLength);
    builder2.writeInt64(BigInt(offset2 !== null && offset2 !== void 0 ? offset2 : 0));
    return builder2.offset();
  }
}
class Footer {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsFooter(bb, obj) {
    return (obj || new Footer()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsFooter(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Footer()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  version() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : MetadataVersion.V1;
  }
  schema(obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? (obj || new Schema$1()).__init(this.bb.__indirect(this.bb_pos + offset2), this.bb) : null;
  }
  dictionaries(index, obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? (obj || new Block()).__init(this.bb.__vector(this.bb_pos + offset2) + index * 24, this.bb) : null;
  }
  dictionariesLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  recordBatches(index, obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 10);
    return offset2 ? (obj || new Block()).__init(this.bb.__vector(this.bb_pos + offset2) + index * 24, this.bb) : null;
  }
  recordBatchesLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 10);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  /**
   * User-defined metadata
   */
  customMetadata(index, obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 12);
    return offset2 ? (obj || new KeyValue()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset2) + index * 4), this.bb) : null;
  }
  customMetadataLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 12);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  static startFooter(builder2) {
    builder2.startObject(5);
  }
  static addVersion(builder2, version2) {
    builder2.addFieldInt16(0, version2, MetadataVersion.V1);
  }
  static addSchema(builder2, schemaOffset) {
    builder2.addFieldOffset(1, schemaOffset, 0);
  }
  static addDictionaries(builder2, dictionariesOffset) {
    builder2.addFieldOffset(2, dictionariesOffset, 0);
  }
  static startDictionariesVector(builder2, numElems) {
    builder2.startVector(24, numElems, 8);
  }
  static addRecordBatches(builder2, recordBatchesOffset) {
    builder2.addFieldOffset(3, recordBatchesOffset, 0);
  }
  static startRecordBatchesVector(builder2, numElems) {
    builder2.startVector(24, numElems, 8);
  }
  static addCustomMetadata(builder2, customMetadataOffset) {
    builder2.addFieldOffset(4, customMetadataOffset, 0);
  }
  static createCustomMetadataVector(builder2, data2) {
    builder2.startVector(4, data2.length, 4);
    for (let i = data2.length - 1; i >= 0; i--) {
      builder2.addOffset(data2[i]);
    }
    return builder2.endVector();
  }
  static startCustomMetadataVector(builder2, numElems) {
    builder2.startVector(4, numElems, 4);
  }
  static endFooter(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static finishFooterBuffer(builder2, offset2) {
    builder2.finish(offset2);
  }
  static finishSizePrefixedFooterBuffer(builder2, offset2) {
    builder2.finish(offset2, void 0, true);
  }
}
class Schema2 {
  constructor(fields = [], metadata, dictionaries, metadataVersion = MetadataVersion.V5) {
    this.fields = fields || [];
    this.metadata = metadata || /* @__PURE__ */ new Map();
    if (!dictionaries) {
      dictionaries = generateDictionaryMap(this.fields);
    }
    this.dictionaries = dictionaries;
    this.metadataVersion = metadataVersion;
  }
  get [Symbol.toStringTag]() {
    return "Schema";
  }
  get names() {
    return this.fields.map((f) => f.name);
  }
  toString() {
    return `Schema<{ ${this.fields.map((f, i) => `${i}: ${f}`).join(", ")} }>`;
  }
  /**
   * Construct a new Schema containing only specified fields.
   *
   * @param fieldNames Names of fields to keep.
   * @returns A new Schema of fields matching the specified names.
   */
  select(fieldNames) {
    const names = new Set(fieldNames);
    const fields = this.fields.filter((f) => names.has(f.name));
    return new Schema2(fields, this.metadata);
  }
  /**
   * Construct a new Schema containing only fields at the specified indices.
   *
   * @param fieldIndices Indices of fields to keep.
   * @returns A new Schema of fields at the specified indices.
   */
  selectAt(fieldIndices) {
    const fields = fieldIndices.map((i) => this.fields[i]).filter(Boolean);
    return new Schema2(fields, this.metadata);
  }
  assign(...args) {
    const other = args[0] instanceof Schema2 ? args[0] : Array.isArray(args[0]) ? new Schema2(args[0]) : new Schema2(args);
    const curFields = [...this.fields];
    const metadata = mergeMaps(mergeMaps(/* @__PURE__ */ new Map(), this.metadata), other.metadata);
    const newFields = other.fields.filter((f2) => {
      const i = curFields.findIndex((f) => f.name === f2.name);
      return ~i ? (curFields[i] = f2.clone({
        metadata: mergeMaps(mergeMaps(/* @__PURE__ */ new Map(), curFields[i].metadata), f2.metadata)
      })) && false : true;
    });
    const newDictionaries = generateDictionaryMap(newFields, /* @__PURE__ */ new Map());
    return new Schema2([...curFields, ...newFields], metadata, new Map([...this.dictionaries, ...newDictionaries]));
  }
}
Schema2.prototype.fields = null;
Schema2.prototype.metadata = null;
Schema2.prototype.dictionaries = null;
class Field2 {
  /** @nocollapse */
  static new(...args) {
    let [name2, type, nullable, metadata] = args;
    if (args[0] && typeof args[0] === "object") {
      ({ name: name2 } = args[0]);
      type === void 0 && (type = args[0].type);
      nullable === void 0 && (nullable = args[0].nullable);
      metadata === void 0 && (metadata = args[0].metadata);
    }
    return new Field2(`${name2}`, type, nullable, metadata);
  }
  constructor(name2, type, nullable = false, metadata) {
    this.name = name2;
    this.type = type;
    this.nullable = nullable;
    this.metadata = metadata || /* @__PURE__ */ new Map();
  }
  get typeId() {
    return this.type.typeId;
  }
  get [Symbol.toStringTag]() {
    return "Field";
  }
  toString() {
    return `${this.name}: ${this.type}`;
  }
  clone(...args) {
    let [name2, type, nullable, metadata] = args;
    !args[0] || typeof args[0] !== "object" ? [name2 = this.name, type = this.type, nullable = this.nullable, metadata = this.metadata] = args : { name: name2 = this.name, type = this.type, nullable = this.nullable, metadata = this.metadata } = args[0];
    return Field2.new(name2, type, nullable, metadata);
  }
}
Field2.prototype.type = null;
Field2.prototype.name = null;
Field2.prototype.nullable = null;
Field2.prototype.metadata = null;
function mergeMaps(m1, m2) {
  return new Map([...m1 || /* @__PURE__ */ new Map(), ...m2 || /* @__PURE__ */ new Map()]);
}
function generateDictionaryMap(fields, dictionaries = /* @__PURE__ */ new Map()) {
  for (let i = -1, n = fields.length; ++i < n; ) {
    const field2 = fields[i];
    const type = field2.type;
    if (DataType.isDictionary(type)) {
      if (!dictionaries.has(type.id)) {
        dictionaries.set(type.id, type.dictionary);
      } else if (dictionaries.get(type.id) !== type.dictionary) {
        throw new Error(`Cannot create Schema containing two different dictionaries with the same Id`);
      }
    }
    if (type.children && type.children.length > 0) {
      generateDictionaryMap(type.children, dictionaries);
    }
  }
  return dictionaries;
}
var Builder$2 = Builder$3;
var ByteBuffer$1 = ByteBuffer$2;
class Footer_ {
  /** @nocollapse */
  static decode(buf2) {
    buf2 = new ByteBuffer$1(toUint8Array(buf2));
    const footer = Footer.getRootAsFooter(buf2);
    const schema = Schema2.decode(footer.schema(), /* @__PURE__ */ new Map(), footer.version());
    return new OffHeapFooter(schema, footer);
  }
  /** @nocollapse */
  static encode(footer) {
    const b = new Builder$2();
    const schemaOffset = Schema2.encode(b, footer.schema);
    Footer.startRecordBatchesVector(b, footer.numRecordBatches);
    for (const rb of [...footer.recordBatches()].slice().reverse()) {
      FileBlock.encode(b, rb);
    }
    const recordBatchesOffset = b.endVector();
    Footer.startDictionariesVector(b, footer.numDictionaries);
    for (const db of [...footer.dictionaryBatches()].slice().reverse()) {
      FileBlock.encode(b, db);
    }
    const dictionaryBatchesOffset = b.endVector();
    Footer.startFooter(b);
    Footer.addSchema(b, schemaOffset);
    Footer.addVersion(b, MetadataVersion.V5);
    Footer.addRecordBatches(b, recordBatchesOffset);
    Footer.addDictionaries(b, dictionaryBatchesOffset);
    Footer.finishFooterBuffer(b, Footer.endFooter(b));
    return b.asUint8Array();
  }
  get numRecordBatches() {
    return this._recordBatches.length;
  }
  get numDictionaries() {
    return this._dictionaryBatches.length;
  }
  constructor(schema, version2 = MetadataVersion.V5, recordBatches, dictionaryBatches) {
    this.schema = schema;
    this.version = version2;
    recordBatches && (this._recordBatches = recordBatches);
    dictionaryBatches && (this._dictionaryBatches = dictionaryBatches);
  }
  *recordBatches() {
    for (let block, i = -1, n = this.numRecordBatches; ++i < n; ) {
      if (block = this.getRecordBatch(i)) {
        yield block;
      }
    }
  }
  *dictionaryBatches() {
    for (let block, i = -1, n = this.numDictionaries; ++i < n; ) {
      if (block = this.getDictionaryBatch(i)) {
        yield block;
      }
    }
  }
  getRecordBatch(index) {
    return index >= 0 && index < this.numRecordBatches && this._recordBatches[index] || null;
  }
  getDictionaryBatch(index) {
    return index >= 0 && index < this.numDictionaries && this._dictionaryBatches[index] || null;
  }
}
class OffHeapFooter extends Footer_ {
  get numRecordBatches() {
    return this._footer.recordBatchesLength();
  }
  get numDictionaries() {
    return this._footer.dictionariesLength();
  }
  constructor(schema, _footer) {
    super(schema, _footer.version());
    this._footer = _footer;
  }
  getRecordBatch(index) {
    if (index >= 0 && index < this.numRecordBatches) {
      const fileBlock = this._footer.recordBatches(index);
      if (fileBlock) {
        return FileBlock.decode(fileBlock);
      }
    }
    return null;
  }
  getDictionaryBatch(index) {
    if (index >= 0 && index < this.numDictionaries) {
      const fileBlock = this._footer.dictionaries(index);
      if (fileBlock) {
        return FileBlock.decode(fileBlock);
      }
    }
    return null;
  }
}
class FileBlock {
  /** @nocollapse */
  static decode(block) {
    return new FileBlock(block.metaDataLength(), block.bodyLength(), block.offset());
  }
  /** @nocollapse */
  static encode(b, fileBlock) {
    const { metaDataLength } = fileBlock;
    const offset2 = BigInt(fileBlock.offset);
    const bodyLength = BigInt(fileBlock.bodyLength);
    return Block.createBlock(b, offset2, metaDataLength, bodyLength);
  }
  constructor(metaDataLength, bodyLength, offset2) {
    this.metaDataLength = metaDataLength;
    this.offset = bigIntToNumber(offset2);
    this.bodyLength = bigIntToNumber(bodyLength);
  }
}
let Message$1 = class Message {
  constructor() {
    this.bb = null;
    this.bb_pos = 0;
  }
  __init(i, bb) {
    this.bb_pos = i;
    this.bb = bb;
    return this;
  }
  static getRootAsMessage(bb, obj) {
    return (obj || new Message()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  static getSizePrefixedRootAsMessage(bb, obj) {
    bb.setPosition(bb.position() + SIZE_PREFIX_LENGTH);
    return (obj || new Message()).__init(bb.readInt32(bb.position()) + bb.position(), bb);
  }
  version() {
    const offset2 = this.bb.__offset(this.bb_pos, 4);
    return offset2 ? this.bb.readInt16(this.bb_pos + offset2) : MetadataVersion.V1;
  }
  headerType() {
    const offset2 = this.bb.__offset(this.bb_pos, 6);
    return offset2 ? this.bb.readUint8(this.bb_pos + offset2) : MessageHeader$1.NONE;
  }
  header(obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 8);
    return offset2 ? this.bb.__union(obj, this.bb_pos + offset2) : null;
  }
  bodyLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 10);
    return offset2 ? this.bb.readInt64(this.bb_pos + offset2) : BigInt("0");
  }
  customMetadata(index, obj) {
    const offset2 = this.bb.__offset(this.bb_pos, 12);
    return offset2 ? (obj || new KeyValue()).__init(this.bb.__indirect(this.bb.__vector(this.bb_pos + offset2) + index * 4), this.bb) : null;
  }
  customMetadataLength() {
    const offset2 = this.bb.__offset(this.bb_pos, 12);
    return offset2 ? this.bb.__vector_len(this.bb_pos + offset2) : 0;
  }
  static startMessage(builder2) {
    builder2.startObject(5);
  }
  static addVersion(builder2, version2) {
    builder2.addFieldInt16(0, version2, MetadataVersion.V1);
  }
  static addHeaderType(builder2, headerType) {
    builder2.addFieldInt8(1, headerType, MessageHeader$1.NONE);
  }
  static addHeader(builder2, headerOffset) {
    builder2.addFieldOffset(2, headerOffset, 0);
  }
  static addBodyLength(builder2, bodyLength) {
    builder2.addFieldInt64(3, bodyLength, BigInt("0"));
  }
  static addCustomMetadata(builder2, customMetadataOffset) {
    builder2.addFieldOffset(4, customMetadataOffset, 0);
  }
  static createCustomMetadataVector(builder2, data2) {
    builder2.startVector(4, data2.length, 4);
    for (let i = data2.length - 1; i >= 0; i--) {
      builder2.addOffset(data2[i]);
    }
    return builder2.endVector();
  }
  static startCustomMetadataVector(builder2, numElems) {
    builder2.startVector(4, numElems, 4);
  }
  static endMessage(builder2) {
    const offset2 = builder2.endObject();
    return offset2;
  }
  static finishMessageBuffer(builder2, offset2) {
    builder2.finish(offset2);
  }
  static finishSizePrefixedMessageBuffer(builder2, offset2) {
    builder2.finish(offset2, void 0, true);
  }
  static createMessage(builder2, version2, headerType, headerOffset, bodyLength, customMetadataOffset) {
    Message.startMessage(builder2);
    Message.addVersion(builder2, version2);
    Message.addHeaderType(builder2, headerType);
    Message.addHeader(builder2, headerOffset);
    Message.addBodyLength(builder2, bodyLength);
    Message.addCustomMetadata(builder2, customMetadataOffset);
    return Message.endMessage(builder2);
  }
};
class TypeAssembler extends Visitor {
  visit(node, builder2) {
    return node == null || builder2 == null ? void 0 : super.visit(node, builder2);
  }
  visitNull(_node, b) {
    Null$1.startNull(b);
    return Null$1.endNull(b);
  }
  visitInt(node, b) {
    Int.startInt(b);
    Int.addBitWidth(b, node.bitWidth);
    Int.addIsSigned(b, node.isSigned);
    return Int.endInt(b);
  }
  visitFloat(node, b) {
    FloatingPoint.startFloatingPoint(b);
    FloatingPoint.addPrecision(b, node.precision);
    return FloatingPoint.endFloatingPoint(b);
  }
  visitBinary(_node, b) {
    Binary$1.startBinary(b);
    return Binary$1.endBinary(b);
  }
  visitLargeBinary(_node, b) {
    LargeBinary$1.startLargeBinary(b);
    return LargeBinary$1.endLargeBinary(b);
  }
  visitBool(_node, b) {
    Bool$1.startBool(b);
    return Bool$1.endBool(b);
  }
  visitUtf8(_node, b) {
    Utf8$1.startUtf8(b);
    return Utf8$1.endUtf8(b);
  }
  visitLargeUtf8(_node, b) {
    LargeUtf8$1.startLargeUtf8(b);
    return LargeUtf8$1.endLargeUtf8(b);
  }
  visitDecimal(node, b) {
    Decimal$1.startDecimal(b);
    Decimal$1.addScale(b, node.scale);
    Decimal$1.addPrecision(b, node.precision);
    Decimal$1.addBitWidth(b, node.bitWidth);
    return Decimal$1.endDecimal(b);
  }
  visitDate(node, b) {
    Date$1.startDate(b);
    Date$1.addUnit(b, node.unit);
    return Date$1.endDate(b);
  }
  visitTime(node, b) {
    Time.startTime(b);
    Time.addUnit(b, node.unit);
    Time.addBitWidth(b, node.bitWidth);
    return Time.endTime(b);
  }
  visitTimestamp(node, b) {
    const timezone = node.timezone && b.createString(node.timezone) || void 0;
    Timestamp.startTimestamp(b);
    Timestamp.addUnit(b, node.unit);
    if (timezone !== void 0) {
      Timestamp.addTimezone(b, timezone);
    }
    return Timestamp.endTimestamp(b);
  }
  visitInterval(node, b) {
    Interval.startInterval(b);
    Interval.addUnit(b, node.unit);
    return Interval.endInterval(b);
  }
  visitDuration(node, b) {
    Duration$1.startDuration(b);
    Duration$1.addUnit(b, node.unit);
    return Duration$1.endDuration(b);
  }
  visitList(_node, b) {
    List$1.startList(b);
    return List$1.endList(b);
  }
  visitStruct(_node, b) {
    Struct_.startStruct_(b);
    return Struct_.endStruct_(b);
  }
  visitUnion(node, b) {
    Union.startTypeIdsVector(b, node.typeIds.length);
    const typeIds = Union.createTypeIdsVector(b, node.typeIds);
    Union.startUnion(b);
    Union.addMode(b, node.mode);
    Union.addTypeIds(b, typeIds);
    return Union.endUnion(b);
  }
  visitDictionary(node, b) {
    const indexType = this.visit(node.indices, b);
    DictionaryEncoding.startDictionaryEncoding(b);
    DictionaryEncoding.addId(b, BigInt(node.id));
    DictionaryEncoding.addIsOrdered(b, node.isOrdered);
    if (indexType !== void 0) {
      DictionaryEncoding.addIndexType(b, indexType);
    }
    return DictionaryEncoding.endDictionaryEncoding(b);
  }
  visitFixedSizeBinary(node, b) {
    FixedSizeBinary$1.startFixedSizeBinary(b);
    FixedSizeBinary$1.addByteWidth(b, node.byteWidth);
    return FixedSizeBinary$1.endFixedSizeBinary(b);
  }
  visitFixedSizeList(node, b) {
    FixedSizeList$1.startFixedSizeList(b);
    FixedSizeList$1.addListSize(b, node.listSize);
    return FixedSizeList$1.endFixedSizeList(b);
  }
  visitMap(node, b) {
    Map$1.startMap(b);
    Map$1.addKeysSorted(b, node.keysSorted);
    return Map$1.endMap(b);
  }
}
const instance$1 = new TypeAssembler();
function schemaFromJSON(_schema, dictionaries = /* @__PURE__ */ new Map()) {
  return new Schema2(schemaFieldsFromJSON(_schema, dictionaries), customMetadataFromJSON(_schema["metadata"]), dictionaries);
}
function recordBatchFromJSON(b) {
  return new RecordBatch$1(b["count"], fieldNodesFromJSON(b["columns"]), buffersFromJSON(b["columns"]), null);
}
function dictionaryBatchFromJSON(b) {
  return new DictionaryBatch$1(recordBatchFromJSON(b["data"]), b["id"], b["isDelta"]);
}
function schemaFieldsFromJSON(_schema, dictionaries) {
  return (_schema["fields"] || []).filter(Boolean).map((f) => Field2.fromJSON(f, dictionaries));
}
function fieldChildrenFromJSON(_field, dictionaries) {
  return (_field["children"] || []).filter(Boolean).map((f) => Field2.fromJSON(f, dictionaries));
}
function fieldNodesFromJSON(xs) {
  return (xs || []).reduce((fieldNodes, column) => [
    ...fieldNodes,
    new FieldNode2(column["count"], nullCountFromJSON(column["VALIDITY"])),
    ...fieldNodesFromJSON(column["children"])
  ], []);
}
function buffersFromJSON(xs, buffers = []) {
  for (let i = -1, n = (xs || []).length; ++i < n; ) {
    const column = xs[i];
    column["VALIDITY"] && buffers.push(new BufferRegion(buffers.length, column["VALIDITY"].length));
    column["TYPE_ID"] && buffers.push(new BufferRegion(buffers.length, column["TYPE_ID"].length));
    column["OFFSET"] && buffers.push(new BufferRegion(buffers.length, column["OFFSET"].length));
    column["DATA"] && buffers.push(new BufferRegion(buffers.length, column["DATA"].length));
    buffers = buffersFromJSON(column["children"], buffers);
  }
  return buffers;
}
function nullCountFromJSON(validity) {
  return (validity || []).reduce((sum, val) => sum + +(val === 0), 0);
}
function fieldFromJSON(_field, dictionaries) {
  let id;
  let keys2;
  let field2;
  let dictMeta;
  let type;
  let dictType;
  if (!dictionaries || !(dictMeta = _field["dictionary"])) {
    type = typeFromJSON(_field, fieldChildrenFromJSON(_field, dictionaries));
    field2 = new Field2(_field["name"], type, _field["nullable"], customMetadataFromJSON(_field["metadata"]));
  } else if (!dictionaries.has(id = dictMeta["id"])) {
    keys2 = (keys2 = dictMeta["indexType"]) ? indexTypeFromJSON(keys2) : new Int32();
    dictionaries.set(id, type = typeFromJSON(_field, fieldChildrenFromJSON(_field, dictionaries)));
    dictType = new Dictionary$1(type, keys2, id, dictMeta["isOrdered"]);
    field2 = new Field2(_field["name"], dictType, _field["nullable"], customMetadataFromJSON(_field["metadata"]));
  } else {
    keys2 = (keys2 = dictMeta["indexType"]) ? indexTypeFromJSON(keys2) : new Int32();
    dictType = new Dictionary$1(dictionaries.get(id), keys2, id, dictMeta["isOrdered"]);
    field2 = new Field2(_field["name"], dictType, _field["nullable"], customMetadataFromJSON(_field["metadata"]));
  }
  return field2 || null;
}
function customMetadataFromJSON(metadata = []) {
  return new Map(metadata.map(({ key: key2, value: value2 }) => [key2, value2]));
}
function indexTypeFromJSON(_type) {
  return new Int_(_type["isSigned"], _type["bitWidth"]);
}
function typeFromJSON(f, children) {
  const typeId = f["type"]["name"];
  switch (typeId) {
    case "NONE":
      return new Null2();
    case "null":
      return new Null2();
    case "binary":
      return new Binary2();
    case "largebinary":
      return new LargeBinary2();
    case "utf8":
      return new Utf82();
    case "largeutf8":
      return new LargeUtf82();
    case "bool":
      return new Bool2();
    case "list":
      return new List2((children || [])[0]);
    case "struct":
      return new Struct(children || []);
    case "struct_":
      return new Struct(children || []);
  }
  switch (typeId) {
    case "int": {
      const t2 = f["type"];
      return new Int_(t2["isSigned"], t2["bitWidth"]);
    }
    case "floatingpoint": {
      const t2 = f["type"];
      return new Float(Precision$1[t2["precision"]]);
    }
    case "decimal": {
      const t2 = f["type"];
      return new Decimal2(t2["scale"], t2["precision"], t2["bitWidth"]);
    }
    case "date": {
      const t2 = f["type"];
      return new Date_(DateUnit$1[t2["unit"]]);
    }
    case "time": {
      const t2 = f["type"];
      return new Time_(TimeUnit$1[t2["unit"]], t2["bitWidth"]);
    }
    case "timestamp": {
      const t2 = f["type"];
      return new Timestamp_(TimeUnit$1[t2["unit"]], t2["timezone"]);
    }
    case "interval": {
      const t2 = f["type"];
      return new Interval_(IntervalUnit$1[t2["unit"]]);
    }
    case "duration": {
      const t2 = f["type"];
      return new Duration2(TimeUnit$1[t2["unit"]]);
    }
    case "union": {
      const t2 = f["type"];
      const [m, ...ms] = (t2["mode"] + "").toLowerCase();
      const mode = m.toUpperCase() + ms.join("");
      return new Union_(UnionMode$1[mode], t2["typeIds"] || [], children || []);
    }
    case "fixedsizebinary": {
      const t2 = f["type"];
      return new FixedSizeBinary2(t2["byteWidth"]);
    }
    case "fixedsizelist": {
      const t2 = f["type"];
      return new FixedSizeList2(t2["listSize"], (children || [])[0]);
    }
    case "map": {
      const t2 = f["type"];
      return new Map_((children || [])[0], t2["keysSorted"]);
    }
  }
  throw new Error(`Unrecognized type: "${typeId}"`);
}
var Builder$1 = Builder$3;
var ByteBuffer2 = ByteBuffer$2;
class Message2 {
  /** @nocollapse */
  static fromJSON(msg, headerType) {
    const message = new Message2(0, MetadataVersion.V5, headerType);
    message._createHeader = messageHeaderFromJSON(msg, headerType);
    return message;
  }
  /** @nocollapse */
  static decode(buf2) {
    buf2 = new ByteBuffer2(toUint8Array(buf2));
    const _message = Message$1.getRootAsMessage(buf2);
    const bodyLength = _message.bodyLength();
    const version2 = _message.version();
    const headerType = _message.headerType();
    const message = new Message2(bodyLength, version2, headerType);
    message._createHeader = decodeMessageHeader(_message, headerType);
    return message;
  }
  /** @nocollapse */
  static encode(message) {
    const b = new Builder$1();
    let headerOffset = -1;
    if (message.isSchema()) {
      headerOffset = Schema2.encode(b, message.header());
    } else if (message.isRecordBatch()) {
      headerOffset = RecordBatch$1.encode(b, message.header());
    } else if (message.isDictionaryBatch()) {
      headerOffset = DictionaryBatch$1.encode(b, message.header());
    }
    Message$1.startMessage(b);
    Message$1.addVersion(b, MetadataVersion.V5);
    Message$1.addHeader(b, headerOffset);
    Message$1.addHeaderType(b, message.headerType);
    Message$1.addBodyLength(b, BigInt(message.bodyLength));
    Message$1.finishMessageBuffer(b, Message$1.endMessage(b));
    return b.asUint8Array();
  }
  /** @nocollapse */
  static from(header, bodyLength = 0) {
    if (header instanceof Schema2) {
      return new Message2(0, MetadataVersion.V5, MessageHeader$1.Schema, header);
    }
    if (header instanceof RecordBatch$1) {
      return new Message2(bodyLength, MetadataVersion.V5, MessageHeader$1.RecordBatch, header);
    }
    if (header instanceof DictionaryBatch$1) {
      return new Message2(bodyLength, MetadataVersion.V5, MessageHeader$1.DictionaryBatch, header);
    }
    throw new Error(`Unrecognized Message header: ${header}`);
  }
  get type() {
    return this.headerType;
  }
  get version() {
    return this._version;
  }
  get headerType() {
    return this._headerType;
  }
  get compression() {
    return this._compression;
  }
  get bodyLength() {
    return this._bodyLength;
  }
  header() {
    return this._createHeader();
  }
  isSchema() {
    return this.headerType === MessageHeader$1.Schema;
  }
  isRecordBatch() {
    return this.headerType === MessageHeader$1.RecordBatch;
  }
  isDictionaryBatch() {
    return this.headerType === MessageHeader$1.DictionaryBatch;
  }
  constructor(bodyLength, version2, headerType, header) {
    this._version = version2;
    this._headerType = headerType;
    this.body = new Uint8Array(0);
    this._compression = header === null || header === void 0 ? void 0 : header.compression;
    header && (this._createHeader = () => header);
    this._bodyLength = bigIntToNumber(bodyLength);
  }
}
let RecordBatch$1 = class RecordBatch2 {
  get nodes() {
    return this._nodes;
  }
  get length() {
    return this._length;
  }
  get buffers() {
    return this._buffers;
  }
  get compression() {
    return this._compression;
  }
  constructor(length2, nodes, buffers, compression) {
    this._nodes = nodes;
    this._buffers = buffers;
    this._length = bigIntToNumber(length2);
    this._compression = compression;
  }
};
let DictionaryBatch$1 = class DictionaryBatch2 {
  get id() {
    return this._id;
  }
  get data() {
    return this._data;
  }
  get isDelta() {
    return this._isDelta;
  }
  get length() {
    return this.data.length;
  }
  get nodes() {
    return this.data.nodes;
  }
  get buffers() {
    return this.data.buffers;
  }
  constructor(data2, id, isDelta = false) {
    this._data = data2;
    this._isDelta = isDelta;
    this._id = bigIntToNumber(id);
  }
};
class BufferRegion {
  constructor(offset2, length2) {
    this.offset = bigIntToNumber(offset2);
    this.length = bigIntToNumber(length2);
  }
}
class FieldNode2 {
  constructor(length2, nullCount) {
    this.length = bigIntToNumber(length2);
    this.nullCount = bigIntToNumber(nullCount);
  }
}
class BodyCompression2 {
  constructor(type, method = BodyCompressionMethod.BUFFER) {
    this.type = type;
    this.method = method;
  }
}
function messageHeaderFromJSON(message, type) {
  return (() => {
    switch (type) {
      case MessageHeader$1.Schema:
        return Schema2.fromJSON(message);
      case MessageHeader$1.RecordBatch:
        return RecordBatch$1.fromJSON(message);
      case MessageHeader$1.DictionaryBatch:
        return DictionaryBatch$1.fromJSON(message);
    }
    throw new Error(`Unrecognized Message type: { name: ${MessageHeader$1[type]}, type: ${type} }`);
  });
}
function decodeMessageHeader(message, type) {
  return (() => {
    switch (type) {
      case MessageHeader$1.Schema:
        return Schema2.decode(message.header(new Schema$1()), /* @__PURE__ */ new Map(), message.version());
      case MessageHeader$1.RecordBatch:
        return RecordBatch$1.decode(message.header(new RecordBatch$2()), message.version());
      case MessageHeader$1.DictionaryBatch:
        return DictionaryBatch$1.decode(message.header(new DictionaryBatch$2()), message.version());
    }
    throw new Error(`Unrecognized Message type: { name: ${MessageHeader$1[type]}, type: ${type} }`);
  });
}
Field2["encode"] = encodeField$1;
Field2["decode"] = decodeField$1;
Field2["fromJSON"] = fieldFromJSON;
Schema2["encode"] = encodeSchema$1;
Schema2["decode"] = decodeSchema$1;
Schema2["fromJSON"] = schemaFromJSON;
RecordBatch$1["encode"] = encodeRecordBatch$1;
RecordBatch$1["decode"] = decodeRecordBatch$1;
RecordBatch$1["fromJSON"] = recordBatchFromJSON;
DictionaryBatch$1["encode"] = encodeDictionaryBatch$1;
DictionaryBatch$1["decode"] = decodeDictionaryBatch$1;
DictionaryBatch$1["fromJSON"] = dictionaryBatchFromJSON;
FieldNode2["encode"] = encodeFieldNode;
FieldNode2["decode"] = decodeFieldNode;
BufferRegion["encode"] = encodeBufferRegion;
BufferRegion["decode"] = decodeBufferRegion;
BodyCompression2["encode"] = encodeBodyCompression;
BodyCompression2["decode"] = decodeBodyCompression;
function decodeSchema$1(_schema, dictionaries = /* @__PURE__ */ new Map(), version2 = MetadataVersion.V5) {
  const fields = decodeSchemaFields$1(_schema, dictionaries);
  return new Schema2(fields, decodeCustomMetadata(_schema), dictionaries, version2);
}
function decodeRecordBatch$1(batch, version2 = MetadataVersion.V5) {
  const recordBatch = new RecordBatch$1(batch.length(), decodeFieldNodes(batch), decodeBuffers(batch, version2), decodeBodyCompression(batch.compression()));
  return recordBatch;
}
function decodeDictionaryBatch$1(batch, version2 = MetadataVersion.V5) {
  return new DictionaryBatch$1(RecordBatch$1.decode(batch.data(), version2), batch.id(), batch.isDelta());
}
function decodeBufferRegion(b) {
  return new BufferRegion(b.offset(), b.length());
}
function decodeFieldNode(f) {
  return new FieldNode2(f.length(), f.nullCount());
}
function decodeFieldNodes(batch) {
  const nodes = [];
  for (let f, i = -1, j = -1, n = batch.nodesLength(); ++i < n; ) {
    if (f = batch.nodes(i)) {
      nodes[++j] = FieldNode2.decode(f);
    }
  }
  return nodes;
}
function decodeBuffers(batch, version2) {
  const bufferRegions = [];
  for (let b, i = -1, j = -1, n = batch.buffersLength(); ++i < n; ) {
    if (b = batch.buffers(i)) {
      if (version2 < MetadataVersion.V4) {
        b.bb_pos += 8 * (i + 1);
      }
      bufferRegions[++j] = BufferRegion.decode(b);
    }
  }
  return bufferRegions;
}
function decodeSchemaFields$1(schema, dictionaries) {
  const fields = [];
  for (let f, i = -1, j = -1, n = schema.fieldsLength(); ++i < n; ) {
    if (f = schema.fields(i)) {
      fields[++j] = Field2.decode(f, dictionaries);
    }
  }
  return fields;
}
function decodeFieldChildren$1(field2, dictionaries) {
  const children = [];
  for (let f, i = -1, j = -1, n = field2.childrenLength(); ++i < n; ) {
    if (f = field2.children(i)) {
      children[++j] = Field2.decode(f, dictionaries);
    }
  }
  return children;
}
function decodeField$1(f, dictionaries) {
  let id;
  let field2;
  let type;
  let keys2;
  let dictType;
  let dictMeta;
  if (!dictionaries || !(dictMeta = f.dictionary())) {
    type = decodeFieldType(f, decodeFieldChildren$1(f, dictionaries));
    field2 = new Field2(f.name(), type, f.nullable(), decodeCustomMetadata(f));
  } else if (!dictionaries.has(id = bigIntToNumber(dictMeta.id()))) {
    keys2 = (keys2 = dictMeta.indexType()) ? decodeIndexType(keys2) : new Int32();
    dictionaries.set(id, type = decodeFieldType(f, decodeFieldChildren$1(f, dictionaries)));
    dictType = new Dictionary$1(type, keys2, id, dictMeta.isOrdered());
    field2 = new Field2(f.name(), dictType, f.nullable(), decodeCustomMetadata(f));
  } else {
    keys2 = (keys2 = dictMeta.indexType()) ? decodeIndexType(keys2) : new Int32();
    dictType = new Dictionary$1(dictionaries.get(id), keys2, id, dictMeta.isOrdered());
    field2 = new Field2(f.name(), dictType, f.nullable(), decodeCustomMetadata(f));
  }
  return field2 || null;
}
function decodeCustomMetadata(parent) {
  const data2 = /* @__PURE__ */ new Map();
  if (parent) {
    for (let entry, key2, i = -1, n = Math.trunc(parent.customMetadataLength()); ++i < n; ) {
      if ((entry = parent.customMetadata(i)) && (key2 = entry.key()) != null) {
        data2.set(key2, entry.value());
      }
    }
  }
  return data2;
}
function decodeIndexType(_type) {
  return new Int_(_type.isSigned(), _type.bitWidth());
}
function decodeFieldType(f, children) {
  const typeId = f.typeType();
  switch (typeId) {
    case Type$2["NONE"]:
      return new Null2();
    case Type$2["Null"]:
      return new Null2();
    case Type$2["Binary"]:
      return new Binary2();
    case Type$2["LargeBinary"]:
      return new LargeBinary2();
    case Type$2["Utf8"]:
      return new Utf82();
    case Type$2["LargeUtf8"]:
      return new LargeUtf82();
    case Type$2["Bool"]:
      return new Bool2();
    case Type$2["List"]:
      return new List2((children || [])[0]);
    case Type$2["Struct_"]:
      return new Struct(children || []);
  }
  switch (typeId) {
    case Type$2["Int"]: {
      const t2 = f.type(new Int());
      return new Int_(t2.isSigned(), t2.bitWidth());
    }
    case Type$2["FloatingPoint"]: {
      const t2 = f.type(new FloatingPoint());
      return new Float(t2.precision());
    }
    case Type$2["Decimal"]: {
      const t2 = f.type(new Decimal$1());
      return new Decimal2(t2.scale(), t2.precision(), t2.bitWidth());
    }
    case Type$2["Date"]: {
      const t2 = f.type(new Date$1());
      return new Date_(t2.unit());
    }
    case Type$2["Time"]: {
      const t2 = f.type(new Time());
      return new Time_(t2.unit(), t2.bitWidth());
    }
    case Type$2["Timestamp"]: {
      const t2 = f.type(new Timestamp());
      return new Timestamp_(t2.unit(), t2.timezone());
    }
    case Type$2["Interval"]: {
      const t2 = f.type(new Interval());
      return new Interval_(t2.unit());
    }
    case Type$2["Duration"]: {
      const t2 = f.type(new Duration$1());
      return new Duration2(t2.unit());
    }
    case Type$2["Union"]: {
      const t2 = f.type(new Union());
      return new Union_(t2.mode(), t2.typeIdsArray() || [], children || []);
    }
    case Type$2["FixedSizeBinary"]: {
      const t2 = f.type(new FixedSizeBinary$1());
      return new FixedSizeBinary2(t2.byteWidth());
    }
    case Type$2["FixedSizeList"]: {
      const t2 = f.type(new FixedSizeList$1());
      return new FixedSizeList2(t2.listSize(), (children || [])[0]);
    }
    case Type$2["Map"]: {
      const t2 = f.type(new Map$1());
      return new Map_((children || [])[0], t2.keysSorted());
    }
  }
  throw new Error(`Unrecognized type: "${Type$2[typeId]}" (${typeId})`);
}
function decodeBodyCompression(b) {
  return b ? new BodyCompression2(b.codec(), b.method()) : null;
}
function encodeSchema$1(b, schema) {
  const fieldOffsets = schema.fields.map((f) => Field2.encode(b, f));
  Schema$1.startFieldsVector(b, fieldOffsets.length);
  const fieldsVectorOffset = Schema$1.createFieldsVector(b, fieldOffsets);
  const metadataOffset = !(schema.metadata && schema.metadata.size > 0) ? -1 : Schema$1.createCustomMetadataVector(b, [...schema.metadata].map(([k, v]) => {
    const key2 = b.createString(`${k}`);
    const val = b.createString(`${v}`);
    KeyValue.startKeyValue(b);
    KeyValue.addKey(b, key2);
    KeyValue.addValue(b, val);
    return KeyValue.endKeyValue(b);
  }));
  Schema$1.startSchema(b);
  Schema$1.addFields(b, fieldsVectorOffset);
  Schema$1.addEndianness(b, platformIsLittleEndian ? Endianness$1.Little : Endianness$1.Big);
  if (metadataOffset !== -1) {
    Schema$1.addCustomMetadata(b, metadataOffset);
  }
  return Schema$1.endSchema(b);
}
function encodeField$1(b, field2) {
  let nameOffset = -1;
  let typeOffset = -1;
  let dictionaryOffset = -1;
  const type = field2.type;
  let typeId = field2.typeId;
  if (!DataType.isDictionary(type)) {
    typeOffset = instance$1.visit(type, b);
  } else {
    typeId = type.dictionary.typeId;
    dictionaryOffset = instance$1.visit(type, b);
    typeOffset = instance$1.visit(type.dictionary, b);
  }
  const childOffsets = (type.children || []).map((f) => Field2.encode(b, f));
  const childrenVectorOffset = Field$1.createChildrenVector(b, childOffsets);
  const metadataOffset = !(field2.metadata && field2.metadata.size > 0) ? -1 : Field$1.createCustomMetadataVector(b, [...field2.metadata].map(([k, v]) => {
    const key2 = b.createString(`${k}`);
    const val = b.createString(`${v}`);
    KeyValue.startKeyValue(b);
    KeyValue.addKey(b, key2);
    KeyValue.addValue(b, val);
    return KeyValue.endKeyValue(b);
  }));
  if (field2.name) {
    nameOffset = b.createString(field2.name);
  }
  Field$1.startField(b);
  Field$1.addType(b, typeOffset);
  Field$1.addTypeType(b, typeId);
  Field$1.addChildren(b, childrenVectorOffset);
  Field$1.addNullable(b, !!field2.nullable);
  if (nameOffset !== -1) {
    Field$1.addName(b, nameOffset);
  }
  if (dictionaryOffset !== -1) {
    Field$1.addDictionary(b, dictionaryOffset);
  }
  if (metadataOffset !== -1) {
    Field$1.addCustomMetadata(b, metadataOffset);
  }
  return Field$1.endField(b);
}
function encodeRecordBatch$1(b, recordBatch) {
  const nodes = recordBatch.nodes || [];
  const buffers = recordBatch.buffers || [];
  RecordBatch$2.startNodesVector(b, nodes.length);
  for (const n of nodes.slice().reverse())
    FieldNode2.encode(b, n);
  const nodesVectorOffset = b.endVector();
  RecordBatch$2.startBuffersVector(b, buffers.length);
  for (const b_ of buffers.slice().reverse())
    BufferRegion.encode(b, b_);
  const buffersVectorOffset = b.endVector();
  let bodyCompressionOffset = null;
  if (recordBatch.compression !== null) {
    bodyCompressionOffset = encodeBodyCompression(b, recordBatch.compression);
  }
  RecordBatch$2.startRecordBatch(b);
  RecordBatch$2.addLength(b, BigInt(recordBatch.length));
  RecordBatch$2.addNodes(b, nodesVectorOffset);
  RecordBatch$2.addBuffers(b, buffersVectorOffset);
  if (recordBatch.compression !== null && bodyCompressionOffset) {
    RecordBatch$2.addCompression(b, bodyCompressionOffset);
  }
  return RecordBatch$2.endRecordBatch(b);
}
function encodeBodyCompression(b, node) {
  BodyCompression$1.startBodyCompression(b);
  BodyCompression$1.addCodec(b, node.type);
  BodyCompression$1.addMethod(b, node.method);
  return BodyCompression$1.endBodyCompression(b);
}
function encodeDictionaryBatch$1(b, dictionaryBatch) {
  const dataOffset = RecordBatch$1.encode(b, dictionaryBatch.data);
  DictionaryBatch$2.startDictionaryBatch(b);
  DictionaryBatch$2.addId(b, BigInt(dictionaryBatch.id));
  DictionaryBatch$2.addIsDelta(b, dictionaryBatch.isDelta);
  DictionaryBatch$2.addData(b, dataOffset);
  return DictionaryBatch$2.endDictionaryBatch(b);
}
function encodeFieldNode(b, node) {
  return FieldNode$1.createFieldNode(b, BigInt(node.length), BigInt(node.nullCount));
}
function encodeBufferRegion(b, node) {
  return Buffer$1.createBuffer(b, BigInt(node.offset), BigInt(node.length));
}
const platformIsLittleEndian = (() => {
  const buffer2 = new ArrayBuffer(2);
  new DataView(buffer2).setInt16(
    0,
    256,
    true
    /* littleEndian */
  );
  return new Int16Array(buffer2)[0] === 256;
})();
const ITERATOR_DONE = Object.freeze({ done: true, value: void 0 });
class ArrowJSON {
  constructor(_json) {
    this._json = _json;
  }
  get schema() {
    return this._json["schema"];
  }
  get batches() {
    return this._json["batches"] || [];
  }
  get dictionaries() {
    return this._json["dictionaries"] || [];
  }
}
class ReadableInterop {
  tee() {
    return this._getDOMStream().tee();
  }
  pipe(writable, options) {
    return this._getNodeStream().pipe(writable, options);
  }
  pipeTo(writable, options) {
    return this._getDOMStream().pipeTo(writable, options);
  }
  pipeThrough(duplex, options) {
    return this._getDOMStream().pipeThrough(duplex, options);
  }
  _getDOMStream() {
    return this._DOMStream || (this._DOMStream = this.toDOMStream());
  }
  _getNodeStream() {
    return this._nodeStream || (this._nodeStream = this.toNodeStream());
  }
}
class AsyncQueue extends ReadableInterop {
  constructor() {
    super();
    this._values = [];
    this.resolvers = [];
    this._closedPromise = new Promise((r) => this._closedPromiseResolve = r);
  }
  get closed() {
    return this._closedPromise;
  }
  cancel(reason) {
    return __awaiter(this, void 0, void 0, function* () {
      yield this.return(reason);
    });
  }
  write(value2) {
    if (this._ensureOpen()) {
      this.resolvers.length <= 0 ? this._values.push(value2) : this.resolvers.shift().resolve({ done: false, value: value2 });
    }
  }
  abort(value2) {
    if (this._closedPromiseResolve) {
      this.resolvers.length <= 0 ? this._error = { error: value2 } : this.resolvers.shift().reject({ done: true, value: value2 });
    }
  }
  close() {
    if (this._closedPromiseResolve) {
      const { resolvers } = this;
      while (resolvers.length > 0) {
        resolvers.shift().resolve(ITERATOR_DONE);
      }
      this._closedPromiseResolve();
      this._closedPromiseResolve = void 0;
    }
  }
  [Symbol.asyncIterator]() {
    return this;
  }
  toDOMStream(options) {
    return streamAdapters.toDOMStream(this._closedPromiseResolve || this._error ? this : this._values, options);
  }
  toNodeStream(options) {
    return streamAdapters.toNodeStream(this._closedPromiseResolve || this._error ? this : this._values, options);
  }
  throw(_) {
    return __awaiter(this, void 0, void 0, function* () {
      yield this.abort(_);
      return ITERATOR_DONE;
    });
  }
  return(_) {
    return __awaiter(this, void 0, void 0, function* () {
      yield this.close();
      return ITERATOR_DONE;
    });
  }
  read(size) {
    return __awaiter(this, void 0, void 0, function* () {
      return (yield this.next(size, "read")).value;
    });
  }
  peek(size) {
    return __awaiter(this, void 0, void 0, function* () {
      return (yield this.next(size, "peek")).value;
    });
  }
  next(..._args) {
    if (this._values.length > 0) {
      return Promise.resolve({ done: false, value: this._values.shift() });
    } else if (this._error) {
      return Promise.reject({ done: true, value: this._error.error });
    } else if (!this._closedPromiseResolve) {
      return Promise.resolve(ITERATOR_DONE);
    } else {
      return new Promise((resolve2, reject) => {
        this.resolvers.push({ resolve: resolve2, reject });
      });
    }
  }
  _ensureOpen() {
    if (this._closedPromiseResolve) {
      return true;
    }
    throw new Error(`AsyncQueue is closed`);
  }
}
class AsyncByteQueue extends AsyncQueue {
  write(value2) {
    if ((value2 = toUint8Array(value2)).byteLength > 0) {
      return super.write(value2);
    }
  }
  toString(sync = false) {
    return sync ? decodeUtf8$1(this.toUint8Array(true)) : this.toUint8Array(false).then(decodeUtf8$1);
  }
  toUint8Array(sync = false) {
    return sync ? joinUint8Arrays(this._values)[0] : (() => __awaiter(this, void 0, void 0, function* () {
      var _a2, e_1, _b2, _c2;
      const buffers = [];
      let byteLength = 0;
      try {
        for (var _d2 = true, _e2 = __asyncValues(this), _f2; _f2 = yield _e2.next(), _a2 = _f2.done, !_a2; _d2 = true) {
          _c2 = _f2.value;
          _d2 = false;
          const chunk = _c2;
          buffers.push(chunk);
          byteLength += chunk.byteLength;
        }
      } catch (e_1_1) {
        e_1 = { error: e_1_1 };
      } finally {
        try {
          if (!_d2 && !_a2 && (_b2 = _e2.return)) yield _b2.call(_e2);
        } finally {
          if (e_1) throw e_1.error;
        }
      }
      return joinUint8Arrays(buffers, byteLength)[0];
    }))();
  }
}
class ByteStream {
  constructor(source2) {
    if (source2) {
      this.source = new ByteStreamSource(streamAdapters.fromIterable(source2));
    }
  }
  [Symbol.iterator]() {
    return this;
  }
  next(value2) {
    return this.source.next(value2);
  }
  throw(value2) {
    return this.source.throw(value2);
  }
  return(value2) {
    return this.source.return(value2);
  }
  peek(size) {
    return this.source.peek(size);
  }
  read(size) {
    return this.source.read(size);
  }
}
class AsyncByteStream {
  constructor(source2) {
    if (source2 instanceof AsyncByteStream) {
      this.source = source2.source;
    } else if (source2 instanceof AsyncByteQueue) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromAsyncIterable(source2));
    } else if (isReadableNodeStream(source2)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromNodeStream(source2));
    } else if (isReadableDOMStream(source2)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromDOMStream(source2));
    } else if (isFetchResponse(source2)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromDOMStream(source2.body));
    } else if (isIterable$1(source2)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromIterable(source2));
    } else if (isPromise(source2)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromAsyncIterable(source2));
    } else if (isAsyncIterable(source2)) {
      this.source = new AsyncByteStreamSource(streamAdapters.fromAsyncIterable(source2));
    }
  }
  [Symbol.asyncIterator]() {
    return this;
  }
  next(value2) {
    return this.source.next(value2);
  }
  throw(value2) {
    return this.source.throw(value2);
  }
  return(value2) {
    return this.source.return(value2);
  }
  get closed() {
    return this.source.closed;
  }
  cancel(reason) {
    return this.source.cancel(reason);
  }
  peek(size) {
    return this.source.peek(size);
  }
  read(size) {
    return this.source.read(size);
  }
}
class ByteStreamSource {
  constructor(source2) {
    this.source = source2;
  }
  cancel(reason) {
    this.return(reason);
  }
  peek(size) {
    return this.next(size, "peek").value;
  }
  read(size) {
    return this.next(size, "read").value;
  }
  next(size, cmd = "read") {
    return this.source.next({ cmd, size });
  }
  throw(value2) {
    return Object.create(this.source.throw && this.source.throw(value2) || ITERATOR_DONE);
  }
  return(value2) {
    return Object.create(this.source.return && this.source.return(value2) || ITERATOR_DONE);
  }
}
class AsyncByteStreamSource {
  constructor(source2) {
    this.source = source2;
    this._closedPromise = new Promise((r) => this._closedPromiseResolve = r);
  }
  cancel(reason) {
    return __awaiter(this, void 0, void 0, function* () {
      yield this.return(reason);
    });
  }
  get closed() {
    return this._closedPromise;
  }
  read(size) {
    return __awaiter(this, void 0, void 0, function* () {
      return (yield this.next(size, "read")).value;
    });
  }
  peek(size) {
    return __awaiter(this, void 0, void 0, function* () {
      return (yield this.next(size, "peek")).value;
    });
  }
  next(size_1) {
    return __awaiter(this, arguments, void 0, function* (size, cmd = "read") {
      return yield this.source.next({ cmd, size });
    });
  }
  throw(value2) {
    return __awaiter(this, void 0, void 0, function* () {
      const result2 = this.source.throw && (yield this.source.throw(value2)) || ITERATOR_DONE;
      this._closedPromiseResolve && this._closedPromiseResolve();
      this._closedPromiseResolve = void 0;
      return Object.create(result2);
    });
  }
  return(value2) {
    return __awaiter(this, void 0, void 0, function* () {
      const result2 = this.source.return && (yield this.source.return(value2)) || ITERATOR_DONE;
      this._closedPromiseResolve && this._closedPromiseResolve();
      this._closedPromiseResolve = void 0;
      return Object.create(result2);
    });
  }
}
class RandomAccessFile extends ByteStream {
  constructor(buffer2, byteLength) {
    super();
    this.position = 0;
    this.buffer = toUint8Array(buffer2);
    this.size = byteLength === void 0 ? this.buffer.byteLength : byteLength;
  }
  readInt32(position) {
    const { buffer: buffer2, byteOffset } = this.readAt(position, 4);
    return new DataView(buffer2, byteOffset).getInt32(0, true);
  }
  seek(position) {
    this.position = Math.min(position, this.size);
    return position < this.size;
  }
  read(nBytes) {
    const { buffer: buffer2, size, position } = this;
    if (buffer2 && position < size) {
      if (typeof nBytes !== "number") {
        nBytes = Number.POSITIVE_INFINITY;
      }
      this.position = Math.min(size, position + Math.min(size - position, nBytes));
      return buffer2.subarray(position, this.position);
    }
    return null;
  }
  readAt(position, nBytes) {
    const buf2 = this.buffer;
    const end = Math.min(this.size, position + nBytes);
    return buf2 ? buf2.subarray(position, end) : new Uint8Array(nBytes);
  }
  close() {
    this.buffer && (this.buffer = null);
  }
  throw(value2) {
    this.close();
    return { done: true, value: value2 };
  }
  return(value2) {
    this.close();
    return { done: true, value: value2 };
  }
}
class AsyncRandomAccessFile extends AsyncByteStream {
  constructor(file, byteLength) {
    super();
    this.position = 0;
    this._handle = file;
    if (typeof byteLength === "number") {
      this.size = byteLength;
    } else {
      this._pending = (() => __awaiter(this, void 0, void 0, function* () {
        this.size = (yield file.stat()).size;
        delete this._pending;
      }))();
    }
  }
  readInt32(position) {
    return __awaiter(this, void 0, void 0, function* () {
      const { buffer: buffer2, byteOffset } = yield this.readAt(position, 4);
      return new DataView(buffer2, byteOffset).getInt32(0, true);
    });
  }
  seek(position) {
    return __awaiter(this, void 0, void 0, function* () {
      this._pending && (yield this._pending);
      this.position = Math.min(position, this.size);
      return position < this.size;
    });
  }
  read(nBytes) {
    return __awaiter(this, void 0, void 0, function* () {
      this._pending && (yield this._pending);
      const { _handle: file, size, position } = this;
      if (file && position < size) {
        if (typeof nBytes !== "number") {
          nBytes = Number.POSITIVE_INFINITY;
        }
        let pos = position, offset2 = 0, bytesRead = 0;
        const end = Math.min(size, pos + Math.min(size - pos, nBytes));
        const buffer2 = new Uint8Array(Math.max(0, (this.position = end) - pos));
        while ((pos += bytesRead) < end && (offset2 += bytesRead) < buffer2.byteLength) {
          ({ bytesRead } = yield file.read(buffer2, offset2, buffer2.byteLength - offset2, pos));
        }
        return buffer2;
      }
      return null;
    });
  }
  readAt(position, nBytes) {
    return __awaiter(this, void 0, void 0, function* () {
      this._pending && (yield this._pending);
      const { _handle: file, size } = this;
      if (file && position + nBytes < size) {
        const end = Math.min(size, position + nBytes);
        const buffer2 = new Uint8Array(end - position);
        return (yield file.read(buffer2, 0, nBytes, position)).buffer;
      }
      return new Uint8Array(nBytes);
    });
  }
  close() {
    return __awaiter(this, void 0, void 0, function* () {
      const f = this._handle;
      this._handle = null;
      f && (yield f.close());
    });
  }
  throw(value2) {
    return __awaiter(this, void 0, void 0, function* () {
      yield this.close();
      return { done: true, value: value2 };
    });
  }
  return(value2) {
    return __awaiter(this, void 0, void 0, function* () {
      yield this.close();
      return { done: true, value: value2 };
    });
  }
}
const carryBit16 = 1 << 16;
function intAsHex(value2) {
  if (value2 < 0) {
    value2 = 4294967295 + value2 + 1;
  }
  return `0x${value2.toString(16)}`;
}
const kInt32DecimalDigits = 8;
const kPowersOfTen = [
  1,
  10,
  100,
  1e3,
  1e4,
  1e5,
  1e6,
  1e7,
  1e8
];
class BaseInt64 {
  constructor(buffer2) {
    this.buffer = buffer2;
  }
  high() {
    return this.buffer[1];
  }
  low() {
    return this.buffer[0];
  }
  _times(other) {
    const L = new Uint32Array([
      this.buffer[1] >>> 16,
      this.buffer[1] & 65535,
      this.buffer[0] >>> 16,
      this.buffer[0] & 65535
    ]);
    const R = new Uint32Array([
      other.buffer[1] >>> 16,
      other.buffer[1] & 65535,
      other.buffer[0] >>> 16,
      other.buffer[0] & 65535
    ]);
    let product2 = L[3] * R[3];
    this.buffer[0] = product2 & 65535;
    let sum = product2 >>> 16;
    product2 = L[2] * R[3];
    sum += product2;
    product2 = L[3] * R[2] >>> 0;
    sum += product2;
    this.buffer[0] += sum << 16;
    this.buffer[1] = sum >>> 0 < product2 ? carryBit16 : 0;
    this.buffer[1] += sum >>> 16;
    this.buffer[1] += L[1] * R[3] + L[2] * R[2] + L[3] * R[1];
    this.buffer[1] += L[0] * R[3] + L[1] * R[2] + L[2] * R[1] + L[3] * R[0] << 16;
    return this;
  }
  _plus(other) {
    const sum = this.buffer[0] + other.buffer[0] >>> 0;
    this.buffer[1] += other.buffer[1];
    if (sum < this.buffer[0] >>> 0) {
      ++this.buffer[1];
    }
    this.buffer[0] = sum;
  }
  lessThan(other) {
    return this.buffer[1] < other.buffer[1] || this.buffer[1] === other.buffer[1] && this.buffer[0] < other.buffer[0];
  }
  equals(other) {
    return this.buffer[1] === other.buffer[1] && this.buffer[0] == other.buffer[0];
  }
  greaterThan(other) {
    return other.lessThan(this);
  }
  hex() {
    return `${intAsHex(this.buffer[1])} ${intAsHex(this.buffer[0])}`;
  }
}
class Uint64 extends BaseInt64 {
  times(other) {
    this._times(other);
    return this;
  }
  plus(other) {
    this._plus(other);
    return this;
  }
  /** @nocollapse */
  static from(val, out_buffer = new Uint32Array(2)) {
    return Uint64.fromString(typeof val === "string" ? val : val.toString(), out_buffer);
  }
  /** @nocollapse */
  static fromNumber(num, out_buffer = new Uint32Array(2)) {
    return Uint64.fromString(num.toString(), out_buffer);
  }
  /** @nocollapse */
  static fromString(str, out_buffer = new Uint32Array(2)) {
    const length2 = str.length;
    const out = new Uint64(out_buffer);
    for (let posn = 0; posn < length2; ) {
      const group = kInt32DecimalDigits < length2 - posn ? kInt32DecimalDigits : length2 - posn;
      const chunk = new Uint64(new Uint32Array([Number.parseInt(str.slice(posn, posn + group), 10), 0]));
      const multiple = new Uint64(new Uint32Array([kPowersOfTen[group], 0]));
      out.times(multiple);
      out.plus(chunk);
      posn += group;
    }
    return out;
  }
  /** @nocollapse */
  static convertArray(values2) {
    const data2 = new Uint32Array(values2.length * 2);
    for (let i = -1, n = values2.length; ++i < n; ) {
      Uint64.from(values2[i], new Uint32Array(data2.buffer, data2.byteOffset + 2 * i * 4, 2));
    }
    return data2;
  }
  /** @nocollapse */
  static multiply(left, right) {
    const rtrn = new Uint64(new Uint32Array(left.buffer));
    return rtrn.times(right);
  }
  /** @nocollapse */
  static add(left, right) {
    const rtrn = new Uint64(new Uint32Array(left.buffer));
    return rtrn.plus(right);
  }
}
class Int64 extends BaseInt64 {
  negate() {
    this.buffer[0] = ~this.buffer[0] + 1;
    this.buffer[1] = ~this.buffer[1];
    if (this.buffer[0] == 0) {
      ++this.buffer[1];
    }
    return this;
  }
  times(other) {
    this._times(other);
    return this;
  }
  plus(other) {
    this._plus(other);
    return this;
  }
  lessThan(other) {
    const this_high = this.buffer[1] << 0;
    const other_high = other.buffer[1] << 0;
    return this_high < other_high || this_high === other_high && this.buffer[0] < other.buffer[0];
  }
  /** @nocollapse */
  static from(val, out_buffer = new Uint32Array(2)) {
    return Int64.fromString(typeof val === "string" ? val : val.toString(), out_buffer);
  }
  /** @nocollapse */
  static fromNumber(num, out_buffer = new Uint32Array(2)) {
    return Int64.fromString(num.toString(), out_buffer);
  }
  /** @nocollapse */
  static fromString(str, out_buffer = new Uint32Array(2)) {
    const negate = str.startsWith("-");
    const length2 = str.length;
    const out = new Int64(out_buffer);
    for (let posn = negate ? 1 : 0; posn < length2; ) {
      const group = kInt32DecimalDigits < length2 - posn ? kInt32DecimalDigits : length2 - posn;
      const chunk = new Int64(new Uint32Array([Number.parseInt(str.slice(posn, posn + group), 10), 0]));
      const multiple = new Int64(new Uint32Array([kPowersOfTen[group], 0]));
      out.times(multiple);
      out.plus(chunk);
      posn += group;
    }
    return negate ? out.negate() : out;
  }
  /** @nocollapse */
  static convertArray(values2) {
    const data2 = new Uint32Array(values2.length * 2);
    for (let i = -1, n = values2.length; ++i < n; ) {
      Int64.from(values2[i], new Uint32Array(data2.buffer, data2.byteOffset + 2 * i * 4, 2));
    }
    return data2;
  }
  /** @nocollapse */
  static multiply(left, right) {
    const rtrn = new Int64(new Uint32Array(left.buffer));
    return rtrn.times(right);
  }
  /** @nocollapse */
  static add(left, right) {
    const rtrn = new Int64(new Uint32Array(left.buffer));
    return rtrn.plus(right);
  }
}
class Int128 {
  constructor(buffer2) {
    this.buffer = buffer2;
  }
  high() {
    return new Int64(new Uint32Array(this.buffer.buffer, this.buffer.byteOffset + 8, 2));
  }
  low() {
    return new Int64(new Uint32Array(this.buffer.buffer, this.buffer.byteOffset, 2));
  }
  negate() {
    this.buffer[0] = ~this.buffer[0] + 1;
    this.buffer[1] = ~this.buffer[1];
    this.buffer[2] = ~this.buffer[2];
    this.buffer[3] = ~this.buffer[3];
    if (this.buffer[0] == 0) {
      ++this.buffer[1];
    }
    if (this.buffer[1] == 0) {
      ++this.buffer[2];
    }
    if (this.buffer[2] == 0) {
      ++this.buffer[3];
    }
    return this;
  }
  times(other) {
    const L0 = new Uint64(new Uint32Array([this.buffer[3], 0]));
    const L1 = new Uint64(new Uint32Array([this.buffer[2], 0]));
    const L2 = new Uint64(new Uint32Array([this.buffer[1], 0]));
    const L3 = new Uint64(new Uint32Array([this.buffer[0], 0]));
    const R0 = new Uint64(new Uint32Array([other.buffer[3], 0]));
    const R1 = new Uint64(new Uint32Array([other.buffer[2], 0]));
    const R2 = new Uint64(new Uint32Array([other.buffer[1], 0]));
    const R3 = new Uint64(new Uint32Array([other.buffer[0], 0]));
    let product2 = Uint64.multiply(L3, R3);
    this.buffer[0] = product2.low();
    const sum = new Uint64(new Uint32Array([product2.high(), 0]));
    product2 = Uint64.multiply(L2, R3);
    sum.plus(product2);
    product2 = Uint64.multiply(L3, R2);
    sum.plus(product2);
    this.buffer[1] = sum.low();
    this.buffer[3] = sum.lessThan(product2) ? 1 : 0;
    this.buffer[2] = sum.high();
    const high = new Uint64(new Uint32Array(this.buffer.buffer, this.buffer.byteOffset + 8, 2));
    high.plus(Uint64.multiply(L1, R3)).plus(Uint64.multiply(L2, R2)).plus(Uint64.multiply(L3, R1));
    this.buffer[3] += Uint64.multiply(L0, R3).plus(Uint64.multiply(L1, R2)).plus(Uint64.multiply(L2, R1)).plus(Uint64.multiply(L3, R0)).low();
    return this;
  }
  plus(other) {
    const sums = new Uint32Array(4);
    sums[3] = this.buffer[3] + other.buffer[3] >>> 0;
    sums[2] = this.buffer[2] + other.buffer[2] >>> 0;
    sums[1] = this.buffer[1] + other.buffer[1] >>> 0;
    sums[0] = this.buffer[0] + other.buffer[0] >>> 0;
    if (sums[0] < this.buffer[0] >>> 0) {
      ++sums[1];
    }
    if (sums[1] < this.buffer[1] >>> 0) {
      ++sums[2];
    }
    if (sums[2] < this.buffer[2] >>> 0) {
      ++sums[3];
    }
    this.buffer[3] = sums[3];
    this.buffer[2] = sums[2];
    this.buffer[1] = sums[1];
    this.buffer[0] = sums[0];
    return this;
  }
  hex() {
    return `${intAsHex(this.buffer[3])} ${intAsHex(this.buffer[2])} ${intAsHex(this.buffer[1])} ${intAsHex(this.buffer[0])}`;
  }
  /** @nocollapse */
  static multiply(left, right) {
    const rtrn = new Int128(new Uint32Array(left.buffer));
    return rtrn.times(right);
  }
  /** @nocollapse */
  static add(left, right) {
    const rtrn = new Int128(new Uint32Array(left.buffer));
    return rtrn.plus(right);
  }
  /** @nocollapse */
  static from(val, out_buffer = new Uint32Array(4)) {
    return Int128.fromString(typeof val === "string" ? val : val.toString(), out_buffer);
  }
  /** @nocollapse */
  static fromNumber(num, out_buffer = new Uint32Array(4)) {
    return Int128.fromString(num.toString(), out_buffer);
  }
  /** @nocollapse */
  static fromString(str, out_buffer = new Uint32Array(4)) {
    const negate = str.startsWith("-");
    const length2 = str.length;
    const out = new Int128(out_buffer);
    for (let posn = negate ? 1 : 0; posn < length2; ) {
      const group = kInt32DecimalDigits < length2 - posn ? kInt32DecimalDigits : length2 - posn;
      const chunk = new Int128(new Uint32Array([Number.parseInt(str.slice(posn, posn + group), 10), 0, 0, 0]));
      const multiple = new Int128(new Uint32Array([kPowersOfTen[group], 0, 0, 0]));
      out.times(multiple);
      out.plus(chunk);
      posn += group;
    }
    return negate ? out.negate() : out;
  }
  /** @nocollapse */
  static convertArray(values2) {
    const data2 = new Uint32Array(values2.length * 4);
    for (let i = -1, n = values2.length; ++i < n; ) {
      Int128.from(values2[i], new Uint32Array(data2.buffer, data2.byteOffset + 4 * 4 * i, 4));
    }
    return data2;
  }
}
function toIntervalDayTimeInt32Array(objects) {
  var _a2, _b2;
  const length2 = objects.length;
  const array2 = new Int32Array(length2 * 2);
  for (let oi = 0, ai = 0; oi < length2; oi++) {
    const interval2 = objects[oi];
    array2[ai++] = (_a2 = interval2["days"]) !== null && _a2 !== void 0 ? _a2 : 0;
    array2[ai++] = (_b2 = interval2["milliseconds"]) !== null && _b2 !== void 0 ? _b2 : 0;
  }
  return array2;
}
function toIntervalMonthDayNanoInt32Array(objects) {
  var _a2, _b2;
  const length2 = objects.length;
  const data2 = new Int32Array(length2 * 4);
  for (let oi = 0, ai = 0; oi < length2; oi++) {
    const interval2 = objects[oi];
    data2[ai++] = (_a2 = interval2["months"]) !== null && _a2 !== void 0 ? _a2 : 0;
    data2[ai++] = (_b2 = interval2["days"]) !== null && _b2 !== void 0 ? _b2 : 0;
    const nanoseconds = interval2["nanoseconds"];
    if (nanoseconds) {
      data2[ai++] = Number(BigInt(nanoseconds) & BigInt(4294967295));
      data2[ai++] = Number(BigInt(nanoseconds) >> BigInt(32));
    } else {
      ai += 2;
    }
  }
  return data2;
}
class VectorLoader extends Visitor {
  constructor(bytes, nodes, buffers, dictionaries, metadataVersion = MetadataVersion.V5) {
    super();
    this.nodesIndex = -1;
    this.buffersIndex = -1;
    this.bytes = bytes;
    this.nodes = nodes;
    this.buffers = buffers;
    this.dictionaries = dictionaries;
    this.metadataVersion = metadataVersion;
  }
  visit(node) {
    return super.visit(node instanceof Field2 ? node.type : node);
  }
  visitNull(type, { length: length2 } = this.nextFieldNode()) {
    return makeData({ type, length: length2 });
  }
  visitBool(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitInt(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitFloat(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitUtf8(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), data: this.readData(type) });
  }
  visitLargeUtf8(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), data: this.readData(type) });
  }
  visitBinary(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), data: this.readData(type) });
  }
  visitLargeBinary(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), data: this.readData(type) });
  }
  visitFixedSizeBinary(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitDate(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitTimestamp(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitTime(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitDecimal(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitList(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), "child": this.visit(type.children[0]) });
  }
  visitStruct(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), children: this.visitMany(type.children) });
  }
  visitUnion(type, { length: length2, nullCount } = this.nextFieldNode()) {
    if (this.metadataVersion < MetadataVersion.V5) {
      this.readNullBitmap(type, nullCount);
    }
    return type.mode === UnionMode$1.Sparse ? this.visitSparseUnion(type, { length: length2, nullCount }) : this.visitDenseUnion(type, { length: length2, nullCount });
  }
  visitDenseUnion(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, typeIds: this.readTypeIds(type), valueOffsets: this.readOffsets(type), children: this.visitMany(type.children) });
  }
  visitSparseUnion(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, typeIds: this.readTypeIds(type), children: this.visitMany(type.children) });
  }
  visitDictionary(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type.indices), dictionary: this.readDictionary(type) });
  }
  visitInterval(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitDuration(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), data: this.readData(type) });
  }
  visitFixedSizeList(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), "child": this.visit(type.children[0]) });
  }
  visitMap(type, { length: length2, nullCount } = this.nextFieldNode()) {
    return makeData({ type, length: length2, nullCount, nullBitmap: this.readNullBitmap(type, nullCount), valueOffsets: this.readOffsets(type), "child": this.visit(type.children[0]) });
  }
  nextFieldNode() {
    return this.nodes[++this.nodesIndex];
  }
  nextBufferRange() {
    return this.buffers[++this.buffersIndex];
  }
  readNullBitmap(type, nullCount, buffer2 = this.nextBufferRange()) {
    return nullCount > 0 && this.readData(type, buffer2) || new Uint8Array(0);
  }
  readOffsets(type, buffer2) {
    return this.readData(type, buffer2);
  }
  readTypeIds(type, buffer2) {
    return this.readData(type, buffer2);
  }
  readData(_type, { length: length2, offset: offset2 } = this.nextBufferRange()) {
    return this.bytes.subarray(offset2, offset2 + length2);
  }
  readDictionary(type) {
    return this.dictionaries.get(type.id);
  }
}
class JSONVectorLoader extends VectorLoader {
  constructor(sources, nodes, buffers, dictionaries, metadataVersion) {
    super(new Uint8Array(0), nodes, buffers, dictionaries, metadataVersion);
    this.sources = sources;
  }
  readNullBitmap(_type, nullCount, { offset: offset2 } = this.nextBufferRange()) {
    return nullCount <= 0 ? new Uint8Array(0) : packBools(this.sources[offset2]);
  }
  readOffsets(_type, { offset: offset2 } = this.nextBufferRange()) {
    return toArrayBufferView(Uint8Array, toArrayBufferView(_type.OffsetArrayType, this.sources[offset2]));
  }
  readTypeIds(type, { offset: offset2 } = this.nextBufferRange()) {
    return toArrayBufferView(Uint8Array, toArrayBufferView(type.ArrayType, this.sources[offset2]));
  }
  readData(type, { offset: offset2 } = this.nextBufferRange()) {
    const { sources } = this;
    if (DataType.isTimestamp(type)) {
      return toArrayBufferView(Uint8Array, Int64.convertArray(sources[offset2]));
    } else if ((DataType.isInt(type) || DataType.isTime(type)) && type.bitWidth === 64 || DataType.isDuration(type)) {
      return toArrayBufferView(Uint8Array, Int64.convertArray(sources[offset2]));
    } else if (DataType.isDate(type) && type.unit === DateUnit$1.MILLISECOND) {
      return toArrayBufferView(Uint8Array, Int64.convertArray(sources[offset2]));
    } else if (DataType.isDecimal(type)) {
      return toArrayBufferView(Uint8Array, Int128.convertArray(sources[offset2]));
    } else if (DataType.isBinary(type) || DataType.isLargeBinary(type) || DataType.isFixedSizeBinary(type)) {
      return binaryDataFromJSON(sources[offset2]);
    } else if (DataType.isBool(type)) {
      return packBools(sources[offset2]);
    } else if (DataType.isUtf8(type) || DataType.isLargeUtf8(type)) {
      return encodeUtf8$1(sources[offset2].join(""));
    } else if (DataType.isInterval(type)) {
      switch (type.unit) {
        case IntervalUnit$1.DAY_TIME:
          return toIntervalDayTimeInt32Array(sources[offset2]);
        case IntervalUnit$1.MONTH_DAY_NANO:
          return toIntervalMonthDayNanoInt32Array(sources[offset2]);
      }
    }
    return toArrayBufferView(Uint8Array, toArrayBufferView(type.ArrayType, sources[offset2].map((x) => +x)));
  }
}
function binaryDataFromJSON(values2) {
  const joined = values2.join("");
  const data2 = new Uint8Array(joined.length / 2);
  for (let i = 0; i < joined.length; i += 2) {
    data2[i >> 1] = Number.parseInt(joined.slice(i, i + 2), 16);
  }
  return data2;
}
class CompressedVectorLoader extends VectorLoader {
  constructor(bodyChunks, nodes, buffers, dictionaries, metadataVersion) {
    super(new Uint8Array(0), nodes, buffers, dictionaries, metadataVersion);
    this.bodyChunks = bodyChunks;
  }
  readData(_type, _buffer = this.nextBufferRange()) {
    return this.bodyChunks[this.buffersIndex];
  }
}
class TypeComparator extends Visitor {
  compareSchemas(schema, other) {
    return schema === other || other instanceof schema.constructor && this.compareManyFields(schema.fields, other.fields);
  }
  compareManyFields(fields, others) {
    return fields === others || Array.isArray(fields) && Array.isArray(others) && fields.length === others.length && fields.every((f, i) => this.compareFields(f, others[i]));
  }
  compareFields(field2, other) {
    return field2 === other || other instanceof field2.constructor && field2.name === other.name && field2.nullable === other.nullable && this.visit(field2.type, other.type);
  }
}
function compareConstructor(type, other) {
  return other instanceof type.constructor;
}
function compareAny(type, other) {
  return type === other || compareConstructor(type, other);
}
function compareInt(type, other) {
  return type === other || compareConstructor(type, other) && type.bitWidth === other.bitWidth && type.isSigned === other.isSigned;
}
function compareFloat(type, other) {
  return type === other || compareConstructor(type, other) && type.precision === other.precision;
}
function compareFixedSizeBinary(type, other) {
  return type === other || compareConstructor(type, other) && type.byteWidth === other.byteWidth;
}
function compareDate(type, other) {
  return type === other || compareConstructor(type, other) && type.unit === other.unit;
}
function compareTimestamp(type, other) {
  return type === other || compareConstructor(type, other) && type.unit === other.unit && type.timezone === other.timezone;
}
function compareTime(type, other) {
  return type === other || compareConstructor(type, other) && type.unit === other.unit && type.bitWidth === other.bitWidth;
}
function compareList(type, other) {
  return type === other || compareConstructor(type, other) && type.children.length === other.children.length && instance.compareManyFields(type.children, other.children);
}
function compareStruct(type, other) {
  return type === other || compareConstructor(type, other) && type.children.length === other.children.length && instance.compareManyFields(type.children, other.children);
}
function compareUnion(type, other) {
  return type === other || compareConstructor(type, other) && type.mode === other.mode && type.typeIds.every((x, i) => x === other.typeIds[i]) && instance.compareManyFields(type.children, other.children);
}
function compareDictionary(type, other) {
  return type === other || compareConstructor(type, other) && type.id === other.id && type.isOrdered === other.isOrdered && instance.visit(type.indices, other.indices) && instance.visit(type.dictionary, other.dictionary);
}
function compareInterval(type, other) {
  return type === other || compareConstructor(type, other) && type.unit === other.unit;
}
function compareDuration(type, other) {
  return type === other || compareConstructor(type, other) && type.unit === other.unit;
}
function compareFixedSizeList(type, other) {
  return type === other || compareConstructor(type, other) && type.listSize === other.listSize && type.children.length === other.children.length && instance.compareManyFields(type.children, other.children);
}
function compareMap(type, other) {
  return type === other || compareConstructor(type, other) && type.keysSorted === other.keysSorted && type.children.length === other.children.length && instance.compareManyFields(type.children, other.children);
}
TypeComparator.prototype.visitNull = compareAny;
TypeComparator.prototype.visitBool = compareAny;
TypeComparator.prototype.visitInt = compareInt;
TypeComparator.prototype.visitInt8 = compareInt;
TypeComparator.prototype.visitInt16 = compareInt;
TypeComparator.prototype.visitInt32 = compareInt;
TypeComparator.prototype.visitInt64 = compareInt;
TypeComparator.prototype.visitUint8 = compareInt;
TypeComparator.prototype.visitUint16 = compareInt;
TypeComparator.prototype.visitUint32 = compareInt;
TypeComparator.prototype.visitUint64 = compareInt;
TypeComparator.prototype.visitFloat = compareFloat;
TypeComparator.prototype.visitFloat16 = compareFloat;
TypeComparator.prototype.visitFloat32 = compareFloat;
TypeComparator.prototype.visitFloat64 = compareFloat;
TypeComparator.prototype.visitUtf8 = compareAny;
TypeComparator.prototype.visitLargeUtf8 = compareAny;
TypeComparator.prototype.visitBinary = compareAny;
TypeComparator.prototype.visitLargeBinary = compareAny;
TypeComparator.prototype.visitFixedSizeBinary = compareFixedSizeBinary;
TypeComparator.prototype.visitDate = compareDate;
TypeComparator.prototype.visitDateDay = compareDate;
TypeComparator.prototype.visitDateMillisecond = compareDate;
TypeComparator.prototype.visitTimestamp = compareTimestamp;
TypeComparator.prototype.visitTimestampSecond = compareTimestamp;
TypeComparator.prototype.visitTimestampMillisecond = compareTimestamp;
TypeComparator.prototype.visitTimestampMicrosecond = compareTimestamp;
TypeComparator.prototype.visitTimestampNanosecond = compareTimestamp;
TypeComparator.prototype.visitTime = compareTime;
TypeComparator.prototype.visitTimeSecond = compareTime;
TypeComparator.prototype.visitTimeMillisecond = compareTime;
TypeComparator.prototype.visitTimeMicrosecond = compareTime;
TypeComparator.prototype.visitTimeNanosecond = compareTime;
TypeComparator.prototype.visitDecimal = compareAny;
TypeComparator.prototype.visitList = compareList;
TypeComparator.prototype.visitStruct = compareStruct;
TypeComparator.prototype.visitUnion = compareUnion;
TypeComparator.prototype.visitDenseUnion = compareUnion;
TypeComparator.prototype.visitSparseUnion = compareUnion;
TypeComparator.prototype.visitDictionary = compareDictionary;
TypeComparator.prototype.visitInterval = compareInterval;
TypeComparator.prototype.visitIntervalDayTime = compareInterval;
TypeComparator.prototype.visitIntervalYearMonth = compareInterval;
TypeComparator.prototype.visitIntervalMonthDayNano = compareInterval;
TypeComparator.prototype.visitDuration = compareDuration;
TypeComparator.prototype.visitDurationSecond = compareDuration;
TypeComparator.prototype.visitDurationMillisecond = compareDuration;
TypeComparator.prototype.visitDurationMicrosecond = compareDuration;
TypeComparator.prototype.visitDurationNanosecond = compareDuration;
TypeComparator.prototype.visitFixedSizeList = compareFixedSizeList;
TypeComparator.prototype.visitMap = compareMap;
const instance = new TypeComparator();
function compareSchemas(schema, other) {
  return instance.compareSchemas(schema, other);
}
function distributeVectorsIntoRecordBatches(schema, vecs) {
  return uniformlyDistributeChunksAcrossRecordBatches(schema, vecs.map((v) => v.data.concat()));
}
function uniformlyDistributeChunksAcrossRecordBatches(schema, cols) {
  const fields = [...schema.fields];
  const batches = [];
  const memo = { numBatches: cols.reduce((n, c) => Math.max(n, c.length), 0) };
  let numBatches = 0, batchLength = 0;
  let i = -1;
  const numColumns = cols.length;
  let child, children = [];
  while (memo.numBatches-- > 0) {
    for (batchLength = Number.POSITIVE_INFINITY, i = -1; ++i < numColumns; ) {
      children[i] = child = cols[i].shift();
      batchLength = Math.min(batchLength, child ? child.length : batchLength);
    }
    if (Number.isFinite(batchLength)) {
      children = distributeChildren(fields, batchLength, children, cols, memo);
      if (batchLength > 0) {
        batches[numBatches++] = makeData({
          type: new Struct(fields),
          length: batchLength,
          nullCount: 0,
          children: children.slice()
        });
      }
    }
  }
  return [
    schema = schema.assign(fields),
    batches.map((data2) => new RecordBatch3(schema, data2))
  ];
}
function distributeChildren(fields, batchLength, children, columns2, memo) {
  var _a2;
  const nullBitmapSize = (batchLength + 63 & -64) >> 3;
  for (let i = -1, n = columns2.length; ++i < n; ) {
    const child = children[i];
    const length2 = child === null || child === void 0 ? void 0 : child.length;
    if (length2 >= batchLength) {
      if (length2 === batchLength) {
        children[i] = child;
      } else {
        children[i] = child.slice(0, batchLength);
        memo.numBatches = Math.max(memo.numBatches, columns2[i].unshift(child.slice(batchLength, length2 - batchLength)));
      }
    } else {
      const field2 = fields[i];
      fields[i] = field2.clone({ nullable: true });
      children[i] = (_a2 = child === null || child === void 0 ? void 0 : child._changeLengthAndBackfillNullBitmap(batchLength)) !== null && _a2 !== void 0 ? _a2 : makeData({
        type: field2.type,
        length: batchLength,
        nullCount: batchLength,
        nullBitmap: new Uint8Array(nullBitmapSize)
      });
    }
  }
  return children;
}
var _a$1;
let Table$2 = class Table {
  constructor(...args) {
    var _b2, _c2;
    if (args.length === 0) {
      this.batches = [];
      this.schema = new Schema2([]);
      this._offsets = [0];
      return this;
    }
    let schema;
    let offsets;
    if (args[0] instanceof Schema2) {
      schema = args.shift();
    }
    if (args.at(-1) instanceof Uint32Array) {
      offsets = args.pop();
    }
    const unwrap = (x) => {
      if (x) {
        if (x instanceof RecordBatch3) {
          return [x];
        } else if (x instanceof Table) {
          return x.batches;
        } else if (x instanceof Data) {
          if (x.type instanceof Struct) {
            return [new RecordBatch3(new Schema2(x.type.children), x)];
          }
        } else if (Array.isArray(x)) {
          return x.flatMap((v) => unwrap(v));
        } else if (typeof x[Symbol.iterator] === "function") {
          return [...x].flatMap((v) => unwrap(v));
        } else if (typeof x === "object") {
          const keys2 = Object.keys(x);
          const vecs = keys2.map((k) => new Vector([x[k]]));
          const batchSchema = schema !== null && schema !== void 0 ? schema : new Schema2(keys2.map((k, i) => new Field2(String(k), vecs[i].type, vecs[i].nullable)));
          const [, batches2] = distributeVectorsIntoRecordBatches(batchSchema, vecs);
          return batches2.length === 0 ? [new RecordBatch3(x)] : batches2;
        }
      }
      return [];
    };
    const batches = args.flatMap((v) => unwrap(v));
    schema = (_c2 = schema !== null && schema !== void 0 ? schema : (_b2 = batches[0]) === null || _b2 === void 0 ? void 0 : _b2.schema) !== null && _c2 !== void 0 ? _c2 : new Schema2([]);
    if (!(schema instanceof Schema2)) {
      throw new TypeError("Table constructor expects a [Schema, RecordBatch[]] pair.");
    }
    for (const batch of batches) {
      if (!(batch instanceof RecordBatch3)) {
        throw new TypeError("Table constructor expects a [Schema, RecordBatch[]] pair.");
      }
      if (!compareSchemas(schema, batch.schema)) {
        throw new TypeError("Table and inner RecordBatch schemas must be equivalent.");
      }
    }
    this.schema = schema;
    this.batches = batches;
    this._offsets = offsets !== null && offsets !== void 0 ? offsets : computeChunkOffsets(this.data);
  }
  /**
   * The contiguous {@link RecordBatch `RecordBatch`} chunks of the Table rows.
   */
  get data() {
    return this.batches.map(({ data: data2 }) => data2);
  }
  /**
   * The number of columns in this Table.
   */
  get numCols() {
    return this.schema.fields.length;
  }
  /**
   * The number of rows in this Table.
   */
  get numRows() {
    return this.data.reduce((numRows, data2) => numRows + data2.length, 0);
  }
  /**
   * The number of null rows in this Table.
   */
  get nullCount() {
    if (this._nullCount === -1) {
      this._nullCount = computeChunkNullCounts(this.data);
    }
    return this._nullCount;
  }
  /**
   * Check whether an element is null.
   *
   * @param index The index at which to read the validity bitmap.
   */
  // @ts-ignore
  isValid(index) {
    return false;
  }
  /**
   * Get an element value by position.
   *
   * @param index The index of the element to read.
   */
  // @ts-ignore
  get(index) {
    return null;
  }
  /**
    * Get an element value by position.
    * @param index The index of the element to read. A negative index will count back from the last element.
    */
  // @ts-ignore
  at(index) {
    return this.get(wrapIndex(index, this.numRows));
  }
  /**
   * Set an element value by position.
   *
   * @param index The index of the element to write.
   * @param value The value to set.
   */
  // @ts-ignore
  set(index, value2) {
    return;
  }
  /**
   * Retrieve the index of the first occurrence of a value in an Vector.
   *
   * @param element The value to locate in the Vector.
   * @param offset The index at which to begin the search. If offset is omitted, the search starts at index 0.
   */
  // @ts-ignore
  indexOf(element, offset2) {
    return -1;
  }
  /**
   * Iterator for rows in this Table.
   */
  [Symbol.iterator]() {
    if (this.batches.length > 0) {
      return instance$2.visit(new Vector(this.data));
    }
    return new Array(0)[Symbol.iterator]();
  }
  /**
   * Return a JavaScript Array of the Table rows.
   *
   * @returns An Array of Table rows.
   */
  toArray() {
    return [...this];
  }
  /**
   * Returns a string representation of the Table rows.
   *
   * @returns A string representation of the Table rows.
   */
  toString() {
    return `[
  ${this.toArray().join(",\n  ")}
]`;
  }
  /**
   * Combines two or more Tables of the same schema.
   *
   * @param others Additional Tables to add to the end of this Tables.
   */
  concat(...others) {
    const schema = this.schema;
    const data2 = this.data.concat(others.flatMap(({ data: data3 }) => data3));
    return new Table(schema, data2.map((data3) => new RecordBatch3(schema, data3)));
  }
  /**
   * Return a zero-copy sub-section of this Table.
   *
   * @param begin The beginning of the specified portion of the Table.
   * @param end The end of the specified portion of the Table. This is exclusive of the element at the index 'end'.
   */
  slice(begin, end) {
    const schema = this.schema;
    [begin, end] = clampRange({ length: this.numRows }, begin, end);
    const data2 = sliceChunks(this.data, this._offsets, begin, end);
    return new Table(schema, data2.map((chunk) => new RecordBatch3(schema, chunk)));
  }
  /**
   * Returns a child Vector by name, or null if this Vector has no child with the given name.
   *
   * @param name The name of the child to retrieve.
   */
  getChild(name2) {
    return this.getChildAt(this.schema.fields.findIndex((f) => f.name === name2));
  }
  /**
   * Returns a child Vector by index, or null if this Vector has no child at the supplied index.
   *
   * @param index The index of the child to retrieve.
   */
  getChildAt(index) {
    if (index > -1 && index < this.schema.fields.length) {
      const data2 = this.data.map((data3) => data3.children[index]);
      if (data2.length === 0) {
        const { type } = this.schema.fields[index];
        const empty2 = makeData({ type, length: 0, nullCount: 0 });
        data2.push(empty2._changeLengthAndBackfillNullBitmap(this.numRows));
      }
      return new Vector(data2);
    }
    return null;
  }
  /**
   * Sets a child Vector by name.
   *
   * @param name The name of the child to overwrite.
   * @returns A new Table with the supplied child for the specified name.
   */
  setChild(name2, child) {
    var _b2;
    return this.setChildAt((_b2 = this.schema.fields) === null || _b2 === void 0 ? void 0 : _b2.findIndex((f) => f.name === name2), child);
  }
  setChildAt(index, child) {
    let schema = this.schema;
    let batches = [...this.batches];
    if (index > -1 && index < this.numCols) {
      if (!child) {
        child = new Vector([makeData({ type: new Null2(), length: this.numRows })]);
      }
      const fields = schema.fields.slice();
      const field2 = fields[index].clone({ type: child.type });
      const children = this.schema.fields.map((_, i) => this.getChildAt(i));
      [fields[index], children[index]] = [field2, child];
      [schema, batches] = distributeVectorsIntoRecordBatches(schema, children);
    }
    return new Table(schema, batches);
  }
  /**
   * Construct a new Table containing only specified columns.
   *
   * @param columnNames Names of columns to keep.
   * @returns A new Table of columns matching the specified names.
   */
  select(columnNames) {
    const nameToIndex = this.schema.fields.reduce((m, f, i) => m.set(f.name, i), /* @__PURE__ */ new Map());
    return this.selectAt(columnNames.map((columnName) => nameToIndex.get(columnName)).filter((x) => x > -1));
  }
  /**
   * Construct a new Table containing only columns at the specified indices.
   *
   * @param columnIndices Indices of columns to keep.
   * @returns A new Table of columns at the specified indices.
   */
  selectAt(columnIndices) {
    const schema = this.schema.selectAt(columnIndices);
    const data2 = this.batches.map((batch) => batch.selectAt(columnIndices));
    return new Table(schema, data2);
  }
  assign(other) {
    const fields = this.schema.fields;
    const [indices, oldToNew] = other.schema.fields.reduce((memo, f2, newIdx) => {
      const [indices2, oldToNew2] = memo;
      const i = fields.findIndex((f) => f.name === f2.name);
      ~i ? oldToNew2[i] = newIdx : indices2.push(newIdx);
      return memo;
    }, [[], []]);
    const schema = this.schema.assign(other.schema);
    const columns2 = [
      ...fields.map((_, i) => [i, oldToNew[i]]).map(([i, j]) => j === void 0 ? this.getChildAt(i) : other.getChildAt(j)),
      ...indices.map((i) => other.getChildAt(i))
    ].filter(Boolean);
    return new Table(...distributeVectorsIntoRecordBatches(schema, columns2));
  }
};
_a$1 = Symbol.toStringTag;
Table$2[_a$1] = ((proto) => {
  proto.schema = null;
  proto.batches = [];
  proto._offsets = new Uint32Array([0]);
  proto._nullCount = -1;
  proto[Symbol.isConcatSpreadable] = true;
  proto["isValid"] = wrapChunkedCall1(isChunkedValid);
  proto["get"] = wrapChunkedCall1(instance$4.getVisitFn(Type$1.Struct));
  proto["set"] = wrapChunkedCall2(instance$5.getVisitFn(Type$1.Struct));
  proto["indexOf"] = wrapChunkedIndexOf(instance$3.getVisitFn(Type$1.Struct));
  return "Table";
})(Table$2.prototype);
var _a;
class RecordBatch3 {
  constructor(...args) {
    switch (args.length) {
      case 2: {
        [this.schema] = args;
        if (!(this.schema instanceof Schema2)) {
          throw new TypeError("RecordBatch constructor expects a [Schema, Data] pair.");
        }
        [
          ,
          this.data = makeData({
            nullCount: 0,
            type: new Struct(this.schema.fields),
            children: this.schema.fields.map((f) => makeData({ type: f.type, nullCount: 0 }))
          })
        ] = args;
        if (!(this.data instanceof Data)) {
          throw new TypeError("RecordBatch constructor expects a [Schema, Data] pair.");
        }
        [this.schema, this.data] = ensureSameLengthData(this.schema, this.data.children);
        break;
      }
      case 1: {
        const [obj] = args;
        const { fields, children, length: length2 } = Object.keys(obj).reduce((memo, name2, i) => {
          memo.children[i] = obj[name2];
          memo.length = Math.max(memo.length, obj[name2].length);
          memo.fields[i] = Field2.new({ name: name2, type: obj[name2].type, nullable: true });
          return memo;
        }, {
          length: 0,
          fields: new Array(),
          children: new Array()
        });
        const schema = new Schema2(fields);
        const data2 = makeData({ type: new Struct(fields), length: length2, children, nullCount: 0 });
        [this.schema, this.data] = ensureSameLengthData(schema, data2.children, length2);
        break;
      }
      default:
        throw new TypeError("RecordBatch constructor expects an Object mapping names to child Data, or a [Schema, Data] pair.");
    }
  }
  get dictionaries() {
    return this._dictionaries || (this._dictionaries = collectDictionaries(this.schema.fields, this.data.children));
  }
  /**
   * The number of columns in this RecordBatch.
   */
  get numCols() {
    return this.schema.fields.length;
  }
  /**
   * The number of rows in this RecordBatch.
   */
  get numRows() {
    return this.data.length;
  }
  /**
   * The number of null rows in this RecordBatch.
   */
  get nullCount() {
    return this.data.nullCount;
  }
  /**
   * Check whether an row is null.
   * @param index The index at which to read the validity bitmap.
   */
  isValid(index) {
    return this.data.getValid(index);
  }
  /**
   * Get a row by position.
   * @param index The index of the row to read.
   */
  get(index) {
    return instance$4.visit(this.data, index);
  }
  /**
    * Get a row value by position.
    * @param index The index of the row to read. A negative index will count back from the last row.
    */
  at(index) {
    return this.get(wrapIndex(index, this.numRows));
  }
  /**
   * Set a row by position.
   * @param index The index of the row to write.
   * @param value The value to set.
   */
  set(index, value2) {
    return instance$5.visit(this.data, index, value2);
  }
  /**
   * Retrieve the index of the first occurrence of a row in an RecordBatch.
   * @param element The row to locate in the RecordBatch.
   * @param offset The index at which to begin the search. If offset is omitted, the search starts at index 0.
   */
  indexOf(element, offset2) {
    return instance$3.visit(this.data, element, offset2);
  }
  /**
   * Iterator for rows in this RecordBatch.
   */
  [Symbol.iterator]() {
    return instance$2.visit(new Vector([this.data]));
  }
  /**
   * Return a JavaScript Array of the RecordBatch rows.
   * @returns An Array of RecordBatch rows.
   */
  toArray() {
    return [...this];
  }
  /**
   * Combines two or more RecordBatch of the same schema.
   * @param others Additional RecordBatch to add to the end of this RecordBatch.
   */
  concat(...others) {
    return new Table$2(this.schema, [this, ...others]);
  }
  /**
   * Return a zero-copy sub-section of this RecordBatch.
   * @param start The beginning of the specified portion of the RecordBatch.
   * @param end The end of the specified portion of the RecordBatch. This is exclusive of the row at the index 'end'.
   */
  slice(begin, end) {
    const [slice2] = new Vector([this.data]).slice(begin, end).data;
    return new RecordBatch3(this.schema, slice2);
  }
  /**
   * Returns a child Vector by name, or null if this Vector has no child with the given name.
   * @param name The name of the child to retrieve.
   */
  getChild(name2) {
    var _b2;
    return this.getChildAt((_b2 = this.schema.fields) === null || _b2 === void 0 ? void 0 : _b2.findIndex((f) => f.name === name2));
  }
  /**
   * Returns a child Vector by index, or null if this Vector has no child at the supplied index.
   * @param index The index of the child to retrieve.
   */
  getChildAt(index) {
    if (index > -1 && index < this.schema.fields.length) {
      return new Vector([this.data.children[index]]);
    }
    return null;
  }
  /**
   * Sets a child Vector by name.
   * @param name The name of the child to overwrite.
   * @returns A new RecordBatch with the new child for the specified name.
   */
  setChild(name2, child) {
    var _b2;
    return this.setChildAt((_b2 = this.schema.fields) === null || _b2 === void 0 ? void 0 : _b2.findIndex((f) => f.name === name2), child);
  }
  setChildAt(index, child) {
    let schema = this.schema;
    let data2 = this.data;
    if (index > -1 && index < this.numCols) {
      if (!child) {
        child = new Vector([makeData({ type: new Null2(), length: this.numRows })]);
      }
      const fields = schema.fields.slice();
      const children = data2.children.slice();
      const field2 = fields[index].clone({ type: child.type });
      [fields[index], children[index]] = [field2, child.data[0]];
      schema = new Schema2(fields, new Map(this.schema.metadata));
      data2 = makeData({ type: new Struct(fields), children });
    }
    return new RecordBatch3(schema, data2);
  }
  /**
   * Construct a new RecordBatch containing only specified columns.
   *
   * @param columnNames Names of columns to keep.
   * @returns A new RecordBatch of columns matching the specified names.
   */
  select(columnNames) {
    const schema = this.schema.select(columnNames);
    const type = new Struct(schema.fields);
    const children = [];
    for (const name2 of columnNames) {
      const index = this.schema.fields.findIndex((f) => f.name === name2);
      if (~index) {
        children[index] = this.data.children[index];
      }
    }
    return new RecordBatch3(schema, makeData({ type, length: this.numRows, children }));
  }
  /**
   * Construct a new RecordBatch containing only columns at the specified indices.
   *
   * @param columnIndices Indices of columns to keep.
   * @returns A new RecordBatch of columns matching at the specified indices.
   */
  selectAt(columnIndices) {
    const schema = this.schema.selectAt(columnIndices);
    const children = columnIndices.map((i) => this.data.children[i]).filter(Boolean);
    const subset = makeData({ type: new Struct(schema.fields), length: this.numRows, children });
    return new RecordBatch3(schema, subset);
  }
}
_a = Symbol.toStringTag;
RecordBatch3[_a] = ((proto) => {
  proto._nullCount = -1;
  proto[Symbol.isConcatSpreadable] = true;
  return "RecordBatch";
})(RecordBatch3.prototype);
function ensureSameLengthData(schema, chunks, maxLength = chunks.reduce((max2, col) => Math.max(max2, col.length), 0)) {
  var _b2;
  const fields = [...schema.fields];
  const children = [...chunks];
  const nullBitmapSize = (maxLength + 63 & -64) >> 3;
  for (const [idx, field2] of schema.fields.entries()) {
    const chunk = chunks[idx];
    if (!chunk || chunk.length !== maxLength) {
      fields[idx] = field2.clone({ nullable: true });
      children[idx] = (_b2 = chunk === null || chunk === void 0 ? void 0 : chunk._changeLengthAndBackfillNullBitmap(maxLength)) !== null && _b2 !== void 0 ? _b2 : makeData({
        type: field2.type,
        length: maxLength,
        nullCount: maxLength,
        nullBitmap: new Uint8Array(nullBitmapSize)
      });
    }
  }
  return [
    schema.assign(fields),
    makeData({ type: new Struct(fields), length: maxLength, children })
  ];
}
function collectDictionaries(fields, children, dictionaries = /* @__PURE__ */ new Map()) {
  var _b2, _c2;
  if (((_b2 = fields === null || fields === void 0 ? void 0 : fields.length) !== null && _b2 !== void 0 ? _b2 : 0) > 0 && (fields === null || fields === void 0 ? void 0 : fields.length) === (children === null || children === void 0 ? void 0 : children.length)) {
    for (let i = -1, n = fields.length; ++i < n; ) {
      const { type } = fields[i];
      const data2 = children[i];
      for (const next of [data2, ...((_c2 = data2 === null || data2 === void 0 ? void 0 : data2.dictionary) === null || _c2 === void 0 ? void 0 : _c2.data) || []]) {
        collectDictionaries(type.children, next === null || next === void 0 ? void 0 : next.children, dictionaries);
      }
      if (DataType.isDictionary(type)) {
        const { id } = type;
        if (!dictionaries.has(id)) {
          if (data2 === null || data2 === void 0 ? void 0 : data2.dictionary) {
            dictionaries.set(id, data2.dictionary);
          }
        } else if (dictionaries.get(id) !== data2.dictionary) {
          throw new Error(`Cannot create Schema containing two different dictionaries with the same Id`);
        }
      }
    }
  }
  return dictionaries;
}
class _InternalEmptyPlaceholderRecordBatch extends RecordBatch3 {
  constructor(schema) {
    const children = schema.fields.map((f) => makeData({ type: f.type }));
    const data2 = makeData({ type: new Struct(schema.fields), nullCount: 0, children });
    super(schema, data2);
  }
}
const invalidMessageType$1 = (type) => `Expected ${MessageHeader$1[type]} Message in stream, but was null or length 0.`;
const nullMessage = (type) => `Header pointer of flatbuffer-encoded ${MessageHeader$1[type]} Message is null or length 0.`;
const invalidMessageMetadata$1 = (expected, actual) => `Expected to read ${expected} metadata bytes, but only read ${actual}.`;
const invalidMessageBodyLength$1 = (expected, actual) => `Expected to read ${expected} bytes for message body, but only read ${actual}.`;
class MessageReader {
  constructor(source2) {
    this.source = source2 instanceof ByteStream ? source2 : new ByteStream(source2);
  }
  [Symbol.iterator]() {
    return this;
  }
  next() {
    let r;
    if ((r = this.readMetadataLength()).done) {
      return ITERATOR_DONE;
    }
    if (r.value === -1 && (r = this.readMetadataLength()).done) {
      return ITERATOR_DONE;
    }
    if ((r = this.readMetadata(r.value)).done) {
      return ITERATOR_DONE;
    }
    return r;
  }
  throw(value2) {
    return this.source.throw(value2);
  }
  return(value2) {
    return this.source.return(value2);
  }
  readMessage(type) {
    let r;
    if ((r = this.next()).done) {
      return null;
    }
    if (type != null && r.value.headerType !== type) {
      throw new Error(invalidMessageType$1(type));
    }
    return r.value;
  }
  readMessageBody(bodyLength) {
    if (bodyLength <= 0) {
      return new Uint8Array(0);
    }
    const buf2 = toUint8Array(this.source.read(bodyLength));
    if (buf2.byteLength < bodyLength) {
      throw new Error(invalidMessageBodyLength$1(bodyLength, buf2.byteLength));
    }
    return (
      /* 1. */
      buf2.byteOffset % 8 === 0 && /* 2. */
      buf2.byteOffset + buf2.byteLength <= buf2.buffer.byteLength ? buf2 : buf2.slice()
    );
  }
  readSchema(throwIfNull = false) {
    const type = MessageHeader$1.Schema;
    const message = this.readMessage(type);
    const schema = message === null || message === void 0 ? void 0 : message.header();
    if (throwIfNull && !schema) {
      throw new Error(nullMessage(type));
    }
    return schema;
  }
  readMetadataLength() {
    const buf2 = this.source.read(PADDING);
    const bb = buf2 && new ByteBuffer$2(buf2);
    const len = (bb === null || bb === void 0 ? void 0 : bb.readInt32(0)) || 0;
    return { done: len === 0, value: len };
  }
  readMetadata(metadataLength) {
    const buf2 = this.source.read(metadataLength);
    if (!buf2) {
      return ITERATOR_DONE;
    }
    if (buf2.byteLength < metadataLength) {
      throw new Error(invalidMessageMetadata$1(metadataLength, buf2.byteLength));
    }
    return { done: false, value: Message2.decode(buf2) };
  }
}
class AsyncMessageReader {
  constructor(source2, byteLength) {
    this.source = source2 instanceof AsyncByteStream ? source2 : isFileHandle(source2) ? new AsyncRandomAccessFile(source2, byteLength) : new AsyncByteStream(source2);
  }
  [Symbol.asyncIterator]() {
    return this;
  }
  next() {
    return __awaiter(this, void 0, void 0, function* () {
      let r;
      if ((r = yield this.readMetadataLength()).done) {
        return ITERATOR_DONE;
      }
      if (r.value === -1 && (r = yield this.readMetadataLength()).done) {
        return ITERATOR_DONE;
      }
      if ((r = yield this.readMetadata(r.value)).done) {
        return ITERATOR_DONE;
      }
      return r;
    });
  }
  throw(value2) {
    return __awaiter(this, void 0, void 0, function* () {
      return yield this.source.throw(value2);
    });
  }
  return(value2) {
    return __awaiter(this, void 0, void 0, function* () {
      return yield this.source.return(value2);
    });
  }
  readMessage(type) {
    return __awaiter(this, void 0, void 0, function* () {
      let r;
      if ((r = yield this.next()).done) {
        return null;
      }
      if (type != null && r.value.headerType !== type) {
        throw new Error(invalidMessageType$1(type));
      }
      return r.value;
    });
  }
  readMessageBody(bodyLength) {
    return __awaiter(this, void 0, void 0, function* () {
      if (bodyLength <= 0) {
        return new Uint8Array(0);
      }
      const buf2 = toUint8Array(yield this.source.read(bodyLength));
      if (buf2.byteLength < bodyLength) {
        throw new Error(invalidMessageBodyLength$1(bodyLength, buf2.byteLength));
      }
      return (
        /* 1. */
        buf2.byteOffset % 8 === 0 && /* 2. */
        buf2.byteOffset + buf2.byteLength <= buf2.buffer.byteLength ? buf2 : buf2.slice()
      );
    });
  }
  readSchema() {
    return __awaiter(this, arguments, void 0, function* (throwIfNull = false) {
      const type = MessageHeader$1.Schema;
      const message = yield this.readMessage(type);
      const schema = message === null || message === void 0 ? void 0 : message.header();
      if (throwIfNull && !schema) {
        throw new Error(nullMessage(type));
      }
      return schema;
    });
  }
  readMetadataLength() {
    return __awaiter(this, void 0, void 0, function* () {
      const buf2 = yield this.source.read(PADDING);
      const bb = buf2 && new ByteBuffer$2(buf2);
      const len = (bb === null || bb === void 0 ? void 0 : bb.readInt32(0)) || 0;
      return { done: len === 0, value: len };
    });
  }
  readMetadata(metadataLength) {
    return __awaiter(this, void 0, void 0, function* () {
      const buf2 = yield this.source.read(metadataLength);
      if (!buf2) {
        return ITERATOR_DONE;
      }
      if (buf2.byteLength < metadataLength) {
        throw new Error(invalidMessageMetadata$1(metadataLength, buf2.byteLength));
      }
      return { done: false, value: Message2.decode(buf2) };
    });
  }
}
class JSONMessageReader extends MessageReader {
  constructor(source2) {
    super(new Uint8Array(0));
    this._schema = false;
    this._body = [];
    this._batchIndex = 0;
    this._dictionaryIndex = 0;
    this._json = source2 instanceof ArrowJSON ? source2 : new ArrowJSON(source2);
  }
  next() {
    const { _json } = this;
    if (!this._schema) {
      this._schema = true;
      const message = Message2.fromJSON(_json.schema, MessageHeader$1.Schema);
      return { done: false, value: message };
    }
    if (this._dictionaryIndex < _json.dictionaries.length) {
      const batch = _json.dictionaries[this._dictionaryIndex++];
      this._body = batch["data"]["columns"];
      const message = Message2.fromJSON(batch, MessageHeader$1.DictionaryBatch);
      return { done: false, value: message };
    }
    if (this._batchIndex < _json.batches.length) {
      const batch = _json.batches[this._batchIndex++];
      this._body = batch["columns"];
      const message = Message2.fromJSON(batch, MessageHeader$1.RecordBatch);
      return { done: false, value: message };
    }
    this._body = [];
    return ITERATOR_DONE;
  }
  readMessageBody(_bodyLength) {
    return flattenDataSources(this._body);
    function flattenDataSources(xs) {
      return (xs || []).reduce((buffers, column) => [
        ...buffers,
        ...column["VALIDITY"] && [column["VALIDITY"]] || [],
        ...column["TYPE_ID"] && [column["TYPE_ID"]] || [],
        ...column["OFFSET"] && [column["OFFSET"]] || [],
        ...column["DATA"] && [column["DATA"]] || [],
        ...flattenDataSources(column["children"])
      ], []);
    }
  }
  readMessage(type) {
    let r;
    if ((r = this.next()).done) {
      return null;
    }
    if (type != null && r.value.headerType !== type) {
      throw new Error(invalidMessageType$1(type));
    }
    return r.value;
  }
  readSchema() {
    const type = MessageHeader$1.Schema;
    const message = this.readMessage(type);
    const schema = message === null || message === void 0 ? void 0 : message.header();
    if (!message || !schema) {
      throw new Error(nullMessage(type));
    }
    return schema;
  }
}
const PADDING = 4;
const MAGIC_STR = "ARROW1";
const MAGIC$1 = new Uint8Array(MAGIC_STR.length);
for (let i = 0; i < MAGIC_STR.length; i += 1) {
  MAGIC$1[i] = MAGIC_STR.codePointAt(i);
}
function checkForMagicArrowString(buffer2, index = 0) {
  for (let i = -1, n = MAGIC$1.length; ++i < n; ) {
    if (MAGIC$1[i] !== buffer2[index + i]) {
      return false;
    }
  }
  return true;
}
const magicLength = MAGIC$1.length;
const magicAndPadding = magicLength + PADDING;
const magicX2AndPadding = magicLength * 2 + PADDING;
class Lz4FrameValidator {
  constructor() {
    this.LZ4_FRAME_MAGIC = new Uint8Array([4, 34, 77, 24]);
    this.MIN_HEADER_LENGTH = 7;
  }
  isValidCodecEncode(codec) {
    const testData = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]);
    const compressed = codec.encode(testData);
    return this._isValidCompressed(compressed);
  }
  _isValidCompressed(buffer2) {
    return this._hasMinimumLength(buffer2) && this._hasValidMagicNumber(buffer2) && this._hasValidVersion(buffer2);
  }
  _hasMinimumLength(buffer2) {
    return buffer2.length >= this.MIN_HEADER_LENGTH;
  }
  _hasValidMagicNumber(buffer2) {
    return this.LZ4_FRAME_MAGIC.every((byte, i) => buffer2[i] === byte);
  }
  _hasValidVersion(buffer2) {
    const flg = buffer2[4];
    const versionBits = (flg & 192) >> 6;
    return versionBits === 1;
  }
}
class ZstdValidator {
  constructor() {
    this.ZSTD_MAGIC = new Uint8Array([40, 181, 47, 253]);
    this.MIN_HEADER_LENGTH = 6;
  }
  isValidCodecEncode(codec) {
    const testData = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]);
    const compressed = codec.encode(testData);
    return this._isValidCompressed(compressed);
  }
  _isValidCompressed(buffer2) {
    return this._hasMinimumLength(buffer2) && this._hasValidMagicNumber(buffer2);
  }
  _hasMinimumLength(buffer2) {
    return buffer2.length >= this.MIN_HEADER_LENGTH;
  }
  _hasValidMagicNumber(buffer2) {
    return this.ZSTD_MAGIC.every((byte, i) => buffer2[i] === byte);
  }
}
const compressionValidators = {
  [CompressionType.LZ4_FRAME]: new Lz4FrameValidator(),
  [CompressionType.ZSTD]: new ZstdValidator()
};
class _CompressionRegistry {
  constructor() {
    this.registry = {};
  }
  set(compression, codec) {
    if ((codec === null || codec === void 0 ? void 0 : codec.encode) && typeof codec.encode === "function" && !compressionValidators[compression].isValidCodecEncode(codec)) {
      throw new Error(`Encoder for ${CompressionType[compression]} is not valid.`);
    }
    this.registry[compression] = codec;
  }
  get(compression) {
    var _a2;
    return ((_a2 = this.registry) === null || _a2 === void 0 ? void 0 : _a2[compression]) || null;
  }
}
const compressionRegistry = new _CompressionRegistry();
const LENGTH_NO_COMPRESSED_DATA = -1;
const COMPRESS_LENGTH_PREFIX = 8;
class RecordBatchReader extends ReadableInterop {
  constructor(impl) {
    super();
    this._impl = impl;
  }
  get closed() {
    return this._impl.closed;
  }
  get schema() {
    return this._impl.schema;
  }
  get autoDestroy() {
    return this._impl.autoDestroy;
  }
  get dictionaries() {
    return this._impl.dictionaries;
  }
  get numDictionaries() {
    return this._impl.numDictionaries;
  }
  get numRecordBatches() {
    return this._impl.numRecordBatches;
  }
  get footer() {
    return this._impl.isFile() ? this._impl.footer : null;
  }
  isSync() {
    return this._impl.isSync();
  }
  isAsync() {
    return this._impl.isAsync();
  }
  isFile() {
    return this._impl.isFile();
  }
  isStream() {
    return this._impl.isStream();
  }
  next() {
    return this._impl.next();
  }
  throw(value2) {
    return this._impl.throw(value2);
  }
  return(value2) {
    return this._impl.return(value2);
  }
  cancel() {
    return this._impl.cancel();
  }
  reset(schema) {
    this._impl.reset(schema);
    this._DOMStream = void 0;
    this._nodeStream = void 0;
    return this;
  }
  open(options) {
    const opening = this._impl.open(options);
    return isPromise(opening) ? opening.then(() => this) : this;
  }
  readRecordBatch(index) {
    return this._impl.isFile() ? this._impl.readRecordBatch(index) : null;
  }
  [Symbol.iterator]() {
    return this._impl[Symbol.iterator]();
  }
  [Symbol.asyncIterator]() {
    return this._impl[Symbol.asyncIterator]();
  }
  toDOMStream() {
    return streamAdapters.toDOMStream(this.isSync() ? { [Symbol.iterator]: () => this } : { [Symbol.asyncIterator]: () => this });
  }
  toNodeStream() {
    return streamAdapters.toNodeStream(this.isSync() ? { [Symbol.iterator]: () => this } : { [Symbol.asyncIterator]: () => this }, { objectMode: true });
  }
  /** @nocollapse */
  // @ts-ignore
  static throughNode(options) {
    throw new Error(`"throughNode" not available in this environment`);
  }
  /** @nocollapse */
  static throughDOM(writableStrategy, readableStrategy) {
    throw new Error(`"throughDOM" not available in this environment`);
  }
  /** @nocollapse */
  static from(source2) {
    if (source2 instanceof RecordBatchReader) {
      return source2;
    } else if (isArrowJSON(source2)) {
      return fromArrowJSON(source2);
    } else if (isFileHandle(source2)) {
      return fromFileHandle(source2);
    } else if (isPromise(source2)) {
      return (() => __awaiter(this, void 0, void 0, function* () {
        return yield RecordBatchReader.from(yield source2);
      }))();
    } else if (isFetchResponse(source2) || isReadableDOMStream(source2) || isReadableNodeStream(source2) || isAsyncIterable(source2)) {
      return fromAsyncByteStream(new AsyncByteStream(source2));
    }
    return fromByteStream(new ByteStream(source2));
  }
  /** @nocollapse */
  static readAll(source2) {
    if (source2 instanceof RecordBatchReader) {
      return source2.isSync() ? readAllSync(source2) : readAllAsync(source2);
    } else if (isArrowJSON(source2) || ArrayBuffer.isView(source2) || isIterable$1(source2) || isIteratorResult(source2)) {
      return readAllSync(source2);
    }
    return readAllAsync(source2);
  }
}
class RecordBatchStreamReader extends RecordBatchReader {
  constructor(_impl) {
    super(_impl);
    this._impl = _impl;
  }
  readAll() {
    return [...this];
  }
  [Symbol.iterator]() {
    return this._impl[Symbol.iterator]();
  }
  [Symbol.asyncIterator]() {
    return __asyncGenerator(this, arguments, function* _a2() {
      yield __await(yield* __asyncDelegator(__asyncValues(this[Symbol.iterator]())));
    });
  }
}
class AsyncRecordBatchStreamReader extends RecordBatchReader {
  constructor(_impl) {
    super(_impl);
    this._impl = _impl;
  }
  readAll() {
    return __awaiter(this, void 0, void 0, function* () {
      var _a2, e_1, _b2, _c2;
      const batches = new Array();
      try {
        for (var _d2 = true, _e2 = __asyncValues(this), _f2; _f2 = yield _e2.next(), _a2 = _f2.done, !_a2; _d2 = true) {
          _c2 = _f2.value;
          _d2 = false;
          const batch = _c2;
          batches.push(batch);
        }
      } catch (e_1_1) {
        e_1 = { error: e_1_1 };
      } finally {
        try {
          if (!_d2 && !_a2 && (_b2 = _e2.return)) yield _b2.call(_e2);
        } finally {
          if (e_1) throw e_1.error;
        }
      }
      return batches;
    });
  }
  [Symbol.iterator]() {
    throw new Error(`AsyncRecordBatchStreamReader is not Iterable`);
  }
  [Symbol.asyncIterator]() {
    return this._impl[Symbol.asyncIterator]();
  }
}
class RecordBatchFileReader extends RecordBatchStreamReader {
  constructor(_impl) {
    super(_impl);
    this._impl = _impl;
  }
}
class AsyncRecordBatchFileReader extends AsyncRecordBatchStreamReader {
  constructor(_impl) {
    super(_impl);
    this._impl = _impl;
  }
}
class RecordBatchReaderImpl {
  get numDictionaries() {
    return this._dictionaryIndex;
  }
  get numRecordBatches() {
    return this._recordBatchIndex;
  }
  constructor(dictionaries = /* @__PURE__ */ new Map()) {
    this.closed = false;
    this.autoDestroy = true;
    this._dictionaryIndex = 0;
    this._recordBatchIndex = 0;
    this.dictionaries = dictionaries;
  }
  isSync() {
    return false;
  }
  isAsync() {
    return false;
  }
  isFile() {
    return false;
  }
  isStream() {
    return false;
  }
  reset(schema) {
    this._dictionaryIndex = 0;
    this._recordBatchIndex = 0;
    this.schema = schema;
    this.dictionaries = /* @__PURE__ */ new Map();
    return this;
  }
  _loadRecordBatch(header, body) {
    let children;
    if (header.compression != null) {
      const codec = compressionRegistry.get(header.compression.type);
      if ((codec === null || codec === void 0 ? void 0 : codec.decode) && typeof codec.decode === "function") {
        const { decommpressedBody, buffers } = this._decompressBuffers(header, body, codec);
        children = this._loadCompressedVectors(header, decommpressedBody, this.schema.fields);
        header = new RecordBatch$1(header.length, header.nodes, buffers, null);
      } else {
        throw new Error("Record batch is compressed but codec not found");
      }
    } else {
      children = this._loadVectors(header, body, this.schema.fields);
    }
    const data2 = makeData({ type: new Struct(this.schema.fields), length: header.length, children });
    return new RecordBatch3(this.schema, data2);
  }
  _loadDictionaryBatch(header, body) {
    const { id, isDelta } = header;
    const { dictionaries, schema } = this;
    const dictionary2 = dictionaries.get(id);
    const type = schema.dictionaries.get(id);
    let data2;
    if (header.data.compression != null) {
      const codec = compressionRegistry.get(header.data.compression.type);
      if ((codec === null || codec === void 0 ? void 0 : codec.decode) && typeof codec.decode === "function") {
        const { decommpressedBody, buffers } = this._decompressBuffers(header.data, body, codec);
        data2 = this._loadCompressedVectors(header.data, decommpressedBody, [type]);
        header = new DictionaryBatch$1(new RecordBatch$1(header.data.length, header.data.nodes, buffers, null), id, isDelta);
      } else {
        throw new Error("Dictionary batch is compressed but codec not found");
      }
    } else {
      data2 = this._loadVectors(header.data, body, [type]);
    }
    return (dictionary2 && isDelta ? dictionary2.concat(new Vector(data2)) : new Vector(data2)).memoize();
  }
  _loadVectors(header, body, types2) {
    return new VectorLoader(body, header.nodes, header.buffers, this.dictionaries, this.schema.metadataVersion).visitMany(types2);
  }
  _loadCompressedVectors(header, body, types2) {
    return new CompressedVectorLoader(body, header.nodes, header.buffers, this.dictionaries, this.schema.metadataVersion).visitMany(types2);
  }
  _decompressBuffers(header, body, codec) {
    const decompressedBuffers = [];
    const newBufferRegions = [];
    let currentOffset = 0;
    for (const { offset: offset2, length: length2 } of header.buffers) {
      if (length2 === 0) {
        decompressedBuffers.push(new Uint8Array(0));
        newBufferRegions.push(new BufferRegion(currentOffset, 0));
        continue;
      }
      const byteBuf = new ByteBuffer$2(body.subarray(offset2, offset2 + length2));
      const uncompressedLenth = bigIntToNumber(byteBuf.readInt64(0));
      const bytes = byteBuf.bytes().subarray(COMPRESS_LENGTH_PREFIX);
      const decompressed = uncompressedLenth === LENGTH_NO_COMPRESSED_DATA ? bytes : codec.decode(bytes);
      decompressedBuffers.push(decompressed);
      const padding = (currentOffset + 7 & -8) - currentOffset;
      currentOffset += padding;
      newBufferRegions.push(new BufferRegion(currentOffset, decompressed.length));
      currentOffset += decompressed.length;
    }
    return {
      decommpressedBody: decompressedBuffers,
      buffers: newBufferRegions
    };
  }
}
class RecordBatchStreamReaderImpl extends RecordBatchReaderImpl {
  constructor(source2, dictionaries) {
    super(dictionaries);
    this._reader = !isArrowJSON(source2) ? new MessageReader(this._handle = source2) : new JSONMessageReader(this._handle = source2);
  }
  isSync() {
    return true;
  }
  isStream() {
    return true;
  }
  [Symbol.iterator]() {
    return this;
  }
  cancel() {
    if (!this.closed && (this.closed = true)) {
      this.reset()._reader.return();
      this._reader = null;
      this.dictionaries = null;
    }
  }
  open(options) {
    if (!this.closed) {
      this.autoDestroy = shouldAutoDestroy(this, options);
      if (!(this.schema || (this.schema = this._reader.readSchema()))) {
        this.cancel();
      }
    }
    return this;
  }
  throw(value2) {
    if (!this.closed && this.autoDestroy && (this.closed = true)) {
      return this.reset()._reader.throw(value2);
    }
    return ITERATOR_DONE;
  }
  return(value2) {
    if (!this.closed && this.autoDestroy && (this.closed = true)) {
      return this.reset()._reader.return(value2);
    }
    return ITERATOR_DONE;
  }
  next() {
    if (this.closed) {
      return ITERATOR_DONE;
    }
    let message;
    const { _reader: reader } = this;
    while (message = this._readNextMessageAndValidate()) {
      if (message.isSchema()) {
        this.reset(message.header());
      } else if (message.isRecordBatch()) {
        this._recordBatchIndex++;
        const header = message.header();
        const buffer2 = reader.readMessageBody(message.bodyLength);
        const recordBatch = this._loadRecordBatch(header, buffer2);
        return { done: false, value: recordBatch };
      } else if (message.isDictionaryBatch()) {
        this._dictionaryIndex++;
        const header = message.header();
        const buffer2 = reader.readMessageBody(message.bodyLength);
        const vector = this._loadDictionaryBatch(header, buffer2);
        this.dictionaries.set(header.id, vector);
      }
    }
    if (this.schema && this._recordBatchIndex === 0) {
      this._recordBatchIndex++;
      return { done: false, value: new _InternalEmptyPlaceholderRecordBatch(this.schema) };
    }
    return this.return();
  }
  _readNextMessageAndValidate(type) {
    return this._reader.readMessage(type);
  }
}
class AsyncRecordBatchStreamReaderImpl extends RecordBatchReaderImpl {
  constructor(source2, dictionaries) {
    super(dictionaries);
    this._reader = new AsyncMessageReader(this._handle = source2);
  }
  isAsync() {
    return true;
  }
  isStream() {
    return true;
  }
  [Symbol.asyncIterator]() {
    return this;
  }
  cancel() {
    return __awaiter(this, void 0, void 0, function* () {
      if (!this.closed && (this.closed = true)) {
        yield this.reset()._reader.return();
        this._reader = null;
        this.dictionaries = null;
      }
    });
  }
  open(options) {
    return __awaiter(this, void 0, void 0, function* () {
      if (!this.closed) {
        this.autoDestroy = shouldAutoDestroy(this, options);
        if (!(this.schema || (this.schema = yield this._reader.readSchema()))) {
          yield this.cancel();
        }
      }
      return this;
    });
  }
  throw(value2) {
    return __awaiter(this, void 0, void 0, function* () {
      if (!this.closed && this.autoDestroy && (this.closed = true)) {
        return yield this.reset()._reader.throw(value2);
      }
      return ITERATOR_DONE;
    });
  }
  return(value2) {
    return __awaiter(this, void 0, void 0, function* () {
      if (!this.closed && this.autoDestroy && (this.closed = true)) {
        return yield this.reset()._reader.return(value2);
      }
      return ITERATOR_DONE;
    });
  }
  next() {
    return __awaiter(this, void 0, void 0, function* () {
      if (this.closed) {
        return ITERATOR_DONE;
      }
      let message;
      const { _reader: reader } = this;
      while (message = yield this._readNextMessageAndValidate()) {
        if (message.isSchema()) {
          yield this.reset(message.header());
        } else if (message.isRecordBatch()) {
          this._recordBatchIndex++;
          const header = message.header();
          const buffer2 = yield reader.readMessageBody(message.bodyLength);
          const recordBatch = this._loadRecordBatch(header, buffer2);
          return { done: false, value: recordBatch };
        } else if (message.isDictionaryBatch()) {
          this._dictionaryIndex++;
          const header = message.header();
          const buffer2 = yield reader.readMessageBody(message.bodyLength);
          const vector = this._loadDictionaryBatch(header, buffer2);
          this.dictionaries.set(header.id, vector);
        }
      }
      if (this.schema && this._recordBatchIndex === 0) {
        this._recordBatchIndex++;
        return { done: false, value: new _InternalEmptyPlaceholderRecordBatch(this.schema) };
      }
      return yield this.return();
    });
  }
  _readNextMessageAndValidate(type) {
    return __awaiter(this, void 0, void 0, function* () {
      return yield this._reader.readMessage(type);
    });
  }
}
class RecordBatchFileReaderImpl extends RecordBatchStreamReaderImpl {
  get footer() {
    return this._footer;
  }
  get numDictionaries() {
    return this._footer ? this._footer.numDictionaries : 0;
  }
  get numRecordBatches() {
    return this._footer ? this._footer.numRecordBatches : 0;
  }
  constructor(source2, dictionaries) {
    super(source2 instanceof RandomAccessFile ? source2 : new RandomAccessFile(source2), dictionaries);
  }
  isSync() {
    return true;
  }
  isFile() {
    return true;
  }
  open(options) {
    if (!this.closed && !this._footer) {
      this.schema = (this._footer = this._readFooter()).schema;
      for (const block of this._footer.dictionaryBatches()) {
        block && this._readDictionaryBatch(this._dictionaryIndex++);
      }
    }
    return super.open(options);
  }
  readRecordBatch(index) {
    var _a2;
    if (this.closed) {
      return null;
    }
    if (!this._footer) {
      this.open();
    }
    const block = (_a2 = this._footer) === null || _a2 === void 0 ? void 0 : _a2.getRecordBatch(index);
    if (block && this._handle.seek(block.offset)) {
      const message = this._reader.readMessage(MessageHeader$1.RecordBatch);
      if (message === null || message === void 0 ? void 0 : message.isRecordBatch()) {
        const header = message.header();
        const buffer2 = this._reader.readMessageBody(message.bodyLength);
        const recordBatch = this._loadRecordBatch(header, buffer2);
        return recordBatch;
      }
    }
    return null;
  }
  _readDictionaryBatch(index) {
    var _a2;
    const block = (_a2 = this._footer) === null || _a2 === void 0 ? void 0 : _a2.getDictionaryBatch(index);
    if (block && this._handle.seek(block.offset)) {
      const message = this._reader.readMessage(MessageHeader$1.DictionaryBatch);
      if (message === null || message === void 0 ? void 0 : message.isDictionaryBatch()) {
        const header = message.header();
        const buffer2 = this._reader.readMessageBody(message.bodyLength);
        const vector = this._loadDictionaryBatch(header, buffer2);
        this.dictionaries.set(header.id, vector);
      }
    }
  }
  _readFooter() {
    const { _handle } = this;
    const offset2 = _handle.size - magicAndPadding;
    const length2 = _handle.readInt32(offset2);
    const buffer2 = _handle.readAt(offset2 - length2, length2);
    return Footer_.decode(buffer2);
  }
  _readNextMessageAndValidate(type) {
    var _a2;
    if (!this._footer) {
      this.open();
    }
    if (this._footer && this._recordBatchIndex < this.numRecordBatches) {
      const block = (_a2 = this._footer) === null || _a2 === void 0 ? void 0 : _a2.getRecordBatch(this._recordBatchIndex);
      if (block && this._handle.seek(block.offset)) {
        return this._reader.readMessage(type);
      }
    }
    return null;
  }
}
class AsyncRecordBatchFileReaderImpl extends AsyncRecordBatchStreamReaderImpl {
  get footer() {
    return this._footer;
  }
  get numDictionaries() {
    return this._footer ? this._footer.numDictionaries : 0;
  }
  get numRecordBatches() {
    return this._footer ? this._footer.numRecordBatches : 0;
  }
  constructor(source2, ...rest) {
    const byteLength = typeof rest[0] !== "number" ? rest.shift() : void 0;
    const dictionaries = rest[0] instanceof Map ? rest.shift() : void 0;
    super(source2 instanceof AsyncRandomAccessFile ? source2 : new AsyncRandomAccessFile(source2, byteLength), dictionaries);
  }
  isFile() {
    return true;
  }
  isAsync() {
    return true;
  }
  open(options) {
    const _super = Object.create(null, {
      open: { get: () => super.open }
    });
    return __awaiter(this, void 0, void 0, function* () {
      if (!this.closed && !this._footer) {
        this.schema = (this._footer = yield this._readFooter()).schema;
        for (const block of this._footer.dictionaryBatches()) {
          block && (yield this._readDictionaryBatch(this._dictionaryIndex++));
        }
      }
      return yield _super.open.call(this, options);
    });
  }
  readRecordBatch(index) {
    return __awaiter(this, void 0, void 0, function* () {
      var _a2;
      if (this.closed) {
        return null;
      }
      if (!this._footer) {
        yield this.open();
      }
      const block = (_a2 = this._footer) === null || _a2 === void 0 ? void 0 : _a2.getRecordBatch(index);
      if (block && (yield this._handle.seek(block.offset))) {
        const message = yield this._reader.readMessage(MessageHeader$1.RecordBatch);
        if (message === null || message === void 0 ? void 0 : message.isRecordBatch()) {
          const header = message.header();
          const buffer2 = yield this._reader.readMessageBody(message.bodyLength);
          const recordBatch = this._loadRecordBatch(header, buffer2);
          return recordBatch;
        }
      }
      return null;
    });
  }
  _readDictionaryBatch(index) {
    return __awaiter(this, void 0, void 0, function* () {
      var _a2;
      const block = (_a2 = this._footer) === null || _a2 === void 0 ? void 0 : _a2.getDictionaryBatch(index);
      if (block && (yield this._handle.seek(block.offset))) {
        const message = yield this._reader.readMessage(MessageHeader$1.DictionaryBatch);
        if (message === null || message === void 0 ? void 0 : message.isDictionaryBatch()) {
          const header = message.header();
          const buffer2 = yield this._reader.readMessageBody(message.bodyLength);
          const vector = this._loadDictionaryBatch(header, buffer2);
          this.dictionaries.set(header.id, vector);
        }
      }
    });
  }
  _readFooter() {
    return __awaiter(this, void 0, void 0, function* () {
      const { _handle } = this;
      _handle._pending && (yield _handle._pending);
      const offset2 = _handle.size - magicAndPadding;
      const length2 = yield _handle.readInt32(offset2);
      const buffer2 = yield _handle.readAt(offset2 - length2, length2);
      return Footer_.decode(buffer2);
    });
  }
  _readNextMessageAndValidate(type) {
    return __awaiter(this, void 0, void 0, function* () {
      if (!this._footer) {
        yield this.open();
      }
      if (this._footer && this._recordBatchIndex < this.numRecordBatches) {
        const block = this._footer.getRecordBatch(this._recordBatchIndex);
        if (block && (yield this._handle.seek(block.offset))) {
          return yield this._reader.readMessage(type);
        }
      }
      return null;
    });
  }
}
class RecordBatchJSONReaderImpl extends RecordBatchStreamReaderImpl {
  constructor(source2, dictionaries) {
    super(source2, dictionaries);
  }
  _loadVectors(header, body, types2) {
    return new JSONVectorLoader(body, header.nodes, header.buffers, this.dictionaries, this.schema.metadataVersion).visitMany(types2);
  }
}
function shouldAutoDestroy(self, options) {
  return options && typeof options["autoDestroy"] === "boolean" ? options["autoDestroy"] : self["autoDestroy"];
}
function* readAllSync(source2) {
  const reader = RecordBatchReader.from(source2);
  try {
    if (!reader.open({ autoDestroy: false }).closed) {
      do {
        yield reader;
      } while (!reader.reset().open().closed);
    }
  } finally {
    reader.cancel();
  }
}
function readAllAsync(source2) {
  return __asyncGenerator(this, arguments, function* readAllAsync_1() {
    const reader = yield __await(RecordBatchReader.from(source2));
    try {
      if (!(yield __await(reader.open({ autoDestroy: false }))).closed) {
        do {
          yield yield __await(reader);
        } while (!(yield __await(reader.reset().open())).closed);
      }
    } finally {
      yield __await(reader.cancel());
    }
  });
}
function fromArrowJSON(source2) {
  return new RecordBatchStreamReader(new RecordBatchJSONReaderImpl(source2));
}
function fromByteStream(source2) {
  const bytes = source2.peek(magicLength + 7 & -8);
  return bytes && bytes.byteLength >= 4 ? !checkForMagicArrowString(bytes) ? new RecordBatchStreamReader(new RecordBatchStreamReaderImpl(source2)) : new RecordBatchFileReader(new RecordBatchFileReaderImpl(source2.read())) : new RecordBatchStreamReader(new RecordBatchStreamReaderImpl((function* () {
  })()));
}
function fromAsyncByteStream(source2) {
  return __awaiter(this, void 0, void 0, function* () {
    const bytes = yield source2.peek(magicLength + 7 & -8);
    return bytes && bytes.byteLength >= 4 ? !checkForMagicArrowString(bytes) ? new AsyncRecordBatchStreamReader(new AsyncRecordBatchStreamReaderImpl(source2)) : new RecordBatchFileReader(new RecordBatchFileReaderImpl(yield source2.read())) : new AsyncRecordBatchStreamReader(new AsyncRecordBatchStreamReaderImpl((function() {
      return __asyncGenerator(this, arguments, function* () {
      });
    })()));
  });
}
function fromFileHandle(source2) {
  return __awaiter(this, void 0, void 0, function* () {
    const { size } = yield source2.stat();
    const file = new AsyncRandomAccessFile(source2, size);
    if (size >= magicX2AndPadding && checkForMagicArrowString(yield file.readAt(0, magicLength + 7 & -8))) {
      return new AsyncRecordBatchFileReader(new AsyncRecordBatchFileReaderImpl(file));
    }
    return new AsyncRecordBatchStreamReader(new AsyncRecordBatchStreamReaderImpl(file));
  });
}
class VectorAssembler extends Visitor {
  /** @nocollapse */
  static assemble(...args) {
    const unwrap = (nodes) => nodes.flatMap((node) => Array.isArray(node) ? unwrap(node) : node instanceof RecordBatch3 ? node.data.children : node.data);
    const assembler = new VectorAssembler();
    assembler.visitMany(unwrap(args));
    return assembler;
  }
  constructor() {
    super();
    this._byteLength = 0;
    this._nodes = [];
    this._buffers = [];
    this._bufferRegions = [];
  }
  visit(data2) {
    if (data2 instanceof Vector) {
      this.visitMany(data2.data);
      return this;
    }
    const { type } = data2;
    if (!DataType.isDictionary(type)) {
      const { length: length2 } = data2;
      if (length2 > 2147483647) {
        throw new RangeError("Cannot write arrays larger than 2^31 - 1 in length");
      }
      if (DataType.isUnion(type)) {
        this.nodes.push(new FieldNode2(length2, 0));
      } else {
        const { nullCount } = data2;
        if (!DataType.isNull(type)) {
          addBuffer.call(this, nullCount <= 0 ? new Uint8Array(0) : truncateBitmap(data2.offset, length2, data2.nullBitmap));
        }
        this.nodes.push(new FieldNode2(length2, nullCount));
      }
    }
    return super.visit(data2);
  }
  visitNull(_null) {
    return this;
  }
  visitDictionary(data2) {
    return this.visit(data2.clone(data2.type.indices));
  }
  get nodes() {
    return this._nodes;
  }
  get buffers() {
    return this._buffers;
  }
  get byteLength() {
    return this._byteLength;
  }
  get bufferRegions() {
    return this._bufferRegions;
  }
}
function addBuffer(values2) {
  const byteLength = values2.byteLength + 7 & -8;
  this.buffers.push(values2);
  this.bufferRegions.push(new BufferRegion(this._byteLength, byteLength));
  this._byteLength += byteLength;
  return this;
}
function assembleUnion(data2) {
  var _a2;
  const { type, length: length2, typeIds, valueOffsets } = data2;
  addBuffer.call(this, typeIds);
  if (type.mode === UnionMode$1.Sparse) {
    return assembleNestedVector.call(this, data2);
  } else if (type.mode === UnionMode$1.Dense) {
    if (data2.offset <= 0) {
      addBuffer.call(this, valueOffsets);
      return assembleNestedVector.call(this, data2);
    } else {
      const shiftedOffsets = new Int32Array(length2);
      const childOffsets = /* @__PURE__ */ Object.create(null);
      const childLengths = /* @__PURE__ */ Object.create(null);
      for (let typeId, shift, index = -1; ++index < length2; ) {
        if ((typeId = typeIds[index]) === void 0) {
          continue;
        }
        if ((shift = childOffsets[typeId]) === void 0) {
          shift = childOffsets[typeId] = valueOffsets[index];
        }
        shiftedOffsets[index] = valueOffsets[index] - shift;
        childLengths[typeId] = ((_a2 = childLengths[typeId]) !== null && _a2 !== void 0 ? _a2 : 0) + 1;
      }
      addBuffer.call(this, shiftedOffsets);
      this.visitMany(data2.children.map((child, childIndex) => {
        const typeId = type.typeIds[childIndex];
        const childOffset = childOffsets[typeId];
        const childLength = childLengths[typeId];
        return child.slice(childOffset, Math.min(length2, childLength));
      }));
    }
  }
  return this;
}
function assembleBoolVector(data2) {
  let values2;
  if (data2.nullCount >= data2.length) {
    return addBuffer.call(this, new Uint8Array(0));
  } else if ((values2 = data2.values) instanceof Uint8Array) {
    return addBuffer.call(this, truncateBitmap(data2.offset, data2.length, values2));
  }
  return addBuffer.call(this, packBools(data2.values));
}
function assembleFlatVector(data2) {
  return addBuffer.call(this, data2.values.subarray(0, data2.length * data2.stride));
}
function assembleFlatListVector(data2) {
  const { length: length2, values: values2, valueOffsets } = data2;
  const begin = bigIntToNumber(valueOffsets[0]);
  const end = bigIntToNumber(valueOffsets[length2]);
  const byteLength = Math.min(end - begin, values2.byteLength - begin);
  addBuffer.call(this, rebaseValueOffsets(-begin, length2 + 1, valueOffsets));
  addBuffer.call(this, values2.subarray(begin, begin + byteLength));
  return this;
}
function assembleListVector(data2) {
  const { length: length2, valueOffsets } = data2;
  if (valueOffsets) {
    const { [0]: begin, [length2]: end } = valueOffsets;
    addBuffer.call(this, rebaseValueOffsets(-begin, length2 + 1, valueOffsets));
    return this.visit(data2.children[0].slice(begin, end - begin));
  }
  return this.visit(data2.children[0]);
}
function assembleNestedVector(data2) {
  return this.visitMany(data2.type.children.map((_, i) => data2.children[i]).filter(Boolean))[0];
}
VectorAssembler.prototype.visitBool = assembleBoolVector;
VectorAssembler.prototype.visitInt = assembleFlatVector;
VectorAssembler.prototype.visitFloat = assembleFlatVector;
VectorAssembler.prototype.visitUtf8 = assembleFlatListVector;
VectorAssembler.prototype.visitLargeUtf8 = assembleFlatListVector;
VectorAssembler.prototype.visitBinary = assembleFlatListVector;
VectorAssembler.prototype.visitLargeBinary = assembleFlatListVector;
VectorAssembler.prototype.visitFixedSizeBinary = assembleFlatVector;
VectorAssembler.prototype.visitDate = assembleFlatVector;
VectorAssembler.prototype.visitTimestamp = assembleFlatVector;
VectorAssembler.prototype.visitTime = assembleFlatVector;
VectorAssembler.prototype.visitDecimal = assembleFlatVector;
VectorAssembler.prototype.visitList = assembleListVector;
VectorAssembler.prototype.visitStruct = assembleNestedVector;
VectorAssembler.prototype.visitUnion = assembleUnion;
VectorAssembler.prototype.visitInterval = assembleFlatVector;
VectorAssembler.prototype.visitDuration = assembleFlatVector;
VectorAssembler.prototype.visitFixedSizeList = assembleListVector;
VectorAssembler.prototype.visitMap = assembleListVector;
class RecordBatchWriter extends ReadableInterop {
  /** @nocollapse */
  // @ts-ignore
  static throughNode(options) {
    throw new Error(`"throughNode" not available in this environment`);
  }
  /** @nocollapse */
  static throughDOM(writableStrategy, readableStrategy) {
    throw new Error(`"throughDOM" not available in this environment`);
  }
  constructor(options) {
    super();
    this._position = 0;
    this._started = false;
    this._compression = null;
    this._sink = new AsyncByteQueue();
    this._schema = null;
    this._dictionaryBlocks = [];
    this._recordBatchBlocks = [];
    this._seenDictionaries = /* @__PURE__ */ new Map();
    this._dictionaryDeltaOffsets = /* @__PURE__ */ new Map();
    isObject$1(options) || (options = { autoDestroy: true, writeLegacyIpcFormat: false, compressionType: null });
    this._autoDestroy = typeof options.autoDestroy === "boolean" ? options.autoDestroy : true;
    this._writeLegacyIpcFormat = typeof options.writeLegacyIpcFormat === "boolean" ? options.writeLegacyIpcFormat : false;
    if (options.compressionType != null) {
      if (this._writeLegacyIpcFormat) {
        throw new Error("Legacy IPC format does not support columnar compression. Use modern IPC format (writeLegacyIpcFormat=false).");
      }
      if (Object.values(CompressionType).includes(options.compressionType)) {
        this._compression = new BodyCompression2(options.compressionType);
      } else {
        const validCompressionTypes = Object.values(CompressionType).filter((v) => typeof v === "string");
        throw new Error(`Unsupported compressionType: ${options.compressionType} Available types: ${validCompressionTypes.join(", ")}`);
      }
    } else {
      this._compression = null;
    }
  }
  toString(sync = false) {
    return this._sink.toString(sync);
  }
  toUint8Array(sync = false) {
    return this._sink.toUint8Array(sync);
  }
  writeAll(input) {
    if (isPromise(input)) {
      return input.then((x) => this.writeAll(x));
    } else if (isAsyncIterable(input)) {
      return writeAllAsync(this, input);
    }
    return writeAll(this, input);
  }
  get closed() {
    return this._sink.closed;
  }
  [Symbol.asyncIterator]() {
    return this._sink[Symbol.asyncIterator]();
  }
  toDOMStream(options) {
    return this._sink.toDOMStream(options);
  }
  toNodeStream(options) {
    return this._sink.toNodeStream(options);
  }
  close() {
    return this.reset()._sink.close();
  }
  abort(reason) {
    return this.reset()._sink.abort(reason);
  }
  finish() {
    this._autoDestroy ? this.close() : this.reset(this._sink, this._schema);
    return this;
  }
  reset(sink = this._sink, schema = null) {
    if (sink === this._sink || sink instanceof AsyncByteQueue) {
      this._sink = sink;
    } else {
      this._sink = new AsyncByteQueue();
      if (sink && isWritableDOMStream(sink)) {
        this.toDOMStream({ type: "bytes" }).pipeTo(sink);
      } else if (sink && isWritableNodeStream(sink)) {
        this.toNodeStream({ objectMode: false }).pipe(sink);
      }
    }
    if (this._started && this._schema) {
      this._writeFooter(this._schema);
    }
    this._started = false;
    this._dictionaryBlocks = [];
    this._recordBatchBlocks = [];
    this._seenDictionaries = /* @__PURE__ */ new Map();
    this._dictionaryDeltaOffsets = /* @__PURE__ */ new Map();
    if (!schema || !compareSchemas(schema, this._schema)) {
      if (schema == null) {
        this._position = 0;
        this._schema = null;
      } else {
        this._started = true;
        this._schema = schema;
        this._writeSchema(schema);
      }
    }
    return this;
  }
  write(payload) {
    let schema = null;
    if (!this._sink) {
      throw new Error(`RecordBatchWriter is closed`);
    } else if (payload == null) {
      return this.finish() && void 0;
    } else if (payload instanceof Table$2 && !(schema = payload.schema)) {
      return this.finish() && void 0;
    } else if (payload instanceof RecordBatch3 && !(schema = payload.schema)) {
      return this.finish() && void 0;
    }
    if (schema && !compareSchemas(schema, this._schema)) {
      if (this._started && this._autoDestroy) {
        return this.close();
      }
      this.reset(this._sink, schema);
    }
    if (payload instanceof RecordBatch3) {
      if (!(payload instanceof _InternalEmptyPlaceholderRecordBatch)) {
        this._writeRecordBatch(payload);
      }
    } else if (payload instanceof Table$2) {
      this.writeAll(payload.batches);
    } else if (isIterable$1(payload)) {
      this.writeAll(payload);
    }
  }
  _writeMessage(message, alignment = 8) {
    const a = alignment - 1;
    const buffer2 = Message2.encode(message);
    const flatbufferSize = buffer2.byteLength;
    const prefixSize = !this._writeLegacyIpcFormat ? 8 : 4;
    const alignedSize = flatbufferSize + prefixSize + a & ~a;
    const nPaddingBytes = alignedSize - flatbufferSize - prefixSize;
    if (message.headerType === MessageHeader$1.RecordBatch) {
      this._recordBatchBlocks.push(new FileBlock(alignedSize, message.bodyLength, this._position));
    } else if (message.headerType === MessageHeader$1.DictionaryBatch) {
      this._dictionaryBlocks.push(new FileBlock(alignedSize, message.bodyLength, this._position));
    }
    if (!this._writeLegacyIpcFormat) {
      this._write(Int32Array.of(-1));
    }
    this._write(Int32Array.of(alignedSize - prefixSize));
    if (flatbufferSize > 0) {
      this._write(buffer2);
    }
    return this._writePadding(nPaddingBytes);
  }
  _write(chunk) {
    if (this._started) {
      const buffer2 = toUint8Array(chunk);
      if (buffer2 && buffer2.byteLength > 0) {
        this._sink.write(buffer2);
        this._position += buffer2.byteLength;
      }
    }
    return this;
  }
  _writeSchema(schema) {
    return this._writeMessage(Message2.from(schema));
  }
  // @ts-ignore
  _writeFooter(schema) {
    return this._writeLegacyIpcFormat ? this._write(Int32Array.of(0)) : this._write(Int32Array.of(-1, 0));
  }
  _writeMagic() {
    return this._write(MAGIC$1);
  }
  _writePadding(nBytes) {
    return nBytes > 0 ? this._write(new Uint8Array(nBytes)) : this;
  }
  _writeRecordBatch(batch) {
    const { byteLength, nodes, bufferRegions, buffers } = this._assembleRecordBatch(batch);
    const recordBatch = new RecordBatch$1(batch.numRows, nodes, bufferRegions, this._compression);
    const message = Message2.from(recordBatch, byteLength);
    return this._writeDictionaries(batch)._writeMessage(message)._writeBodyBuffers(buffers);
  }
  _assembleRecordBatch(batch) {
    let { byteLength, nodes, bufferRegions, buffers } = VectorAssembler.assemble(batch);
    if (this._compression != null) {
      ({ byteLength, bufferRegions, buffers } = this._compressBodyBuffers(buffers));
    }
    return { byteLength, nodes, bufferRegions, buffers };
  }
  _compressBodyBuffers(buffers) {
    const codec = compressionRegistry.get(this._compression.type);
    if (!(codec === null || codec === void 0 ? void 0 : codec.encode) || typeof codec.encode !== "function") {
      throw new Error(`Codec for compression type "${CompressionType[this._compression.type]}" has invalid encode method`);
    }
    let currentOffset = 0;
    const compressedBuffers = [];
    const bufferRegions = [];
    for (const buffer2 of buffers) {
      const byteBuf = toUint8Array(buffer2);
      if (byteBuf.length === 0) {
        compressedBuffers.push(new Uint8Array(0), new Uint8Array(0));
        bufferRegions.push(new BufferRegion(currentOffset, 0));
        continue;
      }
      const compressed = codec.encode(byteBuf);
      const isCompressionEffective = compressed.length < byteBuf.length;
      const finalBuffer = isCompressionEffective ? compressed : byteBuf;
      const byteLength = isCompressionEffective ? finalBuffer.length : LENGTH_NO_COMPRESSED_DATA;
      const lengthPrefix = new ByteBuffer$2(new Uint8Array(COMPRESS_LENGTH_PREFIX));
      lengthPrefix.writeInt64(0, BigInt(byteLength));
      compressedBuffers.push(lengthPrefix.bytes(), new Uint8Array(finalBuffer));
      const padding = (currentOffset + 7 & -8) - currentOffset;
      currentOffset += padding;
      const fullBodyLength = COMPRESS_LENGTH_PREFIX + finalBuffer.length;
      bufferRegions.push(new BufferRegion(currentOffset, fullBodyLength));
      currentOffset += fullBodyLength;
    }
    const finalPadding = (currentOffset + 7 & -8) - currentOffset;
    currentOffset += finalPadding;
    return { byteLength: currentOffset, bufferRegions, buffers: compressedBuffers };
  }
  _writeDictionaryBatch(dictionary2, id, isDelta = false) {
    const { byteLength, nodes, bufferRegions, buffers } = this._assembleRecordBatch(new Vector([dictionary2]));
    const recordBatch = new RecordBatch$1(dictionary2.length, nodes, bufferRegions, this._compression);
    const dictionaryBatch = new DictionaryBatch$1(recordBatch, id, isDelta);
    const message = Message2.from(dictionaryBatch, byteLength);
    return this._writeMessage(message)._writeBodyBuffers(buffers);
  }
  _writeBodyBuffers(buffers) {
    const bufGroupSize = this._compression != null ? 2 : 1;
    const bufs = new Array(bufGroupSize);
    for (let i = 0; i < buffers.length; i += bufGroupSize) {
      let size = 0;
      for (let j = -1; ++j < bufGroupSize; ) {
        bufs[j] = buffers[i + j];
        size += bufs[j].byteLength;
      }
      if (size === 0) {
        continue;
      }
      for (const buf2 of bufs)
        this._write(buf2);
      const padding = (size + 7 & -8) - size;
      if (padding > 0) {
        this._writePadding(padding);
      }
    }
    return this;
  }
  _writeDictionaries(batch) {
    var _a2, _b2;
    for (const [id, dictionary2] of batch.dictionaries) {
      const chunks = (_a2 = dictionary2 === null || dictionary2 === void 0 ? void 0 : dictionary2.data) !== null && _a2 !== void 0 ? _a2 : [];
      const prevDictionary = this._seenDictionaries.get(id);
      const offset2 = (_b2 = this._dictionaryDeltaOffsets.get(id)) !== null && _b2 !== void 0 ? _b2 : 0;
      if (!prevDictionary || prevDictionary.data[0] !== chunks[0]) {
        for (const [index, chunk] of chunks.entries())
          this._writeDictionaryBatch(chunk, id, index > 0);
      } else if (offset2 < chunks.length) {
        for (const chunk of chunks.slice(offset2))
          this._writeDictionaryBatch(chunk, id, true);
      }
      this._seenDictionaries.set(id, dictionary2);
      this._dictionaryDeltaOffsets.set(id, chunks.length);
    }
    return this;
  }
}
class RecordBatchStreamWriter extends RecordBatchWriter {
  /** @nocollapse */
  static writeAll(input, options) {
    const writer = new RecordBatchStreamWriter(options);
    if (isPromise(input)) {
      return input.then((x) => writer.writeAll(x));
    } else if (isAsyncIterable(input)) {
      return writeAllAsync(writer, input);
    }
    return writeAll(writer, input);
  }
}
class RecordBatchFileWriter extends RecordBatchWriter {
  /** @nocollapse */
  static writeAll(input, options) {
    const writer = new RecordBatchFileWriter(options);
    if (isPromise(input)) {
      return input.then((x) => writer.writeAll(x));
    } else if (isAsyncIterable(input)) {
      return writeAllAsync(writer, input);
    }
    return writeAll(writer, input);
  }
  constructor(options) {
    super(options);
    this._autoDestroy = true;
    this._writeLegacyIpcFormat = false;
  }
  // @ts-ignore
  _writeSchema(schema) {
    return this._writeMagic()._writePadding(2);
  }
  _writeDictionaryBatch(dictionary2, id, isDelta = false) {
    if (!isDelta && this._seenDictionaries.has(id)) {
      throw new Error("The Arrow File format does not support replacement dictionaries. ");
    }
    return super._writeDictionaryBatch(dictionary2, id, isDelta);
  }
  _writeFooter(schema) {
    const buffer2 = Footer_.encode(new Footer_(schema, MetadataVersion.V5, this._recordBatchBlocks, this._dictionaryBlocks));
    return super._writeFooter(schema)._write(buffer2)._write(Int32Array.of(buffer2.byteLength))._writeMagic();
  }
}
function writeAll(writer, input) {
  let chunks = input;
  if (input instanceof Table$2) {
    chunks = input.batches;
    writer.reset(void 0, input.schema);
  }
  for (const batch of chunks) {
    writer.write(batch);
  }
  return writer.finish();
}
function writeAllAsync(writer, batches) {
  return __awaiter(this, void 0, void 0, function* () {
    var _a2, batches_1, batches_1_1;
    var _b2, e_1, _c2, _d2;
    try {
      for (_a2 = true, batches_1 = __asyncValues(batches); batches_1_1 = yield batches_1.next(), _b2 = batches_1_1.done, !_b2; _a2 = true) {
        _d2 = batches_1_1.value;
        _a2 = false;
        const batch = _d2;
        writer.write(batch);
      }
    } catch (e_1_1) {
      e_1 = { error: e_1_1 };
    } finally {
      try {
        if (!_a2 && !_b2 && (_c2 = batches_1.return)) yield _c2.call(batches_1);
      } finally {
        if (e_1) throw e_1.error;
      }
    }
    return writer.finish();
  });
}
function tableFromIPC$1(input) {
  const reader = RecordBatchReader.from(input);
  if (isPromise(reader)) {
    return reader.then((reader2) => tableFromIPC$1(reader2));
  }
  if (reader.isAsync()) {
    return reader.readAll().then((xs) => new Table$2(xs));
  }
  return new Table$2(reader.readAll());
}
function tableToIPC$1(table2, type = "stream", compressionType = null) {
  const writerOptions = { compressionType };
  return (type === "stream" ? RecordBatchStreamWriter : RecordBatchFileWriter).writeAll(table2, writerOptions).toUint8Array(true);
}
const ONE = 2147483648;
const ALL = 4294967295;
class BitSet {
  /**
   * Instantiate a new BitSet instance.
   * @param {number} size The number of bits.
   */
  constructor(size) {
    this._size = size;
    this._bits = new Uint32Array(Math.ceil(size / 32));
  }
  /**
   * The number of bits.
   * @return {number}
   */
  get length() {
    return this._size;
  }
  /**
   * The number of bits set to one.
   * https://graphics.stanford.edu/~seander/bithacks.html#CountBitsSetKernighan
   * @return {number}
   */
  count() {
    const n = this._bits.length;
    let count2 = 0;
    for (let i = 0; i < n; ++i) {
      for (let b = this._bits[i]; b; ++count2) {
        b &= b - 1;
      }
    }
    return count2;
  }
  /**
   * Get the bit at a given index.
   * @param {number} i The bit index.
   */
  get(i) {
    return this._bits[i >> 5] & ONE >>> i;
  }
  /**
   * Set the bit at a given index to one.
   * @param {number} i The bit index.
   */
  set(i) {
    this._bits[i >> 5] |= ONE >>> i;
  }
  /**
   * Clear the bit at a given index to zero.
   * @param {number} i The bit index.
   */
  clear(i) {
    this._bits[i >> 5] &= ~(ONE >>> i);
  }
  /**
   * Scan the bits, invoking a callback function with the index of
   * each non-zero bit.
   * @param {(i: number) => void} fn A callback function.
   */
  scan(fn) {
    for (let i = this.next(0); i >= 0; i = this.next(i + 1)) {
      fn(i);
    }
  }
  /**
   * Get the next non-zero bit starting from a given index.
   * @param {number} i The bit index.
   */
  next(i) {
    const bits = this._bits;
    const n = bits.length;
    let index = i >> 5;
    let curr = bits[index] & ALL >>> i;
    for (; index < n; curr = bits[++index]) {
      if (curr !== 0) {
        return (index << 5) + Math.clz32(curr);
      }
    }
    return -1;
  }
  /**
   * Return the index of the nth non-zero bit.
   * @param {number} n The number of non-zero bits to advance.
   * @return {number} The index of the nth non-zero bit.
   */
  nth(n) {
    let i = this.next(0);
    while (n-- && i >= 0) i = this.next(i + 1);
    return i;
  }
  /**
   * Negate all bits in this bitset.
   * Modifies this BitSet in place.
   * @return {this}
   */
  not() {
    const bits = this._bits;
    const n = bits.length;
    for (let i = 0; i < n; ++i) {
      bits[i] = ~bits[i];
    }
    const tail = this._size % 32;
    if (tail) {
      bits[n - 1] &= ONE >> tail - 1;
    }
    return this;
  }
  /**
   * Compute the logical AND of this BitSet and another.
   * @param {BitSet} bitset The BitSet to combine with.
   * @return {BitSet} This BitSet updated with the logical AND.
   */
  and(bitset) {
    if (bitset) {
      const a = this._bits;
      const b = bitset._bits;
      const n = a.length;
      for (let i = 0; i < n; ++i) {
        a[i] &= b[i];
      }
    }
    return this;
  }
  /**
   * Compute the logical OR of this BitSet and another.
   * @param {BitSet} bitset The BitSet to combine with.
   * @return {BitSet} This BitSet updated with the logical OR.
   */
  or(bitset) {
    if (bitset) {
      const a = this._bits;
      const b = bitset._bits;
      const n = a.length;
      for (let i = 0; i < n; ++i) {
        a[i] |= b[i];
      }
    }
    return this;
  }
}
function bin(value2, min2, max2, step, offset2) {
  return value2 == null ? null : value2 < min2 ? -Infinity : value2 > max2 ? Infinity : (value2 = Math.max(min2, Math.min(value2, max2)), min2 + step * Math.floor(1e-14 + (value2 - min2) / step + (offset2 || 0)));
}
function isDate$1(value2) {
  return value2 instanceof Date;
}
function isRegExp(value2) {
  return value2 instanceof RegExp;
}
function isObject(value2) {
  return value2 === Object(value2);
}
function equal(a, b) {
  return a == null || b == null || a !== a || b !== b ? false : a === b ? true : isDate$1(a) || isDate$1(b) ? +a === +b : isRegExp(a) && isRegExp(b) ? a + "" === b + "" : isObject(a) && isObject(b) ? deepEqual(a, b) : false;
}
function deepEqual(a, b) {
  if (Object.getPrototypeOf(a) !== Object.getPrototypeOf(b)) {
    return false;
  }
  if (a.length || b.length) {
    return arrayEqual(a, b);
  }
  const keysA = Object.keys(a);
  const keysB = Object.keys(b);
  if (keysA.length !== keysB.length) {
    return false;
  }
  keysA.sort();
  keysB.sort();
  if (!arrayEqual(keysA, keysB, (a2, b2) => a2 === b2)) {
    return false;
  }
  const n = keysA.length;
  for (let i = 0; i < n; ++i) {
    const k = keysA[i];
    if (!equal(a[k], b[k])) {
      return false;
    }
  }
  return true;
}
function arrayEqual(a, b, test = equal) {
  const n = a.length;
  if (n !== b.length) return false;
  for (let i = 0; i < n; ++i) {
    if (!test(a[i], b[i])) {
      return false;
    }
  }
  return true;
}
function recode(value2, map, fallback) {
  if (map instanceof Map) {
    if (map.has(value2)) return map.get(value2);
  } else {
    const key2 = `${value2}`;
    if (Object.hasOwn(map, key2)) return map[key2];
  }
  return fallback !== void 0 ? fallback : value2;
}
function sequence(start, stop, step) {
  let n = arguments.length;
  start = +start;
  stop = +stop;
  step = n < 2 ? (stop = start, start = 0, 1) : n < 3 ? 1 : +step;
  n = Math.max(0, Math.ceil((stop - start) / step)) | 0;
  const seq = new Array(n);
  for (let i = 0; i < n; ++i) {
    seq[i] = start + i * step;
  }
  return seq;
}
const NULL = void 0;
function isArray$2(value2) {
  return Array.isArray(value2);
}
const TypedArray$1 = Object.getPrototypeOf(Int8Array);
function isTypedArray$1(value2) {
  return value2 instanceof TypedArray$1;
}
function isArrayType(value2) {
  return isArray$2(value2) || isTypedArray$1(value2);
}
function isString(value2) {
  return typeof value2 === "string";
}
function isValid(value2) {
  return value2 != null && value2 === value2;
}
const isSeq = (seq) => isArrayType(seq) || isString(seq);
function compact(array2) {
  return isArrayType(array2) ? array2.filter((v) => isValid(v)) : array2;
}
function concat$2(...values2) {
  return [].concat(...values2);
}
function includes(sequence2, value2, index) {
  return isSeq(sequence2) ? sequence2.includes(value2, index) : false;
}
function indexof(sequence2, value2) {
  return isSeq(sequence2) ? sequence2.indexOf(value2) : -1;
}
function join$1(array2, delim) {
  return isArrayType(array2) ? array2.join(delim) : NULL;
}
function lastindexof(sequence2, value2) {
  return isSeq(sequence2) ? sequence2.lastIndexOf(value2) : -1;
}
function length(sequence2) {
  return isSeq(sequence2) ? sequence2.length : 0;
}
function pluck(array2, property) {
  return isArrayType(array2) ? array2.map((v) => isValid(v) ? v[property] : NULL) : NULL;
}
function reverse(sequence2) {
  return isArrayType(sequence2) ? sequence2.slice().reverse() : isString(sequence2) ? sequence2.split("").reverse().join("") : NULL;
}
function slice$2(sequence2, start, end) {
  return isSeq(sequence2) ? sequence2.slice(start, end) : NULL;
}
const array$1 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  compact,
  concat: concat$2,
  includes,
  indexof,
  join: join$1,
  lastindexof,
  length,
  pluck,
  reverse,
  slice: slice$2
}, Symbol.toStringTag, { value: "Module" }));
function pad(value2, width, char = "0") {
  const s = value2 + "";
  const len = s.length;
  return len < width ? Array(width - len + 1).join(char) + s : s;
}
const pad2 = (v) => (v < 10 ? "0" : "") + v;
const formatYear = (year2) => year2 < 0 ? "-" + pad(-year2, 6) : year2 > 9999 ? "+" + pad(year2, 6) : pad(year2, 4);
function formatISO(year2, month2, date2, hours2, min2, sec, ms, utc, short) {
  const suffix = utc ? "Z" : "";
  return formatYear(year2) + "-" + pad2(month2 + 1) + "-" + pad2(date2) + (!short || ms ? "T" + pad2(hours2) + ":" + pad2(min2) + ":" + pad2(sec) + "." + pad(ms, 3) + suffix : sec ? "T" + pad2(hours2) + ":" + pad2(min2) + ":" + pad2(sec) + suffix : min2 || hours2 || !utc ? "T" + pad2(hours2) + ":" + pad2(min2) + suffix : "");
}
function formatDate(d, short) {
  return isNaN(d) ? "Invalid Date" : formatISO(
    d.getFullYear(),
    d.getMonth(),
    d.getDate(),
    d.getHours(),
    d.getMinutes(),
    d.getSeconds(),
    d.getMilliseconds(),
    false,
    short
  );
}
function formatUTCDate(d, short) {
  return isNaN(d) ? "Invalid Date" : formatISO(
    d.getUTCFullYear(),
    d.getUTCMonth(),
    d.getUTCDate(),
    d.getUTCHours(),
    d.getUTCMinutes(),
    d.getUTCSeconds(),
    d.getUTCMilliseconds(),
    true,
    short
  );
}
const iso_re = /^([-+]\d{2})?\d{4}(-\d{2}(-\d{2})?)?(T\d{2}:\d{2}(:\d{2}(\.\d{3})?)?(Z|[-+]\d{2}:\d{2})?)?$/;
function isISODateString(value2) {
  return value2.match(iso_re) && !isNaN(Date.parse(value2));
}
function parseISODate(value2, parse4 = Date.parse) {
  return isISODateString(value2) ? parse4(value2) : value2;
}
const msMinute = 6e4;
const msDay = 864e5;
const msWeek = 6048e5;
const t0 = /* @__PURE__ */ new Date();
const t1 = /* @__PURE__ */ new Date();
const t = (d) => (t0.setTime(typeof d === "string" ? parseISODate(d) : d), t0);
function format_date(date2, shorten) {
  return formatDate(t(date2), !shorten);
}
function format_utcdate(date2, shorten) {
  return formatUTCDate(t(date2), !shorten);
}
function now() {
  return Date.now();
}
function timestamp$1(date2) {
  return +t(date2);
}
function datetime(year2, month2, date2, hours2, minutes2, seconds2, milliseconds2) {
  return !arguments.length ? new Date(Date.now()) : new Date(
    year2,
    month2 || 0,
    date2 == null ? 1 : date2,
    hours2 || 0,
    minutes2 || 0,
    seconds2 || 0,
    milliseconds2 || 0
  );
}
function year(date2) {
  return t(date2).getFullYear();
}
function quarter(date2) {
  return Math.floor(t(date2).getMonth() / 3);
}
function month(date2) {
  return t(date2).getMonth();
}
function week(date2, firstday) {
  const i = firstday || 0;
  t1.setTime(+date2);
  t1.setDate(t1.getDate() - (t1.getDay() + 7 - i) % 7);
  t1.setHours(0, 0, 0, 0);
  t0.setTime(+date2);
  t0.setMonth(0);
  t0.setDate(1);
  t0.setDate(1 - (t0.getDay() + 7 - i) % 7);
  t0.setHours(0, 0, 0, 0);
  const tz = (t1.getTimezoneOffset() - t0.getTimezoneOffset()) * msMinute;
  return Math.floor((1 + (+t1 - +t0) - tz) / msWeek);
}
function date$1(date2) {
  return t(date2).getDate();
}
function dayofyear(date2) {
  t1.setTime(+date2);
  t1.setHours(0, 0, 0, 0);
  t0.setTime(+t1);
  t0.setMonth(0);
  t0.setDate(1);
  const tz = (t1.getTimezoneOffset() - t0.getTimezoneOffset()) * msMinute;
  return Math.floor(1 + (+t1 - +t0 - tz) / msDay);
}
function dayofweek(date2) {
  return t(date2).getDay();
}
function hours(date2) {
  return t(date2).getHours();
}
function minutes(date2) {
  return t(date2).getMinutes();
}
function seconds(date2) {
  return t(date2).getSeconds();
}
function milliseconds(date2) {
  return t(date2).getMilliseconds();
}
function utcdatetime(year2, month2, date2, hours2, minutes2, seconds2, milliseconds2) {
  return !arguments.length ? new Date(Date.now()) : new Date(Date.UTC(
    year2,
    month2 || 0,
    date2 == null ? 1 : date2,
    hours2 || 0,
    minutes2 || 0,
    seconds2 || 0,
    milliseconds2 || 0
  ));
}
function utcyear(date2) {
  return t(date2).getUTCFullYear();
}
function utcquarter(date2) {
  return Math.floor(t(date2).getUTCMonth() / 3);
}
function utcmonth(date2) {
  return t(date2).getUTCMonth();
}
function utcweek(date2, firstday) {
  const i = firstday || 0;
  t1.setTime(+date2);
  t1.setUTCDate(t1.getUTCDate() - (t1.getUTCDay() + 7 - i) % 7);
  t1.setUTCHours(0, 0, 0, 0);
  t0.setTime(+date2);
  t0.setUTCMonth(0);
  t0.setUTCDate(1);
  t0.setUTCDate(1 - (t0.getUTCDay() + 7 - i) % 7);
  t0.setUTCHours(0, 0, 0, 0);
  return Math.floor((1 + (+t1 - +t0)) / msWeek);
}
function utcdate(date2) {
  return t(date2).getUTCDate();
}
function utcdayofyear(date2) {
  t1.setTime(+date2);
  t1.setUTCHours(0, 0, 0, 0);
  const t02 = Date.UTC(t1.getUTCFullYear(), 0, 1);
  return Math.floor(1 + (+t1 - t02) / msDay);
}
function utcdayofweek(date2) {
  return t(date2).getUTCDay();
}
function utchours(date2) {
  return t(date2).getUTCHours();
}
function utcminutes(date2) {
  return t(date2).getUTCMinutes();
}
function utcseconds(date2) {
  return t(date2).getUTCSeconds();
}
function utcmilliseconds(date2) {
  return t(date2).getUTCMilliseconds();
}
const date$2 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  date: date$1,
  datetime,
  dayofweek,
  dayofyear,
  format_date,
  format_utcdate,
  hours,
  milliseconds,
  minutes,
  month,
  now,
  quarter,
  seconds,
  timestamp: timestamp$1,
  utcdate,
  utcdatetime,
  utcdayofweek,
  utcdayofyear,
  utchours,
  utcmilliseconds,
  utcminutes,
  utcmonth,
  utcquarter,
  utcseconds,
  utcweek,
  utcyear,
  week,
  year
}, Symbol.toStringTag, { value: "Module" }));
function parse_json(value2) {
  return JSON.parse(value2);
}
function to_json(value2) {
  return JSON.stringify(value2);
}
const json = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  parse_json,
  to_json
}, Symbol.toStringTag, { value: "Module" }));
let source = Math.random;
function random$1() {
  return source();
}
function random() {
  return random$1();
}
function is_nan(value2) {
  return Number.isNaN(value2);
}
function is_finite(value2) {
  return Number.isFinite(value2);
}
function abs(value2) {
  return Math.abs(value2);
}
function cbrt(value2) {
  return Math.cbrt(value2);
}
function ceil(value2) {
  return Math.ceil(value2);
}
function clz32(value2) {
  return Math.clz32(value2);
}
function exp(value2) {
  return Math.exp(value2);
}
function expm1(value2) {
  return Math.expm1(value2);
}
function floor(value2) {
  return Math.floor(value2);
}
function fround(value2) {
  return Math.fround(value2);
}
function greatest(...values2) {
  return Math.max(...values2);
}
function least(...values2) {
  return Math.min(...values2);
}
function log(value2) {
  return Math.log(value2);
}
function log10(value2) {
  return Math.log10(value2);
}
function log1p(value2) {
  return Math.log1p(value2);
}
function log2(value2) {
  return Math.log2(value2);
}
function pow(base, exponent) {
  return Math.pow(base, exponent);
}
function round(value2) {
  return Math.round(value2);
}
function sign(value2) {
  return Math.sign(value2);
}
function sqrt(value2) {
  return Math.sqrt(value2);
}
function trunc(value2) {
  return Math.trunc(value2);
}
function degrees(radians2) {
  return 180 * radians2 / Math.PI;
}
function radians(degrees2) {
  return Math.PI * degrees2 / 180;
}
function acos(value2) {
  return Math.acos(value2);
}
function acosh(value2) {
  return Math.acosh(value2);
}
function asin(value2) {
  return Math.asin(value2);
}
function asinh(value2) {
  return Math.asinh(value2);
}
function atan(value2) {
  return Math.atan(value2);
}
function atan2(y, x) {
  return Math.atan2(y, x);
}
function atanh(value2) {
  return Math.atanh(value2);
}
function cos(value2) {
  return Math.cos(value2);
}
function cosh(value2) {
  return Math.cosh(value2);
}
function sin(value2) {
  return Math.sin(value2);
}
function sinh(value2) {
  return Math.sinh(value2);
}
function tan(value2) {
  return Math.tan(value2);
}
function tanh(value2) {
  return Math.tanh(value2);
}
const math = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  abs,
  acos,
  acosh,
  asin,
  asinh,
  atan,
  atan2,
  atanh,
  cbrt,
  ceil,
  clz32,
  cos,
  cosh,
  degrees,
  exp,
  expm1,
  floor,
  fround,
  greatest,
  is_finite,
  is_nan,
  least,
  log,
  log10,
  log1p,
  log2,
  pow,
  radians,
  random,
  round,
  sign,
  sin,
  sinh,
  sqrt,
  tan,
  tanh,
  trunc
}, Symbol.toStringTag, { value: "Module" }));
function isMap(value2) {
  return value2 instanceof Map;
}
function isSet(value2) {
  return value2 instanceof Set;
}
function isMapOrSet(value2) {
  return isMap(value2) || isSet(value2);
}
function array(iter) {
  return Array.from(iter);
}
function has(object2, key2) {
  return isMapOrSet(object2) ? object2.has(key2) : object2 != null ? Object.hasOwn(object2, `${key2}`) : false;
}
function keys(object2) {
  return isMap(object2) ? array(object2.keys()) : object2 != null ? (
    /** @type {K[]} */
    Object.keys(object2)
  ) : [];
}
function values$1(object2) {
  return isMapOrSet(object2) ? array(object2.values()) : object2 != null ? Object.values(object2) : [];
}
function entries$1(object2) {
  return isMapOrSet(object2) ? array(object2.entries()) : object2 != null ? (
    /** @type {[K, V][]} */
    Object.entries(object2)
  ) : [];
}
function object(entries2) {
  return entries2 ? (
    /** @type {Record<K, V>} */
    Object.fromEntries(entries2)
  ) : NULL;
}
const object$1 = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  entries: entries$1,
  has,
  keys,
  object,
  values: values$1
}, Symbol.toStringTag, { value: "Module" }));
function parse_date(value2) {
  return value2 == null ? value2 : new Date(value2);
}
function parse_float(value2) {
  return value2 == null ? value2 : Number.parseFloat(value2);
}
function parse_int(value2, radix) {
  return value2 == null ? value2 : Number.parseInt(value2, radix);
}
function endswith(value2, search, length2) {
  return value2 == null ? false : String(value2).endsWith(search, length2);
}
function match(value2, regexp, index) {
  const m = value2 == null ? value2 : String(value2).match(regexp);
  return index == null || m == null ? m : typeof index === "number" ? m[index] : m.groups ? m.groups[index] : null;
}
function normalize(value2, form) {
  return value2 == null ? value2 : String(value2).normalize(form);
}
function padend(value2, length2, fill) {
  return value2 == null ? value2 : String(value2).padEnd(length2, fill);
}
function padstart(value2, length2, fill) {
  return value2 == null ? value2 : String(value2).padStart(length2, fill);
}
function upper(value2) {
  return value2 == null ? value2 : String(value2).toUpperCase();
}
function lower(value2) {
  return value2 == null ? value2 : String(value2).toLowerCase();
}
function repeat$1(value2, number) {
  return value2 == null ? value2 : String(value2).repeat(number);
}
function replace(value2, pattern, replacement) {
  return value2 == null ? value2 : String(value2).replace(pattern, String(replacement));
}
function split(value2, separator, limit) {
  return value2 == null ? [] : String(value2).split(separator, limit);
}
function startswith(value2, search, position) {
  return value2 == null ? false : String(value2).startsWith(search, position);
}
function substring(value2, start, end) {
  return value2 == null ? value2 : String(value2).substring(start, end);
}
function trim(value2) {
  return value2 == null ? value2 : String(value2).trim();
}
const string = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  endswith,
  lower,
  match,
  normalize,
  padend,
  padstart,
  parse_date,
  parse_float,
  parse_int,
  repeat: repeat$1,
  replace,
  split,
  startswith,
  substring,
  trim,
  upper
}, Symbol.toStringTag, { value: "Module" }));
const functions = {
  bin,
  equal,
  recode,
  sequence,
  ...array$1,
  ...date$2,
  ...json,
  ...math,
  ...object$1,
  ...string
};
function toArray(value2) {
  return value2 != null ? isArray$2(value2) ? value2 : [value2] : [];
}
function isBigInt(value2) {
  return typeof value2 === "bigint";
}
function toString$1(v) {
  return v === void 0 ? v + "" : isBigInt(v) ? v + "n" : JSON.stringify(v);
}
let Op$1 = class Op {
  constructor(name2, fields, params) {
    this.name = name2;
    this.fields = fields;
    this.params = params;
  }
  toString() {
    const args = [
      ...this.fields.map((f) => `d[${toString$1(f)}]`),
      ...this.params.map(toString$1)
    ];
    return `d => op.${this.name}(${args})`;
  }
  toObject() {
    return { expr: this.toString(), func: true };
  }
};
function op(name2, fields = [], params = []) {
  return new Op$1(name2, toArray(fields), toArray(params));
}
const any = (field2) => op("any", field2);
const count = () => op("count");
const array_agg = (field2) => op("array_agg", field2);
const array_agg_distinct = (field2) => op("array_agg_distinct", field2);
const map_agg = (key2, value2) => op("map_agg", [key2, value2]);
const object_agg = (key2, value2) => op("object_agg", [key2, value2]);
const entries_agg = (key2, value2) => op("entries_agg", [key2, value2]);
({
  ...functions
});
function error(message, cause) {
  throw Error(message, { cause });
}
function uniqueName(names, name2) {
  names = isMapOrSet(names) ? names : new Set(names);
  let uname = name2;
  let index = 0;
  while (names.has(uname)) {
    uname = name2 + ++index;
  }
  return uname;
}
function isFunction(value2) {
  return typeof value2 === "function";
}
function repeat(reps, value2) {
  const result2 = Array(reps);
  if (isFunction(value2)) {
    for (let i = 0; i < reps; ++i) {
      result2[i] = value2(i);
    }
  } else {
    result2.fill(value2);
  }
  return result2;
}
function bins(min2, max2, maxbins = 15, nice = true, minstep = 0, step) {
  const base = 10;
  const logb = Math.LN10;
  if (step == null) {
    const level = Math.ceil(Math.log(maxbins) / logb);
    const span = max2 - min2 || Math.abs(min2) || 1;
    const div = [5, 2];
    step = Math.max(
      minstep,
      Math.pow(base, Math.round(Math.log(span) / logb) - level)
    );
    while (Math.ceil(span / step) > maxbins) {
      step *= base;
    }
    const n = div.length;
    for (let i = 0; i < n; ++i) {
      const v = step / div[i];
      if (v >= minstep && span / v <= maxbins) {
        step = v;
      }
    }
  }
  if (nice) {
    let v = Math.log(step);
    const precision = v >= 0 ? 0 : ~~(-v / logb) + 1;
    const eps = Math.pow(base, -precision - 1);
    v = Math.floor(min2 / step + eps) * step;
    min2 = min2 < v ? v - step : v;
    max2 = Math.ceil(max2 / step) * step;
  }
  return [
    min2,
    max2 === min2 ? min2 + step : max2,
    step
  ];
}
function key(value2) {
  const type = typeof value2;
  return type === "string" ? `"${value2}"` : type !== "object" || !value2 ? value2 : isDate$1(value2) ? +value2 : isArray$2(value2) || isTypedArray$1(value2) ? `[${value2.map(key)}]` : isRegExp(value2) ? value2 + "" : objectKey$1(value2);
}
function objectKey$1(value2) {
  let s = "{";
  let i = -1;
  for (const k in value2) {
    if (++i > 0) s += ",";
    s += `"${k}":${key(value2[k])}`;
  }
  s += "}";
  return s;
}
function keyFunction(get2, nulls) {
  const n = get2.length;
  return n === 1 ? (row, data2) => key(get2[0](row, data2)) : (row, data2) => {
    let s = "";
    for (let i = 0; i < n; ++i) {
      if (i > 0) s += "|";
      const v = get2[i](row, data2);
      if (nulls && (v == null || v !== v)) return null;
      s += key(v);
    }
    return s;
  };
}
function distinctMap() {
  const map = /* @__PURE__ */ new Map();
  return {
    count() {
      return map.size;
    },
    values() {
      return Array.from(map.values(), (_) => _.v);
    },
    increment(v) {
      const k = key(v);
      const e = map.get(k);
      e ? ++e.n : map.set(k, { v, n: 1 });
    },
    decrement(v) {
      const k = key(v);
      const e = map.get(k);
      e.n === 1 ? map.delete(k) : --e.n;
    },
    forEach(fn) {
      map.forEach(({ v, n }) => fn(v, n));
    }
  };
}
function noop() {
}
function product(values2, start = 0, stop = values2.length) {
  let prod = values2[start++];
  for (let i = start; i < stop; ++i) {
    prod *= values2[i];
  }
  return prod;
}
function initOp(op2) {
  op2.init = op2.init || noop;
  op2.add = op2.add || noop;
  op2.rem = op2.rem || noop;
  return op2;
}
function initProduct(s, value2) {
  s.product_v = false;
  return s.product = value2;
}
const aggregateFunctions = {
  /** @type {AggregateDef} */
  count: {
    create: () => initOp({
      value: (s) => s.count
    }),
    param: []
  },
  /** @type {AggregateDef} */
  array_agg: {
    create: () => initOp({
      init: (s) => s.values = true,
      value: (s) => s.list.values(s.stream)
    }),
    param: [1]
  },
  /** @type {AggregateDef} */
  object_agg: {
    create: () => initOp({
      init: (s) => s.values = true,
      value: (s) => Object.fromEntries(s.list.values())
    }),
    param: [2]
  },
  /** @type {AggregateDef} */
  map_agg: {
    create: () => initOp({
      init: (s) => s.values = true,
      value: (s) => new Map(s.list.values())
    }),
    param: [2]
  },
  /** @type {AggregateDef} */
  entries_agg: {
    create: () => initOp({
      init: (s) => s.values = true,
      value: (s) => s.list.values(s.stream)
    }),
    param: [2]
  },
  /** @type {AggregateDef} */
  any: {
    create: () => initOp({
      add: (s, v) => {
        if (s.any == null) s.any = v;
      },
      value: (s) => s.valid ? s.any : NULL
    }),
    param: [1]
  },
  /** @type {AggregateDef} */
  valid: {
    create: () => initOp({
      value: (s) => s.valid
    }),
    param: [1]
  },
  /** @type {AggregateDef} */
  invalid: {
    create: () => initOp({
      value: (s) => s.count - s.valid
    }),
    param: [1]
  },
  /** @type {AggregateDef} */
  distinct: {
    create: () => ({
      init: (s) => s.distinct = distinctMap(),
      value: (s) => s.distinct.count() + (s.valid === s.count ? 0 : 1),
      add: (s, v) => s.distinct.increment(v),
      rem: (s, v) => s.distinct.decrement(v)
    }),
    param: [1]
  },
  /** @type {AggregateDef} */
  array_agg_distinct: {
    create: () => initOp({
      value: (s) => s.distinct.values()
    }),
    param: [1],
    req: ["distinct"]
  },
  /** @type {AggregateDef} */
  mode: {
    create: () => initOp({
      value: (s) => {
        let mode = NULL;
        let max2 = 0;
        s.distinct.forEach((value2, count2) => {
          if (count2 > max2) {
            max2 = count2;
            mode = value2;
          }
        });
        return mode;
      }
    }),
    param: [1],
    req: ["distinct"]
  },
  /** @type {AggregateDef} */
  sum: {
    create: () => ({
      init: (s) => s.sum = 0,
      value: (s) => s.valid ? s.sum : NULL,
      add: (s, v) => isBigInt(v) ? s.sum === 0 ? s.sum = v : s.sum += v : s.sum += +v,
      rem: (s, v) => s.sum -= v
    }),
    param: [1]
  },
  /** @type {AggregateDef} */
  product: {
    create: () => ({
      init: (s) => initProduct(s, 1),
      value: (s) => s.valid ? s.product_v ? initProduct(s, product(s.list.values())) : s.product : void 0,
      add: (s, v) => isBigInt(v) ? s.product === 1 ? s.product = v : s.product *= v : s.product *= v,
      rem: (s, v) => v == 0 || v === Infinity || v === -Infinity ? s.product_v = true : s.product /= v
    }),
    param: [1],
    stream: ["array_agg"]
  },
  /** @type {AggregateDef} */
  mean: {
    create: () => ({
      init: (s) => s.mean = 0,
      value: (s) => s.valid ? s.mean : NULL,
      add: (s, v) => {
        s.mean_d = v - s.mean;
        s.mean += s.mean_d / s.valid;
      },
      rem: (s, v) => {
        s.mean_d = v - s.mean;
        s.mean -= s.valid ? s.mean_d / s.valid : s.mean;
      }
    }),
    param: [1]
  },
  /** @type {AggregateDef} */
  average: {
    create: () => initOp({
      value: (s) => s.valid ? s.mean : NULL
    }),
    param: [1],
    req: ["mean"]
  },
  /** @type {AggregateDef} */
  variance: {
    create: () => ({
      init: (s) => s.dev = 0,
      value: (s) => s.valid > 1 ? s.dev / (s.valid - 1) : NULL,
      add: (s, v) => s.dev += s.mean_d * (v - s.mean),
      rem: (s, v) => s.dev -= s.mean_d * (v - s.mean)
    }),
    param: [1],
    req: ["mean"]
  },
  /** @type {AggregateDef} */
  variancep: {
    create: () => initOp({
      value: (s) => s.valid > 1 ? s.dev / s.valid : NULL
    }),
    param: [1],
    req: ["variance"]
  },
  /** @type {AggregateDef} */
  stdev: {
    create: () => initOp({
      value: (s) => s.valid > 1 ? Math.sqrt(s.dev / (s.valid - 1)) : NULL
    }),
    param: [1],
    req: ["variance"]
  },
  /** @type {AggregateDef} */
  stdevp: {
    create: () => initOp({
      value: (s) => s.valid > 1 ? Math.sqrt(s.dev / s.valid) : NULL
    }),
    param: [1],
    req: ["variance"]
  },
  /** @type {AggregateDef} */
  min: {
    create: () => ({
      init: (s) => s.min = NULL,
      value: (s) => s.min = Number.isNaN(s.min) ? s.list.min() : s.min,
      add: (s, v) => {
        if (v < s.min || s.min === NULL) s.min = v;
      },
      rem: (s, v) => {
        if (v <= s.min) s.min = NaN;
      }
    }),
    param: [1],
    stream: ["array_agg"]
  },
  /** @type {AggregateDef} */
  max: {
    create: () => ({
      init: (s) => s.max = NULL,
      value: (s) => s.max = Number.isNaN(s.max) ? s.list.max() : s.max,
      add: (s, v) => {
        if (v > s.max || s.max === NULL) s.max = v;
      },
      rem: (s, v) => {
        if (v >= s.max) s.max = NaN;
      }
    }),
    param: [1],
    stream: ["array_agg"]
  },
  /** @type {AggregateDef} */
  quantile: {
    create: (p) => initOp({
      value: (s) => s.list.quantile(p)
    }),
    param: [1, 1],
    req: ["array_agg"]
  },
  /** @type {AggregateDef} */
  median: {
    create: () => initOp({
      value: (s) => s.list.quantile(0.5)
    }),
    param: [1],
    req: ["array_agg"]
  },
  /** @type {AggregateDef} */
  covariance: {
    create: () => ({
      init: (s) => {
        s.cov = s.mean_x = s.mean_y = s.dev_x = s.dev_y = 0;
      },
      value: (s) => s.valid > 1 ? s.cov / (s.valid - 1) : NULL,
      add: (s, x, y) => {
        const dx = x - s.mean_x;
        const dy = y - s.mean_y;
        s.mean_x += dx / s.valid;
        s.mean_y += dy / s.valid;
        const dy2 = y - s.mean_y;
        s.dev_x += dx * (x - s.mean_x);
        s.dev_y += dy * dy2;
        s.cov += dx * dy2;
      },
      rem: (s, x, y) => {
        const dx = x - s.mean_x;
        const dy = y - s.mean_y;
        s.mean_x -= s.valid ? dx / s.valid : s.mean_x;
        s.mean_y -= s.valid ? dy / s.valid : s.mean_y;
        const dy2 = y - s.mean_y;
        s.dev_x -= dx * (x - s.mean_x);
        s.dev_y -= dy * dy2;
        s.cov -= dx * dy2;
      }
    }),
    param: [2]
  },
  /** @type {AggregateDef} */
  covariancep: {
    create: () => initOp({
      value: (s) => s.valid > 1 ? s.cov / s.valid : NULL
    }),
    param: [2],
    req: ["covariance"]
  },
  /** @type {AggregateDef} */
  corr: {
    create: () => initOp({
      value: (s) => s.valid > 1 ? s.cov / (Math.sqrt(s.dev_x) * Math.sqrt(s.dev_y)) : NULL
    }),
    param: [2],
    req: ["covariance"]
  },
  /** @type {AggregateDef} */
  bins: {
    create: (maxbins, nice, minstep, step) => initOp({
      value: (s) => bins(s.min, s.max, maxbins, nice, minstep, step)
    }),
    param: [1, 4],
    req: ["min", "max"]
  }
};
const rank = {
  create() {
    let rank2;
    return {
      init: () => rank2 = 1,
      value: (w) => {
        const i = w.index;
        return i && !w.peer(i) ? rank2 = i + 1 : rank2;
      }
    };
  },
  param: []
};
const cume_dist = {
  create() {
    let cume;
    return {
      init: () => cume = 0,
      value: (w) => {
        const { index, peer, size } = w;
        let i = index;
        if (cume < i) {
          while (i + 1 < size && peer(i + 1)) ++i;
          cume = i;
        }
        return (1 + cume) / size;
      }
    };
  },
  param: []
};
const windowFunctions = {
  /** @type {WindowDef} */
  row_number: {
    create() {
      return {
        init: noop,
        value: (w) => w.index + 1
      };
    },
    param: []
  },
  /** @type {WindowDef} */
  rank,
  /** @type {WindowDef} */
  avg_rank: {
    create() {
      let j, rank2;
      return {
        init: () => (j = -1, rank2 = 1),
        value: (w) => {
          const i = w.index;
          if (i >= j) {
            for (rank2 = j = i + 1; w.peer(j); rank2 += ++j) ;
            rank2 /= j - i;
          }
          return rank2;
        }
      };
    },
    param: []
  },
  /** @type {WindowDef} */
  dense_rank: {
    create() {
      let drank;
      return {
        init: () => drank = 1,
        value: (w) => {
          const i = w.index;
          return i && !w.peer(i) ? ++drank : drank;
        }
      };
    },
    param: []
  },
  /** @type {WindowDef} */
  percent_rank: {
    create() {
      const { init, value: value2 } = rank.create();
      return {
        init,
        value: (w) => (value2(w) - 1) / (w.size - 1)
      };
    },
    param: []
  },
  /** @type {WindowDef} */
  cume_dist,
  /** @type {WindowDef} */
  ntile: {
    create(num) {
      num = +num;
      if (!(num > 0)) error("ntile num must be greater than zero.");
      const { init, value: value2 } = cume_dist.create();
      return {
        init,
        value: (w) => Math.ceil(num * value2(w))
      };
    },
    param: [0, 1]
  },
  /** @type {WindowDef} */
  lag: {
    create(offset2, defaultValue = NULL) {
      offset2 = +offset2 || 1;
      return {
        init: noop,
        value: (w, f) => {
          const i = w.index - offset2;
          return i >= 0 ? w.value(i, f) : defaultValue;
        }
      };
    },
    param: [1, 2]
  },
  /** @type {WindowDef} */
  lead: {
    create(offset2, defaultValue = NULL) {
      offset2 = +offset2 || 1;
      return {
        init: noop,
        value: (w, f) => {
          const i = w.index + offset2;
          return i < w.size ? w.value(i, f) : defaultValue;
        }
      };
    },
    param: [1, 2]
  },
  /** @type {WindowDef} */
  first_value: {
    create() {
      return {
        init: noop,
        value: (w, f) => w.value(w.i0, f)
      };
    },
    param: [1]
  },
  /** @type {WindowDef} */
  last_value: {
    create() {
      return {
        init: noop,
        value: (w, f) => w.value(w.i1 - 1, f)
      };
    },
    param: [1]
  },
  /** @type {WindowDef} */
  nth_value: {
    create(nth) {
      nth = +nth;
      if (!(nth > 0)) error("nth_value nth must be greater than zero.");
      return {
        init: noop,
        value: (w, f) => {
          const i = w.i0 + (nth - 1);
          return i < w.i1 ? w.value(i, f) : NULL;
        }
      };
    },
    param: [1, 1]
  },
  /** @type {WindowDef} */
  fill_down: {
    create(defaultValue = NULL) {
      let value2;
      return {
        init: () => value2 = defaultValue,
        value: (w, f) => {
          const v = w.value(w.index, f);
          return isValid(v) ? value2 = v : value2;
        }
      };
    },
    param: [1, 1]
  },
  /** @type {WindowDef} */
  fill_up: {
    create(defaultValue = NULL) {
      let value2, idx;
      return {
        init: () => (value2 = defaultValue, idx = -1),
        value: (w, f) => w.index <= idx ? value2 : (idx = find(w, f, w.index)) >= 0 ? value2 = w.value(idx, f) : (idx = w.size, value2 = defaultValue)
      };
    },
    param: [1, 1]
  }
};
function find(w, f, i) {
  for (const n = w.size; i < n; ++i) {
    if (isValid(w.value(i, f))) return i;
  }
  return -1;
}
function hasAggregate(name2) {
  return Object.hasOwn(aggregateFunctions, name2);
}
function hasWindow(name2) {
  return Object.hasOwn(windowFunctions, name2);
}
function hasFunction(name2) {
  return Object.hasOwn(functions, name2) || name2 === "row_object";
}
function getAggregate(name2) {
  return hasAggregate(name2) && aggregateFunctions[name2];
}
function getWindow(name2) {
  return hasWindow(name2) && windowFunctions[name2];
}
function concat$1(list2, fn = ((x, i) => x), delim = "") {
  const n = list2.length;
  if (!n) return "";
  let s = fn(list2[0], 0);
  for (let i = 1; i < n; ++i) {
    s += delim + fn(list2[i], i);
  }
  return s;
}
function unroll$1(args, code, ...lists) {
  const v = ["_", "$"];
  const a = v.slice(0, lists.length);
  a.push(
    '"use strict"; const ' + lists.map((l, j) => l.map((_, i) => `${v[j]}${i} = ${v[j]}[${i}]`).join(", ")).join(", ") + `; return (${args}) => ${code};`
  );
  return Function(...a)(...lists);
}
function ascending(a, b) {
  return a < b ? -1 : a > b ? 1 : a >= b ? 0 : NaN;
}
function max(values2, start = 0, stop = values2.length) {
  let max2 = stop ? values2[start++] : NULL;
  for (let i = start; i < stop; ++i) {
    if (max2 < values2[i]) {
      max2 = values2[i];
    }
  }
  return max2;
}
function min(values2, start = 0, stop = values2.length) {
  let min2 = stop ? values2[start++] : NULL;
  for (let i = start; i < stop; ++i) {
    if (min2 > values2[i]) {
      min2 = values2[i];
    }
  }
  return min2;
}
function toNumeric(value2) {
  return isBigInt(value2) ? value2 : +value2;
}
function quantile(values2, p) {
  const n = values2.length;
  if (!n) return NULL;
  if ((p = +p) <= 0 || n < 2) return toNumeric(values2[0]);
  if (p >= 1) return toNumeric(values2[n - 1]);
  const i = (n - 1) * p;
  const i0 = Math.floor(i);
  const v0 = toNumeric(values2[i0]);
  return isBigInt(v0) ? v0 : v0 + (toNumeric(values2[i0 + 1]) - v0) * (i - i0);
}
let ValueList$1 = class ValueList {
  constructor(values2) {
    this._values = values2 || [];
    this._sorted = null;
    this._start = 0;
  }
  values(copy) {
    if (this._start) {
      this._values = this._values.slice(this._start);
      this._start = 0;
    }
    return copy ? this._values.slice() : this._values;
  }
  add(value2) {
    this._values.push(value2);
    this._sorted = null;
  }
  rem() {
    this._start += 1;
    this._sorted = null;
  }
  min() {
    return this._sorted && this._sorted.length ? this._sorted[0] : min(this._values, this._start);
  }
  max() {
    return this._sorted && this._sorted.length ? this._sorted[this._sorted.length - 1] : max(this._values, this._start);
  }
  quantile(p) {
    if (!this._sorted) {
      this._sorted = this.values(true);
      this._sorted.sort(ascending);
    }
    return quantile(this._sorted, p);
  }
};
class Reducer {
  constructor(outputs) {
    this._outputs = outputs;
  }
  size() {
    return this._outputs.length;
  }
  outputs() {
    return this._outputs;
  }
  // eslint-disable-next-line no-unused-vars
  init(columns2) {
    return {};
  }
  // eslint-disable-next-line no-unused-vars
  add(state, row, data2) {
  }
  // eslint-disable-next-line no-unused-vars
  rem(state, row, data2) {
  }
  // eslint-disable-next-line no-unused-vars
  write(state, values2, index) {
  }
}
const update = (ops, args, fn) => unroll$1(
  args,
  "{" + concat$1(ops, (_, i) => `_${i}.${fn}(${args});`) + "}",
  ops
);
function fieldReducer(oplist, stream) {
  const { ops, output: output2 } = expand$1(oplist, stream);
  const fields = oplist[0].fields;
  const n = fields.length;
  const cls = n === 0 ? FieldReducer : n === 1 ? Field1Reducer : n === 2 ? Field2Reducer : error("Unsupported field count: " + n);
  return new cls(fields, ops, output2, stream);
}
function expand$1(oplist, stream) {
  const has2 = {};
  const ops = [];
  function add(name2, params = []) {
    const key2 = name2 + ":" + params;
    if (has2[key2]) return has2[key2];
    const def = getAggregate(name2);
    const op2 = def.create(...params);
    if (stream < 0 && def.stream) {
      def.stream.forEach((name3) => add(name3, []));
    }
    if (def.req) {
      def.req.forEach((name3) => add(name3, []));
    }
    has2[key2] = op2;
    ops.push(op2);
    return op2;
  }
  const output2 = oplist.map((item) => {
    const op2 = add(item.name, item.params);
    op2.output = item.id;
    return op2;
  });
  return { ops, output: output2 };
}
class FieldReducer extends Reducer {
  constructor(fields, ops, outputs, stream) {
    super(outputs);
    this._op = ops;
    this._fields = fields;
    this._stream = !!stream;
  }
  init() {
    const state = { count: 0, valid: 0, stream: this._stream };
    this._op.forEach((op2) => op2.init(state));
    if (state.values) {
      state.list = new ValueList$1();
    }
    return state;
  }
  write(state, values2, index) {
    const op2 = this._outputs;
    const n = op2.length;
    for (let i = 0; i < n; ++i) {
      values2[op2[i].output][index] = op2[i].value(state);
    }
    return 1;
  }
  _add() {
  }
  _rem() {
  }
  add(state) {
    ++state.count;
  }
  rem(state) {
    --state.count;
  }
}
class Field1Reducer extends FieldReducer {
  constructor(fields, ops, outputs, stream) {
    super(fields, ops, outputs, stream);
    const args = ["state", "v1", "v2"];
    this._add = update(ops, args, "add");
    this._rem = update(ops, args, "rem");
  }
  add(state, row, data2) {
    const value2 = this._fields[0](row, data2);
    ++state.count;
    if (isValid(value2)) {
      ++state.valid;
      if (state.list) state.list.add(value2);
      this._add(state, value2);
    }
  }
  rem(state, row, data2) {
    const value2 = this._fields[0](row, data2);
    --state.count;
    if (isValid(value2)) {
      --state.valid;
      if (state.list) state.list.rem();
      this._rem(state, value2);
    }
  }
}
class Field2Reducer extends FieldReducer {
  constructor(fields, ops, outputs, stream) {
    super(fields, ops, outputs, stream);
    const args = ["state", "v1", "v2"];
    this._add = update(ops, args, "add");
    this._rem = update(ops, args, "rem");
  }
  add(state, row, data2) {
    const value1 = this._fields[0](row, data2);
    const value2 = this._fields[1](row, data2);
    ++state.count;
    if (isValid(value1) && isValid(value2)) {
      ++state.valid;
      if (state.list) state.list.add([value1, value2]);
      this._add(state, value1, value2);
    }
  }
  rem(state, row, data2) {
    const value1 = this._fields[0](row, data2);
    const value2 = this._fields[1](row, data2);
    --state.count;
    if (isValid(value1) && isValid(value2)) {
      --state.valid;
      if (state.list) state.list.rem();
      this._rem(state, value1, value2);
    }
  }
}
function aggregateGet(table2, ops, get2) {
  if (ops.length) {
    const data2 = table2.data();
    const { keys: keys2 } = table2.groups() || {};
    const result2 = aggregate(table2, ops);
    const op2 = keys2 ? (name2, row) => result2[name2][keys2[row]] : (name2) => result2[name2][0];
    get2 = get2.map((f) => (row) => f(row, data2, op2));
  }
  return get2;
}
function aggregate(table2, ops, result2) {
  if (!ops.length) return result2;
  const aggrs = reducers(ops);
  const groups = table2.groups();
  const size = groups ? groups.size : 1;
  result2 = result2 || repeat(ops.length, () => Array(size));
  if (size > 1) {
    aggrs.forEach((aggr) => {
      const cells = reduceGroups(table2, aggr, groups);
      for (let i = 0; i < size; ++i) {
        aggr.write(cells[i], result2, i);
      }
    });
  } else {
    aggrs.forEach((aggr) => {
      const cell = reduceFlat(table2, aggr);
      aggr.write(cell, result2, 0);
    });
  }
  return result2;
}
function reducers(ops, stream) {
  const aggrs = [];
  const fields = {};
  for (const op2 of ops) {
    const key2 = op2.fields.map((f) => f + "").join(",");
    (fields[key2] || (fields[key2] = [])).push(op2);
  }
  for (const key2 in fields) {
    aggrs.push(fieldReducer(fields[key2], stream));
  }
  return aggrs;
}
function reduceFlat(table2, reducer) {
  const cell = reducer.init();
  const data2 = table2.data();
  const bits = table2.mask();
  if (table2.isOrdered()) {
    const idx = table2.indices();
    const m = idx.length;
    for (let i = 0; i < m; ++i) {
      reducer.add(cell, idx[i], data2);
    }
  } else if (bits) {
    for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
      reducer.add(cell, i, data2);
    }
  } else {
    const n = table2.totalRows();
    for (let i = 0; i < n; ++i) {
      reducer.add(cell, i, data2);
    }
  }
  return cell;
}
function reduceGroups(table2, reducer, groups) {
  const { keys: keys2, size } = groups;
  const cells = repeat(size, () => reducer.init());
  const data2 = table2.data();
  if (table2.isOrdered()) {
    const idx = table2.indices();
    const m = idx.length;
    for (let i = 0; i < m; ++i) {
      const row = idx[i];
      reducer.add(cells[keys2[row]], row, data2);
    }
  } else if (table2.isFiltered()) {
    const bits = table2.mask();
    for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
      reducer.add(cells[keys2[i]], i, data2);
    }
  } else {
    const n = table2.totalRows();
    for (let i = 0; i < n; ++i) {
      reducer.add(cells[keys2[i]], i, data2);
    }
  }
  return cells;
}
function groupOutput(cols, groups) {
  const { get: get2, names, rows, size } = groups;
  const m = names.length;
  for (let j = 0; j < m; ++j) {
    const col = cols.add(names[j], Array(size));
    const val = get2[j];
    for (let i = 0; i < size; ++i) {
      col[i] = val(rows[i]);
    }
  }
}
function entries(value2) {
  return isArray$2(value2) ? value2 : isMap(value2) ? value2.entries() : value2 ? Object.entries(value2) : [];
}
const ArrayPattern = "ArrayPattern";
const ArrowFunctionExpression = "ArrowFunctionExpression";
const FunctionExpression = "FunctionExpression";
const Identifier = "Identifier";
const Literal = "Literal";
const MemberExpression = "MemberExpression";
const ObjectExpression = "ObjectExpression";
const ObjectPattern = "ObjectPattern";
const Property = "Property";
const Column$1 = "Column";
const Constant = "Constant";
const Dictionary2 = "Dictionary";
const Function$1 = "Function";
const Parameter = "Parameter";
const Op2 = "Op";
function walk(node, ctx, visitors2, parent) {
  const visit2 = visitors2[node.type] || visitors2["Default"];
  if (visit2 && visit2(node, ctx, parent) === false) return;
  const walker = walkers[node.type];
  if (walker) walker(node, ctx, visitors2);
}
const unary = (node, ctx, visitors2) => {
  walk(node.argument, ctx, visitors2, node);
};
const binary$2 = (node, ctx, visitors2) => {
  walk(node.left, ctx, visitors2, node);
  walk(node.right, ctx, visitors2, node);
};
const ternary = (node, ctx, visitors2) => {
  walk(node.test, ctx, visitors2, node);
  walk(node.consequent, ctx, visitors2, node);
  if (node.alternate) walk(node.alternate, ctx, visitors2, node);
};
const func$1 = (node, ctx, visitors2) => {
  list$3(node.params, ctx, visitors2, node);
  walk(node.body, ctx, visitors2, node);
};
const call$1 = (node, ctx, visitors2) => {
  walk(node.callee, ctx, visitors2, node);
  list$3(node.arguments, ctx, visitors2, node);
};
const list$3 = (nodes, ctx, visitors2, node) => {
  nodes.forEach((item) => walk(item, ctx, visitors2, node));
};
const walkers = {
  TemplateLiteral: (node, ctx, visitors2) => {
    list$3(node.expressions, ctx, visitors2, node);
    list$3(node.quasis, ctx, visitors2, node);
  },
  MemberExpression: (node, ctx, visitors2) => {
    walk(node.object, ctx, visitors2, node);
    walk(node.property, ctx, visitors2, node);
  },
  CallExpression: call$1,
  NewExpression: call$1,
  ArrayExpression: (node, ctx, visitors2) => {
    list$3(node.elements, ctx, visitors2, node);
  },
  AssignmentExpression: binary$2,
  AwaitExpression: unary,
  BinaryExpression: binary$2,
  LogicalExpression: binary$2,
  UnaryExpression: unary,
  UpdateExpression: unary,
  ConditionalExpression: ternary,
  ObjectExpression: (node, ctx, visitors2) => {
    list$3(node.properties, ctx, visitors2, node);
  },
  Property: (node, ctx, visitors2) => {
    walk(node.key, ctx, visitors2, node);
    walk(node.value, ctx, visitors2, node);
  },
  ArrowFunctionExpression: func$1,
  FunctionExpression: func$1,
  FunctionDeclaration: func$1,
  VariableDeclaration: (node, ctx, visitors2) => {
    list$3(node.declarations, ctx, visitors2, node);
  },
  VariableDeclarator: (node, ctx, visitors2) => {
    walk(node.id, ctx, visitors2, node);
    walk(node.init, ctx, visitors2, node);
  },
  SpreadElement: (node, ctx, visitors2) => {
    walk(node.argument, ctx, visitors2, node);
  },
  BlockStatement: (node, ctx, visitors2) => {
    list$3(node.body, ctx, visitors2, node);
  },
  ExpressionStatement: (node, ctx, visitors2) => {
    walk(node.expression, ctx, visitors2, node);
  },
  IfStatement: ternary,
  ForStatement: (node, ctx, visitors2) => {
    walk(node.init, ctx, visitors2, node);
    walk(node.test, ctx, visitors2, node);
    walk(node.update, ctx, visitors2, node);
    walk(node.body, ctx, visitors2, node);
  },
  WhileStatement: (node, ctx, visitors2) => {
    walk(node.test, ctx, visitors2, node);
    walk(node.body, ctx, visitors2, node);
  },
  DoWhileStatement: (node, ctx, visitors2) => {
    walk(node.body, ctx, visitors2, node);
    walk(node.test, ctx, visitors2, node);
  },
  SwitchStatement: (node, ctx, visitors2) => {
    walk(node.discriminant, ctx, visitors2, node);
    list$3(node.cases, ctx, visitors2, node);
  },
  SwitchCase: (node, ctx, visitors2) => {
    if (node.test) walk(node.test, ctx, visitors2, node);
    list$3(node.consequent, ctx, visitors2, node);
  },
  ReturnStatement: unary,
  Program: (node, ctx, visitors2) => {
    walk(node.body[0], ctx, visitors2, node);
  }
};
function strip(node) {
  delete node.start;
  delete node.end;
  delete node.optional;
}
function stripMember(node) {
  strip(node);
  delete node.object;
  delete node.property;
  delete node.computed;
  if (!node.table) delete node.table;
}
function clean(ast) {
  walk(ast, null, {
    Column: stripMember,
    Constant: stripMember,
    Default: strip
  });
  return ast;
}
function is(type, node) {
  return node && node.type === type;
}
function isFunctionExpression(node) {
  return is(FunctionExpression, node) || is(ArrowFunctionExpression, node);
}
const visit$2 = (node, opt2) => {
  const f = visitors$1[node.type];
  return f ? f(node, opt2) : error(`Unsupported expression construct: ${node.type}`);
};
const binary$1 = (node, opt2) => {
  return "(" + visit$2(node.left, opt2) + " " + node.operator + " " + visit$2(node.right, opt2) + ")";
};
const func = (node, opt2) => {
  return "(" + list$2(node.params, opt2) + ")=>" + visit$2(node.body, opt2);
};
const call = (node, opt2) => {
  return visit$2(node.callee, opt2) + "(" + list$2(node.arguments, opt2) + ")";
};
const list$2 = (array2, opt2, delim = ",") => {
  return array2.map((node) => visit$2(node, opt2)).join(delim);
};
const name = (node) => node.computed ? `[${toString$1(node.name)}]` : `.${node.name}`;
const ref$1 = (node, opt2, method) => {
  const table2 = node.table || "";
  return `data${table2}${name(node)}.${method}(${opt2.index}${table2})`;
};
const get$1 = (node, opt2) => {
  const table2 = node.table || "";
  return `data${table2}${name(node)}[${opt2.index}${table2}]`;
};
const visitors$1 = {
  Constant: (node) => node.raw,
  Column: (node, opt2) => node.array ? get$1(node, opt2) : ref$1(node, opt2, "at"),
  Dictionary: (node, opt2) => ref$1(node, opt2, "key"),
  Function: (node) => `fn.${node.name}`,
  Parameter: (node) => `$${name(node)}`,
  Op: (node, opt2) => `op(${toString$1(node.name)},${opt2.op || opt2.index})`,
  Literal: (node) => node.raw,
  Identifier: (node) => node.name,
  TemplateLiteral: (node, opt2) => {
    const { quasis, expressions } = node;
    const n = expressions.length;
    let t2 = quasis[0].value.raw;
    for (let i = 0; i < n; ) {
      t2 += "${" + visit$2(expressions[i], opt2) + "}" + quasis[++i].value.raw;
    }
    return "`" + t2 + "`";
  },
  MemberExpression: (node, opt2) => {
    const d = !node.computed;
    const o = visit$2(node.object, opt2);
    const p = visit$2(node.property, opt2);
    return o + (d ? "." + p : "[" + p + "]");
  },
  CallExpression: call,
  NewExpression: (node, opt2) => {
    return "new " + call(node, opt2);
  },
  ArrayExpression: (node, opt2) => {
    return "[" + list$2(node.elements, opt2) + "]";
  },
  AssignmentExpression: binary$1,
  BinaryExpression: binary$1,
  LogicalExpression: binary$1,
  UnaryExpression: (node, opt2) => {
    return "(" + node.operator + visit$2(node.argument, opt2) + ")";
  },
  ConditionalExpression: (node, opt2) => {
    return "(" + visit$2(node.test, opt2) + "?" + visit$2(node.consequent, opt2) + ":" + visit$2(node.alternate, opt2) + ")";
  },
  ObjectExpression: (node, opt2) => {
    return "({" + list$2(node.properties, opt2) + "})";
  },
  Property: (node, opt2) => {
    const key2 = visit$2(node.key, opt2);
    return (node.computed ? `[${key2}]` : key2) + ":" + visit$2(node.value, opt2);
  },
  ArrowFunctionExpression: func,
  FunctionExpression: func,
  FunctionDeclaration: func,
  ArrayPattern: (node, opt2) => {
    return "[" + list$2(node.elements, opt2) + "]";
  },
  ObjectPattern: (node, opt2) => {
    return "{" + list$2(node.properties, opt2) + "}";
  },
  VariableDeclaration: (node, opt2) => {
    return node.kind + " " + list$2(node.declarations, opt2, ",");
  },
  VariableDeclarator: (node, opt2) => {
    return visit$2(node.id, opt2) + "=" + visit$2(node.init, opt2);
  },
  SpreadElement: (node, opt2) => {
    return "..." + visit$2(node.argument, opt2);
  },
  BlockStatement: (node, opt2) => {
    return "{" + list$2(node.body, opt2, ";") + ";}";
  },
  BreakStatement: () => {
    return "break";
  },
  ExpressionStatement: (node, opt2) => {
    return visit$2(node.expression, opt2);
  },
  IfStatement: (node, opt2) => {
    return "if (" + visit$2(node.test, opt2) + ")" + visit$2(node.consequent, opt2) + (node.alternate ? " else " + visit$2(node.alternate, opt2) : "");
  },
  SwitchStatement: (node, opt2) => {
    return "switch (" + visit$2(node.discriminant, opt2) + ") {" + list$2(node.cases, opt2, "") + "}";
  },
  SwitchCase: (node, opt2) => {
    return (node.test ? "case " + visit$2(node.test, opt2) : "default") + ": " + list$2(node.consequent, opt2, ";") + ";";
  },
  ReturnStatement: (node, opt2) => {
    return "return " + visit$2(node.argument, opt2);
  },
  Program: (node, opt2) => visit$2(node.body[0], opt2)
};
function codegen(node, opt2 = { index: "row" }) {
  return visit$2(node, opt2);
}
function _compile(code, fn, params) {
  code = `"use strict"; return ${code};`;
  return Function("fn", "$", code)(fn, params);
}
const compile = {
  escape: (code, func2, params) => _compile(code, func2, params),
  expr: (code, params) => _compile(`(row,data,op)=>${code}`, functions, params),
  expr2: (code, params) => _compile(`(row0,data0,row,data)=>${code}`, functions, params),
  join: (code, params) => _compile(`(row1,data1,row2,data2)=>${code}`, functions, params),
  param: (code, params) => _compile(code, functions, params)
};
const dictOps = {
  "==": 1,
  "!=": 1,
  "===": 1,
  "!==": 1
};
function rewrite(ref2, name2, index = 0, col = void 0, op2 = void 0) {
  ref2.type = Column$1;
  ref2.name = name2;
  ref2.table = index;
  if (isArrayType(col)) {
    ref2.array = true;
  }
  if (op2 && col && isFunction(col.keyFor)) {
    const lit = dictOps[op2.operator] ? op2.left === ref2 ? op2.right : op2.left : op2.callee && op2.callee.name === "equal" ? op2.arguments[op2.arguments[0] === ref2 ? 1 : 0] : null;
    if (lit && lit.type === Literal) {
      rewriteDictionary(op2, ref2, lit, col.keyFor(lit.value));
    }
  }
  return ref2;
}
function rewriteDictionary(op2, ref2, lit, key2) {
  if (key2 < 0) {
    op2.type = Literal;
    op2.value = false;
    op2.raw = "false";
  } else {
    ref2.type = Dictionary2;
    lit.value = key2;
    lit.raw = key2 + "";
  }
  return true;
}
const ROW_OBJECT = "row_object";
function rowObjectExpression(node, table2, props = table2.columnNames()) {
  node.type = ObjectExpression;
  const p = node.properties = [];
  for (const prop of entries(props)) {
    const [name2, key2] = isArray$2(prop) ? prop : [prop, prop];
    p.push({
      type: Property,
      key: { type: Literal, raw: toString$1(key2) },
      value: rewrite({ computed: true }, name2, 0, table2.column(name2))
    });
  }
  return node;
}
function rowObjectCode(table2, props) {
  return codegen(rowObjectExpression({}, table2, props));
}
function rowObjectBuilder(table2, props) {
  return compile.expr(rowObjectCode(table2, props));
}
function toFunction(value2) {
  return isFunction(value2) ? value2 : () => value2;
}
const ERROR_ESC_AGGRONLY = "Escaped functions are not valid as rollup or pivot values.";
function parseEscape(ctx, spec, params) {
  if (ctx.aggronly) error(ERROR_ESC_AGGRONLY);
  const code = `(row,data)=>fn(${rowObjectCode(ctx.table)},$)`;
  return { escape: compile.escape(code, toFunction(spec.expr), params) };
}
var astralIdentifierCodes = [509, 0, 227, 0, 150, 4, 294, 9, 1368, 2, 2, 1, 6, 3, 41, 2, 5, 0, 166, 1, 574, 3, 9, 9, 7, 9, 32, 4, 318, 1, 80, 3, 71, 10, 50, 3, 123, 2, 54, 14, 32, 10, 3, 1, 11, 3, 46, 10, 8, 0, 46, 9, 7, 2, 37, 13, 2, 9, 6, 1, 45, 0, 13, 2, 49, 13, 9, 3, 2, 11, 83, 11, 7, 0, 3, 0, 158, 11, 6, 9, 7, 3, 56, 1, 2, 6, 3, 1, 3, 2, 10, 0, 11, 1, 3, 6, 4, 4, 68, 8, 2, 0, 3, 0, 2, 3, 2, 4, 2, 0, 15, 1, 83, 17, 10, 9, 5, 0, 82, 19, 13, 9, 214, 6, 3, 8, 28, 1, 83, 16, 16, 9, 82, 12, 9, 9, 7, 19, 58, 14, 5, 9, 243, 14, 166, 9, 71, 5, 2, 1, 3, 3, 2, 0, 2, 1, 13, 9, 120, 6, 3, 6, 4, 0, 29, 9, 41, 6, 2, 3, 9, 0, 10, 10, 47, 15, 343, 9, 54, 7, 2, 7, 17, 9, 57, 21, 2, 13, 123, 5, 4, 0, 2, 1, 2, 6, 2, 0, 9, 9, 49, 4, 2, 1, 2, 4, 9, 9, 330, 3, 10, 1, 2, 0, 49, 6, 4, 4, 14, 10, 5350, 0, 7, 14, 11465, 27, 2343, 9, 87, 9, 39, 4, 60, 6, 26, 9, 535, 9, 470, 0, 2, 54, 8, 3, 82, 0, 12, 1, 19628, 1, 4178, 9, 519, 45, 3, 22, 543, 4, 4, 5, 9, 7, 3, 6, 31, 3, 149, 2, 1418, 49, 513, 54, 5, 49, 9, 0, 15, 0, 23, 4, 2, 14, 1361, 6, 2, 16, 3, 6, 2, 1, 2, 4, 101, 0, 161, 6, 10, 9, 357, 0, 62, 13, 499, 13, 245, 1, 2, 9, 726, 6, 110, 6, 6, 9, 4759, 9, 787719, 239];
var astralIdentifierStartCodes = [0, 11, 2, 25, 2, 18, 2, 1, 2, 14, 3, 13, 35, 122, 70, 52, 268, 28, 4, 48, 48, 31, 14, 29, 6, 37, 11, 29, 3, 35, 5, 7, 2, 4, 43, 157, 19, 35, 5, 35, 5, 39, 9, 51, 13, 10, 2, 14, 2, 6, 2, 1, 2, 10, 2, 14, 2, 6, 2, 1, 4, 51, 13, 310, 10, 21, 11, 7, 25, 5, 2, 41, 2, 8, 70, 5, 3, 0, 2, 43, 2, 1, 4, 0, 3, 22, 11, 22, 10, 30, 66, 18, 2, 1, 11, 21, 11, 25, 71, 55, 7, 1, 65, 0, 16, 3, 2, 2, 2, 28, 43, 28, 4, 28, 36, 7, 2, 27, 28, 53, 11, 21, 11, 18, 14, 17, 111, 72, 56, 50, 14, 50, 14, 35, 39, 27, 10, 22, 251, 41, 7, 1, 17, 2, 60, 28, 11, 0, 9, 21, 43, 17, 47, 20, 28, 22, 13, 52, 58, 1, 3, 0, 14, 44, 33, 24, 27, 35, 30, 0, 3, 0, 9, 34, 4, 0, 13, 47, 15, 3, 22, 0, 2, 0, 36, 17, 2, 24, 20, 1, 64, 6, 2, 0, 2, 3, 2, 14, 2, 9, 8, 46, 39, 7, 3, 1, 3, 21, 2, 6, 2, 1, 2, 4, 4, 0, 19, 0, 13, 4, 31, 9, 2, 0, 3, 0, 2, 37, 2, 0, 26, 0, 2, 0, 45, 52, 19, 3, 21, 2, 31, 47, 21, 1, 2, 0, 185, 46, 42, 3, 37, 47, 21, 0, 60, 42, 14, 0, 72, 26, 38, 6, 186, 43, 117, 63, 32, 7, 3, 0, 3, 7, 2, 1, 2, 23, 16, 0, 2, 0, 95, 7, 3, 38, 17, 0, 2, 0, 29, 0, 11, 39, 8, 0, 22, 0, 12, 45, 20, 0, 19, 72, 200, 32, 32, 8, 2, 36, 18, 0, 50, 29, 113, 6, 2, 1, 2, 37, 22, 0, 26, 5, 2, 1, 2, 31, 15, 0, 328, 18, 16, 0, 2, 12, 2, 33, 125, 0, 80, 921, 103, 110, 18, 195, 2637, 96, 16, 1071, 18, 5, 26, 3994, 6, 582, 6842, 29, 1763, 568, 8, 30, 18, 78, 18, 29, 19, 47, 17, 3, 32, 20, 6, 18, 433, 44, 212, 63, 129, 74, 6, 0, 67, 12, 65, 1, 2, 0, 29, 6135, 9, 1237, 42, 9, 8936, 3, 2, 6, 2, 1, 2, 290, 16, 0, 30, 2, 3, 0, 15, 3, 9, 395, 2309, 106, 6, 12, 4, 8, 8, 9, 5991, 84, 2, 70, 2, 1, 3, 0, 3, 1, 3, 3, 2, 11, 2, 0, 2, 6, 2, 64, 2, 3, 3, 7, 2, 6, 2, 27, 2, 3, 2, 4, 2, 0, 4, 6, 2, 339, 3, 24, 2, 24, 2, 30, 2, 24, 2, 30, 2, 24, 2, 30, 2, 24, 2, 30, 2, 24, 2, 7, 1845, 30, 7, 5, 262, 61, 147, 44, 11, 6, 17, 0, 322, 29, 19, 43, 485, 27, 229, 29, 3, 0, 496, 6, 2, 3, 2, 1, 2, 14, 2, 196, 60, 67, 8, 0, 1205, 3, 2, 26, 2, 1, 2, 0, 3, 0, 2, 9, 2, 3, 2, 0, 2, 0, 7, 0, 5, 0, 2, 0, 2, 0, 2, 2, 2, 1, 2, 0, 3, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 1, 2, 0, 3, 3, 2, 6, 2, 3, 2, 3, 2, 0, 2, 9, 2, 16, 6, 2, 2, 4, 2, 16, 4421, 42719, 33, 4153, 7, 221, 3, 5761, 15, 7472, 16, 621, 2467, 541, 1507, 4938, 6, 4191];
var nonASCIIidentifierChars = "‌‍·̀-ͯ·҃-֑҇-ׇֽֿׁׂׅׄؐ-ًؚ-٩ٰۖ-ۜ۟-۪ۤۧۨ-ۭ۰-۹ܑܰ-݊ަ-ް߀-߉߫-߽߳ࠖ-࠙ࠛ-ࠣࠥ-ࠧࠩ-࡙࠭-࡛ࢗ-࢟࣊-ࣣ࣡-ःऺ-़ा-ॏ॑-ॗॢॣ०-९ঁ-ঃ়া-ৄেৈো-্ৗৢৣ০-৯৾ਁ-ਃ਼ਾ-ੂੇੈੋ-੍ੑ੦-ੱੵઁ-ઃ઼ા-ૅે-ૉો-્ૢૣ૦-૯ૺ-૿ଁ-ଃ଼ା-ୄେୈୋ-୍୕-ୗୢୣ୦-୯ஂா-ூெ-ைொ-்ௗ௦-௯ఀ-ఄ఼ా-ౄె-ైొ-్ౕౖౢౣ౦-౯ಁ-ಃ಼ಾ-ೄೆ-ೈೊ-್ೕೖೢೣ೦-೯ೳഀ-ഃ഻഼ാ-ൄെ-ൈൊ-്ൗൢൣ൦-൯ඁ-ඃ්ා-ුූෘ-ෟ෦-෯ෲෳัิ-ฺ็-๎๐-๙ັິ-ຼ່-໎໐-໙༘༙༠-༩༹༵༷༾༿ཱ-྄྆྇ྍ-ྗྙ-ྼ࿆ါ-ှ၀-၉ၖ-ၙၞ-ၠၢ-ၤၧ-ၭၱ-ၴႂ-ႍႏ-ႝ፝-፟፩-፱ᜒ-᜕ᜲ-᜴ᝒᝓᝲᝳ឴-៓៝០-៩᠋-᠍᠏-᠙ᢩᤠ-ᤫᤰ-᤻᥆-᥏᧐-᧚ᨗ-ᨛᩕ-ᩞ᩠-᩿᩼-᪉᪐-᪙᪰-᪽ᪿ-ᫎᬀ-ᬄ᬴-᭄᭐-᭙᭫-᭳ᮀ-ᮂᮡ-ᮭ᮰-᮹᯦-᯳ᰤ-᰷᱀-᱉᱐-᱙᳐-᳔᳒-᳨᳭᳴᳷-᳹᷀-᷿‌‍‿⁀⁔⃐-⃥⃜⃡-⃰⳯-⵿⳱ⷠ-〪ⷿ-゙゚〯・꘠-꘩꙯ꙴ-꙽ꚞꚟ꛰꛱ꠂ꠆ꠋꠣ-ꠧ꠬ꢀꢁꢴ-ꣅ꣐-꣙꣠-꣱ꣿ-꤉ꤦ-꤭ꥇ-꥓ꦀ-ꦃ꦳-꧀꧐-꧙ꧥ꧰-꧹ꨩ-ꨶꩃꩌꩍ꩐-꩙ꩻ-ꩽꪰꪲ-ꪴꪷꪸꪾ꪿꫁ꫫ-ꫯꫵ꫶ꯣ-ꯪ꯬꯭꯰-꯹ﬞ︀-️︠-︯︳︴﹍-﹏０-９＿･";
var nonASCIIidentifierStartChars = "ªµºÀ-ÖØ-öø-ˁˆ-ˑˠ-ˤˬˮͰ-ʹͶͷͺ-ͽͿΆΈ-ΊΌΎ-ΡΣ-ϵϷ-ҁҊ-ԯԱ-Ֆՙՠ-ֈא-תׯ-ײؠ-يٮٯٱ-ۓەۥۦۮۯۺ-ۼۿܐܒ-ܯݍ-ޥޱߊ-ߪߴߵߺࠀ-ࠕࠚࠤࠨࡀ-ࡘࡠ-ࡪࡰ-ࢇࢉ-ࢎࢠ-ࣉऄ-हऽॐक़-ॡॱ-ঀঅ-ঌএঐও-নপ-রলশ-হঽৎড়ঢ়য়-ৡৰৱৼਅ-ਊਏਐਓ-ਨਪ-ਰਲਲ਼ਵਸ਼ਸਹਖ਼-ੜਫ਼ੲ-ੴઅ-ઍએ-ઑઓ-નપ-રલળવ-હઽૐૠૡૹଅ-ଌଏଐଓ-ନପ-ରଲଳଵ-ହଽଡ଼ଢ଼ୟ-ୡୱஃஅ-ஊஎ-ஐஒ-கஙசஜஞடணதந-பம-ஹௐఅ-ఌఎ-ఐఒ-నప-హఽౘ-ౚౝౠౡಀಅ-ಌಎ-ಐಒ-ನಪ-ಳವ-ಹಽೝೞೠೡೱೲഄ-ഌഎ-ഐഒ-ഺഽൎൔ-ൖൟ-ൡൺ-ൿඅ-ඖක-නඳ-රලව-ෆก-ะาำเ-ๆກຂຄຆ-ຊຌ-ຣລວ-ະາຳຽເ-ໄໆໜ-ໟༀཀ-ཇཉ-ཬྈ-ྌက-ဪဿၐ-ၕၚ-ၝၡၥၦၮ-ၰၵ-ႁႎႠ-ჅჇჍა-ჺჼ-ቈቊ-ቍቐ-ቖቘቚ-ቝበ-ኈኊ-ኍነ-ኰኲ-ኵኸ-ኾዀዂ-ዅወ-ዖዘ-ጐጒ-ጕጘ-ፚᎀ-ᎏᎠ-Ᏽᏸ-ᏽᐁ-ᙬᙯ-ᙿᚁ-ᚚᚠ-ᛪᛮ-ᛸᜀ-ᜑᜟ-ᜱᝀ-ᝑᝠ-ᝬᝮ-ᝰក-ឳៗៜᠠ-ᡸᢀ-ᢨᢪᢰ-ᣵᤀ-ᤞᥐ-ᥭᥰ-ᥴᦀ-ᦫᦰ-ᧉᨀ-ᨖᨠ-ᩔᪧᬅ-ᬳᭅ-ᭌᮃ-ᮠᮮᮯᮺ-ᯥᰀ-ᰣᱍ-ᱏᱚ-ᱽᲀ-ᲊᲐ-ᲺᲽ-Ჿᳩ-ᳬᳮ-ᳳᳵᳶᳺᴀ-ᶿḀ-ἕἘ-Ἕἠ-ὅὈ-Ὅὐ-ὗὙὛὝὟ-ώᾀ-ᾴᾶ-ᾼιῂ-ῄῆ-ῌῐ-ΐῖ-Ίῠ-Ῥῲ-ῴῶ-ῼⁱⁿₐ-ₜℂℇℊ-ℓℕ℘-ℝℤΩℨK-ℹℼ-ℿⅅ-ⅉⅎⅠ-ↈⰀ-ⳤⳫ-ⳮⳲⳳⴀ-ⴥⴧⴭⴰ-ⵧⵯⶀ-ⶖⶠ-ⶦⶨ-ⶮⶰ-ⶶⶸ-ⶾⷀ-ⷆⷈ-ⷎⷐ-ⷖⷘ-ⷞ々-〇〡-〩〱-〵〸-〼ぁ-ゖ゛-ゟァ-ヺー-ヿㄅ-ㄯㄱ-ㆎㆠ-ㆿㇰ-ㇿ㐀-䶿一-ꒌꓐ-ꓽꔀ-ꘌꘐ-ꘟꘪꘫꙀ-ꙮꙿ-ꚝꚠ-ꛯꜗ-ꜟꜢ-ꞈꞋ-ꟍꟐꟑꟓꟕ-Ƛꟲ-ꠁꠃ-ꠅꠇ-ꠊꠌ-ꠢꡀ-ꡳꢂ-ꢳꣲ-ꣷꣻꣽꣾꤊ-ꤥꤰ-ꥆꥠ-ꥼꦄ-ꦲꧏꧠ-ꧤꧦ-ꧯꧺ-ꧾꨀ-ꨨꩀ-ꩂꩄ-ꩋꩠ-ꩶꩺꩾ-ꪯꪱꪵꪶꪹ-ꪽꫀꫂꫛ-ꫝꫠ-ꫪꫲ-ꫴꬁ-ꬆꬉ-ꬎꬑ-ꬖꬠ-ꬦꬨ-ꬮꬰ-ꭚꭜ-ꭩꭰ-ꯢ가-힣ힰ-ퟆퟋ-ퟻ豈-舘並-龎ﬀ-ﬆﬓ-ﬗיִײַ-ﬨשׁ-זּטּ-לּמּנּסּףּפּצּ-ﮱﯓ-ﴽﵐ-ﶏﶒ-ﷇﷰ-ﷻﹰ-ﹴﹶ-ﻼＡ-Ｚａ-ｚｦ-ﾾￂ-ￇￊ-ￏￒ-ￗￚ-ￜ";
var reservedWords = {
  3: "abstract boolean byte char class double enum export extends final float goto implements import int interface long native package private protected public short static super synchronized throws transient volatile",
  5: "class enum extends super const export import",
  6: "enum",
  strict: "implements interface let package private protected public static yield",
  strictBind: "eval arguments"
};
var ecma5AndLessKeywords = "break case catch continue debugger default do else finally for function if return switch throw try var while with null true false instanceof typeof void delete new in this";
var keywords$1 = {
  5: ecma5AndLessKeywords,
  "5module": ecma5AndLessKeywords + " export import",
  6: ecma5AndLessKeywords + " const class extends export import super"
};
var keywordRelationalOperator = /^in(stanceof)?$/;
var nonASCIIidentifierStart = new RegExp("[" + nonASCIIidentifierStartChars + "]");
var nonASCIIidentifier = new RegExp("[" + nonASCIIidentifierStartChars + nonASCIIidentifierChars + "]");
function isInAstralSet(code, set) {
  var pos = 65536;
  for (var i = 0; i < set.length; i += 2) {
    pos += set[i];
    if (pos > code) {
      return false;
    }
    pos += set[i + 1];
    if (pos >= code) {
      return true;
    }
  }
  return false;
}
function isIdentifierStart(code, astral) {
  if (code < 65) {
    return code === 36;
  }
  if (code < 91) {
    return true;
  }
  if (code < 97) {
    return code === 95;
  }
  if (code < 123) {
    return true;
  }
  if (code <= 65535) {
    return code >= 170 && nonASCIIidentifierStart.test(String.fromCharCode(code));
  }
  if (astral === false) {
    return false;
  }
  return isInAstralSet(code, astralIdentifierStartCodes);
}
function isIdentifierChar(code, astral) {
  if (code < 48) {
    return code === 36;
  }
  if (code < 58) {
    return true;
  }
  if (code < 65) {
    return false;
  }
  if (code < 91) {
    return true;
  }
  if (code < 97) {
    return code === 95;
  }
  if (code < 123) {
    return true;
  }
  if (code <= 65535) {
    return code >= 170 && nonASCIIidentifier.test(String.fromCharCode(code));
  }
  if (astral === false) {
    return false;
  }
  return isInAstralSet(code, astralIdentifierStartCodes) || isInAstralSet(code, astralIdentifierCodes);
}
var TokenType = function TokenType2(label, conf) {
  if (conf === void 0) conf = {};
  this.label = label;
  this.keyword = conf.keyword;
  this.beforeExpr = !!conf.beforeExpr;
  this.startsExpr = !!conf.startsExpr;
  this.isLoop = !!conf.isLoop;
  this.isAssign = !!conf.isAssign;
  this.prefix = !!conf.prefix;
  this.postfix = !!conf.postfix;
  this.binop = conf.binop || null;
  this.updateContext = null;
};
function binop(name2, prec) {
  return new TokenType(name2, { beforeExpr: true, binop: prec });
}
var beforeExpr = { beforeExpr: true }, startsExpr = { startsExpr: true };
var keywords = {};
function kw(name2, options) {
  if (options === void 0) options = {};
  options.keyword = name2;
  return keywords[name2] = new TokenType(name2, options);
}
var types$1 = {
  num: new TokenType("num", startsExpr),
  regexp: new TokenType("regexp", startsExpr),
  string: new TokenType("string", startsExpr),
  name: new TokenType("name", startsExpr),
  privateId: new TokenType("privateId", startsExpr),
  eof: new TokenType("eof"),
  // Punctuation token types.
  bracketL: new TokenType("[", { beforeExpr: true, startsExpr: true }),
  bracketR: new TokenType("]"),
  braceL: new TokenType("{", { beforeExpr: true, startsExpr: true }),
  braceR: new TokenType("}"),
  parenL: new TokenType("(", { beforeExpr: true, startsExpr: true }),
  parenR: new TokenType(")"),
  comma: new TokenType(",", beforeExpr),
  semi: new TokenType(";", beforeExpr),
  colon: new TokenType(":", beforeExpr),
  dot: new TokenType("."),
  question: new TokenType("?", beforeExpr),
  questionDot: new TokenType("?."),
  arrow: new TokenType("=>", beforeExpr),
  template: new TokenType("template"),
  invalidTemplate: new TokenType("invalidTemplate"),
  ellipsis: new TokenType("...", beforeExpr),
  backQuote: new TokenType("`", startsExpr),
  dollarBraceL: new TokenType("${", { beforeExpr: true, startsExpr: true }),
  // Operators. These carry several kinds of properties to help the
  // parser use them properly (the presence of these properties is
  // what categorizes them as operators).
  //
  // `binop`, when present, specifies that this operator is a binary
  // operator, and will refer to its precedence.
  //
  // `prefix` and `postfix` mark the operator as a prefix or postfix
  // unary operator.
  //
  // `isAssign` marks all of `=`, `+=`, `-=` etcetera, which act as
  // binary operators with a very low precedence, that should result
  // in AssignmentExpression nodes.
  eq: new TokenType("=", { beforeExpr: true, isAssign: true }),
  assign: new TokenType("_=", { beforeExpr: true, isAssign: true }),
  incDec: new TokenType("++/--", { prefix: true, postfix: true, startsExpr: true }),
  prefix: new TokenType("!/~", { beforeExpr: true, prefix: true, startsExpr: true }),
  logicalOR: binop("||", 1),
  logicalAND: binop("&&", 2),
  bitwiseOR: binop("|", 3),
  bitwiseXOR: binop("^", 4),
  bitwiseAND: binop("&", 5),
  equality: binop("==/!=/===/!==", 6),
  relational: binop("</>/<=/>=", 7),
  bitShift: binop("<</>>/>>>", 8),
  plusMin: new TokenType("+/-", { beforeExpr: true, binop: 9, prefix: true, startsExpr: true }),
  modulo: binop("%", 10),
  star: binop("*", 10),
  slash: binop("/", 10),
  starstar: new TokenType("**", { beforeExpr: true }),
  coalesce: binop("??", 1),
  // Keyword token types.
  _break: kw("break"),
  _case: kw("case", beforeExpr),
  _catch: kw("catch"),
  _continue: kw("continue"),
  _debugger: kw("debugger"),
  _default: kw("default", beforeExpr),
  _do: kw("do", { isLoop: true, beforeExpr: true }),
  _else: kw("else", beforeExpr),
  _finally: kw("finally"),
  _for: kw("for", { isLoop: true }),
  _function: kw("function", startsExpr),
  _if: kw("if"),
  _return: kw("return", beforeExpr),
  _switch: kw("switch"),
  _throw: kw("throw", beforeExpr),
  _try: kw("try"),
  _var: kw("var"),
  _const: kw("const"),
  _while: kw("while", { isLoop: true }),
  _with: kw("with"),
  _new: kw("new", { beforeExpr: true, startsExpr: true }),
  _this: kw("this", startsExpr),
  _super: kw("super", startsExpr),
  _class: kw("class", startsExpr),
  _extends: kw("extends", beforeExpr),
  _export: kw("export"),
  _import: kw("import", startsExpr),
  _null: kw("null", startsExpr),
  _true: kw("true", startsExpr),
  _false: kw("false", startsExpr),
  _in: kw("in", { beforeExpr: true, binop: 7 }),
  _instanceof: kw("instanceof", { beforeExpr: true, binop: 7 }),
  _typeof: kw("typeof", { beforeExpr: true, prefix: true, startsExpr: true }),
  _void: kw("void", { beforeExpr: true, prefix: true, startsExpr: true }),
  _delete: kw("delete", { beforeExpr: true, prefix: true, startsExpr: true })
};
var lineBreak = /\r\n?|\n|\u2028|\u2029/;
var lineBreakG = new RegExp(lineBreak.source, "g");
function isNewLine(code) {
  return code === 10 || code === 13 || code === 8232 || code === 8233;
}
function nextLineBreak(code, from2, end) {
  if (end === void 0) end = code.length;
  for (var i = from2; i < end; i++) {
    var next = code.charCodeAt(i);
    if (isNewLine(next)) {
      return i < end - 1 && next === 13 && code.charCodeAt(i + 1) === 10 ? i + 2 : i + 1;
    }
  }
  return -1;
}
var nonASCIIwhitespace = /[\u1680\u2000-\u200a\u202f\u205f\u3000\ufeff]/;
var skipWhiteSpace = /(?:\s|\/\/.*|\/\*[^]*?\*\/)*/g;
var ref = Object.prototype;
var hasOwnProperty = ref.hasOwnProperty;
var toString = ref.toString;
var hasOwn = Object.hasOwn || (function(obj, propName) {
  return hasOwnProperty.call(obj, propName);
});
var isArray$1 = Array.isArray || (function(obj) {
  return toString.call(obj) === "[object Array]";
});
var regexpCache = /* @__PURE__ */ Object.create(null);
function wordsRegexp(words) {
  return regexpCache[words] || (regexpCache[words] = new RegExp("^(?:" + words.replace(/ /g, "|") + ")$"));
}
function codePointToString(code) {
  if (code <= 65535) {
    return String.fromCharCode(code);
  }
  code -= 65536;
  return String.fromCharCode((code >> 10) + 55296, (code & 1023) + 56320);
}
var loneSurrogate = /(?:[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF])/;
var Position = function Position2(line, col) {
  this.line = line;
  this.column = col;
};
Position.prototype.offset = function offset(n) {
  return new Position(this.line, this.column + n);
};
var SourceLocation = function SourceLocation2(p, start, end) {
  this.start = start;
  this.end = end;
  if (p.sourceFile !== null) {
    this.source = p.sourceFile;
  }
};
function getLineInfo(input, offset2) {
  for (var line = 1, cur = 0; ; ) {
    var nextBreak = nextLineBreak(input, cur, offset2);
    if (nextBreak < 0) {
      return new Position(line, offset2 - cur);
    }
    ++line;
    cur = nextBreak;
  }
}
var defaultOptions = {
  // `ecmaVersion` indicates the ECMAScript version to parse. Must be
  // either 3, 5, 6 (or 2015), 7 (2016), 8 (2017), 9 (2018), 10
  // (2019), 11 (2020), 12 (2021), 13 (2022), 14 (2023), or `"latest"`
  // (the latest version the library supports). This influences
  // support for strict mode, the set of reserved words, and support
  // for new syntax features.
  ecmaVersion: null,
  // `sourceType` indicates the mode the code should be parsed in.
  // Can be either `"script"` or `"module"`. This influences global
  // strict mode and parsing of `import` and `export` declarations.
  sourceType: "script",
  // `onInsertedSemicolon` can be a callback that will be called when
  // a semicolon is automatically inserted. It will be passed the
  // position of the inserted semicolon as an offset, and if
  // `locations` is enabled, it is given the location as a `{line,
  // column}` object as second argument.
  onInsertedSemicolon: null,
  // `onTrailingComma` is similar to `onInsertedSemicolon`, but for
  // trailing commas.
  onTrailingComma: null,
  // By default, reserved words are only enforced if ecmaVersion >= 5.
  // Set `allowReserved` to a boolean value to explicitly turn this on
  // an off. When this option has the value "never", reserved words
  // and keywords can also not be used as property names.
  allowReserved: null,
  // When enabled, a return at the top level is not considered an
  // error.
  allowReturnOutsideFunction: false,
  // When enabled, import/export statements are not constrained to
  // appearing at the top of the program, and an import.meta expression
  // in a script isn't considered an error.
  allowImportExportEverywhere: false,
  // By default, await identifiers are allowed to appear at the top-level scope only if ecmaVersion >= 2022.
  // When enabled, await identifiers are allowed to appear at the top-level scope,
  // but they are still not allowed in non-async functions.
  allowAwaitOutsideFunction: null,
  // When enabled, super identifiers are not constrained to
  // appearing in methods and do not raise an error when they appear elsewhere.
  allowSuperOutsideMethod: null,
  // When enabled, hashbang directive in the beginning of file is
  // allowed and treated as a line comment. Enabled by default when
  // `ecmaVersion` >= 2023.
  allowHashBang: false,
  // By default, the parser will verify that private properties are
  // only used in places where they are valid and have been declared.
  // Set this to false to turn such checks off.
  checkPrivateFields: true,
  // When `locations` is on, `loc` properties holding objects with
  // `start` and `end` properties in `{line, column}` form (with
  // line being 1-based and column 0-based) will be attached to the
  // nodes.
  locations: false,
  // A function can be passed as `onToken` option, which will
  // cause Acorn to call that function with object in the same
  // format as tokens returned from `tokenizer().getToken()`. Note
  // that you are not allowed to call the parser from the
  // callback—that will corrupt its internal state.
  onToken: null,
  // A function can be passed as `onComment` option, which will
  // cause Acorn to call that function with `(block, text, start,
  // end)` parameters whenever a comment is skipped. `block` is a
  // boolean indicating whether this is a block (`/* */`) comment,
  // `text` is the content of the comment, and `start` and `end` are
  // character offsets that denote the start and end of the comment.
  // When the `locations` option is on, two more parameters are
  // passed, the full `{line, column}` locations of the start and
  // end of the comments. Note that you are not allowed to call the
  // parser from the callback—that will corrupt its internal state.
  // When this option has an array as value, objects representing the
  // comments are pushed to it.
  onComment: null,
  // Nodes have their start and end characters offsets recorded in
  // `start` and `end` properties (directly on the node, rather than
  // the `loc` object, which holds line/column data. To also add a
  // [semi-standardized][range] `range` property holding a `[start,
  // end]` array with the same numbers, set the `ranges` option to
  // `true`.
  //
  // [range]: https://bugzilla.mozilla.org/show_bug.cgi?id=745678
  ranges: false,
  // It is possible to parse multiple files into a single AST by
  // passing the tree produced by parsing the first file as
  // `program` option in subsequent parses. This will add the
  // toplevel forms of the parsed file to the `Program` (top) node
  // of an existing parse tree.
  program: null,
  // When `locations` is on, you can pass this to record the source
  // file in every node's `loc` object.
  sourceFile: null,
  // This value, if given, is stored in every node, whether
  // `locations` is on or off.
  directSourceFile: null,
  // When enabled, parenthesized expressions are represented by
  // (non-standard) ParenthesizedExpression nodes
  preserveParens: false
};
var warnedAboutEcmaVersion = false;
function getOptions(opts) {
  var options = {};
  for (var opt2 in defaultOptions) {
    options[opt2] = opts && hasOwn(opts, opt2) ? opts[opt2] : defaultOptions[opt2];
  }
  if (options.ecmaVersion === "latest") {
    options.ecmaVersion = 1e8;
  } else if (options.ecmaVersion == null) {
    if (!warnedAboutEcmaVersion && typeof console === "object" && console.warn) {
      warnedAboutEcmaVersion = true;
      console.warn("Since Acorn 8.0.0, options.ecmaVersion is required.\nDefaulting to 2020, but this will stop working in the future.");
    }
    options.ecmaVersion = 11;
  } else if (options.ecmaVersion >= 2015) {
    options.ecmaVersion -= 2009;
  }
  if (options.allowReserved == null) {
    options.allowReserved = options.ecmaVersion < 5;
  }
  if (!opts || opts.allowHashBang == null) {
    options.allowHashBang = options.ecmaVersion >= 14;
  }
  if (isArray$1(options.onToken)) {
    var tokens = options.onToken;
    options.onToken = function(token) {
      return tokens.push(token);
    };
  }
  if (isArray$1(options.onComment)) {
    options.onComment = pushComment(options, options.onComment);
  }
  return options;
}
function pushComment(options, array2) {
  return function(block, text, start, end, startLoc, endLoc) {
    var comment = {
      type: block ? "Block" : "Line",
      value: text,
      start,
      end
    };
    if (options.locations) {
      comment.loc = new SourceLocation(this, startLoc, endLoc);
    }
    if (options.ranges) {
      comment.range = [start, end];
    }
    array2.push(comment);
  };
}
var SCOPE_TOP = 1, SCOPE_FUNCTION = 2, SCOPE_ASYNC = 4, SCOPE_GENERATOR = 8, SCOPE_ARROW = 16, SCOPE_SIMPLE_CATCH = 32, SCOPE_SUPER = 64, SCOPE_DIRECT_SUPER = 128, SCOPE_CLASS_STATIC_BLOCK = 256, SCOPE_CLASS_FIELD_INIT = 512, SCOPE_VAR = SCOPE_TOP | SCOPE_FUNCTION | SCOPE_CLASS_STATIC_BLOCK;
function functionFlags(async, generator) {
  return SCOPE_FUNCTION | (async ? SCOPE_ASYNC : 0) | (generator ? SCOPE_GENERATOR : 0);
}
var BIND_NONE = 0, BIND_VAR = 1, BIND_LEXICAL = 2, BIND_FUNCTION = 3, BIND_SIMPLE_CATCH = 4, BIND_OUTSIDE = 5;
var Parser = function Parser2(options, input, startPos) {
  this.options = options = getOptions(options);
  this.sourceFile = options.sourceFile;
  this.keywords = wordsRegexp(keywords$1[options.ecmaVersion >= 6 ? 6 : options.sourceType === "module" ? "5module" : 5]);
  var reserved = "";
  if (options.allowReserved !== true) {
    reserved = reservedWords[options.ecmaVersion >= 6 ? 6 : options.ecmaVersion === 5 ? 5 : 3];
    if (options.sourceType === "module") {
      reserved += " await";
    }
  }
  this.reservedWords = wordsRegexp(reserved);
  var reservedStrict = (reserved ? reserved + " " : "") + reservedWords.strict;
  this.reservedWordsStrict = wordsRegexp(reservedStrict);
  this.reservedWordsStrictBind = wordsRegexp(reservedStrict + " " + reservedWords.strictBind);
  this.input = String(input);
  this.containsEsc = false;
  if (startPos) {
    this.pos = startPos;
    this.lineStart = this.input.lastIndexOf("\n", startPos - 1) + 1;
    this.curLine = this.input.slice(0, this.lineStart).split(lineBreak).length;
  } else {
    this.pos = this.lineStart = 0;
    this.curLine = 1;
  }
  this.type = types$1.eof;
  this.value = null;
  this.start = this.end = this.pos;
  this.startLoc = this.endLoc = this.curPosition();
  this.lastTokEndLoc = this.lastTokStartLoc = null;
  this.lastTokStart = this.lastTokEnd = this.pos;
  this.context = this.initialContext();
  this.exprAllowed = true;
  this.inModule = options.sourceType === "module";
  this.strict = this.inModule || this.strictDirective(this.pos);
  this.potentialArrowAt = -1;
  this.potentialArrowInForAwait = false;
  this.yieldPos = this.awaitPos = this.awaitIdentPos = 0;
  this.labels = [];
  this.undefinedExports = /* @__PURE__ */ Object.create(null);
  if (this.pos === 0 && options.allowHashBang && this.input.slice(0, 2) === "#!") {
    this.skipLineComment(2);
  }
  this.scopeStack = [];
  this.enterScope(SCOPE_TOP);
  this.regexpState = null;
  this.privateNameStack = [];
};
var prototypeAccessors = { inFunction: { configurable: true }, inGenerator: { configurable: true }, inAsync: { configurable: true }, canAwait: { configurable: true }, allowSuper: { configurable: true }, allowDirectSuper: { configurable: true }, treatFunctionsAsVar: { configurable: true }, allowNewDotTarget: { configurable: true }, inClassStaticBlock: { configurable: true } };
Parser.prototype.parse = function parse() {
  var node = this.options.program || this.startNode();
  this.nextToken();
  return this.parseTopLevel(node);
};
prototypeAccessors.inFunction.get = function() {
  return (this.currentVarScope().flags & SCOPE_FUNCTION) > 0;
};
prototypeAccessors.inGenerator.get = function() {
  return (this.currentVarScope().flags & SCOPE_GENERATOR) > 0;
};
prototypeAccessors.inAsync.get = function() {
  return (this.currentVarScope().flags & SCOPE_ASYNC) > 0;
};
prototypeAccessors.canAwait.get = function() {
  for (var i = this.scopeStack.length - 1; i >= 0; i--) {
    var ref2 = this.scopeStack[i];
    var flags = ref2.flags;
    if (flags & (SCOPE_CLASS_STATIC_BLOCK | SCOPE_CLASS_FIELD_INIT)) {
      return false;
    }
    if (flags & SCOPE_FUNCTION) {
      return (flags & SCOPE_ASYNC) > 0;
    }
  }
  return this.inModule && this.options.ecmaVersion >= 13 || this.options.allowAwaitOutsideFunction;
};
prototypeAccessors.allowSuper.get = function() {
  var ref2 = this.currentThisScope();
  var flags = ref2.flags;
  return (flags & SCOPE_SUPER) > 0 || this.options.allowSuperOutsideMethod;
};
prototypeAccessors.allowDirectSuper.get = function() {
  return (this.currentThisScope().flags & SCOPE_DIRECT_SUPER) > 0;
};
prototypeAccessors.treatFunctionsAsVar.get = function() {
  return this.treatFunctionsAsVarInScope(this.currentScope());
};
prototypeAccessors.allowNewDotTarget.get = function() {
  for (var i = this.scopeStack.length - 1; i >= 0; i--) {
    var ref2 = this.scopeStack[i];
    var flags = ref2.flags;
    if (flags & (SCOPE_CLASS_STATIC_BLOCK | SCOPE_CLASS_FIELD_INIT) || flags & SCOPE_FUNCTION && !(flags & SCOPE_ARROW)) {
      return true;
    }
  }
  return false;
};
prototypeAccessors.inClassStaticBlock.get = function() {
  return (this.currentVarScope().flags & SCOPE_CLASS_STATIC_BLOCK) > 0;
};
Parser.extend = function extend() {
  var plugins = [], len = arguments.length;
  while (len--) plugins[len] = arguments[len];
  var cls = this;
  for (var i = 0; i < plugins.length; i++) {
    cls = plugins[i](cls);
  }
  return cls;
};
Parser.parse = function parse2(input, options) {
  return new this(options, input).parse();
};
Parser.parseExpressionAt = function parseExpressionAt(input, pos, options) {
  var parser = new this(options, input, pos);
  parser.nextToken();
  return parser.parseExpression();
};
Parser.tokenizer = function tokenizer(input, options) {
  return new this(options, input);
};
Object.defineProperties(Parser.prototype, prototypeAccessors);
var pp$9 = Parser.prototype;
var literal = /^(?:'((?:\\[^]|[^'\\])*?)'|"((?:\\[^]|[^"\\])*?)")/;
pp$9.strictDirective = function(start) {
  if (this.options.ecmaVersion < 5) {
    return false;
  }
  for (; ; ) {
    skipWhiteSpace.lastIndex = start;
    start += skipWhiteSpace.exec(this.input)[0].length;
    var match2 = literal.exec(this.input.slice(start));
    if (!match2) {
      return false;
    }
    if ((match2[1] || match2[2]) === "use strict") {
      skipWhiteSpace.lastIndex = start + match2[0].length;
      var spaceAfter = skipWhiteSpace.exec(this.input), end = spaceAfter.index + spaceAfter[0].length;
      var next = this.input.charAt(end);
      return next === ";" || next === "}" || lineBreak.test(spaceAfter[0]) && !(/[(`.[+\-/*%<>=,?^&]/.test(next) || next === "!" && this.input.charAt(end + 1) === "=");
    }
    start += match2[0].length;
    skipWhiteSpace.lastIndex = start;
    start += skipWhiteSpace.exec(this.input)[0].length;
    if (this.input[start] === ";") {
      start++;
    }
  }
};
pp$9.eat = function(type) {
  if (this.type === type) {
    this.next();
    return true;
  } else {
    return false;
  }
};
pp$9.isContextual = function(name2) {
  return this.type === types$1.name && this.value === name2 && !this.containsEsc;
};
pp$9.eatContextual = function(name2) {
  if (!this.isContextual(name2)) {
    return false;
  }
  this.next();
  return true;
};
pp$9.expectContextual = function(name2) {
  if (!this.eatContextual(name2)) {
    this.unexpected();
  }
};
pp$9.canInsertSemicolon = function() {
  return this.type === types$1.eof || this.type === types$1.braceR || lineBreak.test(this.input.slice(this.lastTokEnd, this.start));
};
pp$9.insertSemicolon = function() {
  if (this.canInsertSemicolon()) {
    if (this.options.onInsertedSemicolon) {
      this.options.onInsertedSemicolon(this.lastTokEnd, this.lastTokEndLoc);
    }
    return true;
  }
};
pp$9.semicolon = function() {
  if (!this.eat(types$1.semi) && !this.insertSemicolon()) {
    this.unexpected();
  }
};
pp$9.afterTrailingComma = function(tokType, notNext) {
  if (this.type === tokType) {
    if (this.options.onTrailingComma) {
      this.options.onTrailingComma(this.lastTokStart, this.lastTokStartLoc);
    }
    if (!notNext) {
      this.next();
    }
    return true;
  }
};
pp$9.expect = function(type) {
  this.eat(type) || this.unexpected();
};
pp$9.unexpected = function(pos) {
  this.raise(pos != null ? pos : this.start, "Unexpected token");
};
var DestructuringErrors = function DestructuringErrors2() {
  this.shorthandAssign = this.trailingComma = this.parenthesizedAssign = this.parenthesizedBind = this.doubleProto = -1;
};
pp$9.checkPatternErrors = function(refDestructuringErrors, isAssign) {
  if (!refDestructuringErrors) {
    return;
  }
  if (refDestructuringErrors.trailingComma > -1) {
    this.raiseRecoverable(refDestructuringErrors.trailingComma, "Comma is not permitted after the rest element");
  }
  var parens = isAssign ? refDestructuringErrors.parenthesizedAssign : refDestructuringErrors.parenthesizedBind;
  if (parens > -1) {
    this.raiseRecoverable(parens, isAssign ? "Assigning to rvalue" : "Parenthesized pattern");
  }
};
pp$9.checkExpressionErrors = function(refDestructuringErrors, andThrow) {
  if (!refDestructuringErrors) {
    return false;
  }
  var shorthandAssign = refDestructuringErrors.shorthandAssign;
  var doubleProto = refDestructuringErrors.doubleProto;
  if (!andThrow) {
    return shorthandAssign >= 0 || doubleProto >= 0;
  }
  if (shorthandAssign >= 0) {
    this.raise(shorthandAssign, "Shorthand property assignments are valid only in destructuring patterns");
  }
  if (doubleProto >= 0) {
    this.raiseRecoverable(doubleProto, "Redefinition of __proto__ property");
  }
};
pp$9.checkYieldAwaitInDefaultParams = function() {
  if (this.yieldPos && (!this.awaitPos || this.yieldPos < this.awaitPos)) {
    this.raise(this.yieldPos, "Yield expression cannot be a default value");
  }
  if (this.awaitPos) {
    this.raise(this.awaitPos, "Await expression cannot be a default value");
  }
};
pp$9.isSimpleAssignTarget = function(expr) {
  if (expr.type === "ParenthesizedExpression") {
    return this.isSimpleAssignTarget(expr.expression);
  }
  return expr.type === "Identifier" || expr.type === "MemberExpression";
};
var pp$8 = Parser.prototype;
pp$8.parseTopLevel = function(node) {
  var exports = /* @__PURE__ */ Object.create(null);
  if (!node.body) {
    node.body = [];
  }
  while (this.type !== types$1.eof) {
    var stmt = this.parseStatement(null, true, exports);
    node.body.push(stmt);
  }
  if (this.inModule) {
    for (var i = 0, list2 = Object.keys(this.undefinedExports); i < list2.length; i += 1) {
      var name2 = list2[i];
      this.raiseRecoverable(this.undefinedExports[name2].start, "Export '" + name2 + "' is not defined");
    }
  }
  this.adaptDirectivePrologue(node.body);
  this.next();
  node.sourceType = this.options.sourceType;
  return this.finishNode(node, "Program");
};
var loopLabel = { kind: "loop" }, switchLabel = { kind: "switch" };
pp$8.isLet = function(context) {
  if (this.options.ecmaVersion < 6 || !this.isContextual("let")) {
    return false;
  }
  skipWhiteSpace.lastIndex = this.pos;
  var skip = skipWhiteSpace.exec(this.input);
  var next = this.pos + skip[0].length, nextCh = this.input.charCodeAt(next);
  if (nextCh === 91 || nextCh === 92) {
    return true;
  }
  if (context) {
    return false;
  }
  if (nextCh === 123 || nextCh > 55295 && nextCh < 56320) {
    return true;
  }
  if (isIdentifierStart(nextCh, true)) {
    var pos = next + 1;
    while (isIdentifierChar(nextCh = this.input.charCodeAt(pos), true)) {
      ++pos;
    }
    if (nextCh === 92 || nextCh > 55295 && nextCh < 56320) {
      return true;
    }
    var ident = this.input.slice(next, pos);
    if (!keywordRelationalOperator.test(ident)) {
      return true;
    }
  }
  return false;
};
pp$8.isAsyncFunction = function() {
  if (this.options.ecmaVersion < 8 || !this.isContextual("async")) {
    return false;
  }
  skipWhiteSpace.lastIndex = this.pos;
  var skip = skipWhiteSpace.exec(this.input);
  var next = this.pos + skip[0].length, after;
  return !lineBreak.test(this.input.slice(this.pos, next)) && this.input.slice(next, next + 8) === "function" && (next + 8 === this.input.length || !(isIdentifierChar(after = this.input.charCodeAt(next + 8)) || after > 55295 && after < 56320));
};
pp$8.isUsingKeyword = function(isAwaitUsing, isFor) {
  if (this.options.ecmaVersion < 17 || !this.isContextual(isAwaitUsing ? "await" : "using")) {
    return false;
  }
  skipWhiteSpace.lastIndex = this.pos;
  var skip = skipWhiteSpace.exec(this.input);
  var next = this.pos + skip[0].length;
  if (lineBreak.test(this.input.slice(this.pos, next))) {
    return false;
  }
  if (isAwaitUsing) {
    var awaitEndPos = next + 5, after;
    if (this.input.slice(next, awaitEndPos) !== "using" || awaitEndPos === this.input.length || isIdentifierChar(after = this.input.charCodeAt(awaitEndPos)) || after > 55295 && after < 56320) {
      return false;
    }
    skipWhiteSpace.lastIndex = awaitEndPos;
    var skipAfterUsing = skipWhiteSpace.exec(this.input);
    if (skipAfterUsing && lineBreak.test(this.input.slice(awaitEndPos, awaitEndPos + skipAfterUsing[0].length))) {
      return false;
    }
  }
  if (isFor) {
    var ofEndPos = next + 2, after$1;
    if (this.input.slice(next, ofEndPos) === "of") {
      if (ofEndPos === this.input.length || !isIdentifierChar(after$1 = this.input.charCodeAt(ofEndPos)) && !(after$1 > 55295 && after$1 < 56320)) {
        return false;
      }
    }
  }
  var ch = this.input.charCodeAt(next);
  return isIdentifierStart(ch, true) || ch === 92;
};
pp$8.isAwaitUsing = function(isFor) {
  return this.isUsingKeyword(true, isFor);
};
pp$8.isUsing = function(isFor) {
  return this.isUsingKeyword(false, isFor);
};
pp$8.parseStatement = function(context, topLevel, exports) {
  var starttype = this.type, node = this.startNode(), kind;
  if (this.isLet(context)) {
    starttype = types$1._var;
    kind = "let";
  }
  switch (starttype) {
    case types$1._break:
    case types$1._continue:
      return this.parseBreakContinueStatement(node, starttype.keyword);
    case types$1._debugger:
      return this.parseDebuggerStatement(node);
    case types$1._do:
      return this.parseDoStatement(node);
    case types$1._for:
      return this.parseForStatement(node);
    case types$1._function:
      if (context && (this.strict || context !== "if" && context !== "label") && this.options.ecmaVersion >= 6) {
        this.unexpected();
      }
      return this.parseFunctionStatement(node, false, !context);
    case types$1._class:
      if (context) {
        this.unexpected();
      }
      return this.parseClass(node, true);
    case types$1._if:
      return this.parseIfStatement(node);
    case types$1._return:
      return this.parseReturnStatement(node);
    case types$1._switch:
      return this.parseSwitchStatement(node);
    case types$1._throw:
      return this.parseThrowStatement(node);
    case types$1._try:
      return this.parseTryStatement(node);
    case types$1._const:
    case types$1._var:
      kind = kind || this.value;
      if (context && kind !== "var") {
        this.unexpected();
      }
      return this.parseVarStatement(node, kind);
    case types$1._while:
      return this.parseWhileStatement(node);
    case types$1._with:
      return this.parseWithStatement(node);
    case types$1.braceL:
      return this.parseBlock(true, node);
    case types$1.semi:
      return this.parseEmptyStatement(node);
    case types$1._export:
    case types$1._import:
      if (this.options.ecmaVersion > 10 && starttype === types$1._import) {
        skipWhiteSpace.lastIndex = this.pos;
        var skip = skipWhiteSpace.exec(this.input);
        var next = this.pos + skip[0].length, nextCh = this.input.charCodeAt(next);
        if (nextCh === 40 || nextCh === 46) {
          return this.parseExpressionStatement(node, this.parseExpression());
        }
      }
      if (!this.options.allowImportExportEverywhere) {
        if (!topLevel) {
          this.raise(this.start, "'import' and 'export' may only appear at the top level");
        }
        if (!this.inModule) {
          this.raise(this.start, "'import' and 'export' may appear only with 'sourceType: module'");
        }
      }
      return starttype === types$1._import ? this.parseImport(node) : this.parseExport(node, exports);
    // If the statement does not start with a statement keyword or a
    // brace, it's an ExpressionStatement or LabeledStatement. We
    // simply start parsing an expression, and afterwards, if the
    // next token is a colon and the expression was a simple
    // Identifier node, we switch to interpreting it as a label.
    default:
      if (this.isAsyncFunction()) {
        if (context) {
          this.unexpected();
        }
        this.next();
        return this.parseFunctionStatement(node, true, !context);
      }
      var usingKind = this.isAwaitUsing(false) ? "await using" : this.isUsing(false) ? "using" : null;
      if (usingKind) {
        if (topLevel && this.options.sourceType === "script") {
          this.raise(this.start, "Using declaration cannot appear in the top level when source type is `script`");
        }
        if (usingKind === "await using") {
          if (!this.canAwait) {
            this.raise(this.start, "Await using cannot appear outside of async function");
          }
          this.next();
        }
        this.next();
        this.parseVar(node, false, usingKind);
        this.semicolon();
        return this.finishNode(node, "VariableDeclaration");
      }
      var maybeName = this.value, expr = this.parseExpression();
      if (starttype === types$1.name && expr.type === "Identifier" && this.eat(types$1.colon)) {
        return this.parseLabeledStatement(node, maybeName, expr, context);
      } else {
        return this.parseExpressionStatement(node, expr);
      }
  }
};
pp$8.parseBreakContinueStatement = function(node, keyword) {
  var isBreak = keyword === "break";
  this.next();
  if (this.eat(types$1.semi) || this.insertSemicolon()) {
    node.label = null;
  } else if (this.type !== types$1.name) {
    this.unexpected();
  } else {
    node.label = this.parseIdent();
    this.semicolon();
  }
  var i = 0;
  for (; i < this.labels.length; ++i) {
    var lab = this.labels[i];
    if (node.label == null || lab.name === node.label.name) {
      if (lab.kind != null && (isBreak || lab.kind === "loop")) {
        break;
      }
      if (node.label && isBreak) {
        break;
      }
    }
  }
  if (i === this.labels.length) {
    this.raise(node.start, "Unsyntactic " + keyword);
  }
  return this.finishNode(node, isBreak ? "BreakStatement" : "ContinueStatement");
};
pp$8.parseDebuggerStatement = function(node) {
  this.next();
  this.semicolon();
  return this.finishNode(node, "DebuggerStatement");
};
pp$8.parseDoStatement = function(node) {
  this.next();
  this.labels.push(loopLabel);
  node.body = this.parseStatement("do");
  this.labels.pop();
  this.expect(types$1._while);
  node.test = this.parseParenExpression();
  if (this.options.ecmaVersion >= 6) {
    this.eat(types$1.semi);
  } else {
    this.semicolon();
  }
  return this.finishNode(node, "DoWhileStatement");
};
pp$8.parseForStatement = function(node) {
  this.next();
  var awaitAt = this.options.ecmaVersion >= 9 && this.canAwait && this.eatContextual("await") ? this.lastTokStart : -1;
  this.labels.push(loopLabel);
  this.enterScope(0);
  this.expect(types$1.parenL);
  if (this.type === types$1.semi) {
    if (awaitAt > -1) {
      this.unexpected(awaitAt);
    }
    return this.parseFor(node, null);
  }
  var isLet = this.isLet();
  if (this.type === types$1._var || this.type === types$1._const || isLet) {
    var init$1 = this.startNode(), kind = isLet ? "let" : this.value;
    this.next();
    this.parseVar(init$1, true, kind);
    this.finishNode(init$1, "VariableDeclaration");
    return this.parseForAfterInit(node, init$1, awaitAt);
  }
  var startsWithLet = this.isContextual("let"), isForOf = false;
  var usingKind = this.isUsing(true) ? "using" : this.isAwaitUsing(true) ? "await using" : null;
  if (usingKind) {
    var init$2 = this.startNode();
    this.next();
    if (usingKind === "await using") {
      this.next();
    }
    this.parseVar(init$2, true, usingKind);
    this.finishNode(init$2, "VariableDeclaration");
    return this.parseForAfterInit(node, init$2, awaitAt);
  }
  var containsEsc = this.containsEsc;
  var refDestructuringErrors = new DestructuringErrors();
  var initPos = this.start;
  var init = awaitAt > -1 ? this.parseExprSubscripts(refDestructuringErrors, "await") : this.parseExpression(true, refDestructuringErrors);
  if (this.type === types$1._in || (isForOf = this.options.ecmaVersion >= 6 && this.isContextual("of"))) {
    if (awaitAt > -1) {
      if (this.type === types$1._in) {
        this.unexpected(awaitAt);
      }
      node.await = true;
    } else if (isForOf && this.options.ecmaVersion >= 8) {
      if (init.start === initPos && !containsEsc && init.type === "Identifier" && init.name === "async") {
        this.unexpected();
      } else if (this.options.ecmaVersion >= 9) {
        node.await = false;
      }
    }
    if (startsWithLet && isForOf) {
      this.raise(init.start, "The left-hand side of a for-of loop may not start with 'let'.");
    }
    this.toAssignable(init, false, refDestructuringErrors);
    this.checkLValPattern(init);
    return this.parseForIn(node, init);
  } else {
    this.checkExpressionErrors(refDestructuringErrors, true);
  }
  if (awaitAt > -1) {
    this.unexpected(awaitAt);
  }
  return this.parseFor(node, init);
};
pp$8.parseForAfterInit = function(node, init, awaitAt) {
  if ((this.type === types$1._in || this.options.ecmaVersion >= 6 && this.isContextual("of")) && init.declarations.length === 1) {
    if (this.options.ecmaVersion >= 9) {
      if (this.type === types$1._in) {
        if (awaitAt > -1) {
          this.unexpected(awaitAt);
        }
      } else {
        node.await = awaitAt > -1;
      }
    }
    return this.parseForIn(node, init);
  }
  if (awaitAt > -1) {
    this.unexpected(awaitAt);
  }
  return this.parseFor(node, init);
};
pp$8.parseFunctionStatement = function(node, isAsync, declarationPosition) {
  this.next();
  return this.parseFunction(node, FUNC_STATEMENT | (declarationPosition ? 0 : FUNC_HANGING_STATEMENT), false, isAsync);
};
pp$8.parseIfStatement = function(node) {
  this.next();
  node.test = this.parseParenExpression();
  node.consequent = this.parseStatement("if");
  node.alternate = this.eat(types$1._else) ? this.parseStatement("if") : null;
  return this.finishNode(node, "IfStatement");
};
pp$8.parseReturnStatement = function(node) {
  if (!this.inFunction && !this.options.allowReturnOutsideFunction) {
    this.raise(this.start, "'return' outside of function");
  }
  this.next();
  if (this.eat(types$1.semi) || this.insertSemicolon()) {
    node.argument = null;
  } else {
    node.argument = this.parseExpression();
    this.semicolon();
  }
  return this.finishNode(node, "ReturnStatement");
};
pp$8.parseSwitchStatement = function(node) {
  this.next();
  node.discriminant = this.parseParenExpression();
  node.cases = [];
  this.expect(types$1.braceL);
  this.labels.push(switchLabel);
  this.enterScope(0);
  var cur;
  for (var sawDefault = false; this.type !== types$1.braceR; ) {
    if (this.type === types$1._case || this.type === types$1._default) {
      var isCase = this.type === types$1._case;
      if (cur) {
        this.finishNode(cur, "SwitchCase");
      }
      node.cases.push(cur = this.startNode());
      cur.consequent = [];
      this.next();
      if (isCase) {
        cur.test = this.parseExpression();
      } else {
        if (sawDefault) {
          this.raiseRecoverable(this.lastTokStart, "Multiple default clauses");
        }
        sawDefault = true;
        cur.test = null;
      }
      this.expect(types$1.colon);
    } else {
      if (!cur) {
        this.unexpected();
      }
      cur.consequent.push(this.parseStatement(null));
    }
  }
  this.exitScope();
  if (cur) {
    this.finishNode(cur, "SwitchCase");
  }
  this.next();
  this.labels.pop();
  return this.finishNode(node, "SwitchStatement");
};
pp$8.parseThrowStatement = function(node) {
  this.next();
  if (lineBreak.test(this.input.slice(this.lastTokEnd, this.start))) {
    this.raise(this.lastTokEnd, "Illegal newline after throw");
  }
  node.argument = this.parseExpression();
  this.semicolon();
  return this.finishNode(node, "ThrowStatement");
};
var empty$1 = [];
pp$8.parseCatchClauseParam = function() {
  var param = this.parseBindingAtom();
  var simple = param.type === "Identifier";
  this.enterScope(simple ? SCOPE_SIMPLE_CATCH : 0);
  this.checkLValPattern(param, simple ? BIND_SIMPLE_CATCH : BIND_LEXICAL);
  this.expect(types$1.parenR);
  return param;
};
pp$8.parseTryStatement = function(node) {
  this.next();
  node.block = this.parseBlock();
  node.handler = null;
  if (this.type === types$1._catch) {
    var clause = this.startNode();
    this.next();
    if (this.eat(types$1.parenL)) {
      clause.param = this.parseCatchClauseParam();
    } else {
      if (this.options.ecmaVersion < 10) {
        this.unexpected();
      }
      clause.param = null;
      this.enterScope(0);
    }
    clause.body = this.parseBlock(false);
    this.exitScope();
    node.handler = this.finishNode(clause, "CatchClause");
  }
  node.finalizer = this.eat(types$1._finally) ? this.parseBlock() : null;
  if (!node.handler && !node.finalizer) {
    this.raise(node.start, "Missing catch or finally clause");
  }
  return this.finishNode(node, "TryStatement");
};
pp$8.parseVarStatement = function(node, kind, allowMissingInitializer) {
  this.next();
  this.parseVar(node, false, kind, allowMissingInitializer);
  this.semicolon();
  return this.finishNode(node, "VariableDeclaration");
};
pp$8.parseWhileStatement = function(node) {
  this.next();
  node.test = this.parseParenExpression();
  this.labels.push(loopLabel);
  node.body = this.parseStatement("while");
  this.labels.pop();
  return this.finishNode(node, "WhileStatement");
};
pp$8.parseWithStatement = function(node) {
  if (this.strict) {
    this.raise(this.start, "'with' in strict mode");
  }
  this.next();
  node.object = this.parseParenExpression();
  node.body = this.parseStatement("with");
  return this.finishNode(node, "WithStatement");
};
pp$8.parseEmptyStatement = function(node) {
  this.next();
  return this.finishNode(node, "EmptyStatement");
};
pp$8.parseLabeledStatement = function(node, maybeName, expr, context) {
  for (var i$1 = 0, list2 = this.labels; i$1 < list2.length; i$1 += 1) {
    var label = list2[i$1];
    if (label.name === maybeName) {
      this.raise(expr.start, "Label '" + maybeName + "' is already declared");
    }
  }
  var kind = this.type.isLoop ? "loop" : this.type === types$1._switch ? "switch" : null;
  for (var i = this.labels.length - 1; i >= 0; i--) {
    var label$1 = this.labels[i];
    if (label$1.statementStart === node.start) {
      label$1.statementStart = this.start;
      label$1.kind = kind;
    } else {
      break;
    }
  }
  this.labels.push({ name: maybeName, kind, statementStart: this.start });
  node.body = this.parseStatement(context ? context.indexOf("label") === -1 ? context + "label" : context : "label");
  this.labels.pop();
  node.label = expr;
  return this.finishNode(node, "LabeledStatement");
};
pp$8.parseExpressionStatement = function(node, expr) {
  node.expression = expr;
  this.semicolon();
  return this.finishNode(node, "ExpressionStatement");
};
pp$8.parseBlock = function(createNewLexicalScope, node, exitStrict) {
  if (createNewLexicalScope === void 0) createNewLexicalScope = true;
  if (node === void 0) node = this.startNode();
  node.body = [];
  this.expect(types$1.braceL);
  if (createNewLexicalScope) {
    this.enterScope(0);
  }
  while (this.type !== types$1.braceR) {
    var stmt = this.parseStatement(null);
    node.body.push(stmt);
  }
  if (exitStrict) {
    this.strict = false;
  }
  this.next();
  if (createNewLexicalScope) {
    this.exitScope();
  }
  return this.finishNode(node, "BlockStatement");
};
pp$8.parseFor = function(node, init) {
  node.init = init;
  this.expect(types$1.semi);
  node.test = this.type === types$1.semi ? null : this.parseExpression();
  this.expect(types$1.semi);
  node.update = this.type === types$1.parenR ? null : this.parseExpression();
  this.expect(types$1.parenR);
  node.body = this.parseStatement("for");
  this.exitScope();
  this.labels.pop();
  return this.finishNode(node, "ForStatement");
};
pp$8.parseForIn = function(node, init) {
  var isForIn = this.type === types$1._in;
  this.next();
  if (init.type === "VariableDeclaration" && init.declarations[0].init != null && (!isForIn || this.options.ecmaVersion < 8 || this.strict || init.kind !== "var" || init.declarations[0].id.type !== "Identifier")) {
    this.raise(
      init.start,
      (isForIn ? "for-in" : "for-of") + " loop variable declaration may not have an initializer"
    );
  }
  node.left = init;
  node.right = isForIn ? this.parseExpression() : this.parseMaybeAssign();
  this.expect(types$1.parenR);
  node.body = this.parseStatement("for");
  this.exitScope();
  this.labels.pop();
  return this.finishNode(node, isForIn ? "ForInStatement" : "ForOfStatement");
};
pp$8.parseVar = function(node, isFor, kind, allowMissingInitializer) {
  node.declarations = [];
  node.kind = kind;
  for (; ; ) {
    var decl = this.startNode();
    this.parseVarId(decl, kind);
    if (this.eat(types$1.eq)) {
      decl.init = this.parseMaybeAssign(isFor);
    } else if (!allowMissingInitializer && kind === "const" && !(this.type === types$1._in || this.options.ecmaVersion >= 6 && this.isContextual("of"))) {
      this.unexpected();
    } else if (!allowMissingInitializer && (kind === "using" || kind === "await using") && this.options.ecmaVersion >= 17 && this.type !== types$1._in && !this.isContextual("of")) {
      this.raise(this.lastTokEnd, "Missing initializer in " + kind + " declaration");
    } else if (!allowMissingInitializer && decl.id.type !== "Identifier" && !(isFor && (this.type === types$1._in || this.isContextual("of")))) {
      this.raise(this.lastTokEnd, "Complex binding patterns require an initialization value");
    } else {
      decl.init = null;
    }
    node.declarations.push(this.finishNode(decl, "VariableDeclarator"));
    if (!this.eat(types$1.comma)) {
      break;
    }
  }
  return node;
};
pp$8.parseVarId = function(decl, kind) {
  decl.id = kind === "using" || kind === "await using" ? this.parseIdent() : this.parseBindingAtom();
  this.checkLValPattern(decl.id, kind === "var" ? BIND_VAR : BIND_LEXICAL, false);
};
var FUNC_STATEMENT = 1, FUNC_HANGING_STATEMENT = 2, FUNC_NULLABLE_ID = 4;
pp$8.parseFunction = function(node, statement, allowExpressionBody, isAsync, forInit) {
  this.initFunction(node);
  if (this.options.ecmaVersion >= 9 || this.options.ecmaVersion >= 6 && !isAsync) {
    if (this.type === types$1.star && statement & FUNC_HANGING_STATEMENT) {
      this.unexpected();
    }
    node.generator = this.eat(types$1.star);
  }
  if (this.options.ecmaVersion >= 8) {
    node.async = !!isAsync;
  }
  if (statement & FUNC_STATEMENT) {
    node.id = statement & FUNC_NULLABLE_ID && this.type !== types$1.name ? null : this.parseIdent();
    if (node.id && !(statement & FUNC_HANGING_STATEMENT)) {
      this.checkLValSimple(node.id, this.strict || node.generator || node.async ? this.treatFunctionsAsVar ? BIND_VAR : BIND_LEXICAL : BIND_FUNCTION);
    }
  }
  var oldYieldPos = this.yieldPos, oldAwaitPos = this.awaitPos, oldAwaitIdentPos = this.awaitIdentPos;
  this.yieldPos = 0;
  this.awaitPos = 0;
  this.awaitIdentPos = 0;
  this.enterScope(functionFlags(node.async, node.generator));
  if (!(statement & FUNC_STATEMENT)) {
    node.id = this.type === types$1.name ? this.parseIdent() : null;
  }
  this.parseFunctionParams(node);
  this.parseFunctionBody(node, allowExpressionBody, false, forInit);
  this.yieldPos = oldYieldPos;
  this.awaitPos = oldAwaitPos;
  this.awaitIdentPos = oldAwaitIdentPos;
  return this.finishNode(node, statement & FUNC_STATEMENT ? "FunctionDeclaration" : "FunctionExpression");
};
pp$8.parseFunctionParams = function(node) {
  this.expect(types$1.parenL);
  node.params = this.parseBindingList(types$1.parenR, false, this.options.ecmaVersion >= 8);
  this.checkYieldAwaitInDefaultParams();
};
pp$8.parseClass = function(node, isStatement) {
  this.next();
  var oldStrict = this.strict;
  this.strict = true;
  this.parseClassId(node, isStatement);
  this.parseClassSuper(node);
  var privateNameMap = this.enterClassBody();
  var classBody = this.startNode();
  var hadConstructor = false;
  classBody.body = [];
  this.expect(types$1.braceL);
  while (this.type !== types$1.braceR) {
    var element = this.parseClassElement(node.superClass !== null);
    if (element) {
      classBody.body.push(element);
      if (element.type === "MethodDefinition" && element.kind === "constructor") {
        if (hadConstructor) {
          this.raiseRecoverable(element.start, "Duplicate constructor in the same class");
        }
        hadConstructor = true;
      } else if (element.key && element.key.type === "PrivateIdentifier" && isPrivateNameConflicted(privateNameMap, element)) {
        this.raiseRecoverable(element.key.start, "Identifier '#" + element.key.name + "' has already been declared");
      }
    }
  }
  this.strict = oldStrict;
  this.next();
  node.body = this.finishNode(classBody, "ClassBody");
  this.exitClassBody();
  return this.finishNode(node, isStatement ? "ClassDeclaration" : "ClassExpression");
};
pp$8.parseClassElement = function(constructorAllowsSuper) {
  if (this.eat(types$1.semi)) {
    return null;
  }
  var ecmaVersion = this.options.ecmaVersion;
  var node = this.startNode();
  var keyName = "";
  var isGenerator = false;
  var isAsync = false;
  var kind = "method";
  var isStatic = false;
  if (this.eatContextual("static")) {
    if (ecmaVersion >= 13 && this.eat(types$1.braceL)) {
      this.parseClassStaticBlock(node);
      return node;
    }
    if (this.isClassElementNameStart() || this.type === types$1.star) {
      isStatic = true;
    } else {
      keyName = "static";
    }
  }
  node.static = isStatic;
  if (!keyName && ecmaVersion >= 8 && this.eatContextual("async")) {
    if ((this.isClassElementNameStart() || this.type === types$1.star) && !this.canInsertSemicolon()) {
      isAsync = true;
    } else {
      keyName = "async";
    }
  }
  if (!keyName && (ecmaVersion >= 9 || !isAsync) && this.eat(types$1.star)) {
    isGenerator = true;
  }
  if (!keyName && !isAsync && !isGenerator) {
    var lastValue = this.value;
    if (this.eatContextual("get") || this.eatContextual("set")) {
      if (this.isClassElementNameStart()) {
        kind = lastValue;
      } else {
        keyName = lastValue;
      }
    }
  }
  if (keyName) {
    node.computed = false;
    node.key = this.startNodeAt(this.lastTokStart, this.lastTokStartLoc);
    node.key.name = keyName;
    this.finishNode(node.key, "Identifier");
  } else {
    this.parseClassElementName(node);
  }
  if (ecmaVersion < 13 || this.type === types$1.parenL || kind !== "method" || isGenerator || isAsync) {
    var isConstructor = !node.static && checkKeyName(node, "constructor");
    var allowsDirectSuper = isConstructor && constructorAllowsSuper;
    if (isConstructor && kind !== "method") {
      this.raise(node.key.start, "Constructor can't have get/set modifier");
    }
    node.kind = isConstructor ? "constructor" : kind;
    this.parseClassMethod(node, isGenerator, isAsync, allowsDirectSuper);
  } else {
    this.parseClassField(node);
  }
  return node;
};
pp$8.isClassElementNameStart = function() {
  return this.type === types$1.name || this.type === types$1.privateId || this.type === types$1.num || this.type === types$1.string || this.type === types$1.bracketL || this.type.keyword;
};
pp$8.parseClassElementName = function(element) {
  if (this.type === types$1.privateId) {
    if (this.value === "constructor") {
      this.raise(this.start, "Classes can't have an element named '#constructor'");
    }
    element.computed = false;
    element.key = this.parsePrivateIdent();
  } else {
    this.parsePropertyName(element);
  }
};
pp$8.parseClassMethod = function(method, isGenerator, isAsync, allowsDirectSuper) {
  var key2 = method.key;
  if (method.kind === "constructor") {
    if (isGenerator) {
      this.raise(key2.start, "Constructor can't be a generator");
    }
    if (isAsync) {
      this.raise(key2.start, "Constructor can't be an async method");
    }
  } else if (method.static && checkKeyName(method, "prototype")) {
    this.raise(key2.start, "Classes may not have a static property named prototype");
  }
  var value2 = method.value = this.parseMethod(isGenerator, isAsync, allowsDirectSuper);
  if (method.kind === "get" && value2.params.length !== 0) {
    this.raiseRecoverable(value2.start, "getter should have no params");
  }
  if (method.kind === "set" && value2.params.length !== 1) {
    this.raiseRecoverable(value2.start, "setter should have exactly one param");
  }
  if (method.kind === "set" && value2.params[0].type === "RestElement") {
    this.raiseRecoverable(value2.params[0].start, "Setter cannot use rest params");
  }
  return this.finishNode(method, "MethodDefinition");
};
pp$8.parseClassField = function(field2) {
  if (checkKeyName(field2, "constructor")) {
    this.raise(field2.key.start, "Classes can't have a field named 'constructor'");
  } else if (field2.static && checkKeyName(field2, "prototype")) {
    this.raise(field2.key.start, "Classes can't have a static field named 'prototype'");
  }
  if (this.eat(types$1.eq)) {
    this.enterScope(SCOPE_CLASS_FIELD_INIT | SCOPE_SUPER);
    field2.value = this.parseMaybeAssign();
    this.exitScope();
  } else {
    field2.value = null;
  }
  this.semicolon();
  return this.finishNode(field2, "PropertyDefinition");
};
pp$8.parseClassStaticBlock = function(node) {
  node.body = [];
  var oldLabels = this.labels;
  this.labels = [];
  this.enterScope(SCOPE_CLASS_STATIC_BLOCK | SCOPE_SUPER);
  while (this.type !== types$1.braceR) {
    var stmt = this.parseStatement(null);
    node.body.push(stmt);
  }
  this.next();
  this.exitScope();
  this.labels = oldLabels;
  return this.finishNode(node, "StaticBlock");
};
pp$8.parseClassId = function(node, isStatement) {
  if (this.type === types$1.name) {
    node.id = this.parseIdent();
    if (isStatement) {
      this.checkLValSimple(node.id, BIND_LEXICAL, false);
    }
  } else {
    if (isStatement === true) {
      this.unexpected();
    }
    node.id = null;
  }
};
pp$8.parseClassSuper = function(node) {
  node.superClass = this.eat(types$1._extends) ? this.parseExprSubscripts(null, false) : null;
};
pp$8.enterClassBody = function() {
  var element = { declared: /* @__PURE__ */ Object.create(null), used: [] };
  this.privateNameStack.push(element);
  return element.declared;
};
pp$8.exitClassBody = function() {
  var ref2 = this.privateNameStack.pop();
  var declared = ref2.declared;
  var used = ref2.used;
  if (!this.options.checkPrivateFields) {
    return;
  }
  var len = this.privateNameStack.length;
  var parent = len === 0 ? null : this.privateNameStack[len - 1];
  for (var i = 0; i < used.length; ++i) {
    var id = used[i];
    if (!hasOwn(declared, id.name)) {
      if (parent) {
        parent.used.push(id);
      } else {
        this.raiseRecoverable(id.start, "Private field '#" + id.name + "' must be declared in an enclosing class");
      }
    }
  }
};
function isPrivateNameConflicted(privateNameMap, element) {
  var name2 = element.key.name;
  var curr = privateNameMap[name2];
  var next = "true";
  if (element.type === "MethodDefinition" && (element.kind === "get" || element.kind === "set")) {
    next = (element.static ? "s" : "i") + element.kind;
  }
  if (curr === "iget" && next === "iset" || curr === "iset" && next === "iget" || curr === "sget" && next === "sset" || curr === "sset" && next === "sget") {
    privateNameMap[name2] = "true";
    return false;
  } else if (!curr) {
    privateNameMap[name2] = next;
    return false;
  } else {
    return true;
  }
}
function checkKeyName(node, name2) {
  var computed = node.computed;
  var key2 = node.key;
  return !computed && (key2.type === "Identifier" && key2.name === name2 || key2.type === "Literal" && key2.value === name2);
}
pp$8.parseExportAllDeclaration = function(node, exports) {
  if (this.options.ecmaVersion >= 11) {
    if (this.eatContextual("as")) {
      node.exported = this.parseModuleExportName();
      this.checkExport(exports, node.exported, this.lastTokStart);
    } else {
      node.exported = null;
    }
  }
  this.expectContextual("from");
  if (this.type !== types$1.string) {
    this.unexpected();
  }
  node.source = this.parseExprAtom();
  if (this.options.ecmaVersion >= 16) {
    node.attributes = this.parseWithClause();
  }
  this.semicolon();
  return this.finishNode(node, "ExportAllDeclaration");
};
pp$8.parseExport = function(node, exports) {
  this.next();
  if (this.eat(types$1.star)) {
    return this.parseExportAllDeclaration(node, exports);
  }
  if (this.eat(types$1._default)) {
    this.checkExport(exports, "default", this.lastTokStart);
    node.declaration = this.parseExportDefaultDeclaration();
    return this.finishNode(node, "ExportDefaultDeclaration");
  }
  if (this.shouldParseExportStatement()) {
    node.declaration = this.parseExportDeclaration(node);
    if (node.declaration.type === "VariableDeclaration") {
      this.checkVariableExport(exports, node.declaration.declarations);
    } else {
      this.checkExport(exports, node.declaration.id, node.declaration.id.start);
    }
    node.specifiers = [];
    node.source = null;
    if (this.options.ecmaVersion >= 16) {
      node.attributes = [];
    }
  } else {
    node.declaration = null;
    node.specifiers = this.parseExportSpecifiers(exports);
    if (this.eatContextual("from")) {
      if (this.type !== types$1.string) {
        this.unexpected();
      }
      node.source = this.parseExprAtom();
      if (this.options.ecmaVersion >= 16) {
        node.attributes = this.parseWithClause();
      }
    } else {
      for (var i = 0, list2 = node.specifiers; i < list2.length; i += 1) {
        var spec = list2[i];
        this.checkUnreserved(spec.local);
        this.checkLocalExport(spec.local);
        if (spec.local.type === "Literal") {
          this.raise(spec.local.start, "A string literal cannot be used as an exported binding without `from`.");
        }
      }
      node.source = null;
      if (this.options.ecmaVersion >= 16) {
        node.attributes = [];
      }
    }
    this.semicolon();
  }
  return this.finishNode(node, "ExportNamedDeclaration");
};
pp$8.parseExportDeclaration = function(node) {
  return this.parseStatement(null);
};
pp$8.parseExportDefaultDeclaration = function() {
  var isAsync;
  if (this.type === types$1._function || (isAsync = this.isAsyncFunction())) {
    var fNode = this.startNode();
    this.next();
    if (isAsync) {
      this.next();
    }
    return this.parseFunction(fNode, FUNC_STATEMENT | FUNC_NULLABLE_ID, false, isAsync);
  } else if (this.type === types$1._class) {
    var cNode = this.startNode();
    return this.parseClass(cNode, "nullableID");
  } else {
    var declaration = this.parseMaybeAssign();
    this.semicolon();
    return declaration;
  }
};
pp$8.checkExport = function(exports, name2, pos) {
  if (!exports) {
    return;
  }
  if (typeof name2 !== "string") {
    name2 = name2.type === "Identifier" ? name2.name : name2.value;
  }
  if (hasOwn(exports, name2)) {
    this.raiseRecoverable(pos, "Duplicate export '" + name2 + "'");
  }
  exports[name2] = true;
};
pp$8.checkPatternExport = function(exports, pat) {
  var type = pat.type;
  if (type === "Identifier") {
    this.checkExport(exports, pat, pat.start);
  } else if (type === "ObjectPattern") {
    for (var i = 0, list2 = pat.properties; i < list2.length; i += 1) {
      var prop = list2[i];
      this.checkPatternExport(exports, prop);
    }
  } else if (type === "ArrayPattern") {
    for (var i$1 = 0, list$1 = pat.elements; i$1 < list$1.length; i$1 += 1) {
      var elt = list$1[i$1];
      if (elt) {
        this.checkPatternExport(exports, elt);
      }
    }
  } else if (type === "Property") {
    this.checkPatternExport(exports, pat.value);
  } else if (type === "AssignmentPattern") {
    this.checkPatternExport(exports, pat.left);
  } else if (type === "RestElement") {
    this.checkPatternExport(exports, pat.argument);
  }
};
pp$8.checkVariableExport = function(exports, decls) {
  if (!exports) {
    return;
  }
  for (var i = 0, list2 = decls; i < list2.length; i += 1) {
    var decl = list2[i];
    this.checkPatternExport(exports, decl.id);
  }
};
pp$8.shouldParseExportStatement = function() {
  return this.type.keyword === "var" || this.type.keyword === "const" || this.type.keyword === "class" || this.type.keyword === "function" || this.isLet() || this.isAsyncFunction();
};
pp$8.parseExportSpecifier = function(exports) {
  var node = this.startNode();
  node.local = this.parseModuleExportName();
  node.exported = this.eatContextual("as") ? this.parseModuleExportName() : node.local;
  this.checkExport(
    exports,
    node.exported,
    node.exported.start
  );
  return this.finishNode(node, "ExportSpecifier");
};
pp$8.parseExportSpecifiers = function(exports) {
  var nodes = [], first = true;
  this.expect(types$1.braceL);
  while (!this.eat(types$1.braceR)) {
    if (!first) {
      this.expect(types$1.comma);
      if (this.afterTrailingComma(types$1.braceR)) {
        break;
      }
    } else {
      first = false;
    }
    nodes.push(this.parseExportSpecifier(exports));
  }
  return nodes;
};
pp$8.parseImport = function(node) {
  this.next();
  if (this.type === types$1.string) {
    node.specifiers = empty$1;
    node.source = this.parseExprAtom();
  } else {
    node.specifiers = this.parseImportSpecifiers();
    this.expectContextual("from");
    node.source = this.type === types$1.string ? this.parseExprAtom() : this.unexpected();
  }
  if (this.options.ecmaVersion >= 16) {
    node.attributes = this.parseWithClause();
  }
  this.semicolon();
  return this.finishNode(node, "ImportDeclaration");
};
pp$8.parseImportSpecifier = function() {
  var node = this.startNode();
  node.imported = this.parseModuleExportName();
  if (this.eatContextual("as")) {
    node.local = this.parseIdent();
  } else {
    this.checkUnreserved(node.imported);
    node.local = node.imported;
  }
  this.checkLValSimple(node.local, BIND_LEXICAL);
  return this.finishNode(node, "ImportSpecifier");
};
pp$8.parseImportDefaultSpecifier = function() {
  var node = this.startNode();
  node.local = this.parseIdent();
  this.checkLValSimple(node.local, BIND_LEXICAL);
  return this.finishNode(node, "ImportDefaultSpecifier");
};
pp$8.parseImportNamespaceSpecifier = function() {
  var node = this.startNode();
  this.next();
  this.expectContextual("as");
  node.local = this.parseIdent();
  this.checkLValSimple(node.local, BIND_LEXICAL);
  return this.finishNode(node, "ImportNamespaceSpecifier");
};
pp$8.parseImportSpecifiers = function() {
  var nodes = [], first = true;
  if (this.type === types$1.name) {
    nodes.push(this.parseImportDefaultSpecifier());
    if (!this.eat(types$1.comma)) {
      return nodes;
    }
  }
  if (this.type === types$1.star) {
    nodes.push(this.parseImportNamespaceSpecifier());
    return nodes;
  }
  this.expect(types$1.braceL);
  while (!this.eat(types$1.braceR)) {
    if (!first) {
      this.expect(types$1.comma);
      if (this.afterTrailingComma(types$1.braceR)) {
        break;
      }
    } else {
      first = false;
    }
    nodes.push(this.parseImportSpecifier());
  }
  return nodes;
};
pp$8.parseWithClause = function() {
  var nodes = [];
  if (!this.eat(types$1._with)) {
    return nodes;
  }
  this.expect(types$1.braceL);
  var attributeKeys = {};
  var first = true;
  while (!this.eat(types$1.braceR)) {
    if (!first) {
      this.expect(types$1.comma);
      if (this.afterTrailingComma(types$1.braceR)) {
        break;
      }
    } else {
      first = false;
    }
    var attr = this.parseImportAttribute();
    var keyName = attr.key.type === "Identifier" ? attr.key.name : attr.key.value;
    if (hasOwn(attributeKeys, keyName)) {
      this.raiseRecoverable(attr.key.start, "Duplicate attribute key '" + keyName + "'");
    }
    attributeKeys[keyName] = true;
    nodes.push(attr);
  }
  return nodes;
};
pp$8.parseImportAttribute = function() {
  var node = this.startNode();
  node.key = this.type === types$1.string ? this.parseExprAtom() : this.parseIdent(this.options.allowReserved !== "never");
  this.expect(types$1.colon);
  if (this.type !== types$1.string) {
    this.unexpected();
  }
  node.value = this.parseExprAtom();
  return this.finishNode(node, "ImportAttribute");
};
pp$8.parseModuleExportName = function() {
  if (this.options.ecmaVersion >= 13 && this.type === types$1.string) {
    var stringLiteral = this.parseLiteral(this.value);
    if (loneSurrogate.test(stringLiteral.value)) {
      this.raise(stringLiteral.start, "An export name cannot include a lone surrogate.");
    }
    return stringLiteral;
  }
  return this.parseIdent(true);
};
pp$8.adaptDirectivePrologue = function(statements) {
  for (var i = 0; i < statements.length && this.isDirectiveCandidate(statements[i]); ++i) {
    statements[i].directive = statements[i].expression.raw.slice(1, -1);
  }
};
pp$8.isDirectiveCandidate = function(statement) {
  return this.options.ecmaVersion >= 5 && statement.type === "ExpressionStatement" && statement.expression.type === "Literal" && typeof statement.expression.value === "string" && // Reject parenthesized strings.
  (this.input[statement.start] === '"' || this.input[statement.start] === "'");
};
var pp$7 = Parser.prototype;
pp$7.toAssignable = function(node, isBinding, refDestructuringErrors) {
  if (this.options.ecmaVersion >= 6 && node) {
    switch (node.type) {
      case "Identifier":
        if (this.inAsync && node.name === "await") {
          this.raise(node.start, "Cannot use 'await' as identifier inside an async function");
        }
        break;
      case "ObjectPattern":
      case "ArrayPattern":
      case "AssignmentPattern":
      case "RestElement":
        break;
      case "ObjectExpression":
        node.type = "ObjectPattern";
        if (refDestructuringErrors) {
          this.checkPatternErrors(refDestructuringErrors, true);
        }
        for (var i = 0, list2 = node.properties; i < list2.length; i += 1) {
          var prop = list2[i];
          this.toAssignable(prop, isBinding);
          if (prop.type === "RestElement" && (prop.argument.type === "ArrayPattern" || prop.argument.type === "ObjectPattern")) {
            this.raise(prop.argument.start, "Unexpected token");
          }
        }
        break;
      case "Property":
        if (node.kind !== "init") {
          this.raise(node.key.start, "Object pattern can't contain getter or setter");
        }
        this.toAssignable(node.value, isBinding);
        break;
      case "ArrayExpression":
        node.type = "ArrayPattern";
        if (refDestructuringErrors) {
          this.checkPatternErrors(refDestructuringErrors, true);
        }
        this.toAssignableList(node.elements, isBinding);
        break;
      case "SpreadElement":
        node.type = "RestElement";
        this.toAssignable(node.argument, isBinding);
        if (node.argument.type === "AssignmentPattern") {
          this.raise(node.argument.start, "Rest elements cannot have a default value");
        }
        break;
      case "AssignmentExpression":
        if (node.operator !== "=") {
          this.raise(node.left.end, "Only '=' operator can be used for specifying default value.");
        }
        node.type = "AssignmentPattern";
        delete node.operator;
        this.toAssignable(node.left, isBinding);
        break;
      case "ParenthesizedExpression":
        this.toAssignable(node.expression, isBinding, refDestructuringErrors);
        break;
      case "ChainExpression":
        this.raiseRecoverable(node.start, "Optional chaining cannot appear in left-hand side");
        break;
      case "MemberExpression":
        if (!isBinding) {
          break;
        }
      default:
        this.raise(node.start, "Assigning to rvalue");
    }
  } else if (refDestructuringErrors) {
    this.checkPatternErrors(refDestructuringErrors, true);
  }
  return node;
};
pp$7.toAssignableList = function(exprList, isBinding) {
  var end = exprList.length;
  for (var i = 0; i < end; i++) {
    var elt = exprList[i];
    if (elt) {
      this.toAssignable(elt, isBinding);
    }
  }
  if (end) {
    var last = exprList[end - 1];
    if (this.options.ecmaVersion === 6 && isBinding && last && last.type === "RestElement" && last.argument.type !== "Identifier") {
      this.unexpected(last.argument.start);
    }
  }
  return exprList;
};
pp$7.parseSpread = function(refDestructuringErrors) {
  var node = this.startNode();
  this.next();
  node.argument = this.parseMaybeAssign(false, refDestructuringErrors);
  return this.finishNode(node, "SpreadElement");
};
pp$7.parseRestBinding = function() {
  var node = this.startNode();
  this.next();
  if (this.options.ecmaVersion === 6 && this.type !== types$1.name) {
    this.unexpected();
  }
  node.argument = this.parseBindingAtom();
  return this.finishNode(node, "RestElement");
};
pp$7.parseBindingAtom = function() {
  if (this.options.ecmaVersion >= 6) {
    switch (this.type) {
      case types$1.bracketL:
        var node = this.startNode();
        this.next();
        node.elements = this.parseBindingList(types$1.bracketR, true, true);
        return this.finishNode(node, "ArrayPattern");
      case types$1.braceL:
        return this.parseObj(true);
    }
  }
  return this.parseIdent();
};
pp$7.parseBindingList = function(close, allowEmpty, allowTrailingComma, allowModifiers) {
  var elts = [], first = true;
  while (!this.eat(close)) {
    if (first) {
      first = false;
    } else {
      this.expect(types$1.comma);
    }
    if (allowEmpty && this.type === types$1.comma) {
      elts.push(null);
    } else if (allowTrailingComma && this.afterTrailingComma(close)) {
      break;
    } else if (this.type === types$1.ellipsis) {
      var rest = this.parseRestBinding();
      this.parseBindingListItem(rest);
      elts.push(rest);
      if (this.type === types$1.comma) {
        this.raiseRecoverable(this.start, "Comma is not permitted after the rest element");
      }
      this.expect(close);
      break;
    } else {
      elts.push(this.parseAssignableListItem(allowModifiers));
    }
  }
  return elts;
};
pp$7.parseAssignableListItem = function(allowModifiers) {
  var elem = this.parseMaybeDefault(this.start, this.startLoc);
  this.parseBindingListItem(elem);
  return elem;
};
pp$7.parseBindingListItem = function(param) {
  return param;
};
pp$7.parseMaybeDefault = function(startPos, startLoc, left) {
  left = left || this.parseBindingAtom();
  if (this.options.ecmaVersion < 6 || !this.eat(types$1.eq)) {
    return left;
  }
  var node = this.startNodeAt(startPos, startLoc);
  node.left = left;
  node.right = this.parseMaybeAssign();
  return this.finishNode(node, "AssignmentPattern");
};
pp$7.checkLValSimple = function(expr, bindingType, checkClashes) {
  if (bindingType === void 0) bindingType = BIND_NONE;
  var isBind = bindingType !== BIND_NONE;
  switch (expr.type) {
    case "Identifier":
      if (this.strict && this.reservedWordsStrictBind.test(expr.name)) {
        this.raiseRecoverable(expr.start, (isBind ? "Binding " : "Assigning to ") + expr.name + " in strict mode");
      }
      if (isBind) {
        if (bindingType === BIND_LEXICAL && expr.name === "let") {
          this.raiseRecoverable(expr.start, "let is disallowed as a lexically bound name");
        }
        if (checkClashes) {
          if (hasOwn(checkClashes, expr.name)) {
            this.raiseRecoverable(expr.start, "Argument name clash");
          }
          checkClashes[expr.name] = true;
        }
        if (bindingType !== BIND_OUTSIDE) {
          this.declareName(expr.name, bindingType, expr.start);
        }
      }
      break;
    case "ChainExpression":
      this.raiseRecoverable(expr.start, "Optional chaining cannot appear in left-hand side");
      break;
    case "MemberExpression":
      if (isBind) {
        this.raiseRecoverable(expr.start, "Binding member expression");
      }
      break;
    case "ParenthesizedExpression":
      if (isBind) {
        this.raiseRecoverable(expr.start, "Binding parenthesized expression");
      }
      return this.checkLValSimple(expr.expression, bindingType, checkClashes);
    default:
      this.raise(expr.start, (isBind ? "Binding" : "Assigning to") + " rvalue");
  }
};
pp$7.checkLValPattern = function(expr, bindingType, checkClashes) {
  if (bindingType === void 0) bindingType = BIND_NONE;
  switch (expr.type) {
    case "ObjectPattern":
      for (var i = 0, list2 = expr.properties; i < list2.length; i += 1) {
        var prop = list2[i];
        this.checkLValInnerPattern(prop, bindingType, checkClashes);
      }
      break;
    case "ArrayPattern":
      for (var i$1 = 0, list$1 = expr.elements; i$1 < list$1.length; i$1 += 1) {
        var elem = list$1[i$1];
        if (elem) {
          this.checkLValInnerPattern(elem, bindingType, checkClashes);
        }
      }
      break;
    default:
      this.checkLValSimple(expr, bindingType, checkClashes);
  }
};
pp$7.checkLValInnerPattern = function(expr, bindingType, checkClashes) {
  if (bindingType === void 0) bindingType = BIND_NONE;
  switch (expr.type) {
    case "Property":
      this.checkLValInnerPattern(expr.value, bindingType, checkClashes);
      break;
    case "AssignmentPattern":
      this.checkLValPattern(expr.left, bindingType, checkClashes);
      break;
    case "RestElement":
      this.checkLValPattern(expr.argument, bindingType, checkClashes);
      break;
    default:
      this.checkLValPattern(expr, bindingType, checkClashes);
  }
};
var TokContext = function TokContext2(token, isExpr, preserveSpace, override, generator) {
  this.token = token;
  this.isExpr = !!isExpr;
  this.preserveSpace = !!preserveSpace;
  this.override = override;
  this.generator = !!generator;
};
var types = {
  b_stat: new TokContext("{", false),
  b_expr: new TokContext("{", true),
  b_tmpl: new TokContext("${", false),
  p_stat: new TokContext("(", false),
  p_expr: new TokContext("(", true),
  q_tmpl: new TokContext("`", true, true, function(p) {
    return p.tryReadTemplateToken();
  }),
  f_stat: new TokContext("function", false),
  f_expr: new TokContext("function", true),
  f_expr_gen: new TokContext("function", true, false, null, true),
  f_gen: new TokContext("function", false, false, null, true)
};
var pp$6 = Parser.prototype;
pp$6.initialContext = function() {
  return [types.b_stat];
};
pp$6.curContext = function() {
  return this.context[this.context.length - 1];
};
pp$6.braceIsBlock = function(prevType) {
  var parent = this.curContext();
  if (parent === types.f_expr || parent === types.f_stat) {
    return true;
  }
  if (prevType === types$1.colon && (parent === types.b_stat || parent === types.b_expr)) {
    return !parent.isExpr;
  }
  if (prevType === types$1._return || prevType === types$1.name && this.exprAllowed) {
    return lineBreak.test(this.input.slice(this.lastTokEnd, this.start));
  }
  if (prevType === types$1._else || prevType === types$1.semi || prevType === types$1.eof || prevType === types$1.parenR || prevType === types$1.arrow) {
    return true;
  }
  if (prevType === types$1.braceL) {
    return parent === types.b_stat;
  }
  if (prevType === types$1._var || prevType === types$1._const || prevType === types$1.name) {
    return false;
  }
  return !this.exprAllowed;
};
pp$6.inGeneratorContext = function() {
  for (var i = this.context.length - 1; i >= 1; i--) {
    var context = this.context[i];
    if (context.token === "function") {
      return context.generator;
    }
  }
  return false;
};
pp$6.updateContext = function(prevType) {
  var update2, type = this.type;
  if (type.keyword && prevType === types$1.dot) {
    this.exprAllowed = false;
  } else if (update2 = type.updateContext) {
    update2.call(this, prevType);
  } else {
    this.exprAllowed = type.beforeExpr;
  }
};
pp$6.overrideContext = function(tokenCtx) {
  if (this.curContext() !== tokenCtx) {
    this.context[this.context.length - 1] = tokenCtx;
  }
};
types$1.parenR.updateContext = types$1.braceR.updateContext = function() {
  if (this.context.length === 1) {
    this.exprAllowed = true;
    return;
  }
  var out = this.context.pop();
  if (out === types.b_stat && this.curContext().token === "function") {
    out = this.context.pop();
  }
  this.exprAllowed = !out.isExpr;
};
types$1.braceL.updateContext = function(prevType) {
  this.context.push(this.braceIsBlock(prevType) ? types.b_stat : types.b_expr);
  this.exprAllowed = true;
};
types$1.dollarBraceL.updateContext = function() {
  this.context.push(types.b_tmpl);
  this.exprAllowed = true;
};
types$1.parenL.updateContext = function(prevType) {
  var statementParens = prevType === types$1._if || prevType === types$1._for || prevType === types$1._with || prevType === types$1._while;
  this.context.push(statementParens ? types.p_stat : types.p_expr);
  this.exprAllowed = true;
};
types$1.incDec.updateContext = function() {
};
types$1._function.updateContext = types$1._class.updateContext = function(prevType) {
  if (prevType.beforeExpr && prevType !== types$1._else && !(prevType === types$1.semi && this.curContext() !== types.p_stat) && !(prevType === types$1._return && lineBreak.test(this.input.slice(this.lastTokEnd, this.start))) && !((prevType === types$1.colon || prevType === types$1.braceL) && this.curContext() === types.b_stat)) {
    this.context.push(types.f_expr);
  } else {
    this.context.push(types.f_stat);
  }
  this.exprAllowed = false;
};
types$1.colon.updateContext = function() {
  if (this.curContext().token === "function") {
    this.context.pop();
  }
  this.exprAllowed = true;
};
types$1.backQuote.updateContext = function() {
  if (this.curContext() === types.q_tmpl) {
    this.context.pop();
  } else {
    this.context.push(types.q_tmpl);
  }
  this.exprAllowed = false;
};
types$1.star.updateContext = function(prevType) {
  if (prevType === types$1._function) {
    var index = this.context.length - 1;
    if (this.context[index] === types.f_expr) {
      this.context[index] = types.f_expr_gen;
    } else {
      this.context[index] = types.f_gen;
    }
  }
  this.exprAllowed = true;
};
types$1.name.updateContext = function(prevType) {
  var allowed = false;
  if (this.options.ecmaVersion >= 6 && prevType !== types$1.dot) {
    if (this.value === "of" && !this.exprAllowed || this.value === "yield" && this.inGeneratorContext()) {
      allowed = true;
    }
  }
  this.exprAllowed = allowed;
};
var pp$5 = Parser.prototype;
pp$5.checkPropClash = function(prop, propHash, refDestructuringErrors) {
  if (this.options.ecmaVersion >= 9 && prop.type === "SpreadElement") {
    return;
  }
  if (this.options.ecmaVersion >= 6 && (prop.computed || prop.method || prop.shorthand)) {
    return;
  }
  var key2 = prop.key;
  var name2;
  switch (key2.type) {
    case "Identifier":
      name2 = key2.name;
      break;
    case "Literal":
      name2 = String(key2.value);
      break;
    default:
      return;
  }
  var kind = prop.kind;
  if (this.options.ecmaVersion >= 6) {
    if (name2 === "__proto__" && kind === "init") {
      if (propHash.proto) {
        if (refDestructuringErrors) {
          if (refDestructuringErrors.doubleProto < 0) {
            refDestructuringErrors.doubleProto = key2.start;
          }
        } else {
          this.raiseRecoverable(key2.start, "Redefinition of __proto__ property");
        }
      }
      propHash.proto = true;
    }
    return;
  }
  name2 = "$" + name2;
  var other = propHash[name2];
  if (other) {
    var redefinition;
    if (kind === "init") {
      redefinition = this.strict && other.init || other.get || other.set;
    } else {
      redefinition = other.init || other[kind];
    }
    if (redefinition) {
      this.raiseRecoverable(key2.start, "Redefinition of property");
    }
  } else {
    other = propHash[name2] = {
      init: false,
      get: false,
      set: false
    };
  }
  other[kind] = true;
};
pp$5.parseExpression = function(forInit, refDestructuringErrors) {
  var startPos = this.start, startLoc = this.startLoc;
  var expr = this.parseMaybeAssign(forInit, refDestructuringErrors);
  if (this.type === types$1.comma) {
    var node = this.startNodeAt(startPos, startLoc);
    node.expressions = [expr];
    while (this.eat(types$1.comma)) {
      node.expressions.push(this.parseMaybeAssign(forInit, refDestructuringErrors));
    }
    return this.finishNode(node, "SequenceExpression");
  }
  return expr;
};
pp$5.parseMaybeAssign = function(forInit, refDestructuringErrors, afterLeftParse) {
  if (this.isContextual("yield")) {
    if (this.inGenerator) {
      return this.parseYield(forInit);
    } else {
      this.exprAllowed = false;
    }
  }
  var ownDestructuringErrors = false, oldParenAssign = -1, oldTrailingComma = -1, oldDoubleProto = -1;
  if (refDestructuringErrors) {
    oldParenAssign = refDestructuringErrors.parenthesizedAssign;
    oldTrailingComma = refDestructuringErrors.trailingComma;
    oldDoubleProto = refDestructuringErrors.doubleProto;
    refDestructuringErrors.parenthesizedAssign = refDestructuringErrors.trailingComma = -1;
  } else {
    refDestructuringErrors = new DestructuringErrors();
    ownDestructuringErrors = true;
  }
  var startPos = this.start, startLoc = this.startLoc;
  if (this.type === types$1.parenL || this.type === types$1.name) {
    this.potentialArrowAt = this.start;
    this.potentialArrowInForAwait = forInit === "await";
  }
  var left = this.parseMaybeConditional(forInit, refDestructuringErrors);
  if (afterLeftParse) {
    left = afterLeftParse.call(this, left, startPos, startLoc);
  }
  if (this.type.isAssign) {
    var node = this.startNodeAt(startPos, startLoc);
    node.operator = this.value;
    if (this.type === types$1.eq) {
      left = this.toAssignable(left, false, refDestructuringErrors);
    }
    if (!ownDestructuringErrors) {
      refDestructuringErrors.parenthesizedAssign = refDestructuringErrors.trailingComma = refDestructuringErrors.doubleProto = -1;
    }
    if (refDestructuringErrors.shorthandAssign >= left.start) {
      refDestructuringErrors.shorthandAssign = -1;
    }
    if (this.type === types$1.eq) {
      this.checkLValPattern(left);
    } else {
      this.checkLValSimple(left);
    }
    node.left = left;
    this.next();
    node.right = this.parseMaybeAssign(forInit);
    if (oldDoubleProto > -1) {
      refDestructuringErrors.doubleProto = oldDoubleProto;
    }
    return this.finishNode(node, "AssignmentExpression");
  } else {
    if (ownDestructuringErrors) {
      this.checkExpressionErrors(refDestructuringErrors, true);
    }
  }
  if (oldParenAssign > -1) {
    refDestructuringErrors.parenthesizedAssign = oldParenAssign;
  }
  if (oldTrailingComma > -1) {
    refDestructuringErrors.trailingComma = oldTrailingComma;
  }
  return left;
};
pp$5.parseMaybeConditional = function(forInit, refDestructuringErrors) {
  var startPos = this.start, startLoc = this.startLoc;
  var expr = this.parseExprOps(forInit, refDestructuringErrors);
  if (this.checkExpressionErrors(refDestructuringErrors)) {
    return expr;
  }
  if (this.eat(types$1.question)) {
    var node = this.startNodeAt(startPos, startLoc);
    node.test = expr;
    node.consequent = this.parseMaybeAssign();
    this.expect(types$1.colon);
    node.alternate = this.parseMaybeAssign(forInit);
    return this.finishNode(node, "ConditionalExpression");
  }
  return expr;
};
pp$5.parseExprOps = function(forInit, refDestructuringErrors) {
  var startPos = this.start, startLoc = this.startLoc;
  var expr = this.parseMaybeUnary(refDestructuringErrors, false, false, forInit);
  if (this.checkExpressionErrors(refDestructuringErrors)) {
    return expr;
  }
  return expr.start === startPos && expr.type === "ArrowFunctionExpression" ? expr : this.parseExprOp(expr, startPos, startLoc, -1, forInit);
};
pp$5.parseExprOp = function(left, leftStartPos, leftStartLoc, minPrec, forInit) {
  var prec = this.type.binop;
  if (prec != null && (!forInit || this.type !== types$1._in)) {
    if (prec > minPrec) {
      var logical = this.type === types$1.logicalOR || this.type === types$1.logicalAND;
      var coalesce = this.type === types$1.coalesce;
      if (coalesce) {
        prec = types$1.logicalAND.binop;
      }
      var op2 = this.value;
      this.next();
      var startPos = this.start, startLoc = this.startLoc;
      var right = this.parseExprOp(this.parseMaybeUnary(null, false, false, forInit), startPos, startLoc, prec, forInit);
      var node = this.buildBinary(leftStartPos, leftStartLoc, left, right, op2, logical || coalesce);
      if (logical && this.type === types$1.coalesce || coalesce && (this.type === types$1.logicalOR || this.type === types$1.logicalAND)) {
        this.raiseRecoverable(this.start, "Logical expressions and coalesce expressions cannot be mixed. Wrap either by parentheses");
      }
      return this.parseExprOp(node, leftStartPos, leftStartLoc, minPrec, forInit);
    }
  }
  return left;
};
pp$5.buildBinary = function(startPos, startLoc, left, right, op2, logical) {
  if (right.type === "PrivateIdentifier") {
    this.raise(right.start, "Private identifier can only be left side of binary expression");
  }
  var node = this.startNodeAt(startPos, startLoc);
  node.left = left;
  node.operator = op2;
  node.right = right;
  return this.finishNode(node, logical ? "LogicalExpression" : "BinaryExpression");
};
pp$5.parseMaybeUnary = function(refDestructuringErrors, sawUnary, incDec, forInit) {
  var startPos = this.start, startLoc = this.startLoc, expr;
  if (this.isContextual("await") && this.canAwait) {
    expr = this.parseAwait(forInit);
    sawUnary = true;
  } else if (this.type.prefix) {
    var node = this.startNode(), update2 = this.type === types$1.incDec;
    node.operator = this.value;
    node.prefix = true;
    this.next();
    node.argument = this.parseMaybeUnary(null, true, update2, forInit);
    this.checkExpressionErrors(refDestructuringErrors, true);
    if (update2) {
      this.checkLValSimple(node.argument);
    } else if (this.strict && node.operator === "delete" && isLocalVariableAccess(node.argument)) {
      this.raiseRecoverable(node.start, "Deleting local variable in strict mode");
    } else if (node.operator === "delete" && isPrivateFieldAccess(node.argument)) {
      this.raiseRecoverable(node.start, "Private fields can not be deleted");
    } else {
      sawUnary = true;
    }
    expr = this.finishNode(node, update2 ? "UpdateExpression" : "UnaryExpression");
  } else if (!sawUnary && this.type === types$1.privateId) {
    if ((forInit || this.privateNameStack.length === 0) && this.options.checkPrivateFields) {
      this.unexpected();
    }
    expr = this.parsePrivateIdent();
    if (this.type !== types$1._in) {
      this.unexpected();
    }
  } else {
    expr = this.parseExprSubscripts(refDestructuringErrors, forInit);
    if (this.checkExpressionErrors(refDestructuringErrors)) {
      return expr;
    }
    while (this.type.postfix && !this.canInsertSemicolon()) {
      var node$1 = this.startNodeAt(startPos, startLoc);
      node$1.operator = this.value;
      node$1.prefix = false;
      node$1.argument = expr;
      this.checkLValSimple(expr);
      this.next();
      expr = this.finishNode(node$1, "UpdateExpression");
    }
  }
  if (!incDec && this.eat(types$1.starstar)) {
    if (sawUnary) {
      this.unexpected(this.lastTokStart);
    } else {
      return this.buildBinary(startPos, startLoc, expr, this.parseMaybeUnary(null, false, false, forInit), "**", false);
    }
  } else {
    return expr;
  }
};
function isLocalVariableAccess(node) {
  return node.type === "Identifier" || node.type === "ParenthesizedExpression" && isLocalVariableAccess(node.expression);
}
function isPrivateFieldAccess(node) {
  return node.type === "MemberExpression" && node.property.type === "PrivateIdentifier" || node.type === "ChainExpression" && isPrivateFieldAccess(node.expression) || node.type === "ParenthesizedExpression" && isPrivateFieldAccess(node.expression);
}
pp$5.parseExprSubscripts = function(refDestructuringErrors, forInit) {
  var startPos = this.start, startLoc = this.startLoc;
  var expr = this.parseExprAtom(refDestructuringErrors, forInit);
  if (expr.type === "ArrowFunctionExpression" && this.input.slice(this.lastTokStart, this.lastTokEnd) !== ")") {
    return expr;
  }
  var result2 = this.parseSubscripts(expr, startPos, startLoc, false, forInit);
  if (refDestructuringErrors && result2.type === "MemberExpression") {
    if (refDestructuringErrors.parenthesizedAssign >= result2.start) {
      refDestructuringErrors.parenthesizedAssign = -1;
    }
    if (refDestructuringErrors.parenthesizedBind >= result2.start) {
      refDestructuringErrors.parenthesizedBind = -1;
    }
    if (refDestructuringErrors.trailingComma >= result2.start) {
      refDestructuringErrors.trailingComma = -1;
    }
  }
  return result2;
};
pp$5.parseSubscripts = function(base, startPos, startLoc, noCalls, forInit) {
  var maybeAsyncArrow = this.options.ecmaVersion >= 8 && base.type === "Identifier" && base.name === "async" && this.lastTokEnd === base.end && !this.canInsertSemicolon() && base.end - base.start === 5 && this.potentialArrowAt === base.start;
  var optionalChained = false;
  while (true) {
    var element = this.parseSubscript(base, startPos, startLoc, noCalls, maybeAsyncArrow, optionalChained, forInit);
    if (element.optional) {
      optionalChained = true;
    }
    if (element === base || element.type === "ArrowFunctionExpression") {
      if (optionalChained) {
        var chainNode = this.startNodeAt(startPos, startLoc);
        chainNode.expression = element;
        element = this.finishNode(chainNode, "ChainExpression");
      }
      return element;
    }
    base = element;
  }
};
pp$5.shouldParseAsyncArrow = function() {
  return !this.canInsertSemicolon() && this.eat(types$1.arrow);
};
pp$5.parseSubscriptAsyncArrow = function(startPos, startLoc, exprList, forInit) {
  return this.parseArrowExpression(this.startNodeAt(startPos, startLoc), exprList, true, forInit);
};
pp$5.parseSubscript = function(base, startPos, startLoc, noCalls, maybeAsyncArrow, optionalChained, forInit) {
  var optionalSupported = this.options.ecmaVersion >= 11;
  var optional = optionalSupported && this.eat(types$1.questionDot);
  if (noCalls && optional) {
    this.raise(this.lastTokStart, "Optional chaining cannot appear in the callee of new expressions");
  }
  var computed = this.eat(types$1.bracketL);
  if (computed || optional && this.type !== types$1.parenL && this.type !== types$1.backQuote || this.eat(types$1.dot)) {
    var node = this.startNodeAt(startPos, startLoc);
    node.object = base;
    if (computed) {
      node.property = this.parseExpression();
      this.expect(types$1.bracketR);
    } else if (this.type === types$1.privateId && base.type !== "Super") {
      node.property = this.parsePrivateIdent();
    } else {
      node.property = this.parseIdent(this.options.allowReserved !== "never");
    }
    node.computed = !!computed;
    if (optionalSupported) {
      node.optional = optional;
    }
    base = this.finishNode(node, "MemberExpression");
  } else if (!noCalls && this.eat(types$1.parenL)) {
    var refDestructuringErrors = new DestructuringErrors(), oldYieldPos = this.yieldPos, oldAwaitPos = this.awaitPos, oldAwaitIdentPos = this.awaitIdentPos;
    this.yieldPos = 0;
    this.awaitPos = 0;
    this.awaitIdentPos = 0;
    var exprList = this.parseExprList(types$1.parenR, this.options.ecmaVersion >= 8, false, refDestructuringErrors);
    if (maybeAsyncArrow && !optional && this.shouldParseAsyncArrow()) {
      this.checkPatternErrors(refDestructuringErrors, false);
      this.checkYieldAwaitInDefaultParams();
      if (this.awaitIdentPos > 0) {
        this.raise(this.awaitIdentPos, "Cannot use 'await' as identifier inside an async function");
      }
      this.yieldPos = oldYieldPos;
      this.awaitPos = oldAwaitPos;
      this.awaitIdentPos = oldAwaitIdentPos;
      return this.parseSubscriptAsyncArrow(startPos, startLoc, exprList, forInit);
    }
    this.checkExpressionErrors(refDestructuringErrors, true);
    this.yieldPos = oldYieldPos || this.yieldPos;
    this.awaitPos = oldAwaitPos || this.awaitPos;
    this.awaitIdentPos = oldAwaitIdentPos || this.awaitIdentPos;
    var node$1 = this.startNodeAt(startPos, startLoc);
    node$1.callee = base;
    node$1.arguments = exprList;
    if (optionalSupported) {
      node$1.optional = optional;
    }
    base = this.finishNode(node$1, "CallExpression");
  } else if (this.type === types$1.backQuote) {
    if (optional || optionalChained) {
      this.raise(this.start, "Optional chaining cannot appear in the tag of tagged template expressions");
    }
    var node$2 = this.startNodeAt(startPos, startLoc);
    node$2.tag = base;
    node$2.quasi = this.parseTemplate({ isTagged: true });
    base = this.finishNode(node$2, "TaggedTemplateExpression");
  }
  return base;
};
pp$5.parseExprAtom = function(refDestructuringErrors, forInit, forNew) {
  if (this.type === types$1.slash) {
    this.readRegexp();
  }
  var node, canBeArrow = this.potentialArrowAt === this.start;
  switch (this.type) {
    case types$1._super:
      if (!this.allowSuper) {
        this.raise(this.start, "'super' keyword outside a method");
      }
      node = this.startNode();
      this.next();
      if (this.type === types$1.parenL && !this.allowDirectSuper) {
        this.raise(node.start, "super() call outside constructor of a subclass");
      }
      if (this.type !== types$1.dot && this.type !== types$1.bracketL && this.type !== types$1.parenL) {
        this.unexpected();
      }
      return this.finishNode(node, "Super");
    case types$1._this:
      node = this.startNode();
      this.next();
      return this.finishNode(node, "ThisExpression");
    case types$1.name:
      var startPos = this.start, startLoc = this.startLoc, containsEsc = this.containsEsc;
      var id = this.parseIdent(false);
      if (this.options.ecmaVersion >= 8 && !containsEsc && id.name === "async" && !this.canInsertSemicolon() && this.eat(types$1._function)) {
        this.overrideContext(types.f_expr);
        return this.parseFunction(this.startNodeAt(startPos, startLoc), 0, false, true, forInit);
      }
      if (canBeArrow && !this.canInsertSemicolon()) {
        if (this.eat(types$1.arrow)) {
          return this.parseArrowExpression(this.startNodeAt(startPos, startLoc), [id], false, forInit);
        }
        if (this.options.ecmaVersion >= 8 && id.name === "async" && this.type === types$1.name && !containsEsc && (!this.potentialArrowInForAwait || this.value !== "of" || this.containsEsc)) {
          id = this.parseIdent(false);
          if (this.canInsertSemicolon() || !this.eat(types$1.arrow)) {
            this.unexpected();
          }
          return this.parseArrowExpression(this.startNodeAt(startPos, startLoc), [id], true, forInit);
        }
      }
      return id;
    case types$1.regexp:
      var value2 = this.value;
      node = this.parseLiteral(value2.value);
      node.regex = { pattern: value2.pattern, flags: value2.flags };
      return node;
    case types$1.num:
    case types$1.string:
      return this.parseLiteral(this.value);
    case types$1._null:
    case types$1._true:
    case types$1._false:
      node = this.startNode();
      node.value = this.type === types$1._null ? null : this.type === types$1._true;
      node.raw = this.type.keyword;
      this.next();
      return this.finishNode(node, "Literal");
    case types$1.parenL:
      var start = this.start, expr = this.parseParenAndDistinguishExpression(canBeArrow, forInit);
      if (refDestructuringErrors) {
        if (refDestructuringErrors.parenthesizedAssign < 0 && !this.isSimpleAssignTarget(expr)) {
          refDestructuringErrors.parenthesizedAssign = start;
        }
        if (refDestructuringErrors.parenthesizedBind < 0) {
          refDestructuringErrors.parenthesizedBind = start;
        }
      }
      return expr;
    case types$1.bracketL:
      node = this.startNode();
      this.next();
      node.elements = this.parseExprList(types$1.bracketR, true, true, refDestructuringErrors);
      return this.finishNode(node, "ArrayExpression");
    case types$1.braceL:
      this.overrideContext(types.b_expr);
      return this.parseObj(false, refDestructuringErrors);
    case types$1._function:
      node = this.startNode();
      this.next();
      return this.parseFunction(node, 0);
    case types$1._class:
      return this.parseClass(this.startNode(), false);
    case types$1._new:
      return this.parseNew();
    case types$1.backQuote:
      return this.parseTemplate();
    case types$1._import:
      if (this.options.ecmaVersion >= 11) {
        return this.parseExprImport(forNew);
      } else {
        return this.unexpected();
      }
    default:
      return this.parseExprAtomDefault();
  }
};
pp$5.parseExprAtomDefault = function() {
  this.unexpected();
};
pp$5.parseExprImport = function(forNew) {
  var node = this.startNode();
  if (this.containsEsc) {
    this.raiseRecoverable(this.start, "Escape sequence in keyword import");
  }
  this.next();
  if (this.type === types$1.parenL && !forNew) {
    return this.parseDynamicImport(node);
  } else if (this.type === types$1.dot) {
    var meta = this.startNodeAt(node.start, node.loc && node.loc.start);
    meta.name = "import";
    node.meta = this.finishNode(meta, "Identifier");
    return this.parseImportMeta(node);
  } else {
    this.unexpected();
  }
};
pp$5.parseDynamicImport = function(node) {
  this.next();
  node.source = this.parseMaybeAssign();
  if (this.options.ecmaVersion >= 16) {
    if (!this.eat(types$1.parenR)) {
      this.expect(types$1.comma);
      if (!this.afterTrailingComma(types$1.parenR)) {
        node.options = this.parseMaybeAssign();
        if (!this.eat(types$1.parenR)) {
          this.expect(types$1.comma);
          if (!this.afterTrailingComma(types$1.parenR)) {
            this.unexpected();
          }
        }
      } else {
        node.options = null;
      }
    } else {
      node.options = null;
    }
  } else {
    if (!this.eat(types$1.parenR)) {
      var errorPos = this.start;
      if (this.eat(types$1.comma) && this.eat(types$1.parenR)) {
        this.raiseRecoverable(errorPos, "Trailing comma is not allowed in import()");
      } else {
        this.unexpected(errorPos);
      }
    }
  }
  return this.finishNode(node, "ImportExpression");
};
pp$5.parseImportMeta = function(node) {
  this.next();
  var containsEsc = this.containsEsc;
  node.property = this.parseIdent(true);
  if (node.property.name !== "meta") {
    this.raiseRecoverable(node.property.start, "The only valid meta property for import is 'import.meta'");
  }
  if (containsEsc) {
    this.raiseRecoverable(node.start, "'import.meta' must not contain escaped characters");
  }
  if (this.options.sourceType !== "module" && !this.options.allowImportExportEverywhere) {
    this.raiseRecoverable(node.start, "Cannot use 'import.meta' outside a module");
  }
  return this.finishNode(node, "MetaProperty");
};
pp$5.parseLiteral = function(value2) {
  var node = this.startNode();
  node.value = value2;
  node.raw = this.input.slice(this.start, this.end);
  if (node.raw.charCodeAt(node.raw.length - 1) === 110) {
    node.bigint = node.value != null ? node.value.toString() : node.raw.slice(0, -1).replace(/_/g, "");
  }
  this.next();
  return this.finishNode(node, "Literal");
};
pp$5.parseParenExpression = function() {
  this.expect(types$1.parenL);
  var val = this.parseExpression();
  this.expect(types$1.parenR);
  return val;
};
pp$5.shouldParseArrow = function(exprList) {
  return !this.canInsertSemicolon();
};
pp$5.parseParenAndDistinguishExpression = function(canBeArrow, forInit) {
  var startPos = this.start, startLoc = this.startLoc, val, allowTrailingComma = this.options.ecmaVersion >= 8;
  if (this.options.ecmaVersion >= 6) {
    this.next();
    var innerStartPos = this.start, innerStartLoc = this.startLoc;
    var exprList = [], first = true, lastIsComma = false;
    var refDestructuringErrors = new DestructuringErrors(), oldYieldPos = this.yieldPos, oldAwaitPos = this.awaitPos, spreadStart;
    this.yieldPos = 0;
    this.awaitPos = 0;
    while (this.type !== types$1.parenR) {
      first ? first = false : this.expect(types$1.comma);
      if (allowTrailingComma && this.afterTrailingComma(types$1.parenR, true)) {
        lastIsComma = true;
        break;
      } else if (this.type === types$1.ellipsis) {
        spreadStart = this.start;
        exprList.push(this.parseParenItem(this.parseRestBinding()));
        if (this.type === types$1.comma) {
          this.raiseRecoverable(
            this.start,
            "Comma is not permitted after the rest element"
          );
        }
        break;
      } else {
        exprList.push(this.parseMaybeAssign(false, refDestructuringErrors, this.parseParenItem));
      }
    }
    var innerEndPos = this.lastTokEnd, innerEndLoc = this.lastTokEndLoc;
    this.expect(types$1.parenR);
    if (canBeArrow && this.shouldParseArrow(exprList) && this.eat(types$1.arrow)) {
      this.checkPatternErrors(refDestructuringErrors, false);
      this.checkYieldAwaitInDefaultParams();
      this.yieldPos = oldYieldPos;
      this.awaitPos = oldAwaitPos;
      return this.parseParenArrowList(startPos, startLoc, exprList, forInit);
    }
    if (!exprList.length || lastIsComma) {
      this.unexpected(this.lastTokStart);
    }
    if (spreadStart) {
      this.unexpected(spreadStart);
    }
    this.checkExpressionErrors(refDestructuringErrors, true);
    this.yieldPos = oldYieldPos || this.yieldPos;
    this.awaitPos = oldAwaitPos || this.awaitPos;
    if (exprList.length > 1) {
      val = this.startNodeAt(innerStartPos, innerStartLoc);
      val.expressions = exprList;
      this.finishNodeAt(val, "SequenceExpression", innerEndPos, innerEndLoc);
    } else {
      val = exprList[0];
    }
  } else {
    val = this.parseParenExpression();
  }
  if (this.options.preserveParens) {
    var par = this.startNodeAt(startPos, startLoc);
    par.expression = val;
    return this.finishNode(par, "ParenthesizedExpression");
  } else {
    return val;
  }
};
pp$5.parseParenItem = function(item) {
  return item;
};
pp$5.parseParenArrowList = function(startPos, startLoc, exprList, forInit) {
  return this.parseArrowExpression(this.startNodeAt(startPos, startLoc), exprList, false, forInit);
};
var empty = [];
pp$5.parseNew = function() {
  if (this.containsEsc) {
    this.raiseRecoverable(this.start, "Escape sequence in keyword new");
  }
  var node = this.startNode();
  this.next();
  if (this.options.ecmaVersion >= 6 && this.type === types$1.dot) {
    var meta = this.startNodeAt(node.start, node.loc && node.loc.start);
    meta.name = "new";
    node.meta = this.finishNode(meta, "Identifier");
    this.next();
    var containsEsc = this.containsEsc;
    node.property = this.parseIdent(true);
    if (node.property.name !== "target") {
      this.raiseRecoverable(node.property.start, "The only valid meta property for new is 'new.target'");
    }
    if (containsEsc) {
      this.raiseRecoverable(node.start, "'new.target' must not contain escaped characters");
    }
    if (!this.allowNewDotTarget) {
      this.raiseRecoverable(node.start, "'new.target' can only be used in functions and class static block");
    }
    return this.finishNode(node, "MetaProperty");
  }
  var startPos = this.start, startLoc = this.startLoc;
  node.callee = this.parseSubscripts(this.parseExprAtom(null, false, true), startPos, startLoc, true, false);
  if (this.eat(types$1.parenL)) {
    node.arguments = this.parseExprList(types$1.parenR, this.options.ecmaVersion >= 8, false);
  } else {
    node.arguments = empty;
  }
  return this.finishNode(node, "NewExpression");
};
pp$5.parseTemplateElement = function(ref2) {
  var isTagged = ref2.isTagged;
  var elem = this.startNode();
  if (this.type === types$1.invalidTemplate) {
    if (!isTagged) {
      this.raiseRecoverable(this.start, "Bad escape sequence in untagged template literal");
    }
    elem.value = {
      raw: this.value.replace(/\r\n?/g, "\n"),
      cooked: null
    };
  } else {
    elem.value = {
      raw: this.input.slice(this.start, this.end).replace(/\r\n?/g, "\n"),
      cooked: this.value
    };
  }
  this.next();
  elem.tail = this.type === types$1.backQuote;
  return this.finishNode(elem, "TemplateElement");
};
pp$5.parseTemplate = function(ref2) {
  if (ref2 === void 0) ref2 = {};
  var isTagged = ref2.isTagged;
  if (isTagged === void 0) isTagged = false;
  var node = this.startNode();
  this.next();
  node.expressions = [];
  var curElt = this.parseTemplateElement({ isTagged });
  node.quasis = [curElt];
  while (!curElt.tail) {
    if (this.type === types$1.eof) {
      this.raise(this.pos, "Unterminated template literal");
    }
    this.expect(types$1.dollarBraceL);
    node.expressions.push(this.parseExpression());
    this.expect(types$1.braceR);
    node.quasis.push(curElt = this.parseTemplateElement({ isTagged }));
  }
  this.next();
  return this.finishNode(node, "TemplateLiteral");
};
pp$5.isAsyncProp = function(prop) {
  return !prop.computed && prop.key.type === "Identifier" && prop.key.name === "async" && (this.type === types$1.name || this.type === types$1.num || this.type === types$1.string || this.type === types$1.bracketL || this.type.keyword || this.options.ecmaVersion >= 9 && this.type === types$1.star) && !lineBreak.test(this.input.slice(this.lastTokEnd, this.start));
};
pp$5.parseObj = function(isPattern, refDestructuringErrors) {
  var node = this.startNode(), first = true, propHash = {};
  node.properties = [];
  this.next();
  while (!this.eat(types$1.braceR)) {
    if (!first) {
      this.expect(types$1.comma);
      if (this.options.ecmaVersion >= 5 && this.afterTrailingComma(types$1.braceR)) {
        break;
      }
    } else {
      first = false;
    }
    var prop = this.parseProperty(isPattern, refDestructuringErrors);
    if (!isPattern) {
      this.checkPropClash(prop, propHash, refDestructuringErrors);
    }
    node.properties.push(prop);
  }
  return this.finishNode(node, isPattern ? "ObjectPattern" : "ObjectExpression");
};
pp$5.parseProperty = function(isPattern, refDestructuringErrors) {
  var prop = this.startNode(), isGenerator, isAsync, startPos, startLoc;
  if (this.options.ecmaVersion >= 9 && this.eat(types$1.ellipsis)) {
    if (isPattern) {
      prop.argument = this.parseIdent(false);
      if (this.type === types$1.comma) {
        this.raiseRecoverable(this.start, "Comma is not permitted after the rest element");
      }
      return this.finishNode(prop, "RestElement");
    }
    prop.argument = this.parseMaybeAssign(false, refDestructuringErrors);
    if (this.type === types$1.comma && refDestructuringErrors && refDestructuringErrors.trailingComma < 0) {
      refDestructuringErrors.trailingComma = this.start;
    }
    return this.finishNode(prop, "SpreadElement");
  }
  if (this.options.ecmaVersion >= 6) {
    prop.method = false;
    prop.shorthand = false;
    if (isPattern || refDestructuringErrors) {
      startPos = this.start;
      startLoc = this.startLoc;
    }
    if (!isPattern) {
      isGenerator = this.eat(types$1.star);
    }
  }
  var containsEsc = this.containsEsc;
  this.parsePropertyName(prop);
  if (!isPattern && !containsEsc && this.options.ecmaVersion >= 8 && !isGenerator && this.isAsyncProp(prop)) {
    isAsync = true;
    isGenerator = this.options.ecmaVersion >= 9 && this.eat(types$1.star);
    this.parsePropertyName(prop);
  } else {
    isAsync = false;
  }
  this.parsePropertyValue(prop, isPattern, isGenerator, isAsync, startPos, startLoc, refDestructuringErrors, containsEsc);
  return this.finishNode(prop, "Property");
};
pp$5.parseGetterSetter = function(prop) {
  var kind = prop.key.name;
  this.parsePropertyName(prop);
  prop.value = this.parseMethod(false);
  prop.kind = kind;
  var paramCount = prop.kind === "get" ? 0 : 1;
  if (prop.value.params.length !== paramCount) {
    var start = prop.value.start;
    if (prop.kind === "get") {
      this.raiseRecoverable(start, "getter should have no params");
    } else {
      this.raiseRecoverable(start, "setter should have exactly one param");
    }
  } else {
    if (prop.kind === "set" && prop.value.params[0].type === "RestElement") {
      this.raiseRecoverable(prop.value.params[0].start, "Setter cannot use rest params");
    }
  }
};
pp$5.parsePropertyValue = function(prop, isPattern, isGenerator, isAsync, startPos, startLoc, refDestructuringErrors, containsEsc) {
  if ((isGenerator || isAsync) && this.type === types$1.colon) {
    this.unexpected();
  }
  if (this.eat(types$1.colon)) {
    prop.value = isPattern ? this.parseMaybeDefault(this.start, this.startLoc) : this.parseMaybeAssign(false, refDestructuringErrors);
    prop.kind = "init";
  } else if (this.options.ecmaVersion >= 6 && this.type === types$1.parenL) {
    if (isPattern) {
      this.unexpected();
    }
    prop.method = true;
    prop.value = this.parseMethod(isGenerator, isAsync);
    prop.kind = "init";
  } else if (!isPattern && !containsEsc && this.options.ecmaVersion >= 5 && !prop.computed && prop.key.type === "Identifier" && (prop.key.name === "get" || prop.key.name === "set") && (this.type !== types$1.comma && this.type !== types$1.braceR && this.type !== types$1.eq)) {
    if (isGenerator || isAsync) {
      this.unexpected();
    }
    this.parseGetterSetter(prop);
  } else if (this.options.ecmaVersion >= 6 && !prop.computed && prop.key.type === "Identifier") {
    if (isGenerator || isAsync) {
      this.unexpected();
    }
    this.checkUnreserved(prop.key);
    if (prop.key.name === "await" && !this.awaitIdentPos) {
      this.awaitIdentPos = startPos;
    }
    if (isPattern) {
      prop.value = this.parseMaybeDefault(startPos, startLoc, this.copyNode(prop.key));
    } else if (this.type === types$1.eq && refDestructuringErrors) {
      if (refDestructuringErrors.shorthandAssign < 0) {
        refDestructuringErrors.shorthandAssign = this.start;
      }
      prop.value = this.parseMaybeDefault(startPos, startLoc, this.copyNode(prop.key));
    } else {
      prop.value = this.copyNode(prop.key);
    }
    prop.kind = "init";
    prop.shorthand = true;
  } else {
    this.unexpected();
  }
};
pp$5.parsePropertyName = function(prop) {
  if (this.options.ecmaVersion >= 6) {
    if (this.eat(types$1.bracketL)) {
      prop.computed = true;
      prop.key = this.parseMaybeAssign();
      this.expect(types$1.bracketR);
      return prop.key;
    } else {
      prop.computed = false;
    }
  }
  return prop.key = this.type === types$1.num || this.type === types$1.string ? this.parseExprAtom() : this.parseIdent(this.options.allowReserved !== "never");
};
pp$5.initFunction = function(node) {
  node.id = null;
  if (this.options.ecmaVersion >= 6) {
    node.generator = node.expression = false;
  }
  if (this.options.ecmaVersion >= 8) {
    node.async = false;
  }
};
pp$5.parseMethod = function(isGenerator, isAsync, allowDirectSuper) {
  var node = this.startNode(), oldYieldPos = this.yieldPos, oldAwaitPos = this.awaitPos, oldAwaitIdentPos = this.awaitIdentPos;
  this.initFunction(node);
  if (this.options.ecmaVersion >= 6) {
    node.generator = isGenerator;
  }
  if (this.options.ecmaVersion >= 8) {
    node.async = !!isAsync;
  }
  this.yieldPos = 0;
  this.awaitPos = 0;
  this.awaitIdentPos = 0;
  this.enterScope(functionFlags(isAsync, node.generator) | SCOPE_SUPER | (allowDirectSuper ? SCOPE_DIRECT_SUPER : 0));
  this.expect(types$1.parenL);
  node.params = this.parseBindingList(types$1.parenR, false, this.options.ecmaVersion >= 8);
  this.checkYieldAwaitInDefaultParams();
  this.parseFunctionBody(node, false, true, false);
  this.yieldPos = oldYieldPos;
  this.awaitPos = oldAwaitPos;
  this.awaitIdentPos = oldAwaitIdentPos;
  return this.finishNode(node, "FunctionExpression");
};
pp$5.parseArrowExpression = function(node, params, isAsync, forInit) {
  var oldYieldPos = this.yieldPos, oldAwaitPos = this.awaitPos, oldAwaitIdentPos = this.awaitIdentPos;
  this.enterScope(functionFlags(isAsync, false) | SCOPE_ARROW);
  this.initFunction(node);
  if (this.options.ecmaVersion >= 8) {
    node.async = !!isAsync;
  }
  this.yieldPos = 0;
  this.awaitPos = 0;
  this.awaitIdentPos = 0;
  node.params = this.toAssignableList(params, true);
  this.parseFunctionBody(node, true, false, forInit);
  this.yieldPos = oldYieldPos;
  this.awaitPos = oldAwaitPos;
  this.awaitIdentPos = oldAwaitIdentPos;
  return this.finishNode(node, "ArrowFunctionExpression");
};
pp$5.parseFunctionBody = function(node, isArrowFunction, isMethod, forInit) {
  var isExpression = isArrowFunction && this.type !== types$1.braceL;
  var oldStrict = this.strict, useStrict = false;
  if (isExpression) {
    node.body = this.parseMaybeAssign(forInit);
    node.expression = true;
    this.checkParams(node, false);
  } else {
    var nonSimple = this.options.ecmaVersion >= 7 && !this.isSimpleParamList(node.params);
    if (!oldStrict || nonSimple) {
      useStrict = this.strictDirective(this.end);
      if (useStrict && nonSimple) {
        this.raiseRecoverable(node.start, "Illegal 'use strict' directive in function with non-simple parameter list");
      }
    }
    var oldLabels = this.labels;
    this.labels = [];
    if (useStrict) {
      this.strict = true;
    }
    this.checkParams(node, !oldStrict && !useStrict && !isArrowFunction && !isMethod && this.isSimpleParamList(node.params));
    if (this.strict && node.id) {
      this.checkLValSimple(node.id, BIND_OUTSIDE);
    }
    node.body = this.parseBlock(false, void 0, useStrict && !oldStrict);
    node.expression = false;
    this.adaptDirectivePrologue(node.body.body);
    this.labels = oldLabels;
  }
  this.exitScope();
};
pp$5.isSimpleParamList = function(params) {
  for (var i = 0, list2 = params; i < list2.length; i += 1) {
    var param = list2[i];
    if (param.type !== "Identifier") {
      return false;
    }
  }
  return true;
};
pp$5.checkParams = function(node, allowDuplicates) {
  var nameHash = /* @__PURE__ */ Object.create(null);
  for (var i = 0, list2 = node.params; i < list2.length; i += 1) {
    var param = list2[i];
    this.checkLValInnerPattern(param, BIND_VAR, allowDuplicates ? null : nameHash);
  }
};
pp$5.parseExprList = function(close, allowTrailingComma, allowEmpty, refDestructuringErrors) {
  var elts = [], first = true;
  while (!this.eat(close)) {
    if (!first) {
      this.expect(types$1.comma);
      if (allowTrailingComma && this.afterTrailingComma(close)) {
        break;
      }
    } else {
      first = false;
    }
    var elt = void 0;
    if (allowEmpty && this.type === types$1.comma) {
      elt = null;
    } else if (this.type === types$1.ellipsis) {
      elt = this.parseSpread(refDestructuringErrors);
      if (refDestructuringErrors && this.type === types$1.comma && refDestructuringErrors.trailingComma < 0) {
        refDestructuringErrors.trailingComma = this.start;
      }
    } else {
      elt = this.parseMaybeAssign(false, refDestructuringErrors);
    }
    elts.push(elt);
  }
  return elts;
};
pp$5.checkUnreserved = function(ref2) {
  var start = ref2.start;
  var end = ref2.end;
  var name2 = ref2.name;
  if (this.inGenerator && name2 === "yield") {
    this.raiseRecoverable(start, "Cannot use 'yield' as identifier inside a generator");
  }
  if (this.inAsync && name2 === "await") {
    this.raiseRecoverable(start, "Cannot use 'await' as identifier inside an async function");
  }
  if (!(this.currentThisScope().flags & SCOPE_VAR) && name2 === "arguments") {
    this.raiseRecoverable(start, "Cannot use 'arguments' in class field initializer");
  }
  if (this.inClassStaticBlock && (name2 === "arguments" || name2 === "await")) {
    this.raise(start, "Cannot use " + name2 + " in class static initialization block");
  }
  if (this.keywords.test(name2)) {
    this.raise(start, "Unexpected keyword '" + name2 + "'");
  }
  if (this.options.ecmaVersion < 6 && this.input.slice(start, end).indexOf("\\") !== -1) {
    return;
  }
  var re = this.strict ? this.reservedWordsStrict : this.reservedWords;
  if (re.test(name2)) {
    if (!this.inAsync && name2 === "await") {
      this.raiseRecoverable(start, "Cannot use keyword 'await' outside an async function");
    }
    this.raiseRecoverable(start, "The keyword '" + name2 + "' is reserved");
  }
};
pp$5.parseIdent = function(liberal) {
  var node = this.parseIdentNode();
  this.next(!!liberal);
  this.finishNode(node, "Identifier");
  if (!liberal) {
    this.checkUnreserved(node);
    if (node.name === "await" && !this.awaitIdentPos) {
      this.awaitIdentPos = node.start;
    }
  }
  return node;
};
pp$5.parseIdentNode = function() {
  var node = this.startNode();
  if (this.type === types$1.name) {
    node.name = this.value;
  } else if (this.type.keyword) {
    node.name = this.type.keyword;
    if ((node.name === "class" || node.name === "function") && (this.lastTokEnd !== this.lastTokStart + 1 || this.input.charCodeAt(this.lastTokStart) !== 46)) {
      this.context.pop();
    }
    this.type = types$1.name;
  } else {
    this.unexpected();
  }
  return node;
};
pp$5.parsePrivateIdent = function() {
  var node = this.startNode();
  if (this.type === types$1.privateId) {
    node.name = this.value;
  } else {
    this.unexpected();
  }
  this.next();
  this.finishNode(node, "PrivateIdentifier");
  if (this.options.checkPrivateFields) {
    if (this.privateNameStack.length === 0) {
      this.raise(node.start, "Private field '#" + node.name + "' must be declared in an enclosing class");
    } else {
      this.privateNameStack[this.privateNameStack.length - 1].used.push(node);
    }
  }
  return node;
};
pp$5.parseYield = function(forInit) {
  if (!this.yieldPos) {
    this.yieldPos = this.start;
  }
  var node = this.startNode();
  this.next();
  if (this.type === types$1.semi || this.canInsertSemicolon() || this.type !== types$1.star && !this.type.startsExpr) {
    node.delegate = false;
    node.argument = null;
  } else {
    node.delegate = this.eat(types$1.star);
    node.argument = this.parseMaybeAssign(forInit);
  }
  return this.finishNode(node, "YieldExpression");
};
pp$5.parseAwait = function(forInit) {
  if (!this.awaitPos) {
    this.awaitPos = this.start;
  }
  var node = this.startNode();
  this.next();
  node.argument = this.parseMaybeUnary(null, true, false, forInit);
  return this.finishNode(node, "AwaitExpression");
};
var pp$4 = Parser.prototype;
pp$4.raise = function(pos, message) {
  var loc = getLineInfo(this.input, pos);
  message += " (" + loc.line + ":" + loc.column + ")";
  if (this.sourceFile) {
    message += " in " + this.sourceFile;
  }
  var err = new SyntaxError(message);
  err.pos = pos;
  err.loc = loc;
  err.raisedAt = this.pos;
  throw err;
};
pp$4.raiseRecoverable = pp$4.raise;
pp$4.curPosition = function() {
  if (this.options.locations) {
    return new Position(this.curLine, this.pos - this.lineStart);
  }
};
var pp$3 = Parser.prototype;
var Scope = function Scope2(flags) {
  this.flags = flags;
  this.var = [];
  this.lexical = [];
  this.functions = [];
};
pp$3.enterScope = function(flags) {
  this.scopeStack.push(new Scope(flags));
};
pp$3.exitScope = function() {
  this.scopeStack.pop();
};
pp$3.treatFunctionsAsVarInScope = function(scope) {
  return scope.flags & SCOPE_FUNCTION || !this.inModule && scope.flags & SCOPE_TOP;
};
pp$3.declareName = function(name2, bindingType, pos) {
  var redeclared = false;
  if (bindingType === BIND_LEXICAL) {
    var scope = this.currentScope();
    redeclared = scope.lexical.indexOf(name2) > -1 || scope.functions.indexOf(name2) > -1 || scope.var.indexOf(name2) > -1;
    scope.lexical.push(name2);
    if (this.inModule && scope.flags & SCOPE_TOP) {
      delete this.undefinedExports[name2];
    }
  } else if (bindingType === BIND_SIMPLE_CATCH) {
    var scope$1 = this.currentScope();
    scope$1.lexical.push(name2);
  } else if (bindingType === BIND_FUNCTION) {
    var scope$2 = this.currentScope();
    if (this.treatFunctionsAsVar) {
      redeclared = scope$2.lexical.indexOf(name2) > -1;
    } else {
      redeclared = scope$2.lexical.indexOf(name2) > -1 || scope$2.var.indexOf(name2) > -1;
    }
    scope$2.functions.push(name2);
  } else {
    for (var i = this.scopeStack.length - 1; i >= 0; --i) {
      var scope$3 = this.scopeStack[i];
      if (scope$3.lexical.indexOf(name2) > -1 && !(scope$3.flags & SCOPE_SIMPLE_CATCH && scope$3.lexical[0] === name2) || !this.treatFunctionsAsVarInScope(scope$3) && scope$3.functions.indexOf(name2) > -1) {
        redeclared = true;
        break;
      }
      scope$3.var.push(name2);
      if (this.inModule && scope$3.flags & SCOPE_TOP) {
        delete this.undefinedExports[name2];
      }
      if (scope$3.flags & SCOPE_VAR) {
        break;
      }
    }
  }
  if (redeclared) {
    this.raiseRecoverable(pos, "Identifier '" + name2 + "' has already been declared");
  }
};
pp$3.checkLocalExport = function(id) {
  if (this.scopeStack[0].lexical.indexOf(id.name) === -1 && this.scopeStack[0].var.indexOf(id.name) === -1) {
    this.undefinedExports[id.name] = id;
  }
};
pp$3.currentScope = function() {
  return this.scopeStack[this.scopeStack.length - 1];
};
pp$3.currentVarScope = function() {
  for (var i = this.scopeStack.length - 1; ; i--) {
    var scope = this.scopeStack[i];
    if (scope.flags & (SCOPE_VAR | SCOPE_CLASS_FIELD_INIT | SCOPE_CLASS_STATIC_BLOCK)) {
      return scope;
    }
  }
};
pp$3.currentThisScope = function() {
  for (var i = this.scopeStack.length - 1; ; i--) {
    var scope = this.scopeStack[i];
    if (scope.flags & (SCOPE_VAR | SCOPE_CLASS_FIELD_INIT | SCOPE_CLASS_STATIC_BLOCK) && !(scope.flags & SCOPE_ARROW)) {
      return scope;
    }
  }
};
var Node = function Node2(parser, pos, loc) {
  this.type = "";
  this.start = pos;
  this.end = 0;
  if (parser.options.locations) {
    this.loc = new SourceLocation(parser, loc);
  }
  if (parser.options.directSourceFile) {
    this.sourceFile = parser.options.directSourceFile;
  }
  if (parser.options.ranges) {
    this.range = [pos, 0];
  }
};
var pp$2 = Parser.prototype;
pp$2.startNode = function() {
  return new Node(this, this.start, this.startLoc);
};
pp$2.startNodeAt = function(pos, loc) {
  return new Node(this, pos, loc);
};
function finishNodeAt(node, type, pos, loc) {
  node.type = type;
  node.end = pos;
  if (this.options.locations) {
    node.loc.end = loc;
  }
  if (this.options.ranges) {
    node.range[1] = pos;
  }
  return node;
}
pp$2.finishNode = function(node, type) {
  return finishNodeAt.call(this, node, type, this.lastTokEnd, this.lastTokEndLoc);
};
pp$2.finishNodeAt = function(node, type, pos, loc) {
  return finishNodeAt.call(this, node, type, pos, loc);
};
pp$2.copyNode = function(node) {
  var newNode = new Node(this, node.start, this.startLoc);
  for (var prop in node) {
    newNode[prop] = node[prop];
  }
  return newNode;
};
var scriptValuesAddedInUnicode = "Gara Garay Gukh Gurung_Khema Hrkt Katakana_Or_Hiragana Kawi Kirat_Rai Krai Nag_Mundari Nagm Ol_Onal Onao Sunu Sunuwar Todhri Todr Tulu_Tigalari Tutg Unknown Zzzz";
var ecma9BinaryProperties = "ASCII ASCII_Hex_Digit AHex Alphabetic Alpha Any Assigned Bidi_Control Bidi_C Bidi_Mirrored Bidi_M Case_Ignorable CI Cased Changes_When_Casefolded CWCF Changes_When_Casemapped CWCM Changes_When_Lowercased CWL Changes_When_NFKC_Casefolded CWKCF Changes_When_Titlecased CWT Changes_When_Uppercased CWU Dash Default_Ignorable_Code_Point DI Deprecated Dep Diacritic Dia Emoji Emoji_Component Emoji_Modifier Emoji_Modifier_Base Emoji_Presentation Extender Ext Grapheme_Base Gr_Base Grapheme_Extend Gr_Ext Hex_Digit Hex IDS_Binary_Operator IDSB IDS_Trinary_Operator IDST ID_Continue IDC ID_Start IDS Ideographic Ideo Join_Control Join_C Logical_Order_Exception LOE Lowercase Lower Math Noncharacter_Code_Point NChar Pattern_Syntax Pat_Syn Pattern_White_Space Pat_WS Quotation_Mark QMark Radical Regional_Indicator RI Sentence_Terminal STerm Soft_Dotted SD Terminal_Punctuation Term Unified_Ideograph UIdeo Uppercase Upper Variation_Selector VS White_Space space XID_Continue XIDC XID_Start XIDS";
var ecma10BinaryProperties = ecma9BinaryProperties + " Extended_Pictographic";
var ecma11BinaryProperties = ecma10BinaryProperties;
var ecma12BinaryProperties = ecma11BinaryProperties + " EBase EComp EMod EPres ExtPict";
var ecma13BinaryProperties = ecma12BinaryProperties;
var ecma14BinaryProperties = ecma13BinaryProperties;
var unicodeBinaryProperties = {
  9: ecma9BinaryProperties,
  10: ecma10BinaryProperties,
  11: ecma11BinaryProperties,
  12: ecma12BinaryProperties,
  13: ecma13BinaryProperties,
  14: ecma14BinaryProperties
};
var ecma14BinaryPropertiesOfStrings = "Basic_Emoji Emoji_Keycap_Sequence RGI_Emoji_Modifier_Sequence RGI_Emoji_Flag_Sequence RGI_Emoji_Tag_Sequence RGI_Emoji_ZWJ_Sequence RGI_Emoji";
var unicodeBinaryPropertiesOfStrings = {
  9: "",
  10: "",
  11: "",
  12: "",
  13: "",
  14: ecma14BinaryPropertiesOfStrings
};
var unicodeGeneralCategoryValues = "Cased_Letter LC Close_Punctuation Pe Connector_Punctuation Pc Control Cc cntrl Currency_Symbol Sc Dash_Punctuation Pd Decimal_Number Nd digit Enclosing_Mark Me Final_Punctuation Pf Format Cf Initial_Punctuation Pi Letter L Letter_Number Nl Line_Separator Zl Lowercase_Letter Ll Mark M Combining_Mark Math_Symbol Sm Modifier_Letter Lm Modifier_Symbol Sk Nonspacing_Mark Mn Number N Open_Punctuation Ps Other C Other_Letter Lo Other_Number No Other_Punctuation Po Other_Symbol So Paragraph_Separator Zp Private_Use Co Punctuation P punct Separator Z Space_Separator Zs Spacing_Mark Mc Surrogate Cs Symbol S Titlecase_Letter Lt Unassigned Cn Uppercase_Letter Lu";
var ecma9ScriptValues = "Adlam Adlm Ahom Anatolian_Hieroglyphs Hluw Arabic Arab Armenian Armn Avestan Avst Balinese Bali Bamum Bamu Bassa_Vah Bass Batak Batk Bengali Beng Bhaiksuki Bhks Bopomofo Bopo Brahmi Brah Braille Brai Buginese Bugi Buhid Buhd Canadian_Aboriginal Cans Carian Cari Caucasian_Albanian Aghb Chakma Cakm Cham Cham Cherokee Cher Common Zyyy Coptic Copt Qaac Cuneiform Xsux Cypriot Cprt Cyrillic Cyrl Deseret Dsrt Devanagari Deva Duployan Dupl Egyptian_Hieroglyphs Egyp Elbasan Elba Ethiopic Ethi Georgian Geor Glagolitic Glag Gothic Goth Grantha Gran Greek Grek Gujarati Gujr Gurmukhi Guru Han Hani Hangul Hang Hanunoo Hano Hatran Hatr Hebrew Hebr Hiragana Hira Imperial_Aramaic Armi Inherited Zinh Qaai Inscriptional_Pahlavi Phli Inscriptional_Parthian Prti Javanese Java Kaithi Kthi Kannada Knda Katakana Kana Kayah_Li Kali Kharoshthi Khar Khmer Khmr Khojki Khoj Khudawadi Sind Lao Laoo Latin Latn Lepcha Lepc Limbu Limb Linear_A Lina Linear_B Linb Lisu Lisu Lycian Lyci Lydian Lydi Mahajani Mahj Malayalam Mlym Mandaic Mand Manichaean Mani Marchen Marc Masaram_Gondi Gonm Meetei_Mayek Mtei Mende_Kikakui Mend Meroitic_Cursive Merc Meroitic_Hieroglyphs Mero Miao Plrd Modi Mongolian Mong Mro Mroo Multani Mult Myanmar Mymr Nabataean Nbat New_Tai_Lue Talu Newa Newa Nko Nkoo Nushu Nshu Ogham Ogam Ol_Chiki Olck Old_Hungarian Hung Old_Italic Ital Old_North_Arabian Narb Old_Permic Perm Old_Persian Xpeo Old_South_Arabian Sarb Old_Turkic Orkh Oriya Orya Osage Osge Osmanya Osma Pahawh_Hmong Hmng Palmyrene Palm Pau_Cin_Hau Pauc Phags_Pa Phag Phoenician Phnx Psalter_Pahlavi Phlp Rejang Rjng Runic Runr Samaritan Samr Saurashtra Saur Sharada Shrd Shavian Shaw Siddham Sidd SignWriting Sgnw Sinhala Sinh Sora_Sompeng Sora Soyombo Soyo Sundanese Sund Syloti_Nagri Sylo Syriac Syrc Tagalog Tglg Tagbanwa Tagb Tai_Le Tale Tai_Tham Lana Tai_Viet Tavt Takri Takr Tamil Taml Tangut Tang Telugu Telu Thaana Thaa Thai Thai Tibetan Tibt Tifinagh Tfng Tirhuta Tirh Ugaritic Ugar Vai Vaii Warang_Citi Wara Yi Yiii Zanabazar_Square Zanb";
var ecma10ScriptValues = ecma9ScriptValues + " Dogra Dogr Gunjala_Gondi Gong Hanifi_Rohingya Rohg Makasar Maka Medefaidrin Medf Old_Sogdian Sogo Sogdian Sogd";
var ecma11ScriptValues = ecma10ScriptValues + " Elymaic Elym Nandinagari Nand Nyiakeng_Puachue_Hmong Hmnp Wancho Wcho";
var ecma12ScriptValues = ecma11ScriptValues + " Chorasmian Chrs Diak Dives_Akuru Khitan_Small_Script Kits Yezi Yezidi";
var ecma13ScriptValues = ecma12ScriptValues + " Cypro_Minoan Cpmn Old_Uyghur Ougr Tangsa Tnsa Toto Vithkuqi Vith";
var ecma14ScriptValues = ecma13ScriptValues + " " + scriptValuesAddedInUnicode;
var unicodeScriptValues = {
  9: ecma9ScriptValues,
  10: ecma10ScriptValues,
  11: ecma11ScriptValues,
  12: ecma12ScriptValues,
  13: ecma13ScriptValues,
  14: ecma14ScriptValues
};
var data = {};
function buildUnicodeData(ecmaVersion) {
  var d = data[ecmaVersion] = {
    binary: wordsRegexp(unicodeBinaryProperties[ecmaVersion] + " " + unicodeGeneralCategoryValues),
    binaryOfStrings: wordsRegexp(unicodeBinaryPropertiesOfStrings[ecmaVersion]),
    nonBinary: {
      General_Category: wordsRegexp(unicodeGeneralCategoryValues),
      Script: wordsRegexp(unicodeScriptValues[ecmaVersion])
    }
  };
  d.nonBinary.Script_Extensions = d.nonBinary.Script;
  d.nonBinary.gc = d.nonBinary.General_Category;
  d.nonBinary.sc = d.nonBinary.Script;
  d.nonBinary.scx = d.nonBinary.Script_Extensions;
}
for (var i = 0, list$1 = [9, 10, 11, 12, 13, 14]; i < list$1.length; i += 1) {
  var ecmaVersion = list$1[i];
  buildUnicodeData(ecmaVersion);
}
var pp$1 = Parser.prototype;
var BranchID = function BranchID2(parent, base) {
  this.parent = parent;
  this.base = base || this;
};
BranchID.prototype.separatedFrom = function separatedFrom(alt) {
  for (var self = this; self; self = self.parent) {
    for (var other = alt; other; other = other.parent) {
      if (self.base === other.base && self !== other) {
        return true;
      }
    }
  }
  return false;
};
BranchID.prototype.sibling = function sibling() {
  return new BranchID(this.parent, this.base);
};
var RegExpValidationState = function RegExpValidationState2(parser) {
  this.parser = parser;
  this.validFlags = "gim" + (parser.options.ecmaVersion >= 6 ? "uy" : "") + (parser.options.ecmaVersion >= 9 ? "s" : "") + (parser.options.ecmaVersion >= 13 ? "d" : "") + (parser.options.ecmaVersion >= 15 ? "v" : "");
  this.unicodeProperties = data[parser.options.ecmaVersion >= 14 ? 14 : parser.options.ecmaVersion];
  this.source = "";
  this.flags = "";
  this.start = 0;
  this.switchU = false;
  this.switchV = false;
  this.switchN = false;
  this.pos = 0;
  this.lastIntValue = 0;
  this.lastStringValue = "";
  this.lastAssertionIsQuantifiable = false;
  this.numCapturingParens = 0;
  this.maxBackReference = 0;
  this.groupNames = /* @__PURE__ */ Object.create(null);
  this.backReferenceNames = [];
  this.branchID = null;
};
RegExpValidationState.prototype.reset = function reset(start, pattern, flags) {
  var unicodeSets = flags.indexOf("v") !== -1;
  var unicode = flags.indexOf("u") !== -1;
  this.start = start | 0;
  this.source = pattern + "";
  this.flags = flags;
  if (unicodeSets && this.parser.options.ecmaVersion >= 15) {
    this.switchU = true;
    this.switchV = true;
    this.switchN = true;
  } else {
    this.switchU = unicode && this.parser.options.ecmaVersion >= 6;
    this.switchV = false;
    this.switchN = unicode && this.parser.options.ecmaVersion >= 9;
  }
};
RegExpValidationState.prototype.raise = function raise(message) {
  this.parser.raiseRecoverable(this.start, "Invalid regular expression: /" + this.source + "/: " + message);
};
RegExpValidationState.prototype.at = function at(i, forceU) {
  if (forceU === void 0) forceU = false;
  var s = this.source;
  var l = s.length;
  if (i >= l) {
    return -1;
  }
  var c = s.charCodeAt(i);
  if (!(forceU || this.switchU) || c <= 55295 || c >= 57344 || i + 1 >= l) {
    return c;
  }
  var next = s.charCodeAt(i + 1);
  return next >= 56320 && next <= 57343 ? (c << 10) + next - 56613888 : c;
};
RegExpValidationState.prototype.nextIndex = function nextIndex(i, forceU) {
  if (forceU === void 0) forceU = false;
  var s = this.source;
  var l = s.length;
  if (i >= l) {
    return l;
  }
  var c = s.charCodeAt(i), next;
  if (!(forceU || this.switchU) || c <= 55295 || c >= 57344 || i + 1 >= l || (next = s.charCodeAt(i + 1)) < 56320 || next > 57343) {
    return i + 1;
  }
  return i + 2;
};
RegExpValidationState.prototype.current = function current(forceU) {
  if (forceU === void 0) forceU = false;
  return this.at(this.pos, forceU);
};
RegExpValidationState.prototype.lookahead = function lookahead(forceU) {
  if (forceU === void 0) forceU = false;
  return this.at(this.nextIndex(this.pos, forceU), forceU);
};
RegExpValidationState.prototype.advance = function advance(forceU) {
  if (forceU === void 0) forceU = false;
  this.pos = this.nextIndex(this.pos, forceU);
};
RegExpValidationState.prototype.eat = function eat(ch, forceU) {
  if (forceU === void 0) forceU = false;
  if (this.current(forceU) === ch) {
    this.advance(forceU);
    return true;
  }
  return false;
};
RegExpValidationState.prototype.eatChars = function eatChars(chs, forceU) {
  if (forceU === void 0) forceU = false;
  var pos = this.pos;
  for (var i = 0, list2 = chs; i < list2.length; i += 1) {
    var ch = list2[i];
    var current2 = this.at(pos, forceU);
    if (current2 === -1 || current2 !== ch) {
      return false;
    }
    pos = this.nextIndex(pos, forceU);
  }
  this.pos = pos;
  return true;
};
pp$1.validateRegExpFlags = function(state) {
  var validFlags = state.validFlags;
  var flags = state.flags;
  var u = false;
  var v = false;
  for (var i = 0; i < flags.length; i++) {
    var flag = flags.charAt(i);
    if (validFlags.indexOf(flag) === -1) {
      this.raise(state.start, "Invalid regular expression flag");
    }
    if (flags.indexOf(flag, i + 1) > -1) {
      this.raise(state.start, "Duplicate regular expression flag");
    }
    if (flag === "u") {
      u = true;
    }
    if (flag === "v") {
      v = true;
    }
  }
  if (this.options.ecmaVersion >= 15 && u && v) {
    this.raise(state.start, "Invalid regular expression flag");
  }
};
function hasProp(obj) {
  for (var _ in obj) {
    return true;
  }
  return false;
}
pp$1.validateRegExpPattern = function(state) {
  this.regexp_pattern(state);
  if (!state.switchN && this.options.ecmaVersion >= 9 && hasProp(state.groupNames)) {
    state.switchN = true;
    this.regexp_pattern(state);
  }
};
pp$1.regexp_pattern = function(state) {
  state.pos = 0;
  state.lastIntValue = 0;
  state.lastStringValue = "";
  state.lastAssertionIsQuantifiable = false;
  state.numCapturingParens = 0;
  state.maxBackReference = 0;
  state.groupNames = /* @__PURE__ */ Object.create(null);
  state.backReferenceNames.length = 0;
  state.branchID = null;
  this.regexp_disjunction(state);
  if (state.pos !== state.source.length) {
    if (state.eat(
      41
      /* ) */
    )) {
      state.raise("Unmatched ')'");
    }
    if (state.eat(
      93
      /* ] */
    ) || state.eat(
      125
      /* } */
    )) {
      state.raise("Lone quantifier brackets");
    }
  }
  if (state.maxBackReference > state.numCapturingParens) {
    state.raise("Invalid escape");
  }
  for (var i = 0, list2 = state.backReferenceNames; i < list2.length; i += 1) {
    var name2 = list2[i];
    if (!state.groupNames[name2]) {
      state.raise("Invalid named capture referenced");
    }
  }
};
pp$1.regexp_disjunction = function(state) {
  var trackDisjunction = this.options.ecmaVersion >= 16;
  if (trackDisjunction) {
    state.branchID = new BranchID(state.branchID, null);
  }
  this.regexp_alternative(state);
  while (state.eat(
    124
    /* | */
  )) {
    if (trackDisjunction) {
      state.branchID = state.branchID.sibling();
    }
    this.regexp_alternative(state);
  }
  if (trackDisjunction) {
    state.branchID = state.branchID.parent;
  }
  if (this.regexp_eatQuantifier(state, true)) {
    state.raise("Nothing to repeat");
  }
  if (state.eat(
    123
    /* { */
  )) {
    state.raise("Lone quantifier brackets");
  }
};
pp$1.regexp_alternative = function(state) {
  while (state.pos < state.source.length && this.regexp_eatTerm(state)) {
  }
};
pp$1.regexp_eatTerm = function(state) {
  if (this.regexp_eatAssertion(state)) {
    if (state.lastAssertionIsQuantifiable && this.regexp_eatQuantifier(state)) {
      if (state.switchU) {
        state.raise("Invalid quantifier");
      }
    }
    return true;
  }
  if (state.switchU ? this.regexp_eatAtom(state) : this.regexp_eatExtendedAtom(state)) {
    this.regexp_eatQuantifier(state);
    return true;
  }
  return false;
};
pp$1.regexp_eatAssertion = function(state) {
  var start = state.pos;
  state.lastAssertionIsQuantifiable = false;
  if (state.eat(
    94
    /* ^ */
  ) || state.eat(
    36
    /* $ */
  )) {
    return true;
  }
  if (state.eat(
    92
    /* \ */
  )) {
    if (state.eat(
      66
      /* B */
    ) || state.eat(
      98
      /* b */
    )) {
      return true;
    }
    state.pos = start;
  }
  if (state.eat(
    40
    /* ( */
  ) && state.eat(
    63
    /* ? */
  )) {
    var lookbehind = false;
    if (this.options.ecmaVersion >= 9) {
      lookbehind = state.eat(
        60
        /* < */
      );
    }
    if (state.eat(
      61
      /* = */
    ) || state.eat(
      33
      /* ! */
    )) {
      this.regexp_disjunction(state);
      if (!state.eat(
        41
        /* ) */
      )) {
        state.raise("Unterminated group");
      }
      state.lastAssertionIsQuantifiable = !lookbehind;
      return true;
    }
  }
  state.pos = start;
  return false;
};
pp$1.regexp_eatQuantifier = function(state, noError) {
  if (noError === void 0) noError = false;
  if (this.regexp_eatQuantifierPrefix(state, noError)) {
    state.eat(
      63
      /* ? */
    );
    return true;
  }
  return false;
};
pp$1.regexp_eatQuantifierPrefix = function(state, noError) {
  return state.eat(
    42
    /* * */
  ) || state.eat(
    43
    /* + */
  ) || state.eat(
    63
    /* ? */
  ) || this.regexp_eatBracedQuantifier(state, noError);
};
pp$1.regexp_eatBracedQuantifier = function(state, noError) {
  var start = state.pos;
  if (state.eat(
    123
    /* { */
  )) {
    var min2 = 0, max2 = -1;
    if (this.regexp_eatDecimalDigits(state)) {
      min2 = state.lastIntValue;
      if (state.eat(
        44
        /* , */
      ) && this.regexp_eatDecimalDigits(state)) {
        max2 = state.lastIntValue;
      }
      if (state.eat(
        125
        /* } */
      )) {
        if (max2 !== -1 && max2 < min2 && !noError) {
          state.raise("numbers out of order in {} quantifier");
        }
        return true;
      }
    }
    if (state.switchU && !noError) {
      state.raise("Incomplete quantifier");
    }
    state.pos = start;
  }
  return false;
};
pp$1.regexp_eatAtom = function(state) {
  return this.regexp_eatPatternCharacters(state) || state.eat(
    46
    /* . */
  ) || this.regexp_eatReverseSolidusAtomEscape(state) || this.regexp_eatCharacterClass(state) || this.regexp_eatUncapturingGroup(state) || this.regexp_eatCapturingGroup(state);
};
pp$1.regexp_eatReverseSolidusAtomEscape = function(state) {
  var start = state.pos;
  if (state.eat(
    92
    /* \ */
  )) {
    if (this.regexp_eatAtomEscape(state)) {
      return true;
    }
    state.pos = start;
  }
  return false;
};
pp$1.regexp_eatUncapturingGroup = function(state) {
  var start = state.pos;
  if (state.eat(
    40
    /* ( */
  )) {
    if (state.eat(
      63
      /* ? */
    )) {
      if (this.options.ecmaVersion >= 16) {
        var addModifiers = this.regexp_eatModifiers(state);
        var hasHyphen = state.eat(
          45
          /* - */
        );
        if (addModifiers || hasHyphen) {
          for (var i = 0; i < addModifiers.length; i++) {
            var modifier = addModifiers.charAt(i);
            if (addModifiers.indexOf(modifier, i + 1) > -1) {
              state.raise("Duplicate regular expression modifiers");
            }
          }
          if (hasHyphen) {
            var removeModifiers = this.regexp_eatModifiers(state);
            if (!addModifiers && !removeModifiers && state.current() === 58) {
              state.raise("Invalid regular expression modifiers");
            }
            for (var i$1 = 0; i$1 < removeModifiers.length; i$1++) {
              var modifier$1 = removeModifiers.charAt(i$1);
              if (removeModifiers.indexOf(modifier$1, i$1 + 1) > -1 || addModifiers.indexOf(modifier$1) > -1) {
                state.raise("Duplicate regular expression modifiers");
              }
            }
          }
        }
      }
      if (state.eat(
        58
        /* : */
      )) {
        this.regexp_disjunction(state);
        if (state.eat(
          41
          /* ) */
        )) {
          return true;
        }
        state.raise("Unterminated group");
      }
    }
    state.pos = start;
  }
  return false;
};
pp$1.regexp_eatCapturingGroup = function(state) {
  if (state.eat(
    40
    /* ( */
  )) {
    if (this.options.ecmaVersion >= 9) {
      this.regexp_groupSpecifier(state);
    } else if (state.current() === 63) {
      state.raise("Invalid group");
    }
    this.regexp_disjunction(state);
    if (state.eat(
      41
      /* ) */
    )) {
      state.numCapturingParens += 1;
      return true;
    }
    state.raise("Unterminated group");
  }
  return false;
};
pp$1.regexp_eatModifiers = function(state) {
  var modifiers = "";
  var ch = 0;
  while ((ch = state.current()) !== -1 && isRegularExpressionModifier(ch)) {
    modifiers += codePointToString(ch);
    state.advance();
  }
  return modifiers;
};
function isRegularExpressionModifier(ch) {
  return ch === 105 || ch === 109 || ch === 115;
}
pp$1.regexp_eatExtendedAtom = function(state) {
  return state.eat(
    46
    /* . */
  ) || this.regexp_eatReverseSolidusAtomEscape(state) || this.regexp_eatCharacterClass(state) || this.regexp_eatUncapturingGroup(state) || this.regexp_eatCapturingGroup(state) || this.regexp_eatInvalidBracedQuantifier(state) || this.regexp_eatExtendedPatternCharacter(state);
};
pp$1.regexp_eatInvalidBracedQuantifier = function(state) {
  if (this.regexp_eatBracedQuantifier(state, true)) {
    state.raise("Nothing to repeat");
  }
  return false;
};
pp$1.regexp_eatSyntaxCharacter = function(state) {
  var ch = state.current();
  if (isSyntaxCharacter(ch)) {
    state.lastIntValue = ch;
    state.advance();
    return true;
  }
  return false;
};
function isSyntaxCharacter(ch) {
  return ch === 36 || ch >= 40 && ch <= 43 || ch === 46 || ch === 63 || ch >= 91 && ch <= 94 || ch >= 123 && ch <= 125;
}
pp$1.regexp_eatPatternCharacters = function(state) {
  var start = state.pos;
  var ch = 0;
  while ((ch = state.current()) !== -1 && !isSyntaxCharacter(ch)) {
    state.advance();
  }
  return state.pos !== start;
};
pp$1.regexp_eatExtendedPatternCharacter = function(state) {
  var ch = state.current();
  if (ch !== -1 && ch !== 36 && !(ch >= 40 && ch <= 43) && ch !== 46 && ch !== 63 && ch !== 91 && ch !== 94 && ch !== 124) {
    state.advance();
    return true;
  }
  return false;
};
pp$1.regexp_groupSpecifier = function(state) {
  if (state.eat(
    63
    /* ? */
  )) {
    if (!this.regexp_eatGroupName(state)) {
      state.raise("Invalid group");
    }
    var trackDisjunction = this.options.ecmaVersion >= 16;
    var known = state.groupNames[state.lastStringValue];
    if (known) {
      if (trackDisjunction) {
        for (var i = 0, list2 = known; i < list2.length; i += 1) {
          var altID = list2[i];
          if (!altID.separatedFrom(state.branchID)) {
            state.raise("Duplicate capture group name");
          }
        }
      } else {
        state.raise("Duplicate capture group name");
      }
    }
    if (trackDisjunction) {
      (known || (state.groupNames[state.lastStringValue] = [])).push(state.branchID);
    } else {
      state.groupNames[state.lastStringValue] = true;
    }
  }
};
pp$1.regexp_eatGroupName = function(state) {
  state.lastStringValue = "";
  if (state.eat(
    60
    /* < */
  )) {
    if (this.regexp_eatRegExpIdentifierName(state) && state.eat(
      62
      /* > */
    )) {
      return true;
    }
    state.raise("Invalid capture group name");
  }
  return false;
};
pp$1.regexp_eatRegExpIdentifierName = function(state) {
  state.lastStringValue = "";
  if (this.regexp_eatRegExpIdentifierStart(state)) {
    state.lastStringValue += codePointToString(state.lastIntValue);
    while (this.regexp_eatRegExpIdentifierPart(state)) {
      state.lastStringValue += codePointToString(state.lastIntValue);
    }
    return true;
  }
  return false;
};
pp$1.regexp_eatRegExpIdentifierStart = function(state) {
  var start = state.pos;
  var forceU = this.options.ecmaVersion >= 11;
  var ch = state.current(forceU);
  state.advance(forceU);
  if (ch === 92 && this.regexp_eatRegExpUnicodeEscapeSequence(state, forceU)) {
    ch = state.lastIntValue;
  }
  if (isRegExpIdentifierStart(ch)) {
    state.lastIntValue = ch;
    return true;
  }
  state.pos = start;
  return false;
};
function isRegExpIdentifierStart(ch) {
  return isIdentifierStart(ch, true) || ch === 36 || ch === 95;
}
pp$1.regexp_eatRegExpIdentifierPart = function(state) {
  var start = state.pos;
  var forceU = this.options.ecmaVersion >= 11;
  var ch = state.current(forceU);
  state.advance(forceU);
  if (ch === 92 && this.regexp_eatRegExpUnicodeEscapeSequence(state, forceU)) {
    ch = state.lastIntValue;
  }
  if (isRegExpIdentifierPart(ch)) {
    state.lastIntValue = ch;
    return true;
  }
  state.pos = start;
  return false;
};
function isRegExpIdentifierPart(ch) {
  return isIdentifierChar(ch, true) || ch === 36 || ch === 95 || ch === 8204 || ch === 8205;
}
pp$1.regexp_eatAtomEscape = function(state) {
  if (this.regexp_eatBackReference(state) || this.regexp_eatCharacterClassEscape(state) || this.regexp_eatCharacterEscape(state) || state.switchN && this.regexp_eatKGroupName(state)) {
    return true;
  }
  if (state.switchU) {
    if (state.current() === 99) {
      state.raise("Invalid unicode escape");
    }
    state.raise("Invalid escape");
  }
  return false;
};
pp$1.regexp_eatBackReference = function(state) {
  var start = state.pos;
  if (this.regexp_eatDecimalEscape(state)) {
    var n = state.lastIntValue;
    if (state.switchU) {
      if (n > state.maxBackReference) {
        state.maxBackReference = n;
      }
      return true;
    }
    if (n <= state.numCapturingParens) {
      return true;
    }
    state.pos = start;
  }
  return false;
};
pp$1.regexp_eatKGroupName = function(state) {
  if (state.eat(
    107
    /* k */
  )) {
    if (this.regexp_eatGroupName(state)) {
      state.backReferenceNames.push(state.lastStringValue);
      return true;
    }
    state.raise("Invalid named reference");
  }
  return false;
};
pp$1.regexp_eatCharacterEscape = function(state) {
  return this.regexp_eatControlEscape(state) || this.regexp_eatCControlLetter(state) || this.regexp_eatZero(state) || this.regexp_eatHexEscapeSequence(state) || this.regexp_eatRegExpUnicodeEscapeSequence(state, false) || !state.switchU && this.regexp_eatLegacyOctalEscapeSequence(state) || this.regexp_eatIdentityEscape(state);
};
pp$1.regexp_eatCControlLetter = function(state) {
  var start = state.pos;
  if (state.eat(
    99
    /* c */
  )) {
    if (this.regexp_eatControlLetter(state)) {
      return true;
    }
    state.pos = start;
  }
  return false;
};
pp$1.regexp_eatZero = function(state) {
  if (state.current() === 48 && !isDecimalDigit(state.lookahead())) {
    state.lastIntValue = 0;
    state.advance();
    return true;
  }
  return false;
};
pp$1.regexp_eatControlEscape = function(state) {
  var ch = state.current();
  if (ch === 116) {
    state.lastIntValue = 9;
    state.advance();
    return true;
  }
  if (ch === 110) {
    state.lastIntValue = 10;
    state.advance();
    return true;
  }
  if (ch === 118) {
    state.lastIntValue = 11;
    state.advance();
    return true;
  }
  if (ch === 102) {
    state.lastIntValue = 12;
    state.advance();
    return true;
  }
  if (ch === 114) {
    state.lastIntValue = 13;
    state.advance();
    return true;
  }
  return false;
};
pp$1.regexp_eatControlLetter = function(state) {
  var ch = state.current();
  if (isControlLetter(ch)) {
    state.lastIntValue = ch % 32;
    state.advance();
    return true;
  }
  return false;
};
function isControlLetter(ch) {
  return ch >= 65 && ch <= 90 || ch >= 97 && ch <= 122;
}
pp$1.regexp_eatRegExpUnicodeEscapeSequence = function(state, forceU) {
  if (forceU === void 0) forceU = false;
  var start = state.pos;
  var switchU = forceU || state.switchU;
  if (state.eat(
    117
    /* u */
  )) {
    if (this.regexp_eatFixedHexDigits(state, 4)) {
      var lead = state.lastIntValue;
      if (switchU && lead >= 55296 && lead <= 56319) {
        var leadSurrogateEnd = state.pos;
        if (state.eat(
          92
          /* \ */
        ) && state.eat(
          117
          /* u */
        ) && this.regexp_eatFixedHexDigits(state, 4)) {
          var trail = state.lastIntValue;
          if (trail >= 56320 && trail <= 57343) {
            state.lastIntValue = (lead - 55296) * 1024 + (trail - 56320) + 65536;
            return true;
          }
        }
        state.pos = leadSurrogateEnd;
        state.lastIntValue = lead;
      }
      return true;
    }
    if (switchU && state.eat(
      123
      /* { */
    ) && this.regexp_eatHexDigits(state) && state.eat(
      125
      /* } */
    ) && isValidUnicode(state.lastIntValue)) {
      return true;
    }
    if (switchU) {
      state.raise("Invalid unicode escape");
    }
    state.pos = start;
  }
  return false;
};
function isValidUnicode(ch) {
  return ch >= 0 && ch <= 1114111;
}
pp$1.regexp_eatIdentityEscape = function(state) {
  if (state.switchU) {
    if (this.regexp_eatSyntaxCharacter(state)) {
      return true;
    }
    if (state.eat(
      47
      /* / */
    )) {
      state.lastIntValue = 47;
      return true;
    }
    return false;
  }
  var ch = state.current();
  if (ch !== 99 && (!state.switchN || ch !== 107)) {
    state.lastIntValue = ch;
    state.advance();
    return true;
  }
  return false;
};
pp$1.regexp_eatDecimalEscape = function(state) {
  state.lastIntValue = 0;
  var ch = state.current();
  if (ch >= 49 && ch <= 57) {
    do {
      state.lastIntValue = 10 * state.lastIntValue + (ch - 48);
      state.advance();
    } while ((ch = state.current()) >= 48 && ch <= 57);
    return true;
  }
  return false;
};
var CharSetNone = 0;
var CharSetOk = 1;
var CharSetString = 2;
pp$1.regexp_eatCharacterClassEscape = function(state) {
  var ch = state.current();
  if (isCharacterClassEscape(ch)) {
    state.lastIntValue = -1;
    state.advance();
    return CharSetOk;
  }
  var negate = false;
  if (state.switchU && this.options.ecmaVersion >= 9 && ((negate = ch === 80) || ch === 112)) {
    state.lastIntValue = -1;
    state.advance();
    var result2;
    if (state.eat(
      123
      /* { */
    ) && (result2 = this.regexp_eatUnicodePropertyValueExpression(state)) && state.eat(
      125
      /* } */
    )) {
      if (negate && result2 === CharSetString) {
        state.raise("Invalid property name");
      }
      return result2;
    }
    state.raise("Invalid property name");
  }
  return CharSetNone;
};
function isCharacterClassEscape(ch) {
  return ch === 100 || ch === 68 || ch === 115 || ch === 83 || ch === 119 || ch === 87;
}
pp$1.regexp_eatUnicodePropertyValueExpression = function(state) {
  var start = state.pos;
  if (this.regexp_eatUnicodePropertyName(state) && state.eat(
    61
    /* = */
  )) {
    var name2 = state.lastStringValue;
    if (this.regexp_eatUnicodePropertyValue(state)) {
      var value2 = state.lastStringValue;
      this.regexp_validateUnicodePropertyNameAndValue(state, name2, value2);
      return CharSetOk;
    }
  }
  state.pos = start;
  if (this.regexp_eatLoneUnicodePropertyNameOrValue(state)) {
    var nameOrValue = state.lastStringValue;
    return this.regexp_validateUnicodePropertyNameOrValue(state, nameOrValue);
  }
  return CharSetNone;
};
pp$1.regexp_validateUnicodePropertyNameAndValue = function(state, name2, value2) {
  if (!hasOwn(state.unicodeProperties.nonBinary, name2)) {
    state.raise("Invalid property name");
  }
  if (!state.unicodeProperties.nonBinary[name2].test(value2)) {
    state.raise("Invalid property value");
  }
};
pp$1.regexp_validateUnicodePropertyNameOrValue = function(state, nameOrValue) {
  if (state.unicodeProperties.binary.test(nameOrValue)) {
    return CharSetOk;
  }
  if (state.switchV && state.unicodeProperties.binaryOfStrings.test(nameOrValue)) {
    return CharSetString;
  }
  state.raise("Invalid property name");
};
pp$1.regexp_eatUnicodePropertyName = function(state) {
  var ch = 0;
  state.lastStringValue = "";
  while (isUnicodePropertyNameCharacter(ch = state.current())) {
    state.lastStringValue += codePointToString(ch);
    state.advance();
  }
  return state.lastStringValue !== "";
};
function isUnicodePropertyNameCharacter(ch) {
  return isControlLetter(ch) || ch === 95;
}
pp$1.regexp_eatUnicodePropertyValue = function(state) {
  var ch = 0;
  state.lastStringValue = "";
  while (isUnicodePropertyValueCharacter(ch = state.current())) {
    state.lastStringValue += codePointToString(ch);
    state.advance();
  }
  return state.lastStringValue !== "";
};
function isUnicodePropertyValueCharacter(ch) {
  return isUnicodePropertyNameCharacter(ch) || isDecimalDigit(ch);
}
pp$1.regexp_eatLoneUnicodePropertyNameOrValue = function(state) {
  return this.regexp_eatUnicodePropertyValue(state);
};
pp$1.regexp_eatCharacterClass = function(state) {
  if (state.eat(
    91
    /* [ */
  )) {
    var negate = state.eat(
      94
      /* ^ */
    );
    var result2 = this.regexp_classContents(state);
    if (!state.eat(
      93
      /* ] */
    )) {
      state.raise("Unterminated character class");
    }
    if (negate && result2 === CharSetString) {
      state.raise("Negated character class may contain strings");
    }
    return true;
  }
  return false;
};
pp$1.regexp_classContents = function(state) {
  if (state.current() === 93) {
    return CharSetOk;
  }
  if (state.switchV) {
    return this.regexp_classSetExpression(state);
  }
  this.regexp_nonEmptyClassRanges(state);
  return CharSetOk;
};
pp$1.regexp_nonEmptyClassRanges = function(state) {
  while (this.regexp_eatClassAtom(state)) {
    var left = state.lastIntValue;
    if (state.eat(
      45
      /* - */
    ) && this.regexp_eatClassAtom(state)) {
      var right = state.lastIntValue;
      if (state.switchU && (left === -1 || right === -1)) {
        state.raise("Invalid character class");
      }
      if (left !== -1 && right !== -1 && left > right) {
        state.raise("Range out of order in character class");
      }
    }
  }
};
pp$1.regexp_eatClassAtom = function(state) {
  var start = state.pos;
  if (state.eat(
    92
    /* \ */
  )) {
    if (this.regexp_eatClassEscape(state)) {
      return true;
    }
    if (state.switchU) {
      var ch$1 = state.current();
      if (ch$1 === 99 || isOctalDigit(ch$1)) {
        state.raise("Invalid class escape");
      }
      state.raise("Invalid escape");
    }
    state.pos = start;
  }
  var ch = state.current();
  if (ch !== 93) {
    state.lastIntValue = ch;
    state.advance();
    return true;
  }
  return false;
};
pp$1.regexp_eatClassEscape = function(state) {
  var start = state.pos;
  if (state.eat(
    98
    /* b */
  )) {
    state.lastIntValue = 8;
    return true;
  }
  if (state.switchU && state.eat(
    45
    /* - */
  )) {
    state.lastIntValue = 45;
    return true;
  }
  if (!state.switchU && state.eat(
    99
    /* c */
  )) {
    if (this.regexp_eatClassControlLetter(state)) {
      return true;
    }
    state.pos = start;
  }
  return this.regexp_eatCharacterClassEscape(state) || this.regexp_eatCharacterEscape(state);
};
pp$1.regexp_classSetExpression = function(state) {
  var result2 = CharSetOk, subResult;
  if (this.regexp_eatClassSetRange(state)) ;
  else if (subResult = this.regexp_eatClassSetOperand(state)) {
    if (subResult === CharSetString) {
      result2 = CharSetString;
    }
    var start = state.pos;
    while (state.eatChars(
      [38, 38]
      /* && */
    )) {
      if (state.current() !== 38 && (subResult = this.regexp_eatClassSetOperand(state))) {
        if (subResult !== CharSetString) {
          result2 = CharSetOk;
        }
        continue;
      }
      state.raise("Invalid character in character class");
    }
    if (start !== state.pos) {
      return result2;
    }
    while (state.eatChars(
      [45, 45]
      /* -- */
    )) {
      if (this.regexp_eatClassSetOperand(state)) {
        continue;
      }
      state.raise("Invalid character in character class");
    }
    if (start !== state.pos) {
      return result2;
    }
  } else {
    state.raise("Invalid character in character class");
  }
  for (; ; ) {
    if (this.regexp_eatClassSetRange(state)) {
      continue;
    }
    subResult = this.regexp_eatClassSetOperand(state);
    if (!subResult) {
      return result2;
    }
    if (subResult === CharSetString) {
      result2 = CharSetString;
    }
  }
};
pp$1.regexp_eatClassSetRange = function(state) {
  var start = state.pos;
  if (this.regexp_eatClassSetCharacter(state)) {
    var left = state.lastIntValue;
    if (state.eat(
      45
      /* - */
    ) && this.regexp_eatClassSetCharacter(state)) {
      var right = state.lastIntValue;
      if (left !== -1 && right !== -1 && left > right) {
        state.raise("Range out of order in character class");
      }
      return true;
    }
    state.pos = start;
  }
  return false;
};
pp$1.regexp_eatClassSetOperand = function(state) {
  if (this.regexp_eatClassSetCharacter(state)) {
    return CharSetOk;
  }
  return this.regexp_eatClassStringDisjunction(state) || this.regexp_eatNestedClass(state);
};
pp$1.regexp_eatNestedClass = function(state) {
  var start = state.pos;
  if (state.eat(
    91
    /* [ */
  )) {
    var negate = state.eat(
      94
      /* ^ */
    );
    var result2 = this.regexp_classContents(state);
    if (state.eat(
      93
      /* ] */
    )) {
      if (negate && result2 === CharSetString) {
        state.raise("Negated character class may contain strings");
      }
      return result2;
    }
    state.pos = start;
  }
  if (state.eat(
    92
    /* \ */
  )) {
    var result$1 = this.regexp_eatCharacterClassEscape(state);
    if (result$1) {
      return result$1;
    }
    state.pos = start;
  }
  return null;
};
pp$1.regexp_eatClassStringDisjunction = function(state) {
  var start = state.pos;
  if (state.eatChars(
    [92, 113]
    /* \q */
  )) {
    if (state.eat(
      123
      /* { */
    )) {
      var result2 = this.regexp_classStringDisjunctionContents(state);
      if (state.eat(
        125
        /* } */
      )) {
        return result2;
      }
    } else {
      state.raise("Invalid escape");
    }
    state.pos = start;
  }
  return null;
};
pp$1.regexp_classStringDisjunctionContents = function(state) {
  var result2 = this.regexp_classString(state);
  while (state.eat(
    124
    /* | */
  )) {
    if (this.regexp_classString(state) === CharSetString) {
      result2 = CharSetString;
    }
  }
  return result2;
};
pp$1.regexp_classString = function(state) {
  var count2 = 0;
  while (this.regexp_eatClassSetCharacter(state)) {
    count2++;
  }
  return count2 === 1 ? CharSetOk : CharSetString;
};
pp$1.regexp_eatClassSetCharacter = function(state) {
  var start = state.pos;
  if (state.eat(
    92
    /* \ */
  )) {
    if (this.regexp_eatCharacterEscape(state) || this.regexp_eatClassSetReservedPunctuator(state)) {
      return true;
    }
    if (state.eat(
      98
      /* b */
    )) {
      state.lastIntValue = 8;
      return true;
    }
    state.pos = start;
    return false;
  }
  var ch = state.current();
  if (ch < 0 || ch === state.lookahead() && isClassSetReservedDoublePunctuatorCharacter(ch)) {
    return false;
  }
  if (isClassSetSyntaxCharacter(ch)) {
    return false;
  }
  state.advance();
  state.lastIntValue = ch;
  return true;
};
function isClassSetReservedDoublePunctuatorCharacter(ch) {
  return ch === 33 || ch >= 35 && ch <= 38 || ch >= 42 && ch <= 44 || ch === 46 || ch >= 58 && ch <= 64 || ch === 94 || ch === 96 || ch === 126;
}
function isClassSetSyntaxCharacter(ch) {
  return ch === 40 || ch === 41 || ch === 45 || ch === 47 || ch >= 91 && ch <= 93 || ch >= 123 && ch <= 125;
}
pp$1.regexp_eatClassSetReservedPunctuator = function(state) {
  var ch = state.current();
  if (isClassSetReservedPunctuator(ch)) {
    state.lastIntValue = ch;
    state.advance();
    return true;
  }
  return false;
};
function isClassSetReservedPunctuator(ch) {
  return ch === 33 || ch === 35 || ch === 37 || ch === 38 || ch === 44 || ch === 45 || ch >= 58 && ch <= 62 || ch === 64 || ch === 96 || ch === 126;
}
pp$1.regexp_eatClassControlLetter = function(state) {
  var ch = state.current();
  if (isDecimalDigit(ch) || ch === 95) {
    state.lastIntValue = ch % 32;
    state.advance();
    return true;
  }
  return false;
};
pp$1.regexp_eatHexEscapeSequence = function(state) {
  var start = state.pos;
  if (state.eat(
    120
    /* x */
  )) {
    if (this.regexp_eatFixedHexDigits(state, 2)) {
      return true;
    }
    if (state.switchU) {
      state.raise("Invalid escape");
    }
    state.pos = start;
  }
  return false;
};
pp$1.regexp_eatDecimalDigits = function(state) {
  var start = state.pos;
  var ch = 0;
  state.lastIntValue = 0;
  while (isDecimalDigit(ch = state.current())) {
    state.lastIntValue = 10 * state.lastIntValue + (ch - 48);
    state.advance();
  }
  return state.pos !== start;
};
function isDecimalDigit(ch) {
  return ch >= 48 && ch <= 57;
}
pp$1.regexp_eatHexDigits = function(state) {
  var start = state.pos;
  var ch = 0;
  state.lastIntValue = 0;
  while (isHexDigit(ch = state.current())) {
    state.lastIntValue = 16 * state.lastIntValue + hexToInt(ch);
    state.advance();
  }
  return state.pos !== start;
};
function isHexDigit(ch) {
  return ch >= 48 && ch <= 57 || ch >= 65 && ch <= 70 || ch >= 97 && ch <= 102;
}
function hexToInt(ch) {
  if (ch >= 65 && ch <= 70) {
    return 10 + (ch - 65);
  }
  if (ch >= 97 && ch <= 102) {
    return 10 + (ch - 97);
  }
  return ch - 48;
}
pp$1.regexp_eatLegacyOctalEscapeSequence = function(state) {
  if (this.regexp_eatOctalDigit(state)) {
    var n1 = state.lastIntValue;
    if (this.regexp_eatOctalDigit(state)) {
      var n2 = state.lastIntValue;
      if (n1 <= 3 && this.regexp_eatOctalDigit(state)) {
        state.lastIntValue = n1 * 64 + n2 * 8 + state.lastIntValue;
      } else {
        state.lastIntValue = n1 * 8 + n2;
      }
    } else {
      state.lastIntValue = n1;
    }
    return true;
  }
  return false;
};
pp$1.regexp_eatOctalDigit = function(state) {
  var ch = state.current();
  if (isOctalDigit(ch)) {
    state.lastIntValue = ch - 48;
    state.advance();
    return true;
  }
  state.lastIntValue = 0;
  return false;
};
function isOctalDigit(ch) {
  return ch >= 48 && ch <= 55;
}
pp$1.regexp_eatFixedHexDigits = function(state, length2) {
  var start = state.pos;
  state.lastIntValue = 0;
  for (var i = 0; i < length2; ++i) {
    var ch = state.current();
    if (!isHexDigit(ch)) {
      state.pos = start;
      return false;
    }
    state.lastIntValue = 16 * state.lastIntValue + hexToInt(ch);
    state.advance();
  }
  return true;
};
var Token = function Token2(p) {
  this.type = p.type;
  this.value = p.value;
  this.start = p.start;
  this.end = p.end;
  if (p.options.locations) {
    this.loc = new SourceLocation(p, p.startLoc, p.endLoc);
  }
  if (p.options.ranges) {
    this.range = [p.start, p.end];
  }
};
var pp = Parser.prototype;
pp.next = function(ignoreEscapeSequenceInKeyword) {
  if (!ignoreEscapeSequenceInKeyword && this.type.keyword && this.containsEsc) {
    this.raiseRecoverable(this.start, "Escape sequence in keyword " + this.type.keyword);
  }
  if (this.options.onToken) {
    this.options.onToken(new Token(this));
  }
  this.lastTokEnd = this.end;
  this.lastTokStart = this.start;
  this.lastTokEndLoc = this.endLoc;
  this.lastTokStartLoc = this.startLoc;
  this.nextToken();
};
pp.getToken = function() {
  this.next();
  return new Token(this);
};
if (typeof Symbol !== "undefined") {
  pp[Symbol.iterator] = function() {
    var this$1$1 = this;
    return {
      next: function() {
        var token = this$1$1.getToken();
        return {
          done: token.type === types$1.eof,
          value: token
        };
      }
    };
  };
}
pp.nextToken = function() {
  var curContext = this.curContext();
  if (!curContext || !curContext.preserveSpace) {
    this.skipSpace();
  }
  this.start = this.pos;
  if (this.options.locations) {
    this.startLoc = this.curPosition();
  }
  if (this.pos >= this.input.length) {
    return this.finishToken(types$1.eof);
  }
  if (curContext.override) {
    return curContext.override(this);
  } else {
    this.readToken(this.fullCharCodeAtPos());
  }
};
pp.readToken = function(code) {
  if (isIdentifierStart(code, this.options.ecmaVersion >= 6) || code === 92) {
    return this.readWord();
  }
  return this.getTokenFromCode(code);
};
pp.fullCharCodeAtPos = function() {
  var code = this.input.charCodeAt(this.pos);
  if (code <= 55295 || code >= 56320) {
    return code;
  }
  var next = this.input.charCodeAt(this.pos + 1);
  return next <= 56319 || next >= 57344 ? code : (code << 10) + next - 56613888;
};
pp.skipBlockComment = function() {
  var startLoc = this.options.onComment && this.curPosition();
  var start = this.pos, end = this.input.indexOf("*/", this.pos += 2);
  if (end === -1) {
    this.raise(this.pos - 2, "Unterminated comment");
  }
  this.pos = end + 2;
  if (this.options.locations) {
    for (var nextBreak = void 0, pos = start; (nextBreak = nextLineBreak(this.input, pos, this.pos)) > -1; ) {
      ++this.curLine;
      pos = this.lineStart = nextBreak;
    }
  }
  if (this.options.onComment) {
    this.options.onComment(
      true,
      this.input.slice(start + 2, end),
      start,
      this.pos,
      startLoc,
      this.curPosition()
    );
  }
};
pp.skipLineComment = function(startSkip) {
  var start = this.pos;
  var startLoc = this.options.onComment && this.curPosition();
  var ch = this.input.charCodeAt(this.pos += startSkip);
  while (this.pos < this.input.length && !isNewLine(ch)) {
    ch = this.input.charCodeAt(++this.pos);
  }
  if (this.options.onComment) {
    this.options.onComment(
      false,
      this.input.slice(start + startSkip, this.pos),
      start,
      this.pos,
      startLoc,
      this.curPosition()
    );
  }
};
pp.skipSpace = function() {
  loop: while (this.pos < this.input.length) {
    var ch = this.input.charCodeAt(this.pos);
    switch (ch) {
      case 32:
      case 160:
        ++this.pos;
        break;
      case 13:
        if (this.input.charCodeAt(this.pos + 1) === 10) {
          ++this.pos;
        }
      case 10:
      case 8232:
      case 8233:
        ++this.pos;
        if (this.options.locations) {
          ++this.curLine;
          this.lineStart = this.pos;
        }
        break;
      case 47:
        switch (this.input.charCodeAt(this.pos + 1)) {
          case 42:
            this.skipBlockComment();
            break;
          case 47:
            this.skipLineComment(2);
            break;
          default:
            break loop;
        }
        break;
      default:
        if (ch > 8 && ch < 14 || ch >= 5760 && nonASCIIwhitespace.test(String.fromCharCode(ch))) {
          ++this.pos;
        } else {
          break loop;
        }
    }
  }
};
pp.finishToken = function(type, val) {
  this.end = this.pos;
  if (this.options.locations) {
    this.endLoc = this.curPosition();
  }
  var prevType = this.type;
  this.type = type;
  this.value = val;
  this.updateContext(prevType);
};
pp.readToken_dot = function() {
  var next = this.input.charCodeAt(this.pos + 1);
  if (next >= 48 && next <= 57) {
    return this.readNumber(true);
  }
  var next2 = this.input.charCodeAt(this.pos + 2);
  if (this.options.ecmaVersion >= 6 && next === 46 && next2 === 46) {
    this.pos += 3;
    return this.finishToken(types$1.ellipsis);
  } else {
    ++this.pos;
    return this.finishToken(types$1.dot);
  }
};
pp.readToken_slash = function() {
  var next = this.input.charCodeAt(this.pos + 1);
  if (this.exprAllowed) {
    ++this.pos;
    return this.readRegexp();
  }
  if (next === 61) {
    return this.finishOp(types$1.assign, 2);
  }
  return this.finishOp(types$1.slash, 1);
};
pp.readToken_mult_modulo_exp = function(code) {
  var next = this.input.charCodeAt(this.pos + 1);
  var size = 1;
  var tokentype = code === 42 ? types$1.star : types$1.modulo;
  if (this.options.ecmaVersion >= 7 && code === 42 && next === 42) {
    ++size;
    tokentype = types$1.starstar;
    next = this.input.charCodeAt(this.pos + 2);
  }
  if (next === 61) {
    return this.finishOp(types$1.assign, size + 1);
  }
  return this.finishOp(tokentype, size);
};
pp.readToken_pipe_amp = function(code) {
  var next = this.input.charCodeAt(this.pos + 1);
  if (next === code) {
    if (this.options.ecmaVersion >= 12) {
      var next2 = this.input.charCodeAt(this.pos + 2);
      if (next2 === 61) {
        return this.finishOp(types$1.assign, 3);
      }
    }
    return this.finishOp(code === 124 ? types$1.logicalOR : types$1.logicalAND, 2);
  }
  if (next === 61) {
    return this.finishOp(types$1.assign, 2);
  }
  return this.finishOp(code === 124 ? types$1.bitwiseOR : types$1.bitwiseAND, 1);
};
pp.readToken_caret = function() {
  var next = this.input.charCodeAt(this.pos + 1);
  if (next === 61) {
    return this.finishOp(types$1.assign, 2);
  }
  return this.finishOp(types$1.bitwiseXOR, 1);
};
pp.readToken_plus_min = function(code) {
  var next = this.input.charCodeAt(this.pos + 1);
  if (next === code) {
    if (next === 45 && !this.inModule && this.input.charCodeAt(this.pos + 2) === 62 && (this.lastTokEnd === 0 || lineBreak.test(this.input.slice(this.lastTokEnd, this.pos)))) {
      this.skipLineComment(3);
      this.skipSpace();
      return this.nextToken();
    }
    return this.finishOp(types$1.incDec, 2);
  }
  if (next === 61) {
    return this.finishOp(types$1.assign, 2);
  }
  return this.finishOp(types$1.plusMin, 1);
};
pp.readToken_lt_gt = function(code) {
  var next = this.input.charCodeAt(this.pos + 1);
  var size = 1;
  if (next === code) {
    size = code === 62 && this.input.charCodeAt(this.pos + 2) === 62 ? 3 : 2;
    if (this.input.charCodeAt(this.pos + size) === 61) {
      return this.finishOp(types$1.assign, size + 1);
    }
    return this.finishOp(types$1.bitShift, size);
  }
  if (next === 33 && code === 60 && !this.inModule && this.input.charCodeAt(this.pos + 2) === 45 && this.input.charCodeAt(this.pos + 3) === 45) {
    this.skipLineComment(4);
    this.skipSpace();
    return this.nextToken();
  }
  if (next === 61) {
    size = 2;
  }
  return this.finishOp(types$1.relational, size);
};
pp.readToken_eq_excl = function(code) {
  var next = this.input.charCodeAt(this.pos + 1);
  if (next === 61) {
    return this.finishOp(types$1.equality, this.input.charCodeAt(this.pos + 2) === 61 ? 3 : 2);
  }
  if (code === 61 && next === 62 && this.options.ecmaVersion >= 6) {
    this.pos += 2;
    return this.finishToken(types$1.arrow);
  }
  return this.finishOp(code === 61 ? types$1.eq : types$1.prefix, 1);
};
pp.readToken_question = function() {
  var ecmaVersion = this.options.ecmaVersion;
  if (ecmaVersion >= 11) {
    var next = this.input.charCodeAt(this.pos + 1);
    if (next === 46) {
      var next2 = this.input.charCodeAt(this.pos + 2);
      if (next2 < 48 || next2 > 57) {
        return this.finishOp(types$1.questionDot, 2);
      }
    }
    if (next === 63) {
      if (ecmaVersion >= 12) {
        var next2$1 = this.input.charCodeAt(this.pos + 2);
        if (next2$1 === 61) {
          return this.finishOp(types$1.assign, 3);
        }
      }
      return this.finishOp(types$1.coalesce, 2);
    }
  }
  return this.finishOp(types$1.question, 1);
};
pp.readToken_numberSign = function() {
  var ecmaVersion = this.options.ecmaVersion;
  var code = 35;
  if (ecmaVersion >= 13) {
    ++this.pos;
    code = this.fullCharCodeAtPos();
    if (isIdentifierStart(code, true) || code === 92) {
      return this.finishToken(types$1.privateId, this.readWord1());
    }
  }
  this.raise(this.pos, "Unexpected character '" + codePointToString(code) + "'");
};
pp.getTokenFromCode = function(code) {
  switch (code) {
    // The interpretation of a dot depends on whether it is followed
    // by a digit or another two dots.
    case 46:
      return this.readToken_dot();
    // Punctuation tokens.
    case 40:
      ++this.pos;
      return this.finishToken(types$1.parenL);
    case 41:
      ++this.pos;
      return this.finishToken(types$1.parenR);
    case 59:
      ++this.pos;
      return this.finishToken(types$1.semi);
    case 44:
      ++this.pos;
      return this.finishToken(types$1.comma);
    case 91:
      ++this.pos;
      return this.finishToken(types$1.bracketL);
    case 93:
      ++this.pos;
      return this.finishToken(types$1.bracketR);
    case 123:
      ++this.pos;
      return this.finishToken(types$1.braceL);
    case 125:
      ++this.pos;
      return this.finishToken(types$1.braceR);
    case 58:
      ++this.pos;
      return this.finishToken(types$1.colon);
    case 96:
      if (this.options.ecmaVersion < 6) {
        break;
      }
      ++this.pos;
      return this.finishToken(types$1.backQuote);
    case 48:
      var next = this.input.charCodeAt(this.pos + 1);
      if (next === 120 || next === 88) {
        return this.readRadixNumber(16);
      }
      if (this.options.ecmaVersion >= 6) {
        if (next === 111 || next === 79) {
          return this.readRadixNumber(8);
        }
        if (next === 98 || next === 66) {
          return this.readRadixNumber(2);
        }
      }
    // Anything else beginning with a digit is an integer, octal
    // number, or float.
    case 49:
    case 50:
    case 51:
    case 52:
    case 53:
    case 54:
    case 55:
    case 56:
    case 57:
      return this.readNumber(false);
    // Quotes produce strings.
    case 34:
    case 39:
      return this.readString(code);
    // Operators are parsed inline in tiny state machines. '=' (61) is
    // often referred to. `finishOp` simply skips the amount of
    // characters it is given as second argument, and returns a token
    // of the type given by its first argument.
    case 47:
      return this.readToken_slash();
    case 37:
    case 42:
      return this.readToken_mult_modulo_exp(code);
    case 124:
    case 38:
      return this.readToken_pipe_amp(code);
    case 94:
      return this.readToken_caret();
    case 43:
    case 45:
      return this.readToken_plus_min(code);
    case 60:
    case 62:
      return this.readToken_lt_gt(code);
    case 61:
    case 33:
      return this.readToken_eq_excl(code);
    case 63:
      return this.readToken_question();
    case 126:
      return this.finishOp(types$1.prefix, 1);
    case 35:
      return this.readToken_numberSign();
  }
  this.raise(this.pos, "Unexpected character '" + codePointToString(code) + "'");
};
pp.finishOp = function(type, size) {
  var str = this.input.slice(this.pos, this.pos + size);
  this.pos += size;
  return this.finishToken(type, str);
};
pp.readRegexp = function() {
  var escaped, inClass, start = this.pos;
  for (; ; ) {
    if (this.pos >= this.input.length) {
      this.raise(start, "Unterminated regular expression");
    }
    var ch = this.input.charAt(this.pos);
    if (lineBreak.test(ch)) {
      this.raise(start, "Unterminated regular expression");
    }
    if (!escaped) {
      if (ch === "[") {
        inClass = true;
      } else if (ch === "]" && inClass) {
        inClass = false;
      } else if (ch === "/" && !inClass) {
        break;
      }
      escaped = ch === "\\";
    } else {
      escaped = false;
    }
    ++this.pos;
  }
  var pattern = this.input.slice(start, this.pos);
  ++this.pos;
  var flagsStart = this.pos;
  var flags = this.readWord1();
  if (this.containsEsc) {
    this.unexpected(flagsStart);
  }
  var state = this.regexpState || (this.regexpState = new RegExpValidationState(this));
  state.reset(start, pattern, flags);
  this.validateRegExpFlags(state);
  this.validateRegExpPattern(state);
  var value2 = null;
  try {
    value2 = new RegExp(pattern, flags);
  } catch (e) {
  }
  return this.finishToken(types$1.regexp, { pattern, flags, value: value2 });
};
pp.readInt = function(radix, len, maybeLegacyOctalNumericLiteral) {
  var allowSeparators = this.options.ecmaVersion >= 12 && len === void 0;
  var isLegacyOctalNumericLiteral = maybeLegacyOctalNumericLiteral && this.input.charCodeAt(this.pos) === 48;
  var start = this.pos, total = 0, lastCode = 0;
  for (var i = 0, e = len == null ? Infinity : len; i < e; ++i, ++this.pos) {
    var code = this.input.charCodeAt(this.pos), val = void 0;
    if (allowSeparators && code === 95) {
      if (isLegacyOctalNumericLiteral) {
        this.raiseRecoverable(this.pos, "Numeric separator is not allowed in legacy octal numeric literals");
      }
      if (lastCode === 95) {
        this.raiseRecoverable(this.pos, "Numeric separator must be exactly one underscore");
      }
      if (i === 0) {
        this.raiseRecoverable(this.pos, "Numeric separator is not allowed at the first of digits");
      }
      lastCode = code;
      continue;
    }
    if (code >= 97) {
      val = code - 97 + 10;
    } else if (code >= 65) {
      val = code - 65 + 10;
    } else if (code >= 48 && code <= 57) {
      val = code - 48;
    } else {
      val = Infinity;
    }
    if (val >= radix) {
      break;
    }
    lastCode = code;
    total = total * radix + val;
  }
  if (allowSeparators && lastCode === 95) {
    this.raiseRecoverable(this.pos - 1, "Numeric separator is not allowed at the last of digits");
  }
  if (this.pos === start || len != null && this.pos - start !== len) {
    return null;
  }
  return total;
};
function stringToNumber(str, isLegacyOctalNumericLiteral) {
  if (isLegacyOctalNumericLiteral) {
    return parseInt(str, 8);
  }
  return parseFloat(str.replace(/_/g, ""));
}
function stringToBigInt(str) {
  if (typeof BigInt !== "function") {
    return null;
  }
  return BigInt(str.replace(/_/g, ""));
}
pp.readRadixNumber = function(radix) {
  var start = this.pos;
  this.pos += 2;
  var val = this.readInt(radix);
  if (val == null) {
    this.raise(this.start + 2, "Expected number in radix " + radix);
  }
  if (this.options.ecmaVersion >= 11 && this.input.charCodeAt(this.pos) === 110) {
    val = stringToBigInt(this.input.slice(start, this.pos));
    ++this.pos;
  } else if (isIdentifierStart(this.fullCharCodeAtPos())) {
    this.raise(this.pos, "Identifier directly after number");
  }
  return this.finishToken(types$1.num, val);
};
pp.readNumber = function(startsWithDot) {
  var start = this.pos;
  if (!startsWithDot && this.readInt(10, void 0, true) === null) {
    this.raise(start, "Invalid number");
  }
  var octal = this.pos - start >= 2 && this.input.charCodeAt(start) === 48;
  if (octal && this.strict) {
    this.raise(start, "Invalid number");
  }
  var next = this.input.charCodeAt(this.pos);
  if (!octal && !startsWithDot && this.options.ecmaVersion >= 11 && next === 110) {
    var val$1 = stringToBigInt(this.input.slice(start, this.pos));
    ++this.pos;
    if (isIdentifierStart(this.fullCharCodeAtPos())) {
      this.raise(this.pos, "Identifier directly after number");
    }
    return this.finishToken(types$1.num, val$1);
  }
  if (octal && /[89]/.test(this.input.slice(start, this.pos))) {
    octal = false;
  }
  if (next === 46 && !octal) {
    ++this.pos;
    this.readInt(10);
    next = this.input.charCodeAt(this.pos);
  }
  if ((next === 69 || next === 101) && !octal) {
    next = this.input.charCodeAt(++this.pos);
    if (next === 43 || next === 45) {
      ++this.pos;
    }
    if (this.readInt(10) === null) {
      this.raise(start, "Invalid number");
    }
  }
  if (isIdentifierStart(this.fullCharCodeAtPos())) {
    this.raise(this.pos, "Identifier directly after number");
  }
  var val = stringToNumber(this.input.slice(start, this.pos), octal);
  return this.finishToken(types$1.num, val);
};
pp.readCodePoint = function() {
  var ch = this.input.charCodeAt(this.pos), code;
  if (ch === 123) {
    if (this.options.ecmaVersion < 6) {
      this.unexpected();
    }
    var codePos = ++this.pos;
    code = this.readHexChar(this.input.indexOf("}", this.pos) - this.pos);
    ++this.pos;
    if (code > 1114111) {
      this.invalidStringToken(codePos, "Code point out of bounds");
    }
  } else {
    code = this.readHexChar(4);
  }
  return code;
};
pp.readString = function(quote) {
  var out = "", chunkStart = ++this.pos;
  for (; ; ) {
    if (this.pos >= this.input.length) {
      this.raise(this.start, "Unterminated string constant");
    }
    var ch = this.input.charCodeAt(this.pos);
    if (ch === quote) {
      break;
    }
    if (ch === 92) {
      out += this.input.slice(chunkStart, this.pos);
      out += this.readEscapedChar(false);
      chunkStart = this.pos;
    } else if (ch === 8232 || ch === 8233) {
      if (this.options.ecmaVersion < 10) {
        this.raise(this.start, "Unterminated string constant");
      }
      ++this.pos;
      if (this.options.locations) {
        this.curLine++;
        this.lineStart = this.pos;
      }
    } else {
      if (isNewLine(ch)) {
        this.raise(this.start, "Unterminated string constant");
      }
      ++this.pos;
    }
  }
  out += this.input.slice(chunkStart, this.pos++);
  return this.finishToken(types$1.string, out);
};
var INVALID_TEMPLATE_ESCAPE_ERROR = {};
pp.tryReadTemplateToken = function() {
  this.inTemplateElement = true;
  try {
    this.readTmplToken();
  } catch (err) {
    if (err === INVALID_TEMPLATE_ESCAPE_ERROR) {
      this.readInvalidTemplateToken();
    } else {
      throw err;
    }
  }
  this.inTemplateElement = false;
};
pp.invalidStringToken = function(position, message) {
  if (this.inTemplateElement && this.options.ecmaVersion >= 9) {
    throw INVALID_TEMPLATE_ESCAPE_ERROR;
  } else {
    this.raise(position, message);
  }
};
pp.readTmplToken = function() {
  var out = "", chunkStart = this.pos;
  for (; ; ) {
    if (this.pos >= this.input.length) {
      this.raise(this.start, "Unterminated template");
    }
    var ch = this.input.charCodeAt(this.pos);
    if (ch === 96 || ch === 36 && this.input.charCodeAt(this.pos + 1) === 123) {
      if (this.pos === this.start && (this.type === types$1.template || this.type === types$1.invalidTemplate)) {
        if (ch === 36) {
          this.pos += 2;
          return this.finishToken(types$1.dollarBraceL);
        } else {
          ++this.pos;
          return this.finishToken(types$1.backQuote);
        }
      }
      out += this.input.slice(chunkStart, this.pos);
      return this.finishToken(types$1.template, out);
    }
    if (ch === 92) {
      out += this.input.slice(chunkStart, this.pos);
      out += this.readEscapedChar(true);
      chunkStart = this.pos;
    } else if (isNewLine(ch)) {
      out += this.input.slice(chunkStart, this.pos);
      ++this.pos;
      switch (ch) {
        case 13:
          if (this.input.charCodeAt(this.pos) === 10) {
            ++this.pos;
          }
        case 10:
          out += "\n";
          break;
        default:
          out += String.fromCharCode(ch);
          break;
      }
      if (this.options.locations) {
        ++this.curLine;
        this.lineStart = this.pos;
      }
      chunkStart = this.pos;
    } else {
      ++this.pos;
    }
  }
};
pp.readInvalidTemplateToken = function() {
  for (; this.pos < this.input.length; this.pos++) {
    switch (this.input[this.pos]) {
      case "\\":
        ++this.pos;
        break;
      case "$":
        if (this.input[this.pos + 1] !== "{") {
          break;
        }
      // fall through
      case "`":
        return this.finishToken(types$1.invalidTemplate, this.input.slice(this.start, this.pos));
      case "\r":
        if (this.input[this.pos + 1] === "\n") {
          ++this.pos;
        }
      // fall through
      case "\n":
      case "\u2028":
      case "\u2029":
        ++this.curLine;
        this.lineStart = this.pos + 1;
        break;
    }
  }
  this.raise(this.start, "Unterminated template");
};
pp.readEscapedChar = function(inTemplate) {
  var ch = this.input.charCodeAt(++this.pos);
  ++this.pos;
  switch (ch) {
    case 110:
      return "\n";
    // 'n' -> '\n'
    case 114:
      return "\r";
    // 'r' -> '\r'
    case 120:
      return String.fromCharCode(this.readHexChar(2));
    // 'x'
    case 117:
      return codePointToString(this.readCodePoint());
    // 'u'
    case 116:
      return "	";
    // 't' -> '\t'
    case 98:
      return "\b";
    // 'b' -> '\b'
    case 118:
      return "\v";
    // 'v' -> '\u000b'
    case 102:
      return "\f";
    // 'f' -> '\f'
    case 13:
      if (this.input.charCodeAt(this.pos) === 10) {
        ++this.pos;
      }
    // '\r\n'
    case 10:
      if (this.options.locations) {
        this.lineStart = this.pos;
        ++this.curLine;
      }
      return "";
    case 56:
    case 57:
      if (this.strict) {
        this.invalidStringToken(
          this.pos - 1,
          "Invalid escape sequence"
        );
      }
      if (inTemplate) {
        var codePos = this.pos - 1;
        this.invalidStringToken(
          codePos,
          "Invalid escape sequence in template string"
        );
      }
    default:
      if (ch >= 48 && ch <= 55) {
        var octalStr = this.input.substr(this.pos - 1, 3).match(/^[0-7]+/)[0];
        var octal = parseInt(octalStr, 8);
        if (octal > 255) {
          octalStr = octalStr.slice(0, -1);
          octal = parseInt(octalStr, 8);
        }
        this.pos += octalStr.length - 1;
        ch = this.input.charCodeAt(this.pos);
        if ((octalStr !== "0" || ch === 56 || ch === 57) && (this.strict || inTemplate)) {
          this.invalidStringToken(
            this.pos - 1 - octalStr.length,
            inTemplate ? "Octal literal in template string" : "Octal literal in strict mode"
          );
        }
        return String.fromCharCode(octal);
      }
      if (isNewLine(ch)) {
        if (this.options.locations) {
          this.lineStart = this.pos;
          ++this.curLine;
        }
        return "";
      }
      return String.fromCharCode(ch);
  }
};
pp.readHexChar = function(len) {
  var codePos = this.pos;
  var n = this.readInt(16, len);
  if (n === null) {
    this.invalidStringToken(codePos, "Bad character escape sequence");
  }
  return n;
};
pp.readWord1 = function() {
  this.containsEsc = false;
  var word = "", first = true, chunkStart = this.pos;
  var astral = this.options.ecmaVersion >= 6;
  while (this.pos < this.input.length) {
    var ch = this.fullCharCodeAtPos();
    if (isIdentifierChar(ch, astral)) {
      this.pos += ch <= 65535 ? 1 : 2;
    } else if (ch === 92) {
      this.containsEsc = true;
      word += this.input.slice(chunkStart, this.pos);
      var escStart = this.pos;
      if (this.input.charCodeAt(++this.pos) !== 117) {
        this.invalidStringToken(this.pos, "Expecting Unicode escape sequence \\uXXXX");
      }
      ++this.pos;
      var esc = this.readCodePoint();
      if (!(first ? isIdentifierStart : isIdentifierChar)(esc, astral)) {
        this.invalidStringToken(escStart, "Invalid Unicode escape");
      }
      word += codePointToString(esc);
      chunkStart = this.pos;
    } else {
      break;
    }
    first = false;
  }
  return word + this.input.slice(chunkStart, this.pos);
};
pp.readWord = function() {
  var word = this.readWord1();
  var type = types$1.name;
  if (this.keywords.test(word)) {
    type = keywords[word];
  }
  return this.finishToken(type, word);
};
var version = "8.15.0";
Parser.acorn = {
  Parser,
  version,
  defaultOptions,
  Position,
  SourceLocation,
  getLineInfo,
  Node,
  TokenType,
  tokTypes: types$1,
  keywordTypes: keywords,
  TokContext,
  tokContexts: types,
  isIdentifierChar,
  isIdentifierStart,
  Token,
  isNewLine,
  lineBreak,
  lineBreakG,
  nonASCIIwhitespace
};
function parse$1(input, options) {
  return Parser.parse(input, options);
}
const constants = {
  undefined: "void(0)",
  Infinity: "Number.POSITIVE_INFINITY",
  NaN: "Number.NaN",
  E: "Math.E",
  LN2: "Math.LN2",
  LN10: "Math.LN10",
  LOG2E: "Math.LOG2E",
  LOG10E: "Math.LOG10E",
  PI: "Math.PI",
  SQRT1_2: "Math.SQRT1_2",
  SQRT2: "Math.SQRT2"
};
function isNumber(value2) {
  return typeof value2 === "number";
}
const PARSER_OPT = { ecmaVersion: 11 };
const DEFAULT_PARAM_ID = "$";
const DEFAULT_TUPLE_ID = "d";
const DEFAULT_TUPLE_ID1 = "d1";
const DEFAULT_TUPLE_ID2 = "d2";
const NO = (msg) => (node, ctx) => ctx.error(node, msg + " not allowed");
const ERROR_AGGREGATE = NO("Aggregate function");
const ERROR_WINDOW = NO("Window function");
const ERROR_ARGUMENT = "Invalid argument";
const ERROR_COLUMN = "Invalid column reference";
const ERROR_AGGRONLY = ERROR_COLUMN + " (must be input to an aggregate function)";
const ERROR_FUNCTION = "Invalid function call";
const ERROR_MEMBER = "Invalid member expression";
const ERROR_OP_PARAMETER = "Invalid operator parameter";
const ERROR_PARAM = "Invalid param reference";
const ERROR_VARIABLE = "Invalid variable reference";
const ERROR_VARIABLE_OP = "Variable not accessible in operator call";
const ERROR_DECLARATION = "Unsupported variable declaration";
const ERROR_DESTRUCTURE = "Unsupported destructuring pattern";
const ERROR_CLOSURE = "Table expressions do not support closures";
const ERROR_ESCAPE = "Use aq.escape(fn) to use a function as-is (including closures)";
const ERROR_USE_PARAMS = "use table.params({ name: value }) to define dynamic parameters";
const ERROR_ADD_FUNCTION = "use aq.addFunction(name, fn) to add new op functions";
const ERROR_VARIABLE_NOTE = `
Note: ${ERROR_CLOSURE}. ${ERROR_ESCAPE}, or ${ERROR_USE_PARAMS}.`;
const ERROR_FUNCTION_NOTE = `
Note: ${ERROR_CLOSURE}. ${ERROR_ESCAPE}, or ${ERROR_ADD_FUNCTION}.`;
const ERROR_ROW_OBJECT = `The ${ROW_OBJECT} method is not valid in multi-table expressions.`;
function parseExpression(ctx, spec) {
  const ast = parseAST(spec);
  let node = ctx.root = ast;
  ctx.spec = spec;
  ctx.tuple = null;
  ctx.tuple1 = null;
  ctx.tuple2 = null;
  ctx.$param = null;
  ctx.$op = 0;
  ctx.scope = /* @__PURE__ */ new Set();
  ctx.paramsRef = /* @__PURE__ */ new Map();
  ctx.columnRef = /* @__PURE__ */ new Map();
  if (isFunctionExpression(node)) {
    parseFunction(node, ctx);
    node = node.body;
  } else if (ctx.join) {
    ctx.scope.add(ctx.tuple1 = DEFAULT_TUPLE_ID1);
    ctx.scope.add(ctx.tuple2 = DEFAULT_TUPLE_ID2);
    ctx.scope.add(ctx.$param = DEFAULT_PARAM_ID);
  } else {
    ctx.scope.add(ctx.tuple = DEFAULT_TUPLE_ID);
    ctx.scope.add(ctx.$param = DEFAULT_PARAM_ID);
  }
  walk(node, ctx, visitors);
  return ctx.root;
}
function parseAST(expr) {
  try {
    const code = expr.field ? fieldRef(expr) : isArray$2(expr) ? toString$1(expr) : expr;
    return parse$1(`expr=(${code})`, PARSER_OPT).body[0].expression.right;
  } catch (err) {
    error(`Expression parse error: ${expr + ""}`);
  }
}
function fieldRef(expr) {
  const col = JSON.stringify(expr + "");
  return !(expr.table || 0) ? `d=>d[${col}]` : `(a,b)=>b[${col}]`;
}
const visitors = {
  FunctionDeclaration: NO("Function definitions"),
  ForStatement: NO("For loops"),
  ForOfStatement: NO("For-of loops"),
  ForInStatement: NO("For-in loops"),
  WhileStatement: NO("While loops"),
  DoWhileStatement: NO("Do-while loops"),
  AwaitExpression: NO("Await expressions"),
  ArrowFunctionExpression: NO("Function definitions"),
  AssignmentExpression: NO("Assignments"),
  FunctionExpression: NO("Function definitions"),
  NewExpression: NO('Use of "new"'),
  UpdateExpression: NO("Update expressions"),
  VariableDeclarator(node, ctx) {
    handleDeclaration(node.id, ctx);
  },
  Identifier(node, ctx, parent) {
    if (handleIdentifier(node, ctx, parent) && !ctx.scope.has(node.name)) {
      ctx.error(node, ERROR_VARIABLE, ERROR_VARIABLE_NOTE);
    }
  },
  CallExpression(node, ctx) {
    const name2 = functionName(node.callee);
    const def = getAggregate(name2) || getWindow(name2);
    if (def) {
      if ((ctx.join || ctx.aggregate === false) && hasAggregate(name2)) {
        ERROR_AGGREGATE(node, ctx);
      }
      if ((ctx.join || ctx.window === false) && hasWindow(name2)) {
        ERROR_WINDOW(node, ctx);
      }
      ctx.$op = 1;
      if (ctx.ast) {
        updateFunctionNode(node, name2, ctx);
        node.arguments.forEach((arg) => walk(arg, ctx, opVisitors));
      } else {
        const op2 = ctx.op(parseOperator(ctx, def, name2, node.arguments));
        Object.assign(node, { type: Op2, name: op2.id });
      }
      ctx.$op = 0;
      return false;
    } else if (hasFunction(name2)) {
      updateFunctionNode(node, name2, ctx);
    } else {
      ctx.error(node, ERROR_FUNCTION, ERROR_FUNCTION_NOTE);
    }
  },
  MemberExpression(node, ctx, parent) {
    const { object: object2, property } = node;
    if (!is(Identifier, object2)) return;
    const { name: name2 } = object2;
    if (isMath(node) && is(Identifier, property) && Object.hasOwn(constants, property.name)) {
      updateConstantNode(node, property.name);
      return;
    }
    const index = name2 === ctx.tuple ? 0 : name2 === ctx.tuple1 ? 1 : name2 === ctx.tuple2 ? 2 : -1;
    if (index >= 0) {
      return spliceMember(node, index, ctx, checkColumn, parent);
    } else if (name2 === ctx.$param) {
      return spliceMember(node, index, ctx, checkParam);
    } else if (ctx.paramsRef.has(name2)) {
      updateParameterNode(node, ctx.paramsRef.get(name2));
    } else if (ctx.columnRef.has(name2)) {
      updateColumnNode(object2, name2, ctx, node);
    } else if (Object.hasOwn(ctx.params, name2)) {
      updateParameterNode(object2, name2);
    }
  }
};
function spliceMember(node, index, ctx, check2, parent) {
  const { property, computed } = node;
  let name2;
  if (!computed) {
    name2 = property.name;
  } else if (is(Literal, property)) {
    name2 = property.value;
  } else try {
    walk(property, ctx, visitors, node);
    name2 = ctx.param(property);
  } catch (e) {
    ctx.error(node, ERROR_MEMBER);
  }
  check2(node, name2, index, ctx, parent);
  return false;
}
const opVisitors = {
  ...visitors,
  VariableDeclarator: NO("Variable declaration in operator call"),
  Identifier(node, ctx, parent) {
    if (handleIdentifier(node, ctx, parent)) {
      ctx.error(node, ERROR_VARIABLE_OP);
    }
  },
  CallExpression(node, ctx) {
    const name2 = functionName(node.callee);
    if (hasFunction(name2)) {
      updateFunctionNode(node, name2, ctx);
    } else {
      ctx.error(node, ERROR_FUNCTION, ERROR_FUNCTION_NOTE);
    }
  }
};
function parseFunction(node, ctx) {
  if (node.generator) NO("Generator functions")(node, ctx);
  if (node.async) NO("Async functions")(node, ctx);
  const { params } = node;
  const len = params.length;
  const setc = (index) => (name2, key2) => ctx.columnRef.set(name2, [key2, index]);
  const setp = (name2, key2) => ctx.paramsRef.set(name2, key2);
  if (!len) ;
  else if (ctx.join) {
    parseRef(ctx, params[0], "tuple1", setc(1));
    if (len > 1) parseRef(ctx, params[1], "tuple2", setc(2));
    if (len > 2) parseRef(ctx, params[2], "$param", setp);
  } else {
    parseRef(ctx, params[0], "tuple", setc(0));
    if (len > 1) parseRef(ctx, params[1], "$param", setp);
  }
  ctx.root = node.body;
}
function parseRef(ctx, node, refName, alias) {
  if (is(Identifier, node)) {
    ctx.scope.add(node.name);
    ctx[refName] = node.name;
  } else if (is(ObjectPattern, node)) {
    node.properties.forEach((p) => {
      const key2 = is(Identifier, p.key) ? p.key.name : is(Literal, p.key) ? p.key.value : ctx.error(p, ERROR_ARGUMENT);
      if (!is(Identifier, p.value)) {
        ctx.error(p.value, ERROR_DESTRUCTURE);
      }
      alias(p.value.name, key2);
    });
  }
}
function parseOperator(ctx, def, name2, args) {
  const fields = [];
  const params = [];
  const idxFields = def.param[0] || 0;
  const idxParams = idxFields + (def.param[1] || 0);
  args.forEach((arg, index) => {
    if (index < idxFields) {
      walk(arg, ctx, opVisitors);
      fields.push(ctx.field(arg));
    } else if (index < idxParams) {
      walk(arg, ctx, opVisitors);
      params.push(ctx.param(arg));
    } else {
      ctx.error(arg, ERROR_OP_PARAMETER);
    }
  });
  return { name: name2, fields, params, ...ctx.spec.window || {} };
}
function functionName(node) {
  return is(Identifier, node) ? node.name : !is(MemberExpression, node) ? null : isMath(node) ? rewriteMath(node.property.name) : node.property.name;
}
function isMath(node) {
  return is(Identifier, node.object) && node.object.name === "Math";
}
function rewriteMath(name2) {
  return name2 === "max" ? "greatest" : name2 === "min" ? "least" : name2;
}
function handleIdentifier(node, ctx, parent) {
  const { name: name2 } = node;
  if (is(MemberExpression, parent) && parent.property === node) ;
  else if (is(Property, parent) && parent.key === node) ;
  else if (ctx.paramsRef.has(name2)) {
    updateParameterNode(node, ctx.paramsRef.get(name2));
  } else if (ctx.columnRef.has(name2)) {
    updateColumnNode(node, name2, ctx, parent);
  } else if (Object.hasOwn(ctx.params, name2)) {
    updateParameterNode(node, name2);
  } else if (Object.hasOwn(constants, name2)) {
    updateConstantNode(node, name2);
  } else {
    return true;
  }
}
function checkColumn(node, name2, index, ctx, parent) {
  const table2 = index === 0 ? ctx.table : index > 0 ? ctx.join[index - 1] : null;
  const col = table2 && table2.column(name2);
  if (table2 && !col) {
    ctx.error(node, ERROR_COLUMN);
  }
  if (ctx.aggronly && !ctx.$op) {
    ctx.error(node, ERROR_AGGRONLY);
  }
  rewrite(node, name2, index, col, parent);
}
function updateColumnNode(node, key2, ctx, parent) {
  const [name2, index] = ctx.columnRef.get(key2);
  checkColumn(node, name2, index, ctx, parent);
}
function checkParam(node, name2, index, ctx) {
  if (ctx.params && !Object.hasOwn(ctx.params, name2)) {
    ctx.error(node, ERROR_PARAM);
  }
  updateParameterNode(node, name2);
}
function updateParameterNode(node, name2) {
  node.type = Parameter;
  node.name = name2;
}
function updateConstantNode(node, name2) {
  node.type = Constant;
  node.name = name2;
  node.raw = constants[name2];
}
function updateFunctionNode(node, name2, ctx) {
  if (name2 === ROW_OBJECT) {
    const t2 = ctx.table;
    if (!t2) ctx.error(node, ERROR_ROW_OBJECT);
    rowObjectExpression(
      node,
      t2,
      node.arguments.length ? node.arguments.map((node2) => {
        const col = ctx.param(node2);
        const name3 = isNumber(col) ? t2.columnName(col) : col;
        if (!t2.column(name3)) ctx.error(node2, ERROR_COLUMN);
        return name3;
      }) : t2.columnNames()
    );
  } else {
    node.callee = { type: Function$1, name: name2 };
  }
}
function handleDeclaration(node, ctx) {
  if (is(Identifier, node)) {
    ctx.scope.add(node.name);
  } else if (is(ArrayPattern, node)) {
    node.elements.forEach((elm) => handleDeclaration(elm, ctx));
  } else if (is(ObjectPattern, node)) {
    node.properties.forEach((prop) => handleDeclaration(prop.value, ctx));
  } else {
    ctx.error(node.id, ERROR_DECLARATION);
  }
}
const ANNOTATE = { [Column$1]: 1, [Op2]: 1 };
function parse3(input, opt2 = {}) {
  const generate = opt2.generate || codegen;
  const compiler = opt2.compiler || compile;
  const params = getParams(opt2);
  const fields = {};
  const opcall = {};
  const names = [];
  const exprs = [];
  let fieldId = 0;
  let opId = -1;
  const compileExpr = opt2.join ? compiler.join : opt2.index == 1 ? compiler.expr2 : compiler.expr;
  const ctx = {
    op(op2) {
      const key2 = opKey(op2);
      return opcall[key2] || (op2.id = ++opId, opcall[key2] = op2);
    },
    field(node) {
      const code = generate(node);
      return fields[code] || (fields[code] = ++fieldId);
    },
    param(node) {
      return is(Literal, node) ? node.value : compiler.param(generate(node), params);
    },
    value(name2, node) {
      names.push(name2);
      const e = node.escape || (opt2.ast ? clean(node) : compileExpr(generate(node), params));
      exprs.push(e);
      if (ANNOTATE[node.type] && e !== node && isObject(e)) {
        e.field = node.name;
      }
    },
    error(node, msg, note = "") {
      const i = node.start - 6;
      const j = node.end - 6;
      const snippet = String(ctx.spec).slice(i, j);
      error(`${msg}: "${snippet}"${note}`);
    }
  };
  Object.assign(ctx, opt2, { params });
  for (const [name2, value2] of entries(input)) {
    ctx.value(
      name2 + "",
      value2.escape ? parseEscape(ctx, value2, params) : parseExpression(ctx, value2)
    );
  }
  if (opt2.ast) {
    return { names, exprs };
  }
  const f = [];
  for (const key2 in fields) {
    f[fields[key2]] = compiler.expr(key2, params);
  }
  const ops = Object.values(opcall);
  ops.forEach((op2) => op2.fields = op2.fields.map((id) => f[id]));
  return { names, exprs, ops };
}
function opKey(op2) {
  let key2 = `${op2.name}(${op2.fields.concat(op2.params).join(",")})`;
  if (op2.frame) {
    const frame = op2.frame.map((v) => Number.isFinite(v) ? Math.abs(v) : -1);
    key2 += `[${frame},${!!op2.peers}]`;
  }
  return key2;
}
function getParams(opt2) {
  return (opt2.table ? getTableParams(opt2.table) : opt2.join ? {
    ...getTableParams(opt2.join[1]),
    ...getTableParams(opt2.join[0])
  } : {}) || {};
}
function getTableParams(table2) {
  return table2 && isFunction(table2.params) ? table2.params() : {};
}
function wrap$1(expr, properties) {
  return expr && expr.expr ? new Wrapper({ ...expr, ...properties }) : new Wrapper(properties, expr);
}
class Wrapper {
  constructor(properties, expr) {
    this.expr = expr;
    Object.assign(this, properties);
  }
  toString() {
    return String(this.expr);
  }
  toObject() {
    return {
      ...this,
      expr: this.toString(),
      ...isFunction(this.expr) ? { func: true } : {}
    };
  }
}
function field$1(expr, name2, table2 = 0) {
  const props = table2 ? { field: true, table: table2 } : { field: true };
  return wrap$1(
    expr,
    name2 ? { expr: name2, ...props } : props
  );
}
function assign$1(map, pairs2) {
  for (const [key2, value2] of entries(pairs2)) {
    map.set(key2, value2);
  }
  return map;
}
function resolve(table2, sel, map = /* @__PURE__ */ new Map()) {
  sel = isNumber(sel) ? table2.columnName(sel) : sel;
  if (isString(sel)) {
    map.set(sel, sel);
  } else if (isArray$2(sel)) {
    sel.forEach((r) => resolve(table2, r, map));
  } else if (isFunction(sel)) {
    resolve(table2, sel(table2), map);
  } else if (isObject(sel)) {
    assign$1(map, sel);
  } else {
    error(`Invalid column selection: ${toString$1(sel)}`);
  }
  return map;
}
function decorate(value2, toObject2) {
  value2.toObject = toObject2;
  return value2;
}
function toObject(value2) {
  return isArray$2(value2) ? value2.map(toObject) : value2 && value2.toObject ? value2.toObject() : value2;
}
function all() {
  return decorate(
    (table2) => table2.columnNames(),
    () => ({ all: [] })
  );
}
function not(...selection) {
  selection = selection.flat();
  return decorate(
    (table2) => {
      const drop = resolve(table2, selection);
      return table2.columnNames((name2) => !drop.has(name2));
    },
    () => ({ not: toObject(selection) })
  );
}
function parseValue(name2, table2, params, options = { window: false }) {
  const exprs = /* @__PURE__ */ new Map();
  const marshal = (param) => {
    param = isNumber(param) ? table2.columnName(param) : param;
    isString(param) ? exprs.set(param, field$1(param)) : isFunction(param) ? resolve(table2, param).forEach(marshal) : isObject(param) ? assign$1(exprs, param) : error(`Invalid ${name2} value: ${param + ""}`);
  };
  toArray(params).forEach(marshal);
  if (options.preparse) {
    options.preparse(exprs);
  }
  return parse3(exprs, { table: table2, ...options });
}
function groupby(table2, ...values2) {
  return _groupby(table2, parseValue("groupby", table2, values2.flat()));
}
function _groupby(table2, exprs) {
  return table2.create({
    groups: createGroups(table2, exprs)
  });
}
function createGroups(table2, { names = [], exprs = [], ops = [] }) {
  const n = names.length;
  if (n === 0) return null;
  if (n === 1 && !table2.isFiltered() && exprs[0].field) {
    const col = table2.column(exprs[0].field);
    if (col.groups) return col.groups(names);
  }
  let get2 = aggregateGet(table2, ops, exprs);
  const getKey = keyFunction(get2);
  const nrows = table2.totalRows();
  const keys2 = new Uint32Array(nrows);
  const index = {};
  const rows = [];
  const data2 = table2.data();
  const bits = table2.mask();
  if (bits) {
    for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
      const key2 = getKey(i, data2) + "";
      keys2[i] = index[key2] ??= rows.push(i) - 1;
    }
  } else {
    for (let i = 0; i < nrows; ++i) {
      const key2 = getKey(i, data2) + "";
      keys2[i] = index[key2] ??= rows.push(i) - 1;
    }
  }
  if (!ops.length) {
    get2 = get2.map((f) => (row) => f(row, data2));
  }
  return { keys: keys2, get: get2, names, rows, size: rows.length };
}
function columnSet(table2) {
  return table2 ? new ColumnSet({ ...table2.data() }, table2.columnNames()) : new ColumnSet();
}
class ColumnSet {
  /**
   * Create a new column set instance.
   * @param {import('./types.js').ColumnData} [data] Initial column data.
   * @param {string[]} [names] Initial column names.
   */
  constructor(data2, names) {
    this.data = data2 || {};
    this.names = names || [];
  }
  /**
   * Add a new column to this set and return the column values.
   * @template {import('./types.js').ColumnType} T
   * @param {string} name The column name.
   * @param {T} values The column values.
   * @return {T} The provided column values.
   */
  add(name2, values2) {
    if (!this.has(name2)) this.names.push(name2 + "");
    return this.data[name2] = values2;
  }
  /**
   * Test if this column set has a columns with the given name.
   * @param {string} name A column name
   * @return {boolean} True if this set contains a column with the given name,
   *  false otherwise.
   */
  has(name2) {
    return Object.hasOwn(this.data, name2);
  }
  /**
   * Add a groupby specification to this column set.
   * @param {import('./types.js').GroupBySpec} groups A groupby specification.
   * @return {this} This column set.
   */
  groupby(groups) {
    this.groups = groups;
    return this;
  }
  /**
   * Create a new table with the contents of this column set, using the same
   * type as a given prototype table. The new table does not inherit the
   * filter, groupby, or orderby state of the prototype.
   * @template {import('./Table.js').Table} T
   * @param {T} proto A prototype table
   * @return {T} The new table.
   */
  new(proto) {
    const { data: data2, names, groups = null } = this;
    return proto.create({ data: data2, names, groups, filter: null, order: null });
  }
  /**
   * Create a derived table with the contents of this column set, using the same
   * type as a given prototype table. The new table will inherit the filter,
   * groupby, and orderby state of the prototype.
   * @template {import('./Table.js').Table} T
   * @param {T} proto A prototype table
   * @return {T} The new table.
   */
  derive(proto) {
    return proto.create(this);
  }
}
function rollup(table2, values2) {
  return _rollup(table2, parse3(values2, { table: table2, aggronly: true, window: false }));
}
function _rollup(table2, { names, exprs, ops = [] }) {
  const cols = columnSet();
  const groups = table2.groups();
  if (groups) groupOutput(cols, groups);
  output$2(names, exprs, groups, aggregate(table2, ops), cols);
  return cols.new(table2);
}
function output$2(names, exprs, groups, result2 = [], cols) {
  if (!exprs.length) return;
  const size = groups ? groups.size : 1;
  const op2 = (id, row) => result2[id][row];
  const n = names.length;
  for (let i = 0; i < n; ++i) {
    const get2 = exprs[i];
    if (get2.field != null) {
      cols.add(names[i], result2[get2.field]);
    } else if (size > 1) {
      const col = cols.add(names[i], Array(size));
      for (let j = 0; j < size; ++j) {
        col[j] = get2(j, null, op2);
      }
    } else {
      cols.add(names[i], [get2(0, null, op2)]);
    }
  }
}
function select(table2, ...columns2) {
  return _select(table2, resolve(table2, columns2.flat()));
}
function _select(table2, columns2) {
  const cols = columnSet();
  columns2.forEach((value2, curr) => {
    const next = isString(value2) ? value2 : curr;
    if (next) {
      const col = table2.column(curr) || error(`Unrecognized column: ${curr}`);
      cols.add(next, col);
    }
  });
  return cols.derive(table2);
}
function regroup(groups, filter2) {
  if (!groups || !filter2) return groups;
  const { keys: keys2, rows, size } = groups;
  const map = new Uint32Array(size);
  filter2.scan((row) => map[keys2[row]] = 1);
  const sum = map.reduce((sum2, val) => sum2 + val, 0);
  if (sum === size) return groups;
  const _rows = Array(sum);
  let _size = 0;
  for (let i = 0; i < size; ++i) {
    if (map[i]) _rows[map[i] = _size++] = rows[i];
  }
  const _keys = new Uint32Array(keys2.length);
  filter2.scan((row) => _keys[row] = map[keys2[row]]);
  return { ...groups, keys: _keys, rows: _rows, size: _size };
}
function reindex(groups, scan2, filter2, nrows) {
  const { keys: keys2, rows, size } = groups;
  let _rows = rows;
  let _size = size;
  let map = null;
  if (filter2) {
    map = new Int32Array(size);
    scan2((row) => map[keys2[row]] = 1);
    const sum = map.reduce((sum2, val) => sum2 + val, 0);
    if (sum !== size) {
      _rows = Array(sum);
      _size = 0;
      for (let i = 0; i < size; ++i) {
        if (map[i]) _rows[map[i] = _size++] = rows[i];
      }
    }
  }
  let r = -1;
  const _keys = new Uint32Array(nrows);
  const fn = _size !== size ? (row) => _keys[++r] = map[keys2[row]] : (row) => _keys[++r] = keys2[row];
  scan2(fn);
  return { ...groups, keys: _keys, rows: _rows, size: _size };
}
function nest(table2, idx, obj, type) {
  const agg = type === "map" || type === true ? map_agg : type === "entries" ? entries_agg : type === "object" ? object_agg : error('groups option must be "map", "entries", or "object".');
  const { names } = table2.groups();
  const col = uniqueName(table2.columnNames(), "_");
  let t2 = select(table2, {}).reify(idx).create({ data: { [col]: obj } });
  t2 = rollup(t2, { [col]: array_agg(col) });
  for (let i = names.length; --i >= 0; ) {
    t2 = rollup(
      groupby(t2, names.slice(0, i)),
      // @ts-ignore
      { [col]: agg(names[i], col) }
    );
  }
  return t2.get(col);
}
function arrayType$1(column) {
  return isTypedArray$1(column) ? column.constructor : Array;
}
let Table$1 = class Table2 {
  /**
   * Instantiate a Table instance.
   * @param {import('./types.js').ColumnData} columns
   *  An object mapping column names to values.
   * @param {string[]} [names]
   *  An ordered list of column names.
   * @param {import('./BitSet.js').BitSet} [filter]
   *  A filtering BitSet.
   * @param {import('./types.js').GroupBySpec} [group]
   *  A groupby specification.
   * @param {import('./types.js').RowComparator} [order]
   *  A row comparator function.
   * @param {import('./types.js').Params} [params]
   *  An object mapping parameter names to values.
   */
  constructor(columns2, names, filter2, group, order, params) {
    const data2 = Object.freeze({ ...columns2 });
    names = names?.slice() ?? Object.keys(data2);
    const nrows = names.length ? data2[names[0]].length : 0;
    this._names = Object.freeze(names);
    this._data = data2;
    this._total = nrows;
    this._nrows = filter2?.count() ?? nrows;
    this._mask = filter2 ?? null;
    this._group = group ?? null;
    this._order = order ?? null;
    this._params = params;
    this._index = null;
    this._partitions = null;
  }
  /**
   * Create a new table with the same type as this table.
   * The new table may have different data, filter, grouping, or ordering
   * based on the values of the optional configuration argument. If a
   * setting is not specified, it is inherited from the current table.
   * @param {import('./types.js').CreateOptions} [options]
   *  Creation options for the new table.
   * @return {this} A newly created table.
   */
  create({
    data: data2 = void 0,
    names = void 0,
    filter: filter2 = void 0,
    groups = void 0,
    order = void 0
  } = {}) {
    const f = filter2 !== void 0 ? filter2 : this.mask();
    return new this.constructor(
      data2 || this._data,
      names || (!data2 ? this._names : null),
      f,
      groups !== void 0 ? groups : regroup(this._group, filter2 && f),
      order !== void 0 ? order : this._order,
      this._params
    );
  }
  /**
   * Get or set table expression parameter values.
   * If called with no arguments, returns the current parameter values
   * as an object. Otherwise, adds the provided parameters to this
   * table's parameter set and returns the table. Any prior parameters
   * with names matching the input parameters are overridden.
   * @param {import('./types.js').Params} [values]
   *  The parameter values.
   * @return {this|import('./types.js').Params}
   *  The current parameter values (if called with no arguments) or this table.
   */
  params(values2) {
    if (arguments.length) {
      if (values2) {
        this._params = { ...this._params, ...values2 };
      }
      return this;
    } else {
      return this._params;
    }
  }
  /**
   * Provide an informative object string tag.
   */
  get [Symbol.toStringTag]() {
    if (!this._names) return "Object";
    const nr = this.numRows();
    const nc = this.numCols();
    const plural = (v) => v !== 1 ? "s" : "";
    return `Table: ${nc} col${plural(nc)} x ${nr} row${plural(nr)}` + (this.isFiltered() ? ` (${this.totalRows()} backing)` : "") + (this.isGrouped() ? `, ${this._group.size} groups` : "") + (this.isOrdered() ? ", ordered" : "");
  }
  /**
   * Indicates if the table has a filter applied.
   * @return {boolean} True if filtered, false otherwise.
   */
  isFiltered() {
    return !!this._mask;
  }
  /**
   * Indicates if the table has a groupby specification.
   * @return {boolean} True if grouped, false otherwise.
   */
  isGrouped() {
    return !!this._group;
  }
  /**
   * Indicates if the table has a row order comparator.
   * @return {boolean} True if ordered, false otherwise.
   */
  isOrdered() {
    return !!this._order;
  }
  /**
   * Get the backing column data for this table.
   * @return {import('./types.js').ColumnData}
   *  Object of named column instances.
   */
  data() {
    return this._data;
  }
  /**
   * Returns the filter bitset mask, if defined.
   * @return {import('./BitSet.js').BitSet} The filter bitset mask.
   */
  mask() {
    return this._mask;
  }
  /**
   * Returns the groupby specification, if defined.
   * @return {import('./types.js').GroupBySpec} The groupby specification.
   */
  groups() {
    return this._group;
  }
  /**
   * Returns the row order comparator function, if specified.
   * @return {import('./types.js').RowComparator}
   *  The row order comparator function.
   */
  comparator() {
    return this._order;
  }
  /**
   * The total number of rows in this table, counting both
   * filtered and unfiltered rows.
   * @return {number} The number of total rows.
   */
  totalRows() {
    return this._total;
  }
  /**
   * The number of active rows in this table. This number may be
   * less than the *totalRows* if the table has been filtered.
   * @return {number} The number of rows.
   */
  numRows() {
    return this._nrows;
  }
  /**
   * The number of active rows in this table. This number may be
   * less than the *totalRows* if the table has been filtered.
   * @return {number} The number of rows.
   */
  get size() {
    return this._nrows;
  }
  /**
   * The number of columns in this table.
   * @return {number} The number of columns.
   */
  numCols() {
    return this._names.length;
  }
  /**
   * Filter function invoked for each column name.
   * @callback NameFilter
   * @param {string} name The column name.
   * @param {number} index The column index.
   * @param {string[]} array The array of names.
   * @return {boolean} Returns true to retain the column name.
   */
  /**
   * The table column names, optionally filtered.
   * @param {NameFilter} [filter] An optional filter function.
   *  If unspecified, all column names are returned.
   * @return {string[]} An array of matching column names.
   */
  columnNames(filter2) {
    return filter2 ? this._names.filter(filter2) : this._names.slice();
  }
  /**
   * The column name at the given index.
   * @param {number} index The column index.
   * @return {string} The column name,
   *  or undefined if the index is out of range.
   */
  columnName(index) {
    return this._names[index];
  }
  /**
   * The column index for the given name.
   * @param {string} name The column name.
   * @return {number} The column index, or -1 if the name is not found.
   */
  columnIndex(name2) {
    return this._names.indexOf(name2);
  }
  /**
   * Get the column instance with the given name.
   * @param {string} name The column name.
   * @return {import('./types.js').ColumnType | undefined}
   *  The named column, or undefined if it does not exist.
   */
  column(name2) {
    return this._data[name2];
  }
  /**
   * Get the column instance at the given index position.
   * @param {number} index The zero-based column index.
   * @return {import('./types.js').ColumnType | undefined}
   *  The column, or undefined if it does not exist.
   */
  columnAt(index) {
    return this._data[this._names[index]];
  }
  /**
   * Get an array of values contained in a column. The resulting array
   * respects any table filter or orderby criteria.
   * @param {string} name The column name.
   * @param {ArrayConstructor | import('./types.js').TypedArrayConstructor} [constructor=Array]
   *  The array constructor for instantiating the output array.
   * @return {import('./types.js').DataValue[] | import('./types.js').TypedArray}
   *  The array of column values.
   */
  array(name2, constructor = Array) {
    const column = this.column(name2);
    const array2 = new constructor(this.numRows());
    let idx = -1;
    this.scan((row) => array2[++idx] = column.at(row), true);
    return array2;
  }
  /**
   * Get the value for the given column and row.
   * @param {string} name The column name.
   * @param {number} [row=0] The row index, defaults to zero if not specified.
   * @return {import('./types.js').DataValue} The table value at (column, row).
   */
  get(name2, row = 0) {
    const column = this.column(name2);
    return this.isFiltered() || this.isOrdered() ? column.at(this.indices()[row]) : column.at(row);
  }
  /**
   * Returns an accessor ("getter") function for a column. The returned
   * function takes a row index as its single argument and returns the
   * corresponding column value.
   * @param {string} name The column name.
   * @return {import('./types.js').ColumnGetter} The column getter function.
   */
  getter(name2) {
    const column = this.column(name2);
    const indices = this.isFiltered() || this.isOrdered() ? this.indices() : null;
    if (indices) {
      return (row) => column.at(indices[row]);
    } else if (column) {
      return (row) => column.at(row);
    } else {
      error(`Unrecognized column: ${name2}`);
    }
  }
  /**
   * Returns an object representing a table row.
   * @param {number} [row=0] The row index, defaults to zero if not specified.
   * @return {object} A row object with named properties for each column.
   */
  object(row = 0) {
    return objectBuilder$1(this)(row);
  }
  /**
   * Returns an array of objects representing table rows.
   * @param {import('./types.js').ObjectsOptions} [options]
   *  The options for row object generation.
   * @return {object[]} An array of row objects.
   */
  objects(options = {}) {
    const { grouped, limit, offset: offset2 } = options;
    const names = resolve(this, options.columns || all());
    const createRow = rowObjectBuilder(this, names);
    const obj = [];
    this.scan(
      (row, data2) => obj.push(createRow(row, data2)),
      true,
      limit,
      offset2
    );
    if (grouped && this.isGrouped()) {
      const idx = [];
      this.scan((row) => idx.push(row), true, limit, offset2);
      return nest(this, idx, obj, grouped);
    }
    return obj;
  }
  /**
   * Returns an iterator over objects representing table rows.
   * @return {Iterator<object>} An iterator over row objects.
   */
  *[Symbol.iterator]() {
    const createRow = objectBuilder$1(this);
    const n = this.numRows();
    for (let i = 0; i < n; ++i) {
      yield createRow(i);
    }
  }
  /**
   * Returns an iterator over column values.
   * @return {Iterator<object>} An iterator over row objects.
   */
  *values(name2) {
    const get2 = this.getter(name2);
    const n = this.numRows();
    for (let i = 0; i < n; ++i) {
      yield get2(i);
    }
  }
  /**
   * Print the contents of this table using the console.table() method.
   * @param {import('./types.js').PrintOptions|number} options
   *  The options for row object generation, determining which rows and
   *  columns are printed. If number-valued, specifies the row limit.
   * @return {this} The table instance.
   */
  print(options = {}) {
    const opt2 = isNumber(options) ? { limit: +options } : { ...options, limit: 10 };
    const obj = this.objects({ ...opt2, grouped: false });
    const msg = `${this[Symbol.toStringTag]}. Showing ${obj.length} rows.`;
    console.log(msg);
    console.table(obj);
    return this;
  }
  /**
   * Returns an array of indices for all rows passing the table filter.
   * @param {boolean} [order=true] A flag indicating if the returned
   *  indices should be sorted if this table is ordered. If false, the
   *  returned indices may or may not be sorted.
   * @return {Uint32Array} An array of row indices.
   */
  indices(order = true) {
    if (this._index) return this._index;
    const n = this.numRows();
    const index = new Uint32Array(n);
    const ordered = this.isOrdered();
    const bits = this.mask();
    let row = -1;
    if (bits) {
      for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
        index[++row] = i;
      }
    } else {
      for (let i = 0; i < n; ++i) {
        index[++row] = i;
      }
    }
    if (order && ordered) {
      const { _order, _data } = this;
      index.sort((a, b) => _order(a, b, _data));
    }
    if (order || !ordered) {
      this._index = index;
    }
    return index;
  }
  /**
   * Returns an array of indices for each group in the table.
   * If the table is not grouped, the result is the same as
   * the *indices* method, but wrapped within an array.
   * @param {boolean} [order=true] A flag indicating if the returned
   *  indices should be sorted if this table is ordered. If false, the
   *  returned indices may or may not be sorted.
   * @return {number[][] | Uint32Array[]} An array of row index arrays, one
   *  per group. The indices will be filtered if the table is filtered.
   */
  partitions(order = true) {
    if (this._partitions) {
      return this._partitions;
    }
    if (!this.isGrouped()) {
      return [this.indices(order)];
    }
    const { keys: keys2, size } = this._group;
    const part = repeat(size, () => []);
    const sort = this._index;
    const bits = this.mask();
    const n = this.numRows();
    if (sort && this.isOrdered()) {
      for (let i = 0, r; i < n; ++i) {
        r = sort[i];
        part[keys2[r]].push(r);
      }
    } else if (bits) {
      for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
        part[keys2[i]].push(i);
      }
    } else {
      for (let i = 0; i < n; ++i) {
        part[keys2[i]].push(i);
      }
    }
    if (order && !sort && this.isOrdered()) {
      const compare2 = this._order;
      const data2 = this._data;
      for (let i = 0; i < size; ++i) {
        part[i].sort((a, b) => compare2(a, b, data2));
      }
    }
    if (order || !this.isOrdered()) {
      this._partitions = part;
    }
    return part;
  }
  /**
   * Create a new fully-materialized instance of this table.
   * All filter and orderby settings are removed from the new table.
   * Instead, the backing data itself is filtered and ordered as needed.
   * @param {number[]} [indices] Ordered row indices to materialize.
   *  If unspecified, all rows passing the table filter are used.
   * @return {this} A reified table.
   */
  reify(indices) {
    const nrows = indices ? indices.length : this.numRows();
    const names = this._names;
    let data2, groups;
    if (!indices && !this.isOrdered()) {
      if (!this.isFiltered()) {
        return this;
      } else if (nrows === this.totalRows()) {
        data2 = this.data();
      }
    }
    if (!data2) {
      const scan2 = indices ? (f) => indices.forEach(f) : (f) => this.scan(f, true);
      const ncols = names.length;
      data2 = {};
      for (let i = 0; i < ncols; ++i) {
        const name2 = names[i];
        const prev = this.column(name2);
        const curr = data2[name2] = new (arrayType$1(prev))(nrows);
        let r = -1;
        isArrayType(prev) ? scan2((row) => curr[++r] = prev[row]) : scan2((row) => curr[++r] = prev.at(row));
      }
      if (this.isGrouped()) {
        groups = reindex(this.groups(), scan2, !!indices, nrows);
      }
    }
    return this.create({ data: data2, names, groups, filter: null, order: null });
  }
  /**
   * Callback function to cancel a table scan.
   * @callback ScanStop
   * @return {void}
   */
  /**
   * Callback function invoked for each row of a table scan.
   * @callback ScanVisitor
   * @param {number} [row] The table row index.
   * @param {import('./types.js').ColumnData} [data]
   *  The backing table data store.
   * @param {ScanStop} [stop] Function to stop the scan early.
   *  Callees can invoke this function to prevent future calls.
   * @return {void}
   */
  /**
   * Perform a table scan, visiting each row of the table.
   * If this table is filtered, only rows passing the filter are visited.
   * @param {ScanVisitor} fn Callback invoked for each row of the table.
   * @param {boolean} [order=false] Indicates if the table should be
   *  scanned in the order determined by *orderby*. This
   *  argument has no effect if the table is unordered.
   * @property {number} [limit=Infinity] The maximum number of rows to scan.
   * @property {number} [offset=0] The row offset indicating how many
   *  initial rows to skip.
   */
  scan(fn, order, limit = Infinity, offset2 = 0) {
    const filter2 = this._mask;
    const nrows = this._nrows;
    const data2 = this._data;
    let i = offset2 || 0;
    if (i > nrows) return;
    const n = Math.min(nrows, i + limit);
    const stop = () => i = this._total;
    if (order && this.isOrdered() || filter2 && this._index) {
      const index = this.indices();
      const data3 = this._data;
      for (; i < n; ++i) {
        fn(index[i], data3, stop);
      }
    } else if (filter2) {
      let c = n - i + 1;
      for (i = filter2.nth(i); --c && i > -1; i = filter2.next(i + 1)) {
        fn(i, data2, stop);
      }
    } else {
      for (; i < n; ++i) {
        fn(i, data2, stop);
      }
    }
  }
};
function objectBuilder$1(table2) {
  let b = table2._builder;
  if (!b) {
    const createRow = rowObjectBuilder(table2);
    const data2 = table2.data();
    if (table2.isOrdered() || table2.isFiltered()) {
      const indices = table2.indices();
      b = (row) => createRow(indices[row], data2);
    } else {
      b = (row) => createRow(row, data2);
    }
    table2._builder = b;
  }
  return b;
}
function assign(table2, ...others) {
  others = others.flat();
  const nrows = table2.numRows();
  const base = table2.reify();
  const cols = columnSet(base).groupby(base.groups());
  others.forEach((input) => {
    input = input instanceof Table$1 ? input : new Table$1(input);
    if (input.numRows() !== nrows) error("Assign row counts do not match");
    input = input.reify();
    input.columnNames((name2) => cols.add(name2, input.column(name2)));
  });
  return cols.new(table2);
}
function concat(table2, ...others) {
  others = others.flat();
  const trows = table2.numRows();
  const nrows = trows + others.reduce((n, t2) => n + t2.numRows(), 0);
  if (trows === nrows) return table2;
  const tables = [table2, ...others];
  const cols = columnSet();
  table2.columnNames().forEach((name2) => {
    const arr = Array(nrows);
    let row = 0;
    tables.forEach((table3) => {
      const col = table3.column(name2) || { at: () => NULL };
      table3.scan((trow) => arr[row++] = col.at(trow));
    });
    cols.add(name2, arr);
  });
  return cols.new(table2);
}
function relocate(table2, columns2, {
  before = void 0,
  after = void 0
} = {}) {
  const bef = before != null;
  const aft = after != null;
  if (!(bef || aft)) {
    error("relocate requires a before or after option.");
  }
  if (bef && aft) {
    error("relocate accepts only one of the before or after options.");
  }
  columns2 = resolve(table2, columns2);
  const anchors = [...resolve(table2, bef ? before : after).keys()];
  const anchor = bef ? anchors[0] : anchors.pop();
  const select2 = /* @__PURE__ */ new Map();
  table2.columnNames().forEach((name2) => {
    const assign2 = !columns2.has(name2);
    if (name2 === anchor) {
      if (aft && assign2) select2.set(name2, name2);
      for (const [key2, value2] of columns2) {
        select2.set(key2, value2);
      }
      if (aft) return;
    }
    if (assign2) select2.set(name2, name2);
  });
  return _select(table2, select2);
}
function bisector(compare2) {
  return {
    left(a, x, lo, hi) {
      if (lo == null) lo = 0;
      if (hi == null) hi = a.length;
      while (lo < hi) {
        const mid = lo + hi >>> 1;
        if (compare2(a[mid], x) < 0) lo = mid + 1;
        else hi = mid;
      }
      return lo;
    },
    right(a, x, lo, hi) {
      if (lo == null) lo = 0;
      if (hi == null) hi = a.length;
      while (lo < hi) {
        const mid = lo + hi >>> 1;
        if (compare2(a[mid], x) > 0) hi = mid;
        else lo = mid + 1;
      }
      return lo;
    }
  };
}
const bisect$1 = bisector(ascending);
function windowState(data2, frame, adjust, ops, aggrs) {
  let rows, peer, cells, result2, key2;
  const isPeer = (index) => peer[index - 1] === peer[index];
  const numOps = ops.length;
  const numAgg = aggrs.length;
  const evaluate = ops.length ? unroll$1(
    ["w", "r", "k"],
    "{" + concat$1(ops, (_, i) => `r[_${i}.id][k]=_${i}.value(w,_${i}.get);`) + "}",
    ops
  ) : () => {
  };
  const w = {
    i0: 0,
    i1: 0,
    index: 0,
    size: 0,
    peer: isPeer,
    init(partition, peers, results, group) {
      w.index = w.i0 = w.i1 = 0;
      w.size = peers.length;
      rows = partition;
      peer = peers;
      result2 = results;
      key2 = group;
      cells = aggrs ? aggrs.map((aggr) => aggr.init()) : null;
      for (let i = 0; i < numOps; ++i) {
        ops[i].init();
      }
      return w;
    },
    value(index, get2) {
      return get2(rows[index], data2);
    },
    step(idx) {
      const [f0, f1] = frame;
      const n = w.size;
      const p0 = w.i0;
      const p1 = w.i1;
      w.i0 = f0 != null ? Math.max(0, idx - Math.abs(f0)) : 0;
      w.i1 = f1 != null ? Math.min(n, idx + Math.abs(f1) + 1) : n;
      w.index = idx;
      if (adjust) {
        if (w.i0 > 0 && isPeer(w.i0)) {
          w.i0 = bisect$1.left(peer, peer[w.i0]);
        }
        if (w.i1 < n && isPeer(w.i1)) {
          w.i1 = bisect$1.right(peer, peer[w.i1 - 1]);
        }
      }
      for (let i = 0; i < numAgg; ++i) {
        const aggr = aggrs[i];
        const cell = cells[i];
        for (let j = p0; j < w.i0; ++j) {
          aggr.rem(cell, rows[j], data2);
        }
        for (let j = p1; j < w.i1; ++j) {
          aggr.add(cell, rows[j], data2);
        }
        aggr.write(cell, result2, key2);
      }
      evaluate(w, result2, key2);
      return result2;
    }
  };
  return w;
}
const frameValue = (op2) => (op2.frame || [null, null]).map((v) => Number.isFinite(v) ? Math.abs(v) : null);
const peersValue = (op2) => !!op2.peers;
function windowOp(spec) {
  const { id, name: name2, fields = [], params = [] } = spec;
  return {
    ...getWindow(name2).create(...params),
    get: fields.length ? fields[0] : null,
    id
  };
}
function window(table2, cols, exprs, result2 = {}, ops) {
  const data2 = table2.data();
  const states = windowStates(ops, data2);
  const nstate = states.length;
  const write = unroll$1(
    ["r", "d", "op"],
    "{" + concat$1(cols, (_, i) => `_${i}[r] = $${i}(r, d, op);`) + "}",
    cols,
    exprs
  );
  table2.partitions().forEach((rows, key2) => {
    const size = rows.length;
    const peers = windowPeers(table2, rows);
    for (let i = 0; i < nstate; ++i) {
      states[i].init(rows, peers, result2, key2);
    }
    const op2 = (id) => result2[id][key2];
    for (let index = 0; index < size; ++index) {
      for (let i = 0; i < nstate; ++i) {
        states[i].step(index);
      }
      write(rows[index], data2, op2);
    }
  });
}
function windowStates(ops, data2) {
  const map = {};
  ops.forEach((op2) => {
    const frame = frameValue(op2);
    const peers = peersValue(op2);
    const key2 = `${frame},${peers}`;
    const { aggOps, winOps } = map[key2] || (map[key2] = {
      frame,
      peers,
      aggOps: [],
      winOps: []
    });
    hasAggregate(op2.name) ? aggOps.push(op2) : winOps.push(windowOp(op2));
  });
  return Object.values(map).map((_) => windowState(
    data2,
    _.frame,
    _.peers,
    _.winOps,
    reducers(_.aggOps, _.frame[0] != null ? -1 : 1)
  ));
}
function windowPeers(table2, rows) {
  if (table2.isOrdered()) {
    const compare2 = table2.comparator();
    const data2 = table2.data();
    const nrows = rows.length;
    const peers = new Uint32Array(nrows);
    for (let i = 1, index = 0; i < nrows; ++i) {
      peers[i] = compare2(rows[i - 1], rows[i], data2) ? ++index : index;
    }
    return peers;
  } else {
    return rows;
  }
}
function isWindowed(op2) {
  return hasWindow(op2.name) || op2.frame && (Number.isFinite(op2.frame[0]) || Number.isFinite(op2.frame[1]));
}
function derive(table2, values2, options = {}) {
  const dt = _derive(table2, parse3(values2, { table: table2 }), options);
  return options.drop || options.before == null && options.after == null ? dt : relocate(
    dt,
    Object.keys(values2).filter((name2) => !table2.column(name2)),
    options
  );
}
function _derive(table2, { names, exprs, ops = [] }, options = {}) {
  const total = table2.totalRows();
  const cols = columnSet(options.drop ? null : table2);
  const data2 = names.map((name2) => cols.add(name2, Array(total)));
  const [aggOps, winOps] = segmentOps(ops);
  const size = table2.isGrouped() ? table2.groups().size : 1;
  const result2 = aggregate(
    table2,
    aggOps,
    repeat(ops.length, () => Array(size))
  );
  winOps.length ? window(table2, data2, exprs, result2, winOps) : output$1(table2, data2, exprs, result2);
  return cols.derive(table2);
}
function segmentOps(ops) {
  const aggOps = [];
  const winOps = [];
  const n = ops.length;
  for (let i = 0; i < n; ++i) {
    const op2 = ops[i];
    op2.id = i;
    (isWindowed(op2) ? winOps : aggOps).push(op2);
  }
  return [aggOps, winOps];
}
function output$1(table2, cols, exprs, result2) {
  const bits = table2.mask();
  const data2 = table2.data();
  const { keys: keys2 } = table2.groups() || {};
  const op2 = keys2 ? (id, row) => result2[id][keys2[row]] : (id) => result2[id][0];
  const m = cols.length;
  for (let j = 0; j < m; ++j) {
    const get2 = exprs[j];
    const col = cols[j];
    if (bits) {
      for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
        col[i] = get2(i, data2, op2);
      }
    } else {
      const n = table2.totalRows();
      for (let i = 0; i < n; ++i) {
        col[i] = get2(i, data2, op2);
      }
    }
  }
}
function filter(table2, criteria) {
  const test = parse3({ p: criteria }, { table: table2 });
  let predicate = test.exprs[0];
  if (test.ops.length) {
    const data2 = _derive(table2, test, { drop: true }).column("p");
    predicate = (row) => data2.at(row);
  }
  return _filter(table2, predicate);
}
function _filter(table2, predicate) {
  const n = table2.totalRows();
  const bits = table2.mask();
  const data2 = table2.data();
  const filter2 = new BitSet(n);
  if (bits) {
    for (let i = bits.next(0); i >= 0; i = bits.next(i + 1)) {
      if (predicate(i, data2)) filter2.set(i);
    }
  } else {
    for (let i = 0; i < n; ++i) {
      if (predicate(i, data2)) filter2.set(i);
    }
  }
  return table2.create({ filter: filter2 });
}
function dedupe(table2, ...keys2) {
  keys2 = keys2.flat();
  const gt = groupby(table2, keys2.length ? keys2 : table2.columnNames());
  return filter(gt, "row_number() === 1").ungroup().reify();
}
function rowLookup(table2, hash) {
  const lut = /* @__PURE__ */ new Map();
  table2.scan((row, data2) => {
    const key2 = hash(row, data2);
    if (key2 != null && key2 === key2) {
      lut.set(key2, row);
    }
  });
  return lut;
}
function indexLookup(idx, data2, hash) {
  const lut = /* @__PURE__ */ new Map();
  const n = idx.length;
  for (let i = 0; i < n; ++i) {
    const row = idx[i];
    const key2 = hash(row, data2);
    if (key2 != null && key2 === key2) {
      lut.has(key2) ? lut.get(key2).push(i) : lut.set(key2, [i]);
    }
  }
  return lut;
}
function intersect$1(a, b) {
  const set = new Set(b);
  return a.filter((x) => set.has(x));
}
function parseKey(name2, table2, params) {
  const exprs = /* @__PURE__ */ new Map();
  toArray(params).forEach((param, i) => {
    param = isNumber(param) ? table2.columnName(param) : param;
    isString(param) ? exprs.set(i, field$1(param)) : isFunction(param) || isObject(param) && param.expr ? exprs.set(i, param) : error(`Invalid ${name2} key value: ${param + ""}`);
  });
  const fn = parse3(exprs, { table: table2, aggregate: false, window: false });
  return keyFunction(fn.exprs, true);
}
function inferKeys(tableL, tableR, on) {
  if (!on) {
    const isect = intersect$1(tableL.columnNames(), tableR.columnNames());
    if (!isect.length) error("Natural join requires shared column names.");
    on = [isect, isect];
  } else if (isString(on)) {
    on = [on, on];
  } else if (isArray$2(on) && on.length === 1) {
    on = [on[0], on[0]];
  }
  return on;
}
function keyPredicate(tableL, tableR, onL, onR) {
  if (onL.length !== onR.length) {
    error("Mismatched number of join keys");
  }
  return [
    parseKey("join", tableL, onL),
    parseKey("join", tableR, onR)
  ];
}
function semijoin(tableL, tableR, on) {
  return join_filter(tableL, tableR, on, { anti: false });
}
function antijoin(tableL, tableR, on) {
  return join_filter(tableL, tableR, on, { anti: true });
}
function join_filter(tableL, tableR, on, options) {
  on = inferKeys(tableL, tableR, on);
  const predicate = isArray$2(on) ? keyPredicate(tableL, tableR, ...on.map(toArray)) : parse3({ on }, { join: [tableL, tableR] }).exprs[0];
  return _join_filter(tableL, tableR, predicate, options);
}
function _join_filter(tableL, tableR, predicate, options = {}) {
  const filter2 = new BitSet(tableL.totalRows());
  const join2 = isArray$2(predicate) ? hashSemiJoin : loopSemiJoin;
  join2(filter2, tableL, tableR, predicate);
  if (options.anti) {
    filter2.not().and(tableL.mask());
  }
  return tableL.create({ filter: filter2 });
}
function hashSemiJoin(filter2, tableL, tableR, [keyL, keyR]) {
  const lut = rowLookup(tableR, keyR);
  tableL.scan((rowL, data2) => {
    const rowR = lut.get(keyL(rowL, data2));
    if (rowR >= 0) filter2.set(rowL);
  });
}
function loopSemiJoin(filter2, tableL, tableR, predicate) {
  const nL = tableL.numRows();
  const nR = tableR.numRows();
  const dataL = tableL.data();
  const dataR = tableR.data();
  if (tableL.isFiltered() || tableR.isFiltered()) {
    const idxL = tableL.indices(false);
    const idxR = tableR.indices(false);
    for (let i = 0; i < nL; ++i) {
      const rowL = idxL[i];
      for (let j = 0; j < nR; ++j) {
        if (predicate(rowL, dataL, idxR[j], dataR)) {
          filter2.set(rowL);
          break;
        }
      }
    }
  } else {
    for (let i = 0; i < nL; ++i) {
      for (let j = 0; j < nR; ++j) {
        if (predicate(i, dataL, j, dataR)) {
          filter2.set(i);
          break;
        }
      }
    }
  }
}
function except(table2, ...others) {
  others = others.flat();
  if (others.length === 0) return table2;
  const names = table2.columnNames();
  return dedupe(others.reduce((a, b) => antijoin(a, b.select(names)), table2));
}
function unroll(table2, values2, options) {
  return _unroll(
    table2,
    parseValue("unroll", table2, values2),
    options && options.drop ? { ...options, drop: parseValue("unroll", table2, options.drop).names } : options
  );
}
function _unroll(table2, { names = [], exprs = [], ops = [] }, options = {}) {
  if (!names.length) return table2;
  const limit = options.limit > 0 ? +options.limit : Infinity;
  const index = options.index ? options.index === true ? "index" : options.index + "" : null;
  const drop = new Set(options.drop);
  const get2 = aggregateGet(table2, ops, exprs);
  const cols = columnSet();
  const nset = new Set(names);
  const priors = [];
  const copies = [];
  const unroll2 = [];
  table2.columnNames().forEach((name2) => {
    if (!drop.has(name2)) {
      const col = cols.add(name2, []);
      if (!nset.has(name2)) {
        priors.push(table2.column(name2));
        copies.push(col);
      }
    }
  });
  names.forEach((name2) => {
    if (!drop.has(name2)) {
      if (!cols.has(name2)) cols.add(name2, []);
      unroll2.push(cols.data[name2]);
    }
  });
  const icol = index ? cols.add(index, []) : null;
  let start = 0;
  const m = priors.length;
  const n = unroll2.length;
  const copy = (row, maxlen) => {
    for (let i = 0; i < m; ++i) {
      copies[i].length = start + maxlen;
      copies[i].fill(priors[i].at(row), start, start + maxlen);
    }
  };
  const indices = icol ? (row, maxlen) => {
    for (let i = 0; i < maxlen; ++i) {
      icol[row + i] = i;
    }
  } : () => {
  };
  if (n === 1) {
    const fn = get2[0];
    const col = unroll2[0];
    table2.scan((row, data2) => {
      const array2 = toArray(fn(row, data2));
      const maxlen = Math.min(array2.length, limit);
      copy(row, maxlen);
      for (let j = 0; j < maxlen; ++j) {
        col[start + j] = array2[j];
      }
      indices(start, maxlen);
      start += maxlen;
    });
  } else {
    table2.scan((row, data2) => {
      let maxlen = 0;
      const arrays = get2.map((fn) => {
        const value2 = toArray(fn(row, data2));
        maxlen = Math.min(Math.max(maxlen, value2.length), limit);
        return value2;
      });
      copy(row, maxlen);
      for (let i = 0; i < n; ++i) {
        const col = unroll2[i];
        const arr = arrays[i];
        for (let j = 0; j < maxlen; ++j) {
          col[start + j] = arr[j];
        }
      }
      indices(start, maxlen);
      start += maxlen;
    });
  }
  return cols.new(table2);
}
function fold(table2, values2, options) {
  return _fold(table2, parseValue("fold", table2, values2), options);
}
function _fold(table2, { names = [], exprs = [], ops = [] }, options = {}) {
  if (names.length === 0) return table2;
  const [k = "key", v = "value"] = options.as || [];
  const vals = aggregateGet(table2, ops, exprs);
  return _unroll(
    table2,
    {
      names: [k, v],
      exprs: [() => names, (row, data2) => vals.map((fn) => fn(row, data2))]
    },
    { ...options, drop: names }
  );
}
function ungroup(table2) {
  return table2.isGrouped() ? table2.create({ groups: null }) : table2;
}
function impute(table2, values2, options = {}) {
  values2 = parse3(values2, { table: table2 });
  values2.names.forEach(
    (name2) => table2.column(name2) ? 0 : error(`Invalid impute column ${toString$1(name2)}`)
  );
  if (options.expand) {
    const opt2 = { preparse: preparse$1, window: false, aggronly: true };
    const params = parseValue("impute", table2, options.expand, opt2);
    const result2 = _rollup(ungroup(table2), params);
    return _impute(
      table2,
      values2,
      params.names,
      params.names.map((name2) => result2.get(name2, 0))
    );
  } else {
    return _impute(table2, values2);
  }
}
function preparse$1(map) {
  map.forEach(
    (value2, key2) => value2.field ? map.set(key2, array_agg_distinct(value2 + "")) : 0
  );
}
function _impute(table2, values2, keys2, arrays) {
  const write = keys2 && keys2.length;
  table2 = write ? expand(table2, keys2, arrays) : table2;
  const { names, exprs, ops } = values2;
  const gets = aggregateGet(table2, ops, exprs);
  const cols = write ? null : columnSet(table2);
  const rows = table2.totalRows();
  names.forEach((name2, i) => {
    const col = table2.column(name2);
    const out = write ? col : cols.add(name2, Array(rows));
    const get2 = gets[i];
    table2.scan((idx) => {
      const v = col.at(idx);
      out[idx] = !isValid(v) ? get2(idx) : v;
    });
  });
  return write ? table2 : table2.create(cols);
}
function expand(table2, keys2, values2) {
  const groups = table2.groups();
  const data2 = table2.data();
  const keyNames = (groups ? groups.names : []).concat(keys2);
  const keyGet = (groups ? groups.get : []).concat(keys2.map((key2) => table2.getter(key2)));
  const hash = /* @__PURE__ */ new Set();
  const keyTable = keyFunction(keyGet);
  table2.scan((idx, data3) => hash.add(keyTable(idx, data3)));
  const names = table2.columnNames();
  const cols = columnSet();
  const out = names.map((name2) => cols.add(name2, []));
  names.forEach((name2, i) => {
    const old = data2[name2];
    const col = out[i];
    table2.scan((row) => col.push(old.at(row)));
  });
  const keyEnum = keyFunction(keyGet.map((k, i) => (a) => a[i]));
  const set = unroll$1(
    "v",
    "{" + out.map((_, i) => `_${i}.push(v[$${i}]);`).join("") + "}",
    out,
    names.map((name2) => keyNames.indexOf(name2))
  );
  if (groups) {
    let row = groups.keys.length;
    const prod = values2.reduce((p, a) => p * a.length, groups.size);
    const keys3 = new Uint32Array(prod + (row - hash.size));
    keys3.set(groups.keys);
    enumerate(groups, values2, (vec, idx) => {
      if (!hash.has(keyEnum(vec))) {
        set(vec);
        keys3[row++] = idx[0];
      }
    });
    cols.groupby({ ...groups, keys: keys3 });
  } else {
    enumerate(groups, values2, (vec) => {
      if (!hash.has(keyEnum(vec))) set(vec);
    });
  }
  return cols.new(table2);
}
function enumerate(groups, values2, callback) {
  const offset2 = groups ? groups.get.length : 0;
  const pad3 = groups ? 1 : 0;
  const len = pad3 + values2.length;
  const lens = new Int32Array(len);
  const idxs = new Int32Array(len);
  const set = [];
  if (groups) {
    const { get: get2, rows, size } = groups;
    lens[0] = size;
    set.push((vec2, idx) => {
      const row = rows[idx];
      for (let i = 0; i < offset2; ++i) {
        vec2[i] = get2[i](row);
      }
    });
  }
  values2.forEach((a, i) => {
    const j = i + offset2;
    lens[i + pad3] = a.length;
    set.push((vec2, idx) => vec2[j] = a[idx]);
  });
  const vec = Array(offset2 + values2.length);
  for (let i = 0; i < len; ++i) {
    set[i](vec, 0);
  }
  callback(vec, idxs);
  for (let i = len - 1; i >= 0; ) {
    const idx = ++idxs[i];
    if (idx < lens[i]) {
      set[i](vec, idx);
      callback(vec, idxs);
      i = len - 1;
    } else {
      idxs[i] = 0;
      set[i](vec, 0);
      --i;
    }
  }
}
function intersect(table2, ...others) {
  others = others.flat();
  const names = table2.columnNames();
  return others.length ? dedupe(others.reduce((a, b) => semijoin(a, b.select(names)), table2)) : table2.reify([]);
}
const OPT_L = { aggregate: false, window: false };
const OPT_R = { ...OPT_L, index: 1 };
const NONE = -Infinity;
function cross(table2, other, values2, options) {
  return join(
    table2,
    other,
    () => true,
    values2,
    { ...options, left: true, right: true }
  );
}
function join(tableL, tableR, on, values2, options = {}) {
  on = inferKeys(tableL, tableR, on);
  const optParse = { join: [tableL, tableR] };
  let predicate;
  if (isArray$2(on)) {
    const [onL, onR] = on.map(toArray);
    predicate = keyPredicate(tableL, tableR, onL, onR);
    if (!values2) {
      values2 = inferValues(tableL, onL, onR, options);
    }
  } else {
    predicate = parse3({ on }, optParse).exprs[0];
    if (!values2) {
      values2 = [all(), all()];
    }
  }
  return _join(
    tableL,
    tableR,
    predicate,
    parseValues$1(tableL, tableR, values2, optParse, options && options.suffix),
    options
  );
}
function inferValues(tableL, onL, onR, options) {
  const isect = [];
  onL.forEach((s, i) => isString(s) && s === onR[i] ? isect.push(s) : 0);
  const vR = not(isect);
  if (options.left && options.right) {
    const shared = new Set(isect);
    return [
      tableL.columnNames().map((s) => {
        const c = `[${toString$1(s)}]`;
        return shared.has(s) ? { [s]: `(a, b) => a${c} == null ? b${c} : a${c}` } : s;
      }),
      vR
    ];
  }
  return options.right ? [vR, all()] : [all(), vR];
}
function parseValues$1(tableL, tableR, values2, optParse, suffix = []) {
  if (isArray$2(values2)) {
    let vL, vR, vJ, n = values2.length;
    vL = vR = vJ = { names: [], exprs: [] };
    if (n--) {
      vL = parseValue("join", tableL, values2[0], optParse);
    }
    if (n--) {
      vR = parseValue("join", tableR, values2[1], OPT_R);
    }
    if (n--) {
      vJ = parse3(values2[2], optParse);
    }
    const rename2 = /* @__PURE__ */ new Set();
    const namesL = new Set(vL.names);
    vR.names.forEach((name2) => {
      if (namesL.has(name2)) {
        rename2.add(name2);
      }
    });
    if (rename2.size) {
      suffix[0] !== "" && rekey(vL.names, rename2, suffix[0] || "_1");
      suffix[1] !== "" && rekey(vR.names, rename2, suffix[1] || "_2");
    }
    return {
      names: vL.names.concat(vR.names, vJ.names),
      exprs: vL.exprs.concat(vR.exprs, vJ.exprs)
    };
  } else {
    return parse3(values2, optParse);
  }
}
function rekey(names, rename2, suffix) {
  names.forEach((name2, i) => rename2.has(name2) ? names[i] = name2 + suffix : 0);
}
function emitter(columns2, getters) {
  const args = ["i", "a", "j", "b"];
  return unroll$1(
    args,
    "{" + concat$1(columns2, (_, i) => `_${i}.push($${i}(${args}));`) + "}",
    columns2,
    getters
  );
}
function _join(tableL, tableR, predicate, { names, exprs }, options = {}) {
  const dataL = tableL.data();
  const idxL = tableL.indices(false);
  const nL = idxL.length;
  const hitL = new Int32Array(nL);
  const dataR = tableR.data();
  const idxR = tableR.indices(false);
  const nR = idxR.length;
  const hitR = new Int32Array(nR);
  const ncols = names.length;
  const cols = columnSet();
  const columns2 = Array(ncols);
  const getters = Array(ncols);
  for (let i = 0; i < names.length; ++i) {
    columns2[i] = cols.add(names[i], []);
    getters[i] = exprs[i];
  }
  const emit = emitter(columns2, getters);
  const join2 = isArray$2(predicate) ? hashJoin : loopJoin;
  join2(emit, predicate, dataL, dataR, idxL, idxR, hitL, hitR, nL, nR);
  if (options.left) {
    for (let i = 0; i < nL; ++i) {
      if (!hitL[i]) {
        emit(idxL[i], dataL, NONE, dataR);
      }
    }
  }
  if (options.right) {
    for (let j = 0; j < nR; ++j) {
      if (!hitR[j]) {
        emit(NONE, dataL, idxR[j], dataR);
      }
    }
  }
  return cols.new(tableL);
}
function loopJoin(emit, predicate, dataL, dataR, idxL, idxR, hitL, hitR, nL, nR) {
  for (let i = 0; i < nL; ++i) {
    const rowL = idxL[i];
    for (let j = 0; j < nR; ++j) {
      const rowR = idxR[j];
      if (predicate(rowL, dataL, rowR, dataR)) {
        emit(rowL, dataL, rowR, dataR);
        hitL[i] = 1;
        hitR[j] = 1;
      }
    }
  }
}
function hashJoin(emit, [keyL, keyR], dataL, dataR, idxL, idxR, hitL, hitR, nL, nR) {
  let dataScan, keyScan, hitScan, idxScan;
  let dataHash, keyHash, hitHash, idxHash;
  let emitScan = emit;
  if (nL >= nR) {
    dataScan = dataL;
    keyScan = keyL;
    hitScan = hitL;
    idxScan = idxL;
    dataHash = dataR;
    keyHash = keyR;
    hitHash = hitR;
    idxHash = idxR;
  } else {
    dataScan = dataR;
    keyScan = keyR;
    hitScan = hitR;
    idxScan = idxR;
    dataHash = dataL;
    keyHash = keyL;
    hitHash = hitL;
    idxHash = idxL;
    emitScan = (i, a, j, b) => emit(j, b, i, a);
  }
  const lut = indexLookup(idxHash, dataHash, keyHash);
  const m = idxScan.length;
  for (let j = 0; j < m; ++j) {
    const rowScan = idxScan[j];
    const list2 = lut.get(keyScan(rowScan, dataScan));
    if (list2) {
      const n = list2.length;
      for (let k = 0; k < n; ++k) {
        const i = list2[k];
        emitScan(rowScan, dataScan, idxHash[i], dataHash);
        hitHash[i] = 1;
      }
      hitScan[j] = 1;
    }
  }
}
function lookup(tableL, tableR, on, ...values2) {
  on = inferKeys(tableL, tableR, on);
  values2 = values2.length === 0 ? [not(tableL.columnNames())] : values2.flat();
  return _lookup(
    tableL,
    tableR,
    [parseKey("lookup", tableL, on[0]), parseKey("lookup", tableR, on[1])],
    parseValue("lookup", tableR, values2)
  );
}
function _lookup(tableL, tableR, [keyL, keyR], { names, exprs, ops = [] }) {
  const cols = columnSet(tableL);
  const total = tableL.totalRows();
  names.forEach((name2) => cols.add(name2, Array(total).fill(NULL)));
  const lut = rowLookup(tableR, keyR);
  const set = unroll$1(
    ["lr", "rr", "data"],
    "{" + concat$1(names, (_, i) => `_[${i}][lr] = $[${i}](rr, data);`) + "}",
    names.map((name2) => cols.data[name2]),
    aggregateGet(tableR, ops, exprs)
  );
  const dataR = tableR.data();
  tableL.scan((lrow, data2) => {
    const rrow = lut.get(keyL(lrow, data2));
    if (rrow >= 0) set(lrow, rrow, dataR);
  });
  return cols.derive(tableL);
}
const _compare = (u, v, lt, gt) => `((u = ${u}) < (v = ${v}) || u == null) && v != null ? ${lt} : (u > v || v == null) && u != null ? ${gt} : ((v = v instanceof Date ? +v : v), (u = u instanceof Date ? +u : u)) !== u && v === v ? ${lt} : v !== v && u === u ? ${gt} : `;
const _collate = (u, v, lt, gt, f) => `(v = ${v}, (u = ${u}) == null && v == null) ? 0 : v == null ? ${gt} : u == null ? ${lt} : (u = ${f}(u,v)) ? u : `;
function compare(table2, fields) {
  const names = [];
  const exprs = [];
  const fn = [];
  let keys2 = null, opA = "0", opB = "0";
  if (table2.isGrouped()) {
    keys2 = table2.groups().keys;
    opA = "ka";
    opB = "kb";
  }
  const { ops } = parse3(fields, {
    table: table2,
    value: (name2, node) => {
      names.push(name2);
      if (node.escape) {
        const f = (i) => `fn[${fn.length}](${i}, data)`;
        exprs.push([f("a"), f("b")]);
        fn.push(node.escape);
      } else {
        exprs.push([
          codegen(node, { index: "a", op: opA }),
          codegen(node, { index: "b", op: opB })
        ]);
      }
    },
    window: false
  });
  const result2 = aggregate(table2, ops);
  const op2 = (id, row) => result2[id][row];
  const n = names.length;
  let code = "return (a, b) => {" + (op2 && table2.isGrouped() ? "const ka = keys[a], kb = keys[b];" : "") + "let u, v; return ";
  for (let i = 0; i < n; ++i) {
    const field2 = fields.get(names[i]);
    const o = field2.desc ? -1 : 1;
    const [u, v] = exprs[i];
    if (field2.collate) {
      code += _collate(u, v, -o, o, `${o < 0 ? "-" : ""}fn[${fn.length}]`);
      fn.push(field2.collate);
    } else {
      code += _compare(u, v, -o, o);
    }
  }
  code += "0;};";
  return Function("op", "keys", "fn", "data", code)(op2, keys2, fn, table2.data());
}
function orderby(table2, ...values2) {
  return _orderby(table2, parseValues(table2, values2.flat()));
}
function parseValues(table2, params) {
  let index = -1;
  const exprs = /* @__PURE__ */ new Map();
  const add = (val) => exprs.set(++index + "", val);
  params.forEach((param) => {
    const expr = param.expr != null ? param.expr : param;
    if (isObject(expr) && !isFunction(expr)) {
      for (const key2 in expr) add(expr[key2]);
    } else {
      add(
        isNumber(expr) ? field$1(param, table2.columnName(expr)) : isString(expr) ? field$1(param) : isFunction(expr) ? param : error(`Invalid orderby field: ${param + ""}`)
      );
    }
  });
  return compare(table2, exprs);
}
function _orderby(table2, comparator) {
  return table2.create({ order: comparator });
}
function pivot(table2, on, values2, options) {
  return _pivot(
    table2,
    parseValue("fold", table2, on),
    parseValue("fold", table2, values2, { preparse, window: false, aggronly: true }),
    options
  );
}
function preparse(map) {
  map.forEach(
    (value2, key2) => value2.field ? map.set(key2, any(value2 + "")) : 0
  );
}
const opt = (value2, defaultValue) => value2 != null ? value2 : defaultValue;
function _pivot(table2, on, values2, options = {}) {
  const { keys: keys2, keyColumn } = pivotKeys(table2, on, options);
  const vsep = opt(options.valueSeparator, "_");
  const namefn = values2.names.length > 1 ? (i, name2) => name2 + vsep + keys2[i] : (i) => keys2[i];
  const results = keys2.map(
    (k) => aggregate(table2, values2.ops.map((op2) => {
      if (op2.name === "count") {
        const fn = (r) => k === keyColumn[r] ? 1 : NaN;
        fn.toString = () => k + ":1";
        return { ...op2, name: "sum", fields: [fn] };
      }
      const fields = op2.fields.map((f) => {
        const fn = (r, d) => k === keyColumn[r] ? f(r, d) : NaN;
        fn.toString = () => k + ":" + f;
        return fn;
      });
      return { ...op2, fields };
    }))
  );
  return output(values2, namefn, table2.groups(), results).new(table2);
}
function pivotKeys(table2, on, options) {
  const limit = options.limit > 0 ? +options.limit : Infinity;
  const sort = opt(options.sort, true);
  const ksep = opt(options.keySeparator, "_");
  const get2 = aggregateGet(table2, on.ops, on.exprs);
  const key2 = get2.length === 1 ? get2[0] : (row, data2) => get2.map((fn) => fn(row, data2)).join(ksep);
  const kcol = Array(table2.totalRows());
  table2.scan((row, data2) => kcol[row] = key2(row, data2));
  const uniq = aggregate(
    ungroup(table2),
    [{
      id: 0,
      name: "array_agg_distinct",
      fields: [((row) => kcol[row])],
      params: []
    }]
  )[0][0];
  const keys2 = sort ? uniq.sort() : uniq;
  return {
    keys: Number.isFinite(limit) ? keys2.slice(0, limit) : keys2,
    keyColumn: kcol
  };
}
function output({ names, exprs }, namefn, groups, results) {
  const size = groups ? groups.size : 1;
  const cols = columnSet();
  const m = results.length;
  const n = names.length;
  let result2;
  const op2 = (id, row) => result2[id][row];
  if (groups) groupOutput(cols, groups);
  for (let i = 0; i < n; ++i) {
    const get2 = exprs[i];
    if (get2.field != null) {
      for (let j = 0; j < m; ++j) {
        cols.add(namefn(j, names[i]), results[j][get2.field]);
      }
    } else if (size > 1) {
      for (let j = 0; j < m; ++j) {
        result2 = results[j];
        const col = cols.add(namefn(j, names[i]), Array(size));
        for (let k = 0; k < size; ++k) {
          col[k] = get2(k, null, op2);
        }
      }
    } else {
      for (let j = 0; j < m; ++j) {
        result2 = results[j];
        cols.add(namefn(j, names[i]), [get2(0, null, op2)]);
      }
    }
  }
  return cols;
}
function reduce(table2, reducer) {
  const cols = columnSet();
  const groups = table2.groups();
  const { get: get2, names = [], rows, size = 1 } = groups || {};
  const counts = new Uint32Array(size + 1);
  names.forEach((name2) => cols.add(name2, null));
  const cells = groups ? reduceGroups(table2, reducer, groups) : [reduceFlat(table2, reducer)];
  reducer.outputs().map((name2) => cols.add(name2, []));
  const n = counts.length - 1;
  let len = 0;
  for (let i = 0; i < n; ++i) {
    len += counts[i + 1] = reducer.write(cells[i], cols.data, counts[i]);
  }
  if (groups) {
    const data2 = table2.data();
    names.forEach((name2, index) => {
      const column = cols.data[name2] = Array(len);
      const getter = get2[index];
      for (let i = 0, j = 0; i < size; ++i) {
        column.fill(getter(rows[i], data2), j, j += counts[i + 1]);
      }
    });
  }
  return cols.new(table2);
}
function rename(table2, ...columns2) {
  const map = /* @__PURE__ */ new Map();
  table2.columnNames((x) => (map.set(x, x), 0));
  return _select(table2, resolve(table2, columns2.flat(), map));
}
function sample$1(buffer2, replace2, index, weight) {
  return (replace2 ? weight ? sampleRW : sampleRU : weight ? sampleNW : sampleNU)(buffer2.length, buffer2, index, weight);
}
function sampleRU(size, buffer2, index) {
  const n = index.length;
  for (let i = 0; i < size; ++i) {
    buffer2[i] = index[n * random$1() | 0];
  }
  return buffer2;
}
function sampleRW(size, buffer2, index, weight) {
  const n = index.length;
  const w = new Float64Array(n);
  let sum = 0;
  for (let i = 0; i < n; ++i) {
    w[i] = sum += weight(index[i]);
  }
  const bisect2 = bisector(ascending).right;
  for (let i = 0; i < size; ++i) {
    buffer2[i] = index[bisect2(w, sum * random$1())];
  }
  return buffer2;
}
function sampleNU(size, buffer2, index) {
  const n = index.length;
  if (size >= n) return index;
  for (let i = 0; i < size; ++i) {
    buffer2[i] = index[i];
  }
  for (let i = size; i < n; ++i) {
    const j = i * random$1();
    if (j < size) {
      buffer2[j | 0] = index[i];
    }
  }
  return buffer2;
}
function sampleNW(size, buffer2, index, weight) {
  const n = index.length;
  if (size >= n) return index;
  const w = new Float32Array(n);
  const k = new Uint32Array(n);
  for (let i = 0; i < n; ++i) {
    k[i] = i;
    w[i] = -Math.log(random$1()) / weight(index[i]);
  }
  k.sort((a, b) => w[a] - w[b]);
  for (let i = 0; i < size; ++i) {
    buffer2[i] = index[k[i]];
  }
  return buffer2;
}
function shuffle(array2, lo = 0, hi = array2.length) {
  let n = hi - (lo = +lo);
  while (n) {
    const i = random$1() * n-- | 0;
    const v = array2[n + lo];
    array2[n + lo] = array2[i + lo];
    array2[i + lo] = v;
  }
  return array2;
}
function sample(table2, size, options = {}) {
  return _sample(
    table2,
    parseSize(table2, size),
    parseWeight(table2, options.weight),
    options
  );
}
const get = (col) => (row) => col.at(row) || 0;
function parseSize(table2, size) {
  return isNumber(size) ? () => size : get(_rollup(table2, parse3({ size }, { table: table2, window: false })).column("size"));
}
function parseWeight(table2, w) {
  if (w == null) return null;
  w = isNumber(w) ? table2.columnName(w) : w;
  return get(
    isString(w) ? table2.column(w) : _derive(table2, parse3({ w }, { table: table2 }), { drop: true }).column("w")
  );
}
function _sample(table2, size, weight, options = {}) {
  const { replace: replace2, shuffle: shuffle$1 } = options;
  const parts = table2.partitions(false);
  let total = 0;
  size = parts.map((idx, group) => {
    let s = size(group);
    total += s = replace2 ? s : Math.min(idx.length, s);
    return s;
  });
  const samples = new Uint32Array(total);
  let curr = 0;
  parts.forEach((idx, group) => {
    const sz = size[group];
    const buf2 = samples.subarray(curr, curr += sz);
    if (!replace2 && sz === idx.length) {
      buf2.set(idx);
    } else {
      sample$1(buf2, replace2, idx, weight);
    }
  });
  if (shuffle$1 !== false && (parts.length > 1 || !replace2)) {
    shuffle(samples);
  }
  return table2.reify(samples);
}
function slice$1(start = 0, end = Infinity) {
  return `${prep$1(start)} < row_number() && row_number() <= ${prep$1(end)}`;
}
function prep$1(index) {
  return index < 0 ? `count() + ${index}` : index;
}
function slice(table2, start = 0, end = Infinity) {
  if (table2.isGrouped()) {
    return filter(table2, slice$1(start, end)).reify();
  }
  const indices = [];
  const nrows = table2.numRows();
  start = Math.max(0, start + (start < 0 ? nrows : 0));
  end = Math.min(nrows, Math.max(0, end + (end < 0 ? nrows : 0)));
  table2.scan((row) => indices.push(row), true, end - start, start);
  return table2.reify(indices);
}
function spread(table2, values2, options) {
  return _spread(table2, parseValue("spread", table2, values2), options);
}
function _spread(table2, { names, exprs, ops = [] }, options = {}) {
  if (names.length === 0) return table2;
  const as = names.length === 1 && options.as || [];
  const drop = options.drop == null ? true : !!options.drop;
  const limit = options.limit == null ? as.length || Infinity : Math.max(1, +options.limit || 1);
  const get2 = aggregateGet(table2, ops, exprs);
  const cols = columnSet();
  const map = names.reduce((map2, name2, i) => map2.set(name2, i), /* @__PURE__ */ new Map());
  const add = (index, name2) => {
    const columns2 = spreadCols(table2, get2[index], limit);
    const n = columns2.length;
    for (let i = 0; i < n; ++i) {
      cols.add(as[i] || `${name2}_${i + 1}`, columns2[i]);
    }
  };
  table2.columnNames().forEach((name2) => {
    if (map.has(name2)) {
      if (!drop) cols.add(name2, table2.column(name2));
      add(map.get(name2), name2);
      map.delete(name2);
    } else {
      cols.add(name2, table2.column(name2));
    }
  });
  map.forEach(add);
  return cols.derive(table2);
}
function spreadCols(table2, get2, limit) {
  const nrows = table2.totalRows();
  const columns2 = [];
  table2.scan((row, data2) => {
    const values2 = toArray(get2(row, data2));
    const n = Math.min(values2.length, limit);
    while (columns2.length < n) {
      columns2.push(Array(nrows).fill(NULL));
    }
    for (let i = 0; i < n; ++i) {
      columns2[i][row] = values2[i];
    }
  });
  return columns2;
}
function union$1(table2, ...others) {
  return dedupe(concat(table2, others.flat()));
}
function unorder(table2) {
  return table2.isOrdered() ? table2.create({ order: null }) : table2;
}
const MAGIC = Uint8Array.of(65, 82, 82, 79, 87, 49);
const EOS = Uint8Array.of(255, 255, 255, 255, 0, 0, 0, 0);
const Version = (
  /** @type {const} */
  {
    /** 0.1.0 (October 2016). */
    V1: 0,
    /** >= 0.8.0 (December 2017). Non-backwards compatible with V3. */
    V4: 3,
    /**
     * >= 1.0.0 (July 2020). Backwards compatible with V4 (V5 readers can read V4
     * metadata and IPC messages). Implementations are recommended to provide a
     * V4 compatibility mode with V5 format changes disabled.
     *
     * Incompatible changes between V4 and V5:
     * - Union buffer layout has changed.
     *   In V5, Unions don't have a validity bitmap buffer.
     */
    V5: 4
  }
);
const Endianness = (
  /** @type {const} */
  {
    Little: 0
  }
);
const MessageHeader = (
  /** @type {const} */
  {
    NONE: 0,
    /**
     * A Schema describes the columns in a record batch.
     */
    Schema: 1,
    /**
     * For sending dictionary encoding information. Any Field can be
     * dictionary-encoded, but in this case none of its children may be
     * dictionary-encoded.
     * There is one vector / column per dictionary, but that vector / column
     * may be spread across multiple dictionary batches by using the isDelta
     * flag.
     */
    DictionaryBatch: 2,
    /**
     * A data header describing the shared memory layout of a "record" or "row"
     * batch. Some systems call this a "row batch" internally and others a "record
     * batch".
     */
    RecordBatch: 3,
    /**
     * EXPERIMENTAL: Metadata for n-dimensional arrays, aka "tensors" or
     * "ndarrays". Arrow implementations in general are not required to implement
     * this type.
     *
     * Not currently supported by Flechette.
     */
    Tensor: 4,
    /**
     * EXPERIMENTAL: Metadata for n-dimensional sparse arrays, aka "sparse
     * tensors". Arrow implementations in general are not required to implement
     * this type.
     *
     * Not currently supported by Flechette.
     */
    SparseTensor: 5
  }
);
const Type = (
  /** @type {const} */
  {
    /**
     * Dictionary types compress data by using a set of integer indices to
     * lookup potentially repeated vales in a separate dictionary of values.
     *
     * This type entry is provided for API convenience, it does not occur
     * in actual Arrow IPC binary data.
     */
    Dictionary: -1,
    /** No data type. Included for flatbuffer compatibility. */
    NONE: 0,
    /** Null values only. */
    Null: 1,
    /** Integers, either signed or unsigned, with 8, 16, 32, or 64 bit widths. */
    Int: 2,
    /** Floating point numbers with 16, 32, or 64 bit precision. */
    Float: 3,
    /** Opaque binary data. */
    Binary: 4,
    /** Unicode with UTF-8 encoding. */
    Utf8: 5,
    /** Booleans represented as 8 bit bytes. */
    Bool: 6,
    /**
     * Exact decimal value represented as an integer value in two's complement.
     * Currently only 128-bit (16-byte) and 256-bit (32-byte) integers are used.
     * The representation uses the endianness indicated in the schema.
     */
    Decimal: 7,
    /**
     * Date is either a 32-bit or 64-bit signed integer type representing an
     * elapsed time since UNIX epoch (1970-01-01), stored in either of two units:
     * - Milliseconds (64 bits) indicating UNIX time elapsed since the epoch (no
     * leap seconds), where the values are evenly divisible by 86400000
     * - Days (32 bits) since the UNIX epoch
     */
    Date: 8,
    /**
     * Time is either a 32-bit or 64-bit signed integer type representing an
     * elapsed time since midnight, stored in either of four units: seconds,
     * milliseconds, microseconds or nanoseconds.
     *
     * The integer `bitWidth` depends on the `unit` and must be one of the following:
     * - SECOND and MILLISECOND: 32 bits
     * - MICROSECOND and NANOSECOND: 64 bits
     *
     * The allowed values are between 0 (inclusive) and 86400 (=24*60*60) seconds
     * (exclusive), adjusted for the time unit (for example, up to 86400000
     * exclusive for the MILLISECOND unit).
     * This definition doesn't allow for leap seconds. Time values from
     * measurements with leap seconds will need to be corrected when ingesting
     * into Arrow (for example by replacing the value 86400 with 86399).
     */
    Time: 9,
    /**
     * Timestamp is a 64-bit signed integer representing an elapsed time since a
     * fixed epoch, stored in either of four units: seconds, milliseconds,
     * microseconds or nanoseconds, and is optionally annotated with a timezone.
     *
     * Timestamp values do not include any leap seconds (in other words, all
     * days are considered 86400 seconds long).
     *
     * The timezone is an optional string for the name of a timezone, one of:
     *
     *  - As used in the Olson timezone database (the "tz database" or
     *    "tzdata"), such as "America/New_York".
     *  - An absolute timezone offset of the form "+XX:XX" or "-XX:XX",
     *    such as "+07:30".
     *
     * Whether a timezone string is present indicates different semantics about
     * the data.
     */
    Timestamp: 10,
    /**
     * A "calendar" interval which models types that don't necessarily
     * have a precise duration without the context of a base timestamp (e.g.
     * days can differ in length during day light savings time transitions).
     * All integers in the units below are stored in the endianness indicated
     * by the schema.
     *
     *  - YEAR_MONTH - Indicates the number of elapsed whole months, stored as
     *    4-byte signed integers.
     *  - DAY_TIME - Indicates the number of elapsed days and milliseconds (no
     *    leap seconds), stored as 2 contiguous 32-bit signed integers (8-bytes
     *    in total). Support of this IntervalUnit is not required for full arrow
     *    compatibility.
     *  - MONTH_DAY_NANO - A triple of the number of elapsed months, days, and
     *    nanoseconds. The values are stored contiguously in 16-byte blocks.
     *    Months and days are encoded as 32-bit signed integers and nanoseconds
     *    is encoded as a 64-bit signed integer. Nanoseconds does not allow for
     *    leap seconds. Each field is independent (e.g. there is no constraint
     *    that nanoseconds have the same sign as days or that the quantity of
     *    nanoseconds represents less than a day's worth of time).
     */
    Interval: 11,
    /**
     * List (vector) data supporting variably-sized lists.
     * A list has a single child data type for list entries.
     */
    List: 12,
    /**
     * A struct consisting of multiple named child data types.
     */
    Struct: 13,
    /**
     * A union is a complex type with parallel child data types. By default ids
     * in the type vector refer to the offsets in the children. Optionally
     * typeIds provides an indirection between the child offset and the type id.
     * For each child `typeIds[offset]` is the id used in the type vector.
     */
    Union: 14,
    /**
     * Binary data where each entry has the same fixed size.
     */
    FixedSizeBinary: 15,
    /**
     * List (vector) data where every list has the same fixed size.
     * A list has a single child data type for list entries.
     */
    FixedSizeList: 16,
    /**
     * A Map is a logical nested type that is represented as
     * List<entries: Struct<key: K, value: V>>
     *
     * In this layout, the keys and values are each respectively contiguous. We do
     * not constrain the key and value types, so the application is responsible
     * for ensuring that the keys are hashable and unique. Whether the keys are sorted
     * may be set in the metadata for this field.
     *
     * In a field with Map type, the field has a child Struct field, which then
     * has two children: key type and the second the value type. The names of the
     * child fields may be respectively "entries", "key", and "value", but this is
     * not enforced.
     *
     * Map
     * ```text
     *   - child[0] entries: Struct
     *   - child[0] key: K
     *   - child[1] value: V
     *  ```
     * Neither the "entries" field nor the "key" field may be nullable.
     *
     * The metadata is structured so that Arrow systems without special handling
     * for Map can make Map an alias for List. The "layout" attribute for the Map
     * field must have the same contents as a List.
     */
    Map: 17,
    /**
     * An absolute length of time unrelated to any calendar artifacts. For the
     * purposes of Arrow implementations, adding this value to a Timestamp
     * ("t1") naively (i.e. simply summing the two numbers) is acceptable even
     * though in some cases the resulting Timestamp (t2) would not account for
     * leap-seconds during the elapsed time between "t1" and "t2". Similarly,
     * representing the difference between two Unix timestamp is acceptable, but
     * would yield a value that is possibly a few seconds off from the true
     * elapsed time.
     *
     * The resolution defaults to millisecond, but can be any of the other
     * supported TimeUnit values as with Timestamp and Time types. This type is
     * always represented as an 8-byte integer.
     */
    Duration: 18,
    /**
     * Same as Binary, but with 64-bit offsets, allowing representation of
     * extremely large data values.
     */
    LargeBinary: 19,
    /**
     * Same as Utf8, but with 64-bit offsets, allowing representation of
     * extremely large data values.
     */
    LargeUtf8: 20,
    /**
     * Same as List, but with 64-bit offsets, allowing representation of
     * extremely large data values.
     */
    LargeList: 21,
    /**
     * Contains two child arrays, run_ends and values. The run_ends child array
     * must be a 16/32/64-bit integer array which encodes the indices at which
     * the run with the value in each corresponding index in the values child
     * array ends. Like list/struct types, the value array can be of any type.
     */
    RunEndEncoded: 22,
    /**
     * Logically the same as Binary, but the internal representation uses a view
     * struct that contains the string length and either the string's entire data
     * inline (for small strings) or an inlined prefix, an index of another buffer,
     * and an offset pointing to a slice in that buffer (for non-small strings).
     *
     * Since it uses a variable number of data buffers, each Field with this type
     * must have a corresponding entry in `variadicBufferCounts`.
     */
    BinaryView: 23,
    /**
     * Logically the same as Utf8, but the internal representation uses a view
     * struct that contains the string length and either the string's entire data
     * inline (for small strings) or an inlined prefix, an index of another buffer,
     * and an offset pointing to a slice in that buffer (for non-small strings).
     *
     * Since it uses a variable number of data buffers, each Field with this type
     * must have a corresponding entry in `variadicBufferCounts`.
     */
    Utf8View: 24,
    /**
     * Represents the same logical types that List can, but contains offsets and
     * sizes allowing for writes in any order and sharing of child values among
     * list values.
     */
    ListView: 25,
    /**
     * Same as ListView, but with 64-bit offsets and sizes, allowing to represent
     * extremely large data values.
     */
    LargeListView: 26
  }
);
const Precision = (
  /** @type {const} */
  {
    /** 16-bit floating point number. */
    HALF: 0,
    /** 32-bit floating point number. */
    SINGLE: 1,
    /** 64-bit floating point number. */
    DOUBLE: 2
  }
);
const DateUnit = (
  /** @type {const} */
  {
    /* Days (as 32 bit int) since the UNIX epoch. */
    DAY: 0,
    /**
     * Milliseconds (as 64 bit int) indicating UNIX time elapsed since the epoch
     * (no leap seconds), with values evenly divisible by 86400000.
     */
    MILLISECOND: 1
  }
);
const TimeUnit = (
  /** @type {const} */
  {
    /** Seconds. */
    SECOND: 0,
    /** Milliseconds. */
    MILLISECOND: 1,
    /** Microseconds. */
    MICROSECOND: 2,
    /** Nanoseconds. */
    NANOSECOND: 3
  }
);
const IntervalUnit = (
  /** @type {const} */
  {
    /**
     * Indicates the number of elapsed whole months, stored as 4-byte signed
     * integers.
     */
    YEAR_MONTH: 0,
    /**
     * Indicates the number of elapsed days and milliseconds (no leap seconds),
     * stored as 2 contiguous 32-bit signed integers (8-bytes in total). Support
     * of this IntervalUnit is not required for full arrow compatibility.
     */
    DAY_TIME: 1,
    /**
     * A triple of the number of elapsed months, days, and nanoseconds.
     * The values are stored contiguously in 16-byte blocks. Months and days are
     * encoded as 32-bit signed integers and nanoseconds is encoded as a 64-bit
     * signed integer. Nanoseconds does not allow for leap seconds. Each field is
     * independent (e.g. there is no constraint that nanoseconds have the same
     * sign as days or that the quantity of nanoseconds represents less than a
     * day's worth of time).
     */
    MONTH_DAY_NANO: 2
  }
);
const UnionMode = (
  /** @type {const} */
  {
    /** Sparse union layout with full arrays for each sub-type. */
    Sparse: 0,
    /** Dense union layout with offsets into value arrays. */
    Dense: 1
  }
);
const uint8Array = Uint8Array;
const uint16Array = Uint16Array;
const uint32Array = Uint32Array;
const uint64Array = BigUint64Array;
const int8Array = Int8Array;
const int16Array = Int16Array;
const int32Array = Int32Array;
const int64Array = BigInt64Array;
const float32Array = Float32Array;
const float64Array = Float64Array;
function isArrayBufferLike(data2) {
  return data2 instanceof ArrayBuffer || typeof SharedArrayBuffer !== "undefined" && data2 instanceof SharedArrayBuffer;
}
function intArrayType(bitWidth, signed) {
  const i = Math.log2(bitWidth) - 3;
  return (signed ? [int8Array, int16Array, int32Array, int64Array] : [uint8Array, uint16Array, uint32Array, uint64Array])[i];
}
const TypedArray = Object.getPrototypeOf(Int8Array);
function isTypedArray(value2) {
  return value2 instanceof TypedArray;
}
function isArray(value2) {
  return Array.isArray(value2) || isTypedArray(value2);
}
function isInt64ArrayType(value2) {
  return value2 === int64Array || value2 === uint64Array;
}
function bisect(offsets, index) {
  let a = 0;
  let b = offsets.length;
  if (b <= 2147483648) {
    do {
      const mid = a + b >>> 1;
      if (offsets[mid] <= index) a = mid + 1;
      else b = mid;
    } while (a < b);
  } else {
    do {
      const mid = Math.trunc((a + b) / 2);
      if (offsets[mid] <= index) a = mid + 1;
      else b = mid;
    } while (a < b);
  }
  return a;
}
function align64(length2, bpe = 1) {
  return (length2 * bpe + 7 & -8) / bpe;
}
function align(array2, length2 = array2.length) {
  const alignedLength = align64(length2, array2.BYTES_PER_ELEMENT);
  return array2.length > alignedLength ? (
    /** @type {T} */
    array2.subarray(0, alignedLength)
  ) : array2.length < alignedLength ? resize(array2, alignedLength) : array2;
}
function resize(array2, newLength, offset2 = 0) {
  const newArray = new array2.constructor(newLength);
  newArray.set(array2, offset2);
  return newArray;
}
function grow(array2, index, shift) {
  while (array2.length <= index) {
    array2 = resize(array2, array2.length << 1, shift ? array2.length : 0);
  }
  return array2;
}
function isDate(value2) {
  return value2 instanceof Date;
}
function isIterable(value2) {
  return typeof value2[Symbol.iterator] === "function";
}
function check(value2, test, message) {
  if (test(value2)) return value2;
  throw new Error(message(value2));
}
function checkOneOf(value2, set, message) {
  set = Array.isArray(set) ? set : Object.values(set);
  return check(
    value2,
    (value3) => set.includes(value3),
    message ?? (() => `${value2} must be one of ${set}`)
  );
}
function keyFor(object2, value2) {
  for (const [key2, val] of Object.entries(object2)) {
    if (val === value2) return key2;
  }
  return "<Unknown>";
}
const invalidDataType = (typeId) => `Unsupported data type: "${keyFor(Type, typeId)}" (id ${typeId})`;
const field = (name2, type, nullable = true, metadata = null) => ({
  name: name2,
  type,
  nullable,
  metadata
});
function isField(value2) {
  return Object.hasOwn(value2, "name") && isDataType(value2.type);
}
function isDataType(value2) {
  return typeof value2?.typeId === "number";
}
function asField(value2, defaultName = "", defaultNullable = true) {
  return isField(value2) ? value2 : field(
    defaultName,
    check(value2, isDataType, () => `Data type expected.`),
    defaultNullable
  );
}
const basicType = (typeId) => ({ typeId });
const dictionary$1 = (type, indexType, ordered = false, id = -1) => ({
  typeId: Type.Dictionary,
  id,
  dictionary: type,
  indices: indexType || int32(),
  ordered
});
const nullType = () => basicType(Type.Null);
const int = (bitWidth = 32, signed = true) => ({
  typeId: Type.Int,
  bitWidth: checkOneOf(bitWidth, [8, 16, 32, 64]),
  signed,
  values: intArrayType(bitWidth, signed)
});
const int8 = () => int(8);
const int16 = () => int(16);
const int32 = () => int(32);
const int64 = () => int(64);
const uint8 = () => int(8, false);
const uint16 = () => int(16, false);
const uint32 = () => int(32, false);
const uint64 = () => int(64, false);
const float = (precision = 2) => ({
  typeId: Type.Float,
  precision: checkOneOf(precision, Precision),
  values: [uint16Array, float32Array, float64Array][precision]
});
const float32 = () => float(Precision.SINGLE);
const float64 = () => float(Precision.DOUBLE);
const binary = () => ({
  typeId: Type.Binary,
  offsets: int32Array
});
const utf8 = () => ({
  typeId: Type.Utf8,
  offsets: int32Array
});
const bool = () => basicType(Type.Bool);
const decimal = (precision, scale, bitWidth = 128) => ({
  typeId: Type.Decimal,
  precision,
  scale,
  bitWidth: checkOneOf(bitWidth, [32, 64, 128, 256]),
  values: bitWidth === 32 ? int32Array : uint64Array
});
const date = (unit) => ({
  typeId: Type.Date,
  unit: checkOneOf(unit, DateUnit),
  values: unit === DateUnit.DAY ? int32Array : int64Array
});
const dateDay = () => date(DateUnit.DAY);
const time = (unit = TimeUnit.MILLISECOND) => {
  unit = checkOneOf(unit, TimeUnit);
  const bitWidth = unit === TimeUnit.SECOND || unit === TimeUnit.MILLISECOND ? 32 : 64;
  return {
    typeId: Type.Time,
    unit,
    bitWidth,
    values: bitWidth === 32 ? int32Array : int64Array
  };
};
const timestamp = (unit = TimeUnit.MILLISECOND, timezone = null) => ({
  typeId: Type.Timestamp,
  unit: checkOneOf(unit, TimeUnit),
  timezone,
  values: int64Array
});
const interval = (unit = IntervalUnit.MONTH_DAY_NANO) => ({
  typeId: Type.Interval,
  unit: checkOneOf(unit, IntervalUnit),
  values: unit === IntervalUnit.MONTH_DAY_NANO ? void 0 : int32Array
});
const list = (child) => ({
  typeId: Type.List,
  children: [asField(child)],
  offsets: int32Array
});
const struct = (children) => ({
  typeId: Type.Struct,
  children: Array.isArray(children) && isField(children[0]) ? (
    /** @type {Field[]} */
    children
  ) : Object.entries(children).map(([name2, type]) => field(name2, type))
});
const union = (mode, children, typeIds, typeIdForValue) => {
  typeIds ??= children.map((v, i) => i);
  return {
    typeId: Type.Union,
    mode: checkOneOf(mode, UnionMode),
    typeIds,
    typeMap: typeIds.reduce((m, id, i) => (m[id] = i, m), {}),
    children: children.map((v, i) => asField(v, `_${i}`)),
    typeIdForValue,
    offsets: int32Array
  };
};
const fixedSizeBinary = (stride) => ({
  typeId: Type.FixedSizeBinary,
  stride
});
const fixedSizeList = (child, stride) => ({
  typeId: Type.FixedSizeList,
  stride,
  children: [asField(child)]
});
const mapType = (keysSorted, child) => ({
  typeId: Type.Map,
  keysSorted,
  children: [child],
  offsets: int32Array
});
const duration = (unit = TimeUnit.MILLISECOND) => ({
  typeId: Type.Duration,
  unit: checkOneOf(unit, TimeUnit),
  values: int64Array
});
const largeBinary = () => ({
  typeId: Type.LargeBinary,
  offsets: int64Array
});
const largeUtf8 = () => ({
  typeId: Type.LargeUtf8,
  offsets: int64Array
});
const largeList = (child) => ({
  typeId: Type.LargeList,
  children: [asField(child)],
  offsets: int64Array
});
const runEndEncoded = (runsField, valuesField) => ({
  typeId: Type.RunEndEncoded,
  children: [
    check(
      asField(runsField, "run_ends"),
      (field2) => field2.type.typeId === Type.Int,
      () => "Run-ends must have an integer type."
    ),
    asField(valuesField, "values")
  ]
});
const listView = (child) => ({
  typeId: Type.ListView,
  children: [asField(child, "value")],
  offsets: int32Array
});
const largeListView = (child) => ({
  typeId: Type.LargeListView,
  children: [asField(child, "value")],
  offsets: int64Array
});
const f64 = new float64Array(2);
const buf = f64.buffer;
const i64 = new int64Array(buf);
const u32 = new uint32Array(buf);
const i32 = new int32Array(buf);
const u8 = new uint8Array(buf);
function identity$1(value2) {
  return value2;
}
function toBigInt(value2) {
  return BigInt(value2);
}
function toOffset(type) {
  return isInt64ArrayType(type) ? toBigInt : identity$1;
}
function toDateDay(value2) {
  return value2 / 864e5 | 0;
}
function toTimestamp(unit) {
  return unit === TimeUnit.SECOND ? (value2) => toBigInt(value2 / 1e3) : unit === TimeUnit.MILLISECOND ? toBigInt : unit === TimeUnit.MICROSECOND ? (value2) => toBigInt(value2 * 1e3) : (value2) => toBigInt(value2 * 1e6);
}
function toMonthDayNanoBytes([m, d, n]) {
  i32[0] = m;
  i32[1] = d;
  i64[1] = toBigInt(n);
  return u8;
}
function toNumber(value2) {
  if (value2 > Number.MAX_SAFE_INTEGER || value2 < Number.MIN_SAFE_INTEGER) {
    throw Error(`BigInt exceeds integer number representation: ${value2}`);
  }
  return Number(value2);
}
function divide(num, div) {
  return Number(num / div) + Number(num % div) / Number(div);
}
function toDecimal32(scale) {
  return (value2) => typeof value2 === "bigint" ? Number(value2) : Math.trunc(value2 * scale);
}
function toDecimal(value2, buf2, offset2, stride, scale) {
  const v = typeof value2 === "bigint" ? value2 : toBigInt(Math.trunc(value2 * scale));
  buf2[offset2] = v;
  if (stride > 1) {
    buf2[offset2 + 1] = v >> 64n;
    if (stride > 2) {
      buf2[offset2 + 2] = v >> 128n;
      buf2[offset2 + 3] = v >> 192n;
    }
  }
}
const asUint64 = (v) => BigInt.asUintN(64, v);
function fromDecimal64(buf2, offset2) {
  return BigInt.asIntN(64, buf2[offset2]);
}
function fromDecimal128(buf2, offset2) {
  const i = offset2 << 1;
  let x;
  if (BigInt.asIntN(64, buf2[i + 1]) < 0) {
    x = asUint64(~buf2[i]) | asUint64(~buf2[i + 1]) << 64n;
    x = -(x + 1n);
  } else {
    x = buf2[i] | buf2[i + 1] << 64n;
  }
  return x;
}
function fromDecimal256(buf2, offset2) {
  const i = offset2 << 2;
  let x;
  if (BigInt.asIntN(64, buf2[i + 3]) < 0) {
    x = asUint64(~buf2[i]) | asUint64(~buf2[i + 1]) << 64n | asUint64(~buf2[i + 2]) << 128n | asUint64(~buf2[i + 3]) << 192n;
    x = -(x + 1n);
  } else {
    x = buf2[i] | buf2[i + 1] << 64n | buf2[i + 2] << 128n | buf2[i + 3] << 192n;
  }
  return x;
}
function toFloat16(value2) {
  if (value2 !== value2) return 32256;
  f64[0] = value2;
  const sign2 = (u32[1] & 2147483648) >> 16 & 65535;
  let expo = u32[1] & 2146435072, sigf = 0;
  if (expo >= 1089470464) {
    if (u32[0] > 0) {
      expo = 31744;
    } else {
      expo = (expo & 2080374784) >> 16;
      sigf = (u32[1] & 1048575) >> 10;
    }
  } else if (expo <= 1056964608) {
    sigf = 1048576 + (u32[1] & 1048575);
    sigf = 1048576 + (sigf << (expo >> 20) - 998) >> 21;
    expo = 0;
  } else {
    expo = expo - 1056964608 >> 10;
    sigf = (u32[1] & 1048575) + 512 >> 10;
  }
  return sign2 | expo | sigf & 65535;
}
const textDecoder = new TextDecoder("utf-8");
const textEncoder = new TextEncoder();
function decodeUtf8(buf2) {
  return textDecoder.decode(buf2);
}
function encodeUtf8(str) {
  return textEncoder.encode(str);
}
function keyString(value2) {
  const val = typeof value2 !== "object" || !value2 ? value2 ?? null : isDate(value2) ? +value2 : isArray(value2) ? `[${value2.map(keyString)}]` : objectKey(value2);
  return `${val}`;
}
function objectKey(value2) {
  let s = "";
  let i = -1;
  for (const k in value2) {
    if (++i > 0) s += ",";
    s += `"${k}":${keyString(value2[k])}`;
  }
  return `{${s}}`;
}
const SIZEOF_INT = 4;
const SIZEOF_SHORT = 2;
function decodeBit(bitmap2, index) {
  return (bitmap2[index >> 3] & 1 << index % 8) !== 0;
}
function readObject(buf2, index) {
  const pos = index + readInt32(buf2, index);
  const vtable = pos - readInt32(buf2, pos);
  const size = readInt16(buf2, vtable);
  return (index2, read, fallback = null) => {
    if (index2 < size) {
      const off = readInt16(buf2, vtable + index2);
      if (off) return read(buf2, pos + off);
    }
    return fallback;
  };
}
function readOffset(buf2, offset2) {
  return offset2;
}
function readBoolean(buf2, offset2) {
  return !!readInt8(buf2, offset2);
}
function readInt8(buf2, offset2) {
  return readUint8(buf2, offset2) << 24 >> 24;
}
function readUint8(buf2, offset2) {
  return buf2[offset2];
}
function readInt16(buf2, offset2) {
  return readUint16(buf2, offset2) << 16 >> 16;
}
function readUint16(buf2, offset2) {
  return buf2[offset2] | buf2[offset2 + 1] << 8;
}
function readInt32(buf2, offset2) {
  return buf2[offset2] | buf2[offset2 + 1] << 8 | buf2[offset2 + 2] << 16 | buf2[offset2 + 3] << 24;
}
function readUint32(buf2, offset2) {
  return readInt32(buf2, offset2) >>> 0;
}
function readInt64(buf2, offset2) {
  return toNumber(BigInt.asIntN(
    64,
    BigInt(readUint32(buf2, offset2)) + (BigInt(readUint32(buf2, offset2 + SIZEOF_INT)) << 32n)
  ));
}
function readString(buf2, index) {
  let offset2 = index + readInt32(buf2, index);
  const length2 = readInt32(buf2, offset2);
  offset2 += SIZEOF_INT;
  return decodeUtf8(buf2.subarray(offset2, offset2 + length2));
}
function readVector(buf2, offset2, stride, extract) {
  if (!offset2) return [];
  const base = offset2 + readInt32(buf2, offset2);
  return Array.from(
    { length: readInt32(buf2, base) },
    (_, i) => extract(buf2, base + SIZEOF_INT + i * stride)
  );
}
const RowIndex = /* @__PURE__ */ Symbol("rowIndex");
function proxyFactory(names, batches) {
  class RowObject {
    /**
     * Create a new proxy row object representing a struct or table row.
     * @param {number} index The record batch row index.
     */
    constructor(index) {
      this[RowIndex] = index;
    }
    /**
     * Return a JSON-compatible object representation.
     */
    toJSON() {
      return structObject(names, batches, this[RowIndex]);
    }
  }
  const proto = RowObject.prototype;
  for (let i = 0; i < names.length; ++i) {
    if (Object.hasOwn(proto, names[i])) continue;
    const batch = batches[i];
    Object.defineProperty(proto, names[i], {
      get() {
        return batch.at(this[RowIndex]);
      },
      enumerable: true
    });
  }
  return (index) => new RowObject(index);
}
function objectFactory(names, batches) {
  return (index) => structObject(names, batches, index);
}
function structObject(names, batches, index) {
  const obj = {};
  for (let i = 0; i < names.length; ++i) {
    obj[names[i]] = batches[i].at(index);
  }
  return obj;
}
function isDirectBatch(batch) {
  return batch instanceof DirectBatch;
}
class Batch {
  /**
   * The array type to use when extracting data from the batch.
   * A null value indicates that the array type should match
   * the type of the batch's values array.
   * @type {ArrayConstructor | TypedArrayConstructor | null}
   */
  static ArrayType = null;
  /**
   * Create a new column batch.
   * @param {object} options
   * @param {number} options.length The length of the batch
   * @param {number} options.nullCount The null value count
   * @param {DataType} options.type The data type.
   * @param {Uint8Array} [options.validity] Validity bitmap buffer
   * @param {TypedArray} [options.values] Values buffer
   * @param {OffsetArray} [options.offsets] Offsets buffer
   * @param {OffsetArray} [options.sizes] Sizes buffer
   * @param {Batch[]} [options.children] Children batches
   */
  constructor({
    length: length2,
    nullCount,
    type,
    validity,
    values: values2,
    offsets,
    sizes,
    children
  }) {
    this.length = length2;
    this.nullCount = nullCount;
    this.type = type;
    this.validity = validity;
    this.values = values2;
    this.offsets = offsets;
    this.sizes = sizes;
    this.children = children;
    if (!nullCount || !this.validity) {
      this.at = (index) => this.value(index);
    }
  }
  /**
   * Provide an informative object string tag.
   */
  get [Symbol.toStringTag]() {
    return "Batch";
  }
  /**
   * Return the value at the given index.
   * @param {number} index The value index.
   * @returns {T | null} The value.
   */
  at(index) {
    return this.isValid(index) ? this.value(index) : null;
  }
  /**
   * Check if a value at the given index is valid (non-null).
   * @param {number} index The value index.
   * @returns {boolean} True if valid, false otherwise.
   */
  isValid(index) {
    return decodeBit(this.validity, index);
  }
  /**
   * Return the value at the given index. This method does not check the
   * validity bitmap and is intended primarily for internal use. In most
   * cases, callers should use the `at()` method instead.
   * @param {number} index The value index
   * @returns {T} The value, ignoring the validity bitmap.
   */
  value(index) {
    return (
      /** @type {T} */
      this.values[index]
    );
  }
  /**
   * Extract an array of values within the given index range. Unlike
   * Array.slice, all arguments are required and may not be negative indices.
   * @param {number} start The starting index, inclusive
   * @param {number} end The ending index, exclusive
   * @returns {ValueArray<T?>} The slice of values
   */
  slice(start, end) {
    const n = end - start;
    const values2 = Array(n);
    for (let i = 0; i < n; ++i) {
      values2[i] = this.at(start + i);
    }
    return values2;
  }
  /**
   * Return an iterator over the values in this batch.
   * @returns {Iterator<T?>}
   */
  *[Symbol.iterator]() {
    for (let i = 0; i < this.length; ++i) {
      yield this.at(i);
    }
  }
}
class DirectBatch extends Batch {
  /**
   * Create a new column batch with direct value array access.
   * @param {object} options
   * @param {number} options.length The length of the batch
   * @param {number} options.nullCount The null value count
   * @param {DataType} options.type The data type.
   * @param {Uint8Array} [options.validity] Validity bitmap buffer
   * @param {TypedArray} options.values Values buffer
   */
  constructor(options) {
    super(options);
    const { length: length2, values: values2 } = this;
    this.values = values2.subarray(0, length2);
  }
  /**
   * Extract an array of values within the given index range. Unlike
   * Array.slice, all arguments are required and may not be negative indices.
   * When feasible, a zero-copy subarray of a typed array is returned.
   * @param {number} start The starting index, inclusive
   * @param {number} end The ending index, exclusive
   * @returns {ValueArray<T?>} The slice of values
   */
  slice(start, end) {
    return this.nullCount ? super.slice(start, end) : this.values.subarray(start, end);
  }
  /**
   * Return an iterator over the values in this batch.
   * @returns {Iterator<T?>}
   */
  [Symbol.iterator]() {
    return this.nullCount ? super[Symbol.iterator]() : (
      /** @type {Iterator<T?>} */
      this.values[Symbol.iterator]()
    );
  }
}
class NumberBatch extends Batch {
  static ArrayType = float64Array;
}
class ArrayBatch extends Batch {
  static ArrayType = Array;
}
class NullBatch extends ArrayBatch {
  /**
   * @param {number} index The value index
   * @returns {null}
   */
  value(index) {
    return null;
  }
}
class Int64Batch extends NumberBatch {
  /**
   * @param {number} index The value index
   */
  value(index) {
    return toNumber(
      /** @type {bigint} */
      this.values[index]
    );
  }
}
class Float16Batch extends NumberBatch {
  /**
   * @param {number} index The value index
   */
  value(index) {
    const v = (
      /** @type {number} */
      this.values[index]
    );
    const expo = (v & 31744) >> 10;
    const sigf = (v & 1023) / 1024;
    const sign2 = (-1) ** ((v & 32768) >> 15);
    switch (expo) {
      case 31:
        return sign2 * (sigf ? Number.NaN : 1 / 0);
      case 0:
        return sign2 * (sigf ? 6103515625e-14 * sigf : 0);
    }
    return sign2 * 2 ** (expo - 15) * (1 + sigf);
  }
}
class BoolBatch extends ArrayBatch {
  /**
   * @param {number} index The value index
   */
  value(index) {
    return decodeBit(
      /** @type {Uint8Array} */
      this.values,
      index
    );
  }
}
class Decimal32NumberBatch extends NumberBatch {
  constructor(options) {
    super(options);
    const { scale } = (
      /** @type {DecimalType} */
      this.type
    );
    this.scale = 10 ** scale;
  }
  /**
   * @param {number} index The value index
   */
  value(index) {
    return (
      /** @type {number} */
      this.values[index] / this.scale
    );
  }
}
class DecimalBatch extends Batch {
  constructor(options) {
    super(options);
    const { bitWidth, scale } = (
      /** @type {DecimalType} */
      this.type
    );
    this.decimal = bitWidth === 64 ? fromDecimal64 : bitWidth === 128 ? fromDecimal128 : fromDecimal256;
    this.scale = 10n ** BigInt(scale);
  }
}
class DecimalNumberBatch extends DecimalBatch {
  static ArrayType = float64Array;
  /**
   * @param {number} index The value index
   */
  value(index) {
    return divide(
      this.decimal(
        /** @type {BigUint64Array} */
        this.values,
        index
      ),
      this.scale
    );
  }
}
class DecimalBigIntBatch extends DecimalBatch {
  static ArrayType = Array;
  /**
   * @param {number} index The value index
   */
  value(index) {
    return this.decimal(
      /** @type {BigUint64Array} */
      this.values,
      index
    );
  }
}
class DateBatch extends ArrayBatch {
  /**
   * Create a new date batch.
   * @param {Batch<number>} batch A batch of timestamp values.
   */
  constructor(batch) {
    super(batch);
    this.source = batch;
  }
  /**
   * @param {number} index The value index
   */
  value(index) {
    return new Date(this.source.value(index));
  }
}
class DateDayBatch extends NumberBatch {
  /**
   * @param {number} index The value index
   * @returns {number}
   */
  value(index) {
    return 864e5 * /** @type {number} */
    this.values[index];
  }
}
const DateDayMillisecondBatch = Int64Batch;
class TimestampSecondBatch extends Int64Batch {
  /**
   * @param {number} index The value index
   */
  value(index) {
    return super.value(index) * 1e3;
  }
}
const TimestampMillisecondBatch = Int64Batch;
class TimestampMicrosecondBatch extends Int64Batch {
  /**
   * @param {number} index The value index
   */
  value(index) {
    return divide(
      /** @type {bigint} */
      this.values[index],
      1000n
    );
  }
}
class TimestampNanosecondBatch extends Int64Batch {
  /**
   * @param {number} index The value index
   */
  value(index) {
    return divide(
      /** @type {bigint} */
      this.values[index],
      1000000n
    );
  }
}
class IntervalDayTimeBatch extends ArrayBatch {
  /**
   * @param {number} index The value index
   * @returns {Int32Array}
   */
  value(index) {
    const values2 = (
      /** @type {Int32Array} */
      this.values
    );
    return values2.subarray(index << 1, index + 1 << 1);
  }
}
class IntervalMonthDayNanoBatch extends ArrayBatch {
  /**
   * @param {number} index The value index
   */
  value(index) {
    const values2 = (
      /** @type {Uint8Array} */
      this.values
    );
    const base = index << 4;
    return Float64Array.of(
      readInt32(values2, base),
      readInt32(values2, base + 4),
      readInt64(values2, base + 8)
    );
  }
}
const offset32 = ({ values: values2, offsets }, index) => values2.subarray(offsets[index], offsets[index + 1]);
const offset64 = ({ values: values2, offsets }, index) => values2.subarray(toNumber(offsets[index]), toNumber(offsets[index + 1]));
class BinaryBatch extends ArrayBatch {
  /**
   * @param {number} index
   * @returns {Uint8Array}
   */
  value(index) {
    return offset32(this, index);
  }
}
class LargeBinaryBatch extends ArrayBatch {
  /**
   * @param {number} index
   * @returns {Uint8Array}
   */
  value(index) {
    return offset64(this, index);
  }
}
class Utf8Batch extends ArrayBatch {
  /**
   * @param {number} index
   */
  value(index) {
    return decodeUtf8(offset32(this, index));
  }
}
class LargeUtf8Batch extends ArrayBatch {
  /**
   * @param {number} index
   */
  value(index) {
    return decodeUtf8(offset64(this, index));
  }
}
class ListBatch extends ArrayBatch {
  /**
   * @param {number} index
   * @returns {ValueArray<V>}
   */
  value(index) {
    const offsets = (
      /** @type {Int32Array} */
      this.offsets
    );
    return this.children[0].slice(offsets[index], offsets[index + 1]);
  }
}
class LargeListBatch extends ArrayBatch {
  /**
   * @param {number} index
   * @returns {ValueArray<V>}
   */
  value(index) {
    const offsets = (
      /** @type {BigInt64Array} */
      this.offsets
    );
    return this.children[0].slice(toNumber(offsets[index]), toNumber(offsets[index + 1]));
  }
}
class ListViewBatch extends ArrayBatch {
  /**
   * @param {number} index
   * @returns {ValueArray<V>}
   */
  value(index) {
    const a = (
      /** @type {number} */
      this.offsets[index]
    );
    const b = a + /** @type {number} */
    this.sizes[index];
    return this.children[0].slice(a, b);
  }
}
class LargeListViewBatch extends ArrayBatch {
  /**
   * @param {number} index
   * @returns {ValueArray<V>}
   */
  value(index) {
    const a = (
      /** @type {bigint} */
      this.offsets[index]
    );
    const b = a + /** @type {bigint} */
    this.sizes[index];
    return this.children[0].slice(toNumber(a), toNumber(b));
  }
}
class FixedBatch extends ArrayBatch {
  constructor(options) {
    super(options);
    this.stride = this.type.stride;
  }
}
class FixedBinaryBatch extends FixedBatch {
  /**
   * @param {number} index
   * @returns {Uint8Array}
   */
  value(index) {
    const { stride, values: values2 } = this;
    return (
      /** @type {Uint8Array} */
      values2.subarray(index * stride, (index + 1) * stride)
    );
  }
}
class FixedListBatch extends FixedBatch {
  /**
   * @param {number} index
   * @returns {ValueArray<V>}
   */
  value(index) {
    const { children, stride } = this;
    return children[0].slice(index * stride, (index + 1) * stride);
  }
}
function pairs({ children, offsets }, index) {
  const [keys2, vals] = children[0].children;
  const start = offsets[index];
  const end = offsets[index + 1];
  const entries2 = [];
  for (let i = start; i < end; ++i) {
    entries2.push([keys2.at(i), vals.at(i)]);
  }
  return entries2;
}
class MapEntryBatch extends ArrayBatch {
  /**
   * Return the value at the given index.
   * @param {number} index The value index.
   * @returns {[K, V][]} The map entries as an array of [key, value] arrays.
   */
  value(index) {
    return (
      /** @type {[K, V][]} */
      pairs(this, index)
    );
  }
}
class MapBatch extends ArrayBatch {
  /**
   * Return the value at the given index.
   * @param {number} index The value index.
   * @returns {Map<K, V>} The map value.
   */
  value(index) {
    return new Map(
      /** @type {[K, V][]} */
      pairs(this, index)
    );
  }
}
class SparseUnionBatch extends ArrayBatch {
  /**
   * Create a new column batch.
   * @param {object} options
   * @param {number} options.length The length of the batch
   * @param {number} options.nullCount The null value count
   * @param {DataType} options.type The data type.
   * @param {Uint8Array} [options.validity] Validity bitmap buffer
   * @param {Int32Array} [options.offsets] Offsets buffer
   * @param {Batch[]} options.children Children batches
   * @param {Int8Array} options.typeIds Union type ids buffer
   * @param {Record<string, number>} options.map A typeId to children index map
   */
  constructor({ typeIds, ...options }) {
    super(options);
    this.typeIds = typeIds;
    this.typeMap = this.type.typeMap;
  }
  /**
   * @param {number} index The value index.
   */
  value(index, offset2 = index) {
    const { typeIds, children, typeMap } = this;
    return children[typeMap[typeIds[index]]].at(offset2);
  }
}
class DenseUnionBatch extends SparseUnionBatch {
  /**
   * @param {number} index The value index.
   */
  value(index) {
    return super.value(
      index,
      /** @type {number} */
      this.offsets[index]
    );
  }
}
class StructBatch extends ArrayBatch {
  constructor(options, factory = objectFactory) {
    super(options);
    this.names = this.type.children.map((child) => child.name);
    this.factory = factory(this.names, this.children);
  }
  /**
   * @param {number} index The value index.
   * @returns {Record<string, any>}
   */
  value(index) {
    return this.factory(index);
  }
}
class StructProxyBatch extends StructBatch {
  constructor(options) {
    super(options, proxyFactory);
  }
}
class RunEndEncodedBatch extends ArrayBatch {
  /**
   * @param {number} index The value index.
   */
  value(index) {
    const [{ values: runs }, vals] = this.children;
    return vals.at(
      bisect(
        /** @type {IntegerArray} */
        runs,
        index
      )
    );
  }
}
class DictionaryBatch3 extends ArrayBatch {
  /**
   * Register the backing dictionary. Dictionaries are added
   * after batch creation as the complete dictionary may not
   * be finished across multiple record batches.
   * @param {Column<T>} dictionary
   * The dictionary of column values.
   */
  setDictionary(dictionary2) {
    this.dictionary = dictionary2;
    this.cache = dictionary2.cache();
    return this;
  }
  /**
   * @param {number} index The value index.
   */
  value(index) {
    return this.cache[this.key(index)];
  }
  /**
   * @param {number} index The value index.
   * @returns {number} The dictionary key
   */
  key(index) {
    return (
      /** @type {number} */
      this.values[index]
    );
  }
}
class ViewBatch extends ArrayBatch {
  /**
   * Create a new view batch.
   * @param {object} options Batch options.
   * @param {number} options.length The length of the batch
   * @param {number} options.nullCount The null value count
   * @param {DataType} options.type The data type.
   * @param {Uint8Array} [options.validity] Validity bitmap buffer
   * @param {Uint8Array} options.values Values buffer
   * @param {Uint8Array[]} options.data View data buffers
   */
  constructor({ data: data2, ...options }) {
    super(options);
    this.data = data2;
  }
  /**
   * Get the binary data at the provided index.
   * @param {number} index The value index.
   * @returns {Uint8Array}
   */
  view(index) {
    const { values: values2, data: data2 } = this;
    const offset2 = index << 4;
    let start = offset2 + 4;
    let buf2 = (
      /** @type {Uint8Array} */
      values2
    );
    const length2 = readInt32(buf2, offset2);
    if (length2 > 12) {
      start = readInt32(buf2, offset2 + 12);
      buf2 = data2[readInt32(buf2, offset2 + 8)];
    }
    return buf2.subarray(start, start + length2);
  }
}
class BinaryViewBatch extends ViewBatch {
  /**
   * @param {number} index The value index.
   */
  value(index) {
    return this.view(index);
  }
}
class Utf8ViewBatch extends ViewBatch {
  /**
   * @param {number} index The value index.
   */
  value(index) {
    return decodeUtf8(this.view(index));
  }
}
function columnBuilder(type) {
  let data2 = [];
  return {
    add(batch) {
      data2.push(batch);
      return this;
    },
    clear: () => data2 = [],
    done: () => new Column(data2, type)
  };
}
class Column {
  /**
   * Create a new column instance.
   * @param {Batch<T>[]} data The value batches.
   * @param {DataType} [type] The column data type.
   *  If not specified, the type is extracted from the batches.
   */
  constructor(data2, type = data2[0]?.type) {
    this.type = type;
    this.length = data2.reduce((m, c) => m + c.length, 0);
    this.nullCount = data2.reduce((m, c) => m + c.nullCount, 0);
    this.data = data2;
    const n = data2.length;
    const offsets = new Int32Array(n + 1);
    if (n === 1) {
      const [batch] = data2;
      offsets[1] = batch.length;
      this.at = (index) => batch.at(index);
    } else {
      for (let i = 0, s = 0; i < n; ++i) {
        offsets[i + 1] = s += data2[i].length;
      }
    }
    this.offsets = offsets;
  }
  /**
   * Provide an informative object string tag.
   */
  get [Symbol.toStringTag]() {
    return "Column";
  }
  /**
   * Return an iterator over the values in this column.
   * @returns {Iterator<T?>}
   */
  [Symbol.iterator]() {
    const data2 = this.data;
    return data2.length === 1 ? data2[0][Symbol.iterator]() : batchedIterator(data2);
  }
  /**
   * Return the column value at the given index. If a column has multiple
   * batches, this method performs binary search over the batch lengths to
   * determine the batch from which to retrieve the value. The search makes
   * lookup less efficient than a standard array access. If making a full
   * scan of a column, consider extracting arrays via `toArray()` or using an
   * iterator (`for (const value of column) {...}`).
   * @param {number} index The row index.
   * @returns {T | null} The value.
   */
  at(index) {
    const { data: data2, offsets } = this;
    const i = bisect(offsets, index) - 1;
    return data2[i]?.at(index - offsets[i]);
  }
  /**
   * Return the column value at the given index. This method is the same as
   * `at()` and is provided for better compatibility with Apache Arrow JS.
   * @param {number} index The row index.
   * @returns {T | null} The value.
   */
  get(index) {
    return this.at(index);
  }
  /**
   * Extract column values into a single array instance. When possible,
   * a zero-copy subarray of the input Arrow data is returned.
   * @returns {ValueArray<T?>}
   */
  toArray() {
    const { length: length2, nullCount, data: data2 } = this;
    const copy = !nullCount && isDirectBatch(data2[0]);
    const n = data2.length;
    if (copy && n === 1) {
      return data2[0].values;
    }
    const ArrayType = !n || nullCount > 0 ? Array : data2[0].constructor.ArrayType ?? data2[0].values.constructor;
    const array2 = new ArrayType(length2);
    return copy ? copyArray(array2, data2) : extractArray(array2, data2);
  }
  /**
   * Return an array of cached column values.
   * Used internally to accelerate dictionary types.
   */
  cache() {
    return this._cache ?? (this._cache = this.toArray());
  }
}
function* batchedIterator(data2) {
  for (let i = 0; i < data2.length; ++i) {
    const iter = data2[i][Symbol.iterator]();
    for (let next = iter.next(); !next.done; next = iter.next()) {
      yield next.value;
    }
  }
}
function copyArray(array2, data2) {
  for (let i = 0, offset2 = 0; i < data2.length; ++i) {
    const { values: values2 } = data2[i];
    array2.set(values2, offset2);
    offset2 += values2.length;
  }
  return array2;
}
function extractArray(array2, data2) {
  let index = -1;
  for (let i = 0; i < data2.length; ++i) {
    const batch = data2[i];
    for (let j = 0; j < batch.length; ++j) {
      array2[++index] = batch.at(j);
    }
  }
  return array2;
}
class Table3 {
  /**
   * Create a new table with the given schema and columns (children).
   * @param {Schema} schema The table schema.
   * @param {Column[]} children The table columns.
   * @param {boolean} [useProxy=false] Flag indicating if row proxy
   *  objects should be used to represent table rows (default `false`).
   */
  constructor(schema, children, useProxy = false) {
    const names = schema.fields.map((f) => f.name);
    this.schema = schema;
    this.names = names;
    this.children = children;
    this.factory = useProxy ? proxyFactory : objectFactory;
    const gen = [];
    this.getFactory = (b) => gen[b] ?? (gen[b] = this.factory(names, children.map((c) => c.data[b])));
  }
  /**
   * Provide an informative object string tag.
   */
  get [Symbol.toStringTag]() {
    return "Table";
  }
  /**
   * The number of columns in this table.
   * @return {number} The number of columns.
   */
  get numCols() {
    return this.names.length;
  }
  /**
   * The number of rows in this table.
   * @return {number} The number of rows.
   */
  get numRows() {
    return this.children[0]?.length ?? 0;
  }
  /**
   * Return the child column at the given index position.
   * @template {T[keyof T]} R
   * @param {number} index The column index.
   * @returns {Column<R>}
   */
  getChildAt(index) {
    return this.children[index];
  }
  /**
   * Return the first child column with the given name.
   * @template {keyof T} P
   * @param {P} name The column name.
   * @returns {Column<T[P]>}
   */
  getChild(name2) {
    const i = this.names.findIndex((x) => x === name2);
    return i > -1 ? this.children[i] : void 0;
  }
  /**
   * Construct a new table containing only columns at the specified indices.
   * The order of columns in the new table matches the order of input indices.
   * @template {T[keyof T]} V
   * @param {number[]} indices The indices of columns to keep.
   * @param {string[]} [as] Optional new names for selected columns.
   * @returns {Table<{ [key: string]: V }>} A new table with selected columns.
   */
  selectAt(indices, as = []) {
    const { children, factory, schema } = this;
    const { fields } = schema;
    return new Table3(
      {
        ...schema,
        fields: indices.map((i, j) => renameField(fields[i], as[j]))
      },
      indices.map((i) => children[i]),
      factory === proxyFactory
    );
  }
  /**
   * Construct a new table containing only columns with the specified names.
   * If columns have duplicate names, the first (with lowest index) is used.
   * The order of columns in the new table matches the order of input names.
   * @template {keyof T} K
   * @param {K[]} names Names of columns to keep.
   * @param {string[]} [as] Optional new names for selected columns.
   * @returns A new table with columns matching the specified names.
   */
  select(names, as) {
    const all2 = (
      /** @type {K[]} */
      this.names
    );
    const indices = names.map((name2) => all2.indexOf(name2));
    return this.selectAt(indices, as);
  }
  /**
   * Return an object mapping column names to extracted value arrays.
   * @returns {{ [P in keyof T]: ValueArray<T[P]> }}
   */
  toColumns() {
    const { children, names } = this;
    const cols = {};
    names.forEach((name2, i) => cols[name2] = children[i]?.toArray() ?? []);
    return cols;
  }
  /**
   * Return an array of objects representing the rows of this table.
   * @returns {{ [P in keyof T]: T[P] }[]}
   */
  toArray() {
    const { children, getFactory, numRows } = this;
    const data2 = children[0]?.data ?? [];
    const output2 = Array(numRows);
    for (let b = 0, row = -1; b < data2.length; ++b) {
      const f = getFactory(b);
      for (let i = 0; i < data2[b].length; ++i) {
        output2[++row] = f(i);
      }
    }
    return output2;
  }
  /**
   * Return an iterator over objects representing the rows of this table.
   * @returns {Generator<{ [P in keyof T]: T[P] }, any, any>}
   */
  *[Symbol.iterator]() {
    const { children, getFactory } = this;
    const data2 = children[0]?.data ?? [];
    for (let b = 0; b < data2.length; ++b) {
      const f = getFactory(b);
      for (let i = 0; i < data2[b].length; ++i) {
        yield f(i);
      }
    }
  }
  /**
   * Return a row object for the given index.
   * @param {number} index The row index.
   * @returns {{ [P in keyof T]: T[P] }} The row object.
   */
  at(index) {
    const { children, getFactory, numRows } = this;
    if (index < 0 || index >= numRows) return null;
    const [{ offsets }] = children;
    const b = bisect(offsets, index) - 1;
    return getFactory(b)(index - offsets[b]);
  }
  /**
   * Return a row object for the given index. This method is the same as
   * `at()` and is provided for better compatibility with Apache Arrow JS.
   * @param {number} index The row index.
   * @returns {{ [P in keyof T]: T[P] }} The row object.
   */
  get(index) {
    return this.at(index);
  }
}
function renameField(field2, name2) {
  return name2 != null && name2 !== field2.name ? { ...field2, name: name2 } : field2;
}
function batchType(type, options = {}) {
  const { typeId, bitWidth, mode, precision, unit } = (
    /** @type {any} */
    type
  );
  const { useBigInt, useDate, useDecimalInt, useMap, useProxy } = options;
  switch (typeId) {
    case Type.Null:
      return NullBatch;
    case Type.Bool:
      return BoolBatch;
    case Type.Int:
    case Type.Time:
    case Type.Duration:
      return useBigInt || bitWidth < 64 ? DirectBatch : Int64Batch;
    case Type.Float:
      return precision ? DirectBatch : Float16Batch;
    case Type.Date:
      return wrap(
        unit === DateUnit.DAY ? DateDayBatch : DateDayMillisecondBatch,
        useDate && DateBatch
      );
    case Type.Timestamp:
      return wrap(
        unit === TimeUnit.SECOND ? TimestampSecondBatch : unit === TimeUnit.MILLISECOND ? TimestampMillisecondBatch : unit === TimeUnit.MICROSECOND ? TimestampMicrosecondBatch : TimestampNanosecondBatch,
        useDate && DateBatch
      );
    case Type.Decimal:
      return bitWidth === 32 ? useDecimalInt ? DirectBatch : Decimal32NumberBatch : useDecimalInt ? DecimalBigIntBatch : DecimalNumberBatch;
    case Type.Interval:
      return unit === IntervalUnit.DAY_TIME ? IntervalDayTimeBatch : unit === IntervalUnit.YEAR_MONTH ? DirectBatch : IntervalMonthDayNanoBatch;
    case Type.FixedSizeBinary:
      return FixedBinaryBatch;
    case Type.Utf8:
      return Utf8Batch;
    case Type.LargeUtf8:
      return LargeUtf8Batch;
    case Type.Binary:
      return BinaryBatch;
    case Type.LargeBinary:
      return LargeBinaryBatch;
    case Type.BinaryView:
      return BinaryViewBatch;
    case Type.Utf8View:
      return Utf8ViewBatch;
    case Type.List:
      return ListBatch;
    case Type.LargeList:
      return LargeListBatch;
    case Type.Map:
      return useMap ? MapBatch : MapEntryBatch;
    case Type.ListView:
      return ListViewBatch;
    case Type.LargeListView:
      return LargeListViewBatch;
    case Type.FixedSizeList:
      return FixedListBatch;
    case Type.Struct:
      return useProxy ? StructProxyBatch : StructBatch;
    case Type.RunEndEncoded:
      return RunEndEncodedBatch;
    case Type.Dictionary:
      return DictionaryBatch3;
    case Type.Union:
      return mode ? DenseUnionBatch : SparseUnionBatch;
  }
  throw new Error(invalidDataType(typeId));
}
function wrap(BaseClass, WrapperClass) {
  return WrapperClass ? class WrapBatch extends WrapperClass {
    constructor(options) {
      super(new BaseClass(options));
    }
  } : BaseClass;
}
function decodeBlock(buf2, index) {
  return {
    offset: readInt64(buf2, index),
    metadataLength: readInt32(buf2, index + 8),
    bodyLength: readInt64(buf2, index + 16)
  };
}
function decodeBlocks(buf2, index) {
  return readVector(buf2, index, 24, decodeBlock);
}
function decodeRecordBatch(buf2, index, version2) {
  const get2 = readObject(buf2, index);
  if (get2(10, readOffset, 0)) {
    throw new Error("Record batch compression not implemented");
  }
  const offset2 = version2 < Version.V4 ? 8 : 0;
  return {
    length: get2(4, readInt64, 0),
    nodes: readVector(buf2, get2(6, readOffset), 16, (buf3, pos) => ({
      length: readInt64(buf3, pos),
      nullCount: readInt64(buf3, pos + 8)
    })),
    regions: readVector(buf2, get2(8, readOffset), 16 + offset2, (buf3, pos) => ({
      offset: readInt64(buf3, pos + offset2),
      length: readInt64(buf3, pos + offset2 + 8)
    })),
    variadic: readVector(buf2, get2(12, readOffset), 8, readInt64)
  };
}
function decodeDictionaryBatch(buf2, index, version2) {
  const get2 = readObject(buf2, index);
  return {
    id: get2(4, readInt64, 0),
    data: get2(6, (buf3, off) => decodeRecordBatch(buf3, off, version2)),
    /**
     * If isDelta is true the values in the dictionary are to be appended to a
     * dictionary with the indicated id. If isDelta is false this dictionary
     * should replace the existing dictionary.
     */
    isDelta: get2(8, readBoolean, false)
  };
}
function decodeDataType(buf2, index, typeId, children) {
  checkOneOf(typeId, Type, invalidDataType);
  const get2 = readObject(buf2, index);
  switch (typeId) {
    // types without flatbuffer objects
    case Type.Binary:
      return binary();
    case Type.Utf8:
      return utf8();
    case Type.LargeBinary:
      return largeBinary();
    case Type.LargeUtf8:
      return largeUtf8();
    case Type.List:
      return list(children[0]);
    case Type.ListView:
      return listView(children[0]);
    case Type.LargeList:
      return largeList(children[0]);
    case Type.LargeListView:
      return largeListView(children[0]);
    case Type.Struct:
      return struct(children);
    case Type.RunEndEncoded:
      return runEndEncoded(children[0], children[1]);
    // types with flatbuffer objects
    case Type.Int:
      return int(
        // @ts-ignore
        get2(4, readInt32, 0),
        // bitwidth
        get2(6, readBoolean, false)
        // signed
      );
    case Type.Float:
      return float(
        // @ts-ignore
        get2(4, readInt16, Precision.HALF)
        // precision
      );
    case Type.Decimal:
      return decimal(
        get2(4, readInt32, 0),
        // precision
        get2(6, readInt32, 0),
        // scale
        // @ts-ignore
        get2(8, readInt32, 128)
        // bitwidth
      );
    case Type.Date:
      return date(
        // @ts-ignore
        get2(4, readInt16, DateUnit.MILLISECOND)
        // unit
      );
    case Type.Time:
      return time(
        // @ts-ignore
        get2(4, readInt16, TimeUnit.MILLISECOND)
        // unit
      );
    case Type.Timestamp:
      return timestamp(
        // @ts-ignore
        get2(4, readInt16, TimeUnit.SECOND),
        // unit
        get2(6, readString)
        // timezone
      );
    case Type.Interval:
      return interval(
        // @ts-ignore
        get2(4, readInt16, IntervalUnit.YEAR_MONTH)
        // unit
      );
    case Type.Duration:
      return duration(
        // @ts-ignore
        get2(4, readInt16, TimeUnit.MILLISECOND)
        // unit
      );
    case Type.FixedSizeBinary:
      return fixedSizeBinary(
        get2(4, readInt32, 0)
        // stride
      );
    case Type.FixedSizeList:
      return fixedSizeList(
        children[0],
        get2(4, readInt32, 0)
        // stride
      );
    case Type.Map:
      return mapType(
        get2(4, readBoolean, false),
        // keysSorted
        children[0]
      );
    case Type.Union:
      return union(
        // @ts-ignore
        get2(4, readInt16, UnionMode.Sparse),
        // mode
        children,
        readVector(buf2, get2(6, readOffset), 4, readInt32)
        // type ids
      );
  }
  return { typeId };
}
function decodeMetadata(buf2, index) {
  const entries2 = readVector(buf2, index, 4, (buf3, pos) => {
    const get2 = readObject(buf3, pos);
    return (
      /** @type {[string, string]} */
      [
        get2(4, readString),
        // 4: key (string)
        get2(6, readString)
        // 6: key (string)
      ]
    );
  });
  return entries2.length ? new Map(entries2) : null;
}
function decodeSchema(buf2, index, version2) {
  const get2 = readObject(buf2, index);
  return {
    version: version2,
    endianness: (
      /** @type {Endianness_} */
      get2(4, readInt16, 0)
    ),
    fields: get2(6, decodeSchemaFields, []),
    metadata: get2(8, decodeMetadata)
  };
}
function decodeSchemaFields(buf2, fieldsOffset) {
  return readVector(buf2, fieldsOffset, 4, decodeField);
}
function decodeField(buf2, index) {
  const get2 = readObject(buf2, index);
  const typeId = get2(8, readUint8, Type.NONE);
  const typeOffset = get2(10, readOffset, 0);
  const dict = get2(12, decodeDictionary);
  const children = get2(14, (buf3, off) => decodeFieldChildren(buf3, off));
  let type = decodeDataType(buf2, typeOffset, typeId, children);
  if (dict) {
    dict.dictionary = type;
    type = dict;
  }
  return {
    name: get2(4, readString),
    type,
    nullable: get2(6, readBoolean, false),
    metadata: get2(16, decodeMetadata)
  };
}
function decodeFieldChildren(buf2, fieldOffset) {
  const children = readVector(buf2, fieldOffset, 4, decodeField);
  return children.length ? children : null;
}
function decodeDictionary(buf2, index) {
  if (!index) return null;
  const get2 = readObject(buf2, index);
  return dictionary$1(
    null,
    // data type will be populated by caller
    get2(6, decodeInt, int32()),
    // index type
    get2(8, readBoolean, false),
    // ordered
    get2(4, readInt64, 0)
    // id
  );
}
function decodeInt(buf2, index) {
  return (
    /** @type {IntType} */
    decodeDataType(buf2, index, Type.Int)
  );
}
const invalidMessageMetadata = (expected, actual) => `Expected to read ${expected} metadata bytes, but only read ${actual}.`;
const invalidMessageBodyLength = (expected, actual) => `Expected to read ${expected} bytes for message body, but only read ${actual}.`;
const invalidMessageType = (type) => `Unsupported message type: ${type} (${keyFor(MessageHeader, type)})`;
function decodeMessage(buf2, index) {
  let metadataLength = readInt32(buf2, index) || 0;
  index += SIZEOF_INT;
  if (metadataLength === -1) {
    metadataLength = readInt32(buf2, index) || 0;
    index += SIZEOF_INT;
  }
  if (metadataLength === 0) return null;
  const head = buf2.subarray(index, index += metadataLength);
  if (head.byteLength < metadataLength) {
    throw new Error(invalidMessageMetadata(metadataLength, head.byteLength));
  }
  const get2 = readObject(head, 0);
  const version2 = (
    /** @type {Version_} */
    get2(4, readInt16, Version.V1)
  );
  const type = (
    /** @type {MessageHeader_} */
    get2(6, readUint8, MessageHeader.NONE)
  );
  const offset2 = get2(8, readOffset, 0);
  const bodyLength = get2(10, readInt64, 0);
  let content;
  if (offset2) {
    const decoder2 = type === MessageHeader.Schema ? decodeSchema : type === MessageHeader.DictionaryBatch ? decodeDictionaryBatch : type === MessageHeader.RecordBatch ? decodeRecordBatch : null;
    if (!decoder2) throw new Error(invalidMessageType(type));
    content = decoder2(head, offset2, version2);
    if (bodyLength > 0) {
      const body = buf2.subarray(index, index += bodyLength);
      if (body.byteLength < bodyLength) {
        throw new Error(invalidMessageBodyLength(bodyLength, body.byteLength));
      }
      content.body = body;
    } else if (type !== MessageHeader.Schema) {
      content.body = new Uint8Array(0);
    }
  }
  return { version: version2, type, index, content };
}
function decodeIPC(data2) {
  const source2 = isArrayBufferLike(data2) ? new Uint8Array(data2) : data2;
  return source2 instanceof Uint8Array && isArrowFileFormat(source2) ? decodeIPCFile(source2) : decodeIPCStream(source2);
}
function isArrowFileFormat(buf2) {
  if (!buf2 || buf2.length < 4) return false;
  for (let i = 0; i < 6; ++i) {
    if (MAGIC[i] !== buf2[i]) return false;
  }
  return true;
}
function decodeIPCStream(data2) {
  const stream = [data2].flat();
  let schema;
  const records = [];
  const dictionaries = [];
  for (const buf2 of stream) {
    if (!(buf2 instanceof Uint8Array)) {
      throw new Error(`IPC data batch was not a Uint8Array.`);
    }
    let offset2 = 0;
    while (true) {
      const m = decodeMessage(buf2, offset2);
      if (m === null) break;
      offset2 = m.index;
      if (!m.content) continue;
      switch (m.type) {
        case MessageHeader.Schema:
          if (!schema) schema = m.content;
          break;
        case MessageHeader.RecordBatch:
          records.push(m.content);
          break;
        case MessageHeader.DictionaryBatch:
          dictionaries.push(m.content);
          break;
      }
    }
  }
  return (
    /** @type {ArrowData} */
    { schema, dictionaries, records, metadata: null }
  );
}
function decodeIPCFile(data2) {
  const offset2 = data2.byteLength - (MAGIC.length + 4);
  const length2 = readInt32(data2, offset2);
  const get2 = readObject(data2, offset2 - length2);
  const version2 = (
    /** @type {Version_} */
    get2(4, readInt16, Version.V1)
  );
  const dicts = get2(8, decodeBlocks, []);
  const recs = get2(10, decodeBlocks, []);
  return (
    /** @type {ArrowData} */
    {
      schema: get2(6, (buf2, index) => decodeSchema(buf2, index, version2)),
      dictionaries: dicts.map(({ offset: offset3 }) => decodeMessage(data2, offset3).content),
      records: recs.map(({ offset: offset3 }) => decodeMessage(data2, offset3).content),
      metadata: get2(12, decodeMetadata)
    }
  );
}
function tableFromIPC(data2, options) {
  return createTable(decodeIPC(data2), options);
}
function createTable(data2, options = {}) {
  const { schema = { fields: [] }, dictionaries, records } = data2;
  const { version: version2, fields } = schema;
  const dictionaryMap = /* @__PURE__ */ new Map();
  const context = contextGenerator(options, version2, dictionaryMap);
  const dictionaryTypes = /* @__PURE__ */ new Map();
  visitSchemaFields(schema, (field2) => {
    const type = field2.type;
    if (type.typeId === Type.Dictionary) {
      dictionaryTypes.set(type.id, type.dictionary);
    }
  });
  const dicts = /* @__PURE__ */ new Map();
  for (const dict of dictionaries) {
    const { id, data: data3, isDelta, body } = dict;
    const type = dictionaryTypes.get(id);
    const batch = visit$1(type, context({ ...data3, body }));
    if (!dicts.has(id)) {
      if (isDelta) {
        throw new Error("Delta update can not be first dictionary batch.");
      }
      dicts.set(id, columnBuilder(type).add(batch));
    } else {
      const dict2 = dicts.get(id);
      if (!isDelta) dict2.clear();
      dict2.add(batch);
    }
  }
  dicts.forEach((value2, key2) => dictionaryMap.set(key2, value2.done()));
  const cols = fields.map((f) => columnBuilder(f.type));
  for (const batch of records) {
    const ctx = context(batch);
    fields.forEach((f, i) => cols[i].add(visit$1(f.type, ctx)));
  }
  return new Table3(schema, cols.map((c) => c.done()), options.useProxy);
}
function visitSchemaFields(schema, visitor) {
  schema.fields.forEach(function visitField(field2) {
    visitor(field2);
    field2.type.dictionary?.children?.forEach(visitField);
    field2.type.children?.forEach(visitField);
  });
}
function contextGenerator(options, version2, dictionaryMap) {
  const base = {
    version: version2,
    options,
    dictionary: (id) => dictionaryMap.get(id)
  };
  return (batch) => {
    const { length: length2, nodes, regions, variadic, body } = batch;
    let nodeIndex = -1;
    let bufferIndex = -1;
    let variadicIndex = -1;
    return {
      ...base,
      length: length2,
      node: () => nodes[++nodeIndex],
      buffer: (ArrayType) => {
        const { length: length3, offset: offset2 } = regions[++bufferIndex];
        return ArrayType ? new ArrayType(body.buffer, body.byteOffset + offset2, length3 / ArrayType.BYTES_PER_ELEMENT) : body.subarray(offset2, offset2 + length3);
      },
      variadic: () => variadic[++variadicIndex],
      visit(children) {
        return children.map((f) => visit$1(f.type, this));
      }
    };
  };
}
function visit$1(type, ctx) {
  const { typeId } = type;
  const { options, node, buffer: buffer2, variadic, version: version2 } = ctx;
  const BatchType = batchType(type, options);
  const base = { ...node(), type };
  if (typeId === Type.Null) {
    return new BatchType({ ...base, nullCount: base.length });
  }
  switch (typeId) {
    // validity and data value buffers
    case Type.Bool:
    case Type.Int:
    case Type.Time:
    case Type.Duration:
    case Type.Float:
    case Type.Decimal:
    case Type.Date:
    case Type.Timestamp:
    case Type.Interval:
    case Type.FixedSizeBinary:
      return new BatchType({
        ...base,
        validity: buffer2(),
        values: buffer2(type.values)
      });
    // validity, offset, and value buffers
    case Type.Utf8:
    case Type.LargeUtf8:
    case Type.Binary:
    case Type.LargeBinary:
      return new BatchType({
        ...base,
        validity: buffer2(),
        offsets: buffer2(type.offsets),
        values: buffer2()
      });
    // views with variadic buffers
    case Type.BinaryView:
    case Type.Utf8View:
      return new BatchType({
        ...base,
        validity: buffer2(),
        values: buffer2(),
        // views buffer
        data: Array.from({ length: variadic() }, () => buffer2())
        // data buffers
      });
    // validity, offset, and list child
    case Type.List:
    case Type.LargeList:
    case Type.Map:
      return new BatchType({
        ...base,
        validity: buffer2(),
        offsets: buffer2(type.offsets),
        children: ctx.visit(type.children)
      });
    // validity, offset, size, and list child
    case Type.ListView:
    case Type.LargeListView:
      return new BatchType({
        ...base,
        validity: buffer2(),
        offsets: buffer2(type.offsets),
        sizes: buffer2(type.offsets),
        children: ctx.visit(type.children)
      });
    // validity and children
    case Type.FixedSizeList:
    case Type.Struct:
      return new BatchType({
        ...base,
        validity: buffer2(),
        children: ctx.visit(type.children)
      });
    // children only
    case Type.RunEndEncoded:
      return new BatchType({
        ...base,
        children: ctx.visit(type.children)
      });
    // dictionary
    case Type.Dictionary: {
      const { id, indices } = type;
      return new BatchType({
        ...base,
        validity: buffer2(),
        values: buffer2(indices.values)
      }).setDictionary(ctx.dictionary(id));
    }
    // union
    case Type.Union: {
      if (version2 < Version.V5) {
        buffer2();
      }
      return new BatchType({
        ...base,
        typeIds: buffer2(int8Array),
        offsets: type.mode === UnionMode.Sparse ? null : buffer2(type.offsets),
        children: ctx.visit(type.children)
      });
    }
    // unsupported type
    default:
      throw new Error(invalidDataType(typeId));
  }
}
function writeInt32(buf2, index, value2) {
  buf2[index] = value2;
  buf2[index + 1] = value2 >> 8;
  buf2[index + 2] = value2 >> 16;
  buf2[index + 3] = value2 >> 24;
}
const INIT_SIZE = 1024;
class Builder2 {
  /**
   * Create a new builder instance.
   * @param {Sink} sink The byte consumer.
   */
  constructor(sink) {
    this.sink = sink;
    this.minalign = 1;
    this.buf = new Uint8Array(INIT_SIZE);
    this.space = INIT_SIZE;
    this.vtables = [];
    this.outputBytes = 0;
  }
  /**
   * Returns the flatbuffer offset, relative to the end of the current buffer.
   * @returns {number} Offset relative to the end of the buffer.
   */
  offset() {
    return this.buf.length - this.space;
  }
  /**
   * Write a flatbuffer int8 value at the current buffer position
   * and advance the internal cursor.
   * @param {number} value
   */
  writeInt8(value2) {
    this.buf[this.space -= 1] = value2;
  }
  /**
   * Write a flatbuffer int16 value at the current buffer position
   * and advance the internal cursor.
   * @param {number} value
   */
  writeInt16(value2) {
    this.buf[this.space -= 2] = value2;
    this.buf[this.space + 1] = value2 >> 8;
  }
  /**
   * Write a flatbuffer int32 value at the current buffer position
   * and advance the internal cursor.
   * @param {number} value
   */
  writeInt32(value2) {
    writeInt32(this.buf, this.space -= 4, value2);
  }
  /**
   * Write a flatbuffer int64 value at the current buffer position
   * and advance the internal cursor.
   * @param {number} value
   */
  writeInt64(value2) {
    const v = BigInt(value2);
    this.writeInt32(Number(BigInt.asIntN(32, v >> BigInt(32))));
    this.writeInt32(Number(BigInt.asIntN(32, v)));
  }
  /**
   * Add a flatbuffer int8 value, properly aligned,
   * @param value The int8 value to add the buffer.
   */
  addInt8(value2) {
    prep(this, 1, 0);
    this.writeInt8(value2);
  }
  /**
   * Add a flatbuffer int16 value, properly aligned,
   * @param value The int16 value to add the buffer.
   */
  addInt16(value2) {
    prep(this, 2, 0);
    this.writeInt16(value2);
  }
  /**
   * Add a flatbuffer int32 value, properly aligned,
   * @param value The int32 value to add the buffer.
   */
  addInt32(value2) {
    prep(this, 4, 0);
    this.writeInt32(value2);
  }
  /**
   * Add a flatbuffer int64 values, properly aligned.
   * @param value The int64 value to add the buffer.
   */
  addInt64(value2) {
    prep(this, 8, 0);
    this.writeInt64(value2);
  }
  /**
   * Add a flatbuffer offset, relative to where it will be written.
   * @param {number} offset The offset to add.
   */
  addOffset(offset2) {
    prep(this, SIZEOF_INT, 0);
    this.writeInt32(this.offset() - offset2 + SIZEOF_INT);
  }
  /**
   * Add a flatbuffer object (vtable).
   * @param {number} numFields The maximum number of fields
   *  this object may include.
   * @param {(tableBuilder: ReturnType<objectBuilder>) => void} [addFields]
   *  A callback function that writes all fields using an object builder.
   * @returns {number} The object offset.
   */
  addObject(numFields, addFields) {
    const b = objectBuilder(this, numFields);
    addFields?.(b);
    return b.finish();
  }
  /**
   * Add a flatbuffer vector (list).
   * @template T
   * @param {T[]} items An array of items to write.
   * @param {number} itemSize The size in bytes of a serialized item.
   * @param {number} alignment The desired byte alignment value.
   * @param {(builder: this, item: T) => void} writeItem A callback
   *  function that writes a vector item to this builder.
   * @returns {number} The vector offset.
   */
  addVector(items, itemSize, alignment, writeItem) {
    const n = items?.length;
    if (!n) return 0;
    prep(this, SIZEOF_INT, itemSize * n);
    prep(this, alignment, itemSize * n);
    for (let i = n; --i >= 0; ) {
      writeItem(this, items[i]);
    }
    this.writeInt32(n);
    return this.offset();
  }
  /**
   * Convenience method for writing a vector of byte buffer offsets.
   * @param {number[]} offsets
   * @returns {number} The vector offset.
   */
  addOffsetVector(offsets) {
    return this.addVector(offsets, 4, 4, (b, off) => b.addOffset(off));
  }
  /**
   * Add a flatbuffer UTF-8 string.
   * @param {string} s The string to encode.
   * @return {number} The string offset.
   */
  addString(s) {
    if (s == null) return 0;
    const utf82 = encodeUtf8(s);
    const n = utf82.length;
    this.addInt8(0);
    prep(this, SIZEOF_INT, n);
    this.buf.set(utf82, this.space -= n);
    this.writeInt32(n);
    return this.offset();
  }
  /**
   * Finish the current flatbuffer by adding a root offset.
   * @param {number} rootOffset The root offset.
   */
  finish(rootOffset) {
    prep(this, this.minalign, SIZEOF_INT);
    this.addOffset(rootOffset);
  }
  /**
   * Flush the current flatbuffer byte buffer content to the sink,
   * and reset the flatbuffer builder state.
   */
  flush() {
    const { buf: buf2, sink } = this;
    const bytes = buf2.subarray(this.space, buf2.length);
    sink.write(bytes);
    this.outputBytes += bytes.byteLength;
    this.minalign = 1;
    this.vtables = [];
    this.buf = new Uint8Array(INIT_SIZE);
    this.space = INIT_SIZE;
  }
  /**
   * Add a byte buffer directly to the builder sink. This method bypasses
   * any unflushed flatbuffer state and leaves it unchanged, writing the
   * buffer to the sink *before* the flatbuffer.
   * The buffer will be padded for 64-bit (8-byte) alignment as needed.
   * @param {Uint8Array} buffer The buffer to add.
   * @returns {number} The total byte count of the buffer and padding.
   */
  addBuffer(buffer2) {
    const size = buffer2.byteLength;
    if (!size) return 0;
    this.sink.write(buffer2);
    this.outputBytes += size;
    const pad3 = (size + 7 & -8) - size;
    this.addPadding(pad3);
    return size + pad3;
  }
  /**
   * Write padding bytes directly to the builder sink. This method bypasses
   * any unflushed flatbuffer state and leaves it unchanged, writing the
   * padding bytes to the sink *before* the flatbuffer.
   * @param {number} byteCount The number of padding bytes.
   */
  addPadding(byteCount) {
    if (byteCount > 0) {
      this.sink.write(new Uint8Array(byteCount));
      this.outputBytes += byteCount;
    }
  }
}
function prep(builder2, size, additionalBytes) {
  let { buf: buf2, space, minalign } = builder2;
  if (size > minalign) {
    builder2.minalign = size;
  }
  const bufSize = buf2.length;
  const used = bufSize - space + additionalBytes;
  const alignSize = ~used + 1 & size - 1;
  buf2 = grow(buf2, used + alignSize + size - 1, true);
  space += buf2.length - bufSize;
  for (let i = 0; i < alignSize; ++i) {
    buf2[--space] = 0;
  }
  builder2.buf = buf2;
  builder2.space = space;
}
function objectBuilder(builder2, numFields) {
  const vtable = Array(numFields).fill(0);
  const startOffset = builder2.offset();
  function slot(index) {
    vtable[index] = builder2.offset();
  }
  return {
    /**
     * Add an int8-valued table field.
     * @param {number} index
     * @param {number} value
     * @param {number} defaultValue
     */
    addInt8(index, value2, defaultValue) {
      if (value2 != defaultValue) {
        builder2.addInt8(value2);
        slot(index);
      }
    },
    /**
     * Add an int16-valued table field.
     * @param {number} index
     * @param {number} value
     * @param {number} defaultValue
     */
    addInt16(index, value2, defaultValue) {
      if (value2 != defaultValue) {
        builder2.addInt16(value2);
        slot(index);
      }
    },
    /**
     * Add an int32-valued table field.
     * @param {number} index
     * @param {number} value
     * @param {number} defaultValue
     */
    addInt32(index, value2, defaultValue) {
      if (value2 != defaultValue) {
        builder2.addInt32(value2);
        slot(index);
      }
    },
    /**
     * Add an int64-valued table field.
     * @param {number} index
     * @param {number} value
     * @param {number} defaultValue
     */
    addInt64(index, value2, defaultValue) {
      if (value2 != defaultValue) {
        builder2.addInt64(value2);
        slot(index);
      }
    },
    /**
     * Add a buffer offset-valued table field.
     * @param {number} index
     * @param {number} value
     * @param {number} defaultValue
     */
    addOffset(index, value2, defaultValue) {
      if (value2 != defaultValue) {
        builder2.addOffset(value2);
        slot(index);
      }
    },
    /**
     * Write the vtable to the buffer and return the table offset.
     * @returns {number} The buffer offset to the vtable.
     */
    finish() {
      builder2.addInt32(0);
      const vtableOffset = builder2.offset();
      let i = numFields;
      while (--i >= 0 && vtable[i] === 0) {
      }
      const size = i + 1;
      for (; i >= 0; --i) {
        builder2.addInt16(vtable[i] ? vtableOffset - vtable[i] : 0);
      }
      const standardFields = 2;
      builder2.addInt16(vtableOffset - startOffset);
      const len = (size + standardFields) * SIZEOF_SHORT;
      builder2.addInt16(len);
      let existingTable = 0;
      const { buf: buf2, vtables, space: vt1 } = builder2;
      outer_loop:
        for (i = 0; i < vtables.length; ++i) {
          const vt2 = buf2.length - vtables[i];
          if (len == readInt16(buf2, vt2)) {
            for (let j = SIZEOF_SHORT; j < len; j += SIZEOF_SHORT) {
              if (readInt16(buf2, vt1 + j) != readInt16(buf2, vt2 + j)) {
                continue outer_loop;
              }
            }
            existingTable = vtables[i];
            break;
          }
        }
      if (existingTable) {
        builder2.space = buf2.length - vtableOffset;
        writeInt32(buf2, builder2.space, existingTable - vtableOffset);
      } else {
        const off = builder2.offset();
        vtables.push(off);
        writeInt32(buf2, buf2.length - vtableOffset, off - vtableOffset);
      }
      return vtableOffset;
    }
  };
}
function encodeRecordBatch(builder2, batch) {
  const { nodes, regions, variadic } = batch;
  const nodeVector = builder2.addVector(
    nodes,
    16,
    8,
    (builder3, node) => {
      builder3.writeInt64(node.nullCount);
      builder3.writeInt64(node.length);
      return builder3.offset();
    }
  );
  const regionVector = builder2.addVector(
    regions,
    16,
    8,
    (builder3, region) => {
      builder3.writeInt64(region.length);
      builder3.writeInt64(region.offset);
      return builder3.offset();
    }
  );
  const variadicVector = builder2.addVector(
    variadic,
    8,
    8,
    (builder3, count2) => builder3.addInt64(count2)
  );
  return builder2.addObject(5, (b) => {
    b.addInt64(0, nodes[0].length, 0);
    b.addOffset(1, nodeVector, 0);
    b.addOffset(2, regionVector, 0);
    b.addOffset(4, variadicVector, 0);
  });
}
function encodeDictionaryBatch(builder2, dictionaryBatch) {
  const dataOffset = encodeRecordBatch(builder2, dictionaryBatch.data);
  return builder2.addObject(3, (b) => {
    b.addInt64(0, dictionaryBatch.id, 0);
    b.addOffset(1, dataOffset, 0);
    b.addInt8(2, +dictionaryBatch.isDelta, 0);
  });
}
function encodeMetadata(builder2, metadata) {
  return metadata?.size > 0 ? builder2.addOffsetVector(Array.from(metadata, ([k, v]) => {
    const key2 = builder2.addString(`${k}`);
    const val = builder2.addString(`${v}`);
    return builder2.addObject(2, (b) => {
      b.addOffset(0, key2, 0);
      b.addOffset(1, val, 0);
    });
  })) : 0;
}
function encodeDataType(builder2, type) {
  const typeId = checkOneOf(type.typeId, Type, invalidDataType);
  switch (typeId) {
    case Type.Dictionary:
      return encodeDictionary(builder2, type);
    case Type.Int:
      return encodeInt(builder2, type);
    case Type.Float:
      return encodeFloat(builder2, type);
    case Type.Decimal:
      return encodeDecimal(builder2, type);
    case Type.Date:
      return encodeDate(builder2, type);
    case Type.Time:
      return encodeTime(builder2, type);
    case Type.Timestamp:
      return encodeTimestamp(builder2, type);
    case Type.Interval:
      return encodeInterval(builder2, type);
    case Type.Duration:
      return encodeDuration(builder2, type);
    case Type.FixedSizeBinary:
    case Type.FixedSizeList:
      return encodeFixedSize(builder2, type);
    case Type.Map:
      return encodeMap(builder2, type);
    case Type.Union:
      return encodeUnion(builder2, type);
  }
  return builder2.addObject(0);
}
function encodeDate(builder2, type) {
  return builder2.addObject(1, (b) => {
    b.addInt16(0, type.unit, DateUnit.MILLISECOND);
  });
}
function encodeDecimal(builder2, type) {
  return builder2.addObject(3, (b) => {
    b.addInt32(0, type.precision, 0);
    b.addInt32(1, type.scale, 0);
    b.addInt32(2, type.bitWidth, 128);
  });
}
function encodeDuration(builder2, type) {
  return builder2.addObject(1, (b) => {
    b.addInt16(0, type.unit, TimeUnit.MILLISECOND);
  });
}
function encodeFixedSize(builder2, type) {
  return builder2.addObject(1, (b) => {
    b.addInt32(0, type.stride, 0);
  });
}
function encodeFloat(builder2, type) {
  return builder2.addObject(1, (b) => {
    b.addInt16(0, type.precision, Precision.HALF);
  });
}
function encodeInt(builder2, type) {
  return builder2.addObject(2, (b) => {
    b.addInt32(0, type.bitWidth, 0);
    b.addInt8(1, +type.signed, 0);
  });
}
function encodeInterval(builder2, type) {
  return builder2.addObject(1, (b) => {
    b.addInt16(0, type.unit, IntervalUnit.YEAR_MONTH);
  });
}
function encodeMap(builder2, type) {
  return builder2.addObject(1, (b) => {
    b.addInt8(0, +type.keysSorted, 0);
  });
}
function encodeTime(builder2, type) {
  return builder2.addObject(2, (b) => {
    b.addInt16(0, type.unit, TimeUnit.MILLISECOND);
    b.addInt32(1, type.bitWidth, 32);
  });
}
function encodeTimestamp(builder2, type) {
  const timezoneOffset = builder2.addString(type.timezone);
  return builder2.addObject(2, (b) => {
    b.addInt16(0, type.unit, TimeUnit.SECOND);
    b.addOffset(1, timezoneOffset, 0);
  });
}
function encodeUnion(builder2, type) {
  const typeIdsOffset = builder2.addVector(
    type.typeIds,
    4,
    4,
    (builder3, value2) => builder3.addInt32(value2)
  );
  return builder2.addObject(2, (b) => {
    b.addInt16(0, type.mode, UnionMode.Sparse);
    b.addOffset(1, typeIdsOffset, 0);
  });
}
function encodeDictionary(builder2, type) {
  return builder2.addObject(4, (b) => {
    b.addInt64(0, type.id, 0);
    b.addOffset(1, encodeDataType(builder2, type.indices), 0);
    b.addInt8(2, +type.ordered, 0);
  });
}
const isLittleEndian = new Uint16Array(new Uint8Array([1, 0]).buffer)[0] === 1;
function encodeSchema(builder2, schema) {
  const { fields, metadata } = schema;
  const fieldOffsets = fields.map((f) => encodeField(builder2, f));
  const fieldsVectorOffset = builder2.addOffsetVector(fieldOffsets);
  const metadataOffset = encodeMetadata(builder2, metadata);
  return builder2.addObject(4, (b) => {
    b.addInt16(0, +!isLittleEndian, 0);
    b.addOffset(1, fieldsVectorOffset, 0);
    b.addOffset(2, metadataOffset, 0);
  });
}
function encodeField(builder2, field2) {
  const { name: name2, nullable, type, metadata } = field2;
  let { typeId } = type;
  let typeOffset = 0;
  let dictionaryOffset = 0;
  if (typeId !== Type.Dictionary) {
    typeOffset = encodeDataType(builder2, type);
  } else {
    const dict = (
      /** @type {DictionaryType} */
      type.dictionary
    );
    typeId = dict.typeId;
    dictionaryOffset = encodeDataType(builder2, type);
    typeOffset = encodeDataType(builder2, dict);
  }
  const childOffsets = (type.children || []).map((f) => encodeField(builder2, f));
  const childrenVectorOffset = builder2.addOffsetVector(childOffsets);
  const metadataOffset = encodeMetadata(builder2, metadata);
  const nameOffset = builder2.addString(name2);
  return builder2.addObject(7, (b) => {
    b.addOffset(0, nameOffset, 0);
    b.addInt8(1, +nullable, 0);
    b.addInt8(2, typeId, Type.NONE);
    b.addOffset(3, typeOffset, 0);
    b.addOffset(4, dictionaryOffset, 0);
    b.addOffset(5, childrenVectorOffset, 0);
    b.addOffset(6, metadataOffset, 0);
  });
}
function writeFooter(builder2, schema, dictBlocks, recordBlocks, metadata) {
  const metadataOffset = encodeMetadata(builder2, metadata);
  const recsOffset = builder2.addVector(recordBlocks, 24, 8, encodeBlock);
  const dictsOffset = builder2.addVector(dictBlocks, 24, 8, encodeBlock);
  const schemaOffset = encodeSchema(builder2, schema);
  builder2.finish(
    builder2.addObject(5, (b) => {
      b.addInt16(0, Version.V5, Version.V1);
      b.addOffset(1, schemaOffset, 0);
      b.addOffset(2, dictsOffset, 0);
      b.addOffset(3, recsOffset, 0);
      b.addOffset(4, metadataOffset, 0);
    })
  );
  const size = builder2.offset();
  builder2.addInt32(0);
  builder2.addInt32(-1);
  builder2.flush();
  builder2.sink.write(new Uint8Array(Int32Array.of(size).buffer));
  builder2.sink.write(MAGIC);
}
function encodeBlock(builder2, { offset: offset2, metadataLength, bodyLength }) {
  builder2.writeInt64(bodyLength);
  builder2.writeInt32(0);
  builder2.writeInt32(metadataLength);
  builder2.writeInt64(offset2);
  return builder2.offset();
}
function writeMessage(builder2, headerType, headerOffset, bodyLength, blocks) {
  builder2.finish(
    builder2.addObject(5, (b) => {
      b.addInt16(0, Version.V5, Version.V1);
      b.addInt8(1, headerType, MessageHeader.NONE);
      b.addOffset(2, headerOffset, 0);
      b.addInt64(3, bodyLength, 0);
    })
  );
  const prefixSize = 8;
  const messageSize = builder2.offset();
  const alignedSize = messageSize + prefixSize + 7 & -8;
  blocks?.push({
    offset: builder2.outputBytes,
    metadataLength: alignedSize,
    bodyLength
  });
  builder2.addInt32(alignedSize - prefixSize);
  builder2.addInt32(-1);
  builder2.flush();
  builder2.addPadding(alignedSize - messageSize - prefixSize);
}
class Sink {
  /**
   * Write bytes to this sink.
   * @param {Uint8Array} bytes The byte buffer to write.
   */
  write(bytes) {
  }
  /**
   * Write padding bytes (zeroes) to this sink.
   * @param {number} byteCount The number of padding bytes.
   */
  pad(byteCount) {
    this.write(new Uint8Array(byteCount));
  }
  /**
   * @returns {Uint8Array | null}
   */
  finish() {
    return null;
  }
}
class MemorySink extends Sink {
  /**
   * A sink that collects bytes in memory.
   */
  constructor() {
    super();
    this.buffers = [];
  }
  /**
   * Write bytes
   * @param {Uint8Array} bytes
   */
  write(bytes) {
    this.buffers.push(bytes);
  }
  /**
   * @returns {Uint8Array}
   */
  finish() {
    const bufs = this.buffers;
    const size = bufs.reduce((sum, b) => sum + b.byteLength, 0);
    const buf2 = new Uint8Array(size);
    for (let i = 0, off = 0; i < bufs.length; ++i) {
      buf2.set(bufs[i], off);
      off += bufs[i].byteLength;
    }
    return buf2;
  }
}
const STREAM = "stream";
const FILE = "file";
function encodeIPC(data2, { sink, format = STREAM } = {}) {
  if (format !== STREAM && format !== FILE) {
    throw new Error(`Unrecognized Arrow IPC format: ${format}`);
  }
  const { schema, dictionaries = [], records = [], metadata } = data2;
  const builder2 = new Builder2(sink || new MemorySink());
  const file = format === FILE;
  const dictBlocks = [];
  const recordBlocks = [];
  if (file) {
    builder2.addBuffer(MAGIC);
  }
  if (schema) {
    writeMessage(
      builder2,
      MessageHeader.Schema,
      encodeSchema(builder2, schema),
      0
    );
  }
  for (const dict of dictionaries) {
    const { data: data3 } = dict;
    writeMessage(
      builder2,
      MessageHeader.DictionaryBatch,
      encodeDictionaryBatch(builder2, dict),
      data3.byteLength,
      dictBlocks
    );
    writeBuffers(builder2, data3.buffers);
  }
  for (const batch of records) {
    writeMessage(
      builder2,
      MessageHeader.RecordBatch,
      encodeRecordBatch(builder2, batch),
      batch.byteLength,
      recordBlocks
    );
    writeBuffers(builder2, batch.buffers);
  }
  builder2.addBuffer(EOS);
  if (file) {
    writeFooter(builder2, schema, dictBlocks, recordBlocks, metadata);
  }
  return builder2.sink;
}
function writeBuffers(builder2, buffers) {
  for (let i = 0; i < buffers.length; ++i) {
    builder2.addBuffer(buffers[i]);
  }
}
function tableToIPC(table2, options) {
  if (typeof options === "string") {
    options = { format: options };
  }
  const columns2 = table2.children;
  checkBatchLengths(columns2);
  const { dictionaries, idMap } = assembleDictionaryBatches(columns2);
  const records = assembleRecordBatches(columns2);
  const schema = assembleSchema(table2.schema, idMap);
  const data2 = { schema, dictionaries, records };
  return encodeIPC(data2, options).finish();
}
function checkBatchLengths(columns2) {
  const n = columns2[0]?.data.map((d) => d.length);
  columns2.forEach(({ data: data2 }) => {
    if (data2.length !== n.length || data2.some((b, i) => b.length !== n[i])) {
      throw new Error("Columns have inconsistent batch sizes.");
    }
  });
}
function assembleContext() {
  let byteLength = 0;
  const nodes = [];
  const regions = [];
  const buffers = [];
  const variadic = [];
  return {
    /**
     * @param {number} length
     * @param {number} nullCount
     */
    node(length2, nullCount) {
      nodes.push({ length: length2, nullCount });
    },
    /**
     * @param {TypedArray} b
     */
    buffer(b) {
      const size = b.byteLength;
      const length2 = size + 7 & -8;
      regions.push({ offset: byteLength, length: length2 });
      byteLength += length2;
      buffers.push(new Uint8Array(b.buffer, b.byteOffset, size));
    },
    /**
     * @param {number} length
     */
    variadic(length2) {
      variadic.push(length2);
    },
    /**
     * @param {DataType} type
     * @param {Batch} batch
     */
    children(type, batch) {
      type.children.forEach((field2, index) => {
        visit(field2.type, batch.children[index], this);
      });
    },
    /**
     * @returns {RecordBatch}
     */
    done() {
      return { byteLength, nodes, regions, variadic, buffers };
    }
  };
}
function assembleDictionaryBatches(columns2) {
  const dictionaries = [];
  const dictMap = /* @__PURE__ */ new Map();
  const idMap = /* @__PURE__ */ new Map();
  let id = -1;
  const visitor = (dictionaryColumn) => {
    if (!dictMap.has(dictionaryColumn)) {
      dictMap.set(dictionaryColumn, ++id);
      for (let i = 0; i < dictionaryColumn.data.length; ++i) {
        dictionaries.push({
          id,
          isDelta: i > 0,
          data: assembleRecordBatch([dictionaryColumn], i)
        });
      }
      idMap.set(dictionaryColumn.type, id);
    } else {
      idMap.set(dictionaryColumn.type, dictMap.get(dictionaryColumn));
    }
  };
  columns2.forEach((col) => visitDictionaries(col.data[0], visitor));
  return { dictionaries, idMap };
}
function visitDictionaries(batch, visitor) {
  if (batch?.type.typeId === Type.Dictionary) {
    const dictionary2 = batch.dictionary;
    visitor(dictionary2);
    visitDictionaries(dictionary2.data[0], visitor);
  }
  batch?.children?.forEach((child) => visitDictionaries(child, visitor));
}
function assembleSchema(schema, idMap) {
  if (!idMap.size) return schema;
  const visit2 = (type) => {
    if (type.typeId === Type.Dictionary) {
      type.id = idMap.get(type.dictionary);
      visitDictType(type);
    }
    if (type.children) {
      (type.children = type.children.slice()).forEach(visitFields);
    }
  };
  const visitFields = (field2, index, array2) => {
    const type = { ...field2.type };
    array2[index] = { ...field2, type };
    visit2(type);
  };
  const visitDictType = (parentType) => {
    const type = { ...parentType.dictionary };
    parentType.dictionary = type;
    visit2(type);
  };
  schema = { ...schema, fields: schema.fields.slice() };
  schema.fields.forEach(visitFields);
  return schema;
}
function assembleRecordBatches(columns2) {
  return (columns2[0]?.data || []).map((_, index) => assembleRecordBatch(columns2, index));
}
function assembleRecordBatch(columns2, batchIndex = 0) {
  const ctx = assembleContext();
  columns2.forEach((column) => {
    visit(column.type, column.data[batchIndex], ctx);
  });
  return ctx.done();
}
function visit(type, batch, ctx) {
  const { typeId } = type;
  ctx.node(batch.length, batch.nullCount);
  if (typeId === Type.Null) return;
  switch (typeId) {
    // validity and value buffers
    // backing dictionaries handled elsewhere
    case Type.Bool:
    case Type.Int:
    case Type.Time:
    case Type.Duration:
    case Type.Float:
    case Type.Date:
    case Type.Timestamp:
    case Type.Decimal:
    case Type.Interval:
    case Type.FixedSizeBinary:
    case Type.Dictionary:
      ctx.buffer(batch.validity);
      ctx.buffer(batch.values);
      return;
    // validity, offset, and value buffers
    case Type.Utf8:
    case Type.LargeUtf8:
    case Type.Binary:
    case Type.LargeBinary:
      ctx.buffer(batch.validity);
      ctx.buffer(batch.offsets);
      ctx.buffer(batch.values);
      return;
    // views with variadic buffers
    case Type.BinaryView:
    case Type.Utf8View:
      ctx.buffer(batch.validity);
      ctx.buffer(batch.values);
      ctx.variadic(batch.data.length);
      batch.data.forEach((b) => ctx.buffer(b));
      return;
    // validity, offset, and list child
    case Type.List:
    case Type.LargeList:
    case Type.Map:
      ctx.buffer(batch.validity);
      ctx.buffer(batch.offsets);
      ctx.children(type, batch);
      return;
    // validity, offset, size, and list child
    case Type.ListView:
    case Type.LargeListView:
      ctx.buffer(batch.validity);
      ctx.buffer(batch.offsets);
      ctx.buffer(batch.sizes);
      ctx.children(type, batch);
      return;
    // validity and children
    case Type.FixedSizeList:
    case Type.Struct:
      ctx.buffer(batch.validity);
      ctx.children(type, batch);
      return;
    // children only
    case Type.RunEndEncoded:
      ctx.children(type, batch);
      return;
    // union
    case Type.Union: {
      ctx.buffer(batch.typeIds);
      if (type.mode === UnionMode.Dense) {
        ctx.buffer(batch.offsets);
      }
      ctx.children(type, batch);
      return;
    }
    // unsupported type
    default:
      throw new Error(invalidDataType(typeId));
  }
}
function buffer(arrayType2) {
  return new Buffer2(arrayType2);
}
class Buffer2 {
  /**
   * Create a new resizable buffer instance.
   * @param {TypedArrayConstructor} arrayType
   */
  constructor(arrayType2 = uint8Array) {
    this.buf = new arrayType2(512);
  }
  /**
   * Return the underlying data as a 64-bit aligned array of minimum size.
   * @param {number} size The desired minimum array size.
   * @returns {TypedArray} The 64-bit aligned array.
   */
  array(size) {
    return align(this.buf, size);
  }
  /**
   * Prepare for writes to the given index, resizing as necessary.
   * @param {number} index The array index to prepare to write to.
   */
  prep(index) {
    if (index >= this.buf.length) {
      this.buf = grow(this.buf, index);
    }
  }
  /**
   * Return the value at the given index.
   * @param {number} index The array index.
   */
  get(index) {
    return this.buf[index];
  }
  /**
   * Set a value at the given index.
   * @param {number | bigint} value The value to set.
   * @param {number} index The index to write to.
   */
  set(value2, index) {
    this.prep(index);
    this.buf[index] = value2;
  }
  /**
   * Write a byte array at the given index. The method should be called
   * only when the underlying buffer is of type Uint8Array.
   * @param {Uint8Array} bytes The byte array.
   * @param {number} index The starting index to write to.
   */
  write(bytes, index) {
    this.prep(index + bytes.length);
    this.buf.set(bytes, index);
  }
}
function bitmap() {
  return new Bitmap();
}
class Bitmap extends Buffer2 {
  /**
   * Set a bit to true at the given bitmap index.
   * @param {number} index The index to write to.
   */
  set(index) {
    const i = index >> 3;
    this.prep(i);
    this.buf[i] |= 1 << index % 8;
  }
}
class BatchBuilder {
  constructor(type, ctx) {
    this.type = type;
    this.ctx = ctx;
    this.batchClass = ctx.batchType(type);
  }
  /**
   * Initialize the builder state.
   * @returns {this} This builder.
   */
  init() {
    this.index = -1;
    return this;
  }
  /**
   * Write a value to the builder.
   * @param {*} value
   * @param {number} index
   * @returns {boolean | void}
   */
  set(value2, index) {
    this.index = index;
    return false;
  }
  /**
   * Returns a batch constructor options object.
   * Used internally to marshal batch data.
   * @returns {Record<string, any>}
   */
  done() {
    return null;
  }
  /**
   * Returns a completed batch and reinitializes the builder state.
   * @returns {Batch}
   */
  batch() {
    const b = new this.batchClass(this.done());
    this.init();
    return b;
  }
}
class ValidityBuilder extends BatchBuilder {
  constructor(type, ctx) {
    super(type, ctx);
  }
  init() {
    this.nullCount = 0;
    this.validity = bitmap();
    return super.init();
  }
  /**
   * @param {*} value
   * @param {number} index
   * @returns {boolean | void}
   */
  set(value2, index) {
    this.index = index;
    const isValid2 = value2 != null;
    if (isValid2) {
      this.validity.set(index);
    } else {
      this.nullCount++;
    }
    return isValid2;
  }
  done() {
    const { index, nullCount, type, validity } = this;
    return {
      length: index + 1,
      nullCount,
      type,
      validity: nullCount ? validity.array((index >> 3) + 1) : new uint8Array(0)
    };
  }
}
function dictionaryContext() {
  const idMap = /* @__PURE__ */ new Map();
  const dicts = /* @__PURE__ */ new Set();
  return {
    /**
     * Get a dictionary values builder for the given dictionary type.
     * @param {DictionaryType} type
     *  The dictionary type.
     * @param {*} ctx The builder context.
     * @returns {ReturnType<dictionaryValues>}
     */
    get(type, ctx) {
      const id = type.id;
      if (id >= 0 && idMap.has(id)) {
        return idMap.get(id);
      } else {
        const dict = dictionaryValues(type, ctx);
        if (id >= 0) idMap.set(id, dict);
        dicts.add(dict);
        return dict;
      }
    },
    /**
     * Finish building dictionary values columns and assign them to
     * their corresponding dictionary batches.
     * @param {ExtractionOptions} options
     */
    finish(options) {
      dicts.forEach((dict) => dict.finish(options));
    }
  };
}
function dictionaryValues(type, ctx) {
  const keys2 = /* @__PURE__ */ Object.create(null);
  const values2 = ctx.builder(type.dictionary);
  const batches = [];
  values2.init();
  let index = -1;
  return {
    type,
    values: values2,
    add(batch) {
      batches.push(batch);
      return batch;
    },
    key(value2) {
      const v = keyString(value2);
      let k = keys2[v];
      if (k === void 0) {
        keys2[v] = k = ++index;
        values2.set(value2, k);
      }
      return k;
    },
    finish(options) {
      const valueType = type.dictionary;
      const batch = new (batchType(valueType, options))(values2.done());
      const dictionary2 = new Column([batch]);
      batches.forEach((batch2) => batch2.setDictionary(dictionary2));
    }
  };
}
class DictionaryBuilder extends ValidityBuilder {
  constructor(type, ctx) {
    super(type, ctx);
    this.dict = ctx.dictionary(type);
  }
  init() {
    this.values = buffer(this.type.indices.values);
    return super.init();
  }
  set(value2, index) {
    if (super.set(value2, index)) {
      this.values.set(this.dict.key(value2), index);
    }
  }
  done() {
    return {
      ...super.done(),
      values: this.values.array(this.index + 1)
    };
  }
  batch() {
    return this.dict.add(super.batch());
  }
}
function inferType$1(visit2) {
  const profile = profiler();
  visit2((value2) => profile.add(value2));
  return profile.type();
}
function profiler() {
  let length2 = 0;
  let nullCount = 0;
  let boolCount = 0;
  let numberCount = 0;
  let intCount = 0;
  let bigintCount = 0;
  let dateCount = 0;
  let dayCount = 0;
  let stringCount = 0;
  let arrayCount = 0;
  let structCount = 0;
  let min2 = Infinity;
  let max2 = -Infinity;
  let minLength = Infinity;
  let maxLength = -Infinity;
  let minBigInt;
  let maxBigInt;
  let arrayProfile;
  let structProfiles = {};
  return {
    add(value2) {
      length2++;
      if (value2 == null) {
        nullCount++;
        return;
      }
      switch (typeof value2) {
        case "string":
          stringCount++;
          break;
        case "number":
          numberCount++;
          if (value2 < min2) min2 = value2;
          if (value2 > max2) max2 = value2;
          if (Number.isInteger(value2)) intCount++;
          break;
        case "bigint":
          bigintCount++;
          if (minBigInt === void 0) {
            minBigInt = maxBigInt = value2;
          } else {
            if (value2 < minBigInt) minBigInt = value2;
            if (value2 > maxBigInt) maxBigInt = value2;
          }
          break;
        case "boolean":
          boolCount++;
          break;
        case "object":
          if (value2 instanceof Date) {
            dateCount++;
            if (+value2 % 864e5 === 0) dayCount++;
          } else if (isArray(value2)) {
            arrayCount++;
            const len = value2.length;
            if (len < minLength) minLength = len;
            if (len > maxLength) maxLength = len;
            arrayProfile ??= profiler();
            value2.forEach(arrayProfile.add);
          } else {
            structCount++;
            for (const key2 in value2) {
              const fieldProfiler = structProfiles[key2] ?? (structProfiles[key2] = profiler());
              fieldProfiler.add(value2[key2]);
            }
          }
      }
    },
    type() {
      const valid = length2 - nullCount;
      return valid === 0 ? nullType() : intCount === valid ? intType(min2, max2) : numberCount === valid ? float64() : bigintCount === valid ? bigintType(minBigInt, maxBigInt) : boolCount === valid ? bool() : dayCount === valid ? dateDay() : dateCount === valid ? timestamp() : stringCount === valid ? dictionary$1(utf8()) : arrayCount === valid ? arrayType(arrayProfile.type(), minLength, maxLength) : structCount === valid ? struct(
        Object.entries(structProfiles).map((_) => field(_[0], _[1].type()))
      ) : unionType();
    }
  };
}
function arrayType(type, minLength, maxLength) {
  return maxLength === minLength ? fixedSizeList(type, minLength) : list(type);
}
function intType(min2, max2) {
  const v = Math.max(Math.abs(min2) - 1, max2);
  return v < 1 << 7 ? int8() : v < 1 << 15 ? int16() : v < 2 ** 31 ? int32() : float64();
}
function bigintType(min2, max2) {
  const v = -min2 > max2 ? -min2 - 1n : max2;
  if (v >= 2 ** 63) {
    throw new Error(`BigInt exceeds 64 bits: ${v}`);
  }
  return int64();
}
function unionType() {
  throw new Error("Mixed types detected, please define a union type.");
}
class BinaryBuilder extends ValidityBuilder {
  constructor(type, ctx) {
    super(type, ctx);
    this.toOffset = toOffset(type.offsets);
  }
  init() {
    this.offsets = buffer(this.type.offsets);
    this.values = buffer();
    this.pos = 0;
    return super.init();
  }
  set(value2, index) {
    const { offsets, values: values2, toOffset: toOffset2 } = this;
    if (super.set(value2, index)) {
      values2.write(value2, this.pos);
      this.pos += value2.length;
    }
    offsets.set(toOffset2(this.pos), index + 1);
  }
  done() {
    return {
      ...super.done(),
      offsets: this.offsets.array(this.index + 2),
      values: this.values.array(this.pos + 1)
    };
  }
}
class BoolBuilder extends ValidityBuilder {
  constructor(type, ctx) {
    super(type, ctx);
  }
  init() {
    this.values = bitmap();
    return super.init();
  }
  set(value2, index) {
    super.set(value2, index);
    if (value2) this.values.set(index);
  }
  done() {
    return {
      ...super.done(),
      values: this.values.array((this.index >> 3) + 1)
    };
  }
}
class DecimalBuilder extends ValidityBuilder {
  constructor(type, ctx) {
    super(type, ctx);
    this.scale = 10 ** type.scale;
    this.stride = type.bitWidth >> 6;
  }
  init() {
    this.values = buffer(this.type.values);
    return super.init();
  }
  set(value2, index) {
    const { scale, stride, values: values2 } = this;
    if (super.set(value2, index)) {
      values2.prep((index + 1) * stride);
      toDecimal(value2, values2.buf, index * stride, stride, scale);
    }
  }
  done() {
    const { index, stride, values: values2 } = this;
    return {
      ...super.done(),
      values: values2.array((index + 1) * stride)
    };
  }
}
class FixedSizeBinaryBuilder extends ValidityBuilder {
  constructor(type, ctx) {
    super(type, ctx);
    this.stride = type.stride;
  }
  init() {
    this.values = buffer();
    return super.init();
  }
  set(value2, index) {
    if (super.set(value2, index)) {
      this.values.write(value2, index * this.stride);
    }
  }
  done() {
    const { stride, values: values2 } = this;
    return {
      ...super.done(),
      values: values2.array(stride * (this.index + 1))
    };
  }
}
class FixedSizeListBuilder extends ValidityBuilder {
  constructor(type, ctx) {
    super(type, ctx);
    this.child = ctx.builder(this.type.children[0].type);
    this.stride = type.stride;
  }
  init() {
    this.child.init();
    return super.init();
  }
  set(value2, index) {
    const { child, stride } = this;
    const base = index * stride;
    if (super.set(value2, index)) {
      for (let i = 0; i < stride; ++i) {
        child.set(value2[i], base + i);
      }
    } else {
      child.index = base + stride;
    }
  }
  done() {
    const { child } = this;
    return {
      ...super.done(),
      children: [child.batch()]
    };
  }
}
class IntervalDayTimeBuilder extends ValidityBuilder {
  init() {
    this.values = buffer(this.type.values);
    return super.init();
  }
  set(value2, index) {
    if (super.set(value2, index)) {
      const i = index << 1;
      this.values.set(value2[0], i);
      this.values.set(value2[1], i + 1);
    }
  }
  done() {
    return {
      ...super.done(),
      values: this.values.array(this.index + 1 << 1)
    };
  }
}
class IntervalMonthDayNanoBuilder extends ValidityBuilder {
  init() {
    this.values = buffer();
    return super.init();
  }
  set(value2, index) {
    if (super.set(value2, index)) {
      this.values.write(toMonthDayNanoBytes(value2), index << 4);
    }
  }
  done() {
    return {
      ...super.done(),
      values: this.values.array(this.index + 1 << 4)
    };
  }
}
class AbstractListBuilder extends ValidityBuilder {
  constructor(type, ctx, child) {
    super(type, ctx);
    this.child = child;
  }
  init() {
    this.child.init();
    const offsetType = this.type.offsets;
    this.offsets = buffer(offsetType);
    this.toOffset = toOffset(offsetType);
    this.pos = 0;
    return super.init();
  }
  done() {
    return {
      ...super.done(),
      offsets: this.offsets.array(this.index + 2),
      children: [this.child.batch()]
    };
  }
}
class ListBuilder extends AbstractListBuilder {
  constructor(type, ctx) {
    super(type, ctx, ctx.builder(type.children[0].type));
  }
  set(value2, index) {
    const { child, offsets, toOffset: toOffset2 } = this;
    if (super.set(value2, index)) {
      value2.forEach((v) => child.set(v, this.pos++));
    }
    offsets.set(toOffset2(this.pos), index + 1);
  }
}
class AbstractStructBuilder extends ValidityBuilder {
  constructor(type, ctx) {
    super(type, ctx);
    this.children = type.children.map((c) => ctx.builder(c.type));
  }
  init() {
    this.children.forEach((c) => c.init());
    return super.init();
  }
  done() {
    const { children } = this;
    children.forEach((c) => c.index = this.index);
    return {
      ...super.done(),
      children: children.map((c) => c.batch())
    };
  }
}
class StructBuilder extends AbstractStructBuilder {
  constructor(type, ctx) {
    super(type, ctx);
    this.setters = this.children.map((child, i) => {
      const name2 = type.children[i].name;
      return (value2, index) => child.set(value2?.[name2], index);
    });
  }
  set(value2, index) {
    super.set(value2, index);
    const setters = this.setters;
    for (let i = 0; i < setters.length; ++i) {
      setters[i](value2, index);
    }
  }
}
class MapBuilder extends AbstractListBuilder {
  constructor(type, ctx) {
    super(type, ctx, new MapStructBuilder(type.children[0].type, ctx));
  }
  set(value2, index) {
    const { child, offsets, toOffset: toOffset2 } = this;
    if (super.set(value2, index)) {
      for (const keyValuePair of value2) {
        child.set(keyValuePair, this.pos++);
      }
    }
    offsets.set(toOffset2(this.pos), index + 1);
  }
}
class MapStructBuilder extends AbstractStructBuilder {
  set(value2, index) {
    super.set(value2, index);
    const [key2, val] = this.children;
    key2.set(value2[0], index);
    val.set(value2[1], index);
  }
}
const NO_VALUE = {};
class RunEndEncodedBuilder extends BatchBuilder {
  constructor(type, ctx) {
    super(type, ctx);
    this.children = type.children.map((c) => ctx.builder(c.type));
  }
  init() {
    this.pos = 0;
    this.key = null;
    this.value = NO_VALUE;
    this.children.forEach((c) => c.init());
    return super.init();
  }
  next() {
    const [runs, vals] = this.children;
    runs.set(this.index + 1, this.pos);
    vals.set(this.value, this.pos++);
  }
  set(value2, index) {
    if (value2 !== this.value) {
      const key2 = keyString(value2);
      if (key2 !== this.key) {
        if (this.key) this.next();
        this.key = key2;
        this.value = value2;
      }
    }
    this.index = index;
  }
  done() {
    this.next();
    const { children, index, type } = this;
    return {
      length: index + 1,
      nullCount: 0,
      type,
      children: children.map((c) => c.batch())
    };
  }
}
class AbstractUnionBuilder extends BatchBuilder {
  constructor(type, ctx) {
    super(type, ctx);
    this.children = type.children.map((c) => ctx.builder(c.type));
    this.typeMap = type.typeMap;
    this.lookup = type.typeIdForValue;
  }
  init() {
    this.nullCount = 0;
    this.typeIds = buffer(int8Array);
    this.children.forEach((c) => c.init());
    return super.init();
  }
  set(value2, index) {
    const { children, lookup: lookup2, typeMap, typeIds } = this;
    this.index = index;
    const typeId = lookup2(value2, index);
    const child = children[typeMap[typeId]];
    typeIds.set(typeId, index);
    if (value2 == null) ++this.nullCount;
    this.update(value2, index, child);
  }
  done() {
    const { children, nullCount, type, typeIds } = this;
    const length2 = this.index + 1;
    return {
      length: length2,
      nullCount,
      type,
      typeIds: typeIds.array(length2),
      children: children.map((c) => c.batch())
    };
  }
}
class SparseUnionBuilder extends AbstractUnionBuilder {
  update(value2, index, child) {
    child.set(value2, index);
    this.children.forEach((c) => {
      if (c !== child) c.set(null, index);
    });
  }
}
class DenseUnionBuilder extends AbstractUnionBuilder {
  init() {
    this.offsets = buffer(this.type.offsets);
    return super.init();
  }
  update(value2, index, child) {
    const offset2 = child.index + 1;
    child.set(value2, offset2);
    this.offsets.set(offset2, index);
  }
  done() {
    return {
      ...super.done(),
      offsets: this.offsets.array(this.index + 1)
    };
  }
}
class Utf8Builder extends BinaryBuilder {
  set(value2, index) {
    super.set(value2 && encodeUtf8(value2), index);
  }
}
class DirectBuilder extends ValidityBuilder {
  constructor(type, ctx) {
    super(type, ctx);
    this.values = buffer(type.values);
  }
  init() {
    this.values = buffer(this.type.values);
    return super.init();
  }
  /**
   * @param {*} value
   * @param {number} index
   * @returns {boolean | void}
   */
  set(value2, index) {
    if (super.set(value2, index)) {
      this.values.set(value2, index);
    }
  }
  done() {
    return {
      ...super.done(),
      values: this.values.array(this.index + 1)
    };
  }
}
class Int64Builder extends DirectBuilder {
  set(value2, index) {
    super.set(value2 == null ? value2 : toBigInt(value2), index);
  }
}
class TransformBuilder extends DirectBuilder {
  constructor(type, ctx, transform) {
    super(type, ctx);
    this.transform = transform;
  }
  set(value2, index) {
    super.set(value2 == null ? value2 : this.transform(value2), index);
  }
}
function builderContext(options = {}, dictionaries = dictionaryContext()) {
  return {
    batchType: (type) => batchType(type, options),
    builder(type) {
      return builder(type, this);
    },
    dictionary(type) {
      return dictionaries.get(type, this);
    },
    finish: () => dictionaries.finish(options)
  };
}
function builder(type, ctx = builderContext()) {
  const { typeId } = type;
  switch (typeId) {
    case Type.Int:
    case Type.Time:
    case Type.Duration:
      return isInt64ArrayType(type.values) ? new Int64Builder(type, ctx) : new DirectBuilder(type, ctx);
    case Type.Float:
      return type.precision ? new DirectBuilder(type, ctx) : new TransformBuilder(type, ctx, toFloat16);
    case Type.Binary:
    case Type.LargeBinary:
      return new BinaryBuilder(type, ctx);
    case Type.Utf8:
    case Type.LargeUtf8:
      return new Utf8Builder(type, ctx);
    case Type.Bool:
      return new BoolBuilder(type, ctx);
    case Type.Decimal:
      return type.bitWidth === 32 ? new TransformBuilder(type, ctx, toDecimal32(type.scale)) : new DecimalBuilder(type, ctx);
    case Type.Date:
      return new TransformBuilder(type, ctx, type.unit ? toBigInt : toDateDay);
    case Type.Timestamp:
      return new TransformBuilder(type, ctx, toTimestamp(type.unit));
    case Type.Interval:
      switch (type.unit) {
        case IntervalUnit.DAY_TIME:
          return new IntervalDayTimeBuilder(type, ctx);
        case IntervalUnit.MONTH_DAY_NANO:
          return new IntervalMonthDayNanoBuilder(type, ctx);
      }
      return new DirectBuilder(type, ctx);
    case Type.List:
    case Type.LargeList:
      return new ListBuilder(type, ctx);
    case Type.Struct:
      return new StructBuilder(type, ctx);
    case Type.Union:
      return type.mode ? new DenseUnionBuilder(type, ctx) : new SparseUnionBuilder(type, ctx);
    case Type.FixedSizeBinary:
      return new FixedSizeBinaryBuilder(type, ctx);
    case Type.FixedSizeList:
      return new FixedSizeListBuilder(type, ctx);
    case Type.Map:
      return new MapBuilder(type, ctx);
    case Type.RunEndEncoded:
      return new RunEndEncodedBuilder(type, ctx);
    case Type.Dictionary:
      return new DictionaryBuilder(type, ctx);
  }
  throw new Error(invalidDataType(typeId));
}
function columnFromValues(values2, type, options = {}, dicts) {
  const visit2 = isIterable(values2) ? (callback) => {
    for (const value2 of values2) callback(value2);
  } : values2;
  type ??= inferType$1(visit2);
  const { maxBatchRows = Infinity, ...opt2 } = options;
  let data2;
  if (type.typeId === Type.Null) {
    let length2 = 0;
    visit2(() => ++length2);
    data2 = nullBatches(type, length2, maxBatchRows);
  } else {
    const ctx = builderContext(opt2, dicts);
    const b = builder(type, ctx).init();
    const next = (b2) => data2.push(b2.batch());
    data2 = [];
    let row = 0;
    visit2((value2) => {
      b.set(value2, row++);
      if (row >= maxBatchRows) {
        next(b);
        row = 0;
      }
    });
    if (row) next(b);
    ctx.finish();
  }
  return new Column(data2, type);
}
function nullBatches(type, length2, limit) {
  const data2 = [];
  const batch = (length3) => new NullBatch({ length: length3, nullCount: length3, type });
  const numBatches = Math.floor(length2 / limit);
  for (let i = 0; i < numBatches; ++i) {
    data2.push(batch(limit));
  }
  const rem = length2 % limit;
  if (rem) data2.push(batch(rem));
  return data2;
}
function columnFromArray(array2, type, options = {}, dicts) {
  return !type && isTypedArray(array2) ? columnFromTypedArray(array2, options) : columnFromValues((v) => array2.forEach(v), type, options, dicts);
}
function columnFromTypedArray(values2, { maxBatchRows, useBigInt }) {
  const arrayType2 = (
    /** @type {TypedArrayConstructor} */
    values2.constructor
  );
  const type = typeForTypedArray(arrayType2);
  const length2 = values2.length;
  const limit = Math.min(maxBatchRows || Infinity, length2);
  const numBatches = Math.floor(length2 / limit);
  const batches = [];
  const batchType2 = isInt64ArrayType(arrayType2) && !useBigInt ? Int64Batch : DirectBatch;
  const add = (start, end) => batches.push(new batchType2({
    length: end - start,
    nullCount: 0,
    type,
    validity: new uint8Array(0),
    values: values2.subarray(start, end)
  }));
  let idx = 0;
  for (let i = 0; i < numBatches; ++i) add(idx, idx += limit);
  if (idx < length2) add(idx, length2);
  return new Column(batches);
}
function typeForTypedArray(arrayType2) {
  switch (arrayType2) {
    case float32Array:
      return float32();
    case float64Array:
      return float64();
    case int8Array:
      return int8();
    case int16Array:
      return int16();
    case int32Array:
      return int32();
    case int64Array:
      return int64();
    case uint8Array:
      return uint8();
    case uint16Array:
      return uint16();
    case uint32Array:
      return uint32();
    case uint64Array:
      return uint64();
  }
}
function tableFromColumns(data2, useProxy) {
  const fields = [];
  const entries2 = Array.isArray(data2) ? data2 : Object.entries(data2);
  const length2 = entries2[0]?.[1].length;
  const columns2 = entries2.map(([name2, col]) => {
    if (col.length !== length2) {
      throw new Error("All columns must have the same length.");
    }
    fields.push(field(name2, col.type));
    return col;
  });
  const schema = {
    version: Version.V5,
    endianness: Endianness.Little,
    fields,
    metadata: null
  };
  return new Table3(schema, columns2, useProxy);
}
function columns(table2, names) {
  return isFunction(names) ? names(table2) : names || table2.columnNames();
}
function toArrow(table2, options = {}) {
  const { columns: columns$1, limit = Infinity, offset: offset2 = 0, types: types2 = {}, ...opt2 } = options;
  const names = columns(table2, columns$1);
  const data2 = table2.data();
  const fullScan = offset2 === 0 && table2.numRows() <= limit && !table2.isFiltered() && !table2.isOrdered();
  return tableFromColumns(names.map((name2) => {
    const values2 = data2[name2];
    const type = types2[name2];
    const isArray2 = isArrayType(values2);
    let col;
    if (fullScan && (isArray2 || isFunction(values2.toArray))) {
      col = columnFromArray(isArray2 ? values2 : values2.toArray(), type, opt2);
    } else {
      const get2 = isArray2 ? (row) => values2[row] : (row) => values2.at(row);
      col = columnFromValues(
        (visit2) => table2.scan((row) => visit2(get2(row)), true, limit, offset2),
        type,
        opt2
      );
    }
    return [name2, col];
  }));
}
function toArrowIPC(data2, options = {}) {
  const { format = "stream", ...toArrowOptions } = options;
  return tableToIPC(toArrow(data2, toArrowOptions), { format });
}
function identity(x) {
  return x;
}
function scan(table2, names, limit = 100, offset2, ctx) {
  const { start = identity, cell, end = identity } = ctx;
  const data2 = table2.data();
  const n = names.length;
  table2.scan((row) => {
    start(row);
    for (let i = 0; i < n; ++i) {
      const name2 = names[i];
      cell(data2[name2].at(row), name2, i);
    }
    end(row);
  }, true, limit, offset2);
}
function toCSV(table2, options = {}) {
  const names = columns(table2, options.columns);
  const format = options.format || {};
  const delim = options.delimiter || ",";
  const header = options.header ?? true;
  const reFormat = new RegExp(`["${delim}
\r]`);
  const formatValue2 = (value2) => value2 == null ? "" : isDate$1(value2) ? formatUTCDate(value2, true) : reFormat.test(value2 += "") ? '"' + value2.replace(/"/g, '""') + '"' : value2;
  const vals = names.map(formatValue2);
  let text = header ? vals.join(delim) + "\n" : "";
  scan(table2, names, options.limit || Infinity, options.offset, {
    cell(value2, name2, index) {
      vals[index] = formatValue2(format[name2] ? format[name2](value2) : value2);
    },
    end() {
      text += vals.join(delim) + "\n";
    }
  });
  return text;
}
function mapObject(obj, fn, output2 = {}) {
  for (const key2 in obj) {
    output2[key2] = fn(obj[key2], key2);
  }
  return output2;
}
function isExactDateUTC(d) {
  return d.getUTCHours() === 0 && d.getUTCMinutes() === 0 && d.getUTCSeconds() === 0 && d.getUTCMilliseconds() === 0;
}
function inferFormat(scan2, options = {}) {
  let count2 = 0;
  let nulls = 0;
  let dates = 0;
  let dutcs = 0;
  let nums = 0;
  let digits = 0;
  scan2((value2) => {
    ++count2;
    if (value2 == null) {
      ++nulls;
      return;
    }
    const type = typeof value2;
    if (type === "object" && isDate$1(value2)) {
      ++dates;
      if (isExactDateUTC(value2)) ++dutcs;
    } else if (type === "number") {
      ++nums;
      if (value2 === value2 && (value2 | 0) !== value2) {
        const s = value2 + "";
        const p = s.indexOf(".");
        if (p >= 0) {
          const e = s.indexOf("e");
          const l = e > 0 ? e : s.length;
          digits = Math.max(digits, l - p - 1);
        }
      }
    }
  });
  return {
    align: (nulls + nums + dates) / count2 > 0.5 ? "r" : "l",
    format: {
      utc: dates === dutcs,
      digits: Math.min(digits, options.maxdigits || 6)
    }
  };
}
function formats(table2, names, options) {
  const formatOpt = options.format || {};
  const alignOpt = options.align || {};
  const format = {};
  const align2 = {};
  names.forEach((name2) => {
    const auto = inferFormat(values(table2, name2), options);
    align2[name2] = alignOpt[name2] || auto.align;
    format[name2] = formatOpt[name2] || auto.format;
  });
  return { align: align2, format };
}
function values(table2, columnName) {
  const column = table2.column(columnName);
  return (fn) => table2.scan((row) => fn(column.at(row)));
}
function formatValue(v, options = {}) {
  if (isFunction(options)) {
    return options(v) + "";
  }
  const type = typeof v;
  if (type === "object") {
    if (isDate$1(v)) {
      return options.utc ? formatUTCDate(v) : formatDate(v);
    } else {
      const s = JSON.stringify(
        v,
        // @ts-ignore
        (k, v2) => isTypedArray$1(v2) ? Array.from(v2) : v2
      );
      const maxlen = options.maxlen || 30;
      return s.length > maxlen ? s.slice(0, 28) + "…" + (s[0] === "[" ? "]" : "}") : s;
    }
  } else if (type === "number") {
    const digits = options.digits || 0;
    let a;
    return v !== 0 && ((a = Math.abs(v)) >= 1e18 || a < Math.pow(10, -digits)) ? v.toExponential(digits) : v.toFixed(digits);
  } else {
    return v + "";
  }
}
function toHTML(table2, options = {}) {
  const names = columns(table2, options.columns);
  const { align: align2, format } = formats(table2, names, options);
  const style = styles$2(options);
  const nullish = options.null;
  const alignValue = (a) => a === "c" ? "center" : a === "r" ? "right" : "left";
  const escape2 = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const baseFormat = (value2, opt2) => escape2(formatValue(value2, opt2));
  const formatter = nullish ? (value2, opt2) => value2 == null ? nullish(value2) : baseFormat(value2, opt2) : baseFormat;
  let r = -1;
  let idx = -1;
  const tag = (tag2, name2, shouldAlign) => {
    const a = shouldAlign ? alignValue(align2[name2]) : "";
    const s = style[tag2] ? style[tag2](name2, idx, r) || "" : "";
    const css = (a ? `text-align: ${a};` + (s ? " " : "") : "") + s;
    return `<${tag2}${css ? ` style="${css}"` : ""}>`;
  };
  let text = tag("table") + tag("thead") + tag("tr", r) + names.map((name2) => `${tag("th", name2, 1)}${name2}</th>`).join("") + "</tr></thead>" + tag("tbody");
  scan(table2, names, options.limit, options.offset, {
    start(row) {
      r = row;
      ++idx;
      text += tag("tr");
    },
    cell(value2, name2) {
      text += tag("td", name2, 1) + formatter(value2, format[name2]) + "</td>";
    },
    end() {
      text += "</tr>";
    }
  });
  return text + "</tbody></table>";
}
function styles$2(options) {
  return mapObject(
    options.style,
    (value2) => isFunction(value2) ? value2 : () => value2
  );
}
const COLUMNS = "columns";
const NDJSON = "ndjson";
const defaultFormatter = (value2) => isDate$1(value2) ? formatUTCDate(value2, true) : value2;
function toJSON(table2, {
  type,
  columns: cols,
  format = {},
  limit,
  offset: offset2
} = {}) {
  const names = columns(table2, cols);
  const fmt = names.map((name2) => format[name2] || defaultFormatter);
  const scan2 = (fn) => table2.scan(fn, true, limit, offset2);
  return type === COLUMNS ? toColumns(table2, names, fmt, scan2) : toRows(table2, names, fmt, scan2, type === NDJSON);
}
function toColumns(table2, names, format, scan2) {
  let text = "{";
  names.forEach((name2, i) => {
    text += (i ? "," : "") + JSON.stringify(name2) + ":[";
    const column = table2.column(name2);
    const formatter = format[i];
    let r = -1;
    scan2((row) => {
      const value2 = column.at(row);
      text += (++r ? "," : "") + JSON.stringify(formatter(value2));
    });
    text += "]";
  });
  return text + "}";
}
function toRows(table2, names, format, scan2, nd = false) {
  const n = names.length;
  const keys2 = names.map((name2) => `"${name2}":`);
  const cols = names.map((name2) => table2.column(name2));
  const finish = nd ? (o) => o.replaceAll("\n", "") : identity;
  const sep = nd ? "\n" : ",";
  let text = nd ? "" : "[";
  let r = -1;
  scan2((row) => {
    const props = [];
    for (let i = 0; i < n; ++i) {
      props.push(keys2[i] + JSON.stringify(format[i](cols[i].at(row))));
    }
    text += (++r ? sep : "") + finish(`{${props.join(",")}}`);
  });
  return text + (nd ? "" : "]");
}
function toMarkdown(table2, options = {}) {
  const names = columns(table2, options.columns);
  const { align: align2, format } = formats(table2, names, options);
  const alignValue = (a) => a === "c" ? ":-:" : a === "r" ? "-:" : ":-";
  const escape2 = (s) => s.replace(/\|/g, "\\|");
  let text = "|" + names.map(escape2).join("|") + "|\n|" + names.map((name2) => alignValue(align2[name2])).join("|") + "|\n";
  scan(table2, names, options.limit, options.offset, {
    start() {
      text += "|";
    },
    cell(value2, name2) {
      text += escape2(formatValue(value2, format[name2])) + "|";
    },
    end() {
      text += "\n";
    }
  });
  return text;
}
class ColumnTable extends Table$1 {
  /**
   * Create a new table with additional columns drawn from one or more input
   * tables. All tables must have the same numer of rows and are reified
   * prior to assignment. In the case of repeated column names, input table
   * columns overwrite existing columns.
   * @param {...(Table|import('./types.js').ColumnData)} tables
   *  The tables to merge with this table.
   * @return {this} A new table with merged columns.
   * @example table.assign(table1, table2)
   */
  assign(...tables) {
    return assign(this, ...tables);
  }
  /**
   * Count the number of values in a group. This method is a shorthand
   * for *rollup* with a count aggregate function.
   * @param {import('./types.js').CountOptions} [options]
   *  Options for the count.
   * @return {this} A new table with groupby and count columns.
   * @example table.groupby('colA').count()
   * @example table.groupby('colA').count({ as: 'num' })
   */
  count(options = {}) {
    const { as = "count" } = options;
    return rollup(this, { [as]: count() });
  }
  /**
   * Derive new column values based on the provided expressions. By default,
   * new columns are added after (higher indices than) existing columns. Use
   * the before or after options to place new columns elsewhere.
   * @param {import('./types.js').ExprObject} values
   *  Object of name-value pairs defining the columns to derive. The input
   *  object should have output column names for keys and table expressions
   *  for values.
   * @param {import('./types.js').DeriveOptions} [options]
   *  Options for dropping or relocating derived columns. Use either a before
   *  or after property to indicate where to place derived columns. Specifying
   *  both before and after is an error. Unlike the *relocate* verb, this
   *  option affects only new columns; updated columns with existing names
   *  are excluded from relocation.
   * @return {this} A new table with derived columns added.
   * @example table.derive({ sumXY: d => d.x + d.y })
   * @example table.derive({ z: d => d.x * d.y }, { before: 'x' })
   */
  derive(values2, options) {
    return derive(this, values2, options);
  }
  /**
   * Filter a table to a subset of rows based on the input criteria.
   * The resulting table provides a filtered view over the original data; no
   * data copy is made. To create a table that copies only filtered data to
   * new data structures, call *reify* on the output table.
   * @param {import('./types.js').TableExpr} criteria
   *  Filter criteria as a table expression. Both aggregate and window
   *  functions are permitted, taking into account *groupby* or *orderby*
   *  settings.
   * @return {this} A new table with filtered rows.
   * @example table.filter(d => abs(d.value) < 5)
   */
  filter(criteria) {
    return filter(this, criteria);
  }
  /**
   * Extract rows with indices from start to end (end not included), where
   * start and end represent per-group ordered row numbers in the table.
   * @param {number} [start] Zero-based index at which to start extraction.
   *  A negative index indicates an offset from the end of the group.
   *  If start is undefined, slice starts from the index 0.
   * @param {number} [end] Zero-based index before which to end extraction.
   *  A negative index indicates an offset from the end of the group.
   *  If end is omitted, slice extracts through the end of the group.
   * @return {this} A new table with sliced rows.
   * @example table.slice(1, -1)
   */
  slice(start, end) {
    return slice(this, start, end);
  }
  /**
   * Group table rows based on a set of column values.
   * Subsequent operations that are sensitive to grouping (such as
   * aggregate functions) will operate over the grouped rows.
   * To undo grouping, use *ungroup*.
   * @param  {...import('./types.js').ExprList} keys
   *  Key column values to group by. The keys may be specified using column
   *  name strings, column index numbers, value objects with output column
   *  names for keys and table expressions for values, or selection helper
   *  functions.
   * @return {this} A new table with grouped rows.
   * @example table.groupby('colA', 'colB')
   * @example table.groupby({ key: d => d.colA + d.colB })
   */
  groupby(...keys2) {
    return groupby(this, ...keys2);
  }
  /**
   * Order table rows based on a set of column values. Subsequent operations
   * sensitive to ordering (such as window functions) will operate over sorted
   * values. The resulting table provides an view over the original data,
   * without any copying. To create a table with sorted data copied to new
   * data strucures, call *reify* on the result of this method. To undo
   * ordering, use *unorder*.
   * @param  {...import('./types.js').OrderKeys} keys
   *  Key values to sort by, in precedence order.
   *  By default, sorting is done in ascending order.
   *  To sort in descending order, wrap values using *desc*.
   *  If a string, order by the column with that name.
   *  If a number, order by the column with that index.
   *  If a function, must be a valid table expression; aggregate functions
   *  are permitted, but window functions are not.
   *  If an object, object values must be valid values parameters
   *  with output column names for keys and table expressions
   *  for values (the output names will be ignored).
   *  If an array, array values must be valid key parameters.
   * @return {this} A new ordered table.
   * @example table.orderby('a', desc('b'))
   * @example table.orderby({ a: 'a', b: desc('b') )})
   * @example table.orderby(desc(d => d.a))
   */
  orderby(...keys2) {
    return orderby(this, ...keys2);
  }
  /**
   * Relocate a subset of columns to change their positions, also
   * potentially renaming them.
   * @param {import('./types.js').Select} columns
   *  An ordered selection of columns to relocate.
   *  The input may consist of column name strings, column integer indices,
   *  rename objects with current column names as keys and new column names
   *  as values, or functions that take a table as input and returns a valid
   *  selection parameter (typically the output of selection helper functions
   *  such as *all*, *not*, or *range*).
   * @param {import('./types.js').RelocateOptions} options
   *  Options for relocating. Must include either the before or after property
   *  to indicate where to place the relocated columns. Specifying both before
   *  and after is an error.
   * @return {this} A new table with relocated columns.
   * @example table.relocate(['colY', 'colZ'], { after: 'colX' })
   * @example table.relocate(not('colB', 'colC'), { before: 'colA' })
   * @example table.relocate({ colA: 'newA', colB: 'newB' }, { after: 'colC' })
   */
  relocate(columns2, options) {
    return relocate(this, toArray(columns2), options);
  }
  /**
   * Rename one or more columns, preserving column order.
   * @param {...import('./types.js').Select} columns
   *  One or more rename objects with current column names as keys and new
   *  column names as values.
   * @return {this} A new table with renamed columns.
   * @example table.rename({ oldName: 'newName' })
   * @example table.rename({ a: 'a2', b: 'b2' })
   */
  rename(...columns2) {
    return rename(this, ...columns2);
  }
  /**
   * Reduce a table, processing all rows to produce a new table.
   * To produce standard aggregate summaries, use the rollup verb.
   * This method allows the use of custom reducer implementations,
   * for example to produce multiple rows for an aggregate.
   * @param {import('../verbs/reduce/reducer.js').Reducer} reducer
   *  The reducer to apply.
   * @return {this} A new table of reducer outputs.
   */
  reduce(reducer) {
    return reduce(this, reducer);
  }
  /**
   * Rollup a table to produce an aggregate summary.
   * Often used in conjunction with *groupby*.
   * To produce counts only, *count* is a shortcut.
   * @param {import('./types.js').ExprObject} [values]
   *  Object of name-value pairs defining aggregate output columns. The input
   *  object should have output column names for keys and table expressions
   *  for values. The expressions must be valid aggregate expressions: window
   *  functions are not allowed and column references must be arguments to
   *  aggregate functions.
   * @return {this} A new table of aggregate summary values.
   * @example table.groupby('colA').rollup({ mean: d => mean(d.colB) })
   * @example table.groupby('colA').rollup({ mean: op.median('colB') })
   */
  rollup(values2) {
    return rollup(this, values2);
  }
  /**
   * Generate a table from a random sample of rows.
   * If the table is grouped, performs a stratified sample by
   * sampling from each group separately.
   * @param {number | import('./types.js').TableExpr} size
   *  The number of samples to draw per group.
   *  If number-valued, the same sample size is used for each group.
   *  If function-valued, the input should be an aggregate table
   *  expression compatible with *rollup*.
   * @param {import('./types.js').SampleOptions} [options]
   *  Options for sampling.
   * @return {this} A new table with sampled rows.
   * @example table.sample(50)
   * @example table.sample(100, { replace: true })
   * @example table.groupby('colA').sample(() => op.floor(0.5 * op.count()))
   */
  sample(size, options) {
    return sample(this, size, options);
  }
  /**
   * Select a subset of columns into a new table, potentially renaming them.
   * @param {...import('./types.js').Select} columns
   *  An ordered selection of columns.
   *  The input may consist of column name strings, column integer indices,
   *  rename objects with current column names as keys and new column names
   *  as values, or functions that take a table as input and returns a valid
   *  selection parameter (typically the output of selection helper functions
   *  such as *all*, *not*, or *range*.).
   * @return {this} A new table of selected columns.
   * @example table.select('colA', 'colB')
   * @example table.select(not('colB', 'colC'))
   * @example table.select({ colA: 'newA', colB: 'newB' })
   */
  select(...columns2) {
    return select(this, ...columns2);
  }
  /**
   * Ungroup a table, removing any grouping criteria.
   * Undoes the effects of *groupby*.
   * @return {this} A new ungrouped table, or this table if not grouped.
   * @example table.ungroup()
   */
  ungroup() {
    return ungroup(this);
  }
  /**
   * Unorder a table, removing any sorting criteria.
   * Undoes the effects of *orderby*.
   * @return {this} A new unordered table, or this table if not ordered.
   * @example table.unorder()
   */
  unorder() {
    return unorder(this);
  }
  // -- Cleaning Verbs ------------------------------------------------------
  /**
   * De-duplicate table rows by removing repeated row values.
   * @param {...import('./types.js').ExprList} keys
   *  Key columns to check for duplicates.
   *  Two rows are considered duplicates if they have matching values for
   *  all keys. If keys are unspecified, all columns are used.
   *  The keys may be specified using column name strings, column index
   *  numbers, value objects with output column names for keys and table
   *  expressions for values, or selection helper functions.
   * @return {this} A new de-duplicated table.
   * @example table.dedupe()
   * @example table.dedupe('a', 'b')
   * @example table.dedupe({ abs: d => op.abs(d.a) })
   */
  dedupe(...keys2) {
    return dedupe(this, ...keys2);
  }
  /**
   * Impute missing values or rows. Accepts a set of column-expression pairs
   * and evaluates the expressions to replace any missing (null, undefined,
   * or NaN) values in the original column.
   * If the expand option is specified, imputes new rows for missing
   * combinations of values. All combinations of key values (a full cross
   * product) are considered for each level of grouping (specified by
   * *groupby*). New rows will be added for any combination
   * of key and groupby values not already contained in the table. For all
   * non-key and non-group columns the new rows are populated with imputation
   * values (first argument) if specified, otherwise undefined.
   * If the expand option is specified, any filter or orderby settings are
   * removed from the output table, but groupby settings persist.
   * @param {import('./types.js').ExprObject} values
   *  Object of name-value pairs for the column values to impute. The input
   *  object should have existing column names for keys and table expressions
   *  for values. The expressions will be evaluated to determine replacements
   *  for any missing values.
   * @param {import('./types.js').ImputeOptions} [options] Imputation options.
   *  The expand property specifies a set of column values to consider for
   *  imputing missing rows. All combinations of expanded values are
   *  considered, and new rows are added for each combination that does not
   *  appear in the input table.
   * @return {this} A new table with imputed values and/or rows.
   * @example table.impute({ v: () => 0 })
   * @example table.impute({ v: d => op.mean(d.v) })
   * @example table.impute({ v: () => 0 }, { expand: ['x', 'y'] })
   */
  impute(values2, options) {
    return impute(this, values2, options);
  }
  // -- Reshaping Verbs -----------------------------------------------------
  /**
   * Fold one or more columns into two key-value pair columns.
   * The fold transform is an inverse of the *pivot* transform.
   * The resulting table has two new columns, one containing the column
   * names (named "key") and the other the column values (named "value").
   * The number of output rows equals the original row count multiplied
   * by the number of folded columns.
   * @param {import('./types.js').ExprList} values The columns to fold.
   *  The columns may be specified using column name strings, column index
   *  numbers, value objects with output column names for keys and table
   *  expressions for values, or selection helper functions.
   * @param {import('./types.js').FoldOptions} [options] Options for folding.
   * @return {this} A new folded table.
   * @example table.fold('colA')
   * @example table.fold(['colA', 'colB'])
   * @example table.fold(range(5, 8))
   */
  fold(values2, options) {
    return fold(this, values2, options);
  }
  /**
   * Pivot columns into a cross-tabulation.
   * The pivot transform is an inverse of the *fold* transform.
   * The resulting table has new columns for each unique combination
   * of the provided *keys*, populated with the provided *values*.
   * The provided *values* must be aggregates, as a single set of keys may
   * include more than one row. If string-valued, the *any* aggregate is used.
   * If only one *values* column is defined, the new pivoted columns will
   * be named using key values directly. Otherwise, input value column names
   * will be included as a component of the output column names.
   * @param {import('./types.js').ExprList} keys
   *  Key values to map to new column names. The keys may be specified using
   *  column name strings, column index numbers, value objects with output
   *  column names for keys and table expressions for values, or selection
   *  helper functions.
   * @param {import('./types.js').ExprList} values Output values for pivoted
   *  columns. Column references will be wrapped in an *any* aggregate. If
   *  object-valued, the input object should have output value names for keys
   *  and aggregate table expressions for values.
   * @param {import('./types.js').PivotOptions} [options]
   *  Options for pivoting.
   * @return {this} A new pivoted table.
   * @example table.pivot('key', 'value')
   * @example table.pivot(['keyA', 'keyB'], ['valueA', 'valueB'])
   * @example table.pivot({ key: d => d.key }, { value: d => op.sum(d.value) })
   */
  pivot(keys2, values2, options) {
    return pivot(this, keys2, values2, options);
  }
  /**
   * Spread array elements into a set of new columns.
   * Output columns are named based on the value key and array index.
   * @param {import('./types.js').ExprList} values
   *  The column values to spread. The values may be specified using column
   *  name strings, column index numbers, value objects with output column
   *  names for keys and table expressions for values, or selection helper
   *  functions.
   * @param {import('./types.js').SpreadOptions } [options]
   *  Options for spreading.
   * @return {this} A new table with the spread columns added.
   * @example table.spread({ a: d => op.split(d.text, '') })
   * @example table.spread('arrayCol', { limit: 100 })
   */
  spread(values2, options) {
    return spread(this, values2, options);
  }
  /**
   * Unroll one or more array-valued columns into new rows.
   * If more than one array value is used, the number of new rows
   * is the smaller of the limit and the largest length.
   * Values for all other columns are copied over.
   * @param {import('./types.js').ExprList} values
   *  The column values to unroll. The values may be specified using column
   *  name strings, column index numbers, value objects with output column
   *  names for keys and table expressions for values, or selection helper
   *  functions.
   * @param {import('./types.js').UnrollOptions} [options]
   *  Options for unrolling.
   * @return {this} A new unrolled table.
   * @example table.unroll('colA', { limit: 1000 })
   */
  unroll(values2, options) {
    return unroll(this, values2, options);
  }
  // -- Joins ---------------------------------------------------------------
  /**
   * Lookup values from a secondary table and add them as new columns.
   * A lookup occurs upon matching key values for rows in both tables.
   * If the secondary table has multiple rows with the same key, only
   * the last observed instance will be considered in the lookup.
   * Lookup is similar to *join_left*, but with a simpler
   * syntax and the added constraint of allowing at most one match only.
   * @param {import('./types.js').TableRef} other
   *  The secondary table to look up values from.
   * @param {import('./types.js').JoinKeys} [on]
   *  Lookup keys (column name strings or table expressions) for this table
   *  and the secondary table, respectively. If unspecified, the values of
   *  all columns with matching names are compared.
   * @param {...import('./types.js').ExprList} [values]
   *  The column values to add from the secondary table. Can be column name
   *  strings or objects with column names as keys and table expressions as
   *  values. If unspecified, includes all columns from the secondary table
   *  whose names do no match any column in the primary table.
   * @return {this} A new table with lookup values added.
   * @example table.lookup(other, ['key1', 'key2'], 'value1', 'value2')
   */
  lookup(other, on, ...values2) {
    return lookup(this, other, on, ...values2);
  }
  /**
   * Join two tables, extending the columns of one table with
   * values from the other table. The current table is considered
   * the "left" table in the join, and the new table input is
   * considered the "right" table in the join. By default an inner
   * join is performed, removing all rows that do not match the
   * join criteria. To perform left, right, or full outer joins, use
   * the *join_left*, *join_right*, or *join_full* methods, or provide
   * an options argument.
   * @param {import('./types.js').TableRef} other
   *  The other (right) table to join with.
   * @param {import('./types.js').JoinPredicate} [on]
   *  The join criteria for matching table rows. If unspecified, the values of
   *  all columns with matching names are compared.
   *  If array-valued, a two-element array should be provided, containing
   *  the columns to compare for the left and right tables, respectively.
   *  If a one-element array or a string value is provided, the same
   *  column names will be drawn from both tables.
   *  If function-valued, should be a two-table table expression that
   *  returns a boolean value. When providing a custom predicate, note that
   *  join key values can be arrays or objects, and that normal join
   *  semantics do not consider null or undefined values to be equal (that is,
   *  null !== null). Use the op.equal function to handle these cases.
   * @param {import('./types.js').JoinValues} [values]
   *  The columns to include in the join output.
   *  If unspecified, all columns from both tables are included; paired
   *  join keys sharing the same column name are included only once.
   *  If array-valued, a two element array should be provided, containing
   *  the columns to include for the left and right tables, respectively.
   *  Array input may consist of column name strings, objects with output
   *  names as keys and single-table table expressions as values, or the
   *  selection helper functions *all*, *not*, or *range*.
   *  If object-valued, specifies the key-value pairs for each output,
   *  defined using two-table table expressions.
   * @param {import('./types.js').JoinOptions} [options]
   *  Options for the join.
   * @return {this} A new joined table.
   * @example table.join(other, ['keyL', 'keyR'])
   * @example table.join(other, (a, b) => op.equal(a.keyL, b.keyR))
   */
  join(other, on, values2, options) {
    return join(this, other, on, values2, options);
  }
  /**
   * Perform a left outer join on two tables. Rows in the left table
   * that do not match a row in the right table will be preserved.
   * This is a convenience method with fixed options for *join*.
   * @param {import('./types.js').TableRef} other
   *  The other (right) table to join with.
   * @param {import('./types.js').JoinPredicate} [on]
   *  The join criteria for matching table rows.
   *  If unspecified, the values of all columns with matching names
   *  are compared.
   *  If array-valued, a two-element array should be provided, containing
   *  the columns to compare for the left and right tables, respectively.
   *  If a one-element array or a string value is provided, the same
   *  column names will be drawn from both tables.
   *  If function-valued, should be a two-table table expression that
   *  returns a boolean value. When providing a custom predicate, note that
   *  join key values can be arrays or objects, and that normal join
   *  semantics do not consider null or undefined values to be equal (that is,
   *  null !== null). Use the op.equal function to handle these cases.
   * @param {import('./types.js').JoinValues} [values]
   *  he columns to include in the join output.
   *  If unspecified, all columns from both tables are included; paired
   *  join keys sharing the same column name are included only once.
   *  If array-valued, a two element array should be provided, containing
   *  the columns to include for the left and right tables, respectively.
   *  Array input may consist of column name strings, objects with output
   *  names as keys and single-table table expressions as values, or the
   *  selection helper functions *all*, *not*, or *range*.
   *  If object-valued, specifies the key-value pairs for each output,
   *  defined using two-table table expressions.
   * @param {import('./types.js').JoinOptions} [options]
   *  Options for the join. With this method, any options will be
   *  overridden with `{left: true, right: false}`.
   * @return {this} A new joined table.
   * @example table.join_left(other, ['keyL', 'keyR'])
   * @example table.join_left(other, (a, b) => op.equal(a.keyL, b.keyR))
   */
  join_left(other, on, values2, options) {
    const opt2 = { ...options, left: true, right: false };
    return join(this, other, on, values2, opt2);
  }
  /**
   * Perform a right outer join on two tables. Rows in the right table
   * that do not match a row in the left table will be preserved.
   * This is a convenience method with fixed options for *join*.
   * @param {import('./types.js').TableRef} other
   *  The other (right) table to join with.
   * @param {import('./types.js').JoinPredicate} [on]
   *  The join criteria for matching table rows.
   *  If unspecified, the values of all columns with matching names
   *  are compared.
   *  If array-valued, a two-element array should be provided, containing
   *  the columns to compare for the left and right tables, respectively.
   *  If a one-element array or a string value is provided, the same
   *  column names will be drawn from both tables.
   *  If function-valued, should be a two-table table expression that
   *  returns a boolean value. When providing a custom predicate, note that
   *  join key values can be arrays or objects, and that normal join
   *  semantics do not consider null or undefined values to be equal (that is,
   *  null !== null). Use the op.equal function to handle these cases.
   * @param {import('./types.js').JoinValues} [values]
   *  The columns to include in the join output.
   *  If unspecified, all columns from both tables are included; paired
   *  join keys sharing the same column name are included only once.
   *  If array-valued, a two element array should be provided, containing
   *  the columns to include for the left and right tables, respectively.
   *  Array input may consist of column name strings, objects with output
   *  names as keys and single-table table expressions as values, or the
   *  selection helper functions *all*, *not*, or *range*.
   *  If object-valued, specifies the key-value pairs for each output,
   *  defined using two-table table expressions.
   * @param {import('./types.js').JoinOptions} [options]
   *  Options for the join. With this method, any options will be overridden
   *  with `{left: false, right: true}`.
   * @return {this} A new joined table.
   * @example table.join_right(other, ['keyL', 'keyR'])
   * @example table.join_right(other, (a, b) => op.equal(a.keyL, b.keyR))
   */
  join_right(other, on, values2, options) {
    const opt2 = { ...options, left: false, right: true };
    return join(this, other, on, values2, opt2);
  }
  /**
   * Perform a full outer join on two tables. Rows in either the left or
   * right table that do not match a row in the other will be preserved.
   * This is a convenience method with fixed options for *join*.
   * @param {import('./types.js').TableRef} other
   *  The other (right) table to join with.
   * @param {import('./types.js').JoinPredicate} [on]
   *  The join criteria for matching table rows.
   *  If unspecified, the values of all columns with matching names
   *  are compared.
   *  If array-valued, a two-element array should be provided, containing
   *  the columns to compare for the left and right tables, respectively.
   *  If a one-element array or a string value is provided, the same
   *  column names will be drawn from both tables.
   *  If function-valued, should be a two-table table expression that
   *  returns a boolean value. When providing a custom predicate, note that
   *  join key values can be arrays or objects, and that normal join
   *  semantics do not consider null or undefined values to be equal (that is,
   *  null !== null). Use the op.equal function to handle these cases.
   * @param {import('./types.js').JoinValues} [values]
   *  The columns to include in the join output.
   *  If unspecified, all columns from both tables are included; paired
   *  join keys sharing the same column name are included only once.
   *  If array-valued, a two element array should be provided, containing
   *  the columns to include for the left and right tables, respectively.
   *  Array input may consist of column name strings, objects with output
   *  names as keys and single-table table expressions as values, or the
   *  selection helper functions *all*, *not*, or *range*.
   *  If object-valued, specifies the key-value pairs for each output,
   *  defined using two-table table expressions.
   * @param {import('./types.js').JoinOptions} [options]
   *  Options for the join. With this method, any options will be overridden
   *  with `{left: true, right: true}`.
   * @return {this} A new joined table.
   * @example table.join_full(other, ['keyL', 'keyR'])
   * @example table.join_full(other, (a, b) => op.equal(a.keyL, b.keyR))
   */
  join_full(other, on, values2, options) {
    const opt2 = { ...options, left: true, right: true };
    return join(this, other, on, values2, opt2);
  }
  /**
   * Produce the Cartesian cross product of two tables. The output table
   * has one row for every pair of input table rows. Beware that outputs
   * may be quite large, as the number of output rows is the product of
   * the input row counts.
   * This is a convenience method for *join* in which the
   * join criteria is always true.
   * @param {import('./types.js').TableRef} other
   *  The other (right) table to join with.
   * @param {import('./types.js').JoinValues} [values]
   *  The columns to include in the output.
   *  If unspecified, all columns from both tables are included.
   *  If array-valued, a two element array should be provided, containing
   *  the columns to include for the left and right tables, respectively.
   *  Array input may consist of column name strings, objects with output
   *  names as keys and single-table table expressions as values, or the
   *  selection helper functions *all*, *not*, or *range*.
   *  If object-valued, specifies the key-value pairs for each output,
   *  defined using two-table table expressions.
   * @param {import('./types.js').JoinOptions} [options]
   *  Options for the join.
   * @return {this} A new joined table.
   * @example table.cross(other)
   * @example table.cross(other, [['leftKey', 'leftVal'], ['rightVal']])
   */
  cross(other, values2, options) {
    return cross(this, other, values2, options);
  }
  /**
   * Perform a semi-join, filtering the left table to only rows that
   * match a row in the right table.
   * @param {import('./types.js').TableRef} other
   *  The other (right) table to join with.
   * @param {import('./types.js').JoinPredicate} [on]
   *  The join criteria for matching table rows.
   *  If unspecified, the values of all columns with matching names
   *  are compared.
   *  If array-valued, a two-element array should be provided, containing
   *  the columns to compare for the left and right tables, respectively.
   *  If a one-element array or a string value is provided, the same
   *  column names will be drawn from both tables.
   *  If function-valued, should be a two-table table expression that
   *  returns a boolean value. When providing a custom predicate, note that
   *  join key values can be arrays or objects, and that normal join
   *  semantics do not consider null or undefined values to be equal (that is,
   *  null !== null). Use the op.equal function to handle these cases.
   * @return {this} A new filtered table.
   * @example table.semijoin(other)
   * @example table.semijoin(other, ['keyL', 'keyR'])
   * @example table.semijoin(other, (a, b) => op.equal(a.keyL, b.keyR))
   */
  semijoin(other, on) {
    return semijoin(this, other, on);
  }
  /**
   * Perform an anti-join, filtering the left table to only rows that
   * do *not* match a row in the right table.
   * @param {import('./types.js').TableRef} other
   *  The other (right) table to join with.
   * @param {import('./types.js').JoinPredicate} [on]
   *  The join criteria for matching table rows.
   *  If unspecified, the values of all columns with matching names
   *  are compared.
   *  If array-valued, a two-element array should be provided, containing
   *  the columns to compare for the left and right tables, respectively.
   *  If a one-element array or a string value is provided, the same
   *  column names will be drawn from both tables.
   *  If function-valued, should be a two-table table expression that
   *  returns a boolean value. When providing a custom predicate, note that
   *  join key values can be arrays or objects, and that normal join
   *  semantics do not consider null or undefined values to be equal (that is,
   *  null !== null). Use the op.equal function to handle these cases.
   * @return {this} A new filtered table.
   * @example table.antijoin(other)
   * @example table.antijoin(other, ['keyL', 'keyR'])
   * @example table.antijoin(other, (a, b) => op.equal(a.keyL, b.keyR))
   */
  antijoin(other, on) {
    return antijoin(this, other, on);
  }
  // -- Set Operations ------------------------------------------------------
  /**
   * Concatenate multiple tables into a single table, preserving all rows.
   * This transformation mirrors the UNION_ALL operation in SQL.
   * Only named columns in this table are included in the output.
   * @param  {...import('./types.js').TableRefList} tables
   *  A list of tables to concatenate.
   * @return {this} A new concatenated table.
   * @example table.concat(other)
   * @example table.concat(other1, other2)
   * @example table.concat([other1, other2])
   */
  concat(...tables) {
    return concat(this, ...tables);
  }
  /**
   * Union multiple tables into a single table, deduplicating all rows.
   * This transformation mirrors the UNION operation in SQL. It is
   * similar to *concat* but suppresses duplicate rows with
   * values identical to another row.
   * Only named columns in this table are included in the output.
   * @param  {...import('./types.js').TableRefList} tables
   *  A list of tables to union.
   * @return {this} A new unioned table.
   * @example table.union(other)
   * @example table.union(other1, other2)
   * @example table.union([other1, other2])
   */
  union(...tables) {
    return union$1(this, ...tables);
  }
  /**
   * Intersect multiple tables, keeping only rows whose with identical
   * values for all columns in all tables, and deduplicates the rows.
   * This transformation is similar to a series of *semijoin*.
   * calls, but additionally suppresses duplicate rows.
   * @param  {...import('./types.js').TableRefList} tables
   *  A list of tables to intersect.
   * @return {this} A new filtered table.
   * @example table.intersect(other)
   * @example table.intersect(other1, other2)
   * @example table.intersect([other1, other2])
   */
  intersect(...tables) {
    return intersect(this, ...tables);
  }
  /**
   * Compute the set difference with multiple tables, keeping only rows in
   * this table that whose values do not occur in the other tables.
   * This transformation is similar to a series of *anitjoin*
   * calls, but additionally suppresses duplicate rows.
   * @param  {...import('./types.js').TableRefList} tables
   *  A list of tables to difference.
   * @return {this} A new filtered table.
   * @example table.except(other)
   * @example table.except(other1, other2)
   * @example table.except([other1, other2])
   */
  except(...tables) {
    return except(this, ...tables);
  }
  // -- Table Output Formats ------------------------------------------------
  /**
   * Format this table as a Flechette Arrow table.
   * @param {import('../format/types.js').ArrowFormatOptions} [options]
   *  The Arrow formatting options.
   * @return {import('@uwdata/flechette').Table} A Flechette Arrow table.
   */
  toArrow(options) {
    return toArrow(this, options);
  }
  /**
   * Format this table as binary data in the Apache Arrow IPC format.
   * @param {import('../format/types.js').ArrowIPCFormatOptions} [options]
   *  The Arrow IPC formatting options.
   * @return {Uint8Array} A new Uint8Array of Arrow-encoded binary data.
   */
  toArrowIPC(options) {
    return toArrowIPC(this, options);
  }
  /**
   * Format this table as a comma-separated values (CSV) string. Other
   * delimiters, such as tabs or pipes ('|'), can be specified using
   * the options argument.
   * @param {import('../format/to-csv.js').CSVFormatOptions} [options]
   *   The CSV formatting options.
   * @return {string} A delimited value string.
   */
  toCSV(options) {
    return toCSV(this, options);
  }
  /**
   * Format this table as an HTML table string.
   * @param {import('../format/to-html.js').HTMLFormatOptions} [options]
   *  The HTML formatting options.
   * @return {string} An HTML table string.
   */
  toHTML(options) {
    return toHTML(this, options);
  }
  /**
   * Format this table as a JavaScript Object Notation (JSON) string.
   * @param {import('../format/to-json.js').JSONFormatOptions} [options]
   *  The JSON formatting options.
   * @return {string} A JSON string.
   */
  toJSON(options) {
    return toJSON(this, options);
  }
  /**
   * Format this table as a GitHub-Flavored Markdown table string.
   * @param {import('../format/to-markdown.js').MarkdownFormatOptions} [options]
   *  The Markdown formatting options.
   * @return {string} A GitHub-Flavored Markdown table string.
   */
  toMarkdown(options) {
    return toMarkdown(this, options);
  }
}
function fromArrow(input, options) {
  const { columns: columns2 = all(), ...rest } = {};
  const arrow = input instanceof ArrayBuffer || input instanceof Uint8Array ? tableFromIPC(input, { useDate: true, ...rest }) : input;
  const { fields } = arrow.schema;
  const names = fields.map((f) => f.name);
  const sel = resolve({
    columnNames: (test) => test ? names.filter(test) : names.slice(),
    columnIndex: (name2) => names.indexOf(name2)
  }, columns2);
  const cols = columnSet();
  sel.forEach((name2, key2) => {
    const col = (
      /** @type {import('./types.js').ArrowColumn} */
      arrow.getChild(key2)
    );
    cols.add(name2, col.type.typeId === -1 ? dictionary(col) : col);
  });
  return new ColumnTable(cols.data, cols.names);
}
function dictionary(column) {
  const { data: data2, length: length2, nullCount } = column;
  const batch = data2[data2.length - 1];
  const cache = batch.cache ?? batch.dictionary.toArray();
  const size = cache.length;
  const keys2 = dictKeys(data2, length2, nullCount, size);
  const get2 = nullCount ? ((k) => k === size ? null : cache[k]) : ((k) => cache[k]);
  return {
    length: length2,
    nullCount,
    at: (row) => get2(keys2[row]),
    key: (row) => keys2[row],
    keyFor(value2) {
      if (value2 === null) return nullCount ? size : -1;
      for (let i = 0; i < size; ++i) {
        if (cache[i] === value2) return i;
      }
      return -1;
    },
    groups(names) {
      const s = size + (nullCount ? 1 : 0);
      return {
        keys: keys2,
        get: [get2],
        names,
        rows: sequence(0, s),
        size: s
      };
    },
    [Symbol.iterator]: () => column[Symbol.iterator](),
    toArray: () => column.toArray()
  };
}
function dictKeys(data2, length2, nulls, size) {
  const v = data2.length > 1 || nulls ? flatten(data2, length2) : data2[0].values;
  return nulls ? nullKeys(data2, v, size) : v;
}
function flatten(data2, length2) {
  const type = data2[0].values.constructor;
  const array2 = new type(length2);
  const n = data2.length;
  for (let i = 0, idx = 0, len; i < n; ++i) {
    len = data2[i].length;
    array2.set(data2[i].values.subarray(0, len), idx);
    idx += len;
  }
  return array2;
}
function nullKeys(data2, keys2, key2) {
  const n = data2.length;
  for (let i = 0, idx = 0, byte; i < n; ++i) {
    const batch = data2[i];
    const { length: length2 } = batch;
    const validity = batch.validity ?? batch.nullBitmap;
    const m = length2 >> 3;
    if (validity && validity.length) {
      for (let j = 0; j <= m; ++j) {
        if ((byte = validity[j]) !== 255) {
          const base = idx + (j << 3);
          if ((byte & 1 << 0) === 0) keys2[base + 0] = key2;
          if ((byte & 1 << 1) === 0) keys2[base + 1] = key2;
          if ((byte & 1 << 2) === 0) keys2[base + 2] = key2;
          if ((byte & 1 << 3) === 0) keys2[base + 3] = key2;
          if ((byte & 1 << 4) === 0) keys2[base + 4] = key2;
          if ((byte & 1 << 5) === 0) keys2[base + 5] = key2;
          if ((byte & 1 << 6) === 0) keys2[base + 6] = key2;
          if ((byte & 1 << 7) === 0) keys2[base + 7] = key2;
        }
      }
    }
    idx += length2;
  }
  return keys2;
}
function escape(value2) {
  return wrap$1(value2, {
    escape: true,
    toString() {
      error("Escaped values can not be serialized.");
    }
  });
}
function columnsFrom(values2, names) {
  const raise2 = (type) => {
    error(`Illegal argument type: ${type || typeof values2}`);
    return (
      /** @type {import('./types.js').ColumnData} */
      {}
    );
  };
  return values2 instanceof Map ? fromKeyValuePairs(values2.entries(), names) : isDate$1(values2) ? raise2("Date") : isRegExp(values2) ? raise2("RegExp") : isString(values2) ? raise2() : isArray$2(values2) ? fromArray(values2, names) : isFunction(values2[Symbol.iterator]) ? fromIterable(values2, names) : isObject(values2) ? fromKeyValuePairs(Object.entries(values2), names) : raise2();
}
function fromKeyValuePairs(entries2, names = ["key", "value"]) {
  const keys2 = [];
  const vals = [];
  for (const [key2, val] of entries2) {
    keys2.push(key2);
    vals.push(val);
  }
  const columns2 = {};
  if (names[0]) columns2[names[0]] = keys2;
  if (names[1]) columns2[names[1]] = vals;
  return columns2;
}
function fromArray(values2, names) {
  const len = values2.length;
  const columns2 = {};
  const add = (name2) => columns2[name2] = Array(len);
  if (len) {
    names = names || Object.keys(values2[0]);
    const cols = names.map(add);
    const n = cols.length;
    for (let idx = 0; idx < len; ++idx) {
      const row = values2[idx];
      for (let i = 0; i < n; ++i) {
        cols[i][idx] = row[names[i]];
      }
    }
  } else if (names) {
    names.forEach(add);
  }
  return columns2;
}
function fromIterable(values2, names) {
  const columns2 = {};
  const add = (name2) => columns2[name2] = [];
  let cols;
  let n;
  for (const row of values2) {
    if (!cols) {
      names = names || Object.keys(row);
      cols = names.map(add);
      n = cols.length;
    }
    for (let i = 0; i < n; ++i) {
      cols[i].push(row[names[i]]);
    }
  }
  if (!cols && names) {
    names.forEach(add);
  }
  return columns2;
}
function table(columns2, names) {
  if (columns2 instanceof ColumnTable) return columns2;
  const data2 = {};
  const keys2 = [];
  for (const [key2, value2] of entries(columns2)) {
    data2[key2] = value2;
    keys2.push(key2);
  }
  return new ColumnTable(data2, keys2);
}
function from(values2, names) {
  return new ColumnTable(columnsFrom(values2, names), names);
}
var lz4 = {};
var xxh32 = {};
var util = {};
var hasRequiredUtil;
function requireUtil() {
  if (hasRequiredUtil) return util;
  hasRequiredUtil = 1;
  util.hashU32 = function hashU32(a) {
    a = a | 0;
    a = a + 2127912214 + (a << 12) | 0;
    a = a ^ -949894596 ^ a >>> 19;
    a = a + 374761393 + (a << 5) | 0;
    a = a + -744332180 ^ a << 9;
    a = a + -42973499 + (a << 3) | 0;
    return a ^ -1252372727 ^ a >>> 16 | 0;
  };
  util.readU64 = function readU64(b, n) {
    var x = 0;
    x |= b[n++] << 0;
    x |= b[n++] << 8;
    x |= b[n++] << 16;
    x |= b[n++] << 24;
    x |= b[n++] << 32;
    x |= b[n++] << 40;
    x |= b[n++] << 48;
    x |= b[n++] << 56;
    return x;
  };
  util.readU32 = function readU32(b, n) {
    var x = 0;
    x |= b[n++] << 0;
    x |= b[n++] << 8;
    x |= b[n++] << 16;
    x |= b[n++] << 24;
    return x;
  };
  util.writeU32 = function writeU32(b, n, x) {
    b[n++] = x >> 0 & 255;
    b[n++] = x >> 8 & 255;
    b[n++] = x >> 16 & 255;
    b[n++] = x >> 24 & 255;
  };
  util.imul = function imul(a, b) {
    var ah = a >>> 16;
    var al = a & 65535;
    var bh = b >>> 16;
    var bl = b & 65535;
    return al * bl + (ah * bl + al * bh << 16) | 0;
  };
  return util;
}
var hasRequiredXxh32;
function requireXxh32() {
  if (hasRequiredXxh32) return xxh32;
  hasRequiredXxh32 = 1;
  var util2 = requireUtil();
  var prime1 = 2654435761;
  var prime2 = 2246822519;
  var prime3 = 3266489917;
  var prime4 = 668265263;
  var prime5 = 374761393;
  function rotl32(x, r) {
    x = x | 0;
    r = r | 0;
    return x >>> (32 - r | 0) | x << r | 0;
  }
  function rotmul32(h, r, m) {
    h = h | 0;
    r = r | 0;
    m = m | 0;
    return util2.imul(h >>> (32 - r | 0) | h << r, m) | 0;
  }
  function shiftxor32(h, s) {
    h = h | 0;
    s = s | 0;
    return h >>> s ^ h | 0;
  }
  function xxhapply(h, src, m0, s, m1) {
    return rotmul32(util2.imul(src, m0) + h, s, m1);
  }
  function xxh1(h, src, index) {
    return rotmul32(h + util2.imul(src[index], prime5), 11, prime1);
  }
  function xxh4(h, src, index) {
    return xxhapply(h, util2.readU32(src, index), prime3, 17, prime4);
  }
  function xxh16(h, src, index) {
    return [
      xxhapply(h[0], util2.readU32(src, index + 0), prime2, 13, prime1),
      xxhapply(h[1], util2.readU32(src, index + 4), prime2, 13, prime1),
      xxhapply(h[2], util2.readU32(src, index + 8), prime2, 13, prime1),
      xxhapply(h[3], util2.readU32(src, index + 12), prime2, 13, prime1)
    ];
  }
  function xxh32$1(seed, src, index, len) {
    var h, l;
    l = len;
    if (len >= 16) {
      h = [
        seed + prime1 + prime2,
        seed + prime2,
        seed,
        seed - prime1
      ];
      while (len >= 16) {
        h = xxh16(h, src, index);
        index += 16;
        len -= 16;
      }
      h = rotl32(h[0], 1) + rotl32(h[1], 7) + rotl32(h[2], 12) + rotl32(h[3], 18) + l;
    } else {
      h = seed + prime5 + len >>> 0;
    }
    while (len >= 4) {
      h = xxh4(h, src, index);
      index += 4;
      len -= 4;
    }
    while (len > 0) {
      h = xxh1(h, src, index);
      index++;
      len--;
    }
    h = shiftxor32(util2.imul(shiftxor32(util2.imul(shiftxor32(h, 15), prime2), 13), prime3), 16);
    return h >>> 0;
  }
  xxh32.hash = xxh32$1;
  return xxh32;
}
var hasRequiredLz4;
function requireLz4() {
  if (hasRequiredLz4) return lz4;
  hasRequiredLz4 = 1;
  (function(exports) {
    var xxhash = requireXxh32();
    var util2 = requireUtil();
    var minMatch = 4;
    var minLength = 13;
    var searchLimit = 5;
    var skipTrigger = 6;
    var hashSize = 1 << 16;
    var mlBits = 4;
    var mlMask = (1 << mlBits) - 1;
    var runBits = 4;
    var runMask = (1 << runBits) - 1;
    var blockBuf = makeBuffer(5 << 20);
    var hashTable = makeHashTable();
    var magicNum = 407708164;
    var fdContentChksum = 4;
    var fdContentSize = 8;
    var fdBlockChksum = 16;
    var fdVersion = 64;
    var fdVersionMask = 192;
    var bsUncompressed = 2147483648;
    var bsDefault = 7;
    var bsShift = 4;
    var bsMask = 7;
    var bsMap = {
      4: 65536,
      5: 262144,
      6: 1048576,
      7: 4194304
    };
    function makeHashTable() {
      try {
        return new Uint32Array(hashSize);
      } catch (error2) {
        var hashTable2 = new Array(hashSize);
        for (var i = 0; i < hashSize; i++) {
          hashTable2[i] = 0;
        }
        return hashTable2;
      }
    }
    function clearHashTable(table2) {
      for (var i = 0; i < hashSize; i++) {
        hashTable[i] = 0;
      }
    }
    function makeBuffer(size) {
      try {
        return new Uint8Array(size);
      } catch (error2) {
        var buf2 = new Array(size);
        for (var i = 0; i < size; i++) {
          buf2[i] = 0;
        }
        return buf2;
      }
    }
    function sliceArray(array2, start, end) {
      if (typeof array2.buffer !== void 0) {
        if (Uint8Array.prototype.slice) {
          return array2.slice(start, end);
        } else {
          var len = array2.length;
          start = start | 0;
          start = start < 0 ? Math.max(len + start, 0) : Math.min(start, len);
          end = end === void 0 ? len : end | 0;
          end = end < 0 ? Math.max(len + end, 0) : Math.min(end, len);
          var arraySlice = new Uint8Array(end - start);
          for (var i = start, n = 0; i < end; ) {
            arraySlice[n++] = array2[i++];
          }
          return arraySlice;
        }
      } else {
        return array2.slice(start, end);
      }
    }
    exports.compressBound = function compressBound(n) {
      return n + n / 255 + 16 | 0;
    };
    exports.decompressBound = function decompressBound(src) {
      var sIndex = 0;
      if (util2.readU32(src, sIndex) !== magicNum) {
        throw new Error("invalid magic number");
      }
      sIndex += 4;
      var descriptor = src[sIndex++];
      if ((descriptor & fdVersionMask) !== fdVersion) {
        throw new Error("incompatible descriptor version " + (descriptor & fdVersionMask));
      }
      var useBlockSum = (descriptor & fdBlockChksum) !== 0;
      var useContentSize = (descriptor & fdContentSize) !== 0;
      var bsIdx = src[sIndex++] >> bsShift & bsMask;
      if (bsMap[bsIdx] === void 0) {
        throw new Error("invalid block size " + bsIdx);
      }
      var maxBlockSize = bsMap[bsIdx];
      if (useContentSize) {
        return util2.readU64(src, sIndex);
      }
      sIndex++;
      var maxSize = 0;
      while (true) {
        var blockSize = util2.readU32(src, sIndex);
        sIndex += 4;
        if (blockSize & bsUncompressed) {
          blockSize &= ~bsUncompressed;
          maxSize += blockSize;
        } else {
          maxSize += maxBlockSize;
        }
        if (blockSize === 0) {
          return maxSize;
        }
        if (useBlockSum) {
          sIndex += 4;
        }
        sIndex += blockSize;
      }
    };
    exports.makeBuffer = makeBuffer;
    exports.decompressBlock = function decompressBlock(src, dst, sIndex, sLength, dIndex) {
      var mLength, mOffset, sEnd, n, i;
      sEnd = sIndex + sLength;
      while (sIndex < sEnd) {
        var token = src[sIndex++];
        var literalCount = token >> 4;
        if (literalCount > 0) {
          if (literalCount === 15) {
            while (true) {
              literalCount += src[sIndex];
              if (src[sIndex++] !== 255) {
                break;
              }
            }
          }
          for (n = sIndex + literalCount; sIndex < n; ) {
            dst[dIndex++] = src[sIndex++];
          }
        }
        if (sIndex >= sEnd) {
          break;
        }
        mLength = token & 15;
        mOffset = src[sIndex++] | src[sIndex++] << 8;
        if (mLength === 15) {
          while (true) {
            mLength += src[sIndex];
            if (src[sIndex++] !== 255) {
              break;
            }
          }
        }
        mLength += minMatch;
        for (i = dIndex - mOffset, n = i + mLength; i < n; ) {
          dst[dIndex++] = dst[i++] | 0;
        }
      }
      return dIndex;
    };
    exports.compressBlock = function compressBlock(src, dst, sIndex, sLength, hashTable2) {
      var mIndex, mAnchor, mLength, mOffset, mStep;
      var literalCount, dIndex, sEnd, n;
      dIndex = 0;
      sEnd = sLength + sIndex;
      mAnchor = sIndex;
      if (sLength >= minLength) {
        var searchMatchCount = (1 << skipTrigger) + 3;
        while (sIndex + minMatch < sEnd - searchLimit) {
          var seq = util2.readU32(src, sIndex);
          var hash = util2.hashU32(seq) >>> 0;
          hash = (hash >> 16 ^ hash) >>> 0 & 65535;
          mIndex = hashTable2[hash] - 1;
          hashTable2[hash] = sIndex + 1;
          if (mIndex < 0 || sIndex - mIndex >>> 16 > 0 || util2.readU32(src, mIndex) !== seq) {
            mStep = searchMatchCount++ >> skipTrigger;
            sIndex += mStep;
            continue;
          }
          searchMatchCount = (1 << skipTrigger) + 3;
          literalCount = sIndex - mAnchor;
          mOffset = sIndex - mIndex;
          sIndex += minMatch;
          mIndex += minMatch;
          mLength = sIndex;
          while (sIndex < sEnd - searchLimit && src[sIndex] === src[mIndex]) {
            sIndex++;
            mIndex++;
          }
          mLength = sIndex - mLength;
          var token = mLength < mlMask ? mLength : mlMask;
          if (literalCount >= runMask) {
            dst[dIndex++] = (runMask << mlBits) + token;
            for (n = literalCount - runMask; n >= 255; n -= 255) {
              dst[dIndex++] = 255;
            }
            dst[dIndex++] = n;
          } else {
            dst[dIndex++] = (literalCount << mlBits) + token;
          }
          for (var i = 0; i < literalCount; i++) {
            dst[dIndex++] = src[mAnchor + i];
          }
          dst[dIndex++] = mOffset;
          dst[dIndex++] = mOffset >> 8;
          if (mLength >= mlMask) {
            for (n = mLength - mlMask; n >= 255; n -= 255) {
              dst[dIndex++] = 255;
            }
            dst[dIndex++] = n;
          }
          mAnchor = sIndex;
        }
      }
      if (mAnchor === 0) {
        return 0;
      }
      literalCount = sEnd - mAnchor;
      if (literalCount >= runMask) {
        dst[dIndex++] = runMask << mlBits;
        for (n = literalCount - runMask; n >= 255; n -= 255) {
          dst[dIndex++] = 255;
        }
        dst[dIndex++] = n;
      } else {
        dst[dIndex++] = literalCount << mlBits;
      }
      sIndex = mAnchor;
      while (sIndex < sEnd) {
        dst[dIndex++] = src[sIndex++];
      }
      return dIndex;
    };
    exports.decompressFrame = function decompressFrame(src, dst) {
      var useBlockSum, useContentSum, useContentSize, descriptor;
      var sIndex = 0;
      var dIndex = 0;
      if (util2.readU32(src, sIndex) !== magicNum) {
        throw new Error("invalid magic number");
      }
      sIndex += 4;
      descriptor = src[sIndex++];
      if ((descriptor & fdVersionMask) !== fdVersion) {
        throw new Error("incompatible descriptor version");
      }
      useBlockSum = (descriptor & fdBlockChksum) !== 0;
      useContentSum = (descriptor & fdContentChksum) !== 0;
      useContentSize = (descriptor & fdContentSize) !== 0;
      var bsIdx = src[sIndex++] >> bsShift & bsMask;
      if (bsMap[bsIdx] === void 0) {
        throw new Error("invalid block size");
      }
      if (useContentSize) {
        sIndex += 8;
      }
      sIndex++;
      while (true) {
        var compSize;
        compSize = util2.readU32(src, sIndex);
        sIndex += 4;
        if (compSize === 0) {
          break;
        }
        if (useBlockSum) {
          sIndex += 4;
        }
        if ((compSize & bsUncompressed) !== 0) {
          compSize &= ~bsUncompressed;
          for (var j = 0; j < compSize; j++) {
            dst[dIndex++] = src[sIndex++];
          }
        } else {
          dIndex = exports.decompressBlock(src, dst, sIndex, compSize, dIndex);
          sIndex += compSize;
        }
      }
      if (useContentSum) {
        sIndex += 4;
      }
      return dIndex;
    };
    exports.compressFrame = function compressFrame(src, dst) {
      var dIndex = 0;
      util2.writeU32(dst, dIndex, magicNum);
      dIndex += 4;
      dst[dIndex++] = fdVersion;
      dst[dIndex++] = bsDefault << bsShift;
      dst[dIndex] = xxhash.hash(0, dst, 4, dIndex - 4) >> 8;
      dIndex++;
      var maxBlockSize = bsMap[bsDefault];
      var remaining = src.length;
      var sIndex = 0;
      clearHashTable();
      while (remaining > 0) {
        var compSize = 0;
        var blockSize = remaining > maxBlockSize ? maxBlockSize : remaining;
        compSize = exports.compressBlock(src, blockBuf, sIndex, blockSize, hashTable);
        if (compSize > blockSize || compSize === 0) {
          util2.writeU32(dst, dIndex, 2147483648 | blockSize);
          dIndex += 4;
          for (var z = sIndex + blockSize; sIndex < z; ) {
            dst[dIndex++] = src[sIndex++];
          }
          remaining -= blockSize;
        } else {
          util2.writeU32(dst, dIndex, compSize);
          dIndex += 4;
          for (var j = 0; j < compSize; ) {
            dst[dIndex++] = blockBuf[j++];
          }
          sIndex += blockSize;
          remaining -= blockSize;
        }
      }
      util2.writeU32(dst, dIndex, 0);
      dIndex += 4;
      return dIndex;
    };
    exports.decompress = function decompress(src, maxSize) {
      var dst, size;
      if (maxSize === void 0) {
        maxSize = exports.decompressBound(src);
      }
      dst = exports.makeBuffer(maxSize);
      size = exports.decompressFrame(src, dst);
      if (size !== maxSize) {
        dst = sliceArray(dst, 0, size);
      }
      return dst;
    };
    exports.compress = function compress(src, maxSize) {
      var dst, size;
      if (maxSize === void 0) {
        maxSize = exports.compressBound(src.length);
      }
      dst = exports.makeBuffer(maxSize);
      size = exports.compressFrame(src, dst);
      if (size !== maxSize) {
        dst = sliceArray(dst, 0, size);
      }
      return dst;
    };
  })(lz4);
  return lz4;
}
var lz4Exports = requireLz4();
const decodeArrowBytes = (bytes) => {
  ensureLZ4CodecRegistered();
  const arrowTable = tableFromIPC$1(bytes);
  const uncompressedBytes = tableToIPC$1(arrowTable);
  let table$1 = fromArrow(uncompressedBytes);
  table$1 = castColumns(table$1);
  const columns2 = {};
  const columnNames = table$1.columnNames();
  for (const colName of columnNames) {
    const colData = table$1.array(colName);
    columns2[colName] = Array.isArray(colData) ? colData : Array.from(colData);
  }
  return table(columns2);
};
let codecRegistered = false;
function ensureLZ4CodecRegistered() {
  if (!codecRegistered) {
    const lz4Codec = {
      encode(data2) {
        return lz4Exports.compress(data2);
      },
      decode(data2) {
        return lz4Exports.decompress(data2);
      }
    };
    compressionRegistry.set(CompressionType.LZ4_FRAME, lz4Codec);
    codecRegistered = true;
  }
}
function castColumns(table2) {
  const columnNames = table2.columnNames();
  const hasValue = columnNames.includes("value") && columnNames.includes("value_type");
  const hasScanRefusal = columnNames.includes("scan_error_refusal");
  if (!hasValue && !hasScanRefusal) {
    return table2;
  }
  const castValue = (value2, valueType) => {
    if (value2 === null || value2 === void 0) {
      return null;
    }
    if (valueType === "boolean") {
      if (typeof value2 === "boolean") {
        return value2;
      }
      const strVal = String(value2).toLowerCase();
      if (strVal === "true") {
        return true;
      }
      if (strVal === "false") {
        return false;
      }
      return null;
    } else if (valueType === "number") {
      if (typeof value2 === "number") {
        return value2;
      }
      const strVal = String(value2).trim();
      if (strVal === "") {
        return null;
      }
      const num = Number(strVal);
      return isNaN(num) ? null : num;
    } else {
      return value2;
    }
  };
  const derivations = {};
  if (hasValue) {
    derivations.value = escape((d) => {
      return castValue(d.value, d.value_type);
    });
  }
  if (hasScanRefusal) {
    derivations.scan_error_refusal = escape(
      (d) => {
        if (typeof d.scan_error_refusal === "string") {
          return d.scan_error_refusal?.toLowerCase() === "true";
        }
        return !!d.scan_error_refusal;
      }
    );
  }
  return table2.derive(derivations);
}
async function expandResultsetRows(columnTable) {
  const colNames = columnTable.columnNames();
  if (!colNames.includes("identifier")) {
    const numRows = columnTable.numRows();
    const identifiers = new Array(numRows);
    if (colNames.includes("uuid")) {
      const uuids = columnTable.array("uuid");
      for (let i = 0; i < numRows; i++) {
        identifiers[i] = uuids[i] ?? crypto.randomUUID();
      }
    } else {
      for (let i = 0; i < numRows; i++) {
        identifiers[i] = crypto.randomUUID();
      }
    }
    columnTable = columnTable.assign({ identifier: identifiers });
  }
  if (!colNames.includes("value_type") || !colNames.includes("value") || columnTable.numRows() === 0) {
    return columnTable;
  }
  const resultsetCount = columnTable.filter((d) => d.value_type === "resultset").numRows();
  if (resultsetCount === 0) {
    return columnTable;
  }
  const resultsetRows = columnTable.filter(
    (d) => d.value_type === "resultset"
  );
  const otherRows = columnTable.filter(
    (d) => d.value_type !== "resultset"
  );
  const resultObjs = resultsetRows.objects();
  const explodedResultsetRows = [];
  for (const row of resultObjs) {
    try {
      const valueStr2 = row.value;
      const results = valueStr2 ? lib.parse(valueStr2) : [];
      if (!results || results.length === 0) {
        const expandedRow = { ...row };
        expandedRow.value = null;
        expandedRow.value_type = "null";
        explodedResultsetRows.push(expandedRow);
        continue;
      }
      for (const result2 of results) {
        const expandedRow = { ...row };
        expandedRow.identifier = result2.uuid ?? crypto.randomUUID();
        expandedRow.label = result2.label ?? null;
        expandedRow.answer = result2.answer ?? null;
        expandedRow.explanation = result2.explanation ?? null;
        if (row.validation_result && typeof row.validation_result === "string") {
          expandedRow.validation_result = await extractLabelValidation(
            expandedRow,
            row.validation_result
          );
        }
        const metadata = result2.metadata ?? {};
        expandedRow.metadata = maybeSerializeValue(metadata);
        const valueType = result2.type ?? inferType(result2.value);
        expandedRow.value_type = valueType;
        const value2 = maybeSerializeValue(result2.value);
        expandedRow.value = value2;
        const references = result2.references ?? [];
        const messageRefs = references.filter((ref2) => ref2.type === "message");
        const eventRefs = references.filter((ref2) => ref2.type === "event");
        expandedRow.message_references = maybeSerializeValue(messageRefs);
        expandedRow.event_references = maybeSerializeValue(eventRefs);
        explodedResultsetRows.push(expandedRow);
      }
    } catch (error2) {
      console.error("Failed to parse resultset value:", error2);
      continue;
    }
  }
  const syntheticRows = await createSyntheticRows(
    explodedResultsetRows,
    resultObjs
  );
  if (explodedResultsetRows.length === 0) {
    return otherRows;
  } else {
    const otherRowsArray = otherRows.objects();
    const allRowsArray = [
      ...otherRowsArray,
      ...explodedResultsetRows,
      ...syntheticRows
    ];
    return from(allRowsArray);
  }
}
async function extractLabelValidation(row, validationResultStr) {
  if (!row.label || typeof row.label !== "string") {
    return validationResultStr;
  }
  try {
    const parsedValidation = await asyncJsonParse(validationResultStr);
    if (typeof parsedValidation === "object" && parsedValidation !== null && !Array.isArray(parsedValidation)) {
      const validationDict = parsedValidation;
      const labelValidation = validationDict[row.label];
      return labelValidation ?? null;
    }
    return parsedValidation;
  } catch (error2) {
    return validationResultStr;
  }
}
async function createSyntheticRows(expandedRows, resultsetRows) {
  if (resultsetRows.length === 0 || expandedRows.length === 0) {
    return [];
  }
  const firstRow = expandedRows[0];
  if (!firstRow || !firstRow.validation_target || typeof firstRow.validation_target !== "string") {
    return [];
  }
  try {
    const parsedTarget = await asyncJsonParse(
      firstRow.validation_target
    );
    if (typeof parsedTarget !== "object" || parsedTarget === null || Array.isArray(parsedTarget)) {
      return [];
    }
    const validationTarget = parsedTarget;
    const parsedResult = firstRow.validation_result ? await asyncJsonParse(
      typeof firstRow.validation_result === "string" ? firstRow.validation_result : JSON.stringify(firstRow.validation_result)
    ) : {};
    const validationResults = typeof parsedResult === "object" && !Array.isArray(parsedResult) ? parsedResult : {};
    const presentLabels = new Set(
      expandedRows.map((row) => row.label).filter((label) => label !== null && label !== void 0)
    );
    const expectedLabels = Object.keys(validationTarget);
    const missingLabels = expectedLabels.filter(
      (label) => !presentLabels.has(label)
    );
    const syntheticRows = [];
    const negativeValues = [false, null, "NONE", "none", 0, ""];
    for (const label of missingLabels) {
      const expectedValue = validationTarget[label];
      if (!negativeValues.includes(expectedValue)) {
        continue;
      }
      const templateRow = { ...resultsetRows[0] };
      templateRow.label = label;
      templateRow.value = expectedValue;
      templateRow.value_type = typeof expectedValue === "boolean" ? "boolean" : "null";
      templateRow.answer = null;
      templateRow.explanation = null;
      templateRow.metadata = maybeSerializeValue({});
      templateRow.message_references = maybeSerializeValue([]);
      templateRow.event_references = maybeSerializeValue([]);
      templateRow.uuid = null;
      templateRow.identifier = crypto.randomUUID();
      templateRow.validation_result = validationResults[label] ?? null;
      templateRow.scan_error = null;
      templateRow.scan_error_traceback = null;
      templateRow.scan_error_type = null;
      templateRow.scan_total_tokens = null;
      templateRow.scan_model_usage = null;
      syntheticRows.push(templateRow);
    }
    return syntheticRows;
  } catch (error2) {
    return [];
  }
}
function inferType(value2) {
  if (typeof value2 === "boolean") {
    return "boolean";
  } else if (typeof value2 === "number") {
    return "number";
  } else if (typeof value2 === "string") {
    return "string";
  } else if (Array.isArray(value2)) {
    return "array";
  } else if (value2 !== null && typeof value2 === "object") {
    return "object";
  }
  return "null";
}
const maybeSerializeValue = (value2) => {
  if (value2 === void 0 || value2 === null) {
    return null;
  }
  if (typeof value2 === "string" || typeof value2 === "number" || typeof value2 === "boolean") {
    return value2;
  }
  return lib.stringify(value2);
};
const useScanDataframe = (params) => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: params === skipToken ? [skipToken] : [
      "scanDataframe",
      params.scansDir,
      params.scanPath,
      params.scanner,
      "scans-inv"
    ],
    queryFn: params === skipToken ? skipToken : async () => expandResultsetRows(
      decodeArrowBytes(
        await api.getScannerDataframe(
          params.scansDir,
          params.scanPath,
          params.scanner
        )
      )
    ),
    staleTime: Infinity
  });
};
const useSelectedScanner = () => {
  const selectedScanner = useStore((state) => state.selectedScanner);
  const defaultScanner = useMapAsyncData(
    useSelectedScan(),
    _get_default_scanner
  );
  const selectedScannerAsyncData = reactExports.useMemo(
    () => selectedScanner ? data$1(selectedScanner) : void 0,
    [selectedScanner]
  );
  return selectedScannerAsyncData ?? defaultScanner;
};
const _get_default_scanner = (s) => {
  const result2 = s.summary.scanners ? Object.keys(s.summary.scanners)[0] : void 0;
  if (!result2) {
    throw new Error("Scan must have a scanner");
  }
  return result2;
};
const useSelectedScanDataframe = () => {
  const { resolvedScansDir, scanPath } = useScanRoute();
  const scanner = useSelectedScanner();
  return useScanDataframe(
    resolvedScansDir && scanPath && scanner.data ? { scansDir: resolvedScansDir, scanPath, scanner: scanner.data } : skipToken
  );
};
const parseScanResultData = async (filtered) => {
  const valueType = filtered.get("value_type", 0);
  const transcript_agent_args_raw = getOptionalColumn(
    filtered,
    "transcript_agent_args",
    0
  );
  const transcript_score_raw = getOptionalColumn(
    filtered,
    "transcript_score",
    0
  );
  const [
    eventReferences,
    inputIds,
    messageReferences,
    metadata,
    scanEvents,
    scanMetadata,
    scanModelUsage,
    scanTags,
    scannerParams,
    transcriptMetadata,
    validationResult,
    validationTarget,
    value2,
    transcriptAgentArgs,
    transcriptScore
  ] = await Promise.all([
    parseJson(filtered.get("event_references", 0)),
    parseJson(filtered.get("input_ids", 0)),
    parseJson(filtered.get("message_references", 0)),
    parseJson(filtered.get("metadata", 0)),
    parseJson(filtered.get("scan_events", 0)),
    parseJson(filtered.get("scan_metadata", 0)),
    parseJson(filtered.get("scan_model_usage", 0)),
    parseJson(filtered.get("scan_tags", 0)),
    parseJson(filtered.get("scanner_params", 0)),
    parseJson(filtered.get("transcript_metadata", 0)),
    tryParseJson(
      filtered.get("validation_result", 0)
    ),
    tryParseJson(filtered.get("validation_target", 0)),
    parseSimpleValue(filtered.get("value", 0), valueType),
    transcript_agent_args_raw ? parseJson(transcript_agent_args_raw) : Promise.resolve(void 0),
    transcript_score_raw !== null && transcript_score_raw !== void 0 ? parseJsonValue(transcript_score_raw) : Promise.resolve(void 0)
  ]);
  const identifier = filtered.get("identifier", 0);
  const uuid = filtered.get("uuid", 0);
  const timestamp2 = getOptionalColumn(filtered, "timestamp");
  const answer = filtered.get("answer", 0);
  const label = getOptionalColumn(filtered, "label");
  const explanation = filtered.get("explanation", 0);
  const inputType = filtered.get("input_type", 0);
  const scanError = filtered.get("scan_error", 0);
  const scanErrorTraceback = filtered.get("scan_error_traceback", 0);
  const scanErrorRefusal = getOptionalColumn(filtered, "scan_error_refusal") ?? false;
  const scanId = filtered.get("scan_id", 0);
  const scanTotalTokens = filtered.get("scan_total_tokens", 0);
  const scannerFile = filtered.get("scanner_file", 0);
  const scannerKey = filtered.get("scanner_key", 0);
  const scannerName = filtered.get("scanner_name", 0);
  const transcriptId = filtered.get("transcript_id", 0);
  const transcriptSourceId = filtered.get("transcript_source_id", 0);
  const transcriptSourceUri = filtered.get(
    "transcript_source_uri",
    0
  );
  const transcriptTaskSet = getOptionalColumn(
    filtered,
    "transcript_task_set"
  );
  const transcriptTaskId = getOptionalColumn(
    filtered,
    "transcript_task_id"
  );
  const transcriptTaskRepeat = getOptionalColumn(
    filtered,
    "transcript_task_repeat"
  );
  const transcriptDate = getOptionalColumn(filtered, "transcript_date");
  const transcriptAgent = getOptionalColumn(
    filtered,
    "transcript_agent"
  );
  const transcriptModel = getOptionalColumn(
    filtered,
    "transcript_model"
  );
  const transcriptSuccess = getOptionalColumn(
    filtered,
    "transcript_success"
  );
  const transcriptTotalTime = getOptionalColumn(
    filtered,
    "transcript_total_time"
  );
  const transcriptTotalTokens = getOptionalColumn(
    filtered,
    "transcript_total_tokens"
  );
  const transcriptMessageCount = getOptionalColumn(
    filtered,
    "transcript_message_count"
  );
  const transcriptError = getOptionalColumn(
    filtered,
    "transcript_error"
  );
  const transcriptLimit = getOptionalColumn(
    filtered,
    "transcript_limit"
  );
  const baseData = {
    identifier,
    uuid,
    timestamp: timestamp2,
    answer,
    label,
    eventReferences,
    explanation,
    inputIds,
    messageReferences,
    metadata,
    scanError,
    scanErrorTraceback,
    scanErrorRefusal,
    scanEvents,
    scanId,
    scanMetadata,
    scanModelUsage,
    scanTags,
    scanTotalTokens,
    scannerFile,
    scannerKey,
    scannerName,
    scannerParams,
    transcriptId,
    transcriptMetadata: transcriptMetadata ?? {},
    transcriptSourceId,
    transcriptSourceUri,
    transcriptTaskSet,
    transcriptTaskId,
    transcriptTaskRepeat,
    transcriptAgent,
    transcriptAgentArgs,
    transcriptDate,
    transcriptModel,
    transcriptScore,
    transcriptSuccess,
    transcriptTotalTime,
    transcriptTotalTokens,
    transcriptMessageCount,
    transcriptError,
    transcriptLimit,
    validationResult,
    validationTarget,
    value: value2 ?? null,
    valueType
  };
  resolveTranscriptPropertiesFromMetadata(baseData);
  return { ...baseData, inputType };
};
const parseScanResultSummaries = async (rowData) => Promise.all(
  rowData.map(async (row) => {
    const r = row;
    const valueType = r.value_type;
    const [
      validationResult,
      validationTarget,
      transcriptMetadata,
      eventReferences,
      messageReferences,
      value2
    ] = await Promise.all([
      tryParseJson(r.validation_result),
      tryParseJson(r.validation_target),
      parseJson(r.transcript_metadata),
      parseJson(r.event_references),
      parseJson(r.message_references),
      parseSimpleValue(r.value, valueType)
    ]);
    const baseSummary = {
      identifier: r.identifier,
      uuid: r.uuid,
      label: r.label,
      explanation: r.explanation,
      eventReferences,
      messageReferences,
      validationResult,
      validationTarget,
      value: value2 ?? null,
      valueType,
      transcriptTaskSet: r.transcript_task_set,
      transcriptTaskId: r.transcript_task_id,
      transcriptTaskRepeat: r.transcript_task_repeat,
      transcriptModel: r.transcript_model,
      transcriptMetadata: transcriptMetadata ?? {},
      transcriptSourceId: r.transcript_source_id,
      scanError: r.scan_error,
      scanErrorRefusal: r.scan_error_refusal,
      timestamp: r.timestamp ? r.timestamp : void 0
    };
    resolveTranscriptPropertiesFromMetadata(baseSummary);
    const inputType = r.input_type;
    return { ...baseSummary, inputType };
  })
);
function resolveTranscriptPropertiesFromMetadata(data2) {
  if (data2.transcriptModel === void 0) {
    data2.transcriptModel = data2.transcriptMetadata["model"];
  }
  if (data2.transcriptTaskSet === void 0) {
    data2.transcriptTaskSet = data2.transcriptMetadata["task_name"];
  }
  if (data2.transcriptTaskId === void 0) {
    data2.transcriptTaskId = data2.transcriptMetadata["id"];
  }
  if (data2.transcriptTaskRepeat === void 0) {
    data2.transcriptTaskRepeat = data2.transcriptMetadata["epoch"];
  }
}
const parseJson = async (text) => text !== null ? asyncJsonParse(text) : void 0;
const tryParseJson = async (text) => {
  try {
    return await asyncJsonParse(text);
  } catch {
    return text;
  }
};
const parseSimpleValue = (val, valueType) => valueType === "object" || valueType === "array" ? parseJson(val) : Promise.resolve(val);
const parseJsonValue = (val) => {
  if (!val) {
    return Promise.resolve(void 0);
  }
  if (typeof val === "string" && isJson(val)) {
    return parseJson(val).then((parsed) => parsed);
  } else {
    return Promise.resolve(val);
  }
};
function getOptionalColumn(table2, columnName, rowIndex = 0) {
  return table2.columnNames().includes(columnName) ? table2.get(columnName, rowIndex) : void 0;
}
function isStringValue(result2) {
  return result2.valueType === "string";
}
function isNumberValue(result2) {
  return result2.valueType === "number";
}
function isBooleanValue(result2) {
  return result2.valueType === "boolean";
}
function isNullValue(result2) {
  return result2.valueType === "null";
}
function isArrayValue(result2) {
  return result2.valueType === "array";
}
function isObjectValue(result2) {
  return result2.valueType === "object";
}
function isTranscriptInput(input) {
  return input.inputType === "transcript";
}
function isMessageInput(input) {
  return input.inputType === "message";
}
function isMessagesInput(input) {
  return input.inputType === "messages";
}
function isEventInput(input) {
  return input.inputType === "event";
}
function isEventsInput(input) {
  return input.inputType === "events";
}
const Explanation = ({
  summary,
  references,
  options
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    MarkdownDivWithReferences,
    {
      markdown: summary?.explanation || "",
      references,
      options
    }
  );
};
const result = "_result_mi1dv_1";
const targetValue = "_targetValue_mi1dv_28";
const styles$1 = {
  result,
  "true": "_true_mi1dv_11",
  "false": "_false_mi1dv_16",
  targetValue
};
const ValidationResult = ({
  result: result2,
  target,
  label
}) => {
  if (typeof result2 === "boolean") {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      Result,
      {
        value: result2,
        targetValue: valueStr(resolveTargetValue(target, label))
      }
    );
  } else if (result2 !== null && typeof result2 === "object") {
    const entries2 = Object.entries(result2);
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles$1.validationTable), children: entries2.map(([key2, value2]) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      Result,
      {
        value: value2,
        targetValue: valueStr(resolveTargetValue(target, key2))
      }
    ) }, `validation-result-${key2}`)) });
  }
};
const Result = ({
  value: value2,
  targetValue: targetValue2
}) => {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(value2 ? styles$1.true : styles$1.false, styles$1.result), children: value2 ? /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(ApplicationIcons.check) }) : /* @__PURE__ */ jsxRuntimeExports.jsx("i", { className: clsx(ApplicationIcons.x) }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "span",
      {
        className: clsx(
          styles$1.targetValue,
          "text-size-smallestest",
          "text-style-secondary"
        ),
        title: targetValue2,
        children: targetValue2
      }
    )
  ] });
};
const resolveTargetValue = (target, key2) => {
  if (target === void 0) {
    return "";
  }
  if (key2 === void 0) {
    return target;
  }
  if (target && typeof target === "object" && !Array.isArray(target)) {
    return target[key2] || false;
  }
  return target;
};
const valueStr = (target) => {
  if (target === null) {
    return "null";
  } else if (typeof target === "string") {
    return target;
  } else if (typeof target === "number" || typeof target === "boolean") {
    return target.toString();
  } else if (Array.isArray(target)) {
    return `[Array(${target.length})]`;
  } else if (typeof target === "object") {
    return "{Object}";
  } else {
    return "undefined";
  }
};
const boolean = "_boolean_8citi_1";
const valueTable = "_valueTable_8citi_25";
const valueKey = "_valueKey_8citi_32";
const inline = "_inline_8citi_38";
const valueValue = "_valueValue_8citi_38";
const value = "_value_8citi_25";
const styles = {
  boolean,
  "true": "_true_8citi_13",
  "false": "_false_8citi_19",
  valueTable,
  valueKey,
  inline,
  valueValue,
  value
};
const Value = ({
  summary: result2,
  references,
  style,
  maxTableSize = 5,
  interactive = false,
  options
}) => {
  if (isStringValue(result2)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      MarkdownDivWithReferences,
      {
        markdown: result2.value,
        references,
        options
      }
    );
  } else if (isNumberValue(result2) && result2.value !== null) {
    return formatPrettyDecimal(result2.value);
  } else if (isBooleanValue(result2)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: clsx(
          styles.boolean,
          result2.value ? styles.true : styles.false
        ),
        children: String(result2.value)
      }
    );
  } else if (isNullValue(result2)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("code", { children: "null" });
  } else if (isArrayValue(result2)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      ValueList2,
      {
        value: result2.value,
        summary: result2,
        references,
        style,
        maxListSize: maxTableSize,
        interactive
      }
    );
  } else if (isObjectValue(result2)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      ValueTable,
      {
        value: result2.value,
        summary: result2,
        references,
        style,
        maxTableSize,
        interactive
      }
    );
  } else {
    return "Unknown value type";
  }
};
const ValueList2 = ({
  value: value2,
  summary: result2,
  maxListSize,
  interactive,
  references,
  style
}) => {
  const itemsToDisplay = value2.slice(0, maxListSize);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: clsx(
        styles.valueTable,
        style === "inline" ? styles.inline : styles.block
      ),
      children: itemsToDisplay.map((item, index) => {
        const displayValue = renderValue(
          index,
          item,
          result2,
          references,
          interactive
        );
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "div",
            {
              className: clsx(
                styles.valueKey,
                "text-style-label",
                "text-style-secondary",
                "text-size-smallest"
              ),
              children: [
                "[",
                index,
                "]"
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles.valueValue), children: displayValue })
        ] }, `value-table-row-${index}`);
      })
    }
  );
};
const ValueTable = ({
  value: value2,
  summary: result2,
  maxTableSize,
  interactive,
  references,
  style
}) => {
  const sortedKeys = Object.keys(value2).sort((a, b) => {
    const aVal = value2[a];
    const bVal = value2[b];
    if (typeof aVal === "boolean" && typeof bVal === "boolean") {
      return Number(bVal) - Number(aVal);
    } else if (typeof aVal === "number" && typeof bVal === "number") {
      return bVal - aVal;
    } else {
      return 0;
    }
  });
  const keysToDisplay = sortedKeys.slice(0, maxTableSize);
  const notShown = Object.keys(value2).length - maxTableSize;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: clsx(
        styles.valueTable,
        style === "inline" ? styles.inline : styles.block
      ),
      children: [
        keysToDisplay.map((key2, index) => {
          const displayValue = renderValue(
            index,
            value2[key2],
            result2,
            references,
            interactive
          );
          return /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "div",
              {
                className: clsx(
                  styles.valueKey,
                  "text-style-label",
                  "text-style-secondary",
                  "text-size-smallest"
                ),
                children: key2
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles.valueValue), children: displayValue })
          ] }, `value-table-row-${key2}`);
        }),
        notShown > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(reactExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "div",
            {
              className: clsx(
                styles.valueKey,
                "text-style-label",
                "text-style-secondary",
                "text-size-smallest"
              ),
              children: [
                notShown,
                " more…"
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles.valueValue) })
        ] }, `value-table-row-more`)
      ]
    }
  );
};
const renderValue = (index, val, summary, references, interactive) => {
  if (typeof val === "string") {
    return /* @__PURE__ */ jsxRuntimeExports.jsx(MarkdownDivWithReferences, { markdown: val, references });
  } else if (typeof val === "number") {
    return formatPrettyDecimal(val);
  } else if (typeof val === "boolean") {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: clsx(styles.boolean, val ? styles.true : styles.false), children: String(val) });
  } else if (val === null) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("pre", { className: clsx(styles.value), children: "null" });
  } else if (Array.isArray(val)) {
    return printArray(val, 25);
  } else if (typeof val === "object") {
    return !interactive ? printObject(val, 35) : /* @__PURE__ */ jsxRuntimeExports.jsx(
      RecordTree,
      {
        id: `value-record-${summary.identifier}-${index}`,
        record: val
      }
    );
  } else {
    return "Unknown value type";
  }
};
const TranscriptView = ({
  id,
  events,
  nodeFilter,
  scrollRef,
  initialEventId,
  className
}) => {
  const { eventNodes, defaultCollapsedIds } = useEventNodes(
    events || [],
    false
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    TranscriptViewNodes,
    {
      id,
      eventNodes,
      defaultCollapsedIds,
      nodeFilter,
      scrollRef,
      initialEventId,
      className
    }
  );
};
const useMarkdownRefs = (summary, inputData) => {
  const { scansDir, scanPath } = useScanRoute();
  const [currentSearchParams] = useSearchParams();
  const buildUrl = reactExports.useMemo(() => {
    if (!summary?.identifier) {
      return (queryParams) => `?${queryParams}`;
    }
    return (queryParams) => {
      if (!scansDir) {
        return `?${queryParams}`;
      }
      const mergedParams = new URLSearchParams(currentSearchParams);
      const newParams = new URLSearchParams(queryParams);
      for (const [key2, value2] of newParams) {
        mergedParams.set(key2, value2);
      }
      return `#${scanResultRoute(scansDir, scanPath, summary.identifier, mergedParams)}`;
    };
  }, [summary?.identifier, scanPath, scansDir, currentSearchParams]);
  const refs = summary ? toMarkdownRefs(
    summary,
    (refId, type) => {
      if (type === "message") {
        return buildUrl(`tab=Result&message=${encodeURIComponent(refId)}`);
      } else {
        return buildUrl(`tab=Result&event=${encodeURIComponent(refId)}`);
      }
    },
    inputData
  ) : [];
  return refs;
};
const toMarkdownRefs = (summary, makeReferenceUrl, inputData) => {
  const refLookup = referenceTable(inputData);
  const refs = [];
  for (const ref2 of summary.messageReferences) {
    const renderPreview = refLookup[ref2.id];
    const refUrl = makeReferenceUrl(ref2.id, "message");
    if (ref2.cite && (renderPreview || refUrl)) {
      refs.push({
        id: ref2.id,
        cite: ref2.cite,
        citePreview: renderPreview,
        citeUrl: refUrl
      });
    }
  }
  for (const ref2 of summary.eventReferences) {
    const renderPreview = refLookup[ref2.id];
    const refUrl = makeReferenceUrl(ref2.id, "event");
    if (ref2.cite && (renderPreview || refUrl)) {
      refs.push({
        id: ref2.id,
        cite: ref2.cite,
        citePreview: renderPreview,
        citeUrl: refUrl
      });
    }
  }
  return refs;
};
const referenceTable = (inputData) => {
  if (!inputData) {
    return {};
  }
  if (isMessageInput(inputData)) {
    if (!inputData.input.id) {
      return {};
    }
    return {
      [inputData.input.id]: () => {
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          ChatView,
          {
            messages: [inputData.input],
            resolveToolCallsIntoPreviousMessage: false
          }
        );
      }
    };
  } else if (isMessagesInput(inputData)) {
    return inputData.input.reduce(
      (acc, msg) => {
        if (msg.id) {
          acc[msg.id] = () => {
            return /* @__PURE__ */ jsxRuntimeExports.jsx(
              ChatView,
              {
                messages: [msg],
                resolveToolCallsIntoPreviousMessage: false
              }
            );
          };
        }
        return acc;
      },
      {}
    );
  } else if (isEventInput(inputData)) {
    if (!inputData.input.uuid) {
      return {};
    }
    return {
      [inputData.input.uuid]: () => {
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          TranscriptView,
          {
            id: "input-event-preview",
            events: [inputData.input]
          }
        );
      }
    };
  } else if (isEventsInput(inputData)) {
    return inputData.input.reduce(
      (acc, event, index) => {
        if (event.uuid) {
          acc[event.uuid] = () => {
            return /* @__PURE__ */ jsxRuntimeExports.jsx(
              TranscriptView,
              {
                id: `input-event-preview-${index}`,
                events: inputData.input
              }
            );
          };
        }
        return acc;
      },
      {}
    );
  } else if (isTranscriptInput(inputData)) {
    const eventRefs = (inputData.input.events || []).reduce((acc, event) => {
      if (event.uuid) {
        acc[event.uuid] = () => {
          return /* @__PURE__ */ jsxRuntimeExports.jsx(TranscriptView, { id: "input-event-preview", events: [event] });
        };
      }
      return acc;
    }, {});
    const messageRefs = (inputData.input.messages || []).reduce((acc, msg) => {
      if (msg.id) {
        acc[msg.id] = () => {
          return /* @__PURE__ */ jsxRuntimeExports.jsx(
            ChatView,
            {
              messages: [msg],
              resolveToolCallsIntoPreviousMessage: false
            }
          );
        };
      }
      return acc;
    }, {});
    return { ...eventRefs, ...messageRefs };
  } else {
    return {};
  }
};
export {
  Card as C,
  Explanation as E,
  TranscriptView as T,
  Value as V,
  CardHeader as a,
  CardBody as b,
  ValidationResult as c,
  resultLog as d,
  resultIdentifier as e,
  isBooleanValue as f,
  isStringValue as g,
  isArrayValue as h,
  isNumberValue as i,
  isObjectValue as j,
  useSelectedScanner as k,
  useSelectedScanDataframe as l,
  useSelectedScan as m,
  getScanDisplayName as n,
  parseScanResultData as o,
  parseScanResultSummaries as p,
  isTranscriptInput as q,
  resultIdentifierStr as r,
  isMessagesInput as s,
  isMessageInput as t,
  useMarkdownRefs as u,
  isEventsInput as v,
  isEventInput as w
};
//# sourceMappingURL=refs.js.map
